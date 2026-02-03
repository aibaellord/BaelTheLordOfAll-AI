#!/usr/bin/env python3
"""
BAEL - Coordination Engine
Multi-agent task coordination.

Features:
- Task coordination
- Resource sharing
- Synchronization
- Conflict resolution
- Distributed execution
"""

import asyncio
import hashlib
import json
import math
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

class CoordinationMode(Enum):
    """Coordination modes."""
    CENTRALIZED = "centralized"
    DISTRIBUTED = "distributed"
    HIERARCHICAL = "hierarchical"
    PEER_TO_PEER = "peer_to_peer"


class SyncType(Enum):
    """Synchronization types."""
    BARRIER = "barrier"
    RENDEZVOUS = "rendezvous"
    CHECKPOINT = "checkpoint"
    HANDSHAKE = "handshake"


class ResourceState(Enum):
    """Resource state."""
    AVAILABLE = "available"
    LOCKED = "locked"
    RESERVED = "reserved"
    BUSY = "busy"


class ConflictType(Enum):
    """Conflict types."""
    RESOURCE = "resource"
    PRIORITY = "priority"
    TEMPORAL = "temporal"
    DEPENDENCY = "dependency"


class ResolutionStrategy(Enum):
    """Conflict resolution strategies."""
    PRIORITY = "priority"
    FIRST_COME = "first_come"
    RANDOM = "random"
    VOTING = "voting"
    NEGOTIATION = "negotiation"


class ExecutionState(Enum):
    """Distributed execution state."""
    PENDING = "pending"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class SharedResource:
    """A shared resource."""
    resource_id: str = ""
    name: str = ""
    resource_type: str = "generic"
    state: ResourceState = ResourceState.AVAILABLE
    owner: Optional[str] = None
    capacity: int = 1
    current_usage: int = 0
    queue: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.resource_id:
            self.resource_id = str(uuid.uuid4())[:8]


@dataclass
class ResourceLock:
    """A resource lock."""
    lock_id: str = ""
    resource_id: str = ""
    holder: str = ""
    acquired_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    exclusive: bool = True

    def __post_init__(self):
        if not self.lock_id:
            self.lock_id = str(uuid.uuid4())[:8]


@dataclass
class SyncPoint:
    """A synchronization point."""
    sync_id: str = ""
    sync_type: SyncType = SyncType.BARRIER
    participants: Set[str] = field(default_factory=set)
    arrived: Set[str] = field(default_factory=set)
    required_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.sync_id:
            self.sync_id = str(uuid.uuid4())[:8]


@dataclass
class Conflict:
    """A coordination conflict."""
    conflict_id: str = ""
    conflict_type: ConflictType = ConflictType.RESOURCE
    agents: Set[str] = field(default_factory=set)
    resource_id: Optional[str] = None
    description: str = ""
    detected_at: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    resolution: Optional[str] = None

    def __post_init__(self):
        if not self.conflict_id:
            self.conflict_id = str(uuid.uuid4())[:8]


@dataclass
class CoordinatedTask:
    """A coordinated task."""
    task_id: str = ""
    name: str = ""
    coordinator: str = ""
    participants: Set[str] = field(default_factory=set)
    dependencies: Set[str] = field(default_factory=set)
    required_resources: Set[str] = field(default_factory=set)
    state: ExecutionState = ExecutionState.PENDING
    progress: Dict[str, float] = field(default_factory=dict)
    results: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.task_id:
            self.task_id = str(uuid.uuid4())[:8]


@dataclass
class AgentState:
    """Agent coordination state."""
    agent_id: str = ""
    status: str = "idle"
    current_task: Optional[str] = None
    held_resources: Set[str] = field(default_factory=set)
    waiting_for: Set[str] = field(default_factory=set)
    last_update: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CoordinationStats:
    """Coordination statistics."""
    tasks_coordinated: int = 0
    resources_managed: int = 0
    syncs_completed: int = 0
    conflicts_resolved: int = 0
    avg_wait_time_ms: float = 0.0


# =============================================================================
# RESOURCE MANAGER
# =============================================================================

class ResourceCoordinator:
    """Coordinate shared resources."""

    def __init__(self):
        self._resources: Dict[str, SharedResource] = {}
        self._locks: Dict[str, ResourceLock] = {}
        self._by_type: Dict[str, Set[str]] = defaultdict(set)
        self._wait_times: List[float] = []

    def register_resource(
        self,
        name: str,
        resource_type: str = "generic",
        capacity: int = 1
    ) -> SharedResource:
        """Register a shared resource."""
        resource = SharedResource(
            name=name,
            resource_type=resource_type,
            capacity=capacity
        )

        self._resources[resource.resource_id] = resource
        self._by_type[resource_type].add(resource.resource_id)

        return resource

    def get_resource(self, resource_id: str) -> Optional[SharedResource]:
        """Get a resource."""
        return self._resources.get(resource_id)

    async def acquire(
        self,
        resource_id: str,
        agent_id: str,
        exclusive: bool = True,
        timeout_sec: Optional[float] = None
    ) -> Optional[ResourceLock]:
        """Acquire a resource lock."""
        resource = self._resources.get(resource_id)
        if not resource:
            return None

        start_time = time.time()
        deadline = start_time + timeout_sec if timeout_sec else None

        while True:
            if resource.state == ResourceState.AVAILABLE or (
                not exclusive and resource.current_usage < resource.capacity
            ):
                lock = ResourceLock(
                    resource_id=resource_id,
                    holder=agent_id,
                    exclusive=exclusive
                )

                self._locks[lock.lock_id] = lock
                resource.owner = agent_id
                resource.current_usage += 1

                if exclusive or resource.current_usage >= resource.capacity:
                    resource.state = ResourceState.LOCKED

                elapsed = (time.time() - start_time) * 1000
                self._wait_times.append(elapsed)

                return lock

            if agent_id not in resource.queue:
                resource.queue.append(agent_id)

            if deadline and time.time() >= deadline:
                if agent_id in resource.queue:
                    resource.queue.remove(agent_id)
                return None

            await asyncio.sleep(0.01)

    def release(self, lock_id: str) -> bool:
        """Release a resource lock."""
        lock = self._locks.pop(lock_id, None)
        if not lock:
            return False

        resource = self._resources.get(lock.resource_id)
        if not resource:
            return False

        resource.current_usage = max(0, resource.current_usage - 1)

        if resource.current_usage == 0:
            resource.state = ResourceState.AVAILABLE
            resource.owner = None

        if resource.queue and resource.state == ResourceState.AVAILABLE:
            pass

        return True

    def get_available(self, resource_type: Optional[str] = None) -> List[SharedResource]:
        """Get available resources."""
        if resource_type:
            resource_ids = self._by_type.get(resource_type, set())
            resources = [self._resources[rid] for rid in resource_ids if rid in self._resources]
        else:
            resources = list(self._resources.values())

        return [r for r in resources if r.state == ResourceState.AVAILABLE]

    def is_available(self, resource_id: str) -> bool:
        """Check if resource is available."""
        resource = self._resources.get(resource_id)
        return resource and resource.state == ResourceState.AVAILABLE

    @property
    def avg_wait_time(self) -> float:
        """Get average wait time in ms."""
        if not self._wait_times:
            return 0.0
        return sum(self._wait_times) / len(self._wait_times)


# =============================================================================
# SYNCHRONIZATION MANAGER
# =============================================================================

class SyncManager:
    """Manage synchronization points."""

    def __init__(self):
        self._sync_points: Dict[str, SyncPoint] = {}
        self._events: Dict[str, asyncio.Event] = {}

    def create_barrier(
        self,
        participants: Set[str],
        sync_id: Optional[str] = None
    ) -> SyncPoint:
        """Create a barrier synchronization point."""
        sync_point = SyncPoint(
            sync_type=SyncType.BARRIER,
            participants=participants,
            required_count=len(participants)
        )

        if sync_id:
            sync_point.sync_id = sync_id

        self._sync_points[sync_point.sync_id] = sync_point
        self._events[sync_point.sync_id] = asyncio.Event()

        return sync_point

    def create_rendezvous(
        self,
        agent1: str,
        agent2: str
    ) -> SyncPoint:
        """Create a rendezvous point between two agents."""
        sync_point = SyncPoint(
            sync_type=SyncType.RENDEZVOUS,
            participants={agent1, agent2},
            required_count=2
        )

        self._sync_points[sync_point.sync_id] = sync_point
        self._events[sync_point.sync_id] = asyncio.Event()

        return sync_point

    def create_checkpoint(
        self,
        participants: Set[str]
    ) -> SyncPoint:
        """Create a checkpoint."""
        sync_point = SyncPoint(
            sync_type=SyncType.CHECKPOINT,
            participants=participants,
            required_count=len(participants)
        )

        self._sync_points[sync_point.sync_id] = sync_point
        self._events[sync_point.sync_id] = asyncio.Event()

        return sync_point

    async def arrive(
        self,
        sync_id: str,
        agent_id: str,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Arrive at a synchronization point."""
        sync_point = self._sync_points.get(sync_id)
        if not sync_point:
            return False

        if agent_id not in sync_point.participants:
            return False

        sync_point.arrived.add(agent_id)

        if data:
            sync_point.data[agent_id] = data

        if len(sync_point.arrived) >= sync_point.required_count:
            sync_point.completed_at = datetime.now()
            event = self._events.get(sync_id)
            if event:
                event.set()

        return True

    async def wait(
        self,
        sync_id: str,
        timeout_sec: Optional[float] = None
    ) -> bool:
        """Wait at a synchronization point."""
        event = self._events.get(sync_id)
        if not event:
            return False

        try:
            await asyncio.wait_for(event.wait(), timeout=timeout_sec)
            return True
        except asyncio.TimeoutError:
            return False

    async def arrive_and_wait(
        self,
        sync_id: str,
        agent_id: str,
        data: Optional[Dict[str, Any]] = None,
        timeout_sec: Optional[float] = None
    ) -> bool:
        """Arrive and wait at a synchronization point."""
        if not await self.arrive(sync_id, agent_id, data):
            return False

        return await self.wait(sync_id, timeout_sec)

    def is_complete(self, sync_id: str) -> bool:
        """Check if sync point is complete."""
        sync_point = self._sync_points.get(sync_id)
        return sync_point and sync_point.completed_at is not None

    def get_data(self, sync_id: str) -> Dict[str, Any]:
        """Get collected data from sync point."""
        sync_point = self._sync_points.get(sync_id)
        if not sync_point:
            return {}
        return dict(sync_point.data)

    def reset(self, sync_id: str) -> bool:
        """Reset a sync point."""
        sync_point = self._sync_points.get(sync_id)
        if not sync_point:
            return False

        sync_point.arrived.clear()
        sync_point.completed_at = None
        sync_point.data.clear()

        event = self._events.get(sync_id)
        if event:
            event.clear()

        return True


# =============================================================================
# CONFLICT RESOLVER
# =============================================================================

class ConflictResolver:
    """Resolve coordination conflicts."""

    def __init__(self):
        self._conflicts: Dict[str, Conflict] = {}
        self._priorities: Dict[str, int] = {}
        self._resolved_count = 0

    def set_priority(self, agent_id: str, priority: int) -> None:
        """Set agent priority."""
        self._priorities[agent_id] = priority

    def get_priority(self, agent_id: str) -> int:
        """Get agent priority."""
        return self._priorities.get(agent_id, 0)

    def detect_conflict(
        self,
        conflict_type: ConflictType,
        agents: Set[str],
        resource_id: Optional[str] = None,
        description: str = ""
    ) -> Conflict:
        """Detect and register a conflict."""
        conflict = Conflict(
            conflict_type=conflict_type,
            agents=agents,
            resource_id=resource_id,
            description=description
        )

        self._conflicts[conflict.conflict_id] = conflict

        return conflict

    def resolve(
        self,
        conflict_id: str,
        strategy: ResolutionStrategy = ResolutionStrategy.PRIORITY
    ) -> Optional[str]:
        """Resolve a conflict, returns winning agent."""
        conflict = self._conflicts.get(conflict_id)
        if not conflict or conflict.resolved:
            return None

        agents = list(conflict.agents)
        if not agents:
            return None

        winner = None

        if strategy == ResolutionStrategy.PRIORITY:
            winner = max(agents, key=lambda a: self._priorities.get(a, 0))

        elif strategy == ResolutionStrategy.FIRST_COME:
            winner = agents[0]

        elif strategy == ResolutionStrategy.RANDOM:
            winner = random.choice(agents)

        elif strategy == ResolutionStrategy.VOTING:
            votes = {a: len(agents) - i for i, a in enumerate(agents)}
            winner = max(votes.keys(), key=lambda a: votes[a])

        conflict.resolved = True
        conflict.resolution = f"{strategy.value}: {winner}"
        self._resolved_count += 1

        return winner

    def get_conflict(self, conflict_id: str) -> Optional[Conflict]:
        """Get a conflict."""
        return self._conflicts.get(conflict_id)

    def get_unresolved(self) -> List[Conflict]:
        """Get unresolved conflicts."""
        return [c for c in self._conflicts.values() if not c.resolved]

    @property
    def resolved_count(self) -> int:
        return self._resolved_count


# =============================================================================
# TASK COORDINATOR
# =============================================================================

class TaskCoordinator:
    """Coordinate distributed tasks."""

    def __init__(self, resource_coordinator: ResourceCoordinator):
        self._resources = resource_coordinator
        self._tasks: Dict[str, CoordinatedTask] = {}
        self._agent_states: Dict[str, AgentState] = {}
        self._completed_count = 0

    def create_task(
        self,
        name: str,
        coordinator: str,
        participants: Set[str],
        dependencies: Optional[Set[str]] = None,
        required_resources: Optional[Set[str]] = None
    ) -> CoordinatedTask:
        """Create a coordinated task."""
        task = CoordinatedTask(
            name=name,
            coordinator=coordinator,
            participants=participants,
            dependencies=dependencies or set(),
            required_resources=required_resources or set()
        )

        for agent_id in participants:
            task.progress[agent_id] = 0.0

        self._tasks[task.task_id] = task

        return task

    def get_task(self, task_id: str) -> Optional[CoordinatedTask]:
        """Get a task."""
        return self._tasks.get(task_id)

    async def start_task(self, task_id: str) -> bool:
        """Start a coordinated task."""
        task = self._tasks.get(task_id)
        if not task:
            return False

        for dep_id in task.dependencies:
            dep_task = self._tasks.get(dep_id)
            if not dep_task or dep_task.state != ExecutionState.COMPLETED:
                return False

        for resource_id in task.required_resources:
            if not self._resources.is_available(resource_id):
                task.state = ExecutionState.WAITING
                return False

        task.state = ExecutionState.RUNNING

        for agent_id in task.participants:
            if agent_id not in self._agent_states:
                self._agent_states[agent_id] = AgentState(agent_id=agent_id)

            self._agent_states[agent_id].status = "working"
            self._agent_states[agent_id].current_task = task_id

        return True

    def update_progress(
        self,
        task_id: str,
        agent_id: str,
        progress: float
    ) -> bool:
        """Update agent's progress on a task."""
        task = self._tasks.get(task_id)
        if not task or agent_id not in task.participants:
            return False

        task.progress[agent_id] = max(0.0, min(1.0, progress))

        if agent_id in self._agent_states:
            self._agent_states[agent_id].last_update = datetime.now()

        return True

    def submit_result(
        self,
        task_id: str,
        agent_id: str,
        result: Any
    ) -> bool:
        """Submit result for a task."""
        task = self._tasks.get(task_id)
        if not task or agent_id not in task.participants:
            return False

        task.results[agent_id] = result
        task.progress[agent_id] = 1.0

        all_done = all(p >= 1.0 for p in task.progress.values())

        if all_done:
            task.state = ExecutionState.COMPLETED
            self._completed_count += 1

            for aid in task.participants:
                if aid in self._agent_states:
                    self._agent_states[aid].status = "idle"
                    self._agent_states[aid].current_task = None

        return True

    def get_agent_state(self, agent_id: str) -> Optional[AgentState]:
        """Get agent state."""
        return self._agent_states.get(agent_id)

    def set_agent_state(
        self,
        agent_id: str,
        status: str,
        waiting_for: Optional[Set[str]] = None
    ) -> None:
        """Set agent state."""
        if agent_id not in self._agent_states:
            self._agent_states[agent_id] = AgentState(agent_id=agent_id)

        self._agent_states[agent_id].status = status
        self._agent_states[agent_id].last_update = datetime.now()

        if waiting_for:
            self._agent_states[agent_id].waiting_for = waiting_for

    def get_task_progress(self, task_id: str) -> float:
        """Get overall task progress."""
        task = self._tasks.get(task_id)
        if not task or not task.progress:
            return 0.0

        return sum(task.progress.values()) / len(task.progress)

    def get_pending_tasks(self) -> List[CoordinatedTask]:
        """Get pending tasks."""
        return [t for t in self._tasks.values() if t.state == ExecutionState.PENDING]

    def get_running_tasks(self) -> List[CoordinatedTask]:
        """Get running tasks."""
        return [t for t in self._tasks.values() if t.state == ExecutionState.RUNNING]

    @property
    def completed_count(self) -> int:
        return self._completed_count


# =============================================================================
# COORDINATION ENGINE
# =============================================================================

class CoordinationEngine:
    """
    Coordination Engine for BAEL.

    Multi-agent task coordination.
    """

    def __init__(self, mode: CoordinationMode = CoordinationMode.CENTRALIZED):
        self._mode = mode

        self._resources = ResourceCoordinator()
        self._sync = SyncManager()
        self._conflicts = ConflictResolver()
        self._tasks = TaskCoordinator(self._resources)

        self._stats = CoordinationStats()

    @property
    def mode(self) -> CoordinationMode:
        """Get coordination mode."""
        return self._mode

    def register_resource(
        self,
        name: str,
        resource_type: str = "generic",
        capacity: int = 1
    ) -> SharedResource:
        """Register a shared resource."""
        resource = self._resources.register_resource(name, resource_type, capacity)
        self._stats.resources_managed += 1
        return resource

    def get_resource(self, resource_id: str) -> Optional[SharedResource]:
        """Get a resource."""
        return self._resources.get_resource(resource_id)

    async def acquire_resource(
        self,
        resource_id: str,
        agent_id: str,
        exclusive: bool = True,
        timeout_sec: Optional[float] = None
    ) -> Optional[ResourceLock]:
        """Acquire a resource lock."""
        return await self._resources.acquire(
            resource_id, agent_id, exclusive, timeout_sec
        )

    def release_resource(self, lock_id: str) -> bool:
        """Release a resource lock."""
        return self._resources.release(lock_id)

    def get_available_resources(
        self,
        resource_type: Optional[str] = None
    ) -> List[SharedResource]:
        """Get available resources."""
        return self._resources.get_available(resource_type)

    def create_barrier(
        self,
        participants: Set[str],
        sync_id: Optional[str] = None
    ) -> SyncPoint:
        """Create a barrier synchronization point."""
        return self._sync.create_barrier(participants, sync_id)

    def create_rendezvous(self, agent1: str, agent2: str) -> SyncPoint:
        """Create a rendezvous point."""
        return self._sync.create_rendezvous(agent1, agent2)

    def create_checkpoint(self, participants: Set[str]) -> SyncPoint:
        """Create a checkpoint."""
        return self._sync.create_checkpoint(participants)

    async def sync_arrive(
        self,
        sync_id: str,
        agent_id: str,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Arrive at a sync point."""
        return await self._sync.arrive(sync_id, agent_id, data)

    async def sync_wait(
        self,
        sync_id: str,
        timeout_sec: Optional[float] = None
    ) -> bool:
        """Wait at a sync point."""
        result = await self._sync.wait(sync_id, timeout_sec)
        if result:
            self._stats.syncs_completed += 1
        return result

    async def barrier(
        self,
        sync_id: str,
        agent_id: str,
        data: Optional[Dict[str, Any]] = None,
        timeout_sec: Optional[float] = None
    ) -> bool:
        """Arrive and wait at a barrier."""
        result = await self._sync.arrive_and_wait(sync_id, agent_id, data, timeout_sec)
        if result and self._sync.is_complete(sync_id):
            self._stats.syncs_completed += 1
        return result

    def get_sync_data(self, sync_id: str) -> Dict[str, Any]:
        """Get data from a sync point."""
        return self._sync.get_data(sync_id)

    def reset_sync(self, sync_id: str) -> bool:
        """Reset a sync point."""
        return self._sync.reset(sync_id)

    def set_priority(self, agent_id: str, priority: int) -> None:
        """Set agent priority."""
        self._conflicts.set_priority(agent_id, priority)

    def detect_conflict(
        self,
        conflict_type: ConflictType,
        agents: Set[str],
        resource_id: Optional[str] = None,
        description: str = ""
    ) -> Conflict:
        """Detect a conflict."""
        return self._conflicts.detect_conflict(
            conflict_type, agents, resource_id, description
        )

    def resolve_conflict(
        self,
        conflict_id: str,
        strategy: ResolutionStrategy = ResolutionStrategy.PRIORITY
    ) -> Optional[str]:
        """Resolve a conflict."""
        winner = self._conflicts.resolve(conflict_id, strategy)
        if winner:
            self._stats.conflicts_resolved += 1
        return winner

    def get_unresolved_conflicts(self) -> List[Conflict]:
        """Get unresolved conflicts."""
        return self._conflicts.get_unresolved()

    def create_task(
        self,
        name: str,
        coordinator: str,
        participants: Set[str],
        dependencies: Optional[Set[str]] = None,
        required_resources: Optional[Set[str]] = None
    ) -> CoordinatedTask:
        """Create a coordinated task."""
        task = self._tasks.create_task(
            name, coordinator, participants, dependencies, required_resources
        )
        self._stats.tasks_coordinated += 1
        return task

    def get_task(self, task_id: str) -> Optional[CoordinatedTask]:
        """Get a task."""
        return self._tasks.get_task(task_id)

    async def start_task(self, task_id: str) -> bool:
        """Start a task."""
        return await self._tasks.start_task(task_id)

    def update_progress(
        self,
        task_id: str,
        agent_id: str,
        progress: float
    ) -> bool:
        """Update task progress."""
        return self._tasks.update_progress(task_id, agent_id, progress)

    def submit_result(
        self,
        task_id: str,
        agent_id: str,
        result: Any
    ) -> bool:
        """Submit task result."""
        return self._tasks.submit_result(task_id, agent_id, result)

    def get_task_progress(self, task_id: str) -> float:
        """Get task progress."""
        return self._tasks.get_task_progress(task_id)

    def get_agent_state(self, agent_id: str) -> Optional[AgentState]:
        """Get agent state."""
        return self._tasks.get_agent_state(agent_id)

    def set_agent_state(
        self,
        agent_id: str,
        status: str,
        waiting_for: Optional[Set[str]] = None
    ) -> None:
        """Set agent state."""
        self._tasks.set_agent_state(agent_id, status, waiting_for)

    def get_pending_tasks(self) -> List[CoordinatedTask]:
        """Get pending tasks."""
        return self._tasks.get_pending_tasks()

    def get_running_tasks(self) -> List[CoordinatedTask]:
        """Get running tasks."""
        return self._tasks.get_running_tasks()

    @property
    def stats(self) -> CoordinationStats:
        """Get coordination statistics."""
        self._stats.avg_wait_time_ms = self._resources.avg_wait_time
        return self._stats

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "mode": self._mode.value,
            "resources_managed": self._stats.resources_managed,
            "tasks_coordinated": self._stats.tasks_coordinated,
            "tasks_completed": self._tasks.completed_count,
            "syncs_completed": self._stats.syncs_completed,
            "conflicts_resolved": self._stats.conflicts_resolved,
            "avg_wait_time_ms": f"{self._resources.avg_wait_time:.2f}",
            "pending_tasks": len(self.get_pending_tasks()),
            "running_tasks": len(self.get_running_tasks()),
            "unresolved_conflicts": len(self.get_unresolved_conflicts())
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Coordination Engine."""
    print("=" * 70)
    print("BAEL - COORDINATION ENGINE DEMO")
    print("Multi-agent Task Coordination")
    print("=" * 70)
    print()

    engine = CoordinationEngine(mode=CoordinationMode.CENTRALIZED)

    # 1. Register Resources
    print("1. REGISTER SHARED RESOURCES:")
    print("-" * 40)

    db_resource = engine.register_resource(
        name="database",
        resource_type="storage",
        capacity=5
    )

    compute_resource = engine.register_resource(
        name="gpu_cluster",
        resource_type="compute",
        capacity=2
    )

    print(f"   Database: capacity={db_resource.capacity}")
    print(f"   GPU Cluster: capacity={compute_resource.capacity}")
    print()

    # 2. Acquire Resources
    print("2. ACQUIRE RESOURCES:")
    print("-" * 40)

    lock1 = await engine.acquire_resource(
        db_resource.resource_id,
        "agent_1",
        exclusive=False,
        timeout_sec=1.0
    )

    lock2 = await engine.acquire_resource(
        db_resource.resource_id,
        "agent_2",
        exclusive=False,
        timeout_sec=1.0
    )

    print(f"   agent_1 acquired database: {lock1 is not None}")
    print(f"   agent_2 acquired database: {lock2 is not None}")

    db = engine.get_resource(db_resource.resource_id)
    print(f"   Database usage: {db.current_usage}/{db.capacity}")
    print()

    # 3. Release Resources
    print("3. RELEASE RESOURCES:")
    print("-" * 40)

    engine.release_resource(lock1.lock_id)
    print(f"   agent_1 released database")

    db = engine.get_resource(db_resource.resource_id)
    print(f"   Database state: {db.state.value}")
    print()

    # 4. Create Barrier
    print("4. CREATE BARRIER:")
    print("-" * 40)

    barrier = engine.create_barrier(
        participants={"agent_1", "agent_2", "agent_3"},
        sync_id="phase1_barrier"
    )

    print(f"   Barrier ID: {barrier.sync_id}")
    print(f"   Participants: {barrier.participants}")
    print(f"   Required: {barrier.required_count}")
    print()

    # 5. Barrier Synchronization
    print("5. BARRIER SYNCHRONIZATION:")
    print("-" * 40)

    async def agent_work(agent_id: str, delay: float):
        await asyncio.sleep(delay)
        await engine.sync_arrive(barrier.sync_id, agent_id, {"status": "ready"})
        print(f"      {agent_id} arrived at barrier")

    await asyncio.gather(
        agent_work("agent_1", 0.1),
        agent_work("agent_2", 0.2),
        agent_work("agent_3", 0.15)
    )

    await engine.sync_wait(barrier.sync_id, timeout_sec=1.0)
    print(f"   Barrier complete: {engine._sync.is_complete(barrier.sync_id)}")

    sync_data = engine.get_sync_data(barrier.sync_id)
    print(f"   Collected data: {list(sync_data.keys())}")
    print()

    # 6. Set Priorities
    print("6. SET AGENT PRIORITIES:")
    print("-" * 40)

    engine.set_priority("agent_1", priority=3)
    engine.set_priority("agent_2", priority=1)
    engine.set_priority("agent_3", priority=2)

    print("   agent_1: priority 3 (highest)")
    print("   agent_2: priority 1 (lowest)")
    print("   agent_3: priority 2")
    print()

    # 7. Detect Conflict
    print("7. DETECT CONFLICT:")
    print("-" * 40)

    conflict = engine.detect_conflict(
        conflict_type=ConflictType.RESOURCE,
        agents={"agent_1", "agent_2"},
        resource_id=compute_resource.resource_id,
        description="Both agents need GPU cluster"
    )

    print(f"   Conflict ID: {conflict.conflict_id}")
    print(f"   Type: {conflict.conflict_type.value}")
    print(f"   Agents: {conflict.agents}")
    print()

    # 8. Resolve Conflict
    print("8. RESOLVE CONFLICT:")
    print("-" * 40)

    winner = engine.resolve_conflict(
        conflict.conflict_id,
        strategy=ResolutionStrategy.PRIORITY
    )

    print(f"   Strategy: priority")
    print(f"   Winner: {winner}")
    print(f"   Resolution: {conflict.resolution}")
    print()

    # 9. Create Coordinated Task
    print("9. CREATE COORDINATED TASK:")
    print("-" * 40)

    task = engine.create_task(
        name="Process Dataset",
        coordinator="agent_1",
        participants={"agent_1", "agent_2", "agent_3"},
        required_resources={db_resource.resource_id}
    )

    print(f"   Task ID: {task.task_id}")
    print(f"   Coordinator: {task.coordinator}")
    print(f"   Participants: {task.participants}")
    print()

    # 10. Start Task
    print("10. START TASK:")
    print("-" * 40)

    engine.release_resource(lock2.lock_id)

    started = await engine.start_task(task.task_id)

    print(f"   Started: {started}")
    print(f"   State: {task.state.value}")
    print()

    # 11. Update Progress
    print("11. UPDATE PROGRESS:")
    print("-" * 40)

    engine.update_progress(task.task_id, "agent_1", 0.5)
    engine.update_progress(task.task_id, "agent_2", 0.75)
    engine.update_progress(task.task_id, "agent_3", 1.0)

    for agent_id, progress in task.progress.items():
        print(f"   {agent_id}: {progress:.0%}")

    overall = engine.get_task_progress(task.task_id)
    print(f"   Overall: {overall:.0%}")
    print()

    # 12. Submit Results
    print("12. SUBMIT RESULTS:")
    print("-" * 40)

    engine.submit_result(task.task_id, "agent_1", {"processed": 100})
    engine.submit_result(task.task_id, "agent_2", {"processed": 150})

    print(f"   agent_1 submitted result")
    print(f"   agent_2 submitted result")
    print(f"   Task state: {task.state.value}")
    print()

    # 13. Agent States
    print("13. AGENT STATES:")
    print("-" * 40)

    for agent_id in ["agent_1", "agent_2", "agent_3"]:
        state = engine.get_agent_state(agent_id)
        if state:
            print(f"   {agent_id}: {state.status}")
    print()

    # 14. Statistics
    print("14. COORDINATION STATISTICS:")
    print("-" * 40)

    stats = engine.stats

    print(f"   Resources Managed: {stats.resources_managed}")
    print(f"   Tasks Coordinated: {stats.tasks_coordinated}")
    print(f"   Syncs Completed: {stats.syncs_completed}")
    print(f"   Conflicts Resolved: {stats.conflicts_resolved}")
    print(f"   Avg Wait Time: {stats.avg_wait_time_ms:.2f} ms")
    print()

    # 15. Summary
    print("15. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Coordination Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
