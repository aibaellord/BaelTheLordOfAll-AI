#!/usr/bin/env python3
"""
BAEL - Circuit Breaker Pattern
Advanced resilience pattern for handling failures in distributed systems.

Features:
- Multiple circuit states (Closed, Open, Half-Open)
- Configurable failure thresholds
- Automatic recovery attempts
- Fallback mechanisms
- Health monitoring
- Event notifications
- Bulkhead pattern
- Timeout handling
- Metrics collection
"""

import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import wraps
from typing import (Any, Awaitable, Callable, Dict, Generic, List, Optional,
                    Set, Tuple, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')


# =============================================================================
# ENUMS
# =============================================================================

class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing recovery


class FailureType(Enum):
    """Types of failures."""
    EXCEPTION = "exception"
    TIMEOUT = "timeout"
    REJECTION = "rejection"
    THRESHOLD = "threshold"


class EventType(Enum):
    """Circuit breaker events."""
    STATE_CHANGE = "state_change"
    SUCCESS = "success"
    FAILURE = "failure"
    REJECTED = "rejected"
    FALLBACK = "fallback"
    RESET = "reset"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class CircuitConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5
    success_threshold: int = 3
    timeout: float = 30.0
    half_open_max_calls: int = 3
    failure_rate_threshold: float = 0.5
    slow_call_duration: float = 5.0
    slow_call_rate_threshold: float = 0.5
    sliding_window_size: int = 100
    sliding_window_type: str = "count"  # count or time
    wait_duration_in_open_state: float = 60.0


@dataclass
class CircuitStats:
    """Circuit breaker statistics."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    timeout_calls: int = 0
    slow_calls: int = 0
    fallback_calls: int = 0
    state_changes: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    last_state_change: Optional[float] = None

    @property
    def failure_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.failed_calls / self.total_calls

    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.successful_calls / self.total_calls


@dataclass
class CallResult:
    """Result of a circuit breaker call."""
    success: bool
    value: Any = None
    error: Optional[Exception] = None
    duration: float = 0.0
    fallback_used: bool = False
    rejected: bool = False


@dataclass
class CircuitEvent:
    """Circuit breaker event."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: float = field(default_factory=time.time)
    event_type: EventType = EventType.SUCCESS
    circuit_name: str = ""
    old_state: Optional[CircuitState] = None
    new_state: Optional[CircuitState] = None
    error: Optional[str] = None
    duration: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# SLIDING WINDOW
# =============================================================================

class SlidingWindow(ABC):
    """Abstract sliding window for tracking calls."""

    @abstractmethod
    def record_success(self, duration: float) -> None:
        """Record a successful call."""
        pass

    @abstractmethod
    def record_failure(self) -> None:
        """Record a failed call."""
        pass

    @abstractmethod
    def get_failure_rate(self) -> float:
        """Get current failure rate."""
        pass

    @abstractmethod
    def get_slow_call_rate(self) -> float:
        """Get slow call rate."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset the window."""
        pass


class CountBasedSlidingWindow(SlidingWindow):
    """Count-based sliding window."""

    def __init__(self, size: int, slow_duration: float = 5.0):
        self.size = size
        self.slow_duration = slow_duration
        self.calls: deque = deque(maxlen=size)

    def record_success(self, duration: float) -> None:
        is_slow = duration > self.slow_duration
        self.calls.append(("success", duration, is_slow))

    def record_failure(self) -> None:
        self.calls.append(("failure", 0, False))

    def get_failure_rate(self) -> float:
        if not self.calls:
            return 0.0
        failures = sum(1 for c in self.calls if c[0] == "failure")
        return failures / len(self.calls)

    def get_slow_call_rate(self) -> float:
        if not self.calls:
            return 0.0
        slow = sum(1 for c in self.calls if c[2])
        return slow / len(self.calls)

    def reset(self) -> None:
        self.calls.clear()


class TimeBasedSlidingWindow(SlidingWindow):
    """Time-based sliding window."""

    def __init__(
        self,
        window_seconds: float = 60.0,
        slow_duration: float = 5.0
    ):
        self.window_seconds = window_seconds
        self.slow_duration = slow_duration
        self.calls: List[Tuple[str, float, bool, float]] = []

    def _cleanup(self) -> None:
        cutoff = time.time() - self.window_seconds
        self.calls = [c for c in self.calls if c[3] > cutoff]

    def record_success(self, duration: float) -> None:
        is_slow = duration > self.slow_duration
        self.calls.append(("success", duration, is_slow, time.time()))
        self._cleanup()

    def record_failure(self) -> None:
        self.calls.append(("failure", 0, False, time.time()))
        self._cleanup()

    def get_failure_rate(self) -> float:
        self._cleanup()
        if not self.calls:
            return 0.0
        failures = sum(1 for c in self.calls if c[0] == "failure")
        return failures / len(self.calls)

    def get_slow_call_rate(self) -> float:
        self._cleanup()
        if not self.calls:
            return 0.0
        slow = sum(1 for c in self.calls if c[2])
        return slow / len(self.calls)

    def reset(self) -> None:
        self.calls.clear()


# =============================================================================
# CIRCUIT BREAKER
# =============================================================================

class CircuitBreaker:
    """
    Circuit breaker for handling failures.
    """

    def __init__(
        self,
        name: str,
        config: CircuitConfig = None,
        fallback: Callable[..., Any] = None
    ):
        self.name = name
        self.config = config or CircuitConfig()
        self.fallback = fallback

        self._state = CircuitState.CLOSED
        self._stats = CircuitStats()
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._last_failure_time: Optional[float] = None
        self._opened_at: Optional[float] = None

        # Sliding window
        if self.config.sliding_window_type == "time":
            self._window = TimeBasedSlidingWindow(
                self.config.sliding_window_size,
                self.config.slow_call_duration
            )
        else:
            self._window = CountBasedSlidingWindow(
                self.config.sliding_window_size,
                self.config.slow_call_duration
            )

        # Event listeners
        self._listeners: List[Callable[[CircuitEvent], Awaitable[None]]] = []

        # Lock for thread safety
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def stats(self) -> CircuitStats:
        return self._stats

    @property
    def is_closed(self) -> bool:
        return self._state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        return self._state == CircuitState.OPEN

    @property
    def is_half_open(self) -> bool:
        return self._state == CircuitState.HALF_OPEN

    def add_listener(
        self,
        listener: Callable[[CircuitEvent], Awaitable[None]]
    ) -> None:
        """Add event listener."""
        self._listeners.append(listener)

    async def _emit_event(self, event: CircuitEvent) -> None:
        """Emit event to listeners."""
        for listener in self._listeners:
            try:
                await listener(event)
            except Exception as e:
                logger.error(f"Event listener error: {e}")

    async def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state."""
        if self._state == new_state:
            return

        old_state = self._state
        self._state = new_state
        self._stats.state_changes += 1
        self._stats.last_state_change = time.time()

        if new_state == CircuitState.OPEN:
            self._opened_at = time.time()
            self._half_open_calls = 0
        elif new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._window.reset()
        elif new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
            self._success_count = 0

        logger.info(f"Circuit {self.name}: {old_state.value} -> {new_state.value}")

        await self._emit_event(CircuitEvent(
            event_type=EventType.STATE_CHANGE,
            circuit_name=self.name,
            old_state=old_state,
            new_state=new_state
        ))

    async def _should_allow_request(self) -> bool:
        """Check if request should be allowed."""
        if self._state == CircuitState.CLOSED:
            return True

        if self._state == CircuitState.OPEN:
            # Check if wait duration has passed
            if self._opened_at:
                elapsed = time.time() - self._opened_at
                if elapsed >= self.config.wait_duration_in_open_state:
                    await self._transition_to(CircuitState.HALF_OPEN)
                    return True
            return False

        if self._state == CircuitState.HALF_OPEN:
            return self._half_open_calls < self.config.half_open_max_calls

        return False

    async def _on_success(self, duration: float) -> None:
        """Handle successful call."""
        self._stats.successful_calls += 1
        self._stats.last_success_time = time.time()

        if duration > self.config.slow_call_duration:
            self._stats.slow_calls += 1

        self._window.record_success(duration)

        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.success_threshold:
                await self._transition_to(CircuitState.CLOSED)

        await self._emit_event(CircuitEvent(
            event_type=EventType.SUCCESS,
            circuit_name=self.name,
            duration=duration
        ))

    async def _on_failure(self, error: Exception) -> None:
        """Handle failed call."""
        self._stats.failed_calls += 1
        self._stats.last_failure_time = time.time()
        self._failure_count += 1
        self._last_failure_time = time.time()

        self._window.record_failure()

        await self._emit_event(CircuitEvent(
            event_type=EventType.FAILURE,
            circuit_name=self.name,
            error=str(error)
        ))

        # Check if should open
        if self._state == CircuitState.CLOSED:
            failure_rate = self._window.get_failure_rate()

            if (self._failure_count >= self.config.failure_threshold or
                failure_rate >= self.config.failure_rate_threshold):
                await self._transition_to(CircuitState.OPEN)

        elif self._state == CircuitState.HALF_OPEN:
            await self._transition_to(CircuitState.OPEN)

    async def call(
        self,
        func: Callable[..., Awaitable[T]],
        *args,
        **kwargs
    ) -> CallResult:
        """Execute a call through the circuit breaker."""
        async with self._lock:
            self._stats.total_calls += 1

            # Check if request is allowed
            if not await self._should_allow_request():
                self._stats.rejected_calls += 1

                await self._emit_event(CircuitEvent(
                    event_type=EventType.REJECTED,
                    circuit_name=self.name
                ))

                # Try fallback
                if self.fallback:
                    try:
                        result = await self.fallback(*args, **kwargs)
                        self._stats.fallback_calls += 1
                        return CallResult(
                            success=True,
                            value=result,
                            fallback_used=True,
                            rejected=True
                        )
                    except Exception as e:
                        return CallResult(
                            success=False,
                            error=e,
                            fallback_used=True,
                            rejected=True
                        )

                return CallResult(
                    success=False,
                    error=CircuitOpenError(f"Circuit {self.name} is open"),
                    rejected=True
                )

            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls += 1

        # Execute the call
        start = time.time()

        try:
            # Apply timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.timeout
            )

            duration = time.time() - start
            await self._on_success(duration)

            return CallResult(
                success=True,
                value=result,
                duration=duration
            )

        except asyncio.TimeoutError:
            self._stats.timeout_calls += 1
            await self._on_failure(TimeoutError("Call timed out"))

            # Try fallback
            if self.fallback:
                try:
                    result = await self.fallback(*args, **kwargs)
                    self._stats.fallback_calls += 1
                    return CallResult(
                        success=True,
                        value=result,
                        fallback_used=True
                    )
                except Exception as e:
                    return CallResult(
                        success=False,
                        error=e,
                        fallback_used=True
                    )

            return CallResult(
                success=False,
                error=TimeoutError("Call timed out"),
                duration=time.time() - start
            )

        except Exception as e:
            await self._on_failure(e)

            # Try fallback
            if self.fallback:
                try:
                    result = await self.fallback(*args, **kwargs)
                    self._stats.fallback_calls += 1
                    return CallResult(
                        success=True,
                        value=result,
                        fallback_used=True
                    )
                except Exception as fallback_error:
                    return CallResult(
                        success=False,
                        error=fallback_error,
                        fallback_used=True
                    )

            return CallResult(
                success=False,
                error=e,
                duration=time.time() - start
            )

    async def reset(self) -> None:
        """Reset the circuit breaker."""
        async with self._lock:
            await self._transition_to(CircuitState.CLOSED)
            self._failure_count = 0
            self._success_count = 0
            self._window.reset()

            await self._emit_event(CircuitEvent(
                event_type=EventType.RESET,
                circuit_name=self.name
            ))


class CircuitOpenError(Exception):
    """Raised when circuit is open."""
    pass


# =============================================================================
# BULKHEAD
# =============================================================================

class Bulkhead:
    """
    Bulkhead pattern for resource isolation.
    Limits concurrent executions.
    """

    def __init__(
        self,
        name: str,
        max_concurrent: int = 10,
        max_wait: float = 5.0
    ):
        self.name = name
        self.max_concurrent = max_concurrent
        self.max_wait = max_wait

        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active = 0
        self._waiting = 0
        self._rejected = 0
        self._completed = 0

    @property
    def active_count(self) -> int:
        return self._active

    @property
    def available(self) -> int:
        return self.max_concurrent - self._active

    async def execute(
        self,
        func: Callable[..., Awaitable[T]],
        *args,
        **kwargs
    ) -> T:
        """Execute with bulkhead protection."""
        self._waiting += 1

        try:
            acquired = await asyncio.wait_for(
                self._semaphore.acquire(),
                timeout=self.max_wait
            )

            if not acquired:
                self._rejected += 1
                raise BulkheadFullError(f"Bulkhead {self.name} is full")

        except asyncio.TimeoutError:
            self._waiting -= 1
            self._rejected += 1
            raise BulkheadFullError(
                f"Bulkhead {self.name} wait timeout"
            )

        self._waiting -= 1
        self._active += 1

        try:
            result = await func(*args, **kwargs)
            self._completed += 1
            return result
        finally:
            self._active -= 1
            self._semaphore.release()

    def get_stats(self) -> Dict[str, Any]:
        """Get bulkhead statistics."""
        return {
            "name": self.name,
            "max_concurrent": self.max_concurrent,
            "active": self._active,
            "waiting": self._waiting,
            "available": self.available,
            "completed": self._completed,
            "rejected": self._rejected
        }


class BulkheadFullError(Exception):
    """Raised when bulkhead is full."""
    pass


# =============================================================================
# CIRCUIT BREAKER MANAGER
# =============================================================================

class CircuitBreakerManager:
    """
    Manager for multiple circuit breakers.
    """

    def __init__(self):
        self.circuits: Dict[str, CircuitBreaker] = {}
        self.bulkheads: Dict[str, Bulkhead] = {}
        self._default_config = CircuitConfig()

    def create_circuit(
        self,
        name: str,
        config: CircuitConfig = None,
        fallback: Callable[..., Any] = None
    ) -> CircuitBreaker:
        """Create a circuit breaker."""
        circuit = CircuitBreaker(
            name,
            config or self._default_config,
            fallback
        )
        self.circuits[name] = circuit
        return circuit

    def get_circuit(self, name: str) -> Optional[CircuitBreaker]:
        """Get a circuit breaker by name."""
        return self.circuits.get(name)

    def create_bulkhead(
        self,
        name: str,
        max_concurrent: int = 10,
        max_wait: float = 5.0
    ) -> Bulkhead:
        """Create a bulkhead."""
        bulkhead = Bulkhead(name, max_concurrent, max_wait)
        self.bulkheads[name] = bulkhead
        return bulkhead

    def get_bulkhead(self, name: str) -> Optional[Bulkhead]:
        """Get a bulkhead by name."""
        return self.bulkheads.get(name)

    def circuit(
        self,
        name: str = None,
        config: CircuitConfig = None,
        fallback: Callable[..., Any] = None
    ) -> Callable:
        """Decorator for circuit breaker."""
        def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[CallResult]]:
            circuit_name = name or func.__name__

            if circuit_name not in self.circuits:
                self.create_circuit(circuit_name, config, fallback)

            circuit = self.circuits[circuit_name]

            @wraps(func)
            async def wrapper(*args, **kwargs) -> CallResult:
                return await circuit.call(func, *args, **kwargs)

            return wrapper

        return decorator

    def bulkhead(
        self,
        name: str = None,
        max_concurrent: int = 10,
        max_wait: float = 5.0
    ) -> Callable:
        """Decorator for bulkhead."""
        def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
            bulkhead_name = name or func.__name__

            if bulkhead_name not in self.bulkheads:
                self.create_bulkhead(bulkhead_name, max_concurrent, max_wait)

            bh = self.bulkheads[bulkhead_name]

            @wraps(func)
            async def wrapper(*args, **kwargs) -> T:
                return await bh.execute(func, *args, **kwargs)

            return wrapper

        return decorator

    async def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for circuit in self.circuits.values():
            await circuit.reset()

    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all circuits."""
        return {
            "circuits": {
                name: {
                    "state": circuit.state.value,
                    "stats": {
                        "total_calls": circuit.stats.total_calls,
                        "successful": circuit.stats.successful_calls,
                        "failed": circuit.stats.failed_calls,
                        "rejected": circuit.stats.rejected_calls,
                        "timeout": circuit.stats.timeout_calls,
                        "fallback": circuit.stats.fallback_calls,
                        "failure_rate": circuit.stats.failure_rate
                    }
                }
                for name, circuit in self.circuits.items()
            },
            "bulkheads": {
                name: bh.get_stats()
                for name, bh in self.bulkheads.items()
            }
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Circuit Breaker System."""
    print("=" * 70)
    print("BAEL - CIRCUIT BREAKER SYSTEM DEMO")
    print("Advanced Resilience Pattern")
    print("=" * 70)
    print()

    manager = CircuitBreakerManager()

    # 1. Basic Circuit Breaker
    print("1. BASIC CIRCUIT BREAKER:")
    print("-" * 40)

    config = CircuitConfig(
        failure_threshold=3,
        success_threshold=2,
        timeout=5.0,
        wait_duration_in_open_state=5.0
    )

    circuit = manager.create_circuit("demo", config)

    # Event listener
    events = []
    async def event_listener(event: CircuitEvent):
        events.append(event)
        print(f"   Event: {event.event_type.value}")

    circuit.add_listener(event_listener)

    # Successful calls
    async def success_call():
        return "success"

    for i in range(3):
        result = await circuit.call(success_call)
        print(f"   Call {i+1}: success={result.success}, value={result.value}")

    print(f"   State: {circuit.state.value}")
    print()

    # 2. Failure Handling
    print("2. FAILURE HANDLING:")
    print("-" * 40)

    fail_count = 0

    async def failing_call():
        nonlocal fail_count
        fail_count += 1
        raise ValueError(f"Failure {fail_count}")

    for i in range(4):
        result = await circuit.call(failing_call)
        print(f"   Call {i+1}: success={result.success}, error={result.error}")

    print(f"   State: {circuit.state.value}")
    print(f"   Failure count: {circuit.stats.failed_calls}")
    print()

    # 3. Circuit Open Behavior
    print("3. CIRCUIT OPEN BEHAVIOR:")
    print("-" * 40)

    result = await circuit.call(success_call)
    print(f"   Call while open: rejected={result.rejected}")
    print(f"   Rejected calls: {circuit.stats.rejected_calls}")
    print()

    # 4. Fallback
    print("4. FALLBACK MECHANISM:")
    print("-" * 40)

    async def fallback_handler():
        return "fallback value"

    circuit_fb = manager.create_circuit(
        "fallback_demo",
        CircuitConfig(failure_threshold=2),
        fallback=fallback_handler
    )

    # Open the circuit
    async def always_fail():
        raise Exception("Always fails")

    for _ in range(3):
        await circuit_fb.call(always_fail)

    result = await circuit_fb.call(always_fail)
    print(f"   Fallback used: {result.fallback_used}")
    print(f"   Value: {result.value}")
    print()

    # 5. Half-Open Recovery
    print("5. HALF-OPEN RECOVERY:")
    print("-" * 40)

    recovery_circuit = manager.create_circuit(
        "recovery",
        CircuitConfig(
            failure_threshold=2,
            success_threshold=2,
            wait_duration_in_open_state=1.0
        )
    )

    # Trigger open state
    for _ in range(3):
        await recovery_circuit.call(always_fail)

    print(f"   State after failures: {recovery_circuit.state.value}")

    # Wait for half-open
    await asyncio.sleep(1.5)

    # Successful calls for recovery
    result = await recovery_circuit.call(success_call)
    print(f"   State after wait: {recovery_circuit.state.value}")

    await recovery_circuit.call(success_call)
    print(f"   State after recovery: {recovery_circuit.state.value}")
    print()

    # 6. Timeout Handling
    print("6. TIMEOUT HANDLING:")
    print("-" * 40)

    timeout_circuit = manager.create_circuit(
        "timeout",
        CircuitConfig(timeout=1.0, failure_threshold=2)
    )

    async def slow_call():
        await asyncio.sleep(2.0)
        return "done"

    result = await timeout_circuit.call(slow_call)
    print(f"   Timeout result: success={result.success}")
    print(f"   Timeout calls: {timeout_circuit.stats.timeout_calls}")
    print()

    # 7. Sliding Window
    print("7. SLIDING WINDOW:")
    print("-" * 40)

    window_circuit = manager.create_circuit(
        "window",
        CircuitConfig(
            sliding_window_size=10,
            failure_rate_threshold=0.5
        )
    )

    # Mix of success and failures
    call_count = 0
    async def mixed_call():
        nonlocal call_count
        call_count += 1
        if call_count % 2 == 0:
            raise ValueError("Even number failure")
        return "odd success"

    for i in range(8):
        result = await window_circuit.call(mixed_call)

    print(f"   Failure rate: {window_circuit._window.get_failure_rate():.2%}")
    print(f"   State: {window_circuit.state.value}")
    print()

    # 8. Bulkhead
    print("8. BULKHEAD PATTERN:")
    print("-" * 40)

    bulkhead = manager.create_bulkhead("limited", max_concurrent=3)

    async def work(id: int):
        await asyncio.sleep(0.5)
        return f"Work {id} done"

    # Execute concurrently
    tasks = [bulkhead.execute(work, i) for i in range(3)]
    results = await asyncio.gather(*tasks)

    print(f"   Completed: {len(results)}")
    print(f"   Stats: {bulkhead.get_stats()}")
    print()

    # 9. Decorator Usage
    print("9. DECORATOR USAGE:")
    print("-" * 40)

    @manager.circuit(name="decorated", config=CircuitConfig(failure_threshold=2))
    async def decorated_call(value: int):
        if value < 0:
            raise ValueError("Negative value")
        return value * 2

    result = await decorated_call(5)
    print(f"   Decorated call: success={result.success}, value={result.value}")

    @manager.bulkhead(name="limited_decorator", max_concurrent=2)
    async def limited_call():
        return "limited"

    result = await limited_call()
    print(f"   Bulkhead call: {result}")
    print()

    # 10. Reset
    print("10. RESET CIRCUIT:")
    print("-" * 40)

    # Get a circuit in open state
    reset_circuit = manager.get_circuit("demo")
    print(f"   Before reset: {reset_circuit.state.value}")

    await reset_circuit.reset()
    print(f"   After reset: {reset_circuit.state.value}")
    print()

    # 11. Statistics
    print("11. STATISTICS:")
    print("-" * 40)

    stats = manager.get_all_stats()
    print(f"   Total circuits: {len(stats['circuits'])}")
    print(f"   Total bulkheads: {len(stats['bulkheads'])}")

    for name, data in stats['circuits'].items():
        print(f"   Circuit '{name}': state={data['state']}, "
              f"calls={data['stats']['total_calls']}")
    print()

    # 12. Events Summary
    print("12. EVENTS SUMMARY:")
    print("-" * 40)

    print(f"   Total events captured: {len(events)}")
    event_types = defaultdict(int)
    for e in events:
        event_types[e.event_type.value] += 1

    for etype, count in event_types.items():
        print(f"   {etype}: {count}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Circuit Breaker System Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
