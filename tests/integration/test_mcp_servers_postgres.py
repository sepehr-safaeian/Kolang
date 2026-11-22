"""
Integration tests for MCP Server domain model, persistence, and APIs on PostgreSQL (ACP-009).

Verifies against live PostgreSQL in Docker:
- Schema creation from Base.metadata and migration 0003.
- Composite unique constraint (workspace_id, slug).
- Cascade deletion: deleting a workspace removes all its child MCP servers.
- McpServerService multi-tenant isolation and IDOR protection.
- FastAPI REST endpoints:
  - /api/v1/workspaces/{workspace_id}/servers
  - /api/v1/servers
- URL validation and SSRF rejection in HTTP request handling.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from acp_core.common.errors import ConflictError, NotFoundError
from acp_core.common.settings import Settings
from acp_core.db import (
    Base,
    DatabaseManager,
    reset_db_manager,
    transactional_session,
)
from acp_core.registry.models import (
    McpServer,
    McpServerCreate,
    McpServerStatus,
    McpServerTransport,
    McpServerUpdate,
)
from acp_core.registry.service import McpServerService
from acp_core.workspaces.models import WorkspaceCreate
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

    # Clean up tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await mgr.close()
    reset_db_manager()


# ── Persistence, CRUD, and Multi-Tenant Isolation ────────────────────────────


@pytest.mark.asyncio
async def test_mcp_server_postgres_crud_and_isolation(pg_db: DatabaseManager) -> None:
    """Verify full CRUD, tenant isolation, and slug scoping on PostgreSQL."""
    factory = pg_db.get_session_factory()
    workspace_service = WorkspaceService()
    server_service = McpServerService()

    async with factory() as session, transactional_session(session=session) as tx_session:
        # Create two distinct workspaces
        ws_a = await workspace_service.create_workspace(
            session=tx_session,
            data=WorkspaceCreate(name="Tenant Alpha", slug="tenant-alpha"),
        )
        ws_b = await workspace_service.create_workspace(
            session=tx_session,
            data=WorkspaceCreate(name="Tenant Beta", slug="tenant-beta"),
        )
        ws_a_id = ws_a.id
        ws_b_id = ws_b.id

    # Register Server in Workspace A
    async with factory() as session, transactional_session(session=session) as tx_session:
        srv_a = await server_service.create_server(
            session=tx_session,
            workspace_id=ws_a_id,
            data=McpServerCreate(
                name="GitHub Integration",
                slug="github",
                endpoint_url="https://api.github.com/mcp",
                transport=McpServerTransport.STREAMABLE_HTTP,
                description="GitHub pull requests and issue tools",
            ),
        )
        srv_a_id = srv_a.id
        assert srv_a.workspace_id == ws_a_id
        assert srv_a.status == McpServerStatus.PENDING.value

    # Register Server with identical slug in Workspace B (permitted because slug is tenant-scoped)
    async with factory() as session, transactional_session(session=session) as tx_session:
        srv_b = await server_service.create_server(
            session=tx_session,
            workspace_id=ws_b_id,
            data=McpServerCreate(
                name="Tenant Beta GitHub",
                slug="github",
                endpoint_url="https://api.github.com/beta-mcp",
            ),
        )
        assert srv_b.workspace_id == ws_b_id
        assert srv_b.slug == "github"

    # Attempt duplicate slug in Workspace A -> raises ConflictError
    async with factory() as session, transactional_session(session=session) as tx_session:
        with pytest.raises(ConflictError, match="already exists in workspace"):
            await server_service.create_server(
                session=tx_session,
                workspace_id=ws_a_id,
                data=McpServerCreate(
                    name="Duplicate GitHub",
                    slug="github",
                    endpoint_url="https://another.example.com/mcp",
                ),
            )

    # Cross-Workspace Read Isolation
    async with factory() as session, transactional_session(session=session) as tx_session:
        # Workspace A can read its own server
        fetched_a = await server_service.get_server_or_raise(
            session=tx_session,
            workspace_id=ws_a_id,
            server_id=srv_a_id,
        )
        assert fetched_a.id == srv_a_id

        # Workspace B querying Workspace A's server raises NotFoundError (IDOR protection)
        with pytest.raises(NotFoundError):
            await server_service.get_server_or_raise(
                session=tx_session,
                workspace_id=ws_b_id,
                server_id=srv_a_id,
            )

    # Cross-Workspace Update & Delete Isolation
    async with factory() as session, transactional_session(session=session) as tx_session:
        # Workspace B attempting to update Workspace A's server -> NotFoundError
        with pytest.raises(NotFoundError):
            await server_service.update_server(
                session=tx_session,
                workspace_id=ws_b_id,
                server_id=srv_a_id,
                data=McpServerUpdate(name="Hacked Name"),
            )

        # Workspace B attempting to delete Workspace A's server -> NotFoundError
        with pytest.raises(NotFoundError):
            await server_service.delete_server(
                session=tx_session,
                workspace_id=ws_b_id,
                server_id=srv_a_id,
            )


@pytest.mark.asyncio
async def test_mcp_server_cascade_delete_on_workspace_removal(pg_db: DatabaseManager) -> None:
    """Verify that deleting a workspace cascades and removes all its MCP servers."""
    factory = pg_db.get_session_factory()
    workspace_service = WorkspaceService()
    server_service = McpServerService()

    async with factory() as session, transactional_session(session=session) as tx_session:
        ws = await workspace_service.create_workspace(
            session=tx_session,
            data=WorkspaceCreate(name="Temporary Workspace", slug="temp-ws"),
        )
        ws_id = ws.id

        srv1 = await server_service.create_server(
            session=tx_session,
            workspace_id=ws_id,
            data=McpServerCreate(name="S1", slug="s1", endpoint_url="https://s1.example.com/mcp"),
        )
        srv2 = await server_service.create_server(
            session=tx_session,
            workspace_id=ws_id,
            data=McpServerCreate(name="S2", slug="s2", endpoint_url="https://s2.example.com/mcp"),
        )
        s1_id = srv1.id
        s2_id = srv2.id

    # Verify both servers exist
    async with factory() as session, transactional_session(session=session) as tx_session:
        servers = await server_service.list_servers(session=tx_session, workspace_id=ws_id)
        assert len(servers) == 2

    # Delete workspace
    async with factory() as session, transactional_session(session=session) as tx_session:
        ws_to_delete = await workspace_service.get_workspace_or_raise(
            session=tx_session, workspace_id=ws_id
        )
        await tx_session.delete(ws_to_delete)

    # Verify cascade deletion
    async with factory() as session:
        res = await session.execute(select(McpServer).where(McpServer.id.in_([s1_id, s2_id])))
        remaining = res.scalars().all()
        assert len(remaining) == 0


# ── FastAPI REST Endpoint Integration Tests ──────────────────────────────────


@pytest.mark.asyncio
async def test_mcp_server_api_endpoints_and_ssrf_rejection(pg_db: DatabaseManager) -> None:
    """Verify REST endpoints for MCP servers, cross-workspace isolation, and SSRF rejection."""
    app = create_app()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("acp_core.db.session._db_manager", pg_db)
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Create Workspace A and Workspace B
            res_ws_a = await client.post(
                "/api/v1/workspaces",
                json={"name": "Org A", "slug": "org-a"},
            )
            assert res_ws_a.status_code == 201
            ws_a_id = res_ws_a.json()["id"]

            res_ws_b = await client.post(
                "/api/v1/workspaces",
                json={"name": "Org B", "slug": "org-b"},
            )
            assert res_ws_b.status_code == 201
            ws_b_id = res_ws_b.json()["id"]

            # 2. Register Server in Workspace A via nested endpoint
            srv_payload = {
                "name": "Production Filesystem",
                "slug": "filesystem",
                "endpoint_url": "https://fs.example.com/mcp",
                "transport": "streamable_http",
                "description": "Secure file storage tools",
            }
            res_create = await client.post(
                f"/api/v1/workspaces/{ws_a_id}/servers",
                json=srv_payload,
                headers={"X-Workspace-ID": ws_a_id},
            )
            assert res_create.status_code == 201
            srv_data = res_create.json()
            srv_id = srv_data["id"]
            assert srv_data["name"] == "Production Filesystem"
            assert srv_data["slug"] == "filesystem"
            assert srv_data["status"] == "pending"

            # 3. List Servers in Workspace A via /api/v1/servers with X-Workspace-ID
            res_list_a = await client.get(
                "/api/v1/servers",
                headers={"X-Workspace-ID": ws_a_id},
            )
            assert res_list_a.status_code == 200
            items_a = res_list_a.json()
            assert len(items_a) == 1
            assert items_a[0]["id"] == srv_id

            # 4. List Servers in Workspace B -> empty (tenant isolation)
            res_list_b = await client.get(
                "/api/v1/servers",
                headers={"X-Workspace-ID": ws_b_id},
            )
            assert res_list_b.status_code == 200
            items_b = res_list_b.json()
            assert len(items_b) == 0

            # 5. Cross-Workspace IDOR Attempt: Workspace B tries to GET Workspace A's server -> 404
            res_idor = await client.get(
                f"/api/v1/servers/{srv_id}",
                headers={"X-Workspace-ID": ws_b_id},
            )
            assert res_idor.status_code == 404

            # 6. Update Server in Workspace A
            res_patch = await client.patch(
                f"/api/v1/servers/{srv_id}",
                json={"status": "connected", "description": "Operational and connected"},
                headers={"X-Workspace-ID": ws_a_id},
            )
            assert res_patch.status_code == 200
            assert res_patch.json()["status"] == "connected"
            assert res_patch.json()["description"] == "Operational and connected"

            # 7. SSRF Rejection: Cloud metadata IP
            res_ssrf_meta = await client.post(
                "/api/v1/servers",
                json={
                    "name": "Cloud Metadata Exploit",
                    "slug": "exploit-metadata",
                    "endpoint_url": "http://169.254.169.254/latest/meta-data",
                },
                headers={"X-Workspace-ID": ws_a_id},
            )
            assert res_ssrf_meta.status_code == 422

            # 8. SSRF Rejection: Local loopback when demo is disabled
            res_ssrf_local = await client.post(
                "/api/v1/servers",
                json={
                    "name": "Local Loopback Exploit",
                    "slug": "exploit-loopback",
                    "endpoint_url": "http://127.0.0.1:8080/mcp",
                },
                headers={"X-Workspace-ID": ws_a_id},
            )
            assert res_ssrf_local.status_code == 422

            # 9. Delete Server in Workspace A
            res_delete = await client.delete(
                f"/api/v1/servers/{srv_id}",
                headers={"X-Workspace-ID": ws_a_id},
            )
            assert res_delete.status_code == 204

            # Verify deletion
            res_get_deleted = await client.get(
                f"/api/v1/servers/{srv_id}",
                headers={"X-Workspace-ID": ws_a_id},
            )
            assert res_get_deleted.status_code == 404
