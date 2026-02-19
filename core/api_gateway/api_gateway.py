"""
BAEL API Gateway
================

Unified API gateway for all BAEL services.

Features:
- Route management
- Middleware chains
- Rate limiting
- Authentication
- Request/response transformation
- Caching
- CORS handling

"Every request flows through the Lord's gate." — Ba'el
"""

import asyncio
import hashlib
import json
import logging
import re
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Pattern, Set, Tuple, Union
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger("BAEL.APIGateway")


# =============================================================================
# ENUMS
# =============================================================================

class RouteMethod(Enum):
    """HTTP methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    OPTIONS = "OPTIONS"
    HEAD = "HEAD"
    ANY = "*"


class AuthType(Enum):
    """Authentication types."""
    NONE = "none"
    API_KEY = "api_key"
    BEARER = "bearer"
    BASIC = "basic"
    JWT = "jwt"
    CUSTOM = "custom"


class RateLimitStrategy(Enum):
    """Rate limiting strategies."""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"


class ResponseFormat(Enum):
    """Response formats."""
    JSON = "json"
    XML = "xml"
    TEXT = "text"
    HTML = "html"
    BINARY = "binary"


class CacheStrategy(Enum):
    """Caching strategies."""
    NO_CACHE = "no_cache"
    MEMORY = "memory"
    DISK = "disk"
    REDIS = "redis"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_size: int = 10
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    by_ip: bool = True
    by_api_key: bool = True


@dataclass
class CORSConfig:
    """CORS configuration."""
    enabled: bool = True
    allow_origins: List[str] = field(default_factory=lambda: ["*"])
    allow_methods: List[str] = field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    allow_headers: List[str] = field(default_factory=lambda: ["*"])
    expose_headers: List[str] = field(default_factory=list)
    max_age: int = 86400
    allow_credentials: bool = False


@dataclass
class AuthConfig:
    """Authentication configuration."""
    auth_type: AuthType = AuthType.NONE
    api_keys: List[str] = field(default_factory=list)
    jwt_secret: Optional[str] = None
    custom_validator: Optional[Callable] = None


@dataclass
class Route:
    """API route definition."""
    path: str
    method: RouteMethod
    handler: Callable
    name: Optional[str] = None
    description: Optional[str] = None
    auth_required: bool = False
    rate_limit: Optional[RateLimitConfig] = None
    cache_ttl: Optional[int] = None
    middleware: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    _pattern: Optional[Pattern] = field(default=None, repr=False)
    _param_names: List[str] = field(default_factory=list, repr=False)

    def __post_init__(self):
        """Compile route pattern."""
        # Convert path params like {id} to regex groups
        pattern = self.path
        params = []

        for match in re.finditer(r'\{(\w+)\}', self.path):
            param_name = match.group(1)
            params.append(param_name)
            pattern = pattern.replace(f'{{{param_name}}}', r'(?P<' + param_name + r'>[^/]+)')

        self._pattern = re.compile(f'^{pattern}$')
        self._param_names = params

    def matches(self, path: str, method: str) -> Optional[Dict[str, str]]:
        """Check if route matches path and method."""
        if self.method != RouteMethod.ANY and self.method.value != method:
            return None

        match = self._pattern.match(path)
        if match:
            return match.groupdict()
        return None


@dataclass
class Middleware:
    """Middleware definition."""
    name: str
    handler: Callable
    order: int = 50
    apply_to: List[str] = field(default_factory=lambda: ["*"])
    skip_for: List[str] = field(default_factory=list)


@dataclass
class Request:
    """HTTP request wrapper."""
    method: str
    path: str
    query_params: Dict[str, List[str]] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    body: bytes = b""
    json_body: Optional[Dict] = None
    path_params: Dict[str, str] = field(default_factory=dict)
    client_ip: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    request_id: str = ""

    def get_header(self, name: str, default: str = "") -> str:
        """Get header value (case-insensitive)."""
        for key, value in self.headers.items():
            if key.lower() == name.lower():
                return value
        return default

    def get_query(self, name: str, default: str = "") -> str:
        """Get query parameter."""
        values = self.query_params.get(name, [])
        return values[0] if values else default


@dataclass
class Response:
    """HTTP response wrapper."""
    status_code: int = 200
    body: Any = None
    headers: Dict[str, str] = field(default_factory=dict)
    content_type: str = "application/json"

    def to_bytes(self) -> bytes:
        """Convert response to bytes."""
        if self.body is None:
            return b""

        if isinstance(self.body, bytes):
            return self.body

        if isinstance(self.body, str):
            return self.body.encode('utf-8')

        if self.content_type == "application/json":
            return json.dumps(self.body).encode('utf-8')

        return str(self.body).encode('utf-8')


@dataclass
class GatewayConfig:
    """API Gateway configuration."""
    host: str = "0.0.0.0"
    port: int = 8080
    cors: CORSConfig = field(default_factory=CORSConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    cache_strategy: CacheStrategy = CacheStrategy.MEMORY
    request_timeout: float = 30.0
    max_request_size: int = 10 * 1024 * 1024  # 10MB


# =============================================================================
# RATE LIMITER
# =============================================================================

class RateLimiter:
    """Request rate limiter."""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._requests: Dict[str, List[float]] = defaultdict(list)
        self._tokens: Dict[str, float] = defaultdict(lambda: config.burst_size)
        self._last_refill: Dict[str, float] = defaultdict(time.time)
        self._lock = threading.Lock()

    def check(self, key: str) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is allowed."""
        now = time.time()

        with self._lock:
            if self.config.strategy == RateLimitStrategy.SLIDING_WINDOW:
                return self._sliding_window(key, now)
            elif self.config.strategy == RateLimitStrategy.TOKEN_BUCKET:
                return self._token_bucket(key, now)
            else:
                return self._fixed_window(key, now)

    def _sliding_window(self, key: str, now: float) -> Tuple[bool, Dict[str, Any]]:
        """Sliding window rate limiting."""
        window = 60.0  # 1 minute
        limit = self.config.requests_per_minute

        # Remove old requests
        self._requests[key] = [
            t for t in self._requests[key]
            if now - t < window
        ]

        if len(self._requests[key]) >= limit:
            retry_after = self._requests[key][0] + window - now
            return False, {
                "limit": limit,
                "remaining": 0,
                "reset": retry_after
            }

        self._requests[key].append(now)
        return True, {
            "limit": limit,
            "remaining": limit - len(self._requests[key]),
            "reset": window
        }

    def _fixed_window(self, key: str, now: float) -> Tuple[bool, Dict[str, Any]]:
        """Fixed window rate limiting."""
        window_start = int(now / 60) * 60  # Current minute
        window_key = f"{key}:{window_start}"

        count = len([t for t in self._requests[window_key] if True])

        if count >= self.config.requests_per_minute:
            return False, {
                "limit": self.config.requests_per_minute,
                "remaining": 0,
                "reset": window_start + 60 - now
            }

        self._requests[window_key].append(now)
        return True, {
            "limit": self.config.requests_per_minute,
            "remaining": self.config.requests_per_minute - count - 1,
            "reset": window_start + 60 - now
        }

    def _token_bucket(self, key: str, now: float) -> Tuple[bool, Dict[str, Any]]:
        """Token bucket rate limiting."""
        # Refill tokens
        elapsed = now - self._last_refill[key]
        refill_rate = self.config.requests_per_minute / 60.0
        new_tokens = elapsed * refill_rate

        self._tokens[key] = min(
            self.config.burst_size,
            self._tokens[key] + new_tokens
        )
        self._last_refill[key] = now

        if self._tokens[key] < 1:
            wait_time = (1 - self._tokens[key]) / refill_rate
            return False, {
                "limit": self.config.burst_size,
                "remaining": 0,
                "reset": wait_time
            }

        self._tokens[key] -= 1
        return True, {
            "limit": self.config.burst_size,
            "remaining": int(self._tokens[key]),
            "reset": 0
        }


# =============================================================================
# AUTH HANDLER
# =============================================================================

class AuthHandler:
    """Request authentication handler."""

    def __init__(self, config: AuthConfig):
        self.config = config
        self._api_keys = set(config.api_keys)

    def authenticate(self, request: Request) -> Tuple[bool, Optional[str]]:
        """Authenticate a request."""
        if self.config.auth_type == AuthType.NONE:
            return True, None

        if self.config.auth_type == AuthType.API_KEY:
            return self._auth_api_key(request)

        if self.config.auth_type == AuthType.BEARER:
            return self._auth_bearer(request)

        if self.config.auth_type == AuthType.BASIC:
            return self._auth_basic(request)

        if self.config.auth_type == AuthType.CUSTOM:
            return self._auth_custom(request)

        return False, "Unknown auth type"

    def _auth_api_key(self, request: Request) -> Tuple[bool, Optional[str]]:
        """API key authentication."""
        # Check header
        api_key = request.get_header("X-API-Key")

        # Check query param
        if not api_key:
            api_key = request.get_query("api_key")

        if not api_key:
            return False, "API key required"

        if api_key not in self._api_keys:
            return False, "Invalid API key"

        return True, None

    def _auth_bearer(self, request: Request) -> Tuple[bool, Optional[str]]:
        """Bearer token authentication."""
        auth_header = request.get_header("Authorization")

        if not auth_header:
            return False, "Authorization header required"

        if not auth_header.startswith("Bearer "):
            return False, "Invalid authorization format"

        token = auth_header[7:]

        # Simple token validation (extend for JWT)
        if len(token) < 10:
            return False, "Invalid token"

        return True, None

    def _auth_basic(self, request: Request) -> Tuple[bool, Optional[str]]:
        """Basic authentication."""
        auth_header = request.get_header("Authorization")

        if not auth_header:
            return False, "Authorization header required"

        if not auth_header.startswith("Basic "):
            return False, "Invalid authorization format"

        # Decode would happen here
        return True, None

    def _auth_custom(self, request: Request) -> Tuple[bool, Optional[str]]:
        """Custom authentication."""
        if self.config.custom_validator:
            try:
                result = self.config.custom_validator(request)
                if result:
                    return True, None
                return False, "Authentication failed"
            except Exception as e:
                return False, str(e)

        return False, "No custom validator configured"

    def add_api_key(self, key: str):
        """Add an API key."""
        self._api_keys.add(key)

    def remove_api_key(self, key: str):
        """Remove an API key."""
        self._api_keys.discard(key)


# =============================================================================
# RESPONSE HANDLER
# =============================================================================

class ResponseHandler:
    """Response formatting and transformation."""

    def __init__(self):
        self._transformers: Dict[str, Callable] = {}

    def success(
        self,
        data: Any = None,
        message: str = "Success",
        status_code: int = 200
    ) -> Response:
        """Create success response."""
        return Response(
            status_code=status_code,
            body={
                "success": True,
                "message": message,
                "data": data
            }
        )

    def error(
        self,
        message: str = "Error",
        status_code: int = 400,
        errors: Optional[List[str]] = None
    ) -> Response:
        """Create error response."""
        return Response(
            status_code=status_code,
            body={
                "success": False,
                "message": message,
                "errors": errors or []
            }
        )

    def not_found(self, message: str = "Resource not found") -> Response:
        """Create 404 response."""
        return self.error(message, 404)

    def unauthorized(self, message: str = "Unauthorized") -> Response:
        """Create 401 response."""
        return self.error(message, 401)

    def rate_limited(self, retry_after: float) -> Response:
        """Create rate limit response."""
        response = self.error("Rate limit exceeded", 429)
        response.headers["Retry-After"] = str(int(retry_after))
        return response


# =============================================================================
# ROUTER
# =============================================================================

class Router:
    """Route management."""

    def __init__(self):
        self._routes: List[Route] = []
        self._named_routes: Dict[str, Route] = {}

    def add(self, route: Route):
        """Add a route."""
        self._routes.append(route)
        if route.name:
            self._named_routes[route.name] = route

    def remove(self, path: str, method: Optional[RouteMethod] = None):
        """Remove a route."""
        self._routes = [
            r for r in self._routes
            if not (r.path == path and (method is None or r.method == method))
        ]

    def match(self, path: str, method: str) -> Optional[Tuple[Route, Dict[str, str]]]:
        """Find matching route."""
        for route in self._routes:
            params = route.matches(path, method)
            if params is not None:
                return route, params
        return None

    def get(
        self,
        path: str,
        handler: Callable,
        **kwargs
    ) -> Route:
        """Add GET route."""
        route = Route(path=path, method=RouteMethod.GET, handler=handler, **kwargs)
        self.add(route)
        return route

    def post(
        self,
        path: str,
        handler: Callable,
        **kwargs
    ) -> Route:
        """Add POST route."""
        route = Route(path=path, method=RouteMethod.POST, handler=handler, **kwargs)
        self.add(route)
        return route

    def put(
        self,
        path: str,
        handler: Callable,
        **kwargs
    ) -> Route:
        """Add PUT route."""
        route = Route(path=path, method=RouteMethod.PUT, handler=handler, **kwargs)
        self.add(route)
        return route

    def delete(
        self,
        path: str,
        handler: Callable,
        **kwargs
    ) -> Route:
        """Add DELETE route."""
        route = Route(path=path, method=RouteMethod.DELETE, handler=handler, **kwargs)
        self.add(route)
        return route

    def list_routes(self) -> List[Dict[str, Any]]:
        """List all routes."""
        return [
            {
                "path": r.path,
                "method": r.method.value,
                "name": r.name,
                "description": r.description,
                "auth_required": r.auth_required,
                "tags": r.tags
            }
            for r in self._routes
        ]


# =============================================================================
# MIDDLEWARE CHAIN
# =============================================================================

class MiddlewareChain:
    """Middleware execution chain."""

    def __init__(self):
        self._middleware: List[Middleware] = []

    def add(self, middleware: Middleware):
        """Add middleware."""
        self._middleware.append(middleware)
        self._middleware.sort(key=lambda m: m.order)

    def remove(self, name: str):
        """Remove middleware."""
        self._middleware = [m for m in self._middleware if m.name != name]

    async def execute(
        self,
        request: Request,
        final_handler: Callable
    ) -> Response:
        """Execute middleware chain."""
        index = 0

        async def next_handler() -> Response:
            nonlocal index

            while index < len(self._middleware):
                middleware = self._middleware[index]
                index += 1

                # Check if middleware applies
                if self._should_apply(middleware, request.path):
                    result = middleware.handler(request, next_handler)
                    if asyncio.iscoroutine(result):
                        return await result
                    return result

            # Call final handler
            result = final_handler(request)
            if asyncio.iscoroutine(result):
                return await result
            return result

        return await next_handler()

    def _should_apply(self, middleware: Middleware, path: str) -> bool:
        """Check if middleware should apply to path."""
        # Check skip list
        for pattern in middleware.skip_for:
            if self._matches_pattern(pattern, path):
                return False

        # Check apply list
        for pattern in middleware.apply_to:
            if pattern == "*" or self._matches_pattern(pattern, path):
                return True

        return False

    def _matches_pattern(self, pattern: str, path: str) -> bool:
        """Check if path matches pattern."""
        if pattern == "*":
            return True

        # Simple wildcard matching
        regex = pattern.replace("*", ".*")
        return bool(re.match(f"^{regex}$", path))


# =============================================================================
# API GATEWAY
# =============================================================================

class APIGateway:
    """Main API Gateway."""

    def __init__(self, config: Optional[GatewayConfig] = None):
        self.config = config or GatewayConfig()

        self.router = Router()
        self.middleware = MiddlewareChain()
        self.rate_limiter = RateLimiter(self.config.rate_limit)
        self.auth = AuthHandler(self.config.auth)
        self.responses = ResponseHandler()

        self._cache: Dict[str, Tuple[Response, float]] = {}
        self._running = False
        self._server = None

        # Add default routes
        self._setup_default_routes()

        # Add default middleware
        self._setup_default_middleware()

    def _setup_default_routes(self):
        """Setup default routes."""
        # Health check
        self.router.get(
            "/health",
            lambda req: self.responses.success({"status": "healthy"}),
            name="health",
            description="Health check endpoint"
        )

        # API info
        self.router.get(
            "/api",
            lambda req: self.responses.success({
                "name": "BAEL API Gateway",
                "version": "3.0.0",
                "routes": len(self.router._routes)
            }),
            name="api_info",
            description="API information"
        )

        # Routes list
        self.router.get(
            "/api/routes",
            lambda req: self.responses.success(self.router.list_routes()),
            name="routes",
            description="List all routes"
        )

    def _setup_default_middleware(self):
        """Setup default middleware."""
        # Request logging
        async def logging_middleware(request: Request, next_handler: Callable) -> Response:
            start = time.time()
            response = await next_handler()
            duration = (time.time() - start) * 1000
            logger.info(
                f"{request.method} {request.path} - {response.status_code} ({duration:.2f}ms)"
            )
            return response

        self.middleware.add(Middleware(
            name="logging",
            handler=logging_middleware,
            order=1
        ))

        # CORS
        async def cors_middleware(request: Request, next_handler: Callable) -> Response:
            if not self.config.cors.enabled:
                return await next_handler()

            # Handle preflight
            if request.method == "OPTIONS":
                return Response(
                    status_code=204,
                    headers={
                        "Access-Control-Allow-Origin": ",".join(self.config.cors.allow_origins),
                        "Access-Control-Allow-Methods": ",".join(self.config.cors.allow_methods),
                        "Access-Control-Allow-Headers": ",".join(self.config.cors.allow_headers),
                        "Access-Control-Max-Age": str(self.config.cors.max_age)
                    }
                )

            response = await next_handler()
            response.headers["Access-Control-Allow-Origin"] = ",".join(self.config.cors.allow_origins)
            return response

        self.middleware.add(Middleware(
            name="cors",
            handler=cors_middleware,
            order=5
        ))

        # Request ID
        async def request_id_middleware(request: Request, next_handler: Callable) -> Response:
            if not request.request_id:
                request.request_id = hashlib.md5(
                    f"{time.time()}{request.path}".encode()
                ).hexdigest()[:12]

            response = await next_handler()
            response.headers["X-Request-ID"] = request.request_id
            return response

        self.middleware.add(Middleware(
            name="request_id",
            handler=request_id_middleware,
            order=2
        ))

    async def handle_request(self, request: Request) -> Response:
        """Handle an incoming request."""
        try:
            # Find matching route
            match = self.router.match(request.path, request.method)

            if not match:
                return self.responses.not_found(f"No route for {request.method} {request.path}")

            route, params = match
            request.path_params = params

            # Check rate limiting
            if route.rate_limit or self.config.rate_limit:
                rate_config = route.rate_limit or self.config.rate_limit
                limiter = RateLimiter(rate_config)
                key = request.client_ip or "default"
                allowed, info = limiter.check(key)

                if not allowed:
                    return self.responses.rate_limited(info.get("reset", 60))

            # Check authentication
            if route.auth_required:
                authenticated, error = self.auth.authenticate(request)
                if not authenticated:
                    return self.responses.unauthorized(error or "Unauthorized")

            # Check cache
            cache_key = f"{request.method}:{request.path}"
            if route.cache_ttl and cache_key in self._cache:
                cached_response, cached_time = self._cache[cache_key]
                if time.time() - cached_time < route.cache_ttl:
                    cached_response.headers["X-Cache"] = "HIT"
                    return cached_response

            # Execute through middleware chain
            async def final_handler(req: Request) -> Response:
                result = route.handler(req)
                if asyncio.iscoroutine(result):
                    return await result
                if isinstance(result, Response):
                    return result
                return self.responses.success(result)

            response = await self.middleware.execute(request, final_handler)

            # Cache response
            if route.cache_ttl:
                self._cache[cache_key] = (response, time.time())
                response.headers["X-Cache"] = "MISS"

            return response

        except Exception as e:
            logger.error(f"Request error: {e}")
            return self.responses.error(str(e), 500)

    def route(
        self,
        path: str,
        method: RouteMethod = RouteMethod.GET,
        **kwargs
    ):
        """Decorator to add a route."""
        def decorator(handler: Callable) -> Callable:
            route = Route(
                path=path,
                method=method,
                handler=handler,
                name=kwargs.get("name", handler.__name__),
                **{k: v for k, v in kwargs.items() if k != "name"}
            )
            self.router.add(route)
            return handler
        return decorator

    def get(self, path: str, **kwargs):
        """Decorator for GET route."""
        return self.route(path, RouteMethod.GET, **kwargs)

    def post(self, path: str, **kwargs):
        """Decorator for POST route."""
        return self.route(path, RouteMethod.POST, **kwargs)

    def put(self, path: str, **kwargs):
        """Decorator for PUT route."""
        return self.route(path, RouteMethod.PUT, **kwargs)

    def delete(self, path: str, **kwargs):
        """Decorator for DELETE route."""
        return self.route(path, RouteMethod.DELETE, **kwargs)

    def use(self, handler: Callable, order: int = 50, **kwargs):
        """Add middleware."""
        name = kwargs.get("name", f"middleware_{len(self.middleware._middleware)}")
        self.middleware.add(Middleware(
            name=name,
            handler=handler,
            order=order,
            **{k: v for k, v in kwargs.items() if k != "name"}
        ))

    async def start(self):
        """Start the API gateway."""
        self._running = True
        logger.info(f"API Gateway starting on {self.config.host}:{self.config.port}")

        # Note: In production, use proper async server like aiohttp or fastapi
        # This is a minimal implementation

    async def stop(self):
        """Stop the API gateway."""
        self._running = False
        logger.info("API Gateway stopped")

    def get_status(self) -> Dict[str, Any]:
        """Get gateway status."""
        return {
            "running": self._running,
            "host": self.config.host,
            "port": self.config.port,
            "routes": len(self.router._routes),
            "middleware": len(self.middleware._middleware),
            "cache_size": len(self._cache),
            "auth_type": self.config.auth.auth_type.value
        }


# =============================================================================
# CONVENIENCE INSTANCE
# =============================================================================

api_gateway = APIGateway()
