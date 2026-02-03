#!/usr/bin/env python3
"""
BAEL - Fuzzy Reasoner
Advanced fuzzy logic reasoning and approximate reasoning.

Features:
- Fuzzy set operations
- Membership functions
- Fuzzy rules
- Defuzzification
- Fuzzy inference
- Linguistic variables
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

class MembershipType(Enum):
    """Types of membership functions."""
    TRIANGULAR = "triangular"
    TRAPEZOIDAL = "trapezoidal"
    GAUSSIAN = "gaussian"
    SINGLETON = "singleton"
    SIGMOID = "sigmoid"
    PI_SHAPED = "pi_shaped"
    S_SHAPED = "s_shaped"
    Z_SHAPED = "z_shaped"


class DefuzzMethod(Enum):
    """Defuzzification methods."""
    CENTROID = "centroid"
    BISECTOR = "bisector"
    MOM = "mom"  # Mean of Maximum
    SOM = "som"  # Smallest of Maximum
    LOM = "lom"  # Largest of Maximum


class HedgeType(Enum):
    """Linguistic hedges."""
    VERY = "very"
    SOMEWHAT = "somewhat"
    SLIGHTLY = "slightly"
    EXTREMELY = "extremely"
    NOT = "not"


class TNormType(Enum):
    """T-norm types for fuzzy AND."""
    MIN = "min"
    PRODUCT = "product"
    LUKASIEWICZ = "lukasiewicz"
    DRASTIC = "drastic"


class SNormType(Enum):
    """S-norm types for fuzzy OR."""
    MAX = "max"
    PROBABILISTIC = "probabilistic"
    LUKASIEWICZ = "lukasiewicz"
    DRASTIC = "drastic"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class FuzzySet:
    """A fuzzy set with membership function."""
    set_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    membership_type: MembershipType = MembershipType.TRIANGULAR
    parameters: Dict[str, float] = field(default_factory=dict)
    universe_min: float = 0.0
    universe_max: float = 1.0


@dataclass
class LinguisticVariable:
    """A linguistic variable with term set."""
    var_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    universe_min: float = 0.0
    universe_max: float = 1.0
    terms: Dict[str, str] = field(default_factory=dict)  # term_name -> set_id


@dataclass
class FuzzyRule:
    """A fuzzy rule (IF-THEN)."""
    rule_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    antecedent: List[Tuple[str, str]] = field(default_factory=list)  # [(var_id, term)]
    consequent: Tuple[str, str] = field(default_factory=tuple)  # (var_id, term)
    weight: float = 1.0
    operator: str = "AND"  # AND or OR


@dataclass
class FuzzyValue:
    """A fuzzified value."""
    value_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    crisp_value: float = 0.0
    memberships: Dict[str, float] = field(default_factory=dict)  # term -> degree


@dataclass
class InferenceResult:
    """Result of fuzzy inference."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    output_variable: str = ""
    fuzzy_output: Dict[str, float] = field(default_factory=dict)
    crisp_output: float = 0.0
    fired_rules: List[str] = field(default_factory=list)


# =============================================================================
# MEMBERSHIP FUNCTIONS
# =============================================================================

class MembershipFunction:
    """Membership function calculator."""

    @staticmethod
    def triangular(x: float, a: float, b: float, c: float) -> float:
        """Triangular membership function."""
        if x <= a or x >= c:
            return 0.0
        elif a < x <= b:
            return (x - a) / (b - a) if b != a else 1.0
        else:  # b < x < c
            return (c - x) / (c - b) if c != b else 1.0

    @staticmethod
    def trapezoidal(x: float, a: float, b: float, c: float, d: float) -> float:
        """Trapezoidal membership function."""
        if x <= a or x >= d:
            return 0.0
        elif a < x < b:
            return (x - a) / (b - a) if b != a else 1.0
        elif b <= x <= c:
            return 1.0
        else:  # c < x < d
            return (d - x) / (d - c) if d != c else 1.0

    @staticmethod
    def gaussian(x: float, mean: float, sigma: float) -> float:
        """Gaussian membership function."""
        if sigma == 0:
            return 1.0 if x == mean else 0.0
        return math.exp(-0.5 * ((x - mean) / sigma) ** 2)

    @staticmethod
    def singleton(x: float, center: float, tolerance: float = 0.001) -> float:
        """Singleton membership function."""
        return 1.0 if abs(x - center) < tolerance else 0.0

    @staticmethod
    def sigmoid(x: float, center: float, slope: float) -> float:
        """Sigmoid membership function."""
        return 1.0 / (1.0 + math.exp(-slope * (x - center)))

    @staticmethod
    def s_shaped(x: float, a: float, b: float) -> float:
        """S-shaped membership function."""
        if x <= a:
            return 0.0
        elif x >= b:
            return 1.0
        elif x <= (a + b) / 2:
            return 2 * ((x - a) / (b - a)) ** 2
        else:
            return 1 - 2 * ((x - b) / (b - a)) ** 2

    @staticmethod
    def z_shaped(x: float, a: float, b: float) -> float:
        """Z-shaped membership function."""
        return 1.0 - MembershipFunction.s_shaped(x, a, b)

    @staticmethod
    def pi_shaped(x: float, a: float, b: float, c: float, d: float) -> float:
        """Pi-shaped membership function."""
        if x <= a or x >= d:
            return 0.0
        elif x < b:
            return MembershipFunction.s_shaped(x, a, b)
        elif x <= c:
            return 1.0
        else:
            return MembershipFunction.z_shaped(x, c, d)


# =============================================================================
# FUZZY SET MANAGER
# =============================================================================

class FuzzySetManager:
    """Manage fuzzy sets."""

    def __init__(self):
        self._sets: Dict[str, FuzzySet] = {}
        self._membership = MembershipFunction()

    def create_set(
        self,
        name: str,
        membership_type: MembershipType,
        parameters: Dict[str, float],
        universe_min: float = 0.0,
        universe_max: float = 1.0
    ) -> FuzzySet:
        """Create a fuzzy set."""
        fuzzy_set = FuzzySet(
            name=name,
            membership_type=membership_type,
            parameters=parameters,
            universe_min=universe_min,
            universe_max=universe_max
        )
        self._sets[fuzzy_set.set_id] = fuzzy_set
        return fuzzy_set

    def get_membership(self, set_id: str, x: float) -> float:
        """Get membership degree for a value."""
        fs = self._sets.get(set_id)
        if not fs:
            return 0.0

        params = fs.parameters

        if fs.membership_type == MembershipType.TRIANGULAR:
            return self._membership.triangular(
                x, params.get('a', 0), params.get('b', 0.5), params.get('c', 1)
            )
        elif fs.membership_type == MembershipType.TRAPEZOIDAL:
            return self._membership.trapezoidal(
                x, params.get('a', 0), params.get('b', 0.25),
                params.get('c', 0.75), params.get('d', 1)
            )
        elif fs.membership_type == MembershipType.GAUSSIAN:
            return self._membership.gaussian(
                x, params.get('mean', 0.5), params.get('sigma', 0.2)
            )
        elif fs.membership_type == MembershipType.SINGLETON:
            return self._membership.singleton(
                x, params.get('center', 0.5), params.get('tolerance', 0.001)
            )
        elif fs.membership_type == MembershipType.SIGMOID:
            return self._membership.sigmoid(
                x, params.get('center', 0.5), params.get('slope', 10)
            )
        elif fs.membership_type == MembershipType.S_SHAPED:
            return self._membership.s_shaped(
                x, params.get('a', 0), params.get('b', 1)
            )
        elif fs.membership_type == MembershipType.Z_SHAPED:
            return self._membership.z_shaped(
                x, params.get('a', 0), params.get('b', 1)
            )
        elif fs.membership_type == MembershipType.PI_SHAPED:
            return self._membership.pi_shaped(
                x, params.get('a', 0), params.get('b', 0.25),
                params.get('c', 0.75), params.get('d', 1)
            )

        return 0.0

    def get_set(self, set_id: str) -> Optional[FuzzySet]:
        """Get a fuzzy set."""
        return self._sets.get(set_id)

    def apply_hedge(
        self,
        membership: float,
        hedge: HedgeType
    ) -> float:
        """Apply linguistic hedge to membership."""
        if hedge == HedgeType.VERY:
            return membership ** 2
        elif hedge == HedgeType.SOMEWHAT:
            return math.sqrt(membership)
        elif hedge == HedgeType.SLIGHTLY:
            return math.sqrt(membership) - membership
        elif hedge == HedgeType.EXTREMELY:
            return membership ** 3
        elif hedge == HedgeType.NOT:
            return 1.0 - membership
        return membership


# =============================================================================
# LINGUISTIC VARIABLE MANAGER
# =============================================================================

class LinguisticVariableManager:
    """Manage linguistic variables."""

    def __init__(self, set_manager: FuzzySetManager):
        self._variables: Dict[str, LinguisticVariable] = {}
        self._sets = set_manager

    def create_variable(
        self,
        name: str,
        universe_min: float = 0.0,
        universe_max: float = 1.0
    ) -> LinguisticVariable:
        """Create a linguistic variable."""
        var = LinguisticVariable(
            name=name,
            universe_min=universe_min,
            universe_max=universe_max
        )
        self._variables[var.var_id] = var
        return var

    def add_term(
        self,
        var_id: str,
        term_name: str,
        membership_type: MembershipType,
        parameters: Dict[str, float]
    ) -> Optional[FuzzySet]:
        """Add a term to a linguistic variable."""
        var = self._variables.get(var_id)
        if not var:
            return None

        # Create fuzzy set for term
        fs = self._sets.create_set(
            term_name,
            membership_type,
            parameters,
            var.universe_min,
            var.universe_max
        )

        var.terms[term_name] = fs.set_id
        return fs

    def get_variable(self, var_id: str) -> Optional[LinguisticVariable]:
        """Get a linguistic variable."""
        return self._variables.get(var_id)

    def fuzzify(
        self,
        var_id: str,
        crisp_value: float
    ) -> FuzzyValue:
        """Fuzzify a crisp value."""
        var = self._variables.get(var_id)
        memberships = {}

        if var:
            for term_name, set_id in var.terms.items():
                membership = self._sets.get_membership(set_id, crisp_value)
                if membership > 0:
                    memberships[term_name] = membership

        return FuzzyValue(
            crisp_value=crisp_value,
            memberships=memberships
        )


# =============================================================================
# FUZZY OPERATORS
# =============================================================================

class FuzzyOperators:
    """Fuzzy logic operators."""

    def __init__(
        self,
        t_norm: TNormType = TNormType.MIN,
        s_norm: SNormType = SNormType.MAX
    ):
        self._t_norm = t_norm
        self._s_norm = s_norm

    def fuzzy_and(self, a: float, b: float) -> float:
        """Fuzzy AND (T-norm)."""
        if self._t_norm == TNormType.MIN:
            return min(a, b)
        elif self._t_norm == TNormType.PRODUCT:
            return a * b
        elif self._t_norm == TNormType.LUKASIEWICZ:
            return max(0, a + b - 1)
        elif self._t_norm == TNormType.DRASTIC:
            if a == 1:
                return b
            elif b == 1:
                return a
            return 0.0
        return min(a, b)

    def fuzzy_or(self, a: float, b: float) -> float:
        """Fuzzy OR (S-norm)."""
        if self._s_norm == SNormType.MAX:
            return max(a, b)
        elif self._s_norm == SNormType.PROBABILISTIC:
            return a + b - a * b
        elif self._s_norm == SNormType.LUKASIEWICZ:
            return min(1, a + b)
        elif self._s_norm == SNormType.DRASTIC:
            if a == 0:
                return b
            elif b == 0:
                return a
            return 1.0
        return max(a, b)

    def fuzzy_not(self, a: float) -> float:
        """Fuzzy NOT (complement)."""
        return 1.0 - a

    def fuzzy_implies(self, a: float, b: float) -> float:
        """Fuzzy implication (Mamdani)."""
        return min(a, b)

    def aggregate(
        self,
        values: List[float],
        operation: str = "AND"
    ) -> float:
        """Aggregate multiple values."""
        if not values:
            return 0.0

        result = values[0]
        for v in values[1:]:
            if operation == "AND":
                result = self.fuzzy_and(result, v)
            else:
                result = self.fuzzy_or(result, v)

        return result


# =============================================================================
# RULE ENGINE
# =============================================================================

class FuzzyRuleEngine:
    """Fuzzy rule engine."""

    def __init__(
        self,
        var_manager: LinguisticVariableManager,
        operators: FuzzyOperators
    ):
        self._variables = var_manager
        self._operators = operators
        self._rules: Dict[str, FuzzyRule] = {}

    def create_rule(
        self,
        antecedent: List[Tuple[str, str]],
        consequent: Tuple[str, str],
        weight: float = 1.0,
        operator: str = "AND"
    ) -> FuzzyRule:
        """Create a fuzzy rule."""
        rule = FuzzyRule(
            antecedent=antecedent,
            consequent=consequent,
            weight=weight,
            operator=operator
        )
        self._rules[rule.rule_id] = rule
        return rule

    def evaluate_rule(
        self,
        rule: FuzzyRule,
        inputs: Dict[str, float]
    ) -> Tuple[float, str]:
        """Evaluate a rule and return firing strength."""
        # Get membership values for antecedent
        memberships = []

        for var_id, term in rule.antecedent:
            var = self._variables.get_variable(var_id)
            if var and var_id in inputs:
                fuzzy_val = self._variables.fuzzify(var_id, inputs[var_id])
                membership = fuzzy_val.memberships.get(term, 0.0)
                memberships.append(membership)

        if not memberships:
            return 0.0, rule.consequent[1]

        # Aggregate antecedent memberships
        firing_strength = self._operators.aggregate(memberships, rule.operator)
        firing_strength *= rule.weight

        return firing_strength, rule.consequent[1]

    def get_rules(self) -> List[FuzzyRule]:
        """Get all rules."""
        return list(self._rules.values())


# =============================================================================
# DEFUZZIFIER
# =============================================================================

class Defuzzifier:
    """Defuzzification module."""

    def __init__(
        self,
        var_manager: LinguisticVariableManager,
        set_manager: FuzzySetManager
    ):
        self._variables = var_manager
        self._sets = set_manager

    def defuzzify(
        self,
        var_id: str,
        fuzzy_output: Dict[str, float],
        method: DefuzzMethod = DefuzzMethod.CENTROID,
        num_samples: int = 100
    ) -> float:
        """Defuzzify a fuzzy output."""
        var = self._variables.get_variable(var_id)
        if not var:
            return 0.0

        # Generate universe samples
        step = (var.universe_max - var.universe_min) / num_samples
        universe = [var.universe_min + i * step for i in range(num_samples + 1)]

        # Calculate aggregated membership for each point
        aggregated = []
        for x in universe:
            max_membership = 0.0
            for term, strength in fuzzy_output.items():
                if term in var.terms:
                    set_id = var.terms[term]
                    membership = self._sets.get_membership(set_id, x)
                    clipped = min(membership, strength)
                    max_membership = max(max_membership, clipped)
            aggregated.append((x, max_membership))

        if method == DefuzzMethod.CENTROID:
            return self._centroid(aggregated)
        elif method == DefuzzMethod.BISECTOR:
            return self._bisector(aggregated)
        elif method == DefuzzMethod.MOM:
            return self._mom(aggregated)
        elif method == DefuzzMethod.SOM:
            return self._som(aggregated)
        elif method == DefuzzMethod.LOM:
            return self._lom(aggregated)

        return self._centroid(aggregated)

    def _centroid(self, aggregated: List[Tuple[float, float]]) -> float:
        """Centroid defuzzification."""
        numerator = sum(x * m for x, m in aggregated)
        denominator = sum(m for _, m in aggregated)
        return numerator / denominator if denominator > 0 else 0.0

    def _bisector(self, aggregated: List[Tuple[float, float]]) -> float:
        """Bisector defuzzification."""
        total_area = sum(m for _, m in aggregated)
        if total_area == 0:
            return 0.0

        half_area = total_area / 2
        cumulative = 0.0

        for x, m in aggregated:
            cumulative += m
            if cumulative >= half_area:
                return x

        return aggregated[-1][0] if aggregated else 0.0

    def _mom(self, aggregated: List[Tuple[float, float]]) -> float:
        """Mean of Maximum defuzzification."""
        max_membership = max(m for _, m in aggregated) if aggregated else 0
        maximums = [x for x, m in aggregated if m == max_membership]
        return sum(maximums) / len(maximums) if maximums else 0.0

    def _som(self, aggregated: List[Tuple[float, float]]) -> float:
        """Smallest of Maximum defuzzification."""
        max_membership = max(m for _, m in aggregated) if aggregated else 0
        maximums = [x for x, m in aggregated if m == max_membership]
        return min(maximums) if maximums else 0.0

    def _lom(self, aggregated: List[Tuple[float, float]]) -> float:
        """Largest of Maximum defuzzification."""
        max_membership = max(m for _, m in aggregated) if aggregated else 0
        maximums = [x for x, m in aggregated if m == max_membership]
        return max(maximums) if maximums else 0.0


# =============================================================================
# FUZZY INFERENCE SYSTEM
# =============================================================================

class FuzzyInferenceSystem:
    """Fuzzy inference system."""

    def __init__(
        self,
        rule_engine: FuzzyRuleEngine,
        defuzzifier: Defuzzifier
    ):
        self._rules = rule_engine
        self._defuzzifier = defuzzifier

    def infer(
        self,
        inputs: Dict[str, float],
        output_var_id: str,
        defuzz_method: DefuzzMethod = DefuzzMethod.CENTROID
    ) -> InferenceResult:
        """Perform fuzzy inference."""
        fuzzy_output: Dict[str, float] = {}
        fired_rules = []

        # Evaluate all rules
        for rule in self._rules.get_rules():
            if rule.consequent[0] == output_var_id:
                strength, term = self._rules.evaluate_rule(rule, inputs)

                if strength > 0:
                    fired_rules.append(rule.rule_id)

                    # Aggregate output (max aggregation)
                    if term in fuzzy_output:
                        fuzzy_output[term] = max(fuzzy_output[term], strength)
                    else:
                        fuzzy_output[term] = strength

        # Defuzzify
        crisp_output = self._defuzzifier.defuzzify(
            output_var_id, fuzzy_output, defuzz_method
        )

        return InferenceResult(
            output_variable=output_var_id,
            fuzzy_output=fuzzy_output,
            crisp_output=crisp_output,
            fired_rules=fired_rules
        )


# =============================================================================
# FUZZY REASONER
# =============================================================================

class FuzzyReasoner:
    """
    Fuzzy Reasoner for BAEL.

    Advanced fuzzy logic reasoning and approximate reasoning.
    """

    def __init__(
        self,
        t_norm: TNormType = TNormType.MIN,
        s_norm: SNormType = SNormType.MAX
    ):
        self._set_manager = FuzzySetManager()
        self._var_manager = LinguisticVariableManager(self._set_manager)
        self._operators = FuzzyOperators(t_norm, s_norm)
        self._rule_engine = FuzzyRuleEngine(self._var_manager, self._operators)
        self._defuzzifier = Defuzzifier(self._var_manager, self._set_manager)
        self._fis = FuzzyInferenceSystem(self._rule_engine, self._defuzzifier)

    # -------------------------------------------------------------------------
    # FUZZY SETS
    # -------------------------------------------------------------------------

    def create_fuzzy_set(
        self,
        name: str,
        membership_type: MembershipType,
        parameters: Dict[str, float],
        universe_min: float = 0.0,
        universe_max: float = 1.0
    ) -> FuzzySet:
        """Create a fuzzy set."""
        return self._set_manager.create_set(
            name, membership_type, parameters, universe_min, universe_max
        )

    def get_membership(self, set_id: str, x: float) -> float:
        """Get membership degree."""
        return self._set_manager.get_membership(set_id, x)

    def apply_hedge(self, membership: float, hedge: HedgeType) -> float:
        """Apply linguistic hedge."""
        return self._set_manager.apply_hedge(membership, hedge)

    # -------------------------------------------------------------------------
    # LINGUISTIC VARIABLES
    # -------------------------------------------------------------------------

    def create_variable(
        self,
        name: str,
        universe_min: float = 0.0,
        universe_max: float = 1.0
    ) -> LinguisticVariable:
        """Create a linguistic variable."""
        return self._var_manager.create_variable(name, universe_min, universe_max)

    def add_term(
        self,
        var_id: str,
        term_name: str,
        membership_type: MembershipType,
        parameters: Dict[str, float]
    ) -> Optional[FuzzySet]:
        """Add a term to a variable."""
        return self._var_manager.add_term(
            var_id, term_name, membership_type, parameters
        )

    def fuzzify(self, var_id: str, crisp_value: float) -> FuzzyValue:
        """Fuzzify a crisp value."""
        return self._var_manager.fuzzify(var_id, crisp_value)

    # -------------------------------------------------------------------------
    # FUZZY RULES
    # -------------------------------------------------------------------------

    def create_rule(
        self,
        antecedent: List[Tuple[str, str]],
        consequent: Tuple[str, str],
        weight: float = 1.0,
        operator: str = "AND"
    ) -> FuzzyRule:
        """Create a fuzzy rule."""
        return self._rule_engine.create_rule(
            antecedent, consequent, weight, operator
        )

    def get_rules(self) -> List[FuzzyRule]:
        """Get all rules."""
        return self._rule_engine.get_rules()

    # -------------------------------------------------------------------------
    # FUZZY OPERATIONS
    # -------------------------------------------------------------------------

    def fuzzy_and(self, a: float, b: float) -> float:
        """Fuzzy AND."""
        return self._operators.fuzzy_and(a, b)

    def fuzzy_or(self, a: float, b: float) -> float:
        """Fuzzy OR."""
        return self._operators.fuzzy_or(a, b)

    def fuzzy_not(self, a: float) -> float:
        """Fuzzy NOT."""
        return self._operators.fuzzy_not(a)

    # -------------------------------------------------------------------------
    # INFERENCE
    # -------------------------------------------------------------------------

    def infer(
        self,
        inputs: Dict[str, float],
        output_var_id: str,
        defuzz_method: DefuzzMethod = DefuzzMethod.CENTROID
    ) -> InferenceResult:
        """Perform fuzzy inference."""
        return self._fis.infer(inputs, output_var_id, defuzz_method)

    def defuzzify(
        self,
        var_id: str,
        fuzzy_output: Dict[str, float],
        method: DefuzzMethod = DefuzzMethod.CENTROID
    ) -> float:
        """Defuzzify a fuzzy output."""
        return self._defuzzifier.defuzzify(var_id, fuzzy_output, method)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Fuzzy Reasoner."""
    print("=" * 70)
    print("BAEL - FUZZY REASONER DEMO")
    print("Advanced Fuzzy Logic Reasoning")
    print("=" * 70)
    print()

    reasoner = FuzzyReasoner()

    # 1. Create Linguistic Variables
    print("1. CREATE LINGUISTIC VARIABLES:")
    print("-" * 40)

    # Temperature variable
    temp = reasoner.create_variable("Temperature", 0.0, 100.0)

    reasoner.add_term(
        temp.var_id, "Cold",
        MembershipType.TRAPEZOIDAL,
        {'a': 0, 'b': 0, 'c': 20, 'd': 30}
    )

    reasoner.add_term(
        temp.var_id, "Warm",
        MembershipType.TRIANGULAR,
        {'a': 20, 'b': 40, 'c': 60}
    )

    reasoner.add_term(
        temp.var_id, "Hot",
        MembershipType.TRAPEZOIDAL,
        {'a': 50, 'b': 70, 'c': 100, 'd': 100}
    )

    print(f"   Variable: {temp.name} (0-100)")
    print(f"   Terms: Cold, Warm, Hot")

    # Humidity variable
    humidity = reasoner.create_variable("Humidity", 0.0, 100.0)

    reasoner.add_term(
        humidity.var_id, "Low",
        MembershipType.TRAPEZOIDAL,
        {'a': 0, 'b': 0, 'c': 30, 'd': 40}
    )

    reasoner.add_term(
        humidity.var_id, "Medium",
        MembershipType.TRIANGULAR,
        {'a': 30, 'b': 50, 'c': 70}
    )

    reasoner.add_term(
        humidity.var_id, "High",
        MembershipType.TRAPEZOIDAL,
        {'a': 60, 'b': 80, 'c': 100, 'd': 100}
    )

    print(f"   Variable: {humidity.name} (0-100)")
    print(f"   Terms: Low, Medium, High")

    # Fan Speed (output)
    fan = reasoner.create_variable("FanSpeed", 0.0, 100.0)

    reasoner.add_term(
        fan.var_id, "Low",
        MembershipType.TRIANGULAR,
        {'a': 0, 'b': 0, 'c': 40}
    )

    reasoner.add_term(
        fan.var_id, "Medium",
        MembershipType.TRIANGULAR,
        {'a': 20, 'b': 50, 'c': 80}
    )

    reasoner.add_term(
        fan.var_id, "High",
        MembershipType.TRIANGULAR,
        {'a': 60, 'b': 100, 'c': 100}
    )

    print(f"   Variable: {fan.name} (0-100)")
    print(f"   Terms: Low, Medium, High")
    print()

    # 2. Fuzzification
    print("2. FUZZIFICATION:")
    print("-" * 40)

    temp_value = 35.0
    fuzzy_temp = reasoner.fuzzify(temp.var_id, temp_value)

    print(f"   Temperature = {temp_value}°C")
    print(f"   Memberships:")
    for term, degree in fuzzy_temp.memberships.items():
        print(f"     {term}: {degree:.2f}")
    print()

    # 3. Create Fuzzy Rules
    print("3. CREATE FUZZY RULES:")
    print("-" * 40)

    # Rule 1: IF temp is Cold AND humidity is Low THEN fan is Low
    rule1 = reasoner.create_rule(
        [(temp.var_id, "Cold"), (humidity.var_id, "Low")],
        (fan.var_id, "Low")
    )

    # Rule 2: IF temp is Warm AND humidity is Medium THEN fan is Medium
    rule2 = reasoner.create_rule(
        [(temp.var_id, "Warm"), (humidity.var_id, "Medium")],
        (fan.var_id, "Medium")
    )

    # Rule 3: IF temp is Hot OR humidity is High THEN fan is High
    rule3 = reasoner.create_rule(
        [(temp.var_id, "Hot"), (humidity.var_id, "High")],
        (fan.var_id, "High"),
        operator="OR"
    )

    # Rule 4: IF temp is Hot AND humidity is High THEN fan is High
    rule4 = reasoner.create_rule(
        [(temp.var_id, "Hot"), (humidity.var_id, "High")],
        (fan.var_id, "High")
    )

    print("   Rule 1: IF Cold AND Low THEN Low")
    print("   Rule 2: IF Warm AND Medium THEN Medium")
    print("   Rule 3: IF Hot OR High THEN High")
    print("   Rule 4: IF Hot AND High THEN High")
    print()

    # 4. Fuzzy Operations
    print("4. FUZZY OPERATIONS:")
    print("-" * 40)

    a, b = 0.7, 0.4
    print(f"   a = {a}, b = {b}")
    print(f"   AND(a, b) = {reasoner.fuzzy_and(a, b):.2f}")
    print(f"   OR(a, b) = {reasoner.fuzzy_or(a, b):.2f}")
    print(f"   NOT(a) = {reasoner.fuzzy_not(a):.2f}")
    print()

    # 5. Linguistic Hedges
    print("5. LINGUISTIC HEDGES:")
    print("-" * 40)

    membership = 0.8
    print(f"   Base membership: {membership}")
    print(f"   VERY: {reasoner.apply_hedge(membership, HedgeType.VERY):.2f}")
    print(f"   SOMEWHAT: {reasoner.apply_hedge(membership, HedgeType.SOMEWHAT):.2f}")
    print(f"   SLIGHTLY: {reasoner.apply_hedge(membership, HedgeType.SLIGHTLY):.2f}")
    print(f"   EXTREMELY: {reasoner.apply_hedge(membership, HedgeType.EXTREMELY):.2f}")
    print(f"   NOT: {reasoner.apply_hedge(membership, HedgeType.NOT):.2f}")
    print()

    # 6. Fuzzy Inference
    print("6. FUZZY INFERENCE:")
    print("-" * 40)

    inputs = {
        temp.var_id: 65.0,  # Hot temperature
        humidity.var_id: 75.0  # High humidity
    }

    result = reasoner.infer(inputs, fan.var_id)

    print(f"   Inputs: Temp={inputs[temp.var_id]}°C, Humidity={inputs[humidity.var_id]}%")
    print(f"   Fuzzy output: {result.fuzzy_output}")
    print(f"   Crisp output: {result.crisp_output:.2f}%")
    print(f"   Fired rules: {len(result.fired_rules)}")
    print()

    # 7. Different Defuzzification Methods
    print("7. DEFUZZIFICATION METHODS:")
    print("-" * 40)

    fuzzy_output = {"Low": 0.2, "Medium": 0.5, "High": 0.8}

    for method in DefuzzMethod:
        value = reasoner.defuzzify(fan.var_id, fuzzy_output, method)
        print(f"   {method.value.upper()}: {value:.2f}")
    print()

    # 8. Multiple Scenarios
    print("8. MULTIPLE SCENARIOS:")
    print("-" * 40)

    scenarios = [
        {"temp": 15.0, "humidity": 30.0, "desc": "Cool and dry"},
        {"temp": 45.0, "humidity": 50.0, "desc": "Warm and moderate"},
        {"temp": 80.0, "humidity": 90.0, "desc": "Hot and humid"},
    ]

    for scenario in scenarios:
        inputs = {
            temp.var_id: scenario["temp"],
            humidity.var_id: scenario["humidity"]
        }
        result = reasoner.infer(inputs, fan.var_id)
        print(f"   {scenario['desc']}: Fan = {result.crisp_output:.1f}%")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Fuzzy Reasoner Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
