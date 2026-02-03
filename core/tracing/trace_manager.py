#!/usr/bin/env python3
"""
BAEL - Trace Manager
Advanced distributed tracing for AI agent operations.

Features:
- Span creation and management
- Context propagation
- Baggage items
- Span links
- Span events
- Span attributes
- Trace sampling
- Exporters
- Trace context
- Performance metrics
"""

import asyncio
import contextlib
import contextvars
import json
import random
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Awaitable, Callable, ContextManager, Dict, Generator,
                    Iterator, List, Optional, Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# CONTEXT VARIABLES
# =============================================================================

_current_span: contextvars.ContextVar['Span'] = contextvars.ContextVar(
    'current_span',
    default=None
)

_current_context: contextvars.ContextVar['TraceContext'] = contextvars.ContextVar(
    'current_context',
    default=None
)


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


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class SpanContext:
    """Span context for propagation."""
    trace_id: str = ""
    span_id: str = ""
    trace_flags: int = 0
    trace_state: Dict[str, str] = field(default_factory=dict)
    is_remote: bool = False

    @property
    def is_valid(self) -> bool:
        return bool(self.trace_id and self.span_id)

    @property
    def is_sampled(self) -> bool:
        return bool(self.trace_flags & 0x01)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "trace_flags": self.trace_flags,
            "trace_state": self.trace_state,
            "is_remote": self.is_remote
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SpanContext':
        return cls(
            trace_id=data.get("trace_id", ""),
            span_id=data.get("span_id", ""),
            trace_flags=data.get("trace_flags", 0),
            trace_state=data.get("trace_state", {}),
            is_remote=data.get("is_remote", False)
        )


@dataclass
class SpanEvent:
    """Event within a span."""
    name: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SpanLink:
    """Link to another span."""
    context: SpanContext = field(default_factory=SpanContext)
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TraceContext:
    """Trace context including baggage."""
    span_context: SpanContext = field(default_factory=SpanContext)
    baggage: Dict[str, str] = field(default_factory=dict)

    def with_baggage(self, key: str, value: str) -> 'TraceContext':
        new_baggage = dict(self.baggage)
        new_baggage[key] = value
        return TraceContext(
            span_context=self.span_context,
            baggage=new_baggage
        )


@dataclass
class TracerConfig:
    """Tracer configuration."""
    service_name: str = "bael"
    sample_rate: float = 1.0
    max_spans_per_trace: int = 1000
    max_attributes: int = 100
    max_events: int = 100
    max_links: int = 100


# =============================================================================
# SPAN
# =============================================================================

class Span:
    """
    A span represents a single operation within a trace.
    """

    def __init__(
        self,
        name: str,
        context: SpanContext,
        parent_context: Optional[SpanContext] = None,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
        links: Optional[List[SpanLink]] = None,
        start_time: Optional[datetime] = None
    ):
        self.name = name
        self.context = context
        self.parent_context = parent_context
        self.kind = kind
        self.attributes: Dict[str, Any] = attributes or {}
        self.links: List[SpanLink] = links or []
        self.events: List[SpanEvent] = []
        self.start_time = start_time or datetime.utcnow()
        self.end_time: Optional[datetime] = None
        self.status = SpanStatus.UNSET
        self.status_message: str = ""
        self._ended = False
        self._lock = threading.RLock()

    @property
    def trace_id(self) -> str:
        return self.context.trace_id

    @property
    def span_id(self) -> str:
        return self.context.span_id

    @property
    def parent_span_id(self) -> Optional[str]:
        return self.parent_context.span_id if self.parent_context else None

    @property
    def duration(self) -> Optional[float]:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    @property
    def is_recording(self) -> bool:
        return not self._ended

    def set_attribute(self, key: str, value: Any) -> 'Span':
        """Set a span attribute."""
        with self._lock:
            if self.is_recording:
                self.attributes[key] = value
        return self

    def set_attributes(self, attributes: Dict[str, Any]) -> 'Span':
        """Set multiple attributes."""
        with self._lock:
            if self.is_recording:
                self.attributes.update(attributes)
        return self

    def add_event(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None
    ) -> 'Span':
        """Add an event to the span."""
        with self._lock:
            if self.is_recording:
                event = SpanEvent(
                    name=name,
                    attributes=attributes or {}
                )
                self.events.append(event)
        return self

    def add_link(
        self,
        context: SpanContext,
        attributes: Optional[Dict[str, Any]] = None
    ) -> 'Span':
        """Add a link to another span."""
        with self._lock:
            if self.is_recording:
                link = SpanLink(
                    context=context,
                    attributes=attributes or {}
                )
                self.links.append(link)
        return self

    def set_status(
        self,
        status: SpanStatus,
        message: str = ""
    ) -> 'Span':
        """Set span status."""
        with self._lock:
            if self.is_recording:
                self.status = status
                self.status_message = message
        return self

    def record_exception(
        self,
        exception: Exception,
        escaped: bool = False
    ) -> 'Span':
        """Record an exception."""
        with self._lock:
            if self.is_recording:
                self.add_event(
                    "exception",
                    {
                        "exception.type": type(exception).__name__,
                        "exception.message": str(exception),
                        "exception.escaped": escaped
                    }
                )
                if self.status == SpanStatus.UNSET:
                    self.set_status(SpanStatus.ERROR, str(exception))
        return self

    def update_name(self, name: str) -> 'Span':
        """Update span name."""
        with self._lock:
            if self.is_recording:
                self.name = name
        return self

    def end(self, end_time: Optional[datetime] = None) -> None:
        """End the span."""
        with self._lock:
            if not self._ended:
                self.end_time = end_time or datetime.utcnow()
                self._ended = True

    def to_dict(self) -> Dict[str, Any]:
        """Serialize span to dictionary."""
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "kind": self.kind.value,
            "status": self.status.value,
            "status_message": self.status_message,
            "attributes": self.attributes,
            "events": [
                {
                    "name": e.name,
                    "timestamp": e.timestamp.isoformat(),
                    "attributes": e.attributes
                }
                for e in self.events
            ],
            "links": [
                {
                    "trace_id": l.context.trace_id,
                    "span_id": l.context.span_id,
                    "attributes": l.attributes
                }
                for l in self.links
            ],
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration * 1000 if self.duration else None
        }

    def __enter__(self) -> 'Span':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_val:
            self.record_exception(exc_val, escaped=True)
        self.end()


# =============================================================================
# SAMPLERS
# =============================================================================

class Sampler(ABC):
    """Base sampler."""

    @abstractmethod
    def should_sample(
        self,
        parent_context: Optional[SpanContext],
        trace_id: str,
        name: str,
        kind: SpanKind,
        attributes: Dict[str, Any]
    ) -> SamplingDecision:
        """Determine if span should be sampled."""
        pass


class AlwaysOnSampler(Sampler):
    """Always sample."""

    def should_sample(
        self,
        parent_context: Optional[SpanContext],
        trace_id: str,
        name: str,
        kind: SpanKind,
        attributes: Dict[str, Any]
    ) -> SamplingDecision:
        return SamplingDecision.RECORD_AND_SAMPLE


class AlwaysOffSampler(Sampler):
    """Never sample."""

    def should_sample(
        self,
        parent_context: Optional[SpanContext],
        trace_id: str,
        name: str,
        kind: SpanKind,
        attributes: Dict[str, Any]
    ) -> SamplingDecision:
        return SamplingDecision.DROP


class ProbabilitySampler(Sampler):
    """Sample based on probability."""

    def __init__(self, rate: float = 1.0):
        self.rate = max(0.0, min(1.0, rate))

    def should_sample(
        self,
        parent_context: Optional[SpanContext],
        trace_id: str,
        name: str,
        kind: SpanKind,
        attributes: Dict[str, Any]
    ) -> SamplingDecision:
        if random.random() < self.rate:
            return SamplingDecision.RECORD_AND_SAMPLE
        return SamplingDecision.DROP


class RateLimitingSampler(Sampler):
    """Sample up to a rate limit."""

    def __init__(self, max_per_second: float = 100.0):
        self.max_per_second = max_per_second
        self._tokens = max_per_second
        self._last_time = time.time()
        self._lock = threading.RLock()

    def should_sample(
        self,
        parent_context: Optional[SpanContext],
        trace_id: str,
        name: str,
        kind: SpanKind,
        attributes: Dict[str, Any]
    ) -> SamplingDecision:
        with self._lock:
            now = time.time()
            elapsed = now - self._last_time
            self._last_time = now

            # Replenish tokens
            self._tokens = min(
                self.max_per_second,
                self._tokens + elapsed * self.max_per_second
            )

            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return SamplingDecision.RECORD_AND_SAMPLE

            return SamplingDecision.DROP


class ParentBasedSampler(Sampler):
    """Sample based on parent decision."""

    def __init__(
        self,
        root_sampler: Sampler = None
    ):
        self.root_sampler = root_sampler or AlwaysOnSampler()

    def should_sample(
        self,
        parent_context: Optional[SpanContext],
        trace_id: str,
        name: str,
        kind: SpanKind,
        attributes: Dict[str, Any]
    ) -> SamplingDecision:
        if parent_context and parent_context.is_valid:
            if parent_context.is_sampled:
                return SamplingDecision.RECORD_AND_SAMPLE
            return SamplingDecision.DROP

        return self.root_sampler.should_sample(
            parent_context, trace_id, name, kind, attributes
        )


# =============================================================================
# EXPORTERS
# =============================================================================

class SpanExporter(ABC):
    """Base span exporter."""

    @abstractmethod
    async def export(self, spans: List[Span]) -> bool:
        """Export spans."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown exporter."""
        pass


class ConsoleExporter(SpanExporter):
    """Export spans to console."""

    def __init__(self, pretty: bool = True):
        self.pretty = pretty

    async def export(self, spans: List[Span]) -> bool:
        for span in spans:
            data = span.to_dict()
            if self.pretty:
                print(json.dumps(data, indent=2, default=str))
            else:
                print(json.dumps(data, default=str))
        return True

    async def shutdown(self) -> None:
        pass


class InMemoryExporter(SpanExporter):
    """Export spans to memory."""

    def __init__(self, max_spans: int = 10000):
        self.max_spans = max_spans
        self._spans: List[Span] = []
        self._lock = threading.RLock()

    async def export(self, spans: List[Span]) -> bool:
        with self._lock:
            self._spans.extend(spans)
            if len(self._spans) > self.max_spans:
                self._spans = self._spans[-self.max_spans:]
        return True

    async def shutdown(self) -> None:
        pass

    def get_spans(self) -> List[Span]:
        """Get all exported spans."""
        with self._lock:
            return list(self._spans)

    def clear(self) -> None:
        """Clear exported spans."""
        with self._lock:
            self._spans.clear()

    def find_by_name(self, name: str) -> List[Span]:
        """Find spans by name."""
        with self._lock:
            return [s for s in self._spans if s.name == name]

    def find_by_trace(self, trace_id: str) -> List[Span]:
        """Find spans by trace ID."""
        with self._lock:
            return [s for s in self._spans if s.trace_id == trace_id]


class BatchExporter(SpanExporter):
    """Batch spans for export."""

    def __init__(
        self,
        exporter: SpanExporter,
        batch_size: int = 100,
        export_interval: float = 5.0
    ):
        self._exporter = exporter
        self.batch_size = batch_size
        self.export_interval = export_interval
        self._queue: List[Span] = []
        self._lock = threading.RLock()
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start batch exporter."""
        self._running = True
        self._task = asyncio.create_task(self._export_loop())

    async def export(self, spans: List[Span]) -> bool:
        with self._lock:
            self._queue.extend(spans)

            if len(self._queue) >= self.batch_size:
                batch = self._queue[:self.batch_size]
                self._queue = self._queue[self.batch_size:]
                await self._exporter.export(batch)

        return True

    async def _export_loop(self) -> None:
        """Background export loop."""
        while self._running:
            await asyncio.sleep(self.export_interval)
            await self._flush()

    async def _flush(self) -> None:
        """Flush pending spans."""
        with self._lock:
            if self._queue:
                batch = self._queue
                self._queue = []

        if batch:
            await self._exporter.export(batch)

    async def shutdown(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        await self._flush()
        await self._exporter.shutdown()


# =============================================================================
# ID GENERATORS
# =============================================================================

class IdGenerator(ABC):
    """Base ID generator."""

    @abstractmethod
    def generate_trace_id(self) -> str:
        """Generate trace ID."""
        pass

    @abstractmethod
    def generate_span_id(self) -> str:
        """Generate span ID."""
        pass


class RandomIdGenerator(IdGenerator):
    """Generate random IDs."""

    def generate_trace_id(self) -> str:
        return uuid.uuid4().hex

    def generate_span_id(self) -> str:
        return uuid.uuid4().hex[:16]


# =============================================================================
# PROPAGATORS
# =============================================================================

class Propagator(ABC):
    """Context propagator."""

    @abstractmethod
    def inject(
        self,
        context: TraceContext,
        carrier: Dict[str, str]
    ) -> None:
        """Inject context into carrier."""
        pass

    @abstractmethod
    def extract(
        self,
        carrier: Dict[str, str]
    ) -> Optional[TraceContext]:
        """Extract context from carrier."""
        pass


class TraceContextPropagator(Propagator):
    """W3C Trace Context propagator."""

    TRACEPARENT = "traceparent"
    TRACESTATE = "tracestate"
    BAGGAGE = "baggage"

    def inject(
        self,
        context: TraceContext,
        carrier: Dict[str, str]
    ) -> None:
        if not context.span_context.is_valid:
            return

        # Inject traceparent
        traceparent = f"00-{context.span_context.trace_id}-{context.span_context.span_id}-{context.span_context.trace_flags:02x}"
        carrier[self.TRACEPARENT] = traceparent

        # Inject tracestate
        if context.span_context.trace_state:
            tracestate = ",".join(
                f"{k}={v}" for k, v in context.span_context.trace_state.items()
            )
            carrier[self.TRACESTATE] = tracestate

        # Inject baggage
        if context.baggage:
            baggage = ",".join(
                f"{k}={v}" for k, v in context.baggage.items()
            )
            carrier[self.BAGGAGE] = baggage

    def extract(
        self,
        carrier: Dict[str, str]
    ) -> Optional[TraceContext]:
        traceparent = carrier.get(self.TRACEPARENT)

        if not traceparent:
            return None

        parts = traceparent.split("-")
        if len(parts) != 4:
            return None

        version, trace_id, span_id, flags = parts

        # Parse trace state
        trace_state = {}
        tracestate = carrier.get(self.TRACESTATE)
        if tracestate:
            for pair in tracestate.split(","):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    trace_state[k.strip()] = v.strip()

        # Parse baggage
        baggage = {}
        baggage_str = carrier.get(self.BAGGAGE)
        if baggage_str:
            for pair in baggage_str.split(","):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    baggage[k.strip()] = v.strip()

        span_context = SpanContext(
            trace_id=trace_id,
            span_id=span_id,
            trace_flags=int(flags, 16),
            trace_state=trace_state,
            is_remote=True
        )

        return TraceContext(
            span_context=span_context,
            baggage=baggage
        )


# =============================================================================
# TRACER
# =============================================================================

class Tracer:
    """
    Tracer for creating spans.
    """

    def __init__(
        self,
        name: str,
        config: TracerConfig,
        id_generator: IdGenerator,
        sampler: Sampler,
        exporter: SpanExporter
    ):
        self.name = name
        self.config = config
        self._id_generator = id_generator
        self._sampler = sampler
        self._exporter = exporter
        self._active_spans: Dict[str, Span] = {}
        self._lock = threading.RLock()

    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
        links: Optional[List[SpanLink]] = None,
        parent: Optional[Span] = None
    ) -> Span:
        """Start a new span."""
        # Get parent context
        parent_context = None
        if parent:
            parent_context = parent.context
        else:
            current = _current_span.get()
            if current:
                parent_context = current.context

        # Generate IDs
        if parent_context and parent_context.is_valid:
            trace_id = parent_context.trace_id
        else:
            trace_id = self._id_generator.generate_trace_id()

        span_id = self._id_generator.generate_span_id()

        # Check sampling
        decision = self._sampler.should_sample(
            parent_context,
            trace_id,
            name,
            kind,
            attributes or {}
        )

        trace_flags = 0x01 if decision == SamplingDecision.RECORD_AND_SAMPLE else 0x00

        # Create span context
        span_context = SpanContext(
            trace_id=trace_id,
            span_id=span_id,
            trace_flags=trace_flags
        )

        # Create span
        span = Span(
            name=name,
            context=span_context,
            parent_context=parent_context,
            kind=kind,
            attributes=attributes,
            links=links
        )

        # Track active span
        with self._lock:
            self._active_spans[span_id] = span

        # Set as current
        _current_span.set(span)

        return span

    @contextlib.contextmanager
    def start_as_current_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> Generator[Span, None, None]:
        """Start span as current context."""
        span = self.start_span(name, kind, attributes, **kwargs)
        token = _current_span.set(span)

        try:
            yield span
        except Exception as e:
            span.record_exception(e, escaped=True)
            raise
        finally:
            span.end()
            _current_span.reset(token)
            asyncio.create_task(self._export_span(span))

    async def _export_span(self, span: Span) -> None:
        """Export a finished span."""
        with self._lock:
            self._active_spans.pop(span.span_id, None)

        if span.context.is_sampled:
            await self._exporter.export([span])

    def get_current_span(self) -> Optional[Span]:
        """Get current span."""
        return _current_span.get()


# =============================================================================
# TRACE MANAGER
# =============================================================================

class TraceManager:
    """
    Trace Manager for BAEL.

    Advanced distributed tracing.
    """

    def __init__(self, config: Optional[TracerConfig] = None):
        self.config = config or TracerConfig()
        self._id_generator = RandomIdGenerator()
        self._sampler: Sampler = ProbabilitySampler(self.config.sample_rate)
        self._exporter = InMemoryExporter()
        self._tracers: Dict[str, Tracer] = {}
        self._propagator = TraceContextPropagator()
        self._lock = threading.RLock()

    # -------------------------------------------------------------------------
    # TRACER
    # -------------------------------------------------------------------------

    def get_tracer(self, name: str = "default") -> Tracer:
        """Get or create a tracer."""
        with self._lock:
            if name not in self._tracers:
                self._tracers[name] = Tracer(
                    name=name,
                    config=self.config,
                    id_generator=self._id_generator,
                    sampler=self._sampler,
                    exporter=self._exporter
                )
            return self._tracers[name]

    # -------------------------------------------------------------------------
    # CONFIGURATION
    # -------------------------------------------------------------------------

    def set_sampler(self, sampler: Sampler) -> None:
        """Set the sampler."""
        self._sampler = sampler

        # Update existing tracers
        with self._lock:
            for tracer in self._tracers.values():
                tracer._sampler = sampler

    def set_exporter(self, exporter: SpanExporter) -> None:
        """Set the exporter."""
        self._exporter = exporter

        # Update existing tracers
        with self._lock:
            for tracer in self._tracers.values():
                tracer._exporter = exporter

    # -------------------------------------------------------------------------
    # SPAN OPERATIONS
    # -------------------------------------------------------------------------

    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
        tracer_name: str = "default"
    ) -> Span:
        """Start a new span."""
        tracer = self.get_tracer(tracer_name)
        return tracer.start_span(name, kind, attributes)

    @contextlib.contextmanager
    def trace(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Generator[Span, None, None]:
        """Trace a code block."""
        tracer = self.get_tracer()
        with tracer.start_as_current_span(name, kind, attributes) as span:
            yield span

    def get_current_span(self) -> Optional[Span]:
        """Get current span."""
        return _current_span.get()

    # -------------------------------------------------------------------------
    # CONTEXT PROPAGATION
    # -------------------------------------------------------------------------

    def inject(self, carrier: Dict[str, str]) -> None:
        """Inject trace context into carrier."""
        span = self.get_current_span()
        if span:
            context = TraceContext(span_context=span.context)
            self._propagator.inject(context, carrier)

    def extract(self, carrier: Dict[str, str]) -> Optional[TraceContext]:
        """Extract trace context from carrier."""
        return self._propagator.extract(carrier)

    def start_span_from_context(
        self,
        name: str,
        context: TraceContext,
        kind: SpanKind = SpanKind.SERVER
    ) -> Span:
        """Start span from extracted context."""
        tracer = self.get_tracer()

        # Create parent span context
        parent_context = context.span_context

        # Generate new span ID
        span_id = self._id_generator.generate_span_id()

        span_context = SpanContext(
            trace_id=parent_context.trace_id,
            span_id=span_id,
            trace_flags=parent_context.trace_flags,
            trace_state=parent_context.trace_state
        )

        span = Span(
            name=name,
            context=span_context,
            parent_context=parent_context,
            kind=kind
        )

        _current_span.set(span)

        return span

    # -------------------------------------------------------------------------
    # BAGGAGE
    # -------------------------------------------------------------------------

    def set_baggage(self, key: str, value: str) -> None:
        """Set baggage item."""
        current = _current_context.get()
        if current:
            new_context = current.with_baggage(key, value)
            _current_context.set(new_context)
        else:
            context = TraceContext(baggage={key: value})
            _current_context.set(context)

    def get_baggage(self, key: str) -> Optional[str]:
        """Get baggage item."""
        current = _current_context.get()
        if current:
            return current.baggage.get(key)
        return None

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def get_exported_spans(self) -> List[Span]:
        """Get exported spans (from InMemoryExporter)."""
        if isinstance(self._exporter, InMemoryExporter):
            return self._exporter.get_spans()
        return []

    def clear_spans(self) -> None:
        """Clear exported spans."""
        if isinstance(self._exporter, InMemoryExporter):
            self._exporter.clear()

    def find_trace(self, trace_id: str) -> List[Span]:
        """Find all spans in a trace."""
        if isinstance(self._exporter, InMemoryExporter):
            return self._exporter.find_by_trace(trace_id)
        return []

    async def shutdown(self) -> None:
        """Shutdown trace manager."""
        await self._exporter.shutdown()


# =============================================================================
# DECORATORS
# =============================================================================

def traced(
    name: Optional[str] = None,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None
) -> Callable:
    """Decorator to trace a function."""

    def decorator(func: Callable) -> Callable:
        span_name = name or func.__name__

        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                # Get or create manager
                tracer = Tracer(
                    "decorator",
                    TracerConfig(),
                    RandomIdGenerator(),
                    AlwaysOnSampler(),
                    InMemoryExporter()
                )

                with tracer.start_as_current_span(span_name, kind, attributes):
                    return await func(*args, **kwargs)

            return async_wrapper
        else:
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                tracer = Tracer(
                    "decorator",
                    TracerConfig(),
                    RandomIdGenerator(),
                    AlwaysOnSampler(),
                    InMemoryExporter()
                )

                span = tracer.start_span(span_name, kind, attributes)
                try:
                    return func(*args, **kwargs)
                finally:
                    span.end()

            return sync_wrapper

    return decorator


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Trace Manager."""
    print("=" * 70)
    print("BAEL - TRACE MANAGER DEMO")
    print("Advanced Distributed Tracing for AI Agents")
    print("=" * 70)
    print()

    manager = TraceManager()

    # 1. Basic Tracing
    print("1. BASIC TRACING:")
    print("-" * 40)

    with manager.trace("process_request") as span:
        span.set_attribute("http.method", "POST")
        span.set_attribute("http.url", "/api/process")

        # Simulate work
        await asyncio.sleep(0.01)

        span.add_event("Processing started")

        await asyncio.sleep(0.01)

        span.add_event("Processing completed")

    print(f"   Span: {span.name}")
    print(f"   Trace ID: {span.trace_id[:8]}...")
    print(f"   Duration: {span.duration*1000:.2f}ms")
    print()

    # 2. Nested Spans
    print("2. NESTED SPANS:")
    print("-" * 40)

    with manager.trace("parent_operation") as parent:
        parent.set_attribute("operation", "parent")

        with manager.trace("child_operation") as child:
            child.set_attribute("operation", "child")
            await asyncio.sleep(0.01)

        print(f"   Parent: {parent.span_id[:8]}...")
        print(f"   Child: {child.span_id[:8]}...")
        print(f"   Child parent: {child.parent_span_id[:8]}...")
    print()

    # 3. Span Kinds
    print("3. SPAN KINDS:")
    print("-" * 40)

    kinds = [SpanKind.SERVER, SpanKind.CLIENT, SpanKind.PRODUCER, SpanKind.CONSUMER]

    for kind in kinds:
        with manager.trace(f"{kind.value}_span", kind=kind) as span:
            await asyncio.sleep(0.001)
        print(f"   {kind.value}: {span.span_id[:8]}...")
    print()

    # 4. Error Handling
    print("4. ERROR HANDLING:")
    print("-" * 40)

    try:
        with manager.trace("failing_operation") as span:
            raise ValueError("Something went wrong")
    except ValueError:
        pass

    print(f"   Status: {span.status.value}")
    print(f"   Events: {[e.name for e in span.events]}")
    print()

    # 5. Context Propagation
    print("5. CONTEXT PROPAGATION:")
    print("-" * 40)

    with manager.trace("outgoing_request") as span:
        carrier = {}
        manager.inject(carrier)

        print(f"   Carrier: {list(carrier.keys())}")
        print(f"   Traceparent: {carrier.get('traceparent', '')[:30]}...")

    # Extract on receiving end
    context = manager.extract(carrier)
    if context:
        print(f"   Extracted trace: {context.span_context.trace_id[:8]}...")
    print()

    # 6. Samplers
    print("6. SAMPLERS:")
    print("-" * 40)

    # Probability sampler
    prob_sampler = ProbabilitySampler(0.5)
    sampled = sum(
        1 for _ in range(100)
        if prob_sampler.should_sample(None, "trace", "span", SpanKind.INTERNAL, {})
           == SamplingDecision.RECORD_AND_SAMPLE
    )
    print(f"   Probability (0.5): ~{sampled}% sampled")

    # Rate limiting sampler
    rate_sampler = RateLimitingSampler(10.0)
    print(f"   Rate limiter: max 10/sec")
    print()

    # 7. Span Attributes
    print("7. SPAN ATTRIBUTES:")
    print("-" * 40)

    with manager.trace("attributed_span") as span:
        span.set_attributes({
            "service.name": "bael",
            "service.version": "1.0.0",
            "http.status_code": 200,
            "custom.value": 42
        })

    for key, value in span.attributes.items():
        print(f"   {key}: {value}")
    print()

    # 8. Span Events
    print("8. SPAN EVENTS:")
    print("-" * 40)

    with manager.trace("event_span") as span:
        span.add_event("cache.miss", {"key": "user:123"})
        span.add_event("db.query", {"table": "users"})
        span.add_event("cache.set", {"key": "user:123", "ttl": 3600})

    for event in span.events:
        print(f"   {event.name}: {event.attributes}")
    print()

    # 9. Span Links
    print("9. SPAN LINKS:")
    print("-" * 40)

    # Create a span to link to
    with manager.trace("linked_span") as linked:
        pass

    with manager.trace("main_span") as span:
        span.add_link(linked.context, {"relationship": "caused_by"})

    for link in span.links:
        print(f"   Link to: {link.context.span_id[:8]}...")
    print()

    # 10. Exported Spans
    print("10. EXPORTED SPANS:")
    print("-" * 40)

    exported = manager.get_exported_spans()
    print(f"   Total exported: {len(exported)}")

    by_name = {}
    for s in exported:
        by_name[s.name] = by_name.get(s.name, 0) + 1

    for name, count in list(by_name.items())[:5]:
        print(f"   - {name}: {count}")
    print()

    # 11. Find Trace
    print("11. FIND TRACE:")
    print("-" * 40)

    if exported:
        trace_id = exported[0].trace_id
        trace_spans = manager.find_trace(trace_id)
        print(f"   Trace {trace_id[:8]}...")
        print(f"   Spans in trace: {len(trace_spans)}")
    print()

    # 12. Span Serialization
    print("12. SPAN SERIALIZATION:")
    print("-" * 40)

    if exported:
        span_dict = exported[0].to_dict()
        print(f"   Keys: {list(span_dict.keys())}")
    print()

    # 13. Tracer
    print("13. NAMED TRACERS:")
    print("-" * 40)

    http_tracer = manager.get_tracer("http")
    db_tracer = manager.get_tracer("database")

    span1 = http_tracer.start_span("http_request")
    span1.end()

    span2 = db_tracer.start_span("db_query")
    span2.end()

    print(f"   HTTP tracer: {http_tracer.name}")
    print(f"   DB tracer: {db_tracer.name}")
    print()

    # Cleanup
    await manager.shutdown()

    print("=" * 70)
    print("DEMO COMPLETE - Trace Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
