"""
🧠 PROBLEM CORE 🧠
==================
Core problem structures.

Features:
- Problem representation
- State spaces
- Solution tracking
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from datetime import datetime
import uuid


class ProblemType(Enum):
    """Types of problems"""
    SEARCH = auto()           # Find path
    OPTIMIZATION = auto()     # Find best
    CONSTRAINT = auto()       # Satisfy constraints
    PLANNING = auto()         # Sequence of actions
    CLASSIFICATION = auto()   # Categorization
    REASONING = auto()        # Logical deduction
    LEARNING = auto()         # Pattern learning


@dataclass
class ProblemState:
    """A state in the problem space"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # State representation
    data: Any = None

    # Evaluation
    cost: float = 0.0
    heuristic: float = 0.0

    # Parent for path reconstruction
    parent_id: Optional[str] = None
    action_from_parent: str = ""

    # Flags
    is_goal: bool = False
    is_dead_end: bool = False

    @property
    def f_score(self) -> float:
        """f(n) = g(n) + h(n)"""
        return self.cost + self.heuristic

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, ProblemState):
            return self.id == other.id
        return False


@dataclass
class Problem:
    """A problem to solve"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Problem definition
    name: str = ""
    description: str = ""
    problem_type: ProblemType = ProblemType.SEARCH

    # States
    initial_state: Optional[ProblemState] = None

    # Goal specification
    goal_test: Optional[Callable[[ProblemState], bool]] = None
    goal_states: List[ProblemState] = field(default_factory=list)

    # Operators
    operators: List[str] = field(default_factory=list)

    # Functions (to be set)
    successor_fn: Optional[Callable[[ProblemState], List[Tuple[str, ProblemState]]]] = None
    cost_fn: Optional[Callable[[ProblemState, str, ProblemState], float]] = None
    heuristic_fn: Optional[Callable[[ProblemState], float]] = None

    # Constraints
    constraints: List[Any] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)

    def is_goal(self, state: ProblemState) -> bool:
        """Check if state is goal"""
        if self.goal_test:
            return self.goal_test(state)
        return state in self.goal_states

    def get_successors(self, state: ProblemState) -> List[Tuple[str, ProblemState]]:
        """Get successor states"""
        if self.successor_fn:
            return self.successor_fn(state)
        return []

    def get_cost(
        self,
        state: ProblemState,
        action: str,
        next_state: ProblemState
    ) -> float:
        """Get action cost"""
        if self.cost_fn:
            return self.cost_fn(state, action, next_state)
        return 1.0  # Default unit cost

    def get_heuristic(self, state: ProblemState) -> float:
        """Get heuristic value"""
        if self.heuristic_fn:
            return self.heuristic_fn(state)
        return 0.0  # Default: no heuristic


@dataclass
class Solution:
    """A solution to a problem"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    problem_id: str = ""

    # Path
    path: List[ProblemState] = field(default_factory=list)
    actions: List[str] = field(default_factory=list)

    # Quality
    total_cost: float = 0.0
    is_optimal: bool = False

    # Metadata
    found_at: datetime = field(default_factory=datetime.now)
    search_method: str = ""

    # Statistics
    nodes_expanded: int = 0
    nodes_generated: int = 0
    time_seconds: float = 0.0

    def __len__(self):
        return len(self.path)

    def is_valid(self) -> bool:
        """Check if solution is valid"""
        return len(self.path) > 0 and self.path[-1].is_goal


class SearchSpace:
    """
    The space of possible states.
    """

    def __init__(self, problem: Problem):
        self.problem = problem

        # State storage
        self.states: Dict[str, ProblemState] = {}

        # Exploration tracking
        self.explored: Set[str] = set()
        self.frontier: List[ProblemState] = []

        # Statistics
        self.nodes_generated = 0
        self.nodes_expanded = 0

        # Initialize with initial state
        if problem.initial_state:
            self.add_state(problem.initial_state)
            self.frontier.append(problem.initial_state)

    def add_state(self, state: ProblemState):
        """Add state to space"""
        self.states[state.id] = state
        self.nodes_generated += 1

    def expand(self, state: ProblemState) -> List[ProblemState]:
        """Expand a state"""
        if state.id in self.explored:
            return []

        self.explored.add(state.id)
        self.nodes_expanded += 1

        successors = []
        for action, next_state in self.problem.get_successors(state):
            # Set parent
            next_state.parent_id = state.id
            next_state.action_from_parent = action

            # Calculate cost
            step_cost = self.problem.get_cost(state, action, next_state)
            next_state.cost = state.cost + step_cost

            # Calculate heuristic
            next_state.heuristic = self.problem.get_heuristic(next_state)

            # Check goal
            next_state.is_goal = self.problem.is_goal(next_state)

            # Add to space
            self.add_state(next_state)
            successors.append(next_state)

        return successors

    def get_path(self, state: ProblemState) -> List[ProblemState]:
        """Reconstruct path from initial to state"""
        path = []
        current = state

        while current:
            path.append(current)
            if current.parent_id:
                current = self.states.get(current.parent_id)
            else:
                break

        return list(reversed(path))

    def get_actions(self, state: ProblemState) -> List[str]:
        """Get actions along path"""
        path = self.get_path(state)
        actions = []

        for s in path[1:]:  # Skip initial state
            actions.append(s.action_from_parent)

        return actions

    def is_explored(self, state: ProblemState) -> bool:
        """Check if state was explored"""
        return state.id in self.explored

    def reset(self):
        """Reset exploration"""
        self.explored.clear()
        self.frontier.clear()
        self.nodes_generated = 0
        self.nodes_expanded = 0

        if self.problem.initial_state:
            self.add_state(self.problem.initial_state)
            self.frontier.append(self.problem.initial_state)


# Export all
__all__ = [
    'ProblemType',
    'ProblemState',
    'Problem',
    'Solution',
    'SearchSpace',
]
