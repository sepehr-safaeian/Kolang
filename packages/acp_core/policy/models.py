"""
Policy domain and persistence models for Kolang (ACP-012).

IMPORTANT: These models define both:
1. Purely internal access control vocabulary (PolicyRule, PolicyCondition, PolicyDecision),
   having NO dependency on JSON-RPC, MCP wire format, or transport protocols.
2. Relational persistence models (Policy, PolicyVersion) establishing versioned,
   immutable, and workspace-scoped authorization policies with audit checksums.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.orm.attributes import get_history

from acp_core.common.errors import PolicyVersionImmutableError
from acp_core.common.types import DecisionEffect, PolicyId, PrincipalKind, WorkspaceId
from acp_core.contracts.models import (
    PolicyDecision,
    PolicyInput,
    PolicyObligation,
)
from acp_core.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, WorkspaceScopedMixin

# Safe slug pattern: lowercase letters, numbers, and hyphens (cannot start or end with hyphen)
SLUG_PATTERN = re.compile(r"^[a-z0-9]([a-z0-9-]{0,98}[a-z0-9])?$")


class PolicyEffect(StrEnum):
    """The effect of a policy evaluation."""

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    CONDITIONAL = "conditional"  # Requires approval or additional verification


class PolicyStatus(StrEnum):
    """Operational lifecycle status of an access control policy."""

    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class PolicyVersionStatus(StrEnum):
    """Lifecycle status of a published policy version."""

    PUBLISHED = "published"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


def compute_policy_checksum(rego_source: str, bundle_reference: str | None = None) -> str:
    """
    Compute deterministic SHA-256 checksum for policy code and bundle reference.

    Used for auditability, tamper detection, and drift tracking across published versions.
    """
    hasher = hashlib.sha256()
    hasher.update(rego_source.encode("utf-8"))
    if bundle_reference:
        hasher.update(b"\x00")
        hasher.update(bundle_reference.encode("utf-8"))
    return hasher.hexdigest()


def create_decision_for_version(
    policy_id: uuid.UUID | str,
    version: int | str,
    decision: DecisionEffect,
    reason_code: str,
    reason_message: str = "",
    obligations: list[PolicyObligation] | None = None,
) -> PolicyDecision:
    """
    Construct a PolicyDecision recording the exact policy ID and version.

    Enforces ACP-012 Rule 2: Every decision must capture the precise policy version
    evaluated by the gateway Policy Decision Point (PDP).
    """
    return PolicyDecision(
        decision=decision,
        reason_code=reason_code,
        reason_message=reason_message,
        policy_id=PolicyId(str(policy_id)),
        version=str(version),
        obligations=obligations or [],
    )


# ── SQLAlchemy 2.0 ORM Models ─────────────────────────────────────────────────


class Policy(Base, UUIDPrimaryKeyMixin, TimestampMixin, WorkspaceScopedMixin):
    """
    SQLAlchemy 2.0 relational model representing an Access Control Policy (ACP-012).

    Represents a managed authorization policy scoped strictly to an organizational
    workspace boundary. Draft authoring is explicitly segregated from published versions.
    """

    __tablename__ = "policies"
    __table_args__ = (
        UniqueConstraint("workspace_id", "slug", name="uq_policies_workspace_id_slug"),
        Index("ix_policies_workspace_id_status", "workspace_id", "status"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    description: Mapped[str] = mapped_column(
        String(512),
        default="",
        server_default="",
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=PolicyStatus.DRAFT.value,
        server_default=PolicyStatus.DRAFT.value,
        index=True,
        nullable=False,
    )
    draft_rego: Mapped[str] = mapped_column(
        Text,
        default="",
        server_default="",
        nullable=False,
    )
    draft_bundle_reference: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        default=None,
    )
    active_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "policy_versions.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_policies_active_version_id_policy_versions",
        ),
        nullable=True,
        default=None,
        index=True,
    )
    active_version_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        default=None,
    )
    created_by: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    updated_by: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        default=None,
    )

    # Relationships
    versions: Mapped[list[PolicyVersion]] = relationship(
        "PolicyVersion",
        back_populates="policy",
        cascade="all, delete-orphan",
        order_by="PolicyVersion.version.asc()",
        foreign_keys="PolicyVersion.policy_id",
        lazy="selectin",
    )
    active_version: Mapped[PolicyVersion | None] = relationship(
        "PolicyVersion",
        foreign_keys=[active_version_id],
        lazy="selectin",
        post_update=True,
    )

    @property
    def is_draft(self) -> bool:
        """Return True if the policy is currently in draft status."""
        return self.status == PolicyStatus.DRAFT.value

    @property
    def is_active(self) -> bool:
        """
        Return True if policy is published active and has an active published version.

        Enforces ACP-012 Rule 3: Policy Drafts must not be applied to the Gateway.
        """
        return self.status == PolicyStatus.ACTIVE.value and self.active_version_id is not None

    def __repr__(self) -> str:
        return (
            f"<Policy(id={self.id!s}, slug='{self.slug}', status='{self.status}', "
            f"active_v={self.active_version_number})>"
        )


class PolicyVersion(Base, UUIDPrimaryKeyMixin, WorkspaceScopedMixin):
    """
    SQLAlchemy 2.0 relational model representing an immutable published Policy Version.

    Stores the historical, point-in-time Rego authorization code and SHA-256 checksum.
    Published versions are strictly immutable; edits must generate a new version.
    """

    __tablename__ = "policy_versions"
    __table_args__ = (
        UniqueConstraint("policy_id", "version", name="uq_policy_versions_policy_id_version"),
        Index("ix_policy_versions_workspace_policy", "workspace_id", "policy_id"),
    )

    policy_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("policies.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    rego_source: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    bundle_reference: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        default=None,
    )
    checksum: Mapped[str] = mapped_column(
        String(64),
        index=True,
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        String(512),
        default="",
        server_default="",
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=PolicyVersionStatus.PUBLISHED.value,
        server_default=PolicyVersionStatus.PUBLISHED.value,
        index=True,
        nullable=False,
    )
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
    published_by: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    policy: Mapped[Policy] = relationship(
        "Policy",
        back_populates="versions",
        foreign_keys=[policy_id],
    )

    @property
    def is_published(self) -> bool:
        """Return True if this version is actively published."""
        return self.status == PolicyVersionStatus.PUBLISHED.value

    def __repr__(self) -> str:
        return (
            f"<PolicyVersion(id={self.id!s}, policy_id={self.policy_id!s}, "
            f"v={self.version}, checksum='{self.checksum[:8]}...', status='{self.status}')>"
        )


@event.listens_for(PolicyVersion, "before_update")
def _prevent_policy_version_mutation(mapper: Any, connection: Any, target: PolicyVersion) -> None:
    """
    Enforce ACP-012 Rule 1: Published policy versions are strictly immutable.

    Any attempt to modify the Rego source, bundle reference, checksum,
    version number, or publishing metadata raises PolicyVersionImmutableError.
    """
    immutable_fields = (
        "rego_source",
        "bundle_reference",
        "checksum",
        "version",
        "policy_id",
        "workspace_id",
        "published_at",
        "published_by",
    )
    for field in immutable_fields:
        history = get_history(target, field)
        if history.has_changes():
            raise PolicyVersionImmutableError(
                f"PolicyVersion '{target.id}' (v{target.version}) is immutable: "
                f"modification of '{field}' is forbidden. Edits must produce a new version."
            )


# ── Pydantic Domain & DTO Models ─────────────────────────────────────────────


class PolicyBase(BaseModel):
    """Base attributes common to all policy representations."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Human-readable policy name",
    )
    slug: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Product-unique URL-friendly slug",
    )
    description: str = Field(
        default="",
        max_length=512,
        description="Brief policy description",
    )

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if not SLUG_PATTERN.match(cleaned):
            msg = (
                f"Invalid slug format: '{v}'. Must be 1-100 characters containing only lowercase "
                "letters, digits, and non-consecutive hyphens, without leading/trailing hyphens."
            )
            raise ValueError(msg)
        return cleaned

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            msg = "Policy name cannot be empty or whitespace only."
            raise ValueError(msg)
        return cleaned


class PolicyCreate(PolicyBase):
    """Payload for creating a new policy draft."""

    id: uuid.UUID | None = Field(
        default=None,
        description="Optional predetermined UUID",
    )
    draft_rego: str = Field(
        default="",
        description="Initial Rego source code in draft state",
    )
    draft_bundle_reference: str | None = Field(
        default=None,
        max_length=255,
        description="Optional bundle reference for draft",
    )
    created_by: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Principal ID authoring the policy draft",
    )


class PolicyDraftUpdate(BaseModel):
    """Payload for updating an existing policy draft without altering published versions."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=512)
    draft_rego: str | None = None
    draft_bundle_reference: str | None = Field(default=None, max_length=255)
    updated_by: str | None = Field(default=None, max_length=128)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        cleaned = v.strip()
        if not cleaned:
            msg = "Policy name cannot be empty or whitespace only."
            raise ValueError(msg)
        return cleaned


class PolicyRead(BaseModel):
    """Public representation of an Access Control Policy."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    slug: str
    description: str
    status: PolicyStatus
    draft_rego: str
    draft_bundle_reference: str | None
    active_version_id: uuid.UUID | None
    active_version_number: int | None
    created_by: str
    updated_by: str | None
    created_at: datetime
    updated_at: datetime

    @property
    def is_draft(self) -> bool:
        return self.status == PolicyStatus.DRAFT

    @property
    def is_active(self) -> bool:
        return self.status == PolicyStatus.ACTIVE and self.active_version_id is not None


class PolicyVersionCreate(BaseModel):
    """Payload for publishing a version directly."""

    rego_source: str = Field(..., min_length=1, description="Immutable Rego policy code")
    bundle_reference: str | None = Field(default=None, max_length=255)
    description: str = Field(default="", max_length=512, description="Version changelog notes")


class PolicyPublishRequest(BaseModel):
    """Request payload to publish a new policy version from draft or explicit code."""

    rego_source: str | None = Field(
        default=None,
        description="Explicit Rego source to publish. If omitted, publishes current draft_rego.",
    )
    bundle_reference: str | None = Field(
        default=None,
        max_length=255,
        description="Optional bundle reference to publish.",
    )
    description: str = Field(
        default="",
        max_length=512,
        description="Changelog for this published version",
    )


class PolicyVersionRead(BaseModel):
    """Public representation of an immutable published policy version."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    policy_id: uuid.UUID
    workspace_id: uuid.UUID
    version: int
    rego_source: str
    bundle_reference: str | None
    checksum: str
    description: str
    status: PolicyVersionStatus
    published_at: datetime
    published_by: str
    created_at: datetime


# ── Internal Access Control Vocabulary (Decoupled from Transport) ─────────────


class PolicyCondition(BaseModel):
    """A condition attached to a CONDITIONAL policy decision."""

    type: str = Field(description="Condition type, e.g. 'approval', 'mfa', 'time_window'")
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Condition parameters, e.g. {'approvers': ['admin']}",
    )


class PolicyRule(BaseModel):
    """A declarative access control rule."""

    id: PolicyId
    workspace_id: WorkspaceId = Field(default=WorkspaceId("default"))
    name: str
    description: str = ""
    effect: PolicyEffect
    principals: list[str] = Field(
        default_factory=list,
        description="Principal patterns (glob), e.g. ['user:*', 'agent:builder-*']",
    )
    servers: list[str] = Field(
        default_factory=list,
        description="Server ID patterns (glob), e.g. ['prod-*']",
    )
    tools: list[str] = Field(
        default_factory=list,
        description="Tool name patterns (glob), e.g. ['read_*', 'query']",
    )
    conditions: list[PolicyCondition] = Field(default_factory=list)
    priority: int = Field(default=0, description="Higher priority rules are evaluated first")
    enabled: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PolicyEvaluationInput(BaseModel):
    """Input data sent to the policy engine for evaluation."""

    principal_id: str
    principal_kind: PrincipalKind
    principal_roles: list[str] = Field(default_factory=list)
    principal_groups: list[str] = Field(default_factory=list)
    server_id: str
    tool_name: str
    arguments_hash: str = Field(
        default="",
        description="SHA-256 hash of the tool arguments (for audit, not content)",
    )
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    request_metadata: dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "Policy",
    "PolicyBase",
    "PolicyCondition",
    "PolicyCreate",
    "PolicyDecision",
    "PolicyDraftUpdate",
    "PolicyEffect",
    "PolicyEvaluationInput",
    "PolicyInput",
    "PolicyObligation",
    "PolicyPublishRequest",
    "PolicyRead",
    "PolicyRule",
    "PolicyStatus",
    "PolicyVersion",
    "PolicyVersionCreate",
    "PolicyVersionRead",
    "PolicyVersionStatus",
    "compute_policy_checksum",
    "create_decision_for_version",
]
