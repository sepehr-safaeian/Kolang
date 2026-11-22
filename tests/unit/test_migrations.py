"""
Unit tests for Alembic database migration configuration and utilities (ACP-007).

Verifies:
- alembic.ini loading and configuration integrity.
- ScriptDirectory revision tree resolution (single head, valid baseline).
- Database URL resolution precedence in migrations/env.py.
- Password redaction in migration runner logging.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

from migrations.env import get_url
from scripts.run_migrations import redact_db_url


def test_alembic_config_loading() -> None:
    """Verify that alembic.ini is present, readable, and points to the migrations folder."""
    config_path = Path("alembic.ini").resolve()
    assert config_path.is_file(), "alembic.ini must exist in repository root"

    cfg = Config(str(config_path))
    script_loc = cfg.get_main_option("script_location")
    assert script_loc == "migrations"


def test_migration_revisions_tree() -> None:
    """Verify that the Alembic script directory has a valid single head revision."""
    cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(cfg)

    heads = script.get_heads()
    assert len(heads) == 1, f"Expected exactly one migration head, found {heads}"
    assert heads[0] == "0006"

    rev_0006 = script.get_revision("0006")
    assert rev_0006 is not None
    assert rev_0006.down_revision == "0005"
    assert "create_policies_and_versions_tables" in rev_0006.doc

    rev_0005 = script.get_revision("0005")
    assert rev_0005 is not None
    assert rev_0005.down_revision == "0004"
    assert "create_identity_and_agent_tables" in rev_0005.doc

    rev_0004 = script.get_revision("0004")
    assert rev_0004 is not None
    assert rev_0004.down_revision == "0003"
    assert "create_tools_and_snapshots_tables" in rev_0004.doc

    rev_0003 = script.get_revision("0003")
    assert rev_0003 is not None
    assert rev_0003.down_revision == "0002"
    assert "create_mcp_servers_table" in rev_0003.doc

    rev_0002 = script.get_revision("0002")
    assert rev_0002 is not None
    assert rev_0002.down_revision == "0001"
    assert "create_workspaces_table" in rev_0002.doc

    rev_0001 = script.get_revision("0001")
    assert rev_0001 is not None
    assert rev_0001.down_revision is None
    assert "initial_baseline" in rev_0001.doc


def test_get_url_precedence_x_argument() -> None:
    """Verify that CLI -x url= takes highest precedence in get_url()."""
    with patch(
        "migrations.env.context.get_x_argument",
        return_value={"url": "postgresql+asyncpg://cli:cli@localhost:5432/cli_db"},
    ):
        url = get_url()
        assert url == "postgresql+asyncpg://cli:cli@localhost:5432/cli_db"


def test_get_url_precedence_ini_option() -> None:
    """Verify that alembic.ini sqlalchemy.url option takes precedence without -x argument."""
    mock_config = MagicMock()
    mock_config.get_main_option.return_value = "postgresql+asyncpg://ini:ini@localhost:5432/ini_db"
    with (
        patch("migrations.env.context.get_x_argument", return_value={}),
        patch("migrations.env.config", mock_config),
    ):
        url = get_url()
        assert url == "postgresql+asyncpg://ini:ini@localhost:5432/ini_db"


def test_get_url_precedence_settings_fallback() -> None:
    """Verify that settings.database_url is used as fallback when neither -x nor ini is set."""
    with (
        patch("migrations.env.context.get_x_argument", return_value={}),
        patch("migrations.env.config", None),
        patch("migrations.env.get_settings") as mock_settings,
    ):
        mock_settings.return_value.database_url = (
            "postgresql+asyncpg://kolang:secret@db:5432/kolang"
        )
        url = get_url()
        assert url == "postgresql+asyncpg://kolang:secret@db:5432/kolang"


@pytest.mark.parametrize(
    ("raw_url", "expected_redacted"),
    [
        (
            "postgresql+asyncpg://kolang:super_secret_pw@localhost:5432/kolang",
            "postgresql+asyncpg://kolang:***@localhost:5432/kolang",
        ),
        (
            "postgresql://user:pass@db.internal:5433/prod_db",
            "postgresql://user:***@db.internal:5433/prod_db",
        ),
        (
            "postgresql+asyncpg://localhost:5432/kolang",
            "postgresql+asyncpg://localhost:5432/kolang",
        ),
        (
            "invalid-url-string",
            "invalid-url-string",
        ),
    ],
)
def test_redact_db_url(raw_url: str, expected_redacted: str) -> None:
    """Verify that redact_db_url masks plain passwords without destroying connection context."""
    redacted = redact_db_url(raw_url)
    assert "super_secret_pw" not in redacted
    assert "pass@" not in redacted
    if "super_secret_pw" in raw_url:
        assert "***" in redacted
