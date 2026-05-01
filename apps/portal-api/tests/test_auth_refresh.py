"""Refresh-token rotation + reuse detection."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.models import RefreshToken, User


@pytest.mark.asyncio
async def test_refresh_rotates_token(
    user_client: AsyncClient, regular_user: User, db: AsyncSession
) -> None:
    old_refresh = user_client.cookies.get("refresh_token")
    assert old_refresh

    resp = await user_client.post("/api/auth/refresh")
    assert resp.status_code == 200

    new_refresh = resp.cookies.get("refresh_token")
    assert new_refresh
    assert new_refresh != old_refresh

    # В БД старый помечен revoked, новый создан, replaced_by_id указывает на новый
    res = await db.execute(
        select(RefreshToken).where(RefreshToken.user_id == regular_user.id)
    )
    tokens = res.scalars().all()
    assert len(tokens) == 2
    revoked = next(t for t in tokens if t.revoked_at is not None)
    active = next(t for t in tokens if t.revoked_at is None)
    assert revoked.replaced_by_id == active.id


@pytest.mark.asyncio
async def test_refresh_reuse_detection(
    client: AsyncClient, regular_user: User, db: AsyncSession
) -> None:
    """Использование уже отозванного refresh -> revoke ВСЕ + 401."""
    # Логинимся
    resp = await client.post(
        "/api/auth/login",
        json={"email": regular_user.email, "password": "test-pass"},
    )
    assert resp.status_code == 200
    refresh_v1 = client.cookies.get("refresh_token")

    # Используем refresh - получаем новый
    r2 = await client.post("/api/auth/refresh")
    assert r2.status_code == 200
    refresh_v2 = client.cookies.get("refresh_token")

    # Возвращаем v1 (как-будто его украли)
    client.cookies.set("refresh_token", refresh_v1)
    r3 = await client.post("/api/auth/refresh")
    assert r3.status_code == 401
    assert r3.json()["error"]["code"] == "REFRESH_REUSE_DETECTED"

    # Все refresh этого юзера теперь revoked, включая v2
    res = await db.execute(
        select(RefreshToken).where(RefreshToken.user_id == regular_user.id)
    )
    tokens = res.scalars().all()
    assert all(t.revoked_at is not None for t in tokens), \
        f"некоторые refresh не отозваны: {tokens}"
    # Suppress unused var warning
    _ = refresh_v2


@pytest.mark.asyncio
async def test_refresh_unknown_token(client: AsyncClient) -> None:
    client.cookies.set("refresh_token", "totally-bogus-token")
    resp = await client.post("/api/auth/refresh")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "REFRESH_INVALID"


@pytest.mark.asyncio
async def test_refresh_no_cookie(client: AsyncClient) -> None:
    resp = await client.post("/api/auth/refresh")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "REFRESH_INVALID"


@pytest.mark.asyncio
async def test_refresh_expired_token(
    client: AsyncClient, regular_user: User, db: AsyncSession
) -> None:
    """Refresh прошёл expires_at."""
    from portal_api.core.security import generate_refresh_token

    raw, h = generate_refresh_token()
    expired = RefreshToken(
        user_id=regular_user.id,
        token_hash=h,
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )
    db.add(expired)
    await db.commit()

    client.cookies.set("refresh_token", raw)
    resp = await client.post("/api/auth/refresh")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "REFRESH_INVALID"


@pytest.mark.asyncio
async def test_refresh_other_session_keeps_working(
    client: AsyncClient, regular_user: User
) -> None:
    """Refresh одной сессии не трогает другие refresh-токены этого юзера."""
    from httpx import ASGITransport, AsyncClient

    from portal_api.main import app

    # Login session 1
    r1 = await client.post(
        "/api/auth/login",
        json={"email": regular_user.email, "password": "test-pass"},
    )
    assert r1.status_code == 200
    rt_session1 = client.cookies.get("refresh_token")

    # Login session 2 (отдельный клиент)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Origin": "http://test"},
    ) as c2:
        r2 = await c2.post(
            "/api/auth/login",
            json={"email": regular_user.email, "password": "test-pass"},
        )
        assert r2.status_code == 200
        rt_session2 = c2.cookies.get("refresh_token")
        assert rt_session1 != rt_session2

        # Session 1 ротирует
        client.cookies.set("refresh_token", rt_session1)
        r3 = await client.post("/api/auth/refresh")
        assert r3.status_code == 200

        # Session 2 всё ещё валиден
        c2.cookies.set("refresh_token", rt_session2)
        r4 = await c2.post("/api/auth/refresh")
        assert r4.status_code == 200
