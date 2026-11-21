"""initial_baseline

Revision ID: 0001
Revises: None
Create Date: 2026-11-21 17:11:46.171725

Establishes the initial database environment and PostgreSQL extensions
(uuid-ossp, pgcrypto) required for subsequent relational models in Kolang ACP.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply baseline schema modifications.

    Enables standard PostgreSQL extensions required for cryptographic hashing
    and UUID operations across all Kolang domain entities.
    """
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')


def downgrade() -> None:
    """Revert baseline schema modifications.

    Non-destructive downgrade: database extensions are retained to avoid
    breaking external shared services or dependencies in multi-tenant databases.
    """
    pass
