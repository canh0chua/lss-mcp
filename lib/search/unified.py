"""Unified search orchestrator - merges results from multiple backends."""
import asyncio
import random
import logging
import re
from typing import Dict, Any, List
from urllib.parse import urlparse

from .scrapers import (
    BraveScraper,
    DuckDuckGoScraper,
    YahooScraper,
    WikipediaScraper,
    _empty_result,
)

logger = logging.getLogger(__name__)

# Source priority weights for ranking (higher = better)
SOURCE_WEIGHTS = {
    "brave": 1.0,
    "duckduckgo": 0.95,
    "yahoo": 0.85,
    "wikipedia": 0.7,
}

# Domain authority scores (simplified)
DOMAIN_AUTHORITY = {
    "wikipedia.org": 0.95,
    "github.com": 0.9,
    "stackoverflow.com": 0.9,
    "reddit.com": 0.8,
    "youtube.com": 0.85,
    "medium.com": 0.8,
    "dev.to": 0.75,
    "docs.python.org": 0.9,
    "realpython.com": 0.85,
}


def _normalize_url(url: str) -> str:
    """Normalize URL for deduplication."""
    url = url.strip().rstrip('/')
    # Remove tracking params
    parsed = urlparse(url)
    clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    return clean.lower()


def _score_result(item: dict, source: str) -> float:
    """Score a result for ranking."""
    score = SOURCE_WEIGHTS.get(source, 0.5)

    # Domain authority boost
    try:
        domain = urlparse(item.get("url", "")).netloc.replace("www.", "")
        for key, val in DOMAIN_AUTHORITY.items():
            if domain.endswith(key):
                score *= (1 + val * 0.3)
                break
    except Exception:
        pass

    # Snippet presence boost
    if item.get("description"):
        score *= 1.1

    # Title quality boost (longer, more descriptive = better)
    title = item.get("title", "")
    if len(title) > 20:
        score *= 1.05

    return score


async def unified_search(query: str, limit: int = 20) -> Dict[str, Any]:
    """
    Run Brave + DuckDuckGo + Yahoo + Wikipedia in parallel.
    Merge, deduplicate, rank, and return combined results.
    """
    engines = [
        ("brave", BraveScraper()),
        ("duckduckgo", DuckDuckGoScraper()),
        ("yahoo", YahooScraper()),
        ("wikipedia", WikipediaScraper()),
    ]

    # Run all in parallel
    tasks = {name: asyncio.create_task(scraper.search(query)) for name, scraper in engines}

    merged = []
    engine_results = {}

    # Wait for all tasks with a timeout (e.g., 20 seconds)
    for name, task in tasks.items():
        try:
            result = await asyncio.wait_for(task, timeout=20)
            web = result.get("web", [])
            engine_results[name] = len(web)
            for item in web:
                merged.append({**item, "_source": name})
            logger.info(f"unified: {name} returned {len(web)} results")
        except asyncio.TimeoutError:
            logger.warning(f"unified: {name} timed out")
            engine_results[name] = 0
        except Exception as e:
            logger.warning(f"unified: {name} failed: {e}")
            engine_results[name] = 0

    # Deduplicate by normalized URL
    seen = set()
    deduped = []
    for item in merged:
        norm = _normalize_url(item.get("url", ""))
        if norm not in seen:
            seen.add(norm)
            deduped.append(item)

    # Score and rank
    for item in deduped:
        item["_score"] = _score_result(item, item.pop("_source", "unknown"))

    deduped.sort(key=lambda x: -x.get("_score", 0))

    # Clean output (remove internal fields)
    clean = []
    for item in deduped[:limit]:
        clean.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "description": item.get("description", item.get("snippet", "")),
        })

    out = _empty_result()
    out["web"] = clean
    return out