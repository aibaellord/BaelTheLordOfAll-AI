#!/usr/bin/env python3
"""
BAEL - Regularizer Engine
Comprehensive regularization techniques for AI agents.

Features:
- L1/L2/Elastic Net regularization
- Dropout variations (standard, spatial, alpha)
- Weight decay strategies
- Data augmentation regularization
- Label smoothing
- Mixup regularization
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
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class RegularizationType(Enum):
    """Types of regularization."""
    NONE = "none"
    L1 = "l1"
    L2 = "l2"
    ELASTIC_NET = "elastic_net"
    DROPOUT = "dropout"
    SPATIAL_DROPOUT = "spatial_dropout"
    ALPHA_DROPOUT = "alpha_dropout"
    WEIGHT_DECAY = "weight_decay"
    LABEL_SMOOTHING = "label_smoothing"
    MIXUP = "mixup"
    CUTOUT = "cutout"
    MAX_NORM = "max_norm"
    SPECTRAL_NORM = "spectral_norm"


class DropoutMode(Enum):
    """Dropout modes."""
    TRAINING = "training"
    INFERENCE = "inference"


class NormType(Enum):
    """Norm types for constraint."""
    L1_NORM = "l1"
    L2_NORM = "l2"
    LINF_NORM = "linf"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class RegularizationResult:
    """Result of regularization."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    reg_type: RegularizationType = RegularizationType.NONE
    penalty: float = 0.0
    applied_to_count: int = 0


@dataclass
class DropoutResult:
    """Result of dropout application."""
    outputs: List[float] = field(default_factory=list)
    mask: List[bool] = field(default_factory=list)
    drop_rate: float = 0.0
    actual_dropped: float = 0.0


@dataclass
class RegularizationConfig:
    """Configuration for regularization."""
    reg_type: RegularizationType = RegularizationType.L2
    strength: float = 0.01
    l1_ratio: float = 0.5
    dropout_rate: float = 0.5
    label_smoothing_factor: float = 0.1
    max_norm_value: float = 1.0


@dataclass
class RegularizationStats:
    """Statistics for regularization."""
    total_penalty: float = 0.0
    applied_count: int = 0
    average_penalty: float = 0.0
    weight_magnitude: float = 0.0


# =============================================================================
# REGULARIZER BASE
# =============================================================================

class Regularizer(ABC):
    """Abstract base regularizer."""

    @abstractmethod
    def penalty(self, weights: List[float]) -> float:
        """Compute penalty."""
        pass

    @abstractmethod
    def gradient(self, weights: List[float]) -> List[float]:
        """Compute regularization gradient."""
        pass


# =============================================================================
# WEIGHT REGULARIZERS
# =============================================================================

class L1Regularizer(Regularizer):
    """L1 (Lasso) regularization."""

    def __init__(self, strength: float = 0.01):
        self._strength = strength

    def penalty(self, weights: List[float]) -> float:
        """Compute L1 penalty."""
        return self._strength * sum(abs(w) for w in weights)

    def gradient(self, weights: List[float]) -> List[float]:
        """Compute L1 gradient."""
        return [
            self._strength * (1.0 if w > 0 else -1.0 if w < 0 else 0.0)
            for w in weights
        ]


class L2Regularizer(Regularizer):
    """L2 (Ridge) regularization."""

    def __init__(self, strength: float = 0.01):
        self._strength = strength

    def penalty(self, weights: List[float]) -> float:
        """Compute L2 penalty."""
        return self._strength * sum(w ** 2 for w in weights) / 2

    def gradient(self, weights: List[float]) -> List[float]:
        """Compute L2 gradient."""
        return [self._strength * w for w in weights]


class ElasticNetRegularizer(Regularizer):
    """Elastic Net regularization (combination of L1 and L2)."""

    def __init__(self, strength: float = 0.01, l1_ratio: float = 0.5):
        self._strength = strength
        self._l1_ratio = l1_ratio
        self._l1 = L1Regularizer(strength * l1_ratio)
        self._l2 = L2Regularizer(strength * (1 - l1_ratio))

    def penalty(self, weights: List[float]) -> float:
        """Compute elastic net penalty."""
        return self._l1.penalty(weights) + self._l2.penalty(weights)

    def gradient(self, weights: List[float]) -> List[float]:
        """Compute elastic net gradient."""
        l1_grad = self._l1.gradient(weights)
        l2_grad = self._l2.gradient(weights)
        return [g1 + g2 for g1, g2 in zip(l1_grad, l2_grad)]


# =============================================================================
# DROPOUT REGULARIZERS
# =============================================================================

class Dropout:
    """Standard dropout."""

    def __init__(self, rate: float = 0.5):
        self._rate = min(max(rate, 0.0), 1.0)
        self._mode = DropoutMode.TRAINING

    def train(self) -> None:
        """Set to training mode."""
        self._mode = DropoutMode.TRAINING

    def eval(self) -> None:
        """Set to evaluation mode."""
        self._mode = DropoutMode.INFERENCE

    def apply(self, x: List[float]) -> DropoutResult:
        """Apply dropout."""
        if self._mode == DropoutMode.INFERENCE:
            return DropoutResult(
                outputs=x.copy(),
                mask=[True] * len(x),
                drop_rate=0.0,
                actual_dropped=0.0
            )

        mask = [random.random() > self._rate for _ in x]
        scale = 1.0 / (1.0 - self._rate) if self._rate < 1.0 else 0.0

        outputs = [
            val * scale if keep else 0.0
            for val, keep in zip(x, mask)
        ]

        dropped_count = sum(1 for m in mask if not m)
        actual_rate = dropped_count / len(mask) if mask else 0.0

        return DropoutResult(
            outputs=outputs,
            mask=mask,
            drop_rate=self._rate,
            actual_dropped=actual_rate
        )


class SpatialDropout:
    """Spatial dropout (drops entire channels)."""

    def __init__(self, rate: float = 0.5):
        self._rate = min(max(rate, 0.0), 1.0)
        self._mode = DropoutMode.TRAINING

    def train(self) -> None:
        self._mode = DropoutMode.TRAINING

    def eval(self) -> None:
        self._mode = DropoutMode.INFERENCE

    def apply(
        self,
        x: List[List[float]],
        channel_axis: int = 0
    ) -> Tuple[List[List[float]], List[bool]]:
        """Apply spatial dropout to channels."""
        if self._mode == DropoutMode.INFERENCE:
            return x, [True] * len(x)

        num_channels = len(x)
        channel_mask = [random.random() > self._rate for _ in range(num_channels)]
        scale = 1.0 / (1.0 - self._rate) if self._rate < 1.0 else 0.0

        outputs = []
        for i, channel in enumerate(x):
            if channel_mask[i]:
                outputs.append([v * scale for v in channel])
            else:
                outputs.append([0.0] * len(channel))

        return outputs, channel_mask


class AlphaDropout:
    """Alpha dropout for SELU networks."""

    def __init__(self, rate: float = 0.5):
        self._rate = min(max(rate, 0.0), 1.0)
        self._mode = DropoutMode.TRAINING
        self._alpha = -1.7580993408473766
        self._scale = 1.0507009873554805

        self._a = ((1 - self._rate) * (1 + self._rate * self._alpha ** 2)) ** -0.5
        self._b = -self._a * self._alpha * self._rate

    def train(self) -> None:
        self._mode = DropoutMode.TRAINING

    def eval(self) -> None:
        self._mode = DropoutMode.INFERENCE

    def apply(self, x: List[float]) -> List[float]:
        """Apply alpha dropout."""
        if self._mode == DropoutMode.INFERENCE:
            return x.copy()

        outputs = []
        for val in x:
            if random.random() > self._rate:
                outputs.append(self._a * val + self._b)
            else:
                outputs.append(self._a * self._alpha + self._b)

        return outputs


# =============================================================================
# WEIGHT CONSTRAINTS
# =============================================================================

class MaxNormConstraint:
    """Max norm constraint on weights."""

    def __init__(self, max_value: float = 2.0, axis: int = 0):
        self._max_value = max_value
        self._axis = axis

    def apply(self, weights: List[float]) -> List[float]:
        """Apply max norm constraint."""
        norm = math.sqrt(sum(w ** 2 for w in weights))

        if norm > self._max_value:
            scale = self._max_value / norm
            return [w * scale for w in weights]

        return weights.copy()


class UnitNormConstraint:
    """Unit norm constraint."""

    def apply(self, weights: List[float]) -> List[float]:
        """Normalize weights to unit norm."""
        norm = math.sqrt(sum(w ** 2 for w in weights))

        if norm > 0:
            return [w / norm for w in weights]

        return weights.copy()


class MinMaxNormConstraint:
    """Min-max norm constraint."""

    def __init__(
        self,
        min_value: float = 0.0,
        max_value: float = 1.0,
        rate: float = 1.0
    ):
        self._min_value = min_value
        self._max_value = max_value
        self._rate = rate

    def apply(self, weights: List[float]) -> List[float]:
        """Apply min-max norm constraint."""
        norm = math.sqrt(sum(w ** 2 for w in weights))

        desired_norm = max(self._min_value, min(self._max_value, norm))

        if norm > 0:
            scale = desired_norm / norm
            blended_scale = 1.0 + self._rate * (scale - 1.0)
            return [w * blended_scale for w in weights]

        return weights.copy()


# =============================================================================
# LABEL REGULARIZATION
# =============================================================================

class LabelSmoother:
    """Label smoothing regularization."""

    def __init__(self, smoothing: float = 0.1):
        self._smoothing = min(max(smoothing, 0.0), 1.0)

    def smooth(
        self,
        labels: List[float],
        num_classes: int
    ) -> List[float]:
        """Apply label smoothing."""
        confidence = 1.0 - self._smoothing
        low_value = self._smoothing / num_classes

        return [
            confidence * l + low_value
            for l in labels
        ]

    def smooth_one_hot(
        self,
        target_class: int,
        num_classes: int
    ) -> List[float]:
        """Create smoothed one-hot vector."""
        confidence = 1.0 - self._smoothing
        low_value = self._smoothing / num_classes

        smoothed = [low_value] * num_classes
        smoothed[target_class] = confidence + low_value

        return smoothed


# =============================================================================
# DATA REGULARIZATION
# =============================================================================

class Mixup:
    """Mixup data augmentation."""

    def __init__(self, alpha: float = 0.2):
        self._alpha = alpha

    def _beta_sample(self) -> float:
        """Sample from beta distribution (approximation)."""
        if self._alpha <= 0:
            return 0.0

        u = random.random()
        v = random.random()

        x = u ** (1.0 / self._alpha)
        y = v ** (1.0 / self._alpha)

        return x / (x + y)

    def mix(
        self,
        x1: List[float],
        y1: List[float],
        x2: List[float],
        y2: List[float]
    ) -> Tuple[List[float], List[float], float]:
        """Mix two samples."""
        lam = self._beta_sample()

        mixed_x = [
            lam * a + (1 - lam) * b
            for a, b in zip(x1, x2)
        ]

        mixed_y = [
            lam * a + (1 - lam) * b
            for a, b in zip(y1, y2)
        ]

        return mixed_x, mixed_y, lam


class Cutout:
    """Cutout regularization."""

    def __init__(self, n_holes: int = 1, length: int = 8):
        self._n_holes = n_holes
        self._length = length

    def apply(self, x: List[float]) -> Tuple[List[float], List[Tuple[int, int]]]:
        """Apply cutout."""
        output = x.copy()
        holes = []

        for _ in range(self._n_holes):
            center = random.randint(0, len(x) - 1)
            start = max(0, center - self._length // 2)
            end = min(len(x), center + self._length // 2)

            for i in range(start, end):
                output[i] = 0.0

            holes.append((start, end))

        return output, holes


class CutMix:
    """CutMix data augmentation."""

    def __init__(self, alpha: float = 1.0):
        self._alpha = alpha

    def _beta_sample(self) -> float:
        """Sample from beta distribution."""
        if self._alpha <= 0:
            return 0.5

        u = random.random()
        v = random.random()

        x = u ** (1.0 / self._alpha)
        y = v ** (1.0 / self._alpha)

        return x / (x + y)

    def apply(
        self,
        x1: List[float],
        y1: List[float],
        x2: List[float],
        y2: List[float]
    ) -> Tuple[List[float], List[float], float]:
        """Apply CutMix."""
        lam = self._beta_sample()

        cut_length = int(len(x1) * (1 - lam))
        cut_start = random.randint(0, len(x1) - cut_length)
        cut_end = cut_start + cut_length

        output = x1.copy()
        for i in range(cut_start, cut_end):
            if i < len(x2):
                output[i] = x2[i]

        actual_lam = 1 - (cut_end - cut_start) / len(x1)

        mixed_y = [
            actual_lam * a + (1 - actual_lam) * b
            for a, b in zip(y1, y2)
        ]

        return output, mixed_y, actual_lam


# =============================================================================
# NOISE REGULARIZATION
# =============================================================================

class GaussianNoise:
    """Gaussian noise injection."""

    def __init__(self, stddev: float = 0.1):
        self._stddev = stddev
        self._training = True

    def train(self) -> None:
        self._training = True

    def eval(self) -> None:
        self._training = False

    def apply(self, x: List[float]) -> List[float]:
        """Apply Gaussian noise."""
        if not self._training:
            return x.copy()

        return [
            val + random.gauss(0, self._stddev)
            for val in x
        ]


class WeightNoise:
    """Weight noise regularization."""

    def __init__(self, stddev: float = 0.05):
        self._stddev = stddev

    def apply(self, weights: List[float]) -> List[float]:
        """Add noise to weights."""
        return [
            w + random.gauss(0, self._stddev)
            for w in weights
        ]


# =============================================================================
# REGULARIZER ENGINE
# =============================================================================

class RegularizerEngine:
    """
    Regularizer Engine for BAEL.

    Comprehensive regularization techniques for AI agents.
    """

    def __init__(self):
        self._regularizers: Dict[str, Regularizer] = {}
        self._dropouts: Dict[str, Dropout] = {}
        self._constraints: Dict[str, MaxNormConstraint] = {}
        self._label_smoother = LabelSmoother()
        self._mixup = Mixup()
        self._cutout = Cutout()
        self._cutmix = CutMix()
        self._gaussian_noise = GaussianNoise()
        self._stats: Dict[str, RegularizationStats] = defaultdict(RegularizationStats)

    def create_regularizer(
        self,
        reg_type: RegularizationType,
        strength: float = 0.01,
        l1_ratio: float = 0.5
    ) -> Optional[Regularizer]:
        """Create regularizer."""
        if reg_type == RegularizationType.L1:
            return L1Regularizer(strength)
        elif reg_type == RegularizationType.L2:
            return L2Regularizer(strength)
        elif reg_type == RegularizationType.ELASTIC_NET:
            return ElasticNetRegularizer(strength, l1_ratio)
        return None

    def add_regularizer(self, name: str, regularizer: Regularizer) -> None:
        """Add named regularizer."""
        self._regularizers[name] = regularizer

    def compute_penalty(
        self,
        weights: List[float],
        reg_type: RegularizationType,
        strength: float = 0.01
    ) -> float:
        """Compute regularization penalty."""
        reg = self.create_regularizer(reg_type, strength)
        if reg:
            return reg.penalty(weights)
        return 0.0

    def compute_gradient(
        self,
        weights: List[float],
        reg_type: RegularizationType,
        strength: float = 0.01
    ) -> List[float]:
        """Compute regularization gradient."""
        reg = self.create_regularizer(reg_type, strength)
        if reg:
            return reg.gradient(weights)
        return [0.0] * len(weights)

    def create_dropout(
        self,
        name: str,
        rate: float = 0.5
    ) -> Dropout:
        """Create and store dropout."""
        dropout = Dropout(rate)
        self._dropouts[name] = dropout
        return dropout

    def apply_dropout(
        self,
        x: List[float],
        rate: float = 0.5,
        training: bool = True
    ) -> DropoutResult:
        """Apply dropout."""
        dropout = Dropout(rate)
        if training:
            dropout.train()
        else:
            dropout.eval()
        return dropout.apply(x)

    def apply_constraint(
        self,
        weights: List[float],
        max_value: float = 2.0
    ) -> List[float]:
        """Apply max norm constraint."""
        constraint = MaxNormConstraint(max_value)
        return constraint.apply(weights)

    def smooth_labels(
        self,
        labels: List[float],
        num_classes: int,
        smoothing: float = 0.1
    ) -> List[float]:
        """Apply label smoothing."""
        self._label_smoother._smoothing = smoothing
        return self._label_smoother.smooth(labels, num_classes)

    def mixup(
        self,
        x1: List[float],
        y1: List[float],
        x2: List[float],
        y2: List[float],
        alpha: float = 0.2
    ) -> Tuple[List[float], List[float], float]:
        """Apply mixup."""
        self._mixup._alpha = alpha
        return self._mixup.mix(x1, y1, x2, y2)

    def cutout(
        self,
        x: List[float],
        n_holes: int = 1,
        length: int = 8
    ) -> Tuple[List[float], List[Tuple[int, int]]]:
        """Apply cutout."""
        self._cutout._n_holes = n_holes
        self._cutout._length = length
        return self._cutout.apply(x)

    def cutmix(
        self,
        x1: List[float],
        y1: List[float],
        x2: List[float],
        y2: List[float],
        alpha: float = 1.0
    ) -> Tuple[List[float], List[float], float]:
        """Apply CutMix."""
        self._cutmix._alpha = alpha
        return self._cutmix.apply(x1, y1, x2, y2)

    def add_noise(
        self,
        x: List[float],
        stddev: float = 0.1,
        training: bool = True
    ) -> List[float]:
        """Add Gaussian noise."""
        self._gaussian_noise._stddev = stddev
        if training:
            self._gaussian_noise.train()
        else:
            self._gaussian_noise.eval()
        return self._gaussian_noise.apply(x)

    def train_mode(self) -> None:
        """Set all dropouts to training mode."""
        for dropout in self._dropouts.values():
            dropout.train()

    def eval_mode(self) -> None:
        """Set all dropouts to evaluation mode."""
        for dropout in self._dropouts.values():
            dropout.eval()


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Regularizer Engine."""
    print("=" * 70)
    print("BAEL - REGULARIZER ENGINE DEMO")
    print("Comprehensive Regularization Techniques for AI Agents")
    print("=" * 70)
    print()

    engine = RegularizerEngine()

    weights = [0.5, -0.3, 0.8, -0.2, 0.1, -0.6, 0.4, -0.7]

    # 1. L1 Regularization
    print("1. L1 REGULARIZATION:")
    print("-" * 40)

    penalty = engine.compute_penalty(weights, RegularizationType.L1, strength=0.01)
    gradient = engine.compute_gradient(weights, RegularizationType.L1, strength=0.01)

    print(f"   Weights: {[f'{w:.2f}' for w in weights]}")
    print(f"   Penalty: {penalty:.4f}")
    print(f"   Gradient: {[f'{g:.3f}' for g in gradient]}")
    print()

    # 2. L2 Regularization
    print("2. L2 REGULARIZATION:")
    print("-" * 40)

    penalty = engine.compute_penalty(weights, RegularizationType.L2, strength=0.01)
    gradient = engine.compute_gradient(weights, RegularizationType.L2, strength=0.01)

    print(f"   Penalty: {penalty:.4f}")
    print(f"   Gradient: {[f'{g:.3f}' for g in gradient]}")
    print()

    # 3. Elastic Net
    print("3. ELASTIC NET REGULARIZATION:")
    print("-" * 40)

    penalty = engine.compute_penalty(weights, RegularizationType.ELASTIC_NET, strength=0.01)
    gradient = engine.compute_gradient(weights, RegularizationType.ELASTIC_NET, strength=0.01)

    print(f"   Penalty: {penalty:.4f}")
    print(f"   Gradient: {[f'{g:.3f}' for g in gradient]}")
    print()

    # 4. Dropout
    print("4. DROPOUT:")
    print("-" * 40)

    inputs = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]

    for rate in [0.2, 0.5, 0.8]:
        result = engine.apply_dropout(inputs, rate=rate, training=True)
        print(f"   Rate {rate}: {[f'{o:.2f}' for o in result.outputs]}")
        print(f"      Actual dropped: {result.actual_dropped:.2%}")
    print()

    # 5. Dropout Inference Mode
    print("5. DROPOUT (INFERENCE MODE):")
    print("-" * 40)

    result = engine.apply_dropout(inputs, rate=0.5, training=False)
    print(f"   Input:  {[f'{i:.2f}' for i in inputs]}")
    print(f"   Output: {[f'{o:.2f}' for o in result.outputs]}")
    print()

    # 6. Max Norm Constraint
    print("6. MAX NORM CONSTRAINT:")
    print("-" * 40)

    large_weights = [w * 10 for w in weights]
    original_norm = math.sqrt(sum(w ** 2 for w in large_weights))

    constrained = engine.apply_constraint(large_weights, max_value=2.0)
    constrained_norm = math.sqrt(sum(w ** 2 for w in constrained))

    print(f"   Original norm: {original_norm:.4f}")
    print(f"   Constrained norm: {constrained_norm:.4f}")
    print(f"   Max value: 2.0")
    print()

    # 7. Label Smoothing
    print("7. LABEL SMOOTHING:")
    print("-" * 40)

    one_hot = [0.0, 0.0, 1.0, 0.0, 0.0]

    for smoothing in [0.0, 0.1, 0.2]:
        smoothed = engine.smooth_labels(one_hot, num_classes=5, smoothing=smoothing)
        print(f"   Smoothing {smoothing}: {[f'{l:.3f}' for l in smoothed]}")
    print()

    # 8. Mixup
    print("8. MIXUP:")
    print("-" * 40)

    x1 = [1.0, 2.0, 3.0, 4.0]
    y1 = [1.0, 0.0, 0.0]
    x2 = [5.0, 6.0, 7.0, 8.0]
    y2 = [0.0, 1.0, 0.0]

    mixed_x, mixed_y, lam = engine.mixup(x1, y1, x2, y2, alpha=0.4)

    print(f"   X1: {x1}, Y1: {y1}")
    print(f"   X2: {x2}, Y2: {y2}")
    print(f"   Lambda: {lam:.3f}")
    print(f"   Mixed X: {[f'{v:.2f}' for v in mixed_x]}")
    print(f"   Mixed Y: {[f'{v:.2f}' for v in mixed_y]}")
    print()

    # 9. Cutout
    print("9. CUTOUT:")
    print("-" * 40)

    data = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    cutout_data, holes = engine.cutout(data, n_holes=1, length=4)

    print(f"   Original: {[f'{d:.0f}' for d in data]}")
    print(f"   Cutout:   {[f'{d:.0f}' for d in cutout_data]}")
    print(f"   Holes: {holes}")
    print()

    # 10. Gaussian Noise
    print("10. GAUSSIAN NOISE:")
    print("-" * 40)

    clean = [1.0, 1.0, 1.0, 1.0, 1.0]

    for stddev in [0.05, 0.1, 0.2]:
        noisy = engine.add_noise(clean, stddev=stddev, training=True)
        print(f"   Stddev {stddev}: {[f'{n:.3f}' for n in noisy]}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Regularizer Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
