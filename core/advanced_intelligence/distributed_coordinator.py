"""
BAEL Distributed Computing Coordinator
========================================

Coordinate distributed computation across multiple workers.

"Divide to conquer, unite to triumph." — Ba'el
"""

import asyncio
import hashlib
import json
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import (
    Any, Callable, Dict, List, Optional, Set, Tuple, Union,
    TypeVar, Generic, AsyncIterator, Awaitable
)
from collections import defaultdict
import heapq
import uuid


class WorkerState(Enum):
    """States a worker can be in."""
    IDLE = "idle"
    BUSY = "busy"
    PAUSED = "paused"
    ERROR = "error"
    OFFLINE = "offline"
    STARTING = "starting"
    STOPPING = "stopping"


class TaskState(Enum):
    """States a task can be in."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskPriority(Enum):
    """Task priority levels."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class SchedulingStrategy(Enum):
    """How to schedule tasks."""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    RANDOM = "random"
    PRIORITY = "priority"
    AFFINITY = "affinity"
    ADAPTIVE = "adaptive"


class PartitionStrategy(Enum):
    """How to partition work."""
    EQUAL = "equal"
    WEIGHTED = "weighted"
    DYNAMIC = "dynamic"
    HASH = "hash"
    RANGE = "range"


@dataclass
class Worker:
    """A compute worker."""
    id: str
    name: str
    state: WorkerState = WorkerState.IDLE
    capacity: int = 10
    current_load: int = 0
    specializations: List[str] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_heartbeat: datetime = field(default_factory=datetime.now)
    tasks_completed: int = 0
    tasks_failed: int = 0

    @property
    def is_available(self) -> bool:
        return self.state == WorkerState.IDLE and self.current_load < self.capacity

    @property
    def load_ratio(self) -> float:
        return self.current_load / self.capacity if self.capacity > 0 else 1.0


@dataclass
class Task:
    """A unit of work."""
    id: str
    name: str
    payload: Dict[str, Any]
    handler: str
    priority: TaskPriority = TaskPriority.NORMAL
    state: TaskState = TaskState.PENDING
    worker_id: Optional[str] = None
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    result: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 300
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() * 1000
        return 0


@dataclass
class TaskGroup:
    """A group of related tasks."""
    id: str
    name: str
    task_ids: List[str]
    parallel: bool = True
    completed_count: int = 0
    failed_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def total_count(self) -> int:
        return len(self.task_ids)

    @property
    def progress(self) -> float:
        return (self.completed_count + self.failed_count) / self.total_count if self.total_count > 0 else 0


@dataclass
class ComputeResult:
    """Result of distributed computation."""
    task_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    worker_id: Optional[str] = None
    duration_ms: float = 0
    retries: int = 0


@dataclass
class DistributedJobResult:
    """Result of a distributed job."""
    job_id: str
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    results: List[ComputeResult]
    duration_ms: float
    workers_used: int


class TaskQueue:
    """Priority-based task queue."""

    def __init__(self):
        self._queue: List[Tuple[int, float, str]] = []  # (priority, timestamp, task_id)
        self._tasks: Dict[str, Task] = {}

    def push(self, task: Task) -> None:
        """Add task to queue."""
        entry = (task.priority.value, time.time(), task.id)
        heapq.heappush(self._queue, entry)
        self._tasks[task.id] = task
        task.state = TaskState.QUEUED

    def pop(self) -> Optional[Task]:
        """Get highest priority task."""
        while self._queue:
            _, _, task_id = heapq.heappop(self._queue)
            if task_id in self._tasks:
                task = self._tasks.pop(task_id)
                return task
        return None

    def peek(self) -> Optional[Task]:
        """View next task without removing."""
        while self._queue:
            _, _, task_id = self._queue[0]
            if task_id in self._tasks:
                return self._tasks[task_id]
            heapq.heappop(self._queue)
        return None

    def remove(self, task_id: str) -> bool:
        """Remove a task from queue."""
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False

    def __len__(self) -> int:
        return len(self._tasks)

    @property
    def is_empty(self) -> bool:
        return len(self._tasks) == 0


class WorkerPool:
    """Manage a pool of workers."""

    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self.workers: Dict[str, Worker] = {}
        self.worker_stats: Dict[str, Dict[str, Any]] = {}

    async def add_worker(
        self,
        name: Optional[str] = None,
        capacity: int = 10,
        specializations: Optional[List[str]] = None
    ) -> Worker:
        """Add a worker to the pool."""
        worker_id = str(uuid.uuid4())[:8]

        worker = Worker(
            id=worker_id,
            name=name or f"worker-{worker_id}",
            capacity=capacity,
            specializations=specializations or [],
            state=WorkerState.STARTING
        )

        self.workers[worker_id] = worker
        self.worker_stats[worker_id] = {
            "tasks_assigned": 0,
            "avg_task_duration_ms": 0,
            "total_duration_ms": 0
        }

        # Simulate startup
        await asyncio.sleep(0.01)
        worker.state = WorkerState.IDLE

        return worker

    async def remove_worker(self, worker_id: str) -> bool:
        """Remove a worker from the pool."""
        if worker_id in self.workers:
            self.workers[worker_id].state = WorkerState.STOPPING
            await asyncio.sleep(0.01)
            del self.workers[worker_id]
            return True
        return False

    def get_available_workers(self) -> List[Worker]:
        """Get all available workers."""
        return [w for w in self.workers.values() if w.is_available]

    def get_worker_by_specialization(self, spec: str) -> Optional[Worker]:
        """Get an available worker with a specialization."""
        for worker in self.workers.values():
            if worker.is_available and spec in worker.specializations:
                return worker
        return None

    def get_least_loaded_worker(self) -> Optional[Worker]:
        """Get the worker with lowest load."""
        available = self.get_available_workers()
        if not available:
            return None
        return min(available, key=lambda w: w.load_ratio)

    def update_heartbeat(self, worker_id: str) -> None:
        """Update worker heartbeat."""
        if worker_id in self.workers:
            self.workers[worker_id].last_heartbeat = datetime.now()

    async def check_health(self) -> Dict[str, Any]:
        """Check health of all workers."""
        now = datetime.now()
        healthy = 0
        unhealthy = 0

        for worker in self.workers.values():
            time_since_heartbeat = (now - worker.last_heartbeat).total_seconds()
            if time_since_heartbeat > 30:
                worker.state = WorkerState.OFFLINE
                unhealthy += 1
            elif worker.state not in (WorkerState.ERROR, WorkerState.OFFLINE):
                healthy += 1
            else:
                unhealthy += 1

        return {
            "total": len(self.workers),
            "healthy": healthy,
            "unhealthy": unhealthy,
            "available": len(self.get_available_workers())
        }


class TaskScheduler:
    """Schedule tasks to workers."""

    def __init__(
        self,
        worker_pool: WorkerPool,
        strategy: SchedulingStrategy = SchedulingStrategy.LEAST_LOADED
    ):
        self.pool = worker_pool
        self.strategy = strategy
        self._round_robin_index = 0

    async def schedule(self, task: Task) -> Optional[Worker]:
        """Schedule a task to a worker."""
        worker = None

        if self.strategy == SchedulingStrategy.ROUND_ROBIN:
            worker = await self._round_robin_schedule()
        elif self.strategy == SchedulingStrategy.LEAST_LOADED:
            worker = self.pool.get_least_loaded_worker()
        elif self.strategy == SchedulingStrategy.RANDOM:
            available = self.pool.get_available_workers()
            if available:
                worker = random.choice(available)
        elif self.strategy == SchedulingStrategy.AFFINITY:
            # Check for specialization match
            handler = task.handler
            worker = self.pool.get_worker_by_specialization(handler)
            if not worker:
                worker = self.pool.get_least_loaded_worker()
        elif self.strategy == SchedulingStrategy.ADAPTIVE:
            worker = await self._adaptive_schedule(task)
        else:
            worker = self.pool.get_least_loaded_worker()

        if worker:
            task.worker_id = worker.id
            worker.current_load += 1
            if worker.current_load >= worker.capacity:
                worker.state = WorkerState.BUSY

        return worker

    async def _round_robin_schedule(self) -> Optional[Worker]:
        """Round-robin scheduling."""
        available = self.pool.get_available_workers()
        if not available:
            return None

        worker = available[self._round_robin_index % len(available)]
        self._round_robin_index += 1
        return worker

    async def _adaptive_schedule(self, task: Task) -> Optional[Worker]:
        """Adaptive scheduling based on task characteristics."""
        available = self.pool.get_available_workers()
        if not available:
            return None

        # Score each worker
        scored_workers = []
        for worker in available:
            score = 0.0

            # Lower load is better
            score += (1 - worker.load_ratio) * 3

            # Specialization match
            if task.handler in worker.specializations:
                score += 2

            # Success rate
            if worker.tasks_completed + worker.tasks_failed > 0:
                success_rate = worker.tasks_completed / (worker.tasks_completed + worker.tasks_failed)
                score += success_rate * 2

            scored_workers.append((worker, score))

        # Return highest scored
        scored_workers.sort(key=lambda x: -x[1])
        return scored_workers[0][0]


class DistributedCoordinator:
    """
    The ultimate distributed computing coordinator.

    Manages workers, schedules tasks, handles failures,
    and coordinates distributed computation.
    """

    def __init__(
        self,
        max_workers: int = 10,
        scheduling_strategy: SchedulingStrategy = SchedulingStrategy.ADAPTIVE
    ):
        self.pool = WorkerPool(max_workers)
        self.queue = TaskQueue()
        self.scheduler = TaskScheduler(self.pool, scheduling_strategy)

        self.tasks: Dict[str, Task] = {}
        self.groups: Dict[str, TaskGroup] = {}
        self.handlers: Dict[str, Callable] = {}

        self._running = False
        self._processing_task: Optional[asyncio.Task] = None

        self.data_dir = Path("data/distributed")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Stats
        self.stats = {
            "tasks_submitted": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "total_duration_ms": 0
        }

    def register_handler(
        self,
        name: str,
        handler: Callable[[Dict[str, Any]], Awaitable[Any]]
    ) -> None:
        """Register a task handler."""
        self.handlers[name] = handler

    async def start(self, initial_workers: int = 4) -> None:
        """Start the coordinator."""
        self._running = True

        # Create initial workers
        for i in range(initial_workers):
            await self.pool.add_worker(
                name=f"worker-{i}",
                capacity=10
            )

        # Start processing loop
        self._processing_task = asyncio.create_task(self._process_loop())

    async def stop(self) -> None:
        """Stop the coordinator."""
        self._running = False

        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass

        # Stop all workers
        for worker_id in list(self.pool.workers.keys()):
            await self.pool.remove_worker(worker_id)

    async def submit(
        self,
        name: str,
        handler: str,
        payload: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        dependencies: Optional[List[str]] = None
    ) -> Task:
        """Submit a task for execution."""
        task_id = str(uuid.uuid4())[:12]

        task = Task(
            id=task_id,
            name=name,
            handler=handler,
            payload=payload,
            priority=priority,
            dependencies=dependencies or []
        )

        self.tasks[task_id] = task
        self.stats["tasks_submitted"] += 1

        # Check dependencies
        if not dependencies or all(self._is_dependency_met(d) for d in dependencies):
            self.queue.push(task)

        return task

    async def submit_batch(
        self,
        tasks: List[Dict[str, Any]],
        parallel: bool = True
    ) -> TaskGroup:
        """Submit multiple tasks as a group."""
        group_id = str(uuid.uuid4())[:8]
        task_ids = []

        for i, task_spec in enumerate(tasks):
            task = await self.submit(
                name=task_spec.get("name", f"batch-{i}"),
                handler=task_spec["handler"],
                payload=task_spec.get("payload", {}),
                priority=TaskPriority(task_spec.get("priority", TaskPriority.NORMAL.value))
            )
            task_ids.append(task.id)

        group = TaskGroup(
            id=group_id,
            name=f"group-{group_id}",
            task_ids=task_ids,
            parallel=parallel
        )

        self.groups[group_id] = group
        return group

    async def map_reduce(
        self,
        handler: str,
        items: List[Any],
        reducer: Optional[Callable[[List[Any]], Any]] = None,
        partition_strategy: PartitionStrategy = PartitionStrategy.EQUAL
    ) -> DistributedJobResult:
        """Map-reduce style distributed computation."""
        start_time = time.time()
        job_id = str(uuid.uuid4())[:8]

        # Partition items
        partitions = await self._partition(items, partition_strategy)

        # Submit map tasks
        map_tasks = []
        for i, partition in enumerate(partitions):
            task = await self.submit(
                name=f"map-{job_id}-{i}",
                handler=handler,
                payload={"items": partition, "partition_id": i},
                priority=TaskPriority.NORMAL
            )
            map_tasks.append(task)

        # Wait for completion
        results = await self._wait_for_tasks([t.id for t in map_tasks])

        # Reduce if reducer provided
        if reducer and results:
            successful_results = [r.result for r in results if r.success and r.result is not None]
            if successful_results:
                final_result = reducer(successful_results)
            else:
                final_result = None
        else:
            final_result = [r.result for r in results]

        # Build result
        completed = len([r for r in results if r.success])
        failed = len([r for r in results if not r.success])

        return DistributedJobResult(
            job_id=job_id,
            total_tasks=len(map_tasks),
            completed_tasks=completed,
            failed_tasks=failed,
            results=results,
            duration_ms=(time.time() - start_time) * 1000,
            workers_used=len(set(r.worker_id for r in results if r.worker_id))
        )

    async def _partition(
        self,
        items: List[Any],
        strategy: PartitionStrategy
    ) -> List[List[Any]]:
        """Partition items for distribution."""
        worker_count = len(self.pool.get_available_workers()) or 1

        if strategy == PartitionStrategy.EQUAL:
            # Equal-sized partitions
            chunk_size = max(1, len(items) // worker_count)
            partitions = []
            for i in range(0, len(items), chunk_size):
                partitions.append(items[i:i + chunk_size])
            return partitions

        elif strategy == PartitionStrategy.HASH:
            # Hash-based partitioning
            partitions = [[] for _ in range(worker_count)]
            for item in items:
                partition_idx = hash(str(item)) % worker_count
                partitions[partition_idx].append(item)
            return [p for p in partitions if p]

        else:
            # Default to equal
            chunk_size = max(1, len(items) // worker_count)
            partitions = []
            for i in range(0, len(items), chunk_size):
                partitions.append(items[i:i + chunk_size])
            return partitions

    async def _wait_for_tasks(
        self,
        task_ids: List[str],
        timeout: float = 300.0
    ) -> List[ComputeResult]:
        """Wait for tasks to complete."""
        results = []
        start_time = time.time()

        while task_ids and (time.time() - start_time) < timeout:
            remaining = []

            for task_id in task_ids:
                task = self.tasks.get(task_id)
                if not task:
                    continue

                if task.state == TaskState.COMPLETED:
                    results.append(ComputeResult(
                        task_id=task.id,
                        success=True,
                        result=task.result,
                        worker_id=task.worker_id,
                        duration_ms=task.duration_ms,
                        retries=task.retry_count
                    ))
                elif task.state == TaskState.FAILED:
                    results.append(ComputeResult(
                        task_id=task.id,
                        success=False,
                        error=task.error,
                        worker_id=task.worker_id,
                        duration_ms=task.duration_ms,
                        retries=task.retry_count
                    ))
                else:
                    remaining.append(task_id)

            task_ids = remaining
            if task_ids:
                await asyncio.sleep(0.01)

        return results

    async def _process_loop(self) -> None:
        """Main processing loop."""
        while self._running:
            if self.queue.is_empty:
                await asyncio.sleep(0.01)
                continue

            # Get next task
            task = self.queue.pop()
            if not task:
                continue

            # Schedule to worker
            worker = await self.scheduler.schedule(task)
            if not worker:
                # No worker available, requeue
                self.queue.push(task)
                await asyncio.sleep(0.01)
                continue

            # Execute task asynchronously
            asyncio.create_task(self._execute_task(task, worker))

    async def _execute_task(self, task: Task, worker: Worker) -> None:
        """Execute a task on a worker."""
        task.state = TaskState.RUNNING
        task.started_at = datetime.now()

        try:
            # Get handler
            handler = self.handlers.get(task.handler)
            if not handler:
                # Default handler
                handler = self._default_handler

            # Execute with timeout
            result = await asyncio.wait_for(
                handler(task.payload),
                timeout=task.timeout_seconds
            )

            task.result = result
            task.state = TaskState.COMPLETED
            task.completed_at = datetime.now()

            worker.tasks_completed += 1
            self.stats["tasks_completed"] += 1
            self.stats["total_duration_ms"] += task.duration_ms

        except asyncio.TimeoutError:
            task.error = "Task timed out"
            task.state = TaskState.FAILED
            task.completed_at = datetime.now()
            worker.tasks_failed += 1
            self.stats["tasks_failed"] += 1

        except Exception as e:
            task.error = str(e)

            # Retry logic
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.state = TaskState.RETRYING
                task.worker_id = None
                self.queue.push(task)
            else:
                task.state = TaskState.FAILED
                task.completed_at = datetime.now()
                worker.tasks_failed += 1
                self.stats["tasks_failed"] += 1

        finally:
            # Release worker
            worker.current_load -= 1
            if worker.current_load < worker.capacity:
                worker.state = WorkerState.IDLE

            # Update group if applicable
            await self._update_group(task)

    async def _default_handler(self, payload: Dict[str, Any]) -> Any:
        """Default task handler."""
        await asyncio.sleep(0.01)  # Simulate work
        return {"processed": True, "payload": payload}

    async def _update_group(self, task: Task) -> None:
        """Update task group status."""
        for group in self.groups.values():
            if task.id in group.task_ids:
                if task.state == TaskState.COMPLETED:
                    group.completed_count += 1
                elif task.state == TaskState.FAILED:
                    group.failed_count += 1

    def _is_dependency_met(self, dep_id: str) -> bool:
        """Check if a dependency is met."""
        dep_task = self.tasks.get(dep_id)
        return dep_task is not None and dep_task.state == TaskState.COMPLETED

    async def get_status(self) -> Dict[str, Any]:
        """Get coordinator status."""
        health = await self.pool.check_health()

        return {
            "running": self._running,
            "workers": {
                "total": len(self.pool.workers),
                "healthy": health["healthy"],
                "available": health["available"]
            },
            "queue": {
                "size": len(self.queue),
                "pending": len([t for t in self.tasks.values() if t.state == TaskState.PENDING]),
                "running": len([t for t in self.tasks.values() if t.state == TaskState.RUNNING])
            },
            "stats": self.stats,
            "groups": len(self.groups)
        }

    async def scale_workers(self, target: int) -> None:
        """Scale worker pool to target size."""
        current = len(self.pool.workers)

        if target > current:
            for i in range(target - current):
                await self.pool.add_worker(
                    capacity=10
                )
        elif target < current:
            workers_to_remove = list(self.pool.workers.keys())[:current - target]
            for worker_id in workers_to_remove:
                await self.pool.remove_worker(worker_id)

    async def save_state(self, filename: str = "distributed_state.json") -> None:
        """Save coordinator state."""
        state = {
            "workers": {
                wid: {
                    "name": w.name,
                    "state": w.state.value,
                    "capacity": w.capacity,
                    "tasks_completed": w.tasks_completed,
                    "tasks_failed": w.tasks_failed
                }
                for wid, w in self.pool.workers.items()
            },
            "stats": self.stats,
            "queue_size": len(self.queue),
            "total_tasks": len(self.tasks),
            "groups": len(self.groups)
        }

        filepath = self.data_dir / filename
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)

    def get_summary(self) -> Dict[str, Any]:
        """Get coordinator summary."""
        return {
            "workers": len(self.pool.workers),
            "available_workers": len(self.pool.get_available_workers()),
            "queue_size": len(self.queue),
            "total_tasks": len(self.tasks),
            "completed_tasks": self.stats["tasks_completed"],
            "failed_tasks": self.stats["tasks_failed"],
            "success_rate": (
                self.stats["tasks_completed"] / max(self.stats["tasks_submitted"], 1)
            ),
            "avg_duration_ms": (
                self.stats["total_duration_ms"] / max(self.stats["tasks_completed"], 1)
            )
        }


# Convenience instance
distributed_coordinator = DistributedCoordinator()
