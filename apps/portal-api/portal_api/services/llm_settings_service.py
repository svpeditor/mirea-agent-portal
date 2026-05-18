"""Резолв эффективных LLM-настроек: значение из БД (если задано админом)
иначе fallback на env (`Settings`). Секреты НИКОГДА не отдаём клиенту
целиком — только `mask()`. В логи значения не пишем.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.config import Settings
from portal_api.models import LlmSettings

# Секретные поля, которые маскируются на GET и принимаются на PUT.
SECRET_FIELDS = (
    "openrouter_api_key",
    "openai_api_key",
    "google_api_key",
    "xai_api_key",
    "anthropic_api_key",
    "deepseek_api_key",
)


@dataclass
class ResolvedLlm:
    openrouter_api_key: str
    openrouter_base_url: str
    allowed_models: list[str]
    provider_mode: str
    # per-provider ключи (Фаза 3); пустая строка = не задан
    provider_keys: dict[str, str]


def _mask(value: str | None) -> dict:
    if not value:
        return {"set": False, "preview": ""}
    v = value.strip()
    preview = f"{v[:4]}…{v[-4:]}" if len(v) > 20 else "••••"
    return {"set": True, "preview": preview}


async def _row(db: AsyncSession) -> LlmSettings | None:
    return (
        await db.execute(sa.select(LlmSettings).where(LlmSettings.id == 1))
    ).scalar_one_or_none()


async def get_effective(db: AsyncSession, settings: Settings) -> ResolvedLlm:
    """БД переопределяет env. Пустые/NULL поля БД = брать env."""
    row = await _row(db)
    db_or = (row.openrouter_api_key or "").strip() if row else ""
    db_models = (row.allowed_models or "").strip() if row else ""
    models = (
        [m.strip() for m in db_models.split(",") if m.strip()]
        if db_models
        else list(settings.llm_allowed_models)
    )
    pkeys = {}
    if row:
        for f in ("openai", "google", "xai", "anthropic", "deepseek"):
            pkeys[f] = (getattr(row, f"{f}_api_key") or "").strip()
    return ResolvedLlm(
        openrouter_api_key=db_or or settings.openrouter_api_key.get_secret_value(),
        openrouter_base_url=settings.openrouter_base_url,
        allowed_models=models,
        provider_mode=(row.provider_mode if row else "openrouter") or "openrouter",
        provider_keys=pkeys,
    )


async def get_masked(db: AsyncSession, settings: Settings) -> dict:
    """Для admin GET. Секреты — только статус+preview, НИКОГДА не целиком.
    Для openrouter показываем что задано: БД либо env-fallback."""
    row = await _row(db)
    out: dict = {
        "provider_mode": (row.provider_mode if row else "openrouter") or "openrouter",
        "allowed_models": (row.allowed_models if row and row.allowed_models else
                           ",".join(settings.llm_allowed_models)),
        "allowed_models_source": "db" if (row and row.allowed_models) else "env",
    }
    db_or = (row.openrouter_api_key or "").strip() if row else ""
    if db_or:
        out["openrouter_api_key"] = {**_mask(db_or), "source": "db"}
    else:
        env_or = settings.openrouter_api_key.get_secret_value()
        out["openrouter_api_key"] = {**_mask(env_or), "source": "env"}
    for f in ("openai", "google", "xai", "anthropic", "deepseek"):
        out[f"{f}_api_key"] = _mask(
            getattr(row, f"{f}_api_key") if row else None
        )
    return out


async def update(
    db: AsyncSession,
    *,
    actor_user_id: uuid.UUID,
    patch: dict,
) -> list[str]:
    """Применяет только присутствующие в patch поля. Пустая строка = очистить,
    отсутствие ключа = не менять. Возвращает список изменённых полей (БЕЗ
    значений — для аудита)."""
    row = await _row(db)
    if row is None:  # singleton мог не засидиться (старый дамп) — создаём
        row = LlmSettings(id=1)
        db.add(row)
    changed: list[str] = []
    # nullable-поля: пустая строка => None (очистить), отсутствие => не менять
    for field in (*SECRET_FIELDS, "allowed_models"):
        if field not in patch:
            continue
        val = patch[field]
        new = (val.strip() if isinstance(val, str) else val) or None
        if getattr(row, field) != new:
            setattr(row, field, new)
            changed.append(field)
    # provider_mode: NOT NULL, только 'openrouter'|'direct'
    if "provider_mode" in patch:
        pm = str(patch["provider_mode"] or "").strip()
        pm = pm if pm in ("openrouter", "direct") else "openrouter"
        if row.provider_mode != pm:
            row.provider_mode = pm
            changed.append("provider_mode")
    row.updated_by_user_id = actor_user_id
    await db.flush()
    return changed
