"""Роутер /llm/v1/* — OpenAI-совместимый прокси."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.config import Settings, get_settings
from portal_api.core.exceptions import NotImplementedAppError
from portal_api.core.llm_auth import ephemeral_token_auth
from portal_api.db import get_db
from portal_api.services import llm_proxy as svc
from portal_api.services.ephemeral_token import EphemeralTokenContext
from portal_api.services.llm_pricing import PricingCache

router = APIRouter(prefix="/llm/v1", tags=["llm-proxy"])


def get_pricing_cache(request: Request) -> PricingCache:
    return request.app.state.pricing_cache


@router.post("/chat/completions")
async def chat_completions(
    payload: dict[str, Any],
    ctx: EphemeralTokenContext = Depends(ephemeral_token_auth),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    pricing_cache: PricingCache = Depends(get_pricing_cache),
) -> Any:
    stream = bool(payload.get("stream", False))
    if stream:
        async def _gen():
            async for chunk in svc.chat_completions_stream(
                db, ephemeral_ctx=ctx, request_body=payload,
                pricing_cache=pricing_cache,
                openrouter_api_key=settings.openrouter_api_key.get_secret_value(),
                openrouter_base_url=settings.openrouter_base_url,
                request_timeout_s=settings.llm_request_timeout_seconds,
            ):
                yield chunk
        return StreamingResponse(_gen(), media_type="text/event-stream")

    result = await svc.chat_completions(
        db, ephemeral_ctx=ctx, request_body=payload, stream=False,
        pricing_cache=pricing_cache,
        openrouter_api_key=settings.openrouter_api_key.get_secret_value(),
        openrouter_base_url=settings.openrouter_base_url,
        request_timeout_s=settings.llm_request_timeout_seconds,
    )
    if isinstance(result, dict) and "_proxied_status" in result:
        raise HTTPException(status_code=result["_proxied_status"], detail=result["_body"])
    return result


@router.post("/completions")
async def completions(
    payload: dict[str, Any],
    ctx: EphemeralTokenContext = Depends(ephemeral_token_auth),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    pricing_cache: PricingCache = Depends(get_pricing_cache),
) -> Any:
    """Legacy completions API."""
    return await chat_completions(
        payload=payload, ctx=ctx, db=db, settings=settings, pricing_cache=pricing_cache,
    )


@router.get("/models")
async def list_models(
    ctx: EphemeralTokenContext = Depends(ephemeral_token_auth),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Возвращает manifest.runtime.llm.models текущего агента в OpenAI-формате."""
    import sqlalchemy as sa
    from portal_api.models import AgentVersion
    av = (await db.execute(
        sa.select(AgentVersion).where(AgentVersion.id == ctx.agent_version_id)
    )).scalar_one()
    models = (
        ((av.manifest_jsonb or {}).get("runtime") or {}).get("llm") or {}
    ).get("models", [])
    return {
        "object": "list",
        "data": [{"id": m, "object": "model", "owned_by": "openrouter"} for m in models],
    }


# Не поддерживаемые эндпоинты — 501.
# ВАЖНО: каждый endpoint должен иметь свою функцию (closures over loop variable
# break this pattern). Регистрируем явно.

async def _not_implemented(
    ctx: EphemeralTokenContext = Depends(ephemeral_token_auth),
) -> None:
    raise NotImplementedAppError(
        "endpoint not supported by portal LLM proxy on MVP",
    )


for _method, _path in [
    ("POST", "/embeddings"),
    ("POST", "/images/generations"),
    ("POST", "/audio/transcriptions"),
    ("POST", "/audio/translations"),
    ("POST", "/audio/speech"),
    ("GET", "/files"),
    ("POST", "/files"),
    ("POST", "/fine_tuning/jobs"),
    ("POST", "/moderations"),
]:
    router.add_api_route(_path, _not_implemented, methods=[_method])
