# ruff: noqa: N817
"""Эндпоинты /api/me — чтение, апдейт, change-password."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.models import RefreshToken, User


@pytest.mark.asyncio
async def test_get_me(user_client: AsyncClient, regular_user: User) -> None:
    resp = await user_client.get("/api/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(regular_user.id)
    assert body["email"] == regular_user.email
    assert body["display_name"] == regular_user.display_name
    assert body["role"] == "user"
    assert "monthly_budget_usd" in body
    assert "password_hash" not in body


@pytest.mark.asyncio
async def test_get_me_without_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/me")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "NOT_AUTHENTICATED"


@pytest.mark.asyncio
async def test_patch_display_name(user_client: AsyncClient, regular_user: User) -> None:
    resp = await user_client.patch("/api/me", json={"display_name": "Новое Имя"})
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "Новое Имя"


@pytest.mark.asyncio
async def test_patch_empty_display_name_rejected(user_client: AsyncClient) -> None:
    resp = await user_client.patch("/api/me", json={"display_name": ""})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_change_password_success(
    user_client: AsyncClient, regular_user: User, db: AsyncSession
) -> None:
    resp = await user_client.post(
        "/api/me/change-password",
        json={"current_password": "test-pass", "new_password": "NewStrongPass123"},
    )
    assert resp.status_code == 200

    # Старый пароль больше не работает
    new_resp = await user_client.post("/api/auth/login", json={
        "email": regular_user.email, "password": "test-pass",
    })
    assert new_resp.status_code == 401

    # Новый — работает
    new_resp2 = await user_client.post("/api/auth/login", json={
        "email": regular_user.email, "password": "NewStrongPass123",
    })
    assert new_resp2.status_code == 200


@pytest.mark.asyncio
async def test_change_password_wrong_current(user_client: AsyncClient) -> None:
    resp = await user_client.post(
        "/api/me/change-password",
        json={"current_password": "wrong", "new_password": "NewStrongPass123"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_change_password_revokes_other_sessions(
    client: AsyncClient, regular_user: User, db: AsyncSession
) -> None:
    """После смены пароля все refresh кроме текущей сессии отзываются."""
    from httpx import ASGITransport
    from httpx import AsyncClient as AC

    from portal_api.main import app

    # Session 1 (наша)
    r1 = await client.post(
        "/api/auth/login", json={"email": regular_user.email, "password": "test-pass"}
    )
    assert r1.status_code == 200

    # Session 2
    async with AC(
        transport=ASGITransport(app=app), base_url="http://test", headers={"Origin": "http://test"}
    ) as c2:
        r2 = await c2.post(
            "/api/auth/login", json={"email": regular_user.email, "password": "test-pass"}
        )
        assert r2.status_code == 200

    # Меняем пароль из session 1
    rp = await client.post(
        "/api/me/change-password",
        json={"current_password": "test-pass", "new_password": "NewPass1234"},
    )
    assert rp.status_code == 200

    # Должна остаться только одна активная — наш текущий refresh
    res = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == regular_user.id,
            RefreshToken.revoked_at.is_(None),
        )
    )
    active = res.scalars().all()
    assert len(active) == 1
