"""Logout: revoke refresh + clear cookies."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.models import RefreshToken, User


@pytest.mark.asyncio
async def test_logout_revokes_refresh(
    user_client: AsyncClient, regular_user: User, db: AsyncSession
) -> None:
    res = await db.execute(select(RefreshToken).where(RefreshToken.user_id == regular_user.id))
    rt_before = res.scalar_one()
    assert rt_before.revoked_at is None

    resp = await user_client.post("/api/auth/logout")
    assert resp.status_code == 200

    await db.refresh(rt_before)
    assert rt_before.revoked_at is not None


@pytest.mark.asyncio
async def test_logout_clears_cookies(user_client: AsyncClient) -> None:
    resp = await user_client.post("/api/auth/logout")
    assert resp.status_code == 200

    # delete_cookie шлёт пустую куку с Max-Age=0
    set_cookies = resp.headers.get_list("set-cookie")
    assert any("access_token=" in c and "Max-Age=0" in c for c in set_cookies)
    assert any("refresh_token=" in c and "Max-Age=0" in c for c in set_cookies)


@pytest.mark.asyncio
async def test_logout_without_refresh_cookie_succeeds(client: AsyncClient) -> None:
    """Идемпотентно: logout без cookies — ОК."""
    resp = await client.post("/api/auth/logout")
    assert resp.status_code == 200
