"""ORM round-trip для LLM-таблиц 1.2.4."""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.models import EphemeralToken, UsageLog, UserQuota
from tests.factories import (
    make_agent, make_agent_version, make_job, make_tab, make_user,
)


@pytest.mark.asyncio
async def test_user_quota_round_trip(db: AsyncSession, admin_user) -> None:
    user = await make_user(db, email="alice@example.com", password="testpasswordX1")
    q = UserQuota(
        user_id=user.id,
        monthly_limit_usd=Decimal("10.0000"),
        period_used_usd=Decimal("1.2345"),
        period_starts_at=datetime(2026, 5, 1, 0, 0, tzinfo=timezone.utc),
        per_job_cap_usd=Decimal("0.7500"),
    )
    db.add(q)
    await db.commit()
    await db.refresh(q)
    assert q.monthly_limit_usd == Decimal("10.0000")
    assert q.period_used_usd == Decimal("1.2345")
    assert q.per_job_cap_usd == Decimal("0.7500")


@pytest.mark.asyncio
async def test_ephemeral_token_round_trip(db: AsyncSession, admin_user) -> None:
    tab = await make_tab(db, slug="t1", name="T", order_idx=1)
    agent = await make_agent(db, slug="a1", tab_id=tab.id, created_by_user_id=admin_user.id)
    av = await make_agent_version(db, agent_id=agent.id, created_by_user_id=admin_user.id, status="ready")
    job = await make_job(db, agent_version_id=av.id, user_id=admin_user.id)

    plaintext = "por-job-" + uuid.uuid4().hex
    h = hashlib.sha256(plaintext.encode()).hexdigest()
    tok = EphemeralToken(
        token_hash=h,
        job_id=job.id,
        user_id=admin_user.id,
        agent_version_id=av.id,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=65),
    )
    db.add(tok)
    await db.commit()
    found = await db.get(EphemeralToken, h)
    assert found is not None
    assert found.job_id == job.id
    assert found.revoked_at is None


@pytest.mark.asyncio
async def test_usage_log_round_trip(db: AsyncSession, admin_user) -> None:
    tab = await make_tab(db, slug="t2", name="T", order_idx=1)
    agent = await make_agent(db, slug="a2", tab_id=tab.id, created_by_user_id=admin_user.id)
    av = await make_agent_version(db, agent_id=agent.id, created_by_user_id=admin_user.id, status="ready")
    job = await make_job(db, agent_version_id=av.id, user_id=admin_user.id)

    log = UsageLog(
        job_id=job.id,
        user_id=admin_user.id,
        agent_id=agent.id,
        agent_version_id=av.id,
        model="deepseek/deepseek-chat",
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        cost_usd=Decimal("0.000042"),
        latency_ms=450,
        status="success",
        openrouter_request_id="req-abc-123",
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    assert log.id is not None
    assert log.cost_usd == Decimal("0.000042")
    assert log.status == "success"
