"""
Upstream MCP Server management API endpoints for Kolang ACP (ACP-009).

Provides workspace-scoped endpoints for registering, listing, viewing,
updating, and removing Upstream MCP Servers.
"""

from __future__ import annotations

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from acp_core.common.errors import AuthorizationError, NotFoundError
from acp_core.db import get_db_session
from acp_core.registry.models import (
    McpServerCreate,
    McpServerRead,
    McpServerStatus,
    McpServerUpdate,
)
from acp_core.registry.service import McpServerService
from acp_core.workspaces.scoping import (
    TenantContext,
    extract_tenant_context,
    resolve_trusted_workspace_id,
)
from acp_core.workspaces.service import WorkspaceService

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["MCP Servers"])
_server_service = McpServerService()
_workspace_service = WorkspaceService()


def _get_workspace_context(
    x_workspace_id: Annotated[str | None, Header(alias="X-Workspace-ID")] = None,
) -> TenantContext:
    """Resolve trusted TenantContext from request headers or contextvars."""
    try:
        return extract_tenant_context()
    except AuthorizationError:
        if x_workspace_id:
            try:
                ws_uuid = uuid.UUID(x_workspace_id)
                return TenantContext(workspace_id=ws_uuid)
            except ValueError as exc:
                raise AuthorizationError(
                    f"Invalid X-Workspace-ID UUID: '{x_workspace_id}'"
                ) from exc
        raise


# ── Nested Workspace Routes: /api/v1/workspaces/{workspace_id}/servers ────────


@router.post(
    "/api/v1/workspaces/{workspace_id}/servers",
    response_model=McpServerRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register MCP server in workspace",
    description="Registers a new Upstream MCP Server scoped to the specified workspace.",
)
async def create_workspace_server(
    workspace_id: uuid.UUID,
    payload: McpServerCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_ctx: Annotated[TenantContext, Depends(_get_workspace_context)] = None,  # type: ignore[assignment]
) -> McpServerRead:
    # Ensure workspace exists
    await _workspace_service.get_workspace_or_raise(session=session, workspace_id=workspace_id)

    # Enforce tenant isolation if tenant_ctx is present
    if tenant_ctx is not None and not tenant_ctx.matches(workspace_id):
        logger.warning(
            "security.cross_workspace_registration_blocked",
            caller_workspace=tenant_ctx.workspace_id_str,
            target_workspace=str(workspace_id),
        )
        raise AuthorizationError("Access denied: cannot register server in another workspace.")

    server = await _server_service.create_server(
        session=session,
        workspace_id=workspace_id,
        data=payload,
    )
    await session.commit()
    await session.refresh(server)
    return McpServerRead.model_validate(server)


@router.get(
    "/api/v1/workspaces/{workspace_id}/servers",
    response_model=list[McpServerRead],
    summary="List MCP servers in workspace",
    description="Lists all MCP servers registered within the specified workspace.",
)
async def list_workspace_servers(
    workspace_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    status_filter: Annotated[McpServerStatus | None, Query(alias="status")] = None,
    tenant_ctx: Annotated[TenantContext, Depends(_get_workspace_context)] = None,  # type: ignore[assignment]
) -> list[McpServerRead]:
    # Ensure workspace exists
    await _workspace_service.get_workspace_or_raise(session=session, workspace_id=workspace_id)

    # Enforce tenant isolation if tenant_ctx is present
    if tenant_ctx is not None and not tenant_ctx.matches(workspace_id):
        logger.warning(
            "security.cross_workspace_list_blocked",
            caller_workspace=tenant_ctx.workspace_id_str,
            target_workspace=str(workspace_id),
        )
        raise AuthorizationError("Access denied: cannot view servers in another workspace.")

    servers = await _server_service.list_servers(
        session=session,
        workspace_id=workspace_id,
        status=status_filter,
    )
    return [McpServerRead.model_validate(s) for s in servers]


@router.get(
    "/api/v1/workspaces/{workspace_id}/servers/{server_id}",
    response_model=McpServerRead,
    summary="Get MCP server in workspace",
    description="Retrieves details for a specific MCP server in the workspace.",
)
async def get_workspace_server(
    workspace_id: uuid.UUID,
    server_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_ctx: Annotated[TenantContext, Depends(_get_workspace_context)] = None,  # type: ignore[assignment]
) -> McpServerRead:
    if tenant_ctx is not None and not tenant_ctx.matches(workspace_id):
        raise NotFoundError(f"MCP Server '{server_id}' not found.")

    server = await _server_service.get_server_or_raise(
        session=session,
        workspace_id=workspace_id,
        server_id=server_id,
    )
    return McpServerRead.model_validate(server)


@router.patch(
    "/api/v1/workspaces/{workspace_id}/servers/{server_id}",
    response_model=McpServerRead,
    summary="Update MCP server in workspace",
    description="Updates mutable attributes of an MCP server within workspace scope.",
)
async def update_workspace_server(
    workspace_id: uuid.UUID,
    server_id: uuid.UUID,
    payload: McpServerUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_ctx: Annotated[TenantContext, Depends(_get_workspace_context)] = None,  # type: ignore[assignment]
) -> McpServerRead:
    if tenant_ctx is not None and not tenant_ctx.matches(workspace_id):
        raise NotFoundError(f"MCP Server '{server_id}' not found.")

    server = await _server_service.update_server(
        session=session,
        workspace_id=workspace_id,
        server_id=server_id,
        data=payload,
    )
    await session.commit()
    await session.refresh(server)
    return McpServerRead.model_validate(server)


@router.delete(
    "/api/v1/workspaces/{workspace_id}/servers/{server_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete MCP server in workspace",
    description="Removes an MCP server from the workspace.",
)
async def delete_workspace_server(
    workspace_id: uuid.UUID,
    server_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_ctx: Annotated[TenantContext, Depends(_get_workspace_context)] = None,  # type: ignore[assignment]
) -> None:
    if tenant_ctx is not None and not tenant_ctx.matches(workspace_id):
        raise NotFoundError(f"MCP Server '{server_id}' not found.")

    await _server_service.delete_server(
        session=session,
        workspace_id=workspace_id,
        server_id=server_id,
    )
    await session.commit()


# ── Top-level Scoped Routes: /api/v1/servers ──────────────────────────────────


@router.post(
    "/api/v1/servers",
    response_model=McpServerRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register MCP server in active tenant workspace",
    description="Registers an Upstream MCP Server in the caller's active workspace scope.",
)
async def create_server(
    payload: McpServerCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_ctx: Annotated[TenantContext, Depends(_get_workspace_context)],
) -> McpServerRead:
    target_ws = resolve_trusted_workspace_id(tenant_ctx, payload.workspace_id)
    server = await _server_service.create_server(
        session=session,
        workspace_id=target_ws,
        data=payload,
    )
    await session.commit()
    await session.refresh(server)
    return McpServerRead.model_validate(server)


@router.get(
    "/api/v1/servers",
    response_model=list[McpServerRead],
    summary="List MCP servers in active tenant workspace",
    description="Lists all MCP servers within the caller's active workspace scope.",
)
async def list_servers(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_ctx: Annotated[TenantContext, Depends(_get_workspace_context)],
    status_filter: Annotated[McpServerStatus | None, Query(alias="status")] = None,
) -> list[McpServerRead]:
    servers = await _server_service.list_servers(
        session=session,
        workspace_id=tenant_ctx.workspace_id,
        status=status_filter,
    )
    return [McpServerRead.model_validate(s) for s in servers]


@router.get(
    "/api/v1/servers/{server_id}",
    response_model=McpServerRead,
    summary="Get MCP server by ID in active workspace",
    description=(
        "Retrieves MCP server details. Returns 404 if server belongs to another workspace."
    ),
)
async def get_server(
    server_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_ctx: Annotated[TenantContext, Depends(_get_workspace_context)],
) -> McpServerRead:
    server = await _server_service.get_server_or_raise(
        session=session,
        workspace_id=tenant_ctx.workspace_id,
        server_id=server_id,
    )
    return McpServerRead.model_validate(server)


@router.patch(
    "/api/v1/servers/{server_id}",
    response_model=McpServerRead,
    summary="Update MCP server in active workspace",
    description=(
        "Updates MCP server attributes. Returns 404 if server belongs to another workspace."
    ),
)
async def update_server(
    server_id: uuid.UUID,
    payload: McpServerUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_ctx: Annotated[TenantContext, Depends(_get_workspace_context)],
) -> McpServerRead:
    server = await _server_service.update_server(
        session=session,
        workspace_id=tenant_ctx.workspace_id,
        server_id=server_id,
        data=payload,
    )
    await session.commit()
    await session.refresh(server)
    return McpServerRead.model_validate(server)


@router.delete(
    "/api/v1/servers/{server_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete MCP server in active workspace",
    description="Deletes an MCP server. Returns 404 if server belongs to another workspace.",
)
async def delete_server(
    server_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_ctx: Annotated[TenantContext, Depends(_get_workspace_context)],
) -> None:
    await _server_service.delete_server(
        session=session,
        workspace_id=tenant_ctx.workspace_id,
        server_id=server_id,
    )
    await session.commit()
