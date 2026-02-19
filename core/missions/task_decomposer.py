"""
BAEL Task Decomposer
=====================

Decompose complex tasks into manageable subtasks.
Uses AI to intelligently break down work.

Features:
- Hierarchical task decomposition
- Dependency detection
- Parallel execution identification
- Resource estimation
- Priority assignment
"""

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class DecompositionStrategy(Enum):
    """Task decomposition strategies."""
    SEQUENTIAL = "sequential"      # One after another
    PARALLEL = "parallel"          # All at once
    HIERARCHICAL = "hierarchical"  # Tree structure
    ITERATIVE = "iterative"        # Repeat until done
    HYBRID = "hybrid"              # Mix of strategies


class TaskComplexity(Enum):
    """Task complexity levels."""
    TRIVIAL = 1     # < 5 minutes
    SIMPLE = 2      # 5-30 minutes
    MODERATE = 3    # 30 min - 2 hours
    COMPLEX = 4     # 2-8 hours
    VERY_COMPLEX = 5  # > 8 hours


class TaskType(Enum):
    """Types of decomposed tasks."""
    ACTION = "action"          # Execute something
    DECISION = "decision"      # Make a choice
    VALIDATION = "validation"  # Check something
    TRANSFORMATION = "transformation"  # Convert data
    COMMUNICATION = "communication"    # Send/receive
    COORDINATION = "coordination"      # Sync tasks


@dataclass
class TaskDependency:
    """Dependency between tasks."""
    from_task_id: str
    to_task_id: str

    # Dependency type
    type: str = "finish_to_start"  # finish_to_start, start_to_start, finish_to_finish

    # Data dependency
    data_key: Optional[str] = None  # Output key from from_task needed by to_task

    def __hash__(self):
        return hash((self.from_task_id, self.to_task_id, self.type))


@dataclass
class ResourceEstimate:
    """Resource estimates for task."""
    cpu_seconds: float = 0.0
    memory_mb: float = 0.0
    api_calls: int = 0
    tokens: int = 0
    network_mb: float = 0.0
    cost_estimate: float = 0.0


@dataclass
class DecomposedTask:
    """A decomposed task unit."""
    id: str
    name: str
    description: str = ""

    # Classification
    type: TaskType = TaskType.ACTION
    complexity: TaskComplexity = TaskComplexity.SIMPLE

    # Hierarchy
    parent_id: Optional[str] = None
    subtask_ids: List[str] = field(default_factory=list)
    depth: int = 0

    # Dependencies
    depends_on: List[str] = field(default_factory=list)

    # Execution
    can_parallel: bool = False
    estimated_duration: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    priority: int = 0  # Higher = more important

    # Resources
    resources: ResourceEstimate = field(default_factory=ResourceEstimate)

    # Instructions
    instructions: List[str] = field(default_factory=list)
    expected_output: Optional[str] = None

    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_leaf(self) -> bool:
        return len(self.subtask_ids) == 0

    @property
    def is_root(self) -> bool:
        return self.parent_id is None


class TaskDecomposer:
    """
    Intelligent task decomposition for BAEL.
    """

    def __init__(
        self,
        llm_client: Optional[Any] = None,
    ):
        self.llm_client = llm_client

        # Task storage
        self.tasks: Dict[str, DecomposedTask] = {}
        self.dependencies: Set[TaskDependency] = set()

        # Decomposition patterns
        self._patterns: Dict[str, Callable] = {}
        self._register_patterns()

        # Stats
        self.stats = {
            "tasks_decomposed": 0,
            "total_subtasks": 0,
            "avg_depth": 0.0,
        }

    def _register_patterns(self) -> None:
        """Register task decomposition patterns."""
        self._patterns["research"] = self._decompose_research
        self._patterns["development"] = self._decompose_development
        self._patterns["analysis"] = self._decompose_analysis
        self._patterns["automation"] = self._decompose_automation

    def _generate_id(self, name: str, parent_id: Optional[str] = None) -> str:
        """Generate task ID."""
        prefix = f"{parent_id}_" if parent_id else ""
        hash_input = f"{prefix}{name}:{time.time()}"
        return f"task_{hashlib.sha256(hash_input.encode()).hexdigest()[:8]}"

    async def decompose(
        self,
        task_description: str,
        strategy: DecompositionStrategy = DecompositionStrategy.HIERARCHICAL,
        max_depth: int = 3,
        pattern: Optional[str] = None,
    ) -> DecomposedTask:
        """
        Decompose a task into subtasks.

        Args:
            task_description: Natural language task description
            strategy: Decomposition strategy
            max_depth: Maximum decomposition depth
            pattern: Specific decomposition pattern

        Returns:
            Root DecomposedTask with subtasks
        """
        self.stats["tasks_decomposed"] += 1

        # Create root task
        root = DecomposedTask(
            id=self._generate_id(task_description[:20]),
            name=task_description[:50],
            description=task_description,
            type=self._infer_task_type(task_description),
            complexity=self._estimate_complexity(task_description),
        )

        self.tasks[root.id] = root

        # Apply pattern if specified
        if pattern and pattern in self._patterns:
            await self._patterns[pattern](root, max_depth)
        elif self.llm_client:
            await self._decompose_with_llm(root, strategy, max_depth)
        else:
            await self._decompose_heuristic(root, strategy, max_depth)

        # Build dependency graph
        self._build_dependencies(root)

        # Calculate statistics
        self._update_stats()

        return root

    async def _decompose_with_llm(
        self,
        task: DecomposedTask,
        strategy: DecompositionStrategy,
        max_depth: int,
        depth: int = 0,
    ) -> None:
        """Decompose using LLM."""
        if depth >= max_depth:
            return

        # Would use LLM to generate subtasks
        # For now, use heuristic
        await self._decompose_heuristic(task, strategy, max_depth, depth)

    async def _decompose_heuristic(
        self,
        task: DecomposedTask,
        strategy: DecompositionStrategy,
        max_depth: int,
        depth: int = 0,
    ) -> None:
        """Heuristic-based decomposition."""
        if depth >= max_depth:
            return

        if task.complexity.value <= TaskComplexity.SIMPLE.value:
            return

        # Generate subtasks based on task description
        subtasks = self._generate_subtasks(task, strategy)

        for subtask in subtasks:
            subtask.parent_id = task.id
            subtask.depth = depth + 1
            task.subtask_ids.append(subtask.id)
            self.tasks[subtask.id] = subtask
            self.stats["total_subtasks"] += 1

            # Recursively decompose
            await self._decompose_heuristic(subtask, strategy, max_depth, depth + 1)

    def _generate_subtasks(
        self,
        task: DecomposedTask,
        strategy: DecompositionStrategy,
    ) -> List[DecomposedTask]:
        """Generate subtasks for a task."""
        subtasks = []
        desc_lower = task.description.lower()

        # Common patterns
        if "research" in desc_lower or "find" in desc_lower:
            subtasks.extend([
                DecomposedTask(
                    id=self._generate_id("search", task.id),
                    name="Search for information",
                    type=TaskType.ACTION,
                    complexity=TaskComplexity.SIMPLE,
                    can_parallel=True,
                ),
                DecomposedTask(
                    id=self._generate_id("filter", task.id),
                    name="Filter and validate results",
                    type=TaskType.VALIDATION,
                    complexity=TaskComplexity.SIMPLE,
                ),
                DecomposedTask(
                    id=self._generate_id("summarize", task.id),
                    name="Summarize findings",
                    type=TaskType.TRANSFORMATION,
                    complexity=TaskComplexity.SIMPLE,
                ),
            ])

        elif "analyze" in desc_lower:
            subtasks.extend([
                DecomposedTask(
                    id=self._generate_id("gather", task.id),
                    name="Gather data",
                    type=TaskType.ACTION,
                    complexity=TaskComplexity.SIMPLE,
                ),
                DecomposedTask(
                    id=self._generate_id("process", task.id),
                    name="Process and clean data",
                    type=TaskType.TRANSFORMATION,
                    complexity=TaskComplexity.SIMPLE,
                ),
                DecomposedTask(
                    id=self._generate_id("analyze", task.id),
                    name="Perform analysis",
                    type=TaskType.ACTION,
                    complexity=TaskComplexity.MODERATE,
                ),
                DecomposedTask(
                    id=self._generate_id("interpret", task.id),
                    name="Interpret results",
                    type=TaskType.DECISION,
                    complexity=TaskComplexity.SIMPLE,
                ),
            ])

        elif "create" in desc_lower or "build" in desc_lower or "develop" in desc_lower:
            subtasks.extend([
                DecomposedTask(
                    id=self._generate_id("design", task.id),
                    name="Design solution",
                    type=TaskType.DECISION,
                    complexity=TaskComplexity.MODERATE,
                ),
                DecomposedTask(
                    id=self._generate_id("implement", task.id),
                    name="Implement solution",
                    type=TaskType.ACTION,
                    complexity=TaskComplexity.COMPLEX,
                ),
                DecomposedTask(
                    id=self._generate_id("test", task.id),
                    name="Test implementation",
                    type=TaskType.VALIDATION,
                    complexity=TaskComplexity.SIMPLE,
                ),
                DecomposedTask(
                    id=self._generate_id("refine", task.id),
                    name="Refine and improve",
                    type=TaskType.ACTION,
                    complexity=TaskComplexity.SIMPLE,
                ),
            ])

        else:
            # Generic decomposition
            subtasks.extend([
                DecomposedTask(
                    id=self._generate_id("understand", task.id),
                    name="Understand requirements",
                    type=TaskType.ACTION,
                    complexity=TaskComplexity.SIMPLE,
                ),
                DecomposedTask(
                    id=self._generate_id("execute", task.id),
                    name="Execute main task",
                    type=TaskType.ACTION,
                    complexity=TaskComplexity.MODERATE,
                ),
                DecomposedTask(
                    id=self._generate_id("verify", task.id),
                    name="Verify completion",
                    type=TaskType.VALIDATION,
                    complexity=TaskComplexity.SIMPLE,
                ),
            ])

        # Set dependencies based on strategy
        if strategy == DecompositionStrategy.SEQUENTIAL:
            for i in range(1, len(subtasks)):
                subtasks[i].depends_on.append(subtasks[i-1].id)
        elif strategy == DecompositionStrategy.PARALLEL:
            for st in subtasks:
                st.can_parallel = True

        return subtasks

    async def _decompose_research(
        self,
        task: DecomposedTask,
        max_depth: int,
    ) -> None:
        """Research-specific decomposition."""
        subtasks = [
            DecomposedTask(
                id=self._generate_id("define_scope", task.id),
                name="Define research scope",
                type=TaskType.DECISION,
                complexity=TaskComplexity.SIMPLE,
            ),
            DecomposedTask(
                id=self._generate_id("identify_sources", task.id),
                name="Identify information sources",
                type=TaskType.ACTION,
                complexity=TaskComplexity.SIMPLE,
            ),
            DecomposedTask(
                id=self._generate_id("gather_info", task.id),
                name="Gather information",
                type=TaskType.ACTION,
                complexity=TaskComplexity.MODERATE,
                can_parallel=True,
            ),
            DecomposedTask(
                id=self._generate_id("evaluate_sources", task.id),
                name="Evaluate source quality",
                type=TaskType.VALIDATION,
                complexity=TaskComplexity.SIMPLE,
            ),
            DecomposedTask(
                id=self._generate_id("synthesize", task.id),
                name="Synthesize findings",
                type=TaskType.TRANSFORMATION,
                complexity=TaskComplexity.MODERATE,
            ),
            DecomposedTask(
                id=self._generate_id("document", task.id),
                name="Document results",
                type=TaskType.ACTION,
                complexity=TaskComplexity.SIMPLE,
            ),
        ]

        # Set dependencies
        subtasks[1].depends_on.append(subtasks[0].id)
        subtasks[2].depends_on.append(subtasks[1].id)
        subtasks[3].depends_on.append(subtasks[2].id)
        subtasks[4].depends_on.append(subtasks[3].id)
        subtasks[5].depends_on.append(subtasks[4].id)

        for st in subtasks:
            st.parent_id = task.id
            st.depth = 1
            task.subtask_ids.append(st.id)
            self.tasks[st.id] = st
            self.stats["total_subtasks"] += 1

    async def _decompose_development(
        self,
        task: DecomposedTask,
        max_depth: int,
    ) -> None:
        """Development-specific decomposition."""
        subtasks = [
            DecomposedTask(
                id=self._generate_id("requirements", task.id),
                name="Gather requirements",
                type=TaskType.ACTION,
                complexity=TaskComplexity.SIMPLE,
            ),
            DecomposedTask(
                id=self._generate_id("design", task.id),
                name="Design architecture",
                type=TaskType.DECISION,
                complexity=TaskComplexity.MODERATE,
            ),
            DecomposedTask(
                id=self._generate_id("implement", task.id),
                name="Implement code",
                type=TaskType.ACTION,
                complexity=TaskComplexity.COMPLEX,
            ),
            DecomposedTask(
                id=self._generate_id("unit_tests", task.id),
                name="Write unit tests",
                type=TaskType.ACTION,
                complexity=TaskComplexity.MODERATE,
                can_parallel=True,
            ),
            DecomposedTask(
                id=self._generate_id("integration", task.id),
                name="Integration testing",
                type=TaskType.VALIDATION,
                complexity=TaskComplexity.MODERATE,
            ),
            DecomposedTask(
                id=self._generate_id("review", task.id),
                name="Code review",
                type=TaskType.VALIDATION,
                complexity=TaskComplexity.SIMPLE,
            ),
            DecomposedTask(
                id=self._generate_id("deploy", task.id),
                name="Deploy",
                type=TaskType.ACTION,
                complexity=TaskComplexity.SIMPLE,
            ),
        ]

        # Set dependencies
        subtasks[1].depends_on.append(subtasks[0].id)
        subtasks[2].depends_on.append(subtasks[1].id)
        subtasks[3].depends_on.append(subtasks[2].id)
        subtasks[4].depends_on.extend([subtasks[2].id, subtasks[3].id])
        subtasks[5].depends_on.append(subtasks[4].id)
        subtasks[6].depends_on.append(subtasks[5].id)

        for st in subtasks:
            st.parent_id = task.id
            st.depth = 1
            task.subtask_ids.append(st.id)
            self.tasks[st.id] = st
            self.stats["total_subtasks"] += 1

    async def _decompose_analysis(
        self,
        task: DecomposedTask,
        max_depth: int,
    ) -> None:
        """Analysis-specific decomposition."""
        await self._decompose_heuristic(
            task,
            DecompositionStrategy.SEQUENTIAL,
            max_depth,
        )

    async def _decompose_automation(
        self,
        task: DecomposedTask,
        max_depth: int,
    ) -> None:
        """Automation-specific decomposition."""
        await self._decompose_heuristic(
            task,
            DecompositionStrategy.SEQUENTIAL,
            max_depth,
        )

    def _infer_task_type(self, description: str) -> TaskType:
        """Infer task type from description."""
        desc_lower = description.lower()

        if any(w in desc_lower for w in ["decide", "choose", "select"]):
            return TaskType.DECISION
        elif any(w in desc_lower for w in ["check", "validate", "verify", "test"]):
            return TaskType.VALIDATION
        elif any(w in desc_lower for w in ["convert", "transform", "parse"]):
            return TaskType.TRANSFORMATION
        elif any(w in desc_lower for w in ["send", "notify", "email"]):
            return TaskType.COMMUNICATION
        elif any(w in desc_lower for w in ["sync", "coordinate", "orchestrate"]):
            return TaskType.COORDINATION

        return TaskType.ACTION

    def _estimate_complexity(self, description: str) -> TaskComplexity:
        """Estimate task complexity."""
        desc_lower = description.lower()
        word_count = len(description.split())

        # Complex keywords
        complex_keywords = ["comprehensive", "complete", "full", "entire", "all"]
        has_complex = any(k in desc_lower for k in complex_keywords)

        if word_count > 50 or has_complex:
            return TaskComplexity.VERY_COMPLEX
        elif word_count > 30:
            return TaskComplexity.COMPLEX
        elif word_count > 15:
            return TaskComplexity.MODERATE
        elif word_count > 5:
            return TaskComplexity.SIMPLE

        return TaskComplexity.TRIVIAL

    def _build_dependencies(self, root: DecomposedTask) -> None:
        """Build dependency graph from task tree."""
        for task in self.tasks.values():
            for dep_id in task.depends_on:
                self.dependencies.add(TaskDependency(
                    from_task_id=dep_id,
                    to_task_id=task.id,
                ))

    def _update_stats(self) -> None:
        """Update decomposition statistics."""
        if self.tasks:
            total_depth = sum(t.depth for t in self.tasks.values())
            self.stats["avg_depth"] = total_depth / len(self.tasks)

    def get_execution_order(self, root_id: str) -> List[List[str]]:
        """
        Get tasks in execution order (levels for parallelism).

        Returns:
            List of lists, each inner list can execute in parallel
        """
        levels: List[List[str]] = []
        completed: Set[str] = set()

        while True:
            # Find tasks whose dependencies are all satisfied
            ready = []
            for task_id, task in self.tasks.items():
                if task_id in completed:
                    continue
                if all(d in completed for d in task.depends_on):
                    ready.append(task_id)

            if not ready:
                break

            levels.append(ready)
            completed.update(ready)

        return levels

    def visualize(self, root_id: str) -> str:
        """Generate text visualization of task tree."""
        lines = []

        def _render(task_id: str, prefix: str = "", is_last: bool = True):
            task = self.tasks.get(task_id)
            if not task:
                return

            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{task.name}")

            child_prefix = prefix + ("    " if is_last else "│   ")
            children = task.subtask_ids

            for i, child_id in enumerate(children):
                _render(child_id, child_prefix, i == len(children) - 1)

        root = self.tasks.get(root_id)
        if root:
            lines.append(root.name)
            for i, child_id in enumerate(root.subtask_ids):
                _render(child_id, "", i == len(root.subtask_ids) - 1)

        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        """Get decomposer statistics."""
        return {
            **self.stats,
            "total_tasks": len(self.tasks),
            "total_dependencies": len(self.dependencies),
        }


def demo():
    """Demonstrate task decomposer."""
    import asyncio

    print("=" * 60)
    print("BAEL Task Decomposer Demo")
    print("=" * 60)

    decomposer = TaskDecomposer()

    # Decompose a complex task
    async def decompose_task():
        return await decomposer.decompose(
            "Build a comprehensive web scraping system that can extract data from multiple sources, handle pagination, and store results in a database",
            strategy=DecompositionStrategy.HIERARCHICAL,
            max_depth=2,
        )

    root_task = asyncio.run(decompose_task())

    print(f"\nRoot task: {root_task.name}")
    print(f"Complexity: {root_task.complexity.value}")
    print(f"Subtasks: {len(root_task.subtask_ids)}")

    # Visualize
    print("\nTask tree:")
    print(decomposer.visualize(root_task.id))

    # Execution order
    execution_order = decomposer.get_execution_order(root_task.id)
    print(f"\nExecution levels: {len(execution_order)}")
    for i, level in enumerate(execution_order):
        task_names = [decomposer.tasks[tid].name for tid in level]
        print(f"  Level {i+1}: {task_names}")

    print(f"\nStats: {decomposer.get_stats()}")


if __name__ == "__main__":
    demo()
