"""
Workspace Service Layer for Kolang.

Provides business logic and lifecycle operations for organizational workspaces,
including creation, lookup, status updates, and tenant boundary verification.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from acp_core.common.errors import ConflictError, NotFoundError
from acp_core.workspaces.models import (
    Workspace,
    WorkspaceCreate,
    WorkspaceStatus,
    WorkspaceUpdate,
)

logger = structlog.get_logger(__name__)


class WorkspaceService:
    """Service handling workspace domain operations and persistence."""

    async def create_workspace(
        self,
        session: AsyncSession,
        data: WorkspaceCreate,
    ) -> Workspace:
        """
        Create a new organizational workspace.

        Args:
            session: Active database session.
            data: Validated workspace creation payload.

        Returns:
            Newly created Workspace entity.

        Raises:
            ConflictError: If slug is already claimed by another workspace.
        """
        # Slug uniqueness check
        existing = await self.get_by_slug(session, data.slug)
        if existing is not None:
            logger.warning("workspace.slug_conflict", slug=data.slug)
            raise ConflictError(f"A workspace with slug '{data.slug}' already exists.")

        workspace = Workspace(
            id=data.id or uuid.uuid4(),
            name=data.name,
            slug=data.slug,
            status=data.status.value,
            description=data.description,
        )
        session.add(workspace)
        await session.flush()

        logger.info(
            "workspace.created",
            workspace_id=str(workspace.id),
            slug=workspace.slug,
            name=workspace.name,
        )
        return workspace

    async def get_workspace(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
    ) -> Workspace | None:
        """Look up a workspace by its unique UUID."""
        result = await session.execute(select(Workspace).where(Workspace.id == workspace_id))
        return result.scalar_one_or_none()

    async def get_workspace_or_raise(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
    ) -> Workspace:
        """Look up a workspace by its UUID or raise NotFoundError."""
        workspace = await self.get_workspace(session, workspace_id)
        if workspace is None:
            raise NotFoundError(f"Workspace with ID '{workspace_id}' not found.")
        return workspace

    async def get_by_slug(
        self,
        session: AsyncSession,
        slug: str,
    ) -> Workspace | None:
        """Look up a workspace by its unique slug."""
        result = await session.execute(
            select(Workspace).where(Workspace.slug == slug.strip().lower())
        )
        return result.scalar_one_or_none()

    async def list_workspaces(
        self,
        session: AsyncSession,
        status: WorkspaceStatus | None = None,
    ) -> Sequence[Workspace]:
        """List workspaces, optionally filtered by operational status."""
        query = select(Workspace).order_by(Workspace.created_at.asc())
        if status is not None:
            query = query.where(Workspace.status == status.value)
        result = await session.execute(query)
        return result.scalars().all()

    async def update_workspace(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        data: WorkspaceUpdate,
    ) -> Workspace:
        """Update mutable fields of a workspace."""
        workspace = await self.get_workspace_or_raise(session, workspace_id)

        if data.name is not None:
            workspace.name = data.name
        if data.status is not None:
            workspace.status = data.status.value
        if data.description is not None:
            workspace.description = data.description

        await session.flush()
        logger.info(
            "workspace.updated",
            workspace_id=str(workspace.id),
            status=workspace.status,
        )
        return workspace

    async def disable_workspace(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
    ) -> Workspace:
        """Disable a workspace, preventing agents and users from executing requests."""
        return await self.update_workspace(
            session=session,
            workspace_id=workspace_id,
            data=WorkspaceUpdate(status=WorkspaceStatus.DISABLED),
        )
