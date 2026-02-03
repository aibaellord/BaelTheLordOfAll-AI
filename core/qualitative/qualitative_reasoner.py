#!/usr/bin/env python3
"""
BAEL - Qualitative Reasoner
Advanced qualitative reasoning and physics.

Features:
- Qualitative values
- Qualitative calculus
- Qualitative physics
- Comparative reasoning
- Trend analysis
- Landmark values
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

class QualitativeValue(Enum):
    """Basic qualitative values."""
    NEGATIVE = "negative"  # -
    ZERO = "zero"  # 0
    POSITIVE = "positive"  # +


class QualitativeDirection(Enum):
    """Qualitative directions/derivatives."""
    DECREASING = "decreasing"  # ↓
    STEADY = "steady"  # →
    INCREASING = "increasing"  # ↑


class QualitativeMagnitude(Enum):
    """Qualitative magnitude comparisons."""
    MUCH_LESS = "much_less"
    LESS = "less"
    EQUAL = "equal"
    GREATER = "greater"
    MUCH_GREATER = "much_greater"


class RelationType(Enum):
    """Types of qualitative relations."""
    PROPORTIONAL = "proportional"  # M+(A,B): when A increases, B increases
    INVERSE = "inverse"  # M-(A,B): when A increases, B decreases
    INFLUENCE_PLUS = "influence_plus"  # I+(A,B): A adds to derivative of B
    INFLUENCE_MINUS = "influence_minus"  # I-(A,B): A subtracts from derivative of B
    CORRESPONDENCE = "correspondence"  # Value correspondence


class BehaviorType(Enum):
    """Types of qualitative behaviors."""
    EQUILIBRIUM = "equilibrium"
    INCREASING = "increasing"
    DECREASING = "decreasing"
    OSCILLATING = "oscillating"
    ASYMPTOTIC = "asymptotic"


class TransitionType(Enum):
    """Types of state transitions."""
    CONTINUOUS = "continuous"
    DISCONTINUOUS = "discontinuous"
    LANDMARK = "landmark"  # Passing through landmark value


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class QValue:
    """A qualitative value."""
    val_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    magnitude: QualitativeValue = QualitativeValue.ZERO
    derivative: QualitativeDirection = QualitativeDirection.STEADY

    def __str__(self):
        mag_sym = {
            QualitativeValue.NEGATIVE: "-",
            QualitativeValue.ZERO: "0",
            QualitativeValue.POSITIVE: "+"
        }
        der_sym = {
            QualitativeDirection.DECREASING: "↓",
            QualitativeDirection.STEADY: "→",
            QualitativeDirection.INCREASING: "↑"
        }
        return f"({mag_sym[self.magnitude]}, {der_sym[self.derivative]})"


@dataclass
class Quantity:
    """A qualitative quantity."""
    qty_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    value: QValue = field(default_factory=QValue)
    quantity_space: List[str] = field(default_factory=list)  # Ordered landmarks
    current_interval: Optional[int] = None


@dataclass
class QualitativeRelation:
    """A qualitative relation between quantities."""
    rel_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    relation_type: RelationType = RelationType.PROPORTIONAL
    source: str = ""  # Quantity name
    target: str = ""  # Quantity name
    strength: float = 1.0


@dataclass
class QualitativeState:
    """A qualitative state of the system."""
    state_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    quantities: Dict[str, QValue] = field(default_factory=dict)
    timestamp: int = 0


@dataclass
class Transition:
    """A transition between states."""
    trans_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    from_state: str = ""
    to_state: str = ""
    transition_type: TransitionType = TransitionType.CONTINUOUS
    reason: str = ""


@dataclass
class Behavior:
    """A qualitative behavior (sequence of states)."""
    behavior_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    states: List[str] = field(default_factory=list)
    behavior_type: BehaviorType = BehaviorType.EQUILIBRIUM


# =============================================================================
# QUALITATIVE VALUE OPERATIONS
# =============================================================================

class QualitativeArithmetic:
    """Qualitative arithmetic operations."""

    @staticmethod
    def add(v1: QualitativeValue, v2: QualitativeValue) -> Set[QualitativeValue]:
        """Add two qualitative values (returns set of possible results)."""
        if v1 == QualitativeValue.ZERO:
            return {v2}
        if v2 == QualitativeValue.ZERO:
            return {v1}
        if v1 == v2:
            return {v1}  # + + + = +, - + - = -
        # Ambiguous: + + - could be -, 0, or +
        return {QualitativeValue.NEGATIVE, QualitativeValue.ZERO, QualitativeValue.POSITIVE}

    @staticmethod
    def multiply(v1: QualitativeValue, v2: QualitativeValue) -> QualitativeValue:
        """Multiply two qualitative values."""
        if v1 == QualitativeValue.ZERO or v2 == QualitativeValue.ZERO:
            return QualitativeValue.ZERO
        if v1 == v2:
            return QualitativeValue.POSITIVE
        return QualitativeValue.NEGATIVE

    @staticmethod
    def negate(v: QualitativeValue) -> QualitativeValue:
        """Negate a qualitative value."""
        if v == QualitativeValue.POSITIVE:
            return QualitativeValue.NEGATIVE
        if v == QualitativeValue.NEGATIVE:
            return QualitativeValue.POSITIVE
        return QualitativeValue.ZERO

    @staticmethod
    def direction_multiply(
        v: QualitativeValue,
        d: QualitativeDirection
    ) -> QualitativeDirection:
        """Determine how a direction is affected by a value sign."""
        if v == QualitativeValue.ZERO:
            return QualitativeDirection.STEADY
        if v == QualitativeValue.POSITIVE:
            return d
        # Negative value reverses direction
        if d == QualitativeDirection.INCREASING:
            return QualitativeDirection.DECREASING
        if d == QualitativeDirection.DECREASING:
            return QualitativeDirection.INCREASING
        return QualitativeDirection.STEADY


# =============================================================================
# QUANTITY MANAGER
# =============================================================================

class QuantityManager:
    """Manage qualitative quantities."""

    def __init__(self):
        self._quantities: Dict[str, Quantity] = {}

    def create_quantity(
        self,
        name: str,
        initial_magnitude: QualitativeValue = QualitativeValue.ZERO,
        initial_derivative: QualitativeDirection = QualitativeDirection.STEADY,
        quantity_space: Optional[List[str]] = None
    ) -> Quantity:
        """Create a qualitative quantity."""
        value = QValue(
            magnitude=initial_magnitude,
            derivative=initial_derivative
        )

        qty = Quantity(
            name=name,
            value=value,
            quantity_space=quantity_space or ["min", "zero", "max"],
            current_interval=1 if quantity_space else None
        )

        self._quantities[name] = qty
        return qty

    def get_quantity(self, name: str) -> Optional[Quantity]:
        """Get a quantity by name."""
        return self._quantities.get(name)

    def set_value(
        self,
        name: str,
        magnitude: QualitativeValue,
        derivative: QualitativeDirection
    ) -> bool:
        """Set quantity value."""
        qty = self._quantities.get(name)
        if qty:
            qty.value.magnitude = magnitude
            qty.value.derivative = derivative
            return True
        return False

    def all_quantities(self) -> List[Quantity]:
        """Get all quantities."""
        return list(self._quantities.values())


# =============================================================================
# RELATION MANAGER
# =============================================================================

class RelationManager:
    """Manage qualitative relations."""

    def __init__(self):
        self._relations: List[QualitativeRelation] = []

    def add_proportional(
        self,
        source: str,
        target: str,
        strength: float = 1.0
    ) -> QualitativeRelation:
        """Add M+ relation: when source increases, target increases."""
        rel = QualitativeRelation(
            relation_type=RelationType.PROPORTIONAL,
            source=source,
            target=target,
            strength=strength
        )
        self._relations.append(rel)
        return rel

    def add_inverse(
        self,
        source: str,
        target: str,
        strength: float = 1.0
    ) -> QualitativeRelation:
        """Add M- relation: when source increases, target decreases."""
        rel = QualitativeRelation(
            relation_type=RelationType.INVERSE,
            source=source,
            target=target,
            strength=strength
        )
        self._relations.append(rel)
        return rel

    def add_influence_plus(
        self,
        source: str,
        target: str,
        strength: float = 1.0
    ) -> QualitativeRelation:
        """Add I+ relation: source value adds to target derivative."""
        rel = QualitativeRelation(
            relation_type=RelationType.INFLUENCE_PLUS,
            source=source,
            target=target,
            strength=strength
        )
        self._relations.append(rel)
        return rel

    def add_influence_minus(
        self,
        source: str,
        target: str,
        strength: float = 1.0
    ) -> QualitativeRelation:
        """Add I- relation: source value subtracts from target derivative."""
        rel = QualitativeRelation(
            relation_type=RelationType.INFLUENCE_MINUS,
            source=source,
            target=target,
            strength=strength
        )
        self._relations.append(rel)
        return rel

    def get_influences_on(self, target: str) -> List[QualitativeRelation]:
        """Get all influences on a quantity."""
        return [r for r in self._relations
                if r.target == target and r.relation_type in
                [RelationType.INFLUENCE_PLUS, RelationType.INFLUENCE_MINUS]]

    def get_proportionals_on(self, target: str) -> List[QualitativeRelation]:
        """Get all proportional relations targeting a quantity."""
        return [r for r in self._relations
                if r.target == target and r.relation_type in
                [RelationType.PROPORTIONAL, RelationType.INVERSE]]

    def all_relations(self) -> List[QualitativeRelation]:
        """Get all relations."""
        return self._relations.copy()


# =============================================================================
# QUALITATIVE SIMULATOR
# =============================================================================

class QualitativeSimulator:
    """Simulate qualitative behavior."""

    def __init__(
        self,
        quantity_manager: QuantityManager,
        relation_manager: RelationManager
    ):
        self._quantities = quantity_manager
        self._relations = relation_manager
        self._states: Dict[str, QualitativeState] = {}
        self._transitions: List[Transition] = []

    def get_current_state(self) -> QualitativeState:
        """Get current qualitative state."""
        state = QualitativeState(timestamp=len(self._states))

        for qty in self._quantities.all_quantities():
            state.quantities[qty.name] = copy.deepcopy(qty.value)

        self._states[state.state_id] = state
        return state

    def compute_derivatives(self) -> Dict[str, Set[QualitativeDirection]]:
        """Compute derivatives based on influences."""
        results: Dict[str, Set[QualitativeDirection]] = {}

        for qty in self._quantities.all_quantities():
            influences = self._relations.get_influences_on(qty.name)

            if not influences:
                results[qty.name] = {qty.value.derivative}
                continue

            # Combine influences
            combined: Set[QualitativeValue] = {QualitativeValue.ZERO}

            for inf in influences:
                source = self._quantities.get_quantity(inf.source)
                if not source:
                    continue

                contribution = source.value.magnitude

                if inf.relation_type == RelationType.INFLUENCE_MINUS:
                    contribution = QualitativeArithmetic.negate(contribution)

                new_combined: Set[QualitativeValue] = set()
                for existing in combined:
                    new_combined |= QualitativeArithmetic.add(existing, contribution)
                combined = new_combined

            # Convert to directions
            directions: Set[QualitativeDirection] = set()
            for val in combined:
                if val == QualitativeValue.POSITIVE:
                    directions.add(QualitativeDirection.INCREASING)
                elif val == QualitativeValue.NEGATIVE:
                    directions.add(QualitativeDirection.DECREASING)
                else:
                    directions.add(QualitativeDirection.STEADY)

            results[qty.name] = directions

        return results

    def step(self) -> Optional[QualitativeState]:
        """Perform one simulation step."""
        old_state = self.get_current_state()

        # Compute new derivatives
        new_derivatives = self.compute_derivatives()

        # Apply changes
        for qty in self._quantities.all_quantities():
            possible = new_derivatives.get(qty.name, {qty.value.derivative})

            # Pick one (deterministic: first in order)
            for d in [QualitativeDirection.DECREASING,
                      QualitativeDirection.STEADY,
                      QualitativeDirection.INCREASING]:
                if d in possible:
                    new_der = d
                    break

            # Update magnitude based on derivative
            if qty.value.derivative == QualitativeDirection.INCREASING:
                if qty.value.magnitude == QualitativeValue.NEGATIVE:
                    qty.value.magnitude = QualitativeValue.ZERO
                elif qty.value.magnitude == QualitativeValue.ZERO:
                    qty.value.magnitude = QualitativeValue.POSITIVE

            elif qty.value.derivative == QualitativeDirection.DECREASING:
                if qty.value.magnitude == QualitativeValue.POSITIVE:
                    qty.value.magnitude = QualitativeValue.ZERO
                elif qty.value.magnitude == QualitativeValue.ZERO:
                    qty.value.magnitude = QualitativeValue.NEGATIVE

            # Update derivative
            qty.value.derivative = new_der

        new_state = self.get_current_state()

        # Record transition
        transition = Transition(
            from_state=old_state.state_id,
            to_state=new_state.state_id,
            transition_type=TransitionType.CONTINUOUS
        )
        self._transitions.append(transition)

        return new_state

    def simulate(self, max_steps: int = 10) -> List[QualitativeState]:
        """Run simulation for multiple steps."""
        states = [self.get_current_state()]

        for _ in range(max_steps):
            new_state = self.step()

            # Check for equilibrium (no change)
            if states and self._states_equal(states[-1], new_state):
                break

            states.append(new_state)

        return states

    def _states_equal(
        self,
        s1: QualitativeState,
        s2: QualitativeState
    ) -> bool:
        """Check if two states are qualitatively equal."""
        if set(s1.quantities.keys()) != set(s2.quantities.keys()):
            return False

        for name in s1.quantities:
            v1 = s1.quantities[name]
            v2 = s2.quantities[name]
            if v1.magnitude != v2.magnitude or v1.derivative != v2.derivative:
                return False

        return True


# =============================================================================
# COMPARATIVE ANALYZER
# =============================================================================

class ComparativeAnalyzer:
    """Analyze comparative relationships."""

    def __init__(self, quantity_manager: QuantityManager):
        self._quantities = quantity_manager
        self._comparisons: Dict[Tuple[str, str], QualitativeMagnitude] = {}

    def set_comparison(
        self,
        qty1: str,
        qty2: str,
        comparison: QualitativeMagnitude
    ) -> None:
        """Set a comparison between quantities."""
        self._comparisons[(qty1, qty2)] = comparison

    def get_comparison(
        self,
        qty1: str,
        qty2: str
    ) -> Optional[QualitativeMagnitude]:
        """Get comparison between quantities."""
        return self._comparisons.get((qty1, qty2))

    def infer_transitivity(self) -> List[Tuple[str, str, QualitativeMagnitude]]:
        """Infer new comparisons via transitivity."""
        inferred = []

        for (a, b), ab in self._comparisons.items():
            for (c, d), cd in self._comparisons.items():
                if b == c:
                    # a R b and b R d => can infer a R d
                    ad = self._transitive_compare(ab, cd)
                    if ad and (a, d) not in self._comparisons:
                        self._comparisons[(a, d)] = ad
                        inferred.append((a, d, ad))

        return inferred

    def _transitive_compare(
        self,
        ab: QualitativeMagnitude,
        bc: QualitativeMagnitude
    ) -> Optional[QualitativeMagnitude]:
        """Compute transitive comparison."""
        # Simplistic: only handle clear cases
        order = {
            QualitativeMagnitude.MUCH_LESS: -2,
            QualitativeMagnitude.LESS: -1,
            QualitativeMagnitude.EQUAL: 0,
            QualitativeMagnitude.GREATER: 1,
            QualitativeMagnitude.MUCH_GREATER: 2
        }

        combined = order[ab] + order[bc]

        if combined <= -2:
            return QualitativeMagnitude.MUCH_LESS
        elif combined == -1:
            return QualitativeMagnitude.LESS
        elif combined == 0:
            return QualitativeMagnitude.EQUAL
        elif combined == 1:
            return QualitativeMagnitude.GREATER
        else:
            return QualitativeMagnitude.MUCH_GREATER


# =============================================================================
# TREND ANALYZER
# =============================================================================

class TrendAnalyzer:
    """Analyze qualitative trends."""

    def __init__(self):
        self._history: Dict[str, List[QValue]] = defaultdict(list)

    def record(self, name: str, value: QValue) -> None:
        """Record a value in history."""
        self._history[name].append(copy.deepcopy(value))

    def get_trend(self, name: str) -> BehaviorType:
        """Analyze trend for a quantity."""
        history = self._history.get(name, [])

        if len(history) < 2:
            return BehaviorType.EQUILIBRIUM

        # Check for oscillation
        sign_changes = 0
        for i in range(1, len(history)):
            if history[i].derivative != history[i-1].derivative:
                sign_changes += 1

        if sign_changes >= len(history) / 2:
            return BehaviorType.OSCILLATING

        # Check for consistent trend
        increasing = all(h.derivative == QualitativeDirection.INCREASING
                        for h in history)
        decreasing = all(h.derivative == QualitativeDirection.DECREASING
                        for h in history)
        steady = all(h.derivative == QualitativeDirection.STEADY
                    for h in history)

        if increasing:
            return BehaviorType.INCREASING
        if decreasing:
            return BehaviorType.DECREASING
        if steady:
            return BehaviorType.EQUILIBRIUM

        # Check for asymptotic (derivative reducing)
        if len(history) >= 3:
            # Simplified check
            pass

        return BehaviorType.EQUILIBRIUM

    def clear_history(self, name: Optional[str] = None) -> None:
        """Clear history."""
        if name:
            self._history[name] = []
        else:
            self._history.clear()


# =============================================================================
# QUALITATIVE REASONER
# =============================================================================

class QualitativeReasoner:
    """
    Qualitative Reasoner for BAEL.

    Advanced qualitative reasoning and physics.
    """

    def __init__(self):
        self._quantities = QuantityManager()
        self._relations = RelationManager()
        self._simulator = QualitativeSimulator(self._quantities, self._relations)
        self._comparator = ComparativeAnalyzer(self._quantities)
        self._trends = TrendAnalyzer()
        self._arithmetic = QualitativeArithmetic()

    # -------------------------------------------------------------------------
    # QUANTITY MANAGEMENT
    # -------------------------------------------------------------------------

    def create_quantity(
        self,
        name: str,
        magnitude: QualitativeValue = QualitativeValue.ZERO,
        derivative: QualitativeDirection = QualitativeDirection.STEADY,
        quantity_space: Optional[List[str]] = None
    ) -> Quantity:
        """Create a qualitative quantity."""
        return self._quantities.create_quantity(
            name, magnitude, derivative, quantity_space
        )

    def get_quantity(self, name: str) -> Optional[Quantity]:
        """Get a quantity by name."""
        return self._quantities.get_quantity(name)

    def set_value(
        self,
        name: str,
        magnitude: QualitativeValue,
        derivative: QualitativeDirection
    ) -> bool:
        """Set quantity value."""
        return self._quantities.set_value(name, magnitude, derivative)

    def all_quantities(self) -> List[Quantity]:
        """Get all quantities."""
        return self._quantities.all_quantities()

    # -------------------------------------------------------------------------
    # RELATION MANAGEMENT
    # -------------------------------------------------------------------------

    def add_proportional(
        self,
        source: str,
        target: str,
        strength: float = 1.0
    ) -> QualitativeRelation:
        """Add M+ relation."""
        return self._relations.add_proportional(source, target, strength)

    def add_inverse(
        self,
        source: str,
        target: str,
        strength: float = 1.0
    ) -> QualitativeRelation:
        """Add M- relation."""
        return self._relations.add_inverse(source, target, strength)

    def add_influence_plus(
        self,
        source: str,
        target: str,
        strength: float = 1.0
    ) -> QualitativeRelation:
        """Add I+ relation."""
        return self._relations.add_influence_plus(source, target, strength)

    def add_influence_minus(
        self,
        source: str,
        target: str,
        strength: float = 1.0
    ) -> QualitativeRelation:
        """Add I- relation."""
        return self._relations.add_influence_minus(source, target, strength)

    def all_relations(self) -> List[QualitativeRelation]:
        """Get all relations."""
        return self._relations.all_relations()

    # -------------------------------------------------------------------------
    # ARITHMETIC
    # -------------------------------------------------------------------------

    def add(
        self,
        v1: QualitativeValue,
        v2: QualitativeValue
    ) -> Set[QualitativeValue]:
        """Add qualitative values."""
        return self._arithmetic.add(v1, v2)

    def multiply(
        self,
        v1: QualitativeValue,
        v2: QualitativeValue
    ) -> QualitativeValue:
        """Multiply qualitative values."""
        return self._arithmetic.multiply(v1, v2)

    def negate(self, v: QualitativeValue) -> QualitativeValue:
        """Negate qualitative value."""
        return self._arithmetic.negate(v)

    # -------------------------------------------------------------------------
    # SIMULATION
    # -------------------------------------------------------------------------

    def simulate(self, max_steps: int = 10) -> List[QualitativeState]:
        """Run simulation."""
        return self._simulator.simulate(max_steps)

    def step(self) -> Optional[QualitativeState]:
        """Perform one simulation step."""
        return self._simulator.step()

    def get_current_state(self) -> QualitativeState:
        """Get current state."""
        return self._simulator.get_current_state()

    def compute_derivatives(self) -> Dict[str, Set[QualitativeDirection]]:
        """Compute derivatives based on influences."""
        return self._simulator.compute_derivatives()

    # -------------------------------------------------------------------------
    # COMPARISON
    # -------------------------------------------------------------------------

    def set_comparison(
        self,
        qty1: str,
        qty2: str,
        comparison: QualitativeMagnitude
    ) -> None:
        """Set a comparison between quantities."""
        self._comparator.set_comparison(qty1, qty2, comparison)

    def get_comparison(
        self,
        qty1: str,
        qty2: str
    ) -> Optional[QualitativeMagnitude]:
        """Get comparison between quantities."""
        return self._comparator.get_comparison(qty1, qty2)

    def infer_comparisons(self) -> List[Tuple[str, str, QualitativeMagnitude]]:
        """Infer new comparisons via transitivity."""
        return self._comparator.infer_transitivity()

    # -------------------------------------------------------------------------
    # TREND ANALYSIS
    # -------------------------------------------------------------------------

    def record_value(self, name: str, value: QValue) -> None:
        """Record value for trend analysis."""
        self._trends.record(name, value)

    def get_trend(self, name: str) -> BehaviorType:
        """Get trend for a quantity."""
        return self._trends.get_trend(name)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Qualitative Reasoner."""
    print("=" * 70)
    print("BAEL - QUALITATIVE REASONER DEMO")
    print("Advanced Qualitative Reasoning and Physics")
    print("=" * 70)
    print()

    reasoner = QualitativeReasoner()

    # 1. Create Quantities
    print("1. CREATE QUANTITIES (Container System):")
    print("-" * 40)

    amount = reasoner.create_quantity(
        "amount",
        QualitativeValue.POSITIVE,
        QualitativeDirection.STEADY,
        ["empty", "low", "normal", "high", "full"]
    )

    inflow = reasoner.create_quantity(
        "inflow",
        QualitativeValue.POSITIVE,
        QualitativeDirection.STEADY
    )

    outflow = reasoner.create_quantity(
        "outflow",
        QualitativeValue.ZERO,
        QualitativeDirection.STEADY
    )

    pressure = reasoner.create_quantity(
        "pressure",
        QualitativeValue.ZERO,
        QualitativeDirection.STEADY
    )

    print(f"   amount: {amount.value}")
    print(f"   inflow: {inflow.value}")
    print(f"   outflow: {outflow.value}")
    print(f"   pressure: {pressure.value}")
    print()

    # 2. Add Relations
    print("2. ADD QUALITATIVE RELATIONS:")
    print("-" * 40)

    # Inflow increases amount
    reasoner.add_influence_plus("inflow", "amount")
    print("   I+(inflow, amount): inflow adds to d(amount)/dt")

    # Outflow decreases amount
    reasoner.add_influence_minus("outflow", "amount")
    print("   I-(outflow, amount): outflow subtracts from d(amount)/dt")

    # Amount proportional to pressure
    reasoner.add_proportional("amount", "pressure")
    print("   M+(amount, pressure): amount and pressure move together")

    # Pressure proportional to outflow
    reasoner.add_proportional("pressure", "outflow")
    print("   M+(pressure, outflow): pressure and outflow move together")

    print()

    # 3. Qualitative Arithmetic
    print("3. QUALITATIVE ARITHMETIC:")
    print("-" * 40)

    result = reasoner.add(QualitativeValue.POSITIVE, QualitativeValue.POSITIVE)
    print(f"   (+) + (+) = {[v.value for v in result]}")

    result = reasoner.add(QualitativeValue.POSITIVE, QualitativeValue.NEGATIVE)
    print(f"   (+) + (-) = {[v.value for v in result]} (ambiguous)")

    result = reasoner.multiply(QualitativeValue.POSITIVE, QualitativeValue.NEGATIVE)
    print(f"   (+) × (-) = {result.value}")

    neg = reasoner.negate(QualitativeValue.POSITIVE)
    print(f"   -(+) = {neg.value}")
    print()

    # 4. Compute Derivatives
    print("4. COMPUTE DERIVATIVES:")
    print("-" * 40)

    derivatives = reasoner.compute_derivatives()
    for qty_name, possible in derivatives.items():
        dirs = [d.value for d in possible]
        print(f"   d({qty_name})/dt: {dirs}")
    print()

    # 5. Simulate
    print("5. QUALITATIVE SIMULATION:")
    print("-" * 40)

    states = reasoner.simulate(max_steps=5)

    for i, state in enumerate(states):
        print(f"   Step {i}:")
        for qty_name, qval in state.quantities.items():
            print(f"      {qty_name}: {qval}")
    print()

    # 6. Comparative Reasoning
    print("6. COMPARATIVE REASONING:")
    print("-" * 40)

    reasoner.set_comparison("inflow", "outflow", QualitativeMagnitude.GREATER)
    reasoner.set_comparison("outflow", "leak", QualitativeMagnitude.GREATER)

    print("   inflow > outflow")
    print("   outflow > leak")

    inferred = reasoner.infer_comparisons()
    for a, b, comp in inferred:
        print(f"   Inferred: {a} {comp.value} {b}")

    direct = reasoner.get_comparison("inflow", "outflow")
    print(f"   Direct comparison (inflow, outflow): {direct.value}")
    print()

    # 7. Trend Analysis
    print("7. TREND ANALYSIS:")
    print("-" * 40)

    # Record some values
    reasoner.record_value("amount", QValue(QualitativeValue.ZERO, QualitativeDirection.INCREASING))
    reasoner.record_value("amount", QValue(QualitativeValue.POSITIVE, QualitativeDirection.INCREASING))
    reasoner.record_value("amount", QValue(QualitativeValue.POSITIVE, QualitativeDirection.INCREASING))

    trend = reasoner.get_trend("amount")
    print(f"   amount trend: {trend.value}")

    # Oscillating pattern
    reasoner.record_value("pressure", QValue(QualitativeValue.POSITIVE, QualitativeDirection.INCREASING))
    reasoner.record_value("pressure", QValue(QualitativeValue.POSITIVE, QualitativeDirection.DECREASING))
    reasoner.record_value("pressure", QValue(QualitativeValue.POSITIVE, QualitativeDirection.INCREASING))
    reasoner.record_value("pressure", QValue(QualitativeValue.POSITIVE, QualitativeDirection.DECREASING))

    trend = reasoner.get_trend("pressure")
    print(f"   pressure trend: {trend.value}")
    print()

    # 8. New System: Thermostat
    print("8. THERMOSTAT EXAMPLE:")
    print("-" * 40)

    thermo = QualitativeReasoner()

    temp = thermo.create_quantity("temperature", QualitativeValue.NEGATIVE, QualitativeDirection.STEADY)
    heat = thermo.create_quantity("heat_flow", QualitativeValue.POSITIVE, QualitativeDirection.STEADY)
    target = thermo.create_quantity("target", QualitativeValue.ZERO, QualitativeDirection.STEADY)

    # Heat increases temperature
    thermo.add_influence_plus("heat_flow", "temperature")

    print(f"   Initial: temp={temp.value}, heat={heat.value}")

    # Simulate
    for i in range(4):
        state = thermo.step()
        t = state.quantities.get("temperature")
        print(f"   Step {i+1}: temperature={t}")
    print()

    # 9. Quantity Spaces
    print("9. QUANTITY SPACES:")
    print("-" * 40)

    level = reasoner.get_quantity("amount")
    print(f"   amount quantity space: {level.quantity_space}")
    print(f"   Landmarks define qualitative intervals")
    print()

    # 10. All Relations
    print("10. SYSTEM RELATIONS:")
    print("-" * 40)

    relations = reasoner.all_relations()
    for rel in relations:
        rel_sym = {
            RelationType.PROPORTIONAL: "M+",
            RelationType.INVERSE: "M-",
            RelationType.INFLUENCE_PLUS: "I+",
            RelationType.INFLUENCE_MINUS: "I-"
        }
        print(f"   {rel_sym[rel.relation_type]}({rel.source}, {rel.target})")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Qualitative Reasoner Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
