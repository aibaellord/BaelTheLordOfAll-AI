#!/usr/bin/env python3
"""
BAEL - Retry Manager
Comprehensive retry logic with multiple strategies.

Features:
- Multiple retry strategies
- Exponential backoff
- Jitter
- Circuit breaker integration
- Retry policies
- Deadline support
- Callback hooks
- Metrics collection
- Async support
- Decorators
"""

import asyncio
import functools
import logging
import random
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import (Any, Awaitable, Callable, Dict, Generic, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)


T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])


# =============================================================================
# ENUMS
# =============================================================================

class RetryStrategy(Enum):
    """Retry strategies."""
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIBONACCI = "fibonacci"
    DECORRELATED_JITTER = "decorrelated_jitter"
    EQUAL_JITTER = "equal_jitter"
    FULL_JITTER = "full_jitter"


class RetryResult(Enum):
    """Retry attempt result."""
    SUCCESS = "success"
    FAILURE = "failure"
    RETRYING = "retrying"
    EXHAUSTED = "exhausted"
    DEADLINE_EXCEEDED = "deadline_exceeded"


class BackoffMode(Enum):
    """Backoff mode."""
    STANDARD = "standard"
    CAPPED = "capped"
    RESET_ON_SUCCESS = "reset_on_success"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class RetryConfig:
    """Retry configuration."""
    max_retries: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    base_delay: float = 1.0
    max_delay: float = 60.0
    jitter_factor: float = 0.1
    backoff_multiplier: float = 2.0
    deadline: Optional[float] = None  # Total time limit
    retryable_exceptions: List[Type[Exception]] = field(default_factory=list)
    non_retryable_exceptions: List[Type[Exception]] = field(default_factory=list)
    retry_on: Optional[Callable[[Exception], bool]] = None
    on_retry: Optional[Callable[[int, Exception, float], None]] = None


@dataclass
class RetryAttempt:
    """Single retry attempt."""
    attempt: int
    timestamp: datetime
    duration: float
    success: bool
    error: Optional[Exception] = None
    delay_before: float = 0.0


@dataclass
class RetryStats:
    """Retry statistics."""
    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    total_retries: int = 0
    total_delay: float = 0.0
    average_attempts: float = 0.0
    last_error: Optional[str] = None


@dataclass
class RetryContext:
    """Context for retry execution."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    config: RetryConfig = field(default_factory=RetryConfig)
    attempts: List[RetryAttempt] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    result: RetryResult = RetryResult.RETRYING
    final_error: Optional[Exception] = None
    final_value: Any = None


# =============================================================================
# DELAY CALCULATORS
# =============================================================================

class DelayCalculator(ABC):
    """Abstract delay calculator."""

    @abstractmethod
    def calculate(self, attempt: int, config: RetryConfig) -> float:
        """Calculate delay for attempt."""
        pass


class FixedDelayCalculator(DelayCalculator):
    """Fixed delay calculator."""

    def calculate(self, attempt: int, config: RetryConfig) -> float:
        return min(config.base_delay, config.max_delay)


class LinearDelayCalculator(DelayCalculator):
    """Linear delay calculator."""

    def calculate(self, attempt: int, config: RetryConfig) -> float:
        delay = config.base_delay * (attempt + 1)
        return min(delay, config.max_delay)


class ExponentialDelayCalculator(DelayCalculator):
    """Exponential backoff delay calculator."""

    def calculate(self, attempt: int, config: RetryConfig) -> float:
        delay = config.base_delay * (config.backoff_multiplier ** attempt)
        return min(delay, config.max_delay)


class FibonacciDelayCalculator(DelayCalculator):
    """Fibonacci delay calculator."""

    def __init__(self):
        self._cache = {0: 1, 1: 1}

    def _fib(self, n: int) -> int:
        if n in self._cache:
            return self._cache[n]
        self._cache[n] = self._fib(n - 1) + self._fib(n - 2)
        return self._cache[n]

    def calculate(self, attempt: int, config: RetryConfig) -> float:
        delay = config.base_delay * self._fib(attempt)
        return min(delay, config.max_delay)


class DecorrelatedJitterCalculator(DelayCalculator):
    """Decorrelated jitter delay calculator."""

    def __init__(self):
        self._last_delay = None

    def calculate(self, attempt: int, config: RetryConfig) -> float:
        if self._last_delay is None:
            self._last_delay = config.base_delay

        delay = random.uniform(config.base_delay, self._last_delay * 3)
        delay = min(delay, config.max_delay)
        self._last_delay = delay
        return delay


class EqualJitterCalculator(DelayCalculator):
    """Equal jitter delay calculator."""

    def calculate(self, attempt: int, config: RetryConfig) -> float:
        base_delay = config.base_delay * (config.backoff_multiplier ** attempt)
        base_delay = min(base_delay, config.max_delay)

        half = base_delay / 2
        jitter = half * random.random()
        return half + jitter


class FullJitterCalculator(DelayCalculator):
    """Full jitter delay calculator."""

    def calculate(self, attempt: int, config: RetryConfig) -> float:
        base_delay = config.base_delay * (config.backoff_multiplier ** attempt)
        base_delay = min(base_delay, config.max_delay)
        return base_delay * random.random()


# =============================================================================
# RETRY POLICIES
# =============================================================================

class RetryPolicy(ABC):
    """Abstract retry policy."""

    @abstractmethod
    def should_retry(self, attempt: int, exception: Exception, context: RetryContext) -> bool:
        """Determine if should retry."""
        pass


class AlwaysRetryPolicy(RetryPolicy):
    """Always retry until max attempts."""

    def should_retry(self, attempt: int, exception: Exception, context: RetryContext) -> bool:
        return attempt < context.config.max_retries


class NeverRetryPolicy(RetryPolicy):
    """Never retry."""

    def should_retry(self, attempt: int, exception: Exception, context: RetryContext) -> bool:
        return False


class ExceptionTypeRetryPolicy(RetryPolicy):
    """Retry based on exception type."""

    def should_retry(self, attempt: int, exception: Exception, context: RetryContext) -> bool:
        if attempt >= context.config.max_retries:
            return False

        # Check non-retryable first
        for exc_type in context.config.non_retryable_exceptions:
            if isinstance(exception, exc_type):
                return False

        # Check retryable
        if context.config.retryable_exceptions:
            return any(isinstance(exception, exc_type)
                      for exc_type in context.config.retryable_exceptions)

        return True


class CallbackRetryPolicy(RetryPolicy):
    """Retry based on callback function."""

    def should_retry(self, attempt: int, exception: Exception, context: RetryContext) -> bool:
        if attempt >= context.config.max_retries:
            return False

        if context.config.retry_on:
            return context.config.retry_on(exception)

        return True


class CompositeRetryPolicy(RetryPolicy):
    """Composite of multiple policies (all must agree)."""

    def __init__(self, policies: List[RetryPolicy]):
        self.policies = policies

    def should_retry(self, attempt: int, exception: Exception, context: RetryContext) -> bool:
        return all(p.should_retry(attempt, exception, context) for p in self.policies)


# =============================================================================
# RETRY EXECUTOR
# =============================================================================

class RetryExecutor:
    """Execute operations with retry logic."""

    CALCULATORS: Dict[RetryStrategy, Type[DelayCalculator]] = {
        RetryStrategy.FIXED: FixedDelayCalculator,
        RetryStrategy.LINEAR: LinearDelayCalculator,
        RetryStrategy.EXPONENTIAL: ExponentialDelayCalculator,
        RetryStrategy.FIBONACCI: FibonacciDelayCalculator,
        RetryStrategy.DECORRELATED_JITTER: DecorrelatedJitterCalculator,
        RetryStrategy.EQUAL_JITTER: EqualJitterCalculator,
        RetryStrategy.FULL_JITTER: FullJitterCalculator,
    }

    def __init__(
        self,
        config: Optional[RetryConfig] = None,
        policy: Optional[RetryPolicy] = None
    ):
        self.config = config or RetryConfig()
        self.policy = policy or ExceptionTypeRetryPolicy()
        self._calculator = self.CALCULATORS.get(
            self.config.strategy, ExponentialDelayCalculator
        )()

    async def execute(
        self,
        func: Callable[..., Awaitable[T]],
        *args,
        **kwargs
    ) -> T:
        """Execute function with retry."""
        context = RetryContext(config=self.config)
        context.start_time = datetime.utcnow()

        deadline_time = None
        if self.config.deadline:
            deadline_time = time.time() + self.config.deadline

        attempt = 0
        last_exception = None

        while attempt <= self.config.max_retries:
            # Check deadline
            if deadline_time and time.time() > deadline_time:
                context.result = RetryResult.DEADLINE_EXCEEDED
                context.final_error = last_exception or TimeoutError("Deadline exceeded")
                raise context.final_error

            start_time = time.time()

            try:
                result = await func(*args, **kwargs)

                duration = time.time() - start_time
                context.attempts.append(RetryAttempt(
                    attempt=attempt,
                    timestamp=datetime.utcnow(),
                    duration=duration,
                    success=True
                ))

                context.end_time = datetime.utcnow()
                context.result = RetryResult.SUCCESS
                context.final_value = result

                return result

            except Exception as e:
                duration = time.time() - start_time
                last_exception = e

                context.attempts.append(RetryAttempt(
                    attempt=attempt,
                    timestamp=datetime.utcnow(),
                    duration=duration,
                    success=False,
                    error=e
                ))

                # Check if should retry
                if not self.policy.should_retry(attempt, e, context):
                    context.result = RetryResult.EXHAUSTED
                    context.final_error = e
                    raise

                # Calculate delay
                delay = self._calculator.calculate(attempt, self.config)

                # Add jitter if not already jittered
                if self.config.strategy not in (
                    RetryStrategy.DECORRELATED_JITTER,
                    RetryStrategy.EQUAL_JITTER,
                    RetryStrategy.FULL_JITTER
                ):
                    jitter = delay * self.config.jitter_factor * random.random()
                    delay += jitter

                # Callback
                if self.config.on_retry:
                    self.config.on_retry(attempt + 1, e, delay)

                logger.debug(f"Retry {attempt + 1}/{self.config.max_retries}, waiting {delay:.2f}s")

                # Check deadline again before sleeping
                if deadline_time:
                    remaining = deadline_time - time.time()
                    if remaining < delay:
                        delay = max(0, remaining)

                await asyncio.sleep(delay)
                attempt += 1

        context.result = RetryResult.EXHAUSTED
        context.final_error = last_exception
        context.end_time = datetime.utcnow()

        raise last_exception or Exception("Retry exhausted")

    def execute_sync(
        self,
        func: Callable[..., T],
        *args,
        **kwargs
    ) -> T:
        """Execute synchronous function with retry."""
        context = RetryContext(config=self.config)
        context.start_time = datetime.utcnow()

        deadline_time = None
        if self.config.deadline:
            deadline_time = time.time() + self.config.deadline

        attempt = 0
        last_exception = None

        while attempt <= self.config.max_retries:
            if deadline_time and time.time() > deadline_time:
                context.result = RetryResult.DEADLINE_EXCEEDED
                raise last_exception or TimeoutError("Deadline exceeded")

            start_time = time.time()

            try:
                result = func(*args, **kwargs)

                duration = time.time() - start_time
                context.attempts.append(RetryAttempt(
                    attempt=attempt,
                    timestamp=datetime.utcnow(),
                    duration=duration,
                    success=True
                ))

                context.end_time = datetime.utcnow()
                context.result = RetryResult.SUCCESS
                context.final_value = result

                return result

            except Exception as e:
                duration = time.time() - start_time
                last_exception = e

                context.attempts.append(RetryAttempt(
                    attempt=attempt,
                    timestamp=datetime.utcnow(),
                    duration=duration,
                    success=False,
                    error=e
                ))

                if not self.policy.should_retry(attempt, e, context):
                    raise

                delay = self._calculator.calculate(attempt, self.config)

                if self.config.strategy not in (
                    RetryStrategy.DECORRELATED_JITTER,
                    RetryStrategy.EQUAL_JITTER,
                    RetryStrategy.FULL_JITTER
                ):
                    jitter = delay * self.config.jitter_factor * random.random()
                    delay += jitter

                if self.config.on_retry:
                    self.config.on_retry(attempt + 1, e, delay)

                time.sleep(delay)
                attempt += 1

        raise last_exception or Exception("Retry exhausted")


# =============================================================================
# RETRY MANAGER
# =============================================================================

class RetryManager:
    """
    Comprehensive Retry Manager for BAEL.

    Provides centralized retry management with multiple strategies.
    """

    def __init__(self):
        self._configs: Dict[str, RetryConfig] = {}
        self._executors: Dict[str, RetryExecutor] = {}
        self._stats: Dict[str, RetryStats] = {}
        self._listeners: List[Callable[[str, RetryAttempt], None]] = []

    # -------------------------------------------------------------------------
    # CONFIGURATION
    # -------------------------------------------------------------------------

    def register_config(self, name: str, config: RetryConfig) -> None:
        """Register a retry configuration."""
        self._configs[name] = config
        self._executors[name] = RetryExecutor(config)
        self._stats[name] = RetryStats()

    def get_config(self, name: str) -> Optional[RetryConfig]:
        """Get configuration by name."""
        return self._configs.get(name)

    def remove_config(self, name: str) -> bool:
        """Remove configuration."""
        if name in self._configs:
            del self._configs[name]
            del self._executors[name]
            del self._stats[name]
            return True
        return False

    # -------------------------------------------------------------------------
    # EXECUTION
    # -------------------------------------------------------------------------

    async def execute(
        self,
        config_name: str,
        func: Callable[..., Awaitable[T]],
        *args,
        **kwargs
    ) -> T:
        """Execute with registered retry configuration."""
        executor = self._executors.get(config_name)
        if not executor:
            raise ValueError(f"Config not found: {config_name}")

        try:
            result = await executor.execute(func, *args, **kwargs)
            self._update_stats(config_name, True)
            return result
        except Exception as e:
            self._update_stats(config_name, False, str(e))
            raise

    async def execute_with_config(
        self,
        config: RetryConfig,
        func: Callable[..., Awaitable[T]],
        *args,
        **kwargs
    ) -> T:
        """Execute with inline retry configuration."""
        executor = RetryExecutor(config)
        return await executor.execute(func, *args, **kwargs)

    def _update_stats(self, name: str, success: bool, error: Optional[str] = None) -> None:
        """Update statistics."""
        stats = self._stats.get(name)
        if stats:
            stats.total_attempts += 1
            if success:
                stats.successful_attempts += 1
            else:
                stats.failed_attempts += 1
                stats.last_error = error

    # -------------------------------------------------------------------------
    # DECORATORS
    # -------------------------------------------------------------------------

    def retry(
        self,
        config_name: Optional[str] = None,
        config: Optional[RetryConfig] = None,
        **config_kwargs
    ):
        """Decorator for retry logic."""
        def decorator(func: F) -> F:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                executor = self._get_executor(config_name, config, config_kwargs)
                return await executor.execute(func, *args, **kwargs)

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                executor = self._get_executor(config_name, config, config_kwargs)
                return executor.execute_sync(func, *args, **kwargs)

            if asyncio.iscoroutinefunction(func):
                return async_wrapper  # type: ignore
            return sync_wrapper  # type: ignore

        return decorator

    def _get_executor(
        self,
        config_name: Optional[str],
        config: Optional[RetryConfig],
        config_kwargs: Dict
    ) -> RetryExecutor:
        """Get executor for decorator."""
        if config_name and config_name in self._executors:
            return self._executors[config_name]

        if config:
            return RetryExecutor(config)

        if config_kwargs:
            return RetryExecutor(RetryConfig(**config_kwargs))

        return RetryExecutor()

    # -------------------------------------------------------------------------
    # LISTENERS
    # -------------------------------------------------------------------------

    def add_listener(self, callback: Callable[[str, RetryAttempt], None]) -> None:
        """Add retry event listener."""
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable) -> None:
        """Remove listener."""
        if callback in self._listeners:
            self._listeners.remove(callback)

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self, name: str) -> Optional[RetryStats]:
        """Get statistics for configuration."""
        return self._stats.get(name)

    def get_all_stats(self) -> Dict[str, RetryStats]:
        """Get all statistics."""
        return dict(self._stats)

    def reset_stats(self, name: Optional[str] = None) -> None:
        """Reset statistics."""
        if name:
            if name in self._stats:
                self._stats[name] = RetryStats()
        else:
            for key in self._stats:
                self._stats[key] = RetryStats()

    # -------------------------------------------------------------------------
    # PRESETS
    # -------------------------------------------------------------------------

    def register_presets(self) -> None:
        """Register common retry presets."""
        # Quick retry for transient errors
        self.register_config("quick", RetryConfig(
            max_retries=3,
            strategy=RetryStrategy.EXPONENTIAL,
            base_delay=0.1,
            max_delay=1.0
        ))

        # Standard retry
        self.register_config("standard", RetryConfig(
            max_retries=5,
            strategy=RetryStrategy.EXPONENTIAL,
            base_delay=1.0,
            max_delay=30.0
        ))

        # Aggressive retry with jitter
        self.register_config("aggressive", RetryConfig(
            max_retries=10,
            strategy=RetryStrategy.FULL_JITTER,
            base_delay=0.5,
            max_delay=60.0
        ))

        # Conservative retry
        self.register_config("conservative", RetryConfig(
            max_retries=3,
            strategy=RetryStrategy.FIXED,
            base_delay=5.0,
            max_delay=5.0
        ))

        # Network retry
        self.register_config("network", RetryConfig(
            max_retries=5,
            strategy=RetryStrategy.DECORRELATED_JITTER,
            base_delay=1.0,
            max_delay=30.0,
            retryable_exceptions=[ConnectionError, TimeoutError]
        ))


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_default_manager = RetryManager()


def retry(
    max_retries: int = 3,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    **kwargs
):
    """Decorator for retry logic."""
    config = RetryConfig(
        max_retries=max_retries,
        strategy=strategy,
        base_delay=base_delay,
        max_delay=max_delay,
        **kwargs
    )
    return _default_manager.retry(config=config)


async def with_retry(
    func: Callable[..., Awaitable[T]],
    *args,
    max_retries: int = 3,
    **kwargs
) -> T:
    """Execute function with retry."""
    config = RetryConfig(max_retries=max_retries)
    executor = RetryExecutor(config)
    return await executor.execute(func, *args, **kwargs)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Retry Manager."""
    print("=" * 70)
    print("BAEL - RETRY MANAGER DEMO")
    print("Comprehensive Retry Logic")
    print("=" * 70)
    print()

    manager = RetryManager()
    manager.register_presets()

    # 1. Basic Retry
    print("1. BASIC RETRY:")
    print("-" * 40)

    attempts = []

    async def flaky_operation():
        attempts.append(time.time())
        if len(attempts) < 3:
            raise ConnectionError("Service unavailable")
        return "Success!"

    manager.register_config("test", RetryConfig(
        max_retries=5,
        strategy=RetryStrategy.EXPONENTIAL,
        base_delay=0.1
    ))

    result = await manager.execute("test", flaky_operation)
    print(f"   Result: {result}")
    print(f"   Attempts: {len(attempts)}")
    print()

    # 2. Delay Strategies
    print("2. DELAY STRATEGIES:")
    print("-" * 40)

    strategies = [
        RetryStrategy.FIXED,
        RetryStrategy.LINEAR,
        RetryStrategy.EXPONENTIAL,
        RetryStrategy.FIBONACCI
    ]

    for strategy in strategies:
        config = RetryConfig(
            strategy=strategy,
            base_delay=1.0,
            max_delay=30.0,
            backoff_multiplier=2.0
        )

        executor = RetryExecutor(config)
        delays = []

        for attempt in range(5):
            delay = executor._calculator.calculate(attempt, config)
            delays.append(f"{delay:.2f}")

        print(f"   {strategy.value:25}: {' -> '.join(delays)}")
    print()

    # 3. Jitter Strategies
    print("3. JITTER STRATEGIES:")
    print("-" * 40)

    jitter_strategies = [
        RetryStrategy.DECORRELATED_JITTER,
        RetryStrategy.EQUAL_JITTER,
        RetryStrategy.FULL_JITTER
    ]

    for strategy in jitter_strategies:
        config = RetryConfig(strategy=strategy, base_delay=1.0)
        executor = RetryExecutor(config)

        delays = []
        for attempt in range(4):
            delay = executor._calculator.calculate(attempt, config)
            delays.append(f"{delay:.2f}")

        print(f"   {strategy.value:25}: {' -> '.join(delays)}")
    print()

    # 4. Retry with Callback
    print("4. RETRY WITH CALLBACK:")
    print("-" * 40)

    retry_events = []

    def on_retry(attempt, error, delay):
        retry_events.append((attempt, str(error), delay))

    attempts.clear()

    config = RetryConfig(
        max_retries=3,
        base_delay=0.1,
        on_retry=on_retry
    )

    try:
        executor = RetryExecutor(config)
        await executor.execute(flaky_operation)
    except:
        pass

    for attempt, error, delay in retry_events:
        print(f"   Attempt {attempt}: {error[:30]}... (wait {delay:.3f}s)")
    print()

    # 5. Exception-Based Retry
    print("5. EXCEPTION-BASED RETRY:")
    print("-" * 40)

    config = RetryConfig(
        max_retries=3,
        base_delay=0.1,
        retryable_exceptions=[ConnectionError],
        non_retryable_exceptions=[ValueError]
    )

    policy = ExceptionTypeRetryPolicy()
    context = RetryContext(config=config)

    conn_error = ConnectionError("Network issue")
    val_error = ValueError("Invalid data")

    print(f"   ConnectionError retryable: {policy.should_retry(0, conn_error, context)}")
    print(f"   ValueError retryable: {policy.should_retry(0, val_error, context)}")
    print()

    # 6. Decorator Usage
    print("6. DECORATOR USAGE:")
    print("-" * 40)

    call_count = 0

    @retry(max_retries=3, base_delay=0.05)
    async def decorated_function():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise Exception("First call fails")
        return f"Success on attempt {call_count}"

    result = await decorated_function()
    print(f"   Result: {result}")
    print()

    # 7. Deadline
    print("7. DEADLINE (time limit):")
    print("-" * 40)

    config = RetryConfig(
        max_retries=100,
        base_delay=0.5,
        deadline=1.0  # 1 second total
    )

    slow_attempts = []

    async def slow_failing():
        slow_attempts.append(time.time())
        await asyncio.sleep(0.3)
        raise ConnectionError("Still failing")

    try:
        executor = RetryExecutor(config)
        await executor.execute(slow_failing)
    except Exception as e:
        print(f"   Stopped after {len(slow_attempts)} attempts")
        print(f"   Error type: {type(e).__name__}")
    print()

    # 8. Preset Configurations
    print("8. PRESET CONFIGURATIONS:")
    print("-" * 40)

    for name in ["quick", "standard", "aggressive", "conservative"]:
        config = manager.get_config(name)
        if config:
            print(f"   {name}: retries={config.max_retries}, strategy={config.strategy.value}")
    print()

    # 9. Statistics
    print("9. STATISTICS:")
    print("-" * 40)

    stats = manager.get_stats("test")
    if stats:
        print(f"   Total attempts: {stats.total_attempts}")
        print(f"   Successful: {stats.successful_attempts}")
        print(f"   Failed: {stats.failed_attempts}")
    print()

    # 10. Composite Policies
    print("10. COMPOSITE POLICIES:")
    print("-" * 40)

    policy1 = ExceptionTypeRetryPolicy()
    policy2 = CallbackRetryPolicy()

    composite = CompositeRetryPolicy([policy1, policy2])

    context = RetryContext(config=RetryConfig(
        max_retries=3,
        retryable_exceptions=[ConnectionError],
        retry_on=lambda e: "temporary" in str(e)
    ))

    err1 = ConnectionError("temporary error")
    err2 = ConnectionError("permanent error")

    print(f"   'temporary' ConnectionError: {composite.should_retry(0, err1, context)}")
    print(f"   'permanent' ConnectionError: {composite.should_retry(0, err2, context)}")
    print()

    # 11. Synchronous Retry
    print("11. SYNCHRONOUS RETRY:")
    print("-" * 40)

    sync_attempts = []

    def sync_flaky():
        sync_attempts.append(1)
        if len(sync_attempts) < 3:
            raise Exception("Sync failure")
        return "Sync success"

    config = RetryConfig(max_retries=5, base_delay=0.01)
    executor = RetryExecutor(config)
    result = executor.execute_sync(sync_flaky)

    print(f"   Result: {result}")
    print(f"   Attempts: {len(sync_attempts)}")
    print()

    # 12. Retry Context
    print("12. RETRY CONTEXT:")
    print("-" * 40)

    context_attempts = []

    async def tracked_operation():
        context_attempts.append(time.time())
        if len(context_attempts) < 2:
            raise Exception("Tracked failure")
        return "tracked success"

    config = RetryConfig(max_retries=3, base_delay=0.05)
    context = RetryContext(config=config)
    executor = RetryExecutor(config)

    await executor.execute(tracked_operation)

    print(f"   Context ID: {context.id[:8]}...")
    print(f"   Attempts tracked: {len(context_attempts)}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Retry Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
