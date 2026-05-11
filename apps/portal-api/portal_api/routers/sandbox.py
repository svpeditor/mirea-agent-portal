"""Sandbox-прокси для агентов: arXiv + (заготовка) другие источники.

Агенты сидят в portal-agents-net (internal=true) и не имеют прямого доступа
к публичному интернету. Этот роутер — единственный legal egress endpoint
для них. Аутентификация: ephemeral bearer token (как у LLM proxy).
Allowlist жёсткий: только arXiv API.
"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote_plus

import feedparser  # type: ignore[import-untyped]
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

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
