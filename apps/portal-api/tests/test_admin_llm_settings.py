"""Тесты admin LLM-настроек. Главный инвариант: секрет НИКОГДА не
возвращается клиенту целиком и не попадает в аудит."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.models import AdminAuditLog

_FULL = "sk-or-v1-SECRET-abcdef1234567890"


@pytest.mark.asyncio
async def test_get_requires_admin(client: AsyncClient, user_client: AsyncClient) -> None:
    # non-admin -> 403 (конвенция как в test_admin_audit)
    assert (await user_client.get("/api/admin/llm-settings")).status_code == 403
    # без auth -> не 200
    assert (await client.get("/api/admin/llm-settings")).status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_masked_env_fallback(admin_client: AsyncClient) -> None:
    r = await admin_client.get("/api/admin/llm-settings")
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["provider_mode"] == "openrouter"
    assert b["openrouter_api_key"]["set"] is True
    assert b["openrouter_api_key"]["source"] == "env"
    # preview маскирован (… для длинных, •••• для коротких) — НЕ полный ключ
    prev = b["openrouter_api_key"]["preview"]
    assert prev and ("…" in prev or prev == "••••")
    assert b["openai_api_key"] == {"set": False, "preview": ""}


@pytest.mark.asyncio
async def test_put_key_never_returned_full(admin_client: AsyncClient) -> None:
    r = await admin_client.put(
        "/api/admin/llm-settings", json={"openrouter_api_key": _FULL},
    )
    assert r.status_code == 200, r.text
    assert _FULL not in r.text  # секрет НИКОГДА не в ответе
    b = r.json()
    assert b["openrouter_api_key"]["set"] is True
    assert b["openrouter_api_key"]["source"] == "db"
    g = await admin_client.get("/api/admin/llm-settings")
    assert _FULL not in g.text


@pytest.mark.asyncio
async def test_put_partial_keep_and_clear(admin_client: AsyncClient) -> None:
    await admin_client.put(
        "/api/admin/llm-settings", json={"openai_api_key": "sk-openai-XYZ12345"},
    )
    # отдельный PUT другого поля не трогает openai
    await admin_client.put(
        "/api/admin/llm-settings", json={"provider_mode": "direct"},
    )
    b = (await admin_client.get("/api/admin/llm-settings")).json()
    assert b["openai_api_key"]["set"] is True
    assert b["provider_mode"] == "direct"
    # пустая строка очищает
    await admin_client.put(
        "/api/admin/llm-settings", json={"openai_api_key": ""},
    )
    b2 = (await admin_client.get("/api/admin/llm-settings")).json()
    assert b2["openai_api_key"]["set"] is False


@pytest.mark.asyncio
async def test_put_provider_mode_invalid_coerced(admin_client: AsyncClient) -> None:
    await admin_client.put(
        "/api/admin/llm-settings", json={"provider_mode": "bogus"},
    )
    b = (await admin_client.get("/api/admin/llm-settings")).json()
    assert b["provider_mode"] == "openrouter"


@pytest.mark.asyncio
async def test_audit_logged_without_secret(
    admin_client: AsyncClient, db: AsyncSession,
) -> None:
    await admin_client.put(
        "/api/admin/llm-settings", json={"openrouter_api_key": _FULL},
    )
    rows = (await db.execute(
        select(AdminAuditLog).where(AdminAuditLog.action == "llm_settings.update")
    )).scalars().all()
    assert rows, "audit-запись не создана"
    last = rows[-1]
    assert "openrouter_api_key" in last.payload_jsonb["changed"]
    # секрет НЕ в аудите
    assert _FULL not in str(last.payload_jsonb)
