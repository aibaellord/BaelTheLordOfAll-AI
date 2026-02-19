"""
BAEL Resilience Patterns
========================

Advanced enterprise resilience patterns:
- Enhanced circuit breakers
- Sophisticated retry policies
- Bulkhead pattern
- Rate limiting algorithms
- Timeout handling
- Fallback strategies

"Ba'el bends but never breaks." — Ba'el
"""

import asyncio
import logging
import time
import random
import math
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Set, Tuple, Union, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import deque
from functools import wraps
import threading

logger = logging.getLogger("BAEL.ResiliencePatterns")

T = TypeVar('T')


# ============================================================================
# ENUMS
# ============================================================================

class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing, reject calls
    HALF_OPEN = "half_open" # Testing recovery


class RetryStrategy(Enum):
    """Retry strategies."""
    IMMEDIATE = "immediate"     # Retry immediately
    FIXED = "fixed"             # Fixed delay
    LINEAR = "linear"           # Linear backoff
    EXPONENTIAL = "exponential" # Exponential backoff
    FIBONACCI = "fibonacci"     # Fibonacci backoff
    JITTER = "jitter"           # Random jitter


class RateLimitAlgorithm(Enum):
    """Rate limiting algorithms."""
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"


class BulkheadType(Enum):
    """Bulkhead isolation types."""
    SEMAPHORE = "semaphore"     # Limits concurrent calls
    THREAD_POOL = "thread_pool" # Separate thread pool


# ============================================================================
# CONFIGURATIONS
# ============================================================================

@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5          # Failures before opening
    success_threshold: int = 3          # Successes to close
    timeout_seconds: float = 30.0       # Time in open state
    half_open_max_calls: int = 3        # Calls allowed in half-open
    failure_rate_threshold: float = 0.5 # Failure rate to open
    slow_call_threshold: float = 5.0    # Seconds for slow call
    slow_call_rate_threshold: float = 0.5


@dataclass
class RetryConfig:
    """Retry configuration."""
    max_attempts: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    base_delay: float = 1.0         # Base delay in seconds
    max_delay: float = 60.0         # Maximum delay
    jitter: float = 0.1             # Random jitter factor
    retryable_exceptions: Tuple[type, ...] = (Exception,)
    non_retryable_exceptions: Tuple[type, ...] = ()


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.TOKEN_BUCKET
    rate: float = 10.0              # Requests per second
    burst: int = 20                 # Burst capacity
    window_seconds: int = 60        # Window for sliding/fixed window


@dataclass
class BulkheadConfig:
    """Bulkhead configuration."""
    bulkhead_type: BulkheadType = BulkheadType.SEMAPHORE
    max_concurrent: int = 10
    max_waiting: int = 100
    max_wait_seconds: float = 30.0


@dataclass
class ResilienceConfig:
    """Overall resilience configuration."""
    enable_circuit_breaker: bool = True
    enable_retry: bool = True
    enable_rate_limit: bool = True
    enable_bulkhead: bool = True
    enable_timeout: bool = True
    default_timeout: float = 30.0


# ============================================================================
# CIRCUIT BREAKER
# ============================================================================

class CircuitBreaker:
    """
    Circuit breaker pattern implementation.

    Prevents cascading failures by failing fast when a service is unavailable.
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        """Initialize circuit breaker."""
        self.name = name
        self.config = config or CircuitBreakerConfig()

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._half_open_calls = 0

        # Metrics window
        self._call_results: deque = deque(maxlen=100)

        self._lock = threading.RLock()

        # Statistics
        self._stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'rejected_calls': 0,
            'state_changes': 0
        }

    @property
    def state(self) -> CircuitState:
        """Get current state."""
        with self._lock:
            self._check_state_timeout()
            return self._state

    def _check_state_timeout(self) -> None:
        """Check if open circuit should transition to half-open."""
        if self._state == CircuitState.OPEN:
            if self._last_failure_time:
                elapsed = (datetime.now() - self._last_failure_time).total_seconds()
                if elapsed >= self.config.timeout_seconds:
                    self._transition_to(CircuitState.HALF_OPEN)

    def _transition_to(self, state: CircuitState) -> None:
        """Transition to a new state."""
        if self._state != state:
            old_state = self._state
            self._state = state
            self._stats['state_changes'] += 1

            if state == CircuitState.CLOSED:
                self._failure_count = 0
                self._success_count = 0
            elif state == CircuitState.HALF_OPEN:
                self._half_open_calls = 0

            logger.info(f"Circuit breaker '{self.name}': {old_state.value} -> {state.value}")

    def _record_success(self) -> None:
        """Record a successful call."""
        with self._lock:
            self._call_results.append(True)
            self._stats['successful_calls'] += 1

            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    self._transition_to(CircuitState.CLOSED)

    def _record_failure(self) -> None:
        """Record a failed call."""
        with self._lock:
            self._call_results.append(False)
            self._stats['failed_calls'] += 1
            self._last_failure_time = datetime.now()

            if self._state == CircuitState.CLOSED:
                self._failure_count += 1

                # Check failure threshold
                if self._failure_count >= self.config.failure_threshold:
                    self._transition_to(CircuitState.OPEN)

                # Check failure rate
                if len(self._call_results) >= 10:
                    failure_rate = 1 - (sum(self._call_results) / len(self._call_results))
                    if failure_rate >= self.config.failure_rate_threshold:
                        self._transition_to(CircuitState.OPEN)

            elif self._state == CircuitState.HALF_OPEN:
                self._transition_to(CircuitState.OPEN)

    def allow_request(self) -> bool:
        """Check if a request is allowed."""
        with self._lock:
            self._check_state_timeout()
            self._stats['total_calls'] += 1

            if self._state == CircuitState.CLOSED:
                return True

            elif self._state == CircuitState.OPEN:
                self._stats['rejected_calls'] += 1
                return False

            elif self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls < self.config.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                self._stats['rejected_calls'] += 1
                return False

        return False

    async def execute(
        self,
        func: Callable,
        *args,
        fallback: Optional[Callable] = None,
        **kwargs
    ) -> Any:
        """Execute a function with circuit breaker protection."""
        if not self.allow_request():
            if fallback:
                return await self._execute_func(fallback, *args, **kwargs)
            raise CircuitBreakerOpenError(f"Circuit breaker '{self.name}' is open")

        try:
            start_time = time.time()
            result = await self._execute_func(func, *args, **kwargs)
            elapsed = time.time() - start_time

            # Check for slow calls
            if elapsed > self.config.slow_call_threshold:
                self._record_failure()
            else:
                self._record_success()

            return result

        except Exception as e:
            self._record_failure()

            if fallback:
                return await self._execute_func(fallback, *args, **kwargs)
            raise

    async def _execute_func(self, func: Callable, *args, **kwargs) -> Any:
        """Execute a function (sync or async)."""
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        return func(*args, **kwargs)

    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        with self._lock:
            return {
                **self._stats,
                'state': self._state.value,
                'failure_count': self._failure_count,
                'success_count': self._success_count
            }

    def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        with self._lock:
            self._transition_to(CircuitState.CLOSED)
            self._failure_count = 0
            self._success_count = 0
            self._call_results.clear()


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


# ============================================================================
# RETRY HANDLER
# ============================================================================

class RetryHandler:
    """
    Retry handler with multiple strategies.
    """

    def __init__(self, config: Optional[RetryConfig] = None):
        """Initialize retry handler."""
        self.config = config or RetryConfig()
        self._fibonacci_cache = [0, 1]

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for an attempt."""
        strategy = self.config.strategy
        base = self.config.base_delay

        if strategy == RetryStrategy.IMMEDIATE:
            delay = 0
        elif strategy == RetryStrategy.FIXED:
            delay = base
        elif strategy == RetryStrategy.LINEAR:
            delay = base * attempt
        elif strategy == RetryStrategy.EXPONENTIAL:
            delay = base * (2 ** attempt)
        elif strategy == RetryStrategy.FIBONACCI:
            delay = base * self._get_fibonacci(attempt)
        elif strategy == RetryStrategy.JITTER:
            delay = base * (2 ** attempt)
        else:
            delay = base

        # Apply jitter
        if self.config.jitter > 0:
            jitter = random.uniform(-self.config.jitter, self.config.jitter)
            delay *= (1 + jitter)

        # Cap at max delay
        return min(delay, self.config.max_delay)

    def _get_fibonacci(self, n: int) -> int:
        """Get nth Fibonacci number."""
        while len(self._fibonacci_cache) <= n:
            self._fibonacci_cache.append(
                self._fibonacci_cache[-1] + self._fibonacci_cache[-2]
            )
        return self._fibonacci_cache[n]

    def _should_retry(self, exception: Exception) -> bool:
        """Check if exception should be retried."""
        # Check non-retryable first
        if isinstance(exception, self.config.non_retryable_exceptions):
            return False

        # Check retryable
        return isinstance(exception, self.config.retryable_exceptions)

    async def execute(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Execute a function with retry logic."""
        last_exception = None

        for attempt in range(self.config.max_attempts):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                return func(*args, **kwargs)

            except Exception as e:
                last_exception = e

                if not self._should_retry(e):
                    raise

                if attempt < self.config.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    logger.warning(
                        f"Retry attempt {attempt + 1}/{self.config.max_attempts} "
                        f"after {delay:.2f}s: {e}"
                    )
                    await asyncio.sleep(delay)

        raise last_exception


# ============================================================================
# RATE LIMITER
# ============================================================================

class RateLimiter:
    """
    Rate limiter with multiple algorithms.
    """

    def __init__(
        self,
        name: str,
        config: Optional[RateLimitConfig] = None
    ):
        """Initialize rate limiter."""
        self.name = name
        self.config = config or RateLimitConfig()

        # Token bucket
        self._tokens = float(config.burst if config else 20)
        self._last_refill = time.time()

        # Sliding window
        self._request_times: deque = deque()

        # Fixed window
        self._window_start = time.time()
        self._window_count = 0

        self._lock = threading.RLock()

        # Statistics
        self._stats = {
            'total_requests': 0,
            'allowed_requests': 0,
            'rejected_requests': 0
        }

    def _refill_tokens(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self._last_refill
        self._tokens = min(
            self.config.burst,
            self._tokens + (elapsed * self.config.rate)
        )
        self._last_refill = now

    def _token_bucket_allow(self) -> bool:
        """Token bucket algorithm."""
        with self._lock:
            self._refill_tokens()

            if self._tokens >= 1:
                self._tokens -= 1
                return True
            return False

    def _sliding_window_allow(self) -> bool:
        """Sliding window algorithm."""
        with self._lock:
            now = time.time()
            window_start = now - self.config.window_seconds

            # Remove old requests
            while self._request_times and self._request_times[0] < window_start:
                self._request_times.popleft()

            max_requests = int(self.config.rate * self.config.window_seconds)

            if len(self._request_times) < max_requests:
                self._request_times.append(now)
                return True
            return False

    def _fixed_window_allow(self) -> bool:
        """Fixed window algorithm."""
        with self._lock:
            now = time.time()

            # Check if we need a new window
            if now - self._window_start >= self.config.window_seconds:
                self._window_start = now
                self._window_count = 0

            max_requests = int(self.config.rate * self.config.window_seconds)

            if self._window_count < max_requests:
                self._window_count += 1
                return True
            return False

    def allow(self) -> bool:
        """Check if a request is allowed."""
        self._stats['total_requests'] += 1

        if self.config.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
            allowed = self._token_bucket_allow()
        elif self.config.algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
            allowed = self._sliding_window_allow()
        elif self.config.algorithm == RateLimitAlgorithm.FIXED_WINDOW:
            allowed = self._fixed_window_allow()
        else:
            allowed = self._token_bucket_allow()

        if allowed:
            self._stats['allowed_requests'] += 1
        else:
            self._stats['rejected_requests'] += 1

        return allowed

    async def acquire(self, timeout: float = 30.0) -> bool:
        """Wait until rate limit allows."""
        start = time.time()

        while time.time() - start < timeout:
            if self.allow():
                return True
            await asyncio.sleep(0.1)

        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics."""
        with self._lock:
            return {
                **self._stats,
                'current_tokens': self._tokens if hasattr(self, '_tokens') else 0
            }


class RateLimitExceededError(Exception):
    """Raised when rate limit is exceeded."""
    pass


# ============================================================================
# BULKHEAD
# ============================================================================

class Bulkhead:
    """
    Bulkhead pattern for isolation.

    Limits concurrent operations to prevent resource exhaustion.
    """

    def __init__(
        self,
        name: str,
        config: Optional[BulkheadConfig] = None
    ):
        """Initialize bulkhead."""
        self.name = name
        self.config = config or BulkheadConfig()

        self._semaphore = asyncio.Semaphore(self.config.max_concurrent)
        self._waiting = 0
        self._lock = threading.RLock()

        # Statistics
        self._stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'rejected_calls': 0,
            'current_concurrent': 0,
            'max_concurrent_reached': 0
        }

    async def acquire(self) -> bool:
        """Acquire a slot in the bulkhead."""
        with self._lock:
            self._stats['total_calls'] += 1

            if self._waiting >= self.config.max_waiting:
                self._stats['rejected_calls'] += 1
                return False

            self._waiting += 1

        try:
            acquired = await asyncio.wait_for(
                self._semaphore.acquire(),
                timeout=self.config.max_wait_seconds
            )

            if acquired:
                with self._lock:
                    self._stats['current_concurrent'] += 1
                    if self._stats['current_concurrent'] > self._stats['max_concurrent_reached']:
                        self._stats['max_concurrent_reached'] = self._stats['current_concurrent']

            return acquired

        except asyncio.TimeoutError:
            with self._lock:
                self._stats['rejected_calls'] += 1
            return False
        finally:
            with self._lock:
                self._waiting -= 1

    def release(self) -> None:
        """Release a slot in the bulkhead."""
        self._semaphore.release()
        with self._lock:
            self._stats['current_concurrent'] = max(0, self._stats['current_concurrent'] - 1)
            self._stats['successful_calls'] += 1

    async def execute(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Execute a function with bulkhead protection."""
        if not await self.acquire():
            raise BulkheadFullError(f"Bulkhead '{self.name}' is full")

        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return func(*args, **kwargs)
        finally:
            self.release()

    def get_stats(self) -> Dict[str, Any]:
        """Get bulkhead statistics."""
        with self._lock:
            return {
                **self._stats,
                'waiting': self._waiting,
                'available_slots': self.config.max_concurrent - self._stats['current_concurrent']
            }


class BulkheadFullError(Exception):
    """Raised when bulkhead is full."""
    pass


# ============================================================================
# TIMEOUT HANDLER
# ============================================================================

class TimeoutHandler:
    """
    Timeout handler for operations.
    """

    def __init__(self, default_timeout: float = 30.0):
        """Initialize timeout handler."""
        self.default_timeout = default_timeout

    async def execute(
        self,
        func: Callable,
        *args,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Any:
        """Execute a function with timeout."""
        timeout = timeout or self.default_timeout

        try:
            if asyncio.iscoroutinefunction(func):
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout
                )
            else:
                return await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, lambda: func(*args, **kwargs)
                    ),
                    timeout=timeout
                )
        except asyncio.TimeoutError:
            raise TimeoutError(f"Operation timed out after {timeout}s")


# ============================================================================
# FALLBACK HANDLER
# ============================================================================

class FallbackHandler:
    """
    Fallback handler for failed operations.
    """

    def __init__(self):
        """Initialize fallback handler."""
        self._fallbacks: Dict[str, Callable] = {}

    def register(
        self,
        name: str,
        fallback: Callable
    ) -> None:
        """Register a fallback function."""
        self._fallbacks[name] = fallback

    async def execute(
        self,
        func: Callable,
        *args,
        fallback: Optional[Callable] = None,
        fallback_name: Optional[str] = None,
        **kwargs
    ) -> Any:
        """Execute a function with fallback."""
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return func(*args, **kwargs)

        except Exception as e:
            # Try provided fallback
            if fallback:
                if asyncio.iscoroutinefunction(fallback):
                    return await fallback(*args, **kwargs)
                return fallback(*args, **kwargs)

            # Try registered fallback
            if fallback_name and fallback_name in self._fallbacks:
                fb = self._fallbacks[fallback_name]
                if asyncio.iscoroutinefunction(fb):
                    return await fb(*args, **kwargs)
                return fb(*args, **kwargs)

            raise


# ============================================================================
# MAIN RESILIENCE ENGINE
# ============================================================================

class ResilienceEngine:
    """
    Main resilience engine combining all patterns.

    Features:
    - Circuit breakers
    - Retry handlers
    - Rate limiters
    - Bulkheads
    - Timeouts
    - Fallbacks

    "Ba'el stands unshaken through any storm." — Ba'el
    """

    def __init__(self, config: Optional[ResilienceConfig] = None):
        """Initialize resilience engine."""
        self.config = config or ResilienceConfig()

        # Pattern instances
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._rate_limiters: Dict[str, RateLimiter] = {}
        self._bulkheads: Dict[str, Bulkhead] = {}

        self._retry_handler = RetryHandler()
        self._timeout_handler = TimeoutHandler(self.config.default_timeout)
        self._fallback_handler = FallbackHandler()

        self._lock = threading.RLock()

        logger.info("ResilienceEngine initialized")

    # ========================================================================
    # CIRCUIT BREAKER
    # ========================================================================

    def get_circuit_breaker(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """Get or create a circuit breaker."""
        with self._lock:
            if name not in self._circuit_breakers:
                self._circuit_breakers[name] = CircuitBreaker(name, config)
            return self._circuit_breakers[name]

    # ========================================================================
    # RATE LIMITER
    # ========================================================================

    def get_rate_limiter(
        self,
        name: str,
        config: Optional[RateLimitConfig] = None
    ) -> RateLimiter:
        """Get or create a rate limiter."""
        with self._lock:
            if name not in self._rate_limiters:
                self._rate_limiters[name] = RateLimiter(name, config)
            return self._rate_limiters[name]

    # ========================================================================
    # BULKHEAD
    # ========================================================================

    def get_bulkhead(
        self,
        name: str,
        config: Optional[BulkheadConfig] = None
    ) -> Bulkhead:
        """Get or create a bulkhead."""
        with self._lock:
            if name not in self._bulkheads:
                self._bulkheads[name] = Bulkhead(name, config)
            return self._bulkheads[name]

    # ========================================================================
    # COMBINED EXECUTION
    # ========================================================================

    async def execute(
        self,
        func: Callable,
        *args,
        circuit_breaker: Optional[str] = None,
        rate_limiter: Optional[str] = None,
        bulkhead: Optional[str] = None,
        timeout: Optional[float] = None,
        retry: bool = False,
        retry_config: Optional[RetryConfig] = None,
        fallback: Optional[Callable] = None,
        **kwargs
    ) -> Any:
        """Execute a function with multiple resilience patterns."""

        # Rate limiting
        if rate_limiter and self.config.enable_rate_limit:
            limiter = self.get_rate_limiter(rate_limiter)
            if not limiter.allow():
                if fallback:
                    return await self._execute_fallback(fallback, *args, **kwargs)
                raise RateLimitExceededError(f"Rate limit exceeded for '{rate_limiter}'")

        # Bulkhead
        if bulkhead and self.config.enable_bulkhead:
            bh = self.get_bulkhead(bulkhead)
            if not await bh.acquire():
                if fallback:
                    return await self._execute_fallback(fallback, *args, **kwargs)
                raise BulkheadFullError(f"Bulkhead '{bulkhead}' is full")

        try:
            # Circuit breaker
            if circuit_breaker and self.config.enable_circuit_breaker:
                cb = self.get_circuit_breaker(circuit_breaker)
                if not cb.allow_request():
                    if fallback:
                        return await self._execute_fallback(fallback, *args, **kwargs)
                    raise CircuitBreakerOpenError(f"Circuit breaker '{circuit_breaker}' is open")

            try:
                # Retry
                if retry and self.config.enable_retry:
                    handler = RetryHandler(retry_config) if retry_config else self._retry_handler

                    if timeout and self.config.enable_timeout:
                        result = await handler.execute(
                            lambda: self._timeout_handler.execute(func, *args, timeout=timeout, **kwargs)
                        )
                    else:
                        result = await handler.execute(func, *args, **kwargs)

                # Timeout only
                elif timeout and self.config.enable_timeout:
                    result = await self._timeout_handler.execute(func, *args, timeout=timeout, **kwargs)

                # Direct execution
                else:
                    if asyncio.iscoroutinefunction(func):
                        result = await func(*args, **kwargs)
                    else:
                        result = func(*args, **kwargs)

                # Record success for circuit breaker
                if circuit_breaker and self.config.enable_circuit_breaker:
                    self._circuit_breakers[circuit_breaker]._record_success()

                return result

            except Exception as e:
                # Record failure for circuit breaker
                if circuit_breaker and self.config.enable_circuit_breaker:
                    self._circuit_breakers[circuit_breaker]._record_failure()

                if fallback:
                    return await self._execute_fallback(fallback, *args, **kwargs)
                raise

        finally:
            # Release bulkhead
            if bulkhead and self.config.enable_bulkhead:
                self._bulkheads[bulkhead].release()

    async def _execute_fallback(
        self,
        fallback: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Execute a fallback function."""
        if asyncio.iscoroutinefunction(fallback):
            return await fallback(*args, **kwargs)
        return fallback(*args, **kwargs)

    # ========================================================================
    # STATUS
    # ========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        return {
            'circuit_breakers': {
                name: cb.get_stats()
                for name, cb in self._circuit_breakers.items()
            },
            'rate_limiters': {
                name: rl.get_stats()
                for name, rl in self._rate_limiters.items()
            },
            'bulkheads': {
                name: bh.get_stats()
                for name, bh in self._bulkheads.items()
            }
        }


# ============================================================================
# CONVENIENCE INSTANCE
# ============================================================================

resilience_engine = ResilienceEngine()


# ============================================================================
# DECORATORS
# ============================================================================

def circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None,
    fallback: Optional[Callable] = None
) -> Callable:
    """Decorator for circuit breaker pattern."""
    def decorator(func: Callable) -> Callable:
        cb = resilience_engine.get_circuit_breaker(name, config)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await cb.execute(func, *args, fallback=fallback, **kwargs)

        return wrapper
    return decorator


def retry(
    config: Optional[RetryConfig] = None
) -> Callable:
    """Decorator for retry pattern."""
    def decorator(func: Callable) -> Callable:
        handler = RetryHandler(config)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await handler.execute(func, *args, **kwargs)

        return wrapper
    return decorator


def rate_limit(
    name: str,
    config: Optional[RateLimitConfig] = None
) -> Callable:
    """Decorator for rate limiting."""
    def decorator(func: Callable) -> Callable:
        limiter = resilience_engine.get_rate_limiter(name, config)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not limiter.allow():
                raise RateLimitExceededError(f"Rate limit exceeded for '{name}'")

            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return func(*args, **kwargs)

        return wrapper
    return decorator


def bulkhead(
    name: str,
    config: Optional[BulkheadConfig] = None
) -> Callable:
    """Decorator for bulkhead pattern."""
    def decorator(func: Callable) -> Callable:
        bh = resilience_engine.get_bulkhead(name, config)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await bh.execute(func, *args, **kwargs)

        return wrapper
    return decorator


def timeout(seconds: float) -> Callable:
    """Decorator for timeout."""
    def decorator(func: Callable) -> Callable:
        handler = TimeoutHandler(seconds)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await handler.execute(func, *args, timeout=seconds, **kwargs)

        return wrapper
    return decorator


def fallback(fallback_func: Callable) -> Callable:
    """Decorator for fallback pattern."""
    def decorator(func: Callable) -> Callable:
        handler = FallbackHandler()

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await handler.execute(func, *args, fallback=fallback_func, **kwargs)

        return wrapper
    return decorator
