"""
BAEL - Task Decomposer
Intelligent task breakdown and planning.

Features:
- Automatic task decomposition
- Dependency analysis
- Parallel task identification
- Time estimation
- Priority assignment
"""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.TaskDecomposer")


# =============================================================================
# TYPES & ENUMS
# =============================================================================

class TaskType(Enum):
    """Types of tasks."""
    ANALYSIS = "analysis"
    RESEARCH = "research"
    DESIGN = "design"
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    REVIEW = "review"
    DOCUMENTATION = "documentation"
    DEPLOYMENT = "deployment"


class TaskPriority(Enum):
    """Task priorities."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    OPTIONAL = 5


class TaskStatus(Enum):
    """Task status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Task:
    """A decomposed task."""
    id: str
    title: str
    description: str
    type: TaskType
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING

    # Dependencies
    depends_on: List[str] = field(default_factory=list)
    blocks: List[str] = field(default_factory=list)

    # Execution
    estimated_minutes: int = 30
    actual_minutes: Optional[int] = None

    # Assignment
    persona_id: Optional[str] = None
    tools_required: List[str] = field(default_factory=list)

    # Tracking
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Results
    output: Optional[str] = None
    artifacts: List[str] = field(default_factory=list)

    # Subtasks
    subtasks: List['Task'] = field(default_factory=list)
    parent_id: Optional[str] = None


@dataclass
class TaskPlan:
    """A complete task plan."""
    id: str
    title: str
    objective: str
    tasks: List[Task]

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    estimated_total_minutes: int = 0

    # Execution order
    execution_order: List[List[str]] = field(default_factory=list)  # Parallel groups

    # Status
    status: TaskStatus = TaskStatus.PENDING
    progress_percent: float = 0.0


# =============================================================================
# TASK DECOMPOSER
# =============================================================================

class TaskDecomposer:
    """Decomposes complex tasks into manageable subtasks."""

    def __init__(self, model_router=None):
        self.model_router = model_router
        self._task_counter = 0

        # Task type detection patterns
        self.type_patterns = {
            TaskType.ANALYSIS: ["analyze", "understand", "evaluate", "assess", "review"],
            TaskType.RESEARCH: ["research", "find", "search", "learn", "investigate"],
            TaskType.DESIGN: ["design", "architect", "plan", "structure", "model"],
            TaskType.IMPLEMENTATION: ["implement", "build", "create", "develop", "code", "write"],
            TaskType.TESTING: ["test", "verify", "validate", "check", "ensure"],
            TaskType.REVIEW: ["review", "audit", "inspect", "examine"],
            TaskType.DOCUMENTATION: ["document", "explain", "describe", "readme"],
            TaskType.DEPLOYMENT: ["deploy", "release", "publish", "launch"]
        }

    async def decompose(self, objective: str, depth: int = 2) -> TaskPlan:
        """Decompose an objective into a task plan."""
        plan_id = f"plan_{self._task_counter}"
        self._task_counter += 1

        logger.info(f"Decomposing: {objective}")

        # Generate tasks
        if self.model_router:
            tasks = await self._ai_decompose(objective, depth)
        else:
            tasks = self._heuristic_decompose(objective)

        # Analyze dependencies
        self._analyze_dependencies(tasks)

        # Create execution order
        execution_order = self._create_execution_order(tasks)

        # Calculate estimates
        total_minutes = sum(t.estimated_minutes for t in tasks)

        plan = TaskPlan(
            id=plan_id,
            title=f"Plan: {objective[:50]}",
            objective=objective,
            tasks=tasks,
            estimated_total_minutes=total_minutes,
            execution_order=execution_order
        )

        logger.info(f"Created plan with {len(tasks)} tasks, estimated {total_minutes} minutes")

        return plan

    async def _ai_decompose(self, objective: str, depth: int) -> List[Task]:
        """Use AI to decompose task."""
        decompose_prompt = f"""Decompose this objective into specific, actionable tasks:

Objective: {objective}

For each task provide:
1. Title (short, action-oriented)
2. Description (what needs to be done)
3. Type (analysis/research/design/implementation/testing/review/documentation/deployment)
4. Priority (critical/high/medium/low)
5. Estimated minutes
6. Dependencies (which tasks must complete first)

Format each task as:
TASK: [title]
DESC: [description]
TYPE: [type]
PRIORITY: [priority]
TIME: [minutes]
DEPENDS: [comma-separated task titles or "none"]

Provide {depth * 3}-{depth * 5} tasks covering the full scope."""

        try:
            response = await self.model_router.generate(
                decompose_prompt,
                model_type='reasoning'
            )

            return self._parse_tasks(response)

        except Exception as e:
            logger.error(f"AI decomposition failed: {e}")
            return self._heuristic_decompose(objective)

    def _parse_tasks(self, response: str) -> List[Task]:
        """Parse tasks from AI response."""
        tasks = []
        current_task = {}

        for line in response.split('\n'):
            line = line.strip()

            if line.startswith('TASK:'):
                if current_task:
                    tasks.append(self._create_task(current_task))
                current_task = {'title': line[5:].strip()}

            elif line.startswith('DESC:'):
                current_task['description'] = line[5:].strip()

            elif line.startswith('TYPE:'):
                current_task['type'] = line[5:].strip().lower()

            elif line.startswith('PRIORITY:'):
                current_task['priority'] = line[9:].strip().lower()

            elif line.startswith('TIME:'):
                try:
                    current_task['time'] = int(line[5:].strip().split()[0])
                except:
                    current_task['time'] = 30

            elif line.startswith('DEPENDS:'):
                deps = line[8:].strip()
                current_task['depends'] = [] if deps.lower() == 'none' else [d.strip() for d in deps.split(',')]

        if current_task:
            tasks.append(self._create_task(current_task))

        return tasks

    def _create_task(self, data: Dict[str, Any]) -> Task:
        """Create task from parsed data."""
        task_id = f"task_{self._task_counter}"
        self._task_counter += 1

        # Map type
        type_mapping = {
            'analysis': TaskType.ANALYSIS,
            'research': TaskType.RESEARCH,
            'design': TaskType.DESIGN,
            'implementation': TaskType.IMPLEMENTATION,
            'testing': TaskType.TESTING,
            'review': TaskType.REVIEW,
            'documentation': TaskType.DOCUMENTATION,
            'deployment': TaskType.DEPLOYMENT
        }
        task_type = type_mapping.get(data.get('type', ''), TaskType.IMPLEMENTATION)

        # Map priority
        priority_mapping = {
            'critical': TaskPriority.CRITICAL,
            'high': TaskPriority.HIGH,
            'medium': TaskPriority.MEDIUM,
            'low': TaskPriority.LOW,
            'optional': TaskPriority.OPTIONAL
        }
        priority = priority_mapping.get(data.get('priority', ''), TaskPriority.MEDIUM)

        return Task(
            id=task_id,
            title=data.get('title', 'Untitled Task'),
            description=data.get('description', ''),
            type=task_type,
            priority=priority,
            estimated_minutes=data.get('time', 30),
            depends_on=data.get('depends', [])
        )

    def _heuristic_decompose(self, objective: str) -> List[Task]:
        """Decompose using heuristics when AI unavailable."""
        tasks = []
        objective_lower = objective.lower()

        # Standard development phases
        phases = [
            ("Analyze requirements", TaskType.ANALYSIS, 20),
            ("Research best practices", TaskType.RESEARCH, 30),
            ("Design solution", TaskType.DESIGN, 45),
            ("Implement core functionality", TaskType.IMPLEMENTATION, 90),
            ("Write tests", TaskType.TESTING, 45),
            ("Review and refactor", TaskType.REVIEW, 30),
            ("Write documentation", TaskType.DOCUMENTATION, 30)
        ]

        for i, (title, task_type, time) in enumerate(phases):
            task = Task(
                id=f"task_{self._task_counter}",
                title=title,
                description=f"{title} for: {objective}",
                type=task_type,
                estimated_minutes=time,
                depends_on=[f"task_{self._task_counter - 1}"] if i > 0 else []
            )
            self._task_counter += 1
            tasks.append(task)

        return tasks

    def _analyze_dependencies(self, tasks: List[Task]) -> None:
        """Analyze and set up task dependencies."""
        # Create title to task mapping
        title_map = {t.title: t for t in tasks}

        for task in tasks:
            # Convert title dependencies to IDs
            resolved_deps = []
            for dep in task.depends_on:
                if dep in title_map:
                    resolved_deps.append(title_map[dep].id)
            task.depends_on = resolved_deps

            # Set up blocks relationship
            for dep_id in task.depends_on:
                for t in tasks:
                    if t.id == dep_id:
                        if task.id not in t.blocks:
                            t.blocks.append(task.id)

        # Detect type-based dependencies
        type_order = [
            TaskType.ANALYSIS,
            TaskType.RESEARCH,
            TaskType.DESIGN,
            TaskType.IMPLEMENTATION,
            TaskType.TESTING,
            TaskType.REVIEW,
            TaskType.DOCUMENTATION,
            TaskType.DEPLOYMENT
        ]

        # Group by type
        by_type = defaultdict(list)
        for task in tasks:
            by_type[task.type].append(task)

        # Add implicit dependencies
        for i, task_type in enumerate(type_order[1:], 1):
            prev_type = type_order[i - 1]
            for task in by_type[task_type]:
                for prev_task in by_type[prev_type]:
                    if prev_task.id not in task.depends_on:
                        # Only add if no explicit dependency exists
                        pass  # Keep explicit dependencies only

    def _create_execution_order(self, tasks: List[Task]) -> List[List[str]]:
        """Create parallel execution groups."""
        if not tasks:
            return []

        # Build dependency graph
        remaining = set(t.id for t in tasks)
        completed = set()
        order = []

        task_map = {t.id: t for t in tasks}

        while remaining:
            # Find tasks with all dependencies satisfied
            ready = []
            for task_id in remaining:
                task = task_map[task_id]
                if all(dep in completed for dep in task.depends_on):
                    ready.append(task_id)

            if not ready:
                # Circular dependency or error - add remaining
                logger.warning(f"Possible circular dependency, adding remaining tasks")
                ready = list(remaining)

            order.append(ready)
            for task_id in ready:
                remaining.remove(task_id)
                completed.add(task_id)

        return order

    def detect_task_type(self, text: str) -> TaskType:
        """Detect task type from text."""
        text_lower = text.lower()

        for task_type, patterns in self.type_patterns.items():
            for pattern in patterns:
                if pattern in text_lower:
                    return task_type

        return TaskType.IMPLEMENTATION


# =============================================================================
# TASK EXECUTOR
# =============================================================================

class TaskExecutor:
    """Executes task plans."""

    def __init__(self, brain=None):
        self.brain = brain
        self.current_plan: Optional[TaskPlan] = None
        self.current_task: Optional[Task] = None

    async def execute_plan(self, plan: TaskPlan) -> Dict[str, Any]:
        """Execute a task plan."""
        self.current_plan = plan
        plan.status = TaskStatus.IN_PROGRESS

        results = []

        for parallel_group in plan.execution_order:
            # Execute tasks in parallel group
            group_tasks = [self._execute_task(plan, task_id) for task_id in parallel_group]
            group_results = await asyncio.gather(*group_tasks, return_exceptions=True)

            for task_id, result in zip(parallel_group, group_results):
                if isinstance(result, Exception):
                    results.append({
                        "task_id": task_id,
                        "status": "error",
                        "error": str(result)
                    })
                else:
                    results.append(result)

            # Update progress
            completed = sum(1 for t in plan.tasks if t.status == TaskStatus.COMPLETED)
            plan.progress_percent = (completed / len(plan.tasks)) * 100

        # Final status
        all_completed = all(t.status == TaskStatus.COMPLETED for t in plan.tasks)
        plan.status = TaskStatus.COMPLETED if all_completed else TaskStatus.FAILED

        return {
            "plan_id": plan.id,
            "status": plan.status.value,
            "progress": plan.progress_percent,
            "results": results
        }

    async def _execute_task(self, plan: TaskPlan, task_id: str) -> Dict[str, Any]:
        """Execute a single task."""
        # Find task
        task = next((t for t in plan.tasks if t.id == task_id), None)
        if not task:
            return {"task_id": task_id, "status": "not_found"}

        self.current_task = task
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.now()

        try:
            # Execute based on brain availability
            if self.brain:
                result = await self._execute_with_brain(task)
            else:
                result = await self._simulate_execution(task)

            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.actual_minutes = int((task.completed_at - task.started_at).total_seconds() / 60)
            task.output = result.get("output", "")

            return {
                "task_id": task_id,
                "status": "completed",
                "output": result
            }

        except Exception as e:
            task.status = TaskStatus.FAILED
            logger.error(f"Task {task_id} failed: {e}")
            return {
                "task_id": task_id,
                "status": "failed",
                "error": str(e)
            }

    async def _execute_with_brain(self, task: Task) -> Dict[str, Any]:
        """Execute task using brain."""
        prompt = f"""Execute this task:

Title: {task.title}
Description: {task.description}
Type: {task.type.value}

Provide a complete, actionable result."""

        result = await self.brain.think(prompt)

        return {
            "output": result.get("response", ""),
            "artifacts": []
        }

    async def _simulate_execution(self, task: Task) -> Dict[str, Any]:
        """Simulate task execution."""
        await asyncio.sleep(0.1)  # Simulate work

        return {
            "output": f"Simulated completion of: {task.title}",
            "artifacts": []
        }


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Test task decomposer."""
    decomposer = TaskDecomposer()

    objective = "Build a REST API with user authentication, CRUD operations for posts, and comprehensive testing"

    plan = await decomposer.decompose(objective)

    print(f"\n📋 Task Plan: {plan.title}")
    print(f"   Objective: {plan.objective}")
    print(f"   Total estimated: {plan.estimated_total_minutes} minutes")
    print(f"\n📝 Tasks ({len(plan.tasks)}):")

    for task in plan.tasks:
        deps = ", ".join(task.depends_on) if task.depends_on else "none"
        print(f"   [{task.id}] {task.title}")
        print(f"       Type: {task.type.value} | Priority: {task.priority.name} | Est: {task.estimated_minutes}min")
        print(f"       Depends on: {deps}")

    print(f"\n🔄 Execution Order:")
    for i, group in enumerate(plan.execution_order):
        print(f"   Phase {i + 1}: {', '.join(group)}")

    # Execute
    executor = TaskExecutor()
    result = await executor.execute_plan(plan)

    print(f"\n✅ Execution Result:")
    print(f"   Status: {result['status']}")
    print(f"   Progress: {result['progress']:.1f}%")


if __name__ == "__main__":
    asyncio.run(main())
