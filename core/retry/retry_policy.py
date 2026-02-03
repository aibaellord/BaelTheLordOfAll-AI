#!/usr/bin/env python3
"""
BAEL - Retry Policy System
Comprehensive retry mechanism with multiple strategies.

This module provides a complete retry framework
for handling transient failures.

Features:
- Multiple retry strategies (exponential, linear, fibonacci)
- Configurable backoff algorithms
- Jitter support for thundering herd prevention
- Circuit breaker integration
- Retry predicates
- Deadline support
- Retry statistics
- Async operation support
- Context propagation
- Retry budgets
"""

import asyncio
import functools
import logging
import random
import time
import traceback
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import (Any, Callable, Coroutine, Dict, Generic, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')


# =============================================================================
# ENUMS
# =============================================================================

class RetryStrategy(Enum):
    """Retry backoff strategies."""
    IMMEDIATE = "immediate"
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIBONACCI = "fibonacci"
    DECORRELATED_JITTER = "decorrelated_jitter"
    CUSTOM = "custom"


class RetryOutcome(Enum):
    """Outcome of a retry attempt."""
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    EXHAUSTED = "exhausted"
    CANCELLED = "cancelled"


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class JitterType(Enum):
    """Jitter algorithms."""
    NONE = "none"
    FULL = "full"
    EQUAL = "equal"
    DECORRELATED = "decorrelated"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class RetryConfig:
    """Retry configuration."""
    max_retries: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL

    # Delays
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0
    multiplier: float = 2.0

    # Jitter
    jitter: JitterType = JitterType.EQUAL
    jitter_factor: float = 0.5

    # Timeout
    timeout: Optional[float] = None  # Per-attempt timeout
    deadline: Optional[float] = None  # Total deadline

    # Retryable
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    fatal_exceptions: Tuple[Type[Exception], ...] = ()

    # Custom predicate
    should_retry: Optional[Callable[[Exception], bool]] = None


@dataclass
class RetryAttempt:
    """Information about a retry attempt."""
    attempt: int
    exception: Optional[Exception] = None
    result: Any = None
    delay: float = 0.0
    duration: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def succeeded(self) -> bool:
        return self.exception is None


@dataclass
class RetryResult(Generic[T]):
    """Result of a retried operation."""
    outcome: RetryOutcome
    value: Optional[T] = None
    attempts: List[RetryAttempt] = field(default_factory=list)
    total_duration: float = 0.0

    @property
    def succeeded(self) -> bool:
        return self.outcome == RetryOutcome.SUCCESS

    @property
    def final_exception(self) -> Optional[Exception]:
        if self.attempts:
            return self.attempts[-1].exception
        return None

    @property
    def attempt_count(self) -> int:
        return len(self.attempts)


@dataclass
class RetryStats:
    """Statistics for retry operations."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_retries: int = 0
    total_duration: float = 0.0

    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.successful_calls / self.total_calls

    @property
    def avg_retries(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.total_retries / self.total_calls


# =============================================================================
# BACKOFF STRATEGIES
# =============================================================================

class BackoffStrategy(ABC):
    """Abstract backoff strategy."""

    @abstractmethod
    def get_delay(self, attempt: int, config: RetryConfig) -> float:
        """Get delay for attempt number."""
        pass


class ImmediateBackoff(BackoffStrategy):
    """No delay between retries."""

    def get_delay(self, attempt: int, config: RetryConfig) -> float:
        return 0.0


class FixedBackoff(BackoffStrategy):
    """Fixed delay between retries."""

    def get_delay(self, attempt: int, config: RetryConfig) -> float:
        return config.initial_delay


class LinearBackoff(BackoffStrategy):
    """Linear increasing delay."""

    def get_delay(self, attempt: int, config: RetryConfig) -> float:
        delay = config.initial_delay * attempt
        return min(delay, config.max_delay)


class ExponentialBackoff(BackoffStrategy):
    """Exponential increasing delay."""

    def get_delay(self, attempt: int, config: RetryConfig) -> float:
        delay = config.initial_delay * (config.multiplier ** (attempt - 1))
        return min(delay, config.max_delay)


class FibonacciBackoff(BackoffStrategy):
    """Fibonacci sequence delay."""

    def __init__(self):
        self._cache: Dict[int, int] = {0: 0, 1: 1}

    def _fib(self, n: int) -> int:
        if n in self._cache:
            return self._cache[n]
        self._cache[n] = self._fib(n - 1) + self._fib(n - 2)
        return self._cache[n]

    def get_delay(self, attempt: int, config: RetryConfig) -> float:
        delay = config.initial_delay * self._fib(attempt + 1)
        return min(delay, config.max_delay)


class DecorrelatedJitterBackoff(BackoffStrategy):
    """Decorrelated jitter backoff (AWS style)."""

    def __init__(self):
        self._last_delay = 0.0

    def get_delay(self, attempt: int, config: RetryConfig) -> float:
        if attempt == 1:
            self._last_delay = config.initial_delay
        else:
            self._last_delay = random.uniform(
                config.initial_delay,
                self._last_delay * 3
            )
        return min(self._last_delay, config.max_delay)


# =============================================================================
# JITTER
# =============================================================================

class JitterCalculator:
    """Jitter calculation utilities."""

    @staticmethod
    def apply_jitter(
        delay: float,
        jitter_type: JitterType,
        factor: float = 0.5
    ) -> float:
        """Apply jitter to delay."""
        if jitter_type == JitterType.NONE:
            return delay

        elif jitter_type == JitterType.FULL:
            return random.uniform(0, delay)

        elif jitter_type == JitterType.EQUAL:
            half = delay / 2
            return half + random.uniform(0, half)

        elif jitter_type == JitterType.DECORRELATED:
            return random.uniform(delay * (1 - factor), delay * (1 + factor))

        return delay


# =============================================================================
# CIRCUIT BREAKER
# =============================================================================

@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5
    success_threshold: int = 2
    timeout: float = 60.0  # seconds
    half_open_max_calls: int = 3


class CircuitBreaker:
    """
    Circuit breaker for preventing cascading failures.

    States:
    - CLOSED: Normal operation, failures tracked
    - OPEN: Requests fail immediately
    - HALF_OPEN: Limited test requests allowed
    """

    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._last_failure_time: Optional[float] = None

    @property
    def state(self) -> CircuitState:
        self._check_timeout()
        return self._state

    @property
    def is_closed(self) -> bool:
        return self.state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN

    def _check_timeout(self) -> None:
        """Check if open state should transition to half-open."""
        if self._state == CircuitState.OPEN:
            if self._last_failure_time:
                elapsed = time.time() - self._last_failure_time
                if elapsed >= self.config.timeout:
                    self._transition_to_half_open()

    def _transition_to_half_open(self) -> None:
        """Transition to half-open state."""
        self._state = CircuitState.HALF_OPEN
        self._half_open_calls = 0
        self._success_count = 0

    def can_execute(self) -> bool:
        """Check if request can be executed."""
        state = self.state

        if state == CircuitState.CLOSED:
            return True

        if state == CircuitState.OPEN:
            return False

        # Half-open
        return self._half_open_calls < self.config.half_open_max_calls

    def record_success(self) -> None:
        """Record successful execution."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            self._half_open_calls += 1

            if self._success_count >= self.config.success_threshold:
                self._state = CircuitState.CLOSED
                self._failure_count = 0

        elif self._state == CircuitState.CLOSED:
            self._failure_count = 0

    def record_failure(self) -> None:
        """Record failed execution."""
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            self._failure_count = self.config.failure_threshold

        elif self._state == CircuitState.CLOSED:
            self._failure_count += 1

            if self._failure_count >= self.config.failure_threshold:
                self._state = CircuitState.OPEN

    def reset(self) -> None:
        """Reset circuit breaker."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open."""

    def __init__(self, circuit_name: str):
        self.circuit_name = circuit_name
        super().__init__(f"Circuit breaker '{circuit_name}' is open")


# =============================================================================
# RETRY BUDGET
# =============================================================================

class RetryBudget:
    """
    Retry budget to limit retry rate.

    Prevents retry storms by limiting the percentage
    of requests that can be retries.
    """

    def __init__(
        self,
        token_ratio: float = 0.2,  # Max 20% retries
        min_retries: int = 10,
        ttl: float = 10.0  # Token TTL in seconds
    ):
        self.token_ratio = token_ratio
        self.min_retries = min_retries
        self.ttl = ttl

        self._requests: deque = deque()
        self._retries: deque = deque()

    def _cleanup(self) -> None:
        """Remove expired entries."""
        now = time.time()
        cutoff = now - self.ttl

        while self._requests and self._requests[0] < cutoff:
            self._requests.popleft()

        while self._retries and self._retries[0] < cutoff:
            self._retries.popleft()

    def record_request(self) -> None:
        """Record a request."""
        self._cleanup()
        self._requests.append(time.time())

    def can_retry(self) -> bool:
        """Check if retry is allowed."""
        self._cleanup()

        request_count = len(self._requests)
        retry_count = len(self._retries)

        # Always allow minimum retries
        if retry_count < self.min_retries:
            return True

        # Check ratio
        if request_count == 0:
            return True

        current_ratio = retry_count / request_count
        return current_ratio < self.token_ratio

    def record_retry(self) -> bool:
        """Record a retry attempt. Returns True if allowed."""
        if not self.can_retry():
            return False

        self._retries.append(time.time())
        return True


# =============================================================================
# RETRY EXECUTOR
# =============================================================================

class RetryExecutor:
    """
    Executes operations with retry logic.
    """

    def __init__(self, config: RetryConfig = None):
        self.config = config or RetryConfig()

        # Backoff strategies
        self._strategies: Dict[RetryStrategy, BackoffStrategy] = {
            RetryStrategy.IMMEDIATE: ImmediateBackoff(),
            RetryStrategy.FIXED: FixedBackoff(),
            RetryStrategy.LINEAR: LinearBackoff(),
            RetryStrategy.EXPONENTIAL: ExponentialBackoff(),
            RetryStrategy.FIBONACCI: FibonacciBackoff(),
            RetryStrategy.DECORRELATED_JITTER: DecorrelatedJitterBackoff(),
        }

        # Statistics
        self.stats = RetryStats()

        # Optional circuit breaker
        self.circuit_breaker: Optional[CircuitBreaker] = None

        # Optional retry budget
        self.retry_budget: Optional[RetryBudget] = None

    def with_circuit_breaker(
        self,
        name: str,
        config: CircuitBreakerConfig = None
    ) -> 'RetryExecutor':
        """Add circuit breaker."""
        self.circuit_breaker = CircuitBreaker(name, config)
        return self

    def with_retry_budget(
        self,
        token_ratio: float = 0.2,
        min_retries: int = 10
    ) -> 'RetryExecutor':
        """Add retry budget."""
        self.retry_budget = RetryBudget(token_ratio, min_retries)
        return self

    def _get_delay(self, attempt: int) -> float:
        """Get delay for attempt."""
        strategy = self._strategies.get(
            self.config.strategy,
            self._strategies[RetryStrategy.EXPONENTIAL]
        )

        delay = strategy.get_delay(attempt, self.config)

        # Apply jitter
        delay = JitterCalculator.apply_jitter(
            delay,
            self.config.jitter,
            self.config.jitter_factor
        )

        return delay

    def _should_retry(self, exception: Exception) -> bool:
        """Check if exception is retryable."""
        # Check fatal exceptions
        if isinstance(exception, self.config.fatal_exceptions):
            return False

        # Check custom predicate
        if self.config.should_retry:
            return self.config.should_retry(exception)

        # Check retryable exceptions
        return isinstance(exception, self.config.retryable_exceptions)

    async def execute(
        self,
        func: Callable[[], Coroutine[Any, Any, T]]
    ) -> RetryResult[T]:
        """Execute function with retries."""
        attempts: List[RetryAttempt] = []
        start_time = time.time()
        deadline_time = None

        if self.config.deadline:
            deadline_time = start_time + self.config.deadline

        # Record request for budget
        if self.retry_budget:
            self.retry_budget.record_request()

        for attempt in range(1, self.config.max_retries + 2):
            attempt_start = time.time()

            # Check circuit breaker
            if self.circuit_breaker and not self.circuit_breaker.can_execute():
                self.stats.failed_calls += 1
                return RetryResult(
                    outcome=RetryOutcome.FAILURE,
                    attempts=attempts,
                    total_duration=time.time() - start_time
                )

            # Check deadline
            if deadline_time and time.time() >= deadline_time:
                self.stats.failed_calls += 1
                return RetryResult(
                    outcome=RetryOutcome.TIMEOUT,
                    attempts=attempts,
                    total_duration=time.time() - start_time
                )

            try:
                # Execute with optional timeout
                if self.config.timeout:
                    result = await asyncio.wait_for(
                        func(),
                        timeout=self.config.timeout
                    )
                else:
                    result = await func()

                # Success
                attempt_record = RetryAttempt(
                    attempt=attempt,
                    result=result,
                    duration=time.time() - attempt_start
                )
                attempts.append(attempt_record)

                if self.circuit_breaker:
                    self.circuit_breaker.record_success()

                self.stats.successful_calls += 1
                self.stats.total_calls += 1
                self.stats.total_retries += attempt - 1
                self.stats.total_duration += time.time() - start_time

                return RetryResult(
                    outcome=RetryOutcome.SUCCESS,
                    value=result,
                    attempts=attempts,
                    total_duration=time.time() - start_time
                )

            except asyncio.TimeoutError as e:
                attempt_record = RetryAttempt(
                    attempt=attempt,
                    exception=e,
                    duration=time.time() - attempt_start
                )
                attempts.append(attempt_record)

                if self.circuit_breaker:
                    self.circuit_breaker.record_failure()

            except Exception as e:
                attempt_record = RetryAttempt(
                    attempt=attempt,
                    exception=e,
                    duration=time.time() - attempt_start
                )
                attempts.append(attempt_record)

                if self.circuit_breaker:
                    self.circuit_breaker.record_failure()

                if not self._should_retry(e):
                    self.stats.failed_calls += 1
                    self.stats.total_calls += 1
                    return RetryResult(
                        outcome=RetryOutcome.FAILURE,
                        attempts=attempts,
                        total_duration=time.time() - start_time
                    )

            # Check if we should retry
            if attempt > self.config.max_retries:
                break

            # Check retry budget
            if self.retry_budget and not self.retry_budget.record_retry():
                break

            # Calculate and wait delay
            delay = self._get_delay(attempt)

            # Check if delay would exceed deadline
            if deadline_time:
                remaining = deadline_time - time.time()
                if delay >= remaining:
                    break

            attempt_record.delay = delay
            await asyncio.sleep(delay)

        self.stats.failed_calls += 1
        self.stats.total_calls += 1
        self.stats.total_retries += len(attempts) - 1
        self.stats.total_duration += time.time() - start_time

        return RetryResult(
            outcome=RetryOutcome.EXHAUSTED,
            attempts=attempts,
            total_duration=time.time() - start_time
        )

    def execute_sync(
        self,
        func: Callable[[], T]
    ) -> RetryResult[T]:
        """Execute synchronous function with retries."""
        attempts: List[RetryAttempt] = []
        start_time = time.time()
        deadline_time = None

        if self.config.deadline:
            deadline_time = start_time + self.config.deadline

        for attempt in range(1, self.config.max_retries + 2):
            attempt_start = time.time()

            # Check circuit breaker
            if self.circuit_breaker and not self.circuit_breaker.can_execute():
                return RetryResult(
                    outcome=RetryOutcome.FAILURE,
                    attempts=attempts,
                    total_duration=time.time() - start_time
                )

            # Check deadline
            if deadline_time and time.time() >= deadline_time:
                return RetryResult(
                    outcome=RetryOutcome.TIMEOUT,
                    attempts=attempts,
                    total_duration=time.time() - start_time
                )

            try:
                result = func()

                attempt_record = RetryAttempt(
                    attempt=attempt,
                    result=result,
                    duration=time.time() - attempt_start
                )
                attempts.append(attempt_record)

                if self.circuit_breaker:
                    self.circuit_breaker.record_success()

                return RetryResult(
                    outcome=RetryOutcome.SUCCESS,
                    value=result,
                    attempts=attempts,
                    total_duration=time.time() - start_time
                )

            except Exception as e:
                attempt_record = RetryAttempt(
                    attempt=attempt,
                    exception=e,
                    duration=time.time() - attempt_start
                )
                attempts.append(attempt_record)

                if self.circuit_breaker:
                    self.circuit_breaker.record_failure()

                if not self._should_retry(e):
                    return RetryResult(
                        outcome=RetryOutcome.FAILURE,
                        attempts=attempts,
                        total_duration=time.time() - start_time
                    )

            if attempt > self.config.max_retries:
                break

            delay = self._get_delay(attempt)

            if deadline_time:
                remaining = deadline_time - time.time()
                if delay >= remaining:
                    break

            attempt_record.delay = delay
            time.sleep(delay)

        return RetryResult(
            outcome=RetryOutcome.EXHAUSTED,
            attempts=attempts,
            total_duration=time.time() - start_time
        )


# =============================================================================
# DECORATORS
# =============================================================================

def retry(
    max_retries: int = 3,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    timeout: Optional[float] = None
) -> Callable:
    """
    Retry decorator for functions.

    Usage:
        @retry(max_retries=3, strategy=RetryStrategy.EXPONENTIAL)
        async def fetch_data():
            ...
    """
    config = RetryConfig(
        max_retries=max_retries,
        strategy=strategy,
        initial_delay=initial_delay,
        max_delay=max_delay,
        retryable_exceptions=retryable_exceptions,
        timeout=timeout
    )
    executor = RetryExecutor(config)

    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                async def execute():
                    return await func(*args, **kwargs)
                result = await executor.execute(execute)
                if result.succeeded:
                    return result.value
                raise result.final_exception or RuntimeError("Retry exhausted")
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                def execute():
                    return func(*args, **kwargs)
                result = executor.execute_sync(execute)
                if result.succeeded:
                    return result.value
                raise result.final_exception or RuntimeError("Retry exhausted")
            return sync_wrapper

    return decorator


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    timeout: float = 60.0
) -> Callable:
    """
    Circuit breaker decorator.

    Usage:
        @circuit_breaker("external_api", failure_threshold=5)
        async def call_api():
            ...
    """
    cb = CircuitBreaker(
        name,
        CircuitBreakerConfig(failure_threshold=failure_threshold, timeout=timeout)
    )

    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                if not cb.can_execute():
                    raise CircuitOpenError(name)
                try:
                    result = await func(*args, **kwargs)
                    cb.record_success()
                    return result
                except Exception as e:
                    cb.record_failure()
                    raise
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                if not cb.can_execute():
                    raise CircuitOpenError(name)
                try:
                    result = func(*args, **kwargs)
                    cb.record_success()
                    return result
                except Exception as e:
                    cb.record_failure()
                    raise
            return sync_wrapper

    return decorator


# =============================================================================
# RETRY MANAGER
# =============================================================================

class RetryManager:
    """
    Master retry policy manager for BAEL.

    Provides centralized retry configuration and execution.
    """

    def __init__(self):
        self.executors: Dict[str, RetryExecutor] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.default_config = RetryConfig()

    # Configuration
    def create_executor(
        self,
        name: str,
        config: RetryConfig = None
    ) -> RetryExecutor:
        """Create a named retry executor."""
        executor = RetryExecutor(config or self.default_config)
        self.executors[name] = executor
        return executor

    def get_executor(self, name: str) -> Optional[RetryExecutor]:
        """Get executor by name."""
        return self.executors.get(name)

    def create_circuit_breaker(
        self,
        name: str,
        config: CircuitBreakerConfig = None
    ) -> CircuitBreaker:
        """Create a circuit breaker."""
        cb = CircuitBreaker(name, config)
        self.circuit_breakers[name] = cb
        return cb

    def get_circuit_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        return self.circuit_breakers.get(name)

    # Execution
    async def execute(
        self,
        name: str,
        func: Callable[[], Coroutine[Any, Any, T]]
    ) -> RetryResult[T]:
        """Execute with named executor."""
        executor = self.get_executor(name)
        if not executor:
            executor = self.create_executor(name)
        return await executor.execute(func)

    async def execute_with_config(
        self,
        func: Callable[[], Coroutine[Any, Any, T]],
        config: RetryConfig
    ) -> RetryResult[T]:
        """Execute with custom config."""
        executor = RetryExecutor(config)
        return await executor.execute(func)

    # Statistics
    def get_stats(self) -> Dict[str, RetryStats]:
        """Get statistics for all executors."""
        return {
            name: executor.stats
            for name, executor in self.executors.items()
        }

    def get_circuit_breaker_states(self) -> Dict[str, CircuitState]:
        """Get all circuit breaker states."""
        return {
            name: cb.state
            for name, cb in self.circuit_breakers.items()
        }

    def reset_all_circuit_breakers(self) -> None:
        """Reset all circuit breakers."""
        for cb in self.circuit_breakers.values():
            cb.reset()


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Retry Policy System."""
    print("=" * 70)
    print("BAEL - RETRY POLICY SYSTEM DEMO")
    print("Comprehensive Retry Mechanisms")
    print("=" * 70)
    print()

    manager = RetryManager()

    # 1. Basic Retry
    print("1. BASIC RETRY:")
    print("-" * 40)

    attempt_count = 0

    async def flaky_operation():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise ConnectionError(f"Attempt {attempt_count} failed")
        return "Success!"

    config = RetryConfig(
        max_retries=5,
        strategy=RetryStrategy.EXPONENTIAL,
        initial_delay=0.1,
        max_delay=2.0
    )

    executor = RetryExecutor(config)
    result = await executor.execute(flaky_operation)

    print(f"   Outcome: {result.outcome.value}")
    print(f"   Attempts: {result.attempt_count}")
    print(f"   Total duration: {result.total_duration:.3f}s")
    print(f"   Value: {result.value}")
    print()

    # 2. Different Strategies
    print("2. BACKOFF STRATEGIES:")
    print("-" * 40)

    strategies = [
        (RetryStrategy.FIXED, "Fixed"),
        (RetryStrategy.LINEAR, "Linear"),
        (RetryStrategy.EXPONENTIAL, "Exponential"),
        (RetryStrategy.FIBONACCI, "Fibonacci"),
    ]

    for strategy, name in strategies:
        config = RetryConfig(
            strategy=strategy,
            initial_delay=0.5,
            max_delay=10.0
        )
        executor = RetryExecutor(config)

        delays = []
        for i in range(1, 6):
            delay = executor._get_delay(i)
            delays.append(f"{delay:.2f}")

        print(f"   {name}: {' → '.join(delays)}s")
    print()

    # 3. Circuit Breaker
    print("3. CIRCUIT BREAKER:")
    print("-" * 40)

    cb = CircuitBreaker(
        "api",
        CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout=5.0
        )
    )

    print(f"   Initial state: {cb.state.value}")

    # Simulate failures
    for i in range(4):
        cb.record_failure()
        print(f"   After failure {i+1}: {cb.state.value}")

    print(f"   Can execute: {cb.can_execute()}")
    print()

    # 4. Retry with Circuit Breaker
    print("4. RETRY + CIRCUIT BREAKER:")
    print("-" * 40)

    executor = RetryExecutor(RetryConfig(max_retries=2, initial_delay=0.1))
    executor.with_circuit_breaker("service", CircuitBreakerConfig(failure_threshold=2))

    fail_count = 0

    async def failing_service():
        nonlocal fail_count
        fail_count += 1
        raise RuntimeError(f"Service error {fail_count}")

    # First call - will fail and open circuit
    result1 = await executor.execute(failing_service)
    print(f"   Result 1: {result1.outcome.value}")
    print(f"   Circuit state: {executor.circuit_breaker.state.value}")
    print()

    # 5. Retry Budget
    print("5. RETRY BUDGET:")
    print("-" * 40)

    budget = RetryBudget(token_ratio=0.3, min_retries=2)

    # Simulate requests
    for i in range(5):
        budget.record_request()

    print(f"   Requests: 5")

    retries = 0
    for i in range(10):
        if budget.record_retry():
            retries += 1

    print(f"   Allowed retries: {retries}")
    print(f"   (Budget limited to 30% of requests)")
    print()

    # 6. Retry Decorator
    print("6. RETRY DECORATOR:")
    print("-" * 40)

    call_count = 0

    @retry(max_retries=3, initial_delay=0.05)
    async def decorated_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("Not ready")
        return f"Called {call_count} times"

    result = await decorated_function()
    print(f"   Result: {result}")
    print()

    # 7. Custom Retry Predicate
    print("7. CUSTOM RETRY PREDICATE:")
    print("-" * 40)

    def should_retry(e: Exception) -> bool:
        # Only retry on specific errors
        return "temporary" in str(e).lower()

    config = RetryConfig(
        max_retries=5,
        initial_delay=0.1,
        should_retry=should_retry
    )

    executor = RetryExecutor(config)

    temp_error_count = 0

    async def conditional_operation():
        nonlocal temp_error_count
        temp_error_count += 1
        if temp_error_count < 3:
            raise RuntimeError("Temporary failure")
        return "Done"

    result = await executor.execute(conditional_operation)
    print(f"   Outcome: {result.outcome.value}")
    print(f"   Attempts: {result.attempt_count}")
    print()

    # 8. Timeout and Deadline
    print("8. TIMEOUT AND DEADLINE:")
    print("-" * 40)

    config = RetryConfig(
        max_retries=10,
        timeout=0.5,
        deadline=2.0,
        initial_delay=0.3
    )

    executor = RetryExecutor(config)

    async def slow_operation():
        await asyncio.sleep(2)  # Exceeds timeout
        return "Done"

    start = time.time()
    result = await executor.execute(slow_operation)
    elapsed = time.time() - start

    print(f"   Outcome: {result.outcome.value}")
    print(f"   Elapsed: {elapsed:.2f}s (deadline was 2s)")
    print(f"   Attempts before deadline: {result.attempt_count}")
    print()

    # 9. Manager Statistics
    print("9. RETRY MANAGER:")
    print("-" * 40)

    manager.create_executor("database", RetryConfig(max_retries=3))
    manager.create_executor("api", RetryConfig(max_retries=5))
    manager.create_circuit_breaker("external_service")

    db_count = 0

    async def db_operation():
        nonlocal db_count
        db_count += 1
        if db_count < 2:
            raise ConnectionError("DB unavailable")
        return "Connected"

    await manager.execute("database", db_operation)

    stats = manager.get_stats()
    print(f"   Executors: {list(stats.keys())}")

    db_stats = stats.get("database")
    if db_stats:
        print(f"   Database stats:")
        print(f"      Total calls: {db_stats.total_calls}")
        print(f"      Success rate: {db_stats.success_rate:.0%}")
    print()

    # 10. Jitter Demonstration
    print("10. JITTER ALGORITHMS:")
    print("-" * 40)

    base_delay = 1.0

    for jitter_type in JitterType:
        delays = []
        for _ in range(5):
            delay = JitterCalculator.apply_jitter(base_delay, jitter_type, 0.5)
            delays.append(f"{delay:.2f}")
        print(f"   {jitter_type.value}: {', '.join(delays)}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Retry Policy System Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
