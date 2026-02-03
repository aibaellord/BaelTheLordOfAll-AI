#!/usr/bin/env python3
"""
BAEL - Batching Engine
Batch processing for agents.

Features:
- Batch collection
- Size-based batching
- Time-based batching
- Parallel processing
- Retry handling
"""

import asyncio
import hashlib
import json
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (
    Any, Callable, Coroutine, Dict, Generic, Iterator, List, Optional, Set,
    Tuple, Type, TypeVar, Union
)


T = TypeVar('T')
R = TypeVar('R')


# =============================================================================
# ENUMS
# =============================================================================

class BatchStrategy(Enum):
    """Batching strategies."""
    SIZE = "size"
    TIME = "time"
    SIZE_OR_TIME = "size_or_time"
    COUNT = "count"
    ADAPTIVE = "adaptive"


class BatchStatus(Enum):
    """Batch statuses."""
    COLLECTING = "collecting"
    READY = "ready"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class ItemStatus(Enum):
    """Item statuses."""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class ExecutionMode(Enum):
    """Execution modes."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CHUNKED = "chunked"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class BatchItem(Generic[T]):
    """An item in a batch."""
    item_id: str = ""
    data: Optional[T] = None
    status: ItemStatus = ItemStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    added_at: datetime = field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None
    retry_count: int = 0
    
    def __post_init__(self):
        if not self.item_id:
            self.item_id = str(uuid.uuid4())[:8]


@dataclass
class Batch(Generic[T]):
    """A batch of items."""
    batch_id: str = ""
    items: List[BatchItem[T]] = field(default_factory=list)
    status: BatchStatus = BatchStatus.COLLECTING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.batch_id:
            self.batch_id = str(uuid.uuid4())[:8]
    
    @property
    def size(self) -> int:
        return len(self.items)
    
    @property
    def succeeded_count(self) -> int:
        return sum(1 for i in self.items if i.status == ItemStatus.SUCCEEDED)
    
    @property
    def failed_count(self) -> int:
        return sum(1 for i in self.items if i.status == ItemStatus.FAILED)
    
    @property
    def duration_seconds(self) -> float:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0


@dataclass
class BatchConfig:
    """Batch configuration."""
    max_size: int = 100
    max_wait_seconds: float = 10.0
    strategy: BatchStrategy = BatchStrategy.SIZE_OR_TIME
    execution_mode: ExecutionMode = ExecutionMode.PARALLEL
    max_parallel: int = 10
    chunk_size: int = 10
    max_retries: int = 3
    retry_delay_seconds: float = 1.0


@dataclass
class BatchResult(Generic[R]):
    """Batch processing result."""
    batch_id: str = ""
    total_items: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    results: List[R] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0


@dataclass
class BatchStats:
    """Batching statistics."""
    batches_processed: int = 0
    items_processed: int = 0
    items_succeeded: int = 0
    items_failed: int = 0
    avg_batch_size: float = 0.0
    avg_processing_time: float = 0.0


# =============================================================================
# BATCH COLLECTOR
# =============================================================================

class BatchCollector(Generic[T]):
    """Collect items into batches."""
    
    def __init__(
        self,
        max_size: int = 100,
        max_wait_seconds: float = 10.0,
        strategy: BatchStrategy = BatchStrategy.SIZE_OR_TIME
    ):
        self._max_size = max_size
        self._max_wait_seconds = max_wait_seconds
        self._strategy = strategy
        
        self._current_batch: Optional[Batch[T]] = None
        self._ready_batches: List[Batch[T]] = []
        self._lock = asyncio.Lock()
    
    async def add(self, item: T) -> Optional[str]:
        """Add item to current batch."""
        async with self._lock:
            if self._current_batch is None:
                self._current_batch = Batch[T]()
            
            batch_item = BatchItem[T](data=item)
            self._current_batch.items.append(batch_item)
            
            if self._should_flush():
                self._flush()
            
            return batch_item.item_id
    
    def _should_flush(self) -> bool:
        """Check if batch should be flushed."""
        if not self._current_batch:
            return False
        
        if self._strategy == BatchStrategy.SIZE:
            return len(self._current_batch.items) >= self._max_size
        
        elif self._strategy == BatchStrategy.TIME:
            elapsed = (datetime.now() - self._current_batch.created_at).total_seconds()
            return elapsed >= self._max_wait_seconds
        
        elif self._strategy == BatchStrategy.SIZE_OR_TIME:
            if len(self._current_batch.items) >= self._max_size:
                return True
            elapsed = (datetime.now() - self._current_batch.created_at).total_seconds()
            return elapsed >= self._max_wait_seconds
        
        return False
    
    def _flush(self) -> None:
        """Flush current batch."""
        if self._current_batch and self._current_batch.items:
            self._current_batch.status = BatchStatus.READY
            self._ready_batches.append(self._current_batch)
            self._current_batch = None
    
    async def flush(self) -> Optional[Batch[T]]:
        """Force flush current batch."""
        async with self._lock:
            if self._current_batch and self._current_batch.items:
                self._flush()
                return self._ready_batches[-1] if self._ready_batches else None
        return None
    
    async def get_ready_batch(self) -> Optional[Batch[T]]:
        """Get a ready batch."""
        async with self._lock:
            if self._ready_batches:
                return self._ready_batches.pop(0)
            return None
    
    def has_ready_batches(self) -> bool:
        """Check if there are ready batches."""
        return len(self._ready_batches) > 0
    
    def pending_count(self) -> int:
        """Count pending items."""
        count = 0
        if self._current_batch:
            count += len(self._current_batch.items)
        for batch in self._ready_batches:
            count += len(batch.items)
        return count


# =============================================================================
# BATCH PROCESSOR
# =============================================================================

class BatchProcessor(Generic[T, R]):
    """Process batches of items."""
    
    def __init__(
        self,
        processor: Callable[[T], R],
        config: Optional[BatchConfig] = None
    ):
        self._processor = processor
        self._config = config or BatchConfig()
        self._semaphore = asyncio.Semaphore(self._config.max_parallel)
    
    async def process(self, batch: Batch[T]) -> BatchResult[R]:
        """Process a batch."""
        batch.status = BatchStatus.PROCESSING
        batch.started_at = datetime.now()
        
        result = BatchResult[R](
            batch_id=batch.batch_id,
            total_items=len(batch.items)
        )
        
        if self._config.execution_mode == ExecutionMode.SEQUENTIAL:
            await self._process_sequential(batch, result)
        
        elif self._config.execution_mode == ExecutionMode.PARALLEL:
            await self._process_parallel(batch, result)
        
        elif self._config.execution_mode == ExecutionMode.CHUNKED:
            await self._process_chunked(batch, result)
        
        batch.completed_at = datetime.now()
        result.duration_seconds = batch.duration_seconds
        
        if result.failed == 0:
            batch.status = BatchStatus.COMPLETED
        elif result.succeeded == 0:
            batch.status = BatchStatus.FAILED
        else:
            batch.status = BatchStatus.PARTIAL
        
        return result
    
    async def _process_sequential(
        self,
        batch: Batch[T],
        result: BatchResult[R]
    ) -> None:
        """Process items sequentially."""
        for item in batch.items:
            await self._process_item(item, result)
    
    async def _process_parallel(
        self,
        batch: Batch[T],
        result: BatchResult[R]
    ) -> None:
        """Process items in parallel."""
        tasks = [
            self._process_item_with_semaphore(item, result)
            for item in batch.items
        ]
        await asyncio.gather(*tasks)
    
    async def _process_chunked(
        self,
        batch: Batch[T],
        result: BatchResult[R]
    ) -> None:
        """Process items in chunks."""
        for i in range(0, len(batch.items), self._config.chunk_size):
            chunk = batch.items[i:i + self._config.chunk_size]
            tasks = [
                self._process_item_with_semaphore(item, result)
                for item in chunk
            ]
            await asyncio.gather(*tasks)
    
    async def _process_item_with_semaphore(
        self,
        item: BatchItem[T],
        result: BatchResult[R]
    ) -> None:
        """Process item with semaphore."""
        async with self._semaphore:
            await self._process_item(item, result)
    
    async def _process_item(
        self,
        item: BatchItem[T],
        result: BatchResult[R]
    ) -> None:
        """Process a single item."""
        item.status = ItemStatus.PROCESSING
        
        for attempt in range(self._config.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(self._processor):
                    output = await self._processor(item.data)
                else:
                    output = self._processor(item.data)
                
                item.status = ItemStatus.SUCCEEDED
                item.result = output
                item.processed_at = datetime.now()
                
                result.succeeded += 1
                result.results.append(output)
                return
            
            except Exception as e:
                item.retry_count += 1
                item.error = str(e)
                
                if attempt < self._config.max_retries:
                    await asyncio.sleep(self._config.retry_delay_seconds)
        
        item.status = ItemStatus.FAILED
        item.processed_at = datetime.now()
        result.failed += 1
        result.errors.append(item.error or "Unknown error")


# =============================================================================
# BATCH QUEUE
# =============================================================================

class BatchQueue(Generic[T]):
    """Queue for batches."""
    
    def __init__(self):
        self._queue: List[Batch[T]] = []
        self._processing: Dict[str, Batch[T]] = {}
        self._completed: List[Batch[T]] = []
    
    def enqueue(self, batch: Batch[T]) -> str:
        """Enqueue a batch."""
        batch.status = BatchStatus.READY
        self._queue.append(batch)
        return batch.batch_id
    
    def dequeue(self) -> Optional[Batch[T]]:
        """Dequeue a batch."""
        if self._queue:
            batch = self._queue.pop(0)
            batch.status = BatchStatus.PROCESSING
            self._processing[batch.batch_id] = batch
            return batch
        return None
    
    def complete(self, batch_id: str) -> bool:
        """Mark batch as complete."""
        batch = self._processing.get(batch_id)
        
        if batch:
            del self._processing[batch_id]
            self._completed.append(batch)
            return True
        
        return False
    
    def get_pending(self) -> List[Batch[T]]:
        """Get pending batches."""
        return list(self._queue)
    
    def get_processing(self) -> List[Batch[T]]:
        """Get processing batches."""
        return list(self._processing.values())
    
    def get_completed(self) -> List[Batch[T]]:
        """Get completed batches."""
        return list(self._completed)
    
    def queue_size(self) -> int:
        """Get queue size."""
        return len(self._queue)
    
    def processing_count(self) -> int:
        """Get processing count."""
        return len(self._processing)


# =============================================================================
# BATCH BUILDER
# =============================================================================

class BatchBuilder(Generic[T]):
    """Build batches manually."""
    
    def __init__(self):
        self._items: List[BatchItem[T]] = []
        self._metadata: Dict[str, Any] = {}
    
    def add(self, item: T) -> "BatchBuilder[T]":
        """Add an item."""
        self._items.append(BatchItem[T](data=item))
        return self
    
    def add_many(self, items: List[T]) -> "BatchBuilder[T]":
        """Add multiple items."""
        for item in items:
            self.add(item)
        return self
    
    def with_metadata(self, key: str, value: Any) -> "BatchBuilder[T]":
        """Add metadata."""
        self._metadata[key] = value
        return self
    
    def build(self) -> Batch[T]:
        """Build the batch."""
        batch = Batch[T](
            items=list(self._items),
            metadata=dict(self._metadata)
        )
        batch.status = BatchStatus.READY
        self._items.clear()
        self._metadata.clear()
        return batch


# =============================================================================
# BATCHING ENGINE
# =============================================================================

class BatchingEngine:
    """
    Batching Engine for BAEL.
    
    Batch collection and processing.
    """
    
    def __init__(self, config: Optional[BatchConfig] = None):
        self._config = config or BatchConfig()
        
        self._collectors: Dict[str, BatchCollector] = {}
        self._queues: Dict[str, BatchQueue] = {}
        self._processors: Dict[str, BatchProcessor] = {}
        
        self._stats = BatchStats()
        self._results: Dict[str, BatchResult] = {}
    
    # ----- Collector Management -----
    
    def create_collector(
        self,
        name: str,
        max_size: int = 100,
        max_wait_seconds: float = 10.0,
        strategy: BatchStrategy = BatchStrategy.SIZE_OR_TIME
    ) -> BatchCollector:
        """Create a batch collector."""
        collector = BatchCollector(
            max_size=max_size,
            max_wait_seconds=max_wait_seconds,
            strategy=strategy
        )
        self._collectors[name] = collector
        return collector
    
    def get_collector(self, name: str) -> Optional[BatchCollector]:
        """Get a collector."""
        return self._collectors.get(name)
    
    async def add_to_collector(
        self,
        collector_name: str,
        item: Any
    ) -> Optional[str]:
        """Add item to collector."""
        collector = self._collectors.get(collector_name)
        
        if collector:
            return await collector.add(item)
        
        return None
    
    async def flush_collector(
        self,
        collector_name: str
    ) -> Optional[Batch]:
        """Flush a collector."""
        collector = self._collectors.get(collector_name)
        
        if collector:
            return await collector.flush()
        
        return None
    
    # ----- Queue Management -----
    
    def create_queue(self, name: str) -> BatchQueue:
        """Create a batch queue."""
        queue = BatchQueue()
        self._queues[name] = queue
        return queue
    
    def get_queue(self, name: str) -> Optional[BatchQueue]:
        """Get a queue."""
        return self._queues.get(name)
    
    def enqueue_batch(self, queue_name: str, batch: Batch) -> Optional[str]:
        """Enqueue a batch."""
        queue = self._queues.get(queue_name)
        
        if queue:
            return queue.enqueue(batch)
        
        return None
    
    def dequeue_batch(self, queue_name: str) -> Optional[Batch]:
        """Dequeue a batch."""
        queue = self._queues.get(queue_name)
        
        if queue:
            return queue.dequeue()
        
        return None
    
    # ----- Processor Management -----
    
    def register_processor(
        self,
        name: str,
        processor: Callable,
        config: Optional[BatchConfig] = None
    ) -> BatchProcessor:
        """Register a batch processor."""
        batch_processor = BatchProcessor(
            processor=processor,
            config=config or self._config
        )
        self._processors[name] = batch_processor
        return batch_processor
    
    def get_processor(self, name: str) -> Optional[BatchProcessor]:
        """Get a processor."""
        return self._processors.get(name)
    
    # ----- Batch Operations -----
    
    async def process_batch(
        self,
        batch: Batch,
        processor_name: str
    ) -> BatchResult:
        """Process a batch."""
        processor = self._processors.get(processor_name)
        
        if not processor:
            return BatchResult(
                batch_id=batch.batch_id,
                total_items=len(batch.items),
                failed=len(batch.items),
                errors=["Processor not found"]
            )
        
        result = await processor.process(batch)
        
        self._stats.batches_processed += 1
        self._stats.items_processed += result.total_items
        self._stats.items_succeeded += result.succeeded
        self._stats.items_failed += result.failed
        
        self._results[batch.batch_id] = result
        
        return result
    
    async def process_from_queue(
        self,
        queue_name: str,
        processor_name: str
    ) -> Optional[BatchResult]:
        """Process batch from queue."""
        batch = self.dequeue_batch(queue_name)
        
        if batch:
            result = await self.process_batch(batch, processor_name)
            
            queue = self._queues.get(queue_name)
            if queue:
                queue.complete(batch.batch_id)
            
            return result
        
        return None
    
    async def process_all_from_queue(
        self,
        queue_name: str,
        processor_name: str
    ) -> List[BatchResult]:
        """Process all batches from queue."""
        results = []
        
        while True:
            result = await self.process_from_queue(queue_name, processor_name)
            
            if result:
                results.append(result)
            else:
                break
        
        return results
    
    # ----- Batch Building -----
    
    def builder(self) -> BatchBuilder:
        """Get a batch builder."""
        return BatchBuilder()
    
    def create_batch(self, items: List[Any]) -> Batch:
        """Create a batch from items."""
        return self.builder().add_many(items).build()
    
    # ----- Direct Processing -----
    
    async def process_items(
        self,
        items: List[Any],
        processor: Callable,
        config: Optional[BatchConfig] = None
    ) -> BatchResult:
        """Process items directly."""
        batch = self.create_batch(items)
        
        batch_processor = BatchProcessor(
            processor=processor,
            config=config or self._config
        )
        
        return await batch_processor.process(batch)
    
    async def map(
        self,
        items: List[Any],
        func: Callable,
        parallel: bool = True
    ) -> List[Any]:
        """Map function over items in batches."""
        config = BatchConfig(
            execution_mode=ExecutionMode.PARALLEL if parallel else ExecutionMode.SEQUENTIAL
        )
        
        result = await self.process_items(items, func, config)
        return result.results
    
    # ----- Results -----
    
    def get_result(self, batch_id: str) -> Optional[BatchResult]:
        """Get batch result."""
        return self._results.get(batch_id)
    
    def get_all_results(self) -> List[BatchResult]:
        """Get all results."""
        return list(self._results.values())
    
    def clear_results(self) -> int:
        """Clear results."""
        count = len(self._results)
        self._results.clear()
        return count
    
    # ----- Collector to Queue Pipeline -----
    
    async def collector_to_queue(
        self,
        collector_name: str,
        queue_name: str
    ) -> int:
        """Move ready batches from collector to queue."""
        collector = self._collectors.get(collector_name)
        queue = self._queues.get(queue_name)
        
        if not collector or not queue:
            return 0
        
        count = 0
        
        while collector.has_ready_batches():
            batch = await collector.get_ready_batch()
            if batch:
                queue.enqueue(batch)
                count += 1
        
        return count
    
    # ----- Statistics -----
    
    def get_stats(self) -> BatchStats:
        """Get statistics."""
        stats = self._stats
        
        if stats.batches_processed > 0:
            stats.avg_batch_size = stats.items_processed / stats.batches_processed
        
        return stats
    
    def stats(self) -> Dict[str, Any]:
        """Get stats as dict."""
        s = self.get_stats()
        
        return {
            "batches_processed": s.batches_processed,
            "items_processed": s.items_processed,
            "items_succeeded": s.items_succeeded,
            "items_failed": s.items_failed,
            "avg_batch_size": s.avg_batch_size,
            "collectors": len(self._collectors),
            "queues": len(self._queues),
            "processors": len(self._processors)
        }
    
    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "collectors": list(self._collectors.keys()),
            "queues": list(self._queues.keys()),
            "processors": list(self._processors.keys()),
            "results": len(self._results)
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Batching Engine."""
    print("=" * 70)
    print("BAEL - BATCHING ENGINE DEMO")
    print("Batch Collection & Processing")
    print("=" * 70)
    print()
    
    engine = BatchingEngine()
    
    # 1. Direct Processing
    print("1. DIRECT PROCESSING:")
    print("-" * 40)
    
    items = [1, 2, 3, 4, 5]
    
    async def double(x):
        await asyncio.sleep(0.01)
        return x * 2
    
    result = await engine.process_items(items, double)
    print(f"   Input: {items}")
    print(f"   Output: {result.results}")
    print(f"   Succeeded: {result.succeeded}/{result.total_items}")
    print()
    
    # 2. Map Function
    print("2. MAP FUNCTION:")
    print("-" * 40)
    
    results = await engine.map([1, 2, 3, 4, 5], lambda x: x ** 2, parallel=True)
    print(f"   Squares: {results}")
    print()
    
    # 3. Batch Builder
    print("3. BATCH BUILDER:")
    print("-" * 40)
    
    batch = (
        engine.builder()
        .add("item1")
        .add("item2")
        .add_many(["item3", "item4", "item5"])
        .with_metadata("source", "demo")
        .build()
    )
    
    print(f"   Batch ID: {batch.batch_id}")
    print(f"   Items: {batch.size}")
    print(f"   Metadata: {batch.metadata}")
    print()
    
    # 4. Create Collector
    print("4. BATCH COLLECTOR:")
    print("-" * 40)
    
    engine.create_collector(
        "events",
        max_size=5,
        max_wait_seconds=1.0,
        strategy=BatchStrategy.SIZE_OR_TIME
    )
    
    for i in range(7):
        await engine.add_to_collector("events", {"event": i})
    
    collector = engine.get_collector("events")
    print(f"   Added 7 items to collector")
    print(f"   Pending: {collector.pending_count()}")
    print(f"   Ready batches: {collector.has_ready_batches()}")
    print()
    
    # 5. Flush Collector
    print("5. FLUSH COLLECTOR:")
    print("-" * 40)
    
    await engine.flush_collector("events")
    
    print(f"   Flushed collector")
    print(f"   Pending: {collector.pending_count()}")
    print(f"   Ready batches: {collector.has_ready_batches()}")
    print()
    
    # 6. Create Queue
    print("6. BATCH QUEUE:")
    print("-" * 40)
    
    engine.create_queue("processing")
    
    batch1 = engine.create_batch([1, 2, 3])
    batch2 = engine.create_batch([4, 5, 6])
    
    engine.enqueue_batch("processing", batch1)
    engine.enqueue_batch("processing", batch2)
    
    queue = engine.get_queue("processing")
    print(f"   Queue size: {queue.queue_size()}")
    print()
    
    # 7. Register Processor
    print("7. REGISTER PROCESSOR:")
    print("-" * 40)
    
    engine.register_processor(
        "square",
        lambda x: x ** 2,
        BatchConfig(execution_mode=ExecutionMode.PARALLEL)
    )
    
    print(f"   Registered 'square' processor")
    print()
    
    # 8. Process from Queue
    print("8. PROCESS FROM QUEUE:")
    print("-" * 40)
    
    result = await engine.process_from_queue("processing", "square")
    print(f"   Batch: {result.batch_id}")
    print(f"   Results: {result.results}")
    print(f"   Duration: {result.duration_seconds:.4f}s")
    print()
    
    # 9. Process All from Queue
    print("9. PROCESS ALL FROM QUEUE:")
    print("-" * 40)
    
    engine.enqueue_batch("processing", engine.create_batch([7, 8, 9]))
    engine.enqueue_batch("processing", engine.create_batch([10, 11, 12]))
    
    results = await engine.process_all_from_queue("processing", "square")
    print(f"   Processed {len(results)} batches")
    for r in results:
        print(f"   - {r.results}")
    print()
    
    # 10. Collector to Queue Pipeline
    print("10. COLLECTOR TO QUEUE PIPELINE:")
    print("-" * 40)
    
    engine.create_collector("pipeline", max_size=3)
    engine.create_queue("pipeline_queue")
    
    for i in range(10):
        await engine.add_to_collector("pipeline", i)
    
    await engine.flush_collector("pipeline")
    
    moved = await engine.collector_to_queue("pipeline", "pipeline_queue")
    print(f"   Moved {moved} batches to queue")
    
    pq = engine.get_queue("pipeline_queue")
    print(f"   Queue size: {pq.queue_size()}")
    print()
    
    # 11. Error Handling with Retries
    print("11. ERROR HANDLING:")
    print("-" * 40)
    
    fail_count = {"value": 0}
    
    async def sometimes_fail(x):
        fail_count["value"] += 1
        if fail_count["value"] % 3 == 0:
            raise Exception("Simulated failure")
        return x * 2
    
    engine.register_processor(
        "unreliable",
        sometimes_fail,
        BatchConfig(max_retries=2)
    )
    
    batch = engine.create_batch([1, 2, 3, 4, 5])
    result = await engine.process_batch(batch, "unreliable")
    
    print(f"   Succeeded: {result.succeeded}")
    print(f"   Failed: {result.failed}")
    print(f"   Errors: {len(result.errors)}")
    print()
    
    # 12. Sequential vs Parallel
    print("12. EXECUTION MODES:")
    print("-" * 40)
    
    async def slow_process(x):
        await asyncio.sleep(0.05)
        return x
    
    items = list(range(10))
    
    start = time.time()
    engine.register_processor("seq", slow_process, BatchConfig(execution_mode=ExecutionMode.SEQUENTIAL))
    batch = engine.create_batch(items[:5])
    await engine.process_batch(batch, "seq")
    seq_time = time.time() - start
    
    start = time.time()
    engine.register_processor("par", slow_process, BatchConfig(execution_mode=ExecutionMode.PARALLEL))
    batch = engine.create_batch(items[:5])
    await engine.process_batch(batch, "par")
    par_time = time.time() - start
    
    print(f"   Sequential: {seq_time:.3f}s")
    print(f"   Parallel: {par_time:.3f}s")
    print(f"   Speedup: {seq_time / par_time:.2f}x")
    print()
    
    # 13. Chunked Processing
    print("13. CHUNKED PROCESSING:")
    print("-" * 40)
    
    engine.register_processor(
        "chunked",
        lambda x: x,
        BatchConfig(execution_mode=ExecutionMode.CHUNKED, chunk_size=3)
    )
    
    batch = engine.create_batch(list(range(10)))
    result = await engine.process_batch(batch, "chunked")
    print(f"   Processed {result.total_items} items in chunks of 3")
    print(f"   Results: {result.results}")
    print()
    
    # 14. Get Results
    print("14. STORED RESULTS:")
    print("-" * 40)
    
    all_results = engine.get_all_results()
    print(f"   Total results stored: {len(all_results)}")
    
    for r in all_results[-3:]:
        print(f"   - Batch {r.batch_id}: {r.succeeded}/{r.total_items} succeeded")
    print()
    
    # 15. Statistics
    print("15. STATISTICS:")
    print("-" * 40)
    
    stats = engine.stats()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"   {key}: {value:.2f}")
        else:
            print(f"   {key}: {value}")
    print()
    
    # 16. Summary
    print("16. ENGINE SUMMARY:")
    print("-" * 40)
    
    summary = engine.summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()
    
    print("=" * 70)
    print("DEMO COMPLETE - Batching Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
