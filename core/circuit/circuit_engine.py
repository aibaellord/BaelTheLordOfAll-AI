#!/usr/bin/env python3
"""
BAEL - Circuit Engine
Circuit breaker pattern for agents.

Features:
- Circuit breaker states
- Failure detection
- Recovery strategies
- Health monitoring
- Fallback handling
"""

import asyncio
import hashlib
import json
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (
    Any, Callable, Coroutine, Dict, Generic, List, Optional, Set, Tuple,
    Type, TypeVar, Union
)


T = TypeVar('T')
R = TypeVar('R')


# =============================================================================
# ENUMS
# =============================================================================

class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class FailureType(Enum):
    """Failure types."""
    EXCEPTION = "exception"
    TIMEOUT = "timeout"
    SLOW_CALL = "slow_call"
    CUSTOM = "custom"


class RecoveryStrategy(Enum):
    """Recovery strategies."""
    FIXED_WAIT = "fixed_wait"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    NO_WAIT = "no_wait"


class HealthStatus(Enum):
    """Health statuses."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class CircuitConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5
    success_threshold: int = 3
    timeout_seconds: float = 30.0
    slow_call_threshold_seconds: float = 5.0
    half_open_max_calls: int = 3
    recovery_strategy: RecoveryStrategy = RecoveryStrategy.EXPONENTIAL_BACKOFF
    initial_wait_seconds: float = 5.0
    max_wait_seconds: float = 60.0
    failure_rate_threshold: float = 0.5


@dataclass
class CallResult:
    """Result of a call."""
    success: bool = True
    value: Any = None
    error: Optional[Exception] = None
    duration_seconds: float = 0.0
    failure_type: Optional[FailureType] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class CircuitStats:
    """Circuit statistics."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    slow_calls: int = 0
    timeouts: int = 0
    state_changes: int = 0
    last_failure: Optional[datetime] = None
    last_success: Optional[datetime] = None
    
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
class StateTransition:
    """State transition record."""
    from_state: CircuitState
    to_state: CircuitState
    reason: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class HealthCheck:
    """Health check result."""
    status: HealthStatus
    circuit_state: CircuitState
    failure_rate: float
    message: str
    timestamp: datetime = field(default_factory=datetime.now)


# =============================================================================
# FAILURE DETECTOR
# =============================================================================

class FailureDetector:
    """Detect failures in calls."""
    
    def __init__(self, config: CircuitConfig):
        self._config = config
        self._exception_types: Set[Type[Exception]] = {Exception}
    
    def register_exception(self, exc_type: Type[Exception]) -> None:
        """Register exception type as failure."""
        self._exception_types.add(exc_type)
    
    def is_failure(self, result: CallResult) -> bool:
        """Check if result is a failure."""
        if not result.success:
            return True
        
        if result.error is not None:
            return True
        
        if result.duration_seconds > self._config.slow_call_threshold_seconds:
            return True
        
        return False
    
    def classify_failure(
        self,
        error: Optional[Exception],
        duration: float
    ) -> Optional[FailureType]:
        """Classify failure type."""
        if duration > self._config.timeout_seconds:
            return FailureType.TIMEOUT
        
        if duration > self._config.slow_call_threshold_seconds:
            return FailureType.SLOW_CALL
        
        if error is not None:
            return FailureType.EXCEPTION
        
        return None


# =============================================================================
# RECOVERY CALCULATOR
# =============================================================================

class RecoveryCalculator:
    """Calculate recovery wait times."""
    
    def __init__(self, config: CircuitConfig):
        self._config = config
        self._attempt = 0
    
    def reset(self) -> None:
        """Reset attempt counter."""
        self._attempt = 0
    
    def next_wait(self) -> float:
        """Get next wait time."""
        self._attempt += 1
        
        if self._config.recovery_strategy == RecoveryStrategy.NO_WAIT:
            return 0.0
        
        elif self._config.recovery_strategy == RecoveryStrategy.FIXED_WAIT:
            return self._config.initial_wait_seconds
        
        elif self._config.recovery_strategy == RecoveryStrategy.LINEAR_BACKOFF:
            wait = self._config.initial_wait_seconds * self._attempt
            return min(wait, self._config.max_wait_seconds)
        
        elif self._config.recovery_strategy == RecoveryStrategy.EXPONENTIAL_BACKOFF:
            wait = self._config.initial_wait_seconds * (2 ** (self._attempt - 1))
            return min(wait, self._config.max_wait_seconds)
        
        return self._config.initial_wait_seconds
    
    @property
    def attempt(self) -> int:
        return self._attempt


# =============================================================================
# SLIDING WINDOW
# =============================================================================

class SlidingWindow:
    """Sliding window for call tracking."""
    
    def __init__(self, size: int = 100):
        self._size = size
        self._results: deque = deque(maxlen=size)
    
    def add(self, result: CallResult) -> None:
        """Add result to window."""
        self._results.append(result)
    
    def failure_rate(self) -> float:
        """Calculate failure rate."""
        if not self._results:
            return 0.0
        
        failures = sum(1 for r in self._results if not r.success)
        return failures / len(self._results)
    
    def success_rate(self) -> float:
        """Calculate success rate."""
        return 1.0 - self.failure_rate()
    
    def count(self) -> int:
        """Get result count."""
        return len(self._results)
    
    def failures(self) -> int:
        """Get failure count."""
        return sum(1 for r in self._results if not r.success)
    
    def successes(self) -> int:
        """Get success count."""
        return sum(1 for r in self._results if r.success)
    
    def clear(self) -> None:
        """Clear window."""
        self._results.clear()
    
    def recent_failures(self, n: int) -> int:
        """Count recent failures."""
        recent = list(self._results)[-n:]
        return sum(1 for r in recent if not r.success)
    
    def recent_successes(self, n: int) -> int:
        """Count recent successes."""
        recent = list(self._results)[-n:]
        return sum(1 for r in recent if r.success)


# =============================================================================
# CIRCUIT BREAKER
# =============================================================================

class CircuitBreaker:
    """Circuit breaker implementation."""
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitConfig] = None,
        fallback: Optional[Callable] = None
    ):
        self._name = name
        self._config = config or CircuitConfig()
        self._fallback = fallback
        
        self._state = CircuitState.CLOSED
        self._stats = CircuitStats()
        self._window = SlidingWindow()
        self._detector = FailureDetector(self._config)
        self._recovery = RecoveryCalculator(self._config)
        
        self._transitions: List[StateTransition] = []
        self._opened_at: Optional[datetime] = None
        self._half_open_calls = 0
        
        self._callbacks: Dict[str, List[Callable]] = defaultdict(list)
    
    async def call(
        self,
        func: Callable[..., Coroutine],
        *args,
        **kwargs
    ) -> CallResult:
        """Execute call through circuit breaker."""
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._transition_to(CircuitState.HALF_OPEN, "timeout expired")
            else:
                self._stats.rejected_calls += 1
                return await self._handle_rejection()
        
        if self._state == CircuitState.HALF_OPEN:
            if self._half_open_calls >= self._config.half_open_max_calls:
                self._stats.rejected_calls += 1
                return await self._handle_rejection()
            self._half_open_calls += 1
        
        result = await self._execute(func, *args, **kwargs)
        self._record_result(result)
        
        return result
    
    async def _execute(
        self,
        func: Callable[..., Coroutine],
        *args,
        **kwargs
    ) -> CallResult:
        """Execute the function."""
        start = time.time()
        
        try:
            value = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self._config.timeout_seconds
            )
            
            duration = time.time() - start
            
            return CallResult(
                success=True,
                value=value,
                duration_seconds=duration
            )
        
        except asyncio.TimeoutError:
            duration = time.time() - start
            self._stats.timeouts += 1
            
            return CallResult(
                success=False,
                error=asyncio.TimeoutError("Call timed out"),
                duration_seconds=duration,
                failure_type=FailureType.TIMEOUT
            )
        
        except Exception as e:
            duration = time.time() - start
            failure_type = self._detector.classify_failure(e, duration)
            
            return CallResult(
                success=False,
                error=e,
                duration_seconds=duration,
                failure_type=failure_type
            )
    
    def _record_result(self, result: CallResult) -> None:
        """Record call result."""
        self._window.add(result)
        self._stats.total_calls += 1
        
        if result.success:
            self._stats.successful_calls += 1
            self._stats.last_success = datetime.now()
            self._on_success()
        else:
            self._stats.failed_calls += 1
            self._stats.last_failure = datetime.now()
            
            if result.duration_seconds > self._config.slow_call_threshold_seconds:
                self._stats.slow_calls += 1
            
            self._on_failure()
    
    def _on_success(self) -> None:
        """Handle successful call."""
        if self._state == CircuitState.HALF_OPEN:
            if self._window.recent_successes(
                self._config.success_threshold
            ) >= self._config.success_threshold:
                self._transition_to(CircuitState.CLOSED, "success threshold reached")
    
    def _on_failure(self) -> None:
        """Handle failed call."""
        if self._state == CircuitState.CLOSED:
            if self._window.recent_failures(
                self._config.failure_threshold
            ) >= self._config.failure_threshold:
                self._transition_to(CircuitState.OPEN, "failure threshold reached")
        
        elif self._state == CircuitState.HALF_OPEN:
            self._transition_to(CircuitState.OPEN, "failure in half-open state")
    
    def _should_attempt_reset(self) -> bool:
        """Check if should attempt reset."""
        if not self._opened_at:
            return True
        
        wait_time = self._recovery.next_wait()
        elapsed = (datetime.now() - self._opened_at).total_seconds()
        
        return elapsed >= wait_time
    
    def _transition_to(self, new_state: CircuitState, reason: str) -> None:
        """Transition to new state."""
        if new_state == self._state:
            return
        
        transition = StateTransition(
            from_state=self._state,
            to_state=new_state,
            reason=reason
        )
        self._transitions.append(transition)
        
        old_state = self._state
        self._state = new_state
        self._stats.state_changes += 1
        
        if new_state == CircuitState.OPEN:
            self._opened_at = datetime.now()
        elif new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
        elif new_state == CircuitState.CLOSED:
            self._recovery.reset()
            self._window.clear()
        
        self._notify("state_change", old_state, new_state, reason)
    
    async def _handle_rejection(self) -> CallResult:
        """Handle rejected call."""
        if self._fallback:
            try:
                if asyncio.iscoroutinefunction(self._fallback):
                    value = await self._fallback()
                else:
                    value = self._fallback()
                
                return CallResult(success=True, value=value)
            except Exception as e:
                return CallResult(success=False, error=e)
        
        return CallResult(
            success=False,
            error=Exception("Circuit is open")
        )
    
    def on(self, event: str, callback: Callable) -> None:
        """Register event callback."""
        self._callbacks[event].append(callback)
    
    def _notify(self, event: str, *args) -> None:
        """Notify callbacks."""
        for callback in self._callbacks.get(event, []):
            try:
                callback(*args)
            except Exception:
                pass
    
    def reset(self) -> None:
        """Reset circuit breaker."""
        self._state = CircuitState.CLOSED
        self._window.clear()
        self._recovery.reset()
        self._half_open_calls = 0
        self._opened_at = None
    
    def force_open(self) -> None:
        """Force circuit open."""
        self._transition_to(CircuitState.OPEN, "forced open")
    
    def force_closed(self) -> None:
        """Force circuit closed."""
        self._transition_to(CircuitState.CLOSED, "forced closed")
    
    def health_check(self) -> HealthCheck:
        """Get health check."""
        if self._state == CircuitState.CLOSED:
            if self._window.failure_rate() < 0.1:
                status = HealthStatus.HEALTHY
                message = "Circuit is healthy"
            else:
                status = HealthStatus.DEGRADED
                message = "Circuit has some failures"
        elif self._state == CircuitState.HALF_OPEN:
            status = HealthStatus.DEGRADED
            message = "Circuit is recovering"
        else:
            status = HealthStatus.UNHEALTHY
            message = "Circuit is open"
        
        return HealthCheck(
            status=status,
            circuit_state=self._state,
            failure_rate=self._window.failure_rate(),
            message=message
        )
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def state(self) -> CircuitState:
        return self._state
    
    @property
    def stats(self) -> CircuitStats:
        return self._stats
    
    @property
    def transitions(self) -> List[StateTransition]:
        return list(self._transitions)


# =============================================================================
# CIRCUIT MANAGER
# =============================================================================

class CircuitManager:
    """Manage multiple circuit breakers."""
    
    def __init__(self):
        self._circuits: Dict[str, CircuitBreaker] = {}
    
    def create(
        self,
        name: str,
        config: Optional[CircuitConfig] = None,
        fallback: Optional[Callable] = None
    ) -> CircuitBreaker:
        """Create circuit breaker."""
        circuit = CircuitBreaker(name, config, fallback)
        self._circuits[name] = circuit
        return circuit
    
    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker."""
        return self._circuits.get(name)
    
    def remove(self, name: str) -> bool:
        """Remove circuit breaker."""
        return self._circuits.pop(name, None) is not None
    
    def list_circuits(self) -> List[str]:
        """List circuit names."""
        return list(self._circuits.keys())
    
    def reset_all(self) -> None:
        """Reset all circuits."""
        for circuit in self._circuits.values():
            circuit.reset()
    
    def health_checks(self) -> Dict[str, HealthCheck]:
        """Get all health checks."""
        return {
            name: circuit.health_check()
            for name, circuit in self._circuits.items()
        }
    
    def stats(self) -> Dict[str, CircuitStats]:
        """Get all stats."""
        return {
            name: circuit.stats
            for name, circuit in self._circuits.items()
        }


# =============================================================================
# CIRCUIT ENGINE
# =============================================================================

class CircuitEngine:
    """
    Circuit Engine for BAEL.
    
    Circuit breaker pattern for agents.
    """
    
    def __init__(self, default_config: Optional[CircuitConfig] = None):
        self._default_config = default_config or CircuitConfig()
        self._manager = CircuitManager()
        
        self._global_callbacks: Dict[str, List[Callable]] = defaultdict(list)
    
    # ----- Circuit Creation -----
    
    def create(
        self,
        name: str,
        config: Optional[CircuitConfig] = None,
        fallback: Optional[Callable] = None
    ) -> CircuitBreaker:
        """Create circuit breaker."""
        config = config or self._default_config
        circuit = self._manager.create(name, config, fallback)
        
        circuit.on("state_change", lambda *args: self._on_state_change(name, *args))
        
        return circuit
    
    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker."""
        return self._manager.get(name)
    
    def remove(self, name: str) -> bool:
        """Remove circuit breaker."""
        return self._manager.remove(name)
    
    def list_circuits(self) -> List[str]:
        """List circuits."""
        return self._manager.list_circuits()
    
    # ----- Circuit Execution -----
    
    async def call(
        self,
        circuit_name: str,
        func: Callable[..., Coroutine],
        *args,
        **kwargs
    ) -> CallResult:
        """Execute call through circuit."""
        circuit = self._manager.get(circuit_name)
        
        if not circuit:
            circuit = self.create(circuit_name)
        
        return await circuit.call(func, *args, **kwargs)
    
    async def execute(
        self,
        circuit_name: str,
        func: Callable[..., Coroutine],
        *args,
        fallback: Optional[Callable] = None,
        **kwargs
    ) -> Any:
        """Execute and return value or fallback."""
        circuit = self._manager.get(circuit_name)
        
        if not circuit:
            circuit = self.create(circuit_name, fallback=fallback)
        
        result = await circuit.call(func, *args, **kwargs)
        
        if result.success:
            return result.value
        elif fallback:
            if asyncio.iscoroutinefunction(fallback):
                return await fallback()
            return fallback()
        else:
            raise result.error or Exception("Call failed")
    
    # ----- Decorator -----
    
    def protect(
        self,
        circuit_name: str,
        config: Optional[CircuitConfig] = None,
        fallback: Optional[Callable] = None
    ):
        """Decorator to protect function with circuit breaker."""
        def decorator(func: Callable):
            circuit = self._manager.get(circuit_name)
            if not circuit:
                circuit = self.create(circuit_name, config, fallback)
            
            async def wrapper(*args, **kwargs):
                result = await circuit.call(func, *args, **kwargs)
                if result.success:
                    return result.value
                elif result.error:
                    raise result.error
                return None
            
            return wrapper
        
        return decorator
    
    # ----- Circuit Control -----
    
    def reset(self, name: str) -> bool:
        """Reset circuit."""
        circuit = self._manager.get(name)
        if circuit:
            circuit.reset()
            return True
        return False
    
    def reset_all(self) -> None:
        """Reset all circuits."""
        self._manager.reset_all()
    
    def force_open(self, name: str) -> bool:
        """Force circuit open."""
        circuit = self._manager.get(name)
        if circuit:
            circuit.force_open()
            return True
        return False
    
    def force_closed(self, name: str) -> bool:
        """Force circuit closed."""
        circuit = self._manager.get(name)
        if circuit:
            circuit.force_closed()
            return True
        return False
    
    def state(self, name: str) -> Optional[CircuitState]:
        """Get circuit state."""
        circuit = self._manager.get(name)
        return circuit.state if circuit else None
    
    def is_open(self, name: str) -> bool:
        """Check if circuit is open."""
        state = self.state(name)
        return state == CircuitState.OPEN
    
    def is_closed(self, name: str) -> bool:
        """Check if circuit is closed."""
        state = self.state(name)
        return state == CircuitState.CLOSED
    
    def is_half_open(self, name: str) -> bool:
        """Check if circuit is half-open."""
        state = self.state(name)
        return state == CircuitState.HALF_OPEN
    
    # ----- Health -----
    
    def health_check(self, name: str) -> Optional[HealthCheck]:
        """Get health check for circuit."""
        circuit = self._manager.get(name)
        return circuit.health_check() if circuit else None
    
    def all_health_checks(self) -> Dict[str, HealthCheck]:
        """Get all health checks."""
        return self._manager.health_checks()
    
    def overall_health(self) -> HealthStatus:
        """Get overall health status."""
        checks = self.all_health_checks()
        
        if not checks:
            return HealthStatus.HEALTHY
        
        unhealthy = sum(1 for c in checks.values() if c.status == HealthStatus.UNHEALTHY)
        degraded = sum(1 for c in checks.values() if c.status == HealthStatus.DEGRADED)
        
        if unhealthy > len(checks) / 2:
            return HealthStatus.UNHEALTHY
        elif unhealthy > 0 or degraded > 0:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY
    
    # ----- Events -----
    
    def on(self, event: str, callback: Callable) -> None:
        """Register global event callback."""
        self._global_callbacks[event].append(callback)
    
    def _on_state_change(
        self,
        circuit_name: str,
        old_state: CircuitState,
        new_state: CircuitState,
        reason: str
    ) -> None:
        """Handle state change."""
        for callback in self._global_callbacks.get("state_change", []):
            try:
                callback(circuit_name, old_state, new_state, reason)
            except Exception:
                pass
    
    # ----- Statistics -----
    
    def get_stats(self, name: str) -> Optional[CircuitStats]:
        """Get circuit stats."""
        circuit = self._manager.get(name)
        return circuit.stats if circuit else None
    
    def all_stats(self) -> Dict[str, CircuitStats]:
        """Get all stats."""
        return self._manager.stats()
    
    def stats(self) -> Dict[str, Any]:
        """Get engine stats."""
        all_stats = self.all_stats()
        
        total_calls = sum(s.total_calls for s in all_stats.values())
        total_failures = sum(s.failed_calls for s in all_stats.values())
        total_rejections = sum(s.rejected_calls for s in all_stats.values())
        
        open_count = sum(
            1 for name in self.list_circuits()
            if self.is_open(name)
        )
        
        return {
            "circuits": len(self.list_circuits()),
            "open_circuits": open_count,
            "total_calls": total_calls,
            "total_failures": total_failures,
            "total_rejections": total_rejections,
            "overall_health": self.overall_health().value
        }
    
    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        circuits_summary = {}
        
        for name in self.list_circuits():
            circuit = self.get(name)
            if circuit:
                circuits_summary[name] = {
                    "state": circuit.state.value,
                    "failure_rate": f"{circuit.stats.failure_rate:.2%}",
                    "total_calls": circuit.stats.total_calls
                }
        
        return {
            "circuits": circuits_summary,
            "overall_health": self.overall_health().value
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Circuit Engine."""
    print("=" * 70)
    print("BAEL - CIRCUIT ENGINE DEMO")
    print("Circuit Breaker Pattern for Agents")
    print("=" * 70)
    print()
    
    engine = CircuitEngine()
    
    # 1. Create Circuit
    print("1. CREATE CIRCUIT:")
    print("-" * 40)
    
    circuit = engine.create("test_circuit", CircuitConfig(
        failure_threshold=3,
        success_threshold=2,
        timeout_seconds=5.0
    ))
    
    print(f"   Created: {circuit.name}")
    print(f"   State: {circuit.state.value}")
    print()
    
    # 2. Successful Calls
    print("2. SUCCESSFUL CALLS:")
    print("-" * 40)
    
    async def success_func():
        await asyncio.sleep(0.1)
        return "success"
    
    for i in range(3):
        result = await engine.call("test_circuit", success_func)
        print(f"   Call {i+1}: {result.value}")
    
    print(f"   State: {engine.state('test_circuit').value}")
    print()
    
    # 3. Failed Calls
    print("3. FAILED CALLS:")
    print("-" * 40)
    
    async def fail_func():
        raise Exception("Intentional failure")
    
    for i in range(3):
        result = await engine.call("fail_circuit", fail_func)
        print(f"   Call {i+1}: success={result.success}")
    
    print(f"   State: {engine.state('fail_circuit').value}")
    print()
    
    # 4. Circuit Open
    print("4. CIRCUIT OPEN:")
    print("-" * 40)
    
    fail_circuit = engine.get("fail_circuit")
    print(f"   Is open: {engine.is_open('fail_circuit')}")
    print(f"   Failed calls: {fail_circuit.stats.failed_calls}")
    print(f"   Rejected calls: {fail_circuit.stats.rejected_calls}")
    
    result = await engine.call("fail_circuit", fail_func)
    print(f"   Call while open: success={result.success}")
    print(f"   Rejected calls: {fail_circuit.stats.rejected_calls}")
    print()
    
    # 5. Fallback
    print("5. FALLBACK:")
    print("-" * 40)
    
    def fallback():
        return "fallback value"
    
    fb_circuit = engine.create("fallback_circuit", fallback=fallback)
    fb_circuit.force_open()
    
    result = await engine.call("fallback_circuit", fail_func)
    print(f"   Result: {result.value}")
    print()
    
    # 6. Reset Circuit
    print("6. RESET CIRCUIT:")
    print("-" * 40)
    
    print(f"   Before reset: {engine.state('fail_circuit').value}")
    engine.reset("fail_circuit")
    print(f"   After reset: {engine.state('fail_circuit').value}")
    print()
    
    # 7. Force States
    print("7. FORCE STATES:")
    print("-" * 40)
    
    engine.force_open("test_circuit")
    print(f"   Forced open: {engine.state('test_circuit').value}")
    
    engine.force_closed("test_circuit")
    print(f"   Forced closed: {engine.state('test_circuit').value}")
    print()
    
    # 8. Health Check
    print("8. HEALTH CHECK:")
    print("-" * 40)
    
    health = engine.health_check("test_circuit")
    print(f"   Status: {health.status.value}")
    print(f"   Circuit state: {health.circuit_state.value}")
    print(f"   Failure rate: {health.failure_rate:.2%}")
    print(f"   Message: {health.message}")
    print()
    
    # 9. All Health Checks
    print("9. ALL HEALTH CHECKS:")
    print("-" * 40)
    
    all_checks = engine.all_health_checks()
    for name, check in all_checks.items():
        print(f"   {name}: {check.status.value}")
    
    print(f"   Overall: {engine.overall_health().value}")
    print()
    
    # 10. Protected Function
    print("10. PROTECTED FUNCTION:")
    print("-" * 40)
    
    @engine.protect("protected_circuit")
    async def protected_func(x):
        return x * 2
    
    result = await protected_func(5)
    print(f"   Result: {result}")
    print()
    
    # 11. Execute with Fallback
    print("11. EXECUTE WITH FALLBACK:")
    print("-" * 40)
    
    engine.force_open("exec_circuit")
    
    result = await engine.execute(
        "exec_circuit",
        fail_func,
        fallback=lambda: "fallback value"
    )
    print(f"   Result: {result}")
    print()
    
    # 12. Circuit Stats
    print("12. CIRCUIT STATS:")
    print("-" * 40)
    
    stats = engine.get_stats("test_circuit")
    print(f"   Total calls: {stats.total_calls}")
    print(f"   Successful: {stats.successful_calls}")
    print(f"   Failed: {stats.failed_calls}")
    print(f"   Failure rate: {stats.failure_rate:.2%}")
    print(f"   State changes: {stats.state_changes}")
    print()
    
    # 13. Transitions
    print("13. TRANSITIONS:")
    print("-" * 40)
    
    transitions = circuit.transitions
    for t in transitions[:5]:
        print(f"   {t.from_state.value} -> {t.to_state.value}: {t.reason}")
    print()
    
    # 14. Event Callbacks
    print("14. EVENT CALLBACKS:")
    print("-" * 40)
    
    changes = []
    
    def on_change(name, old, new, reason):
        changes.append((name, old.value, new.value))
    
    engine.on("state_change", on_change)
    
    engine.create("callback_circuit")
    engine.force_open("callback_circuit")
    engine.force_closed("callback_circuit")
    
    for change in changes:
        print(f"   {change[0]}: {change[1]} -> {change[2]}")
    print()
    
    # 15. Engine Statistics
    print("15. ENGINE STATISTICS:")
    print("-" * 40)
    
    stats = engine.stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()
    
    # 16. Engine Summary
    print("16. ENGINE SUMMARY:")
    print("-" * 40)
    
    summary = engine.summary()
    print(f"   Overall health: {summary['overall_health']}")
    print(f"   Circuits: {len(summary['circuits'])}")
    for name, info in list(summary["circuits"].items())[:3]:
        print(f"   - {name}: {info['state']}")
    print()
    
    print("=" * 70)
    print("DEMO COMPLETE - Circuit Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
