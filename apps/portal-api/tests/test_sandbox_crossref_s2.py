"""Тесты для /api/sandbox/crossref и /api/sandbox/semantic-scholar."""
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


async def _setup_bearer(db, admin_user) -> str:
    user = await make_user(db, email="sb2@x.x", password="testpasswordX1")
    db.add(UserQuota(
        user_id=user.id, monthly_limit_usd=Decimal("5"), period_used_usd=Decimal("0"),
        period_starts_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        per_job_cap_usd=Decimal("0.5"),
    ))
    tab = await make_tab(db, slug="t-sb2", name="T", order_idx=1)
    agent = await make_agent(db, slug="a-sb2", tab_id=tab.id, created_by_user_id=admin_user.id)
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


# --- Crossref ---

CROSSREF_OK = {
    "message": {
        "items": [
            {
                "DOI": "10.1109/5.771073",
                "title": ["Attention Is All You Need"],
                "author": [
                    {"given": "Ashish", "family": "Vaswani"},
                    {"given": "Noam", "family": "Shazeer"},
                ],
                "issued": {"date-parts": [[2017, 6, 12]]},
                "container-title": ["NeurIPS"],
                "type": "journal-article",
                "is-referenced-by-count": 95000,
                "URL": "https://doi.org/10.1109/5.771073",
            }
        ]
    }
}


@pytest.mark.asyncio
async def test_crossref_returns_parsed_works(client, db, admin_user) -> None:
    _override_db(db)
    plain = await _setup_bearer(db, admin_user)

    with respx.mock(base_url="https://api.crossref.org") as mock:
        mock.get("/works").mock(return_value=httpx.Response(200, json=CROSSREF_OK))
        r = await client.get(
            "/api/sandbox/crossref?query=attention&rows=5",
            headers={"Authorization": f"Bearer {plain}"},
        )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total"] == 1
    w = data["works"][0]
    assert w["doi"] == "10.1109/5.771073"
    assert w["title"] == "Attention Is All You Need"
    assert w["authors"] == ["Ashish Vaswani", "Noam Shazeer"]
    assert w["year"] == 2017
    assert w["venue"] == "NeurIPS"
    assert w["citation_count"] == 95000


@pytest.mark.asyncio
async def test_crossref_sends_polite_user_agent(client, db, admin_user) -> None:
    _override_db(db)
    plain = await _setup_bearer(db, admin_user)

    with respx.mock(base_url="https://api.crossref.org") as mock:
        route = mock.get("/works").mock(return_value=httpx.Response(200, json=CROSSREF_OK))
        await client.get(
            "/api/sandbox/crossref?query=x",
            headers={"Authorization": f"Bearer {plain}"},
        )
    sent = route.calls[0].request
    assert "mirea-agent-portal" in sent.headers["user-agent"]
    assert "mailto:" in sent.headers["user-agent"]


@pytest.mark.asyncio
async def test_crossref_502_on_upstream_error(client, db, admin_user) -> None:
    _override_db(db)
    plain = await _setup_bearer(db, admin_user)

    with respx.mock(base_url="https://api.crossref.org") as mock:
        mock.get("/works").mock(return_value=httpx.Response(503))
        r = await client.get(
            "/api/sandbox/crossref?query=x",
            headers={"Authorization": f"Bearer {plain}"},
        )
    assert r.status_code == 502
    assert r.json()["detail"]["error"]["code"] == "CROSSREF_BAD_STATUS"


@pytest.mark.asyncio
async def test_crossref_requires_bearer(client) -> None:
    r = await client.get("/api/sandbox/crossref?query=x")
    assert r.status_code == 401


# --- Semantic Scholar ---

S2_OK = {
    "data": [
        {
            "paperId": "abc123",
            "title": "Sparse Transformers",
            "abstract": "Sparsity helps.",
            "authors": [{"name": "Rewon Child"}, {"name": "Scott Gray"}],
            "year": 2019,
            "venue": "arXiv",
            "citationCount": 500,
            "referenceCount": 30,
            "externalIds": {"DOI": "10.1000/sparse", "ArXiv": "1904.10509"},
            "url": "https://www.semanticscholar.org/paper/abc123",
        }
    ]
}


@pytest.mark.asyncio
async def test_s2_returns_parsed_papers(client, db, admin_user) -> None:
    _override_db(db)
    plain = await _setup_bearer(db, admin_user)

    with respx.mock(base_url="https://api.semanticscholar.org") as mock:
        mock.get("/graph/v1/paper/search").mock(return_value=httpx.Response(200, json=S2_OK))
        r = await client.get(
            "/api/sandbox/semantic-scholar?query=transformer&limit=10",
            headers={"Authorization": f"Bearer {plain}"},
        )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total"] == 1
    p = data["papers"][0]
    assert p["paper_id"] == "abc123"
    assert p["arxiv_id"] == "1904.10509"
    assert p["doi"] == "10.1000/sparse"
    assert p["citation_count"] == 500


@pytest.mark.asyncio
async def test_s2_passes_through_429_rate_limit(client, db, admin_user) -> None:
    _override_db(db)
    plain = await _setup_bearer(db, admin_user)

    with respx.mock(base_url="https://api.semanticscholar.org") as mock:
        mock.get("/graph/v1/paper/search").mock(return_value=httpx.Response(429))
        r = await client.get(
            "/api/sandbox/semantic-scholar?query=x",
            headers={"Authorization": f"Bearer {plain}"},
        )
    assert r.status_code == 429
    assert r.json()["detail"]["error"]["code"] == "S2_RATE_LIMITED"


@pytest.mark.asyncio
async def test_s2_requires_bearer(client) -> None:
    r = await client.get("/api/sandbox/semantic-scholar?query=x")
    assert r.status_code == 401
