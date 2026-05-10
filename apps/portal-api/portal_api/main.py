"""FastAPI app — точка входа."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from portal_api.bootstrap import bootstrap_admin, bootstrap_tabs
from portal_api.config import get_settings
from portal_api.core.exceptions import AppError
from portal_api.core.logging import configure_logging
from portal_api.core.origin import OriginCheckMiddleware
from portal_api.core.request_log import RequestLogMiddleware
from portal_api.core.sentry import init_sentry
from portal_api.db import get_sessionmaker
from portal_api.routers import (
    admin_agent_versions,
    admin_agents,
    admin_invites,
    admin_tabs,
    admin_users,
    auth,
    health,
    jobs,
    jobs_ws,
    me,
    public_agents,
    public_tabs,
)
from portal_api.routers.admin_quota import router as admin_quota_router
from portal_api.routers.llm_proxy import router as llm_proxy_router
from portal_api.services.llm_pricing import PricingCache, periodic_refresh


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    init_sentry(settings)
    session_local = get_sessionmaker()
    async with session_local() as session:
        await bootstrap_admin(session, settings)
        await bootstrap_tabs(session)
    cache = PricingCache(
        base_url=settings.openrouter_base_url,
        timeout_s=settings.llm_request_timeout_seconds,
    )
    await cache.refresh()
    app.state.pricing_cache = cache
    refresh_task = asyncio.create_task(
        periodic_refresh(cache, settings.llm_pricing_refresh_interval_seconds)
    )
    try:
        yield
    finally:
        refresh_task.cancel()
        try:
            await refresh_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="MIREA Agent Portal API", version="0.1.0", lifespan=lifespan)

app.add_middleware(OriginCheckMiddleware)
app.add_middleware(RequestLogMiddleware)  # outermost — sees status from inner middleware


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    body: dict[str, object] = {"error": {"code": exc.code, "message": exc.message}}
    if exc.details is not None:
        body["error"]["details"] = exc.details  # type: ignore[index]
    return JSONResponse(status_code=exc.status_code, content=body)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Невалидные данные.",
                "details": [
                    {"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]}
                    for e in exc.errors()
                ],
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logging.getLogger(__name__).exception("unhandled_exception", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Внутренняя ошибка сервера. Попробуй позже.",
            }
        },
    )


app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(me.router, prefix="/api")
app.include_router(admin_users.router, prefix="/api")
app.include_router(admin_invites.router, prefix="/api")
app.include_router(admin_tabs.router, prefix="/api")
app.include_router(admin_agents.router, prefix="/api")
app.include_router(admin_agent_versions.router, prefix="/api")
app.include_router(public_tabs.router, prefix="/api")
app.include_router(public_agents.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(jobs_ws.router, prefix="/api")
app.include_router(admin_quota_router)
app.include_router(llm_proxy_router)
