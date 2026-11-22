"""
Domain Service Layer for MCP Server Registration and Management (ACP-009).

Enforces:
1. Workspace-scoped data isolation (servers cannot be accessed across workspaces).
2. Protection against IDOR and cross-tenant enumeration.
3. Slug uniqueness per workspace.
4. SSRF and endpoint URL validation during creation and modification.
5. Structured audit and operational logging with sanitized URLs.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from acp_core.common.errors import ConflictError, NotFoundError, ValidationError
from acp_core.registry.models import (
    McpServer,
    McpServerCreate,
    McpServerStatus,
    McpServerUpdate,
)
from acp_core.registry.validation import sanitize_endpoint_url, validate_mcp_endpoint_url

logger = structlog.get_logger(__name__)


class McpServerService:
    """
    Workspace-scoped domain service for managing Upstream MCP Server entities.

    Guarantees strict multi-tenant boundary isolation: callers can only access,
    mutate, or list servers belonging to their authorized workspace.
    """

    async def create_server(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        data: McpServerCreate,
    ) -> McpServer:
        """
        Register a new Upstream MCP Server scoped to a workspace.

        Args:
            session: Active database session.
            workspace_id: Verified workspace boundary.
            data: Registration payload.

        Returns:
            Newly created McpServer entity.

        Raises:
            ValidationError: If workspace_id in payload mismatches or URL is invalid.
            ConflictError: If a server with the same slug already exists in this workspace.
        """
        # Enforce payload workspace consistency
        if data.workspace_id is not None and data.workspace_id != workspace_id:
            logger.warning(
                "security.workspace_spoofing_attempt",
                caller_workspace=str(workspace_id),
                payload_workspace=str(data.workspace_id),
            )
            raise ValidationError(
                f"Payload workspace_id '{data.workspace_id}' does not match "
                f"target workspace '{workspace_id}'."
            )

        # Enforce slug uniqueness within workspace
        existing = await self.get_server_by_slug(
            session=session, workspace_id=workspace_id, slug=data.slug
        )
        if existing is not None:
            raise ConflictError(
                f"MCP Server with slug '{data.slug}' already exists in workspace '{workspace_id}'."
            )

        # Validate endpoint URL with SSRF guardrails
        validated_url = validate_mcp_endpoint_url(data.endpoint_url)

        server = McpServer(
            id=data.id or uuid.uuid4(),
            workspace_id=workspace_id,
            name=data.name,
            slug=data.slug,
            endpoint_url=validated_url,
            transport=data.transport.value,
            status=data.status.value,
            auth_profile_id=data.auth_profile_id,
            description=data.description,
            metadata_=data.metadata,
        )

        session.add(server)
        await session.flush()

        logger.info(
            "mcp_server.created",
            workspace_id=str(workspace_id),
            server_id=str(server.id),
            slug=server.slug,
            transport=server.transport,
            endpoint=sanitize_endpoint_url(server.endpoint_url),
        )
        return server

    async def get_server(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        server_id: uuid.UUID,
    ) -> McpServer | None:
        """
        Retrieve an MCP server by ID scoped strictly to workspace_id.

        Returns None if not found or if the server belongs to another workspace.
        """
        stmt = select(McpServer).where(
            McpServer.workspace_id == workspace_id,
            McpServer.id == server_id,
        )
        result = await session.execute(stmt)
        server = result.scalar_one_or_none()

        if server is None:
            # Check if server exists in another workspace to log security event
            check_other = select(McpServer.workspace_id).where(McpServer.id == server_id)
            res_other = await session.execute(check_other)
            other_ws = res_other.scalar_one_or_none()
            if other_ws is not None:
                logger.warning(
                    "security.idor_server_blocked",
                    caller_workspace=str(workspace_id),
                    target_workspace=str(other_ws),
                    server_id=str(server_id),
                )
        return server

    async def get_server_or_raise(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        server_id: uuid.UUID,
    ) -> McpServer:
        """
        Retrieve an MCP server by ID or raise NotFoundError.

        Guarantees that requesting a server from another workspace returns 404
        without leaking its existence.
        """
        server = await self.get_server(
            session=session, workspace_id=workspace_id, server_id=server_id
        )
        if server is None:
            raise NotFoundError(
                f"MCP Server '{server_id}' not found in workspace '{workspace_id}'."
            )
        return server

    async def get_server_by_slug(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        slug: str,
    ) -> McpServer | None:
        """Retrieve an MCP server by slug within a specific workspace."""
        cleaned_slug = slug.strip().lower()
        stmt = select(McpServer).where(
            McpServer.workspace_id == workspace_id,
            McpServer.slug == cleaned_slug,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_servers(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        status: McpServerStatus | None = None,
    ) -> Sequence[McpServer]:
        """
        List all MCP servers belonging to a workspace, optionally filtered by status.
        """
        stmt = select(McpServer).where(McpServer.workspace_id == workspace_id)
        if status is not None:
            stmt = stmt.where(McpServer.status == status.value)
        stmt = stmt.order_by(McpServer.created_at.desc())

        result = await session.execute(stmt)
        return result.scalars().all()

    async def update_server(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        server_id: uuid.UUID,
        data: McpServerUpdate,
    ) -> McpServer:
        """
        Update mutable fields of an existing MCP server within workspace scope.

        Raises NotFoundError if server does not exist in the caller's workspace.
        """
        server = await self.get_server_or_raise(
            session=session,
            workspace_id=workspace_id,
            server_id=server_id,
        )

        if data.name is not None:
            server.name = data.name
        if data.endpoint_url is not None:
            validated_url = validate_mcp_endpoint_url(data.endpoint_url)
            server.endpoint_url = validated_url
        if data.transport is not None:
            server.transport = data.transport.value
        if data.status is not None:
            server.status = data.status.value
        if data.auth_profile_id is not None:
            server.auth_profile_id = data.auth_profile_id
        if data.description is not None:
            server.description = data.description
        if data.metadata is not None:
            server.metadata_ = data.metadata

        await session.flush()
        logger.info(
            "mcp_server.updated",
            workspace_id=str(workspace_id),
            server_id=str(server.id),
            status=server.status,
            endpoint=sanitize_endpoint_url(server.endpoint_url),
        )
        return server

    async def delete_server(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        server_id: uuid.UUID,
    ) -> None:
        """
        Delete an MCP server entity within workspace scope.

        Raises NotFoundError if server does not exist in the caller's workspace.
        """
        server = await self.get_server_or_raise(
            session=session,
            workspace_id=workspace_id,
            server_id=server_id,
        )
        await session.delete(server)
        await session.flush()
        logger.info(
            "mcp_server.deleted",
            workspace_id=str(workspace_id),
            server_id=str(server_id),
        )
