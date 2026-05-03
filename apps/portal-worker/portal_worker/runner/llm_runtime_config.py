"""Конфигурация LLM-режима для запуска агентского контейнера."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LlmRuntimeConfig:
    """Передаётся в run_agent_container если manifest.runtime.llm присутствует.

    Атрибуты:
        ephemeral_token: plaintext OpenRouter-совместимый ephemeral-ключ; пробрасывается
            агенту через env OPENROUTER_API_KEY.
        agents_network_name: имя docker-сети (internal=true) куда подключить контейнер.
        proxy_base_url: значение OPENROUTER_BASE_URL для агента (URL прокси portal-api).
    """

    ephemeral_token: str
    agents_network_name: str
    proxy_base_url: str
