#!/usr/bin/env python3
"""
BAEL - Request Pipeline System
Comprehensive middleware and request processing pipeline.

Features:
- Middleware chain
- Request/Response transformation
- Error handling
- Validation
- Authentication
- Rate limiting
- Caching
- Compression
- Logging
- Metrics
"""

import asyncio
import gzip
import hashlib
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import (Any, Awaitable, Callable, Dict, Generic, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')


# =============================================================================
# ENUMS
# =============================================================================

class RequestMethod(Enum):
    """HTTP request methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class ResponseStatus(Enum):
    """Response status codes."""
    OK = 200
    CREATED = 201
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    TOO_MANY_REQUESTS = 429
    INTERNAL_ERROR = 500
    SERVICE_UNAVAILABLE = 503


class PipelinePhase(Enum):
    """Pipeline execution phases."""
    PRE_PROCESS = "pre_process"
    AUTHENTICATE = "authenticate"
    AUTHORIZE = "authorize"
    VALIDATE = "validate"
    TRANSFORM = "transform"
    EXECUTE = "execute"
    POST_PROCESS = "post_process"
    ERROR = "error"


class MiddlewarePriority(Enum):
    """Middleware priority levels."""
    CRITICAL = 0
    HIGH = 100
    NORMAL = 500
    LOW = 900
    LOWEST = 1000


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class RequestContext:
    """Request context."""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    method: RequestMethod = RequestMethod.GET
    path: str = "/"
    headers: Dict[str, str] = field(default_factory=dict)
    query_params: Dict[str, str] = field(default_factory=dict)
    body: Any = None
    user: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    started_at: float = field(default_factory=time.time)

    def get_header(self, name: str, default: str = None) -> Optional[str]:
        return self.headers.get(name.lower(), default)

    def set_header(self, name: str, value: str) -> None:
        self.headers[name.lower()] = value


@dataclass
class ResponseContext:
    """Response context."""
    status: ResponseStatus = ResponseStatus.OK
    headers: Dict[str, str] = field(default_factory=dict)
    body: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def set_header(self, name: str, value: str) -> None:
        self.headers[name.lower()] = value

    def add_error(self, error: str) -> None:
        self.errors.append(error)


@dataclass
class PipelineContext:
    """Pipeline execution context."""
    request: RequestContext
    response: ResponseContext = field(default_factory=ResponseContext)
    phase: PipelinePhase = PipelinePhase.PRE_PROCESS
    should_continue: bool = True
    timings: Dict[str, float] = field(default_factory=dict)

    def abort(self, status: ResponseStatus, error: str = None) -> None:
        """Abort pipeline execution."""
        self.should_continue = False
        self.response.status = status
        if error:
            self.response.add_error(error)


@dataclass
class MiddlewareStats:
    """Middleware statistics."""
    name: str
    invocations: int = 0
    total_time: float = 0.0
    errors: int = 0

    @property
    def avg_time(self) -> float:
        if self.invocations == 0:
            return 0.0
        return self.total_time / self.invocations


# =============================================================================
# MIDDLEWARE BASE
# =============================================================================

class Middleware(ABC):
    """Base middleware class."""

    name: str = "base"
    priority: int = MiddlewarePriority.NORMAL.value

    @abstractmethod
    async def process(
        self,
        context: PipelineContext,
        next_middleware: Callable[[PipelineContext], Awaitable[None]]
    ) -> None:
        """Process request through middleware."""
        pass

    async def on_error(
        self,
        context: PipelineContext,
        error: Exception
    ) -> None:
        """Handle errors."""
        pass


# =============================================================================
# BUILT-IN MIDDLEWARE
# =============================================================================

class LoggingMiddleware(Middleware):
    """Request/Response logging middleware."""

    name = "logging"
    priority = MiddlewarePriority.CRITICAL.value

    def __init__(self, log_body: bool = False):
        self.log_body = log_body

    async def process(
        self,
        context: PipelineContext,
        next_middleware: Callable[[PipelineContext], Awaitable[None]]
    ) -> None:
        request = context.request

        logger.info(
            f"[{request.request_id}] {request.method.value} {request.path}"
        )

        await next_middleware(context)

        duration = time.time() - request.started_at

        logger.info(
            f"[{request.request_id}] {context.response.status.value} "
            f"({duration*1000:.2f}ms)"
        )


class AuthenticationMiddleware(Middleware):
    """Authentication middleware."""

    name = "authentication"
    priority = MiddlewarePriority.HIGH.value

    def __init__(
        self,
        token_validator: Callable[[str], Optional[Dict[str, Any]]] = None,
        public_paths: List[str] = None
    ):
        self.token_validator = token_validator
        self.public_paths = public_paths or []

    async def process(
        self,
        context: PipelineContext,
        next_middleware: Callable[[PipelineContext], Awaitable[None]]
    ) -> None:
        # Skip public paths
        if context.request.path in self.public_paths:
            await next_middleware(context)
            return

        auth_header = context.request.get_header("authorization")

        if not auth_header:
            context.abort(ResponseStatus.UNAUTHORIZED, "Missing authorization")
            return

        # Extract token
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        else:
            token = auth_header

        # Validate token
        if self.token_validator:
            user = self.token_validator(token)

            if not user:
                context.abort(ResponseStatus.UNAUTHORIZED, "Invalid token")
                return

            context.request.user = user
        else:
            # Default: just accept any token
            context.request.user = {"token": token}

        await next_middleware(context)


class RateLimitMiddleware(Middleware):
    """Rate limiting middleware."""

    name = "rate_limit"
    priority = MiddlewarePriority.HIGH.value

    def __init__(
        self,
        requests_per_second: int = 10,
        burst: int = 20
    ):
        self.requests_per_second = requests_per_second
        self.burst = burst
        self.tokens: Dict[str, float] = defaultdict(lambda: burst)
        self.last_update: Dict[str, float] = {}

    def _get_client_id(self, context: PipelineContext) -> str:
        """Extract client identifier."""
        if context.request.user:
            return context.request.user.get("id", "anonymous")
        return context.request.get_header("x-client-id", "anonymous")

    async def process(
        self,
        context: PipelineContext,
        next_middleware: Callable[[PipelineContext], Awaitable[None]]
    ) -> None:
        client_id = self._get_client_id(context)
        now = time.time()

        # Token bucket algorithm
        if client_id in self.last_update:
            elapsed = now - self.last_update[client_id]
            self.tokens[client_id] = min(
                self.burst,
                self.tokens[client_id] + elapsed * self.requests_per_second
            )

        self.last_update[client_id] = now

        if self.tokens[client_id] < 1:
            context.response.set_header(
                "retry-after",
                str(int(1 / self.requests_per_second))
            )
            context.abort(ResponseStatus.TOO_MANY_REQUESTS, "Rate limit exceeded")
            return

        self.tokens[client_id] -= 1

        await next_middleware(context)


class CacheMiddleware(Middleware):
    """Response caching middleware."""

    name = "cache"
    priority = MiddlewarePriority.NORMAL.value

    def __init__(
        self,
        ttl: int = 300,
        cacheable_methods: List[RequestMethod] = None
    ):
        self.ttl = ttl
        self.cacheable_methods = cacheable_methods or [RequestMethod.GET]
        self.cache: Dict[str, Tuple[Any, float]] = {}

    def _get_cache_key(self, request: RequestContext) -> str:
        """Generate cache key."""
        key_parts = [
            request.method.value,
            request.path,
            json.dumps(request.query_params, sort_keys=True)
        ]
        return hashlib.md5(":".join(key_parts).encode()).hexdigest()

    async def process(
        self,
        context: PipelineContext,
        next_middleware: Callable[[PipelineContext], Awaitable[None]]
    ) -> None:
        request = context.request

        # Only cache specified methods
        if request.method not in self.cacheable_methods:
            await next_middleware(context)
            return

        cache_key = self._get_cache_key(request)

        # Check cache
        if cache_key in self.cache:
            cached_body, cached_at = self.cache[cache_key]

            if time.time() - cached_at < self.ttl:
                context.response.body = cached_body
                context.response.set_header("x-cache", "HIT")
                return

        await next_middleware(context)

        # Cache successful responses
        if context.response.status == ResponseStatus.OK:
            self.cache[cache_key] = (context.response.body, time.time())
            context.response.set_header("x-cache", "MISS")


class CompressionMiddleware(Middleware):
    """Response compression middleware."""

    name = "compression"
    priority = MiddlewarePriority.LOW.value

    def __init__(self, min_size: int = 1024):
        self.min_size = min_size

    async def process(
        self,
        context: PipelineContext,
        next_middleware: Callable[[PipelineContext], Awaitable[None]]
    ) -> None:
        await next_middleware(context)

        # Check if client accepts gzip
        accept_encoding = context.request.get_header("accept-encoding", "")

        if "gzip" not in accept_encoding:
            return

        body = context.response.body

        if body is None:
            return

        # Serialize if needed
        if not isinstance(body, (str, bytes)):
            body = json.dumps(body)

        if isinstance(body, str):
            body = body.encode()

        # Only compress if above threshold
        if len(body) < self.min_size:
            return

        compressed = gzip.compress(body)

        # Only use if smaller
        if len(compressed) < len(body):
            context.response.body = compressed
            context.response.set_header("content-encoding", "gzip")


class ValidationMiddleware(Middleware):
    """Request validation middleware."""

    name = "validation"
    priority = MiddlewarePriority.NORMAL.value

    def __init__(
        self,
        validators: Dict[str, Callable[[Any], List[str]]] = None
    ):
        self.validators = validators or {}

    def add_validator(
        self,
        path: str,
        validator: Callable[[Any], List[str]]
    ) -> None:
        """Add path validator."""
        self.validators[path] = validator

    async def process(
        self,
        context: PipelineContext,
        next_middleware: Callable[[PipelineContext], Awaitable[None]]
    ) -> None:
        path = context.request.path

        if path in self.validators:
            validator = self.validators[path]
            errors = validator(context.request.body)

            if errors:
                context.response.status = ResponseStatus.BAD_REQUEST
                context.response.body = {"errors": errors}
                context.abort(ResponseStatus.BAD_REQUEST, "; ".join(errors))
                return

        await next_middleware(context)


class CORSMiddleware(Middleware):
    """CORS handling middleware."""

    name = "cors"
    priority = MiddlewarePriority.CRITICAL.value

    def __init__(
        self,
        allowed_origins: List[str] = None,
        allowed_methods: List[str] = None,
        allowed_headers: List[str] = None,
        max_age: int = 86400
    ):
        self.allowed_origins = allowed_origins or ["*"]
        self.allowed_methods = allowed_methods or [
            "GET", "POST", "PUT", "DELETE", "OPTIONS"
        ]
        self.allowed_headers = allowed_headers or [
            "Content-Type", "Authorization"
        ]
        self.max_age = max_age

    async def process(
        self,
        context: PipelineContext,
        next_middleware: Callable[[PipelineContext], Awaitable[None]]
    ) -> None:
        origin = context.request.get_header("origin")

        if origin:
            if "*" in self.allowed_origins or origin in self.allowed_origins:
                context.response.set_header("access-control-allow-origin", origin)

        context.response.set_header(
            "access-control-allow-methods",
            ", ".join(self.allowed_methods)
        )

        context.response.set_header(
            "access-control-allow-headers",
            ", ".join(self.allowed_headers)
        )

        # Handle preflight
        if context.request.method == RequestMethod.OPTIONS:
            context.response.set_header(
                "access-control-max-age",
                str(self.max_age)
            )
            context.response.status = ResponseStatus.NO_CONTENT
            return

        await next_middleware(context)


class MetricsMiddleware(Middleware):
    """Metrics collection middleware."""

    name = "metrics"
    priority = MiddlewarePriority.CRITICAL.value

    def __init__(self):
        self.request_count: Dict[str, int] = defaultdict(int)
        self.request_duration: Dict[str, List[float]] = defaultdict(list)
        self.status_count: Dict[int, int] = defaultdict(int)
        self.error_count = 0

    async def process(
        self,
        context: PipelineContext,
        next_middleware: Callable[[PipelineContext], Awaitable[None]]
    ) -> None:
        path = context.request.path
        method = context.request.method.value
        key = f"{method}:{path}"

        self.request_count[key] += 1

        start = time.time()

        try:
            await next_middleware(context)
        except Exception as e:
            self.error_count += 1
            raise
        finally:
            duration = time.time() - start
            self.request_duration[key].append(duration)
            self.status_count[context.response.status.value] += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get collected metrics."""
        return {
            "total_requests": sum(self.request_count.values()),
            "requests_by_endpoint": dict(self.request_count),
            "status_codes": dict(self.status_count),
            "errors": self.error_count,
            "avg_duration_by_endpoint": {
                k: sum(v) / len(v) if v else 0
                for k, v in self.request_duration.items()
            }
        }


class ErrorHandlerMiddleware(Middleware):
    """Error handling middleware."""

    name = "error_handler"
    priority = MiddlewarePriority.CRITICAL.value

    def __init__(
        self,
        include_traceback: bool = False,
        error_handlers: Dict[Type[Exception], Callable] = None
    ):
        self.include_traceback = include_traceback
        self.error_handlers = error_handlers or {}

    async def process(
        self,
        context: PipelineContext,
        next_middleware: Callable[[PipelineContext], Awaitable[None]]
    ) -> None:
        try:
            await next_middleware(context)
        except Exception as e:
            error_type = type(e)

            if error_type in self.error_handlers:
                handler = self.error_handlers[error_type]
                handler(context, e)
            else:
                context.response.status = ResponseStatus.INTERNAL_ERROR
                context.response.body = {
                    "error": str(e),
                    "type": error_type.__name__
                }

            logger.exception(f"Pipeline error: {e}")


class TransformMiddleware(Middleware):
    """Request/Response transformation middleware."""

    name = "transform"
    priority = MiddlewarePriority.NORMAL.value

    def __init__(self):
        self.request_transformers: List[Callable[[RequestContext], None]] = []
        self.response_transformers: List[Callable[[ResponseContext], None]] = []

    def add_request_transformer(
        self,
        transformer: Callable[[RequestContext], None]
    ) -> None:
        self.request_transformers.append(transformer)

    def add_response_transformer(
        self,
        transformer: Callable[[ResponseContext], None]
    ) -> None:
        self.response_transformers.append(transformer)

    async def process(
        self,
        context: PipelineContext,
        next_middleware: Callable[[PipelineContext], Awaitable[None]]
    ) -> None:
        # Transform request
        for transformer in self.request_transformers:
            transformer(context.request)

        await next_middleware(context)

        # Transform response
        for transformer in self.response_transformers:
            transformer(context.response)


# =============================================================================
# PIPELINE BUILDER
# =============================================================================

class PipelineBuilder:
    """Fluent pipeline builder."""

    def __init__(self):
        self.middleware_list: List[Middleware] = []

    def use(self, middleware: Middleware) -> 'PipelineBuilder':
        """Add middleware."""
        self.middleware_list.append(middleware)
        return self

    def use_logging(self, log_body: bool = False) -> 'PipelineBuilder':
        return self.use(LoggingMiddleware(log_body))

    def use_authentication(
        self,
        validator: Callable = None,
        public_paths: List[str] = None
    ) -> 'PipelineBuilder':
        return self.use(AuthenticationMiddleware(validator, public_paths))

    def use_rate_limit(
        self,
        rps: int = 10,
        burst: int = 20
    ) -> 'PipelineBuilder':
        return self.use(RateLimitMiddleware(rps, burst))

    def use_cache(
        self,
        ttl: int = 300
    ) -> 'PipelineBuilder':
        return self.use(CacheMiddleware(ttl))

    def use_compression(
        self,
        min_size: int = 1024
    ) -> 'PipelineBuilder':
        return self.use(CompressionMiddleware(min_size))

    def use_cors(
        self,
        origins: List[str] = None
    ) -> 'PipelineBuilder':
        return self.use(CORSMiddleware(origins))

    def use_metrics(self) -> 'PipelineBuilder':
        return self.use(MetricsMiddleware())

    def use_error_handler(
        self,
        include_traceback: bool = False
    ) -> 'PipelineBuilder':
        return self.use(ErrorHandlerMiddleware(include_traceback))

    def build(self) -> 'RequestPipeline':
        """Build the pipeline."""
        pipeline = RequestPipeline()

        # Sort by priority
        sorted_middleware = sorted(
            self.middleware_list,
            key=lambda m: m.priority
        )

        for middleware in sorted_middleware:
            pipeline.add_middleware(middleware)

        return pipeline


# =============================================================================
# REQUEST PIPELINE
# =============================================================================

class RequestPipeline:
    """
    Comprehensive Request Pipeline for BAEL.
    """

    def __init__(self):
        self.middleware: List[Middleware] = []
        self.stats: Dict[str, MiddlewareStats] = {}
        self.handlers: Dict[str, Callable[[PipelineContext], Awaitable[None]]] = {}

    def add_middleware(self, middleware: Middleware) -> None:
        """Add middleware to pipeline."""
        self.middleware.append(middleware)
        self.stats[middleware.name] = MiddlewareStats(name=middleware.name)

        # Re-sort by priority
        self.middleware.sort(key=lambda m: m.priority)

    def remove_middleware(self, name: str) -> bool:
        """Remove middleware by name."""
        for i, m in enumerate(self.middleware):
            if m.name == name:
                self.middleware.pop(i)
                del self.stats[name]
                return True
        return False

    def register_handler(
        self,
        path: str,
        handler: Callable[[PipelineContext], Awaitable[None]]
    ) -> None:
        """Register request handler."""
        self.handlers[path] = handler

    async def execute(self, context: PipelineContext) -> ResponseContext:
        """Execute the pipeline."""

        async def final_handler(ctx: PipelineContext) -> None:
            """Final handler - route to registered handler."""
            if not ctx.should_continue:
                return

            path = ctx.request.path
            handler = self.handlers.get(path)

            if handler:
                await handler(ctx)
            else:
                ctx.response.status = ResponseStatus.NOT_FOUND
                ctx.response.body = {"error": "Not found"}

        # Build middleware chain
        chain = self._build_chain(final_handler)

        # Execute chain
        await chain(context)

        return context.response

    def _build_chain(
        self,
        final: Callable[[PipelineContext], Awaitable[None]]
    ) -> Callable[[PipelineContext], Awaitable[None]]:
        """Build middleware chain."""

        async def execute_chain(context: PipelineContext) -> None:
            """Execute middleware chain."""

            index = 0

            async def next_middleware(ctx: PipelineContext) -> None:
                nonlocal index

                if not ctx.should_continue:
                    return

                if index < len(self.middleware):
                    middleware = self.middleware[index]
                    index += 1

                    start = time.time()
                    try:
                        await middleware.process(ctx, next_middleware)

                        # Update stats
                        self.stats[middleware.name].invocations += 1
                        self.stats[middleware.name].total_time += time.time() - start
                    except Exception as e:
                        self.stats[middleware.name].errors += 1
                        await middleware.on_error(ctx, e)
                        raise
                else:
                    await final(ctx)

            await next_middleware(context)

        return execute_chain

    async def process_request(
        self,
        method: RequestMethod,
        path: str,
        headers: Dict[str, str] = None,
        body: Any = None,
        query_params: Dict[str, str] = None
    ) -> ResponseContext:
        """Process a request."""
        request = RequestContext(
            method=method,
            path=path,
            headers=headers or {},
            body=body,
            query_params=query_params or {}
        )

        context = PipelineContext(request=request)

        return await self.execute(context)

    def get_middleware_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get middleware statistics."""
        return {
            name: {
                "invocations": stats.invocations,
                "total_time": stats.total_time,
                "avg_time": stats.avg_time,
                "errors": stats.errors
            }
            for name, stats in self.stats.items()
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Request Pipeline System."""
    print("=" * 70)
    print("BAEL - REQUEST PIPELINE SYSTEM DEMO")
    print("Comprehensive Middleware Pipeline")
    print("=" * 70)
    print()

    # 1. Build Pipeline
    print("1. BUILD PIPELINE:")
    print("-" * 40)

    metrics = MetricsMiddleware()

    pipeline = (
        PipelineBuilder()
        .use_error_handler()
        .use(metrics)
        .use_logging()
        .use_cors(["*"])
        .use_rate_limit(rps=5, burst=10)
        .use_cache(ttl=60)
        .use_compression(min_size=500)
        .build()
    )

    print(f"   Middleware count: {len(pipeline.middleware)}")

    for m in pipeline.middleware:
        print(f"      - {m.name} (priority: {m.priority})")
    print()

    # 2. Register Handlers
    print("2. REGISTER HANDLERS:")
    print("-" * 40)

    async def get_users(ctx: PipelineContext) -> None:
        ctx.response.body = {
            "users": [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"},
                {"id": 3, "name": "Charlie"}
            ]
        }

    async def get_user(ctx: PipelineContext) -> None:
        user_id = ctx.request.query_params.get("id", "1")
        ctx.response.body = {
            "id": int(user_id),
            "name": "Alice",
            "email": "alice@example.com"
        }

    async def create_user(ctx: PipelineContext) -> None:
        ctx.response.status = ResponseStatus.CREATED
        ctx.response.body = {
            "id": 4,
            "created": True,
            **ctx.request.body
        }

    pipeline.register_handler("/api/users", get_users)
    pipeline.register_handler("/api/user", get_user)
    pipeline.register_handler("/api/users/create", create_user)

    print(f"   Registered handlers: {len(pipeline.handlers)}")
    print()

    # 3. Process GET Request
    print("3. PROCESS GET REQUEST:")
    print("-" * 40)

    response = await pipeline.process_request(
        method=RequestMethod.GET,
        path="/api/users",
        headers={"accept-encoding": "gzip"}
    )

    print(f"   Status: {response.status.value}")
    print(f"   Cache: {response.headers.get('x-cache', 'N/A')}")

    if isinstance(response.body, dict):
        print(f"   Users: {len(response.body.get('users', []))}")
    print()

    # 4. Process Request with Query Params
    print("4. REQUEST WITH PARAMS:")
    print("-" * 40)

    response = await pipeline.process_request(
        method=RequestMethod.GET,
        path="/api/user",
        query_params={"id": "42"}
    )

    print(f"   Status: {response.status.value}")

    if isinstance(response.body, dict):
        print(f"   User ID: {response.body.get('id')}")
        print(f"   Name: {response.body.get('name')}")
    print()

    # 5. Process POST Request
    print("5. PROCESS POST REQUEST:")
    print("-" * 40)

    response = await pipeline.process_request(
        method=RequestMethod.POST,
        path="/api/users/create",
        headers={"content-type": "application/json"},
        body={"name": "David", "email": "david@example.com"}
    )

    print(f"   Status: {response.status.value}")

    if isinstance(response.body, dict):
        print(f"   Created ID: {response.body.get('id')}")
        print(f"   Name: {response.body.get('name')}")
    print()

    # 6. Cache Hit
    print("6. CACHE HIT:")
    print("-" * 40)

    # First request (cache miss)
    response1 = await pipeline.process_request(
        method=RequestMethod.GET,
        path="/api/users"
    )

    print(f"   First request: {response1.headers.get('x-cache', 'N/A')}")

    # Second request (cache hit)
    response2 = await pipeline.process_request(
        method=RequestMethod.GET,
        path="/api/users"
    )

    print(f"   Second request: {response2.headers.get('x-cache', 'N/A')}")
    print()

    # 7. Rate Limiting
    print("7. RATE LIMITING:")
    print("-" * 40)

    success_count = 0
    limited_count = 0

    for i in range(15):
        response = await pipeline.process_request(
            method=RequestMethod.POST,
            path="/api/users/create",
            body={"name": f"User{i}"}
        )

        if response.status == ResponseStatus.TOO_MANY_REQUESTS:
            limited_count += 1
        else:
            success_count += 1

    print(f"   Successful: {success_count}")
    print(f"   Rate limited: {limited_count}")
    print()

    # 8. Not Found
    print("8. NOT FOUND:")
    print("-" * 40)

    response = await pipeline.process_request(
        method=RequestMethod.GET,
        path="/api/unknown"
    )

    print(f"   Status: {response.status.value}")

    if isinstance(response.body, dict):
        print(f"   Error: {response.body.get('error')}")
    print()

    # 9. CORS Headers
    print("9. CORS HEADERS:")
    print("-" * 40)

    response = await pipeline.process_request(
        method=RequestMethod.GET,
        path="/api/users",
        headers={"origin": "http://localhost:3000"}
    )

    print(f"   Origin: {response.headers.get('access-control-allow-origin', 'N/A')}")
    print(f"   Methods: {response.headers.get('access-control-allow-methods', 'N/A')}")
    print()

    # 10. Middleware Stats
    print("10. MIDDLEWARE STATISTICS:")
    print("-" * 40)

    stats = pipeline.get_middleware_stats()

    for name, stat in stats.items():
        print(f"   {name}:")
        print(f"      Invocations: {stat['invocations']}")
        print(f"      Avg time: {stat['avg_time']*1000:.2f}ms")
    print()

    # 11. Metrics
    print("11. REQUEST METRICS:")
    print("-" * 40)

    metrics_data = metrics.get_stats()

    print(f"   Total requests: {metrics_data['total_requests']}")
    print(f"   Status codes:")

    for code, count in metrics_data['status_codes'].items():
        print(f"      {code}: {count}")
    print()

    # 12. Custom Middleware
    print("12. CUSTOM MIDDLEWARE:")
    print("-" * 40)

    class RequestIdMiddleware(Middleware):
        name = "request_id"
        priority = 0

        async def process(self, context, next_middleware):
            context.response.set_header(
                "x-request-id",
                context.request.request_id
            )
            await next_middleware(context)

    pipeline.add_middleware(RequestIdMiddleware())

    response = await pipeline.process_request(
        method=RequestMethod.GET,
        path="/api/users"
    )

    print(f"   Request ID header: {response.headers.get('x-request-id', 'N/A')[:8]}...")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Request Pipeline System Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
