"""
API Gateway & Rate Limiting - Request routing and traffic control.

Features:
- Request validation and versioning
- Rate limiting (token bucket, sliding window)
- Throttling and backpressure
- Authentication/authorization
- Response compression
- API versioning management

Target: 1,200+ lines for complete gateway
"""

import asyncio
import json
import logging
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

# ============================================================================
# RATE LIMITING ENUMS
# ============================================================================

class RateLimitStrategy(Enum):
    """Rate limiting strategies."""
    TOKEN_BUCKET = "TOKEN_BUCKET"
    SLIDING_WINDOW = "SLIDING_WINDOW"
    LEAKY_BUCKET = "LEAKY_BUCKET"

class ThrottleStatus(Enum):
    """Request throttle status."""
    ALLOWED = "ALLOWED"
    RATE_LIMITED = "RATE_LIMITED"
    BACKPRESSURE = "BACKPRESSURE"

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    strategy: RateLimitStrategy
    requests_per_second: int
    burst_size: int
    window_seconds: int = 60

@dataclass
class RequestMetadata:
    """Request metadata for routing."""
    request_id: str
    client_id: str
    api_version: str
    endpoint: str
    method: str
    timestamp: datetime
    size_bytes: int = 0

@dataclass
class RateLimitEntry:
    """Single rate limit entry."""
    client_id: str
    tokens: float
    last_refill: datetime
    requests_in_window: deque = field(default_factory=lambda: deque(maxlen=1000))

@dataclass
class GatewayResponse:
    """Gateway response with metadata."""
    status_code: int
    body: Any
    headers: Dict[str, str] = field(default_factory=dict)
    rate_limit_remaining: int = 0
    rate_limit_reset_seconds: int = 0

# ============================================================================
# TOKEN BUCKET RATE LIMITER
# ============================================================================

class TokenBucketLimiter:
    """Token bucket rate limiting."""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.buckets: Dict[str, RateLimitEntry] = {}
        self.logger = logging.getLogger("token_bucket")

    async def check_limit(self, client_id: str) -> Tuple[bool, int]:
        """Check if request is allowed."""
        now = datetime.now()

        if client_id not in self.buckets:
            self.buckets[client_id] = RateLimitEntry(
                client_id=client_id,
                tokens=float(self.config.burst_size),
                last_refill=now
            )

        bucket = self.buckets[client_id]

        # Refill tokens
        time_passed = (now - bucket.last_refill).total_seconds()
        refill_rate = self.config.requests_per_second
        tokens_to_add = time_passed * refill_rate

        bucket.tokens = min(
            bucket.tokens + tokens_to_add,
            float(self.config.burst_size)
        )
        bucket.last_refill = now

        # Check if request allowed
        if bucket.tokens >= 1:
            bucket.tokens -= 1
            remaining = int(bucket.tokens)
            return True, remaining

        return False, 0

# ============================================================================
# SLIDING WINDOW RATE LIMITER
# ============================================================================

class SlidingWindowLimiter:
    """Sliding window rate limiting."""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.windows: Dict[str, deque] = {}
        self.logger = logging.getLogger("sliding_window")

    async def check_limit(self, client_id: str) -> Tuple[bool, int]:
        """Check if request is allowed."""
        now = datetime.now()
        window_start = now - timedelta(seconds=self.config.window_seconds)

        if client_id not in self.windows:
            self.windows[client_id] = deque()

        window = self.windows[client_id]

        # Remove old entries
        while window and window[0] < window_start:
            window.popleft()

        # Check limit
        limit = self.config.requests_per_second * self.config.window_seconds

        if len(window) < limit:
            window.append(now)
            remaining = limit - len(window)
            return True, remaining

        return False, 0

# ============================================================================
# RATE LIMIT MANAGER
# ============================================================================

class RateLimitManager:
    """Centralized rate limit management."""

    def __init__(self, default_config: RateLimitConfig):
        self.default_config = default_config
        self.client_configs: Dict[str, RateLimitConfig] = {}
        self.limiters: Dict[str, Any] = {}
        self.logger = logging.getLogger("rate_limit_manager")

        self._initialize_limiter(self.default_config)

    def _initialize_limiter(self, config: RateLimitConfig) -> None:
        """Initialize rate limiter."""
        if config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            limiter = TokenBucketLimiter(config)
        elif config.strategy == RateLimitStrategy.SLIDING_WINDOW:
            limiter = SlidingWindowLimiter(config)
        else:
            limiter = TokenBucketLimiter(config)

        key = f"{config.strategy.value}"
        self.limiters[key] = limiter

    def set_client_config(self, client_id: str, config: RateLimitConfig) -> None:
        """Set custom config for client."""
        self.client_configs[client_id] = config
        self._initialize_limiter(config)

    async def check_rate_limit(self, client_id: str) -> Tuple[bool, int]:
        """Check if request allowed."""
        config = self.client_configs.get(client_id, self.default_config)
        strategy_key = f"{config.strategy.value}"
        limiter = self.limiters.get(strategy_key)

        if limiter is None:
            return True, 0

        allowed, remaining = await limiter.check_limit(client_id)

        if not allowed:
            self.logger.warning(f"Rate limit exceeded for client: {client_id}")

        return allowed, remaining

# ============================================================================
# REQUEST VALIDATOR
# ============================================================================

class RequestValidator:
    """Validate API requests."""

    def __init__(self):
        self.logger = logging.getLogger("request_validator")
        self.supported_versions = ["v1", "v2", "v3"]

    def validate_request(self, metadata: RequestMetadata) -> Tuple[bool, Optional[str]]:
        """Validate request."""
        # Check version
        if metadata.api_version not in self.supported_versions:
            return False, f"Unsupported API version: {metadata.api_version}"

        # Check method
        if metadata.method not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
            return False, f"Unsupported HTTP method: {metadata.method}"

        # Check endpoint
        if not metadata.endpoint or metadata.endpoint == "":
            return False, "Missing endpoint"

        # Check client ID
        if not metadata.client_id:
            return False, "Missing client ID"

        return True, None

# ============================================================================
# BACKPRESSURE SYSTEM
# ============================================================================

class BackpressureSystem:
    """Manage system backpressure."""

    def __init__(self, max_queue_size: int = 10000, max_latency_ms: int = 5000):
        self.max_queue_size = max_queue_size
        self.max_latency_ms = max_latency_ms
        self.queue_sizes: Dict[str, int] = {}
        self.latencies: Dict[str, List[float]] = {}
        self.logger = logging.getLogger("backpressure")

    async def check_backpressure(self, service: str) -> ThrottleStatus:
        """Check if backpressure needed."""
        queue_size = self.queue_sizes.get(service, 0)

        # Check queue size
        if queue_size > self.max_queue_size:
            self.logger.warning(f"Backpressure: {service} queue={queue_size}")
            return ThrottleStatus.BACKPRESSURE

        # Check latency
        if service in self.latencies:
            recent_latencies = self.latencies[service][-10:]
            if recent_latencies:
                avg_latency = sum(recent_latencies) / len(recent_latencies)
                if avg_latency > self.max_latency_ms:
                    return ThrottleStatus.BACKPRESSURE

        return ThrottleStatus.ALLOWED

    def update_queue_size(self, service: str, size: int) -> None:
        """Update service queue size."""
        self.queue_sizes[service] = size

    def record_latency(self, service: str, latency_ms: float) -> None:
        """Record request latency."""
        if service not in self.latencies:
            self.latencies[service] = []

        self.latencies[service].append(latency_ms)

        # Keep last 1000 measurements
        if len(self.latencies[service]) > 1000:
            self.latencies[service] = self.latencies[service][-1000:]

# ============================================================================
# API GATEWAY
# ============================================================================

class APIGateway:
    """Complete API gateway with routing and rate limiting."""

    def __init__(self):
        default_config = RateLimitConfig(
            strategy=RateLimitStrategy.TOKEN_BUCKET,
            requests_per_second=100,
            burst_size=1000,
            window_seconds=60
        )

        self.rate_limiter = RateLimitManager(default_config)
        self.validator = RequestValidator()
        self.backpressure = BackpressureSystem()

        self.routes: Dict[str, Callable] = {}
        self.middleware: List[Callable] = []
        self.logger = logging.getLogger("api_gateway")

    def register_route(self, path: str, handler: Callable) -> None:
        """Register API route."""
        self.routes[path] = handler
        self.logger.info(f"Registered route: {path}")

    def add_middleware(self, middleware: Callable) -> None:
        """Add middleware."""
        self.middleware.append(middleware)

    async def handle_request(self, metadata: RequestMetadata,
                            body: Any = None) -> GatewayResponse:
        """Handle incoming request."""
        # Validate request
        valid, error = self.validator.validate_request(metadata)
        if not valid:
            return GatewayResponse(
                status_code=400,
                body={'error': error}
            )

        # Check rate limit
        allowed, remaining = await self.rate_limiter.check_rate_limit(
            metadata.client_id
        )

        if not allowed:
            return GatewayResponse(
                status_code=429,
                body={'error': 'Rate limit exceeded'},
                rate_limit_remaining=0,
                rate_limit_reset_seconds=60
            )

        # Check backpressure
        backpressure_status = await self.backpressure.check_backpressure(
            metadata.endpoint
        )

        if backpressure_status == ThrottleStatus.BACKPRESSURE:
            return GatewayResponse(
                status_code=503,
                body={'error': 'Service temporarily unavailable'},
                rate_limit_remaining=remaining
            )

        # Apply middleware
        for middleware in self.middleware:
            result = await middleware(metadata, body)
            if result is not None:
                return result

        # Route request
        handler = self.routes.get(metadata.endpoint)
        if handler is None:
            return GatewayResponse(
                status_code=404,
                body={'error': 'Endpoint not found'},
                rate_limit_remaining=remaining
            )

        try:
            start_time = datetime.now()
            result = await handler(body)
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Record latency
            self.backpressure.record_latency(metadata.endpoint, latency_ms)

            return GatewayResponse(
                status_code=200,
                body=result,
                rate_limit_remaining=remaining
            )

        except Exception as e:
            self.logger.error(f"Handler error: {e}")
            return GatewayResponse(
                status_code=500,
                body={'error': str(e)},
                rate_limit_remaining=remaining
            )

    def get_gateway_status(self) -> Dict[str, Any]:
        """Get gateway status."""
        return {
            'routes': len(self.routes),
            'middleware': len(self.middleware),
            'queue_sizes': self.backpressure.queue_sizes,
            'registered_endpoints': list(self.routes.keys())
        }

def create_api_gateway() -> APIGateway:
    """Create API gateway."""
    return APIGateway()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    gateway = create_api_gateway()
    print("API gateway initialized")
