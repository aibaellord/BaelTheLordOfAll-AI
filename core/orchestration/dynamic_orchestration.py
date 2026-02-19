"""
⚡ DYNAMIC ORCHESTRATION ⚡
==========================
Adaptive task orchestration.

Features:
- Dynamic scheduling
- Resource management
- Adaptive load handling
- Cross-system coordination
"""

import math
import asyncio
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict, deque
import uuid
import heapq


class TaskPriority(Enum):
    """Task priority levels"""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


@dataclass
class OrchestratorConfig:
    """Configuration for orchestrator"""
    max_concurrent_tasks: int = 10
    task_timeout: float = 300.0
    retry_limit: int = 3
    queue_size: int = 1000
    adaptive_scaling: bool = True
    min_workers: int = 1
    max_workers: int = 20


@dataclass
class Task:
    """Task to be orchestrated"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    priority: TaskPriority = TaskPriority.NORMAL

    # Execution
    handler: Optional[Callable] = None
    args: Tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)

    # Dependencies
    depends_on: Set[str] = field(default_factory=set)  # Task IDs

    # Resources
    required_resources: Dict[str, float] = field(default_factory=dict)

    # State
    status: str = "pending"  # pending, running, completed, failed
    retries: int = 0

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Results
    result: Any = None
    error: Optional[str] = None

    def __lt__(self, other):
        """For priority queue ordering"""
        return self.priority.value < other.priority.value


@dataclass
class TaskResult:
    """Result of task execution"""
    task_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    duration: float = 0.0


@dataclass
class Resource:
    """Managed resource"""
    name: str
    total: float
    available: float = 0.0

    def __post_init__(self):
        self.available = self.total

    def allocate(self, amount: float) -> bool:
        if amount <= self.available:
            self.available -= amount
            return True
        return False

    def release(self, amount: float):
        self.available = min(self.total, self.available + amount)


class ResourcePool:
    """
    Manages resource allocation.
    """

    def __init__(self):
        self.resources: Dict[str, Resource] = {}
        self.allocations: Dict[str, Dict[str, float]] = {}  # task_id -> {resource: amount}

    def add_resource(self, name: str, total: float):
        """Add resource to pool"""
        self.resources[name] = Resource(name=name, total=total)

    def can_allocate(self, requirements: Dict[str, float]) -> bool:
        """Check if can allocate resources"""
        for name, amount in requirements.items():
            resource = self.resources.get(name)
            if not resource or resource.available < amount:
                return False
        return True

    def allocate(
        self,
        task_id: str,
        requirements: Dict[str, float]
    ) -> bool:
        """Allocate resources for task"""
        if not self.can_allocate(requirements):
            return False

        allocations = {}
        for name, amount in requirements.items():
            self.resources[name].allocate(amount)
            allocations[name] = amount

        self.allocations[task_id] = allocations
        return True

    def release(self, task_id: str):
        """Release task's resources"""
        if task_id in self.allocations:
            for name, amount in self.allocations[task_id].items():
                if name in self.resources:
                    self.resources[name].release(amount)
            del self.allocations[task_id]

    def get_utilization(self) -> Dict[str, float]:
        """Get resource utilization"""
        return {
            name: 1 - (res.available / res.total)
            for name, res in self.resources.items()
            if res.total > 0
        }


class DynamicScheduler:
    """
    Dynamic task scheduler with priority queue.
    """

    def __init__(self, config: OrchestratorConfig = None):
        self.config = config or OrchestratorConfig()

        # Priority queue
        self.queue: List[Task] = []

        # Task registry
        self.tasks: Dict[str, Task] = {}

        # Completed tasks for dependency checking
        self.completed: Set[str] = set()

        # Resources
        self.resources = ResourcePool()

    def submit(self, task: Task):
        """Submit task to scheduler"""
        self.tasks[task.id] = task

        if self._can_schedule(task):
            heapq.heappush(self.queue, task)
        else:
            task.status = "waiting"

    def _can_schedule(self, task: Task) -> bool:
        """Check if task can be scheduled"""
        # Check dependencies
        for dep_id in task.depends_on:
            if dep_id not in self.completed:
                return False

        # Check resources
        if task.required_resources:
            if not self.resources.can_allocate(task.required_resources):
                return False

        return True

    def get_next(self) -> Optional[Task]:
        """Get next task to execute"""
        while self.queue:
            task = heapq.heappop(self.queue)

            if task.id not in self.tasks:
                continue  # Task was cancelled

            if self._can_schedule(task):
                if task.required_resources:
                    self.resources.allocate(task.id, task.required_resources)
                return task
            else:
                # Re-queue
                heapq.heappush(self.queue, task)
                break

        return None

    def complete(self, task_id: str, success: bool):
        """Mark task as complete"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = "completed" if success else "failed"
            task.completed_at = datetime.now()

            self.completed.add(task_id)
            self.resources.release(task_id)

            # Check waiting tasks
            self._check_waiting()

    def _check_waiting(self):
        """Check if waiting tasks can now be scheduled"""
        for task in self.tasks.values():
            if task.status == "waiting" and self._can_schedule(task):
                heapq.heappush(self.queue, task)
                task.status = "pending"

    def cancel(self, task_id: str):
        """Cancel task"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = "cancelled"
            self.resources.release(task_id)
            del self.tasks[task_id]


class AdaptiveOrchestrator:
    """
    Orchestrator that adapts to load.
    """

    def __init__(self, config: OrchestratorConfig = None):
        self.config = config or OrchestratorConfig()
        self.scheduler = DynamicScheduler(config)

        # Worker pool
        self.active_workers = 0
        self.target_workers = self.config.min_workers

        # Metrics
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.total_latency = 0.0

        # Load tracking
        self.load_history: deque = deque(maxlen=100)

    def submit(self, task: Task):
        """Submit task"""
        self.scheduler.submit(task)
        self._adapt_workers()

    def _adapt_workers(self):
        """Adapt worker count to load"""
        if not self.config.adaptive_scaling:
            return

        queue_size = len(self.scheduler.queue)
        self.load_history.append(queue_size)

        avg_load = sum(self.load_history) / len(self.load_history)

        if avg_load > self.target_workers * 2:
            # Scale up
            self.target_workers = min(
                self.config.max_workers,
                self.target_workers + 1
            )
        elif avg_load < self.target_workers * 0.5 and self.target_workers > self.config.min_workers:
            # Scale down
            self.target_workers = max(
                self.config.min_workers,
                self.target_workers - 1
            )

    async def run(self):
        """Run orchestrator loop"""
        while True:
            # Start workers if needed
            while self.active_workers < self.target_workers:
                task = self.scheduler.get_next()
                if task:
                    asyncio.create_task(self._execute_task(task))
                    self.active_workers += 1
                else:
                    break

            await asyncio.sleep(0.1)

    async def _execute_task(self, task: Task):
        """Execute task"""
        task.status = "running"
        task.started_at = datetime.now()

        try:
            if task.handler:
                if asyncio.iscoroutinefunction(task.handler):
                    result = await asyncio.wait_for(
                        task.handler(*task.args, **task.kwargs),
                        timeout=self.config.task_timeout
                    )
                else:
                    result = await asyncio.wait_for(
                        asyncio.to_thread(task.handler, *task.args, **task.kwargs),
                        timeout=self.config.task_timeout
                    )

                task.result = result

            task.status = "completed"
            task.completed_at = datetime.now()

            duration = (task.completed_at - task.started_at).total_seconds()
            self.total_latency += duration
            self.completed_tasks += 1

            self.scheduler.complete(task.id, True)

        except Exception as e:
            task.error = str(e)

            if task.retries < self.config.retry_limit:
                task.retries += 1
                task.status = "pending"
                self.scheduler.submit(task)
            else:
                task.status = "failed"
                self.failed_tasks += 1
                self.scheduler.complete(task.id, False)

        finally:
            self.active_workers -= 1

    def get_metrics(self) -> Dict[str, Any]:
        """Get orchestrator metrics"""
        return {
            'completed_tasks': self.completed_tasks,
            'failed_tasks': self.failed_tasks,
            'success_rate': (
                self.completed_tasks / (self.completed_tasks + self.failed_tasks)
                if self.completed_tasks + self.failed_tasks > 0 else 1.0
            ),
            'avg_latency': (
                self.total_latency / self.completed_tasks
                if self.completed_tasks > 0 else 0
            ),
            'active_workers': self.active_workers,
            'target_workers': self.target_workers,
            'queue_size': len(self.scheduler.queue),
            'resource_utilization': self.scheduler.resources.get_utilization()
        }


class TranscendentOrchestrator:
    """
    Supreme orchestration layer.

    Coordinates all system components:
    - Task scheduling
    - Resource management
    - Cross-system communication
    - Adaptive optimization
    """

    def __init__(self, config: OrchestratorConfig = None):
        self.config = config or OrchestratorConfig()
        self.orchestrator = AdaptiveOrchestrator(config)

        # Subsystem orchestrators
        self.subsystems: Dict[str, AdaptiveOrchestrator] = {}

        # Cross-system task routing
        self.routing_rules: Dict[str, str] = {}  # task_pattern -> subsystem

        # Global state
        self.global_context: Dict[str, Any] = {}

        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = defaultdict(list)

    def add_subsystem(
        self,
        name: str,
        orchestrator: AdaptiveOrchestrator = None
    ):
        """Add subsystem orchestrator"""
        self.subsystems[name] = orchestrator or AdaptiveOrchestrator(self.config)

    def add_routing_rule(self, pattern: str, subsystem: str):
        """Add task routing rule"""
        self.routing_rules[pattern] = subsystem

    def route_task(self, task: Task) -> str:
        """Determine which subsystem should handle task"""
        for pattern, subsystem in self.routing_rules.items():
            if pattern in task.name:
                return subsystem
        return "main"

    def submit(self, task: Task):
        """Submit task with intelligent routing"""
        subsystem = self.route_task(task)

        if subsystem in self.subsystems:
            self.subsystems[subsystem].submit(task)
        else:
            self.orchestrator.submit(task)

        self._emit_event('task_submitted', task)

    def on_event(self, event_type: str, handler: Callable):
        """Register event handler"""
        self.event_handlers[event_type].append(handler)

    def _emit_event(self, event_type: str, data: Any):
        """Emit event to handlers"""
        for handler in self.event_handlers.get(event_type, []):
            try:
                handler(data)
            except Exception:
                pass

    def get_global_metrics(self) -> Dict[str, Any]:
        """Get metrics across all subsystems"""
        metrics = {
            'main': self.orchestrator.get_metrics()
        }

        for name, orch in self.subsystems.items():
            metrics[name] = orch.get_metrics()

        # Aggregate
        total_completed = sum(m['completed_tasks'] for m in metrics.values())
        total_failed = sum(m['failed_tasks'] for m in metrics.values())

        metrics['aggregate'] = {
            'total_completed': total_completed,
            'total_failed': total_failed,
            'overall_success_rate': (
                total_completed / (total_completed + total_failed)
                if total_completed + total_failed > 0 else 1.0
            ),
            'subsystems': len(self.subsystems) + 1
        }

        return metrics

    async def run_all(self):
        """Run all orchestrators"""
        tasks = [self.orchestrator.run()]

        for orch in self.subsystems.values():
            tasks.append(orch.run())

        await asyncio.gather(*tasks)


# Export all
__all__ = [
    'OrchestratorConfig',
    'TaskPriority',
    'Task',
    'TaskResult',
    'Resource',
    'ResourcePool',
    'DynamicScheduler',
    'AdaptiveOrchestrator',
    'TranscendentOrchestrator',
]
