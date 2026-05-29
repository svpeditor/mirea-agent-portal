"""datasets — общая база данных для агентов.

Таблицы `datasets` (каталог) и `dataset_records` (записи: ключ + JSON и/или
текст, например LaTeX). Один агент наполняет, другие читают; права задаются в
манифесте агента (`runtime.datasets`). FK на agents/jobs = SET NULL, чтобы
удаление агента или джоба не ломало накопленные данные.

Revision ID: 0013_datasets
Revises: 0012_agent_deleted_at
Create Date: 2026-05-30 00:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0013_datasets"
down_revision = "0012_agent_deleted_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "datasets",
        sa.Column(
            "id", sa.UUID(), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("slug", sa.Text(), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.func.now(),
        ),
    )
    op.create_table(
        "dataset_records",
        sa.Column(
            "id", sa.UUID(), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("dataset_id", sa.UUID(), nullable=False),
        sa.Column("record_key", sa.Text(), nullable=False),
        sa.Column(
            "content_format", sa.Text(), nullable=False,
            server_default=sa.text("'json'"),
        ),
        sa.Column("value_jsonb", postgresql.JSONB(), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("created_by_agent_id", sa.UUID(), nullable=True),
        sa.Column("created_by_job_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["created_by_agent_id"], ["agents.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_job_id"], ["jobs.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint(
            "dataset_id", "record_key", name="dataset_records_key_uq"
        ),
    )
    op.create_index(
        "ix_dataset_records_dataset", "dataset_records", ["dataset_id"]
    )
    op.create_index(
        "ix_dataset_records_dataset_created",
        "dataset_records", ["dataset_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_dataset_records_dataset_created", table_name="dataset_records")
    op.drop_index("ix_dataset_records_dataset", table_name="dataset_records")
    op.drop_table("dataset_records")
    op.drop_table("datasets")
