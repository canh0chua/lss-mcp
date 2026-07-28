"""Lightweight search API using CRW/LightPanda.

Provides a FastAPI application exposing both SearXNG-compatible and direct API endpoints.
"""

import logging
from urllib.parse import urlparse
import httpx
from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

logger = logging.getLogger("searchapi")

app = FastAPI(title="Search API", version="1.0.0")

# Import local CRW-based scrapers
try:
    from lib.search import get_scraper
except ImportError as e:
    logger.warning("Search scrapers not available: %s", e)
    get_scraper = None

class SearchResult(BaseModel):
    url: str
    title: str
    content: str
    engine: str = "crw"
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

def format_searxng_response(search_data: Dict[str, Any], query: str) -> SearchResponse:
    results = []
    raw_results = search_data.get("web", [])[:20]
    for i, item in enumerate(raw_results, 1):
        url = item.get("url", "")
        title = item.get("title", "")
        snippet = item.get("description", "")
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

@app.get("/healthz")
async def health():
    return {"status": "ok"}

@app.get("/api/v1/web")
async def api_web(
    s: str = Query(..., alias="s"),
    scraper: str = Query("brave", alias="scraper"),
    nsfw: bool = Query(False, alias="nsfw"),
    country: str = Query("", alias="country"),
    lang: str = Query("", alias="lang"),
    time_min: int = Query(0, alias="time_min"),
    time_max: int = Query(0, alias="time_max"),
    npt: str = Query("", alias="npt"),
):
    logger.info("Search request: engine=%s, query=%s, nsfw=%s, country=%s, lang=%s", 
                scraper, s, nsfw, country, lang)
    if get_scraper is None:
        logger.error("Search failed: scrapers not available")
        return JSONResponse(
            status_code=503,
            content={"status": "error", "message": "Search scrapers not available"},
        )
    try:
        scraper_cls = get_scraper(scraper)
        instance = scraper_cls()
        result = await instance.search(s)
        result_count = len(result.get("web", []))
        logger.info("Search completed: engine=%s, query=%s, results=%d", 
                    scraper, s, result_count)
        return result
    except ValueError as e:
        logger.warning("Search validation error: %s", str(e))
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": str(e)},
        )
    except Exception as e:
        logger.error("Search failed: %s", e, exc_info=True)
        return JSONResponse(
            status_code=502,
            content={"status": "error", "message": f"Search failed: {str(e)}"},
        )

@app.get("/api/v1/images")
async def api_images(
    s: str = Query(..., alias="s"),
    scraper: str = Query("brave", alias="scraper"),
    nsfw: bool = Query(False, alias="nsfw"),
    country: str = Query("", alias="country"),
    lang: str = Query("", alias="lang"),
    time_min: int = Query(0, alias="time_min"),
    time_max: int = Query(0, alias="time_max"),
    npt: str = Query("", alias="npt"),
):
    if get_scraper is None:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "message": "Search scrapers not available"},
        )
    try:
        scraper_cls = get_scraper(scraper)
        instance = scraper_cls()
        result = await instance.search(s)
        return result
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": str(e)},
        )
    except Exception as e:
        logger.error("Image search failed: %s", e, exc_info=True)
        return JSONResponse(
            status_code=502,
            content={"status": "error", "message": f"Image search failed: {str(e)}"},
        )

@app.get("/api/v1/videos")
async def api_videos(
    s: str = Query(..., alias="s"),
    scraper: str = Query("brave", alias="scraper"),
    nsfw: bool = Query(False, alias="nsfw"),
    country: str = Query("", alias="country"),
    lang: str = Query("", alias="lang"),
    time_min: int = Query(0, alias="time_min"),
    time_max: int = Query(0, alias="time_max"),
    npt: str = Query("", alias="npt"),
):
    if get_scraper is None:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "message": "Search scrapers not available"},
        )
    try:
        scraper_cls = get_scraper(scraper)
        instance = scraper_cls()
        result = await instance.search(s)
        return result
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": str(e)},
        )
    except Exception as e:
        logger.error("Video search failed: %s", e, exc_info=True)
        return JSONResponse(
            status_code=502,
            content={"status": "error", "message": f"Video search failed: {str(e)}"},
        )

@app.get("/api/v1/news")
async def api_news(
    s: str = Query(..., alias="s"),
    scraper: str = Query("brave", alias="scraper"),
    nsfw: bool = Query(False, alias="nsfw"),
    country: str = Query("", alias="country"),
    lang: str = Query("", alias="lang"),
    time_min: int = Query(0, alias="time_min"),
    time_max: int = Query(0, alias="time_max"),
    npt: str = Query("", alias="npt"),
):
    if get_scraper is None:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "message": "Search scrapers not available"},
        )
    try:
        scraper_cls = get_scraper(scraper)
        instance = scraper_cls()
        result = await instance.search(s)
        return result
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": str(e)},
        )
    except Exception as e:
        logger.error("News search failed: %s", e, exc_info=True)
        return JSONResponse(
            status_code=502,
            content={"status": "error", "message": f"News search failed: {str(e)}"},
        )

@app.get("/api/v1/music")
async def api_music(
    s: str = Query(..., alias="s"),
    scraper: str = Query("brave", alias="scraper"),
    nsfw: bool = Query(False, alias="nsfw"),
    country: str = Query("", alias="country"),
    lang: str = Query("", alias="lang"),
    time_min: int = Query(0, alias="time_min"),
    time_max: int = Query(0, alias="time_max"),
    npt: str = Query("", alias="npt"),
):
    if get_scraper is None:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "message": "Search scrapers not available"},
        )
    try:
        scraper_cls = get_scraper(scraper)
        instance = scraper_cls()
        result = await instance.search(s)
        return result
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": str(e)},
        )
    except Exception as e:
        logger.error("Music search failed: %s", e, exc_info=True)
        return JSONResponse(
            status_code=502,
            content={"status": "error", "message": f"Music search failed: {str(e)}"},
        )

@app.get("/search")
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
    scraper_name = engine or "brave"
    try:
        scraper_cls = get_scraper(scraper_name)
        instance = scraper_cls()
        search_data = await instance.search(q)
        searxng_resp = format_searxng_response(search_data, q)
        return searxng_resp.model_dump()
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)},
        )
    except Exception as e:
        logger.error("Search failed: %s", e, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": f"Internal server error: {str(e)}"},
        )

@app.get("/autocomplete")
async def autocomplete(q: str = Query(..., alias="q")):
    return {"suggestions": []}