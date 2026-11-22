"""
Domain Service Layer for Tool Catalog and Snapshot Management (ACP-010).

Enforces:
1. Workspace-scoped multi-tenant data isolation (tools and snapshots strictly segregated).
2. Anti-IDOR protection against cross-workspace enumeration and tampering.
3. Server ownership verification: tools can only be registered to servers in the same workspace.
4. Tool name uniqueness per server (`uq_tools_server_id_name`).
5. Untrusted input handling and deterministic fingerprinting.
6. Structured audit and operational logging.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from acp_core.common.errors import ConflictError, NotFoundError, ValidationError
from acp_core.registry.models import McpServer
from acp_core.registry.tool_models import (
    Tool,
    ToolCreate,
    ToolSnapshot,
    ToolSnapshotCreate,
    ToolUpdate,
)

logger = structlog.get_logger(__name__)


class ToolService:
    """
    Domain service for managing Tool Catalog and Tool Snapshot entities.

    Guarantees strict organizational workspace boundaries: callers can only create,
    read, update, or delete tools and discovery snapshots within their verified workspace.
    """

    async def _verify_server_in_workspace(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        server_id: uuid.UUID,
    ) -> McpServer:
        """
        Verify that the referenced MCP Server exists and belongs to the workspace.

        Args:
            session: Active database session.
            workspace_id: Caller's verified workspace.
            server_id: Target MCP server ID.

        Returns:
            The verified McpServer instance.

        Raises:
            NotFoundError: If server does not exist or belongs to another workspace.
        """
        stmt = select(McpServer).where(
            McpServer.id == server_id,
            McpServer.workspace_id == workspace_id,
        )
        result = await session.execute(stmt)
        server = result.scalar_one_or_none()
        if server is None:
            logger.warning(
                "security.cross_workspace_server_access_blocked",
                caller_workspace=str(workspace_id),
                server_id=str(server_id),
            )
            raise NotFoundError(
                f"MCP Server '{server_id}' not found in workspace '{workspace_id}'."
            )
        return server

    # ── Tool Operations ───────────────────────────────────────────────────────

    async def create_tool(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        data: ToolCreate,
    ) -> Tool:
        """
        Register a new discovered Tool in the workspace catalog.

        Args:
            session: Active database session.
            workspace_id: Verified workspace boundary.
            data: Tool registration payload.

        Returns:
            Newly created Tool entity.

        Raises:
            ValidationError: If payload workspace_id mismatches caller's workspace.
            NotFoundError: If referenced server does not belong to the workspace.
            ConflictError: If a tool with the same name already exists on this server.
        """
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

        # Verify server belongs to this workspace
        await self._verify_server_in_workspace(
            session=session,
            workspace_id=workspace_id,
            server_id=data.server_id,
        )

        # Enforce name uniqueness per server
        existing = await self.get_tool_by_server_and_name(
            session=session,
            workspace_id=workspace_id,
            server_id=data.server_id,
            name=data.name,
        )
        if existing is not None:
            raise ConflictError(
                f"Tool with name '{data.name}' already exists on server '{data.server_id}'."
            )

        fingerprint = data.resolve_fingerprint()
        now = datetime.now(UTC)

        tool = Tool(
            id=data.id or uuid.uuid4(),
            workspace_id=workspace_id,
            server_id=data.server_id,
            name=data.name,
            title=data.title,
            description=data.description,
            input_schema=data.input_schema,
            annotations=data.annotations,
            fingerprint=fingerprint,
            classification_status=data.classification_status.value,
            risk_labels=data.risk_labels,
            is_enabled=data.is_enabled,
            first_discovered_at=data.first_discovered_at or now,
            last_discovered_at=data.last_discovered_at or now,
        )

        session.add(tool)
        await session.flush()

        logger.info(
            "registry.tool_created",
            tool_id=str(tool.id),
            workspace_id=str(workspace_id),
            server_id=str(data.server_id),
            tool_name=tool.name,
            fingerprint=fingerprint[:12],
        )
        return tool

    async def get_tool(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        tool_id: uuid.UUID,
    ) -> Tool | None:
        """
        Retrieve a Tool by ID, strictly scoped to the authorized workspace.

        Args:
            session: Active database session.
            workspace_id: Authorized workspace ID.
            tool_id: Primary key of the tool.

        Returns:
            Tool if found and owned by workspace, else None.
        """
        stmt = select(Tool).where(
            Tool.id == tool_id,
            Tool.workspace_id == workspace_id,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_tool_by_server_and_name(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        server_id: uuid.UUID,
        name: str,
    ) -> Tool | None:
        """
        Retrieve a Tool by server ID and name within a workspace.

        Args:
            session: Active database session.
            workspace_id: Authorized workspace ID.
            server_id: Owning MCP server ID.
            name: Tool name.

        Returns:
            Tool if found, else None.
        """
        stmt = select(Tool).where(
            Tool.workspace_id == workspace_id,
            Tool.server_id == server_id,
            Tool.name == name,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_tools_for_server(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        server_id: uuid.UUID,
    ) -> Sequence[Tool]:
        """
        List all tools associated with an MCP server in a workspace.

        Args:
            session: Active database session.
            workspace_id: Authorized workspace boundary.
            server_id: Target MCP server ID.

        Returns:
            Sequence of Tool instances.
        """
        stmt = (
            select(Tool)
            .where(
                Tool.workspace_id == workspace_id,
                Tool.server_id == server_id,
            )
            .order_by(Tool.name.asc())
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    async def list_tools_for_workspace(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        is_enabled: bool | None = None,
    ) -> Sequence[Tool]:
        """
        List all tools cataloged in a workspace.

        Args:
            session: Active database session.
            workspace_id: Authorized workspace boundary.
            is_enabled: Optional filter by enabled flag.

        Returns:
            Sequence of Tool instances.
        """
        stmt = select(Tool).where(Tool.workspace_id == workspace_id)
        if is_enabled is not None:
            stmt = stmt.where(Tool.is_enabled == is_enabled)
        stmt = stmt.order_by(Tool.name.asc())
        result = await session.execute(stmt)
        return result.scalars().all()

    async def update_tool(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        tool_id: uuid.UUID,
        data: ToolUpdate,
    ) -> Tool:
        """
        Update mutable fields of a Tool.

        Args:
            session: Active database session.
            workspace_id: Authorized workspace boundary.
            tool_id: ID of the tool to update.
            data: Update payload.

        Returns:
            Updated Tool entity.

        Raises:
            NotFoundError: If tool does not exist in workspace.
        """
        tool = await self.get_tool(session=session, workspace_id=workspace_id, tool_id=tool_id)
        if tool is None:
            raise NotFoundError(f"Tool '{tool_id}' not found in workspace '{workspace_id}'.")

        update_dict = data.model_dump(exclude_unset=True)

        if "title" in update_dict:
            tool.title = update_dict["title"]
        if "description" in update_dict:
            tool.description = update_dict["description"]
        if "input_schema" in update_dict:
            tool.input_schema = update_dict["input_schema"]
        if "annotations" in update_dict:
            tool.annotations = update_dict["annotations"]
        if update_dict.get("classification_status") is not None:
            tool.classification_status = update_dict["classification_status"].value
        if update_dict.get("risk_labels") is not None:
            tool.risk_labels = update_dict["risk_labels"]
        if update_dict.get("is_enabled") is not None:
            tool.is_enabled = update_dict["is_enabled"]

        # Recompute fingerprint if schema, description, or title changed
        if any(k in update_dict for k in ("input_schema", "description", "title")):
            from acp_core.registry.tool_validation import compute_tool_fingerprint

            tool.fingerprint = compute_tool_fingerprint(
                name=tool.name,
                input_schema=tool.input_schema,
                description=tool.description,
                title=tool.title,
            )

        tool.updated_at = datetime.now(UTC)
        await session.flush()

        logger.info(
            "registry.tool_updated",
            tool_id=str(tool_id),
            workspace_id=str(workspace_id),
            fields=list(update_dict.keys()),
        )
        return tool

    async def delete_tool(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        tool_id: uuid.UUID,
    ) -> bool:
        """
        Delete a Tool from the workspace catalog.

        Args:
            session: Active database session.
            workspace_id: Authorized workspace boundary.
            tool_id: Tool ID.

        Returns:
            True if deleted, False if not found.
        """
        tool = await self.get_tool(session=session, workspace_id=workspace_id, tool_id=tool_id)
        if tool is None:
            return False

        await session.delete(tool)
        await session.flush()

        logger.info(
            "registry.tool_deleted",
            tool_id=str(tool_id),
            workspace_id=str(workspace_id),
        )
        return True

    # ── Snapshot Operations ───────────────────────────────────────────────────

    async def create_snapshot(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        data: ToolSnapshotCreate,
    ) -> ToolSnapshot:
        """
        Record a historical discovery snapshot for an MCP server.

        Args:
            session: Active database session.
            workspace_id: Authorized workspace boundary.
            data: Snapshot payload.

        Returns:
            Newly created ToolSnapshot entity.

        Raises:
            ValidationError: If payload workspace_id mismatches caller's workspace.
            NotFoundError: If server does not exist in workspace.
        """
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

        await self._verify_server_in_workspace(
            session=session,
            workspace_id=workspace_id,
            server_id=data.server_id,
        )

        catalog_hash = data.resolve_catalog_hash()
        tool_count = data.resolve_tool_count()

        snapshot = ToolSnapshot(
            id=data.id or uuid.uuid4(),
            workspace_id=workspace_id,
            server_id=data.server_id,
            snapshot_at=datetime.now(UTC),
            catalog_hash=catalog_hash,
            tools_data=data.tools_data,
            tool_count=tool_count,
            metadata_=data.metadata,
        )

        session.add(snapshot)
        await session.flush()

        logger.info(
            "registry.tool_snapshot_created",
            snapshot_id=str(snapshot.id),
            workspace_id=str(workspace_id),
            server_id=str(data.server_id),
            tool_count=tool_count,
            catalog_hash=catalog_hash[:12],
        )
        return snapshot

    async def get_snapshot(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        snapshot_id: uuid.UUID,
    ) -> ToolSnapshot | None:
        """
        Retrieve a discovery snapshot by ID, strictly scoped to workspace.

        Args:
            session: Active database session.
            workspace_id: Authorized workspace ID.
            snapshot_id: Snapshot ID.

        Returns:
            ToolSnapshot if found and authorized, else None.
        """
        stmt = select(ToolSnapshot).where(
            ToolSnapshot.id == snapshot_id,
            ToolSnapshot.workspace_id == workspace_id,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_snapshots_for_server(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        server_id: uuid.UUID,
        limit: int = 20,
    ) -> Sequence[ToolSnapshot]:
        """
        List historical discovery snapshots for a server in chronological descending order.

        Args:
            session: Active database session.
            workspace_id: Authorized workspace boundary.
            server_id: MCP server ID.
            limit: Maximum snapshots to return.

        Returns:
            Sequence of ToolSnapshot entities.
        """
        stmt = (
            select(ToolSnapshot)
            .where(
                ToolSnapshot.workspace_id == workspace_id,
                ToolSnapshot.server_id == server_id,
            )
            .order_by(ToolSnapshot.snapshot_at.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return result.scalars().all()
