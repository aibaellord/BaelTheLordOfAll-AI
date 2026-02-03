#!/usr/bin/env python3
"""
BAEL - Batch Processor
Advanced batch processing for AI agent operations.

Features:
- Batch job management
- Parallel processing
- Progress tracking
- Error handling
- Retry logic
- Checkpointing
- Rate limiting
- Resource management
- Batch scheduling
- Result aggregation
"""

import asyncio
import copy
import functools
import json
import os
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, AsyncIterator, Awaitable, Callable, Dict, Generic,
                    Iterator, List, Optional, Set, Tuple, TypeVar)

T = TypeVar('T')
R = TypeVar('R')


# =============================================================================
# ENUMS
# =============================================================================

class BatchState(Enum):
    """Batch processing states."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProcessingMode(Enum):
    """Processing modes."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    ASYNC = "async"


class ErrorStrategy(Enum):
    """Error handling strategies."""
    FAIL_FAST = "fail_fast"
    CONTINUE = "continue"
    RETRY = "retry"
    SKIP = "skip"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class BatchConfig:
    """Batch processing configuration."""
    batch_size: int = 100
    max_workers: int = 4
    mode: ProcessingMode = ProcessingMode.PARALLEL
    error_strategy: ErrorStrategy = ErrorStrategy.CONTINUE
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: Optional[float] = None
    rate_limit: Optional[float] = None  # items per second
    checkpoint_interval: int = 0  # 0 = no checkpointing


@dataclass
class BatchItem(Generic[T]):
    """A single item in a batch."""
    item_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    data: T = None
    index: int = 0
    retries: int = 0
    state: BatchState = BatchState.PENDING
    error: Optional[str] = None
    result: Any = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class BatchProgress:
    """Batch processing progress."""
    total: int = 0
    completed: int = 0
    failed: int = 0
    skipped: int = 0
    pending: int = 0
    current_batch: int = 0
    total_batches: int = 0
    elapsed_ms: float = 0.0
    estimated_remaining_ms: float = 0.0

    @property
    def percent(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.completed + self.failed + self.skipped) / self.total * 100


@dataclass
class BatchResult(Generic[T, R]):
    """Result of batch processing."""
    batch_id: str
    state: BatchState
    total_items: int
    successful: int
    failed: int
    skipped: int
    results: List[R] = field(default_factory=list)
    errors: List[Tuple[int, str]] = field(default_factory=list)
    duration_ms: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class Checkpoint:
    """Batch checkpoint."""
    batch_id: str
    processed_indices: Set[int] = field(default_factory=set)
    failed_indices: Dict[int, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class BatchStats:
    """Batch processing statistics."""
    total_batches: int = 0
    total_items: int = 0
    successful_items: int = 0
    failed_items: int = 0
    avg_duration_ms: float = 0.0
    avg_items_per_second: float = 0.0


# =============================================================================
# BATCH PROCESSOR BASE
# =============================================================================

class ItemProcessor(ABC, Generic[T, R]):
    """Abstract item processor."""

    @abstractmethod
    async def process(self, item: T, index: int) -> R:
        """Process a single item."""
        pass

    async def on_error(self, item: T, index: int, error: Exception) -> None:
        """Handle processing error."""
        pass

    async def on_complete(self, item: T, index: int, result: R) -> None:
        """Handle successful processing."""
        pass


class FunctionProcessor(ItemProcessor[T, R]):
    """Function-based processor."""

    def __init__(self, func: Callable[[T, int], Awaitable[R]]):
        self.func = func

    async def process(self, item: T, index: int) -> R:
        return await self.func(item, index)


class SyncFunctionProcessor(ItemProcessor[T, R]):
    """Sync function processor."""

    def __init__(self, func: Callable[[T, int], R]):
        self.func = func
        self._executor = ThreadPoolExecutor(max_workers=1)

    async def process(self, item: T, index: int) -> R:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self.func,
            item,
            index
        )


# =============================================================================
# RATE LIMITER
# =============================================================================

class BatchRateLimiter:
    """Rate limiter for batch processing."""

    def __init__(self, items_per_second: float):
        self.items_per_second = items_per_second
        self._interval = 1.0 / items_per_second
        self._last_time = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait for rate limit."""
        async with self._lock:
            now = time.time()
            elapsed = now - self._last_time

            if elapsed < self._interval:
                await asyncio.sleep(self._interval - elapsed)

            self._last_time = time.time()


# =============================================================================
# CHECKPOINT MANAGER
# =============================================================================

class CheckpointManager:
    """Manages batch checkpoints."""

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path
        self._checkpoints: Dict[str, Checkpoint] = {}
        self._lock = threading.RLock()

    def save(self, checkpoint: Checkpoint) -> None:
        """Save a checkpoint."""
        with self._lock:
            self._checkpoints[checkpoint.batch_id] = checkpoint

            if self.storage_path:
                self._persist(checkpoint)

    def load(self, batch_id: str) -> Optional[Checkpoint]:
        """Load a checkpoint."""
        with self._lock:
            if batch_id in self._checkpoints:
                return self._checkpoints[batch_id]

            if self.storage_path:
                return self._load_from_disk(batch_id)

            return None

    def delete(self, batch_id: str) -> None:
        """Delete a checkpoint."""
        with self._lock:
            self._checkpoints.pop(batch_id, None)

            if self.storage_path:
                filepath = os.path.join(self.storage_path, f"{batch_id}.json")
                if os.path.exists(filepath):
                    os.remove(filepath)

    def _persist(self, checkpoint: Checkpoint) -> None:
        """Persist checkpoint to disk."""
        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path)

        filepath = os.path.join(self.storage_path, f"{checkpoint.batch_id}.json")
        data = {
            "batch_id": checkpoint.batch_id,
            "processed_indices": list(checkpoint.processed_indices),
            "failed_indices": checkpoint.failed_indices,
            "timestamp": checkpoint.timestamp.isoformat()
        }

        with open(filepath, 'w') as f:
            json.dump(data, f)

    def _load_from_disk(self, batch_id: str) -> Optional[Checkpoint]:
        """Load checkpoint from disk."""
        filepath = os.path.join(self.storage_path, f"{batch_id}.json")

        if not os.path.exists(filepath):
            return None

        with open(filepath, 'r') as f:
            data = json.load(f)

        return Checkpoint(
            batch_id=data["batch_id"],
            processed_indices=set(data["processed_indices"]),
            failed_indices=data["failed_indices"],
            timestamp=datetime.fromisoformat(data["timestamp"])
        )


# =============================================================================
# BATCH JOB
# =============================================================================

class BatchJob(Generic[T, R]):
    """
    A batch processing job.
    """

    def __init__(
        self,
        batch_id: Optional[str] = None,
        items: Optional[List[T]] = None,
        processor: Optional[ItemProcessor[T, R]] = None,
        config: Optional[BatchConfig] = None
    ):
        self.batch_id = batch_id or str(uuid.uuid4())
        self.config = config or BatchConfig()
        self.processor = processor

        self._items: List[BatchItem[T]] = []
        self._results: List[R] = []
        self._errors: List[Tuple[int, str]] = []

        self.state = BatchState.PENDING
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

        self._progress_callbacks: List[Callable[[BatchProgress], None]] = []
        self._rate_limiter: Optional[BatchRateLimiter] = None
        self._cancel_event = asyncio.Event()

        if items:
            self.set_items(items)

        if config and config.rate_limit:
            self._rate_limiter = BatchRateLimiter(config.rate_limit)

    def set_items(self, items: List[T]) -> None:
        """Set items to process."""
        self._items = [
            BatchItem(data=item, index=i)
            for i, item in enumerate(items)
        ]

    def set_processor(self, processor: ItemProcessor[T, R]) -> None:
        """Set the item processor."""
        self.processor = processor

    def on_progress(self, callback: Callable[[BatchProgress], None]) -> None:
        """Register progress callback."""
        self._progress_callbacks.append(callback)

    def cancel(self) -> None:
        """Cancel the batch job."""
        self._cancel_event.set()
        self.state = BatchState.CANCELLED

    def pause(self) -> None:
        """Pause the batch job."""
        if self.state == BatchState.RUNNING:
            self.state = BatchState.PAUSED

    def resume(self) -> None:
        """Resume the batch job."""
        if self.state == BatchState.PAUSED:
            self.state = BatchState.RUNNING

    async def run(self) -> BatchResult[T, R]:
        """Execute the batch job."""
        if not self.processor:
            raise ValueError("No processor set")

        self.state = BatchState.RUNNING
        self.started_at = datetime.utcnow()
        start_time = time.time()

        try:
            if self.config.mode == ProcessingMode.SEQUENTIAL:
                await self._run_sequential()
            elif self.config.mode == ProcessingMode.PARALLEL:
                await self._run_parallel()
            else:  # ASYNC
                await self._run_async()

            self.state = BatchState.COMPLETED
        except Exception as e:
            self.state = BatchState.FAILED
            self._errors.append((-1, str(e)))
        finally:
            self.completed_at = datetime.utcnow()

        return BatchResult(
            batch_id=self.batch_id,
            state=self.state,
            total_items=len(self._items),
            successful=len(self._results),
            failed=len(self._errors),
            skipped=sum(1 for i in self._items if i.state == BatchState.CANCELLED),
            results=self._results,
            errors=self._errors,
            duration_ms=(time.time() - start_time) * 1000,
            started_at=self.started_at,
            completed_at=self.completed_at
        )

    async def _run_sequential(self) -> None:
        """Run items sequentially."""
        for batch_item in self._items:
            if self._cancel_event.is_set():
                break

            while self.state == BatchState.PAUSED:
                await asyncio.sleep(0.1)

            await self._process_item(batch_item)
            self._notify_progress()

    async def _run_parallel(self) -> None:
        """Run items in parallel batches."""
        batch_size = self.config.batch_size
        batches = [
            self._items[i:i + batch_size]
            for i in range(0, len(self._items), batch_size)
        ]

        for batch_num, batch in enumerate(batches):
            if self._cancel_event.is_set():
                break

            while self.state == BatchState.PAUSED:
                await asyncio.sleep(0.1)

            tasks = [
                self._process_item(item)
                for item in batch
            ]

            await asyncio.gather(*tasks, return_exceptions=True)
            self._notify_progress()

    async def _run_async(self) -> None:
        """Run all items asynchronously with worker limit."""
        semaphore = asyncio.Semaphore(self.config.max_workers)

        async def bounded_process(item: BatchItem[T]) -> None:
            async with semaphore:
                if self._cancel_event.is_set():
                    return
                await self._process_item(item)

        tasks = [bounded_process(item) for item in self._items]
        await asyncio.gather(*tasks, return_exceptions=True)
        self._notify_progress()

    async def _process_item(self, batch_item: BatchItem[T]) -> None:
        """Process a single batch item."""
        if self._rate_limiter:
            await self._rate_limiter.acquire()

        batch_item.state = BatchState.RUNNING
        batch_item.started_at = datetime.utcnow()

        try:
            if self.config.timeout:
                result = await asyncio.wait_for(
                    self.processor.process(batch_item.data, batch_item.index),
                    timeout=self.config.timeout
                )
            else:
                result = await self.processor.process(
                    batch_item.data,
                    batch_item.index
                )

            batch_item.result = result
            batch_item.state = BatchState.COMPLETED
            self._results.append(result)

            await self.processor.on_complete(
                batch_item.data,
                batch_item.index,
                result
            )

        except Exception as e:
            batch_item.error = str(e)

            # Retry logic
            if (self.config.error_strategy == ErrorStrategy.RETRY and
                batch_item.retries < self.config.max_retries):
                batch_item.retries += 1
                batch_item.state = BatchState.PENDING
                await asyncio.sleep(self.config.retry_delay * batch_item.retries)
                await self._process_item(batch_item)
                return

            await self.processor.on_error(batch_item.data, batch_item.index, e)

            if self.config.error_strategy == ErrorStrategy.FAIL_FAST:
                self._cancel_event.set()
                raise

            batch_item.state = BatchState.FAILED
            self._errors.append((batch_item.index, str(e)))

        finally:
            batch_item.completed_at = datetime.utcnow()

    def _notify_progress(self) -> None:
        """Notify progress callbacks."""
        progress = self.get_progress()

        for callback in self._progress_callbacks:
            try:
                callback(progress)
            except Exception:
                pass

    def get_progress(self) -> BatchProgress:
        """Get current progress."""
        completed = sum(1 for i in self._items if i.state == BatchState.COMPLETED)
        failed = sum(1 for i in self._items if i.state == BatchState.FAILED)
        skipped = sum(1 for i in self._items if i.state == BatchState.CANCELLED)
        pending = len(self._items) - completed - failed - skipped

        elapsed = 0.0
        estimated = 0.0

        if self.started_at:
            elapsed = (datetime.utcnow() - self.started_at).total_seconds() * 1000
            processed = completed + failed + skipped
            if processed > 0:
                rate = elapsed / processed
                estimated = rate * pending

        return BatchProgress(
            total=len(self._items),
            completed=completed,
            failed=failed,
            skipped=skipped,
            pending=pending,
            elapsed_ms=elapsed,
            estimated_remaining_ms=estimated
        )


# =============================================================================
# BATCH PROCESSOR
# =============================================================================

class BatchProcessor:
    """
    Batch Processor for BAEL.

    Advanced batch processing management.
    """

    def __init__(
        self,
        default_config: Optional[BatchConfig] = None,
        checkpoint_path: Optional[str] = None
    ):
        self.default_config = default_config or BatchConfig()

        self._jobs: Dict[str, BatchJob] = {}
        self._checkpoint_manager = CheckpointManager(checkpoint_path)
        self._stats = BatchStats()
        self._lock = threading.RLock()

    # -------------------------------------------------------------------------
    # JOB CREATION
    # -------------------------------------------------------------------------

    def create_job(
        self,
        items: List[T],
        processor: ItemProcessor[T, R],
        config: Optional[BatchConfig] = None
    ) -> BatchJob[T, R]:
        """Create a batch job."""
        job = BatchJob(
            items=items,
            processor=processor,
            config=config or self.default_config
        )

        with self._lock:
            self._jobs[job.batch_id] = job

        return job

    def create_job_from_func(
        self,
        items: List[T],
        func: Callable[[T, int], Awaitable[R]],
        config: Optional[BatchConfig] = None
    ) -> BatchJob[T, R]:
        """Create job with async function."""
        processor = FunctionProcessor(func)
        return self.create_job(items, processor, config)

    def create_job_from_sync_func(
        self,
        items: List[T],
        func: Callable[[T, int], R],
        config: Optional[BatchConfig] = None
    ) -> BatchJob[T, R]:
        """Create job with sync function."""
        processor = SyncFunctionProcessor(func)
        return self.create_job(items, processor, config)

    # -------------------------------------------------------------------------
    # EXECUTION
    # -------------------------------------------------------------------------

    async def run(self, job: BatchJob[T, R]) -> BatchResult[T, R]:
        """Run a batch job."""
        result = await job.run()

        with self._lock:
            self._update_stats(result)

        return result

    async def process(
        self,
        items: List[T],
        func: Callable[[T, int], Awaitable[R]],
        config: Optional[BatchConfig] = None
    ) -> BatchResult[T, R]:
        """Convenience method to process items."""
        job = self.create_job_from_func(items, func, config)
        return await self.run(job)

    async def process_sync(
        self,
        items: List[T],
        func: Callable[[T, int], R],
        config: Optional[BatchConfig] = None
    ) -> BatchResult[T, R]:
        """Process with sync function."""
        job = self.create_job_from_sync_func(items, func, config)
        return await self.run(job)

    # -------------------------------------------------------------------------
    # JOB MANAGEMENT
    # -------------------------------------------------------------------------

    def get_job(self, batch_id: str) -> Optional[BatchJob]:
        """Get a job by ID."""
        with self._lock:
            return self._jobs.get(batch_id)

    def cancel_job(self, batch_id: str) -> bool:
        """Cancel a job."""
        job = self.get_job(batch_id)
        if job:
            job.cancel()
            return True
        return False

    def pause_job(self, batch_id: str) -> bool:
        """Pause a job."""
        job = self.get_job(batch_id)
        if job:
            job.pause()
            return True
        return False

    def resume_job(self, batch_id: str) -> bool:
        """Resume a job."""
        job = self.get_job(batch_id)
        if job:
            job.resume()
            return True
        return False

    def list_jobs(self) -> List[Dict[str, Any]]:
        """List all jobs."""
        with self._lock:
            return [
                {
                    "batch_id": job.batch_id,
                    "state": job.state.value,
                    "items": len(job._items),
                    "progress": job.get_progress().percent
                }
                for job in self._jobs.values()
            ]

    # -------------------------------------------------------------------------
    # CHECKPOINTING
    # -------------------------------------------------------------------------

    def save_checkpoint(self, job: BatchJob) -> None:
        """Save job checkpoint."""
        processed = {
            i.index for i in job._items
            if i.state == BatchState.COMPLETED
        }
        failed = {
            i.index: i.error
            for i in job._items
            if i.state == BatchState.FAILED
        }

        checkpoint = Checkpoint(
            batch_id=job.batch_id,
            processed_indices=processed,
            failed_indices=failed
        )

        self._checkpoint_manager.save(checkpoint)

    def load_checkpoint(self, batch_id: str) -> Optional[Checkpoint]:
        """Load job checkpoint."""
        return self._checkpoint_manager.load(batch_id)

    async def resume_from_checkpoint(
        self,
        batch_id: str,
        items: List[T],
        processor: ItemProcessor[T, R],
        config: Optional[BatchConfig] = None
    ) -> BatchResult[T, R]:
        """Resume job from checkpoint."""
        checkpoint = self.load_checkpoint(batch_id)

        if not checkpoint:
            # No checkpoint, start fresh
            job = self.create_job(items, processor, config)
            return await self.run(job)

        # Filter out already processed items
        remaining_items = [
            item for i, item in enumerate(items)
            if i not in checkpoint.processed_indices
        ]

        job = self.create_job(remaining_items, processor, config)
        job.batch_id = batch_id

        return await self.run(job)

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    async def chunk_and_process(
        self,
        items: List[T],
        chunk_size: int,
        func: Callable[[List[T]], Awaitable[List[R]]],
        config: Optional[BatchConfig] = None
    ) -> List[R]:
        """Process items in chunks."""
        results = []

        chunks = [
            items[i:i + chunk_size]
            for i in range(0, len(items), chunk_size)
        ]

        for chunk in chunks:
            chunk_results = await func(chunk)
            results.extend(chunk_results)

        return results

    async def map(
        self,
        items: List[T],
        func: Callable[[T], Awaitable[R]],
        config: Optional[BatchConfig] = None
    ) -> List[R]:
        """Map function over items."""
        async def indexed_func(item: T, index: int) -> R:
            return await func(item)

        result = await self.process(items, indexed_func, config)
        return result.results

    async def filter(
        self,
        items: List[T],
        predicate: Callable[[T], Awaitable[bool]],
        config: Optional[BatchConfig] = None
    ) -> List[T]:
        """Filter items."""
        async def check(item: T, index: int) -> Tuple[int, bool]:
            return (index, await predicate(item))

        result = await self.process(items, check, config)

        passing_indices = {idx for idx, passed in result.results if passed}
        return [item for i, item in enumerate(items) if i in passing_indices]

    # -------------------------------------------------------------------------
    # STATS
    # -------------------------------------------------------------------------

    def get_stats(self) -> BatchStats:
        """Get processing statistics."""
        with self._lock:
            return BatchStats(
                total_batches=self._stats.total_batches,
                total_items=self._stats.total_items,
                successful_items=self._stats.successful_items,
                failed_items=self._stats.failed_items,
                avg_duration_ms=self._stats.avg_duration_ms,
                avg_items_per_second=self._stats.avg_items_per_second
            )

    def _update_stats(self, result: BatchResult) -> None:
        """Update statistics."""
        self._stats.total_batches += 1
        self._stats.total_items += result.total_items
        self._stats.successful_items += result.successful
        self._stats.failed_items += result.failed

        # Update averages
        n = self._stats.total_batches
        self._stats.avg_duration_ms = (
            (self._stats.avg_duration_ms * (n - 1) + result.duration_ms) / n
        )

        if result.duration_ms > 0:
            items_per_sec = result.total_items / (result.duration_ms / 1000)
            self._stats.avg_items_per_second = (
                (self._stats.avg_items_per_second * (n - 1) + items_per_sec) / n
            )


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Batch Processor."""
    print("=" * 70)
    print("BAEL - BATCH PROCESSOR DEMO")
    print("Advanced Batch Processing for AI Agents")
    print("=" * 70)
    print()

    processor = BatchProcessor()

    # 1. Basic Batch Processing
    print("1. BASIC BATCH PROCESSING:")
    print("-" * 40)

    items = list(range(10))

    async def double(item: int, index: int) -> int:
        await asyncio.sleep(0.01)  # Simulate work
        return item * 2

    result = await processor.process(items, double)
    print(f"   Input: {items}")
    print(f"   Output: {result.results}")
    print(f"   Duration: {result.duration_ms:.2f}ms")
    print()

    # 2. Parallel Processing
    print("2. PARALLEL PROCESSING:")
    print("-" * 40)

    parallel_config = BatchConfig(
        mode=ProcessingMode.PARALLEL,
        batch_size=5,
        max_workers=4
    )

    async def slow_process(item: int, index: int) -> int:
        await asyncio.sleep(0.05)  # Simulate slow work
        return item ** 2

    result = await processor.process(items, slow_process, parallel_config)
    print(f"   Input: {items}")
    print(f"   Output: {result.results}")
    print(f"   Duration: {result.duration_ms:.2f}ms")
    print()

    # 3. Error Handling
    print("3. ERROR HANDLING:")
    print("-" * 40)

    async def risky_process(item: int, index: int) -> int:
        if item == 5:
            raise ValueError("Item 5 is bad!")
        return item

    error_config = BatchConfig(error_strategy=ErrorStrategy.CONTINUE)
    result = await processor.process(items, risky_process, error_config)

    print(f"   Successful: {result.successful}")
    print(f"   Failed: {result.failed}")
    print(f"   Errors: {result.errors}")
    print()

    # 4. Retry Logic
    print("4. RETRY LOGIC:")
    print("-" * 40)

    attempt_count = defaultdict(int)

    async def flaky_process(item: int, index: int) -> int:
        attempt_count[index] += 1
        if attempt_count[index] < 2 and item == 3:
            raise ValueError("Temporary failure")
        return item

    retry_config = BatchConfig(
        error_strategy=ErrorStrategy.RETRY,
        max_retries=3,
        retry_delay=0.1
    )

    result = await processor.process(items[:5], flaky_process, retry_config)
    print(f"   Results: {result.results}")
    print(f"   Attempt counts: {dict(attempt_count)}")
    print()

    # 5. Progress Tracking
    print("5. PROGRESS TRACKING:")
    print("-" * 40)

    progress_log = []

    def on_progress(p: BatchProgress):
        progress_log.append(f"{p.percent:.0f}%")

    job = processor.create_job_from_func(
        list(range(20)),
        double,
        BatchConfig(batch_size=5)
    )
    job.on_progress(on_progress)

    await processor.run(job)
    print(f"   Progress updates: {progress_log}")
    print()

    # 6. Rate Limiting
    print("6. RATE LIMITING:")
    print("-" * 40)

    rate_config = BatchConfig(
        rate_limit=10.0,  # 10 items per second
        mode=ProcessingMode.SEQUENTIAL
    )

    start = time.time()
    result = await processor.process(
        list(range(5)),
        lambda item, idx: asyncio.sleep(0) or item,  # type: ignore
        rate_config
    )
    duration = time.time() - start

    print(f"   Items: 5, Rate: 10/sec")
    print(f"   Expected: ~0.5s, Actual: {duration:.2f}s")
    print()

    # 7. Sync Function Processing
    print("7. SYNC FUNCTION PROCESSING:")
    print("-" * 40)

    def sync_process(item: int, index: int) -> str:
        time.sleep(0.01)
        return f"processed_{item}"

    result = await processor.process_sync(list(range(5)), sync_process)
    print(f"   Results: {result.results}")
    print()

    # 8. Map Operation
    print("8. MAP OPERATION:")
    print("-" * 40)

    async def to_string(item: int) -> str:
        return f"item_{item}"

    mapped = await processor.map(list(range(5)), to_string)
    print(f"   Input: [0, 1, 2, 3, 4]")
    print(f"   Output: {mapped}")
    print()

    # 9. Filter Operation
    print("9. FILTER OPERATION:")
    print("-" * 40)

    async def is_even(item: int) -> bool:
        return item % 2 == 0

    filtered = await processor.filter(list(range(10)), is_even)
    print(f"   Input: [0-9]")
    print(f"   Evens: {filtered}")
    print()

    # 10. Job Management
    print("10. JOB MANAGEMENT:")
    print("-" * 40)

    job = processor.create_job_from_func(
        list(range(100)),
        lambda x, i: asyncio.sleep(0.01) or x,  # type: ignore
        BatchConfig(mode=ProcessingMode.ASYNC, max_workers=10)
    )

    # Start in background
    task = asyncio.create_task(processor.run(job))
    await asyncio.sleep(0.05)

    progress = job.get_progress()
    print(f"   Progress: {progress.percent:.1f}%")
    print(f"   State: {job.state.value}")

    await task
    print(f"   Final state: {job.state.value}")
    print()

    # 11. Chunk Processing
    print("11. CHUNK PROCESSING:")
    print("-" * 40)

    async def process_chunk(chunk: List[int]) -> List[str]:
        return [f"chunk_item_{x}" for x in chunk]

    chunked = await processor.chunk_and_process(
        list(range(10)),
        chunk_size=3,
        func=process_chunk
    )
    print(f"   Chunk size: 3")
    print(f"   Results: {chunked[:5]}...")
    print()

    # 12. Custom Processor
    print("12. CUSTOM PROCESSOR:")
    print("-" * 40)

    class LoggingProcessor(ItemProcessor[int, int]):
        def __init__(self):
            self.log = []

        async def process(self, item: int, index: int) -> int:
            self.log.append(f"Processing {item}")
            return item * 10

        async def on_complete(self, item: int, index: int, result: int) -> None:
            self.log.append(f"Completed {item} -> {result}")

    custom = LoggingProcessor()
    job = processor.create_job(list(range(3)), custom)
    await processor.run(job)

    print(f"   Log: {custom.log}")
    print()

    # 13. Job List
    print("13. JOB LIST:")
    print("-" * 40)

    jobs = processor.list_jobs()
    print(f"   Total jobs: {len(jobs)}")
    if jobs:
        print(f"   Last job: {jobs[-1]}")
    print()

    # 14. Statistics
    print("14. STATISTICS:")
    print("-" * 40)

    stats = processor.get_stats()
    print(f"   Total batches: {stats.total_batches}")
    print(f"   Total items: {stats.total_items}")
    print(f"   Successful: {stats.successful_items}")
    print(f"   Failed: {stats.failed_items}")
    print(f"   Avg duration: {stats.avg_duration_ms:.2f}ms")
    print(f"   Avg items/sec: {stats.avg_items_per_second:.2f}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Batch Processor Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
