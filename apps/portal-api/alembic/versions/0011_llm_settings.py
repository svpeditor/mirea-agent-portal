"""llm_settings — редактируемые из UI настройки LLM (ключ OpenRouter,
provider_mode, per-provider ключи, override whitelist). Singleton (id=1).

Секреты хранятся в БД, НИКОГДА не возвращаются клиенту целиком (admin GET
маскирует), не логируются. Фаза 2: openrouter_api_key + allowed_models.
Фаза 3 (колонки заведены сразу, чтобы не плодить миграцию): provider_mode
+ per-provider ключи.

Revision ID: 0011_llm_settings
Revises: 0010_invite_role
Create Date: 2026-05-18 16:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0011_llm_settings"
down_revision = "0010_invite_role"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_settings",
        sa.Column("id", sa.SmallInteger(), primary_key=True),
        sa.Column("openrouter_api_key", sa.Text(), nullable=True),
        sa.Column(
            "provider_mode", sa.Text(), nullable=False,
            server_default="openrouter",
        ),
        sa.Column("openai_api_key", sa.Text(), nullable=True),
        sa.Column("google_api_key", sa.Text(), nullable=True),
        sa.Column("xai_api_key", sa.Text(), nullable=True),
        sa.Column("anthropic_api_key", sa.Text(), nullable=True),
        sa.Column("deepseek_api_key", sa.Text(), nullable=True),
        sa.Column("allowed_models", sa.Text(), nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_by_user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.CheckConstraint("id = 1", name="llm_settings_singleton"),
        sa.CheckConstraint(
            "provider_mode IN ('openrouter', 'direct')",
            name="llm_settings_provider_mode_check",
        ),
    )
    # set_updated_at() уже определён в 0001 — вешаем триггер.
    op.execute("""
    CREATE TRIGGER llm_settings_updated_at
    BEFORE UPDATE ON llm_settings
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    """)
    # Сидим singleton-строку (пустую — fallback на env, пока админ не задаст).
    op.execute("INSERT INTO llm_settings (id) VALUES (1)")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS llm_settings_updated_at ON llm_settings")
    op.drop_table("llm_settings")
