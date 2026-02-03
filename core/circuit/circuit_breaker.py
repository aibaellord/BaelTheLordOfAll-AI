#!/usr/bin/env python3
"""
BAEL - Circuit Breaker System
Comprehensive resilience and fault tolerance system.

Features:
- Circuit breaker pattern (closed, open, half-open)
- Failure counting
- Success rate monitoring
- Automatic recovery
- Fallback handlers
- Health checking
- Bulkhead pattern
- Retry with backoff
- Timeout handling
- Metrics and statistics
"""

import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from functools import wraps
from typing import (Any, Awaitable, Callable, Coroutine, Deque, Dict, Generic,
                    List, Optional, Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing, reject all calls
    HALF_OPEN = "half_open" # Testing if service recovered


class FailureType(Enum):
    """Types of failures."""
    EXCEPTION = "exception"
    TIMEOUT = "timeout"
    REJECTED = "rejected"
    BAD_RESPONSE = "bad_response"


class RetryStrategy(Enum):
    """Retry strategies."""
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    JITTER = "jitter"


class BulkheadType(Enum):
    """Bulkhead isolation types."""
    SEMAPHORE = "semaphore"
    THREAD_POOL = "thread_pool"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class CircuitConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5              # Failures to open circuit
    success_threshold: int = 3              # Successes to close circuit
    timeout_seconds: float = 30.0           # Time in open state before half-open
    call_timeout: float = 10.0              # Timeout per call
    rolling_window_seconds: float = 60.0    # Window for failure counting
    half_open_max_calls: int = 3            # Max calls in half-open state
    slow_call_duration: float = 5.0         # Threshold for slow calls
    slow_call_rate_threshold: float = 0.5   # Rate that triggers open


@dataclass
class CircuitStats:
    """Circuit breaker statistics."""
    state: CircuitState = CircuitState.CLOSED
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    slow_calls: int = 0
    timeouts: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    state_changed_at: datetime = field(default_factory=datetime.utcnow)
    consecutive_failures: int = 0
    consecutive_successes: int = 0


@dataclass
class CallResult:
    """Result of a circuit breaker call."""
    success: bool
    value: Any = None
    error: Optional[Exception] = None
    duration: float = 0.0
    failure_type: Optional[FailureType] = None
    retries: int = 0


@dataclass
class RetryConfig:
    """Retry configuration."""
    max_retries: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    base_delay: float = 1.0
    max_delay: float = 60.0
    jitter_factor: float = 0.1
    retryable_exceptions: List[Type[Exception]] = field(default_factory=list)


@dataclass
class BulkheadConfig:
    """Bulkhead configuration."""
    max_concurrent: int = 10
    max_wait: float = 5.0
    bulkhead_type: BulkheadType = BulkheadType.SEMAPHORE


@dataclass
class HealthStatus:
    """Health status of a circuit."""
    circuit_id: str
    state: CircuitState
    healthy: bool
    success_rate: float
    failure_rate: float
    average_response_time: float
    active_calls: int
    rejected_rate: float


# =============================================================================
# CALL RECORD
# =============================================================================

@dataclass
class CallRecord:
    """Record of a call attempt."""
    timestamp: datetime
    success: bool
    duration: float
    failure_type: Optional[FailureType] = None


# =============================================================================
# SLIDING WINDOW
# =============================================================================

class SlidingWindow:
    """Sliding time window for call statistics."""

    def __init__(self, window_seconds: float):
        self.window_seconds = window_seconds
        self.records: Deque[CallRecord] = deque()
        self._lock = asyncio.Lock()

    async def add(self, record: CallRecord) -> None:
        """Add a record to the window."""
        async with self._lock:
            self.records.append(record)
            await self._cleanup()

    async def _cleanup(self) -> None:
        """Remove old records."""
        cutoff = datetime.utcnow() - timedelta(seconds=self.window_seconds)
        while self.records and self.records[0].timestamp < cutoff:
            self.records.popleft()

    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics from the window."""
        async with self._lock:
            await self._cleanup()

            if not self.records:
                return {
                    "total": 0,
                    "success": 0,
                    "failure": 0,
                    "success_rate": 1.0,
                    "failure_rate": 0.0,
                    "avg_duration": 0.0
                }

            total = len(self.records)
            success = sum(1 for r in self.records if r.success)
            failure = total - success
            durations = [r.duration for r in self.records]

            return {
                "total": total,
                "success": success,
                "failure": failure,
                "success_rate": success / total if total else 1.0,
                "failure_rate": failure / total if total else 0.0,
                "avg_duration": sum(durations) / len(durations) if durations else 0.0
            }

    async def failure_count(self) -> int:
        """Get failure count in window."""
        async with self._lock:
            await self._cleanup()
            return sum(1 for r in self.records if not r.success)

    async def success_count(self) -> int:
        """Get success count in window."""
        async with self._lock:
            await self._cleanup()
            return sum(1 for r in self.records if r.success)


# =============================================================================
# BULKHEAD
# =============================================================================

class Bulkhead:
    """Bulkhead for concurrent call limiting."""

    def __init__(self, config: BulkheadConfig):
        self.config = config
        self._semaphore = asyncio.Semaphore(config.max_concurrent)
        self._active_calls = 0
        self._rejected = 0
        self._lock = asyncio.Lock()

    async def acquire(self) -> bool:
        """Try to acquire a slot."""
        try:
            acquired = await asyncio.wait_for(
                self._semaphore.acquire(),
                timeout=self.config.max_wait
            )
            if acquired:
                async with self._lock:
                    self._active_calls += 1
                return True
        except asyncio.TimeoutError:
            async with self._lock:
                self._rejected += 1
            return False
        return False

    async def release(self) -> None:
        """Release a slot."""
        self._semaphore.release()
        async with self._lock:
            self._active_calls = max(0, self._active_calls - 1)

    @property
    def active_calls(self) -> int:
        """Get active call count."""
        return self._active_calls

    @property
    def rejected_count(self) -> int:
        """Get rejected count."""
        return self._rejected


# =============================================================================
# RETRY HANDLER
# =============================================================================

class RetryHandler:
    """Retry logic handler."""

    def __init__(self, config: RetryConfig):
        self.config = config

    def should_retry(self, attempt: int, exception: Optional[Exception]) -> bool:
        """Check if should retry."""
        if attempt >= self.config.max_retries:
            return False

        if exception and self.config.retryable_exceptions:
            return any(isinstance(exception, exc_type)
                      for exc_type in self.config.retryable_exceptions)

        return True

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt."""
        import random

        if self.config.strategy == RetryStrategy.FIXED:
            delay = self.config.base_delay

        elif self.config.strategy == RetryStrategy.LINEAR:
            delay = self.config.base_delay * (attempt + 1)

        elif self.config.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.config.base_delay * (2 ** attempt)

        elif self.config.strategy == RetryStrategy.JITTER:
            base = self.config.base_delay * (2 ** attempt)
            jitter = base * self.config.jitter_factor * random.random()
            delay = base + jitter

        else:
            delay = self.config.base_delay

        return min(delay, self.config.max_delay)

    async def execute_with_retry(
        self,
        func: Callable[..., Awaitable[Any]],
        *args,
        **kwargs
    ) -> Tuple[Any, int]:
        """Execute function with retries."""
        last_exception = None

        for attempt in range(self.config.max_retries + 1):
            try:
                result = await func(*args, **kwargs)
                return result, attempt
            except Exception as e:
                last_exception = e

                if not self.should_retry(attempt, e):
                    raise

                delay = self.get_delay(attempt)
                await asyncio.sleep(delay)

        raise last_exception or Exception("Retry exhausted")


# =============================================================================
# CIRCUIT BREAKER
# =============================================================================

class CircuitBreaker:
    """
    Circuit breaker implementation.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Circuit tripped, requests fail fast
    - HALF_OPEN: Testing if service recovered
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitConfig] = None,
        fallback: Optional[Callable[..., Any]] = None
    ):
        self.name = name
        self.config = config or CircuitConfig()
        self.fallback = fallback

        self._state = CircuitState.CLOSED
        self._stats = CircuitStats()
        self._window = SlidingWindow(self.config.rolling_window_seconds)
        self._lock = asyncio.Lock()
        self._half_open_calls = 0
        self._opened_at: Optional[datetime] = None

    @property
    def state(self) -> CircuitState:
        """Get current state."""
        return self._state

    @property
    def stats(self) -> CircuitStats:
        """Get statistics."""
        return self._stats

    async def call(
        self,
        func: Callable[..., Awaitable[Any]],
        *args,
        **kwargs
    ) -> CallResult:
        """Execute a call through the circuit breaker."""
        # Check if call is allowed
        allowed, reason = await self._allow_call()

        if not allowed:
            self._stats.rejected_calls += 1

            # Try fallback
            if self.fallback:
                try:
                    result = await self.fallback(*args, **kwargs) if asyncio.iscoroutinefunction(self.fallback) else self.fallback(*args, **kwargs)
                    return CallResult(success=True, value=result)
                except Exception as e:
                    return CallResult(success=False, error=e, failure_type=FailureType.REJECTED)

            return CallResult(
                success=False,
                error=Exception(f"Circuit {self.name} is {self._state.value}: {reason}"),
                failure_type=FailureType.REJECTED
            )

        # Execute call
        start_time = time.time()

        try:
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.call_timeout
            )

            duration = time.time() - start_time
            await self._on_success(duration)

            return CallResult(success=True, value=result, duration=duration)

        except asyncio.TimeoutError:
            duration = time.time() - start_time
            await self._on_failure(FailureType.TIMEOUT, duration)

            if self.fallback:
                try:
                    result = await self.fallback(*args, **kwargs) if asyncio.iscoroutinefunction(self.fallback) else self.fallback(*args, **kwargs)
                    return CallResult(success=True, value=result, duration=duration)
                except Exception:
                    pass

            return CallResult(
                success=False,
                error=asyncio.TimeoutError("Call timed out"),
                duration=duration,
                failure_type=FailureType.TIMEOUT
            )

        except Exception as e:
            duration = time.time() - start_time
            await self._on_failure(FailureType.EXCEPTION, duration)

            if self.fallback:
                try:
                    result = await self.fallback(*args, **kwargs) if asyncio.iscoroutinefunction(self.fallback) else self.fallback(*args, **kwargs)
                    return CallResult(success=True, value=result, duration=duration)
                except Exception:
                    pass

            return CallResult(
                success=False,
                error=e,
                duration=duration,
                failure_type=FailureType.EXCEPTION
            )

    async def _allow_call(self) -> Tuple[bool, str]:
        """Check if a call is allowed."""
        async with self._lock:
            if self._state == CircuitState.CLOSED:
                return True, "Circuit closed"

            elif self._state == CircuitState.OPEN:
                # Check if timeout has elapsed
                if self._opened_at:
                    elapsed = (datetime.utcnow() - self._opened_at).total_seconds()
                    if elapsed >= self.config.timeout_seconds:
                        await self._transition_to(CircuitState.HALF_OPEN)
                        return True, "Circuit half-open"

                return False, "Circuit open"

            elif self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.config.half_open_max_calls:
                    return False, "Half-open call limit reached"

                self._half_open_calls += 1
                return True, "Half-open test call"

        return False, "Unknown state"

    async def _on_success(self, duration: float) -> None:
        """Handle successful call."""
        self._stats.total_calls += 1
        self._stats.successful_calls += 1
        self._stats.consecutive_successes += 1
        self._stats.consecutive_failures = 0
        self._stats.last_success_time = datetime.utcnow()

        if duration > self.config.slow_call_duration:
            self._stats.slow_calls += 1

        await self._window.add(CallRecord(
            timestamp=datetime.utcnow(),
            success=True,
            duration=duration
        ))

        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                if self._stats.consecutive_successes >= self.config.success_threshold:
                    await self._transition_to(CircuitState.CLOSED)

    async def _on_failure(self, failure_type: FailureType, duration: float) -> None:
        """Handle failed call."""
        self._stats.total_calls += 1
        self._stats.failed_calls += 1
        self._stats.consecutive_failures += 1
        self._stats.consecutive_successes = 0
        self._stats.last_failure_time = datetime.utcnow()

        if failure_type == FailureType.TIMEOUT:
            self._stats.timeouts += 1

        await self._window.add(CallRecord(
            timestamp=datetime.utcnow(),
            success=False,
            duration=duration,
            failure_type=failure_type
        ))

        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                # Single failure in half-open trips to open
                await self._transition_to(CircuitState.OPEN)

            elif self._state == CircuitState.CLOSED:
                failure_count = await self._window.failure_count()
                if failure_count >= self.config.failure_threshold:
                    await self._transition_to(CircuitState.OPEN)

    async def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to new state."""
        old_state = self._state
        self._state = new_state
        self._stats.state = new_state
        self._stats.state_changed_at = datetime.utcnow()

        if new_state == CircuitState.OPEN:
            self._opened_at = datetime.utcnow()
            self._half_open_calls = 0

        elif new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0

        elif new_state == CircuitState.CLOSED:
            self._opened_at = None
            self._half_open_calls = 0
            self._stats.consecutive_failures = 0

        logger.info(f"Circuit {self.name}: {old_state.value} -> {new_state.value}")

    async def reset(self) -> None:
        """Reset circuit to closed state."""
        async with self._lock:
            await self._transition_to(CircuitState.CLOSED)
            self._stats = CircuitStats()

    async def force_open(self) -> None:
        """Force circuit to open state."""
        async with self._lock:
            await self._transition_to(CircuitState.OPEN)

    async def get_health(self) -> HealthStatus:
        """Get circuit health status."""
        window_stats = await self._window.get_stats()

        return HealthStatus(
            circuit_id=self.name,
            state=self._state,
            healthy=self._state == CircuitState.CLOSED,
            success_rate=window_stats["success_rate"],
            failure_rate=window_stats["failure_rate"],
            average_response_time=window_stats["avg_duration"],
            active_calls=0,
            rejected_rate=self._stats.rejected_calls / max(1, self._stats.total_calls)
        )


# =============================================================================
# CIRCUIT BREAKER MANAGER
# =============================================================================

class CircuitBreakerManager:
    """
    Manager for multiple circuit breakers.

    Provides centralized management and monitoring.
    """

    def __init__(self):
        self._circuits: Dict[str, CircuitBreaker] = {}
        self._bulkheads: Dict[str, Bulkhead] = {}
        self._retry_handlers: Dict[str, RetryHandler] = {}
        self._global_fallback: Optional[Callable] = None
        self._listeners: List[Callable] = []

    # -------------------------------------------------------------------------
    # CIRCUIT MANAGEMENT
    # -------------------------------------------------------------------------

    def register(
        self,
        name: str,
        config: Optional[CircuitConfig] = None,
        fallback: Optional[Callable] = None,
        bulkhead_config: Optional[BulkheadConfig] = None,
        retry_config: Optional[RetryConfig] = None
    ) -> CircuitBreaker:
        """Register a circuit breaker."""
        circuit = CircuitBreaker(name, config, fallback)
        self._circuits[name] = circuit

        if bulkhead_config:
            self._bulkheads[name] = Bulkhead(bulkhead_config)

        if retry_config:
            self._retry_handlers[name] = RetryHandler(retry_config)

        return circuit

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        return self._circuits.get(name)

    def remove(self, name: str) -> bool:
        """Remove circuit breaker."""
        if name in self._circuits:
            del self._circuits[name]
            self._bulkheads.pop(name, None)
            self._retry_handlers.pop(name, None)
            return True
        return False

    # -------------------------------------------------------------------------
    # CALL EXECUTION
    # -------------------------------------------------------------------------

    async def execute(
        self,
        circuit_name: str,
        func: Callable[..., Awaitable[Any]],
        *args,
        **kwargs
    ) -> CallResult:
        """Execute a call through a circuit breaker."""
        circuit = self._circuits.get(circuit_name)
        if not circuit:
            raise ValueError(f"Circuit {circuit_name} not found")

        bulkhead = self._bulkheads.get(circuit_name)
        retry_handler = self._retry_handlers.get(circuit_name)

        # Acquire bulkhead if configured
        if bulkhead:
            if not await bulkhead.acquire():
                return CallResult(
                    success=False,
                    error=Exception("Bulkhead rejected"),
                    failure_type=FailureType.REJECTED
                )

        try:
            # Execute with retry if configured
            if retry_handler:
                wrapped = self._wrap_with_circuit(circuit, func)
                result, retries = await retry_handler.execute_with_retry(
                    wrapped, *args, **kwargs
                )
                result.retries = retries
                return result

            # Direct circuit call
            return await circuit.call(func, *args, **kwargs)

        finally:
            if bulkhead:
                await bulkhead.release()

    def _wrap_with_circuit(
        self,
        circuit: CircuitBreaker,
        func: Callable[..., Awaitable[Any]]
    ) -> Callable[..., Awaitable[CallResult]]:
        """Wrap function with circuit breaker."""
        async def wrapped(*args, **kwargs) -> CallResult:
            result = await circuit.call(func, *args, **kwargs)
            if not result.success:
                raise result.error or Exception("Call failed")
            return result
        return wrapped

    # -------------------------------------------------------------------------
    # DECORATOR
    # -------------------------------------------------------------------------

    def breaker(
        self,
        circuit_name: str,
        config: Optional[CircuitConfig] = None,
        fallback: Optional[Callable] = None
    ):
        """Decorator for circuit breaker."""
        def decorator(func: Callable[..., Awaitable[Any]]):
            # Auto-register if not exists
            if circuit_name not in self._circuits:
                self.register(circuit_name, config, fallback)

            @wraps(func)
            async def wrapper(*args, **kwargs):
                result = await self.execute(circuit_name, func, *args, **kwargs)
                if result.success:
                    return result.value
                raise result.error or Exception("Circuit breaker call failed")

            return wrapper
        return decorator

    # -------------------------------------------------------------------------
    # MONITORING
    # -------------------------------------------------------------------------

    async def get_all_health(self) -> Dict[str, HealthStatus]:
        """Get health of all circuits."""
        results = {}
        for name, circuit in self._circuits.items():
            results[name] = await circuit.get_health()
        return results

    async def get_all_stats(self) -> Dict[str, CircuitStats]:
        """Get stats of all circuits."""
        return {name: circuit.stats for name, circuit in self._circuits.items()}

    def list_circuits(self) -> List[str]:
        """List all circuit names."""
        return list(self._circuits.keys())

    def get_open_circuits(self) -> List[str]:
        """Get names of open circuits."""
        return [name for name, circuit in self._circuits.items()
                if circuit.state == CircuitState.OPEN]

    # -------------------------------------------------------------------------
    # BATCH OPERATIONS
    # -------------------------------------------------------------------------

    async def reset_all(self) -> None:
        """Reset all circuits."""
        for circuit in self._circuits.values():
            await circuit.reset()

    async def force_open_all(self) -> None:
        """Force all circuits to open."""
        for circuit in self._circuits.values():
            await circuit.force_open()

    # -------------------------------------------------------------------------
    # LISTENERS
    # -------------------------------------------------------------------------

    def add_listener(self, callback: Callable[[str, CircuitState, CircuitState], None]) -> None:
        """Add state change listener."""
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable) -> None:
        """Remove listener."""
        if callback in self._listeners:
            self._listeners.remove(callback)

    # -------------------------------------------------------------------------
    # EXPORT/IMPORT
    # -------------------------------------------------------------------------

    def export_state(self) -> Dict[str, Any]:
        """Export manager state."""
        return {
            "circuits": {
                name: {
                    "state": circuit.state.value,
                    "stats": {
                        "total_calls": circuit.stats.total_calls,
                        "successful_calls": circuit.stats.successful_calls,
                        "failed_calls": circuit.stats.failed_calls,
                        "rejected_calls": circuit.stats.rejected_calls
                    }
                }
                for name, circuit in self._circuits.items()
            }
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Circuit Breaker System."""
    print("=" * 70)
    print("BAEL - CIRCUIT BREAKER SYSTEM DEMO")
    print("Resilience and Fault Tolerance")
    print("=" * 70)
    print()

    manager = CircuitBreakerManager()

    # 1. Register Circuit Breakers
    print("1. REGISTER CIRCUIT BREAKERS:")
    print("-" * 40)

    config = CircuitConfig(
        failure_threshold=3,
        success_threshold=2,
        timeout_seconds=5.0,
        call_timeout=2.0
    )

    service_circuit = manager.register(
        "service-a",
        config=config,
        fallback=lambda: {"status": "fallback", "cached": True}
    )

    manager.register(
        "service-b",
        config=CircuitConfig(failure_threshold=5),
        bulkhead_config=BulkheadConfig(max_concurrent=5),
        retry_config=RetryConfig(max_retries=2, strategy=RetryStrategy.EXPONENTIAL)
    )

    print(f"   Registered: {manager.list_circuits()}")
    print()

    # 2. Successful Calls
    print("2. SUCCESSFUL CALLS:")
    print("-" * 40)

    async def successful_call():
        await asyncio.sleep(0.1)
        return {"status": "success"}

    for i in range(5):
        result = await manager.execute("service-a", successful_call)
        print(f"   Call {i+1}: success={result.success}, duration={result.duration:.3f}s")

    print(f"   Circuit state: {service_circuit.state.value}")
    print()

    # 3. Failing Calls
    print("3. FAILING CALLS:")
    print("-" * 40)

    call_count = 0

    async def failing_call():
        nonlocal call_count
        call_count += 1
        raise Exception(f"Service error #{call_count}")

    for i in range(5):
        result = await manager.execute("service-a", failing_call)
        print(f"   Call {i+1}: success={result.success}, state={service_circuit.state.value}")
        if result.error:
            print(f"           error={str(result.error)[:40]}")

    print()

    # 4. Open Circuit
    print("4. CIRCUIT OPEN - FAST FAIL:")
    print("-" * 40)

    print(f"   State: {service_circuit.state.value}")
    result = await manager.execute("service-a", successful_call)
    print(f"   Call rejected: {not result.success}")
    print(f"   Failure type: {result.failure_type}")
    print(f"   Fallback used: {'fallback' in str(result.value)}")
    print()

    # 5. Wait for Half-Open
    print("5. WAIT FOR HALF-OPEN:")
    print("-" * 40)

    print(f"   Waiting {config.timeout_seconds}s...")
    await asyncio.sleep(config.timeout_seconds + 0.1)

    # Trigger state check
    result = await manager.execute("service-a", successful_call)
    print(f"   State: {service_circuit.state.value}")
    print(f"   Test call: success={result.success}")
    print()

    # 6. Recovery
    print("6. RECOVERY TO CLOSED:")
    print("-" * 40)

    for i in range(config.success_threshold):
        result = await manager.execute("service-a", successful_call)
        print(f"   Success {i+1}: state={service_circuit.state.value}")

    print()

    # 7. Statistics
    print("7. STATISTICS:")
    print("-" * 40)

    stats = service_circuit.stats
    print(f"   Total calls: {stats.total_calls}")
    print(f"   Successful: {stats.successful_calls}")
    print(f"   Failed: {stats.failed_calls}")
    print(f"   Rejected: {stats.rejected_calls}")
    print()

    # 8. Health Check
    print("8. HEALTH CHECK:")
    print("-" * 40)

    health = await service_circuit.get_health()
    print(f"   Circuit: {health.circuit_id}")
    print(f"   State: {health.state.value}")
    print(f"   Healthy: {health.healthy}")
    print(f"   Success rate: {health.success_rate:.2%}")
    print()

    # 9. Timeout Handling
    print("9. TIMEOUT HANDLING:")
    print("-" * 40)

    await service_circuit.reset()

    async def slow_call():
        await asyncio.sleep(5)
        return "done"

    result = await manager.execute("service-a", slow_call)
    print(f"   Success: {result.success}")
    print(f"   Failure type: {result.failure_type}")
    print(f"   Duration: {result.duration:.2f}s")
    print()

    # 10. Retry Handler
    print("10. RETRY HANDLER:")
    print("-" * 40)

    retry_handler = RetryHandler(RetryConfig(
        max_retries=3,
        strategy=RetryStrategy.EXPONENTIAL,
        base_delay=0.1
    ))

    attempts = []

    async def flaky_call():
        attempts.append(time.time())
        if len(attempts) < 3:
            raise Exception("Temporary error")
        return "success after retries"

    try:
        result, retries = await retry_handler.execute_with_retry(flaky_call)
        print(f"   Result: {result}")
        print(f"   Retries: {retries}")
    except Exception as e:
        print(f"   Error: {e}")

    print()

    # 11. Bulkhead
    print("11. BULKHEAD CONCURRENCY:")
    print("-" * 40)

    bulkhead = Bulkhead(BulkheadConfig(max_concurrent=3, max_wait=1.0))

    async def concurrent_task(task_id: int):
        acquired = await bulkhead.acquire()
        if acquired:
            try:
                await asyncio.sleep(0.5)
                return f"Task {task_id} completed"
            finally:
                await bulkhead.release()
        return f"Task {task_id} rejected"

    tasks = [concurrent_task(i) for i in range(6)]
    results = await asyncio.gather(*tasks)

    completed = sum(1 for r in results if "completed" in r)
    rejected = sum(1 for r in results if "rejected" in r)

    print(f"   Completed: {completed}")
    print(f"   Rejected: {rejected}")
    print()

    # 12. Decorator Usage
    print("12. DECORATOR USAGE:")
    print("-" * 40)

    @manager.breaker("decorated-circuit", config=CircuitConfig(failure_threshold=2))
    async def decorated_function(x: int):
        return x * 2

    result = await decorated_function(21)
    print(f"   Result: {result}")
    print(f"   Circuits: {manager.list_circuits()}")
    print()

    # 13. All Health Status
    print("13. ALL CIRCUITS HEALTH:")
    print("-" * 40)

    all_health = await manager.get_all_health()
    for name, health in all_health.items():
        print(f"   {name}: {health.state.value}, healthy={health.healthy}")
    print()

    # 14. Export State
    print("14. EXPORT STATE:")
    print("-" * 40)

    state = manager.export_state()
    print(f"   Circuits: {len(state['circuits'])}")
    for name, info in state['circuits'].items():
        print(f"   {name}: {info['state']}, calls={info['stats']['total_calls']}")
    print()

    # 15. Force Open/Reset
    print("15. ADMINISTRATIVE CONTROLS:")
    print("-" * 40)

    await service_circuit.force_open()
    print(f"   After force_open: {service_circuit.state.value}")

    await service_circuit.reset()
    print(f"   After reset: {service_circuit.state.value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Circuit Breaker System Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
