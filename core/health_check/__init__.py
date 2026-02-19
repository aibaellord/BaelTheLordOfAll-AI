"""
BAEL Health Check Engine Implementation
=========================================

System health monitoring and reporting.

"Ba'el monitors the vital signs of all systems." — Ba'el
"""

import asyncio
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import uuid

logger = logging.getLogger("BAEL.HealthCheck")


# ============================================================================
# ENUMS
# ============================================================================

class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class CheckType(Enum):
    """Health check types."""
    LIVENESS = "liveness"     # Is the service alive?
    READINESS = "readiness"   # Is the service ready to serve?
    STARTUP = "startup"       # Has the service started?
    DEPENDENCY = "dependency" # Is dependency healthy?
    RESOURCE = "resource"     # Are resources within limits?


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class HealthCheck:
    """A health check definition."""
    id: str
    name: str
    check_type: CheckType

    # Check function
    check_fn: Optional[Callable[[], bool]] = None
    async_check_fn: Optional[Callable[[], bool]] = None

    # Configuration
    interval_seconds: float = 30.0
    timeout_seconds: float = 5.0
    failure_threshold: int = 3
    success_threshold: int = 1

    # State
    status: HealthStatus = HealthStatus.UNKNOWN
    last_check: Optional[datetime] = None
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None

    # Counters
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    total_checks: int = 0
    total_failures: int = 0

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'type': self.check_type.value,
            'status': self.status.value,
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'consecutive_failures': self.consecutive_failures,
            'metadata': self.metadata
        }


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    check_id: str
    success: bool
    status: HealthStatus
    message: Optional[str] = None
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthReport:
    """Overall health report."""
    status: HealthStatus
    checks: Dict[str, HealthCheckResult]
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': self.status.value,
            'checks': {
                k: {
                    'success': v.success,
                    'status': v.status.value,
                    'message': v.message,
                    'duration_ms': v.duration_ms
                }
                for k, v in self.checks.items()
            },
            'timestamp': self.timestamp.isoformat(),
            'duration_ms': self.duration_ms
        }


@dataclass
class HealthCheckConfig:
    """Health check engine configuration."""
    enabled: bool = True
    default_interval_seconds: float = 30.0
    default_timeout_seconds: float = 5.0
    parallel_checks: bool = True


# ============================================================================
# HEALTH CHECK ENGINE
# ============================================================================

class HealthCheckEngine:
    """
    Health check monitoring engine.

    Features:
    - Multiple check types
    - Configurable thresholds
    - Parallel execution
    - Status aggregation

    "Ba'el ensures all systems function perfectly." — Ba'el
    """

    def __init__(self, config: Optional[HealthCheckConfig] = None):
        """Initialize health check engine."""
        self.config = config or HealthCheckConfig()

        # Checks
        self._checks: Dict[str, HealthCheck] = {}

        # Background task
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # Callbacks
        self._on_status_change: Optional[Callable] = None
        self._on_unhealthy: Optional[Callable] = None

        # Thread safety
        self._lock = threading.RLock()

        # Stats
        self._stats = {
            'total_checks_run': 0,
            'total_failures': 0
        }

        logger.info("Health check engine initialized")

    # ========================================================================
    # CHECK REGISTRATION
    # ========================================================================

    def register(
        self,
        name: str,
        check_fn: Optional[Callable[[], bool]] = None,
        async_check_fn: Optional[Callable[[], bool]] = None,
        check_type: CheckType = CheckType.LIVENESS,
        interval: Optional[float] = None,
        timeout: Optional[float] = None,
        failure_threshold: int = 3,
        success_threshold: int = 1,
        check_id: Optional[str] = None
    ) -> HealthCheck:
        """
        Register a health check.

        Args:
            name: Check name
            check_fn: Sync check function
            async_check_fn: Async check function
            check_type: Type of check
            interval: Check interval
            timeout: Check timeout
            failure_threshold: Failures before unhealthy
            success_threshold: Successes before healthy
            check_id: Optional ID

        Returns:
            Registered health check
        """
        check = HealthCheck(
            id=check_id or str(uuid.uuid4()),
            name=name,
            check_type=check_type,
            check_fn=check_fn,
            async_check_fn=async_check_fn,
            interval_seconds=interval or self.config.default_interval_seconds,
            timeout_seconds=timeout or self.config.default_timeout_seconds,
            failure_threshold=failure_threshold,
            success_threshold=success_threshold
        )

        with self._lock:
            self._checks[check.id] = check

        logger.info(f"Health check registered: {name}")

        return check

    def register_dependency(
        self,
        name: str,
        check_fn: Callable[[], bool],
        critical: bool = True,
        **kwargs
    ) -> HealthCheck:
        """Register a dependency health check."""
        check = self.register(
            name=name,
            check_fn=check_fn,
            check_type=CheckType.DEPENDENCY,
            **kwargs
        )
        check.metadata['critical'] = critical
        return check

    def register_resource(
        self,
        name: str,
        check_fn: Callable[[], bool],
        threshold_warning: float = 0.7,
        threshold_critical: float = 0.9,
        **kwargs
    ) -> HealthCheck:
        """Register a resource health check."""
        check = self.register(
            name=name,
            check_fn=check_fn,
            check_type=CheckType.RESOURCE,
            **kwargs
        )
        check.metadata['threshold_warning'] = threshold_warning
        check.metadata['threshold_critical'] = threshold_critical
        return check

    def unregister(self, check_id: str) -> bool:
        """Unregister a health check."""
        with self._lock:
            if check_id in self._checks:
                del self._checks[check_id]
                return True
        return False

    # ========================================================================
    # CHECK EXECUTION
    # ========================================================================

    async def run_check(
        self,
        check: HealthCheck
    ) -> HealthCheckResult:
        """
        Run a single health check.

        Args:
            check: Health check to run

        Returns:
            Check result
        """
        start_time = time.time()
        success = False
        message = None
        details = {}

        try:
            if check.async_check_fn:
                success = await asyncio.wait_for(
                    check.async_check_fn(),
                    timeout=check.timeout_seconds
                )
            elif check.check_fn:
                success = await asyncio.wait_for(
                    asyncio.to_thread(check.check_fn),
                    timeout=check.timeout_seconds
                )
            else:
                success = True
                message = "No check function defined"

        except asyncio.TimeoutError:
            success = False
            message = f"Check timed out after {check.timeout_seconds}s"

        except Exception as e:
            success = False
            message = str(e)

        duration_ms = (time.time() - start_time) * 1000

        # Update check state
        self._update_check_state(check, success)

        self._stats['total_checks_run'] += 1
        if not success:
            self._stats['total_failures'] += 1

        return HealthCheckResult(
            check_id=check.id,
            success=success,
            status=check.status,
            message=message,
            duration_ms=duration_ms,
            details=details
        )

    def _update_check_state(
        self,
        check: HealthCheck,
        success: bool
    ) -> None:
        """Update check state after execution."""
        now = datetime.now()
        check.last_check = now
        check.total_checks += 1

        previous_status = check.status

        if success:
            check.last_success = now
            check.consecutive_failures = 0
            check.consecutive_successes += 1

            if check.consecutive_successes >= check.success_threshold:
                check.status = HealthStatus.HEALTHY
        else:
            check.last_failure = now
            check.consecutive_successes = 0
            check.consecutive_failures += 1
            check.total_failures += 1

            if check.consecutive_failures >= check.failure_threshold:
                check.status = HealthStatus.UNHEALTHY
            elif check.consecutive_failures > 0:
                check.status = HealthStatus.DEGRADED

        # Trigger callbacks
        if check.status != previous_status:
            if self._on_status_change:
                asyncio.create_task(
                    self._call_handler(
                        self._on_status_change,
                        check,
                        previous_status
                    )
                )

            if check.status == HealthStatus.UNHEALTHY and self._on_unhealthy:
                asyncio.create_task(
                    self._call_handler(self._on_unhealthy, check)
                )

    async def _call_handler(
        self,
        handler: Callable,
        *args
    ) -> Any:
        """Call handler function."""
        if asyncio.iscoroutinefunction(handler):
            return await handler(*args)
        else:
            return await asyncio.to_thread(handler, *args)

    # ========================================================================
    # HEALTH REPORT
    # ========================================================================

    async def check_health(
        self,
        check_types: Optional[List[CheckType]] = None
    ) -> HealthReport:
        """
        Run all health checks and generate report.

        Args:
            check_types: Filter by check types

        Returns:
            Health report
        """
        start_time = time.time()

        # Filter checks
        checks = list(self._checks.values())
        if check_types:
            checks = [c for c in checks if c.check_type in check_types]

        # Run checks
        if self.config.parallel_checks:
            tasks = [self.run_check(check) for check in checks]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            results = []
            for check in checks:
                result = await self.run_check(check)
                results.append(result)

        # Build results dict
        check_results = {}
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                check_results[checks[i].id] = HealthCheckResult(
                    check_id=checks[i].id,
                    success=False,
                    status=HealthStatus.UNHEALTHY,
                    message=str(result)
                )
            else:
                check_results[result.check_id] = result

        # Determine overall status
        overall_status = self._aggregate_status(check_results)

        duration_ms = (time.time() - start_time) * 1000

        return HealthReport(
            status=overall_status,
            checks=check_results,
            duration_ms=duration_ms
        )

    def _aggregate_status(
        self,
        results: Dict[str, HealthCheckResult]
    ) -> HealthStatus:
        """Aggregate status from individual checks."""
        if not results:
            return HealthStatus.UNKNOWN

        statuses = [r.status for r in results.values()]

        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY

        if any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED

        if all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY

        return HealthStatus.UNKNOWN

    async def liveness(self) -> HealthReport:
        """Run liveness checks only."""
        return await self.check_health([CheckType.LIVENESS])

    async def readiness(self) -> HealthReport:
        """Run readiness checks only."""
        return await self.check_health([
            CheckType.READINESS,
            CheckType.DEPENDENCY
        ])

    # ========================================================================
    # BACKGROUND MONITORING
    # ========================================================================

    async def start(self) -> None:
        """Start background health monitoring."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())

        logger.info("Health monitoring started")

    async def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while self._running:
            now = time.time()

            for check in list(self._checks.values()):
                if check.last_check:
                    since_last = now - check.last_check.timestamp()
                    if since_last < check.interval_seconds:
                        continue

                asyncio.create_task(self.run_check(check))

            await asyncio.sleep(1)  # Check every second

    async def stop(self) -> None:
        """Stop background monitoring."""
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Health monitoring stopped")

    # ========================================================================
    # CALLBACKS
    # ========================================================================

    def on_status_change(
        self,
        callback: Callable[[HealthCheck, HealthStatus], None]
    ) -> None:
        """Set status change callback."""
        self._on_status_change = callback

    def on_unhealthy(
        self,
        callback: Callable[[HealthCheck], None]
    ) -> None:
        """Set unhealthy callback."""
        self._on_unhealthy = callback

    # ========================================================================
    # QUERIES
    # ========================================================================

    def get_check(self, check_id: str) -> Optional[HealthCheck]:
        """Get check by ID."""
        return self._checks.get(check_id)

    def get_checks_by_type(
        self,
        check_type: CheckType
    ) -> List[HealthCheck]:
        """Get checks by type."""
        return [
            c for c in self._checks.values()
            if c.check_type == check_type
        ]

    def get_unhealthy_checks(self) -> List[HealthCheck]:
        """Get all unhealthy checks."""
        return [
            c for c in self._checks.values()
            if c.status == HealthStatus.UNHEALTHY
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            'registered_checks': len(self._checks),
            'unhealthy_count': len(self.get_unhealthy_checks()),
            'running': self._running,
            **self._stats
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

health_engine: Optional[HealthCheckEngine] = None


def get_health_engine(
    config: Optional[HealthCheckConfig] = None
) -> HealthCheckEngine:
    """Get or create health engine."""
    global health_engine
    if health_engine is None:
        health_engine = HealthCheckEngine(config)
    return health_engine


def register_health_check(name: str, check_fn: Callable, **kwargs) -> HealthCheck:
    """Register a health check."""
    return get_health_engine().register(name, check_fn=check_fn, **kwargs)


async def check_health() -> HealthReport:
    """Run all health checks."""
    return await get_health_engine().check_health()
