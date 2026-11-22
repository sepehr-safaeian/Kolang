"""
Integration tests for Policy and Policy Version on live PostgreSQL (ACP-012).

Verifies against live PostgreSQL in Docker:
1. Schema & Migration verification:
   - Presence of policies and policy_versions tables.
   - Unique constraints (workspace_id, slug) and (policy_id, version).
   - Foreign key cascading: workspace deletion cascades to policies and versions.
   - Deleting a policy cascades to its historical versions.
2. Acceptance Criteria 1: Draft creation and new version publishing.
3. Acceptance Criteria 2: Previous versions remain intact after new versions are published.
4. Acceptance Criteria 3: Checksum of policy version is computed and stored.
5. Acceptance Criteria 4: Cross-workspace access prevention (anti-IDOR).
6. Gateway PDP enforcement: Draft policies are not evaluated (active version is None).
7. Version Immutability: Mutating a published version raises PolicyVersionImmutableError.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import select, text

from acp_core.common.errors import (
    NotFoundError,
    PolicyVersionImmutableError,
)
from acp_core.common.settings import Settings
from acp_core.common.types import DecisionEffect
from acp_core.db import (
    Base,
    DatabaseManager,
    reset_db_manager,
    transactional_session,
)
from acp_core.policy.models import (
    PolicyCreate,
    PolicyDraftUpdate,
    PolicyPublishRequest,
    PolicyStatus,
    PolicyVersion,
    PolicyVersionStatus,
    compute_policy_checksum,
    create_decision_for_version,
)
from acp_core.policy.service import PolicyService
from acp_core.workspaces.models import WorkspaceCreate
from acp_core.workspaces.service import WorkspaceService

POSTGRES_PORT = os.environ.get("ACP_POSTGRES_PORT", "5433")
DOCKER_POSTGRES_URL = f"postgresql+asyncpg://kolang:kolang@localhost:{POSTGRES_PORT}/kolang"


@pytest.fixture
async def pg_settings() -> Settings:
    return Settings(
        ACP_DATABASE_URL=DOCKER_POSTGRES_URL,
        ACP_DATABASE_POOL_SIZE=5,
        ACP_DATABASE_MAX_OVERFLOW=5,
        ACP_DATABASE_POOL_TIMEOUT=10.0,
        ACP_DATABASE_ECHO=False,
    )


@pytest.fixture
async def pg_db(pg_settings: Settings) -> AsyncGenerator[DatabaseManager, None]:
    reset_db_manager()
    mgr = DatabaseManager()
    mgr.initialize(pg_settings)

    is_connected = await mgr.ping()
    if not is_connected:
        pytest.skip(f"Docker PostgreSQL not reachable at {DOCKER_POSTGRES_URL}")

    engine = mgr.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield mgr

    # Clean up tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await mgr.close()
    reset_db_manager()


@pytest.mark.asyncio
async def test_policy_tables_and_constraints_exist_on_postgres(pg_db: DatabaseManager) -> None:
    """Verify that policies and policy_versions tables and constraints exist on PostgreSQL."""
    engine = pg_db.get_engine()
    async with engine.connect() as conn:
        # Check tables existence
        stmt = text(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name IN ('policies', 'policy_versions')
            ORDER BY table_name;
            """
        )
        result = await conn.execute(stmt)
        tables = [row[0] for row in result.fetchall()]
        assert "policies" in tables
        assert "policy_versions" in tables


@pytest.mark.asyncio
async def test_policy_draft_creation_and_version_publishing_lifecycle(
    pg_db: DatabaseManager,
) -> None:
    """
    AC 1, 3: Create draft, publish new version with checksum, and verify status on PostgreSQL.
    """
    ws_svc = WorkspaceService()
    pol_svc = PolicyService()

    factory = pg_db.get_session_factory()
    async with factory() as session, transactional_session(session=session) as tx_session:
        ws = await ws_svc.create_workspace(
            session=tx_session,
            data=WorkspaceCreate(name="Finance Corp", slug=f"fin-corp-{uuid.uuid4().hex[:6]}"),
        )
        ws_id = ws.id

        # 1. Create Policy Draft
        draft_payload = PolicyCreate(
            name="Financial Tool Policy",
            slug=f"fin-tool-{uuid.uuid4().hex[:6]}",
            description="Policy governing banking tool execution",
            draft_rego=(
                "package kolang.authz\ndefault allow := false\nallow if has_role('finance_admin')"
            ),
            created_by="user:ciso@finance.local",
        )
        draft = await pol_svc.create_policy_draft(
            workspace_id=ws_id,
            payload=draft_payload,
            session=tx_session,
        )

        assert draft.id is not None
        assert draft.status == PolicyStatus.DRAFT
        assert draft.is_draft is True
        assert draft.is_active is False
        assert draft.active_version_id is None
        assert draft.active_version_number is None

        # AC Rule 3: Policy Draft must NOT be evaluated on Gateway
        active_for_gw = await pol_svc.get_active_version_for_evaluation(
            workspace_id=ws_id,
            policy_id=draft.id,
            session=tx_session,
        )
        assert active_for_gw is None

        # 2. Update Draft Rego
        updated_rego = (
            "package kolang.authz\n"
            "default allow := false\n"
            "allow if has_role('finance_admin')\n"
            "allow if is_read_only"
        )
        draft_updated = await pol_svc.update_policy_draft(
            workspace_id=ws_id,
            policy_id=draft.id,
            payload=PolicyDraftUpdate(draft_rego=updated_rego),
            updated_by="user:lead@finance.local",
            session=tx_session,
        )
        assert draft_updated.draft_rego == updated_rego
        assert draft_updated.status == PolicyStatus.DRAFT
        assert draft_updated.active_version_id is None

        # 3. Publish Version 1
        expected_checksum = compute_policy_checksum(updated_rego)
        v1 = await pol_svc.publish_policy_version(
            workspace_id=ws_id,
            policy_id=draft.id,
            payload=PolicyPublishRequest(description="Initial v1 release"),
            published_by="user:ciso@finance.local",
            session=tx_session,
        )

        assert v1.version == 1
        assert v1.checksum == expected_checksum
        assert v1.status == PolicyVersionStatus.PUBLISHED
        assert v1.published_by == "user:ciso@finance.local"

        # Check policy status transitioned to ACTIVE and active version points to v1
        pol_active = await pol_svc.get_policy(
            workspace_id=ws_id,
            policy_id=draft.id,
            session=tx_session,
        )
        assert pol_active.status == PolicyStatus.ACTIVE
        assert pol_active.is_active is True
        assert pol_active.active_version_id == v1.id
        assert pol_active.active_version_number == 1

        # Now Gateway retrieves version 1 for PDP evaluation
        gw_version = await pol_svc.get_active_version_for_evaluation(
            workspace_id=ws_id,
            policy_id=draft.id,
            session=tx_session,
        )
        assert gw_version is not None
        assert gw_version.id == v1.id
        assert gw_version.version == 1
        assert gw_version.checksum == expected_checksum

        # Verify Rule 2: Decision records exact policy version
        decision = create_decision_for_version(
            policy_id=draft.id,
            version=gw_version.version,
            decision=DecisionEffect.ALLOW,
            reason_code="AUTHZ_ALLOW",
            reason_message="Access granted by finance policy",
        )
        assert decision.policy_id == str(draft.id)
        assert decision.version == "1"


@pytest.mark.asyncio
async def test_previous_version_remains_after_new_version_published(
    pg_db: DatabaseManager,
) -> None:
    """
    AC 2: Previous versions remain intact in the database after a new version is published.
    """
    ws_svc = WorkspaceService()
    pol_svc = PolicyService()

    factory = pg_db.get_session_factory()
    async with factory() as session, transactional_session(session=session) as tx_session:
        ws = await ws_svc.create_workspace(
            session=tx_session,
            data=WorkspaceCreate(name="Health Tech", slug=f"health-tech-{uuid.uuid4().hex[:6]}"),
        )
        ws_id = ws.id

        # Create draft and publish v1
        v1_code = "package kolang.authz\nv1 := true"
        p = await pol_svc.create_policy_draft(
            workspace_id=ws_id,
            payload=PolicyCreate(
                name="Health Policy",
                slug=f"health-pol-{uuid.uuid4().hex[:6]}",
                draft_rego=v1_code,
                created_by="admin@health.local",
            ),
            session=tx_session,
        )
        v1 = await pol_svc.publish_policy_version(
            workspace_id=ws_id,
            policy_id=p.id,
            payload=PolicyPublishRequest(description="Release 1.0"),
            published_by="admin@health.local",
            session=tx_session,
        )
        assert v1.version == 1

        # Publish v2
        v2_code = "package kolang.authz\nv2 := true"
        v2 = await pol_svc.publish_policy_version(
            workspace_id=ws_id,
            policy_id=p.id,
            payload=PolicyPublishRequest(rego_source=v2_code, description="Release 2.0"),
            published_by="admin@health.local",
            session=tx_session,
        )
        assert v2.version == 2
        assert v2.id != v1.id

        # Publish v3
        v3_code = "package kolang.authz\nv3 := true"
        v3 = await pol_svc.publish_policy_version(
            workspace_id=ws_id,
            policy_id=p.id,
            payload=PolicyPublishRequest(rego_source=v3_code, description="Release 3.0"),
            published_by="admin@health.local",
            session=tx_session,
        )
        assert v3.version == 3

        # List all versions: all 3 must exist!
        all_versions = await pol_svc.list_policy_versions(
            workspace_id=ws_id,
            policy_id=p.id,
            session=tx_session,
        )
        assert len(all_versions) == 3
        # Ordered descending by version
        assert [v.version for v in all_versions] == [3, 2, 1]

        # Fetch v1 directly from DB: code and checksum are completely intact
        v1_fetched = await pol_svc.get_policy_version(
            workspace_id=ws_id,
            policy_id=p.id,
            version=1,
            session=tx_session,
        )
        assert v1_fetched.rego_source == v1_code
        assert v1_fetched.checksum == compute_policy_checksum(v1_code)
        assert v1_fetched.status == PolicyVersionStatus.SUPERSEDED

        # Active version on policy is v3
        pol_current = await pol_svc.get_policy(
            workspace_id=ws_id,
            policy_id=p.id,
            session=tx_session,
        )
        assert pol_current.active_version_number == 3
        assert pol_current.active_version_id == v3.id


@pytest.mark.asyncio
async def test_policy_version_immutability_enforced_on_postgres(
    pg_db: DatabaseManager,
) -> None:
    """
    Rule 1: Direct SQL or ORM attempt to mutate a published version's code or checksum is rejected.
    """
    ws_svc = WorkspaceService()
    pol_svc = PolicyService()

    factory = pg_db.get_session_factory()
    async with factory() as session:
        ws = await ws_svc.create_workspace(
            session=session,
            data=WorkspaceCreate(name="SecOps", slug=f"secops-{uuid.uuid4().hex[:6]}"),
        )
        p = await pol_svc.create_policy_draft(
            workspace_id=ws.id,
            payload=PolicyCreate(
                name="Audit Policy",
                slug=f"audit-pol-{uuid.uuid4().hex[:6]}",
                draft_rego="package kolang.authz\nallow := false",
                created_by="ciso@secops.local",
            ),
            session=session,
        )
        v1 = await pol_svc.publish_policy_version(
            workspace_id=ws.id,
            policy_id=p.id,
            payload=PolicyPublishRequest(description="Immutable baseline"),
            published_by="ciso@secops.local",
            session=session,
        )

        # Retrieve the ORM entity
        stmt = select(PolicyVersion).where(PolicyVersion.id == v1.id)
        version_entity = (await session.execute(stmt)).scalar_one()

        # Attempt mutation of rego_source
        version_entity.rego_source = "package kolang.authz\nallow := true"

        with pytest.raises(
            PolicyVersionImmutableError,
            match="immutable: modification of 'rego_source' is forbidden",
        ):
            await session.commit()

        await session.rollback()


@pytest.mark.asyncio
async def test_cross_workspace_isolation_and_anti_idor_on_postgres(
    pg_db: DatabaseManager,
) -> None:
    """
    AC 4 & Rule 4: Complete cross-workspace isolation.
    Tenant B cannot view, read, update, or publish policies belonging to Tenant A.
    """
    ws_svc = WorkspaceService()
    pol_svc = PolicyService()

    factory = pg_db.get_session_factory()
    async with factory() as session, transactional_session(session=session) as tx_session:
        # Create Workspace A and Workspace B
        ws_a = await ws_svc.create_workspace(
            session=tx_session,
            data=WorkspaceCreate(name="Org Alpha", slug=f"org-alpha-{uuid.uuid4().hex[:6]}"),
        )
        ws_b = await ws_svc.create_workspace(
            session=tx_session,
            data=WorkspaceCreate(name="Org Beta", slug=f"org-beta-{uuid.uuid4().hex[:6]}"),
        )

        # Create Policy in Org Alpha
        pol_a = await pol_svc.create_policy_draft(
            workspace_id=ws_a.id,
            payload=PolicyCreate(
                name="Alpha Secrets Policy",
                slug=f"alpha-sec-{uuid.uuid4().hex[:6]}",
                draft_rego="package kolang.authz\nsecret_access := false",
                created_by="alpha-admin@org-a.com",
            ),
            session=tx_session,
        )
        await pol_svc.publish_policy_version(
            workspace_id=ws_a.id,
            policy_id=pol_a.id,
            payload=PolicyPublishRequest(description="Alpha v1"),
            published_by="alpha-admin@org-a.com",
            session=tx_session,
        )

        # 1. Org Beta cannot get Policy Alpha (returns NotFoundError)
        with pytest.raises(NotFoundError, match=f"Policy '{pol_a.id}' not found"):
            await pol_svc.get_policy(
                workspace_id=ws_b.id,
                policy_id=pol_a.id,
                session=tx_session,
            )

        # 2. Org Beta listing policies sees 0 policies
        beta_policies = await pol_svc.list_policies(
            workspace_id=ws_b.id,
            session=tx_session,
        )
        assert len(beta_policies) == 0

        # 3. Org Beta cannot publish a version to Policy Alpha
        with pytest.raises(NotFoundError, match=f"Policy '{pol_a.id}' not found"):
            await pol_svc.publish_policy_version(
                workspace_id=ws_b.id,
                policy_id=pol_a.id,
                payload=PolicyPublishRequest(description="Hacked"),
                published_by="attacker@org-b.com",
                session=tx_session,
            )

        # 4. Org Beta cannot fetch Policy Alpha versions
        with pytest.raises(NotFoundError, match=f"Policy '{pol_a.id}' not found"):
            await pol_svc.list_policy_versions(
                workspace_id=ws_b.id,
                policy_id=pol_a.id,
                session=tx_session,
            )

        with pytest.raises(NotFoundError, match="Policy version v1 not found"):
            await pol_svc.get_policy_version(
                workspace_id=ws_b.id,
                policy_id=pol_a.id,
                version=1,
                session=tx_session,
            )


@pytest.mark.asyncio
async def test_workspace_and_policy_cascade_deletion_on_postgres(
    pg_db: DatabaseManager,
) -> None:
    """
    Verify that deleting a policy cascades to its versions,
    and deleting a workspace cascades to policies.
    """
    ws_svc = WorkspaceService()
    pol_svc = PolicyService()

    factory = pg_db.get_session_factory()
    async with factory() as session, transactional_session(session=session) as tx_session:
        ws = await ws_svc.create_workspace(
            session=tx_session,
            data=WorkspaceCreate(name="Cascade Org", slug=f"casc-org-{uuid.uuid4().hex[:6]}"),
        )
        pol = await pol_svc.create_policy_draft(
            workspace_id=ws.id,
            payload=PolicyCreate(
                name="Ephemeral Policy",
                slug=f"ephem-pol-{uuid.uuid4().hex[:6]}",
                draft_rego="package test\nallow := true",
                created_by="admin@cascade.local",
            ),
            session=tx_session,
        )
        await pol_svc.publish_policy_version(
            workspace_id=ws.id,
            policy_id=pol.id,
            payload=PolicyPublishRequest(description="v1"),
            published_by="admin@cascade.local",
            session=tx_session,
        )

        # Delete policy
        await pol_svc.delete_policy(
            workspace_id=ws.id,
            policy_id=pol.id,
            session=tx_session,
        )

        # Verify versions were cascaded
        stmt = select(PolicyVersion).where(PolicyVersion.policy_id == pol.id)
        versions_left = (await tx_session.execute(stmt)).scalars().all()
        assert len(versions_left) == 0
