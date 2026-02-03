#!/usr/bin/env python3
"""
BAEL - Game Theory Engine
Advanced strategic and game-theoretic reasoning.

Features:
- Normal form games
- Extensive form games
- Nash equilibrium
- Dominant strategies
- Pareto optimality
- Mechanism design
"""

import asyncio
import copy
import hashlib
import itertools
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


# =============================================================================
# ENUMS
# =============================================================================

class GameType(Enum):
    """Types of games."""
    NORMAL_FORM = "normal_form"
    EXTENSIVE_FORM = "extensive_form"
    REPEATED = "repeated"
    COOPERATIVE = "cooperative"
    BAYESIAN = "bayesian"


class EquilibriumType(Enum):
    """Types of equilibria."""
    NASH = "nash"
    DOMINANT_STRATEGY = "dominant_strategy"
    SUBGAME_PERFECT = "subgame_perfect"
    CORRELATED = "correlated"


class StrategyType(Enum):
    """Types of strategies."""
    PURE = "pure"
    MIXED = "mixed"
    BEHAVIORAL = "behavioral"


class Dominance(Enum):
    """Types of dominance."""
    STRICTLY_DOMINANT = "strictly_dominant"
    WEAKLY_DOMINANT = "weakly_dominant"
    STRICTLY_DOMINATED = "strictly_dominated"
    WEAKLY_DOMINATED = "weakly_dominated"
    NONE = "none"


class SolutionConcept(Enum):
    """Solution concepts."""
    NASH_EQUILIBRIUM = "nash_equilibrium"
    DOMINANT_STRATEGY = "dominant_strategy"
    MINIMAX = "minimax"
    MAXIMIN = "maximin"
    PARETO_OPTIMAL = "pareto_optimal"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Player:
    """A game player."""
    player_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    strategies: List[str] = field(default_factory=list)


@dataclass
class Strategy:
    """A strategy in the game."""
    strategy_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    player_id: str = ""
    name: str = ""
    strategy_type: StrategyType = StrategyType.PURE
    probabilities: Dict[str, float] = field(default_factory=dict)  # For mixed


@dataclass
class Payoff:
    """A payoff for a strategy profile."""
    profile: Tuple[str, ...] = field(default_factory=tuple)  # Strategy IDs
    payoffs: Dict[str, float] = field(default_factory=dict)  # Player ID -> payoff


@dataclass
class GameNode:
    """A node in extensive form game."""
    node_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    player_id: str = ""  # Empty for terminal nodes
    children: Dict[str, str] = field(default_factory=dict)  # Action -> child node ID
    payoffs: Optional[Dict[str, float]] = None  # For terminal nodes
    information_set: str = ""


@dataclass
class NormalFormGame:
    """A normal (strategic) form game."""
    game_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    players: List[str] = field(default_factory=list)
    payoff_matrix: Dict[Tuple, Dict[str, float]] = field(default_factory=dict)


@dataclass
class Equilibrium:
    """An equilibrium of the game."""
    eq_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    eq_type: EquilibriumType = EquilibriumType.NASH
    strategy_profile: Dict[str, str] = field(default_factory=dict)
    payoffs: Dict[str, float] = field(default_factory=dict)


# =============================================================================
# PLAYER MANAGER
# =============================================================================

class PlayerManager:
    """Manage game players."""

    def __init__(self):
        self._players: Dict[str, Player] = {}
        self._strategies: Dict[str, Strategy] = {}

    def create_player(
        self,
        name: str,
        strategies: Optional[List[str]] = None
    ) -> Player:
        """Create a player."""
        player = Player(name=name, strategies=strategies or [])
        self._players[player.player_id] = player
        return player

    def add_strategy(
        self,
        player_id: str,
        name: str,
        strategy_type: StrategyType = StrategyType.PURE,
        probabilities: Optional[Dict[str, float]] = None
    ) -> Optional[Strategy]:
        """Add a strategy to a player."""
        player = self._players.get(player_id)
        if not player:
            return None

        strategy = Strategy(
            player_id=player_id,
            name=name,
            strategy_type=strategy_type,
            probabilities=probabilities or {}
        )

        self._strategies[strategy.strategy_id] = strategy
        player.strategies.append(strategy.strategy_id)

        return strategy

    def get_player(self, player_id: str) -> Optional[Player]:
        """Get a player."""
        return self._players.get(player_id)

    def get_strategy(self, strategy_id: str) -> Optional[Strategy]:
        """Get a strategy."""
        return self._strategies.get(strategy_id)

    def get_player_strategies(self, player_id: str) -> List[Strategy]:
        """Get all strategies of a player."""
        player = self._players.get(player_id)
        if not player:
            return []
        return [
            self._strategies[sid]
            for sid in player.strategies
            if sid in self._strategies
        ]


# =============================================================================
# NORMAL FORM GAME BUILDER
# =============================================================================

class NormalFormGameBuilder:
    """Build normal form games."""

    def __init__(self, player_manager: PlayerManager):
        self._players = player_manager
        self._games: Dict[str, NormalFormGame] = {}

    def create_game(
        self,
        name: str,
        player_ids: List[str]
    ) -> NormalFormGame:
        """Create a normal form game."""
        game = NormalFormGame(
            name=name,
            players=player_ids
        )
        self._games[game.game_id] = game
        return game

    def set_payoff(
        self,
        game_id: str,
        strategy_profile: Tuple[str, ...],
        payoffs: Dict[str, float]
    ) -> bool:
        """Set payoff for a strategy profile."""
        game = self._games.get(game_id)
        if not game:
            return False

        game.payoff_matrix[strategy_profile] = payoffs
        return True

    def get_payoff(
        self,
        game_id: str,
        strategy_profile: Tuple[str, ...]
    ) -> Optional[Dict[str, float]]:
        """Get payoff for a strategy profile."""
        game = self._games.get(game_id)
        if not game:
            return None
        return game.payoff_matrix.get(strategy_profile)

    def get_game(self, game_id: str) -> Optional[NormalFormGame]:
        """Get a game."""
        return self._games.get(game_id)

    def all_strategy_profiles(
        self,
        game_id: str
    ) -> List[Tuple[str, ...]]:
        """Get all possible strategy profiles."""
        game = self._games.get(game_id)
        if not game:
            return []

        strategies_per_player = []
        for player_id in game.players:
            strategies = self._players.get_player_strategies(player_id)
            strategies_per_player.append([s.strategy_id for s in strategies])

        return list(itertools.product(*strategies_per_player))


# =============================================================================
# DOMINANCE ANALYZER
# =============================================================================

class DominanceAnalyzer:
    """Analyze strategy dominance."""

    def __init__(
        self,
        game_builder: NormalFormGameBuilder,
        player_manager: PlayerManager
    ):
        self._games = game_builder
        self._players = player_manager

    def check_dominance(
        self,
        game_id: str,
        player_id: str,
        strategy_id: str
    ) -> Dominance:
        """Check dominance of a strategy."""
        game = self._games.get_game(game_id)
        if not game:
            return Dominance.NONE

        player_strategies = self._players.get_player_strategies(player_id)
        strategy_ids = [s.strategy_id for s in player_strategies]

        if strategy_id not in strategy_ids:
            return Dominance.NONE

        other_strategies = [s for s in strategy_ids if s != strategy_id]

        # Check if strictly dominant
        is_strictly_dominant = True
        is_weakly_dominant = True
        is_strictly_dominated = True
        is_weakly_dominated = True

        all_profiles = self._games.all_strategy_profiles(game_id)
        player_idx = game.players.index(player_id)

        for other_strat in other_strategies:
            for profile in all_profiles:
                if profile[player_idx] not in (strategy_id, other_strat):
                    continue

                # Create profiles for comparison
                profile1 = list(profile)
                profile1[player_idx] = strategy_id
                profile2 = list(profile)
                profile2[player_idx] = other_strat

                payoff1 = self._games.get_payoff(game_id, tuple(profile1))
                payoff2 = self._games.get_payoff(game_id, tuple(profile2))

                if payoff1 and payoff2:
                    p1 = payoff1.get(player_id, 0)
                    p2 = payoff2.get(player_id, 0)

                    if p1 <= p2:
                        is_strictly_dominant = False
                    if p1 < p2:
                        is_weakly_dominant = False
                    if p1 >= p2:
                        is_strictly_dominated = False
                    if p1 > p2:
                        is_weakly_dominated = False

        if is_strictly_dominant:
            return Dominance.STRICTLY_DOMINANT
        elif is_weakly_dominant:
            return Dominance.WEAKLY_DOMINANT
        elif is_strictly_dominated:
            return Dominance.STRICTLY_DOMINATED
        elif is_weakly_dominated:
            return Dominance.WEAKLY_DOMINATED

        return Dominance.NONE

    def find_dominant_strategies(
        self,
        game_id: str
    ) -> Dict[str, Optional[str]]:
        """Find dominant strategy for each player."""
        game = self._games.get_game(game_id)
        if not game:
            return {}

        dominant = {}

        for player_id in game.players:
            strategies = self._players.get_player_strategies(player_id)
            dominant[player_id] = None

            for strategy in strategies:
                dom = self.check_dominance(game_id, player_id, strategy.strategy_id)
                if dom in (Dominance.STRICTLY_DOMINANT, Dominance.WEAKLY_DOMINANT):
                    dominant[player_id] = strategy.strategy_id
                    break

        return dominant


# =============================================================================
# EQUILIBRIUM FINDER
# =============================================================================

class EquilibriumFinder:
    """Find game equilibria."""

    def __init__(
        self,
        game_builder: NormalFormGameBuilder,
        player_manager: PlayerManager
    ):
        self._games = game_builder
        self._players = player_manager

    def find_nash_equilibria(self, game_id: str) -> List[Equilibrium]:
        """Find all pure strategy Nash equilibria."""
        game = self._games.get_game(game_id)
        if not game:
            return []

        equilibria = []
        all_profiles = self._games.all_strategy_profiles(game_id)

        for profile in all_profiles:
            if self._is_nash_equilibrium(game, profile):
                payoffs = self._games.get_payoff(game_id, profile) or {}

                strategy_profile = {}
                for i, player_id in enumerate(game.players):
                    strategy_profile[player_id] = profile[i]

                eq = Equilibrium(
                    eq_type=EquilibriumType.NASH,
                    strategy_profile=strategy_profile,
                    payoffs=payoffs
                )
                equilibria.append(eq)

        return equilibria

    def _is_nash_equilibrium(
        self,
        game: NormalFormGame,
        profile: Tuple[str, ...]
    ) -> bool:
        """Check if a profile is a Nash equilibrium."""
        for i, player_id in enumerate(game.players):
            current_payoff = self._games.get_payoff(game.game_id, profile)
            if not current_payoff:
                return False

            current_utility = current_payoff.get(player_id, 0)

            # Check all alternative strategies
            strategies = self._players.get_player_strategies(player_id)
            for alt_strategy in strategies:
                if alt_strategy.strategy_id == profile[i]:
                    continue

                # Create alternative profile
                alt_profile = list(profile)
                alt_profile[i] = alt_strategy.strategy_id

                alt_payoff = self._games.get_payoff(game.game_id, tuple(alt_profile))
                if alt_payoff:
                    alt_utility = alt_payoff.get(player_id, 0)
                    if alt_utility > current_utility:
                        return False

        return True

    def find_minimax_strategies(
        self,
        game_id: str
    ) -> Dict[str, Tuple[str, float]]:
        """Find minimax strategy for each player."""
        game = self._games.get_game(game_id)
        if not game:
            return {}

        result = {}

        for player_id in game.players:
            strategies = self._players.get_player_strategies(player_id)
            best_strategy = None
            best_value = float('-inf')

            for strategy in strategies:
                # Find minimum payoff for this strategy
                min_payoff = float('inf')
                all_profiles = self._games.all_strategy_profiles(game_id)
                player_idx = game.players.index(player_id)

                for profile in all_profiles:
                    if profile[player_idx] != strategy.strategy_id:
                        continue

                    payoff = self._games.get_payoff(game_id, profile)
                    if payoff:
                        p = payoff.get(player_id, 0)
                        min_payoff = min(min_payoff, p)

                if min_payoff > best_value:
                    best_value = min_payoff
                    best_strategy = strategy.strategy_id

            if best_strategy:
                result[player_id] = (best_strategy, best_value)

        return result


# =============================================================================
# PARETO ANALYZER
# =============================================================================

class ParetoAnalyzer:
    """Analyze Pareto optimality."""

    def __init__(self, game_builder: NormalFormGameBuilder):
        self._games = game_builder

    def is_pareto_optimal(
        self,
        game_id: str,
        profile: Tuple[str, ...]
    ) -> bool:
        """Check if a profile is Pareto optimal."""
        game = self._games.get_game(game_id)
        if not game:
            return False

        current_payoffs = self._games.get_payoff(game_id, profile)
        if not current_payoffs:
            return False

        all_profiles = self._games.all_strategy_profiles(game_id)

        for other_profile in all_profiles:
            if other_profile == profile:
                continue

            other_payoffs = self._games.get_payoff(game_id, other_profile)
            if not other_payoffs:
                continue

            # Check if other_profile Pareto dominates profile
            at_least_as_good = True
            strictly_better = False

            for player_id in game.players:
                current = current_payoffs.get(player_id, 0)
                other = other_payoffs.get(player_id, 0)

                if other < current:
                    at_least_as_good = False
                    break
                if other > current:
                    strictly_better = True

            if at_least_as_good and strictly_better:
                return False  # Profile is Pareto dominated

        return True

    def find_pareto_optimal(self, game_id: str) -> List[Tuple[str, ...]]:
        """Find all Pareto optimal profiles."""
        game = self._games.get_game(game_id)
        if not game:
            return []

        all_profiles = self._games.all_strategy_profiles(game_id)
        return [p for p in all_profiles if self.is_pareto_optimal(game_id, p)]


# =============================================================================
# GAME SOLVER
# =============================================================================

class GameSolver:
    """Solve games using various solution concepts."""

    def __init__(
        self,
        equilibrium_finder: EquilibriumFinder,
        dominance_analyzer: DominanceAnalyzer,
        pareto_analyzer: ParetoAnalyzer
    ):
        self._eq_finder = equilibrium_finder
        self._dom_analyzer = dominance_analyzer
        self._pareto_analyzer = pareto_analyzer

    def solve(
        self,
        game_id: str,
        concept: SolutionConcept = SolutionConcept.NASH_EQUILIBRIUM
    ) -> Dict[str, Any]:
        """Solve the game using specified solution concept."""
        if concept == SolutionConcept.NASH_EQUILIBRIUM:
            equilibria = self._eq_finder.find_nash_equilibria(game_id)
            return {
                "concept": concept.value,
                "equilibria": equilibria,
                "count": len(equilibria)
            }

        elif concept == SolutionConcept.DOMINANT_STRATEGY:
            dominant = self._dom_analyzer.find_dominant_strategies(game_id)
            return {
                "concept": concept.value,
                "dominant_strategies": dominant
            }

        elif concept == SolutionConcept.MINIMAX:
            minimax = self._eq_finder.find_minimax_strategies(game_id)
            return {
                "concept": concept.value,
                "minimax_strategies": minimax
            }

        elif concept == SolutionConcept.PARETO_OPTIMAL:
            pareto = self._pareto_analyzer.find_pareto_optimal(game_id)
            return {
                "concept": concept.value,
                "pareto_optimal": pareto,
                "count": len(pareto)
            }

        return {"concept": concept.value, "result": None}


# =============================================================================
# GAME THEORY ENGINE
# =============================================================================

class GameTheoryEngine:
    """
    Game Theory Engine for BAEL.

    Advanced strategic and game-theoretic reasoning.
    """

    def __init__(self):
        self._player_manager = PlayerManager()
        self._game_builder = NormalFormGameBuilder(self._player_manager)
        self._dominance_analyzer = DominanceAnalyzer(
            self._game_builder, self._player_manager
        )
        self._equilibrium_finder = EquilibriumFinder(
            self._game_builder, self._player_manager
        )
        self._pareto_analyzer = ParetoAnalyzer(self._game_builder)
        self._solver = GameSolver(
            self._equilibrium_finder,
            self._dominance_analyzer,
            self._pareto_analyzer
        )

    # -------------------------------------------------------------------------
    # PLAYERS
    # -------------------------------------------------------------------------

    def create_player(
        self,
        name: str,
        strategies: Optional[List[str]] = None
    ) -> Player:
        """Create a player."""
        return self._player_manager.create_player(name, strategies)

    def add_strategy(
        self,
        player_id: str,
        name: str,
        strategy_type: StrategyType = StrategyType.PURE
    ) -> Optional[Strategy]:
        """Add strategy to player."""
        return self._player_manager.add_strategy(
            player_id, name, strategy_type
        )

    def get_player(self, player_id: str) -> Optional[Player]:
        """Get a player."""
        return self._player_manager.get_player(player_id)

    def get_player_strategies(self, player_id: str) -> List[Strategy]:
        """Get player's strategies."""
        return self._player_manager.get_player_strategies(player_id)

    # -------------------------------------------------------------------------
    # GAMES
    # -------------------------------------------------------------------------

    def create_game(
        self,
        name: str,
        player_ids: List[str]
    ) -> NormalFormGame:
        """Create a normal form game."""
        return self._game_builder.create_game(name, player_ids)

    def set_payoff(
        self,
        game_id: str,
        strategy_profile: Tuple[str, ...],
        payoffs: Dict[str, float]
    ) -> bool:
        """Set payoff for strategy profile."""
        return self._game_builder.set_payoff(game_id, strategy_profile, payoffs)

    def get_payoff(
        self,
        game_id: str,
        strategy_profile: Tuple[str, ...]
    ) -> Optional[Dict[str, float]]:
        """Get payoff for strategy profile."""
        return self._game_builder.get_payoff(game_id, strategy_profile)

    def get_game(self, game_id: str) -> Optional[NormalFormGame]:
        """Get a game."""
        return self._game_builder.get_game(game_id)

    # -------------------------------------------------------------------------
    # ANALYSIS
    # -------------------------------------------------------------------------

    def check_dominance(
        self,
        game_id: str,
        player_id: str,
        strategy_id: str
    ) -> Dominance:
        """Check strategy dominance."""
        return self._dominance_analyzer.check_dominance(
            game_id, player_id, strategy_id
        )

    def find_dominant_strategies(
        self,
        game_id: str
    ) -> Dict[str, Optional[str]]:
        """Find dominant strategies."""
        return self._dominance_analyzer.find_dominant_strategies(game_id)

    def find_nash_equilibria(self, game_id: str) -> List[Equilibrium]:
        """Find Nash equilibria."""
        return self._equilibrium_finder.find_nash_equilibria(game_id)

    def find_minimax_strategies(
        self,
        game_id: str
    ) -> Dict[str, Tuple[str, float]]:
        """Find minimax strategies."""
        return self._equilibrium_finder.find_minimax_strategies(game_id)

    def is_pareto_optimal(
        self,
        game_id: str,
        profile: Tuple[str, ...]
    ) -> bool:
        """Check if profile is Pareto optimal."""
        return self._pareto_analyzer.is_pareto_optimal(game_id, profile)

    def find_pareto_optimal(self, game_id: str) -> List[Tuple[str, ...]]:
        """Find Pareto optimal profiles."""
        return self._pareto_analyzer.find_pareto_optimal(game_id)

    # -------------------------------------------------------------------------
    # SOLVING
    # -------------------------------------------------------------------------

    def solve(
        self,
        game_id: str,
        concept: SolutionConcept = SolutionConcept.NASH_EQUILIBRIUM
    ) -> Dict[str, Any]:
        """Solve game using solution concept."""
        return self._solver.solve(game_id, concept)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Game Theory Engine."""
    print("=" * 70)
    print("BAEL - GAME THEORY ENGINE DEMO")
    print("Advanced Strategic and Game-Theoretic Reasoning")
    print("=" * 70)
    print()

    engine = GameTheoryEngine()

    # 1. Create Players
    print("1. CREATE PLAYERS:")
    print("-" * 40)

    player1 = engine.create_player("Player 1")
    player2 = engine.create_player("Player 2")

    print(f"   {player1.name} (ID: {player1.player_id[:8]}...)")
    print(f"   {player2.name} (ID: {player2.player_id[:8]}...)")
    print()

    # 2. Add Strategies (Prisoner's Dilemma)
    print("2. ADD STRATEGIES (Prisoner's Dilemma):")
    print("-" * 40)

    p1_cooperate = engine.add_strategy(player1.player_id, "Cooperate")
    p1_defect = engine.add_strategy(player1.player_id, "Defect")

    p2_cooperate = engine.add_strategy(player2.player_id, "Cooperate")
    p2_defect = engine.add_strategy(player2.player_id, "Defect")

    print(f"   Player 1: Cooperate, Defect")
    print(f"   Player 2: Cooperate, Defect")
    print()

    # 3. Create Game
    print("3. CREATE PRISONER'S DILEMMA GAME:")
    print("-" * 40)

    game = engine.create_game(
        "Prisoner's Dilemma",
        [player1.player_id, player2.player_id]
    )

    # Set payoffs (C,C), (C,D), (D,C), (D,D)
    engine.set_payoff(
        game.game_id,
        (p1_cooperate.strategy_id, p2_cooperate.strategy_id),
        {player1.player_id: -1, player2.player_id: -1}
    )

    engine.set_payoff(
        game.game_id,
        (p1_cooperate.strategy_id, p2_defect.strategy_id),
        {player1.player_id: -3, player2.player_id: 0}
    )

    engine.set_payoff(
        game.game_id,
        (p1_defect.strategy_id, p2_cooperate.strategy_id),
        {player1.player_id: 0, player2.player_id: -3}
    )

    engine.set_payoff(
        game.game_id,
        (p1_defect.strategy_id, p2_defect.strategy_id),
        {player1.player_id: -2, player2.player_id: -2}
    )

    print("   Payoff Matrix:")
    print("                  P2: Cooperate  P2: Defect")
    print("   P1: Cooperate    (-1, -1)      (-3, 0)")
    print("   P1: Defect       (0, -3)       (-2, -2)")
    print()

    # 4. Check Dominance
    print("4. DOMINANCE ANALYSIS:")
    print("-" * 40)

    dom_coop = engine.check_dominance(
        game.game_id, player1.player_id, p1_cooperate.strategy_id
    )
    dom_defect = engine.check_dominance(
        game.game_id, player1.player_id, p1_defect.strategy_id
    )

    print(f"   Player 1 'Cooperate': {dom_coop.value}")
    print(f"   Player 1 'Defect': {dom_defect.value}")

    dominant = engine.find_dominant_strategies(game.game_id)
    print(f"   Dominant strategies: {dominant}")
    print()

    # 5. Find Nash Equilibria
    print("5. NASH EQUILIBRIA:")
    print("-" * 40)

    equilibria = engine.find_nash_equilibria(game.game_id)

    print(f"   Found {len(equilibria)} Nash equilibrium/equilibria:")
    for eq in equilibria:
        strategies = []
        for pid, sid in eq.strategy_profile.items():
            player = engine.get_player(pid)
            strategy = engine._player_manager.get_strategy(sid)
            strategies.append(f"{player.name}: {strategy.name}")
        print(f"     {strategies}")
        print(f"     Payoffs: {eq.payoffs}")
    print()

    # 6. Minimax Strategies
    print("6. MINIMAX STRATEGIES:")
    print("-" * 40)

    minimax = engine.find_minimax_strategies(game.game_id)

    for pid, (sid, value) in minimax.items():
        player = engine.get_player(pid)
        strategy = engine._player_manager.get_strategy(sid)
        print(f"   {player.name}: {strategy.name} (guaranteed: {value})")
    print()

    # 7. Pareto Optimality
    print("7. PARETO OPTIMALITY:")
    print("-" * 40)

    pareto = engine.find_pareto_optimal(game.game_id)

    print(f"   Pareto optimal outcomes: {len(pareto)}")
    for profile in pareto:
        payoff = engine.get_payoff(game.game_id, profile)
        strategies = []
        for i, sid in enumerate(profile):
            strategy = engine._player_manager.get_strategy(sid)
            strategies.append(strategy.name if strategy else "?")
        print(f"     ({', '.join(strategies)}): {payoff}")
    print()

    # 8. Solve with Different Concepts
    print("8. SOLVE WITH SOLUTION CONCEPTS:")
    print("-" * 40)

    for concept in [SolutionConcept.NASH_EQUILIBRIUM,
                   SolutionConcept.DOMINANT_STRATEGY,
                   SolutionConcept.PARETO_OPTIMAL]:
        result = engine.solve(game.game_id, concept)
        print(f"   {concept.value}:")
        if "count" in result:
            print(f"     Count: {result['count']}")
        elif "dominant_strategies" in result:
            print(f"     Result: Found")
    print()

    # 9. Create Coordination Game
    print("9. COORDINATION GAME EXAMPLE:")
    print("-" * 40)

    alice = engine.create_player("Alice")
    bob = engine.create_player("Bob")

    a_left = engine.add_strategy(alice.player_id, "Left")
    a_right = engine.add_strategy(alice.player_id, "Right")
    b_left = engine.add_strategy(bob.player_id, "Left")
    b_right = engine.add_strategy(bob.player_id, "Right")

    coord_game = engine.create_game(
        "Coordination Game",
        [alice.player_id, bob.player_id]
    )

    # Coordination payoffs
    engine.set_payoff(coord_game.game_id, (a_left.strategy_id, b_left.strategy_id),
                     {alice.player_id: 2, bob.player_id: 2})
    engine.set_payoff(coord_game.game_id, (a_left.strategy_id, b_right.strategy_id),
                     {alice.player_id: 0, bob.player_id: 0})
    engine.set_payoff(coord_game.game_id, (a_right.strategy_id, b_left.strategy_id),
                     {alice.player_id: 0, bob.player_id: 0})
    engine.set_payoff(coord_game.game_id, (a_right.strategy_id, b_right.strategy_id),
                     {alice.player_id: 1, bob.player_id: 1})

    coord_eq = engine.find_nash_equilibria(coord_game.game_id)
    print(f"   Coordination Game Nash Equilibria: {len(coord_eq)}")
    for eq in coord_eq:
        print(f"     Payoffs: {eq.payoffs}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Game Theory Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
