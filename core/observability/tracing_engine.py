"""
BAEL Distributed Tracing Engine
=================================

OpenTelemetry-compatible distributed tracing.
Tracks requests across service boundaries.

Features:
- Span management
- Context propagation
- Trace correlation
- Sampling strategies
- Multiple exporters
"""

import hashlib
import logging
import random
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


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


@dataclass
class SpanContext:
    """Context for span propagation."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None

    # Flags
    sampled: bool = True

    # Baggage (propagated context)
    baggage: Dict[str, str] = field(default_factory=dict)

    def to_header(self) -> str:
        """Convert to W3C trace context header."""
        flags = "01" if self.sampled else "00"
        return f"00-{self.trace_id}-{self.span_id}-{flags}"

    @classmethod
    def from_header(cls, header: str) -> Optional["SpanContext"]:
        """Parse W3C trace context header."""
        try:
            parts = header.split("-")
            if len(parts) >= 4:
                return cls(
                    trace_id=parts[1],
                    span_id=parts[2],
                    sampled=parts[3] == "01",
                )
        except Exception:
            pass
        return None


@dataclass
class SpanEvent:
    """An event within a span."""
    name: str
    timestamp: datetime
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SpanLink:
    """Link to another span."""
    context: SpanContext
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Span:
    """A single span in a trace."""
    name: str
    context: SpanContext
    kind: SpanKind = SpanKind.INTERNAL

    # Timing
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

    # Status
    status: SpanStatus = SpanStatus.UNSET
    status_message: str = ""

    # Attributes
    attributes: Dict[str, Any] = field(default_factory=dict)

    # Events and links
    events: List[SpanEvent] = field(default_factory=list)
    links: List[SpanLink] = field(default_factory=list)

    # Resource
    service_name: str = "bael"

    def set_attribute(self, key: str, value: Any) -> None:
        """Set an attribute."""
        self.attributes[key] = value

    def set_status(self, status: SpanStatus, message: str = "") -> None:
        """Set span status."""
        self.status = status
        self.status_message = message

    def add_event(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add an event."""
        event = SpanEvent(
            name=name,
            timestamp=datetime.now(),
            attributes=attributes or {},
        )
        self.events.append(event)

    def record_exception(self, exception: Exception) -> None:
        """Record an exception."""
        self.add_event(
            "exception",
            {
                "exception.type": type(exception).__name__,
                "exception.message": str(exception),
            },
        )
        self.set_status(SpanStatus.ERROR, str(exception))

    def end(self) -> None:
        """End the span."""
        self.end_time = datetime.now()
        if self.status == SpanStatus.UNSET:
            self.status = SpanStatus.OK

    @property
    def duration_ms(self) -> float:
        """Get span duration in milliseconds."""
        if not self.end_time:
            return 0.0
        delta = self.end_time - self.start_time
        return delta.total_seconds() * 1000

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "trace_id": self.context.trace_id,
            "span_id": self.context.span_id,
            "parent_span_id": self.context.parent_span_id,
            "kind": self.kind.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "status": self.status.value,
            "attributes": self.attributes,
            "events": [
                {"name": e.name, "timestamp": e.timestamp.isoformat()}
                for e in self.events
            ],
            "service": self.service_name,
        }


class TraceExporter:
    """Base class for trace exporters."""

    def export(self, spans: List[Span]) -> bool:
        """Export spans. Returns success."""
        raise NotImplementedError

    def shutdown(self) -> None:
        """Shutdown exporter."""
        pass


class ConsoleExporter(TraceExporter):
    """Export spans to console."""

    def export(self, spans: List[Span]) -> bool:
        for span in spans:
            print(f"[TRACE] {span.name}: {span.duration_ms:.2f}ms ({span.status.value})")
        return True


class InMemoryExporter(TraceExporter):
    """Export spans to memory (for testing)."""

    def __init__(self):
        self.spans: List[Span] = []

    def export(self, spans: List[Span]) -> bool:
        self.spans.extend(spans)
        return True

    def clear(self) -> None:
        self.spans.clear()


class Tracer:
    """
    Tracer for creating spans.
    """

    def __init__(
        self,
        name: str = "bael-tracer",
        service_name: str = "bael",
        sample_rate: float = 1.0,
    ):
        self.name = name
        self.service_name = service_name
        self.sample_rate = sample_rate

        # Context storage (thread-local)
        self._context = threading.local()

        # Pending spans
        self._spans: List[Span] = []

        # Exporters
        self._exporters: List[TraceExporter] = []

    def add_exporter(self, exporter: TraceExporter) -> None:
        """Add a trace exporter."""
        self._exporters.append(exporter)

    def _generate_id(self, length: int = 32) -> str:
        """Generate random ID."""
        return hashlib.md5(
            f"{random.random()}:{time.time()}".encode()
        ).hexdigest()[:length]

    def _get_current_span(self) -> Optional[Span]:
        """Get current active span."""
        return getattr(self._context, 'current_span', None)

    def _set_current_span(self, span: Optional[Span]) -> None:
        """Set current active span."""
        self._context.current_span = span

    def _should_sample(self) -> bool:
        """Determine if trace should be sampled."""
        return random.random() < self.sample_rate

    @contextmanager
    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
        parent_context: Optional[SpanContext] = None,
    ) -> Generator[Span, None, None]:
        """
        Start a new span.

        Args:
            name: Span name
            kind: Span kind
            attributes: Initial attributes
            parent_context: Optional parent context

        Yields:
            The created span
        """
        # Determine parent
        parent_span = self._get_current_span()

        if parent_context:
            trace_id = parent_context.trace_id
            parent_span_id = parent_context.span_id
            sampled = parent_context.sampled
        elif parent_span:
            trace_id = parent_span.context.trace_id
            parent_span_id = parent_span.context.span_id
            sampled = parent_span.context.sampled
        else:
            trace_id = self._generate_id(32)
            parent_span_id = None
            sampled = self._should_sample()

        # Create context
        context = SpanContext(
            trace_id=trace_id,
            span_id=self._generate_id(16),
            parent_span_id=parent_span_id,
            sampled=sampled,
        )

        # Create span
        span = Span(
            name=name,
            context=context,
            kind=kind,
            service_name=self.service_name,
        )

        if attributes:
            span.attributes.update(attributes)

        # Set as current
        previous_span = self._get_current_span()
        self._set_current_span(span)

        try:
            yield span
        except Exception as e:
            span.record_exception(e)
            raise
        finally:
            span.end()
            self._set_current_span(previous_span)

            if sampled:
                self._spans.append(span)
                self._maybe_export()

    def _maybe_export(self, force: bool = False) -> None:
        """Export spans if threshold reached."""
        if len(self._spans) >= 10 or force:
            spans_to_export = list(self._spans)
            self._spans.clear()

            for exporter in self._exporters:
                try:
                    exporter.export(spans_to_export)
                except Exception as e:
                    logger.warning(f"Export failed: {e}")

    def flush(self) -> None:
        """Flush all pending spans."""
        self._maybe_export(force=True)


class TracingEngine:
    """
    Main tracing engine for BAEL.

    Manages distributed tracing.
    """

    def __init__(
        self,
        service_name: str = "bael",
        sample_rate: float = 1.0,
    ):
        self.service_name = service_name
        self.sample_rate = sample_rate

        # Create tracer
        self.tracer = Tracer(
            name="bael-tracer",
            service_name=service_name,
            sample_rate=sample_rate,
        )

        # In-memory exporter for demo
        self._memory_exporter = InMemoryExporter()
        self.tracer.add_exporter(self._memory_exporter)

        # Stats
        self.stats = {
            "traces_created": 0,
            "spans_created": 0,
        }

    @contextmanager
    def trace(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        **attributes,
    ) -> Generator[Span, None, None]:
        """
        Create a trace/span.

        Args:
            name: Operation name
            kind: Span kind
            **attributes: Span attributes

        Yields:
            The span
        """
        with self.tracer.start_span(name, kind, attributes) as span:
            self.stats["spans_created"] += 1
            yield span

    def trace_function(
        self,
        name: Optional[str] = None,
        kind: SpanKind = SpanKind.INTERNAL,
    ) -> Callable:
        """
        Decorator to trace a function.

        Args:
            name: Optional span name (defaults to function name)
            kind: Span kind

        Returns:
            Decorator
        """
        def decorator(func: Callable) -> Callable:
            span_name = name or func.__name__

            def wrapper(*args, **kwargs):
                with self.trace(span_name, kind) as span:
                    span.set_attribute("function.args_count", len(args))
                    try:
                        result = func(*args, **kwargs)
                        return result
                    except Exception as e:
                        span.record_exception(e)
                        raise

            return wrapper
        return decorator

    def get_current_context(self) -> Optional[SpanContext]:
        """Get current span context for propagation."""
        span = self.tracer._get_current_span()
        return span.context if span else None

    def inject_context(self, headers: Dict[str, str]) -> None:
        """Inject trace context into headers."""
        context = self.get_current_context()
        if context:
            headers["traceparent"] = context.to_header()
            if context.baggage:
                headers["baggage"] = ",".join(
                    f"{k}={v}" for k, v in context.baggage.items()
                )

    def extract_context(self, headers: Dict[str, str]) -> Optional[SpanContext]:
        """Extract trace context from headers."""
        traceparent = headers.get("traceparent")
        if traceparent:
            return SpanContext.from_header(traceparent)
        return None

    def get_traces(self) -> List[Dict[str, Any]]:
        """Get recent traces."""
        traces: Dict[str, List[Span]] = {}

        for span in self._memory_exporter.spans:
            trace_id = span.context.trace_id
            if trace_id not in traces:
                traces[trace_id] = []
            traces[trace_id].append(span)

        return [
            {
                "trace_id": trace_id,
                "spans": [s.to_dict() for s in spans],
                "duration_ms": max(s.duration_ms for s in spans) if spans else 0,
            }
            for trace_id, spans in traces.items()
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            **self.stats,
            "sample_rate": self.sample_rate,
            "pending_spans": len(self.tracer._spans),
            "exported_spans": len(self._memory_exporter.spans),
        }


def demo():
    """Demonstrate tracing engine."""
    print("=" * 60)
    print("BAEL Distributed Tracing Demo")
    print("=" * 60)

    engine = TracingEngine(service_name="demo-service")
    engine.tracer.add_exporter(ConsoleExporter())

    # Basic tracing
    print("\nBasic tracing:")
    with engine.trace("process_request", http_method="GET", path="/api/data") as span:
        time.sleep(0.05)  # Simulate work

        with engine.trace("database_query", query="SELECT *") as db_span:
            time.sleep(0.02)

        with engine.trace("format_response") as fmt_span:
            time.sleep(0.01)

    # Function decorator
    print("\nDecorated function:")

    @engine.trace_function("calculate")
    def calculate(x: int, y: int) -> int:
        time.sleep(0.01)
        return x + y

    result = calculate(5, 3)
    print(f"  Result: {result}")

    # Context propagation
    print("\nContext propagation:")
    headers = {}
    with engine.trace("outgoing_request") as span:
        engine.inject_context(headers)
        print(f"  Injected headers: {headers}")

    extracted = engine.extract_context(headers)
    if extracted:
        print(f"  Extracted trace_id: {extracted.trace_id[:16]}...")

    # View traces
    print("\nRecent traces:")
    for trace in engine.get_traces():
        print(f"  Trace {trace['trace_id'][:16]}...: "
              f"{len(trace['spans'])} spans, "
              f"{trace['duration_ms']:.2f}ms")

    print(f"\nStats: {engine.get_stats()}")


if __name__ == "__main__":
    demo()
