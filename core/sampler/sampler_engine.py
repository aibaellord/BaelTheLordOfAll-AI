#!/usr/bin/env python3
"""
BAEL - Sampler Engine
Comprehensive data sampling for ML pipelines.

Features:
- Random sampling
- Stratified sampling
- Weighted sampling
- Reservoir sampling
- Importance sampling
- Bootstrap sampling
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
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Sequence, Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class SamplerType(Enum):
    """Sampler types."""
    RANDOM = "random"
    SEQUENTIAL = "sequential"
    STRATIFIED = "stratified"
    WEIGHTED = "weighted"
    RESERVOIR = "reservoir"
    IMPORTANCE = "importance"
    BOOTSTRAP = "bootstrap"
    CLUSTER = "cluster"
    SYSTEMATIC = "systematic"
    CUSTOM = "custom"


class ReplacementMode(Enum):
    """Sampling replacement modes."""
    WITH_REPLACEMENT = "with_replacement"
    WITHOUT_REPLACEMENT = "without_replacement"


class BalanceStrategy(Enum):
    """Class balancing strategies."""
    UNDERSAMPLE = "undersample"
    OVERSAMPLE = "oversample"
    HYBRID = "hybrid"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Sample:
    """A single sample."""
    index: int = 0
    data: Any = None
    label: Optional[Any] = None
    weight: float = 1.0
    selected_count: int = 0


@dataclass
class SamplingResult:
    """Result of sampling operation."""
    samples: List[Sample] = field(default_factory=list)
    indices: List[int] = field(default_factory=list)
    weights: List[float] = field(default_factory=list)
    total_population: int = 0
    sample_size: int = 0
    method: str = ""


@dataclass
class SamplerConfig:
    """Sampler configuration."""
    seed: Optional[int] = None
    replacement: ReplacementMode = ReplacementMode.WITHOUT_REPLACEMENT
    shuffle: bool = True
    drop_last: bool = False


@dataclass
class SamplerStats:
    """Sampler statistics."""
    total_samples: int = 0
    unique_samples: int = 0
    mean_weight: float = 0.0
    class_distribution: Dict[Any, int] = field(default_factory=dict)
    sampling_rate: float = 0.0


# =============================================================================
# BASE SAMPLER
# =============================================================================

class BaseSampler(ABC, Generic[T]):
    """Abstract base sampler."""

    def __init__(
        self,
        data: Optional[List[T]] = None,
        config: Optional[SamplerConfig] = None,
        name: Optional[str] = None
    ):
        self._data = data or []
        self.config = config or SamplerConfig()
        self.name = name or self.__class__.__name__

        if self.config.seed is not None:
            random.seed(self.config.seed)

    @abstractmethod
    def sample(self, n: int) -> SamplingResult:
        """Sample n items from data."""
        pass

    def set_data(self, data: List[T]) -> None:
        """Set data source."""
        self._data = data

    def __len__(self) -> int:
        """Return data length."""
        return len(self._data)

    def __iter__(self) -> Iterator[int]:
        """Iterate over sample indices."""
        result = self.sample(len(self._data))
        return iter(result.indices)


# =============================================================================
# SAMPLER IMPLEMENTATIONS
# =============================================================================

class RandomSampler(BaseSampler[T]):
    """Random sampler."""

    def sample(self, n: int) -> SamplingResult:
        """Sample n random items."""
        population = list(range(len(self._data)))

        if self.config.replacement == ReplacementMode.WITH_REPLACEMENT:
            indices = [random.choice(population) for _ in range(n)]
        else:
            n = min(n, len(population))
            indices = random.sample(population, n)

        samples = [
            Sample(index=idx, data=self._data[idx])
            for idx in indices
        ]

        return SamplingResult(
            samples=samples,
            indices=indices,
            weights=[1.0] * len(indices),
            total_population=len(self._data),
            sample_size=len(indices),
            method="random"
        )


class SequentialSampler(BaseSampler[T]):
    """Sequential sampler."""

    def sample(self, n: int) -> SamplingResult:
        """Sample n sequential items."""
        n = min(n, len(self._data))
        indices = list(range(n))

        samples = [
            Sample(index=idx, data=self._data[idx])
            for idx in indices
        ]

        return SamplingResult(
            samples=samples,
            indices=indices,
            weights=[1.0] * n,
            total_population=len(self._data),
            sample_size=n,
            method="sequential"
        )


class StratifiedSampler(BaseSampler[T]):
    """Stratified sampler for labeled data."""

    def __init__(
        self,
        data: Optional[List[T]] = None,
        labels: Optional[List[Any]] = None,
        config: Optional[SamplerConfig] = None
    ):
        super().__init__(data, config, "StratifiedSampler")
        self._labels = labels or []

    def set_labels(self, labels: List[Any]) -> None:
        """Set labels."""
        self._labels = labels

    def sample(self, n: int) -> SamplingResult:
        """Sample n items maintaining class proportions."""
        if not self._labels or len(self._labels) != len(self._data):
            return RandomSampler(self._data, self.config).sample(n)

        label_indices: Dict[Any, List[int]] = defaultdict(list)
        for idx, label in enumerate(self._labels):
            label_indices[label].append(idx)

        label_counts = {label: len(indices) for label, indices in label_indices.items()}
        total = sum(label_counts.values())

        all_indices = []
        for label, indices in label_indices.items():
            n_samples = max(1, int(n * len(indices) / total))

            if self.config.replacement == ReplacementMode.WITH_REPLACEMENT:
                selected = [random.choice(indices) for _ in range(n_samples)]
            else:
                n_samples = min(n_samples, len(indices))
                selected = random.sample(indices, n_samples)

            all_indices.extend(selected)

        if self.config.shuffle:
            random.shuffle(all_indices)

        samples = [
            Sample(
                index=idx,
                data=self._data[idx],
                label=self._labels[idx]
            )
            for idx in all_indices
        ]

        return SamplingResult(
            samples=samples,
            indices=all_indices,
            weights=[1.0] * len(all_indices),
            total_population=len(self._data),
            sample_size=len(all_indices),
            method="stratified"
        )


class WeightedSampler(BaseSampler[T]):
    """Weighted random sampler."""

    def __init__(
        self,
        data: Optional[List[T]] = None,
        weights: Optional[List[float]] = None,
        config: Optional[SamplerConfig] = None
    ):
        super().__init__(data, config, "WeightedSampler")
        self._weights = weights or []

    def set_weights(self, weights: List[float]) -> None:
        """Set sampling weights."""
        self._weights = weights

    def sample(self, n: int) -> SamplingResult:
        """Sample n items according to weights."""
        if not self._weights or len(self._weights) != len(self._data):
            return RandomSampler(self._data, self.config).sample(n)

        population = list(range(len(self._data)))

        if self.config.replacement == ReplacementMode.WITH_REPLACEMENT:
            indices = random.choices(population, weights=self._weights, k=n)
        else:
            indices = []
            remaining = list(population)
            remaining_weights = list(self._weights)

            n = min(n, len(remaining))

            for _ in range(n):
                if not remaining:
                    break

                idx = random.choices(range(len(remaining)), weights=remaining_weights)[0]
                indices.append(remaining[idx])

                remaining.pop(idx)
                remaining_weights.pop(idx)

        samples = [
            Sample(
                index=idx,
                data=self._data[idx],
                weight=self._weights[idx]
            )
            for idx in indices
        ]

        return SamplingResult(
            samples=samples,
            indices=indices,
            weights=[self._weights[idx] for idx in indices],
            total_population=len(self._data),
            sample_size=len(indices),
            method="weighted"
        )


class ReservoirSampler(BaseSampler[T]):
    """Reservoir sampling for streaming data."""

    def __init__(
        self,
        reservoir_size: int = 100,
        config: Optional[SamplerConfig] = None
    ):
        super().__init__(None, config, "ReservoirSampler")
        self._reservoir_size = reservoir_size
        self._reservoir: List[Tuple[int, T]] = []
        self._count = 0

    def add(self, item: T) -> None:
        """Add item to stream."""
        self._count += 1

        if len(self._reservoir) < self._reservoir_size:
            self._reservoir.append((self._count - 1, item))
        else:
            j = random.randint(0, self._count - 1)
            if j < self._reservoir_size:
                self._reservoir[j] = (self._count - 1, item)

    def get_reservoir(self) -> List[T]:
        """Get current reservoir."""
        return [item for _, item in self._reservoir]

    def sample(self, n: int) -> SamplingResult:
        """Get samples from reservoir."""
        n = min(n, len(self._reservoir))
        selected = random.sample(self._reservoir, n)

        indices = [idx for idx, _ in selected]
        samples = [
            Sample(index=idx, data=item)
            for idx, item in selected
        ]

        return SamplingResult(
            samples=samples,
            indices=indices,
            weights=[1.0] * n,
            total_population=self._count,
            sample_size=n,
            method="reservoir"
        )

    def reset(self) -> None:
        """Reset reservoir."""
        self._reservoir = []
        self._count = 0


class ImportanceSampler(BaseSampler[T]):
    """Importance sampler with target distribution."""

    def __init__(
        self,
        data: Optional[List[T]] = None,
        proposal_weights: Optional[List[float]] = None,
        target_weights: Optional[List[float]] = None,
        config: Optional[SamplerConfig] = None
    ):
        super().__init__(data, config, "ImportanceSampler")
        self._proposal = proposal_weights or []
        self._target = target_weights or []

    def set_distributions(
        self,
        proposal: List[float],
        target: List[float]
    ) -> None:
        """Set proposal and target distributions."""
        self._proposal = proposal
        self._target = target

    def sample(self, n: int) -> SamplingResult:
        """Sample with importance weights."""
        if (not self._proposal or not self._target or
            len(self._proposal) != len(self._data) or
            len(self._target) != len(self._data)):
            return RandomSampler(self._data, self.config).sample(n)

        population = list(range(len(self._data)))
        indices = random.choices(population, weights=self._proposal, k=n)

        importance_weights = []
        for idx in indices:
            q = self._proposal[idx]
            p = self._target[idx]

            if q > 0:
                w = p / q
            else:
                w = 0.0
            importance_weights.append(w)

        sum_w = sum(importance_weights)
        if sum_w > 0:
            importance_weights = [w / sum_w * len(importance_weights) for w in importance_weights]

        samples = [
            Sample(
                index=idx,
                data=self._data[idx],
                weight=w
            )
            for idx, w in zip(indices, importance_weights)
        ]

        return SamplingResult(
            samples=samples,
            indices=indices,
            weights=importance_weights,
            total_population=len(self._data),
            sample_size=len(indices),
            method="importance"
        )


class BootstrapSampler(BaseSampler[T]):
    """Bootstrap sampler."""

    def sample(self, n: int) -> SamplingResult:
        """Bootstrap sample (with replacement)."""
        population = list(range(len(self._data)))
        indices = [random.choice(population) for _ in range(n)]

        samples = [
            Sample(index=idx, data=self._data[idx])
            for idx in indices
        ]

        return SamplingResult(
            samples=samples,
            indices=indices,
            weights=[1.0] * n,
            total_population=len(self._data),
            sample_size=n,
            method="bootstrap"
        )

    def bootstrap_samples(self, n_samples: int, n_bootstrap: int) -> List[SamplingResult]:
        """Generate multiple bootstrap samples."""
        return [self.sample(n_samples) for _ in range(n_bootstrap)]


class SystematicSampler(BaseSampler[T]):
    """Systematic sampler."""

    def sample(self, n: int) -> SamplingResult:
        """Systematic sampling."""
        if n >= len(self._data):
            indices = list(range(len(self._data)))
        else:
            k = len(self._data) / n
            start = random.uniform(0, k)
            indices = [int(start + i * k) for i in range(n)]
            indices = [idx for idx in indices if idx < len(self._data)]

        samples = [
            Sample(index=idx, data=self._data[idx])
            for idx in indices
        ]

        return SamplingResult(
            samples=samples,
            indices=indices,
            weights=[1.0] * len(indices),
            total_population=len(self._data),
            sample_size=len(indices),
            method="systematic"
        )


class BalancedSampler(BaseSampler[T]):
    """Balanced sampler for imbalanced classes."""

    def __init__(
        self,
        data: Optional[List[T]] = None,
        labels: Optional[List[Any]] = None,
        strategy: BalanceStrategy = BalanceStrategy.OVERSAMPLE,
        config: Optional[SamplerConfig] = None
    ):
        super().__init__(data, config, "BalancedSampler")
        self._labels = labels or []
        self._strategy = strategy

    def set_labels(self, labels: List[Any]) -> None:
        """Set labels."""
        self._labels = labels

    def sample(self, n: int) -> SamplingResult:
        """Sample with class balancing."""
        if not self._labels or len(self._labels) != len(self._data):
            return RandomSampler(self._data, self.config).sample(n)

        label_indices: Dict[Any, List[int]] = defaultdict(list)
        for idx, label in enumerate(self._labels):
            label_indices[label].append(idx)

        class_counts = {label: len(indices) for label, indices in label_indices.items()}

        if self._strategy == BalanceStrategy.UNDERSAMPLE:
            target_count = min(class_counts.values())
        elif self._strategy == BalanceStrategy.OVERSAMPLE:
            target_count = max(class_counts.values())
        else:
            target_count = sum(class_counts.values()) // len(class_counts)

        all_indices = []

        for label, indices in label_indices.items():
            current_count = len(indices)

            if current_count >= target_count:
                selected = random.sample(indices, target_count)
            else:
                selected = list(indices)
                while len(selected) < target_count:
                    selected.extend(random.choices(indices, k=target_count - len(selected)))
                selected = selected[:target_count]

            all_indices.extend(selected)

        if self.config.shuffle:
            random.shuffle(all_indices)

        samples = [
            Sample(
                index=idx,
                data=self._data[idx],
                label=self._labels[idx]
            )
            for idx in all_indices
        ]

        return SamplingResult(
            samples=samples,
            indices=all_indices,
            weights=[1.0] * len(all_indices),
            total_population=len(self._data),
            sample_size=len(all_indices),
            method="balanced"
        )


# =============================================================================
# SAMPLER ENGINE
# =============================================================================

class SamplerEngine:
    """
    Sampler Engine for BAEL.

    Comprehensive data sampling for ML pipelines.
    """

    def __init__(self):
        self._samplers: Dict[str, BaseSampler] = {}

    def create_sampler(
        self,
        name: str,
        sampler_type: SamplerType,
        data: Optional[List[Any]] = None,
        config: Optional[SamplerConfig] = None,
        **kwargs
    ) -> BaseSampler:
        """Create and register sampler."""
        if sampler_type == SamplerType.RANDOM:
            sampler = RandomSampler(data, config)
        elif sampler_type == SamplerType.SEQUENTIAL:
            sampler = SequentialSampler(data, config)
        elif sampler_type == SamplerType.STRATIFIED:
            sampler = StratifiedSampler(data, config=config, **kwargs)
        elif sampler_type == SamplerType.WEIGHTED:
            sampler = WeightedSampler(data, config=config, **kwargs)
        elif sampler_type == SamplerType.RESERVOIR:
            sampler = ReservoirSampler(config=config, **kwargs)
        elif sampler_type == SamplerType.IMPORTANCE:
            sampler = ImportanceSampler(data, config=config, **kwargs)
        elif sampler_type == SamplerType.BOOTSTRAP:
            sampler = BootstrapSampler(data, config)
        elif sampler_type == SamplerType.SYSTEMATIC:
            sampler = SystematicSampler(data, config)
        else:
            sampler = RandomSampler(data, config)

        self._samplers[name] = sampler
        return sampler

    def get_sampler(self, name: str) -> Optional[BaseSampler]:
        """Get sampler by name."""
        return self._samplers.get(name)

    def sample(
        self,
        name: str,
        n: int
    ) -> SamplingResult:
        """Sample from named sampler."""
        if name not in self._samplers:
            return SamplingResult()
        return self._samplers[name].sample(n)

    def get_stats(self, result: SamplingResult) -> SamplerStats:
        """Compute sampling statistics."""
        unique = len(set(result.indices))

        label_dist: Dict[Any, int] = defaultdict(int)
        for sample in result.samples:
            if sample.label is not None:
                label_dist[sample.label] += 1

        mean_weight = sum(result.weights) / len(result.weights) if result.weights else 0.0

        return SamplerStats(
            total_samples=result.sample_size,
            unique_samples=unique,
            mean_weight=mean_weight,
            class_distribution=dict(label_dist),
            sampling_rate=result.sample_size / result.total_population if result.total_population else 0.0
        )


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Sampler Engine."""
    print("=" * 70)
    print("BAEL - SAMPLER ENGINE DEMO")
    print("Comprehensive Data Sampling for ML Pipelines")
    print("=" * 70)
    print()

    engine = SamplerEngine()

    data = list(range(100))
    labels = [i % 4 for i in range(100)]

    # 1. Random Sampling
    print("1. RANDOM SAMPLING:")
    print("-" * 40)

    random_sampler = engine.create_sampler("random", SamplerType.RANDOM, data)
    result = engine.sample("random", 10)

    print(f"   Population: {result.total_population}")
    print(f"   Sample size: {result.sample_size}")
    print(f"   Indices: {result.indices[:10]}")
    print()

    # 2. Sequential Sampling
    print("2. SEQUENTIAL SAMPLING:")
    print("-" * 40)

    seq_sampler = engine.create_sampler("sequential", SamplerType.SEQUENTIAL, data)
    result = engine.sample("sequential", 10)

    print(f"   Indices: {result.indices}")
    print()

    # 3. Stratified Sampling
    print("3. STRATIFIED SAMPLING:")
    print("-" * 40)

    strat_sampler = engine.create_sampler(
        "stratified",
        SamplerType.STRATIFIED,
        data,
        labels=labels
    )
    result = engine.sample("stratified", 20)

    stats = engine.get_stats(result)
    print(f"   Sample size: {result.sample_size}")
    print(f"   Class distribution: {stats.class_distribution}")
    print()

    # 4. Weighted Sampling
    print("4. WEIGHTED SAMPLING:")
    print("-" * 40)

    weights = [1.0 if i < 20 else 0.1 for i in range(100)]

    weighted_sampler = engine.create_sampler(
        "weighted",
        SamplerType.WEIGHTED,
        data,
        weights=weights
    )
    result = engine.sample("weighted", 20)

    low_idx = sum(1 for idx in result.indices if idx < 20)
    print(f"   Samples from first 20 (high weight): {low_idx}")
    print(f"   Samples from rest (low weight): {len(result.indices) - low_idx}")
    print()

    # 5. Reservoir Sampling
    print("5. RESERVOIR SAMPLING:")
    print("-" * 40)

    reservoir = engine.create_sampler(
        "reservoir",
        SamplerType.RESERVOIR,
        reservoir_size=10
    )

    for i in range(1000):
        reservoir.add(i)

    result = reservoir.sample(5)

    print(f"   Stream size: 1000")
    print(f"   Reservoir size: 10")
    print(f"   Sample: {[s.data for s in result.samples]}")
    print()

    # 6. Bootstrap Sampling
    print("6. BOOTSTRAP SAMPLING:")
    print("-" * 40)

    bootstrap_sampler = engine.create_sampler(
        "bootstrap",
        SamplerType.BOOTSTRAP,
        data
    )

    result = bootstrap_sampler.sample(10)
    stats = engine.get_stats(result)

    print(f"   Sample size: {result.sample_size}")
    print(f"   Unique samples: {stats.unique_samples}")
    print(f"   Indices: {result.indices}")
    print()

    # 7. Systematic Sampling
    print("7. SYSTEMATIC SAMPLING:")
    print("-" * 40)

    systematic_sampler = engine.create_sampler(
        "systematic",
        SamplerType.SYSTEMATIC,
        data
    )

    result = engine.sample("systematic", 10)

    print(f"   Indices: {result.indices}")

    if len(result.indices) > 1:
        gaps = [result.indices[i+1] - result.indices[i] for i in range(len(result.indices)-1)]
        print(f"   Gaps: {gaps}")
    print()

    # 8. Balanced Sampling
    print("8. BALANCED SAMPLING:")
    print("-" * 40)

    imbalanced_labels = [0] * 80 + [1] * 15 + [2] * 5
    imbalanced_data = list(range(100))

    balanced_sampler = BalancedSampler(
        imbalanced_data,
        imbalanced_labels,
        BalanceStrategy.OVERSAMPLE
    )

    result = balanced_sampler.sample(100)
    stats = engine.get_stats(result)

    print(f"   Original distribution: 0:80, 1:15, 2:5")
    print(f"   Balanced distribution: {stats.class_distribution}")
    print()

    # 9. Sampling Statistics
    print("9. SAMPLING STATISTICS:")
    print("-" * 40)

    result = engine.sample("random", 50)
    stats = engine.get_stats(result)

    print(f"   Total samples: {stats.total_samples}")
    print(f"   Unique samples: {stats.unique_samples}")
    print(f"   Sampling rate: {stats.sampling_rate:.2%}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Sampler Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
