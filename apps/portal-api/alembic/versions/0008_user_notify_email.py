"""Email notifications opt-in.

Revision ID: 0008_user_notify_email
Revises: 0007_agent_cost_cap
Create Date: 2026-05-11 17:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008_user_notify_email"
down_revision = "0007_agent_cost_cap"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "notify_on_job_finish",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "notify_on_job_finish")
