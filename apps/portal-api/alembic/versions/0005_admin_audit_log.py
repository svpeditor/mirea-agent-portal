"""Admin audit log: таблица для трекинга административных действий.

Revision ID: 0005_admin_audit_log
Revises: 0004_llm_proxy
Create Date: 2026-05-10 23:50:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005_admin_audit_log"
down_revision = "0004_llm_proxy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_audit_log",
        sa.Column(
            "id", sa.UUID(), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "actor_user_id", sa.UUID(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("resource_type", sa.Text(), nullable=False),
        sa.Column("resource_id", sa.Text(), nullable=True),
        sa.Column(
            "payload_jsonb",
            sa.dialects.postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("ip", sa.Text(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
    )
    op.create_index(
        "ix_admin_audit_log_created_at",
        "admin_audit_log",
        ["created_at"],
        postgresql_using="btree",
    )
    op.create_index(
        "ix_admin_audit_log_actor",
        "admin_audit_log",
        ["actor_user_id"],
    )
    op.create_index(
        "ix_admin_audit_log_resource",
        "admin_audit_log",
        ["resource_type", "resource_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_admin_audit_log_resource", table_name="admin_audit_log")
    op.drop_index("ix_admin_audit_log_actor", table_name="admin_audit_log")
    op.drop_index("ix_admin_audit_log_created_at", table_name="admin_audit_log")
    op.drop_table("admin_audit_log")
