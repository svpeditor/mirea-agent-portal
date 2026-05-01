"""Login + защита от user enumeration."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.models import User


@pytest.mark.asyncio
async def test_login_with_valid_credentials(client: AsyncClient, regular_user: User) -> None:
    resp = await client.post(
        "/api/auth/login",
        json={"email": regular_user.email, "password": "test-pass"},
    )
    assert resp.status_code == 200
    assert resp.json()["user"]["email"] == regular_user.email
    assert "access_token" in resp.cookies
    assert "refresh_token" in resp.cookies


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, regular_user: User) -> None:
    resp = await client.post(
        "/api/auth/login",
        json={"email": regular_user.email, "password": "wrong"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_unknown_user(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "anything"},
    )
    # Тот же код, что и для wrong-password — нет user enumeration
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_email_case_insensitive(client: AsyncClient, regular_user: User) -> None:
    resp = await client.post(
        "/api/auth/login",
        json={"email": regular_user.email.upper(), "password": "test-pass"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_login_missing_password(client: AsyncClient, regular_user: User) -> None:
    resp = await client.post(
        "/api/auth/login",
        json={"email": regular_user.email, "password": ""},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_unknown_user_actually_runs_bcrypt(client: AsyncClient) -> None:
    """Timing-pad: dummy hash must be valid bcrypt so verify_password actually runs the work."""
    from portal_api.core.security import verify_password
    from portal_api.services.auth_service import _get_dummy_hash

    h = _get_dummy_hash()
    # Must start with a valid bcrypt prefix and have correct length
    assert h.startswith(("$2a$", "$2b$", "$2y$"))
    assert len(h) == 60

    # Must NOT raise — must actually run and return False
    result = verify_password("anything", h)
    assert result is False


@pytest.mark.asyncio
async def test_login_creates_refresh_token_in_db(
    client: AsyncClient, regular_user: User, db: AsyncSession
) -> None:
    from sqlalchemy import select

    from portal_api.models import RefreshToken

    resp = await client.post(
        "/api/auth/login",
        json={"email": regular_user.email, "password": "test-pass"},
    )
    assert resp.status_code == 200

    res = await db.execute(
        select(RefreshToken).where(RefreshToken.user_id == regular_user.id)
    )
    tokens = res.scalars().all()
    assert len(tokens) == 1
    assert tokens[0].revoked_at is None
