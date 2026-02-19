"""
BAEL Task Scheduler Engine
==========================

Advanced task scheduling with cron expressions, intervals, dependencies,
and intelligent retry mechanisms.

Features:
- Cron expression scheduling
- Interval-based execution
- Task dependencies with DAG resolution
- Priority queuing with aging
- Retry policies with exponential backoff
- Task result persistence
- Concurrent execution with limits

"Every moment serves a purpose in Ba'el's grand design." — Ba'el
"""

import asyncio
import logging
import re
import heapq
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Set, Tuple, Awaitable, Union
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import defaultdict
import uuid
import traceback
import json
from pathlib import Path

logger = logging.getLogger("BAEL.TaskScheduler")


# ============================================================================
# ENUMS
# ============================================================================

class TaskStatus(Enum):
    """Status of a scheduled task."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING_DEPS = "waiting_deps"
    RETRYING = "retrying"
    SKIPPED = "skipped"


class TaskPriority(Enum):
    """Priority levels for tasks."""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5


class ScheduleType(Enum):
    """Types of scheduling."""
    ONCE = "once"           # Run once at specific time
    INTERVAL = "interval"   # Run every N seconds/minutes/hours
    CRON = "cron"          # Cron expression
    DEPENDENCY = "dependency"  # Run after dependencies complete
    IMMEDIATE = "immediate"    # Run immediately
    MANUAL = "manual"          # Only run when triggered


class RetryPolicy(Enum):
    """Retry behavior policies."""
    NONE = "none"              # No retry
    IMMEDIATE = "immediate"     # Retry immediately
    LINEAR = "linear"          # Linear backoff
    EXPONENTIAL = "exponential"  # Exponential backoff
    FIBONACCI = "fibonacci"      # Fibonacci sequence backoff


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Schedule:
    """Scheduling configuration for a task."""
    type: ScheduleType

    # For ONCE
    run_at: Optional[datetime] = None

    # For INTERVAL
    interval_seconds: int = 0

    # For CRON
    cron_expression: Optional[str] = None

    # For DEPENDENCY
    depends_on: List[str] = field(default_factory=list)

    # Common
    timezone: str = "UTC"
    start_after: Optional[datetime] = None
    end_before: Optional[datetime] = None
    max_runs: Optional[int] = None


@dataclass
class TaskDependency:
    """Task dependency definition."""
    task_id: str
    require_success: bool = True  # Require successful completion
    timeout_seconds: int = 3600   # Max wait time


@dataclass
class TaskResult:
    """Result of a task execution."""
    task_id: str
    status: TaskStatus
    started_at: datetime
    completed_at: datetime
    result: Any = None
    error: Optional[str] = None
    execution_time_ms: int = 0
    attempt: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    """A scheduled task definition."""
    id: str
    name: str
    handler: Callable[..., Awaitable[Any]]
    schedule: Schedule

    # Configuration
    priority: TaskPriority = TaskPriority.NORMAL
    timeout_seconds: int = 300
    max_retries: int = 3
    retry_policy: RetryPolicy = RetryPolicy.EXPONENTIAL
    retry_delay_seconds: int = 10

    # State
    status: TaskStatus = TaskStatus.PENDING
    run_count: int = 0
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    current_attempt: int = 0

    # Arguments
    args: Tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    # History
    results: List[TaskResult] = field(default_factory=list)


@dataclass
class SchedulerConfig:
    """Configuration for the task scheduler."""
    max_concurrent_tasks: int = 10
    default_timeout_seconds: int = 300
    tick_interval_seconds: float = 1.0
    priority_aging_seconds: int = 60
    priority_aging_factor: float = 0.1
    persist_results: bool = True
    result_retention_count: int = 100
    enable_dead_letter_queue: bool = True


# ============================================================================
# CRON PARSER
# ============================================================================

class CronParser:
    """
    Parse and evaluate cron expressions.

    Format: minute hour day-of-month month day-of-week

    Examples:
    - "* * * * *" - Every minute
    - "0 * * * *" - Every hour
    - "0 0 * * *" - Every day at midnight
    - "0 0 * * 0" - Every Sunday at midnight
    - "0 0 1 * *" - First day of every month
    - "*/15 * * * *" - Every 15 minutes
    - "0 9-17 * * 1-5" - 9 AM to 5 PM, Monday to Friday
    """

    FIELD_NAMES = ['minute', 'hour', 'day', 'month', 'weekday']
    FIELD_RANGES = [
        (0, 59),   # minute
        (0, 23),   # hour
        (1, 31),   # day
        (1, 12),   # month
        (0, 6)     # weekday (0 = Sunday)
    ]

    # Named values
    MONTH_NAMES = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }

    WEEKDAY_NAMES = {
        'sun': 0, 'mon': 1, 'tue': 2, 'wed': 3, 'thu': 4, 'fri': 5, 'sat': 6
    }

    def __init__(self, expression: str):
        """Parse a cron expression."""
        self.expression = expression
        self.fields = self._parse(expression)

    def _parse(self, expression: str) -> List[Set[int]]:
        """Parse cron expression into field sets."""
        parts = expression.strip().split()

        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: expected 5 fields, got {len(parts)}")

        fields = []
        for i, part in enumerate(parts):
            field_range = self.FIELD_RANGES[i]
            values = self._parse_field(part, field_range, i)
            fields.append(values)

        return fields

    def _parse_field(self, field: str, range_: Tuple[int, int], field_idx: int) -> Set[int]:
        """Parse a single cron field."""
        min_val, max_val = range_
        values = set()

        for part in field.split(','):
            if part == '*':
                values.update(range(min_val, max_val + 1))
            elif '/' in part:
                base, step = part.split('/')
                step = int(step)
                if base == '*':
                    start = min_val
                else:
                    start = self._parse_value(base, field_idx)
                values.update(range(start, max_val + 1, step))
            elif '-' in part:
                start, end = part.split('-')
                start = self._parse_value(start, field_idx)
                end = self._parse_value(end, field_idx)
                values.update(range(start, end + 1))
            else:
                values.add(self._parse_value(part, field_idx))

        return values

    def _parse_value(self, value: str, field_idx: int) -> int:
        """Parse a single value, handling names."""
        value_lower = value.lower()

        if field_idx == 3:  # Month
            if value_lower in self.MONTH_NAMES:
                return self.MONTH_NAMES[value_lower]
        elif field_idx == 4:  # Weekday
            if value_lower in self.WEEKDAY_NAMES:
                return self.WEEKDAY_NAMES[value_lower]

        return int(value)

    def matches(self, dt: datetime) -> bool:
        """Check if a datetime matches the cron expression."""
        return (
            dt.minute in self.fields[0] and
            dt.hour in self.fields[1] and
            dt.day in self.fields[2] and
            dt.month in self.fields[3] and
            dt.weekday() in self.fields[4]  # Monday = 0 in Python
        )

    def next_run(self, after: Optional[datetime] = None) -> datetime:
        """Calculate the next run time after the given datetime."""
        if after is None:
            after = datetime.now()

        # Start from the next minute
        current = after.replace(second=0, microsecond=0) + timedelta(minutes=1)

        # Find next matching time (max 2 years ahead)
        max_iterations = 60 * 24 * 365 * 2  # ~2 years of minutes

        for _ in range(max_iterations):
            if self.matches(current):
                return current
            current += timedelta(minutes=1)

        raise ValueError(f"Could not find next run time for: {self.expression}")


# ============================================================================
# TASK QUEUE
# ============================================================================

class TaskQueue:
    """
    Priority queue for tasks with aging support.

    Tasks age over time, increasing their priority to prevent starvation.
    """

    def __init__(self, config: SchedulerConfig):
        """Initialize task queue."""
        self.config = config
        self._queue: List[Tuple[float, str, Task]] = []
        self._tasks: Dict[str, Task] = {}
        self._counter = 0

    def push(self, task: Task) -> None:
        """Add a task to the queue."""
        priority = self._calculate_priority(task)
        heapq.heappush(self._queue, (priority, task.id, task))
        self._tasks[task.id] = task

    def pop(self) -> Optional[Task]:
        """Remove and return the highest priority task."""
        while self._queue:
            priority, task_id, task = heapq.heappop(self._queue)
            if task_id in self._tasks:
                del self._tasks[task_id]
                return task
        return None

    def peek(self) -> Optional[Task]:
        """Return the highest priority task without removing it."""
        while self._queue:
            priority, task_id, task = self._queue[0]
            if task_id in self._tasks:
                return task
            heapq.heappop(self._queue)
        return None

    def remove(self, task_id: str) -> bool:
        """Remove a task from the queue."""
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False

    def _calculate_priority(self, task: Task) -> float:
        """Calculate effective priority with aging."""
        base = task.priority.value

        # Apply aging based on queue time
        age_factor = 0.0
        if task.created_at:
            age_seconds = (datetime.now() - task.created_at).total_seconds()
            age_factor = (age_seconds / self.config.priority_aging_seconds) * self.config.priority_aging_factor

        return base - age_factor

    def refresh_priorities(self) -> None:
        """Refresh all priorities to account for aging."""
        new_queue = []
        for _, task_id, task in self._queue:
            if task_id in self._tasks:
                priority = self._calculate_priority(task)
                new_queue.append((priority, task_id, task))
        heapq.heapify(new_queue)
        self._queue = new_queue

    def __len__(self) -> int:
        return len(self._tasks)

    def is_empty(self) -> bool:
        return len(self._tasks) == 0


# ============================================================================
# DEPENDENCY RESOLVER
# ============================================================================

class DependencyResolver:
    """
    Resolve task dependencies using topological sorting.

    Detects cycles and determines execution order.
    """

    def __init__(self):
        """Initialize dependency resolver."""
        self._dependencies: Dict[str, Set[str]] = defaultdict(set)
        self._dependents: Dict[str, Set[str]] = defaultdict(set)

    def add_dependency(self, task_id: str, depends_on: str) -> None:
        """Add a dependency relationship."""
        self._dependencies[task_id].add(depends_on)
        self._dependents[depends_on].add(task_id)

    def remove_task(self, task_id: str) -> None:
        """Remove a task and its dependencies."""
        # Remove from dependencies
        for dep_id in self._dependencies.pop(task_id, set()):
            self._dependents[dep_id].discard(task_id)

        # Remove from dependents
        for dependent_id in self._dependents.pop(task_id, set()):
            self._dependencies[dependent_id].discard(task_id)

    def get_dependencies(self, task_id: str) -> Set[str]:
        """Get all dependencies for a task."""
        return self._dependencies.get(task_id, set())

    def get_dependents(self, task_id: str) -> Set[str]:
        """Get all tasks that depend on this task."""
        return self._dependents.get(task_id, set())

    def can_run(self, task_id: str, completed_tasks: Set[str]) -> bool:
        """Check if a task can run based on completed dependencies."""
        deps = self._dependencies.get(task_id, set())
        return deps.issubset(completed_tasks)

    def has_cycle(self) -> bool:
        """Check if there are any dependency cycles."""
        try:
            self.topological_sort()
            return False
        except ValueError:
            return True

    def topological_sort(self) -> List[str]:
        """Return tasks in dependency order."""
        in_degree = defaultdict(int)
        all_tasks = set(self._dependencies.keys()) | set(self._dependents.keys())

        for task_id in all_tasks:
            in_degree[task_id] = len(self._dependencies.get(task_id, set()))

        queue = [t for t in all_tasks if in_degree[t] == 0]
        result = []

        while queue:
            task_id = queue.pop(0)
            result.append(task_id)

            for dependent in self._dependents.get(task_id, set()):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(result) != len(all_tasks):
            raise ValueError("Dependency cycle detected")

        return result


# ============================================================================
# TASK EXECUTOR
# ============================================================================

class TaskExecutor:
    """
    Execute tasks with timeout, retry, and result handling.
    """

    def __init__(self, config: SchedulerConfig):
        """Initialize task executor."""
        self.config = config
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._dead_letter_queue: List[TaskResult] = []

    async def execute(self, task: Task) -> TaskResult:
        """Execute a task with full lifecycle management."""
        started_at = datetime.now()
        task.status = TaskStatus.RUNNING
        task.current_attempt += 1

        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                task.handler(*task.args, **task.kwargs),
                timeout=task.timeout_seconds
            )

            completed_at = datetime.now()
            execution_time = int((completed_at - started_at).total_seconds() * 1000)

            task_result = TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                started_at=started_at,
                completed_at=completed_at,
                result=result,
                execution_time_ms=execution_time,
                attempt=task.current_attempt
            )

            task.status = TaskStatus.COMPLETED
            task.last_run = completed_at
            task.run_count += 1

            logger.info(f"Task {task.name} completed in {execution_time}ms")

        except asyncio.TimeoutError:
            completed_at = datetime.now()
            execution_time = int((completed_at - started_at).total_seconds() * 1000)

            task_result = TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                started_at=started_at,
                completed_at=completed_at,
                error=f"Task timed out after {task.timeout_seconds}s",
                execution_time_ms=execution_time,
                attempt=task.current_attempt
            )

            task.status = TaskStatus.FAILED
            logger.error(f"Task {task.name} timed out")

        except Exception as e:
            completed_at = datetime.now()
            execution_time = int((completed_at - started_at).total_seconds() * 1000)

            task_result = TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                started_at=started_at,
                completed_at=completed_at,
                error=f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}",
                execution_time_ms=execution_time,
                attempt=task.current_attempt
            )

            task.status = TaskStatus.FAILED
            logger.error(f"Task {task.name} failed: {e}")

        # Store result
        task.results.append(task_result)

        # Trim results if needed
        if len(task.results) > self.config.result_retention_count:
            task.results = task.results[-self.config.result_retention_count:]

        # Handle failure with retry
        if task_result.status == TaskStatus.FAILED and self._should_retry(task):
            task.status = TaskStatus.RETRYING
            task_result.metadata['will_retry'] = True
            task_result.metadata['retry_delay'] = self._get_retry_delay(task)
        elif task_result.status == TaskStatus.FAILED and self.config.enable_dead_letter_queue:
            self._dead_letter_queue.append(task_result)

        return task_result

    def _should_retry(self, task: Task) -> bool:
        """Determine if a task should be retried."""
        if task.retry_policy == RetryPolicy.NONE:
            return False
        return task.current_attempt < task.max_retries

    def _get_retry_delay(self, task: Task) -> int:
        """Calculate retry delay based on policy."""
        attempt = task.current_attempt
        base_delay = task.retry_delay_seconds

        if task.retry_policy == RetryPolicy.IMMEDIATE:
            return 0
        elif task.retry_policy == RetryPolicy.LINEAR:
            return base_delay * attempt
        elif task.retry_policy == RetryPolicy.EXPONENTIAL:
            return base_delay * (2 ** (attempt - 1))
        elif task.retry_policy == RetryPolicy.FIBONACCI:
            # Fibonacci sequence
            a, b = 1, 1
            for _ in range(attempt - 1):
                a, b = b, a + b
            return base_delay * a

        return base_delay

    def get_dead_letter_queue(self) -> List[TaskResult]:
        """Get failed tasks that exhausted retries."""
        return self._dead_letter_queue.copy()

    def clear_dead_letter_queue(self) -> int:
        """Clear the dead letter queue."""
        count = len(self._dead_letter_queue)
        self._dead_letter_queue.clear()
        return count


# ============================================================================
# MAIN TASK SCHEDULER
# ============================================================================

class TaskScheduler:
    """
    Main task scheduler engine.

    Manages task lifecycle:
    1. Registration - Define tasks with schedules
    2. Scheduling - Calculate next run times
    3. Queuing - Priority-based queuing
    4. Execution - Run with timeout and retry
    5. Persistence - Store results

    Features:
    - Cron expression scheduling
    - Interval-based execution
    - Task dependencies with DAG resolution
    - Priority queuing with aging
    - Retry policies with backoff
    - Concurrent execution with limits
    - Dead letter queue for failed tasks
    """

    def __init__(self, config: Optional[SchedulerConfig] = None):
        """Initialize task scheduler."""
        self.config = config or SchedulerConfig()

        # Components
        self.queue = TaskQueue(self.config)
        self.executor = TaskExecutor(self.config)
        self.dependency_resolver = DependencyResolver()

        # Task registry
        self._tasks: Dict[str, Task] = {}
        self._completed_task_ids: Set[str] = set()

        # State
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        self._running_count = 0
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent_tasks)

        # Statistics
        self._stats = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'retried_tasks': 0,
            'cancelled_tasks': 0
        }

        logger.info("TaskScheduler initialized")

    # ========================================================================
    # TASK REGISTRATION
    # ========================================================================

    def register(
        self,
        name: str,
        handler: Callable[..., Awaitable[Any]],
        schedule: Schedule,
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout_seconds: int = 300,
        max_retries: int = 3,
        retry_policy: RetryPolicy = RetryPolicy.EXPONENTIAL,
        retry_delay_seconds: int = 10,
        args: Tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        task_id: Optional[str] = None
    ) -> Task:
        """Register a new task."""
        task = Task(
            id=task_id or str(uuid.uuid4()),
            name=name,
            handler=handler,
            schedule=schedule,
            priority=priority,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            retry_policy=retry_policy,
            retry_delay_seconds=retry_delay_seconds,
            args=args,
            kwargs=kwargs or {},
            tags=tags or []
        )

        # Register dependencies
        if schedule.type == ScheduleType.DEPENDENCY:
            for dep_id in schedule.depends_on:
                self.dependency_resolver.add_dependency(task.id, dep_id)

        # Calculate initial next run
        task.next_run = self._calculate_next_run(task)

        self._tasks[task.id] = task
        self._stats['total_tasks'] += 1

        logger.info(f"Registered task: {name} (ID: {task.id})")
        return task

    def unregister(self, task_id: str) -> bool:
        """Unregister a task."""
        if task_id in self._tasks:
            task = self._tasks.pop(task_id)
            self.dependency_resolver.remove_task(task_id)
            self.queue.remove(task_id)
            logger.info(f"Unregistered task: {task.name}")
            return True
        return False

    # ========================================================================
    # DECORATORS
    # ========================================================================

    def task(
        self,
        name: Optional[str] = None,
        schedule: Optional[Schedule] = None,
        **kwargs
    ) -> Callable:
        """Decorator to register a function as a task."""
        def decorator(func: Callable[..., Awaitable[Any]]) -> Callable:
            task_name = name or func.__name__
            task_schedule = schedule or Schedule(type=ScheduleType.MANUAL)
            self.register(task_name, func, task_schedule, **kwargs)
            return func
        return decorator

    def cron(
        self,
        expression: str,
        name: Optional[str] = None,
        **kwargs
    ) -> Callable:
        """Decorator for cron-scheduled tasks."""
        def decorator(func: Callable[..., Awaitable[Any]]) -> Callable:
            task_name = name or func.__name__
            schedule = Schedule(type=ScheduleType.CRON, cron_expression=expression)
            self.register(task_name, func, schedule, **kwargs)
            return func
        return decorator

    def interval(
        self,
        seconds: int = 0,
        minutes: int = 0,
        hours: int = 0,
        name: Optional[str] = None,
        **kwargs
    ) -> Callable:
        """Decorator for interval-scheduled tasks."""
        def decorator(func: Callable[..., Awaitable[Any]]) -> Callable:
            task_name = name or func.__name__
            total_seconds = seconds + (minutes * 60) + (hours * 3600)
            schedule = Schedule(type=ScheduleType.INTERVAL, interval_seconds=total_seconds)
            self.register(task_name, func, schedule, **kwargs)
            return func
        return decorator

    # ========================================================================
    # SCHEDULING
    # ========================================================================

    def _calculate_next_run(self, task: Task) -> Optional[datetime]:
        """Calculate the next run time for a task."""
        now = datetime.now()
        schedule = task.schedule

        # Check time bounds
        if schedule.start_after and now < schedule.start_after:
            return schedule.start_after

        if schedule.end_before and now >= schedule.end_before:
            return None

        # Check max runs
        if schedule.max_runs and task.run_count >= schedule.max_runs:
            return None

        if schedule.type == ScheduleType.IMMEDIATE:
            return now

        elif schedule.type == ScheduleType.ONCE:
            if task.run_count == 0 and schedule.run_at and schedule.run_at > now:
                return schedule.run_at
            return None

        elif schedule.type == ScheduleType.INTERVAL:
            if task.last_run:
                return task.last_run + timedelta(seconds=schedule.interval_seconds)
            return now

        elif schedule.type == ScheduleType.CRON:
            if schedule.cron_expression:
                parser = CronParser(schedule.cron_expression)
                return parser.next_run(now)
            return None

        elif schedule.type == ScheduleType.DEPENDENCY:
            # Will be scheduled when dependencies complete
            return None

        elif schedule.type == ScheduleType.MANUAL:
            return None

        return None

    # ========================================================================
    # EXECUTION
    # ========================================================================

    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            return

        self._running = True
        self._scheduler_task = asyncio.create_task(self._run_scheduler())
        logger.info("TaskScheduler started")

    async def stop(self) -> None:
        """Stop the scheduler."""
        if not self._running:
            return

        self._running = False

        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

        logger.info("TaskScheduler stopped")

    async def _run_scheduler(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                await self._tick()
                await asyncio.sleep(self.config.tick_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler tick error: {e}")

    async def _tick(self) -> None:
        """Single scheduler tick - check and queue ready tasks."""
        now = datetime.now()

        for task_id, task in list(self._tasks.items()):
            if task.status in [TaskStatus.RUNNING, TaskStatus.QUEUED]:
                continue

            # Handle retrying tasks
            if task.status == TaskStatus.RETRYING:
                if task.results:
                    last_result = task.results[-1]
                    retry_delay = last_result.metadata.get('retry_delay', 0)
                    retry_after = last_result.completed_at + timedelta(seconds=retry_delay)
                    if now >= retry_after:
                        self._queue_task(task)
                        self._stats['retried_tasks'] += 1
                continue

            # Check dependency tasks
            if task.schedule.type == ScheduleType.DEPENDENCY:
                if self.dependency_resolver.can_run(task.id, self._completed_task_ids):
                    self._queue_task(task)
                continue

            # Check scheduled tasks
            if task.next_run and now >= task.next_run:
                self._queue_task(task)

        # Execute queued tasks
        while not self.queue.is_empty() and self._running_count < self.config.max_concurrent_tasks:
            task = self.queue.pop()
            if task:
                asyncio.create_task(self._execute_task(task))

        # Refresh queue priorities periodically
        self.queue.refresh_priorities()

    def _queue_task(self, task: Task) -> None:
        """Add a task to the execution queue."""
        task.status = TaskStatus.QUEUED
        self.queue.push(task)
        logger.debug(f"Queued task: {task.name}")

    async def _execute_task(self, task: Task) -> None:
        """Execute a task with concurrency control."""
        async with self._semaphore:
            self._running_count += 1
            try:
                result = await self.executor.execute(task)

                if result.status == TaskStatus.COMPLETED:
                    self._stats['completed_tasks'] += 1
                    self._completed_task_ids.add(task.id)

                    # Schedule dependents
                    for dependent_id in self.dependency_resolver.get_dependents(task.id):
                        if dependent_id in self._tasks:
                            dependent = self._tasks[dependent_id]
                            if dependent.status == TaskStatus.WAITING_DEPS:
                                if self.dependency_resolver.can_run(dependent_id, self._completed_task_ids):
                                    self._queue_task(dependent)

                    # Calculate next run
                    task.next_run = self._calculate_next_run(task)
                    if task.next_run:
                        task.status = TaskStatus.PENDING

                elif result.status == TaskStatus.FAILED:
                    if task.status != TaskStatus.RETRYING:
                        self._stats['failed_tasks'] += 1

            finally:
                self._running_count -= 1

    # ========================================================================
    # MANUAL TRIGGERS
    # ========================================================================

    async def run_now(self, task_id: str) -> Optional[TaskResult]:
        """Manually trigger a task to run immediately."""
        if task_id not in self._tasks:
            return None

        task = self._tasks[task_id]

        if task.status == TaskStatus.RUNNING:
            logger.warning(f"Task {task.name} is already running")
            return None

        self._queue_task(task)

        # Wait for completion
        while task.status in [TaskStatus.QUEUED, TaskStatus.RUNNING]:
            await asyncio.sleep(0.1)

        return task.results[-1] if task.results else None

    def cancel(self, task_id: str) -> bool:
        """Cancel a pending or queued task."""
        if task_id not in self._tasks:
            return False

        task = self._tasks[task_id]

        if task.status in [TaskStatus.PENDING, TaskStatus.QUEUED, TaskStatus.WAITING_DEPS]:
            task.status = TaskStatus.CANCELLED
            self.queue.remove(task_id)
            self._stats['cancelled_tasks'] += 1
            logger.info(f"Cancelled task: {task.name}")
            return True

        return False

    def cancel_all(self) -> int:
        """Cancel all pending tasks."""
        count = 0
        for task_id in list(self._tasks.keys()):
            if self.cancel(task_id):
                count += 1
        return count

    # ========================================================================
    # QUERY METHODS
    # ========================================================================

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self._tasks.get(task_id)

    def get_tasks_by_tag(self, tag: str) -> List[Task]:
        """Get tasks with a specific tag."""
        return [t for t in self._tasks.values() if tag in t.tags]

    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """Get tasks with a specific status."""
        return [t for t in self._tasks.values() if t.status == status]

    def get_running_tasks(self) -> List[Task]:
        """Get currently running tasks."""
        return self.get_tasks_by_status(TaskStatus.RUNNING)

    def get_pending_tasks(self) -> List[Task]:
        """Get pending tasks."""
        return self.get_tasks_by_status(TaskStatus.PENDING)

    def get_failed_tasks(self) -> List[Task]:
        """Get failed tasks."""
        return self.get_tasks_by_status(TaskStatus.FAILED)

    def get_all_tasks(self) -> List[Task]:
        """Get all registered tasks."""
        return list(self._tasks.values())

    def get_statistics(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        return {
            **self._stats,
            'registered_tasks': len(self._tasks),
            'queued_tasks': len(self.queue),
            'running_tasks': self._running_count,
            'dead_letter_count': len(self.executor.get_dead_letter_queue())
        }

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return {
            'running': self._running,
            'tasks': {
                task.id: {
                    'name': task.name,
                    'status': task.status.value,
                    'priority': task.priority.value,
                    'next_run': task.next_run.isoformat() if task.next_run else None,
                    'last_run': task.last_run.isoformat() if task.last_run else None,
                    'run_count': task.run_count
                }
                for task in self._tasks.values()
            },
            'statistics': self.get_statistics()
        }


# ============================================================================
# CONVENIENCE INSTANCE
# ============================================================================

task_scheduler = TaskScheduler()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def every_minute() -> Schedule:
    """Create a schedule that runs every minute."""
    return Schedule(type=ScheduleType.CRON, cron_expression="* * * * *")


def every_hour() -> Schedule:
    """Create a schedule that runs every hour."""
    return Schedule(type=ScheduleType.CRON, cron_expression="0 * * * *")


def every_day(hour: int = 0, minute: int = 0) -> Schedule:
    """Create a schedule that runs daily at a specific time."""
    return Schedule(type=ScheduleType.CRON, cron_expression=f"{minute} {hour} * * *")


def every_week(weekday: int = 0, hour: int = 0, minute: int = 0) -> Schedule:
    """Create a schedule that runs weekly on a specific day and time."""
    return Schedule(type=ScheduleType.CRON, cron_expression=f"{minute} {hour} * * {weekday}")


def once_at(dt: datetime) -> Schedule:
    """Create a schedule that runs once at a specific time."""
    return Schedule(type=ScheduleType.ONCE, run_at=dt)


def interval(seconds: int) -> Schedule:
    """Create an interval schedule."""
    return Schedule(type=ScheduleType.INTERVAL, interval_seconds=seconds)


def depends_on(*task_ids: str) -> Schedule:
    """Create a dependency-based schedule."""
    return Schedule(type=ScheduleType.DEPENDENCY, depends_on=list(task_ids))
