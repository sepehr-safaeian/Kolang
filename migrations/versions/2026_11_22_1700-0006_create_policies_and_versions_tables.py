"""create_policies_and_versions_tables

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-22 17:00:00.000000

Establishes relational tables for Access Control Policies and immutable
Policy Versions within organizational workspaces (ACP-012).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create policies and policy_versions tables with indexes and constraints."""
    # ── 1. Create policies table ─────────────────────────────────────────────
    op.create_table(
        "policies",
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
            sa.String(length=20),
            server_default=sa.text("'draft'"),
            nullable=False,
        ),
        sa.Column(
            "draft_rego",
            sa.Text(),
            server_default=sa.text("''"),
            nullable=False,
        ),
        sa.Column(
            "draft_bundle_reference",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "active_version_id",
            sa.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "active_version_number",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "created_by",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "updated_by",
            sa.String(length=128),
            nullable=True,
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
            name=op.f("fk_policies_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_policies")),
        sa.UniqueConstraint(
            "workspace_id",
            "slug",
            name=op.f("uq_policies_workspace_id_slug"),
        ),
    )
    op.create_index(
        op.f("ix_policies_workspace_id"),
        "policies",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_policies_slug"),
        "policies",
        ["slug"],
        unique=False,
    )
    op.create_index(
        op.f("ix_policies_status"),
        "policies",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_policies_workspace_id_status",
        "policies",
        ["workspace_id", "status"],
        unique=False,
    )

    # ── 2. Create policy_versions table ──────────────────────────────────────
    op.create_table(
        "policy_versions",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column(
            "policy_id",
            sa.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            sa.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "rego_source",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "bundle_reference",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "checksum",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.String(length=512),
            server_default=sa.text("''"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'published'"),
            nullable=False,
        ),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "published_by",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_policy_versions")),
        sa.ForeignKeyConstraint(
            ["policy_id"],
            ["policies.id"],
            name=op.f("fk_policy_versions_policy_id_policies"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_policy_versions_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "policy_id",
            "version",
            name=op.f("uq_policy_versions_policy_id_version"),
        ),
    )
    op.create_index(
        op.f("ix_policy_versions_policy_id"),
        "policy_versions",
        ["policy_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_policy_versions_workspace_id"),
        "policy_versions",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_policy_versions_checksum"),
        "policy_versions",
        ["checksum"],
        unique=False,
    )
    op.create_index(
        op.f("ix_policy_versions_status"),
        "policy_versions",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_policy_versions_workspace_policy",
        "policy_versions",
        ["workspace_id", "policy_id"],
        unique=False,
    )

    # ── 3. Establish foreign key from policies to policy_versions ────────────
    op.create_foreign_key(
        op.f("fk_policies_active_version_id_policy_versions"),
        "policies",
        "policy_versions",
        ["active_version_id"],
        ["id"],
        ondelete="SET NULL",
        use_alter=True,
    )
    op.create_index(
        op.f("ix_policies_active_version_id"),
        "policies",
        ["active_version_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop policies and policy_versions tables in reverse dependency order."""
    op.execute(
        'ALTER TABLE IF EXISTS "policies" '
        'DROP CONSTRAINT IF EXISTS "fk_policies_active_version_id_policy_versions";'
    )
    op.execute('DROP INDEX IF EXISTS "ix_policies_active_version_id";')

    # Drop policy_versions table and indexes
    op.execute('DROP INDEX IF EXISTS "ix_policy_versions_workspace_policy";')
    op.execute('DROP INDEX IF EXISTS "ix_policy_versions_status";')
    op.execute('DROP INDEX IF EXISTS "ix_policy_versions_checksum";')
    op.execute('DROP INDEX IF EXISTS "ix_policy_versions_workspace_id";')
    op.execute('DROP INDEX IF EXISTS "ix_policy_versions_policy_id";')
    op.execute('DROP TABLE IF EXISTS "policy_versions" CASCADE;')

    # Drop policies table and indexes
    op.execute('DROP INDEX IF EXISTS "ix_policies_workspace_id_status";')
    op.execute('DROP INDEX IF EXISTS "ix_policies_status";')
    op.execute('DROP INDEX IF EXISTS "ix_policies_slug";')
    op.execute('DROP INDEX IF EXISTS "ix_policies_workspace_id";')
    op.execute('DROP TABLE IF EXISTS "policies" CASCADE;')
