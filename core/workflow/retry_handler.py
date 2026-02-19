"""
BAEL Retry Handler
===================

Retry logic and error recovery for workflows.
Handles transient failures gracefully.

Features:
- Multiple backoff strategies
- Circuit breaker pattern
- Retry policies
- Error classification
- Recovery hooks
"""

import asyncio
import hashlib
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Type

logger = logging.getLogger(__name__)


class BackoffStrategy(Enum):
    """Backoff strategies for retries."""
    CONSTANT = "constant"  # Same delay each time
    LINEAR = "linear"  # delay * attempt
    EXPONENTIAL = "exponential"  # base ^ attempt
    FIBONACCI = "fibonacci"  # Fibonacci sequence
    DECORRELATED_JITTER = "decorrelated_jitter"  # AWS style


class ErrorCategory(Enum):
    """Categories of errors."""
    TRANSIENT = "transient"  # Temporary, worth retrying
    PERMANENT = "permanent"  # Won't succeed on retry
    RESOURCE = "resource"  # Resource exhaustion
    NETWORK = "network"  # Network issues
    TIMEOUT = "timeout"  # Timeouts
    RATE_LIMIT = "rate_limit"  # Rate limiting
    UNKNOWN = "unknown"  # Unknown error


@dataclass
class RetryPolicy:
    """Policy for retry behavior."""
    # Retry limits
    max_attempts: int = 3
    max_delay_seconds: float = 60.0

    # Backoff
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    base_delay_seconds: float = 1.0
    backoff_multiplier: float = 2.0

    # Jitter
    jitter: bool = True
    jitter_range: float = 0.3  # +/- 30%

    # Retry conditions
    retryable_errors: Set[Type[Exception]] = field(default_factory=lambda: {
        TimeoutError,
        ConnectionError,
        asyncio.TimeoutError,
    })
    retryable_categories: Set[ErrorCategory] = field(default_factory=lambda: {
        ErrorCategory.TRANSIENT,
        ErrorCategory.NETWORK,
        ErrorCategory.TIMEOUT,
        ErrorCategory.RATE_LIMIT,
    })

    # Circuit breaker
    circuit_breaker_enabled: bool = True
    failure_threshold: int = 5
    recovery_timeout_seconds: float = 30.0


@dataclass
class RetryResult:
    """Result of retry operation."""
    success: bool
    value: Any = None
    error: Optional[Exception] = None

    # Attempts
    attempts: int = 0
    total_delay_seconds: float = 0.0

    # Error info
    error_category: ErrorCategory = ErrorCategory.UNKNOWN

    # History
    attempt_errors: List[str] = field(default_factory=list)
    attempt_times: List[float] = field(default_factory=list)


class CircuitBreaker:
    """
    Circuit breaker for preventing cascade failures.
    """

    class State(Enum):
        CLOSED = "closed"  # Normal operation
        OPEN = "open"  # Failing, reject requests
        HALF_OPEN = "half_open"  # Testing recovery

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

        self.state = self.State.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.success_count = 0

    def can_execute(self) -> bool:
        """Check if execution is allowed."""
        if self.state == self.State.CLOSED:
            return True

        if self.state == self.State.OPEN:
            # Check if recovery timeout passed
            if self.last_failure_time:
                elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                if elapsed >= self.recovery_timeout:
                    self.state = self.State.HALF_OPEN
                    return True
            return False

        # Half-open: allow one request
        return True

    def record_success(self) -> None:
        """Record successful execution."""
        if self.state == self.State.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= 2:  # Require 2 successes
                self.state = self.State.CLOSED
                self.failure_count = 0
        else:
            self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self) -> None:
        """Record failed execution."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        self.success_count = 0

        if self.failure_count >= self.failure_threshold:
            self.state = self.State.OPEN

    def reset(self) -> None:
        """Reset circuit breaker."""
        self.state = self.State.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None


class RetryHandler:
    """
    Retry handler for BAEL.

    Manages retry logic with various strategies.
    """

    # Known transient error messages
    TRANSIENT_PATTERNS = [
        "timeout",
        "temporary",
        "retry",
        "rate limit",
        "too many requests",
        "service unavailable",
        "connection reset",
        "connection refused",
    ]

    def __init__(
        self,
        policy: Optional[RetryPolicy] = None,
    ):
        self.policy = policy or RetryPolicy()

        # Circuit breakers per resource
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}

        # Fibonacci cache
        self._fib_cache = [0, 1]

        # Stats
        self.stats = {
            "total_attempts": 0,
            "total_retries": 0,
            "successes": 0,
            "permanent_failures": 0,
        }

    async def execute(
        self,
        func: Callable,
        *args,
        resource_id: str = "default",
        **kwargs,
    ) -> RetryResult:
        """
        Execute function with retry logic.

        Args:
            func: Function to execute
            resource_id: Resource identifier for circuit breaker
            *args, **kwargs: Function arguments

        Returns:
            Retry result
        """
        result = RetryResult()
        total_delay = 0.0

        # Get circuit breaker
        circuit_breaker = self._get_circuit_breaker(resource_id)

        for attempt in range(1, self.policy.max_attempts + 1):
            result.attempts = attempt
            self.stats["total_attempts"] += 1

            # Check circuit breaker
            if self.policy.circuit_breaker_enabled and not circuit_breaker.can_execute():
                result.success = False
                result.error = Exception("Circuit breaker open")
                result.error_category = ErrorCategory.RESOURCE
                return result

            try:
                start = time.time()

                # Execute
                if asyncio.iscoroutinefunction(func):
                    value = await func(*args, **kwargs)
                else:
                    value = func(*args, **kwargs)

                result.attempt_times.append(time.time() - start)
                result.success = True
                result.value = value

                circuit_breaker.record_success()
                self.stats["successes"] += 1

                return result

            except Exception as e:
                result.attempt_times.append(time.time() - start if 'start' in dir() else 0)
                result.attempt_errors.append(str(e))
                result.error = e
                result.error_category = self._categorize_error(e)

                circuit_breaker.record_failure()

                # Check if should retry
                if not self._should_retry(e, result.error_category, attempt):
                    result.success = False
                    self.stats["permanent_failures"] += 1
                    return result

                # Calculate delay
                delay = self._calculate_delay(attempt)
                total_delay += delay
                result.total_delay_seconds = total_delay

                self.stats["total_retries"] += 1

                logger.warning(
                    f"Retry {attempt}/{self.policy.max_attempts} after {delay:.2f}s: {e}"
                )

                await asyncio.sleep(delay)

        result.success = False
        self.stats["permanent_failures"] += 1

        return result

    def _get_circuit_breaker(self, resource_id: str) -> CircuitBreaker:
        """Get or create circuit breaker for resource."""
        if resource_id not in self._circuit_breakers:
            self._circuit_breakers[resource_id] = CircuitBreaker(
                failure_threshold=self.policy.failure_threshold,
                recovery_timeout=self.policy.recovery_timeout_seconds,
            )
        return self._circuit_breakers[resource_id]

    def _categorize_error(self, error: Exception) -> ErrorCategory:
        """Categorize an error."""
        error_msg = str(error).lower()

        # Check error type
        if isinstance(error, TimeoutError):
            return ErrorCategory.TIMEOUT
        if isinstance(error, ConnectionError):
            return ErrorCategory.NETWORK

        # Check message patterns
        for pattern in self.TRANSIENT_PATTERNS:
            if pattern in error_msg:
                if "rate" in pattern:
                    return ErrorCategory.RATE_LIMIT
                return ErrorCategory.TRANSIENT

        # Check if in retryable errors
        for error_type in self.policy.retryable_errors:
            if isinstance(error, error_type):
                return ErrorCategory.TRANSIENT

        return ErrorCategory.UNKNOWN

    def _should_retry(
        self,
        error: Exception,
        category: ErrorCategory,
        attempt: int,
    ) -> bool:
        """Check if should retry."""
        if attempt >= self.policy.max_attempts:
            return False

        # Check category
        if category in self.policy.retryable_categories:
            return True

        # Check error type
        for error_type in self.policy.retryable_errors:
            if isinstance(error, error_type):
                return True

        return False

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay before next retry."""
        base = self.policy.base_delay_seconds

        if self.policy.backoff_strategy == BackoffStrategy.CONSTANT:
            delay = base
        elif self.policy.backoff_strategy == BackoffStrategy.LINEAR:
            delay = base * attempt
        elif self.policy.backoff_strategy == BackoffStrategy.EXPONENTIAL:
            delay = base * (self.policy.backoff_multiplier ** (attempt - 1))
        elif self.policy.backoff_strategy == BackoffStrategy.FIBONACCI:
            delay = base * self._fibonacci(attempt)
        elif self.policy.backoff_strategy == BackoffStrategy.DECORRELATED_JITTER:
            # AWS decorrelated jitter
            prev_delay = base if attempt == 1 else base * (self.policy.backoff_multiplier ** (attempt - 2))
            delay = random.uniform(base, prev_delay * 3)
        else:
            delay = base

        # Apply jitter
        if self.policy.jitter:
            jitter = delay * self.policy.jitter_range
            delay = delay + random.uniform(-jitter, jitter)

        # Cap at max
        delay = min(delay, self.policy.max_delay_seconds)

        return max(0, delay)

    def _fibonacci(self, n: int) -> int:
        """Get nth Fibonacci number."""
        while len(self._fib_cache) <= n:
            self._fib_cache.append(
                self._fib_cache[-1] + self._fib_cache[-2]
            )
        return self._fib_cache[n]

    def reset_circuit_breaker(self, resource_id: str) -> None:
        """Reset a circuit breaker."""
        if resource_id in self._circuit_breakers:
            self._circuit_breakers[resource_id].reset()

    def get_circuit_breaker_status(self, resource_id: str) -> Dict[str, Any]:
        """Get circuit breaker status."""
        if resource_id not in self._circuit_breakers:
            return {"state": "not_found"}

        cb = self._circuit_breakers[resource_id]
        return {
            "state": cb.state.value,
            "failure_count": cb.failure_count,
            "last_failure": cb.last_failure_time,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get handler statistics."""
        return {
            **self.stats,
            "success_rate": (
                self.stats["successes"] /
                max(self.stats["total_attempts"], 1)
            ),
            "circuit_breakers": len(self._circuit_breakers),
        }


def demo():
    """Demonstrate retry handler."""
    import asyncio

    print("=" * 60)
    print("BAEL Retry Handler Demo")
    print("=" * 60)

    policy = RetryPolicy(
        max_attempts=5,
        backoff_strategy=BackoffStrategy.EXPONENTIAL,
        base_delay_seconds=0.1,
        backoff_multiplier=2.0,
        jitter=True,
    )

    handler = RetryHandler(policy)

    # Simulate flaky function
    attempt_count = 0

    async def flaky_operation():
        nonlocal attempt_count
        attempt_count += 1

        if attempt_count < 3:
            raise ConnectionError(f"Connection failed (attempt {attempt_count})")

        return {"status": "success", "attempt": attempt_count}

    print("\nTest 1: Flaky operation (succeeds on 3rd try)")
    attempt_count = 0

    async def run_test1():
        result = await handler.execute(flaky_operation, resource_id="api_1")
        return result

    result = asyncio.run(run_test1())
    print(f"  Success: {result.success}")
    print(f"  Attempts: {result.attempts}")
    print(f"  Value: {result.value}")
    print(f"  Total delay: {result.total_delay_seconds:.3f}s")
    print(f"  Errors: {result.attempt_errors}")

    # Test permanent failure
    print("\nTest 2: Permanent failure")

    async def always_fails():
        raise ValueError("Permanent error - will never succeed")

    async def run_test2():
        result = await handler.execute(always_fails, resource_id="api_2")
        return result

    result = asyncio.run(run_test2())
    print(f"  Success: {result.success}")
    print(f"  Attempts: {result.attempts}")
    print(f"  Error category: {result.error_category.value}")

    # Test circuit breaker
    print("\nTest 3: Circuit breaker")

    fail_count = 0

    async def trigger_circuit_breaker():
        nonlocal fail_count
        fail_count += 1
        raise ConnectionError(f"Service down (fail #{fail_count})")

    async def run_test3():
        for i in range(3):
            result = await handler.execute(
                trigger_circuit_breaker,
                resource_id="api_3",
            )
            status = handler.get_circuit_breaker_status("api_3")
            print(f"  Run {i+1}: {status['state']}, failures: {status['failure_count']}")

    asyncio.run(run_test3())

    # Backoff strategies demo
    print("\nBackoff strategies (delays for 5 attempts):")

    for strategy in BackoffStrategy:
        temp_policy = RetryPolicy(
            backoff_strategy=strategy,
            base_delay_seconds=1.0,
            jitter=False,
        )
        temp_handler = RetryHandler(temp_policy)

        delays = [temp_handler._calculate_delay(i) for i in range(1, 6)]
        delays_str = ", ".join(f"{d:.2f}s" for d in delays)
        print(f"  {strategy.value}: {delays_str}")

    print(f"\nStats: {handler.get_stats()}")


if __name__ == "__main__":
    demo()
