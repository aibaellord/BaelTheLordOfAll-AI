#!/usr/bin/env python3
"""
BAEL - Preference Learner
Advanced preference learning from data and feedback.

Features:
- Learn from pairwise comparisons
- Learn from ratings
- Active preference learning
- Preference model fitting
- Utility function estimation
- Preference drift detection
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

class ComparisonResult(Enum):
    """Result of a pairwise comparison."""
    FIRST_PREFERRED = "first_preferred"  # A > B
    SECOND_PREFERRED = "second_preferred"  # B > A
    INDIFFERENT = "indifferent"  # A ~ B
    INCOMPARABLE = "incomparable"  # Can't compare


class LearningMethod(Enum):
    """Preference learning methods."""
    BRADLEY_TERRY = "bradley_terry"
    ELO = "elo"
    PLACKETT_LUCE = "plackett_luce"
    THURSTONE = "thurstone"
    REGRESSION = "regression"


class QueryStrategy(Enum):
    """Active learning query strategies."""
    RANDOM = "random"
    UNCERTAINTY = "uncertainty"
    EXPECTED_INFO_GAIN = "expected_info_gain"
    QUERY_BY_COMMITTEE = "query_by_committee"


class ModelType(Enum):
    """Preference model types."""
    LINEAR = "linear"
    NONLINEAR = "nonlinear"
    LEXICOGRAPHIC = "lexicographic"
    WEIGHTED_SUM = "weighted_sum"


class DriftType(Enum):
    """Types of preference drift."""
    NO_DRIFT = "no_drift"
    GRADUAL = "gradual"
    SUDDEN = "sudden"
    RECURRING = "recurring"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Item:
    """An item with features."""
    item_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    features: Dict[str, float] = field(default_factory=dict)
    utility: float = 0.0


@dataclass
class Comparison:
    """A pairwise comparison."""
    comp_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    item1: str = ""  # Item ID
    item2: str = ""  # Item ID
    result: ComparisonResult = ComparisonResult.INDIFFERENT
    confidence: float = 1.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Rating:
    """A rating for an item."""
    rating_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    item_id: str = ""
    value: float = 0.0
    max_value: float = 5.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PreferenceModel:
    """A learned preference model."""
    model_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    model_type: ModelType = ModelType.LINEAR
    weights: Dict[str, float] = field(default_factory=dict)
    parameters: Dict[str, float] = field(default_factory=dict)
    accuracy: float = 0.0


@dataclass
class LearningResult:
    """Result of preference learning."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    method: LearningMethod = LearningMethod.BRADLEY_TERRY
    num_comparisons: int = 0
    num_iterations: int = 0
    convergence: float = 0.0
    model: Optional[PreferenceModel] = None


@dataclass
class DriftDetection:
    """Result of drift detection."""
    detection_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    drift_type: DriftType = DriftType.NO_DRIFT
    drift_magnitude: float = 0.0
    change_point: Optional[datetime] = None


# =============================================================================
# ITEM MANAGER
# =============================================================================

class ItemManager:
    """Manage items."""

    def __init__(self):
        self._items: Dict[str, Item] = {}

    def add(
        self,
        name: str,
        features: Dict[str, float]
    ) -> Item:
        """Add an item."""
        item = Item(name=name, features=features)
        self._items[item.item_id] = item
        return item

    def get(self, item_id: str) -> Optional[Item]:
        """Get an item."""
        return self._items.get(item_id)

    def all_items(self) -> List[Item]:
        """Get all items."""
        return list(self._items.values())

    def feature_names(self) -> Set[str]:
        """Get all feature names."""
        features: Set[str] = set()
        for item in self._items.values():
            features.update(item.features.keys())
        return features


# =============================================================================
# COMPARISON COLLECTOR
# =============================================================================

class ComparisonCollector:
    """Collect and manage pairwise comparisons."""

    def __init__(self):
        self._comparisons: List[Comparison] = []
        self._by_item: Dict[str, List[Comparison]] = defaultdict(list)

    def add(
        self,
        item1: str,
        item2: str,
        result: ComparisonResult,
        confidence: float = 1.0
    ) -> Comparison:
        """Add a comparison."""
        comp = Comparison(
            item1=item1,
            item2=item2,
            result=result,
            confidence=confidence
        )
        self._comparisons.append(comp)
        self._by_item[item1].append(comp)
        self._by_item[item2].append(comp)
        return comp

    def all_comparisons(self) -> List[Comparison]:
        """Get all comparisons."""
        return self._comparisons.copy()

    def comparisons_for(self, item_id: str) -> List[Comparison]:
        """Get comparisons involving an item."""
        return self._by_item.get(item_id, [])

    def win_loss_record(self, item_id: str) -> Tuple[int, int, int]:
        """Get win/loss/tie record for an item."""
        wins, losses, ties = 0, 0, 0

        for comp in self.comparisons_for(item_id):
            if comp.item1 == item_id:
                if comp.result == ComparisonResult.FIRST_PREFERRED:
                    wins += 1
                elif comp.result == ComparisonResult.SECOND_PREFERRED:
                    losses += 1
                else:
                    ties += 1
            else:
                if comp.result == ComparisonResult.SECOND_PREFERRED:
                    wins += 1
                elif comp.result == ComparisonResult.FIRST_PREFERRED:
                    losses += 1
                else:
                    ties += 1

        return wins, losses, ties


# =============================================================================
# BRADLEY-TERRY MODEL
# =============================================================================

class BradleyTerryLearner:
    """Learn preferences using Bradley-Terry model."""

    def __init__(self):
        self._strengths: Dict[str, float] = {}

    def learn(
        self,
        comparisons: List[Comparison],
        items: List[Item],
        max_iterations: int = 100,
        tolerance: float = 1e-6
    ) -> LearningResult:
        """Learn strength parameters from comparisons."""
        # Initialize strengths
        for item in items:
            self._strengths[item.item_id] = 1.0

        for iteration in range(max_iterations):
            old_strengths = self._strengths.copy()

            # Update each strength
            for item in items:
                item_id = item.item_id

                numerator = 0.0
                denominator = 0.0

                for comp in comparisons:
                    if comp.item1 == item_id or comp.item2 == item_id:
                        other_id = comp.item2 if comp.item1 == item_id else comp.item1
                        other_strength = self._strengths.get(other_id, 1.0)
                        my_strength = self._strengths.get(item_id, 1.0)

                        # Count wins for this item
                        if comp.item1 == item_id and comp.result == ComparisonResult.FIRST_PREFERRED:
                            numerator += 1
                        elif comp.item2 == item_id and comp.result == ComparisonResult.SECOND_PREFERRED:
                            numerator += 1

                        denominator += 1.0 / (my_strength + other_strength)

                if denominator > 0:
                    self._strengths[item_id] = numerator / denominator

            # Normalize
            total = sum(self._strengths.values())
            if total > 0:
                for item_id in self._strengths:
                    self._strengths[item_id] /= total
                    self._strengths[item_id] *= len(items)

            # Check convergence
            max_change = max(
                abs(self._strengths[k] - old_strengths[k])
                for k in self._strengths
            )

            if max_change < tolerance:
                break

        # Create model
        model = PreferenceModel(
            model_type=ModelType.LINEAR,
            parameters={"strengths": self._strengths.copy()}
        )

        return LearningResult(
            method=LearningMethod.BRADLEY_TERRY,
            num_comparisons=len(comparisons),
            num_iterations=iteration + 1,
            convergence=max_change,
            model=model
        )

    def get_strength(self, item_id: str) -> float:
        """Get learned strength for an item."""
        return self._strengths.get(item_id, 0.0)

    def predict(self, item1: str, item2: str) -> float:
        """Predict probability that item1 is preferred to item2."""
        s1 = self._strengths.get(item1, 1.0)
        s2 = self._strengths.get(item2, 1.0)

        if s1 + s2 == 0:
            return 0.5

        return s1 / (s1 + s2)


# =============================================================================
# ELO RATING SYSTEM
# =============================================================================

class EloLearner:
    """Learn preferences using Elo rating system."""

    def __init__(self, k_factor: float = 32.0, initial_rating: float = 1500.0):
        self._k = k_factor
        self._initial = initial_rating
        self._ratings: Dict[str, float] = {}

    def learn(
        self,
        comparisons: List[Comparison],
        items: List[Item]
    ) -> LearningResult:
        """Learn ratings from comparisons."""
        # Initialize ratings
        for item in items:
            self._ratings[item.item_id] = self._initial

        # Process comparisons in order
        for comp in comparisons:
            self._update(comp)

        model = PreferenceModel(
            model_type=ModelType.LINEAR,
            parameters={"ratings": self._ratings.copy(), "k": self._k}
        )

        return LearningResult(
            method=LearningMethod.ELO,
            num_comparisons=len(comparisons),
            num_iterations=len(comparisons),
            model=model
        )

    def _update(self, comp: Comparison) -> None:
        """Update ratings based on comparison."""
        r1 = self._ratings.get(comp.item1, self._initial)
        r2 = self._ratings.get(comp.item2, self._initial)

        # Expected scores
        e1 = 1.0 / (1.0 + 10 ** ((r2 - r1) / 400.0))
        e2 = 1.0 - e1

        # Actual scores
        if comp.result == ComparisonResult.FIRST_PREFERRED:
            s1, s2 = 1.0, 0.0
        elif comp.result == ComparisonResult.SECOND_PREFERRED:
            s1, s2 = 0.0, 1.0
        else:
            s1, s2 = 0.5, 0.5

        # Update ratings
        self._ratings[comp.item1] = r1 + self._k * (s1 - e1)
        self._ratings[comp.item2] = r2 + self._k * (s2 - e2)

    def get_rating(self, item_id: str) -> float:
        """Get Elo rating for an item."""
        return self._ratings.get(item_id, self._initial)

    def predict(self, item1: str, item2: str) -> float:
        """Predict probability that item1 wins against item2."""
        r1 = self._ratings.get(item1, self._initial)
        r2 = self._ratings.get(item2, self._initial)

        return 1.0 / (1.0 + 10 ** ((r2 - r1) / 400.0))


# =============================================================================
# UTILITY FUNCTION ESTIMATOR
# =============================================================================

class UtilityEstimator:
    """Estimate utility function from preferences."""

    def __init__(self, items: ItemManager):
        self._items = items
        self._weights: Dict[str, float] = {}

    def learn_weights(
        self,
        comparisons: List[Comparison]
    ) -> PreferenceModel:
        """Learn feature weights from comparisons."""
        features = list(self._items.feature_names())
        n_features = len(features)

        if n_features == 0:
            return PreferenceModel()

        # Initialize weights
        for f in features:
            self._weights[f] = 1.0 / n_features

        # Gradient descent
        learning_rate = 0.1

        for _ in range(100):
            for comp in comparisons:
                item1 = self._items.get(comp.item1)
                item2 = self._items.get(comp.item2)

                if not item1 or not item2:
                    continue

                u1 = self._utility(item1)
                u2 = self._utility(item2)

                # Predicted probability
                p = 1.0 / (1.0 + math.exp(-(u1 - u2)))

                # Target
                if comp.result == ComparisonResult.FIRST_PREFERRED:
                    target = 1.0
                elif comp.result == ComparisonResult.SECOND_PREFERRED:
                    target = 0.0
                else:
                    target = 0.5

                # Gradient
                error = target - p

                for f in features:
                    f1 = item1.features.get(f, 0.0)
                    f2 = item2.features.get(f, 0.0)
                    self._weights[f] += learning_rate * error * (f1 - f2)

            # Normalize weights
            total = sum(abs(w) for w in self._weights.values())
            if total > 0:
                for f in self._weights:
                    self._weights[f] /= total

        return PreferenceModel(
            model_type=ModelType.WEIGHTED_SUM,
            weights=self._weights.copy()
        )

    def _utility(self, item: Item) -> float:
        """Compute utility of an item."""
        return sum(
            self._weights.get(f, 0.0) * v
            for f, v in item.features.items()
        )

    def get_utility(self, item: Item) -> float:
        """Get utility of an item."""
        return self._utility(item)

    def get_weights(self) -> Dict[str, float]:
        """Get learned weights."""
        return self._weights.copy()


# =============================================================================
# ACTIVE LEARNER
# =============================================================================

class ActiveLearner:
    """Active preference learning with query selection."""

    def __init__(
        self,
        items: ItemManager,
        bt_learner: BradleyTerryLearner
    ):
        self._items = items
        self._bt = bt_learner
        self._compared: Set[Tuple[str, str]] = set()

    def select_query(
        self,
        strategy: QueryStrategy = QueryStrategy.UNCERTAINTY
    ) -> Optional[Tuple[str, str]]:
        """Select next pair to compare."""
        all_items = self._items.all_items()

        if len(all_items) < 2:
            return None

        if strategy == QueryStrategy.RANDOM:
            return self._random_query(all_items)
        elif strategy == QueryStrategy.UNCERTAINTY:
            return self._uncertainty_query(all_items)
        else:
            return self._random_query(all_items)

    def _random_query(self, items: List[Item]) -> Optional[Tuple[str, str]]:
        """Random query selection."""
        candidates = [
            (i.item_id, j.item_id)
            for i in items for j in items
            if i.item_id < j.item_id and (i.item_id, j.item_id) not in self._compared
        ]

        if not candidates:
            return None

        pair = random.choice(candidates)
        self._compared.add(pair)
        return pair

    def _uncertainty_query(self, items: List[Item]) -> Optional[Tuple[str, str]]:
        """Select pair with highest uncertainty (closest to 0.5)."""
        best_pair = None
        best_uncertainty = 0.0

        for i in items:
            for j in items:
                if i.item_id >= j.item_id:
                    continue

                if (i.item_id, j.item_id) in self._compared:
                    continue

                prob = self._bt.predict(i.item_id, j.item_id)
                uncertainty = 1.0 - abs(prob - 0.5) * 2

                if uncertainty > best_uncertainty:
                    best_uncertainty = uncertainty
                    best_pair = (i.item_id, j.item_id)

        if best_pair:
            self._compared.add(best_pair)

        return best_pair

    def mark_compared(self, item1: str, item2: str) -> None:
        """Mark a pair as compared."""
        if item1 < item2:
            self._compared.add((item1, item2))
        else:
            self._compared.add((item2, item1))


# =============================================================================
# DRIFT DETECTOR
# =============================================================================

class DriftDetector:
    """Detect preference drift over time."""

    def __init__(self, window_size: int = 50):
        self._window_size = window_size
        self._history: List[Tuple[datetime, Dict[str, float]]] = []

    def add_snapshot(
        self,
        strengths: Dict[str, float],
        timestamp: Optional[datetime] = None
    ) -> None:
        """Add a preference snapshot."""
        ts = timestamp or datetime.now()
        self._history.append((ts, strengths.copy()))

    def detect_drift(self) -> DriftDetection:
        """Detect preference drift."""
        if len(self._history) < 2:
            return DriftDetection(drift_type=DriftType.NO_DRIFT)

        # Compare recent to old
        recent = self._history[-1][1]

        # Average of first half
        old_items = self._history[:len(self._history) // 2]
        if not old_items:
            return DriftDetection(drift_type=DriftType.NO_DRIFT)

        old_avg: Dict[str, float] = defaultdict(float)
        for _, strengths in old_items:
            for k, v in strengths.items():
                old_avg[k] += v / len(old_items)

        # Compute drift magnitude
        common_keys = set(recent.keys()) & set(old_avg.keys())
        if not common_keys:
            return DriftDetection(drift_type=DriftType.NO_DRIFT)

        total_change = sum(
            abs(recent[k] - old_avg[k]) for k in common_keys
        )
        avg_change = total_change / len(common_keys)

        # Classify drift
        if avg_change < 0.05:
            drift_type = DriftType.NO_DRIFT
        elif avg_change < 0.2:
            drift_type = DriftType.GRADUAL
        else:
            drift_type = DriftType.SUDDEN

        return DriftDetection(
            drift_type=drift_type,
            drift_magnitude=avg_change,
            change_point=self._history[len(self._history) // 2][0]
        )


# =============================================================================
# PREFERENCE LEARNER
# =============================================================================

class PreferenceLearner:
    """
    Preference Learner for BAEL.

    Advanced preference learning from data and feedback.
    """

    def __init__(self):
        self._items = ItemManager()
        self._comparisons = ComparisonCollector()
        self._bt = BradleyTerryLearner()
        self._elo = EloLearner()
        self._utility = UtilityEstimator(self._items)
        self._active = ActiveLearner(self._items, self._bt)
        self._drift = DriftDetector()

    # -------------------------------------------------------------------------
    # ITEMS
    # -------------------------------------------------------------------------

    def add_item(
        self,
        name: str,
        features: Dict[str, float]
    ) -> Item:
        """Add an item."""
        return self._items.add(name, features)

    def get_item(self, item_id: str) -> Optional[Item]:
        """Get an item."""
        return self._items.get(item_id)

    def all_items(self) -> List[Item]:
        """Get all items."""
        return self._items.all_items()

    # -------------------------------------------------------------------------
    # COMPARISONS
    # -------------------------------------------------------------------------

    def add_comparison(
        self,
        item1: str,
        item2: str,
        result: ComparisonResult,
        confidence: float = 1.0
    ) -> Comparison:
        """Add a pairwise comparison."""
        comp = self._comparisons.add(item1, item2, result, confidence)
        self._active.mark_compared(item1, item2)
        return comp

    def all_comparisons(self) -> List[Comparison]:
        """Get all comparisons."""
        return self._comparisons.all_comparisons()

    def win_loss(self, item_id: str) -> Tuple[int, int, int]:
        """Get win/loss/tie record."""
        return self._comparisons.win_loss_record(item_id)

    # -------------------------------------------------------------------------
    # LEARNING
    # -------------------------------------------------------------------------

    def learn_bradley_terry(
        self,
        max_iterations: int = 100
    ) -> LearningResult:
        """Learn using Bradley-Terry model."""
        result = self._bt.learn(
            self._comparisons.all_comparisons(),
            self._items.all_items(),
            max_iterations
        )

        # Snapshot for drift detection
        self._drift.add_snapshot(self._bt._strengths)

        return result

    def learn_elo(self) -> LearningResult:
        """Learn using Elo rating system."""
        return self._elo.learn(
            self._comparisons.all_comparisons(),
            self._items.all_items()
        )

    def learn_utility(self) -> PreferenceModel:
        """Learn utility function from comparisons."""
        return self._utility.learn_weights(
            self._comparisons.all_comparisons()
        )

    # -------------------------------------------------------------------------
    # PREDICTIONS
    # -------------------------------------------------------------------------

    def predict_bt(self, item1: str, item2: str) -> float:
        """Predict preference using Bradley-Terry."""
        return self._bt.predict(item1, item2)

    def predict_elo(self, item1: str, item2: str) -> float:
        """Predict preference using Elo."""
        return self._elo.predict(item1, item2)

    def get_strength(self, item_id: str) -> float:
        """Get Bradley-Terry strength."""
        return self._bt.get_strength(item_id)

    def get_rating(self, item_id: str) -> float:
        """Get Elo rating."""
        return self._elo.get_rating(item_id)

    def get_utility(self, item: Item) -> float:
        """Get utility of an item."""
        return self._utility.get_utility(item)

    def get_weights(self) -> Dict[str, float]:
        """Get learned feature weights."""
        return self._utility.get_weights()

    # -------------------------------------------------------------------------
    # ACTIVE LEARNING
    # -------------------------------------------------------------------------

    def suggest_comparison(
        self,
        strategy: QueryStrategy = QueryStrategy.UNCERTAINTY
    ) -> Optional[Tuple[str, str]]:
        """Suggest next comparison to make."""
        return self._active.select_query(strategy)

    # -------------------------------------------------------------------------
    # DRIFT DETECTION
    # -------------------------------------------------------------------------

    def detect_drift(self) -> DriftDetection:
        """Detect preference drift."""
        return self._drift.detect_drift()

    # -------------------------------------------------------------------------
    # RANKING
    # -------------------------------------------------------------------------

    def rank_items_bt(self) -> List[Tuple[Item, float]]:
        """Rank items by Bradley-Terry strength."""
        items = self._items.all_items()
        ranked = [(item, self._bt.get_strength(item.item_id)) for item in items]
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked

    def rank_items_elo(self) -> List[Tuple[Item, float]]:
        """Rank items by Elo rating."""
        items = self._items.all_items()
        ranked = [(item, self._elo.get_rating(item.item_id)) for item in items]
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Preference Learner."""
    print("=" * 70)
    print("BAEL - PREFERENCE LEARNER DEMO")
    print("Advanced Preference Learning from Data")
    print("=" * 70)
    print()

    learner = PreferenceLearner()

    # 1. Add Items
    print("1. ADD ITEMS:")
    print("-" * 40)

    a = learner.add_item("Item A", {"quality": 0.9, "price": 0.3})
    b = learner.add_item("Item B", {"quality": 0.7, "price": 0.5})
    c = learner.add_item("Item C", {"quality": 0.5, "price": 0.8})
    d = learner.add_item("Item D", {"quality": 0.8, "price": 0.4})

    for item in learner.all_items():
        print(f"   {item.name}: {item.features}")
    print()

    # 2. Add Comparisons
    print("2. ADD COMPARISONS:")
    print("-" * 40)

    learner.add_comparison(a.item_id, b.item_id, ComparisonResult.FIRST_PREFERRED)
    learner.add_comparison(a.item_id, c.item_id, ComparisonResult.FIRST_PREFERRED)
    learner.add_comparison(b.item_id, c.item_id, ComparisonResult.FIRST_PREFERRED)
    learner.add_comparison(d.item_id, b.item_id, ComparisonResult.FIRST_PREFERRED)
    learner.add_comparison(a.item_id, d.item_id, ComparisonResult.INDIFFERENT)
    learner.add_comparison(d.item_id, c.item_id, ComparisonResult.FIRST_PREFERRED)

    print(f"   Total comparisons: {len(learner.all_comparisons())}")
    print()

    # 3. Win/Loss Records
    print("3. WIN/LOSS RECORDS:")
    print("-" * 40)

    for item in learner.all_items():
        w, l, t = learner.win_loss(item.item_id)
        print(f"   {item.name}: {w}W-{l}L-{t}T")
    print()

    # 4. Learn Bradley-Terry
    print("4. BRADLEY-TERRY LEARNING:")
    print("-" * 40)

    result_bt = learner.learn_bradley_terry()
    print(f"   Iterations: {result_bt.num_iterations}")
    print(f"   Convergence: {result_bt.convergence:.6f}")
    print()

    # 5. Bradley-Terry Strengths
    print("5. BRADLEY-TERRY STRENGTHS:")
    print("-" * 40)

    for item in learner.all_items():
        strength = learner.get_strength(item.item_id)
        print(f"   {item.name}: {strength:.4f}")
    print()

    # 6. Learn Elo
    print("6. ELO RATINGS:")
    print("-" * 40)

    learner.learn_elo()

    for item in learner.all_items():
        rating = learner.get_rating(item.item_id)
        print(f"   {item.name}: {rating:.1f}")
    print()

    # 7. Predictions
    print("7. PREDICTIONS (P(A > B)):")
    print("-" * 40)

    p_bt = learner.predict_bt(a.item_id, c.item_id)
    p_elo = learner.predict_elo(a.item_id, c.item_id)

    print(f"   P(A > C) Bradley-Terry: {p_bt:.4f}")
    print(f"   P(A > C) Elo: {p_elo:.4f}")
    print()

    # 8. Learn Utility Function
    print("8. UTILITY FUNCTION LEARNING:")
    print("-" * 40)

    model = learner.learn_utility()
    weights = learner.get_weights()

    print(f"   Learned weights:")
    for feature, weight in weights.items():
        print(f"     {feature}: {weight:.4f}")
    print()

    # 9. Ranking
    print("9. ITEM RANKINGS:")
    print("-" * 40)

    print("   Bradley-Terry ranking:")
    for i, (item, strength) in enumerate(learner.rank_items_bt(), 1):
        print(f"     {i}. {item.name} ({strength:.4f})")

    print("\n   Elo ranking:")
    for i, (item, rating) in enumerate(learner.rank_items_elo(), 1):
        print(f"     {i}. {item.name} ({rating:.1f})")
    print()

    # 10. Active Learning
    print("10. ACTIVE LEARNING SUGGESTION:")
    print("-" * 40)

    suggestion = learner.suggest_comparison(QueryStrategy.UNCERTAINTY)
    if suggestion:
        i1 = learner.get_item(suggestion[0])
        i2 = learner.get_item(suggestion[1])
        if i1 and i2:
            print(f"   Suggested comparison: {i1.name} vs {i2.name}")
            print(f"   (Most uncertain pair)")
    else:
        print(f"   No more comparisons needed")
    print()

    # 11. Drift Detection
    print("11. PREFERENCE DRIFT DETECTION:")
    print("-" * 40)

    # Simulate preference changes
    learner.learn_bradley_terry()  # Add another snapshot

    drift = learner.detect_drift()
    print(f"   Drift type: {drift.drift_type.value}")
    print(f"   Magnitude: {drift.drift_magnitude:.4f}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Preference Learner Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
