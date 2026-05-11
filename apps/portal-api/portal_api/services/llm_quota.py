"""Pre-flight + post-flight квоты для LLM-прокси.

Pre-flight: короткая транзакция с FOR UPDATE на user_quotas; lazy month reset;
проверка estimated_cost <= min(remaining_monthly, remaining_per_job).
Post-flight: вторая короткая транзакция; INSERT в llm_usage_logs делается
вызывающим кодом (services/llm_proxy), эта функция только инкрементит счётчики.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import sqlalchemy as sa
from dateutil.relativedelta import relativedelta
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.config import get_settings
from portal_api.core.exceptions import (
    PerJobCapExceededError,
    QuotaExhaustedError,
)
from portal_api.models import Job, User, UserQuota

MSK_OFFSET = timedelta(hours=3)


def _floor_to_month_start_msk_utc(now_utc: datetime) -> datetime:
    """Возвращает начало текущего месяца по МСК, в UTC.

    Пример: now_utc = 2026-05-03 12:00 UTC → МСК = 15:00, месяц май → начало
    1 мая 00:00 МСК = 30 апреля 21:00 UTC.
    """
    msk = now_utc + MSK_OFFSET
    msk_month_start = msk.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return msk_month_start - MSK_OFFSET


async def preflight(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    job_id: uuid.UUID,
    estimated_cost: Decimal,
) -> None:
    """Проверяет квоту перед вызовом LLM.

    Выполняет lazy month reset если период устарел, затем проверяет:
    - estimated_cost <= remaining_monthly (иначе QuotaExhaustedError)
    - estimated_cost <= remaining_per_job (иначе PerJobCapExceededError)
    """
    now = datetime.now(timezone.utc)

    quota = (
        await db.execute(
            sa.select(UserQuota).where(UserQuota.user_id == user_id).with_for_update()
        )
    ).scalar_one_or_none()
    if quota is None:
        # Lazy backfill: бутстрапнутый админ и старые юзеры из preview-БД
        # могут не иметь quota-строки. Создаём дефолтную по роли.
        user = (
            await db.execute(sa.select(User).where(User.id == user_id))
        ).scalar_one()
        settings = get_settings()
        monthly = (
            Decimal("999999.9999") if user.role == "admin"
            else settings.llm_default_user_quota_usd
        )
        quota = UserQuota(
            user_id=user_id,
            monthly_limit_usd=monthly,
            per_job_cap_usd=settings.llm_default_per_job_cap_usd,
            period_starts_at=_floor_to_month_start_msk_utc(now),
        )
        db.add(quota)
        await db.flush()

    if now >= quota.period_starts_at + relativedelta(months=1):
        quota.period_used_usd = Decimal("0.0000")
        quota.period_starts_at = _floor_to_month_start_msk_utc(now)
        await db.flush()

    remaining_monthly = quota.monthly_limit_usd - quota.period_used_usd
    if estimated_cost > remaining_monthly:
        raise QuotaExhaustedError(
            f"monthly limit ${quota.monthly_limit_usd} exceeded "
            f"(used ${quota.period_used_usd}, requested ~${estimated_cost})"
        )

    job = (
        await db.execute(sa.select(Job).where(Job.id == job_id))
    ).scalar_one()
    remaining_per_job = quota.per_job_cap_usd - job.cost_usd_total
    if estimated_cost > remaining_per_job:
        raise PerJobCapExceededError(
            f"per-job cap ${quota.per_job_cap_usd} exceeded "
            f"(used ${job.cost_usd_total}, requested ~${estimated_cost})"
        )


async def postflight(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    job_id: uuid.UUID,
    real_cost: Decimal,
) -> None:
    """Инкрементирует счётчики после успешного вызова LLM.

    Увеличивает period_used_usd у UserQuota и cost_usd_total у Job.
    INSERT в llm_usage_logs выполняется вызывающим кодом.
    """
    quota = (
        await db.execute(
            sa.select(UserQuota).where(UserQuota.user_id == user_id).with_for_update()
        )
    ).scalar_one()
    quota.period_used_usd += real_cost

    await db.execute(
        sa.update(Job)
        .where(Job.id == job_id)
        .values(cost_usd_total=Job.cost_usd_total + real_cost)
    )
    await db.flush()
