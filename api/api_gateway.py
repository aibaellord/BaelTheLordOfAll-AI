"""
Advanced API Gateway & Router for BAEL

Provides intelligent request routing, rate limiting, caching,
compression, versioning, and advanced API features.
"""

import asyncio
import gzip
import hashlib
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HTTPMethod(Enum):
    """HTTP methods"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class CacheStrategy(Enum):
    """Caching strategies"""
    NO_CACHE = "no_cache"
    PRIVATE = "private"
    PUBLIC = "public"
    MAX_AGE = "max_age"


@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    max_requests: int
    window_seconds: int
    burst_size: int = 0
    per_user: bool = False
    per_ip: bool = False


@dataclass
class CacheConfig:
    """Cache configuration for route"""
    enabled: bool = True
    ttl_seconds: int = 300
    strategy: CacheStrategy = CacheStrategy.PUBLIC
    vary_by: List[str] = field(default_factory=list)
    compression_enabled: bool = True


@dataclass
class Request:
    """API request"""
    request_id: str
    method: HTTPMethod
    path: str
    version: str
    headers: Dict[str, str] = field(default_factory=dict)
    query_params: Dict[str, Any] = field(default_factory=dict)
    body: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def get_cache_key(self, vary_by: List[str] = None) -> str:
        """Generate cache key for request"""
        parts = [self.method.value, self.path, self.version]

        if vary_by:
            for param in vary_by:
                if param in self.query_params:
                    parts.append(str(self.query_params[param]))
                elif param in self.headers:
                    parts.append(self.headers[param])

        key_str = "|".join(parts)
        return hashlib.sha256(key_str.encode()).hexdigest()


@dataclass
class Response:
    """API response"""
    status_code: int = 200
    data: Optional[Dict[str, Any]] = None
    headers: Dict[str, str] = field(default_factory=dict)
    cache_config: Optional[CacheConfig] = None
    compression_enabled: bool = True
    timestamp: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status_code,
            "data": self.data,
            "error": self.error,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class Route:
    """API route configuration"""
    path: str
    methods: List[HTTPMethod]
    handler: Callable
    version: str = "v1"
    rate_limit: Optional[RateLimitConfig] = None
    cache_config: Optional[CacheConfig] = None
    requires_auth: bool = False
    description: str = ""
    tags: List[str] = field(default_factory=list)


class RateLimiter:
    """Rate limiting implementation"""

    def __init__(self):
        self.limits: Dict[str, deque] = defaultdict(deque)

    def is_allowed(self, key: str, config: RateLimitConfig) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is allowed under rate limit"""
        now = time.time()
        window_start = now - config.window_seconds

        # Clean old requests
        while self.limits[key] and self.limits[key][0] < window_start:
            self.limits[key].popleft()

        # Check limit
        request_count = len(self.limits[key])

        if request_count >= config.max_requests:
            reset_at = self.limits[key][0] + config.window_seconds
            return False, {
                "limit": config.max_requests,
                "remaining": 0,
                "reset_at": reset_at,
                "retry_after": int(reset_at - now)
            }

        # Record request
        self.limits[key].append(now)

        return True, {
            "limit": config.max_requests,
            "remaining": config.max_requests - request_count - 1,
            "reset_at": window_start + config.window_seconds,
            "retry_after": None
        }


class ResponseCache:
    """Caches API responses"""

    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, Tuple[Response, float]] = {}
        self.max_size = max_size

    def get(self, cache_key: str) -> Optional[Response]:
        """Get cached response"""
        if cache_key not in self.cache:
            return None

        response, expires_at = self.cache[cache_key]

        if time.time() > expires_at:
            del self.cache[cache_key]
            return None

        return response

    def set(self, cache_key: str, response: Response, ttl_seconds: int):
        """Cache response"""
        if len(self.cache) >= self.max_size:
            # Simple eviction: remove oldest
            oldest_key = min(self.cache.keys(),
                           key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]

        expires_at = time.time() + ttl_seconds
        self.cache[cache_key] = (response, expires_at)

    def clear(self):
        """Clear all cache"""
        self.cache.clear()


class ResponseCompressor:
    """Compresses API responses"""

    @staticmethod
    def should_compress(data: str, min_size_bytes: int = 1024) -> bool:
        """Check if response should be compressed"""
        return len(data.encode()) >= min_size_bytes

    @staticmethod
    def compress_gzip(data: str, level: int = 6) -> bytes:
        """Compress using gzip"""
        return gzip.compress(data.encode(), compresslevel=level)

    @staticmethod
    def decompress_gzip(data: bytes) -> str:
        """Decompress gzip data"""
        return gzip.decompress(data).decode()


class AuthenticationHandler:
    """Handles API authentication"""

    def __init__(self):
        self.valid_keys: Dict[str, Dict[str, Any]] = {}
        self.tokens: Dict[str, Tuple[str, float]] = {}  # token -> (user_id, expires_at)

    def register_api_key(self, key: str, user_id: str, scopes: List[str] = None):
        """Register API key"""
        self.valid_keys[key] = {
            "user_id": user_id,
            "scopes": scopes or [],
            "created_at": datetime.now().isoformat(),
            "active": True
        }
        logger.info(f"Registered API key for user {user_id}")

    def validate_api_key(self, key: str) -> Tuple[bool, Optional[str]]:
        """Validate API key"""
        if key not in self.valid_keys:
            return False, None

        key_info = self.valid_keys[key]
        if not key_info["active"]:
            return False, None

        return True, key_info["user_id"]

    def generate_token(self, user_id: str, expires_in_seconds: int = 3600) -> str:
        """Generate authentication token"""
        token = str(uuid.uuid4())
        expires_at = time.time() + expires_in_seconds
        self.tokens[token] = (user_id, expires_at)
        return token

    def validate_token(self, token: str) -> Tuple[bool, Optional[str]]:
        """Validate authentication token"""
        if token not in self.tokens:
            return False, None

        user_id, expires_at = self.tokens[token]

        if time.time() > expires_at:
            del self.tokens[token]
            return False, None

        return True, user_id


class APIGateway:
    """Main API gateway"""

    def __init__(self):
        self.routes: Dict[str, List[Route]] = defaultdict(list)
        self.rate_limiter = RateLimiter()
        self.cache = ResponseCache()
        self.compressor = ResponseCompressor()
        self.auth = AuthenticationHandler()
        self.request_history: deque = deque(maxlen=10000)
        self.metrics: Dict[str, Any] = {
            "total_requests": 0,
            "cache_hits": 0,
            "rate_limit_hits": 0,
            "errors": 0
        }

    def register_route(self, route: Route):
        """Register API route"""
        self.routes[route.path].append(route)
        logger.info(f"Registered route: {route.path} {route.methods}")

    def get_routes(self, version: str = None) -> List[Route]:
        """Get routes"""
        routes = []
        for path_routes in self.routes.values():
            for route in path_routes:
                if version is None or route.version == version:
                    routes.append(route)
        return routes

    async def handle_request(self, request: Request) -> Response:
        """Handle API request"""
        self.request_history.append(request)
        self.metrics["total_requests"] += 1

        logger.info(f"Request: {request.method.value} {request.path} (ID: {request.request_id})")

        # Check cache
        matching_routes = self._find_matching_routes(request)
        if not matching_routes:
            return Response(status_code=404, error="Route not found")

        route = matching_routes[0]

        # Check cache
        if route.cache_config and route.cache_config.enabled:
            cache_key = request.get_cache_key(route.cache_config.vary_by)
            cached_response = self.cache.get(cache_key)
            if cached_response:
                self.metrics["cache_hits"] += 1
                logger.debug(f"Cache hit for {request.path}")
                return cached_response

        # Check authentication
        if route.requires_auth:
            valid, user_id = self._authenticate(request)
            if not valid:
                return Response(status_code=401, error="Unauthorized")
            request.user_id = user_id

        # Check rate limit
        if route.rate_limit:
            rate_limit_key = self._get_rate_limit_key(request, route)
            allowed, limit_info = self.rate_limiter.is_allowed(
                rate_limit_key,
                route.rate_limit
            )
            if not allowed:
                self.metrics["rate_limit_hits"] += 1
                logger.warning(f"Rate limit exceeded for {rate_limit_key}")
                return Response(
                    status_code=429,
                    error="Too many requests",
                    headers={
                        "Retry-After": str(limit_info["retry_after"])
                    }
                )

        # Call handler
        try:
            response = await self._call_handler(route.handler, request)

            # Cache response
            if route.cache_config and route.cache_config.enabled:
                cache_key = request.get_cache_key(route.cache_config.vary_by)
                self.cache.set(cache_key, response, route.cache_config.ttl_seconds)

            # Compress response
            if response.compression_enabled and response.data:
                response_json = json.dumps(response.to_dict())
                if self.compressor.should_compress(response_json):
                    compressed = self.compressor.compress_gzip(response_json)
                    response.headers["Content-Encoding"] = "gzip"

            return response

        except Exception as e:
            self.metrics["errors"] += 1
            logger.error(f"Error handling request: {e}")
            return Response(status_code=500, error=str(e))

    def _find_matching_routes(self, request: Request) -> List[Route]:
        """Find matching routes for request"""
        matching = []

        for path, routes in self.routes.items():
            if self._path_matches(request.path, path):
                for route in routes:
                    if request.method in route.methods:
                        matching.append(route)

        # Sort by version match
        matching.sort(key=lambda r: r.version == request.version, reverse=True)

        return matching

    def _path_matches(self, request_path: str, route_path: str) -> bool:
        """Check if request path matches route pattern"""
        # Simple pattern matching
        request_parts = request_path.split('/')
        route_parts = route_path.split('/')

        if len(request_parts) != len(route_parts):
            return False

        for req_part, route_part in zip(request_parts, route_parts):
            if route_part.startswith('{') and route_part.endswith('}'):
                continue
            if req_part != route_part:
                return False

        return True

    def _authenticate(self, request: Request) -> Tuple[bool, Optional[str]]:
        """Authenticate request"""
        auth_header = request.headers.get("Authorization", "")

        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            return self.auth.validate_token(token)

        if auth_header.startswith("ApiKey "):
            key = auth_header[7:]
            return self.auth.validate_api_key(key)

        return False, None

    def _get_rate_limit_key(self, request: Request, route: Route) -> str:
        """Get rate limit key"""
        if route.rate_limit.per_user and request.user_id:
            return f"user:{request.user_id}"
        if route.rate_limit.per_ip and request.ip_address:
            return f"ip:{request.ip_address}"
        return f"global"

    async def _call_handler(self, handler: Callable, request: Request) -> Response:
        """Call route handler"""
        if asyncio.iscoroutinefunction(handler):
            return await handler(request)
        else:
            return handler(request)

    def get_metrics(self) -> Dict[str, Any]:
        """Get gateway metrics"""
        return {
            **self.metrics,
            "cache_size": len(self.cache.cache),
            "routes_registered": sum(len(r) for r in self.routes.values()),
            "request_history_size": len(self.request_history)
        }

    def get_api_documentation(self) -> Dict[str, Any]:
        """Generate API documentation"""
        docs = {
            "title": "BAEL API",
            "version": "v1",
            "routes": []
        }

        for route in self.get_routes():
            docs["routes"].append({
                "path": route.path,
                "methods": [m.value for m in route.methods],
                "version": route.version,
                "description": route.description,
                "tags": route.tags,
                "requires_auth": route.requires_auth,
                "rate_limit": {
                    "max_requests": route.rate_limit.max_requests if route.rate_limit else None,
                    "window_seconds": route.rate_limit.window_seconds if route.rate_limit else None
                } if route.rate_limit else None
            })

        return docs


# Global gateway instance
_api_gateway = None


def get_api_gateway() -> APIGateway:
    """Get global API gateway"""
    global _api_gateway
    if _api_gateway is None:
        _api_gateway = APIGateway()
    return _api_gateway


if __name__ == "__main__":
    logger.info("API Gateway initialized")
