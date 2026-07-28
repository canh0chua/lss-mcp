"""ScraperBase class and CRW client implementation.

This module provides a base class for web scraping backends and a
CRW (Firecrawl-compatible) client implementation.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
import json
import urllib.request
import urllib.error
import urllib.parse

logger = logging.getLogger(__name__)


@dataclass
class ScrapeResult:
    """Standardized result from a scrape operation."""
    url: str
    success: bool
    content: Optional[str] = None
    html: Optional[str] = None
    markdown: Optional[str] = None
    links: Optional[List[str]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ScraperBase(ABC):
    """
    Abstract base class for web scraping backends.
    
    All scraper implementations should inherit from this class and
    implement the required abstract methods.
    """
    
    @abstractmethod
    def scrape(self, url: str, formats: Optional[List[str]] = None) -> ScrapeResult:
        """
        Scrape a single URL and return the content.
        
        Args:
            url: The URL to scrape
            formats: List of desired formats (e.g., ['markdown', 'html', 'links'])
                    If None, defaults to ['markdown']
        
        Returns:
            ScrapeResult containing the requested content
        """
        pass
    
    @abstractmethod
    def search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """
        Perform a web search (if supported by the backend).
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            
        Returns:
            Dictionary with search results
        """
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if the scraper service is available and healthy.
        
        Returns:
            True if the service is healthy, False otherwise
        """
        pass
    
    def close(self) -> None:
        """
        Clean up resources. Override if needed.
        """
        pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class CRWClient(ScraperBase):
    """
    CRW (Firecrawl-compatible) client.
    
    Connects to a CRW service running at a specified base URL.
    Implements the Firecrawl API v1 specification.
    """
    
    def __init__(self, base_url: str = "http://localhost:3002", timeout: int = 30):
        """
        Initialize the CRW client.
        
        Args:
            base_url: Base URL of the CRW service (default: http://localhost:3002)
            timeout: Request timeout in seconds (default: 30)
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
    
    def _request(self, method: str, path: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make an HTTP request to the CRW service."""
        url = f"{self.base_url}{path}"
        headers = {'Content-Type': 'application/json'}
        
        logger.debug("CRW request: %s %s", method, path)
        if data:
            logger.debug("CRW request payload: %s", data)
        
        try:
            req_data = json.dumps(data).encode('utf-8') if data else None
            req = urllib.request.Request(
                url,
                data=req_data,
                headers=headers,
                method=method
            )
            
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                content = resp.read().decode('utf-8')
                result = json.loads(content)
                logger.debug("CRW response: %s", result)
                return result
                
        except urllib.error.HTTPError as e:
            err_msg = f"HTTP {e.code}"
            try:
                err_data = json.loads(e.read().decode('utf-8'))
                err_msg = err_data.get("error", err_msg)
            except:
                pass
            logger.warning("CRW HTTP error: %s %s - %s", method, path, err_msg)
            return {"success": False, "error": err_msg}
        except urllib.error.URLError as e:
            logger.warning("CRW URL error: %s %s - %s", method, path, str(e))
            return {"success": False, "error": f"URL error: {str(e)}"}
        except json.JSONDecodeError as e:
            logger.warning("CRW JSON decode error: %s", str(e))
            return {"success": False, "error": "Invalid JSON response"}
        except Exception as e:
            logger.warning("CRW request failed: %s %s - %s", method, path, str(e))
            return {"success": False, "error": f"Request failed: {str(e)}"}
    
    def health_check(self) -> bool:
        """Check if the CRW service is healthy."""
        try:
            resp = self._request("GET", "/health")
            return resp.get("status") == "ok"
        except Exception:
            return False
    
    def scrape(self, url: str, formats: Optional[List[str]] = None) -> ScrapeResult:
        """
        Scrape a URL using the CRW /v1/scrape endpoint.
        
        Args:
            url: The URL to scrape
            formats: List of formats (default: ['markdown'])
            
        Returns:
            ScrapeResult with the scraped content
        """
        if formats is None:
            formats = ["markdown"]
        
        payload = {
            "url": url,
            "formats": formats
        }
        
        resp = self._request("POST", "/v1/scrape", data=payload)
        
        if not resp.get("success", False):
            return ScrapeResult(
                url=url,
                success=False,
                error=resp.get("error", "Unknown error from CRW service")
            )
        
        # Extract data from the response
        scraped_data = resp.get("data", {})
        result = ScrapeResult(
            url=url,
            success=True,
            metadata=resp.get("metadata", {})
        )
        
        # Map the formats to result fields
        if "markdown" in scraped_data:
            result.markdown = scraped_data["markdown"]
        if "html" in scraped_data:
            result.html = scraped_data["html"]
        if "links" in scraped_data:
            result.links = scraped_data["links"]
        
        # Set content to markdown if available, otherwise html
        result.content = result.markdown or result.html
        
        return result
    
    def search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """
        Perform a web search via CRW /v1/search endpoint.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            Dictionary with search results or error information
        """
        payload = {
            "query": query,
            "limit": limit
        }
        
        return self._request("POST", "/v1/search", data=payload)
    
    def crawl(self, url: str, limit: int = 10) -> Dict[str, Any]:
        """
        Start a crawl job via CRW /v1/crawl endpoint.
        
        Args:
            url: Starting URL for the crawl
            limit: Maximum number of pages to crawl
            
        Returns:
            Dictionary with crawl job information
        """
        payload = {
            "url": url,
            "limit": limit
        }
        
        return self._request("POST", "/v1/crawl", data=payload)
    
    def close(self) -> None:
        """
        Clean up resources. For CRWClient with urllib, no explicit cleanup needed.
        """
        pass


# Registry integration
ENGINES = {}

def register_scraper(name: str, scraper_class: type) -> None:
    """
    Register a scraper class in the global ENGINES dictionary.
    
    Args:
        name: Name to register the scraper under
        scraper_class: ScraperBase subclass
    """
    if not issubclass(scraper_class, ScraperBase):
        raise TypeError(f"{scraper_class} must inherit from ScraperBase")
    ENGINES[name] = scraper_class

# Auto-register CRW client
register_scraper("crw", CRWClient)
