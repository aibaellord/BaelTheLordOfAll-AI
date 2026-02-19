"""
BAEL Monitoring Engine
======================

Comprehensive monitoring, metrics, alerting, and observability.

Features:
- Real-time metrics collection
- Custom alert rules
- Health checks
- Dashboard generation
- Performance tracking

"Omniscient observation across all dimensions." — Ba'el
"""

import asyncio
import hashlib
import json
import logging
import os
import statistics
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger("BAEL.Monitoring")


# =============================================================================
# ENUMS
# =============================================================================

class MetricType(Enum):
    """Types of metrics."""
    COUNTER = "counter"      # Monotonically increasing
    GAUGE = "gauge"          # Point-in-time value
    HISTOGRAM = "histogram"  # Distribution
    SUMMARY = "summary"      # Quantiles
    TIMER = "timer"          # Duration measurements


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = 1
    WARNING = 2
    CRITICAL = 3
    EMERGENCY = 4


class AlertStatus(Enum):
    """Alert status."""
    PENDING = "pending"
    FIRING = "firing"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"
    SILENCED = "silenced"


class HealthStatus(Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class AggregationType(Enum):
    """Aggregation types for metrics."""
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    P50 = "p50"
    P90 = "p90"
    P95 = "p95"
    P99 = "p99"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Metric:
    """A metric data point."""
    name: str
    metric_type: MetricType
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    labels: Dict[str, str] = field(default_factory=dict)
    unit: Optional[str] = None
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.metric_type.value,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "labels": self.labels,
            "unit": self.unit
        }


@dataclass
class Alert:
    """An alert event."""
    id: str
    name: str
    severity: AlertSeverity
    status: AlertStatus
    message: str
    metric_name: Optional[str] = None
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    fired_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None


@dataclass
class AlertRule:
    """An alert rule definition."""
    name: str
    metric_name: str
    condition: str  # "gt", "lt", "eq", "ne", "gte", "lte"
    threshold: float
    severity: AlertSeverity
    message_template: str
    for_duration: Optional[timedelta] = None  # How long condition must be true
    labels: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True

    def evaluate(self, value: float) -> bool:
        """Evaluate rule against value."""
        if self.condition == "gt":
            return value > self.threshold
        elif self.condition == "lt":
            return value < self.threshold
        elif self.condition == "eq":
            return abs(value - self.threshold) < 0.0001
        elif self.condition == "ne":
            return abs(value - self.threshold) >= 0.0001
        elif self.condition == "gte":
            return value >= self.threshold
        elif self.condition == "lte":
            return value <= self.threshold
        return False


@dataclass
class HealthCheck:
    """A health check definition."""
    name: str
    check_fn: Callable[[], bool]
    interval_seconds: float = 30.0
    timeout_seconds: float = 10.0
    failure_threshold: int = 3
    recovery_threshold: int = 2
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class HealthResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    message: str = ""
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthReport:
    """Overall health report."""
    overall_status: HealthStatus
    checks: List[HealthResult]
    timestamp: datetime = field(default_factory=datetime.now)
    uptime_seconds: float = 0.0
    version: str = "3.0.0"


@dataclass
class MonitoringConfig:
    """Monitoring engine configuration."""
    metrics_retention_hours: int = 24
    metrics_resolution_seconds: int = 10
    alert_check_interval_seconds: float = 15.0
    health_check_interval_seconds: float = 30.0
    max_metrics_per_name: int = 10000
    storage_path: Path = field(default_factory=lambda: Path("data/monitoring"))


# =============================================================================
# METRICS COLLECTOR
# =============================================================================

class MetricsCollector:
    """Collects and stores metrics."""

    def __init__(self, config: MonitoringConfig):
        self.config = config
        self._metrics: Dict[str, deque] = {}
        self._counters: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = {}
        self._lock = threading.Lock()
        self._callbacks: List[Callable[[Metric], None]] = []

    def record(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        labels: Optional[Dict[str, str]] = None,
        unit: Optional[str] = None
    ):
        """Record a metric."""
        metric = Metric(
            name=name,
            metric_type=metric_type,
            value=value,
            labels=labels or {},
            unit=unit
        )

        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = deque(maxlen=self.config.max_metrics_per_name)
            self._metrics[name].append(metric)

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(metric)
            except Exception as e:
                logger.error(f"Metric callback error: {e}")

    def counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Increment a counter."""
        key = f"{name}:{json.dumps(labels or {}, sort_keys=True)}"

        with self._lock:
            if key not in self._counters:
                self._counters[key] = 0.0
            self._counters[key] += value
            total = self._counters[key]

        self.record(name, total, MetricType.COUNTER, labels)

    def gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None, unit: Optional[str] = None):
        """Set a gauge value."""
        self.record(name, value, MetricType.GAUGE, labels, unit)

    def histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a histogram observation."""
        key = f"{name}:{json.dumps(labels or {}, sort_keys=True)}"

        with self._lock:
            if key not in self._histograms:
                self._histograms[key] = []
            self._histograms[key].append(value)

            # Keep only recent values
            if len(self._histograms[key]) > 10000:
                self._histograms[key] = self._histograms[key][-5000:]

        self.record(name, value, MetricType.HISTOGRAM, labels)

    def timer(self, name: str):
        """Context manager for timing operations."""
        return MetricTimer(self, name)

    def get_latest(self, name: str, labels: Optional[Dict[str, str]] = None) -> Optional[Metric]:
        """Get latest metric value."""
        with self._lock:
            if name in self._metrics and self._metrics[name]:
                return self._metrics[name][-1]
        return None

    def get_history(
        self,
        name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Metric]:
        """Get metric history."""
        with self._lock:
            if name not in self._metrics:
                return []

            metrics = list(self._metrics[name])

        # Filter by time range
        if start_time:
            metrics = [m for m in metrics if m.timestamp >= start_time]
        if end_time:
            metrics = [m for m in metrics if m.timestamp <= end_time]

        return metrics[-limit:]

    def aggregate(
        self,
        name: str,
        aggregation: AggregationType,
        window_seconds: Optional[float] = None
    ) -> Optional[float]:
        """Aggregate metric values."""
        with self._lock:
            if name not in self._metrics:
                return None

            values = []
            cutoff = None
            if window_seconds:
                cutoff = datetime.now() - timedelta(seconds=window_seconds)

            for metric in self._metrics[name]:
                if cutoff and metric.timestamp < cutoff:
                    continue
                values.append(metric.value)

        if not values:
            return None

        if aggregation == AggregationType.SUM:
            return sum(values)
        elif aggregation == AggregationType.AVG:
            return statistics.mean(values)
        elif aggregation == AggregationType.MIN:
            return min(values)
        elif aggregation == AggregationType.MAX:
            return max(values)
        elif aggregation == AggregationType.COUNT:
            return len(values)
        elif aggregation == AggregationType.P50:
            return self._percentile(values, 50)
        elif aggregation == AggregationType.P90:
            return self._percentile(values, 90)
        elif aggregation == AggregationType.P95:
            return self._percentile(values, 95)
        elif aggregation == AggregationType.P99:
            return self._percentile(values, 99)

        return None

    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile."""
        sorted_values = sorted(values)
        k = (len(sorted_values) - 1) * percentile / 100
        f = int(k)
        c = f + 1 if f + 1 < len(sorted_values) else f
        return sorted_values[f] + (k - f) * (sorted_values[c] - sorted_values[f])

    def list_metrics(self) -> List[str]:
        """List all metric names."""
        with self._lock:
            return list(self._metrics.keys())

    def add_callback(self, callback: Callable[[Metric], None]):
        """Add a callback for new metrics."""
        self._callbacks.append(callback)

    def cleanup(self, older_than_hours: Optional[int] = None):
        """Clean up old metrics."""
        hours = older_than_hours or self.config.metrics_retention_hours
        cutoff = datetime.now() - timedelta(hours=hours)

        with self._lock:
            for name in self._metrics:
                while self._metrics[name] and self._metrics[name][0].timestamp < cutoff:
                    self._metrics[name].popleft()


class MetricTimer:
    """Context manager for timing operations."""

    def __init__(self, collector: MetricsCollector, name: str, labels: Optional[Dict[str, str]] = None):
        self.collector = collector
        self.name = name
        self.labels = labels or {}
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        self.collector.record(
            f"{self.name}_duration_ms",
            duration_ms,
            MetricType.TIMER,
            self.labels,
            "ms"
        )
        return False


# =============================================================================
# ALERT MANAGER
# =============================================================================

class AlertManager:
    """Manages alerts and alert rules."""

    def __init__(self, config: MonitoringConfig, metrics: MetricsCollector):
        self.config = config
        self.metrics = metrics

        self._rules: Dict[str, AlertRule] = {}
        self._alerts: Dict[str, Alert] = {}
        self._pending_alerts: Dict[str, Tuple[datetime, AlertRule, float]] = {}
        self._callbacks: List[Callable[[Alert], None]] = []
        self._running = False

    def add_rule(self, rule: AlertRule):
        """Add an alert rule."""
        self._rules[rule.name] = rule

    def remove_rule(self, name: str):
        """Remove an alert rule."""
        if name in self._rules:
            del self._rules[name]

    def get_rules(self) -> List[AlertRule]:
        """Get all alert rules."""
        return list(self._rules.values())

    def fire_alert(self, rule: AlertRule, value: float):
        """Fire an alert."""
        alert_id = hashlib.md5(
            f"{rule.name}{time.time()}".encode()
        ).hexdigest()[:12]

        message = rule.message_template.replace("{value}", str(value))
        message = message.replace("{threshold}", str(rule.threshold))
        message = message.replace("{metric}", rule.metric_name)

        alert = Alert(
            id=alert_id,
            name=rule.name,
            severity=rule.severity,
            status=AlertStatus.FIRING,
            message=message,
            metric_name=rule.metric_name,
            metric_value=value,
            threshold=rule.threshold,
            labels=rule.labels
        )

        self._alerts[alert_id] = alert

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")

        return alert

    def resolve_alert(self, alert_id: str):
        """Resolve an alert."""
        if alert_id in self._alerts:
            self._alerts[alert_id].status = AlertStatus.RESOLVED
            self._alerts[alert_id].resolved_at = datetime.now()

    def acknowledge_alert(self, alert_id: str, user: str):
        """Acknowledge an alert."""
        if alert_id in self._alerts:
            self._alerts[alert_id].status = AlertStatus.ACKNOWLEDGED
            self._alerts[alert_id].acknowledged_by = user

    def silence_alert(self, alert_id: str):
        """Silence an alert."""
        if alert_id in self._alerts:
            self._alerts[alert_id].status = AlertStatus.SILENCED

    def get_alerts(
        self,
        status: Optional[AlertStatus] = None,
        severity: Optional[AlertSeverity] = None,
        limit: int = 100
    ) -> List[Alert]:
        """Get alerts."""
        alerts = list(self._alerts.values())

        if status:
            alerts = [a for a in alerts if a.status == status]

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        # Sort by severity (desc) then time (desc)
        alerts.sort(key=lambda a: (-a.severity.value, a.fired_at), reverse=True)

        return alerts[:limit]

    def add_callback(self, callback: Callable[[Alert], None]):
        """Add alert callback."""
        self._callbacks.append(callback)

    async def start(self):
        """Start alert checking."""
        self._running = True
        while self._running:
            await self._check_rules()
            await asyncio.sleep(self.config.alert_check_interval_seconds)

    async def stop(self):
        """Stop alert checking."""
        self._running = False

    async def _check_rules(self):
        """Check all alert rules."""
        for rule in self._rules.values():
            if not rule.enabled:
                continue

            metric = self.metrics.get_latest(rule.metric_name)
            if not metric:
                continue

            if rule.evaluate(metric.value):
                # Condition is true
                if rule.for_duration:
                    # Need to wait for duration
                    if rule.name not in self._pending_alerts:
                        self._pending_alerts[rule.name] = (datetime.now(), rule, metric.value)
                    else:
                        start_time, _, _ = self._pending_alerts[rule.name]
                        if datetime.now() - start_time >= rule.for_duration:
                            self.fire_alert(rule, metric.value)
                            del self._pending_alerts[rule.name]
                else:
                    # Fire immediately
                    # Check if already firing for this rule
                    already_firing = any(
                        a.name == rule.name and a.status == AlertStatus.FIRING
                        for a in self._alerts.values()
                    )
                    if not already_firing:
                        self.fire_alert(rule, metric.value)
            else:
                # Condition is false, remove from pending
                if rule.name in self._pending_alerts:
                    del self._pending_alerts[rule.name]


# =============================================================================
# HEALTH MONITOR
# =============================================================================

class HealthMonitor:
    """Monitors system health."""

    def __init__(self, config: MonitoringConfig):
        self.config = config
        self._checks: Dict[str, HealthCheck] = {}
        self._results: Dict[str, HealthResult] = {}
        self._failure_counts: Dict[str, int] = {}
        self._recovery_counts: Dict[str, int] = {}
        self._start_time = datetime.now()
        self._running = False

        # Register default checks
        self._register_defaults()

    def _register_defaults(self):
        """Register default health checks."""
        # Memory check
        self.register(HealthCheck(
            name="memory",
            check_fn=self._check_memory,
            interval_seconds=60.0
        ))

        # Disk check
        self.register(HealthCheck(
            name="disk",
            check_fn=self._check_disk,
            interval_seconds=300.0
        ))

    def _check_memory(self) -> bool:
        """Check memory usage."""
        try:
            import resource
            usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            # On macOS, this is in bytes; on Linux, it's in KB
            max_mb = 2048  # 2GB threshold
            return (usage / 1024 / 1024) < max_mb
        except:
            return True  # Assume healthy if we can't check

    def _check_disk(self) -> bool:
        """Check disk space."""
        try:
            import shutil
            usage = shutil.disk_usage("/")
            free_percent = usage.free / usage.total * 100
            return free_percent > 10  # More than 10% free
        except:
            return True

    def register(self, check: HealthCheck):
        """Register a health check."""
        self._checks[check.name] = check
        self._failure_counts[check.name] = 0
        self._recovery_counts[check.name] = 0
        self._results[check.name] = HealthResult(
            name=check.name,
            status=HealthStatus.UNKNOWN,
            message="Not yet checked"
        )

    def unregister(self, name: str):
        """Unregister a health check."""
        if name in self._checks:
            del self._checks[name]

    async def check(self, name: str) -> HealthResult:
        """Run a specific health check."""
        if name not in self._checks:
            return HealthResult(
                name=name,
                status=HealthStatus.UNKNOWN,
                message="Check not found"
            )

        check = self._checks[name]
        start_time = time.time()

        try:
            # Run check with timeout
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, check.check_fn),
                timeout=check.timeout_seconds
            )

            duration_ms = (time.time() - start_time) * 1000

            if result:
                self._failure_counts[name] = 0
                self._recovery_counts[name] += 1

                if self._recovery_counts[name] >= check.recovery_threshold:
                    status = HealthStatus.HEALTHY
                else:
                    status = self._results[name].status  # Keep previous status

                health_result = HealthResult(
                    name=name,
                    status=status,
                    message="Check passed",
                    duration_ms=duration_ms
                )
            else:
                self._recovery_counts[name] = 0
                self._failure_counts[name] += 1

                if self._failure_counts[name] >= check.failure_threshold:
                    status = HealthStatus.UNHEALTHY
                else:
                    status = HealthStatus.DEGRADED

                health_result = HealthResult(
                    name=name,
                    status=status,
                    message=f"Check failed ({self._failure_counts[name]} failures)",
                    duration_ms=duration_ms
                )

        except asyncio.TimeoutError:
            health_result = HealthResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check timed out after {check.timeout_seconds}s"
            )
            self._failure_counts[name] += 1

        except Exception as e:
            health_result = HealthResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check error: {str(e)}"
            )
            self._failure_counts[name] += 1

        self._results[name] = health_result
        return health_result

    async def check_all(self) -> HealthReport:
        """Run all health checks."""
        results = []

        for name in self._checks:
            result = await self.check(name)
            results.append(result)

        # Determine overall status
        statuses = [r.status for r in results]

        if all(s == HealthStatus.HEALTHY for s in statuses):
            overall_status = HealthStatus.HEALTHY
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            overall_status = HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.UNKNOWN

        uptime = (datetime.now() - self._start_time).total_seconds()

        return HealthReport(
            overall_status=overall_status,
            checks=results,
            uptime_seconds=uptime
        )

    def get_report(self) -> HealthReport:
        """Get current health report without running checks."""
        results = list(self._results.values())

        statuses = [r.status for r in results]

        if all(s == HealthStatus.HEALTHY for s in statuses):
            overall_status = HealthStatus.HEALTHY
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            overall_status = HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.UNKNOWN

        uptime = (datetime.now() - self._start_time).total_seconds()

        return HealthReport(
            overall_status=overall_status,
            checks=results,
            uptime_seconds=uptime
        )

    async def start(self):
        """Start continuous health monitoring."""
        self._running = True
        while self._running:
            await self.check_all()
            await asyncio.sleep(self.config.health_check_interval_seconds)

    async def stop(self):
        """Stop health monitoring."""
        self._running = False


# =============================================================================
# DASHBOARD MANAGER
# =============================================================================

class DashboardManager:
    """Manages monitoring dashboards."""

    def __init__(
        self,
        metrics: MetricsCollector,
        alerts: AlertManager,
        health: HealthMonitor
    ):
        self.metrics = metrics
        self.alerts = alerts
        self.health = health
        self._dashboards: Dict[str, Dict[str, Any]] = {}

        # Create default dashboard
        self._create_default_dashboard()

    def _create_default_dashboard(self):
        """Create the default system dashboard."""
        self._dashboards["system"] = {
            "name": "System Overview",
            "description": "BAEL system monitoring dashboard",
            "panels": [
                {
                    "id": "health",
                    "type": "status",
                    "title": "System Health",
                    "data_source": "health"
                },
                {
                    "id": "alerts",
                    "type": "alerts",
                    "title": "Active Alerts",
                    "data_source": "alerts",
                    "filters": {"status": "firing"}
                },
                {
                    "id": "metrics_list",
                    "type": "list",
                    "title": "Key Metrics",
                    "data_source": "metrics"
                }
            ]
        }

    def create_dashboard(
        self,
        name: str,
        description: str = "",
        panels: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Create a new dashboard."""
        dashboard_id = hashlib.md5(name.encode()).hexdigest()[:8]

        self._dashboards[dashboard_id] = {
            "id": dashboard_id,
            "name": name,
            "description": description,
            "panels": panels or [],
            "created_at": datetime.now().isoformat()
        }

        return dashboard_id

    def get_dashboard(self, dashboard_id: str) -> Optional[Dict[str, Any]]:
        """Get a dashboard by ID."""
        return self._dashboards.get(dashboard_id)

    def list_dashboards(self) -> List[Dict[str, Any]]:
        """List all dashboards."""
        return [
            {"id": k, "name": v.get("name", k)}
            for k, v in self._dashboards.items()
        ]

    def delete_dashboard(self, dashboard_id: str):
        """Delete a dashboard."""
        if dashboard_id in self._dashboards and dashboard_id != "system":
            del self._dashboards[dashboard_id]

    def get_dashboard_data(self, dashboard_id: str) -> Dict[str, Any]:
        """Get dashboard with populated data."""
        dashboard = self._dashboards.get(dashboard_id)
        if not dashboard:
            return {}

        result = {**dashboard}

        for panel in result.get("panels", []):
            panel["data"] = self._get_panel_data(panel)

        return result

    def _get_panel_data(self, panel: Dict[str, Any]) -> Any:
        """Get data for a panel."""
        data_source = panel.get("data_source")

        if data_source == "health":
            report = self.health.get_report()
            return {
                "overall_status": report.overall_status.value,
                "uptime_seconds": report.uptime_seconds,
                "checks": [
                    {
                        "name": c.name,
                        "status": c.status.value,
                        "message": c.message
                    }
                    for c in report.checks
                ]
            }

        elif data_source == "alerts":
            filters = panel.get("filters", {})
            status = None
            if "status" in filters:
                status = AlertStatus(filters["status"])

            alerts = self.alerts.get_alerts(status=status, limit=10)
            return [
                {
                    "id": a.id,
                    "name": a.name,
                    "severity": a.severity.name,
                    "message": a.message,
                    "fired_at": a.fired_at.isoformat()
                }
                for a in alerts
            ]

        elif data_source == "metrics":
            metric_names = self.metrics.list_metrics()
            return [
                {
                    "name": name,
                    "latest": self.metrics.get_latest(name).value if self.metrics.get_latest(name) else None
                }
                for name in metric_names[:20]  # Limit to 20
            ]

        return None


# =============================================================================
# MONITORING ENGINE
# =============================================================================

class MonitoringEngine:
    """Main monitoring engine."""

    def __init__(self, config: Optional[MonitoringConfig] = None):
        self.config = config or MonitoringConfig()
        self.config.storage_path.mkdir(parents=True, exist_ok=True)

        self.metrics = MetricsCollector(self.config)
        self.alerts = AlertManager(self.config, self.metrics)
        self.health = HealthMonitor(self.config)
        self.dashboards = DashboardManager(self.metrics, self.alerts, self.health)

        self._running = False
        self._tasks: List[asyncio.Task] = []

        # Register default alert rules
        self._register_default_rules()

    def _register_default_rules(self):
        """Register default alert rules."""
        # High error rate
        self.alerts.add_rule(AlertRule(
            name="high_error_rate",
            metric_name="error_rate",
            condition="gt",
            threshold=0.1,  # 10%
            severity=AlertSeverity.CRITICAL,
            message_template="Error rate is {value} (threshold: {threshold})"
        ))

        # High latency
        self.alerts.add_rule(AlertRule(
            name="high_latency",
            metric_name="request_latency_p99",
            condition="gt",
            threshold=1000,  # 1 second
            severity=AlertSeverity.WARNING,
            message_template="P99 latency is {value}ms (threshold: {threshold}ms)"
        ))

    async def start(self):
        """Start the monitoring engine."""
        self._running = True

        # Start alert checking
        self._tasks.append(asyncio.create_task(self.alerts.start()))

        # Start health monitoring
        self._tasks.append(asyncio.create_task(self.health.start()))

        # Start metrics cleanup
        self._tasks.append(asyncio.create_task(self._cleanup_loop()))

        logger.info("Monitoring engine started")

    async def stop(self):
        """Stop the monitoring engine."""
        self._running = False

        await self.alerts.stop()
        await self.health.stop()

        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._tasks.clear()
        logger.info("Monitoring engine stopped")

    async def _cleanup_loop(self):
        """Periodic cleanup of old data."""
        while self._running:
            self.metrics.cleanup()
            await asyncio.sleep(3600)  # Every hour

    def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        labels: Optional[Dict[str, str]] = None,
        unit: Optional[str] = None
    ):
        """Record a metric."""
        self.metrics.record(name, value, metric_type, labels, unit)

    def increment(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Increment a counter."""
        self.metrics.counter(name, value, labels)

    def time(self, name: str):
        """Get a timer context manager."""
        return self.metrics.timer(name)

    def get_status(self) -> Dict[str, Any]:
        """Get monitoring status."""
        health_report = self.health.get_report()

        return {
            "running": self._running,
            "health": {
                "status": health_report.overall_status.value,
                "uptime_seconds": health_report.uptime_seconds
            },
            "metrics": {
                "count": len(self.metrics.list_metrics()),
                "names": self.metrics.list_metrics()[:10]
            },
            "alerts": {
                "firing": len(self.alerts.get_alerts(status=AlertStatus.FIRING)),
                "total": len(self.alerts._alerts)
            },
            "dashboards": len(self.dashboards._dashboards)
        }


# =============================================================================
# CONVENIENCE INSTANCE
# =============================================================================

monitoring_engine = MonitoringEngine()
