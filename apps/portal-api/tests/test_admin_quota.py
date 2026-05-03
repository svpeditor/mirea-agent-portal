"""PATCH /api/admin/users/{id}/quota + POST .../reset + расширенный GET /api/admin/users/{id}."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from portal_api.models import UserQuota
from tests.factories import make_user


@pytest.mark.asyncio
async def test_get_admin_user_returns_quota(db, client, admin_user, admin_token) -> None:
    target = await make_user(db, email="t1@x.x", password="testpasswordX1")
    db.add(UserQuota(
        user_id=target.id, monthly_limit_usd=Decimal("5"), period_used_usd=Decimal("0"),
        period_starts_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        per_job_cap_usd=Decimal("0.5"),
    ))
    await db.commit()

    r = await client.get(
        f"/api/admin/users/{target.id}",
        headers={"Cookie": f"access_token={admin_token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["quota"]["monthly_limit_usd"] == "5.0000"


@pytest.mark.asyncio
async def test_patch_quota(db, client, admin_user, admin_token) -> None:
    target = await make_user(db, email="t2@x.x", password="testpasswordX1")
    db.add(UserQuota(
        user_id=target.id, monthly_limit_usd=Decimal("5"), period_used_usd=Decimal("0"),
        period_starts_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        per_job_cap_usd=Decimal("0.5"),
    ))
    await db.commit()

    r = await client.patch(
        f"/api/admin/users/{target.id}/quota",
        headers={"Cookie": f"access_token={admin_token}"},
        json={"monthly_limit_usd": "10.0", "per_job_cap_usd": "2.0"},
    )
    assert r.status_code == 200
    assert r.json()["monthly_limit_usd"] == "10.0000"
    assert r.json()["per_job_cap_usd"] == "2.0000"

    q = await db.get(UserQuota, target.id)
    await db.refresh(q)
    assert q.monthly_limit_usd == Decimal("10.0000")
    assert q.per_job_cap_usd == Decimal("2.0000")


@pytest.mark.asyncio
async def test_reset_quota(db, client, admin_user, admin_token) -> None:
    target = await make_user(db, email="t3@x.x", password="testpasswordX1")
    db.add(UserQuota(
        user_id=target.id, monthly_limit_usd=Decimal("5"), period_used_usd=Decimal("3.5"),
        period_starts_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        per_job_cap_usd=Decimal("0.5"),
    ))
    await db.commit()

    r = await client.post(
        f"/api/admin/users/{target.id}/quota/reset",
        headers={"Cookie": f"access_token={admin_token}"},
    )
    assert r.status_code == 200
    assert r.json()["period_used_usd"] == "0.0000"


@pytest.mark.asyncio
async def test_non_admin_cannot_patch_quota(db, client, normal_user, normal_user_token) -> None:
    r = await client.patch(
        f"/api/admin/users/{normal_user.id}/quota",
        headers={"Cookie": f"access_token={normal_user_token}"},
        json={"monthly_limit_usd": "9999.0"},
    )
    assert r.status_code == 403
