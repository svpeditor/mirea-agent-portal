"""End-to-end через FastAPI: POST /llm/v1/chat/completions с реальным httpx mock."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import httpx
import pytest
import respx

from portal_api.models import UserQuota
from portal_api.services import ephemeral_token as eph_svc
from tests.factories import (
    make_agent, make_agent_version, make_job, make_tab, make_user,
)


@pytest.mark.asyncio
async def test_post_chat_completions_non_stream(client, db, admin_user) -> None:
    from portal_api.db import get_db as _db_get_db
    from portal_api.main import app
    from portal_api.services.llm_pricing import ModelPricing, PricingCache

    # Настроить pricing_cache в app.state
    cache = PricingCache(base_url="https://openrouter.ai/api/v1", timeout_s=5.0)
    cache._data["deepseek/deepseek-chat"] = ModelPricing(  # noqa: SLF001
        model="deepseek/deepseek-chat",
        prompt_per_token=Decimal("0.00000014"),
        completion_per_token=Decimal("0.00000028"),
        context_length=64000,
    )
    app.state.pricing_cache = cache

    # Также переопределить portal_api.db.get_db (используется в ephemeral_token_auth)
    async def _override_db():
        yield db

    app.dependency_overrides[_db_get_db] = _override_db

    user = await make_user(db, email="r@x.x", password="testpasswordX1")
    db.add(UserQuota(
        user_id=user.id, monthly_limit_usd=Decimal("5"),
        period_used_usd=Decimal("0"),
        period_starts_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        per_job_cap_usd=Decimal("0.5"),
    ))
    tab = await make_tab(db, slug="t-r", name="T", order_idx=1)
    agent = await make_agent(db, slug="a-r", tab_id=tab.id, created_by_user_id=admin_user.id)
    av = await make_agent_version(
        db, agent_id=agent.id, created_by_user_id=admin_user.id, status="ready",
        manifest_jsonb={"runtime": {"llm": {"provider": "openrouter", "models": ["deepseek/deepseek-chat"]}}},
    )
    job = await make_job(db, agent_version_id=av.id, user_id=user.id)
    plain, _ = eph_svc.generate()
    await eph_svc.insert(
        db, plaintext=plain, job_id=job.id, user_id=user.id,
        agent_version_id=av.id, ttl=timedelta(minutes=65),
    )
    await db.flush()

    with respx.mock(base_url="https://openrouter.ai/api/v1") as mock:
        mock.post("/chat/completions").mock(return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": "ok"}}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
            },
        ))
        resp = await client.post(
            "/llm/v1/chat/completions",
            headers={"Authorization": f"Bearer {plain}"},
            json={"model": "deepseek/deepseek-chat", "messages": [{"role": "user", "content": "Hi"}]},
        )
    assert resp.status_code == 200
    assert resp.json()["choices"][0]["message"]["content"] == "ok"


@pytest.mark.asyncio
async def test_post_chat_completions_streaming(client, db, admin_user) -> None:
    from portal_api.db import get_db as _db_get_db
    from portal_api.main import app
    from portal_api.services.llm_pricing import ModelPricing, PricingCache

    # Настроить pricing_cache в app.state
    cache = PricingCache(base_url="https://openrouter.ai/api/v1", timeout_s=5.0)
    cache._data["deepseek/deepseek-chat"] = ModelPricing(  # noqa: SLF001
        model="deepseek/deepseek-chat",
        prompt_per_token=Decimal("0.00000014"),
        completion_per_token=Decimal("0.00000028"),
        context_length=64000,
    )
    app.state.pricing_cache = cache

    # Также переопределить portal_api.db.get_db (используется в ephemeral_token_auth)
    async def _override_db():
        yield db

    app.dependency_overrides[_db_get_db] = _override_db

    user = await make_user(db, email="rs@x.x", password="testpasswordX1")
    db.add(UserQuota(
        user_id=user.id, monthly_limit_usd=Decimal("5"),
        period_used_usd=Decimal("0"),
        period_starts_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        per_job_cap_usd=Decimal("0.5"),
    ))
    tab = await make_tab(db, slug="t-rs", name="T", order_idx=1)
    agent = await make_agent(db, slug="a-rs", tab_id=tab.id, created_by_user_id=admin_user.id)
    av = await make_agent_version(
        db, agent_id=agent.id, created_by_user_id=admin_user.id, status="ready",
        manifest_jsonb={"runtime": {"llm": {"provider": "openrouter", "models": ["deepseek/deepseek-chat"]}}},
    )
    job = await make_job(db, agent_version_id=av.id, user_id=user.id)
    plain, _ = eph_svc.generate()
    await eph_svc.insert(
        db, plaintext=plain, job_id=job.id, user_id=user.id,
        agent_version_id=av.id, ttl=timedelta(minutes=65),
    )
    await db.flush()

    sse = (
        b'data: {"choices":[{"delta":{"content":"hi"}}]}\n\n'
        b'data: {"choices":[],"usage":{"prompt_tokens":3,"completion_tokens":1,"total_tokens":4}}\n\n'
        b'data: [DONE]\n\n'
    )

    with respx.mock(base_url="https://openrouter.ai/api/v1") as mock:
        mock.post("/chat/completions").mock(return_value=httpx.Response(
            200, content=sse,
            headers={"content-type": "text/event-stream"},
        ))
        async with client.stream(
            "POST", "/llm/v1/chat/completions",
            headers={"Authorization": f"Bearer {plain}"},
            json={"model": "deepseek/deepseek-chat", "messages": [{"role": "user", "content": "Hi"}], "stream": True},
        ) as r:
            assert r.status_code == 200
            body = b""
            async for chunk in r.aiter_bytes():
                body += chunk
    assert b"data: [DONE]" in body
