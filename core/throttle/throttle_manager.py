#!/usr/bin/env python3
"""
BAEL - Throttle Manager
Advanced throttling for AI agent operations.

Features:
- Token bucket algorithm
- Sliding window algorithm
- Fixed window algorithm
- Leaky bucket algorithm
- Adaptive throttling
- Priority queuing
- Quota management
- Burst handling
- Statistics tracking
- Dynamic limits
"""

import asyncio
import heapq
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Awaitable, Callable, Dict, Generic, Iterator, List,
                    Optional, Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ThrottleAlgorithm(Enum):
    """Throttle algorithms."""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    LEAKY_BUCKET = "leaky_bucket"
    ADAPTIVE = "adaptive"


class ThrottleResult(Enum):
    """Throttle result."""
    ALLOWED = "allowed"
    THROTTLED = "throttled"
    QUEUED = "queued"
    REJECTED = "rejected"


class Priority(Enum):
    """Request priority."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class QuotaPeriod(Enum):
    """Quota period."""
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    MONTH = "month"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class ThrottleConfig:
    """Throttle configuration."""
    name: str = "default"
    algorithm: ThrottleAlgorithm = ThrottleAlgorithm.TOKEN_BUCKET
    rate: float = 10.0  # requests per second
    burst: int = 20
    window_size: float = 1.0  # seconds
    queue_enabled: bool = False
    queue_size: int = 100
    queue_timeout: float = 30.0


@dataclass
class ThrottleState:
    """Throttle state."""
    tokens: float = 0.0
    last_update: float = 0.0
    window_start: float = 0.0
    window_count: int = 0
    queue_size: int = 0


@dataclass
class ThrottleResponse:
    """Throttle response."""
    result: ThrottleResult = ThrottleResult.ALLOWED
    wait_time: float = 0.0
    remaining: int = 0
    reset_at: float = 0.0
    retry_after: Optional[float] = None


@dataclass
class QuotaConfig:
    """Quota configuration."""
    quota_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    limit: int = 1000
    period: QuotaPeriod = QuotaPeriod.HOUR
    soft_limit: Optional[int] = None
    burst_allowance: int = 0


@dataclass
class QuotaUsage:
    """Quota usage."""
    used: int = 0
    remaining: int = 0
    limit: int = 0
    reset_at: datetime = field(default_factory=datetime.utcnow)
    percentage: float = 0.0


@dataclass
class ThrottleStats:
    """Throttle statistics."""
    total_requests: int = 0
    allowed: int = 0
    throttled: int = 0
    queued: int = 0
    rejected: int = 0
    avg_wait_time: float = 0.0
    peak_rate: float = 0.0


# =============================================================================
# THROTTLE ALGORITHMS
# =============================================================================

class Throttler(ABC):
    """Base throttler interface."""

    @abstractmethod
    def acquire(self, tokens: int = 1) -> ThrottleResponse:
        """Try to acquire tokens."""
        pass

    @abstractmethod
    def get_state(self) -> ThrottleState:
        """Get current state."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset throttler."""
        pass


class TokenBucket(Throttler):
    """Token bucket throttler."""

    def __init__(self, config: ThrottleConfig):
        self._rate = config.rate
        self._burst = config.burst
        self._tokens = float(config.burst)
        self._last_update = time.time()
        self._lock = threading.Lock()

    def acquire(self, tokens: int = 1) -> ThrottleResponse:
        with self._lock:
            now = time.time()

            # Refill tokens
            elapsed = now - self._last_update
            self._tokens = min(
                self._burst,
                self._tokens + elapsed * self._rate
            )
            self._last_update = now

            if self._tokens >= tokens:
                self._tokens -= tokens
                return ThrottleResponse(
                    result=ThrottleResult.ALLOWED,
                    remaining=int(self._tokens),
                    reset_at=now + (self._burst - self._tokens) / self._rate
                )

            wait_time = (tokens - self._tokens) / self._rate

            return ThrottleResponse(
                result=ThrottleResult.THROTTLED,
                wait_time=wait_time,
                remaining=0,
                retry_after=wait_time
            )

    def get_state(self) -> ThrottleState:
        with self._lock:
            return ThrottleState(
                tokens=self._tokens,
                last_update=self._last_update
            )

    def reset(self) -> None:
        with self._lock:
            self._tokens = float(self._burst)
            self._last_update = time.time()


class SlidingWindow(Throttler):
    """Sliding window throttler."""

    def __init__(self, config: ThrottleConfig):
        self._rate = int(config.rate)
        self._window_size = config.window_size
        self._requests: deque = deque()
        self._lock = threading.Lock()

    def acquire(self, tokens: int = 1) -> ThrottleResponse:
        with self._lock:
            now = time.time()
            window_start = now - self._window_size

            # Remove old requests
            while self._requests and self._requests[0] < window_start:
                self._requests.popleft()

            if len(self._requests) + tokens <= self._rate:
                for _ in range(tokens):
                    self._requests.append(now)

                return ThrottleResponse(
                    result=ThrottleResult.ALLOWED,
                    remaining=self._rate - len(self._requests),
                    reset_at=now + self._window_size
                )

            # Calculate wait time
            if self._requests:
                oldest = self._requests[0]
                wait_time = oldest + self._window_size - now
            else:
                wait_time = 0

            return ThrottleResponse(
                result=ThrottleResult.THROTTLED,
                wait_time=wait_time,
                remaining=0,
                retry_after=wait_time
            )

    def get_state(self) -> ThrottleState:
        with self._lock:
            return ThrottleState(
                window_count=len(self._requests),
                window_start=self._requests[0] if self._requests else 0
            )

    def reset(self) -> None:
        with self._lock:
            self._requests.clear()


class FixedWindow(Throttler):
    """Fixed window throttler."""

    def __init__(self, config: ThrottleConfig):
        self._rate = int(config.rate)
        self._window_size = config.window_size
        self._count = 0
        self._window_start = time.time()
        self._lock = threading.Lock()

    def acquire(self, tokens: int = 1) -> ThrottleResponse:
        with self._lock:
            now = time.time()

            # Check if window expired
            if now - self._window_start >= self._window_size:
                self._window_start = now
                self._count = 0

            if self._count + tokens <= self._rate:
                self._count += tokens

                return ThrottleResponse(
                    result=ThrottleResult.ALLOWED,
                    remaining=self._rate - self._count,
                    reset_at=self._window_start + self._window_size
                )

            wait_time = self._window_start + self._window_size - now

            return ThrottleResponse(
                result=ThrottleResult.THROTTLED,
                wait_time=wait_time,
                remaining=0,
                retry_after=wait_time
            )

    def get_state(self) -> ThrottleState:
        with self._lock:
            return ThrottleState(
                window_count=self._count,
                window_start=self._window_start
            )

    def reset(self) -> None:
        with self._lock:
            self._count = 0
            self._window_start = time.time()


class LeakyBucket(Throttler):
    """Leaky bucket throttler."""

    def __init__(self, config: ThrottleConfig):
        self._rate = config.rate
        self._burst = config.burst
        self._water = 0.0
        self._last_leak = time.time()
        self._lock = threading.Lock()

    def acquire(self, tokens: int = 1) -> ThrottleResponse:
        with self._lock:
            now = time.time()

            # Leak water
            elapsed = now - self._last_leak
            self._water = max(0, self._water - elapsed * self._rate)
            self._last_leak = now

            if self._water + tokens <= self._burst:
                self._water += tokens

                return ThrottleResponse(
                    result=ThrottleResult.ALLOWED,
                    remaining=int(self._burst - self._water),
                    reset_at=now + self._water / self._rate
                )

            wait_time = (self._water + tokens - self._burst) / self._rate

            return ThrottleResponse(
                result=ThrottleResult.THROTTLED,
                wait_time=wait_time,
                remaining=0,
                retry_after=wait_time
            )

    def get_state(self) -> ThrottleState:
        with self._lock:
            return ThrottleState(
                tokens=self._burst - self._water,
                last_update=self._last_leak
            )

    def reset(self) -> None:
        with self._lock:
            self._water = 0.0
            self._last_leak = time.time()


class AdaptiveThrottler(Throttler):
    """Adaptive throttler that adjusts based on load."""

    def __init__(self, config: ThrottleConfig):
        self._base_rate = config.rate
        self._min_rate = config.rate * 0.1
        self._max_rate = config.rate * 2.0
        self._current_rate = config.rate
        self._burst = config.burst
        self._window_size = config.window_size
        self._success_count = 0
        self._failure_count = 0
        self._adjust_interval = 10.0
        self._last_adjust = time.time()
        self._inner = TokenBucket(config)
        self._lock = threading.Lock()

    def acquire(self, tokens: int = 1) -> ThrottleResponse:
        response = self._inner.acquire(tokens)

        with self._lock:
            if response.result == ThrottleResult.ALLOWED:
                self._success_count += 1
            else:
                self._failure_count += 1

            # Periodically adjust rate
            now = time.time()
            if now - self._last_adjust >= self._adjust_interval:
                self._adjust_rate()
                self._last_adjust = now

        return response

    def _adjust_rate(self) -> None:
        """Adjust rate based on success/failure ratio."""
        total = self._success_count + self._failure_count

        if total == 0:
            return

        success_ratio = self._success_count / total

        if success_ratio > 0.95:
            # Increase rate
            self._current_rate = min(
                self._max_rate,
                self._current_rate * 1.1
            )
        elif success_ratio < 0.8:
            # Decrease rate
            self._current_rate = max(
                self._min_rate,
                self._current_rate * 0.9
            )

        # Update inner throttler
        self._inner._rate = self._current_rate

        # Reset counters
        self._success_count = 0
        self._failure_count = 0

    def record_success(self) -> None:
        """Record successful operation."""
        with self._lock:
            self._success_count += 1

    def record_failure(self) -> None:
        """Record failed operation."""
        with self._lock:
            self._failure_count += 1

    def get_state(self) -> ThrottleState:
        return self._inner.get_state()

    def reset(self) -> None:
        with self._lock:
            self._success_count = 0
            self._failure_count = 0
            self._current_rate = self._base_rate
            self._inner.reset()


# =============================================================================
# PRIORITY QUEUE
# =============================================================================

@dataclass(order=True)
class QueuedRequest:
    """Queued request."""
    priority: int
    timestamp: float
    request_id: str = field(compare=False)
    event: asyncio.Event = field(compare=False)


class PriorityQueue:
    """Priority queue for throttled requests."""

    def __init__(self, max_size: int = 100, timeout: float = 30.0):
        self._max_size = max_size
        self._timeout = timeout
        self._queue: List[QueuedRequest] = []
        self._requests: Dict[str, QueuedRequest] = {}
        self._lock = threading.Lock()

    def enqueue(
        self,
        priority: Priority = Priority.NORMAL,
        request_id: Optional[str] = None
    ) -> Optional[QueuedRequest]:
        """Enqueue a request."""
        with self._lock:
            if len(self._queue) >= self._max_size:
                return None

            rid = request_id or str(uuid.uuid4())
            event = asyncio.Event()

            request = QueuedRequest(
                priority=priority.value,
                timestamp=time.time(),
                request_id=rid,
                event=event
            )

            heapq.heappush(self._queue, request)
            self._requests[rid] = request

            return request

    def dequeue(self) -> Optional[QueuedRequest]:
        """Dequeue highest priority request."""
        with self._lock:
            while self._queue:
                request = heapq.heappop(self._queue)

                # Check if expired
                if time.time() - request.timestamp > self._timeout:
                    if request.request_id in self._requests:
                        del self._requests[request.request_id]
                    continue

                if request.request_id in self._requests:
                    del self._requests[request.request_id]
                    return request

            return None

    def cancel(self, request_id: str) -> bool:
        """Cancel a queued request."""
        with self._lock:
            if request_id in self._requests:
                del self._requests[request_id]
                return True
            return False

    def size(self) -> int:
        """Get queue size."""
        with self._lock:
            return len(self._requests)

    def clear(self) -> None:
        """Clear the queue."""
        with self._lock:
            self._queue.clear()
            self._requests.clear()


# =============================================================================
# QUOTA MANAGER
# =============================================================================

class QuotaManager:
    """Quota management for usage limits."""

    def __init__(self):
        self._quotas: Dict[str, QuotaConfig] = {}
        self._usage: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._reset_times: Dict[str, Dict[str, datetime]] = defaultdict(dict)
        self._lock = threading.RLock()

    def create_quota(self, config: QuotaConfig) -> None:
        """Create a quota."""
        with self._lock:
            self._quotas[config.quota_id] = config

    def check_quota(
        self,
        quota_id: str,
        subject: str,
        amount: int = 1
    ) -> Tuple[bool, QuotaUsage]:
        """Check if quota allows operation."""
        with self._lock:
            config = self._quotas.get(quota_id)
            if not config:
                return (True, QuotaUsage())

            # Check and reset if period expired
            self._check_reset(quota_id, subject, config)

            current = self._usage[quota_id][subject]
            allowed = current + amount <= config.limit

            usage = QuotaUsage(
                used=current,
                remaining=max(0, config.limit - current),
                limit=config.limit,
                reset_at=self._reset_times[quota_id].get(subject, datetime.utcnow()),
                percentage=current / config.limit * 100 if config.limit > 0 else 0
            )

            return (allowed, usage)

    def consume_quota(
        self,
        quota_id: str,
        subject: str,
        amount: int = 1
    ) -> bool:
        """Consume quota."""
        with self._lock:
            allowed, _ = self.check_quota(quota_id, subject, amount)

            if allowed:
                self._usage[quota_id][subject] += amount
                return True

            return False

    def get_usage(self, quota_id: str, subject: str) -> QuotaUsage:
        """Get quota usage."""
        with self._lock:
            _, usage = self.check_quota(quota_id, subject, 0)
            return usage

    def _check_reset(
        self,
        quota_id: str,
        subject: str,
        config: QuotaConfig
    ) -> None:
        """Check and reset if period expired."""
        now = datetime.utcnow()
        reset_time = self._reset_times[quota_id].get(subject)

        if reset_time is None:
            reset_time = self._calculate_reset_time(now, config.period)
            self._reset_times[quota_id][subject] = reset_time

        if now >= reset_time:
            self._usage[quota_id][subject] = 0
            self._reset_times[quota_id][subject] = self._calculate_reset_time(
                now, config.period
            )

    def _calculate_reset_time(
        self,
        now: datetime,
        period: QuotaPeriod
    ) -> datetime:
        """Calculate next reset time."""
        if period == QuotaPeriod.SECOND:
            return now + timedelta(seconds=1)
        elif period == QuotaPeriod.MINUTE:
            return now + timedelta(minutes=1)
        elif period == QuotaPeriod.HOUR:
            return now + timedelta(hours=1)
        elif period == QuotaPeriod.DAY:
            return now + timedelta(days=1)
        elif period == QuotaPeriod.MONTH:
            return now + timedelta(days=30)

        return now + timedelta(hours=1)

    def reset_quota(self, quota_id: str, subject: Optional[str] = None) -> None:
        """Reset quota usage."""
        with self._lock:
            if subject:
                self._usage[quota_id][subject] = 0
            else:
                self._usage[quota_id].clear()


# =============================================================================
# THROTTLE MANAGER
# =============================================================================

class ThrottleManager:
    """
    Throttle Manager for BAEL.

    Advanced throttling.
    """

    def __init__(self):
        self._throttlers: Dict[str, Throttler] = {}
        self._queues: Dict[str, PriorityQueue] = {}
        self._configs: Dict[str, ThrottleConfig] = {}
        self._quotas = QuotaManager()
        self._stats: Dict[str, ThrottleStats] = defaultdict(ThrottleStats)
        self._lock = threading.RLock()

    # -------------------------------------------------------------------------
    # THROTTLER MANAGEMENT
    # -------------------------------------------------------------------------

    def create_throttler(self, config: ThrottleConfig) -> Throttler:
        """Create a throttler."""
        with self._lock:
            if config.algorithm == ThrottleAlgorithm.TOKEN_BUCKET:
                throttler = TokenBucket(config)
            elif config.algorithm == ThrottleAlgorithm.SLIDING_WINDOW:
                throttler = SlidingWindow(config)
            elif config.algorithm == ThrottleAlgorithm.FIXED_WINDOW:
                throttler = FixedWindow(config)
            elif config.algorithm == ThrottleAlgorithm.LEAKY_BUCKET:
                throttler = LeakyBucket(config)
            elif config.algorithm == ThrottleAlgorithm.ADAPTIVE:
                throttler = AdaptiveThrottler(config)
            else:
                throttler = TokenBucket(config)

            self._throttlers[config.name] = throttler
            self._configs[config.name] = config

            if config.queue_enabled:
                self._queues[config.name] = PriorityQueue(
                    max_size=config.queue_size,
                    timeout=config.queue_timeout
                )

            return throttler

    def get_throttler(self, name: str) -> Optional[Throttler]:
        """Get throttler by name."""
        with self._lock:
            return self._throttlers.get(name)

    def remove_throttler(self, name: str) -> bool:
        """Remove a throttler."""
        with self._lock:
            if name in self._throttlers:
                del self._throttlers[name]
                if name in self._queues:
                    del self._queues[name]
                if name in self._configs:
                    del self._configs[name]
                return True
            return False

    # -------------------------------------------------------------------------
    # THROTTLE OPERATIONS
    # -------------------------------------------------------------------------

    def acquire(
        self,
        throttler_name: str,
        tokens: int = 1,
        priority: Priority = Priority.NORMAL
    ) -> ThrottleResponse:
        """Acquire tokens from throttler."""
        with self._lock:
            throttler = self._throttlers.get(throttler_name)
            if not throttler:
                return ThrottleResponse(result=ThrottleResult.ALLOWED)

            stats = self._stats[throttler_name]
            stats.total_requests += 1

            response = throttler.acquire(tokens)

            if response.result == ThrottleResult.ALLOWED:
                stats.allowed += 1
            else:
                stats.throttled += 1

                # Try to queue if enabled
                config = self._configs.get(throttler_name)
                queue = self._queues.get(throttler_name)

                if config and config.queue_enabled and queue:
                    request = queue.enqueue(priority)
                    if request:
                        stats.queued += 1
                        response.result = ThrottleResult.QUEUED
                    else:
                        stats.rejected += 1
                        response.result = ThrottleResult.REJECTED

            return response

    async def acquire_async(
        self,
        throttler_name: str,
        tokens: int = 1,
        priority: Priority = Priority.NORMAL,
        wait: bool = True
    ) -> ThrottleResponse:
        """Async acquire with waiting."""
        response = self.acquire(throttler_name, tokens, priority)

        if response.result == ThrottleResult.ALLOWED:
            return response

        if wait and response.wait_time > 0:
            await asyncio.sleep(response.wait_time)
            return self.acquire(throttler_name, tokens, priority)

        return response

    async def wait_for_token(
        self,
        throttler_name: str,
        timeout: Optional[float] = None
    ) -> bool:
        """Wait until token is available."""
        start = time.time()

        while True:
            response = self.acquire(throttler_name)

            if response.result == ThrottleResult.ALLOWED:
                return True

            if timeout and time.time() - start >= timeout:
                return False

            wait = min(response.wait_time, 0.1)
            await asyncio.sleep(wait)

    # -------------------------------------------------------------------------
    # QUEUE OPERATIONS
    # -------------------------------------------------------------------------

    async def process_queue(self, throttler_name: str) -> int:
        """Process queued requests."""
        queue = self._queues.get(throttler_name)
        if not queue:
            return 0

        processed = 0

        while True:
            response = self.acquire(throttler_name)

            if response.result != ThrottleResult.ALLOWED:
                break

            request = queue.dequeue()
            if not request:
                break

            request.event.set()
            processed += 1

        return processed

    def get_queue_size(self, throttler_name: str) -> int:
        """Get queue size."""
        queue = self._queues.get(throttler_name)
        return queue.size() if queue else 0

    # -------------------------------------------------------------------------
    # QUOTA OPERATIONS
    # -------------------------------------------------------------------------

    def create_quota(self, config: QuotaConfig) -> None:
        """Create a quota."""
        self._quotas.create_quota(config)

    def check_quota(
        self,
        quota_id: str,
        subject: str,
        amount: int = 1
    ) -> Tuple[bool, QuotaUsage]:
        """Check quota."""
        return self._quotas.check_quota(quota_id, subject, amount)

    def consume_quota(
        self,
        quota_id: str,
        subject: str,
        amount: int = 1
    ) -> bool:
        """Consume quota."""
        return self._quotas.consume_quota(quota_id, subject, amount)

    def get_quota_usage(self, quota_id: str, subject: str) -> QuotaUsage:
        """Get quota usage."""
        return self._quotas.get_usage(quota_id, subject)

    # -------------------------------------------------------------------------
    # COMBINED THROTTLE + QUOTA
    # -------------------------------------------------------------------------

    def check_and_acquire(
        self,
        throttler_name: str,
        quota_id: Optional[str] = None,
        subject: Optional[str] = None,
        tokens: int = 1
    ) -> Tuple[ThrottleResponse, Optional[QuotaUsage]]:
        """Check quota and acquire throttle token."""
        # Check quota first
        if quota_id and subject:
            allowed, usage = self.check_quota(quota_id, subject, tokens)
            if not allowed:
                return (
                    ThrottleResponse(result=ThrottleResult.REJECTED),
                    usage
                )
        else:
            usage = None

        # Acquire throttle token
        response = self.acquire(throttler_name, tokens)

        # Consume quota if allowed
        if response.result == ThrottleResult.ALLOWED and quota_id and subject:
            self.consume_quota(quota_id, subject, tokens)

        return (response, usage)

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self, throttler_name: str) -> ThrottleStats:
        """Get statistics for a throttler."""
        with self._lock:
            return self._stats.get(throttler_name, ThrottleStats())

    def get_all_stats(self) -> Dict[str, ThrottleStats]:
        """Get statistics for all throttlers."""
        with self._lock:
            return dict(self._stats)

    def reset_stats(self, throttler_name: Optional[str] = None) -> None:
        """Reset statistics."""
        with self._lock:
            if throttler_name:
                self._stats[throttler_name] = ThrottleStats()
            else:
                self._stats.clear()

    # -------------------------------------------------------------------------
    # STATE
    # -------------------------------------------------------------------------

    def get_state(self, throttler_name: str) -> Optional[ThrottleState]:
        """Get throttler state."""
        with self._lock:
            throttler = self._throttlers.get(throttler_name)
            if throttler:
                return throttler.get_state()
            return None

    def reset(self, throttler_name: str) -> bool:
        """Reset a throttler."""
        with self._lock:
            throttler = self._throttlers.get(throttler_name)
            if throttler:
                throttler.reset()
                return True
            return False

    def list_throttlers(self) -> List[str]:
        """List all throttler names."""
        with self._lock:
            return list(self._throttlers.keys())


# =============================================================================
# DECORATORS
# =============================================================================

def throttled(
    manager: ThrottleManager,
    throttler_name: str,
    tokens: int = 1,
    wait: bool = True
):
    """Decorator for throttled functions."""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            response = await manager.acquire_async(
                throttler_name, tokens, wait=wait
            )

            if response.result != ThrottleResult.ALLOWED:
                raise Exception(f"Throttled: {response.result.value}")

            return await func(*args, **kwargs)

        def sync_wrapper(*args, **kwargs):
            response = manager.acquire(throttler_name, tokens)

            if response.result != ThrottleResult.ALLOWED:
                raise Exception(f"Throttled: {response.result.value}")

            return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Throttle Manager."""
    print("=" * 70)
    print("BAEL - THROTTLE MANAGER DEMO")
    print("Advanced Throttling for AI Agents")
    print("=" * 70)
    print()

    manager = ThrottleManager()

    # 1. Token Bucket Throttler
    print("1. TOKEN BUCKET THROTTLER:")
    print("-" * 40)

    manager.create_throttler(ThrottleConfig(
        name="api",
        algorithm=ThrottleAlgorithm.TOKEN_BUCKET,
        rate=5.0,
        burst=10
    ))

    results = []
    for i in range(15):
        response = manager.acquire("api")
        results.append(response.result.value)

    print(f"   15 requests: {results}")
    print()

    # 2. Sliding Window Throttler
    print("2. SLIDING WINDOW THROTTLER:")
    print("-" * 40)

    manager.create_throttler(ThrottleConfig(
        name="sliding",
        algorithm=ThrottleAlgorithm.SLIDING_WINDOW,
        rate=3.0,
        window_size=1.0
    ))

    for i in range(5):
        response = manager.acquire("sliding")
        print(f"   Request {i+1}: {response.result.value}, remaining: {response.remaining}")
    print()

    # 3. Fixed Window Throttler
    print("3. FIXED WINDOW THROTTLER:")
    print("-" * 40)

    manager.create_throttler(ThrottleConfig(
        name="fixed",
        algorithm=ThrottleAlgorithm.FIXED_WINDOW,
        rate=4.0,
        window_size=1.0
    ))

    for i in range(6):
        response = manager.acquire("fixed")
        print(f"   Request {i+1}: {response.result.value}")
    print()

    # 4. Leaky Bucket Throttler
    print("4. LEAKY BUCKET THROTTLER:")
    print("-" * 40)

    manager.create_throttler(ThrottleConfig(
        name="leaky",
        algorithm=ThrottleAlgorithm.LEAKY_BUCKET,
        rate=2.0,
        burst=5
    ))

    for i in range(7):
        response = manager.acquire("leaky")
        print(f"   Request {i+1}: {response.result.value}")
    print()

    # 5. Async Throttling with Wait
    print("5. ASYNC THROTTLING WITH WAIT:")
    print("-" * 40)

    manager.reset("api")

    async def make_request(i):
        response = await manager.acquire_async("api", wait=True)
        return (i, response.result.value)

    tasks = [make_request(i) for i in range(5)]
    results = await asyncio.gather(*tasks)

    for i, result in results:
        print(f"   Request {i}: {result}")
    print()

    # 6. Priority Queue
    print("6. PRIORITY QUEUE:")
    print("-" * 40)

    manager.create_throttler(ThrottleConfig(
        name="queued",
        algorithm=ThrottleAlgorithm.TOKEN_BUCKET,
        rate=1.0,
        burst=2,
        queue_enabled=True,
        queue_size=10
    ))

    # Make requests with different priorities
    for i, priority in enumerate([
        Priority.LOW, Priority.NORMAL, Priority.HIGH, Priority.CRITICAL
    ]):
        response = manager.acquire("queued", priority=priority)
        print(f"   {priority.name}: {response.result.value}")

    print(f"   Queue size: {manager.get_queue_size('queued')}")
    print()

    # 7. Quota Management
    print("7. QUOTA MANAGEMENT:")
    print("-" * 40)

    manager.create_quota(QuotaConfig(
        quota_id="daily_api",
        name="Daily API Quota",
        limit=100,
        period=QuotaPeriod.DAY
    ))

    for i in range(3):
        manager.consume_quota("daily_api", "user123", amount=25)
        usage = manager.get_quota_usage("daily_api", "user123")
        print(f"   After {(i+1)*25}: {usage.used}/{usage.limit} ({usage.percentage:.1f}%)")
    print()

    # 8. Combined Throttle + Quota
    print("8. COMBINED THROTTLE + QUOTA:")
    print("-" * 40)

    manager.reset("api")

    for i in range(3):
        response, usage = manager.check_and_acquire(
            "api",
            quota_id="daily_api",
            subject="user456",
            tokens=1
        )
        print(f"   Request {i+1}: {response.result.value}, "
              f"quota: {usage.used}/{usage.limit}" if usage else "")
    print()

    # 9. Adaptive Throttler
    print("9. ADAPTIVE THROTTLER:")
    print("-" * 40)

    manager.create_throttler(ThrottleConfig(
        name="adaptive",
        algorithm=ThrottleAlgorithm.ADAPTIVE,
        rate=5.0,
        burst=10
    ))

    throttler = manager.get_throttler("adaptive")

    for i in range(10):
        response = manager.acquire("adaptive")
        if isinstance(throttler, AdaptiveThrottler):
            if response.result == ThrottleResult.ALLOWED:
                throttler.record_success()
            else:
                throttler.record_failure()

    state = manager.get_state("adaptive")
    print(f"   Tokens: {state.tokens:.1f}")
    print()

    # 10. Statistics
    print("10. STATISTICS:")
    print("-" * 40)

    stats = manager.get_stats("api")

    print(f"   Total requests: {stats.total_requests}")
    print(f"   Allowed: {stats.allowed}")
    print(f"   Throttled: {stats.throttled}")
    print(f"   Queued: {stats.queued}")
    print(f"   Rejected: {stats.rejected}")
    print()

    # 11. List Throttlers
    print("11. LIST THROTTLERS:")
    print("-" * 40)

    throttlers = manager.list_throttlers()

    for name in throttlers:
        state = manager.get_state(name)
        print(f"   {name}: tokens={state.tokens:.1f}" if state else f"   {name}")
    print()

    # 12. Reset and Cleanup
    print("12. RESET AND CLEANUP:")
    print("-" * 40)

    manager.reset("api")
    manager.reset_stats("api")

    print("   Reset api throttler and stats")

    stats = manager.get_stats("api")
    print(f"   Stats after reset: {stats.total_requests} requests")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Throttle Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
