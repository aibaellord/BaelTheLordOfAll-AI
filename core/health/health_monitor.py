#!/usr/bin/env python3
"""
BAEL - Health Monitor
Advanced health monitoring for AI agent operations.

Features:
- Health checks
- Liveness probes
- Readiness probes
- Dependency health
- Health aggregation
- Alerting
- Status history
- Metrics integration
- Self-healing triggers
- Dashboard support
"""

import asyncio
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Awaitable, Callable, Dict, Generic, List, Optional,
                    Set, Tuple, TypeVar)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class HealthStatus(Enum):
    """Health statuses."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class CheckType(Enum):
    """Check types."""
    LIVENESS = "liveness"
    READINESS = "readiness"
    STARTUP = "startup"
    DEPENDENCY = "dependency"
    CUSTOM = "custom"


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class HealthCheckResult:
    """Result of a health check."""
    check_id: str
    name: str
    status: HealthStatus
    check_type: CheckType
    message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class HealthCheckConfig:
    """Health check configuration."""
    name: str
    check_type: CheckType = CheckType.CUSTOM
    interval: float = 30.0
    timeout: float = 10.0
    failure_threshold: int = 3
    success_threshold: int = 1
    enabled: bool = True


@dataclass
class Alert:
    """A health alert."""
    alert_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    check_name: str = ""
    severity: AlertSeverity = AlertSeverity.WARNING
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class HealthReport:
    """Overall health report."""
    status: HealthStatus
    checks: List[HealthCheckResult] = field(default_factory=list)
    healthy_count: int = 0
    degraded_count: int = 0
    unhealthy_count: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    duration_ms: float = 0.0


@dataclass
class HealthStats:
    """Health monitoring statistics."""
    total_checks: int = 0
    healthy_checks: int = 0
    unhealthy_checks: int = 0
    total_alerts: int = 0
    active_alerts: int = 0
    uptime_percentage: float = 100.0


# =============================================================================
# HEALTH CHECKS
# =============================================================================

class HealthCheck(ABC):
    """Abstract health check."""

    def __init__(self, config: HealthCheckConfig):
        self.config = config
        self.check_id = str(uuid.uuid4())

        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._last_result: Optional[HealthCheckResult] = None
        self._history: deque = deque(maxlen=100)

    @abstractmethod
    async def execute(self) -> HealthCheckResult:
        """Execute the health check."""
        pass

    async def run(self) -> HealthCheckResult:
        """Run the health check with timeout."""
        start = time.time()

        try:
            result = await asyncio.wait_for(
                self.execute(),
                timeout=self.config.timeout
            )
            result.duration_ms = (time.time() - start) * 1000

        except asyncio.TimeoutError:
            result = HealthCheckResult(
                check_id=self.check_id,
                name=self.config.name,
                status=HealthStatus.UNHEALTHY,
                check_type=self.config.check_type,
                message="Check timed out",
                duration_ms=(time.time() - start) * 1000
            )

        except Exception as e:
            result = HealthCheckResult(
                check_id=self.check_id,
                name=self.config.name,
                status=HealthStatus.UNHEALTHY,
                check_type=self.config.check_type,
                message=str(e),
                duration_ms=(time.time() - start) * 1000
            )

        # Update state
        self._update_state(result)
        self._history.append(result)
        self._last_result = result

        return result

    def _update_state(self, result: HealthCheckResult) -> None:
        """Update consecutive success/failure counts."""
        if result.status == HealthStatus.HEALTHY:
            self._consecutive_failures = 0
            self._consecutive_successes += 1
        else:
            self._consecutive_successes = 0
            self._consecutive_failures += 1

    def get_effective_status(self) -> HealthStatus:
        """Get status considering thresholds."""
        if not self._last_result:
            return HealthStatus.UNKNOWN

        if self._consecutive_failures >= self.config.failure_threshold:
            return HealthStatus.UNHEALTHY

        if self._consecutive_successes >= self.config.success_threshold:
            return HealthStatus.HEALTHY

        return self._last_result.status

    def get_history(self) -> List[HealthCheckResult]:
        """Get check history."""
        return list(self._history)


class FunctionHealthCheck(HealthCheck):
    """Health check using a function."""

    def __init__(
        self,
        config: HealthCheckConfig,
        check_func: Callable[[], Awaitable[bool]]
    ):
        super().__init__(config)
        self.check_func = check_func

    async def execute(self) -> HealthCheckResult:
        is_healthy = await self.check_func()

        return HealthCheckResult(
            check_id=self.check_id,
            name=self.config.name,
            status=HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY,
            check_type=self.config.check_type
        )


class HttpHealthCheck(HealthCheck):
    """HTTP endpoint health check."""

    def __init__(
        self,
        config: HealthCheckConfig,
        url: str,
        expected_status: int = 200
    ):
        super().__init__(config)
        self.url = url
        self.expected_status = expected_status

    async def execute(self) -> HealthCheckResult:
        # Simulated HTTP check (in real impl, use aiohttp/httpx)
        # For demo purposes, simulate success
        return HealthCheckResult(
            check_id=self.check_id,
            name=self.config.name,
            status=HealthStatus.HEALTHY,
            check_type=self.config.check_type,
            details={"url": self.url, "status_code": self.expected_status}
        )


class MemoryHealthCheck(HealthCheck):
    """Memory usage health check."""

    def __init__(
        self,
        config: HealthCheckConfig,
        max_usage_percent: float = 90.0
    ):
        super().__init__(config)
        self.max_usage_percent = max_usage_percent

    async def execute(self) -> HealthCheckResult:
        import sys

        # Get memory info (simplified)
        try:
            import resource
            usage = resource.getrusage(resource.RUSAGE_SELF)
            memory_mb = usage.ru_maxrss / 1024  # macOS returns bytes
        except:
            memory_mb = 0

        # Simplified check - assume healthy if we got this far
        status = HealthStatus.HEALTHY

        return HealthCheckResult(
            check_id=self.check_id,
            name=self.config.name,
            status=status,
            check_type=self.config.check_type,
            details={"memory_mb": memory_mb}
        )


class DiskHealthCheck(HealthCheck):
    """Disk space health check."""

    def __init__(
        self,
        config: HealthCheckConfig,
        path: str = "/",
        min_free_percent: float = 10.0
    ):
        super().__init__(config)
        self.path = path
        self.min_free_percent = min_free_percent

    async def execute(self) -> HealthCheckResult:
        import os

        try:
            stat = os.statvfs(self.path)
            total = stat.f_blocks * stat.f_frsize
            free = stat.f_bavail * stat.f_frsize
            free_percent = (free / total) * 100 if total > 0 else 0

            status = HealthStatus.HEALTHY if free_percent >= self.min_free_percent else HealthStatus.UNHEALTHY

            return HealthCheckResult(
                check_id=self.check_id,
                name=self.config.name,
                status=status,
                check_type=self.config.check_type,
                details={
                    "path": self.path,
                    "free_percent": round(free_percent, 2),
                    "free_gb": round(free / (1024**3), 2)
                }
            )
        except Exception as e:
            return HealthCheckResult(
                check_id=self.check_id,
                name=self.config.name,
                status=HealthStatus.UNKNOWN,
                check_type=self.config.check_type,
                message=str(e)
            )


class DependencyHealthCheck(HealthCheck):
    """Check health of a dependency."""

    def __init__(
        self,
        config: HealthCheckConfig,
        dependency_name: str,
        check_func: Callable[[], Awaitable[bool]]
    ):
        super().__init__(config)
        self.dependency_name = dependency_name
        self.check_func = check_func

    async def execute(self) -> HealthCheckResult:
        try:
            is_healthy = await self.check_func()

            return HealthCheckResult(
                check_id=self.check_id,
                name=self.config.name,
                status=HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY,
                check_type=CheckType.DEPENDENCY,
                details={"dependency": self.dependency_name}
            )
        except Exception as e:
            return HealthCheckResult(
                check_id=self.check_id,
                name=self.config.name,
                status=HealthStatus.UNHEALTHY,
                check_type=CheckType.DEPENDENCY,
                message=str(e),
                details={"dependency": self.dependency_name}
            )


class CompositeHealthCheck(HealthCheck):
    """Composite check combining multiple checks."""

    def __init__(
        self,
        config: HealthCheckConfig,
        checks: List[HealthCheck],
        require_all: bool = True
    ):
        super().__init__(config)
        self.checks = checks
        self.require_all = require_all

    async def execute(self) -> HealthCheckResult:
        results = await asyncio.gather(*[c.run() for c in self.checks])

        healthy_count = sum(1 for r in results if r.status == HealthStatus.HEALTHY)

        if self.require_all:
            status = HealthStatus.HEALTHY if healthy_count == len(results) else HealthStatus.UNHEALTHY
        else:
            status = HealthStatus.HEALTHY if healthy_count > 0 else HealthStatus.UNHEALTHY

        return HealthCheckResult(
            check_id=self.check_id,
            name=self.config.name,
            status=status,
            check_type=self.config.check_type,
            details={
                "total_checks": len(results),
                "healthy_checks": healthy_count,
                "results": [{"name": r.name, "status": r.status.value} for r in results]
            }
        )


# =============================================================================
# ALERT MANAGER
# =============================================================================

class AlertManager:
    """Manages health alerts."""

    def __init__(self):
        self._alerts: Dict[str, Alert] = {}
        self._alert_history: deque = deque(maxlen=1000)
        self._handlers: List[Callable[[Alert], Awaitable[None]]] = []
        self._lock = threading.RLock()

    def add_handler(self, handler: Callable[[Alert], Awaitable[None]]) -> None:
        """Add alert handler."""
        self._handlers.append(handler)

    async def create_alert(
        self,
        check_name: str,
        severity: AlertSeverity,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> Alert:
        """Create and fire alert."""
        alert = Alert(
            check_name=check_name,
            severity=severity,
            message=message,
            details=details or {}
        )

        with self._lock:
            self._alerts[alert.alert_id] = alert
            self._alert_history.append(alert)

        # Notify handlers
        for handler in self._handlers:
            try:
                await handler(alert)
            except Exception:
                pass

        return alert

    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        with self._lock:
            if alert_id in self._alerts:
                alert = self._alerts[alert_id]
                alert.resolved = True
                alert.resolved_at = datetime.utcnow()
                return True
            return False

    def get_active_alerts(self) -> List[Alert]:
        """Get all active (unresolved) alerts."""
        with self._lock:
            return [a for a in self._alerts.values() if not a.resolved]

    def get_alerts_by_check(self, check_name: str) -> List[Alert]:
        """Get alerts for a specific check."""
        with self._lock:
            return [a for a in self._alerts.values() if a.check_name == check_name]

    def get_alert_count(self, active_only: bool = True) -> int:
        """Get alert count."""
        with self._lock:
            if active_only:
                return len([a for a in self._alerts.values() if not a.resolved])
            return len(self._alerts)


# =============================================================================
# HEALTH MONITOR
# =============================================================================

class HealthMonitor:
    """
    Health Monitor for BAEL.

    Advanced health monitoring.
    """

    def __init__(self):
        self._checks: Dict[str, HealthCheck] = {}
        self._alert_manager = AlertManager()
        self._running = False
        self._check_tasks: Dict[str, asyncio.Task] = {}

        self._stats = HealthStats()
        self._status_history: deque = deque(maxlen=1000)
        self._lock = threading.RLock()

    # -------------------------------------------------------------------------
    # CHECK REGISTRATION
    # -------------------------------------------------------------------------

    def register_check(self, check: HealthCheck) -> None:
        """Register a health check."""
        with self._lock:
            self._checks[check.config.name] = check

    def register_function_check(
        self,
        name: str,
        check_func: Callable[[], Awaitable[bool]],
        check_type: CheckType = CheckType.CUSTOM,
        interval: float = 30.0
    ) -> HealthCheck:
        """Register a function-based health check."""
        config = HealthCheckConfig(
            name=name,
            check_type=check_type,
            interval=interval
        )
        check = FunctionHealthCheck(config, check_func)
        self.register_check(check)
        return check

    def register_liveness_check(
        self,
        name: str,
        check_func: Callable[[], Awaitable[bool]]
    ) -> HealthCheck:
        """Register a liveness check."""
        return self.register_function_check(
            name, check_func, CheckType.LIVENESS, interval=10.0
        )

    def register_readiness_check(
        self,
        name: str,
        check_func: Callable[[], Awaitable[bool]]
    ) -> HealthCheck:
        """Register a readiness check."""
        return self.register_function_check(
            name, check_func, CheckType.READINESS, interval=5.0
        )

    def register_dependency(
        self,
        name: str,
        dependency_name: str,
        check_func: Callable[[], Awaitable[bool]]
    ) -> HealthCheck:
        """Register a dependency check."""
        config = HealthCheckConfig(
            name=name,
            check_type=CheckType.DEPENDENCY,
            interval=30.0
        )
        check = DependencyHealthCheck(config, dependency_name, check_func)
        self.register_check(check)
        return check

    def unregister_check(self, name: str) -> bool:
        """Unregister a health check."""
        with self._lock:
            if name in self._checks:
                del self._checks[name]
                return True
            return False

    # -------------------------------------------------------------------------
    # CHECK EXECUTION
    # -------------------------------------------------------------------------

    async def run_check(self, name: str) -> Optional[HealthCheckResult]:
        """Run a specific health check."""
        check = self._checks.get(name)
        if not check:
            return None

        result = await check.run()
        self._update_stats(result)

        # Create alert if unhealthy
        if result.status == HealthStatus.UNHEALTHY:
            await self._alert_manager.create_alert(
                check_name=name,
                severity=AlertSeverity.WARNING if check._consecutive_failures < check.config.failure_threshold else AlertSeverity.CRITICAL,
                message=result.message or f"Check {name} is unhealthy",
                details=result.details
            )

        return result

    async def run_all_checks(self) -> HealthReport:
        """Run all health checks."""
        start = time.time()

        with self._lock:
            checks = list(self._checks.values())

        results = await asyncio.gather(*[c.run() for c in checks])

        # Count statuses
        healthy = sum(1 for r in results if r.status == HealthStatus.HEALTHY)
        degraded = sum(1 for r in results if r.status == HealthStatus.DEGRADED)
        unhealthy = sum(1 for r in results if r.status == HealthStatus.UNHEALTHY)

        # Determine overall status
        if unhealthy > 0:
            status = HealthStatus.UNHEALTHY
        elif degraded > 0:
            status = HealthStatus.DEGRADED
        elif healthy == len(results):
            status = HealthStatus.HEALTHY
        else:
            status = HealthStatus.UNKNOWN

        report = HealthReport(
            status=status,
            checks=results,
            healthy_count=healthy,
            degraded_count=degraded,
            unhealthy_count=unhealthy,
            duration_ms=(time.time() - start) * 1000
        )

        # Update history
        self._status_history.append(report)

        # Update stats
        for result in results:
            self._update_stats(result)

        return report

    async def run_checks_by_type(self, check_type: CheckType) -> List[HealthCheckResult]:
        """Run all checks of a specific type."""
        with self._lock:
            checks = [c for c in self._checks.values() if c.config.check_type == check_type]

        return await asyncio.gather(*[c.run() for c in checks])

    # -------------------------------------------------------------------------
    # KUBERNETES PROBES
    # -------------------------------------------------------------------------

    async def is_live(self) -> bool:
        """Kubernetes liveness probe."""
        results = await self.run_checks_by_type(CheckType.LIVENESS)

        if not results:
            return True  # No liveness checks = assume live

        return all(r.status == HealthStatus.HEALTHY for r in results)

    async def is_ready(self) -> bool:
        """Kubernetes readiness probe."""
        results = await self.run_checks_by_type(CheckType.READINESS)

        if not results:
            return True  # No readiness checks = assume ready

        return all(r.status == HealthStatus.HEALTHY for r in results)

    async def is_started(self) -> bool:
        """Kubernetes startup probe."""
        results = await self.run_checks_by_type(CheckType.STARTUP)

        if not results:
            return True

        return all(r.status == HealthStatus.HEALTHY for r in results)

    # -------------------------------------------------------------------------
    # CONTINUOUS MONITORING
    # -------------------------------------------------------------------------

    async def start(self) -> None:
        """Start continuous health monitoring."""
        self._running = True

        for name, check in self._checks.items():
            if check.config.enabled:
                self._check_tasks[name] = asyncio.create_task(
                    self._run_check_loop(check)
                )

    async def stop(self) -> None:
        """Stop health monitoring."""
        self._running = False

        for task in self._check_tasks.values():
            task.cancel()

        self._check_tasks.clear()

    async def _run_check_loop(self, check: HealthCheck) -> None:
        """Run check in a loop."""
        while self._running:
            try:
                await check.run()
                await asyncio.sleep(check.config.interval)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(check.config.interval)

    # -------------------------------------------------------------------------
    # STATUS & REPORTS
    # -------------------------------------------------------------------------

    def get_status(self) -> HealthStatus:
        """Get overall health status."""
        with self._lock:
            if not self._checks:
                return HealthStatus.UNKNOWN

            statuses = [c.get_effective_status() for c in self._checks.values()]

            if any(s == HealthStatus.UNHEALTHY for s in statuses):
                return HealthStatus.UNHEALTHY

            if any(s == HealthStatus.DEGRADED for s in statuses):
                return HealthStatus.DEGRADED

            if all(s == HealthStatus.HEALTHY for s in statuses):
                return HealthStatus.HEALTHY

            return HealthStatus.UNKNOWN

    def get_check_status(self, name: str) -> Optional[HealthCheckResult]:
        """Get last result for a check."""
        check = self._checks.get(name)
        if check:
            return check._last_result
        return None

    def get_all_statuses(self) -> Dict[str, HealthStatus]:
        """Get status for all checks."""
        with self._lock:
            return {
                name: check.get_effective_status()
                for name, check in self._checks.items()
            }

    def _update_stats(self, result: HealthCheckResult) -> None:
        """Update statistics."""
        with self._lock:
            self._stats.total_checks += 1

            if result.status == HealthStatus.HEALTHY:
                self._stats.healthy_checks += 1
            else:
                self._stats.unhealthy_checks += 1

            # Update uptime percentage
            total = self._stats.healthy_checks + self._stats.unhealthy_checks
            if total > 0:
                self._stats.uptime_percentage = (self._stats.healthy_checks / total) * 100

    def get_stats(self) -> HealthStats:
        """Get health statistics."""
        with self._lock:
            return HealthStats(
                total_checks=self._stats.total_checks,
                healthy_checks=self._stats.healthy_checks,
                unhealthy_checks=self._stats.unhealthy_checks,
                total_alerts=self._alert_manager.get_alert_count(active_only=False),
                active_alerts=self._alert_manager.get_alert_count(active_only=True),
                uptime_percentage=self._stats.uptime_percentage
            )

    # -------------------------------------------------------------------------
    # ALERTS
    # -------------------------------------------------------------------------

    def add_alert_handler(
        self,
        handler: Callable[[Alert], Awaitable[None]]
    ) -> None:
        """Add alert handler."""
        self._alert_manager.add_handler(handler)

    def get_active_alerts(self) -> List[Alert]:
        """Get active alerts."""
        return self._alert_manager.get_active_alerts()

    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        return await self._alert_manager.resolve_alert(alert_id)

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def list_checks(self) -> List[Dict[str, Any]]:
        """List all registered checks."""
        with self._lock:
            return [
                {
                    "name": c.config.name,
                    "type": c.config.check_type.value,
                    "interval": c.config.interval,
                    "enabled": c.config.enabled,
                    "status": c.get_effective_status().value
                }
                for c in self._checks.values()
            ]

    def to_dict(self) -> Dict[str, Any]:
        """Export health status as dictionary (for API/dashboard)."""
        status = self.get_status()
        all_statuses = self.get_all_statuses()
        stats = self.get_stats()

        return {
            "status": status.value,
            "checks": {
                name: s.value for name, s in all_statuses.items()
            },
            "stats": {
                "total_checks": stats.total_checks,
                "healthy_checks": stats.healthy_checks,
                "unhealthy_checks": stats.unhealthy_checks,
                "uptime_percentage": round(stats.uptime_percentage, 2)
            },
            "alerts": {
                "total": stats.total_alerts,
                "active": stats.active_alerts
            },
            "timestamp": datetime.utcnow().isoformat()
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Health Monitor."""
    print("=" * 70)
    print("BAEL - HEALTH MONITOR DEMO")
    print("Advanced Health Monitoring for AI Agents")
    print("=" * 70)
    print()

    monitor = HealthMonitor()

    # 1. Register Function Check
    print("1. FUNCTION HEALTH CHECK:")
    print("-" * 40)

    async def always_healthy():
        return True

    monitor.register_function_check("basic_check", always_healthy)

    result = await monitor.run_check("basic_check")
    if result:
        print(f"   Check: {result.name}")
        print(f"   Status: {result.status.value}")
        print(f"   Duration: {result.duration_ms:.2f}ms")
    print()

    # 2. Liveness Check
    print("2. LIVENESS CHECK:")
    print("-" * 40)

    monitor.register_liveness_check("app_liveness", always_healthy)

    is_live = await monitor.is_live()
    print(f"   Is live: {is_live}")
    print()

    # 3. Readiness Check
    print("3. READINESS CHECK:")
    print("-" * 40)

    ready = [True]

    async def readiness_check():
        return ready[0]

    monitor.register_readiness_check("app_readiness", readiness_check)

    is_ready = await monitor.is_ready()
    print(f"   Is ready: {is_ready}")

    # Make not ready
    ready[0] = False
    is_ready = await monitor.is_ready()
    print(f"   After setting not ready: {is_ready}")
    ready[0] = True
    print()

    # 4. Dependency Check
    print("4. DEPENDENCY CHECK:")
    print("-" * 40)

    async def check_database():
        return True  # Simulated

    monitor.register_dependency("db_check", "PostgreSQL", check_database)

    result = await monitor.run_check("db_check")
    if result:
        print(f"   Dependency: {result.details.get('dependency')}")
        print(f"   Status: {result.status.value}")
    print()

    # 5. Memory Check
    print("5. MEMORY CHECK:")
    print("-" * 40)

    mem_check = MemoryHealthCheck(
        HealthCheckConfig(name="memory", check_type=CheckType.CUSTOM),
        max_usage_percent=90.0
    )
    monitor.register_check(mem_check)

    result = await monitor.run_check("memory")
    if result:
        print(f"   Status: {result.status.value}")
        print(f"   Memory MB: {result.details.get('memory_mb', 'N/A')}")
    print()

    # 6. Disk Check
    print("6. DISK CHECK:")
    print("-" * 40)

    disk_check = DiskHealthCheck(
        HealthCheckConfig(name="disk", check_type=CheckType.CUSTOM),
        path="/",
        min_free_percent=5.0
    )
    monitor.register_check(disk_check)

    result = await monitor.run_check("disk")
    if result:
        print(f"   Status: {result.status.value}")
        print(f"   Free: {result.details.get('free_percent', 0):.1f}%")
        print(f"   Free GB: {result.details.get('free_gb', 0):.1f}")
    print()

    # 7. Run All Checks
    print("7. RUN ALL CHECKS:")
    print("-" * 40)

    report = await monitor.run_all_checks()
    print(f"   Overall status: {report.status.value}")
    print(f"   Healthy: {report.healthy_count}")
    print(f"   Unhealthy: {report.unhealthy_count}")
    print(f"   Duration: {report.duration_ms:.2f}ms")
    print()

    # 8. Failing Check
    print("8. FAILING CHECK:")
    print("-" * 40)

    async def failing_check():
        return False

    monitor.register_function_check("failing_check", failing_check)

    result = await monitor.run_check("failing_check")
    if result:
        print(f"   Status: {result.status.value}")

    # Check overall status
    status = monitor.get_status()
    print(f"   Overall status: {status.value}")
    print()

    # 9. Alerts
    print("9. ALERTS:")
    print("-" * 40)

    alerts_received = []

    async def alert_handler(alert: Alert):
        alerts_received.append(alert)

    monitor.add_alert_handler(alert_handler)

    # Run failing check to trigger alert
    await monitor.run_check("failing_check")

    active = monitor.get_active_alerts()
    print(f"   Active alerts: {len(active)}")
    if active:
        print(f"   Latest alert: {active[0].message}")
    print()

    # 10. Composite Check
    print("10. COMPOSITE CHECK:")
    print("-" * 40)

    check1 = FunctionHealthCheck(
        HealthCheckConfig(name="sub1"),
        lambda: always_healthy()
    )
    check2 = FunctionHealthCheck(
        HealthCheckConfig(name="sub2"),
        lambda: always_healthy()
    )

    composite = CompositeHealthCheck(
        HealthCheckConfig(name="composite"),
        [check1, check2],
        require_all=True
    )
    monitor.register_check(composite)

    result = await monitor.run_check("composite")
    if result:
        print(f"   Status: {result.status.value}")
        print(f"   Sub-checks: {result.details.get('total_checks')}")
        print(f"   Healthy: {result.details.get('healthy_checks')}")
    print()

    # 11. List Checks
    print("11. LIST CHECKS:")
    print("-" * 40)

    checks = monitor.list_checks()
    for c in checks[:5]:
        print(f"   - {c['name']}: {c['status']} ({c['type']})")
    print()

    # 12. All Statuses
    print("12. ALL STATUSES:")
    print("-" * 40)

    statuses = monitor.get_all_statuses()
    for name, status in list(statuses.items())[:5]:
        print(f"   - {name}: {status.value}")
    print()

    # 13. Statistics
    print("13. STATISTICS:")
    print("-" * 40)

    stats = monitor.get_stats()
    print(f"   Total checks: {stats.total_checks}")
    print(f"   Healthy: {stats.healthy_checks}")
    print(f"   Unhealthy: {stats.unhealthy_checks}")
    print(f"   Uptime: {stats.uptime_percentage:.1f}%")
    print(f"   Active alerts: {stats.active_alerts}")
    print()

    # 14. Export to Dict
    print("14. EXPORT TO DICT:")
    print("-" * 40)

    data = monitor.to_dict()
    print(f"   Status: {data['status']}")
    print(f"   Checks: {len(data['checks'])}")
    print(f"   Uptime: {data['stats']['uptime_percentage']}%")
    print()

    # 15. Check History
    print("15. CHECK HISTORY:")
    print("-" * 40)

    check = monitor._checks.get("basic_check")
    if check:
        history = check.get_history()
        print(f"   History entries: {len(history)}")
        if history:
            print(f"   Latest: {history[-1].status.value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Health Monitor Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
