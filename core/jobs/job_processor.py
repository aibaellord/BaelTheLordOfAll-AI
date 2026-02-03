#!/usr/bin/env python3
"""
BAEL - Background Job Processor
Comprehensive job scheduling and processing system.

This module provides a complete background job framework
for asynchronous task processing.

Features:
- Job queues (priority, delayed, scheduled)
- Worker pools
- Job persistence
- Retry logic
- Progress tracking
- Job dependencies
- Cron-style scheduling
- Dead letter queues
- Job batching
- Metrics and monitoring
"""

import asyncio
import functools
import hashlib
import heapq
import json
import logging
import os
import pickle
import random
import time
import traceback
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import (Any, Callable, Coroutine, Dict, Generic, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

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
    RETRYING = "retrying"
    CANCELLED = "cancelled"
    DEAD = "dead"


class JobPriority(Enum):
    """Job priority levels."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class QueueType(Enum):
    """Queue types."""
    IMMEDIATE = "immediate"
    DELAYED = "delayed"
    SCHEDULED = "scheduled"
    BATCH = "batch"


class WorkerState(Enum):
    """Worker states."""
    IDLE = "idle"
    BUSY = "busy"
    STOPPING = "stopping"
    STOPPED = "stopped"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class JobConfig:
    """Job configuration."""
    max_retries: int = 3
    retry_delay: float = 60.0  # seconds
    timeout: float = 300.0  # 5 minutes
    priority: JobPriority = JobPriority.NORMAL

    # Scheduling
    delay: Optional[float] = None  # Initial delay
    schedule: Optional[str] = None  # Cron expression

    # Dependencies
    depends_on: List[str] = field(default_factory=list)

    # Options
    unique: bool = False  # Prevent duplicate jobs
    persist: bool = True  # Persist to storage
    dead_letter: bool = True  # Move to DLQ on final failure


@dataclass
class JobResult:
    """Result of job execution."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    duration: float = 0.0


@dataclass
class Job:
    """Job definition."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    handler: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    config: JobConfig = field(default_factory=JobConfig)

    # State
    status: JobStatus = JobStatus.PENDING
    attempts: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Progress
    progress: float = 0.0
    progress_message: str = ""

    # Results
    result: Optional[JobResult] = None
    error_history: List[str] = field(default_factory=list)

    def __lt__(self, other: 'Job') -> bool:
        """Priority comparison for heap."""
        return self.config.priority.value < other.config.priority.value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "handler": self.handler,
            "payload": self.payload,
            "status": self.status.value,
            "attempts": self.attempts,
            "priority": self.config.priority.value,
            "created_at": self.created_at.isoformat(),
            "progress": self.progress
        }


@dataclass
class ScheduledJob:
    """Scheduled recurring job."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    handler: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    schedule: str = ""  # Cron expression
    config: JobConfig = field(default_factory=JobConfig)

    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0


@dataclass
class WorkerStats:
    """Worker statistics."""
    jobs_processed: int = 0
    jobs_failed: int = 0
    total_duration: float = 0.0
    current_job: Optional[str] = None


# =============================================================================
# CRON PARSER (Simple Implementation)
# =============================================================================

class CronParser:
    """
    Simple cron expression parser.

    Supports: minute hour day_of_month month day_of_week
    Special characters: * (any), */n (every n), n-m (range), n,m (list)
    """

    FIELDS = ['minute', 'hour', 'day', 'month', 'weekday']
    RANGES = {
        'minute': (0, 59),
        'hour': (0, 23),
        'day': (1, 31),
        'month': (1, 12),
        'weekday': (0, 6)
    }

    @classmethod
    def parse_field(cls, field: str, name: str) -> Set[int]:
        """Parse a single cron field."""
        min_val, max_val = cls.RANGES[name]

        if field == '*':
            return set(range(min_val, max_val + 1))

        if field.startswith('*/'):
            step = int(field[2:])
            return set(range(min_val, max_val + 1, step))

        if '-' in field:
            start, end = map(int, field.split('-'))
            return set(range(start, end + 1))

        if ',' in field:
            return set(map(int, field.split(',')))

        return {int(field)}

    @classmethod
    def parse(cls, expression: str) -> Dict[str, Set[int]]:
        """Parse cron expression."""
        parts = expression.split()

        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {expression}")

        return {
            name: cls.parse_field(parts[i], name)
            for i, name in enumerate(cls.FIELDS)
        }

    @classmethod
    def next_run(cls, expression: str, from_time: datetime = None) -> datetime:
        """Calculate next run time."""
        schedule = cls.parse(expression)
        now = from_time or datetime.now()

        # Start from next minute
        current = now.replace(second=0, microsecond=0) + timedelta(minutes=1)

        for _ in range(366 * 24 * 60):  # Max 1 year search
            if (current.minute in schedule['minute'] and
                current.hour in schedule['hour'] and
                current.day in schedule['day'] and
                current.month in schedule['month'] and
                current.weekday() in schedule['weekday']):
                return current

            current += timedelta(minutes=1)

        raise ValueError("Could not find next run time")


# =============================================================================
# JOB HANDLERS
# =============================================================================

class JobHandler(ABC):
    """Abstract job handler."""

    @abstractmethod
    async def execute(
        self,
        job: Job,
        context: 'JobContext'
    ) -> JobResult:
        """Execute the job."""
        pass


class FunctionHandler(JobHandler):
    """Handler for function-based jobs."""

    def __init__(self, func: Callable):
        self.func = func

    async def execute(
        self,
        job: Job,
        context: 'JobContext'
    ) -> JobResult:
        start = time.time()

        try:
            if asyncio.iscoroutinefunction(self.func):
                result = await self.func(job.payload, context)
            else:
                result = self.func(job.payload, context)

            return JobResult(
                success=True,
                data=result,
                duration=time.time() - start
            )
        except Exception as e:
            return JobResult(
                success=False,
                error=str(e),
                duration=time.time() - start
            )


# =============================================================================
# JOB CONTEXT
# =============================================================================

class JobContext:
    """Context provided to job handlers."""

    def __init__(self, job: Job, processor: 'JobProcessor'):
        self.job = job
        self._processor = processor
        self._cancelled = False

    @property
    def job_id(self) -> str:
        return self.job.id

    @property
    def attempt(self) -> int:
        return self.job.attempts

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    def update_progress(self, progress: float, message: str = "") -> None:
        """Update job progress."""
        self.job.progress = min(100, max(0, progress))
        self.job.progress_message = message

    async def enqueue(
        self,
        handler: str,
        payload: Dict[str, Any],
        **kwargs
    ) -> str:
        """Enqueue a child job."""
        return await self._processor.enqueue(
            handler,
            payload,
            **kwargs
        )

    def cancel(self) -> None:
        """Mark job as cancelled."""
        self._cancelled = True


# =============================================================================
# JOB QUEUES
# =============================================================================

class JobQueue(ABC):
    """Abstract job queue."""

    @abstractmethod
    async def enqueue(self, job: Job) -> None:
        """Add job to queue."""
        pass

    @abstractmethod
    async def dequeue(self) -> Optional[Job]:
        """Get next job from queue."""
        pass

    @abstractmethod
    async def size(self) -> int:
        """Get queue size."""
        pass


class MemoryQueue(JobQueue):
    """In-memory job queue with priority support."""

    def __init__(self):
        self._queue: List[Tuple[int, float, Job]] = []
        self._lock = asyncio.Lock()
        self._counter = 0

    async def enqueue(self, job: Job) -> None:
        async with self._lock:
            # Priority, counter for FIFO within priority, job
            heapq.heappush(
                self._queue,
                (job.config.priority.value, self._counter, job)
            )
            self._counter += 1

    async def dequeue(self) -> Optional[Job]:
        async with self._lock:
            if self._queue:
                _, _, job = heapq.heappop(self._queue)
                return job
            return None

    async def size(self) -> int:
        return len(self._queue)


class DelayedQueue(JobQueue):
    """Queue for delayed jobs."""

    def __init__(self):
        self._jobs: List[Tuple[float, Job]] = []  # (run_time, job)
        self._lock = asyncio.Lock()

    async def enqueue(self, job: Job) -> None:
        delay = job.config.delay or 0
        run_time = time.time() + delay

        async with self._lock:
            heapq.heappush(self._jobs, (run_time, job))

    async def dequeue(self) -> Optional[Job]:
        async with self._lock:
            now = time.time()

            if self._jobs and self._jobs[0][0] <= now:
                _, job = heapq.heappop(self._jobs)
                return job

            return None

    async def size(self) -> int:
        return len(self._jobs)

    async def next_ready_time(self) -> Optional[float]:
        """Time until next job is ready."""
        if self._jobs:
            return max(0, self._jobs[0][0] - time.time())
        return None


class DeadLetterQueue:
    """Queue for failed jobs."""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._jobs: deque = deque(maxlen=max_size)
        self._lock = asyncio.Lock()

    async def add(self, job: Job) -> None:
        async with self._lock:
            job.status = JobStatus.DEAD
            self._jobs.append(job)

    async def get_all(self) -> List[Job]:
        async with self._lock:
            return list(self._jobs)

    async def retry(self, job_id: str) -> Optional[Job]:
        """Remove job from DLQ for retry."""
        async with self._lock:
            for i, job in enumerate(self._jobs):
                if job.id == job_id:
                    del self._jobs[i]
                    job.status = JobStatus.PENDING
                    job.attempts = 0
                    return job
            return None

    async def size(self) -> int:
        return len(self._jobs)


# =============================================================================
# WORKERS
# =============================================================================

class Worker:
    """Job processing worker."""

    def __init__(
        self,
        worker_id: str,
        processor: 'JobProcessor'
    ):
        self.id = worker_id
        self.processor = processor
        self.state = WorkerState.IDLE
        self.stats = WorkerStats()

        self._task: Optional[asyncio.Task] = None
        self._current_job: Optional[Job] = None

    async def start(self) -> None:
        """Start the worker."""
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        """Stop the worker."""
        self.state = WorkerState.STOPPING
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.state = WorkerState.STOPPED

    async def _run(self) -> None:
        """Main worker loop."""
        while self.state != WorkerState.STOPPING:
            try:
                job = await self.processor._get_next_job()

                if job:
                    await self._process_job(job)
                else:
                    await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {self.id} error: {e}")
                await asyncio.sleep(1)

    async def _process_job(self, job: Job) -> None:
        """Process a single job."""
        self.state = WorkerState.BUSY
        self._current_job = job
        self.stats.current_job = job.id

        try:
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now()
            job.attempts += 1

            # Get handler
            handler = self.processor.handlers.get(job.handler)
            if not handler:
                raise RuntimeError(f"Unknown handler: {job.handler}")

            # Create context
            context = JobContext(job, self.processor)

            # Execute with timeout
            try:
                if job.config.timeout:
                    result = await asyncio.wait_for(
                        handler.execute(job, context),
                        timeout=job.config.timeout
                    )
                else:
                    result = await handler.execute(job, context)
            except asyncio.TimeoutError:
                result = JobResult(
                    success=False,
                    error="Job timeout exceeded"
                )

            job.result = result

            if result.success:
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.now()
                self.stats.jobs_processed += 1
            else:
                job.error_history.append(result.error or "Unknown error")

                if job.attempts < job.config.max_retries:
                    job.status = JobStatus.RETRYING
                    await self._schedule_retry(job)
                else:
                    job.status = JobStatus.FAILED
                    self.stats.jobs_failed += 1

                    if job.config.dead_letter:
                        await self.processor.dlq.add(job)

            self.stats.total_duration += result.duration

        except Exception as e:
            logger.error(f"Job {job.id} error: {e}")
            job.status = JobStatus.FAILED
            job.error_history.append(str(e))
            self.stats.jobs_failed += 1

        finally:
            self.state = WorkerState.IDLE
            self._current_job = None
            self.stats.current_job = None

            # Notify completion
            await self.processor._job_completed(job)

    async def _schedule_retry(self, job: Job) -> None:
        """Schedule job for retry."""
        # Exponential backoff
        delay = job.config.retry_delay * (2 ** (job.attempts - 1))
        job.config.delay = delay

        await self.processor.delayed_queue.enqueue(job)


# =============================================================================
# JOB PROCESSOR
# =============================================================================

class JobProcessor:
    """
    Master job processor for BAEL.

    Provides comprehensive background job processing.
    """

    def __init__(
        self,
        num_workers: int = 4,
        persistence_path: Optional[str] = None
    ):
        self.num_workers = num_workers
        self.persistence_path = persistence_path

        # Queues
        self.queue = MemoryQueue()
        self.delayed_queue = DelayedQueue()
        self.dlq = DeadLetterQueue()

        # Handlers
        self.handlers: Dict[str, JobHandler] = {}

        # Workers
        self.workers: List[Worker] = []

        # Jobs tracking
        self.jobs: Dict[str, Job] = {}
        self.scheduled_jobs: Dict[str, ScheduledJob] = {}

        # Callbacks
        self.on_complete: List[Callable[[Job], None]] = []
        self.on_failure: List[Callable[[Job], None]] = []

        # State
        self._running = False
        self._delayed_task: Optional[asyncio.Task] = None
        self._scheduler_task: Optional[asyncio.Task] = None

        # Statistics
        self.total_enqueued = 0
        self.total_completed = 0
        self.total_failed = 0

    # Registration
    def register_handler(
        self,
        name: str,
        handler: Union[JobHandler, Callable]
    ) -> None:
        """Register a job handler."""
        if isinstance(handler, JobHandler):
            self.handlers[name] = handler
        else:
            self.handlers[name] = FunctionHandler(handler)

    def handler(
        self,
        name: str
    ) -> Callable:
        """Decorator to register a handler."""
        def decorator(func: Callable) -> Callable:
            self.register_handler(name, func)
            return func
        return decorator

    # Enqueueing
    async def enqueue(
        self,
        handler: str,
        payload: Dict[str, Any] = None,
        name: str = None,
        priority: JobPriority = JobPriority.NORMAL,
        delay: float = None,
        max_retries: int = 3,
        timeout: float = 300,
        unique: bool = False,
        depends_on: List[str] = None
    ) -> str:
        """Enqueue a new job."""
        if handler not in self.handlers:
            raise ValueError(f"Unknown handler: {handler}")

        config = JobConfig(
            max_retries=max_retries,
            timeout=timeout,
            priority=priority,
            delay=delay,
            unique=unique,
            depends_on=depends_on or []
        )

        job = Job(
            name=name or handler,
            handler=handler,
            payload=payload or {},
            config=config
        )

        # Check uniqueness
        if unique:
            key = self._job_key(handler, payload)
            for existing in self.jobs.values():
                if (existing.status in (JobStatus.PENDING, JobStatus.QUEUED, JobStatus.RUNNING)
                    and self._job_key(existing.handler, existing.payload) == key):
                    return existing.id

        # Check dependencies
        if config.depends_on:
            for dep_id in config.depends_on:
                dep = self.jobs.get(dep_id)
                if dep and dep.status not in (JobStatus.COMPLETED,):
                    job.status = JobStatus.PENDING
                    self.jobs[job.id] = job
                    return job.id

        self.jobs[job.id] = job
        self.total_enqueued += 1

        # Add to appropriate queue
        if delay:
            await self.delayed_queue.enqueue(job)
        else:
            job.status = JobStatus.QUEUED
            await self.queue.enqueue(job)

        return job.id

    async def enqueue_bulk(
        self,
        jobs: List[Dict[str, Any]]
    ) -> List[str]:
        """Enqueue multiple jobs."""
        job_ids = []
        for job_spec in jobs:
            job_id = await self.enqueue(**job_spec)
            job_ids.append(job_id)
        return job_ids

    def _job_key(
        self,
        handler: str,
        payload: Dict[str, Any]
    ) -> str:
        """Generate unique key for job."""
        data = json.dumps({"handler": handler, "payload": payload}, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()

    # Scheduling
    def schedule(
        self,
        name: str,
        handler: str,
        cron: str,
        payload: Dict[str, Any] = None
    ) -> str:
        """Schedule a recurring job."""
        scheduled = ScheduledJob(
            name=name,
            handler=handler,
            schedule=cron,
            payload=payload or {},
            next_run=CronParser.next_run(cron)
        )

        self.scheduled_jobs[scheduled.id] = scheduled
        return scheduled.id

    # Job Management
    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        return self.jobs.get(job_id)

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a job."""
        job = self.jobs.get(job_id)
        if not job:
            return False

        if job.status in (JobStatus.PENDING, JobStatus.QUEUED):
            job.status = JobStatus.CANCELLED
            return True

        return False

    async def retry_job(self, job_id: str) -> bool:
        """Retry a failed job."""
        job = self.jobs.get(job_id)
        if not job:
            # Check DLQ
            job = await self.dlq.retry(job_id)
            if not job:
                return False

        if job.status in (JobStatus.FAILED, JobStatus.DEAD):
            job.status = JobStatus.QUEUED
            job.attempts = 0
            job.error_history.clear()
            await self.queue.enqueue(job)
            return True

        return False

    # Internal
    async def _get_next_job(self) -> Optional[Job]:
        """Get next job for processing."""
        job = await self.queue.dequeue()
        return job

    async def _job_completed(self, job: Job) -> None:
        """Handle job completion."""
        if job.status == JobStatus.COMPLETED:
            self.total_completed += 1

            for callback in self.on_complete:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(job)
                    else:
                        callback(job)
                except Exception as e:
                    logger.error(f"Completion callback error: {e}")

            # Check dependent jobs
            for dep_job in self.jobs.values():
                if job.id in dep_job.config.depends_on:
                    if dep_job.status == JobStatus.PENDING:
                        # Check if all dependencies completed
                        all_done = all(
                            self.jobs.get(d, Job()).status == JobStatus.COMPLETED
                            for d in dep_job.config.depends_on
                        )
                        if all_done:
                            dep_job.status = JobStatus.QUEUED
                            await self.queue.enqueue(dep_job)

        elif job.status == JobStatus.FAILED:
            self.total_failed += 1

            for callback in self.on_failure:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(job)
                    else:
                        callback(job)
                except Exception as e:
                    logger.error(f"Failure callback error: {e}")

    # Lifecycle
    async def start(self) -> None:
        """Start the job processor."""
        if self._running:
            return

        self._running = True

        # Create workers
        for i in range(self.num_workers):
            worker = Worker(f"worker-{i}", self)
            self.workers.append(worker)
            await worker.start()

        # Start delayed job processor
        self._delayed_task = asyncio.create_task(self._process_delayed())

        # Start scheduler
        self._scheduler_task = asyncio.create_task(self._run_scheduler())

    async def stop(self) -> None:
        """Stop the job processor."""
        self._running = False

        # Stop workers
        for worker in self.workers:
            await worker.stop()

        # Stop tasks
        if self._delayed_task:
            self._delayed_task.cancel()
            try:
                await self._delayed_task
            except asyncio.CancelledError:
                pass

        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

    async def _process_delayed(self) -> None:
        """Process delayed jobs."""
        while self._running:
            try:
                job = await self.delayed_queue.dequeue()

                if job:
                    job.status = JobStatus.QUEUED
                    job.config.delay = None
                    await self.queue.enqueue(job)
                else:
                    # Wait for next job
                    next_time = await self.delayed_queue.next_ready_time()
                    if next_time:
                        await asyncio.sleep(min(next_time, 1.0))
                    else:
                        await asyncio.sleep(0.5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Delayed processor error: {e}")
                await asyncio.sleep(1)

    async def _run_scheduler(self) -> None:
        """Run scheduled jobs."""
        while self._running:
            try:
                now = datetime.now()

                for scheduled in self.scheduled_jobs.values():
                    if not scheduled.enabled:
                        continue

                    if scheduled.next_run and scheduled.next_run <= now:
                        # Enqueue job
                        await self.enqueue(
                            handler=scheduled.handler,
                            payload=scheduled.payload,
                            name=f"{scheduled.name}-{scheduled.run_count + 1}"
                        )

                        scheduled.last_run = now
                        scheduled.run_count += 1
                        scheduled.next_run = CronParser.next_run(scheduled.schedule, now)

                await asyncio.sleep(30)  # Check every 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(10)

    # Statistics
    def get_stats(self) -> Dict[str, Any]:
        """Get processor statistics."""
        status_counts = defaultdict(int)
        for job in self.jobs.values():
            status_counts[job.status.value] += 1

        worker_stats = []
        for worker in self.workers:
            worker_stats.append({
                "id": worker.id,
                "state": worker.state.value,
                "jobs_processed": worker.stats.jobs_processed,
                "jobs_failed": worker.stats.jobs_failed,
                "current_job": worker.stats.current_job
            })

        return {
            "running": self._running,
            "workers": len(self.workers),
            "total_enqueued": self.total_enqueued,
            "total_completed": self.total_completed,
            "total_failed": self.total_failed,
            "queue_size": len([j for j in self.jobs.values() if j.status == JobStatus.QUEUED]),
            "status_counts": dict(status_counts),
            "worker_stats": worker_stats,
            "scheduled_jobs": len(self.scheduled_jobs),
            "dlq_size": len(self.dlq._jobs)
        }

    async def get_queue_size(self) -> int:
        """Get current queue size."""
        return await self.queue.size()

    async def get_dlq_jobs(self) -> List[Job]:
        """Get dead letter queue jobs."""
        return await self.dlq.get_all()


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Background Job Processor."""
    print("=" * 70)
    print("BAEL - BACKGROUND JOB PROCESSOR DEMO")
    print("Comprehensive Job Scheduling and Processing")
    print("=" * 70)
    print()

    processor = JobProcessor(num_workers=2)

    # 1. Register Handlers
    print("1. REGISTERING HANDLERS:")
    print("-" * 40)

    @processor.handler("send_email")
    async def send_email(payload: Dict, context: JobContext):
        await asyncio.sleep(0.1)  # Simulate work
        context.update_progress(50, "Sending...")
        await asyncio.sleep(0.1)
        context.update_progress(100, "Sent")
        return {"sent_to": payload.get("to"), "status": "delivered"}

    @processor.handler("process_data")
    async def process_data(payload: Dict, context: JobContext):
        items = payload.get("items", [])
        for i, item in enumerate(items):
            context.update_progress((i + 1) / len(items) * 100, f"Processing {item}")
            await asyncio.sleep(0.05)
        return {"processed": len(items)}

    @processor.handler("failing_job")
    async def failing_job(payload: Dict, context: JobContext):
        if context.attempt < 3:
            raise RuntimeError(f"Failure on attempt {context.attempt}")
        return {"success": True}

    print("   Registered: send_email")
    print("   Registered: process_data")
    print("   Registered: failing_job")
    print()

    # 2. Start Processor
    print("2. STARTING PROCESSOR:")
    print("-" * 40)

    await processor.start()
    print(f"   Workers started: {len(processor.workers)}")
    print()

    # 3. Enqueue Jobs
    print("3. ENQUEUEING JOBS:")
    print("-" * 40)

    # Simple job
    job1_id = await processor.enqueue(
        "send_email",
        payload={"to": "user@example.com", "subject": "Hello"},
        priority=JobPriority.HIGH
    )
    print(f"   Enqueued: send_email [{job1_id[:8]}]")

    # Job with delay
    job2_id = await processor.enqueue(
        "process_data",
        payload={"items": ["a", "b", "c", "d"]},
        delay=0.5
    )
    print(f"   Enqueued: process_data (delayed) [{job2_id[:8]}]")

    # Job that fails and retries
    job3_id = await processor.enqueue(
        "failing_job",
        payload={"test": True},
        max_retries=3
    )
    print(f"   Enqueued: failing_job [{job3_id[:8]}]")
    print()

    # 4. Wait for Completion
    print("4. PROCESSING JOBS:")
    print("-" * 40)

    await asyncio.sleep(3)  # Wait for jobs to complete

    for job_id in [job1_id, job2_id, job3_id]:
        job = await processor.get_job(job_id)
        if job:
            status = job.status.value
            result = job.result.data if job.result and job.result.success else "N/A"
            print(f"   {job.name}: {status} - Result: {result}")
    print()

    # 5. Job Dependencies
    print("5. JOB DEPENDENCIES:")
    print("-" * 40)

    parent_id = await processor.enqueue(
        "send_email",
        payload={"to": "parent@test.com"},
        name="parent_job"
    )

    child_id = await processor.enqueue(
        "send_email",
        payload={"to": "child@test.com"},
        name="child_job",
        depends_on=[parent_id]
    )

    print(f"   Parent job: {parent_id[:8]}")
    print(f"   Child job: {child_id[:8]} (depends on parent)")

    await asyncio.sleep(1)

    child = await processor.get_job(child_id)
    print(f"   Child status: {child.status.value}")
    print()

    # 6. Priority Queue
    print("6. PRIORITY QUEUE:")
    print("-" * 40)

    priorities = [
        (JobPriority.LOW, "low_priority"),
        (JobPriority.HIGH, "high_priority"),
        (JobPriority.CRITICAL, "critical_job"),
        (JobPriority.NORMAL, "normal_priority"),
    ]

    for priority, name in priorities:
        await processor.enqueue(
            "send_email",
            payload={"type": name},
            name=name,
            priority=priority
        )
        print(f"   Enqueued: {name} ({priority.name})")

    await asyncio.sleep(1)
    print()

    # 7. Scheduled Jobs
    print("7. SCHEDULED JOBS:")
    print("-" * 40)

    # Note: This won't run immediately in the demo
    schedule_id = processor.schedule(
        name="hourly_report",
        handler="send_email",
        cron="0 * * * *",  # Every hour
        payload={"type": "report"}
    )

    scheduled = processor.scheduled_jobs[schedule_id]
    print(f"   Scheduled: hourly_report")
    print(f"   Next run: {scheduled.next_run}")
    print()

    # 8. Dead Letter Queue
    print("8. DEAD LETTER QUEUE:")
    print("-" * 40)

    @processor.handler("always_fails")
    async def always_fails(payload: Dict, context: JobContext):
        raise RuntimeError("This always fails")

    fail_id = await processor.enqueue(
        "always_fails",
        payload={},
        max_retries=1
    )

    await asyncio.sleep(2)

    dlq_jobs = await processor.get_dlq_jobs()
    print(f"   DLQ size: {len(dlq_jobs)}")

    if dlq_jobs:
        print(f"   Failed job: {dlq_jobs[0].name}")
        print(f"   Errors: {dlq_jobs[0].error_history}")
    print()

    # 9. Bulk Enqueueing
    print("9. BULK ENQUEUEING:")
    print("-" * 40)

    bulk_jobs = [
        {"handler": "send_email", "payload": {"to": f"user{i}@test.com"}}
        for i in range(5)
    ]

    job_ids = await processor.enqueue_bulk(bulk_jobs)
    print(f"   Enqueued {len(job_ids)} jobs")

    await asyncio.sleep(1)
    print()

    # 10. Statistics
    print("10. STATISTICS:")
    print("-" * 40)

    stats = processor.get_stats()
    print(f"    Running: {stats['running']}")
    print(f"    Workers: {stats['workers']}")
    print(f"    Total enqueued: {stats['total_enqueued']}")
    print(f"    Total completed: {stats['total_completed']}")
    print(f"    Total failed: {stats['total_failed']}")
    print(f"    Status counts: {stats['status_counts']}")
    print()

    # Cleanup
    await processor.stop()

    print("=" * 70)
    print("DEMO COMPLETE - Job Processor Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
