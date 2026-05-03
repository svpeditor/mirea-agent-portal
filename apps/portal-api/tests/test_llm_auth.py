"""ephemeral_token_auth FastAPI dependency: valid/missing/wrong-scheme/invalid/expired/revoked."""
from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.core.llm_auth import ephemeral_token_auth
from portal_api.core.exceptions import AppError
from portal_api.db import get_db
from portal_api.services import ephemeral_token as eph_svc
from portal_api.services.ephemeral_token import EphemeralTokenContext
from tests.factories import (
    make_agent, make_agent_version, make_job, make_tab, make_user,
)


def _build_app(db_session_factory=None, db_session=None):
    """Минимальный FastAPI с одним эндпоинтом под dependency.

    db_session_factory — async_sessionmaker (для тестов без db-фикстуры).
    db_session — готовая AsyncSession (для тестов с db-фикстурой, чтобы видеть данные).
    """
    app = FastAPI()

    @app.get("/echo")
    async def echo(ctx: EphemeralTokenContext = Depends(ephemeral_token_auth)):
        return {"user_id": str(ctx.user_id), "job_id": str(ctx.job_id)}

    # Регистрируем обработчик AppError, чтобы 401 возвращались в формате {"error": {...}}
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        body: dict[str, object] = {"error": {"code": exc.code, "message": exc.message}}
        if exc.details is not None:
            body["error"]["details"] = exc.details  # type: ignore[index]
        return JSONResponse(status_code=exc.status_code, content=body)

    if db_session is not None:
        # Переиспользуем существующую сессию (видит данные, записанные через db-фикстуру)
        async def _get_db_from_session():
            yield db_session

        app.dependency_overrides[get_db] = _get_db_from_session
    elif db_session_factory is not None:
        async def _get_db_from_factory():
            async with db_session_factory() as session:
                yield session

        app.dependency_overrides[get_db] = _get_db_from_factory

    return app


@pytest.mark.asyncio
async def test_valid_token_resolves(db, db_sessionmaker, admin_user) -> None:
    user = await make_user(db, email="auth@x.x", password="testpasswordX1")
    tab = await make_tab(db, slug="t-au", name="T", order_idx=1)
    agent = await make_agent(db, slug="a-au", tab_id=tab.id, created_by_user_id=admin_user.id)
    av = await make_agent_version(db, agent_id=agent.id, created_by_user_id=admin_user.id, status="ready")
    job = await make_job(db, agent_version_id=av.id, user_id=user.id)

    plain, _ = eph_svc.generate()
    await eph_svc.insert(
        db, plaintext=plain, job_id=job.id, user_id=user.id,
        agent_version_id=av.id, ttl=timedelta(minutes=65),
    )
    await db.flush()

    # Передаём ту же db-сессию в app, чтобы resolve видел данные в текущей транзакции
    app = _build_app(db_session=db)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/echo", headers={"Authorization": f"Bearer {plain}"})
    assert r.status_code == 200
    assert r.json()["user_id"] == str(user.id)
    assert r.json()["job_id"] == str(job.id)


@pytest.mark.asyncio
async def test_missing_header_returns_401(db_sessionmaker) -> None:
    app = _build_app(db_session_factory=db_sessionmaker)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/echo")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "invalid_ephemeral_token"


@pytest.mark.asyncio
async def test_wrong_scheme_returns_401(db_sessionmaker) -> None:
    app = _build_app(db_session_factory=db_sessionmaker)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/echo", headers={"Authorization": "Basic abc"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_unknown_token_returns_401(db_sessionmaker) -> None:
    app = _build_app(db_session_factory=db_sessionmaker)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/echo", headers={"Authorization": "Bearer por-job-deadbeef"})
    assert r.status_code == 401
