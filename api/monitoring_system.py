"""
Advanced Monitoring & Observability System for BAEL

Provides metrics collection, distributed tracing, log aggregation,
alerts, dashboards, anomaly detection, and SLA tracking.
"""

import asyncio
import json
import logging
import statistics
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Metric types"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"
    SUMMARY = "summary"


class SeverityLevel(Enum):
    """Alert severity levels"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    INFO = 5


@dataclass
class Metric:
    """Single metric data point"""
    name: str
    value: float
    metric_type: MetricType
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "type": self.metric_type.value,
            "labels": self.labels,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class LogEntry:
    """Structured log entry"""
    timestamp: datetime
    level: str
    message: str
    service: str
    trace_id: str
    span_id: str
    duration_ms: float = 0.0
    error: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level,
            "message": self.message,
            "service": self.service,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "context": self.context
        }


@dataclass
class Span:
    """Distributed trace span"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation_name: str
    service_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0
    status: str = "unknown"
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "operation_name": self.operation_name,
            "service_name": self.service_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "attributes": self.attributes,
            "events": self.events
        }


@dataclass
class Alert:
    """Alert definition and state"""
    alert_id: str
    name: str
    condition: str
    severity: SeverityLevel
    threshold: float
    triggered: bool = False
    trigger_time: Optional[datetime] = None
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "name": self.name,
            "condition": self.condition,
            "severity": self.severity.name,
            "threshold": self.threshold,
            "triggered": self.triggered,
            "trigger_time": self.trigger_time.isoformat() if self.trigger_time else None,
            "trigger_count": self.trigger_count
        }


class MetricsCollector:
    """Collects and aggregates metrics"""

    def __init__(self, max_history: int = 1000):
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self.max_history = max_history

    def record_metric(self, metric: Metric):
        """Record a metric"""
        self.metrics[metric.name].append(metric)
        logger.debug(f"Recorded metric: {metric.name} = {metric.value}")

    def counter(self, name: str, value: float = 1.0, labels: Dict[str, str] = None):
        """Record counter metric"""
        metric = Metric(
            name=name,
            value=value,
            metric_type=MetricType.COUNTER,
            labels=labels or {}
        )
        self.record_metric(metric)

    def gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record gauge metric"""
        metric = Metric(
            name=name,
            value=value,
            metric_type=MetricType.GAUGE,
            labels=labels or {}
        )
        self.record_metric(metric)

    def histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record histogram metric"""
        metric = Metric(
            name=name,
            value=value,
            metric_type=MetricType.HISTOGRAM,
            labels=labels or {}
        )
        self.record_metric(metric)

    def timer(self, name: str, duration_ms: float, labels: Dict[str, str] = None):
        """Record timer metric"""
        metric = Metric(
            name=name,
            value=duration_ms,
            metric_type=MetricType.TIMER,
            labels=labels or {}
        )
        self.record_metric(metric)

    def get_metric_summary(self, metric_name: str) -> Dict[str, Any]:
        """Get statistical summary of metric"""
        if metric_name not in self.metrics:
            return {}

        values = [m.value for m in self.metrics[metric_name]]
        if not values:
            return {}

        return {
            "name": metric_name,
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0,
            "p95": sorted(values)[int(len(values) * 0.95)] if values else 0,
            "p99": sorted(values)[int(len(values) * 0.99)] if values else 0
        }

    def get_all_metrics(self) -> List[Dict[str, Any]]:
        """Get all metrics"""
        metrics = []
        for metric_name in self.metrics:
            summary = self.get_metric_summary(metric_name)
            if summary:
                metrics.append(summary)
        return metrics


class LogAggregator:
    """Aggregates logs from all services"""

    def __init__(self, max_logs: int = 10000):
        self.logs: deque = deque(maxlen=max_logs)
        self.logs_by_service: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.logs_by_level: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))

    def log(self, entry: LogEntry):
        """Record log entry"""
        self.logs.append(entry)
        self.logs_by_service[entry.service].append(entry)
        self.logs_by_level[entry.level].append(entry)
        logger.info(f"[{entry.level}] {entry.service}: {entry.message}")

    def get_logs(self, limit: int = 100, level: Optional[str] = None,
                 service: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get logs with optional filtering"""
        logs = list(self.logs)

        if level:
            logs = [l for l in logs if l.level == level]

        if service:
            logs = [l for l in logs if l.service == service]

        return [l.to_dict() for l in logs[-limit:]]

    def get_error_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get error logs"""
        error_logs = list(self.logs_by_level.get("ERROR", []))
        return [l.to_dict() for l in error_logs[-limit:]]

    def get_logs_by_service(self, service: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get logs for specific service"""
        logs = list(self.logs_by_service.get(service, []))
        return [l.to_dict() for l in logs[-limit:]]


class DistributedTracer:
    """Manages distributed tracing"""

    def __init__(self):
        self.traces: Dict[str, List[Span]] = defaultdict(list)
        self.all_spans: deque = deque(maxlen=10000)

    def start_span(self, trace_id: str, operation_name: str, service_name: str,
                   parent_span_id: Optional[str] = None) -> Span:
        """Start a new span"""
        import uuid
        span_id = str(uuid.uuid4())

        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            service_name=service_name,
            start_time=datetime.now()
        )

        self.traces[trace_id].append(span)
        logger.debug(f"Started span: {operation_name} ({span_id})")

        return span

    def end_span(self, span: Span, status: str = "ok"):
        """End a span"""
        span.end_time = datetime.now()
        span.duration_ms = (span.end_time - span.start_time).total_seconds() * 1000
        span.status = status
        self.all_spans.append(span)
        logger.debug(f"Ended span: {span.operation_name} ({span.span_id}) - {status}")

    def add_event(self, span: Span, event_name: str, attributes: Dict[str, Any] = None):
        """Add event to span"""
        span.events.append({
            "name": event_name,
            "timestamp": datetime.now().isoformat(),
            "attributes": attributes or {}
        })

    def set_attribute(self, span: Span, key: str, value: Any):
        """Set span attribute"""
        span.attributes[key] = value

    def get_trace(self, trace_id: str) -> List[Dict[str, Any]]:
        """Get trace spans"""
        spans = self.traces.get(trace_id, [])
        return [s.to_dict() for s in spans]

    def get_trace_summary(self, trace_id: str) -> Dict[str, Any]:
        """Get trace summary"""
        spans = self.traces.get(trace_id, [])
        if not spans:
            return {}

        total_duration = sum((s.duration_ms for s in spans if s.duration_ms), 0)
        errors = sum(1 for s in spans if s.status != "ok")

        return {
            "trace_id": trace_id,
            "span_count": len(spans),
            "total_duration_ms": total_duration,
            "error_count": errors,
            "services": list(set(s.service_name for s in spans)),
            "operations": [s.operation_name for s in spans]
        }


class AnomalyDetector:
    """Detects anomalies in metrics"""

    def __init__(self, window_size: int = 100, std_multiplier: float = 3.0):
        self.window_size = window_size
        self.std_multiplier = std_multiplier
        self.baselines: Dict[str, Dict[str, float]] = {}

    def detect_anomaly(self, metric_name: str, value: float,
                       history: List[float]) -> Tuple[bool, Dict[str, Any]]:
        """Detect if value is anomalous"""
        if len(history) < self.window_size:
            return False, {}

        recent_values = history[-self.window_size:]
        mean = statistics.mean(recent_values)
        stdev = statistics.stdev(recent_values) if len(recent_values) > 1 else 0

        threshold = mean + (stdev * self.std_multiplier)
        is_anomaly = value > threshold

        return is_anomaly, {
            "metric": metric_name,
            "value": value,
            "mean": mean,
            "stdev": stdev,
            "threshold": threshold,
            "is_anomaly": is_anomaly
        }


class AlertManager:
    """Manages alerts and triggers"""

    def __init__(self):
        self.alerts: Dict[str, Alert] = {}
        self.alert_history: deque = deque(maxlen=10000)

    def create_alert(self, alert_id: str, name: str, condition: str,
                    severity: SeverityLevel, threshold: float) -> Alert:
        """Create a new alert"""
        alert = Alert(
            alert_id=alert_id,
            name=name,
            condition=condition,
            severity=severity,
            threshold=threshold
        )
        self.alerts[alert_id] = alert
        logger.info(f"Created alert: {name}")
        return alert

    def evaluate_alert(self, alert_id: str, current_value: float) -> bool:
        """Evaluate if alert should trigger"""
        alert = self.alerts.get(alert_id)
        if not alert:
            return False

        triggered = current_value > alert.threshold

        if triggered and not alert.triggered:
            alert.triggered = True
            alert.trigger_time = datetime.now()
            alert.trigger_count += 1
            self.alert_history.append((alert_id, datetime.now(), "triggered"))
            logger.warning(f"ALERT TRIGGERED: {alert.name} (value: {current_value})")
        elif not triggered and alert.triggered:
            alert.triggered = False
            self.alert_history.append((alert_id, datetime.now(), "resolved"))
            logger.info(f"ALERT RESOLVED: {alert.name}")

        return triggered

    def get_alerts(self, severity: Optional[SeverityLevel] = None) -> List[Dict[str, Any]]:
        """Get alerts"""
        alerts = list(self.alerts.values())

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        return [a.to_dict() for a in alerts]

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get currently active alerts"""
        return [a.to_dict() for a in self.alerts.values() if a.triggered]


class MonitoringDashboard:
    """Unified monitoring dashboard"""

    def __init__(self, metrics_collector: MetricsCollector,
                 log_aggregator: LogAggregator,
                 tracer: DistributedTracer,
                 alert_manager: AlertManager):
        self.metrics = metrics_collector
        self.logs = log_aggregator
        self.tracer = tracer
        self.alerts = alert_manager
        self.created_at = datetime.now()

    def get_dashboard(self) -> Dict[str, Any]:
        """Get complete dashboard snapshot"""
        return {
            "timestamp": datetime.now().isoformat(),
            "system_health": self.get_system_health(),
            "metrics": self.metrics.get_all_metrics(),
            "active_alerts": self.alerts.get_active_alerts(),
            "recent_errors": self.logs.get_error_logs(limit=10),
            "uptime_seconds": (datetime.now() - self.created_at).total_seconds()
        }

    def get_system_health(self) -> Dict[str, Any]:
        """Get system health status"""
        active_alerts = self.alerts.get_active_alerts()
        error_logs = self.logs.get_error_logs(limit=1)

        critical_alerts = sum(1 for a in active_alerts if a["severity"] == "CRITICAL")
        high_alerts = sum(1 for a in active_alerts if a["severity"] == "HIGH")

        if critical_alerts > 0:
            status = "CRITICAL"
        elif high_alerts > 0:
            status = "WARNING"
        else:
            status = "HEALTHY"

        return {
            "status": status,
            "active_alerts": len(active_alerts),
            "critical_alerts": critical_alerts,
            "high_alerts": high_alerts,
            "recent_errors": len(error_logs)
        }

    def get_performance_report(self) -> Dict[str, Any]:
        """Get performance metrics report"""
        metrics = self.metrics.get_all_metrics()

        timing_metrics = [m for m in metrics if "duration" in m["name"] or "latency" in m["name"]]

        return {
            "total_metrics": len(metrics),
            "timing_metrics": timing_metrics,
            "report_time": datetime.now().isoformat()
        }

    def get_reliability_report(self) -> Dict[str, Any]:
        """Get reliability metrics"""
        error_count = len(self.logs.logs_by_level.get("ERROR", []))
        total_logs = len(self.logs.logs)
        error_rate = (error_count / total_logs * 100) if total_logs > 0 else 0

        return {
            "total_logs": total_logs,
            "error_count": error_count,
            "error_rate": round(error_rate, 2),
            "uptime_seconds": (datetime.now() - self.created_at).total_seconds()
        }


# Global instances
_metrics_collector = MetricsCollector()
_log_aggregator = LogAggregator()
_distributed_tracer = DistributedTracer()
_alert_manager = AlertManager()
_monitoring_dashboard = MonitoringDashboard(
    _metrics_collector,
    _log_aggregator,
    _distributed_tracer,
    _alert_manager
)


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector"""
    return _metrics_collector


def get_log_aggregator() -> LogAggregator:
    """Get global log aggregator"""
    return _log_aggregator


def get_distributed_tracer() -> DistributedTracer:
    """Get global distributed tracer"""
    return _distributed_tracer


def get_alert_manager() -> AlertManager:
    """Get global alert manager"""
    return _alert_manager


def get_monitoring_dashboard() -> MonitoringDashboard:
    """Get global monitoring dashboard"""
    return _monitoring_dashboard


if __name__ == "__main__":
    logger.info("Monitoring & Observability System initialized")
