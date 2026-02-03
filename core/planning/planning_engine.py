#!/usr/bin/env python3
"""
BAEL - Planning Engine
Advanced planning and goal decomposition for AI agents.

Features:
- Goal decomposition
- Task planning
- Plan execution
- Dependency resolution
- Plan optimization
- Partial order planning
- Hierarchical task networks
- Plan monitoring
"""

import asyncio
import copy
import hashlib
import json
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Awaitable, Callable, Dict, Generic, Iterator, List,
                    Optional, Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class PlanStatus(Enum):
    """Plan status."""
    DRAFT = "draft"
    READY = "ready"
    EXECUTING = "executing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStatus(Enum):
    """Task status."""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class GoalPriority(Enum):
    """Goal priority."""
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    OPTIONAL = 1


class DependencyType(Enum):
    """Dependency type."""
    FINISH_TO_START = "finish_to_start"
    START_TO_START = "start_to_start"
    FINISH_TO_FINISH = "finish_to_finish"
    START_TO_FINISH = "start_to_finish"


class PlanType(Enum):
    """Plan type."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HIERARCHICAL = "hierarchical"
    CONDITIONAL = "conditional"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Goal:
    """Agent goal."""
    goal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    priority: GoalPriority = GoalPriority.MEDIUM
    deadline: Optional[datetime] = None
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)
    subgoals: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    """Plan task."""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    action: Optional[Callable] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    estimated_duration: float = 0.0
    actual_duration: float = 0.0
    retries: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Dependency:
    """Task dependency."""
    from_task: str
    to_task: str
    dep_type: DependencyType = DependencyType.FINISH_TO_START
    lag: float = 0.0


@dataclass
class Plan:
    """Execution plan."""
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    goal_id: Optional[str] = None
    tasks: List[Task] = field(default_factory=list)
    dependencies: List[Dependency] = field(default_factory=list)
    status: PlanStatus = PlanStatus.DRAFT
    plan_type: PlanType = PlanType.SEQUENTIAL
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanStats:
    """Plan statistics."""
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    pending_tasks: int = 0
    total_duration: float = 0.0
    avg_task_duration: float = 0.0


@dataclass
class ExecutionStep:
    """Plan execution step."""
    step_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str = ""
    action: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    result: Any = None
    error: Optional[str] = None


# =============================================================================
# GOAL MANAGER
# =============================================================================

class GoalManager:
    """Manage agent goals."""

    def __init__(self):
        self._goals: Dict[str, Goal] = {}
        self._active_goals: Set[str] = set()

    def create_goal(
        self,
        name: str,
        description: str = "",
        priority: GoalPriority = GoalPriority.MEDIUM,
        deadline: Optional[datetime] = None
    ) -> Goal:
        """Create goal."""
        goal = Goal(
            name=name,
            description=description,
            priority=priority,
            deadline=deadline
        )

        self._goals[goal.goal_id] = goal
        return goal

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Get goal."""
        return self._goals.get(goal_id)

    def add_subgoal(
        self,
        parent_id: str,
        subgoal_id: str
    ) -> bool:
        """Add subgoal."""
        parent = self._goals.get(parent_id)
        if parent:
            parent.subgoals.append(subgoal_id)
            return True
        return False

    def add_precondition(
        self,
        goal_id: str,
        condition: str
    ) -> bool:
        """Add precondition."""
        goal = self._goals.get(goal_id)
        if goal:
            goal.preconditions.append(condition)
            return True
        return False

    def add_postcondition(
        self,
        goal_id: str,
        condition: str
    ) -> bool:
        """Add postcondition."""
        goal = self._goals.get(goal_id)
        if goal:
            goal.postconditions.append(condition)
            return True
        return False

    def activate_goal(self, goal_id: str) -> bool:
        """Activate goal."""
        if goal_id in self._goals:
            self._active_goals.add(goal_id)
            return True
        return False

    def deactivate_goal(self, goal_id: str) -> bool:
        """Deactivate goal."""
        if goal_id in self._active_goals:
            self._active_goals.discard(goal_id)
            return True
        return False

    def get_active_goals(self) -> List[Goal]:
        """Get active goals."""
        return [self._goals[gid] for gid in self._active_goals if gid in self._goals]

    def prioritize_goals(self) -> List[Goal]:
        """Get goals sorted by priority."""
        active = self.get_active_goals()
        return sorted(active, key=lambda g: g.priority.value, reverse=True)


# =============================================================================
# TASK BUILDER
# =============================================================================

class TaskBuilder:
    """Build tasks."""

    def __init__(self):
        self._task = Task()

    def name(self, name: str) -> "TaskBuilder":
        """Set name."""
        self._task.name = name
        return self

    def description(self, description: str) -> "TaskBuilder":
        """Set description."""
        self._task.description = description
        return self

    def action(self, action: Callable) -> "TaskBuilder":
        """Set action."""
        self._task.action = action
        return self

    def parameter(self, key: str, value: Any) -> "TaskBuilder":
        """Set parameter."""
        self._task.parameters[key] = value
        return self

    def depends_on(self, task_id: str) -> "TaskBuilder":
        """Add dependency."""
        self._task.dependencies.append(task_id)
        return self

    def estimated_duration(self, seconds: float) -> "TaskBuilder":
        """Set estimated duration."""
        self._task.estimated_duration = seconds
        return self

    def max_retries(self, retries: int) -> "TaskBuilder":
        """Set max retries."""
        self._task.max_retries = retries
        return self

    def build(self) -> Task:
        """Build task."""
        task = self._task
        self._task = Task()
        return task


# =============================================================================
# PLAN BUILDER
# =============================================================================

class PlanBuilder:
    """Build plans."""

    def __init__(self, name: str = ""):
        self._plan = Plan(name=name)
        self._task_map: Dict[str, Task] = {}

    def name(self, name: str) -> "PlanBuilder":
        """Set name."""
        self._plan.name = name
        return self

    def goal(self, goal_id: str) -> "PlanBuilder":
        """Set goal."""
        self._plan.goal_id = goal_id
        return self

    def plan_type(self, plan_type: PlanType) -> "PlanBuilder":
        """Set plan type."""
        self._plan.plan_type = plan_type
        return self

    def add_task(self, task: Task) -> "PlanBuilder":
        """Add task."""
        self._plan.tasks.append(task)
        self._task_map[task.task_id] = task
        return self

    def add_dependency(
        self,
        from_task: str,
        to_task: str,
        dep_type: DependencyType = DependencyType.FINISH_TO_START
    ) -> "PlanBuilder":
        """Add dependency."""
        dep = Dependency(
            from_task=from_task,
            to_task=to_task,
            dep_type=dep_type
        )
        self._plan.dependencies.append(dep)
        return self

    def build(self) -> Plan:
        """Build plan."""
        plan = self._plan
        self._plan = Plan()
        return plan


# =============================================================================
# DEPENDENCY RESOLVER
# =============================================================================

class DependencyResolver:
    """Resolve task dependencies."""

    def __init__(self):
        self._graph: Dict[str, Set[str]] = defaultdict(set)
        self._reverse_graph: Dict[str, Set[str]] = defaultdict(set)

    def add_dependency(
        self,
        from_task: str,
        to_task: str
    ) -> None:
        """Add dependency."""
        self._graph[from_task].add(to_task)
        self._reverse_graph[to_task].add(from_task)

    def get_dependencies(self, task_id: str) -> Set[str]:
        """Get task dependencies."""
        return self._reverse_graph.get(task_id, set())

    def get_dependents(self, task_id: str) -> Set[str]:
        """Get dependent tasks."""
        return self._graph.get(task_id, set())

    def topological_sort(self, task_ids: List[str]) -> List[str]:
        """Sort tasks topologically."""
        in_degree = {tid: 0 for tid in task_ids}

        for tid in task_ids:
            for dep in self._reverse_graph.get(tid, set()):
                if dep in in_degree:
                    in_degree[tid] += 1

        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        result = []

        while queue:
            task = queue.pop(0)
            result.append(task)

            for dependent in self._graph.get(task, set()):
                if dependent in in_degree:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

        if len(result) != len(task_ids):
            raise ValueError("Circular dependency detected")

        return result

    def detect_cycles(self, task_ids: List[str]) -> List[List[str]]:
        """Detect cycles in dependencies."""
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(task: str, path: List[str]) -> None:
            visited.add(task)
            rec_stack.add(task)
            path.append(task)

            for neighbor in self._graph.get(task, set()):
                if neighbor not in visited:
                    dfs(neighbor, path.copy())
                elif neighbor in rec_stack:
                    idx = path.index(neighbor)
                    cycles.append(path[idx:])

            rec_stack.discard(task)

        for tid in task_ids:
            if tid not in visited:
                dfs(tid, [])

        return cycles

    def get_ready_tasks(
        self,
        task_ids: List[str],
        completed: Set[str]
    ) -> List[str]:
        """Get tasks ready for execution."""
        ready = []

        for tid in task_ids:
            deps = self._reverse_graph.get(tid, set())
            if deps.issubset(completed):
                ready.append(tid)

        return ready


# =============================================================================
# PLAN EXECUTOR
# =============================================================================

class PlanExecutor:
    """Execute plans."""

    def __init__(self):
        self._running_plans: Dict[str, Plan] = {}
        self._execution_history: List[ExecutionStep] = []

    async def execute_task(self, task: Task) -> Any:
        """Execute single task."""
        task.status = TaskStatus.RUNNING
        task.start_time = datetime.now()

        try:
            if task.action:
                if asyncio.iscoroutinefunction(task.action):
                    result = await task.action(**task.parameters)
                else:
                    result = task.action(**task.parameters)
            else:
                result = None

            task.result = result
            task.status = TaskStatus.COMPLETED
            task.end_time = datetime.now()
            task.actual_duration = (task.end_time - task.start_time).total_seconds()

            return result

        except Exception as e:
            task.error = str(e)
            task.retries += 1

            if task.retries < task.max_retries:
                task.status = TaskStatus.PENDING
            else:
                task.status = TaskStatus.FAILED
                task.end_time = datetime.now()

            raise

    async def execute_sequential(self, plan: Plan) -> Dict[str, Any]:
        """Execute plan sequentially."""
        plan.status = PlanStatus.EXECUTING
        plan.started_at = datetime.now()

        results = {}

        for task in plan.tasks:
            if task.status != TaskStatus.COMPLETED:
                try:
                    result = await self.execute_task(task)
                    results[task.task_id] = result

                    self._execution_history.append(ExecutionStep(
                        task_id=task.task_id,
                        action="execute",
                        result=result
                    ))

                except Exception as e:
                    self._execution_history.append(ExecutionStep(
                        task_id=task.task_id,
                        action="execute",
                        error=str(e)
                    ))

                    if task.status == TaskStatus.FAILED:
                        plan.status = PlanStatus.FAILED
                        return results

        plan.status = PlanStatus.COMPLETED
        plan.completed_at = datetime.now()

        return results

    async def execute_parallel(self, plan: Plan) -> Dict[str, Any]:
        """Execute plan in parallel."""
        plan.status = PlanStatus.EXECUTING
        plan.started_at = datetime.now()

        resolver = DependencyResolver()

        for dep in plan.dependencies:
            resolver.add_dependency(dep.from_task, dep.to_task)

        task_map = {t.task_id: t for t in plan.tasks}
        completed = set()
        results = {}

        while len(completed) < len(plan.tasks):
            ready = resolver.get_ready_tasks(
                [t.task_id for t in plan.tasks if t.task_id not in completed],
                completed
            )

            if not ready:
                break

            tasks = []
            for tid in ready:
                task = task_map[tid]
                if task.status != TaskStatus.COMPLETED:
                    tasks.append(self.execute_task(task))

            if tasks:
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                for i, tid in enumerate(ready):
                    if isinstance(batch_results[i], Exception):
                        task_map[tid].status = TaskStatus.FAILED
                    else:
                        results[tid] = batch_results[i]
                        completed.add(tid)

        all_completed = all(t.status == TaskStatus.COMPLETED for t in plan.tasks)

        plan.status = PlanStatus.COMPLETED if all_completed else PlanStatus.FAILED
        plan.completed_at = datetime.now()

        return results

    async def execute(self, plan: Plan) -> Dict[str, Any]:
        """Execute plan."""
        self._running_plans[plan.plan_id] = plan

        try:
            if plan.plan_type == PlanType.SEQUENTIAL:
                return await self.execute_sequential(plan)
            elif plan.plan_type == PlanType.PARALLEL:
                return await self.execute_parallel(plan)
            else:
                return await self.execute_sequential(plan)
        finally:
            if plan.plan_id in self._running_plans:
                del self._running_plans[plan.plan_id]

    def get_history(self) -> List[ExecutionStep]:
        """Get execution history."""
        return self._execution_history.copy()


# =============================================================================
# PLAN OPTIMIZER
# =============================================================================

class PlanOptimizer:
    """Optimize plans."""

    def optimize_order(self, plan: Plan) -> Plan:
        """Optimize task order."""
        if not plan.dependencies:
            return plan

        resolver = DependencyResolver()

        for dep in plan.dependencies:
            resolver.add_dependency(dep.from_task, dep.to_task)

        task_ids = [t.task_id for t in plan.tasks]

        try:
            sorted_ids = resolver.topological_sort(task_ids)
            task_map = {t.task_id: t for t in plan.tasks}
            plan.tasks = [task_map[tid] for tid in sorted_ids]
        except ValueError:
            pass

        return plan

    def parallelize(self, plan: Plan) -> Plan:
        """Convert to parallel where possible."""
        if not plan.dependencies:
            plan.plan_type = PlanType.PARALLEL
            return plan

        resolver = DependencyResolver()

        for dep in plan.dependencies:
            resolver.add_dependency(dep.from_task, dep.to_task)

        levels: List[List[str]] = []
        completed = set()
        remaining = set(t.task_id for t in plan.tasks)

        while remaining:
            ready = []

            for tid in remaining:
                deps = resolver.get_dependencies(tid)
                if deps.issubset(completed):
                    ready.append(tid)

            if not ready:
                break

            levels.append(ready)

            for tid in ready:
                completed.add(tid)
                remaining.discard(tid)

        plan.plan_type = PlanType.PARALLEL
        plan.metadata["parallelization_levels"] = levels

        return plan

    def estimate_duration(self, plan: Plan) -> float:
        """Estimate plan duration."""
        if plan.plan_type == PlanType.SEQUENTIAL:
            return sum(t.estimated_duration for t in plan.tasks)

        levels = plan.metadata.get("parallelization_levels", [])

        if not levels:
            return sum(t.estimated_duration for t in plan.tasks)

        task_map = {t.task_id: t for t in plan.tasks}
        total = 0.0

        for level in levels:
            level_max = max(
                task_map[tid].estimated_duration
                for tid in level
                if tid in task_map
            )
            total += level_max

        return total


# =============================================================================
# PLAN MONITOR
# =============================================================================

class PlanMonitor:
    """Monitor plan execution."""

    def __init__(self):
        self._plans: Dict[str, Plan] = {}
        self._alerts: List[Dict[str, Any]] = []

    def register_plan(self, plan: Plan) -> None:
        """Register plan for monitoring."""
        self._plans[plan.plan_id] = plan

    def get_progress(self, plan_id: str) -> Dict[str, Any]:
        """Get plan progress."""
        plan = self._plans.get(plan_id)

        if not plan:
            return {}

        total = len(plan.tasks)
        completed = sum(1 for t in plan.tasks if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in plan.tasks if t.status == TaskStatus.FAILED)
        running = sum(1 for t in plan.tasks if t.status == TaskStatus.RUNNING)

        return {
            "plan_id": plan_id,
            "status": plan.status.value,
            "total_tasks": total,
            "completed": completed,
            "failed": failed,
            "running": running,
            "progress_percent": (completed / total * 100) if total > 0 else 0
        }

    def check_deadlines(self, plan_id: str) -> List[Task]:
        """Check for tasks past deadline."""
        plan = self._plans.get(plan_id)

        if not plan:
            return []

        overdue = []
        now = datetime.now()

        for task in plan.tasks:
            if task.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
                if task.start_time:
                    expected_end = task.start_time + timedelta(seconds=task.estimated_duration * 2)
                    if now > expected_end:
                        overdue.append(task)

        return overdue

    def get_stats(self, plan_id: str) -> PlanStats:
        """Get plan statistics."""
        plan = self._plans.get(plan_id)

        if not plan:
            return PlanStats()

        completed = [t for t in plan.tasks if t.status == TaskStatus.COMPLETED]
        durations = [t.actual_duration for t in completed if t.actual_duration > 0]

        return PlanStats(
            total_tasks=len(plan.tasks),
            completed_tasks=len(completed),
            failed_tasks=sum(1 for t in plan.tasks if t.status == TaskStatus.FAILED),
            pending_tasks=sum(1 for t in plan.tasks if t.status == TaskStatus.PENDING),
            total_duration=sum(durations),
            avg_task_duration=sum(durations) / len(durations) if durations else 0.0
        )


# =============================================================================
# HIERARCHICAL TASK NETWORK
# =============================================================================

@dataclass
class HTNMethod:
    """HTN method for decomposing tasks."""
    method_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    task_name: str = ""
    preconditions: List[str] = field(default_factory=list)
    subtasks: List[str] = field(default_factory=list)


class HTNPlanner:
    """Hierarchical Task Network planner."""

    def __init__(self):
        self._methods: Dict[str, List[HTNMethod]] = defaultdict(list)
        self._primitive_tasks: Set[str] = set()

    def add_method(
        self,
        task_name: str,
        subtasks: List[str],
        preconditions: Optional[List[str]] = None
    ) -> str:
        """Add decomposition method."""
        method = HTNMethod(
            task_name=task_name,
            subtasks=subtasks,
            preconditions=preconditions or []
        )

        self._methods[task_name].append(method)
        return method.method_id

    def set_primitive(self, task_name: str) -> None:
        """Mark task as primitive."""
        self._primitive_tasks.add(task_name)

    def decompose(
        self,
        task_name: str,
        state: Dict[str, Any]
    ) -> List[str]:
        """Decompose task into subtasks."""
        if task_name in self._primitive_tasks:
            return [task_name]

        methods = self._methods.get(task_name, [])

        for method in methods:
            if self._check_preconditions(method.preconditions, state):
                result = []
                for subtask in method.subtasks:
                    result.extend(self.decompose(subtask, state))
                return result

        return [task_name]

    def _check_preconditions(
        self,
        preconditions: List[str],
        state: Dict[str, Any]
    ) -> bool:
        """Check if preconditions are met."""
        for cond in preconditions:
            if cond.startswith("!"):
                if state.get(cond[1:], False):
                    return False
            else:
                if not state.get(cond, False):
                    return False
        return True

    def plan(
        self,
        goals: List[str],
        state: Dict[str, Any]
    ) -> List[str]:
        """Create plan for goals."""
        plan = []

        for goal in goals:
            tasks = self.decompose(goal, state)
            plan.extend(tasks)

        return plan


# =============================================================================
# PLANNING ENGINE
# =============================================================================

class PlanningEngine:
    """
    Planning Engine for BAEL.

    Advanced planning and goal decomposition.
    """

    def __init__(self):
        self._goal_manager = GoalManager()
        self._executor = PlanExecutor()
        self._optimizer = PlanOptimizer()
        self._monitor = PlanMonitor()
        self._htn_planner = HTNPlanner()
        self._plans: Dict[str, Plan] = {}

    # -------------------------------------------------------------------------
    # GOALS
    # -------------------------------------------------------------------------

    def create_goal(
        self,
        name: str,
        description: str = "",
        priority: str = "medium",
        deadline: Optional[datetime] = None
    ) -> Goal:
        """Create goal."""
        priority_map = {
            "critical": GoalPriority.CRITICAL,
            "high": GoalPriority.HIGH,
            "medium": GoalPriority.MEDIUM,
            "low": GoalPriority.LOW,
            "optional": GoalPriority.OPTIONAL
        }

        return self._goal_manager.create_goal(
            name=name,
            description=description,
            priority=priority_map.get(priority.lower(), GoalPriority.MEDIUM),
            deadline=deadline
        )

    def decompose_goal(
        self,
        parent_goal: Goal,
        subgoal_names: List[str]
    ) -> List[Goal]:
        """Decompose goal into subgoals."""
        subgoals = []

        for name in subgoal_names:
            subgoal = self._goal_manager.create_goal(
                name=name,
                priority=parent_goal.priority
            )
            self._goal_manager.add_subgoal(parent_goal.goal_id, subgoal.goal_id)
            subgoals.append(subgoal)

        return subgoals

    def activate_goal(self, goal_id: str) -> bool:
        """Activate goal."""
        return self._goal_manager.activate_goal(goal_id)

    def get_active_goals(self) -> List[Goal]:
        """Get active goals by priority."""
        return self._goal_manager.prioritize_goals()

    # -------------------------------------------------------------------------
    # PLANNING
    # -------------------------------------------------------------------------

    def create_plan(
        self,
        name: str,
        goal_id: Optional[str] = None,
        plan_type: str = "sequential"
    ) -> PlanBuilder:
        """Create plan builder."""
        builder = PlanBuilder(name)

        if goal_id:
            builder.goal(goal_id)

        type_map = {
            "sequential": PlanType.SEQUENTIAL,
            "parallel": PlanType.PARALLEL,
            "hierarchical": PlanType.HIERARCHICAL
        }

        builder.plan_type(type_map.get(plan_type, PlanType.SEQUENTIAL))

        return builder

    def create_task(self) -> TaskBuilder:
        """Create task builder."""
        return TaskBuilder()

    def register_plan(self, plan: Plan) -> str:
        """Register plan."""
        self._plans[plan.plan_id] = plan
        self._monitor.register_plan(plan)
        return plan.plan_id

    def get_plan(self, plan_id: str) -> Optional[Plan]:
        """Get plan."""
        return self._plans.get(plan_id)

    # -------------------------------------------------------------------------
    # OPTIMIZATION
    # -------------------------------------------------------------------------

    def optimize_plan(self, plan: Plan) -> Plan:
        """Optimize plan."""
        plan = self._optimizer.optimize_order(plan)
        plan = self._optimizer.parallelize(plan)
        return plan

    def estimate_duration(self, plan: Plan) -> float:
        """Estimate plan duration."""
        return self._optimizer.estimate_duration(plan)

    # -------------------------------------------------------------------------
    # EXECUTION
    # -------------------------------------------------------------------------

    async def execute_plan(self, plan_id: str) -> Dict[str, Any]:
        """Execute plan."""
        plan = self._plans.get(plan_id)

        if not plan:
            raise ValueError(f"Plan not found: {plan_id}")

        plan.status = PlanStatus.READY
        return await self._executor.execute(plan)

    def get_progress(self, plan_id: str) -> Dict[str, Any]:
        """Get plan progress."""
        return self._monitor.get_progress(plan_id)

    def get_stats(self, plan_id: str) -> PlanStats:
        """Get plan statistics."""
        return self._monitor.get_stats(plan_id)

    # -------------------------------------------------------------------------
    # HTN
    # -------------------------------------------------------------------------

    def add_decomposition(
        self,
        task_name: str,
        subtasks: List[str],
        preconditions: Optional[List[str]] = None
    ) -> str:
        """Add task decomposition method."""
        return self._htn_planner.add_method(task_name, subtasks, preconditions)

    def set_primitive_task(self, task_name: str) -> None:
        """Mark task as primitive."""
        self._htn_planner.set_primitive(task_name)

    def htn_plan(
        self,
        goals: List[str],
        state: Dict[str, Any]
    ) -> List[str]:
        """Create HTN plan."""
        return self._htn_planner.plan(goals, state)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Planning Engine."""
    print("=" * 70)
    print("BAEL - PLANNING ENGINE DEMO")
    print("Advanced Planning and Goal Decomposition")
    print("=" * 70)
    print()

    engine = PlanningEngine()

    # 1. Goals
    print("1. GOAL MANAGEMENT:")
    print("-" * 40)

    main_goal = engine.create_goal(
        name="Deploy Application",
        description="Deploy the application to production",
        priority="high",
        deadline=datetime.now() + timedelta(hours=2)
    )

    print(f"   Created goal: {main_goal.name}")
    print(f"   Priority: {main_goal.priority.name}")
    print()

    # 2. Goal Decomposition
    print("2. GOAL DECOMPOSITION:")
    print("-" * 40)

    subgoals = engine.decompose_goal(main_goal, [
        "Build Application",
        "Run Tests",
        "Deploy to Staging",
        "Deploy to Production"
    ])

    for sg in subgoals:
        print(f"   - {sg.name}")
    print()

    # 3. Activate Goals
    print("3. ACTIVE GOALS:")
    print("-" * 40)

    engine.activate_goal(main_goal.goal_id)
    for sg in subgoals:
        engine.activate_goal(sg.goal_id)

    active = engine.get_active_goals()
    print(f"   Active goals: {len(active)}")
    print()

    # 4. Create Plan
    print("4. CREATE PLAN:")
    print("-" * 40)

    # Create tasks
    task1 = (engine.create_task()
        .name("Compile Code")
        .estimated_duration(30.0)
        .action(lambda: {"status": "compiled"})
        .build())

    task2 = (engine.create_task()
        .name("Run Unit Tests")
        .estimated_duration(60.0)
        .depends_on(task1.task_id)
        .action(lambda: {"tests": 50, "passed": 50})
        .build())

    task3 = (engine.create_task()
        .name("Run Integration Tests")
        .estimated_duration(120.0)
        .depends_on(task1.task_id)
        .action(lambda: {"tests": 20, "passed": 20})
        .build())

    task4 = (engine.create_task()
        .name("Deploy")
        .estimated_duration(45.0)
        .depends_on(task2.task_id)
        .depends_on(task3.task_id)
        .action(lambda: {"deployed": True})
        .build())

    # Build plan
    plan = (engine.create_plan("Deployment Plan", main_goal.goal_id, "parallel")
        .add_task(task1)
        .add_task(task2)
        .add_task(task3)
        .add_task(task4)
        .add_dependency(task1.task_id, task2.task_id)
        .add_dependency(task1.task_id, task3.task_id)
        .add_dependency(task2.task_id, task4.task_id)
        .add_dependency(task3.task_id, task4.task_id)
        .build())

    engine.register_plan(plan)

    print(f"   Plan: {plan.name}")
    print(f"   Tasks: {len(plan.tasks)}")
    print(f"   Dependencies: {len(plan.dependencies)}")
    print()

    # 5. Optimize Plan
    print("5. OPTIMIZE PLAN:")
    print("-" * 40)

    original_duration = engine.estimate_duration(plan)

    optimized_plan = engine.optimize_plan(plan)

    optimized_duration = engine.estimate_duration(optimized_plan)

    print(f"   Original duration: {original_duration}s")
    print(f"   Optimized duration: {optimized_duration}s")

    levels = optimized_plan.metadata.get("parallelization_levels", [])
    print(f"   Parallelization levels: {len(levels)}")
    print()

    # 6. Execute Plan
    print("6. EXECUTE PLAN:")
    print("-" * 40)

    results = await engine.execute_plan(plan.plan_id)

    for task_id, result in results.items():
        task = next((t for t in plan.tasks if t.task_id == task_id), None)
        if task:
            print(f"   {task.name}: {result}")
    print()

    # 7. Plan Progress
    print("7. PLAN PROGRESS:")
    print("-" * 40)

    progress = engine.get_progress(plan.plan_id)

    print(f"   Status: {progress.get('status')}")
    print(f"   Completed: {progress.get('completed')}/{progress.get('total_tasks')}")
    print(f"   Progress: {progress.get('progress_percent'):.1f}%")
    print()

    # 8. Plan Statistics
    print("8. PLAN STATISTICS:")
    print("-" * 40)

    stats = engine.get_stats(plan.plan_id)

    print(f"   Total tasks: {stats.total_tasks}")
    print(f"   Completed: {stats.completed_tasks}")
    print(f"   Failed: {stats.failed_tasks}")
    print(f"   Total duration: {stats.total_duration:.2f}s")
    print()

    # 9. HTN Planning
    print("9. HIERARCHICAL TASK NETWORK:")
    print("-" * 40)

    # Define decomposition methods
    engine.add_decomposition("travel", ["get_transport", "go_to_destination"])
    engine.add_decomposition(
        "get_transport",
        ["call_taxi"],
        preconditions=["has_phone"]
    )
    engine.add_decomposition(
        "get_transport",
        ["walk_to_bus"],
        preconditions=["!has_phone"]
    )

    # Mark primitives
    engine.set_primitive_task("call_taxi")
    engine.set_primitive_task("walk_to_bus")
    engine.set_primitive_task("go_to_destination")

    # Plan with state
    state = {"has_phone": True}
    htn_plan = engine.htn_plan(["travel"], state)

    print(f"   State: {state}")
    print(f"   Plan: {htn_plan}")
    print()

    # 10. HTN with different state
    print("10. HTN ALTERNATIVE STATE:")
    print("-" * 40)

    state = {"has_phone": False}
    htn_plan = engine.htn_plan(["travel"], state)

    print(f"   State: {state}")
    print(f"   Plan: {htn_plan}")
    print()

    # 11. Simple Sequential Plan
    print("11. SIMPLE SEQUENTIAL PLAN:")
    print("-" * 40)

    simple_plan = (engine.create_plan("Simple Plan", plan_type="sequential")
        .add_task(engine.create_task()
            .name("Step 1")
            .action(lambda: "done1")
            .build())
        .add_task(engine.create_task()
            .name("Step 2")
            .action(lambda: "done2")
            .build())
        .add_task(engine.create_task()
            .name("Step 3")
            .action(lambda: "done3")
            .build())
        .build())

    engine.register_plan(simple_plan)
    results = await engine.execute_plan(simple_plan.plan_id)

    print(f"   Executed: {len(results)} tasks")
    print(f"   Status: {simple_plan.status.value}")
    print()

    # 12. Task with Retry
    print("12. TASK WITH RETRY:")
    print("-" * 40)

    attempt_count = {"count": 0}

    def flaky_task():
        attempt_count["count"] += 1
        if attempt_count["count"] < 3:
            raise Exception("Temporary failure")
        return "success"

    retry_task = (engine.create_task()
        .name("Flaky Task")
        .max_retries(5)
        .action(flaky_task)
        .build())

    retry_plan = (engine.create_plan("Retry Plan")
        .add_task(retry_task)
        .build())

    engine.register_plan(retry_plan)

    try:
        results = await engine.execute_plan(retry_plan.plan_id)
        print(f"   Result: {results}")
        print(f"   Attempts: {retry_task.retries + 1}")
    except Exception as e:
        print(f"   Failed: {e}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Planning Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
