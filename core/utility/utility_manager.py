#!/usr/bin/env python3
"""
BAEL - Utility Manager
Advanced utility theory and decision analysis.

Features:
- Utility functions
- Expected utility calculation
- Risk preferences
- Multi-attribute utility
- Value of information
- Decision analysis
"""

import asyncio
import copy
import hashlib
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

class UtilityType(Enum):
    """Types of utility functions."""
    LINEAR = "linear"
    LOGARITHMIC = "logarithmic"
    EXPONENTIAL = "exponential"
    POWER = "power"
    QUADRATIC = "quadratic"


class RiskPreference(Enum):
    """Risk preference types."""
    RISK_NEUTRAL = "risk_neutral"
    RISK_AVERSE = "risk_averse"
    RISK_SEEKING = "risk_seeking"


class AggregationType(Enum):
    """Aggregation methods for multi-attribute utility."""
    ADDITIVE = "additive"
    MULTIPLICATIVE = "multiplicative"
    WEIGHTED_SUM = "weighted_sum"
    MIN = "min"
    MAX = "max"


class DecisionCriterion(Enum):
    """Decision criteria."""
    EXPECTED_UTILITY = "expected_utility"
    MAXIMIN = "maximin"
    MAXIMAX = "maximax"
    MINIMAX_REGRET = "minimax_regret"
    HURWICZ = "hurwicz"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Outcome:
    """An outcome of an action."""
    outcome_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    value: float = 0.0
    attributes: Dict[str, float] = field(default_factory=dict)


@dataclass
class Probability:
    """A probability distribution over outcomes."""
    prob_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    probabilities: Dict[str, float] = field(default_factory=dict)  # outcome_id -> prob


@dataclass
class Action:
    """An action with probabilistic outcomes."""
    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    outcomes: List[str] = field(default_factory=list)
    distribution: Optional[str] = None  # Probability ID


@dataclass
class Attribute:
    """An attribute for multi-attribute utility."""
    attr_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    weight: float = 1.0
    min_value: float = 0.0
    max_value: float = 1.0
    utility_type: UtilityType = UtilityType.LINEAR


@dataclass
class UtilityFunction:
    """A utility function specification."""
    func_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    utility_type: UtilityType = UtilityType.LINEAR
    parameters: Dict[str, float] = field(default_factory=dict)
    risk_preference: RiskPreference = RiskPreference.RISK_NEUTRAL


@dataclass
class Decision:
    """A decision problem."""
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    actions: List[str] = field(default_factory=list)
    recommended_action: Optional[str] = None
    expected_utilities: Dict[str, float] = field(default_factory=dict)


@dataclass
class InformationValue:
    """Value of information calculation."""
    info_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    decision_id: str = ""
    voi: float = 0.0
    perfect_info_utility: float = 0.0
    base_utility: float = 0.0


# =============================================================================
# UTILITY CALCULATOR
# =============================================================================

class UtilityCalculator:
    """Calculate utility values."""

    def __init__(self):
        self._functions: Dict[str, UtilityFunction] = {}

    def create_function(
        self,
        utility_type: UtilityType,
        parameters: Optional[Dict[str, float]] = None,
        risk_preference: RiskPreference = RiskPreference.RISK_NEUTRAL
    ) -> UtilityFunction:
        """Create a utility function."""
        func = UtilityFunction(
            utility_type=utility_type,
            parameters=parameters or {},
            risk_preference=risk_preference
        )
        self._functions[func.func_id] = func
        return func

    def calculate(
        self,
        func_id: str,
        value: float
    ) -> float:
        """Calculate utility for a value."""
        func = self._functions.get(func_id)
        if not func:
            return value  # Default to linear

        params = func.parameters

        if func.utility_type == UtilityType.LINEAR:
            a = params.get('a', 1.0)
            b = params.get('b', 0.0)
            return a * value + b

        elif func.utility_type == UtilityType.LOGARITHMIC:
            a = params.get('a', 1.0)
            if value <= 0:
                return float('-inf')
            return a * math.log(value)

        elif func.utility_type == UtilityType.EXPONENTIAL:
            a = params.get('a', 1.0)
            r = params.get('r', 1.0)  # Risk aversion coefficient
            if r == 0:
                return value
            return (1 - math.exp(-r * value)) / r

        elif func.utility_type == UtilityType.POWER:
            a = params.get('a', 1.0)
            gamma = params.get('gamma', 0.5)  # Power coefficient
            if value < 0:
                return -a * (abs(value) ** gamma)
            return a * (value ** gamma)

        elif func.utility_type == UtilityType.QUADRATIC:
            a = params.get('a', 1.0)
            b = params.get('b', 0.0)
            return a * value - b * (value ** 2)

        return value

    def get_function(self, func_id: str) -> Optional[UtilityFunction]:
        """Get a utility function."""
        return self._functions.get(func_id)

    def infer_risk_preference(
        self,
        func_id: str
    ) -> RiskPreference:
        """Infer risk preference from utility function."""
        func = self._functions.get(func_id)
        if not func:
            return RiskPreference.RISK_NEUTRAL

        # Check concavity at midpoint
        x1, x2 = 0.0, 1.0
        mid = (x1 + x2) / 2

        u1 = self.calculate(func_id, x1)
        u2 = self.calculate(func_id, x2)
        u_mid = self.calculate(func_id, mid)

        expected = (u1 + u2) / 2

        if abs(u_mid - expected) < 0.001:
            return RiskPreference.RISK_NEUTRAL
        elif u_mid > expected:
            return RiskPreference.RISK_AVERSE
        else:
            return RiskPreference.RISK_SEEKING


# =============================================================================
# OUTCOME MANAGER
# =============================================================================

class OutcomeManager:
    """Manage outcomes."""

    def __init__(self):
        self._outcomes: Dict[str, Outcome] = {}
        self._probabilities: Dict[str, Probability] = {}

    def create_outcome(
        self,
        description: str,
        value: float = 0.0,
        attributes: Optional[Dict[str, float]] = None
    ) -> Outcome:
        """Create an outcome."""
        outcome = Outcome(
            description=description,
            value=value,
            attributes=attributes or {}
        )
        self._outcomes[outcome.outcome_id] = outcome
        return outcome

    def create_probability(
        self,
        probabilities: Dict[str, float]
    ) -> Probability:
        """Create a probability distribution."""
        # Normalize
        total = sum(probabilities.values())
        if total > 0:
            probabilities = {k: v / total for k, v in probabilities.items()}

        prob = Probability(probabilities=probabilities)
        self._probabilities[prob.prob_id] = prob
        return prob

    def get_outcome(self, outcome_id: str) -> Optional[Outcome]:
        """Get an outcome."""
        return self._outcomes.get(outcome_id)

    def get_probability(self, prob_id: str) -> Optional[Probability]:
        """Get a probability distribution."""
        return self._probabilities.get(prob_id)

    def expected_value(self, prob_id: str) -> float:
        """Calculate expected value."""
        prob = self._probabilities.get(prob_id)
        if not prob:
            return 0.0

        ev = 0.0
        for outcome_id, p in prob.probabilities.items():
            outcome = self._outcomes.get(outcome_id)
            if outcome:
                ev += p * outcome.value

        return ev


# =============================================================================
# ACTION MANAGER
# =============================================================================

class ActionManager:
    """Manage actions."""

    def __init__(self, outcome_manager: OutcomeManager):
        self._outcomes = outcome_manager
        self._actions: Dict[str, Action] = {}

    def create_action(
        self,
        name: str,
        description: str = "",
        outcomes: Optional[List[str]] = None,
        distribution_id: Optional[str] = None
    ) -> Action:
        """Create an action."""
        action = Action(
            name=name,
            description=description,
            outcomes=outcomes or [],
            distribution=distribution_id
        )
        self._actions[action.action_id] = action
        return action

    def get_action(self, action_id: str) -> Optional[Action]:
        """Get an action."""
        return self._actions.get(action_id)

    def get_expected_value(self, action_id: str) -> float:
        """Get expected value of action."""
        action = self._actions.get(action_id)
        if not action or not action.distribution:
            return 0.0
        return self._outcomes.expected_value(action.distribution)

    def all_actions(self) -> List[Action]:
        """Get all actions."""
        return list(self._actions.values())


# =============================================================================
# MULTI-ATTRIBUTE UTILITY
# =============================================================================

class MultiAttributeUtility:
    """Multi-attribute utility theory."""

    def __init__(self, utility_calculator: UtilityCalculator):
        self._utility = utility_calculator
        self._attributes: Dict[str, Attribute] = {}

    def create_attribute(
        self,
        name: str,
        weight: float = 1.0,
        min_value: float = 0.0,
        max_value: float = 1.0,
        utility_type: UtilityType = UtilityType.LINEAR
    ) -> Attribute:
        """Create an attribute."""
        attr = Attribute(
            name=name,
            weight=weight,
            min_value=min_value,
            max_value=max_value,
            utility_type=utility_type
        )
        self._attributes[attr.attr_id] = attr
        return attr

    def normalize_weights(self) -> None:
        """Normalize attribute weights to sum to 1."""
        total = sum(a.weight for a in self._attributes.values())
        if total > 0:
            for attr in self._attributes.values():
                attr.weight /= total

    def calculate_mau(
        self,
        attribute_values: Dict[str, float],
        aggregation: AggregationType = AggregationType.WEIGHTED_SUM
    ) -> float:
        """Calculate multi-attribute utility."""
        if aggregation == AggregationType.WEIGHTED_SUM:
            return self._weighted_sum(attribute_values)
        elif aggregation == AggregationType.MULTIPLICATIVE:
            return self._multiplicative(attribute_values)
        elif aggregation == AggregationType.MIN:
            return self._min_aggregation(attribute_values)
        elif aggregation == AggregationType.MAX:
            return self._max_aggregation(attribute_values)
        else:
            return self._weighted_sum(attribute_values)

    def _weighted_sum(self, values: Dict[str, float]) -> float:
        """Weighted sum aggregation."""
        total = 0.0

        for attr_id, attr in self._attributes.items():
            if attr.name in values:
                # Normalize to [0, 1]
                raw = values[attr.name]
                normalized = (raw - attr.min_value) / (attr.max_value - attr.min_value)
                normalized = max(0, min(1, normalized))

                total += attr.weight * normalized

        return total

    def _multiplicative(self, values: Dict[str, float]) -> float:
        """Multiplicative aggregation."""
        result = 1.0

        for attr_id, attr in self._attributes.items():
            if attr.name in values:
                raw = values[attr.name]
                normalized = (raw - attr.min_value) / (attr.max_value - attr.min_value)
                normalized = max(0.001, min(1, normalized))

                result *= (normalized ** attr.weight)

        return result

    def _min_aggregation(self, values: Dict[str, float]) -> float:
        """Min aggregation."""
        utilities = []

        for attr_id, attr in self._attributes.items():
            if attr.name in values:
                raw = values[attr.name]
                normalized = (raw - attr.min_value) / (attr.max_value - attr.min_value)
                utilities.append(attr.weight * normalized)

        return min(utilities) if utilities else 0.0

    def _max_aggregation(self, values: Dict[str, float]) -> float:
        """Max aggregation."""
        utilities = []

        for attr_id, attr in self._attributes.items():
            if attr.name in values:
                raw = values[attr.name]
                normalized = (raw - attr.min_value) / (attr.max_value - attr.min_value)
                utilities.append(attr.weight * normalized)

        return max(utilities) if utilities else 0.0


# =============================================================================
# EXPECTED UTILITY CALCULATOR
# =============================================================================

class ExpectedUtilityCalculator:
    """Calculate expected utilities."""

    def __init__(
        self,
        utility_calculator: UtilityCalculator,
        outcome_manager: OutcomeManager
    ):
        self._utility = utility_calculator
        self._outcomes = outcome_manager

    def calculate_eu(
        self,
        func_id: str,
        prob_id: str
    ) -> float:
        """Calculate expected utility."""
        prob = self._outcomes.get_probability(prob_id)
        if not prob:
            return 0.0

        eu = 0.0
        for outcome_id, p in prob.probabilities.items():
            outcome = self._outcomes.get_outcome(outcome_id)
            if outcome:
                utility = self._utility.calculate(func_id, outcome.value)
                eu += p * utility

        return eu

    def certainty_equivalent(
        self,
        func_id: str,
        prob_id: str
    ) -> float:
        """Calculate certainty equivalent."""
        eu = self.calculate_eu(func_id, prob_id)

        # Find value x such that u(x) = EU
        func = self._utility.get_function(func_id)
        if not func:
            return eu

        # Binary search for certainty equivalent
        low, high = -1000.0, 1000.0

        for _ in range(100):
            mid = (low + high) / 2
            u_mid = self._utility.calculate(func_id, mid)

            if abs(u_mid - eu) < 0.001:
                return mid
            elif u_mid < eu:
                low = mid
            else:
                high = mid

        return (low + high) / 2

    def risk_premium(
        self,
        func_id: str,
        prob_id: str
    ) -> float:
        """Calculate risk premium."""
        ev = self._outcomes.expected_value(prob_id)
        ce = self.certainty_equivalent(func_id, prob_id)
        return ev - ce


# =============================================================================
# DECISION ANALYZER
# =============================================================================

class DecisionAnalyzer:
    """Analyze decisions."""

    def __init__(
        self,
        action_manager: ActionManager,
        eu_calculator: ExpectedUtilityCalculator
    ):
        self._actions = action_manager
        self._eu_calc = eu_calculator
        self._decisions: Dict[str, Decision] = {}

    def create_decision(
        self,
        name: str,
        action_ids: List[str]
    ) -> Decision:
        """Create a decision problem."""
        decision = Decision(
            name=name,
            actions=action_ids
        )
        self._decisions[decision.decision_id] = decision
        return decision

    def analyze(
        self,
        decision_id: str,
        func_id: str,
        criterion: DecisionCriterion = DecisionCriterion.EXPECTED_UTILITY
    ) -> Optional[str]:
        """Analyze decision and recommend action."""
        decision = self._decisions.get(decision_id)
        if not decision:
            return None

        if criterion == DecisionCriterion.EXPECTED_UTILITY:
            return self._max_expected_utility(decision, func_id)
        elif criterion == DecisionCriterion.MAXIMIN:
            return self._maximin(decision, func_id)
        elif criterion == DecisionCriterion.MAXIMAX:
            return self._maximax(decision, func_id)

        return None

    def _max_expected_utility(
        self,
        decision: Decision,
        func_id: str
    ) -> Optional[str]:
        """Maximum expected utility criterion."""
        best_action = None
        best_eu = float('-inf')

        for action_id in decision.actions:
            action = self._actions.get_action(action_id)
            if action and action.distribution:
                eu = self._eu_calc.calculate_eu(func_id, action.distribution)
                decision.expected_utilities[action_id] = eu

                if eu > best_eu:
                    best_eu = eu
                    best_action = action_id

        decision.recommended_action = best_action
        return best_action

    def _maximin(
        self,
        decision: Decision,
        func_id: str
    ) -> Optional[str]:
        """Maximin criterion."""
        best_action = None
        best_min = float('-inf')

        for action_id in decision.actions:
            action = self._actions.get_action(action_id)
            if action:
                min_utility = float('inf')

                for outcome_id in action.outcomes:
                    outcome = self._actions._outcomes.get_outcome(outcome_id)
                    if outcome:
                        u = self._eu_calc._utility.calculate(func_id, outcome.value)
                        min_utility = min(min_utility, u)

                if min_utility > best_min:
                    best_min = min_utility
                    best_action = action_id

        decision.recommended_action = best_action
        return best_action

    def _maximax(
        self,
        decision: Decision,
        func_id: str
    ) -> Optional[str]:
        """Maximax criterion."""
        best_action = None
        best_max = float('-inf')

        for action_id in decision.actions:
            action = self._actions.get_action(action_id)
            if action:
                max_utility = float('-inf')

                for outcome_id in action.outcomes:
                    outcome = self._actions._outcomes.get_outcome(outcome_id)
                    if outcome:
                        u = self._eu_calc._utility.calculate(func_id, outcome.value)
                        max_utility = max(max_utility, u)

                if max_utility > best_max:
                    best_max = max_utility
                    best_action = action_id

        decision.recommended_action = best_action
        return best_action

    def get_decision(self, decision_id: str) -> Optional[Decision]:
        """Get a decision."""
        return self._decisions.get(decision_id)


# =============================================================================
# VALUE OF INFORMATION
# =============================================================================

class ValueOfInformation:
    """Calculate value of information."""

    def __init__(
        self,
        decision_analyzer: DecisionAnalyzer,
        eu_calculator: ExpectedUtilityCalculator
    ):
        self._decisions = decision_analyzer
        self._eu_calc = eu_calculator

    def calculate_vpi(
        self,
        decision_id: str,
        func_id: str
    ) -> Optional[InformationValue]:
        """Calculate value of perfect information."""
        decision = self._decisions.get_decision(decision_id)
        if not decision:
            return None

        # Get base expected utility (without information)
        best_action = self._decisions.analyze(
            decision_id, func_id,
            DecisionCriterion.EXPECTED_UTILITY
        )

        base_eu = decision.expected_utilities.get(best_action, 0.0)

        # Calculate expected utility with perfect information
        # (weighted average of best outcomes)
        perfect_eu = 0.0

        # Simplified: assume perfect info gives max EU
        all_eus = list(decision.expected_utilities.values())
        if all_eus:
            perfect_eu = max(all_eus)

        voi = InformationValue(
            decision_id=decision_id,
            voi=perfect_eu - base_eu,
            perfect_info_utility=perfect_eu,
            base_utility=base_eu
        )

        return voi


# =============================================================================
# UTILITY MANAGER
# =============================================================================

class UtilityManager:
    """
    Utility Manager for BAEL.

    Advanced utility theory and decision analysis.
    """

    def __init__(self):
        self._utility_calc = UtilityCalculator()
        self._outcome_manager = OutcomeManager()
        self._action_manager = ActionManager(self._outcome_manager)
        self._mau = MultiAttributeUtility(self._utility_calc)
        self._eu_calc = ExpectedUtilityCalculator(
            self._utility_calc, self._outcome_manager
        )
        self._decision_analyzer = DecisionAnalyzer(
            self._action_manager, self._eu_calc
        )
        self._voi = ValueOfInformation(self._decision_analyzer, self._eu_calc)

    # -------------------------------------------------------------------------
    # UTILITY FUNCTIONS
    # -------------------------------------------------------------------------

    def create_utility_function(
        self,
        utility_type: UtilityType,
        parameters: Optional[Dict[str, float]] = None,
        risk_preference: RiskPreference = RiskPreference.RISK_NEUTRAL
    ) -> UtilityFunction:
        """Create a utility function."""
        return self._utility_calc.create_function(
            utility_type, parameters, risk_preference
        )

    def calculate_utility(self, func_id: str, value: float) -> float:
        """Calculate utility of a value."""
        return self._utility_calc.calculate(func_id, value)

    def infer_risk_preference(self, func_id: str) -> RiskPreference:
        """Infer risk preference from utility function."""
        return self._utility_calc.infer_risk_preference(func_id)

    # -------------------------------------------------------------------------
    # OUTCOMES
    # -------------------------------------------------------------------------

    def create_outcome(
        self,
        description: str,
        value: float = 0.0,
        attributes: Optional[Dict[str, float]] = None
    ) -> Outcome:
        """Create an outcome."""
        return self._outcome_manager.create_outcome(
            description, value, attributes
        )

    def create_probability_distribution(
        self,
        probabilities: Dict[str, float]
    ) -> Probability:
        """Create a probability distribution."""
        return self._outcome_manager.create_probability(probabilities)

    def expected_value(self, prob_id: str) -> float:
        """Calculate expected value."""
        return self._outcome_manager.expected_value(prob_id)

    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------

    def create_action(
        self,
        name: str,
        description: str = "",
        outcomes: Optional[List[str]] = None,
        distribution_id: Optional[str] = None
    ) -> Action:
        """Create an action."""
        return self._action_manager.create_action(
            name, description, outcomes, distribution_id
        )

    def get_action_expected_value(self, action_id: str) -> float:
        """Get expected value of action."""
        return self._action_manager.get_expected_value(action_id)

    # -------------------------------------------------------------------------
    # MULTI-ATTRIBUTE UTILITY
    # -------------------------------------------------------------------------

    def create_attribute(
        self,
        name: str,
        weight: float = 1.0,
        min_value: float = 0.0,
        max_value: float = 1.0,
        utility_type: UtilityType = UtilityType.LINEAR
    ) -> Attribute:
        """Create an attribute."""
        return self._mau.create_attribute(
            name, weight, min_value, max_value, utility_type
        )

    def normalize_weights(self) -> None:
        """Normalize attribute weights."""
        self._mau.normalize_weights()

    def calculate_mau(
        self,
        attribute_values: Dict[str, float],
        aggregation: AggregationType = AggregationType.WEIGHTED_SUM
    ) -> float:
        """Calculate multi-attribute utility."""
        return self._mau.calculate_mau(attribute_values, aggregation)

    # -------------------------------------------------------------------------
    # EXPECTED UTILITY
    # -------------------------------------------------------------------------

    def calculate_expected_utility(
        self,
        func_id: str,
        prob_id: str
    ) -> float:
        """Calculate expected utility."""
        return self._eu_calc.calculate_eu(func_id, prob_id)

    def certainty_equivalent(
        self,
        func_id: str,
        prob_id: str
    ) -> float:
        """Calculate certainty equivalent."""
        return self._eu_calc.certainty_equivalent(func_id, prob_id)

    def risk_premium(self, func_id: str, prob_id: str) -> float:
        """Calculate risk premium."""
        return self._eu_calc.risk_premium(func_id, prob_id)

    # -------------------------------------------------------------------------
    # DECISION ANALYSIS
    # -------------------------------------------------------------------------

    def create_decision(
        self,
        name: str,
        action_ids: List[str]
    ) -> Decision:
        """Create a decision problem."""
        return self._decision_analyzer.create_decision(name, action_ids)

    def analyze_decision(
        self,
        decision_id: str,
        func_id: str,
        criterion: DecisionCriterion = DecisionCriterion.EXPECTED_UTILITY
    ) -> Optional[str]:
        """Analyze decision and get recommendation."""
        return self._decision_analyzer.analyze(decision_id, func_id, criterion)

    def get_decision(self, decision_id: str) -> Optional[Decision]:
        """Get a decision."""
        return self._decision_analyzer.get_decision(decision_id)

    # -------------------------------------------------------------------------
    # VALUE OF INFORMATION
    # -------------------------------------------------------------------------

    def calculate_vpi(
        self,
        decision_id: str,
        func_id: str
    ) -> Optional[InformationValue]:
        """Calculate value of perfect information."""
        return self._voi.calculate_vpi(decision_id, func_id)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Utility Manager."""
    print("=" * 70)
    print("BAEL - UTILITY MANAGER DEMO")
    print("Advanced Utility Theory and Decision Analysis")
    print("=" * 70)
    print()

    manager = UtilityManager()

    # 1. Create Utility Functions
    print("1. UTILITY FUNCTIONS:")
    print("-" * 40)

    linear_func = manager.create_utility_function(
        UtilityType.LINEAR,
        {'a': 1.0, 'b': 0.0}
    )

    log_func = manager.create_utility_function(
        UtilityType.LOGARITHMIC,
        {'a': 1.0},
        RiskPreference.RISK_AVERSE
    )

    exp_func = manager.create_utility_function(
        UtilityType.EXPONENTIAL,
        {'r': 0.5},  # Risk aversion coefficient
        RiskPreference.RISK_AVERSE
    )

    print(f"   Linear: U(x) = x")
    print(f"   Logarithmic: U(x) = ln(x)")
    print(f"   Exponential: U(x) = (1 - e^(-rx)) / r")
    print()

    # 2. Calculate Utilities
    print("2. UTILITY CALCULATIONS:")
    print("-" * 40)

    values = [10, 50, 100]
    for val in values:
        u_lin = manager.calculate_utility(linear_func.func_id, val)
        u_log = manager.calculate_utility(log_func.func_id, val)
        u_exp = manager.calculate_utility(exp_func.func_id, val)
        print(f"   Value {val}: Linear={u_lin:.2f}, Log={u_log:.2f}, Exp={u_exp:.2f}")
    print()

    # 3. Create Outcomes
    print("3. CREATE OUTCOMES:")
    print("-" * 40)

    win_big = manager.create_outcome("Win big", 1000)
    win_small = manager.create_outcome("Win small", 100)
    lose = manager.create_outcome("Lose", -50)

    print(f"   {win_big.description}: ${win_big.value}")
    print(f"   {win_small.description}: ${win_small.value}")
    print(f"   {lose.description}: ${lose.value}")
    print()

    # 4. Create Probability Distribution
    print("4. PROBABILITY DISTRIBUTION:")
    print("-" * 40)

    risky_dist = manager.create_probability_distribution({
        win_big.outcome_id: 0.1,
        win_small.outcome_id: 0.3,
        lose.outcome_id: 0.6
    })

    ev = manager.expected_value(risky_dist.prob_id)
    print(f"   P(Win big)=0.1, P(Win small)=0.3, P(Lose)=0.6")
    print(f"   Expected Value: ${ev:.2f}")
    print()

    # 5. Expected Utility
    print("5. EXPECTED UTILITY:")
    print("-" * 40)

    # Create safe outcome
    safe = manager.create_outcome("Safe return", 50)
    safe_dist = manager.create_probability_distribution({
        safe.outcome_id: 1.0
    })

    eu_risky = manager.calculate_expected_utility(linear_func.func_id, risky_dist.prob_id)
    eu_safe = manager.calculate_expected_utility(linear_func.func_id, safe_dist.prob_id)

    print(f"   EU(Risky, Linear): {eu_risky:.2f}")
    print(f"   EU(Safe, Linear): {eu_safe:.2f}")
    print()

    # 6. Certainty Equivalent & Risk Premium
    print("6. CERTAINTY EQUIVALENT & RISK PREMIUM:")
    print("-" * 40)

    ce = manager.certainty_equivalent(linear_func.func_id, risky_dist.prob_id)
    rp = manager.risk_premium(linear_func.func_id, risky_dist.prob_id)

    print(f"   Certainty Equivalent: ${ce:.2f}")
    print(f"   Risk Premium: ${rp:.2f}")
    print()

    # 7. Multi-Attribute Utility
    print("7. MULTI-ATTRIBUTE UTILITY:")
    print("-" * 40)

    quality = manager.create_attribute("quality", weight=0.4, min_value=0, max_value=100)
    price = manager.create_attribute("price", weight=0.3, min_value=0, max_value=1000)
    speed = manager.create_attribute("speed", weight=0.3, min_value=0, max_value=10)

    manager.normalize_weights()

    option_a = {"quality": 80, "price": 500, "speed": 7}
    option_b = {"quality": 60, "price": 300, "speed": 9}

    mau_a = manager.calculate_mau(option_a)
    mau_b = manager.calculate_mau(option_b)

    print(f"   Option A: quality=80, price=500, speed=7")
    print(f"   Option B: quality=60, price=300, speed=9")
    print(f"   MAU(A): {mau_a:.3f}")
    print(f"   MAU(B): {mau_b:.3f}")
    print()

    # 8. Decision Analysis
    print("8. DECISION ANALYSIS:")
    print("-" * 40)

    risky_action = manager.create_action(
        "Risky Investment",
        "High risk, high reward",
        [win_big.outcome_id, win_small.outcome_id, lose.outcome_id],
        risky_dist.prob_id
    )

    safe_action = manager.create_action(
        "Safe Investment",
        "Low risk, guaranteed return",
        [safe.outcome_id],
        safe_dist.prob_id
    )

    decision = manager.create_decision(
        "Investment Choice",
        [risky_action.action_id, safe_action.action_id]
    )

    recommended = manager.analyze_decision(
        decision.decision_id,
        linear_func.func_id,
        DecisionCriterion.EXPECTED_UTILITY
    )

    rec_action = manager._action_manager.get_action(recommended) if recommended else None
    print(f"   Decision: {decision.name}")
    print(f"   Recommended (EU): {rec_action.name if rec_action else 'None'}")
    print(f"   Expected utilities: {decision.expected_utilities}")
    print()

    # 9. Value of Perfect Information
    print("9. VALUE OF PERFECT INFORMATION:")
    print("-" * 40)

    vpi = manager.calculate_vpi(decision.decision_id, linear_func.func_id)

    if vpi:
        print(f"   Base EU: {vpi.base_utility:.2f}")
        print(f"   Perfect Info EU: {vpi.perfect_info_utility:.2f}")
        print(f"   VPI: {vpi.voi:.2f}")
    print()

    # 10. Risk Preference Analysis
    print("10. RISK PREFERENCE ANALYSIS:")
    print("-" * 40)

    pref_lin = manager.infer_risk_preference(linear_func.func_id)
    pref_log = manager.infer_risk_preference(log_func.func_id)
    pref_exp = manager.infer_risk_preference(exp_func.func_id)

    print(f"   Linear function: {pref_lin.value}")
    print(f"   Logarithmic function: {pref_log.value}")
    print(f"   Exponential function: {pref_exp.value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Utility Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
