"""LLM proxy: user_quotas, llm_ephemeral_tokens, llm_usage_logs, jobs.cost_usd_total.

Revision ID: 0004_llm_proxy
Revises: 0003_jobs
Create Date: 2026-05-03 22:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_llm_proxy"
down_revision = "0003_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_quotas",
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("monthly_limit_usd", sa.Numeric(10, 4), nullable=False, server_default=sa.text("5.0000")),
        sa.Column("period_used_usd", sa.Numeric(10, 4), nullable=False, server_default=sa.text("0.0000")),
        sa.Column("period_starts_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("per_job_cap_usd", sa.Numeric(10, 4), nullable=False, server_default=sa.text("0.5000")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.execute(sa.text("""
        INSERT INTO user_quotas (user_id, period_starts_at, monthly_limit_usd)
        SELECT
            u.id,
            (date_trunc('month', (now() AT TIME ZONE 'Europe/Moscow')) AT TIME ZONE 'Europe/Moscow'),
            CASE u.role WHEN 'admin' THEN 999999.9999 ELSE 5.0000 END
        FROM users u
    """))

    op.create_table(
        "llm_ephemeral_tokens",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("job_id", sa.UUID(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("agent_version_id", sa.UUID(), sa.ForeignKey("agent_versions.id"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("llm_ephemeral_tokens_job_id_idx", "llm_ephemeral_tokens", ["job_id"])
    op.create_index("llm_ephemeral_tokens_expires_at_idx", "llm_ephemeral_tokens", ["expires_at"])

    op.create_table(
        "llm_usage_logs",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", sa.UUID(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("agent_id", sa.UUID(), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("agent_version_id", sa.UUID(), sa.ForeignKey("agent_versions.id"), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("openrouter_request_id", sa.String(128), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "llm_usage_logs_user_created_idx",
        "llm_usage_logs",
        ["user_id", sa.text("created_at DESC")],
    )
    op.create_index("llm_usage_logs_job_idx", "llm_usage_logs", ["job_id"])
    op.create_index(
        "llm_usage_logs_agent_created_idx",
        "llm_usage_logs",
        ["agent_id", sa.text("created_at DESC")],
    )

    op.add_column(
        "jobs",
        sa.Column("cost_usd_total", sa.Numeric(10, 6), nullable=False, server_default=sa.text("0")),
    )


def downgrade() -> None:
    op.drop_column("jobs", "cost_usd_total")
    op.drop_index("llm_usage_logs_agent_created_idx", table_name="llm_usage_logs")
    op.drop_index("llm_usage_logs_job_idx", table_name="llm_usage_logs")
    op.drop_index("llm_usage_logs_user_created_idx", table_name="llm_usage_logs")
    op.drop_table("llm_usage_logs")
    op.drop_index("llm_ephemeral_tokens_expires_at_idx", table_name="llm_ephemeral_tokens")
    op.drop_index("llm_ephemeral_tokens_job_id_idx", table_name="llm_ephemeral_tokens")
    op.drop_table("llm_ephemeral_tokens")
    op.drop_table("user_quotas")
