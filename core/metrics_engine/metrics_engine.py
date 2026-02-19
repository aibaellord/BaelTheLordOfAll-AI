"""
BAEL Metrics Engine
===================

Prometheus-compatible metrics collection and export.

"Ba'el quantifies all aspects of existence." — Ba'el
"""

import asyncio
import logging
import math
import time
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Callable, Union
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import defaultdict
import statistics

logger = logging.getLogger("BAEL.Metrics")


# ============================================================================
# ENUMS
# ============================================================================

class MetricType(Enum):
    """Metric types."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class AggregationType(Enum):
    """Aggregation types."""
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    LAST = "last"
    RATE = "rate"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class MetricLabels:
    """Labels for a metric."""
    labels: Dict[str, str] = field(default_factory=dict)

    def __hash__(self):
        """Hash for use as dict key."""
        return hash(tuple(sorted(self.labels.items())))

    def __eq__(self, other):
        """Compare labels."""
        if isinstance(other, MetricLabels):
            return self.labels == other.labels
        return False

    def to_prometheus(self) -> str:
        """Convert to Prometheus label format."""
        if not self.labels:
            return ""

        pairs = [f'{k}="{v}"' for k, v in sorted(self.labels.items())]
        return "{" + ",".join(pairs) + "}"


@dataclass
class MetricValue:
    """A metric value."""
    value: float
    timestamp: float = field(default_factory=time.time)
    labels: MetricLabels = field(default_factory=MetricLabels)


# ============================================================================
# COUNTER
# ============================================================================

class Counter:
    """
    A monotonically increasing counter.

    Only increases (or resets).
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        label_names: Optional[List[str]] = None
    ):
        """Initialize counter."""
        self.name = name
        self.description = description
        self.label_names = label_names or []
        self.metric_type = MetricType.COUNTER

        self._values: Dict[MetricLabels, float] = defaultdict(float)
        self._created: Dict[MetricLabels, float] = {}
        self._lock = threading.Lock()

    def inc(self, value: float = 1.0, **labels) -> None:
        """Increment the counter."""
        if value < 0:
            raise ValueError("Counter can only increase")

        label_key = MetricLabels(labels)

        with self._lock:
            if label_key not in self._created:
                self._created[label_key] = time.time()

            self._values[label_key] += value

    def get(self, **labels) -> float:
        """Get counter value."""
        label_key = MetricLabels(labels)
        return self._values.get(label_key, 0.0)

    def reset(self, **labels) -> None:
        """Reset counter (should rarely be used)."""
        label_key = MetricLabels(labels)

        with self._lock:
            self._values[label_key] = 0.0
            self._created[label_key] = time.time()

    def collect(self) -> List[MetricValue]:
        """Collect all values."""
        with self._lock:
            return [
                MetricValue(
                    value=value,
                    labels=labels
                )
                for labels, value in self._values.items()
            ]

    def to_prometheus(self) -> str:
        """Export in Prometheus format."""
        lines = []

        lines.append(f"# HELP {self.name} {self.description}")
        lines.append(f"# TYPE {self.name} counter")

        with self._lock:
            for labels, value in self._values.items():
                label_str = labels.to_prometheus()
                lines.append(f"{self.name}{label_str} {value}")

        return "\n".join(lines)


# ============================================================================
# GAUGE
# ============================================================================

class Gauge:
    """
    A gauge that can go up or down.

    Represents a current value like temperature.
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        label_names: Optional[List[str]] = None
    ):
        """Initialize gauge."""
        self.name = name
        self.description = description
        self.label_names = label_names or []
        self.metric_type = MetricType.GAUGE

        self._values: Dict[MetricLabels, float] = {}
        self._lock = threading.Lock()

    def set(self, value: float, **labels) -> None:
        """Set gauge value."""
        label_key = MetricLabels(labels)

        with self._lock:
            self._values[label_key] = value

    def inc(self, value: float = 1.0, **labels) -> None:
        """Increment gauge."""
        label_key = MetricLabels(labels)

        with self._lock:
            current = self._values.get(label_key, 0.0)
            self._values[label_key] = current + value

    def dec(self, value: float = 1.0, **labels) -> None:
        """Decrement gauge."""
        label_key = MetricLabels(labels)

        with self._lock:
            current = self._values.get(label_key, 0.0)
            self._values[label_key] = current - value

    def get(self, **labels) -> float:
        """Get gauge value."""
        label_key = MetricLabels(labels)
        return self._values.get(label_key, 0.0)

    def set_to_current_time(self, **labels) -> None:
        """Set gauge to current timestamp."""
        self.set(time.time(), **labels)

    def track_inprogress(self, **labels):
        """Context manager to track in-progress operations."""
        return _GaugeInProgress(self, labels)

    def collect(self) -> List[MetricValue]:
        """Collect all values."""
        with self._lock:
            return [
                MetricValue(
                    value=value,
                    labels=labels
                )
                for labels, value in self._values.items()
            ]

    def to_prometheus(self) -> str:
        """Export in Prometheus format."""
        lines = []

        lines.append(f"# HELP {self.name} {self.description}")
        lines.append(f"# TYPE {self.name} gauge")

        with self._lock:
            for labels, value in self._values.items():
                label_str = labels.to_prometheus()
                lines.append(f"{self.name}{label_str} {value}")

        return "\n".join(lines)


class _GaugeInProgress:
    """Context manager for tracking in-progress operations."""

    def __init__(self, gauge: Gauge, labels: Dict[str, str]):
        self.gauge = gauge
        self.labels = labels

    def __enter__(self):
        self.gauge.inc(**self.labels)
        return self

    def __exit__(self, *args):
        self.gauge.dec(**self.labels)


# ============================================================================
# HISTOGRAM
# ============================================================================

class Histogram:
    """
    A histogram for measuring distributions.

    Uses buckets to count observations.
    """

    DEFAULT_BUCKETS = (
        0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5,
        0.75, 1.0, 2.5, 5.0, 7.5, 10.0, float("inf")
    )

    def __init__(
        self,
        name: str,
        description: str = "",
        label_names: Optional[List[str]] = None,
        buckets: Optional[Tuple[float, ...]] = None
    ):
        """Initialize histogram."""
        self.name = name
        self.description = description
        self.label_names = label_names or []
        self.buckets = buckets or self.DEFAULT_BUCKETS
        self.metric_type = MetricType.HISTOGRAM

        self._buckets: Dict[MetricLabels, Dict[float, int]] = defaultdict(
            lambda: {b: 0 for b in self.buckets}
        )
        self._sums: Dict[MetricLabels, float] = defaultdict(float)
        self._counts: Dict[MetricLabels, int] = defaultdict(int)
        self._lock = threading.Lock()

    def observe(self, value: float, **labels) -> None:
        """Record an observation."""
        label_key = MetricLabels(labels)

        with self._lock:
            self._sums[label_key] += value
            self._counts[label_key] += 1

            for bucket in self.buckets:
                if value <= bucket:
                    self._buckets[label_key][bucket] += 1

    def time(self, **labels):
        """Context manager to time operations."""
        return _HistogramTimer(self, labels)

    def get_count(self, **labels) -> int:
        """Get observation count."""
        label_key = MetricLabels(labels)
        return self._counts.get(label_key, 0)

    def get_sum(self, **labels) -> float:
        """Get sum of observations."""
        label_key = MetricLabels(labels)
        return self._sums.get(label_key, 0.0)

    def get_bucket(self, bucket: float, **labels) -> int:
        """Get bucket count."""
        label_key = MetricLabels(labels)
        return self._buckets[label_key].get(bucket, 0)

    def collect(self) -> List[MetricValue]:
        """Collect all values."""
        values = []

        with self._lock:
            for labels in self._counts:
                values.append(MetricValue(
                    value=self._sums[labels],
                    labels=labels
                ))

        return values

    def to_prometheus(self) -> str:
        """Export in Prometheus format."""
        lines = []

        lines.append(f"# HELP {self.name} {self.description}")
        lines.append(f"# TYPE {self.name} histogram")

        with self._lock:
            for labels in self._counts:
                label_str = labels.to_prometheus()
                base_labels = labels.labels.copy()

                # Export buckets
                cumulative = 0
                for bucket in sorted(self.buckets):
                    cumulative += self._buckets[labels].get(bucket, 0)

                    if bucket == float("inf"):
                        bucket_label = "+Inf"
                    else:
                        bucket_label = str(bucket)

                    bucket_labels = {**base_labels, "le": bucket_label}
                    bucket_label_str = MetricLabels(bucket_labels).to_prometheus()

                    lines.append(f"{self.name}_bucket{bucket_label_str} {cumulative}")

                # Export sum and count
                lines.append(f"{self.name}_sum{label_str} {self._sums[labels]}")
                lines.append(f"{self.name}_count{label_str} {self._counts[labels]}")

        return "\n".join(lines)


class _HistogramTimer:
    """Context manager for timing operations."""

    def __init__(self, histogram: Histogram, labels: Dict[str, str]):
        self.histogram = histogram
        self.labels = labels
        self.start_time: float = 0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, *args):
        duration = time.time() - self.start_time
        self.histogram.observe(duration, **self.labels)


# ============================================================================
# SUMMARY
# ============================================================================

class Summary:
    """
    A summary for calculating quantiles.

    Calculates streaming quantiles over observations.
    """

    DEFAULT_QUANTILES = (0.5, 0.9, 0.95, 0.99)
    MAX_SAMPLES = 1000

    def __init__(
        self,
        name: str,
        description: str = "",
        label_names: Optional[List[str]] = None,
        quantiles: Optional[Tuple[float, ...]] = None
    ):
        """Initialize summary."""
        self.name = name
        self.description = description
        self.label_names = label_names or []
        self.quantiles = quantiles or self.DEFAULT_QUANTILES
        self.metric_type = MetricType.SUMMARY

        self._samples: Dict[MetricLabels, List[float]] = defaultdict(list)
        self._sums: Dict[MetricLabels, float] = defaultdict(float)
        self._counts: Dict[MetricLabels, int] = defaultdict(int)
        self._lock = threading.Lock()

    def observe(self, value: float, **labels) -> None:
        """Record an observation."""
        label_key = MetricLabels(labels)

        with self._lock:
            self._sums[label_key] += value
            self._counts[label_key] += 1

            samples = self._samples[label_key]
            samples.append(value)

            # Keep only last N samples
            if len(samples) > self.MAX_SAMPLES:
                self._samples[label_key] = samples[-self.MAX_SAMPLES:]

    def time(self, **labels):
        """Context manager to time operations."""
        return _SummaryTimer(self, labels)

    def get_quantile(self, quantile: float, **labels) -> float:
        """Get a quantile value."""
        label_key = MetricLabels(labels)
        samples = self._samples.get(label_key, [])

        if not samples:
            return 0.0

        sorted_samples = sorted(samples)
        idx = int(quantile * len(sorted_samples))
        return sorted_samples[min(idx, len(sorted_samples) - 1)]

    def get_count(self, **labels) -> int:
        """Get observation count."""
        label_key = MetricLabels(labels)
        return self._counts.get(label_key, 0)

    def get_sum(self, **labels) -> float:
        """Get sum of observations."""
        label_key = MetricLabels(labels)
        return self._sums.get(label_key, 0.0)

    def collect(self) -> List[MetricValue]:
        """Collect all values."""
        values = []

        with self._lock:
            for labels in self._counts:
                values.append(MetricValue(
                    value=self._sums[labels],
                    labels=labels
                ))

        return values

    def to_prometheus(self) -> str:
        """Export in Prometheus format."""
        lines = []

        lines.append(f"# HELP {self.name} {self.description}")
        lines.append(f"# TYPE {self.name} summary")

        with self._lock:
            for labels in self._counts:
                label_str = labels.to_prometheus()
                base_labels = labels.labels.copy()

                # Export quantiles
                samples = self._samples.get(labels, [])
                if samples:
                    sorted_samples = sorted(samples)

                    for q in self.quantiles:
                        idx = int(q * len(sorted_samples))
                        value = sorted_samples[min(idx, len(sorted_samples) - 1)]

                        q_labels = {**base_labels, "quantile": str(q)}
                        q_label_str = MetricLabels(q_labels).to_prometheus()

                        lines.append(f"{self.name}{q_label_str} {value}")

                # Export sum and count
                lines.append(f"{self.name}_sum{label_str} {self._sums[labels]}")
                lines.append(f"{self.name}_count{label_str} {self._counts[labels]}")

        return "\n".join(lines)


class _SummaryTimer:
    """Context manager for timing operations."""

    def __init__(self, summary: Summary, labels: Dict[str, str]):
        self.summary = summary
        self.labels = labels
        self.start_time: float = 0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, *args):
        duration = time.time() - self.start_time
        self.summary.observe(duration, **self.labels)


# ============================================================================
# METRICS REGISTRY
# ============================================================================

class MetricsRegistry:
    """Registry for all metrics."""

    def __init__(self):
        """Initialize registry."""
        self._metrics: Dict[str, Union[Counter, Gauge, Histogram, Summary]] = {}
        self._lock = threading.Lock()

    def register(
        self,
        metric: Union[Counter, Gauge, Histogram, Summary]
    ) -> None:
        """Register a metric."""
        with self._lock:
            if metric.name in self._metrics:
                raise ValueError(f"Metric already registered: {metric.name}")

            self._metrics[metric.name] = metric

    def unregister(self, name: str) -> None:
        """Unregister a metric."""
        with self._lock:
            self._metrics.pop(name, None)

    def get(self, name: str) -> Optional[Union[Counter, Gauge, Histogram, Summary]]:
        """Get a metric by name."""
        return self._metrics.get(name)

    def counter(
        self,
        name: str,
        description: str = "",
        label_names: Optional[List[str]] = None
    ) -> Counter:
        """Create and register a counter."""
        counter = Counter(name, description, label_names)
        self.register(counter)
        return counter

    def gauge(
        self,
        name: str,
        description: str = "",
        label_names: Optional[List[str]] = None
    ) -> Gauge:
        """Create and register a gauge."""
        gauge = Gauge(name, description, label_names)
        self.register(gauge)
        return gauge

    def histogram(
        self,
        name: str,
        description: str = "",
        label_names: Optional[List[str]] = None,
        buckets: Optional[Tuple[float, ...]] = None
    ) -> Histogram:
        """Create and register a histogram."""
        histogram = Histogram(name, description, label_names, buckets)
        self.register(histogram)
        return histogram

    def summary(
        self,
        name: str,
        description: str = "",
        label_names: Optional[List[str]] = None,
        quantiles: Optional[Tuple[float, ...]] = None
    ) -> Summary:
        """Create and register a summary."""
        summary = Summary(name, description, label_names, quantiles)
        self.register(summary)
        return summary

    def collect(self) -> Dict[str, List[MetricValue]]:
        """Collect all metrics."""
        with self._lock:
            return {
                name: metric.collect()
                for name, metric in self._metrics.items()
            }

    def to_prometheus(self) -> str:
        """Export all metrics in Prometheus format."""
        lines = []

        with self._lock:
            for name, metric in sorted(self._metrics.items()):
                lines.append(metric.to_prometheus())
                lines.append("")

        return "\n".join(lines)


# ============================================================================
# METRICS CONFIG
# ============================================================================

@dataclass
class MetricsConfig:
    """Metrics configuration."""
    namespace: str = "bael"
    subsystem: str = ""
    push_gateway_url: Optional[str] = None
    push_interval: float = 10.0
    enable_default_metrics: bool = True


# ============================================================================
# MAIN METRICS ENGINE
# ============================================================================

class MetricsEngine:
    """
    Main metrics engine.

    Features:
    - Prometheus-compatible metrics
    - Counters, Gauges, Histograms, Summaries
    - Labels and dimensions
    - Push gateway support

    "Ba'el measures all dimensions." — Ba'el
    """

    def __init__(self, config: Optional[MetricsConfig] = None):
        """Initialize metrics engine."""
        self.config = config or MetricsConfig()
        self.registry = MetricsRegistry()

        self._running = False
        self._push_task: Optional[asyncio.Task] = None

        # Default metrics
        if self.config.enable_default_metrics:
            self._setup_default_metrics()

        logger.info("MetricsEngine initialized")

    def _setup_default_metrics(self) -> None:
        """Setup default process metrics."""
        self._process_cpu_seconds = self.counter(
            "process_cpu_seconds_total",
            "Total user and system CPU time spent in seconds"
        )

        self._process_start_time = self.gauge(
            "process_start_time_seconds",
            "Start time of the process since unix epoch in seconds"
        )
        self._process_start_time.set(time.time())

    def _full_name(self, name: str) -> str:
        """Get full metric name with namespace."""
        parts = [self.config.namespace]

        if self.config.subsystem:
            parts.append(self.config.subsystem)

        parts.append(name)

        return "_".join(parts)

    # ========================================================================
    # METRIC CREATION
    # ========================================================================

    def counter(
        self,
        name: str,
        description: str = "",
        label_names: Optional[List[str]] = None
    ) -> Counter:
        """Create a counter."""
        full_name = self._full_name(name)
        return self.registry.counter(full_name, description, label_names)

    def gauge(
        self,
        name: str,
        description: str = "",
        label_names: Optional[List[str]] = None
    ) -> Gauge:
        """Create a gauge."""
        full_name = self._full_name(name)
        return self.registry.gauge(full_name, description, label_names)

    def histogram(
        self,
        name: str,
        description: str = "",
        label_names: Optional[List[str]] = None,
        buckets: Optional[Tuple[float, ...]] = None
    ) -> Histogram:
        """Create a histogram."""
        full_name = self._full_name(name)
        return self.registry.histogram(full_name, description, label_names, buckets)

    def summary(
        self,
        name: str,
        description: str = "",
        label_names: Optional[List[str]] = None,
        quantiles: Optional[Tuple[float, ...]] = None
    ) -> Summary:
        """Create a summary."""
        full_name = self._full_name(name)
        return self.registry.summary(full_name, description, label_names, quantiles)

    # ========================================================================
    # EXPORT
    # ========================================================================

    def expose(self) -> str:
        """Expose metrics in Prometheus format."""
        return self.registry.to_prometheus()

    def collect(self) -> Dict[str, List[MetricValue]]:
        """Collect all metrics."""
        return self.registry.collect()

    # ========================================================================
    # PUSH GATEWAY
    # ========================================================================

    async def start_push(self) -> None:
        """Start pushing metrics to gateway."""
        if not self.config.push_gateway_url:
            return

        self._running = True
        self._push_task = asyncio.create_task(self._push_loop())

    async def stop_push(self) -> None:
        """Stop pushing metrics."""
        self._running = False

        if self._push_task:
            self._push_task.cancel()
            try:
                await self._push_task
            except asyncio.CancelledError:
                pass

    async def _push_loop(self) -> None:
        """Push metrics periodically."""
        while self._running:
            try:
                await self._push_metrics()
                await asyncio.sleep(self.config.push_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Push failed: {e}")

    async def _push_metrics(self) -> None:
        """Push metrics to gateway."""
        # Implementation would use aiohttp to push to gateway
        # For now, just log
        logger.debug(f"Would push metrics to {self.config.push_gateway_url}")

    # ========================================================================
    # CONVENIENCE METHODS
    # ========================================================================

    def time(
        self,
        name: str,
        description: str = "",
        label_names: Optional[List[str]] = None,
        **labels
    ):
        """Decorator to time function execution."""
        histogram = self.histogram(name, description, label_names)

        def decorator(func):
            if asyncio.iscoroutinefunction(func):
                async def async_wrapper(*args, **kwargs):
                    with histogram.time(**labels):
                        return await func(*args, **kwargs)
                return async_wrapper
            else:
                def sync_wrapper(*args, **kwargs):
                    with histogram.time(**labels):
                        return func(*args, **kwargs)
                return sync_wrapper

        return decorator

    def count(
        self,
        name: str,
        description: str = "",
        label_names: Optional[List[str]] = None,
        **labels
    ):
        """Decorator to count function calls."""
        counter = self.counter(name, description, label_names)

        def decorator(func):
            if asyncio.iscoroutinefunction(func):
                async def async_wrapper(*args, **kwargs):
                    counter.inc(**labels)
                    return await func(*args, **kwargs)
                return async_wrapper
            else:
                def sync_wrapper(*args, **kwargs):
                    counter.inc(**labels)
                    return func(*args, **kwargs)
                return sync_wrapper

        return decorator

    # ========================================================================
    # STATUS
    # ========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get metrics engine status."""
        return {
            'total_metrics': len(self.registry._metrics),
            'namespace': self.config.namespace,
            'push_enabled': bool(self.config.push_gateway_url),
            'running': self._running
        }


# ============================================================================
# CONVENIENCE INSTANCE
# ============================================================================

metrics_engine = MetricsEngine()
