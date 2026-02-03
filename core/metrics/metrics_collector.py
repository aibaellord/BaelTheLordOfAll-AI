#!/usr/bin/env python3
"""
BAEL - Metrics Collector System
Comprehensive metrics collection and aggregation.

This module provides a complete metrics framework
for monitoring and observability.

Features:
- Counter, Gauge, Histogram, Summary metrics
- Labels and dimensions
- Multiple backends (memory, file)
- Time-series storage
- Aggregation functions
- Metric queries
- Exporters (Prometheus format)
- Alerts and thresholds
- Rate calculations
- Percentile calculations
"""

import asyncio
import bisect
import json
import logging
import math
import os
import statistics
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)

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


class AggregationType(Enum):
    """Aggregation functions."""
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    RATE = "rate"
    P50 = "p50"
    P90 = "p90"
    P95 = "p95"
    P99 = "p99"


class AlertStatus(Enum):
    """Alert status."""
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class MetricConfig:
    """Metric configuration."""
    name: str
    metric_type: MetricType
    description: str = ""
    labels: List[str] = field(default_factory=list)
    buckets: List[float] = field(default_factory=lambda: [.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10])
    quantiles: List[float] = field(default_factory=lambda: [0.5, 0.9, 0.95, 0.99])


@dataclass
class DataPoint:
    """Single metric data point."""
    value: float
    timestamp: float = field(default_factory=time.time)
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class TimeSeries:
    """Time series data."""
    metric_name: str
    labels: Dict[str, str]
    points: deque = field(default_factory=lambda: deque(maxlen=10000))

    def add(self, value: float, timestamp: float = None) -> None:
        self.points.append(DataPoint(
            value=value,
            timestamp=timestamp or time.time(),
            labels=self.labels
        ))

    @property
    def label_key(self) -> str:
        return json.dumps(self.labels, sort_keys=True)


@dataclass
class AlertConfig:
    """Alert configuration."""
    name: str
    metric_name: str
    condition: str  # "gt", "lt", "eq", "ne"
    threshold: float
    duration: float = 60.0  # seconds
    labels: Dict[str, str] = field(default_factory=dict)
    severity: AlertStatus = AlertStatus.WARNING


@dataclass
class Alert:
    """Active alert."""
    config: AlertConfig
    status: AlertStatus = AlertStatus.OK
    value: float = 0.0
    triggered_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    @property
    def is_active(self) -> bool:
        return self.status != AlertStatus.OK and self.resolved_at is None


# =============================================================================
# METRIC IMPLEMENTATIONS
# =============================================================================

class Metric(ABC):
    """Abstract base metric."""

    def __init__(self, config: MetricConfig):
        self.config = config
        self.created_at = time.time()
        self._lock = threading.Lock()

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def type(self) -> MetricType:
        return self.config.metric_type

    @abstractmethod
    def collect(self) -> List[DataPoint]:
        """Collect current metric values."""
        pass


class Counter(Metric):
    """Counter metric (monotonically increasing)."""

    def __init__(self, config: MetricConfig):
        config.metric_type = MetricType.COUNTER
        super().__init__(config)
        self._values: Dict[str, float] = defaultdict(float)

    def inc(self, amount: float = 1, labels: Dict[str, str] = None) -> float:
        """Increment counter."""
        if amount < 0:
            raise ValueError("Counter can only increase")

        key = self._label_key(labels)
        with self._lock:
            self._values[key] += amount
            return self._values[key]

    def get(self, labels: Dict[str, str] = None) -> float:
        """Get current value."""
        key = self._label_key(labels)
        return self._values.get(key, 0)

    def collect(self) -> List[DataPoint]:
        with self._lock:
            return [
                DataPoint(value=v, labels=self._parse_key(k))
                for k, v in self._values.items()
            ]

    def _label_key(self, labels: Dict[str, str] = None) -> str:
        return json.dumps(labels or {}, sort_keys=True)

    def _parse_key(self, key: str) -> Dict[str, str]:
        return json.loads(key) if key else {}


class Gauge(Metric):
    """Gauge metric (can go up and down)."""

    def __init__(self, config: MetricConfig):
        config.metric_type = MetricType.GAUGE
        super().__init__(config)
        self._values: Dict[str, float] = defaultdict(float)

    def set(self, value: float, labels: Dict[str, str] = None) -> None:
        """Set gauge value."""
        key = self._label_key(labels)
        with self._lock:
            self._values[key] = value

    def inc(self, amount: float = 1, labels: Dict[str, str] = None) -> float:
        """Increment gauge."""
        key = self._label_key(labels)
        with self._lock:
            self._values[key] += amount
            return self._values[key]

    def dec(self, amount: float = 1, labels: Dict[str, str] = None) -> float:
        """Decrement gauge."""
        return self.inc(-amount, labels)

    def get(self, labels: Dict[str, str] = None) -> float:
        """Get current value."""
        key = self._label_key(labels)
        return self._values.get(key, 0)

    def collect(self) -> List[DataPoint]:
        with self._lock:
            return [
                DataPoint(value=v, labels=self._parse_key(k))
                for k, v in self._values.items()
            ]

    def _label_key(self, labels: Dict[str, str] = None) -> str:
        return json.dumps(labels or {}, sort_keys=True)

    def _parse_key(self, key: str) -> Dict[str, str]:
        return json.loads(key) if key else {}


class Histogram(Metric):
    """Histogram metric for distributions."""

    def __init__(self, config: MetricConfig):
        config.metric_type = MetricType.HISTOGRAM
        super().__init__(config)
        self.buckets = sorted(config.buckets)
        self._values: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {"sum": 0, "count": 0, **{str(b): 0 for b in self.buckets}}
        )

    def observe(self, value: float, labels: Dict[str, str] = None) -> None:
        """Observe a value."""
        key = self._label_key(labels)
        with self._lock:
            self._values[key]["sum"] += value
            self._values[key]["count"] += 1

            for bucket in self.buckets:
                if value <= bucket:
                    self._values[key][str(bucket)] += 1

    def get_bucket_counts(self, labels: Dict[str, str] = None) -> Dict[str, float]:
        """Get bucket counts."""
        key = self._label_key(labels)
        return dict(self._values.get(key, {}))

    def collect(self) -> List[DataPoint]:
        result = []
        with self._lock:
            for k, v in self._values.items():
                labels = self._parse_key(k)

                # Sum
                result.append(DataPoint(
                    value=v["sum"],
                    labels={**labels, "__type__": "sum"}
                ))

                # Count
                result.append(DataPoint(
                    value=v["count"],
                    labels={**labels, "__type__": "count"}
                ))

                # Buckets
                for bucket in self.buckets:
                    result.append(DataPoint(
                        value=v[str(bucket)],
                        labels={**labels, "__type__": "bucket", "le": str(bucket)}
                    ))

        return result

    def _label_key(self, labels: Dict[str, str] = None) -> str:
        return json.dumps(labels or {}, sort_keys=True)

    def _parse_key(self, key: str) -> Dict[str, str]:
        return json.loads(key) if key else {}


class Summary(Metric):
    """Summary metric for quantiles."""

    def __init__(self, config: MetricConfig, max_age: float = 600):
        config.metric_type = MetricType.SUMMARY
        super().__init__(config)
        self.quantiles = config.quantiles
        self.max_age = max_age
        self._values: Dict[str, List[Tuple[float, float]]] = defaultdict(list)

    def observe(self, value: float, labels: Dict[str, str] = None) -> None:
        """Observe a value."""
        key = self._label_key(labels)
        now = time.time()

        with self._lock:
            # Add new value
            self._values[key].append((now, value))

            # Remove old values
            cutoff = now - self.max_age
            self._values[key] = [
                (t, v) for t, v in self._values[key]
                if t >= cutoff
            ]

    def get_quantile(self, q: float, labels: Dict[str, str] = None) -> Optional[float]:
        """Get a specific quantile."""
        key = self._label_key(labels)
        values = [v for _, v in self._values.get(key, [])]

        if not values:
            return None

        values.sort()
        idx = int(len(values) * q)
        return values[min(idx, len(values) - 1)]

    def collect(self) -> List[DataPoint]:
        result = []
        now = time.time()

        with self._lock:
            for k, entries in self._values.items():
                labels = self._parse_key(k)
                values = [v for t, v in entries if t >= now - self.max_age]

                if not values:
                    continue

                # Sum and count
                result.append(DataPoint(
                    value=sum(values),
                    labels={**labels, "__type__": "sum"}
                ))
                result.append(DataPoint(
                    value=len(values),
                    labels={**labels, "__type__": "count"}
                ))

                # Quantiles
                values.sort()
                for q in self.quantiles:
                    idx = int(len(values) * q)
                    qval = values[min(idx, len(values) - 1)]
                    result.append(DataPoint(
                        value=qval,
                        labels={**labels, "__type__": "quantile", "quantile": str(q)}
                    ))

        return result

    def _label_key(self, labels: Dict[str, str] = None) -> str:
        return json.dumps(labels or {}, sort_keys=True)

    def _parse_key(self, key: str) -> Dict[str, str]:
        return json.loads(key) if key else {}


# =============================================================================
# STORAGE BACKENDS
# =============================================================================

class MetricStorage(ABC):
    """Abstract metric storage."""

    @abstractmethod
    async def store(self, metric_name: str, points: List[DataPoint]) -> None:
        pass

    @abstractmethod
    async def query(
        self,
        metric_name: str,
        start: float,
        end: float,
        labels: Dict[str, str] = None
    ) -> List[DataPoint]:
        pass


class MemoryStorage(MetricStorage):
    """In-memory metric storage."""

    def __init__(self, max_age: float = 3600):
        self.max_age = max_age
        self._series: Dict[str, Dict[str, TimeSeries]] = defaultdict(dict)
        self._lock = asyncio.Lock()

    async def store(self, metric_name: str, points: List[DataPoint]) -> None:
        async with self._lock:
            for point in points:
                key = json.dumps(point.labels, sort_keys=True)

                if key not in self._series[metric_name]:
                    self._series[metric_name][key] = TimeSeries(
                        metric_name=metric_name,
                        labels=point.labels
                    )

                self._series[metric_name][key].add(point.value, point.timestamp)

    async def query(
        self,
        metric_name: str,
        start: float,
        end: float,
        labels: Dict[str, str] = None
    ) -> List[DataPoint]:
        async with self._lock:
            result = []

            for key, series in self._series.get(metric_name, {}).items():
                # Filter by labels
                if labels:
                    if not all(series.labels.get(k) == v for k, v in labels.items()):
                        continue

                # Filter by time
                for point in series.points:
                    if start <= point.timestamp <= end:
                        result.append(point)

            return sorted(result, key=lambda p: p.timestamp)

    async def cleanup(self) -> int:
        """Remove old data points."""
        cutoff = time.time() - self.max_age
        removed = 0

        async with self._lock:
            for metric_series in self._series.values():
                for series in metric_series.values():
                    original_len = len(series.points)
                    series.points = deque(
                        (p for p in series.points if p.timestamp >= cutoff),
                        maxlen=series.points.maxlen
                    )
                    removed += original_len - len(series.points)

        return removed


class FileStorage(MetricStorage):
    """File-based metric storage."""

    def __init__(self, directory: str):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    async def store(self, metric_name: str, points: List[DataPoint]) -> None:
        file_path = self.directory / f"{metric_name}.jsonl"

        lines = []
        for point in points:
            lines.append(json.dumps({
                "value": point.value,
                "timestamp": point.timestamp,
                "labels": point.labels
            }))

        with open(file_path, 'a') as f:
            f.write('\n'.join(lines) + '\n')

    async def query(
        self,
        metric_name: str,
        start: float,
        end: float,
        labels: Dict[str, str] = None
    ) -> List[DataPoint]:
        file_path = self.directory / f"{metric_name}.jsonl"

        if not file_path.exists():
            return []

        result = []

        with open(file_path, 'r') as f:
            for line in f:
                if not line.strip():
                    continue

                data = json.loads(line)

                if not (start <= data["timestamp"] <= end):
                    continue

                if labels:
                    if not all(data["labels"].get(k) == v for k, v in labels.items()):
                        continue

                result.append(DataPoint(
                    value=data["value"],
                    timestamp=data["timestamp"],
                    labels=data["labels"]
                ))

        return sorted(result, key=lambda p: p.timestamp)


# =============================================================================
# AGGREGATION
# =============================================================================

class Aggregator:
    """Metric aggregation utilities."""

    @staticmethod
    def aggregate(
        points: List[DataPoint],
        aggregation: AggregationType,
        window: float = 60.0
    ) -> List[DataPoint]:
        """Aggregate data points."""
        if not points:
            return []

        # Group by window
        windows: Dict[int, List[float]] = defaultdict(list)

        for point in points:
            bucket = int(point.timestamp / window)
            windows[bucket].append(point.value)

        result = []
        for bucket, values in sorted(windows.items()):
            timestamp = bucket * window

            if aggregation == AggregationType.SUM:
                value = sum(values)
            elif aggregation == AggregationType.AVG:
                value = statistics.mean(values)
            elif aggregation == AggregationType.MIN:
                value = min(values)
            elif aggregation == AggregationType.MAX:
                value = max(values)
            elif aggregation == AggregationType.COUNT:
                value = len(values)
            elif aggregation == AggregationType.RATE:
                value = len(values) / window
            elif aggregation == AggregationType.P50:
                value = Aggregator._percentile(values, 0.5)
            elif aggregation == AggregationType.P90:
                value = Aggregator._percentile(values, 0.9)
            elif aggregation == AggregationType.P95:
                value = Aggregator._percentile(values, 0.95)
            elif aggregation == AggregationType.P99:
                value = Aggregator._percentile(values, 0.99)
            else:
                value = statistics.mean(values)

            result.append(DataPoint(value=value, timestamp=timestamp))

        return result

    @staticmethod
    def _percentile(values: List[float], p: float) -> float:
        """Calculate percentile."""
        if not values:
            return 0

        sorted_values = sorted(values)
        idx = int(len(sorted_values) * p)
        return sorted_values[min(idx, len(sorted_values) - 1)]

    @staticmethod
    def rate(points: List[DataPoint], window: float = 60.0) -> List[DataPoint]:
        """Calculate rate of change."""
        if len(points) < 2:
            return []

        result = []
        sorted_points = sorted(points, key=lambda p: p.timestamp)

        for i in range(1, len(sorted_points)):
            prev = sorted_points[i - 1]
            curr = sorted_points[i]

            time_diff = curr.timestamp - prev.timestamp
            if time_diff <= 0:
                continue

            rate = (curr.value - prev.value) / time_diff
            result.append(DataPoint(value=rate, timestamp=curr.timestamp))

        return result


# =============================================================================
# EXPORTERS
# =============================================================================

class MetricExporter(ABC):
    """Abstract metric exporter."""

    @abstractmethod
    def export(self, metrics: Dict[str, Metric]) -> str:
        pass


class PrometheusExporter(MetricExporter):
    """Export metrics in Prometheus format."""

    def export(self, metrics: Dict[str, Metric]) -> str:
        lines = []

        for name, metric in metrics.items():
            # Add help
            lines.append(f"# HELP {name} {metric.config.description}")
            lines.append(f"# TYPE {name} {metric.type.value}")

            for point in metric.collect():
                label_str = self._format_labels(point.labels)
                lines.append(f"{name}{label_str} {point.value}")

        return '\n'.join(lines)

    def _format_labels(self, labels: Dict[str, str]) -> str:
        if not labels:
            return ""

        # Filter internal labels
        filtered = {k: v for k, v in labels.items() if not k.startswith("__")}

        if not filtered:
            return ""

        parts = [f'{k}="{v}"' for k, v in sorted(filtered.items())]
        return "{" + ",".join(parts) + "}"


class JSONExporter(MetricExporter):
    """Export metrics as JSON."""

    def export(self, metrics: Dict[str, Metric]) -> str:
        result = {}

        for name, metric in metrics.items():
            result[name] = {
                "type": metric.type.value,
                "description": metric.config.description,
                "values": [
                    {
                        "value": p.value,
                        "timestamp": p.timestamp,
                        "labels": p.labels
                    }
                    for p in metric.collect()
                ]
            }

        return json.dumps(result, indent=2)


# =============================================================================
# METRICS COLLECTOR
# =============================================================================

class MetricsCollector:
    """
    Master metrics collector for BAEL.

    Provides comprehensive metrics collection and management.
    """

    def __init__(self, storage: MetricStorage = None):
        self.storage = storage or MemoryStorage()
        self.metrics: Dict[str, Metric] = {}
        self.alerts: Dict[str, AlertConfig] = {}
        self.active_alerts: Dict[str, Alert] = {}

        # Exporters
        self.prometheus_exporter = PrometheusExporter()
        self.json_exporter = JSONExporter()

        # Background tasks
        self._running = False
        self._collect_task: Optional[asyncio.Task] = None
        self._alert_task: Optional[asyncio.Task] = None

        # Callbacks
        self.on_alert: List[Callable[[Alert], None]] = []

    # Metric Creation
    def counter(
        self,
        name: str,
        description: str = "",
        labels: List[str] = None
    ) -> Counter:
        """Create or get a counter metric."""
        if name not in self.metrics:
            config = MetricConfig(
                name=name,
                metric_type=MetricType.COUNTER,
                description=description,
                labels=labels or []
            )
            self.metrics[name] = Counter(config)
        return self.metrics[name]

    def gauge(
        self,
        name: str,
        description: str = "",
        labels: List[str] = None
    ) -> Gauge:
        """Create or get a gauge metric."""
        if name not in self.metrics:
            config = MetricConfig(
                name=name,
                metric_type=MetricType.GAUGE,
                description=description,
                labels=labels or []
            )
            self.metrics[name] = Gauge(config)
        return self.metrics[name]

    def histogram(
        self,
        name: str,
        description: str = "",
        labels: List[str] = None,
        buckets: List[float] = None
    ) -> Histogram:
        """Create or get a histogram metric."""
        if name not in self.metrics:
            config = MetricConfig(
                name=name,
                metric_type=MetricType.HISTOGRAM,
                description=description,
                labels=labels or [],
                buckets=buckets or [.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10]
            )
            self.metrics[name] = Histogram(config)
        return self.metrics[name]

    def summary(
        self,
        name: str,
        description: str = "",
        labels: List[str] = None,
        quantiles: List[float] = None
    ) -> Summary:
        """Create or get a summary metric."""
        if name not in self.metrics:
            config = MetricConfig(
                name=name,
                metric_type=MetricType.SUMMARY,
                description=description,
                labels=labels or [],
                quantiles=quantiles or [0.5, 0.9, 0.95, 0.99]
            )
            self.metrics[name] = Summary(config)
        return self.metrics[name]

    # Collection
    async def collect_all(self) -> None:
        """Collect and store all metrics."""
        for name, metric in self.metrics.items():
            points = metric.collect()
            if points:
                await self.storage.store(name, points)

    # Queries
    async def query(
        self,
        metric_name: str,
        start: float = None,
        end: float = None,
        labels: Dict[str, str] = None,
        aggregation: AggregationType = None,
        window: float = 60.0
    ) -> List[DataPoint]:
        """Query metric data."""
        start = start or (time.time() - 3600)
        end = end or time.time()

        points = await self.storage.query(metric_name, start, end, labels)

        if aggregation:
            points = Aggregator.aggregate(points, aggregation, window)

        return points

    async def query_instant(
        self,
        metric_name: str,
        labels: Dict[str, str] = None
    ) -> Optional[float]:
        """Get current metric value."""
        if metric_name in self.metrics:
            metric = self.metrics[metric_name]

            if isinstance(metric, (Counter, Gauge)):
                return metric.get(labels)

        # Query storage
        now = time.time()
        points = await self.storage.query(metric_name, now - 60, now, labels)

        if points:
            return points[-1].value

        return None

    # Alerts
    def add_alert(
        self,
        name: str,
        metric_name: str,
        condition: str,
        threshold: float,
        duration: float = 60.0,
        labels: Dict[str, str] = None,
        severity: AlertStatus = AlertStatus.WARNING
    ) -> AlertConfig:
        """Add an alert rule."""
        config = AlertConfig(
            name=name,
            metric_name=metric_name,
            condition=condition,
            threshold=threshold,
            duration=duration,
            labels=labels or {},
            severity=severity
        )
        self.alerts[name] = config
        return config

    async def check_alerts(self) -> List[Alert]:
        """Check all alert conditions."""
        triggered = []

        for name, config in self.alerts.items():
            value = await self.query_instant(config.metric_name, config.labels)

            if value is None:
                continue

            is_firing = self._check_condition(value, config.condition, config.threshold)

            if is_firing:
                if name not in self.active_alerts:
                    alert = Alert(
                        config=config,
                        status=config.severity,
                        value=value,
                        triggered_at=datetime.now()
                    )
                    self.active_alerts[name] = alert
                    triggered.append(alert)

                    for callback in self.on_alert:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(alert)
                            else:
                                callback(alert)
                        except:
                            pass
            else:
                if name in self.active_alerts:
                    alert = self.active_alerts[name]
                    alert.status = AlertStatus.OK
                    alert.resolved_at = datetime.now()
                    del self.active_alerts[name]

        return triggered

    def _check_condition(
        self,
        value: float,
        condition: str,
        threshold: float
    ) -> bool:
        """Check alert condition."""
        if condition == "gt":
            return value > threshold
        elif condition == "gte":
            return value >= threshold
        elif condition == "lt":
            return value < threshold
        elif condition == "lte":
            return value <= threshold
        elif condition == "eq":
            return value == threshold
        elif condition == "ne":
            return value != threshold
        return False

    # Export
    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        return self.prometheus_exporter.export(self.metrics)

    def export_json(self) -> str:
        """Export metrics as JSON."""
        return self.json_exporter.export(self.metrics)

    # Lifecycle
    async def start(self, collect_interval: float = 10.0) -> None:
        """Start background collection."""
        self._running = True
        self._collect_task = asyncio.create_task(
            self._collection_loop(collect_interval)
        )
        self._alert_task = asyncio.create_task(
            self._alert_loop()
        )

    async def stop(self) -> None:
        """Stop background collection."""
        self._running = False

        if self._collect_task:
            self._collect_task.cancel()
            try:
                await self._collect_task
            except asyncio.CancelledError:
                pass

        if self._alert_task:
            self._alert_task.cancel()
            try:
                await self._alert_task
            except asyncio.CancelledError:
                pass

    async def _collection_loop(self, interval: float) -> None:
        """Background collection loop."""
        while self._running:
            try:
                await self.collect_all()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Collection error: {e}")
                await asyncio.sleep(1)

    async def _alert_loop(self) -> None:
        """Background alert checking."""
        while self._running:
            try:
                await self.check_alerts()
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Alert check error: {e}")
                await asyncio.sleep(5)

    # Statistics
    def get_statistics(self) -> Dict[str, Any]:
        """Get collector statistics."""
        return {
            "metrics_count": len(self.metrics),
            "alerts_count": len(self.alerts),
            "active_alerts": len(self.active_alerts),
            "metrics": list(self.metrics.keys())
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Metrics Collector System."""
    print("=" * 70)
    print("BAEL - METRICS COLLECTOR SYSTEM DEMO")
    print("Comprehensive Metrics Collection")
    print("=" * 70)
    print()

    collector = MetricsCollector()

    # 1. Create Metrics
    print("1. CREATING METRICS:")
    print("-" * 40)

    requests_total = collector.counter(
        "http_requests_total",
        "Total HTTP requests",
        labels=["method", "status"]
    )
    print("   Created: http_requests_total (counter)")

    active_connections = collector.gauge(
        "active_connections",
        "Active connections"
    )
    print("   Created: active_connections (gauge)")

    request_duration = collector.histogram(
        "http_request_duration_seconds",
        "Request duration in seconds",
        buckets=[0.01, 0.05, 0.1, 0.5, 1, 5]
    )
    print("   Created: http_request_duration_seconds (histogram)")

    response_size = collector.summary(
        "http_response_size_bytes",
        "Response size in bytes"
    )
    print("   Created: http_response_size_bytes (summary)")
    print()

    # 2. Record Values
    print("2. RECORDING VALUES:")
    print("-" * 40)

    # Counter
    for _ in range(10):
        requests_total.inc(labels={"method": "GET", "status": "200"})
    requests_total.inc(3, labels={"method": "POST", "status": "201"})
    requests_total.inc(2, labels={"method": "GET", "status": "404"})

    print(f"   GET 200: {requests_total.get({'method': 'GET', 'status': '200'})}")
    print(f"   POST 201: {requests_total.get({'method': 'POST', 'status': '201'})}")

    # Gauge
    active_connections.set(50)
    active_connections.inc(10)
    active_connections.dec(5)
    print(f"   Active connections: {active_connections.get()}")

    # Histogram
    import random
    for _ in range(100):
        request_duration.observe(random.uniform(0.01, 2))

    buckets = request_duration.get_bucket_counts()
    print(f"   Request duration observations: {int(buckets.get('count', 0))}")

    # Summary
    for _ in range(100):
        response_size.observe(random.uniform(100, 10000))

    p50 = response_size.get_quantile(0.5)
    p99 = response_size.get_quantile(0.99)
    print(f"   Response size p50: {p50:.0f} bytes")
    print(f"   Response size p99: {p99:.0f} bytes")
    print()

    # 3. Collection
    print("3. COLLECTING METRICS:")
    print("-" * 40)

    await collector.collect_all()
    print("   Metrics collected to storage")
    print()

    # 4. Queries
    print("4. QUERYING METRICS:")
    print("-" * 40)

    now = time.time()
    points = await collector.query(
        "http_requests_total",
        start=now - 3600,
        end=now
    )
    print(f"   http_requests_total points: {len(points)}")

    instant = await collector.query_instant("active_connections")
    print(f"   active_connections instant: {instant}")
    print()

    # 5. Aggregation
    print("5. AGGREGATION:")
    print("-" * 40)

    # Add more points for aggregation demo
    for i in range(60):
        requests_total.inc(random.randint(1, 10))

    await collector.collect_all()

    points = await collector.query(
        "http_requests_total",
        start=now - 300,
        end=now + 60,
        aggregation=AggregationType.SUM,
        window=30
    )
    print(f"   SUM aggregated points: {len(points)}")

    rate_points = await collector.query(
        "http_requests_total",
        start=now - 300,
        end=now + 60,
        aggregation=AggregationType.RATE,
        window=30
    )
    print(f"   RATE aggregated points: {len(rate_points)}")
    print()

    # 6. Alerts
    print("6. ALERTS:")
    print("-" * 40)

    collector.add_alert(
        name="high_error_rate",
        metric_name="http_requests_total",
        condition="gt",
        threshold=100,
        severity=AlertStatus.WARNING
    )
    print("   Added: high_error_rate alert")

    collector.add_alert(
        name="too_many_connections",
        metric_name="active_connections",
        condition="gt",
        threshold=40,
        severity=AlertStatus.CRITICAL
    )
    print("   Added: too_many_connections alert")

    triggered = await collector.check_alerts()
    print(f"   Triggered alerts: {len(triggered)}")

    for alert in collector.active_alerts.values():
        print(f"      - {alert.config.name}: {alert.status.value} (value={alert.value})")
    print()

    # 7. Export Prometheus
    print("7. PROMETHEUS EXPORT:")
    print("-" * 40)

    prometheus_output = collector.export_prometheus()
    lines = prometheus_output.split('\n')[:10]
    for line in lines:
        print(f"   {line}")
    print("   ...")
    print()

    # 8. Export JSON
    print("8. JSON EXPORT:")
    print("-" * 40)

    json_output = collector.export_json()
    data = json.loads(json_output)
    for metric_name in list(data.keys())[:2]:
        print(f"   {metric_name}:")
        print(f"      type: {data[metric_name]['type']}")
        print(f"      values: {len(data[metric_name]['values'])} points")
    print()

    # 9. Timer Context
    print("9. TIMING OPERATIONS:")
    print("-" * 40)

    import time as time_module

    start = time_module.time()
    await asyncio.sleep(0.1)
    duration = time_module.time() - start
    request_duration.observe(duration)

    print(f"   Recorded operation duration: {duration:.3f}s")
    print()

    # 10. Statistics
    print("10. STATISTICS:")
    print("-" * 40)

    stats = collector.get_statistics()
    print(f"    Metrics count: {stats['metrics_count']}")
    print(f"    Alerts count: {stats['alerts_count']}")
    print(f"    Active alerts: {stats['active_alerts']}")
    print(f"    Metric names: {stats['metrics']}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Metrics Collector Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
