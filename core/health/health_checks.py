#!/usr/bin/env python3
"""
BAEL - Health Check System
Comprehensive health check and monitoring system.

This module provides a complete health check framework
for system health monitoring and reporting.

Features:
- Component health checks
- Dependency checks
- Aggregated health status
- Health history
- Readiness probes
- Liveness probes
- Custom health indicators
- Health endpoints
- Alerting integration
- Self-healing triggers
"""

import asyncio
import json
import logging
import os
import socket
import time
import traceback
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import (Any, Callable, Coroutine, Dict, Generic, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class CheckType(Enum):
    """Types of health checks."""
    LIVENESS = "liveness"
    READINESS = "readiness"
    STARTUP = "startup"
    DEPENDENCY = "dependency"
    CUSTOM = "custom"


class Severity(Enum):
    """Health check severity."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TriggerAction(Enum):
    """Self-healing trigger actions."""
    RESTART = "restart"
    RESET = "reset"
    NOTIFY = "notify"
    SCALE = "scale"
    FAILOVER = "failover"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class HealthCheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    checked_at: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None

    @property
    def is_healthy(self) -> bool:
        return self.status == HealthStatus.HEALTHY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "duration_ms": self.duration_ms,
            "checked_at": self.checked_at.isoformat(),
            "error": self.error
        }


@dataclass
class ComponentHealth:
    """Health of a component."""
    name: str
    status: HealthStatus = HealthStatus.UNKNOWN
    checks: List[HealthCheckResult] = field(default_factory=list)
    last_checked: Optional[datetime] = None
    consecutive_failures: int = 0
    severity: Severity = Severity.MEDIUM

    def update(self, result: HealthCheckResult) -> None:
        """Update with check result."""
        self.checks.append(result)
        self.last_checked = result.checked_at

        if result.status == HealthStatus.HEALTHY:
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1

        # Keep only last 100 checks
        if len(self.checks) > 100:
            self.checks = self.checks[-100:]

        self._calculate_status()

    def _calculate_status(self) -> None:
        """Calculate overall status from recent checks."""
        if not self.checks:
            self.status = HealthStatus.UNKNOWN
            return

        recent = self.checks[-5:]
        healthy = sum(1 for c in recent if c.status == HealthStatus.HEALTHY)

        if healthy == len(recent):
            self.status = HealthStatus.HEALTHY
        elif healthy >= len(recent) // 2:
            self.status = HealthStatus.DEGRADED
        else:
            self.status = HealthStatus.UNHEALTHY


@dataclass
class SystemHealth:
    """Overall system health."""
    status: HealthStatus = HealthStatus.UNKNOWN
    components: Dict[str, ComponentHealth] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    uptime: float = 0.0
    version: str = "1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "uptime": self.uptime,
            "version": self.version,
            "components": {
                name: {
                    "status": comp.status.value,
                    "last_checked": comp.last_checked.isoformat() if comp.last_checked else None,
                    "consecutive_failures": comp.consecutive_failures
                }
                for name, comp in self.components.items()
            }
        }


@dataclass
class HealthCheckConfig:
    """Configuration for a health check."""
    name: str
    check_type: CheckType = CheckType.LIVENESS
    interval: float = 30.0  # seconds
    timeout: float = 10.0
    severity: Severity = Severity.MEDIUM
    enabled: bool = True

    # Thresholds
    failure_threshold: int = 3
    success_threshold: int = 1

    # Self-healing
    auto_heal: bool = False
    heal_action: TriggerAction = TriggerAction.NOTIFY


@dataclass
class HealthAlert:
    """Health alert."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    component: str = ""
    severity: Severity = Severity.MEDIUM
    message: str = ""
    status: HealthStatus = HealthStatus.UNHEALTHY
    triggered_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None

    @property
    def is_active(self) -> bool:
        return self.resolved_at is None


# =============================================================================
# HEALTH INDICATORS
# =============================================================================

class HealthIndicator(ABC):
    """Abstract health indicator."""

    def __init__(self, name: str, config: HealthCheckConfig = None):
        self.name = name
        self.config = config or HealthCheckConfig(name=name)

    @abstractmethod
    async def check(self) -> HealthCheckResult:
        """Perform health check."""
        pass


class DiskSpaceIndicator(HealthIndicator):
    """Check disk space."""

    def __init__(
        self,
        name: str = "disk_space",
        path: str = "/",
        threshold_percent: float = 90.0
    ):
        super().__init__(name)
        self.path = path
        self.threshold = threshold_percent

    async def check(self) -> HealthCheckResult:
        try:
            import shutil
            total, used, free = shutil.disk_usage(self.path)
            used_percent = (used / total) * 100

            status = HealthStatus.HEALTHY
            if used_percent > self.threshold:
                status = HealthStatus.UNHEALTHY
            elif used_percent > self.threshold - 10:
                status = HealthStatus.DEGRADED

            return HealthCheckResult(
                name=self.name,
                status=status,
                message=f"Disk usage: {used_percent:.1f}%",
                details={
                    "total_gb": total / (1024**3),
                    "used_gb": used / (1024**3),
                    "free_gb": free / (1024**3),
                    "used_percent": used_percent
                }
            )
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNKNOWN,
                error=str(e)
            )


class MemoryIndicator(HealthIndicator):
    """Check memory usage."""

    def __init__(
        self,
        name: str = "memory",
        threshold_percent: float = 90.0
    ):
        super().__init__(name)
        self.threshold = threshold_percent

    async def check(self) -> HealthCheckResult:
        try:
            import resource

            # Get memory info from /proc/meminfo if available
            try:
                with open('/proc/meminfo', 'r') as f:
                    meminfo = dict(
                        line.split(':')[:2]
                        for line in f.readlines()
                    )

                total = int(meminfo['MemTotal'].strip().split()[0]) * 1024
                free = int(meminfo['MemFree'].strip().split()[0]) * 1024
                available = int(meminfo.get('MemAvailable', meminfo['MemFree']).strip().split()[0]) * 1024

                used_percent = ((total - available) / total) * 100
            except:
                # Fallback
                used_percent = 50.0
                total = 0
                available = 0

            status = HealthStatus.HEALTHY
            if used_percent > self.threshold:
                status = HealthStatus.UNHEALTHY
            elif used_percent > self.threshold - 10:
                status = HealthStatus.DEGRADED

            return HealthCheckResult(
                name=self.name,
                status=status,
                message=f"Memory usage: {used_percent:.1f}%",
                details={
                    "total_mb": total / (1024**2),
                    "available_mb": available / (1024**2),
                    "used_percent": used_percent
                }
            )
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNKNOWN,
                error=str(e)
            )


class TCPHealthIndicator(HealthIndicator):
    """Check TCP connectivity."""

    def __init__(
        self,
        name: str,
        host: str,
        port: int,
        timeout: float = 5.0
    ):
        super().__init__(name)
        self.host = host
        self.port = port
        self.timeout = timeout

    async def check(self) -> HealthCheckResult:
        start = time.time()

        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.timeout
            )
            writer.close()
            await writer.wait_closed()

            duration = (time.time() - start) * 1000

            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.HEALTHY,
                message=f"TCP connection successful",
                duration_ms=duration,
                details={
                    "host": self.host,
                    "port": self.port
                }
            )
        except asyncio.TimeoutError:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message="Connection timeout",
                duration_ms=(time.time() - start) * 1000,
                details={"host": self.host, "port": self.port}
            )
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                duration_ms=(time.time() - start) * 1000,
                error=str(e)
            )


class HTTPHealthIndicator(HealthIndicator):
    """Check HTTP endpoint."""

    def __init__(
        self,
        name: str,
        url: str,
        timeout: float = 10.0,
        expected_status: List[int] = None
    ):
        super().__init__(name)
        self.url = url
        self.timeout = timeout
        self.expected_status = expected_status or [200]

    async def check(self) -> HealthCheckResult:
        from urllib.parse import urlparse

        start = time.time()
        parsed = urlparse(self.url)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        path = parsed.path or '/'

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=self.timeout
            )

            request = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
            writer.write(request.encode())
            await writer.drain()

            response = await asyncio.wait_for(
                reader.read(1024),
                timeout=self.timeout
            )

            writer.close()
            await writer.wait_closed()

            duration = (time.time() - start) * 1000

            # Parse status
            if response:
                status_line = response.decode().split('\r\n')[0]
                status_code = int(status_line.split()[1])

                if status_code in self.expected_status:
                    return HealthCheckResult(
                        name=self.name,
                        status=HealthStatus.HEALTHY,
                        message=f"HTTP {status_code}",
                        duration_ms=duration,
                        details={"url": self.url, "status_code": status_code}
                    )
                else:
                    return HealthCheckResult(
                        name=self.name,
                        status=HealthStatus.UNHEALTHY,
                        message=f"Unexpected status: {status_code}",
                        duration_ms=duration,
                        details={"url": self.url, "status_code": status_code}
                    )

            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message="No response",
                duration_ms=duration
            )

        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                duration_ms=(time.time() - start) * 1000,
                error=str(e)
            )


class CustomHealthIndicator(HealthIndicator):
    """Custom function-based health indicator."""

    def __init__(
        self,
        name: str,
        check_func: Callable[[], Coroutine[Any, Any, HealthCheckResult]]
    ):
        super().__init__(name)
        self.check_func = check_func

    async def check(self) -> HealthCheckResult:
        try:
            return await self.check_func()
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                error=str(e)
            )


# =============================================================================
# HEALTH CHECK MANAGER
# =============================================================================

class HealthCheckManager:
    """
    Master health check management for BAEL.

    Provides comprehensive health monitoring and reporting.
    """

    def __init__(self):
        self.indicators: Dict[str, HealthIndicator] = {}
        self.components: Dict[str, ComponentHealth] = {}
        self.alerts: List[HealthAlert] = []

        # Callbacks
        self.on_unhealthy: List[Callable[[str, HealthCheckResult], None]] = []
        self.on_healthy: List[Callable[[str, HealthCheckResult], None]] = []
        self.on_alert: List[Callable[[HealthAlert], None]] = []

        # Background task
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # Tracking
        self.start_time = datetime.now()
        self.checks_performed = 0
        self.failures_detected = 0

        # History
        self.history: deque = deque(maxlen=1000)

    # Registration
    def register(
        self,
        indicator: HealthIndicator,
        component: str = None
    ) -> None:
        """Register a health indicator."""
        self.indicators[indicator.name] = indicator

        component_name = component or indicator.name
        if component_name not in self.components:
            self.components[component_name] = ComponentHealth(
                name=component_name,
                severity=indicator.config.severity
            )

    def register_tcp_check(
        self,
        name: str,
        host: str,
        port: int,
        component: str = None
    ) -> None:
        """Register a TCP health check."""
        indicator = TCPHealthIndicator(name, host, port)
        self.register(indicator, component)

    def register_http_check(
        self,
        name: str,
        url: str,
        component: str = None
    ) -> None:
        """Register an HTTP health check."""
        indicator = HTTPHealthIndicator(name, url)
        self.register(indicator, component)

    def register_custom_check(
        self,
        name: str,
        check_func: Callable[[], Coroutine[Any, Any, HealthCheckResult]],
        component: str = None
    ) -> None:
        """Register a custom health check."""
        indicator = CustomHealthIndicator(name, check_func)
        self.register(indicator, component)

    # Execution
    async def check(self, name: str) -> HealthCheckResult:
        """Run a specific health check."""
        if name not in self.indicators:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNKNOWN,
                error=f"Indicator not found: {name}"
            )

        indicator = self.indicators[name]

        start = time.time()
        try:
            result = await asyncio.wait_for(
                indicator.check(),
                timeout=indicator.config.timeout
            )
        except asyncio.TimeoutError:
            result = HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                error="Health check timeout"
            )
        except Exception as e:
            result = HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                error=str(e)
            )

        result.duration_ms = (time.time() - start) * 1000

        # Update component
        component_name = name  # Default: one-to-one mapping
        if component_name in self.components:
            self.components[component_name].update(result)

        # Track
        self.checks_performed += 1
        if not result.is_healthy:
            self.failures_detected += 1

        # History
        self.history.append(result)

        # Callbacks
        await self._handle_result(result)

        return result

    async def check_all(self) -> Dict[str, HealthCheckResult]:
        """Run all health checks."""
        results = {}

        # Run checks concurrently
        tasks = {
            name: asyncio.create_task(self.check(name))
            for name in self.indicators
        }

        for name, task in tasks.items():
            results[name] = await task

        return results

    async def _handle_result(self, result: HealthCheckResult) -> None:
        """Handle health check result."""
        if result.status == HealthStatus.UNHEALTHY:
            for callback in self.on_unhealthy:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(result.name, result)
                    else:
                        callback(result.name, result)
                except Exception as e:
                    logger.error(f"Callback error: {e}")

            # Check if alert needed
            component = self.components.get(result.name)
            if component and component.consecutive_failures >= 3:
                await self._create_alert(result)

        elif result.status == HealthStatus.HEALTHY:
            for callback in self.on_healthy:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(result.name, result)
                    else:
                        callback(result.name, result)
                except:
                    pass

            # Resolve alerts
            self._resolve_alerts(result.name)

    async def _create_alert(self, result: HealthCheckResult) -> None:
        """Create health alert."""
        component = self.components.get(result.name)

        # Check if active alert exists
        for alert in self.alerts:
            if alert.component == result.name and alert.is_active:
                return  # Alert already exists

        alert = HealthAlert(
            component=result.name,
            severity=component.severity if component else Severity.MEDIUM,
            message=result.message or result.error or "Health check failed",
            status=result.status
        )

        self.alerts.append(alert)

        for callback in self.on_alert:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except:
                pass

    def _resolve_alerts(self, component: str) -> None:
        """Resolve active alerts for a component."""
        for alert in self.alerts:
            if alert.component == component and alert.is_active:
                alert.resolved_at = datetime.now()

    # Status
    def get_status(self) -> SystemHealth:
        """Get overall system health."""
        uptime = (datetime.now() - self.start_time).total_seconds()

        # Calculate overall status
        statuses = [c.status for c in self.components.values()]

        if not statuses:
            overall = HealthStatus.UNKNOWN
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            overall = HealthStatus.HEALTHY
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            overall = HealthStatus.UNHEALTHY
        else:
            overall = HealthStatus.DEGRADED

        return SystemHealth(
            status=overall,
            components=self.components.copy(),
            uptime=uptime
        )

    def is_ready(self) -> bool:
        """Check if system is ready (all readiness checks pass)."""
        for name, indicator in self.indicators.items():
            if indicator.config.check_type == CheckType.READINESS:
                if name in self.components:
                    if self.components[name].status != HealthStatus.HEALTHY:
                        return False
        return True

    def is_alive(self) -> bool:
        """Check if system is alive (critical liveness checks pass)."""
        for name, indicator in self.indicators.items():
            if indicator.config.check_type == CheckType.LIVENESS:
                if indicator.config.severity == Severity.CRITICAL:
                    if name in self.components:
                        if self.components[name].status == HealthStatus.UNHEALTHY:
                            return False
        return True

    # Kubernetes-style endpoints
    async def liveness_probe(self) -> Tuple[bool, Dict[str, Any]]:
        """Kubernetes liveness probe."""
        alive = self.is_alive()
        return alive, {
            "status": "ok" if alive else "fail",
            "timestamp": datetime.now().isoformat()
        }

    async def readiness_probe(self) -> Tuple[bool, Dict[str, Any]]:
        """Kubernetes readiness probe."""
        ready = self.is_ready()
        return ready, {
            "status": "ready" if ready else "not_ready",
            "timestamp": datetime.now().isoformat()
        }

    async def startup_probe(self) -> Tuple[bool, Dict[str, Any]]:
        """Kubernetes startup probe."""
        # Run all startup checks
        for name, indicator in self.indicators.items():
            if indicator.config.check_type == CheckType.STARTUP:
                result = await self.check(name)
                if not result.is_healthy:
                    return False, {"status": "starting", "failed": name}

        return True, {"status": "started"}

    # Background task
    async def start(self) -> None:
        """Start background health checking."""
        self._running = True
        self._task = asyncio.create_task(self._check_loop())

    async def stop(self) -> None:
        """Stop background health checking."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _check_loop(self) -> None:
        """Background health check loop."""
        while self._running:
            try:
                await self.check_all()
                await asyncio.sleep(30)  # Default interval
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(5)

    # Alerts
    def get_active_alerts(self) -> List[HealthAlert]:
        """Get active alerts."""
        return [a for a in self.alerts if a.is_active]

    def get_alerts_history(
        self,
        limit: int = 100,
        severity: Severity = None
    ) -> List[HealthAlert]:
        """Get alerts history."""
        alerts = self.alerts[-limit:]

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        return alerts

    # Statistics
    def get_statistics(self) -> Dict[str, Any]:
        """Get health check statistics."""
        status = self.get_status()

        healthy_count = sum(
            1 for c in self.components.values()
            if c.status == HealthStatus.HEALTHY
        )

        return {
            "overall_status": status.status.value,
            "uptime_seconds": status.uptime,
            "total_components": len(self.components),
            "healthy_components": healthy_count,
            "checks_performed": self.checks_performed,
            "failures_detected": self.failures_detected,
            "active_alerts": len(self.get_active_alerts()),
            "total_alerts": len(self.alerts)
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Health Check System."""
    print("=" * 70)
    print("BAEL - HEALTH CHECK SYSTEM DEMO")
    print("System Health Monitoring and Reporting")
    print("=" * 70)
    print()

    manager = HealthCheckManager()

    # 1. Register Health Checks
    print("1. REGISTERING HEALTH CHECKS:")
    print("-" * 40)

    manager.register(DiskSpaceIndicator(), component="storage")
    print("   Registered: disk_space (storage)")

    manager.register(MemoryIndicator(), component="resources")
    print("   Registered: memory (resources)")

    manager.register_tcp_check("localhost_check", "127.0.0.1", 80, "network")
    print("   Registered: localhost_check (network)")

    # Custom check
    async def database_check() -> HealthCheckResult:
        return HealthCheckResult(
            name="database",
            status=HealthStatus.HEALTHY,
            message="Database connection OK",
            details={"connections": 10, "pool_size": 20}
        )

    manager.register_custom_check("database", database_check, "data")
    print("   Registered: database (data)")
    print()

    # 2. Run Individual Checks
    print("2. INDIVIDUAL HEALTH CHECKS:")
    print("-" * 40)

    disk_result = await manager.check("disk_space")
    print(f"   Disk Space: {disk_result.status.value}")
    if disk_result.details:
        print(f"      Used: {disk_result.details.get('used_percent', 0):.1f}%")

    memory_result = await manager.check("memory")
    print(f"   Memory: {memory_result.status.value}")

    db_result = await manager.check("database")
    print(f"   Database: {db_result.status.value}")
    print()

    # 3. Run All Checks
    print("3. ALL HEALTH CHECKS:")
    print("-" * 40)

    all_results = await manager.check_all()
    for name, result in all_results.items():
        status_icon = "✓" if result.is_healthy else "✗"
        print(f"   {status_icon} {name}: {result.status.value} ({result.duration_ms:.1f}ms)")
    print()

    # 4. System Status
    print("4. SYSTEM STATUS:")
    print("-" * 40)

    status = manager.get_status()
    print(f"   Overall Status: {status.status.value}")
    print(f"   Uptime: {status.uptime:.1f} seconds")
    print(f"   Components:")
    for name, comp in status.components.items():
        print(f"      - {name}: {comp.status.value}")
    print()

    # 5. Liveness/Readiness
    print("5. KUBERNETES PROBES:")
    print("-" * 40)

    alive, liveness_data = await manager.liveness_probe()
    print(f"   Liveness: {'PASS' if alive else 'FAIL'}")

    ready, readiness_data = await manager.readiness_probe()
    print(f"   Readiness: {'PASS' if ready else 'FAIL'}")
    print()

    # 6. Event Handlers
    print("6. EVENT HANDLERS:")
    print("-" * 40)

    unhealthy_events = []

    def on_unhealthy(name: str, result: HealthCheckResult):
        unhealthy_events.append(name)

    manager.on_unhealthy.append(on_unhealthy)

    # Simulate unhealthy check
    async def failing_check() -> HealthCheckResult:
        return HealthCheckResult(
            name="failing_service",
            status=HealthStatus.UNHEALTHY,
            message="Service unavailable"
        )

    manager.register_custom_check("failing_service", failing_check, "external")
    await manager.check("failing_service")
    await manager.check("failing_service")
    await manager.check("failing_service")

    print(f"   Unhealthy events captured: {unhealthy_events}")
    print()

    # 7. Alerts
    print("7. HEALTH ALERTS:")
    print("-" * 40)

    active = manager.get_active_alerts()
    print(f"   Active alerts: {len(active)}")
    for alert in active:
        print(f"      - {alert.component}: {alert.message}")
    print()

    # 8. Check History
    print("8. CHECK HISTORY:")
    print("-" * 40)

    print(f"   Total checks in history: {len(manager.history)}")
    recent = list(manager.history)[-5:]
    for result in recent:
        print(f"      - {result.name}: {result.status.value}")
    print()

    # 9. Health Report
    print("9. HEALTH REPORT:")
    print("-" * 40)

    report = status.to_dict()
    print(f"   Status: {report['status']}")
    print(f"   Timestamp: {report['timestamp']}")
    for comp_name, comp_data in report['components'].items():
        print(f"   {comp_name}:")
        print(f"      status: {comp_data['status']}")
        print(f"      failures: {comp_data['consecutive_failures']}")
    print()

    # 10. Statistics
    print("10. STATISTICS:")
    print("-" * 40)

    stats = manager.get_statistics()
    for key, value in stats.items():
        print(f"    {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Health Check System Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
