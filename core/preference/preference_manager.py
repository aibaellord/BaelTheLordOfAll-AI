#!/usr/bin/env python3
"""
BAEL - Preference Manager
Advanced preference learning and personalization.

Features:
- Preference modeling
- Preference learning from feedback
- Multi-attribute utility
- Preference aggregation
- Pareto optimization
- Trade-off analysis
- Preference elicitation
- Adaptive personalization
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

class PreferenceType(Enum):
    """Types of preferences."""
    ORDINAL = "ordinal"  # Ranking
    CARDINAL = "cardinal"  # Numerical scores
    BINARY = "binary"  # Like/dislike
    INTERVAL = "interval"  # Ranges
    COMPARATIVE = "comparative"  # Pairwise comparisons


class FeedbackType(Enum):
    """Types of feedback."""
    EXPLICIT = "explicit"  # Direct ratings
    IMPLICIT = "implicit"  # Behavioral signals
    COMPARISON = "comparison"  # A vs B
    RANKING = "ranking"  # Ordered list


class AggregationMethod(Enum):
    """Methods for aggregating preferences."""
    WEIGHTED_SUM = "weighted_sum"
    BORDA_COUNT = "borda_count"
    CONDORCET = "condorcet"
    PLURALITY = "plurality"
    APPROVAL = "approval"


class LearningMethod(Enum):
    """Methods for learning preferences."""
    BANDIT = "bandit"
    BAYESIAN = "bayesian"
    REGRESSION = "regression"
    COLLABORATIVE = "collaborative"


class TradeoffType(Enum):
    """Types of trade-offs."""
    LINEAR = "linear"
    CONVEX = "convex"
    CONCAVE = "concave"
    LEXICOGRAPHIC = "lexicographic"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Preference:
    """A preference specification."""
    preference_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    attribute: str = ""
    preference_type: PreferenceType = PreferenceType.CARDINAL
    value: Any = None
    weight: float = 1.0
    confidence: float = 1.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class PreferenceProfile:
    """A user's preference profile."""
    profile_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    preferences: Dict[str, Preference] = field(default_factory=dict)
    attribute_weights: Dict[str, float] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class Feedback:
    """User feedback."""
    feedback_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    feedback_type: FeedbackType = FeedbackType.EXPLICIT
    item_id: str = ""
    value: Any = None
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class Item:
    """An item with attributes."""
    item_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    attributes: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Recommendation:
    """A recommendation."""
    recommendation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    item_id: str = ""
    score: float = 0.0
    confidence: float = 0.0
    explanation: str = ""


@dataclass
class TradeoffAnalysis:
    """Result of trade-off analysis."""
    analysis_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    attribute1: str = ""
    attribute2: str = ""
    tradeoff_type: TradeoffType = TradeoffType.LINEAR
    slope: float = 0.0
    optimal_points: List[Dict[str, float]] = field(default_factory=list)


# =============================================================================
# UTILITY FUNCTION
# =============================================================================

class UtilityFunction:
    """Multi-attribute utility function."""

    def __init__(self):
        self._attribute_functions: Dict[str, Callable[[float], float]] = {}
        self._weights: Dict[str, float] = {}

    def set_attribute_function(
        self,
        attribute: str,
        function: Callable[[float], float],
        weight: float = 1.0
    ) -> None:
        """Set utility function for an attribute."""
        self._attribute_functions[attribute] = function
        self._weights[attribute] = weight

    def set_linear_attribute(
        self,
        attribute: str,
        weight: float = 1.0,
        ideal_value: float = 1.0
    ) -> None:
        """Set linear utility for attribute."""
        def linear_utility(x: float) -> float:
            return x / ideal_value if ideal_value != 0 else 0

        self._attribute_functions[attribute] = linear_utility
        self._weights[attribute] = weight

    def set_diminishing_returns(
        self,
        attribute: str,
        weight: float = 1.0,
        saturation: float = 1.0
    ) -> None:
        """Set diminishing returns utility."""
        def diminishing_utility(x: float) -> float:
            return 1 - math.exp(-x / saturation) if saturation != 0 else 0

        self._attribute_functions[attribute] = diminishing_utility
        self._weights[attribute] = weight

    def compute_utility(
        self,
        item: Item
    ) -> float:
        """Compute utility of an item."""
        total_utility = 0.0
        total_weight = sum(self._weights.values())

        if total_weight == 0:
            return 0.0

        for attr, value in item.attributes.items():
            if attr in self._attribute_functions:
                func = self._attribute_functions[attr]
                weight = self._weights.get(attr, 1.0)
                total_utility += weight * func(value)

        return total_utility / total_weight


# =============================================================================
# PREFERENCE LEARNER
# =============================================================================

class PreferenceLearner:
    """Learn preferences from feedback."""

    def __init__(self, method: LearningMethod = LearningMethod.BANDIT):
        self._method = method
        self._feedback_history: List[Feedback] = []
        self._learned_weights: Dict[str, float] = {}
        self._counts: Dict[str, int] = defaultdict(int)
        self._values: Dict[str, float] = defaultdict(float)

    def add_feedback(self, feedback: Feedback) -> None:
        """Add feedback for learning."""
        self._feedback_history.append(feedback)

    def learn(self, user_id: str) -> Dict[str, float]:
        """Learn preference weights from feedback."""
        user_feedback = [
            f for f in self._feedback_history
            if f.user_id == user_id
        ]

        if not user_feedback:
            return {}

        if self._method == LearningMethod.BANDIT:
            return self._learn_bandit(user_feedback)
        elif self._method == LearningMethod.BAYESIAN:
            return self._learn_bayesian(user_feedback)
        elif self._method == LearningMethod.REGRESSION:
            return self._learn_regression(user_feedback)

        return {}

    def _learn_bandit(self, feedback: List[Feedback]) -> Dict[str, float]:
        """Learn using multi-armed bandit approach."""
        attribute_values: Dict[str, List[float]] = defaultdict(list)

        for f in feedback:
            if f.feedback_type == FeedbackType.EXPLICIT:
                # Assume value is a rating and context contains attributes
                for attr, attr_value in f.context.items():
                    if isinstance(attr_value, (int, float)):
                        # Higher rating means preference for high attribute value
                        weight = f.value * attr_value if isinstance(f.value, (int, float)) else 0
                        attribute_values[attr].append(weight)

        # Compute average weights
        weights = {}
        for attr, values in attribute_values.items():
            if values:
                weights[attr] = sum(values) / len(values)

        return weights

    def _learn_bayesian(self, feedback: List[Feedback]) -> Dict[str, float]:
        """Learn using Bayesian approach."""
        # Prior: uniform weights
        weights: Dict[str, float] = {}
        counts: Dict[str, int] = defaultdict(int)

        for f in feedback:
            if f.feedback_type == FeedbackType.COMPARISON:
                # Comparison: value is (item1, item2, preferred)
                if isinstance(f.value, tuple) and len(f.value) >= 3:
                    item1, item2, preferred = f.value[:3]
                    # Update weights based on preference
                    for attr in f.context.get("attributes", []):
                        if attr not in weights:
                            weights[attr] = 0.5

                        # Update with pseudo-count
                        counts[attr] += 1
                        alpha = 1.0 / counts[attr]

                        if preferred == item1:
                            weights[attr] = weights[attr] * (1 - alpha) + 1.0 * alpha
                        else:
                            weights[attr] = weights[attr] * (1 - alpha) + 0.0 * alpha

        return weights

    def _learn_regression(self, feedback: List[Feedback]) -> Dict[str, float]:
        """Learn using linear regression."""
        # Collect data points
        X = []  # Features
        y = []  # Ratings

        attributes = set()

        for f in feedback:
            if f.feedback_type == FeedbackType.EXPLICIT:
                if isinstance(f.value, (int, float)):
                    features = f.context.copy()
                    X.append(features)
                    y.append(f.value)
                    attributes.update(features.keys())

        if not X or not y:
            return {}

        # Simple gradient descent
        weights = {attr: random.random() for attr in attributes}
        lr = 0.01

        for _ in range(100):  # 100 iterations
            for features, target in zip(X, y):
                pred = sum(
                    weights.get(attr, 0) * val
                    for attr, val in features.items()
                    if isinstance(val, (int, float))
                )
                error = target - pred

                for attr, val in features.items():
                    if isinstance(val, (int, float)) and attr in weights:
                        weights[attr] += lr * error * val

        return weights


# =============================================================================
# PREFERENCE AGGREGATOR
# =============================================================================

class PreferenceAggregator:
    """Aggregate preferences from multiple sources."""

    def __init__(self, method: AggregationMethod = AggregationMethod.WEIGHTED_SUM):
        self._method = method

    def aggregate(
        self,
        preferences: List[Preference]
    ) -> Dict[str, float]:
        """Aggregate preferences."""
        if not preferences:
            return {}

        if self._method == AggregationMethod.WEIGHTED_SUM:
            return self._weighted_sum(preferences)
        elif self._method == AggregationMethod.BORDA_COUNT:
            return self._borda_count(preferences)
        elif self._method == AggregationMethod.CONDORCET:
            return self._condorcet(preferences)
        elif self._method == AggregationMethod.PLURALITY:
            return self._plurality(preferences)

        return {}

    def _weighted_sum(self, preferences: List[Preference]) -> Dict[str, float]:
        """Aggregate using weighted sum."""
        totals: Dict[str, float] = defaultdict(float)
        weights: Dict[str, float] = defaultdict(float)

        for pref in preferences:
            if isinstance(pref.value, (int, float)):
                totals[pref.attribute] += pref.value * pref.weight * pref.confidence
                weights[pref.attribute] += pref.weight * pref.confidence

        return {
            attr: totals[attr] / weights[attr] if weights[attr] > 0 else 0
            for attr in totals
        }

    def _borda_count(self, preferences: List[Preference]) -> Dict[str, float]:
        """Aggregate using Borda count."""
        scores: Dict[str, float] = defaultdict(float)

        # Group by user
        user_prefs: Dict[str, List[Preference]] = defaultdict(list)
        for pref in preferences:
            user_prefs[pref.user_id].append(pref)

        for user_id, prefs in user_prefs.items():
            if prefs and prefs[0].preference_type == PreferenceType.ORDINAL:
                # Sort by value (rank)
                sorted_prefs = sorted(
                    prefs,
                    key=lambda p: p.value if isinstance(p.value, (int, float)) else 0,
                    reverse=True
                )

                n = len(sorted_prefs)
                for rank, pref in enumerate(sorted_prefs):
                    scores[pref.attribute] += n - rank - 1

        return dict(scores)

    def _condorcet(self, preferences: List[Preference]) -> Dict[str, float]:
        """Aggregate using Condorcet method."""
        # Count pairwise wins
        wins: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

        # Group by user
        user_prefs: Dict[str, List[Preference]] = defaultdict(list)
        for pref in preferences:
            user_prefs[pref.user_id].append(pref)

        for prefs in user_prefs.values():
            if prefs and prefs[0].preference_type == PreferenceType.COMPARATIVE:
                # Each pref.value should be (winner, loser)
                for pref in prefs:
                    if isinstance(pref.value, tuple) and len(pref.value) >= 2:
                        winner, loser = pref.value[:2]
                        wins[winner][loser] += 1

        # Count total wins
        total_wins = {}
        all_items = set(wins.keys())
        for w in wins.values():
            all_items.update(w.keys())

        for item in all_items:
            total_wins[item] = sum(wins[item].values())

        return total_wins

    def _plurality(self, preferences: List[Preference]) -> Dict[str, float]:
        """Aggregate using plurality voting."""
        votes: Dict[str, int] = defaultdict(int)

        for pref in preferences:
            if pref.preference_type == PreferenceType.BINARY:
                if pref.value:  # True = vote for
                    votes[pref.attribute] += 1

        return dict(votes)

    def aggregate_rankings(
        self,
        rankings: List[List[str]]
    ) -> List[str]:
        """Aggregate multiple rankings into one."""
        # Use Borda count
        scores: Dict[str, float] = defaultdict(float)

        for ranking in rankings:
            n = len(ranking)
            for rank, item in enumerate(ranking):
                scores[item] += n - rank

        # Sort by score
        return sorted(scores.keys(), key=lambda x: scores[x], reverse=True)


# =============================================================================
# PARETO OPTIMIZER
# =============================================================================

class ParetoOptimizer:
    """Find Pareto-optimal solutions."""

    def __init__(self):
        self._objectives: Dict[str, bool] = {}  # attr -> maximize

    def add_objective(
        self,
        attribute: str,
        maximize: bool = True
    ) -> None:
        """Add an objective."""
        self._objectives[attribute] = maximize

    def is_dominated(
        self,
        item1: Item,
        item2: Item
    ) -> bool:
        """Check if item1 is Pareto-dominated by item2."""
        all_worse = True
        any_strictly_worse = False

        for attr, maximize in self._objectives.items():
            v1 = item1.attributes.get(attr, 0)
            v2 = item2.attributes.get(attr, 0)

            if maximize:
                if v1 > v2:
                    all_worse = False
                if v2 > v1:
                    any_strictly_worse = True
            else:
                if v1 < v2:
                    all_worse = False
                if v2 < v1:
                    any_strictly_worse = True

        return all_worse and any_strictly_worse

    def find_pareto_front(
        self,
        items: List[Item]
    ) -> List[Item]:
        """Find Pareto-optimal items."""
        pareto = []

        for item in items:
            is_dominated = False
            for other in items:
                if item != other and self.is_dominated(item, other):
                    is_dominated = True
                    break

            if not is_dominated:
                pareto.append(item)

        return pareto

    def hypervolume(
        self,
        items: List[Item],
        reference_point: Dict[str, float]
    ) -> float:
        """Compute hypervolume indicator (simplified 2D)."""
        if len(self._objectives) != 2:
            return 0.0  # Only support 2D

        attrs = list(self._objectives.keys())

        # Sort by first objective
        sorted_items = sorted(
            items,
            key=lambda x: x.attributes.get(attrs[0], 0)
        )

        volume = 0.0
        prev_y = reference_point.get(attrs[1], 0)

        for item in sorted_items:
            x = item.attributes.get(attrs[0], 0)
            y = item.attributes.get(attrs[1], 0)

            ref_x = reference_point.get(attrs[0], 0)

            width = x - ref_x
            height = prev_y - y

            if width > 0 and height > 0:
                volume += width * height

            prev_y = min(prev_y, y)

        return volume


# =============================================================================
# ELICITATION ENGINE
# =============================================================================

class ElicitationEngine:
    """Elicit preferences from users."""

    def __init__(self):
        self._questions_asked: List[Dict[str, Any]] = []
        self._uncertainty: Dict[str, float] = {}

    def generate_comparison_question(
        self,
        items: List[Item]
    ) -> Tuple[Item, Item]:
        """Generate a pairwise comparison question."""
        if len(items) < 2:
            raise ValueError("Need at least 2 items")

        # Select items that maximize information gain
        # Simple: random selection for now
        i, j = random.sample(range(len(items)), 2)
        return items[i], items[j]

    def generate_rating_question(
        self,
        items: List[Item],
        attributes: List[str]
    ) -> Tuple[Item, str]:
        """Generate a rating question."""
        if not items or not attributes:
            raise ValueError("Need items and attributes")

        # Select item and attribute with highest uncertainty
        best_item = items[0]
        best_attr = attributes[0]
        best_uncertainty = 0.0

        for item in items:
            for attr in attributes:
                key = f"{item.item_id}_{attr}"
                uncertainty = self._uncertainty.get(key, 1.0)
                if uncertainty > best_uncertainty:
                    best_uncertainty = uncertainty
                    best_item = item
                    best_attr = attr

        return best_item, best_attr

    def process_comparison_response(
        self,
        item1: Item,
        item2: Item,
        preferred: Item,
        profile: PreferenceProfile
    ) -> None:
        """Process comparison response."""
        # Update uncertainty
        for attr in item1.attributes:
            if attr in item2.attributes:
                key1 = f"{item1.item_id}_{attr}"
                key2 = f"{item2.item_id}_{attr}"

                # Reduce uncertainty for compared attributes
                self._uncertainty[key1] = self._uncertainty.get(key1, 1.0) * 0.8
                self._uncertainty[key2] = self._uncertainty.get(key2, 1.0) * 0.8

                # Update preference weights
                v1 = item1.attributes.get(attr, 0)
                v2 = item2.attributes.get(attr, 0)

                if preferred == item1 and v1 > v2:
                    # User prefers higher values
                    profile.attribute_weights[attr] = profile.attribute_weights.get(attr, 0.5) * 1.1
                elif preferred == item2 and v2 > v1:
                    profile.attribute_weights[attr] = profile.attribute_weights.get(attr, 0.5) * 1.1

    def estimate_iterations_needed(
        self,
        num_items: int,
        num_attributes: int,
        target_uncertainty: float = 0.1
    ) -> int:
        """Estimate number of questions needed."""
        # Heuristic based on information theory
        total_parameters = num_items * num_attributes
        current_uncertainty = 1.0
        iterations = 0

        while current_uncertainty > target_uncertainty and iterations < 1000:
            # Each question reduces uncertainty by ~20%
            current_uncertainty *= 0.8
            iterations += 1

        return min(iterations, total_parameters * 2)


# =============================================================================
# PREFERENCE MANAGER
# =============================================================================

class PreferenceManager:
    """
    Preference Manager for BAEL.

    Advanced preference learning and personalization.
    """

    def __init__(self):
        self._profiles: Dict[str, PreferenceProfile] = {}
        self._items: Dict[str, Item] = {}
        self._learner = PreferenceLearner(LearningMethod.BANDIT)
        self._aggregator = PreferenceAggregator(AggregationMethod.WEIGHTED_SUM)
        self._pareto = ParetoOptimizer()
        self._elicitation = ElicitationEngine()
        self._utility_functions: Dict[str, UtilityFunction] = {}

    # -------------------------------------------------------------------------
    # PROFILE MANAGEMENT
    # -------------------------------------------------------------------------

    def create_profile(self, user_id: str) -> PreferenceProfile:
        """Create a new preference profile."""
        profile = PreferenceProfile(user_id=user_id)
        self._profiles[user_id] = profile
        return profile

    def get_profile(self, user_id: str) -> Optional[PreferenceProfile]:
        """Get user's preference profile."""
        return self._profiles.get(user_id)

    def update_preference(
        self,
        user_id: str,
        attribute: str,
        value: Any,
        preference_type: PreferenceType = PreferenceType.CARDINAL,
        weight: float = 1.0
    ) -> Preference:
        """Update a preference."""
        profile = self._profiles.get(user_id)
        if not profile:
            profile = self.create_profile(user_id)

        pref = Preference(
            user_id=user_id,
            attribute=attribute,
            preference_type=preference_type,
            value=value,
            weight=weight
        )

        profile.preferences[attribute] = pref
        profile.updated_at = time.time()

        return pref

    # -------------------------------------------------------------------------
    # ITEM MANAGEMENT
    # -------------------------------------------------------------------------

    def add_item(
        self,
        name: str,
        attributes: Dict[str, float]
    ) -> Item:
        """Add an item."""
        item = Item(name=name, attributes=attributes)
        self._items[item.item_id] = item
        return item

    def get_item(self, item_id: str) -> Optional[Item]:
        """Get an item."""
        return self._items.get(item_id)

    def get_all_items(self) -> List[Item]:
        """Get all items."""
        return list(self._items.values())

    # -------------------------------------------------------------------------
    # FEEDBACK
    # -------------------------------------------------------------------------

    def record_feedback(
        self,
        user_id: str,
        item_id: str,
        value: Any,
        feedback_type: FeedbackType = FeedbackType.EXPLICIT,
        context: Optional[Dict[str, Any]] = None
    ) -> Feedback:
        """Record user feedback."""
        feedback = Feedback(
            user_id=user_id,
            item_id=item_id,
            value=value,
            feedback_type=feedback_type,
            context=context or {}
        )

        self._learner.add_feedback(feedback)

        return feedback

    def learn_preferences(self, user_id: str) -> Dict[str, float]:
        """Learn preferences from feedback."""
        weights = self._learner.learn(user_id)

        # Update profile
        profile = self._profiles.get(user_id)
        if profile:
            profile.attribute_weights.update(weights)
            profile.updated_at = time.time()

        return weights

    # -------------------------------------------------------------------------
    # UTILITY
    # -------------------------------------------------------------------------

    def create_utility_function(self, user_id: str) -> UtilityFunction:
        """Create utility function for user."""
        utility = UtilityFunction()
        self._utility_functions[user_id] = utility
        return utility

    def get_utility_function(self, user_id: str) -> Optional[UtilityFunction]:
        """Get user's utility function."""
        return self._utility_functions.get(user_id)

    def compute_item_utility(
        self,
        user_id: str,
        item_id: str
    ) -> float:
        """Compute utility of an item for a user."""
        utility = self._utility_functions.get(user_id)
        item = self._items.get(item_id)

        if not utility or not item:
            return 0.0

        return utility.compute_utility(item)

    # -------------------------------------------------------------------------
    # RECOMMENDATIONS
    # -------------------------------------------------------------------------

    def recommend(
        self,
        user_id: str,
        top_k: int = 5
    ) -> List[Recommendation]:
        """Generate recommendations for user."""
        profile = self._profiles.get(user_id)
        utility = self._utility_functions.get(user_id)

        if not profile and not utility:
            return []

        recommendations = []

        for item in self._items.values():
            if utility:
                score = utility.compute_utility(item)
            else:
                # Use profile weights
                score = 0.0
                for attr, value in item.attributes.items():
                    weight = profile.attribute_weights.get(attr, 0.5) if profile else 0.5
                    score += weight * value

            rec = Recommendation(
                user_id=user_id,
                item_id=item.item_id,
                score=score,
                confidence=0.8,
                explanation=f"Based on your preferences"
            )
            recommendations.append(rec)

        # Sort by score and return top k
        recommendations.sort(key=lambda r: r.score, reverse=True)
        return recommendations[:top_k]

    # -------------------------------------------------------------------------
    # PARETO OPTIMIZATION
    # -------------------------------------------------------------------------

    def add_objective(
        self,
        attribute: str,
        maximize: bool = True
    ) -> None:
        """Add optimization objective."""
        self._pareto.add_objective(attribute, maximize)

    def find_pareto_optimal(self) -> List[Item]:
        """Find Pareto-optimal items."""
        return self._pareto.find_pareto_front(list(self._items.values()))

    # -------------------------------------------------------------------------
    # AGGREGATION
    # -------------------------------------------------------------------------

    def aggregate_preferences(
        self,
        user_ids: List[str]
    ) -> Dict[str, float]:
        """Aggregate preferences from multiple users."""
        all_prefs = []

        for user_id in user_ids:
            profile = self._profiles.get(user_id)
            if profile:
                all_prefs.extend(profile.preferences.values())

        return self._aggregator.aggregate(all_prefs)

    # -------------------------------------------------------------------------
    # ELICITATION
    # -------------------------------------------------------------------------

    def ask_comparison(self) -> Tuple[Item, Item]:
        """Generate a comparison question."""
        items = list(self._items.values())
        if len(items) < 2:
            raise ValueError("Need at least 2 items")
        return self._elicitation.generate_comparison_question(items)

    def answer_comparison(
        self,
        user_id: str,
        item1: Item,
        item2: Item,
        preferred: Item
    ) -> None:
        """Process comparison answer."""
        profile = self._profiles.get(user_id)
        if not profile:
            profile = self.create_profile(user_id)

        self._elicitation.process_comparison_response(
            item1, item2, preferred, profile
        )

    # -------------------------------------------------------------------------
    # TRADE-OFF ANALYSIS
    # -------------------------------------------------------------------------

    def analyze_tradeoffs(
        self,
        attribute1: str,
        attribute2: str
    ) -> TradeoffAnalysis:
        """Analyze trade-offs between attributes."""
        items = list(self._items.values())

        # Get Pareto front for these two attributes
        self._pareto._objectives = {attribute1: True, attribute2: True}
        pareto_items = self._pareto.find_pareto_front(items)

        # Compute slope
        if len(pareto_items) >= 2:
            values = [
                (
                    item.attributes.get(attribute1, 0),
                    item.attributes.get(attribute2, 0)
                )
                for item in pareto_items
            ]
            values.sort()

            if len(values) >= 2:
                dx = values[-1][0] - values[0][0]
                dy = values[-1][1] - values[0][1]
                slope = dy / dx if dx != 0 else 0
            else:
                slope = 0
        else:
            slope = 0

        return TradeoffAnalysis(
            attribute1=attribute1,
            attribute2=attribute2,
            tradeoff_type=TradeoffType.LINEAR if abs(slope) > 0.1 else TradeoffType.CONVEX,
            slope=slope,
            optimal_points=[
                {"item": item.name, **item.attributes}
                for item in pareto_items
            ]
        )


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Preference Manager."""
    print("=" * 70)
    print("BAEL - PREFERENCE MANAGER DEMO")
    print("Advanced Preference Learning and Personalization")
    print("=" * 70)
    print()

    manager = PreferenceManager()

    # 1. Create Items
    print("1. CREATE ITEMS:")
    print("-" * 40)

    items = [
        manager.add_item("Laptop A", {"price": 1000, "performance": 0.8, "portability": 0.6}),
        manager.add_item("Laptop B", {"price": 1500, "performance": 0.9, "portability": 0.7}),
        manager.add_item("Laptop C", {"price": 800, "performance": 0.6, "portability": 0.9}),
        manager.add_item("Laptop D", {"price": 2000, "performance": 0.95, "portability": 0.5}),
        manager.add_item("Laptop E", {"price": 1200, "performance": 0.85, "portability": 0.75}),
    ]

    for item in items:
        print(f"   {item.name}: price=${item.attributes['price']}, "
              f"perf={item.attributes['performance']}, port={item.attributes['portability']}")
    print()

    # 2. Create User Profile
    print("2. CREATE USER PROFILE:")
    print("-" * 40)

    profile = manager.create_profile("user_1")
    print(f"   Created profile for user_1")

    # Set initial preferences
    manager.update_preference("user_1", "performance", 0.8, PreferenceType.CARDINAL, weight=1.5)
    manager.update_preference("user_1", "portability", 0.7, PreferenceType.CARDINAL, weight=1.0)
    manager.update_preference("user_1", "price", 0.5, PreferenceType.CARDINAL, weight=0.8)

    print(f"   Preferences set: performance=0.8 (w=1.5), portability=0.7 (w=1.0), price=0.5 (w=0.8)")
    print()

    # 3. Create Utility Function
    print("3. CREATE UTILITY FUNCTION:")
    print("-" * 40)

    utility = manager.create_utility_function("user_1")
    utility.set_linear_attribute("performance", weight=1.5, ideal_value=1.0)
    utility.set_diminishing_returns("portability", weight=1.0, saturation=0.8)
    utility.set_linear_attribute("price", weight=-0.8, ideal_value=2000)  # Lower is better

    print("   Performance: linear (weight=1.5)")
    print("   Portability: diminishing returns (weight=1.0)")
    print("   Price: linear negative (weight=-0.8)")
    print()

    # 4. Compute Utilities
    print("4. ITEM UTILITIES:")
    print("-" * 40)

    for item in items:
        u = manager.compute_item_utility("user_1", item.item_id)
        print(f"   {item.name}: utility = {u:.3f}")
    print()

    # 5. Generate Recommendations
    print("5. RECOMMENDATIONS:")
    print("-" * 40)

    recs = manager.recommend("user_1", top_k=3)
    for i, rec in enumerate(recs, 1):
        item = manager.get_item(rec.item_id)
        print(f"   {i}. {item.name if item else 'Unknown'} (score: {rec.score:.3f})")
    print()

    # 6. Record Feedback
    print("6. RECORD FEEDBACK:")
    print("-" * 40)

    # User provides ratings
    manager.record_feedback(
        "user_1", items[1].item_id, 4.5,
        FeedbackType.EXPLICIT,
        {"performance": 0.9, "portability": 0.7}
    )
    manager.record_feedback(
        "user_1", items[2].item_id, 3.0,
        FeedbackType.EXPLICIT,
        {"performance": 0.6, "portability": 0.9}
    )

    print("   Recorded: Laptop B = 4.5, Laptop C = 3.0")

    # Learn from feedback
    learned = manager.learn_preferences("user_1")
    print(f"   Learned weights: {learned}")
    print()

    # 7. Pareto Optimization
    print("7. PARETO OPTIMIZATION:")
    print("-" * 40)

    manager.add_objective("performance", maximize=True)
    manager.add_objective("portability", maximize=True)

    pareto_items = manager.find_pareto_optimal()
    print(f"   Pareto-optimal items:")
    for item in pareto_items:
        print(f"     - {item.name}")
    print()

    # 8. Preference Aggregation
    print("8. PREFERENCE AGGREGATION:")
    print("-" * 40)

    # Create another user
    manager.create_profile("user_2")
    manager.update_preference("user_2", "performance", 0.6, PreferenceType.CARDINAL, weight=1.0)
    manager.update_preference("user_2", "portability", 0.9, PreferenceType.CARDINAL, weight=1.5)
    manager.update_preference("user_2", "price", 0.8, PreferenceType.CARDINAL, weight=1.2)

    aggregated = manager.aggregate_preferences(["user_1", "user_2"])
    print(f"   Aggregated preferences:")
    for attr, val in aggregated.items():
        print(f"     {attr}: {val:.3f}")
    print()

    # 9. Trade-off Analysis
    print("9. TRADE-OFF ANALYSIS:")
    print("-" * 40)

    tradeoff = manager.analyze_tradeoffs("performance", "portability")
    print(f"   Attributes: {tradeoff.attribute1} vs {tradeoff.attribute2}")
    print(f"   Trade-off type: {tradeoff.tradeoff_type.value}")
    print(f"   Slope: {tradeoff.slope:.3f}")
    print(f"   Optimal points: {len(tradeoff.optimal_points)}")
    print()

    # 10. Elicitation
    print("10. PREFERENCE ELICITATION:")
    print("-" * 40)

    try:
        item1, item2 = manager.ask_comparison()
        print(f"   Question: Do you prefer {item1.name} or {item2.name}?")

        # Simulate user answer
        preferred = item1 if random.random() > 0.5 else item2
        print(f"   User answered: {preferred.name}")

        manager.answer_comparison("user_1", item1, item2, preferred)
        print("   Preferences updated based on response")
    except ValueError as e:
        print(f"   Error: {e}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Preference Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
