#!/usr/bin/env python3
"""
BAEL - Strategy Engine
Advanced strategic planning and game-theoretic reasoning.

Features:
- Game theory analysis
- Strategy selection
- Opponent modeling
- Nash equilibrium computation
- Minimax search
- Monte Carlo tree search
- Multi-objective optimization
- Strategic planning
"""

import asyncio
import hashlib
import math
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class GameType(Enum):
    """Types of games."""
    ZERO_SUM = "zero_sum"
    GENERAL_SUM = "general_sum"
    COOPERATIVE = "cooperative"
    SEQUENTIAL = "sequential"
    SIMULTANEOUS = "simultaneous"
    REPEATED = "repeated"


class StrategySelectionMethod(Enum):
    """Strategy selection methods."""
    MAXIMIN = "maximin"
    MAXIMAX = "maximax"
    MINIMAX = "minimax"
    EXPECTED_VALUE = "expected_value"
    REGRET_MINIMIZATION = "regret_minimization"
    NASH_EQUILIBRIUM = "nash_equilibrium"


class OpponentType(Enum):
    """Opponent modeling types."""
    COOPERATIVE = "cooperative"
    COMPETITIVE = "competitive"
    RANDOM = "random"
    ADAPTIVE = "adaptive"
    TRICKSTER = "trickster"


class NodeState(Enum):
    """MCTS node states."""
    UNEXPANDED = "unexpanded"
    EXPANDED = "expanded"
    TERMINAL = "terminal"


class ObjectiveType(Enum):
    """Objective types."""
    MAXIMIZE = "maximize"
    MINIMIZE = "minimize"
    SATISFICE = "satisfice"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Strategy:
    """A strategy."""
    strategy_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    actions: List[str] = field(default_factory=list)
    probabilities: List[float] = field(default_factory=list)
    expected_payoff: float = 0.0
    risk: float = 0.0


@dataclass
class Payoff:
    """Payoff for players."""
    player_payoffs: Dict[str, float] = field(default_factory=dict)

    def get(self, player: str) -> float:
        return self.player_payoffs.get(player, 0.0)


@dataclass
class GameState:
    """State of a game."""
    state_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    players: List[str] = field(default_factory=list)
    current_player: str = ""
    actions_taken: List[Tuple[str, str]] = field(default_factory=list)
    is_terminal: bool = False
    payoffs: Optional[Payoff] = None


@dataclass
class OpponentModel:
    """Model of an opponent."""
    opponent_id: str = ""
    opponent_type: OpponentType = OpponentType.RANDOM
    belief_about_strategy: Dict[str, float] = field(default_factory=dict)
    action_history: List[str] = field(default_factory=list)
    cooperation_rate: float = 0.5
    aggression_level: float = 0.5


@dataclass
class MCTSNode:
    """Monte Carlo Tree Search node."""
    node_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: Any = None
    parent: Optional[str] = None
    children: Dict[str, str] = field(default_factory=dict)  # action -> node_id
    visits: int = 0
    total_value: float = 0.0
    node_state: NodeState = NodeState.UNEXPANDED
    untried_actions: List[str] = field(default_factory=list)


@dataclass
class Objective:
    """Strategic objective."""
    objective_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    objective_type: ObjectiveType = ObjectiveType.MAXIMIZE
    weight: float = 1.0
    target_value: Optional[float] = None
    current_value: float = 0.0


@dataclass
class StrategicPlan:
    """A strategic plan."""
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    objectives: List[Objective] = field(default_factory=list)
    strategies: List[Strategy] = field(default_factory=list)
    selected_strategy: Optional[str] = None
    expected_outcomes: Dict[str, float] = field(default_factory=dict)
    contingencies: Dict[str, str] = field(default_factory=dict)


# =============================================================================
# PAYOFF MATRIX
# =============================================================================

class PayoffMatrix:
    """Payoff matrix for games."""

    def __init__(self, players: List[str]):
        self._players = players
        self._payoffs: Dict[Tuple[str, ...], Payoff] = {}
        self._actions: Dict[str, List[str]] = {p: [] for p in players}

    def set_actions(self, player: str, actions: List[str]) -> None:
        """Set available actions for a player."""
        self._actions[player] = actions

    def get_actions(self, player: str) -> List[str]:
        """Get actions for a player."""
        return self._actions.get(player, [])

    def set_payoff(
        self,
        action_profile: Tuple[str, ...],
        payoffs: Dict[str, float]
    ) -> None:
        """Set payoff for action profile."""
        self._payoffs[action_profile] = Payoff(player_payoffs=payoffs)

    def get_payoff(
        self,
        action_profile: Tuple[str, ...]
    ) -> Optional[Payoff]:
        """Get payoff for action profile."""
        return self._payoffs.get(action_profile)

    def get_player_payoff(
        self,
        player: str,
        action_profile: Tuple[str, ...]
    ) -> float:
        """Get specific player's payoff."""
        payoff = self._payoffs.get(action_profile)
        if payoff:
            return payoff.get(player)
        return 0.0


# =============================================================================
# NASH EQUILIBRIUM SOLVER
# =============================================================================

class NashEquilibriumSolver:
    """Solve for Nash equilibrium."""

    def __init__(self, payoff_matrix: PayoffMatrix):
        self._matrix = payoff_matrix

    def find_pure_nash(self) -> List[Tuple[str, ...]]:
        """Find pure strategy Nash equilibria."""
        players = self._matrix._players

        if len(players) != 2:
            return []  # Only 2-player for now

        equilibria = []

        p1, p2 = players
        actions1 = self._matrix.get_actions(p1)
        actions2 = self._matrix.get_actions(p2)

        for a1 in actions1:
            for a2 in actions2:
                profile = (a1, a2)

                # Check if p1 wants to deviate
                p1_best = True
                current_payoff = self._matrix.get_player_payoff(p1, profile)
                for alt_a1 in actions1:
                    if alt_a1 != a1:
                        alt_payoff = self._matrix.get_player_payoff(p1, (alt_a1, a2))
                        if alt_payoff > current_payoff:
                            p1_best = False
                            break

                # Check if p2 wants to deviate
                p2_best = True
                current_payoff = self._matrix.get_player_payoff(p2, profile)
                for alt_a2 in actions2:
                    if alt_a2 != a2:
                        alt_payoff = self._matrix.get_player_payoff(p2, (a1, alt_a2))
                        if alt_payoff > current_payoff:
                            p2_best = False
                            break

                if p1_best and p2_best:
                    equilibria.append(profile)

        return equilibria

    def find_mixed_nash_2x2(self) -> Optional[Dict[str, Dict[str, float]]]:
        """Find mixed Nash equilibrium for 2x2 games."""
        players = self._matrix._players

        if len(players) != 2:
            return None

        p1, p2 = players
        actions1 = self._matrix.get_actions(p1)
        actions2 = self._matrix.get_actions(p2)

        if len(actions1) != 2 or len(actions2) != 2:
            return None

        # Get payoffs
        a1, b1 = actions1
        a2, b2 = actions2

        # Player 1's payoffs
        u11 = self._matrix.get_player_payoff(p1, (a1, a2))
        u12 = self._matrix.get_player_payoff(p1, (a1, b2))
        u21 = self._matrix.get_player_payoff(p1, (b1, a2))
        u22 = self._matrix.get_player_payoff(p1, (b1, b2))

        # Player 2's payoffs
        v11 = self._matrix.get_player_payoff(p2, (a1, a2))
        v12 = self._matrix.get_player_payoff(p2, (a1, b2))
        v21 = self._matrix.get_player_payoff(p2, (b1, a2))
        v22 = self._matrix.get_player_payoff(p2, (b1, b2))

        # Solve for mixed strategies
        # p2 must make p1 indifferent
        denom1 = (u11 - u12 - u21 + u22)
        if abs(denom1) < 1e-10:
            q = 0.5
        else:
            q = (u22 - u12) / denom1

        # p1 must make p2 indifferent
        denom2 = (v11 - v12 - v21 + v22)
        if abs(denom2) < 1e-10:
            p = 0.5
        else:
            p = (v22 - v21) / denom2

        # Clamp to [0, 1]
        p = max(0.0, min(1.0, p))
        q = max(0.0, min(1.0, q))

        return {
            p1: {a1: p, b1: 1 - p},
            p2: {a2: q, b2: 1 - q}
        }


# =============================================================================
# MINIMAX SOLVER
# =============================================================================

class MinimaxSolver:
    """Minimax search for sequential games."""

    def __init__(
        self,
        get_actions: Callable[[Any], List[str]],
        apply_action: Callable[[Any, str], Any],
        is_terminal: Callable[[Any], bool],
        evaluate: Callable[[Any], float],
        get_player: Callable[[Any], str],
        maximizing_player: str
    ):
        self._get_actions = get_actions
        self._apply_action = apply_action
        self._is_terminal = is_terminal
        self._evaluate = evaluate
        self._get_player = get_player
        self._maximizing_player = maximizing_player
        self._nodes_explored = 0

    def minimax(
        self,
        state: Any,
        depth: int,
        alpha: float = float('-inf'),
        beta: float = float('inf')
    ) -> Tuple[float, Optional[str]]:
        """Minimax with alpha-beta pruning."""
        self._nodes_explored += 1

        if depth == 0 or self._is_terminal(state):
            return self._evaluate(state), None

        actions = self._get_actions(state)
        current_player = self._get_player(state)
        is_maximizing = current_player == self._maximizing_player

        best_action = None

        if is_maximizing:
            value = float('-inf')
            for action in actions:
                new_state = self._apply_action(state, action)
                child_value, _ = self.minimax(new_state, depth - 1, alpha, beta)

                if child_value > value:
                    value = child_value
                    best_action = action

                alpha = max(alpha, value)
                if beta <= alpha:
                    break

            return value, best_action
        else:
            value = float('inf')
            for action in actions:
                new_state = self._apply_action(state, action)
                child_value, _ = self.minimax(new_state, depth - 1, alpha, beta)

                if child_value < value:
                    value = child_value
                    best_action = action

                beta = min(beta, value)
                if beta <= alpha:
                    break

            return value, best_action

    def get_nodes_explored(self) -> int:
        """Get number of nodes explored."""
        return self._nodes_explored


# =============================================================================
# MONTE CARLO TREE SEARCH
# =============================================================================

class MCTS:
    """Monte Carlo Tree Search."""

    def __init__(
        self,
        get_actions: Callable[[Any], List[str]],
        apply_action: Callable[[Any, str], Any],
        is_terminal: Callable[[Any], bool],
        get_reward: Callable[[Any], float],
        exploration_constant: float = 1.41
    ):
        self._get_actions = get_actions
        self._apply_action = apply_action
        self._is_terminal = is_terminal
        self._get_reward = get_reward
        self._c = exploration_constant
        self._nodes: Dict[str, MCTSNode] = {}

    def search(
        self,
        root_state: Any,
        iterations: int = 1000
    ) -> str:
        """Run MCTS and return best action."""
        # Create root node
        root = MCTSNode(
            state=root_state,
            untried_actions=self._get_actions(root_state)
        )
        self._nodes[root.node_id] = root

        for _ in range(iterations):
            node = root
            state = root_state

            # Selection
            while node.untried_actions == [] and node.children:
                node = self._select_child(node)
                state = node.state

            # Expansion
            if node.untried_actions:
                action = random.choice(node.untried_actions)
                node.untried_actions.remove(action)
                state = self._apply_action(state, action)

                child = MCTSNode(
                    state=state,
                    parent=node.node_id,
                    untried_actions=self._get_actions(state) if not self._is_terminal(state) else []
                )
                self._nodes[child.node_id] = child
                node.children[action] = child.node_id
                node = child

            # Simulation
            sim_state = state
            while not self._is_terminal(sim_state):
                actions = self._get_actions(sim_state)
                if not actions:
                    break
                action = random.choice(actions)
                sim_state = self._apply_action(sim_state, action)

            reward = self._get_reward(sim_state)

            # Backpropagation
            while node:
                node.visits += 1
                node.total_value += reward
                if node.parent:
                    node = self._nodes.get(node.parent)
                else:
                    node = None

        # Return best action
        return self._best_action(root)

    def _select_child(self, node: MCTSNode) -> MCTSNode:
        """Select child using UCB1."""
        best_score = float('-inf')
        best_child = None

        for action, child_id in node.children.items():
            child = self._nodes.get(child_id)
            if child:
                exploitation = child.total_value / child.visits if child.visits > 0 else 0
                exploration = self._c * math.sqrt(
                    math.log(node.visits) / child.visits
                ) if child.visits > 0 else float('inf')
                score = exploitation + exploration

                if score > best_score:
                    best_score = score
                    best_child = child

        return best_child or node

    def _best_action(self, node: MCTSNode) -> str:
        """Get best action from root."""
        best_visits = -1
        best_action = ""

        for action, child_id in node.children.items():
            child = self._nodes.get(child_id)
            if child and child.visits > best_visits:
                best_visits = child.visits
                best_action = action

        return best_action


# =============================================================================
# OPPONENT MODELER
# =============================================================================

class OpponentModeler:
    """Model opponent behavior."""

    def __init__(self):
        self._models: Dict[str, OpponentModel] = {}

    def create_model(
        self,
        opponent_id: str,
        initial_type: OpponentType = OpponentType.RANDOM
    ) -> OpponentModel:
        """Create opponent model."""
        model = OpponentModel(
            opponent_id=opponent_id,
            opponent_type=initial_type
        )
        self._models[opponent_id] = model
        return model

    def get_model(self, opponent_id: str) -> Optional[OpponentModel]:
        """Get opponent model."""
        return self._models.get(opponent_id)

    def update_model(
        self,
        opponent_id: str,
        action: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update model based on observed action."""
        model = self._models.get(opponent_id)
        if not model:
            return

        model.action_history.append(action)

        # Update strategy beliefs
        if action not in model.belief_about_strategy:
            model.belief_about_strategy[action] = 0.0

        # Frequency-based update
        total = len(model.action_history)
        for act in set(model.action_history):
            count = model.action_history.count(act)
            model.belief_about_strategy[act] = count / total

        # Update cooperation/aggression estimates
        if context:
            if context.get("is_cooperative"):
                model.cooperation_rate = model.cooperation_rate * 0.9 + 0.1
            else:
                model.cooperation_rate = model.cooperation_rate * 0.9

            if context.get("is_aggressive"):
                model.aggression_level = model.aggression_level * 0.9 + 0.1
            else:
                model.aggression_level = model.aggression_level * 0.9

    def predict_action(
        self,
        opponent_id: str,
        available_actions: List[str]
    ) -> Dict[str, float]:
        """Predict opponent's action distribution."""
        model = self._models.get(opponent_id)

        if not model or not model.belief_about_strategy:
            # Uniform distribution
            return {a: 1.0 / len(available_actions) for a in available_actions}

        # Use beliefs
        total = sum(
            model.belief_about_strategy.get(a, 0.0)
            for a in available_actions
        )

        if total == 0:
            return {a: 1.0 / len(available_actions) for a in available_actions}

        return {
            a: model.belief_about_strategy.get(a, 0.0) / total
            for a in available_actions
        }

    def classify_opponent(self, opponent_id: str) -> OpponentType:
        """Classify opponent type based on history."""
        model = self._models.get(opponent_id)
        if not model:
            return OpponentType.RANDOM

        if model.cooperation_rate > 0.7:
            return OpponentType.COOPERATIVE
        elif model.aggression_level > 0.7:
            return OpponentType.COMPETITIVE
        elif len(set(model.action_history)) > len(model.action_history) * 0.8:
            return OpponentType.RANDOM
        else:
            return OpponentType.ADAPTIVE


# =============================================================================
# MULTI-OBJECTIVE OPTIMIZER
# =============================================================================

class MultiObjectiveOptimizer:
    """Multi-objective optimization."""

    def __init__(self):
        self._objectives: List[Objective] = []

    def add_objective(
        self,
        name: str,
        objective_type: ObjectiveType,
        weight: float = 1.0,
        target_value: Optional[float] = None
    ) -> Objective:
        """Add an objective."""
        objective = Objective(
            name=name,
            objective_type=objective_type,
            weight=weight,
            target_value=target_value
        )
        self._objectives.append(objective)
        return objective

    def evaluate_solution(
        self,
        values: Dict[str, float]
    ) -> float:
        """Evaluate a solution against all objectives."""
        total_score = 0.0
        total_weight = sum(o.weight for o in self._objectives)

        for obj in self._objectives:
            value = values.get(obj.name, 0.0)
            obj.current_value = value

            if obj.objective_type == ObjectiveType.MAXIMIZE:
                score = value
            elif obj.objective_type == ObjectiveType.MINIMIZE:
                score = -value
            else:  # SATISFICE
                if obj.target_value is not None:
                    if value >= obj.target_value:
                        score = 1.0
                    else:
                        score = value / obj.target_value
                else:
                    score = value

            total_score += score * obj.weight

        return total_score / total_weight if total_weight > 0 else 0.0

    def is_pareto_dominated(
        self,
        solution1: Dict[str, float],
        solution2: Dict[str, float]
    ) -> bool:
        """Check if solution1 is Pareto dominated by solution2."""
        at_least_one_better = False

        for obj in self._objectives:
            v1 = solution1.get(obj.name, 0.0)
            v2 = solution2.get(obj.name, 0.0)

            if obj.objective_type == ObjectiveType.MAXIMIZE:
                if v2 < v1:
                    return False
                if v2 > v1:
                    at_least_one_better = True
            elif obj.objective_type == ObjectiveType.MINIMIZE:
                if v2 > v1:
                    return False
                if v2 < v1:
                    at_least_one_better = True

        return at_least_one_better

    def find_pareto_front(
        self,
        solutions: List[Dict[str, float]]
    ) -> List[Dict[str, float]]:
        """Find Pareto-optimal solutions."""
        pareto = []

        for sol in solutions:
            is_dominated = False
            for other in solutions:
                if sol != other and self.is_pareto_dominated(sol, other):
                    is_dominated = True
                    break

            if not is_dominated:
                pareto.append(sol)

        return pareto


# =============================================================================
# STRATEGY ENGINE
# =============================================================================

class StrategyEngine:
    """
    Strategy Engine for BAEL.

    Advanced strategic planning and game-theoretic reasoning.
    """

    def __init__(self):
        self._payoff_matrices: Dict[str, PayoffMatrix] = {}
        self._opponent_modeler = OpponentModeler()
        self._multi_objective = MultiObjectiveOptimizer()
        self._plans: Dict[str, StrategicPlan] = {}
        self._strategies: Dict[str, Strategy] = {}

    # -------------------------------------------------------------------------
    # GAME SETUP
    # -------------------------------------------------------------------------

    def create_game(
        self,
        game_id: str,
        players: List[str]
    ) -> PayoffMatrix:
        """Create a new game."""
        matrix = PayoffMatrix(players)
        self._payoff_matrices[game_id] = matrix
        return matrix

    def get_game(self, game_id: str) -> Optional[PayoffMatrix]:
        """Get a game's payoff matrix."""
        return self._payoff_matrices.get(game_id)

    def set_game_payoffs(
        self,
        game_id: str,
        player: str,
        actions: List[str],
        payoffs: Dict[Tuple[str, ...], Dict[str, float]]
    ) -> None:
        """Set payoffs for a game."""
        matrix = self._payoff_matrices.get(game_id)
        if matrix:
            matrix.set_actions(player, actions)
            for profile, payoff_dict in payoffs.items():
                matrix.set_payoff(profile, payoff_dict)

    # -------------------------------------------------------------------------
    # NASH EQUILIBRIUM
    # -------------------------------------------------------------------------

    def find_nash_equilibria(
        self,
        game_id: str
    ) -> List[Tuple[str, ...]]:
        """Find Nash equilibria for a game."""
        matrix = self._payoff_matrices.get(game_id)
        if not matrix:
            return []

        solver = NashEquilibriumSolver(matrix)
        return solver.find_pure_nash()

    def find_mixed_nash(
        self,
        game_id: str
    ) -> Optional[Dict[str, Dict[str, float]]]:
        """Find mixed Nash equilibrium."""
        matrix = self._payoff_matrices.get(game_id)
        if not matrix:
            return None

        solver = NashEquilibriumSolver(matrix)
        return solver.find_mixed_nash_2x2()

    # -------------------------------------------------------------------------
    # MINIMAX
    # -------------------------------------------------------------------------

    def minimax_search(
        self,
        state: Any,
        depth: int,
        get_actions: Callable,
        apply_action: Callable,
        is_terminal: Callable,
        evaluate: Callable,
        get_player: Callable,
        maximizing_player: str
    ) -> Tuple[float, Optional[str]]:
        """Run minimax search."""
        solver = MinimaxSolver(
            get_actions,
            apply_action,
            is_terminal,
            evaluate,
            get_player,
            maximizing_player
        )
        return solver.minimax(state, depth)

    # -------------------------------------------------------------------------
    # MCTS
    # -------------------------------------------------------------------------

    def mcts_search(
        self,
        state: Any,
        iterations: int,
        get_actions: Callable,
        apply_action: Callable,
        is_terminal: Callable,
        get_reward: Callable
    ) -> str:
        """Run MCTS and get best action."""
        mcts = MCTS(
            get_actions,
            apply_action,
            is_terminal,
            get_reward
        )
        return mcts.search(state, iterations)

    # -------------------------------------------------------------------------
    # OPPONENT MODELING
    # -------------------------------------------------------------------------

    def create_opponent_model(
        self,
        opponent_id: str,
        initial_type: OpponentType = OpponentType.RANDOM
    ) -> OpponentModel:
        """Create opponent model."""
        return self._opponent_modeler.create_model(opponent_id, initial_type)

    def update_opponent_model(
        self,
        opponent_id: str,
        action: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update opponent model."""
        self._opponent_modeler.update_model(opponent_id, action, context)

    def predict_opponent_action(
        self,
        opponent_id: str,
        available_actions: List[str]
    ) -> Dict[str, float]:
        """Predict opponent action distribution."""
        return self._opponent_modeler.predict_action(opponent_id, available_actions)

    def classify_opponent(self, opponent_id: str) -> OpponentType:
        """Classify opponent type."""
        return self._opponent_modeler.classify_opponent(opponent_id)

    # -------------------------------------------------------------------------
    # MULTI-OBJECTIVE
    # -------------------------------------------------------------------------

    def add_objective(
        self,
        name: str,
        objective_type: ObjectiveType,
        weight: float = 1.0,
        target_value: Optional[float] = None
    ) -> Objective:
        """Add strategic objective."""
        return self._multi_objective.add_objective(
            name, objective_type, weight, target_value
        )

    def evaluate_strategy(
        self,
        values: Dict[str, float]
    ) -> float:
        """Evaluate strategy against objectives."""
        return self._multi_objective.evaluate_solution(values)

    def find_pareto_optimal(
        self,
        solutions: List[Dict[str, float]]
    ) -> List[Dict[str, float]]:
        """Find Pareto-optimal solutions."""
        return self._multi_objective.find_pareto_front(solutions)

    # -------------------------------------------------------------------------
    # STRATEGY MANAGEMENT
    # -------------------------------------------------------------------------

    def create_strategy(
        self,
        name: str,
        description: str = "",
        actions: Optional[List[str]] = None,
        probabilities: Optional[List[float]] = None
    ) -> Strategy:
        """Create a strategy."""
        strategy = Strategy(
            name=name,
            description=description,
            actions=actions or [],
            probabilities=probabilities or []
        )
        self._strategies[strategy.strategy_id] = strategy
        return strategy

    def get_strategy(self, strategy_id: str) -> Optional[Strategy]:
        """Get strategy by ID."""
        return self._strategies.get(strategy_id)

    def select_action_from_strategy(
        self,
        strategy: Strategy
    ) -> str:
        """Select action based on strategy probabilities."""
        if not strategy.actions:
            return ""

        if not strategy.probabilities:
            return random.choice(strategy.actions)

        r = random.random()
        cumulative = 0.0

        for action, prob in zip(strategy.actions, strategy.probabilities):
            cumulative += prob
            if r <= cumulative:
                return action

        return strategy.actions[-1]

    # -------------------------------------------------------------------------
    # STRATEGIC PLANNING
    # -------------------------------------------------------------------------

    def create_plan(
        self,
        objectives: List[Objective],
        strategies: List[Strategy]
    ) -> StrategicPlan:
        """Create a strategic plan."""
        plan = StrategicPlan(
            objectives=objectives,
            strategies=strategies
        )
        self._plans[plan.plan_id] = plan
        return plan

    def select_best_strategy(
        self,
        plan: StrategicPlan,
        evaluation_function: Callable[[Strategy], float]
    ) -> Optional[Strategy]:
        """Select best strategy for plan."""
        if not plan.strategies:
            return None

        best_strategy = max(
            plan.strategies,
            key=evaluation_function
        )

        plan.selected_strategy = best_strategy.strategy_id
        return best_strategy

    def add_contingency(
        self,
        plan_id: str,
        trigger: str,
        response_strategy_id: str
    ) -> None:
        """Add contingency to plan."""
        plan = self._plans.get(plan_id)
        if plan:
            plan.contingencies[trigger] = response_strategy_id


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Strategy Engine."""
    print("=" * 70)
    print("BAEL - STRATEGY ENGINE DEMO")
    print("Advanced Strategic Planning and Game-Theoretic Reasoning")
    print("=" * 70)
    print()

    engine = StrategyEngine()

    # 1. Create Prisoner's Dilemma Game
    print("1. PRISONER'S DILEMMA GAME:")
    print("-" * 40)

    matrix = engine.create_game("prisoners_dilemma", ["Player1", "Player2"])
    matrix.set_actions("Player1", ["Cooperate", "Defect"])
    matrix.set_actions("Player2", ["Cooperate", "Defect"])

    # Set payoffs
    matrix.set_payoff(("Cooperate", "Cooperate"), {"Player1": 3, "Player2": 3})
    matrix.set_payoff(("Cooperate", "Defect"), {"Player1": 0, "Player2": 5})
    matrix.set_payoff(("Defect", "Cooperate"), {"Player1": 5, "Player2": 0})
    matrix.set_payoff(("Defect", "Defect"), {"Player1": 1, "Player2": 1})

    print("   Payoff Matrix:")
    print("                    Player2: Cooperate  Defect")
    print("   Player1: Cooperate     (3,3)         (0,5)")
    print("   Player1: Defect        (5,0)         (1,1)")
    print()

    # 2. Find Nash Equilibrium
    print("2. NASH EQUILIBRIUM:")
    print("-" * 40)

    nash = engine.find_nash_equilibria("prisoners_dilemma")
    print(f"   Pure Nash equilibria: {nash}")

    mixed = engine.find_mixed_nash("prisoners_dilemma")
    if mixed:
        print("   Mixed Nash equilibrium:")
        for player, probs in mixed.items():
            print(f"     {player}: {probs}")
    print()

    # 3. Opponent Modeling
    print("3. OPPONENT MODELING:")
    print("-" * 40)

    engine.create_opponent_model("OpponentA", OpponentType.RANDOM)

    # Simulate opponent history
    for _ in range(10):
        action = random.choice(["Cooperate", "Cooperate", "Defect"])
        engine.update_opponent_model("OpponentA", action, {"is_cooperative": action == "Cooperate"})

    prediction = engine.predict_opponent_action("OpponentA", ["Cooperate", "Defect"])
    opp_type = engine.classify_opponent("OpponentA")

    print(f"   Opponent type: {opp_type.value}")
    print(f"   Predicted actions: {prediction}")
    print()

    # 4. Create Strategies
    print("4. CREATE STRATEGIES:")
    print("-" * 40)

    s1 = engine.create_strategy(
        "Tit-for-Tat",
        "Cooperate first, then mirror opponent",
        ["Cooperate", "Mirror"],
        [0.5, 0.5]
    )

    s2 = engine.create_strategy(
        "Always Defect",
        "Always defect",
        ["Defect"],
        [1.0]
    )

    s3 = engine.create_strategy(
        "Random",
        "Random 50/50",
        ["Cooperate", "Defect"],
        [0.5, 0.5]
    )

    print(f"   Created strategies: Tit-for-Tat, Always Defect, Random")
    print()

    # 5. Multi-Objective Optimization
    print("5. MULTI-OBJECTIVE OPTIMIZATION:")
    print("-" * 40)

    engine.add_objective("profit", ObjectiveType.MAXIMIZE, weight=0.6)
    engine.add_objective("risk", ObjectiveType.MINIMIZE, weight=0.3)
    engine.add_objective("reputation", ObjectiveType.MAXIMIZE, weight=0.1)

    solutions = [
        {"profit": 100, "risk": 30, "reputation": 0.8},
        {"profit": 80, "risk": 10, "reputation": 0.9},
        {"profit": 120, "risk": 50, "reputation": 0.6},
        {"profit": 90, "risk": 20, "reputation": 0.85},
    ]

    for i, sol in enumerate(solutions):
        score = engine.evaluate_strategy(sol)
        print(f"   Solution {i+1}: score={score:.2f}")

    pareto = engine.find_pareto_optimal(solutions)
    print(f"   Pareto optimal: {len(pareto)} solutions")
    print()

    # 6. Strategic Planning
    print("6. STRATEGIC PLANNING:")
    print("-" * 40)

    plan = engine.create_plan(
        objectives=[],
        strategies=[s1, s2, s3]
    )

    # Select best strategy
    def evaluate(s: Strategy) -> float:
        return len(s.actions) * 0.3 + (1 if "Cooperate" in s.actions else 0) * 0.7

    best = engine.select_best_strategy(plan, evaluate)
    print(f"   Selected strategy: {best.name if best else 'None'}")

    # Add contingency
    engine.add_contingency(plan.plan_id, "opponent_defects", s2.strategy_id)
    print(f"   Contingencies: {plan.contingencies}")
    print()

    # 7. Action Selection
    print("7. ACTION SELECTION:")
    print("-" * 40)

    for strategy in [s1, s2, s3]:
        action = engine.select_action_from_strategy(strategy)
        print(f"   {strategy.name}: selected '{action}'")
    print()

    # 8. Simple MCTS Demo
    print("8. MCTS DEMO (Simplified):")
    print("-" * 40)

    # Simple game state
    class SimpleState:
        def __init__(self, value=0, depth=0):
            self.value = value
            self.depth = depth

    def get_actions(state):
        if state.depth >= 3:
            return []
        return ["A", "B"]

    def apply_action(state, action):
        new_value = state.value + (1 if action == "A" else -1)
        return SimpleState(new_value, state.depth + 1)

    def is_terminal(state):
        return state.depth >= 3

    def get_reward(state):
        return state.value

    best_action = engine.mcts_search(
        SimpleState(),
        iterations=100,
        get_actions=get_actions,
        apply_action=apply_action,
        is_terminal=is_terminal,
        get_reward=get_reward
    )

    print(f"   MCTS recommended action: {best_action}")
    print()

    # 9. Minimax Demo
    print("9. MINIMAX DEMO:")
    print("-" * 40)

    def get_player(state):
        return "max" if state.depth % 2 == 0 else "min"

    def evaluate_state(state):
        return state.value

    value, action = engine.minimax_search(
        state=SimpleState(),
        depth=3,
        get_actions=get_actions,
        apply_action=apply_action,
        is_terminal=is_terminal,
        evaluate=evaluate_state,
        get_player=get_player,
        maximizing_player="max"
    )

    print(f"   Minimax value: {value}")
    print(f"   Minimax action: {action}")
    print()

    # 10. Game Theory Analysis
    print("10. GAME THEORY SUMMARY:")
    print("-" * 40)

    game = engine.get_game("prisoners_dilemma")
    if game:
        print(f"   Players: {game._players}")
        print(f"   P1 actions: {game.get_actions('Player1')}")
        print(f"   P2 actions: {game.get_actions('Player2')}")

        # Show some payoffs
        for profile in [("Cooperate", "Cooperate"), ("Defect", "Defect")]:
            p1_payoff = game.get_player_payoff("Player1", profile)
            p2_payoff = game.get_player_payoff("Player2", profile)
            print(f"   {profile}: P1={p1_payoff}, P2={p2_payoff}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Strategy Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
