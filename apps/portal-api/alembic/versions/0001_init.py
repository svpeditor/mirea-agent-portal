"""init: users + invites + refresh_tokens.

Revision ID: 0001_init
Revises:
Create Date: 2026-04-30
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import INET, UUID

from alembic import op

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")  # для gen_random_uuid()

    op.create_table(
        "users",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="user"),
        sa.Column(
            "monthly_budget_usd",
            sa.Numeric(10, 2),
            nullable=False,
            server_default=sa.text("5.00"),
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
        sa.UniqueConstraint("email", name="users_email_key"),
        sa.CheckConstraint("role IN ('user', 'admin')", name="users_role_check"),
    )

    # trigger на updated_at
    op.execute("""
    CREATE OR REPLACE FUNCTION set_updated_at()
    RETURNS TRIGGER AS $$
    BEGIN
      NEW.updated_at = now();
      RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    op.execute("""
    CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    """)

    op.create_table(
        "invites",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("created_by_user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("token", name="invites_token_key"),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"],
            name="invites_created_by_fkey", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["used_by_user_id"], ["users.id"],
            name="invites_used_by_fkey", ondelete="SET NULL",
        ),
    )
    op.create_index(
        "invites_pending_email_idx",
        "invites",
        ["email"],
        postgresql_where=sa.text("used_at IS NULL"),
    )

    op.create_table(
        "refresh_tokens",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_id", UUID(as_uuid=True), nullable=True),
        sa.Column("user_agent", sa.String(), nullable=True),
        sa.Column("ip", INET(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="refresh_tokens_user_fkey", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["replaced_by_id"], ["refresh_tokens.id"],
            name="refresh_tokens_replaced_by_fkey", ondelete="SET NULL",
        ),
    )
    op.create_index(
        "refresh_tokens_active_idx",
        "refresh_tokens",
        ["user_id"],
        postgresql_where=sa.text("revoked_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("refresh_tokens_active_idx", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_index("invites_pending_email_idx", table_name="invites")
    op.drop_table("invites")
    op.execute("DROP TRIGGER IF EXISTS users_updated_at ON users")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")
    op.drop_table("users")
