#!/usr/bin/env python3
"""
BAEL - Stream Manager
Advanced stream processing for AI agent operations.

Features:
- Data streaming
- Window operations
- Stream aggregation
- Watermarks
- Event time processing
- Late data handling
- Stream joins
- Windowed computations
- Tumbling/Sliding/Session windows
- Stream partitioning
"""

import asyncio
import copy
import heapq
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, AsyncIterator, Awaitable, Callable, Dict, Generic,
                    Iterator, List, Optional, Set, Tuple, TypeVar, Union)

T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')


# =============================================================================
# ENUMS
# =============================================================================

class WindowType(Enum):
    """Window types."""
    TUMBLING = "tumbling"
    SLIDING = "sliding"
    SESSION = "session"
    GLOBAL = "global"


class TriggerType(Enum):
    """Trigger types."""
    PROCESSING_TIME = "processing_time"
    EVENT_TIME = "event_time"
    COUNT = "count"
    CONTINUOUS = "continuous"


class StreamState(Enum):
    """Stream states."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class WatermarkStrategy(Enum):
    """Watermark strategies."""
    STRICT = "strict"
    BOUNDED = "bounded"
    PERIODIC = "periodic"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class StreamConfig:
    """Stream configuration."""
    buffer_size: int = 1000
    watermark_delay_ms: int = 1000
    late_data_allowed_ms: int = 5000
    checkpoint_interval_ms: int = 10000
    parallelism: int = 1


@dataclass
class StreamEvent(Generic[T]):
    """Stream event."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    key: Optional[str] = None
    value: Optional[T] = None
    event_time: datetime = field(default_factory=datetime.utcnow)
    processing_time: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WindowSpec:
    """Window specification."""
    window_type: WindowType = WindowType.TUMBLING
    size_ms: int = 10000
    slide_ms: int = 5000  # For sliding windows
    gap_ms: int = 30000  # For session windows
    trigger_type: TriggerType = TriggerType.PROCESSING_TIME


@dataclass
class WindowResult(Generic[T]):
    """Window computation result."""
    window_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    window_start: datetime = field(default_factory=datetime.utcnow)
    window_end: datetime = field(default_factory=datetime.utcnow)
    key: Optional[str] = None
    result: Optional[T] = None
    event_count: int = 0
    late_count: int = 0


@dataclass
class Watermark:
    """Stream watermark."""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source_id: str = ""


@dataclass
class StreamStats:
    """Stream statistics."""
    events_processed: int = 0
    events_dropped: int = 0
    late_events: int = 0
    windows_emitted: int = 0
    watermarks_advanced: int = 0
    processing_time_ms: float = 0.0


# =============================================================================
# WINDOW IMPLEMENTATION
# =============================================================================

class Window(Generic[T]):
    """Window for stream processing."""

    def __init__(
        self,
        window_id: str,
        start: datetime,
        end: datetime,
        key: Optional[str] = None
    ):
        self.window_id = window_id
        self.start = start
        self.end = end
        self.key = key
        self._events: List[StreamEvent[T]] = []
        self._late_events: List[StreamEvent[T]] = []

    def add(self, event: StreamEvent[T]) -> None:
        """Add event to window."""
        self._events.append(event)

    def add_late(self, event: StreamEvent[T]) -> None:
        """Add late event."""
        self._late_events.append(event)

    def events(self) -> List[StreamEvent[T]]:
        """Get all events."""
        return list(self._events)

    def count(self) -> int:
        """Get event count."""
        return len(self._events)

    def is_expired(self, watermark: datetime) -> bool:
        """Check if window is expired."""
        return watermark > self.end


class WindowAssigner(ABC, Generic[T]):
    """Assigns events to windows."""

    @abstractmethod
    def assign(
        self,
        event: StreamEvent[T],
        current_watermark: datetime
    ) -> List[Tuple[datetime, datetime]]:
        """Assign event to window(s). Returns list of (start, end) tuples."""
        pass


class TumblingWindowAssigner(WindowAssigner[T]):
    """Tumbling window assigner."""

    def __init__(self, size_ms: int):
        self.size_ms = size_ms

    def assign(
        self,
        event: StreamEvent[T],
        current_watermark: datetime
    ) -> List[Tuple[datetime, datetime]]:
        event_time = event.event_time

        # Calculate window
        epoch = datetime(1970, 1, 1)
        event_ms = int((event_time - epoch).total_seconds() * 1000)

        window_start_ms = (event_ms // self.size_ms) * self.size_ms
        window_start = epoch + timedelta(milliseconds=window_start_ms)
        window_end = window_start + timedelta(milliseconds=self.size_ms)

        return [(window_start, window_end)]


class SlidingWindowAssigner(WindowAssigner[T]):
    """Sliding window assigner."""

    def __init__(self, size_ms: int, slide_ms: int):
        self.size_ms = size_ms
        self.slide_ms = slide_ms

    def assign(
        self,
        event: StreamEvent[T],
        current_watermark: datetime
    ) -> List[Tuple[datetime, datetime]]:
        event_time = event.event_time
        epoch = datetime(1970, 1, 1)
        event_ms = int((event_time - epoch).total_seconds() * 1000)

        windows = []

        # Find all windows this event belongs to
        last_start = (event_ms // self.slide_ms) * self.slide_ms
        first_start = last_start - self.size_ms + self.slide_ms

        for start_ms in range(first_start, last_start + 1, self.slide_ms):
            if start_ms + self.size_ms > event_ms:
                window_start = epoch + timedelta(milliseconds=start_ms)
                window_end = window_start + timedelta(milliseconds=self.size_ms)
                windows.append((window_start, window_end))

        return windows


class SessionWindowAssigner(WindowAssigner[T]):
    """Session window assigner."""

    def __init__(self, gap_ms: int):
        self.gap_ms = gap_ms

    def assign(
        self,
        event: StreamEvent[T],
        current_watermark: datetime
    ) -> List[Tuple[datetime, datetime]]:
        event_time = event.event_time
        gap = timedelta(milliseconds=self.gap_ms)

        return [(event_time, event_time + gap)]


# =============================================================================
# STREAM OPERATORS
# =============================================================================

class StreamOperator(ABC, Generic[T]):
    """Base stream operator."""

    @abstractmethod
    async def process(
        self,
        event: StreamEvent[T]
    ) -> Optional[StreamEvent[Any]]:
        """Process event."""
        pass


class MapOperator(StreamOperator[T]):
    """Map operator."""

    def __init__(self, func: Callable[[T], Any]):
        self._func = func

    async def process(
        self,
        event: StreamEvent[T]
    ) -> Optional[StreamEvent[Any]]:
        if event.value is None:
            return None

        result = self._func(event.value)

        return StreamEvent(
            key=event.key,
            value=result,
            event_time=event.event_time,
            metadata=event.metadata
        )


class FilterOperator(StreamOperator[T]):
    """Filter operator."""

    def __init__(self, predicate: Callable[[T], bool]):
        self._predicate = predicate

    async def process(
        self,
        event: StreamEvent[T]
    ) -> Optional[StreamEvent[T]]:
        if event.value is None:
            return None

        if self._predicate(event.value):
            return event
        return None


class FlatMapOperator(StreamOperator[T]):
    """FlatMap operator."""

    def __init__(self, func: Callable[[T], List[Any]]):
        self._func = func
        self._pending: deque = deque()

    async def process(
        self,
        event: StreamEvent[T]
    ) -> Optional[StreamEvent[Any]]:
        if event.value is None:
            return None

        results = self._func(event.value)

        for result in results[1:]:
            self._pending.append(StreamEvent(
                key=event.key,
                value=result,
                event_time=event.event_time,
                metadata=event.metadata
            ))

        if results:
            return StreamEvent(
                key=event.key,
                value=results[0],
                event_time=event.event_time,
                metadata=event.metadata
            )
        return None

    def has_pending(self) -> bool:
        return len(self._pending) > 0

    def get_pending(self) -> Optional[StreamEvent]:
        if self._pending:
            return self._pending.popleft()
        return None


class KeyByOperator(StreamOperator[T]):
    """KeyBy operator."""

    def __init__(self, key_selector: Callable[[T], str]):
        self._key_selector = key_selector

    async def process(
        self,
        event: StreamEvent[T]
    ) -> Optional[StreamEvent[T]]:
        if event.value is None:
            return None

        key = self._key_selector(event.value)

        return StreamEvent(
            key=key,
            value=event.value,
            event_time=event.event_time,
            metadata=event.metadata
        )


# =============================================================================
# STREAM
# =============================================================================

class Stream(Generic[T]):
    """Data stream."""

    def __init__(self, name: str = ""):
        self.stream_id = str(uuid.uuid4())
        self.name = name or f"stream_{self.stream_id[:8]}"

        self._operators: List[StreamOperator] = []
        self._windows: Dict[str, Window] = {}
        self._window_spec: Optional[WindowSpec] = None
        self._window_assigner: Optional[WindowAssigner] = None

        self._buffer: deque = deque()
        self._watermark = datetime.min
        self._state = StreamState.IDLE

        self._lock = threading.RLock()
        self._stats = StreamStats()

        self._sink: Optional[Callable[[StreamEvent], Awaitable[None]]] = None
        self._window_func: Optional[Callable[[Window], Any]] = None

    # -------------------------------------------------------------------------
    # OPERATORS
    # -------------------------------------------------------------------------

    def map(self, func: Callable[[T], Any]) -> 'Stream':
        """Add map operator."""
        self._operators.append(MapOperator(func))
        return self

    def filter(self, predicate: Callable[[T], bool]) -> 'Stream':
        """Add filter operator."""
        self._operators.append(FilterOperator(predicate))
        return self

    def flat_map(self, func: Callable[[T], List[Any]]) -> 'Stream':
        """Add flatmap operator."""
        self._operators.append(FlatMapOperator(func))
        return self

    def key_by(self, key_selector: Callable[[T], str]) -> 'Stream':
        """Add keyby operator."""
        self._operators.append(KeyByOperator(key_selector))
        return self

    # -------------------------------------------------------------------------
    # WINDOWING
    # -------------------------------------------------------------------------

    def window(self, spec: WindowSpec) -> 'Stream':
        """Set window specification."""
        self._window_spec = spec

        if spec.window_type == WindowType.TUMBLING:
            self._window_assigner = TumblingWindowAssigner(spec.size_ms)
        elif spec.window_type == WindowType.SLIDING:
            self._window_assigner = SlidingWindowAssigner(spec.size_ms, spec.slide_ms)
        elif spec.window_type == WindowType.SESSION:
            self._window_assigner = SessionWindowAssigner(spec.gap_ms)

        return self

    def tumbling_window(self, size_ms: int) -> 'Stream':
        """Set tumbling window."""
        return self.window(WindowSpec(
            window_type=WindowType.TUMBLING,
            size_ms=size_ms
        ))

    def sliding_window(
        self,
        size_ms: int,
        slide_ms: int
    ) -> 'Stream':
        """Set sliding window."""
        return self.window(WindowSpec(
            window_type=WindowType.SLIDING,
            size_ms=size_ms,
            slide_ms=slide_ms
        ))

    def session_window(self, gap_ms: int) -> 'Stream':
        """Set session window."""
        return self.window(WindowSpec(
            window_type=WindowType.SESSION,
            gap_ms=gap_ms
        ))

    def aggregate(
        self,
        func: Callable[[Window], Any]
    ) -> 'Stream':
        """Set window aggregation function."""
        self._window_func = func
        return self

    # -------------------------------------------------------------------------
    # SINK
    # -------------------------------------------------------------------------

    def sink(
        self,
        handler: Callable[[StreamEvent], Awaitable[None]]
    ) -> 'Stream':
        """Set sink handler."""
        self._sink = handler
        return self

    # -------------------------------------------------------------------------
    # PROCESSING
    # -------------------------------------------------------------------------

    async def emit(self, event: StreamEvent[T]) -> None:
        """Emit event into stream."""
        start = time.time()

        with self._lock:
            self._stats.events_processed += 1

        # Apply operators
        current: Optional[StreamEvent] = event

        for op in self._operators:
            if current is None:
                break
            current = await op.process(current)

        if current is None:
            return

        # Window processing
        if self._window_assigner:
            await self._process_windowed(current)
        elif self._sink:
            await self._sink(current)

        elapsed = (time.time() - start) * 1000
        with self._lock:
            self._stats.processing_time_ms += elapsed

    async def _process_windowed(
        self,
        event: StreamEvent
    ) -> None:
        """Process event with windowing."""
        windows = self._window_assigner.assign(event, self._watermark)

        for start, end in windows:
            window_key = f"{event.key}_{start.isoformat()}"

            with self._lock:
                if window_key not in self._windows:
                    self._windows[window_key] = Window(
                        window_id=window_key,
                        start=start,
                        end=end,
                        key=event.key
                    )

                window = self._windows[window_key]

                # Check if late
                if event.event_time < self._watermark:
                    window.add_late(event)
                    self._stats.late_events += 1
                else:
                    window.add(event)

    def advance_watermark(self, timestamp: datetime) -> List[WindowResult]:
        """Advance watermark and trigger windows."""
        results = []

        with self._lock:
            if timestamp <= self._watermark:
                return results

            self._watermark = timestamp
            self._stats.watermarks_advanced += 1

            # Check expired windows
            expired = []
            for key, window in self._windows.items():
                if window.is_expired(timestamp):
                    expired.append(key)

                    # Compute window result
                    if self._window_func:
                        result = self._window_func(window)
                    else:
                        result = window.events()

                    results.append(WindowResult(
                        window_id=window.window_id,
                        window_start=window.start,
                        window_end=window.end,
                        key=window.key,
                        result=result,
                        event_count=window.count(),
                        late_count=len(window._late_events)
                    ))

                    self._stats.windows_emitted += 1

            # Clean up expired
            for key in expired:
                del self._windows[key]

        return results

    # -------------------------------------------------------------------------
    # CONTROL
    # -------------------------------------------------------------------------

    def start(self) -> None:
        """Start stream."""
        with self._lock:
            self._state = StreamState.RUNNING

    def pause(self) -> None:
        """Pause stream."""
        with self._lock:
            self._state = StreamState.PAUSED

    def stop(self) -> None:
        """Stop stream."""
        with self._lock:
            self._state = StreamState.STOPPED

    def state(self) -> StreamState:
        """Get stream state."""
        with self._lock:
            return self._state

    # -------------------------------------------------------------------------
    # STATS
    # -------------------------------------------------------------------------

    def stats(self) -> StreamStats:
        """Get stream stats."""
        with self._lock:
            return copy.copy(self._stats)

    def window_count(self) -> int:
        """Get active window count."""
        with self._lock:
            return len(self._windows)


# =============================================================================
# STREAM MANAGER
# =============================================================================

class StreamManager:
    """
    Stream Manager for BAEL.

    Advanced stream processing.
    """

    def __init__(self):
        self._streams: Dict[str, Stream] = {}
        self._lock = threading.RLock()

    def create_stream(
        self,
        name: str = ""
    ) -> Stream:
        """Create new stream."""
        stream = Stream(name)

        with self._lock:
            self._streams[stream.stream_id] = stream

        return stream

    def get_stream(self, stream_id: str) -> Optional[Stream]:
        """Get stream by ID."""
        with self._lock:
            return self._streams.get(stream_id)

    def delete_stream(self, stream_id: str) -> bool:
        """Delete stream."""
        with self._lock:
            if stream_id in self._streams:
                del self._streams[stream_id]
                return True
            return False

    def list_streams(self) -> List[Stream]:
        """List all streams."""
        with self._lock:
            return list(self._streams.values())

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def create_event(
        self,
        value: Any,
        key: Optional[str] = None,
        event_time: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> StreamEvent:
        """Create stream event."""
        return StreamEvent(
            key=key,
            value=value,
            event_time=event_time or datetime.utcnow(),
            metadata=metadata or {}
        )

    def create_tumbling_window(
        self,
        size_ms: int
    ) -> WindowSpec:
        """Create tumbling window spec."""
        return WindowSpec(
            window_type=WindowType.TUMBLING,
            size_ms=size_ms
        )

    def create_sliding_window(
        self,
        size_ms: int,
        slide_ms: int
    ) -> WindowSpec:
        """Create sliding window spec."""
        return WindowSpec(
            window_type=WindowType.SLIDING,
            size_ms=size_ms,
            slide_ms=slide_ms
        )

    # -------------------------------------------------------------------------
    # BATCH HELPERS
    # -------------------------------------------------------------------------

    async def emit_batch(
        self,
        stream: Stream,
        events: List[StreamEvent]
    ) -> None:
        """Emit batch of events."""
        for event in events:
            await stream.emit(event)

    # -------------------------------------------------------------------------
    # STATS
    # -------------------------------------------------------------------------

    def get_all_stats(self) -> Dict[str, StreamStats]:
        """Get stats for all streams."""
        with self._lock:
            return {
                sid: s.stats()
                for sid, s in self._streams.items()
            }

    def stream_count(self) -> int:
        """Get stream count."""
        with self._lock:
            return len(self._streams)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Stream Manager."""
    print("=" * 70)
    print("BAEL - STREAM MANAGER DEMO")
    print("Advanced Stream Processing for AI Agents")
    print("=" * 70)
    print()

    manager = StreamManager()

    # 1. Create Stream
    print("1. CREATE STREAM:")
    print("-" * 40)

    stream = manager.create_stream("data_stream")

    print(f"   Stream: {stream.name}")
    print(f"   ID: {stream.stream_id[:8]}...")
    print()

    # 2. Add Operators
    print("2. ADD OPERATORS:")
    print("-" * 40)

    processed = []

    stream.map(lambda x: x * 2).filter(lambda x: x > 5)

    async def collect(event):
        processed.append(event.value)

    stream.sink(collect)
    stream.start()

    print(f"   Added: map(x*2), filter(x>5)")
    print()

    # 3. Emit Events
    print("3. EMIT EVENTS:")
    print("-" * 40)

    for i in range(10):
        event = manager.create_event(value=i)
        await stream.emit(event)

    print(f"   Emitted: 10 events")
    print(f"   Processed (>5): {processed}")
    print()

    # 4. Tumbling Window
    print("4. TUMBLING WINDOW:")
    print("-" * 40)

    windowed = manager.create_stream("windowed")
    windowed.tumbling_window(1000)

    def count_window(w):
        return w.count()

    windowed.aggregate(count_window)
    windowed.start()

    # Emit events
    now = datetime.utcnow()
    for i in range(5):
        event = manager.create_event(
            value=i,
            event_time=now + timedelta(milliseconds=i * 100)
        )
        await windowed.emit(event)

    print(f"   Active windows: {windowed.window_count()}")

    # Advance watermark
    results = windowed.advance_watermark(now + timedelta(seconds=2))
    print(f"   Window results: {len(results)}")
    for r in results:
        print(f"   - Count: {r.result}")
    print()

    # 5. KeyBy Operation
    print("5. KEYBY OPERATION:")
    print("-" * 40)

    keyed = manager.create_stream("keyed")
    keyed.key_by(lambda x: x["category"])

    keyed_results = []

    async def collect_keyed(event):
        keyed_results.append((event.key, event.value))

    keyed.sink(collect_keyed)
    keyed.start()

    for item in [
        {"category": "A", "value": 1},
        {"category": "B", "value": 2},
        {"category": "A", "value": 3}
    ]:
        event = manager.create_event(value=item)
        await keyed.emit(event)

    print(f"   Keyed results:")
    for key, val in keyed_results:
        print(f"   - Key: {key}, Value: {val}")
    print()

    # 6. Sliding Window
    print("6. SLIDING WINDOW:")
    print("-" * 40)

    sliding = manager.create_stream("sliding")
    sliding.sliding_window(size_ms=2000, slide_ms=1000)
    sliding.aggregate(lambda w: [e.value for e in w.events()])
    sliding.start()

    now = datetime.utcnow()
    for i in range(4):
        event = manager.create_event(
            value=f"item_{i}",
            event_time=now + timedelta(milliseconds=i * 600)
        )
        await sliding.emit(event)

    print(f"   Active windows: {sliding.window_count()}")
    print()

    # 7. Stream Stats
    print("7. STREAM STATS:")
    print("-" * 40)

    stats = stream.stats()

    print(f"   Events processed: {stats.events_processed}")
    print(f"   Windows emitted: {stats.windows_emitted}")
    print(f"   Processing time: {stats.processing_time_ms:.2f} ms")
    print()

    # 8. FlatMap
    print("8. FLATMAP OPERATION:")
    print("-" * 40)

    flat = manager.create_stream("flat")
    flat.flat_map(lambda x: x.split())

    flat_results = []

    async def collect_flat(event):
        flat_results.append(event.value)

    flat.sink(collect_flat)
    flat.start()

    event = manager.create_event(value="hello world test")
    await flat.emit(event)

    print(f"   Input: 'hello world test'")
    print(f"   Output: {flat_results}")
    print()

    # 9. Create Event
    print("9. CREATE EVENT:")
    print("-" * 40)

    event = manager.create_event(
        value={"data": 123},
        key="partition_1",
        metadata={"source": "demo"}
    )

    print(f"   Event ID: {event.event_id[:8]}...")
    print(f"   Key: {event.key}")
    print(f"   Value: {event.value}")
    print()

    # 10. Watermark
    print("10. WATERMARK:")
    print("-" * 40)

    wm_stream = manager.create_stream("watermarked")
    wm_stream.tumbling_window(1000)
    wm_stream.aggregate(lambda w: sum(e.value for e in w.events()))
    wm_stream.start()

    now = datetime.utcnow()

    # Add events
    for i in range(3):
        event = manager.create_event(
            value=i + 1,
            event_time=now + timedelta(milliseconds=i * 200)
        )
        await wm_stream.emit(event)

    # Advance watermark
    results = wm_stream.advance_watermark(now + timedelta(seconds=5))

    print(f"   Windows triggered: {len(results)}")
    for r in results:
        print(f"   - Sum: {r.result}, Events: {r.event_count}")
    print()

    # 11. Stream State
    print("11. STREAM STATE:")
    print("-" * 40)

    print(f"   Current state: {stream.state().value}")

    stream.pause()
    print(f"   After pause: {stream.state().value}")

    stream.start()
    print(f"   After start: {stream.state().value}")
    print()

    # 12. List Streams
    print("12. LIST STREAMS:")
    print("-" * 40)

    streams = manager.list_streams()

    for s in streams:
        print(f"   {s.name}: {s.state().value}")
    print()

    # 13. Delete Stream
    print("13. DELETE STREAM:")
    print("-" * 40)

    count_before = manager.stream_count()
    deleted = manager.delete_stream(flat.stream_id)
    count_after = manager.stream_count()

    print(f"   Deleted: {deleted}")
    print(f"   Streams: {count_before} -> {count_after}")
    print()

    # 14. All Stats
    print("14. ALL STATS:")
    print("-" * 40)

    all_stats = manager.get_all_stats()

    for sid, stats in list(all_stats.items())[:3]:
        print(f"   {sid[:8]}...: {stats.events_processed} events")
    print()

    # 15. Window Count
    print("15. WINDOW COUNT:")
    print("-" * 40)

    for s in manager.list_streams():
        print(f"   {s.name}: {s.window_count()} active windows")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Stream Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
