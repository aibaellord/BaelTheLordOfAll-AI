#!/usr/bin/env python3
"""
BAEL - Case-Based Reasoner
Advanced case-based reasoning and retrieval.

Features:
- Case representation
- Similarity-based retrieval
- Case adaptation
- Case retention
- Solution transfer
- Learning from experience
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

class SimilarityMetric(Enum):
    """Similarity metrics for case comparison."""
    EUCLIDEAN = "euclidean"
    COSINE = "cosine"
    JACCARD = "jaccard"
    WEIGHTED = "weighted"
    MANHATTAN = "manhattan"


class AdaptationType(Enum):
    """Types of case adaptation."""
    NULL = "null"  # No adaptation
    SUBSTITUTION = "substitution"  # Substitute values
    TRANSFORMATION = "transformation"  # Transform solution
    DERIVATIONAL = "derivational"  # Replay derivation
    COMPOSITIONAL = "compositional"  # Combine cases


class FeatureType(Enum):
    """Types of features."""
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    BOOLEAN = "boolean"
    SET = "set"
    TEXT = "text"


class RetentionPolicy(Enum):
    """Case retention policies."""
    ALWAYS = "always"
    FAILURE_DRIVEN = "failure_driven"
    NOVELTY_BASED = "novelty_based"
    COVERAGE_BASED = "coverage_based"


class CaseStatus(Enum):
    """Status of a case."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DEPRECATED = "deprecated"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Feature:
    """A feature in a case."""
    feature_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    feature_type: FeatureType = FeatureType.NUMERIC
    weight: float = 1.0
    is_discriminating: bool = True


@dataclass
class Case:
    """A case in the case base."""
    case_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    problem: Dict[str, Any] = field(default_factory=dict)  # Problem features
    solution: Dict[str, Any] = field(default_factory=dict)  # Solution features
    outcome: Optional[Dict[str, Any]] = None  # Actual outcome
    success: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    usage_count: int = 0
    status: CaseStatus = CaseStatus.ACTIVE
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalResult:
    """Result of case retrieval."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query: Dict[str, Any] = field(default_factory=dict)
    retrieved_cases: List[Tuple[str, float]] = field(default_factory=list)  # (case_id, similarity)
    retrieval_time: float = 0.0


@dataclass
class AdaptationResult:
    """Result of case adaptation."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_case_id: str = ""
    adapted_solution: Dict[str, Any] = field(default_factory=dict)
    adaptation_type: AdaptationType = AdaptationType.NULL
    confidence: float = 1.0
    changes: List[str] = field(default_factory=list)


@dataclass
class LearningResult:
    """Result of learning from a case."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    new_case_id: Optional[str] = None
    retained: bool = False
    reason: str = ""


# =============================================================================
# FEATURE MANAGER
# =============================================================================

class FeatureManager:
    """Manage case features."""

    def __init__(self):
        self._features: Dict[str, Feature] = {}

    def define_feature(
        self,
        name: str,
        feature_type: FeatureType = FeatureType.NUMERIC,
        weight: float = 1.0,
        is_discriminating: bool = True
    ) -> Feature:
        """Define a feature."""
        feature = Feature(
            name=name,
            feature_type=feature_type,
            weight=weight,
            is_discriminating=is_discriminating
        )
        self._features[name] = feature
        return feature

    def get_feature(self, name: str) -> Optional[Feature]:
        """Get a feature by name."""
        return self._features.get(name)

    def all_features(self) -> List[Feature]:
        """Get all features."""
        return list(self._features.values())

    def discriminating_features(self) -> List[Feature]:
        """Get discriminating features only."""
        return [f for f in self._features.values() if f.is_discriminating]

    def set_weight(self, name: str, weight: float) -> bool:
        """Set feature weight."""
        if name in self._features:
            self._features[name].weight = weight
            return True
        return False


# =============================================================================
# CASE BASE
# =============================================================================

class CaseBase:
    """Store and manage cases."""

    def __init__(self):
        self._cases: Dict[str, Case] = {}
        self._index: Dict[str, Set[str]] = defaultdict(set)  # feature_value -> case_ids

    def add_case(
        self,
        name: str,
        problem: Dict[str, Any],
        solution: Dict[str, Any],
        outcome: Optional[Dict[str, Any]] = None,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Case:
        """Add a case to the case base."""
        case = Case(
            name=name,
            problem=problem,
            solution=solution,
            outcome=outcome,
            success=success,
            metadata=metadata or {}
        )

        self._cases[case.case_id] = case
        self._index_case(case)

        return case

    def _index_case(self, case: Case) -> None:
        """Index a case by its features."""
        for key, value in case.problem.items():
            index_key = f"{key}:{value}"
            self._index[index_key].add(case.case_id)

    def get_case(self, case_id: str) -> Optional[Case]:
        """Get a case by ID."""
        return self._cases.get(case_id)

    def remove_case(self, case_id: str) -> bool:
        """Remove a case."""
        if case_id in self._cases:
            case = self._cases[case_id]

            # Remove from index
            for key, value in case.problem.items():
                index_key = f"{key}:{value}"
                self._index[index_key].discard(case_id)

            del self._cases[case_id]
            return True
        return False

    def all_cases(self) -> List[Case]:
        """Get all active cases."""
        return [c for c in self._cases.values() if c.status == CaseStatus.ACTIVE]

    def case_count(self) -> int:
        """Get number of cases."""
        return len(self._cases)

    def increment_usage(self, case_id: str) -> None:
        """Increment usage count for a case."""
        if case_id in self._cases:
            self._cases[case_id].usage_count += 1


# =============================================================================
# SIMILARITY CALCULATOR
# =============================================================================

class SimilarityCalculator:
    """Calculate similarity between cases."""

    def __init__(self, feature_manager: FeatureManager):
        self._features = feature_manager

    def calculate(
        self,
        case1: Dict[str, Any],
        case2: Dict[str, Any],
        metric: SimilarityMetric = SimilarityMetric.WEIGHTED
    ) -> float:
        """Calculate similarity between two problem descriptions."""
        if metric == SimilarityMetric.EUCLIDEAN:
            return self._euclidean_similarity(case1, case2)
        elif metric == SimilarityMetric.COSINE:
            return self._cosine_similarity(case1, case2)
        elif metric == SimilarityMetric.JACCARD:
            return self._jaccard_similarity(case1, case2)
        elif metric == SimilarityMetric.MANHATTAN:
            return self._manhattan_similarity(case1, case2)
        else:
            return self._weighted_similarity(case1, case2)

    def _weighted_similarity(
        self,
        case1: Dict[str, Any],
        case2: Dict[str, Any]
    ) -> float:
        """Weighted feature similarity."""
        total_weight = 0.0
        weighted_sim = 0.0

        all_keys = set(case1.keys()) | set(case2.keys())

        for key in all_keys:
            feature = self._features.get_feature(key)
            if not feature or not feature.is_discriminating:
                continue

            weight = feature.weight
            total_weight += weight

            if key not in case1 or key not in case2:
                continue

            v1, v2 = case1[key], case2[key]
            sim = self._feature_similarity(v1, v2, feature.feature_type)
            weighted_sim += weight * sim

        return weighted_sim / total_weight if total_weight > 0 else 0.0

    def _feature_similarity(
        self,
        v1: Any,
        v2: Any,
        feature_type: FeatureType
    ) -> float:
        """Calculate similarity for a single feature."""
        if v1 == v2:
            return 1.0

        if feature_type == FeatureType.NUMERIC:
            try:
                diff = abs(float(v1) - float(v2))
                max_val = max(abs(float(v1)), abs(float(v2)), 1.0)
                return 1.0 - min(diff / max_val, 1.0)
            except (ValueError, TypeError):
                return 0.0

        elif feature_type == FeatureType.CATEGORICAL:
            return 1.0 if v1 == v2 else 0.0

        elif feature_type == FeatureType.BOOLEAN:
            return 1.0 if bool(v1) == bool(v2) else 0.0

        elif feature_type == FeatureType.SET:
            try:
                s1 = set(v1) if isinstance(v1, (list, set)) else {v1}
                s2 = set(v2) if isinstance(v2, (list, set)) else {v2}
                intersection = len(s1 & s2)
                union = len(s1 | s2)
                return intersection / union if union > 0 else 0.0
            except TypeError:
                return 0.0

        elif feature_type == FeatureType.TEXT:
            # Simple word overlap
            w1 = set(str(v1).lower().split())
            w2 = set(str(v2).lower().split())
            intersection = len(w1 & w2)
            union = len(w1 | w2)
            return intersection / union if union > 0 else 0.0

        return 0.0

    def _euclidean_similarity(
        self,
        case1: Dict[str, Any],
        case2: Dict[str, Any]
    ) -> float:
        """Euclidean distance-based similarity."""
        common_keys = set(case1.keys()) & set(case2.keys())

        if not common_keys:
            return 0.0

        sum_sq = 0.0
        for key in common_keys:
            try:
                diff = float(case1[key]) - float(case2[key])
                sum_sq += diff ** 2
            except (ValueError, TypeError):
                if case1[key] != case2[key]:
                    sum_sq += 1.0

        distance = math.sqrt(sum_sq)
        return 1.0 / (1.0 + distance)

    def _cosine_similarity(
        self,
        case1: Dict[str, Any],
        case2: Dict[str, Any]
    ) -> float:
        """Cosine similarity."""
        common_keys = set(case1.keys()) & set(case2.keys())

        if not common_keys:
            return 0.0

        dot_product = 0.0
        norm1 = 0.0
        norm2 = 0.0

        for key in common_keys:
            try:
                v1 = float(case1[key])
                v2 = float(case2[key])
                dot_product += v1 * v2
                norm1 += v1 ** 2
                norm2 += v2 ** 2
            except (ValueError, TypeError):
                pass

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (math.sqrt(norm1) * math.sqrt(norm2))

    def _jaccard_similarity(
        self,
        case1: Dict[str, Any],
        case2: Dict[str, Any]
    ) -> float:
        """Jaccard similarity for categorical features."""
        matches = 0
        total = 0

        all_keys = set(case1.keys()) | set(case2.keys())

        for key in all_keys:
            total += 1
            if key in case1 and key in case2 and case1[key] == case2[key]:
                matches += 1

        return matches / total if total > 0 else 0.0

    def _manhattan_similarity(
        self,
        case1: Dict[str, Any],
        case2: Dict[str, Any]
    ) -> float:
        """Manhattan distance-based similarity."""
        common_keys = set(case1.keys()) & set(case2.keys())

        if not common_keys:
            return 0.0

        total_diff = 0.0
        for key in common_keys:
            try:
                diff = abs(float(case1[key]) - float(case2[key]))
                total_diff += diff
            except (ValueError, TypeError):
                if case1[key] != case2[key]:
                    total_diff += 1.0

        return 1.0 / (1.0 + total_diff)


# =============================================================================
# CASE RETRIEVER
# =============================================================================

class CaseRetriever:
    """Retrieve similar cases."""

    def __init__(
        self,
        case_base: CaseBase,
        similarity_calculator: SimilarityCalculator
    ):
        self._case_base = case_base
        self._similarity = similarity_calculator

    def retrieve(
        self,
        query: Dict[str, Any],
        k: int = 5,
        metric: SimilarityMetric = SimilarityMetric.WEIGHTED,
        threshold: float = 0.0
    ) -> RetrievalResult:
        """Retrieve k most similar cases."""
        import time
        start = time.time()

        similarities = []

        for case in self._case_base.all_cases():
            sim = self._similarity.calculate(query, case.problem, metric)
            if sim >= threshold:
                similarities.append((case.case_id, sim))

        # Sort by similarity descending
        similarities.sort(key=lambda x: -x[1])

        # Take top k
        top_k = similarities[:k]

        return RetrievalResult(
            query=query,
            retrieved_cases=top_k,
            retrieval_time=time.time() - start
        )

    def retrieve_by_index(
        self,
        query: Dict[str, Any],
        k: int = 5
    ) -> List[str]:
        """Fast retrieval using index."""
        # Find cases with matching feature values
        candidate_counts: Dict[str, int] = defaultdict(int)

        for key, value in query.items():
            index_key = f"{key}:{value}"
            for case_id in self._case_base._index.get(index_key, []):
                candidate_counts[case_id] += 1

        # Sort by number of matching features
        sorted_candidates = sorted(
            candidate_counts.items(),
            key=lambda x: -x[1]
        )

        return [c[0] for c in sorted_candidates[:k]]


# =============================================================================
# CASE ADAPTER
# =============================================================================

class CaseAdapter:
    """Adapt retrieved cases to new problems."""

    def __init__(self, feature_manager: FeatureManager):
        self._features = feature_manager
        self._adaptation_rules: Dict[str, Callable] = {}

    def register_adaptation_rule(
        self,
        feature_name: str,
        rule: Callable[[Any, Any, Dict], Any]
    ) -> None:
        """Register an adaptation rule for a feature."""
        self._adaptation_rules[feature_name] = rule

    def adapt(
        self,
        source_case: Case,
        query: Dict[str, Any],
        adaptation_type: AdaptationType = AdaptationType.SUBSTITUTION
    ) -> AdaptationResult:
        """Adapt a case's solution to a new problem."""
        if adaptation_type == AdaptationType.NULL:
            return AdaptationResult(
                source_case_id=source_case.case_id,
                adapted_solution=source_case.solution.copy(),
                adaptation_type=AdaptationType.NULL,
                confidence=1.0
            )

        elif adaptation_type == AdaptationType.SUBSTITUTION:
            return self._substitution_adapt(source_case, query)

        elif adaptation_type == AdaptationType.TRANSFORMATION:
            return self._transformation_adapt(source_case, query)

        return AdaptationResult(
            source_case_id=source_case.case_id,
            adapted_solution=source_case.solution.copy(),
            adaptation_type=AdaptationType.NULL
        )

    def _substitution_adapt(
        self,
        source: Case,
        query: Dict[str, Any]
    ) -> AdaptationResult:
        """Substitute solution values based on problem differences."""
        adapted = source.solution.copy()
        changes = []

        # Find differences in problem
        for key, new_value in query.items():
            old_value = source.problem.get(key)

            if old_value != new_value:
                # Apply adaptation rule if exists
                if key in self._adaptation_rules:
                    rule = self._adaptation_rules[key]

                    # Update corresponding solution features
                    for sol_key in list(adapted.keys()):
                        adapted[sol_key] = rule(old_value, new_value, adapted)
                        changes.append(f"{sol_key}: adapted based on {key}")

        # Calculate confidence based on changes
        confidence = 1.0 - (len(changes) * 0.1)
        confidence = max(0.3, confidence)

        return AdaptationResult(
            source_case_id=source.case_id,
            adapted_solution=adapted,
            adaptation_type=AdaptationType.SUBSTITUTION,
            confidence=confidence,
            changes=changes
        )

    def _transformation_adapt(
        self,
        source: Case,
        query: Dict[str, Any]
    ) -> AdaptationResult:
        """Transform solution using problem differences."""
        adapted = source.solution.copy()
        changes = []

        # Calculate proportional differences
        for key, new_value in query.items():
            old_value = source.problem.get(key)

            if old_value is None:
                continue

            feature = self._features.get_feature(key)
            if feature and feature.feature_type == FeatureType.NUMERIC:
                try:
                    old_f = float(old_value)
                    new_f = float(new_value)

                    if old_f != 0:
                        ratio = new_f / old_f

                        # Apply ratio to numeric solution features
                        for sol_key, sol_value in adapted.items():
                            sol_feature = self._features.get_feature(sol_key)
                            if sol_feature and sol_feature.feature_type == FeatureType.NUMERIC:
                                try:
                                    adapted[sol_key] = float(sol_value) * ratio
                                    changes.append(f"{sol_key}: scaled by {ratio:.2f}")
                                except (ValueError, TypeError):
                                    pass
                except (ValueError, TypeError):
                    pass

        confidence = 1.0 - (len(changes) * 0.15)
        confidence = max(0.2, confidence)

        return AdaptationResult(
            source_case_id=source.case_id,
            adapted_solution=adapted,
            adaptation_type=AdaptationType.TRANSFORMATION,
            confidence=confidence,
            changes=changes
        )


# =============================================================================
# CASE LEARNER
# =============================================================================

class CaseLearner:
    """Learn from new cases."""

    def __init__(
        self,
        case_base: CaseBase,
        similarity_calculator: SimilarityCalculator
    ):
        self._case_base = case_base
        self._similarity = similarity_calculator
        self._retention_policy = RetentionPolicy.NOVELTY_BASED
        self._novelty_threshold = 0.7

    def set_retention_policy(
        self,
        policy: RetentionPolicy,
        threshold: float = 0.7
    ) -> None:
        """Set retention policy."""
        self._retention_policy = policy
        self._novelty_threshold = threshold

    def learn(
        self,
        problem: Dict[str, Any],
        solution: Dict[str, Any],
        outcome: Optional[Dict[str, Any]] = None,
        success: bool = True,
        name: str = ""
    ) -> LearningResult:
        """Learn from a new case experience."""
        if self._retention_policy == RetentionPolicy.ALWAYS:
            return self._retain_always(problem, solution, outcome, success, name)

        elif self._retention_policy == RetentionPolicy.FAILURE_DRIVEN:
            return self._retain_on_failure(problem, solution, outcome, success, name)

        elif self._retention_policy == RetentionPolicy.NOVELTY_BASED:
            return self._retain_on_novelty(problem, solution, outcome, success, name)

        elif self._retention_policy == RetentionPolicy.COVERAGE_BASED:
            return self._retain_for_coverage(problem, solution, outcome, success, name)

        return LearningResult(retained=False, reason="Unknown policy")

    def _retain_always(
        self,
        problem: Dict[str, Any],
        solution: Dict[str, Any],
        outcome: Optional[Dict[str, Any]],
        success: bool,
        name: str
    ) -> LearningResult:
        """Always retain the case."""
        case = self._case_base.add_case(
            name=name or f"Case-{self._case_base.case_count() + 1}",
            problem=problem,
            solution=solution,
            outcome=outcome,
            success=success
        )

        return LearningResult(
            new_case_id=case.case_id,
            retained=True,
            reason="Always retain policy"
        )

    def _retain_on_failure(
        self,
        problem: Dict[str, Any],
        solution: Dict[str, Any],
        outcome: Optional[Dict[str, Any]],
        success: bool,
        name: str
    ) -> LearningResult:
        """Retain only failure cases."""
        if success:
            return LearningResult(
                retained=False,
                reason="Success case - not retained under failure-driven policy"
            )

        case = self._case_base.add_case(
            name=name or f"Failure-{self._case_base.case_count() + 1}",
            problem=problem,
            solution=solution,
            outcome=outcome,
            success=False
        )

        return LearningResult(
            new_case_id=case.case_id,
            retained=True,
            reason="Failure case retained"
        )

    def _retain_on_novelty(
        self,
        problem: Dict[str, Any],
        solution: Dict[str, Any],
        outcome: Optional[Dict[str, Any]],
        success: bool,
        name: str
    ) -> LearningResult:
        """Retain if case is novel (dissimilar to existing cases)."""
        # Check similarity to existing cases
        max_similarity = 0.0

        for case in self._case_base.all_cases():
            sim = self._similarity.calculate(problem, case.problem)
            max_similarity = max(max_similarity, sim)

        if max_similarity < self._novelty_threshold:
            case = self._case_base.add_case(
                name=name or f"Novel-{self._case_base.case_count() + 1}",
                problem=problem,
                solution=solution,
                outcome=outcome,
                success=success
            )

            return LearningResult(
                new_case_id=case.case_id,
                retained=True,
                reason=f"Novel case (max similarity: {max_similarity:.2f})"
            )

        return LearningResult(
            retained=False,
            reason=f"Too similar to existing case (similarity: {max_similarity:.2f})"
        )

    def _retain_for_coverage(
        self,
        problem: Dict[str, Any],
        solution: Dict[str, Any],
        outcome: Optional[Dict[str, Any]],
        success: bool,
        name: str
    ) -> LearningResult:
        """Retain if case improves coverage."""
        # Simple coverage: retain if any feature value is new
        existing_values: Set[str] = set()

        for case in self._case_base.all_cases():
            for key, value in case.problem.items():
                existing_values.add(f"{key}:{value}")

        new_values = []
        for key, value in problem.items():
            if f"{key}:{value}" not in existing_values:
                new_values.append(f"{key}:{value}")

        if new_values:
            case = self._case_base.add_case(
                name=name or f"Coverage-{self._case_base.case_count() + 1}",
                problem=problem,
                solution=solution,
                outcome=outcome,
                success=success
            )

            return LearningResult(
                new_case_id=case.case_id,
                retained=True,
                reason=f"Improves coverage with: {new_values[:3]}"
            )

        return LearningResult(
            retained=False,
            reason="Does not improve coverage"
        )


# =============================================================================
# CASE-BASED REASONER
# =============================================================================

class CaseBasedReasoner:
    """
    Case-Based Reasoner for BAEL.

    Advanced case-based reasoning and retrieval.
    """

    def __init__(self):
        self._features = FeatureManager()
        self._case_base = CaseBase()
        self._similarity = SimilarityCalculator(self._features)
        self._retriever = CaseRetriever(self._case_base, self._similarity)
        self._adapter = CaseAdapter(self._features)
        self._learner = CaseLearner(self._case_base, self._similarity)

    # -------------------------------------------------------------------------
    # FEATURE MANAGEMENT
    # -------------------------------------------------------------------------

    def define_feature(
        self,
        name: str,
        feature_type: FeatureType = FeatureType.NUMERIC,
        weight: float = 1.0,
        is_discriminating: bool = True
    ) -> Feature:
        """Define a feature."""
        return self._features.define_feature(
            name, feature_type, weight, is_discriminating
        )

    def set_feature_weight(self, name: str, weight: float) -> bool:
        """Set feature weight."""
        return self._features.set_weight(name, weight)

    def all_features(self) -> List[Feature]:
        """Get all defined features."""
        return self._features.all_features()

    # -------------------------------------------------------------------------
    # CASE MANAGEMENT
    # -------------------------------------------------------------------------

    def add_case(
        self,
        name: str,
        problem: Dict[str, Any],
        solution: Dict[str, Any],
        outcome: Optional[Dict[str, Any]] = None,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Case:
        """Add a case directly."""
        return self._case_base.add_case(
            name, problem, solution, outcome, success, metadata
        )

    def get_case(self, case_id: str) -> Optional[Case]:
        """Get a case by ID."""
        return self._case_base.get_case(case_id)

    def remove_case(self, case_id: str) -> bool:
        """Remove a case."""
        return self._case_base.remove_case(case_id)

    def case_count(self) -> int:
        """Get number of cases."""
        return self._case_base.case_count()

    def all_cases(self) -> List[Case]:
        """Get all active cases."""
        return self._case_base.all_cases()

    # -------------------------------------------------------------------------
    # RETRIEVAL
    # -------------------------------------------------------------------------

    def retrieve(
        self,
        query: Dict[str, Any],
        k: int = 5,
        metric: SimilarityMetric = SimilarityMetric.WEIGHTED,
        threshold: float = 0.0
    ) -> RetrievalResult:
        """Retrieve similar cases."""
        return self._retriever.retrieve(query, k, metric, threshold)

    def most_similar(
        self,
        query: Dict[str, Any],
        metric: SimilarityMetric = SimilarityMetric.WEIGHTED
    ) -> Optional[Tuple[Case, float]]:
        """Get the most similar case."""
        result = self.retrieve(query, k=1, metric=metric)

        if result.retrieved_cases:
            case_id, sim = result.retrieved_cases[0]
            case = self.get_case(case_id)
            if case:
                return (case, sim)

        return None

    # -------------------------------------------------------------------------
    # ADAPTATION
    # -------------------------------------------------------------------------

    def register_adaptation_rule(
        self,
        feature_name: str,
        rule: Callable[[Any, Any, Dict], Any]
    ) -> None:
        """Register an adaptation rule."""
        self._adapter.register_adaptation_rule(feature_name, rule)

    def adapt(
        self,
        source_case: Case,
        query: Dict[str, Any],
        adaptation_type: AdaptationType = AdaptationType.SUBSTITUTION
    ) -> AdaptationResult:
        """Adapt a case's solution."""
        return self._adapter.adapt(source_case, query, adaptation_type)

    # -------------------------------------------------------------------------
    # LEARNING
    # -------------------------------------------------------------------------

    def set_retention_policy(
        self,
        policy: RetentionPolicy,
        threshold: float = 0.7
    ) -> None:
        """Set retention policy."""
        self._learner.set_retention_policy(policy, threshold)

    def learn(
        self,
        problem: Dict[str, Any],
        solution: Dict[str, Any],
        outcome: Optional[Dict[str, Any]] = None,
        success: bool = True,
        name: str = ""
    ) -> LearningResult:
        """Learn from experience."""
        return self._learner.learn(problem, solution, outcome, success, name)

    # -------------------------------------------------------------------------
    # COMPLETE CBR CYCLE
    # -------------------------------------------------------------------------

    def solve(
        self,
        problem: Dict[str, Any],
        k: int = 5,
        adaptation_type: AdaptationType = AdaptationType.SUBSTITUTION
    ) -> Optional[AdaptationResult]:
        """Complete CBR cycle: retrieve, reuse, revise."""
        # RETRIEVE
        result = self.retrieve(problem, k=k)

        if not result.retrieved_cases:
            return None

        # Get best case
        best_id, _ = result.retrieved_cases[0]
        best_case = self.get_case(best_id)

        if not best_case:
            return None

        # Track usage
        self._case_base.increment_usage(best_id)

        # REUSE (adapt)
        adapted = self.adapt(best_case, problem, adaptation_type)

        return adapted


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Case-Based Reasoner."""
    print("=" * 70)
    print("BAEL - CASE-BASED REASONER DEMO")
    print("Advanced Case-Based Reasoning and Retrieval")
    print("=" * 70)
    print()

    cbr = CaseBasedReasoner()

    # 1. Define Features
    print("1. DEFINE FEATURES:")
    print("-" * 40)

    cbr.define_feature("bedrooms", FeatureType.NUMERIC, weight=2.0)
    cbr.define_feature("bathrooms", FeatureType.NUMERIC, weight=1.5)
    cbr.define_feature("sqft", FeatureType.NUMERIC, weight=2.5)
    cbr.define_feature("location", FeatureType.CATEGORICAL, weight=3.0)
    cbr.define_feature("garage", FeatureType.BOOLEAN, weight=1.0)

    print("   Defined: bedrooms, bathrooms, sqft, location, garage")
    print(f"   Total features: {len(cbr.all_features())}")
    print()

    # 2. Add Cases
    print("2. ADD CASES (House Pricing):")
    print("-" * 40)

    c1 = cbr.add_case(
        "House1",
        problem={"bedrooms": 3, "bathrooms": 2, "sqft": 1500, "location": "suburb", "garage": True},
        solution={"price": 350000, "days_on_market": 30}
    )

    c2 = cbr.add_case(
        "House2",
        problem={"bedrooms": 4, "bathrooms": 3, "sqft": 2200, "location": "city", "garage": True},
        solution={"price": 550000, "days_on_market": 21}
    )

    c3 = cbr.add_case(
        "House3",
        problem={"bedrooms": 2, "bathrooms": 1, "sqft": 1000, "location": "suburb", "garage": False},
        solution={"price": 220000, "days_on_market": 45}
    )

    c4 = cbr.add_case(
        "House4",
        problem={"bedrooms": 5, "bathrooms": 4, "sqft": 3500, "location": "city", "garage": True},
        solution={"price": 850000, "days_on_market": 14}
    )

    print(f"   Added {cbr.case_count()} cases")
    for case in cbr.all_cases():
        print(f"      {case.name}: ${case.solution['price']:,}")
    print()

    # 3. Retrieve Similar Cases
    print("3. RETRIEVE SIMILAR CASES:")
    print("-" * 40)

    query = {"bedrooms": 3, "bathrooms": 2, "sqft": 1800, "location": "suburb", "garage": True}
    print(f"   Query: {query}")

    result = cbr.retrieve(query, k=3)

    print(f"   Retrieved {len(result.retrieved_cases)} cases in {result.retrieval_time:.4f}s:")
    for case_id, sim in result.retrieved_cases:
        case = cbr.get_case(case_id)
        print(f"      {case.name}: similarity={sim:.3f}")
    print()

    # 4. Get Most Similar
    print("4. MOST SIMILAR CASE:")
    print("-" * 40)

    best = cbr.most_similar(query)
    if best:
        case, sim = best
        print(f"   Best match: {case.name}")
        print(f"   Similarity: {sim:.3f}")
        print(f"   Solution: {case.solution}")
    print()

    # 5. Adapt Solution
    print("5. ADAPT SOLUTION:")
    print("-" * 40)

    if best:
        # Substitution adaptation
        adapted = cbr.adapt(best[0], query, AdaptationType.SUBSTITUTION)
        print(f"   Substitution adaptation:")
        print(f"      Adapted: {adapted.adapted_solution}")
        print(f"      Confidence: {adapted.confidence:.2f}")

        # Transformation adaptation
        adapted2 = cbr.adapt(best[0], query, AdaptationType.TRANSFORMATION)
        print(f"   Transformation adaptation:")
        print(f"      Adapted: {adapted2.adapted_solution}")
        print(f"      Changes: {adapted2.changes}")
    print()

    # 6. Complete CBR Cycle
    print("6. COMPLETE CBR CYCLE (solve):")
    print("-" * 40)

    new_query = {"bedrooms": 4, "bathrooms": 2, "sqft": 2000, "location": "city", "garage": False}
    print(f"   New query: {new_query}")

    solution = cbr.solve(new_query, k=3, adaptation_type=AdaptationType.TRANSFORMATION)

    if solution:
        print(f"   Source case: {cbr.get_case(solution.source_case_id).name}")
        print(f"   Adapted solution: {solution.adapted_solution}")
        print(f"   Confidence: {solution.confidence:.2f}")
    print()

    # 7. Learn from Experience
    print("7. LEARN FROM EXPERIENCE:")
    print("-" * 40)

    cbr.set_retention_policy(RetentionPolicy.NOVELTY_BASED, threshold=0.8)

    learn_result = cbr.learn(
        problem={"bedrooms": 6, "bathrooms": 5, "sqft": 4000, "location": "rural", "garage": True},
        solution={"price": 750000, "days_on_market": 60},
        success=True,
        name="RuralMansion"
    )

    print(f"   Retained: {learn_result.retained}")
    print(f"   Reason: {learn_result.reason}")
    print(f"   New case ID: {learn_result.new_case_id}")
    print(f"   Total cases now: {cbr.case_count()}")
    print()

    # 8. Different Similarity Metrics
    print("8. COMPARE SIMILARITY METRICS:")
    print("-" * 40)

    for metric in [SimilarityMetric.WEIGHTED, SimilarityMetric.EUCLIDEAN,
                   SimilarityMetric.JACCARD, SimilarityMetric.COSINE]:
        result = cbr.retrieve(query, k=1, metric=metric)
        if result.retrieved_cases:
            case_id, sim = result.retrieved_cases[0]
            case = cbr.get_case(case_id)
            print(f"   {metric.value}: {case.name} (sim={sim:.3f})")
    print()

    # 9. Retention Policies
    print("9. DIFFERENT RETENTION POLICIES:")
    print("-" * 40)

    similar_case = {"bedrooms": 3, "bathrooms": 2, "sqft": 1550, "location": "suburb", "garage": True}

    for policy in [RetentionPolicy.ALWAYS, RetentionPolicy.NOVELTY_BASED]:
        cbr.set_retention_policy(policy, threshold=0.9)
        result = cbr.learn(
            problem=similar_case,
            solution={"price": 360000, "days_on_market": 28},
            name=f"Test-{policy.value}"
        )
        print(f"   {policy.value}: retained={result.retained}")
        print(f"      Reason: {result.reason}")
    print()

    # 10. Feature Weights
    print("10. ADJUST FEATURE WEIGHTS:")
    print("-" * 40)

    cbr.set_feature_weight("location", 5.0)  # Increase location importance

    result1 = cbr.retrieve({"bedrooms": 3, "location": "city"}, k=2)
    result2 = cbr.retrieve({"bedrooms": 3, "location": "suburb"}, k=2)

    print(f"   Query (city): top match = {cbr.get_case(result1.retrieved_cases[0][0]).name}")
    print(f"   Query (suburb): top match = {cbr.get_case(result2.retrieved_cases[0][0]).name}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Case-Based Reasoner Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
