"""PricingCache: refresh, miss → forced refresh, fallback при недоступности."""
from __future__ import annotations

from decimal import Decimal

import httpx
import pytest
import respx

from portal_api.services.llm_pricing import (
    FALLBACK_COMPLETION_PER_TOKEN,
    FALLBACK_PROMPT_PER_TOKEN,
    ModelPricing,
    PricingCache,
)


@pytest.fixture
def cache() -> PricingCache:
    return PricingCache(base_url="https://openrouter.ai/api/v1", timeout_s=5.0)


@pytest.mark.asyncio
async def test_refresh_populates_cache(cache: PricingCache) -> None:
    with respx.mock(base_url="https://openrouter.ai/api/v1") as mock:
        mock.get("/models").mock(
            return_value=httpx.Response(
                200,
                json={"data": [
                    {
                        "id": "deepseek/deepseek-chat",
                        "context_length": 64000,
                        "pricing": {"prompt": "0.00000014", "completion": "0.00000028"},
                    },
                    {
                        "id": "anthropic/claude-haiku-4-5",
                        "context_length": 200000,
                        "pricing": {"prompt": "0.000001", "completion": "0.000005"},
                    },
                ]},
            )
        )
        await cache.refresh()

    p = await cache.get("deepseek/deepseek-chat")
    assert p.prompt_per_token == Decimal("0.00000014")
    assert p.completion_per_token == Decimal("0.00000028")
    assert p.context_length == 64000


@pytest.mark.asyncio
async def test_get_miss_triggers_forced_refresh(cache: PricingCache) -> None:
    refresh_count = 0

    with respx.mock(base_url="https://openrouter.ai/api/v1") as mock:
        def _handler(request: httpx.Request) -> httpx.Response:
            nonlocal refresh_count
            refresh_count += 1
            return httpx.Response(200, json={"data": [
                {"id": "x/y", "context_length": 100, "pricing": {"prompt": "0", "completion": "0"}},
            ]})

        mock.get("/models").mock(side_effect=_handler)

        # Cache пуст
        p = await cache.get("x/y")
        assert refresh_count == 1
        assert p.prompt_per_token == Decimal("0")


@pytest.mark.asyncio
async def test_get_miss_after_forced_refresh_fallback(cache: PricingCache) -> None:
    """Если модели нет даже после refresh — worst-case fallback."""
    with respx.mock(base_url="https://openrouter.ai/api/v1") as mock:
        mock.get("/models").mock(
            return_value=httpx.Response(200, json={"data": []})
        )
        p = await cache.get("unknown/model-xyz")
        assert p.prompt_per_token == FALLBACK_PROMPT_PER_TOKEN
        assert p.completion_per_token == FALLBACK_COMPLETION_PER_TOKEN
        assert p.context_length > 0


@pytest.mark.asyncio
async def test_refresh_failure_keeps_old_cache(cache: PricingCache) -> None:
    # Первый успешный refresh
    with respx.mock(base_url="https://openrouter.ai/api/v1") as mock:
        mock.get("/models").mock(
            return_value=httpx.Response(200, json={"data": [
                {"id": "a/b", "context_length": 100, "pricing": {"prompt": "0.001", "completion": "0.002"}},
            ]})
        )
        await cache.refresh()

    # Второй refresh — ошибка
    with respx.mock(base_url="https://openrouter.ai/api/v1") as mock:
        mock.get("/models").mock(return_value=httpx.Response(503, json={"error": "down"}))
        await cache.refresh()  # не должен бросить

    # Старые цены остались
    p = await cache.get("a/b")
    assert p.prompt_per_token == Decimal("0.001")
