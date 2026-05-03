"""llm_proxy non-streaming: forward + validate model + post-flight + error mapping."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import httpx
import pytest
import respx
import sqlalchemy as sa

from portal_api.core.exceptions import (
    ModelNotInWhitelistError, OpenRouterUpstreamError,
)
from portal_api.models import UsageLog, UserQuota
from portal_api.services import ephemeral_token as eph_svc
from portal_api.services import llm_proxy
from portal_api.services.ephemeral_token import EphemeralTokenContext
from portal_api.services.llm_pricing import ModelPricing, PricingCache
from tests.factories import (
    make_agent, make_agent_version, make_job, make_tab, make_user,
)


@pytest.fixture
async def llm_setup(db, admin_user):
    """User c quota + agent c manifest.runtime.llm.models = [deepseek/deepseek-chat]."""
    user = await make_user(db, email="px@x.x", password="testpasswordX1")
    db.add(UserQuota(
        user_id=user.id,
        monthly_limit_usd=Decimal("5.0000"),
        period_used_usd=Decimal("0"),
        period_starts_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        per_job_cap_usd=Decimal("0.5000"),
    ))
    tab = await make_tab(db, slug="t-px", name="T", order_idx=1)
    agent = await make_agent(db, slug="a-px", tab_id=tab.id, created_by_user_id=admin_user.id)
    av = await make_agent_version(
        db, agent_id=agent.id, created_by_user_id=admin_user.id, status="ready",
        manifest_jsonb={"runtime": {"llm": {"provider": "openrouter", "models": ["deepseek/deepseek-chat"]}}},
    )
    job = await make_job(db, agent_version_id=av.id, user_id=user.id)
    await db.commit()
    return user, agent, av, job


@pytest.fixture
def pricing_cache_with_deepseek() -> PricingCache:
    cache = PricingCache(base_url="https://openrouter.ai/api/v1", timeout_s=5.0)
    cache._data["deepseek/deepseek-chat"] = ModelPricing(  # noqa: SLF001
        model="deepseek/deepseek-chat",
        prompt_per_token=Decimal("0.00000014"),
        completion_per_token=Decimal("0.00000028"),
        context_length=64000,
    )
    return cache


@pytest.mark.asyncio
async def test_chat_completions_success_non_stream(
    db, llm_setup, pricing_cache_with_deepseek,
) -> None:
    user, agent, av, job = llm_setup
    ctx = EphemeralTokenContext(
        user_id=user.id, agent_id=agent.id,
        agent_version_id=av.id, job_id=job.id,
    )

    with respx.mock(base_url="https://openrouter.ai/api/v1") as mock:
        mock.post("/chat/completions").mock(return_value=httpx.Response(
            200,
            json={
                "id": "gen-1",
                "choices": [{"message": {"role": "assistant", "content": "hi"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            },
            headers={"x-request-id": "req-xyz"},
        ))

        result = await llm_proxy.chat_completions(
            db,
            ephemeral_ctx=ctx,
            request_body={"model": "deepseek/deepseek-chat", "messages": [{"role": "user", "content": "hi"}]},
            stream=False,
            pricing_cache=pricing_cache_with_deepseek,
            openrouter_api_key="sk-or-v1-real",
            openrouter_base_url="https://openrouter.ai/api/v1",
            request_timeout_s=10.0,
        )

    assert result["choices"][0]["message"]["content"] == "hi"

    log = (await db.execute(sa.select(UsageLog).where(UsageLog.job_id == job.id))).scalar_one()
    assert log.status == "success"
    assert log.prompt_tokens == 10
    assert log.completion_tokens == 5
    expected_cost = Decimal("10") * Decimal("0.00000014") + Decimal("5") * Decimal("0.00000028")
    # DB stores Numeric(10,6) — compare rounded to 6dp
    assert log.cost_usd == expected_cost.quantize(Decimal("0.000001"))

    q = await db.get(UserQuota, user.id)
    assert q.period_used_usd == expected_cost.quantize(Decimal("0.0001"))


@pytest.mark.asyncio
async def test_chat_completions_model_not_in_whitelist(
    db, llm_setup, pricing_cache_with_deepseek,
) -> None:
    user, agent, av, job = llm_setup
    ctx = EphemeralTokenContext(
        user_id=user.id, agent_id=agent.id,
        agent_version_id=av.id, job_id=job.id,
    )

    with pytest.raises(ModelNotInWhitelistError):
        await llm_proxy.chat_completions(
            db, ephemeral_ctx=ctx,
            request_body={"model": "anthropic/claude-opus-99", "messages": []},
            stream=False,
            pricing_cache=pricing_cache_with_deepseek,
            openrouter_api_key="sk-or-v1-real",
            openrouter_base_url="https://openrouter.ai/api/v1",
            request_timeout_s=10.0,
        )

    log = (await db.execute(sa.select(UsageLog).where(UsageLog.job_id == job.id))).scalar_one()
    assert log.status == "model_not_in_whitelist"
    assert log.cost_usd == Decimal("0")


@pytest.mark.asyncio
async def test_chat_completions_openrouter_5xx(
    db, llm_setup, pricing_cache_with_deepseek,
) -> None:
    user, agent, av, job = llm_setup
    ctx = EphemeralTokenContext(
        user_id=user.id, agent_id=agent.id,
        agent_version_id=av.id, job_id=job.id,
    )

    with respx.mock(base_url="https://openrouter.ai/api/v1") as mock:
        mock.post("/chat/completions").mock(return_value=httpx.Response(503, json={"error": "down"}))
        with pytest.raises(OpenRouterUpstreamError):
            await llm_proxy.chat_completions(
                db, ephemeral_ctx=ctx,
                request_body={"model": "deepseek/deepseek-chat", "messages": [{"role": "user", "content": "x"}]},
                stream=False,
                pricing_cache=pricing_cache_with_deepseek,
                openrouter_api_key="sk-or-v1-real",
                openrouter_base_url="https://openrouter.ai/api/v1",
                request_timeout_s=10.0,
            )

    log = (await db.execute(sa.select(UsageLog).where(UsageLog.job_id == job.id))).scalar_one()
    assert log.status == "openrouter_upstream_error"
