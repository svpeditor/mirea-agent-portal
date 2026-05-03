"""LLM-прокси: forward к OpenRouter с pre/post-flight квотами и логированием.

Non-streaming chat_completions: проверка модели → preflight → forward → postflight.
Streaming реализован отдельно в chat_completions_stream (см. Task 9).
"""
from __future__ import annotations

import json
import time
import uuid
from decimal import Decimal
from typing import Any

import httpx
import sqlalchemy as sa
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.core.exceptions import (
    AppError, ModelNotInWhitelistError, OpenRouterTimeoutError,
    OpenRouterUpstreamError,
)
from portal_api.models import AgentVersion, UsageLog
from portal_api.services import llm_quota
from portal_api.services.ephemeral_token import EphemeralTokenContext
from portal_api.services.llm_pricing import ModelPricing, PricingCache

logger = structlog.get_logger(__name__)


def _estimate_prompt_tokens(messages: list[dict[str, Any]]) -> int:
    """Грубая оценка: 1 токен ≈ 3 символа JSON."""
    return max(1, len(json.dumps(messages, ensure_ascii=False)) // 3)


def _estimate_completion_tokens(request_body: dict[str, Any], pricing: ModelPricing) -> int:
    return int(request_body.get("max_tokens") or pricing.context_length)


def _calc_cost(pricing: ModelPricing, prompt_tokens: int, completion_tokens: int) -> Decimal:
    return (
        Decimal(prompt_tokens) * pricing.prompt_per_token
        + Decimal(completion_tokens) * pricing.completion_per_token
    )


async def _validate_model_in_whitelist(
    db: AsyncSession, *, agent_version_id: uuid.UUID, model: str,
) -> list[str]:
    """Возвращает список разрешённых моделей agent_version. Бросает если не в whitelist'е."""
    av = (await db.execute(
        sa.select(AgentVersion).where(AgentVersion.id == agent_version_id)
    )).scalar_one()
    allowed = (
        ((av.manifest_jsonb or {}).get("runtime") or {}).get("llm") or {}
    ).get("models", [])
    if not allowed:
        raise ModelNotInWhitelistError("agent has no LLM models declared")
    if model not in allowed:
        raise ModelNotInWhitelistError(
            f"model {model!r} not in agent whitelist {allowed}"
        )
    return allowed


async def _write_usage_log(
    db: AsyncSession,
    *,
    ctx: EphemeralTokenContext,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    cost_usd: Decimal,
    latency_ms: int,
    status: str,
    openrouter_request_id: str | None,
) -> None:
    log = UsageLog(
        job_id=ctx.job_id,
        user_id=ctx.user_id,
        agent_id=ctx.agent_id,
        agent_version_id=ctx.agent_version_id,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
        status=status,
        openrouter_request_id=openrouter_request_id,
    )
    db.add(log)
    await db.flush()


async def chat_completions(
    db: AsyncSession,
    *,
    ephemeral_ctx: EphemeralTokenContext,
    request_body: dict[str, Any],
    stream: bool,
    pricing_cache: PricingCache,
    openrouter_api_key: str,
    openrouter_base_url: str,
    request_timeout_s: float,
) -> dict[str, Any]:
    """Non-streaming chat completion. Streaming → chat_completions_stream (Task 9)."""
    if stream:
        raise RuntimeError("use chat_completions_stream for stream=True")

    model = request_body.get("model")
    if not model:
        raise ModelNotInWhitelistError("request body has no 'model' field")

    try:
        await _validate_model_in_whitelist(
            db, agent_version_id=ephemeral_ctx.agent_version_id, model=model,
        )
    except ModelNotInWhitelistError:
        await _write_usage_log(
            db, ctx=ephemeral_ctx, model=model, prompt_tokens=0,
            completion_tokens=0, cost_usd=Decimal("0"), latency_ms=0,
            status="model_not_in_whitelist", openrouter_request_id=None,
        )
        await db.commit()
        raise

    pricing = await pricing_cache.get(model)

    estimated_prompt = _estimate_prompt_tokens(request_body.get("messages", []))
    estimated_completion = _estimate_completion_tokens(request_body, pricing)
    estimated_cost = _calc_cost(pricing, estimated_prompt, estimated_completion)

    try:
        await llm_quota.preflight(
            db, user_id=ephemeral_ctx.user_id, job_id=ephemeral_ctx.job_id,
            estimated_cost=estimated_cost,
        )
        await db.commit()
    except AppError as exc:
        await _write_usage_log(
            db, ctx=ephemeral_ctx, model=model, prompt_tokens=0,
            completion_tokens=0, cost_usd=Decimal("0"), latency_ms=0,
            status=exc.code, openrouter_request_id=None,
        )
        await db.commit()
        raise

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=request_timeout_s) as client:
            resp = await client.post(
                f"{openrouter_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {openrouter_api_key}"},
                json=request_body,
            )
    except httpx.TimeoutException:
        latency = int((time.monotonic() - start) * 1000)
        await _write_usage_log(
            db, ctx=ephemeral_ctx, model=model, prompt_tokens=0,
            completion_tokens=0, cost_usd=Decimal("0"), latency_ms=latency,
            status="openrouter_timeout", openrouter_request_id=None,
        )
        await db.commit()
        raise OpenRouterTimeoutError(f"OpenRouter timeout after {request_timeout_s}s")

    latency_ms = int((time.monotonic() - start) * 1000)
    upstream_request_id = resp.headers.get("x-request-id")

    if resp.status_code >= 500:
        await _write_usage_log(
            db, ctx=ephemeral_ctx, model=model, prompt_tokens=0,
            completion_tokens=0, cost_usd=Decimal("0"), latency_ms=latency_ms,
            status="openrouter_upstream_error", openrouter_request_id=upstream_request_id,
        )
        await db.commit()
        raise OpenRouterUpstreamError(
            f"OpenRouter returned {resp.status_code}: {resp.text[:200]}"
        )

    if resp.status_code >= 400:
        await _write_usage_log(
            db, ctx=ephemeral_ctx, model=model, prompt_tokens=0,
            completion_tokens=0, cost_usd=Decimal("0"), latency_ms=latency_ms,
            status=f"openrouter_{resp.status_code}", openrouter_request_id=upstream_request_id,
        )
        await db.commit()
        return {"_proxied_status": resp.status_code, "_body": resp.json()}

    response_data = resp.json()
    usage = response_data.get("usage", {})
    prompt_tokens = int(usage.get("prompt_tokens", 0))
    completion_tokens = int(usage.get("completion_tokens", 0))
    real_cost = _calc_cost(pricing, prompt_tokens, completion_tokens)

    await _write_usage_log(
        db, ctx=ephemeral_ctx, model=model,
        prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
        cost_usd=real_cost, latency_ms=latency_ms,
        status="success", openrouter_request_id=upstream_request_id,
    )
    await llm_quota.postflight(
        db, user_id=ephemeral_ctx.user_id, job_id=ephemeral_ctx.job_id,
        real_cost=real_cost,
    )
    await db.commit()

    return response_data


async def chat_completions_stream(
    db: AsyncSession,
    *,
    ephemeral_ctx: EphemeralTokenContext,
    request_body: dict[str, Any],
    pricing_cache: PricingCache,
    openrouter_api_key: str,
    openrouter_base_url: str,
    request_timeout_s: float,
):
    """Async generator: streams SSE chunks к клиенту, парсит usage в последнем chunk."""
    model = request_body.get("model")
    if not model:
        raise ModelNotInWhitelistError("request body has no 'model' field")

    try:
        await _validate_model_in_whitelist(
            db, agent_version_id=ephemeral_ctx.agent_version_id, model=model,
        )
    except ModelNotInWhitelistError:
        await _write_usage_log(
            db, ctx=ephemeral_ctx, model=model, prompt_tokens=0,
            completion_tokens=0, cost_usd=Decimal("0"), latency_ms=0,
            status="model_not_in_whitelist", openrouter_request_id=None,
        )
        await db.commit()
        raise

    pricing = await pricing_cache.get(model)

    estimated_prompt = _estimate_prompt_tokens(request_body.get("messages", []))
    estimated_completion = _estimate_completion_tokens(request_body, pricing)
    estimated_cost = _calc_cost(pricing, estimated_prompt, estimated_completion)

    try:
        await llm_quota.preflight(
            db, user_id=ephemeral_ctx.user_id, job_id=ephemeral_ctx.job_id,
            estimated_cost=estimated_cost,
        )
        await db.commit()
    except AppError as exc:
        await _write_usage_log(
            db, ctx=ephemeral_ctx, model=model, prompt_tokens=0,
            completion_tokens=0, cost_usd=Decimal("0"), latency_ms=0,
            status=exc.code, openrouter_request_id=None,
        )
        await db.commit()
        raise

    forwarded_body = dict(request_body)
    forwarded_body["stream"] = True
    stream_options = dict(forwarded_body.get("stream_options") or {})
    stream_options["include_usage"] = True
    forwarded_body["stream_options"] = stream_options

    start = time.monotonic()
    upstream_request_id: str | None = None
    parsed_usage: dict[str, int] | None = None
    streamed_content_size = 0
    error_status: str | None = None

    try:
        async with httpx.AsyncClient(timeout=request_timeout_s) as client:
            async with client.stream(
                "POST", f"{openrouter_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {openrouter_api_key}"},
                json=forwarded_body,
            ) as resp:
                upstream_request_id = resp.headers.get("x-request-id")
                if resp.status_code >= 500:
                    error_status = "openrouter_upstream_error"
                elif resp.status_code >= 400:
                    error_status = f"openrouter_{resp.status_code}"

                async for raw_chunk in resp.aiter_bytes():
                    streamed_content_size += len(raw_chunk)
                    yield raw_chunk
                    if parsed_usage is None:
                        for line in raw_chunk.split(b"\n"):
                            if not line.startswith(b"data: ") or line == b"data: [DONE]":
                                continue
                            payload = line[6:].strip()
                            if not payload:
                                continue
                            try:
                                obj = json.loads(payload)
                            except json.JSONDecodeError:
                                continue
                            if "usage" in obj and obj["usage"]:
                                parsed_usage = obj["usage"]
                                break
    except httpx.TimeoutException:
        error_status = "openrouter_timeout"

    latency_ms = int((time.monotonic() - start) * 1000)

    if error_status:
        await _write_usage_log(
            db, ctx=ephemeral_ctx, model=model, prompt_tokens=0,
            completion_tokens=0, cost_usd=Decimal("0"), latency_ms=latency_ms,
            status=error_status, openrouter_request_id=upstream_request_id,
        )
        await db.commit()
        if error_status == "openrouter_timeout":
            raise OpenRouterTimeoutError(f"OpenRouter timeout after {request_timeout_s}s")
        if error_status == "openrouter_upstream_error":
            raise OpenRouterUpstreamError("OpenRouter 5xx during streaming")
        return

    if parsed_usage:
        prompt_tokens = int(parsed_usage.get("prompt_tokens", 0))
        completion_tokens = int(parsed_usage.get("completion_tokens", 0))
    else:
        logger.warning(
            "llm_stream_no_usage_chunk", job_id=str(ephemeral_ctx.job_id),
            streamed_size=streamed_content_size,
        )
        prompt_tokens = estimated_prompt
        completion_tokens = max(1, streamed_content_size // 3)

    real_cost = _calc_cost(pricing, prompt_tokens, completion_tokens)
    await _write_usage_log(
        db, ctx=ephemeral_ctx, model=model,
        prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
        cost_usd=real_cost, latency_ms=latency_ms,
        status="success", openrouter_request_id=upstream_request_id,
    )
    await llm_quota.postflight(
        db, user_id=ephemeral_ctx.user_id, job_id=ephemeral_ctx.job_id,
        real_cost=real_cost,
    )
    await db.commit()
