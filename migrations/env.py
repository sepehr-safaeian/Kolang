from __future__ import annotations

import asyncio
import concurrent.futures
import contextlib
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

import acp_core.registry.models
import acp_core.workspaces.models  # noqa: F401
from acp_core.common.settings import get_settings
from acp_core.db.base import Base

# Alembic Config object, which provides access to the values within the .ini file in use.
try:
    config = context.config
except (NameError, AttributeError):
    config = None

# Interpret the config file for Python logging.
if config is not None and config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Model MetaData target for 'autogenerate' support
target_metadata = Base.metadata


def get_url() -> str:
    """Resolve database connection URL for migrations.

    Priority:
    1. Alembic runtime argument (-x url=...)
    2. Alembic config ini option (sqlalchemy.url)
    3. Application settings (ACP_DATABASE_URL / DATABASE_URL)
    """
    with contextlib.suppress(NameError, AttributeError):
        x_args = context.get_x_argument(as_dictionary=True)
        url_arg = x_args.get("url")
        if url_arg:
            return str(url_arg)

    if config is not None:
        ini_url = config.get_main_option("sqlalchemy.url")
        if ini_url:
            return ini_url

    settings = get_settings()
    return settings.database_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode without an active DB connection.

    Generates SQL scripts against literal binds without requiring a live database.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations synchronously inside the connection context."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with an async SQLAlchemy engine."""
    url = get_url()
    configuration = config.get_section(config.config_ini_section, {}) if config is not None else {}
    configuration["sqlalchemy.url"] = url

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entrypoint for online migrations using asyncio.

    Safely handles both CLI environments and active event loops (e.g. async test runners).
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, run_async_migrations())
            future.result()
    else:
        asyncio.run(run_async_migrations())


with contextlib.suppress(NameError, AttributeError):
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        run_migrations_online()
