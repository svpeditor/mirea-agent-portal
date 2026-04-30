"""FastAPI app — точка входа."""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from portal_api.bootstrap import bootstrap_admin
from portal_api.config import get_settings
from portal_api.core.exceptions import AppError
from portal_api.db import get_sessionmaker
from portal_api.routers import auth, health


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    session_local = get_sessionmaker()
    async with session_local() as session:
        await bootstrap_admin(session, settings)
    yield


app = FastAPI(title="MIREA Agent Portal API", version="0.1.0", lifespan=lifespan)


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


app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
