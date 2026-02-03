#!/usr/bin/env python3
"""
BAEL - Task Executor
Advanced task execution engine for AI agent operations.

Features:
- Async task execution
- Parallel execution
- Task prioritization
- Retry mechanisms
- Timeout handling
- Task cancellation
- Progress tracking
- Result aggregation
- Execution graphs
- Task dependencies
"""

import asyncio
import heapq
import logging
import threading
import time
import traceback
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Awaitable, Callable, Coroutine, Dict, Generic, List,
                    Optional, Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)


T = TypeVar('T')
R = TypeVar('R')


# =============================================================================
# ENUMS
# =============================================================================

class TaskState(Enum):
    """Task execution states."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class TaskPriority(Enum):
    """Task priorities."""
    LOWEST = 1
    LOW = 2
    NORMAL = 3
    HIGH = 4
    HIGHEST = 5
    CRITICAL = 6


class RetryStrategy(Enum):
    """Retry strategies."""
    NONE = "none"
    IMMEDIATE = "immediate"
    FIXED_DELAY = "fixed_delay"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"


class ExecutionMode(Enum):
    """Execution modes."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONCURRENT = "concurrent"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class TaskConfig:
    """Task configuration."""
    timeout: Optional[float] = None
    priority: TaskPriority = TaskPriority.NORMAL
    retry_strategy: RetryStrategy = RetryStrategy.NONE
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_multiplier: float = 2.0
    retry_max_delay: float = 60.0


@dataclass
class TaskResult(Generic[T]):
    """Task execution result."""
    task_id: str
    success: bool
    value: Optional[T] = None
    error: Optional[Exception] = None
    execution_time_ms: float = 0.0
    retry_count: int = 0
    completed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TaskProgress:
    """Task progress information."""
    task_id: str
    state: TaskState
    progress_percent: float = 0.0
    current_step: str = ""
    total_steps: int = 1
    current_step_num: int = 0
    started_at: Optional[datetime] = None
    estimated_remaining_ms: Optional[float] = None


@dataclass
class ExecutionStats:
    """Execution statistics."""
    total_executed: int = 0
    total_succeeded: int = 0
    total_failed: int = 0
    total_cancelled: int = 0
    total_timeout: int = 0
    avg_execution_time_ms: float = 0.0
    total_retries: int = 0


@dataclass
class TaskDependency:
    """Task dependency information."""
    task_id: str
    depends_on: List[str] = field(default_factory=list)
    required: bool = True


# =============================================================================
# TASK INTERFACE
# =============================================================================

class Task(ABC, Generic[T]):
    """Base task interface."""

    def __init__(
        self,
        task_id: Optional[str] = None,
        config: Optional[TaskConfig] = None
    ):
        self.task_id = task_id or str(uuid.uuid4())
        self.config = config or TaskConfig()
        self._state = TaskState.PENDING
        self._progress = TaskProgress(task_id=self.task_id, state=self._state)
        self._lock = threading.RLock()
        self._cancel_event = asyncio.Event()

    @property
    def state(self) -> TaskState:
        with self._lock:
            return self._state

    @state.setter
    def state(self, value: TaskState) -> None:
        with self._lock:
            self._state = value
            self._progress.state = value

    @property
    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    @abstractmethod
    async def execute(self) -> T:
        """Execute the task."""
        pass

    def cancel(self) -> None:
        """Cancel the task."""
        self._cancel_event.set()

    def check_cancelled(self) -> None:
        """Check if cancelled and raise."""
        if self.is_cancelled:
            raise TaskCancelledError(f"Task {self.task_id} was cancelled")

    def report_progress(
        self,
        percent: float = 0.0,
        step: str = "",
        step_num: int = 0,
        total_steps: int = 1
    ) -> None:
        """Report task progress."""
        with self._lock:
            self._progress.progress_percent = percent
            self._progress.current_step = step
            self._progress.current_step_num = step_num
            self._progress.total_steps = total_steps

    def get_progress(self) -> TaskProgress:
        """Get current progress."""
        with self._lock:
            return TaskProgress(
                task_id=self._progress.task_id,
                state=self._progress.state,
                progress_percent=self._progress.progress_percent,
                current_step=self._progress.current_step,
                total_steps=self._progress.total_steps,
                current_step_num=self._progress.current_step_num,
                started_at=self._progress.started_at
            )


# =============================================================================
# TASK IMPLEMENTATIONS
# =============================================================================

class FunctionTask(Task[T]):
    """Task that executes a function."""

    def __init__(
        self,
        func: Callable[..., Awaitable[T]],
        args: Tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
        config: Optional[TaskConfig] = None
    ):
        super().__init__(task_id, config)
        self._func = func
        self._args = args
        self._kwargs = kwargs or {}

    async def execute(self) -> T:
        self.check_cancelled()
        return await self._func(*self._args, **self._kwargs)


class SyncFunctionTask(Task[T]):
    """Task that executes a sync function."""

    def __init__(
        self,
        func: Callable[..., T],
        args: Tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
        config: Optional[TaskConfig] = None
    ):
        super().__init__(task_id, config)
        self._func = func
        self._args = args
        self._kwargs = kwargs or {}
        self._executor = ThreadPoolExecutor(max_workers=1)

    async def execute(self) -> T:
        self.check_cancelled()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            lambda: self._func(*self._args, **self._kwargs)
        )


class CompositeTask(Task[List[Any]]):
    """Task composed of multiple subtasks."""

    def __init__(
        self,
        tasks: List[Task],
        mode: ExecutionMode = ExecutionMode.PARALLEL,
        task_id: Optional[str] = None,
        config: Optional[TaskConfig] = None
    ):
        super().__init__(task_id, config)
        self._tasks = tasks
        self._mode = mode

    async def execute(self) -> List[Any]:
        self.check_cancelled()

        if self._mode == ExecutionMode.SEQUENTIAL:
            results = []
            for i, task in enumerate(self._tasks):
                self.report_progress(
                    percent=(i / len(self._tasks)) * 100,
                    step=f"Task {i+1}/{len(self._tasks)}",
                    step_num=i,
                    total_steps=len(self._tasks)
                )
                results.append(await task.execute())
            return results
        else:
            # Parallel execution
            return await asyncio.gather(*[t.execute() for t in self._tasks])


class ChainTask(Task[T]):
    """Task that chains multiple tasks, passing results."""

    def __init__(
        self,
        tasks: List[Task],
        task_id: Optional[str] = None,
        config: Optional[TaskConfig] = None
    ):
        super().__init__(task_id, config)
        self._tasks = tasks

    async def execute(self) -> T:
        self.check_cancelled()

        result = None
        for i, task in enumerate(self._tasks):
            self.report_progress(
                percent=(i / len(self._tasks)) * 100,
                step=f"Chain step {i+1}/{len(self._tasks)}"
            )

            if isinstance(task, FunctionTask) and result is not None:
                # Pass previous result as first argument
                task._args = (result,) + task._args

            result = await task.execute()

        return result


# =============================================================================
# RETRY HANDLER
# =============================================================================

class RetryHandler:
    """Handles retry logic for tasks."""

    def calculate_delay(
        self,
        config: TaskConfig,
        attempt: int
    ) -> float:
        """Calculate retry delay."""
        if config.retry_strategy == RetryStrategy.NONE:
            return 0
        elif config.retry_strategy == RetryStrategy.IMMEDIATE:
            return 0
        elif config.retry_strategy == RetryStrategy.FIXED_DELAY:
            return config.retry_delay
        elif config.retry_strategy == RetryStrategy.LINEAR_BACKOFF:
            return min(
                config.retry_delay * attempt,
                config.retry_max_delay
            )
        elif config.retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            return min(
                config.retry_delay * (config.retry_multiplier ** (attempt - 1)),
                config.retry_max_delay
            )
        return config.retry_delay

    def should_retry(
        self,
        config: TaskConfig,
        attempt: int,
        error: Exception
    ) -> bool:
        """Determine if task should be retried."""
        if config.retry_strategy == RetryStrategy.NONE:
            return False
        if attempt >= config.max_retries:
            return False
        # Don't retry cancellation
        if isinstance(error, (TaskCancelledError, asyncio.CancelledError)):
            return False
        return True


# =============================================================================
# TASK QUEUE
# =============================================================================

class TaskQueue:
    """Priority queue for tasks."""

    def __init__(self, max_size: int = 10000):
        self._queue: List[Tuple[int, float, Task]] = []
        self._max_size = max_size
        self._lock = threading.RLock()
        self._counter = 0

    def push(self, task: Task) -> bool:
        """Push a task onto the queue."""
        with self._lock:
            if len(self._queue) >= self._max_size:
                return False

            # Priority is negated for min-heap (higher priority = lower number)
            priority = -task.config.priority.value
            self._counter += 1
            heapq.heappush(self._queue, (priority, self._counter, task))
            task.state = TaskState.QUEUED
            return True

    def pop(self) -> Optional[Task]:
        """Pop the highest priority task."""
        with self._lock:
            if not self._queue:
                return None
            _, _, task = heapq.heappop(self._queue)
            return task

    def peek(self) -> Optional[Task]:
        """Peek at the highest priority task."""
        with self._lock:
            if not self._queue:
                return None
            return self._queue[0][2]

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._queue)

    @property
    def is_empty(self) -> bool:
        with self._lock:
            return len(self._queue) == 0


# =============================================================================
# DEPENDENCY GRAPH
# =============================================================================

class DependencyGraph:
    """Tracks task dependencies."""

    def __init__(self):
        self._dependencies: Dict[str, Set[str]] = defaultdict(set)
        self._dependents: Dict[str, Set[str]] = defaultdict(set)
        self._completed: Set[str] = set()
        self._lock = threading.RLock()

    def add_dependency(self, task_id: str, depends_on: str) -> None:
        """Add a dependency."""
        with self._lock:
            self._dependencies[task_id].add(depends_on)
            self._dependents[depends_on].add(task_id)

    def mark_completed(self, task_id: str) -> List[str]:
        """Mark a task as completed, return newly ready tasks."""
        with self._lock:
            self._completed.add(task_id)

            ready = []
            for dependent in self._dependents.get(task_id, set()):
                if self.is_ready(dependent):
                    ready.append(dependent)

            return ready

    def is_ready(self, task_id: str) -> bool:
        """Check if a task is ready to execute."""
        with self._lock:
            deps = self._dependencies.get(task_id, set())
            return deps.issubset(self._completed)

    def get_ready_tasks(self, task_ids: List[str]) -> List[str]:
        """Get all ready tasks from a list."""
        with self._lock:
            return [tid for tid in task_ids if self.is_ready(tid)]

    def has_circular_dependency(self, task_id: str) -> bool:
        """Check for circular dependencies."""
        visited = set()
        stack = [task_id]

        while stack:
            current = stack.pop()
            if current in visited:
                if current == task_id:
                    return True
                continue
            visited.add(current)

            with self._lock:
                for dep in self._dependencies.get(current, set()):
                    stack.append(dep)

        return False


# =============================================================================
# EXCEPTIONS
# =============================================================================

class TaskError(Exception):
    """Base task error."""
    pass


class TaskCancelledError(TaskError):
    """Task was cancelled."""
    pass


class TaskTimeoutError(TaskError):
    """Task timed out."""
    pass


class TaskDependencyError(TaskError):
    """Task dependency error."""
    pass


# =============================================================================
# TASK EXECUTOR
# =============================================================================

class TaskExecutor:
    """
    Task Executor for BAEL.

    Advanced task execution engine.
    """

    def __init__(
        self,
        max_workers: int = 10,
        queue_size: int = 10000
    ):
        self._max_workers = max_workers
        self._queue = TaskQueue(max_size=queue_size)
        self._dependency_graph = DependencyGraph()
        self._retry_handler = RetryHandler()
        self._running_tasks: Dict[str, Task] = {}
        self._completed_tasks: Dict[str, TaskResult] = {}
        self._callbacks: Dict[str, List[Callable[[TaskResult], None]]] = defaultdict(list)
        self._stats = ExecutionStats()
        self._lock = threading.RLock()
        self._running = False
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._worker_task: Optional[asyncio.Task] = None

    # -------------------------------------------------------------------------
    # TASK SUBMISSION
    # -------------------------------------------------------------------------

    def submit(
        self,
        task: Task,
        dependencies: Optional[List[str]] = None
    ) -> str:
        """Submit a task for execution."""
        # Add dependencies
        if dependencies:
            for dep in dependencies:
                self._dependency_graph.add_dependency(task.task_id, dep)

        self._queue.push(task)

        with self._lock:
            logger.debug(f"Task {task.task_id} submitted")

        return task.task_id

    def submit_function(
        self,
        func: Callable[..., Awaitable[T]],
        *args,
        config: Optional[TaskConfig] = None,
        dependencies: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """Submit a function as a task."""
        task = FunctionTask(
            func=func,
            args=args,
            kwargs=kwargs,
            config=config
        )
        return self.submit(task, dependencies)

    def submit_sync(
        self,
        func: Callable[..., T],
        *args,
        config: Optional[TaskConfig] = None,
        dependencies: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """Submit a sync function as a task."""
        task = SyncFunctionTask(
            func=func,
            args=args,
            kwargs=kwargs,
            config=config
        )
        return self.submit(task, dependencies)

    # -------------------------------------------------------------------------
    # TASK EXECUTION
    # -------------------------------------------------------------------------

    async def execute(self, task: Task[T]) -> TaskResult[T]:
        """Execute a single task with retry logic."""
        task.state = TaskState.RUNNING
        task._progress.started_at = datetime.utcnow()

        with self._lock:
            self._running_tasks[task.task_id] = task

        start_time = time.time()
        attempt = 0
        last_error: Optional[Exception] = None

        while True:
            attempt += 1

            try:
                # Apply timeout if configured
                if task.config.timeout:
                    result = await asyncio.wait_for(
                        task.execute(),
                        timeout=task.config.timeout
                    )
                else:
                    result = await task.execute()

                # Success
                task.state = TaskState.COMPLETED
                execution_time = (time.time() - start_time) * 1000

                task_result = TaskResult(
                    task_id=task.task_id,
                    success=True,
                    value=result,
                    execution_time_ms=execution_time,
                    retry_count=attempt - 1
                )

                self._update_stats(task_result)
                self._mark_completed(task, task_result)

                return task_result

            except asyncio.TimeoutError:
                last_error = TaskTimeoutError(f"Task {task.task_id} timed out")
                task.state = TaskState.TIMEOUT

                with self._lock:
                    self._stats.total_timeout += 1
                break

            except TaskCancelledError:
                task.state = TaskState.CANCELLED

                with self._lock:
                    self._stats.total_cancelled += 1
                break

            except Exception as e:
                last_error = e

                if self._retry_handler.should_retry(task.config, attempt, e):
                    delay = self._retry_handler.calculate_delay(task.config, attempt)

                    with self._lock:
                        self._stats.total_retries += 1

                    logger.debug(f"Task {task.task_id} retry {attempt}, delay {delay}s")
                    await asyncio.sleep(delay)
                    continue

                task.state = TaskState.FAILED
                break

        # Task failed
        execution_time = (time.time() - start_time) * 1000

        task_result = TaskResult(
            task_id=task.task_id,
            success=False,
            error=last_error,
            execution_time_ms=execution_time,
            retry_count=attempt - 1
        )

        self._update_stats(task_result)
        self._mark_completed(task, task_result)

        return task_result

    async def run(
        self,
        func: Callable[..., Awaitable[T]],
        *args,
        config: Optional[TaskConfig] = None,
        **kwargs
    ) -> T:
        """Execute a function and return its result."""
        task = FunctionTask(
            func=func,
            args=args,
            kwargs=kwargs,
            config=config
        )
        result = await self.execute(task)

        if not result.success:
            raise result.error or TaskError("Task failed")

        return result.value

    async def run_all(
        self,
        funcs: List[Callable[..., Awaitable[T]]],
        mode: ExecutionMode = ExecutionMode.PARALLEL,
        config: Optional[TaskConfig] = None
    ) -> List[TaskResult[T]]:
        """Execute multiple functions."""
        tasks = [
            FunctionTask(func=f, config=config)
            for f in funcs
        ]

        if mode == ExecutionMode.SEQUENTIAL:
            results = []
            for task in tasks:
                results.append(await self.execute(task))
            return results
        else:
            return await asyncio.gather(*[self.execute(t) for t in tasks])

    # -------------------------------------------------------------------------
    # WORKER LOOP
    # -------------------------------------------------------------------------

    async def start(self) -> None:
        """Start the executor worker loop."""
        if self._running:
            return

        self._running = True
        self._semaphore = asyncio.Semaphore(self._max_workers)
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("Task Executor started")

    async def stop(self) -> None:
        """Stop the executor."""
        self._running = False

        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

        logger.info("Task Executor stopped")

    async def _worker_loop(self) -> None:
        """Main worker loop."""
        while self._running:
            task = self._queue.pop()

            if not task:
                await asyncio.sleep(0.01)
                continue

            # Check dependencies
            if not self._dependency_graph.is_ready(task.task_id):
                # Re-queue with delay
                self._queue.push(task)
                await asyncio.sleep(0.01)
                continue

            # Execute with semaphore
            async def run_task():
                async with self._semaphore:
                    await self.execute(task)

            asyncio.create_task(run_task())

    # -------------------------------------------------------------------------
    # CALLBACKS
    # -------------------------------------------------------------------------

    def on_complete(
        self,
        task_id: str,
        callback: Callable[[TaskResult], None]
    ) -> None:
        """Register a completion callback."""
        with self._lock:
            # Check if already completed
            if task_id in self._completed_tasks:
                callback(self._completed_tasks[task_id])
            else:
                self._callbacks[task_id].append(callback)

    # -------------------------------------------------------------------------
    # STATUS
    # -------------------------------------------------------------------------

    def get_result(self, task_id: str) -> Optional[TaskResult]:
        """Get a task result."""
        with self._lock:
            return self._completed_tasks.get(task_id)

    def get_progress(self, task_id: str) -> Optional[TaskProgress]:
        """Get task progress."""
        with self._lock:
            task = self._running_tasks.get(task_id)
            if task:
                return task.get_progress()
        return None

    def cancel(self, task_id: str) -> bool:
        """Cancel a task."""
        with self._lock:
            task = self._running_tasks.get(task_id)
            if task:
                task.cancel()
                return True
        return False

    def get_stats(self) -> ExecutionStats:
        """Get execution statistics."""
        with self._lock:
            return ExecutionStats(
                total_executed=self._stats.total_executed,
                total_succeeded=self._stats.total_succeeded,
                total_failed=self._stats.total_failed,
                total_cancelled=self._stats.total_cancelled,
                total_timeout=self._stats.total_timeout,
                avg_execution_time_ms=self._stats.avg_execution_time_ms,
                total_retries=self._stats.total_retries
            )

    @property
    def pending_count(self) -> int:
        return self._queue.size

    @property
    def running_count(self) -> int:
        with self._lock:
            return len(self._running_tasks)

    # -------------------------------------------------------------------------
    # INTERNAL
    # -------------------------------------------------------------------------

    def _update_stats(self, result: TaskResult) -> None:
        """Update statistics."""
        with self._lock:
            self._stats.total_executed += 1

            if result.success:
                self._stats.total_succeeded += 1
            else:
                self._stats.total_failed += 1

            # Update average
            n = self._stats.total_executed
            self._stats.avg_execution_time_ms = (
                (self._stats.avg_execution_time_ms * (n - 1) + result.execution_time_ms) / n
            )

    def _mark_completed(self, task: Task, result: TaskResult) -> None:
        """Mark a task as completed."""
        with self._lock:
            self._completed_tasks[task.task_id] = result
            self._running_tasks.pop(task.task_id, None)

            # Trigger callbacks
            callbacks = self._callbacks.pop(task.task_id, [])

        for callback in callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"Callback error: {e}")

        # Update dependency graph
        self._dependency_graph.mark_completed(task.task_id)


# =============================================================================
# BATCH EXECUTOR
# =============================================================================

class BatchExecutor:
    """Executes tasks in batches."""

    def __init__(
        self,
        executor: TaskExecutor,
        batch_size: int = 10
    ):
        self._executor = executor
        self._batch_size = batch_size

    async def execute_batch(
        self,
        funcs: List[Callable[..., Awaitable[T]]],
        config: Optional[TaskConfig] = None
    ) -> List[TaskResult[T]]:
        """Execute functions in batches."""
        results = []

        for i in range(0, len(funcs), self._batch_size):
            batch = funcs[i:i + self._batch_size]
            batch_results = await self._executor.run_all(batch, config=config)
            results.extend(batch_results)

        return results


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Task Executor."""
    print("=" * 70)
    print("BAEL - TASK EXECUTOR DEMO")
    print("Advanced Task Execution for AI Agents")
    print("=" * 70)
    print()

    executor = TaskExecutor(max_workers=5)

    # 1. Basic Task Execution
    print("1. BASIC TASK EXECUTION:")
    print("-" * 40)

    async def simple_task(x: int) -> int:
        await asyncio.sleep(0.1)
        return x * 2

    result = await executor.run(simple_task, 21)
    print(f"   Input: 21, Result: {result}")
    print()

    # 2. Task with Config
    print("2. TASK WITH CONFIGURATION:")
    print("-" * 40)

    config = TaskConfig(
        timeout=5.0,
        priority=TaskPriority.HIGH
    )

    result = await executor.run(simple_task, 10, config=config)
    print(f"   Priority: HIGH, Timeout: 5s")
    print(f"   Result: {result}")
    print()

    # 3. Parallel Execution
    print("3. PARALLEL EXECUTION:")
    print("-" * 40)

    async def delayed_task(x: int) -> int:
        await asyncio.sleep(0.1)
        return x * x

    funcs = [lambda x=i: delayed_task(x) for i in range(5)]

    start = time.time()
    results = await executor.run_all(funcs, mode=ExecutionMode.PARALLEL)
    elapsed = (time.time() - start) * 1000

    print(f"   5 tasks executed in parallel")
    print(f"   Results: {[r.value for r in results]}")
    print(f"   Total time: {elapsed:.2f}ms (parallel)")
    print()

    # 4. Sequential Execution
    print("4. SEQUENTIAL EXECUTION:")
    print("-" * 40)

    start = time.time()
    results = await executor.run_all(funcs[:3], mode=ExecutionMode.SEQUENTIAL)
    elapsed = (time.time() - start) * 1000

    print(f"   3 tasks executed sequentially")
    print(f"   Results: {[r.value for r in results]}")
    print(f"   Total time: {elapsed:.2f}ms (sequential)")
    print()

    # 5. Retry Logic
    print("5. RETRY LOGIC:")
    print("-" * 40)

    attempt_count = {"count": 0}

    async def flaky_task() -> str:
        attempt_count["count"] += 1
        if attempt_count["count"] < 3:
            raise ValueError(f"Attempt {attempt_count['count']} failed")
        return "success"

    retry_config = TaskConfig(
        retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        max_retries=5,
        retry_delay=0.1
    )

    task = FunctionTask(func=flaky_task, config=retry_config)
    result = await executor.execute(task)

    print(f"   Flaky task succeeded after {result.retry_count} retries")
    print(f"   Total attempts: {attempt_count['count']}")
    print(f"   Result: {result.value}")
    print()

    # 6. Timeout Handling
    print("6. TIMEOUT HANDLING:")
    print("-" * 40)

    async def slow_task() -> str:
        await asyncio.sleep(10)
        return "done"

    timeout_config = TaskConfig(timeout=0.1)
    task = FunctionTask(func=slow_task, config=timeout_config)
    result = await executor.execute(task)

    print(f"   Task timed out: {not result.success}")
    print(f"   Error type: {type(result.error).__name__}")
    print()

    # 7. Task Cancellation
    print("7. TASK CANCELLATION:")
    print("-" * 40)

    cancelled = False

    async def cancellable_task() -> str:
        nonlocal cancelled
        try:
            for i in range(100):
                await asyncio.sleep(0.01)
            return "completed"
        except asyncio.CancelledError:
            cancelled = True
            raise

    task = FunctionTask(func=cancellable_task)

    async def cancel_after_delay():
        await asyncio.sleep(0.1)
        task.cancel()

    asyncio.create_task(cancel_after_delay())
    result = await executor.execute(task)

    print(f"   Task was cancelled: {result.success == False}")
    print(f"   State: {task.state.value}")
    print()

    # 8. Composite Tasks
    print("8. COMPOSITE TASKS:")
    print("-" * 40)

    subtasks = [
        FunctionTask(func=lambda x=i: delayed_task(x))
        for i in range(3)
    ]

    composite = CompositeTask(tasks=subtasks, mode=ExecutionMode.PARALLEL)
    result = await executor.execute(composite)

    print(f"   Composite task executed")
    print(f"   Subtask results: {result.value}")
    print()

    # 9. Task Queue
    print("9. TASK QUEUE:")
    print("-" * 40)

    queue = TaskQueue()

    # Add tasks with different priorities
    for priority in [TaskPriority.LOW, TaskPriority.HIGH, TaskPriority.NORMAL]:
        task = FunctionTask(
            func=lambda: asyncio.sleep(0),
            config=TaskConfig(priority=priority)
        )
        queue.push(task)

    print(f"   Queue size: {queue.size}")

    # Pop should return highest priority first
    first = queue.pop()
    print(f"   First popped: {first.config.priority.name}")
    print()

    # 10. Statistics
    print("10. EXECUTION STATISTICS:")
    print("-" * 40)

    stats = executor.get_stats()
    print(f"   Total executed: {stats.total_executed}")
    print(f"   Succeeded: {stats.total_succeeded}")
    print(f"   Failed: {stats.total_failed}")
    print(f"   Timeouts: {stats.total_timeout}")
    print(f"   Total retries: {stats.total_retries}")
    print(f"   Avg time: {stats.avg_execution_time_ms:.2f}ms")
    print()

    # 11. Worker Mode
    print("11. WORKER MODE (ASYNC QUEUE):")
    print("-" * 40)

    worker_executor = TaskExecutor(max_workers=3)
    await worker_executor.start()

    # Submit tasks
    task_ids = []
    for i in range(5):
        tid = worker_executor.submit_function(simple_task, i)
        task_ids.append(tid)

    print(f"   Submitted {len(task_ids)} tasks")
    print(f"   Pending: {worker_executor.pending_count}")

    # Wait for completion
    await asyncio.sleep(0.5)

    print(f"   After processing - Pending: {worker_executor.pending_count}")

    await worker_executor.stop()
    print("   Worker stopped")
    print()

    # 12. Batch Execution
    print("12. BATCH EXECUTION:")
    print("-" * 40)

    batch_executor = BatchExecutor(executor, batch_size=3)

    batch_funcs = [lambda x=i: delayed_task(x) for i in range(7)]
    results = await batch_executor.execute_batch(batch_funcs)

    print(f"   7 tasks in batches of 3")
    print(f"   Results: {[r.value for r in results]}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Task Executor Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
