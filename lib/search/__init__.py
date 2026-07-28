"""4get-compatible search scrapers using CRW."""

from .scrapers import (
    BraveScraper,
    DuckDuckGoScraper,
    YahooScraper,
    WikipediaScraper,
)
from .unified import unified_search

ENGINES = {
    "brave": BraveScraper,
    "ddg": DuckDuckGoScraper,
    "duckduckgo": DuckDuckGoScraper,
    "yahoo": YahooScraper,
    "wikipedia": WikipediaScraper,
}

def get_scraper(engine_name: str):
    """Get a scraper class by engine name."""
    scraper = ENGINES.get(engine_name)
    if scraper is None:
        raise ValueError(f"Unknown search engine: {engine_name}")
    return scraper

__all__ = [
    "BraveScraper",
    "DuckDuckGoScraper",
    "YahooScraper",
    "WikipediaScraper",
    "get_scraper",
    "unified_search",
]
