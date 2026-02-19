"""
BAEL Reality Simulation Engine
==============================

Multi-universe simulation and optimization.

"Ba'el simulates all realities." — Ba'el
"""

import logging
import threading
import random
import math
import copy
import asyncio
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod
import heapq
import time

logger = logging.getLogger("BAEL.RealitySimulation")


T = TypeVar('T')


# ============================================================================
# REALITY STATE
# ============================================================================

@dataclass
class RealityState:
    """
    A state of reality at a point in time.
    """
    id: str
    variables: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0
    energy: float = 1.0  # Probability weight
    parent_id: Optional[str] = None
    branch_point: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def clone(self, new_id: str) -> 'RealityState':
        """Create deep copy with new ID."""
        return RealityState(
            id=new_id,
            variables=copy.deepcopy(self.variables),
            timestamp=self.timestamp,
            energy=self.energy,
            parent_id=self.id,
            branch_point=f"clone_at_{self.timestamp}",
            metadata=copy.deepcopy(self.metadata)
        )

    def get(self, key: str, default: Any = None) -> Any:
        """Get variable value."""
        return self.variables.get(key, default)

    def set(self, key: str, value: Any) -> 'RealityState':
        """Set variable value (returns self for chaining)."""
        self.variables[key] = value
        return self


# ============================================================================
# REALITY BRANCH
# ============================================================================

@dataclass
class RealityBranch:
    """
    A branch in the multiverse tree.
    """
    id: str
    states: List[RealityState]
    probability: float = 1.0
    fitness: float = 0.0
    is_alive: bool = True
    children: List[str] = field(default_factory=list)

    @property
    def current_state(self) -> RealityState:
        return self.states[-1] if self.states else None

    @property
    def timeline_length(self) -> int:
        return len(self.states)


# ============================================================================
# REALITY RULES
# ============================================================================

class RealityRule(ABC):
    """
    A rule that governs reality evolution.
    """

    @abstractmethod
    def apply(self, state: RealityState) -> RealityState:
        """Apply rule to state."""
        pass

    @abstractmethod
    def can_apply(self, state: RealityState) -> bool:
        """Check if rule can apply."""
        pass


class DeterministicRule(RealityRule):
    """
    Deterministic state transition.
    """

    def __init__(
        self,
        name: str,
        condition: Callable[[RealityState], bool],
        transform: Callable[[RealityState], RealityState]
    ):
        self.name = name
        self._condition = condition
        self._transform = transform

    def can_apply(self, state: RealityState) -> bool:
        return self._condition(state)

    def apply(self, state: RealityState) -> RealityState:
        return self._transform(state)


class ProbabilisticRule(RealityRule):
    """
    Probabilistic branching rule.
    """

    def __init__(
        self,
        name: str,
        condition: Callable[[RealityState], bool],
        outcomes: List[Tuple[float, Callable[[RealityState], RealityState]]]
    ):
        """
        Args:
            name: Rule name
            condition: When to apply
            outcomes: List of (probability, transform) pairs
        """
        self.name = name
        self._condition = condition
        self._outcomes = outcomes

    def can_apply(self, state: RealityState) -> bool:
        return self._condition(state)

    def apply(self, state: RealityState) -> RealityState:
        # Sample from distribution
        r = random.random()
        cumulative = 0.0

        for prob, transform in self._outcomes:
            cumulative += prob
            if r <= cumulative:
                new_state = transform(state)
                new_state.energy *= prob
                return new_state

        return state

    def get_all_outcomes(
        self,
        state: RealityState
    ) -> List[Tuple[float, RealityState]]:
        """Get all possible outcomes with probabilities."""
        results = []
        for prob, transform in self._outcomes:
            new_state = transform(state.clone(f"{state.id}_outcome_{len(results)}"))
            new_state.energy *= prob
            results.append((prob, new_state))
        return results


# ============================================================================
# MULTIVERSE SIMULATOR
# ============================================================================

class MultiverseSimulator:
    """
    Simulate multiple parallel realities.

    Features:
    - Branch tracking
    - Probability-weighted sampling
    - Reality merging
    - Timeline analysis

    "Ba'el simulates the multiverse." — Ba'el
    """

    def __init__(self, max_branches: int = 1000):
        """
        Initialize simulator.

        Args:
            max_branches: Maximum active branches
        """
        self._max_branches = max_branches
        self._branches: Dict[str, RealityBranch] = {}
        self._rules: List[RealityRule] = []
        self._fitness_fn: Optional[Callable[[RealityState], float]] = None
        self._next_id = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        """Generate unique ID."""
        self._next_id += 1
        return f"reality_{self._next_id}"

    def add_rule(self, rule: RealityRule) -> 'MultiverseSimulator':
        """Add evolution rule."""
        self._rules.append(rule)
        return self

    def set_fitness_function(
        self,
        fn: Callable[[RealityState], float]
    ) -> 'MultiverseSimulator':
        """Set fitness function for branch selection."""
        self._fitness_fn = fn
        return self

    def create_initial_reality(
        self,
        initial_state: Dict[str, Any]
    ) -> str:
        """Create initial reality and return branch ID."""
        with self._lock:
            state = RealityState(
                id=self._generate_id(),
                variables=initial_state,
                timestamp=0.0
            )

            branch = RealityBranch(
                id=self._generate_id(),
                states=[state],
                probability=1.0
            )

            self._branches[branch.id] = branch
            return branch.id

    def step(self, branch_id: str) -> List[str]:
        """
        Advance a branch by one step.

        Returns new branch IDs (may fork).
        """
        with self._lock:
            if branch_id not in self._branches:
                return []

            branch = self._branches[branch_id]
            if not branch.is_alive:
                return []

            current = branch.current_state
            new_branches = []

            # Find applicable rules
            applicable = [r for r in self._rules if r.can_apply(current)]

            if not applicable:
                # No rules apply, reality persists
                new_state = current.clone(self._generate_id())
                new_state.timestamp += 1.0
                branch.states.append(new_state)
                return [branch_id]

            # Apply first applicable rule
            rule = applicable[0]

            if isinstance(rule, ProbabilisticRule):
                # Create branches for all outcomes
                outcomes = rule.get_all_outcomes(current)

                for prob, new_state in outcomes:
                    new_state.timestamp = current.timestamp + 1.0

                    if len(outcomes) == 1:
                        # Single outcome, continue branch
                        branch.states.append(new_state)
                        branch.probability *= prob
                        new_branches.append(branch_id)
                    else:
                        # Multiple outcomes, create new branches
                        new_branch = RealityBranch(
                            id=self._generate_id(),
                            states=branch.states[:-1] + [new_state],
                            probability=branch.probability * prob
                        )
                        self._branches[new_branch.id] = new_branch
                        branch.children.append(new_branch.id)
                        new_branches.append(new_branch.id)

                if len(outcomes) > 1:
                    branch.is_alive = False
            else:
                # Deterministic rule
                new_state = rule.apply(current.clone(self._generate_id()))
                new_state.timestamp = current.timestamp + 1.0
                branch.states.append(new_state)
                new_branches.append(branch_id)

            # Prune low-probability branches
            self._prune_branches()

            return new_branches

    def _prune_branches(self):
        """Prune branches to stay under limit."""
        if len(self._branches) <= self._max_branches:
            return

        # Sort by probability * fitness
        alive_branches = [
            (bid, b) for bid, b in self._branches.items()
            if b.is_alive
        ]

        if self._fitness_fn:
            alive_branches.sort(
                key=lambda x: x[1].probability * self._fitness_fn(x[1].current_state),
                reverse=True
            )
        else:
            alive_branches.sort(key=lambda x: x[1].probability, reverse=True)

        # Keep top branches
        to_keep = set(bid for bid, _ in alive_branches[:self._max_branches])

        for bid in list(self._branches.keys()):
            if bid not in to_keep:
                self._branches[bid].is_alive = False

    def simulate(
        self,
        steps: int,
        initial_state: Dict[str, Any]
    ) -> List[RealityBranch]:
        """
        Run full simulation.

        Returns all resulting branches.
        """
        with self._lock:
            # Create initial reality
            initial_id = self.create_initial_reality(initial_state)
            active = {initial_id}

            for _ in range(steps):
                new_active = set()
                for branch_id in active:
                    new_ids = self.step(branch_id)
                    new_active.update(new_ids)
                active = new_active

                if not active:
                    break

            return [b for b in self._branches.values() if b.is_alive]

    def get_best_branch(self) -> Optional[RealityBranch]:
        """Get highest probability/fitness branch."""
        alive = [b for b in self._branches.values() if b.is_alive]
        if not alive:
            return None

        if self._fitness_fn:
            return max(
                alive,
                key=lambda b: b.probability * self._fitness_fn(b.current_state)
            )
        return max(alive, key=lambda b: b.probability)

    def get_timeline(self, branch_id: str) -> List[RealityState]:
        """Get full timeline for a branch."""
        if branch_id not in self._branches:
            return []
        return self._branches[branch_id].states

    def merge_similar_branches(
        self,
        similarity_threshold: float = 0.9
    ) -> int:
        """
        Merge similar branches to reduce complexity.

        Returns number of merges.
        """
        with self._lock:
            alive = [b for b in self._branches.values() if b.is_alive]
            merged_count = 0

            for i, b1 in enumerate(alive):
                if not b1.is_alive:
                    continue

                for b2 in alive[i + 1:]:
                    if not b2.is_alive:
                        continue

                    # Check similarity of current states
                    s1 = b1.current_state.variables
                    s2 = b2.current_state.variables

                    if self._states_similar(s1, s2, similarity_threshold):
                        # Merge into higher probability branch
                        if b1.probability >= b2.probability:
                            b1.probability += b2.probability
                            b2.is_alive = False
                        else:
                            b2.probability += b1.probability
                            b1.is_alive = False
                        merged_count += 1

            return merged_count

    def _states_similar(
        self,
        s1: Dict,
        s2: Dict,
        threshold: float
    ) -> bool:
        """Check if two states are similar."""
        keys = set(s1.keys()) | set(s2.keys())
        if not keys:
            return True

        matches = sum(1 for k in keys if s1.get(k) == s2.get(k))
        return matches / len(keys) >= threshold


# ============================================================================
# MONTE CARLO TREE SEARCH (MCTS)
# ============================================================================

@dataclass
class MCTSNode:
    """Node in MCTS tree."""
    state: RealityState
    parent: Optional['MCTSNode'] = None
    children: List['MCTSNode'] = field(default_factory=list)
    visits: int = 0
    value: float = 0.0
    untried_actions: List[Any] = field(default_factory=list)
    action: Any = None  # Action that led to this state


class MonteCarloTreeSearch:
    """
    MCTS for optimal decision making.

    "Ba'el searches optimally." — Ba'el
    """

    def __init__(
        self,
        get_actions: Callable[[RealityState], List[Any]],
        apply_action: Callable[[RealityState, Any], RealityState],
        is_terminal: Callable[[RealityState], bool],
        evaluate: Callable[[RealityState], float],
        exploration_weight: float = 1.414
    ):
        """
        Initialize MCTS.

        Args:
            get_actions: Get available actions from state
            apply_action: Apply action to state
            is_terminal: Check if state is terminal
            evaluate: Evaluate terminal state (0-1)
            exploration_weight: UCB exploration parameter
        """
        self._get_actions = get_actions
        self._apply_action = apply_action
        self._is_terminal = is_terminal
        self._evaluate = evaluate
        self._c = exploration_weight
        self._lock = threading.RLock()

    def search(
        self,
        initial_state: RealityState,
        iterations: int = 1000
    ) -> Any:
        """
        Search for best action.

        Returns best action from initial state.
        """
        with self._lock:
            root = MCTSNode(
                state=initial_state,
                untried_actions=list(self._get_actions(initial_state))
            )

            for _ in range(iterations):
                node = self._select(root)

                if node.untried_actions:
                    node = self._expand(node)

                result = self._simulate(node)
                self._backpropagate(node, result)

            # Return action leading to best child
            if not root.children:
                return None

            best_child = max(root.children, key=lambda c: c.visits)
            return best_child.action

    def _select(self, node: MCTSNode) -> MCTSNode:
        """Select node to expand using UCB1."""
        while not self._is_terminal(node.state) and not node.untried_actions:
            if not node.children:
                return node
            node = self._ucb_select(node)
        return node

    def _ucb_select(self, node: MCTSNode) -> MCTSNode:
        """Select child with highest UCB1 value."""
        log_parent = math.log(node.visits) if node.visits > 0 else 0

        def ucb(child: MCTSNode) -> float:
            if child.visits == 0:
                return float('inf')
            exploit = child.value / child.visits
            explore = self._c * math.sqrt(log_parent / child.visits)
            return exploit + explore

        return max(node.children, key=ucb)

    def _expand(self, node: MCTSNode) -> MCTSNode:
        """Expand node with untried action."""
        action = node.untried_actions.pop()
        new_state = self._apply_action(node.state, action)

        child = MCTSNode(
            state=new_state,
            parent=node,
            untried_actions=list(self._get_actions(new_state)),
            action=action
        )

        node.children.append(child)
        return child

    def _simulate(self, node: MCTSNode) -> float:
        """Random playout from node."""
        state = node.state

        while not self._is_terminal(state):
            actions = self._get_actions(state)
            if not actions:
                break
            action = random.choice(actions)
            state = self._apply_action(state, action)

        return self._evaluate(state)

    def _backpropagate(self, node: MCTSNode, result: float):
        """Backpropagate result up tree."""
        while node:
            node.visits += 1
            node.value += result
            node = node.parent


# ============================================================================
# GENETIC REALITY OPTIMIZER
# ============================================================================

class GeneticRealityOptimizer:
    """
    Optimize reality using genetic algorithms.

    "Ba'el evolves realities." — Ba'el
    """

    def __init__(
        self,
        fitness_fn: Callable[[RealityState], float],
        mutate_fn: Callable[[RealityState], RealityState],
        crossover_fn: Optional[Callable[[RealityState, RealityState], RealityState]] = None,
        population_size: int = 100,
        mutation_rate: float = 0.1,
        elite_fraction: float = 0.1
    ):
        """
        Initialize optimizer.

        Args:
            fitness_fn: Evaluate reality fitness
            mutate_fn: Mutate reality state
            crossover_fn: Combine two realities
            population_size: Number of realities
            mutation_rate: Probability of mutation
            elite_fraction: Fraction of elite to preserve
        """
        self._fitness = fitness_fn
        self._mutate = mutate_fn
        self._crossover = crossover_fn
        self._pop_size = population_size
        self._mutation_rate = mutation_rate
        self._elite_frac = elite_fraction
        self._lock = threading.RLock()

    def optimize(
        self,
        initial_population: List[RealityState],
        generations: int = 100
    ) -> RealityState:
        """
        Run genetic optimization.

        Returns best reality found.
        """
        with self._lock:
            # Initialize population
            population = list(initial_population)
            while len(population) < self._pop_size:
                base = random.choice(initial_population)
                population.append(self._mutate(base))

            for gen in range(generations):
                # Evaluate fitness
                scored = [(self._fitness(r), r) for r in population]
                scored.sort(key=lambda x: x[0], reverse=True)

                # Select elite
                elite_count = int(self._elite_frac * self._pop_size)
                elite = [r for _, r in scored[:elite_count]]

                # Create new population
                new_population = list(elite)

                while len(new_population) < self._pop_size:
                    # Tournament selection
                    p1 = self._tournament_select(scored)
                    p2 = self._tournament_select(scored)

                    # Crossover
                    if self._crossover and random.random() < 0.7:
                        child = self._crossover(p1, p2)
                    else:
                        child = p1.clone(f"gen{gen}_{len(new_population)}")

                    # Mutation
                    if random.random() < self._mutation_rate:
                        child = self._mutate(child)

                    new_population.append(child)

                population = new_population

            # Return best
            best = max(population, key=self._fitness)
            return best

    def _tournament_select(
        self,
        scored: List[Tuple[float, RealityState]],
        tournament_size: int = 3
    ) -> RealityState:
        """Tournament selection."""
        tournament = random.sample(scored, min(tournament_size, len(scored)))
        return max(tournament, key=lambda x: x[0])[1]


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_multiverse_simulator(
    max_branches: int = 1000
) -> MultiverseSimulator:
    """Create multiverse simulator."""
    return MultiverseSimulator(max_branches)


def create_mcts(
    get_actions: Callable,
    apply_action: Callable,
    is_terminal: Callable,
    evaluate: Callable
) -> MonteCarloTreeSearch:
    """Create MCTS instance."""
    return MonteCarloTreeSearch(get_actions, apply_action, is_terminal, evaluate)


def create_genetic_optimizer(
    fitness_fn: Callable[[RealityState], float],
    mutate_fn: Callable[[RealityState], RealityState]
) -> GeneticRealityOptimizer:
    """Create genetic reality optimizer."""
    return GeneticRealityOptimizer(fitness_fn, mutate_fn)
