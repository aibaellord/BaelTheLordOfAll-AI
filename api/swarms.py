"""
Agent Swarms System for BAEL Phase 2

Implements distributed agent swarms for parallel task execution with
coordination, task decomposition, and emergent intelligence patterns.

Key Components:
- Swarm management and orchestration
- Task decomposition into micro-tasks
- Agent roles and specialization
- Coordination and synchronization
- Emergent behavior patterns
- Swarm intelligence metrics
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)


class AgentRole(str, Enum):
    """Agent specialization roles."""
    WORKER = "worker"  # Executes tasks
    COORDINATOR = "coordinator"  # Coordinates subtasks
    ANALYZER = "analyzer"  # Analyzes and optimizes
    VALIDATOR = "validator"  # Validates results
    MONITOR = "monitor"  # Tracks swarm health
    LEADER = "leader"  # Overall coordination


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentStatus(str, Enum):
    """Agent status in swarm."""
    IDLE = "idle"
    BUSY = "busy"
    WAITING = "waiting"
    ERROR = "error"
    TERMINATED = "terminated"


@dataclass
class Task:
    """Atomic unit of work."""
    task_id: str
    description: str
    priority: int = 1  # 1-10, higher is more important
    dependencies: List[str] = field(default_factory=list)  # Task IDs this depends on
    status: TaskStatus = TaskStatus.PENDING
    assigned_to: Optional[str] = None  # Agent ID
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float = 0.0  # milliseconds
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "description": self.description,
            "priority": self.priority,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "assigned_to": self.assigned_to,
            "result": self.result,
            "error": self.error,
            "execution_time": self.execution_time,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
        }


@dataclass
class Agent:
    """Individual agent in swarm."""
    agent_id: str
    role: AgentRole
    capability_tags: List[str] = field(default_factory=list)
    status: AgentStatus = AgentStatus.IDLE
    current_task_id: Optional[str] = None
    completed_tasks: int = 0
    success_rate: float = 1.0
    response_time_avg: float = 0.0
    energy_level: float = 100.0  # Simulated energy
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_id": self.agent_id,
            "role": self.role.value,
            "capability_tags": self.capability_tags,
            "status": self.status.value,
            "current_task_id": self.current_task_id,
            "completed_tasks": self.completed_tasks,
            "success_rate": self.success_rate,
            "response_time_avg": self.response_time_avg,
            "energy_level": self.energy_level,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class SwarmMetrics:
    """Metrics about swarm performance."""
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    avg_task_time: float = 0.0
    avg_success_rate: float = 1.0
    swarm_efficiency: float = 0.0  # 0-1, tasks completed vs potential
    parallelization_degree: float = 1.0  # How parallel are tasks
    emergent_patterns: List[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "avg_task_time": self.avg_task_time,
            "avg_success_rate": self.avg_success_rate,
            "swarm_efficiency": self.swarm_efficiency,
            "parallelization_degree": self.parallelization_degree,
            "emergent_patterns": self.emergent_patterns,
            "last_updated": self.last_updated.isoformat(),
        }


class TaskDecomposer:
    """Decomposes complex tasks into subtasks."""

    def __init__(self):
        """Initialize decomposer."""
        self.decomposition_patterns = self._load_patterns()

    def _load_patterns(self) -> Dict[str, Callable]:
        """Load decomposition patterns."""
        return {
            "divide_and_conquer": self._divide_and_conquer,
            "pipeline": self._pipeline_decomposition,
            "map_reduce": self._map_reduce,
            "staged": self._staged_decomposition,
        }

    def decompose(
        self,
        task: Task,
        pattern: str = "divide_and_conquer",
        num_subtasks: int = 4,
    ) -> List[Task]:
        """Decompose task into subtasks."""
        if pattern not in self.decomposition_patterns:
            pattern = "divide_and_conquer"

        decomposer = self.decomposition_patterns[pattern]
        subtasks = decomposer(task, num_subtasks)

        # Set dependencies
        for i, subtask in enumerate(subtasks):
            if i > 0:
                subtask.dependencies = [subtasks[i - 1].task_id]

        return subtasks

    def _divide_and_conquer(self, task: Task, num_subtasks: int) -> List[Task]:
        """Divide task into independent subtasks."""
        subtasks = []
        for i in range(num_subtasks):
            subtask_id = f"{task.task_id}_sub_{i}"
            subtask = Task(
                task_id=subtask_id,
                description=f"Part {i+1}/{num_subtasks}: {task.description}",
                priority=task.priority,
                metadata={
                    "parent_task": task.task_id,
                    "part": i + 1,
                    "total_parts": num_subtasks,
                },
            )
            subtasks.append(subtask)
        return subtasks

    def _pipeline_decomposition(self, task: Task, num_stages: int) -> List[Task]:
        """Decompose into sequential pipeline stages."""
        subtasks = []
        stages = [
            "input_preparation",
            "processing",
            "validation",
            "output",
        ]
        stages = stages[:num_stages]

        for i, stage in enumerate(stages):
            subtask_id = f"{task.task_id}_{stage}"
            subtask = Task(
                task_id=subtask_id,
                description=f"{stage}: {task.description}",
                priority=task.priority,
                metadata={"parent_task": task.task_id, "stage": stage},
            )
            subtasks.append(subtask)
        return subtasks

    def _map_reduce(self, task: Task, num_mappers: int) -> List[Task]:
        """Decompose into map and reduce phases."""
        subtasks = []

        # Mapper tasks
        for i in range(num_mappers):
            mapper_task = Task(
                task_id=f"{task.task_id}_map_{i}",
                description=f"Map {i+1}: {task.description}",
                priority=task.priority,
                metadata={"parent_task": task.task_id, "phase": "map"},
            )
            subtasks.append(mapper_task)

        # Reduce task (depends on all mappers)
        reduce_task = Task(
            task_id=f"{task.task_id}_reduce",
            description=f"Reduce: {task.description}",
            priority=task.priority,
            dependencies=[st.task_id for st in subtasks],
            metadata={"parent_task": task.task_id, "phase": "reduce"},
        )
        subtasks.append(reduce_task)

        return subtasks

    def _staged_decomposition(self, task: Task, num_stages: int) -> List[Task]:
        """Decompose into numbered stages."""
        subtasks = []
        for i in range(num_stages):
            subtask = Task(
                task_id=f"{task.task_id}_stage_{i}",
                description=f"Stage {i+1}/{num_stages}: {task.description}",
                priority=task.priority,
                metadata={
                    "parent_task": task.task_id,
                    "stage_number": i + 1,
                    "total_stages": num_stages,
                },
            )
            subtasks.append(subtask)
        return subtasks


class CoordinationManager:
    """Manages agent coordination and synchronization."""

    def __init__(self):
        """Initialize coordinator."""
        self.task_graph: Dict[str, Set[str]] = {}  # task -> dependencies
        self.completed_tasks: Set[str] = set()
        self.locks: Dict[str, asyncio.Lock] = {}

    def add_dependency(self, task_id: str, depends_on: str) -> None:
        """Add task dependency."""
        if task_id not in self.task_graph:
            self.task_graph[task_id] = set()
        self.task_graph[task_id].add(depends_on)

    def can_execute(self, task_id: str) -> bool:
        """Check if task's dependencies are satisfied."""
        if task_id not in self.task_graph:
            return True

        dependencies = self.task_graph[task_id]
        return dependencies.issubset(self.completed_tasks)

    def mark_completed(self, task_id: str) -> None:
        """Mark task as completed."""
        self.completed_tasks.add(task_id)

    def get_next_executable(self, available_tasks: List[str]) -> Optional[str]:
        """Get next executable task from available list."""
        executable = [t for t in available_tasks if self.can_execute(t)]
        if not executable:
            return None

        # Prioritize by dependency chain
        return max(executable, key=lambda t: len(self.task_graph.get(t, set())))

    async def synchronize_barrier(self, task_ids: List[str]) -> None:
        """Wait for all tasks to complete."""
        while not all(t in self.completed_tasks for t in task_ids):
            await asyncio.sleep(0.1)


class SwarmIntelligence:
    """Implements emergent swarm intelligence patterns."""

    def __init__(self):
        """Initialize swarm intelligence."""
        self.pheromone_trails: Dict[str, float] = {}  # Task -> desirability
        self.patterns: List[str] = []

    def update_pheromone(self, task_id: str, success: bool, strength: float = 1.0) -> None:
        """Update pheromone trail (attraction/repulsion)."""
        current = self.pheromone_trails.get(task_id, 0.0)
        delta = strength if success else -strength * 0.5
        self.pheromone_trails[task_id] = max(0.0, current + delta)

    def get_task_attractiveness(self, task_id: str) -> float:
        """Get attractiveness of task to agents."""
        return self.pheromone_trails.get(task_id, 0.5)

    def detect_pattern(self, agent_behaviors: List[Dict[str, Any]]) -> Optional[str]:
        """Detect emergent patterns in swarm behavior."""
        if len(agent_behaviors) < 3:
            return None

        # Check for synchronization pattern
        active_count = sum(1 for b in agent_behaviors if b.get("active"))
        if active_count / len(agent_behaviors) > 0.8:
            return "synchronized_execution"

        # Check for specialization pattern
        roles = set(b.get("role") for b in agent_behaviors)
        if len(roles) > len(agent_behaviors) * 0.5:
            return "role_specialization"

        # Check for cascade pattern
        error_count = sum(1 for b in agent_behaviors if b.get("error"))
        if error_count > len(agent_behaviors) * 0.3:
            return "error_cascade"

        return None


class Swarm:
    """Main swarm orchestrator."""

    def __init__(self, swarm_id: str, num_agents: int = 4):
        """Initialize swarm."""
        self.swarm_id = swarm_id
        self.agents: Dict[str, Agent] = {}
        self.tasks: Dict[str, Task] = {}
        self.task_queue: List[str] = []
        self.decomposer = TaskDecomposer()
        self.coordinator = CoordinationManager()
        self.intelligence = SwarmIntelligence()
        self.metrics = SwarmMetrics()

        # Create agents
        self._create_agents(num_agents)

        self.created_at = datetime.now()

    def _create_agents(self, num_agents: int) -> None:
        """Create agents with different roles."""
        roles = [
            AgentRole.WORKER,
            AgentRole.WORKER,
            AgentRole.COORDINATOR,
            AgentRole.VALIDATOR,
        ]

        for i in range(num_agents):
            role = roles[i % len(roles)]
            agent = Agent(
                agent_id=f"{self.swarm_id}_agent_{i}",
                role=role,
                capability_tags=self._get_capability_tags(role),
            )
            self.agents[agent.agent_id] = agent

    def _get_capability_tags(self, role: AgentRole) -> List[str]:
        """Get capability tags for role."""
        tags = {
            AgentRole.WORKER: ["execute", "compute", "process"],
            AgentRole.COORDINATOR: ["coordinate", "schedule", "balance"],
            AgentRole.VALIDATOR: ["validate", "verify", "check"],
            AgentRole.ANALYZER: ["analyze", "optimize", "report"],
            AgentRole.MONITOR: ["monitor", "health", "metrics"],
            AgentRole.LEADER: ["lead", "decide", "strategize"],
        }
        return tags.get(role, ["general"])

    def submit_task(self, task: Task, decompose: bool = False) -> str:
        """Submit task to swarm."""
        self.tasks[task.task_id] = task
        self.task_queue.append(task.task_id)
        self.metrics.total_tasks += 1

        if decompose:
            subtasks = self.decomposer.decompose(task)
            for subtask in subtasks:
                self.tasks[subtask.task_id] = subtask
                self.task_queue.append(subtask.task_id)
                # Register dependencies
                for dep in subtask.dependencies:
                    self.coordinator.add_dependency(subtask.task_id, dep)

        return task.task_id

    def assign_task(self, task_id: str, agent_id: str) -> bool:
        """Assign task to agent."""
        if task_id not in self.tasks or agent_id not in self.agents:
            return False

        task = self.tasks[task_id]
        agent = self.agents[agent_id]

        # Check dependencies
        if not self.coordinator.can_execute(task_id):
            return False

        # Check agent availability
        if agent.status != AgentStatus.IDLE:
            return False

        # Assign
        task.assigned_to = agent_id
        task.status = TaskStatus.ASSIGNED
        agent.current_task_id = task_id
        agent.status = AgentStatus.BUSY

        return True

    def complete_task(self, task_id: str, result: Any, execution_time: float) -> None:
        """Mark task as completed."""
        task = self.tasks.get(task_id)
        if not task:
            return

        task.status = TaskStatus.COMPLETED
        task.result = result
        task.execution_time = execution_time
        task.completed_at = datetime.now()

        # Update coordinator
        self.coordinator.mark_completed(task_id)

        # Update agent
        if task.assigned_to:
            agent = self.agents.get(task.assigned_to)
            if agent:
                agent.status = AgentStatus.IDLE
                agent.current_task_id = None
                agent.completed_tasks += 1
                self.intelligence.update_pheromone(task_id, True)

        self.metrics.completed_tasks += 1

    def get_task_for_agent(self, agent_id: str) -> Optional[Task]:
        """Get next task for agent."""
        if agent_id not in self.agents:
            return None

        agent = self.agents[agent_id]

        # Find executable tasks
        available = [t for t in self.task_queue if self.tasks[t].status == TaskStatus.PENDING]
        executable = [t for t in available if self.coordinator.can_execute(t)]

        if not executable:
            return None

        # Sort by attractiveness and priority
        executable.sort(
            key=lambda t: (
                -self.tasks[t].priority,
                -self.intelligence.get_task_attractiveness(t),
            )
        )

        task = self.tasks[executable[0]]
        return task

    def get_swarm_status(self) -> Dict[str, Any]:
        """Get overall swarm status."""
        agent_statuses = [a.status.value for a in self.agents.values()]
        active_agents = sum(1 for s in agent_statuses if s == "busy")

        completed = len([t for t in self.tasks.values() if t.status == TaskStatus.COMPLETED])
        failed = len([t for t in self.tasks.values() if t.status == TaskStatus.FAILED])

        return {
            "swarm_id": self.swarm_id,
            "num_agents": len(self.agents),
            "active_agents": active_agents,
            "total_tasks": self.metrics.total_tasks,
            "completed_tasks": completed,
            "failed_tasks": failed,
            "pending_tasks": len([t for t in self.tasks.values() if t.status == TaskStatus.PENDING]),
            "agent_statuses": agent_statuses,
            "efficiency": completed / self.metrics.total_tasks if self.metrics.total_tasks > 0 else 0,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "swarm_id": self.swarm_id,
            "num_agents": len(self.agents),
            "agents": [a.to_dict() for a in self.agents.values()],
            "tasks": [t.to_dict() for t in self.tasks.values()],
            "metrics": self.metrics.to_dict(),
            "status": self.get_swarm_status(),
        }


class SwarmOrchestrator:
    """Orchestrates multiple swarms."""

    def __init__(self):
        """Initialize orchestrator."""
        self.swarms: Dict[str, Swarm] = {}
        self.global_metrics: Dict[str, float] = {}

    def create_swarm(self, num_agents: int = 4) -> Swarm:
        """Create new swarm."""
        swarm_id = f"swarm_{len(self.swarms)}_{datetime.now().timestamp()}"
        swarm = Swarm(swarm_id, num_agents)
        self.swarms[swarm_id] = swarm
        return swarm

    def get_swarm(self, swarm_id: str) -> Optional[Swarm]:
        """Get swarm by ID."""
        return self.swarms.get(swarm_id)

    def get_orchestrator_status(self) -> Dict[str, Any]:
        """Get status of all swarms."""
        return {
            "num_swarms": len(self.swarms),
            "swarms": {sid: s.get_swarm_status() for sid, s in self.swarms.items()},
            "total_tasks": sum(s.metrics.total_tasks for s in self.swarms.values()),
            "total_completed": sum(
                len([t for t in s.tasks.values() if t.status == TaskStatus.COMPLETED])
                for s in self.swarms.values()
            ),
        }


# Global swarm orchestrator
_orchestrator = None


def get_swarm_orchestrator() -> SwarmOrchestrator:
    """Get or create global swarm orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = SwarmOrchestrator()
    return _orchestrator
