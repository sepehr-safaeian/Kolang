"""
MCP Server domain and persistence models for Kolang ACP (ACP-009).

Provides the domain model, persistence entity, and DTO schemas for registering,
managing, and monitoring Upstream MCP Servers within organizational workspaces.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from acp_core.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, WorkspaceScopedMixin
from acp_core.registry.validation import validate_mcp_endpoint_url

# Safe slug pattern: lowercase letters, numbers, and hyphens (cannot start or end with hyphen)
SLUG_PATTERN = re.compile(r"^[a-z0-9]([a-z0-9-]{0,98}[a-z0-9])?$")


class McpServerTransport(StrEnum):
    """Supported MCP upstream server transport types."""

    STREAMABLE_HTTP = "streamable_http"
    SSE = "sse"
    STDIO = "stdio"


class McpServerStatus(StrEnum):
    """Operational lifecycle and connectivity status of an upstream MCP server."""

    PENDING = "pending"
    CONNECTED = "connected"
    UNAVAILABLE = "unavailable"
    ERROR = "error"
    DISABLED = "disabled"


# ── SQLAlchemy 2.0 ORM Model ─────────────────────────────────────────────────


class McpServer(Base, UUIDPrimaryKeyMixin, TimestampMixin, WorkspaceScopedMixin):
    """
    SQLAlchemy 2.0 relational model representing an Upstream MCP Server.

    Represents a remote or local Model Context Protocol tool provider scoped
    strictly to an organizational Workspace boundary.
    """

    __tablename__ = "mcp_servers"
    __table_args__ = (
        UniqueConstraint("workspace_id", "slug", name="uq_mcp_servers_workspace_id_slug"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    endpoint_url: Mapped[str] = mapped_column(String(512), nullable=False)
    transport: Mapped[str] = mapped_column(
        String(30),
        default=McpServerTransport.STREAMABLE_HTTP.value,
        server_default=McpServerTransport.STREAMABLE_HTTP.value,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default=McpServerStatus.PENDING.value,
        server_default=McpServerStatus.PENDING.value,
        index=True,
        nullable=False,
    )
    auth_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        nullable=True,
        default=None,
    )
    last_discovered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    last_health_check_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    description: Mapped[str] = mapped_column(
        String(255),
        default="",
        server_default="",
        nullable=False,
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        default=dict,
        server_default="{}",
        nullable=False,
    )

    @property
    def is_connected(self) -> bool:
        """Return True if server is in CONNECTED operational status."""
        return self.status == McpServerStatus.CONNECTED.value

    @property
    def is_enabled(self) -> bool:
        """Return True if server is not in DISABLED status."""
        return self.status != McpServerStatus.DISABLED.value

    def __repr__(self) -> str:
        return (
            f"<McpServer(id={self.id!s}, workspace_id={self.workspace_id!s}, "
            f"slug='{self.slug}', transport='{self.transport}', status='{self.status}')>"
        )


# ── Pydantic Domain & DTO Models ─────────────────────────────────────────────


class McpServerBase(BaseModel):
    """Base schema attributes for MCP Server representations."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Human-readable server name",
    )
    slug: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Workspace-unique URL-friendly slug",
    )
    endpoint_url: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="Validated Upstream MCP Server endpoint URL",
    )
    transport: McpServerTransport = Field(
        default=McpServerTransport.STREAMABLE_HTTP,
        description="MCP wire transport (default Streamable HTTP)",
    )
    status: McpServerStatus = Field(
        default=McpServerStatus.PENDING,
        description="Server connectivity and operational status",
    )
    auth_profile_id: uuid.UUID | None = Field(
        default=None,
        description="Optional ID of associated credential auth profile",
    )
    description: str = Field(
        default="",
        max_length=255,
        description="Brief description of server tools and purpose",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom server metadata and capabilities",
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
            msg = "Server name cannot be empty or whitespace only."
            raise ValueError(msg)
        return cleaned

    @field_validator("endpoint_url")
    @classmethod
    def validate_endpoint_url(cls, v: str) -> str:
        return validate_mcp_endpoint_url(v)


class McpServerCreate(McpServerBase):
    """Payload for registering a new Upstream MCP Server."""

    id: uuid.UUID | None = Field(
        default=None,
        description="Optional predetermined UUID for deterministic registration/testing",
    )
    workspace_id: uuid.UUID | None = Field(
        default=None,
        description="Target workspace ID (must match verified TenantContext)",
    )


class McpServerUpdate(BaseModel):
    """Payload for updating mutable attributes of an existing MCP Server."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=100)
    endpoint_url: str | None = Field(default=None, min_length=1, max_length=512)
    transport: McpServerTransport | None = None
    status: McpServerStatus | None = None
    auth_profile_id: uuid.UUID | None = None
    description: str | None = Field(default=None, max_length=255)
    metadata: dict[str, Any] | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        cleaned = v.strip()
        if not cleaned:
            msg = "Server name cannot be empty or whitespace only."
            raise ValueError(msg)
        return cleaned

    @field_validator("endpoint_url")
    @classmethod
    def validate_endpoint_url(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return validate_mcp_endpoint_url(v)


class McpServerRead(BaseModel):
    """Public read model for an Upstream MCP Server."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    slug: str
    endpoint_url: str
    transport: McpServerTransport
    status: McpServerStatus
    auth_profile_id: uuid.UUID | None
    last_discovered_at: datetime | None
    last_health_check_at: datetime | None
    description: str
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_")
    created_at: datetime
    updated_at: datetime
