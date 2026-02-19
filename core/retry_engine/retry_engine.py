"""
BAEL Retry Engine Implementation
================================

Smart retry strategies and policies.

"Ba'el persists until victory is achieved." — Ba'el
"""

import asyncio
import functools
import logging
import random
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Type, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("BAEL.Retry")


# ============================================================================
# ENUMS
# ============================================================================

class RetryStrategy(Enum):
    """Retry strategies."""
    IMMEDIATE = "immediate"           # Retry immediately
    FIXED = "fixed"                   # Fixed delay
    LINEAR = "linear"                 # Linear backoff
    EXPONENTIAL = "exponential"       # Exponential backoff
    FIBONACCI = "fibonacci"           # Fibonacci sequence
    DECORRELATED_JITTER = "decorrelated_jitter"  # AWS-style
    CUSTOM = "custom"                 # Custom function


class RetryState(Enum):
    """Retry operation state."""
    PENDING = "pending"
    RETRYING = "retrying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    EXHAUSTED = "exhausted"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class RetryAttempt:
    """A single retry attempt."""
    number: int
    started_at: datetime
    ended_at: Optional[datetime] = None

    # Result
    success: bool = False
    error: Optional[Exception] = None
    result: Any = None

    # Timing
    duration_ms: float = 0.0
    delay_before: float = 0.0

    @property
    def duration(self) -> timedelta:
        if self.ended_at:
            return self.ended_at - self.started_at
        return timedelta(0)


@dataclass
class RetryResult:
    """Result of retry operation."""
    success: bool
    result: Any = None
    error: Optional[Exception] = None

    # Attempts
    attempts: List[RetryAttempt] = field(default_factory=list)
    total_attempts: int = 0

    # Timing
    total_duration_ms: float = 0.0

    @property
    def last_attempt(self) -> Optional[RetryAttempt]:
        if self.attempts:
            return self.attempts[-1]
        return None

    @property
    def first_attempt(self) -> Optional[RetryAttempt]:
        if self.attempts:
            return self.attempts[0]
        return None


@dataclass
class RetryPolicy:
    """Retry policy configuration."""
    # Max attempts
    max_attempts: int = 3

    # Strategy
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL

    # Timing
    base_delay: float = 1.0       # Seconds
    max_delay: float = 60.0       # Seconds

    # Jitter
    jitter: bool = True
    jitter_factor: float = 0.1   # 10% jitter

    # Exponential specific
    multiplier: float = 2.0

    # Exception handling
    retryable_exceptions: List[Type[Exception]] = field(
        default_factory=lambda: [Exception]
    )
    non_retryable_exceptions: List[Type[Exception]] = field(default_factory=list)

    # Custom delay function
    delay_function: Optional[Callable[[int], float]] = None

    # Callbacks
    on_retry: Optional[Callable[[RetryAttempt], None]] = None
    on_success: Optional[Callable[[RetryResult], None]] = None
    on_failure: Optional[Callable[[RetryResult], None]] = None


@dataclass
class RetryConfig:
    """Retry engine configuration."""
    default_max_attempts: int = 3
    default_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    default_base_delay: float = 1.0
    collect_metrics: bool = True


# ============================================================================
# DELAY CALCULATORS
# ============================================================================

def immediate_delay(attempt: int, policy: RetryPolicy) -> float:
    """Immediate retry (no delay)."""
    return 0.0


def fixed_delay(attempt: int, policy: RetryPolicy) -> float:
    """Fixed delay between retries."""
    return policy.base_delay


def linear_delay(attempt: int, policy: RetryPolicy) -> float:
    """Linear backoff."""
    delay = policy.base_delay * attempt
    return min(delay, policy.max_delay)


def exponential_delay(attempt: int, policy: RetryPolicy) -> float:
    """Exponential backoff."""
    delay = policy.base_delay * (policy.multiplier ** (attempt - 1))
    return min(delay, policy.max_delay)


def fibonacci_delay(attempt: int, policy: RetryPolicy) -> float:
    """Fibonacci sequence delay."""
    fib = [1, 1]
    for _ in range(attempt):
        fib.append(fib[-1] + fib[-2])
    delay = policy.base_delay * fib[min(attempt, len(fib) - 1)]
    return min(delay, policy.max_delay)


def decorrelated_jitter_delay(attempt: int, policy: RetryPolicy) -> float:
    """AWS-style decorrelated jitter."""
    # sleep = min(cap, random_between(base, sleep * 3))
    # We use a simpler approximation here
    delay = policy.base_delay + random.uniform(0, policy.base_delay * 3 * attempt)
    return min(delay, policy.max_delay)


DELAY_CALCULATORS = {
    RetryStrategy.IMMEDIATE: immediate_delay,
    RetryStrategy.FIXED: fixed_delay,
    RetryStrategy.LINEAR: linear_delay,
    RetryStrategy.EXPONENTIAL: exponential_delay,
    RetryStrategy.FIBONACCI: fibonacci_delay,
    RetryStrategy.DECORRELATED_JITTER: decorrelated_jitter_delay,
}


# ============================================================================
# MAIN ENGINE
# ============================================================================

class RetryEngine:
    """
    Main retry engine.

    Features:
    - Multiple retry strategies
    - Jitter support
    - Exception filtering
    - Callbacks
    - Metrics

    "Ba'el's persistence knows no bounds." — Ba'el
    """

    def __init__(self, config: Optional[RetryConfig] = None):
        """Initialize retry engine."""
        self.config = config or RetryConfig()

        # Metrics
        self._total_retries: int = 0
        self._successful_retries: int = 0
        self._failed_retries: int = 0

        self._lock = threading.RLock()

        logger.info("RetryEngine initialized")

    # ========================================================================
    # DELAY CALCULATION
    # ========================================================================

    def calculate_delay(self, attempt: int, policy: RetryPolicy) -> float:
        """Calculate delay before next attempt."""
        # Custom delay function
        if policy.strategy == RetryStrategy.CUSTOM and policy.delay_function:
            delay = policy.delay_function(attempt)
        else:
            calculator = DELAY_CALCULATORS.get(
                policy.strategy,
                exponential_delay
            )
            delay = calculator(attempt, policy)

        # Add jitter
        if policy.jitter and delay > 0:
            jitter_range = delay * policy.jitter_factor
            delay += random.uniform(-jitter_range, jitter_range)
            delay = max(0, delay)  # Ensure non-negative

        return min(delay, policy.max_delay)

    # ========================================================================
    # EXCEPTION HANDLING
    # ========================================================================

    def is_retryable(self, exception: Exception, policy: RetryPolicy) -> bool:
        """Check if exception should trigger retry."""
        # Check non-retryable first
        for exc_type in policy.non_retryable_exceptions:
            if isinstance(exception, exc_type):
                return False

        # Check retryable
        for exc_type in policy.retryable_exceptions:
            if isinstance(exception, exc_type):
                return True

        return False

    # ========================================================================
    # SYNC RETRY
    # ========================================================================

    def execute(
        self,
        func: Callable,
        *args,
        policy: Optional[RetryPolicy] = None,
        **kwargs
    ) -> RetryResult:
        """
        Execute function with retry.

        Args:
            func: Function to execute
            *args: Function arguments
            policy: Retry policy
            **kwargs: Function keyword arguments

        Returns:
            RetryResult
        """
        policy = policy or RetryPolicy(
            max_attempts=self.config.default_max_attempts,
            strategy=self.config.default_strategy,
            base_delay=self.config.default_base_delay
        )

        attempts: List[RetryAttempt] = []
        start_time = time.time()

        for attempt_num in range(1, policy.max_attempts + 1):
            attempt = RetryAttempt(
                number=attempt_num,
                started_at=datetime.now()
            )

            try:
                # Execute function
                result = func(*args, **kwargs)

                # Success
                attempt.ended_at = datetime.now()
                attempt.success = True
                attempt.result = result
                attempt.duration_ms = (time.time() - start_time) * 1000
                attempts.append(attempt)

                # Update metrics
                with self._lock:
                    self._total_retries += attempt_num - 1
                    self._successful_retries += 1

                # Success callback
                final_result = RetryResult(
                    success=True,
                    result=result,
                    attempts=attempts,
                    total_attempts=attempt_num,
                    total_duration_ms=(time.time() - start_time) * 1000
                )

                if policy.on_success:
                    policy.on_success(final_result)

                return final_result

            except Exception as e:
                attempt.ended_at = datetime.now()
                attempt.success = False
                attempt.error = e
                attempt.duration_ms = (time.time() - start_time) * 1000
                attempts.append(attempt)

                # Check if should retry
                if not self.is_retryable(e, policy):
                    logger.debug(f"Non-retryable exception: {type(e).__name__}")
                    break

                if attempt_num >= policy.max_attempts:
                    logger.debug(f"Max attempts ({policy.max_attempts}) reached")
                    break

                # Calculate delay
                delay = self.calculate_delay(attempt_num, policy)
                attempt.delay_before = delay

                # Retry callback
                if policy.on_retry:
                    policy.on_retry(attempt)

                logger.debug(
                    f"Retry attempt {attempt_num}/{policy.max_attempts}, "
                    f"waiting {delay:.2f}s"
                )

                # Wait before retry
                time.sleep(delay)

        # All attempts failed
        with self._lock:
            self._total_retries += policy.max_attempts - 1
            self._failed_retries += 1

        last_error = attempts[-1].error if attempts else None

        final_result = RetryResult(
            success=False,
            error=last_error,
            attempts=attempts,
            total_attempts=len(attempts),
            total_duration_ms=(time.time() - start_time) * 1000
        )

        if policy.on_failure:
            policy.on_failure(final_result)

        return final_result

    # ========================================================================
    # ASYNC RETRY
    # ========================================================================

    async def execute_async(
        self,
        func: Callable,
        *args,
        policy: Optional[RetryPolicy] = None,
        **kwargs
    ) -> RetryResult:
        """
        Execute async function with retry.

        Args:
            func: Async function to execute
            *args: Function arguments
            policy: Retry policy
            **kwargs: Function keyword arguments

        Returns:
            RetryResult
        """
        policy = policy or RetryPolicy(
            max_attempts=self.config.default_max_attempts,
            strategy=self.config.default_strategy,
            base_delay=self.config.default_base_delay
        )

        attempts: List[RetryAttempt] = []
        start_time = time.time()

        for attempt_num in range(1, policy.max_attempts + 1):
            attempt = RetryAttempt(
                number=attempt_num,
                started_at=datetime.now()
            )

            try:
                # Execute async function
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None,
                        lambda: func(*args, **kwargs)
                    )

                # Success
                attempt.ended_at = datetime.now()
                attempt.success = True
                attempt.result = result
                attempts.append(attempt)

                with self._lock:
                    self._total_retries += attempt_num - 1
                    self._successful_retries += 1

                final_result = RetryResult(
                    success=True,
                    result=result,
                    attempts=attempts,
                    total_attempts=attempt_num,
                    total_duration_ms=(time.time() - start_time) * 1000
                )

                if policy.on_success:
                    policy.on_success(final_result)

                return final_result

            except Exception as e:
                attempt.ended_at = datetime.now()
                attempt.success = False
                attempt.error = e
                attempts.append(attempt)

                if not self.is_retryable(e, policy):
                    break

                if attempt_num >= policy.max_attempts:
                    break

                delay = self.calculate_delay(attempt_num, policy)
                attempt.delay_before = delay

                if policy.on_retry:
                    policy.on_retry(attempt)

                await asyncio.sleep(delay)

        with self._lock:
            self._total_retries += len(attempts) - 1
            self._failed_retries += 1

        last_error = attempts[-1].error if attempts else None

        final_result = RetryResult(
            success=False,
            error=last_error,
            attempts=attempts,
            total_attempts=len(attempts),
            total_duration_ms=(time.time() - start_time) * 1000
        )

        if policy.on_failure:
            policy.on_failure(final_result)

        return final_result

    # ========================================================================
    # STATUS
    # ========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        with self._lock:
            return {
                'total_retries': self._total_retries,
                'successful_retries': self._successful_retries,
                'failed_retries': self._failed_retries,
                'default_strategy': self.config.default_strategy.value
            }

    def reset_metrics(self) -> None:
        """Reset metrics."""
        with self._lock:
            self._total_retries = 0
            self._successful_retries = 0
            self._failed_retries = 0


# ============================================================================
# DECORATOR
# ============================================================================

def with_retry(
    max_attempts: int = 3,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_exceptions: Optional[List[Type[Exception]]] = None,
    on_retry: Optional[Callable] = None
):
    """
    Decorator for retry with policy.

    Usage:
        @with_retry(max_attempts=5, strategy=RetryStrategy.EXPONENTIAL)
        def my_function():
            ...
    """
    def decorator(func: Callable) -> Callable:
        policy = RetryPolicy(
            max_attempts=max_attempts,
            strategy=strategy,
            base_delay=base_delay,
            max_delay=max_delay,
            retryable_exceptions=retryable_exceptions or [Exception],
            on_retry=on_retry
        )

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            result = retry_engine.execute(func, *args, policy=policy, **kwargs)
            if result.success:
                return result.result
            raise result.error or Exception("Retry failed")

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await retry_engine.execute_async(func, *args, policy=policy, **kwargs)
            if result.success:
                return result.result
            raise result.error or Exception("Retry failed")

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# ============================================================================
# CONVENIENCE
# ============================================================================

retry_engine = RetryEngine()


def retry(
    func: Callable,
    *args,
    max_attempts: int = 3,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    **kwargs
) -> Any:
    """Execute function with default retry policy."""
    policy = RetryPolicy(
        max_attempts=max_attempts,
        strategy=strategy
    )
    result = retry_engine.execute(func, *args, policy=policy, **kwargs)
    if result.success:
        return result.result
    raise result.error or Exception("Retry failed")
