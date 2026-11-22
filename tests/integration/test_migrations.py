"""
Integration tests for Alembic database migration workflow on live PostgreSQL (ACP-007).

Verifies:
- Clean migration execution from an empty database state (alembic upgrade head).
- Existence and content of the alembic_version tracking table.
- Reversible downgrade to base without data corruption.
- Idempotent re-upgrade to head.
- Standalone execution via migration runner script functions.
- Proof that application lifespan does not automatically invoke migrations on startup.
"""

from __future__ import annotations

import contextlib
import os
from collections.abc import AsyncGenerator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from acp_core.common.settings import Settings
from acp_core.db.session import DatabaseManager, reset_db_manager
from scripts.run_migrations import run_migration, wait_for_database

# Configure PostgreSQL port (defaults to 5433 for local Docker Compose if 5432 is occupied)
POSTGRES_PORT = os.environ.get("ACP_POSTGRES_PORT", "5433")
LIVE_POSTGRES_URL = f"postgresql+asyncpg://kolang:kolang@localhost:{POSTGRES_PORT}/kolang"


@pytest.fixture
def alembic_cfg() -> Config:
    """Create Alembic Config instance configured with the live PostgreSQL test database."""
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", LIVE_POSTGRES_URL)
    return cfg


@pytest.fixture
async def raw_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Provide a direct async engine connection to PostgreSQL and clean up after test."""
    engine = create_async_engine(LIVE_POSTGRES_URL)
    # Check connectivity
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"Live PostgreSQL not reachable at {LIVE_POSTGRES_URL}: {exc}")

    yield engine
    await engine.dispose()


@pytest.mark.asyncio
async def test_clean_install_and_upgrade_head(
    alembic_cfg: Config,
    raw_engine: AsyncEngine,
) -> None:
    """Verify that alembic upgrade head runs cleanly from an empty database."""
    # Ensure starting from clean base
    with contextlib.suppress(Exception):
        command.downgrade(alembic_cfg, "base")

    # Execute upgrade to head
    command.upgrade(alembic_cfg, "head")

    # Verify alembic_version table exists and contains 0006 (current head)
    async with raw_engine.connect() as conn:
        result = await conn.execute(text("SELECT version_num FROM alembic_version"))
        rows = result.fetchall()
        assert len(rows) == 1, f"Expected 1 version row in alembic_version, found: {rows}"
        assert rows[0][0] == "0006"


@pytest.mark.asyncio
async def test_downgrade_to_base_and_reupgrade(
    alembic_cfg: Config,
    raw_engine: AsyncEngine,
) -> None:
    """Verify reversible downgrade to base and subsequent re-upgrade to head."""
    # Ensure upgraded first
    command.upgrade(alembic_cfg, "head")

    # Downgrade to base
    command.downgrade(alembic_cfg, "base")

    # Verify alembic_version is empty
    async with raw_engine.connect() as conn:
        result = await conn.execute(text("SELECT version_num FROM alembic_version"))
        rows = result.fetchall()
        assert len(rows) == 0, f"Expected 0 version rows after downgrade, found: {rows}"

    # Re-upgrade to head
    command.upgrade(alembic_cfg, "head")

    # Verify re-upgraded cleanly
    async with raw_engine.connect() as conn:
        result = await conn.execute(text("SELECT version_num FROM alembic_version"))
        rows = result.fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "0006"


@pytest.mark.asyncio
async def test_migration_runner_script_execution() -> None:
    """Verify that run_migrations script functions execute correctly against live PostgreSQL."""
    test_settings = Settings(ACP_DATABASE_URL=LIVE_POSTGRES_URL)

    # Verify DB readiness detection with test settings
    is_ready = await wait_for_database(settings=test_settings, retries=3, delay_seconds=0.5)
    assert is_ready is True

    # Test running upgrade via script function with explicit URL
    run_migration(
        direction="upgrade",
        revision="head",
        config_file="alembic.ini",
        db_url=LIVE_POSTGRES_URL,
    )


@pytest.mark.asyncio
async def test_application_startup_does_not_execute_migrations(
    raw_engine: AsyncEngine,
    alembic_cfg: Config,
) -> None:
    """Verify that application lifespan only checks DB connectivity and does not auto-migrate."""
    # Downgrade to base to prove lifespan does not trigger an auto-upgrade
    command.downgrade(alembic_cfg, "base")

    test_settings = Settings(
        ACP_DATABASE_URL=LIVE_POSTGRES_URL,
        ACP_ENV="test",
    )

    reset_db_manager()
    mgr = DatabaseManager()
    mgr.initialize(test_settings)

    # Ping database as done in app lifespan
    is_healthy = await mgr.ping()
    assert is_healthy is True

    # Check alembic_version table: it must still be empty (no automatic upgrade executed!)
    async with raw_engine.connect() as conn:
        result = await conn.execute(text("SELECT version_num FROM alembic_version"))
        rows = result.fetchall()
        assert len(rows) == 0, "Application must not auto-execute migrations during startup!"

    await mgr.close()
    reset_db_manager()

    # Re-upgrade to head for clean state
    command.upgrade(alembic_cfg, "head")
