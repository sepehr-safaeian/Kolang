"""
Demo Workspace Seeding for Kolang ACP.

Provides deterministic demo seed data for local development, demonstration,
and verification tests without requiring manual database bootstrap steps.
"""

from __future__ import annotations

import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from acp_core.workspaces.models import Workspace, WorkspaceStatus

logger = structlog.get_logger(__name__)

# Deterministic demo workspace identifier
DEMO_WORKSPACE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEMO_WORKSPACE_NAME = "Demo Workspace"
DEMO_WORKSPACE_SLUG = "demo"
DEMO_WORKSPACE_DESCRIPTION = "Default seeded workspace for local development and evaluation."


async def seed_demo_workspace(session: AsyncSession) -> Workspace:
    """
    Ensure the standard Demo Workspace exists in the database.

    Idempotent operation: creates the workspace if absent; returns existing if present.

    Args:
        session: Active SQLAlchemy async session.

    Returns:
        The active demo Workspace instance.
    """
    # 1. Check by deterministic ID
    result = await session.execute(select(Workspace).where(Workspace.id == DEMO_WORKSPACE_ID))
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    # 2. Check by unique slug in case created with a different ID
    result_by_slug = await session.execute(
        select(Workspace).where(Workspace.slug == DEMO_WORKSPACE_SLUG)
    )
    existing_by_slug = result_by_slug.scalar_one_or_none()
    if existing_by_slug:
        return existing_by_slug

    # 3. Create demo workspace
    demo_ws = Workspace(
        id=DEMO_WORKSPACE_ID,
        name=DEMO_WORKSPACE_NAME,
        slug=DEMO_WORKSPACE_SLUG,
        status=WorkspaceStatus.ACTIVE.value,
        description=DEMO_WORKSPACE_DESCRIPTION,
    )
    session.add(demo_ws)
    await session.flush()

    logger.info(
        "workspace.demo_seeded",
        workspace_id=str(DEMO_WORKSPACE_ID),
        slug=DEMO_WORKSPACE_SLUG,
        name=DEMO_WORKSPACE_NAME,
    )
    return demo_ws
