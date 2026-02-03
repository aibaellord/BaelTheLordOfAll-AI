#!/usr/bin/env python3
"""
BAEL - API Gateway System
Comprehensive API gateway and routing framework.

This module provides a complete API gateway
for request routing and management.

Features:
- Route matching (exact, prefix, regex)
- Request/response transformation
- Rate limiting
- Authentication middleware
- Load balancing
- Request validation
- Caching
- Logging and metrics
- Timeout handling
- Error handling
"""

import asyncio
import hashlib
import json
import logging
import re
import time
import traceback
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import (Any, Callable, Coroutine, Dict, List, Optional, Pattern,
                    Set, Tuple, Type, TypeVar, Union)
from urllib.parse import parse_qs, urlparse

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
    ANY = "*"


class RouteType(Enum):
    """Route matching types."""
    EXACT = "exact"
    PREFIX = "prefix"
    REGEX = "regex"
    PARAMETER = "parameter"


class LoadBalanceStrategy(Enum):
    """Load balancing strategies."""
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED = "weighted"


class AuthType(Enum):
    """Authentication types."""
    NONE = "none"
    API_KEY = "api_key"
    BEARER = "bearer"
    BASIC = "basic"
    CUSTOM = "custom"


class CacheStrategy(Enum):
    """Caching strategies."""
    NONE = "none"
    MEMORY = "memory"
    DISTRIBUTED = "distributed"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Request:
    """HTTP request representation."""
    method: HttpMethod
    path: str
    headers: Dict[str, str] = field(default_factory=dict)
    query_params: Dict[str, List[str]] = field(default_factory=dict)
    body: Optional[bytes] = None

    # Parsed data
    path_params: Dict[str, str] = field(default_factory=dict)
    json_body: Optional[Dict] = None

    # Metadata
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    client_ip: str = ""

    def get_header(self, name: str, default: str = None) -> Optional[str]:
        return self.headers.get(name, self.headers.get(name.lower(), default))

    def get_query(self, name: str, default: str = None) -> Optional[str]:
        values = self.query_params.get(name, [])
        return values[0] if values else default

    def parse_json(self) -> Optional[Dict]:
        if self.json_body is None and self.body:
            try:
                self.json_body = json.loads(self.body.decode('utf-8'))
            except:
                pass
        return self.json_body


@dataclass
class Response:
    """HTTP response representation."""
    status: int = 200
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[bytes] = None

    # Metadata
    duration_ms: float = 0.0

    @classmethod
    def json(cls, data: Any, status: int = 200) -> 'Response':
        body = json.dumps(data).encode('utf-8')
        return cls(
            status=status,
            headers={"Content-Type": "application/json"},
            body=body
        )

    @classmethod
    def text(cls, text: str, status: int = 200) -> 'Response':
        return cls(
            status=status,
            headers={"Content-Type": "text/plain"},
            body=text.encode('utf-8')
        )

    @classmethod
    def error(cls, message: str, status: int = 500) -> 'Response':
        return cls.json({"error": message}, status)


@dataclass
class RouteConfig:
    """Route configuration."""
    path: str
    methods: List[HttpMethod] = field(default_factory=lambda: [HttpMethod.ANY])
    route_type: RouteType = RouteType.EXACT

    # Backend
    backend: Optional[str] = None
    backends: List[str] = field(default_factory=list)
    load_balance: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN

    # Options
    timeout: float = 30.0
    retry: int = 0

    # Auth
    auth: AuthType = AuthType.NONE
    auth_config: Dict[str, Any] = field(default_factory=dict)

    # Cache
    cache: CacheStrategy = CacheStrategy.NONE
    cache_ttl: float = 60.0

    # Rate limiting
    rate_limit: Optional[int] = None  # requests per minute

    # Transformations
    request_transform: Optional[str] = None
    response_transform: Optional[str] = None


@dataclass
class Route:
    """Registered route."""
    config: RouteConfig
    handler: Optional[Callable] = None
    pattern: Optional[Pattern] = None
    param_names: List[str] = field(default_factory=list)

    # Load balancer state
    current_backend: int = 0
    backend_connections: Dict[str, int] = field(default_factory=dict)


@dataclass
class GatewayStats:
    """Gateway statistics."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_duration: float = 0.0

    # Per route
    route_stats: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: {"count": 0, "errors": 0}))


# =============================================================================
# MIDDLEWARE
# =============================================================================

class Middleware(ABC):
    """Abstract middleware."""

    @abstractmethod
    async def process_request(
        self,
        request: Request,
        context: Dict[str, Any]
    ) -> Optional[Response]:
        """Process request. Return Response to short-circuit."""
        pass

    async def process_response(
        self,
        request: Request,
        response: Response,
        context: Dict[str, Any]
    ) -> Response:
        """Process response."""
        return response


class LoggingMiddleware(Middleware):
    """Request/response logging."""

    async def process_request(
        self,
        request: Request,
        context: Dict[str, Any]
    ) -> Optional[Response]:
        context['start_time'] = time.time()
        logger.info(f"Request: {request.method.value} {request.path}")
        return None

    async def process_response(
        self,
        request: Request,
        response: Response,
        context: Dict[str, Any]
    ) -> Response:
        duration = (time.time() - context.get('start_time', 0)) * 1000
        logger.info(f"Response: {response.status} ({duration:.1f}ms)")
        return response


class CorsMiddleware(Middleware):
    """CORS handling."""

    def __init__(
        self,
        origins: List[str] = None,
        methods: List[str] = None,
        headers: List[str] = None
    ):
        self.origins = origins or ["*"]
        self.methods = methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.headers = headers or ["Content-Type", "Authorization"]

    async def process_request(
        self,
        request: Request,
        context: Dict[str, Any]
    ) -> Optional[Response]:
        # Handle preflight
        if request.method == HttpMethod.OPTIONS:
            return Response(
                status=204,
                headers=self._get_cors_headers(request)
            )
        return None

    async def process_response(
        self,
        request: Request,
        response: Response,
        context: Dict[str, Any]
    ) -> Response:
        response.headers.update(self._get_cors_headers(request))
        return response

    def _get_cors_headers(self, request: Request) -> Dict[str, str]:
        origin = request.get_header("Origin", "*")

        if "*" in self.origins or origin in self.origins:
            return {
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Methods": ", ".join(self.methods),
                "Access-Control-Allow-Headers": ", ".join(self.headers),
                "Access-Control-Max-Age": "86400"
            }
        return {}


class RateLimitMiddleware(Middleware):
    """Rate limiting."""

    def __init__(self, default_limit: int = 100):
        self.default_limit = default_limit
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.window = 60  # seconds

    async def process_request(
        self,
        request: Request,
        context: Dict[str, Any]
    ) -> Optional[Response]:
        route = context.get('route')
        limit = route.config.rate_limit if route else self.default_limit

        if not limit:
            return None

        key = self._get_key(request)
        now = time.time()

        # Clean old requests
        while self.requests[key] and self.requests[key][0] < now - self.window:
            self.requests[key].popleft()

        if len(self.requests[key]) >= limit:
            return Response.error("Rate limit exceeded", 429)

        self.requests[key].append(now)
        return None

    def _get_key(self, request: Request) -> str:
        return f"{request.client_ip}:{request.path}"


class AuthMiddleware(Middleware):
    """Authentication middleware."""

    def __init__(self):
        self.api_keys: Set[str] = set()
        self.validators: Dict[AuthType, Callable] = {}

    def add_api_key(self, key: str) -> None:
        self.api_keys.add(key)

    def set_validator(
        self,
        auth_type: AuthType,
        validator: Callable[[Request, Dict], bool]
    ) -> None:
        self.validators[auth_type] = validator

    async def process_request(
        self,
        request: Request,
        context: Dict[str, Any]
    ) -> Optional[Response]:
        route = context.get('route')
        if not route or route.config.auth == AuthType.NONE:
            return None

        auth_type = route.config.auth

        if auth_type == AuthType.API_KEY:
            return await self._validate_api_key(request, route.config.auth_config)

        elif auth_type == AuthType.BEARER:
            return await self._validate_bearer(request, route.config.auth_config)

        elif auth_type == AuthType.BASIC:
            return await self._validate_basic(request, route.config.auth_config)

        elif auth_type == AuthType.CUSTOM:
            validator = self.validators.get(AuthType.CUSTOM)
            if validator and not validator(request, route.config.auth_config):
                return Response.error("Unauthorized", 401)

        return None

    async def _validate_api_key(
        self,
        request: Request,
        config: Dict
    ) -> Optional[Response]:
        header = config.get('header', 'X-API-Key')
        key = request.get_header(header)

        if not key or key not in self.api_keys:
            return Response.error("Invalid API key", 401)
        return None

    async def _validate_bearer(
        self,
        request: Request,
        config: Dict
    ) -> Optional[Response]:
        auth = request.get_header('Authorization', '')

        if not auth.startswith('Bearer '):
            return Response.error("Missing bearer token", 401)

        token = auth[7:]
        # Validate token (simplified)
        if not token:
            return Response.error("Invalid token", 401)

        return None

    async def _validate_basic(
        self,
        request: Request,
        config: Dict
    ) -> Optional[Response]:
        import base64

        auth = request.get_header('Authorization', '')

        if not auth.startswith('Basic '):
            return Response.error("Missing basic auth", 401)

        try:
            encoded = auth[6:]
            decoded = base64.b64decode(encoded).decode('utf-8')
            username, password = decoded.split(':', 1)

            expected_user = config.get('username')
            expected_pass = config.get('password')

            if username != expected_user or password != expected_pass:
                return Response.error("Invalid credentials", 401)
        except:
            return Response.error("Invalid auth header", 401)

        return None


# =============================================================================
# CACHING
# =============================================================================

class Cache(ABC):
    """Abstract cache."""

    @abstractmethod
    async def get(self, key: str) -> Optional[bytes]:
        pass

    @abstractmethod
    async def set(self, key: str, value: bytes, ttl: float) -> None:
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        pass


class MemoryCache(Cache):
    """In-memory cache."""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: Dict[str, Tuple[bytes, float]] = {}
        self.access_order: deque = deque()

    async def get(self, key: str) -> Optional[bytes]:
        if key not in self.cache:
            return None

        value, expires = self.cache[key]

        if time.time() > expires:
            await self.delete(key)
            return None

        return value

    async def set(self, key: str, value: bytes, ttl: float) -> None:
        # Evict if full
        while len(self.cache) >= self.max_size and self.access_order:
            old_key = self.access_order.popleft()
            if old_key in self.cache:
                del self.cache[old_key]

        expires = time.time() + ttl
        self.cache[key] = (value, expires)
        self.access_order.append(key)

    async def delete(self, key: str) -> None:
        if key in self.cache:
            del self.cache[key]


class CacheMiddleware(Middleware):
    """Response caching."""

    def __init__(self, cache: Cache = None):
        self.cache = cache or MemoryCache()

    async def process_request(
        self,
        request: Request,
        context: Dict[str, Any]
    ) -> Optional[Response]:
        route = context.get('route')
        if not route or route.config.cache == CacheStrategy.NONE:
            return None

        # Only cache GET requests
        if request.method != HttpMethod.GET:
            return None

        key = self._cache_key(request)
        cached = await self.cache.get(key)

        if cached:
            context['cached'] = True
            return Response(
                status=200,
                headers={"X-Cache": "HIT"},
                body=cached
            )

        return None

    async def process_response(
        self,
        request: Request,
        response: Response,
        context: Dict[str, Any]
    ) -> Response:
        if context.get('cached'):
            return response

        route = context.get('route')
        if not route or route.config.cache == CacheStrategy.NONE:
            return response

        if request.method != HttpMethod.GET or response.status != 200:
            return response

        key = self._cache_key(request)
        if response.body:
            await self.cache.set(key, response.body, route.config.cache_ttl)

        response.headers["X-Cache"] = "MISS"
        return response

    def _cache_key(self, request: Request) -> str:
        data = f"{request.method.value}:{request.path}:{json.dumps(request.query_params, sort_keys=True)}"
        return hashlib.sha256(data.encode()).hexdigest()


# =============================================================================
# ROUTER
# =============================================================================

class Router:
    """Request router."""

    def __init__(self):
        self.routes: List[Route] = []
        self.default_handler: Optional[Callable] = None

    def add_route(
        self,
        path: str,
        handler: Callable = None,
        methods: List[HttpMethod] = None,
        **kwargs
    ) -> Route:
        """Add a route."""
        config = RouteConfig(
            path=path,
            methods=methods or [HttpMethod.ANY],
            **kwargs
        )

        route = Route(config=config, handler=handler)

        # Parse route type and pattern
        if '{' in path or '<' in path:
            route.config.route_type = RouteType.PARAMETER
            route.pattern, route.param_names = self._compile_param_pattern(path)
        elif path.endswith('*'):
            route.config.route_type = RouteType.PREFIX
            route.pattern = re.compile(f"^{re.escape(path[:-1])}")
        elif config.route_type == RouteType.REGEX:
            route.pattern = re.compile(path)

        self.routes.append(route)
        return route

    def _compile_param_pattern(self, path: str) -> Tuple[Pattern, List[str]]:
        """Compile parameterized path to regex."""
        param_names = []

        # Convert {param} or <param> to regex groups
        def replace(match):
            param_names.append(match.group(1))
            return r'([^/]+)'

        pattern = re.sub(r'\{(\w+)\}|<(\w+)>', lambda m: replace(m) if m.group(1) else replace(type('M', (), {'group': lambda s, i: m.group(2)})()), path)
        pattern = f"^{pattern}$"

        return re.compile(pattern), param_names

    def match(self, request: Request) -> Optional[Route]:
        """Find matching route."""
        for route in self.routes:
            if self._matches(route, request):
                return route
        return None

    def _matches(self, route: Route, request: Request) -> bool:
        """Check if route matches request."""
        # Check method
        if HttpMethod.ANY not in route.config.methods:
            if request.method not in route.config.methods:
                return False

        # Check path
        if route.config.route_type == RouteType.EXACT:
            if request.path != route.config.path:
                return False

        elif route.config.route_type == RouteType.PREFIX:
            if not request.path.startswith(route.config.path.rstrip('*')):
                return False

        elif route.pattern:
            match = route.pattern.match(request.path)
            if not match:
                return False

            # Extract path params
            if route.param_names:
                for i, name in enumerate(route.param_names):
                    request.path_params[name] = match.group(i + 1)

        return True

    # Decorator helpers
    def get(self, path: str, **kwargs) -> Callable:
        def decorator(func: Callable) -> Callable:
            self.add_route(path, func, [HttpMethod.GET], **kwargs)
            return func
        return decorator

    def post(self, path: str, **kwargs) -> Callable:
        def decorator(func: Callable) -> Callable:
            self.add_route(path, func, [HttpMethod.POST], **kwargs)
            return func
        return decorator

    def put(self, path: str, **kwargs) -> Callable:
        def decorator(func: Callable) -> Callable:
            self.add_route(path, func, [HttpMethod.PUT], **kwargs)
            return func
        return decorator

    def delete(self, path: str, **kwargs) -> Callable:
        def decorator(func: Callable) -> Callable:
            self.add_route(path, func, [HttpMethod.DELETE], **kwargs)
            return func
        return decorator


# =============================================================================
# LOAD BALANCER
# =============================================================================

class LoadBalancer:
    """Backend load balancer."""

    def __init__(self, strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN):
        self.strategy = strategy
        self.backends: List[str] = []
        self.weights: Dict[str, int] = {}
        self.current_index = 0
        self.connections: Dict[str, int] = defaultdict(int)

    def add_backend(self, url: str, weight: int = 1) -> None:
        self.backends.append(url)
        self.weights[url] = weight

    def get_backend(self) -> Optional[str]:
        if not self.backends:
            return None

        if self.strategy == LoadBalanceStrategy.ROUND_ROBIN:
            return self._round_robin()

        elif self.strategy == LoadBalanceStrategy.RANDOM:
            return self._random()

        elif self.strategy == LoadBalanceStrategy.LEAST_CONNECTIONS:
            return self._least_connections()

        elif self.strategy == LoadBalanceStrategy.WEIGHTED:
            return self._weighted()

        return self._round_robin()

    def _round_robin(self) -> str:
        backend = self.backends[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.backends)
        return backend

    def _random(self) -> str:
        import random
        return random.choice(self.backends)

    def _least_connections(self) -> str:
        return min(self.backends, key=lambda b: self.connections.get(b, 0))

    def _weighted(self) -> str:
        import random
        total = sum(self.weights.get(b, 1) for b in self.backends)
        r = random.uniform(0, total)

        cumulative = 0
        for backend in self.backends:
            cumulative += self.weights.get(backend, 1)
            if r <= cumulative:
                return backend

        return self.backends[-1]

    def record_connection(self, backend: str) -> None:
        self.connections[backend] += 1

    def record_disconnection(self, backend: str) -> None:
        self.connections[backend] = max(0, self.connections[backend] - 1)


# =============================================================================
# API GATEWAY
# =============================================================================

class APIGateway:
    """
    Master API gateway for BAEL.

    Provides comprehensive request routing and processing.
    """

    def __init__(self):
        self.router = Router()
        self.middleware: List[Middleware] = []
        self.load_balancers: Dict[str, LoadBalancer] = {}
        self.stats = GatewayStats()

        # Transformers
        self.request_transformers: Dict[str, Callable] = {}
        self.response_transformers: Dict[str, Callable] = {}

    # Configuration
    def use(self, middleware: Middleware) -> 'APIGateway':
        """Add middleware."""
        self.middleware.append(middleware)
        return self

    def route(
        self,
        path: str,
        methods: List[HttpMethod] = None,
        **kwargs
    ) -> Callable:
        """Route decorator."""
        def decorator(func: Callable) -> Callable:
            self.router.add_route(path, func, methods, **kwargs)
            return func
        return decorator

    def add_route(
        self,
        path: str,
        handler: Callable = None,
        **kwargs
    ) -> Route:
        """Add a route."""
        return self.router.add_route(path, handler, **kwargs)

    def add_load_balancer(
        self,
        name: str,
        backends: List[str],
        strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN
    ) -> LoadBalancer:
        """Add a load balancer."""
        lb = LoadBalancer(strategy)
        for backend in backends:
            lb.add_backend(backend)
        self.load_balancers[name] = lb
        return lb

    def add_transformer(
        self,
        name: str,
        request_fn: Callable = None,
        response_fn: Callable = None
    ) -> None:
        """Add request/response transformers."""
        if request_fn:
            self.request_transformers[name] = request_fn
        if response_fn:
            self.response_transformers[name] = response_fn

    # Processing
    async def handle(self, request: Request) -> Response:
        """Handle incoming request."""
        start = time.time()
        context: Dict[str, Any] = {}

        try:
            # Match route
            route = self.router.match(request)
            context['route'] = route

            # Process request middleware
            for mw in self.middleware:
                response = await mw.process_request(request, context)
                if response:
                    return await self._process_response_middleware(request, response, context)

            # No route found
            if not route:
                self.stats.failed_requests += 1
                return Response.error("Not Found", 404)

            # Transform request
            if route.config.request_transform:
                transformer = self.request_transformers.get(route.config.request_transform)
                if transformer:
                    request = await self._call(transformer, request)

            # Execute handler or proxy
            if route.handler:
                response = await self._execute_handler(route, request, context)
            elif route.config.backend or route.config.backends:
                response = await self._proxy_request(route, request, context)
            else:
                response = Response.error("No handler configured", 500)

            # Transform response
            if route.config.response_transform:
                transformer = self.response_transformers.get(route.config.response_transform)
                if transformer:
                    response = await self._call(transformer, response)

            # Update stats
            self.stats.total_requests += 1
            if response.status < 400:
                self.stats.successful_requests += 1
            else:
                self.stats.failed_requests += 1

            self.stats.route_stats[route.config.path]["count"] += 1
            if response.status >= 400:
                self.stats.route_stats[route.config.path]["errors"] += 1

        except Exception as e:
            logger.error(f"Gateway error: {e}")
            self.stats.failed_requests += 1
            response = Response.error(str(e), 500)

        response.duration_ms = (time.time() - start) * 1000
        self.stats.total_duration += response.duration_ms

        return await self._process_response_middleware(request, response, context)

    async def _execute_handler(
        self,
        route: Route,
        request: Request,
        context: Dict[str, Any]
    ) -> Response:
        """Execute route handler."""
        try:
            if route.config.timeout:
                result = await asyncio.wait_for(
                    self._call(route.handler, request),
                    timeout=route.config.timeout
                )
            else:
                result = await self._call(route.handler, request)

            if isinstance(result, Response):
                return result
            elif isinstance(result, dict):
                return Response.json(result)
            elif isinstance(result, str):
                return Response.text(result)
            else:
                return Response.json({"result": result})

        except asyncio.TimeoutError:
            return Response.error("Request timeout", 504)
        except Exception as e:
            logger.error(f"Handler error: {e}")
            return Response.error(str(e), 500)

    async def _proxy_request(
        self,
        route: Route,
        request: Request,
        context: Dict[str, Any]
    ) -> Response:
        """Proxy request to backend."""
        # Get backend URL
        if route.config.backends:
            lb_name = route.config.path
            if lb_name not in self.load_balancers:
                lb = LoadBalancer(route.config.load_balance)
                for backend in route.config.backends:
                    lb.add_backend(backend)
                self.load_balancers[lb_name] = lb

            backend = self.load_balancers[lb_name].get_backend()
        else:
            backend = route.config.backend

        if not backend:
            return Response.error("No backend available", 503)

        # In a real implementation, this would make an HTTP request
        # For demo purposes, we return a simulated response
        return Response.json({
            "proxied_to": backend,
            "path": request.path,
            "method": request.method.value
        })

    async def _process_response_middleware(
        self,
        request: Request,
        response: Response,
        context: Dict[str, Any]
    ) -> Response:
        """Process response through middleware."""
        for mw in reversed(self.middleware):
            response = await mw.process_response(request, response, context)
        return response

    async def _call(self, func: Callable, *args, **kwargs) -> Any:
        """Call function (async or sync)."""
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        return func(*args, **kwargs)

    # Statistics
    def get_stats(self) -> Dict[str, Any]:
        """Get gateway statistics."""
        return {
            "total_requests": self.stats.total_requests,
            "successful_requests": self.stats.successful_requests,
            "failed_requests": self.stats.failed_requests,
            "avg_duration_ms": self.stats.total_duration / max(self.stats.total_requests, 1),
            "success_rate": self.stats.successful_requests / max(self.stats.total_requests, 1),
            "routes": dict(self.stats.route_stats)
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the API Gateway System."""
    print("=" * 70)
    print("BAEL - API GATEWAY SYSTEM DEMO")
    print("Comprehensive Request Routing and Processing")
    print("=" * 70)
    print()

    gateway = APIGateway()

    # 1. Add Middleware
    print("1. ADDING MIDDLEWARE:")
    print("-" * 40)

    gateway.use(LoggingMiddleware())
    print("   Added: LoggingMiddleware")

    gateway.use(CorsMiddleware(origins=["http://localhost:3000"]))
    print("   Added: CorsMiddleware")

    gateway.use(RateLimitMiddleware(default_limit=100))
    print("   Added: RateLimitMiddleware")

    auth = AuthMiddleware()
    auth.add_api_key("test-api-key-123")
    gateway.use(auth)
    print("   Added: AuthMiddleware")

    gateway.use(CacheMiddleware())
    print("   Added: CacheMiddleware")
    print()

    # 2. Add Routes
    print("2. ADDING ROUTES:")
    print("-" * 40)

    @gateway.route("/health", methods=[HttpMethod.GET])
    async def health_check(request: Request) -> Response:
        return Response.json({"status": "healthy"})
    print("   Route: GET /health")

    @gateway.route("/users/{id}", methods=[HttpMethod.GET])
    async def get_user(request: Request) -> Response:
        user_id = request.path_params.get("id")
        return Response.json({"user_id": user_id, "name": f"User {user_id}"})
    print("   Route: GET /users/{id}")

    @gateway.route("/api/*", methods=[HttpMethod.ANY], route_type=RouteType.PREFIX)
    async def api_handler(request: Request) -> Response:
        return Response.json({"path": request.path, "method": request.method.value})
    print("   Route: * /api/*")

    gateway.add_route(
        "/protected",
        handler=lambda r: Response.json({"secret": "data"}),
        methods=[HttpMethod.GET],
        auth=AuthType.API_KEY
    )
    print("   Route: GET /protected (auth required)")

    gateway.add_route(
        "/cached",
        handler=lambda r: Response.json({"time": str(datetime.now())}),
        methods=[HttpMethod.GET],
        cache=CacheStrategy.MEMORY,
        cache_ttl=60
    )
    print("   Route: GET /cached (cached)")
    print()

    # 3. Test Routes
    print("3. TESTING ROUTES:")
    print("-" * 40)

    # Health check
    request = Request(method=HttpMethod.GET, path="/health")
    response = await gateway.handle(request)
    print(f"   GET /health -> {response.status}")

    # User endpoint
    request = Request(method=HttpMethod.GET, path="/users/123")
    response = await gateway.handle(request)
    data = json.loads(response.body.decode())
    print(f"   GET /users/123 -> {data}")

    # Prefix matching
    request = Request(method=HttpMethod.POST, path="/api/v1/items")
    response = await gateway.handle(request)
    print(f"   POST /api/v1/items -> {response.status}")

    # Not found
    request = Request(method=HttpMethod.GET, path="/unknown")
    response = await gateway.handle(request)
    print(f"   GET /unknown -> {response.status}")
    print()

    # 4. Authentication
    print("4. AUTHENTICATION:")
    print("-" * 40)

    # Without API key
    request = Request(method=HttpMethod.GET, path="/protected")
    response = await gateway.handle(request)
    print(f"   Without key: {response.status}")

    # With API key
    request = Request(
        method=HttpMethod.GET,
        path="/protected",
        headers={"X-API-Key": "test-api-key-123"}
    )
    response = await gateway.handle(request)
    print(f"   With key: {response.status}")
    print()

    # 5. Caching
    print("5. CACHING:")
    print("-" * 40)

    request = Request(method=HttpMethod.GET, path="/cached")
    response1 = await gateway.handle(request)
    cache_header1 = response1.headers.get("X-Cache", "NONE")

    response2 = await gateway.handle(request)
    cache_header2 = response2.headers.get("X-Cache", "NONE")

    print(f"   First request: {cache_header1}")
    print(f"   Second request: {cache_header2}")
    print()

    # 6. Load Balancing
    print("6. LOAD BALANCING:")
    print("-" * 40)

    lb = gateway.add_load_balancer(
        "api-backends",
        ["http://backend1:8080", "http://backend2:8080", "http://backend3:8080"],
        LoadBalanceStrategy.ROUND_ROBIN
    )

    for i in range(5):
        backend = lb.get_backend()
        print(f"   Request {i+1}: {backend}")
    print()

    # 7. Request Transformation
    print("7. REQUEST TRANSFORMATION:")
    print("-" * 40)

    def add_request_id(request: Request) -> Request:
        request.headers["X-Request-ID"] = str(uuid.uuid4())
        return request

    gateway.add_transformer("add_id", request_fn=add_request_id)

    gateway.add_route(
        "/transform",
        handler=lambda r: Response.json({"request_id": r.headers.get("X-Request-ID")}),
        methods=[HttpMethod.GET],
        request_transform="add_id"
    )

    request = Request(method=HttpMethod.GET, path="/transform")
    response = await gateway.handle(request)
    data = json.loads(response.body.decode())
    print(f"   Added request ID: {data.get('request_id', 'N/A')[:8]}...")
    print()

    # 8. Rate Limiting
    print("8. RATE LIMITING:")
    print("-" * 40)

    gateway.add_route(
        "/limited",
        handler=lambda r: Response.json({"ok": True}),
        methods=[HttpMethod.GET],
        rate_limit=5
    )

    limited_count = 0
    for i in range(7):
        request = Request(
            method=HttpMethod.GET,
            path="/limited",
            client_ip="192.168.1.1"
        )
        response = await gateway.handle(request)
        if response.status == 429:
            limited_count += 1
        print(f"   Request {i+1}: {response.status}")

    print(f"   Rate limited: {limited_count} requests")
    print()

    # 9. CORS
    print("9. CORS:")
    print("-" * 40)

    request = Request(
        method=HttpMethod.OPTIONS,
        path="/health",
        headers={"Origin": "http://localhost:3000"}
    )
    response = await gateway.handle(request)

    print(f"   Preflight status: {response.status}")
    print(f"   Allow-Origin: {response.headers.get('Access-Control-Allow-Origin')}")
    print()

    # 10. Statistics
    print("10. GATEWAY STATISTICS:")
    print("-" * 40)

    stats = gateway.get_stats()
    print(f"    Total requests: {stats['total_requests']}")
    print(f"    Successful: {stats['successful_requests']}")
    print(f"    Failed: {stats['failed_requests']}")
    print(f"    Avg duration: {stats['avg_duration_ms']:.2f}ms")
    print(f"    Success rate: {stats['success_rate']:.1%}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - API Gateway System Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
