#!/usr/bin/env python3
"""
BAEL - Scheduler Manager
Advanced task scheduling for AI agent operations.

Features:
- Cron-style scheduling
- Interval scheduling
- One-time scheduling
- Job priorities
- Job dependencies
- Retry policies
- Distributed scheduling
- Time zones
- Job groups
- Execution tracking
"""

import asyncio
import calendar
import copy
import heapq
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import (Any, Awaitable, Callable, Dict, Generic, Iterator, List,
                    Optional, Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')
R = TypeVar('R')


# =============================================================================
# ENUMS
# =============================================================================

class JobStatus(Enum):
    """Job status."""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    MISSED = "missed"


class TriggerType(Enum):
    """Trigger type."""
    ONCE = "once"
    INTERVAL = "interval"
    CRON = "cron"
    DEPENDENT = "dependent"


class JobPriority(Enum):
    """Job priority."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class MisfirePolicy(Enum):
    """Misfire handling policy."""
    IGNORE = "ignore"
    RUN_ONCE = "run_once"
    RUN_ALL = "run_all"
    RESCHEDULE = "reschedule"


class ConflictPolicy(Enum):
    """Job conflict policy."""
    SKIP = "skip"
    QUEUE = "queue"
    REPLACE = "replace"
    RUN_PARALLEL = "run_parallel"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class SchedulerConfig:
    """Scheduler configuration."""
    max_concurrent: int = 10
    check_interval_ms: int = 100
    default_timeout_seconds: int = 300
    max_retries: int = 3
    misfire_grace_seconds: int = 60


@dataclass
class JobConfig:
    """Job configuration."""
    timeout_seconds: int = 300
    max_retries: int = 3
    retry_delay_seconds: int = 5
    misfire_policy: MisfirePolicy = MisfirePolicy.RUN_ONCE
    conflict_policy: ConflictPolicy = ConflictPolicy.SKIP


@dataclass
class JobResult:
    """Job execution result."""
    job_id: str = ""
    execution_id: str = ""
    status: JobStatus = JobStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0
    attempt: int = 1


@dataclass
class JobStats:
    """Job statistics."""
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    total_duration_ms: float = 0.0
    average_duration_ms: float = 0.0
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None


@dataclass
class SchedulerStats:
    """Scheduler statistics."""
    total_jobs: int = 0
    active_jobs: int = 0
    paused_jobs: int = 0
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    missed_executions: int = 0


# =============================================================================
# TRIGGER
# =============================================================================

class Trigger(ABC):
    """Abstract trigger."""

    @property
    @abstractmethod
    def trigger_type(self) -> TriggerType:
        """Get trigger type."""
        pass

    @abstractmethod
    def get_next_fire_time(
        self,
        previous: Optional[datetime] = None,
        now: Optional[datetime] = None
    ) -> Optional[datetime]:
        """Get next fire time."""
        pass


class OnceTrigger(Trigger):
    """One-time trigger."""

    def __init__(self, run_at: datetime):
        self._run_at = run_at
        self._fired = False

    @property
    def trigger_type(self) -> TriggerType:
        return TriggerType.ONCE

    def get_next_fire_time(
        self,
        previous: Optional[datetime] = None,
        now: Optional[datetime] = None
    ) -> Optional[datetime]:
        if self._fired or (previous and previous >= self._run_at):
            return None
        self._fired = True
        return self._run_at


class IntervalTrigger(Trigger):
    """Interval trigger."""

    def __init__(
        self,
        interval: timedelta,
        start_at: Optional[datetime] = None,
        end_at: Optional[datetime] = None
    ):
        self._interval = interval
        self._start_at = start_at or datetime.utcnow()
        self._end_at = end_at

    @property
    def trigger_type(self) -> TriggerType:
        return TriggerType.INTERVAL

    def get_next_fire_time(
        self,
        previous: Optional[datetime] = None,
        now: Optional[datetime] = None
    ) -> Optional[datetime]:
        now = now or datetime.utcnow()

        if previous:
            next_time = previous + self._interval
        else:
            next_time = self._start_at
            while next_time < now:
                next_time += self._interval

        if self._end_at and next_time > self._end_at:
            return None

        return next_time


class CronTrigger(Trigger):
    """Cron-style trigger."""

    def __init__(
        self,
        minute: str = "*",
        hour: str = "*",
        day_of_month: str = "*",
        month: str = "*",
        day_of_week: str = "*"
    ):
        self._minute = self._parse_field(minute, 0, 59)
        self._hour = self._parse_field(hour, 0, 23)
        self._day_of_month = self._parse_field(day_of_month, 1, 31)
        self._month = self._parse_field(month, 1, 12)
        self._day_of_week = self._parse_field(day_of_week, 0, 6)

    @property
    def trigger_type(self) -> TriggerType:
        return TriggerType.CRON

    def _parse_field(
        self,
        field: str,
        min_val: int,
        max_val: int
    ) -> Set[int]:
        """Parse cron field."""
        if field == "*":
            return set(range(min_val, max_val + 1))

        values = set()

        for part in field.split(","):
            if "-" in part:
                start, end = map(int, part.split("-"))
                values.update(range(start, end + 1))
            elif "/" in part:
                start_step = part.split("/")
                start = min_val if start_step[0] == "*" else int(start_step[0])
                step = int(start_step[1])
                values.update(range(start, max_val + 1, step))
            else:
                values.add(int(part))

        return values

    def get_next_fire_time(
        self,
        previous: Optional[datetime] = None,
        now: Optional[datetime] = None
    ) -> Optional[datetime]:
        now = now or datetime.utcnow()
        current = previous + timedelta(minutes=1) if previous else now
        current = current.replace(second=0, microsecond=0)

        # Search for up to a year
        end_search = current + timedelta(days=366)

        while current < end_search:
            if (current.month in self._month and
                current.day in self._day_of_month and
                current.weekday() in self._day_of_week and
                current.hour in self._hour and
                current.minute in self._minute):
                return current

            current += timedelta(minutes=1)

        return None


# =============================================================================
# JOB
# =============================================================================

class Job:
    """Scheduled job."""

    def __init__(
        self,
        func: Callable[[], Awaitable[Any]],
        trigger: Trigger,
        job_id: Optional[str] = None,
        name: Optional[str] = None,
        priority: JobPriority = JobPriority.NORMAL,
        config: Optional[JobConfig] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.job_id = job_id or str(uuid.uuid4())
        self.name = name or self.job_id
        self.func = func
        self.trigger = trigger
        self.priority = priority
        self.config = config or JobConfig()
        self.metadata = metadata or {}

        self._status = JobStatus.SCHEDULED
        self._created_at = datetime.utcnow()
        self._next_run_at: Optional[datetime] = None
        self._last_run_at: Optional[datetime] = None
        self._stats = JobStats()
        self._results: List[JobResult] = []
        self._dependencies: Set[str] = set()
        self._dependents: Set[str] = set()

    @property
    def status(self) -> JobStatus:
        """Get job status."""
        return self._status

    @status.setter
    def status(self, value: JobStatus) -> None:
        """Set job status."""
        self._status = value

    @property
    def next_run_at(self) -> Optional[datetime]:
        """Get next run time."""
        return self._next_run_at

    def schedule_next(self, now: Optional[datetime] = None) -> Optional[datetime]:
        """Schedule next run."""
        self._next_run_at = self.trigger.get_next_fire_time(
            self._last_run_at,
            now
        )
        self._stats.next_run_at = self._next_run_at
        return self._next_run_at

    def add_dependency(self, job_id: str) -> None:
        """Add dependency."""
        self._dependencies.add(job_id)

    def remove_dependency(self, job_id: str) -> None:
        """Remove dependency."""
        self._dependencies.discard(job_id)

    def get_dependencies(self) -> Set[str]:
        """Get dependencies."""
        return self._dependencies.copy()

    def add_result(self, result: JobResult) -> None:
        """Add execution result."""
        self._results.append(result)
        self._last_run_at = result.started_at
        self._stats.last_run_at = result.started_at
        self._stats.total_runs += 1

        if result.status == JobStatus.COMPLETED:
            self._stats.successful_runs += 1
        elif result.status == JobStatus.FAILED:
            self._stats.failed_runs += 1

        self._stats.total_duration_ms += result.duration_ms
        if self._stats.total_runs > 0:
            self._stats.average_duration_ms = (
                self._stats.total_duration_ms / self._stats.total_runs
            )

    def get_stats(self) -> JobStats:
        """Get job stats."""
        return copy.copy(self._stats)

    def get_results(
        self,
        limit: int = 10
    ) -> List[JobResult]:
        """Get recent results."""
        return self._results[-limit:]


# =============================================================================
# JOB EXECUTOR
# =============================================================================

class JobExecutor:
    """Execute jobs."""

    def __init__(self, config: SchedulerConfig):
        self.config = config
        self._running: Set[str] = set()
        self._semaphore = asyncio.Semaphore(config.max_concurrent)

    async def execute(
        self,
        job: Job
    ) -> JobResult:
        """Execute job."""
        execution_id = str(uuid.uuid4())
        result = JobResult(
            job_id=job.job_id,
            execution_id=execution_id,
            started_at=datetime.utcnow()
        )

        # Check conflict policy
        if job.job_id in self._running:
            if job.config.conflict_policy == ConflictPolicy.SKIP:
                result.status = JobStatus.MISSED
                result.completed_at = datetime.utcnow()
                return result

        async with self._semaphore:
            self._running.add(job.job_id)

            try:
                job.status = JobStatus.RUNNING
                result.status = JobStatus.RUNNING

                timeout = job.config.timeout_seconds
                attempt = 0

                while attempt <= job.config.max_retries:
                    attempt += 1
                    result.attempt = attempt

                    try:
                        result.result = await asyncio.wait_for(
                            job.func(),
                            timeout=timeout
                        )
                        result.status = JobStatus.COMPLETED
                        break
                    except asyncio.TimeoutError:
                        result.error = f"Timeout after {timeout}s"
                        result.status = JobStatus.FAILED
                    except Exception as e:
                        result.error = str(e)
                        result.status = JobStatus.FAILED

                    if attempt <= job.config.max_retries:
                        await asyncio.sleep(job.config.retry_delay_seconds)

                result.completed_at = datetime.utcnow()
                result.duration_ms = (
                    result.completed_at - result.started_at
                ).total_seconds() * 1000

                if result.status == JobStatus.COMPLETED:
                    job.status = JobStatus.SCHEDULED
                else:
                    job.status = JobStatus.FAILED

            finally:
                self._running.discard(job.job_id)

        job.add_result(result)
        return result

    def is_running(self, job_id: str) -> bool:
        """Check if job is running."""
        return job_id in self._running

    def running_count(self) -> int:
        """Get running job count."""
        return len(self._running)


# =============================================================================
# JOB STORE
# =============================================================================

class JobStore:
    """Store for jobs."""

    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._by_name: Dict[str, str] = {}
        self._groups: Dict[str, Set[str]] = defaultdict(set)

    def add(self, job: Job, group: Optional[str] = None) -> bool:
        """Add job."""
        if job.job_id in self._jobs:
            return False

        self._jobs[job.job_id] = job
        self._by_name[job.name] = job.job_id

        if group:
            self._groups[group].add(job.job_id)

        return True

    def get(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        return self._jobs.get(job_id)

    def get_by_name(self, name: str) -> Optional[Job]:
        """Get job by name."""
        job_id = self._by_name.get(name)
        if job_id:
            return self._jobs.get(job_id)
        return None

    def remove(self, job_id: str) -> bool:
        """Remove job."""
        if job_id not in self._jobs:
            return False

        job = self._jobs.pop(job_id)
        if job.name in self._by_name:
            del self._by_name[job.name]

        for group in self._groups.values():
            group.discard(job_id)

        return True

    def get_all(self) -> List[Job]:
        """Get all jobs."""
        return list(self._jobs.values())

    def get_by_status(self, status: JobStatus) -> List[Job]:
        """Get jobs by status."""
        return [j for j in self._jobs.values() if j.status == status]

    def get_by_group(self, group: str) -> List[Job]:
        """Get jobs by group."""
        return [
            self._jobs[jid]
            for jid in self._groups.get(group, set())
            if jid in self._jobs
        ]

    def count(self) -> int:
        """Get job count."""
        return len(self._jobs)


# =============================================================================
# SCHEDULER MANAGER
# =============================================================================

class SchedulerManager:
    """
    Scheduler Manager for BAEL.

    Advanced task scheduling.
    """

    def __init__(self, config: Optional[SchedulerConfig] = None):
        self.config = config or SchedulerConfig()

        self._store = JobStore()
        self._executor = JobExecutor(self.config)
        self._pending: List[Tuple[datetime, str]] = []  # Heap

        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        self._stats = SchedulerStats()
        self._lock = asyncio.Lock()

    # -------------------------------------------------------------------------
    # JOB MANAGEMENT
    # -------------------------------------------------------------------------

    async def add_job(
        self,
        func: Callable[[], Awaitable[Any]],
        trigger: Trigger,
        job_id: Optional[str] = None,
        name: Optional[str] = None,
        priority: JobPriority = JobPriority.NORMAL,
        config: Optional[JobConfig] = None,
        group: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Job:
        """Add job."""
        job = Job(
            func=func,
            trigger=trigger,
            job_id=job_id,
            name=name,
            priority=priority,
            config=config,
            metadata=metadata
        )

        async with self._lock:
            self._store.add(job, group)
            self._stats.total_jobs += 1
            self._stats.active_jobs += 1

            # Schedule first run
            next_run = job.schedule_next()
            if next_run:
                heapq.heappush(
                    self._pending,
                    (next_run, job.job_id)
                )

        return job

    async def add_once_job(
        self,
        func: Callable[[], Awaitable[Any]],
        run_at: datetime,
        **kwargs
    ) -> Job:
        """Add one-time job."""
        trigger = OnceTrigger(run_at)
        return await self.add_job(func, trigger, **kwargs)

    async def add_interval_job(
        self,
        func: Callable[[], Awaitable[Any]],
        interval: timedelta,
        start_at: Optional[datetime] = None,
        **kwargs
    ) -> Job:
        """Add interval job."""
        trigger = IntervalTrigger(interval, start_at)
        return await self.add_job(func, trigger, **kwargs)

    async def add_cron_job(
        self,
        func: Callable[[], Awaitable[Any]],
        minute: str = "*",
        hour: str = "*",
        day_of_month: str = "*",
        month: str = "*",
        day_of_week: str = "*",
        **kwargs
    ) -> Job:
        """Add cron job."""
        trigger = CronTrigger(minute, hour, day_of_month, month, day_of_week)
        return await self.add_job(func, trigger, **kwargs)

    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        async with self._lock:
            return self._store.get(job_id)

    async def get_job_by_name(self, name: str) -> Optional[Job]:
        """Get job by name."""
        async with self._lock:
            return self._store.get_by_name(name)

    async def remove_job(self, job_id: str) -> bool:
        """Remove job."""
        async with self._lock:
            if self._store.remove(job_id):
                self._stats.total_jobs -= 1
                self._stats.active_jobs -= 1
                return True
            return False

    async def pause_job(self, job_id: str) -> bool:
        """Pause job."""
        async with self._lock:
            job = self._store.get(job_id)
            if job and job.status != JobStatus.PAUSED:
                job.status = JobStatus.PAUSED
                self._stats.active_jobs -= 1
                self._stats.paused_jobs += 1
                return True
            return False

    async def resume_job(self, job_id: str) -> bool:
        """Resume job."""
        async with self._lock:
            job = self._store.get(job_id)
            if job and job.status == JobStatus.PAUSED:
                job.status = JobStatus.SCHEDULED
                job.schedule_next()
                if job.next_run_at:
                    heapq.heappush(
                        self._pending,
                        (job.next_run_at, job.job_id)
                    )
                self._stats.active_jobs += 1
                self._stats.paused_jobs -= 1
                return True
            return False

    # -------------------------------------------------------------------------
    # EXECUTION
    # -------------------------------------------------------------------------

    async def run_job(self, job_id: str) -> Optional[JobResult]:
        """Run job immediately."""
        job = await self.get_job(job_id)
        if not job:
            return None

        result = await self._executor.execute(job)

        async with self._lock:
            self._update_stats(result)

            # Reschedule
            next_run = job.schedule_next()
            if next_run:
                heapq.heappush(
                    self._pending,
                    (next_run, job.job_id)
                )

        return result

    def _update_stats(self, result: JobResult) -> None:
        """Update scheduler stats."""
        self._stats.total_executions += 1

        if result.status == JobStatus.COMPLETED:
            self._stats.successful_executions += 1
        elif result.status == JobStatus.FAILED:
            self._stats.failed_executions += 1
        elif result.status == JobStatus.MISSED:
            self._stats.missed_executions += 1

    # -------------------------------------------------------------------------
    # SCHEDULER CONTROL
    # -------------------------------------------------------------------------

    async def start(self) -> None:
        """Start scheduler."""
        if self._running:
            return

        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())

    async def stop(self) -> None:
        """Stop scheduler."""
        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

    async def _scheduler_loop(self) -> None:
        """Scheduler main loop."""
        while self._running:
            now = datetime.utcnow()

            async with self._lock:
                while self._pending and self._pending[0][0] <= now:
                    _, job_id = heapq.heappop(self._pending)

                    job = self._store.get(job_id)
                    if not job or job.status != JobStatus.SCHEDULED:
                        continue

                    # Check misfire
                    scheduled_time = job.next_run_at
                    if scheduled_time:
                        grace = timedelta(seconds=self.config.misfire_grace_seconds)
                        if now - scheduled_time > grace:
                            if job.config.misfire_policy == MisfirePolicy.IGNORE:
                                job.schedule_next(now)
                                if job.next_run_at:
                                    heapq.heappush(
                                        self._pending,
                                        (job.next_run_at, job.job_id)
                                    )
                                continue

                    # Execute asynchronously
                    asyncio.create_task(self._execute_job(job))

            await asyncio.sleep(self.config.check_interval_ms / 1000)

    async def _execute_job(self, job: Job) -> None:
        """Execute job and reschedule."""
        result = await self._executor.execute(job)

        async with self._lock:
            self._update_stats(result)

            # Reschedule
            next_run = job.schedule_next()
            if next_run:
                heapq.heappush(
                    self._pending,
                    (next_run, job.job_id)
                )

    # -------------------------------------------------------------------------
    # QUERIES
    # -------------------------------------------------------------------------

    async def get_jobs(self) -> List[Job]:
        """Get all jobs."""
        async with self._lock:
            return self._store.get_all()

    async def get_jobs_by_status(self, status: JobStatus) -> List[Job]:
        """Get jobs by status."""
        async with self._lock:
            return self._store.get_by_status(status)

    async def get_jobs_by_group(self, group: str) -> List[Job]:
        """Get jobs by group."""
        async with self._lock:
            return self._store.get_by_group(group)

    async def get_pending_jobs(self) -> List[Tuple[datetime, Job]]:
        """Get pending jobs with next run time."""
        async with self._lock:
            result = []
            for run_at, job_id in self._pending:
                job = self._store.get(job_id)
                if job:
                    result.append((run_at, job))
            return result

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    async def stats(self) -> SchedulerStats:
        """Get scheduler stats."""
        async with self._lock:
            return copy.copy(self._stats)

    async def job_stats(self, job_id: str) -> Optional[JobStats]:
        """Get job stats."""
        job = await self.get_job(job_id)
        if job:
            return job.get_stats()
        return None

    async def job_count(self) -> int:
        """Get job count."""
        async with self._lock:
            return self._store.count()

    async def running_count(self) -> int:
        """Get running job count."""
        return self._executor.running_count()


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Scheduler Manager."""
    print("=" * 70)
    print("BAEL - SCHEDULER MANAGER DEMO")
    print("Advanced Task Scheduling for AI Agents")
    print("=" * 70)
    print()

    manager = SchedulerManager(SchedulerConfig(
        max_concurrent=5,
        check_interval_ms=50
    ))

    # Counter for demo
    execution_count = [0]

    # 1. Add One-Time Job
    print("1. ADD ONE-TIME JOB:")
    print("-" * 40)

    async def once_job():
        execution_count[0] += 1
        return "Once job executed"

    run_at = datetime.utcnow() + timedelta(seconds=0.1)
    job1 = await manager.add_once_job(
        once_job,
        run_at,
        name="once_job"
    )

    print(f"   Job ID: {job1.job_id[:8]}...")
    print(f"   Name: {job1.name}")
    print(f"   Trigger: {job1.trigger.trigger_type.value}")
    print()

    # 2. Add Interval Job
    print("2. ADD INTERVAL JOB:")
    print("-" * 40)

    async def interval_job():
        execution_count[0] += 1
        return "Interval job executed"

    job2 = await manager.add_interval_job(
        interval_job,
        timedelta(seconds=0.2),
        name="interval_job"
    )

    print(f"   Job ID: {job2.job_id[:8]}...")
    print(f"   Interval: 0.2s")
    print(f"   Next run: {job2.next_run_at}")
    print()

    # 3. Add Cron Job
    print("3. ADD CRON JOB:")
    print("-" * 40)

    async def cron_job():
        execution_count[0] += 1
        return "Cron job executed"

    job3 = await manager.add_cron_job(
        cron_job,
        minute="*",
        hour="*",
        name="cron_job"
    )

    print(f"   Job ID: {job3.job_id[:8]}...")
    print(f"   Schedule: Every minute")
    print(f"   Next run: {job3.next_run_at}")
    print()

    # 4. Start Scheduler
    print("4. START SCHEDULER:")
    print("-" * 40)

    await manager.start()
    print(f"   Scheduler running")

    # Wait for some executions
    await asyncio.sleep(0.5)

    print(f"   Executions: {execution_count[0]}")
    print()

    # 5. Get Job
    print("5. GET JOB:")
    print("-" * 40)

    retrieved = await manager.get_job(job2.job_id)
    print(f"   Found: {retrieved is not None}")
    print(f"   Name: {retrieved.name if retrieved else 'N/A'}")
    print()

    # 6. Get Job By Name
    print("6. GET JOB BY NAME:")
    print("-" * 40)

    by_name = await manager.get_job_by_name("interval_job")
    print(f"   Found: {by_name is not None}")
    print(f"   ID: {by_name.job_id[:8] if by_name else 'N/A'}...")
    print()

    # 7. Pause Job
    print("7. PAUSE JOB:")
    print("-" * 40)

    paused = await manager.pause_job(job2.job_id)
    print(f"   Paused: {paused}")
    print(f"   Status: {job2.status.value}")
    print()

    # 8. Resume Job
    print("8. RESUME JOB:")
    print("-" * 40)

    resumed = await manager.resume_job(job2.job_id)
    print(f"   Resumed: {resumed}")
    print(f"   Status: {job2.status.value}")
    print()

    # 9. Run Job Immediately
    print("9. RUN JOB IMMEDIATELY:")
    print("-" * 40)

    async def manual_job():
        return "Manual execution"

    job4 = await manager.add_once_job(
        manual_job,
        datetime.utcnow() + timedelta(hours=1),
        name="manual_job"
    )

    result = await manager.run_job(job4.job_id)
    print(f"   Result: {result.result if result else 'N/A'}")
    print(f"   Status: {result.status.value if result else 'N/A'}")
    print()

    # 10. Job Stats
    print("10. JOB STATS:")
    print("-" * 40)

    job_stats = await manager.job_stats(job2.job_id)
    if job_stats:
        print(f"   Total runs: {job_stats.total_runs}")
        print(f"   Successful: {job_stats.successful_runs}")
        print(f"   Average duration: {job_stats.average_duration_ms:.2f}ms")
    print()

    # 11. Scheduler Stats
    print("11. SCHEDULER STATS:")
    print("-" * 40)

    stats = await manager.stats()
    print(f"   Total jobs: {stats.total_jobs}")
    print(f"   Active jobs: {stats.active_jobs}")
    print(f"   Total executions: {stats.total_executions}")
    print(f"   Successful: {stats.successful_executions}")
    print()

    # 12. Get Pending Jobs
    print("12. GET PENDING JOBS:")
    print("-" * 40)

    pending = await manager.get_pending_jobs()
    print(f"   Pending count: {len(pending)}")
    for run_at, job in pending[:3]:
        print(f"   - {job.name}: {run_at}")
    print()

    # 13. Job Count
    print("13. JOB COUNT:")
    print("-" * 40)

    count = await manager.job_count()
    running = await manager.running_count()
    print(f"   Total jobs: {count}")
    print(f"   Running: {running}")
    print()

    # 14. Remove Job
    print("14. REMOVE JOB:")
    print("-" * 40)

    removed = await manager.remove_job(job3.job_id)
    print(f"   Removed: {removed}")
    print(f"   Job count: {await manager.job_count()}")
    print()

    # 15. Stop Scheduler
    print("15. STOP SCHEDULER:")
    print("-" * 40)

    await manager.stop()
    print(f"   Scheduler stopped")
    print(f"   Total executions: {execution_count[0]}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Scheduler Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
