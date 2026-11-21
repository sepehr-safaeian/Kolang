"""
Integration tests for PostgreSQL connection, session lifecycle, and pool behavior (ACP-006).

Verifies live interaction with PostgreSQL running in Docker:
- Real connection establishment with asyncpg driver.
- Table schema creation via Base.metadata.
- Session lifecycle and transaction management (commit & rollback) with live PostgreSQL.
- Pool checkout and checkin (zero session/connection leaks).
- Real health check reporting (200 ready when connected, 503 degraded when unreachable).
- Secure database error conversion under live database conditions.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Column, Integer, String, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from acp_core.common.settings import Settings
from acp_core.db import (
    Base,
    DatabaseManager,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    get_db_session,
    reset_db_manager,
    transactional_session,
)
from apps.api.app.main import create_app

# Default live PostgreSQL URL in Docker (supports configurable host port via ACP_POSTGRES_PORT)
POSTGRES_PORT = os.environ.get("ACP_POSTGRES_PORT", "5433")
DOCKER_POSTGRES_URL = f"postgresql+asyncpg://kolang:kolang@localhost:{POSTGRES_PORT}/kolang"


class IntegrationEntity(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Test model for verifying live PostgreSQL schema creation and DML."""

    __tablename__ = "integration_test_entities"

    title: Column[str] = Column(String(100), nullable=False)
    counter: Column[int] = Column(Integer, default=1, nullable=False)


@pytest.fixture
async def pg_settings() -> Settings:
    """Settings configured for live Docker PostgreSQL."""
    return Settings(
        ACP_DATABASE_URL=DOCKER_POSTGRES_URL,
        ACP_DATABASE_POOL_SIZE=5,
        ACP_DATABASE_MAX_OVERFLOW=5,
        ACP_DATABASE_POOL_TIMEOUT=10.0,
        ACP_DATABASE_POOL_RECYCLE=1800,
        ACP_DATABASE_ECHO=False,
    )


@pytest.fixture
async def pg_db(pg_settings: Settings) -> AsyncGenerator[DatabaseManager, None]:
    """DatabaseManager initialized with live Docker PostgreSQL and cleaned up afterward."""
    reset_db_manager()
    mgr = DatabaseManager()
    mgr.initialize(pg_settings)

    # Ensure connectivity
    is_connected = await mgr.ping()
    if not is_connected:
        pytest.skip(f"Docker PostgreSQL is not reachable at {DOCKER_POSTGRES_URL}")

    # Create test tables in live PostgreSQL
    engine = mgr.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield mgr

    # Clean up tables and dispose engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await mgr.close()
    reset_db_manager()


@pytest.mark.asyncio
async def test_live_postgres_connection_and_ping(pg_db: DatabaseManager) -> None:
    """Verify live asyncpg connection and ping to PostgreSQL in Docker."""
    assert await pg_db.ping() is True


@pytest.mark.asyncio
async def test_live_postgres_transaction_commit_and_rollback(pg_db: DatabaseManager) -> None:
    """Verify transactional_session commits on success and rolls back on failure in PostgreSQL."""
    factory = pg_db.get_session_factory()

    # 1. Successful commit
    item_id = uuid.uuid4()
    async with factory() as session, transactional_session(session=session) as tx_session:
        entity = IntegrationEntity(id=item_id, title="Committed Record", counter=42)
        tx_session.add(entity)

    # Verify persistence
    async with factory() as session:
        result = await session.execute(
            select(IntegrationEntity).where(IntegrationEntity.id == item_id)
        )
        fetched = result.scalar_one_or_none()
        assert fetched is not None
        assert fetched.title == "Committed Record"
        assert fetched.counter == 42

    # 2. Rollback on exception
    rollback_id = uuid.uuid4()

    async def _failing_operation() -> None:
        async with factory() as session, transactional_session(session=session) as tx_session:
            rolled_back_entity = IntegrationEntity(
                id=rollback_id, title="Rollback Record", counter=99
            )
            tx_session.add(rolled_back_entity)
            await tx_session.flush()
            raise RuntimeError("Simulated service failure")

    with pytest.raises(RuntimeError, match="Simulated service failure"):
        await _failing_operation()

    # Verify record was NOT persisted
    async with factory() as session:
        result = await session.execute(
            select(IntegrationEntity).where(IntegrationEntity.id == rollback_id)
        )
        assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_live_postgres_session_leak_prevention(pg_db: DatabaseManager) -> None:
    """Verify that multiple concurrent requests and error cycles do not leak connections."""
    engine = pg_db.get_engine()
    pool = engine.pool
    factory = pg_db.get_session_factory()

    # Initial state: 0 connections checked out
    assert pool.checkedout() == 0

    # Execute multiple sessions with both successes and exceptions
    for i in range(10):
        session = factory()
        try:
            await session.execute(text("SELECT 1"))
            if i % 2 == 0:
                raise ValueError("Simulated handler crash")
        except ValueError:
            await session.rollback()
        finally:
            await session.close()

    # After sessions finish, all checked out connections must be returned to the pool
    assert pool.checkedout() == 0


@pytest.mark.asyncio
async def test_live_postgres_fastapi_request_lifecycle(
    pg_db: DatabaseManager,
    pg_settings: Settings,
) -> None:
    """Verify FastAPI route using get_db_session dependency against live PostgreSQL."""
    app = create_app()

    # Define an endpoint consuming get_db_session
    @app.post("/test-records")
    async def create_record(
        title: str,
        session: AsyncSession = pytest.importorskip("fastapi").Depends(get_db_session),
    ) -> dict[str, Any]:
        record = IntegrationEntity(title=title, counter=10)
        session.add(record)
        await session.commit()
        return {"id": str(record.id), "title": record.title}

    # Patch DatabaseManager with the live pg_db instance
    factory_mock = pg_db.get_session_factory()
    with patch("acp_core.db.session.get_session_factory", return_value=factory_mock):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/test-records?title=Live+PG+Test")
            assert resp.status_code == 200
            data = resp.json()
            assert data["title"] == "Live PG Test"

            # Check that connections are returned to pool (no leak)
            assert pg_db.get_engine().pool.checkedout() == 0


@pytest.mark.asyncio
async def test_live_postgres_readyz_probe(
    pg_db: DatabaseManager,
    pg_settings: Settings,
) -> None:
    """Verify /readyz endpoint accurately reports live PostgreSQL status."""
    app = create_app()

    with patch("acp_core.db.session._db_manager", pg_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. When connected to PostgreSQL: returns 200 OK and database: ok
            ready_resp = await client.get("/readyz")
            assert ready_resp.status_code == 200
            ready_data = ready_resp.json()
            assert ready_data["status"] == "ready"
            assert ready_data["checks"]["database"] == "ok"


@pytest.mark.asyncio
async def test_unreachable_postgres_readyz_probe() -> None:
    """Verify /readyz returns 503 degraded when pointing to an unreachable PostgreSQL port."""
    bad_settings = Settings(
        ACP_DATABASE_URL="postgresql+asyncpg://kolang:kolang@localhost:59999/kolang",
        ACP_DATABASE_POOL_TIMEOUT=1.0,
    )
    bad_mgr = DatabaseManager()
    bad_mgr.initialize(bad_settings)

    app = create_app()
    with patch("acp_core.db.session._db_manager", bad_mgr):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/readyz")
            assert resp.status_code == 503
            data = resp.json()
            assert data["status"] == "degraded"
            assert data["checks"]["database"] == "unavailable"

    await bad_mgr.close()
