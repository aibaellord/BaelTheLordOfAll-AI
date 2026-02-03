#!/usr/bin/env python3
"""
BAEL - Data Normalization Engine
Comprehensive data normalization and standardization.

Features:
- Z-score normalization
- Min-Max scaling
- Robust scaling
- L1/L2 normalization
- Quantile transformation
- Power transformation
"""

import asyncio
import math
import random
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Sequence,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class NormalizationType(Enum):
    """Normalization types."""
    ZSCORE = "zscore"
    MINMAX = "minmax"
    MAXABS = "maxabs"
    ROBUST = "robust"
    L1 = "l1"
    L2 = "l2"
    QUANTILE = "quantile"
    POWER = "power"
    LOG = "log"
    CUSTOM = "custom"


class FitMode(Enum):
    """Fitting mode."""
    FIT = "fit"
    TRANSFORM = "transform"
    FIT_TRANSFORM = "fit_transform"
    INVERSE = "inverse"


class ClipMode(Enum):
    """Value clipping mode."""
    NONE = "none"
    CLIP = "clip"
    WRAP = "wrap"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class NormalizationStats:
    """Statistics for normalization."""
    mean: Optional[List[float]] = None
    std: Optional[List[float]] = None
    min_val: Optional[List[float]] = None
    max_val: Optional[List[float]] = None
    median: Optional[List[float]] = None
    q1: Optional[List[float]] = None
    q3: Optional[List[float]] = None
    iqr: Optional[List[float]] = None
    n_samples: int = 0
    n_features: int = 0


@dataclass
class NormalizationConfig:
    """Normalization configuration."""
    feature_range: Tuple[float, float] = (0.0, 1.0)
    with_centering: bool = True
    with_scaling: bool = True
    clip: bool = False
    epsilon: float = 1e-8
    copy: bool = True


@dataclass
class TransformResult:
    """Result of transformation."""
    data: List[List[float]] = field(default_factory=list)
    stats: Optional[NormalizationStats] = None
    normalization_type: str = ""
    inverse_possible: bool = True


# =============================================================================
# BASE NORMALIZER
# =============================================================================

class BaseNormalizer(ABC):
    """Abstract base normalizer."""

    def __init__(
        self,
        config: Optional[NormalizationConfig] = None,
        name: Optional[str] = None
    ):
        self.config = config or NormalizationConfig()
        self.name = name or self.__class__.__name__
        self.stats: Optional[NormalizationStats] = None
        self._fitted = False

    @abstractmethod
    def _compute_stats(self, data: List[List[float]]) -> NormalizationStats:
        """Compute statistics from data."""
        pass

    @abstractmethod
    def _transform_impl(
        self,
        data: List[List[float]],
        stats: NormalizationStats
    ) -> List[List[float]]:
        """Transform data using stats."""
        pass

    @abstractmethod
    def _inverse_impl(
        self,
        data: List[List[float]],
        stats: NormalizationStats
    ) -> List[List[float]]:
        """Inverse transform data."""
        pass

    def fit(self, data: List[List[float]]) -> 'BaseNormalizer':
        """Fit normalizer to data."""
        self.stats = self._compute_stats(data)
        self._fitted = True
        return self

    def transform(self, data: List[List[float]]) -> List[List[float]]:
        """Transform data using fitted parameters."""
        if not self._fitted:
            raise ValueError("Normalizer not fitted. Call fit() first.")
        return self._transform_impl(data, self.stats)

    def fit_transform(self, data: List[List[float]]) -> List[List[float]]:
        """Fit and transform data."""
        self.fit(data)
        return self.transform(data)

    def inverse_transform(self, data: List[List[float]]) -> List[List[float]]:
        """Inverse transform data."""
        if not self._fitted:
            raise ValueError("Normalizer not fitted.")
        return self._inverse_impl(data, self.stats)


# =============================================================================
# NORMALIZER IMPLEMENTATIONS
# =============================================================================

class ZScoreNormalizer(BaseNormalizer):
    """Z-score (standard) normalization."""

    def __init__(self, config: Optional[NormalizationConfig] = None):
        super().__init__(config, "ZScoreNormalizer")

    def _compute_stats(self, data: List[List[float]]) -> NormalizationStats:
        """Compute mean and std."""
        if not data:
            return NormalizationStats()

        n_samples = len(data)
        n_features = len(data[0])

        means = [0.0] * n_features
        for row in data:
            for j, val in enumerate(row):
                means[j] += val
        means = [m / n_samples for m in means]

        stds = [0.0] * n_features
        for row in data:
            for j, val in enumerate(row):
                stds[j] += (val - means[j]) ** 2
        stds = [math.sqrt(s / n_samples) for s in stds]

        return NormalizationStats(
            mean=means,
            std=stds,
            n_samples=n_samples,
            n_features=n_features
        )

    def _transform_impl(
        self,
        data: List[List[float]],
        stats: NormalizationStats
    ) -> List[List[float]]:
        """Apply z-score normalization."""
        result = []

        for row in data:
            new_row = []
            for j, val in enumerate(row):
                std = stats.std[j] if stats.std[j] > self.config.epsilon else 1.0
                new_val = (val - stats.mean[j]) / std
                new_row.append(new_val)
            result.append(new_row)

        return result

    def _inverse_impl(
        self,
        data: List[List[float]],
        stats: NormalizationStats
    ) -> List[List[float]]:
        """Inverse z-score normalization."""
        result = []

        for row in data:
            new_row = []
            for j, val in enumerate(row):
                std = stats.std[j] if stats.std[j] > self.config.epsilon else 1.0
                new_val = val * std + stats.mean[j]
                new_row.append(new_val)
            result.append(new_row)

        return result


class MinMaxNormalizer(BaseNormalizer):
    """Min-Max normalization."""

    def __init__(self, config: Optional[NormalizationConfig] = None):
        super().__init__(config, "MinMaxNormalizer")

    def _compute_stats(self, data: List[List[float]]) -> NormalizationStats:
        """Compute min and max."""
        if not data:
            return NormalizationStats()

        n_samples = len(data)
        n_features = len(data[0])

        mins = [float('inf')] * n_features
        maxs = [float('-inf')] * n_features

        for row in data:
            for j, val in enumerate(row):
                mins[j] = min(mins[j], val)
                maxs[j] = max(maxs[j], val)

        return NormalizationStats(
            min_val=mins,
            max_val=maxs,
            n_samples=n_samples,
            n_features=n_features
        )

    def _transform_impl(
        self,
        data: List[List[float]],
        stats: NormalizationStats
    ) -> List[List[float]]:
        """Apply min-max normalization."""
        result = []
        low, high = self.config.feature_range

        for row in data:
            new_row = []
            for j, val in enumerate(row):
                range_val = stats.max_val[j] - stats.min_val[j]
                if range_val < self.config.epsilon:
                    range_val = 1.0

                scaled = (val - stats.min_val[j]) / range_val
                new_val = scaled * (high - low) + low

                if self.config.clip:
                    new_val = max(low, min(high, new_val))

                new_row.append(new_val)
            result.append(new_row)

        return result

    def _inverse_impl(
        self,
        data: List[List[float]],
        stats: NormalizationStats
    ) -> List[List[float]]:
        """Inverse min-max normalization."""
        result = []
        low, high = self.config.feature_range

        for row in data:
            new_row = []
            for j, val in enumerate(row):
                range_val = stats.max_val[j] - stats.min_val[j]
                if range_val < self.config.epsilon:
                    range_val = 1.0

                unscaled = (val - low) / (high - low)
                new_val = unscaled * range_val + stats.min_val[j]
                new_row.append(new_val)
            result.append(new_row)

        return result


class MaxAbsNormalizer(BaseNormalizer):
    """Max absolute value normalization."""

    def __init__(self, config: Optional[NormalizationConfig] = None):
        super().__init__(config, "MaxAbsNormalizer")

    def _compute_stats(self, data: List[List[float]]) -> NormalizationStats:
        """Compute max absolute values."""
        if not data:
            return NormalizationStats()

        n_samples = len(data)
        n_features = len(data[0])

        maxabs = [0.0] * n_features

        for row in data:
            for j, val in enumerate(row):
                maxabs[j] = max(maxabs[j], abs(val))

        return NormalizationStats(
            max_val=maxabs,
            n_samples=n_samples,
            n_features=n_features
        )

    def _transform_impl(
        self,
        data: List[List[float]],
        stats: NormalizationStats
    ) -> List[List[float]]:
        """Apply max-abs normalization."""
        result = []

        for row in data:
            new_row = []
            for j, val in enumerate(row):
                maxabs = stats.max_val[j] if stats.max_val[j] > self.config.epsilon else 1.0
                new_row.append(val / maxabs)
            result.append(new_row)

        return result

    def _inverse_impl(
        self,
        data: List[List[float]],
        stats: NormalizationStats
    ) -> List[List[float]]:
        """Inverse max-abs normalization."""
        result = []

        for row in data:
            new_row = []
            for j, val in enumerate(row):
                maxabs = stats.max_val[j] if stats.max_val[j] > self.config.epsilon else 1.0
                new_row.append(val * maxabs)
            result.append(new_row)

        return result


class RobustNormalizer(BaseNormalizer):
    """Robust normalization using median and IQR."""

    def __init__(self, config: Optional[NormalizationConfig] = None):
        super().__init__(config, "RobustNormalizer")

    def _compute_stats(self, data: List[List[float]]) -> NormalizationStats:
        """Compute median and IQR."""
        if not data:
            return NormalizationStats()

        n_samples = len(data)
        n_features = len(data[0])

        medians = []
        q1s = []
        q3s = []
        iqrs = []

        for j in range(n_features):
            col = sorted([row[j] for row in data])
            n = len(col)

            median = col[n // 2] if n % 2 else (col[n // 2 - 1] + col[n // 2]) / 2

            q1_idx = n // 4
            q3_idx = 3 * n // 4

            q1 = col[q1_idx]
            q3 = col[q3_idx]
            iqr = q3 - q1

            medians.append(median)
            q1s.append(q1)
            q3s.append(q3)
            iqrs.append(iqr)

        return NormalizationStats(
            median=medians,
            q1=q1s,
            q3=q3s,
            iqr=iqrs,
            n_samples=n_samples,
            n_features=n_features
        )

    def _transform_impl(
        self,
        data: List[List[float]],
        stats: NormalizationStats
    ) -> List[List[float]]:
        """Apply robust normalization."""
        result = []

        for row in data:
            new_row = []
            for j, val in enumerate(row):
                iqr = stats.iqr[j] if stats.iqr[j] > self.config.epsilon else 1.0
                new_val = (val - stats.median[j]) / iqr
                new_row.append(new_val)
            result.append(new_row)

        return result

    def _inverse_impl(
        self,
        data: List[List[float]],
        stats: NormalizationStats
    ) -> List[List[float]]:
        """Inverse robust normalization."""
        result = []

        for row in data:
            new_row = []
            for j, val in enumerate(row):
                iqr = stats.iqr[j] if stats.iqr[j] > self.config.epsilon else 1.0
                new_val = val * iqr + stats.median[j]
                new_row.append(new_val)
            result.append(new_row)

        return result


class L1Normalizer(BaseNormalizer):
    """L1 (Manhattan) normalization - row-wise."""

    def __init__(self, config: Optional[NormalizationConfig] = None):
        super().__init__(config, "L1Normalizer")

    def _compute_stats(self, data: List[List[float]]) -> NormalizationStats:
        """No global stats needed for L1 norm."""
        return NormalizationStats(
            n_samples=len(data),
            n_features=len(data[0]) if data else 0
        )

    def _transform_impl(
        self,
        data: List[List[float]],
        stats: NormalizationStats
    ) -> List[List[float]]:
        """Apply L1 normalization."""
        result = []

        for row in data:
            norm = sum(abs(val) for val in row)
            if norm < self.config.epsilon:
                norm = 1.0
            new_row = [val / norm for val in row]
            result.append(new_row)

        return result

    def _inverse_impl(
        self,
        data: List[List[float]],
        stats: NormalizationStats
    ) -> List[List[float]]:
        """L1 normalization is not invertible."""
        return data


class L2Normalizer(BaseNormalizer):
    """L2 (Euclidean) normalization - row-wise."""

    def __init__(self, config: Optional[NormalizationConfig] = None):
        super().__init__(config, "L2Normalizer")

    def _compute_stats(self, data: List[List[float]]) -> NormalizationStats:
        """No global stats needed for L2 norm."""
        return NormalizationStats(
            n_samples=len(data),
            n_features=len(data[0]) if data else 0
        )

    def _transform_impl(
        self,
        data: List[List[float]],
        stats: NormalizationStats
    ) -> List[List[float]]:
        """Apply L2 normalization."""
        result = []

        for row in data:
            norm = math.sqrt(sum(val ** 2 for val in row))
            if norm < self.config.epsilon:
                norm = 1.0
            new_row = [val / norm for val in row]
            result.append(new_row)

        return result

    def _inverse_impl(
        self,
        data: List[List[float]],
        stats: NormalizationStats
    ) -> List[List[float]]:
        """L2 normalization is not invertible."""
        return data


class LogNormalizer(BaseNormalizer):
    """Log transformation normalization."""

    def __init__(self, config: Optional[NormalizationConfig] = None):
        super().__init__(config, "LogNormalizer")

    def _compute_stats(self, data: List[List[float]]) -> NormalizationStats:
        """No stats needed for log transform."""
        return NormalizationStats(
            n_samples=len(data),
            n_features=len(data[0]) if data else 0
        )

    def _transform_impl(
        self,
        data: List[List[float]],
        stats: NormalizationStats
    ) -> List[List[float]]:
        """Apply log transformation."""
        result = []

        for row in data:
            new_row = []
            for val in row:
                safe_val = max(self.config.epsilon, val)
                new_row.append(math.log(safe_val + 1))
            result.append(new_row)

        return result

    def _inverse_impl(
        self,
        data: List[List[float]],
        stats: NormalizationStats
    ) -> List[List[float]]:
        """Inverse log transformation."""
        result = []

        for row in data:
            new_row = [math.exp(val) - 1 for val in row]
            result.append(new_row)

        return result


# =============================================================================
# NORMALIZER ENGINE
# =============================================================================

class NormalizerEngine:
    """
    Normalization Engine for BAEL.

    Comprehensive data normalization and standardization.
    """

    def __init__(self):
        self._normalizers: Dict[str, BaseNormalizer] = {}
        self._pipelines: Dict[str, List[str]] = {}

    def create_normalizer(
        self,
        name: str,
        norm_type: NormalizationType,
        config: Optional[NormalizationConfig] = None
    ) -> BaseNormalizer:
        """Create and register normalizer."""
        if norm_type == NormalizationType.ZSCORE:
            normalizer = ZScoreNormalizer(config)
        elif norm_type == NormalizationType.MINMAX:
            normalizer = MinMaxNormalizer(config)
        elif norm_type == NormalizationType.MAXABS:
            normalizer = MaxAbsNormalizer(config)
        elif norm_type == NormalizationType.ROBUST:
            normalizer = RobustNormalizer(config)
        elif norm_type == NormalizationType.L1:
            normalizer = L1Normalizer(config)
        elif norm_type == NormalizationType.L2:
            normalizer = L2Normalizer(config)
        elif norm_type == NormalizationType.LOG:
            normalizer = LogNormalizer(config)
        else:
            normalizer = ZScoreNormalizer(config)

        self._normalizers[name] = normalizer
        return normalizer

    def get_normalizer(self, name: str) -> Optional[BaseNormalizer]:
        """Get normalizer by name."""
        return self._normalizers.get(name)

    def fit(self, name: str, data: List[List[float]]) -> bool:
        """Fit normalizer."""
        if name not in self._normalizers:
            return False
        self._normalizers[name].fit(data)
        return True

    def transform(self, name: str, data: List[List[float]]) -> List[List[float]]:
        """Transform data."""
        if name not in self._normalizers:
            return data
        return self._normalizers[name].transform(data)

    def fit_transform(
        self,
        name: str,
        data: List[List[float]]
    ) -> List[List[float]]:
        """Fit and transform data."""
        if name not in self._normalizers:
            return data
        return self._normalizers[name].fit_transform(data)

    def inverse_transform(
        self,
        name: str,
        data: List[List[float]]
    ) -> List[List[float]]:
        """Inverse transform data."""
        if name not in self._normalizers:
            return data
        return self._normalizers[name].inverse_transform(data)

    def get_stats(self, name: str) -> Optional[NormalizationStats]:
        """Get normalizer statistics."""
        if name not in self._normalizers:
            return None
        return self._normalizers[name].stats


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Normalization Engine."""
    print("=" * 70)
    print("BAEL - NORMALIZATION ENGINE DEMO")
    print("Comprehensive Data Normalization and Standardization")
    print("=" * 70)
    print()

    engine = NormalizerEngine()

    data = [
        [1.0, 100.0, 10.0],
        [2.0, 200.0, 20.0],
        [3.0, 300.0, 30.0],
        [4.0, 400.0, 40.0],
        [5.0, 500.0, 50.0]
    ]

    print(f"Original Data:")
    for row in data:
        print(f"   {row}")
    print()

    # 1. Z-Score Normalization
    print("1. Z-SCORE NORMALIZATION:")
    print("-" * 40)

    engine.create_normalizer("zscore", NormalizationType.ZSCORE)
    zscore_data = engine.fit_transform("zscore", data)

    for row in zscore_data:
        print(f"   {[round(x, 3) for x in row]}")
    print()

    # 2. Min-Max Normalization
    print("2. MIN-MAX NORMALIZATION:")
    print("-" * 40)

    engine.create_normalizer("minmax", NormalizationType.MINMAX)
    minmax_data = engine.fit_transform("minmax", data)

    for row in minmax_data:
        print(f"   {[round(x, 3) for x in row]}")
    print()

    # 3. Max-Abs Normalization
    print("3. MAX-ABS NORMALIZATION:")
    print("-" * 40)

    engine.create_normalizer("maxabs", NormalizationType.MAXABS)
    maxabs_data = engine.fit_transform("maxabs", data)

    for row in maxabs_data:
        print(f"   {[round(x, 3) for x in row]}")
    print()

    # 4. Robust Normalization
    print("4. ROBUST NORMALIZATION:")
    print("-" * 40)

    engine.create_normalizer("robust", NormalizationType.ROBUST)
    robust_data = engine.fit_transform("robust", data)

    for row in robust_data:
        print(f"   {[round(x, 3) for x in row]}")
    print()

    # 5. L1 Normalization
    print("5. L1 NORMALIZATION (row-wise):")
    print("-" * 40)

    engine.create_normalizer("l1", NormalizationType.L1)
    l1_data = engine.fit_transform("l1", data)

    for row in l1_data:
        print(f"   {[round(x, 4) for x in row]}")
    print()

    # 6. L2 Normalization
    print("6. L2 NORMALIZATION (row-wise):")
    print("-" * 40)

    engine.create_normalizer("l2", NormalizationType.L2)
    l2_data = engine.fit_transform("l2", data)

    for row in l2_data:
        norm = math.sqrt(sum(x**2 for x in row))
        print(f"   {[round(x, 4) for x in row]}  norm={round(norm, 3)}")
    print()

    # 7. Log Transformation
    print("7. LOG TRANSFORMATION:")
    print("-" * 40)

    engine.create_normalizer("log", NormalizationType.LOG)
    log_data = engine.fit_transform("log", data)

    for row in log_data:
        print(f"   {[round(x, 3) for x in row]}")
    print()

    # 8. Inverse Transform
    print("8. INVERSE TRANSFORM (min-max):")
    print("-" * 40)

    inverse_data = engine.inverse_transform("minmax", minmax_data)

    for row in inverse_data:
        print(f"   {[round(x, 1) for x in row]}")
    print()

    # 9. Statistics
    print("9. NORMALIZER STATISTICS:")
    print("-" * 40)

    zscore_stats = engine.get_stats("zscore")
    print(f"   Z-Score Mean: {[round(x, 1) for x in zscore_stats.mean]}")
    print(f"   Z-Score Std: {[round(x, 1) for x in zscore_stats.std]}")

    minmax_stats = engine.get_stats("minmax")
    print(f"   Min-Max Min: {[round(x, 1) for x in minmax_stats.min_val]}")
    print(f"   Min-Max Max: {[round(x, 1) for x in minmax_stats.max_val]}")
    print()

    # 10. Custom Range
    print("10. CUSTOM RANGE NORMALIZATION:")
    print("-" * 40)

    config = NormalizationConfig(feature_range=(-1.0, 1.0))
    engine.create_normalizer("custom_range", NormalizationType.MINMAX, config)
    custom_data = engine.fit_transform("custom_range", data)

    for row in custom_data:
        print(f"   {[round(x, 3) for x in row]}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Normalization Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
