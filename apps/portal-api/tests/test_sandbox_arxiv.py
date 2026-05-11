"""Тесты для /api/sandbox/arxiv — allowlist-proxy для агентов."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import httpx
import pytest
import respx

from portal_api.models import UserQuota
from portal_api.services import ephemeral_token as eph_svc
from tests.factories import (
    make_agent, make_agent_version, make_job, make_tab, make_user,
)


_ARXIV_ATOM_2_ENTRIES = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2401.01234v1</id>
    <title>Attention Revisited</title>
    <summary>We revisit attention. </summary>
    <published>2024-01-02T00:00:00Z</published>
    <author><name>Vaswani A.</name></author>
    <author><name>Shazeer N.</name></author>
    <link href="https://arxiv.org/abs/2401.01234v1"/>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2310.55555v2</id>
    <title>Sparse Transformers</title>
    <summary>Sparsity helps. </summary>
    <published>2023-10-20T00:00:00Z</published>
    <author><name>Child R.</name></author>
    <link href="https://arxiv.org/abs/2310.55555v2"/>
  </entry>
</feed>
"""


async def _setup_bearer(db, admin_user) -> str:
    """Создаёт user+quota+agent+version+job+ephemeral, возвращает plaintext-токен."""
    user = await make_user(db, email="sb@x.x", password="testpasswordX1")
    db.add(UserQuota(
        user_id=user.id, monthly_limit_usd=Decimal("5"), period_used_usd=Decimal("0"),
        period_starts_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        per_job_cap_usd=Decimal("0.5"),
    ))
    tab = await make_tab(db, slug="t-sb", name="T", order_idx=1)
    agent = await make_agent(db, slug="a-sb", tab_id=tab.id, created_by_user_id=admin_user.id)
    av = await make_agent_version(
        db, agent_id=agent.id, created_by_user_id=admin_user.id, status="ready",
    )
    job = await make_job(db, agent_version_id=av.id, user_id=user.id)
    plain, _ = eph_svc.generate()
    await eph_svc.insert(
        db, plaintext=plain, job_id=job.id, user_id=user.id,
        agent_version_id=av.id, ttl=timedelta(minutes=65),
    )
    await db.flush()
    return plain


def _override_db(db):
    from portal_api.db import get_db as _db_get_db
    from portal_api.main import app

    async def _f():
        yield db
    app.dependency_overrides[_db_get_db] = _f


@pytest.mark.asyncio
async def test_arxiv_returns_parsed_papers(client, db, admin_user) -> None:
    _override_db(db)
    plain = await _setup_bearer(db, admin_user)

    with respx.mock(base_url="https://export.arxiv.org") as mock:
        mock.get("/api/query").mock(
            return_value=httpx.Response(200, text=_ARXIV_ATOM_2_ENTRIES),
        )
        r = await client.get(
            "/api/sandbox/arxiv?search_query=transformer&max_results=5",
            headers={"Authorization": f"Bearer {plain}"},
        )

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total"] == 2
    assert data["papers"][0]["title"] == "Attention Revisited"
    assert data["papers"][0]["year"] == 2024
    assert data["papers"][0]["arxiv_id"] == "2401.01234v1"
    assert data["papers"][0]["authors"] == ["Vaswani A.", "Shazeer N."]


@pytest.mark.asyncio
async def test_arxiv_wraps_plain_query_in_all_prefix(client, db, admin_user) -> None:
    """Если в search_query нет field-spec (`ti:`/`au:`), оборачиваем в `all:`."""
    _override_db(db)
    plain = await _setup_bearer(db, admin_user)

    with respx.mock(base_url="https://export.arxiv.org") as mock:
        route = mock.get("/api/query").mock(
            return_value=httpx.Response(200, text=_ARXIV_ATOM_2_ENTRIES),
        )
        await client.get(
            "/api/sandbox/arxiv?search_query=foobar",
            headers={"Authorization": f"Bearer {plain}"},
        )

    sent_url = str(route.calls[0].request.url)
    assert "all%3Afoobar" in sent_url or "all:foobar" in sent_url


@pytest.mark.asyncio
async def test_arxiv_keeps_field_prefix_intact(client, db, admin_user) -> None:
    _override_db(db)
    plain = await _setup_bearer(db, admin_user)

    with respx.mock(base_url="https://export.arxiv.org") as mock:
        route = mock.get("/api/query").mock(
            return_value=httpx.Response(200, text=_ARXIV_ATOM_2_ENTRIES),
        )
        await client.get(
            "/api/sandbox/arxiv?search_query=ti:transformer",
            headers={"Authorization": f"Bearer {plain}"},
        )

    sent_url = str(route.calls[0].request.url)
    # field-prefix не должен быть обёрнут в all:
    assert "all%3Ati" not in sent_url


@pytest.mark.asyncio
async def test_arxiv_502_when_upstream_5xx(client, db, admin_user) -> None:
    _override_db(db)
    plain = await _setup_bearer(db, admin_user)

    with respx.mock(base_url="https://export.arxiv.org") as mock:
        mock.get("/api/query").mock(return_value=httpx.Response(503, text="busy"))
        r = await client.get(
            "/api/sandbox/arxiv?search_query=test",
            headers={"Authorization": f"Bearer {plain}"},
        )
    assert r.status_code == 502
    assert r.json()["detail"]["error"]["code"] == "ARXIV_BAD_STATUS"


@pytest.mark.asyncio
async def test_arxiv_502_on_network_error(client, db, admin_user) -> None:
    _override_db(db)
    plain = await _setup_bearer(db, admin_user)

    with respx.mock(base_url="https://export.arxiv.org") as mock:
        mock.get("/api/query").mock(side_effect=httpx.ConnectError("offline"))
        r = await client.get(
            "/api/sandbox/arxiv?search_query=test",
            headers={"Authorization": f"Bearer {plain}"},
        )
    assert r.status_code == 502
    assert r.json()["detail"]["error"]["code"] == "ARXIV_UNAVAILABLE"


@pytest.mark.asyncio
async def test_arxiv_requires_bearer_token(client) -> None:
    """Без auth — 401, не 403 от Origin middleware."""
    r = await client.get("/api/sandbox/arxiv?search_query=test")
    assert r.status_code == 401, r.text


@pytest.mark.asyncio
async def test_arxiv_rejects_huge_max_results(client, db, admin_user) -> None:
    _override_db(db)
    plain = await _setup_bearer(db, admin_user)
    r = await client.get(
        "/api/sandbox/arxiv?search_query=test&max_results=9999",
        headers={"Authorization": f"Bearer {plain}"},
    )
    assert r.status_code == 422  # FastAPI validation


@pytest.mark.asyncio
async def test_arxiv_rejects_empty_query(client, db, admin_user) -> None:
    _override_db(db)
    plain = await _setup_bearer(db, admin_user)
    r = await client.get(
        "/api/sandbox/arxiv?search_query=",
        headers={"Authorization": f"Bearer {plain}"},
    )
    assert r.status_code == 422
