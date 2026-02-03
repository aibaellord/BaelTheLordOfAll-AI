#!/usr/bin/env python3
"""
BAEL - Loss Manager
Comprehensive loss function management for AI agents.

Features:
- Regression losses
- Classification losses
- Custom losses
- Loss weighting
- Multi-task losses
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

class LossType(Enum):
    """Loss function types."""
    MSE = "mse"
    MAE = "mae"
    RMSE = "rmse"
    HUBER = "huber"
    LOG_COSH = "log_cosh"
    CROSS_ENTROPY = "cross_entropy"
    BINARY_CROSS_ENTROPY = "binary_cross_entropy"
    FOCAL = "focal"
    HINGE = "hinge"
    KL_DIVERGENCE = "kl_divergence"
    COSINE = "cosine"
    CONTRASTIVE = "contrastive"
    TRIPLET = "triplet"


class ReductionType(Enum):
    """Reduction types for losses."""
    NONE = "none"
    MEAN = "mean"
    SUM = "sum"


class LossStatus(Enum):
    """Loss computation status."""
    COMPUTED = "computed"
    CACHED = "cached"
    AGGREGATED = "aggregated"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class LossValue:
    """A computed loss value."""
    loss_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    value: float = 0.0
    loss_type: LossType = LossType.MSE
    status: LossStatus = LossStatus.COMPUTED
    batch_size: int = 0


@dataclass
class MultiLoss:
    """Multiple loss values with weights."""
    losses: Dict[str, float] = field(default_factory=dict)
    weights: Dict[str, float] = field(default_factory=dict)
    total: float = 0.0


@dataclass
class LossStats:
    """Loss statistics."""
    mean: float = 0.0
    min_val: float = 0.0
    max_val: float = 0.0
    std: float = 0.0
    count: int = 0


@dataclass
class LossHistory:
    """Loss history for tracking."""
    history_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    values: List[float] = field(default_factory=list)
    epochs: List[int] = field(default_factory=list)


# =============================================================================
# LOSS FUNCTION BASE
# =============================================================================

class LossFunction(ABC):
    """Abstract base loss function."""

    @abstractmethod
    def compute(
        self,
        predictions: List[float],
        targets: List[float]
    ) -> float:
        """Compute loss."""
        pass

    @abstractmethod
    def gradient(
        self,
        predictions: List[float],
        targets: List[float]
    ) -> List[float]:
        """Compute gradient of loss."""
        pass


# =============================================================================
# REGRESSION LOSSES
# =============================================================================

class MSELoss(LossFunction):
    """Mean Squared Error loss."""

    def __init__(self, reduction: ReductionType = ReductionType.MEAN):
        self._reduction = reduction

    def compute(
        self,
        predictions: List[float],
        targets: List[float]
    ) -> float:
        """Compute MSE."""
        if len(predictions) != len(targets) or not predictions:
            return 0.0

        losses = [(p - t) ** 2 for p, t in zip(predictions, targets)]

        if self._reduction == ReductionType.MEAN:
            return sum(losses) / len(losses)
        elif self._reduction == ReductionType.SUM:
            return sum(losses)
        return sum(losses) / len(losses)

    def gradient(
        self,
        predictions: List[float],
        targets: List[float]
    ) -> List[float]:
        """Compute MSE gradient."""
        n = len(predictions)
        if n == 0:
            return []

        if self._reduction == ReductionType.MEAN:
            return [2 * (p - t) / n for p, t in zip(predictions, targets)]
        return [2 * (p - t) for p, t in zip(predictions, targets)]


class MAELoss(LossFunction):
    """Mean Absolute Error loss."""

    def __init__(self, reduction: ReductionType = ReductionType.MEAN):
        self._reduction = reduction

    def compute(
        self,
        predictions: List[float],
        targets: List[float]
    ) -> float:
        """Compute MAE."""
        if len(predictions) != len(targets) or not predictions:
            return 0.0

        losses = [abs(p - t) for p, t in zip(predictions, targets)]

        if self._reduction == ReductionType.MEAN:
            return sum(losses) / len(losses)
        elif self._reduction == ReductionType.SUM:
            return sum(losses)
        return sum(losses) / len(losses)

    def gradient(
        self,
        predictions: List[float],
        targets: List[float]
    ) -> List[float]:
        """Compute MAE gradient."""
        n = len(predictions)
        grads = []

        for p, t in zip(predictions, targets):
            if p > t:
                g = 1.0
            elif p < t:
                g = -1.0
            else:
                g = 0.0

            if self._reduction == ReductionType.MEAN:
                g /= n

            grads.append(g)

        return grads


class HuberLoss(LossFunction):
    """Huber loss (smooth L1)."""

    def __init__(
        self,
        delta: float = 1.0,
        reduction: ReductionType = ReductionType.MEAN
    ):
        self._delta = delta
        self._reduction = reduction

    def compute(
        self,
        predictions: List[float],
        targets: List[float]
    ) -> float:
        """Compute Huber loss."""
        if len(predictions) != len(targets) or not predictions:
            return 0.0

        losses = []
        for p, t in zip(predictions, targets):
            error = abs(p - t)
            if error <= self._delta:
                losses.append(0.5 * error ** 2)
            else:
                losses.append(self._delta * error - 0.5 * self._delta ** 2)

        if self._reduction == ReductionType.MEAN:
            return sum(losses) / len(losses)
        elif self._reduction == ReductionType.SUM:
            return sum(losses)
        return sum(losses) / len(losses)

    def gradient(
        self,
        predictions: List[float],
        targets: List[float]
    ) -> List[float]:
        """Compute Huber gradient."""
        n = len(predictions)
        grads = []

        for p, t in zip(predictions, targets):
            error = p - t
            if abs(error) <= self._delta:
                g = error
            else:
                g = self._delta if error > 0 else -self._delta

            if self._reduction == ReductionType.MEAN:
                g /= n

            grads.append(g)

        return grads


class LogCoshLoss(LossFunction):
    """Log-Cosh loss."""

    def __init__(self, reduction: ReductionType = ReductionType.MEAN):
        self._reduction = reduction

    def compute(
        self,
        predictions: List[float],
        targets: List[float]
    ) -> float:
        """Compute Log-Cosh loss."""
        if len(predictions) != len(targets) or not predictions:
            return 0.0

        losses = []
        for p, t in zip(predictions, targets):
            x = p - t
            x = max(-500, min(500, x))
            losses.append(math.log(math.cosh(x)))

        if self._reduction == ReductionType.MEAN:
            return sum(losses) / len(losses)
        elif self._reduction == ReductionType.SUM:
            return sum(losses)
        return sum(losses) / len(losses)

    def gradient(
        self,
        predictions: List[float],
        targets: List[float]
    ) -> List[float]:
        """Compute Log-Cosh gradient."""
        n = len(predictions)
        grads = []

        for p, t in zip(predictions, targets):
            g = math.tanh(p - t)
            if self._reduction == ReductionType.MEAN:
                g /= n
            grads.append(g)

        return grads


# =============================================================================
# CLASSIFICATION LOSSES
# =============================================================================

class BinaryCrossEntropyLoss(LossFunction):
    """Binary Cross Entropy loss."""

    def __init__(
        self,
        epsilon: float = 1e-15,
        reduction: ReductionType = ReductionType.MEAN
    ):
        self._epsilon = epsilon
        self._reduction = reduction

    def compute(
        self,
        predictions: List[float],
        targets: List[float]
    ) -> float:
        """Compute BCE."""
        if len(predictions) != len(targets) or not predictions:
            return 0.0

        losses = []
        for p, t in zip(predictions, targets):
            p = max(self._epsilon, min(1 - self._epsilon, p))
            loss = -t * math.log(p) - (1 - t) * math.log(1 - p)
            losses.append(loss)

        if self._reduction == ReductionType.MEAN:
            return sum(losses) / len(losses)
        elif self._reduction == ReductionType.SUM:
            return sum(losses)
        return sum(losses) / len(losses)

    def gradient(
        self,
        predictions: List[float],
        targets: List[float]
    ) -> List[float]:
        """Compute BCE gradient."""
        n = len(predictions)
        grads = []

        for p, t in zip(predictions, targets):
            p = max(self._epsilon, min(1 - self._epsilon, p))
            g = (p - t) / (p * (1 - p))

            if self._reduction == ReductionType.MEAN:
                g /= n

            grads.append(g)

        return grads


class CrossEntropyLoss(LossFunction):
    """Cross Entropy loss for multi-class."""

    def __init__(
        self,
        epsilon: float = 1e-15,
        reduction: ReductionType = ReductionType.MEAN
    ):
        self._epsilon = epsilon
        self._reduction = reduction

    def compute(
        self,
        predictions: List[float],
        targets: List[float]
    ) -> float:
        """Compute cross entropy."""
        if len(predictions) != len(targets) or not predictions:
            return 0.0

        total = 0.0
        for p, t in zip(predictions, targets):
            if t > 0:
                p = max(self._epsilon, p)
                total += t * math.log(p)

        return -total

    def gradient(
        self,
        predictions: List[float],
        targets: List[float]
    ) -> List[float]:
        """Compute cross entropy gradient."""
        grads = []

        for p, t in zip(predictions, targets):
            p = max(self._epsilon, p)
            g = -t / p
            grads.append(g)

        return grads


class FocalLoss(LossFunction):
    """Focal loss for imbalanced classification."""

    def __init__(
        self,
        gamma: float = 2.0,
        alpha: float = 0.25,
        epsilon: float = 1e-15,
        reduction: ReductionType = ReductionType.MEAN
    ):
        self._gamma = gamma
        self._alpha = alpha
        self._epsilon = epsilon
        self._reduction = reduction

    def compute(
        self,
        predictions: List[float],
        targets: List[float]
    ) -> float:
        """Compute focal loss."""
        if len(predictions) != len(targets) or not predictions:
            return 0.0

        losses = []
        for p, t in zip(predictions, targets):
            p = max(self._epsilon, min(1 - self._epsilon, p))

            if t == 1:
                loss = -self._alpha * ((1 - p) ** self._gamma) * math.log(p)
            else:
                loss = -(1 - self._alpha) * (p ** self._gamma) * math.log(1 - p)

            losses.append(loss)

        if self._reduction == ReductionType.MEAN:
            return sum(losses) / len(losses)
        elif self._reduction == ReductionType.SUM:
            return sum(losses)
        return sum(losses) / len(losses)

    def gradient(
        self,
        predictions: List[float],
        targets: List[float]
    ) -> List[float]:
        """Compute focal loss gradient (simplified)."""
        n = len(predictions)
        grads = []

        for p, t in zip(predictions, targets):
            p = max(self._epsilon, min(1 - self._epsilon, p))

            if t == 1:
                g = self._alpha * (1 - p) ** (self._gamma - 1) * (
                    self._gamma * p * math.log(p) + p - 1
                )
            else:
                g = (1 - self._alpha) * p ** (self._gamma - 1) * (
                    -self._gamma * (1 - p) * math.log(1 - p) + p
                )

            if self._reduction == ReductionType.MEAN:
                g /= n

            grads.append(g)

        return grads


class HingeLoss(LossFunction):
    """Hinge loss for SVM."""

    def __init__(self, reduction: ReductionType = ReductionType.MEAN):
        self._reduction = reduction

    def compute(
        self,
        predictions: List[float],
        targets: List[float]
    ) -> float:
        """Compute hinge loss."""
        if len(predictions) != len(targets) or not predictions:
            return 0.0

        losses = [max(0, 1 - t * p) for p, t in zip(predictions, targets)]

        if self._reduction == ReductionType.MEAN:
            return sum(losses) / len(losses)
        elif self._reduction == ReductionType.SUM:
            return sum(losses)
        return sum(losses) / len(losses)

    def gradient(
        self,
        predictions: List[float],
        targets: List[float]
    ) -> List[float]:
        """Compute hinge gradient."""
        n = len(predictions)
        grads = []

        for p, t in zip(predictions, targets):
            if 1 - t * p > 0:
                g = -t
            else:
                g = 0

            if self._reduction == ReductionType.MEAN:
                g /= n

            grads.append(g)

        return grads


# =============================================================================
# SPECIALIZED LOSSES
# =============================================================================

class KLDivergenceLoss(LossFunction):
    """KL Divergence loss."""

    def __init__(
        self,
        epsilon: float = 1e-15,
        reduction: ReductionType = ReductionType.MEAN
    ):
        self._epsilon = epsilon
        self._reduction = reduction

    def compute(
        self,
        predictions: List[float],
        targets: List[float]
    ) -> float:
        """Compute KL divergence."""
        if len(predictions) != len(targets) or not predictions:
            return 0.0

        total = 0.0
        for p, t in zip(predictions, targets):
            if t > 0:
                p = max(self._epsilon, p)
                t = max(self._epsilon, t)
                total += t * math.log(t / p)

        return total

    def gradient(
        self,
        predictions: List[float],
        targets: List[float]
    ) -> List[float]:
        """Compute KL gradient."""
        grads = []

        for p, t in zip(predictions, targets):
            p = max(self._epsilon, p)
            g = -t / p
            grads.append(g)

        return grads


class CosineSimilarityLoss(LossFunction):
    """Cosine similarity loss."""

    def __init__(self, reduction: ReductionType = ReductionType.MEAN):
        self._reduction = reduction

    def compute(
        self,
        predictions: List[float],
        targets: List[float]
    ) -> float:
        """Compute cosine loss."""
        if len(predictions) != len(targets) or not predictions:
            return 0.0

        dot = sum(p * t for p, t in zip(predictions, targets))
        norm_p = math.sqrt(sum(p ** 2 for p in predictions))
        norm_t = math.sqrt(sum(t ** 2 for t in targets))

        if norm_p == 0 or norm_t == 0:
            return 1.0

        return 1 - dot / (norm_p * norm_t)

    def gradient(
        self,
        predictions: List[float],
        targets: List[float]
    ) -> List[float]:
        """Compute cosine gradient (simplified)."""
        dot = sum(p * t for p, t in zip(predictions, targets))
        norm_p = math.sqrt(sum(p ** 2 for p in predictions))
        norm_t = math.sqrt(sum(t ** 2 for t in targets))

        if norm_p == 0 or norm_t == 0:
            return [0.0] * len(predictions)

        grads = []
        for p, t in zip(predictions, targets):
            g = (dot * p / (norm_p ** 2) - t) / (norm_p * norm_t)
            grads.append(g)

        return grads


# =============================================================================
# LOSS AGGREGATOR
# =============================================================================

class LossAggregator:
    """Aggregate multiple losses."""

    def __init__(self):
        self._losses: Dict[str, LossFunction] = {}
        self._weights: Dict[str, float] = {}

    def add_loss(
        self,
        name: str,
        loss_fn: LossFunction,
        weight: float = 1.0
    ) -> None:
        """Add a loss function."""
        self._losses[name] = loss_fn
        self._weights[name] = weight

    def compute(
        self,
        predictions_dict: Dict[str, List[float]],
        targets_dict: Dict[str, List[float]]
    ) -> MultiLoss:
        """Compute aggregated loss."""
        losses = {}
        total = 0.0

        for name, loss_fn in self._losses.items():
            if name in predictions_dict and name in targets_dict:
                loss = loss_fn.compute(predictions_dict[name], targets_dict[name])
                losses[name] = loss
                total += self._weights[name] * loss

        return MultiLoss(
            losses=losses,
            weights=self._weights.copy(),
            total=total
        )


# =============================================================================
# LOSS MANAGER
# =============================================================================

class LossManager:
    """
    Loss Manager for BAEL.

    Comprehensive loss function management for AI agents.
    """

    def __init__(self):
        self._losses: Dict[str, LossFunction] = {}
        self._history: Dict[str, LossHistory] = {}
        self._aggregator = LossAggregator()

    def create_loss(
        self,
        name: str,
        loss_type: LossType,
        **kwargs
    ) -> LossFunction:
        """Create a loss function."""
        if loss_type == LossType.MSE:
            loss = MSELoss(**kwargs)
        elif loss_type == LossType.MAE:
            loss = MAELoss(**kwargs)
        elif loss_type == LossType.HUBER:
            loss = HuberLoss(**kwargs)
        elif loss_type == LossType.LOG_COSH:
            loss = LogCoshLoss(**kwargs)
        elif loss_type == LossType.BINARY_CROSS_ENTROPY:
            loss = BinaryCrossEntropyLoss(**kwargs)
        elif loss_type == LossType.CROSS_ENTROPY:
            loss = CrossEntropyLoss(**kwargs)
        elif loss_type == LossType.FOCAL:
            loss = FocalLoss(**kwargs)
        elif loss_type == LossType.HINGE:
            loss = HingeLoss(**kwargs)
        elif loss_type == LossType.KL_DIVERGENCE:
            loss = KLDivergenceLoss(**kwargs)
        elif loss_type == LossType.COSINE:
            loss = CosineSimilarityLoss(**kwargs)
        else:
            loss = MSELoss(**kwargs)

        self._losses[name] = loss
        return loss

    def compute(
        self,
        name: str,
        predictions: List[float],
        targets: List[float]
    ) -> float:
        """Compute loss."""
        if name not in self._losses:
            return 0.0
        return self._losses[name].compute(predictions, targets)

    def gradient(
        self,
        name: str,
        predictions: List[float],
        targets: List[float]
    ) -> List[float]:
        """Compute loss gradient."""
        if name not in self._losses:
            return []
        return self._losses[name].gradient(predictions, targets)

    def add_multi_loss(
        self,
        name: str,
        loss_type: LossType,
        weight: float = 1.0,
        **kwargs
    ) -> None:
        """Add loss to multi-task aggregator."""
        loss = self.create_loss(name, loss_type, **kwargs)
        self._aggregator.add_loss(name, loss, weight)

    def compute_multi(
        self,
        predictions_dict: Dict[str, List[float]],
        targets_dict: Dict[str, List[float]]
    ) -> MultiLoss:
        """Compute multi-task loss."""
        return self._aggregator.compute(predictions_dict, targets_dict)

    def record(self, name: str, value: float, epoch: int) -> None:
        """Record loss value."""
        if name not in self._history:
            self._history[name] = LossHistory()

        self._history[name].values.append(value)
        self._history[name].epochs.append(epoch)

    def get_stats(self, name: str) -> Optional[LossStats]:
        """Get loss statistics."""
        if name not in self._history or not self._history[name].values:
            return None

        values = self._history[name].values
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)

        return LossStats(
            mean=mean,
            min_val=min(values),
            max_val=max(values),
            std=math.sqrt(variance),
            count=len(values)
        )


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Loss Manager."""
    print("=" * 70)
    print("BAEL - LOSS MANAGER DEMO")
    print("Comprehensive Loss Function Management for AI Agents")
    print("=" * 70)
    print()

    manager = LossManager()

    predictions = [0.9, 0.1, 0.7, 0.8, 0.2]
    targets = [1.0, 0.0, 1.0, 1.0, 0.0]

    # 1. Regression Losses
    print("1. REGRESSION LOSSES:")
    print("-" * 40)

    reg_preds = [1.1, 2.3, 3.0, 4.2, 5.5]
    reg_targets = [1.0, 2.0, 3.0, 4.0, 5.0]

    manager.create_loss("mse", LossType.MSE)
    manager.create_loss("mae", LossType.MAE)
    manager.create_loss("huber", LossType.HUBER, delta=1.0)
    manager.create_loss("log_cosh", LossType.LOG_COSH)

    for name in ["mse", "mae", "huber", "log_cosh"]:
        loss = manager.compute(name, reg_preds, reg_targets)
        print(f"   {name.upper()}: {loss:.4f}")
    print()

    # 2. Classification Losses
    print("2. CLASSIFICATION LOSSES:")
    print("-" * 40)

    manager.create_loss("bce", LossType.BINARY_CROSS_ENTROPY)
    manager.create_loss("focal", LossType.FOCAL, gamma=2.0)
    manager.create_loss("hinge", LossType.HINGE)

    hinge_preds = [0.5, -0.3, 0.8, 0.6, -0.1]
    hinge_targets = [1, -1, 1, 1, -1]

    print(f"   BCE: {manager.compute('bce', predictions, targets):.4f}")
    print(f"   Focal: {manager.compute('focal', predictions, targets):.4f}")
    print(f"   Hinge: {manager.compute('hinge', hinge_preds, hinge_targets):.4f}")
    print()

    # 3. Gradients
    print("3. LOSS GRADIENTS:")
    print("-" * 40)

    mse_grad = manager.gradient("mse", reg_preds, reg_targets)
    bce_grad = manager.gradient("bce", predictions, targets)

    print(f"   MSE gradients: {[f'{g:.4f}' for g in mse_grad]}")
    print(f"   BCE gradients: {[f'{g:.4f}' for g in bce_grad]}")
    print()

    # 4. Specialized Losses
    print("4. SPECIALIZED LOSSES:")
    print("-" * 40)

    manager.create_loss("kl", LossType.KL_DIVERGENCE)
    manager.create_loss("cosine", LossType.COSINE)

    probs_p = [0.3, 0.4, 0.3]
    probs_q = [0.25, 0.5, 0.25]

    print(f"   KL Divergence: {manager.compute('kl', probs_p, probs_q):.4f}")

    vec_a = [1.0, 2.0, 3.0]
    vec_b = [1.0, 2.0, 2.0]
    print(f"   Cosine Loss: {manager.compute('cosine', vec_a, vec_b):.4f}")
    print()

    # 5. Multi-Task Loss
    print("5. MULTI-TASK LOSS:")
    print("-" * 40)

    manager.add_multi_loss("regression", LossType.MSE, weight=1.0)
    manager.add_multi_loss("classification", LossType.BINARY_CROSS_ENTROPY, weight=0.5)

    preds_dict = {
        "regression": reg_preds,
        "classification": predictions
    }
    targets_dict = {
        "regression": reg_targets,
        "classification": targets
    }

    multi_loss = manager.compute_multi(preds_dict, targets_dict)

    print(f"   Individual losses:")
    for name, value in multi_loss.losses.items():
        weight = multi_loss.weights[name]
        print(f"      {name}: {value:.4f} (weight: {weight})")
    print(f"   Total weighted loss: {multi_loss.total:.4f}")
    print()

    # 6. Loss History
    print("6. LOSS HISTORY:")
    print("-" * 40)

    for epoch in range(10):
        loss = 1.0 / (epoch + 1) + random.gauss(0, 0.01)
        manager.record("training", loss, epoch)

    stats = manager.get_stats("training")
    print(f"   Training loss stats:")
    print(f"      Mean: {stats.mean:.4f}")
    print(f"      Min: {stats.min_val:.4f}")
    print(f"      Max: {stats.max_val:.4f}")
    print(f"      Std: {stats.std:.4f}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Loss Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
