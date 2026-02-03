#!/usr/bin/env python3
"""
BAEL - Distributed Tracing System
Comprehensive distributed tracing and request correlation.

Features:
- Trace context propagation
- Span management
- Trace sampling
- Context injection/extraction
- Trace exporters
- Span annotations
- Baggage handling
- Parent-child relationships
- Performance metrics
- Trace visualization
"""

import asyncio
import hashlib
import logging
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import (Any, Awaitable, Callable, Dict, Generator, Generic, List,
                    Optional, Set, Tuple, TypeVar, Union)

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class SpanKind(Enum):
    """Span kinds."""
    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"


class SpanStatus(Enum):
    """Span status codes."""
    UNSET = "unset"
    OK = "ok"
    ERROR = "error"


class SamplingDecision(Enum):
    """Sampling decisions."""
    DROP = "drop"
    RECORD_ONLY = "record_only"
    RECORD_AND_SAMPLE = "record_and_sample"


class PropagationFormat(Enum):
    """Propagation formats."""
    W3C_TRACEPARENT = "w3c"
    B3_SINGLE = "b3_single"
    B3_MULTI = "b3_multi"
    JAEGER = "jaeger"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class TraceContext:
    """Trace context for propagation."""
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    parent_span_id: Optional[str] = None
    trace_flags: int = 1  # 0 = not sampled, 1 = sampled
    trace_state: Dict[str, str] = field(default_factory=dict)
    baggage: Dict[str, str] = field(default_factory=dict)

    @property
    def is_sampled(self) -> bool:
        return self.trace_flags & 1 == 1


@dataclass
class SpanEvent:
    """Event within a span."""
    name: str
    timestamp: float = field(default_factory=time.time)
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SpanLink:
    """Link to another span."""
    trace_id: str
    span_id: str
    trace_state: Dict[str, str] = field(default_factory=dict)
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Span:
    """Represents a span in a trace."""
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    trace_id: str = ""
    parent_span_id: Optional[str] = None
    name: str = ""
    kind: SpanKind = SpanKind.INTERNAL
    status: SpanStatus = SpanStatus.UNSET
    status_message: str = ""
    start_time: float = field(default_factory=time.time)
    end_time: float = 0.0
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[SpanEvent] = field(default_factory=list)
    links: List[SpanLink] = field(default_factory=list)
    resource: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        if self.end_time == 0:
            return (time.time() - self.start_time) * 1000
        return (self.end_time - self.start_time) * 1000

    @property
    def is_finished(self) -> bool:
        return self.end_time > 0

    def add_event(self, name: str, attributes: Dict[str, Any] = None) -> None:
        """Add an event."""
        self.events.append(SpanEvent(
            name=name,
            attributes=attributes or {}
        ))

    def add_link(
        self,
        trace_id: str,
        span_id: str,
        attributes: Dict[str, Any] = None
    ) -> None:
        """Add a link."""
        self.links.append(SpanLink(
            trace_id=trace_id,
            span_id=span_id,
            attributes=attributes or {}
        ))

    def set_attribute(self, key: str, value: Any) -> None:
        """Set an attribute."""
        self.attributes[key] = value

    def set_status(self, status: SpanStatus, message: str = "") -> None:
        """Set span status."""
        self.status = status
        self.status_message = message

    def finish(self, end_time: float = None) -> None:
        """Finish the span."""
        self.end_time = end_time or time.time()


@dataclass
class Trace:
    """Complete trace with all spans."""
    trace_id: str
    spans: List[Span] = field(default_factory=list)
    root_span_id: Optional[str] = None

    @property
    def duration_ms(self) -> float:
        if not self.spans:
            return 0.0

        start = min(s.start_time for s in self.spans)
        end = max(s.end_time or time.time() for s in self.spans)

        return (end - start) * 1000

    @property
    def span_count(self) -> int:
        return len(self.spans)

    def get_span(self, span_id: str) -> Optional[Span]:
        """Get span by ID."""
        for span in self.spans:
            if span.span_id == span_id:
                return span
        return None


# =============================================================================
# SAMPLERS
# =============================================================================

class Sampler(ABC):
    """Abstract sampler."""

    @abstractmethod
    def should_sample(
        self,
        trace_id: str,
        name: str,
        parent_context: Optional[TraceContext] = None
    ) -> SamplingDecision:
        """Determine sampling decision."""
        pass


class AlwaysOnSampler(Sampler):
    """Always sample."""

    def should_sample(
        self,
        trace_id: str,
        name: str,
        parent_context: Optional[TraceContext] = None
    ) -> SamplingDecision:
        return SamplingDecision.RECORD_AND_SAMPLE


class AlwaysOffSampler(Sampler):
    """Never sample."""

    def should_sample(
        self,
        trace_id: str,
        name: str,
        parent_context: Optional[TraceContext] = None
    ) -> SamplingDecision:
        return SamplingDecision.DROP


class ProbabilitySampler(Sampler):
    """Sample with probability."""

    def __init__(self, probability: float = 0.1):
        self.probability = max(0.0, min(1.0, probability))

    def should_sample(
        self,
        trace_id: str,
        name: str,
        parent_context: Optional[TraceContext] = None
    ) -> SamplingDecision:
        # Use trace_id for deterministic sampling
        hash_val = int(hashlib.md5(trace_id.encode()).hexdigest(), 16)
        threshold = int(self.probability * (2 ** 128))

        if hash_val < threshold:
            return SamplingDecision.RECORD_AND_SAMPLE

        return SamplingDecision.DROP


class RateLimitingSampler(Sampler):
    """Sample with rate limiting."""

    def __init__(self, max_traces_per_second: int = 10):
        self.max_traces = max_traces_per_second
        self._count = 0
        self._window_start = time.time()

    def should_sample(
        self,
        trace_id: str,
        name: str,
        parent_context: Optional[TraceContext] = None
    ) -> SamplingDecision:
        now = time.time()

        if now - self._window_start >= 1.0:
            self._count = 0
            self._window_start = now

        if self._count >= self.max_traces:
            return SamplingDecision.DROP

        self._count += 1
        return SamplingDecision.RECORD_AND_SAMPLE


class ParentBasedSampler(Sampler):
    """Sample based on parent."""

    def __init__(
        self,
        root_sampler: Sampler = None,
        remote_parent_sampled: Sampler = None,
        remote_parent_not_sampled: Sampler = None
    ):
        self.root_sampler = root_sampler or AlwaysOnSampler()
        self.remote_parent_sampled = remote_parent_sampled or AlwaysOnSampler()
        self.remote_parent_not_sampled = remote_parent_not_sampled or AlwaysOffSampler()

    def should_sample(
        self,
        trace_id: str,
        name: str,
        parent_context: Optional[TraceContext] = None
    ) -> SamplingDecision:
        if not parent_context:
            return self.root_sampler.should_sample(trace_id, name)

        if parent_context.is_sampled:
            return self.remote_parent_sampled.should_sample(trace_id, name, parent_context)

        return self.remote_parent_not_sampled.should_sample(trace_id, name, parent_context)


# =============================================================================
# PROPAGATORS
# =============================================================================

class Propagator(ABC):
    """Abstract propagator."""

    @abstractmethod
    def inject(self, context: TraceContext, carrier: Dict[str, str]) -> None:
        """Inject context into carrier."""
        pass

    @abstractmethod
    def extract(self, carrier: Dict[str, str]) -> Optional[TraceContext]:
        """Extract context from carrier."""
        pass


class W3CTraceContextPropagator(Propagator):
    """W3C Trace Context propagator."""

    TRACEPARENT = "traceparent"
    TRACESTATE = "tracestate"

    def inject(self, context: TraceContext, carrier: Dict[str, str]) -> None:
        """Inject W3C traceparent."""
        flags = "01" if context.is_sampled else "00"

        traceparent = f"00-{context.trace_id}-{context.span_id}-{flags}"
        carrier[self.TRACEPARENT] = traceparent

        if context.trace_state:
            pairs = [f"{k}={v}" for k, v in context.trace_state.items()]
            carrier[self.TRACESTATE] = ",".join(pairs)

    def extract(self, carrier: Dict[str, str]) -> Optional[TraceContext]:
        """Extract W3C traceparent."""
        traceparent = carrier.get(self.TRACEPARENT)

        if not traceparent:
            return None

        parts = traceparent.split("-")

        if len(parts) != 4:
            return None

        version, trace_id, span_id, flags = parts

        context = TraceContext(
            trace_id=trace_id,
            span_id=span_id,
            trace_flags=int(flags, 16)
        )

        # Parse tracestate
        tracestate = carrier.get(self.TRACESTATE, "")

        if tracestate:
            for pair in tracestate.split(","):
                if "=" in pair:
                    key, value = pair.split("=", 1)
                    context.trace_state[key.strip()] = value.strip()

        return context


class B3SinglePropagator(Propagator):
    """B3 single header propagator."""

    B3 = "b3"

    def inject(self, context: TraceContext, carrier: Dict[str, str]) -> None:
        """Inject B3 single header."""
        sampled = "1" if context.is_sampled else "0"

        if context.parent_span_id:
            b3 = f"{context.trace_id}-{context.span_id}-{sampled}-{context.parent_span_id}"
        else:
            b3 = f"{context.trace_id}-{context.span_id}-{sampled}"

        carrier[self.B3] = b3

    def extract(self, carrier: Dict[str, str]) -> Optional[TraceContext]:
        """Extract B3 single header."""
        b3 = carrier.get(self.B3)

        if not b3:
            return None

        parts = b3.split("-")

        if len(parts) < 2:
            return None

        trace_id = parts[0]
        span_id = parts[1]
        sampled = parts[2] if len(parts) > 2 else "1"
        parent_span_id = parts[3] if len(parts) > 3 else None

        return TraceContext(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            trace_flags=1 if sampled == "1" else 0
        )


# =============================================================================
# EXPORTERS
# =============================================================================

class SpanExporter(ABC):
    """Abstract span exporter."""

    @abstractmethod
    async def export(self, spans: List[Span]) -> bool:
        """Export spans."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown exporter."""
        pass


class ConsoleExporter(SpanExporter):
    """Console exporter for debugging."""

    async def export(self, spans: List[Span]) -> bool:
        """Export to console."""
        for span in spans:
            print(f"[TRACE] {span.trace_id[:8]}... {span.name} "
                  f"({span.duration_ms:.2f}ms) [{span.status.value}]")

        return True

    async def shutdown(self) -> None:
        pass


class InMemoryExporter(SpanExporter):
    """In-memory exporter for testing."""

    def __init__(self, max_spans: int = 10000):
        self._spans: List[Span] = []
        self._max_spans = max_spans

    async def export(self, spans: List[Span]) -> bool:
        """Store spans in memory."""
        self._spans.extend(spans)

        if len(self._spans) > self._max_spans:
            self._spans = self._spans[-self._max_spans:]

        return True

    async def shutdown(self) -> None:
        self._spans.clear()

    def get_spans(self) -> List[Span]:
        return self._spans.copy()

    def get_finished_spans(self) -> List[Span]:
        return [s for s in self._spans if s.is_finished]


class BatchExporter(SpanExporter):
    """Batching exporter wrapper."""

    def __init__(
        self,
        exporter: SpanExporter,
        max_batch_size: int = 512,
        batch_timeout: float = 5.0
    ):
        self._exporter = exporter
        self._max_batch_size = max_batch_size
        self._batch_timeout = batch_timeout
        self._batch: List[Span] = []
        self._last_flush = time.time()

    async def export(self, spans: List[Span]) -> bool:
        """Add to batch and flush if needed."""
        self._batch.extend(spans)

        should_flush = (
            len(self._batch) >= self._max_batch_size or
            time.time() - self._last_flush >= self._batch_timeout
        )

        if should_flush:
            return await self._flush()

        return True

    async def _flush(self) -> bool:
        """Flush batch."""
        if not self._batch:
            return True

        batch = self._batch
        self._batch = []
        self._last_flush = time.time()

        return await self._exporter.export(batch)

    async def shutdown(self) -> None:
        await self._flush()
        await self._exporter.shutdown()


# =============================================================================
# SPAN PROCESSOR
# =============================================================================

class SpanProcessor(ABC):
    """Abstract span processor."""

    @abstractmethod
    def on_start(self, span: Span, parent_context: Optional[TraceContext]) -> None:
        """Called when span starts."""
        pass

    @abstractmethod
    def on_end(self, span: Span) -> None:
        """Called when span ends."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown processor."""
        pass


class SimpleSpanProcessor(SpanProcessor):
    """Simple synchronous span processor."""

    def __init__(self, exporter: SpanExporter):
        self._exporter = exporter

    def on_start(self, span: Span, parent_context: Optional[TraceContext]) -> None:
        pass

    def on_end(self, span: Span) -> None:
        asyncio.create_task(self._exporter.export([span]))

    async def shutdown(self) -> None:
        await self._exporter.shutdown()


class BatchSpanProcessor(SpanProcessor):
    """Batch span processor."""

    def __init__(
        self,
        exporter: SpanExporter,
        max_queue_size: int = 2048,
        batch_timeout: float = 5.0
    ):
        self._exporter = exporter
        self._max_queue_size = max_queue_size
        self._batch_timeout = batch_timeout
        self._queue: List[Span] = []
        self._task: Optional[asyncio.Task] = None

    def on_start(self, span: Span, parent_context: Optional[TraceContext]) -> None:
        pass

    def on_end(self, span: Span) -> None:
        if len(self._queue) < self._max_queue_size:
            self._queue.append(span)

    async def _export_loop(self) -> None:
        while True:
            await asyncio.sleep(self._batch_timeout)
            await self._flush()

    async def _flush(self) -> None:
        if not self._queue:
            return

        batch = self._queue
        self._queue = []

        await self._exporter.export(batch)

    async def shutdown(self) -> None:
        if self._task:
            self._task.cancel()

        await self._flush()
        await self._exporter.shutdown()


# =============================================================================
# TRACER
# =============================================================================

class Tracer:
    """Tracer for creating spans."""

    def __init__(
        self,
        name: str,
        provider: 'TracerProvider'
    ):
        self.name = name
        self._provider = provider

    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        parent: Optional[TraceContext] = None,
        attributes: Dict[str, Any] = None,
        links: List[SpanLink] = None
    ) -> Span:
        """Start a new span."""
        return self._provider.start_span(
            name=name,
            kind=kind,
            parent=parent,
            attributes=attributes,
            links=links
        )

    @contextmanager
    def span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Dict[str, Any] = None
    ) -> Generator[Span, None, None]:
        """Context manager for span."""
        span = self.start_span(name, kind, attributes=attributes)

        try:
            yield span
        except Exception as e:
            span.set_status(SpanStatus.ERROR, str(e))
            raise
        finally:
            span.finish()
            self._provider.end_span(span)

    @asynccontextmanager
    async def async_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Dict[str, Any] = None
    ):
        """Async context manager for span."""
        span = self.start_span(name, kind, attributes=attributes)

        try:
            yield span
        except Exception as e:
            span.set_status(SpanStatus.ERROR, str(e))
            raise
        finally:
            span.finish()
            self._provider.end_span(span)


# =============================================================================
# TRACER PROVIDER
# =============================================================================

class TracerProvider:
    """Provides tracers."""

    def __init__(
        self,
        sampler: Sampler = None,
        resource: Dict[str, Any] = None
    ):
        self.sampler = sampler or AlwaysOnSampler()
        self.resource = resource or {}

        self._processors: List[SpanProcessor] = []
        self._active_context: Optional[TraceContext] = None
        self._tracers: Dict[str, Tracer] = {}

    def add_span_processor(self, processor: SpanProcessor) -> None:
        """Add span processor."""
        self._processors.append(processor)

    def get_tracer(self, name: str) -> Tracer:
        """Get or create tracer."""
        if name not in self._tracers:
            self._tracers[name] = Tracer(name, self)

        return self._tracers[name]

    def get_current_context(self) -> Optional[TraceContext]:
        """Get current trace context."""
        return self._active_context

    def set_current_context(self, context: TraceContext) -> None:
        """Set current trace context."""
        self._active_context = context

    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        parent: Optional[TraceContext] = None,
        attributes: Dict[str, Any] = None,
        links: List[SpanLink] = None
    ) -> Span:
        """Start a new span."""
        parent_ctx = parent or self._active_context

        if parent_ctx:
            trace_id = parent_ctx.trace_id
            parent_span_id = parent_ctx.span_id
        else:
            trace_id = uuid.uuid4().hex
            parent_span_id = None

        # Sampling decision
        decision = self.sampler.should_sample(trace_id, name, parent_ctx)

        span = Span(
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            name=name,
            kind=kind,
            attributes=attributes or {},
            links=links or [],
            resource=self.resource.copy()
        )

        # Update context
        context = TraceContext(
            trace_id=trace_id,
            span_id=span.span_id,
            parent_span_id=parent_span_id,
            trace_flags=1 if decision == SamplingDecision.RECORD_AND_SAMPLE else 0
        )

        if parent_ctx:
            context.baggage = parent_ctx.baggage.copy()
            context.trace_state = parent_ctx.trace_state.copy()

        self._active_context = context

        # Notify processors
        for processor in self._processors:
            processor.on_start(span, parent_ctx)

        return span

    def end_span(self, span: Span) -> None:
        """End a span."""
        for processor in self._processors:
            processor.on_end(span)

    async def shutdown(self) -> None:
        """Shutdown provider."""
        for processor in self._processors:
            await processor.shutdown()


# =============================================================================
# DISTRIBUTED TRACER
# =============================================================================

class DistributedTracer:
    """
    Comprehensive Distributed Tracing System for BAEL.
    """

    def __init__(
        self,
        service_name: str,
        sampler: Sampler = None,
        propagator: Propagator = None
    ):
        self.service_name = service_name

        self.provider = TracerProvider(
            sampler=sampler or AlwaysOnSampler(),
            resource={
                "service.name": service_name,
                "service.version": "1.0.0"
            }
        )

        self.propagator = propagator or W3CTraceContextPropagator()

        self._traces: Dict[str, Trace] = {}
        self._exporter = InMemoryExporter()

        # Add processor
        self.provider.add_span_processor(
            SimpleSpanProcessor(self._exporter)
        )

    # -------------------------------------------------------------------------
    # TRACER ACCESS
    # -------------------------------------------------------------------------

    def get_tracer(self, name: str = None) -> Tracer:
        """Get a tracer."""
        return self.provider.get_tracer(name or self.service_name)

    # -------------------------------------------------------------------------
    # SPAN OPERATIONS
    # -------------------------------------------------------------------------

    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        parent: Optional[TraceContext] = None,
        attributes: Dict[str, Any] = None
    ) -> Span:
        """Start a new span."""
        return self.provider.start_span(name, kind, parent, attributes)

    def end_span(self, span: Span) -> None:
        """End a span."""
        span.finish()
        self.provider.end_span(span)

        # Store in trace
        if span.trace_id not in self._traces:
            self._traces[span.trace_id] = Trace(trace_id=span.trace_id)

        self._traces[span.trace_id].spans.append(span)

        if not span.parent_span_id:
            self._traces[span.trace_id].root_span_id = span.span_id

    @contextmanager
    def span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Dict[str, Any] = None
    ) -> Generator[Span, None, None]:
        """Context manager for span."""
        span = self.start_span(name, kind, attributes=attributes)

        try:
            yield span
        except Exception as e:
            span.set_status(SpanStatus.ERROR, str(e))
            raise
        finally:
            self.end_span(span)

    @asynccontextmanager
    async def async_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Dict[str, Any] = None
    ):
        """Async context manager for span."""
        span = self.start_span(name, kind, attributes=attributes)

        try:
            yield span
        except Exception as e:
            span.set_status(SpanStatus.ERROR, str(e))
            raise
        finally:
            self.end_span(span)

    # -------------------------------------------------------------------------
    # CONTEXT PROPAGATION
    # -------------------------------------------------------------------------

    def inject(self, carrier: Dict[str, str]) -> None:
        """Inject current context into carrier."""
        context = self.provider.get_current_context()

        if context:
            self.propagator.inject(context, carrier)

    def extract(self, carrier: Dict[str, str]) -> Optional[TraceContext]:
        """Extract context from carrier."""
        return self.propagator.extract(carrier)

    def with_context(self, context: TraceContext) -> 'DistributedTracer':
        """Set context and return self."""
        self.provider.set_current_context(context)
        return self

    # -------------------------------------------------------------------------
    # BAGGAGE
    # -------------------------------------------------------------------------

    def set_baggage(self, key: str, value: str) -> None:
        """Set baggage item."""
        context = self.provider.get_current_context()

        if context:
            context.baggage[key] = value

    def get_baggage(self, key: str) -> Optional[str]:
        """Get baggage item."""
        context = self.provider.get_current_context()

        if context:
            return context.baggage.get(key)

        return None

    # -------------------------------------------------------------------------
    # TRACE ACCESS
    # -------------------------------------------------------------------------

    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """Get trace by ID."""
        return self._traces.get(trace_id)

    def get_current_trace_id(self) -> Optional[str]:
        """Get current trace ID."""
        context = self.provider.get_current_context()
        return context.trace_id if context else None

    def get_current_span_id(self) -> Optional[str]:
        """Get current span ID."""
        context = self.provider.get_current_context()
        return context.span_id if context else None

    # -------------------------------------------------------------------------
    # TRACE ANALYSIS
    # -------------------------------------------------------------------------

    def get_trace_tree(self, trace_id: str) -> Dict[str, Any]:
        """Get trace as tree structure."""
        trace = self._traces.get(trace_id)

        if not trace:
            return {}

        def build_tree(span_id: str) -> Dict[str, Any]:
            span = trace.get_span(span_id)

            if not span:
                return {}

            children = [
                s for s in trace.spans
                if s.parent_span_id == span_id
            ]

            return {
                "span_id": span.span_id,
                "name": span.name,
                "kind": span.kind.value,
                "status": span.status.value,
                "duration_ms": span.duration_ms,
                "attributes": span.attributes,
                "events": [
                    {"name": e.name, "attributes": e.attributes}
                    for e in span.events
                ],
                "children": [
                    build_tree(c.span_id)
                    for c in children
                ]
            }

        if trace.root_span_id:
            return build_tree(trace.root_span_id)

        return {}

    def get_critical_path(self, trace_id: str) -> List[Span]:
        """Get critical path of trace."""
        trace = self._traces.get(trace_id)

        if not trace or not trace.spans:
            return []

        # Simple critical path: longest chain
        def get_chain(span: Span) -> List[Span]:
            children = [
                s for s in trace.spans
                if s.parent_span_id == span.span_id
            ]

            if not children:
                return [span]

            longest = max(
                (get_chain(c) for c in children),
                key=lambda chain: sum(s.duration_ms for s in chain)
            )

            return [span] + longest

        root = next(
            (s for s in trace.spans if not s.parent_span_id),
            trace.spans[0]
        )

        return get_chain(root)

    # -------------------------------------------------------------------------
    # METRICS
    # -------------------------------------------------------------------------

    def get_trace_metrics(self, trace_id: str) -> Dict[str, Any]:
        """Get metrics for a trace."""
        trace = self._traces.get(trace_id)

        if not trace:
            return {}

        total_duration = trace.duration_ms
        spans_by_kind = defaultdict(int)
        spans_by_status = defaultdict(int)

        for span in trace.spans:
            spans_by_kind[span.kind.value] += 1
            spans_by_status[span.status.value] += 1

        return {
            "trace_id": trace_id,
            "span_count": trace.span_count,
            "total_duration_ms": total_duration,
            "spans_by_kind": dict(spans_by_kind),
            "spans_by_status": dict(spans_by_status)
        }

    def get_service_metrics(self) -> Dict[str, Any]:
        """Get aggregated metrics."""
        total_traces = len(self._traces)
        total_spans = sum(t.span_count for t in self._traces.values())

        avg_duration = 0.0
        if total_traces > 0:
            avg_duration = sum(
                t.duration_ms for t in self._traces.values()
            ) / total_traces

        return {
            "service": self.service_name,
            "total_traces": total_traces,
            "total_spans": total_spans,
            "avg_trace_duration_ms": avg_duration
        }

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def get_all_spans(self) -> List[Span]:
        """Get all recorded spans."""
        return self._exporter.get_finished_spans()

    async def shutdown(self) -> None:
        """Shutdown tracer."""
        await self.provider.shutdown()


# =============================================================================
# DECORATORS
# =============================================================================

def traced(
    tracer: DistributedTracer,
    name: str = None,
    kind: SpanKind = SpanKind.INTERNAL
):
    """Decorator for tracing functions."""
    def decorator(func: Callable):
        span_name = name or func.__name__

        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                async with tracer.async_span(span_name, kind):
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                with tracer.span(span_name, kind):
                    return func(*args, **kwargs)
            return sync_wrapper

    return decorator


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Distributed Tracing System."""
    print("=" * 70)
    print("BAEL - DISTRIBUTED TRACING SYSTEM DEMO")
    print("Comprehensive Distributed Tracing")
    print("=" * 70)
    print()

    tracer = DistributedTracer(
        "bael-demo-service",
        sampler=AlwaysOnSampler()
    )

    # 1. Basic Span
    print("1. BASIC SPAN:")
    print("-" * 40)

    with tracer.span("process-request", SpanKind.SERVER) as span:
        span.set_attribute("http.method", "GET")
        span.set_attribute("http.url", "/api/users")
        await asyncio.sleep(0.05)  # Simulate work
        span.set_status(SpanStatus.OK)
        print(f"   Span: {span.name}")
        print(f"   Trace ID: {span.trace_id[:16]}...")
    print()

    # 2. Nested Spans
    print("2. NESTED SPANS:")
    print("-" * 40)

    with tracer.span("handle-order", SpanKind.SERVER) as parent:
        parent.set_attribute("order.id", "ORD-123")

        with tracer.span("validate-order", SpanKind.INTERNAL) as child1:
            await asyncio.sleep(0.01)
            print(f"   {child1.name} (parent: {child1.parent_span_id[:8]}...)")

        with tracer.span("process-payment", SpanKind.CLIENT) as child2:
            await asyncio.sleep(0.02)
            child2.add_event("payment_started")
            child2.add_event("payment_completed", {"amount": 99.99})
            print(f"   {child2.name} (parent: {child2.parent_span_id[:8]}...)")

        with tracer.span("ship-order", SpanKind.PRODUCER) as child3:
            await asyncio.sleep(0.01)
            print(f"   {child3.name} (parent: {child3.parent_span_id[:8]}...)")
    print()

    # 3. Context Propagation
    print("3. CONTEXT PROPAGATION:")
    print("-" * 40)

    with tracer.span("api-call", SpanKind.CLIENT) as span:
        carrier = {}
        tracer.inject(carrier)

        print(f"   Injected headers:")
        for key, value in carrier.items():
            print(f"      {key}: {value}")
    print()

    # 4. Extract Context
    print("4. EXTRACT CONTEXT:")
    print("-" * 40)

    incoming_headers = {
        "traceparent": "00-abcd1234abcd1234abcd1234abcd1234-1234567890abcdef-01"
    }

    context = tracer.extract(incoming_headers)

    if context:
        print(f"   Trace ID: {context.trace_id}")
        print(f"   Span ID: {context.span_id}")
        print(f"   Sampled: {context.is_sampled}")
    print()

    # 5. Baggage
    print("5. BAGGAGE:")
    print("-" * 40)

    with tracer.span("with-baggage"):
        tracer.set_baggage("user.id", "user-456")
        tracer.set_baggage("tenant.id", "tenant-789")

        print(f"   user.id: {tracer.get_baggage('user.id')}")
        print(f"   tenant.id: {tracer.get_baggage('tenant.id')}")
    print()

    # 6. Span Events
    print("6. SPAN EVENTS:")
    print("-" * 40)

    with tracer.span("with-events") as span:
        span.add_event("cache_miss", {"key": "user:123"})
        await asyncio.sleep(0.01)
        span.add_event("db_query", {"query": "SELECT * FROM users", "rows": 42})
        await asyncio.sleep(0.01)
        span.add_event("cache_set", {"key": "user:123", "ttl": 300})

        for event in span.events:
            print(f"   Event: {event.name} - {event.attributes}")
    print()

    # 7. Error Handling
    print("7. ERROR HANDLING:")
    print("-" * 40)

    try:
        with tracer.span("with-error") as span:
            span.set_attribute("operation", "risky")
            raise ValueError("Something went wrong")
    except ValueError as e:
        print(f"   Caught error: {e}")
        print(f"   Span status: ERROR")
    print()

    # 8. Async Span
    print("8. ASYNC SPAN:")
    print("-" * 40)

    async with tracer.async_span("async-operation", SpanKind.INTERNAL) as span:
        span.set_attribute("async", True)
        await asyncio.sleep(0.02)
        span.add_event("async_complete")
        print(f"   Async span: {span.name}")
        print(f"   Duration: {span.duration_ms:.2f}ms")
    print()

    # 9. Get Trace
    print("9. GET TRACE:")
    print("-" * 40)

    trace_id = tracer.get_current_trace_id()

    if trace_id:
        trace = tracer.get_trace(trace_id)
        if trace:
            print(f"   Trace ID: {trace.trace_id[:16]}...")
            print(f"   Span count: {trace.span_count}")
            print(f"   Duration: {trace.duration_ms:.2f}ms")
    print()

    # 10. Trace Tree
    print("10. TRACE TREE:")
    print("-" * 40)

    # Create a trace with hierarchy
    with tracer.span("root-operation") as root:
        with tracer.span("child-1"):
            with tracer.span("grandchild-1"):
                pass
        with tracer.span("child-2"):
            pass

    tree = tracer.get_trace_tree(root.trace_id)

    def print_tree(node, indent=0):
        print("   " + "  " * indent + f"- {node.get('name', 'unknown')}")
        for child in node.get('children', []):
            print_tree(child, indent + 1)

    if tree:
        print_tree(tree)
    print()

    # 11. Critical Path
    print("11. CRITICAL PATH:")
    print("-" * 40)

    critical_path = tracer.get_critical_path(root.trace_id)

    for i, span in enumerate(critical_path):
        print(f"   {i+1}. {span.name} ({span.duration_ms:.2f}ms)")
    print()

    # 12. Service Metrics
    print("12. SERVICE METRICS:")
    print("-" * 40)

    metrics = tracer.get_service_metrics()

    print(f"   Service: {metrics['service']}")
    print(f"   Total traces: {metrics['total_traces']}")
    print(f"   Total spans: {metrics['total_spans']}")
    print(f"   Avg duration: {metrics['avg_trace_duration_ms']:.2f}ms")
    print()

    # Shutdown
    await tracer.shutdown()

    print("=" * 70)
    print("DEMO COMPLETE - Distributed Tracing System Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
