"""Кеш цен моделей OpenRouter с фоновым refresh.

Не персистится в БД — при рестарте загружается заново через первый запрос или
background-таск. При недоступности OpenRouter оставляет старый кеш и пишет warn.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from decimal import Decimal

import httpx
import structlog

logger = structlog.get_logger(__name__)

FALLBACK_PROMPT_PER_TOKEN = Decimal("0.00010")
FALLBACK_COMPLETION_PER_TOKEN = Decimal("0.00010")
FALLBACK_CONTEXT_LENGTH = 32_000


@dataclass(frozen=True)
class ModelPricing:
    """Цена модели в USD за один токен."""

    model: str
    prompt_per_token: Decimal
    completion_per_token: Decimal
    context_length: int


class PricingCache:
    """In-memory кеш модельных цен.

    Использование:
        cache = PricingCache(base_url=..., timeout_s=...)
        await cache.refresh()  # при старте или из background-таска
        p = await cache.get("deepseek/deepseek-chat")
    """

    def __init__(self, *, base_url: str, timeout_s: float = 30.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s
        self._data: dict[str, ModelPricing] = {}
        self._lock = asyncio.Lock()

    async def refresh(self) -> None:
        """Тянет /models из OpenRouter. При ошибке оставляет старый кеш."""
        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                resp = await client.get(f"{self._base_url}/models")
                resp.raise_for_status()
                payload = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("llm_pricing_refresh_failed", error=str(exc))
            return

        new_data: dict[str, ModelPricing] = {}
        for item in payload.get("data", []):
            try:
                model_id = item["id"]
                pricing = item["pricing"]
                new_data[model_id] = ModelPricing(
                    model=model_id,
                    prompt_per_token=Decimal(str(pricing["prompt"])),
                    completion_per_token=Decimal(str(pricing["completion"])),
                    context_length=int(item.get("context_length") or FALLBACK_CONTEXT_LENGTH),
                )
            except (KeyError, ValueError, TypeError) as exc:  # noqa: PERF203
                logger.warning("llm_pricing_skip_model", item=item, error=str(exc))

        async with self._lock:
            self._data = new_data
        logger.info("llm_pricing_refreshed", count=len(new_data))

    async def get(self, model: str) -> ModelPricing:
        """Возвращает pricing. Если модели нет — forced refresh, потом fallback."""
        if model in self._data:
            return self._data[model]

        await self.refresh()
        if model in self._data:
            return self._data[model]

        logger.warning("llm_pricing_fallback_used", model=model)
        return ModelPricing(
            model=model,
            prompt_per_token=FALLBACK_PROMPT_PER_TOKEN,
            completion_per_token=FALLBACK_COMPLETION_PER_TOKEN,
            context_length=FALLBACK_CONTEXT_LENGTH,
        )

    def models_in_cache(self) -> list[str]:
        """Список моделей в кеше (для GET /llm/v1/models метаданных)."""
        return list(self._data.keys())


async def periodic_refresh(cache: PricingCache, interval_s: int) -> None:
    """Background-таск: refresh каждые interval_s секунд."""
    while True:
        await asyncio.sleep(interval_s)
        await cache.refresh()
