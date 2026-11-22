"""
Policy Domain Service for Kolang ACP (ACP-012).

Provides:
- Workspace-scoped lifecycle management for Access Control Policies (Policy)
- Segregated draft authoring and version publishing
- Deterministic SHA-256 checksum computation and immutability guarantees
- Strict workspace isolation and anti-IDOR protection
- PDP evaluation gateway filtering (preventing drafts from being enforced)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from acp_core.common.errors import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from acp_core.policy.models import (
    Policy,
    PolicyCreate,
    PolicyDraftUpdate,
    PolicyPublishRequest,
    PolicyRead,
    PolicyStatus,
    PolicyVersion,
    PolicyVersionRead,
    PolicyVersionStatus,
    compute_policy_checksum,
)
from acp_core.workspaces.models import Workspace

logger = structlog.get_logger(__name__)


class PolicyService:
    """
    Domain service for Policy authoring, publishing, versioning, and evaluation retrieval.

    Enforces workspace isolation, draft/publish segregation, version immutability,
    and audit tracking.
    """

    def __init__(self, session: AsyncSession | None = None) -> None:
        self._default_session = session

    def _get_session(self, session: AsyncSession | None) -> AsyncSession:
        active = session or self._default_session
        if active is None:
            msg = "An active AsyncSession is required to execute PolicyService operations."
            raise ValueError(msg)
        return active

    async def create_policy_draft(
        self,
        workspace_id: uuid.UUID,
        payload: PolicyCreate,
        session: AsyncSession | None = None,
    ) -> PolicyRead:
        """
        Create a new Access Control Policy in DRAFT status.

        The draft policy is not published and will NOT be evaluated by the gateway PDP.
        Enforces workspace boundary and unique slug constraint per workspace.
        """
        s = self._get_session(session)

        # 1. Verify workspace exists
        ws_stmt = select(Workspace.id).where(Workspace.id == workspace_id)
        if (await s.execute(ws_stmt)).scalar_one_or_none() is None:
            raise NotFoundError(f"Workspace '{workspace_id}' not found.")

        # 2. Check slug uniqueness within workspace
        slug_stmt = select(Policy.id).where(
            Policy.workspace_id == workspace_id,
            Policy.slug == payload.slug,
        )
        if (await s.execute(slug_stmt)).scalar_one_or_none() is not None:
            raise ConflictError(
                f"Policy with slug '{payload.slug}' already exists in workspace '{workspace_id}'."
            )

        now = datetime.now(UTC)
        policy = Policy(
            id=payload.id or uuid.uuid4(),
            workspace_id=workspace_id,
            name=payload.name,
            slug=payload.slug,
            description=payload.description,
            status=PolicyStatus.DRAFT.value,
            draft_rego=payload.draft_rego,
            draft_bundle_reference=payload.draft_bundle_reference,
            active_version_id=None,
            active_version_number=None,
            created_by=payload.created_by,
            updated_by=None,
            created_at=now,
            updated_at=now,
        )
        s.add(policy)
        await s.commit()
        await s.refresh(policy)

        logger.info(
            "policy.draft_created",
            workspace_id=str(workspace_id),
            policy_id=str(policy.id),
            slug=policy.slug,
            status=policy.status,
            created_by=policy.created_by,
        )
        return PolicyRead.model_validate(policy)

    async def update_policy_draft(
        self,
        workspace_id: uuid.UUID,
        policy_id: uuid.UUID,
        payload: PolicyDraftUpdate,
        updated_by: str,
        session: AsyncSession | None = None,
    ) -> PolicyRead:
        """
        Update draft configuration or Rego code of an existing policy.

        Modifying draft code does NOT affect previously published immutable versions.
        """
        s = self._get_session(session)

        stmt = select(Policy).where(
            Policy.id == policy_id,
            Policy.workspace_id == workspace_id,
        )
        policy = (await s.execute(stmt)).scalar_one_or_none()
        if policy is None:
            raise NotFoundError(f"Policy '{policy_id}' not found in workspace.")

        if payload.name is not None:
            policy.name = payload.name
        if payload.description is not None:
            policy.description = payload.description
        if payload.draft_rego is not None:
            policy.draft_rego = payload.draft_rego
        if payload.draft_bundle_reference is not None:
            policy.draft_bundle_reference = payload.draft_bundle_reference

        policy.updated_by = updated_by or payload.updated_by
        policy.updated_at = datetime.now(UTC)

        await s.commit()
        await s.refresh(policy)

        logger.info(
            "policy.draft_updated",
            workspace_id=str(workspace_id),
            policy_id=str(policy.id),
            updated_by=policy.updated_by,
        )
        return PolicyRead.model_validate(policy)

    async def publish_policy_version(
        self,
        workspace_id: uuid.UUID,
        policy_id: uuid.UUID,
        payload: PolicyPublishRequest,
        published_by: str,
        session: AsyncSession | None = None,
    ) -> PolicyVersionRead:
        """
        Publish a new, immutable PolicyVersion from draft or explicit code.

        Enforces:
        - Version numbers are sequential (1, 2, 3...)
        - Deterministic SHA-256 checksum is computed and stored
        - Previous published versions remain completely intact in history
        - Policy transitions to ACTIVE status and references this new active version
        """
        s = self._get_session(session)

        stmt = select(Policy).where(
            Policy.id == policy_id,
            Policy.workspace_id == workspace_id,
        )
        policy = (await s.execute(stmt)).scalar_one_or_none()
        if policy is None:
            raise NotFoundError(f"Policy '{policy_id}' not found in workspace.")

        # Determine rego source to publish
        rego_source = payload.rego_source if payload.rego_source is not None else policy.draft_rego
        if not rego_source or not rego_source.strip():
            raise ValidationError("Cannot publish policy version without rego_source.")

        bundle_reference = (
            payload.bundle_reference
            if payload.bundle_reference is not None
            else policy.draft_bundle_reference
        )

        # Compute SHA-256 checksum
        checksum = compute_policy_checksum(rego_source, bundle_reference)

        # Determine sequential version number
        v_stmt = select(func.coalesce(func.max(PolicyVersion.version), 0)).where(
            PolicyVersion.policy_id == policy.id,
        )
        max_version = (await s.execute(v_stmt)).scalar_one()
        next_version = int(max_version) + 1

        # Supersede prior active version(s) in history without deleting them
        if policy.active_version_id is not None:
            prev_stmt = select(PolicyVersion).where(
                PolicyVersion.policy_id == policy.id,
                PolicyVersion.status == PolicyVersionStatus.PUBLISHED.value,
            )
            prev_versions = (await s.execute(prev_stmt)).scalars().all()
            for pv in prev_versions:
                pv.status = PolicyVersionStatus.SUPERSEDED.value

        now = datetime.now(UTC)
        # Create immutable new version
        new_version = PolicyVersion(
            id=uuid.uuid4(),
            policy_id=policy.id,
            workspace_id=workspace_id,
            version=next_version,
            rego_source=rego_source,
            bundle_reference=bundle_reference,
            checksum=checksum,
            description=payload.description or f"Release v{next_version}",
            status=PolicyVersionStatus.PUBLISHED.value,
            published_at=now,
            published_by=published_by,
            created_at=now,
        )
        s.add(new_version)
        await s.flush()

        # Update policy active pointer and transition to ACTIVE status
        policy.active_version_id = new_version.id
        policy.active_version_number = new_version.version
        policy.status = PolicyStatus.ACTIVE.value
        policy.updated_by = published_by

        await s.commit()
        await s.refresh(new_version)

        logger.info(
            "policy.version_published",
            workspace_id=str(workspace_id),
            policy_id=str(policy.id),
            version=new_version.version,
            checksum=new_version.checksum,
            published_by=published_by,
        )
        return PolicyVersionRead.model_validate(new_version)

    async def get_policy(
        self,
        workspace_id: uuid.UUID,
        policy_id: uuid.UUID,
        session: AsyncSession | None = None,
    ) -> PolicyRead:
        """
        Retrieve a policy by ID strictly within the caller's workspace boundary.

        Raises NotFoundError if the policy does not exist in the caller's workspace,
        preventing IDOR enumeration across tenants.
        """
        s = self._get_session(session)
        stmt = select(Policy).where(
            Policy.id == policy_id,
            Policy.workspace_id == workspace_id,
        )
        policy = (await s.execute(stmt)).scalar_one_or_none()
        if policy is None:
            logger.warning(
                "security.idor_policy_access_blocked",
                workspace_id=str(workspace_id),
                attempted_policy_id=str(policy_id),
            )
            raise NotFoundError(f"Policy '{policy_id}' not found.")
        return PolicyRead.model_validate(policy)

    async def get_policy_by_slug(
        self,
        workspace_id: uuid.UUID,
        slug: str,
        session: AsyncSession | None = None,
    ) -> PolicyRead:
        """Retrieve a policy by slug strictly within the caller's workspace boundary."""
        s = self._get_session(session)
        stmt = select(Policy).where(
            Policy.slug == slug,
            Policy.workspace_id == workspace_id,
        )
        policy = (await s.execute(stmt)).scalar_one_or_none()
        if policy is None:
            raise NotFoundError(f"Policy with slug '{slug}' not found.")
        return PolicyRead.model_validate(policy)

    async def list_policies(
        self,
        workspace_id: uuid.UUID,
        status: PolicyStatus | None = None,
        session: AsyncSession | None = None,
    ) -> list[PolicyRead]:
        """List all policies scoped strictly to the specified workspace."""
        s = self._get_session(session)
        query = select(Policy).where(Policy.workspace_id == workspace_id)
        if status is not None:
            query = query.where(Policy.status == status.value)
        query = query.order_by(Policy.created_at.desc())

        result = await s.execute(query)
        policies = result.scalars().all()
        return [PolicyRead.model_validate(p) for p in policies]

    async def get_active_version_for_evaluation(
        self,
        workspace_id: uuid.UUID,
        policy_id: uuid.UUID,
        session: AsyncSession | None = None,
    ) -> PolicyVersionRead | None:
        """
        Retrieve the active policy version for gateway Policy Decision Point (PDP) evaluation.

        ENFORCEMENT OF ACP-012 RULE 3:
        Policy drafts or unpublished policies MUST NEVER be applied to the Gateway.
        Returns None if:
        - Policy status is DRAFT.
        - Policy has no active published version (active_version_id is None).
        - Policy is archived or deprecated.
        """
        s = self._get_session(session)
        policy_stmt = select(Policy).where(
            Policy.id == policy_id,
            Policy.workspace_id == workspace_id,
        )
        policy = (await s.execute(policy_stmt)).scalar_one_or_none()
        if policy is None:
            raise NotFoundError(f"Policy '{policy_id}' not found.")

        # If policy is draft or not active, or has no active version, return None
        if policy.status != PolicyStatus.ACTIVE.value or policy.active_version_id is None:
            return None

        v_stmt = select(PolicyVersion).where(
            PolicyVersion.id == policy.active_version_id,
            PolicyVersion.workspace_id == workspace_id,
        )
        version = (await s.execute(v_stmt)).scalar_one_or_none()
        if version is None:
            return None

        return PolicyVersionRead.model_validate(version)

    async def get_policy_version(
        self,
        workspace_id: uuid.UUID,
        policy_id: uuid.UUID,
        version: int,
        session: AsyncSession | None = None,
    ) -> PolicyVersionRead:
        """Retrieve a specific version of a policy strictly within workspace scope."""
        s = self._get_session(session)
        stmt = select(PolicyVersion).where(
            PolicyVersion.policy_id == policy_id,
            PolicyVersion.workspace_id == workspace_id,
            PolicyVersion.version == version,
        )
        pv = (await s.execute(stmt)).scalar_one_or_none()
        if pv is None:
            raise NotFoundError(
                f"Policy version v{version} not found for policy '{policy_id}' in workspace."
            )
        return PolicyVersionRead.model_validate(pv)

    async def list_policy_versions(
        self,
        workspace_id: uuid.UUID,
        policy_id: uuid.UUID,
        session: AsyncSession | None = None,
    ) -> list[PolicyVersionRead]:
        """
        List all historical published versions of a policy in descending version order.

        Guarantees that previous versions remain intact after new versions are published.
        """
        s = self._get_session(session)

        # Enforce that parent policy belongs to the workspace
        p_stmt = select(Policy.id).where(
            Policy.id == policy_id,
            Policy.workspace_id == workspace_id,
        )
        if (await s.execute(p_stmt)).scalar_one_or_none() is None:
            raise NotFoundError(f"Policy '{policy_id}' not found in workspace.")

        stmt = (
            select(PolicyVersion)
            .where(
                PolicyVersion.policy_id == policy_id,
                PolicyVersion.workspace_id == workspace_id,
            )
            .order_by(PolicyVersion.version.desc())
        )
        result = await s.execute(stmt)
        versions = result.scalars().all()
        return [PolicyVersionRead.model_validate(v) for v in versions]

    async def delete_policy(
        self,
        workspace_id: uuid.UUID,
        policy_id: uuid.UUID,
        session: AsyncSession | None = None,
    ) -> None:
        """Delete a policy and cascade deletion to all its versions."""
        s = self._get_session(session)
        stmt = select(Policy).where(
            Policy.id == policy_id,
            Policy.workspace_id == workspace_id,
        )
        policy = (await s.execute(stmt)).scalar_one_or_none()
        if policy is None:
            raise NotFoundError(f"Policy '{policy_id}' not found in workspace.")

        await s.delete(policy)
        await s.commit()
        logger.info(
            "policy.deleted",
            workspace_id=str(workspace_id),
            policy_id=str(policy_id),
        )
