"""
BAEL Scraper Core
==================

Main scraping engine with multiple backends.
Handles HTTP requests, rate limiting, and orchestration.

Features:
- Multiple scraping strategies
- Automatic retry with backoff
- Rate limiting per domain
- Request queuing
- Session management
- Cookie handling
"""

import asyncio
import hashlib
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class ScraperType(Enum):
    """Scraper backend types."""
    REQUESTS = "requests"
    HTTPX = "httpx"
    AIOHTTP = "aiohttp"
    PLAYWRIGHT = "playwright"
    SELENIUM = "selenium"
    CLOUDSCRAPER = "cloudscraper"


@dataclass
class ScrapingConfig:
    """Scraping configuration."""
    # Backend
    scraper_type: ScraperType = ScraperType.HTTPX

    # Rate limiting
    requests_per_second: float = 2.0
    requests_per_domain: float = 1.0
    randomize_delay: bool = True
    delay_range: Tuple[float, float] = (0.5, 2.0)

    # Retries
    max_retries: int = 3
    retry_backoff: float = 2.0
    retry_codes: List[int] = field(default_factory=lambda: [429, 500, 502, 503, 504])

    # Timeouts
    connect_timeout: float = 10.0
    read_timeout: float = 30.0
    total_timeout: float = 60.0

    # Headers
    default_headers: Dict[str, str] = field(default_factory=lambda: {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    })

    # User agents
    rotate_user_agent: bool = True
    user_agents: List[str] = field(default_factory=lambda: [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ])

    # Caching
    enable_cache: bool = True
    cache_ttl: int = 3600
    cache_directory: str = ".scraper_cache"

    # Robots.txt
    respect_robots_txt: bool = False


@dataclass
class ScrapingResult:
    """Result of a scraping operation."""
    url: str
    status_code: int
    content: str
    headers: Dict[str, str] = field(default_factory=dict)

    # Timing
    request_time_ms: float = 0.0

    # Metadata
    from_cache: bool = False
    retries: int = 0
    proxy_used: Optional[str] = None
    user_agent: Optional[str] = None

    # Errors
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        """Check if request was successful."""
        return self.error is None and 200 <= self.status_code < 400

    @property
    def content_length(self) -> int:
        """Get content length."""
        return len(self.content) if self.content else 0


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(
        self,
        rate: float,
        burst: int = 1,
    ):
        self.rate = rate
        self.burst = burst
        self.tokens = burst
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Acquire a token, waiting if necessary."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_update = now

            if self.tokens < 1:
                wait_time = (1 - self.tokens) / self.rate
                await asyncio.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= 1


class ScraperCore:
    """
    Main scraping engine for BAEL.
    """

    def __init__(
        self,
        config: Optional[ScrapingConfig] = None,
    ):
        self.config = config or ScrapingConfig()

        # Rate limiters per domain
        self.domain_limiters: Dict[str, RateLimiter] = {}
        self.global_limiter = RateLimiter(
            rate=self.config.requests_per_second,
            burst=5,
        )

        # Session cache
        self.sessions: Dict[str, Any] = {}

        # Request cache
        self.cache: Dict[str, Tuple[ScrapingResult, datetime]] = {}

        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cache_hits": 0,
            "total_retries": 0,
            "bytes_downloaded": 0,
        }

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        return parsed.netloc

    def _get_domain_limiter(self, domain: str) -> RateLimiter:
        """Get or create rate limiter for domain."""
        if domain not in self.domain_limiters:
            self.domain_limiters[domain] = RateLimiter(
                rate=self.config.requests_per_domain,
                burst=2,
            )
        return self.domain_limiters[domain]

    def _get_user_agent(self) -> str:
        """Get user agent string."""
        if self.config.rotate_user_agent and self.config.user_agents:
            return random.choice(self.config.user_agents)
        return self.config.user_agents[0] if self.config.user_agents else "BAEL/1.0"

    def _get_delay(self) -> float:
        """Get request delay."""
        if self.config.randomize_delay:
            return random.uniform(*self.config.delay_range)
        return self.config.delay_range[0]

    def _cache_key(self, url: str, **kwargs) -> str:
        """Generate cache key."""
        key_data = f"{url}:{kwargs}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    def _get_cached(self, cache_key: str) -> Optional[ScrapingResult]:
        """Get cached result if valid."""
        if not self.config.enable_cache:
            return None

        if cache_key in self.cache:
            result, cached_at = self.cache[cache_key]
            if datetime.now() - cached_at < timedelta(seconds=self.config.cache_ttl):
                self.stats["cache_hits"] += 1
                result.from_cache = True
                return result
            else:
                del self.cache[cache_key]

        return None

    def _set_cache(self, cache_key: str, result: ScrapingResult) -> None:
        """Cache a result."""
        if self.config.enable_cache and result.success:
            self.cache[cache_key] = (result, datetime.now())

    async def _scrape_httpx(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        proxy: Optional[str] = None,
    ) -> ScrapingResult:
        """Scrape using httpx."""
        try:
            import httpx
        except ImportError:
            logger.error("httpx not installed")
            return ScrapingResult(
                url=url,
                status_code=0,
                content="",
                error="httpx not installed",
            )

        user_agent = self._get_user_agent()
        request_headers = {**self.config.default_headers}
        request_headers["User-Agent"] = user_agent
        if headers:
            request_headers.update(headers)

        start_time = time.monotonic()

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(
                    connect=self.config.connect_timeout,
                    read=self.config.read_timeout,
                    pool=5.0,
                ),
                proxy=proxy,
                follow_redirects=True,
            ) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    data=data,
                    json=json_data,
                )

                elapsed = (time.monotonic() - start_time) * 1000

                return ScrapingResult(
                    url=str(response.url),
                    status_code=response.status_code,
                    content=response.text,
                    headers=dict(response.headers),
                    request_time_ms=elapsed,
                    proxy_used=proxy,
                    user_agent=user_agent,
                )

        except Exception as e:
            elapsed = (time.monotonic() - start_time) * 1000
            return ScrapingResult(
                url=url,
                status_code=0,
                content="",
                request_time_ms=elapsed,
                error=str(e),
            )

    async def _scrape_aiohttp(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        proxy: Optional[str] = None,
    ) -> ScrapingResult:
        """Scrape using aiohttp."""
        try:
            import aiohttp
        except ImportError:
            logger.error("aiohttp not installed")
            return ScrapingResult(
                url=url,
                status_code=0,
                content="",
                error="aiohttp not installed",
            )

        user_agent = self._get_user_agent()
        request_headers = {**self.config.default_headers}
        request_headers["User-Agent"] = user_agent
        if headers:
            request_headers.update(headers)

        start_time = time.monotonic()

        try:
            timeout = aiohttp.ClientTimeout(
                total=self.config.total_timeout,
                connect=self.config.connect_timeout,
            )

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    data=data,
                    json=json_data,
                    proxy=proxy,
                ) as response:
                    content = await response.text()
                    elapsed = (time.monotonic() - start_time) * 1000

                    return ScrapingResult(
                        url=str(response.url),
                        status_code=response.status,
                        content=content,
                        headers=dict(response.headers),
                        request_time_ms=elapsed,
                        proxy_used=proxy,
                        user_agent=user_agent,
                    )

        except Exception as e:
            elapsed = (time.monotonic() - start_time) * 1000
            return ScrapingResult(
                url=url,
                status_code=0,
                content="",
                request_time_ms=elapsed,
                error=str(e),
            )

    async def scrape(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        proxy: Optional[str] = None,
        use_cache: bool = True,
    ) -> ScrapingResult:
        """
        Scrape a URL.

        Args:
            url: URL to scrape
            method: HTTP method
            headers: Optional headers
            data: Form data
            json_data: JSON data
            proxy: Proxy URL
            use_cache: Whether to use cache

        Returns:
            ScrapingResult
        """
        # Check cache
        if use_cache and method.upper() == "GET":
            cache_key = self._cache_key(url, headers=headers)
            cached = self._get_cached(cache_key)
            if cached:
                return cached

        # Rate limiting
        domain = self._get_domain(url)
        await self.global_limiter.acquire()
        await self._get_domain_limiter(domain).acquire()

        # Random delay
        if self.config.randomize_delay:
            await asyncio.sleep(self._get_delay())

        self.stats["total_requests"] += 1

        # Scrape with retries
        last_result = None
        retries = 0

        for attempt in range(self.config.max_retries + 1):
            if self.config.scraper_type == ScraperType.HTTPX:
                result = await self._scrape_httpx(
                    url, method, headers, data, json_data, proxy
                )
            elif self.config.scraper_type == ScraperType.AIOHTTP:
                result = await self._scrape_aiohttp(
                    url, method, headers, data, json_data, proxy
                )
            else:
                result = await self._scrape_httpx(
                    url, method, headers, data, json_data, proxy
                )

            last_result = result

            if result.success:
                break

            if result.status_code in self.config.retry_codes or result.error:
                retries += 1
                self.stats["total_retries"] += 1
                wait_time = self.config.retry_backoff ** attempt
                logger.debug(f"Retry {attempt + 1} for {url}, waiting {wait_time}s")
                await asyncio.sleep(wait_time)
            else:
                break

        last_result.retries = retries

        if last_result.success:
            self.stats["successful_requests"] += 1
            self.stats["bytes_downloaded"] += last_result.content_length

            # Cache result
            if use_cache and method.upper() == "GET":
                cache_key = self._cache_key(url, headers=headers)
                self._set_cache(cache_key, last_result)
        else:
            self.stats["failed_requests"] += 1

        return last_result

    async def scrape_batch(
        self,
        urls: List[str],
        concurrency: int = 5,
        **kwargs,
    ) -> List[ScrapingResult]:
        """
        Scrape multiple URLs concurrently.

        Args:
            urls: List of URLs
            concurrency: Max concurrent requests
            **kwargs: Arguments to pass to scrape()

        Returns:
            List of ScrapingResult
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def scrape_with_semaphore(url: str) -> ScrapingResult:
            async with semaphore:
                return await self.scrape(url, **kwargs)

        tasks = [scrape_with_semaphore(url) for url in urls]
        return await asyncio.gather(*tasks)

    def get_stats(self) -> Dict[str, Any]:
        """Get scraping statistics."""
        return {
            **self.stats,
            "cache_size": len(self.cache),
            "domains_tracked": len(self.domain_limiters),
        }

    def clear_cache(self) -> int:
        """Clear cache and return number of items cleared."""
        count = len(self.cache)
        self.cache.clear()
        return count


def demo():
    """Demonstrate scraper core."""
    print("=" * 60)
    print("BAEL Scraper Core Demo")
    print("=" * 60)

    config = ScrapingConfig(
        scraper_type=ScraperType.HTTPX,
        requests_per_second=2.0,
    )

    scraper = ScraperCore(config)

    print(f"\nScraper configuration:")
    print(f"  Type: {config.scraper_type.value}")
    print(f"  Rate: {config.requests_per_second} req/s")
    print(f"  User agents: {len(config.user_agents)}")

    print(f"\nStats: {scraper.get_stats()}")


if __name__ == "__main__":
    demo()
