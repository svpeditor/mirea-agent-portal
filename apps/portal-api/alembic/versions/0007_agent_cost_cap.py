"""Per-agent cost cap.

Revision ID: 0007_agent_cost_cap
Revises: 0006_user_avatar
Create Date: 2026-05-11 16:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007_agent_cost_cap"
down_revision = "0006_user_avatar"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column(
            "cost_cap_usd",
            sa.Numeric(10, 4),
            nullable=True,
            server_default=None,
        ),
    )


def downgrade() -> None:
    op.drop_column("agents", "cost_cap_usd")
