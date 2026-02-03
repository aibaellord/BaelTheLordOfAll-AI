#!/usr/bin/env python3
"""
BAEL - Background Job Scheduler
Comprehensive background job and task scheduling system.

Features:
- Job scheduling (cron, interval, one-time)
- Priority queues
- Retry policies
- Job dependencies
- Worker pools
- Rate limiting
- Job history
- Dead letter queue
- Job progress tracking
- Distributed locking
"""

import asyncio
import hashlib
import heapq
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import (Any, Awaitable, Callable, Dict, Generic, List, Optional,
                    Set, Tuple, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class JobStatus(Enum):
    """Job execution status."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"
    DEAD = "dead"


class JobPriority(Enum):
    """Job priorities."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class ScheduleType(Enum):
    """Schedule types."""
    IMMEDIATE = "immediate"
    DELAYED = "delayed"
    CRON = "cron"
    INTERVAL = "interval"
    ONE_TIME = "one_time"


class RetryStrategy(Enum):
    """Retry strategies."""
    NONE = "none"
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class RetryConfig:
    """Retry configuration."""
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 300.0
    multiplier: float = 2.0

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for attempt."""
        if self.strategy == RetryStrategy.NONE:
            return 0.0

        if self.strategy == RetryStrategy.FIXED:
            return self.initial_delay

        if self.strategy == RetryStrategy.LINEAR:
            delay = self.initial_delay * attempt
            return min(delay, self.max_delay)

        if self.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.initial_delay * (self.multiplier ** (attempt - 1))
            return min(delay, self.max_delay)

        return self.initial_delay


@dataclass
class CronSchedule:
    """Cron schedule definition."""
    minute: str = "*"
    hour: str = "*"
    day_of_month: str = "*"
    month: str = "*"
    day_of_week: str = "*"

    def matches(self, dt: datetime) -> bool:
        """Check if datetime matches cron schedule."""
        return (
            self._matches_field(self.minute, dt.minute, 0, 59) and
            self._matches_field(self.hour, dt.hour, 0, 23) and
            self._matches_field(self.day_of_month, dt.day, 1, 31) and
            self._matches_field(self.month, dt.month, 1, 12) and
            self._matches_field(self.day_of_week, dt.weekday(), 0, 6)
        )

    def _matches_field(
        self,
        pattern: str,
        value: int,
        min_val: int,
        max_val: int
    ) -> bool:
        """Check if value matches pattern."""
        if pattern == "*":
            return True

        # Handle comma-separated values
        if "," in pattern:
            values = [int(v) for v in pattern.split(",")]
            return value in values

        # Handle ranges
        if "-" in pattern:
            start, end = pattern.split("-")
            return int(start) <= value <= int(end)

        # Handle steps
        if "/" in pattern:
            base, step = pattern.split("/")
            step = int(step)

            if base == "*":
                return value % step == 0

            return (value - int(base)) % step == 0

        # Exact match
        return value == int(pattern)

    def next_run(self, after: datetime = None) -> datetime:
        """Calculate next run time."""
        if after is None:
            after = datetime.now()

        dt = after.replace(second=0, microsecond=0) + timedelta(minutes=1)

        for _ in range(525600):  # Max 1 year
            if self.matches(dt):
                return dt

            dt += timedelta(minutes=1)

        return dt


@dataclass
class JobDefinition:
    """Job definition."""
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    handler: str = ""
    args: List[Any] = field(default_factory=list)
    kwargs: Dict[str, Any] = field(default_factory=dict)

    # Scheduling
    schedule_type: ScheduleType = ScheduleType.IMMEDIATE
    scheduled_at: float = 0.0
    interval: float = 0.0  # seconds for interval jobs
    cron: Optional[CronSchedule] = None

    # Priority and retry
    priority: JobPriority = JobPriority.NORMAL
    retry_config: RetryConfig = field(default_factory=RetryConfig)

    # Dependencies
    dependencies: List[str] = field(default_factory=list)

    # Timeout
    timeout: float = 300.0  # 5 minutes default

    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Queue
    queue: str = "default"


@dataclass
class JobExecution:
    """Job execution instance."""
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str = ""
    status: JobStatus = JobStatus.PENDING

    # Timing
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    completed_at: float = 0.0

    # Progress
    progress: float = 0.0  # 0-100
    progress_message: str = ""

    # Result
    result: Any = None
    error: str = ""

    # Retry info
    attempt: int = 1
    next_retry_at: float = 0.0

    # Worker
    worker_id: str = ""

    @property
    def duration(self) -> float:
        if self.started_at == 0:
            return 0.0

        end = self.completed_at if self.completed_at > 0 else time.time()
        return end - self.started_at

    def __lt__(self, other):
        return self.created_at < other.created_at


@dataclass
class Worker:
    """Worker definition."""
    worker_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    queues: List[str] = field(default_factory=lambda: ["default"])
    concurrency: int = 1
    status: str = "idle"
    current_jobs: List[str] = field(default_factory=list)
    processed_count: int = 0
    failed_count: int = 0
    started_at: float = field(default_factory=time.time)


@dataclass
class QueueStats:
    """Queue statistics."""
    name: str = ""
    pending: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0
    dead: int = 0


# =============================================================================
# JOB HANDLER REGISTRY
# =============================================================================

class JobHandlerRegistry:
    """Registry for job handlers."""

    def __init__(self):
        self._handlers: Dict[str, Callable] = {}

    def register(
        self,
        name: str,
        handler: Callable
    ) -> None:
        """Register a job handler."""
        self._handlers[name] = handler

    def get(self, name: str) -> Optional[Callable]:
        """Get handler by name."""
        return self._handlers.get(name)

    def decorator(self, name: str = None):
        """Decorator for registering handlers."""
        def wrapper(func: Callable):
            handler_name = name or func.__name__
            self.register(handler_name, func)
            return func

        return wrapper

    def list_handlers(self) -> List[str]:
        """List all registered handlers."""
        return list(self._handlers.keys())


# =============================================================================
# JOB STORE
# =============================================================================

class JobStore(ABC):
    """Abstract job store."""

    @abstractmethod
    async def save_job(self, job: JobDefinition) -> bool:
        pass

    @abstractmethod
    async def get_job(self, job_id: str) -> Optional[JobDefinition]:
        pass

    @abstractmethod
    async def delete_job(self, job_id: str) -> bool:
        pass

    @abstractmethod
    async def save_execution(self, execution: JobExecution) -> bool:
        pass

    @abstractmethod
    async def get_execution(self, execution_id: str) -> Optional[JobExecution]:
        pass

    @abstractmethod
    async def get_job_executions(self, job_id: str) -> List[JobExecution]:
        pass


class InMemoryJobStore(JobStore):
    """In-memory job store."""

    def __init__(self):
        self._jobs: Dict[str, JobDefinition] = {}
        self._executions: Dict[str, JobExecution] = {}
        self._job_executions: Dict[str, List[str]] = defaultdict(list)

    async def save_job(self, job: JobDefinition) -> bool:
        self._jobs[job.job_id] = job
        return True

    async def get_job(self, job_id: str) -> Optional[JobDefinition]:
        return self._jobs.get(job_id)

    async def delete_job(self, job_id: str) -> bool:
        if job_id in self._jobs:
            del self._jobs[job_id]
            return True
        return False

    async def save_execution(self, execution: JobExecution) -> bool:
        self._executions[execution.execution_id] = execution
        self._job_executions[execution.job_id].append(execution.execution_id)
        return True

    async def get_execution(self, execution_id: str) -> Optional[JobExecution]:
        return self._executions.get(execution_id)

    async def get_job_executions(self, job_id: str) -> List[JobExecution]:
        exec_ids = self._job_executions.get(job_id, [])

        return [
            self._executions[eid]
            for eid in exec_ids
            if eid in self._executions
        ]

    async def list_jobs(self) -> List[JobDefinition]:
        return list(self._jobs.values())


# =============================================================================
# JOB QUEUE
# =============================================================================

class JobQueue:
    """Priority job queue."""

    def __init__(self, name: str = "default"):
        self.name = name
        self._queue: List[Tuple[int, float, JobExecution]] = []
        self._pending: Dict[str, JobExecution] = {}
        self._lock = asyncio.Lock()

    async def enqueue(self, execution: JobExecution, priority: JobPriority) -> None:
        """Add job to queue."""
        async with self._lock:
            heapq.heappush(
                self._queue,
                (priority.value, execution.created_at, execution)
            )
            self._pending[execution.execution_id] = execution

    async def dequeue(self) -> Optional[JobExecution]:
        """Get next job from queue."""
        async with self._lock:
            while self._queue:
                _, _, execution = heapq.heappop(self._queue)

                if execution.execution_id in self._pending:
                    del self._pending[execution.execution_id]
                    return execution

        return None

    async def peek(self) -> Optional[JobExecution]:
        """Peek at next job without removing."""
        async with self._lock:
            if self._queue:
                return self._queue[0][2]

        return None

    async def remove(self, execution_id: str) -> bool:
        """Remove job from queue."""
        async with self._lock:
            if execution_id in self._pending:
                del self._pending[execution_id]
                return True

        return False

    @property
    def size(self) -> int:
        return len(self._pending)

    def is_empty(self) -> bool:
        return len(self._pending) == 0


# =============================================================================
# DEAD LETTER QUEUE
# =============================================================================

class DeadLetterQueue:
    """Dead letter queue for failed jobs."""

    def __init__(self, max_size: int = 1000):
        self._queue: List[JobExecution] = []
        self._max_size = max_size

    def add(self, execution: JobExecution) -> None:
        """Add failed job to DLQ."""
        execution.status = JobStatus.DEAD
        self._queue.append(execution)

        # Trim if needed
        if len(self._queue) > self._max_size:
            self._queue = self._queue[-self._max_size:]

    def get_all(self) -> List[JobExecution]:
        """Get all dead jobs."""
        return self._queue.copy()

    def retry(self, execution_id: str) -> Optional[JobExecution]:
        """Retry a dead job."""
        for i, execution in enumerate(self._queue):
            if execution.execution_id == execution_id:
                del self._queue[i]
                execution.status = JobStatus.RETRYING
                execution.attempt = 1
                return execution

        return None

    def clear(self) -> int:
        """Clear all dead jobs."""
        count = len(self._queue)
        self._queue.clear()
        return count

    @property
    def size(self) -> int:
        return len(self._queue)


# =============================================================================
# RATE LIMITER
# =============================================================================

class RateLimiter:
    """Job rate limiter."""

    def __init__(self):
        self._limits: Dict[str, Tuple[int, float]] = {}  # queue -> (max, window)
        self._counts: Dict[str, List[float]] = defaultdict(list)

    def set_limit(
        self,
        queue: str,
        max_jobs: int,
        window_seconds: float
    ) -> None:
        """Set rate limit for queue."""
        self._limits[queue] = (max_jobs, window_seconds)

    def can_process(self, queue: str) -> bool:
        """Check if job can be processed."""
        if queue not in self._limits:
            return True

        max_jobs, window = self._limits[queue]
        now = time.time()

        # Clean old entries
        self._counts[queue] = [
            t for t in self._counts[queue]
            if now - t < window
        ]

        return len(self._counts[queue]) < max_jobs

    def record(self, queue: str) -> None:
        """Record job processing."""
        self._counts[queue].append(time.time())


# =============================================================================
# JOB SCHEDULER
# =============================================================================

class JobScheduler:
    """
    Comprehensive Job Scheduler for BAEL.
    """

    def __init__(self):
        self.store = InMemoryJobStore()
        self.handlers = JobHandlerRegistry()
        self.dlq = DeadLetterQueue()
        self.rate_limiter = RateLimiter()

        self._queues: Dict[str, JobQueue] = {"default": JobQueue("default")}
        self._workers: Dict[str, Worker] = {}
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        self._worker_tasks: Dict[str, asyncio.Task] = {}

    # -------------------------------------------------------------------------
    # QUEUE MANAGEMENT
    # -------------------------------------------------------------------------

    def create_queue(self, name: str) -> JobQueue:
        """Create a new queue."""
        if name not in self._queues:
            self._queues[name] = JobQueue(name)

        return self._queues[name]

    def get_queue(self, name: str) -> Optional[JobQueue]:
        """Get queue by name."""
        return self._queues.get(name)

    def list_queues(self) -> List[str]:
        """List all queues."""
        return list(self._queues.keys())

    # -------------------------------------------------------------------------
    # JOB SCHEDULING
    # -------------------------------------------------------------------------

    async def schedule(
        self,
        name: str,
        handler: str,
        args: List[Any] = None,
        kwargs: Dict[str, Any] = None,
        priority: JobPriority = JobPriority.NORMAL,
        queue: str = "default",
        delay: float = 0.0,
        retry_config: RetryConfig = None,
        timeout: float = 300.0,
        tags: List[str] = None,
        dependencies: List[str] = None
    ) -> JobDefinition:
        """Schedule a new job."""
        job = JobDefinition(
            name=name,
            handler=handler,
            args=args or [],
            kwargs=kwargs or {},
            priority=priority,
            queue=queue,
            timeout=timeout,
            tags=tags or [],
            dependencies=dependencies or [],
            retry_config=retry_config or RetryConfig()
        )

        if delay > 0:
            job.schedule_type = ScheduleType.DELAYED
            job.scheduled_at = time.time() + delay
        else:
            job.schedule_type = ScheduleType.IMMEDIATE
            job.scheduled_at = time.time()

        await self.store.save_job(job)

        # Create execution
        execution = JobExecution(
            job_id=job.job_id,
            status=JobStatus.PENDING
        )

        await self.store.save_execution(execution)

        # Queue if immediate
        if job.schedule_type == ScheduleType.IMMEDIATE:
            await self._enqueue(job, execution)

        return job

    async def schedule_at(
        self,
        name: str,
        handler: str,
        run_at: datetime,
        **kwargs
    ) -> JobDefinition:
        """Schedule job at specific time."""
        delay = (run_at - datetime.now()).total_seconds()
        delay = max(0, delay)

        return await self.schedule(name, handler, delay=delay, **kwargs)

    async def schedule_cron(
        self,
        name: str,
        handler: str,
        cron: CronSchedule,
        **kwargs
    ) -> JobDefinition:
        """Schedule recurring cron job."""
        job = JobDefinition(
            name=name,
            handler=handler,
            args=kwargs.pop("args", []),
            kwargs=kwargs.pop("kwargs", {}),
            schedule_type=ScheduleType.CRON,
            cron=cron,
            **kwargs
        )

        # Calculate next run
        next_run = cron.next_run()
        job.scheduled_at = next_run.timestamp()

        await self.store.save_job(job)

        return job

    async def schedule_interval(
        self,
        name: str,
        handler: str,
        interval: float,
        start_immediately: bool = True,
        **kwargs
    ) -> JobDefinition:
        """Schedule recurring interval job."""
        job = JobDefinition(
            name=name,
            handler=handler,
            args=kwargs.pop("args", []),
            kwargs=kwargs.pop("kwargs", {}),
            schedule_type=ScheduleType.INTERVAL,
            interval=interval,
            **kwargs
        )

        if start_immediately:
            job.scheduled_at = time.time()
        else:
            job.scheduled_at = time.time() + interval

        await self.store.save_job(job)

        return job

    async def _enqueue(
        self,
        job: JobDefinition,
        execution: JobExecution
    ) -> None:
        """Enqueue job for execution."""
        queue = self._queues.get(job.queue)

        if not queue:
            queue = self.create_queue(job.queue)

        execution.status = JobStatus.QUEUED
        await self.store.save_execution(execution)

        await queue.enqueue(execution, job.priority)

    # -------------------------------------------------------------------------
    # JOB CONTROL
    # -------------------------------------------------------------------------

    async def cancel(self, job_id: str) -> bool:
        """Cancel a job."""
        job = await self.store.get_job(job_id)

        if not job:
            return False

        executions = await self.store.get_job_executions(job_id)

        for execution in executions:
            if execution.status in [JobStatus.PENDING, JobStatus.QUEUED]:
                execution.status = JobStatus.CANCELLED
                await self.store.save_execution(execution)

                # Remove from queue
                queue = self._queues.get(job.queue)

                if queue:
                    await queue.remove(execution.execution_id)

        return True

    async def retry(self, execution_id: str) -> Optional[JobExecution]:
        """Retry a failed execution."""
        execution = await self.store.get_execution(execution_id)

        if not execution:
            return None

        if execution.status not in [JobStatus.FAILED, JobStatus.DEAD]:
            return None

        job = await self.store.get_job(execution.job_id)

        if not job:
            return None

        # Create new execution
        new_execution = JobExecution(
            job_id=job.job_id,
            status=JobStatus.PENDING,
            attempt=execution.attempt + 1
        )

        await self.store.save_execution(new_execution)
        await self._enqueue(job, new_execution)

        return new_execution

    async def get_job(self, job_id: str) -> Optional[JobDefinition]:
        """Get job by ID."""
        return await self.store.get_job(job_id)

    async def get_execution(self, execution_id: str) -> Optional[JobExecution]:
        """Get execution by ID."""
        return await self.store.get_execution(execution_id)

    async def get_job_history(
        self,
        job_id: str,
        limit: int = 10
    ) -> List[JobExecution]:
        """Get job execution history."""
        executions = await self.store.get_job_executions(job_id)
        return sorted(executions, key=lambda e: e.created_at, reverse=True)[:limit]

    # -------------------------------------------------------------------------
    # WORKER MANAGEMENT
    # -------------------------------------------------------------------------

    def create_worker(
        self,
        name: str,
        queues: List[str] = None,
        concurrency: int = 1
    ) -> Worker:
        """Create a worker."""
        worker = Worker(
            name=name,
            queues=queues or ["default"],
            concurrency=concurrency
        )

        self._workers[worker.worker_id] = worker

        return worker

    def get_worker(self, worker_id: str) -> Optional[Worker]:
        """Get worker by ID."""
        return self._workers.get(worker_id)

    def list_workers(self) -> List[Worker]:
        """List all workers."""
        return list(self._workers.values())

    async def _run_worker(self, worker: Worker) -> None:
        """Run worker loop."""
        while self._running:
            if len(worker.current_jobs) >= worker.concurrency:
                await asyncio.sleep(0.1)
                continue

            # Find job from queues
            execution = None
            job = None

            for queue_name in worker.queues:
                queue = self._queues.get(queue_name)

                if not queue:
                    continue

                # Check rate limit
                if not self.rate_limiter.can_process(queue_name):
                    continue

                execution = await queue.dequeue()

                if execution:
                    job = await self.store.get_job(execution.job_id)

                    if job:
                        self.rate_limiter.record(queue_name)
                        break

            if not execution or not job:
                await asyncio.sleep(0.1)
                continue

            # Process job
            worker.current_jobs.append(execution.execution_id)
            worker.status = "busy"

            try:
                await self._execute_job(job, execution, worker)
                worker.processed_count += 1
            except Exception as e:
                worker.failed_count += 1
                logger.error(f"Job failed: {e}")
            finally:
                worker.current_jobs.remove(execution.execution_id)

                if not worker.current_jobs:
                    worker.status = "idle"

    async def _execute_job(
        self,
        job: JobDefinition,
        execution: JobExecution,
        worker: Worker
    ) -> None:
        """Execute a job."""
        handler = self.handlers.get(job.handler)

        if not handler:
            execution.status = JobStatus.FAILED
            execution.error = f"Handler not found: {job.handler}"
            await self.store.save_execution(execution)
            return

        # Check dependencies
        if not await self._check_dependencies(job):
            # Re-queue with delay
            execution.status = JobStatus.PENDING
            await self.store.save_execution(execution)
            await asyncio.sleep(1)
            await self._enqueue(job, execution)
            return

        # Start execution
        execution.status = JobStatus.RUNNING
        execution.started_at = time.time()
        execution.worker_id = worker.worker_id
        await self.store.save_execution(execution)

        try:
            # Execute with timeout
            if asyncio.iscoroutinefunction(handler):
                result = await asyncio.wait_for(
                    handler(*job.args, **job.kwargs),
                    timeout=job.timeout
                )
            else:
                result = await asyncio.wait_for(
                    asyncio.to_thread(handler, *job.args, **job.kwargs),
                    timeout=job.timeout
                )

            execution.status = JobStatus.COMPLETED
            execution.result = result
            execution.completed_at = time.time()
            execution.progress = 100.0

        except asyncio.TimeoutError:
            execution.status = JobStatus.FAILED
            execution.error = f"Job timed out after {job.timeout}s"
            await self._handle_failure(job, execution)

        except Exception as e:
            execution.status = JobStatus.FAILED
            execution.error = str(e)
            await self._handle_failure(job, execution)

        await self.store.save_execution(execution)

        # Schedule next for recurring jobs
        if execution.status == JobStatus.COMPLETED:
            await self._schedule_next_run(job)

    async def _handle_failure(
        self,
        job: JobDefinition,
        execution: JobExecution
    ) -> None:
        """Handle job failure."""
        retry_config = job.retry_config

        if execution.attempt >= retry_config.max_retries:
            # Send to DLQ
            execution.status = JobStatus.DEAD
            self.dlq.add(execution)
            return

        if retry_config.strategy == RetryStrategy.NONE:
            return

        # Schedule retry
        delay = retry_config.get_delay(execution.attempt)

        new_execution = JobExecution(
            job_id=job.job_id,
            status=JobStatus.RETRYING,
            attempt=execution.attempt + 1,
            next_retry_at=time.time() + delay
        )

        await self.store.save_execution(new_execution)

        # Delay then queue
        await asyncio.sleep(delay)
        await self._enqueue(job, new_execution)

    async def _check_dependencies(self, job: JobDefinition) -> bool:
        """Check if job dependencies are met."""
        for dep_id in job.dependencies:
            dep_job = await self.store.get_job(dep_id)

            if not dep_job:
                continue

            executions = await self.store.get_job_executions(dep_id)

            if not executions:
                return False

            latest = max(executions, key=lambda e: e.created_at)

            if latest.status != JobStatus.COMPLETED:
                return False

        return True

    async def _schedule_next_run(self, job: JobDefinition) -> None:
        """Schedule next run for recurring jobs."""
        if job.schedule_type == ScheduleType.INTERVAL:
            job.scheduled_at = time.time() + job.interval
            await self.store.save_job(job)

            execution = JobExecution(
                job_id=job.job_id,
                status=JobStatus.PENDING
            )
            await self.store.save_execution(execution)

        elif job.schedule_type == ScheduleType.CRON and job.cron:
            next_run = job.cron.next_run()
            job.scheduled_at = next_run.timestamp()
            await self.store.save_job(job)

    # -------------------------------------------------------------------------
    # SCHEDULER CONTROL
    # -------------------------------------------------------------------------

    async def start(self) -> None:
        """Start the scheduler."""
        self._running = True

        # Start scheduler loop
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())

        # Start workers
        for worker in self._workers.values():
            task = asyncio.create_task(self._run_worker(worker))
            self._worker_tasks[worker.worker_id] = task

    async def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False

        if self._scheduler_task:
            self._scheduler_task.cancel()

            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

        for task in self._worker_tasks.values():
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            now = time.time()

            # Check scheduled jobs
            jobs = await self.store.list_jobs()

            for job in jobs:
                if job.scheduled_at <= now:
                    if job.schedule_type in [ScheduleType.DELAYED, ScheduleType.CRON, ScheduleType.INTERVAL]:
                        execution = JobExecution(
                            job_id=job.job_id,
                            status=JobStatus.PENDING
                        )

                        await self.store.save_execution(execution)
                        await self._enqueue(job, execution)

                        # Update scheduled time for one-time
                        if job.schedule_type == ScheduleType.DELAYED:
                            job.scheduled_at = float('inf')
                            await self.store.save_job(job)

            await asyncio.sleep(1)

    # -------------------------------------------------------------------------
    # PROGRESS TRACKING
    # -------------------------------------------------------------------------

    async def update_progress(
        self,
        execution_id: str,
        progress: float,
        message: str = ""
    ) -> None:
        """Update job progress."""
        execution = await self.store.get_execution(execution_id)

        if execution:
            execution.progress = min(100, max(0, progress))
            execution.progress_message = message
            await self.store.save_execution(execution)

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    async def get_queue_stats(self, queue_name: str) -> QueueStats:
        """Get queue statistics."""
        queue = self._queues.get(queue_name)

        if not queue:
            return QueueStats(name=queue_name)

        # Count from store
        jobs = await self.store.list_jobs()
        queue_jobs = [j for j in jobs if j.queue == queue_name]

        stats = QueueStats(name=queue_name, pending=queue.size)

        for job in queue_jobs:
            executions = await self.store.get_job_executions(job.job_id)

            for exec in executions:
                if exec.status == JobStatus.RUNNING:
                    stats.running += 1
                elif exec.status == JobStatus.COMPLETED:
                    stats.completed += 1
                elif exec.status == JobStatus.FAILED:
                    stats.failed += 1
                elif exec.status == JobStatus.DEAD:
                    stats.dead += 1

        return stats

    async def get_stats(self) -> Dict[str, Any]:
        """Get overall statistics."""
        jobs = await self.store.list_jobs()

        return {
            "total_jobs": len(jobs),
            "queues": len(self._queues),
            "workers": len(self._workers),
            "dead_letter_queue": self.dlq.size,
            "queue_stats": {
                name: await self.get_queue_stats(name)
                for name in self._queues.keys()
            }
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Job Scheduler System."""
    print("=" * 70)
    print("BAEL - BACKGROUND JOB SCHEDULER DEMO")
    print("Comprehensive Job Scheduling System")
    print("=" * 70)
    print()

    scheduler = JobScheduler()

    # 1. Register Handlers
    print("1. REGISTER JOB HANDLERS:")
    print("-" * 40)

    @scheduler.handlers.decorator("process_data")
    async def process_data(data_id: str):
        await asyncio.sleep(0.1)  # Simulate work
        return f"Processed {data_id}"

    @scheduler.handlers.decorator("send_email")
    async def send_email(to: str, subject: str):
        await asyncio.sleep(0.05)
        return f"Sent to {to}: {subject}"

    @scheduler.handlers.decorator("cleanup")
    async def cleanup():
        await asyncio.sleep(0.02)
        return "Cleanup complete"

    print(f"   Registered: {scheduler.handlers.list_handlers()}")
    print()

    # 2. Create Workers
    print("2. CREATE WORKERS:")
    print("-" * 40)

    worker1 = scheduler.create_worker("worker-1", ["default"], concurrency=2)
    worker2 = scheduler.create_worker("worker-2", ["high-priority"], concurrency=1)

    print(f"   Created: {worker1.name} (queues: {worker1.queues})")
    print(f"   Created: {worker2.name} (queues: {worker2.queues})")
    print()

    # 3. Create Queues
    print("3. CREATE QUEUES:")
    print("-" * 40)

    scheduler.create_queue("high-priority")
    scheduler.create_queue("batch")

    print(f"   Queues: {scheduler.list_queues()}")
    print()

    # 4. Schedule Immediate Jobs
    print("4. SCHEDULE IMMEDIATE JOBS:")
    print("-" * 40)

    job1 = await scheduler.schedule(
        name="Process User Data",
        handler="process_data",
        args=["user_123"],
        priority=JobPriority.NORMAL,
        tags=["data", "processing"]
    )
    print(f"   Scheduled: {job1.name} (ID: {job1.job_id[:8]}...)")

    job2 = await scheduler.schedule(
        name="Send Welcome Email",
        handler="send_email",
        args=["user@example.com", "Welcome!"],
        priority=JobPriority.HIGH,
        queue="high-priority"
    )
    print(f"   Scheduled: {job2.name} (ID: {job2.job_id[:8]}...)")
    print()

    # 5. Schedule Delayed Job
    print("5. SCHEDULE DELAYED JOB:")
    print("-" * 40)

    job3 = await scheduler.schedule(
        name="Delayed Task",
        handler="cleanup",
        delay=2.0
    )
    print(f"   Scheduled: {job3.name}")
    print(f"   Runs in: 2 seconds")
    print()

    # 6. Schedule with Retry Config
    print("6. SCHEDULE WITH RETRY:")
    print("-" * 40)

    retry_config = RetryConfig(
        strategy=RetryStrategy.EXPONENTIAL,
        max_retries=3,
        initial_delay=1.0
    )

    job4 = await scheduler.schedule(
        name="Retriable Task",
        handler="process_data",
        args=["data_456"],
        retry_config=retry_config
    )
    print(f"   Scheduled: {job4.name}")
    print(f"   Retry: exponential, max 3 attempts")
    print()

    # 7. Schedule Cron Job
    print("7. SCHEDULE CRON JOB:")
    print("-" * 40)

    cron = CronSchedule(minute="*/5")

    job5 = await scheduler.schedule_cron(
        name="Every 5 Minutes Cleanup",
        handler="cleanup",
        cron=cron
    )
    print(f"   Scheduled: {job5.name}")
    print(f"   Cron: */5 * * * *")
    print(f"   Next run: {datetime.fromtimestamp(job5.scheduled_at)}")
    print()

    # 8. Schedule Interval Job
    print("8. SCHEDULE INTERVAL JOB:")
    print("-" * 40)

    job6 = await scheduler.schedule_interval(
        name="Heartbeat",
        handler="cleanup",
        interval=60.0,
        start_immediately=False
    )
    print(f"   Scheduled: {job6.name}")
    print(f"   Interval: every 60 seconds")
    print()

    # 9. Set Rate Limit
    print("9. SET RATE LIMIT:")
    print("-" * 40)

    scheduler.rate_limiter.set_limit("default", 10, 60.0)
    print("   Queue 'default': max 10 jobs per 60 seconds")
    print()

    # 10. Start Scheduler
    print("10. START SCHEDULER:")
    print("-" * 40)

    await scheduler.start()
    print("   Scheduler started!")

    # Wait for jobs to process
    await asyncio.sleep(0.5)
    print("   Processing jobs...")
    print()

    # 11. Check Job Status
    print("11. CHECK JOB STATUS:")
    print("-" * 40)

    executions = await scheduler.store.get_job_executions(job1.job_id)

    for exec in executions:
        print(f"   Job: {job1.name}")
        print(f"   Status: {exec.status.value}")
        print(f"   Duration: {exec.duration*1000:.1f}ms")

        if exec.result:
            print(f"   Result: {exec.result}")
    print()

    # 12. Worker Status
    print("12. WORKER STATUS:")
    print("-" * 40)

    for worker in scheduler.list_workers():
        print(f"   {worker.name}:")
        print(f"      Status: {worker.status}")
        print(f"      Processed: {worker.processed_count}")
        print(f"      Failed: {worker.failed_count}")
    print()

    # 13. Queue Stats
    print("13. QUEUE STATS:")
    print("-" * 40)

    stats = await scheduler.get_queue_stats("default")
    print(f"   Queue: {stats.name}")
    print(f"      Pending: {stats.pending}")
    print(f"      Running: {stats.running}")
    print(f"      Completed: {stats.completed}")
    print(f"      Failed: {stats.failed}")
    print()

    # 14. Cancel Job
    print("14. CANCEL JOB:")
    print("-" * 40)

    # Schedule and cancel
    cancel_job = await scheduler.schedule(
        name="To Be Cancelled",
        handler="process_data",
        args=["cancel_me"],
        delay=10.0
    )

    cancelled = await scheduler.cancel(cancel_job.job_id)
    print(f"   Scheduled: {cancel_job.name}")
    print(f"   Cancelled: {cancelled}")
    print()

    # 15. Job History
    print("15. JOB HISTORY:")
    print("-" * 40)

    history = await scheduler.get_job_history(job1.job_id)
    print(f"   Job: {job1.name}")
    print(f"   Executions: {len(history)}")

    for exec in history:
        print(f"      - Attempt {exec.attempt}: {exec.status.value}")
    print()

    # 16. Overall Stats
    print("16. OVERALL STATS:")
    print("-" * 40)

    overall = await scheduler.get_stats()
    print(f"   Total jobs: {overall['total_jobs']}")
    print(f"   Queues: {overall['queues']}")
    print(f"   Workers: {overall['workers']}")
    print(f"   Dead letter queue: {overall['dead_letter_queue']}")
    print()

    # Stop scheduler
    await scheduler.stop()

    print("=" * 70)
    print("DEMO COMPLETE - Job Scheduler System Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
