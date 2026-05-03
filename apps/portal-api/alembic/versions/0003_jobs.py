"""jobs

Revision ID: 0003_jobs
Revises: 0002_registry
Create Date: 2026-05-01

"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0003_jobs"
down_revision = "0002_registry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("agent_version_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("agent_versions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("params_jsonb", postgresql.JSONB(),
                  server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("finished_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("exit_code", sa.Integer()),
        sa.Column("error_msg", sa.Text()),
        sa.Column("error_code", sa.Text()),
        sa.Column("output_summary_jsonb", postgresql.JSONB()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('queued','running','ready','failed','cancelled')",
            name="jobs_status_check",
        ),
    )
    op.create_index("jobs_user_created_idx", "jobs",
                    ["created_by_user_id", sa.text("created_at DESC")])
    op.create_index("jobs_status_idx", "jobs", ["status"],
                    postgresql_where=sa.text("status IN ('queued','running')"))
    op.create_index("jobs_agent_version_idx", "jobs", ["agent_version_id"])

    op.create_table(
        "job_events",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("ts", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("payload_jsonb", postgresql.JSONB(), nullable=False),
        sa.UniqueConstraint("job_id", "seq", name="job_events_job_id_seq_key"),
    )
    op.create_index("job_events_job_seq_idx", "job_events", ["job_id", "seq"])

    op.create_table(
        "job_files",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("content_type", sa.Text()),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.Text(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("kind IN ('input','output')", name="job_files_kind_check"),
        sa.UniqueConstraint("job_id", "kind", "filename", name="job_files_job_kind_filename_key"),
    )
    op.create_index("job_files_job_kind_idx", "job_files", ["job_id", "kind"])


def downgrade() -> None:
    op.drop_index("job_files_job_kind_idx", table_name="job_files")
    op.drop_table("job_files")
    op.drop_index("job_events_job_seq_idx", table_name="job_events")
    op.drop_table("job_events")
    op.drop_index("jobs_agent_version_idx", table_name="jobs")
    op.drop_index("jobs_status_idx", table_name="jobs")
    op.drop_index("jobs_user_created_idx", table_name="jobs")
    op.drop_table("jobs")
