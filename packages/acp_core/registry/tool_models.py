"""
Tool Catalog and Tool Snapshot domain and persistence models for Kolang (ACP-010).

Provides the domain models, persistence entities, and DTO schemas for:
1. Tool: The current definition of a discovered MCP tool from an upstream server.
2. ToolSnapshot: Historical versioned discovery output for change tracking and drift detection.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from acp_core.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, WorkspaceScopedMixin
from acp_core.registry.tool_validation import (
    compute_catalog_hash,
    compute_tool_fingerprint,
    validate_risk_labels,
    validate_tool_annotations,
    validate_tool_description,
    validate_tool_input_schema,
    validate_tool_name,
    validate_tool_title,
)


class ToolClassificationStatus(StrEnum):
    """Classification and sensitivity status of a registered tool."""

    UNCLASSIFIED = "unclassified"
    SAFE = "safe"
    SENSITIVE = "sensitive"
    RESTRICTED = "restricted"
    FORBIDDEN = "forbidden"


# ── 1. SQLAlchemy 2.0 ORM Models ─────────────────────────────────────────────


class Tool(Base, UUIDPrimaryKeyMixin, TimestampMixin, WorkspaceScopedMixin):
    """
    SQLAlchemy 2.0 relational model representing a discovered MCP Tool.

    Represents the active catalog definition of a tool exposed by an upstream
    MCP server. Scoped strictly to an organizational workspace.

    Security Notice:
    - `description` and `input_schema` are treated as UNTRUSTED upstream input.
    - `input_schema` serves solely as an invocation contract, never as proof of safe execution.
    - Name is unique per upstream server (`uq_tools_server_id_name`).
    """

    __tablename__ = "tools"
    __table_args__ = (
        UniqueConstraint("server_id", "name", name="uq_tools_server_id_name"),
        Index("ix_tools_workspace_id_name", "workspace_id", "name"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    server_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mcp_servers.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    description: Mapped[str] = mapped_column(
        String(4096),
        default="",
        server_default="",
        nullable=False,
    )
    input_schema: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
    )
    annotations: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
        default=None,
    )
    fingerprint: Mapped[str] = mapped_column(
        String(64),
        index=True,
        nullable=False,
    )
    classification_status: Mapped[str] = mapped_column(
        String(30),
        default=ToolClassificationStatus.UNCLASSIFIED.value,
        server_default=ToolClassificationStatus.UNCLASSIFIED.value,
        index=True,
        nullable=False,
    )
    risk_labels: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        server_default="[]",
        nullable=False,
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        index=True,
        nullable=False,
    )
    first_discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
    last_discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<Tool(id={self.id!s}, server_id={self.server_id!s}, "
            f"name='{self.name}', status='{self.classification_status}', "
            f"enabled={self.is_enabled})>"
        )


class ToolSnapshot(Base, UUIDPrimaryKeyMixin, TimestampMixin, WorkspaceScopedMixin):
    """
    SQLAlchemy 2.0 model representing a point-in-time discovery snapshot.

    Stores the historical state of all tools discovered from an MCP server during
    a discovery sweep. Enables change detection, drift auditing, and schema evolution.
    """

    __tablename__ = "tool_snapshots"
    __table_args__ = (Index("ix_tool_snapshots_workspace_server", "workspace_id", "server_id"),)

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    server_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mcp_servers.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    snapshot_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        index=True,
        nullable=False,
    )
    catalog_hash: Mapped[str] = mapped_column(
        String(64),
        index=True,
        nullable=False,
    )
    tools_data: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
    )
    tool_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        server_default="{}",
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<ToolSnapshot(id={self.id!s}, server_id={self.server_id!s}, "
            f"hash='{self.catalog_hash[:12]}...', tool_count={self.tool_count})>"
        )


# ── 2. Pydantic Domain & DTO Schemas ─────────────────────────────────────────


class ToolBase(BaseModel):
    """Base schema attributes for MCP Tool representations."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Tool name/identifier (unique within owning server)",
    )
    title: str | None = Field(
        default=None,
        max_length=255,
        description="Optional human-readable title",
    )
    description: str = Field(
        default="",
        max_length=4096,
        description="Untrusted description of tool capabilities",
    )
    input_schema: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON Schema contract for tool invocation arguments",
    )
    annotations: dict[str, Any] | None = Field(
        default=None,
        description="Optional tool annotations from protocol/SDK",
    )
    classification_status: ToolClassificationStatus = Field(
        default=ToolClassificationStatus.UNCLASSIFIED,
        description="Classification and sensitivity rating",
    )
    risk_labels: list[str] = Field(
        default_factory=list,
        description="Discrete set of security risk labels",
    )
    is_enabled: bool = Field(
        default=True,
        description="Whether this tool is active for execution",
    )

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        return validate_tool_name(v)

    @field_validator("title")
    @classmethod
    def _validate_title(cls, v: str | None) -> str | None:
        return validate_tool_title(v)

    @field_validator("description")
    @classmethod
    def _validate_description(cls, v: str) -> str:
        return validate_tool_description(v)

    @field_validator("input_schema")
    @classmethod
    def _validate_input_schema(cls, v: dict[str, Any]) -> dict[str, Any]:
        return validate_tool_input_schema(v)

    @field_validator("annotations")
    @classmethod
    def _validate_annotations(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        return validate_tool_annotations(v)

    @field_validator("risk_labels")
    @classmethod
    def _validate_risk_labels(cls, v: list[str]) -> list[str]:
        return validate_risk_labels(v)


class ToolCreate(ToolBase):
    """Payload for registering or persisting a discovered tool."""

    id: uuid.UUID | None = Field(
        default=None,
        description="Optional predetermined UUID for deterministic registration/testing",
    )
    workspace_id: uuid.UUID | None = Field(
        default=None,
        description="Owning workspace boundary",
    )
    server_id: uuid.UUID = Field(
        ...,
        description="ID of the upstream MCP server exposing this tool",
    )
    fingerprint: str | None = Field(
        default=None,
        max_length=64,
        description="Deterministic hash; auto-computed if omitted",
    )
    first_discovered_at: datetime | None = Field(
        default=None,
        description="Discovery timestamp",
    )
    last_discovered_at: datetime | None = Field(
        default=None,
        description="Most recent discovery timestamp",
    )

    def resolve_fingerprint(self) -> str:
        """Resolve or compute the tool fingerprint."""
        if self.fingerprint:
            return self.fingerprint
        return compute_tool_fingerprint(
            name=self.name,
            input_schema=self.input_schema,
            description=self.description,
            title=self.title,
        )


class ToolUpdate(BaseModel):
    """Payload for modifying an existing tool in the catalog."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=4096)
    input_schema: dict[str, Any] | None = None
    annotations: dict[str, Any] | None = None
    classification_status: ToolClassificationStatus | None = None
    risk_labels: list[str] | None = None
    is_enabled: bool | None = None

    @field_validator("title")
    @classmethod
    def _validate_title(cls, v: str | None) -> str | None:
        return validate_tool_title(v)

    @field_validator("description")
    @classmethod
    def _validate_description(cls, v: str | None) -> str | None:
        return validate_tool_description(v) if v is not None else None

    @field_validator("input_schema")
    @classmethod
    def _validate_input_schema(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        return validate_tool_input_schema(v) if v is not None else None

    @field_validator("annotations")
    @classmethod
    def _validate_annotations(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        return validate_tool_annotations(v) if v is not None else None

    @field_validator("risk_labels")
    @classmethod
    def _validate_risk_labels(cls, v: list[str] | None) -> list[str] | None:
        return validate_risk_labels(v) if v is not None else None


class ToolRead(BaseModel):
    """Public read model for a catalog Tool."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    server_id: uuid.UUID
    name: str
    title: str | None
    description: str
    input_schema: dict[str, Any]
    annotations: dict[str, Any] | None
    fingerprint: str
    classification_status: ToolClassificationStatus
    risk_labels: list[str]
    is_enabled: bool
    first_discovered_at: datetime
    last_discovered_at: datetime
    created_at: datetime
    updated_at: datetime


class ToolSnapshotCreate(BaseModel):
    """Payload for creating a historical tool discovery snapshot."""

    id: uuid.UUID | None = Field(
        default=None,
        description="Optional predetermined UUID for snapshot",
    )
    workspace_id: uuid.UUID | None = Field(
        default=None,
        description="Owning workspace boundary",
    )
    server_id: uuid.UUID = Field(
        ...,
        description="ID of the upstream MCP server",
    )
    tools_data: list[dict[str, Any]] = Field(
        ...,
        description="Full serialized list of tool definitions at discovery time",
    )
    catalog_hash: str | None = Field(
        default=None,
        max_length=64,
        description="Cumulative hash; auto-computed if omitted",
    )
    tool_count: int | None = Field(
        default=None,
        ge=0,
        description="Number of discovered tools; auto-counted if omitted",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Operational metadata from discovery execution",
    )

    def resolve_catalog_hash(self) -> str:
        """Resolve or compute cumulative catalog hash."""
        if self.catalog_hash:
            return self.catalog_hash
        return compute_catalog_hash(self.tools_data)

    def resolve_tool_count(self) -> int:
        """Resolve or count tools."""
        if self.tool_count is not None:
            return self.tool_count
        return len(self.tools_data)


class ToolSnapshotRead(BaseModel):
    """Public read model for a historical tool catalog snapshot."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    server_id: uuid.UUID
    snapshot_at: datetime
    catalog_hash: str
    tools_data: list[dict[str, Any]]
    tool_count: int
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_")
    created_at: datetime
    updated_at: datetime
