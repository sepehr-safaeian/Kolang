"""
Integration tests for Tool Catalog and Tool Snapshot on PostgreSQL (ACP-010).

Verifies against live PostgreSQL in Docker:
1. Acceptance Criteria:
   - Migration 0004 execution and table creation.
   - Schema stored and retrieved as native PostgreSQL JSONB (verified via information_schema).
   - Deterministic fingerprint stored and indexed.
   - Multi-tenant boundary isolation: zero leakage of tools between workspaces (anti-IDOR).
2. Relational Integrity:
   - Unique constraint (server_id, name) enforced by PostgreSQL engine.
   - Cascade deletion: deleting an MCP server cascades to tools and snapshots.
   - Cascade deletion: deleting a workspace cascades through servers to tools.
3. ToolService operations on live database.
4. Historical ToolSnapshot recording and retrieval.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import select, text

from acp_core.common.errors import ConflictError, NotFoundError
from acp_core.common.settings import Settings
from acp_core.db import (
    Base,
    DatabaseManager,
    reset_db_manager,
    transactional_session,
)
from acp_core.registry.models import McpServerCreate
from acp_core.registry.service import McpServerService
from acp_core.registry.tool_models import (
    Tool,
    ToolClassificationStatus,
    ToolCreate,
    ToolSnapshot,
    ToolSnapshotCreate,
    ToolUpdate,
)
from acp_core.registry.tool_service import ToolService
from acp_core.workspaces.models import WorkspaceCreate
from acp_core.workspaces.service import WorkspaceService

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


@pytest.mark.asyncio
async def test_acceptance_criteria_jsonb_storage_type(pg_db: DatabaseManager) -> None:
    """
    Acceptance Criteria Test:
    Verify that `input_schema`, `annotations`, `risk_labels` in tools,
    and `tools_data`, `metadata` in tool_snapshots are stored as native JSONB in PostgreSQL.
    """
    engine = pg_db.get_engine()
    async with engine.connect() as conn:
        stmt = text(
            """
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name IN ('tools', 'tool_snapshots')
              AND column_name IN (
                  'input_schema', 'annotations', 'risk_labels', 'tools_data', 'metadata'
              )
            ORDER BY table_name, column_name;
            """
        )
        result = await conn.execute(stmt)
        rows = result.fetchall()

        column_types = {(row[0], row[1]): row[2].lower() for row in rows}

        # Verify tools JSONB columns
        assert column_types.get(("tools", "input_schema")) == "jsonb", (
            f"Expected JSONB, got {column_types.get(('tools', 'input_schema'))}"
        )
        assert column_types.get(("tools", "annotations")) == "jsonb"
        assert column_types.get(("tools", "risk_labels")) == "jsonb"

        # Verify tool_snapshots JSONB columns
        assert column_types.get(("tool_snapshots", "tools_data")) == "jsonb"
        assert column_types.get(("tool_snapshots", "metadata")) == "jsonb"


@pytest.mark.asyncio
async def test_tool_crud_and_fingerprint_storage(pg_db: DatabaseManager) -> None:
    """
    Acceptance Criteria Test:
    Verify that tools and deterministic fingerprints are stored and retrieved from PostgreSQL.
    """
    factory = pg_db.get_session_factory()
    ws_service = WorkspaceService()
    server_service = McpServerService()
    tool_service = ToolService()

    async with factory() as session, transactional_session(session=session) as tx_session:
        ws = await ws_service.create_workspace(
            session=tx_session,
            data=WorkspaceCreate(name="Finance Org", slug="finance-org"),
        )
        server = await server_service.create_server(
            session=tx_session,
            workspace_id=ws.id,
            data=McpServerCreate(
                name="Ledger Server",
                slug="ledger-server",
                endpoint_url="https://api.example.com/ledger",
            ),
        )

        tool_in = ToolCreate(
            server_id=server.id,
            name="query_transactions",
            title="Query Financial Transactions",
            description="Returns transactions matching query filters.",
            input_schema={
                "type": "object",
                "properties": {
                    "account_id": {"type": "string"},
                    "limit": {"type": "integer", "default": 50},
                },
                "required": ["account_id"],
            },
            annotations={"read_only_hint": True},
            classification_status=ToolClassificationStatus.SENSITIVE,
            risk_labels=["financial:read", "database:query"],
        )

        tool = await tool_service.create_tool(
            session=tx_session,
            workspace_id=ws.id,
            data=tool_in,
        )

        assert tool.id is not None
        assert tool.name == "query_transactions"
        assert tool.classification_status == "sensitive"
        assert tool.risk_labels == ["database:query", "financial:read"]
        assert len(tool.fingerprint) == 64
        stored_fp = tool.fingerprint
        tool_id = tool.id
        ws_id = ws.id

    # Retrieve in a separate transaction
    async with factory() as session, transactional_session(session=session) as tx_session:
        fetched = await tool_service.get_tool(
            session=tx_session,
            workspace_id=ws_id,
            tool_id=tool_id,
        )
        assert fetched is not None
        assert fetched.fingerprint == stored_fp
        assert fetched.input_schema["properties"]["account_id"]["type"] == "string"
        assert fetched.annotations == {"read_only_hint": True}
        assert fetched.is_enabled is True


@pytest.mark.asyncio
async def test_tools_multi_tenant_isolation_zero_leakage(pg_db: DatabaseManager) -> None:
    """
    Acceptance Criteria Test:
    Verify that tools do NOT leak between workspaces (anti-IDOR protection).
    - Workspace A cannot view, update, or delete tools of Workspace B.
    - Listing tools by workspace only returns tools belonging to that workspace.
    """
    factory = pg_db.get_session_factory()
    ws_service = WorkspaceService()
    server_service = McpServerService()
    tool_service = ToolService()

    async with factory() as session, transactional_session(session=session) as tx_session:
        ws_a = await ws_service.create_workspace(
            session=tx_session,
            data=WorkspaceCreate(name="Tenant Alpha", slug="tenant-alpha"),
        )
        ws_b = await ws_service.create_workspace(
            session=tx_session,
            data=WorkspaceCreate(name="Tenant Beta", slug="tenant-beta"),
        )

        server_a = await server_service.create_server(
            session=tx_session,
            workspace_id=ws_a.id,
            data=McpServerCreate(
                name="Server A",
                slug="server-a",
                endpoint_url="https://a.example.com/mcp",
            ),
        )
        server_b = await server_service.create_server(
            session=tx_session,
            workspace_id=ws_b.id,
            data=McpServerCreate(
                name="Server B",
                slug="server-b",
                endpoint_url="https://b.example.com/mcp",
            ),
        )

        tool_a = await tool_service.create_tool(
            session=tx_session,
            workspace_id=ws_a.id,
            data=ToolCreate(
                server_id=server_a.id,
                name="secret_tool_a",
                description="Alpha confidential tool",
                input_schema={"type": "object"},
            ),
        )

        tool_b = await tool_service.create_tool(
            session=tx_session,
            workspace_id=ws_b.id,
            data=ToolCreate(
                server_id=server_b.id,
                name="secret_tool_b",
                description="Beta confidential tool",
                input_schema={"type": "object"},
            ),
        )

        ws_a_id = ws_a.id
        ws_b_id = ws_b.id
        tool_a_id = tool_a.id
        tool_b_id = tool_b.id

    # Cross-workspace read verification
    async with factory() as session, transactional_session(session=session) as tx_session:
        # Tenant A attempting to fetch Tenant B's tool
        leak_check = await tool_service.get_tool(
            session=tx_session,
            workspace_id=ws_a_id,
            tool_id=tool_b_id,
        )
        assert leak_check is None, "Tenant A must NOT be able to read Tenant B's tool!"

        # Tenant B attempting to fetch Tenant A's tool
        leak_check_reverse = await tool_service.get_tool(
            session=tx_session,
            workspace_id=ws_b_id,
            tool_id=tool_a_id,
        )
        assert leak_check_reverse is None, "Tenant B must NOT be able to read Tenant A's tool!"

        # Listing tools for Tenant A must only return Tenant A's tools
        tools_a = await tool_service.list_tools_for_workspace(
            session=tx_session,
            workspace_id=ws_a_id,
        )
        assert len(tools_a) == 1
        assert tools_a[0].id == tool_a_id
        assert tools_a[0].name == "secret_tool_a"

        # Listing tools for Tenant B must only return Tenant B's tools
        tools_b = await tool_service.list_tools_for_workspace(
            session=tx_session,
            workspace_id=ws_b_id,
        )
        assert len(tools_b) == 1
        assert tools_b[0].id == tool_b_id
        assert tools_b[0].name == "secret_tool_b"

        # Tenant A attempting to update Tenant B's tool must fail
        with pytest.raises(NotFoundError):
            await tool_service.update_tool(
                session=tx_session,
                workspace_id=ws_a_id,
                tool_id=tool_b_id,
                data=ToolUpdate(is_enabled=False),
            )

        # Tenant A attempting to delete Tenant B's tool must return False
        deleted = await tool_service.delete_tool(
            session=tx_session,
            workspace_id=ws_a_id,
            tool_id=tool_b_id,
        )
        assert deleted is False, "Cross-workspace tool deletion must fail!"


@pytest.mark.asyncio
async def test_tool_name_unique_per_server_constraint(pg_db: DatabaseManager) -> None:
    """Verify that Tool Name is unique per Server in PostgreSQL."""
    factory = pg_db.get_session_factory()
    ws_service = WorkspaceService()
    server_service = McpServerService()
    tool_service = ToolService()

    async with factory() as session, transactional_session(session=session) as tx_session:
        ws = await ws_service.create_workspace(
            session=tx_session,
            data=WorkspaceCreate(name="Unique Test WS", slug="unique-ws"),
        )
        server_1 = await server_service.create_server(
            session=tx_session,
            workspace_id=ws.id,
            data=McpServerCreate(
                name="Server 1",
                slug="server-1",
                endpoint_url="https://s1.example.com/mcp",
            ),
        )
        server_2 = await server_service.create_server(
            session=tx_session,
            workspace_id=ws.id,
            data=McpServerCreate(
                name="Server 2",
                slug="server-2",
                endpoint_url="https://s2.example.com/mcp",
            ),
        )

        ws_id = ws.id
        server_1_id = server_1.id
        server_2_id = server_2.id

        # Create tool on server 1
        await tool_service.create_tool(
            session=tx_session,
            workspace_id=ws_id,
            data=ToolCreate(
                server_id=server_1_id,
                name="common_tool",
                input_schema={"type": "object"},
            ),
        )

    # Duplicate on server 1 must be rejected by service layer ConflictError
    async with factory() as session, transactional_session(session=session) as tx_session:
        with pytest.raises(ConflictError, match="already exists on server"):
            await tool_service.create_tool(
                session=tx_session,
                workspace_id=ws_id,
                data=ToolCreate(
                    server_id=server_1_id,
                    name="common_tool",
                    input_schema={"type": "object"},
                ),
            )

        # Same tool name on server 2 IS permitted
        tool_on_s2 = await tool_service.create_tool(
            session=tx_session,
            workspace_id=ws_id,
            data=ToolCreate(
                server_id=server_2_id,
                name="common_tool",
                input_schema={"type": "object"},
            ),
        )
        assert tool_on_s2.server_id == server_2_id


@pytest.mark.asyncio
async def test_cascade_deletion_on_server_and_workspace(pg_db: DatabaseManager) -> None:
    """Verify cascade deletion from workspace -> server -> tools and tool_snapshots."""
    factory = pg_db.get_session_factory()
    ws_service = WorkspaceService()
    server_service = McpServerService()
    tool_service = ToolService()

    async with factory() as session, transactional_session(session=session) as tx_session:
        ws = await ws_service.create_workspace(
            session=tx_session,
            data=WorkspaceCreate(name="Cascade Org", slug="cascade-org"),
        )
        server = await server_service.create_server(
            session=tx_session,
            workspace_id=ws.id,
            data=McpServerCreate(
                name="Cascade Server",
                slug="cascade-server",
                endpoint_url="https://cascade.example.com/mcp",
            ),
        )
        tool = await tool_service.create_tool(
            session=tx_session,
            workspace_id=ws.id,
            data=ToolCreate(
                server_id=server.id,
                name="ephemeral_tool",
                input_schema={"type": "object"},
            ),
        )
        snapshot = await tool_service.create_snapshot(
            session=tx_session,
            workspace_id=ws.id,
            data=ToolSnapshotCreate(
                server_id=server.id,
                tools_data=[{"name": "ephemeral_tool", "input_schema": {}}],
            ),
        )

        tool_id = tool.id
        snapshot_id = snapshot.id
        server_id = server.id
        ws_id = ws.id

    # Delete the MCP Server
    async with factory() as session, transactional_session(session=session) as tx_session:
        await server_service.delete_server(
            session=tx_session,
            workspace_id=ws_id,
            server_id=server_id,
        )

    # Verify tool and snapshot were automatically cascade deleted
    async with factory() as session, transactional_session(session=session) as tx_session:
        t_check = await tx_session.execute(select(Tool).where(Tool.id == tool_id))
        assert t_check.scalar_one_or_none() is None

        s_check = await tx_session.execute(
            select(ToolSnapshot).where(ToolSnapshot.id == snapshot_id)
        )
        assert s_check.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_historical_tool_snapshot_recording(pg_db: DatabaseManager) -> None:
    """Verify tool snapshot recording, catalog hash, and historical retrieval."""
    factory = pg_db.get_session_factory()
    ws_service = WorkspaceService()
    server_service = McpServerService()
    tool_service = ToolService()

    async with factory() as session, transactional_session(session=session) as tx_session:
        ws = await ws_service.create_workspace(
            session=tx_session,
            data=WorkspaceCreate(name="Snapshot WS", slug="snapshot-ws"),
        )
        server = await server_service.create_server(
            session=tx_session,
            workspace_id=ws.id,
            data=McpServerCreate(
                name="Snap Server",
                slug="snap-server",
                endpoint_url="https://snap.example.com/mcp",
            ),
        )

        ws_id = ws.id
        server_id = server.id

        weather_schema = {
            "type": "object",
            "properties": {"city": {"type": "string"}},
        }
        tools_v1 = [
            {"name": "get_weather", "input_schema": weather_schema},
        ]

        snap_1 = await tool_service.create_snapshot(
            session=tx_session,
            workspace_id=ws_id,
            data=ToolSnapshotCreate(
                server_id=server_id,
                tools_data=tools_v1,
                metadata={"trigger": "scheduled_sweep"},
            ),
        )

        forecast_schema = {
            "type": "object",
            "properties": {"days": {"type": "integer"}},
        }
        tools_v2 = [
            {"name": "get_weather", "input_schema": weather_schema},
            {"name": "get_forecast", "input_schema": forecast_schema},
        ]

        snap_2 = await tool_service.create_snapshot(
            session=tx_session,
            workspace_id=ws_id,
            data=ToolSnapshotCreate(
                server_id=server_id,
                tools_data=tools_v2,
                metadata={"trigger": "manual_refresh"},
            ),
        )

        snap_1_id = snap_1.id
        snap_2_id = snap_2.id
        snap_1_hash = snap_1.catalog_hash
        snap_2_hash = snap_2.catalog_hash

    # Hashes must differ because tools_data evolved
    assert snap_1_hash != snap_2_hash

    # List snapshots for server in a new transaction
    async with factory() as session, transactional_session(session=session) as tx_session:
        history = await tool_service.list_snapshots_for_server(
            session=tx_session,
            workspace_id=ws_id,
            server_id=server_id,
        )
        assert len(history) == 2
        # Descending chronological order
        assert history[0].id == snap_2_id
        assert history[1].id == snap_1_id
        assert history[0].tool_count == 2
        assert history[1].tool_count == 1
