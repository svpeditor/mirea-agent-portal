"""Резолвер upstream-цели для LLM-прокси.

provider_mode = глобальная настройка портала (llm_settings). Агенты ВСЕГДА
шлют OpenRouter-слаги (`openai/gpt-4o`, `google/gemini-2.5-flash`, ...);
портал прозрачно решает, идти ли через OpenRouter или напрямую к
провайдеру.

direct поддержан для OpenAI-совместимых провайдеров (OpenAI, xAI/Grok,
Google через OpenAI-endpoint) — там меняются base_url+key, а тело/usage
остаются OpenAI-схемой (квоты/pricing считаются как раньше).

Anthropic (нативная схема /v1/messages) и DeepSeek (несовпадение id
слага и нативного имени модели) в direct-режиме всё равно идут через
OpenRouter — документированное ограничение, чтобы не плодить хрупкие
адаптеры. Если ключ провайдера не задан — graceful fallback на
OpenRouter (никогда не ломаем рабочего агента).
"""
from __future__ import annotations

from dataclasses import dataclass

from portal_api.services.llm_settings_service import ResolvedLlm

# prefix -> (provider_key_name, openai-compatible base_url)
_DIRECT_PROVIDERS: dict[str, tuple[str, str]] = {
    "openai/": ("openai", "https://api.openai.com/v1"),
    "x-ai/": ("xai", "https://api.x.ai/v1"),
    "google/": ("google", "https://generativelanguage.googleapis.com/v1beta/openai"),
}


@dataclass
class UpstreamTarget:
    base_url: str
    api_key: str
    # если задано — заменить request_body["model"] на это перед upstream-вызовом
    # (direct-провайдеры ждут `gpt-4o`, а не `openai/gpt-4o`)
    upstream_model: str | None
    route: str  # 'openrouter' | 'direct:openai' | ...


def resolve(model: str, resolved: ResolvedLlm) -> UpstreamTarget:
    def _openrouter() -> UpstreamTarget:
        return UpstreamTarget(
            base_url=resolved.openrouter_base_url,
            api_key=resolved.openrouter_api_key,
            upstream_model=None,
            route="openrouter",
        )

    if resolved.provider_mode != "direct" or not model:
        return _openrouter()

    for prefix, (prov, base) in _DIRECT_PROVIDERS.items():
        if model.startswith(prefix):
            key = (resolved.provider_keys.get(prov) or "").strip()
            if key:
                return UpstreamTarget(
                    base_url=base,
                    api_key=key,
                    upstream_model=model[len(prefix):],
                    route=f"direct:{prov}",
                )
            # ключ не задан — не ломаем агента, идём через OpenRouter
            return _openrouter()

    # anthropic/* , deepseek/* , неизвестные — всегда OpenRouter
    return _openrouter()
