#!/usr/bin/env python3
"""
BAEL - Tracing Engine
Distributed tracing for agents.

Features:
- Trace context propagation
- Span management
- Baggage items
- Trace sampling
- Multi-service correlation
"""

import asyncio
import base64
import hashlib
import json
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (
    Any, Callable, Dict, Generic, List, Optional, Set, Tuple, Type, TypeVar, Union
)


T = TypeVar('T')


# =============================================================================
# CONTEXT VARIABLES
# =============================================================================

_current_trace: ContextVar[Optional["TraceContext"]] = ContextVar("current_trace", default=None)
_current_span: ContextVar[Optional["TracingSpan"]] = ContextVar("current_span", default=None)


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
    W3C_TRACEPARENT = "w3c_traceparent"
    B3_SINGLE = "b3_single"
    B3_MULTI = "b3_multi"
    JAEGER = "jaeger"
    CUSTOM = "custom"


class TracingState(Enum):
    """Tracing states."""
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class TracingConfig:
    """Tracing configuration."""
    service_name: str = "bael"
    sample_rate: float = 1.0
    max_spans_per_trace: int = 1000
    propagation_format: PropagationFormat = PropagationFormat.W3C_TRACEPARENT
    debug: bool = False


@dataclass
class TraceContext:
    """Trace context for propagation."""
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    parent_span_id: str = ""
    trace_flags: int = 0
    trace_state: str = ""
    sampled: bool = True
    
    def with_span(self, span_id: str) -> "TraceContext":
        """Create new context with span as parent."""
        return TraceContext(
            trace_id=self.trace_id,
            span_id=span_id,
            parent_span_id=self.span_id,
            trace_flags=self.trace_flags,
            trace_state=self.trace_state,
            sampled=self.sampled
        )


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
    trace_state: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TracingSpan:
    """A tracing span."""
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    trace_id: str = ""
    parent_span_id: str = ""
    name: str = ""
    kind: SpanKind = SpanKind.INTERNAL
    status: SpanStatus = SpanStatus.UNSET
    status_message: str = ""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[SpanEvent] = field(default_factory=list)
    links: List[SpanLink] = field(default_factory=list)
    baggage: Dict[str, str] = field(default_factory=dict)
    
    @property
    def duration_ms(self) -> float:
        if self.end_time:
            delta = self.end_time - self.start_time
            return delta.total_seconds() * 1000
        return 0.0
    
    @property
    def is_recording(self) -> bool:
        return self.end_time is None
    
    @property
    def context(self) -> TraceContext:
        return TraceContext(
            trace_id=self.trace_id,
            span_id=self.span_id,
            parent_span_id=self.parent_span_id,
            sampled=True
        )


@dataclass
class Trace:
    """A complete trace."""
    trace_id: str = ""
    root_span_id: str = ""
    spans: List[TracingSpan] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    service_name: str = ""
    
    @property
    def duration_ms(self) -> float:
        if self.end_time:
            delta = self.end_time - self.start_time
            return delta.total_seconds() * 1000
        return 0.0
    
    @property
    def span_count(self) -> int:
        return len(self.spans)


@dataclass
class TracingStats:
    """Tracing statistics."""
    traces_created: int = 0
    spans_created: int = 0
    spans_sampled: int = 0
    spans_dropped: int = 0
    errors_recorded: int = 0


# =============================================================================
# SAMPLER
# =============================================================================

class Sampler(ABC):
    """Abstract sampler."""
    
    @abstractmethod
    def should_sample(
        self,
        trace_id: str,
        name: str,
        kind: SpanKind,
        attributes: Dict[str, Any]
    ) -> SamplingDecision:
        """Decide whether to sample."""
        pass


class AlwaysOnSampler(Sampler):
    """Always samples."""
    
    def should_sample(
        self,
        trace_id: str,
        name: str,
        kind: SpanKind,
        attributes: Dict[str, Any]
    ) -> SamplingDecision:
        return SamplingDecision.RECORD_AND_SAMPLE


class AlwaysOffSampler(Sampler):
    """Never samples."""
    
    def should_sample(
        self,
        trace_id: str,
        name: str,
        kind: SpanKind,
        attributes: Dict[str, Any]
    ) -> SamplingDecision:
        return SamplingDecision.DROP


class ProbabilitySampler(Sampler):
    """Samples based on probability."""
    
    def __init__(self, rate: float = 1.0):
        self._rate = max(0.0, min(1.0, rate))
    
    def should_sample(
        self,
        trace_id: str,
        name: str,
        kind: SpanKind,
        attributes: Dict[str, Any]
    ) -> SamplingDecision:
        hash_value = int(hashlib.md5(trace_id.encode()).hexdigest()[:8], 16)
        threshold = int(self._rate * 0xFFFFFFFF)
        
        if hash_value <= threshold:
            return SamplingDecision.RECORD_AND_SAMPLE
        return SamplingDecision.DROP


class RateLimitingSampler(Sampler):
    """Rate-limited sampler."""
    
    def __init__(self, traces_per_second: float = 100.0):
        self._rate = traces_per_second
        self._tokens = traces_per_second
        self._last_refill = time.time()
    
    def should_sample(
        self,
        trace_id: str,
        name: str,
        kind: SpanKind,
        attributes: Dict[str, Any]
    ) -> SamplingDecision:
        now = time.time()
        elapsed = now - self._last_refill
        self._tokens = min(self._rate, self._tokens + elapsed * self._rate)
        self._last_refill = now
        
        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return SamplingDecision.RECORD_AND_SAMPLE
        return SamplingDecision.DROP


# =============================================================================
# PROPAGATOR
# =============================================================================

class Propagator(ABC):
    """Abstract context propagator."""
    
    @abstractmethod
    def inject(self, context: TraceContext) -> Dict[str, str]:
        """Inject context into headers."""
        pass
    
    @abstractmethod
    def extract(self, headers: Dict[str, str]) -> Optional[TraceContext]:
        """Extract context from headers."""
        pass


class W3CTraceContextPropagator(Propagator):
    """W3C Trace Context propagator."""
    
    TRACEPARENT_HEADER = "traceparent"
    TRACESTATE_HEADER = "tracestate"
    
    def inject(self, context: TraceContext) -> Dict[str, str]:
        """Inject W3C trace context."""
        flags = "01" if context.sampled else "00"
        traceparent = f"00-{context.trace_id}-{context.span_id}-{flags}"
        
        headers = {self.TRACEPARENT_HEADER: traceparent}
        
        if context.trace_state:
            headers[self.TRACESTATE_HEADER] = context.trace_state
        
        return headers
    
    def extract(self, headers: Dict[str, str]) -> Optional[TraceContext]:
        """Extract W3C trace context."""
        traceparent = headers.get(self.TRACEPARENT_HEADER)
        
        if not traceparent:
            return None
        
        parts = traceparent.split("-")
        if len(parts) != 4:
            return None
        
        version, trace_id, span_id, flags = parts
        
        return TraceContext(
            trace_id=trace_id,
            span_id=span_id,
            trace_flags=int(flags, 16),
            trace_state=headers.get(self.TRACESTATE_HEADER, ""),
            sampled=(int(flags, 16) & 0x01) == 1
        )


class B3Propagator(Propagator):
    """B3 propagator (single header format)."""
    
    B3_HEADER = "b3"
    
    def inject(self, context: TraceContext) -> Dict[str, str]:
        """Inject B3 context."""
        sampled = "1" if context.sampled else "0"
        b3 = f"{context.trace_id}-{context.span_id}-{sampled}"
        
        if context.parent_span_id:
            b3 += f"-{context.parent_span_id}"
        
        return {self.B3_HEADER: b3}
    
    def extract(self, headers: Dict[str, str]) -> Optional[TraceContext]:
        """Extract B3 context."""
        b3 = headers.get(self.B3_HEADER)
        
        if not b3:
            return None
        
        parts = b3.split("-")
        if len(parts) < 3:
            return None
        
        trace_id = parts[0]
        span_id = parts[1]
        sampled = parts[2] == "1"
        parent_span_id = parts[3] if len(parts) > 3 else ""
        
        return TraceContext(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            sampled=sampled
        )


# =============================================================================
# SPAN PROCESSOR
# =============================================================================

class SpanProcessor(ABC):
    """Abstract span processor."""
    
    @abstractmethod
    def on_start(self, span: TracingSpan) -> None:
        """Called when a span starts."""
        pass
    
    @abstractmethod
    def on_end(self, span: TracingSpan) -> None:
        """Called when a span ends."""
        pass


class SimpleSpanProcessor(SpanProcessor):
    """Simple span processor that stores spans."""
    
    def __init__(self):
        self._spans: List[TracingSpan] = []
    
    def on_start(self, span: TracingSpan) -> None:
        """Record span start."""
        pass
    
    def on_end(self, span: TracingSpan) -> None:
        """Record span end."""
        self._spans.append(span)
    
    def get_spans(self) -> List[TracingSpan]:
        """Get recorded spans."""
        return list(self._spans)
    
    def clear(self) -> None:
        """Clear recorded spans."""
        self._spans.clear()


class BatchSpanProcessor(SpanProcessor):
    """Batching span processor."""
    
    def __init__(self, batch_size: int = 100):
        self._batch_size = batch_size
        self._batch: List[TracingSpan] = []
        self._exported: List[List[TracingSpan]] = []
    
    def on_start(self, span: TracingSpan) -> None:
        pass
    
    def on_end(self, span: TracingSpan) -> None:
        self._batch.append(span)
        
        if len(self._batch) >= self._batch_size:
            self._export_batch()
    
    def _export_batch(self) -> None:
        if self._batch:
            self._exported.append(list(self._batch))
            self._batch.clear()
    
    def flush(self) -> None:
        self._export_batch()
    
    def get_exported(self) -> List[List[TracingSpan]]:
        return self._exported


# =============================================================================
# TRACER
# =============================================================================

class Tracer:
    """Creates and manages spans."""
    
    def __init__(
        self,
        service_name: str,
        sampler: Optional[Sampler] = None,
        processor: Optional[SpanProcessor] = None
    ):
        self._service_name = service_name
        self._sampler = sampler or AlwaysOnSampler()
        self._processor = processor or SimpleSpanProcessor()
        self._traces: Dict[str, Trace] = {}
    
    @property
    def service_name(self) -> str:
        return self._service_name
    
    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        parent: Optional[TracingSpan] = None,
        context: Optional[TraceContext] = None,
        attributes: Optional[Dict[str, Any]] = None,
        links: Optional[List[SpanLink]] = None
    ) -> TracingSpan:
        """Start a new span."""
        if context:
            trace_id = context.trace_id
            parent_span_id = context.span_id
        elif parent:
            trace_id = parent.trace_id
            parent_span_id = parent.span_id
        else:
            trace_id = uuid.uuid4().hex
            parent_span_id = ""
        
        decision = self._sampler.should_sample(
            trace_id, name, kind, attributes or {}
        )
        
        span = TracingSpan(
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            name=name,
            kind=kind,
            attributes=attributes or {},
            links=links or []
        )
        
        self._processor.on_start(span)
        
        if trace_id not in self._traces:
            self._traces[trace_id] = Trace(
                trace_id=trace_id,
                root_span_id=span.span_id,
                service_name=self._service_name
            )
        
        self._traces[trace_id].spans.append(span)
        
        return span
    
    def end_span(
        self,
        span: TracingSpan,
        status: SpanStatus = SpanStatus.OK,
        status_message: str = ""
    ) -> None:
        """End a span."""
        span.end_time = datetime.now()
        span.status = status
        span.status_message = status_message
        
        self._processor.on_end(span)
        
        if span.trace_id in self._traces:
            trace = self._traces[span.trace_id]
            if span.span_id == trace.root_span_id:
                trace.end_time = span.end_time
    
    def add_event(
        self,
        span: TracingSpan,
        name: str,
        attributes: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add an event to a span."""
        event = SpanEvent(name=name, attributes=attributes or {})
        span.events.append(event)
    
    def set_attribute(self, span: TracingSpan, key: str, value: Any) -> None:
        """Set a span attribute."""
        span.attributes[key] = value
    
    def set_baggage(self, span: TracingSpan, key: str, value: str) -> None:
        """Set baggage on a span."""
        span.baggage[key] = value
    
    def record_exception(
        self,
        span: TracingSpan,
        exception: Exception,
        escaped: bool = True
    ) -> None:
        """Record an exception on a span."""
        span.status = SpanStatus.ERROR
        span.status_message = str(exception)
        
        self.add_event(span, "exception", {
            "exception.type": type(exception).__name__,
            "exception.message": str(exception),
            "exception.escaped": escaped
        })
    
    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """Get a trace by ID."""
        return self._traces.get(trace_id)
    
    def get_traces(self) -> List[Trace]:
        """Get all traces."""
        return list(self._traces.values())


# =============================================================================
# TRACING ENGINE
# =============================================================================

class TracingEngine:
    """
    Tracing Engine for BAEL.
    
    Distributed tracing for agents.
    """
    
    def __init__(self, config: Optional[TracingConfig] = None):
        self._config = config or TracingConfig()
        self._sampler: Sampler = ProbabilitySampler(self._config.sample_rate)
        self._processor = SimpleSpanProcessor()
        self._tracer = Tracer(
            self._config.service_name,
            self._sampler,
            self._processor
        )
        self._propagator: Propagator = W3CTraceContextPropagator()
        self._stats = TracingStats()
        self._state = TracingState.ACTIVE
    
    # ----- Configuration -----
    
    @property
    def config(self) -> TracingConfig:
        return self._config
    
    @property
    def state(self) -> TracingState:
        return self._state
    
    def set_sampler(self, sampler: Sampler) -> None:
        """Set the sampler."""
        self._sampler = sampler
        self._tracer._sampler = sampler
    
    def set_propagator(self, propagator: Propagator) -> None:
        """Set the propagator."""
        self._propagator = propagator
    
    # ----- Context Management -----
    
    def get_current_trace(self) -> Optional[TraceContext]:
        """Get the current trace context."""
        return _current_trace.get()
    
    def get_current_span(self) -> Optional[TracingSpan]:
        """Get the current span."""
        return _current_span.get()
    
    def set_current_span(self, span: TracingSpan) -> None:
        """Set the current span."""
        _current_span.set(span)
        _current_trace.set(span.context)
    
    # ----- Span Management -----
    
    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        parent: Optional[TracingSpan] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> TracingSpan:
        """Start a new span."""
        if self._state != TracingState.ACTIVE:
            return TracingSpan(name=name)
        
        if parent is None:
            parent = self.get_current_span()
        
        span = self._tracer.start_span(
            name=name,
            kind=kind,
            parent=parent,
            attributes=attributes
        )
        
        self._stats.spans_created += 1
        
        if parent is None:
            self._stats.traces_created += 1
        
        return span
    
    def end_span(
        self,
        span: TracingSpan,
        status: SpanStatus = SpanStatus.OK,
        error: Optional[Exception] = None
    ) -> None:
        """End a span."""
        if error:
            self._tracer.record_exception(span, error)
            status = SpanStatus.ERROR
            self._stats.errors_recorded += 1
        
        self._tracer.end_span(span, status)
    
    def add_event(
        self,
        span: TracingSpan,
        name: str,
        attributes: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add an event to a span."""
        self._tracer.add_event(span, name, attributes)
    
    def set_attribute(self, span: TracingSpan, key: str, value: Any) -> None:
        """Set a span attribute."""
        self._tracer.set_attribute(span, key, value)
    
    def set_baggage(self, span: TracingSpan, key: str, value: str) -> None:
        """Set baggage on a span."""
        self._tracer.set_baggage(span, key, value)
    
    # ----- Context Propagation -----
    
    def inject(self, span: TracingSpan) -> Dict[str, str]:
        """Inject trace context into headers."""
        return self._propagator.inject(span.context)
    
    def extract(self, headers: Dict[str, str]) -> Optional[TraceContext]:
        """Extract trace context from headers."""
        return self._propagator.extract(headers)
    
    def start_span_from_headers(
        self,
        name: str,
        headers: Dict[str, str],
        kind: SpanKind = SpanKind.SERVER
    ) -> TracingSpan:
        """Start a span from incoming headers."""
        context = self.extract(headers)
        
        return self._tracer.start_span(
            name=name,
            kind=kind,
            context=context
        )
    
    # ----- Span Context Manager -----
    
    class SpanContextManager:
        """Context manager for spans."""
        
        def __init__(self, engine: "TracingEngine", span: TracingSpan):
            self._engine = engine
            self._span = span
            self._token = None
        
        def __enter__(self) -> TracingSpan:
            self._token = _current_span.set(self._span)
            return self._span
        
        def __exit__(self, exc_type, exc_val, exc_tb) -> None:
            if exc_type:
                self._engine.end_span(self._span, SpanStatus.ERROR, exc_val)
            else:
                self._engine.end_span(self._span, SpanStatus.OK)
            
            if self._token:
                _current_span.reset(self._token)
    
    def span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None
    ) -> SpanContextManager:
        """Create a span context manager."""
        span = self.start_span(name, kind, attributes=attributes)
        return self.SpanContextManager(self, span)
    
    # ----- Trace Queries -----
    
    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """Get a trace by ID."""
        return self._tracer.get_trace(trace_id)
    
    def get_traces(self) -> List[Trace]:
        """Get all traces."""
        return self._tracer.get_traces()
    
    def get_spans(self) -> List[TracingSpan]:
        """Get all recorded spans."""
        if isinstance(self._processor, SimpleSpanProcessor):
            return self._processor.get_spans()
        return []
    
    def get_trace_tree(self, trace_id: str) -> Dict[str, Any]:
        """Get a trace as a tree structure."""
        trace = self.get_trace(trace_id)
        
        if not trace:
            return {}
        
        spans_by_id = {s.span_id: s for s in trace.spans}
        
        def build_tree(span_id: str) -> Dict[str, Any]:
            span = spans_by_id.get(span_id)
            if not span:
                return {}
            
            children = [
                s for s in trace.spans
                if s.parent_span_id == span_id
            ]
            
            return {
                "span_id": span.span_id,
                "name": span.name,
                "duration_ms": span.duration_ms,
                "status": span.status.value,
                "children": [build_tree(c.span_id) for c in children]
            }
        
        return build_tree(trace.root_span_id)
    
    # ----- Control -----
    
    def pause(self) -> None:
        """Pause tracing."""
        self._state = TracingState.PAUSED
    
    def resume(self) -> None:
        """Resume tracing."""
        self._state = TracingState.ACTIVE
    
    def stop(self) -> None:
        """Stop tracing."""
        self._state = TracingState.STOPPED
    
    # ----- Stats -----
    
    @property
    def stats(self) -> TracingStats:
        return self._stats
    
    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "service": self._config.service_name,
            "state": self._state.value,
            "sample_rate": self._config.sample_rate,
            "traces_created": self._stats.traces_created,
            "spans_created": self._stats.spans_created,
            "errors_recorded": self._stats.errors_recorded
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Tracing Engine."""
    print("=" * 70)
    print("BAEL - TRACING ENGINE DEMO")
    print("Distributed Tracing for Agents")
    print("=" * 70)
    print()
    
    config = TracingConfig(
        service_name="bael-demo",
        sample_rate=1.0
    )
    
    engine = TracingEngine(config)
    
    # 1. Start a Root Span
    print("1. START ROOT SPAN:")
    print("-" * 40)
    
    root_span = engine.start_span("handle_request", SpanKind.SERVER)
    engine.set_attribute(root_span, "http.method", "GET")
    engine.set_attribute(root_span, "http.url", "/api/search")
    
    print(f"   Trace ID: {root_span.trace_id[:16]}...")
    print(f"   Span ID: {root_span.span_id}")
    print(f"   Name: {root_span.name}")
    print()
    
    # 2. Child Span
    print("2. CREATE CHILD SPAN:")
    print("-" * 40)
    
    child_span = engine.start_span("query_database", SpanKind.CLIENT, parent=root_span)
    engine.set_attribute(child_span, "db.system", "postgres")
    await asyncio.sleep(0.03)
    engine.end_span(child_span)
    
    print(f"   Parent: {child_span.parent_span_id}")
    print(f"   Duration: {child_span.duration_ms:.2f}ms")
    print()
    
    # 3. Add Events
    print("3. ADD EVENTS:")
    print("-" * 40)
    
    engine.add_event(root_span, "validation_complete", {"valid": True})
    await asyncio.sleep(0.01)
    engine.add_event(root_span, "processing_started")
    
    print(f"   Events: {len(root_span.events)}")
    for event in root_span.events:
        print(f"   - {event.name}: {event.attributes}")
    print()
    
    # 4. Set Baggage
    print("4. SET BAGGAGE:")
    print("-" * 40)
    
    engine.set_baggage(root_span, "user_id", "user-123")
    engine.set_baggage(root_span, "tenant", "acme")
    
    print(f"   Baggage: {root_span.baggage}")
    print()
    
    # 5. End Root Span
    print("5. END ROOT SPAN:")
    print("-" * 40)
    
    await asyncio.sleep(0.02)
    engine.end_span(root_span)
    
    print(f"   Duration: {root_span.duration_ms:.2f}ms")
    print(f"   Status: {root_span.status.value}")
    print()
    
    # 6. Span Context Manager
    print("6. SPAN CONTEXT MANAGER:")
    print("-" * 40)
    
    with engine.span("process_item", SpanKind.INTERNAL) as span:
        engine.set_attribute(span, "item_id", "item-1")
        await asyncio.sleep(0.015)
        engine.add_event(span, "item_processed")
    
    print(f"   Span: {span.name}")
    print(f"   Duration: {span.duration_ms:.2f}ms")
    print()
    
    # 7. Context Propagation
    print("7. CONTEXT PROPAGATION:")
    print("-" * 40)
    
    upstream_span = engine.start_span("upstream_request", SpanKind.CLIENT)
    
    headers = engine.inject(upstream_span)
    print(f"   Injected headers: {headers}")
    
    extracted = engine.extract(headers)
    print(f"   Extracted trace ID: {extracted.trace_id[:16]}...")
    
    engine.end_span(upstream_span)
    print()
    
    # 8. Start from Headers
    print("8. START FROM HEADERS:")
    print("-" * 40)
    
    incoming_headers = {
        "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    }
    
    incoming_span = engine.start_span_from_headers("handle_incoming", incoming_headers)
    print(f"   Trace ID from header: {incoming_span.trace_id[:16]}...")
    engine.end_span(incoming_span)
    print()
    
    # 9. Error Recording
    print("9. ERROR RECORDING:")
    print("-" * 40)
    
    error_span = engine.start_span("failing_operation")
    
    try:
        raise ValueError("Something went wrong")
    except Exception as e:
        engine.end_span(error_span, error=e)
    
    print(f"   Status: {error_span.status.value}")
    print(f"   Message: {error_span.status_message}")
    print(f"   Events: {[e.name for e in error_span.events]}")
    print()
    
    # 10. Get Trace
    print("10. GET TRACE:")
    print("-" * 40)
    
    trace = engine.get_trace(root_span.trace_id)
    
    if trace:
        print(f"   Trace ID: {trace.trace_id[:16]}...")
        print(f"   Span count: {trace.span_count}")
        print(f"   Duration: {trace.duration_ms:.2f}ms")
    print()
    
    # 11. Trace Tree
    print("11. TRACE TREE:")
    print("-" * 40)
    
    tree = engine.get_trace_tree(root_span.trace_id)
    
    def print_tree(node: Dict, indent: int = 0):
        if node:
            prefix = "  " * indent
            print(f"{prefix}- {node['name']} ({node['duration_ms']:.2f}ms)")
            for child in node.get('children', []):
                print_tree(child, indent + 1)
    
    print_tree(tree)
    print()
    
    # 12. All Spans
    print("12. ALL SPANS:")
    print("-" * 40)
    
    spans = engine.get_spans()
    print(f"   Total spans: {len(spans)}")
    for s in spans[:5]:
        print(f"   - {s.name}: {s.duration_ms:.2f}ms ({s.status.value})")
    print()
    
    # 13. Statistics
    print("13. STATISTICS:")
    print("-" * 40)
    
    stats = engine.stats
    print(f"   Traces created: {stats.traces_created}")
    print(f"   Spans created: {stats.spans_created}")
    print(f"   Errors recorded: {stats.errors_recorded}")
    print()
    
    # 14. Engine Summary
    print("14. ENGINE SUMMARY:")
    print("-" * 40)
    
    summary = engine.summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()
    
    print("=" * 70)
    print("DEMO COMPLETE - Tracing Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
