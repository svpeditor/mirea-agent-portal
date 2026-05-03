"""GET /api/admin/usage: aggregation by_user / by_agent / by_model."""
from __future__ import annotations

from decimal import Decimal

import pytest

from portal_api.models import UsageLog
from tests.factories import (
    make_agent, make_agent_version, make_job, make_tab, make_user,
)


@pytest.mark.asyncio
async def test_admin_usage_summary(db, client, admin_user, admin_token) -> None:
    user1 = await make_user(db, email="u1@x.x", password="testpasswordX1")
    user2 = await make_user(db, email="u2@x.x", password="testpasswordX1")
    tab = await make_tab(db, slug="t-au", name="T", order_idx=1)
    agent_a = await make_agent(db, slug="aa", tab_id=tab.id, created_by_user_id=admin_user.id)
    agent_b = await make_agent(db, slug="bb", tab_id=tab.id, created_by_user_id=admin_user.id)
    av_a = await make_agent_version(db, agent_id=agent_a.id, created_by_user_id=admin_user.id, status="ready")
    av_b = await make_agent_version(db, agent_id=agent_b.id, created_by_user_id=admin_user.id, status="ready")
    job1 = await make_job(db, agent_version_id=av_a.id, user_id=user1.id)
    job2 = await make_job(db, agent_version_id=av_b.id, user_id=user2.id)

    db.add(UsageLog(
        job_id=job1.id, user_id=user1.id, agent_id=agent_a.id, agent_version_id=av_a.id,
        model="m1", prompt_tokens=10, completion_tokens=5, total_tokens=15,
        cost_usd=Decimal("0.1"), latency_ms=100, status="success",
    ))
    db.add(UsageLog(
        job_id=job2.id, user_id=user2.id, agent_id=agent_b.id, agent_version_id=av_b.id,
        model="m2", prompt_tokens=20, completion_tokens=10, total_tokens=30,
        cost_usd=Decimal("0.2"), latency_ms=200, status="success",
    ))
    db.add(UsageLog(
        job_id=job1.id, user_id=user1.id, agent_id=agent_a.id, agent_version_id=av_a.id,
        model="m1", prompt_tokens=5, completion_tokens=3, total_tokens=8,
        cost_usd=Decimal("0.05"), latency_ms=50, status="success",
    ))
    await db.commit()

    r = await client.get(
        "/api/admin/usage",
        headers={"Cookie": f"access_token={admin_token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total_requests"] == 3
    assert body["total_cost_usd"] == "0.350000"
    by_user_map = {u["email"]: u for u in body["by_user"]}
    assert by_user_map["u1@x.x"]["cost_usd"] == "0.150000"
    assert by_user_map["u2@x.x"]["cost_usd"] == "0.200000"


@pytest.mark.asyncio
async def test_admin_usage_filtered_by_agent(db, client, admin_user, admin_token) -> None:
    user = await make_user(db, email="uf@x.x", password="testpasswordX1")
    tab = await make_tab(db, slug="t-aufa", name="T", order_idx=1)
    agent = await make_agent(db, slug="aa-f", tab_id=tab.id, created_by_user_id=admin_user.id)
    av = await make_agent_version(db, agent_id=agent.id, created_by_user_id=admin_user.id, status="ready")
    job = await make_job(db, agent_version_id=av.id, user_id=user.id)
    db.add(UsageLog(
        job_id=job.id, user_id=user.id, agent_id=agent.id, agent_version_id=av.id,
        model="x", prompt_tokens=1, completion_tokens=1, total_tokens=2,
        cost_usd=Decimal("0.01"), latency_ms=10, status="success",
    ))
    await db.commit()

    r = await client.get(
        f"/api/admin/usage?agent_id={agent.id}",
        headers={"Cookie": f"access_token={admin_token}"},
    )
    assert r.status_code == 200
    assert r.json()["total_requests"] == 1
