"""
Unit tests for Kolang database layer, session lifecycle, and transaction management (ACP-006).

Verifies:
- Centralized DatabaseManager, AsyncEngine, and sessionmaker initialization.
- Connection pool configuration parameters.
- FastAPI session dependency lifecycle (get_db_session) with guaranteed cleanup.
- Session leak prevention on successful execution and exceptions.
- Service boundary transaction management (transactional_session).
- Safe public database error conversion (SQLAlchemyError to standardized ErrorResponse).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Column, Integer, String
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from acp_core.common.errors import DatabaseConnectionError, DatabaseError
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


# Sample dummy model for verifying metadata and DeclarativeBase mixins
class DummyEntity(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "dummy_entities"

    name: Column[str] = Column(String(50), nullable=False)
    count: Column[int] = Column(Integer, default=0, nullable=False)


@pytest.fixture(autouse=True)
def _reset_db() -> None:
    """Reset database manager before and after each test."""
    reset_db_manager()
    yield
    reset_db_manager()


# ── DeclarativeBase and Mixins ───────────────────────────────────────────────


def test_declarative_base_and_mixins() -> None:
    """Verify that Base, UUIDPrimaryKeyMixin, and TimestampMixin configure properly."""
    assert "dummy_entities" in Base.metadata.tables
    table = Base.metadata.tables["dummy_entities"]

    assert "id" in table.c
    assert "created_at" in table.c
    assert "updated_at" in table.c
    assert "name" in table.c
    assert "count" in table.c


# ── DatabaseManager & Pool Configuration ─────────────────────────────────────


def test_database_manager_pool_configuration() -> None:
    """Verify DatabaseManager configures engine with pool options from settings."""
    custom_settings = Settings(
        ACP_DATABASE_URL="postgresql+asyncpg://user:pass@db.internal:5432/kolang_test",
        ACP_DATABASE_POOL_SIZE=15,
        ACP_DATABASE_MAX_OVERFLOW=25,
        ACP_DATABASE_POOL_TIMEOUT=45.0,
        ACP_DATABASE_POOL_RECYCLE=3600,
        ACP_DATABASE_ECHO=False,
    )
    mgr = DatabaseManager()
    mgr.initialize(custom_settings)

    assert mgr.is_initialized is True
    engine = mgr.get_engine()
    assert engine is not None

    # Verify pool configuration
    pool = engine.pool
    assert pool.size() == 15
    assert pool._max_overflow == 25
    assert pool._timeout == 45.0
    assert pool._recycle == 3600
    assert pool._pre_ping is True


@pytest.mark.asyncio
async def test_database_manager_close() -> None:
    """Verify closing DatabaseManager disposes of the engine cleanly."""
    mgr = DatabaseManager()
    mgr.initialize()
    assert mgr.is_initialized is True

    await mgr.close()
    assert mgr.is_initialized is False
    assert mgr._engine is None
    assert mgr._session_factory is None


@pytest.mark.asyncio
async def test_ping_db_success_and_failure() -> None:
    """Verify ping_db returns True on successful query and False on connection error."""
    mgr = DatabaseManager()

    # Success case
    with patch.object(mgr, "get_engine") as mock_get_engine:
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = None
        mock_engine = MagicMock()
        mock_engine.connect.return_value.__aenter__.return_value = mock_conn
        mock_get_engine.return_value = mock_engine

        assert await mgr.ping() is True
        mock_conn.execute.assert_awaited_once()

    # Failure case
    with patch.object(mgr, "get_engine") as mock_get_engine:
        mock_engine = MagicMock()
        conn_err = OperationalError("statement", {}, Exception("Connection refused"))
        mock_engine.connect.side_effect = conn_err
        mock_get_engine.return_value = mock_engine

        assert await mgr.ping() is False


# ── Session Lifecycle & Leak Prevention (get_db_session) ─────────────────────


@pytest.mark.asyncio
async def test_get_db_session_success_lifecycle() -> None:
    """Verify get_db_session creates session and guarantees closure upon completion."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_factory = MagicMock(return_value=mock_session)

    with patch("acp_core.db.session.get_session_factory", return_value=mock_factory):
        session_gen = get_db_session()
        yielded_session = await anext(session_gen)

        assert yielded_session is mock_session
        assert mock_session.close.call_count == 0

        # Terminate generator cleanly
        with pytest.raises(StopAsyncIteration):
            await anext(session_gen)

        mock_session.close.assert_awaited_once()
        assert mock_session.rollback.call_count == 0


@pytest.mark.asyncio
async def test_get_db_session_exception_rollback_and_leak_prevention() -> None:
    """Verify get_db_session rolls back and strictly closes session when an exception occurs."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_factory = MagicMock(return_value=mock_session)

    with patch("acp_core.db.session.get_session_factory", return_value=mock_factory):
        session_gen = get_db_session()
        yielded_session = await anext(session_gen)
        assert yielded_session is mock_session

        # Simulate unhandled exception in request handler
        with pytest.raises(RuntimeError, match="Handler failure"):
            await session_gen.athrow(RuntimeError("Handler failure"))

        # Crucial: verify rollback was called AND session was closed (no leak)
        mock_session.rollback.assert_awaited_once()
        mock_session.close.assert_awaited_once()


# ── Service Boundary Transactions (transactional_session) ───────────────────


@pytest.mark.asyncio
async def test_transactional_session_commit_on_success() -> None:
    """Verify transactional_session commits and closes when block executes without error."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_factory = MagicMock(return_value=mock_session)

    with patch("acp_core.db.session.get_session_factory", return_value=mock_factory):
        async with transactional_session() as session:
            assert session is mock_session

        mock_session.commit.assert_awaited_once()
        mock_session.rollback.assert_not_called()
        mock_session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_transactional_session_rollback_on_error() -> None:
    """Verify transactional_session rolls back and closes when block raises an exception."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_factory = MagicMock(return_value=mock_session)

    async def _fail_transaction() -> None:
        async with transactional_session() as session:
            assert session is mock_session
            raise ValueError("Domain validation failure")

    with patch("acp_core.db.session.get_session_factory", return_value=mock_factory):
        with pytest.raises(ValueError, match="Domain validation failure"):
            await _fail_transaction()

        mock_session.commit.assert_not_called()
        mock_session.rollback.assert_awaited_once()
        mock_session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_transactional_session_reuse_existing_session() -> None:
    """Verify passing an existing session commits without premature closure."""
    existing_session = AsyncMock(spec=AsyncSession)

    async with transactional_session(session=existing_session) as session:
        assert session is existing_session

    existing_session.commit.assert_awaited_once()
    existing_session.close.assert_not_called()


# ── Safe Database Error Conversion & Redaction ───────────────────────────────


@pytest.mark.asyncio
async def test_safe_sqlalchemy_error_conversion_in_api() -> None:
    """
    Verify that unhandled SQLAlchemy errors in routes are safely caught,
    redacted, and converted to standardized 500 JSON responses without
    leaking internal tables, queries, or database credentials.
    """
    app = create_app()

    # Route that triggers a low-level DBAPI error with sensitive query details
    @app.get("/test-db-error")
    async def route_raising_db_error() -> None:
        raw_error = DBAPIError(
            "SELECT * FROM confidential_users WHERE password_hash = 'secret123';",
            {},
            Exception("FATAL: password authentication failed for user 'internal_admin'"),
        )
        raise raw_error

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/test-db-error",
            headers={"X-Request-ID": "req-db-leak-check"},
        )

        assert response.status_code == 500
        data = response.json()

        # Machine-readable error code and generic message
        assert data["error"] == "DATABASE_ERROR"
        assert data["message"] == "A database error occurred."
        assert data["request_id"] == "req-db-leak-check"
        assert data["details"] == {}

        # Critical: ensure zero leaks of sensitive query, table name, or credentials
        raw_text = response.text
        assert "confidential_users" not in raw_text
        assert "password_hash" not in raw_text
        assert "secret123" not in raw_text
        assert "internal_admin" not in raw_text


@pytest.mark.asyncio
async def test_database_error_hierarchy() -> None:
    """Verify DatabaseError and DatabaseConnectionError status codes and attributes."""
    err = DatabaseError("Custom safe DB error", details={"entity": "tool"})
    assert err.code == "DATABASE_ERROR"
    assert err.status_code == 500
    assert err.message == "Custom safe DB error"
    assert err.details == {"entity": "tool"}

    conn_err = DatabaseConnectionError()
    assert conn_err.code == "DATABASE_CONNECTION_ERROR"
    assert conn_err.status_code == 503
    assert conn_err.message == "Database service is currently unavailable."
