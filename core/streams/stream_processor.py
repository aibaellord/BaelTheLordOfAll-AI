#!/usr/bin/env python3
"""
BAEL - Stream Processor
Advanced stream processing for AI agent real-time operations.

Features:
- Event streams
- Windowed operations
- Aggregations
- Filtering/mapping
- Back-pressure handling
- Stream joining
- Stateful processing
- Async generators
- Buffer management
- Stream transformations
"""

import asyncio
import collections
import functools
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, AsyncGenerator, AsyncIterator, Awaitable, Callable,
                    Deque, Dict, Generic, Iterator, List, Optional, Set, Tuple,
                    TypeVar, Union)

T = TypeVar('T')
S = TypeVar('S')
R = TypeVar('R')
K = TypeVar('K')
V = TypeVar('V')


# =============================================================================
# ENUMS
# =============================================================================

class StreamState(Enum):
    """Stream states."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


class WindowType(Enum):
    """Window types."""
    TUMBLING = "tumbling"
    SLIDING = "sliding"
    SESSION = "session"
    COUNT = "count"


class BackpressureStrategy(Enum):
    """Back-pressure strategies."""
    BUFFER = "buffer"
    DROP_OLDEST = "drop_oldest"
    DROP_NEWEST = "drop_newest"
    BLOCK = "block"
    ERROR = "error"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class StreamEvent(Generic[T]):
    """An event in the stream."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    data: T = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    key: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class StreamConfig:
    """Stream configuration."""
    buffer_size: int = 1000
    backpressure: BackpressureStrategy = BackpressureStrategy.BUFFER
    timeout: Optional[float] = None
    batch_size: int = 1


@dataclass
class WindowConfig:
    """Window configuration."""
    window_type: WindowType = WindowType.TUMBLING
    size_ms: int = 1000
    slide_ms: int = 500  # For sliding windows
    max_events: int = 1000  # For count windows


@dataclass
class StreamStats:
    """Stream statistics."""
    events_processed: int = 0
    events_dropped: int = 0
    errors: int = 0
    avg_latency_ms: float = 0.0
    throughput_per_sec: float = 0.0


@dataclass
class AggregationResult(Generic[T]):
    """Result of an aggregation."""
    key: Optional[str] = None
    value: T = None
    count: int = 0
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None


# =============================================================================
# STREAM OPERATORS
# =============================================================================

class StreamOperator(ABC, Generic[T, R]):
    """Abstract stream operator."""

    @abstractmethod
    async def process(self, event: StreamEvent[T]) -> Optional[StreamEvent[R]]:
        """Process an event."""
        pass


class MapOperator(StreamOperator[T, R]):
    """Map operator."""

    def __init__(self, func: Callable[[T], R]):
        self.func = func

    async def process(self, event: StreamEvent[T]) -> Optional[StreamEvent[R]]:
        result = self.func(event.data)
        return StreamEvent(
            data=result,
            timestamp=event.timestamp,
            key=event.key,
            headers=event.headers.copy()
        )


class AsyncMapOperator(StreamOperator[T, R]):
    """Async map operator."""

    def __init__(self, func: Callable[[T], Awaitable[R]]):
        self.func = func

    async def process(self, event: StreamEvent[T]) -> Optional[StreamEvent[R]]:
        result = await self.func(event.data)
        return StreamEvent(
            data=result,
            timestamp=event.timestamp,
            key=event.key,
            headers=event.headers.copy()
        )


class FilterOperator(StreamOperator[T, T]):
    """Filter operator."""

    def __init__(self, predicate: Callable[[T], bool]):
        self.predicate = predicate

    async def process(self, event: StreamEvent[T]) -> Optional[StreamEvent[T]]:
        if self.predicate(event.data):
            return event
        return None


class FlatMapOperator(StreamOperator[T, R]):
    """Flat map operator."""

    def __init__(self, func: Callable[[T], List[R]]):
        self.func = func
        self._pending: Deque[StreamEvent[R]] = deque()

    async def process(self, event: StreamEvent[T]) -> Optional[StreamEvent[R]]:
        results = self.func(event.data)

        for result in results[1:]:
            self._pending.append(StreamEvent(
                data=result,
                timestamp=event.timestamp,
                key=event.key
            ))

        if results:
            return StreamEvent(
                data=results[0],
                timestamp=event.timestamp,
                key=event.key
            )
        return None

    def has_pending(self) -> bool:
        return len(self._pending) > 0

    def pop_pending(self) -> Optional[StreamEvent[R]]:
        if self._pending:
            return self._pending.popleft()
        return None


class KeyByOperator(StreamOperator[T, T]):
    """Key by operator."""

    def __init__(self, key_func: Callable[[T], str]):
        self.key_func = key_func

    async def process(self, event: StreamEvent[T]) -> Optional[StreamEvent[T]]:
        event.key = self.key_func(event.data)
        return event


# =============================================================================
# WINDOW
# =============================================================================

class Window(Generic[T]):
    """
    A window of events.
    """

    def __init__(
        self,
        config: WindowConfig,
        key: Optional[str] = None
    ):
        self.config = config
        self.key = key

        self._events: List[StreamEvent[T]] = []
        self._start_time: Optional[datetime] = None
        self._last_event_time: Optional[datetime] = None

    def add(self, event: StreamEvent[T]) -> bool:
        """Add event to window. Returns True if window is full."""
        if self._start_time is None:
            self._start_time = event.timestamp

        self._events.append(event)
        self._last_event_time = event.timestamp

        return self._is_complete()

    def _is_complete(self) -> bool:
        """Check if window is complete."""
        if self.config.window_type == WindowType.COUNT:
            return len(self._events) >= self.config.max_events

        if self._start_time is None:
            return False

        elapsed = (datetime.utcnow() - self._start_time).total_seconds() * 1000
        return elapsed >= self.config.size_ms

    def get_events(self) -> List[StreamEvent[T]]:
        """Get all events in window."""
        return self._events.copy()

    def clear(self) -> List[StreamEvent[T]]:
        """Clear window and return events."""
        events = self._events
        self._events = []
        self._start_time = None
        return events

    @property
    def count(self) -> int:
        return len(self._events)

    @property
    def start(self) -> Optional[datetime]:
        return self._start_time


# =============================================================================
# AGGREGATOR
# =============================================================================

class Aggregator(ABC, Generic[T, R]):
    """Abstract aggregator."""

    @abstractmethod
    def add(self, value: T) -> None:
        pass

    @abstractmethod
    def result(self) -> R:
        pass

    @abstractmethod
    def reset(self) -> None:
        pass


class CountAggregator(Aggregator[Any, int]):
    """Count aggregator."""

    def __init__(self):
        self._count = 0

    def add(self, value: Any) -> None:
        self._count += 1

    def result(self) -> int:
        return self._count

    def reset(self) -> None:
        self._count = 0


class SumAggregator(Aggregator[float, float]):
    """Sum aggregator."""

    def __init__(self):
        self._sum = 0.0

    def add(self, value: float) -> None:
        self._sum += value

    def result(self) -> float:
        return self._sum

    def reset(self) -> None:
        self._sum = 0.0


class AvgAggregator(Aggregator[float, float]):
    """Average aggregator."""

    def __init__(self):
        self._sum = 0.0
        self._count = 0

    def add(self, value: float) -> None:
        self._sum += value
        self._count += 1

    def result(self) -> float:
        if self._count == 0:
            return 0.0
        return self._sum / self._count

    def reset(self) -> None:
        self._sum = 0.0
        self._count = 0


class MinAggregator(Aggregator[float, float]):
    """Minimum aggregator."""

    def __init__(self):
        self._min: Optional[float] = None

    def add(self, value: float) -> None:
        if self._min is None or value < self._min:
            self._min = value

    def result(self) -> float:
        return self._min if self._min is not None else 0.0

    def reset(self) -> None:
        self._min = None


class MaxAggregator(Aggregator[float, float]):
    """Maximum aggregator."""

    def __init__(self):
        self._max: Optional[float] = None

    def add(self, value: float) -> None:
        if self._max is None or value > self._max:
            self._max = value

    def result(self) -> float:
        return self._max if self._max is not None else 0.0

    def reset(self) -> None:
        self._max = None


class CollectAggregator(Aggregator[T, List[T]]):
    """Collect into list aggregator."""

    def __init__(self, max_size: int = 1000):
        self._items: List[T] = []
        self._max_size = max_size

    def add(self, value: T) -> None:
        if len(self._items) < self._max_size:
            self._items.append(value)

    def result(self) -> List[T]:
        return self._items.copy()

    def reset(self) -> None:
        self._items = []


# =============================================================================
# STREAM BUFFER
# =============================================================================

class StreamBuffer(Generic[T]):
    """
    Buffer for stream events.
    """

    def __init__(
        self,
        max_size: int = 1000,
        strategy: BackpressureStrategy = BackpressureStrategy.BUFFER
    ):
        self.max_size = max_size
        self.strategy = strategy

        self._buffer: Deque[StreamEvent[T]] = deque(maxlen=max_size)
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Condition()
        self._dropped = 0

    async def put(self, event: StreamEvent[T]) -> bool:
        """Put event in buffer."""
        async with self._not_empty:
            if len(self._buffer) >= self.max_size:
                if self.strategy == BackpressureStrategy.DROP_OLDEST:
                    self._buffer.popleft()
                    self._dropped += 1
                elif self.strategy == BackpressureStrategy.DROP_NEWEST:
                    self._dropped += 1
                    return False
                elif self.strategy == BackpressureStrategy.BLOCK:
                    while len(self._buffer) >= self.max_size:
                        await asyncio.sleep(0.01)
                elif self.strategy == BackpressureStrategy.ERROR:
                    raise BufferError("Buffer full")

            self._buffer.append(event)
            self._not_empty.notify()
            return True

    async def get(self, timeout: Optional[float] = None) -> Optional[StreamEvent[T]]:
        """Get event from buffer."""
        async with self._not_empty:
            while not self._buffer:
                try:
                    await asyncio.wait_for(
                        self._not_empty.wait(),
                        timeout=timeout
                    )
                except asyncio.TimeoutError:
                    return None

            return self._buffer.popleft()

    async def get_batch(
        self,
        batch_size: int,
        timeout: Optional[float] = None
    ) -> List[StreamEvent[T]]:
        """Get batch of events."""
        events = []
        deadline = time.time() + (timeout or 0)

        while len(events) < batch_size:
            remaining = deadline - time.time() if timeout else None

            if remaining is not None and remaining <= 0:
                break

            event = await self.get(timeout=remaining)
            if event:
                events.append(event)
            else:
                break

        return events

    @property
    def size(self) -> int:
        return len(self._buffer)

    @property
    def dropped(self) -> int:
        return self._dropped

    def clear(self) -> None:
        self._buffer.clear()


# =============================================================================
# STREAM
# =============================================================================

class Stream(Generic[T]):
    """
    A data stream.
    """

    def __init__(
        self,
        config: Optional[StreamConfig] = None
    ):
        self.config = config or StreamConfig()
        self.stream_id = str(uuid.uuid4())

        self._buffer = StreamBuffer[T](
            max_size=self.config.buffer_size,
            strategy=self.config.backpressure
        )

        self._operators: List[StreamOperator] = []
        self._sinks: List[Callable[[StreamEvent], Awaitable[None]]] = []

        self._state = StreamState.IDLE
        self._stats = StreamStats()
        self._start_time: Optional[float] = None

        self._cancel_event = asyncio.Event()

    # -------------------------------------------------------------------------
    # OPERATORS
    # -------------------------------------------------------------------------

    def map(self, func: Callable[[T], R]) -> 'Stream[R]':
        """Add map operator."""
        self._operators.append(MapOperator(func))
        return self  # type: ignore

    def map_async(self, func: Callable[[T], Awaitable[R]]) -> 'Stream[R]':
        """Add async map operator."""
        self._operators.append(AsyncMapOperator(func))
        return self  # type: ignore

    def filter(self, predicate: Callable[[T], bool]) -> 'Stream[T]':
        """Add filter operator."""
        self._operators.append(FilterOperator(predicate))
        return self

    def flat_map(self, func: Callable[[T], List[R]]) -> 'Stream[R]':
        """Add flat map operator."""
        self._operators.append(FlatMapOperator(func))
        return self  # type: ignore

    def key_by(self, key_func: Callable[[T], str]) -> 'Stream[T]':
        """Add key by operator."""
        self._operators.append(KeyByOperator(key_func))
        return self

    # -------------------------------------------------------------------------
    # SINKS
    # -------------------------------------------------------------------------

    def sink(self, func: Callable[[StreamEvent[T]], Awaitable[None]]) -> 'Stream[T]':
        """Add a sink."""
        self._sinks.append(func)
        return self

    def print_sink(self) -> 'Stream[T]':
        """Add print sink."""
        async def printer(event: StreamEvent[T]) -> None:
            print(f"[{event.timestamp}] {event.data}")

        self._sinks.append(printer)
        return self

    # -------------------------------------------------------------------------
    # INPUT
    # -------------------------------------------------------------------------

    async def emit(self, data: T, key: Optional[str] = None) -> bool:
        """Emit an event to the stream."""
        event = StreamEvent(data=data, key=key)
        return await self._buffer.put(event)

    async def emit_many(self, items: List[T]) -> int:
        """Emit multiple events."""
        count = 0
        for item in items:
            if await self.emit(item):
                count += 1
        return count

    # -------------------------------------------------------------------------
    # EXECUTION
    # -------------------------------------------------------------------------

    async def start(self) -> None:
        """Start stream processing."""
        self._state = StreamState.RUNNING
        self._start_time = time.time()

        while not self._cancel_event.is_set():
            try:
                event = await self._buffer.get(timeout=0.1)
                if event:
                    await self._process_event(event)
            except Exception as e:
                self._stats.errors += 1
                self._state = StreamState.ERROR

    async def stop(self) -> None:
        """Stop stream processing."""
        self._cancel_event.set()
        self._state = StreamState.COMPLETED

    async def _process_event(self, event: StreamEvent) -> None:
        """Process a single event through operators."""
        start = time.time()
        current = event

        for op in self._operators:
            if current is None:
                break
            current = await op.process(current)

            # Handle flat map pending
            if isinstance(op, FlatMapOperator):
                while op.has_pending():
                    pending = op.pop_pending()
                    if pending:
                        await self._deliver(pending)

        if current:
            await self._deliver(current)

        # Update stats
        latency = (time.time() - start) * 1000
        self._stats.events_processed += 1

        n = self._stats.events_processed
        self._stats.avg_latency_ms = (
            (self._stats.avg_latency_ms * (n - 1) + latency) / n
        )

        if self._start_time:
            elapsed = time.time() - self._start_time
            if elapsed > 0:
                self._stats.throughput_per_sec = n / elapsed

    async def _deliver(self, event: StreamEvent) -> None:
        """Deliver event to sinks."""
        for sink in self._sinks:
            await sink(event)

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    async def collect(self, max_events: int = 1000) -> List[T]:
        """Collect events into a list."""
        results: List[T] = []

        async def collector(event: StreamEvent[T]) -> None:
            if len(results) < max_events:
                results.append(event.data)

        self._sinks.append(collector)
        return results

    def get_stats(self) -> StreamStats:
        """Get stream statistics."""
        return StreamStats(
            events_processed=self._stats.events_processed,
            events_dropped=self._buffer.dropped,
            errors=self._stats.errors,
            avg_latency_ms=self._stats.avg_latency_ms,
            throughput_per_sec=self._stats.throughput_per_sec
        )

    @property
    def state(self) -> StreamState:
        return self._state


# =============================================================================
# WINDOWED STREAM
# =============================================================================

class WindowedStream(Generic[T, R]):
    """
    A windowed stream with aggregation.
    """

    def __init__(
        self,
        source: Stream[T],
        window_config: WindowConfig,
        aggregator: Aggregator[T, R],
        value_extractor: Optional[Callable[[T], Any]] = None
    ):
        self.source = source
        self.window_config = window_config
        self.aggregator = aggregator
        self.value_extractor = value_extractor or (lambda x: x)

        self._windows: Dict[Optional[str], Window[T]] = {}
        self._results: List[AggregationResult[R]] = []
        self._lock = asyncio.Lock()

    def get_window(self, key: Optional[str]) -> Window[T]:
        """Get or create window for key."""
        if key not in self._windows:
            self._windows[key] = Window(self.window_config, key)
        return self._windows[key]

    async def add_event(self, event: StreamEvent[T]) -> Optional[AggregationResult[R]]:
        """Add event to appropriate window."""
        async with self._lock:
            window = self.get_window(event.key)
            is_complete = window.add(event)

            if is_complete:
                return await self._flush_window(window)

            return None

    async def _flush_window(self, window: Window[T]) -> AggregationResult[R]:
        """Flush window and get aggregation result."""
        events = window.clear()

        self.aggregator.reset()
        for event in events:
            value = self.value_extractor(event.data)
            self.aggregator.add(value)

        result = AggregationResult(
            key=window.key,
            value=self.aggregator.result(),
            count=len(events),
            window_start=window.start,
            window_end=datetime.utcnow()
        )

        self._results.append(result)
        return result

    async def flush_all(self) -> List[AggregationResult[R]]:
        """Flush all windows."""
        results = []

        async with self._lock:
            for window in list(self._windows.values()):
                if window.count > 0:
                    result = await self._flush_window(window)
                    results.append(result)

        return results

    def get_results(self) -> List[AggregationResult[R]]:
        """Get all aggregation results."""
        return self._results.copy()


# =============================================================================
# STREAM PROCESSOR
# =============================================================================

class StreamProcessor:
    """
    Stream Processor for BAEL.

    Advanced stream processing.
    """

    def __init__(self):
        self._streams: Dict[str, Stream] = {}
        self._windowed_streams: Dict[str, WindowedStream] = {}
        self._lock = threading.RLock()

    # -------------------------------------------------------------------------
    # STREAM CREATION
    # -------------------------------------------------------------------------

    def create_stream(
        self,
        config: Optional[StreamConfig] = None
    ) -> Stream:
        """Create a new stream."""
        stream = Stream(config)

        with self._lock:
            self._streams[stream.stream_id] = stream

        return stream

    def create_windowed_stream(
        self,
        source: Stream[T],
        window_type: WindowType = WindowType.TUMBLING,
        window_size_ms: int = 1000,
        aggregation: str = "count"
    ) -> WindowedStream:
        """Create a windowed stream."""
        window_config = WindowConfig(
            window_type=window_type,
            size_ms=window_size_ms
        )

        # Select aggregator
        aggregator: Aggregator
        if aggregation == "count":
            aggregator = CountAggregator()
        elif aggregation == "sum":
            aggregator = SumAggregator()
        elif aggregation == "avg":
            aggregator = AvgAggregator()
        elif aggregation == "min":
            aggregator = MinAggregator()
        elif aggregation == "max":
            aggregator = MaxAggregator()
        elif aggregation == "collect":
            aggregator = CollectAggregator()
        else:
            aggregator = CountAggregator()

        windowed = WindowedStream(source, window_config, aggregator)

        with self._lock:
            self._windowed_streams[source.stream_id] = windowed

        return windowed

    # -------------------------------------------------------------------------
    # GENERATORS
    # -------------------------------------------------------------------------

    async def from_iterable(
        self,
        items: List[T],
        delay: float = 0.0
    ) -> Stream[T]:
        """Create stream from iterable."""
        stream = self.create_stream()

        async def emit_items():
            for item in items:
                await stream.emit(item)
                if delay > 0:
                    await asyncio.sleep(delay)

        asyncio.create_task(emit_items())
        return stream

    async def from_async_generator(
        self,
        gen: AsyncGenerator[T, None]
    ) -> Stream[T]:
        """Create stream from async generator."""
        stream = self.create_stream()

        async def emit_items():
            async for item in gen:
                await stream.emit(item)

        asyncio.create_task(emit_items())
        return stream

    def from_callback(self) -> Tuple[Stream[T], Callable[[T], Awaitable[None]]]:
        """Create stream with callback for emission."""
        stream = self.create_stream()

        async def callback(item: T) -> None:
            await stream.emit(item)

        return stream, callback

    # -------------------------------------------------------------------------
    # MERGING/JOINING
    # -------------------------------------------------------------------------

    def merge(self, *streams: Stream[T]) -> Stream[T]:
        """Merge multiple streams."""
        merged = self.create_stream()

        async def forward(event: StreamEvent[T]) -> None:
            await merged.emit(event.data, event.key)

        for stream in streams:
            stream.sink(forward)

        return merged

    def zip_streams(
        self,
        stream1: Stream[T],
        stream2: Stream[S]
    ) -> Stream[Tuple[T, S]]:
        """Zip two streams."""
        zipped = self.create_stream()
        buffer1: List[T] = []
        buffer2: List[S] = []
        lock = asyncio.Lock()

        async def on_stream1(event: StreamEvent[T]) -> None:
            async with lock:
                if buffer2:
                    await zipped.emit((event.data, buffer2.pop(0)))
                else:
                    buffer1.append(event.data)

        async def on_stream2(event: StreamEvent[S]) -> None:
            async with lock:
                if buffer1:
                    await zipped.emit((buffer1.pop(0), event.data))
                else:
                    buffer2.append(event.data)

        stream1.sink(on_stream1)
        stream2.sink(on_stream2)

        return zipped

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def get_stream(self, stream_id: str) -> Optional[Stream]:
        """Get stream by ID."""
        with self._lock:
            return self._streams.get(stream_id)

    def list_streams(self) -> List[Dict[str, Any]]:
        """List all streams."""
        with self._lock:
            return [
                {
                    "stream_id": s.stream_id,
                    "state": s.state.value,
                    "events_processed": s.get_stats().events_processed
                }
                for s in self._streams.values()
            ]

    async def stop_all(self) -> None:
        """Stop all streams."""
        with self._lock:
            streams = list(self._streams.values())

        for stream in streams:
            await stream.stop()


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Stream Processor."""
    print("=" * 70)
    print("BAEL - STREAM PROCESSOR DEMO")
    print("Advanced Stream Processing for AI Agents")
    print("=" * 70)
    print()

    processor = StreamProcessor()

    # 1. Basic Stream
    print("1. BASIC STREAM:")
    print("-" * 40)

    stream = processor.create_stream()
    collected: List[int] = []

    async def collector(event: StreamEvent[int]) -> None:
        collected.append(event.data)

    stream.sink(collector)

    # Emit events
    for i in range(5):
        await stream.emit(i)

    # Process
    task = asyncio.create_task(stream.start())
    await asyncio.sleep(0.2)
    await stream.stop()

    print(f"   Emitted: [0, 1, 2, 3, 4]")
    print(f"   Collected: {collected}")
    print()

    # 2. Map Operator
    print("2. MAP OPERATOR:")
    print("-" * 40)

    stream = processor.create_stream()
    mapped: List[int] = []

    stream.map(lambda x: x * 2).sink(
        lambda e: mapped.append(e.data) or asyncio.sleep(0)  # type: ignore
    )

    for i in range(5):
        await stream.emit(i)

    task = asyncio.create_task(stream.start())
    await asyncio.sleep(0.2)
    await stream.stop()

    print(f"   Input: [0, 1, 2, 3, 4]")
    print(f"   Mapped (x2): {mapped}")
    print()

    # 3. Filter Operator
    print("3. FILTER OPERATOR:")
    print("-" * 40)

    stream = processor.create_stream()
    filtered: List[int] = []

    stream.filter(lambda x: x % 2 == 0).sink(
        lambda e: filtered.append(e.data) or asyncio.sleep(0)  # type: ignore
    )

    for i in range(10):
        await stream.emit(i)

    task = asyncio.create_task(stream.start())
    await asyncio.sleep(0.2)
    await stream.stop()

    print(f"   Input: [0-9]")
    print(f"   Filtered (even): {filtered}")
    print()

    # 4. Chained Operators
    print("4. CHAINED OPERATORS:")
    print("-" * 40)

    stream = processor.create_stream()
    chained: List[str] = []

    (stream
     .filter(lambda x: x > 2)
     .map(lambda x: x ** 2)
     .map(lambda x: f"val_{x}")
     .sink(lambda e: chained.append(e.data) or asyncio.sleep(0)))  # type: ignore

    for i in range(6):
        await stream.emit(i)

    task = asyncio.create_task(stream.start())
    await asyncio.sleep(0.2)
    await stream.stop()

    print(f"   Input: [0, 1, 2, 3, 4, 5]")
    print(f"   Filter(>2) -> Square -> Format: {chained}")
    print()

    # 5. Windowed Aggregation
    print("5. WINDOWED AGGREGATION:")
    print("-" * 40)

    stream = processor.create_stream()
    windowed = processor.create_windowed_stream(
        stream,
        window_type=WindowType.COUNT,
        window_size_ms=100,
        aggregation="sum"
    )

    # Set up window config for count-based
    windowed.window_config.max_events = 3

    for i in range(9):
        event = StreamEvent(data=float(i + 1))
        result = await windowed.add_event(event)
        if result:
            print(f"   Window closed: sum={result.value}, count={result.count}")

    print()

    # 6. Key-Based Aggregation
    print("6. KEY-BASED AGGREGATION:")
    print("-" * 40)

    stream = processor.create_stream()
    windowed = processor.create_windowed_stream(
        stream,
        window_type=WindowType.COUNT,
        aggregation="sum"
    )
    windowed.window_config.max_events = 2

    events = [
        ("A", 10), ("B", 20), ("A", 30), ("B", 40), ("A", 50), ("B", 60)
    ]

    for key, value in events:
        event = StreamEvent(data=float(value), key=key)
        result = await windowed.add_event(event)
        if result:
            print(f"   Key '{result.key}' window: sum={result.value}")

    print()

    # 7. Different Aggregators
    print("7. DIFFERENT AGGREGATORS:")
    print("-" * 40)

    numbers = [1.0, 2.0, 3.0, 4.0, 5.0]

    # Sum
    agg = SumAggregator()
    for n in numbers:
        agg.add(n)
    print(f"   Numbers: {numbers}")
    print(f"   Sum: {agg.result()}")

    # Average
    agg = AvgAggregator()
    for n in numbers:
        agg.add(n)
    print(f"   Avg: {agg.result()}")

    # Min/Max
    min_agg = MinAggregator()
    max_agg = MaxAggregator()
    for n in numbers:
        min_agg.add(n)
        max_agg.add(n)
    print(f"   Min: {min_agg.result()}, Max: {max_agg.result()}")
    print()

    # 8. Back-pressure Strategies
    print("8. BACK-PRESSURE STRATEGIES:")
    print("-" * 40)

    # Small buffer with drop oldest
    config = StreamConfig(
        buffer_size=3,
        backpressure=BackpressureStrategy.DROP_OLDEST
    )
    stream = processor.create_stream(config)

    for i in range(10):
        await stream.emit(i)

    stats = stream.get_stats()
    print(f"   Buffer size: 3, Emitted: 10")
    print(f"   Dropped (oldest): {stream._buffer.dropped}")
    print()

    # 9. Stream Statistics
    print("9. STREAM STATISTICS:")
    print("-" * 40)

    stream = processor.create_stream()
    stream.map(lambda x: x * 2).sink(lambda e: asyncio.sleep(0))

    for i in range(100):
        await stream.emit(i)

    task = asyncio.create_task(stream.start())
    await asyncio.sleep(0.3)
    await stream.stop()

    stats = stream.get_stats()
    print(f"   Events processed: {stats.events_processed}")
    print(f"   Avg latency: {stats.avg_latency_ms:.3f}ms")
    print(f"   Throughput: {stats.throughput_per_sec:.2f}/sec")
    print()

    # 10. Stream from Iterable
    print("10. STREAM FROM ITERABLE:")
    print("-" * 40)

    items = ["a", "b", "c", "d", "e"]
    stream = await processor.from_iterable(items, delay=0.01)

    received: List[str] = []
    stream.sink(lambda e: received.append(e.data) or asyncio.sleep(0))  # type: ignore

    task = asyncio.create_task(stream.start())
    await asyncio.sleep(0.2)
    await stream.stop()

    print(f"   Source: {items}")
    print(f"   Received: {received}")
    print()

    # 11. Merge Streams
    print("11. MERGE STREAMS:")
    print("-" * 40)

    stream1 = processor.create_stream()
    stream2 = processor.create_stream()
    merged = processor.merge(stream1, stream2)

    merged_items: List[str] = []
    merged.sink(lambda e: merged_items.append(e.data) or asyncio.sleep(0))  # type: ignore

    await stream1.emit("A1")
    await stream2.emit("B1")
    await stream1.emit("A2")
    await stream2.emit("B2")

    task = asyncio.create_task(merged.start())
    await asyncio.sleep(0.2)
    await merged.stop()

    print(f"   Stream1: [A1, A2], Stream2: [B1, B2]")
    print(f"   Merged: {merged_items}")
    print()

    # 12. Flat Map
    print("12. FLAT MAP:")
    print("-" * 40)

    stream = processor.create_stream()
    flat_results: List[str] = []

    stream.flat_map(lambda x: [f"{x}_1", f"{x}_2", f"{x}_3"]).sink(
        lambda e: flat_results.append(e.data) or asyncio.sleep(0)  # type: ignore
    )

    await stream.emit("item")

    task = asyncio.create_task(stream.start())
    await asyncio.sleep(0.2)
    await stream.stop()

    print(f"   Input: 'item'")
    print(f"   Flat mapped: {flat_results}")
    print()

    # 13. List Streams
    print("13. LIST STREAMS:")
    print("-" * 40)

    streams = processor.list_streams()
    print(f"   Total streams: {len(streams)}")
    print()

    # 14. Stop All
    print("14. STOP ALL STREAMS:")
    print("-" * 40)

    await processor.stop_all()
    print("   All streams stopped ✓")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Stream Processor Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
