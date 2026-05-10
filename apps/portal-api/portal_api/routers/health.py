"""Health-check эндпоинты.

`GET /health` — лёгкий liveness probe (всегда 200, пока процесс жив).
`GET /health/full` — readiness probe: пингует Postgres и Redis,
показывает uptime/environment, отдаёт 503 если зависимость недоступна.
"""
# ruff: noqa: B008
from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.config import Settings, get_settings
from portal_api.deps import get_db

router = APIRouter(tags=["health"])

_STARTED_AT = time.monotonic()


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness — всегда 200, пока процесс жив."""
    return {"status": "ok"}


@router.get("/health/full")
async def health_full(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Readiness — пинг Postgres + Redis. 503 если что-то недоступно."""
    checks: dict[str, Any] = {}
    failed: list[str] = []

    try:
        await db.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as exc:
        checks["postgres"] = f"error: {type(exc).__name__}"
        failed.append("postgres")

    redis_client = AsyncRedis.from_url(str(settings.redis_url))
    try:
        pong = await redis_client.ping()
        checks["redis"] = "ok" if pong else "error: no PONG"
        if not pong:
            failed.append("redis")
    except Exception as exc:
        checks["redis"] = f"error: {type(exc).__name__}"
        failed.append("redis")
    finally:
        await redis_client.aclose()

    body: dict[str, Any] = {
        "status": "ok" if not failed else "degraded",
        "checks": checks,
        "uptime_seconds": round(time.monotonic() - _STARTED_AT, 1),
        "environment": settings.environment,
    }
    if failed:
        raise HTTPException(status_code=503, detail=body)
    return body
