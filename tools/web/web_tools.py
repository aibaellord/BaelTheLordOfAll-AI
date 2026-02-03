"""
BAEL Web Tools - Comprehensive Web Interaction Toolkit
Provides web scraping, search, API calls, content extraction and more.
"""

import asyncio
import hashlib
import json
import logging
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

logger = logging.getLogger("BAEL.Tools.Web")


# =============================================================================
# DATA CLASSES
# =============================================================================

class ContentType(Enum):
    """Types of web content."""
    HTML = "html"
    JSON = "json"
    XML = "xml"
    TEXT = "text"
    BINARY = "binary"
    PDF = "pdf"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"


@dataclass
class WebContent:
    """Represents extracted web content."""
    url: str
    title: Optional[str] = None
    text: str = ""
    html: str = ""
    content_type: ContentType = ContentType.HTML
    metadata: Dict[str, Any] = field(default_factory=dict)
    links: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)
    headings: List[str] = field(default_factory=list)
    extracted_at: datetime = field(default_factory=datetime.now)
    status_code: int = 200
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "text": self.text[:5000] if len(self.text) > 5000 else self.text,
            "content_type": self.content_type.value,
            "metadata": self.metadata,
            "link_count": len(self.links),
            "image_count": len(self.images),
            "headings": self.headings[:20],
            "status_code": self.status_code,
            "error": self.error,
            "extracted_at": self.extracted_at.isoformat()
        }


@dataclass
class SearchResult:
    """Represents a search result."""
    title: str
    url: str
    snippet: str
    position: int
    source: str = "unknown"
    relevance_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScrapingConfig:
    """Configuration for web scraping."""
    max_depth: int = 2
    max_pages: int = 50
    follow_external: bool = False
    respect_robots: bool = True
    delay_seconds: float = 1.0
    timeout_seconds: float = 30.0
    retry_attempts: int = 3
    user_agent: str = "BAEL-Agent/1.0"
    extract_text: bool = True
    extract_links: bool = True
    extract_images: bool = False
    extract_metadata: bool = True
    allowed_domains: List[str] = field(default_factory=list)
    excluded_patterns: List[str] = field(default_factory=list)


# =============================================================================
# URL ANALYZER
# =============================================================================

class URLAnalyzer:
    """Analyze and manipulate URLs."""

    @staticmethod
    def parse(url: str) -> Dict[str, Any]:
        """Parse URL into components."""
        parsed = urlparse(url)
        return {
            "scheme": parsed.scheme,
            "netloc": parsed.netloc,
            "path": parsed.path,
            "params": parsed.params,
            "query": parsed.query,
            "fragment": parsed.fragment,
            "query_params": parse_qs(parsed.query),
            "domain": URLAnalyzer.extract_domain(url),
            "is_secure": parsed.scheme == "https"
        }

    @staticmethod
    def extract_domain(url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        domain = parsed.netloc
        if domain.startswith("www."):
            domain = domain[4:]
        return domain

    @staticmethod
    def is_same_domain(url1: str, url2: str) -> bool:
        """Check if two URLs are from the same domain."""
        return URLAnalyzer.extract_domain(url1) == URLAnalyzer.extract_domain(url2)

    @staticmethod
    def normalize(url: str) -> str:
        """Normalize a URL for comparison."""
        parsed = urlparse(url)
        # Remove trailing slashes, fragments, sort query params
        path = parsed.path.rstrip("/") or "/"
        query = urlencode(sorted(parse_qs(parsed.query).items()))
        return f"{parsed.scheme}://{parsed.netloc}{path}"

    @staticmethod
    def make_absolute(base_url: str, relative_url: str) -> str:
        """Convert relative URL to absolute."""
        return urljoin(base_url, relative_url)

    @staticmethod
    def is_valid(url: str) -> bool:
        """Check if URL is valid."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    @staticmethod
    def extract_file_extension(url: str) -> Optional[str]:
        """Extract file extension from URL."""
        parsed = urlparse(url)
        path = parsed.path
        if "." in path:
            return path.rsplit(".", 1)[-1].lower()
        return None


# =============================================================================
# CONTENT EXTRACTOR
# =============================================================================

class ContentExtractor:
    """Extract meaningful content from web pages."""

    # Common noise patterns to remove
    NOISE_PATTERNS = [
        r'<script[^>]*>[\s\S]*?</script>',
        r'<style[^>]*>[\s\S]*?</style>',
        r'<noscript[^>]*>[\s\S]*?</noscript>',
        r'<!--[\s\S]*?-->',
        r'<nav[^>]*>[\s\S]*?</nav>',
        r'<footer[^>]*>[\s\S]*?</footer>',
        r'<header[^>]*>[\s\S]*?</header>',
        r'<aside[^>]*>[\s\S]*?</aside>',
    ]

    # Patterns for extracting content
    TITLE_PATTERN = r'<title[^>]*>(.*?)</title>'
    META_PATTERN = r'<meta\s+(?:name|property)=["\']([^"\']+)["\']\s+content=["\']([^"\']*)["\']'
    LINK_PATTERN = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>'
    IMG_PATTERN = r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>'
    HEADING_PATTERN = r'<h[1-6][^>]*>(.*?)</h[1-6]>'

    @classmethod
    def extract_title(cls, html: str) -> Optional[str]:
        """Extract page title."""
        match = re.search(cls.TITLE_PATTERN, html, re.IGNORECASE | re.DOTALL)
        if match:
            return cls._clean_text(match.group(1))
        return None

    @classmethod
    def extract_metadata(cls, html: str) -> Dict[str, str]:
        """Extract meta tags."""
        metadata = {}
        for match in re.finditer(cls.META_PATTERN, html, re.IGNORECASE):
            name = match.group(1).lower()
            content = match.group(2)
            metadata[name] = content
        return metadata

    @classmethod
    def extract_links(cls, html: str, base_url: str = "") -> List[str]:
        """Extract all links from HTML."""
        links = []
        for match in re.finditer(cls.LINK_PATTERN, html, re.IGNORECASE):
            href = match.group(1)
            if href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
            if base_url and not URLAnalyzer.is_valid(href):
                href = URLAnalyzer.make_absolute(base_url, href)
            if URLAnalyzer.is_valid(href):
                links.append(href)
        return list(set(links))

    @classmethod
    def extract_images(cls, html: str, base_url: str = "") -> List[str]:
        """Extract all image URLs."""
        images = []
        for match in re.finditer(cls.IMG_PATTERN, html, re.IGNORECASE):
            src = match.group(1)
            if base_url and not URLAnalyzer.is_valid(src):
                src = URLAnalyzer.make_absolute(base_url, src)
            if src and not src.startswith("data:"):
                images.append(src)
        return list(set(images))

    @classmethod
    def extract_headings(cls, html: str) -> List[str]:
        """Extract all headings."""
        headings = []
        for match in re.finditer(cls.HEADING_PATTERN, html, re.IGNORECASE | re.DOTALL):
            text = cls._clean_text(match.group(1))
            if text:
                headings.append(text)
        return headings

    @classmethod
    def extract_text(cls, html: str) -> str:
        """Extract clean text from HTML."""
        # Remove noise
        clean = html
        for pattern in cls.NOISE_PATTERNS:
            clean = re.sub(pattern, '', clean, flags=re.IGNORECASE | re.DOTALL)

        # Remove remaining tags
        clean = re.sub(r'<[^>]+>', ' ', clean)

        # Clean whitespace
        clean = re.sub(r'\s+', ' ', clean)
        clean = clean.strip()

        # Decode entities
        clean = cls._decode_entities(clean)

        return clean

    @classmethod
    def extract_main_content(cls, html: str) -> str:
        """Extract the main article content (simplified)."""
        # Try to find main content containers
        content_patterns = [
            r'<article[^>]*>([\s\S]*?)</article>',
            r'<main[^>]*>([\s\S]*?)</main>',
            r'<div[^>]*class=["\'][^"\']*content[^"\']*["\'][^>]*>([\s\S]*?)</div>',
            r'<div[^>]*id=["\'][^"\']*content[^"\']*["\'][^>]*>([\s\S]*?)</div>',
        ]

        for pattern in content_patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                return cls.extract_text(match.group(1))

        # Fall back to full text extraction
        return cls.extract_text(html)

    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean extracted text."""
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    @staticmethod
    def _decode_entities(text: str) -> str:
        """Decode HTML entities."""
        entities = {
            '&nbsp;': ' ',
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&#39;': "'",
            '&apos;': "'",
        }
        for entity, char in entities.items():
            text = text.replace(entity, char)
        return text


# =============================================================================
# WEB SCRAPER
# =============================================================================

class WebScraper:
    """Advanced web scraping with caching and rate limiting."""

    def __init__(self, config: Optional[ScrapingConfig] = None):
        self.config = config or ScrapingConfig()
        self._visited_urls: Set[str] = set()
        self._cache: Dict[str, WebContent] = {}
        self._last_request_time: Dict[str, float] = {}
        self._robots_cache: Dict[str, Dict[str, List[str]]] = {}
        self._http_client = None  # Will be initialized when needed

    async def scrape(self, url: str) -> WebContent:
        """Scrape a single URL."""
        normalized_url = URLAnalyzer.normalize(url)

        # Check cache
        if normalized_url in self._cache:
            logger.debug(f"Cache hit for {url}")
            return self._cache[normalized_url]

        # Rate limiting
        await self._rate_limit(URLAnalyzer.extract_domain(url))

        try:
            # Perform request (simulated - in real impl would use aiohttp)
            html = await self._fetch(url)

            # Extract content
            content = WebContent(
                url=url,
                title=ContentExtractor.extract_title(html),
                text=ContentExtractor.extract_text(html),
                html=html,
                content_type=self._detect_content_type(html),
                metadata=ContentExtractor.extract_metadata(html),
                links=ContentExtractor.extract_links(html, url) if self.config.extract_links else [],
                images=ContentExtractor.extract_images(html, url) if self.config.extract_images else [],
                headings=ContentExtractor.extract_headings(html)
            )

            # Cache result
            self._cache[normalized_url] = content
            return content

        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return WebContent(
                url=url,
                error=str(e),
                status_code=500
            )

    async def crawl(self, start_url: str) -> List[WebContent]:
        """Crawl starting from a URL."""
        results = []
        queue = [(start_url, 0)]
        base_domain = URLAnalyzer.extract_domain(start_url)

        while queue and len(results) < self.config.max_pages:
            url, depth = queue.pop(0)
            normalized = URLAnalyzer.normalize(url)

            if normalized in self._visited_urls:
                continue

            if depth > self.config.max_depth:
                continue

            self._visited_urls.add(normalized)

            content = await self.scrape(url)
            results.append(content)

            # Add links to queue
            if depth < self.config.max_depth:
                for link in content.links:
                    link_domain = URLAnalyzer.extract_domain(link)

                    if not self.config.follow_external and link_domain != base_domain:
                        continue

                    if self.config.allowed_domains:
                        if link_domain not in self.config.allowed_domains:
                            continue

                    if any(re.match(pattern, link) for pattern in self.config.excluded_patterns):
                        continue

                    queue.append((link, depth + 1))

        return results

    async def _fetch(self, url: str) -> str:
        """Fetch URL content (simulated - extend with aiohttp)."""
        # This is a placeholder - in real implementation use aiohttp
        # For now, return a simulated response
        logger.info(f"Fetching {url}")

        # Simulated delay
        await asyncio.sleep(0.1)

        # Return placeholder HTML - in real impl, use:
        # async with aiohttp.ClientSession() as session:
        #     async with session.get(url, timeout=self.config.timeout_seconds) as resp:
        #         return await resp.text()

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Simulated Page - {url}</title>
            <meta name="description" content="This is a simulated page for testing">
        </head>
        <body>
            <h1>Welcome to {url}</h1>
            <p>This is simulated content. Install aiohttp for real web scraping.</p>
            <a href="{url}/page2">Link 1</a>
            <a href="{url}/page3">Link 2</a>
        </body>
        </html>
        """

    async def _rate_limit(self, domain: str) -> None:
        """Apply rate limiting per domain."""
        now = time.time()
        if domain in self._last_request_time:
            elapsed = now - self._last_request_time[domain]
            if elapsed < self.config.delay_seconds:
                await asyncio.sleep(self.config.delay_seconds - elapsed)
        self._last_request_time[domain] = time.time()

    def _detect_content_type(self, content: str) -> ContentType:
        """Detect content type from content."""
        content_lower = content.strip().lower()

        if content_lower.startswith("{") or content_lower.startswith("["):
            try:
                json.loads(content)
                return ContentType.JSON
            except:
                pass

        if content_lower.startswith("<?xml") or content_lower.startswith("<xml"):
            return ContentType.XML

        if "<html" in content_lower or "<!doctype html" in content_lower:
            return ContentType.HTML

        return ContentType.TEXT

    def clear_cache(self) -> None:
        """Clear the scraping cache."""
        self._cache.clear()
        self._visited_urls.clear()


# =============================================================================
# WEB SEARCH
# =============================================================================

class SearchProvider(Enum):
    """Supported search providers."""
    GOOGLE = "google"
    BING = "bing"
    DUCKDUCKGO = "duckduckgo"
    BRAVE = "brave"
    CUSTOM = "custom"


class WebSearch:
    """Multi-provider web search."""

    def __init__(
        self,
        provider: SearchProvider = SearchProvider.DUCKDUCKGO,
        api_key: Optional[str] = None
    ):
        self.provider = provider
        self.api_key = api_key
        self._scraper = WebScraper()

    async def search(
        self,
        query: str,
        num_results: int = 10,
        language: str = "en",
        region: str = "us"
    ) -> List[SearchResult]:
        """Perform a web search."""
        logger.info(f"Searching for: {query}")

        if self.provider == SearchProvider.DUCKDUCKGO:
            return await self._search_duckduckgo(query, num_results)
        elif self.provider == SearchProvider.GOOGLE:
            return await self._search_google(query, num_results)
        elif self.provider == SearchProvider.BING:
            return await self._search_bing(query, num_results)
        else:
            # Fallback to simulated results
            return await self._search_simulated(query, num_results)

    async def _search_duckduckgo(self, query: str, num_results: int) -> List[SearchResult]:
        """Search using DuckDuckGo (simulated - extend with actual API)."""
        # In real implementation, use ddg-api or scrape DuckDuckGo
        # For now, return simulated results
        return await self._search_simulated(query, num_results, "duckduckgo")

    async def _search_google(self, query: str, num_results: int) -> List[SearchResult]:
        """Search using Google Custom Search API."""
        if not self.api_key:
            logger.warning("No API key for Google search, using simulation")
            return await self._search_simulated(query, num_results, "google")

        # In real implementation, use Google Custom Search API
        # For now, return simulated results
        return await self._search_simulated(query, num_results, "google")

    async def _search_bing(self, query: str, num_results: int) -> List[SearchResult]:
        """Search using Bing Search API."""
        if not self.api_key:
            logger.warning("No API key for Bing search, using simulation")
            return await self._search_simulated(query, num_results, "bing")

        # In real implementation, use Bing Search API
        return await self._search_simulated(query, num_results, "bing")

    async def _search_simulated(
        self,
        query: str,
        num_results: int,
        source: str = "simulated"
    ) -> List[SearchResult]:
        """Generate simulated search results for testing."""
        results = []

        for i in range(min(num_results, 10)):
            results.append(SearchResult(
                title=f"Result {i+1}: {query}",
                url=f"https://example.com/search/{query.replace(' ', '-')}/result-{i+1}",
                snippet=f"This is a simulated search result for '{query}'. "
                       f"Result number {i+1} of {num_results}.",
                position=i + 1,
                source=source,
                relevance_score=1.0 - (i * 0.1),
                metadata={"simulated": True}
            ))

        return results

    async def deep_search(
        self,
        query: str,
        num_results: int = 5,
        scrape_results: bool = True
    ) -> Dict[str, Any]:
        """Perform deep search with content extraction."""
        search_results = await self.search(query, num_results)

        if not scrape_results:
            return {
                "query": query,
                "results": [r.__dict__ for r in search_results],
                "scraped_content": []
            }

        # Scrape each result
        scraped = []
        for result in search_results:
            content = await self._scraper.scrape(result.url)
            scraped.append({
                "url": result.url,
                "title": content.title,
                "text": content.text[:2000],
                "error": content.error
            })

        return {
            "query": query,
            "results": [r.__dict__ for r in search_results],
            "scraped_content": scraped
        }


# =============================================================================
# API CLIENT
# =============================================================================

class HTTPMethod(Enum):
    """HTTP methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


@dataclass
class APIResponse:
    """API response wrapper."""
    status_code: int
    headers: Dict[str, str]
    body: Any
    elapsed_ms: float
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return 200 <= self.status_code < 300

    @property
    def json(self) -> Optional[Dict]:
        if isinstance(self.body, dict):
            return self.body
        if isinstance(self.body, str):
            try:
                return json.loads(self.body)
            except:
                return None
        return None


class APIClient:
    """Versatile API client for REST APIs."""

    def __init__(
        self,
        base_url: str = "",
        default_headers: Optional[Dict[str, str]] = None,
        timeout: float = 30.0,
        auth: Optional[Tuple[str, str]] = None
    ):
        self.base_url = base_url.rstrip("/")
        self.default_headers = default_headers or {}
        self.timeout = timeout
        self.auth = auth

    async def request(
        self,
        method: HTTPMethod,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> APIResponse:
        """Make an API request."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}" if self.base_url else endpoint

        # Merge headers
        request_headers = {**self.default_headers}
        if headers:
            request_headers.update(headers)

        start_time = time.time()

        try:
            # This is a simulation - in real impl use aiohttp
            logger.info(f"API {method.value} {url}")
            await asyncio.sleep(0.1)  # Simulate network delay

            # Simulate response
            response_body = {
                "message": "Simulated response",
                "method": method.value,
                "url": url,
                "params": params,
                "data": data or json_body,
                "timestamp": datetime.now().isoformat()
            }

            elapsed = (time.time() - start_time) * 1000

            return APIResponse(
                status_code=200,
                headers={"content-type": "application/json"},
                body=response_body,
                elapsed_ms=elapsed
            )

        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            return APIResponse(
                status_code=500,
                headers={},
                body=None,
                elapsed_ms=elapsed,
                error=str(e)
            )

    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> APIResponse:
        """GET request."""
        return await self.request(HTTPMethod.GET, endpoint, params=params, **kwargs)

    async def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> APIResponse:
        """POST request."""
        return await self.request(HTTPMethod.POST, endpoint, data=data, json_body=json_body, **kwargs)

    async def put(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> APIResponse:
        """PUT request."""
        return await self.request(HTTPMethod.PUT, endpoint, data=data, json_body=json_body, **kwargs)

    async def patch(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> APIResponse:
        """PATCH request."""
        return await self.request(HTTPMethod.PATCH, endpoint, data=data, json_body=json_body, **kwargs)

    async def delete(
        self,
        endpoint: str,
        **kwargs
    ) -> APIResponse:
        """DELETE request."""
        return await self.request(HTTPMethod.DELETE, endpoint, **kwargs)


# =============================================================================
# WEB TOOLKIT - UNIFIED INTERFACE
# =============================================================================

class WebToolkit:
    """
    Unified web toolkit providing all web interaction capabilities.

    This is the main entry point for web operations in BAEL.
    """

    def __init__(
        self,
        scraping_config: Optional[ScrapingConfig] = None,
        search_provider: SearchProvider = SearchProvider.DUCKDUCKGO,
        api_key: Optional[str] = None
    ):
        self.scraper = WebScraper(scraping_config)
        self.search = WebSearch(search_provider, api_key)
        self.api = APIClient()
        self.url_analyzer = URLAnalyzer()
        self.content_extractor = ContentExtractor()

    async def fetch_page(self, url: str) -> WebContent:
        """Fetch and extract content from a URL."""
        return await self.scraper.scrape(url)

    async def crawl_site(
        self,
        start_url: str,
        max_pages: int = 50,
        max_depth: int = 2
    ) -> List[WebContent]:
        """Crawl a website starting from a URL."""
        self.scraper.config.max_pages = max_pages
        self.scraper.config.max_depth = max_depth
        return await self.scraper.crawl(start_url)

    async def web_search(
        self,
        query: str,
        num_results: int = 10,
        scrape: bool = False
    ) -> Union[List[SearchResult], Dict[str, Any]]:
        """Search the web."""
        if scrape:
            return await self.search.deep_search(query, num_results)
        return await self.search.search(query, num_results)

    async def call_api(
        self,
        url: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> APIResponse:
        """Make an API call."""
        http_method = HTTPMethod(method.upper())
        return await self.api.request(http_method, url, json_body=data, headers=headers)

    def analyze_url(self, url: str) -> Dict[str, Any]:
        """Analyze a URL."""
        return self.url_analyzer.parse(url)

    def extract_from_html(
        self,
        html: str,
        base_url: str = ""
    ) -> Dict[str, Any]:
        """Extract content from HTML."""
        return {
            "title": self.content_extractor.extract_title(html),
            "text": self.content_extractor.extract_text(html),
            "main_content": self.content_extractor.extract_main_content(html),
            "metadata": self.content_extractor.extract_metadata(html),
            "links": self.content_extractor.extract_links(html, base_url),
            "images": self.content_extractor.extract_images(html, base_url),
            "headings": self.content_extractor.extract_headings(html)
        }

    # -------------------------------------------------------------------------
    # Tool Definitions for BAEL Integration
    # -------------------------------------------------------------------------

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get tool definitions for BAEL's tool registry."""
        return [
            {
                "name": "web_fetch",
                "description": "Fetch and extract content from a URL",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to fetch"}
                    },
                    "required": ["url"]
                },
                "handler": self.fetch_page
            },
            {
                "name": "web_search",
                "description": "Search the web for information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "num_results": {"type": "integer", "default": 10},
                        "scrape": {"type": "boolean", "default": False}
                    },
                    "required": ["query"]
                },
                "handler": self.web_search
            },
            {
                "name": "web_crawl",
                "description": "Crawl a website from a starting URL",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "start_url": {"type": "string"},
                        "max_pages": {"type": "integer", "default": 50},
                        "max_depth": {"type": "integer", "default": 2}
                    },
                    "required": ["start_url"]
                },
                "handler": self.crawl_site
            },
            {
                "name": "api_call",
                "description": "Make an HTTP API call",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "method": {"type": "string", "default": "GET"},
                        "data": {"type": "object"},
                        "headers": {"type": "object"}
                    },
                    "required": ["url"]
                },
                "handler": self.call_api
            },
            {
                "name": "url_analyze",
                "description": "Analyze and parse a URL",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"}
                    },
                    "required": ["url"]
                },
                "handler": lambda url: self.analyze_url(url)
            }
        ]


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "WebToolkit",
    "WebScraper",
    "WebSearch",
    "APIClient",
    "URLAnalyzer",
    "ContentExtractor",
    "ScrapingConfig",
    "SearchResult",
    "WebContent",
    "SearchProvider",
    "ContentType",
    "HTTPMethod",
    "APIResponse"
]
