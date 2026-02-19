"""
BAEL Job Queue Engine
======================

Background job processing with workers, priorities, and retries.

"Ba'el's workers never rest, never fail, always deliver." — Ba'el
"""

import asyncio
import logging
import uuid
import threading
import pickle
import base64
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Union, TypeVar, Awaitable
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import defaultdict
import heapq
import functools
import traceback

logger = logging.getLogger("BAEL.JobQueue")

T = TypeVar("T")


# ============================================================================
# ENUMS
# ============================================================================

class JobStatus(Enum):
    """Job status."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class JobPriority(Enum):
    """Job priority."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class JobType(Enum):
    """Job type."""
    SYNC = "sync"
    ASYNC = "async"


class RetryStrategy(Enum):
    """Retry strategy."""
    NONE = "none"
    IMMEDIATE = "immediate"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class JobResult:
    """Result of a job execution."""
    success: bool
    value: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class Job:
    """A job to execute."""
    id: str
    name: str
    func_name: str
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)

    # Priority
    priority: JobPriority = JobPriority.NORMAL

    # Status
    status: JobStatus = JobStatus.PENDING

    # Retry
    retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    max_retries: int = 3
    retry_count: int = 0
    retry_delay: float = 1.0

    # Timeout
    timeout_seconds: Optional[float] = None

    # Scheduling
    scheduled_at: Optional[datetime] = None
    run_at: Optional[datetime] = None

    # Execution
    worker_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Result
    result: Optional[JobResult] = None

    # Dependencies
    depends_on: List[str] = field(default_factory=list)

    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Created
    created_at: datetime = field(default_factory=datetime.now)

    def __lt__(self, other: 'Job') -> bool:
        """Compare for priority queue."""
        if self.priority.value != other.priority.value:
            return self.priority.value > other.priority.value
        return self.created_at < other.created_at


@dataclass
class Worker:
    """A job worker."""
    id: str
    name: str
    status: str = "idle"
    current_job: Optional[str] = None
    jobs_completed: int = 0
    jobs_failed: int = 0
    started_at: datetime = field(default_factory=datetime.now)
    last_heartbeat: datetime = field(default_factory=datetime.now)


@dataclass
class JobQueueConfig:
    """Job queue configuration."""
    max_workers: int = 4
    default_timeout: float = 300.0
    default_max_retries: int = 3
    default_retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    poll_interval: float = 0.1
    dead_letter_enabled: bool = True


# ============================================================================
# JOB REGISTRY
# ============================================================================

class JobRegistry:
    """Registry of job functions."""

    def __init__(self):
        """Initialize registry."""
        self._jobs: Dict[str, Callable] = {}

    def register(self, name: str, func: Callable) -> None:
        """Register a job function."""
        self._jobs[name] = func

    def get(self, name: str) -> Optional[Callable]:
        """Get a job function."""
        return self._jobs.get(name)

    def list(self) -> List[str]:
        """List registered jobs."""
        return list(self._jobs.keys())


# ============================================================================
# JOB QUEUE
# ============================================================================

class PriorityJobQueue:
    """Priority queue for jobs."""

    def __init__(self):
        """Initialize queue."""
        self._queue: List[Job] = []
        self._lock = threading.Lock()

    def push(self, job: Job) -> None:
        """Add job to queue."""
        with self._lock:
            heapq.heappush(self._queue, job)

    def pop(self) -> Optional[Job]:
        """Get highest priority job."""
        with self._lock:
            if self._queue:
                return heapq.heappop(self._queue)
            return None

    def peek(self) -> Optional[Job]:
        """Peek at next job."""
        with self._lock:
            if self._queue:
                return self._queue[0]
            return None

    def size(self) -> int:
        """Get queue size."""
        return len(self._queue)


# ============================================================================
# WORKER POOL
# ============================================================================

class WorkerPool:
    """Pool of workers."""

    def __init__(self, max_workers: int = 4):
        """Initialize pool."""
        self.max_workers = max_workers
        self._workers: Dict[str, Worker] = {}
        self._tasks: Dict[str, asyncio.Task] = {}
        self._lock = threading.Lock()

    def create_worker(self, name: Optional[str] = None) -> Worker:
        """Create a new worker."""
        worker_id = str(uuid.uuid4())
        worker = Worker(
            id=worker_id,
            name=name or f"worker-{worker_id[:8]}"
        )

        with self._lock:
            self._workers[worker_id] = worker

        return worker

    def get_idle_worker(self) -> Optional[Worker]:
        """Get an idle worker."""
        with self._lock:
            for worker in self._workers.values():
                if worker.status == "idle":
                    return worker
        return None

    def count_active(self) -> int:
        """Count active workers."""
        with self._lock:
            return sum(1 for w in self._workers.values() if w.status == "busy")

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        with self._lock:
            return {
                'total': len(self._workers),
                'idle': sum(1 for w in self._workers.values() if w.status == "idle"),
                'busy': sum(1 for w in self._workers.values() if w.status == "busy"),
                'jobs_completed': sum(w.jobs_completed for w in self._workers.values()),
                'jobs_failed': sum(w.jobs_failed for w in self._workers.values())
            }


# ============================================================================
# MAIN JOB QUEUE ENGINE
# ============================================================================

class JobQueueEngine:
    """
    Main job queue engine.

    Features:
    - Priority-based job scheduling
    - Multiple workers
    - Retry strategies
    - Dependencies

    "Ba'el ensures every task reaches completion." — Ba'el
    """

    def __init__(self, config: Optional[JobQueueConfig] = None):
        """Initialize job queue engine."""
        self.config = config or JobQueueConfig()

        # Registry
        self._registry = JobRegistry()

        # Queue
        self._queue = PriorityJobQueue()

        # Workers
        self._pool = WorkerPool(self.config.max_workers)

        # Jobs
        self._jobs: Dict[str, Job] = {}
        self._dead_letter: List[Job] = []

        # Stats
        self._stats = defaultdict(int)

        # State
        self._running = False
        self._task: Optional[asyncio.Task] = None

        self._lock = threading.RLock()

        logger.info("JobQueueEngine initialized")

    # ========================================================================
    # REGISTRATION
    # ========================================================================

    def register(self, name: str, func: Callable) -> None:
        """Register a job function."""
        self._registry.register(name, func)

    # ========================================================================
    # ENQUEUEING
    # ========================================================================

    def enqueue(
        self,
        name: str,
        *args,
        priority: JobPriority = JobPriority.NORMAL,
        delay: Optional[float] = None,
        run_at: Optional[datetime] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        depends_on: Optional[List[str]] = None,
        **kwargs
    ) -> Job:
        """
        Enqueue a job.

        Args:
            name: Job function name
            *args: Job arguments
            priority: Job priority
            delay: Delay before running
            run_at: Specific time to run
            timeout: Job timeout
            max_retries: Max retry attempts
            depends_on: Job IDs this depends on

        Returns:
            Job object
        """
        # Check function exists
        if not self._registry.get(name):
            raise ValueError(f"Job not registered: {name}")

        # Create job
        job = Job(
            id=str(uuid.uuid4()),
            name=name,
            func_name=name,
            args=args,
            kwargs=kwargs,
            priority=priority,
            timeout_seconds=timeout or self.config.default_timeout,
            max_retries=max_retries if max_retries is not None else self.config.default_max_retries,
            retry_strategy=self.config.default_retry_strategy,
            depends_on=depends_on or []
        )

        # Scheduling
        if delay:
            job.run_at = datetime.now() + timedelta(seconds=delay)
        elif run_at:
            job.run_at = run_at

        # Store and queue
        with self._lock:
            self._jobs[job.id] = job
            job.status = JobStatus.QUEUED
            self._queue.push(job)
            self._stats['enqueued'] += 1

        logger.debug(f"Enqueued job: {job.id} ({name})")

        return job

    def enqueue_many(
        self,
        jobs: List[Dict[str, Any]]
    ) -> List[Job]:
        """Enqueue multiple jobs."""
        return [self.enqueue(**job) for job in jobs]

    # ========================================================================
    # EXECUTION
    # ========================================================================

    async def start(self) -> None:
        """Start the job queue."""
        if self._running:
            return

        self._running = True

        # Create workers
        for i in range(self.config.max_workers):
            self._pool.create_worker(f"worker-{i}")

        # Start main loop
        self._task = asyncio.create_task(self._process_loop())

        logger.info("JobQueueEngine started")

    async def stop(self) -> None:
        """Stop the job queue."""
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("JobQueueEngine stopped")

    async def _process_loop(self) -> None:
        """Main processing loop."""
        while self._running:
            try:
                # Get next job
                job = self._queue.pop()

                if not job:
                    await asyncio.sleep(self.config.poll_interval)
                    continue

                # Check dependencies
                if job.depends_on:
                    deps_complete = all(
                        self._jobs.get(dep_id, Job(id="", name="", func_name="")).status == JobStatus.COMPLETED
                        for dep_id in job.depends_on
                    )

                    if not deps_complete:
                        self._queue.push(job)
                        await asyncio.sleep(self.config.poll_interval)
                        continue

                # Check scheduled time
                if job.run_at and datetime.now() < job.run_at:
                    self._queue.push(job)
                    await asyncio.sleep(self.config.poll_interval)
                    continue

                # Get worker
                worker = self._pool.get_idle_worker()

                if not worker:
                    self._queue.push(job)
                    await asyncio.sleep(self.config.poll_interval)
                    continue

                # Execute job
                asyncio.create_task(self._execute_job(job, worker))

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Processing error: {e}")

    async def _execute_job(self, job: Job, worker: Worker) -> None:
        """Execute a job."""
        # Update state
        job.status = JobStatus.RUNNING
        job.worker_id = worker.id
        job.started_at = datetime.now()

        worker.status = "busy"
        worker.current_job = job.id

        start_time = datetime.now()

        try:
            # Get function
            func = self._registry.get(job.func_name)

            if not func:
                raise ValueError(f"Job function not found: {job.func_name}")

            # Execute with timeout
            if asyncio.iscoroutinefunction(func):
                result = await asyncio.wait_for(
                    func(*job.args, **job.kwargs),
                    timeout=job.timeout_seconds
                )
            else:
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, functools.partial(func, *job.args, **job.kwargs)),
                    timeout=job.timeout_seconds
                )

            # Success
            end_time = datetime.now()
            job.result = JobResult(
                success=True,
                value=result,
                duration_ms=(end_time - start_time).total_seconds() * 1000,
                started_at=start_time,
                completed_at=end_time
            )
            job.status = JobStatus.COMPLETED
            job.completed_at = end_time

            worker.jobs_completed += 1
            self._stats['completed'] += 1

            logger.debug(f"Job completed: {job.id}")

        except asyncio.TimeoutError:
            job.status = JobStatus.TIMEOUT
            job.result = JobResult(
                success=False,
                error="Job timed out"
            )
            await self._handle_failure(job)

        except Exception as e:
            job.result = JobResult(
                success=False,
                error=str(e)
            )
            await self._handle_failure(job)

        finally:
            worker.status = "idle"
            worker.current_job = None
            worker.last_heartbeat = datetime.now()

    async def _handle_failure(self, job: Job) -> None:
        """Handle job failure."""
        if job.retry_count < job.max_retries:
            # Retry
            job.retry_count += 1
            job.status = JobStatus.RETRYING

            # Calculate delay
            delay = self._calculate_retry_delay(job)
            job.run_at = datetime.now() + timedelta(seconds=delay)

            self._queue.push(job)
            self._stats['retried'] += 1

            logger.warning(f"Job retrying: {job.id} (attempt {job.retry_count})")
        else:
            # Failed permanently
            job.status = JobStatus.FAILED
            job.completed_at = datetime.now()

            if self.config.dead_letter_enabled:
                self._dead_letter.append(job)

            self._stats['failed'] += 1

            logger.error(f"Job failed: {job.id} - {job.result.error if job.result else 'Unknown'}")

    def _calculate_retry_delay(self, job: Job) -> float:
        """Calculate retry delay."""
        base = job.retry_delay
        attempt = job.retry_count

        if job.retry_strategy == RetryStrategy.IMMEDIATE:
            return 0
        elif job.retry_strategy == RetryStrategy.LINEAR:
            return base * attempt
        elif job.retry_strategy == RetryStrategy.EXPONENTIAL:
            return base * (2 ** (attempt - 1))
        else:
            return base

    # ========================================================================
    # JOB MANAGEMENT
    # ========================================================================

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID."""
        return self._jobs.get(job_id)

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job."""
        with self._lock:
            if job_id in self._jobs:
                job = self._jobs[job_id]
                if job.status in [JobStatus.PENDING, JobStatus.QUEUED]:
                    job.status = JobStatus.CANCELLED
                    self._stats['cancelled'] += 1
                    return True
        return False

    def get_jobs(
        self,
        status: Optional[JobStatus] = None,
        limit: int = 100
    ) -> List[Job]:
        """Get jobs by status."""
        jobs = list(self._jobs.values())

        if status:
            jobs = [j for j in jobs if j.status == status]

        return sorted(jobs, key=lambda j: j.created_at, reverse=True)[:limit]

    # ========================================================================
    # STATUS
    # ========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        return {
            'running': self._running,
            'queue_size': self._queue.size(),
            'total_jobs': len(self._jobs),
            'workers': self._pool.get_stats(),
            'stats': dict(self._stats),
            'dead_letter_count': len(self._dead_letter)
        }


# ============================================================================
# DECORATOR
# ============================================================================

def job(
    name: Optional[str] = None,
    priority: JobPriority = JobPriority.NORMAL,
    timeout: Optional[float] = None,
    max_retries: int = 3
):
    """Decorator to register a job function."""
    def decorator(func: Callable) -> Callable:
        job_name = name or func.__name__

        # Register with global engine
        job_queue_engine.register(job_name, func)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return job_queue_engine.enqueue(
                job_name,
                *args,
                priority=priority,
                timeout=timeout,
                max_retries=max_retries,
                **kwargs
            )

        return wrapper

    return decorator


# ============================================================================
# CONVENIENCE INSTANCE
# ============================================================================

job_queue_engine = JobQueueEngine()
