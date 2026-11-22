"""create_workspaces_table

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-22 12:00:00.000000

Establishes the workspaces relational table for organizational multi-tenancy,
data isolation, and tenant boundary enforcement across Kolang ACP.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create workspaces table and unique index on slug."""
    op.create_table(
        "workspaces",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.String(length=255),
            server_default=sa.text("''"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workspaces")),
    )
    op.create_index(
        op.f("ix_workspaces_slug"),
        "workspaces",
        ["slug"],
        unique=True,
    )


def downgrade() -> None:
    """Drop workspaces table and associated index."""
    op.execute('DROP INDEX IF EXISTS "ix_workspaces_slug";')
    op.execute('DROP TABLE IF EXISTS "workspaces" CASCADE;')
