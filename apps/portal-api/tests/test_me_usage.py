"""GET /api/me/usage — cursor pagination для llm_usage_logs."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from portal_api.models import UsageLog
from tests.factories import (
    make_agent, make_agent_version, make_job, make_tab,
)


@pytest.mark.asyncio
async def test_usage_returns_user_logs_only(
    db, client, normal_user, normal_user_token, admin_user,
) -> None:
    tab = await make_tab(db, slug="t-u", name="T", order_idx=1)
    agent = await make_agent(db, slug="a-u", tab_id=tab.id, created_by_user_id=admin_user.id)
    av = await make_agent_version(db, agent_id=agent.id, created_by_user_id=admin_user.id, status="ready")
    job = await make_job(db, agent_version_id=av.id, user_id=normal_user.id)
    db.add(UsageLog(
        job_id=job.id, user_id=normal_user.id, agent_id=agent.id,
        agent_version_id=av.id, model="deepseek/deepseek-chat",
        prompt_tokens=10, completion_tokens=5, total_tokens=15,
        cost_usd=Decimal("0.0001"), latency_ms=100, status="success",
    ))
    other_job = await make_job(db, agent_version_id=av.id, user_id=admin_user.id)
    db.add(UsageLog(
        job_id=other_job.id, user_id=admin_user.id, agent_id=agent.id,
        agent_version_id=av.id, model="deepseek/deepseek-chat",
        prompt_tokens=99, completion_tokens=99, total_tokens=198,
        cost_usd=Decimal("0.0099"), latency_ms=200, status="success",
    ))
    await db.commit()

    r = await client.get(
        "/api/me/usage?limit=50",
        headers={"Cookie": f"access_token={normal_user_token}"},
    )
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["model"] == "deepseek/deepseek-chat"
    assert items[0]["prompt_tokens"] == 10


@pytest.mark.asyncio
async def test_usage_cursor_pagination(
    db, client, normal_user, normal_user_token, admin_user,
) -> None:
    tab = await make_tab(db, slug="t-u2", name="T", order_idx=1)
    agent = await make_agent(db, slug="a-u2", tab_id=tab.id, created_by_user_id=admin_user.id)
    av = await make_agent_version(db, agent_id=agent.id, created_by_user_id=admin_user.id, status="ready")
    job = await make_job(db, agent_version_id=av.id, user_id=normal_user.id)
    base_ts = datetime.now(timezone.utc)
    for i in range(5):
        db.add(UsageLog(
            job_id=job.id, user_id=normal_user.id, agent_id=agent.id,
            agent_version_id=av.id, model="m", prompt_tokens=i, completion_tokens=i,
            total_tokens=2*i, cost_usd=Decimal("0.001"), latency_ms=10, status="success",
            created_at=base_ts - timedelta(minutes=i),
        ))
    await db.commit()

    r = await client.get(
        "/api/me/usage?limit=2",
        headers={"Cookie": f"access_token={normal_user_token}"},
    )
    body = r.json()
    assert len(body["items"]) == 2
    cursor = body["next_cursor"]
    assert cursor is not None

    r2 = await client.get(
        f"/api/me/usage?limit=2&cursor={cursor}",
        headers={"Cookie": f"access_token={normal_user_token}"},
    )
    body2 = r2.json()
    assert len(body2["items"]) == 2
