"""Invite.role - роль, которая будет проставлена юзеру при регистрации по инвайту.

Revision ID: 0010_invite_role
Revises: 0009_cron_jobs
Create Date: 2026-05-13 01:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0010_invite_role"
down_revision = "0009_cron_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "invites",
        sa.Column("role", sa.String(), nullable=False, server_default="user"),
    )
    op.create_check_constraint(
        "invites_role_check",
        "invites",
        "role IN ('user', 'admin')",
    )


def downgrade() -> None:
    op.drop_constraint("invites_role_check", "invites", type_="check")
    op.drop_column("invites", "role")
