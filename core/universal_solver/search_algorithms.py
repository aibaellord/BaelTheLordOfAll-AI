"""
🧠 SEARCH ALGORITHMS 🧠
=======================
State space search algorithms.

Features:
- Uninformed search
- Informed search
- Local search
"""

from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Set
from datetime import datetime
import heapq
import time

from .problem_core import Problem, ProblemState, Solution, SearchSpace


@dataclass
class SearchNode:
    """Node in search tree"""
    state: ProblemState

    # For priority queue
    priority: float = 0.0

    def __lt__(self, other):
        return self.priority < other.priority


@dataclass
class SearchResult:
    """Result of a search"""
    solution: Optional[Solution] = None
    success: bool = False

    # Statistics
    nodes_expanded: int = 0
    nodes_generated: int = 0
    max_frontier_size: int = 0
    time_seconds: float = 0.0

    # Search info
    algorithm: str = ""
    terminated_reason: str = ""


class SearchAlgorithm(ABC):
    """Base class for search algorithms"""

    def __init__(self):
        self.name = "Search"

    @abstractmethod
    def search(self, problem: Problem) -> SearchResult:
        """Perform search"""
        pass

    def _create_solution(
        self,
        goal_state: ProblemState,
        search_space: SearchSpace,
        start_time: float
    ) -> Solution:
        """Create solution from goal state"""
        return Solution(
            problem_id=search_space.problem.id,
            path=search_space.get_path(goal_state),
            actions=search_space.get_actions(goal_state),
            total_cost=goal_state.cost,
            found_at=datetime.now(),
            search_method=self.name,
            nodes_expanded=search_space.nodes_expanded,
            nodes_generated=search_space.nodes_generated,
            time_seconds=time.time() - start_time
        )


class BreadthFirstSearch(SearchAlgorithm):
    """Breadth-first search"""

    def __init__(self):
        super().__init__()
        self.name = "BFS"

    def search(self, problem: Problem) -> SearchResult:
        start_time = time.time()

        search_space = SearchSpace(problem)
        result = SearchResult(algorithm=self.name)

        frontier = [problem.initial_state]
        max_frontier = 1

        while frontier:
            max_frontier = max(max_frontier, len(frontier))

            # FIFO - pop from front
            current = frontier.pop(0)

            # Goal check
            if problem.is_goal(current):
                result.success = True
                result.solution = self._create_solution(
                    current, search_space, start_time
                )
                break

            # Expand
            successors = search_space.expand(current)

            # Add to frontier
            for successor in successors:
                if not search_space.is_explored(successor):
                    frontier.append(successor)

        result.nodes_expanded = search_space.nodes_expanded
        result.nodes_generated = search_space.nodes_generated
        result.max_frontier_size = max_frontier
        result.time_seconds = time.time() - start_time
        result.terminated_reason = "goal_found" if result.success else "exhausted"

        return result


class DepthFirstSearch(SearchAlgorithm):
    """Depth-first search"""

    def __init__(self, max_depth: int = 100):
        super().__init__()
        self.name = "DFS"
        self.max_depth = max_depth

    def search(self, problem: Problem) -> SearchResult:
        start_time = time.time()

        search_space = SearchSpace(problem)
        result = SearchResult(algorithm=self.name)

        frontier = [(problem.initial_state, 0)]  # (state, depth)
        max_frontier = 1

        while frontier:
            max_frontier = max(max_frontier, len(frontier))

            # LIFO - pop from end
            current, depth = frontier.pop()

            # Depth limit
            if depth > self.max_depth:
                continue

            # Goal check
            if problem.is_goal(current):
                result.success = True
                result.solution = self._create_solution(
                    current, search_space, start_time
                )
                break

            # Expand
            successors = search_space.expand(current)

            # Add to frontier (reverse for left-to-right exploration)
            for successor in reversed(successors):
                if not search_space.is_explored(successor):
                    frontier.append((successor, depth + 1))

        result.nodes_expanded = search_space.nodes_expanded
        result.nodes_generated = search_space.nodes_generated
        result.max_frontier_size = max_frontier
        result.time_seconds = time.time() - start_time
        result.terminated_reason = "goal_found" if result.success else "exhausted"

        return result


class IterativeDeepeningSearch(SearchAlgorithm):
    """Iterative deepening DFS"""

    def __init__(self, max_depth: int = 100):
        super().__init__()
        self.name = "IDS"
        self.max_depth = max_depth

    def search(self, problem: Problem) -> SearchResult:
        start_time = time.time()
        result = SearchResult(algorithm=self.name)

        total_expanded = 0
        total_generated = 0

        for depth_limit in range(self.max_depth):
            dfs = DepthFirstSearch(max_depth=depth_limit)
            dfs_result = dfs.search(problem)

            total_expanded += dfs_result.nodes_expanded
            total_generated += dfs_result.nodes_generated

            if dfs_result.success:
                result.success = True
                result.solution = dfs_result.solution
                break

        result.nodes_expanded = total_expanded
        result.nodes_generated = total_generated
        result.time_seconds = time.time() - start_time
        result.terminated_reason = "goal_found" if result.success else "max_depth"

        return result


class AStarSearch(SearchAlgorithm):
    """A* search"""

    def __init__(self):
        super().__init__()
        self.name = "A*"

    def search(self, problem: Problem) -> SearchResult:
        start_time = time.time()

        search_space = SearchSpace(problem)
        result = SearchResult(algorithm=self.name)

        # Priority queue: (f_score, node)
        initial = problem.initial_state
        initial.heuristic = problem.get_heuristic(initial)

        frontier = []
        heapq.heappush(frontier, SearchNode(initial, initial.f_score))

        max_frontier = 1

        while frontier:
            max_frontier = max(max_frontier, len(frontier))

            # Pop lowest f-score
            node = heapq.heappop(frontier)
            current = node.state

            # Skip if already explored
            if search_space.is_explored(current):
                continue

            # Goal check
            if problem.is_goal(current):
                result.success = True
                result.solution = self._create_solution(
                    current, search_space, start_time
                )
                result.solution.is_optimal = True
                break

            # Expand
            successors = search_space.expand(current)

            # Add to frontier
            for successor in successors:
                if not search_space.is_explored(successor):
                    heapq.heappush(
                        frontier,
                        SearchNode(successor, successor.f_score)
                    )

        result.nodes_expanded = search_space.nodes_expanded
        result.nodes_generated = search_space.nodes_generated
        result.max_frontier_size = max_frontier
        result.time_seconds = time.time() - start_time
        result.terminated_reason = "goal_found" if result.success else "exhausted"

        return result


class BeamSearch(SearchAlgorithm):
    """Beam search with limited frontier"""

    def __init__(self, beam_width: int = 10):
        super().__init__()
        self.name = "BeamSearch"
        self.beam_width = beam_width

    def search(self, problem: Problem) -> SearchResult:
        start_time = time.time()

        search_space = SearchSpace(problem)
        result = SearchResult(algorithm=self.name)

        # Current level
        current_level = [problem.initial_state]

        while current_level:
            # Check goals
            for state in current_level:
                if problem.is_goal(state):
                    result.success = True
                    result.solution = self._create_solution(
                        state, search_space, start_time
                    )
                    result.nodes_expanded = search_space.nodes_expanded
                    result.nodes_generated = search_space.nodes_generated
                    result.time_seconds = time.time() - start_time
                    result.terminated_reason = "goal_found"
                    return result

            # Expand all in current level
            next_level = []
            for state in current_level:
                successors = search_space.expand(state)
                next_level.extend(successors)

            if not next_level:
                break

            # Keep only best (by heuristic)
            next_level.sort(key=lambda s: s.heuristic)
            current_level = next_level[:self.beam_width]

        result.nodes_expanded = search_space.nodes_expanded
        result.nodes_generated = search_space.nodes_generated
        result.time_seconds = time.time() - start_time
        result.terminated_reason = "exhausted"

        return result


class BestFirstSearch(SearchAlgorithm):
    """Greedy best-first search"""

    def __init__(self):
        super().__init__()
        self.name = "BestFirst"

    def search(self, problem: Problem) -> SearchResult:
        start_time = time.time()

        search_space = SearchSpace(problem)
        result = SearchResult(algorithm=self.name)

        # Priority queue by heuristic only
        initial = problem.initial_state
        initial.heuristic = problem.get_heuristic(initial)

        frontier = []
        heapq.heappush(frontier, SearchNode(initial, initial.heuristic))

        max_frontier = 1

        while frontier:
            max_frontier = max(max_frontier, len(frontier))

            node = heapq.heappop(frontier)
            current = node.state

            if search_space.is_explored(current):
                continue

            if problem.is_goal(current):
                result.success = True
                result.solution = self._create_solution(
                    current, search_space, start_time
                )
                break

            successors = search_space.expand(current)

            for successor in successors:
                if not search_space.is_explored(successor):
                    heapq.heappush(
                        frontier,
                        SearchNode(successor, successor.heuristic)
                    )

        result.nodes_expanded = search_space.nodes_expanded
        result.nodes_generated = search_space.nodes_generated
        result.max_frontier_size = max_frontier
        result.time_seconds = time.time() - start_time
        result.terminated_reason = "goal_found" if result.success else "exhausted"

        return result


class BidirectionalSearch(SearchAlgorithm):
    """Bidirectional search"""

    def __init__(self):
        super().__init__()
        self.name = "Bidirectional"

    def search(self, problem: Problem) -> SearchResult:
        start_time = time.time()
        result = SearchResult(algorithm=self.name)

        if not problem.goal_states:
            result.terminated_reason = "no_goal_states"
            return result

        # Forward from initial
        forward_explored: Dict[str, ProblemState] = {}
        forward_frontier = [problem.initial_state]

        # Backward from goals (simplified - needs reverse operators)
        backward_explored: Dict[str, ProblemState] = {}
        backward_frontier = list(problem.goal_states)

        nodes_expanded = 0

        while forward_frontier and backward_frontier:
            # Expand forward
            if forward_frontier:
                current = forward_frontier.pop(0)

                if current.id in backward_explored:
                    # Found connection
                    result.success = True
                    result.terminated_reason = "goal_found"
                    break

                forward_explored[current.id] = current
                nodes_expanded += 1

                for action, successor in problem.get_successors(current):
                    if successor.id not in forward_explored:
                        successor.parent_id = current.id
                        forward_frontier.append(successor)

            # Expand backward (simplified)
            if backward_frontier:
                current = backward_frontier.pop(0)

                if current.id in forward_explored:
                    result.success = True
                    result.terminated_reason = "goal_found"
                    break

                backward_explored[current.id] = current
                nodes_expanded += 1

        result.nodes_expanded = nodes_expanded
        result.time_seconds = time.time() - start_time

        return result


# Export all
__all__ = [
    'SearchNode',
    'SearchResult',
    'SearchAlgorithm',
    'BreadthFirstSearch',
    'DepthFirstSearch',
    'IterativeDeepeningSearch',
    'AStarSearch',
    'BeamSearch',
    'BestFirstSearch',
    'BidirectionalSearch',
]
