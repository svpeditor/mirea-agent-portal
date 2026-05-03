"""GET /api/me возвращает поле quota."""
from __future__ import annotations

from decimal import Decimal

import pytest


@pytest.mark.asyncio
async def test_me_returns_quota(client, normal_user, normal_user_token) -> None:
    r = await client.get(
        "/api/me",
        headers={"Cookie": f"access_token={normal_user_token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "quota" in body
    q = body["quota"]
    assert q["monthly_limit_usd"] == "5.0000"
    assert q["per_job_cap_usd"] == "0.5000"
    assert q["period_used_usd"] == "0.0000"
    assert "period_starts_at" in q
