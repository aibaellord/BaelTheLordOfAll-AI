#!/usr/bin/env python3
"""
BAEL - Telemetry Engine
Telemetry collection for agents.

Features:
- Metrics collection
- Distributed tracing
- Event logging
- Resource monitoring
- Export destinations
"""

import asyncio
import hashlib
import json
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (
    Any, Callable, Dict, Generic, List, Optional, Set, Tuple, Type, TypeVar, Union
)


T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class MetricType(Enum):
    """Metric types."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"
    TIMER = "timer"


class SpanKind(Enum):
    """Span kinds for tracing."""
    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"


class SpanStatus(Enum):
    """Span status."""
    UNSET = "unset"
    OK = "ok"
    ERROR = "error"


class TelemetryLevel(Enum):
    """Telemetry levels."""
    OFF = 0
    MINIMAL = 1
    STANDARD = 2
    DETAILED = 3
    DEBUG = 4


class ExporterType(Enum):
    """Exporter types."""
    CONSOLE = "console"
    MEMORY = "memory"
    FILE = "file"
    HTTP = "http"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class TelemetryConfig:
    """Telemetry configuration."""
    level: TelemetryLevel = TelemetryLevel.STANDARD
    service_name: str = "bael"
    service_version: str = "1.0.0"
    environment: str = "development"
    sample_rate: float = 1.0
    batch_size: int = 100
    flush_interval: float = 10.0


@dataclass
class MetricValue:
    """A metric value."""
    name: str = ""
    value: float = 0.0
    metric_type: MetricType = MetricType.GAUGE
    timestamp: datetime = field(default_factory=datetime.now)
    labels: Dict[str, str] = field(default_factory=dict)
    unit: str = ""


@dataclass
class SpanContext:
    """Span context for distributed tracing."""
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    parent_span_id: str = ""
    sampled: bool = True
    trace_flags: int = 0


@dataclass
class SpanEvent:
    """Event within a span."""
    name: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SpanLink:
    """Link between spans."""
    trace_id: str = ""
    span_id: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Span:
    """A distributed trace span."""
    name: str = ""
    context: SpanContext = field(default_factory=SpanContext)
    kind: SpanKind = SpanKind.INTERNAL
    status: SpanStatus = SpanStatus.UNSET
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[SpanEvent] = field(default_factory=list)
    links: List[SpanLink] = field(default_factory=list)
    
    @property
    def duration_ms(self) -> float:
        if self.end_time:
            delta = self.end_time - self.start_time
            return delta.total_seconds() * 1000
        return 0.0


@dataclass
class ResourceInfo:
    """Resource information."""
    service_name: str = ""
    service_version: str = ""
    environment: str = ""
    host_name: str = ""
    attributes: Dict[str, str] = field(default_factory=dict)


@dataclass
class TelemetryStats:
    """Telemetry statistics."""
    metrics_collected: int = 0
    spans_collected: int = 0
    events_collected: int = 0
    bytes_exported: int = 0
    export_count: int = 0
    errors: int = 0


# =============================================================================
# METRIC CLASSES
# =============================================================================

class Counter:
    """A counter metric (monotonically increasing)."""
    
    def __init__(self, name: str, labels: Optional[Dict[str, str]] = None):
        self._name = name
        self._labels = labels or {}
        self._value = 0.0
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def value(self) -> float:
        return self._value
    
    def inc(self, amount: float = 1.0) -> None:
        """Increment the counter."""
        if amount < 0:
            raise ValueError("Counter can only be incremented")
        self._value += amount
    
    def get_metric(self) -> MetricValue:
        """Get as metric value."""
        return MetricValue(
            name=self._name,
            value=self._value,
            metric_type=MetricType.COUNTER,
            labels=self._labels
        )


class Gauge:
    """A gauge metric (can go up and down)."""
    
    def __init__(self, name: str, labels: Optional[Dict[str, str]] = None):
        self._name = name
        self._labels = labels or {}
        self._value = 0.0
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def value(self) -> float:
        return self._value
    
    def set(self, value: float) -> None:
        """Set the gauge value."""
        self._value = value
    
    def inc(self, amount: float = 1.0) -> None:
        """Increment the gauge."""
        self._value += amount
    
    def dec(self, amount: float = 1.0) -> None:
        """Decrement the gauge."""
        self._value -= amount
    
    def get_metric(self) -> MetricValue:
        """Get as metric value."""
        return MetricValue(
            name=self._name,
            value=self._value,
            metric_type=MetricType.GAUGE,
            labels=self._labels
        )


class Histogram:
    """A histogram metric (distribution of values)."""
    
    def __init__(
        self,
        name: str,
        buckets: Optional[List[float]] = None,
        labels: Optional[Dict[str, str]] = None
    ):
        self._name = name
        self._labels = labels or {}
        self._buckets = buckets or [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        self._bucket_counts: Dict[float, int] = {b: 0 for b in self._buckets}
        self._bucket_counts[float('inf')] = 0
        self._sum = 0.0
        self._count = 0
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def count(self) -> int:
        return self._count
    
    @property
    def sum(self) -> float:
        return self._sum
    
    def observe(self, value: float) -> None:
        """Record an observation."""
        self._sum += value
        self._count += 1
        
        for bucket in sorted(self._bucket_counts.keys()):
            if value <= bucket:
                self._bucket_counts[bucket] += 1
    
    def get_percentile(self, percentile: float) -> float:
        """Get approximate percentile."""
        target = self._count * (percentile / 100.0)
        cumulative = 0
        prev_bucket = 0.0
        
        for bucket in sorted(self._bucket_counts.keys()):
            cumulative += self._bucket_counts[bucket]
            if cumulative >= target:
                return bucket
            prev_bucket = bucket
        
        return prev_bucket
    
    def get_metric(self) -> MetricValue:
        """Get as metric value."""
        return MetricValue(
            name=self._name,
            value=self._sum / self._count if self._count > 0 else 0,
            metric_type=MetricType.HISTOGRAM,
            labels=self._labels
        )


class Timer:
    """A timer metric (for measuring durations)."""
    
    def __init__(self, name: str, labels: Optional[Dict[str, str]] = None):
        self._name = name
        self._labels = labels or {}
        self._histogram = Histogram(name, labels=labels)
        self._start_time: Optional[float] = None
    
    @property
    def name(self) -> str:
        return self._name
    
    def start(self) -> None:
        """Start the timer."""
        self._start_time = time.time()
    
    def stop(self) -> float:
        """Stop the timer and record duration."""
        if self._start_time is None:
            return 0.0
        
        duration = time.time() - self._start_time
        self._histogram.observe(duration)
        self._start_time = None
        return duration
    
    def record(self, duration: float) -> None:
        """Record a duration directly."""
        self._histogram.observe(duration)
    
    def __enter__(self) -> "Timer":
        self.start()
        return self
    
    def __exit__(self, *args) -> None:
        self.stop()
    
    def get_metric(self) -> MetricValue:
        """Get as metric value."""
        return MetricValue(
            name=self._name,
            value=self._histogram.sum / self._histogram.count if self._histogram.count > 0 else 0,
            metric_type=MetricType.TIMER,
            labels=self._labels,
            unit="seconds"
        )


# =============================================================================
# TRACER
# =============================================================================

class Tracer:
    """Distributed tracer."""
    
    def __init__(self, service_name: str, sample_rate: float = 1.0):
        self._service_name = service_name
        self._sample_rate = sample_rate
        self._spans: List[Span] = []
        self._active_spans: Dict[str, Span] = {}
    
    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        parent: Optional[Span] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Span:
        """Start a new span."""
        sampled = random.random() < self._sample_rate
        
        if parent:
            context = SpanContext(
                trace_id=parent.context.trace_id,
                parent_span_id=parent.context.span_id,
                sampled=parent.context.sampled and sampled
            )
        else:
            context = SpanContext(sampled=sampled)
        
        span = Span(
            name=name,
            context=context,
            kind=kind,
            attributes=attributes or {}
        )
        
        self._active_spans[span.context.span_id] = span
        return span
    
    def end_span(self, span: Span, status: SpanStatus = SpanStatus.OK) -> None:
        """End a span."""
        span.end_time = datetime.now()
        span.status = status
        
        if span.context.span_id in self._active_spans:
            del self._active_spans[span.context.span_id]
        
        if span.context.sampled:
            self._spans.append(span)
    
    def add_event(
        self,
        span: Span,
        name: str,
        attributes: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add an event to a span."""
        event = SpanEvent(name=name, attributes=attributes or {})
        span.events.append(event)
    
    def set_attribute(self, span: Span, key: str, value: Any) -> None:
        """Set a span attribute."""
        span.attributes[key] = value
    
    def get_spans(self) -> List[Span]:
        """Get collected spans."""
        return list(self._spans)
    
    def clear(self) -> None:
        """Clear collected spans."""
        self._spans.clear()
    
    def count(self) -> int:
        """Count collected spans."""
        return len(self._spans)


# =============================================================================
# EXPORTER
# =============================================================================

class TelemetryExporter(ABC):
    """Abstract telemetry exporter."""
    
    @abstractmethod
    async def export_metrics(self, metrics: List[MetricValue]) -> bool:
        """Export metrics."""
        pass
    
    @abstractmethod
    async def export_spans(self, spans: List[Span]) -> bool:
        """Export spans."""
        pass


class ConsoleExporter(TelemetryExporter):
    """Console exporter for debugging."""
    
    async def export_metrics(self, metrics: List[MetricValue]) -> bool:
        """Export metrics to console."""
        for metric in metrics:
            labels_str = ",".join(f"{k}={v}" for k, v in metric.labels.items())
            print(f"[METRIC] {metric.name}{{{labels_str}}} = {metric.value}")
        return True
    
    async def export_spans(self, spans: List[Span]) -> bool:
        """Export spans to console."""
        for span in spans:
            print(f"[SPAN] {span.name} trace={span.context.trace_id[:8]} "
                  f"span={span.context.span_id[:8]} duration={span.duration_ms:.2f}ms "
                  f"status={span.status.value}")
        return True


class MemoryExporter(TelemetryExporter):
    """In-memory exporter for testing."""
    
    def __init__(self):
        self._metrics: List[MetricValue] = []
        self._spans: List[Span] = []
    
    async def export_metrics(self, metrics: List[MetricValue]) -> bool:
        """Export metrics to memory."""
        self._metrics.extend(metrics)
        return True
    
    async def export_spans(self, spans: List[Span]) -> bool:
        """Export spans to memory."""
        self._spans.extend(spans)
        return True
    
    @property
    def metrics(self) -> List[MetricValue]:
        return self._metrics
    
    @property
    def spans(self) -> List[Span]:
        return self._spans
    
    def clear(self) -> None:
        """Clear exported data."""
        self._metrics.clear()
        self._spans.clear()


# =============================================================================
# METRIC REGISTRY
# =============================================================================

class MetricRegistry:
    """Registry for metrics."""
    
    def __init__(self):
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}
        self._timers: Dict[str, Timer] = {}
    
    def counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> Counter:
        """Get or create a counter."""
        key = self._key(name, labels)
        if key not in self._counters:
            self._counters[key] = Counter(name, labels)
        return self._counters[key]
    
    def gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> Gauge:
        """Get or create a gauge."""
        key = self._key(name, labels)
        if key not in self._gauges:
            self._gauges[key] = Gauge(name, labels)
        return self._gauges[key]
    
    def histogram(
        self,
        name: str,
        buckets: Optional[List[float]] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> Histogram:
        """Get or create a histogram."""
        key = self._key(name, labels)
        if key not in self._histograms:
            self._histograms[key] = Histogram(name, buckets, labels)
        return self._histograms[key]
    
    def timer(self, name: str, labels: Optional[Dict[str, str]] = None) -> Timer:
        """Get or create a timer."""
        key = self._key(name, labels)
        if key not in self._timers:
            self._timers[key] = Timer(name, labels)
        return self._timers[key]
    
    def _key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """Create a unique key for a metric."""
        if not labels:
            return name
        
        labels_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{labels_str}}}"
    
    def get_all_metrics(self) -> List[MetricValue]:
        """Get all metrics."""
        metrics = []
        
        for counter in self._counters.values():
            metrics.append(counter.get_metric())
        
        for gauge in self._gauges.values():
            metrics.append(gauge.get_metric())
        
        for histogram in self._histograms.values():
            metrics.append(histogram.get_metric())
        
        for timer in self._timers.values():
            metrics.append(timer.get_metric())
        
        return metrics
    
    def clear(self) -> None:
        """Clear all metrics."""
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
        self._timers.clear()


# =============================================================================
# TELEMETRY ENGINE
# =============================================================================

class TelemetryEngine:
    """
    Telemetry Engine for BAEL.
    
    Telemetry collection for agents.
    """
    
    def __init__(self, config: Optional[TelemetryConfig] = None):
        self._config = config or TelemetryConfig()
        self._registry = MetricRegistry()
        self._tracer = Tracer(self._config.service_name, self._config.sample_rate)
        self._exporters: List[TelemetryExporter] = []
        self._resource = ResourceInfo(
            service_name=self._config.service_name,
            service_version=self._config.service_version,
            environment=self._config.environment
        )
        self._stats = TelemetryStats()
        self._running = False
        self._export_task: Optional[asyncio.Task] = None
    
    # ----- Configuration -----
    
    @property
    def config(self) -> TelemetryConfig:
        return self._config
    
    @property
    def resource(self) -> ResourceInfo:
        return self._resource
    
    # ----- Exporters -----
    
    def add_exporter(self, exporter: TelemetryExporter) -> None:
        """Add an exporter."""
        self._exporters.append(exporter)
    
    def remove_exporter(self, exporter: TelemetryExporter) -> None:
        """Remove an exporter."""
        if exporter in self._exporters:
            self._exporters.remove(exporter)
    
    # ----- Metrics -----
    
    def counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> Counter:
        """Get or create a counter."""
        counter = self._registry.counter(name, labels)
        self._stats.metrics_collected += 1
        return counter
    
    def gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> Gauge:
        """Get or create a gauge."""
        gauge = self._registry.gauge(name, labels)
        self._stats.metrics_collected += 1
        return gauge
    
    def histogram(
        self,
        name: str,
        buckets: Optional[List[float]] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> Histogram:
        """Get or create a histogram."""
        histogram = self._registry.histogram(name, buckets, labels)
        self._stats.metrics_collected += 1
        return histogram
    
    def timer(self, name: str, labels: Optional[Dict[str, str]] = None) -> Timer:
        """Get or create a timer."""
        timer = self._registry.timer(name, labels)
        self._stats.metrics_collected += 1
        return timer
    
    def record(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record a gauge value."""
        gauge = self._registry.gauge(name, labels)
        gauge.set(value)
        self._stats.metrics_collected += 1
    
    def increment(self, name: str, amount: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter."""
        counter = self._registry.counter(name, labels)
        counter.inc(amount)
        self._stats.metrics_collected += 1
    
    def get_metrics(self) -> List[MetricValue]:
        """Get all metrics."""
        return self._registry.get_all_metrics()
    
    # ----- Tracing -----
    
    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        parent: Optional[Span] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Span:
        """Start a new span."""
        span = self._tracer.start_span(name, kind, parent, attributes)
        self._stats.spans_collected += 1
        return span
    
    def end_span(self, span: Span, status: SpanStatus = SpanStatus.OK) -> None:
        """End a span."""
        self._tracer.end_span(span, status)
    
    def add_span_event(
        self,
        span: Span,
        name: str,
        attributes: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add an event to a span."""
        self._tracer.add_event(span, name, attributes)
        self._stats.events_collected += 1
    
    def set_span_attribute(self, span: Span, key: str, value: Any) -> None:
        """Set a span attribute."""
        self._tracer.set_attribute(span, key, value)
    
    def get_spans(self) -> List[Span]:
        """Get collected spans."""
        return self._tracer.get_spans()
    
    # ----- Context Manager for Spans -----
    
    class SpanContextManager:
        """Context manager for spans."""
        
        def __init__(self, engine: "TelemetryEngine", span: Span):
            self._engine = engine
            self._span = span
        
        def __enter__(self) -> Span:
            return self._span
        
        def __exit__(self, exc_type, exc_val, exc_tb) -> None:
            status = SpanStatus.ERROR if exc_type else SpanStatus.OK
            self._engine.end_span(self._span, status)
    
    def span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        parent: Optional[Span] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> SpanContextManager:
        """Create a span context manager."""
        span = self.start_span(name, kind, parent, attributes)
        return self.SpanContextManager(self, span)
    
    # ----- Export -----
    
    async def export(self) -> bool:
        """Export all telemetry data."""
        metrics = self._registry.get_all_metrics()
        spans = self._tracer.get_spans()
        
        success = True
        
        for exporter in self._exporters:
            try:
                if metrics:
                    await exporter.export_metrics(metrics)
                if spans:
                    await exporter.export_spans(spans)
                
                self._stats.export_count += 1
            except Exception as e:
                self._stats.errors += 1
                success = False
        
        self._tracer.clear()
        return success
    
    async def start_export_loop(self) -> None:
        """Start the export loop."""
        self._running = True
        
        while self._running:
            await asyncio.sleep(self._config.flush_interval)
            await self.export()
    
    def stop_export_loop(self) -> None:
        """Stop the export loop."""
        self._running = False
    
    # ----- Stats -----
    
    @property
    def stats(self) -> TelemetryStats:
        return self._stats
    
    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "service": self._config.service_name,
            "level": self._config.level.name,
            "exporters": len(self._exporters),
            "metrics_collected": self._stats.metrics_collected,
            "spans_collected": self._stats.spans_collected,
            "events_collected": self._stats.events_collected,
            "export_count": self._stats.export_count,
            "errors": self._stats.errors
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Telemetry Engine."""
    print("=" * 70)
    print("BAEL - TELEMETRY ENGINE DEMO")
    print("Telemetry Collection for Agents")
    print("=" * 70)
    print()
    
    config = TelemetryConfig(
        service_name="bael-demo",
        service_version="1.0.0",
        environment="development"
    )
    
    engine = TelemetryEngine(config)
    
    memory_exporter = MemoryExporter()
    engine.add_exporter(memory_exporter)
    
    # 1. Counter Metric
    print("1. COUNTER METRIC:")
    print("-" * 40)
    
    requests = engine.counter("http_requests_total", {"method": "GET", "path": "/api"})
    requests.inc()
    requests.inc()
    requests.inc(5)
    
    print(f"   Counter: {requests.name} = {requests.value}")
    print()
    
    # 2. Gauge Metric
    print("2. GAUGE METRIC:")
    print("-" * 40)
    
    active_agents = engine.gauge("active_agents", {"type": "search"})
    active_agents.set(5)
    active_agents.inc(2)
    active_agents.dec(1)
    
    print(f"   Gauge: {active_agents.name} = {active_agents.value}")
    print()
    
    # 3. Histogram Metric
    print("3. HISTOGRAM METRIC:")
    print("-" * 40)
    
    latency = engine.histogram("request_latency_seconds", labels={"endpoint": "search"})
    
    for val in [0.1, 0.15, 0.2, 0.25, 0.3, 0.5, 0.8, 1.0, 1.5, 2.0]:
        latency.observe(val)
    
    print(f"   Histogram: {latency.name}")
    print(f"   Count: {latency.count}")
    print(f"   Sum: {latency.sum}")
    print(f"   P50: {latency.get_percentile(50)}")
    print(f"   P90: {latency.get_percentile(90)}")
    print(f"   P99: {latency.get_percentile(99)}")
    print()
    
    # 4. Timer Metric
    print("4. TIMER METRIC:")
    print("-" * 40)
    
    timer = engine.timer("operation_duration", {"operation": "search"})
    
    timer.start()
    await asyncio.sleep(0.1)
    duration = timer.stop()
    print(f"   Timer duration: {duration:.3f}s")
    
    with timer:
        await asyncio.sleep(0.05)
    print(f"   Context manager timer completed")
    print()
    
    # 5. Record and Increment
    print("5. RECORD AND INCREMENT:")
    print("-" * 40)
    
    engine.record("cpu_usage", 45.5, {"host": "server-1"})
    engine.increment("events_processed", 10, {"type": "message"})
    
    print(f"   Recorded cpu_usage: 45.5")
    print(f"   Incremented events_processed by 10")
    print()
    
    # 6. Start a Span
    print("6. START A SPAN:")
    print("-" * 40)
    
    span = engine.start_span("handle_request", SpanKind.SERVER, attributes={"http.method": "GET"})
    engine.set_span_attribute(span, "http.url", "/api/search")
    
    await asyncio.sleep(0.05)
    
    engine.add_span_event(span, "query_started", {"query": "test"})
    await asyncio.sleep(0.03)
    engine.add_span_event(span, "query_completed", {"results": 10})
    
    engine.end_span(span, SpanStatus.OK)
    
    print(f"   Span: {span.name}")
    print(f"   Trace ID: {span.context.trace_id[:16]}...")
    print(f"   Span ID: {span.context.span_id}")
    print(f"   Duration: {span.duration_ms:.2f}ms")
    print(f"   Events: {len(span.events)}")
    print()
    
    # 7. Nested Spans
    print("7. NESTED SPANS:")
    print("-" * 40)
    
    parent = engine.start_span("parent_operation", SpanKind.INTERNAL)
    
    child1 = engine.start_span("child_1", parent=parent)
    await asyncio.sleep(0.02)
    engine.end_span(child1)
    
    child2 = engine.start_span("child_2", parent=parent)
    await asyncio.sleep(0.03)
    engine.end_span(child2)
    
    engine.end_span(parent)
    
    print(f"   Parent: {parent.name} ({parent.duration_ms:.2f}ms)")
    print(f"   Child 1: {child1.name} ({child1.duration_ms:.2f}ms)")
    print(f"   Child 2: {child2.name} ({child2.duration_ms:.2f}ms)")
    print()
    
    # 8. Span Context Manager
    print("8. SPAN CONTEXT MANAGER:")
    print("-" * 40)
    
    with engine.span("context_managed_operation", SpanKind.CLIENT) as span:
        engine.set_span_attribute(span, "db.system", "postgres")
        await asyncio.sleep(0.04)
        engine.add_span_event(span, "query_executed")
    
    print(f"   Span: {span.name}")
    print(f"   Status: {span.status.value}")
    print(f"   Duration: {span.duration_ms:.2f}ms")
    print()
    
    # 9. Export Telemetry
    print("9. EXPORT TELEMETRY:")
    print("-" * 40)
    
    await engine.export()
    
    print(f"   Exported metrics: {len(memory_exporter.metrics)}")
    print(f"   Exported spans: {len(memory_exporter.spans)}")
    print()
    
    # 10. Get All Metrics
    print("10. GET ALL METRICS:")
    print("-" * 40)
    
    all_metrics = engine.get_metrics()
    for metric in all_metrics[:5]:
        labels = ",".join(f"{k}={v}" for k, v in metric.labels.items())
        print(f"   {metric.name}{{{labels}}} = {metric.value:.2f} ({metric.metric_type.value})")
    print()
    
    # 11. Resource Info
    print("11. RESOURCE INFO:")
    print("-" * 40)
    
    resource = engine.resource
    print(f"   Service: {resource.service_name}")
    print(f"   Version: {resource.service_version}")
    print(f"   Environment: {resource.environment}")
    print()
    
    # 12. Statistics
    print("12. STATISTICS:")
    print("-" * 40)
    
    stats = engine.stats
    print(f"   Metrics collected: {stats.metrics_collected}")
    print(f"   Spans collected: {stats.spans_collected}")
    print(f"   Events collected: {stats.events_collected}")
    print(f"   Export count: {stats.export_count}")
    print()
    
    # 13. Engine Summary
    print("13. ENGINE SUMMARY:")
    print("-" * 40)
    
    summary = engine.summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()
    
    print("=" * 70)
    print("DEMO COMPLETE - Telemetry Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
