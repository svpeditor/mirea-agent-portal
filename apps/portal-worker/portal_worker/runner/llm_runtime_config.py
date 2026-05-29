"""Конфигурация sandbox-доступа агента к portal-api (LLM-прокси + общая БД)."""
# ruff: noqa: RUF002
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LlmRuntimeConfig:
    """Передаётся в run_agent_container, когда у джоба есть ephemeral-токен.

    Токен выдаётся, если агент объявил runtime.llm и/или runtime.datasets.

    Атрибуты:
        ephemeral_token: plaintext ephemeral-ключ; агенту через env
            OPENROUTER_API_KEY (LLM) и PORTAL_AGENT_TOKEN (sandbox-api).
        agents_network_name: имя docker-сети (internal=true) куда подключить контейнер.
        proxy_base_url: значение OPENROUTER_BASE_URL для агента (URL LLM-прокси).
        api_base_url: корень portal-api для sandbox-эндпоинтов
            (env PORTAL_API_BASE_URL), например http://api:8000.
        llm_enabled: объявил ли агент runtime.llm. Если нет (агент только с
            runtime.datasets) — НЕ выдаём ему OPENROUTER_*-кредл (минимизируем
            доступ); sandbox-токен (PORTAL_AGENT_TOKEN) выдаём всегда.
    """

    ephemeral_token: str
    agents_network_name: str
    proxy_base_url: str
    api_base_url: str
    llm_enabled: bool = True
