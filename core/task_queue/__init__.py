"""
BAEL Task Queue Engine Implementation
======================================

In-memory task queue with priorities and scheduling.

"Ba'el orchestrates all tasks with divine order." — Ba'el
"""

import asyncio
import heapq
import logging
import threading
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("BAEL.TaskQueue")


# ============================================================================
# ENUMS
# ============================================================================

class TaskPriority(Enum):
    """Task priorities."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class TaskState(Enum):
    """Task states."""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class ExecutionMode(Enum):
    """Execution modes."""
    IMMEDIATE = "immediate"
    DELAYED = "delayed"
    SCHEDULED = "scheduled"
    RECURRING = "recurring"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Task:
    """A task in the queue."""
    id: str
    name: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)

    # Execution
    priority: TaskPriority = TaskPriority.NORMAL
    mode: ExecutionMode = ExecutionMode.IMMEDIATE
    execute_at: Optional[float] = None
    interval: Optional[float] = None  # For recurring

    # State
    state: TaskState = TaskState.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    # Result
    result: Any = None
    error: Optional[str] = None

    # Retry
    max_retries: int = 3
    retry_count: int = 0
    retry_delay: float = 1.0

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other: 'Task') -> bool:
        """Comparison for priority queue."""
        if self.execute_at and other.execute_at:
            if self.execute_at != other.execute_at:
                return self.execute_at < other.execute_at
        return self.priority.value < other.priority.value

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'priority': self.priority.value,
            'state': self.state.value,
            'created_at': self.created_at,
            'error': self.error,
            'retry_count': self.retry_count
        }


@dataclass
class TaskQueueConfig:
    """Task queue configuration."""
    max_workers: int = 4
    max_queue_size: int = 10000
    default_priority: TaskPriority = TaskPriority.NORMAL
    default_max_retries: int = 3
    poll_interval: float = 0.1


@dataclass
class QueueStats:
    """Queue statistics."""
    pending: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0
    cancelled: int = 0
    total_processed: int = 0
    avg_execution_time: float = 0.0


# ============================================================================
# TASK QUEUE ENGINE
# ============================================================================

class TaskQueueEngine:
    """
    In-memory task queue engine.

    Features:
    - Priority-based ordering
    - Delayed/scheduled execution
    - Recurring tasks
    - Automatic retries

    "Ba'el executes all tasks in perfect order." — Ba'el
    """

    def __init__(self, config: Optional[TaskQueueConfig] = None):
        """Initialize task queue."""
        self.config = config or TaskQueueConfig()

        # Priority queue (min-heap)
        self._queue: List[Task] = []

        # Task storage
        self._tasks: Dict[str, Task] = {}

        # Recurring tasks
        self._recurring: Dict[str, Task] = {}

        # Running tasks
        self._running: Dict[str, Task] = {}

        # Results
        self._results: Dict[str, Any] = {}

        # Workers
        self._workers: List[asyncio.Task] = []
        self._running_flag = False

        # Stats
        self._stats = QueueStats()
        self._execution_times: List[float] = []

        # Thread safety
        self._lock = threading.RLock()
        self._queue_lock = asyncio.Lock() if asyncio.get_event_loop_policy() else None

        # Event loop
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        logger.info(
            f"Task queue initialized (workers={self.config.max_workers})"
        )

    # ========================================================================
    # TASK SUBMISSION
    # ========================================================================

    def submit(
        self,
        func: Callable,
        *args,
        name: Optional[str] = None,
        priority: Optional[TaskPriority] = None,
        delay: Optional[float] = None,
        execute_at: Optional[datetime] = None,
        max_retries: Optional[int] = None,
        metadata: Optional[Dict] = None,
        **kwargs
    ) -> str:
        """
        Submit a task to the queue.

        Args:
            func: Function to execute
            *args: Function arguments
            name: Task name
            priority: Task priority
            delay: Delay before execution
            execute_at: Specific execution time
            max_retries: Maximum retry attempts
            metadata: Task metadata
            **kwargs: Function keyword arguments

        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())

        # Calculate execution time
        exec_time = None
        mode = ExecutionMode.IMMEDIATE

        if delay:
            exec_time = time.time() + delay
            mode = ExecutionMode.DELAYED
        elif execute_at:
            exec_time = execute_at.timestamp()
            mode = ExecutionMode.SCHEDULED

        task = Task(
            id=task_id,
            name=name or func.__name__,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority or self.config.default_priority,
            mode=mode,
            execute_at=exec_time,
            max_retries=max_retries or self.config.default_max_retries,
            metadata=metadata or {}
        )

        with self._lock:
            self._tasks[task_id] = task
            heapq.heappush(self._queue, task)
            self._stats.pending += 1

        logger.debug(f"Task submitted: {task_id} ({task.name})")

        return task_id

    def submit_recurring(
        self,
        func: Callable,
        interval: float,
        *args,
        name: Optional[str] = None,
        priority: Optional[TaskPriority] = None,
        start_delay: float = 0,
        **kwargs
    ) -> str:
        """
        Submit a recurring task.

        Args:
            func: Function to execute
            interval: Interval between executions (seconds)
            *args: Function arguments
            name: Task name
            priority: Task priority
            start_delay: Initial delay
            **kwargs: Function keyword arguments

        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())

        task = Task(
            id=task_id,
            name=name or func.__name__,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority or self.config.default_priority,
            mode=ExecutionMode.RECURRING,
            interval=interval,
            execute_at=time.time() + start_delay
        )

        with self._lock:
            self._tasks[task_id] = task
            self._recurring[task_id] = task
            heapq.heappush(self._queue, task)
            self._stats.pending += 1

        return task_id

    # ========================================================================
    # TASK MANAGEMENT
    # ========================================================================

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        return self._tasks.get(task_id)

    def cancel(self, task_id: str) -> bool:
        """
        Cancel a task.

        Args:
            task_id: Task ID

        Returns:
            True if cancelled
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False

            if task.state in (TaskState.RUNNING, TaskState.COMPLETED):
                return False

            task.state = TaskState.CANCELLED
            self._stats.cancelled += 1
            self._stats.pending -= 1

            # Remove from recurring
            self._recurring.pop(task_id, None)

        return True

    def get_result(
        self,
        task_id: str,
        timeout: Optional[float] = None
    ) -> Any:
        """
        Get task result (blocks until complete).

        Args:
            task_id: Task ID
            timeout: Maximum wait time

        Returns:
            Task result

        Raises:
            TimeoutError: If timeout exceeded
            Exception: If task failed
        """
        deadline = time.time() + timeout if timeout else None

        while True:
            task = self._tasks.get(task_id)

            if not task:
                raise ValueError(f"Unknown task: {task_id}")

            if task.state == TaskState.COMPLETED:
                return task.result

            if task.state == TaskState.FAILED:
                raise Exception(task.error)

            if task.state == TaskState.CANCELLED:
                raise Exception("Task was cancelled")

            if deadline and time.time() > deadline:
                raise TimeoutError("Timeout waiting for task")

            time.sleep(0.01)

    async def get_result_async(
        self,
        task_id: str,
        timeout: Optional[float] = None
    ) -> Any:
        """Get task result asynchronously."""
        deadline = time.time() + timeout if timeout else None

        while True:
            task = self._tasks.get(task_id)

            if not task:
                raise ValueError(f"Unknown task: {task_id}")

            if task.state == TaskState.COMPLETED:
                return task.result

            if task.state == TaskState.FAILED:
                raise Exception(task.error)

            if task.state == TaskState.CANCELLED:
                raise Exception("Task was cancelled")

            if deadline and time.time() > deadline:
                raise TimeoutError("Timeout waiting for task")

            await asyncio.sleep(0.01)

    # ========================================================================
    # EXECUTION
    # ========================================================================

    async def start(self) -> None:
        """Start the task queue workers."""
        if self._running_flag:
            return

        self._running_flag = True
        self._loop = asyncio.get_event_loop()

        # Start workers
        for i in range(self.config.max_workers):
            worker = asyncio.create_task(self._worker_loop(i))
            self._workers.append(worker)

        logger.info(f"Task queue started with {len(self._workers)} workers")

    async def stop(self, wait: bool = True) -> None:
        """Stop the task queue."""
        self._running_flag = False

        if wait:
            # Wait for workers
            for worker in self._workers:
                worker.cancel()
                try:
                    await worker
                except asyncio.CancelledError:
                    pass

        self._workers.clear()
        logger.info("Task queue stopped")

    async def _worker_loop(self, worker_id: int) -> None:
        """Worker loop for processing tasks."""
        logger.debug(f"Worker {worker_id} started")

        while self._running_flag:
            task = await self._get_next_task()

            if task:
                await self._execute_task(task)
            else:
                await asyncio.sleep(self.config.poll_interval)

        logger.debug(f"Worker {worker_id} stopped")

    async def _get_next_task(self) -> Optional[Task]:
        """Get next task from queue."""
        with self._lock:
            now = time.time()

            while self._queue:
                task = heapq.heappop(self._queue)

                # Check if cancelled
                if task.state == TaskState.CANCELLED:
                    continue

                # Check execution time
                if task.execute_at and task.execute_at > now:
                    heapq.heappush(self._queue, task)
                    return None

                # Ready to execute
                task.state = TaskState.RUNNING
                task.started_at = now
                self._running[task.id] = task
                self._stats.pending -= 1
                self._stats.running += 1

                return task

        return None

    async def _execute_task(self, task: Task) -> None:
        """Execute a task."""
        start_time = time.time()

        try:
            # Execute function
            if asyncio.iscoroutinefunction(task.func):
                result = await task.func(*task.args, **task.kwargs)
            else:
                result = await asyncio.to_thread(
                    task.func, *task.args, **task.kwargs
                )

            # Success
            task.state = TaskState.COMPLETED
            task.result = result
            task.completed_at = time.time()

            self._stats.completed += 1
            self._stats.total_processed += 1

            execution_time = time.time() - start_time
            self._execution_times.append(execution_time)

            logger.debug(f"Task completed: {task.id} ({execution_time:.3f}s)")

        except Exception as e:
            logger.error(f"Task failed: {task.id} - {e}")

            # Check retries
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.state = TaskState.RETRYING
                task.execute_at = time.time() + (task.retry_delay * task.retry_count)

                with self._lock:
                    heapq.heappush(self._queue, task)
                    self._stats.pending += 1

                logger.info(
                    f"Task {task.id} retry {task.retry_count}/{task.max_retries}"
                )
            else:
                task.state = TaskState.FAILED
                task.error = str(e)
                task.completed_at = time.time()

                self._stats.failed += 1
                self._stats.total_processed += 1

        finally:
            with self._lock:
                self._running.pop(task.id, None)
                self._stats.running -= 1

            # Re-schedule recurring tasks
            if (task.mode == ExecutionMode.RECURRING and
                task.state == TaskState.COMPLETED and
                task.id in self._recurring):

                task.state = TaskState.SCHEDULED
                task.execute_at = time.time() + task.interval

                with self._lock:
                    heapq.heappush(self._queue, task)
                    self._stats.pending += 1

    # ========================================================================
    # SYNCHRONOUS EXECUTION
    # ========================================================================

    def run_sync(self, task_id: str) -> Any:
        """
        Run a task synchronously (blocking).

        Args:
            task_id: Task ID

        Returns:
            Task result
        """
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Unknown task: {task_id}")

        task.state = TaskState.RUNNING
        task.started_at = time.time()

        try:
            if asyncio.iscoroutinefunction(task.func):
                result = asyncio.run(task.func(*task.args, **task.kwargs))
            else:
                result = task.func(*task.args, **task.kwargs)

            task.state = TaskState.COMPLETED
            task.result = result
            task.completed_at = time.time()

            return result

        except Exception as e:
            task.state = TaskState.FAILED
            task.error = str(e)
            task.completed_at = time.time()
            raise

    # ========================================================================
    # STATS
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        avg_time = (
            sum(self._execution_times) / len(self._execution_times)
            if self._execution_times else 0
        )

        return {
            'pending': self._stats.pending,
            'running': self._stats.running,
            'completed': self._stats.completed,
            'failed': self._stats.failed,
            'cancelled': self._stats.cancelled,
            'total_processed': self._stats.total_processed,
            'avg_execution_time': avg_time,
            'queue_size': len(self._queue),
            'workers': len(self._workers)
        }

    def get_pending_tasks(self) -> List[Dict]:
        """Get pending tasks."""
        return [
            t.to_dict() for t in self._tasks.values()
            if t.state == TaskState.PENDING
        ]

    def get_running_tasks(self) -> List[Dict]:
        """Get running tasks."""
        return [t.to_dict() for t in self._running.values()]


# ============================================================================
# CONVENIENCE
# ============================================================================

_queue: Optional[TaskQueueEngine] = None


def get_task_queue(
    config: Optional[TaskQueueConfig] = None
) -> TaskQueueEngine:
    """Get or create task queue."""
    global _queue
    if _queue is None:
        _queue = TaskQueueEngine(config)
    return _queue


def submit_task(
    func: Callable,
    *args,
    **kwargs
) -> str:
    """Submit a task to the global queue."""
    return get_task_queue().submit(func, *args, **kwargs)


def submit_delayed(
    func: Callable,
    delay: float,
    *args,
    **kwargs
) -> str:
    """Submit a delayed task."""
    return get_task_queue().submit(func, *args, delay=delay, **kwargs)


async def start_queue() -> None:
    """Start the global task queue."""
    await get_task_queue().start()


async def stop_queue() -> None:
    """Stop the global task queue."""
    await get_task_queue().stop()
