"""
BAEL Self-Healing System
=========================

Autonomous error detection, diagnosis, and recovery.

"A system that heals itself is immortal." — Ba'el
"""

import asyncio
import logging
import traceback
import time
import re
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger("BAEL.SelfHealing")


class ErrorSeverity(Enum):
    """Error severity levels."""
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4
    FATAL = 5


class ErrorCategory(Enum):
    """Categories of errors."""
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    RESOURCE = "resource"
    CONFIGURATION = "configuration"
    DEPENDENCY = "dependency"
    TIMEOUT = "timeout"
    VALIDATION = "validation"
    PERMISSION = "permission"
    DATA = "data"
    UNKNOWN = "unknown"


class RecoveryAction(Enum):
    """Types of recovery actions."""
    RETRY = "retry"
    RETRY_WITH_BACKOFF = "retry_backoff"
    FALLBACK = "fallback"
    RESTART = "restart"
    RECONFIGURE = "reconfigure"
    SKIP = "skip"
    ESCALATE = "escalate"
    CACHE = "cache"
    THROTTLE = "throttle"


class HealthStatus(Enum):
    """System health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


@dataclass
class ErrorPattern:
    """Pattern for identifying specific errors."""
    pattern: str  # Regex pattern
    category: ErrorCategory
    severity: ErrorSeverity
    recovery_actions: List[RecoveryAction]
    max_retries: int = 3
    backoff_factor: float = 2.0
    description: str = ""


@dataclass
class ErrorOccurrence:
    """Record of an error occurrence."""
    error_id: str
    error_type: str
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    timestamp: datetime
    traceback: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    recovered: bool = False
    recovery_action: Optional[RecoveryAction] = None


@dataclass
class RecoveryResult:
    """Result of a recovery attempt."""
    success: bool
    action_taken: RecoveryAction
    attempts: int
    duration_seconds: float
    message: str = ""
    result: Any = None


@dataclass
class HealthReport:
    """System health report."""
    status: HealthStatus
    components: Dict[str, HealthStatus]
    error_rate: float
    recovery_rate: float
    uptime_seconds: float
    last_check: datetime
    recommendations: List[str]


# =============================================================================
# ERROR PATTERNS
# =============================================================================

DEFAULT_PATTERNS = [
    # Network errors
    ErrorPattern(
        pattern=r"(connection|network|socket|connect).*(error|refused|timeout|failed)",
        category=ErrorCategory.NETWORK,
        severity=ErrorSeverity.ERROR,
        recovery_actions=[RecoveryAction.RETRY_WITH_BACKOFF, RecoveryAction.FALLBACK],
        max_retries=3,
        description="Network connectivity issues",
    ),

    # Rate limiting
    ErrorPattern(
        pattern=r"(rate.?limit|too.?many.?requests|429|throttl)",
        category=ErrorCategory.RATE_LIMIT,
        severity=ErrorSeverity.WARNING,
        recovery_actions=[RecoveryAction.THROTTLE, RecoveryAction.RETRY_WITH_BACKOFF],
        max_retries=5,
        backoff_factor=3.0,
        description="API rate limiting",
    ),

    # Authentication
    ErrorPattern(
        pattern=r"(auth|unauthorized|401|403|forbidden|permission.?denied|invalid.?(token|key|credential))",
        category=ErrorCategory.AUTHENTICATION,
        severity=ErrorSeverity.CRITICAL,
        recovery_actions=[RecoveryAction.RECONFIGURE, RecoveryAction.ESCALATE],
        max_retries=1,
        description="Authentication/authorization failures",
    ),

    # Timeouts
    ErrorPattern(
        pattern=r"(timeout|timed?.?out|deadline.?exceeded)",
        category=ErrorCategory.TIMEOUT,
        severity=ErrorSeverity.ERROR,
        recovery_actions=[RecoveryAction.RETRY, RecoveryAction.FALLBACK],
        max_retries=2,
        description="Operation timeouts",
    ),

    # Resource exhaustion
    ErrorPattern(
        pattern=r"(memory|disk|space|quota|resource|out.?of|exhausted|insufficient)",
        category=ErrorCategory.RESOURCE,
        severity=ErrorSeverity.CRITICAL,
        recovery_actions=[RecoveryAction.CACHE, RecoveryAction.ESCALATE],
        max_retries=1,
        description="Resource exhaustion",
    ),

    # Configuration
    ErrorPattern(
        pattern=r"(config|setting|environment|variable|not.?found|missing|invalid.?configuration)",
        category=ErrorCategory.CONFIGURATION,
        severity=ErrorSeverity.ERROR,
        recovery_actions=[RecoveryAction.RECONFIGURE, RecoveryAction.FALLBACK],
        max_retries=1,
        description="Configuration issues",
    ),

    # Dependency issues
    ErrorPattern(
        pattern=r"(import|module|package|dependency|not.?installed|no.?module)",
        category=ErrorCategory.DEPENDENCY,
        severity=ErrorSeverity.CRITICAL,
        recovery_actions=[RecoveryAction.ESCALATE],
        max_retries=0,
        description="Missing dependencies",
    ),

    # Validation
    ErrorPattern(
        pattern=r"(invalid|validation|schema|format|type.?error|value.?error)",
        category=ErrorCategory.VALIDATION,
        severity=ErrorSeverity.WARNING,
        recovery_actions=[RecoveryAction.SKIP, RecoveryAction.FALLBACK],
        max_retries=1,
        description="Validation failures",
    ),
]


class SelfHealingSystem:
    """
    Autonomous self-healing system for BAEL.

    Features:
    - Automatic error detection and categorization
    - Pattern-based error recognition
    - Multi-strategy recovery
    - Learning from recovery outcomes
    - Health monitoring
    - Circuit breaker pattern
    """

    def __init__(self):
        self.patterns = DEFAULT_PATTERNS.copy()
        self._error_history: List[ErrorOccurrence] = []
        self._recovery_stats: Dict[ErrorCategory, Dict[str, int]] = defaultdict(lambda: {"attempts": 0, "successes": 0})
        self._circuit_breakers: Dict[str, Dict[str, Any]] = {}
        self._fallbacks: Dict[str, Callable] = {}
        self._start_time = datetime.now()

        # Component health tracking
        self._component_health: Dict[str, HealthStatus] = {}
        self._component_errors: Dict[str, List[datetime]] = defaultdict(list)

    def add_pattern(self, pattern: ErrorPattern) -> None:
        """Add a custom error pattern."""
        self.patterns.append(pattern)

    def register_fallback(self, key: str, fallback: Callable) -> None:
        """Register a fallback function for a specific key."""
        self._fallbacks[key] = fallback

    async def execute_with_healing(
        self,
        func: Callable,
        *args,
        fallback_key: str = None,
        component: str = "default",
        **kwargs,
    ) -> Any:
        """
        Execute function with automatic healing.

        Args:
            func: Function to execute
            *args: Positional arguments
            fallback_key: Key for registered fallback
            component: Component name for health tracking
            **kwargs: Keyword arguments

        Returns:
            Function result or fallback result
        """
        # Check circuit breaker
        if self._is_circuit_open(component):
            if fallback_key and fallback_key in self._fallbacks:
                return await self._execute_fallback(fallback_key, *args, **kwargs)
            raise Exception(f"Circuit breaker open for {component}")

        error_occurrence = None
        matched_pattern = None

        try:
            # Execute function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # Success - update health
            self._record_success(component)
            return result

        except Exception as e:
            # Categorize error
            error_occurrence, matched_pattern = self._categorize_error(e, component)
            self._error_history.append(error_occurrence)
            self._record_error(component)

            # Attempt recovery
            recovery_result = await self._attempt_recovery(
                func, args, kwargs, error_occurrence, matched_pattern, fallback_key
            )

            if recovery_result.success:
                error_occurrence.recovered = True
                error_occurrence.recovery_action = recovery_result.action_taken
                return recovery_result.result
            else:
                # Check if we should open circuit breaker
                self._check_circuit_breaker(component)
                raise

    def _categorize_error(
        self,
        error: Exception,
        component: str,
    ) -> Tuple[ErrorOccurrence, Optional[ErrorPattern]]:
        """Categorize an error based on patterns."""
        error_str = str(error).lower()
        error_type = type(error).__name__
        tb = traceback.format_exc()

        # Find matching pattern
        matched_pattern = None
        category = ErrorCategory.UNKNOWN
        severity = ErrorSeverity.ERROR

        for pattern in self.patterns:
            if re.search(pattern.pattern, error_str, re.IGNORECASE) or \
               re.search(pattern.pattern, tb, re.IGNORECASE):
                matched_pattern = pattern
                category = pattern.category
                severity = pattern.severity
                break

        # Create occurrence record
        occurrence = ErrorOccurrence(
            error_id=f"{component}_{int(time.time() * 1000)}",
            error_type=error_type,
            message=str(error),
            category=category,
            severity=severity,
            timestamp=datetime.now(),
            traceback=tb,
            context={"component": component},
        )

        logger.warning(f"Error categorized: {category.value} ({severity.value}) - {error_type}: {str(error)[:100]}")

        return occurrence, matched_pattern

    async def _attempt_recovery(
        self,
        func: Callable,
        args: tuple,
        kwargs: dict,
        error: ErrorOccurrence,
        pattern: Optional[ErrorPattern],
        fallback_key: str,
    ) -> RecoveryResult:
        """Attempt to recover from an error."""
        start_time = time.time()

        if pattern is None:
            # No pattern matched - use default retry
            return await self._retry_with_backoff(func, args, kwargs, max_retries=2)

        self._recovery_stats[error.category]["attempts"] += 1

        # Try recovery actions in order
        for action in pattern.recovery_actions:
            result = await self._execute_recovery_action(
                action, func, args, kwargs, pattern, fallback_key
            )

            if result.success:
                self._recovery_stats[error.category]["successes"] += 1
                result.duration_seconds = time.time() - start_time
                return result

        return RecoveryResult(
            success=False,
            action_taken=RecoveryAction.ESCALATE,
            attempts=pattern.max_retries,
            duration_seconds=time.time() - start_time,
            message="All recovery actions failed",
        )

    async def _execute_recovery_action(
        self,
        action: RecoveryAction,
        func: Callable,
        args: tuple,
        kwargs: dict,
        pattern: ErrorPattern,
        fallback_key: str,
    ) -> RecoveryResult:
        """Execute a specific recovery action."""

        if action == RecoveryAction.RETRY:
            return await self._simple_retry(func, args, kwargs, pattern.max_retries)

        elif action == RecoveryAction.RETRY_WITH_BACKOFF:
            return await self._retry_with_backoff(
                func, args, kwargs, pattern.max_retries, pattern.backoff_factor
            )

        elif action == RecoveryAction.FALLBACK:
            if fallback_key and fallback_key in self._fallbacks:
                try:
                    result = await self._execute_fallback(fallback_key, *args, **kwargs)
                    return RecoveryResult(
                        success=True,
                        action_taken=action,
                        attempts=1,
                        duration_seconds=0,
                        result=result,
                    )
                except Exception:
                    pass
            return RecoveryResult(success=False, action_taken=action, attempts=1, duration_seconds=0)

        elif action == RecoveryAction.THROTTLE:
            # Wait and retry
            await asyncio.sleep(5)
            return await self._simple_retry(func, args, kwargs, 1)

        elif action == RecoveryAction.SKIP:
            return RecoveryResult(
                success=True,
                action_taken=action,
                attempts=0,
                duration_seconds=0,
                result=None,
                message="Skipped",
            )

        elif action == RecoveryAction.CACHE:
            # Try to return cached result
            # This is a simplified version - in production, integrate with cache system
            return RecoveryResult(success=False, action_taken=action, attempts=0, duration_seconds=0)

        else:
            return RecoveryResult(success=False, action_taken=action, attempts=0, duration_seconds=0)

    async def _simple_retry(
        self,
        func: Callable,
        args: tuple,
        kwargs: dict,
        max_retries: int,
    ) -> RecoveryResult:
        """Simple retry without backoff."""
        for attempt in range(max_retries):
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                return RecoveryResult(
                    success=True,
                    action_taken=RecoveryAction.RETRY,
                    attempts=attempt + 1,
                    duration_seconds=0,
                    result=result,
                )
            except Exception:
                continue

        return RecoveryResult(
            success=False,
            action_taken=RecoveryAction.RETRY,
            attempts=max_retries,
            duration_seconds=0,
        )

    async def _retry_with_backoff(
        self,
        func: Callable,
        args: tuple,
        kwargs: dict,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
    ) -> RecoveryResult:
        """Retry with exponential backoff."""
        delay = 1.0

        for attempt in range(max_retries):
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                return RecoveryResult(
                    success=True,
                    action_taken=RecoveryAction.RETRY_WITH_BACKOFF,
                    attempts=attempt + 1,
                    duration_seconds=0,
                    result=result,
                )
            except Exception:
                if attempt < max_retries - 1:
                    await asyncio.sleep(delay)
                    delay *= backoff_factor

        return RecoveryResult(
            success=False,
            action_taken=RecoveryAction.RETRY_WITH_BACKOFF,
            attempts=max_retries,
            duration_seconds=0,
        )

    async def _execute_fallback(self, key: str, *args, **kwargs) -> Any:
        """Execute a registered fallback."""
        fallback = self._fallbacks[key]
        if asyncio.iscoroutinefunction(fallback):
            return await fallback(*args, **kwargs)
        return fallback(*args, **kwargs)

    def _is_circuit_open(self, component: str) -> bool:
        """Check if circuit breaker is open for component."""
        if component not in self._circuit_breakers:
            return False

        breaker = self._circuit_breakers[component]
        if breaker["state"] == "open":
            # Check if enough time has passed for half-open
            if time.time() - breaker["opened_at"] > breaker["timeout"]:
                breaker["state"] = "half-open"
                return False
            return True
        return False

    def _check_circuit_breaker(self, component: str) -> None:
        """Check if circuit breaker should be opened."""
        errors = self._component_errors[component]
        recent = [e for e in errors if e > datetime.now() - timedelta(minutes=1)]

        if len(recent) >= 5:  # 5 errors in 1 minute
            self._circuit_breakers[component] = {
                "state": "open",
                "opened_at": time.time(),
                "timeout": 30,  # 30 second timeout
                "error_count": len(recent),
            }
            logger.warning(f"Circuit breaker opened for {component}")

    def _record_success(self, component: str) -> None:
        """Record successful execution."""
        self._component_health[component] = HealthStatus.HEALTHY

        # Half-open circuit breaker → close it
        if component in self._circuit_breakers:
            if self._circuit_breakers[component]["state"] == "half-open":
                del self._circuit_breakers[component]
                logger.info(f"Circuit breaker closed for {component}")

    def _record_error(self, component: str) -> None:
        """Record error occurrence."""
        self._component_errors[component].append(datetime.now())

        # Keep only last hour of errors
        cutoff = datetime.now() - timedelta(hours=1)
        self._component_errors[component] = [
            e for e in self._component_errors[component] if e > cutoff
        ]

        # Update health status
        error_count = len(self._component_errors[component])
        if error_count >= 10:
            self._component_health[component] = HealthStatus.CRITICAL
        elif error_count >= 5:
            self._component_health[component] = HealthStatus.UNHEALTHY
        elif error_count >= 2:
            self._component_health[component] = HealthStatus.DEGRADED

    def get_health_report(self) -> HealthReport:
        """Get comprehensive health report."""
        # Calculate overall status
        component_statuses = list(self._component_health.values())
        if HealthStatus.CRITICAL in component_statuses:
            overall = HealthStatus.CRITICAL
        elif HealthStatus.UNHEALTHY in component_statuses:
            overall = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in component_statuses:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY

        # Calculate rates
        total_errors = len(self._error_history)
        recovered = sum(1 for e in self._error_history if e.recovered)
        recovery_rate = recovered / total_errors if total_errors > 0 else 1.0

        uptime = (datetime.now() - self._start_time).total_seconds()
        error_rate = total_errors / (uptime / 3600) if uptime > 0 else 0

        # Generate recommendations
        recommendations = []
        for category, stats in self._recovery_stats.items():
            if stats["attempts"] > 0:
                success_rate = stats["successes"] / stats["attempts"]
                if success_rate < 0.5:
                    recommendations.append(
                        f"High failure rate for {category.value} errors ({success_rate:.0%}). Consider adding fallbacks."
                    )

        for component, status in self._component_health.items():
            if status in (HealthStatus.UNHEALTHY, HealthStatus.CRITICAL):
                recommendations.append(f"Component '{component}' is {status.value}. Investigate errors.")

        return HealthReport(
            status=overall,
            components=self._component_health.copy(),
            error_rate=error_rate,
            recovery_rate=recovery_rate,
            uptime_seconds=uptime,
            last_check=datetime.now(),
            recommendations=recommendations,
        )

    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of errors."""
        by_category = defaultdict(int)
        by_severity = defaultdict(int)

        for error in self._error_history:
            by_category[error.category.value] += 1
            by_severity[error.severity.value] += 1

        return {
            "total_errors": len(self._error_history),
            "by_category": dict(by_category),
            "by_severity": dict(by_severity),
            "recovery_stats": {
                k.value: v for k, v in self._recovery_stats.items()
            },
            "circuit_breakers": {
                k: v["state"] for k, v in self._circuit_breakers.items()
            },
        }


# =============================================================================
# DECORATOR
# =============================================================================

_healing_system = SelfHealingSystem()


def self_healing(
    fallback_key: str = None,
    component: str = "default",
):
    """Decorator for self-healing execution."""
    def decorator(func: Callable) -> Callable:
        async def async_wrapper(*args, **kwargs):
            return await _healing_system.execute_with_healing(
                func, *args, fallback_key=fallback_key, component=component, **kwargs
            )

        def sync_wrapper(*args, **kwargs):
            return asyncio.run(_healing_system.execute_with_healing(
                func, *args, fallback_key=fallback_key, component=component, **kwargs
            ))

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def get_healing_system() -> SelfHealingSystem:
    """Get the global self-healing system."""
    return _healing_system
