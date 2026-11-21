"""
Database engine, connection pooling, and SQLAlchemy session lifecycle management for Kolang.

Provides centralized AsyncEngine, connection pool configuration, session factory,
FastAPI dependency injection (get_db_session) with guaranteed cleanup, and
transaction management at service boundaries (transactional_session).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from acp_core.common.redaction import redact_exception
from acp_core.common.settings import Settings, get_settings

logger = structlog.get_logger()


class DatabaseManager:
    """
    Centralized manager for database AsyncEngine and sessionmaker lifecycle.

    Maintains a single configured engine with connection pooling and
    provides session factories for request dependencies and service transactions.
    """

    def __init__(self) -> None:
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None
        self._settings: Settings | None = None
        self._is_initialized: bool = False

    @property
    def is_initialized(self) -> bool:
        """Return True if the engine and session factory have been initialized."""
        return self._is_initialized and self._engine is not None

    def initialize(self, settings: Settings | None = None) -> None:
        """
        Initialize the AsyncEngine and session factory with connection pool settings.

        Args:
            settings: Optional Settings instance. Defaults to get_settings().
        """
        current_settings = settings or get_settings()
        self._settings = current_settings

        raw_url = current_settings.database_url
        # Normalize postgresql:// or postgres:// to postgresql+asyncpg://
        if raw_url.startswith("postgresql://"):
            url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif raw_url.startswith("postgres://"):
            url = raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
        else:
            url = raw_url

        engine_kwargs: dict[str, Any] = {
            "echo": current_settings.database_echo,
            "future": True,
        }

        # Configure connection pooling based on dialect
        if url.startswith("sqlite"):
            # SQLite does not support standard QueuePool overflow arguments
            engine_kwargs["connect_args"] = {"check_same_thread": False}
        else:
            # PostgreSQL / asyncpg connection pool configuration
            engine_kwargs.update(
                {
                    "pool_size": current_settings.database_pool_size,
                    "max_overflow": current_settings.database_max_overflow,
                    "pool_timeout": current_settings.database_pool_timeout,
                    "pool_recycle": current_settings.database_pool_recycle,
                    "pool_pre_ping": True,
                }
            )

        self._engine = create_async_engine(url, **engine_kwargs)
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        self._is_initialized = True

        logger.info(
            "database.initialized",
            event_name="database.initialized",
            component="database",
            url=Settings.sanitize_url(url),
            pool_size=current_settings.database_pool_size,
            max_overflow=current_settings.database_max_overflow,
        )

    async def close(self) -> None:
        """Dispose of the database engine and release all pooled connections."""
        if self._engine is not None:
            logger.info(
                "database.closing",
                event_name="database.closing",
                component="database",
            )
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            self._is_initialized = False

    def get_engine(self) -> AsyncEngine:
        """Return the active AsyncEngine, initializing it if necessary."""
        if self._engine is None:
            self.initialize(self._settings)
        assert self._engine is not None
        return self._engine

    def get_session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Return the active async_sessionmaker, initializing it if necessary."""
        if self._session_factory is None:
            self.initialize(self._settings)
        assert self._session_factory is not None
        return self._session_factory

    async def ping(self) -> bool:
        """
        Execute a quick lightweight query (SELECT 1) to verify database connectivity.

        Returns:
            True if database responded successfully, False otherwise.
        """
        try:
            engine = self.get_engine()
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as exc:
            logger.warning(
                "database.ping_failed",
                event_name="database.ping_failed",
                component="database",
                error=redact_exception(exc),
            )
            return False


# Global singleton database manager instance
_db_manager = DatabaseManager()


def get_db_manager() -> DatabaseManager:
    """Return the global DatabaseManager singleton."""
    return _db_manager


def get_db_engine() -> AsyncEngine:
    """Return the global AsyncEngine instance."""
    return _db_manager.get_engine()


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the global async_sessionmaker factory."""
    return _db_manager.get_session_factory()


async def init_db(settings: Settings | None = None) -> None:
    """Initialize the database engine and session factory."""
    _db_manager.initialize(settings)


async def close_db() -> None:
    """Close the database engine and release pool connections."""
    await _db_manager.close()


async def ping_db() -> bool:
    """Probe database connectivity via lightweight SELECT 1 query."""
    return await _db_manager.ping()


def reset_db_manager() -> None:
    """Reset the internal database manager state (used primarily for test isolation)."""
    global _db_manager
    _db_manager = DatabaseManager()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency yielding a scoped AsyncSession per request.

    Guarantees:
    - Session is instantiated from the central session factory.
    - Session rolls back any uncommitted changes on unhandled exceptions.
    - Session is strictly closed in the finally block, preventing connection leaks.
    """
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


@asynccontextmanager
async def transactional_session(
    session: AsyncSession | None = None,
) -> AsyncGenerator[AsyncSession, None]:
    """
    Asynchronous context manager for transaction management at explicit service boundaries.

    Usage:
        async with transactional_session() as session:
            # perform database operations
            # commits automatically if no error occurs
            # rolls back automatically on exception

    If an existing session is passed, commits upon block success and rolls back on exception,
    without closing the caller's session.
    If no session is passed, opens a new session, commits upon block success, rolls back on
    exception, and guarantees session closure in the finally block.
    """
    if session is not None:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
    else:
        factory = get_session_factory()
        new_session = factory()
        try:
            yield new_session
            await new_session.commit()
        except Exception:
            await new_session.rollback()
            raise
        finally:
            await new_session.close()
