"""
Kolang Database Package.

Provides SQLAlchemy 2.0 DeclarativeBase, centralized connection pooling,
session factory, FastAPI dependency injection, and transaction context managers.
"""

from __future__ import annotations

from acp_core.db.base import (
    Base,
    TenantScopedMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    WorkspaceScopedMixin,
)
from acp_core.db.session import (
    DatabaseManager,
    close_db,
    get_db_engine,
    get_db_manager,
    get_db_session,
    get_session_factory,
    init_db,
    ping_db,
    reset_db_manager,
    transactional_session,
)

__all__ = [
    "Base",
    "DatabaseManager",
    "TenantScopedMixin",
    "TimestampMixin",
    "UUIDPrimaryKeyMixin",
    "WorkspaceScopedMixin",
    "close_db",
    "get_db_engine",
    "get_db_manager",
    "get_db_session",
    "get_session_factory",
    "init_db",
    "ping_db",
    "reset_db_manager",
    "transactional_session",
]
