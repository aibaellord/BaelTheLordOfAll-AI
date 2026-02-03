#!/usr/bin/env python3
"""
BAEL - Streaming Pipeline Manager
Comprehensive data streaming and pipeline system.

Features:
- Pipeline composition
- Backpressure handling
- Stream transformations
- Windowing operations
- Aggregations
- Parallel processing
- Error handling
- Metrics collection
- Fan-in/fan-out patterns
- Batching and buffering
"""

import asyncio
import hashlib
import json
import logging
import queue
import statistics
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import (Any, AsyncIterator, Callable, Dict, Generic, Iterator,
                    List, Optional, Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')


# =============================================================================
# ENUMS
# =============================================================================

class PipelineState(Enum):
    """Pipeline state."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class WindowType(Enum):
    """Window type."""
    TUMBLING = "tumbling"
    SLIDING = "sliding"
    SESSION = "session"
    COUNT = "count"


class BackpressureStrategy(Enum):
    """Backpressure handling strategy."""
    BUFFER = "buffer"
    DROP_OLDEST = "drop_oldest"
    DROP_NEWEST = "drop_newest"
    BLOCK = "block"
    ERROR = "error"


class ErrorStrategy(Enum):
    """Error handling strategy."""
    FAIL = "fail"
    SKIP = "skip"
    RETRY = "retry"
    DEAD_LETTER = "dead_letter"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class StreamItem(Generic[T]):
    """Item in stream."""
    value: T
    timestamp: datetime = field(default_factory=datetime.utcnow)
    key: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Window(Generic[T]):
    """Window of items."""
    items: List[StreamItem[T]]
    start_time: datetime
    end_time: datetime
    key: Optional[str] = None

    @property
    def size(self) -> int:
        return len(self.items)

    @property
    def values(self) -> List[T]:
        return [item.value for item in self.items]


@dataclass
class PipelineMetrics:
    """Pipeline metrics."""
    items_processed: int = 0
    items_dropped: int = 0
    items_failed: int = 0
    processing_time_ms: float = 0.0
    throughput: float = 0.0
    latency_avg_ms: float = 0.0
    latency_p99_ms: float = 0.0
    backpressure_events: int = 0


@dataclass
class StageConfig:
    """Stage configuration."""
    parallelism: int = 1
    buffer_size: int = 1000
    backpressure: BackpressureStrategy = BackpressureStrategy.BUFFER
    error_strategy: ErrorStrategy = ErrorStrategy.SKIP
    retry_attempts: int = 3
    timeout: Optional[float] = None


# =============================================================================
# STREAM OPERATORS
# =============================================================================

class StreamOperator(ABC, Generic[T, R]):
    """Abstract stream operator."""

    @abstractmethod
    async def process(self, item: StreamItem[T]) -> Optional[StreamItem[R]]:
        """Process single item."""
        pass

    async def process_batch(
        self,
        items: List[StreamItem[T]]
    ) -> List[StreamItem[R]]:
        """Process batch of items."""
        results = []

        for item in items:
            result = await self.process(item)

            if result:
                results.append(result)

        return results


class MapOperator(StreamOperator[T, R]):
    """Map transformation operator."""

    def __init__(self, func: Callable[[T], R]):
        self.func = func

    async def process(self, item: StreamItem[T]) -> Optional[StreamItem[R]]:
        if asyncio.iscoroutinefunction(self.func):
            result = await self.func(item.value)
        else:
            result = self.func(item.value)

        return StreamItem(
            value=result,
            timestamp=item.timestamp,
            key=item.key,
            metadata=item.metadata
        )


class FilterOperator(StreamOperator[T, T]):
    """Filter operator."""

    def __init__(self, predicate: Callable[[T], bool]):
        self.predicate = predicate

    async def process(self, item: StreamItem[T]) -> Optional[StreamItem[T]]:
        if asyncio.iscoroutinefunction(self.predicate):
            should_pass = await self.predicate(item.value)
        else:
            should_pass = self.predicate(item.value)

        return item if should_pass else None


class FlatMapOperator(StreamOperator[T, R]):
    """FlatMap operator."""

    def __init__(self, func: Callable[[T], List[R]]):
        self.func = func

    async def process(self, item: StreamItem[T]) -> Optional[StreamItem[R]]:
        # This returns first item; use process_batch for full expansion
        if asyncio.iscoroutinefunction(self.func):
            results = await self.func(item.value)
        else:
            results = self.func(item.value)

        if results:
            return StreamItem(
                value=results[0],
                timestamp=item.timestamp,
                key=item.key,
                metadata=item.metadata
            )

        return None

    async def process_batch(
        self,
        items: List[StreamItem[T]]
    ) -> List[StreamItem[R]]:
        results = []

        for item in items:
            if asyncio.iscoroutinefunction(self.func):
                expanded = await self.func(item.value)
            else:
                expanded = self.func(item.value)

            for value in expanded:
                results.append(StreamItem(
                    value=value,
                    timestamp=item.timestamp,
                    key=item.key,
                    metadata=item.metadata
                ))

        return results


class KeyByOperator(StreamOperator[T, T]):
    """KeyBy operator for partitioning."""

    def __init__(self, key_func: Callable[[T], str]):
        self.key_func = key_func

    async def process(self, item: StreamItem[T]) -> Optional[StreamItem[T]]:
        if asyncio.iscoroutinefunction(self.key_func):
            key = await self.key_func(item.value)
        else:
            key = self.key_func(item.value)

        return StreamItem(
            value=item.value,
            timestamp=item.timestamp,
            key=key,
            metadata=item.metadata
        )


class AggregateOperator(StreamOperator[T, R]):
    """Aggregate operator."""

    def __init__(
        self,
        init: Callable[[], R],
        accumulate: Callable[[R, T], R],
        emit_on_each: bool = False
    ):
        self.init = init
        self.accumulate = accumulate
        self.emit_on_each = emit_on_each
        self._state: Dict[str, R] = {}

    async def process(self, item: StreamItem[T]) -> Optional[StreamItem[R]]:
        key = item.key or "__default__"

        if key not in self._state:
            self._state[key] = self.init()

        self._state[key] = self.accumulate(self._state[key], item.value)

        if self.emit_on_each:
            return StreamItem(
                value=self._state[key],
                timestamp=item.timestamp,
                key=item.key,
                metadata=item.metadata
            )

        return None

    def get_state(self) -> Dict[str, R]:
        return dict(self._state)


# =============================================================================
# WINDOWING
# =============================================================================

class WindowManager(Generic[T]):
    """Window manager for stream windowing."""

    def __init__(
        self,
        window_type: WindowType,
        size: Union[timedelta, int],
        slide: Optional[Union[timedelta, int]] = None
    ):
        self.window_type = window_type
        self.size = size
        self.slide = slide or size
        self._windows: Dict[str, List[StreamItem[T]]] = defaultdict(list)
        self._window_start: Dict[str, datetime] = {}

    def add(self, item: StreamItem[T]) -> List[Window[T]]:
        """Add item and return completed windows."""
        key = item.key or "__default__"

        if key not in self._window_start:
            self._window_start[key] = item.timestamp

        self._windows[key].append(item)

        return self._check_windows(key, item.timestamp)

    def _check_windows(self, key: str, current_time: datetime) -> List[Window[T]]:
        """Check if windows should be emitted."""
        completed = []

        if self.window_type == WindowType.TUMBLING:
            if isinstance(self.size, timedelta):
                start = self._window_start[key]

                if current_time - start >= self.size:
                    completed.append(Window(
                        items=self._windows[key],
                        start_time=start,
                        end_time=current_time,
                        key=key if key != "__default__" else None
                    ))

                    self._windows[key] = []
                    self._window_start[key] = current_time

        elif self.window_type == WindowType.COUNT:
            if isinstance(self.size, int):
                while len(self._windows[key]) >= self.size:
                    window_items = self._windows[key][:self.size]
                    completed.append(Window(
                        items=window_items,
                        start_time=window_items[0].timestamp,
                        end_time=window_items[-1].timestamp,
                        key=key if key != "__default__" else None
                    ))

                    self._windows[key] = self._windows[key][self.size:]

        return completed

    def flush(self) -> List[Window[T]]:
        """Flush all remaining windows."""
        completed = []

        for key, items in self._windows.items():
            if items:
                completed.append(Window(
                    items=items,
                    start_time=items[0].timestamp,
                    end_time=items[-1].timestamp,
                    key=key if key != "__default__" else None
                ))

        self._windows.clear()
        self._window_start.clear()

        return completed


# =============================================================================
# PIPELINE STAGE
# =============================================================================

class PipelineStage(Generic[T, R]):
    """Pipeline stage."""

    def __init__(
        self,
        name: str,
        operator: StreamOperator[T, R],
        config: Optional[StageConfig] = None
    ):
        self.name = name
        self.operator = operator
        self.config = config or StageConfig()

        self._buffer: asyncio.Queue = asyncio.Queue(maxsize=self.config.buffer_size)
        self._metrics = PipelineMetrics()
        self._running = False
        self._next_stages: List["PipelineStage"] = []
        self._latencies: deque = deque(maxlen=1000)

    def connect(self, stage: "PipelineStage") -> "PipelineStage":
        """Connect to next stage."""
        self._next_stages.append(stage)
        return stage

    async def emit(self, item: StreamItem[T]) -> bool:
        """Emit item to stage."""
        if self.config.backpressure == BackpressureStrategy.BLOCK:
            await self._buffer.put(item)
            return True

        elif self.config.backpressure == BackpressureStrategy.DROP_NEWEST:
            try:
                self._buffer.put_nowait(item)
                return True
            except asyncio.QueueFull:
                self._metrics.items_dropped += 1
                self._metrics.backpressure_events += 1
                return False

        elif self.config.backpressure == BackpressureStrategy.DROP_OLDEST:
            if self._buffer.full():
                try:
                    self._buffer.get_nowait()
                    self._metrics.items_dropped += 1
                    self._metrics.backpressure_events += 1
                except asyncio.QueueEmpty:
                    pass

            await self._buffer.put(item)
            return True

        else:
            try:
                self._buffer.put_nowait(item)
                return True
            except asyncio.QueueFull:
                await self._buffer.put(item)
                return True

    async def run(self) -> None:
        """Run stage processing loop."""
        self._running = True

        while self._running:
            try:
                item = await asyncio.wait_for(
                    self._buffer.get(),
                    timeout=1.0
                )

                start_time = time.time()

                try:
                    result = await self._process_with_retry(item)

                    if result:
                        # Forward to next stages
                        for next_stage in self._next_stages:
                            await next_stage.emit(result)

                    self._metrics.items_processed += 1

                    latency_ms = (time.time() - start_time) * 1000
                    self._latencies.append(latency_ms)
                    self._update_metrics()

                except Exception as e:
                    self._metrics.items_failed += 1

                    if self.config.error_strategy == ErrorStrategy.FAIL:
                        raise

            except asyncio.TimeoutError:
                continue

            except asyncio.CancelledError:
                break

    async def _process_with_retry(
        self,
        item: StreamItem[T]
    ) -> Optional[StreamItem[R]]:
        """Process item with retry logic."""
        attempts = 0
        last_error = None

        while attempts < self.config.retry_attempts:
            try:
                return await self.operator.process(item)

            except Exception as e:
                last_error = e
                attempts += 1

                if attempts < self.config.retry_attempts:
                    await asyncio.sleep(0.1 * attempts)

        if self.config.error_strategy == ErrorStrategy.RETRY:
            raise last_error

        return None

    def _update_metrics(self) -> None:
        """Update metrics."""
        if self._latencies:
            sorted_latencies = sorted(self._latencies)
            self._metrics.latency_avg_ms = statistics.mean(sorted_latencies)

            p99_index = int(len(sorted_latencies) * 0.99)
            self._metrics.latency_p99_ms = sorted_latencies[min(p99_index, len(sorted_latencies) - 1)]

    def stop(self) -> None:
        """Stop stage."""
        self._running = False

    def get_metrics(self) -> PipelineMetrics:
        """Get stage metrics."""
        return self._metrics


# =============================================================================
# STREAM PIPELINE
# =============================================================================

class StreamPipeline:
    """
    Comprehensive Stream Pipeline for BAEL.

    Provides data streaming and pipeline processing.
    """

    def __init__(self, name: str = "pipeline"):
        self.name = name
        self._stages: List[PipelineStage] = []
        self._source_stage: Optional[PipelineStage] = None
        self._state = PipelineState.IDLE
        self._tasks: List[asyncio.Task] = []
        self._metrics = PipelineMetrics()
        self._start_time: Optional[float] = None

    # -------------------------------------------------------------------------
    # PIPELINE BUILDING
    # -------------------------------------------------------------------------

    def source(
        self,
        name: str = "source",
        config: Optional[StageConfig] = None
    ) -> "StreamPipeline":
        """Create source stage."""
        # Identity operator for source
        operator = MapOperator(lambda x: x)
        stage = PipelineStage(name, operator, config)

        self._source_stage = stage
        self._stages.append(stage)

        return self

    def map(
        self,
        func: Callable[[T], R],
        name: str = None,
        config: Optional[StageConfig] = None
    ) -> "StreamPipeline":
        """Add map transformation."""
        stage_name = name or f"map_{len(self._stages)}"
        operator = MapOperator(func)
        stage = PipelineStage(stage_name, operator, config)

        if self._stages:
            self._stages[-1].connect(stage)

        self._stages.append(stage)

        return self

    def filter(
        self,
        predicate: Callable[[T], bool],
        name: str = None,
        config: Optional[StageConfig] = None
    ) -> "StreamPipeline":
        """Add filter transformation."""
        stage_name = name or f"filter_{len(self._stages)}"
        operator = FilterOperator(predicate)
        stage = PipelineStage(stage_name, operator, config)

        if self._stages:
            self._stages[-1].connect(stage)

        self._stages.append(stage)

        return self

    def flat_map(
        self,
        func: Callable[[T], List[R]],
        name: str = None,
        config: Optional[StageConfig] = None
    ) -> "StreamPipeline":
        """Add flatMap transformation."""
        stage_name = name or f"flatmap_{len(self._stages)}"
        operator = FlatMapOperator(func)
        stage = PipelineStage(stage_name, operator, config)

        if self._stages:
            self._stages[-1].connect(stage)

        self._stages.append(stage)

        return self

    def key_by(
        self,
        key_func: Callable[[T], str],
        name: str = None,
        config: Optional[StageConfig] = None
    ) -> "StreamPipeline":
        """Add keyBy partitioning."""
        stage_name = name or f"keyby_{len(self._stages)}"
        operator = KeyByOperator(key_func)
        stage = PipelineStage(stage_name, operator, config)

        if self._stages:
            self._stages[-1].connect(stage)

        self._stages.append(stage)

        return self

    def aggregate(
        self,
        init: Callable[[], R],
        accumulate: Callable[[R, T], R],
        name: str = None,
        emit_on_each: bool = True,
        config: Optional[StageConfig] = None
    ) -> "StreamPipeline":
        """Add aggregation."""
        stage_name = name or f"aggregate_{len(self._stages)}"
        operator = AggregateOperator(init, accumulate, emit_on_each)
        stage = PipelineStage(stage_name, operator, config)

        if self._stages:
            self._stages[-1].connect(stage)

        self._stages.append(stage)

        return self

    def sink(
        self,
        handler: Callable[[T], None],
        name: str = "sink",
        config: Optional[StageConfig] = None
    ) -> "StreamPipeline":
        """Add sink handler."""
        async def sink_func(x):
            if asyncio.iscoroutinefunction(handler):
                await handler(x)
            else:
                handler(x)
            return x

        stage_name = name or f"sink_{len(self._stages)}"
        operator = MapOperator(sink_func)
        stage = PipelineStage(stage_name, operator, config)

        if self._stages:
            self._stages[-1].connect(stage)

        self._stages.append(stage)

        return self

    # -------------------------------------------------------------------------
    # PIPELINE EXECUTION
    # -------------------------------------------------------------------------

    async def start(self) -> None:
        """Start pipeline execution."""
        if self._state == PipelineState.RUNNING:
            return

        self._state = PipelineState.RUNNING
        self._start_time = time.time()

        # Start all stages
        for stage in self._stages:
            task = asyncio.create_task(stage.run())
            self._tasks.append(task)

    async def stop(self) -> None:
        """Stop pipeline execution."""
        self._state = PipelineState.COMPLETED

        # Stop all stages
        for stage in self._stages:
            stage.stop()

        # Cancel tasks
        for task in self._tasks:
            task.cancel()

        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        self._tasks.clear()

    async def emit(self, value: T) -> bool:
        """Emit value to pipeline."""
        if not self._source_stage:
            return False

        item = StreamItem(value=value)
        return await self._source_stage.emit(item)

    async def emit_batch(self, values: List[T]) -> int:
        """Emit batch of values."""
        count = 0

        for value in values:
            if await self.emit(value):
                count += 1

        return count

    async def process_stream(
        self,
        stream: AsyncIterator[T]
    ) -> None:
        """Process async stream."""
        await self.start()

        try:
            async for value in stream:
                await self.emit(value)
        finally:
            await asyncio.sleep(0.5)  # Allow processing to complete
            await self.stop()

    # -------------------------------------------------------------------------
    # METRICS
    # -------------------------------------------------------------------------

    def get_metrics(self) -> Dict[str, PipelineMetrics]:
        """Get metrics for all stages."""
        return {
            stage.name: stage.get_metrics()
            for stage in self._stages
        }

    def get_overall_metrics(self) -> PipelineMetrics:
        """Get aggregated metrics."""
        metrics = PipelineMetrics()

        for stage in self._stages:
            stage_metrics = stage.get_metrics()
            metrics.items_processed += stage_metrics.items_processed
            metrics.items_dropped += stage_metrics.items_dropped
            metrics.items_failed += stage_metrics.items_failed
            metrics.backpressure_events += stage_metrics.backpressure_events

        if self._start_time:
            elapsed = time.time() - self._start_time
            metrics.throughput = metrics.items_processed / max(1, elapsed)

        return metrics

    @property
    def state(self) -> PipelineState:
        """Get pipeline state."""
        return self._state


# =============================================================================
# STREAM BUILDER
# =============================================================================

class StreamBuilder:
    """Fluent builder for stream pipelines."""

    @staticmethod
    def from_source(name: str = "pipeline") -> StreamPipeline:
        """Create pipeline from source."""
        return StreamPipeline(name).source()

    @staticmethod
    async def from_iterator(
        iterator: Iterator[T],
        pipeline: StreamPipeline
    ) -> None:
        """Feed iterator to pipeline."""
        await pipeline.start()

        for item in iterator:
            await pipeline.emit(item)
            await asyncio.sleep(0)  # Yield control

        await asyncio.sleep(0.5)
        await pipeline.stop()

    @staticmethod
    async def from_async_iterator(
        iterator: AsyncIterator[T],
        pipeline: StreamPipeline
    ) -> None:
        """Feed async iterator to pipeline."""
        await pipeline.process_stream(iterator)


# =============================================================================
# PIPELINE MANAGER
# =============================================================================

class PipelineManager:
    """
    Manager for multiple streaming pipelines.
    """

    def __init__(self):
        self._pipelines: Dict[str, StreamPipeline] = {}
        self._stats: Dict[str, int] = defaultdict(int)

    def create_pipeline(self, name: str) -> StreamPipeline:
        """Create new pipeline."""
        pipeline = StreamPipeline(name)
        self._pipelines[name] = pipeline
        self._stats["pipelines_created"] += 1

        return pipeline

    def get_pipeline(self, name: str) -> Optional[StreamPipeline]:
        """Get pipeline by name."""
        return self._pipelines.get(name)

    async def start_pipeline(self, name: str) -> bool:
        """Start pipeline."""
        pipeline = self._pipelines.get(name)

        if pipeline:
            await pipeline.start()
            return True

        return False

    async def stop_pipeline(self, name: str) -> bool:
        """Stop pipeline."""
        pipeline = self._pipelines.get(name)

        if pipeline:
            await pipeline.stop()
            return True

        return False

    async def stop_all(self) -> None:
        """Stop all pipelines."""
        for pipeline in self._pipelines.values():
            await pipeline.stop()

    def list_pipelines(self) -> List[str]:
        """List pipeline names."""
        return list(self._pipelines.keys())

    def get_all_metrics(self) -> Dict[str, Dict[str, PipelineMetrics]]:
        """Get metrics for all pipelines."""
        return {
            name: pipeline.get_metrics()
            for name, pipeline in self._pipelines.items()
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        return {
            "pipeline_count": len(self._pipelines),
            "pipelines_created": self._stats["pipelines_created"],
            "running_pipelines": len([
                p for p in self._pipelines.values()
                if p.state == PipelineState.RUNNING
            ])
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Streaming Pipeline Manager."""
    print("=" * 70)
    print("BAEL - STREAMING PIPELINE MANAGER DEMO")
    print("Comprehensive Data Streaming System")
    print("=" * 70)
    print()

    # 1. Simple Pipeline
    print("1. SIMPLE PIPELINE:")
    print("-" * 40)

    results = []

    pipeline = (
        StreamBuilder.from_source("simple")
        .map(lambda x: x * 2)
        .filter(lambda x: x > 5)
        .sink(lambda x: results.append(x))
    )

    await pipeline.start()

    for i in range(10):
        await pipeline.emit(i)

    await asyncio.sleep(0.2)
    await pipeline.stop()

    print(f"   Input: 0-9")
    print(f"   Transform: x * 2, filter > 5")
    print(f"   Results: {results}")
    print()

    # 2. Map Transformation
    print("2. MAP TRANSFORMATION:")
    print("-" * 40)

    results = []

    pipeline = (
        StreamBuilder.from_source("map_demo")
        .map(lambda x: x ** 2)
        .map(lambda x: f"squared: {x}")
        .sink(lambda x: results.append(x))
    )

    await pipeline.start()

    for i in [1, 2, 3, 4, 5]:
        await pipeline.emit(i)

    await asyncio.sleep(0.2)
    await pipeline.stop()

    print(f"   Results: {results}")
    print()

    # 3. Filter and Transform
    print("3. FILTER AND TRANSFORM:")
    print("-" * 40)

    results = []

    pipeline = (
        StreamBuilder.from_source("filter_demo")
        .filter(lambda x: x % 2 == 0)  # Even numbers
        .map(lambda x: x * 10)
        .sink(lambda x: results.append(x))
    )

    await pipeline.start()

    for i in range(10):
        await pipeline.emit(i)

    await asyncio.sleep(0.2)
    await pipeline.stop()

    print(f"   Input: 0-9")
    print(f"   Even numbers * 10: {results}")
    print()

    # 4. FlatMap
    print("4. FLATMAP:")
    print("-" * 40)

    results = []

    pipeline = (
        StreamBuilder.from_source("flatmap_demo")
        .flat_map(lambda x: [x, x * 2, x * 3])
        .sink(lambda x: results.append(x))
    )

    await pipeline.start()

    for i in [1, 2]:
        await pipeline.emit(i)

    await asyncio.sleep(0.2)
    await pipeline.stop()

    print(f"   Input: [1, 2]")
    print(f"   FlatMap [x, x*2, x*3]: {results}")
    print()

    # 5. KeyBy and Aggregation
    print("5. KEYBY AND AGGREGATION:")
    print("-" * 40)

    results = []

    pipeline = (
        StreamBuilder.from_source("aggregate_demo")
        .key_by(lambda x: "even" if x % 2 == 0 else "odd")
        .aggregate(
            init=lambda: 0,
            accumulate=lambda acc, x: acc + x,
            emit_on_each=True
        )
        .sink(lambda x: results.append(x))
    )

    await pipeline.start()

    for i in range(6):
        await pipeline.emit(i)

    await asyncio.sleep(0.2)
    await pipeline.stop()

    print(f"   Input: 0-5")
    print(f"   Grouped sum results: {results[:6]}")
    print()

    # 6. Async Processing
    print("6. ASYNC PROCESSING:")
    print("-" * 40)

    results = []

    async def async_transform(x):
        await asyncio.sleep(0.01)
        return x * 100

    pipeline = (
        StreamBuilder.from_source("async_demo")
        .map(async_transform)
        .sink(lambda x: results.append(x))
    )

    await pipeline.start()

    for i in range(5):
        await pipeline.emit(i)

    await asyncio.sleep(0.3)
    await pipeline.stop()

    print(f"   Async results: {results}")
    print()

    # 7. Windowing
    print("7. WINDOWING:")
    print("-" * 40)

    window_mgr = WindowManager(
        window_type=WindowType.COUNT,
        size=3
    )

    windows = []

    for i in range(10):
        item = StreamItem(value=i)
        completed = window_mgr.add(item)
        windows.extend(completed)

    windows.extend(window_mgr.flush())

    print(f"   Input: 0-9")
    print(f"   Windows (size=3):")

    for w in windows:
        print(f"      {w.values}")
    print()

    # 8. Backpressure Handling
    print("8. BACKPRESSURE HANDLING:")
    print("-" * 40)

    results = []

    config = StageConfig(
        buffer_size=5,
        backpressure=BackpressureStrategy.DROP_OLDEST
    )

    pipeline = (
        StreamBuilder.from_source("backpressure_demo")
        .map(lambda x: x, config=config)
        .sink(lambda x: results.append(x))
    )

    await pipeline.start()

    # Emit faster than processing
    for i in range(20):
        await pipeline.emit(i)

    await asyncio.sleep(0.3)
    await pipeline.stop()

    metrics = pipeline.get_overall_metrics()
    print(f"   Emitted: 20")
    print(f"   Processed: {metrics.items_processed}")
    print(f"   Dropped: {metrics.items_dropped}")
    print()

    # 9. Pipeline Metrics
    print("9. PIPELINE METRICS:")
    print("-" * 40)

    results = []

    pipeline = (
        StreamBuilder.from_source("metrics_demo")
        .map(lambda x: x * 2)
        .filter(lambda x: x > 0)
        .sink(lambda x: results.append(x))
    )

    await pipeline.start()

    for i in range(100):
        await pipeline.emit(i)

    await asyncio.sleep(0.3)
    await pipeline.stop()

    stage_metrics = pipeline.get_metrics()

    for name, metrics in stage_metrics.items():
        print(f"   {name}:")
        print(f"      Processed: {metrics.items_processed}")
        print(f"      Failed: {metrics.items_failed}")
    print()

    # 10. Pipeline Manager
    print("10. PIPELINE MANAGER:")
    print("-" * 40)

    manager = PipelineManager()

    p1 = manager.create_pipeline("pipeline1")
    p1.source().map(lambda x: x + 1)

    p2 = manager.create_pipeline("pipeline2")
    p2.source().filter(lambda x: x > 0)

    print(f"   Pipelines: {manager.list_pipelines()}")
    print(f"   Stats: {manager.get_stats()}")

    await manager.stop_all()
    print()

    # 11. Complex Pipeline
    print("11. COMPLEX PIPELINE:")
    print("-" * 40)

    word_counts = defaultdict(int)

    def count_words(word):
        word_counts[word] += 1

    pipeline = (
        StreamBuilder.from_source("word_count")
        .flat_map(lambda text: text.lower().split())
        .filter(lambda word: len(word) > 2)
        .sink(count_words)
    )

    await pipeline.start()

    texts = [
        "The quick brown fox",
        "jumps over the lazy dog",
        "The dog barks at the fox"
    ]

    for text in texts:
        await pipeline.emit(text)

    await asyncio.sleep(0.3)
    await pipeline.stop()

    print(f"   Word counts: {dict(word_counts)}")
    print()

    # 12. Error Handling
    print("12. ERROR HANDLING:")
    print("-" * 40)

    results = []
    errors = []

    def risky_transform(x):
        if x == 5:
            raise ValueError("Error on 5!")
        return x * 2

    config = StageConfig(
        error_strategy=ErrorStrategy.SKIP,
        retry_attempts=1
    )

    pipeline = (
        StreamBuilder.from_source("error_demo")
        .map(risky_transform, config=config)
        .sink(lambda x: results.append(x))
    )

    await pipeline.start()

    for i in range(10):
        await pipeline.emit(i)

    await asyncio.sleep(0.3)
    await pipeline.stop()

    metrics = pipeline.get_overall_metrics()
    print(f"   Results (5 should be skipped): {results}")
    print(f"   Failed items: {metrics.items_failed}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Streaming Pipeline Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
