#!/usr/bin/env python3
"""
BAEL - Monitoring Engine
System monitoring and observability for agents.

Features:
- Metric collection
- Health checks
- Alerting
- Performance monitoring
- Resource tracking
"""

import asyncio
import hashlib
import json
import math
import random
import statistics
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class MetricType(Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"
    TIMER = "timer"


class HealthStatus(Enum):
    """Health statuses."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class AlertSeverity(Enum):
    """Alert severities."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertState(Enum):
    """Alert states."""
    PENDING = "pending"
    FIRING = "firing"
    RESOLVED = "resolved"


class CheckType(Enum):
    """Health check types."""
    LIVENESS = "liveness"
    READINESS = "readiness"
    STARTUP = "startup"


class AggregationType(Enum):
    """Metric aggregation types."""
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    P50 = "p50"
    P90 = "p90"
    P99 = "p99"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class MetricValue:
    """A metric value point."""
    timestamp: datetime = field(default_factory=datetime.now)
    value: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class Metric:
    """A metric definition."""
    metric_id: str = ""
    name: str = ""
    metric_type: MetricType = MetricType.GAUGE
    description: str = ""
    values: List[MetricValue] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if not self.metric_id:
            self.metric_id = str(uuid.uuid4())[:8]


@dataclass
class HealthCheck:
    """A health check definition."""
    check_id: str = ""
    name: str = ""
    check_type: CheckType = CheckType.LIVENESS
    checker: Optional[Callable] = None
    interval: int = 30
    timeout: int = 10
    last_check: Optional[datetime] = None
    last_status: HealthStatus = HealthStatus.UNKNOWN
    last_message: str = ""

    def __post_init__(self):
        if not self.check_id:
            self.check_id = str(uuid.uuid4())[:8]


@dataclass
class Alert:
    """An alert definition."""
    alert_id: str = ""
    name: str = ""
    severity: AlertSeverity = AlertSeverity.WARNING
    condition: Optional[Callable] = None
    message: str = ""
    state: AlertState = AlertState.PENDING
    fired_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    labels: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if not self.alert_id:
            self.alert_id = str(uuid.uuid4())[:8]


@dataclass
class AlertRule:
    """An alerting rule."""
    rule_id: str = ""
    name: str = ""
    metric_name: str = ""
    operator: str = ">"
    threshold: float = 0.0
    duration: int = 0
    severity: AlertSeverity = AlertSeverity.WARNING
    message_template: str = ""

    def __post_init__(self):
        if not self.rule_id:
            self.rule_id = str(uuid.uuid4())[:8]


@dataclass
class MonitoringConfig:
    """Monitoring configuration."""
    retention_period: int = 3600
    max_values_per_metric: int = 1000
    default_check_interval: int = 30
    enable_alerting: bool = True


# =============================================================================
# METRIC COLLECTOR
# =============================================================================

class MetricCollector:
    """Collect and store metrics."""

    def __init__(self, max_values: int = 1000):
        self._metrics: Dict[str, Metric] = {}
        self._max_values = max_values

    def register(
        self,
        name: str,
        metric_type: MetricType,
        description: str = "",
        labels: Optional[Dict[str, str]] = None
    ) -> Metric:
        """Register a metric."""
        metric = Metric(
            name=name,
            metric_type=metric_type,
            description=description,
            labels=labels or {}
        )

        self._metrics[name] = metric

        return metric

    def get(self, name: str) -> Optional[Metric]:
        """Get metric by name."""
        return self._metrics.get(name)

    def record(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ) -> bool:
        """Record a metric value."""
        metric = self._metrics.get(name)

        if not metric:
            return False

        metric_value = MetricValue(
            value=value,
            labels=labels or {}
        )

        metric.values.append(metric_value)

        if len(metric.values) > self._max_values:
            metric.values = metric.values[-self._max_values:]

        return True

    def increment(
        self,
        name: str,
        value: float = 1.0,
        labels: Optional[Dict[str, str]] = None
    ) -> bool:
        """Increment a counter metric."""
        metric = self._metrics.get(name)

        if not metric or metric.metric_type != MetricType.COUNTER:
            return False

        current = metric.values[-1].value if metric.values else 0

        return self.record(name, current + value, labels)

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ) -> bool:
        """Set a gauge metric."""
        metric = self._metrics.get(name)

        if not metric or metric.metric_type != MetricType.GAUGE:
            return False

        return self.record(name, value, labels)

    def observe(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ) -> bool:
        """Observe a value for histogram/summary."""
        return self.record(name, value, labels)

    def get_current(self, name: str) -> Optional[float]:
        """Get current value of a metric."""
        metric = self._metrics.get(name)

        if metric and metric.values:
            return metric.values[-1].value

        return None

    def get_values(
        self,
        name: str,
        since: Optional[datetime] = None
    ) -> List[MetricValue]:
        """Get metric values since timestamp."""
        metric = self._metrics.get(name)

        if not metric:
            return []

        if since:
            return [v for v in metric.values if v.timestamp >= since]

        return list(metric.values)

    def aggregate(
        self,
        name: str,
        aggregation: AggregationType,
        since: Optional[datetime] = None
    ) -> Optional[float]:
        """Aggregate metric values."""
        values = self.get_values(name, since)

        if not values:
            return None

        nums = [v.value for v in values]

        if aggregation == AggregationType.SUM:
            return sum(nums)
        elif aggregation == AggregationType.AVG:
            return statistics.mean(nums)
        elif aggregation == AggregationType.MIN:
            return min(nums)
        elif aggregation == AggregationType.MAX:
            return max(nums)
        elif aggregation == AggregationType.COUNT:
            return len(nums)
        elif aggregation == AggregationType.P50:
            return statistics.median(nums)
        elif aggregation == AggregationType.P90:
            return self._percentile(nums, 90)
        elif aggregation == AggregationType.P99:
            return self._percentile(nums, 99)

        return None

    def _percentile(self, values: List[float], p: float) -> float:
        """Calculate percentile."""
        sorted_vals = sorted(values)
        k = (len(sorted_vals) - 1) * p / 100
        f = math.floor(k)
        c = math.ceil(k)

        if f == c:
            return sorted_vals[int(k)]

        return sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f)

    def clear(self, name: str) -> bool:
        """Clear metric values."""
        metric = self._metrics.get(name)

        if metric:
            metric.values.clear()
            return True

        return False

    def delete(self, name: str) -> bool:
        """Delete a metric."""
        if name in self._metrics:
            del self._metrics[name]
            return True
        return False

    def count(self) -> int:
        """Count metrics."""
        return len(self._metrics)

    def all(self) -> List[Metric]:
        """Get all metrics."""
        return list(self._metrics.values())


# =============================================================================
# HEALTH CHECKER
# =============================================================================

class HealthChecker:
    """Perform health checks."""

    def __init__(self):
        self._checks: Dict[str, HealthCheck] = {}

    def register(
        self,
        name: str,
        checker: Callable,
        check_type: CheckType = CheckType.LIVENESS,
        interval: int = 30,
        timeout: int = 10
    ) -> HealthCheck:
        """Register a health check."""
        check = HealthCheck(
            name=name,
            checker=checker,
            check_type=check_type,
            interval=interval,
            timeout=timeout
        )

        self._checks[name] = check

        return check

    def get(self, name: str) -> Optional[HealthCheck]:
        """Get health check by name."""
        return self._checks.get(name)

    async def run_check(self, name: str) -> Tuple[HealthStatus, str]:
        """Run a health check."""
        check = self._checks.get(name)

        if not check or not check.checker:
            return HealthStatus.UNKNOWN, "Check not found"

        try:
            if asyncio.iscoroutinefunction(check.checker):
                result = await asyncio.wait_for(
                    check.checker(),
                    timeout=check.timeout
                )
            else:
                result = check.checker()

            if isinstance(result, tuple):
                status, message = result
            elif isinstance(result, bool):
                status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
                message = "OK" if result else "Failed"
            else:
                status = HealthStatus.HEALTHY
                message = str(result)

            check.last_check = datetime.now()
            check.last_status = status
            check.last_message = message

            return status, message

        except asyncio.TimeoutError:
            check.last_check = datetime.now()
            check.last_status = HealthStatus.UNHEALTHY
            check.last_message = "Timeout"

            return HealthStatus.UNHEALTHY, "Timeout"

        except Exception as e:
            check.last_check = datetime.now()
            check.last_status = HealthStatus.UNHEALTHY
            check.last_message = str(e)

            return HealthStatus.UNHEALTHY, str(e)

    async def run_all(self) -> Dict[str, Tuple[HealthStatus, str]]:
        """Run all health checks."""
        results = {}

        for name in self._checks:
            results[name] = await self.run_check(name)

        return results

    def get_overall_status(self) -> HealthStatus:
        """Get overall health status."""
        statuses = [c.last_status for c in self._checks.values()]

        if not statuses:
            return HealthStatus.UNKNOWN

        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY

        if any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED

        if any(s == HealthStatus.UNKNOWN for s in statuses):
            return HealthStatus.UNKNOWN

        return HealthStatus.HEALTHY

    def get_by_type(self, check_type: CheckType) -> List[HealthCheck]:
        """Get checks by type."""
        return [c for c in self._checks.values() if c.check_type == check_type]

    def delete(self, name: str) -> bool:
        """Delete a health check."""
        if name in self._checks:
            del self._checks[name]
            return True
        return False

    def count(self) -> int:
        """Count health checks."""
        return len(self._checks)

    def all(self) -> List[HealthCheck]:
        """Get all health checks."""
        return list(self._checks.values())


# =============================================================================
# ALERT MANAGER
# =============================================================================

class AlertManager:
    """Manage alerts."""

    def __init__(self):
        self._rules: Dict[str, AlertRule] = {}
        self._alerts: Dict[str, Alert] = {}
        self._handlers: List[Callable] = []

    def add_rule(
        self,
        name: str,
        metric_name: str,
        operator: str,
        threshold: float,
        severity: AlertSeverity = AlertSeverity.WARNING,
        duration: int = 0,
        message_template: str = ""
    ) -> AlertRule:
        """Add an alerting rule."""
        rule = AlertRule(
            name=name,
            metric_name=metric_name,
            operator=operator,
            threshold=threshold,
            severity=severity,
            duration=duration,
            message_template=message_template or f"{metric_name} {operator} {threshold}"
        )

        self._rules[name] = rule

        return rule

    def get_rule(self, name: str) -> Optional[AlertRule]:
        """Get rule by name."""
        return self._rules.get(name)

    def evaluate_rule(
        self,
        rule: AlertRule,
        current_value: float
    ) -> bool:
        """Evaluate if rule condition is met."""
        op = rule.operator
        threshold = rule.threshold

        if op == ">":
            return current_value > threshold
        elif op == ">=":
            return current_value >= threshold
        elif op == "<":
            return current_value < threshold
        elif op == "<=":
            return current_value <= threshold
        elif op == "==":
            return current_value == threshold
        elif op == "!=":
            return current_value != threshold

        return False

    def fire_alert(
        self,
        rule: AlertRule,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ) -> Alert:
        """Fire an alert."""
        message = rule.message_template.format(
            value=value,
            threshold=rule.threshold
        ) if "{" in rule.message_template else f"{rule.metric_name} = {value} ({rule.operator} {rule.threshold})"

        alert = Alert(
            name=rule.name,
            severity=rule.severity,
            message=message,
            state=AlertState.FIRING,
            fired_at=datetime.now(),
            labels=labels or {}
        )

        self._alerts[alert.alert_id] = alert

        for handler in self._handlers:
            try:
                handler(alert)
            except Exception:
                pass

        return alert

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        alert = self._alerts.get(alert_id)

        if alert:
            alert.state = AlertState.RESOLVED
            alert.resolved_at = datetime.now()
            return True

        return False

    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get alert by ID."""
        return self._alerts.get(alert_id)

    def get_firing(self) -> List[Alert]:
        """Get firing alerts."""
        return [a for a in self._alerts.values() if a.state == AlertState.FIRING]

    def get_by_severity(self, severity: AlertSeverity) -> List[Alert]:
        """Get alerts by severity."""
        return [a for a in self._alerts.values() if a.severity == severity]

    def add_handler(self, handler: Callable) -> None:
        """Add an alert handler."""
        self._handlers.append(handler)

    def clear_resolved(self) -> int:
        """Clear resolved alerts."""
        resolved = [aid for aid, a in self._alerts.items()
                   if a.state == AlertState.RESOLVED]

        for aid in resolved:
            del self._alerts[aid]

        return len(resolved)

    def delete_rule(self, name: str) -> bool:
        """Delete a rule."""
        if name in self._rules:
            del self._rules[name]
            return True
        return False

    def count_rules(self) -> int:
        """Count rules."""
        return len(self._rules)

    def count_alerts(self) -> int:
        """Count alerts."""
        return len(self._alerts)

    def all_rules(self) -> List[AlertRule]:
        """Get all rules."""
        return list(self._rules.values())

    def all_alerts(self) -> List[Alert]:
        """Get all alerts."""
        return list(self._alerts.values())


# =============================================================================
# TIMER
# =============================================================================

class Timer:
    """Context manager for timing operations."""

    def __init__(
        self,
        collector: MetricCollector,
        metric_name: str,
        labels: Optional[Dict[str, str]] = None
    ):
        self._collector = collector
        self._metric_name = metric_name
        self._labels = labels or {}
        self._start: Optional[float] = None

    def __enter__(self):
        self._start = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._start:
            duration = time.time() - self._start
            self._collector.observe(self._metric_name, duration, self._labels)

    async def __aenter__(self):
        self._start = time.time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._start:
            duration = time.time() - self._start
            self._collector.observe(self._metric_name, duration, self._labels)


# =============================================================================
# MONITORING ENGINE
# =============================================================================

class MonitoringEngine:
    """
    Monitoring Engine for BAEL.

    System monitoring and observability.
    """

    def __init__(self, config: Optional[MonitoringConfig] = None):
        self._config = config or MonitoringConfig()

        self._metric_collector = MetricCollector(
            self._config.max_values_per_metric
        )
        self._health_checker = HealthChecker()
        self._alert_manager = AlertManager()

    # ----- Metric Operations -----

    def register_counter(
        self,
        name: str,
        description: str = ""
    ) -> Metric:
        """Register a counter metric."""
        return self._metric_collector.register(
            name,
            MetricType.COUNTER,
            description
        )

    def register_gauge(
        self,
        name: str,
        description: str = ""
    ) -> Metric:
        """Register a gauge metric."""
        return self._metric_collector.register(
            name,
            MetricType.GAUGE,
            description
        )

    def register_histogram(
        self,
        name: str,
        description: str = ""
    ) -> Metric:
        """Register a histogram metric."""
        return self._metric_collector.register(
            name,
            MetricType.HISTOGRAM,
            description
        )

    def register_timer(
        self,
        name: str,
        description: str = ""
    ) -> Metric:
        """Register a timer metric."""
        return self._metric_collector.register(
            name,
            MetricType.TIMER,
            description
        )

    def increment(
        self,
        name: str,
        value: float = 1.0,
        labels: Optional[Dict[str, str]] = None
    ) -> bool:
        """Increment counter."""
        return self._metric_collector.increment(name, value, labels)

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ) -> bool:
        """Set gauge value."""
        return self._metric_collector.set_gauge(name, value, labels)

    def observe(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ) -> bool:
        """Observe value for histogram."""
        return self._metric_collector.observe(name, value, labels)

    def timer(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None
    ) -> Timer:
        """Get timer context manager."""
        return Timer(self._metric_collector, name, labels)

    def get_metric(self, name: str) -> Optional[Metric]:
        """Get metric by name."""
        return self._metric_collector.get(name)

    def get_current_value(self, name: str) -> Optional[float]:
        """Get current metric value."""
        return self._metric_collector.get_current(name)

    def aggregate(
        self,
        name: str,
        aggregation: AggregationType,
        since: Optional[datetime] = None
    ) -> Optional[float]:
        """Aggregate metric values."""
        return self._metric_collector.aggregate(name, aggregation, since)

    # ----- Health Check Operations -----

    def register_health_check(
        self,
        name: str,
        checker: Callable,
        check_type: CheckType = CheckType.LIVENESS,
        interval: int = 30
    ) -> HealthCheck:
        """Register a health check."""
        return self._health_checker.register(
            name,
            checker,
            check_type,
            interval
        )

    async def run_health_check(
        self,
        name: str
    ) -> Tuple[HealthStatus, str]:
        """Run a health check."""
        return await self._health_checker.run_check(name)

    async def run_all_health_checks(
        self
    ) -> Dict[str, Tuple[HealthStatus, str]]:
        """Run all health checks."""
        return await self._health_checker.run_all()

    def get_health_status(self) -> HealthStatus:
        """Get overall health status."""
        return self._health_checker.get_overall_status()

    def get_health_check(self, name: str) -> Optional[HealthCheck]:
        """Get health check by name."""
        return self._health_checker.get(name)

    # ----- Alerting Operations -----

    def add_alert_rule(
        self,
        name: str,
        metric_name: str,
        operator: str,
        threshold: float,
        severity: AlertSeverity = AlertSeverity.WARNING
    ) -> AlertRule:
        """Add an alerting rule."""
        return self._alert_manager.add_rule(
            name,
            metric_name,
            operator,
            threshold,
            severity
        )

    def check_alerts(self) -> List[Alert]:
        """Check all alert rules."""
        fired = []

        for rule in self._alert_manager.all_rules():
            value = self._metric_collector.get_current(rule.metric_name)

            if value is not None and self._alert_manager.evaluate_rule(rule, value):
                alert = self._alert_manager.fire_alert(rule, value)
                fired.append(alert)

        return fired

    def get_firing_alerts(self) -> List[Alert]:
        """Get firing alerts."""
        return self._alert_manager.get_firing()

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        return self._alert_manager.resolve_alert(alert_id)

    def add_alert_handler(self, handler: Callable) -> None:
        """Add an alert handler."""
        self._alert_manager.add_handler(handler)

    # ----- Export -----

    def export_metrics(self) -> Dict[str, Any]:
        """Export all metrics."""
        return {
            m.name: {
                "type": m.metric_type.value,
                "current": self._metric_collector.get_current(m.name),
                "count": len(m.values)
            }
            for m in self._metric_collector.all()
        }

    def export_health(self) -> Dict[str, Any]:
        """Export health status."""
        return {
            c.name: {
                "type": c.check_type.value,
                "status": c.last_status.value,
                "message": c.last_message,
                "last_check": c.last_check.isoformat() if c.last_check else None
            }
            for c in self._health_checker.all()
        }

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "metrics": self._metric_collector.count(),
            "health_checks": self._health_checker.count(),
            "alert_rules": self._alert_manager.count_rules(),
            "firing_alerts": len(self._alert_manager.get_firing()),
            "overall_health": self._health_checker.get_overall_status().value
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Monitoring Engine."""
    print("=" * 70)
    print("BAEL - MONITORING ENGINE DEMO")
    print("System Monitoring and Observability")
    print("=" * 70)
    print()

    engine = MonitoringEngine()

    # 1. Register Metrics
    print("1. REGISTER METRICS:")
    print("-" * 40)

    engine.register_counter("requests_total", "Total HTTP requests")
    engine.register_gauge("active_connections", "Active connections")
    engine.register_histogram("request_duration", "Request duration seconds")
    engine.register_timer("processing_time", "Processing time")

    print("   Registered: requests_total (counter)")
    print("   Registered: active_connections (gauge)")
    print("   Registered: request_duration (histogram)")
    print("   Registered: processing_time (timer)")
    print()

    # 2. Record Metrics
    print("2. RECORD METRICS:")
    print("-" * 40)

    for _ in range(5):
        engine.increment("requests_total")

    engine.set_gauge("active_connections", 42)

    for val in [0.1, 0.2, 0.15, 0.3, 0.12]:
        engine.observe("request_duration", val)

    print(f"   requests_total: {engine.get_current_value('requests_total')}")
    print(f"   active_connections: {engine.get_current_value('active_connections')}")
    print()

    # 3. Use Timer
    print("3. USE TIMER:")
    print("-" * 40)

    with engine.timer("processing_time"):
        await asyncio.sleep(0.1)

    print(f"   processing_time: {engine.get_current_value('processing_time'):.4f}s")
    print()

    # 4. Aggregate Metrics
    print("4. AGGREGATE METRICS:")
    print("-" * 40)

    avg = engine.aggregate("request_duration", AggregationType.AVG)
    p90 = engine.aggregate("request_duration", AggregationType.P90)
    max_val = engine.aggregate("request_duration", AggregationType.MAX)

    print(f"   request_duration avg: {avg:.4f}s")
    print(f"   request_duration p90: {p90:.4f}s")
    print(f"   request_duration max: {max_val:.4f}s")
    print()

    # 5. Register Health Checks
    print("5. REGISTER HEALTH CHECKS:")
    print("-" * 40)

    def db_check():
        return True, "Database connected"

    async def api_check():
        await asyncio.sleep(0.01)
        return HealthStatus.HEALTHY, "API responding"

    engine.register_health_check("database", db_check, CheckType.READINESS)
    engine.register_health_check("api", api_check, CheckType.LIVENESS)

    print("   Registered: database (readiness)")
    print("   Registered: api (liveness)")
    print()

    # 6. Run Health Checks
    print("6. RUN HEALTH CHECKS:")
    print("-" * 40)

    results = await engine.run_all_health_checks()

    for name, (status, message) in results.items():
        print(f"   {name}: {status.value} - {message}")
    print()

    # 7. Get Overall Health
    print("7. GET OVERALL HEALTH:")
    print("-" * 40)

    overall = engine.get_health_status()
    print(f"   Overall status: {overall.value}")
    print()

    # 8. Add Alert Rules
    print("8. ADD ALERT RULES:")
    print("-" * 40)

    engine.add_alert_rule(
        "high_connections",
        "active_connections",
        ">",
        40,
        AlertSeverity.WARNING
    )

    engine.add_alert_rule(
        "slow_requests",
        "request_duration",
        ">",
        0.5,
        AlertSeverity.ERROR
    )

    print("   Rule: high_connections (active_connections > 40)")
    print("   Rule: slow_requests (request_duration > 0.5)")
    print()

    # 9. Check Alerts
    print("9. CHECK ALERTS:")
    print("-" * 40)

    fired = engine.check_alerts()

    print(f"   Fired alerts: {len(fired)}")
    for alert in fired:
        print(f"   - {alert.name}: {alert.message} ({alert.severity.value})")
    print()

    # 10. Get Firing Alerts
    print("10. GET FIRING ALERTS:")
    print("-" * 40)

    firing = engine.get_firing_alerts()
    print(f"   Currently firing: {len(firing)}")
    print()

    # 11. Alert Handler
    print("11. ALERT HANDLER:")
    print("-" * 40)

    handled_alerts = []

    def alert_handler(alert):
        handled_alerts.append(alert.name)

    engine.add_alert_handler(alert_handler)

    engine.set_gauge("active_connections", 50)
    engine.check_alerts()

    print(f"   Handled: {handled_alerts}")
    print()

    # 12. Resolve Alert
    print("12. RESOLVE ALERT:")
    print("-" * 40)

    firing = engine.get_firing_alerts()

    if firing:
        resolved = engine.resolve_alert(firing[0].alert_id)
        print(f"   Resolved: {resolved}")
        print(f"   Still firing: {len(engine.get_firing_alerts())}")
    print()

    # 13. Export Metrics
    print("13. EXPORT METRICS:")
    print("-" * 40)

    export = engine.export_metrics()

    for name, data in export.items():
        print(f"   {name}: {data['type']} = {data['current']}")
    print()

    # 14. Export Health
    print("14. EXPORT HEALTH:")
    print("-" * 40)

    health = engine.export_health()

    for name, data in health.items():
        print(f"   {name}: {data['status']} ({data['type']})")
    print()

    # 15. Summary
    print("15. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Monitoring Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
