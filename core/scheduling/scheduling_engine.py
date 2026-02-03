#!/usr/bin/env python3
"""
BAEL - Scheduling Engine
Task scheduling and time management for agents.

Features:
- Task scheduling
- Cron expressions
- Priority queues
- Deadline management
- Resource allocation
"""

import asyncio
import hashlib
import heapq
import json
import math
import random
import re
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ScheduleType(Enum):
    """Types of schedules."""
    ONCE = "once"
    RECURRING = "recurring"
    CRON = "cron"
    INTERVAL = "interval"
    DELAYED = "delayed"


class TaskStatus(Enum):
    """Task statuses."""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priorities."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5


class ResourceType(Enum):
    """Resource types."""
    CPU = "cpu"
    MEMORY = "memory"
    GPU = "gpu"
    NETWORK = "network"
    STORAGE = "storage"


class ConflictResolution(Enum):
    """Conflict resolution strategies."""
    SKIP = "skip"
    QUEUE = "queue"
    REPLACE = "replace"
    PARALLEL = "parallel"


class TimeUnit(Enum):
    """Time units."""
    SECONDS = "seconds"
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"
    WEEKS = "weeks"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Schedule:
    """A schedule definition."""
    schedule_id: str = ""
    schedule_type: ScheduleType = ScheduleType.ONCE
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    interval: Optional[int] = None
    interval_unit: TimeUnit = TimeUnit.SECONDS
    cron_expression: Optional[str] = None
    max_runs: Optional[int] = None
    run_count: int = 0

    def __post_init__(self):
        if not self.schedule_id:
            self.schedule_id = str(uuid.uuid4())[:8]


@dataclass
class ScheduledTask:
    """A scheduled task."""
    task_id: str = ""
    name: str = ""
    handler: Optional[Callable] = None
    schedule: Optional[Schedule] = None
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    run_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.task_id:
            self.task_id = str(uuid.uuid4())[:8]

    def __lt__(self, other):
        if self.next_run and other.next_run:
            return self.next_run < other.next_run
        return self.priority.value > other.priority.value


@dataclass
class TaskResult:
    """Result of a task execution."""
    result_id: str = ""
    task_id: str = ""
    success: bool = True
    result: Any = None
    error: Optional[str] = None
    duration: float = 0.0
    executed_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.result_id:
            self.result_id = str(uuid.uuid4())[:8]


@dataclass
class Resource:
    """A resource for task execution."""
    resource_id: str = ""
    resource_type: ResourceType = ResourceType.CPU
    capacity: float = 100.0
    used: float = 0.0
    reserved: float = 0.0

    def __post_init__(self):
        if not self.resource_id:
            self.resource_id = str(uuid.uuid4())[:8]

    @property
    def available(self) -> float:
        return self.capacity - self.used - self.reserved


@dataclass
class Deadline:
    """A deadline for a task."""
    deadline_id: str = ""
    task_id: str = ""
    due_time: datetime = field(default_factory=datetime.now)
    hard: bool = True
    penalty: float = 0.0

    def __post_init__(self):
        if not self.deadline_id:
            self.deadline_id = str(uuid.uuid4())[:8]


@dataclass
class SchedulerConfig:
    """Scheduler configuration."""
    max_concurrent: int = 10
    default_priority: TaskPriority = TaskPriority.NORMAL
    conflict_resolution: ConflictResolution = ConflictResolution.QUEUE
    tick_interval: float = 1.0


# =============================================================================
# CRON PARSER
# =============================================================================

class CronParser:
    """Parse cron expressions."""

    def __init__(self):
        self._fields = ["minute", "hour", "day", "month", "weekday"]

    def parse(self, expression: str) -> Dict[str, List[int]]:
        """Parse cron expression."""
        parts = expression.strip().split()

        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {expression}")

        result = {}

        ranges = [
            (0, 59),
            (0, 23),
            (1, 31),
            (1, 12),
            (0, 6)
        ]

        for i, (part, field, (min_val, max_val)) in enumerate(
            zip(parts, self._fields, ranges)
        ):
            result[field] = self._parse_field(part, min_val, max_val)

        return result

    def _parse_field(
        self,
        field: str,
        min_val: int,
        max_val: int
    ) -> List[int]:
        """Parse a single cron field."""
        if field == "*":
            return list(range(min_val, max_val + 1))

        if "/" in field:
            base, step = field.split("/")
            step = int(step)

            if base == "*":
                return list(range(min_val, max_val + 1, step))
            else:
                start = int(base)
                return list(range(start, max_val + 1, step))

        if "-" in field:
            start, end = field.split("-")
            return list(range(int(start), int(end) + 1))

        if "," in field:
            return [int(x) for x in field.split(",")]

        return [int(field)]

    def next_run(
        self,
        expression: str,
        after: Optional[datetime] = None
    ) -> datetime:
        """Calculate next run time from cron expression."""
        after = after or datetime.now()
        parsed = self.parse(expression)

        current = after.replace(second=0, microsecond=0) + timedelta(minutes=1)

        for _ in range(365 * 24 * 60):
            if (current.minute in parsed["minute"] and
                current.hour in parsed["hour"] and
                current.day in parsed["day"] and
                current.month in parsed["month"] and
                current.weekday() in parsed["weekday"]):
                return current

            current += timedelta(minutes=1)

        raise ValueError("Could not find next run time")


# =============================================================================
# TASK QUEUE
# =============================================================================

class TaskQueue:
    """Priority queue for tasks."""

    def __init__(self):
        self._queue: List[ScheduledTask] = []
        self._task_map: Dict[str, ScheduledTask] = {}

    def push(self, task: ScheduledTask) -> None:
        """Push task to queue."""
        heapq.heappush(self._queue, task)
        self._task_map[task.task_id] = task

    def pop(self) -> Optional[ScheduledTask]:
        """Pop highest priority task."""
        while self._queue:
            task = heapq.heappop(self._queue)

            if task.task_id in self._task_map:
                del self._task_map[task.task_id]
                return task

        return None

    def peek(self) -> Optional[ScheduledTask]:
        """Peek at next task."""
        while self._queue:
            if self._queue[0].task_id in self._task_map:
                return self._queue[0]
            heapq.heappop(self._queue)

        return None

    def remove(self, task_id: str) -> bool:
        """Remove task from queue."""
        if task_id in self._task_map:
            del self._task_map[task_id]
            return True
        return False

    def get(self, task_id: str) -> Optional[ScheduledTask]:
        """Get task by ID."""
        return self._task_map.get(task_id)

    def update_priority(
        self,
        task_id: str,
        priority: TaskPriority
    ) -> bool:
        """Update task priority."""
        task = self._task_map.get(task_id)

        if task:
            task.priority = priority
            heapq.heapify(self._queue)
            return True

        return False

    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return len(self._task_map) == 0

    def count(self) -> int:
        """Count tasks in queue."""
        return len(self._task_map)

    def clear(self) -> None:
        """Clear the queue."""
        self._queue.clear()
        self._task_map.clear()

    def all(self) -> List[ScheduledTask]:
        """Get all tasks."""
        return list(self._task_map.values())


# =============================================================================
# RESOURCE MANAGER
# =============================================================================

class ResourceManager:
    """Manage resources for task execution."""

    def __init__(self):
        self._resources: Dict[str, Resource] = {}
        self._reservations: Dict[str, Dict[str, float]] = {}

    def add_resource(
        self,
        resource_type: ResourceType,
        capacity: float = 100.0
    ) -> Resource:
        """Add a resource."""
        resource = Resource(
            resource_type=resource_type,
            capacity=capacity
        )

        self._resources[resource.resource_id] = resource

        return resource

    def get_resource(self, resource_id: str) -> Optional[Resource]:
        """Get resource by ID."""
        return self._resources.get(resource_id)

    def get_by_type(self, resource_type: ResourceType) -> List[Resource]:
        """Get resources by type."""
        return [r for r in self._resources.values() if r.resource_type == resource_type]

    def reserve(
        self,
        task_id: str,
        resource_id: str,
        amount: float
    ) -> bool:
        """Reserve resource for task."""
        resource = self._resources.get(resource_id)

        if not resource or resource.available < amount:
            return False

        resource.reserved += amount

        if task_id not in self._reservations:
            self._reservations[task_id] = {}

        self._reservations[task_id][resource_id] = amount

        return True

    def release(self, task_id: str) -> None:
        """Release all resources for task."""
        if task_id in self._reservations:
            for resource_id, amount in self._reservations[task_id].items():
                resource = self._resources.get(resource_id)
                if resource:
                    resource.reserved -= amount

            del self._reservations[task_id]

    def allocate(
        self,
        task_id: str,
        resource_id: str,
        amount: float
    ) -> bool:
        """Allocate resource for task."""
        resource = self._resources.get(resource_id)

        if not resource:
            return False

        reserved = self._reservations.get(task_id, {}).get(resource_id, 0)

        if reserved >= amount:
            resource.reserved -= amount
            resource.used += amount

            if task_id in self._reservations:
                self._reservations[task_id][resource_id] -= amount

            return True

        return False

    def deallocate(
        self,
        resource_id: str,
        amount: float
    ) -> bool:
        """Deallocate resource."""
        resource = self._resources.get(resource_id)

        if resource:
            resource.used = max(0, resource.used - amount)
            return True

        return False

    def get_availability(self) -> Dict[str, float]:
        """Get resource availability."""
        return {
            r.resource_id: r.available
            for r in self._resources.values()
        }

    def count(self) -> int:
        """Count resources."""
        return len(self._resources)


# =============================================================================
# DEADLINE TRACKER
# =============================================================================

class DeadlineTracker:
    """Track task deadlines."""

    def __init__(self):
        self._deadlines: Dict[str, Deadline] = {}
        self._by_task: Dict[str, Deadline] = {}

    def set_deadline(
        self,
        task_id: str,
        due_time: datetime,
        hard: bool = True,
        penalty: float = 0.0
    ) -> Deadline:
        """Set a deadline for a task."""
        deadline = Deadline(
            task_id=task_id,
            due_time=due_time,
            hard=hard,
            penalty=penalty
        )

        self._deadlines[deadline.deadline_id] = deadline
        self._by_task[task_id] = deadline

        return deadline

    def get_deadline(self, task_id: str) -> Optional[Deadline]:
        """Get deadline for task."""
        return self._by_task.get(task_id)

    def is_overdue(self, task_id: str) -> bool:
        """Check if task is overdue."""
        deadline = self._by_task.get(task_id)

        if deadline:
            return datetime.now() > deadline.due_time

        return False

    def time_remaining(self, task_id: str) -> Optional[timedelta]:
        """Get time remaining until deadline."""
        deadline = self._by_task.get(task_id)

        if deadline:
            return deadline.due_time - datetime.now()

        return None

    def get_overdue(self) -> List[Deadline]:
        """Get all overdue deadlines."""
        now = datetime.now()
        return [d for d in self._deadlines.values() if d.due_time < now]

    def get_upcoming(
        self,
        within: timedelta = timedelta(hours=1)
    ) -> List[Deadline]:
        """Get upcoming deadlines."""
        now = datetime.now()
        threshold = now + within

        return [
            d for d in self._deadlines.values()
            if now <= d.due_time <= threshold
        ]

    def remove_deadline(self, task_id: str) -> bool:
        """Remove deadline for task."""
        deadline = self._by_task.get(task_id)

        if deadline:
            del self._deadlines[deadline.deadline_id]
            del self._by_task[task_id]
            return True

        return False

    def count(self) -> int:
        """Count deadlines."""
        return len(self._deadlines)


# =============================================================================
# SCHEDULING ENGINE
# =============================================================================

class SchedulingEngine:
    """
    Scheduling Engine for BAEL.

    Task scheduling and time management.
    """

    def __init__(self, config: Optional[SchedulerConfig] = None):
        self._config = config or SchedulerConfig()

        self._task_queue = TaskQueue()
        self._cron_parser = CronParser()
        self._resource_manager = ResourceManager()
        self._deadline_tracker = DeadlineTracker()

        self._tasks: Dict[str, ScheduledTask] = {}
        self._results: Dict[str, List[TaskResult]] = defaultdict(list)
        self._running: Set[str] = set()
        self._running_flag = False

    # ----- Task Operations -----

    def schedule_once(
        self,
        name: str,
        handler: Callable,
        at: datetime,
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> ScheduledTask:
        """Schedule a one-time task."""
        schedule = Schedule(
            schedule_type=ScheduleType.ONCE,
            start_time=at,
            max_runs=1
        )

        task = ScheduledTask(
            name=name,
            handler=handler,
            schedule=schedule,
            priority=priority,
            next_run=at,
            status=TaskStatus.SCHEDULED
        )

        self._tasks[task.task_id] = task
        self._task_queue.push(task)

        return task

    def schedule_interval(
        self,
        name: str,
        handler: Callable,
        interval: int,
        unit: TimeUnit = TimeUnit.SECONDS,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_runs: Optional[int] = None
    ) -> ScheduledTask:
        """Schedule an interval task."""
        schedule = Schedule(
            schedule_type=ScheduleType.INTERVAL,
            interval=interval,
            interval_unit=unit,
            max_runs=max_runs
        )

        next_run = self._calculate_next_interval(interval, unit)

        task = ScheduledTask(
            name=name,
            handler=handler,
            schedule=schedule,
            priority=priority,
            next_run=next_run,
            status=TaskStatus.SCHEDULED
        )

        self._tasks[task.task_id] = task
        self._task_queue.push(task)

        return task

    def schedule_cron(
        self,
        name: str,
        handler: Callable,
        cron_expression: str,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_runs: Optional[int] = None
    ) -> ScheduledTask:
        """Schedule a cron task."""
        schedule = Schedule(
            schedule_type=ScheduleType.CRON,
            cron_expression=cron_expression,
            max_runs=max_runs
        )

        next_run = self._cron_parser.next_run(cron_expression)

        task = ScheduledTask(
            name=name,
            handler=handler,
            schedule=schedule,
            priority=priority,
            next_run=next_run,
            status=TaskStatus.SCHEDULED
        )

        self._tasks[task.task_id] = task
        self._task_queue.push(task)

        return task

    def schedule_delayed(
        self,
        name: str,
        handler: Callable,
        delay: int,
        unit: TimeUnit = TimeUnit.SECONDS,
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> ScheduledTask:
        """Schedule a delayed task."""
        at = self._calculate_next_interval(delay, unit)

        return self.schedule_once(name, handler, at, priority)

    def _calculate_next_interval(
        self,
        interval: int,
        unit: TimeUnit
    ) -> datetime:
        """Calculate next run time from interval."""
        now = datetime.now()

        if unit == TimeUnit.SECONDS:
            return now + timedelta(seconds=interval)
        elif unit == TimeUnit.MINUTES:
            return now + timedelta(minutes=interval)
        elif unit == TimeUnit.HOURS:
            return now + timedelta(hours=interval)
        elif unit == TimeUnit.DAYS:
            return now + timedelta(days=interval)
        elif unit == TimeUnit.WEEKS:
            return now + timedelta(weeks=interval)

        return now + timedelta(seconds=interval)

    # ----- Task Management -----

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get task by ID."""
        return self._tasks.get(task_id)

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task."""
        task = self._tasks.get(task_id)

        if task:
            task.status = TaskStatus.CANCELLED
            self._task_queue.remove(task_id)
            return True

        return False

    def pause_task(self, task_id: str) -> bool:
        """Pause a task."""
        task = self._tasks.get(task_id)

        if task:
            task.status = TaskStatus.PENDING
            self._task_queue.remove(task_id)
            return True

        return False

    def resume_task(self, task_id: str) -> bool:
        """Resume a paused task."""
        task = self._tasks.get(task_id)

        if task and task.status == TaskStatus.PENDING:
            task.status = TaskStatus.SCHEDULED
            self._task_queue.push(task)
            return True

        return False

    def update_priority(
        self,
        task_id: str,
        priority: TaskPriority
    ) -> bool:
        """Update task priority."""
        task = self._tasks.get(task_id)

        if task:
            task.priority = priority
            return self._task_queue.update_priority(task_id, priority)

        return False

    # ----- Deadline Operations -----

    def set_deadline(
        self,
        task_id: str,
        due_time: datetime,
        hard: bool = True
    ) -> Optional[Deadline]:
        """Set deadline for task."""
        task = self._tasks.get(task_id)

        if task:
            return self._deadline_tracker.set_deadline(task_id, due_time, hard)

        return None

    def get_deadline(self, task_id: str) -> Optional[Deadline]:
        """Get deadline for task."""
        return self._deadline_tracker.get_deadline(task_id)

    def is_overdue(self, task_id: str) -> bool:
        """Check if task is overdue."""
        return self._deadline_tracker.is_overdue(task_id)

    def get_overdue_tasks(self) -> List[ScheduledTask]:
        """Get overdue tasks."""
        overdue = self._deadline_tracker.get_overdue()
        return [self._tasks[d.task_id] for d in overdue if d.task_id in self._tasks]

    # ----- Resource Operations -----

    def add_resource(
        self,
        resource_type: ResourceType,
        capacity: float = 100.0
    ) -> Resource:
        """Add a resource."""
        return self._resource_manager.add_resource(resource_type, capacity)

    def reserve_resource(
        self,
        task_id: str,
        resource_id: str,
        amount: float
    ) -> bool:
        """Reserve resource for task."""
        return self._resource_manager.reserve(task_id, resource_id, amount)

    def get_resource_availability(self) -> Dict[str, float]:
        """Get resource availability."""
        return self._resource_manager.get_availability()

    # ----- Execution -----

    async def execute_task(self, task: ScheduledTask) -> TaskResult:
        """Execute a single task."""
        task.status = TaskStatus.RUNNING
        self._running.add(task.task_id)

        start_time = time.time()

        try:
            if asyncio.iscoroutinefunction(task.handler):
                result_value = await task.handler()
            else:
                result_value = task.handler()

            duration = time.time() - start_time

            result = TaskResult(
                task_id=task.task_id,
                success=True,
                result=result_value,
                duration=duration
            )

            task.status = TaskStatus.COMPLETED

        except Exception as e:
            duration = time.time() - start_time

            result = TaskResult(
                task_id=task.task_id,
                success=False,
                error=str(e),
                duration=duration
            )

            task.status = TaskStatus.FAILED

        finally:
            self._running.discard(task.task_id)
            task.last_run = datetime.now()
            task.run_count += 1

            if task.schedule:
                task.schedule.run_count += 1

        self._results[task.task_id].append(result)
        self._resource_manager.release(task.task_id)

        self._reschedule_if_needed(task)

        return result

    def _reschedule_if_needed(self, task: ScheduledTask) -> None:
        """Reschedule task if needed."""
        if not task.schedule:
            return

        schedule = task.schedule

        if schedule.max_runs and schedule.run_count >= schedule.max_runs:
            return

        if schedule.schedule_type == ScheduleType.INTERVAL:
            task.next_run = self._calculate_next_interval(
                schedule.interval,
                schedule.interval_unit
            )
            task.status = TaskStatus.SCHEDULED
            self._task_queue.push(task)

        elif schedule.schedule_type == ScheduleType.CRON:
            task.next_run = self._cron_parser.next_run(schedule.cron_expression)
            task.status = TaskStatus.SCHEDULED
            self._task_queue.push(task)

    async def tick(self) -> List[TaskResult]:
        """Process one tick of the scheduler."""
        results = []
        now = datetime.now()

        while len(self._running) < self._config.max_concurrent:
            task = self._task_queue.peek()

            if not task:
                break

            if task.next_run and task.next_run > now:
                break

            task = self._task_queue.pop()

            if task:
                result = await self.execute_task(task)
                results.append(result)

        return results

    async def run(self) -> None:
        """Run the scheduler loop."""
        self._running_flag = True

        while self._running_flag:
            await self.tick()
            await asyncio.sleep(self._config.tick_interval)

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running_flag = False

    # ----- Results -----

    def get_results(self, task_id: str) -> List[TaskResult]:
        """Get results for task."""
        return self._results.get(task_id, [])

    def get_last_result(self, task_id: str) -> Optional[TaskResult]:
        """Get last result for task."""
        results = self._results.get(task_id, [])
        return results[-1] if results else None

    # ----- Status -----

    def get_pending_tasks(self) -> List[ScheduledTask]:
        """Get pending tasks."""
        return [t for t in self._tasks.values() if t.status == TaskStatus.SCHEDULED]

    def get_running_tasks(self) -> List[ScheduledTask]:
        """Get running tasks."""
        return [t for t in self._tasks.values() if t.status == TaskStatus.RUNNING]

    def summary(self) -> Dict[str, Any]:
        """Get scheduler summary."""
        return {
            "total_tasks": len(self._tasks),
            "queued": self._task_queue.count(),
            "running": len(self._running),
            "resources": self._resource_manager.count(),
            "deadlines": self._deadline_tracker.count()
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Scheduling Engine."""
    print("=" * 70)
    print("BAEL - SCHEDULING ENGINE DEMO")
    print("Task Scheduling and Time Management")
    print("=" * 70)
    print()

    engine = SchedulingEngine()

    execution_log = []

    def task_a():
        execution_log.append(("Task A", datetime.now()))
        return "A completed"

    def task_b():
        execution_log.append(("Task B", datetime.now()))
        return "B completed"

    async def async_task():
        await asyncio.sleep(0.1)
        execution_log.append(("Async Task", datetime.now()))
        return "Async completed"

    # 1. Schedule One-Time Task
    print("1. SCHEDULE ONE-TIME TASK:")
    print("-" * 40)

    run_time = datetime.now() + timedelta(seconds=1)
    task1 = engine.schedule_once("task_a", task_a, run_time)

    print(f"   Scheduled: {task1.name}")
    print(f"   Run at: {task1.next_run}")
    print(f"   Status: {task1.status.value}")
    print()

    # 2. Schedule Interval Task
    print("2. SCHEDULE INTERVAL TASK:")
    print("-" * 40)

    task2 = engine.schedule_interval(
        "task_b",
        task_b,
        interval=2,
        unit=TimeUnit.SECONDS,
        max_runs=3
    )

    print(f"   Scheduled: {task2.name}")
    print(f"   Interval: 2 seconds")
    print(f"   Max runs: 3")
    print()

    # 3. Schedule Delayed Task
    print("3. SCHEDULE DELAYED TASK:")
    print("-" * 40)

    task3 = engine.schedule_delayed(
        "async_task",
        async_task,
        delay=1,
        unit=TimeUnit.SECONDS,
        priority=TaskPriority.HIGH
    )

    print(f"   Scheduled: {task3.name}")
    print(f"   Delay: 1 second")
    print(f"   Priority: {task3.priority.value}")
    print()

    # 4. Parse Cron Expression
    print("4. PARSE CRON EXPRESSION:")
    print("-" * 40)

    cron = CronParser()
    parsed = cron.parse("*/5 * * * *")

    print(f"   Expression: */5 * * * *")
    print(f"   Minutes: {parsed['minute'][:5]}...")

    next_run = cron.next_run("0 12 * * *")
    print(f"   Next run for '0 12 * * *': {next_run}")
    print()

    # 5. Set Deadline
    print("5. SET DEADLINE:")
    print("-" * 40)

    deadline = engine.set_deadline(
        task1.task_id,
        datetime.now() + timedelta(minutes=5),
        hard=True
    )

    print(f"   Task: {task1.name}")
    print(f"   Due: {deadline.due_time}")
    print(f"   Hard deadline: {deadline.hard}")
    print(f"   Overdue: {engine.is_overdue(task1.task_id)}")
    print()

    # 6. Add Resources
    print("6. ADD RESOURCES:")
    print("-" * 40)

    cpu = engine.add_resource(ResourceType.CPU, 100.0)
    memory = engine.add_resource(ResourceType.MEMORY, 1024.0)

    print(f"   CPU: {cpu.capacity} units")
    print(f"   Memory: {memory.capacity} MB")
    print()

    # 7. Reserve Resources
    print("7. RESERVE RESOURCES:")
    print("-" * 40)

    reserved = engine.reserve_resource(task1.task_id, cpu.resource_id, 25.0)
    print(f"   Reserved 25 CPU for task_a: {reserved}")

    availability = engine.get_resource_availability()
    print(f"   Available: {availability}")
    print()

    # 8. Get Task
    print("8. GET TASK:")
    print("-" * 40)

    retrieved = engine.get_task(task1.task_id)

    if retrieved:
        print(f"   Name: {retrieved.name}")
        print(f"   Priority: {retrieved.priority.value}")
        print(f"   Status: {retrieved.status.value}")
    print()

    # 9. Update Priority
    print("9. UPDATE PRIORITY:")
    print("-" * 40)

    engine.update_priority(task2.task_id, TaskPriority.URGENT)
    updated = engine.get_task(task2.task_id)

    print(f"   Task: {updated.name}")
    print(f"   New priority: {updated.priority.value}")
    print()

    # 10. Execute Tasks
    print("10. EXECUTE TASKS:")
    print("-" * 40)

    await asyncio.sleep(1.5)

    results = await engine.tick()

    print(f"   Executed: {len(results)} tasks")

    for result in results:
        task = engine.get_task(result.task_id)
        print(f"     {task.name}: {result.success}, {result.duration:.3f}s")
    print()

    # 11. Get Results
    print("11. GET RESULTS:")
    print("-" * 40)

    for task_id in [task1.task_id, task3.task_id]:
        last = engine.get_last_result(task_id)

        if last:
            task = engine.get_task(task_id)
            print(f"   {task.name}: {last.result}")
    print()

    # 12. Pending Tasks
    print("12. PENDING TASKS:")
    print("-" * 40)

    pending = engine.get_pending_tasks()

    print(f"   Count: {len(pending)}")
    for task in pending:
        print(f"     {task.name}: next run {task.next_run}")
    print()

    # 13. Cancel Task
    print("13. CANCEL TASK:")
    print("-" * 40)

    cancelled = engine.cancel_task(task2.task_id)
    task2_updated = engine.get_task(task2.task_id)

    print(f"   Cancelled: {cancelled}")
    print(f"   Status: {task2_updated.status.value}")
    print()

    # 14. Execution Log
    print("14. EXECUTION LOG:")
    print("-" * 40)

    for name, timestamp in execution_log:
        print(f"   {name} at {timestamp.strftime('%H:%M:%S.%f')}")
    print()

    # 15. Summary
    print("15. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Scheduling Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
