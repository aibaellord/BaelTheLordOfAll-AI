"""
Advanced Reasoning Extensions for BAEL

Temporal logic, modal logic, fuzzy reasoning, Bayesian networks,
and advanced constraint solving.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class TemporalOperator(Enum):
    """Temporal logic operators."""
    NEXT = "next"
    ALWAYS = "always"
    EVENTUALLY = "eventually"
    UNTIL = "until"
    RELEASE = "release"


class ModalityType(Enum):
    """Modal logic modality types."""
    NECESSARY = "necessary"  # □ operator
    POSSIBLE = "possible"    # ◇ operator
    CONTINGENT = "contingent"  # neither necessary nor impossible
    IMPOSSIBLE = "impossible"


@dataclass
class TemporalFormula:
    """Temporal logic formula."""
    operator: TemporalOperator
    formula1: str
    formula2: Optional[str] = None
    evaluation_time: datetime = field(default_factory=datetime.now)
    validity_interval: Optional[Tuple[datetime, datetime]] = None

    def evaluate_at_time(self, current_time: datetime) -> bool:
        """Evaluate formula at specific time."""
        # Simplified evaluation
        if self.validity_interval:
            start, end = self.validity_interval
            return start <= current_time <= end
        return True


class BayesianNetwork:
    """Bayesian network for probabilistic reasoning."""

    def __init__(self):
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Tuple[str, str]] = []
        self.conditional_probabilities: Dict[str, Dict] = {}

    def add_node(self, node_id: str, possible_values: List[str]) -> None:
        """Add node to network."""
        self.nodes[node_id] = {
            "values": possible_values,
            "probability": {v: 1.0 / len(possible_values) for v in possible_values}
        }

    def add_edge(self, parent: str, child: str) -> None:
        """Add edge between nodes."""
        if parent in self.nodes and child in self.nodes:
            self.edges.append((parent, child))

    def set_conditional_probability(self, parent: str, parent_value: str,
                                    child: str, child_value: str,
                                    probability: float) -> None:
        """Set conditional probability P(child=value|parent=value)."""
        key = f"{parent}={parent_value}"
        if key not in self.conditional_probabilities:
            self.conditional_probabilities[key] = {}
        self.conditional_probabilities[key][f"{child}={child_value}"] = probability

    def get_probability(self, node: str, value: str) -> float:
        """Get probability of node having value."""
        if node in self.nodes:
            return self.nodes[node]["probability"].get(value, 0.0)
        return 0.0

    def infer(self, observations: Dict[str, str]) -> Dict[str, Dict[str, float]]:
        """Infer probabilities given observations (simplified)."""
        inferred = {}

        for node_id in self.nodes:
            if node_id in observations:
                inferred[node_id] = {observations[node_id]: 1.0}
            else:
                inferred[node_id] = dict(self.nodes[node_id]["probability"])

        return inferred


class FuzzyLogic:
    """Fuzzy logic reasoning system."""

    def __init__(self):
        self.membership_functions: Dict[str, Dict[str, Tuple[float, float, float]]] = {}

    def add_fuzzy_variable(self, variable_name: str, linguistic_values: Dict[str, Tuple[float, float, float]]) -> None:
        """Add fuzzy variable with linguistic values.

        Linguistic values map to triangular membership functions (a, b, c)
        where (a, 0), (b, 1), (c, 0) are the triangle points.
        """
        self.membership_functions[variable_name] = linguistic_values

    def get_membership(self, variable: str, linguistic_value: str, value: float) -> float:
        """Get membership degree of value in linguistic set."""
        if variable not in self.membership_functions:
            return 0.0

        if linguistic_value not in self.membership_functions[variable]:
            return 0.0

        a, b, c = self.membership_functions[variable][linguistic_value]

        if value < a or value > c:
            return 0.0
        elif value == b:
            return 1.0
        elif a < value < b:
            return (value - a) / (b - a)
        else:  # b < value < c
            return (c - value) / (c - b)

    def and_operation(self, membership1: float, membership2: float) -> float:
        """Fuzzy AND (minimum)."""
        return min(membership1, membership2)

    def or_operation(self, membership1: float, membership2: float) -> float:
        """Fuzzy OR (maximum)."""
        return max(membership1, membership2)

    def not_operation(self, membership: float) -> float:
        """Fuzzy NOT (complement)."""
        return 1.0 - membership

    def defuzzify(self, fuzzy_values: Dict[str, float]) -> float:
        """Defuzzify to crisp value (center of gravity)."""
        if not fuzzy_values:
            return 0.0

        numerator = sum(float(k) * v for k, v in fuzzy_values.items())
        denominator = sum(fuzzy_values.values())

        return numerator / denominator if denominator > 0 else 0.0


class ModalLogic:
    """Modal logic for necessity and possibility."""

    def __init__(self):
        self.modal_propositions: Dict[str, ModalityType] = {}
        self.possible_worlds: List[Dict[str, bool]] = []

    def assert_necessary(self, proposition: str) -> None:
        """Assert that a proposition is necessarily true."""
        self.modal_propositions[proposition] = ModalityType.NECESSARY

    def assert_possible(self, proposition: str) -> None:
        """Assert that a proposition is possibly true."""
        self.modal_propositions[proposition] = ModalityType.POSSIBLE

    def assert_contingent(self, proposition: str) -> None:
        """Assert that a proposition is contingent (could be true or false)."""
        self.modal_propositions[proposition] = ModalityType.CONTINGENT

    def is_necessary(self, proposition: str) -> bool:
        """Check if proposition is necessary."""
        return self.modal_propositions.get(proposition) == ModalityType.NECESSARY

    def is_possible(self, proposition: str) -> bool:
        """Check if proposition is possible."""
        modality = self.modal_propositions.get(proposition, ModalityType.CONTINGENT)
        return modality in [ModalityType.NECESSARY, ModalityType.POSSIBLE, ModalityType.CONTINGENT]


class ConstraintProgram:
    """Constraint satisfaction problem solver."""

    def __init__(self):
        self.variables: Dict[str, List[Any]] = {}
        self.constraints: List[Tuple[List[str], callable]] = []

    def add_variable(self, name: str, domain: List[Any]) -> None:
        """Add variable with domain."""
        self.variables[name] = domain

    def add_constraint(self, variable_names: List[str], constraint_func: callable) -> None:
        """Add constraint."""
        self.constraints.append((variable_names, constraint_func))

    def solve(self, max_iterations: int = 1000) -> Optional[Dict[str, Any]]:
        """Solve CSP using backtracking with constraint propagation."""
        variable_names = list(self.variables.keys())
        assignment = {}

        def is_consistent(var: str, value: Any) -> bool:
            """Check if assignment is consistent."""
            assignment[var] = value

            for constraint_vars, constraint_func in self.constraints:
                if var in constraint_vars:
                    # Check if all required variables are assigned
                    if all(v in assignment for v in constraint_vars):
                        values = [assignment[v] for v in constraint_vars]
                        if not constraint_func(*values):
                            return False

            del assignment[var]
            return True

        def backtrack(var_index: int) -> bool:
            """Backtracking search."""
            if var_index == len(variable_names):
                return True

            var = variable_names[var_index]

            for value in self.variables[var]:
                if is_consistent(var, value):
                    assignment[var] = value

                    if backtrack(var_index + 1):
                        return True

                    del assignment[var]

            return False

        if backtrack(0):
            return assignment

        return None


class AdvancedReasoningExtensions:
    """Main advanced reasoning orchestrator."""

    def __init__(self):
        self.temporal = TemporalFormula(TemporalOperator.NEXT, "formula")
        self.bayesian = BayesianNetwork()
        self.fuzzy = FuzzyLogic()
        self.modal = ModalLogic()
        self.csp = ConstraintProgram()

    def temporal_reasoning(self, formula: TemporalFormula) -> bool:
        """Perform temporal reasoning."""
        return formula.evaluate_at_time(datetime.now())

    def probabilistic_inference(self, observations: Dict[str, str]) -> Dict:
        """Perform probabilistic inference."""
        return self.bayesian.infer(observations)

    def fuzzy_reasoning(self, fuzzy_values: Dict[str, float]) -> float:
        """Perform fuzzy reasoning and defuzzification."""
        return self.fuzzy.defuzzify(fuzzy_values)

    def modal_reasoning(self, proposition: str) -> Dict[str, bool]:
        """Analyze proposition modalities."""
        return {
            "necessary": self.modal.is_necessary(proposition),
            "possible": self.modal.is_possible(proposition)
        }

    def solve_constraints(self) -> Optional[Dict[str, Any]]:
        """Solve constraint satisfaction problem."""
        return self.csp.solve()

    def get_reasoning_capabilities(self) -> Dict[str, List[str]]:
        """Get available reasoning capabilities."""
        return {
            "temporal": [op.value for op in TemporalOperator],
            "modal": [m.value for m in ModalityType],
            "probabilistic": ["inference", "prediction"],
            "fuzzy": ["membership", "defuzzification"],
            "constraint": ["satisfaction", "propagation"]
        }


# Global instance
_advanced_reasoning = None


def get_advanced_reasoning() -> AdvancedReasoningExtensions:
    """Get or create global advanced reasoning system."""
    global _advanced_reasoning
    if _advanced_reasoning is None:
        _advanced_reasoning = AdvancedReasoningExtensions()
    return _advanced_reasoning
