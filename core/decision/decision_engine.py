#!/usr/bin/env python3
"""
BAEL - Decision Engine
Advanced decision-making system.

Features:
- Multi-criteria decision making
- Utility theory
- Decision trees
- Probabilistic decision making
- Decision under uncertainty
"""

import asyncio
import hashlib
import json
import math
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class DecisionStrategy(Enum):
    """Decision strategies."""
    MAXIMIZE_EXPECTED_UTILITY = "maximize_expected_utility"
    MINIMAX = "minimax"
    MAXIMIN = "maximin"
    SATISFICING = "satisficing"
    WEIGHTED_SUM = "weighted_sum"
    PARETO_OPTIMAL = "pareto_optimal"


class DecisionUncertainty(Enum):
    """Uncertainty levels."""
    CERTAINTY = "certainty"
    RISK = "risk"
    UNCERTAINTY = "uncertainty"
    AMBIGUITY = "ambiguity"


class CriteriaType(Enum):
    """Criteria types."""
    BENEFIT = "benefit"
    COST = "cost"


class DecisionStatus(Enum):
    """Decision statuses."""
    PENDING = "pending"
    ANALYZING = "analyzing"
    DECIDED = "decided"
    EXECUTED = "executed"
    REVIEWED = "reviewed"


class OutcomeType(Enum):
    """Outcome types."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    UNKNOWN = "unknown"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Criterion:
    """A decision criterion."""
    criterion_id: str = ""
    name: str = ""
    weight: float = 1.0
    criteria_type: CriteriaType = CriteriaType.BENEFIT
    min_value: float = 0.0
    max_value: float = 1.0

    def __post_init__(self):
        if not self.criterion_id:
            self.criterion_id = str(uuid.uuid4())[:8]


@dataclass
class Alternative:
    """A decision alternative."""
    alternative_id: str = ""
    name: str = ""
    description: str = ""
    scores: Dict[str, float] = field(default_factory=dict)
    probability: float = 1.0
    utility: float = 0.0

    def __post_init__(self):
        if not self.alternative_id:
            self.alternative_id = str(uuid.uuid4())[:8]


@dataclass
class DecisionNode:
    """A decision tree node."""
    node_id: str = ""
    name: str = ""
    node_type: str = "decision"
    alternatives: List[str] = field(default_factory=list)
    probabilities: Dict[str, float] = field(default_factory=dict)
    payoffs: Dict[str, float] = field(default_factory=dict)
    children: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if not self.node_id:
            self.node_id = str(uuid.uuid4())[:8]


@dataclass
class Decision:
    """A decision record."""
    decision_id: str = ""
    problem: str = ""
    alternatives: List[str] = field(default_factory=list)
    criteria: List[str] = field(default_factory=list)
    selected_alternative: Optional[str] = None
    confidence: float = 0.0
    strategy: DecisionStrategy = DecisionStrategy.MAXIMIZE_EXPECTED_UTILITY
    uncertainty: DecisionUncertainty = DecisionUncertainty.RISK
    status: DecisionStatus = DecisionStatus.PENDING
    rationale: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.decision_id:
            self.decision_id = str(uuid.uuid4())[:8]


@dataclass
class Outcome:
    """An outcome of a decision."""
    outcome_id: str = ""
    decision_id: str = ""
    outcome_type: OutcomeType = OutcomeType.UNKNOWN
    actual_utility: float = 0.0
    expected_utility: float = 0.0
    lessons: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.outcome_id:
            self.outcome_id = str(uuid.uuid4())[:8]


@dataclass
class DecisionStats:
    """Decision statistics."""
    total_decisions: int = 0
    successful: int = 0
    partial: int = 0
    failed: int = 0
    avg_confidence: float = 0.0
    utility_accuracy: float = 0.0


# =============================================================================
# CRITERIA MANAGER
# =============================================================================

class CriteriaManager:
    """Manage decision criteria."""

    def __init__(self):
        self._criteria: Dict[str, Criterion] = {}

    def add(
        self,
        name: str,
        weight: float = 1.0,
        criteria_type: CriteriaType = CriteriaType.BENEFIT,
        min_value: float = 0.0,
        max_value: float = 1.0
    ) -> Criterion:
        """Add a criterion."""
        criterion = Criterion(
            name=name,
            weight=max(0.0, weight),
            criteria_type=criteria_type,
            min_value=min_value,
            max_value=max_value
        )

        self._criteria[criterion.criterion_id] = criterion

        return criterion

    def get(self, criterion_id: str) -> Optional[Criterion]:
        """Get a criterion."""
        return self._criteria.get(criterion_id)

    def find_by_name(self, name: str) -> Optional[Criterion]:
        """Find criterion by name."""
        for c in self._criteria.values():
            if c.name.lower() == name.lower():
                return c
        return None

    def update_weight(self, criterion_id: str, weight: float) -> bool:
        """Update criterion weight."""
        criterion = self._criteria.get(criterion_id)
        if criterion:
            criterion.weight = max(0.0, weight)
            return True
        return False

    def normalize_weights(self) -> None:
        """Normalize weights to sum to 1."""
        total = sum(c.weight for c in self._criteria.values())

        if total > 0:
            for criterion in self._criteria.values():
                criterion.weight /= total

    def get_all(self) -> List[Criterion]:
        """Get all criteria."""
        return list(self._criteria.values())

    def remove(self, criterion_id: str) -> bool:
        """Remove a criterion."""
        if criterion_id in self._criteria:
            del self._criteria[criterion_id]
            return True
        return False


# =============================================================================
# ALTERNATIVE MANAGER
# =============================================================================

class AlternativeManager:
    """Manage decision alternatives."""

    def __init__(self):
        self._alternatives: Dict[str, Alternative] = {}

    def add(
        self,
        name: str,
        description: str = "",
        scores: Optional[Dict[str, float]] = None,
        probability: float = 1.0
    ) -> Alternative:
        """Add an alternative."""
        alternative = Alternative(
            name=name,
            description=description,
            scores=scores or {},
            probability=max(0.0, min(1.0, probability))
        )

        self._alternatives[alternative.alternative_id] = alternative

        return alternative

    def get(self, alternative_id: str) -> Optional[Alternative]:
        """Get an alternative."""
        return self._alternatives.get(alternative_id)

    def find_by_name(self, name: str) -> Optional[Alternative]:
        """Find alternative by name."""
        for a in self._alternatives.values():
            if a.name.lower() == name.lower():
                return a
        return None

    def set_score(
        self,
        alternative_id: str,
        criterion_id: str,
        score: float
    ) -> bool:
        """Set score for an alternative on a criterion."""
        alternative = self._alternatives.get(alternative_id)
        if alternative:
            alternative.scores[criterion_id] = score
            return True
        return False

    def set_probability(
        self,
        alternative_id: str,
        probability: float
    ) -> bool:
        """Set probability for an alternative."""
        alternative = self._alternatives.get(alternative_id)
        if alternative:
            alternative.probability = max(0.0, min(1.0, probability))
            return True
        return False

    def get_all(self) -> List[Alternative]:
        """Get all alternatives."""
        return list(self._alternatives.values())

    def remove(self, alternative_id: str) -> bool:
        """Remove an alternative."""
        if alternative_id in self._alternatives:
            del self._alternatives[alternative_id]
            return True
        return False

    def clear(self) -> None:
        """Clear all alternatives."""
        self._alternatives.clear()


# =============================================================================
# UTILITY CALCULATOR
# =============================================================================

class UtilityCalculator:
    """Calculate utilities."""

    def __init__(self, criteria_manager: CriteriaManager):
        self._criteria = criteria_manager
        self._utility_functions: Dict[str, Callable[[float], float]] = {}

    def set_utility_function(
        self,
        criterion_id: str,
        fn: Callable[[float], float]
    ) -> None:
        """Set utility function for a criterion."""
        self._utility_functions[criterion_id] = fn

    def calculate_utility(
        self,
        alternative: Alternative
    ) -> float:
        """Calculate utility for an alternative."""
        total_utility = 0.0
        total_weight = 0.0

        for criterion in self._criteria.get_all():
            if criterion.criterion_id not in alternative.scores:
                continue

            score = alternative.scores[criterion.criterion_id]

            normalized = self._normalize_score(score, criterion)

            if criterion.criterion_id in self._utility_functions:
                utility = self._utility_functions[criterion.criterion_id](normalized)
            else:
                utility = normalized

            total_utility += utility * criterion.weight
            total_weight += criterion.weight

        if total_weight > 0:
            return total_utility / total_weight

        return 0.0

    def _normalize_score(
        self,
        score: float,
        criterion: Criterion
    ) -> float:
        """Normalize a score."""
        range_val = criterion.max_value - criterion.min_value

        if range_val == 0:
            return 0.5

        normalized = (score - criterion.min_value) / range_val

        if criterion.criteria_type == CriteriaType.COST:
            normalized = 1 - normalized

        return max(0.0, min(1.0, normalized))

    def calculate_expected_utility(
        self,
        alternative: Alternative
    ) -> float:
        """Calculate expected utility considering probability."""
        utility = self.calculate_utility(alternative)
        return utility * alternative.probability


# =============================================================================
# DECISION ANALYZER
# =============================================================================

class DecisionAnalyzer:
    """Analyze decisions."""

    def __init__(
        self,
        criteria_manager: CriteriaManager,
        alternative_manager: AlternativeManager,
        utility_calculator: UtilityCalculator
    ):
        self._criteria = criteria_manager
        self._alternatives = alternative_manager
        self._utility = utility_calculator

    def analyze_weighted_sum(self) -> List[Tuple[Alternative, float]]:
        """Analyze using weighted sum method."""
        results = []

        for alt in self._alternatives.get_all():
            utility = self._utility.calculate_utility(alt)
            alt.utility = utility
            results.append((alt, utility))

        return sorted(results, key=lambda x: x[1], reverse=True)

    def analyze_expected_utility(self) -> List[Tuple[Alternative, float]]:
        """Analyze using expected utility."""
        results = []

        for alt in self._alternatives.get_all():
            eu = self._utility.calculate_expected_utility(alt)
            results.append((alt, eu))

        return sorted(results, key=lambda x: x[1], reverse=True)

    def analyze_minimax(self) -> List[Tuple[Alternative, float]]:
        """Analyze using minimax (minimize maximum regret)."""
        results = []

        for alt in self._alternatives.get_all():
            scores = list(alt.scores.values())
            if scores:
                max_regret = max(1 - s for s in scores)
                results.append((alt, -max_regret))

        return sorted(results, key=lambda x: x[1], reverse=True)

    def analyze_maximin(self) -> List[Tuple[Alternative, float]]:
        """Analyze using maximin (maximize minimum payoff)."""
        results = []

        for alt in self._alternatives.get_all():
            scores = list(alt.scores.values())
            if scores:
                min_score = min(scores)
                results.append((alt, min_score))

        return sorted(results, key=lambda x: x[1], reverse=True)

    def analyze_satisficing(
        self,
        thresholds: Dict[str, float]
    ) -> List[Alternative]:
        """Find satisficing alternatives."""
        satisficing = []

        for alt in self._alternatives.get_all():
            satisfies_all = True

            for criterion_id, threshold in thresholds.items():
                if criterion_id in alt.scores:
                    if alt.scores[criterion_id] < threshold:
                        satisfies_all = False
                        break

            if satisfies_all:
                satisficing.append(alt)

        return satisficing

    def find_pareto_optimal(self) -> List[Alternative]:
        """Find Pareto optimal alternatives."""
        alternatives = self._alternatives.get_all()
        pareto = []

        for alt in alternatives:
            dominated = False

            for other in alternatives:
                if other.alternative_id == alt.alternative_id:
                    continue

                if self._dominates(other, alt):
                    dominated = True
                    break

            if not dominated:
                pareto.append(alt)

        return pareto

    def _dominates(self, alt1: Alternative, alt2: Alternative) -> bool:
        """Check if alt1 dominates alt2."""
        dominated_in_all = True
        better_in_one = False

        criteria = self._criteria.get_all()

        for criterion in criteria:
            cid = criterion.criterion_id
            score1 = alt1.scores.get(cid, 0)
            score2 = alt2.scores.get(cid, 0)

            if criterion.criteria_type == CriteriaType.COST:
                score1, score2 = -score1, -score2

            if score1 < score2:
                dominated_in_all = False
            elif score1 > score2:
                better_in_one = True

        return dominated_in_all and better_in_one

    def sensitivity_analysis(
        self,
        criterion_id: str,
        weight_range: Tuple[float, float] = (0.0, 1.0),
        steps: int = 10
    ) -> Dict[str, List[Tuple[float, float]]]:
        """Perform sensitivity analysis on a criterion weight."""
        results: Dict[str, List[Tuple[float, float]]] = defaultdict(list)

        criterion = self._criteria.get(criterion_id)
        if not criterion:
            return results

        original_weight = criterion.weight

        step_size = (weight_range[1] - weight_range[0]) / steps

        for i in range(steps + 1):
            weight = weight_range[0] + i * step_size
            criterion.weight = weight

            for alt in self._alternatives.get_all():
                utility = self._utility.calculate_utility(alt)
                results[alt.name].append((weight, utility))

        criterion.weight = original_weight

        return dict(results)


# =============================================================================
# DECISION TREE
# =============================================================================

class DecisionTree:
    """Decision tree for sequential decisions."""

    def __init__(self):
        self._nodes: Dict[str, DecisionNode] = {}
        self._root: Optional[str] = None

    def add_decision_node(
        self,
        name: str,
        alternatives: List[str],
        payoffs: Optional[Dict[str, float]] = None
    ) -> DecisionNode:
        """Add a decision node."""
        node = DecisionNode(
            name=name,
            node_type="decision",
            alternatives=alternatives,
            payoffs=payoffs or {}
        )

        self._nodes[node.node_id] = node

        if self._root is None:
            self._root = node.node_id

        return node

    def add_chance_node(
        self,
        name: str,
        outcomes: List[str],
        probabilities: Dict[str, float]
    ) -> DecisionNode:
        """Add a chance node."""
        node = DecisionNode(
            name=name,
            node_type="chance",
            alternatives=outcomes,
            probabilities=probabilities
        )

        self._nodes[node.node_id] = node

        return node

    def add_terminal_node(
        self,
        name: str,
        payoff: float
    ) -> DecisionNode:
        """Add a terminal node."""
        node = DecisionNode(
            name=name,
            node_type="terminal",
            payoffs={"terminal": payoff}
        )

        self._nodes[node.node_id] = node

        return node

    def link_nodes(
        self,
        parent_id: str,
        child_id: str,
        branch: str
    ) -> bool:
        """Link nodes."""
        parent = self._nodes.get(parent_id)
        if not parent:
            return False

        parent.children[branch] = child_id
        return True

    def evaluate(self, node_id: Optional[str] = None) -> Tuple[float, Optional[str]]:
        """Evaluate tree from a node."""
        if node_id is None:
            node_id = self._root

        if node_id is None:
            return 0.0, None

        node = self._nodes.get(node_id)
        if not node:
            return 0.0, None

        if node.node_type == "terminal":
            return node.payoffs.get("terminal", 0.0), None

        if node.node_type == "decision":
            best_value = float("-inf")
            best_action = None

            for alt in node.alternatives:
                child_id = node.children.get(alt)
                if child_id:
                    value, _ = self.evaluate(child_id)
                else:
                    value = node.payoffs.get(alt, 0.0)

                if value > best_value:
                    best_value = value
                    best_action = alt

            return best_value, best_action

        if node.node_type == "chance":
            expected_value = 0.0

            for outcome in node.alternatives:
                prob = node.probabilities.get(outcome, 0.0)
                child_id = node.children.get(outcome)

                if child_id:
                    value, _ = self.evaluate(child_id)
                else:
                    value = node.payoffs.get(outcome, 0.0)

                expected_value += prob * value

            return expected_value, None

        return 0.0, None

    def get_node(self, node_id: str) -> Optional[DecisionNode]:
        """Get a node."""
        return self._nodes.get(node_id)

    @property
    def root(self) -> Optional[str]:
        return self._root


# =============================================================================
# DECISION ENGINE
# =============================================================================

class DecisionEngine:
    """
    Decision Engine for BAEL.

    Advanced decision-making system.
    """

    def __init__(self):
        self._criteria = CriteriaManager()
        self._alternatives = AlternativeManager()
        self._utility = UtilityCalculator(self._criteria)
        self._analyzer = DecisionAnalyzer(
            self._criteria,
            self._alternatives,
            self._utility
        )
        self._tree = DecisionTree()

        self._decisions: Dict[str, Decision] = {}
        self._outcomes: Dict[str, Outcome] = {}
        self._stats = DecisionStats()

    def add_criterion(
        self,
        name: str,
        weight: float = 1.0,
        criteria_type: CriteriaType = CriteriaType.BENEFIT,
        min_value: float = 0.0,
        max_value: float = 1.0
    ) -> Criterion:
        """Add a decision criterion."""
        return self._criteria.add(
            name, weight, criteria_type, min_value, max_value
        )

    def update_criterion_weight(
        self,
        criterion_id: str,
        weight: float
    ) -> bool:
        """Update criterion weight."""
        return self._criteria.update_weight(criterion_id, weight)

    def normalize_criteria_weights(self) -> None:
        """Normalize criteria weights."""
        self._criteria.normalize_weights()

    def add_alternative(
        self,
        name: str,
        description: str = "",
        scores: Optional[Dict[str, float]] = None,
        probability: float = 1.0
    ) -> Alternative:
        """Add an alternative."""
        return self._alternatives.add(
            name, description, scores, probability
        )

    def set_alternative_score(
        self,
        alternative_id: str,
        criterion_id: str,
        score: float
    ) -> bool:
        """Set score for an alternative."""
        return self._alternatives.set_score(
            alternative_id, criterion_id, score
        )

    def set_utility_function(
        self,
        criterion_id: str,
        fn: Callable[[float], float]
    ) -> None:
        """Set utility function."""
        self._utility.set_utility_function(criterion_id, fn)

    def analyze(
        self,
        strategy: DecisionStrategy = DecisionStrategy.MAXIMIZE_EXPECTED_UTILITY,
        **kwargs
    ) -> List[Tuple[Alternative, float]]:
        """Analyze alternatives using a strategy."""
        if strategy == DecisionStrategy.WEIGHTED_SUM:
            return self._analyzer.analyze_weighted_sum()
        elif strategy == DecisionStrategy.MAXIMIZE_EXPECTED_UTILITY:
            return self._analyzer.analyze_expected_utility()
        elif strategy == DecisionStrategy.MINIMAX:
            return self._analyzer.analyze_minimax()
        elif strategy == DecisionStrategy.MAXIMIN:
            return self._analyzer.analyze_maximin()
        elif strategy == DecisionStrategy.SATISFICING:
            thresholds = kwargs.get("thresholds", {})
            alts = self._analyzer.analyze_satisficing(thresholds)
            return [(alt, 1.0) for alt in alts]
        elif strategy == DecisionStrategy.PARETO_OPTIMAL:
            alts = self._analyzer.find_pareto_optimal()
            return [(alt, 1.0) for alt in alts]

        return self._analyzer.analyze_expected_utility()

    def decide(
        self,
        problem: str,
        strategy: DecisionStrategy = DecisionStrategy.MAXIMIZE_EXPECTED_UTILITY,
        uncertainty: DecisionUncertainty = DecisionUncertainty.RISK,
        **kwargs
    ) -> Decision:
        """Make a decision."""
        results = self.analyze(strategy, **kwargs)

        selected = results[0][0] if results else None
        confidence = results[0][1] if results else 0.0

        decision = Decision(
            problem=problem,
            alternatives=[a.name for a, _ in results],
            criteria=[c.name for c in self._criteria.get_all()],
            selected_alternative=selected.name if selected else None,
            confidence=confidence,
            strategy=strategy,
            uncertainty=uncertainty,
            status=DecisionStatus.DECIDED,
            rationale=self._generate_rationale(results, strategy)
        )

        self._decisions[decision.decision_id] = decision
        self._stats.total_decisions += 1

        return decision

    def _generate_rationale(
        self,
        results: List[Tuple[Alternative, float]],
        strategy: DecisionStrategy
    ) -> str:
        """Generate decision rationale."""
        if not results:
            return "No alternatives available"

        best, score = results[0]

        rationale = f"Using {strategy.value} strategy, "
        rationale += f"'{best.name}' was selected with score {score:.3f}. "

        if len(results) > 1:
            second, second_score = results[1]
            margin = score - second_score
            rationale += f"Margin over '{second.name}': {margin:.3f}"

        return rationale

    def record_outcome(
        self,
        decision_id: str,
        outcome_type: OutcomeType,
        actual_utility: float,
        lessons: Optional[List[str]] = None
    ) -> Outcome:
        """Record decision outcome."""
        decision = self._decisions.get(decision_id)

        outcome = Outcome(
            decision_id=decision_id,
            outcome_type=outcome_type,
            actual_utility=actual_utility,
            expected_utility=decision.confidence if decision else 0.0,
            lessons=lessons or []
        )

        self._outcomes[outcome.outcome_id] = outcome

        if decision:
            decision.status = DecisionStatus.REVIEWED

        self._update_stats(outcome_type)

        return outcome

    def _update_stats(self, outcome_type: OutcomeType) -> None:
        """Update statistics."""
        if outcome_type == OutcomeType.SUCCESS:
            self._stats.successful += 1
        elif outcome_type == OutcomeType.PARTIAL:
            self._stats.partial += 1
        elif outcome_type == OutcomeType.FAILURE:
            self._stats.failed += 1

        if self._outcomes:
            accuracies = []
            for outcome in self._outcomes.values():
                if outcome.expected_utility > 0:
                    accuracy = 1 - abs(outcome.actual_utility - outcome.expected_utility)
                    accuracies.append(accuracy)

            if accuracies:
                self._stats.utility_accuracy = sum(accuracies) / len(accuracies)

    def sensitivity_analysis(
        self,
        criterion_id: str,
        weight_range: Tuple[float, float] = (0.0, 1.0),
        steps: int = 10
    ) -> Dict[str, List[Tuple[float, float]]]:
        """Perform sensitivity analysis."""
        return self._analyzer.sensitivity_analysis(
            criterion_id, weight_range, steps
        )

    def find_pareto_optimal(self) -> List[Alternative]:
        """Find Pareto optimal alternatives."""
        return self._analyzer.find_pareto_optimal()

    def add_decision_tree_node(
        self,
        name: str,
        node_type: str = "decision",
        alternatives: Optional[List[str]] = None,
        probabilities: Optional[Dict[str, float]] = None,
        payoff: float = 0.0
    ) -> DecisionNode:
        """Add a decision tree node."""
        if node_type == "decision":
            return self._tree.add_decision_node(name, alternatives or [])
        elif node_type == "chance":
            return self._tree.add_chance_node(
                name, alternatives or [], probabilities or {}
            )
        else:
            return self._tree.add_terminal_node(name, payoff)

    def link_tree_nodes(
        self,
        parent_id: str,
        child_id: str,
        branch: str
    ) -> bool:
        """Link decision tree nodes."""
        return self._tree.link_nodes(parent_id, child_id, branch)

    def evaluate_decision_tree(self) -> Tuple[float, Optional[str]]:
        """Evaluate decision tree."""
        return self._tree.evaluate()

    def get_decision(self, decision_id: str) -> Optional[Decision]:
        """Get a decision."""
        return self._decisions.get(decision_id)

    def get_decisions(
        self,
        status: Optional[DecisionStatus] = None,
        limit: int = 20
    ) -> List[Decision]:
        """Get decisions."""
        decisions = list(self._decisions.values())

        if status:
            decisions = [d for d in decisions if d.status == status]

        decisions.sort(key=lambda d: d.timestamp, reverse=True)

        return decisions[:limit]

    def clear_alternatives(self) -> None:
        """Clear all alternatives."""
        self._alternatives.clear()

    @property
    def stats(self) -> DecisionStats:
        """Get statistics."""
        confidences = [d.confidence for d in self._decisions.values()]
        if confidences:
            self._stats.avg_confidence = sum(confidences) / len(confidences)

        return self._stats

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "criteria": len(self._criteria.get_all()),
            "alternatives": len(self._alternatives.get_all()),
            "total_decisions": self._stats.total_decisions,
            "successful": self._stats.successful,
            "partial": self._stats.partial,
            "failed": self._stats.failed,
            "avg_confidence": f"{self._stats.avg_confidence:.2f}",
            "utility_accuracy": f"{self._stats.utility_accuracy:.2f}",
            "tree_nodes": len(self._tree._nodes)
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Decision Engine."""
    print("=" * 70)
    print("BAEL - DECISION ENGINE DEMO")
    print("Advanced Decision-Making System")
    print("=" * 70)
    print()

    engine = DecisionEngine()

    # 1. Add Criteria
    print("1. ADD DECISION CRITERIA:")
    print("-" * 40)

    cost = engine.add_criterion(
        "cost",
        weight=0.3,
        criteria_type=CriteriaType.COST,
        min_value=0,
        max_value=1000
    )

    quality = engine.add_criterion(
        "quality",
        weight=0.4,
        criteria_type=CriteriaType.BENEFIT,
        min_value=0,
        max_value=10
    )

    speed = engine.add_criterion(
        "speed",
        weight=0.3,
        criteria_type=CriteriaType.BENEFIT,
        min_value=0,
        max_value=100
    )

    print(f"   {cost.name}: weight={cost.weight}, type={cost.criteria_type.value}")
    print(f"   {quality.name}: weight={quality.weight}, type={quality.criteria_type.value}")
    print(f"   {speed.name}: weight={speed.weight}, type={speed.criteria_type.value}")
    print()

    # 2. Add Alternatives
    print("2. ADD ALTERNATIVES:")
    print("-" * 40)

    alt_a = engine.add_alternative(
        "Option A",
        "Fast and cheap but lower quality",
        probability=0.95
    )

    alt_b = engine.add_alternative(
        "Option B",
        "High quality but expensive",
        probability=0.90
    )

    alt_c = engine.add_alternative(
        "Option C",
        "Balanced approach",
        probability=0.85
    )

    engine.set_alternative_score(alt_a.alternative_id, cost.criterion_id, 200)
    engine.set_alternative_score(alt_a.alternative_id, quality.criterion_id, 5)
    engine.set_alternative_score(alt_a.alternative_id, speed.criterion_id, 90)

    engine.set_alternative_score(alt_b.alternative_id, cost.criterion_id, 800)
    engine.set_alternative_score(alt_b.alternative_id, quality.criterion_id, 9)
    engine.set_alternative_score(alt_b.alternative_id, speed.criterion_id, 60)

    engine.set_alternative_score(alt_c.alternative_id, cost.criterion_id, 500)
    engine.set_alternative_score(alt_c.alternative_id, quality.criterion_id, 7)
    engine.set_alternative_score(alt_c.alternative_id, speed.criterion_id, 75)

    print(f"   {alt_a.name}: cost=200, quality=5, speed=90")
    print(f"   {alt_b.name}: cost=800, quality=9, speed=60")
    print(f"   {alt_c.name}: cost=500, quality=7, speed=75")
    print()

    # 3. Analyze with Different Strategies
    print("3. ANALYZE WITH DIFFERENT STRATEGIES:")
    print("-" * 40)

    strategies = [
        DecisionStrategy.WEIGHTED_SUM,
        DecisionStrategy.MAXIMIZE_EXPECTED_UTILITY,
        DecisionStrategy.MINIMAX,
        DecisionStrategy.MAXIMIN
    ]

    for strategy in strategies:
        results = engine.analyze(strategy)
        best = results[0] if results else (None, 0)
        print(f"   {strategy.value}:")
        print(f"     Best: {best[0].name if best[0] else 'None'} ({best[1]:.3f})")
    print()

    # 4. Find Pareto Optimal
    print("4. FIND PARETO OPTIMAL:")
    print("-" * 40)

    pareto = engine.find_pareto_optimal()
    print(f"   Pareto optimal alternatives: {[a.name for a in pareto]}")
    print()

    # 5. Make Decision
    print("5. MAKE DECISION:")
    print("-" * 40)

    decision = engine.decide(
        problem="Select best implementation approach",
        strategy=DecisionStrategy.MAXIMIZE_EXPECTED_UTILITY,
        uncertainty=DecisionUncertainty.RISK
    )

    print(f"   Problem: {decision.problem}")
    print(f"   Selected: {decision.selected_alternative}")
    print(f"   Confidence: {decision.confidence:.3f}")
    print(f"   Strategy: {decision.strategy.value}")
    print(f"   Rationale: {decision.rationale}")
    print()

    # 6. Sensitivity Analysis
    print("6. SENSITIVITY ANALYSIS:")
    print("-" * 40)

    sensitivity = engine.sensitivity_analysis(
        quality.criterion_id,
        weight_range=(0.1, 0.7),
        steps=5
    )

    print(f"   Varying '{quality.name}' weight:")
    for alt_name, points in sensitivity.items():
        print(f"   {alt_name}:")
        for weight, utility in points[:3]:
            print(f"     w={weight:.2f} -> u={utility:.3f}")
    print()

    # 7. Record Outcome
    print("7. RECORD OUTCOME:")
    print("-" * 40)

    outcome = engine.record_outcome(
        decision.decision_id,
        OutcomeType.SUCCESS,
        actual_utility=0.85,
        lessons=["Balanced approach works well", "Consider speed more"]
    )

    print(f"   Outcome: {outcome.outcome_type.value}")
    print(f"   Expected: {outcome.expected_utility:.3f}")
    print(f"   Actual: {outcome.actual_utility:.3f}")
    print(f"   Lessons: {outcome.lessons}")
    print()

    # 8. Decision Tree
    print("8. DECISION TREE:")
    print("-" * 40)

    root = engine.add_decision_tree_node(
        "invest_decision",
        node_type="decision",
        alternatives=["invest", "wait"]
    )

    chance1 = engine.add_decision_tree_node(
        "market_outcome",
        node_type="chance",
        alternatives=["up", "down"],
        probabilities={"up": 0.6, "down": 0.4}
    )

    term_up = engine.add_decision_tree_node("profit", node_type="terminal", payoff=100)
    term_down = engine.add_decision_tree_node("loss", node_type="terminal", payoff=-50)
    term_wait = engine.add_decision_tree_node("no_change", node_type="terminal", payoff=0)

    engine.link_tree_nodes(root.node_id, chance1.node_id, "invest")
    engine.link_tree_nodes(root.node_id, term_wait.node_id, "wait")
    engine.link_tree_nodes(chance1.node_id, term_up.node_id, "up")
    engine.link_tree_nodes(chance1.node_id, term_down.node_id, "down")

    value, action = engine.evaluate_decision_tree()

    print(f"   Expected value: {value:.2f}")
    print(f"   Best action: {action}")
    print()

    # 9. Custom Utility Function
    print("9. CUSTOM UTILITY FUNCTION:")
    print("-" * 40)

    def risk_averse_utility(x):
        return math.sqrt(x)

    engine.set_utility_function(quality.criterion_id, risk_averse_utility)

    results = engine.analyze(DecisionStrategy.WEIGHTED_SUM)

    print("   With risk-averse utility for quality:")
    for alt, score in results:
        print(f"     {alt.name}: {score:.3f}")
    print()

    # 10. Statistics
    print("10. DECISION STATISTICS:")
    print("-" * 40)

    stats = engine.stats

    print(f"   Total Decisions: {stats.total_decisions}")
    print(f"   Successful: {stats.successful}")
    print(f"   Partial: {stats.partial}")
    print(f"   Failed: {stats.failed}")
    print(f"   Avg Confidence: {stats.avg_confidence:.3f}")
    print(f"   Utility Accuracy: {stats.utility_accuracy:.3f}")
    print()

    # 11. Summary
    print("11. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Decision Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
