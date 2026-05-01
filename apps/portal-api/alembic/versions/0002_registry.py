"""0002 registry — tabs, agents, agent_versions.

Revision ID: 0002_registry
Revises: 0001_init
Create Date: 2026-05-01
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0002_registry"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # tabs
    op.create_table(
        "tabs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("slug", sa.Text, nullable=False, unique=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("icon", sa.Text, nullable=True),
        sa.Column("order_idx", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "is_system", sa.Boolean, nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.execute(
        "CREATE TRIGGER tabs_set_updated_at "
        "BEFORE UPDATE ON tabs FOR EACH ROW "
        "EXECUTE FUNCTION set_updated_at()"
    )

    # agents
    op.create_table(
        "agents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("slug", sa.Text, nullable=False, unique=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("icon", sa.Text, nullable=True),
        sa.Column("short_description", sa.Text, nullable=False),
        sa.Column(
            "tab_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tabs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        # FK добавим после создания agent_versions
        sa.Column("current_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "enabled", sa.Boolean, nullable=False, server_default=sa.text("false")
        ),
        sa.Column("git_url", sa.Text, nullable=False),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.execute(
        "CREATE TRIGGER agents_set_updated_at "
        "BEFORE UPDATE ON agents FOR EACH ROW "
        "EXECUTE FUNCTION set_updated_at()"
    )
    op.create_index("ix_agents_tab_id", "agents", ["tab_id"])
    op.create_index(
        "ix_agents_enabled_current",
        "agents",
        ["enabled", "current_version_id"],
        postgresql_where=sa.text("enabled = true AND current_version_id IS NOT NULL"),
    )

    # agent_versions
    op.create_table(
        "agent_versions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("git_sha", sa.Text, nullable=False),
        sa.Column("git_ref", sa.Text, nullable=False),
        sa.Column("manifest_jsonb", postgresql.JSONB, nullable=False),
        sa.Column("manifest_version", sa.Text, nullable=False),
        sa.Column("docker_image_tag", sa.Text, nullable=True),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("build_log", sa.Text, nullable=True),
        sa.Column("build_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("build_finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("build_error", sa.Text, nullable=True),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "status IN ('pending_build','building','ready','failed')",
            name="agent_versions_status_check",
        ),
        sa.UniqueConstraint(
            "agent_id", "git_sha", name="agent_versions_agent_id_git_sha_key"
        ),
    )
    op.create_index(
        "ix_agent_versions_agent_created",
        "agent_versions",
        ["agent_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_agent_versions_status_pending_building",
        "agent_versions",
        ["status"],
        postgresql_where=sa.text("status IN ('pending_build','building')"),
    )

    # FK agents.current_version_id → agent_versions.id (после создания agent_versions)
    op.create_foreign_key(
        "fk_agents_current_version_id",
        source_table="agents",
        referent_table="agent_versions",
        local_cols=["current_version_id"],
        remote_cols=["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_agents_current_version_id", "agents", type_="foreignkey")
    op.drop_index(
        "ix_agent_versions_status_pending_building", table_name="agent_versions"
    )
    op.drop_index("ix_agent_versions_agent_created", table_name="agent_versions")
    op.drop_table("agent_versions")
    op.drop_index("ix_agents_enabled_current", table_name="agents")
    op.drop_index("ix_agents_tab_id", table_name="agents")
    op.execute("DROP TRIGGER IF EXISTS agents_set_updated_at ON agents")
    op.drop_table("agents")
    op.execute("DROP TRIGGER IF EXISTS tabs_set_updated_at ON tabs")
    op.drop_table("tabs")
