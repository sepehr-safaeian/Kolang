"""
Identity domain and persistence models for Kolang ACP (ACP-011).

Defines:
- Workload Agent identity model (Agent)
- MCP Client Registration model (McpClientRegistration)
- Workspace Membership model (WorkspaceMembership)
- Runtime PrincipalContext model post-token validation
- Decoded token claims (TokenClaims)
- Backwards-compatible Principal and AuthContext contracts
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import JSON, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from acp_core.common.errors import AuthorizationError
from acp_core.common.types import (
    PrincipalId,
    PrincipalKind,
    WorkspaceId,
)
from acp_core.contracts.models import Principal
from acp_core.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, WorkspaceScopedMixin

# Safe slug pattern: lowercase letters, numbers, and hyphens (cannot start or end with hyphen)
SLUG_PATTERN = re.compile(r"^[a-z0-9]([a-z0-9-]{0,98}[a-z0-9])?$")

__all__ = [
    "Agent",
    "AgentBase",
    "AgentCreate",
    "AgentRead",
    "AgentStatus",
    "AgentUpdate",
    "AuthContext",
    "ClientStatus",
    "McpClientRegistration",
    "McpClientRegistrationBase",
    "McpClientRegistrationCreate",
    "McpClientRegistrationRead",
    "McpClientRegistrationUpdate",
    "MembershipStatus",
    "Principal",
    "PrincipalContext",
    "TokenClaims",
    "WorkspaceMembership",
    "WorkspaceMembershipBase",
    "WorkspaceMembershipCreate",
    "WorkspaceMembershipRead",
    "WorkspaceMembershipUpdate",
    "WorkspaceRole",
]


# ── Lifecycle and Role Enums ─────────────────────────────────────────────────


class AgentStatus(StrEnum):
    """Operational lifecycle status of an Agent workload."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


class ClientStatus(StrEnum):
    """Operational lifecycle status of an MCP client registration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    REVOKED = "revoked"


class WorkspaceRole(StrEnum):
    """Standardized roles for human users within an organizational workspace."""

    ADMIN = "admin"
    OPERATOR = "operator"
    DEVELOPER = "developer"
    VIEWER = "viewer"


class MembershipStatus(StrEnum):
    """Operational status of a user's membership in a workspace."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    INVITED = "invited"


# ── SQLAlchemy 2.0 Relational ORM Entities ───────────────────────────────────


class Agent(Base, UUIDPrimaryKeyMixin, TimestampMixin, WorkspaceScopedMixin):
    """
    SQLAlchemy 2.0 relational model representing an Agent Workload.

    An Agent is an autonomous or semi-autonomous AI workload bounded by
    an organizational Workspace boundary. Inactive agents are forbidden
    from executing new operations.
    """

    __tablename__ = "agents"
    __table_args__ = (
        UniqueConstraint("workspace_id", "slug", name="uq_agents_workspace_id_slug"),
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
        String(30),
        default=AgentStatus.ACTIVE.value,
        server_default=AgentStatus.ACTIVE.value,
        index=True,
        nullable=False,
    )
    owner_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        default=None,
        doc="Optional human owner user ID or email responsible for this agent workload",
    )
    team: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default=None,
        doc="Optional organizational team managing this agent workload",
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        server_default="{}",
        nullable=False,
    )

    @property
    def is_active(self) -> bool:
        """Return True if agent is active and permitted to execute operations."""
        return self.status == AgentStatus.ACTIVE.value

    def __repr__(self) -> str:
        return f"<Agent(id={self.id!s}, name='{self.name}', status='{self.status}')>"


class McpClientRegistration(Base, UUIDPrimaryKeyMixin, TimestampMixin, WorkspaceScopedMixin):
    """
    SQLAlchemy 2.0 relational model representing an authorized MCP Client in IdP.

    Represents an expected OAuth2/OIDC client ID from the Identity Provider (e.g. Keycloak
    azp or client_id). Used to authenticate incoming downstream MCP tool calls, verify
    client status, and map service accounts to agent workload identities.
    """

    __tablename__ = "mcp_client_registrations"
    __table_args__ = (
        UniqueConstraint("workspace_id", "client_id", name="uq_mcp_client_workspace_client_id"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    client_id: Mapped[str] = mapped_column(
        String(128),
        index=True,
        nullable=False,
        doc="Client ID expected in OIDC claims (azp or client_id)",
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30),
        default=ClientStatus.ACTIVE.value,
        server_default=ClientStatus.ACTIVE.value,
        index=True,
        nullable=False,
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
        index=True,
        doc="Optional mapped Agent workload identity when this client represents an agent",
    )
    client_type: Mapped[str] = mapped_column(
        String(30),
        default="agent",
        server_default="agent",
        nullable=False,
        doc="Classification: agent, user_interface, or service",
    )
    description: Mapped[str] = mapped_column(
        String(512),
        default="",
        server_default="",
        nullable=False,
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        server_default="{}",
        nullable=False,
    )

    @property
    def is_active(self) -> bool:
        """Return True if client registration is active."""
        return self.status == ClientStatus.ACTIVE.value

    def __repr__(self) -> str:
        return (
            f"<McpClientRegistration(id={self.id!s}, "
            f"client_id='{self.client_id}', status='{self.status}')>"
        )


class WorkspaceMembership(Base, UUIDPrimaryKeyMixin, TimestampMixin, WorkspaceScopedMixin):
    """
    SQLAlchemy 2.0 relational model representing a User's Workspace Membership.

    Associates a human user (identified by their IdP sub claim) with an organizational
    workspace, assigning a specific role and tracking membership lifecycle status.
    """

    __tablename__ = "workspace_memberships"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_memberships_user_id"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        String(128),
        index=True,
        nullable=False,
        doc="Human user identifier from IdP sub claim",
    )
    role: Mapped[str] = mapped_column(
        String(30),
        default=WorkspaceRole.DEVELOPER.value,
        server_default=WorkspaceRole.DEVELOPER.value,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default=MembershipStatus.ACTIVE.value,
        server_default=MembershipStatus.ACTIVE.value,
        index=True,
        nullable=False,
    )
    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        default=None,
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        server_default="{}",
        nullable=False,
    )

    @property
    def is_active(self) -> bool:
        """Return True if membership is active."""
        return self.status == MembershipStatus.ACTIVE.value

    def __repr__(self) -> str:
        return (
            f"<WorkspaceMembership(workspace_id={self.workspace_id!s}, "
            f"user_id='{self.user_id}', role='{self.role}')>"
        )


# ── Pydantic DTOs & Validation Schemas ─────────────────────────────────────────


class AgentBase(BaseModel):
    """Base schema attributes for Agent workload."""

    name: str = Field(..., min_length=1, max_length=100, description="Agent display name")
    slug: str = Field(..., min_length=1, max_length=100, description="Unique slug per workspace")
    description: str = Field(default="", max_length=512, description="Agent description")
    status: AgentStatus = Field(default=AgentStatus.ACTIVE, description="Agent status")
    owner_id: str | None = Field(default=None, max_length=128, description="Owner ID / email")
    team: str | None = Field(default=None, max_length=100, description="Managing team")
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, val: str) -> str:
        cleaned = val.strip().lower()
        if not SLUG_PATTERN.match(cleaned):
            msg = (
                f"Agent slug '{val}' is invalid. "
                "Must contain lowercase letters, digits, and hyphens."
            )
            raise ValueError(msg)
        return cleaned


class AgentCreate(AgentBase):
    """Payload schema for registering a new Agent workload."""


class AgentUpdate(BaseModel):
    """Payload schema for modifying an existing Agent workload."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=512)
    status: AgentStatus | None = None
    owner_id: str | None = Field(default=None, max_length=128)
    team: str | None = Field(default=None, max_length=100)
    metadata: dict[str, Any] | None = None


class AgentRead(AgentBase):
    """Response schema representing an Agent workload."""

    id: uuid.UUID
    workspace_id: uuid.UUID
    description: str = Field(default="", max_length=512)
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _fallback_datetime_if_none(cls, v: Any) -> Any:
        return v if v is not None else datetime.now(UTC)

    @property
    def is_active(self) -> bool:
        """Return True if agent is active."""
        return self.status == AgentStatus.ACTIVE


class McpClientRegistrationBase(BaseModel):
    """Base schema attributes for MCP Client Registration."""

    client_id: str = Field(..., min_length=1, max_length=128, description="IdP client identifier")
    name: str = Field(..., min_length=1, max_length=100, description="Client display name")
    status: ClientStatus = Field(default=ClientStatus.ACTIVE, description="Client status")
    agent_id: uuid.UUID | None = Field(default=None, description="Mapped Agent workload ID")
    client_type: str = Field(
        default="agent", max_length=30, description="Type: agent, user_interface, service"
    )
    description: str = Field(default="", max_length=512)
    metadata: dict[str, Any] = Field(default_factory=dict)


class McpClientRegistrationCreate(McpClientRegistrationBase):
    """Payload schema for creating an MCP Client Registration."""


class McpClientRegistrationUpdate(BaseModel):
    """Payload schema for updating an MCP Client Registration."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    status: ClientStatus | None = None
    agent_id: uuid.UUID | None = None
    client_type: str | None = Field(default=None, max_length=30)
    description: str | None = Field(default=None, max_length=512)
    metadata: dict[str, Any] | None = None


class McpClientRegistrationRead(McpClientRegistrationBase):
    """Response schema representing an MCP Client Registration."""

    id: uuid.UUID
    workspace_id: uuid.UUID
    description: str = Field(default="", max_length=512)
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _fallback_datetime_if_none(cls, v: Any) -> Any:
        return v if v is not None else datetime.now(UTC)

    @field_validator("client_type", mode="before")
    @classmethod
    def _fallback_client_type_if_none(cls, v: Any) -> Any:
        return v if v is not None else "agent"

    @property
    def is_active(self) -> bool:
        """Return True if client is active."""
        return self.status == ClientStatus.ACTIVE


class WorkspaceMembershipBase(BaseModel):
    """Base schema attributes for Workspace Membership."""

    user_id: str = Field(..., min_length=1, max_length=128, description="User IdP sub claim")
    role: WorkspaceRole = Field(default=WorkspaceRole.DEVELOPER, description="Assigned role")
    status: MembershipStatus = Field(
        default=MembershipStatus.ACTIVE, description="Membership status"
    )
    email: str | None = Field(default=None, max_length=255, description="User email")
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkspaceMembershipCreate(WorkspaceMembershipBase):
    """Payload schema for creating a Workspace Membership."""


class WorkspaceMembershipUpdate(BaseModel):
    """Payload schema for updating a Workspace Membership."""

    role: WorkspaceRole | None = None
    status: MembershipStatus | None = None
    email: str | None = Field(default=None, max_length=255)
    metadata: dict[str, Any] | None = None


class WorkspaceMembershipRead(WorkspaceMembershipBase):
    """Response schema representing a Workspace Membership."""

    id: uuid.UUID
    workspace_id: uuid.UUID
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _fallback_datetime_if_none(cls, v: Any) -> Any:
        return v if v is not None else datetime.now(UTC)

    @property
    def is_active(self) -> bool:
        """Return True if membership is active."""
        return self.status == MembershipStatus.ACTIVE


# ── Token Claims & Runtime Security Context ───────────────────────────────────


class TokenClaims(BaseModel):
    """Decoded and validated OIDC/JWT token claims."""

    sub: str = Field(..., description="Subject identifier (user or service account)")
    iss: str = Field(..., description="Token issuer URL")
    aud: list[str] = Field(default_factory=list, description="Audience")
    exp: int = Field(..., description="Expiration timestamp (epoch seconds)")
    iat: int = Field(..., description="Issued-at timestamp (epoch seconds)")
    roles: list[str] = Field(default_factory=list, description="Realm or client roles")
    groups: list[str] = Field(default_factory=list, description="User groups")
    client_id: str | None = Field(default=None, description="Client ID claim")
    azp: str | None = Field(default=None, description="Authorized party client ID")
    scope: str | None = Field(default=None, description="Token scopes")
    email: str | None = Field(default=None, description="User email address")
    preferred_username: str | None = Field(default=None, description="Human username")
    workspace_id: str | None = Field(default=None, description="Custom workspace scope claim")

    @property
    def effective_client_id(self) -> str | None:
        """Resolve the effective client ID from azp or client_id claim."""
        return self.azp or self.client_id


class PrincipalContext(BaseModel):
    """
    Runtime security and identity context established post-token validation.

    Strictly discriminates between Human Users, Autonomous Agents, and Services.
    Guarantees that:
    1. Human User and Agent identities are distinct types.
    2. Inactive or revoked Agents/Clients cannot execute operations.
    3. Untrusted headers (such as X-Agent-ID) are never accepted as identity proof.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    principal_id: str = Field(..., description="Unique principal identifier")
    kind: PrincipalKind = Field(..., description="Identity kind: user, agent, or service")
    workspace_id: uuid.UUID = Field(..., description="Tenant workspace UUID")
    roles: list[str] = Field(default_factory=list, description="Active authorization roles")
    client_id: str | None = Field(default=None, description="Validated IdP client ID")
    user_id: str | None = Field(default=None, description="Human user ID (if user principal)")
    agent_id: uuid.UUID | None = Field(
        default=None, description="Agent workload ID (if agent principal)"
    )
    agent: AgentRead | None = Field(default=None, description="Agent workload record")
    client: McpClientRegistrationRead | None = Field(
        default=None, description="Registered client record"
    )
    membership: WorkspaceMembershipRead | None = Field(
        default=None, description="Workspace membership record"
    )
    token_claims: TokenClaims = Field(..., description="Decoded token claims")
    authenticated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    auth_method: str = "oidc"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_user(self) -> bool:
        """Return True if principal is a verified human user."""
        return self.kind == PrincipalKind.USER

    @property
    def is_agent(self) -> bool:
        """Return True if principal is an autonomous agent workload."""
        return self.kind == PrincipalKind.AGENT

    @property
    def is_service(self) -> bool:
        """Return True if principal is a background service account."""
        return self.kind == PrincipalKind.SERVICE

    def check_can_execute(self) -> None:
        """
        Enforce that the principal is active and authorized to execute new requests.

        Raises:
            AuthorizationError: If the agent, client, or membership is inactive.
        """
        # 1. Agent Status Enforcement
        if self.is_agent and self.agent is not None and not self.agent.is_active:
            msg = (
                f"Agent '{self.agent.name}' (id={self.agent.id}) has status "
                f"'{self.agent.status}' and cannot execute new requests."
            )
            raise AuthorizationError(
                msg, details={"agent_id": str(self.agent.id), "status": self.agent.status}
            )

        # 2. Client Status Enforcement
        if self.client is not None and not self.client.is_active:
            msg = (
                f"MCP Client '{self.client.client_id}' is {self.client.status} "
                "and cannot execute requests."
            )
            raise AuthorizationError(
                msg, details={"client_id": self.client.client_id, "status": self.client.status}
            )

        # 3. Workspace Membership Status Enforcement for Human Users
        if self.is_user and self.membership is not None and not self.membership.is_active:
            msg = (
                f"User membership in workspace '{self.workspace_id}' is "
                f"{self.membership.status} and cannot execute requests."
            )
            raise AuthorizationError(
                msg,
                details={"workspace_id": str(self.workspace_id), "status": self.membership.status},
            )

    def to_principal(self) -> Principal:
        """
        Convert this runtime PrincipalContext into a canonical internal Principal contract.

        Ensures full interoperability across all existing ACP components expecting Principal.
        """
        name = ""
        email = None
        if self.agent is not None:
            name = self.agent.name
        elif self.token_claims.preferred_username:
            name = self.token_claims.preferred_username
        if self.token_claims.email:
            email = self.token_claims.email

        return Principal(
            id=PrincipalId(self.principal_id),
            kind=self.kind,
            workspace_id=WorkspaceId(str(self.workspace_id)),
            roles=self.roles,
            name=name,
            email=email,
            groups=self.token_claims.groups,
            metadata=dict(self.metadata),
        )


class AuthContext(BaseModel):
    """Full authentication context for a request (backwards-compatible)."""

    principal: Principal
    token_claims: TokenClaims
    authenticated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    auth_method: str = "oidc"
