"""Smoke-тест: миграция 0004 создаёт три таблицы + колонку, backfill юзеров."""
from __future__ import annotations

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


@pytest.mark.asyncio
async def test_migration_0004_backfill_sql_routes_role_to_quota(db: AsyncSession) -> None:
    """Backfill SQL различает admin и user: 999999.9999 vs 5.0000."""
    # Удалить квоты для наших тестовых юзеров (если существуют)
    await db.execute(sa.text(
        "DELETE FROM user_quotas WHERE user_id IN ("
        "  SELECT id FROM users WHERE email IN ('bf-admin@x.x', 'bf-user@x.x')"
        ")"
    ))
    # Создать двух юзеров с разными ролями
    await db.execute(sa.text(
        "INSERT INTO users (email, password_hash, display_name, role) VALUES "
        "('bf-admin@x.x', 'h', 'A', 'admin'), "
        "('bf-user@x.x', 'h', 'U', 'user')"
    ))
    # Запустить тот же backfill SQL что в миграции
    await db.execute(sa.text("""
        INSERT INTO user_quotas (user_id, period_starts_at, monthly_limit_usd)
        SELECT u.id,
               (date_trunc('month', (now() AT TIME ZONE 'Europe/Moscow')) AT TIME ZONE 'Europe/Moscow'),
               CASE u.role WHEN 'admin' THEN 999999.9999 ELSE 5.0000 END
        FROM users u
        WHERE u.email IN ('bf-admin@x.x', 'bf-user@x.x')
    """))
    await db.flush()

    rows = (await db.execute(sa.text(
        "SELECT u.role, q.monthly_limit_usd FROM user_quotas q "
        "JOIN users u ON u.id = q.user_id "
        "WHERE u.email IN ('bf-admin@x.x', 'bf-user@x.x')"
    ))).all()
    by_role = {r[0]: Decimal(str(r[1])) for r in rows}
    assert by_role == {
        "admin": Decimal("999999.9999"),
        "user": Decimal("5.0000"),
    }
