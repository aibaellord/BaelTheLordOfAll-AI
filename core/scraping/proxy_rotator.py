"""
BAEL Proxy Rotator
===================

Proxy management and rotation for anonymous scraping.
Supports multiple proxy sources and health monitoring.

Features:
- Multiple proxy providers
- Automatic rotation
- Health checking
- Geolocation selection
- Authentication support
- Failover handling
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class ProxyType(Enum):
    """Proxy types."""
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"
    ROTATING = "rotating"  # Provider handles rotation


class ProxySource(Enum):
    """Proxy sources/providers."""
    MANUAL = "manual"
    FILE = "file"
    API = "api"
    FREE_PROXY_LIST = "freeproxylist"
    PROXYSCRAPE = "proxyscrape"
    GEONODE = "geonode"
    WEBSHARE = "webshare"
    BRIGHTDATA = "brightdata"
    SMARTPROXY = "smartproxy"
    OXYLABS = "oxylabs"


@dataclass
class ProxyConfig:
    """Proxy configuration."""
    # Sources
    sources: List[ProxySource] = field(default_factory=lambda: [ProxySource.MANUAL])

    # Rotation
    rotation_strategy: str = "random"  # random, round_robin, least_used, fastest
    rotate_on_error: bool = True
    rotate_on_ban: bool = True
    max_uses_per_proxy: int = 100

    # Health check
    health_check_interval: int = 300  # seconds
    health_check_url: str = "https://httpbin.org/ip"
    health_check_timeout: int = 10
    max_failures: int = 3

    # Filtering
    require_https: bool = False
    require_anonymous: bool = True
    allowed_countries: List[str] = field(default_factory=list)

    # Authentication
    default_username: Optional[str] = None
    default_password: Optional[str] = None


@dataclass
class ProxyHealth:
    """Proxy health information."""
    proxy: str
    is_working: bool = True
    last_checked: Optional[datetime] = None
    response_time_ms: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    last_error: Optional[str] = None
    detected_ip: Optional[str] = None
    country: Optional[str] = None

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.0
        return self.success_count / total

    @property
    def score(self) -> float:
        """Calculate proxy score (higher is better)."""
        if not self.is_working:
            return 0.0

        # Factors: success rate, response time
        rate_score = self.success_rate * 100
        time_score = max(0, 100 - self.response_time_ms / 50)  # Penalty for slow

        return (rate_score + time_score) / 2


@dataclass
class Proxy:
    """Proxy definition."""
    host: str
    port: int
    proxy_type: ProxyType = ProxyType.HTTP
    username: Optional[str] = None
    password: Optional[str] = None
    country: Optional[str] = None

    # Runtime state
    use_count: int = 0
    health: Optional[ProxyHealth] = None

    @property
    def url(self) -> str:
        """Get proxy URL."""
        scheme = self.proxy_type.value
        if scheme == "rotating":
            scheme = "http"

        if self.username and self.password:
            return f"{scheme}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{scheme}://{self.host}:{self.port}"

    @classmethod
    def from_url(cls, url: str) -> "Proxy":
        """Parse proxy from URL."""
        parsed = urlparse(url)

        proxy_type = ProxyType.HTTP
        if parsed.scheme in ("socks4", "socks5"):
            proxy_type = ProxyType(parsed.scheme)
        elif parsed.scheme == "https":
            proxy_type = ProxyType.HTTPS

        return cls(
            host=parsed.hostname or "",
            port=parsed.port or 8080,
            proxy_type=proxy_type,
            username=parsed.username,
            password=parsed.password,
        )


class ProxyRotator:
    """
    Proxy rotation and management for BAEL.
    """

    def __init__(
        self,
        config: Optional[ProxyConfig] = None,
    ):
        self.config = config or ProxyConfig()

        # Proxy pool
        self.proxies: List[Proxy] = []
        self.current_index = 0

        # Health tracking
        self.health_data: Dict[str, ProxyHealth] = {}

        # Blacklist
        self.blacklist: Dict[str, datetime] = {}
        self.blacklist_duration = timedelta(hours=1)

        # Stats
        self.stats = {
            "total_rotations": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "proxies_blacklisted": 0,
        }

        # Background task
        self._health_check_task: Optional[asyncio.Task] = None

    def add_proxy(
        self,
        proxy: Proxy,
    ) -> None:
        """Add a proxy to the pool."""
        self.proxies.append(proxy)
        self.health_data[proxy.url] = ProxyHealth(proxy=proxy.url)

    def add_proxies_from_list(
        self,
        proxy_urls: List[str],
    ) -> int:
        """Add proxies from URL list."""
        count = 0
        for url in proxy_urls:
            try:
                proxy = Proxy.from_url(url)
                self.add_proxy(proxy)
                count += 1
            except Exception as e:
                logger.warning(f"Failed to parse proxy URL: {e}")
        return count

    def add_proxies_from_file(
        self,
        filepath: str,
    ) -> int:
        """Load proxies from file (one per line)."""
        try:
            with open(filepath, "r") as f:
                lines = [line.strip() for line in f if line.strip()]
            return self.add_proxies_from_list(lines)
        except Exception as e:
            logger.error(f"Failed to load proxies from file: {e}")
            return 0

    async def fetch_free_proxies(self) -> int:
        """Fetch proxies from free sources."""
        proxies = []

        # ProxyScrape API
        try:
            import httpx

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    "https://api.proxyscrape.com/v2/",
                    params={
                        "request": "displayproxies",
                        "protocol": "http",
                        "timeout": 10000,
                        "country": "all",
                        "ssl": "all",
                        "anonymity": "all",
                    },
                )

                if response.status_code == 200:
                    for line in response.text.strip().split("\n"):
                        if line.strip():
                            parts = line.strip().split(":")
                            if len(parts) == 2:
                                proxies.append(f"http://{parts[0]}:{parts[1]}")
        except Exception as e:
            logger.warning(f"Failed to fetch from ProxyScrape: {e}")

        # Add fetched proxies
        return self.add_proxies_from_list(proxies)

    def get_available_proxies(self) -> List[Proxy]:
        """Get list of available (non-blacklisted) proxies."""
        now = datetime.now()

        # Clean expired blacklist entries
        self.blacklist = {
            url: exp for url, exp in self.blacklist.items()
            if exp > now
        }

        # Filter available
        available = [
            p for p in self.proxies
            if p.url not in self.blacklist
            and (p.health is None or p.health.is_working)
        ]

        return available

    def get_next_proxy(self) -> Optional[Proxy]:
        """Get next proxy according to rotation strategy."""
        available = self.get_available_proxies()

        if not available:
            logger.warning("No available proxies")
            return None

        strategy = self.config.rotation_strategy

        if strategy == "random":
            proxy = random.choice(available)

        elif strategy == "round_robin":
            self.current_index = (self.current_index + 1) % len(available)
            proxy = available[self.current_index]

        elif strategy == "least_used":
            proxy = min(available, key=lambda p: p.use_count)

        elif strategy == "fastest":
            # Sort by response time, prefer tested proxies
            def sort_key(p):
                health = self.health_data.get(p.url)
                if health and health.last_checked:
                    return health.response_time_ms
                return float("inf")

            proxy = min(available, key=sort_key)

        else:
            proxy = random.choice(available)

        proxy.use_count += 1
        self.stats["total_rotations"] += 1

        return proxy

    def blacklist_proxy(
        self,
        proxy: Proxy,
        reason: str = "error",
    ) -> None:
        """Blacklist a proxy."""
        self.blacklist[proxy.url] = datetime.now() + self.blacklist_duration
        self.stats["proxies_blacklisted"] += 1

        if proxy.url in self.health_data:
            self.health_data[proxy.url].is_working = False
            self.health_data[proxy.url].last_error = reason

        logger.info(f"Blacklisted proxy {proxy.host}:{proxy.port}: {reason}")

    def report_success(
        self,
        proxy: Proxy,
        response_time_ms: float = 0.0,
    ) -> None:
        """Report successful use of proxy."""
        self.stats["successful_requests"] += 1

        if proxy.url in self.health_data:
            health = self.health_data[proxy.url]
            health.success_count += 1
            health.response_time_ms = response_time_ms
            health.last_checked = datetime.now()

    def report_failure(
        self,
        proxy: Proxy,
        error: str = "",
    ) -> None:
        """Report failed use of proxy."""
        self.stats["failed_requests"] += 1

        if proxy.url in self.health_data:
            health = self.health_data[proxy.url]
            health.failure_count += 1
            health.last_error = error
            health.last_checked = datetime.now()

            # Auto-blacklist on too many failures
            if health.failure_count >= self.config.max_failures:
                self.blacklist_proxy(proxy, f"Too many failures: {error}")

    async def check_proxy_health(
        self,
        proxy: Proxy,
    ) -> ProxyHealth:
        """Check health of a single proxy."""
        try:
            import httpx
        except ImportError:
            logger.error("httpx not installed")
            return ProxyHealth(proxy=proxy.url, is_working=False)

        start_time = time.monotonic()

        try:
            async with httpx.AsyncClient(
                proxy=proxy.url,
                timeout=self.config.health_check_timeout,
            ) as client:
                response = await client.get(self.config.health_check_url)

                elapsed = (time.monotonic() - start_time) * 1000

                health = ProxyHealth(
                    proxy=proxy.url,
                    is_working=response.status_code == 200,
                    last_checked=datetime.now(),
                    response_time_ms=elapsed,
                )

                # Try to extract IP from response
                try:
                    data = response.json()
                    health.detected_ip = data.get("origin", "").split(",")[0].strip()
                except:
                    pass

                return health

        except Exception as e:
            return ProxyHealth(
                proxy=proxy.url,
                is_working=False,
                last_checked=datetime.now(),
                last_error=str(e),
            )

    async def check_all_proxies(self) -> Dict[str, ProxyHealth]:
        """Check health of all proxies."""
        tasks = [self.check_proxy_health(p) for p in self.proxies]
        results = await asyncio.gather(*tasks)

        for health in results:
            self.health_data[health.proxy] = health

            # Find matching proxy and update
            for proxy in self.proxies:
                if proxy.url == health.proxy:
                    proxy.health = health
                    break

        return self.health_data

    async def start_health_monitoring(self) -> None:
        """Start background health monitoring."""
        if self._health_check_task:
            return

        async def monitor_loop():
            while True:
                await asyncio.sleep(self.config.health_check_interval)
                try:
                    await self.check_all_proxies()
                except Exception as e:
                    logger.error(f"Health check error: {e}")

        self._health_check_task = asyncio.create_task(monitor_loop())

    def stop_health_monitoring(self) -> None:
        """Stop background health monitoring."""
        if self._health_check_task:
            self._health_check_task.cancel()
            self._health_check_task = None

    def get_stats(self) -> Dict[str, Any]:
        """Get rotator statistics."""
        working = sum(1 for h in self.health_data.values() if h.is_working)

        return {
            **self.stats,
            "total_proxies": len(self.proxies),
            "working_proxies": working,
            "blacklisted_proxies": len(self.blacklist),
            "available_proxies": len(self.get_available_proxies()),
        }


def demo():
    """Demonstrate proxy rotator."""
    print("=" * 60)
    print("BAEL Proxy Rotator Demo")
    print("=" * 60)

    config = ProxyConfig(
        rotation_strategy="random",
        max_uses_per_proxy=100,
    )

    rotator = ProxyRotator(config)

    # Add sample proxies
    sample_proxies = [
        "http://proxy1.example.com:8080",
        "http://user:pass@proxy2.example.com:3128",
        "socks5://proxy3.example.com:1080",
    ]

    count = rotator.add_proxies_from_list(sample_proxies)
    print(f"\nAdded {count} proxies")

    # Get next proxy
    proxy = rotator.get_next_proxy()
    if proxy:
        print(f"\nNext proxy: {proxy.host}:{proxy.port}")
        print(f"  Type: {proxy.proxy_type.value}")
        print(f"  URL: {proxy.url}")

    print(f"\nStats: {rotator.get_stats()}")


if __name__ == "__main__":
    demo()
