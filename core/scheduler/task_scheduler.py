#!/usr/bin/env python3
"""
BAEL - Task Scheduler
Advanced task scheduling and execution system.

This module provides comprehensive task scheduling
with cron expressions, intervals, and one-time executions.

Features:
- Cron expression support
- Interval scheduling
- One-time execution
- Task dependencies
- Concurrent execution limits
- Task retries
- Execution history
- Task groups
- Timezone support
- Graceful shutdown
"""

import asyncio
import calendar
import heapq
import logging
import re
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum, auto
from typing import (Any, Awaitable, Callable, Dict, List, Optional, Set, Tuple,
                    Union)

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class ScheduleType(Enum):
    """Schedule type."""
    ONCE = "once"
    INTERVAL = "interval"
    CRON = "cron"
    DEPENDENT = "dependent"


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


class MisfirePolicy(Enum):
    """What to do when a scheduled run is missed."""
    SKIP = "skip"  # Skip missed runs
    RUN_ONCE = "run_once"  # Run once immediately
    RUN_ALL = "run_all"  # Run all missed executions


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class TaskResult:
    """Task execution result."""
    task_id: str
    status: TaskStatus
    started_at: float
    finished_at: float
    result: Any = None
    error: Optional[str] = None
    retry_count: int = 0


@dataclass
class TaskConfig:
    """Task configuration."""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    schedule_type: ScheduleType = ScheduleType.ONCE
    priority: TaskPriority = TaskPriority.NORMAL
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: Optional[float] = None
    max_instances: int = 1  # Max concurrent instances
    misfire_policy: MisfirePolicy = MisfirePolicy.SKIP
    depends_on: List[str] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScheduledRun:
    """A scheduled task run."""
    run_id: str
    task_id: str
    scheduled_time: float
    priority: int = 5

    def __lt__(self, other: 'ScheduledRun') -> bool:
        # Higher priority first, then earlier time
        if self.priority != other.priority:
            return self.priority > other.priority
        return self.scheduled_time < other.scheduled_time


@dataclass
class ExecutionHistory:
    """Task execution history entry."""
    run_id: str
    task_id: str
    task_name: str
    status: TaskStatus
    scheduled_time: float
    started_at: float
    finished_at: float
    duration: float
    result: Any = None
    error: Optional[str] = None


# =============================================================================
# CRON EXPRESSION PARSER
# =============================================================================

class CronField:
    """Represents a cron field (minute, hour, etc.)."""

    def __init__(
        self,
        min_val: int,
        max_val: int,
        aliases: Dict[str, int] = None
    ):
        self.min_val = min_val
        self.max_val = max_val
        self.aliases = aliases or {}
        self.values: Set[int] = set()

    def parse(self, expr: str) -> 'CronField':
        """Parse cron field expression."""
        # Apply aliases
        for alias, value in self.aliases.items():
            expr = expr.upper().replace(alias.upper(), str(value))

        self.values = set()

        for part in expr.split(','):
            if '/' in part:
                self._parse_step(part)
            elif '-' in part:
                self._parse_range(part)
            elif part == '*':
                self.values.update(range(self.min_val, self.max_val + 1))
            else:
                value = int(part)
                if self.min_val <= value <= self.max_val:
                    self.values.add(value)

        return self

    def _parse_range(self, expr: str) -> None:
        """Parse range expression (e.g., '1-5')."""
        start, end = expr.split('-')
        start, end = int(start), int(end)
        self.values.update(range(
            max(start, self.min_val),
            min(end, self.max_val) + 1
        ))

    def _parse_step(self, expr: str) -> None:
        """Parse step expression (e.g., '*/5' or '1-10/2')."""
        range_part, step = expr.split('/')
        step = int(step)

        if range_part == '*':
            start, end = self.min_val, self.max_val
        elif '-' in range_part:
            start, end = map(int, range_part.split('-'))
        else:
            start = int(range_part)
            end = self.max_val

        self.values.update(range(start, end + 1, step))

    def matches(self, value: int) -> bool:
        """Check if value matches this field."""
        return value in self.values

    def next_value(self, current: int) -> Optional[int]:
        """Get next matching value >= current."""
        for v in sorted(self.values):
            if v >= current:
                return v
        return None

    def first_value(self) -> int:
        """Get first matching value."""
        return min(self.values)


class CronExpression:
    """
    Cron expression parser and evaluator.

    Format: minute hour day_of_month month day_of_week

    Examples:
    - "*/5 * * * *" - Every 5 minutes
    - "0 * * * *" - Every hour
    - "0 0 * * *" - Every day at midnight
    - "0 0 * * 0" - Every Sunday at midnight
    - "0 9-17 * * 1-5" - 9am-5pm on weekdays
    """

    # Day of week aliases
    DOW_ALIASES = {
        'SUN': 0, 'MON': 1, 'TUE': 2, 'WED': 3,
        'THU': 4, 'FRI': 5, 'SAT': 6
    }

    # Month aliases
    MONTH_ALIASES = {
        'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4,
        'MAY': 5, 'JUN': 6, 'JUL': 7, 'AUG': 8,
        'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
    }

    def __init__(self, expression: str):
        self.expression = expression
        self._parse(expression)

    def _parse(self, expression: str) -> None:
        """Parse cron expression."""
        parts = expression.strip().split()

        if len(parts) != 5:
            raise ValueError(
                f"Invalid cron expression: expected 5 fields, got {len(parts)}"
            )

        self.minute = CronField(0, 59).parse(parts[0])
        self.hour = CronField(0, 23).parse(parts[1])
        self.day = CronField(1, 31).parse(parts[2])
        self.month = CronField(1, 12, self.MONTH_ALIASES).parse(parts[3])
        self.dow = CronField(0, 6, self.DOW_ALIASES).parse(parts[4])

    def matches(self, dt: datetime) -> bool:
        """Check if datetime matches the cron expression."""
        return (
            self.minute.matches(dt.minute) and
            self.hour.matches(dt.hour) and
            self.day.matches(dt.day) and
            self.month.matches(dt.month) and
            self.dow.matches(dt.weekday())
        )

    def next_run(self, after: datetime = None) -> datetime:
        """Calculate next run time after given datetime."""
        if after is None:
            after = datetime.now()

        # Start from next minute
        dt = after.replace(second=0, microsecond=0) + timedelta(minutes=1)

        # Search for next matching time (max 4 years)
        max_iterations = 365 * 24 * 60 * 4

        for _ in range(max_iterations):
            if self.matches(dt):
                return dt
            dt += timedelta(minutes=1)

        raise ValueError("Could not find next run time within 4 years")


# =============================================================================
# SCHEDULE TYPES
# =============================================================================

class Schedule(ABC):
    """Abstract schedule base."""

    @abstractmethod
    def next_run(self, after: float = None) -> Optional[float]:
        """Calculate next run time."""
        pass

    @abstractmethod
    def get_type(self) -> ScheduleType:
        """Get schedule type."""
        pass


class OnceSchedule(Schedule):
    """One-time execution schedule."""

    def __init__(self, run_at: float):
        self.run_at = run_at
        self.executed = False

    def next_run(self, after: float = None) -> Optional[float]:
        if self.executed:
            return None

        after = after or time.time()

        if self.run_at >= after:
            return self.run_at
        return None

    def get_type(self) -> ScheduleType:
        return ScheduleType.ONCE


class IntervalSchedule(Schedule):
    """Interval-based schedule."""

    def __init__(
        self,
        seconds: float = 0,
        minutes: float = 0,
        hours: float = 0,
        days: float = 0,
        start_at: float = None
    ):
        self.interval = (
            seconds +
            minutes * 60 +
            hours * 3600 +
            days * 86400
        )
        self.start_at = start_at or time.time()
        self.last_run: Optional[float] = None

    def next_run(self, after: float = None) -> Optional[float]:
        after = after or time.time()

        if self.last_run is None:
            # First run
            if self.start_at >= after:
                return self.start_at
            else:
                # Calculate next interval from start
                elapsed = after - self.start_at
                intervals = int(elapsed / self.interval) + 1
                return self.start_at + (intervals * self.interval)

        return self.last_run + self.interval

    def get_type(self) -> ScheduleType:
        return ScheduleType.INTERVAL


class CronSchedule(Schedule):
    """Cron-based schedule."""

    def __init__(self, expression: str):
        self.cron = CronExpression(expression)

    def next_run(self, after: float = None) -> Optional[float]:
        after_dt = datetime.fromtimestamp(after or time.time())
        next_dt = self.cron.next_run(after_dt)
        return next_dt.timestamp()

    def get_type(self) -> ScheduleType:
        return ScheduleType.CRON


class DependentSchedule(Schedule):
    """Schedule that depends on other tasks."""

    def __init__(self, depends_on: List[str]):
        self.depends_on = depends_on
        self._trigger_time: Optional[float] = None

    def trigger(self) -> None:
        """Trigger the schedule."""
        self._trigger_time = time.time()

    def next_run(self, after: float = None) -> Optional[float]:
        if self._trigger_time is not None:
            t = self._trigger_time
            self._trigger_time = None
            return t
        return None

    def get_type(self) -> ScheduleType:
        return ScheduleType.DEPENDENT


# =============================================================================
# TASK
# =============================================================================

class ScheduledTask:
    """A scheduled task."""

    def __init__(
        self,
        func: Callable[..., Awaitable[Any]],
        schedule: Schedule,
        config: TaskConfig = None,
        args: Tuple = None,
        kwargs: Dict = None
    ):
        self.func = func
        self.schedule = schedule
        self.config = config or TaskConfig()
        self.args = args or ()
        self.kwargs = kwargs or {}

        # Execution state
        self.running_instances = 0
        self.last_run: Optional[float] = None
        self.next_run: Optional[float] = None
        self.history: List[ExecutionHistory] = []
        self.enabled = True

        # Statistics
        self.run_count = 0
        self.success_count = 0
        self.failure_count = 0

    async def execute(self) -> TaskResult:
        """Execute the task."""
        started_at = time.time()
        retry_count = 0
        result = None
        error = None
        status = TaskStatus.PENDING

        while retry_count <= self.config.max_retries:
            try:
                self.running_instances += 1

                # Execute with timeout
                if self.config.timeout:
                    result = await asyncio.wait_for(
                        self.func(*self.args, **self.kwargs),
                        timeout=self.config.timeout
                    )
                else:
                    result = await self.func(*self.args, **self.kwargs)

                status = TaskStatus.COMPLETED
                self.success_count += 1
                break

            except asyncio.TimeoutError:
                error = "Task timeout"
                status = TaskStatus.FAILED
                retry_count += 1

            except Exception as e:
                error = str(e)
                status = TaskStatus.FAILED
                retry_count += 1

                if retry_count <= self.config.max_retries:
                    await asyncio.sleep(self.config.retry_delay * retry_count)

            finally:
                self.running_instances -= 1

        if status == TaskStatus.FAILED:
            self.failure_count += 1

        finished_at = time.time()
        self.run_count += 1
        self.last_run = finished_at

        return TaskResult(
            task_id=self.config.task_id,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            result=result,
            error=error,
            retry_count=retry_count
        )

    def update_next_run(self) -> None:
        """Update next run time."""
        self.next_run = self.schedule.next_run(self.last_run)


# =============================================================================
# TASK SCHEDULER
# =============================================================================

class TaskScheduler:
    """
    Advanced task scheduler.
    """

    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self.tasks: Dict[str, ScheduledTask] = {}
        self.task_groups: Dict[str, Set[str]] = defaultdict(set)

        # Run queue
        self._run_queue: List[ScheduledRun] = []

        # Control
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        self._executor_task: Optional[asyncio.Task] = None
        self._active_workers = 0
        self._lock = asyncio.Lock()

        # History
        self.execution_history: List[ExecutionHistory] = []
        self.max_history = 1000

        # Statistics
        self.stats = {
            "tasks_executed": 0,
            "tasks_succeeded": 0,
            "tasks_failed": 0,
            "total_execution_time": 0.0
        }

    def add_task(
        self,
        func: Callable[..., Awaitable[Any]],
        schedule: Schedule,
        task_id: str = None,
        name: str = None,
        group: str = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 3,
        timeout: float = None,
        args: Tuple = None,
        kwargs: Dict = None,
        **config_kwargs
    ) -> str:
        """Add a scheduled task."""
        config = TaskConfig(
            task_id=task_id or str(uuid.uuid4()),
            name=name or func.__name__,
            schedule_type=schedule.get_type(),
            priority=priority,
            max_retries=max_retries,
            timeout=timeout,
            **config_kwargs
        )

        task = ScheduledTask(
            func=func,
            schedule=schedule,
            config=config,
            args=args,
            kwargs=kwargs
        )

        task.update_next_run()
        self.tasks[config.task_id] = task

        if group:
            self.task_groups[group].add(config.task_id)

        logger.info(f"Task added: {config.name} ({config.task_id})")

        return config.task_id

    def add_cron_task(
        self,
        func: Callable[..., Awaitable[Any]],
        cron_expr: str,
        **kwargs
    ) -> str:
        """Add a cron-scheduled task."""
        schedule = CronSchedule(cron_expr)
        return self.add_task(func, schedule, **kwargs)

    def add_interval_task(
        self,
        func: Callable[..., Awaitable[Any]],
        seconds: float = 0,
        minutes: float = 0,
        hours: float = 0,
        **kwargs
    ) -> str:
        """Add an interval-scheduled task."""
        schedule = IntervalSchedule(
            seconds=seconds,
            minutes=minutes,
            hours=hours
        )
        return self.add_task(func, schedule, **kwargs)

    def add_once_task(
        self,
        func: Callable[..., Awaitable[Any]],
        run_at: float = None,
        delay: float = 0,
        **kwargs
    ) -> str:
        """Add a one-time task."""
        if run_at is None:
            run_at = time.time() + delay

        schedule = OnceSchedule(run_at)
        return self.add_task(func, schedule, **kwargs)

    def remove_task(self, task_id: str) -> bool:
        """Remove a task."""
        if task_id in self.tasks:
            del self.tasks[task_id]

            # Remove from groups
            for group_tasks in self.task_groups.values():
                group_tasks.discard(task_id)

            return True
        return False

    def enable_task(self, task_id: str) -> None:
        """Enable a task."""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = True

    def disable_task(self, task_id: str) -> None:
        """Disable a task."""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = False

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get task by ID."""
        return self.tasks.get(task_id)

    def get_tasks_by_group(self, group: str) -> List[ScheduledTask]:
        """Get all tasks in a group."""
        task_ids = self.task_groups.get(group, set())
        return [self.tasks[tid] for tid in task_ids if tid in self.tasks]

    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            return

        self._running = True

        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        self._executor_task = asyncio.create_task(self._executor_loop())

        logger.info("Task scheduler started")

    async def stop(self, wait: bool = True) -> None:
        """Stop the scheduler."""
        self._running = False

        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

        if self._executor_task:
            self._executor_task.cancel()
            try:
                await self._executor_task
            except asyncio.CancelledError:
                pass

        if wait:
            # Wait for running tasks
            while self._active_workers > 0:
                await asyncio.sleep(0.1)

        logger.info("Task scheduler stopped")

    async def _scheduler_loop(self) -> None:
        """Main scheduling loop."""
        while self._running:
            try:
                now = time.time()

                # Check each task for scheduling
                for task in self.tasks.values():
                    if not task.enabled:
                        continue

                    if task.next_run is None:
                        task.update_next_run()

                    if task.next_run is not None and task.next_run <= now:
                        # Check max instances
                        if task.running_instances >= task.config.max_instances:
                            continue

                        # Schedule the run
                        run = ScheduledRun(
                            run_id=str(uuid.uuid4()),
                            task_id=task.config.task_id,
                            scheduled_time=task.next_run,
                            priority=task.config.priority.value
                        )

                        async with self._lock:
                            heapq.heappush(self._run_queue, run)

                        # Update next run
                        task.update_next_run()

                await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(1)

    async def _executor_loop(self) -> None:
        """Task execution loop."""
        while self._running:
            try:
                if self._active_workers >= self.max_workers:
                    await asyncio.sleep(0.1)
                    continue

                run: Optional[ScheduledRun] = None

                async with self._lock:
                    if self._run_queue:
                        run = heapq.heappop(self._run_queue)

                if run is None:
                    await asyncio.sleep(0.1)
                    continue

                # Execute task
                asyncio.create_task(self._execute_run(run))

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Executor loop error: {e}")
                await asyncio.sleep(1)

    async def _execute_run(self, run: ScheduledRun) -> None:
        """Execute a scheduled run."""
        task = self.tasks.get(run.task_id)
        if not task or not task.enabled:
            return

        self._active_workers += 1
        started_at = time.time()

        try:
            result = await task.execute()

            # Record history
            history = ExecutionHistory(
                run_id=run.run_id,
                task_id=task.config.task_id,
                task_name=task.config.name,
                status=result.status,
                scheduled_time=run.scheduled_time,
                started_at=result.started_at,
                finished_at=result.finished_at,
                duration=result.finished_at - result.started_at,
                result=result.result,
                error=result.error
            )

            self.execution_history.append(history)

            # Trim history
            if len(self.execution_history) > self.max_history:
                self.execution_history = self.execution_history[-self.max_history:]

            # Update stats
            self.stats["tasks_executed"] += 1
            self.stats["total_execution_time"] += history.duration

            if result.status == TaskStatus.COMPLETED:
                self.stats["tasks_succeeded"] += 1
                # Trigger dependent tasks
                await self._trigger_dependents(task.config.task_id)
            else:
                self.stats["tasks_failed"] += 1

        except Exception as e:
            logger.error(f"Task execution error: {e}")
            self.stats["tasks_failed"] += 1

        finally:
            self._active_workers -= 1

    async def _trigger_dependents(self, completed_task_id: str) -> None:
        """Trigger tasks that depend on completed task."""
        for task in self.tasks.values():
            if isinstance(task.schedule, DependentSchedule):
                if completed_task_id in task.schedule.depends_on:
                    task.schedule.trigger()

    async def run_now(self, task_id: str) -> Optional[TaskResult]:
        """Run a task immediately."""
        task = self.tasks.get(task_id)
        if not task:
            return None

        return await task.execute()

    def get_pending_runs(self) -> List[ScheduledRun]:
        """Get pending runs."""
        return list(self._run_queue)

    def get_history(
        self,
        task_id: str = None,
        limit: int = 100
    ) -> List[ExecutionHistory]:
        """Get execution history."""
        history = self.execution_history

        if task_id:
            history = [h for h in history if h.task_id == task_id]

        return history[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        return {
            **self.stats,
            "total_tasks": len(self.tasks),
            "enabled_tasks": sum(1 for t in self.tasks.values() if t.enabled),
            "active_workers": self._active_workers,
            "pending_runs": len(self._run_queue)
        }


# =============================================================================
# SCHEDULER MANAGER
# =============================================================================

class TaskSchedulerManager:
    """
    Master task scheduler manager for BAEL.
    """

    def __init__(self, max_workers: int = 10):
        self.scheduler = TaskScheduler(max_workers)

    async def start(self) -> None:
        """Start scheduler."""
        await self.scheduler.start()

    async def stop(self, wait: bool = True) -> None:
        """Stop scheduler."""
        await self.scheduler.stop(wait)

    def cron(
        self,
        expression: str,
        name: str = None,
        **kwargs
    ) -> Callable:
        """Decorator for cron-scheduled tasks."""
        def decorator(func: Callable) -> Callable:
            self.scheduler.add_cron_task(
                func,
                expression,
                name=name or func.__name__,
                **kwargs
            )
            return func
        return decorator

    def interval(
        self,
        seconds: float = 0,
        minutes: float = 0,
        hours: float = 0,
        name: str = None,
        **kwargs
    ) -> Callable:
        """Decorator for interval-scheduled tasks."""
        def decorator(func: Callable) -> Callable:
            self.scheduler.add_interval_task(
                func,
                seconds=seconds,
                minutes=minutes,
                hours=hours,
                name=name or func.__name__,
                **kwargs
            )
            return func
        return decorator

    def add_cron(
        self,
        func: Callable,
        expression: str,
        **kwargs
    ) -> str:
        """Add cron task."""
        return self.scheduler.add_cron_task(func, expression, **kwargs)

    def add_interval(
        self,
        func: Callable,
        seconds: float = 0,
        minutes: float = 0,
        hours: float = 0,
        **kwargs
    ) -> str:
        """Add interval task."""
        return self.scheduler.add_interval_task(
            func,
            seconds=seconds,
            minutes=minutes,
            hours=hours,
            **kwargs
        )

    def add_once(
        self,
        func: Callable,
        run_at: float = None,
        delay: float = 0,
        **kwargs
    ) -> str:
        """Add one-time task."""
        return self.scheduler.add_once_task(func, run_at, delay, **kwargs)

    async def run(self, task_id: str) -> Optional[TaskResult]:
        """Run task immediately."""
        return await self.scheduler.run_now(task_id)

    def remove(self, task_id: str) -> bool:
        """Remove task."""
        return self.scheduler.remove_task(task_id)

    def enable(self, task_id: str) -> None:
        """Enable task."""
        self.scheduler.enable_task(task_id)

    def disable(self, task_id: str) -> None:
        """Disable task."""
        self.scheduler.disable_task(task_id)

    def get_history(
        self,
        task_id: str = None,
        limit: int = 100
    ) -> List[ExecutionHistory]:
        """Get history."""
        return self.scheduler.get_history(task_id, limit)

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics."""
        return self.scheduler.get_statistics()


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Task Scheduler."""
    print("=" * 70)
    print("BAEL - TASK SCHEDULER DEMO")
    print("Advanced Task Scheduling System")
    print("=" * 70)
    print()

    manager = TaskSchedulerManager(max_workers=5)

    # 1. Cron Expression Parsing
    print("1. CRON EXPRESSION PARSING:")
    print("-" * 40)

    cron = CronExpression("*/5 * * * *")
    print(f"   Expression: */5 * * * *")
    print(f"   Minutes: {sorted(cron.minute.values)}")

    cron2 = CronExpression("0 9-17 * * 1-5")
    print(f"   Expression: 0 9-17 * * 1-5")
    print(f"   Hours: {sorted(cron2.hour.values)}")
    print(f"   Days: {sorted(cron2.dow.values)}")

    # Next run calculation
    next_run = cron.next_run()
    print(f"   Next run: {next_run.strftime('%Y-%m-%d %H:%M')}")
    print()

    # 2. Add Interval Tasks
    print("2. INTERVAL TASKS:")
    print("-" * 40)

    execution_count = {"cleanup": 0, "sync": 0, "heartbeat": 0}

    async def cleanup_task():
        execution_count["cleanup"] += 1
        print(f"   🧹 Cleanup executed (count: {execution_count['cleanup']})")
        return "cleaned"

    async def sync_task():
        execution_count["sync"] += 1
        print(f"   🔄 Sync executed (count: {execution_count['sync']})")
        return "synced"

    task_id1 = manager.add_interval(
        cleanup_task,
        seconds=1,
        name="CleanupTask"
    )
    print(f"   Added: CleanupTask (every 1 second)")

    task_id2 = manager.add_interval(
        sync_task,
        seconds=2,
        name="SyncTask"
    )
    print(f"   Added: SyncTask (every 2 seconds)")
    print()

    # 3. Add One-Time Task
    print("3. ONE-TIME TASKS:")
    print("-" * 40)

    async def scheduled_report():
        print("   📊 Scheduled report generated!")
        return {"report": "data"}

    task_id3 = manager.add_once(
        scheduled_report,
        delay=1.5,
        name="ScheduledReport"
    )
    print(f"   Added: ScheduledReport (runs in 1.5 seconds)")
    print()

    # 4. Start Scheduler and Run
    print("4. RUNNING SCHEDULER:")
    print("-" * 40)

    await manager.start()
    print("   Scheduler started, running for 4 seconds...")
    print()

    await asyncio.sleep(4)

    await manager.stop()
    print()
    print("   Scheduler stopped")
    print()

    # 5. Execution History
    print("5. EXECUTION HISTORY:")
    print("-" * 40)

    history = manager.get_history(limit=10)
    print(f"   Total executions: {len(history)}")

    for entry in history[-5:]:
        status_icon = "✅" if entry.status == TaskStatus.COMPLETED else "❌"
        print(f"     {status_icon} {entry.task_name}: {entry.duration:.3f}s")
    print()

    # 6. Task with Retries
    print("6. TASK WITH RETRIES:")
    print("-" * 40)

    attempt = {"count": 0}

    async def flaky_task():
        attempt["count"] += 1
        if attempt["count"] < 3:
            print(f"   ⚠️ Attempt {attempt['count']} failed")
            raise Exception("Simulated failure")
        print(f"   ✅ Attempt {attempt['count']} succeeded")
        return "success"

    manager2 = TaskSchedulerManager()
    task_id = manager2.add_once(
        flaky_task,
        delay=0,
        name="FlakyTask",
        max_retries=3
    )

    result = await manager2.run(task_id)
    print(f"   Final status: {result.status.value}")
    print(f"   Retries: {result.retry_count}")
    print()

    # 7. Task with Timeout
    print("7. TASK WITH TIMEOUT:")
    print("-" * 40)

    async def slow_task():
        await asyncio.sleep(5)
        return "done"

    task_id = manager2.add_once(
        slow_task,
        delay=0,
        name="SlowTask",
        timeout=0.5,
        max_retries=0
    )

    result = await manager2.run(task_id)
    print(f"   Status: {result.status.value}")
    print(f"   Error: {result.error}")
    print()

    # 8. Task Groups
    print("8. TASK GROUPS:")
    print("-" * 40)

    async def group_task_a():
        return "A"

    async def group_task_b():
        return "B"

    manager3 = TaskSchedulerManager()

    manager3.scheduler.add_interval_task(
        group_task_a,
        seconds=10,
        name="GroupTaskA",
        group="data_tasks"
    )

    manager3.scheduler.add_interval_task(
        group_task_b,
        seconds=15,
        name="GroupTaskB",
        group="data_tasks"
    )

    data_tasks = manager3.scheduler.get_tasks_by_group("data_tasks")
    print(f"   Tasks in 'data_tasks' group: {len(data_tasks)}")
    for task in data_tasks:
        print(f"     - {task.config.name}")
    print()

    # 9. Cron Scheduling Demo
    print("9. CRON SCHEDULING:")
    print("-" * 40)

    cron_examples = [
        ("*/15 * * * *", "Every 15 minutes"),
        ("0 * * * *", "Every hour"),
        ("0 0 * * *", "Every day at midnight"),
        ("0 9 * * 1-5", "9 AM on weekdays"),
        ("0 0 1 * *", "First of every month"),
    ]

    for expr, desc in cron_examples:
        cron = CronExpression(expr)
        next_run = cron.next_run()
        print(f"   {expr}")
        print(f"     {desc}")
        print(f"     Next: {next_run.strftime('%Y-%m-%d %H:%M')}")
    print()

    # 10. Statistics
    print("10. STATISTICS:")
    print("-" * 40)

    stats = manager.get_statistics()
    print(f"    Tasks executed: {stats['tasks_executed']}")
    print(f"    Tasks succeeded: {stats['tasks_succeeded']}")
    print(f"    Tasks failed: {stats['tasks_failed']}")
    print(f"    Total execution time: {stats['total_execution_time']:.3f}s")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Task Scheduler Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
