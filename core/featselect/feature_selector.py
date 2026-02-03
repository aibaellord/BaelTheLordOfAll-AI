#!/usr/bin/env python3
"""
BAEL - Feature Selector
Advanced feature selection and importance analysis.

Features:
- Filter methods (correlation, variance)
- Wrapper methods (forward/backward)
- Embedded methods (regularization)
- Feature importance
- Mutual information
- Feature ranking
"""

import asyncio
import math
import random
import uuid
from abc import ABC, abstractmethod
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class SelectionMethod(Enum):
    """Feature selection methods."""
    FILTER = "filter"
    WRAPPER = "wrapper"
    EMBEDDED = "embedded"


class FilterType(Enum):
    """Filter method types."""
    VARIANCE = "variance"
    CORRELATION = "correlation"
    MUTUAL_INFO = "mutual_info"
    CHI_SQUARE = "chi_square"


class WrapperType(Enum):
    """Wrapper method types."""
    FORWARD = "forward"
    BACKWARD = "backward"
    BIDIRECTIONAL = "bidirectional"
    EXHAUSTIVE = "exhaustive"


class EmbeddedType(Enum):
    """Embedded method types."""
    L1 = "l1"
    L2 = "l2"
    TREE = "tree"


class FeatureStatus(Enum):
    """Feature status."""
    SELECTED = "selected"
    REJECTED = "rejected"
    PENDING = "pending"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Feature:
    """A feature."""
    feat_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    dtype: str = "numeric"
    importance: float = 0.0
    variance: float = 0.0
    correlation_target: float = 0.0
    status: FeatureStatus = FeatureStatus.PENDING


@dataclass
class Sample:
    """A data sample."""
    sample_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    features: Dict[str, float] = field(default_factory=dict)
    label: Optional[str] = None


@dataclass
class SelectionResult:
    """Feature selection result."""
    method: SelectionMethod = SelectionMethod.FILTER
    selected: List[str] = field(default_factory=list)
    rejected: List[str] = field(default_factory=list)
    scores: Dict[str, float] = field(default_factory=dict)


@dataclass
class ImportanceResult:
    """Feature importance result."""
    feature: str = ""
    importance: float = 0.0
    rank: int = 0
    method: str = ""


# =============================================================================
# FEATURE STORE
# =============================================================================

class FeatureStore:
    """Store for features and samples."""

    def __init__(self):
        self._features: Dict[str, Feature] = {}
        self._samples: List[Sample] = []

    def add_feature(self, name: str, dtype: str = "numeric") -> Feature:
        """Add a feature."""
        feat = Feature(name=name, dtype=dtype)
        self._features[name] = feat
        return feat

    def get_feature(self, name: str) -> Optional[Feature]:
        """Get a feature."""
        return self._features.get(name)

    def all_features(self) -> List[Feature]:
        """Get all features."""
        return list(self._features.values())

    def add_sample(
        self,
        features: Dict[str, float],
        label: Optional[str] = None
    ) -> Sample:
        """Add a sample."""
        sample = Sample(features=features, label=label)
        self._samples.append(sample)
        return sample

    def all_samples(self) -> List[Sample]:
        """Get all samples."""
        return self._samples

    def get_column(self, feature_name: str) -> List[float]:
        """Get all values for a feature."""
        return [s.features.get(feature_name, 0.0) for s in self._samples]

    def get_labels(self) -> List[str]:
        """Get all labels."""
        return [s.label for s in self._samples if s.label]


# =============================================================================
# VARIANCE FILTER
# =============================================================================

class VarianceFilter:
    """Filter features by variance."""

    def calculate_variance(self, values: List[float]) -> float:
        """Calculate variance of values."""
        if len(values) < 2:
            return 0.0

        mean = sum(values) / len(values)
        sq_diff = sum((v - mean) ** 2 for v in values)
        return sq_diff / len(values)

    def filter(
        self,
        store: FeatureStore,
        threshold: float = 0.0
    ) -> SelectionResult:
        """Filter low variance features."""
        selected = []
        rejected = []
        scores = {}

        for feat in store.all_features():
            values = store.get_column(feat.name)
            var = self.calculate_variance(values)

            scores[feat.name] = var
            feat.variance = var

            if var > threshold:
                selected.append(feat.name)
                feat.status = FeatureStatus.SELECTED
            else:
                rejected.append(feat.name)
                feat.status = FeatureStatus.REJECTED

        return SelectionResult(
            method=SelectionMethod.FILTER,
            selected=selected,
            rejected=rejected,
            scores=scores
        )


# =============================================================================
# CORRELATION FILTER
# =============================================================================

class CorrelationFilter:
    """Filter features by correlation."""

    def pearson_correlation(
        self,
        x: List[float],
        y: List[float]
    ) -> float:
        """Calculate Pearson correlation."""
        n = min(len(x), len(y))
        if n < 2:
            return 0.0

        mean_x = sum(x[:n]) / n
        mean_y = sum(y[:n]) / n

        cov = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        std_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x[:n]))
        std_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y[:n]))

        if std_x == 0 or std_y == 0:
            return 0.0

        return cov / (std_x * std_y)

    def filter_by_target(
        self,
        store: FeatureStore,
        target_values: List[float],
        threshold: float = 0.1
    ) -> SelectionResult:
        """Filter by correlation with target."""
        selected = []
        rejected = []
        scores = {}

        for feat in store.all_features():
            values = store.get_column(feat.name)
            corr = abs(self.pearson_correlation(values, target_values))

            scores[feat.name] = corr
            feat.correlation_target = corr

            if corr >= threshold:
                selected.append(feat.name)
                feat.status = FeatureStatus.SELECTED
            else:
                rejected.append(feat.name)
                feat.status = FeatureStatus.REJECTED

        return SelectionResult(
            method=SelectionMethod.FILTER,
            selected=selected,
            rejected=rejected,
            scores=scores
        )

    def remove_correlated(
        self,
        store: FeatureStore,
        threshold: float = 0.9
    ) -> SelectionResult:
        """Remove highly correlated features."""
        features = store.all_features()
        selected = set(f.name for f in features)
        rejected = []
        scores = {}

        for i, f1 in enumerate(features):
            if f1.name not in selected:
                continue

            for f2 in features[i + 1:]:
                if f2.name not in selected:
                    continue

                v1 = store.get_column(f1.name)
                v2 = store.get_column(f2.name)
                corr = abs(self.pearson_correlation(v1, v2))

                scores[(f1.name, f2.name)] = corr

                if corr >= threshold:
                    # Remove the one with lower target correlation
                    if f1.correlation_target < f2.correlation_target:
                        selected.discard(f1.name)
                        rejected.append(f1.name)
                    else:
                        selected.discard(f2.name)
                        rejected.append(f2.name)

        return SelectionResult(
            method=SelectionMethod.FILTER,
            selected=list(selected),
            rejected=rejected,
            scores={str(k): v for k, v in scores.items()}
        )


# =============================================================================
# MUTUAL INFORMATION
# =============================================================================

class MutualInformation:
    """Mutual information-based selection."""

    def discretize(
        self,
        values: List[float],
        bins: int = 10
    ) -> List[int]:
        """Discretize continuous values."""
        if not values:
            return []

        min_v = min(values)
        max_v = max(values)

        if max_v == min_v:
            return [0] * len(values)

        bin_width = (max_v - min_v) / bins

        return [min(int((v - min_v) / bin_width), bins - 1) for v in values]

    def entropy(self, values: List[int]) -> float:
        """Calculate entropy."""
        if not values:
            return 0.0

        counts = Counter(values)
        n = len(values)

        return -sum(
            (c / n) * math.log2(c / n)
            for c in counts.values()
            if c > 0
        )

    def mutual_info(
        self,
        x: List[float],
        y: List[float],
        bins: int = 10
    ) -> float:
        """Calculate mutual information."""
        x_disc = self.discretize(x, bins)
        y_disc = self.discretize(y, bins)

        h_x = self.entropy(x_disc)
        h_y = self.entropy(y_disc)

        # Joint entropy
        joint = list(zip(x_disc, y_disc))
        h_xy = self.entropy([hash(p) for p in joint])

        return h_x + h_y - h_xy

    def rank_features(
        self,
        store: FeatureStore,
        target_values: List[float]
    ) -> List[ImportanceResult]:
        """Rank features by mutual information."""
        results = []

        for feat in store.all_features():
            values = store.get_column(feat.name)
            mi = self.mutual_info(values, target_values)

            results.append(ImportanceResult(
                feature=feat.name,
                importance=mi,
                method="mutual_information"
            ))

        # Sort and assign ranks
        results.sort(key=lambda r: r.importance, reverse=True)
        for i, r in enumerate(results):
            r.rank = i + 1

        return results


# =============================================================================
# FORWARD SELECTION
# =============================================================================

class ForwardSelection:
    """Forward feature selection."""

    def __init__(self):
        self._evaluator: Optional[Callable[[List[str]], float]] = None

    def set_evaluator(self, evaluator: Callable[[List[str]], float]) -> None:
        """Set the evaluation function."""
        self._evaluator = evaluator

    def select(
        self,
        features: List[str],
        k: int = 5
    ) -> SelectionResult:
        """Select k best features."""
        if not self._evaluator:
            # Default: random scores
            self._evaluator = lambda fs: random.random()

        selected = []
        remaining = list(features)
        scores = {}

        for _ in range(min(k, len(features))):
            best_feat = None
            best_score = float('-inf')

            for feat in remaining:
                candidate = selected + [feat]
                score = self._evaluator(candidate)

                if score > best_score:
                    best_score = score
                    best_feat = feat

            if best_feat:
                selected.append(best_feat)
                remaining.remove(best_feat)
                scores[best_feat] = best_score

        return SelectionResult(
            method=SelectionMethod.WRAPPER,
            selected=selected,
            rejected=remaining,
            scores=scores
        )


# =============================================================================
# BACKWARD ELIMINATION
# =============================================================================

class BackwardElimination:
    """Backward feature elimination."""

    def __init__(self):
        self._evaluator: Optional[Callable[[List[str]], float]] = None

    def set_evaluator(self, evaluator: Callable[[List[str]], float]) -> None:
        """Set the evaluation function."""
        self._evaluator = evaluator

    def select(
        self,
        features: List[str],
        k: int = 5
    ) -> SelectionResult:
        """Select k best features."""
        if not self._evaluator:
            self._evaluator = lambda fs: random.random()

        selected = list(features)
        rejected = []
        scores = {}

        while len(selected) > k:
            worst_feat = None
            best_score = float('-inf')

            for feat in selected:
                candidate = [f for f in selected if f != feat]
                score = self._evaluator(candidate)

                if score > best_score:
                    best_score = score
                    worst_feat = feat

            if worst_feat:
                selected.remove(worst_feat)
                rejected.append(worst_feat)
                scores[worst_feat] = best_score

        return SelectionResult(
            method=SelectionMethod.WRAPPER,
            selected=selected,
            rejected=rejected,
            scores=scores
        )


# =============================================================================
# IMPORTANCE CALCULATOR
# =============================================================================

class ImportanceCalculator:
    """Calculate feature importance."""

    def permutation_importance(
        self,
        store: FeatureStore,
        evaluator: Callable[[List[Sample]], float],
        n_repeats: int = 5
    ) -> List[ImportanceResult]:
        """Calculate permutation importance."""
        results = []
        samples = store.all_samples()

        if not samples:
            return results

        # Baseline score
        baseline = evaluator(samples)

        for feat in store.all_features():
            importance_scores = []

            for _ in range(n_repeats):
                # Permute feature
                permuted = []
                values = [s.features.get(feat.name, 0.0) for s in samples]
                random.shuffle(values)

                for i, sample in enumerate(samples):
                    new_features = dict(sample.features)
                    new_features[feat.name] = values[i]
                    permuted.append(Sample(
                        features=new_features,
                        label=sample.label
                    ))

                # Calculate score drop
                score = evaluator(permuted)
                importance_scores.append(baseline - score)

            avg_importance = sum(importance_scores) / len(importance_scores)

            results.append(ImportanceResult(
                feature=feat.name,
                importance=avg_importance,
                method="permutation"
            ))

            feat.importance = avg_importance

        # Sort and rank
        results.sort(key=lambda r: r.importance, reverse=True)
        for i, r in enumerate(results):
            r.rank = i + 1

        return results


# =============================================================================
# FEATURE SELECTOR
# =============================================================================

class FeatureSelector:
    """
    Feature Selector for BAEL.

    Advanced feature selection and importance analysis.
    """

    def __init__(self):
        self._store = FeatureStore()
        self._variance = VarianceFilter()
        self._correlation = CorrelationFilter()
        self._mutual_info = MutualInformation()
        self._forward = ForwardSelection()
        self._backward = BackwardElimination()
        self._importance = ImportanceCalculator()

    # -------------------------------------------------------------------------
    # FEATURES AND SAMPLES
    # -------------------------------------------------------------------------

    def add_feature(self, name: str, dtype: str = "numeric") -> Feature:
        """Add a feature."""
        return self._store.add_feature(name, dtype)

    def add_sample(
        self,
        features: Dict[str, float],
        label: Optional[str] = None
    ) -> Sample:
        """Add a sample."""
        return self._store.add_sample(features, label)

    def all_features(self) -> List[Feature]:
        """Get all features."""
        return self._store.all_features()

    def all_samples(self) -> List[Sample]:
        """Get all samples."""
        return self._store.all_samples()

    # -------------------------------------------------------------------------
    # FILTER METHODS
    # -------------------------------------------------------------------------

    def filter_by_variance(self, threshold: float = 0.0) -> SelectionResult:
        """Filter by variance threshold."""
        return self._variance.filter(self._store, threshold)

    def filter_by_correlation(
        self,
        target_values: List[float],
        threshold: float = 0.1
    ) -> SelectionResult:
        """Filter by correlation with target."""
        return self._correlation.filter_by_target(
            self._store, target_values, threshold
        )

    def remove_correlated_features(
        self,
        threshold: float = 0.9
    ) -> SelectionResult:
        """Remove highly correlated features."""
        return self._correlation.remove_correlated(self._store, threshold)

    def rank_by_mutual_info(
        self,
        target_values: List[float]
    ) -> List[ImportanceResult]:
        """Rank features by mutual information."""
        return self._mutual_info.rank_features(self._store, target_values)

    # -------------------------------------------------------------------------
    # WRAPPER METHODS
    # -------------------------------------------------------------------------

    def forward_selection(
        self,
        evaluator: Callable[[List[str]], float],
        k: int = 5
    ) -> SelectionResult:
        """Forward feature selection."""
        self._forward.set_evaluator(evaluator)
        feature_names = [f.name for f in self._store.all_features()]
        return self._forward.select(feature_names, k)

    def backward_elimination(
        self,
        evaluator: Callable[[List[str]], float],
        k: int = 5
    ) -> SelectionResult:
        """Backward feature elimination."""
        self._backward.set_evaluator(evaluator)
        feature_names = [f.name for f in self._store.all_features()]
        return self._backward.select(feature_names, k)

    # -------------------------------------------------------------------------
    # IMPORTANCE
    # -------------------------------------------------------------------------

    def permutation_importance(
        self,
        evaluator: Callable[[List[Sample]], float],
        n_repeats: int = 5
    ) -> List[ImportanceResult]:
        """Calculate permutation importance."""
        return self._importance.permutation_importance(
            self._store, evaluator, n_repeats
        )

    def top_features(self, k: int = 5) -> List[Feature]:
        """Get top k features by importance."""
        sorted_feats = sorted(
            self._store.all_features(),
            key=lambda f: f.importance,
            reverse=True
        )
        return sorted_feats[:k]

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def select_top(self, k: int = 5) -> List[str]:
        """Select top k features."""
        top = self.top_features(k)
        return [f.name for f in top]

    def get_stats(self) -> Dict[str, Any]:
        """Get feature statistics."""
        feats = self._store.all_features()

        return {
            "total_features": len(feats),
            "selected": sum(1 for f in feats if f.status == FeatureStatus.SELECTED),
            "rejected": sum(1 for f in feats if f.status == FeatureStatus.REJECTED),
            "pending": sum(1 for f in feats if f.status == FeatureStatus.PENDING),
            "avg_importance": sum(f.importance for f in feats) / len(feats) if feats else 0
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Feature Selector."""
    print("=" * 70)
    print("BAEL - FEATURE SELECTOR DEMO")
    print("Advanced Feature Selection and Importance Analysis")
    print("=" * 70)
    print()

    selector = FeatureSelector()

    # 1. Add Features
    print("1. ADD FEATURES:")
    print("-" * 40)

    features = ["age", "income", "education", "experience", "credit_score",
                "debt_ratio", "employment_years", "num_accounts"]

    for name in features:
        selector.add_feature(name)
        print(f"   Added: {name}")
    print()

    # 2. Add Samples
    print("2. ADD SAMPLES:")
    print("-" * 40)

    for _ in range(100):
        sample_features = {
            "age": random.uniform(18, 70),
            "income": random.uniform(20000, 150000),
            "education": random.uniform(0, 20),
            "experience": random.uniform(0, 50),
            "credit_score": random.uniform(300, 850),
            "debt_ratio": random.uniform(0, 1),
            "employment_years": random.uniform(0, 40),
            "num_accounts": random.uniform(1, 10)
        }
        label = "approved" if random.random() > 0.5 else "denied"
        selector.add_sample(sample_features, label)

    print(f"   Added {len(selector.all_samples())} samples")
    print()

    # 3. Variance Filter
    print("3. VARIANCE FILTER:")
    print("-" * 40)

    result = selector.filter_by_variance(threshold=0.0)
    print(f"   Selected: {len(result.selected)} features")
    for name, score in sorted(result.scores.items(), key=lambda x: -x[1])[:5]:
        print(f"      {name}: variance={score:.2f}")
    print()

    # 4. Correlation Filter
    print("4. CORRELATION FILTER:")
    print("-" * 40)

    # Create target values (1 for approved, 0 for denied)
    target = [1.0 if s.label == "approved" else 0.0 for s in selector.all_samples()]

    result = selector.filter_by_correlation(target, threshold=0.0)
    print(f"   Correlation with target:")
    for name, score in sorted(result.scores.items(), key=lambda x: -x[1])[:5]:
        print(f"      {name}: correlation={score:.3f}")
    print()

    # 5. Mutual Information
    print("5. MUTUAL INFORMATION:")
    print("-" * 40)

    mi_results = selector.rank_by_mutual_info(target)
    print(f"   Feature ranking by mutual information:")
    for r in mi_results[:5]:
        print(f"      #{r.rank} {r.feature}: MI={r.importance:.4f}")
    print()

    # 6. Forward Selection
    print("6. FORWARD SELECTION:")
    print("-" * 40)

    def evaluator(feats):
        # Simulate model evaluation
        return random.random() * len(feats) / 8

    result = selector.forward_selection(evaluator, k=3)
    print(f"   Selected: {result.selected}")
    for name, score in result.scores.items():
        print(f"      {name}: score={score:.3f}")
    print()

    # 7. Backward Elimination
    print("7. BACKWARD ELIMINATION:")
    print("-" * 40)

    result = selector.backward_elimination(evaluator, k=3)
    print(f"   Selected: {result.selected}")
    print(f"   Eliminated: {result.rejected}")
    print()

    # 8. Permutation Importance
    print("8. PERMUTATION IMPORTANCE:")
    print("-" * 40)

    def sample_evaluator(samples):
        # Simulate model accuracy
        return random.random()

    importance = selector.permutation_importance(sample_evaluator, n_repeats=3)
    print(f"   Feature importance (permutation):")
    for r in importance[:5]:
        print(f"      #{r.rank} {r.feature}: importance={r.importance:.4f}")
    print()

    # 9. Top Features
    print("9. TOP FEATURES:")
    print("-" * 40)

    top = selector.top_features(5)
    for i, feat in enumerate(top, 1):
        print(f"   #{i} {feat.name}: importance={feat.importance:.4f}")
    print()

    # 10. Statistics
    print("10. STATISTICS:")
    print("-" * 40)

    stats = selector.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Feature Selector Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
