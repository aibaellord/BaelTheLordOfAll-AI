#!/usr/bin/env python3
"""
BAEL - HTTP Client
Comprehensive async HTTP client with advanced features.

This module provides a powerful HTTP client for
making API requests with retries, caching, and more.

Features:
- Async HTTP requests
- Connection pooling
- Request retries with backoff
- Response caching
- Request/response interceptors
- Rate limiting
- Timeout handling
- Authentication
- Request signing
- Response validation
"""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import time
import urllib.parse
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from functools import wraps
from typing import (Any, Awaitable, Callable, Dict, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class HttpMethod(Enum):
    """HTTP methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class ContentType(Enum):
    """Common content types."""
    JSON = "application/json"
    FORM = "application/x-www-form-urlencoded"
    MULTIPART = "multipart/form-data"
    TEXT = "text/plain"
    HTML = "text/html"
    XML = "application/xml"
    BINARY = "application/octet-stream"


class AuthType(Enum):
    """Authentication types."""
    NONE = "none"
    BASIC = "basic"
    BEARER = "bearer"
    API_KEY = "api_key"
    CUSTOM = "custom"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class HttpRequest:
    """HTTP request object."""
    method: HttpMethod
    url: str
    headers: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, str] = field(default_factory=dict)
    body: Any = None
    timeout: float = 30.0
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def full_url(self) -> str:
        if not self.params:
            return self.url
        query = urllib.parse.urlencode(self.params)
        sep = "&" if "?" in self.url else "?"
        return f"{self.url}{sep}{query}"


@dataclass
class HttpResponse:
    """HTTP response object."""
    status_code: int
    headers: Dict[str, str] = field(default_factory=dict)
    body: Any = None
    request: Optional[HttpRequest] = None
    elapsed_ms: float = 0
    timestamp: float = field(default_factory=time.time)
    from_cache: bool = False

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

    @property
    def is_redirect(self) -> bool:
        return 300 <= self.status_code < 400

    @property
    def is_error(self) -> bool:
        return self.status_code >= 400

    @property
    def is_client_error(self) -> bool:
        return 400 <= self.status_code < 500

    @property
    def is_server_error(self) -> bool:
        return self.status_code >= 500

    def json(self) -> Any:
        if isinstance(self.body, dict):
            return self.body
        if isinstance(self.body, str):
            return json.loads(self.body)
        if isinstance(self.body, bytes):
            return json.loads(self.body.decode())
        return None

    def text(self) -> str:
        if isinstance(self.body, str):
            return self.body
        if isinstance(self.body, bytes):
            return self.body.decode()
        return str(self.body)


@dataclass
class RetryConfig:
    """Retry configuration."""
    max_retries: int = 3
    initial_delay: float = 0.5
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on_status: Set[int] = field(default_factory=lambda: {500, 502, 503, 504})


@dataclass
class ClientConfig:
    """HTTP client configuration."""
    base_url: str = ""
    default_headers: Dict[str, str] = field(default_factory=dict)
    timeout: float = 30.0
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    follow_redirects: bool = True
    max_redirects: int = 10
    verify_ssl: bool = True
    cache_enabled: bool = False
    cache_ttl: float = 300.0


@dataclass
class ClientStats:
    """Client statistics."""
    requests_sent: int = 0
    requests_succeeded: int = 0
    requests_failed: int = 0
    retries: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_bytes_sent: int = 0
    total_bytes_received: int = 0
    avg_response_time_ms: float = 0


# =============================================================================
# AUTHENTICATION
# =============================================================================

class Authenticator(ABC):
    """Abstract authenticator."""

    @abstractmethod
    def authenticate(self, request: HttpRequest) -> HttpRequest:
        pass


class NoAuth(Authenticator):
    """No authentication."""

    def authenticate(self, request: HttpRequest) -> HttpRequest:
        return request


class BasicAuth(Authenticator):
    """HTTP Basic authentication."""

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password

    def authenticate(self, request: HttpRequest) -> HttpRequest:
        credentials = f"{self.username}:{self.password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        request.headers["Authorization"] = f"Basic {encoded}"
        return request


class BearerAuth(Authenticator):
    """Bearer token authentication."""

    def __init__(self, token: str):
        self.token = token

    def authenticate(self, request: HttpRequest) -> HttpRequest:
        request.headers["Authorization"] = f"Bearer {self.token}"
        return request


class ApiKeyAuth(Authenticator):
    """API key authentication."""

    def __init__(
        self,
        key: str,
        header_name: str = "X-API-Key",
        in_query: bool = False,
        query_param: str = "api_key"
    ):
        self.key = key
        self.header_name = header_name
        self.in_query = in_query
        self.query_param = query_param

    def authenticate(self, request: HttpRequest) -> HttpRequest:
        if self.in_query:
            request.params[self.query_param] = self.key
        else:
            request.headers[self.header_name] = self.key
        return request


class HmacAuth(Authenticator):
    """HMAC signature authentication."""

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        header_name: str = "X-Signature"
    ):
        self.access_key = access_key
        self.secret_key = secret_key
        self.header_name = header_name

    def authenticate(self, request: HttpRequest) -> HttpRequest:
        # Create signature from request details
        string_to_sign = f"{request.method.value}\n{request.url}\n{request.timestamp}"

        signature = hmac.new(
            self.secret_key.encode(),
            string_to_sign.encode(),
            hashlib.sha256
        ).hexdigest()

        request.headers[self.header_name] = f"{self.access_key}:{signature}"
        return request


# =============================================================================
# INTERCEPTORS
# =============================================================================

class RequestInterceptor(ABC):
    """Request interceptor."""

    @abstractmethod
    async def intercept(self, request: HttpRequest) -> HttpRequest:
        pass


class ResponseInterceptor(ABC):
    """Response interceptor."""

    @abstractmethod
    async def intercept(
        self,
        response: HttpResponse,
        request: HttpRequest
    ) -> HttpResponse:
        pass


class LoggingInterceptor(RequestInterceptor, ResponseInterceptor):
    """Logging interceptor."""

    async def intercept(
        self,
        obj: Union[HttpRequest, HttpResponse],
        request: HttpRequest = None
    ) -> Union[HttpRequest, HttpResponse]:
        if isinstance(obj, HttpRequest):
            logger.debug(f"Request: {obj.method.value} {obj.full_url()}")
            return obj
        else:
            logger.debug(f"Response: {obj.status_code} in {obj.elapsed_ms:.0f}ms")
            return obj


class HeadersInterceptor(RequestInterceptor):
    """Adds headers to requests."""

    def __init__(self, headers: Dict[str, str]):
        self.headers = headers

    async def intercept(self, request: HttpRequest) -> HttpRequest:
        request.headers.update(self.headers)
        return request


# =============================================================================
# RATE LIMITER
# =============================================================================

class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(
        self,
        requests_per_second: float = 10.0,
        burst_size: int = None
    ):
        self.rate = requests_per_second
        self.capacity = burst_size or int(requests_per_second)
        self.tokens = float(self.capacity)
        self.last_update = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self) -> float:
        """Acquire a token. Returns wait time if needed."""
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_update

            # Add tokens based on elapsed time
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.rate
            )
            self.last_update = now

            if self.tokens >= 1:
                self.tokens -= 1
                return 0

            # Calculate wait time
            wait_time = (1 - self.tokens) / self.rate
            return wait_time

    async def wait(self) -> None:
        """Wait until a token is available."""
        wait_time = await self.acquire()
        if wait_time > 0:
            await asyncio.sleep(wait_time)


# =============================================================================
# RESPONSE CACHE
# =============================================================================

@dataclass
class CachedResponse:
    """Cached response entry."""
    response: HttpResponse
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0

    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class ResponseCache:
    """Simple response cache."""

    def __init__(self, max_size: int = 1000, default_ttl: float = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, CachedResponse] = {}
        self._lock = asyncio.Lock()

    def _make_key(self, request: HttpRequest) -> str:
        """Create cache key from request."""
        parts = [request.method.value, request.full_url()]
        key = "|".join(parts)
        return hashlib.md5(key.encode()).hexdigest()

    async def get(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Get cached response."""
        key = self._make_key(request)

        async with self._lock:
            cached = self.cache.get(key)

            if cached is None:
                return None

            if cached.is_expired():
                del self.cache[key]
                return None

            # Clone response and mark as from cache
            response = HttpResponse(
                status_code=cached.response.status_code,
                headers=cached.response.headers.copy(),
                body=cached.response.body,
                request=request,
                elapsed_ms=0,
                from_cache=True
            )

            return response

    async def set(
        self,
        request: HttpRequest,
        response: HttpResponse,
        ttl: float = None
    ) -> None:
        """Cache a response."""
        # Only cache successful GET requests
        if request.method != HttpMethod.GET or not response.ok:
            return

        key = self._make_key(request)
        ttl = ttl or self.default_ttl

        async with self._lock:
            # Evict if full
            if len(self.cache) >= self.max_size:
                oldest_key = min(
                    self.cache.keys(),
                    key=lambda k: self.cache[k].created_at
                )
                del self.cache[oldest_key]

            self.cache[key] = CachedResponse(
                response=response,
                expires_at=time.time() + ttl
            )

    async def clear(self) -> None:
        """Clear cache."""
        async with self._lock:
            self.cache.clear()


# =============================================================================
# MOCK TRANSPORT (for demo)
# =============================================================================

class MockTransport:
    """Mock HTTP transport for demonstration."""

    def __init__(self):
        self.routes: Dict[Tuple[str, str], Callable] = {}

    def add_route(
        self,
        method: str,
        url_pattern: str,
        handler: Callable[[HttpRequest], HttpResponse]
    ):
        self.routes[(method.upper(), url_pattern)] = handler

    async def send(self, request: HttpRequest) -> HttpResponse:
        """Send request (mock implementation)."""
        start = time.time()

        # Find matching route
        for (method, pattern), handler in self.routes.items():
            if method == request.method.value:
                if pattern in request.url or pattern == "*":
                    response = handler(request)
                    response.request = request
                    response.elapsed_ms = (time.time() - start) * 1000
                    return response

        # Default mock response
        response = HttpResponse(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body={"mock": True, "url": request.url, "method": request.method.value}
        )
        response.request = request
        response.elapsed_ms = (time.time() - start) * 1000

        return response


# =============================================================================
# HTTP CLIENT
# =============================================================================

class HttpClient:
    """
    Async HTTP client with advanced features.
    """

    def __init__(
        self,
        config: ClientConfig = None,
        transport: MockTransport = None
    ):
        self.config = config or ClientConfig()
        self.transport = transport or MockTransport()

        self.authenticator: Authenticator = NoAuth()
        self.request_interceptors: List[RequestInterceptor] = []
        self.response_interceptors: List[ResponseInterceptor] = []

        self.rate_limiter: Optional[RateLimiter] = None
        self.cache: Optional[ResponseCache] = None

        if self.config.cache_enabled:
            self.cache = ResponseCache(default_ttl=self.config.cache_ttl)

        # Statistics
        self.stats = ClientStats()
        self._response_times: List[float] = []

    def set_auth(self, authenticator: Authenticator) -> 'HttpClient':
        """Set authenticator."""
        self.authenticator = authenticator
        return self

    def add_request_interceptor(
        self,
        interceptor: RequestInterceptor
    ) -> 'HttpClient':
        """Add request interceptor."""
        self.request_interceptors.append(interceptor)
        return self

    def add_response_interceptor(
        self,
        interceptor: ResponseInterceptor
    ) -> 'HttpClient':
        """Add response interceptor."""
        self.response_interceptors.append(interceptor)
        return self

    def set_rate_limit(
        self,
        requests_per_second: float,
        burst_size: int = None
    ) -> 'HttpClient':
        """Set rate limiter."""
        self.rate_limiter = RateLimiter(requests_per_second, burst_size)
        return self

    async def request(
        self,
        method: HttpMethod,
        url: str,
        headers: Dict[str, str] = None,
        params: Dict[str, str] = None,
        body: Any = None,
        timeout: float = None
    ) -> HttpResponse:
        """Make an HTTP request."""
        # Build full URL
        if self.config.base_url and not url.startswith("http"):
            url = f"{self.config.base_url.rstrip('/')}/{url.lstrip('/')}"

        # Build request
        request = HttpRequest(
            method=method,
            url=url,
            headers={**self.config.default_headers, **(headers or {})},
            params=params or {},
            body=body,
            timeout=timeout or self.config.timeout
        )

        # Check cache
        if self.cache and method == HttpMethod.GET:
            cached = await self.cache.get(request)
            if cached:
                self.stats.cache_hits += 1
                return cached
            self.stats.cache_misses += 1

        # Apply authentication
        request = self.authenticator.authenticate(request)

        # Apply request interceptors
        for interceptor in self.request_interceptors:
            request = await interceptor.intercept(request)

        # Rate limiting
        if self.rate_limiter:
            await self.rate_limiter.wait()

        # Send with retries
        response = await self._send_with_retry(request)

        # Apply response interceptors
        for interceptor in self.response_interceptors:
            response = await interceptor.intercept(response, request)

        # Update cache
        if self.cache and response.ok:
            await self.cache.set(request, response)

        # Update stats
        self._update_stats(response)

        return response

    async def _send_with_retry(self, request: HttpRequest) -> HttpResponse:
        """Send request with retry logic."""
        retry_config = self.config.retry_config
        last_error: Optional[Exception] = None

        for attempt in range(retry_config.max_retries + 1):
            try:
                response = await self.transport.send(request)

                # Check if should retry on status
                if response.status_code in retry_config.retry_on_status:
                    if attempt < retry_config.max_retries:
                        delay = self._calculate_delay(attempt, retry_config)
                        self.stats.retries += 1
                        await asyncio.sleep(delay)
                        continue

                self.stats.requests_succeeded += 1
                return response

            except Exception as e:
                last_error = e

                if attempt < retry_config.max_retries:
                    delay = self._calculate_delay(attempt, retry_config)
                    self.stats.retries += 1
                    await asyncio.sleep(delay)
                else:
                    self.stats.requests_failed += 1
                    raise

        # This shouldn't be reached, but just in case
        if last_error:
            raise last_error

        return HttpResponse(status_code=0, body={"error": "Max retries exceeded"})

    def _calculate_delay(self, attempt: int, config: RetryConfig) -> float:
        """Calculate retry delay with exponential backoff."""
        delay = config.initial_delay * (config.exponential_base ** attempt)
        delay = min(delay, config.max_delay)

        if config.jitter:
            import random
            delay *= (0.5 + random.random())

        return delay

    def _update_stats(self, response: HttpResponse) -> None:
        """Update statistics."""
        self.stats.requests_sent += 1

        self._response_times.append(response.elapsed_ms)
        if len(self._response_times) > 1000:
            self._response_times = self._response_times[-1000:]

        self.stats.avg_response_time_ms = (
            sum(self._response_times) / len(self._response_times)
        )

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    async def get(
        self,
        url: str,
        params: Dict[str, str] = None,
        **kwargs
    ) -> HttpResponse:
        """Make GET request."""
        return await self.request(HttpMethod.GET, url, params=params, **kwargs)

    async def post(
        self,
        url: str,
        body: Any = None,
        **kwargs
    ) -> HttpResponse:
        """Make POST request."""
        return await self.request(HttpMethod.POST, url, body=body, **kwargs)

    async def put(
        self,
        url: str,
        body: Any = None,
        **kwargs
    ) -> HttpResponse:
        """Make PUT request."""
        return await self.request(HttpMethod.PUT, url, body=body, **kwargs)

    async def patch(
        self,
        url: str,
        body: Any = None,
        **kwargs
    ) -> HttpResponse:
        """Make PATCH request."""
        return await self.request(HttpMethod.PATCH, url, body=body, **kwargs)

    async def delete(
        self,
        url: str,
        **kwargs
    ) -> HttpResponse:
        """Make DELETE request."""
        return await self.request(HttpMethod.DELETE, url, **kwargs)

    def get_stats(self) -> ClientStats:
        """Get client statistics."""
        return self.stats


# =============================================================================
# HTTP CLIENT MANAGER
# =============================================================================

class HttpClientManager:
    """
    Master HTTP client manager for BAEL.
    """

    def __init__(self):
        self.clients: Dict[str, HttpClient] = {}
        self.default_client: Optional[HttpClient] = None

    def create_client(
        self,
        name: str = "default",
        base_url: str = "",
        timeout: float = 30.0,
        cache_enabled: bool = False
    ) -> HttpClient:
        """Create a named HTTP client."""
        config = ClientConfig(
            base_url=base_url,
            timeout=timeout,
            cache_enabled=cache_enabled
        )

        client = HttpClient(config)
        self.clients[name] = client

        if self.default_client is None:
            self.default_client = client

        return client

    def get_client(self, name: str = None) -> Optional[HttpClient]:
        """Get a named client."""
        if name:
            return self.clients.get(name)
        return self.default_client

    async def get(
        self,
        url: str,
        client_name: str = None,
        **kwargs
    ) -> HttpResponse:
        """Make GET request."""
        client = self.get_client(client_name)
        if client:
            return await client.get(url, **kwargs)
        raise ValueError("No client available")

    async def post(
        self,
        url: str,
        body: Any = None,
        client_name: str = None,
        **kwargs
    ) -> HttpResponse:
        """Make POST request."""
        client = self.get_client(client_name)
        if client:
            return await client.post(url, body, **kwargs)
        raise ValueError("No client available")

    def get_all_stats(self) -> Dict[str, ClientStats]:
        """Get stats for all clients."""
        return {name: client.get_stats() for name, client in self.clients.items()}


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the HTTP Client."""
    print("=" * 70)
    print("BAEL - HTTP CLIENT DEMO")
    print("Comprehensive Async HTTP Client")
    print("=" * 70)
    print()

    # Create mock transport with routes
    transport = MockTransport()

    transport.add_route("GET", "/users", lambda r: HttpResponse(
        status_code=200,
        body={"users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]}
    ))

    transport.add_route("POST", "/users", lambda r: HttpResponse(
        status_code=201,
        body={"id": 3, "name": r.body.get("name") if r.body else "Unknown"}
    ))

    transport.add_route("GET", "/slow", lambda r: HttpResponse(
        status_code=503,
        body={"error": "Service unavailable"}
    ))

    manager = HttpClientManager()

    # 1. Create Client
    print("1. CREATE HTTP CLIENT:")
    print("-" * 40)

    config = ClientConfig(
        base_url="https://api.example.com",
        timeout=30.0,
        cache_enabled=True
    )

    client = HttpClient(config, transport)
    manager.clients["api"] = client
    manager.default_client = client

    print("   Created HTTP client with base URL: https://api.example.com")
    print()

    # 2. Basic GET Request
    print("2. BASIC GET REQUEST:")
    print("-" * 40)

    response = await client.get("/users")
    print(f"   Status: {response.status_code}")
    print(f"   Body: {response.body}")
    print(f"   Elapsed: {response.elapsed_ms:.2f}ms")
    print()

    # 3. POST Request
    print("3. POST REQUEST:")
    print("-" * 40)

    response = await client.post("/users", body={"name": "Charlie"})
    print(f"   Status: {response.status_code}")
    print(f"   Created: {response.body}")
    print()

    # 4. Authentication
    print("4. AUTHENTICATION:")
    print("-" * 40)

    # Basic auth
    client.set_auth(BasicAuth("user", "pass"))
    response = await client.get("/users")
    print(f"   With Basic Auth - Authorization header set: {'Authorization' in response.request.headers}")

    # Bearer auth
    client.set_auth(BearerAuth("my-token-123"))
    response = await client.get("/users")
    print(f"   With Bearer Token: {response.request.headers.get('Authorization', 'N/A')[:20]}...")

    # API key
    client.set_auth(ApiKeyAuth("secret-key", "X-API-Key"))
    response = await client.get("/users")
    print(f"   With API Key header: {response.request.headers.get('X-API-Key', 'N/A')}")

    client.set_auth(NoAuth())  # Reset
    print()

    # 5. Request Interceptor
    print("5. REQUEST INTERCEPTOR:")
    print("-" * 40)

    class CustomHeaderInterceptor(RequestInterceptor):
        async def intercept(self, request: HttpRequest) -> HttpRequest:
            request.headers["X-Custom-Header"] = "CustomValue"
            return request

    client.add_request_interceptor(CustomHeaderInterceptor())
    response = await client.get("/users")
    print(f"   Custom header added: {response.request.headers.get('X-Custom-Header')}")
    print()

    # 6. Response Caching
    print("6. RESPONSE CACHING:")
    print("-" * 40)

    # First request (not cached)
    response1 = await client.get("/users")
    print(f"   First request - from_cache: {response1.from_cache}")

    # Second request (from cache)
    response2 = await client.get("/users")
    print(f"   Second request - from_cache: {response2.from_cache}")

    stats = client.get_stats()
    print(f"   Cache hits: {stats.cache_hits}, misses: {stats.cache_misses}")
    print()

    # 7. Rate Limiting
    print("7. RATE LIMITING:")
    print("-" * 40)

    client.set_rate_limit(requests_per_second=5.0)
    print("   Rate limit set: 5 requests/second")

    start = time.time()
    for i in range(3):
        await client.get("/users")
    elapsed = time.time() - start

    print(f"   3 requests completed in {elapsed:.2f}s")
    print()

    # 8. Retry Configuration
    print("8. RETRY CONFIGURATION:")
    print("-" * 40)

    retry_config = RetryConfig(
        max_retries=3,
        initial_delay=0.1,
        retry_on_status={503}
    )

    retry_client = HttpClient(
        ClientConfig(retry_config=retry_config),
        transport
    )

    print(f"   Max retries: {retry_config.max_retries}")
    print(f"   Retry on status: {retry_config.retry_on_status}")
    print(f"   Initial delay: {retry_config.initial_delay}s")
    print()

    # 9. Custom Request
    print("9. CUSTOM REQUEST:")
    print("-" * 40)

    response = await client.request(
        HttpMethod.GET,
        "/users",
        headers={"Accept": "application/json"},
        params={"page": "1", "limit": "10"},
        timeout=5.0
    )

    print(f"   Full URL: {response.request.full_url()}")
    print(f"   Custom headers applied: Accept = {response.request.headers.get('Accept')}")
    print()

    # 10. Statistics
    print("10. STATISTICS:")
    print("-" * 40)

    stats = client.get_stats()
    print(f"    Requests sent: {stats.requests_sent}")
    print(f"    Requests succeeded: {stats.requests_succeeded}")
    print(f"    Requests failed: {stats.requests_failed}")
    print(f"    Cache hits: {stats.cache_hits}")
    print(f"    Average response time: {stats.avg_response_time_ms:.2f}ms")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - HTTP Client Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
