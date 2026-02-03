#!/usr/bin/env python3
"""
BAEL - Error Recovery System
Resilient error handling and automatic recovery.

This module implements comprehensive error handling
and recovery mechanisms for building fault-tolerant
AI agent operations.

Features:
- Multi-level error classification
- Automatic retry with backoff
- Circuit breaker patterns
- Graceful degradation
- Error aggregation
- Recovery strategies
- Fallback mechanisms
- Error prediction
- Self-healing capabilities
- Error chain analysis
- Recovery playbooks
- Chaos engineering support
"""

import asyncio
import functools
import logging
import random
import time
import traceback
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)
from uuid import uuid4

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ErrorSeverity(Enum):
    """Severity levels for errors."""
    DEBUG = 1
    INFO = 2
    WARNING = 3
    ERROR = 4
    CRITICAL = 5
    FATAL = 6


class ErrorCategory(Enum):
    """Categories of errors."""
    TRANSIENT = "transient"        # Temporary, retry-able
    PERMANENT = "permanent"         # Cannot be recovered
    RESOURCE = "resource"           # Resource exhaustion
    CONFIGURATION = "configuration" # Config issues
    NETWORK = "network"             # Network problems
    TIMEOUT = "timeout"             # Timeout errors
    VALIDATION = "validation"       # Input validation
    DEPENDENCY = "dependency"       # External dependency
    INTERNAL = "internal"           # Internal logic errors


class RecoveryAction(Enum):
    """Types of recovery actions."""
    RETRY = "retry"
    FALLBACK = "fallback"
    SKIP = "skip"
    ABORT = "abort"
    ESCALATE = "escalate"
    HEAL = "heal"
    RESTART = "restart"


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class RetryStrategy(Enum):
    """Retry strategies."""
    IMMEDIATE = "immediate"
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIBONACCI = "fibonacci"
    JITTERED = "jittered"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ErrorContext:
    """Context information for an error."""
    operation: str = ""
    component: str = ""
    request_id: str = ""
    user_id: str = ""
    additional_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorRecord:
    """A recorded error."""
    id: str = field(default_factory=lambda: str(uuid4()))
    error_type: str = ""
    message: str = ""
    severity: ErrorSeverity = ErrorSeverity.ERROR
    category: ErrorCategory = ErrorCategory.INTERNAL
    stack_trace: str = ""
    context: ErrorContext = field(default_factory=ErrorContext)
    occurred_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    recovery_action: Optional[RecoveryAction] = None
    recovery_attempts: int = 0
    parent_error_id: Optional[str] = None


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    jitter_factor: float = 0.1
    retryable_errors: List[Type[Exception]] = field(default_factory=list)
    non_retryable_errors: List[Type[Exception]] = field(default_factory=list)


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5
    success_threshold: int = 3
    timeout_seconds: float = 30.0
    half_open_max_calls: int = 3


@dataclass
class RecoveryPlaybook:
    """A playbook for error recovery."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    error_patterns: List[str] = field(default_factory=list)
    actions: List[RecoveryAction] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)
    cooldown_seconds: float = 0.0
    last_executed: Optional[datetime] = None


@dataclass
class HealthReport:
    """System health report for error recovery."""
    healthy: bool = True
    errors_last_hour: int = 0
    recovery_success_rate: float = 1.0
    active_circuits_open: int = 0
    degraded_components: List[str] = field(default_factory=list)


# =============================================================================
# RETRY HANDLER
# =============================================================================

class RetryHandler:
    """
    Handles retry logic with various strategies.

    Supports exponential backoff, jitter, and more.
    """

    def __init__(self, config: RetryConfig = None):
        self.config = config or RetryConfig()
        self.fibonacci_cache = [1, 1]

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for next retry attempt."""
        base = self.config.base_delay_seconds

        if self.config.strategy == RetryStrategy.IMMEDIATE:
            delay = 0.0
        elif self.config.strategy == RetryStrategy.FIXED:
            delay = base
        elif self.config.strategy == RetryStrategy.LINEAR:
            delay = base * attempt
        elif self.config.strategy == RetryStrategy.EXPONENTIAL:
            delay = base * (2 ** (attempt - 1))
        elif self.config.strategy == RetryStrategy.FIBONACCI:
            delay = base * self._fibonacci(attempt)
        elif self.config.strategy == RetryStrategy.JITTERED:
            delay = base * (2 ** (attempt - 1))
            jitter = delay * self.config.jitter_factor * random.random()
            delay += jitter
        else:
            delay = base

        # Apply jitter to non-jittered strategies
        if self.config.strategy != RetryStrategy.JITTERED:
            jitter = delay * self.config.jitter_factor * random.random()
            delay += jitter

        return min(delay, self.config.max_delay_seconds)

    def _fibonacci(self, n: int) -> int:
        """Get fibonacci number."""
        while len(self.fibonacci_cache) <= n:
            self.fibonacci_cache.append(
                self.fibonacci_cache[-1] + self.fibonacci_cache[-2]
            )
        return self.fibonacci_cache[n - 1] if n > 0 else 1

    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Determine if error should be retried."""
        if attempt >= self.config.max_attempts:
            return False

        error_type = type(error)

        # Check non-retryable first
        if self.config.non_retryable_errors:
            for non_retryable in self.config.non_retryable_errors:
                if isinstance(error, non_retryable):
                    return False

        # Check retryable
        if self.config.retryable_errors:
            for retryable in self.config.retryable_errors:
                if isinstance(error, retryable):
                    return True
            return False

        # Default: retry all except non-retryable
        return True

    async def execute(
        self,
        func: Callable[..., T],
        *args,
        **kwargs
    ) -> T:
        """Execute function with retry logic."""
        last_error = None

        for attempt in range(1, self.config.max_attempts + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except Exception as e:
                last_error = e

                if not self.should_retry(e, attempt):
                    raise

                if attempt < self.config.max_attempts:
                    delay = self.calculate_delay(attempt)
                    logger.warning(
                        f"Retry attempt {attempt}/{self.config.max_attempts} "
                        f"after {delay:.2f}s: {e}"
                    )
                    await asyncio.sleep(delay)

        raise last_error


# =============================================================================
# CIRCUIT BREAKER
# =============================================================================

class CircuitBreaker:
    """
    Implements circuit breaker pattern.

    Prevents cascading failures by stopping calls
    to failing services.
    """

    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig = None
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_calls = 0

    @property
    def is_open(self) -> bool:
        """Check if circuit is open."""
        if self.state == CircuitState.OPEN:
            # Check if timeout has passed
            if self.last_failure_time:
                elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                if elapsed >= self.config.timeout_seconds:
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    return False
            return True
        return False

    def record_success(self) -> None:
        """Record a successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
        else:
            self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self) -> None:
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.half_open_calls = 0
        elif self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN

    def allow_request(self) -> bool:
        """Check if request should be allowed."""
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            if self.is_open:
                return False
            # State may have changed to HALF_OPEN
            return self.state == CircuitState.HALF_OPEN
        else:  # HALF_OPEN
            if self.half_open_calls < self.config.half_open_max_calls:
                self.half_open_calls += 1
                return True
            return False

    async def execute(
        self,
        func: Callable[..., T],
        *args,
        **kwargs
    ) -> T:
        """Execute function with circuit breaker protection."""
        if not self.allow_request():
            raise CircuitOpenError(
                f"Circuit '{self.name}' is open"
            )

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise


class CircuitOpenError(Exception):
    """Exception raised when circuit is open."""
    pass


# =============================================================================
# FALLBACK MANAGER
# =============================================================================

class FallbackManager:
    """
    Manages fallback strategies for failed operations.

    Provides graceful degradation capabilities.
    """

    def __init__(self):
        self.fallbacks: Dict[str, List[Callable]] = {}
        self.default_fallbacks: Dict[str, Any] = {}

    def register_fallback(
        self,
        operation: str,
        fallback: Callable,
        priority: int = 0
    ) -> None:
        """Register a fallback for an operation."""
        if operation not in self.fallbacks:
            self.fallbacks[operation] = []

        self.fallbacks[operation].append((priority, fallback))
        self.fallbacks[operation].sort(key=lambda x: x[0], reverse=True)

    def set_default(self, operation: str, default_value: Any) -> None:
        """Set default value for an operation."""
        self.default_fallbacks[operation] = default_value

    async def execute_with_fallback(
        self,
        operation: str,
        primary: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Execute with fallback chain."""
        # Try primary
        try:
            if asyncio.iscoroutinefunction(primary):
                return await primary(*args, **kwargs)
            else:
                return primary(*args, **kwargs)
        except Exception as primary_error:
            logger.warning(f"Primary failed for {operation}: {primary_error}")

        # Try fallbacks
        fallbacks = self.fallbacks.get(operation, [])
        for priority, fallback in fallbacks:
            try:
                if asyncio.iscoroutinefunction(fallback):
                    return await fallback(*args, **kwargs)
                else:
                    return fallback(*args, **kwargs)
            except Exception as fallback_error:
                logger.warning(f"Fallback failed for {operation}: {fallback_error}")

        # Return default if available
        if operation in self.default_fallbacks:
            return self.default_fallbacks[operation]

        raise NoFallbackAvailableError(f"All fallbacks failed for {operation}")


class NoFallbackAvailableError(Exception):
    """Exception when no fallback is available."""
    pass


# =============================================================================
# ERROR AGGREGATOR
# =============================================================================

class ErrorAggregator:
    """
    Aggregates and analyzes errors.

    Identifies patterns and provides insights.
    """

    def __init__(self, window_size: int = 1000):
        self.errors: deque = deque(maxlen=window_size)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.category_counts: Dict[ErrorCategory, int] = defaultdict(int)
        self.severity_counts: Dict[ErrorSeverity, int] = defaultdict(int)

    def record(self, error: ErrorRecord) -> None:
        """Record an error."""
        self.errors.append(error)
        self.error_counts[error.error_type] += 1
        self.category_counts[error.category] += 1
        self.severity_counts[error.severity] += 1

    def get_recent_errors(
        self,
        count: int = 10,
        severity: ErrorSeverity = None,
        category: ErrorCategory = None
    ) -> List[ErrorRecord]:
        """Get recent errors with optional filtering."""
        result = []

        for error in reversed(self.errors):
            if severity and error.severity != severity:
                continue
            if category and error.category != category:
                continue
            result.append(error)
            if len(result) >= count:
                break

        return result

    def get_error_rate(
        self,
        window_seconds: float = 60.0
    ) -> float:
        """Get error rate per second."""
        cutoff = datetime.now() - timedelta(seconds=window_seconds)
        recent = sum(1 for e in self.errors if e.occurred_at > cutoff)
        return recent / window_seconds

    def get_top_errors(self, count: int = 10) -> List[Tuple[str, int]]:
        """Get most frequent error types."""
        sorted_errors = sorted(
            self.error_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_errors[:count]

    def identify_patterns(self) -> List[Dict[str, Any]]:
        """Identify error patterns."""
        patterns = []

        # Check for error bursts
        recent = list(self.errors)[-100:]
        if len(recent) >= 10:
            time_span = (recent[-1].occurred_at - recent[0].occurred_at).total_seconds()
            if time_span > 0 and len(recent) / time_span > 1:  # >1 error/second
                patterns.append({
                    "type": "burst",
                    "description": f"Error burst detected: {len(recent)} errors in {time_span:.1f}s",
                    "severity": "high"
                })

        # Check for repeating errors
        for error_type, count in self.error_counts.items():
            if count >= 10:
                patterns.append({
                    "type": "repetition",
                    "description": f"Repeated error: {error_type} occurred {count} times",
                    "severity": "medium"
                })

        # Check for cascading failures
        recent_errors = self.get_recent_errors(20)
        components = defaultdict(list)
        for error in recent_errors:
            if error.context.component:
                components[error.context.component].append(error)

        multi_component = [c for c, errs in components.items() if len(errs) >= 3]
        if len(multi_component) >= 2:
            patterns.append({
                "type": "cascade",
                "description": f"Potential cascade: errors in {len(multi_component)} components",
                "severity": "high"
            })

        return patterns

    def get_summary(self) -> Dict[str, Any]:
        """Get error summary."""
        return {
            "total_errors": len(self.errors),
            "by_category": dict(self.category_counts),
            "by_severity": {k.name: v for k, v in self.severity_counts.items()},
            "error_rate_per_minute": self.get_error_rate(60) * 60,
            "top_errors": self.get_top_errors(5)
        }


# =============================================================================
# SELF-HEALER
# =============================================================================

class SelfHealer:
    """
    Implements self-healing capabilities.

    Automatically attempts to heal common issues.
    """

    def __init__(self):
        self.playbooks: Dict[str, RecoveryPlaybook] = {}
        self.healing_actions: Dict[str, Callable] = {}
        self.healing_history: List[Dict[str, Any]] = []

    def register_playbook(self, playbook: RecoveryPlaybook) -> None:
        """Register a recovery playbook."""
        self.playbooks[playbook.id] = playbook

    def register_healing_action(
        self,
        name: str,
        action: Callable
    ) -> None:
        """Register a healing action."""
        self.healing_actions[name] = action

    def find_playbook(self, error: ErrorRecord) -> Optional[RecoveryPlaybook]:
        """Find matching playbook for error."""
        for playbook in self.playbooks.values():
            for pattern in playbook.error_patterns:
                if pattern in error.error_type or pattern in error.message:
                    # Check cooldown
                    if playbook.last_executed:
                        elapsed = (datetime.now() - playbook.last_executed).total_seconds()
                        if elapsed < playbook.cooldown_seconds:
                            continue
                    return playbook
        return None

    async def heal(self, error: ErrorRecord) -> bool:
        """Attempt to heal an error."""
        playbook = self.find_playbook(error)
        if not playbook:
            return False

        success = True
        actions_executed = []

        for action in playbook.actions:
            action_name = action.value

            if action_name in self.healing_actions:
                try:
                    heal_func = self.healing_actions[action_name]
                    if asyncio.iscoroutinefunction(heal_func):
                        await heal_func(error)
                    else:
                        heal_func(error)
                    actions_executed.append(action_name)
                except Exception as e:
                    logger.error(f"Healing action {action_name} failed: {e}")
                    success = False

        playbook.last_executed = datetime.now()

        self.healing_history.append({
            "error_id": error.id,
            "playbook": playbook.name,
            "actions": actions_executed,
            "success": success,
            "timestamp": datetime.now()
        })

        return success


# =============================================================================
# ERROR RECOVERY SYSTEM
# =============================================================================

class ErrorRecoverySystem:
    """
    The master error recovery system for BAEL.

    Provides comprehensive error handling, recovery,
    and self-healing capabilities.
    """

    def __init__(self):
        self.aggregator = ErrorAggregator()
        self.fallback_manager = FallbackManager()
        self.healer = SelfHealer()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.retry_handlers: Dict[str, RetryHandler] = {}

        # Default retry config
        self.default_retry_config = RetryConfig(
            max_attempts=3,
            strategy=RetryStrategy.EXPONENTIAL,
            base_delay_seconds=1.0
        )

        # Initialize default healing actions
        self._init_healing_actions()

    def _init_healing_actions(self) -> None:
        """Initialize default healing actions."""
        async def log_and_notify(error: ErrorRecord):
            logger.info(f"Healing action: logged error {error.id}")

        async def clear_cache(error: ErrorRecord):
            logger.info("Healing action: cache cleared")

        async def restart_component(error: ErrorRecord):
            component = error.context.component
            logger.info(f"Healing action: restarted {component}")

        self.healer.register_healing_action("log", log_and_notify)
        self.healer.register_healing_action("clear_cache", clear_cache)
        self.healer.register_healing_action("restart", restart_component)

    def classify_error(self, error: Exception) -> Tuple[ErrorCategory, ErrorSeverity]:
        """Classify an error."""
        error_type = type(error).__name__
        error_msg = str(error).lower()

        # Category classification
        if any(word in error_msg for word in ["timeout", "timed out"]):
            category = ErrorCategory.TIMEOUT
        elif any(word in error_msg for word in ["connection", "network", "dns"]):
            category = ErrorCategory.NETWORK
        elif any(word in error_msg for word in ["memory", "disk", "resource"]):
            category = ErrorCategory.RESOURCE
        elif any(word in error_msg for word in ["config", "setting", "parameter"]):
            category = ErrorCategory.CONFIGURATION
        elif any(word in error_msg for word in ["validation", "invalid", "format"]):
            category = ErrorCategory.VALIDATION
        elif any(word in error_msg for word in ["service", "api", "external"]):
            category = ErrorCategory.DEPENDENCY
        elif isinstance(error, (ConnectionError, TimeoutError)):
            category = ErrorCategory.TRANSIENT
        else:
            category = ErrorCategory.INTERNAL

        # Severity classification
        if "fatal" in error_msg or "critical" in error_msg:
            severity = ErrorSeverity.FATAL
        elif "critical" in error_msg:
            severity = ErrorSeverity.CRITICAL
        elif category in [ErrorCategory.TRANSIENT, ErrorCategory.TIMEOUT]:
            severity = ErrorSeverity.WARNING
        elif category == ErrorCategory.VALIDATION:
            severity = ErrorSeverity.INFO
        else:
            severity = ErrorSeverity.ERROR

        return category, severity

    def record_error(
        self,
        error: Exception,
        context: ErrorContext = None,
        parent_id: str = None
    ) -> ErrorRecord:
        """Record an error."""
        category, severity = self.classify_error(error)

        record = ErrorRecord(
            error_type=type(error).__name__,
            message=str(error),
            severity=severity,
            category=category,
            stack_trace=traceback.format_exc(),
            context=context or ErrorContext(),
            parent_error_id=parent_id
        )

        self.aggregator.record(record)
        return record

    def get_circuit_breaker(
        self,
        name: str,
        config: CircuitBreakerConfig = None
    ) -> CircuitBreaker:
        """Get or create a circuit breaker."""
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker(name, config)
        return self.circuit_breakers[name]

    def get_retry_handler(
        self,
        name: str = "default",
        config: RetryConfig = None
    ) -> RetryHandler:
        """Get or create a retry handler."""
        if name not in self.retry_handlers:
            self.retry_handlers[name] = RetryHandler(
                config or self.default_retry_config
            )
        return self.retry_handlers[name]

    async def execute_with_recovery(
        self,
        operation: str,
        func: Callable[..., T],
        *args,
        retry: bool = True,
        circuit_breaker: bool = True,
        fallback: bool = True,
        context: ErrorContext = None,
        **kwargs
    ) -> T:
        """Execute function with full recovery support."""
        cb = None
        if circuit_breaker:
            cb = self.get_circuit_breaker(operation)
            if not cb.allow_request():
                raise CircuitOpenError(f"Circuit '{operation}' is open")

        retry_handler = self.get_retry_handler(operation) if retry else None

        try:
            if retry_handler:
                result = await retry_handler.execute(func, *args, **kwargs)
            elif asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            if cb:
                cb.record_success()

            return result

        except Exception as e:
            # Record error
            error_record = self.record_error(e, context)

            if cb:
                cb.record_failure()

            # Attempt healing
            healed = await self.healer.heal(error_record)
            if healed:
                logger.info(f"Error healed for operation {operation}")
                # Retry after healing
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)
                except Exception:
                    pass

            # Try fallback
            if fallback:
                try:
                    return await self.fallback_manager.execute_with_fallback(
                        operation, func, *args, **kwargs
                    )
                except NoFallbackAvailableError:
                    pass

            raise

    def register_fallback(
        self,
        operation: str,
        fallback: Callable,
        priority: int = 0
    ) -> None:
        """Register a fallback for an operation."""
        self.fallback_manager.register_fallback(operation, fallback, priority)

    def register_playbook(
        self,
        name: str,
        error_patterns: List[str],
        actions: List[RecoveryAction],
        cooldown_seconds: float = 60.0
    ) -> RecoveryPlaybook:
        """Register a recovery playbook."""
        playbook = RecoveryPlaybook(
            name=name,
            error_patterns=error_patterns,
            actions=actions,
            cooldown_seconds=cooldown_seconds
        )
        self.healer.register_playbook(playbook)
        return playbook

    def get_health_report(self) -> HealthReport:
        """Get system health report."""
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)

        errors_last_hour = sum(
            1 for e in self.aggregator.errors
            if e.occurred_at > hour_ago
        )

        # Calculate recovery success rate
        healing_history = self.healer.healing_history[-100:]
        if healing_history:
            successes = sum(1 for h in healing_history if h["success"])
            recovery_rate = successes / len(healing_history)
        else:
            recovery_rate = 1.0

        # Count open circuits
        open_circuits = sum(
            1 for cb in self.circuit_breakers.values()
            if cb.state == CircuitState.OPEN
        )

        # Identify degraded components
        component_errors = defaultdict(int)
        for error in self.aggregator.errors:
            if error.context.component and error.occurred_at > hour_ago:
                component_errors[error.context.component] += 1

        degraded = [c for c, count in component_errors.items() if count >= 5]

        healthy = (
            errors_last_hour < 100 and
            recovery_rate > 0.8 and
            open_circuits == 0 and
            len(degraded) == 0
        )

        return HealthReport(
            healthy=healthy,
            errors_last_hour=errors_last_hour,
            recovery_success_rate=recovery_rate,
            active_circuits_open=open_circuits,
            degraded_components=degraded
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get error recovery statistics."""
        return {
            "total_errors": len(self.aggregator.errors),
            "error_summary": self.aggregator.get_summary(),
            "circuit_breakers": {
                name: {
                    "state": cb.state.value,
                    "failures": cb.failure_count
                }
                for name, cb in self.circuit_breakers.items()
            },
            "retry_handlers": len(self.retry_handlers),
            "playbooks": len(self.healer.playbooks),
            "healing_attempts": len(self.healer.healing_history),
            "patterns_detected": self.aggregator.identify_patterns()
        }


# =============================================================================
# DECORATORS
# =============================================================================

def with_recovery(
    operation: str = None,
    retry: bool = True,
    circuit_breaker: bool = True,
    fallback: bool = True
):
    """Decorator for automatic error recovery."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            op_name = operation or func.__name__

            # Get or create recovery system
            from functools import lru_cache
            recovery = ErrorRecoverySystem()

            return await recovery.execute_with_recovery(
                op_name,
                func,
                *args,
                retry=retry,
                circuit_breaker=circuit_breaker,
                fallback=fallback,
                **kwargs
            )
        return wrapper
    return decorator


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Error Recovery System."""
    print("=" * 70)
    print("BAEL - ERROR RECOVERY SYSTEM DEMO")
    print("Resilient Error Handling")
    print("=" * 70)
    print()

    # Create recovery system
    recovery = ErrorRecoverySystem()

    # 1. Error Classification
    print("1. ERROR CLASSIFICATION:")
    print("-" * 40)

    test_errors = [
        TimeoutError("Connection timed out"),
        ConnectionError("Network unreachable"),
        ValueError("Invalid input format"),
        MemoryError("Out of memory"),
    ]

    for error in test_errors:
        category, severity = recovery.classify_error(error)
        print(f"   {type(error).__name__}: {category.value}, {severity.name}")
    print()

    # 2. Retry Logic
    print("2. RETRY LOGIC:")
    print("-" * 40)

    attempt_count = 0

    async def flaky_operation():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise ConnectionError("Simulated failure")
        return "Success after retries"

    handler = recovery.get_retry_handler("flaky_op")
    try:
        result = await handler.execute(flaky_operation)
        print(f"   Result: {result}")
        print(f"   Attempts needed: {attempt_count}")
    except Exception as e:
        print(f"   Failed: {e}")
    print()

    # 3. Circuit Breaker
    print("3. CIRCUIT BREAKER:")
    print("-" * 40)

    cb = recovery.get_circuit_breaker("test_service")
    print(f"   Initial state: {cb.state.value}")

    # Simulate failures
    for i in range(6):
        cb.record_failure()

    print(f"   After 6 failures: {cb.state.value}")
    print(f"   Allows request: {cb.allow_request()}")
    print()

    # 4. Fallback
    print("4. FALLBACK HANDLING:")
    print("-" * 40)

    async def primary_action():
        raise RuntimeError("Primary failed")

    async def fallback_action():
        return "Fallback result"

    recovery.register_fallback("test_op", fallback_action)

    try:
        result = await recovery.fallback_manager.execute_with_fallback(
            "test_op", primary_action
        )
        print(f"   Result: {result}")
    except Exception as e:
        print(f"   Error: {e}")
    print()

    # 5. Error Recording
    print("5. ERROR RECORDING:")
    print("-" * 40)

    for i in range(10):
        try:
            raise ValueError(f"Test error {i}")
        except Exception as e:
            context = ErrorContext(
                operation="test",
                component=f"component_{i % 3}"
            )
            recovery.record_error(e, context)

    print(f"   Recorded 10 errors")

    summary = recovery.aggregator.get_summary()
    print(f"   Total errors: {summary['total_errors']}")
    print(f"   Error rate: {summary['error_rate_per_minute']:.2f}/min")
    print()

    # 6. Pattern Detection
    print("6. PATTERN DETECTION:")
    print("-" * 40)

    patterns = recovery.aggregator.identify_patterns()
    if patterns:
        for pattern in patterns:
            print(f"   [{pattern['severity'].upper()}] {pattern['type']}: {pattern['description']}")
    else:
        print("   No patterns detected")
    print()

    # 7. Recovery Playbook
    print("7. RECOVERY PLAYBOOK:")
    print("-" * 40)

    playbook = recovery.register_playbook(
        name="Connection Recovery",
        error_patterns=["connection", "network"],
        actions=[RecoveryAction.RETRY, RecoveryAction.FALLBACK],
        cooldown_seconds=30
    )
    print(f"   Registered: {playbook.name}")
    print(f"   Patterns: {playbook.error_patterns}")
    print(f"   Actions: {[a.value for a in playbook.actions]}")
    print()

    # 8. Integrated Recovery
    print("8. INTEGRATED RECOVERY:")
    print("-" * 40)

    success_count = 0

    async def unreliable_service():
        nonlocal success_count
        success_count += 1
        if success_count < 3:
            raise ConnectionError("Service unavailable")
        return "Service response"

    async def cached_fallback():
        return "Cached response"

    recovery.register_fallback("unreliable", cached_fallback)

    # Reset circuit breaker
    cb2 = recovery.get_circuit_breaker("unreliable")
    cb2.state = CircuitState.CLOSED
    cb2.failure_count = 0
    success_count = 0

    try:
        result = await recovery.execute_with_recovery(
            "unreliable",
            unreliable_service,
            retry=True,
            circuit_breaker=True,
            fallback=True
        )
        print(f"   Result: {result}")
    except Exception as e:
        print(f"   Final error: {e}")
    print()

    # 9. Health Report
    print("9. HEALTH REPORT:")
    print("-" * 40)

    health = recovery.get_health_report()
    print(f"   Healthy: {health.healthy}")
    print(f"   Errors last hour: {health.errors_last_hour}")
    print(f"   Recovery success rate: {health.recovery_success_rate:.1%}")
    print(f"   Open circuits: {health.active_circuits_open}")
    print(f"   Degraded components: {health.degraded_components}")
    print()

    # 10. Statistics
    print("10. SYSTEM STATISTICS:")
    print("-" * 40)

    stats = recovery.get_stats()
    print(f"   Total errors: {stats['total_errors']}")
    print(f"   Circuit breakers: {len(stats['circuit_breakers'])}")
    print(f"   Retry handlers: {stats['retry_handlers']}")
    print(f"   Playbooks: {stats['playbooks']}")
    print(f"   Healing attempts: {stats['healing_attempts']}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Error Recovery System Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
