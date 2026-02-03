#!/usr/bin/env python3
"""
BAEL - Task Engine
Task decomposition, scheduling, and execution.

Features:
- Hierarchical task decomposition
- Priority scheduling
- Dependency management
- Resource allocation
- Progress tracking
"""

import asyncio
import hashlib
import heapq
import json
import random
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

class TaskStatus(Enum):
    """Task status."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority levels."""
    LOWEST = 1
    LOW = 2
    NORMAL = 3
    HIGH = 4
    HIGHEST = 5
    CRITICAL = 6


class TaskType(Enum):
    """Task types."""
    ATOMIC = "atomic"
    COMPOSITE = "composite"
    RECURRING = "recurring"
    CONDITIONAL = "conditional"
    PARALLEL = "parallel"


class SchedulingPolicy(Enum):
    """Scheduling policies."""
    FIFO = "fifo"
    PRIORITY = "priority"
    SHORTEST_FIRST = "shortest_first"
    DEADLINE = "deadline"
    ROUND_ROBIN = "round_robin"


class ResourceType(Enum):
    """Resource types."""
    CPU = "cpu"
    MEMORY = "memory"
    GPU = "gpu"
    IO = "io"
    NETWORK = "network"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class ResourceRequirement:
    """Resource requirement."""
    resource_type: ResourceType
    amount: float
    exclusive: bool = False


@dataclass
class TaskDefinition:
    """Task definition."""
    task_id: str = ""
    name: str = ""
    description: str = ""
    task_type: TaskType = TaskType.ATOMIC
    handler: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    estimated_duration: float = 60.0
    timeout: float = 300.0
    max_retries: int = 3
    dependencies: List[str] = field(default_factory=list)
    resources: List[ResourceRequirement] = field(default_factory=list)
    subtasks: List["TaskDefinition"] = field(default_factory=list)
    deadline: Optional[datetime] = None

    def __post_init__(self):
        if not self.task_id:
            self.task_id = str(uuid.uuid4())[:8]

    def __lt__(self, other: "TaskDefinition") -> bool:
        return self.priority.value > other.priority.value


@dataclass
class TaskInstance:
    """Task execution instance."""
    instance_id: str = ""
    task_id: str = ""
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    result: Any = None
    error: Optional[str] = None
    retries: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    assigned_worker: Optional[str] = None
    subtask_instances: List["TaskInstance"] = field(default_factory=list)

    def __post_init__(self):
        if not self.instance_id:
            self.instance_id = str(uuid.uuid4())[:8]


@dataclass
class TaskResult:
    """Task execution result."""
    task_id: str
    instance_id: str
    success: bool = True
    output: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    subtask_results: List["TaskResult"] = field(default_factory=list)


@dataclass
class ResourcePool:
    """Resource pool."""
    pool_id: str = ""
    resource_type: ResourceType = ResourceType.CPU
    total: float = 100.0
    available: float = 100.0
    allocated: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        if not self.pool_id:
            self.pool_id = str(uuid.uuid4())[:8]

    def allocate(self, task_id: str, amount: float) -> bool:
        if amount <= self.available:
            self.available -= amount
            self.allocated[task_id] = self.allocated.get(task_id, 0) + amount
            return True
        return False

    def release(self, task_id: str) -> float:
        amount = self.allocated.pop(task_id, 0)
        self.available += amount
        return amount


@dataclass
class TaskStats:
    """Task statistics."""
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    total_duration_ms: float = 0.0
    avg_duration_ms: float = 0.0
    by_priority: Dict[str, int] = field(default_factory=dict)
    by_type: Dict[str, int] = field(default_factory=dict)


# =============================================================================
# TASK DECOMPOSER
# =============================================================================

class TaskDecomposer:
    """Decompose tasks into subtasks."""

    def __init__(self):
        self._decomposition_rules: Dict[str, Callable] = {}

    def register_rule(
        self,
        task_type: str,
        rule: Callable[[TaskDefinition], List[TaskDefinition]]
    ) -> None:
        """Register a decomposition rule."""
        self._decomposition_rules[task_type] = rule

    def decompose(self, task: TaskDefinition) -> List[TaskDefinition]:
        """Decompose a task."""
        if task.subtasks:
            return task.subtasks

        rule = self._decomposition_rules.get(task.name)
        if rule:
            return rule(task)

        return [task]

    def create_hierarchy(
        self,
        root_task: TaskDefinition,
        max_depth: int = 5
    ) -> TaskDefinition:
        """Create task hierarchy."""
        if max_depth <= 0:
            return root_task

        subtasks = self.decompose(root_task)

        if subtasks and subtasks != [root_task]:
            root_task.subtasks = [
                self.create_hierarchy(st, max_depth - 1)
                for st in subtasks
            ]
            root_task.task_type = TaskType.COMPOSITE

        return root_task


# =============================================================================
# SCHEDULER
# =============================================================================

class TaskScheduler:
    """Schedule tasks for execution."""

    def __init__(self, policy: SchedulingPolicy = SchedulingPolicy.PRIORITY):
        self._policy = policy
        self._queue: List[Tuple[int, TaskDefinition]] = []
        self._counter = 0

    def enqueue(self, task: TaskDefinition) -> None:
        """Add task to queue."""
        priority = -task.priority.value

        if self._policy == SchedulingPolicy.SHORTEST_FIRST:
            priority = task.estimated_duration
        elif self._policy == SchedulingPolicy.DEADLINE and task.deadline:
            priority = task.deadline.timestamp()
        elif self._policy == SchedulingPolicy.FIFO:
            priority = self._counter

        heapq.heappush(self._queue, (priority, self._counter, task))
        self._counter += 1

    def dequeue(self) -> Optional[TaskDefinition]:
        """Get next task."""
        if self._queue:
            _, _, task = heapq.heappop(self._queue)
            return task
        return None

    def peek(self) -> Optional[TaskDefinition]:
        """Peek at next task."""
        if self._queue:
            return self._queue[0][2]
        return None

    @property
    def size(self) -> int:
        return len(self._queue)

    def clear(self) -> None:
        self._queue.clear()


# =============================================================================
# RESOURCE MANAGER
# =============================================================================

class ResourceManager:
    """Manage resources for tasks."""

    def __init__(self):
        self._pools: Dict[ResourceType, ResourcePool] = {}

        for rt in ResourceType:
            self._pools[rt] = ResourcePool(resource_type=rt)

    def configure_pool(
        self,
        resource_type: ResourceType,
        total: float
    ) -> None:
        """Configure a resource pool."""
        self._pools[resource_type].total = total
        self._pools[resource_type].available = total

    def allocate(
        self,
        task_id: str,
        requirements: List[ResourceRequirement]
    ) -> bool:
        """Allocate resources for a task."""
        for req in requirements:
            pool = self._pools.get(req.resource_type)
            if not pool or pool.available < req.amount:
                self.release(task_id, requirements)
                return False

        for req in requirements:
            self._pools[req.resource_type].allocate(task_id, req.amount)

        return True

    def release(
        self,
        task_id: str,
        requirements: Optional[List[ResourceRequirement]] = None
    ) -> None:
        """Release resources."""
        for pool in self._pools.values():
            pool.release(task_id)

    def get_availability(self) -> Dict[ResourceType, float]:
        """Get resource availability."""
        return {
            rt: pool.available / pool.total
            for rt, pool in self._pools.items()
        }


# =============================================================================
# DEPENDENCY RESOLVER
# =============================================================================

class DependencyResolver:
    """Resolve task dependencies."""

    def __init__(self):
        self._graph: Dict[str, Set[str]] = defaultdict(set)
        self._reverse_graph: Dict[str, Set[str]] = defaultdict(set)

    def add_dependency(self, task_id: str, depends_on: str) -> None:
        """Add a dependency."""
        self._graph[task_id].add(depends_on)
        self._reverse_graph[depends_on].add(task_id)

    def add_task(self, task: TaskDefinition) -> None:
        """Add task with dependencies."""
        for dep in task.dependencies:
            self.add_dependency(task.task_id, dep)

    def get_ready_tasks(
        self,
        completed: Set[str],
        all_tasks: Set[str]
    ) -> List[str]:
        """Get tasks ready for execution."""
        ready = []

        for task_id in all_tasks:
            if task_id in completed:
                continue

            deps = self._graph.get(task_id, set())
            if deps.issubset(completed):
                ready.append(task_id)

        return ready

    def topological_sort(self, tasks: List[str]) -> List[str]:
        """Topological sort of tasks."""
        in_degree = defaultdict(int)
        task_set = set(tasks)

        for task_id in tasks:
            for dep in self._graph.get(task_id, set()):
                if dep in task_set:
                    in_degree[task_id] += 1

        queue = deque([t for t in tasks if in_degree[t] == 0])
        result = []

        while queue:
            task_id = queue.popleft()
            result.append(task_id)

            for dependent in self._reverse_graph.get(task_id, set()):
                if dependent in task_set:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

        return result

    def has_cycle(self) -> bool:
        """Check for cycles."""
        visited = set()
        rec_stack = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for dep in self._reverse_graph.get(node, set()):
                if dep not in visited:
                    if dfs(dep):
                        return True
                elif dep in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for node in self._graph:
            if node not in visited:
                if dfs(node):
                    return True

        return False


# =============================================================================
# TASK EXECUTOR
# =============================================================================

class TaskExecutor:
    """Execute tasks."""

    def __init__(self, max_workers: int = 4):
        self._max_workers = max_workers
        self._handlers: Dict[str, Callable] = {}
        self._running: Dict[str, TaskInstance] = {}

    def register_handler(
        self,
        name: str,
        handler: Callable
    ) -> None:
        """Register a task handler."""
        self._handlers[name] = handler

    async def execute(
        self,
        task: TaskDefinition,
        instance: TaskInstance
    ) -> TaskResult:
        """Execute a task."""
        instance.status = TaskStatus.RUNNING
        instance.started_at = datetime.now()
        self._running[task.task_id] = instance

        start_time = time.time()

        result = TaskResult(
            task_id=task.task_id,
            instance_id=instance.instance_id
        )

        try:
            if task.task_type == TaskType.COMPOSITE and task.subtasks:
                subtask_results = []

                for subtask in task.subtasks:
                    sub_instance = TaskInstance(task_id=subtask.task_id)
                    instance.subtask_instances.append(sub_instance)

                    sub_result = await self.execute(subtask, sub_instance)
                    subtask_results.append(sub_result)

                    if not sub_result.success:
                        raise Exception(f"Subtask failed: {sub_result.error}")

                result.subtask_results = subtask_results
                result.output = [sr.output for sr in subtask_results]
                result.success = True

            elif task.task_type == TaskType.PARALLEL and task.subtasks:
                sub_instances = []
                tasks_to_run = []

                for subtask in task.subtasks:
                    sub_instance = TaskInstance(task_id=subtask.task_id)
                    sub_instances.append(sub_instance)
                    instance.subtask_instances.append(sub_instance)
                    tasks_to_run.append(self.execute(subtask, sub_instance))

                subtask_results = await asyncio.gather(
                    *tasks_to_run,
                    return_exceptions=True
                )

                result.subtask_results = [
                    sr for sr in subtask_results
                    if isinstance(sr, TaskResult)
                ]
                result.success = all(
                    isinstance(sr, TaskResult) and sr.success
                    for sr in subtask_results
                )

            else:
                handler = self._handlers.get(task.handler or task.name)

                if handler:
                    if asyncio.iscoroutinefunction(handler):
                        output = await asyncio.wait_for(
                            handler(**task.params),
                            timeout=task.timeout
                        )
                    else:
                        output = handler(**task.params)
                else:
                    await asyncio.sleep(0.01)
                    output = {"executed": True, **task.params}

                result.output = output
                result.success = True

            instance.status = TaskStatus.COMPLETED
            instance.progress = 1.0
            instance.result = result.output

        except asyncio.TimeoutError:
            result.success = False
            result.error = "Task timeout"
            instance.status = TaskStatus.FAILED
            instance.error = "Timeout"

        except Exception as e:
            result.success = False
            result.error = str(e)
            instance.status = TaskStatus.FAILED
            instance.error = str(e)

        result.duration_ms = (time.time() - start_time) * 1000
        instance.completed_at = datetime.now()

        self._running.pop(task.task_id, None)

        return result

    @property
    def running_count(self) -> int:
        return len(self._running)


# =============================================================================
# TASK ENGINE
# =============================================================================

class TaskEngine:
    """
    Task Engine for BAEL.

    Task decomposition, scheduling, and execution.
    """

    def __init__(
        self,
        policy: SchedulingPolicy = SchedulingPolicy.PRIORITY,
        max_workers: int = 4
    ):
        self._decomposer = TaskDecomposer()
        self._scheduler = TaskScheduler(policy)
        self._resolver = DependencyResolver()
        self._resources = ResourceManager()
        self._executor = TaskExecutor(max_workers)

        self._tasks: Dict[str, TaskDefinition] = {}
        self._instances: Dict[str, TaskInstance] = {}

        self._stats = TaskStats()

    def define_task(
        self,
        name: str,
        task_type: TaskType = TaskType.ATOMIC,
        handler: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        dependencies: Optional[List[str]] = None,
        estimated_duration: float = 60.0,
        timeout: float = 300.0
    ) -> TaskDefinition:
        """Define a task."""
        task = TaskDefinition(
            name=name,
            task_type=task_type,
            handler=handler,
            params=params or {},
            priority=priority,
            dependencies=dependencies or [],
            estimated_duration=estimated_duration,
            timeout=timeout
        )

        self._tasks[task.task_id] = task
        self._resolver.add_task(task)

        return task

    def define_composite(
        self,
        name: str,
        subtask_names: List[str],
        parallel: bool = False,
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> TaskDefinition:
        """Define a composite task."""
        subtasks = []

        for subtask_name in subtask_names:
            for task in self._tasks.values():
                if task.name == subtask_name:
                    subtasks.append(task)
                    break

        task = TaskDefinition(
            name=name,
            task_type=TaskType.PARALLEL if parallel else TaskType.COMPOSITE,
            priority=priority,
            subtasks=subtasks
        )

        self._tasks[task.task_id] = task

        return task

    def register_handler(
        self,
        name: str,
        handler: Callable
    ) -> None:
        """Register a task handler."""
        self._executor.register_handler(name, handler)

    def register_decomposition(
        self,
        task_name: str,
        rule: Callable[[TaskDefinition], List[TaskDefinition]]
    ) -> None:
        """Register a decomposition rule."""
        self._decomposer.register_rule(task_name, rule)

    def schedule(self, task_id: str) -> bool:
        """Schedule a task."""
        task = self._tasks.get(task_id)
        if not task:
            return False

        completed = {
            tid for tid, inst in self._instances.items()
            if inst.status == TaskStatus.COMPLETED
        }

        deps = set(task.dependencies)
        if not deps.issubset(completed):
            return False

        self._scheduler.enqueue(task)

        return True

    async def execute(self, task_id: str) -> Optional[TaskResult]:
        """Execute a task directly."""
        task = self._tasks.get(task_id)
        if not task:
            return None

        if task.resources:
            if not self._resources.allocate(task_id, task.resources):
                return TaskResult(
                    task_id=task_id,
                    instance_id="",
                    success=False,
                    error="Resource allocation failed"
                )

        instance = TaskInstance(task_id=task_id)
        self._instances[instance.instance_id] = instance

        result = await self._executor.execute(task, instance)

        if task.resources:
            self._resources.release(task_id)

        self._update_stats(task, result)

        return result

    async def run_scheduled(self) -> List[TaskResult]:
        """Run all scheduled tasks."""
        results = []

        while self._scheduler.size > 0:
            task = self._scheduler.dequeue()
            if task:
                result = await self.execute(task.task_id)
                if result:
                    results.append(result)

        return results

    async def run_all(
        self,
        task_ids: Optional[List[str]] = None
    ) -> List[TaskResult]:
        """Run all tasks with dependency resolution."""
        if task_ids is None:
            task_ids = list(self._tasks.keys())

        sorted_ids = self._resolver.topological_sort(task_ids)

        completed: Set[str] = set()
        results = []

        for task_id in sorted_ids:
            ready = self._resolver.get_ready_tasks(completed, set([task_id]))

            if task_id in ready:
                result = await self.execute(task_id)
                if result:
                    results.append(result)
                    if result.success:
                        completed.add(task_id)

        return results

    def get_task(self, task_id: str) -> Optional[TaskDefinition]:
        """Get a task definition."""
        return self._tasks.get(task_id)

    def get_instance(self, instance_id: str) -> Optional[TaskInstance]:
        """Get a task instance."""
        return self._instances.get(instance_id)

    def get_progress(self, task_id: str) -> float:
        """Get task progress."""
        for instance in self._instances.values():
            if instance.task_id == task_id:
                return instance.progress
        return 0.0

    def configure_resources(
        self,
        resource_type: ResourceType,
        total: float
    ) -> None:
        """Configure a resource pool."""
        self._resources.configure_pool(resource_type, total)

    def _update_stats(
        self,
        task: TaskDefinition,
        result: TaskResult
    ) -> None:
        """Update statistics."""
        self._stats.total_tasks += 1

        if result.success:
            self._stats.completed_tasks += 1
        else:
            self._stats.failed_tasks += 1

        self._stats.total_duration_ms += result.duration_ms

        priority_key = task.priority.name
        self._stats.by_priority[priority_key] = \
            self._stats.by_priority.get(priority_key, 0) + 1

        type_key = task.task_type.value
        self._stats.by_type[type_key] = \
            self._stats.by_type.get(type_key, 0) + 1

        if self._stats.total_tasks > 0:
            self._stats.avg_duration_ms = \
                self._stats.total_duration_ms / self._stats.total_tasks

    @property
    def stats(self) -> TaskStats:
        """Get task statistics."""
        return self._stats

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "defined_tasks": len(self._tasks),
            "task_instances": len(self._instances),
            "queue_size": self._scheduler.size,
            "running": self._executor.running_count,
            "completed": self._stats.completed_tasks,
            "failed": self._stats.failed_tasks,
            "avg_duration_ms": round(self._stats.avg_duration_ms, 2),
            "by_priority": self._stats.by_priority,
            "by_type": self._stats.by_type
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Task Engine."""
    print("=" * 70)
    print("BAEL - TASK ENGINE DEMO")
    print("Task Decomposition and Execution")
    print("=" * 70)
    print()

    engine = TaskEngine(
        policy=SchedulingPolicy.PRIORITY,
        max_workers=4
    )

    # 1. Register Handlers
    print("1. REGISTER HANDLERS:")
    print("-" * 40)

    async def fetch_data(**params):
        await asyncio.sleep(0.02)
        return {"data": params.get("source", "default"), "rows": 100}

    async def process_data(**params):
        await asyncio.sleep(0.03)
        return {"processed": True, "items": params.get("count", 50)}

    async def save_results(**params):
        await asyncio.sleep(0.01)
        return {"saved": True, "path": params.get("path", "/tmp")}

    engine.register_handler("fetch", fetch_data)
    engine.register_handler("process", process_data)
    engine.register_handler("save", save_results)

    print("   Registered: fetch, process, save")
    print()

    # 2. Define Tasks
    print("2. DEFINE TASKS:")
    print("-" * 40)

    task1 = engine.define_task(
        name="fetch_data",
        handler="fetch",
        params={"source": "api"},
        priority=TaskPriority.HIGH
    )

    task2 = engine.define_task(
        name="process_data",
        handler="process",
        params={"count": 100},
        priority=TaskPriority.NORMAL,
        dependencies=[task1.task_id]
    )

    task3 = engine.define_task(
        name="save_results",
        handler="save",
        params={"path": "/data/output"},
        priority=TaskPriority.NORMAL,
        dependencies=[task2.task_id]
    )

    print(f"   Defined: {task1.name} (ID: {task1.task_id})")
    print(f"   Defined: {task2.name} (ID: {task2.task_id})")
    print(f"   Defined: {task3.name} (ID: {task3.task_id})")
    print()

    # 3. Run All with Dependencies
    print("3. RUN ALL WITH DEPENDENCIES:")
    print("-" * 40)

    results = await engine.run_all([task1.task_id, task2.task_id, task3.task_id])

    for result in results:
        status = "✓" if result.success else "✗"
        print(f"   {status} Task {result.task_id[:8]}: {result.duration_ms:.2f}ms")
        print(f"      Output: {result.output}")
    print()

    # 4. Define Composite Task
    print("4. DEFINE COMPOSITE TASK:")
    print("-" * 40)

    sub1 = engine.define_task(name="step_1", handler="fetch", params={"source": "a"})
    sub2 = engine.define_task(name="step_2", handler="fetch", params={"source": "b"})
    sub3 = engine.define_task(name="step_3", handler="process", params={"count": 25})

    composite = engine.define_composite(
        name="pipeline",
        subtask_names=["step_1", "step_2", "step_3"],
        parallel=False
    )

    result = await engine.execute(composite.task_id)

    print(f"   Composite: {composite.name}")
    print(f"   Subtasks: {len(composite.subtasks)}")
    print(f"   Success: {result.success}")
    print(f"   Duration: {result.duration_ms:.2f}ms")
    print()

    # 5. Parallel Task
    print("5. PARALLEL TASK:")
    print("-" * 40)

    par1 = engine.define_task(name="parallel_1", handler="fetch", params={"source": "x"})
    par2 = engine.define_task(name="parallel_2", handler="fetch", params={"source": "y"})
    par3 = engine.define_task(name="parallel_3", handler="fetch", params={"source": "z"})

    parallel = engine.define_composite(
        name="parallel_pipeline",
        subtask_names=["parallel_1", "parallel_2", "parallel_3"],
        parallel=True
    )

    result = await engine.execute(parallel.task_id)

    print(f"   Parallel: {parallel.name}")
    print(f"   Subtasks: {len(parallel.subtasks)}")
    print(f"   Success: {result.success}")
    print(f"   Duration: {result.duration_ms:.2f}ms (parallel)")
    print()

    # 6. Priority Scheduling
    print("6. PRIORITY SCHEDULING:")
    print("-" * 40)

    low = engine.define_task(name="low_priority", priority=TaskPriority.LOW)
    high = engine.define_task(name="high_priority", priority=TaskPriority.HIGH)
    critical = engine.define_task(name="critical", priority=TaskPriority.CRITICAL)

    engine.schedule(low.task_id)
    engine.schedule(high.task_id)
    engine.schedule(critical.task_id)

    print(f"   Queue size: {engine._scheduler.size}")

    results = await engine.run_scheduled()

    for i, result in enumerate(results):
        task = engine.get_task(result.task_id)
        print(f"   {i+1}. {task.name} ({task.priority.name})")
    print()

    # 7. Resource Management
    print("7. RESOURCE MANAGEMENT:")
    print("-" * 40)

    engine.configure_resources(ResourceType.CPU, 100.0)
    engine.configure_resources(ResourceType.MEMORY, 1000.0)

    resource_task = engine.define_task(
        name="resource_heavy",
        handler="process",
        params={"count": 1000}
    )
    resource_task.resources = [
        ResourceRequirement(ResourceType.CPU, 50.0),
        ResourceRequirement(ResourceType.MEMORY, 500.0)
    ]

    result = await engine.execute(resource_task.task_id)

    availability = engine._resources.get_availability()
    print(f"   Task: {resource_task.name}")
    print(f"   Success: {result.success}")
    print(f"   CPU Available: {availability[ResourceType.CPU]:.0%}")
    print(f"   Memory Available: {availability[ResourceType.MEMORY]:.0%}")
    print()

    # 8. Task Decomposition
    print("8. TASK DECOMPOSITION:")
    print("-" * 40)

    def decompose_etl(task: TaskDefinition) -> List[TaskDefinition]:
        return [
            TaskDefinition(name="extract", handler="fetch"),
            TaskDefinition(name="transform", handler="process"),
            TaskDefinition(name="load", handler="save")
        ]

    engine.register_decomposition("etl_pipeline", decompose_etl)

    etl = TaskDefinition(name="etl_pipeline")
    decomposed = engine._decomposer.create_hierarchy(etl)

    print(f"   Original: {etl.name}")
    print(f"   Subtasks: {len(decomposed.subtasks)}")
    for st in decomposed.subtasks:
        print(f"      - {st.name}")
    print()

    # 9. Statistics
    print("9. STATISTICS:")
    print("-" * 40)

    stats = engine.stats

    print(f"   Total Tasks: {stats.total_tasks}")
    print(f"   Completed: {stats.completed_tasks}")
    print(f"   Failed: {stats.failed_tasks}")
    print(f"   Avg Duration: {stats.avg_duration_ms:.2f}ms")
    print(f"   By Priority: {stats.by_priority}")
    print(f"   By Type: {stats.by_type}")
    print()

    # 10. Engine Summary
    print("10. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    print(f"   Defined: {summary['defined_tasks']}")
    print(f"   Instances: {summary['task_instances']}")
    print(f"   Running: {summary['running']}")
    print(f"   Completed: {summary['completed']}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Task Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
