"""Sandbox-прокси для агентов: arXiv + (заготовка) другие источники.

Агенты сидят в portal-agents-net (internal=true) и не имеют прямого доступа
к публичному интернету. Этот роутер — единственный legal egress endpoint
для них. Аутентификация: ephemeral bearer token (как у LLM proxy).
Allowlist жёсткий: только arXiv API.
"""
# ruff: noqa: B008, RUF002, RUF003
from __future__ import annotations

import ipaddress
import re
import socket
from typing import Any
from urllib.parse import quote_plus, urlparse

import feedparser  # type: ignore[import-untyped]
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response

from portal_api.core.llm_auth import ephemeral_token_auth
from portal_api.services.ephemeral_token import EphemeralTokenContext

router = APIRouter(prefix="/api/sandbox", tags=["sandbox"])

ARXIV_API = "https://export.arxiv.org/api/query"
ARXIV_TIMEOUT_S = 30.0
MAX_RESULTS_HARD_CAP = 100

CROSSREF_API = "https://api.crossref.org/works"
CROSSREF_TIMEOUT_S = 30.0
# Crossref просит User-Agent с контактом (polite pool).
CROSSREF_UA = "mirea-agent-portal/1.0 (mailto:noreply@mirea.ru)"

S2_API = "https://api.semanticscholar.org/graph/v1/paper/search"
S2_TIMEOUT_S = 30.0
S2_FIELDS = "paperId,title,abstract,authors,year,venue,citationCount,referenceCount,externalIds,url"

OPENALEX_API = "https://api.openalex.org/works"
OPENALEX_TIMEOUT_S = 30.0
# OpenAlex просит контакт в mailto (polite pool) — даёт стабильный rate limit.
OPENALEX_MAILTO = "noreply@mirea.ru"

CYBERLENINKA_API = "https://cyberleninka.ru/api/search"
CYBERLENINKA_BASE = "https://cyberleninka.ru"
CYBERLENINKA_TIMEOUT_S = 30.0
CYBERLENINKA_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
# /article/n/<slug> — slug из латиницы, цифр и дефисов (транслит заголовка).
_CL_SLUG_RE = re.compile(r"\A[a-z0-9-]{3,200}\Z")

UNPAYWALL_API = "https://api.unpaywall.org/v2"
UNPAYWALL_EMAIL = "noreply@mirea.ru"
OA_PDF_TIMEOUT_S = 60.0
_DOI_RE = re.compile(r"\A10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\Z")

ARXIV_PDF_BASE = "https://arxiv.org/pdf"
ARXIV_PDF_TIMEOUT_S = 60.0
MAX_PDF_BYTES = 25 * 1024 * 1024  # arXiv PDF почти всегда < 5 МБ; 25 — запас


def _strip_html(s: str) -> str:
    """Убрать html-теги (CyberLeninka подсвечивает совпадения <b>...</b>)."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def _openalex_abstract(inv_index: dict[str, list[int]] | None) -> str:
    """Восстановить abstract из abstract_inverted_index OpenAlex."""
    if not inv_index:
        return ""
    positions: list[tuple[int, str]] = []
    for word, idxs in inv_index.items():
        for i in idxs:
            positions.append((i, word))
    positions.sort(key=lambda t: t[0])
    return " ".join(w for _, w in positions)
# new-style `2401.01234`(+`vN`) или old-style `math/0501001` / `cs.AI/0501001`(+`vN`)
_ARXIV_ID_RE = re.compile(
    r"\A(\d{4}\.\d{4,5}(v\d+)?|[a-z\-]+(\.[A-Z]{2})?/\d{7}(v\d+)?)\Z"
)


@router.get("/arxiv")
async def arxiv_search(
    search_query: str = Query(..., min_length=1, max_length=500),
    max_results: int = Query(20, ge=1, le=MAX_RESULTS_HARD_CAP),
    _ctx: EphemeralTokenContext = Depends(ephemeral_token_auth),
) -> dict[str, Any]:
    """Прокси к export.arxiv.org/api/query?search_query=...

    Принимает простой текстовый запрос. Атом-ответ парсим в JSON.
    Никакого raw passthrough: не даём агенту делать что-то кроме поиска.
    """
    # arXiv API принимает запросы вида all:keyword. Если юзер уже передал
    # field-spec (например `ti:transformer`), сохраним; иначе оборачиваем в all:.
    if not re.match(r"^[a-zA-Z]+:", search_query):
        q = f"all:{search_query}"
    else:
        q = search_query
    url = (
        f"{ARXIV_API}"
        f"?search_query={quote_plus(q)}"
        f"&start=0&max_results={max_results}"
        "&sortBy=relevance&sortOrder=descending"
    )
    try:
        async with httpx.AsyncClient(
            timeout=ARXIV_TIMEOUT_S, follow_redirects=True,
        ) as client:
            r = await client.get(url)
    except httpx.TimeoutException as e:
        raise HTTPException(
            status_code=504,
            detail={"error": {"code": "ARXIV_TIMEOUT", "message": str(e)}},
        ) from e
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=502,
            detail={"error": {"code": "ARXIV_UNAVAILABLE", "message": str(e)}},
        ) from e

    if r.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail={
                "error": {
                    "code": "ARXIV_BAD_STATUS",
                    "message": f"arXiv ответил {r.status_code}",
                }
            },
        )

    feed = feedparser.parse(r.text)
    papers: list[dict[str, Any]] = []
    for entry in feed.entries:
        arxiv_id = entry.get("id", "").rsplit("/", 1)[-1]
        if not arxiv_id:
            continue
        title = re.sub(r"\s+", " ", entry.get("title", "")).strip()
        abstract = re.sub(r"\s+", " ", entry.get("summary", "")).strip()
        authors = [a.get("name", "") for a in entry.get("authors", [])]
        year_match = re.match(r"(\d{4})", entry.get("published", ""))
        year = int(year_match.group(1)) if year_match else None
        papers.append({
            "arxiv_id": arxiv_id,
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "year": year,
            "url": entry.get("link", ""),
            "published": entry.get("published", ""),
        })
    return {
        "search_query": q,
        "total": len(papers),
        "papers": papers,
    }


@router.get("/arxiv-pdf")
async def arxiv_pdf(
    arxiv_id: str = Query(..., min_length=1, max_length=40),
    _ctx: EphemeralTokenContext = Depends(ephemeral_token_auth),
) -> Response:
    """Скачать PDF статьи arXiv через allowlist-прокси.

    Агент в internal-сети без интернета — это единственный способ забрать
    сам файл. Жёстко: только валидный arxiv_id, только arxiv.org/pdf,
    content-type обязан быть PDF, лимит размера.
    """
    aid = arxiv_id.removeprefix("arxiv:").strip()
    if not _ARXIV_ID_RE.match(aid):
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "ARXIV_PDF_BAD_ID",
                              "message": f"невалидный arxiv_id: {arxiv_id!r}"}},
        )
    url = f"{ARXIV_PDF_BASE}/{aid}.pdf"
    too_large = HTTPException(
        status_code=502,
        detail={"error": {"code": "ARXIV_PDF_TOO_LARGE",
                          "message": f"PDF превышает лимит {MAX_PDF_BYTES} байт"}},
    )
    try:
        async with httpx.AsyncClient(
            timeout=ARXIV_PDF_TIMEOUT_S, follow_redirects=True,
        ) as client, client.stream("GET", url) as r:
            if r.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail={"error": {"code": "ARXIV_PDF_BAD_STATUS",
                                      "message": f"arXiv ответил {r.status_code}"}},
                )
            clen = r.headers.get("content-length", "")
            if clen.isdigit() and int(clen) > MAX_PDF_BYTES:
                raise too_large
            ctype = r.headers.get("content-type", "")
            # Стримим с ранним обрывом — не материализуем гигантский ответ в RAM.
            buf = bytearray()
            async for chunk in r.aiter_bytes():
                buf += chunk
                if len(buf) > MAX_PDF_BYTES:
                    raise too_large
            body = bytes(buf)
    except httpx.TimeoutException as e:
        raise HTTPException(
            status_code=504,
            detail={"error": {"code": "ARXIV_PDF_TIMEOUT", "message": str(e)}},
        ) from e
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=502,
            detail={"error": {"code": "ARXIV_PDF_UNAVAILABLE", "message": str(e)}},
        ) from e

    if "application/pdf" not in ctype and not body[:5].startswith(b"%PDF"):
        raise HTTPException(
            status_code=502,
            detail={"error": {"code": "ARXIV_PDF_NOT_PDF",
                              "message": f"ожидался PDF, получен {ctype or 'unknown'}"}},
        )

    safe = re.sub(r"[^A-Za-z0-9._-]", "_", aid)
    return Response(
        content=body,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe}.pdf"'},
    )


@router.get("/crossref")
async def crossref_search(
    query: str = Query(..., min_length=1, max_length=500),
    rows: int = Query(20, ge=1, le=MAX_RESULTS_HARD_CAP),
    _ctx: EphemeralTokenContext = Depends(ephemeral_token_auth),
) -> dict[str, Any]:
    """Прокси к Crossref Works API. Возвращает DOI/citation-rich статьи."""
    params = {"query": query, "rows": rows, "select": "DOI,title,author,issued,container-title,abstract,URL,type,is-referenced-by-count"}
    headers = {"User-Agent": CROSSREF_UA}
    try:
        async with httpx.AsyncClient(timeout=CROSSREF_TIMEOUT_S, follow_redirects=True) as client:
            r = await client.get(CROSSREF_API, params=params, headers=headers)
    except httpx.TimeoutException as e:
        raise HTTPException(
            status_code=504,
            detail={"error": {"code": "CROSSREF_TIMEOUT", "message": str(e)}},
        ) from e
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=502,
            detail={"error": {"code": "CROSSREF_UNAVAILABLE", "message": str(e)}},
        ) from e

    if r.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail={"error": {"code": "CROSSREF_BAD_STATUS", "message": f"Crossref ответил {r.status_code}"}},
        )

    items = (r.json().get("message") or {}).get("items", [])
    works: list[dict[str, Any]] = []
    for item in items:
        title = (item.get("title") or [""])[0]
        if not title:
            continue
        authors = [
            f"{a.get('given', '')} {a.get('family', '')}".strip()
            for a in item.get("author", []) if a.get("family")
        ]
        year = None
        issued = item.get("issued", {}).get("date-parts", [])
        if issued and isinstance(issued[0], list) and issued[0]:
            year = issued[0][0]
        venue = (item.get("container-title") or [""])[0]
        works.append({
            "doi": item.get("DOI"),
            "title": re.sub(r"\s+", " ", title).strip(),
            "abstract": item.get("abstract", ""),  # JATS-XML, не plain text
            "authors": authors,
            "year": year,
            "venue": venue,
            "type": item.get("type"),
            "citation_count": item.get("is-referenced-by-count", 0),
            "url": item.get("URL"),
        })
    return {"query": query, "total": len(works), "works": works}


@router.get("/semantic-scholar")
async def s2_search(
    query: str = Query(..., min_length=1, max_length=500),
    limit: int = Query(20, ge=1, le=MAX_RESULTS_HARD_CAP),
    _ctx: EphemeralTokenContext = Depends(ephemeral_token_auth),
) -> dict[str, Any]:
    """Прокси к Semantic Scholar Graph API. Лучшие abstracts + citation counts."""
    params = {"query": query, "limit": limit, "fields": S2_FIELDS}
    try:
        async with httpx.AsyncClient(timeout=S2_TIMEOUT_S, follow_redirects=True) as client:
            r = await client.get(S2_API, params=params)
    except httpx.TimeoutException as e:
        raise HTTPException(
            status_code=504,
            detail={"error": {"code": "S2_TIMEOUT", "message": str(e)}},
        ) from e
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=502,
            detail={"error": {"code": "S2_UNAVAILABLE", "message": str(e)}},
        ) from e

    if r.status_code == 429:
        raise HTTPException(
            status_code=429,
            detail={"error": {"code": "S2_RATE_LIMITED", "message": "Semantic Scholar rate limit. Подожди минуту."}},
        )
    if r.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail={"error": {"code": "S2_BAD_STATUS", "message": f"Semantic Scholar ответил {r.status_code}"}},
        )

    data = r.json()
    papers: list[dict[str, Any]] = []
    for p in data.get("data", []):
        ext = p.get("externalIds") or {}
        papers.append({
            "paper_id": p.get("paperId"),
            "title": p.get("title", ""),
            "abstract": p.get("abstract") or "",
            "authors": [a.get("name", "") for a in (p.get("authors") or [])],
            "year": p.get("year"),
            "venue": p.get("venue") or "",
            "citation_count": p.get("citationCount", 0),
            "reference_count": p.get("referenceCount", 0),
            "doi": ext.get("DOI"),
            "arxiv_id": ext.get("ArXiv"),
            "url": p.get("url"),
        })
    return {
        "query": query,
        "total": len(papers),
        "papers": papers,
    }


@router.get("/openalex")
async def openalex_search(
    query: str = Query(..., min_length=1, max_length=500),
    per_page: int = Query(20, ge=1, le=MAX_RESULTS_HARD_CAP),
    _ctx: EphemeralTokenContext = Depends(ephemeral_token_auth),
) -> dict[str, Any]:
    """Прокси к OpenAlex Works API. Широкое покрытие + флаг open-access + oa_url."""
    params = {"search": query, "per-page": per_page, "mailto": OPENALEX_MAILTO}
    try:
        async with httpx.AsyncClient(
            timeout=OPENALEX_TIMEOUT_S, follow_redirects=True,
        ) as client:
            r = await client.get(OPENALEX_API, params=params)
    except httpx.TimeoutException as e:
        raise HTTPException(
            status_code=504,
            detail={"error": {"code": "OPENALEX_TIMEOUT", "message": str(e)}},
        ) from e
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=502,
            detail={"error": {"code": "OPENALEX_UNAVAILABLE", "message": str(e)}},
        ) from e

    if r.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail={"error": {"code": "OPENALEX_BAD_STATUS",
                              "message": f"OpenAlex ответил {r.status_code}"}},
        )

    works: list[dict[str, Any]] = []
    for w in r.json().get("results", []):
        title = w.get("display_name") or ""
        if not title:
            continue
        authors = [
            (a.get("author") or {}).get("display_name", "")
            for a in w.get("authorships", [])
        ]
        oa = w.get("open_access") or {}
        doi = (w.get("doi") or "").replace("https://doi.org/", "") or None
        works.append({
            "title": re.sub(r"\s+", " ", title).strip(),
            "abstract": _openalex_abstract(w.get("abstract_inverted_index")),
            "authors": [a for a in authors if a],
            "year": w.get("publication_year"),
            "doi": doi,
            "citation_count": w.get("cited_by_count", 0),
            "venue": ((w.get("primary_location") or {}).get("source") or {}).get(
                "display_name", ""
            ),
            "is_oa": bool(oa.get("is_oa")),
            "oa_url": oa.get("oa_url"),
            "url": oa.get("oa_url") or w.get("id", ""),
        })
    return {"query": query, "total": len(works), "works": works}


@router.get("/cyberleninka")
async def cyberleninka_search(
    query: str = Query(..., min_length=1, max_length=500),
    size: int = Query(20, ge=1, le=MAX_RESULTS_HARD_CAP),
    _ctx: EphemeralTokenContext = Depends(ephemeral_token_auth),
) -> dict[str, Any]:
    """Прокси к CyberLeninka search API — русскоязычные научные статьи.

    Search-ответ уже содержит заголовок, аннотацию, авторов, год и журнал,
    поэтому парсить страницы статей не нужно. PDF открытого доступа берётся
    через /api/sandbox/cyberleninka-pdf по slug.
    """
    body = {"mode": "articles", "size": size, "q": query}
    headers = {"User-Agent": CYBERLENINKA_UA, "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(
            timeout=CYBERLENINKA_TIMEOUT_S, follow_redirects=True,
        ) as client:
            r = await client.post(CYBERLENINKA_API, json=body, headers=headers)
    except httpx.TimeoutException as e:
        raise HTTPException(
            status_code=504,
            detail={"error": {"code": "CYBERLENINKA_TIMEOUT", "message": str(e)}},
        ) from e
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=502,
            detail={"error": {"code": "CYBERLENINKA_UNAVAILABLE", "message": str(e)}},
        ) from e

    if r.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail={"error": {"code": "CYBERLENINKA_BAD_STATUS",
                              "message": f"CyberLeninka ответил {r.status_code}"}},
        )

    articles: list[dict[str, Any]] = []
    for a in r.json().get("articles", []):
        link = a.get("link") or ""
        slug = link.rsplit("/", 1)[-1] if link else ""
        title = _strip_html(a.get("name", ""))
        if not title:
            continue
        year = None
        try:
            year = int(str(a.get("year")).strip()) if a.get("year") else None
        except (ValueError, TypeError):
            year = None
        articles.append({
            "title": title,
            "abstract": _strip_html(a.get("annotation", "")),
            "authors": a.get("authors") or [],
            "year": year,
            "journal": _strip_html(a.get("journal", "")),
            "slug": slug,
            "url": f"{CYBERLENINKA_BASE}{link}" if link else "",
            "pdf_url": f"{CYBERLENINKA_BASE}{link}/pdf" if link else "",
        })
    return {"query": query, "total": len(articles), "articles": articles}


def _is_safe_public_url(url: str) -> bool:
    """https + хост не резолвится в приватный/loopback диапазон (анти-SSRF)."""
    try:
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname:
            return False
        infos = socket.getaddrinfo(parsed.hostname, None)
        for info in infos:
            ip = ipaddress.ip_address(info[4][0])
            if (ip.is_private or ip.is_loopback or ip.is_link_local
                    or ip.is_reserved or ip.is_multicast):
                return False
        return True
    except (socket.gaierror, ValueError):
        return False


async def _download_pdf(url: str, *, code: str, headers: dict[str, str] | None = None) -> bytes:
    """Стримит PDF с лимитом размера и проверкой content-type. Бросает HTTPException."""
    too_large = HTTPException(
        status_code=502,
        detail={"error": {"code": f"{code}_TOO_LARGE",
                          "message": f"PDF превышает лимит {MAX_PDF_BYTES} байт"}},
    )
    try:
        async with httpx.AsyncClient(
            timeout=OA_PDF_TIMEOUT_S, follow_redirects=True,
        ) as client, client.stream("GET", url, headers=headers or {}) as r:
            if r.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail={"error": {"code": f"{code}_BAD_STATUS",
                                      "message": f"источник ответил {r.status_code}"}},
                )
            clen = r.headers.get("content-length", "")
            if clen.isdigit() and int(clen) > MAX_PDF_BYTES:
                raise too_large
            ctype = r.headers.get("content-type", "")
            buf = bytearray()
            async for chunk in r.aiter_bytes():
                buf += chunk
                if len(buf) > MAX_PDF_BYTES:
                    raise too_large
            body = bytes(buf)
    except httpx.TimeoutException as e:
        raise HTTPException(
            status_code=504,
            detail={"error": {"code": f"{code}_TIMEOUT", "message": str(e)}},
        ) from e
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=502,
            detail={"error": {"code": f"{code}_UNAVAILABLE", "message": str(e)}},
        ) from e

    if "application/pdf" not in ctype and not body[:5].startswith(b"%PDF"):
        raise HTTPException(
            status_code=502,
            detail={"error": {"code": f"{code}_NOT_PDF",
                              "message": f"ожидался PDF, получен {ctype or 'unknown'}"}},
        )
    return body


@router.get("/cyberleninka-pdf")
async def cyberleninka_pdf(
    slug: str = Query(..., min_length=3, max_length=200),
    _ctx: EphemeralTokenContext = Depends(ephemeral_token_auth),
) -> Response:
    """Скачать PDF статьи CyberLeninka (открытый доступ) по slug."""
    s = slug.strip().strip("/")
    if not _CL_SLUG_RE.match(s):
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "CYBERLENINKA_PDF_BAD_SLUG",
                              "message": f"невалидный slug: {slug!r}"}},
        )
    url = f"{CYBERLENINKA_BASE}/article/n/{s}/pdf"
    body = await _download_pdf(url, code="CYBERLENINKA_PDF",
                               headers={"User-Agent": CYBERLENINKA_UA})
    return Response(
        content=body,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{s}.pdf"'},
    )


@router.get("/oa-pdf")
async def oa_pdf(
    doi: str = Query(..., min_length=7, max_length=200),
    _ctx: EphemeralTokenContext = Depends(ephemeral_token_auth),
) -> Response:
    """Скачать PDF открытого доступа по DOI через Unpaywall (только легальный OA).

    Unpaywall возвращает только легально открытые версии; качаем именно её URL
    (не произвольный, заданный агентом), с https-проверкой и анти-SSRF-гардом.
    """
    d = doi.strip().removeprefix("https://doi.org/").removeprefix("doi:").strip()
    if not _DOI_RE.match(d):
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "OA_PDF_BAD_DOI", "message": f"невалидный DOI: {doi!r}"}},
        )
    meta_url = f"{UNPAYWALL_API}/{quote_plus(d)}?email={UNPAYWALL_EMAIL}"
    try:
        async with httpx.AsyncClient(timeout=OPENALEX_TIMEOUT_S, follow_redirects=True) as client:
            mr = await client.get(meta_url)
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=502,
            detail={"error": {"code": "OA_PDF_UNPAYWALL_UNAVAILABLE", "message": str(e)}},
        ) from e
    if mr.status_code == 404:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "OA_PDF_NOT_FOUND", "message": "DOI не найден в Unpaywall."}},
        )
    if mr.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail={"error": {"code": "OA_PDF_UNPAYWALL_BAD_STATUS",
                              "message": f"Unpaywall ответил {mr.status_code}"}},
        )
    best = (mr.json() or {}).get("best_oa_location") or {}
    pdf_url = best.get("url_for_pdf")
    if not pdf_url:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "OA_PDF_NO_OA",
                              "message": "Нет открытой PDF-версии (легальный OA отсутствует)."}},
        )
    if not _is_safe_public_url(pdf_url):
        raise HTTPException(
            status_code=502,
            detail={"error": {"code": "OA_PDF_UNSAFE_URL",
                              "message": "OA-ссылка не прошла проверку безопасности."}},
        )
    body = await _download_pdf(pdf_url, code="OA_PDF")
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", d)
    return Response(
        content=body,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe}.pdf"'},
    )
