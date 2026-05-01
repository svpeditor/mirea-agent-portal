"""Admin endpoints для invite-токенов."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.models import Invite, User
from tests.factories import InviteFactory, UserFactory


@pytest.mark.asyncio
async def test_create_invite(admin_client: AsyncClient, db: AsyncSession) -> None:
    resp = await admin_client.post(
        "/api/admin/invites",
        json={"email": "newbie@example.com"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "token" in body
    assert body["email"] == "newbie@example.com"
    assert "expires_at" in body
    assert "registration_url" in body

    res = await db.execute(select(Invite).where(Invite.email == "newbie@example.com"))
    assert res.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_create_invite_email_already_registered(
    admin_client: AsyncClient, db: AsyncSession
) -> None:
    """Email уже у зарегистрированного юзера — 409."""
    await UserFactory.create(db, email="existing@example.com")
    await db.commit()

    resp = await admin_client.post(
        "/api/admin/invites", json={"email": "existing@example.com"}
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


@pytest.mark.asyncio
async def test_create_invite_already_pending(
    admin_client: AsyncClient, db: AsyncSession, admin_user: User
) -> None:
    await InviteFactory.create(db, created_by=admin_user, email="pending@example.com")
    await db.commit()

    resp = await admin_client.post(
        "/api/admin/invites", json={"email": "pending@example.com"}
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "INVITE_ALREADY_PENDING"


@pytest.mark.asyncio
async def test_list_invites_active(
    admin_client: AsyncClient, db: AsyncSession, admin_user: User
) -> None:
    await InviteFactory.create(db, created_by=admin_user, email="active1@example.com")
    await InviteFactory.create(
        db, created_by=admin_user, email="used@example.com",
        used_at=datetime.now(UTC),
    )
    await InviteFactory.create(
        db, created_by=admin_user, email="exp@example.com",
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )
    await db.commit()

    resp = await admin_client.get("/api/admin/invites?status=active")
    assert resp.status_code == 200
    emails = [i["email"] for i in resp.json()["invites"]]
    assert "active1@example.com" in emails
    assert "used@example.com" not in emails
    assert "exp@example.com" not in emails


@pytest.mark.asyncio
async def test_list_invites_used(
    admin_client: AsyncClient, db: AsyncSession, admin_user: User
) -> None:
    await InviteFactory.create(
        db, created_by=admin_user, email="u@example.com", used_at=datetime.now(UTC)
    )
    await db.commit()

    resp = await admin_client.get("/api/admin/invites?status=used")
    assert resp.status_code == 200
    assert any(i["email"] == "u@example.com" for i in resp.json()["invites"])


@pytest.mark.asyncio
async def test_cancel_invite(
    admin_client: AsyncClient, db: AsyncSession, admin_user: User
) -> None:
    invite = await InviteFactory.create(db, created_by=admin_user, email="cancel@example.com")
    await db.commit()

    resp = await admin_client.delete(f"/api/admin/invites/{invite.id}")
    assert resp.status_code == 200

    await db.refresh(invite)
    assert invite.used_at is not None


@pytest.mark.asyncio
async def test_create_invite_unauth(client: AsyncClient) -> None:
    resp = await client.post("/api/admin/invites", json={"email": "x@example.com"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_invite_as_user_forbidden(user_client: AsyncClient) -> None:
    resp = await user_client.post("/api/admin/invites", json={"email": "x@example.com"})
    assert resp.status_code == 403
