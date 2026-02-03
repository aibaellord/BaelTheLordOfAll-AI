#!/usr/bin/env python3
"""
BAEL - Active Learner
Advanced active learning and sample selection.

Features:
- Uncertainty sampling
- Query-by-committee
- Expected model change
- Information density
- Batch mode active learning
- Pool-based and stream-based
"""

import asyncio
import copy
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

class SamplingStrategy(Enum):
    """Active learning sampling strategies."""
    RANDOM = "random"
    UNCERTAINTY = "uncertainty"
    QUERY_BY_COMMITTEE = "query_by_committee"
    EXPECTED_MODEL_CHANGE = "expected_model_change"
    INFORMATION_DENSITY = "information_density"
    DIVERSITY = "diversity"


class UncertaintyMeasure(Enum):
    """Uncertainty measures."""
    LEAST_CONFIDENCE = "least_confidence"
    MARGIN = "margin"
    ENTROPY = "entropy"


class LearningMode(Enum):
    """Active learning modes."""
    POOL_BASED = "pool_based"
    STREAM_BASED = "stream_based"
    MEMBERSHIP_QUERY = "membership_query"


class QueryStatus(Enum):
    """Status of a query."""
    PENDING = "pending"
    LABELED = "labeled"
    SKIPPED = "skipped"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Sample:
    """A data sample."""
    sample_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    features: Dict[str, Any] = field(default_factory=dict)
    label: Optional[str] = None
    predicted_probs: Dict[str, float] = field(default_factory=dict)
    uncertainty: float = 0.0
    informativeness: float = 0.0


@dataclass
class Query:
    """A query for label."""
    query_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sample_id: str = ""
    strategy: SamplingStrategy = SamplingStrategy.UNCERTAINTY
    score: float = 0.0
    status: QueryStatus = QueryStatus.PENDING
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class Committee:
    """A committee of models."""
    committee_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    models: List[str] = field(default_factory=list)
    predictions: Dict[str, Dict[str, float]] = field(default_factory=dict)


@dataclass
class LabelBudget:
    """Budget for labeling."""
    total: int = 100
    used: int = 0

    @property
    def remaining(self) -> int:
        return max(0, self.total - self.used)

    @property
    def exhausted(self) -> bool:
        return self.used >= self.total


@dataclass
class ActiveLearningState:
    """State of active learning."""
    labeled_samples: List[str] = field(default_factory=list)
    unlabeled_samples: List[str] = field(default_factory=list)
    queries: List[str] = field(default_factory=list)
    iteration: int = 0


# =============================================================================
# SAMPLE POOL
# =============================================================================

class SamplePool:
    """Pool of samples."""

    def __init__(self):
        self._samples: Dict[str, Sample] = {}
        self._labeled: Set[str] = set()
        self._unlabeled: Set[str] = set()

    def add(
        self,
        features: Dict[str, Any],
        label: Optional[str] = None
    ) -> Sample:
        """Add a sample."""
        sample = Sample(features=features, label=label)
        self._samples[sample.sample_id] = sample

        if label is not None:
            self._labeled.add(sample.sample_id)
        else:
            self._unlabeled.add(sample.sample_id)

        return sample

    def get(self, sample_id: str) -> Optional[Sample]:
        """Get a sample."""
        return self._samples.get(sample_id)

    def label(self, sample_id: str, label: str) -> Optional[Sample]:
        """Label a sample."""
        sample = self._samples.get(sample_id)
        if sample:
            sample.label = label
            self._labeled.add(sample_id)
            self._unlabeled.discard(sample_id)
        return sample

    def labeled_samples(self) -> List[Sample]:
        """Get labeled samples."""
        return [self._samples[sid] for sid in self._labeled]

    def unlabeled_samples(self) -> List[Sample]:
        """Get unlabeled samples."""
        return [self._samples[sid] for sid in self._unlabeled]

    def all_samples(self) -> List[Sample]:
        """Get all samples."""
        return list(self._samples.values())

    def n_labeled(self) -> int:
        """Number of labeled samples."""
        return len(self._labeled)

    def n_unlabeled(self) -> int:
        """Number of unlabeled samples."""
        return len(self._unlabeled)


# =============================================================================
# UNCERTAINTY SAMPLER
# =============================================================================

class UncertaintySampler:
    """Sample based on uncertainty."""

    def __init__(
        self,
        measure: UncertaintyMeasure = UncertaintyMeasure.ENTROPY
    ):
        self._measure = measure

    def compute_uncertainty(
        self,
        probs: Dict[str, float]
    ) -> float:
        """Compute uncertainty from probabilities."""
        if not probs:
            return 1.0

        values = list(probs.values())

        if self._measure == UncertaintyMeasure.LEAST_CONFIDENCE:
            return 1.0 - max(values)

        elif self._measure == UncertaintyMeasure.MARGIN:
            sorted_probs = sorted(values, reverse=True)
            if len(sorted_probs) >= 2:
                return 1.0 - (sorted_probs[0] - sorted_probs[1])
            return 1.0 - sorted_probs[0]

        elif self._measure == UncertaintyMeasure.ENTROPY:
            entropy = 0.0
            for p in values:
                if p > 0:
                    entropy -= p * math.log2(p)
            # Normalize
            max_entropy = math.log2(len(values)) if len(values) > 1 else 1.0
            return entropy / max_entropy if max_entropy > 0 else 0.0

        return 0.0

    def select(
        self,
        samples: List[Sample],
        n: int = 1
    ) -> List[Sample]:
        """Select most uncertain samples."""
        for sample in samples:
            sample.uncertainty = self.compute_uncertainty(sample.predicted_probs)

        sorted_samples = sorted(samples, key=lambda s: s.uncertainty, reverse=True)
        return sorted_samples[:n]


# =============================================================================
# QUERY BY COMMITTEE
# =============================================================================

class QueryByCommittee:
    """Query-by-committee sampling."""

    def __init__(self, n_models: int = 3):
        self._n_models = n_models
        self._committees: Dict[str, Committee] = {}

    def create_committee(self) -> Committee:
        """Create a committee."""
        committee = Committee(
            models=[f"model_{i}" for i in range(self._n_models)]
        )
        self._committees[committee.committee_id] = committee
        return committee

    def vote(
        self,
        sample: Sample,
        model_predictions: Dict[str, Dict[str, float]]
    ) -> float:
        """Calculate vote entropy (disagreement)."""
        # Aggregate votes
        vote_counts = defaultdict(int)

        for model, probs in model_predictions.items():
            if probs:
                best_label = max(probs.keys(), key=lambda k: probs[k])
                vote_counts[best_label] += 1

        # Calculate entropy of votes
        total = sum(vote_counts.values())
        if total == 0:
            return 1.0

        entropy = 0.0
        for count in vote_counts.values():
            p = count / total
            if p > 0:
                entropy -= p * math.log2(p)

        # Normalize
        max_entropy = math.log2(len(vote_counts)) if len(vote_counts) > 1 else 1.0
        return entropy / max_entropy if max_entropy > 0 else 0.0

    def select(
        self,
        samples: List[Sample],
        model_predictions: Dict[str, Dict[str, Dict[str, float]]],
        n: int = 1
    ) -> List[Sample]:
        """Select samples with highest disagreement."""
        disagreements = []

        for sample in samples:
            sample_preds = {
                model: preds.get(sample.sample_id, {})
                for model, preds in model_predictions.items()
            }
            disagreement = self.vote(sample, sample_preds)
            disagreements.append((sample, disagreement))

        sorted_samples = sorted(disagreements, key=lambda x: x[1], reverse=True)
        return [s for s, _ in sorted_samples[:n]]


# =============================================================================
# DIVERSITY SAMPLER
# =============================================================================

class DiversitySampler:
    """Sample diverse examples."""

    def compute_similarity(
        self,
        sample1: Sample,
        sample2: Sample
    ) -> float:
        """Compute similarity between samples."""
        common = set(sample1.features.keys()) & set(sample2.features.keys())
        if not common:
            return 0.0

        matches = sum(
            1 for k in common
            if sample1.features[k] == sample2.features[k]
        )

        return matches / len(common)

    def select_diverse(
        self,
        samples: List[Sample],
        n: int = 5
    ) -> List[Sample]:
        """Select diverse samples using greedy selection."""
        if len(samples) <= n:
            return samples

        selected = [samples[0]]
        remaining = samples[1:]

        while len(selected) < n and remaining:
            # Find sample most dissimilar to selected
            best_sample = None
            best_min_sim = float('inf')

            for sample in remaining:
                min_sim = min(
                    self.compute_similarity(sample, s)
                    for s in selected
                )
                if min_sim < best_min_sim:
                    best_min_sim = min_sim
                    best_sample = sample

            if best_sample:
                selected.append(best_sample)
                remaining.remove(best_sample)
            else:
                break

        return selected


# =============================================================================
# INFORMATION DENSITY
# =============================================================================

class InformationDensity:
    """Information density sampling."""

    def __init__(self, beta: float = 1.0):
        self._beta = beta

    def compute_density(
        self,
        sample: Sample,
        all_samples: List[Sample]
    ) -> float:
        """Compute information density."""
        if len(all_samples) <= 1:
            return 1.0

        # Average similarity to all other samples
        total_sim = 0.0
        count = 0

        for other in all_samples:
            if other.sample_id != sample.sample_id:
                sim = self._similarity(sample, other)
                total_sim += sim
                count += 1

        avg_sim = total_sim / count if count > 0 else 0.0
        return avg_sim ** self._beta

    def _similarity(self, s1: Sample, s2: Sample) -> float:
        """Compute similarity."""
        common = set(s1.features.keys()) & set(s2.features.keys())
        if not common:
            return 0.0

        matches = sum(1 for k in common if s1.features[k] == s2.features[k])
        return matches / len(common)

    def select(
        self,
        samples: List[Sample],
        n: int = 1
    ) -> List[Sample]:
        """Select samples with highest information density weighted uncertainty."""
        for sample in samples:
            density = self.compute_density(sample, samples)
            sample.informativeness = sample.uncertainty * density

        sorted_samples = sorted(samples, key=lambda s: s.informativeness, reverse=True)
        return sorted_samples[:n]


# =============================================================================
# ACTIVE LEARNER
# =============================================================================

class ActiveLearner:
    """
    Active Learner for BAEL.

    Advanced active learning and sample selection.
    """

    def __init__(
        self,
        budget: int = 100,
        strategy: SamplingStrategy = SamplingStrategy.UNCERTAINTY
    ):
        self._pool = SamplePool()
        self._budget = LabelBudget(total=budget)
        self._strategy = strategy
        self._uncertainty_sampler = UncertaintySampler()
        self._qbc = QueryByCommittee()
        self._diversity_sampler = DiversitySampler()
        self._info_density = InformationDensity()
        self._queries: Dict[str, Query] = {}
        self._state = ActiveLearningState()

    # -------------------------------------------------------------------------
    # POOL MANAGEMENT
    # -------------------------------------------------------------------------

    def add_sample(
        self,
        features: Dict[str, Any],
        label: Optional[str] = None
    ) -> Sample:
        """Add a sample to pool."""
        sample = self._pool.add(features, label)

        if label is None:
            self._state.unlabeled_samples.append(sample.sample_id)
        else:
            self._state.labeled_samples.append(sample.sample_id)

        return sample

    def get_sample(self, sample_id: str) -> Optional[Sample]:
        """Get a sample."""
        return self._pool.get(sample_id)

    def labeled_samples(self) -> List[Sample]:
        """Get labeled samples."""
        return self._pool.labeled_samples()

    def unlabeled_samples(self) -> List[Sample]:
        """Get unlabeled samples."""
        return self._pool.unlabeled_samples()

    # -------------------------------------------------------------------------
    # PREDICTIONS
    # -------------------------------------------------------------------------

    def update_predictions(
        self,
        predictions: Dict[str, Dict[str, float]]
    ) -> None:
        """Update predictions for samples."""
        for sample_id, probs in predictions.items():
            sample = self._pool.get(sample_id)
            if sample:
                sample.predicted_probs = probs

    # -------------------------------------------------------------------------
    # QUERY SELECTION
    # -------------------------------------------------------------------------

    def select_queries(
        self,
        n: int = 1,
        strategy: Optional[SamplingStrategy] = None
    ) -> List[Query]:
        """Select samples to query."""
        if self._budget.exhausted:
            return []

        strategy = strategy or self._strategy
        unlabeled = self._pool.unlabeled_samples()

        if not unlabeled:
            return []

        n = min(n, self._budget.remaining, len(unlabeled))

        if strategy == SamplingStrategy.RANDOM:
            selected = random.sample(unlabeled, n)

        elif strategy == SamplingStrategy.UNCERTAINTY:
            selected = self._uncertainty_sampler.select(unlabeled, n)

        elif strategy == SamplingStrategy.DIVERSITY:
            selected = self._diversity_sampler.select_diverse(unlabeled, n)

        elif strategy == SamplingStrategy.INFORMATION_DENSITY:
            # First compute uncertainties
            for sample in unlabeled:
                sample.uncertainty = self._uncertainty_sampler.compute_uncertainty(
                    sample.predicted_probs
                )
            selected = self._info_density.select(unlabeled, n)

        else:
            selected = random.sample(unlabeled, n)

        # Create queries
        queries = []
        for sample in selected:
            query = Query(
                sample_id=sample.sample_id,
                strategy=strategy,
                score=sample.uncertainty
            )
            self._queries[query.query_id] = query
            self._state.queries.append(query.query_id)
            queries.append(query)

        return queries

    # -------------------------------------------------------------------------
    # LABELING
    # -------------------------------------------------------------------------

    def label_sample(
        self,
        sample_id: str,
        label: str
    ) -> Optional[Sample]:
        """Label a sample."""
        if self._budget.exhausted:
            return None

        sample = self._pool.label(sample_id, label)
        if sample:
            self._budget.used += 1

            if sample_id in self._state.unlabeled_samples:
                self._state.unlabeled_samples.remove(sample_id)

            if sample_id not in self._state.labeled_samples:
                self._state.labeled_samples.append(sample_id)

            # Update query status
            for query in self._queries.values():
                if query.sample_id == sample_id:
                    query.status = QueryStatus.LABELED

        return sample

    def answer_query(
        self,
        query_id: str,
        label: str
    ) -> Optional[Sample]:
        """Answer a query with a label."""
        query = self._queries.get(query_id)
        if not query:
            return None

        return self.label_sample(query.sample_id, label)

    # -------------------------------------------------------------------------
    # BUDGET
    # -------------------------------------------------------------------------

    def budget_remaining(self) -> int:
        """Get remaining budget."""
        return self._budget.remaining

    def budget_used(self) -> int:
        """Get used budget."""
        return self._budget.used

    def is_exhausted(self) -> bool:
        """Check if budget is exhausted."""
        return self._budget.exhausted

    # -------------------------------------------------------------------------
    # STATE
    # -------------------------------------------------------------------------

    def get_state(self) -> ActiveLearningState:
        """Get current state."""
        return self._state

    def next_iteration(self) -> int:
        """Move to next iteration."""
        self._state.iteration += 1
        return self._state.iteration

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def statistics(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            "n_labeled": self._pool.n_labeled(),
            "n_unlabeled": self._pool.n_unlabeled(),
            "budget_total": self._budget.total,
            "budget_used": self._budget.used,
            "budget_remaining": self._budget.remaining,
            "n_queries": len(self._queries),
            "iteration": self._state.iteration
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Active Learner."""
    print("=" * 70)
    print("BAEL - ACTIVE LEARNER DEMO")
    print("Advanced Active Learning and Sample Selection")
    print("=" * 70)
    print()

    learner = ActiveLearner(budget=10, strategy=SamplingStrategy.UNCERTAINTY)

    # 1. Add Samples
    print("1. ADD SAMPLES:")
    print("-" * 40)

    # Add some labeled samples
    learner.add_sample({"color": "red", "size": "large"}, label="positive")
    learner.add_sample({"color": "blue", "size": "small"}, label="negative")

    # Add unlabeled samples
    unlabeled_data = [
        {"color": "red", "size": "small"},
        {"color": "blue", "size": "large"},
        {"color": "green", "size": "medium"},
        {"color": "red", "size": "medium"},
        {"color": "blue", "size": "medium"},
        {"color": "green", "size": "small"},
        {"color": "green", "size": "large"},
    ]

    for features in unlabeled_data:
        learner.add_sample(features)

    print(f"   Labeled: {learner._pool.n_labeled()}")
    print(f"   Unlabeled: {learner._pool.n_unlabeled()}")
    print()

    # 2. Update Predictions
    print("2. UPDATE PREDICTIONS:")
    print("-" * 40)

    # Simulate model predictions
    predictions = {}
    for sample in learner.unlabeled_samples():
        # Random predictions for demo
        p = random.random()
        predictions[sample.sample_id] = {
            "positive": p,
            "negative": 1 - p
        }

    learner.update_predictions(predictions)
    print("   Updated predictions for all unlabeled samples")
    print()

    # 3. Select Queries (Uncertainty)
    print("3. SELECT QUERIES (UNCERTAINTY):")
    print("-" * 40)

    queries = learner.select_queries(n=3, strategy=SamplingStrategy.UNCERTAINTY)
    for query in queries:
        sample = learner.get_sample(query.sample_id)
        if sample:
            print(f"   Query {query.query_id[:8]}...")
            print(f"      Features: {sample.features}")
            print(f"      Uncertainty: {query.score:.3f}")
    print()

    # 4. Answer Queries
    print("4. ANSWER QUERIES:")
    print("-" * 40)

    for query in queries:
        # Simulate human labeling
        label = random.choice(["positive", "negative"])
        learner.answer_query(query.query_id, label)
        print(f"   Labeled: {query.query_id[:8]}... → {label}")
    print()

    # 5. Diversity Sampling
    print("5. DIVERSITY SAMPLING:")
    print("-" * 40)

    queries = learner.select_queries(n=2, strategy=SamplingStrategy.DIVERSITY)
    for query in queries:
        sample = learner.get_sample(query.sample_id)
        if sample:
            print(f"   Selected: {sample.features}")
    print()

    # 6. Information Density
    print("6. INFORMATION DENSITY:")
    print("-" * 40)

    queries = learner.select_queries(n=2, strategy=SamplingStrategy.INFORMATION_DENSITY)
    for query in queries:
        sample = learner.get_sample(query.sample_id)
        if sample:
            print(f"   Selected: {sample.features}")
            print(f"      Informativeness: {sample.informativeness:.3f}")
    print()

    # 7. Budget Status
    print("7. BUDGET STATUS:")
    print("-" * 40)

    print(f"   Total: {learner._budget.total}")
    print(f"   Used: {learner.budget_used()}")
    print(f"   Remaining: {learner.budget_remaining()}")
    print(f"   Exhausted: {learner.is_exhausted()}")
    print()

    # 8. Statistics
    print("8. STATISTICS:")
    print("-" * 40)

    stats = learner.statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()

    # 9. Active Learning Loop
    print("9. ACTIVE LEARNING LOOP:")
    print("-" * 40)

    learner2 = ActiveLearner(budget=5)

    for features in unlabeled_data[:5]:
        learner2.add_sample(features)

    # Simulate predictions
    for sample in learner2.unlabeled_samples():
        p = random.random()
        sample.predicted_probs = {"pos": p, "neg": 1 - p}

    iteration = 0
    while not learner2.is_exhausted() and learner2._pool.n_unlabeled() > 0:
        iteration = learner2.next_iteration()

        queries = learner2.select_queries(n=1)
        if not queries:
            break

        for query in queries:
            label = random.choice(["pos", "neg"])
            learner2.answer_query(query.query_id, label)
            print(f"   Iteration {iteration}: labeled 1 sample as '{label}'")

    print(f"\n   Final: {learner2._pool.n_labeled()} labeled, {learner2._pool.n_unlabeled()} unlabeled")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Active Learner Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
