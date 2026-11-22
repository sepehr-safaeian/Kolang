"""
Workspace management API endpoints for Kolang ACP.

Provides endpoints for creating, listing, viewing, updating workspaces,
and seeding the demo workspace for local development.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from acp_core.db import get_db_session
from acp_core.workspaces.models import (
    WorkspaceCreate,
    WorkspaceRead,
    WorkspaceStatus,
    WorkspaceUpdate,
)
from acp_core.workspaces.seed import seed_demo_workspace
from acp_core.workspaces.service import WorkspaceService

router = APIRouter(prefix="/api/v1/workspaces", tags=["Workspaces"])
_service = WorkspaceService()


@router.post(
    "",
    response_model=WorkspaceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new workspace",
    description="Creates a new organizational boundary for tenant resources.",
)
async def create_workspace(
    payload: WorkspaceCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WorkspaceRead:
    workspace = await _service.create_workspace(session=session, data=payload)
    await session.commit()
    await session.refresh(workspace)
    return WorkspaceRead.model_validate(workspace)


@router.get(
    "",
    response_model=list[WorkspaceRead],
    summary="List workspaces",
    description="List all organizational workspaces, optionally filtered by status.",
)
async def list_workspaces(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    status_filter: Annotated[WorkspaceStatus | None, Query(alias="status")] = None,
) -> list[WorkspaceRead]:
    workspaces = await _service.list_workspaces(session=session, status=status_filter)
    return [WorkspaceRead.model_validate(ws) for ws in workspaces]


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceRead,
    summary="Get workspace by ID",
    description="Retrieve workspace metadata for a given UUID.",
)
async def get_workspace(
    workspace_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WorkspaceRead:
    workspace = await _service.get_workspace_or_raise(session=session, workspace_id=workspace_id)
    return WorkspaceRead.model_validate(workspace)


@router.patch(
    "/{workspace_id}",
    response_model=WorkspaceRead,
    summary="Update workspace",
    description="Update mutable workspace attributes such as name, status, or description.",
)
async def update_workspace(
    workspace_id: uuid.UUID,
    payload: WorkspaceUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WorkspaceRead:
    workspace = await _service.update_workspace(
        session=session,
        workspace_id=workspace_id,
        data=payload,
    )
    await session.commit()
    await session.refresh(workspace)
    return WorkspaceRead.model_validate(workspace)


@router.post(
    "/seed-demo",
    response_model=WorkspaceRead,
    status_code=status.HTTP_200_OK,
    summary="Seed demo workspace",
    description="Idempotently ensures the standard Demo Workspace exists.",
)
async def seed_demo(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WorkspaceRead:
    demo_ws = await seed_demo_workspace(session=session)
    await session.commit()
    await session.refresh(demo_ws)
    return WorkspaceRead.model_validate(demo_ws)
