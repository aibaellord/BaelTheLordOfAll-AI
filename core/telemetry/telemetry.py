"""
BAEL - Telemetry & Monitoring
Advanced observability and metrics collection.

Features:
- Metrics collection
- Distributed tracing
- Log aggregation
- Alerting
- Dashboard export
- Performance profiling
"""

import asyncio
import functools
import json
import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.Telemetry")


# =============================================================================
# TYPES & ENUMS
# =============================================================================

class MetricType(Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SpanStatus(Enum):
    """Trace span status."""
    OK = "ok"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class MetricPoint:
    """A single metric data point."""
    name: str
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE


@dataclass
class HistogramBucket:
    """A histogram bucket."""
    le: float  # Less than or equal
    count: int


@dataclass
class Span:
    """A trace span."""
    trace_id: str
    span_id: str
    parent_id: Optional[str]
    name: str

    # Timing
    start_time: float
    end_time: Optional[float] = None

    # Status
    status: SpanStatus = SpanStatus.OK
    error: Optional[str] = None

    # Context
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0


@dataclass
class Alert:
    """An alert."""
    id: str
    name: str
    severity: AlertSeverity
    message: str

    # Context
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)

    # Timing
    fired_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None

    # Status
    is_resolved: bool = False


# =============================================================================
# METRICS COLLECTOR
# =============================================================================

class MetricsCollector:
    """Collects and stores metrics."""

    def __init__(self, retention_hours: int = 24):
        self.retention = timedelta(hours=retention_hours)

        # Storage
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._summaries: Dict[str, List[float]] = defaultdict(list)

        # Time series
        self._time_series: Dict[str, List[MetricPoint]] = defaultdict(list)

        # Histogram bucket boundaries
        self._histogram_buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]

        self._lock = threading.Lock()

    def inc(self, name: str, value: float = 1, labels: Dict[str, str] = None) -> None:
        """Increment a counter."""
        key = self._make_key(name, labels)
        with self._lock:
            self._counters[key] += value
            self._record_point(name, self._counters[key], labels, MetricType.COUNTER)

    def dec(self, name: str, value: float = 1, labels: Dict[str, str] = None) -> None:
        """Decrement a counter (for gauges)."""
        key = self._make_key(name, labels)
        with self._lock:
            self._counters[key] -= value

    def set(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        """Set a gauge value."""
        key = self._make_key(name, labels)
        with self._lock:
            self._gauges[key] = value
            self._record_point(name, value, labels, MetricType.GAUGE)

    def observe(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        """Observe a histogram/summary value."""
        key = self._make_key(name, labels)
        with self._lock:
            self._histograms[key].append(value)
            self._summaries[key].append(value)
            self._record_point(name, value, labels, MetricType.HISTOGRAM)

            # Keep only recent values for summary
            if len(self._summaries[key]) > 10000:
                self._summaries[key] = self._summaries[key][-5000:]

    def _make_key(self, name: str, labels: Dict[str, str] = None) -> str:
        """Create a unique key for metric."""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def _record_point(
        self,
        name: str,
        value: float,
        labels: Dict[str, str] = None,
        metric_type: MetricType = MetricType.GAUGE
    ) -> None:
        """Record a time series point."""
        point = MetricPoint(
            name=name,
            value=value,
            timestamp=datetime.now(),
            labels=labels or {},
            metric_type=metric_type
        )
        self._time_series[name].append(point)

        # Prune old points
        cutoff = datetime.now() - self.retention
        self._time_series[name] = [
            p for p in self._time_series[name]
            if p.timestamp > cutoff
        ]

    def get(self, name: str, labels: Dict[str, str] = None) -> Optional[float]:
        """Get current metric value."""
        key = self._make_key(name, labels)

        if key in self._counters:
            return self._counters[key]
        if key in self._gauges:
            return self._gauges[key]

        return None

    def get_histogram(self, name: str, labels: Dict[str, str] = None) -> Dict[str, Any]:
        """Get histogram statistics."""
        key = self._make_key(name, labels)
        values = self._histograms.get(key, [])

        if not values:
            return {"count": 0, "sum": 0, "buckets": []}

        # Calculate bucket counts
        buckets = []
        for boundary in self._histogram_buckets:
            count = sum(1 for v in values if v <= boundary)
            buckets.append(HistogramBucket(le=boundary, count=count))
        buckets.append(HistogramBucket(le=float('inf'), count=len(values)))

        return {
            "count": len(values),
            "sum": sum(values),
            "buckets": buckets
        }

    def get_summary(self, name: str, labels: Dict[str, str] = None) -> Dict[str, Any]:
        """Get summary statistics."""
        key = self._make_key(name, labels)
        values = sorted(self._summaries.get(key, []))

        if not values:
            return {"count": 0, "sum": 0, "quantiles": {}}

        def percentile(p: float) -> float:
            k = (len(values) - 1) * p
            f = int(k)
            c = f + 1 if f < len(values) - 1 else f
            return values[f] + (k - f) * (values[c] - values[f])

        return {
            "count": len(values),
            "sum": sum(values),
            "quantiles": {
                "p50": percentile(0.5),
                "p90": percentile(0.9),
                "p95": percentile(0.95),
                "p99": percentile(0.99)
            }
        }

    def get_time_series(
        self,
        name: str,
        start: datetime = None,
        end: datetime = None
    ) -> List[MetricPoint]:
        """Get time series data."""
        points = self._time_series.get(name, [])

        if start:
            points = [p for p in points if p.timestamp >= start]
        if end:
            points = [p for p in points if p.timestamp <= end]

        return points

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []

        # Counters
        for key, value in self._counters.items():
            name, labels = self._parse_key(key)
            labels_str = self._format_labels(labels)
            lines.append(f"{name}{labels_str} {value}")

        # Gauges
        for key, value in self._gauges.items():
            name, labels = self._parse_key(key)
            labels_str = self._format_labels(labels)
            lines.append(f"{name}{labels_str} {value}")

        # Histograms
        for key in self._histograms:
            name, labels = self._parse_key(key)
            hist = self.get_histogram(name, labels)
            labels_str = self._format_labels(labels)

            for bucket in hist["buckets"]:
                le = bucket.le if bucket.le != float('inf') else "+Inf"
                lines.append(f'{name}_bucket{{le="{le}"{labels_str[1:] if labels_str else "}"} {bucket.count}')
            lines.append(f"{name}_count{labels_str} {hist['count']}")
            lines.append(f"{name}_sum{labels_str} {hist['sum']}")

        return "\n".join(lines)

    def _parse_key(self, key: str) -> Tuple[str, Dict[str, str]]:
        """Parse metric key into name and labels."""
        if '{' not in key:
            return key, {}

        name = key[:key.index('{')]
        labels_str = key[key.index('{')+1:key.index('}')]
        labels = {}

        for pair in labels_str.split(','):
            if '=' in pair:
                k, v = pair.split('=', 1)
                labels[k] = v

        return name, labels

    def _format_labels(self, labels: Dict[str, str]) -> str:
        """Format labels for Prometheus."""
        if not labels:
            return ""
        pairs = [f'{k}="{v}"' for k, v in labels.items()]
        return "{" + ",".join(pairs) + "}"


# =============================================================================
# TRACER
# =============================================================================

class Tracer:
    """Distributed tracing."""

    def __init__(self):
        self._spans: Dict[str, Span] = {}
        self._active_spans: Dict[str, str] = {}  # context_id -> span_id
        self._span_counter = 0
        self._trace_counter = 0

    def start_span(
        self,
        name: str,
        parent_span: Span = None,
        attributes: Dict[str, Any] = None
    ) -> Span:
        """Start a new span."""
        self._span_counter += 1
        span_id = f"span_{self._span_counter}"

        if parent_span:
            trace_id = parent_span.trace_id
            parent_id = parent_span.span_id
        else:
            self._trace_counter += 1
            trace_id = f"trace_{self._trace_counter}"
            parent_id = None

        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_id=parent_id,
            name=name,
            start_time=time.time(),
            attributes=attributes or {}
        )

        self._spans[span_id] = span
        return span

    def end_span(
        self,
        span: Span,
        status: SpanStatus = SpanStatus.OK,
        error: str = None
    ) -> None:
        """End a span."""
        span.end_time = time.time()
        span.status = status
        span.error = error

    def add_event(
        self,
        span: Span,
        name: str,
        attributes: Dict[str, Any] = None
    ) -> None:
        """Add an event to a span."""
        span.events.append({
            "name": name,
            "timestamp": time.time(),
            "attributes": attributes or {}
        })

    def get_trace(self, trace_id: str) -> List[Span]:
        """Get all spans in a trace."""
        return [s for s in self._spans.values() if s.trace_id == trace_id]

    def trace(self, name: str = None) -> Callable:
        """Decorator for automatic tracing."""
        def decorator(func: Callable) -> Callable:
            span_name = name or func.__name__

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                span = self.start_span(span_name)
                try:
                    result = await func(*args, **kwargs)
                    self.end_span(span, SpanStatus.OK)
                    return result
                except Exception as e:
                    self.end_span(span, SpanStatus.ERROR, str(e))
                    raise

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                span = self.start_span(span_name)
                try:
                    result = func(*args, **kwargs)
                    self.end_span(span, SpanStatus.OK)
                    return result
                except Exception as e:
                    self.end_span(span, SpanStatus.ERROR, str(e))
                    raise

            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper

        return decorator

    def export_jaeger(self, trace_id: str) -> Dict[str, Any]:
        """Export trace in Jaeger format."""
        spans = self.get_trace(trace_id)

        return {
            "traceID": trace_id,
            "spans": [
                {
                    "spanID": s.span_id,
                    "parentSpanID": s.parent_id,
                    "operationName": s.name,
                    "startTime": int(s.start_time * 1000000),
                    "duration": int(s.duration_ms * 1000),
                    "tags": [{"key": k, "value": v} for k, v in s.attributes.items()],
                    "logs": [
                        {
                            "timestamp": int(e["timestamp"] * 1000000),
                            "fields": [{"key": "event", "value": e["name"]}]
                        }
                        for e in s.events
                    ]
                }
                for s in spans
            ]
        }


# =============================================================================
# ALERTING
# =============================================================================

class AlertManager:
    """Manages alerts."""

    def __init__(self):
        self._rules: Dict[str, Dict[str, Any]] = {}
        self._alerts: Dict[str, Alert] = {}
        self._handlers: List[Callable[[Alert], None]] = []

    def add_rule(
        self,
        name: str,
        condition: Callable[[], bool],
        severity: AlertSeverity,
        message: str,
        labels: Dict[str, str] = None
    ) -> None:
        """Add an alert rule."""
        self._rules[name] = {
            "condition": condition,
            "severity": severity,
            "message": message,
            "labels": labels or {}
        }

    def remove_rule(self, name: str) -> None:
        """Remove an alert rule."""
        self._rules.pop(name, None)

    def add_handler(self, handler: Callable[[Alert], None]) -> None:
        """Add an alert handler."""
        self._handlers.append(handler)

    async def evaluate(self) -> List[Alert]:
        """Evaluate all alert rules."""
        new_alerts = []

        for name, rule in self._rules.items():
            try:
                is_firing = rule["condition"]()

                if is_firing:
                    if name not in self._alerts or self._alerts[name].is_resolved:
                        # New alert
                        alert = Alert(
                            id=f"alert_{name}_{time.time()}",
                            name=name,
                            severity=rule["severity"],
                            message=rule["message"],
                            labels=rule["labels"]
                        )
                        self._alerts[name] = alert
                        new_alerts.append(alert)

                        # Notify handlers
                        for handler in self._handlers:
                            try:
                                handler(alert)
                            except Exception as e:
                                logger.error(f"Alert handler error: {e}")
                else:
                    # Resolve if was firing
                    if name in self._alerts and not self._alerts[name].is_resolved:
                        self._alerts[name].is_resolved = True
                        self._alerts[name].resolved_at = datetime.now()

            except Exception as e:
                logger.error(f"Alert evaluation error for {name}: {e}")

        return new_alerts

    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts."""
        return [a for a in self._alerts.values() if not a.is_resolved]

    def get_alert_history(
        self,
        since: datetime = None,
        severity: AlertSeverity = None
    ) -> List[Alert]:
        """Get alert history."""
        alerts = list(self._alerts.values())

        if since:
            alerts = [a for a in alerts if a.fired_at >= since]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        return sorted(alerts, key=lambda a: a.fired_at, reverse=True)


# =============================================================================
# PROFILER
# =============================================================================

class Profiler:
    """Performance profiler."""

    def __init__(self):
        self._profiles: Dict[str, List[float]] = defaultdict(list)
        self._active_profiles: Dict[str, float] = {}

    def start(self, name: str) -> None:
        """Start profiling a section."""
        self._active_profiles[name] = time.perf_counter()

    def stop(self, name: str) -> float:
        """Stop profiling and return duration."""
        if name not in self._active_profiles:
            return 0.0

        start = self._active_profiles.pop(name)
        duration = time.perf_counter() - start
        self._profiles[name].append(duration)

        return duration

    def profile(self, name: str = None) -> Callable:
        """Decorator for profiling."""
        def decorator(func: Callable) -> Callable:
            profile_name = name or func.__name__

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                self.start(profile_name)
                try:
                    return await func(*args, **kwargs)
                finally:
                    self.stop(profile_name)

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                self.start(profile_name)
                try:
                    return func(*args, **kwargs)
                finally:
                    self.stop(profile_name)

            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper

        return decorator

    def get_stats(self, name: str) -> Dict[str, float]:
        """Get profiling statistics."""
        durations = self._profiles.get(name, [])

        if not durations:
            return {"count": 0}

        return {
            "count": len(durations),
            "total": sum(durations),
            "mean": sum(durations) / len(durations),
            "min": min(durations),
            "max": max(durations),
            "p50": sorted(durations)[len(durations) // 2],
            "p95": sorted(durations)[int(len(durations) * 0.95)] if len(durations) >= 20 else max(durations)
        }

    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """Get all profiling statistics."""
        return {name: self.get_stats(name) for name in self._profiles}

    def reset(self, name: str = None) -> None:
        """Reset profiling data."""
        if name:
            self._profiles.pop(name, None)
        else:
            self._profiles.clear()


# =============================================================================
# TELEMETRY MANAGER
# =============================================================================

class TelemetryManager:
    """Central telemetry management."""

    def __init__(self):
        self.metrics = MetricsCollector()
        self.tracer = Tracer()
        self.alerts = AlertManager()
        self.profiler = Profiler()

        self._running = False

    async def start(self) -> None:
        """Start telemetry collection."""
        self._running = True

        # Start alert evaluation loop
        asyncio.create_task(self._alert_loop())

        logger.info("Telemetry manager started")

    async def stop(self) -> None:
        """Stop telemetry collection."""
        self._running = False
        logger.info("Telemetry manager stopped")

    async def _alert_loop(self) -> None:
        """Periodic alert evaluation."""
        while self._running:
            await asyncio.sleep(30)  # Evaluate every 30 seconds
            await self.alerts.evaluate()

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for dashboard."""
        return {
            "metrics": {
                "prometheus": self.metrics.export_prometheus()
            },
            "traces": {
                "recent": list(self.tracer._spans.values())[-10:]
            },
            "alerts": {
                "active": [
                    {
                        "name": a.name,
                        "severity": a.severity.value,
                        "message": a.message,
                        "fired_at": a.fired_at.isoformat()
                    }
                    for a in self.alerts.get_active_alerts()
                ]
            },
            "profiles": self.profiler.get_all_stats()
        }


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Test telemetry."""
    telemetry = TelemetryManager()
    await telemetry.start()

    # Test metrics
    print("Testing metrics...")
    telemetry.metrics.inc("requests_total", labels={"method": "GET", "path": "/api"})
    telemetry.metrics.inc("requests_total", labels={"method": "GET", "path": "/api"})
    telemetry.metrics.set("active_connections", 5)

    for i in range(10):
        telemetry.metrics.observe("request_duration_seconds", 0.1 + i * 0.05)

    print(f"Request count: {telemetry.metrics.get('requests_total', {'method': 'GET', 'path': '/api'})}")
    print(f"Duration summary: {telemetry.metrics.get_summary('request_duration_seconds')}")

    # Test tracing
    print("\nTesting tracing...")
    parent_span = telemetry.tracer.start_span("main_operation")
    child_span = telemetry.tracer.start_span("sub_operation", parent_span)
    telemetry.tracer.add_event(child_span, "processing_started")
    await asyncio.sleep(0.1)
    telemetry.tracer.end_span(child_span)
    telemetry.tracer.end_span(parent_span)

    print(f"Trace: {telemetry.tracer.export_jaeger(parent_span.trace_id)}")

    # Test profiling
    print("\nTesting profiling...")

    @telemetry.profiler.profile("test_function")
    async def test_function():
        await asyncio.sleep(0.1)

    for _ in range(5):
        await test_function()

    print(f"Profile stats: {telemetry.profiler.get_stats('test_function')}")

    # Test alerts
    print("\nTesting alerts...")
    telemetry.alerts.add_rule(
        "high_error_rate",
        lambda: True,  # Always fires for testing
        AlertSeverity.WARNING,
        "Error rate is high",
        {"service": "api"}
    )

    await telemetry.alerts.evaluate()
    print(f"Active alerts: {len(telemetry.alerts.get_active_alerts())}")

    # Export prometheus format
    print("\n" + "=" * 40)
    print("Prometheus metrics:")
    print(telemetry.metrics.export_prometheus())

    await telemetry.stop()


if __name__ == "__main__":
    asyncio.run(main())
