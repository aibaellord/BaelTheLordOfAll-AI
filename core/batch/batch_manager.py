#!/usr/bin/env python3
"""
BAEL - Batch Manager
Advanced batch processing for AI agent operations.

Features:
- Batch creation and management
- Batch scheduling
- Batch execution
- Batch tracking
- Retry handling
- Progress monitoring
- Error aggregation
- Batch splitting
- Batch merging
- Parallel processing
"""

import asyncio
import copy
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Awaitable, Callable, Dict, Generic, Iterator, List,
                    Optional, Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')
R = TypeVar('R')
K = TypeVar('K')


# =============================================================================
# ENUMS
# =============================================================================

class BatchStatus(Enum):
    """Batch status."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"


class BatchPriority(Enum):
    """Batch priority."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class ItemStatus(Enum):
    """Batch item status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class SplitStrategy(Enum):
    """Batch split strategy."""
    FIXED_SIZE = "fixed_size"
    FIXED_COUNT = "fixed_count"
    BY_KEY = "by_key"
    ADAPTIVE = "adaptive"


class RetryPolicy(Enum):
    """Retry policy."""
    NONE = "none"
    IMMEDIATE = "immediate"
    EXPONENTIAL = "exponential"
    FIXED_DELAY = "fixed_delay"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class BatchConfig:
    """Batch configuration."""
    max_batch_size: int = 1000
    max_concurrent: int = 10
    timeout_seconds: int = 300
    retry_policy: RetryPolicy = RetryPolicy.EXPONENTIAL
    max_retries: int = 3
    initial_delay_ms: int = 100
    max_delay_ms: int = 10000


@dataclass
class BatchItem(Generic[T]):
    """Batch item."""
    item_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    data: Optional[T] = None
    status: ItemStatus = ItemStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    attempts: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchResult:
    """Batch result."""
    batch_id: str = ""
    status: BatchStatus = BatchStatus.PENDING
    total_items: int = 0
    completed_items: int = 0
    failed_items: int = 0
    skipped_items: int = 0
    results: List[Any] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0


@dataclass
class BatchStats:
    """Batch statistics."""
    total_batches: int = 0
    completed_batches: int = 0
    failed_batches: int = 0
    total_items_processed: int = 0
    total_items_failed: int = 0
    average_batch_time_ms: float = 0.0
    average_item_time_ms: float = 0.0


# =============================================================================
# BATCH
# =============================================================================

class Batch(Generic[T]):
    """Batch of items."""

    def __init__(
        self,
        batch_id: Optional[str] = None,
        priority: BatchPriority = BatchPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.batch_id = batch_id or str(uuid.uuid4())
        self.priority = priority
        self.metadata = metadata or {}

        self._items: Dict[str, BatchItem[T]] = {}
        self._item_order: List[str] = []
        self._status = BatchStatus.PENDING
        self._created_at = datetime.utcnow()
        self._started_at: Optional[datetime] = None
        self._completed_at: Optional[datetime] = None

    def add_item(
        self,
        data: T,
        item_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> BatchItem[T]:
        """Add item to batch."""
        item = BatchItem(
            item_id=item_id or str(uuid.uuid4()),
            data=data,
            metadata=metadata or {}
        )
        self._items[item.item_id] = item
        self._item_order.append(item.item_id)
        return item

    def add_items(
        self,
        items: List[T]
    ) -> List[BatchItem[T]]:
        """Add multiple items."""
        return [self.add_item(item) for item in items]

    def get_item(self, item_id: str) -> Optional[BatchItem[T]]:
        """Get item by ID."""
        return self._items.get(item_id)

    def items(self) -> Iterator[BatchItem[T]]:
        """Iterate items."""
        for item_id in self._item_order:
            yield self._items[item_id]

    def pending_items(self) -> Iterator[BatchItem[T]]:
        """Get pending items."""
        for item in self.items():
            if item.status == ItemStatus.PENDING:
                yield item

    def failed_items(self) -> Iterator[BatchItem[T]]:
        """Get failed items."""
        for item in self.items():
            if item.status == ItemStatus.FAILED:
                yield item

    @property
    def status(self) -> BatchStatus:
        """Get batch status."""
        return self._status

    @status.setter
    def status(self, value: BatchStatus) -> None:
        """Set batch status."""
        self._status = value
        if value == BatchStatus.RUNNING and not self._started_at:
            self._started_at = datetime.utcnow()
        elif value in (BatchStatus.COMPLETED, BatchStatus.FAILED, BatchStatus.PARTIAL):
            self._completed_at = datetime.utcnow()

    def size(self) -> int:
        """Get batch size."""
        return len(self._items)

    def completed_count(self) -> int:
        """Get completed count."""
        return sum(1 for i in self.items() if i.status == ItemStatus.COMPLETED)

    def failed_count(self) -> int:
        """Get failed count."""
        return sum(1 for i in self.items() if i.status == ItemStatus.FAILED)

    def progress(self) -> float:
        """Get progress (0.0 - 1.0)."""
        if not self._items:
            return 0.0
        processed = self.completed_count() + self.failed_count()
        return processed / len(self._items)

    def to_result(self) -> BatchResult:
        """Convert to batch result."""
        results = []
        errors = []

        for item in self.items():
            if item.result is not None:
                results.append(item.result)
            if item.error:
                errors.append(item.error)

        duration_ms = 0.0
        if self._started_at and self._completed_at:
            duration_ms = (
                self._completed_at - self._started_at
            ).total_seconds() * 1000

        return BatchResult(
            batch_id=self.batch_id,
            status=self._status,
            total_items=len(self._items),
            completed_items=self.completed_count(),
            failed_items=self.failed_count(),
            results=results,
            errors=errors,
            started_at=self._started_at,
            completed_at=self._completed_at,
            duration_ms=duration_ms
        )


# =============================================================================
# BATCH PROCESSOR
# =============================================================================

class BatchProcessor(ABC, Generic[T, R]):
    """Abstract batch processor."""

    @abstractmethod
    async def process_item(
        self,
        item: BatchItem[T]
    ) -> R:
        """Process single item."""
        pass

    async def process_batch(
        self,
        batch: Batch[T],
        config: BatchConfig
    ) -> BatchResult:
        """Process entire batch."""
        batch.status = BatchStatus.RUNNING

        semaphore = asyncio.Semaphore(config.max_concurrent)

        async def process_with_semaphore(item: BatchItem[T]) -> None:
            async with semaphore:
                await self._process_item_with_retry(item, config)

        tasks = [
            process_with_semaphore(item)
            for item in batch.pending_items()
        ]

        try:
            await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=config.timeout_seconds
            )
        except asyncio.TimeoutError:
            pass

        # Determine final status
        if batch.failed_count() == 0:
            batch.status = BatchStatus.COMPLETED
        elif batch.completed_count() == 0:
            batch.status = BatchStatus.FAILED
        else:
            batch.status = BatchStatus.PARTIAL

        return batch.to_result()

    async def _process_item_with_retry(
        self,
        item: BatchItem[T],
        config: BatchConfig
    ) -> None:
        """Process item with retry."""
        delay_ms = config.initial_delay_ms

        while item.attempts < config.max_retries + 1:
            item.attempts += 1
            item.status = ItemStatus.PROCESSING
            item.started_at = datetime.utcnow()

            try:
                item.result = await self.process_item(item)
                item.status = ItemStatus.COMPLETED
                item.completed_at = datetime.utcnow()
                return
            except Exception as e:
                item.error = str(e)

                if item.attempts >= config.max_retries + 1:
                    item.status = ItemStatus.FAILED
                    item.completed_at = datetime.utcnow()
                    return

                # Wait before retry
                if config.retry_policy == RetryPolicy.IMMEDIATE:
                    pass
                elif config.retry_policy == RetryPolicy.FIXED_DELAY:
                    await asyncio.sleep(delay_ms / 1000)
                elif config.retry_policy == RetryPolicy.EXPONENTIAL:
                    await asyncio.sleep(delay_ms / 1000)
                    delay_ms = min(delay_ms * 2, config.max_delay_ms)

        item.status = ItemStatus.FAILED


class FunctionProcessor(BatchProcessor[T, R]):
    """Function-based processor."""

    def __init__(self, func: Callable[[T], Awaitable[R]]):
        self._func = func

    async def process_item(self, item: BatchItem[T]) -> R:
        """Process item using function."""
        return await self._func(item.data)


# =============================================================================
# BATCH SPLITTER
# =============================================================================

class BatchSplitter(Generic[T]):
    """Split batches into smaller batches."""

    def split_fixed_size(
        self,
        batch: Batch[T],
        size: int
    ) -> List[Batch[T]]:
        """Split by fixed size."""
        result: List[Batch[T]] = []
        current_batch: Optional[Batch[T]] = None

        for item in batch.items():
            if current_batch is None or current_batch.size() >= size:
                current_batch = Batch[T](
                    priority=batch.priority,
                    metadata=batch.metadata.copy()
                )
                result.append(current_batch)

            current_batch.add_item(
                item.data,
                item_id=item.item_id,
                metadata=item.metadata
            )

        return result

    def split_fixed_count(
        self,
        batch: Batch[T],
        count: int
    ) -> List[Batch[T]]:
        """Split into fixed number of batches."""
        if batch.size() == 0 or count <= 0:
            return []

        size = max(1, batch.size() // count)
        return self.split_fixed_size(batch, size)

    def split_by_key(
        self,
        batch: Batch[T],
        key_func: Callable[[T], K]
    ) -> Dict[K, Batch[T]]:
        """Split by key function."""
        result: Dict[K, Batch[T]] = {}

        for item in batch.items():
            key = key_func(item.data)

            if key not in result:
                result[key] = Batch[T](
                    priority=batch.priority,
                    metadata=batch.metadata.copy()
                )

            result[key].add_item(
                item.data,
                item_id=item.item_id,
                metadata=item.metadata
            )

        return result


# =============================================================================
# BATCH MERGER
# =============================================================================

class BatchMerger(Generic[T]):
    """Merge batches together."""

    def merge(
        self,
        batches: List[Batch[T]],
        priority: Optional[BatchPriority] = None
    ) -> Batch[T]:
        """Merge multiple batches."""
        # Use highest priority if not specified
        if priority is None:
            priority = max(b.priority for b in batches) if batches else BatchPriority.NORMAL

        merged = Batch[T](priority=priority)

        for batch in batches:
            for item in batch.items():
                merged.add_item(
                    item.data,
                    item_id=item.item_id,
                    metadata=item.metadata
                )

        return merged

    def merge_results(
        self,
        results: List[BatchResult]
    ) -> BatchResult:
        """Merge batch results."""
        if not results:
            return BatchResult()

        merged = BatchResult(
            batch_id=str(uuid.uuid4()),
            total_items=sum(r.total_items for r in results),
            completed_items=sum(r.completed_items for r in results),
            failed_items=sum(r.failed_items for r in results),
            started_at=min(
                (r.started_at for r in results if r.started_at),
                default=None
            ),
            completed_at=max(
                (r.completed_at for r in results if r.completed_at),
                default=None
            ),
            duration_ms=sum(r.duration_ms for r in results)
        )

        for result in results:
            merged.results.extend(result.results)
            merged.errors.extend(result.errors)

        # Determine status
        if merged.failed_items == 0:
            merged.status = BatchStatus.COMPLETED
        elif merged.completed_items == 0:
            merged.status = BatchStatus.FAILED
        else:
            merged.status = BatchStatus.PARTIAL

        return merged


# =============================================================================
# BATCH QUEUE
# =============================================================================

class BatchQueue(Generic[T]):
    """Priority queue for batches."""

    def __init__(self, max_size: int = 1000):
        self._max_size = max_size
        self._queues: Dict[BatchPriority, List[Batch[T]]] = {
            p: [] for p in BatchPriority
        }
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Event()

    async def enqueue(self, batch: Batch[T]) -> bool:
        """Add batch to queue."""
        async with self._lock:
            total = sum(len(q) for q in self._queues.values())
            if total >= self._max_size:
                return False

            batch.status = BatchStatus.QUEUED
            self._queues[batch.priority].append(batch)
            self._not_empty.set()
            return True

    async def dequeue(self) -> Optional[Batch[T]]:
        """Get next batch from queue."""
        while True:
            async with self._lock:
                # Check from highest to lowest priority
                for priority in reversed(list(BatchPriority)):
                    if self._queues[priority]:
                        return self._queues[priority].pop(0)

                # Check if all empty
                if all(len(q) == 0 for q in self._queues.values()):
                    self._not_empty.clear()

            # Wait for items
            await self._not_empty.wait()

    async def peek(self) -> Optional[Batch[T]]:
        """Peek at next batch without removing."""
        async with self._lock:
            for priority in reversed(list(BatchPriority)):
                if self._queues[priority]:
                    return self._queues[priority][0]
            return None

    async def size(self) -> int:
        """Get total queue size."""
        async with self._lock:
            return sum(len(q) for q in self._queues.values())

    async def size_by_priority(self, priority: BatchPriority) -> int:
        """Get size by priority."""
        async with self._lock:
            return len(self._queues[priority])

    async def clear(self) -> int:
        """Clear queue."""
        async with self._lock:
            total = sum(len(q) for q in self._queues.values())
            for q in self._queues.values():
                q.clear()
            self._not_empty.clear()
            return total


# =============================================================================
# BATCH SCHEDULER
# =============================================================================

class BatchScheduler(Generic[T]):
    """Batch scheduler."""

    def __init__(self):
        self._scheduled: Dict[str, Tuple[datetime, Batch[T]]] = {}
        self._lock = asyncio.Lock()

    async def schedule(
        self,
        batch: Batch[T],
        run_at: datetime
    ) -> str:
        """Schedule batch for future execution."""
        async with self._lock:
            schedule_id = str(uuid.uuid4())
            self._scheduled[schedule_id] = (run_at, batch)
            return schedule_id

    async def schedule_delay(
        self,
        batch: Batch[T],
        delay: timedelta
    ) -> str:
        """Schedule batch with delay."""
        run_at = datetime.utcnow() + delay
        return await self.schedule(batch, run_at)

    async def cancel(self, schedule_id: str) -> bool:
        """Cancel scheduled batch."""
        async with self._lock:
            if schedule_id in self._scheduled:
                del self._scheduled[schedule_id]
                return True
            return False

    async def get_due(self) -> List[Tuple[str, Batch[T]]]:
        """Get batches due for execution."""
        now = datetime.utcnow()
        due = []

        async with self._lock:
            to_remove = []
            for schedule_id, (run_at, batch) in self._scheduled.items():
                if run_at <= now:
                    due.append((schedule_id, batch))
                    to_remove.append(schedule_id)

            for schedule_id in to_remove:
                del self._scheduled[schedule_id]

        return due

    async def pending_count(self) -> int:
        """Get pending scheduled count."""
        async with self._lock:
            return len(self._scheduled)


# =============================================================================
# BATCH MANAGER
# =============================================================================

class BatchManager:
    """
    Batch Manager for BAEL.

    Advanced batch processing.
    """

    def __init__(self, config: Optional[BatchConfig] = None):
        self.config = config or BatchConfig()

        self._batches: Dict[str, Batch] = {}
        self._results: Dict[str, BatchResult] = {}
        self._queue: BatchQueue = BatchQueue()
        self._scheduler: BatchScheduler = BatchScheduler()
        self._splitter: BatchSplitter = BatchSplitter()
        self._merger: BatchMerger = BatchMerger()

        self._stats = BatchStats()
        self._batch_times: List[float] = []
        self._item_times: List[float] = []
        self._lock = asyncio.Lock()

        self._running = False
        self._worker_task: Optional[asyncio.Task] = None

    # -------------------------------------------------------------------------
    # BATCH CREATION
    # -------------------------------------------------------------------------

    async def create_batch(
        self,
        items: Optional[List[Any]] = None,
        priority: BatchPriority = BatchPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Batch:
        """Create new batch."""
        batch = Batch(priority=priority, metadata=metadata)

        if items:
            batch.add_items(items)

        async with self._lock:
            self._batches[batch.batch_id] = batch
            self._stats.total_batches += 1

        return batch

    async def get_batch(self, batch_id: str) -> Optional[Batch]:
        """Get batch by ID."""
        async with self._lock:
            return self._batches.get(batch_id)

    async def delete_batch(self, batch_id: str) -> bool:
        """Delete batch."""
        async with self._lock:
            if batch_id in self._batches:
                del self._batches[batch_id]
                return True
            return False

    # -------------------------------------------------------------------------
    # BATCH PROCESSING
    # -------------------------------------------------------------------------

    async def process_batch(
        self,
        batch: Batch,
        processor: Callable[[Any], Awaitable[Any]]
    ) -> BatchResult:
        """Process batch with function."""
        func_processor = FunctionProcessor(processor)

        start_time = time.time()
        result = await func_processor.process_batch(batch, self.config)
        duration_ms = (time.time() - start_time) * 1000

        async with self._lock:
            self._results[batch.batch_id] = result

            if result.status == BatchStatus.COMPLETED:
                self._stats.completed_batches += 1
            elif result.status == BatchStatus.FAILED:
                self._stats.failed_batches += 1

            self._stats.total_items_processed += result.completed_items
            self._stats.total_items_failed += result.failed_items

            self._batch_times.append(duration_ms)
            if result.completed_items > 0:
                item_time = duration_ms / result.completed_items
                self._item_times.append(item_time)

            self._update_averages()

        return result

    async def process_items(
        self,
        items: List[Any],
        processor: Callable[[Any], Awaitable[Any]],
        priority: BatchPriority = BatchPriority.NORMAL
    ) -> BatchResult:
        """Process items as batch."""
        batch = await self.create_batch(items, priority)
        return await self.process_batch(batch, processor)

    # -------------------------------------------------------------------------
    # QUEUE OPERATIONS
    # -------------------------------------------------------------------------

    async def enqueue(
        self,
        batch: Batch,
        processor: Callable[[Any], Awaitable[Any]]
    ) -> bool:
        """Enqueue batch for processing."""
        # Store processor reference
        batch.metadata["_processor"] = processor
        return await self._queue.enqueue(batch)

    async def queue_size(self) -> int:
        """Get queue size."""
        return await self._queue.size()

    async def start_worker(self) -> None:
        """Start batch worker."""
        if self._running:
            return

        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop())

    async def stop_worker(self) -> None:
        """Stop batch worker."""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

    async def _worker_loop(self) -> None:
        """Worker loop."""
        while self._running:
            # Check scheduled batches
            due = await self._scheduler.get_due()
            for schedule_id, batch in due:
                await self._queue.enqueue(batch)

            # Process queue
            try:
                batch = await asyncio.wait_for(
                    self._queue.dequeue(),
                    timeout=1.0
                )

                processor = batch.metadata.get("_processor")
                if processor:
                    await self.process_batch(batch, processor)
            except asyncio.TimeoutError:
                pass

    # -------------------------------------------------------------------------
    # SCHEDULING
    # -------------------------------------------------------------------------

    async def schedule_batch(
        self,
        batch: Batch,
        run_at: datetime,
        processor: Callable[[Any], Awaitable[Any]]
    ) -> str:
        """Schedule batch for future execution."""
        batch.metadata["_processor"] = processor
        return await self._scheduler.schedule(batch, run_at)

    async def schedule_batch_delay(
        self,
        batch: Batch,
        delay: timedelta,
        processor: Callable[[Any], Awaitable[Any]]
    ) -> str:
        """Schedule batch with delay."""
        batch.metadata["_processor"] = processor
        return await self._scheduler.schedule_delay(batch, delay)

    async def cancel_scheduled(self, schedule_id: str) -> bool:
        """Cancel scheduled batch."""
        return await self._scheduler.cancel(schedule_id)

    # -------------------------------------------------------------------------
    # SPLITTING AND MERGING
    # -------------------------------------------------------------------------

    async def split_batch(
        self,
        batch: Batch,
        size: int
    ) -> List[Batch]:
        """Split batch by size."""
        return self._splitter.split_fixed_size(batch, size)

    async def split_batch_count(
        self,
        batch: Batch,
        count: int
    ) -> List[Batch]:
        """Split batch into count parts."""
        return self._splitter.split_fixed_count(batch, count)

    async def merge_batches(
        self,
        batches: List[Batch],
        priority: Optional[BatchPriority] = None
    ) -> Batch:
        """Merge batches."""
        merged = self._merger.merge(batches, priority)

        async with self._lock:
            self._batches[merged.batch_id] = merged

        return merged

    async def merge_results(
        self,
        batch_ids: List[str]
    ) -> BatchResult:
        """Merge batch results."""
        async with self._lock:
            results = [
                self._results[bid]
                for bid in batch_ids
                if bid in self._results
            ]

        return self._merger.merge_results(results)

    # -------------------------------------------------------------------------
    # RESULTS
    # -------------------------------------------------------------------------

    async def get_result(self, batch_id: str) -> Optional[BatchResult]:
        """Get batch result."""
        async with self._lock:
            return self._results.get(batch_id)

    async def wait_for_result(
        self,
        batch_id: str,
        timeout: Optional[float] = None
    ) -> Optional[BatchResult]:
        """Wait for batch result."""
        start = time.time()

        while True:
            async with self._lock:
                if batch_id in self._results:
                    return self._results[batch_id]

            if timeout and (time.time() - start) > timeout:
                return None

            await asyncio.sleep(0.1)

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def _update_averages(self) -> None:
        """Update average times."""
        if self._batch_times:
            self._stats.average_batch_time_ms = (
                sum(self._batch_times) / len(self._batch_times)
            )
        if self._item_times:
            self._stats.average_item_time_ms = (
                sum(self._item_times) / len(self._item_times)
            )

    async def stats(self) -> BatchStats:
        """Get batch stats."""
        async with self._lock:
            return copy.copy(self._stats)

    async def batch_count(self) -> int:
        """Get total batch count."""
        async with self._lock:
            return len(self._batches)

    async def pending_count(self) -> int:
        """Get pending count."""
        async with self._lock:
            return sum(
                1 for b in self._batches.values()
                if b.status in (BatchStatus.PENDING, BatchStatus.QUEUED)
            )


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Batch Manager."""
    print("=" * 70)
    print("BAEL - BATCH MANAGER DEMO")
    print("Advanced Batch Processing for AI Agents")
    print("=" * 70)
    print()

    manager = BatchManager(BatchConfig(
        max_concurrent=5,
        max_retries=2
    ))

    # 1. Create Batch
    print("1. CREATE BATCH:")
    print("-" * 40)

    items = list(range(1, 11))
    batch = await manager.create_batch(
        items,
        priority=BatchPriority.HIGH
    )

    print(f"   Batch ID: {batch.batch_id[:8]}...")
    print(f"   Items: {batch.size()}")
    print(f"   Priority: {batch.priority.name}")
    print()

    # 2. Process Batch
    print("2. PROCESS BATCH:")
    print("-" * 40)

    async def process_item(item):
        await asyncio.sleep(0.05)
        return item * 2

    result = await manager.process_batch(batch, process_item)

    print(f"   Status: {result.status.value}")
    print(f"   Completed: {result.completed_items}/{result.total_items}")
    print(f"   Duration: {result.duration_ms:.2f}ms")
    print(f"   Results: {result.results[:5]}...")
    print()

    # 3. Split Batch
    print("3. SPLIT BATCH:")
    print("-" * 40)

    large_batch = await manager.create_batch(list(range(100)))
    splits = await manager.split_batch(large_batch, 25)

    print(f"   Original size: {large_batch.size()}")
    print(f"   Split count: {len(splits)}")
    print(f"   Split sizes: {[s.size() for s in splits]}")
    print()

    # 4. Merge Batches
    print("4. MERGE BATCHES:")
    print("-" * 40)

    batch1 = await manager.create_batch([1, 2, 3])
    batch2 = await manager.create_batch([4, 5, 6])
    merged = await manager.merge_batches([batch1, batch2])

    print(f"   Batch 1 size: {batch1.size()}")
    print(f"   Batch 2 size: {batch2.size()}")
    print(f"   Merged size: {merged.size()}")
    print()

    # 5. Process With Errors
    print("5. PROCESS WITH ERRORS:")
    print("-" * 40)

    error_batch = await manager.create_batch(list(range(10)))

    async def flaky_processor(item):
        if item % 3 == 0:
            raise ValueError(f"Error on {item}")
        return item

    result = await manager.process_batch(error_batch, flaky_processor)

    print(f"   Status: {result.status.value}")
    print(f"   Completed: {result.completed_items}")
    print(f"   Failed: {result.failed_items}")
    print(f"   Errors: {len(result.errors)}")
    print()

    # 6. Queue Operations
    print("6. QUEUE OPERATIONS:")
    print("-" * 40)

    queue_batch = await manager.create_batch([1, 2, 3])
    enqueued = await manager.enqueue(queue_batch, process_item)

    print(f"   Enqueued: {enqueued}")
    print(f"   Queue size: {await manager.queue_size()}")
    print()

    # 7. Priority Processing
    print("7. PRIORITY PROCESSING:")
    print("-" * 40)

    low = await manager.create_batch([1], priority=BatchPriority.LOW)
    normal = await manager.create_batch([2], priority=BatchPriority.NORMAL)
    high = await manager.create_batch([3], priority=BatchPriority.HIGH)
    critical = await manager.create_batch([4], priority=BatchPriority.CRITICAL)

    await manager.enqueue(low, process_item)
    await manager.enqueue(normal, process_item)
    await manager.enqueue(high, process_item)
    await manager.enqueue(critical, process_item)

    print(f"   Queue size: {await manager.queue_size()}")
    print(f"   Low priority: {low.priority.name}")
    print(f"   Critical priority: {critical.priority.name}")
    print()

    # 8. Batch Progress
    print("8. BATCH PROGRESS:")
    print("-" * 40)

    progress_batch = await manager.create_batch(list(range(5)))

    # Manually set some items complete
    for i, item in enumerate(progress_batch.items()):
        if i < 3:
            item.status = ItemStatus.COMPLETED

    print(f"   Total items: {progress_batch.size()}")
    print(f"   Completed: {progress_batch.completed_count()}")
    print(f"   Progress: {progress_batch.progress():.0%}")
    print()

    # 9. Process Items Directly
    print("9. PROCESS ITEMS DIRECTLY:")
    print("-" * 40)

    result = await manager.process_items(
        [10, 20, 30],
        process_item
    )

    print(f"   Results: {result.results}")
    print(f"   Duration: {result.duration_ms:.2f}ms")
    print()

    # 10. Get Batch
    print("10. GET BATCH:")
    print("-" * 40)

    retrieved = await manager.get_batch(batch.batch_id)
    print(f"   Found: {retrieved is not None}")
    print(f"   Status: {retrieved.status.value if retrieved else 'N/A'}")
    print()

    # 11. Get Result
    print("11. GET RESULT:")
    print("-" * 40)

    result = await manager.get_result(batch.batch_id)
    print(f"   Found: {result is not None}")
    print(f"   Status: {result.status.value if result else 'N/A'}")
    print()

    # 12. Stats
    print("12. STATS:")
    print("-" * 40)

    stats = await manager.stats()
    print(f"   Total batches: {stats.total_batches}")
    print(f"   Completed: {stats.completed_batches}")
    print(f"   Failed: {stats.failed_batches}")
    print(f"   Items processed: {stats.total_items_processed}")
    print(f"   Avg batch time: {stats.average_batch_time_ms:.2f}ms")
    print()

    # 13. Batch Count
    print("13. BATCH COUNT:")
    print("-" * 40)

    print(f"   Total batches: {await manager.batch_count()}")
    print(f"   Pending: {await manager.pending_count()}")
    print()

    # 14. Delete Batch
    print("14. DELETE BATCH:")
    print("-" * 40)

    deleted = await manager.delete_batch(batch.batch_id)
    print(f"   Deleted: {deleted}")
    print(f"   Batch count after: {await manager.batch_count()}")
    print()

    # 15. Scheduled Count
    print("15. SCHEDULED COUNT:")
    print("-" * 40)

    print(f"   Scheduled: {await manager._scheduler.pending_count()}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Batch Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
