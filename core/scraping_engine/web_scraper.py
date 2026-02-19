"""
BAEL Web Scraping Engine
========================

Professional-grade web scraping with:
- Intelligent content extraction
- Rate limiting and politeness
- Proxy rotation
- Caching and deduplication
- Anti-detection measures

"Extract knowledge from the infinite web." — Ba'el
"""

import asyncio
import hashlib
import json
import logging
import random
import re
import time
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Pattern, Set, Tuple, Union
from html.parser import HTMLParser

logger = logging.getLogger("BAEL.Scraper")


# =============================================================================
# ENUMS
# =============================================================================

class ScraperType(Enum):
    """Types of scrapers."""
    BASIC = "basic"          # Simple HTML fetching
    DYNAMIC = "dynamic"      # JavaScript rendering
    API = "api"              # REST API consumption
    FEEDS = "feeds"          # RSS/Atom feeds
    STRUCTURED = "structured" # JSON-LD, microdata


class ContentType(Enum):
    """Types of content to extract."""
    HTML = "html"
    JSON = "json"
    XML = "xml"
    TEXT = "text"
    BINARY = "binary"
    PDF = "pdf"
    IMAGE = "image"


class ExtractionMethod(Enum):
    """Content extraction methods."""
    CSS_SELECTOR = "css"
    XPATH = "xpath"
    REGEX = "regex"
    JSON_PATH = "jsonpath"
    CUSTOM = "custom"


class RateLimitStrategy(Enum):
    """Rate limiting strategies."""
    FIXED = "fixed"           # Fixed delay between requests
    RANDOM = "random"         # Random delay within range
    ADAPTIVE = "adaptive"     # Adjust based on response times
    DOMAIN_BASED = "domain"   # Per-domain limits


class CrawlStrategy(Enum):
    """Crawling strategies."""
    BFS = "bfs"              # Breadth-first search
    DFS = "dfs"              # Depth-first search
    PRIORITY = "priority"    # Priority queue
    RANDOM = "random"        # Random selection


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ScraperConfig:
    """Configuration for the scraper."""
    user_agent: str = "BAEL-Scraper/3.0 (Intelligent Web Crawler)"
    timeout_seconds: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    follow_redirects: bool = True
    max_redirects: int = 5
    verify_ssl: bool = True
    rate_limit_strategy: RateLimitStrategy = RateLimitStrategy.ADAPTIVE
    requests_per_second: float = 1.0
    respect_robots_txt: bool = True
    max_concurrent: int = 5
    cache_enabled: bool = True
    cache_ttl_hours: int = 24
    proxy_enabled: bool = False
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class PageRequest:
    """Request for a page."""
    url: str
    method: str = "GET"
    headers: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, str] = field(default_factory=dict)
    data: Optional[Dict[str, Any]] = None
    json_data: Optional[Dict[str, Any]] = None
    cookies: Dict[str, str] = field(default_factory=dict)
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PageResponse:
    """Response from a page request."""
    url: str
    status_code: int
    headers: Dict[str, str]
    content: bytes
    text: str
    content_type: ContentType
    encoding: str = "utf-8"
    response_time_ms: float = 0.0
    from_cache: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedData:
    """Extracted data from a page."""
    url: str
    data: Dict[str, Any]
    extraction_method: ExtractionMethod
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScrapingResult:
    """Result of a scraping operation."""
    success: bool
    url: str
    extracted: List[ExtractedData] = field(default_factory=list)
    links_found: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    duration_ms: float = 0.0
    pages_scraped: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CrawlState:
    """State of a crawl operation."""
    seed_urls: List[str]
    visited: Set[str] = field(default_factory=set)
    queue: List[str] = field(default_factory=list)
    results: List[ScrapingResult] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    max_pages: int = 100
    max_depth: int = 3
    current_depth: int = 0


# =============================================================================
# HTML PARSER
# =============================================================================

class SimpleHTMLParser(HTMLParser):
    """Simple HTML parser for content extraction."""

    def __init__(self):
        super().__init__()
        self.text_parts: List[str] = []
        self.links: List[str] = []
        self.images: List[str] = []
        self.scripts: List[str] = []
        self.meta: Dict[str, str] = {}
        self._in_script = False
        self._in_style = False
        self._current_tag = ""

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        self._current_tag = tag
        attrs_dict = dict(attrs)

        if tag == "script":
            self._in_script = True
        elif tag == "style":
            self._in_style = True
        elif tag == "a" and "href" in attrs_dict:
            href = attrs_dict["href"]
            if href:
                self.links.append(href)
        elif tag == "img" and "src" in attrs_dict:
            src = attrs_dict["src"]
            if src:
                self.images.append(src)
        elif tag == "meta":
            name = attrs_dict.get("name") or attrs_dict.get("property", "")
            content = attrs_dict.get("content", "")
            if name and content:
                self.meta[name] = content

    def handle_endtag(self, tag: str):
        if tag == "script":
            self._in_script = False
        elif tag == "style":
            self._in_style = False
        self._current_tag = ""

    def handle_data(self, data: str):
        if not self._in_script and not self._in_style:
            text = data.strip()
            if text:
                self.text_parts.append(text)

    def get_text(self) -> str:
        """Get extracted text."""
        return " ".join(self.text_parts)


# =============================================================================
# CONTENT EXTRACTOR
# =============================================================================

class ContentExtractor:
    """Extracts content from web pages."""

    def __init__(self):
        self._patterns: Dict[str, Pattern] = {}
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile common regex patterns."""
        self._patterns = {
            "email": re.compile(r'[\w\.-]+@[\w\.-]+\.\w+'),
            "phone": re.compile(r'\+?[\d\s\-\(\)]{10,}'),
            "url": re.compile(r'https?://[^\s<>"\']+'),
            "price": re.compile(r'\$[\d,]+\.?\d*'),
            "date": re.compile(r'\d{1,4}[-/]\d{1,2}[-/]\d{1,4}'),
            "json_ld": re.compile(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.DOTALL),
        }

    def extract_text(self, html: str) -> str:
        """Extract clean text from HTML."""
        parser = SimpleHTMLParser()
        parser.feed(html)
        return parser.get_text()

    def extract_links(self, html: str, base_url: str = "") -> List[str]:
        """Extract all links from HTML."""
        parser = SimpleHTMLParser()
        parser.feed(html)

        links = []
        for link in parser.links:
            if link.startswith("http"):
                links.append(link)
            elif link.startswith("/") and base_url:
                # Absolute path
                parsed = urllib.parse.urlparse(base_url)
                links.append(f"{parsed.scheme}://{parsed.netloc}{link}")
            elif base_url and not link.startswith("#"):
                # Relative path
                links.append(urllib.parse.urljoin(base_url, link))

        return list(set(links))

    def extract_meta(self, html: str) -> Dict[str, str]:
        """Extract meta tags from HTML."""
        parser = SimpleHTMLParser()
        parser.feed(html)
        return parser.meta

    def extract_images(self, html: str, base_url: str = "") -> List[str]:
        """Extract image URLs from HTML."""
        parser = SimpleHTMLParser()
        parser.feed(html)

        images = []
        for img in parser.images:
            if img.startswith("http"):
                images.append(img)
            elif img.startswith("/") and base_url:
                parsed = urllib.parse.urlparse(base_url)
                images.append(f"{parsed.scheme}://{parsed.netloc}{img}")
            elif base_url:
                images.append(urllib.parse.urljoin(base_url, img))

        return images

    def extract_by_pattern(
        self,
        text: str,
        pattern_name: str
    ) -> List[str]:
        """Extract data using named pattern."""
        pattern = self._patterns.get(pattern_name)
        if pattern:
            return pattern.findall(text)
        return []

    def extract_by_regex(self, text: str, pattern: str) -> List[str]:
        """Extract data using custom regex."""
        try:
            compiled = re.compile(pattern)
            return compiled.findall(text)
        except re.error:
            return []

    def extract_structured_data(self, html: str) -> List[Dict[str, Any]]:
        """Extract JSON-LD structured data."""
        results = []

        matches = self._patterns["json_ld"].findall(html)
        for match in matches:
            try:
                data = json.loads(match)
                results.append(data)
            except json.JSONDecodeError:
                pass

        return results

    def extract_tables(self, html: str) -> List[List[List[str]]]:
        """Extract tables from HTML (simplified)."""
        tables = []

        # Simple regex-based table extraction
        table_pattern = re.compile(r'<table[^>]*>(.*?)</table>', re.DOTALL | re.IGNORECASE)
        row_pattern = re.compile(r'<tr[^>]*>(.*?)</tr>', re.DOTALL | re.IGNORECASE)
        cell_pattern = re.compile(r'<t[hd][^>]*>(.*?)</t[hd]>', re.DOTALL | re.IGNORECASE)

        for table_match in table_pattern.findall(html):
            table = []
            for row_match in row_pattern.findall(table_match):
                row = []
                for cell_match in cell_pattern.findall(row_match):
                    # Strip HTML tags from cell content
                    clean_cell = re.sub(r'<[^>]+>', '', cell_match).strip()
                    row.append(clean_cell)
                if row:
                    table.append(row)
            if table:
                tables.append(table)

        return tables

    def extract_article(self, html: str) -> Dict[str, Any]:
        """Extract article content (simplified readability)."""
        # Extract meta information
        meta = self.extract_meta(html)

        # Try to find title
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE)
        title = title_match.group(1) if title_match else meta.get("og:title", "")

        # Try to find main content
        # Look for article, main, or content divs
        content_patterns = [
            r'<article[^>]*>(.*?)</article>',
            r'<main[^>]*>(.*?)</main>',
            r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>',
        ]

        content = ""
        for pattern in content_patterns:
            match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1)
                break

        # Clean content
        clean_content = self.extract_text(content) if content else self.extract_text(html)

        return {
            "title": title.strip() if title else "",
            "description": meta.get("description", meta.get("og:description", "")),
            "content": clean_content,
            "image": meta.get("og:image", ""),
            "author": meta.get("author", ""),
            "published": meta.get("article:published_time", "")
        }


# =============================================================================
# RATE LIMITER
# =============================================================================

class RateLimiter:
    """Rate limiting for requests."""

    def __init__(
        self,
        requests_per_second: float = 1.0,
        strategy: RateLimitStrategy = RateLimitStrategy.FIXED
    ):
        self.requests_per_second = requests_per_second
        self.strategy = strategy
        self._last_request: Dict[str, float] = {}
        self._request_times: List[float] = []
        self._domain_limits: Dict[str, float] = {}

    async def wait(self, url: str):
        """Wait before making a request."""
        domain = urllib.parse.urlparse(url).netloc
        now = time.time()

        if self.strategy == RateLimitStrategy.FIXED:
            delay = 1.0 / self.requests_per_second
        elif self.strategy == RateLimitStrategy.RANDOM:
            base_delay = 1.0 / self.requests_per_second
            delay = random.uniform(base_delay * 0.5, base_delay * 1.5)
        elif self.strategy == RateLimitStrategy.ADAPTIVE:
            delay = self._calculate_adaptive_delay()
        elif self.strategy == RateLimitStrategy.DOMAIN_BASED:
            delay = self._domain_limits.get(domain, 1.0 / self.requests_per_second)
        else:
            delay = 1.0

        last_request = self._last_request.get(domain, 0)
        elapsed = now - last_request

        if elapsed < delay:
            await asyncio.sleep(delay - elapsed)

        self._last_request[domain] = time.time()
        self._request_times.append(time.time())

        # Keep only recent request times
        cutoff = now - 60
        self._request_times = [t for t in self._request_times if t > cutoff]

    def _calculate_adaptive_delay(self) -> float:
        """Calculate adaptive delay based on recent performance."""
        if not self._request_times:
            return 1.0 / self.requests_per_second

        # Calculate current rate
        recent_count = len(self._request_times)
        if recent_count < 2:
            return 1.0 / self.requests_per_second

        duration = self._request_times[-1] - self._request_times[0]
        if duration <= 0:
            return 1.0 / self.requests_per_second

        current_rate = recent_count / duration

        # Adjust delay to maintain target rate
        if current_rate > self.requests_per_second:
            return 1.0 / self.requests_per_second * 1.2
        else:
            return 1.0 / self.requests_per_second * 0.9

    def set_domain_limit(self, domain: str, requests_per_second: float):
        """Set rate limit for a specific domain."""
        self._domain_limits[domain] = 1.0 / requests_per_second


# =============================================================================
# PROXY MANAGER
# =============================================================================

class ProxyManager:
    """Manages proxy rotation."""

    def __init__(self):
        self._proxies: List[Dict[str, str]] = []
        self._current_index = 0
        self._failures: Dict[str, int] = {}
        self._max_failures = 3

    def add_proxy(
        self,
        host: str,
        port: int,
        protocol: str = "http",
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        """Add a proxy to the pool."""
        proxy_url = f"{protocol}://"
        if username and password:
            proxy_url += f"{username}:{password}@"
        proxy_url += f"{host}:{port}"

        self._proxies.append({
            "http": proxy_url,
            "https": proxy_url
        })

    def get_proxy(self) -> Optional[Dict[str, str]]:
        """Get next available proxy."""
        if not self._proxies:
            return None

        # Skip failed proxies
        attempts = 0
        while attempts < len(self._proxies):
            proxy = self._proxies[self._current_index]
            proxy_key = proxy.get("http", "")

            if self._failures.get(proxy_key, 0) < self._max_failures:
                self._current_index = (self._current_index + 1) % len(self._proxies)
                return proxy

            self._current_index = (self._current_index + 1) % len(self._proxies)
            attempts += 1

        return None

    def report_failure(self, proxy: Dict[str, str]):
        """Report a proxy failure."""
        proxy_key = proxy.get("http", "")
        self._failures[proxy_key] = self._failures.get(proxy_key, 0) + 1

    def report_success(self, proxy: Dict[str, str]):
        """Report a proxy success."""
        proxy_key = proxy.get("http", "")
        self._failures[proxy_key] = 0

    def remove_proxy(self, proxy: Dict[str, str]):
        """Remove a proxy from the pool."""
        if proxy in self._proxies:
            self._proxies.remove(proxy)


# =============================================================================
# CACHE MANAGER
# =============================================================================

class CacheManager:
    """Manages response caching."""

    def __init__(self, cache_dir: Optional[Path] = None, ttl_hours: int = 24):
        self.cache_dir = cache_dir or Path("data/scraper_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_hours = ttl_hours
        self._memory_cache: Dict[str, Tuple[datetime, PageResponse]] = {}

    def _url_to_key(self, url: str) -> str:
        """Convert URL to cache key."""
        return hashlib.md5(url.encode()).hexdigest()

    def get(self, url: str) -> Optional[PageResponse]:
        """Get cached response."""
        key = self._url_to_key(url)
        now = datetime.now()

        # Check memory cache
        if key in self._memory_cache:
            cached_time, response = self._memory_cache[key]
            if now - cached_time < timedelta(hours=self.ttl_hours):
                response.from_cache = True
                return response
            else:
                del self._memory_cache[key]

        # Check disk cache
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text())
                cached_time = datetime.fromisoformat(data["cached_at"])

                if now - cached_time < timedelta(hours=self.ttl_hours):
                    response = PageResponse(
                        url=data["url"],
                        status_code=data["status_code"],
                        headers=data["headers"],
                        content=data["content"].encode(),
                        text=data["content"],
                        content_type=ContentType(data["content_type"]),
                        encoding=data.get("encoding", "utf-8"),
                        from_cache=True
                    )
                    return response
                else:
                    cache_file.unlink()
            except (json.JSONDecodeError, KeyError):
                cache_file.unlink()

        return None

    def set(self, url: str, response: PageResponse):
        """Cache a response."""
        key = self._url_to_key(url)
        now = datetime.now()

        # Memory cache
        self._memory_cache[key] = (now, response)

        # Disk cache
        cache_file = self.cache_dir / f"{key}.json"
        data = {
            "url": url,
            "status_code": response.status_code,
            "headers": response.headers,
            "content": response.text,
            "content_type": response.content_type.value,
            "encoding": response.encoding,
            "cached_at": now.isoformat()
        }
        cache_file.write_text(json.dumps(data))

    def clear(self):
        """Clear all cache."""
        self._memory_cache.clear()
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()


# =============================================================================
# ROBOTS.TXT PARSER
# =============================================================================

class RobotsParser:
    """Parses robots.txt files."""

    def __init__(self):
        self._rules: Dict[str, Dict[str, Any]] = {}

    def parse(self, content: str, base_url: str):
        """Parse robots.txt content."""
        domain = urllib.parse.urlparse(base_url).netloc

        rules = {
            "disallowed": [],
            "allowed": [],
            "crawl_delay": None,
            "sitemaps": []
        }

        current_agent = "*"
        applies_to_us = False

        for line in content.split("\n"):
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            if ":" not in line:
                continue

            key, value = line.split(":", 1)
            key = key.strip().lower()
            value = value.strip()

            if key == "user-agent":
                current_agent = value.lower()
                applies_to_us = current_agent in ["*", "bael-scraper", "bael"]
            elif applies_to_us:
                if key == "disallow" and value:
                    rules["disallowed"].append(value)
                elif key == "allow" and value:
                    rules["allowed"].append(value)
                elif key == "crawl-delay":
                    try:
                        rules["crawl_delay"] = float(value)
                    except ValueError:
                        pass

            if key == "sitemap":
                rules["sitemaps"].append(value)

        self._rules[domain] = rules

    def is_allowed(self, url: str) -> bool:
        """Check if URL is allowed."""
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc
        path = parsed.path

        if domain not in self._rules:
            return True

        rules = self._rules[domain]

        # Check allowed first (more specific)
        for allowed_path in rules["allowed"]:
            if path.startswith(allowed_path):
                return True

        # Check disallowed
        for disallowed_path in rules["disallowed"]:
            if path.startswith(disallowed_path):
                return False

        return True

    def get_crawl_delay(self, domain: str) -> Optional[float]:
        """Get crawl delay for domain."""
        if domain in self._rules:
            return self._rules[domain].get("crawl_delay")
        return None

    def get_sitemaps(self, domain: str) -> List[str]:
        """Get sitemaps for domain."""
        if domain in self._rules:
            return self._rules[domain].get("sitemaps", [])
        return []


# =============================================================================
# WEB SCRAPING ENGINE
# =============================================================================

class WebScrapingEngine:
    """Main web scraping engine."""

    def __init__(self, config: Optional[ScraperConfig] = None):
        self.config = config or ScraperConfig()
        self.extractor = ContentExtractor()
        self.rate_limiter = RateLimiter(
            self.config.requests_per_second,
            self.config.rate_limit_strategy
        )
        self.proxy_manager = ProxyManager()
        self.cache = CacheManager(ttl_hours=self.config.cache_ttl_hours)
        self.robots_parser = RobotsParser()

        # Statistics
        self._stats = {
            "requests_made": 0,
            "cache_hits": 0,
            "errors": 0,
            "bytes_downloaded": 0
        }

    async def fetch(self, request: PageRequest) -> PageResponse:
        """Fetch a page."""
        # Check cache first
        if self.config.cache_enabled:
            cached = self.cache.get(request.url)
            if cached:
                self._stats["cache_hits"] += 1
                return cached

        # Rate limiting
        await self.rate_limiter.wait(request.url)

        # Check robots.txt
        if self.config.respect_robots_txt:
            if not self.robots_parser.is_allowed(request.url):
                logger.warning(f"URL blocked by robots.txt: {request.url}")
                return PageResponse(
                    url=request.url,
                    status_code=403,
                    headers={},
                    content=b"Blocked by robots.txt",
                    text="Blocked by robots.txt",
                    content_type=ContentType.TEXT
                )

        # Build headers
        headers = {
            "User-Agent": self.config.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            **self.config.headers,
            **request.headers
        }

        # Make request (simplified - would use aiohttp/httpx in production)
        start_time = time.time()

        try:
            # Simulate HTTP request
            # In production, use aiohttp or httpx
            import urllib.request
            import urllib.error

            req = urllib.request.Request(
                request.url,
                headers=headers,
                method=request.method
            )

            try:
                with urllib.request.urlopen(req, timeout=self.config.timeout_seconds) as response:
                    content = response.read()
                    status_code = response.status
                    response_headers = dict(response.headers)
            except urllib.error.HTTPError as e:
                content = e.read() if hasattr(e, 'read') else b""
                status_code = e.code
                response_headers = dict(e.headers) if hasattr(e, 'headers') else {}

            duration_ms = (time.time() - start_time) * 1000

            # Determine content type
            content_type_header = response_headers.get("Content-Type", "text/html")
            if "json" in content_type_header:
                content_type = ContentType.JSON
            elif "xml" in content_type_header:
                content_type = ContentType.XML
            elif "html" in content_type_header:
                content_type = ContentType.HTML
            else:
                content_type = ContentType.TEXT

            # Decode content
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                text = content.decode("latin-1")

            page_response = PageResponse(
                url=request.url,
                status_code=status_code,
                headers=response_headers,
                content=content,
                text=text,
                content_type=content_type,
                response_time_ms=duration_ms
            )

            # Cache response
            if self.config.cache_enabled and 200 <= status_code < 300:
                self.cache.set(request.url, page_response)

            # Update stats
            self._stats["requests_made"] += 1
            self._stats["bytes_downloaded"] += len(content)

            return page_response

        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"Request failed: {request.url} - {e}")

            return PageResponse(
                url=request.url,
                status_code=0,
                headers={},
                content=str(e).encode(),
                text=str(e),
                content_type=ContentType.TEXT,
                response_time_ms=(time.time() - start_time) * 1000
            )

    async def scrape(
        self,
        url: str,
        extraction_rules: Optional[Dict[str, Any]] = None
    ) -> ScrapingResult:
        """Scrape a single URL."""
        start_time = time.time()

        request = PageRequest(url=url)
        response = await self.fetch(request)

        if response.status_code != 200:
            return ScrapingResult(
                success=False,
                url=url,
                errors=[f"HTTP {response.status_code}"],
                duration_ms=(time.time() - start_time) * 1000
            )

        extracted_data = []

        # Apply extraction rules
        if extraction_rules:
            data = {}
            for name, rule in extraction_rules.items():
                method = rule.get("method", "regex")
                pattern = rule.get("pattern", "")

                if method == "regex":
                    matches = self.extractor.extract_by_regex(response.text, pattern)
                    data[name] = matches[0] if len(matches) == 1 else matches
                elif method == "text":
                    data[name] = self.extractor.extract_text(response.text)
                elif method == "meta":
                    data[name] = self.extractor.extract_meta(response.text).get(pattern, "")
                elif method == "links":
                    data[name] = self.extractor.extract_links(response.text, url)

            extracted_data.append(ExtractedData(
                url=url,
                data=data,
                extraction_method=ExtractionMethod.REGEX
            ))
        else:
            # Default extraction
            extracted_data.append(ExtractedData(
                url=url,
                data={
                    "text": self.extractor.extract_text(response.text),
                    "meta": self.extractor.extract_meta(response.text),
                    "structured_data": self.extractor.extract_structured_data(response.text)
                },
                extraction_method=ExtractionMethod.CUSTOM
            ))

        # Extract links for crawling
        links = self.extractor.extract_links(response.text, url)

        return ScrapingResult(
            success=True,
            url=url,
            extracted=extracted_data,
            links_found=links,
            duration_ms=(time.time() - start_time) * 1000,
            pages_scraped=1
        )

    async def crawl(
        self,
        seed_urls: List[str],
        max_pages: int = 100,
        max_depth: int = 3,
        url_filter: Optional[Callable[[str], bool]] = None,
        extraction_rules: Optional[Dict[str, Any]] = None
    ) -> List[ScrapingResult]:
        """Crawl multiple pages starting from seed URLs."""
        state = CrawlState(
            seed_urls=seed_urls,
            max_pages=max_pages,
            max_depth=max_depth
        )

        state.queue = list(seed_urls)

        while state.queue and len(state.visited) < max_pages:
            # Get next URL
            url = state.queue.pop(0)

            if url in state.visited:
                continue

            # Apply filter
            if url_filter and not url_filter(url):
                continue

            state.visited.add(url)

            # Scrape URL
            result = await self.scrape(url, extraction_rules)
            state.results.append(result)

            # Add found links to queue
            if result.success:
                for link in result.links_found:
                    if link not in state.visited and link not in state.queue:
                        # Stay within same domain by default
                        if urllib.parse.urlparse(link).netloc == urllib.parse.urlparse(url).netloc:
                            state.queue.append(link)

        return state.results

    async def extract_article(self, url: str) -> Dict[str, Any]:
        """Extract article content from URL."""
        request = PageRequest(url=url)
        response = await self.fetch(request)

        if response.status_code != 200:
            return {"error": f"HTTP {response.status_code}"}

        return self.extractor.extract_article(response.text)

    async def extract_emails(self, url: str) -> List[str]:
        """Extract email addresses from URL."""
        request = PageRequest(url=url)
        response = await self.fetch(request)

        if response.status_code != 200:
            return []

        return self.extractor.extract_by_pattern(response.text, "email")

    async def extract_tables(self, url: str) -> List[List[List[str]]]:
        """Extract tables from URL."""
        request = PageRequest(url=url)
        response = await self.fetch(request)

        if response.status_code != 200:
            return []

        return self.extractor.extract_tables(response.text)

    def get_stats(self) -> Dict[str, Any]:
        """Get scraping statistics."""
        return {
            **self._stats,
            "cache_hit_rate": (
                self._stats["cache_hits"] / max(1, self._stats["requests_made"] + self._stats["cache_hits"])
            )
        }

    def clear_cache(self):
        """Clear the cache."""
        self.cache.clear()


# =============================================================================
# CONVENIENCE INSTANCE
# =============================================================================

scraper_engine = WebScrapingEngine()
