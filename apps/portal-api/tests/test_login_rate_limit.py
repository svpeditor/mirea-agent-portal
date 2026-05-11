"""Login rate limit (5 неудачных попыток / 15 мин → 429)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from portal_api.models import User
from portal_api.services.login_rate_limit import LoginRateLimit


def _override_redis(redis_url: str):
    from portal_api.config import get_settings as cfg_get_settings
    from portal_api.deps import get_settings as deps_get_settings
    from portal_api.main import app

    base = cfg_get_settings()
    object.__setattr__(base, "redis_url", redis_url)
    app.dependency_overrides[deps_get_settings] = lambda: base

    def cleanup() -> None:
        app.dependency_overrides.pop(deps_get_settings, None)

    return cleanup


@pytest.mark.asyncio
async def test_six_wrong_passwords_returns_429(
    client: AsyncClient, regular_user: User, redis_url: str, reset_redis,
) -> None:
    cleanup = _override_redis(redis_url)
    try:
        # 5 попыток с неверным паролем — все 401
        for _ in range(5):
            r = await client.post(
                "/api/auth/login",
                json={"email": regular_user.email, "password": "bad"},
            )
            assert r.status_code == 401

        # 6-я даёт 429
        r = await client.post(
            "/api/auth/login",
            json={"email": regular_user.email, "password": "bad"},
        )
        assert r.status_code == 429
        assert r.json()["error"]["code"] == "LOGIN_RATE_LIMITED"
        assert "Retry-After" in r.headers
        retry_after = int(r.headers["Retry-After"])
        assert 0 < retry_after <= 15 * 60
    finally:
        cleanup()


@pytest.mark.asyncio
async def test_successful_login_resets_counter(
    client: AsyncClient, regular_user: User, redis_url: str, reset_redis,
) -> None:
    """4 неудачных попыток + успешная — счётчик сбрасывается, можно ещё."""
    cleanup = _override_redis(redis_url)
    try:
        for _ in range(4):
            r = await client.post(
                "/api/auth/login",
                json={"email": regular_user.email, "password": "bad"},
            )
            assert r.status_code == 401

        # успешный логин
        r = await client.post(
            "/api/auth/login",
            json={"email": regular_user.email, "password": "test-pass"},
        )
        assert r.status_code == 200

        # снова 5 неудачных — должны проходить (счётчик сброшен)
        for _ in range(5):
            r = await client.post(
                "/api/auth/login",
                json={"email": regular_user.email, "password": "bad"},
            )
            assert r.status_code == 401
    finally:
        cleanup()


@pytest.mark.asyncio
async def test_redis_down_fails_open(client: AsyncClient, regular_user: User) -> None:
    """Если Redis недоступен — login работает (fail-open)."""
    cleanup = _override_redis("redis://127.0.0.1:1/0")
    try:
        r = await client.post(
            "/api/auth/login",
            json={"email": regular_user.email, "password": "test-pass"},
        )
        assert r.status_code == 200
    finally:
        cleanup()


@pytest.mark.asyncio
async def test_rate_limit_per_email(
    client: AsyncClient, regular_user: User, redis_url: str, reset_redis,
) -> None:
    """Лимит изолирует email-ы — 5 попыток для one@ не блокируют two@."""
    cleanup = _override_redis(redis_url)
    try:
        for _ in range(5):
            r = await client.post(
                "/api/auth/login",
                json={"email": "one@example.com", "password": "bad"},
            )
            assert r.status_code == 401

        # для другого email — всё ещё открыт
        r = await client.post(
            "/api/auth/login",
            json={"email": regular_user.email, "password": "test-pass"},
        )
        assert r.status_code == 200
    finally:
        cleanup()


@pytest.mark.asyncio
async def test_service_check_isolated(redis_url: str, reset_redis) -> None:
    """Прямые вызовы LoginRateLimit (без HTTP)."""
    rl = LoginRateLimit(redis_url=redis_url, limit=3, window_seconds=60)
    ip = "1.2.3.4"
    email = "x@y.z"
    for _ in range(3):
        allowed, _ = await rl.check(ip, email)
        assert allowed is True
        await rl.record_failure(ip, email)

    allowed, retry_after = await rl.check(ip, email)
    assert allowed is False
    assert retry_after > 0

    await rl.reset(ip, email)
    allowed, _ = await rl.check(ip, email)
    assert allowed is True
