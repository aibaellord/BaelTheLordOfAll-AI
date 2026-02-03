#!/usr/bin/env python3
"""
BAEL - Advanced Task Decomposer
Hierarchical task decomposition and planning system.

This module implements sophisticated task decomposition
capabilities for breaking down complex objectives into
executable sub-tasks with dependency management.

Features:
- Hierarchical task breakdown
- Dependency graph construction
- Parallel task identification
- Critical path analysis
- Task estimation
- Constraint propagation
- Dynamic decomposition
- Template-based decomposition
- Recursive refinement
- Task prioritization
- Resource requirement analysis
- Completion tracking
"""

import asyncio
import hashlib
import json
import logging
import math
import re
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    TypeVar, Union)
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class TaskStatus(Enum):
    """Status of a task."""
    PENDING = "pending"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Priority levels for tasks."""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5


class DependencyType(Enum):
    """Types of task dependencies."""
    FINISH_TO_START = "finish_to_start"
    START_TO_START = "start_to_start"
    FINISH_TO_FINISH = "finish_to_finish"
    START_TO_FINISH = "start_to_finish"


class DecompositionStrategy(Enum):
    """Strategies for task decomposition."""
    RECURSIVE = "recursive"
    TEMPLATE = "template"
    GOAL_BASED = "goal_based"
    KNOWLEDGE_BASED = "knowledge_based"
    HYBRID = "hybrid"


class TaskType(Enum):
    """Types of tasks."""
    ATOMIC = "atomic"
    COMPOSITE = "composite"
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    CONDITIONAL = "conditional"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ResourceRequirement:
    """Resource requirement for a task."""
    resource_type: str = ""
    amount: float = 0.0
    unit: str = ""
    optional: bool = False


@dataclass
class TaskConstraint:
    """A constraint on task execution."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    type: str = ""
    expression: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Dependency:
    """A dependency between tasks."""
    id: str = field(default_factory=lambda: str(uuid4()))
    source_task_id: str = ""
    target_task_id: str = ""
    type: DependencyType = DependencyType.FINISH_TO_START
    lag: timedelta = field(default_factory=lambda: timedelta(0))
    condition: Optional[str] = None


@dataclass
class TaskEstimate:
    """Time and resource estimates for a task."""
    optimistic_hours: float = 0.0
    most_likely_hours: float = 0.0
    pessimistic_hours: float = 0.0
    confidence: float = 0.5

    @property
    def expected_hours(self) -> float:
        """Calculate expected duration using PERT formula."""
        return (
            self.optimistic_hours +
            4 * self.most_likely_hours +
            self.pessimistic_hours
        ) / 6

    @property
    def std_deviation(self) -> float:
        """Calculate standard deviation."""
        return (self.pessimistic_hours - self.optimistic_hours) / 6


@dataclass
class DecomposableTask:
    """A task in the decomposition hierarchy."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    type: TaskType = TaskType.ATOMIC
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    dependencies: List[Dependency] = field(default_factory=list)
    resources: List[ResourceRequirement] = field(default_factory=list)
    constraints: List[TaskConstraint] = field(default_factory=list)
    estimate: TaskEstimate = field(default_factory=TaskEstimate)
    depth: int = 0
    progress: float = 0.0
    output: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class DecompositionTemplate:
    """Template for decomposing tasks of a certain type."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    pattern: str = ""
    sub_tasks: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DecompositionResult:
    """Result of task decomposition."""
    root_task: DecomposableTask = None
    all_tasks: Dict[str, DecomposableTask] = field(default_factory=dict)
    dependency_graph: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    critical_path: List[str] = field(default_factory=list)
    parallelizable_groups: List[List[str]] = field(default_factory=list)
    total_estimated_hours: float = 0.0
    max_depth: int = 0


# =============================================================================
# DEPENDENCY GRAPH
# =============================================================================

class TaskDependencyGraph:
    """Manages task dependencies as a directed graph."""

    def __init__(self):
        self.nodes: Dict[str, DecomposableTask] = {}
        self.edges: Dict[str, List[Dependency]] = defaultdict(list)
        self.reverse_edges: Dict[str, List[str]] = defaultdict(list)

    def add_task(self, task: DecomposableTask) -> None:
        """Add a task to the graph."""
        self.nodes[task.id] = task

    def add_dependency(self, dependency: Dependency) -> None:
        """Add a dependency edge."""
        self.edges[dependency.source_task_id].append(dependency)
        self.reverse_edges[dependency.target_task_id].append(dependency.source_task_id)

    def get_dependencies(self, task_id: str) -> List[DecomposableTask]:
        """Get all tasks that this task depends on."""
        predecessors = self.reverse_edges.get(task_id, [])
        return [self.nodes[pid] for pid in predecessors if pid in self.nodes]

    def get_dependents(self, task_id: str) -> List[DecomposableTask]:
        """Get all tasks that depend on this task."""
        deps = self.edges.get(task_id, [])
        return [self.nodes[d.target_task_id] for d in deps if d.target_task_id in self.nodes]

    def topological_sort(self) -> List[str]:
        """Return tasks in topological order."""
        in_degree = defaultdict(int)

        for node_id in self.nodes:
            in_degree[node_id] = len(self.reverse_edges.get(node_id, []))

        queue = deque([n for n in self.nodes if in_degree[n] == 0])
        result = []

        while queue:
            node_id = queue.popleft()
            result.append(node_id)

            for dep in self.edges.get(node_id, []):
                target = dep.target_task_id
                in_degree[target] -= 1
                if in_degree[target] == 0:
                    queue.append(target)

        if len(result) != len(self.nodes):
            logger.warning("Dependency cycle detected in task graph")

        return result

    def find_critical_path(self) -> Tuple[List[str], float]:
        """Find the critical path through the graph."""
        earliest_start: Dict[str, float] = {}
        earliest_finish: Dict[str, float] = {}

        for task_id in self.topological_sort():
            task = self.nodes[task_id]

            predecessors = self.reverse_edges.get(task_id, [])
            if not predecessors:
                earliest_start[task_id] = 0
            else:
                earliest_start[task_id] = max(
                    earliest_finish.get(p, 0) for p in predecessors
                )

            earliest_finish[task_id] = (
                earliest_start[task_id] + task.estimate.expected_hours
            )

        end_nodes = [
            n for n in self.nodes
            if not self.edges.get(n, [])
        ]

        if not end_nodes:
            return [], 0.0

        latest_end = max(end_nodes, key=lambda n: earliest_finish.get(n, 0))
        total_duration = earliest_finish.get(latest_end, 0)

        critical_path = []
        current = latest_end

        while current:
            critical_path.insert(0, current)
            predecessors = self.reverse_edges.get(current, [])

            if not predecessors:
                break

            current_start = earliest_start[current]
            for pred in predecessors:
                if abs(earliest_finish.get(pred, 0) - current_start) < 0.001:
                    current = pred
                    break
            else:
                break

        return critical_path, total_duration

    def find_parallel_groups(self) -> List[List[str]]:
        """Find groups of tasks that can run in parallel."""
        levels: Dict[str, int] = {}

        for task_id in self.topological_sort():
            predecessors = self.reverse_edges.get(task_id, [])
            if not predecessors:
                levels[task_id] = 0
            else:
                levels[task_id] = max(levels.get(p, 0) for p in predecessors) + 1

        level_groups: Dict[int, List[str]] = defaultdict(list)
        for task_id, level in levels.items():
            level_groups[level].append(task_id)

        return [tasks for level, tasks in sorted(level_groups.items())]

    def detect_cycles(self) -> List[List[str]]:
        """Detect and return all cycles in the graph."""
        cycles = []
        visited = set()
        rec_stack = set()
        path = []

        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)

            for dep in self.edges.get(node_id, []):
                target = dep.target_task_id
                if target not in visited:
                    if dfs(target):
                        return True
                elif target in rec_stack:
                    cycle_start = path.index(target)
                    cycles.append(path[cycle_start:])
                    return True

            path.pop()
            rec_stack.remove(node_id)
            return False

        for node_id in self.nodes:
            if node_id not in visited:
                dfs(node_id)

        return cycles


# =============================================================================
# DECOMPOSITION STRATEGIES
# =============================================================================

class DecompositionStrategyBase(ABC):
    """Base class for decomposition strategies."""

    @abstractmethod
    async def decompose(
        self,
        task: DecomposableTask,
        context: Dict[str, Any]
    ) -> List[DecomposableTask]:
        """Decompose a task into sub-tasks."""
        pass


class RecursiveTaskDecomposition(DecompositionStrategyBase):
    """Recursive decomposition strategy."""

    def __init__(self, max_depth: int = 5, min_hours: float = 1.0):
        self.max_depth = max_depth
        self.min_hours = min_hours
        self.decomposition_rules: List[Callable] = []

    def add_rule(self, rule: Callable[[DecomposableTask], List[Dict[str, Any]]]) -> None:
        """Add a decomposition rule."""
        self.decomposition_rules.append(rule)

    async def decompose(
        self,
        task: DecomposableTask,
        context: Dict[str, Any]
    ) -> List[DecomposableTask]:
        """Recursively decompose task."""
        if task.depth >= self.max_depth:
            return []

        if task.estimate.expected_hours <= self.min_hours:
            task.type = TaskType.ATOMIC
            return []

        sub_task_specs = []
        for rule in self.decomposition_rules:
            specs = rule(task)
            if specs:
                sub_task_specs = specs
                break

        if not sub_task_specs:
            sub_task_specs = self._default_decomposition(task)

        sub_tasks = []
        for spec in sub_task_specs:
            sub_task = DecomposableTask(
                name=spec.get("name", f"Sub-task of {task.name}"),
                description=spec.get("description", ""),
                type=spec.get("type", TaskType.ATOMIC),
                priority=task.priority,
                parent_id=task.id,
                depth=task.depth + 1,
                estimate=TaskEstimate(
                    most_likely_hours=spec.get("hours", 1.0),
                    optimistic_hours=spec.get("hours", 1.0) * 0.7,
                    pessimistic_hours=spec.get("hours", 1.0) * 1.5
                )
            )
            sub_tasks.append(sub_task)
            task.children_ids.append(sub_task.id)

        task.type = TaskType.COMPOSITE
        return sub_tasks

    def _default_decomposition(self, task: DecomposableTask) -> List[Dict[str, Any]]:
        """Default decomposition into 3 sub-tasks."""
        hours = task.estimate.expected_hours / 3
        return [
            {"name": f"{task.name} - Setup", "hours": hours * 0.2},
            {"name": f"{task.name} - Execute", "hours": hours * 0.6},
            {"name": f"{task.name} - Finalize", "hours": hours * 0.2}
        ]


class TemplateTaskDecomposition(DecompositionStrategyBase):
    """Template-based decomposition strategy."""

    def __init__(self):
        self.templates: Dict[str, DecompositionTemplate] = {}

    def add_template(self, template: DecompositionTemplate) -> None:
        """Add a decomposition template."""
        self.templates[template.name] = template

    async def decompose(
        self,
        task: DecomposableTask,
        context: Dict[str, Any]
    ) -> List[DecomposableTask]:
        """Decompose using matching template."""
        matching_template = None

        for template in self.templates.values():
            if template.pattern:
                if re.match(template.pattern, task.name, re.IGNORECASE):
                    matching_template = template
                    break
            elif template.name.lower() in task.name.lower():
                matching_template = template
                break

        if not matching_template:
            return []

        sub_tasks = []
        for spec in matching_template.sub_tasks:
            sub_task = DecomposableTask(
                name=spec.get("name", "").format(task_name=task.name),
                description=spec.get("description", ""),
                type=TaskType(spec.get("type", "atomic")),
                priority=task.priority,
                parent_id=task.id,
                depth=task.depth + 1,
                estimate=TaskEstimate(
                    most_likely_hours=spec.get("hours", 1.0)
                )
            )
            sub_tasks.append(sub_task)
            task.children_ids.append(sub_task.id)

        task.type = TaskType.COMPOSITE
        return sub_tasks


class GoalBasedTaskDecomposition(DecompositionStrategyBase):
    """Goal-based decomposition strategy."""

    async def decompose(
        self,
        task: DecomposableTask,
        context: Dict[str, Any]
    ) -> List[DecomposableTask]:
        """Decompose based on goals in task description."""
        goals = self._extract_goals(task.description)

        if not goals:
            return []

        sub_tasks = []
        hours_per_goal = task.estimate.expected_hours / len(goals)

        for i, goal in enumerate(goals):
            sub_task = DecomposableTask(
                name=f"Achieve: {goal}",
                description=f"Complete the goal: {goal}",
                type=TaskType.ATOMIC,
                priority=task.priority,
                parent_id=task.id,
                depth=task.depth + 1,
                estimate=TaskEstimate(most_likely_hours=hours_per_goal)
            )
            sub_tasks.append(sub_task)
            task.children_ids.append(sub_task.id)

        task.type = TaskType.COMPOSITE
        return sub_tasks

    def _extract_goals(self, description: str) -> List[str]:
        """Extract goals from description."""
        goals = []

        numbered = re.findall(r'\d+\.\s*(.+?)(?=\d+\.|$)', description, re.DOTALL)
        if numbered:
            goals.extend([g.strip() for g in numbered if g.strip()])

        bullets = re.findall(r'[-*•]\s*(.+?)(?=[-*•]|$)', description, re.DOTALL)
        if bullets:
            goals.extend([g.strip() for g in bullets if g.strip()])

        return goals[:10]


# =============================================================================
# ADVANCED TASK DECOMPOSER
# =============================================================================

class AdvancedTaskDecomposer:
    """
    Advanced task decomposition system for BAEL.

    Provides hierarchical task breakdown with multiple
    strategies and dependency management.
    """

    def __init__(self):
        self.strategies: Dict[DecompositionStrategy, DecompositionStrategyBase] = {
            DecompositionStrategy.RECURSIVE: RecursiveTaskDecomposition(),
            DecompositionStrategy.TEMPLATE: TemplateTaskDecomposition(),
            DecompositionStrategy.GOAL_BASED: GoalBasedTaskDecomposition()
        }
        self.dependency_graph = TaskDependencyGraph()
        self.tasks: Dict[str, DecomposableTask] = {}
        self.templates: List[DecompositionTemplate] = []

        self._init_default_templates()

    def _init_default_templates(self) -> None:
        """Initialize default decomposition templates."""
        template_strategy = self.strategies[DecompositionStrategy.TEMPLATE]

        template_strategy.add_template(DecompositionTemplate(
            name="development",
            pattern=r"(develop|create|build|implement).*",
            sub_tasks=[
                {"name": "Design {task_name}", "hours": 2.0, "type": "atomic"},
                {"name": "Implement {task_name}", "hours": 4.0, "type": "atomic"},
                {"name": "Test {task_name}", "hours": 2.0, "type": "atomic"},
                {"name": "Document {task_name}", "hours": 1.0, "type": "atomic"}
            ]
        ))

        template_strategy.add_template(DecompositionTemplate(
            name="research",
            pattern=r"(research|investigate|analyze|study).*",
            sub_tasks=[
                {"name": "Define scope for {task_name}", "hours": 1.0},
                {"name": "Gather information for {task_name}", "hours": 3.0},
                {"name": "Analyze findings for {task_name}", "hours": 2.0},
                {"name": "Compile results for {task_name}", "hours": 1.0}
            ]
        ))

        template_strategy.add_template(DecompositionTemplate(
            name="integration",
            pattern=r"(integrate|connect|link|combine).*",
            sub_tasks=[
                {"name": "Analyze interfaces for {task_name}", "hours": 1.0},
                {"name": "Develop adapters for {task_name}", "hours": 3.0},
                {"name": "Test integration for {task_name}", "hours": 2.0},
                {"name": "Deploy {task_name}", "hours": 1.0}
            ]
        ))

        template_strategy.add_template(DecompositionTemplate(
            name="optimization",
            pattern=r"(optimize|improve|enhance|refactor).*",
            sub_tasks=[
                {"name": "Profile {task_name}", "hours": 1.0},
                {"name": "Identify bottlenecks for {task_name}", "hours": 1.5},
                {"name": "Implement optimizations for {task_name}", "hours": 3.0},
                {"name": "Benchmark {task_name}", "hours": 1.5}
            ]
        ))

    async def decompose(
        self,
        task_name: str,
        description: str = "",
        estimated_hours: float = 8.0,
        strategy: DecompositionStrategy = DecompositionStrategy.HYBRID,
        max_depth: int = 5,
        context: Dict[str, Any] = None
    ) -> DecompositionResult:
        """Decompose a task into a hierarchy of sub-tasks."""
        context = context or {}

        root_task = DecomposableTask(
            name=task_name,
            description=description,
            type=TaskType.COMPOSITE,
            estimate=TaskEstimate(
                most_likely_hours=estimated_hours,
                optimistic_hours=estimated_hours * 0.7,
                pessimistic_hours=estimated_hours * 1.5
            ),
            depth=0
        )

        self.tasks[root_task.id] = root_task
        self.dependency_graph.add_task(root_task)

        tasks_to_process = [root_task]
        all_tasks = {root_task.id: root_task}

        while tasks_to_process:
            current_task = tasks_to_process.pop(0)

            if current_task.depth >= max_depth:
                current_task.type = TaskType.ATOMIC
                continue

            sub_tasks = await self._apply_strategy(
                current_task, strategy, context
            )

            for sub_task in sub_tasks:
                all_tasks[sub_task.id] = sub_task
                self.tasks[sub_task.id] = sub_task
                self.dependency_graph.add_task(sub_task)
                tasks_to_process.append(sub_task)

        self._create_default_dependencies(root_task, all_tasks)

        critical_path, total_hours = self.dependency_graph.find_critical_path()
        parallel_groups = self.dependency_graph.find_parallel_groups()
        max_depth_found = max(t.depth for t in all_tasks.values())

        return DecompositionResult(
            root_task=root_task,
            all_tasks=all_tasks,
            dependency_graph=dict(self.dependency_graph.edges),
            critical_path=critical_path,
            parallelizable_groups=parallel_groups,
            total_estimated_hours=total_hours,
            max_depth=max_depth_found
        )

    async def _apply_strategy(
        self,
        task: DecomposableTask,
        strategy: DecompositionStrategy,
        context: Dict[str, Any]
    ) -> List[DecomposableTask]:
        """Apply decomposition strategy."""
        if strategy == DecompositionStrategy.HYBRID:
            sub_tasks = await self.strategies[DecompositionStrategy.TEMPLATE].decompose(
                task, context
            )
            if not sub_tasks:
                sub_tasks = await self.strategies[DecompositionStrategy.RECURSIVE].decompose(
                    task, context
                )
            return sub_tasks
        else:
            decomposer = self.strategies.get(strategy)
            if decomposer:
                return await decomposer.decompose(task, context)
            return []

    def _create_default_dependencies(
        self,
        parent: DecomposableTask,
        all_tasks: Dict[str, DecomposableTask]
    ) -> None:
        """Create sequential dependencies between sibling tasks."""
        children = [
            all_tasks[cid] for cid in parent.children_ids
            if cid in all_tasks
        ]

        for i in range(len(children) - 1):
            dependency = Dependency(
                source_task_id=children[i].id,
                target_task_id=children[i + 1].id,
                type=DependencyType.FINISH_TO_START
            )
            children[i].dependencies.append(dependency)
            self.dependency_graph.add_dependency(dependency)

        for child in children:
            if child.children_ids:
                self._create_default_dependencies(child, all_tasks)

    def add_dependency(
        self,
        source_task_id: str,
        target_task_id: str,
        dependency_type: DependencyType = DependencyType.FINISH_TO_START
    ) -> bool:
        """Add a custom dependency between tasks."""
        if source_task_id not in self.tasks or target_task_id not in self.tasks:
            return False

        dependency = Dependency(
            source_task_id=source_task_id,
            target_task_id=target_task_id,
            type=dependency_type
        )

        self.tasks[source_task_id].dependencies.append(dependency)
        self.dependency_graph.add_dependency(dependency)

        cycles = self.dependency_graph.detect_cycles()
        if cycles:
            logger.warning(f"Cycle detected after adding dependency: {cycles}")

        return True

    def get_ready_tasks(self) -> List[DecomposableTask]:
        """Get all tasks that are ready to execute."""
        ready = []

        for task in self.tasks.values():
            if task.status != TaskStatus.PENDING:
                continue

            if task.type != TaskType.ATOMIC:
                continue

            dependencies_met = True
            for dep_id in self.dependency_graph.reverse_edges.get(task.id, []):
                dep_task = self.tasks.get(dep_id)
                if dep_task and dep_task.status != TaskStatus.COMPLETED:
                    dependencies_met = False
                    break

            if dependencies_met:
                ready.append(task)

        return sorted(ready, key=lambda t: t.priority.value)

    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        output: Any = None,
        error: str = None
    ) -> bool:
        """Update task status and propagate changes."""
        task = self.tasks.get(task_id)
        if not task:
            return False

        old_status = task.status
        task.status = status
        task.output = output
        task.error = error

        if status == TaskStatus.IN_PROGRESS and not task.started_at:
            task.started_at = datetime.now()
        elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            task.completed_at = datetime.now()

        if status == TaskStatus.COMPLETED:
            task.progress = 100.0
            self._propagate_progress(task)

        return True

    def _propagate_progress(self, task: DecomposableTask) -> None:
        """Propagate progress to parent tasks."""
        if not task.parent_id:
            return

        parent = self.tasks.get(task.parent_id)
        if not parent:
            return

        children = [
            self.tasks[cid] for cid in parent.children_ids
            if cid in self.tasks
        ]

        if children:
            parent.progress = sum(c.progress for c in children) / len(children)

            if all(c.status == TaskStatus.COMPLETED for c in children):
                parent.status = TaskStatus.COMPLETED
                parent.completed_at = datetime.now()
                self._propagate_progress(parent)

    def get_task_tree(self, task_id: str = None) -> Dict[str, Any]:
        """Get task hierarchy as a tree structure."""
        if task_id:
            root = self.tasks.get(task_id)
        else:
            roots = [t for t in self.tasks.values() if not t.parent_id]
            if not roots:
                return {}
            root = roots[0]

        if not root:
            return {}

        def build_tree(task: DecomposableTask) -> Dict[str, Any]:
            children = [
                build_tree(self.tasks[cid])
                for cid in task.children_ids
                if cid in self.tasks
            ]

            return {
                "id": task.id,
                "name": task.name,
                "type": task.type.value,
                "status": task.status.value,
                "priority": task.priority.value,
                "progress": task.progress,
                "estimated_hours": task.estimate.expected_hours,
                "depth": task.depth,
                "children": children
            }

        return build_tree(root)

    def estimate_completion_time(self) -> Dict[str, Any]:
        """Estimate overall completion time."""
        critical_path, duration = self.dependency_graph.find_critical_path()

        total_variance = sum(
            self.tasks[tid].estimate.std_deviation ** 2
            for tid in critical_path
            if tid in self.tasks
        )
        std_dev = math.sqrt(total_variance)

        return {
            "expected_hours": duration,
            "optimistic_hours": duration - 2 * std_dev,
            "pessimistic_hours": duration + 2 * std_dev,
            "confidence_90_hours": duration + 1.28 * std_dev,
            "critical_path_length": len(critical_path),
            "critical_path_tasks": [
                self.tasks[tid].name for tid in critical_path if tid in self.tasks
            ]
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Advanced Task Decomposer."""
    print("=" * 70)
    print("BAEL - ADVANCED TASK DECOMPOSER DEMO")
    print("Hierarchical Task Breakdown")
    print("=" * 70)
    print()

    decomposer = AdvancedTaskDecomposer()

    # 1. Simple Decomposition
    print("1. TASK DECOMPOSITION:")
    print("-" * 40)

    result = await decomposer.decompose(
        task_name="Develop BAEL Core Module",
        description="""
        Create the core module with:
        1. Event handling system
        2. State management
        3. Plugin architecture
        4. API interfaces
        """,
        estimated_hours=40.0,
        strategy=DecompositionStrategy.TEMPLATE
    )

    print(f"   Root Task: {result.root_task.name}")
    print(f"   Total Tasks: {len(result.all_tasks)}")
    print(f"   Max Depth: {result.max_depth}")
    print(f"   Estimated Hours: {result.total_estimated_hours:.1f}")
    print()

    # 2. Task Tree
    print("2. TASK HIERARCHY:")
    print("-" * 40)

    def print_tree(node: Dict, indent: int = 0):
        prefix = "   " + "  " * indent
        status_icon = "✓" if node["status"] == "completed" else "○"
        print(f"{prefix}{status_icon} {node['name']} ({node['estimated_hours']:.1f}h)")
        for child in node.get("children", []):
            print_tree(child, indent + 1)

    tree = decomposer.get_task_tree()
    print_tree(tree)
    print()

    # 3. Critical Path
    print("3. CRITICAL PATH ANALYSIS:")
    print("-" * 40)

    completion = decomposer.estimate_completion_time()
    print(f"   Expected: {completion['expected_hours']:.1f} hours")
    print(f"   Optimistic: {completion['optimistic_hours']:.1f} hours")
    print(f"   Pessimistic: {completion['pessimistic_hours']:.1f} hours")
    print()

    # 4. Ready Tasks
    print("4. READY TASKS:")
    print("-" * 40)

    ready = decomposer.get_ready_tasks()
    for task in ready[:5]:
        print(f"   - {task.name} (Priority: {task.priority.name})")
    print()

    # 5. Parallel Groups
    print("5. PARALLELIZABLE GROUPS:")
    print("-" * 40)

    for i, group in enumerate(result.parallelizable_groups[:3]):
        task_names = [
            decomposer.tasks[tid].name
            for tid in group if tid in decomposer.tasks
        ][:3]
        print(f"   Level {i}: {', '.join(task_names)}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Task Decomposer Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
