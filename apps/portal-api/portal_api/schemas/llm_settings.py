"""Схемы admin LLM-настроек. Секреты только пишутся (PUT), на GET —
маскированный dict (см. llm_settings_service.get_masked)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class LlmSettingsUpdateIn(BaseModel):
    """Partial update. Отсутствие поля = не менять; пустая строка ИЛИ
    явный JSON null = очистить (для секретов/allowed_models → fallback на
    env). Какие реально пришли — определяется через model_fields_set."""

    model_config = ConfigDict(str_strip_whitespace=True)

    openrouter_api_key: str | None = None
    openai_api_key: str | None = None
    google_api_key: str | None = None
    xai_api_key: str | None = None
    anthropic_api_key: str | None = None
    deepseek_api_key: str | None = None
    provider_mode: str | None = None
    allowed_models: str | None = None
