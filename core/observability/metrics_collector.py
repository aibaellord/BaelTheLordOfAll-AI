"""
BAEL Metrics Collector
=======================

Prometheus-compatible metrics collection.
Tracks system performance and business metrics.

Features:
- Counter, Gauge, Histogram, Timer
- Labels and dimensions
- Aggregations
- Export formats
- Rate calculations
"""

import hashlib
import logging
import math
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricSample:
    """A single metric sample."""
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class Metric:
    """Base metric class."""
    name: str
    description: str = ""
    metric_type: MetricType = MetricType.GAUGE

    # Labels
    label_names: List[str] = field(default_factory=list)

    # Data
    samples: Dict[str, List[MetricSample]] = field(default_factory=dict)

    def _labels_key(self, labels: Dict[str, str]) -> str:
        """Create key from labels."""
        sorted_items = sorted(labels.items())
        return str(sorted_items)

    def record(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record a sample."""
        labels = labels or {}
        key = self._labels_key(labels)

        if key not in self.samples:
            self.samples[key] = []

        self.samples[key].append(MetricSample(value=value, labels=labels))

    def get_current_value(
        self,
        labels: Optional[Dict[str, str]] = None,
    ) -> Optional[float]:
        """Get current value."""
        labels = labels or {}
        key = self._labels_key(labels)

        if key in self.samples and self.samples[key]:
            return self.samples[key][-1].value
        return None

    def to_prometheus(self) -> str:
        """Export in Prometheus format."""
        lines = []
        lines.append(f"# HELP {self.name} {self.description}")
        lines.append(f"# TYPE {self.name} {self.metric_type.value}")

        for key, samples in self.samples.items():
            if samples:
                sample = samples[-1]
                label_str = ",".join(
                    f'{k}="{v}"' for k, v in sample.labels.items()
                )
                if label_str:
                    lines.append(f"{self.name}{{{label_str}}} {sample.value}")
                else:
                    lines.append(f"{self.name} {sample.value}")

        return "\n".join(lines)


class Counter(Metric):
    """
    A counter metric (monotonically increasing).
    """

    def __init__(self, name: str, description: str = "", label_names: List[str] = None):
        super().__init__(
            name=name,
            description=description,
            metric_type=MetricType.COUNTER,
            label_names=label_names or [],
        )
        self._values: Dict[str, float] = {}

    def inc(self, amount: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment counter."""
        labels = labels or {}
        key = self._labels_key(labels)

        if key not in self._values:
            self._values[key] = 0

        self._values[key] += amount
        self.record(self._values[key], labels)

    def get_value(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Get counter value."""
        labels = labels or {}
        key = self._labels_key(labels)
        return self._values.get(key, 0.0)


class Gauge(Metric):
    """
    A gauge metric (can go up or down).
    """

    def __init__(self, name: str, description: str = "", label_names: List[str] = None):
        super().__init__(
            name=name,
            description=description,
            metric_type=MetricType.GAUGE,
            label_names=label_names or [],
        )
        self._values: Dict[str, float] = {}

    def set(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set gauge value."""
        labels = labels or {}
        key = self._labels_key(labels)

        self._values[key] = value
        self.record(value, labels)

    def inc(self, amount: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment gauge."""
        labels = labels or {}
        key = self._labels_key(labels)

        current = self._values.get(key, 0.0)
        self.set(current + amount, labels)

    def dec(self, amount: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Decrement gauge."""
        self.inc(-amount, labels)

    def get_value(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Get gauge value."""
        labels = labels or {}
        key = self._labels_key(labels)
        return self._values.get(key, 0.0)


class Histogram(Metric):
    """
    A histogram metric for distribution tracking.
    """

    DEFAULT_BUCKETS = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]

    def __init__(
        self,
        name: str,
        description: str = "",
        buckets: Optional[List[float]] = None,
        label_names: List[str] = None,
    ):
        super().__init__(
            name=name,
            description=description,
            metric_type=MetricType.HISTOGRAM,
            label_names=label_names or [],
        )

        self.buckets = sorted(buckets or self.DEFAULT_BUCKETS)

        # Per-label-set data
        self._bucket_counts: Dict[str, Dict[float, int]] = {}
        self._sums: Dict[str, float] = {}
        self._counts: Dict[str, int] = {}

    def observe(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record an observation."""
        labels = labels or {}
        key = self._labels_key(labels)

        # Initialize if needed
        if key not in self._bucket_counts:
            self._bucket_counts[key] = {b: 0 for b in self.buckets}
            self._bucket_counts[key][float('inf')] = 0
            self._sums[key] = 0.0
            self._counts[key] = 0

        # Update buckets
        for bucket in self.buckets:
            if value <= bucket:
                self._bucket_counts[key][bucket] += 1
        self._bucket_counts[key][float('inf')] += 1

        # Update sum and count
        self._sums[key] += value
        self._counts[key] += 1

        self.record(value, labels)

    def get_percentile(
        self,
        percentile: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> float:
        """Get approximate percentile from histogram."""
        labels = labels or {}
        key = self._labels_key(labels)

        if key not in self._counts or self._counts[key] == 0:
            return 0.0

        target_count = percentile * self._counts[key] / 100.0
        cumulative = 0

        for bucket in self.buckets:
            cumulative += self._bucket_counts[key].get(bucket, 0)
            if cumulative >= target_count:
                return bucket

        return self.buckets[-1] if self.buckets else 0.0

    def get_stats(
        self,
        labels: Optional[Dict[str, str]] = None,
    ) -> Dict[str, float]:
        """Get histogram statistics."""
        labels = labels or {}
        key = self._labels_key(labels)

        count = self._counts.get(key, 0)
        total = self._sums.get(key, 0.0)

        return {
            "count": count,
            "sum": total,
            "avg": total / count if count > 0 else 0.0,
            "p50": self.get_percentile(50, labels),
            "p95": self.get_percentile(95, labels),
            "p99": self.get_percentile(99, labels),
        }

    def to_prometheus(self) -> str:
        """Export in Prometheus format."""
        lines = []
        lines.append(f"# HELP {self.name} {self.description}")
        lines.append(f"# TYPE {self.name} histogram")

        for key in self._bucket_counts:
            labels_str = key if key != "[]" else ""

            # Buckets
            cumulative = 0
            for bucket in self.buckets + [float('inf')]:
                cumulative += self._bucket_counts[key].get(bucket, 0)
                le = "+Inf" if bucket == float('inf') else str(bucket)
                lines.append(f'{self.name}_bucket{{le="{le}"}} {cumulative}')

            lines.append(f'{self.name}_sum {self._sums.get(key, 0)}')
            lines.append(f'{self.name}_count {self._counts.get(key, 0)}')

        return "\n".join(lines)


class Timer:
    """
    Timer for measuring durations.
    """

    def __init__(self, histogram: Histogram, labels: Optional[Dict[str, str]] = None):
        self.histogram = histogram
        self.labels = labels or {}
        self._start_time: Optional[float] = None

    def start(self) -> "Timer":
        """Start timer."""
        self._start_time = time.time()
        return self

    def stop(self) -> float:
        """Stop timer and record duration."""
        if self._start_time is None:
            return 0.0

        duration = time.time() - self._start_time
        self.histogram.observe(duration, self.labels)
        return duration

    @contextmanager
    def time(self) -> Generator[None, None, None]:
        """Context manager for timing."""
        self.start()
        try:
            yield
        finally:
            self.stop()


class MetricsCollector:
    """
    Metrics collector for BAEL.

    Manages all metrics.
    """

    def __init__(self, prefix: str = "bael"):
        self.prefix = prefix

        # Registered metrics
        self._metrics: Dict[str, Metric] = {}

        # Lock for thread safety
        self._lock = threading.Lock()

        # Built-in metrics
        self._setup_default_metrics()

        # Stats
        self.stats = {
            "metrics_registered": 0,
            "samples_collected": 0,
        }

    def _setup_default_metrics(self) -> None:
        """Setup default system metrics."""
        self.register_counter(
            "requests_total",
            "Total number of requests",
            ["method", "endpoint", "status"],
        )

        self.register_histogram(
            "request_duration_seconds",
            "Request duration in seconds",
            label_names=["method", "endpoint"],
        )

        self.register_gauge(
            "active_connections",
            "Number of active connections",
        )

    def _full_name(self, name: str) -> str:
        """Get full metric name with prefix."""
        return f"{self.prefix}_{name}"

    def register_counter(
        self,
        name: str,
        description: str = "",
        label_names: Optional[List[str]] = None,
    ) -> Counter:
        """Register a counter metric."""
        full_name = self._full_name(name)

        with self._lock:
            if full_name in self._metrics:
                metric = self._metrics[full_name]
                if isinstance(metric, Counter):
                    return metric
                raise ValueError(f"Metric {name} exists with different type")

            counter = Counter(full_name, description, label_names)
            self._metrics[full_name] = counter
            self.stats["metrics_registered"] += 1

            return counter

    def register_gauge(
        self,
        name: str,
        description: str = "",
        label_names: Optional[List[str]] = None,
    ) -> Gauge:
        """Register a gauge metric."""
        full_name = self._full_name(name)

        with self._lock:
            if full_name in self._metrics:
                metric = self._metrics[full_name]
                if isinstance(metric, Gauge):
                    return metric
                raise ValueError(f"Metric {name} exists with different type")

            gauge = Gauge(full_name, description, label_names)
            self._metrics[full_name] = gauge
            self.stats["metrics_registered"] += 1

            return gauge

    def register_histogram(
        self,
        name: str,
        description: str = "",
        buckets: Optional[List[float]] = None,
        label_names: Optional[List[str]] = None,
    ) -> Histogram:
        """Register a histogram metric."""
        full_name = self._full_name(name)

        with self._lock:
            if full_name in self._metrics:
                metric = self._metrics[full_name]
                if isinstance(metric, Histogram):
                    return metric
                raise ValueError(f"Metric {name} exists with different type")

            histogram = Histogram(full_name, description, buckets, label_names)
            self._metrics[full_name] = histogram
            self.stats["metrics_registered"] += 1

            return histogram

    def get_counter(self, name: str) -> Optional[Counter]:
        """Get a counter by name."""
        full_name = self._full_name(name)
        metric = self._metrics.get(full_name)
        return metric if isinstance(metric, Counter) else None

    def get_gauge(self, name: str) -> Optional[Gauge]:
        """Get a gauge by name."""
        full_name = self._full_name(name)
        metric = self._metrics.get(full_name)
        return metric if isinstance(metric, Gauge) else None

    def get_histogram(self, name: str) -> Optional[Histogram]:
        """Get a histogram by name."""
        full_name = self._full_name(name)
        metric = self._metrics.get(full_name)
        return metric if isinstance(metric, Histogram) else None

    def create_timer(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None,
    ) -> Timer:
        """Create a timer for a histogram."""
        histogram = self.get_histogram(name)
        if not histogram:
            histogram = self.register_histogram(name, f"Timer for {name}")
        return Timer(histogram, labels)

    def export_prometheus(self) -> str:
        """Export all metrics in Prometheus format."""
        lines = []

        for metric in self._metrics.values():
            lines.append(metric.to_prometheus())
            lines.append("")

        return "\n".join(lines)

    def export_json(self) -> Dict[str, Any]:
        """Export all metrics as JSON."""
        result = {}

        for name, metric in self._metrics.items():
            if isinstance(metric, Counter):
                result[name] = {"type": "counter", "values": dict(metric._values)}
            elif isinstance(metric, Gauge):
                result[name] = {"type": "gauge", "values": dict(metric._values)}
            elif isinstance(metric, Histogram):
                result[name] = {
                    "type": "histogram",
                    "stats": {k: metric.get_stats() for k in metric._counts.keys()},
                }

        return result

    def get_stats(self) -> Dict[str, Any]:
        """Get collector statistics."""
        return {
            **self.stats,
            "metrics_count": len(self._metrics),
            "metrics": list(self._metrics.keys()),
        }


def demo():
    """Demonstrate metrics collector."""
    print("=" * 60)
    print("BAEL Metrics Collector Demo")
    print("=" * 60)

    collector = MetricsCollector(prefix="demo")

    # Counter
    print("\nCounter:")
    requests = collector.register_counter(
        "http_requests",
        "Total HTTP requests",
        ["method", "status"],
    )

    requests.inc(labels={"method": "GET", "status": "200"})
    requests.inc(labels={"method": "GET", "status": "200"})
    requests.inc(labels={"method": "POST", "status": "201"})
    requests.inc(labels={"method": "GET", "status": "404"})

    print(f"  GET 200: {requests.get_value({'method': 'GET', 'status': '200'})}")
    print(f"  POST 201: {requests.get_value({'method': 'POST', 'status': '201'})}")

    # Gauge
    print("\nGauge:")
    connections = collector.register_gauge("active_conns", "Active connections")

    connections.set(10)
    connections.inc(5)
    connections.dec(3)

    print(f"  Active connections: {connections.get_value()}")

    # Histogram
    print("\nHistogram:")
    durations = collector.register_histogram(
        "request_duration",
        "Request duration",
        buckets=[0.01, 0.05, 0.1, 0.5, 1.0],
    )

    import random
    for _ in range(100):
        durations.observe(random.uniform(0.001, 0.5))

    stats = durations.get_stats()
    print(f"  Count: {stats['count']}")
    print(f"  Avg: {stats['avg']:.4f}s")
    print(f"  P50: {stats['p50']:.4f}s")
    print(f"  P99: {stats['p99']:.4f}s")

    # Timer
    print("\nTimer:")
    timer = collector.create_timer("operation_duration")

    with timer.time():
        time.sleep(0.05)

    timer_stats = collector.get_histogram("operation_duration").get_stats()
    print(f"  Duration: {timer_stats['avg']:.4f}s")

    # Prometheus export
    print("\nPrometheus format (excerpt):")
    prom = collector.export_prometheus()
    for line in prom.split("\n")[:10]:
        print(f"  {line}")

    print(f"\nStats: {collector.get_stats()}")


if __name__ == "__main__":
    demo()
