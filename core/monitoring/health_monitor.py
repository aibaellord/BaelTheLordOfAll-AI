#!/usr/bin/env python3
"""
BAEL - Agent Health Monitor
Comprehensive health monitoring and alerting.

Features:
- Health checks for all components
- Liveness and readiness probes
- Automatic recovery actions
- Alert management
- Status dashboard data
"""

import asyncio
import logging
import platform
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# TYPES
# =============================================================================

class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ComponentType(Enum):
    """Types of monitored components."""
    CORE = "core"
    API = "api"
    DATABASE = "database"
    CACHE = "cache"
    LLM = "llm"
    MEMORY = "memory"
    TOOL = "tool"
    EXTERNAL = "external"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    component: str
    status: HealthStatus
    message: str = ""
    latency_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component": self.component,
            "status": self.status.value,
            "message": self.message,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class Alert:
    """Health alert."""
    id: str
    component: str
    severity: AlertSeverity
    title: str
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "component": self.component,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "metadata": self.metadata
        }


@dataclass
class ComponentHealth:
    """Health status of a component."""
    name: str
    type: ComponentType
    status: HealthStatus
    last_check: Optional[datetime] = None
    consecutive_failures: int = 0
    uptime_percent: float = 100.0
    check_history: List[HealthCheckResult] = field(default_factory=list)


# =============================================================================
# HEALTH CHECKS
# =============================================================================

class HealthCheck(ABC):
    """Abstract health check."""

    def __init__(self, name: str, component_type: ComponentType):
        self.name = name
        self.component_type = component_type
        self.timeout: float = 10.0

    @abstractmethod
    async def check(self) -> HealthCheckResult:
        """Run health check."""
        pass


class PingCheck(HealthCheck):
    """Simple ping/pong check."""

    def __init__(self, name: str, ping_func: Callable):
        super().__init__(name, ComponentType.CORE)
        self.ping_func = ping_func

    async def check(self) -> HealthCheckResult:
        start = time.perf_counter()
        try:
            if asyncio.iscoroutinefunction(self.ping_func):
                result = await asyncio.wait_for(self.ping_func(), self.timeout)
            else:
                result = self.ping_func()

            latency = (time.perf_counter() - start) * 1000

            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY,
                message="Ping successful" if result else "Ping failed",
                latency_ms=latency
            )
        except asyncio.TimeoutError:
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message="Health check timed out",
                latency_ms=self.timeout * 1000
            )
        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                latency_ms=(time.perf_counter() - start) * 1000
            )


class HTTPCheck(HealthCheck):
    """HTTP endpoint health check."""

    def __init__(
        self,
        name: str,
        url: str,
        expected_status: int = 200
    ):
        super().__init__(name, ComponentType.API)
        self.url = url
        self.expected_status = expected_status

    async def check(self) -> HealthCheckResult:
        import httpx

        start = time.perf_counter()
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.url, timeout=self.timeout)

            latency = (time.perf_counter() - start) * 1000

            if response.status_code == self.expected_status:
                return HealthCheckResult(
                    component=self.name,
                    status=HealthStatus.HEALTHY,
                    message=f"HTTP {response.status_code}",
                    latency_ms=latency,
                    metadata={"url": self.url}
                )
            else:
                return HealthCheckResult(
                    component=self.name,
                    status=HealthStatus.DEGRADED,
                    message=f"Expected {self.expected_status}, got {response.status_code}",
                    latency_ms=latency,
                    metadata={"url": self.url}
                )
        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                latency_ms=(time.perf_counter() - start) * 1000,
                metadata={"url": self.url}
            )


class DatabaseCheck(HealthCheck):
    """Database connectivity check."""

    def __init__(self, name: str, query_func: Callable):
        super().__init__(name, ComponentType.DATABASE)
        self.query_func = query_func

    async def check(self) -> HealthCheckResult:
        start = time.perf_counter()
        try:
            if asyncio.iscoroutinefunction(self.query_func):
                await asyncio.wait_for(self.query_func(), self.timeout)
            else:
                self.query_func()

            latency = (time.perf_counter() - start) * 1000

            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.HEALTHY,
                message="Database query successful",
                latency_ms=latency
            )
        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                latency_ms=(time.perf_counter() - start) * 1000
            )


class MemoryCheck(HealthCheck):
    """Memory usage check."""

    def __init__(
        self,
        name: str = "memory",
        warning_threshold: float = 0.8,
        critical_threshold: float = 0.95
    ):
        super().__init__(name, ComponentType.CORE)
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold

    async def check(self) -> HealthCheckResult:
        try:
            import psutil
            memory = psutil.virtual_memory()

            usage_percent = memory.percent / 100

            if usage_percent >= self.critical_threshold:
                status = HealthStatus.UNHEALTHY
                message = f"Critical memory usage: {memory.percent}%"
            elif usage_percent >= self.warning_threshold:
                status = HealthStatus.DEGRADED
                message = f"High memory usage: {memory.percent}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Memory usage: {memory.percent}%"

            return HealthCheckResult(
                component=self.name,
                status=status,
                message=message,
                metadata={
                    "total_mb": memory.total / (1024 * 1024),
                    "available_mb": memory.available / (1024 * 1024),
                    "percent": memory.percent
                }
            )
        except ImportError:
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNKNOWN,
                message="psutil not available"
            )


class DiskCheck(HealthCheck):
    """Disk space check."""

    def __init__(
        self,
        name: str = "disk",
        path: str = "/",
        warning_threshold: float = 0.8,
        critical_threshold: float = 0.95
    ):
        super().__init__(name, ComponentType.CORE)
        self.path = path
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold

    async def check(self) -> HealthCheckResult:
        try:
            import psutil
            disk = psutil.disk_usage(self.path)

            usage_percent = disk.percent / 100

            if usage_percent >= self.critical_threshold:
                status = HealthStatus.UNHEALTHY
                message = f"Critical disk usage: {disk.percent}%"
            elif usage_percent >= self.warning_threshold:
                status = HealthStatus.DEGRADED
                message = f"High disk usage: {disk.percent}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Disk usage: {disk.percent}%"

            return HealthCheckResult(
                component=self.name,
                status=status,
                message=message,
                metadata={
                    "total_gb": disk.total / (1024 ** 3),
                    "free_gb": disk.free / (1024 ** 3),
                    "percent": disk.percent
                }
            )
        except ImportError:
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNKNOWN,
                message="psutil not available"
            )


class LLMCheck(HealthCheck):
    """LLM provider health check."""

    def __init__(self, name: str, provider_func: Callable):
        super().__init__(name, ComponentType.LLM)
        self.provider_func = provider_func
        self.timeout = 30.0  # LLM calls can be slow

    async def check(self) -> HealthCheckResult:
        start = time.perf_counter()
        try:
            if asyncio.iscoroutinefunction(self.provider_func):
                response = await asyncio.wait_for(self.provider_func(), self.timeout)
            else:
                response = self.provider_func()

            latency = (time.perf_counter() - start) * 1000

            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.HEALTHY if response else HealthStatus.DEGRADED,
                message="LLM responding" if response else "LLM returned empty response",
                latency_ms=latency
            )
        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                latency_ms=(time.perf_counter() - start) * 1000
            )


# =============================================================================
# HEALTH MONITOR
# =============================================================================

class HealthMonitor:
    """Monitor system health."""

    def __init__(
        self,
        check_interval: float = 30.0,
        max_history: int = 100
    ):
        self.check_interval = check_interval
        self.max_history = max_history

        self.checks: Dict[str, HealthCheck] = {}
        self.components: Dict[str, ComponentHealth] = {}
        self.alerts: List[Alert] = []

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._alert_handlers: List[Callable] = []
        self._recovery_handlers: Dict[str, Callable] = {}

    def register_check(self, check: HealthCheck) -> None:
        """Register a health check."""
        self.checks[check.name] = check
        self.components[check.name] = ComponentHealth(
            name=check.name,
            type=check.component_type,
            status=HealthStatus.UNKNOWN
        )
        logger.info(f"Registered health check: {check.name}")

    def register_alert_handler(self, handler: Callable[[Alert], None]) -> None:
        """Register alert notification handler."""
        self._alert_handlers.append(handler)

    def register_recovery_action(
        self,
        component: str,
        action: Callable
    ) -> None:
        """Register automatic recovery action."""
        self._recovery_handlers[component] = action

    async def start(self) -> None:
        """Start health monitoring."""
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("Health monitor started")

    async def stop(self) -> None:
        """Stop health monitoring."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Health monitor stopped")

    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                await self.run_all_checks()
            except Exception as e:
                logger.error(f"Health check error: {e}")

            await asyncio.sleep(self.check_interval)

    async def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all health checks."""
        results = {}

        # Run checks concurrently
        check_tasks = {
            name: check.check()
            for name, check in self.checks.items()
        }

        for name, task in check_tasks.items():
            try:
                result = await task
                results[name] = result
                await self._process_result(name, result)
            except Exception as e:
                logger.error(f"Check {name} failed: {e}")
                results[name] = HealthCheckResult(
                    component=name,
                    status=HealthStatus.UNKNOWN,
                    message=str(e)
                )

        return results

    async def run_check(self, name: str) -> Optional[HealthCheckResult]:
        """Run specific health check."""
        if name not in self.checks:
            return None

        result = await self.checks[name].check()
        await self._process_result(name, result)
        return result

    async def _process_result(
        self,
        name: str,
        result: HealthCheckResult
    ) -> None:
        """Process health check result."""
        component = self.components[name]

        # Update history
        component.check_history.append(result)
        if len(component.check_history) > self.max_history:
            component.check_history = component.check_history[-self.max_history:]

        # Calculate uptime
        healthy_count = sum(
            1 for r in component.check_history
            if r.status == HealthStatus.HEALTHY
        )
        component.uptime_percent = (healthy_count / len(component.check_history)) * 100

        # Track failures
        if result.status in (HealthStatus.UNHEALTHY, HealthStatus.DEGRADED):
            component.consecutive_failures += 1
        else:
            component.consecutive_failures = 0

        # Update status
        previous_status = component.status
        component.status = result.status
        component.last_check = result.timestamp

        # Create alerts
        if result.status == HealthStatus.UNHEALTHY:
            await self._create_alert(
                component=name,
                severity=AlertSeverity.ERROR,
                title=f"{name} is unhealthy",
                message=result.message
            )

            # Trigger recovery if available
            if name in self._recovery_handlers:
                try:
                    recovery = self._recovery_handlers[name]
                    if asyncio.iscoroutinefunction(recovery):
                        await recovery()
                    else:
                        recovery()
                    logger.info(f"Recovery action executed for {name}")
                except Exception as e:
                    logger.error(f"Recovery failed for {name}: {e}")

        elif result.status == HealthStatus.DEGRADED:
            await self._create_alert(
                component=name,
                severity=AlertSeverity.WARNING,
                title=f"{name} is degraded",
                message=result.message
            )

        # Resolve alerts when healthy again
        if previous_status != HealthStatus.HEALTHY and result.status == HealthStatus.HEALTHY:
            await self._resolve_alerts(name)

    async def _create_alert(
        self,
        component: str,
        severity: AlertSeverity,
        title: str,
        message: str
    ) -> Alert:
        """Create and dispatch alert."""
        # Check for existing unresolved alert
        for alert in self.alerts:
            if not alert.resolved and alert.component == component and alert.title == title:
                return alert

        alert = Alert(
            id=str(uuid4()),
            component=component,
            severity=severity,
            title=title,
            message=message
        )

        self.alerts.append(alert)

        # Notify handlers
        for handler in self._alert_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                logger.error(f"Alert handler error: {e}")

        return alert

    async def _resolve_alerts(self, component: str) -> None:
        """Resolve all alerts for a component."""
        for alert in self.alerts:
            if not alert.resolved and alert.component == component:
                alert.resolved = True
                alert.resolved_at = datetime.now()
                logger.info(f"Resolved alert: {alert.title}")

    def get_status(self) -> Dict[str, Any]:
        """Get overall health status."""
        statuses = [c.status for c in self.components.values()]

        if all(s == HealthStatus.HEALTHY for s in statuses):
            overall = HealthStatus.HEALTHY
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            overall = HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.UNKNOWN

        return {
            "status": overall.value,
            "components": {
                name: {
                    "status": c.status.value,
                    "type": c.type.value,
                    "last_check": c.last_check.isoformat() if c.last_check else None,
                    "consecutive_failures": c.consecutive_failures,
                    "uptime_percent": c.uptime_percent
                }
                for name, c in self.components.items()
            },
            "active_alerts": len([a for a in self.alerts if not a.resolved]),
            "timestamp": datetime.now().isoformat()
        }

    def get_liveness(self) -> Dict[str, Any]:
        """Kubernetes liveness probe."""
        return {
            "status": "ok",
            "timestamp": datetime.now().isoformat()
        }

    def get_readiness(self) -> Dict[str, Any]:
        """Kubernetes readiness probe."""
        critical_components = [
            c for c in self.components.values()
            if c.type in (ComponentType.CORE, ComponentType.DATABASE, ComponentType.LLM)
        ]

        all_ready = all(
            c.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)
            for c in critical_components
        )

        return {
            "ready": all_ready,
            "components": {
                c.name: c.status.value for c in critical_components
            },
            "timestamp": datetime.now().isoformat()
        }

    def get_alerts(
        self,
        resolved: Optional[bool] = None,
        severity: Optional[AlertSeverity] = None
    ) -> List[Alert]:
        """Get filtered alerts."""
        alerts = self.alerts

        if resolved is not None:
            alerts = [a for a in alerts if a.resolved == resolved]

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        return alerts

    def get_system_info(self) -> Dict[str, Any]:
        """Get system information."""
        info = {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "hostname": platform.node(),
            "timestamp": datetime.now().isoformat()
        }

        try:
            import psutil
            info.update({
                "cpu_count": psutil.cpu_count(),
                "memory_total_gb": psutil.virtual_memory().total / (1024 ** 3),
                "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat()
            })
        except ImportError:
            pass

        return info


# =============================================================================
# GLOBAL MONITOR
# =============================================================================

_monitor: Optional[HealthMonitor] = None


def get_health_monitor() -> HealthMonitor:
    """Get global health monitor."""
    global _monitor
    if _monitor is None:
        _monitor = HealthMonitor()
    return _monitor


# =============================================================================
# MAIN
# =============================================================================

async def demo():
    """Demo health monitor."""
    monitor = HealthMonitor(check_interval=5.0)

    # Register checks
    monitor.register_check(MemoryCheck())
    monitor.register_check(DiskCheck())

    # Register a simple ping check
    async def ping_service():
        await asyncio.sleep(0.1)
        return True

    monitor.register_check(PingCheck("main_service", ping_service))

    # Register alert handler
    def on_alert(alert: Alert):
        print(f"ALERT: [{alert.severity.value}] {alert.title}: {alert.message}")

    monitor.register_alert_handler(on_alert)

    # Run checks
    print("Running health checks...")
    results = await monitor.run_all_checks()

    for name, result in results.items():
        print(f"  {name}: {result.status.value} ({result.latency_ms:.1f}ms)")

    # Get status
    print("\nOverall status:")
    status = monitor.get_status()
    print(f"  Status: {status['status']}")
    print(f"  Active alerts: {status['active_alerts']}")

    # Liveness/readiness
    print(f"\nLiveness: {monitor.get_liveness()}")
    print(f"Readiness: {monitor.get_readiness()}")

    # System info
    print(f"\nSystem info: {monitor.get_system_info()}")


if __name__ == "__main__":
    asyncio.run(demo())
