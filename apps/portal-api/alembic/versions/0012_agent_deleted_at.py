"""agent_deleted_at — soft-delete агентов.

Добавляет nullable-колонку `deleted_at` в таблицу `agents`. NULL = агент
жив, не-NULL = soft-deleted (момент удаления). Hard-delete небезопасен:
jobs/llm_usage_logs хранят финансовые записи (cost_usd) под FK RESTRICT/NO
ACTION на агента/версии. Поэтому удаление = пометка deleted_at + enabled=False.

Revision ID: 0012_agent_deleted_at
Revises: 0011_llm_settings
Create Date: 2026-05-29 00:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0012_agent_deleted_at"
down_revision = "0011_llm_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("agents", "deleted_at")
