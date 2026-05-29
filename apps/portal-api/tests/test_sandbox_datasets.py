"""Sandbox datasets: запись/чтение/гранты/кросс-агент/лимиты + минт токена.

Эндпоинты /api/sandbox/datasets аутентифицируются ephemeral-токеном
(Bearer). Auth-зависимость берёт get_db из portal_api.db, а роутер — из
portal_api.deps; это РАЗНЫЕ объекты, поэтому переопределяем оба.
"""
from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.services import ephemeral_token as eph_svc
from tests.factories import (
    make_agent,
    make_agent_version,
    make_job,
    make_tab,
    make_user,
)


@pytest_asyncio.fixture
async def sandbox_client(db: AsyncSession) -> AsyncClient:
    """AsyncClient к реальному app с обоими get_db, направленными в тестовую сессию."""
    from portal_api.db import get_db as db_get_db
    from portal_api.deps import get_db as deps_get_db
    from portal_api.main import app

    async def _override():
        yield db

    app.dependency_overrides[deps_get_db] = _override
    app.dependency_overrides[db_get_db] = _override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"Origin": "http://test"},
        ) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


async def _mint_agent_token(
    db: AsyncSession,
    *,
    grants: list[dict],
    slug_suffix: str,
) -> str:
    """Создать агента с runtime.datasets-грантами + job + ephemeral-токен."""
    user = await make_user(db)
    tab = await make_tab(db)
    agent = await make_agent(
        db, slug=f"a-{slug_suffix}-{uuid.uuid4().hex[:6]}",
        tab_id=tab.id, created_by_user_id=user.id, enabled=True,
    )
    version = await make_agent_version(
        db, agent_id=agent.id, created_by_user_id=user.id, status="ready",
        manifest_jsonb={"runtime": {"datasets": grants}},
    )
    job = await make_job(db, agent_version_id=version.id, user_id=user.id)
    plain, _ = eph_svc.generate()
    await eph_svc.insert(
        db, plaintext=plain, job_id=job.id, user_id=user.id,
        agent_version_id=version.id, ttl=timedelta(hours=1),
    )
    await db.flush()
    return plain


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_put_then_get(db: AsyncSession, sandbox_client: AsyncClient) -> None:
    token = await _mint_agent_token(
        db, grants=[{"slug": "math-tasks", "access": "readwrite"}], slug_suffix="rw",
    )
    put = await sandbox_client.put(
        "/api/sandbox/datasets/math-tasks/record",
        headers=_auth(token),
        json={"key": "task-1", "content_format": "latex", "content": r"\section{X}"},
    )
    assert put.status_code == 200, put.text
    assert put.json()["key"] == "task-1"
    assert put.json()["content"] == r"\section{X}"

    got = await sandbox_client.get(
        "/api/sandbox/datasets/math-tasks/record",
        headers=_auth(token), params={"key": "task-1"},
    )
    assert got.status_code == 200, got.text
    assert got.json()["content"] == r"\section{X}"
    assert got.json()["content_format"] == "latex"


@pytest.mark.asyncio
async def test_cross_agent_read(db: AsyncSession, sandbox_client: AsyncClient) -> None:
    """Один агент пишет (write), другой читает (read) тот же датасет."""
    writer = await _mint_agent_token(
        db, grants=[{"slug": "shared", "access": "write"}], slug_suffix="w",
    )
    reader = await _mint_agent_token(
        db, grants=[{"slug": "shared", "access": "read"}], slug_suffix="r",
    )
    put = await sandbox_client.put(
        "/api/sandbox/datasets/shared/record",
        headers=_auth(writer),
        json={"key": "k1", "value": {"answer": 42}},
    )
    assert put.status_code == 200, put.text

    got = await sandbox_client.get(
        "/api/sandbox/datasets/shared/record",
        headers=_auth(reader), params={"key": "k1"},
    )
    assert got.status_code == 200, got.text
    assert got.json()["value"] == {"answer": 42}


@pytest.mark.asyncio
async def test_access_denied_no_grant(
    db: AsyncSession, sandbox_client: AsyncClient
) -> None:
    token = await _mint_agent_token(
        db, grants=[{"slug": "allowed", "access": "readwrite"}], slug_suffix="ng",
    )
    # Датасет не объявлен в манифесте -> 403.
    r = await sandbox_client.get(
        "/api/sandbox/datasets/other-ds/record",
        headers=_auth(token), params={"key": "x"},
    )
    assert r.status_code == 403, r.text
    assert r.json()["error"]["code"] == "dataset_access_denied"


@pytest.mark.asyncio
async def test_read_only_cannot_write(
    db: AsyncSession, sandbox_client: AsyncClient
) -> None:
    token = await _mint_agent_token(
        db, grants=[{"slug": "ro", "access": "read"}], slug_suffix="ro",
    )
    r = await sandbox_client.put(
        "/api/sandbox/datasets/ro/record",
        headers=_auth(token), json={"key": "k", "value": {"a": 1}},
    )
    assert r.status_code == 403, r.text
    assert r.json()["error"]["code"] == "dataset_access_denied"


@pytest.mark.asyncio
async def test_upsert_keeps_single_record(
    db: AsyncSession, sandbox_client: AsyncClient
) -> None:
    token = await _mint_agent_token(
        db, grants=[{"slug": "up", "access": "readwrite"}], slug_suffix="up",
    )
    for v in (1, 2, 3):
        r = await sandbox_client.put(
            "/api/sandbox/datasets/up/record",
            headers=_auth(token), json={"key": "same", "value": {"v": v}},
        )
        assert r.status_code == 200, r.text

    lst = await sandbox_client.get(
        "/api/sandbox/datasets/up/records", headers=_auth(token),
    )
    assert lst.status_code == 200, lst.text
    body = lst.json()
    assert body["total"] == 1
    assert body["items"][0]["value"] == {"v": 3}


@pytest.mark.asyncio
async def test_list_prefix(db: AsyncSession, sandbox_client: AsyncClient) -> None:
    token = await _mint_agent_token(
        db, grants=[{"slug": "lp", "access": "readwrite"}], slug_suffix="lp",
    )
    for k in ("task-1", "task-2", "note-1"):
        await sandbox_client.put(
            "/api/sandbox/datasets/lp/record",
            headers=_auth(token), json={"key": k, "value": {"k": k}},
        )
    r = await sandbox_client.get(
        "/api/sandbox/datasets/lp/records",
        headers=_auth(token), params={"prefix": "task-"},
    )
    assert r.status_code == 200, r.text
    keys = {i["key"] for i in r.json()["items"]}
    assert keys == {"task-1", "task-2"}
    assert r.json()["total"] == 2


@pytest.mark.asyncio
async def test_get_missing_404(db: AsyncSession, sandbox_client: AsyncClient) -> None:
    token = await _mint_agent_token(
        db, grants=[{"slug": "m404", "access": "readwrite"}], slug_suffix="m4",
    )
    r = await sandbox_client.get(
        "/api/sandbox/datasets/m404/record",
        headers=_auth(token), params={"key": "nope"},
    )
    assert r.status_code == 404, r.text
    assert r.json()["error"]["code"] == "dataset_record_not_found"


@pytest.mark.asyncio
async def test_record_too_large_413(
    db: AsyncSession, sandbox_client: AsyncClient
) -> None:
    token = await _mint_agent_token(
        db, grants=[{"slug": "big", "access": "readwrite"}], slug_suffix="big",
    )
    huge = "x" * (256 * 1024 + 10)
    r = await sandbox_client.put(
        "/api/sandbox/datasets/big/record",
        headers=_auth(token), json={"key": "k", "content": huge},
    )
    assert r.status_code == 413, r.text
    assert r.json()["error"]["code"] == "dataset_record_too_large"


@pytest.mark.asyncio
async def test_delete_then_get_404(
    db: AsyncSession, sandbox_client: AsyncClient
) -> None:
    token = await _mint_agent_token(
        db, grants=[{"slug": "del", "access": "readwrite"}], slug_suffix="del",
    )
    await sandbox_client.put(
        "/api/sandbox/datasets/del/record",
        headers=_auth(token), json={"key": "k", "value": {"a": 1}},
    )
    dele = await sandbox_client.request(
        "DELETE", "/api/sandbox/datasets/del/record",
        headers=_auth(token), params={"key": "k"},
    )
    assert dele.status_code == 204, dele.text
    got = await sandbox_client.get(
        "/api/sandbox/datasets/del/record",
        headers=_auth(token), params={"key": "k"},
    )
    assert got.status_code == 404, got.text


@pytest.mark.asyncio
async def test_unauthenticated_401(sandbox_client: AsyncClient) -> None:
    r = await sandbox_client.get(
        "/api/sandbox/datasets/anything/record", params={"key": "x"},
    )
    assert r.status_code == 401, r.text


@pytest.mark.asyncio
async def test_job_service_mints_token_for_dataset_only_agent(
    db: AsyncSession,
) -> None:
    """Агент без runtime.llm, но с runtime.datasets, всё равно получает токен."""
    from portal_api.services import job_service

    user = await make_user(db)
    tab = await make_tab(db)
    agent = await make_agent(
        db, slug=f"ds-only-{uuid.uuid4().hex[:6]}",
        tab_id=tab.id, created_by_user_id=user.id, enabled=True,
    )
    version = await make_agent_version(
        db, agent_id=agent.id, created_by_user_id=user.id, status="ready",
        manifest_jsonb={"runtime": {"datasets": [{"slug": "x", "access": "write"}]}},
    )
    agent.current_version_id = version.id
    await db.flush()

    _job, token = await job_service.create_job(
        db, agent_slug=agent.slug, params={}, user_id=user.id,
    )
    assert token is not None
    assert token.startswith("por-job-")


@pytest.mark.asyncio
async def test_admin_list_records_and_delete(
    db: AsyncSession, admin_client: AsyncClient, admin_user: object
) -> None:
    """Admin видит датасеты + записи, удаляет запись и датасет целиком."""
    from portal_api.models import Dataset, DatasetRecord

    ds = Dataset(id=uuid.uuid4(), slug="adm-ds", description="demo")
    db.add(ds)
    await db.flush()
    db.add(DatasetRecord(
        id=uuid.uuid4(), dataset_id=ds.id, record_key="k1",
        content_format="json", value_jsonb={"a": 1},
    ))
    db.add(DatasetRecord(
        id=uuid.uuid4(), dataset_id=ds.id, record_key="k2",
        content_format="latex", content_text="x",
    ))
    await db.commit()

    lst = await admin_client.get("/api/admin/datasets")
    assert lst.status_code == 200, lst.text
    item = next(d for d in lst.json() if d["slug"] == "adm-ds")
    assert item["record_count"] == 2

    recs = await admin_client.get("/api/admin/datasets/adm-ds/records")
    assert recs.status_code == 200, recs.text
    assert {r["key"] for r in recs.json()} == {"k1", "k2"}

    d1 = await admin_client.request(
        "DELETE", "/api/admin/datasets/adm-ds/record", params={"key": "k1"}
    )
    assert d1.status_code == 204, d1.text

    dd = await admin_client.delete("/api/admin/datasets/adm-ds")
    assert dd.status_code == 204, dd.text

    after = await admin_client.get("/api/admin/datasets/adm-ds/records")
    assert after.status_code == 404, after.text


@pytest.mark.asyncio
async def test_admin_delete_unknown_dataset_404(
    db: AsyncSession, admin_client: AsyncClient
) -> None:
    r = await admin_client.delete("/api/admin/datasets/nope-ds")
    assert r.status_code == 404, r.text
    assert r.json()["error"]["code"] == "DATASET_NOT_FOUND"


@pytest.mark.asyncio
async def test_job_service_no_token_for_plain_agent(db: AsyncSession) -> None:
    """Агент без runtime.llm и без runtime.datasets — токен не выдаётся."""
    from portal_api.services import job_service

    user = await make_user(db)
    tab = await make_tab(db)
    agent = await make_agent(
        db, slug=f"plain-{uuid.uuid4().hex[:6]}",
        tab_id=tab.id, created_by_user_id=user.id, enabled=True,
    )
    version = await make_agent_version(
        db, agent_id=agent.id, created_by_user_id=user.id, status="ready",
        manifest_jsonb={"runtime": {}},
    )
    agent.current_version_id = version.id
    await db.flush()

    _job, token = await job_service.create_job(
        db, agent_slug=agent.slug, params={}, user_id=user.id,
    )
    assert token is None
