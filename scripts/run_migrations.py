#!/usr/bin/env python3
"""
Database Migration Execution Script for Kolang ACP.

Executes Alembic migrations as a distinct deployment/startup phase.
Prevents automatic execution across multiple web worker processes or individual requests.

Usage:
    python scripts/run_migrations.py [--revision head] [--direction upgrade]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

import structlog
from alembic import command
from alembic.config import Config

from acp_core.common.settings import Settings, get_settings
from acp_core.db.session import DatabaseManager, reset_db_manager

logger = structlog.get_logger("kolang.migrations")


def redact_db_url(url: str) -> str:
    """Return a database URL with sensitive password redacted for safe logging."""
    try:
        parsed = urlsplit(url)
        if parsed.password:
            netloc = f"{parsed.username}:***@{parsed.hostname}"
            if parsed.port:
                netloc += f":{parsed.port}"
            return parsed._replace(netloc=netloc).geturl()
    except Exception as exc:
        logger.debug("migration.url_redaction_skipped", reason=str(exc))
    return url


async def wait_for_database(
    settings: Settings | None = None,
    retries: int = 15,
    delay_seconds: float = 2.0,
) -> bool:
    """Wait for database availability before attempting schema migration.

    Args:
        settings: Optional Settings instance. If None, loaded via get_settings().
        retries: Maximum connection attempts before failing.
        delay_seconds: Seconds to wait between attempts.

    Returns:
        True if connection succeeded within allowed attempts, False otherwise.
    """
    if settings is None:
        settings = get_settings()

    safe_url = redact_db_url(settings.database_url)
    logger.info("migration.check_db_connectivity", target=safe_url, max_attempts=retries)

    reset_db_manager()
    mgr = DatabaseManager()
    mgr.initialize(settings)

    for attempt in range(1, retries + 1):
        try:
            is_healthy = await mgr.ping()
            if is_healthy:
                logger.info(
                    "migration.database_ready",
                    attempt=attempt,
                    component="migration_runner",
                )
                await mgr.close()
                reset_db_manager()
                return True
        except Exception as exc:
            logger.warning(
                "migration.db_ping_failed",
                attempt=attempt,
                error=type(exc).__name__,
            )

        if attempt < retries:
            time.sleep(delay_seconds)

    await mgr.close()
    reset_db_manager()
    return False


def run_migration(
    direction: str = "upgrade",
    revision: str = "head",
    config_file: str | Path = "alembic.ini",
    db_url: str | None = None,
) -> None:
    """Execute Alembic migration synchronously using Alembic Command API.

    Args:
        direction: Migration action, either 'upgrade' or 'downgrade'.
        revision: Target revision identifier (e.g. 'head', 'base', or specific rev ID).
        config_file: Path to alembic.ini configuration file.
        db_url: Optional explicit database URL overriding settings.

    Raises:
        ValueError: If direction is not 'upgrade' or 'downgrade'.
    """
    cfg_path = Path(config_file).resolve()
    if not cfg_path.is_file():
        raise FileNotFoundError(f"Alembic configuration file not found at: {cfg_path}")

    alembic_cfg = Config(str(cfg_path))
    if db_url:
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        target_url = db_url
    else:
        settings = get_settings()
        target_url = settings.database_url

    safe_url = redact_db_url(target_url)

    logger.info(
        "migration.starting",
        direction=direction,
        target_revision=revision,
        database=safe_url,
    )

    if direction == "upgrade":
        command.upgrade(alembic_cfg, revision)
    elif direction == "downgrade":
        command.downgrade(alembic_cfg, revision)
    else:
        raise ValueError(f"Unsupported migration direction: {direction!r}")

    logger.info(
        "migration.completed",
        direction=direction,
        target_revision=revision,
    )


def main() -> int:
    """CLI entrypoint for standalone migration execution."""
    parser = argparse.ArgumentParser(
        description="Kolang Agent Control Plane — Database Migration Runner"
    )
    parser.add_argument(
        "--direction",
        choices=["upgrade", "downgrade"],
        default="upgrade",
        help="Direction of migration (default: upgrade)",
    )
    parser.add_argument(
        "--revision",
        default="head",
        help="Target revision (default: head for upgrade, base/rev for downgrade)",
    )
    parser.add_argument(
        "--config",
        default="alembic.ini",
        help="Path to alembic.ini (default: alembic.ini)",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=10,
        help="Number of database readiness ping retries (default: 10)",
    )
    parser.add_argument(
        "--wait-seconds",
        type=float,
        default=2.0,
        help="Delay between readiness attempts in seconds (default: 2.0)",
    )

    args = parser.parse_args()

    # Step 1: Wait for database readiness
    db_available = asyncio.run(
        wait_for_database(retries=args.retries, delay_seconds=args.wait_seconds)
    )
    if not db_available:
        logger.error("migration.failed_database_unreachable")
        return 1

    # Step 2: Run Alembic migration
    try:
        run_migration(
            direction=args.direction,
            revision=args.revision,
            config_file=args.config,
        )
        return 0
    except Exception as exc:
        logger.error(
            "migration.execution_failed",
            error=type(exc).__name__,
            message=str(exc),
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
