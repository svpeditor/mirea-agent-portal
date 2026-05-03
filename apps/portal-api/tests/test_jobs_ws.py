"""WS /api/jobs/{id}/stream -- resync + pub/sub bridge."""
from __future__ import annotations

import copy
import json
import os
import secrets
import time
import uuid

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from starlette.websockets import WebSocketDisconnect

from portal_api.main import app


def _reset_global_db_engine() -> None:
    """Reset the global SQLAlchemy engine/sessionmaker.

    Needed before TestClient so its lifespan creates a fresh engine in its own
    event loop, avoiding asyncpg 'attached to different loop' errors.
    """
    import portal_api.db as db_module
    db_module._engine = None
    db_module._sessionmaker = None


def _make_settings_override(redis_url: str):
    """Return a get_settings() override with redis_url pointing at the test container."""
    from pydantic import RedisDsn

    from portal_api.config import get_settings
    base = get_settings()
    s = copy.copy(base)
    object.__setattr__(s, "redis_url", RedisDsn(redis_url))
    return lambda: s


def _make_db_override():
    """Return a get_db override that creates a FRESH engine per call.

    Uses NullPool to avoid asyncpg connection pooling cross-event-loop issues.
    Each request gets a fresh connection that's closed immediately after use.
    """
    db_url = os.environ["DATABASE_URL"]

    async def override_get_db():
        # NullPool: no connection reuse, no pool state tied to any event loop
        engine = create_async_engine(db_url, poolclass=NullPool)
        sm = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with sm() as session:
            yield session
        await engine.dispose()

    return override_get_db


async def _setup_ws_scenario(*, set_running: bool = False):
    """Create user + agent + job with real commits. Returns (user_id, job_id).

    Uses the pytest session event loop for setup.
    """
    from portal_api.core.security import hash_password
    from portal_api.models import User
    from portal_api.services.job_service import create_job
    from tests.factories import make_agent, make_agent_version, make_tab

    engine = create_async_engine(os.environ["DATABASE_URL"], poolclass=NullPool)
    sm = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    suffix = secrets.token_hex(4)

    try:
        async with sm() as session:
            user = User(
                email=f"ws-{suffix}@example.com",
                password_hash=hash_password("test"),
                display_name="WS User",
                role="user",
            )
            session.add(user)
            await session.flush()
            user_id = user.id

            tab = await make_tab(session, slug=f"ws-{suffix}", name="T", order_idx=1)
            agent = await make_agent(session, slug=f"ws-{suffix}", tab_id=tab.id,
                                      created_by_user_id=user_id, enabled=True)
            v = await make_agent_version(session, agent_id=agent.id,
                                          created_by_user_id=user_id, status="ready")
            agent.current_version_id = v.id
            await session.commit()

            job, _eph = await create_job(session, agent_slug=f"ws-{suffix}", params={},
                                         user_id=user_id)
            if set_running:
                job.status = "running"
            await session.commit()
            job_id = job.id
    finally:
        await engine.dispose()

    return user_id, job_id


async def _setup_user():
    """Create an isolated user with real commits. Returns user_id."""
    from portal_api.core.security import hash_password
    from portal_api.models import User

    engine = create_async_engine(os.environ["DATABASE_URL"], poolclass=NullPool)
    sm = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    suffix = secrets.token_hex(4)
    try:
        async with sm() as session:
            user = User(
                email=f"ws-stranger-{suffix}@example.com",
                password_hash=hash_password("test"),
                display_name="Stranger",
                role="user",
            )
            session.add(user)
            await session.commit()
            return user.id
    finally:
        await engine.dispose()


async def _add_events(job_id: uuid.UUID, seqs) -> None:
    """Insert job events with real commits."""
    engine = create_async_engine(os.environ["DATABASE_URL"], poolclass=NullPool)
    try:
        async with engine.connect() as conn:
            for s in seqs:
                await conn.execute(
                    sa.text(
                        "INSERT INTO job_events"
                        " (id, job_id, seq, event_type, payload_jsonb, ts)"
                        " VALUES (:id, :jid, :seq, 'progress', :payload, NOW())"
                    ),
                    {"id": str(uuid.uuid4()), "jid": str(job_id),
                     "seq": s, "payload": json.dumps({"v": s})},
                )
            await conn.commit()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_ws_resync_sends_existing_events(
    redis_url, reset_redis, _migrated,
) -> None:
    from portal_api.core.security import create_access_token
    from portal_api.deps import get_db, get_settings

    user_id, job_id = await _setup_ws_scenario(set_running=True)
    await _add_events(job_id, [1, 2, 3])

    app.dependency_overrides[get_settings] = _make_settings_override(redis_url)
    app.dependency_overrides[get_db] = _make_db_override()

    token = create_access_token(str(user_id), "user")

    try:
        _reset_global_db_engine()
        with TestClient(app, cookies={"access_token": token}) as tc, tc.websocket_connect(f"/api/jobs/{job_id}/stream?since=1") as ws:  # noqa: E501
            msg = ws.receive_json()
            assert msg["type"] == "resync"
            assert [e["seq"] for e in msg["events"]] == [2, 3]
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_db, None)
        _reset_global_db_engine()


@pytest.mark.asyncio
async def test_ws_pubsub_forwards_new_events(
    redis_url, reset_redis, _migrated,
) -> None:
    from portal_api.core.security import create_access_token
    from portal_api.deps import get_db, get_settings

    user_id, job_id = await _setup_ws_scenario(set_running=True)

    app.dependency_overrides[get_settings] = _make_settings_override(redis_url)
    app.dependency_overrides[get_db] = _make_db_override()

    token = create_access_token(str(user_id), "user")

    try:
        _reset_global_db_engine()
        with TestClient(app, cookies={"access_token": token}) as tc, tc.websocket_connect(f"/api/jobs/{job_id}/stream?since=0") as ws:  # noqa: E501
            ws.receive_json()  # resync (empty)
            # Publish from a sync Redis client to avoid event-loop crossing
            import redis as sync_redis
            r = sync_redis.from_url(redis_url)
            r.publish(
                f"job:{job_id}",
                json.dumps({"seq": 1, "event": {"type": "started"}}),
            )
            r.close()
            time.sleep(0.3)
            msg = ws.receive_json()
            assert msg == {"seq": 1, "event": {"type": "started"}}
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_db, None)
        _reset_global_db_engine()


@pytest.mark.asyncio
async def test_ws_close_4404_for_other_user(
    reset_redis, _migrated,
) -> None:
    from portal_api.core.security import create_access_token
    from portal_api.deps import get_db

    # Job created by owner; stranger tries to connect
    _owner_id, job_id = await _setup_ws_scenario()
    stranger_id = await _setup_user()

    app.dependency_overrides[get_db] = _make_db_override()

    token = create_access_token(str(stranger_id), "user")

    try:
        _reset_global_db_engine()
        with TestClient(app, cookies={"access_token": token}) as tc, pytest.raises(WebSocketDisconnect) as exc_info, tc.websocket_connect(f"/api/jobs/{job_id}/stream"):  # noqa: E501
            pass
        assert exc_info.value.code == 4404
    finally:
        app.dependency_overrides.pop(get_db, None)
        _reset_global_db_engine()


@pytest.mark.asyncio
async def test_ws_close_4401_unauth(_migrated) -> None:
    # Ensure at least one user exists so bootstrap_admin doesn't raise
    await _setup_user()
    _reset_global_db_engine()
    with TestClient(app) as tc, pytest.raises(WebSocketDisconnect) as exc_info, tc.websocket_connect(f"/api/jobs/{uuid.uuid4()}/stream"):  # noqa: E501
        pass
    assert exc_info.value.code == 4401
