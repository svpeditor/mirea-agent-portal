"""E2E с реальным OpenRouter. Skipped по умолчанию (`-m openrouter_live`).

Стоимость прогона ≈ $0.0005. Требует:
  - OPENROUTER_API_KEY_TEST=sk-or-v1-... в env
  - Docker + portal-api/portal-worker запущены
  - Реестр агентов: echo-llm fixture опубликован как agent_version
"""
from __future__ import annotations

import asyncio
import os
import time
from decimal import Decimal

import pytest
import sqlalchemy as sa

from portal_api.models import Job, UsageLog, UserQuota

pytestmark = pytest.mark.openrouter_live


@pytest.mark.asyncio
async def test_e2e_echo_llm_full_loop(
    client,
    db,
    normal_user,
    normal_user_token,
    admin_user,
    published_echo_llm,
) -> None:  # type: ignore[no-untyped-def]
    if not os.environ.get("OPENROUTER_API_KEY_TEST"):
        pytest.skip("OPENROUTER_API_KEY_TEST not set")

    agent_id, agent_version_id = published_echo_llm

    # POST job
    quota_before = await db.get(UserQuota, normal_user.id)
    used_before = quota_before.period_used_usd

    r = await client.post(
        "/api/agents/echo-llm/jobs",
        headers={"Cookie": f"access_token={normal_user_token}"},
        files={"params": (None, "{}")},
    )
    assert r.status_code in (200, 201, 202)
    body = r.json()
    job_id = body.get("id") or (body.get("job") or {}).get("id")
    assert job_id, f"no job_id in response: {body}"

    # Poll до terminal status
    deadline = time.monotonic() + 120
    final_status = None
    while time.monotonic() < deadline:
        r2 = await client.get(
            f"/api/jobs/{job_id}",
            headers={"Cookie": f"access_token={normal_user_token}"},
        )
        st = r2.json().get("status")
        if st in ("succeeded", "failed", "cancelled", "timed_out"):
            final_status = st
            break
        await asyncio.sleep(2)
    assert final_status == "succeeded", f"job did not succeed: {final_status}"

    # UsageLog записан
    logs = (
        await db.execute(
            sa.select(UsageLog).where(
                UsageLog.job_id == job_id,
                UsageLog.status == "success",
            )
        )
    ).scalars().all()
    assert len(logs) >= 1
    total_log_cost = sum((log.cost_usd for log in logs), start=Decimal("0"))
    assert total_log_cost > Decimal("0")

    # UserQuota.period_used_usd увеличился
    await db.refresh(quota_before)
    assert quota_before.period_used_usd > used_before

    # Job.cost_usd_total синхронизирован с UsageLog
    job = await db.get(Job, job_id)
    await db.refresh(job)
    assert job.cost_usd_total == total_log_cost
