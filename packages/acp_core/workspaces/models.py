"""
Workspace domain and persistence models for Kolang.

Provides the primary organizational boundary for multi-tenancy, data isolation,
and policy enforcement across all Agent Control Plane capabilities.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from acp_core.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

# Safe slug pattern: lowercase letters, numbers, and hyphens (cannot start or end with hyphen)
SLUG_PATTERN = re.compile(r"^[a-z0-9]([a-z0-9-]{0,98}[a-z0-9])?$")


class WorkspaceStatus(StrEnum):
    """Operational lifecycle status of an organizational workspace."""

    ACTIVE = "active"
    DISABLED = "disabled"
    SUSPENDED = "suspended"


# ── SQLAlchemy 2.0 ORM Model ─────────────────────────────────────────────────


class Workspace(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    SQLAlchemy 2.0 relational model representing an organizational Workspace.

    Acts as the root tenancy boundary. All child resources (servers, tools,
    agents, policies, approvals, credentials, audit events) must be associated
    with a workspace to ensure complete tenant data isolation.
    """

    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        default=WorkspaceStatus.ACTIVE.value,
        server_default=WorkspaceStatus.ACTIVE.value,
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        String(255),
        default="",
        server_default="",
        nullable=False,
    )

    @property
    def is_active(self) -> bool:
        """Return True if workspace is active and able to execute operations."""
        return self.status == WorkspaceStatus.ACTIVE.value

    def __repr__(self) -> str:
        return f"<Workspace(id={self.id!s}, slug='{self.slug}', status='{self.status}')>"


# ── Pydantic Domain & DTO Models ─────────────────────────────────────────────


class WorkspaceBase(BaseModel):
    """Base attributes common to all workspace representations."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Human-readable workspace name",
    )
    slug: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Product-unique URL-friendly slug",
    )
    status: WorkspaceStatus = Field(
        default=WorkspaceStatus.ACTIVE,
        description="Workspace lifecycle status",
    )
    description: str = Field(
        default="",
        max_length=255,
        description="Brief workspace description",
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
            msg = "Workspace name cannot be empty or whitespace only."
            raise ValueError(msg)
        return cleaned


class WorkspaceCreate(WorkspaceBase):
    """Payload for creating a new workspace."""

    id: uuid.UUID | None = Field(
        default=None,
        description="Optional predetermined UUID (e.g. for deterministic demo seed)",
    )


class WorkspaceUpdate(BaseModel):
    """Payload for updating an existing workspace."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=100)
    status: WorkspaceStatus | None = None
    description: str | None = Field(default=None, max_length=255)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        cleaned = v.strip()
        if not cleaned:
            msg = "Workspace name cannot be empty or whitespace only."
            raise ValueError(msg)
        return cleaned


class WorkspaceRead(BaseModel):
    """Public representation of an organizational workspace."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    status: WorkspaceStatus
    description: str
    created_at: datetime
    updated_at: datetime
