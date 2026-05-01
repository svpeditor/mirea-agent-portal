"""Admin endpoints для управления юзерами."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.models import User
from tests.factories import UserFactory


@pytest.mark.asyncio
async def test_list_users_as_admin(
    admin_client: AsyncClient, db: AsyncSession, admin_user: User
) -> None:
    await UserFactory.create(db, email="alpha@example.com")
    await UserFactory.create(db, email="beta@example.com")
    await db.commit()

    resp = await admin_client.get("/api/admin/users")
    assert resp.status_code == 200
    body = resp.json()
    emails = [u["email"] for u in body["users"]]
    assert "alpha@example.com" in emails
    assert "beta@example.com" in emails
    assert admin_user.email in emails


@pytest.mark.asyncio
async def test_list_users_as_regular_forbidden(user_client: AsyncClient) -> None:
    resp = await user_client.get("/api/admin/users")
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_list_users_unauth(client: AsyncClient) -> None:
    resp = await client.get("/api/admin/users")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_user_by_id(
    admin_client: AsyncClient, db: AsyncSession
) -> None:
    target = await UserFactory.create(db, email="target@example.com")
    await db.commit()

    resp = await admin_client.get(f"/api/admin/users/{target.id}")
    assert resp.status_code == 200
    assert resp.json()["email"] == "target@example.com"


@pytest.mark.asyncio
async def test_get_user_not_found(admin_client: AsyncClient) -> None:
    import uuid
    resp = await admin_client.get(f"/api/admin/users/{uuid.uuid4()}")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "USER_NOT_FOUND"


@pytest.mark.asyncio
async def test_patch_user_role(
    admin_client: AsyncClient, db: AsyncSession
) -> None:
    target = await UserFactory.create(db, email="promo@example.com")
    await db.commit()

    resp = await admin_client.patch(
        f"/api/admin/users/{target.id}",
        json={"role": "admin"},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"


@pytest.mark.asyncio
async def test_patch_user_invalid_role(
    admin_client: AsyncClient, db: AsyncSession
) -> None:
    target = await UserFactory.create(db, email="x@example.com")
    await db.commit()

    resp = await admin_client.patch(
        f"/api/admin/users/{target.id}",
        json={"role": "superadmin"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_delete_user(
    admin_client: AsyncClient, db: AsyncSession
) -> None:
    target = await UserFactory.create(db, email="bye@example.com")
    await db.commit()

    resp = await admin_client.delete(f"/api/admin/users/{target.id}")
    assert resp.status_code == 200

    res = await db.execute(select(User).where(User.id == target.id))
    assert res.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_reset_password(
    admin_client: AsyncClient, db: AsyncSession
) -> None:
    target = await UserFactory.create(db, email="forgot@example.com", password="OriginalPass")
    await db.commit()
    original_hash = target.password_hash

    resp = await admin_client.post(f"/api/admin/users/{target.id}/reset-password")
    assert resp.status_code == 200
    body = resp.json()
    assert "temporary_password" in body
    assert len(body["temporary_password"]) >= 12

    # Hash изменился
    await db.refresh(target)
    assert target.password_hash != original_hash


@pytest.mark.asyncio
async def test_reset_password_revokes_refresh(
    admin_client: AsyncClient, db: AsyncSession
) -> None:
    """После reset-password все refresh-токены этого юзера revoked."""
    from httpx import ASGITransport
    from httpx import AsyncClient as AsyncClient2

    from portal_api.main import app
    from portal_api.models import RefreshToken

    target = await UserFactory.create(db, email="logged@example.com", password="OldPass1234")
    await db.commit()

    # Залогиним target в отдельный клиент
    async with AsyncClient2(
        transport=ASGITransport(app=app), base_url="http://test", headers={"Origin": "http://test"}
    ) as c2:
        r = await c2.post(
            "/api/auth/login",
            json={"email": "logged@example.com", "password": "OldPass1234"},
        )
        assert r.status_code == 200

    # Админ ресетит
    resp = await admin_client.post(f"/api/admin/users/{target.id}/reset-password")
    assert resp.status_code == 200

    # Refresh у target всё revoked
    res = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == target.id,
            RefreshToken.revoked_at.is_(None),
        )
    )
    assert res.scalars().first() is None
