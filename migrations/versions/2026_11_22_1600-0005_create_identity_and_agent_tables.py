"""create_identity_and_agent_tables

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-22 16:00:00.000000

Establishes relational tables for Agent Workloads, MCP Client Registrations,
and Workspace Memberships within organizational workspaces (ACP-011).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create agents, mcp_client_registrations, and workspace_memberships tables."""
    # ── 1. Create agents table ───────────────────────────────────────────────
    op.create_table(
        "agents",
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
        sa.Column(
            "description",
            sa.String(length=512),
            server_default=sa.text("''"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column(
            "owner_id",
            sa.String(length=128),
            nullable=True,
        ),
        sa.Column(
            "team",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
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
            name=op.f("fk_agents_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agents")),
        sa.UniqueConstraint(
            "workspace_id",
            "slug",
            name=op.f("uq_agents_workspace_id_slug"),
        ),
    )
    op.create_index(
        op.f("ix_agents_workspace_id"),
        "agents",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agents_slug"),
        "agents",
        ["slug"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agents_status"),
        "agents",
        ["status"],
        unique=False,
    )

    # ── 2. Create mcp_client_registrations table ──────────────────────────────
    op.create_table(
        "mcp_client_registrations",
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
            "client_id",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "status",
            sa.String(length=30),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column(
            "agent_id",
            sa.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "client_type",
            sa.String(length=30),
            server_default=sa.text("'agent'"),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.String(length=512),
            server_default=sa.text("''"),
            nullable=False,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
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
            name=op.f("fk_mcp_client_registrations_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["agents.id"],
            name=op.f("fk_mcp_client_registrations_agent_id_agents"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mcp_client_registrations")),
        sa.UniqueConstraint(
            "workspace_id",
            "client_id",
            name=op.f("uq_mcp_client_registrations_workspace_id_client_id"),
        ),
    )
    op.create_index(
        op.f("ix_mcp_client_registrations_workspace_id"),
        "mcp_client_registrations",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_mcp_client_registrations_client_id"),
        "mcp_client_registrations",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_mcp_client_registrations_agent_id"),
        "mcp_client_registrations",
        ["agent_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_mcp_client_registrations_status"),
        "mcp_client_registrations",
        ["status"],
        unique=False,
    )

    # ── 3. Create workspace_memberships table ─────────────────────────────────
    op.create_table(
        "workspace_memberships",
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
            "user_id",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.String(length=30),
            server_default=sa.text("'developer'"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column(
            "email",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
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
            name=op.f("fk_workspace_memberships_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workspace_memberships")),
        sa.UniqueConstraint(
            "workspace_id",
            "user_id",
            name=op.f("uq_workspace_memberships_workspace_id_user_id"),
        ),
    )
    op.create_index(
        op.f("ix_workspace_memberships_workspace_id"),
        "workspace_memberships",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_workspace_memberships_user_id"),
        "workspace_memberships",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_workspace_memberships_status"),
        "workspace_memberships",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    """Drop identity tables in reverse dependency order."""
    op.execute('DROP INDEX IF EXISTS "ix_workspace_memberships_status";')
    op.execute('DROP INDEX IF EXISTS "ix_workspace_memberships_user_id";')
    op.execute('DROP INDEX IF EXISTS "ix_workspace_memberships_workspace_id";')
    op.execute('DROP TABLE IF EXISTS "workspace_memberships" CASCADE;')

    op.execute('DROP INDEX IF EXISTS "ix_mcp_client_registrations_status";')
    op.execute('DROP INDEX IF EXISTS "ix_mcp_client_registrations_agent_id";')
    op.execute('DROP INDEX IF EXISTS "ix_mcp_client_registrations_client_id";')
    op.execute('DROP INDEX IF EXISTS "ix_mcp_client_registrations_workspace_id";')
    op.execute('DROP TABLE IF EXISTS "mcp_client_registrations" CASCADE;')

    op.execute('DROP INDEX IF EXISTS "ix_agents_status";')
    op.execute('DROP INDEX IF EXISTS "ix_agents_slug";')
    op.execute('DROP INDEX IF EXISTS "ix_agents_workspace_id";')
    op.execute('DROP TABLE IF EXISTS "agents" CASCADE;')
