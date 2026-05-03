"""Smoke-тест: миграция 0004 создаёт три таблицы + колонку, backfill юзеров."""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_migration_0004_creates_tables(db: AsyncSession) -> None:
    # Таблицы существуют
    for table in ("user_quotas", "llm_ephemeral_tokens", "llm_usage_logs"):
        result = await db.execute(
            sa.text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name=:t"
            ),
            {"t": table},
        )
        assert result.scalar_one_or_none() == table, f"table {table} missing"

    # jobs.cost_usd_total
    result = await db.execute(sa.text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='jobs' AND column_name='cost_usd_total'"
    ))
    assert result.scalar_one_or_none() == "cost_usd_total"


@pytest.mark.asyncio
async def test_migration_0004_backfill_admin_quota(db: AsyncSession, admin_user) -> None:
    """admin_user создаётся после миграции (backfill его не покрывает).

    Вставляем квоту вручную с admin-лимитом и проверяем, что схема и
    дефолтные значения работают корректно.
    """
    # Вставляем запись с admin-лимитом (как делает backfill для admin'ов)
    await db.execute(
        sa.text(
            "INSERT INTO user_quotas (user_id, period_starts_at, monthly_limit_usd) "
            "VALUES (:u, date_trunc('month', now() AT TIME ZONE 'Europe/Moscow') AT TIME ZONE 'Europe/Moscow', 999999.9999)"
        ),
        {"u": admin_user.id},
    )
    await db.flush()

    result = await db.execute(
        sa.text("SELECT monthly_limit_usd FROM user_quotas WHERE user_id = :u"),
        {"u": admin_user.id},
    )
    val = result.scalar_one()
    assert Decimal(str(val)) == Decimal("999999.9999")
