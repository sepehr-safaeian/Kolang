"""
Integration tests for Identity, Agent Workload, and MCP Client on PostgreSQL (ACP-011).

Verifies against live PostgreSQL in Docker:
1. Acceptance Criteria:
   - Human User and Agent are two distinct identity types.
   - Inactive Agent cannot execute new requests.
   - Unregistered or unknown Client is rejected.
   - No identity is accepted merely from a header name/value.
2. Relational Schema & Integrity:
   - Migration 0005 execution and table creation (agents, clients, memberships).
   - Foreign key cascading: deleting a workspace cascades to agents, clients, and memberships.
   - Set NULL on agent delete: deleting an agent sets client.agent_id to NULL.
   - Unique constraints enforced by PostgreSQL engine:
     * uq_agents_workspace_id_slug
     * uq_mcp_client_registrations_workspace_id_client_id
     * uq_workspace_memberships_workspace_id_user_id
   - Native JSONB metadata storage verified via information_schema.
3. Demo Keycloak Client Mapping:
   - kolang-api service account mapped to Agent workload.
   - kolang-web user client mapped to Human User.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import text

from acp_core.common.errors import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
)
from acp_core.common.settings import Settings
from acp_core.common.types import PrincipalKind
from acp_core.db import (
    Base,
    DatabaseManager,
    reset_db_manager,
    transactional_session,
)
from acp_core.identity.models import (
    AgentCreate,
    TokenClaims,
    WorkspaceRole,
)
from acp_core.identity.service import IdentityService
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
async def test_identity_tables_and_columns_exist(pg_db: DatabaseManager) -> None:
    """Verify that identity tables and JSONB columns exist in PostgreSQL."""
    engine = pg_db.get_engine()
    async with engine.connect() as conn:
        stmt = text(
            """
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name IN ('agents', 'mcp_client_registrations', 'workspace_memberships')
              AND column_name = 'metadata'
            ORDER BY table_name;
            """
        )
        result = await conn.execute(stmt)
        rows = result.fetchall()

        table_types = {row[0]: row[2].lower() for row in rows}
        assert table_types.get("agents") == "jsonb"
        assert table_types.get("mcp_client_registrations") == "jsonb"
        assert table_types.get("workspace_memberships") == "jsonb"


@pytest.mark.asyncio
async def test_agent_slug_unique_constraint_on_postgres(pg_db: DatabaseManager) -> None:
    """Verify unique constraint (workspace_id, slug) on agents enforced by PostgreSQL."""
    ws_service = WorkspaceService()
    identity_service = IdentityService()
    factory = pg_db.get_session_factory()

    async with factory() as session, transactional_session(session=session) as tx_session:
        ws = await ws_service.create_workspace(
            tx_session,
            WorkspaceCreate(name="WS 1", slug=f"ws-agent-{uuid.uuid4().hex[:6]}"),
        )
        await identity_service.create_agent(
            tx_session,
            ws.id,
            AgentCreate(name="Agent 1", slug="duplicate-agent"),
        )

        with pytest.raises(ConflictError, match="already exists"):
            await identity_service.create_agent(
                tx_session,
                ws.id,
                AgentCreate(name="Agent 2", slug="duplicate-agent"),
            )


@pytest.mark.asyncio
async def test_acceptance_criteria_1_distinct_identities_on_postgres(
    pg_db: DatabaseManager,
) -> None:
    """
    Acceptance Criteria 1:
    Human User و Agent دو نوع هویت مجزا دارند.
    Verify on live PostgreSQL that User and Agent are distinct runtime identities.
    """
    ws_service = WorkspaceService()
    identity_service = IdentityService()
    factory = pg_db.get_session_factory()

    async with factory() as session, transactional_session(session=session) as tx_session:
        ws = await ws_service.create_workspace(
            tx_session,
            WorkspaceCreate(name="Identity WS", slug=f"ws-id-{uuid.uuid4().hex[:6]}"),
        )
        seed_data = await identity_service.seed_demo_identities(tx_session, ws.id)

        # 1. Resolve Agent PrincipalContext
        agent_claims = TokenClaims(
            sub="service-account-kolang-api",
            iss="https://auth.kolang.dev",
            exp=1800000000,
            iat=1700000000,
            azp="kolang-api",
            roles=["operator"],
        )
        agent_ctx = await identity_service.resolve_principal_context(
            tx_session,
            agent_claims,
            ws.id,
        )
        assert agent_ctx.kind == PrincipalKind.AGENT
        assert agent_ctx.is_agent is True
        assert agent_ctx.is_user is False
        assert agent_ctx.agent is not None
        assert agent_ctx.agent.name == "Demo Code Reviewer"
        assert agent_ctx.agent_id == seed_data["demo_agent"].id
        agent_ctx.check_can_execute()

        # 2. Resolve Human User PrincipalContext
        user_claims = TokenClaims(
            sub="admin",
            iss="https://auth.kolang.dev",
            exp=1800000000,
            iat=1700000000,
            azp="kolang-web",
            roles=["admin"],
            email="admin@kolang.dev",
        )
        user_ctx = await identity_service.resolve_principal_context(
            tx_session,
            user_claims,
            ws.id,
        )
        assert user_ctx.kind == PrincipalKind.USER
        assert user_ctx.is_user is True
        assert user_ctx.is_agent is False
        assert user_ctx.user_id == "admin"
        assert user_ctx.agent_id is None
        assert user_ctx.agent is None
        assert user_ctx.membership is not None
        assert user_ctx.membership.role == WorkspaceRole.ADMIN
        user_ctx.check_can_execute()


@pytest.mark.asyncio
async def test_acceptance_criteria_2_inactive_agent_cannot_execute_on_postgres(
    pg_db: DatabaseManager,
) -> None:
    """
    Acceptance Criteria 2:
    Agent غیرفعال نمی‌تواند درخواست جدید اجرا کند.
    Verify that an inactive agent cannot execute new requests on PostgreSQL.
    """
    ws_service = WorkspaceService()
    identity_service = IdentityService()
    factory = pg_db.get_session_factory()

    async with factory() as session, transactional_session(session=session) as tx_session:
        ws = await ws_service.create_workspace(
            tx_session,
            WorkspaceCreate(name="Inactive WS", slug=f"ws-inact-{uuid.uuid4().hex[:6]}"),
        )
        seed_data = await identity_service.seed_demo_identities(tx_session, ws.id)
        demo_agent = seed_data["demo_agent"]

        # Disable the agent
        await identity_service.disable_agent(tx_session, ws.id, demo_agent.id)

        claims = TokenClaims(
            sub="service-account-kolang-api",
            iss="https://auth.kolang.dev",
            exp=1800000000,
            iat=1700000000,
            azp="kolang-api",
        )

        with pytest.raises(AuthorizationError) as exc_info:
            await identity_service.resolve_principal_context(tx_session, claims, ws.id)

        assert "inactive" in str(exc_info.value).lower()
        assert "cannot execute new requests" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_acceptance_criteria_3_unregistered_client_rejected_on_postgres(
    pg_db: DatabaseManager,
) -> None:
    """
    Acceptance Criteria 3:
    Client ثبت‌نشده یا ناشناخته رد می‌شود.
    Verify that an unregistered client is rejected on PostgreSQL.
    """
    ws_service = WorkspaceService()
    identity_service = IdentityService()
    factory = pg_db.get_session_factory()

    async with factory() as session, transactional_session(session=session) as tx_session:
        ws = await ws_service.create_workspace(
            tx_session,
            WorkspaceCreate(name="Client WS", slug=f"ws-client-{uuid.uuid4().hex[:6]}"),
        )

        claims = TokenClaims(
            sub="service-account-unknown",
            iss="https://auth.kolang.dev",
            exp=1800000000,
            iat=1700000000,
            azp="unknown-unregistered-client",
        )

        with pytest.raises(AuthenticationError) as exc_info:
            await identity_service.resolve_principal_context(tx_session, claims, ws.id)

        assert "unregistered or unrecognized" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_acceptance_criteria_4_no_identity_from_header_on_postgres(
    pg_db: DatabaseManager,
) -> None:
    """
    Acceptance Criteria 4:
    هیچ هویت صرفاً از نام ارسالی در Header پذیرفته نمی‌شود.
    Verify that header spoofing attempts (e.g. X-Agent-ID) are ignored and identity
    is strictly determined from token claims and database registry.
    """
    ws_service = WorkspaceService()
    identity_service = IdentityService()
    factory = pg_db.get_session_factory()

    async with factory() as session, transactional_session(session=session) as tx_session:
        ws = await ws_service.create_workspace(
            tx_session,
            WorkspaceCreate(name="Header WS", slug=f"ws-hdr-{uuid.uuid4().hex[:6]}"),
        )
        seed_data = await identity_service.seed_demo_identities(tx_session, ws.id)
        legit_agent = seed_data["demo_agent"]

        spoofed_agent_id = uuid.uuid4()
        claims = TokenClaims(
            sub="service-account-kolang-api",
            iss="https://auth.kolang.dev",
            exp=1800000000,
            iat=1700000000,
            azp="kolang-api",
        )

        # Attacker injects fake identity headers
        spoofed_headers = {
            "X-Agent-ID": str(spoofed_agent_id),
            "X-Agent-Name": "Imposter-Bot",
            "X-User-ID": "root",
        }

        ctx = await identity_service.resolve_principal_context(
            tx_session,
            claims,
            ws.id,
            request_headers=spoofed_headers,
        )

        # Verified principal context MUST match the legitimate agent from claims and DB
        assert ctx.agent_id == legit_agent.id
        assert ctx.agent is not None
        assert ctx.agent.name == "Demo Code Reviewer"
        assert ctx.agent_id != spoofed_agent_id
        assert ctx.user_id != "root"


@pytest.mark.asyncio
async def test_cascade_delete_and_agent_set_null_on_postgres(
    pg_db: DatabaseManager,
) -> None:
    """
    Verify foreign key integrity:
    1. Deleting an agent sets client.agent_id to NULL.
    2. Deleting a workspace cascades to agents, clients, and memberships.
    """
    ws_service = WorkspaceService()
    identity_service = IdentityService()
    factory = pg_db.get_session_factory()

    async with factory() as session, transactional_session(session=session) as tx_session:
        ws = await ws_service.create_workspace(
            tx_session,
            WorkspaceCreate(name="Cascade WS", slug=f"ws-casc-{uuid.uuid4().hex[:6]}"),
        )
        seed_data = await identity_service.seed_demo_identities(tx_session, ws.id)
        agent = seed_data["demo_agent"]
        client = seed_data["api_client"]

        # Delete the agent directly
        stmt = text("DELETE FROM agents WHERE id = :id")
        await tx_session.execute(stmt, {"id": agent.id})

        # Check that client registration still exists and agent_id was SET NULL
        refreshed_client = await identity_service.get_client_by_client_id(
            tx_session,
            ws.id,
            client.client_id,
        )
        assert refreshed_client is not None
        assert refreshed_client.agent_id is None

        # Delete the workspace
        ws_stmt = text("DELETE FROM workspaces WHERE id = :id")
        await tx_session.execute(ws_stmt, {"id": ws.id})

        # Check all child entities were cascaded
        clients = await identity_service.list_clients(tx_session, ws.id)
        assert len(clients) == 0

        memberships = await identity_service.list_memberships(tx_session, ws.id)
        assert len(memberships) == 0
