"""
🧠 HEURISTIC REASONING 🧠
=========================
Heuristic problem solving.

Features:
- Means-ends analysis
- Analogical reasoning
- Case-based reasoning
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from abc import ABC, abstractmethod
import uuid
import math

from .problem_core import Problem, ProblemState, Solution


@dataclass
class Heuristic:
    """A heuristic function"""
    name: str

    # The heuristic function
    evaluate: Callable[[ProblemState], float] = None

    # Properties
    is_admissible: bool = True  # Never overestimates
    is_consistent: bool = True  # Monotonic

    def __call__(self, state: ProblemState) -> float:
        if self.evaluate:
            return self.evaluate(state)
        return 0.0


class HeuristicRule:
    """
    Rule-based heuristic.
    """

    def __init__(self, name: str = ""):
        self.name = name

        # Condition -> action rules
        self.rules: List[Tuple[Callable[[ProblemState], bool], Callable[[ProblemState], float]]] = []

        # Default value
        self.default_value: float = 0.0

    def add_rule(
        self,
        condition: Callable[[ProblemState], bool],
        action: Callable[[ProblemState], float]
    ):
        """Add heuristic rule"""
        self.rules.append((condition, action))

    def evaluate(self, state: ProblemState) -> float:
        """Evaluate heuristic"""
        for condition, action in self.rules:
            if condition(state):
                return action(state)
        return self.default_value

    def to_heuristic(self) -> Heuristic:
        """Convert to Heuristic"""
        return Heuristic(
            name=self.name,
            evaluate=self.evaluate,
            is_admissible=False,  # Cannot guarantee
            is_consistent=False
        )


@dataclass
class Difference:
    """Difference between states"""
    name: str
    current_value: Any
    goal_value: Any
    importance: float = 1.0

    def magnitude(self) -> float:
        """Magnitude of difference"""
        if isinstance(self.current_value, (int, float)) and isinstance(self.goal_value, (int, float)):
            return abs(self.goal_value - self.current_value)
        elif self.current_value == self.goal_value:
            return 0.0
        return 1.0


@dataclass
class Operator:
    """Operator that reduces differences"""
    name: str
    preconditions: Dict[str, Any] = field(default_factory=dict)
    effects: Dict[str, Any] = field(default_factory=dict)
    reduces: List[str] = field(default_factory=list)  # Differences it reduces

    def can_apply(self, state: Dict[str, Any]) -> bool:
        """Check if operator can be applied"""
        for key, value in self.preconditions.items():
            if key not in state or state[key] != value:
                return False
        return True

    def apply(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Apply operator"""
        new_state = state.copy()
        new_state.update(self.effects)
        return new_state


class MeansEndsAnalysis:
    """
    Means-ends analysis problem solving.
    """

    def __init__(self):
        self.operators: List[Operator] = []

        # Track applied operators
        self.trace: List[str] = []

    def add_operator(self, operator: Operator):
        """Add operator"""
        self.operators.append(operator)

    def find_differences(
        self,
        current: Dict[str, Any],
        goal: Dict[str, Any]
    ) -> List[Difference]:
        """Find differences between current and goal"""
        differences = []

        for key, goal_value in goal.items():
            current_value = current.get(key)

            if current_value != goal_value:
                diff = Difference(
                    name=key,
                    current_value=current_value,
                    goal_value=goal_value
                )
                differences.append(diff)

        # Sort by magnitude
        differences.sort(key=lambda d: d.magnitude(), reverse=True)
        return differences

    def find_operator_for_difference(
        self,
        difference: Difference
    ) -> Optional[Operator]:
        """Find operator that reduces difference"""
        for operator in self.operators:
            if difference.name in operator.reduces:
                return operator
        return None

    def solve(
        self,
        initial: Dict[str, Any],
        goal: Dict[str, Any],
        max_steps: int = 100
    ) -> Optional[List[str]]:
        """Solve using means-ends analysis"""
        self.trace = []
        current = initial.copy()

        for _ in range(max_steps):
            differences = self.find_differences(current, goal)

            if not differences:
                return self.trace  # Goal reached

            # Try to reduce most important difference
            solved_any = False

            for diff in differences:
                operator = self.find_operator_for_difference(diff)

                if operator:
                    if operator.can_apply(current):
                        # Apply operator
                        current = operator.apply(current)
                        self.trace.append(operator.name)
                        solved_any = True
                        break
                    else:
                        # Subgoal: achieve preconditions
                        subgoal = operator.preconditions
                        sub_solution = self.solve(current, subgoal, max_steps // 2)

                        if sub_solution:
                            # Apply subgoal solution
                            for op_name in sub_solution:
                                op = next((o for o in self.operators if o.name == op_name), None)
                                if op and op.can_apply(current):
                                    current = op.apply(current)

                            # Now try original operator
                            if operator.can_apply(current):
                                current = operator.apply(current)
                                self.trace.append(operator.name)
                                solved_any = True
                                break

            if not solved_any:
                return None  # Stuck

        return None  # Max steps exceeded


@dataclass
class Case:
    """A case for case-based reasoning"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Problem description
    problem: Dict[str, Any] = field(default_factory=dict)

    # Solution
    solution: Any = None

    # Outcome
    success: bool = True
    outcome: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    domain: str = ""
    tags: List[str] = field(default_factory=list)


class CaseBasedReasoner:
    """
    Case-based reasoning.
    """

    def __init__(self):
        self.case_base: List[Case] = []

        # Similarity weights
        self.weights: Dict[str, float] = {}

    def add_case(self, case: Case):
        """Add case to case base"""
        self.case_base.append(case)

    def set_weight(self, feature: str, weight: float):
        """Set feature weight for similarity"""
        self.weights[feature] = weight

    def similarity(self, problem1: Dict[str, Any], problem2: Dict[str, Any]) -> float:
        """Compute weighted similarity"""
        if not problem1 or not problem2:
            return 0.0

        total_weight = 0.0
        weighted_sim = 0.0

        all_features = set(problem1.keys()) | set(problem2.keys())

        for feature in all_features:
            weight = self.weights.get(feature, 1.0)
            total_weight += weight

            v1 = problem1.get(feature)
            v2 = problem2.get(feature)

            if v1 == v2:
                weighted_sim += weight
            elif isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                # Numeric similarity
                max_val = max(abs(v1), abs(v2), 1)
                sim = 1.0 - abs(v1 - v2) / max_val
                weighted_sim += weight * max(0, sim)

        return weighted_sim / total_weight if total_weight > 0 else 0.0

    def retrieve(
        self,
        problem: Dict[str, Any],
        n: int = 5
    ) -> List[Tuple[Case, float]]:
        """Retrieve similar cases"""
        similarities = []

        for case in self.case_base:
            sim = self.similarity(problem, case.problem)
            similarities.append((case, sim))

        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:n]

    def adapt(
        self,
        case: Case,
        new_problem: Dict[str, Any]
    ) -> Any:
        """Adapt case solution to new problem"""
        # Simple adaptation: return solution if similar enough
        # In practice, this would involve more sophisticated adaptation
        return case.solution

    def solve(self, problem: Dict[str, Any]) -> Optional[Any]:
        """Solve using case-based reasoning"""
        # Retrieve
        similar = self.retrieve(problem, n=3)

        if not similar:
            return None

        # Use most similar case
        best_case, similarity = similar[0]

        if similarity < 0.3:
            return None  # Not similar enough

        # Adapt
        solution = self.adapt(best_case, problem)

        return solution

    def retain(
        self,
        problem: Dict[str, Any],
        solution: Any,
        success: bool = True
    ):
        """Retain new case"""
        case = Case(
            problem=problem,
            solution=solution,
            success=success
        )
        self.add_case(case)


class AnalogicalReasoner:
    """
    Analogical reasoning.
    """

    def __init__(self):
        self.source_domains: Dict[str, List[Dict[str, Any]]] = {}

        # Mapping rules
        self.mappings: Dict[Tuple[str, str], Dict[str, str]] = {}

    def add_source_domain(self, domain: str, examples: List[Dict[str, Any]]):
        """Add source domain with examples"""
        self.source_domains[domain] = examples

    def add_mapping(
        self,
        source_domain: str,
        target_domain: str,
        mapping: Dict[str, str]
    ):
        """Add mapping between domains"""
        self.mappings[(source_domain, target_domain)] = mapping

    def find_analogies(
        self,
        target: Dict[str, Any],
        target_domain: str
    ) -> List[Tuple[str, Dict[str, Any], float]]:
        """Find analogous examples from source domains"""
        analogies = []

        for source_domain, examples in self.source_domains.items():
            mapping = self.mappings.get((source_domain, target_domain), {})

            for example in examples:
                # Map example to target domain
                mapped_example = self._apply_mapping(example, mapping)

                # Compute structural similarity
                similarity = self._structural_similarity(target, mapped_example)

                if similarity > 0.3:
                    analogies.append((source_domain, example, similarity))

        analogies.sort(key=lambda x: x[2], reverse=True)
        return analogies

    def _apply_mapping(
        self,
        source: Dict[str, Any],
        mapping: Dict[str, str]
    ) -> Dict[str, Any]:
        """Apply mapping to source"""
        if not mapping:
            return source

        result = {}
        for key, value in source.items():
            mapped_key = mapping.get(key, key)
            result[mapped_key] = value

        return result

    def _structural_similarity(
        self,
        target: Dict[str, Any],
        mapped_source: Dict[str, Any]
    ) -> float:
        """Compute structural similarity"""
        common_keys = set(target.keys()) & set(mapped_source.keys())
        all_keys = set(target.keys()) | set(mapped_source.keys())

        if not all_keys:
            return 0.0

        return len(common_keys) / len(all_keys)

    def transfer(
        self,
        source_domain: str,
        source_solution: Any,
        target_domain: str
    ) -> Any:
        """Transfer solution across domains"""
        mapping = self.mappings.get((source_domain, target_domain), {})

        if isinstance(source_solution, dict):
            return self._apply_mapping(source_solution, mapping)

        return source_solution


# Export all
__all__ = [
    'Heuristic',
    'HeuristicRule',
    'Difference',
    'Operator',
    'MeansEndsAnalysis',
    'Case',
    'CaseBasedReasoner',
    'AnalogicalReasoner',
]
