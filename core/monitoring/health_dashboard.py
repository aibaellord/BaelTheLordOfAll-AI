#!/usr/bin/env python3
"""
BAEL - Health Dashboard System
Comprehensive system health monitoring and dashboard.

Features:
- Health checks
- Service status
- Performance metrics
- Resource monitoring
- Alert management
- Dependency tracking
- SLA monitoring
- Historical data
- Trend analysis
- Dashboard widgets
"""

import asyncio
import json
import logging
import statistics
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import (Any, Awaitable, Callable, Dict, Generic, List, Optional,
                    Set, Tuple, TypeVar, Union)

logger = logging.getLogger(__name__)


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
    """Health check types."""
    LIVENESS = "liveness"
    READINESS = "readiness"
    STARTUP = "startup"
    CUSTOM = "custom"


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class MetricType(Enum):
    """Metric types."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class ResourceType(Enum):
    """Resource types."""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    CONNECTION = "connection"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class HealthCheckResult:
    """Health check result."""
    check_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    status: HealthStatus = HealthStatus.UNKNOWN
    message: str = ""
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthCheck:
    """Health check definition."""
    check_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    check_type: CheckType = CheckType.LIVENESS
    interval: float = 30.0  # seconds
    timeout: float = 5.0
    retries: int = 3
    enabled: bool = True
    critical: bool = False
    last_result: Optional[HealthCheckResult] = None
    last_check: float = 0.0


@dataclass
class ServiceStatus:
    """Service status."""
    service_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    status: HealthStatus = HealthStatus.UNKNOWN
    version: str = ""
    uptime: float = 0.0
    started_at: float = field(default_factory=time.time)
    checks: Dict[str, HealthCheckResult] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Metric:
    """Metric data point."""
    metric_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    value: float = 0.0
    metric_type: MetricType = MetricType.GAUGE
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    unit: str = ""


@dataclass
class ResourceUsage:
    """Resource usage snapshot."""
    resource_type: ResourceType = ResourceType.CPU
    current: float = 0.0
    limit: float = 100.0
    unit: str = "%"
    timestamp: float = field(default_factory=time.time)

    @property
    def utilization(self) -> float:
        if self.limit <= 0:
            return 0.0
        return (self.current / self.limit) * 100


@dataclass
class Alert:
    """Alert definition."""
    alert_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    severity: AlertSeverity = AlertSeverity.WARNING
    status: AlertStatus = AlertStatus.ACTIVE
    message: str = ""
    source: str = ""
    created_at: float = field(default_factory=time.time)
    acknowledged_at: float = 0.0
    resolved_at: float = 0.0
    acknowledged_by: str = ""
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class SLADefinition:
    """SLA definition."""
    sla_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    target: float = 99.9  # percentage
    metric: str = ""  # e.g., "uptime", "response_time"
    window_hours: int = 720  # 30 days
    current_value: float = 100.0
    breaches: int = 0


@dataclass
class DashboardWidget:
    """Dashboard widget configuration."""
    widget_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    widget_type: str = "gauge"  # gauge, chart, table, status
    data_source: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    position: Tuple[int, int] = (0, 0)
    size: Tuple[int, int] = (1, 1)


# =============================================================================
# HEALTH CHECK EXECUTOR
# =============================================================================

class HealthCheckExecutor:
    """Executes health checks."""

    def __init__(self):
        self._check_handlers: Dict[str, Callable] = {}

    def register(
        self,
        name: str,
        handler: Callable[[], Awaitable[HealthCheckResult]]
    ) -> None:
        """Register health check handler."""
        self._check_handlers[name] = handler

    async def execute(
        self,
        check: HealthCheck
    ) -> HealthCheckResult:
        """Execute a health check."""
        handler = self._check_handlers.get(check.name)

        if not handler:
            return HealthCheckResult(
                name=check.name,
                status=HealthStatus.UNKNOWN,
                message="No handler registered"
            )

        start_time = time.time()

        try:
            result = await asyncio.wait_for(
                handler(),
                timeout=check.timeout
            )

            result.duration_ms = (time.time() - start_time) * 1000
            return result

        except asyncio.TimeoutError:
            return HealthCheckResult(
                name=check.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check timed out after {check.timeout}s",
                duration_ms=(time.time() - start_time) * 1000
            )

        except Exception as e:
            return HealthCheckResult(
                name=check.name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                duration_ms=(time.time() - start_time) * 1000
            )


# =============================================================================
# METRICS COLLECTOR
# =============================================================================

class MetricsCollector:
    """Collects and stores metrics."""

    def __init__(self, retention_hours: int = 24):
        self._metrics: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=1000)
        )
        self._retention = retention_hours * 3600

    def record(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        labels: Dict[str, str] = None,
        unit: str = ""
    ) -> Metric:
        """Record a metric."""
        metric = Metric(
            name=name,
            value=value,
            metric_type=metric_type,
            labels=labels or {},
            unit=unit
        )

        self._metrics[name].append(metric)
        self._cleanup()

        return metric

    def get_latest(self, name: str) -> Optional[Metric]:
        """Get latest metric value."""
        if name in self._metrics and self._metrics[name]:
            return self._metrics[name][-1]
        return None

    def get_history(
        self,
        name: str,
        since: float = None,
        limit: int = 100
    ) -> List[Metric]:
        """Get metric history."""
        if name not in self._metrics:
            return []

        metrics = list(self._metrics[name])

        if since:
            metrics = [m for m in metrics if m.timestamp >= since]

        return metrics[-limit:]

    def get_stats(self, name: str) -> Dict[str, float]:
        """Get metric statistics."""
        metrics = self.get_history(name)

        if not metrics:
            return {}

        values = [m.value for m in metrics]

        return {
            "min": min(values),
            "max": max(values),
            "avg": statistics.mean(values),
            "median": statistics.median(values),
            "stddev": statistics.stdev(values) if len(values) > 1 else 0,
            "count": len(values)
        }

    def _cleanup(self) -> None:
        """Clean up old metrics."""
        cutoff = time.time() - self._retention

        for name in self._metrics:
            while self._metrics[name]:
                if self._metrics[name][0].timestamp < cutoff:
                    self._metrics[name].popleft()
                else:
                    break


# =============================================================================
# RESOURCE MONITOR
# =============================================================================

class ResourceMonitor:
    """Monitors system resources."""

    def __init__(self):
        self._resources: Dict[ResourceType, ResourceUsage] = {}
        self._history: Dict[ResourceType, deque] = defaultdict(
            lambda: deque(maxlen=100)
        )
        self._thresholds: Dict[ResourceType, float] = {
            ResourceType.CPU: 80.0,
            ResourceType.MEMORY: 85.0,
            ResourceType.DISK: 90.0,
        }

    def update(
        self,
        resource_type: ResourceType,
        current: float,
        limit: float = 100.0,
        unit: str = "%"
    ) -> ResourceUsage:
        """Update resource usage."""
        usage = ResourceUsage(
            resource_type=resource_type,
            current=current,
            limit=limit,
            unit=unit
        )

        self._resources[resource_type] = usage
        self._history[resource_type].append(usage)

        return usage

    def get_usage(self, resource_type: ResourceType) -> Optional[ResourceUsage]:
        """Get current resource usage."""
        return self._resources.get(resource_type)

    def get_all_usage(self) -> Dict[ResourceType, ResourceUsage]:
        """Get all resource usage."""
        return self._resources.copy()

    def get_history(
        self,
        resource_type: ResourceType,
        limit: int = 100
    ) -> List[ResourceUsage]:
        """Get resource history."""
        return list(self._history.get(resource_type, []))[-limit:]

    def check_thresholds(self) -> List[Tuple[ResourceType, float]]:
        """Check for threshold violations."""
        violations = []

        for resource_type, usage in self._resources.items():
            threshold = self._thresholds.get(resource_type, 100.0)

            if usage.utilization > threshold:
                violations.append((resource_type, usage.utilization))

        return violations

    def set_threshold(
        self,
        resource_type: ResourceType,
        threshold: float
    ) -> None:
        """Set resource threshold."""
        self._thresholds[resource_type] = threshold


# =============================================================================
# ALERT MANAGER
# =============================================================================

class AlertManager:
    """Manages system alerts."""

    def __init__(self, max_alerts: int = 1000):
        self._alerts: Dict[str, Alert] = {}
        self._history: List[Alert] = []
        self._max_alerts = max_alerts
        self._handlers: List[Callable[[Alert], Awaitable[None]]] = []

    async def create(
        self,
        name: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.WARNING,
        source: str = "",
        labels: Dict[str, str] = None
    ) -> Alert:
        """Create a new alert."""
        alert = Alert(
            name=name,
            message=message,
            severity=severity,
            source=source,
            labels=labels or {}
        )

        self._alerts[alert.alert_id] = alert

        # Notify handlers
        for handler in self._handlers:
            try:
                await handler(alert)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")

        return alert

    def acknowledge(
        self,
        alert_id: str,
        acknowledged_by: str
    ) -> Optional[Alert]:
        """Acknowledge an alert."""
        alert = self._alerts.get(alert_id)

        if alert:
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = time.time()
            alert.acknowledged_by = acknowledged_by

        return alert

    def resolve(self, alert_id: str) -> Optional[Alert]:
        """Resolve an alert."""
        alert = self._alerts.get(alert_id)

        if alert:
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = time.time()

            # Move to history
            self._history.append(alert)
            del self._alerts[alert_id]

            # Trim history
            if len(self._history) > self._max_alerts:
                self._history = self._history[-self._max_alerts:]

        return alert

    def get_active(
        self,
        severity: AlertSeverity = None
    ) -> List[Alert]:
        """Get active alerts."""
        alerts = list(self._alerts.values())

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        return sorted(alerts, key=lambda a: a.created_at, reverse=True)

    def get_history(
        self,
        limit: int = 100,
        since: float = None
    ) -> List[Alert]:
        """Get alert history."""
        history = self._history

        if since:
            history = [a for a in history if a.created_at >= since]

        return history[-limit:]

    def register_handler(
        self,
        handler: Callable[[Alert], Awaitable[None]]
    ) -> None:
        """Register alert handler."""
        self._handlers.append(handler)

    def get_stats(self) -> Dict[str, Any]:
        """Get alert statistics."""
        active = list(self._alerts.values())

        by_severity = defaultdict(int)
        for alert in active:
            by_severity[alert.severity.value] += 1

        return {
            "active_count": len(active),
            "by_severity": dict(by_severity),
            "history_count": len(self._history)
        }


# =============================================================================
# SLA MONITOR
# =============================================================================

class SLAMonitor:
    """Monitors SLA compliance."""

    def __init__(self):
        self._slas: Dict[str, SLADefinition] = {}
        self._measurements: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=10000)
        )

    def define(
        self,
        name: str,
        target: float,
        metric: str,
        window_hours: int = 720
    ) -> SLADefinition:
        """Define an SLA."""
        sla = SLADefinition(
            name=name,
            target=target,
            metric=metric,
            window_hours=window_hours
        )

        self._slas[sla.sla_id] = sla

        return sla

    def record(
        self,
        sla_id: str,
        value: float,
        success: bool = True
    ) -> None:
        """Record SLA measurement."""
        if sla_id not in self._slas:
            return

        self._measurements[sla_id].append({
            "value": value,
            "success": success,
            "timestamp": time.time()
        })

    def calculate(self, sla_id: str) -> Optional[float]:
        """Calculate current SLA value."""
        sla = self._slas.get(sla_id)

        if not sla:
            return None

        measurements = list(self._measurements.get(sla_id, []))

        if not measurements:
            return 100.0

        # Filter by window
        cutoff = time.time() - (sla.window_hours * 3600)
        measurements = [m for m in measurements if m["timestamp"] >= cutoff]

        if not measurements:
            return 100.0

        success_count = sum(1 for m in measurements if m["success"])
        current = (success_count / len(measurements)) * 100

        sla.current_value = current

        if current < sla.target:
            sla.breaches += 1

        return current

    def get_status(self, sla_id: str) -> Optional[Dict[str, Any]]:
        """Get SLA status."""
        sla = self._slas.get(sla_id)

        if not sla:
            return None

        current = self.calculate(sla_id)

        return {
            "name": sla.name,
            "target": sla.target,
            "current": current,
            "window_hours": sla.window_hours,
            "breaches": sla.breaches,
            "compliant": current >= sla.target if current else True
        }

    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get all SLA status."""
        return {
            sla_id: self.get_status(sla_id)
            for sla_id in self._slas
        }


# =============================================================================
# HEALTH DASHBOARD
# =============================================================================

class HealthDashboard:
    """
    Comprehensive Health Dashboard for BAEL.
    """

    def __init__(self):
        self.executor = HealthCheckExecutor()
        self.metrics = MetricsCollector()
        self.resources = ResourceMonitor()
        self.alerts = AlertManager()
        self.sla = SLAMonitor()

        self._services: Dict[str, ServiceStatus] = {}
        self._checks: Dict[str, HealthCheck] = {}
        self._widgets: Dict[str, DashboardWidget] = {}
        self._running = False
        self._check_task: Optional[asyncio.Task] = None

    # -------------------------------------------------------------------------
    # SERVICE MANAGEMENT
    # -------------------------------------------------------------------------

    def register_service(
        self,
        name: str,
        version: str = "1.0.0",
        dependencies: List[str] = None
    ) -> ServiceStatus:
        """Register a service."""
        service = ServiceStatus(
            name=name,
            version=version,
            dependencies=dependencies or []
        )

        self._services[service.service_id] = service

        return service

    def get_service(self, service_id: str) -> Optional[ServiceStatus]:
        """Get service status."""
        return self._services.get(service_id)

    def update_service_status(
        self,
        service_id: str,
        status: HealthStatus,
        metadata: Dict[str, Any] = None
    ) -> Optional[ServiceStatus]:
        """Update service status."""
        service = self._services.get(service_id)

        if service:
            service.status = status
            service.uptime = time.time() - service.started_at

            if metadata:
                service.metadata.update(metadata)

        return service

    def list_services(self) -> List[ServiceStatus]:
        """List all services."""
        return list(self._services.values())

    # -------------------------------------------------------------------------
    # HEALTH CHECKS
    # -------------------------------------------------------------------------

    def register_check(
        self,
        name: str,
        handler: Callable[[], Awaitable[HealthCheckResult]],
        check_type: CheckType = CheckType.LIVENESS,
        interval: float = 30.0,
        timeout: float = 5.0,
        critical: bool = False
    ) -> HealthCheck:
        """Register a health check."""
        check = HealthCheck(
            name=name,
            check_type=check_type,
            interval=interval,
            timeout=timeout,
            critical=critical
        )

        self._checks[check.check_id] = check
        self.executor.register(name, handler)

        return check

    async def run_check(self, check_id: str) -> Optional[HealthCheckResult]:
        """Run a single health check."""
        check = self._checks.get(check_id)

        if not check or not check.enabled:
            return None

        result = await self.executor.execute(check)

        check.last_result = result
        check.last_check = time.time()

        # Record metric
        self.metrics.record(
            f"health_check_{check.name}_duration",
            result.duration_ms,
            MetricType.GAUGE,
            {"check": check.name},
            "ms"
        )

        # Create alert if unhealthy
        if result.status == HealthStatus.UNHEALTHY and check.critical:
            await self.alerts.create(
                f"Health check failed: {check.name}",
                result.message,
                AlertSeverity.CRITICAL,
                source="health_check"
            )

        return result

    async def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all health checks."""
        results = {}

        for check_id, check in self._checks.items():
            if check.enabled:
                result = await self.run_check(check_id)

                if result:
                    results[check.name] = result

        return results

    def get_check_status(self, check_id: str) -> Optional[Dict[str, Any]]:
        """Get check status."""
        check = self._checks.get(check_id)

        if not check:
            return None

        return {
            "name": check.name,
            "type": check.check_type.value,
            "enabled": check.enabled,
            "critical": check.critical,
            "last_status": check.last_result.status.value if check.last_result else "unknown",
            "last_check": check.last_check,
            "last_duration_ms": check.last_result.duration_ms if check.last_result else 0
        }

    # -------------------------------------------------------------------------
    # OVERALL HEALTH
    # -------------------------------------------------------------------------

    async def get_health(self) -> Dict[str, Any]:
        """Get overall health status."""
        # Run all checks
        check_results = await self.run_all_checks()

        # Determine overall status
        statuses = [r.status for r in check_results.values()]

        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            overall = HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            overall = HealthStatus.DEGRADED
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            overall = HealthStatus.HEALTHY
        else:
            overall = HealthStatus.UNKNOWN

        # Get resource violations
        resource_violations = self.resources.check_thresholds()

        # Get active alerts
        active_alerts = self.alerts.get_active()

        return {
            "status": overall.value,
            "timestamp": time.time(),
            "checks": {
                name: {
                    "status": result.status.value,
                    "message": result.message,
                    "duration_ms": result.duration_ms
                }
                for name, result in check_results.items()
            },
            "resources": {
                rt.value: {
                    "current": usage.current,
                    "limit": usage.limit,
                    "utilization": usage.utilization,
                    "unit": usage.unit
                }
                for rt, usage in self.resources.get_all_usage().items()
            },
            "alerts": {
                "active": len(active_alerts),
                "critical": len([a for a in active_alerts if a.severity == AlertSeverity.CRITICAL])
            },
            "services": {
                s.name: s.status.value
                for s in self._services.values()
            }
        }

    async def get_liveness(self) -> Dict[str, Any]:
        """Get liveness status (is the service running)."""
        liveness_checks = [
            c for c in self._checks.values()
            if c.check_type == CheckType.LIVENESS and c.enabled
        ]

        results = []

        for check in liveness_checks:
            result = await self.run_check(check.check_id)

            if result:
                results.append(result)

        alive = all(r.status == HealthStatus.HEALTHY for r in results)

        return {
            "alive": alive,
            "checks": [
                {
                    "name": r.name,
                    "status": r.status.value
                }
                for r in results
            ]
        }

    async def get_readiness(self) -> Dict[str, Any]:
        """Get readiness status (is the service ready to serve)."""
        readiness_checks = [
            c for c in self._checks.values()
            if c.check_type == CheckType.READINESS and c.enabled
        ]

        results = []

        for check in readiness_checks:
            result = await self.run_check(check.check_id)

            if result:
                results.append(result)

        ready = all(r.status == HealthStatus.HEALTHY for r in results)

        return {
            "ready": ready,
            "checks": [
                {
                    "name": r.name,
                    "status": r.status.value
                }
                for r in results
            ]
        }

    # -------------------------------------------------------------------------
    # DASHBOARD
    # -------------------------------------------------------------------------

    def add_widget(
        self,
        name: str,
        widget_type: str,
        data_source: str,
        config: Dict[str, Any] = None,
        position: Tuple[int, int] = (0, 0),
        size: Tuple[int, int] = (1, 1)
    ) -> DashboardWidget:
        """Add dashboard widget."""
        widget = DashboardWidget(
            name=name,
            widget_type=widget_type,
            data_source=data_source,
            config=config or {},
            position=position,
            size=size
        )

        self._widgets[widget.widget_id] = widget

        return widget

    def get_dashboard(self) -> Dict[str, Any]:
        """Get dashboard configuration."""
        return {
            "widgets": [
                {
                    "id": w.widget_id,
                    "name": w.name,
                    "type": w.widget_type,
                    "data_source": w.data_source,
                    "config": w.config,
                    "position": w.position,
                    "size": w.size
                }
                for w in self._widgets.values()
            ]
        }

    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get dashboard with current data."""
        health = await self.get_health()

        return {
            "health": health,
            "resources": {
                rt.value: self.resources.get_usage(rt).__dict__
                for rt in ResourceType
                if self.resources.get_usage(rt)
            },
            "alerts": self.alerts.get_stats(),
            "slas": self.sla.get_all_status(),
            "metrics": {
                name: self.metrics.get_stats(name)
                for name in ["response_time", "request_count", "error_rate"]
                if self.metrics.get_latest(name)
            }
        }

    # -------------------------------------------------------------------------
    # BACKGROUND MONITORING
    # -------------------------------------------------------------------------

    async def start_monitoring(self) -> None:
        """Start background monitoring."""
        self._running = True
        self._check_task = asyncio.create_task(self._monitoring_loop())

    async def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        self._running = False

        if self._check_task:
            self._check_task.cancel()

            try:
                await self._check_task
            except asyncio.CancelledError:
                pass

    async def _monitoring_loop(self) -> None:
        """Background monitoring loop."""
        while self._running:
            for check_id, check in self._checks.items():
                if not check.enabled:
                    continue

                # Check if it's time to run
                if time.time() - check.last_check >= check.interval:
                    await self.run_check(check_id)

            await asyncio.sleep(1)

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get dashboard statistics."""
        return {
            "services": len(self._services),
            "checks": len(self._checks),
            "widgets": len(self._widgets),
            "active_alerts": len(self.alerts.get_active()),
            "slas": len(self.sla._slas)
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Health Dashboard System."""
    print("=" * 70)
    print("BAEL - HEALTH DASHBOARD DEMO")
    print("Comprehensive Health Monitoring System")
    print("=" * 70)
    print()

    dashboard = HealthDashboard()

    # 1. Register Services
    print("1. REGISTER SERVICES:")
    print("-" * 40)

    api_service = dashboard.register_service(
        "api-gateway",
        "2.1.0",
        dependencies=["database", "cache"]
    )
    print(f"   Registered: {api_service.name} v{api_service.version}")

    db_service = dashboard.register_service("database", "5.7.0")
    print(f"   Registered: {db_service.name} v{db_service.version}")

    cache_service = dashboard.register_service("cache", "6.2.0")
    print(f"   Registered: {cache_service.name} v{cache_service.version}")
    print()

    # 2. Register Health Checks
    print("2. REGISTER HEALTH CHECKS:")
    print("-" * 40)

    async def db_health_check():
        await asyncio.sleep(0.05)  # Simulate check
        return HealthCheckResult(
            name="database",
            status=HealthStatus.HEALTHY,
            message="Connection OK"
        )

    async def cache_health_check():
        await asyncio.sleep(0.02)
        return HealthCheckResult(
            name="cache",
            status=HealthStatus.HEALTHY,
            message="Redis OK"
        )

    async def api_health_check():
        await asyncio.sleep(0.01)
        return HealthCheckResult(
            name="api",
            status=HealthStatus.HEALTHY,
            message="API responding"
        )

    dashboard.register_check(
        "database",
        db_health_check,
        CheckType.READINESS,
        interval=30.0,
        critical=True
    )
    print("   Registered: database (readiness, critical)")

    dashboard.register_check(
        "cache",
        cache_health_check,
        CheckType.READINESS,
        interval=30.0
    )
    print("   Registered: cache (readiness)")

    dashboard.register_check(
        "api",
        api_health_check,
        CheckType.LIVENESS,
        interval=10.0
    )
    print("   Registered: api (liveness)")
    print()

    # 3. Run Health Checks
    print("3. RUN HEALTH CHECKS:")
    print("-" * 40)

    results = await dashboard.run_all_checks()

    for name, result in results.items():
        status = "✓" if result.status == HealthStatus.HEALTHY else "✗"
        print(f"   [{status}] {name}: {result.status.value}")
        print(f"       Duration: {result.duration_ms:.2f}ms")
    print()

    # 4. Update Resources
    print("4. UPDATE RESOURCES:")
    print("-" * 40)

    dashboard.resources.update(ResourceType.CPU, 45.5, 100.0, "%")
    dashboard.resources.update(ResourceType.MEMORY, 2048, 4096, "MB")
    dashboard.resources.update(ResourceType.DISK, 75.0, 100.0, "%")

    for rt, usage in dashboard.resources.get_all_usage().items():
        print(f"   {rt.value}: {usage.current}{usage.unit} / {usage.limit}{usage.unit}")
        print(f"       Utilization: {usage.utilization:.1f}%")
    print()

    # 5. Record Metrics
    print("5. RECORD METRICS:")
    print("-" * 40)

    for i in range(10):
        dashboard.metrics.record("response_time", 50 + i * 5, MetricType.GAUGE, unit="ms")
        dashboard.metrics.record("request_count", i + 1, MetricType.COUNTER)

    response_stats = dashboard.metrics.get_stats("response_time")
    print(f"   response_time:")
    print(f"       Min: {response_stats['min']}ms")
    print(f"       Max: {response_stats['max']}ms")
    print(f"       Avg: {response_stats['avg']:.1f}ms")
    print()

    # 6. Create Alerts
    print("6. CREATE ALERTS:")
    print("-" * 40)

    alert1 = await dashboard.alerts.create(
        "High CPU Usage",
        "CPU usage exceeded 80% threshold",
        AlertSeverity.WARNING,
        source="resource_monitor"
    )
    print(f"   Created: {alert1.name} ({alert1.severity.value})")

    alert2 = await dashboard.alerts.create(
        "Database Connection Pool Low",
        "Connection pool at 90% capacity",
        AlertSeverity.ERROR,
        source="database"
    )
    print(f"   Created: {alert2.name} ({alert2.severity.value})")

    active = dashboard.alerts.get_active()
    print(f"   Active alerts: {len(active)}")
    print()

    # 7. Acknowledge Alert
    print("7. ACKNOWLEDGE ALERT:")
    print("-" * 40)

    dashboard.alerts.acknowledge(alert1.alert_id, "admin")
    print(f"   Acknowledged: {alert1.name}")
    print(f"   Status: {alert1.status.value}")
    print()

    # 8. Define SLA
    print("8. DEFINE SLA:")
    print("-" * 40)

    uptime_sla = dashboard.sla.define(
        "API Uptime",
        target=99.9,
        metric="uptime",
        window_hours=720
    )
    print(f"   Defined: {uptime_sla.name}")
    print(f"   Target: {uptime_sla.target}%")

    # Record measurements
    for i in range(100):
        dashboard.sla.record(uptime_sla.sla_id, 1.0, success=True)

    dashboard.sla.record(uptime_sla.sla_id, 0.0, success=False)  # One failure

    sla_status = dashboard.sla.get_status(uptime_sla.sla_id)
    print(f"   Current: {sla_status['current']:.2f}%")
    print(f"   Compliant: {sla_status['compliant']}")
    print()

    # 9. Add Dashboard Widgets
    print("9. ADD DASHBOARD WIDGETS:")
    print("-" * 40)

    dashboard.add_widget(
        "System Health",
        "status",
        "health_status",
        position=(0, 0),
        size=(2, 1)
    )
    print("   Added: System Health (status)")

    dashboard.add_widget(
        "CPU Usage",
        "gauge",
        "resource_cpu",
        config={"max": 100, "thresholds": [60, 80]},
        position=(0, 1)
    )
    print("   Added: CPU Usage (gauge)")

    dashboard.add_widget(
        "Response Time",
        "chart",
        "metric_response_time",
        config={"period": "1h", "type": "line"},
        position=(1, 1),
        size=(2, 1)
    )
    print("   Added: Response Time (chart)")
    print()

    # 10. Get Liveness
    print("10. LIVENESS CHECK:")
    print("-" * 40)

    liveness = await dashboard.get_liveness()
    status = "✓" if liveness['alive'] else "✗"
    print(f"   [{status}] Alive: {liveness['alive']}")
    print()

    # 11. Get Readiness
    print("11. READINESS CHECK:")
    print("-" * 40)

    readiness = await dashboard.get_readiness()
    status = "✓" if readiness['ready'] else "✗"
    print(f"   [{status}] Ready: {readiness['ready']}")
    print()

    # 12. Overall Health
    print("12. OVERALL HEALTH:")
    print("-" * 40)

    health = await dashboard.get_health()

    print(f"   Status: {health['status']}")
    print(f"   Checks: {len(health['checks'])}")
    print(f"   Resources: {len(health['resources'])}")
    print(f"   Active alerts: {health['alerts']['active']}")
    print()

    # 13. Dashboard Data
    print("13. DASHBOARD DATA:")
    print("-" * 40)

    data = await dashboard.get_dashboard_data()

    print(f"   Health status: {data['health']['status']}")
    print(f"   Alert stats: {data['alerts']}")
    print(f"   SLAs: {len(data['slas'])}")
    print()

    # 14. Statistics
    print("14. STATISTICS:")
    print("-" * 40)

    stats = dashboard.get_stats()

    print(f"   Services: {stats['services']}")
    print(f"   Checks: {stats['checks']}")
    print(f"   Widgets: {stats['widgets']}")
    print(f"   Active alerts: {stats['active_alerts']}")
    print(f"   SLAs: {stats['slas']}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Health Dashboard System Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
