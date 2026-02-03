#!/usr/bin/env python3
"""
BAEL - Job Queue Manager
Advanced job queue management for AI agent operations.

Features:
- Job scheduling
- Priority queues
- Delayed jobs
- Recurring jobs
- Job chaining
- Job groups
- Progress tracking
- Rate limiting
- Job persistence
- Worker management
"""

import asyncio
import heapq
import json
import logging
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Awaitable, Callable, Dict, Generic, List, Optional,
                    Set, Tuple, TypeVar)

logger = logging.getLogger(__name__)


T = TypeVar('T')
R = TypeVar('R')


# =============================================================================
# ENUMS
# =============================================================================

class JobState(Enum):
    """Job execution states."""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class JobPriority(Enum):
    """Job priorities."""
    LOWEST = 1
    LOW = 2
    NORMAL = 3
    HIGH = 4
    HIGHEST = 5
    CRITICAL = 6


class RetryPolicy(Enum):
    """Job retry policies."""
    NONE = "none"
    IMMEDIATE = "immediate"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"


class RecurrenceType(Enum):
    """Job recurrence types."""
    NONE = "none"
    INTERVAL = "interval"
    CRON = "cron"
    FIXED_RATE = "fixed_rate"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class JobConfig:
    """Job configuration."""
    priority: JobPriority = JobPriority.NORMAL
    timeout: float = 300.0  # 5 minutes
    max_retries: int = 3
    retry_policy: RetryPolicy = RetryPolicy.EXPONENTIAL
    retry_delay: float = 1.0
    retry_max_delay: float = 60.0


@dataclass
class RecurrenceConfig:
    """Recurrence configuration."""
    recurrence_type: RecurrenceType = RecurrenceType.NONE
    interval_seconds: float = 60.0
    max_occurrences: Optional[int] = None
    end_at: Optional[datetime] = None


@dataclass
class JobResult(Generic[T]):
    """Job execution result."""
    job_id: str
    success: bool
    result: Optional[T] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    attempt: int = 1
    completed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class JobProgress:
    """Job progress information."""
    job_id: str
    state: JobState
    progress_percent: float = 0.0
    current_step: str = ""
    steps_completed: int = 0
    total_steps: int = 1
    started_at: Optional[datetime] = None
    estimated_remaining_ms: Optional[float] = None


@dataclass
class JobInfo:
    """Job information."""
    job_id: str
    name: str
    state: JobState
    priority: JobPriority
    created_at: datetime
    scheduled_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    attempt: int
    progress: float


@dataclass
class QueueStats:
    """Queue statistics."""
    total_jobs: int = 0
    pending_jobs: int = 0
    running_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    cancelled_jobs: int = 0
    avg_execution_time_ms: float = 0.0
    avg_wait_time_ms: float = 0.0


# =============================================================================
# JOB CLASS
# =============================================================================

class Job(Generic[T]):
    """
    A job to be executed.
    """

    def __init__(
        self,
        name: str,
        handler: Callable[['Job'], Awaitable[T]],
        args: Optional[Dict[str, Any]] = None,
        config: Optional[JobConfig] = None,
        recurrence: Optional[RecurrenceConfig] = None,
        job_id: Optional[str] = None
    ):
        self.job_id = job_id or str(uuid.uuid4())
        self.name = name
        self.handler = handler
        self.args = args or {}
        self.config = config or JobConfig()
        self.recurrence = recurrence or RecurrenceConfig()

        self.state = JobState.PENDING
        self.created_at = datetime.utcnow()
        self.scheduled_at: Optional[datetime] = None
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

        self.attempt = 0
        self.result: Optional[T] = None
        self.error: Optional[str] = None

        self._progress = JobProgress(job_id=self.job_id, state=self.state)
        self._cancel_event = asyncio.Event()
        self._lock = threading.RLock()

        # Chain and group
        self.next_job: Optional['Job'] = None
        self.group_id: Optional[str] = None
        self.occurrence_count = 0

    @property
    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def cancel(self) -> None:
        """Cancel the job."""
        self._cancel_event.set()
        with self._lock:
            self.state = JobState.CANCELLED

    def check_cancelled(self) -> None:
        """Check if cancelled and raise."""
        if self.is_cancelled:
            raise JobCancelledError(f"Job {self.job_id} was cancelled")

    def report_progress(
        self,
        percent: float,
        step: str = "",
        steps_completed: int = 0,
        total_steps: int = 1
    ) -> None:
        """Report job progress."""
        with self._lock:
            self._progress.progress_percent = percent
            self._progress.current_step = step
            self._progress.steps_completed = steps_completed
            self._progress.total_steps = total_steps

    def get_progress(self) -> JobProgress:
        """Get current progress."""
        with self._lock:
            return JobProgress(
                job_id=self.job_id,
                state=self.state,
                progress_percent=self._progress.progress_percent,
                current_step=self._progress.current_step,
                steps_completed=self._progress.steps_completed,
                total_steps=self._progress.total_steps,
                started_at=self.started_at
            )

    def get_info(self) -> JobInfo:
        """Get job information."""
        with self._lock:
            return JobInfo(
                job_id=self.job_id,
                name=self.name,
                state=self.state,
                priority=self.config.priority,
                created_at=self.created_at,
                scheduled_at=self.scheduled_at,
                started_at=self.started_at,
                completed_at=self.completed_at,
                attempt=self.attempt,
                progress=self._progress.progress_percent
            )

    def then(self, next_job: 'Job') -> 'Job':
        """Chain another job to run after this one."""
        self.next_job = next_job
        return next_job


# =============================================================================
# JOB STORE
# =============================================================================

class JobStore(ABC):
    """Abstract job store."""

    @abstractmethod
    async def save(self, job: Job) -> bool:
        pass

    @abstractmethod
    async def get(self, job_id: str) -> Optional[Job]:
        pass

    @abstractmethod
    async def delete(self, job_id: str) -> bool:
        pass

    @abstractmethod
    async def get_by_state(self, state: JobState) -> List[Job]:
        pass


class InMemoryJobStore(JobStore):
    """In-memory job store."""

    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.RLock()

    async def save(self, job: Job) -> bool:
        with self._lock:
            self._jobs[job.job_id] = job
            return True

    async def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    async def delete(self, job_id: str) -> bool:
        with self._lock:
            return self._jobs.pop(job_id, None) is not None

    async def get_by_state(self, state: JobState) -> List[Job]:
        with self._lock:
            return [j for j in self._jobs.values() if j.state == state]


# =============================================================================
# PRIORITY QUEUE
# =============================================================================

class PriorityJobQueue:
    """Priority-based job queue."""

    def __init__(self, max_size: int = 10000):
        self._queue: List[Tuple[int, datetime, float, Job]] = []
        self._max_size = max_size
        self._lock = threading.RLock()
        self._counter = 0

    def push(self, job: Job, scheduled_at: Optional[datetime] = None) -> bool:
        """Push a job onto the queue."""
        with self._lock:
            if len(self._queue) >= self._max_size:
                return False

            schedule_time = scheduled_at or datetime.utcnow()
            priority = -job.config.priority.value
            self._counter += 1

            heapq.heappush(
                self._queue,
                (schedule_time.timestamp(), priority, self._counter, job)
            )

            job.state = JobState.SCHEDULED
            job.scheduled_at = schedule_time
            return True

    def pop(self) -> Optional[Job]:
        """Pop the next job to execute."""
        now = datetime.utcnow().timestamp()

        with self._lock:
            while self._queue:
                scheduled_ts, _, _, job = self._queue[0]

                if scheduled_ts <= now:
                    heapq.heappop(self._queue)
                    if job.state != JobState.CANCELLED:
                        job.state = JobState.QUEUED
                        return job
                else:
                    break

        return None

    def peek(self) -> Optional[Job]:
        """Peek at the next job."""
        with self._lock:
            if self._queue:
                return self._queue[0][3]
        return None

    def time_until_next(self) -> Optional[float]:
        """Time until next job is ready."""
        with self._lock:
            if not self._queue:
                return None

            scheduled_ts = self._queue[0][0]
            now = datetime.utcnow().timestamp()
            return max(0, scheduled_ts - now)

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._queue)

    @property
    def is_empty(self) -> bool:
        with self._lock:
            return len(self._queue) == 0


# =============================================================================
# WORKER
# =============================================================================

class Worker:
    """Job worker."""

    def __init__(
        self,
        worker_id: str,
        queue: 'JobQueue'
    ):
        self.worker_id = worker_id
        self.queue = queue
        self.current_job: Optional[Job] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the worker."""
        self._running = True
        self._task = asyncio.create_task(self._work_loop())
        logger.info(f"Worker {self.worker_id} started")

    async def stop(self) -> None:
        """Stop the worker."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info(f"Worker {self.worker_id} stopped")

    async def _work_loop(self) -> None:
        """Main work loop."""
        while self._running:
            job = self.queue._get_next_job()

            if not job:
                wait_time = self.queue._queue.time_until_next()
                if wait_time:
                    await asyncio.sleep(min(wait_time, 0.1))
                else:
                    await asyncio.sleep(0.01)
                continue

            self.current_job = job
            await self.queue._execute_job(job)
            self.current_job = None


# =============================================================================
# EXCEPTIONS
# =============================================================================

class JobError(Exception):
    """Base job error."""
    pass


class JobCancelledError(JobError):
    """Job was cancelled."""
    pass


class JobTimeoutError(JobError):
    """Job timed out."""
    pass


class JobRetryExhaustedError(JobError):
    """Job retries exhausted."""
    pass


# =============================================================================
# JOB QUEUE
# =============================================================================

class JobQueue:
    """
    Job Queue Manager for BAEL.

    Advanced job scheduling and execution.
    """

    def __init__(
        self,
        num_workers: int = 4,
        max_queue_size: int = 10000
    ):
        self._num_workers = num_workers
        self._queue = PriorityJobQueue(max_size=max_queue_size)
        self._store = InMemoryJobStore()
        self._workers: List[Worker] = []
        self._running_jobs: Dict[str, Job] = {}
        self._job_results: Dict[str, JobResult] = {}
        self._callbacks: Dict[str, List[Callable[[JobResult], None]]] = defaultdict(list)
        self._groups: Dict[str, List[str]] = defaultdict(list)
        self._stats = QueueStats()
        self._lock = threading.RLock()
        self._running = False

    # -------------------------------------------------------------------------
    # JOB SUBMISSION
    # -------------------------------------------------------------------------

    async def submit(
        self,
        name: str,
        handler: Callable[[Job], Awaitable[T]],
        args: Optional[Dict[str, Any]] = None,
        config: Optional[JobConfig] = None,
        delay: Optional[float] = None,
        scheduled_at: Optional[datetime] = None
    ) -> str:
        """Submit a job for execution."""
        job = Job(
            name=name,
            handler=handler,
            args=args,
            config=config
        )

        await self._store.save(job)

        # Calculate schedule time
        if scheduled_at:
            schedule_time = scheduled_at
        elif delay:
            schedule_time = datetime.utcnow() + timedelta(seconds=delay)
        else:
            schedule_time = datetime.utcnow()

        self._queue.push(job, schedule_time)

        with self._lock:
            self._stats.total_jobs += 1
            self._stats.pending_jobs += 1

        logger.debug(f"Job submitted: {job.job_id} ({name})")
        return job.job_id

    async def submit_recurring(
        self,
        name: str,
        handler: Callable[[Job], Awaitable[T]],
        interval: float,
        args: Optional[Dict[str, Any]] = None,
        config: Optional[JobConfig] = None,
        max_occurrences: Optional[int] = None
    ) -> str:
        """Submit a recurring job."""
        recurrence = RecurrenceConfig(
            recurrence_type=RecurrenceType.INTERVAL,
            interval_seconds=interval,
            max_occurrences=max_occurrences
        )

        job = Job(
            name=name,
            handler=handler,
            args=args,
            config=config,
            recurrence=recurrence
        )

        await self._store.save(job)
        self._queue.push(job)

        with self._lock:
            self._stats.total_jobs += 1
            self._stats.pending_jobs += 1

        logger.info(f"Recurring job submitted: {job.job_id} (every {interval}s)")
        return job.job_id

    # -------------------------------------------------------------------------
    # JOB GROUPS
    # -------------------------------------------------------------------------

    async def submit_group(
        self,
        group_name: str,
        jobs: List[Tuple[str, Callable[[Job], Awaitable[Any]], Dict[str, Any]]]
    ) -> str:
        """Submit a group of jobs."""
        group_id = str(uuid.uuid4())

        for name, handler, args in jobs:
            job = Job(name=name, handler=handler, args=args)
            job.group_id = group_id

            await self._store.save(job)
            self._queue.push(job)

            with self._lock:
                self._groups[group_id].append(job.job_id)
                self._stats.total_jobs += 1
                self._stats.pending_jobs += 1

        logger.info(f"Job group submitted: {group_id} ({len(jobs)} jobs)")
        return group_id

    async def get_group_status(self, group_id: str) -> Dict[str, int]:
        """Get status of a job group."""
        with self._lock:
            job_ids = self._groups.get(group_id, [])

        status: Dict[str, int] = defaultdict(int)

        for job_id in job_ids:
            job = await self._store.get(job_id)
            if job:
                status[job.state.value] += 1

        return dict(status)

    # -------------------------------------------------------------------------
    # JOB EXECUTION
    # -------------------------------------------------------------------------

    async def _execute_job(self, job: Job[T]) -> JobResult[T]:
        """Execute a job."""
        job.state = JobState.RUNNING
        job.started_at = datetime.utcnow()
        job.attempt += 1

        with self._lock:
            self._running_jobs[job.job_id] = job
            self._stats.pending_jobs -= 1
            self._stats.running_jobs += 1

        start_time = time.time()

        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                job.handler(job),
                timeout=job.config.timeout
            )

            job.result = result
            job.state = JobState.COMPLETED
            job.completed_at = datetime.utcnow()

            execution_time = (time.time() - start_time) * 1000

            job_result = JobResult(
                job_id=job.job_id,
                success=True,
                result=result,
                execution_time_ms=execution_time,
                attempt=job.attempt
            )

            self._on_job_complete(job, job_result)

            return job_result

        except asyncio.TimeoutError:
            return await self._handle_job_failure(
                job,
                JobTimeoutError(f"Job {job.job_id} timed out"),
                start_time
            )

        except JobCancelledError as e:
            job.state = JobState.CANCELLED
            job.error = str(e)

            with self._lock:
                self._stats.cancelled_jobs += 1
                self._stats.running_jobs -= 1
                self._running_jobs.pop(job.job_id, None)

            return JobResult(
                job_id=job.job_id,
                success=False,
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000
            )

        except Exception as e:
            return await self._handle_job_failure(job, e, start_time)

    async def _handle_job_failure(
        self,
        job: Job,
        error: Exception,
        start_time: float
    ) -> JobResult:
        """Handle job failure with retry logic."""
        job.error = str(error)

        # Check if should retry
        if (
            job.config.retry_policy != RetryPolicy.NONE and
            job.attempt < job.config.max_retries
        ):
            delay = self._calculate_retry_delay(job)

            logger.debug(f"Job {job.job_id} retry {job.attempt}, delay {delay}s")

            with self._lock:
                self._running_jobs.pop(job.job_id, None)
                self._stats.running_jobs -= 1
                self._stats.pending_jobs += 1

            # Reschedule
            schedule_time = datetime.utcnow() + timedelta(seconds=delay)
            job.state = JobState.SCHEDULED
            self._queue.push(job, schedule_time)

            return JobResult(
                job_id=job.job_id,
                success=False,
                error=str(error),
                execution_time_ms=(time.time() - start_time) * 1000,
                attempt=job.attempt
            )

        # Job failed permanently
        job.state = JobState.FAILED
        job.completed_at = datetime.utcnow()

        execution_time = (time.time() - start_time) * 1000

        job_result = JobResult(
            job_id=job.job_id,
            success=False,
            error=str(error),
            execution_time_ms=execution_time,
            attempt=job.attempt
        )

        with self._lock:
            self._running_jobs.pop(job.job_id, None)
            self._stats.running_jobs -= 1
            self._stats.failed_jobs += 1
            self._job_results[job.job_id] = job_result

        self._trigger_callbacks(job.job_id, job_result)

        return job_result

    def _calculate_retry_delay(self, job: Job) -> float:
        """Calculate retry delay."""
        base = job.config.retry_delay

        if job.config.retry_policy == RetryPolicy.IMMEDIATE:
            return 0
        elif job.config.retry_policy == RetryPolicy.LINEAR:
            return min(base * job.attempt, job.config.retry_max_delay)
        elif job.config.retry_policy == RetryPolicy.EXPONENTIAL:
            return min(base * (2 ** (job.attempt - 1)), job.config.retry_max_delay)

        return base

    def _on_job_complete(self, job: Job, result: JobResult) -> None:
        """Handle job completion."""
        with self._lock:
            self._running_jobs.pop(job.job_id, None)
            self._stats.running_jobs -= 1
            self._stats.completed_jobs += 1
            self._job_results[job.job_id] = result

        self._trigger_callbacks(job.job_id, result)

        # Handle chained job
        if job.next_job:
            asyncio.create_task(self._schedule_chained_job(job))

        # Handle recurring job
        if job.recurrence.recurrence_type != RecurrenceType.NONE:
            asyncio.create_task(self._schedule_recurring_job(job))

    async def _schedule_chained_job(self, job: Job) -> None:
        """Schedule the next job in a chain."""
        if job.next_job:
            self._queue.push(job.next_job)
            with self._lock:
                self._stats.pending_jobs += 1

    async def _schedule_recurring_job(self, job: Job) -> None:
        """Schedule the next occurrence of a recurring job."""
        job.occurrence_count += 1

        # Check max occurrences
        if (
            job.recurrence.max_occurrences and
            job.occurrence_count >= job.recurrence.max_occurrences
        ):
            return

        # Check end time
        if job.recurrence.end_at and datetime.utcnow() >= job.recurrence.end_at:
            return

        # Create new job for next occurrence
        new_job = Job(
            name=job.name,
            handler=job.handler,
            args=job.args,
            config=job.config,
            recurrence=job.recurrence
        )
        new_job.occurrence_count = job.occurrence_count

        schedule_time = datetime.utcnow() + timedelta(
            seconds=job.recurrence.interval_seconds
        )

        await self._store.save(new_job)
        self._queue.push(new_job, schedule_time)

        with self._lock:
            self._stats.total_jobs += 1
            self._stats.pending_jobs += 1

    # -------------------------------------------------------------------------
    # JOB MANAGEMENT
    # -------------------------------------------------------------------------

    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID."""
        return await self._store.get(job_id)

    async def get_result(self, job_id: str) -> Optional[JobResult]:
        """Get job result."""
        with self._lock:
            return self._job_results.get(job_id)

    def get_progress(self, job_id: str) -> Optional[JobProgress]:
        """Get job progress."""
        with self._lock:
            job = self._running_jobs.get(job_id)
            if job:
                return job.get_progress()
        return None

    async def cancel(self, job_id: str) -> bool:
        """Cancel a job."""
        job = await self._store.get(job_id)
        if job:
            job.cancel()
            with self._lock:
                if job.state == JobState.RUNNING:
                    self._stats.running_jobs -= 1
                elif job.state in (JobState.PENDING, JobState.SCHEDULED, JobState.QUEUED):
                    self._stats.pending_jobs -= 1
                self._stats.cancelled_jobs += 1
            return True
        return False

    async def pause(self, job_id: str) -> bool:
        """Pause a job."""
        job = await self._store.get(job_id)
        if job and job.state in (JobState.PENDING, JobState.SCHEDULED):
            job.state = JobState.PAUSED
            return True
        return False

    async def resume(self, job_id: str) -> bool:
        """Resume a paused job."""
        job = await self._store.get(job_id)
        if job and job.state == JobState.PAUSED:
            job.state = JobState.SCHEDULED
            self._queue.push(job)
            return True
        return False

    # -------------------------------------------------------------------------
    # CALLBACKS
    # -------------------------------------------------------------------------

    def on_complete(
        self,
        job_id: str,
        callback: Callable[[JobResult], None]
    ) -> None:
        """Register a completion callback."""
        with self._lock:
            if job_id in self._job_results:
                callback(self._job_results[job_id])
            else:
                self._callbacks[job_id].append(callback)

    def _trigger_callbacks(self, job_id: str, result: JobResult) -> None:
        """Trigger callbacks for a job."""
        with self._lock:
            callbacks = self._callbacks.pop(job_id, [])

        for callback in callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    # -------------------------------------------------------------------------
    # QUEUE OPERATIONS
    # -------------------------------------------------------------------------

    def _get_next_job(self) -> Optional[Job]:
        """Get the next job to execute."""
        return self._queue.pop()

    # -------------------------------------------------------------------------
    # LIFECYCLE
    # -------------------------------------------------------------------------

    async def start(self) -> None:
        """Start the job queue."""
        if self._running:
            return

        self._running = True

        # Start workers
        for i in range(self._num_workers):
            worker = Worker(f"worker-{i}", self)
            self._workers.append(worker)
            await worker.start()

        logger.info(f"Job Queue started with {self._num_workers} workers")

    async def stop(self, wait: bool = True) -> None:
        """Stop the job queue."""
        self._running = False

        # Stop workers
        for worker in self._workers:
            await worker.stop()

        self._workers.clear()

        logger.info("Job Queue stopped")

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> QueueStats:
        """Get queue statistics."""
        with self._lock:
            return QueueStats(
                total_jobs=self._stats.total_jobs,
                pending_jobs=self._stats.pending_jobs,
                running_jobs=self._stats.running_jobs,
                completed_jobs=self._stats.completed_jobs,
                failed_jobs=self._stats.failed_jobs,
                cancelled_jobs=self._stats.cancelled_jobs
            )

    @property
    def queue_size(self) -> int:
        return self._queue.size

    @property
    def running_count(self) -> int:
        with self._lock:
            return len(self._running_jobs)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Job Queue Manager."""
    print("=" * 70)
    print("BAEL - JOB QUEUE DEMO")
    print("Advanced Job Scheduling for AI Agents")
    print("=" * 70)
    print()

    queue = JobQueue(num_workers=2)
    await queue.start()

    # 1. Basic Job Submission
    print("1. BASIC JOB SUBMISSION:")
    print("-" * 40)

    async def simple_job(job: Job) -> str:
        await asyncio.sleep(0.1)
        return f"Hello from {job.name}!"

    job_id = await queue.submit("greeting", simple_job)
    print(f"   Submitted job: {job_id[:8]}...")

    await asyncio.sleep(0.2)

    result = await queue.get_result(job_id)
    if result:
        print(f"   Result: {result.result}")
        print(f"   Success: {result.success}")
    print()

    # 2. Job with Arguments
    print("2. JOB WITH ARGUMENTS:")
    print("-" * 40)

    async def calculate_job(job: Job) -> int:
        a = job.args.get("a", 0)
        b = job.args.get("b", 0)
        return a + b

    job_id = await queue.submit(
        "calculator",
        calculate_job,
        args={"a": 10, "b": 32}
    )

    await asyncio.sleep(0.2)

    result = await queue.get_result(job_id)
    if result:
        print(f"   10 + 32 = {result.result}")
    print()

    # 3. Priority Jobs
    print("3. PRIORITY JOBS:")
    print("-" * 40)

    results_order = []

    async def priority_job(job: Job) -> None:
        results_order.append(job.args["order"])
        await asyncio.sleep(0.05)

    # Submit in reverse order
    await queue.submit("job3", priority_job, {"order": 3}, JobConfig(priority=JobPriority.LOW))
    await queue.submit("job1", priority_job, {"order": 1}, JobConfig(priority=JobPriority.HIGHEST))
    await queue.submit("job2", priority_job, {"order": 2}, JobConfig(priority=JobPriority.NORMAL))

    await asyncio.sleep(0.5)

    print(f"   Execution order (by priority): {results_order}")
    print()

    # 4. Delayed Jobs
    print("4. DELAYED JOBS:")
    print("-" * 40)

    async def delayed_job(job: Job) -> str:
        return f"Executed at {datetime.utcnow().strftime('%H:%M:%S.%f')[:12]}"

    start = datetime.utcnow()
    job_id = await queue.submit("delayed", delayed_job, delay=0.5)
    print(f"   Submitted at: {start.strftime('%H:%M:%S.%f')[:12]}")

    await asyncio.sleep(0.7)

    result = await queue.get_result(job_id)
    if result:
        print(f"   {result.result}")
    print()

    # 5. Retry Logic
    print("5. RETRY LOGIC:")
    print("-" * 40)

    attempt_count = {"count": 0}

    async def flaky_job(job: Job) -> str:
        attempt_count["count"] += 1
        if attempt_count["count"] < 3:
            raise ValueError(f"Attempt {attempt_count['count']} failed")
        return "Success!"

    config = JobConfig(
        retry_policy=RetryPolicy.IMMEDIATE,
        max_retries=5
    )

    job_id = await queue.submit("flaky", flaky_job, config=config)

    await asyncio.sleep(1.0)

    result = await queue.get_result(job_id)
    print(f"   Total attempts: {attempt_count['count']}")
    if result:
        print(f"   Final result: {result.result}")
    print()

    # 6. Job Progress
    print("6. JOB PROGRESS:")
    print("-" * 40)

    async def progress_job(job: Job) -> str:
        for i in range(5):
            job.report_progress(
                percent=(i + 1) * 20,
                step=f"Step {i + 1}",
                steps_completed=i + 1,
                total_steps=5
            )
            await asyncio.sleep(0.1)
        return "Done!"

    job_id = await queue.submit("progressive", progress_job)

    for _ in range(3):
        await asyncio.sleep(0.15)
        progress = queue.get_progress(job_id)
        if progress:
            print(f"   Progress: {progress.progress_percent}% - {progress.current_step}")

    await asyncio.sleep(0.5)
    print()

    # 7. Job Groups
    print("7. JOB GROUPS:")
    print("-" * 40)

    async def group_job(job: Job) -> int:
        await asyncio.sleep(0.1)
        return job.args["value"] * 2

    group_id = await queue.submit_group("calculations", [
        ("calc1", group_job, {"value": 1}),
        ("calc2", group_job, {"value": 2}),
        ("calc3", group_job, {"value": 3}),
    ])

    await asyncio.sleep(0.5)

    status = await queue.get_group_status(group_id)
    print(f"   Group ID: {group_id[:8]}...")
    print(f"   Status: {dict(status)}")
    print()

    # 8. Recurring Jobs
    print("8. RECURRING JOBS:")
    print("-" * 40)

    recurring_count = {"count": 0}

    async def recurring_job(job: Job) -> None:
        recurring_count["count"] += 1

    job_id = await queue.submit_recurring(
        "heartbeat",
        recurring_job,
        interval=0.2,
        max_occurrences=3
    )

    print(f"   Recurring job: {job_id[:8]}...")

    await asyncio.sleep(0.8)

    print(f"   Executions: {recurring_count['count']}")
    print()

    # 9. Job Cancellation
    print("9. JOB CANCELLATION:")
    print("-" * 40)

    async def long_job(job: Job) -> str:
        for _ in range(100):
            job.check_cancelled()
            await asyncio.sleep(0.1)
        return "Done"

    job_id = await queue.submit("long_task", long_job)
    await asyncio.sleep(0.2)

    cancelled = await queue.cancel(job_id)
    print(f"   Job cancelled: {cancelled}")
    print()

    # 10. Statistics
    print("10. QUEUE STATISTICS:")
    print("-" * 40)

    stats = queue.get_stats()
    print(f"   Total jobs: {stats.total_jobs}")
    print(f"   Pending: {stats.pending_jobs}")
    print(f"   Running: {stats.running_jobs}")
    print(f"   Completed: {stats.completed_jobs}")
    print(f"   Failed: {stats.failed_jobs}")
    print(f"   Cancelled: {stats.cancelled_jobs}")
    print()

    # 11. Job Callbacks
    print("11. JOB CALLBACKS:")
    print("-" * 40)

    callback_received = {"result": None}

    def on_complete(result: JobResult):
        callback_received["result"] = result

    job_id = await queue.submit("callback_job", simple_job)
    queue.on_complete(job_id, on_complete)

    await asyncio.sleep(0.3)

    if callback_received["result"]:
        print(f"   Callback received: {callback_received['result'].success}")
    print()

    # Shutdown
    await queue.stop()

    print("=" * 70)
    print("DEMO COMPLETE - Job Queue Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
