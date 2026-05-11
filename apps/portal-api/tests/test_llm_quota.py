"""llm_quota: preflight/postflight + lazy month reset + сериализация под FOR UPDATE."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.core.exceptions import (
    PerJobCapExceededError,
    QuotaExhaustedError,
)
from portal_api.models import Job, UserQuota
from portal_api.services import llm_quota
from tests.factories import (
    make_agent,
    make_agent_version,
    make_job,
    make_tab,
)


@pytest.fixture
async def quota_user(db: AsyncSession, admin_user):
    """Создаёт юзера с квотой 5.0 / per_job 0.5, period_starts_at = начало мая 2026 МСК."""
    from tests.factories import make_user

    u = await make_user(db, email="qu@x.x", password="testpasswordX1")
    period_start_msk = datetime(2026, 5, 1, 0, 0, tzinfo=timezone.utc)  # упрощённо
    q = UserQuota(
        user_id=u.id,
        monthly_limit_usd=Decimal("5.0000"),
        period_used_usd=Decimal("0.0000"),
        period_starts_at=period_start_msk,
        per_job_cap_usd=Decimal("0.5000"),
    )
    db.add(q)
    await db.commit()
    return u


@pytest.fixture
async def llm_job(db: AsyncSession, quota_user, admin_user):
    tab = await make_tab(db, slug="t-q", name="T", order_idx=1)
    agent = await make_agent(
        db, slug="a-q", tab_id=tab.id, created_by_user_id=admin_user.id
    )
    av = await make_agent_version(
        db, agent_id=agent.id, created_by_user_id=admin_user.id, status="ready"
    )
    return await make_job(db, agent_version_id=av.id, user_id=quota_user.id)


@pytest.mark.asyncio
async def test_preflight_passes_when_under_limits(
    db: AsyncSession, quota_user, llm_job
) -> None:
    await llm_quota.preflight(
        db,
        user_id=quota_user.id,
        job_id=llm_job.id,
        estimated_cost=Decimal("0.0010"),
    )


@pytest.mark.asyncio
async def test_preflight_quota_exhausted(
    db: AsyncSession, quota_user, llm_job
) -> None:
    await db.execute(
        sa.update(UserQuota)
        .where(UserQuota.user_id == quota_user.id)
        .values(period_used_usd=Decimal("4.9999"))
    )
    await db.commit()

    with pytest.raises(QuotaExhaustedError):
        await llm_quota.preflight(
            db,
            user_id=quota_user.id,
            job_id=llm_job.id,
            estimated_cost=Decimal("0.0010"),
        )


@pytest.mark.asyncio
async def test_preflight_per_job_cap_exceeded(
    db: AsyncSession, quota_user, llm_job
) -> None:
    await db.execute(
        sa.update(Job).where(Job.id == llm_job.id).values(cost_usd_total=Decimal("0.4990"))
    )
    await db.commit()

    with pytest.raises(PerJobCapExceededError):
        await llm_quota.preflight(
            db,
            user_id=quota_user.id,
            job_id=llm_job.id,
            estimated_cost=Decimal("0.0050"),
        )


@pytest.mark.asyncio
async def test_postflight_increments_used_and_job_total(
    db: AsyncSession, quota_user, llm_job
) -> None:
    await llm_quota.postflight(
        db,
        user_id=quota_user.id,
        job_id=llm_job.id,
        real_cost=Decimal("0.0123"),
    )
    await db.commit()

    q = await db.get(UserQuota, quota_user.id)
    assert q.period_used_usd == Decimal("0.0123")
    j = await db.get(Job, llm_job.id)
    assert j.cost_usd_total == Decimal("0.012300")


@pytest.mark.asyncio
async def test_preflight_lazy_backfill_creates_missing_quota(
    db: AsyncSession, admin_user, llm_job
) -> None:
    """Если UserQuota отсутствует, preflight создаёт дефолтную, а не падает 500."""
    from tests.factories import make_agent, make_agent_version, make_job, make_tab, make_user

    u = await make_user(db, email="nq@x.x", password="testpasswordY1")
    tab2 = await make_tab(db, slug="t-q2", name="T2", order_idx=2)
    agent = await make_agent(
        db, slug="a-q2", tab_id=tab2.id, created_by_user_id=admin_user.id
    )
    av = await make_agent_version(
        db, agent_id=agent.id, created_by_user_id=admin_user.id, status="ready"
    )
    job = await make_job(db, agent_version_id=av.id, user_id=u.id)
    await db.commit()

    assert await db.get(UserQuota, u.id) is None

    await llm_quota.preflight(
        db, user_id=u.id, job_id=job.id, estimated_cost=Decimal("0.0010")
    )

    q_after = await db.get(UserQuota, u.id)
    assert q_after is not None
    assert q_after.monthly_limit_usd > Decimal("0")


@pytest.mark.asyncio
async def test_lazy_month_reset(db: AsyncSession, quota_user, llm_job) -> None:
    """period_starts_at < 1 мес назад → preflight ресетит period_used + двигает период."""
    await db.execute(
        sa.update(UserQuota)
        .where(UserQuota.user_id == quota_user.id)
        .values(
            period_starts_at=datetime(2026, 4, 1, 0, 0, tzinfo=timezone.utc),
            period_used_usd=Decimal("4.9000"),
        )
    )
    await db.commit()

    from freezegun import freeze_time

    with freeze_time("2026-06-15 12:00:00", tz_offset=3):
        await llm_quota.preflight(
            db,
            user_id=quota_user.id,
            job_id=llm_job.id,
            estimated_cost=Decimal("0.0010"),
        )

    q = await db.get(UserQuota, quota_user.id)
    assert q.period_used_usd == Decimal("0.0000")
    # period_starts_at хранится в UTC; конвертируем в МСК (+3ч) для проверки месяца
    from datetime import timedelta as _td

    period_msk = q.period_starts_at + _td(hours=3)
    assert period_msk.month == 6
    assert period_msk.day == 1
