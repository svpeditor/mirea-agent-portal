"""User avatar: storage_key + content_type.

Revision ID: 0006_user_avatar
Revises: 0005_admin_audit_log
Create Date: 2026-05-11 14:30:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006_user_avatar"
down_revision = "0005_admin_audit_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("avatar_storage_key", sa.Text(), nullable=True)
    )
    op.add_column(
        "users", sa.Column("avatar_content_type", sa.Text(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("users", "avatar_content_type")
    op.drop_column("users", "avatar_storage_key")
