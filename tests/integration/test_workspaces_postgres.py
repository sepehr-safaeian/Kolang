"""
Integration tests for Workspace Domain Model and Seeding on PostgreSQL (ACP-008).

Verifies against live PostgreSQL in Docker:
- Schema persistence and unique slug constraints on the workspaces table.
- WorkspaceService CRUD lifecycle (create, read, list, update, disable).
- Idempotent execution of seed_demo_workspace().
- FastAPI workspace management endpoints (/api/v1/workspaces).
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from acp_core.common.errors import ConflictError
from acp_core.common.settings import Settings
from acp_core.db import (
    Base,
    DatabaseManager,
    reset_db_manager,
    transactional_session,
)
from acp_core.workspaces.models import (
    Workspace,
    WorkspaceCreate,
    WorkspaceStatus,
    WorkspaceUpdate,
)
from acp_core.workspaces.seed import (
    DEMO_WORKSPACE_ID,
    DEMO_WORKSPACE_NAME,
    DEMO_WORKSPACE_SLUG,
    seed_demo_workspace,
)
from acp_core.workspaces.service import WorkspaceService
from apps.api.app.main import create_app

POSTGRES_PORT = os.environ.get("ACP_POSTGRES_PORT", "5433")
DOCKER_POSTGRES_URL = f"postgresql+asyncpg://kolang:kolang@localhost:{POSTGRES_PORT}/kolang"


@pytest.fixture
async def pg_settings() -> Settings:
    return Settings(
        ACP_DATABASE_URL=DOCKER_POSTGRES_URL,
        ACP_DATABASE_POOL_SIZE=5,
        ACP_DATABASE_MAX_OVERFLOW=5,
        ACP_DATABASE_POOL_TIMEOUT=10.0,
        ACP_DATABASE_ECHO=False,
    )


@pytest.fixture
async def pg_db(pg_settings: Settings) -> AsyncGenerator[DatabaseManager, None]:
    reset_db_manager()
    mgr = DatabaseManager()
    mgr.initialize(pg_settings)

    is_connected = await mgr.ping()
    if not is_connected:
        pytest.skip(f"Docker PostgreSQL not reachable at {DOCKER_POSTGRES_URL}")

    engine = mgr.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield mgr

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await mgr.close()
    reset_db_manager()


@pytest.mark.asyncio
async def test_live_postgres_workspace_crud_lifecycle(pg_db: DatabaseManager) -> None:
    """Verify WorkspaceService operations on live PostgreSQL."""
    factory = pg_db.get_session_factory()
    service = WorkspaceService()

    # 1. Create Workspace
    async with factory() as session, transactional_session(session=session) as tx_session:
        created = await service.create_workspace(
            session=tx_session,
            data=WorkspaceCreate(
                name="Acme Corporation",
                slug="acme-corp",
                description="Acme enterprise tenant",
            ),
        )
        ws_id = created.id
        assert ws_id is not None
        assert created.slug == "acme-corp"
        assert created.status == WorkspaceStatus.ACTIVE.value

    # 2. Retrieve Workspace
    async with factory() as session:
        fetched = await service.get_workspace(session, ws_id)
        assert fetched is not None
        assert fetched.name == "Acme Corporation"
        assert fetched.slug == "acme-corp"
        assert fetched.is_active is True

    # 3. Update Workspace
    async with factory() as session, transactional_session(session=session) as tx_session:
        updated = await service.update_workspace(
            session=tx_session,
            workspace_id=ws_id,
            data=WorkspaceUpdate(name="Acme Global Inc.", description="Updated description"),
        )
        assert updated.name == "Acme Global Inc."

    # 4. Disable Workspace
    async with factory() as session, transactional_session(session=session) as tx_session:
        disabled = await service.disable_workspace(session=tx_session, workspace_id=ws_id)
        assert disabled.status == WorkspaceStatus.DISABLED.value
        assert disabled.is_active is False

    # 5. Verify persistence
    async with factory() as session:
        refetched = await service.get_workspace(session, ws_id)
        assert refetched is not None
        assert refetched.name == "Acme Global Inc."
        assert refetched.status == WorkspaceStatus.DISABLED.value


@pytest.mark.asyncio
async def test_live_postgres_slug_uniqueness_enforced(pg_db: DatabaseManager) -> None:
    """Verify that duplicate slugs raise ConflictError and DB unique constraint."""
    factory = pg_db.get_session_factory()
    service = WorkspaceService()

    async with factory() as session, transactional_session(session=session) as tx_session:
        await service.create_workspace(
            session=tx_session,
            data=WorkspaceCreate(name="Original", slug="duplicate-slug"),
        )

    # Attempting to create duplicate slug via service raises ConflictError
    async with factory() as session, transactional_session(session=session) as tx_session:
        with pytest.raises(ConflictError, match="already exists"):
            await service.create_workspace(
                session=tx_session,
                data=WorkspaceCreate(name="Duplicate", slug="duplicate-slug"),
            )


@pytest.mark.asyncio
async def test_live_postgres_seed_demo_workspace_idempotent(pg_db: DatabaseManager) -> None:
    """Verify demo workspace seeding on PostgreSQL: creates demo workspace and is idempotent."""
    factory = pg_db.get_session_factory()

    # 1. First run seeds demo workspace
    async with factory() as session, transactional_session(session=session) as tx_session:
        demo_1 = await seed_demo_workspace(tx_session)
        assert demo_1.id == DEMO_WORKSPACE_ID
        assert demo_1.slug == DEMO_WORKSPACE_SLUG
        assert demo_1.name == DEMO_WORKSPACE_NAME

    # 2. Second run is completely idempotent
    async with factory() as session, transactional_session(session=session) as tx_session:
        demo_2 = await seed_demo_workspace(tx_session)
        assert demo_2.id == DEMO_WORKSPACE_ID
        assert demo_2.slug == DEMO_WORKSPACE_SLUG

    # 3. Verify exactly one demo row exists
    async with factory() as session:
        result = await session.execute(
            select(Workspace).where(Workspace.slug == DEMO_WORKSPACE_SLUG)
        )
        rows = result.scalars().all()
        assert len(rows) == 1


@pytest.mark.asyncio
async def test_workspace_api_endpoints(pg_db: DatabaseManager) -> None:
    """Verify FastAPI /api/v1/workspaces endpoints against PostgreSQL."""
    app = create_app()

    # Ensure DB manager is bound
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("acp_core.db.session._db_manager", pg_db)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Seed demo workspace via API
            seed_resp = await client.post("/api/v1/workspaces/seed-demo")
            assert seed_resp.status_code == 200
            seed_data = seed_resp.json()
            assert seed_data["slug"] == "demo"
            assert seed_data["id"] == str(DEMO_WORKSPACE_ID)

            # 2. List workspaces
            list_resp = await client.get("/api/v1/workspaces")
            assert list_resp.status_code == 200
            items = list_resp.json()
            assert len(items) >= 1
            assert any(item["slug"] == "demo" for item in items)

            # 3. Create second workspace
            create_resp = await client.post(
                "/api/v1/workspaces",
                json={
                    "name": "Beta Workspace",
                    "slug": "beta-ws",
                    "description": "Beta testing tenant",
                },
            )
            assert create_resp.status_code == 201
            beta_data = create_resp.json()
            assert beta_data["slug"] == "beta-ws"
            beta_id = beta_data["id"]

            # 4. Get workspace by ID
            get_resp = await client.get(f"/api/v1/workspaces/{beta_id}")
            assert get_resp.status_code == 200
            assert get_resp.json()["name"] == "Beta Workspace"

            # 5. Patch workspace
            patch_resp = await client.patch(
                f"/api/v1/workspaces/{beta_id}",
                json={"name": "Beta Renamed", "status": "disabled"},
            )
            assert patch_resp.status_code == 200
            assert patch_resp.json()["name"] == "Beta Renamed"
            assert patch_resp.json()["status"] == "disabled"
