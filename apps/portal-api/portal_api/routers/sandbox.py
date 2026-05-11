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
