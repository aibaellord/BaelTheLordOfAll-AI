"""
BAEL Scheduler Engine
=====================

Advanced task scheduling with cron, intervals, and one-time jobs.

"Ba'el commands when events manifest." — Ba'el
"""

import asyncio
import logging
import re
import uuid
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Awaitable, Union
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import defaultdict
import heapq
import traceback

logger = logging.getLogger("BAEL.Scheduler")


# ============================================================================
# ENUMS
# ============================================================================

class JobStatus(Enum):
    """Job statuses."""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class JobType(Enum):
    """Job types."""
    CRON = "cron"
    INTERVAL = "interval"
    ONE_TIME = "one_time"
    DEPENDENT = "dependent"


class TriggerType(Enum):
    """Trigger types."""
    CRON = "cron"
    INTERVAL = "interval"
    DATE = "date"
    IMMEDIATE = "immediate"


class ExecutionPolicy(Enum):
    """Execution policies."""
    PARALLEL = "parallel"       # Allow parallel executions
    SEQUENTIAL = "sequential"   # Queue if running
    SKIP = "skip"               # Skip if running
    REPLACE = "replace"         # Cancel running, start new


# ============================================================================
# CRON EXPRESSION PARSER
# ============================================================================

@dataclass
class CronExpression:
    """
    Cron expression parser and evaluator.

    Format: minute hour day_of_month month day_of_week

    Supports:
    - * (any)
    - */n (every n)
    - n-m (range)
    - n,m,o (list)
    """

    expression: str

    # Parsed fields
    minute: List[int] = field(default_factory=list)
    hour: List[int] = field(default_factory=list)
    day_of_month: List[int] = field(default_factory=list)
    month: List[int] = field(default_factory=list)
    day_of_week: List[int] = field(default_factory=list)

    def __post_init__(self):
        """Parse the expression."""
        self._parse()

    def _parse(self) -> None:
        """Parse cron expression."""
        parts = self.expression.strip().split()

        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {self.expression}")

        self.minute = self._parse_field(parts[0], 0, 59)
        self.hour = self._parse_field(parts[1], 0, 23)
        self.day_of_month = self._parse_field(parts[2], 1, 31)
        self.month = self._parse_field(parts[3], 1, 12)
        self.day_of_week = self._parse_field(parts[4], 0, 6)

    def _parse_field(self, field: str, min_val: int, max_val: int) -> List[int]:
        """Parse a single cron field."""
        values = set()

        for part in field.split(','):
            if part == '*':
                values.update(range(min_val, max_val + 1))

            elif part.startswith('*/'):
                step = int(part[2:])
                values.update(range(min_val, max_val + 1, step))

            elif '-' in part:
                if '/' in part:
                    range_part, step = part.split('/')
                    start, end = map(int, range_part.split('-'))
                    values.update(range(start, end + 1, int(step)))
                else:
                    start, end = map(int, part.split('-'))
                    values.update(range(start, end + 1))

            else:
                values.add(int(part))

        return sorted(v for v in values if min_val <= v <= max_val)

    def matches(self, dt: datetime) -> bool:
        """Check if datetime matches cron expression."""
        return (
            dt.minute in self.minute and
            dt.hour in self.hour and
            dt.day in self.day_of_month and
            dt.month in self.month and
            dt.weekday() in self.day_of_week
        )

    def next_run(self, from_time: Optional[datetime] = None) -> datetime:
        """Calculate next run time."""
        current = from_time or datetime.now()
        current = current.replace(second=0, microsecond=0) + timedelta(minutes=1)

        # Search for next matching time (up to 2 years)
        for _ in range(2 * 365 * 24 * 60):
            if self.matches(current):
                return current
            current += timedelta(minutes=1)

        raise ValueError(f"Could not find next run time for: {self.expression}")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Trigger:
    """Job trigger."""
    id: str
    trigger_type: TriggerType

    # Cron
    cron_expression: Optional[str] = None
    cron: Optional[CronExpression] = None

    # Interval
    interval_seconds: float = 0

    # Date
    run_date: Optional[datetime] = None

    # State
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None

    def __post_init__(self):
        """Initialize trigger."""
        if self.cron_expression:
            self.cron = CronExpression(self.cron_expression)

        self._calculate_next_run()

    def _calculate_next_run(self) -> None:
        """Calculate next run time."""
        now = datetime.now()

        if self.trigger_type == TriggerType.CRON and self.cron:
            self.next_run = self.cron.next_run(now)

        elif self.trigger_type == TriggerType.INTERVAL:
            base = self.last_run or now
            self.next_run = base + timedelta(seconds=self.interval_seconds)

        elif self.trigger_type == TriggerType.DATE:
            self.next_run = self.run_date

        elif self.trigger_type == TriggerType.IMMEDIATE:
            self.next_run = now

    def update_after_run(self) -> None:
        """Update trigger after job runs."""
        self.last_run = datetime.now()

        if self.trigger_type == TriggerType.CRON:
            self._calculate_next_run()

        elif self.trigger_type == TriggerType.INTERVAL:
            self._calculate_next_run()

        elif self.trigger_type in (TriggerType.DATE, TriggerType.IMMEDIATE):
            self.next_run = None  # One-time jobs


@dataclass
class JobResult:
    """Job execution result."""
    job_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    traceback: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: Optional[datetime] = None
    duration_ms: float = 0.0


@dataclass
class Job:
    """A scheduled job."""
    id: str
    name: str

    # Handler
    handler: Union[Callable[[], Any], Callable[[], Awaitable[Any]]]
    is_async: bool = False

    # Trigger
    trigger: Optional[Trigger] = None

    # Type
    job_type: JobType = JobType.CRON

    # Status
    status: JobStatus = JobStatus.PENDING

    # Configuration
    max_retries: int = 3
    retry_delay: float = 60.0
    timeout: float = 3600.0

    # Execution policy
    policy: ExecutionPolicy = ExecutionPolicy.SKIP

    # Dependencies
    depends_on: List[str] = field(default_factory=list)

    # State
    retry_count: int = 0
    last_result: Optional[JobResult] = None
    run_count: int = 0

    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)

    def __lt__(self, other: 'Job') -> bool:
        """Compare jobs by next run time."""
        if not self.trigger or not self.trigger.next_run:
            return False
        if not other.trigger or not other.trigger.next_run:
            return True
        return self.trigger.next_run < other.trigger.next_run


# ============================================================================
# JOB QUEUE
# ============================================================================

class JobQueue:
    """Priority queue for jobs based on next run time."""

    def __init__(self):
        """Initialize queue."""
        self._heap: List[Tuple[datetime, str]] = []
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()

    def push(self, job: Job) -> None:
        """Add job to queue."""
        with self._lock:
            self._jobs[job.id] = job

            if job.trigger and job.trigger.next_run:
                heapq.heappush(self._heap, (job.trigger.next_run, job.id))

    def pop(self) -> Optional[Job]:
        """Get next job to run."""
        with self._lock:
            now = datetime.now()

            while self._heap:
                run_time, job_id = self._heap[0]

                if run_time > now:
                    return None

                heapq.heappop(self._heap)

                if job_id in self._jobs:
                    return self._jobs[job_id]

            return None

    def peek(self) -> Optional[datetime]:
        """Peek at next run time."""
        with self._lock:
            if self._heap:
                return self._heap[0][0]
            return None

    def reschedule(self, job: Job) -> None:
        """Reschedule a job."""
        with self._lock:
            if job.trigger and job.trigger.next_run:
                heapq.heappush(self._heap, (job.trigger.next_run, job.id))

    def remove(self, job_id: str) -> Optional[Job]:
        """Remove job from queue."""
        with self._lock:
            return self._jobs.pop(job_id, None)

    def get(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        return self._jobs.get(job_id)

    def all(self) -> List[Job]:
        """Get all jobs."""
        return list(self._jobs.values())


# ============================================================================
# JOB EXECUTOR
# ============================================================================

class JobExecutor:
    """Executes jobs."""

    def __init__(self):
        """Initialize executor."""
        self._running: Dict[str, asyncio.Task] = {}
        self._results: Dict[str, List[JobResult]] = defaultdict(list)

    async def execute(self, job: Job) -> JobResult:
        """Execute a job."""
        result = JobResult(
            job_id=job.id,
            success=False,
            started_at=datetime.now()
        )

        try:
            # Check execution policy
            if job.id in self._running:
                if job.policy == ExecutionPolicy.SKIP:
                    result.error = "Job already running (skipped)"
                    return result

                elif job.policy == ExecutionPolicy.REPLACE:
                    self._running[job.id].cancel()
                    del self._running[job.id]

                elif job.policy == ExecutionPolicy.SEQUENTIAL:
                    # Wait for running job
                    await self._running[job.id]

            # Execute with timeout
            task = asyncio.create_task(self._run_job(job))
            self._running[job.id] = task

            try:
                result.result = await asyncio.wait_for(task, timeout=job.timeout)
                result.success = True
            except asyncio.TimeoutError:
                result.error = f"Job timed out after {job.timeout} seconds"
                task.cancel()
            except asyncio.CancelledError:
                result.error = "Job was cancelled"
            except Exception as e:
                result.error = str(e)
                result.traceback = traceback.format_exc()
            finally:
                if job.id in self._running:
                    del self._running[job.id]

        except Exception as e:
            result.error = str(e)
            result.traceback = traceback.format_exc()

        finally:
            result.finished_at = datetime.now()
            result.duration_ms = (
                result.finished_at - result.started_at
            ).total_seconds() * 1000

            # Store result
            self._results[job.id].append(result)

            # Keep only last 100 results per job
            if len(self._results[job.id]) > 100:
                self._results[job.id] = self._results[job.id][-100:]

        return result

    async def _run_job(self, job: Job) -> Any:
        """Run the job handler."""
        if job.is_async:
            return await job.handler()
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, job.handler)

    def is_running(self, job_id: str) -> bool:
        """Check if job is running."""
        return job_id in self._running

    def get_history(self, job_id: str, limit: int = 10) -> List[JobResult]:
        """Get job execution history."""
        return self._results.get(job_id, [])[-limit:]

    async def cancel(self, job_id: str) -> bool:
        """Cancel a running job."""
        if job_id in self._running:
            self._running[job_id].cancel()
            del self._running[job_id]
            return True
        return False


# ============================================================================
# SCHEDULER CONFIG
# ============================================================================

@dataclass
class SchedulerConfig:
    """Scheduler configuration."""
    tick_interval: float = 1.0
    max_concurrent_jobs: int = 10
    enable_persistence: bool = False
    persistence_path: str = "./scheduler_state.json"
    timezone: str = "UTC"


# ============================================================================
# MAIN SCHEDULER ENGINE
# ============================================================================

class SchedulerEngine:
    """
    Main scheduler engine.

    Features:
    - Cron-based scheduling
    - Interval jobs
    - One-time tasks
    - Job dependencies
    - Retry logic

    "Ba'el orchestrates the flow of time." — Ba'el
    """

    def __init__(self, config: Optional[SchedulerConfig] = None):
        """Initialize scheduler."""
        self.config = config or SchedulerConfig()

        self._queue = JobQueue()
        self._executor = JobExecutor()

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._semaphore: Optional[asyncio.Semaphore] = None

        self._lock = threading.RLock()

        logger.info("SchedulerEngine initialized")

    # ========================================================================
    # JOB MANAGEMENT
    # ========================================================================

    def add_cron_job(
        self,
        name: str,
        handler: Callable,
        cron_expression: str,
        is_async: bool = False,
        **kwargs
    ) -> Job:
        """Add a cron-based job."""
        trigger = Trigger(
            id=str(uuid.uuid4()),
            trigger_type=TriggerType.CRON,
            cron_expression=cron_expression
        )

        job = Job(
            id=str(uuid.uuid4()),
            name=name,
            handler=handler,
            is_async=is_async,
            trigger=trigger,
            job_type=JobType.CRON,
            **kwargs
        )

        self._queue.push(job)
        job.status = JobStatus.SCHEDULED

        logger.info(f"Added cron job: {name} ({cron_expression})")

        return job

    def add_interval_job(
        self,
        name: str,
        handler: Callable,
        interval_seconds: float,
        is_async: bool = False,
        **kwargs
    ) -> Job:
        """Add an interval-based job."""
        trigger = Trigger(
            id=str(uuid.uuid4()),
            trigger_type=TriggerType.INTERVAL,
            interval_seconds=interval_seconds
        )

        job = Job(
            id=str(uuid.uuid4()),
            name=name,
            handler=handler,
            is_async=is_async,
            trigger=trigger,
            job_type=JobType.INTERVAL,
            **kwargs
        )

        self._queue.push(job)
        job.status = JobStatus.SCHEDULED

        logger.info(f"Added interval job: {name} (every {interval_seconds}s)")

        return job

    def add_one_time_job(
        self,
        name: str,
        handler: Callable,
        run_at: Optional[datetime] = None,
        is_async: bool = False,
        **kwargs
    ) -> Job:
        """Add a one-time job."""
        if run_at:
            trigger = Trigger(
                id=str(uuid.uuid4()),
                trigger_type=TriggerType.DATE,
                run_date=run_at
            )
        else:
            trigger = Trigger(
                id=str(uuid.uuid4()),
                trigger_type=TriggerType.IMMEDIATE
            )

        job = Job(
            id=str(uuid.uuid4()),
            name=name,
            handler=handler,
            is_async=is_async,
            trigger=trigger,
            job_type=JobType.ONE_TIME,
            **kwargs
        )

        self._queue.push(job)
        job.status = JobStatus.SCHEDULED

        logger.info(f"Added one-time job: {name}")

        return job

    def add_dependent_job(
        self,
        name: str,
        handler: Callable,
        depends_on: List[str],
        is_async: bool = False,
        **kwargs
    ) -> Job:
        """Add a job that depends on other jobs."""
        job = Job(
            id=str(uuid.uuid4()),
            name=name,
            handler=handler,
            is_async=is_async,
            job_type=JobType.DEPENDENT,
            depends_on=depends_on,
            **kwargs
        )

        self._queue.push(job)
        job.status = JobStatus.PENDING

        logger.info(f"Added dependent job: {name} (depends on {depends_on})")

        return job

    def remove_job(self, job_id: str) -> bool:
        """Remove a job."""
        job = self._queue.remove(job_id)
        if job:
            job.status = JobStatus.CANCELLED
            return True
        return False

    def pause_job(self, job_id: str) -> bool:
        """Pause a job."""
        job = self._queue.get(job_id)
        if job:
            job.status = JobStatus.PAUSED
            return True
        return False

    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job."""
        job = self._queue.get(job_id)
        if job and job.status == JobStatus.PAUSED:
            job.status = JobStatus.SCHEDULED
            return True
        return False

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID."""
        return self._queue.get(job_id)

    def list_jobs(self, status: Optional[JobStatus] = None) -> List[Job]:
        """List all jobs."""
        jobs = self._queue.all()

        if status:
            jobs = [j for j in jobs if j.status == status]

        return jobs

    # ========================================================================
    # SCHEDULER CONTROL
    # ========================================================================

    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            return

        self._running = True
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent_jobs)
        self._task = asyncio.create_task(self._run_loop())

        logger.info("Scheduler started")

    async def stop(self) -> None:
        """Stop the scheduler."""
        if not self._running:
            return

        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Scheduler stopped")

    async def _run_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                await self._tick()
                await asyncio.sleep(self.config.tick_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")

    async def _tick(self) -> None:
        """Process one scheduler tick."""
        # Process due jobs
        while True:
            job = self._queue.pop()

            if not job:
                break

            if job.status != JobStatus.SCHEDULED:
                continue

            # Check dependencies
            if job.depends_on:
                deps_met = all(
                    self._check_dependency(dep_id)
                    for dep_id in job.depends_on
                )

                if not deps_met:
                    # Reschedule for later
                    job.trigger.next_run = datetime.now() + timedelta(minutes=1)
                    self._queue.reschedule(job)
                    continue

            # Execute job
            asyncio.create_task(self._execute_job(job))

    def _check_dependency(self, job_id: str) -> bool:
        """Check if a dependency is satisfied."""
        job = self._queue.get(job_id)

        if not job:
            return True

        if job.last_result and job.last_result.success:
            return True

        return False

    async def _execute_job(self, job: Job) -> None:
        """Execute a job."""
        async with self._semaphore:
            job.status = JobStatus.RUNNING

            try:
                result = await self._executor.execute(job)
                job.last_result = result
                job.run_count += 1

                if result.success:
                    job.retry_count = 0
                    job.status = JobStatus.COMPLETED
                else:
                    # Handle retry
                    if job.retry_count < job.max_retries:
                        job.retry_count += 1
                        job.status = JobStatus.SCHEDULED

                        # Schedule retry
                        if job.trigger:
                            job.trigger.next_run = datetime.now() + timedelta(
                                seconds=job.retry_delay * job.retry_count
                            )
                            self._queue.reschedule(job)
                    else:
                        job.status = JobStatus.FAILED

                # Reschedule recurring jobs
                if result.success and job.job_type in (JobType.CRON, JobType.INTERVAL):
                    if job.trigger:
                        job.trigger.update_after_run()
                        job.status = JobStatus.SCHEDULED
                        self._queue.reschedule(job)

            except Exception as e:
                logger.error(f"Job execution error: {e}")
                job.status = JobStatus.FAILED

    # ========================================================================
    # EXECUTION
    # ========================================================================

    async def run_now(self, job_id: str) -> Optional[JobResult]:
        """Run a job immediately."""
        job = self._queue.get(job_id)

        if not job:
            return None

        return await self._executor.execute(job)

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job."""
        return await self._executor.cancel(job_id)

    def is_running(self, job_id: str) -> bool:
        """Check if a job is running."""
        return self._executor.is_running(job_id)

    def get_history(self, job_id: str, limit: int = 10) -> List[JobResult]:
        """Get job execution history."""
        return self._executor.get_history(job_id, limit)

    # ========================================================================
    # STATUS
    # ========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        jobs = self._queue.all()

        return {
            'running': self._running,
            'total_jobs': len(jobs),
            'scheduled_jobs': sum(1 for j in jobs if j.status == JobStatus.SCHEDULED),
            'running_jobs': sum(1 for j in jobs if j.status == JobStatus.RUNNING),
            'failed_jobs': sum(1 for j in jobs if j.status == JobStatus.FAILED),
            'next_run': self._queue.peek(),
        }


# ============================================================================
# CONVENIENCE DECORATORS
# ============================================================================

def cron(expression: str, **kwargs):
    """Decorator to schedule a function with cron."""
    def decorator(func):
        scheduler_engine.add_cron_job(
            name=func.__name__,
            handler=func,
            cron_expression=expression,
            is_async=asyncio.iscoroutinefunction(func),
            **kwargs
        )
        return func
    return decorator


def interval(seconds: float, **kwargs):
    """Decorator to schedule a function with interval."""
    def decorator(func):
        scheduler_engine.add_interval_job(
            name=func.__name__,
            handler=func,
            interval_seconds=seconds,
            is_async=asyncio.iscoroutinefunction(func),
            **kwargs
        )
        return func
    return decorator


# ============================================================================
# CONVENIENCE INSTANCE
# ============================================================================

scheduler_engine = SchedulerEngine()
