"""
4get + SearXNG-compatible HTTP gateway.

Can run standalone (python gateway.py) or be started as a daemon thread
from server.py via start_gateway_thread().
"""
import json
import logging
import os
from urllib.parse import urlparse
from typing import Any, Callable, Dict, List, Optional

import httpx
import uvicorn
from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger("gateway")

FOURGET_URL: Optional[str] = None
_internal_search: Optional[Callable] = None  # set by server.py

gateway_app = FastAPI(title="4get+SearXNG Gateway", version="2.0.0")


# ── SearXNG models ──────────────────────────────────────────
class SearXNGResult(BaseModel):
    url: str = ""
    title: str = ""
    content: str = ""
    engine: str = "internal"
    template: str = "default.html"
    parsed_url: List[str] = Field(default_factory=list)
    engines: List[str] = Field(default_factory=list)
    positions: List[int] = Field(default_factory=list)
    score: float = 1.0
    category: str = "general"


class SearXNGResponse(BaseModel):
    query: str
    number_of_results: int = 0
    results: List[SearXNGResult] = Field(default_factory=list)
    answers: List[Any] = Field(default_factory=list)
    corrections: List[Any] = Field(default_factory=list)
    infoboxes: List[Any] = Field(default_factory=list)
    suggestions: List[Any] = Field(default_factory=list)
    unresponsive_engines: List[List[str]] = Field(default_factory=list)


def _parse_url(u: str) -> List[str]:
    try:
        p = urlparse(u)
        return [p.scheme, p.netloc, p.path, p.query, p.fragment]
    except Exception:
        return ["", "", "", "", ""]


def _fourget_to_searxng(raw: Dict[str, Any], original_query: str) -> SearXNGResponse:
    results = []
    items = raw.get("web", [])[:20]
    for i, item in enumerate(items, 1):
        results.append(SearXNGResult(
            url=item.get("url", ""),
            title=item.get("title", ""),
            content=item.get("description", ""),
            parsed_url=_parse_url(item.get("url", "")),
            positions=[i],
            category="general",
        ))
    return SearXNGResponse(
        query=original_query,
        number_of_results=len(results),
        results=results,
    )


async def _do_search(query: str) -> Dict[str, Any]:
    if _internal_search is None:
        return {"status": "error", "web": [], "message": "Search backend not ready"}
    raw = await _internal_search(query=query, type="web", limit=20)
    return json.loads(raw)


# ── Routes ──────────────────────────────────────────────────
@gateway_app.get("/healthz")
async def health():
    return {"status": "ok"}


@gateway_app.get("/search")
async def searxng_search(
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
        data = await _do_search(q)
    except Exception as e:
        logger.error("search failed: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})
    return _fourget_to_searxng(data, q).model_dump()


@gateway_app.get("/api/v1/search")
async def fourget_search(
    request: Request,
    s: str = Query(..., alias="s"),
    scraper: Optional[str] = Query(None),
    nsfw: bool = Query(False),
    npt: Optional[str] = Query(None),
):
    try:
        data = await _do_search(s)
    except Exception as e:
        logger.error("search failed: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})
    return {
        "status": "ok",
        "web": data.get("web", data.get("results", [])),
        "npt": data.get("npt"),
    }


# ── Standalone entry point ──────────────────────────────────
def start_gateway_thread(search_fn: Callable):
    """Start the gateway as a daemon thread. Called by server.py."""
    _globals = globals()
    _globals["_internal_search"] = search_fn

    def _run():
        bind = os.getenv("GATEWAY_BIND", "0.0.0.0:8080")
        host, port = bind.split(":")
        logger.info("Gateway on %s:%s", host, port)
        uvicorn.run(gateway_app, host=host, port=int(port), log_level="warning", access_log=False)

    import threading
    t = threading.Thread(target=_run, daemon=True, name="gateway")
    t.start()
    return t


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bind = os.getenv("GATEWAY_BIND", "0.0.0.0:8080")
    host, port = bind.split(":")
    logger.info("Gateway standalone on %s:%s", host, port)
    uvicorn.run(gateway_app, host=host, port=int(port), log_level="info")