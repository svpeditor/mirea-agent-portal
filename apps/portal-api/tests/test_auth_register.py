"""Регистрация по invite-токену."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.models import Invite, User
from tests.factories import InviteFactory, UserFactory


@pytest.mark.asyncio
async def test_register_with_valid_invite(
    client: AsyncClient, db: AsyncSession, admin_user: User
) -> None:
    invite = await InviteFactory.create(db, created_by=admin_user, email="new@example.com")
    await db.commit()

    resp = await client.post(
        "/api/auth/register",
        json={
            "token": invite.token,
            "email": "new@example.com",
            "display_name": "Новый Юзер",
            "password": "Strong1234",
        },
    )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["user"]["email"] == "new@example.com"
    assert body["user"]["display_name"] == "Новый Юзер"
    assert body["user"]["role"] == "user"

    # Cookies стоят
    assert "access_token" in resp.cookies
    assert "refresh_token" in resp.cookies

    # Юзер создан в БД
    res = await db.execute(select(User).where(User.email == "new@example.com"))
    assert res.scalar_one_or_none() is not None

    # Invite помечен used
    res2 = await db.execute(select(Invite).where(Invite.id == invite.id))
    used = res2.scalar_one()
    assert used.used_at is not None


@pytest.mark.asyncio
async def test_register_with_unknown_token(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/auth/register",
        json={
            "token": "nope-not-a-real-token",
            "email": "x@example.com",
            "display_name": "X",
            "password": "Strong1234",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVITE_INVALID"


@pytest.mark.asyncio
async def test_register_with_used_token(
    client: AsyncClient, db: AsyncSession, admin_user: User
) -> None:
    invite = await InviteFactory.create(
        db, created_by=admin_user, email="used@example.com",
        used_at=datetime.now(UTC),
    )
    await db.commit()

    resp = await client.post(
        "/api/auth/register",
        json={
            "token": invite.token,
            "email": "used@example.com",
            "display_name": "X",
            "password": "Strong1234",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVITE_INVALID"


@pytest.mark.asyncio
async def test_register_with_expired_token(
    client: AsyncClient, db: AsyncSession, admin_user: User
) -> None:
    invite = await InviteFactory.create(
        db, created_by=admin_user, email="exp@example.com",
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )
    await db.commit()

    resp = await client.post(
        "/api/auth/register",
        json={
            "token": invite.token,
            "email": "exp@example.com",
            "display_name": "X",
            "password": "Strong1234",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVITE_INVALID"


@pytest.mark.asyncio
async def test_register_email_mismatch(
    client: AsyncClient, db: AsyncSession, admin_user: User
) -> None:
    invite = await InviteFactory.create(db, created_by=admin_user, email="alpha@example.com")
    await db.commit()

    resp = await client.post(
        "/api/auth/register",
        json={
            "token": invite.token,
            "email": "beta@example.com",  # другой email
            "display_name": "X",
            "password": "Strong1234",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVITE_INVALID"


@pytest.mark.asyncio
async def test_register_short_password(
    client: AsyncClient, db: AsyncSession, admin_user: User
) -> None:
    invite = await InviteFactory.create(db, created_by=admin_user, email="x@example.com")
    await db.commit()

    resp = await client.post(
        "/api/auth/register",
        json={
            "token": invite.token,
            "email": "x@example.com",
            "display_name": "X",
            "password": "short",  # < 8 символов
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_empty_display_name(
    client: AsyncClient, db: AsyncSession, admin_user: User
) -> None:
    invite = await InviteFactory.create(db, created_by=admin_user, email="x@example.com")
    await db.commit()

    resp = await client.post(
        "/api/auth/register",
        json={
            "token": invite.token,
            "email": "x@example.com",
            "display_name": "",
            "password": "Strong1234",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_email_normalized_lowercase(
    client: AsyncClient, db: AsyncSession, admin_user: User
) -> None:
    invite = await InviteFactory.create(db, created_by=admin_user, email="case@example.com")
    await db.commit()

    resp = await client.post(
        "/api/auth/register",
        json={
            "token": invite.token,
            "email": "CASE@EXAMPLE.com",  # верхний регистр
            "display_name": "X",
            "password": "Strong1234",
        },
    )
    assert resp.status_code == 201

    res = await db.execute(select(User).where(User.email == "case@example.com"))
    assert res.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_register_email_already_exists(
    client: AsyncClient, db: AsyncSession, admin_user: User
) -> None:
    """Юзер с этим email уже есть в БД."""
    await UserFactory.create(db, email="dup@example.com")
    invite = await InviteFactory.create(db, created_by=admin_user, email="dup@example.com")
    await db.commit()

    resp = await client.post(
        "/api/auth/register",
        json={
            "token": invite.token,
            "email": "dup@example.com",
            "display_name": "X",
            "password": "Strong1234",
        },
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_register_double_use_race(
    client: AsyncClient, db: AsyncSession, admin_user: User
) -> None:
    """Один и тот же токен второй раз — fail."""
    invite = await InviteFactory.create(db, created_by=admin_user, email="race@example.com")
    await db.commit()

    body = {
        "token": invite.token,
        "email": "race@example.com",
        "display_name": "X",
        "password": "Strong1234",
    }
    r1 = await client.post("/api/auth/register", json=body)
    assert r1.status_code == 201

    # Создадим новый клиент чтобы не было запутывания cookie
    body2 = {**body, "email": "race@example.com", "display_name": "Y"}
    r2 = await client.post("/api/auth/register", json=body2)
    assert r2.status_code == 400
    assert r2.json()["error"]["code"] == "INVITE_INVALID"
