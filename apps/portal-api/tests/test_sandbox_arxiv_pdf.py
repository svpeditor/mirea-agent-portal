"""Тесты для /api/sandbox/arxiv-pdf — allowlist-proxy скачивания PDF.

Агент сидит в internal-сети без интернета; единственный способ забрать
сам файл статьи — через этот endpoint. Allowlist жёсткий: только
arxiv.org/pdf, только валидный arxiv_id, лимит размера, content-type guard.
"""
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

_PDF_BYTES = b"%PDF-1.5\n1 0 obj\n<<>>\nendobj\ntrailer\n%%EOF\n"


async def _setup_bearer(db, admin_user) -> str:
    user = await make_user(db, email="sbpdf@x.x", password="testpasswordX1")
    db.add(UserQuota(
        user_id=user.id, monthly_limit_usd=Decimal("5"), period_used_usd=Decimal("0"),
        period_starts_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        per_job_cap_usd=Decimal("0.5"),
    ))
    tab = await make_tab(db, slug="t-sbpdf", name="T", order_idx=1)
    agent = await make_agent(db, slug="a-sbpdf", tab_id=tab.id, created_by_user_id=admin_user.id)
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
async def test_pdf_streams_bytes(client, db, admin_user) -> None:
    _override_db(db)
    plain = await _setup_bearer(db, admin_user)

    with respx.mock(base_url="https://arxiv.org") as mock:
        route = mock.get("/pdf/2401.01234v1.pdf").mock(
            return_value=httpx.Response(
                200, content=_PDF_BYTES,
                headers={"content-type": "application/pdf"},
            ),
        )
        r = await client.get(
            "/api/sandbox/arxiv-pdf?arxiv_id=2401.01234v1",
            headers={"Authorization": f"Bearer {plain}"},
        )

    assert route.called
    assert r.status_code == 200, r.text
    assert r.content == _PDF_BYTES
    assert r.headers["content-type"].startswith("application/pdf")
    assert "2401.01234v1.pdf" in r.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_pdf_accepts_old_style_id(client, db, admin_user) -> None:
    _override_db(db)
    plain = await _setup_bearer(db, admin_user)

    with respx.mock(base_url="https://arxiv.org") as mock:
        mock.get("/pdf/math/0501001.pdf").mock(
            return_value=httpx.Response(
                200, content=_PDF_BYTES, headers={"content-type": "application/pdf"},
            ),
        )
        r = await client.get(
            "/api/sandbox/arxiv-pdf?arxiv_id=math/0501001",
            headers={"Authorization": f"Bearer {plain}"},
        )
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
def test_arxiv_id_regex_rejects_trailing_newline() -> None:
    """L1: regex как самостоятельный примитив безопасности не должен
    матчить хвостовой \\n (защита если кто-то уберёт .strip() до match)."""
    from portal_api.routers.sandbox import _ARXIV_ID_RE

    assert _ARXIV_ID_RE.match("2401.01234")
    assert not _ARXIV_ID_RE.match("2401.01234\n")
    assert not _ARXIV_ID_RE.match("2401.01234\nrm -rf")


@pytest.mark.parametrize("bad", ["../etc/passwd", "http://evil.com/x", "2401.01234 x", "a" * 60])
async def test_pdf_rejects_invalid_id(client, db, admin_user, bad) -> None:
    _override_db(db)
    plain = await _setup_bearer(db, admin_user)
    r = await client.get(
        "/api/sandbox/arxiv-pdf",
        params={"arxiv_id": bad},
        headers={"Authorization": f"Bearer {plain}"},
    )
    assert r.status_code == 422, r.text


@pytest.mark.asyncio
async def test_pdf_502_on_upstream_5xx(client, db, admin_user) -> None:
    _override_db(db)
    plain = await _setup_bearer(db, admin_user)
    with respx.mock(base_url="https://arxiv.org") as mock:
        mock.get("/pdf/2401.01234.pdf").mock(return_value=httpx.Response(503))
        r = await client.get(
            "/api/sandbox/arxiv-pdf?arxiv_id=2401.01234",
            headers={"Authorization": f"Bearer {plain}"},
        )
    assert r.status_code == 502
    assert r.json()["detail"]["error"]["code"] == "ARXIV_PDF_BAD_STATUS"


@pytest.mark.asyncio
async def test_pdf_502_on_network_error(client, db, admin_user) -> None:
    _override_db(db)
    plain = await _setup_bearer(db, admin_user)
    with respx.mock(base_url="https://arxiv.org") as mock:
        mock.get("/pdf/2401.01234.pdf").mock(side_effect=httpx.ConnectError("offline"))
        r = await client.get(
            "/api/sandbox/arxiv-pdf?arxiv_id=2401.01234",
            headers={"Authorization": f"Bearer {plain}"},
        )
    assert r.status_code == 502
    assert r.json()["detail"]["error"]["code"] == "ARXIV_PDF_UNAVAILABLE"


@pytest.mark.asyncio
async def test_pdf_502_when_not_pdf(client, db, admin_user) -> None:
    """arXiv иногда отдаёт HTML-страницу ошибки с 200 — это не PDF."""
    _override_db(db)
    plain = await _setup_bearer(db, admin_user)
    with respx.mock(base_url="https://arxiv.org") as mock:
        mock.get("/pdf/2401.01234.pdf").mock(
            return_value=httpx.Response(
                200, content=b"<html>not found</html>",
                headers={"content-type": "text/html"},
            ),
        )
        r = await client.get(
            "/api/sandbox/arxiv-pdf?arxiv_id=2401.01234",
            headers={"Authorization": f"Bearer {plain}"},
        )
    assert r.status_code == 502
    assert r.json()["detail"]["error"]["code"] == "ARXIV_PDF_NOT_PDF"


@pytest.mark.asyncio
async def test_pdf_502_when_too_large(client, db, admin_user) -> None:
    _override_db(db)
    plain = await _setup_bearer(db, admin_user)
    huge = b"%PDF-1.5" + b"0" * (26 * 1024 * 1024)
    with respx.mock(base_url="https://arxiv.org") as mock:
        mock.get("/pdf/2401.01234.pdf").mock(
            return_value=httpx.Response(
                200, content=huge, headers={"content-type": "application/pdf"},
            ),
        )
        r = await client.get(
            "/api/sandbox/arxiv-pdf?arxiv_id=2401.01234",
            headers={"Authorization": f"Bearer {plain}"},
        )
    assert r.status_code == 502
    assert r.json()["detail"]["error"]["code"] == "ARXIV_PDF_TOO_LARGE"


@pytest.mark.asyncio
async def test_pdf_requires_bearer_token(client) -> None:
    r = await client.get("/api/sandbox/arxiv-pdf?arxiv_id=2401.01234")
    assert r.status_code == 401, r.text
