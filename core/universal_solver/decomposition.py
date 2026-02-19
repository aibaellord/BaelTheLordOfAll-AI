"""
🧠 PROBLEM DECOMPOSITION 🧠
===========================
Break problems into subproblems.

Features:
- Hierarchical decomposition
- Dependency analysis
- Subproblem synthesis
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import uuid

from .problem_core import Problem, ProblemType, Solution


class DecompositionStrategy(Enum):
    """Decomposition strategies"""
    SEQUENTIAL = auto()      # Subproblems in order
    PARALLEL = auto()        # Independent subproblems
    HIERARCHICAL = auto()    # Tree structure
    FUNCTIONAL = auto()      # By function
    GOAL = auto()           # By subgoal


@dataclass
class SubProblem:
    """A subproblem of a larger problem"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Parent
    parent_problem_id: str = ""

    # The subproblem itself
    problem: Optional[Problem] = None

    # Position in decomposition
    index: int = 0
    depth: int = 0

    # Dependencies
    depends_on: List[str] = field(default_factory=list)  # IDs of dependent subproblems

    # Solution
    solution: Optional[Solution] = None
    is_solved: bool = False

    # Priority
    priority: float = 0.0

    def can_solve(self, solved_ids: Set[str]) -> bool:
        """Check if all dependencies are satisfied"""
        return all(dep in solved_ids for dep in self.depends_on)


class ProblemDecomposer:
    """
    Decomposes problems into subproblems.
    """

    def __init__(self):
        self.strategies: Dict[DecompositionStrategy, Callable] = {
            DecompositionStrategy.SEQUENTIAL: self._sequential_decomposition,
            DecompositionStrategy.PARALLEL: self._parallel_decomposition,
            DecompositionStrategy.HIERARCHICAL: self._hierarchical_decomposition,
            DecompositionStrategy.FUNCTIONAL: self._functional_decomposition,
            DecompositionStrategy.GOAL: self._goal_decomposition,
        }

    def decompose(
        self,
        problem: Problem,
        strategy: DecompositionStrategy = DecompositionStrategy.HIERARCHICAL,
        max_depth: int = 5
    ) -> List[SubProblem]:
        """Decompose problem"""
        decompose_fn = self.strategies.get(strategy)

        if decompose_fn:
            return decompose_fn(problem, max_depth)

        return [SubProblem(
            parent_problem_id=problem.id,
            problem=problem,
            index=0
        )]

    def _sequential_decomposition(
        self,
        problem: Problem,
        max_depth: int
    ) -> List[SubProblem]:
        """Decompose into sequential subproblems"""
        subproblems = []

        # Split by operators
        n_parts = min(len(problem.operators), 5) or 3

        for i in range(n_parts):
            sub = SubProblem(
                parent_problem_id=problem.id,
                problem=Problem(
                    name=f"{problem.name}_part_{i}",
                    problem_type=problem.problem_type,
                ),
                index=i,
                priority=n_parts - i  # Earlier = higher priority
            )

            # Sequential dependency
            if i > 0:
                sub.depends_on = [subproblems[i - 1].id]

            subproblems.append(sub)

        return subproblems

    def _parallel_decomposition(
        self,
        problem: Problem,
        max_depth: int
    ) -> List[SubProblem]:
        """Decompose into parallel subproblems"""
        subproblems = []

        n_parts = min(len(problem.constraints), 4) or 2

        for i in range(n_parts):
            sub = SubProblem(
                parent_problem_id=problem.id,
                problem=Problem(
                    name=f"{problem.name}_parallel_{i}",
                    problem_type=problem.problem_type,
                ),
                index=i,
                depends_on=[],  # No dependencies - parallel
                priority=1.0
            )
            subproblems.append(sub)

        return subproblems

    def _hierarchical_decomposition(
        self,
        problem: Problem,
        max_depth: int
    ) -> List[SubProblem]:
        """Hierarchical decomposition"""
        subproblems = []

        def decompose_recursive(prob: Problem, depth: int, parent_idx: str):
            if depth >= max_depth:
                return

            # Create 2-3 subproblems at each level
            n_children = 2 if depth > 0 else 3

            for i in range(n_children):
                idx = f"{parent_idx}.{i}" if parent_idx else str(i)

                sub = SubProblem(
                    parent_problem_id=prob.id,
                    problem=Problem(
                        name=f"{problem.name}_{idx}",
                        problem_type=prob.problem_type,
                    ),
                    index=len(subproblems),
                    depth=depth,
                    priority=1.0 / (depth + 1)
                )
                subproblems.append(sub)

                # Recurse
                if depth < max_depth - 1:
                    decompose_recursive(sub.problem, depth + 1, idx)

        decompose_recursive(problem, 0, "")
        return subproblems

    def _functional_decomposition(
        self,
        problem: Problem,
        max_depth: int
    ) -> List[SubProblem]:
        """Decompose by function"""
        # Common functional decomposition
        functions = ["analyze", "design", "implement", "verify", "optimize"]

        subproblems = []
        for i, func in enumerate(functions):
            sub = SubProblem(
                parent_problem_id=problem.id,
                problem=Problem(
                    name=f"{problem.name}_{func}",
                    problem_type=problem.problem_type,
                ),
                index=i,
                priority=len(functions) - i
            )

            # Sequential dependencies
            if i > 0:
                sub.depends_on = [subproblems[i - 1].id]

            subproblems.append(sub)

        return subproblems

    def _goal_decomposition(
        self,
        problem: Problem,
        max_depth: int
    ) -> List[SubProblem]:
        """Decompose by subgoals"""
        subproblems = []

        # Each goal state becomes a subproblem
        for i, goal in enumerate(problem.goal_states):
            sub = SubProblem(
                parent_problem_id=problem.id,
                problem=Problem(
                    name=f"{problem.name}_goal_{i}",
                    problem_type=problem.problem_type,
                    goal_states=[goal],
                ),
                index=i,
                priority=1.0
            )
            subproblems.append(sub)

        return subproblems


class HierarchicalDecomposer:
    """
    Hierarchical task network decomposition.
    """

    def __init__(self):
        # Method library: task -> decomposition methods
        self.methods: Dict[str, List[Callable]] = {}

        # Primitive tasks (cannot be decomposed further)
        self.primitives: Set[str] = set()

    def add_method(self, task: str, method: Callable[[Any], List[str]]):
        """Add decomposition method for task"""
        if task not in self.methods:
            self.methods[task] = []
        self.methods[task].append(method)

    def add_primitive(self, task: str):
        """Mark task as primitive"""
        self.primitives.add(task)

    def decompose(
        self,
        task: str,
        state: Any = None
    ) -> List[str]:
        """Decompose task into subtasks"""
        if task in self.primitives:
            return [task]

        if task not in self.methods:
            return [task]  # No method - treat as primitive

        # Try methods until one succeeds
        for method in self.methods[task]:
            try:
                subtasks = method(state)
                if subtasks:
                    # Recursively decompose subtasks
                    result = []
                    for subtask in subtasks:
                        result.extend(self.decompose(subtask, state))
                    return result
            except Exception:
                continue

        return [task]  # No method succeeded

    def plan(
        self,
        goal_task: str,
        initial_state: Any = None
    ) -> List[str]:
        """Generate plan by decomposing goal task"""
        return self.decompose(goal_task, initial_state)


class SubproblemSynthesizer:
    """
    Synthesizes solutions from subproblem solutions.
    """

    def __init__(self):
        self.synthesis_rules: List[Callable] = []

    def add_rule(self, rule: Callable[[List[Solution]], Solution]):
        """Add synthesis rule"""
        self.synthesis_rules.append(rule)

    def synthesize(
        self,
        subproblems: List[SubProblem],
        original_problem: Problem
    ) -> Optional[Solution]:
        """Synthesize solution from subproblem solutions"""
        # Check all subproblems are solved
        if not all(sp.is_solved for sp in subproblems):
            return None

        # Collect solutions
        solutions = [sp.solution for sp in subproblems if sp.solution]

        if not solutions:
            return None

        # Try synthesis rules
        for rule in self.synthesis_rules:
            try:
                combined = rule(solutions)
                if combined:
                    combined.problem_id = original_problem.id
                    return combined
            except Exception:
                continue

        # Default: concatenate paths
        combined = Solution(
            problem_id=original_problem.id,
            search_method="subproblem_synthesis"
        )

        for sol in solutions:
            combined.path.extend(sol.path)
            combined.actions.extend(sol.actions)
            combined.total_cost += sol.total_cost
            combined.nodes_expanded += sol.nodes_expanded

        return combined


# Export all
__all__ = [
    'DecompositionStrategy',
    'SubProblem',
    'ProblemDecomposer',
    'HierarchicalDecomposer',
    'SubproblemSynthesizer',
]
