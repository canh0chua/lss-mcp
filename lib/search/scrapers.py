"""4get-compatible search scrapers using CRW."""

import logging
import httpx
import os
import re
from typing import Dict, Any, List, Optional

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    BeautifulSoup = None  # Type hint fallback

try:
    from lxml import html as lxml_html
    LXML_AVAILABLE = True
except ImportError:
    LXML_AVAILABLE = False
    lxml_html = None  # Type hint fallback

logger = logging.getLogger(__name__)

CRW_URL = os.getenv("CRW_URL", "http://crw:3000")


def _empty_result() -> Dict[str, Any]:
    return {
        "status": "ok",
        "spelling": {"type": "no_correction", "using": None, "correction": None},
        "npt": None,
        "answer": [],
        "web": [],
        "image": [],
        "video": [],
        "news": [],
        "related": [],
    }


async def _crw_scrape(
    url: str,
    js: bool = True,
    return_format: str = "markdown",
    headers: Optional[Dict[str, str]] = None,
    cookies: Optional[List[str]] = None,
) -> str:
    """Fetch page via CRW and return content in specified format."""
    async with httpx.AsyncClient(timeout=30) as client:
        payload = {
            "url": url,
            "formats": [return_format],
            "waitFor": 2 if js else 0,
        }
        if headers:
            payload["headers"] = headers
        if cookies:
            payload["cookies"] = cookies

        resp = await client.post(
            f"{CRW_URL}/v1/scrape",
            json=payload,
            headers={"User-Agent": "Mozilla/5.0 (compatible; 4get-replacement/1.0)"},
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            raise Exception(data.get("error", "CRW scrape failed"))
        return data["data"][return_format]


# -- Working scrapers ------------------------------------------------------
class BraveScraper:
    async def search(self, query: str, **kwargs) -> Dict[str, Any]:
        url = f"https://search.brave.com/search?q={query}"
        md = await _crw_scrape(url, js=True)
        out = _empty_result()
        results = []
        seen_urls = set()
        lines = md.split("\n")

        for i, line in enumerate(lines):
            line = line.strip()
            # Match [Title](url) markdown links
            m = re.search(r'\[([^\]]+)\]\(([^)]+)\)', line)
            if not m:
                continue
            title = m.group(1).strip()
            link = m.group(2).strip()
            if not title or link.startswith("/") or any(x in link for x in ["search.brave.com", "brave.com", "/search?", "/videos?", "/news?", "/images?"]):
                continue
            # Normalize URL for deduplication
            norm_link = link.lower().rstrip("/")
            if not link or norm_link in seen_urls:
                continue
            seen_urls.add(norm_link)
            desc = ""
            # Look ahead for a description line
            for j in range(i + 1, min(i + 6, len(lines))):
                nxt = lines[j].strip()
                if not nxt:
                    continue
                if nxt.startswith("[") or nxt.startswith("![") or nxt == "* * *":
                    continue
                if " > " in nxt:
                    continue
                desc = nxt[:200]
                break
            results.append({"title": title, "url": link, "description": desc})

        out["web"] = results[:20]
        return out


class DuckDuckGoScraper:
    async def search(self, query: str, **kwargs) -> Dict[str, Any]:
        url = f"https://duckduckgo.com/html/?q={query}"
        md = await _crw_scrape(url, js=True)
        out = _empty_result()
        results = []
        seen_urls = set()
        lines = md.split("\n")

        for i, line in enumerate(lines):
            line = line.strip()
            # Match the title line: ## [Title](//duckduckgo.com/l/?uddg=...)
            m = re.search(r'^##?\s*\[([^\]]+)\]\(//duckduckgo\.com/l/\?uddg=([^)]+)', line)
            if not m:
                continue
            title = m.group(1).strip()
            # Extract the actual URL from the uddg parameter
            from urllib.parse import unquote
            param_string = m.group(2)
            if '&' in param_string:
                param_string = param_string.split('&')[0]
            try:
                link = unquote(param_string)
            except Exception:
                link = param_string
            if 'duckduckgo.com' in link:
                continue
            norm_link = link.lower().rstrip("/")
            if not link or norm_link in seen_urls:
                continue
            seen_urls.add(norm_link)
            desc = ""
            for offset in range(1, 3):
                if i + offset < len(lines):
                    cand = lines[i + offset].strip()
                    if not cand.startswith('![') and cand.startswith('[') and '://' in cand:
                        inner_match = re.match(r'\[([^\]]+)\]\([^)]+\)', cand)
                        if inner_match:
                            desc = inner_match.group(1).strip()
                            desc = re.sub(r'\*\*(.*?)\*\*', r'\1', desc)
                            break
            results.append({
                "title": title,
                "url": link,
                "description": desc
            })

        out["web"] = results[:20]
        return out


class MojeekScraper:
    async def search(self, query: str, **kwargs) -> Dict[str, Any]:
        url = f"https://www.mojeek.com/search?q={query}"
        md = await _crw_scrape(url, js=False)
        out = _empty_result()
        results = []
        for line in md.split("\n"):
            line = line.strip()
            m = re.search(r'\[([^\]]+)\]\(([^)]+)\)', line)
            if not m:
                continue
            title = m.group(1).strip()
            link = m.group(2).strip()
            if not title or link.startswith("/") or "mojeek.com" in link:
                continue
            results.append({"title": title, "url": link, "description": ""})
        out["web"] = results[:20]
        return out


class YahooScraper:
    async def search(self, query: str, **kwargs) -> Dict[str, Any]:
        url = f"https://search.yahoo.com/search?p={query}"
        md = await _crw_scrape(url, js=True)
        out = _empty_result()
        results = []
        seen_urls: set = set()
        lines = md.split("\n")

        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # Yahoo js=True format: titles appear as ### Title](URL)
            m = re.match(r'^#{1,4}\s+([^\]]+)\]\(([^)]+)\)', line_stripped)
            if not m:
                continue

            title = m.group(1).strip()
            link = m.group(2).strip()

            if not title or link.startswith("/") or "yahoo.com" in link:
                continue

            norm_link = link.lower().rstrip("/")
            if norm_link in seen_urls:
                continue
            seen_urls.add(norm_link)

            desc = ""
            for j in range(i + 1, min(i + 6, len(lines))):
                nxt = lines[j].strip()
                if not nxt:
                    continue
                if re.match(r'^\*\s*\[', nxt):
                    continue
                if nxt == "*":
                    continue
                if nxt.startswith("!["):
                    continue
                desc = re.sub(r'\*\*([^*]+)\*\*', r'\1', nxt)[:200]
                break

            results.append({"title": title, "url": link, "description": desc})

        out["web"] = results[:20]
        return out


class WikipediaScraper:
    async def search(self, query: str, **kwargs) -> Dict[str, Any]:
        out = _empty_result()
        results = []
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://en.wikipedia.org/w/api.php",
                    params={
                        "action": "query",
                        "list": "search",
                        "srsearch": query,
                        "srlimit": 10,
                        "format": "json",
                    },
                    headers={"User-Agent": "LSS-MCP/1.0 (search aggregator)"},
                )
                data = resp.json()
                for item in data.get("query", {}).get("search", []):
                    title = item.get("title", "")
                    page_url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
                    snippet = re.sub(r'<[^>]+>', '', item.get("snippet", ""))
                    results.append({"title": title, "url": page_url, "description": snippet})
        except Exception as e:
            logger.error(f"Wikipedia search failed: {e}")
        out["web"] = results[:10]
        return out
