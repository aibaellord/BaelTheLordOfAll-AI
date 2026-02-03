#!/usr/bin/env python3
"""
BAEL - Performance Monitor
Real-time system monitoring and performance analytics.

This module implements comprehensive performance monitoring
for tracking system health, resource usage, latencies,
and generating actionable insights.

Features:
- Real-time metrics collection
- Multi-dimensional monitoring
- Threshold alerts
- Anomaly detection
- Trend analysis
- Performance profiling
- Resource tracking
- Latency monitoring
- Throughput measurement
- Health scoring
- Dashboard generation
- Historical analysis
"""

import asyncio
import logging
import math
import statistics
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    TypeVar, Union)
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class MetricType(Enum):
    """Types of metrics."""
    COUNTER = "counter"         # Monotonically increasing
    GAUGE = "gauge"             # Point-in-time value
    HISTOGRAM = "histogram"     # Distribution of values
    TIMER = "timer"             # Duration measurements
    RATE = "rate"               # Rate of change


class AlertSeverity(Enum):
    """Severity levels for alerts."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class TrendDirection(Enum):
    """Direction of metric trend."""
    UP = "up"
    DOWN = "down"
    STABLE = "stable"
    VOLATILE = "volatile"


class AggregationType(Enum):
    """Types of metric aggregation."""
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    P50 = "p50"
    P95 = "p95"
    P99 = "p99"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class MetricValue:
    """A single metric measurement."""
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class MetricDefinition:
    """Definition of a metric."""
    name: str
    type: MetricType
    description: str = ""
    unit: str = ""
    labels: List[str] = field(default_factory=list)
    retention_hours: int = 24


@dataclass
class Metric:
    """A complete metric with history."""
    definition: MetricDefinition
    values: deque = field(default_factory=lambda: deque(maxlen=10000))
    current_value: float = 0.0
    min_value: float = float('inf')
    max_value: float = float('-inf')
    sum_value: float = 0.0
    count: int = 0

    def record(self, value: float, labels: Dict[str, str] = None) -> None:
        """Record a new value."""
        mv = MetricValue(value=value, labels=labels or {})
        self.values.append(mv)

        self.current_value = value
        self.min_value = min(self.min_value, value)
        self.max_value = max(self.max_value, value)
        self.sum_value += value
        self.count += 1

    @property
    def avg_value(self) -> float:
        """Get average value."""
        if self.count == 0:
            return 0.0
        return self.sum_value / self.count

    def get_percentile(self, p: float) -> float:
        """Get percentile value."""
        if not self.values:
            return 0.0

        sorted_values = sorted(v.value for v in self.values)
        index = int(len(sorted_values) * p / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]


@dataclass
class ThresholdConfig:
    """Configuration for metric thresholds."""
    metric_name: str
    warning_threshold: Optional[float] = None
    error_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None
    comparison: str = "above"  # "above" or "below"


@dataclass
class Alert:
    """A performance alert."""
    id: str = field(default_factory=lambda: str(uuid4()))
    metric_name: str = ""
    severity: AlertSeverity = AlertSeverity.WARNING
    message: str = ""
    value: float = 0.0
    threshold: float = 0.0
    triggered_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    acknowledged: bool = False


@dataclass
class HealthCheck:
    """A health check result."""
    name: str
    status: HealthStatus = HealthStatus.UNKNOWN
    message: str = ""
    latency_ms: float = 0.0
    checked_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceProfile:
    """A performance profile capture."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0
    metrics: Dict[str, float] = field(default_factory=dict)
    spans: List[Dict[str, Any]] = field(default_factory=list)


# =============================================================================
# METRIC COLLECTORS
# =============================================================================

class MetricCollector(ABC):
    """Base class for metric collection."""

    @abstractmethod
    async def collect(self) -> Dict[str, float]:
        """Collect metrics."""
        pass


class SystemMetricCollector(MetricCollector):
    """
    Collects system-level metrics.

    Simulates CPU, memory, disk, network metrics.
    """

    def __init__(self):
        self.base_cpu = 20.0
        self.base_memory = 45.0

    async def collect(self) -> Dict[str, float]:
        """Collect system metrics."""
        import random

        return {
            "cpu_percent": self.base_cpu + random.uniform(-5, 10),
            "memory_percent": self.base_memory + random.uniform(-3, 5),
            "disk_percent": 55.0 + random.uniform(-2, 2),
            "network_bytes_sent": random.randint(1000, 10000),
            "network_bytes_recv": random.randint(5000, 50000),
            "open_files": random.randint(50, 200),
            "thread_count": random.randint(10, 50)
        }


class ApplicationMetricCollector(MetricCollector):
    """
    Collects application-level metrics.

    Tracks requests, latencies, errors.
    """

    def __init__(self):
        self.request_count = 0
        self.error_count = 0

    async def collect(self) -> Dict[str, float]:
        """Collect application metrics."""
        import random

        # Simulate activity
        new_requests = random.randint(10, 100)
        new_errors = random.randint(0, 2)

        self.request_count += new_requests
        self.error_count += new_errors

        return {
            "requests_total": self.request_count,
            "errors_total": self.error_count,
            "requests_per_second": new_requests,
            "error_rate": new_errors / max(new_requests, 1),
            "response_time_ms": random.uniform(10, 100),
            "active_connections": random.randint(5, 50),
            "queue_depth": random.randint(0, 20)
        }


class AgentMetricCollector(MetricCollector):
    """
    Collects BAEL agent metrics.

    Tracks agent activity and performance.
    """

    def __init__(self):
        self.tasks_completed = 0
        self.tokens_used = 0

    async def collect(self) -> Dict[str, float]:
        """Collect agent metrics."""
        import random

        new_tasks = random.randint(1, 10)
        new_tokens = random.randint(100, 1000)

        self.tasks_completed += new_tasks
        self.tokens_used += new_tokens

        return {
            "active_agents": random.randint(3, 15),
            "tasks_completed": self.tasks_completed,
            "tasks_pending": random.randint(0, 30),
            "tokens_used": self.tokens_used,
            "council_decisions": random.randint(0, 5),
            "engine_operations": random.randint(5, 25),
            "cache_hit_rate": random.uniform(0.6, 0.95)
        }


# =============================================================================
# ANOMALY DETECTOR
# =============================================================================

class AnomalyDetector:
    """
    Detects anomalies in metric values.

    Uses statistical methods for anomaly detection.
    """

    def __init__(
        self,
        std_threshold: float = 3.0,
        window_size: int = 100
    ):
        self.std_threshold = std_threshold
        self.window_size = window_size
        self.baselines: Dict[str, Dict[str, float]] = {}

    def update_baseline(
        self,
        metric_name: str,
        values: List[float]
    ) -> None:
        """Update baseline statistics for a metric."""
        if len(values) < 10:
            return

        self.baselines[metric_name] = {
            "mean": statistics.mean(values),
            "std": statistics.stdev(values) if len(values) > 1 else 0,
            "median": statistics.median(values)
        }

    def is_anomaly(
        self,
        metric_name: str,
        value: float
    ) -> Tuple[bool, float]:
        """Check if value is anomalous. Returns (is_anomaly, z_score)."""
        baseline = self.baselines.get(metric_name)

        if not baseline or baseline["std"] == 0:
            return False, 0.0

        z_score = abs(value - baseline["mean"]) / baseline["std"]
        is_anomaly = z_score > self.std_threshold

        return is_anomaly, z_score

    def detect_trend(
        self,
        values: List[float],
        window: int = 10
    ) -> TrendDirection:
        """Detect trend direction."""
        if len(values) < window * 2:
            return TrendDirection.STABLE

        recent = values[-window:]
        previous = values[-window*2:-window]

        recent_avg = statistics.mean(recent)
        previous_avg = statistics.mean(previous)

        # Calculate coefficient of variation for volatility
        if len(values) > window:
            std = statistics.stdev(values[-window:])
            cv = std / recent_avg if recent_avg > 0 else 0
            if cv > 0.5:
                return TrendDirection.VOLATILE

        diff_percent = (recent_avg - previous_avg) / previous_avg if previous_avg > 0 else 0

        if diff_percent > 0.1:
            return TrendDirection.UP
        elif diff_percent < -0.1:
            return TrendDirection.DOWN
        else:
            return TrendDirection.STABLE


# =============================================================================
# HEALTH CHECKER
# =============================================================================

class HealthChecker:
    """
    Performs health checks on system components.

    Aggregates health status across components.
    """

    def __init__(self):
        self.checks: Dict[str, Callable] = {}
        self.results: Dict[str, HealthCheck] = {}

    def register_check(
        self,
        name: str,
        check_func: Callable[[], Tuple[HealthStatus, str]]
    ) -> None:
        """Register a health check."""
        self.checks[name] = check_func

    async def run_check(self, name: str) -> HealthCheck:
        """Run a specific health check."""
        check_func = self.checks.get(name)
        if not check_func:
            return HealthCheck(
                name=name,
                status=HealthStatus.UNKNOWN,
                message="Check not found"
            )

        start_time = time.time()

        try:
            if asyncio.iscoroutinefunction(check_func):
                status, message = await check_func()
            else:
                status, message = check_func()
        except Exception as e:
            status = HealthStatus.UNHEALTHY
            message = str(e)

        latency = (time.time() - start_time) * 1000

        result = HealthCheck(
            name=name,
            status=status,
            message=message,
            latency_ms=latency
        )

        self.results[name] = result
        return result

    async def run_all_checks(self) -> Dict[str, HealthCheck]:
        """Run all health checks."""
        for name in self.checks:
            await self.run_check(name)
        return self.results

    def get_overall_status(self) -> HealthStatus:
        """Get aggregated health status."""
        if not self.results:
            return HealthStatus.UNKNOWN

        statuses = [r.status for r in self.results.values()]

        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN


# =============================================================================
# ALERT MANAGER
# =============================================================================

class AlertManager:
    """
    Manages performance alerts.

    Triggers and tracks alerts based on thresholds.
    """

    def __init__(self):
        self.thresholds: Dict[str, ThresholdConfig] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.callbacks: List[Callable[[Alert], None]] = []

    def set_threshold(self, config: ThresholdConfig) -> None:
        """Set threshold for a metric."""
        self.thresholds[config.metric_name] = config

    def add_callback(self, callback: Callable[[Alert], None]) -> None:
        """Add alert callback."""
        self.callbacks.append(callback)

    def check(
        self,
        metric_name: str,
        value: float
    ) -> Optional[Alert]:
        """Check if value triggers an alert."""
        config = self.thresholds.get(metric_name)
        if not config:
            return None

        severity = None
        threshold = None

        # Determine severity
        if config.comparison == "above":
            if config.critical_threshold and value >= config.critical_threshold:
                severity = AlertSeverity.CRITICAL
                threshold = config.critical_threshold
            elif config.error_threshold and value >= config.error_threshold:
                severity = AlertSeverity.ERROR
                threshold = config.error_threshold
            elif config.warning_threshold and value >= config.warning_threshold:
                severity = AlertSeverity.WARNING
                threshold = config.warning_threshold
        else:  # below
            if config.critical_threshold and value <= config.critical_threshold:
                severity = AlertSeverity.CRITICAL
                threshold = config.critical_threshold
            elif config.error_threshold and value <= config.error_threshold:
                severity = AlertSeverity.ERROR
                threshold = config.error_threshold
            elif config.warning_threshold and value <= config.warning_threshold:
                severity = AlertSeverity.WARNING
                threshold = config.warning_threshold

        if severity:
            # Check if alert already exists
            existing = self.active_alerts.get(metric_name)
            if existing and existing.severity == severity:
                return None  # Don't duplicate

            alert = Alert(
                metric_name=metric_name,
                severity=severity,
                message=f"{metric_name} is {config.comparison} threshold: {value:.2f} {'>' if config.comparison == 'above' else '<'} {threshold}",
                value=value,
                threshold=threshold
            )

            self.active_alerts[metric_name] = alert
            self.alert_history.append(alert)

            # Trigger callbacks
            for callback in self.callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    logger.error(f"Alert callback error: {e}")

            return alert
        else:
            # Resolve existing alert
            if metric_name in self.active_alerts:
                existing = self.active_alerts[metric_name]
                existing.resolved_at = datetime.now()
                del self.active_alerts[metric_name]

        return None

    def acknowledge(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        for alert in self.active_alerts.values():
            if alert.id == alert_id:
                alert.acknowledged = True
                return True
        return False

    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts."""
        return list(self.active_alerts.values())


# =============================================================================
# PERFORMANCE MONITOR
# =============================================================================

class PerformanceMonitor:
    """
    The master performance monitor for BAEL.

    Provides comprehensive real-time monitoring,
    alerting, and performance analysis.
    """

    def __init__(
        self,
        collection_interval_seconds: float = 5.0
    ):
        self.metrics: Dict[str, Metric] = {}
        self.collectors: List[MetricCollector] = []
        self.anomaly_detector = AnomalyDetector()
        self.health_checker = HealthChecker()
        self.alert_manager = AlertManager()

        self.collection_interval = collection_interval_seconds
        self.is_running = False
        self.collection_task: Optional[asyncio.Task] = None

        # Profiling
        self.profiles: Dict[str, PerformanceProfile] = {}
        self.active_profiles: Dict[str, PerformanceProfile] = {}

        # Initialize default collectors
        self._init_default_collectors()
        self._init_default_health_checks()

    def _init_default_collectors(self) -> None:
        """Initialize default metric collectors."""
        self.collectors.append(SystemMetricCollector())
        self.collectors.append(ApplicationMetricCollector())
        self.collectors.append(AgentMetricCollector())

    def _init_default_health_checks(self) -> None:
        """Initialize default health checks."""
        def check_cpu():
            cpu = self.get_metric_value("cpu_percent")
            if cpu > 90:
                return HealthStatus.UNHEALTHY, f"CPU critical: {cpu:.1f}%"
            elif cpu > 70:
                return HealthStatus.DEGRADED, f"CPU high: {cpu:.1f}%"
            return HealthStatus.HEALTHY, f"CPU normal: {cpu:.1f}%"

        def check_memory():
            mem = self.get_metric_value("memory_percent")
            if mem > 90:
                return HealthStatus.UNHEALTHY, f"Memory critical: {mem:.1f}%"
            elif mem > 80:
                return HealthStatus.DEGRADED, f"Memory high: {mem:.1f}%"
            return HealthStatus.HEALTHY, f"Memory normal: {mem:.1f}%"

        def check_errors():
            error_rate = self.get_metric_value("error_rate")
            if error_rate > 0.1:
                return HealthStatus.UNHEALTHY, f"Error rate high: {error_rate:.2%}"
            elif error_rate > 0.05:
                return HealthStatus.DEGRADED, f"Error rate elevated: {error_rate:.2%}"
            return HealthStatus.HEALTHY, f"Error rate normal: {error_rate:.2%}"

        self.health_checker.register_check("cpu", check_cpu)
        self.health_checker.register_check("memory", check_memory)
        self.health_checker.register_check("errors", check_errors)

    def register_metric(
        self,
        name: str,
        metric_type: MetricType,
        description: str = "",
        unit: str = ""
    ) -> None:
        """Register a new metric."""
        definition = MetricDefinition(
            name=name,
            type=metric_type,
            description=description,
            unit=unit
        )
        self.metrics[name] = Metric(definition=definition)

    def record(
        self,
        metric_name: str,
        value: float,
        labels: Dict[str, str] = None
    ) -> None:
        """Record a metric value."""
        if metric_name not in self.metrics:
            # Auto-register
            self.register_metric(metric_name, MetricType.GAUGE)

        self.metrics[metric_name].record(value, labels)

        # Check for alerts
        self.alert_manager.check(metric_name, value)

    def get_metric_value(
        self,
        metric_name: str,
        aggregation: AggregationType = AggregationType.AVG
    ) -> float:
        """Get metric value with aggregation."""
        metric = self.metrics.get(metric_name)
        if not metric:
            return 0.0

        if aggregation == AggregationType.AVG:
            return metric.avg_value
        elif aggregation == AggregationType.MIN:
            return metric.min_value if metric.min_value != float('inf') else 0.0
        elif aggregation == AggregationType.MAX:
            return metric.max_value if metric.max_value != float('-inf') else 0.0
        elif aggregation == AggregationType.SUM:
            return metric.sum_value
        elif aggregation == AggregationType.COUNT:
            return metric.count
        elif aggregation == AggregationType.P50:
            return metric.get_percentile(50)
        elif aggregation == AggregationType.P95:
            return metric.get_percentile(95)
        elif aggregation == AggregationType.P99:
            return metric.get_percentile(99)
        else:
            return metric.current_value

    def set_threshold(
        self,
        metric_name: str,
        warning: Optional[float] = None,
        error: Optional[float] = None,
        critical: Optional[float] = None,
        comparison: str = "above"
    ) -> None:
        """Set alert thresholds for a metric."""
        config = ThresholdConfig(
            metric_name=metric_name,
            warning_threshold=warning,
            error_threshold=error,
            critical_threshold=critical,
            comparison=comparison
        )
        self.alert_manager.set_threshold(config)

    async def collect_metrics(self) -> Dict[str, float]:
        """Collect metrics from all collectors."""
        all_metrics = {}

        for collector in self.collectors:
            try:
                metrics = await collector.collect()
                all_metrics.update(metrics)

                for name, value in metrics.items():
                    self.record(name, value)
            except Exception as e:
                logger.error(f"Metric collection error: {e}")

        return all_metrics

    async def start(self) -> None:
        """Start continuous monitoring."""
        if self.is_running:
            return

        self.is_running = True
        self.collection_task = asyncio.create_task(self._collection_loop())

    async def stop(self) -> None:
        """Stop monitoring."""
        self.is_running = False
        if self.collection_task:
            self.collection_task.cancel()
            try:
                await self.collection_task
            except asyncio.CancelledError:
                pass

    async def _collection_loop(self) -> None:
        """Continuous collection loop."""
        while self.is_running:
            try:
                await self.collect_metrics()

                # Update anomaly baselines periodically
                for name, metric in self.metrics.items():
                    values = [v.value for v in metric.values]
                    self.anomaly_detector.update_baseline(name, values)

            except Exception as e:
                logger.error(f"Collection loop error: {e}")

            await asyncio.sleep(self.collection_interval)

    async def check_health(self) -> Dict[str, HealthCheck]:
        """Run all health checks."""
        return await self.health_checker.run_all_checks()

    def get_overall_health(self) -> HealthStatus:
        """Get overall system health."""
        return self.health_checker.get_overall_status()

    def start_profile(self, name: str) -> str:
        """Start a performance profile."""
        profile = PerformanceProfile(name=name)
        self.active_profiles[profile.id] = profile
        return profile.id

    def add_span(
        self,
        profile_id: str,
        span_name: str,
        duration_ms: float,
        metadata: Dict[str, Any] = None
    ) -> None:
        """Add a span to a profile."""
        profile = self.active_profiles.get(profile_id)
        if profile:
            profile.spans.append({
                "name": span_name,
                "duration_ms": duration_ms,
                "metadata": metadata or {},
                "timestamp": datetime.now().isoformat()
            })

    def end_profile(self, profile_id: str) -> Optional[PerformanceProfile]:
        """End a performance profile."""
        profile = self.active_profiles.pop(profile_id, None)
        if profile:
            profile.end_time = datetime.now()
            profile.duration_ms = (
                profile.end_time - profile.start_time
            ).total_seconds() * 1000

            # Capture current metrics
            for name, metric in self.metrics.items():
                profile.metrics[name] = metric.current_value

            self.profiles[profile.id] = profile
        return profile

    def get_trends(self) -> Dict[str, TrendDirection]:
        """Get trends for all metrics."""
        trends = {}
        for name, metric in self.metrics.items():
            values = [v.value for v in metric.values]
            trends[name] = self.anomaly_detector.detect_trend(values)
        return trends

    def get_anomalies(self) -> List[Tuple[str, float, float]]:
        """Get current anomalies."""
        anomalies = []
        for name, metric in self.metrics.items():
            is_anomaly, z_score = self.anomaly_detector.is_anomaly(
                name, metric.current_value
            )
            if is_anomaly:
                anomalies.append((name, metric.current_value, z_score))
        return anomalies

    def get_dashboard(self) -> Dict[str, Any]:
        """Get monitoring dashboard data."""
        alerts = self.alert_manager.get_active_alerts()
        health = self.health_checker.get_overall_status()
        trends = self.get_trends()
        anomalies = self.get_anomalies()

        # Key metrics summary
        key_metrics = {
            "cpu_percent": self.get_metric_value("cpu_percent"),
            "memory_percent": self.get_metric_value("memory_percent"),
            "error_rate": self.get_metric_value("error_rate"),
            "response_time_ms": self.get_metric_value("response_time_ms"),
            "requests_per_second": self.get_metric_value("requests_per_second"),
            "active_agents": self.get_metric_value("active_agents")
        }

        return {
            "health": health.value,
            "alerts_active": len(alerts),
            "anomalies_detected": len(anomalies),
            "metrics_count": len(self.metrics),
            "key_metrics": key_metrics,
            "trends": {k: v.value for k, v in trends.items()},
            "alerts": [
                {"metric": a.metric_name, "severity": a.severity.value}
                for a in alerts
            ]
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get monitor statistics."""
        return {
            "metrics_registered": len(self.metrics),
            "collectors": len(self.collectors),
            "health_checks": len(self.health_checker.checks),
            "thresholds_configured": len(self.alert_manager.thresholds),
            "active_alerts": len(self.alert_manager.active_alerts),
            "alert_history": len(self.alert_manager.alert_history),
            "profiles_completed": len(self.profiles),
            "is_running": self.is_running
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Performance Monitor."""
    print("=" * 70)
    print("BAEL - PERFORMANCE MONITOR DEMO")
    print("Real-time System Monitoring")
    print("=" * 70)
    print()

    # Create monitor
    monitor = PerformanceMonitor(collection_interval_seconds=1.0)

    # 1. Setup Thresholds
    print("1. CONFIGURING THRESHOLDS:")
    print("-" * 40)

    monitor.set_threshold("cpu_percent", warning=70, error=85, critical=95)
    monitor.set_threshold("memory_percent", warning=75, error=90, critical=95)
    monitor.set_threshold("error_rate", warning=0.05, error=0.1, critical=0.2)

    print("   Configured thresholds for CPU, memory, and errors")
    print()

    # 2. Collect Metrics
    print("2. COLLECTING METRICS:")
    print("-" * 40)

    # Collect a few rounds
    for i in range(3):
        metrics = await monitor.collect_metrics()
        print(f"   Round {i+1}: Collected {len(metrics)} metrics")

    print()

    # 3. View Key Metrics
    print("3. KEY METRICS:")
    print("-" * 40)

    key_names = ["cpu_percent", "memory_percent", "requests_per_second", "error_rate"]
    for name in key_names:
        value = monitor.get_metric_value(name)
        print(f"   {name}: {value:.2f}")
    print()

    # 4. Health Checks
    print("4. HEALTH CHECKS:")
    print("-" * 40)

    health_results = await monitor.check_health()
    for name, check in health_results.items():
        print(f"   {name}: {check.status.value} - {check.message} ({check.latency_ms:.1f}ms)")

    overall = monitor.get_overall_health()
    print(f"\n   Overall Health: {overall.value}")
    print()

    # 5. Trend Analysis
    print("5. TREND ANALYSIS:")
    print("-" * 40)

    # Collect more data for trends
    for _ in range(5):
        await monitor.collect_metrics()

    trends = monitor.get_trends()
    for name, trend in list(trends.items())[:5]:
        print(f"   {name}: {trend.value}")
    print()

    # 6. Anomaly Detection
    print("6. ANOMALY DETECTION:")
    print("-" * 40)

    anomalies = monitor.get_anomalies()
    if anomalies:
        for name, value, z_score in anomalies:
            print(f"   ANOMALY: {name} = {value:.2f} (z-score: {z_score:.2f})")
    else:
        print("   No anomalies detected")
    print()

    # 7. Profiling
    print("7. PERFORMANCE PROFILING:")
    print("-" * 40)

    profile_id = monitor.start_profile("test_operation")

    # Simulate spans
    monitor.add_span(profile_id, "initialization", 5.2)
    await asyncio.sleep(0.1)
    monitor.add_span(profile_id, "processing", 15.7)
    await asyncio.sleep(0.1)
    monitor.add_span(profile_id, "cleanup", 2.3)

    profile = monitor.end_profile(profile_id)

    print(f"   Profile: {profile.name}")
    print(f"   Duration: {profile.duration_ms:.1f}ms")
    print(f"   Spans: {len(profile.spans)}")
    for span in profile.spans:
        print(f"     - {span['name']}: {span['duration_ms']:.1f}ms")
    print()

    # 8. Alerts
    print("8. ALERT SYSTEM:")
    print("-" * 40)

    # Manually trigger a high value to see alert
    monitor.record("cpu_percent", 88.0)

    alerts = monitor.alert_manager.get_active_alerts()
    if alerts:
        for alert in alerts:
            print(f"   ALERT [{alert.severity.value.upper()}]: {alert.message}")
    else:
        print("   No active alerts")
    print()

    # 9. Dashboard
    print("9. MONITORING DASHBOARD:")
    print("-" * 40)

    dashboard = monitor.get_dashboard()

    print(f"   Health: {dashboard['health']}")
    print(f"   Active Alerts: {dashboard['alerts_active']}")
    print(f"   Anomalies: {dashboard['anomalies_detected']}")
    print(f"   Total Metrics: {dashboard['metrics_count']}")
    print("\n   Key Metrics:")
    for name, value in dashboard['key_metrics'].items():
        print(f"     - {name}: {value:.2f}")
    print()

    # 10. Statistics
    print("10. MONITOR STATISTICS:")
    print("-" * 40)

    stats = monitor.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Performance Monitor Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
