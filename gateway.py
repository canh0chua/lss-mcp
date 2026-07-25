"""
SearXNG-compatible Gateway for 4get (embedded in MCP server container)

Exposes a SearXNG-compatible API on port 8080 and translates requests to the
4get API. CRW and other clients that expect SearXNG connect here seamlessly.

Why this exists instead of running SearXNG:
- ~20MB image vs ~200MB+ SearXNG container
- No upstream engine CAPTCHAs or blocked requests (4get handles that upstream)
- 4get is already deployed and maintained in this stack
- Single container to manage instead of two

Started by server.py via start_gateway_thread().
"""

import logging
from urllib.parse import urlparse
import httpx
from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

logger = logging.getLogger("gateway")

FOURGET_URL = None  # Set at startup from env
gateway_app = FastAPI(title="SearXNG-to-4get Gateway", version="1.0.0")


class SearchResult(BaseModel):
    url: str
    title: str
    content: str
    engine: str = "4get"
    template: str = "default.html"
    parsed_url: List[str] = Field(default_factory=list)
    engines: List[str] = Field(default_factory=list)
    positions: List[int] = Field(default_factory=list)
    score: float = 1.0
    category: str = "general"


class SearchResponse(BaseModel):
    query: str
    number_of_results: int = 0
    results: List[SearchResult] = Field(default_factory=list)
    answers: List[Any] = Field(default_factory=list)
    corrections: List[Any] = Field(default_factory=list)
    infoboxes: List[Any] = Field(default_factory=list)
    suggestions: List[Any] = Field(default_factory=list)
    unresponsive_engines: List[List[str]] = Field(default_factory=list)


def parse_url(url: str) -> List[str]:
    try:
        parsed = urlparse(url)
        return [parsed.scheme, parsed.netloc, parsed.path, parsed.query, parsed.fragment]
    except Exception:
        return ["", "", "", "", ""]


def fourget_to_searxng(fourget_data: Dict[str, Any], query: str) -> SearchResponse:
    results = []
    raw_results = fourget_data.get("web", [])[:20]  # 4get uses "web" key

    for i, item in enumerate(raw_results, 1):
        url = item.get("url", "")
        title = item.get("title", "")
        snippet = item.get("description", "")  # 4get uses "description"

        result = SearchResult(
            url=url,
            title=title,
            content=snippet,
            parsed_url=parse_url(url),
            positions=[i],
            category="general",
        )
        results.append(result)

    return SearchResponse(
        query=query,
        number_of_results=len(results),
        results=results,
    )


@gateway_app.get("/healthz")
async def health():
    return {"status": "ok"}


@gateway_app.get("/search")
async def search(
    request: Request,
    q: str = Query(..., alias="q"),
    format: str = Query("json", alias="format"),
    pageno: int = Query(1, alias="pageno"),
    categories: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    time_range: Optional[str] = Query(None),
    engine: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    sortby: Optional[str] = Query(None),
):
    try:
        params = {"s": q}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{FOURGET_URL}/api/v1/web", params=params)
            if resp.status_code != 200:
                logger.error("4get returned %d: %s", resp.status_code, resp.text)
                return JSONResponse(
                    status_code=502,
                    content={"error": f"Backend search failed with status {resp.status_code}"},
                )

            fourget_data = resp.json()
            if fourget_data.get("status") != "ok":
                logger.error("4get returned error status: %s", fourget_data.get("status"))
                return JSONResponse(
                    status_code=502,
                    content={"error": f"Backend search failed: {fourget_data.get('status')}"},
                )

            searxng_resp = fourget_to_searxng(fourget_data, q)
            return searxng_resp.model_dump()

    except httpx.RequestError as e:
        logger.error("HTTP error connecting to 4get: %s", e)
        return JSONResponse(
            status_code=502,
            content={"error": f"Cannot connect to search backend: {str(e)}"},
        )
    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": f"Internal server error: {str(e)}"},
        )


@gateway_app.get("/autocomplete")
async def autocomplete(q: str = Query(..., alias="q")):
    return {"suggestions": []}
