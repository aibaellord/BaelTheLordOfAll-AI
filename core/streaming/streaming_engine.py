#!/usr/bin/env python3
"""
BAEL - Streaming Engine
Stream processing for agents.

Features:
- Event streams
- Stream transformations
- Windowing operations
- Backpressure handling
- Stream composition
"""

import asyncio
import hashlib
import json
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (
    Any, AsyncIterator, Callable, Coroutine, Dict, Generic, Iterator, List,
    Optional, Set, Tuple, Type, TypeVar, Union
)


T = TypeVar('T')
R = TypeVar('R')


# =============================================================================
# ENUMS
# =============================================================================

class StreamState(Enum):
    """Stream states."""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


class BackpressureStrategy(Enum):
    """Backpressure strategies."""
    BUFFER = "buffer"
    DROP_OLDEST = "drop_oldest"
    DROP_NEWEST = "drop_newest"
    BLOCK = "block"
    ERROR = "error"


class WindowType(Enum):
    """Window types."""
    TUMBLING = "tumbling"
    SLIDING = "sliding"
    SESSION = "session"
    COUNT = "count"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class StreamEvent(Generic[T]):
    """A stream event."""
    event_id: str = ""
    data: Optional[T] = None
    timestamp: datetime = field(default_factory=datetime.now)
    key: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.event_id:
            self.event_id = str(uuid.uuid4())[:8]


@dataclass
class StreamConfig:
    """Stream configuration."""
    buffer_size: int = 1000
    backpressure: BackpressureStrategy = BackpressureStrategy.BUFFER
    prefetch: int = 10
    timeout_seconds: float = 30.0


@dataclass
class WindowSpec:
    """Window specification."""
    window_type: WindowType = WindowType.TUMBLING
    size_seconds: float = 60.0
    slide_seconds: float = 0.0
    count: int = 100
    gap_seconds: float = 30.0


@dataclass
class StreamStats:
    """Stream statistics."""
    events_received: int = 0
    events_processed: int = 0
    events_dropped: int = 0
    errors: int = 0
    start_time: Optional[datetime] = None
    last_event_time: Optional[datetime] = None
    
    @property
    def events_per_second(self) -> float:
        if not self.start_time:
            return 0.0
        elapsed = (datetime.now() - self.start_time).total_seconds()
        if elapsed == 0:
            return 0.0
        return self.events_processed / elapsed


# =============================================================================
# STREAM SOURCE
# =============================================================================

class StreamSource(Generic[T], ABC):
    """Base stream source."""
    
    @abstractmethod
    async def emit(self) -> AsyncIterator[T]:
        """Emit items."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the source."""
        pass


class IterableSource(StreamSource[T]):
    """Source from iterable."""
    
    def __init__(self, items: List[T]):
        self._items = items
        self._index = 0
    
    async def emit(self) -> AsyncIterator[T]:
        for item in self._items:
            yield item
    
    async def close(self) -> None:
        pass


class GeneratorSource(StreamSource[T]):
    """Source from generator function."""
    
    def __init__(self, generator: Callable[[], AsyncIterator[T]]):
        self._generator = generator
    
    async def emit(self) -> AsyncIterator[T]:
        async for item in self._generator():
            yield item
    
    async def close(self) -> None:
        pass


class IntervalSource(StreamSource[int]):
    """Emit items at intervals."""
    
    def __init__(
        self,
        interval_seconds: float = 1.0,
        count: Optional[int] = None
    ):
        self._interval = interval_seconds
        self._count = count
        self._running = True
    
    async def emit(self) -> AsyncIterator[int]:
        i = 0
        while self._running:
            if self._count is not None and i >= self._count:
                break
            yield i
            i += 1
            await asyncio.sleep(self._interval)
    
    async def close(self) -> None:
        self._running = False


class QueueSource(StreamSource[T]):
    """Source from async queue."""
    
    def __init__(self, queue: Optional[asyncio.Queue] = None):
        self._queue = queue or asyncio.Queue()
        self._running = True
    
    async def put(self, item: T) -> None:
        """Put item in queue."""
        await self._queue.put(item)
    
    async def emit(self) -> AsyncIterator[T]:
        while self._running:
            try:
                item = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0
                )
                yield item
            except asyncio.TimeoutError:
                continue
    
    async def close(self) -> None:
        self._running = False


# =============================================================================
# STREAM SINK
# =============================================================================

class StreamSink(Generic[T], ABC):
    """Base stream sink."""
    
    @abstractmethod
    async def write(self, item: T) -> None:
        """Write an item."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the sink."""
        pass


class ListSink(StreamSink[T]):
    """Collect to list."""
    
    def __init__(self):
        self._items: List[T] = []
    
    async def write(self, item: T) -> None:
        self._items.append(item)
    
    async def close(self) -> None:
        pass
    
    def get_items(self) -> List[T]:
        return list(self._items)


class CallbackSink(StreamSink[T]):
    """Call function for each item."""
    
    def __init__(self, callback: Callable[[T], Any]):
        self._callback = callback
    
    async def write(self, item: T) -> None:
        if asyncio.iscoroutinefunction(self._callback):
            await self._callback(item)
        else:
            self._callback(item)
    
    async def close(self) -> None:
        pass


class ConsoleSink(StreamSink[Any]):
    """Print to console."""
    
    def __init__(self, prefix: str = ""):
        self._prefix = prefix
    
    async def write(self, item: Any) -> None:
        print(f"{self._prefix}{item}")
    
    async def close(self) -> None:
        pass


# =============================================================================
# STREAM OPERATORS
# =============================================================================

class StreamOperator(Generic[T, R], ABC):
    """Base stream operator."""
    
    @abstractmethod
    async def apply(self, item: T) -> Optional[R]:
        """Apply operator to item."""
        pass


class MapOperator(StreamOperator[T, R]):
    """Map transformation."""
    
    def __init__(self, func: Callable[[T], R]):
        self._func = func
    
    async def apply(self, item: T) -> Optional[R]:
        if asyncio.iscoroutinefunction(self._func):
            return await self._func(item)
        return self._func(item)


class FilterOperator(StreamOperator[T, T]):
    """Filter items."""
    
    def __init__(self, predicate: Callable[[T], bool]):
        self._predicate = predicate
    
    async def apply(self, item: T) -> Optional[T]:
        if asyncio.iscoroutinefunction(self._predicate):
            result = await self._predicate(item)
        else:
            result = self._predicate(item)
        
        return item if result else None


class FlatMapOperator(StreamOperator[T, R]):
    """Flat map (one-to-many)."""
    
    def __init__(self, func: Callable[[T], List[R]]):
        self._func = func
        self._buffer: List[R] = []
    
    async def apply(self, item: T) -> Optional[R]:
        if not self._buffer:
            if asyncio.iscoroutinefunction(self._func):
                self._buffer = await self._func(item)
            else:
                self._buffer = self._func(item)
        
        if self._buffer:
            return self._buffer.pop(0)
        
        return None


# =============================================================================
# STREAM BUFFER
# =============================================================================

class StreamBuffer(Generic[T]):
    """Buffered stream with backpressure."""
    
    def __init__(
        self,
        max_size: int = 1000,
        strategy: BackpressureStrategy = BackpressureStrategy.BUFFER
    ):
        self._max_size = max_size
        self._strategy = strategy
        self._buffer: deque = deque(maxlen=max_size if strategy == BackpressureStrategy.DROP_OLDEST else None)
        self._dropped = 0
    
    async def put(self, item: T) -> bool:
        """Put item in buffer."""
        if len(self._buffer) >= self._max_size:
            if self._strategy == BackpressureStrategy.DROP_OLDEST:
                self._buffer.popleft()
                self._dropped += 1
            elif self._strategy == BackpressureStrategy.DROP_NEWEST:
                self._dropped += 1
                return False
            elif self._strategy == BackpressureStrategy.ERROR:
                raise Exception("Buffer overflow")
            elif self._strategy == BackpressureStrategy.BLOCK:
                while len(self._buffer) >= self._max_size:
                    await asyncio.sleep(0.01)
        
        self._buffer.append(item)
        return True
    
    async def get(self) -> Optional[T]:
        """Get item from buffer."""
        if self._buffer:
            return self._buffer.popleft()
        return None
    
    def size(self) -> int:
        """Get buffer size."""
        return len(self._buffer)
    
    def is_empty(self) -> bool:
        """Check if empty."""
        return len(self._buffer) == 0
    
    @property
    def dropped_count(self) -> int:
        return self._dropped


# =============================================================================
# WINDOW MANAGER
# =============================================================================

class WindowManager(Generic[T]):
    """Manage windowed streams."""
    
    def __init__(self, spec: WindowSpec):
        self._spec = spec
        self._windows: Dict[str, List[T]] = defaultdict(list)
        self._window_start: Dict[str, datetime] = {}
        self._last_event: Dict[str, datetime] = {}
    
    def add(self, key: str, item: T) -> Optional[List[T]]:
        """Add item to window, return window if complete."""
        now = datetime.now()
        
        if key not in self._window_start:
            self._window_start[key] = now
        
        self._last_event[key] = now
        self._windows[key].append(item)
        
        if self._should_emit(key, now):
            window = list(self._windows[key])
            self._reset_window(key, now)
            return window
        
        return None
    
    def _should_emit(self, key: str, now: datetime) -> bool:
        """Check if window should emit."""
        if self._spec.window_type == WindowType.TUMBLING:
            elapsed = (now - self._window_start[key]).total_seconds()
            return elapsed >= self._spec.size_seconds
        
        elif self._spec.window_type == WindowType.COUNT:
            return len(self._windows[key]) >= self._spec.count
        
        elif self._spec.window_type == WindowType.SESSION:
            last = self._last_event.get(key)
            if last:
                gap = (now - last).total_seconds()
                return gap >= self._spec.gap_seconds
        
        return False
    
    def _reset_window(self, key: str, now: datetime) -> None:
        """Reset window."""
        self._windows[key] = []
        self._window_start[key] = now
    
    def flush(self, key: str) -> List[T]:
        """Flush window."""
        window = list(self._windows.get(key, []))
        self._windows[key] = []
        return window
    
    def flush_all(self) -> Dict[str, List[T]]:
        """Flush all windows."""
        result = {}
        for key in list(self._windows.keys()):
            if self._windows[key]:
                result[key] = self.flush(key)
        return result


# =============================================================================
# STREAM
# =============================================================================

class Stream(Generic[T]):
    """A composable stream."""
    
    def __init__(
        self,
        source: StreamSource[T],
        config: Optional[StreamConfig] = None
    ):
        self._source = source
        self._config = config or StreamConfig()
        self._operators: List[StreamOperator] = []
        self._state = StreamState.CREATED
        self._stats = StreamStats()
    
    def map(self, func: Callable[[T], R]) -> "Stream[R]":
        """Map transformation."""
        self._operators.append(MapOperator(func))
        return self
    
    def filter(self, predicate: Callable[[T], bool]) -> "Stream[T]":
        """Filter items."""
        self._operators.append(FilterOperator(predicate))
        return self
    
    def flat_map(self, func: Callable[[T], List[R]]) -> "Stream[R]":
        """Flat map transformation."""
        self._operators.append(FlatMapOperator(func))
        return self
    
    async def collect(self) -> List[Any]:
        """Collect to list."""
        sink = ListSink()
        await self.run(sink)
        return sink.get_items()
    
    async def for_each(self, callback: Callable[[T], Any]) -> None:
        """Execute callback for each item."""
        sink = CallbackSink(callback)
        await self.run(sink)
    
    async def run(self, sink: StreamSink) -> None:
        """Run the stream."""
        self._state = StreamState.RUNNING
        self._stats.start_time = datetime.now()
        
        try:
            async for item in self._source.emit():
                self._stats.events_received += 1
                
                result = item
                skip = False
                
                for op in self._operators:
                    result = await op.apply(result)
                    if result is None:
                        skip = True
                        break
                
                if not skip:
                    await sink.write(result)
                    self._stats.events_processed += 1
                    self._stats.last_event_time = datetime.now()
            
            self._state = StreamState.COMPLETED
        
        except Exception as e:
            self._state = StreamState.ERROR
            self._stats.errors += 1
            raise
        
        finally:
            await self._source.close()
            await sink.close()
    
    async def take(self, n: int) -> List[Any]:
        """Take first n items."""
        results = []
        count = 0
        
        async for item in self._source.emit():
            if count >= n:
                break
            
            result = item
            skip = False
            
            for op in self._operators:
                result = await op.apply(result)
                if result is None:
                    skip = True
                    break
            
            if not skip:
                results.append(result)
                count += 1
        
        return results
    
    async def first(self) -> Optional[Any]:
        """Get first item."""
        items = await self.take(1)
        return items[0] if items else None
    
    async def count(self) -> int:
        """Count items."""
        return len(await self.collect())
    
    @property
    def state(self) -> StreamState:
        return self._state
    
    @property
    def stats(self) -> StreamStats:
        return self._stats


# =============================================================================
# STREAMING ENGINE
# =============================================================================

class StreamingEngine:
    """
    Streaming Engine for BAEL.
    
    Event stream processing.
    """
    
    def __init__(self, config: Optional[StreamConfig] = None):
        self._config = config or StreamConfig()
        
        self._streams: Dict[str, Stream] = {}
        self._sources: Dict[str, StreamSource] = {}
        self._sinks: Dict[str, StreamSink] = {}
        self._windows: Dict[str, WindowManager] = {}
        
        self._stats: Dict[str, StreamStats] = {}
    
    # ----- Stream Creation -----
    
    def from_iterable(self, items: List[Any]) -> Stream:
        """Create stream from iterable."""
        source = IterableSource(items)
        return Stream(source, self._config)
    
    def from_generator(
        self,
        generator: Callable[[], AsyncIterator]
    ) -> Stream:
        """Create stream from generator."""
        source = GeneratorSource(generator)
        return Stream(source, self._config)
    
    def from_interval(
        self,
        interval_seconds: float = 1.0,
        count: Optional[int] = None
    ) -> Stream:
        """Create interval stream."""
        source = IntervalSource(interval_seconds, count)
        return Stream(source, self._config)
    
    def from_queue(
        self,
        queue: Optional[asyncio.Queue] = None
    ) -> Tuple[Stream, QueueSource]:
        """Create stream from queue."""
        source = QueueSource(queue)
        return Stream(source, self._config), source
    
    # ----- Named Streams -----
    
    def register_stream(self, name: str, stream: Stream) -> None:
        """Register a named stream."""
        self._streams[name] = stream
    
    def get_stream(self, name: str) -> Optional[Stream]:
        """Get a named stream."""
        return self._streams.get(name)
    
    def list_streams(self) -> List[str]:
        """List stream names."""
        return list(self._streams.keys())
    
    # ----- Source Management -----
    
    def register_source(self, name: str, source: StreamSource) -> None:
        """Register a source."""
        self._sources[name] = source
    
    def get_source(self, name: str) -> Optional[StreamSource]:
        """Get a source."""
        return self._sources.get(name)
    
    # ----- Sink Management -----
    
    def register_sink(self, name: str, sink: StreamSink) -> None:
        """Register a sink."""
        self._sinks[name] = sink
    
    def get_sink(self, name: str) -> Optional[StreamSink]:
        """Get a sink."""
        return self._sinks.get(name)
    
    # ----- Windowing -----
    
    def create_window(self, name: str, spec: WindowSpec) -> WindowManager:
        """Create a window manager."""
        manager = WindowManager(spec)
        self._windows[name] = manager
        return manager
    
    def get_window(self, name: str) -> Optional[WindowManager]:
        """Get a window manager."""
        return self._windows.get(name)
    
    def add_to_window(
        self,
        window_name: str,
        key: str,
        item: Any
    ) -> Optional[List[Any]]:
        """Add item to window."""
        manager = self._windows.get(window_name)
        
        if manager:
            return manager.add(key, item)
        
        return None
    
    # ----- Direct Processing -----
    
    async def process(
        self,
        items: List[Any],
        *operators: Callable
    ) -> List[Any]:
        """Process items through operators."""
        stream = self.from_iterable(items)
        
        for op in operators:
            stream = stream.map(op)
        
        return await stream.collect()
    
    async def filter_items(
        self,
        items: List[Any],
        predicate: Callable[[Any], bool]
    ) -> List[Any]:
        """Filter items."""
        stream = self.from_iterable(items)
        return await stream.filter(predicate).collect()
    
    async def map_items(
        self,
        items: List[Any],
        func: Callable[[Any], Any]
    ) -> List[Any]:
        """Map items."""
        stream = self.from_iterable(items)
        return await stream.map(func).collect()
    
    # ----- Aggregations -----
    
    async def reduce(
        self,
        items: List[Any],
        func: Callable[[Any, Any], Any],
        initial: Any = None
    ) -> Any:
        """Reduce items."""
        result = initial
        
        for item in items:
            if result is None:
                result = item
            else:
                result = func(result, item)
        
        return result
    
    async def sum(self, items: List[float]) -> float:
        """Sum items."""
        return sum(items)
    
    async def avg(self, items: List[float]) -> float:
        """Average items."""
        return sum(items) / len(items) if items else 0.0
    
    async def count(self, items: List[Any]) -> int:
        """Count items."""
        return len(items)
    
    # ----- Pipeline -----
    
    async def pipeline(
        self,
        source_name: str,
        sink_name: str,
        operators: List[Callable]
    ) -> StreamStats:
        """Run a pipeline."""
        source = self._sources.get(source_name)
        sink = self._sinks.get(sink_name)
        
        if not source or not sink:
            return StreamStats()
        
        stream = Stream(source, self._config)
        
        for op in operators:
            stream = stream.map(op)
        
        await stream.run(sink)
        
        self._stats[f"{source_name}->{sink_name}"] = stream.stats
        return stream.stats
    
    # ----- Statistics -----
    
    def get_stats(self, stream_name: str) -> Optional[StreamStats]:
        """Get stream stats."""
        stream = self._streams.get(stream_name)
        return stream.stats if stream else None
    
    def stats(self) -> Dict[str, Any]:
        """Get engine stats."""
        total_events = 0
        total_processed = 0
        total_errors = 0
        
        for stream in self._streams.values():
            total_events += stream.stats.events_received
            total_processed += stream.stats.events_processed
            total_errors += stream.stats.errors
        
        return {
            "streams": len(self._streams),
            "sources": len(self._sources),
            "sinks": len(self._sinks),
            "windows": len(self._windows),
            "total_events": total_events,
            "total_processed": total_processed,
            "total_errors": total_errors
        }
    
    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "streams": self.list_streams(),
            "sources": list(self._sources.keys()),
            "sinks": list(self._sinks.keys()),
            "windows": list(self._windows.keys())
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Streaming Engine."""
    print("=" * 70)
    print("BAEL - STREAMING ENGINE DEMO")
    print("Event Stream Processing")
    print("=" * 70)
    print()
    
    engine = StreamingEngine()
    
    # 1. Basic Stream
    print("1. BASIC STREAM:")
    print("-" * 40)
    
    stream = engine.from_iterable([1, 2, 3, 4, 5])
    result = await stream.collect()
    print(f"   Input: [1, 2, 3, 4, 5]")
    print(f"   Output: {result}")
    print()
    
    # 2. Map Transformation
    print("2. MAP TRANSFORMATION:")
    print("-" * 40)
    
    result = await engine.from_iterable([1, 2, 3, 4, 5]).map(lambda x: x * 2).collect()
    print(f"   Double: {result}")
    
    result = await engine.from_iterable([1, 2, 3, 4, 5]).map(lambda x: x ** 2).collect()
    print(f"   Square: {result}")
    print()
    
    # 3. Filter Transformation
    print("3. FILTER TRANSFORMATION:")
    print("-" * 40)
    
    result = await engine.from_iterable([1, 2, 3, 4, 5, 6]).filter(lambda x: x % 2 == 0).collect()
    print(f"   Even: {result}")
    
    result = await engine.from_iterable([1, 2, 3, 4, 5, 6]).filter(lambda x: x > 3).collect()
    print(f"   > 3: {result}")
    print()
    
    # 4. Chained Transformations
    print("4. CHAINED TRANSFORMATIONS:")
    print("-" * 40)
    
    result = await (
        engine.from_iterable([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        .filter(lambda x: x % 2 == 0)
        .map(lambda x: x ** 2)
        .collect()
    )
    print(f"   Even squared: {result}")
    print()
    
    # 5. Take and First
    print("5. TAKE AND FIRST:")
    print("-" * 40)
    
    stream = engine.from_iterable(list(range(100)))
    first_10 = await stream.take(10)
    print(f"   First 10: {first_10}")
    
    stream = engine.from_iterable([1, 2, 3])
    first = await stream.first()
    print(f"   First: {first}")
    print()
    
    # 6. Count
    print("6. COUNT:")
    print("-" * 40)
    
    count = await engine.from_iterable(list(range(50))).filter(lambda x: x % 2 == 0).count()
    print(f"   Even count in 0-49: {count}")
    print()
    
    # 7. For Each
    print("7. FOR EACH:")
    print("-" * 40)
    
    collected = []
    await engine.from_iterable([1, 2, 3]).for_each(lambda x: collected.append(x * 10))
    print(f"   Collected: {collected}")
    print()
    
    # 8. Interval Stream
    print("8. INTERVAL STREAM:")
    print("-" * 40)
    
    stream = engine.from_interval(interval_seconds=0.1, count=5)
    result = await stream.collect()
    print(f"   Interval values: {result}")
    print()
    
    # 9. Queue Stream
    print("9. QUEUE STREAM:")
    print("-" * 40)
    
    stream, source = engine.from_queue()
    
    async def producer():
        for i in range(5):
            await source.put(i)
        await source.close()
    
    asyncio.create_task(producer())
    result = await stream.take(5)
    print(f"   Queue values: {result}")
    print()
    
    # 10. Window Manager
    print("10. WINDOW MANAGER:")
    print("-" * 40)
    
    window = engine.create_window(
        "events",
        WindowSpec(window_type=WindowType.COUNT, count=3)
    )
    
    for i in range(10):
        result = engine.add_to_window("events", "key1", i)
        if result:
            print(f"   Window emitted: {result}")
    
    remaining = window.flush("key1")
    print(f"   Remaining: {remaining}")
    print()
    
    # 11. Direct Processing
    print("11. DIRECT PROCESSING:")
    print("-" * 40)
    
    result = await engine.process(
        [1, 2, 3, 4, 5],
        lambda x: x * 2,
        lambda x: x + 1
    )
    print(f"   (x*2)+1: {result}")
    print()
    
    # 12. Filter Items
    print("12. FILTER ITEMS:")
    print("-" * 40)
    
    result = await engine.filter_items(
        ["apple", "banana", "cherry", "date"],
        lambda x: len(x) > 5
    )
    print(f"   Long fruits: {result}")
    print()
    
    # 13. Map Items
    print("13. MAP ITEMS:")
    print("-" * 40)
    
    result = await engine.map_items(
        ["hello", "world"],
        lambda x: x.upper()
    )
    print(f"   Uppercase: {result}")
    print()
    
    # 14. Reduce
    print("14. REDUCE:")
    print("-" * 40)
    
    result = await engine.reduce([1, 2, 3, 4, 5], lambda a, b: a + b)
    print(f"   Sum: {result}")
    
    result = await engine.reduce([1, 2, 3, 4, 5], lambda a, b: a * b)
    print(f"   Product: {result}")
    print()
    
    # 15. Aggregations
    print("15. AGGREGATIONS:")
    print("-" * 40)
    
    items = [1.0, 2.0, 3.0, 4.0, 5.0]
    print(f"   Sum: {await engine.sum(items)}")
    print(f"   Avg: {await engine.avg(items)}")
    print(f"   Count: {await engine.count(items)}")
    print()
    
    # 16. Stream Stats
    print("16. STREAM STATS:")
    print("-" * 40)
    
    stream = engine.from_iterable(list(range(100)))
    await stream.filter(lambda x: x % 2 == 0).collect()
    
    stats = stream.stats
    print(f"   Received: {stats.events_received}")
    print(f"   Processed: {stats.events_processed}")
    print(f"   Rate: {stats.events_per_second:.2f}/s")
    print()
    
    # 17. Register Stream
    print("17. REGISTER STREAM:")
    print("-" * 40)
    
    stream = engine.from_iterable([1, 2, 3])
    engine.register_stream("my_stream", stream)
    
    retrieved = engine.get_stream("my_stream")
    print(f"   Registered: {'my_stream' in engine.list_streams()}")
    print(f"   Streams: {engine.list_streams()}")
    print()
    
    # 18. Engine Statistics
    print("18. ENGINE STATISTICS:")
    print("-" * 40)
    
    stats = engine.stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()
    
    # 19. Engine Summary
    print("19. ENGINE SUMMARY:")
    print("-" * 40)
    
    summary = engine.summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()
    
    print("=" * 70)
    print("DEMO COMPLETE - Streaming Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
