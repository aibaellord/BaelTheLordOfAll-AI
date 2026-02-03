#!/usr/bin/env python3
"""
BAEL - Gradient Manager
Advanced gradient computation and management for AI agents.

Features:
- Numerical gradients
- Gradient clipping
- Gradient accumulation
- Gradient checkpointing concepts
- Gradient statistics
"""

import asyncio
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

class GradientClipType(Enum):
    """Gradient clipping types."""
    NONE = "none"
    VALUE = "value"
    NORM = "norm"
    GLOBAL_NORM = "global_norm"


class GradientStatus(Enum):
    """Gradient status."""
    COMPUTED = "computed"
    ACCUMULATED = "accumulated"
    CLIPPED = "clipped"
    ZEROED = "zeroed"


class AggregationType(Enum):
    """Gradient aggregation types."""
    SUM = "sum"
    MEAN = "mean"
    WEIGHTED = "weighted"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Gradient:
    """A gradient value."""
    gradient_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parameter_name: str = ""
    value: float = 0.0
    status: GradientStatus = GradientStatus.COMPUTED
    step: int = 0


@dataclass
class GradientVector:
    """A vector of gradients."""
    vector_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    values: List[float] = field(default_factory=list)
    parameter_name: str = ""
    step: int = 0


@dataclass
class GradientStats:
    """Gradient statistics."""
    mean: float = 0.0
    std: float = 0.0
    min_val: float = 0.0
    max_val: float = 0.0
    l2_norm: float = 0.0
    count: int = 0


@dataclass
class ClipResult:
    """Result of gradient clipping."""
    clipped_gradients: List[float] = field(default_factory=list)
    original_norm: float = 0.0
    clipped_norm: float = 0.0
    was_clipped: bool = False


@dataclass
class AccumulationBuffer:
    """Buffer for gradient accumulation."""
    buffer_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    gradients: Dict[str, List[float]] = field(default_factory=dict)
    accumulation_steps: int = 0
    current_step: int = 0


# =============================================================================
# NUMERICAL GRADIENT CALCULATOR
# =============================================================================

class NumericalGradientCalculator:
    """Calculate numerical gradients."""

    def __init__(self, epsilon: float = 1e-7):
        self._epsilon = epsilon

    def compute(
        self,
        f: Callable[[List[float]], float],
        x: List[float]
    ) -> List[float]:
        """Compute numerical gradient using finite differences."""
        gradients = []

        for i in range(len(x)):
            x_plus = x.copy()
            x_minus = x.copy()

            x_plus[i] += self._epsilon
            x_minus[i] -= self._epsilon

            f_plus = f(x_plus)
            f_minus = f(x_minus)

            grad = (f_plus - f_minus) / (2 * self._epsilon)
            gradients.append(grad)

        return gradients

    def check_gradient(
        self,
        f: Callable[[List[float]], float],
        x: List[float],
        analytical_grad: List[float],
        tolerance: float = 1e-4
    ) -> Tuple[bool, List[float]]:
        """Check analytical gradient against numerical."""
        numerical_grad = self.compute(f, x)

        differences = []
        all_close = True

        for num, ana in zip(numerical_grad, analytical_grad):
            diff = abs(num - ana)
            relative_diff = diff / max(abs(num), abs(ana), 1e-8)
            differences.append(relative_diff)

            if relative_diff > tolerance:
                all_close = False

        return all_close, differences


# =============================================================================
# GRADIENT CLIPPER
# =============================================================================

class GradientClipper:
    """Clip gradients to prevent explosion."""

    @staticmethod
    def clip_by_value(
        gradients: List[float],
        min_val: float,
        max_val: float
    ) -> ClipResult:
        """Clip gradients by value."""
        clipped = [max(min_val, min(max_val, g)) for g in gradients]

        original_norm = math.sqrt(sum(g ** 2 for g in gradients))
        clipped_norm = math.sqrt(sum(g ** 2 for g in clipped))

        was_clipped = any(
            g != c for g, c in zip(gradients, clipped)
        )

        return ClipResult(
            clipped_gradients=clipped,
            original_norm=original_norm,
            clipped_norm=clipped_norm,
            was_clipped=was_clipped
        )

    @staticmethod
    def clip_by_norm(
        gradients: List[float],
        max_norm: float
    ) -> ClipResult:
        """Clip gradients by L2 norm."""
        norm = math.sqrt(sum(g ** 2 for g in gradients))

        if norm <= max_norm:
            return ClipResult(
                clipped_gradients=gradients.copy(),
                original_norm=norm,
                clipped_norm=norm,
                was_clipped=False
            )

        scale = max_norm / norm
        clipped = [g * scale for g in gradients]

        return ClipResult(
            clipped_gradients=clipped,
            original_norm=norm,
            clipped_norm=max_norm,
            was_clipped=True
        )

    @staticmethod
    def clip_by_global_norm(
        gradient_lists: List[List[float]],
        max_norm: float
    ) -> Tuple[List[ClipResult], float]:
        """Clip multiple gradient vectors by global norm."""
        global_norm_sq = 0.0
        for grads in gradient_lists:
            global_norm_sq += sum(g ** 2 for g in grads)

        global_norm = math.sqrt(global_norm_sq)

        if global_norm <= max_norm:
            results = [
                ClipResult(
                    clipped_gradients=g.copy(),
                    original_norm=math.sqrt(sum(x ** 2 for x in g)),
                    clipped_norm=math.sqrt(sum(x ** 2 for x in g)),
                    was_clipped=False
                )
                for g in gradient_lists
            ]
            return results, global_norm

        scale = max_norm / global_norm

        results = []
        for grads in gradient_lists:
            clipped = [g * scale for g in grads]
            local_norm = math.sqrt(sum(g ** 2 for g in grads))
            clipped_norm = math.sqrt(sum(g ** 2 for g in clipped))

            results.append(ClipResult(
                clipped_gradients=clipped,
                original_norm=local_norm,
                clipped_norm=clipped_norm,
                was_clipped=True
            ))

        return results, global_norm


# =============================================================================
# GRADIENT ACCUMULATOR
# =============================================================================

class GradientAccumulator:
    """Accumulate gradients over multiple steps."""

    def __init__(self, accumulation_steps: int = 1):
        self._accumulation_steps = accumulation_steps
        self._buffers: Dict[str, AccumulationBuffer] = {}

    def create_buffer(self, buffer_name: str) -> AccumulationBuffer:
        """Create an accumulation buffer."""
        buffer = AccumulationBuffer(accumulation_steps=self._accumulation_steps)
        self._buffers[buffer_name] = buffer
        return buffer

    def accumulate(
        self,
        buffer_name: str,
        param_name: str,
        gradients: List[float]
    ) -> None:
        """Accumulate gradients."""
        if buffer_name not in self._buffers:
            self.create_buffer(buffer_name)

        buffer = self._buffers[buffer_name]

        if param_name not in buffer.gradients:
            buffer.gradients[param_name] = [0.0] * len(gradients)

        for i, g in enumerate(gradients):
            buffer.gradients[param_name][i] += g

        buffer.current_step += 1

    def should_step(self, buffer_name: str) -> bool:
        """Check if we should perform an optimization step."""
        if buffer_name not in self._buffers:
            return False

        buffer = self._buffers[buffer_name]
        return buffer.current_step >= buffer.accumulation_steps

    def get_accumulated(
        self,
        buffer_name: str,
        param_name: str
    ) -> Optional[List[float]]:
        """Get accumulated gradients."""
        if buffer_name not in self._buffers:
            return None

        buffer = self._buffers[buffer_name]
        if param_name not in buffer.gradients:
            return None

        gradients = buffer.gradients[param_name]
        return [g / buffer.accumulation_steps for g in gradients]

    def reset(self, buffer_name: str) -> None:
        """Reset accumulation buffer."""
        if buffer_name in self._buffers:
            buffer = self._buffers[buffer_name]
            buffer.gradients.clear()
            buffer.current_step = 0


# =============================================================================
# GRADIENT STATISTICS
# =============================================================================

class GradientStatistics:
    """Compute gradient statistics."""

    def __init__(self, window_size: int = 100):
        self._window_size = window_size
        self._history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=window_size)
        )

    def record(self, param_name: str, gradients: List[float]) -> None:
        """Record gradients for statistics."""
        stats = self.compute_stats(gradients)
        self._history[param_name].append(stats)

    def compute_stats(self, gradients: List[float]) -> GradientStats:
        """Compute statistics for gradients."""
        if not gradients:
            return GradientStats()

        n = len(gradients)
        mean = sum(gradients) / n
        variance = sum((g - mean) ** 2 for g in gradients) / n
        std = math.sqrt(variance)

        min_val = min(gradients)
        max_val = max(gradients)
        l2_norm = math.sqrt(sum(g ** 2 for g in gradients))

        return GradientStats(
            mean=mean,
            std=std,
            min_val=min_val,
            max_val=max_val,
            l2_norm=l2_norm,
            count=n
        )

    def get_history_stats(self, param_name: str) -> Optional[GradientStats]:
        """Get average statistics over history."""
        if param_name not in self._history or not self._history[param_name]:
            return None

        history = self._history[param_name]
        n = len(history)

        avg_mean = sum(s.mean for s in history) / n
        avg_std = sum(s.std for s in history) / n
        avg_norm = sum(s.l2_norm for s in history) / n
        min_val = min(s.min_val for s in history)
        max_val = max(s.max_val for s in history)

        return GradientStats(
            mean=avg_mean,
            std=avg_std,
            min_val=min_val,
            max_val=max_val,
            l2_norm=avg_norm,
            count=n
        )

    def detect_explosion(
        self,
        param_name: str,
        threshold: float = 100.0
    ) -> bool:
        """Detect gradient explosion."""
        if param_name not in self._history or not self._history[param_name]:
            return False

        recent = self._history[param_name][-1]
        return recent.l2_norm > threshold

    def detect_vanishing(
        self,
        param_name: str,
        threshold: float = 1e-7
    ) -> bool:
        """Detect vanishing gradients."""
        if param_name not in self._history or not self._history[param_name]:
            return False

        recent = self._history[param_name][-1]
        return recent.l2_norm < threshold


# =============================================================================
# GRADIENT SCALER (for mixed precision concepts)
# =============================================================================

class GradientScaler:
    """Scale gradients for numerical stability."""

    def __init__(self, init_scale: float = 65536.0, growth_factor: float = 2.0):
        self._scale = init_scale
        self._growth_factor = growth_factor
        self._backoff_factor = 0.5
        self._growth_interval = 2000
        self._step = 0

    def scale(self, gradients: List[float]) -> List[float]:
        """Scale gradients."""
        return [g * self._scale for g in gradients]

    def unscale(self, gradients: List[float]) -> List[float]:
        """Unscale gradients."""
        return [g / self._scale for g in gradients]

    def check_for_inf_nan(self, gradients: List[float]) -> bool:
        """Check for inf or nan in gradients."""
        for g in gradients:
            if math.isnan(g) or math.isinf(g):
                return True
        return False

    def update(self, had_overflow: bool) -> None:
        """Update scale based on overflow status."""
        if had_overflow:
            self._scale *= self._backoff_factor
            self._step = 0
        else:
            self._step += 1
            if self._step >= self._growth_interval:
                self._scale *= self._growth_factor
                self._step = 0


# =============================================================================
# GRADIENT MANAGER
# =============================================================================

class GradientManager:
    """
    Gradient Manager for BAEL.

    Advanced gradient computation and management for AI agents.
    """

    def __init__(self):
        self._numerical = NumericalGradientCalculator()
        self._clipper = GradientClipper()
        self._accumulator = GradientAccumulator()
        self._statistics = GradientStatistics()
        self._scaler = GradientScaler()

    # -------------------------------------------------------------------------
    # NUMERICAL GRADIENTS
    # -------------------------------------------------------------------------

    def compute_numerical_gradient(
        self,
        f: Callable[[List[float]], float],
        x: List[float],
        epsilon: float = 1e-7
    ) -> List[float]:
        """Compute numerical gradient."""
        self._numerical._epsilon = epsilon
        return self._numerical.compute(f, x)

    def check_gradient(
        self,
        f: Callable[[List[float]], float],
        x: List[float],
        analytical_grad: List[float],
        tolerance: float = 1e-4
    ) -> Tuple[bool, List[float]]:
        """Check analytical gradient against numerical."""
        return self._numerical.check_gradient(f, x, analytical_grad, tolerance)

    # -------------------------------------------------------------------------
    # CLIPPING
    # -------------------------------------------------------------------------

    def clip_by_value(
        self,
        gradients: List[float],
        min_val: float = -1.0,
        max_val: float = 1.0
    ) -> ClipResult:
        """Clip gradients by value."""
        return self._clipper.clip_by_value(gradients, min_val, max_val)

    def clip_by_norm(
        self,
        gradients: List[float],
        max_norm: float = 1.0
    ) -> ClipResult:
        """Clip gradients by norm."""
        return self._clipper.clip_by_norm(gradients, max_norm)

    def clip_global_norm(
        self,
        gradient_lists: List[List[float]],
        max_norm: float = 1.0
    ) -> Tuple[List[ClipResult], float]:
        """Clip multiple gradient vectors by global norm."""
        return self._clipper.clip_by_global_norm(gradient_lists, max_norm)

    # -------------------------------------------------------------------------
    # ACCUMULATION
    # -------------------------------------------------------------------------

    def setup_accumulation(
        self,
        buffer_name: str,
        accumulation_steps: int
    ) -> AccumulationBuffer:
        """Setup gradient accumulation."""
        self._accumulator._accumulation_steps = accumulation_steps
        return self._accumulator.create_buffer(buffer_name)

    def accumulate(
        self,
        buffer_name: str,
        param_name: str,
        gradients: List[float]
    ) -> None:
        """Accumulate gradients."""
        self._accumulator.accumulate(buffer_name, param_name, gradients)

    def should_update(self, buffer_name: str) -> bool:
        """Check if we should update parameters."""
        return self._accumulator.should_step(buffer_name)

    def get_accumulated(
        self,
        buffer_name: str,
        param_name: str
    ) -> Optional[List[float]]:
        """Get accumulated gradients."""
        return self._accumulator.get_accumulated(buffer_name, param_name)

    def reset_accumulation(self, buffer_name: str) -> None:
        """Reset accumulation buffer."""
        self._accumulator.reset(buffer_name)

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def record_gradients(
        self,
        param_name: str,
        gradients: List[float]
    ) -> GradientStats:
        """Record and get statistics for gradients."""
        self._statistics.record(param_name, gradients)
        return self._statistics.compute_stats(gradients)

    def get_gradient_stats(self, param_name: str) -> Optional[GradientStats]:
        """Get gradient statistics history."""
        return self._statistics.get_history_stats(param_name)

    def is_exploding(
        self,
        param_name: str,
        threshold: float = 100.0
    ) -> bool:
        """Check for gradient explosion."""
        return self._statistics.detect_explosion(param_name, threshold)

    def is_vanishing(
        self,
        param_name: str,
        threshold: float = 1e-7
    ) -> bool:
        """Check for vanishing gradients."""
        return self._statistics.detect_vanishing(param_name, threshold)

    # -------------------------------------------------------------------------
    # SCALING
    # -------------------------------------------------------------------------

    def scale_gradients(self, gradients: List[float]) -> List[float]:
        """Scale gradients."""
        return self._scaler.scale(gradients)

    def unscale_gradients(self, gradients: List[float]) -> List[float]:
        """Unscale gradients."""
        return self._scaler.unscale(gradients)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Gradient Manager."""
    print("=" * 70)
    print("BAEL - GRADIENT MANAGER DEMO")
    print("Advanced Gradient Computation and Management for AI Agents")
    print("=" * 70)
    print()

    manager = GradientManager()

    # 1. Numerical Gradients
    print("1. NUMERICAL GRADIENTS:")
    print("-" * 40)

    def quadratic(x):
        return sum(xi ** 2 for xi in x)

    x = [1.0, 2.0, 3.0]
    numerical_grad = manager.compute_numerical_gradient(quadratic, x)
    analytical_grad = [2 * xi for xi in x]

    print(f"   Function: f(x) = sum(x_i^2)")
    print(f"   x = {x}")
    print(f"   Numerical gradient: {[f'{g:.4f}' for g in numerical_grad]}")
    print(f"   Analytical gradient: {analytical_grad}")

    passed, diffs = manager.check_gradient(quadratic, x, analytical_grad)
    print(f"   Gradient check passed: {passed}")
    print()

    # 2. Gradient Clipping
    print("2. GRADIENT CLIPPING:")
    print("-" * 40)

    gradients = [0.5, 2.0, -1.5, 0.1, 3.0]

    clip_value = manager.clip_by_value(gradients, -1.0, 1.0)
    print(f"   Original: {gradients}")
    print(f"   Clipped by value [-1, 1]: {[f'{g:.2f}' for g in clip_value.clipped_gradients]}")
    print(f"   Was clipped: {clip_value.was_clipped}")

    clip_norm = manager.clip_by_norm(gradients, 2.0)
    print(f"   Clipped by norm 2.0: {[f'{g:.2f}' for g in clip_norm.clipped_gradients]}")
    print(f"   Original norm: {clip_norm.original_norm:.2f}")
    print(f"   Clipped norm: {clip_norm.clipped_norm:.2f}")
    print()

    # 3. Global Norm Clipping
    print("3. GLOBAL NORM CLIPPING:")
    print("-" * 40)

    grad_lists = [
        [1.0, 2.0, 3.0],
        [4.0, 5.0, 6.0]
    ]

    results, global_norm = manager.clip_global_norm(grad_lists, 5.0)
    print(f"   Original global norm: {global_norm:.2f}")
    print(f"   After clipping:")
    for i, r in enumerate(results):
        print(f"      Grad {i}: {[f'{g:.2f}' for g in r.clipped_gradients]}")
    print()

    # 4. Gradient Accumulation
    print("4. GRADIENT ACCUMULATION:")
    print("-" * 40)

    manager.setup_accumulation("batch", accumulation_steps=4)

    for i in range(4):
        grads = [random.gauss(0, 1) for _ in range(3)]
        manager.accumulate("batch", "layer1", grads)
        print(f"   Step {i+1}: accumulated {[f'{g:.2f}' for g in grads]}")

        if manager.should_update("batch"):
            print(f"   Should update: True")

    accumulated = manager.get_accumulated("batch", "layer1")
    print(f"   Final averaged: {[f'{g:.2f}' for g in accumulated]}")

    manager.reset_accumulation("batch")
    print()

    # 5. Gradient Statistics
    print("5. GRADIENT STATISTICS:")
    print("-" * 40)

    for i in range(10):
        grads = [random.gauss(0, 0.1 * (i + 1)) for _ in range(5)]
        stats = manager.record_gradients("layer2", grads)

        if i == 9:
            print(f"   Last gradient stats:")
            print(f"      Mean: {stats.mean:.4f}")
            print(f"      Std: {stats.std:.4f}")
            print(f"      L2 norm: {stats.l2_norm:.4f}")

    history_stats = manager.get_gradient_stats("layer2")
    print(f"   History average norm: {history_stats.l2_norm:.4f}")
    print()

    # 6. Explosion/Vanishing Detection
    print("6. EXPLOSION/VANISHING DETECTION:")
    print("-" * 40)

    large_grads = [100.0, 200.0, 300.0]
    manager.record_gradients("large", large_grads)
    print(f"   Large gradients: {large_grads}")
    print(f"   Is exploding: {manager.is_exploding('large', threshold=50.0)}")

    small_grads = [1e-8, 1e-9, 1e-10]
    manager.record_gradients("small", small_grads)
    print(f"   Small gradients: {small_grads}")
    print(f"   Is vanishing: {manager.is_vanishing('small', threshold=1e-6)}")
    print()

    # 7. Gradient Scaling
    print("7. GRADIENT SCALING:")
    print("-" * 40)

    grads = [0.001, 0.002, 0.003]
    scaled = manager.scale_gradients(grads)
    unscaled = manager.unscale_gradients(scaled)

    print(f"   Original: {grads}")
    print(f"   Scaled: {[f'{g:.2f}' for g in scaled]}")
    print(f"   Unscaled: {unscaled}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Gradient Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
