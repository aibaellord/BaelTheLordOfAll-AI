"""
Parallel Execution - Maximum Throughput Engine
================================================

Advanced parallel execution patterns for maximum performance.

"Simultaneity is the key to dominance." — Ba'el
"""

import asyncio
import logging
import time
import threading
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Generic, Coroutine
from dataclasses import dataclass, field
from functools import partial
import queue

logger = logging.getLogger("BAEL.HiddenTechniques.ParallelExecution")

T = TypeVar('T')
R = TypeVar('R')


class ExecutionStrategy(Enum):
    """Execution strategies."""
    SEQUENTIAL = "sequential"      # One at a time
    THREADED = "threaded"          # Thread pool
    PROCESS = "process"            # Process pool
    ASYNC = "async"                # Asyncio
    HYBRID = "hybrid"              # Mix of async + threads
    ADAPTIVE = "adaptive"          # Adapts to workload


class TaskPriority(Enum):
    """Task priority levels."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


@dataclass
class TaskResult(Generic[T]):
    """Result of a parallel task."""
    task_id: str
    success: bool
    result: Optional[T] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0
    retries: int = 0


@dataclass
class ExecutionStats:
    """Execution statistics."""
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    total_time: float = 0.0
    average_time: float = 0.0
    parallelism_factor: float = 0.0


@dataclass
class BatchResult(Generic[T]):
    """Result of a batch execution."""
    results: List[TaskResult[T]]
    stats: ExecutionStats

    @property
    def successful(self) -> List[T]:
        return [r.result for r in self.results if r.success and r.result is not None]

    @property
    def failed(self) -> List[TaskResult[T]]:
        return [r for r in self.results if not r.success]


class ParallelExecutor:
    """
    High-performance parallel execution engine.

    Features:
    - Multiple execution strategies
    - Automatic concurrency optimization
    - Priority queuing
    - Rate limiting integration
    - Error handling and retries
    """

    def __init__(
        self,
        strategy: ExecutionStrategy = ExecutionStrategy.ASYNC,
        max_workers: int = None,
        max_concurrent: int = 10,
    ):
        self.strategy = strategy
        self.max_workers = max_workers or (multiprocessing.cpu_count() * 2)
        self.max_concurrent = max_concurrent

        self._thread_pool: Optional[ThreadPoolExecutor] = None
        self._process_pool: Optional[ProcessPoolExecutor] = None
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._stats = ExecutionStats()

    async def execute_batch(
        self,
        tasks: List[Callable[[], T]],
        timeout: float = None,
        retry_count: int = 0,
    ) -> BatchResult[T]:
        """
        Execute a batch of tasks in parallel.

        Args:
            tasks: List of callable tasks
            timeout: Overall timeout in seconds
            retry_count: Number of retries per task

        Returns:
            BatchResult with all results
        """
        start_time = time.time()

        if self.strategy == ExecutionStrategy.SEQUENTIAL:
            results = await self._execute_sequential(tasks, timeout, retry_count)
        elif self.strategy == ExecutionStrategy.THREADED:
            results = await self._execute_threaded(tasks, timeout, retry_count)
        elif self.strategy == ExecutionStrategy.PROCESS:
            results = await self._execute_process(tasks, timeout, retry_count)
        elif self.strategy == ExecutionStrategy.ASYNC:
            results = await self._execute_async(tasks, timeout, retry_count)
        elif self.strategy == ExecutionStrategy.HYBRID:
            results = await self._execute_hybrid(tasks, timeout, retry_count)
        elif self.strategy == ExecutionStrategy.ADAPTIVE:
            results = await self._execute_adaptive(tasks, timeout, retry_count)
        else:
            results = await self._execute_async(tasks, timeout, retry_count)

        total_time = time.time() - start_time

        # Calculate stats
        stats = ExecutionStats(
            total_tasks=len(tasks),
            completed_tasks=sum(1 for r in results if r.success),
            failed_tasks=sum(1 for r in results if not r.success),
            total_time=total_time,
            average_time=sum(r.duration_seconds for r in results) / len(results) if results else 0,
            parallelism_factor=sum(r.duration_seconds for r in results) / total_time if total_time > 0 else 0,
        )

        return BatchResult(results=results, stats=stats)

    async def map(
        self,
        func: Callable[[T], R],
        items: List[T],
        timeout: float = None,
    ) -> List[R]:
        """
        Map a function over items in parallel.

        Args:
            func: Function to apply
            items: Items to process
            timeout: Timeout per item

        Returns:
            List of results in order
        """
        tasks = [partial(func, item) for item in items]
        result = await self.execute_batch(tasks, timeout)
        return [r.result for r in result.results]

    async def map_async(
        self,
        func: Callable[[T], Coroutine[Any, Any, R]],
        items: List[T],
        max_concurrent: int = None,
    ) -> List[R]:
        """
        Map an async function over items.

        Args:
            func: Async function to apply
            items: Items to process
            max_concurrent: Max concurrent tasks

        Returns:
            List of results in order
        """
        max_concurrent = max_concurrent or self.max_concurrent
        semaphore = asyncio.Semaphore(max_concurrent)

        async def limited_func(item):
            async with semaphore:
                return await func(item)

        return await asyncio.gather(*[limited_func(item) for item in items])

    async def scatter_gather(
        self,
        funcs: List[Callable[[], T]],
        combiner: Callable[[List[T]], R] = None,
    ) -> R:
        """
        Execute multiple functions and combine results.

        Args:
            funcs: Functions to execute
            combiner: Function to combine results

        Returns:
            Combined result
        """
        result = await self.execute_batch(funcs)
        successful = result.successful

        if combiner:
            return combiner(successful)
        return successful

    async def pipeline(
        self,
        stages: List[Callable[[T], T]],
        initial_data: T,
    ) -> T:
        """
        Execute stages in a pipeline.

        Args:
            stages: List of stage functions
            initial_data: Initial input

        Returns:
            Final result after all stages
        """
        data = initial_data
        for stage in stages:
            if asyncio.iscoroutinefunction(stage):
                data = await stage(data)
            else:
                data = stage(data)
        return data

    async def race(
        self,
        tasks: List[Callable[[], T]],
        timeout: float = None,
    ) -> TaskResult[T]:
        """
        Execute tasks and return first successful result.

        Args:
            tasks: Tasks to race
            timeout: Timeout for race

        Returns:
            First successful result
        """
        if not tasks:
            return TaskResult(task_id="empty", success=False, error="No tasks")

        async def run_task(idx: int, task: Callable) -> TaskResult[T]:
            start = time.time()
            try:
                if asyncio.iscoroutinefunction(task):
                    result = await task()
                else:
                    result = task()
                return TaskResult(
                    task_id=f"task_{idx}",
                    success=True,
                    result=result,
                    duration_seconds=time.time() - start,
                )
            except Exception as e:
                return TaskResult(
                    task_id=f"task_{idx}",
                    success=False,
                    error=str(e),
                    duration_seconds=time.time() - start,
                )

        # Create tasks
        coroutines = [run_task(i, task) for i, task in enumerate(tasks)]

        # Race them
        done, pending = await asyncio.wait(
            [asyncio.create_task(c) for c in coroutines],
            timeout=timeout,
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Cancel pending
        for task in pending:
            task.cancel()

        # Return first successful
        for task in done:
            result = task.result()
            if result.success:
                return result

        # All failed, return first failure
        if done:
            return list(done)[0].result()

        return TaskResult(task_id="timeout", success=False, error="All tasks timed out")

    async def _execute_sequential(
        self,
        tasks: List[Callable],
        timeout: float,
        retry_count: int,
    ) -> List[TaskResult]:
        """Execute tasks sequentially."""
        results = []
        for i, task in enumerate(tasks):
            result = await self._execute_single(f"task_{i}", task, timeout, retry_count)
            results.append(result)
        return results

    async def _execute_async(
        self,
        tasks: List[Callable],
        timeout: float,
        retry_count: int,
    ) -> List[TaskResult]:
        """Execute tasks using asyncio."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)

        async def limited_execute(idx: int, task: Callable) -> TaskResult:
            async with self._semaphore:
                return await self._execute_single(f"task_{idx}", task, timeout, retry_count)

        return await asyncio.gather(*[
            limited_execute(i, task) for i, task in enumerate(tasks)
        ])

    async def _execute_threaded(
        self,
        tasks: List[Callable],
        timeout: float,
        retry_count: int,
    ) -> List[TaskResult]:
        """Execute tasks using thread pool."""
        if self._thread_pool is None:
            self._thread_pool = ThreadPoolExecutor(max_workers=self.max_workers)

        loop = asyncio.get_event_loop()

        async def run_in_thread(idx: int, task: Callable) -> TaskResult:
            start = time.time()
            try:
                result = await loop.run_in_executor(self._thread_pool, task)
                return TaskResult(
                    task_id=f"task_{idx}",
                    success=True,
                    result=result,
                    duration_seconds=time.time() - start,
                )
            except Exception as e:
                return TaskResult(
                    task_id=f"task_{idx}",
                    success=False,
                    error=str(e),
                    duration_seconds=time.time() - start,
                )

        return await asyncio.gather(*[
            run_in_thread(i, task) for i, task in enumerate(tasks)
        ])

    async def _execute_process(
        self,
        tasks: List[Callable],
        timeout: float,
        retry_count: int,
    ) -> List[TaskResult]:
        """Execute tasks using process pool."""
        if self._process_pool is None:
            self._process_pool = ProcessPoolExecutor(max_workers=min(self.max_workers, multiprocessing.cpu_count()))

        loop = asyncio.get_event_loop()

        async def run_in_process(idx: int, task: Callable) -> TaskResult:
            start = time.time()
            try:
                result = await loop.run_in_executor(self._process_pool, task)
                return TaskResult(
                    task_id=f"task_{idx}",
                    success=True,
                    result=result,
                    duration_seconds=time.time() - start,
                )
            except Exception as e:
                return TaskResult(
                    task_id=f"task_{idx}",
                    success=False,
                    error=str(e),
                    duration_seconds=time.time() - start,
                )

        return await asyncio.gather(*[
            run_in_process(i, task) for i, task in enumerate(tasks)
        ])

    async def _execute_hybrid(
        self,
        tasks: List[Callable],
        timeout: float,
        retry_count: int,
    ) -> List[TaskResult]:
        """Execute using hybrid async + threads."""
        # Use async for I/O bound, threads for CPU bound
        # Simple heuristic: use threads for larger task lists
        if len(tasks) > 100:
            return await self._execute_threaded(tasks, timeout, retry_count)
        else:
            return await self._execute_async(tasks, timeout, retry_count)

    async def _execute_adaptive(
        self,
        tasks: List[Callable],
        timeout: float,
        retry_count: int,
    ) -> List[TaskResult]:
        """Adapt execution strategy based on task characteristics."""
        if len(tasks) <= 3:
            return await self._execute_sequential(tasks, timeout, retry_count)
        elif len(tasks) <= 50:
            return await self._execute_async(tasks, timeout, retry_count)
        else:
            return await self._execute_threaded(tasks, timeout, retry_count)

    async def _execute_single(
        self,
        task_id: str,
        task: Callable,
        timeout: float,
        retry_count: int,
    ) -> TaskResult:
        """Execute a single task with retries."""
        last_error = None
        retries = 0

        for attempt in range(retry_count + 1):
            start = time.time()
            try:
                if asyncio.iscoroutinefunction(task):
                    if timeout:
                        result = await asyncio.wait_for(task(), timeout)
                    else:
                        result = await task()
                else:
                    result = task()

                return TaskResult(
                    task_id=task_id,
                    success=True,
                    result=result,
                    duration_seconds=time.time() - start,
                    retries=retries,
                )
            except asyncio.TimeoutError:
                last_error = "Timeout"
                retries += 1
            except Exception as e:
                last_error = str(e)
                retries += 1

        return TaskResult(
            task_id=task_id,
            success=False,
            error=last_error,
            duration_seconds=0,
            retries=retries,
        )

    def shutdown(self):
        """Shutdown executor pools."""
        if self._thread_pool:
            self._thread_pool.shutdown(wait=False)
        if self._process_pool:
            self._process_pool.shutdown(wait=False)


class PriorityQueue:
    """Priority-based task queue."""

    def __init__(self, max_size: int = 1000):
        self._queues: Dict[TaskPriority, asyncio.Queue] = {
            priority: asyncio.Queue(maxsize=max_size)
            for priority in TaskPriority
        }
        self._total = 0

    async def put(self, item: Any, priority: TaskPriority = TaskPriority.NORMAL) -> None:
        """Add item with priority."""
        await self._queues[priority].put(item)
        self._total += 1

    async def get(self) -> Any:
        """Get highest priority item."""
        for priority in TaskPriority:
            q = self._queues[priority]
            if not q.empty():
                self._total -= 1
                return await q.get()

        # Wait on all queues
        done, pending = await asyncio.wait(
            [asyncio.create_task(q.get()) for q in self._queues.values()],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()

        self._total -= 1
        return list(done)[0].result()

    def qsize(self) -> int:
        return self._total

    def empty(self) -> bool:
        return self._total == 0


class WorkerPool:
    """
    Pool of workers for continuous task processing.
    """

    def __init__(
        self,
        num_workers: int = 5,
        task_queue: PriorityQueue = None,
    ):
        self.num_workers = num_workers
        self.queue = task_queue or PriorityQueue()
        self._workers: List[asyncio.Task] = []
        self._running = False
        self._results: List[Any] = []

    async def start(self) -> None:
        """Start worker pool."""
        self._running = True
        self._workers = [
            asyncio.create_task(self._worker(i))
            for i in range(self.num_workers)
        ]

    async def stop(self) -> None:
        """Stop worker pool."""
        self._running = False
        for worker in self._workers:
            worker.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)

    async def submit(self, task: Callable, priority: TaskPriority = TaskPriority.NORMAL) -> None:
        """Submit a task to the pool."""
        await self.queue.put(task, priority)

    async def _worker(self, worker_id: int) -> None:
        """Worker coroutine."""
        while self._running:
            try:
                task = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                try:
                    if asyncio.iscoroutinefunction(task):
                        result = await task()
                    else:
                        result = task()
                    self._results.append(result)
                except Exception as e:
                    logger.error(f"Worker {worker_id} task failed: {e}")
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def parallel_map(func: Callable, items: List, max_concurrent: int = 10) -> List:
    """Quick parallel map function."""
    executor = ParallelExecutor(max_concurrent=max_concurrent)
    return await executor.map(func, items)


async def parallel_execute(tasks: List[Callable], max_concurrent: int = 10) -> List:
    """Quick parallel execution."""
    executor = ParallelExecutor(max_concurrent=max_concurrent)
    result = await executor.execute_batch(tasks)
    return result.successful


async def race_tasks(tasks: List[Callable], timeout: float = None) -> Any:
    """Race tasks and return first result."""
    executor = ParallelExecutor()
    result = await executor.race(tasks, timeout)
    return result.result if result.success else None
