#!/usr/bin/env python3
"""
BAEL - Heuristic Manager
Advanced heuristic search and optimization.

Features:
- A* search
- Beam search
- Iterative deepening
- Heuristic functions
- Meta-heuristics
- Simulated annealing
"""

import asyncio
import copy
import heapq
import math
import random
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')
S = TypeVar('S')  # State type


# =============================================================================
# ENUMS
# =============================================================================

class SearchStrategy(Enum):
    """Search strategies."""
    BEST_FIRST = "best_first"
    A_STAR = "a_star"
    BEAM = "beam"
    GREEDY = "greedy"
    ITERATIVE_DEEPENING = "iterative_deepening"


class OptimizationStrategy(Enum):
    """Optimization strategies."""
    HILL_CLIMBING = "hill_climbing"
    SIMULATED_ANNEALING = "simulated_annealing"
    GENETIC = "genetic"
    TABU = "tabu"


class HeuristicType(Enum):
    """Types of heuristics."""
    ADMISSIBLE = "admissible"
    INADMISSIBLE = "inadmissible"
    CONSISTENT = "consistent"


class SearchStatus(Enum):
    """Status of search."""
    RUNNING = "running"
    FOUND = "found"
    NOT_FOUND = "not_found"
    TERMINATED = "terminated"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class State:
    """A search state."""
    state_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    data: Any = None

    def __hash__(self):
        return hash(self.state_id)

    def __eq__(self, other):
        if isinstance(other, State):
            return self.state_id == other.state_id
        return False


@dataclass
class SearchNode:
    """A node in search tree."""
    node_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: State = field(default_factory=State)
    parent_id: Optional[str] = None
    action: Optional[str] = None
    g_cost: float = 0.0  # Cost from start
    h_cost: float = 0.0  # Heuristic estimate to goal
    depth: int = 0

    @property
    def f_cost(self) -> float:
        """Total estimated cost."""
        return self.g_cost + self.h_cost

    def __lt__(self, other: "SearchNode") -> bool:
        return self.f_cost < other.f_cost


@dataclass
class SearchResult:
    """Result of a search."""
    status: SearchStatus = SearchStatus.NOT_FOUND
    path: List[str] = field(default_factory=list)
    cost: float = 0.0
    nodes_expanded: int = 0
    nodes_generated: int = 0
    max_depth: int = 0


@dataclass
class HeuristicFunction:
    """A heuristic function."""
    func_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    function: Optional[Callable[[State, State], float]] = None
    heuristic_type: HeuristicType = HeuristicType.ADMISSIBLE


@dataclass
class TabuEntry:
    """An entry in tabu list."""
    solution: Any = None
    tenure: int = 5
    added_at: int = 0


# =============================================================================
# HEURISTIC FUNCTION LIBRARY
# =============================================================================

class HeuristicLibrary:
    """Library of heuristic functions."""

    @staticmethod
    def manhattan_distance(
        state: State,
        goal: State
    ) -> float:
        """Manhattan distance heuristic."""
        if not hasattr(state.data, '__iter__') or not hasattr(goal.data, '__iter__'):
            return 0.0

        try:
            s_data = list(state.data)
            g_data = list(goal.data)
            return sum(abs(s - g) for s, g in zip(s_data, g_data))
        except:
            return 0.0

    @staticmethod
    def euclidean_distance(
        state: State,
        goal: State
    ) -> float:
        """Euclidean distance heuristic."""
        if not hasattr(state.data, '__iter__') or not hasattr(goal.data, '__iter__'):
            return 0.0

        try:
            s_data = list(state.data)
            g_data = list(goal.data)
            return math.sqrt(sum((s - g) ** 2 for s, g in zip(s_data, g_data)))
        except:
            return 0.0

    @staticmethod
    def hamming_distance(
        state: State,
        goal: State
    ) -> float:
        """Hamming distance (mismatched positions)."""
        if not hasattr(state.data, '__iter__') or not hasattr(goal.data, '__iter__'):
            return 0.0

        try:
            s_data = list(state.data)
            g_data = list(goal.data)
            return sum(1 for s, g in zip(s_data, g_data) if s != g)
        except:
            return 0.0

    @staticmethod
    def zero_heuristic(state: State, goal: State) -> float:
        """Zero heuristic (Dijkstra's algorithm)."""
        return 0.0


# =============================================================================
# A* SEARCH
# =============================================================================

class AStarSearch:
    """A* search algorithm."""

    def __init__(
        self,
        heuristic: Callable[[State, State], float] = HeuristicLibrary.zero_heuristic
    ):
        self._heuristic = heuristic
        self._nodes: Dict[str, SearchNode] = {}

    def search(
        self,
        start: State,
        goal: State,
        successors: Callable[[State], List[Tuple[State, str, float]]],
        max_nodes: int = 10000
    ) -> SearchResult:
        """
        Perform A* search.

        successors: function returning [(next_state, action, cost), ...]
        """
        result = SearchResult()

        # Initialize
        start_node = SearchNode(
            state=start,
            g_cost=0.0,
            h_cost=self._heuristic(start, goal)
        )
        self._nodes[start_node.node_id] = start_node

        open_set: List[SearchNode] = [start_node]
        closed_set: Set[str] = set()
        state_to_node: Dict[str, str] = {start.state_id: start_node.node_id}

        while open_set and result.nodes_expanded < max_nodes:
            # Get node with lowest f_cost
            current = heapq.heappop(open_set)
            result.nodes_expanded += 1

            # Goal check
            if current.state.state_id == goal.state_id:
                result.status = SearchStatus.FOUND
                result.cost = current.g_cost
                result.path = self._reconstruct_path(current.node_id)
                return result

            closed_set.add(current.state.state_id)
            result.max_depth = max(result.max_depth, current.depth)

            # Expand successors
            for next_state, action, cost in successors(current.state):
                if next_state.state_id in closed_set:
                    continue

                g_cost = current.g_cost + cost
                h_cost = self._heuristic(next_state, goal)

                # Check if we've seen this state
                if next_state.state_id in state_to_node:
                    existing_id = state_to_node[next_state.state_id]
                    existing = self._nodes[existing_id]
                    if g_cost < existing.g_cost:
                        existing.g_cost = g_cost
                        existing.parent_id = current.node_id
                        existing.action = action
                        heapq.heapify(open_set)
                else:
                    new_node = SearchNode(
                        state=next_state,
                        parent_id=current.node_id,
                        action=action,
                        g_cost=g_cost,
                        h_cost=h_cost,
                        depth=current.depth + 1
                    )
                    self._nodes[new_node.node_id] = new_node
                    state_to_node[next_state.state_id] = new_node.node_id
                    heapq.heappush(open_set, new_node)
                    result.nodes_generated += 1

        result.status = SearchStatus.NOT_FOUND if not open_set else SearchStatus.TERMINATED
        return result

    def _reconstruct_path(self, node_id: str) -> List[str]:
        """Reconstruct path from goal to start."""
        path = []
        current_id = node_id

        while current_id:
            node = self._nodes[current_id]
            if node.action:
                path.append(node.action)
            current_id = node.parent_id

        return list(reversed(path))


# =============================================================================
# BEAM SEARCH
# =============================================================================

class BeamSearch:
    """Beam search algorithm."""

    def __init__(
        self,
        beam_width: int = 3,
        heuristic: Callable[[State, State], float] = HeuristicLibrary.zero_heuristic
    ):
        self._beam_width = beam_width
        self._heuristic = heuristic

    def search(
        self,
        start: State,
        goal: State,
        successors: Callable[[State], List[Tuple[State, str, float]]],
        max_depth: int = 100
    ) -> SearchResult:
        """Perform beam search."""
        result = SearchResult()

        beam: List[SearchNode] = [SearchNode(
            state=start,
            h_cost=self._heuristic(start, goal)
        )]

        for depth in range(max_depth):
            result.max_depth = depth

            # Check for goal
            for node in beam:
                if node.state.state_id == goal.state_id:
                    result.status = SearchStatus.FOUND
                    result.cost = node.g_cost
                    return result

            # Expand all nodes in beam
            candidates: List[SearchNode] = []

            for node in beam:
                result.nodes_expanded += 1

                for next_state, action, cost in successors(node.state):
                    new_node = SearchNode(
                        state=next_state,
                        parent_id=node.node_id,
                        action=action,
                        g_cost=node.g_cost + cost,
                        h_cost=self._heuristic(next_state, goal),
                        depth=depth + 1
                    )
                    candidates.append(new_node)
                    result.nodes_generated += 1

            if not candidates:
                break

            # Keep best beam_width nodes
            candidates.sort(key=lambda n: n.h_cost)
            beam = candidates[:self._beam_width]

        result.status = SearchStatus.NOT_FOUND
        return result


# =============================================================================
# ITERATIVE DEEPENING
# =============================================================================

class IterativeDeepening:
    """Iterative deepening depth-first search."""

    def __init__(self):
        self._found = False
        self._result_node: Optional[SearchNode] = None

    def search(
        self,
        start: State,
        goal: State,
        successors: Callable[[State], List[Tuple[State, str, float]]],
        max_depth: int = 100
    ) -> SearchResult:
        """Perform iterative deepening search."""
        result = SearchResult()

        for depth_limit in range(max_depth):
            self._found = False
            self._result_node = None

            expanded, generated = self._dls(
                SearchNode(state=start),
                goal,
                successors,
                depth_limit
            )

            result.nodes_expanded += expanded
            result.nodes_generated += generated
            result.max_depth = depth_limit

            if self._found:
                result.status = SearchStatus.FOUND
                if self._result_node:
                    result.cost = self._result_node.g_cost
                return result

        result.status = SearchStatus.NOT_FOUND
        return result

    def _dls(
        self,
        node: SearchNode,
        goal: State,
        successors: Callable[[State], List[Tuple[State, str, float]]],
        limit: int
    ) -> Tuple[int, int]:
        """Depth-limited search."""
        if node.state.state_id == goal.state_id:
            self._found = True
            self._result_node = node
            return (0, 0)

        if limit == 0:
            return (0, 0)

        expanded = 1
        generated = 0

        for next_state, action, cost in successors(node.state):
            new_node = SearchNode(
                state=next_state,
                parent_id=node.node_id,
                action=action,
                g_cost=node.g_cost + cost,
                depth=node.depth + 1
            )
            generated += 1

            e, g = self._dls(new_node, goal, successors, limit - 1)
            expanded += e
            generated += g

            if self._found:
                return (expanded, generated)

        return (expanded, generated)


# =============================================================================
# SIMULATED ANNEALING
# =============================================================================

class SimulatedAnnealing:
    """Simulated annealing optimization."""

    def __init__(
        self,
        initial_temp: float = 1000.0,
        cooling_rate: float = 0.995,
        min_temp: float = 0.01
    ):
        self._initial_temp = initial_temp
        self._cooling_rate = cooling_rate
        self._min_temp = min_temp

    def optimize(
        self,
        initial: State,
        energy: Callable[[State], float],
        neighbor: Callable[[State], State],
        max_iterations: int = 10000
    ) -> Tuple[State, float]:
        """Optimize using simulated annealing."""
        current = initial
        current_energy = energy(current)

        best = current
        best_energy = current_energy

        temperature = self._initial_temp

        for _ in range(max_iterations):
            if temperature < self._min_temp:
                break

            # Generate neighbor
            next_state = neighbor(current)
            next_energy = energy(next_state)

            # Calculate acceptance probability
            delta = next_energy - current_energy

            if delta < 0:
                # Better solution - accept
                current = next_state
                current_energy = next_energy

                if current_energy < best_energy:
                    best = current
                    best_energy = current_energy
            else:
                # Worse solution - accept with probability
                prob = math.exp(-delta / temperature)
                if random.random() < prob:
                    current = next_state
                    current_energy = next_energy

            # Cool down
            temperature *= self._cooling_rate

        return best, best_energy


# =============================================================================
# TABU SEARCH
# =============================================================================

class TabuSearch:
    """Tabu search optimization."""

    def __init__(self, tabu_tenure: int = 10):
        self._tenure = tabu_tenure
        self._tabu_list: List[TabuEntry] = []
        self._iteration = 0

    def optimize(
        self,
        initial: State,
        objective: Callable[[State], float],
        neighbors: Callable[[State], List[State]],
        max_iterations: int = 1000
    ) -> Tuple[State, float]:
        """Optimize using tabu search."""
        current = initial
        current_value = objective(current)

        best = current
        best_value = current_value

        for self._iteration in range(max_iterations):
            # Get non-tabu neighbors
            neighbor_list = neighbors(current)
            valid_neighbors = [
                n for n in neighbor_list
                if not self._is_tabu(n)
            ]

            if not valid_neighbors:
                # All neighbors are tabu - use aspiration criterion
                valid_neighbors = neighbor_list

            if not valid_neighbors:
                break

            # Find best neighbor
            best_neighbor = min(valid_neighbors, key=objective)
            best_neighbor_value = objective(best_neighbor)

            # Move to best neighbor
            current = best_neighbor
            current_value = best_neighbor_value

            # Update best if improved
            if current_value < best_value:
                best = current
                best_value = current_value

            # Add to tabu list
            self._add_tabu(current)

            # Expire old tabu entries
            self._expire_tabu()

        return best, best_value

    def _is_tabu(self, state: State) -> bool:
        """Check if state is in tabu list."""
        return any(
            entry.solution == state.data
            for entry in self._tabu_list
        )

    def _add_tabu(self, state: State) -> None:
        """Add state to tabu list."""
        self._tabu_list.append(TabuEntry(
            solution=state.data,
            tenure=self._tenure,
            added_at=self._iteration
        ))

    def _expire_tabu(self) -> None:
        """Remove expired tabu entries."""
        self._tabu_list = [
            entry for entry in self._tabu_list
            if self._iteration - entry.added_at < entry.tenure
        ]


# =============================================================================
# HEURISTIC MANAGER
# =============================================================================

class HeuristicManager:
    """
    Heuristic Manager for BAEL.

    Advanced heuristic search and optimization.
    """

    def __init__(self):
        self._heuristics: Dict[str, HeuristicFunction] = {}
        self._a_star: Optional[AStarSearch] = None
        self._beam: Optional[BeamSearch] = None
        self._ids: Optional[IterativeDeepening] = None
        self._sa: Optional[SimulatedAnnealing] = None
        self._tabu: Optional[TabuSearch] = None

    # -------------------------------------------------------------------------
    # HEURISTIC FUNCTIONS
    # -------------------------------------------------------------------------

    def register_heuristic(
        self,
        name: str,
        function: Callable[[State, State], float],
        heuristic_type: HeuristicType = HeuristicType.ADMISSIBLE
    ) -> HeuristicFunction:
        """Register a heuristic function."""
        hf = HeuristicFunction(
            name=name,
            function=function,
            heuristic_type=heuristic_type
        )
        self._heuristics[name] = hf
        return hf

    def get_heuristic(self, name: str) -> Optional[HeuristicFunction]:
        """Get a heuristic function."""
        return self._heuristics.get(name)

    def list_heuristics(self) -> List[str]:
        """List registered heuristics."""
        return list(self._heuristics.keys())

    # -------------------------------------------------------------------------
    # A* SEARCH
    # -------------------------------------------------------------------------

    def a_star(
        self,
        start: State,
        goal: State,
        successors: Callable[[State], List[Tuple[State, str, float]]],
        heuristic_name: Optional[str] = None,
        max_nodes: int = 10000
    ) -> SearchResult:
        """Perform A* search."""
        hf = HeuristicLibrary.zero_heuristic

        if heuristic_name and heuristic_name in self._heuristics:
            func = self._heuristics[heuristic_name].function
            if func:
                hf = func

        self._a_star = AStarSearch(hf)
        return self._a_star.search(start, goal, successors, max_nodes)

    # -------------------------------------------------------------------------
    # BEAM SEARCH
    # -------------------------------------------------------------------------

    def beam_search(
        self,
        start: State,
        goal: State,
        successors: Callable[[State], List[Tuple[State, str, float]]],
        beam_width: int = 3,
        heuristic_name: Optional[str] = None,
        max_depth: int = 100
    ) -> SearchResult:
        """Perform beam search."""
        hf = HeuristicLibrary.zero_heuristic

        if heuristic_name and heuristic_name in self._heuristics:
            func = self._heuristics[heuristic_name].function
            if func:
                hf = func

        self._beam = BeamSearch(beam_width, hf)
        return self._beam.search(start, goal, successors, max_depth)

    # -------------------------------------------------------------------------
    # ITERATIVE DEEPENING
    # -------------------------------------------------------------------------

    def iterative_deepening(
        self,
        start: State,
        goal: State,
        successors: Callable[[State], List[Tuple[State, str, float]]],
        max_depth: int = 100
    ) -> SearchResult:
        """Perform iterative deepening search."""
        self._ids = IterativeDeepening()
        return self._ids.search(start, goal, successors, max_depth)

    # -------------------------------------------------------------------------
    # SIMULATED ANNEALING
    # -------------------------------------------------------------------------

    def simulated_annealing(
        self,
        initial: State,
        energy: Callable[[State], float],
        neighbor: Callable[[State], State],
        initial_temp: float = 1000.0,
        cooling_rate: float = 0.995,
        max_iterations: int = 10000
    ) -> Tuple[State, float]:
        """Perform simulated annealing optimization."""
        self._sa = SimulatedAnnealing(initial_temp, cooling_rate)
        return self._sa.optimize(initial, energy, neighbor, max_iterations)

    # -------------------------------------------------------------------------
    # TABU SEARCH
    # -------------------------------------------------------------------------

    def tabu_search(
        self,
        initial: State,
        objective: Callable[[State], float],
        neighbors: Callable[[State], List[State]],
        tabu_tenure: int = 10,
        max_iterations: int = 1000
    ) -> Tuple[State, float]:
        """Perform tabu search optimization."""
        self._tabu = TabuSearch(tabu_tenure)
        return self._tabu.optimize(initial, objective, neighbors, max_iterations)

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def create_state(self, data: Any) -> State:
        """Create a search state."""
        return State(data=data)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Heuristic Manager."""
    print("=" * 70)
    print("BAEL - HEURISTIC MANAGER DEMO")
    print("Advanced Heuristic Search and Optimization")
    print("=" * 70)
    print()

    manager = HeuristicManager()

    # 1. Register Heuristics
    print("1. REGISTER HEURISTICS:")
    print("-" * 40)

    manager.register_heuristic(
        "manhattan",
        HeuristicLibrary.manhattan_distance,
        HeuristicType.ADMISSIBLE
    )
    manager.register_heuristic(
        "euclidean",
        HeuristicLibrary.euclidean_distance,
        HeuristicType.ADMISSIBLE
    )

    print(f"   Registered: {manager.list_heuristics()}")
    print()

    # 2. A* Search - Grid Navigation
    print("2. A* SEARCH - GRID NAVIGATION:")
    print("-" * 40)

    start = manager.create_state((0, 0))
    goal = manager.create_state((3, 3))

    def grid_successors(state: State) -> List[Tuple[State, str, float]]:
        x, y = state.data
        moves = []
        for dx, dy, action in [(0, 1, "up"), (0, -1, "down"), (1, 0, "right"), (-1, 0, "left")]:
            nx, ny = x + dx, y + dy
            if 0 <= nx <= 5 and 0 <= ny <= 5:
                new_state = State(data=(nx, ny))
                moves.append((new_state, action, 1.0))
        return moves

    result = manager.a_star(start, goal, grid_successors, "manhattan")
    print(f"   Status: {result.status.value}")
    print(f"   Path: {result.path}")
    print(f"   Cost: {result.cost}")
    print(f"   Nodes expanded: {result.nodes_expanded}")
    print()

    # 3. Beam Search
    print("3. BEAM SEARCH:")
    print("-" * 40)

    result = manager.beam_search(
        start, goal, grid_successors,
        beam_width=3,
        heuristic_name="manhattan"
    )
    print(f"   Status: {result.status.value}")
    print(f"   Nodes expanded: {result.nodes_expanded}")
    print()

    # 4. Iterative Deepening
    print("4. ITERATIVE DEEPENING:")
    print("-" * 40)

    result = manager.iterative_deepening(
        start, goal, grid_successors,
        max_depth=10
    )
    print(f"   Status: {result.status.value}")
    print(f"   Max depth reached: {result.max_depth}")
    print(f"   Nodes expanded: {result.nodes_expanded}")
    print()

    # 5. Simulated Annealing - Function Minimization
    print("5. SIMULATED ANNEALING:")
    print("-" * 40)

    # Minimize f(x) = (x-5)^2
    initial = manager.create_state(0.0)

    def energy(state: State) -> float:
        x = state.data
        return (x - 5) ** 2

    def neighbor(state: State) -> State:
        x = state.data
        return State(data=x + random.uniform(-1, 1))

    best, best_energy = manager.simulated_annealing(
        initial, energy, neighbor,
        initial_temp=100.0,
        max_iterations=1000
    )
    print(f"   Minimizing (x-5)²")
    print(f"   Best x: {best.data:.4f}")
    print(f"   Best energy: {best_energy:.6f}")
    print()

    # 6. Tabu Search
    print("6. TABU SEARCH:")
    print("-" * 40)

    # Minimize sum of squares
    initial = manager.create_state([5, 5, 5])

    def objective(state: State) -> float:
        return sum(x ** 2 for x in state.data)

    def neighbors(state: State) -> List[State]:
        result = []
        for i in range(len(state.data)):
            for delta in [-1, 1]:
                new_data = list(state.data)
                new_data[i] += delta
                result.append(State(data=new_data))
        return result

    best, best_value = manager.tabu_search(
        initial, objective, neighbors,
        tabu_tenure=5,
        max_iterations=100
    )
    print(f"   Minimizing sum(x²)")
    print(f"   Best solution: {best.data}")
    print(f"   Best value: {best_value}")
    print()

    # 7. Compare Heuristics
    print("7. COMPARE HEURISTICS:")
    print("-" * 40)

    start = manager.create_state((0, 0))
    goal = manager.create_state((4, 4))

    for heuristic in ["manhattan", "euclidean"]:
        result = manager.a_star(start, goal, grid_successors, heuristic)
        print(f"   {heuristic}: expanded={result.nodes_expanded}, cost={result.cost}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Heuristic Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
