#!/usr/bin/env python3
"""
BAEL - Advanced Scheduling System
Task scheduling with cron, intervals, and intelligent prioritization.

Features:
- Cron-based scheduling
- Interval scheduling
- Priority-based execution
- Dependency management
- Retry policies
- Distributed scheduling
- Rate limiting
"""

import asyncio
import hashlib
import heapq
import json
import logging
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# SCHEDULE TYPES
# =============================================================================

class ScheduleType(Enum):
    """Types of schedules."""
    ONCE = "once"
    INTERVAL = "interval"
    CRON = "cron"
    DEPENDENCY = "dependency"


class JobStatus(Enum):
    """Job execution status."""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class Priority(Enum):
    """Job priority levels."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


@dataclass
class RetryPolicy:
    """Retry policy configuration."""
    max_retries: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 300.0  # seconds
    exponential_base: float = 2.0
    jitter: float = 0.1  # random jitter factor

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for attempt."""
        import random

        delay = min(
            self.initial_delay * (self.exponential_base ** attempt),
            self.max_delay
        )

        # Add jitter
        jitter_range = delay * self.jitter
        delay += random.uniform(-jitter_range, jitter_range)

        return max(0, delay)


@dataclass
class JobResult:
    """Result of job execution."""
    job_id: str
    status: JobStatus
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: float = 0
    retries: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "retries": self.retries
        }


# =============================================================================
# CRON PARSER
# =============================================================================

class CronParser:
    """Parse and evaluate cron expressions."""

    # Cron field ranges
    RANGES = {
        "minute": (0, 59),
        "hour": (0, 23),
        "day": (1, 31),
        "month": (1, 12),
        "weekday": (0, 6)
    }

    # Month names
    MONTHS = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
    }

    # Weekday names
    WEEKDAYS = {
        "sun": 0, "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6
    }

    @classmethod
    def parse(cls, expression: str) -> Dict[str, Set[int]]:
        """Parse cron expression into field values."""
        parts = expression.strip().split()

        if len(parts) == 5:
            minute, hour, day, month, weekday = parts
        elif len(parts) == 6:
            # With seconds
            _, minute, hour, day, month, weekday = parts
        else:
            raise ValueError(f"Invalid cron expression: {expression}")

        return {
            "minute": cls._parse_field(minute, "minute"),
            "hour": cls._parse_field(hour, "hour"),
            "day": cls._parse_field(day, "day"),
            "month": cls._parse_field(month, "month"),
            "weekday": cls._parse_field(weekday, "weekday")
        }

    @classmethod
    def _parse_field(cls, field: str, field_name: str) -> Set[int]:
        """Parse a single cron field."""
        min_val, max_val = cls.RANGES[field_name]
        values: Set[int] = set()

        # Replace names with numbers
        field = field.lower()
        if field_name == "month":
            for name, num in cls.MONTHS.items():
                field = field.replace(name, str(num))
        elif field_name == "weekday":
            for name, num in cls.WEEKDAYS.items():
                field = field.replace(name, str(num))

        for part in field.split(","):
            if part == "*":
                values.update(range(min_val, max_val + 1))
            elif "-" in part:
                # Range
                if "/" in part:
                    range_part, step = part.split("/")
                    start, end = map(int, range_part.split("-"))
                    values.update(range(start, end + 1, int(step)))
                else:
                    start, end = map(int, part.split("-"))
                    values.update(range(start, end + 1))
            elif "/" in part:
                # Step
                base, step = part.split("/")
                if base == "*":
                    values.update(range(min_val, max_val + 1, int(step)))
                else:
                    values.update(range(int(base), max_val + 1, int(step)))
            else:
                values.add(int(part))

        return values

    @classmethod
    def next_run(cls, expression: str, after: datetime = None) -> datetime:
        """Calculate next run time for cron expression."""
        if after is None:
            after = datetime.now()

        fields = cls.parse(expression)

        # Start from next minute
        current = after.replace(second=0, microsecond=0) + timedelta(minutes=1)

        # Find next matching time (max 1 year ahead)
        max_iterations = 525600  # minutes in a year

        for _ in range(max_iterations):
            if (current.minute in fields["minute"] and
                current.hour in fields["hour"] and
                current.day in fields["day"] and
                current.month in fields["month"] and
                current.weekday() in fields["weekday"]):
                return current

            current += timedelta(minutes=1)

        raise ValueError(f"No valid run time found for: {expression}")


# =============================================================================
# JOB DEFINITION
# =============================================================================

@dataclass
class Job:
    """Scheduled job definition."""
    id: str
    name: str
    func: Callable
    args: Tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    schedule_type: ScheduleType = ScheduleType.ONCE

    # Timing
    run_at: Optional[datetime] = None
    interval_seconds: float = 0
    cron_expression: Optional[str] = None

    # Execution
    priority: Priority = Priority.NORMAL
    timeout_seconds: float = 300
    retry_policy: Optional[RetryPolicy] = None

    # Dependencies
    depends_on: List[str] = field(default_factory=list)

    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # State
    status: JobStatus = JobStatus.PENDING
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    run_count: int = 0
    error_count: int = 0

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid4())
        self._calculate_next_run()

    def _calculate_next_run(self) -> None:
        """Calculate next run time."""
        now = datetime.now()

        if self.schedule_type == ScheduleType.ONCE:
            self.next_run = self.run_at or now
        elif self.schedule_type == ScheduleType.INTERVAL:
            if self.last_run:
                self.next_run = self.last_run + timedelta(seconds=self.interval_seconds)
            else:
                self.next_run = now
        elif self.schedule_type == ScheduleType.CRON:
            if self.cron_expression:
                self.next_run = CronParser.next_run(self.cron_expression, self.last_run or now)

    def should_run(self, now: datetime = None) -> bool:
        """Check if job should run."""
        if now is None:
            now = datetime.now()

        if self.status in (JobStatus.RUNNING, JobStatus.CANCELLED):
            return False

        if self.schedule_type == ScheduleType.DEPENDENCY:
            return False  # Handled by dependency resolver

        return self.next_run is not None and self.next_run <= now

    def __lt__(self, other: "Job") -> bool:
        """Compare jobs by priority and next run time."""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return (self.next_run or datetime.max) < (other.next_run or datetime.max)


# =============================================================================
# JOB QUEUE
# =============================================================================

class JobQueue:
    """Priority queue for jobs."""

    def __init__(self):
        self._queue: List[Tuple[int, int, datetime, Job]] = []
        self._counter = 0
        self._lock = asyncio.Lock()

    async def push(self, job: Job) -> None:
        """Add job to queue."""
        async with self._lock:
            # Priority tuple: (priority, counter, next_run, job)
            heapq.heappush(
                self._queue,
                (job.priority.value, self._counter, job.next_run or datetime.max, job)
            )
            self._counter += 1

    async def pop(self) -> Optional[Job]:
        """Get highest priority job."""
        async with self._lock:
            if self._queue:
                _, _, _, job = heapq.heappop(self._queue)
                return job
            return None

    async def peek(self) -> Optional[Job]:
        """Peek at highest priority job without removing."""
        async with self._lock:
            if self._queue:
                _, _, _, job = self._queue[0]
                return job
            return None

    async def remove(self, job_id: str) -> bool:
        """Remove job from queue."""
        async with self._lock:
            for i, (_, _, _, job) in enumerate(self._queue):
                if job.id == job_id:
                    self._queue.pop(i)
                    heapq.heapify(self._queue)
                    return True
            return False

    @property
    def size(self) -> int:
        """Get queue size."""
        return len(self._queue)

    @property
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return len(self._queue) == 0


# =============================================================================
# DEPENDENCY RESOLVER
# =============================================================================

class DependencyResolver:
    """Resolve job dependencies."""

    def __init__(self):
        self.dependencies: Dict[str, Set[str]] = {}  # job_id -> depends_on
        self.dependents: Dict[str, Set[str]] = {}  # job_id -> depended_by
        self.completed: Set[str] = set()

    def add_job(self, job: Job) -> None:
        """Add job with dependencies."""
        self.dependencies[job.id] = set(job.depends_on)

        for dep_id in job.depends_on:
            if dep_id not in self.dependents:
                self.dependents[dep_id] = set()
            self.dependents[dep_id].add(job.id)

    def mark_completed(self, job_id: str) -> List[str]:
        """Mark job as completed and return newly runnable jobs."""
        self.completed.add(job_id)

        runnable = []
        for dependent_id in self.dependents.get(job_id, set()):
            if self.can_run(dependent_id):
                runnable.append(dependent_id)

        return runnable

    def can_run(self, job_id: str) -> bool:
        """Check if all dependencies are satisfied."""
        deps = self.dependencies.get(job_id, set())
        return deps.issubset(self.completed)

    def get_order(self, jobs: List[Job]) -> List[Job]:
        """Get topological order of jobs."""
        # Kahn's algorithm
        in_degree: Dict[str, int] = {}
        graph: Dict[str, List[str]] = {}

        for job in jobs:
            in_degree[job.id] = len(job.depends_on)
            graph[job.id] = []

        for job in jobs:
            for dep_id in job.depends_on:
                if dep_id in graph:
                    graph[dep_id].append(job.id)

        # Start with jobs that have no dependencies
        queue = [job for job in jobs if in_degree[job.id] == 0]
        result = []

        while queue:
            job = queue.pop(0)
            result.append(job)

            for dependent_id in graph.get(job.id, []):
                in_degree[dependent_id] -= 1
                if in_degree[dependent_id] == 0:
                    dependent = next((j for j in jobs if j.id == dependent_id), None)
                    if dependent:
                        queue.append(dependent)

        if len(result) != len(jobs):
            raise ValueError("Circular dependency detected")

        return result


# =============================================================================
# RATE LIMITER
# =============================================================================

class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, rate: float, capacity: float):
        self.rate = rate  # tokens per second
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: float = 1.0) -> bool:
        """Try to acquire tokens."""
        async with self._lock:
            now = time.time()

            # Add tokens based on elapsed time
            elapsed = now - self.last_update
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            return False

    async def wait_for(self, tokens: float = 1.0) -> None:
        """Wait until tokens are available."""
        while not await self.acquire(tokens):
            await asyncio.sleep(0.1)


# =============================================================================
# SCHEDULER
# =============================================================================

class Scheduler:
    """Advanced job scheduler."""

    def __init__(
        self,
        max_workers: int = 10,
        default_retry_policy: Optional[RetryPolicy] = None
    ):
        self.max_workers = max_workers
        self.default_retry_policy = default_retry_policy or RetryPolicy()

        self.jobs: Dict[str, Job] = {}
        self.queue = JobQueue()
        self.dependency_resolver = DependencyResolver()
        self.rate_limiters: Dict[str, RateLimiter] = {}

        self._running = False
        self._workers: List[asyncio.Task] = []
        self._results: Dict[str, JobResult] = {}
        self._callbacks: Dict[str, List[Callable]] = {}

    def add_job(
        self,
        func: Callable,
        name: str = None,
        schedule_type: ScheduleType = ScheduleType.ONCE,
        run_at: datetime = None,
        interval_seconds: float = 0,
        cron: str = None,
        priority: Priority = Priority.NORMAL,
        timeout: float = 300,
        retry_policy: RetryPolicy = None,
        depends_on: List[str] = None,
        tags: List[str] = None,
        **kwargs
    ) -> str:
        """Add a job to the scheduler."""
        job = Job(
            id=str(uuid4()),
            name=name or func.__name__,
            func=func,
            kwargs=kwargs,
            schedule_type=schedule_type,
            run_at=run_at,
            interval_seconds=interval_seconds,
            cron_expression=cron,
            priority=priority,
            timeout_seconds=timeout,
            retry_policy=retry_policy or self.default_retry_policy,
            depends_on=depends_on or [],
            tags=tags or []
        )

        self.jobs[job.id] = job

        if job.depends_on:
            self.dependency_resolver.add_job(job)
        else:
            asyncio.create_task(self.queue.push(job))

        logger.info(f"Added job: {job.name} ({job.id})")

        return job.id

    def add_rate_limiter(self, name: str, rate: float, capacity: float) -> None:
        """Add a rate limiter."""
        self.rate_limiters[name] = RateLimiter(rate, capacity)

    def on_job_complete(self, job_id: str, callback: Callable) -> None:
        """Register callback for job completion."""
        if job_id not in self._callbacks:
            self._callbacks[job_id] = []
        self._callbacks[job_id].append(callback)

    async def run_job(self, job: Job) -> JobResult:
        """Execute a single job."""
        job.status = JobStatus.RUNNING
        job.last_run = datetime.now()

        result = JobResult(
            job_id=job.id,
            status=JobStatus.RUNNING,
            started_at=job.last_run
        )

        retry_count = 0
        retry_policy = job.retry_policy or self.default_retry_policy

        while True:
            try:
                # Apply timeout
                if asyncio.iscoroutinefunction(job.func):
                    output = await asyncio.wait_for(
                        job.func(*job.args, **job.kwargs),
                        timeout=job.timeout_seconds
                    )
                else:
                    output = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: job.func(*job.args, **job.kwargs)
                    )

                result.status = JobStatus.COMPLETED
                result.result = output
                job.status = JobStatus.COMPLETED
                job.run_count += 1

                break

            except asyncio.TimeoutError:
                result.error = f"Job timed out after {job.timeout_seconds}s"
                result.status = JobStatus.FAILED
                job.status = JobStatus.FAILED
                job.error_count += 1
                break

            except Exception as e:
                retry_count += 1
                result.retries = retry_count

                if retry_count <= retry_policy.max_retries:
                    delay = retry_policy.get_delay(retry_count)
                    logger.warning(f"Job {job.name} failed, retrying in {delay:.1f}s (attempt {retry_count})")
                    job.status = JobStatus.RETRYING
                    await asyncio.sleep(delay)
                else:
                    result.error = str(e)
                    result.status = JobStatus.FAILED
                    job.status = JobStatus.FAILED
                    job.error_count += 1
                    break

        result.completed_at = datetime.now()
        result.duration_ms = (result.completed_at - result.started_at).total_seconds() * 1000

        # Update next run for recurring jobs
        job._calculate_next_run()

        # Handle dependencies
        if result.status == JobStatus.COMPLETED:
            runnable = self.dependency_resolver.mark_completed(job.id)
            for job_id in runnable:
                if job_id in self.jobs:
                    await self.queue.push(self.jobs[job_id])

        # Store result
        self._results[job.id] = result

        # Call callbacks
        for callback in self._callbacks.get(job.id, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(result)
                else:
                    callback(result)
            except Exception as e:
                logger.error(f"Callback error: {e}")

        return result

    async def _worker(self, worker_id: int) -> None:
        """Worker coroutine that processes jobs."""
        logger.debug(f"Worker {worker_id} started")

        while self._running:
            try:
                job = await self.queue.pop()

                if job is None:
                    await asyncio.sleep(0.1)
                    continue

                if not job.should_run():
                    # Re-queue if not ready
                    await self.queue.push(job)
                    await asyncio.sleep(0.1)
                    continue

                logger.info(f"Worker {worker_id} executing: {job.name}")
                await self.run_job(job)

                # Re-queue if recurring
                if job.schedule_type in (ScheduleType.INTERVAL, ScheduleType.CRON):
                    if job.status != JobStatus.CANCELLED:
                        job.status = JobStatus.SCHEDULED
                        await self.queue.push(job)

            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(1)

        logger.debug(f"Worker {worker_id} stopped")

    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            return

        self._running = True

        # Start workers
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(i))
            self._workers.append(worker)

        logger.info(f"Scheduler started with {self.max_workers} workers")

    async def stop(self, wait: bool = True) -> None:
        """Stop the scheduler."""
        self._running = False

        if wait:
            # Wait for workers to finish
            await asyncio.gather(*self._workers, return_exceptions=True)

        self._workers.clear()
        logger.info("Scheduler stopped")

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a job."""
        if job_id in self.jobs:
            self.jobs[job_id].status = JobStatus.CANCELLED
            await self.queue.remove(job_id)
            return True
        return False

    def get_result(self, job_id: str) -> Optional[JobResult]:
        """Get job result."""
        return self._results.get(job_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        status_counts = {}
        for job in self.jobs.values():
            status = job.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_jobs": len(self.jobs),
            "queue_size": self.queue.size,
            "workers": self.max_workers,
            "running": self._running,
            "status_counts": status_counts,
            "completed_results": len(self._results)
        }


# =============================================================================
# DECORATORS
# =============================================================================

def scheduled(
    scheduler: Scheduler = None,
    cron: str = None,
    interval: float = None,
    priority: Priority = Priority.NORMAL,
    timeout: float = 300
):
    """Decorator to schedule a function."""
    def decorator(func: Callable) -> Callable:
        if scheduler is not None:
            schedule_type = ScheduleType.CRON if cron else ScheduleType.INTERVAL
            scheduler.add_job(
                func,
                schedule_type=schedule_type,
                cron=cron,
                interval_seconds=interval or 0,
                priority=priority,
                timeout=timeout
            )
        return func
    return decorator


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def every(interval: float) -> Dict[str, Any]:
    """Create interval schedule config."""
    return {
        "schedule_type": ScheduleType.INTERVAL,
        "interval_seconds": interval
    }


def cron(expression: str) -> Dict[str, Any]:
    """Create cron schedule config."""
    return {
        "schedule_type": ScheduleType.CRON,
        "cron": expression
    }


def at(time: datetime) -> Dict[str, Any]:
    """Create one-time schedule config."""
    return {
        "schedule_type": ScheduleType.ONCE,
        "run_at": time
    }


# =============================================================================
# MAIN
# =============================================================================

async def demo():
    """Demo the scheduler."""
    scheduler = Scheduler(max_workers=3)

    async def sample_task(name: str):
        print(f"Running task: {name}")
        await asyncio.sleep(1)
        return f"Completed: {name}"

    def sync_task(x: int) -> int:
        print(f"Computing: {x}")
        return x * 2

    # Add jobs
    job1 = scheduler.add_job(
        sample_task,
        name="async_task",
        priority=Priority.HIGH,
        name="First task"
    )

    job2 = scheduler.add_job(
        sync_task,
        name="sync_task",
        priority=Priority.NORMAL,
        x=42
    )

    job3 = scheduler.add_job(
        sample_task,
        name="dependent_task",
        schedule_type=ScheduleType.DEPENDENCY,
        depends_on=[job1],
        name="After first"
    )

    # Interval job
    scheduler.add_job(
        sample_task,
        name="recurring",
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=5,
        name="Every 5 seconds"
    )

    # Start scheduler
    await scheduler.start()

    # Run for a bit
    await asyncio.sleep(10)

    # Show stats
    print("\nStats:", scheduler.get_stats())

    # Stop
    await scheduler.stop()


if __name__ == "__main__":
    asyncio.run(demo())
