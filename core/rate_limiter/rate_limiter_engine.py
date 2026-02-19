"""
BAEL Rate Limiter Engine
=========================

Advanced rate limiting with multiple algorithms.

"Ba'el controls the flow of reality." — Ba'el
"""

import asyncio
import logging
import time
import threading
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import defaultdict, deque

logger = logging.getLogger("BAEL.RateLimiter")


# ============================================================================
# ENUMS
# ============================================================================

class RateLimitAlgorithm(Enum):
    """Rate limiting algorithms."""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    SLIDING_WINDOW_LOG = "sliding_window_log"
    FIXED_WINDOW = "fixed_window"
    LEAKY_BUCKET = "leaky_bucket"


class RateLimitScope(Enum):
    """Rate limit scope."""
    GLOBAL = "global"
    USER = "user"
    IP = "ip"
    API_KEY = "api_key"
    ENDPOINT = "endpoint"
    CUSTOM = "custom"


class RateLimitAction(Enum):
    """Action when rate limit exceeded."""
    REJECT = "reject"
    QUEUE = "queue"
    THROTTLE = "throttle"
    LOG_ONLY = "log_only"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class RateLimit:
    """A rate limit definition."""
    id: str
    name: str

    # Limits
    max_requests: int
    window_seconds: float

    # Algorithm
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.SLIDING_WINDOW

    # Scope
    scope: RateLimitScope = RateLimitScope.GLOBAL
    scope_key: Optional[str] = None

    # Action
    action: RateLimitAction = RateLimitAction.REJECT

    # Token bucket specific
    bucket_size: Optional[int] = None
    refill_rate: Optional[float] = None

    # Burst
    burst_size: int = 0

    # Retry
    retry_after_header: bool = True


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool

    # Current state
    remaining: int
    limit: int
    reset_at: datetime

    # If rejected
    retry_after_seconds: Optional[float] = None

    # Metadata
    scope_key: Optional[str] = None
    algorithm: Optional[RateLimitAlgorithm] = None


@dataclass
class Quota:
    """A usage quota."""
    id: str
    name: str

    # Limits
    max_amount: int
    period: str  # "hour", "day", "month"

    # Current usage
    current_usage: int = 0

    # Reset
    reset_at: Optional[datetime] = None


@dataclass
class RateLimiterConfig:
    """Rate limiter configuration."""
    default_algorithm: RateLimitAlgorithm = RateLimitAlgorithm.SLIDING_WINDOW
    default_action: RateLimitAction = RateLimitAction.REJECT
    enable_distributed: bool = False
    cleanup_interval_seconds: float = 60.0


# ============================================================================
# RATE LIMITER IMPLEMENTATIONS
# ============================================================================

class TokenBucket:
    """Token bucket rate limiter."""

    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.

        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = time.time()
        self._lock = threading.Lock()

    def acquire(self, tokens: int = 1) -> Tuple[bool, float]:
        """
        Try to acquire tokens.

        Returns:
            (allowed, wait_time)
        """
        with self._lock:
            self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True, 0.0
            else:
                # Calculate wait time
                needed = tokens - self.tokens
                wait_time = needed / self.refill_rate
                return False, wait_time

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill

        self.tokens = min(
            self.capacity,
            self.tokens + elapsed * self.refill_rate
        )

        self.last_refill = now

    @property
    def available(self) -> int:
        """Get available tokens."""
        with self._lock:
            self._refill()
            return int(self.tokens)


class SlidingWindow:
    """Sliding window rate limiter."""

    def __init__(self, max_requests: int, window_seconds: float):
        """
        Initialize sliding window.

        Args:
            max_requests: Maximum requests per window
            window_seconds: Window duration in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: deque = deque()
        self._lock = threading.Lock()

    def acquire(self) -> Tuple[bool, float]:
        """
        Try to make a request.

        Returns:
            (allowed, wait_time)
        """
        with self._lock:
            now = time.time()
            window_start = now - self.window_seconds

            # Remove old requests
            while self.requests and self.requests[0] < window_start:
                self.requests.popleft()

            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True, 0.0
            else:
                # Calculate wait time
                oldest = self.requests[0]
                wait_time = oldest - window_start
                return False, max(0.0, wait_time)

    @property
    def remaining(self) -> int:
        """Get remaining requests in window."""
        with self._lock:
            now = time.time()
            window_start = now - self.window_seconds

            # Count valid requests
            count = sum(1 for r in self.requests if r >= window_start)

            return max(0, self.max_requests - count)

    @property
    def reset_at(self) -> datetime:
        """Get when the window resets."""
        with self._lock:
            if self.requests:
                oldest = self.requests[0]
                reset_time = oldest + self.window_seconds
                return datetime.fromtimestamp(reset_time)
            return datetime.now()


class FixedWindow:
    """Fixed window rate limiter."""

    def __init__(self, max_requests: int, window_seconds: float):
        """
        Initialize fixed window.

        Args:
            max_requests: Maximum requests per window
            window_seconds: Window duration in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.window_start = time.time()
        self.count = 0
        self._lock = threading.Lock()

    def acquire(self) -> Tuple[bool, float]:
        """
        Try to make a request.

        Returns:
            (allowed, wait_time)
        """
        with self._lock:
            now = time.time()

            # Check if we need a new window
            if now >= self.window_start + self.window_seconds:
                self.window_start = now
                self.count = 0

            if self.count < self.max_requests:
                self.count += 1
                return True, 0.0
            else:
                # Wait until next window
                wait_time = (self.window_start + self.window_seconds) - now
                return False, max(0.0, wait_time)

    @property
    def remaining(self) -> int:
        """Get remaining requests in window."""
        with self._lock:
            return max(0, self.max_requests - self.count)

    @property
    def reset_at(self) -> datetime:
        """Get when the window resets."""
        reset_time = self.window_start + self.window_seconds
        return datetime.fromtimestamp(reset_time)


class LeakyBucket:
    """Leaky bucket rate limiter."""

    def __init__(self, capacity: int, leak_rate: float):
        """
        Initialize leaky bucket.

        Args:
            capacity: Maximum bucket size
            leak_rate: Requests leaked per second
        """
        self.capacity = capacity
        self.leak_rate = leak_rate
        self.water = 0.0
        self.last_leak = time.time()
        self._lock = threading.Lock()

    def acquire(self) -> Tuple[bool, float]:
        """
        Try to add a request.

        Returns:
            (allowed, wait_time)
        """
        with self._lock:
            self._leak()

            if self.water < self.capacity:
                self.water += 1
                return True, 0.0
            else:
                # Calculate wait time (time for one to leak)
                wait_time = 1.0 / self.leak_rate
                return False, wait_time

    def _leak(self) -> None:
        """Leak water based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_leak

        leaked = elapsed * self.leak_rate
        self.water = max(0, self.water - leaked)

        self.last_leak = now

    @property
    def remaining(self) -> int:
        """Get remaining capacity."""
        with self._lock:
            self._leak()
            return int(self.capacity - self.water)


# ============================================================================
# MAIN RATE LIMITER ENGINE
# ============================================================================

class RateLimiterEngine:
    """
    Main rate limiter engine.

    Features:
    - Multiple algorithms
    - User/IP/API key scoping
    - Quotas
    - Retry-After headers

    "Ba'el governs the pace of all things." — Ba'el
    """

    def __init__(self, config: Optional[RateLimiterConfig] = None):
        """Initialize rate limiter engine."""
        self.config = config or RateLimiterConfig()

        # Rate limits
        self._limits: Dict[str, RateLimit] = {}

        # Limiters by key
        self._limiters: Dict[str, Any] = {}

        # Quotas
        self._quotas: Dict[str, Dict[str, Quota]] = defaultdict(dict)

        self._lock = threading.RLock()

        logger.info("RateLimiterEngine initialized")

    # ========================================================================
    # LIMIT MANAGEMENT
    # ========================================================================

    def create_limit(
        self,
        name: str,
        max_requests: int,
        window_seconds: float,
        algorithm: Optional[RateLimitAlgorithm] = None,
        scope: RateLimitScope = RateLimitScope.GLOBAL,
        **kwargs
    ) -> RateLimit:
        """Create a rate limit."""
        import uuid

        limit = RateLimit(
            id=str(uuid.uuid4()),
            name=name,
            max_requests=max_requests,
            window_seconds=window_seconds,
            algorithm=algorithm or self.config.default_algorithm,
            scope=scope,
            action=kwargs.get('action', self.config.default_action),
            bucket_size=kwargs.get('bucket_size', max_requests),
            refill_rate=kwargs.get('refill_rate', max_requests / window_seconds),
            burst_size=kwargs.get('burst_size', 0)
        )

        with self._lock:
            self._limits[name] = limit

        return limit

    def get_limit(self, name: str) -> Optional[RateLimit]:
        """Get a rate limit by name."""
        return self._limits.get(name)

    def delete_limit(self, name: str) -> bool:
        """Delete a rate limit."""
        with self._lock:
            if name in self._limits:
                del self._limits[name]
                return True
            return False

    # ========================================================================
    # RATE LIMITING
    # ========================================================================

    def check(
        self,
        limit_name: str,
        key: Optional[str] = None
    ) -> RateLimitResult:
        """
        Check if a request is allowed.

        Args:
            limit_name: Name of the rate limit
            key: Scope key (user_id, ip, etc.)

        Returns:
            RateLimitResult
        """
        limit = self._limits.get(limit_name)

        if not limit:
            # No limit defined, allow
            return RateLimitResult(
                allowed=True,
                remaining=float('inf'),
                limit=0,
                reset_at=datetime.now()
            )

        # Get or create limiter
        limiter_key = self._get_limiter_key(limit, key)
        limiter = self._get_or_create_limiter(limit, limiter_key)

        # Check limit
        allowed, wait_time = limiter.acquire()

        return RateLimitResult(
            allowed=allowed,
            remaining=limiter.remaining if hasattr(limiter, 'remaining') else 0,
            limit=limit.max_requests,
            reset_at=limiter.reset_at if hasattr(limiter, 'reset_at') else datetime.now(),
            retry_after_seconds=wait_time if not allowed else None,
            scope_key=key,
            algorithm=limit.algorithm
        )

    async def check_async(
        self,
        limit_name: str,
        key: Optional[str] = None
    ) -> RateLimitResult:
        """Async version of check."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.check, limit_name, key)

    def _get_limiter_key(self, limit: RateLimit, key: Optional[str]) -> str:
        """Get the key for a limiter."""
        if limit.scope == RateLimitScope.GLOBAL:
            return f"{limit.name}:global"
        else:
            return f"{limit.name}:{key or 'unknown'}"

    def _get_or_create_limiter(self, limit: RateLimit, key: str) -> Any:
        """Get or create a limiter for a key."""
        with self._lock:
            if key not in self._limiters:
                self._limiters[key] = self._create_limiter(limit)

            return self._limiters[key]

    def _create_limiter(self, limit: RateLimit) -> Any:
        """Create a limiter based on algorithm."""
        if limit.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
            return TokenBucket(
                capacity=limit.bucket_size or limit.max_requests,
                refill_rate=limit.refill_rate or (limit.max_requests / limit.window_seconds)
            )

        elif limit.algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
            return SlidingWindow(
                max_requests=limit.max_requests,
                window_seconds=limit.window_seconds
            )

        elif limit.algorithm == RateLimitAlgorithm.FIXED_WINDOW:
            return FixedWindow(
                max_requests=limit.max_requests,
                window_seconds=limit.window_seconds
            )

        elif limit.algorithm == RateLimitAlgorithm.LEAKY_BUCKET:
            return LeakyBucket(
                capacity=limit.max_requests,
                leak_rate=limit.max_requests / limit.window_seconds
            )

        else:
            return SlidingWindow(
                max_requests=limit.max_requests,
                window_seconds=limit.window_seconds
            )

    # ========================================================================
    # QUOTAS
    # ========================================================================

    def create_quota(
        self,
        name: str,
        max_amount: int,
        period: str = "day"
    ) -> Quota:
        """Create a quota."""
        import uuid

        now = datetime.now()

        # Calculate reset time
        if period == "hour":
            reset_at = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        elif period == "day":
            reset_at = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        elif period == "month":
            if now.month == 12:
                reset_at = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                reset_at = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            reset_at = now + timedelta(days=1)

        quota = Quota(
            id=str(uuid.uuid4()),
            name=name,
            max_amount=max_amount,
            period=period,
            reset_at=reset_at
        )

        return quota

    def check_quota(
        self,
        quota_name: str,
        key: str,
        amount: int = 1
    ) -> Tuple[bool, Quota]:
        """
        Check and update quota.

        Returns:
            (allowed, quota)
        """
        with self._lock:
            if quota_name not in self._quotas[key]:
                # Create default quota
                self._quotas[key][quota_name] = self.create_quota(quota_name, 1000)

            quota = self._quotas[key][quota_name]

            # Check if needs reset
            if quota.reset_at and datetime.now() >= quota.reset_at:
                quota.current_usage = 0

                # Update reset time
                now = datetime.now()
                if quota.period == "hour":
                    quota.reset_at = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
                elif quota.period == "day":
                    quota.reset_at = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                elif quota.period == "month":
                    if now.month == 12:
                        quota.reset_at = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                    else:
                        quota.reset_at = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)

            # Check quota
            if quota.current_usage + amount <= quota.max_amount:
                quota.current_usage += amount
                return True, quota
            else:
                return False, quota

    # ========================================================================
    # DECORATORS
    # ========================================================================

    def limit(self, limit_name: str, key_func: Optional[Callable] = None):
        """
        Decorator to apply rate limiting to a function.

        Args:
            limit_name: Name of the rate limit
            key_func: Function to extract key from request
        """
        def decorator(func):
            if asyncio.iscoroutinefunction(func):
                async def async_wrapper(*args, **kwargs):
                    key = key_func(*args, **kwargs) if key_func else None
                    result = await self.check_async(limit_name, key)

                    if not result.allowed:
                        raise RateLimitExceeded(result)

                    return await func(*args, **kwargs)
                return async_wrapper
            else:
                def sync_wrapper(*args, **kwargs):
                    key = key_func(*args, **kwargs) if key_func else None
                    result = self.check(limit_name, key)

                    if not result.allowed:
                        raise RateLimitExceeded(result)

                    return func(*args, **kwargs)
                return sync_wrapper

        return decorator

    # ========================================================================
    # CLEANUP
    # ========================================================================

    def cleanup(self, max_age_seconds: float = 3600) -> int:
        """Cleanup old limiters."""
        # For now, just clear all
        with self._lock:
            count = len(self._limiters)
            self._limiters.clear()
            return count

    # ========================================================================
    # STATUS
    # ========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get rate limiter status."""
        return {
            'total_limits': len(self._limits),
            'active_limiters': len(self._limiters),
            'default_algorithm': self.config.default_algorithm.value
        }


# ============================================================================
# EXCEPTION
# ============================================================================

class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, result: RateLimitResult):
        self.result = result
        super().__init__(
            f"Rate limit exceeded. Retry after {result.retry_after_seconds:.1f} seconds."
        )


# ============================================================================
# CONVENIENCE INSTANCE
# ============================================================================

rate_limiter_engine = RateLimiterEngine()
