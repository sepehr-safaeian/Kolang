"""create_tools_and_snapshots_tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-22 15:00:00.000000

Establishes relational tables for Tool Catalog and Tool Discovery Snapshots
within organizational workspaces (ACP-010).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create tools and tool_snapshots tables with indexes and constraints."""
    # ── 1. Create tools table ────────────────────────────────────────────────
    op.create_table(
        "tools",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            sa.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "server_id",
            sa.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column(
            "description",
            sa.String(length=4096),
            server_default=sa.text("''"),
            nullable=False,
        ),
        sa.Column(
            "input_schema",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "annotations",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "classification_status",
            sa.String(length=30),
            server_default=sa.text("'unclassified'"),
            nullable=False,
        ),
        sa.Column(
            "risk_labels",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "is_enabled",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "first_discovered_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "last_discovered_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
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
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_tools_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["server_id"],
            ["mcp_servers.id"],
            name=op.f("fk_tools_server_id_mcp_servers"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tools")),
        sa.UniqueConstraint(
            "server_id",
            "name",
            name=op.f("uq_tools_server_id_name"),
        ),
    )
    op.create_index(
        op.f("ix_tools_workspace_id"),
        "tools",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tools_server_id"),
        "tools",
        ["server_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tools_fingerprint"),
        "tools",
        ["fingerprint"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tools_classification_status"),
        "tools",
        ["classification_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tools_is_enabled"),
        "tools",
        ["is_enabled"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tools_workspace_id_name"),
        "tools",
        ["workspace_id", "name"],
        unique=False,
    )

    # ── 2. Create tool_snapshots table ───────────────────────────────────────
    op.create_table(
        "tool_snapshots",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            sa.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "server_id",
            sa.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "snapshot_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("catalog_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "tools_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "tool_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
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
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_tool_snapshots_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["server_id"],
            ["mcp_servers.id"],
            name=op.f("fk_tool_snapshots_server_id_mcp_servers"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tool_snapshots")),
    )
    op.create_index(
        op.f("ix_tool_snapshots_workspace_id"),
        "tool_snapshots",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tool_snapshots_server_id"),
        "tool_snapshots",
        ["server_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tool_snapshots_snapshot_at"),
        "tool_snapshots",
        ["snapshot_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tool_snapshots_catalog_hash"),
        "tool_snapshots",
        ["catalog_hash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tool_snapshots_workspace_server"),
        "tool_snapshots",
        ["workspace_id", "server_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop tool_snapshots and tools tables with indexes."""
    op.execute('DROP INDEX IF EXISTS "ix_tool_snapshots_workspace_server";')
    op.execute('DROP INDEX IF EXISTS "ix_tool_snapshots_catalog_hash";')
    op.execute('DROP INDEX IF EXISTS "ix_tool_snapshots_snapshot_at";')
    op.execute('DROP INDEX IF EXISTS "ix_tool_snapshots_server_id";')
    op.execute('DROP INDEX IF EXISTS "ix_tool_snapshots_workspace_id";')
    op.execute('DROP TABLE IF EXISTS "tool_snapshots" CASCADE;')

    op.execute('DROP INDEX IF EXISTS "ix_tools_workspace_id_name";')
    op.execute('DROP INDEX IF EXISTS "ix_tools_is_enabled";')
    op.execute('DROP INDEX IF EXISTS "ix_tools_classification_status";')
    op.execute('DROP INDEX IF EXISTS "ix_tools_fingerprint";')
    op.execute('DROP INDEX IF EXISTS "ix_tools_server_id";')
    op.execute('DROP INDEX IF EXISTS "ix_tools_workspace_id";')
    op.execute('DROP TABLE IF EXISTS "tools" CASCADE;')
