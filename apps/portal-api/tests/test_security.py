"""Security: cookie attrs, Origin check, no user enumeration, нет паролей в response."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from portal_api.models import User


@pytest.mark.asyncio
async def test_cookies_have_security_attributes(
    client: AsyncClient, regular_user: User
) -> None:
    resp = await client.post(
        "/api/auth/login",
        json={"email": regular_user.email, "password": "test-pass"},
    )
    assert resp.status_code == 200

    set_cookies = resp.headers.get_list("set-cookie")
    access_cookie = next(c for c in set_cookies if c.startswith("access_token="))
    refresh_cookie = next(c for c in set_cookies if c.startswith("refresh_token="))

    # samesite=lax (а не strict) — нужен для cross-port WebSocket handshake.
    # path=/ (а не /api) — frontend rewrite на корне.
    # См. fixes 6b12d39 (WS cross-port) и b466452 (cookie path /api → /).
    assert "HttpOnly" in access_cookie
    assert "samesite=lax" in access_cookie.lower().replace(" ", "")
    assert "Path=/" in access_cookie

    assert "HttpOnly" in refresh_cookie
    assert "Path=/" in refresh_cookie


@pytest.mark.asyncio
async def test_post_with_bad_origin_rejected(
    client: AsyncClient, regular_user: User
) -> None:
    resp = await client.post(
        "/api/auth/login",
        json={"email": regular_user.email, "password": "test-pass"},
        headers={"Origin": "https://evil.example"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "ORIGIN_MISMATCH"


@pytest.mark.asyncio
async def test_get_with_bad_origin_allowed(
    user_client: AsyncClient
) -> None:
    """GET идемпотентен и не проверяется."""
    resp = await user_client.get("/api/me", headers={"Origin": "https://evil.example"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_llm_proxy_post_without_origin_not_blocked_by_middleware(
    client: AsyncClient,
) -> None:
    """POST на /llm/v1/* без Origin не должен ловить ORIGIN_MISMATCH.

    Агентский контейнер в изолированной docker-сети не выставляет Origin —
    аутентификация идёт по Bearer-токену (ephemeral), CSRF неприменим.
    Без exempt'а middleware блокировал бы все вызовы LLM из агентов 403.

    Тест проверяет именно факт прохождения middleware (любой не-403
    ответ от роутера). Реальный ответ зависит от токена: без него — 401
    из ephemeral_token_auth, а не 403 от Origin-проверки.
    """
    resp = await client.post(
        "/llm/v1/chat/completions",
        json={"model": "deepseek/deepseek-chat", "messages": []},
    )
    assert resp.status_code != 403, (
        "Origin middleware заблокировал LLM-прокси — добавь /llm/v1 "
        "в _BEARER_AUTH_PREFIXES (apps/portal-api/portal_api/core/origin.py)"
    )


@pytest.mark.asyncio
async def test_no_user_enumeration_in_login(client: AsyncClient, regular_user: User) -> None:
    """Login с неверным паролем и login несуществующего юзера дают одинаковую ошибку."""
    r1 = await client.post(
        "/api/auth/login",
        json={"email": regular_user.email, "password": "wrong-pass"},
    )
    r2 = await client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "wrong-pass"},
    )
    assert r1.status_code == r2.status_code == 401
    assert r1.json() == r2.json()


@pytest.mark.asyncio
async def test_password_hash_never_in_response(
    user_client: AsyncClient, admin_client: AsyncClient, regular_user: User
) -> None:
    """Ни один эндпоинт не возвращает password_hash."""
    r1 = await user_client.get("/api/me")
    assert "password_hash" not in r1.text
    assert "password" not in r1.text  # ни в каком виде

    r2 = await admin_client.get(f"/api/admin/users/{regular_user.id}")
    assert "password_hash" not in r2.text
