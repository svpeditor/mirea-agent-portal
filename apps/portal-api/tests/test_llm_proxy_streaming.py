"""llm_proxy streaming: SSE pass-through + usage chunk parsing."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import httpx
import pytest
import respx
import sqlalchemy as sa

from portal_api.models import UsageLog, UserQuota
from portal_api.services import llm_proxy
from portal_api.services.ephemeral_token import EphemeralTokenContext
from portal_api.services.llm_pricing import ModelPricing, PricingCache
from tests.factories import (
    make_agent, make_agent_version, make_job, make_tab, make_user,
)


SSE_STREAM_BODY = (
    b'data: {"choices":[{"delta":{"content":"Hel"}}]}\n\n'
    b'data: {"choices":[{"delta":{"content":"lo"}}]}\n\n'
    b'data: {"choices":[],"usage":{"prompt_tokens":7,"completion_tokens":2,"total_tokens":9}}\n\n'
    b'data: [DONE]\n\n'
)


@pytest.fixture
async def setup(db, admin_user):
    user = await make_user(db, email="st@x.x", password="testpasswordX1")
    db.add(UserQuota(
        user_id=user.id,
        monthly_limit_usd=Decimal("5"),
        period_used_usd=Decimal("0"),
        period_starts_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        per_job_cap_usd=Decimal("0.5"),
    ))
    tab = await make_tab(db, slug="t-st", name="T", order_idx=1)
    agent = await make_agent(db, slug="a-st", tab_id=tab.id, created_by_user_id=admin_user.id)
    av = await make_agent_version(
        db, agent_id=agent.id, created_by_user_id=admin_user.id, status="ready",
        manifest_jsonb={"runtime": {"llm": {"provider": "openrouter", "models": ["deepseek/deepseek-chat"]}}},
    )
    job = await make_job(db, agent_version_id=av.id, user_id=user.id)
    await db.commit()
    return EphemeralTokenContext(
        user_id=user.id, agent_id=agent.id, agent_version_id=av.id, job_id=job.id,
    ), user, agent, av, job


@pytest.fixture
def pricing() -> PricingCache:
    cache = PricingCache(base_url="https://openrouter.ai/api/v1", timeout_s=5.0)
    cache._data["deepseek/deepseek-chat"] = ModelPricing(  # noqa: SLF001
        model="deepseek/deepseek-chat",
        prompt_per_token=Decimal("0.00000014"),
        completion_per_token=Decimal("0.00000028"),
        context_length=64000,
    )
    return cache


@pytest.mark.asyncio
async def test_streaming_passes_through_and_logs_usage(db, setup, pricing) -> None:
    ctx, user, _, _, job = setup

    with respx.mock(base_url="https://openrouter.ai/api/v1") as mock:
        mock.post("/chat/completions").mock(return_value=httpx.Response(
            200, content=SSE_STREAM_BODY,
            headers={"content-type": "text/event-stream", "x-request-id": "req-st"},
        ))

        chunks = []
        async for chunk in llm_proxy.chat_completions_stream(
            db,
            ephemeral_ctx=ctx,
            request_body={"model": "deepseek/deepseek-chat", "messages": [{"role": "user", "content": "Hi"}]},
            pricing_cache=pricing,
            openrouter_api_key="sk-or-v1-real",
            openrouter_base_url="https://openrouter.ai/api/v1",
            request_timeout_s=10.0,
        ):
            chunks.append(chunk)

    body = b"".join(chunks)
    assert b"data: [DONE]" in body
    assert b'"content":"Hel"' in body

    log = (await db.execute(sa.select(UsageLog).where(UsageLog.job_id == job.id))).scalar_one()
    assert log.status == "success"
    assert log.prompt_tokens == 7
    assert log.completion_tokens == 2

    q = await db.get(UserQuota, user.id)
    expected = (Decimal("7") * Decimal("0.00000014") + Decimal("2") * Decimal("0.00000028")).quantize(Decimal("0.0001"))
    assert q.period_used_usd == expected


@pytest.mark.asyncio
async def test_streaming_inject_include_usage(db, setup, pricing) -> None:
    """Прокси должен override stream_options.include_usage даже если клиент не передал."""
    ctx, _, _, _, _ = setup
    forwarded_body: dict = {}

    with respx.mock(base_url="https://openrouter.ai/api/v1") as mock:
        def _capture(request: httpx.Request) -> httpx.Response:
            import json as _json
            forwarded_body.update(_json.loads(request.content))
            return httpx.Response(200, content=SSE_STREAM_BODY)

        mock.post("/chat/completions").mock(side_effect=_capture)

        async for _ in llm_proxy.chat_completions_stream(
            db, ephemeral_ctx=ctx,
            request_body={"model": "deepseek/deepseek-chat", "messages": [{"role": "user", "content": "x"}], "stream": True},
            pricing_cache=pricing,
            openrouter_api_key="sk-or-v1-real",
            openrouter_base_url="https://openrouter.ai/api/v1",
            request_timeout_s=10.0,
        ):
            pass

    assert forwarded_body.get("stream") is True
    assert forwarded_body.get("stream_options", {}).get("include_usage") is True
