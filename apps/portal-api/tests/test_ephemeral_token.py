"""ephemeral_token: gen, hash, insert, resolve, revoke."""
from __future__ import annotations

import hashlib
from datetime import timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.models import EphemeralToken
from portal_api.services import ephemeral_token as svc
from tests.factories import (
    make_agent, make_agent_version, make_job, make_tab,
)


@pytest.mark.asyncio
async def test_generate_format() -> None:
    plain, h = svc.generate()
    assert plain.startswith("por-job-")
    assert len(plain) == 8 + 32  # "por-job-" + 32 hex chars (uuid4().hex)
    assert h == hashlib.sha256(plain.encode()).hexdigest()
    assert len(h) == 64


@pytest.mark.asyncio
async def test_insert_and_resolve(db: AsyncSession, admin_user) -> None:
    tab = await make_tab(db, slug="t-eph", name="T", order_idx=1)
    agent = await make_agent(db, slug="a-eph", tab_id=tab.id, created_by_user_id=admin_user.id)
    av = await make_agent_version(db, agent_id=agent.id, created_by_user_id=admin_user.id, status="ready")
    job = await make_job(db, agent_version_id=av.id, user_id=admin_user.id)

    plain, _ = svc.generate()
    await svc.insert(
        db,
        plaintext=plain,
        job_id=job.id,
        user_id=admin_user.id,
        agent_version_id=av.id,
        ttl=timedelta(minutes=65),
    )
    await db.commit()

    ctx = await svc.resolve(db, plain)
    assert ctx is not None
    assert ctx.user_id == admin_user.id
    assert ctx.agent_version_id == av.id
    assert ctx.agent_id == agent.id
    assert ctx.job_id == job.id


@pytest.mark.asyncio
async def test_resolve_unknown_returns_none(db: AsyncSession) -> None:
    ctx = await svc.resolve(db, "por-job-deadbeefdeadbeefdeadbeefdeadbeef")
    assert ctx is None


@pytest.mark.asyncio
async def test_resolve_revoked_returns_none(db: AsyncSession, admin_user) -> None:
    tab = await make_tab(db, slug="t-r", name="T", order_idx=1)
    agent = await make_agent(db, slug="a-r", tab_id=tab.id, created_by_user_id=admin_user.id)
    av = await make_agent_version(db, agent_id=agent.id, created_by_user_id=admin_user.id, status="ready")
    job = await make_job(db, agent_version_id=av.id, user_id=admin_user.id)

    plain, _ = svc.generate()
    await svc.insert(
        db, plaintext=plain, job_id=job.id, user_id=admin_user.id,
        agent_version_id=av.id, ttl=timedelta(minutes=65),
    )
    await db.commit()

    await svc.revoke_by_job(db, job.id)
    await db.commit()

    ctx = await svc.resolve(db, plain)
    assert ctx is None


@pytest.mark.asyncio
async def test_resolve_expired_returns_none(db: AsyncSession, admin_user) -> None:
    tab = await make_tab(db, slug="t-e", name="T", order_idx=1)
    agent = await make_agent(db, slug="a-e", tab_id=tab.id, created_by_user_id=admin_user.id)
    av = await make_agent_version(db, agent_id=agent.id, created_by_user_id=admin_user.id, status="ready")
    job = await make_job(db, agent_version_id=av.id, user_id=admin_user.id)

    plain, _ = svc.generate()
    await svc.insert(
        db, plaintext=plain, job_id=job.id, user_id=admin_user.id,
        agent_version_id=av.id, ttl=timedelta(seconds=-1),  # уже истёк
    )
    await db.commit()

    ctx = await svc.resolve(db, plain)
    assert ctx is None
