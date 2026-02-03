#!/usr/bin/env python3
"""
BAEL - Distributed Tracing System
Comprehensive request tracing and span management.

This module provides a complete distributed tracing framework
for observability across services.

Features:
- Span creation and management
- Context propagation
- Trace sampling
- Multiple exporters
- Baggage items
- Span events and attributes
- Trace visualization
- Performance analysis
- Error tracking
- Integration support
"""

import asyncio
import functools
import json
import logging
import os
import random
import threading
import time
import traceback
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import (Any, Callable, Coroutine, Dict, Generic, Iterator, List,
                    Optional, Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class SpanKind(Enum):
    """Types of spans."""
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
# DATA STRUCTURES
# =============================================================================

@dataclass
class TraceContext:
    """Trace context for propagation."""
    trace_id: str
    span_id: str
    trace_flags: int = 0
    trace_state: Dict[str, str] = field(default_factory=dict)

    @property
    def is_sampled(self) -> bool:
        return (self.trace_flags & 0x01) != 0

    def to_header(self) -> str:
        """Convert to W3C traceparent header."""
        return f"00-{self.trace_id}-{self.span_id}-{self.trace_flags:02x}"

    @classmethod
    def from_header(cls, header: str) -> Optional['TraceContext']:
        """Parse from W3C traceparent header."""
        try:
            parts = header.split('-')
            if len(parts) != 4:
                return None

            return cls(
                trace_id=parts[1],
                span_id=parts[2],
                trace_flags=int(parts[3], 16)
            )
        except:
            return None


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
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Span:
    """A single trace span."""
    name: str
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    parent_span_id: Optional[str] = None

    kind: SpanKind = SpanKind.INTERNAL
    status: SpanStatus = SpanStatus.UNSET
    status_message: str = ""

    # Timing
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None

    # Data
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[SpanEvent] = field(default_factory=list)
    links: List[SpanLink] = field(default_factory=list)
    baggage: Dict[str, str] = field(default_factory=dict)

    # Sampling
    is_sampled: bool = True
    is_recording: bool = True

    @property
    def duration_ns(self) -> int:
        """Duration in nanoseconds."""
        if self.end_time is None:
            return 0
        return int((self.end_time - self.start_time) * 1e9)

    @property
    def duration_ms(self) -> float:
        """Duration in milliseconds."""
        return self.duration_ns / 1e6

    def set_attribute(self, key: str, value: Any) -> 'Span':
        """Set an attribute."""
        if self.is_recording:
            self.attributes[key] = value
        return self

    def set_attributes(self, attributes: Dict[str, Any]) -> 'Span':
        """Set multiple attributes."""
        if self.is_recording:
            self.attributes.update(attributes)
        return self

    def add_event(
        self,
        name: str,
        attributes: Dict[str, Any] = None
    ) -> 'Span':
        """Add an event."""
        if self.is_recording:
            self.events.append(SpanEvent(
                name=name,
                attributes=attributes or {}
            ))
        return self

    def add_link(
        self,
        trace_id: str,
        span_id: str,
        attributes: Dict[str, Any] = None
    ) -> 'Span':
        """Add a link to another span."""
        if self.is_recording:
            self.links.append(SpanLink(
                trace_id=trace_id,
                span_id=span_id,
                attributes=attributes or {}
            ))
        return self

    def set_status(
        self,
        status: SpanStatus,
        message: str = ""
    ) -> 'Span':
        """Set span status."""
        self.status = status
        self.status_message = message
        return self

    def record_exception(
        self,
        exception: Exception,
        attributes: Dict[str, Any] = None
    ) -> 'Span':
        """Record an exception."""
        self.set_status(SpanStatus.ERROR, str(exception))

        exc_attrs = {
            "exception.type": type(exception).__name__,
            "exception.message": str(exception),
            "exception.stacktrace": traceback.format_exc()
        }

        if attributes:
            exc_attrs.update(attributes)

        self.add_event("exception", exc_attrs)
        return self

    def end(self, end_time: float = None) -> None:
        """End the span."""
        self.end_time = end_time or time.time()

    def get_context(self) -> TraceContext:
        """Get trace context for propagation."""
        return TraceContext(
            trace_id=self.trace_id,
            span_id=self.span_id,
            trace_flags=1 if self.is_sampled else 0
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "kind": self.kind.value,
            "status": self.status.value,
            "status_message": self.status_message,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "attributes": self.attributes,
            "events": [
                {"name": e.name, "timestamp": e.timestamp, "attributes": e.attributes}
                for e in self.events
            ]
        }


@dataclass
class Trace:
    """Complete trace with all spans."""
    trace_id: str
    spans: List[Span] = field(default_factory=list)

    @property
    def root_span(self) -> Optional[Span]:
        """Get root span."""
        for span in self.spans:
            if span.parent_span_id is None:
                return span
        return self.spans[0] if self.spans else None

    @property
    def duration_ms(self) -> float:
        """Total trace duration."""
        if not self.spans:
            return 0

        start = min(s.start_time for s in self.spans)
        end = max((s.end_time or s.start_time) for s in self.spans)
        return (end - start) * 1000

    def get_span(self, span_id: str) -> Optional[Span]:
        """Get span by ID."""
        for span in self.spans:
            if span.span_id == span_id:
                return span
        return None

    def get_children(self, span_id: str) -> List[Span]:
        """Get child spans."""
        return [s for s in self.spans if s.parent_span_id == span_id]


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


class TraceIdRatioSampler(Sampler):
    """Sample based on trace ID ratio."""

    def __init__(self, ratio: float = 0.1):
        self.ratio = max(0.0, min(1.0, ratio))

    def should_sample(
        self,
        trace_id: str,
        name: str,
        parent_context: Optional[TraceContext] = None
    ) -> SamplingDecision:
        # Use trace ID to make consistent decisions
        hash_val = int(trace_id[:8], 16) / (16 ** 8)

        if hash_val < self.ratio:
            return SamplingDecision.RECORD_AND_SAMPLE
        return SamplingDecision.DROP


class ParentBasedSampler(Sampler):
    """Sample based on parent span decision."""

    def __init__(self, root_sampler: Sampler = None):
        self.root_sampler = root_sampler or AlwaysOnSampler()

    def should_sample(
        self,
        trace_id: str,
        name: str,
        parent_context: Optional[TraceContext] = None
    ) -> SamplingDecision:
        if parent_context:
            if parent_context.is_sampled:
                return SamplingDecision.RECORD_AND_SAMPLE
            return SamplingDecision.DROP

        return self.root_sampler.should_sample(trace_id, name, None)


# =============================================================================
# EXPORTERS
# =============================================================================

class SpanExporter(ABC):
    """Abstract span exporter."""

    @abstractmethod
    async def export(self, spans: List[Span]) -> bool:
        pass

    async def shutdown(self) -> None:
        pass


class ConsoleExporter(SpanExporter):
    """Export spans to console."""

    def __init__(self, pretty: bool = True):
        self.pretty = pretty

    async def export(self, spans: List[Span]) -> bool:
        for span in spans:
            if self.pretty:
                self._print_pretty(span)
            else:
                print(json.dumps(span.to_dict()))
        return True

    def _print_pretty(self, span: Span) -> None:
        print(f"\n{'─' * 50}")
        print(f"Span: {span.name}")
        print(f"  Trace ID: {span.trace_id[:8]}...")
        print(f"  Span ID: {span.span_id}")
        print(f"  Parent: {span.parent_span_id or 'None'}")
        print(f"  Duration: {span.duration_ms:.2f}ms")
        print(f"  Status: {span.status.value}")

        if span.attributes:
            print(f"  Attributes: {span.attributes}")

        if span.events:
            print(f"  Events: {len(span.events)}")
            for event in span.events:
                print(f"    - {event.name}")


class MemoryExporter(SpanExporter):
    """Store spans in memory."""

    def __init__(self, max_spans: int = 10000):
        self.spans: deque = deque(maxlen=max_spans)
        self._lock = asyncio.Lock()

    async def export(self, spans: List[Span]) -> bool:
        async with self._lock:
            self.spans.extend(spans)
        return True

    async def get_spans(self) -> List[Span]:
        async with self._lock:
            return list(self.spans)

    async def get_trace(self, trace_id: str) -> Optional[Trace]:
        async with self._lock:
            trace_spans = [s for s in self.spans if s.trace_id == trace_id]
            if trace_spans:
                return Trace(trace_id=trace_id, spans=trace_spans)
            return None

    async def clear(self) -> None:
        async with self._lock:
            self.spans.clear()


class FileExporter(SpanExporter):
    """Export spans to file."""

    def __init__(self, file_path: str):
        self.file_path = file_path

    async def export(self, spans: List[Span]) -> bool:
        try:
            with open(self.file_path, 'a') as f:
                for span in spans:
                    f.write(json.dumps(span.to_dict()) + '\n')
            return True
        except Exception as e:
            logger.error(f"File export error: {e}")
            return False


class BatchExporter(SpanExporter):
    """Batch spans for export."""

    def __init__(
        self,
        exporter: SpanExporter,
        max_batch_size: int = 512,
        max_queue_size: int = 2048,
        export_interval: float = 5.0
    ):
        self.exporter = exporter
        self.max_batch_size = max_batch_size
        self.max_queue_size = max_queue_size
        self.export_interval = export_interval

        self._queue: deque = deque(maxlen=max_queue_size)
        self._lock = asyncio.Lock()
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._export_loop())

    async def shutdown(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        # Export remaining spans
        async with self._lock:
            if self._queue:
                await self.exporter.export(list(self._queue))
                self._queue.clear()

    async def export(self, spans: List[Span]) -> bool:
        async with self._lock:
            self._queue.extend(spans)
        return True

    async def _export_loop(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(self.export_interval)

                async with self._lock:
                    if not self._queue:
                        continue

                    batch = []
                    while self._queue and len(batch) < self.max_batch_size:
                        batch.append(self._queue.popleft())

                if batch:
                    await self.exporter.export(batch)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Batch export error: {e}")


# =============================================================================
# SPAN PROCESSOR
# =============================================================================

class SpanProcessor(ABC):
    """Abstract span processor."""

    @abstractmethod
    def on_start(self, span: Span) -> None:
        pass

    @abstractmethod
    async def on_end(self, span: Span) -> None:
        pass

    async def shutdown(self) -> None:
        pass


class SimpleSpanProcessor(SpanProcessor):
    """Simple synchronous span processor."""

    def __init__(self, exporter: SpanExporter):
        self.exporter = exporter

    def on_start(self, span: Span) -> None:
        pass

    async def on_end(self, span: Span) -> None:
        await self.exporter.export([span])

    async def shutdown(self) -> None:
        await self.exporter.shutdown()


class BatchSpanProcessor(SpanProcessor):
    """Batch span processor."""

    def __init__(self, exporter: SpanExporter):
        self.batch_exporter = BatchExporter(exporter)

    def on_start(self, span: Span) -> None:
        pass

    async def on_end(self, span: Span) -> None:
        await self.batch_exporter.export([span])

    async def shutdown(self) -> None:
        await self.batch_exporter.shutdown()


# =============================================================================
# TRACER
# =============================================================================

class Tracer:
    """
    Core tracer for creating and managing spans.
    """

    def __init__(
        self,
        name: str,
        sampler: Sampler = None,
        processors: List[SpanProcessor] = None
    ):
        self.name = name
        self.sampler = sampler or AlwaysOnSampler()
        self.processors = processors or []

        # Context storage
        self._context: threading.local = threading.local()
        self._async_context: Dict[int, List[Span]] = {}

    @property
    def current_span(self) -> Optional[Span]:
        """Get current active span."""
        stack = self._get_span_stack()
        return stack[-1] if stack else None

    def _get_span_stack(self) -> List[Span]:
        """Get span stack for current context."""
        # Try async context first
        task_id = id(asyncio.current_task()) if asyncio.current_task() else None

        if task_id and task_id in self._async_context:
            return self._async_context[task_id]

        # Fall back to thread local
        if not hasattr(self._context, 'stack'):
            self._context.stack = []
        return self._context.stack

    def _push_span(self, span: Span) -> None:
        """Push span to stack."""
        task_id = id(asyncio.current_task()) if asyncio.current_task() else None

        if task_id:
            if task_id not in self._async_context:
                self._async_context[task_id] = []
            self._async_context[task_id].append(span)
        else:
            if not hasattr(self._context, 'stack'):
                self._context.stack = []
            self._context.stack.append(span)

    def _pop_span(self) -> Optional[Span]:
        """Pop span from stack."""
        task_id = id(asyncio.current_task()) if asyncio.current_task() else None

        if task_id and task_id in self._async_context:
            stack = self._async_context[task_id]
            if stack:
                return stack.pop()
        else:
            stack = self._get_span_stack()
            if stack:
                return stack.pop()

        return None

    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Dict[str, Any] = None,
        links: List[SpanLink] = None,
        parent: Optional[TraceContext] = None
    ) -> Span:
        """Start a new span."""
        current = self.current_span

        # Determine trace ID and parent
        if parent:
            trace_id = parent.trace_id
            parent_span_id = parent.span_id
        elif current:
            trace_id = current.trace_id
            parent_span_id = current.span_id
        else:
            trace_id = uuid.uuid4().hex
            parent_span_id = None

        # Sampling decision
        parent_ctx = parent or (current.get_context() if current else None)
        decision = self.sampler.should_sample(trace_id, name, parent_ctx)

        is_sampled = decision == SamplingDecision.RECORD_AND_SAMPLE
        is_recording = decision != SamplingDecision.DROP

        # Create span
        span = Span(
            name=name,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            kind=kind,
            is_sampled=is_sampled,
            is_recording=is_recording
        )

        if attributes:
            span.set_attributes(attributes)

        if links:
            span.links = links

        # Copy baggage from parent
        if current:
            span.baggage = current.baggage.copy()

        # Notify processors
        for processor in self.processors:
            processor.on_start(span)

        # Push to stack
        self._push_span(span)

        return span

    async def end_span(self, span: Span = None) -> None:
        """End a span."""
        if span is None:
            span = self._pop_span()
        else:
            # Remove from stack
            stack = self._get_span_stack()
            if span in stack:
                stack.remove(span)

        if span:
            span.end()

            # Notify processors
            for processor in self.processors:
                await processor.on_end(span)

    @asynccontextmanager
    async def span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Dict[str, Any] = None
    ):
        """Async context manager for spans."""
        span = self.start_span(name, kind, attributes)
        try:
            yield span
            if span.status == SpanStatus.UNSET:
                span.set_status(SpanStatus.OK)
        except Exception as e:
            span.record_exception(e)
            raise
        finally:
            await self.end_span(span)

    @contextmanager
    def span_sync(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Dict[str, Any] = None
    ):
        """Sync context manager for spans."""
        span = self.start_span(name, kind, attributes)
        try:
            yield span
            if span.status == SpanStatus.UNSET:
                span.set_status(SpanStatus.OK)
        except Exception as e:
            span.record_exception(e)
            raise
        finally:
            span.end()
            # Note: processors won't be notified in sync mode
            self._pop_span()


# =============================================================================
# TRACING MANAGER
# =============================================================================

class TracingManager:
    """
    Master tracing manager for BAEL.

    Provides comprehensive distributed tracing.
    """

    def __init__(
        self,
        service_name: str,
        sampler: Sampler = None
    ):
        self.service_name = service_name
        self.sampler = sampler or AlwaysOnSampler()

        # Exporters and processors
        self.memory_exporter = MemoryExporter()
        self.processors: List[SpanProcessor] = []

        # Create tracer
        self.tracer = Tracer(
            name=service_name,
            sampler=self.sampler,
            processors=self.processors
        )

        # Statistics
        self.spans_created = 0
        self.spans_exported = 0
        self.errors_recorded = 0

    def add_exporter(self, exporter: SpanExporter) -> None:
        """Add span exporter."""
        processor = SimpleSpanProcessor(exporter)
        self.processors.append(processor)
        self.tracer.processors.append(processor)

    def add_memory_exporter(self) -> None:
        """Add memory exporter for querying."""
        processor = SimpleSpanProcessor(self.memory_exporter)
        self.processors.append(processor)
        self.tracer.processors.append(processor)

    def add_console_exporter(self, pretty: bool = True) -> None:
        """Add console exporter."""
        self.add_exporter(ConsoleExporter(pretty))

    # Span creation
    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Dict[str, Any] = None
    ) -> Span:
        """Start a new span."""
        self.spans_created += 1
        return self.tracer.start_span(name, kind, attributes)

    @asynccontextmanager
    async def span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Dict[str, Any] = None
    ):
        """Create span as async context manager."""
        async with self.tracer.span(name, kind, attributes) as span:
            yield span

    @property
    def current_span(self) -> Optional[Span]:
        """Get current active span."""
        return self.tracer.current_span

    # Context propagation
    def inject(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Inject trace context into headers."""
        span = self.current_span
        if span:
            context = span.get_context()
            headers['traceparent'] = context.to_header()

            if context.trace_state:
                headers['tracestate'] = ','.join(
                    f'{k}={v}' for k, v in context.trace_state.items()
                )

            if span.baggage:
                for key, value in span.baggage.items():
                    headers[f'baggage-{key}'] = value

        return headers

    def extract(self, headers: Dict[str, str]) -> Optional[TraceContext]:
        """Extract trace context from headers."""
        traceparent = headers.get('traceparent')

        if traceparent:
            context = TraceContext.from_header(traceparent)

            if context:
                # Parse tracestate
                tracestate = headers.get('tracestate', '')
                if tracestate:
                    for part in tracestate.split(','):
                        if '=' in part:
                            k, v = part.split('=', 1)
                            context.trace_state[k.strip()] = v.strip()

            return context

        return None

    # Trace queries
    async def get_trace(self, trace_id: str) -> Optional[Trace]:
        """Get complete trace by ID."""
        return await self.memory_exporter.get_trace(trace_id)

    async def get_recent_spans(self, limit: int = 100) -> List[Span]:
        """Get recent spans."""
        spans = await self.memory_exporter.get_spans()
        return list(spans)[-limit:]

    async def get_spans_by_name(self, name: str) -> List[Span]:
        """Get spans by operation name."""
        spans = await self.memory_exporter.get_spans()
        return [s for s in spans if s.name == name]

    # Analysis
    async def get_trace_summary(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Get trace summary."""
        trace = await self.get_trace(trace_id)
        if not trace:
            return None

        return {
            "trace_id": trace.trace_id,
            "span_count": len(trace.spans),
            "duration_ms": trace.duration_ms,
            "root_span": trace.root_span.name if trace.root_span else None,
            "has_errors": any(s.status == SpanStatus.ERROR for s in trace.spans),
            "services": list(set(
                s.attributes.get("service.name", "unknown")
                for s in trace.spans
            ))
        }

    async def get_service_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get per-service statistics."""
        spans = await self.memory_exporter.get_spans()

        stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "count": 0,
            "errors": 0,
            "total_duration": 0
        })

        for span in spans:
            service = span.attributes.get("service.name", self.service_name)
            stats[service]["count"] += 1
            stats[service]["total_duration"] += span.duration_ms

            if span.status == SpanStatus.ERROR:
                stats[service]["errors"] += 1

        # Calculate averages
        for service, data in stats.items():
            if data["count"] > 0:
                data["avg_duration_ms"] = data["total_duration"] / data["count"]
                data["error_rate"] = data["errors"] / data["count"]

        return dict(stats)

    # Decorators
    def trace(
        self,
        name: str = None,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Dict[str, Any] = None
    ) -> Callable:
        """Decorator to trace a function."""
        def decorator(func: Callable) -> Callable:
            span_name = name or func.__name__

            if asyncio.iscoroutinefunction(func):
                @functools.wraps(func)
                async def async_wrapper(*args, **kwargs):
                    async with self.span(span_name, kind, attributes) as span:
                        try:
                            return await func(*args, **kwargs)
                        except Exception as e:
                            span.record_exception(e)
                            raise
                return async_wrapper
            else:
                @functools.wraps(func)
                def sync_wrapper(*args, **kwargs):
                    with self.tracer.span_sync(span_name, kind, attributes) as span:
                        try:
                            return func(*args, **kwargs)
                        except Exception as e:
                            span.record_exception(e)
                            raise
                return sync_wrapper

        return decorator

    # Lifecycle
    async def shutdown(self) -> None:
        """Shutdown tracing."""
        for processor in self.processors:
            await processor.shutdown()

    # Statistics
    def get_statistics(self) -> Dict[str, Any]:
        """Get tracing statistics."""
        return {
            "service_name": self.service_name,
            "spans_created": self.spans_created,
            "processor_count": len(self.processors),
            "memory_spans": len(self.memory_exporter.spans)
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Distributed Tracing System."""
    print("=" * 70)
    print("BAEL - DISTRIBUTED TRACING SYSTEM DEMO")
    print("Comprehensive Request Tracing")
    print("=" * 70)
    print()

    manager = TracingManager(service_name="bael-demo")
    manager.add_memory_exporter()

    # 1. Basic Span Creation
    print("1. BASIC SPAN CREATION:")
    print("-" * 40)

    async with manager.span("demo-operation") as span:
        span.set_attribute("user.id", "123")
        span.set_attribute("http.method", "GET")
        await asyncio.sleep(0.1)
        span.add_event("processing_started")
        await asyncio.sleep(0.1)
        span.add_event("processing_complete")

    print(f"   Created span: demo-operation")
    print(f"   Trace ID: {span.trace_id[:8]}...")
    print(f"   Duration: {span.duration_ms:.2f}ms")
    print()

    # 2. Nested Spans
    print("2. NESTED SPANS:")
    print("-" * 40)

    async with manager.span("parent-operation") as parent:
        parent.set_attribute("level", "parent")

        async with manager.span("child-operation-1") as child1:
            child1.set_attribute("level", "child")
            await asyncio.sleep(0.05)

        async with manager.span("child-operation-2") as child2:
            child2.set_attribute("level", "child")
            await asyncio.sleep(0.05)

            async with manager.span("grandchild") as grandchild:
                grandchild.set_attribute("level", "grandchild")
                await asyncio.sleep(0.02)

    print(f"   Parent: {parent.span_id}")
    print(f"   Child 1: {child1.span_id} (parent: {child1.parent_span_id})")
    print(f"   Child 2: {child2.span_id} (parent: {child2.parent_span_id})")
    print(f"   Grandchild: {grandchild.span_id} (parent: {grandchild.parent_span_id})")
    print()

    # 3. Error Recording
    print("3. ERROR RECORDING:")
    print("-" * 40)

    try:
        async with manager.span("failing-operation") as span:
            span.set_attribute("attempt", 1)
            raise ValueError("Simulated error")
    except ValueError:
        pass

    print(f"   Status: {span.status.value}")
    print(f"   Status message: {span.status_message}")
    print(f"   Events: {len(span.events)}")
    if span.events:
        print(f"   Exception type: {span.events[0].attributes.get('exception.type')}")
    print()

    # 4. Span Events
    print("4. SPAN EVENTS:")
    print("-" * 40)

    async with manager.span("event-demo") as span:
        span.add_event("cache_lookup", {"cache_hit": False})
        await asyncio.sleep(0.05)
        span.add_event("db_query", {"table": "users", "rows": 10})
        await asyncio.sleep(0.05)
        span.add_event("response_sent", {"status": 200})

    print(f"   Events recorded: {len(span.events)}")
    for event in span.events:
        print(f"      - {event.name}: {event.attributes}")
    print()

    # 5. Context Propagation
    print("5. CONTEXT PROPAGATION:")
    print("-" * 40)

    async with manager.span("upstream-service") as upstream:
        upstream.baggage["request_id"] = "req-123"
        upstream.baggage["tenant_id"] = "tenant-456"

        # Simulate HTTP call with context injection
        headers = {}
        manager.inject(headers)

        print(f"   Injected headers:")
        for key, value in headers.items():
            print(f"      {key}: {value[:50]}...")
    print()

    # 6. Sampling
    print("6. SAMPLING:")
    print("-" * 40)

    # Create manager with ratio sampler
    ratio_manager = TracingManager(
        service_name="sampled-service",
        sampler=TraceIdRatioSampler(ratio=0.5)
    )

    sampled_count = 0
    total = 100

    for _ in range(total):
        span = ratio_manager.start_span("sampled-operation")
        if span.is_sampled:
            sampled_count += 1
        span.end()

    print(f"   Ratio: 50%")
    print(f"   Sampled: {sampled_count}/{total} ({sampled_count/total:.0%})")
    print()

    # 7. Trace Decorator
    print("7. TRACE DECORATOR:")
    print("-" * 40)

    @manager.trace("decorated-function")
    async def process_data(data: Dict) -> Dict:
        await asyncio.sleep(0.05)
        return {"processed": True, **data}

    result = await process_data({"input": "test"})
    print(f"   Function result: {result}")

    recent = await manager.get_recent_spans(1)
    if recent:
        print(f"   Span created: {recent[-1].name}")
        print(f"   Duration: {recent[-1].duration_ms:.2f}ms")
    print()

    # 8. Trace Query
    print("8. TRACE QUERY:")
    print("-" * 40)

    trace = await manager.get_trace(parent.trace_id)
    if trace:
        print(f"   Trace ID: {trace.trace_id[:8]}...")
        print(f"   Span count: {len(trace.spans)}")
        print(f"   Total duration: {trace.duration_ms:.2f}ms")
        print(f"   Root span: {trace.root_span.name if trace.root_span else 'None'}")
    print()

    # 9. Service Statistics
    print("9. SERVICE STATISTICS:")
    print("-" * 40)

    stats = await manager.get_service_stats()
    for service, data in stats.items():
        print(f"   {service}:")
        print(f"      Span count: {data['count']}")
        print(f"      Avg duration: {data.get('avg_duration_ms', 0):.2f}ms")
        print(f"      Error rate: {data.get('error_rate', 0):.1%}")
    print()

    # 10. Trace Summary
    print("10. TRACE SUMMARY:")
    print("-" * 40)

    summary = await manager.get_trace_summary(parent.trace_id)
    if summary:
        for key, value in summary.items():
            print(f"    {key}: {value}")
    print()

    # Cleanup
    await manager.shutdown()

    print("=" * 70)
    print("DEMO COMPLETE - Distributed Tracing Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
