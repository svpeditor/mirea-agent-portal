# ruff: noqa: B008
"""WebSocket: real-time stream events для job."""
from __future__ import annotations

import asyncio
import json
import uuid

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.config import Settings, get_settings
from portal_api.core.ws_auth import get_current_user_ws
from portal_api.deps import get_db
from portal_api.services import job_event_service, job_service

router = APIRouter()


@router.websocket("/jobs/{job_id}/stream")
async def stream_job(
    websocket: WebSocket,
    job_id: uuid.UUID,
    since: int = 0,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> None:
    user = await get_current_user_ws(websocket, db)
    job = await job_service.get_job_for_user(db, job_id, user)
    if job is None:
        await websocket.close(code=4404, reason="job_not_found")
        return

    await websocket.accept()

    # 1. Resync -- отдать все события c seq > since
    events = await job_event_service.list_since(db, job_id, since=since, limit=1000)
    await websocket.send_json({"type": "resync", "events": events})

    # 2. Если job уже в финальном статусе -- закрыть
    if job.status in ("result", "failed", "cancelled"):
        await websocket.close(code=1000)
        return

    # 3. Subscribe to Redis pub/sub + heartbeat
    redis = aioredis.from_url(str(settings.redis_url))  # type: ignore[no-untyped-call]
    pubsub = redis.pubsub()
    await pubsub.subscribe(f"job:{job_id}")
    stop_event = asyncio.Event()

    async def reader() -> None:
        try:
            async for msg in pubsub.listen():
                if stop_event.is_set():
                    return
                if msg["type"] != "message":
                    continue
                data = msg["data"]
                if isinstance(data, bytes):
                    data = data.decode()
                await websocket.send_text(data)
                try:
                    parsed = json.loads(data)
                    et = parsed.get("event", {}).get("type")
                    if et in ("result", "failed"):
                        await websocket.close(code=1000)
                        stop_event.set()
                        return
                except (json.JSONDecodeError, AttributeError):
                    pass
        except Exception:
            stop_event.set()

    async def heartbeat() -> None:
        try:
            while not stop_event.is_set():
                await asyncio.sleep(30)
                if stop_event.is_set():
                    return
                await websocket.send_json({"type": "ping"})
        except Exception:
            stop_event.set()

    try:
        await asyncio.gather(reader(), heartbeat())
    except WebSocketDisconnect:
        stop_event.set()
    finally:
        await pubsub.unsubscribe(f"job:{job_id}")
        await pubsub.aclose()
        await redis.aclose()
