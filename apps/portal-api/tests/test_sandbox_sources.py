"""Тесты sandbox-прокси источников: CyberLeninka, OpenAlex, OA-PDF.

Внешние API замоканы через respx. Минт ephemeral-токена + override обоих
get_db — как в test_sandbox_arxiv_pdf.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import httpx
import pytest
import respx

from portal_api.models import UserQuota
from portal_api.routers.sandbox import (
    _is_safe_public_url,
    _openalex_abstract,
    _strip_html,
)
from portal_api.services import ephemeral_token as eph_svc
from tests.factories import make_agent, make_agent_version, make_job, make_tab, make_user

_PDF = b"%PDF-1.5\n1 0 obj<<>>endobj\ntrailer\n%%EOF\n"


async def _bearer(db, admin_user) -> str:
    user = await make_user(db, email="sbsrc@x.x", password="testpasswordX1")
    db.add(UserQuota(
        user_id=user.id, monthly_limit_usd=Decimal("5"), period_used_usd=Decimal("0"),
        period_starts_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        per_job_cap_usd=Decimal("0.5"),
    ))
    tab = await make_tab(db, slug="t-sbsrc", name="T", order_idx=1)
    agent = await make_agent(db, slug="a-sbsrc", tab_id=tab.id, created_by_user_id=admin_user.id)
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


# --- Чистые хелперы ---


def test_strip_html() -> None:
    assert _strip_html("Внедрение <b>цифровых</b>  технологий") == "Внедрение цифровых технологий"
    assert _strip_html(None) == ""


def test_openalex_abstract_reconstruct() -> None:
    inv = {"Digital": [0], "math": [1], "education": [2]}
    assert _openalex_abstract(inv) == "Digital math education"
    assert _openalex_abstract(None) == ""


def test_is_safe_public_url_rejects_private_and_http() -> None:
    assert _is_safe_public_url("http://example.com/x.pdf") is False  # не https
    assert _is_safe_public_url("https://127.0.0.1/x.pdf") is False   # loopback
    assert _is_safe_public_url("https://10.0.0.5/x.pdf") is False    # private
    assert _is_safe_public_url("ftp://example.com/x") is False


def test_is_safe_public_url_allows_public(monkeypatch) -> None:
    monkeypatch.setattr(
        "portal_api.routers.sandbox.socket.getaddrinfo",
        lambda *a, **k: [(2, 1, 6, "", ("93.184.216.34", 443))],
    )
    assert _is_safe_public_url("https://example.org/paper.pdf") is True


# --- Эндпоинты ---


@pytest.mark.asyncio
async def test_cyberleninka_search(client, db, admin_user) -> None:
    _override_db(db)
    plain = await _bearer(db, admin_user)
    payload = {"found": 1, "articles": [{
        "name": "Внедрение <b>цифровых</b> технологий",
        "annotation": "В статье <b>анализируется</b> внедрение",
        "link": "/article/n/vnedrenie-tehnologiy",
        "authors": ["Иванов И. И."], "year": "2023", "journal": "Журнал",
    }]}
    with respx.mock(base_url="https://cyberleninka.ru") as mock:
        mock.post("/api/search").mock(return_value=httpx.Response(200, json=payload))
        r = await client.get(
            "/api/sandbox/cyberleninka?query=цифровые технологии&size=3",
            headers={"Authorization": f"Bearer {plain}"},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 1
    a = body["articles"][0]
    assert a["title"] == "Внедрение цифровых технологий"
    assert a["abstract"] == "В статье анализируется внедрение"
    assert a["authors"] == ["Иванов И. И."]
    assert a["year"] == 2023
    assert a["slug"] == "vnedrenie-tehnologiy"
    assert a["url"] == "https://cyberleninka.ru/article/n/vnedrenie-tehnologiy"
    assert a["pdf_url"] == "https://cyberleninka.ru/article/n/vnedrenie-tehnologiy/pdf"


@pytest.mark.asyncio
async def test_openalex_search(client, db, admin_user) -> None:
    _override_db(db)
    plain = await _bearer(db, admin_user)
    payload = {"results": [{
        "display_name": "Digital Technology in Mathematics Education",
        "abstract_inverted_index": {"Why": [0], "it": [1], "works": [2]},
        "authorships": [{"author": {"display_name": "Jane Doe"}}],
        "publication_year": 2015, "cited_by_count": 242,
        "doi": "https://doi.org/10.1007/x",
        "open_access": {"is_oa": True, "oa_url": "https://repo.example.org/x.pdf"},
        "primary_location": {"source": {"display_name": "Springer"}},
        "id": "https://openalex.org/W1",
    }]}
    with respx.mock(base_url="https://api.openalex.org") as mock:
        mock.get("/works").mock(return_value=httpx.Response(200, json=payload))
        r = await client.get(
            "/api/sandbox/openalex?query=math education&per_page=2",
            headers={"Authorization": f"Bearer {plain}"},
        )
    assert r.status_code == 200, r.text
    w = r.json()["works"][0]
    assert w["title"] == "Digital Technology in Mathematics Education"
    assert w["abstract"] == "Why it works"
    assert w["authors"] == ["Jane Doe"]
    assert w["year"] == 2015
    assert w["doi"] == "10.1007/x"
    assert w["is_oa"] is True
    assert w["oa_url"] == "https://repo.example.org/x.pdf"


@pytest.mark.asyncio
async def test_cyberleninka_pdf(client, db, admin_user) -> None:
    _override_db(db)
    plain = await _bearer(db, admin_user)
    with respx.mock(base_url="https://cyberleninka.ru") as mock:
        mock.get("/article/n/vnedrenie-tehnologiy/pdf").mock(
            return_value=httpx.Response(200, content=_PDF,
                                        headers={"content-type": "application/pdf"}),
        )
        r = await client.get(
            "/api/sandbox/cyberleninka-pdf?slug=vnedrenie-tehnologiy",
            headers={"Authorization": f"Bearer {plain}"},
        )
    assert r.status_code == 200, r.text
    assert r.content == _PDF
    assert r.headers["content-type"].startswith("application/pdf")


@pytest.mark.asyncio
async def test_cyberleninka_pdf_bad_slug(client, db, admin_user) -> None:
    _override_db(db)
    plain = await _bearer(db, admin_user)
    r = await client.get(
        "/api/sandbox/cyberleninka-pdf?slug=../etc/passwd",
        headers={"Authorization": f"Bearer {plain}"},
    )
    assert r.status_code == 422, r.text


@pytest.mark.asyncio
async def test_oa_pdf_happy(client, db, admin_user, monkeypatch) -> None:
    _override_db(db)
    plain = await _bearer(db, admin_user)
    monkeypatch.setattr(
        "portal_api.routers.sandbox.socket.getaddrinfo",
        lambda *a, **k: [(2, 1, 6, "", ("93.184.216.34", 443))],
    )
    with respx.mock() as mock:
        mock.get(url__startswith="https://api.unpaywall.org/v2/").mock(
            return_value=httpx.Response(200, json={
                "best_oa_location": {"url_for_pdf": "https://repo.example.org/x.pdf"},
            }),
        )
        mock.get("https://repo.example.org/x.pdf").mock(
            return_value=httpx.Response(200, content=_PDF,
                                        headers={"content-type": "application/pdf"}),
        )
        r = await client.get(
            "/api/sandbox/oa-pdf?doi=10.1007/x",
            headers={"Authorization": f"Bearer {plain}"},
        )
    assert r.status_code == 200, r.text
    assert r.content == _PDF


@pytest.mark.asyncio
async def test_oa_pdf_no_oa(client, db, admin_user) -> None:
    _override_db(db)
    plain = await _bearer(db, admin_user)
    with respx.mock() as mock:
        mock.get(url__startswith="https://api.unpaywall.org/v2/").mock(
            return_value=httpx.Response(200, json={"best_oa_location": None}),
        )
        r = await client.get(
            "/api/sandbox/oa-pdf?doi=10.1007/closed",
            headers={"Authorization": f"Bearer {plain}"},
        )
    assert r.status_code == 404, r.text
    # sandbox-прокси кидают HTTPException -> FastAPI оборачивает в {"detail": ...}
    assert r.json()["detail"]["error"]["code"] == "OA_PDF_NO_OA"


@pytest.mark.asyncio
async def test_oa_pdf_bad_doi(client, db, admin_user) -> None:
    _override_db(db)
    plain = await _bearer(db, admin_user)
    r = await client.get(
        "/api/sandbox/oa-pdf?doi=not-a-doi",
        headers={"Authorization": f"Bearer {plain}"},
    )
    assert r.status_code == 422, r.text


@pytest.mark.asyncio
async def test_sources_require_token(client, db, admin_user) -> None:
    _override_db(db)
    await _bearer(db, admin_user)
    for path in ("/api/sandbox/cyberleninka?query=x", "/api/sandbox/openalex?query=x"):
        r = await client.get(path)
        assert r.status_code == 401, (path, r.text)
