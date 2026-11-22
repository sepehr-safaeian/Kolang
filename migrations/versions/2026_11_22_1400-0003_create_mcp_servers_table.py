"""create_mcp_servers_table

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-22 14:00:00.000000

Establishes the mcp_servers relational table for registering, managing, and
monitoring Upstream MCP Servers within organizational workspaces (ACP-009).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create mcp_servers table with tenant isolation and indexes."""
    op.create_table(
        "mcp_servers",
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
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("endpoint_url", sa.String(length=512), nullable=False),
        sa.Column(
            "transport",
            sa.String(length=30),
            server_default=sa.text("'streamable_http'"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column(
            "auth_profile_id",
            sa.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "last_discovered_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "last_health_check_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "description",
            sa.String(length=255),
            server_default=sa.text("''"),
            nullable=False,
        ),
        sa.Column(
            "metadata",
            sa.JSON(),
            server_default=sa.text("'{}'"),
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
            name=op.f("fk_mcp_servers_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mcp_servers")),
        sa.UniqueConstraint(
            "workspace_id",
            "slug",
            name=op.f("uq_mcp_servers_workspace_id_slug"),
        ),
    )
    op.create_index(
        op.f("ix_mcp_servers_workspace_id"),
        "mcp_servers",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_mcp_servers_slug"),
        "mcp_servers",
        ["slug"],
        unique=False,
    )
    op.create_index(
        op.f("ix_mcp_servers_status"),
        "mcp_servers",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    """Drop mcp_servers table and associated indexes."""
    op.execute('DROP INDEX IF EXISTS "ix_mcp_servers_status";')
    op.execute('DROP INDEX IF EXISTS "ix_mcp_servers_slug";')
    op.execute('DROP INDEX IF EXISTS "ix_mcp_servers_workspace_id";')
    op.execute('DROP TABLE IF EXISTS "mcp_servers" CASCADE;')
