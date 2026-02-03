#!/usr/bin/env python3
"""
BAEL - Activation Manager
Comprehensive activation function management for AI agents.

Features:
- Standard activations (ReLU, Sigmoid, Tanh)
- Advanced activations (GELU, Swish, Mish)
- Parametric activations (PReLU, ELU)
- Activation statistics
- Custom activations
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

class ActivationType(Enum):
    """Activation function types."""
    RELU = "relu"
    LEAKY_RELU = "leaky_relu"
    PRELU = "prelu"
    ELU = "elu"
    SELU = "selu"
    SIGMOID = "sigmoid"
    TANH = "tanh"
    SOFTMAX = "softmax"
    SOFTPLUS = "softplus"
    SOFTSIGN = "softsign"
    GELU = "gelu"
    SWISH = "swish"
    MISH = "mish"
    HARD_SIGMOID = "hard_sigmoid"
    HARD_SWISH = "hard_swish"
    LINEAR = "linear"


class ActivationProperty(Enum):
    """Properties of activation functions."""
    BOUNDED = "bounded"
    UNBOUNDED = "unbounded"
    MONOTONIC = "monotonic"
    NON_MONOTONIC = "non_monotonic"
    DIFFERENTIABLE = "differentiable"
    ZERO_CENTERED = "zero_centered"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class ActivationResult:
    """Result of activation computation."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    inputs: List[float] = field(default_factory=list)
    outputs: List[float] = field(default_factory=list)
    activation_type: ActivationType = ActivationType.RELU


@dataclass
class ActivationStats:
    """Statistics for activation outputs."""
    mean: float = 0.0
    std: float = 0.0
    min_val: float = 0.0
    max_val: float = 0.0
    sparsity: float = 0.0
    saturation: float = 0.0


@dataclass
class ActivationConfig:
    """Configuration for activation function."""
    activation_type: ActivationType = ActivationType.RELU
    alpha: float = 0.01
    beta: float = 1.0
    threshold: float = 20.0


# =============================================================================
# ACTIVATION FUNCTION BASE
# =============================================================================

class ActivationFunction(ABC):
    """Abstract base activation function."""

    @abstractmethod
    def forward(self, x: float) -> float:
        """Apply activation."""
        pass

    @abstractmethod
    def derivative(self, x: float) -> float:
        """Compute derivative."""
        pass

    def forward_batch(self, x: List[float]) -> List[float]:
        """Apply activation to batch."""
        return [self.forward(xi) for xi in x]

    def derivative_batch(self, x: List[float]) -> List[float]:
        """Compute derivatives for batch."""
        return [self.derivative(xi) for xi in x]


# =============================================================================
# STANDARD ACTIVATIONS
# =============================================================================

class ReLU(ActivationFunction):
    """Rectified Linear Unit."""

    def forward(self, x: float) -> float:
        return max(0.0, x)

    def derivative(self, x: float) -> float:
        return 1.0 if x > 0 else 0.0


class LeakyReLU(ActivationFunction):
    """Leaky ReLU."""

    def __init__(self, alpha: float = 0.01):
        self._alpha = alpha

    def forward(self, x: float) -> float:
        return x if x > 0 else self._alpha * x

    def derivative(self, x: float) -> float:
        return 1.0 if x > 0 else self._alpha


class PReLU(ActivationFunction):
    """Parametric ReLU with learnable alpha."""

    def __init__(self, alpha: float = 0.25):
        self._alpha = alpha
        self._alpha_gradient = 0.0

    def forward(self, x: float) -> float:
        return x if x > 0 else self._alpha * x

    def derivative(self, x: float) -> float:
        return 1.0 if x > 0 else self._alpha

    def alpha_gradient(self, x: float) -> float:
        """Gradient with respect to alpha."""
        return x if x < 0 else 0.0

    def update_alpha(self, gradient: float, lr: float = 0.01) -> None:
        """Update alpha parameter."""
        self._alpha -= lr * gradient


class ELU(ActivationFunction):
    """Exponential Linear Unit."""

    def __init__(self, alpha: float = 1.0):
        self._alpha = alpha

    def forward(self, x: float) -> float:
        return x if x > 0 else self._alpha * (math.exp(x) - 1)

    def derivative(self, x: float) -> float:
        return 1.0 if x > 0 else self._alpha * math.exp(x)


class SELU(ActivationFunction):
    """Scaled Exponential Linear Unit."""

    def __init__(self):
        self._alpha = 1.6732632423543772
        self._lambda = 1.0507009873554805

    def forward(self, x: float) -> float:
        if x > 0:
            return self._lambda * x
        else:
            return self._lambda * self._alpha * (math.exp(x) - 1)

    def derivative(self, x: float) -> float:
        if x > 0:
            return self._lambda
        else:
            return self._lambda * self._alpha * math.exp(x)


class Sigmoid(ActivationFunction):
    """Sigmoid activation."""

    def forward(self, x: float) -> float:
        x = max(-500, min(500, x))
        return 1.0 / (1.0 + math.exp(-x))

    def derivative(self, x: float) -> float:
        s = self.forward(x)
        return s * (1 - s)


class Tanh(ActivationFunction):
    """Hyperbolic tangent."""

    def forward(self, x: float) -> float:
        return math.tanh(x)

    def derivative(self, x: float) -> float:
        t = math.tanh(x)
        return 1 - t ** 2


# =============================================================================
# ADVANCED ACTIVATIONS
# =============================================================================

class Softmax:
    """Softmax activation (vector function)."""

    def __init__(self, temperature: float = 1.0):
        self._temperature = temperature

    def forward(self, x: List[float]) -> List[float]:
        """Apply softmax."""
        x_scaled = [xi / self._temperature for xi in x]
        max_val = max(x_scaled)
        exp_vals = [math.exp(xi - max_val) for xi in x_scaled]
        total = sum(exp_vals)

        if total == 0:
            return [1.0 / len(x)] * len(x)

        return [e / total for e in exp_vals]

    def jacobian(self, x: List[float]) -> List[List[float]]:
        """Compute Jacobian matrix."""
        s = self.forward(x)
        n = len(s)

        jacobian = [[0.0] * n for _ in range(n)]

        for i in range(n):
            for j in range(n):
                if i == j:
                    jacobian[i][j] = s[i] * (1 - s[i])
                else:
                    jacobian[i][j] = -s[i] * s[j]

        return jacobian


class Softplus(ActivationFunction):
    """Softplus activation."""

    def __init__(self, beta: float = 1.0, threshold: float = 20.0):
        self._beta = beta
        self._threshold = threshold

    def forward(self, x: float) -> float:
        if x * self._beta > self._threshold:
            return x
        return math.log(1 + math.exp(self._beta * x)) / self._beta

    def derivative(self, x: float) -> float:
        if x * self._beta > self._threshold:
            return 1.0
        exp_val = math.exp(self._beta * x)
        return exp_val / (1 + exp_val)


class Softsign(ActivationFunction):
    """Softsign activation."""

    def forward(self, x: float) -> float:
        return x / (1 + abs(x))

    def derivative(self, x: float) -> float:
        return 1 / ((1 + abs(x)) ** 2)


class GELU(ActivationFunction):
    """Gaussian Error Linear Unit."""

    def forward(self, x: float) -> float:
        return 0.5 * x * (1 + math.tanh(
            math.sqrt(2 / math.pi) * (x + 0.044715 * x ** 3)
        ))

    def derivative(self, x: float) -> float:
        cdf = 0.5 * (1 + math.tanh(
            math.sqrt(2 / math.pi) * (x + 0.044715 * x ** 3)
        ))

        pdf = math.exp(-0.5 * x ** 2) / math.sqrt(2 * math.pi)

        return cdf + x * pdf


class Swish(ActivationFunction):
    """Swish (SiLU) activation."""

    def __init__(self, beta: float = 1.0):
        self._beta = beta

    def forward(self, x: float) -> float:
        x_clamped = max(-500, min(500, self._beta * x))
        return x / (1 + math.exp(-x_clamped))

    def derivative(self, x: float) -> float:
        x_clamped = max(-500, min(500, self._beta * x))
        sigmoid = 1 / (1 + math.exp(-x_clamped))
        return sigmoid + x * sigmoid * (1 - sigmoid) * self._beta


class Mish(ActivationFunction):
    """Mish activation."""

    def _softplus(self, x: float) -> float:
        if x > 20:
            return x
        return math.log(1 + math.exp(x))

    def forward(self, x: float) -> float:
        sp = self._softplus(x)
        return x * math.tanh(sp)

    def derivative(self, x: float) -> float:
        sp = self._softplus(x)
        tanh_sp = math.tanh(sp)
        sigmoid = 1 / (1 + math.exp(-x)) if x < 20 else 1.0

        omega = 4 * (x + 1) + 4 * math.exp(2 * x) + math.exp(3 * x) + \
                math.exp(x) * (4 * x + 6)
        delta = 2 * math.exp(x) + math.exp(2 * x) + 2

        return math.exp(x) * omega / (delta ** 2)


class HardSigmoid(ActivationFunction):
    """Hard sigmoid approximation."""

    def forward(self, x: float) -> float:
        return max(0.0, min(1.0, (x + 1) / 2))

    def derivative(self, x: float) -> float:
        if -1 < x < 1:
            return 0.5
        return 0.0


class HardSwish(ActivationFunction):
    """Hard swish approximation."""

    def forward(self, x: float) -> float:
        if x <= -3:
            return 0.0
        elif x >= 3:
            return x
        else:
            return x * (x + 3) / 6

    def derivative(self, x: float) -> float:
        if x <= -3:
            return 0.0
        elif x >= 3:
            return 1.0
        else:
            return (2 * x + 3) / 6


class Linear(ActivationFunction):
    """Linear (identity) activation."""

    def forward(self, x: float) -> float:
        return x

    def derivative(self, x: float) -> float:
        return 1.0


# =============================================================================
# ACTIVATION ANALYZER
# =============================================================================

class ActivationAnalyzer:
    """Analyze activation function outputs."""

    def compute_stats(self, outputs: List[float]) -> ActivationStats:
        """Compute statistics for activation outputs."""
        if not outputs:
            return ActivationStats()

        n = len(outputs)
        mean = sum(outputs) / n
        variance = sum((o - mean) ** 2 for o in outputs) / n
        std = math.sqrt(variance)

        min_val = min(outputs)
        max_val = max(outputs)

        zero_count = sum(1 for o in outputs if o == 0)
        sparsity = zero_count / n

        saturated = sum(1 for o in outputs if abs(o) > 0.99 or abs(o) < 0.01)
        saturation = saturated / n

        return ActivationStats(
            mean=mean,
            std=std,
            min_val=min_val,
            max_val=max_val,
            sparsity=sparsity,
            saturation=saturation
        )

    def get_properties(
        self,
        activation_type: ActivationType
    ) -> List[ActivationProperty]:
        """Get properties of activation function."""
        properties = []

        bounded = {
            ActivationType.SIGMOID,
            ActivationType.TANH,
            ActivationType.SOFTMAX,
            ActivationType.SOFTSIGN,
            ActivationType.HARD_SIGMOID
        }

        monotonic = {
            ActivationType.RELU,
            ActivationType.LEAKY_RELU,
            ActivationType.SIGMOID,
            ActivationType.TANH,
            ActivationType.SOFTPLUS,
            ActivationType.LINEAR
        }

        zero_centered = {
            ActivationType.TANH,
            ActivationType.SELU,
            ActivationType.ELU,
            ActivationType.GELU
        }

        if activation_type in bounded:
            properties.append(ActivationProperty.BOUNDED)
        else:
            properties.append(ActivationProperty.UNBOUNDED)

        if activation_type in monotonic:
            properties.append(ActivationProperty.MONOTONIC)
        else:
            properties.append(ActivationProperty.NON_MONOTONIC)

        if activation_type in zero_centered:
            properties.append(ActivationProperty.ZERO_CENTERED)

        properties.append(ActivationProperty.DIFFERENTIABLE)

        return properties


# =============================================================================
# ACTIVATION MANAGER
# =============================================================================

class ActivationManager:
    """
    Activation Manager for BAEL.

    Comprehensive activation function management for AI agents.
    """

    def __init__(self):
        self._activations: Dict[str, ActivationFunction] = {}
        self._softmax = Softmax()
        self._analyzer = ActivationAnalyzer()
        self._init_default_activations()

    def _init_default_activations(self) -> None:
        """Initialize default activation functions."""
        self._activations["relu"] = ReLU()
        self._activations["leaky_relu"] = LeakyReLU()
        self._activations["prelu"] = PReLU()
        self._activations["elu"] = ELU()
        self._activations["selu"] = SELU()
        self._activations["sigmoid"] = Sigmoid()
        self._activations["tanh"] = Tanh()
        self._activations["softplus"] = Softplus()
        self._activations["softsign"] = Softsign()
        self._activations["gelu"] = GELU()
        self._activations["swish"] = Swish()
        self._activations["mish"] = Mish()
        self._activations["hard_sigmoid"] = HardSigmoid()
        self._activations["hard_swish"] = HardSwish()
        self._activations["linear"] = Linear()

    def get_activation(self, name: str) -> Optional[ActivationFunction]:
        """Get activation function by name."""
        return self._activations.get(name.lower())

    def create_activation(
        self,
        activation_type: ActivationType,
        **kwargs
    ) -> ActivationFunction:
        """Create activation function with custom parameters."""
        if activation_type == ActivationType.RELU:
            return ReLU()
        elif activation_type == ActivationType.LEAKY_RELU:
            return LeakyReLU(kwargs.get("alpha", 0.01))
        elif activation_type == ActivationType.PRELU:
            return PReLU(kwargs.get("alpha", 0.25))
        elif activation_type == ActivationType.ELU:
            return ELU(kwargs.get("alpha", 1.0))
        elif activation_type == ActivationType.SELU:
            return SELU()
        elif activation_type == ActivationType.SIGMOID:
            return Sigmoid()
        elif activation_type == ActivationType.TANH:
            return Tanh()
        elif activation_type == ActivationType.SOFTPLUS:
            return Softplus(
                kwargs.get("beta", 1.0),
                kwargs.get("threshold", 20.0)
            )
        elif activation_type == ActivationType.SOFTSIGN:
            return Softsign()
        elif activation_type == ActivationType.GELU:
            return GELU()
        elif activation_type == ActivationType.SWISH:
            return Swish(kwargs.get("beta", 1.0))
        elif activation_type == ActivationType.MISH:
            return Mish()
        elif activation_type == ActivationType.HARD_SIGMOID:
            return HardSigmoid()
        elif activation_type == ActivationType.HARD_SWISH:
            return HardSwish()
        elif activation_type == ActivationType.LINEAR:
            return Linear()
        else:
            return ReLU()

    def apply(
        self,
        x: Union[float, List[float]],
        activation_type: ActivationType
    ) -> Union[float, List[float]]:
        """Apply activation function."""
        activation = self.create_activation(activation_type)

        if isinstance(x, list):
            return activation.forward_batch(x)
        return activation.forward(x)

    def derivative(
        self,
        x: Union[float, List[float]],
        activation_type: ActivationType
    ) -> Union[float, List[float]]:
        """Compute activation derivative."""
        activation = self.create_activation(activation_type)

        if isinstance(x, list):
            return activation.derivative_batch(x)
        return activation.derivative(x)

    def softmax(
        self,
        x: List[float],
        temperature: float = 1.0
    ) -> List[float]:
        """Apply softmax."""
        self._softmax._temperature = temperature
        return self._softmax.forward(x)

    def analyze(self, outputs: List[float]) -> ActivationStats:
        """Analyze activation outputs."""
        return self._analyzer.compute_stats(outputs)

    def get_properties(
        self,
        activation_type: ActivationType
    ) -> List[ActivationProperty]:
        """Get activation function properties."""
        return self._analyzer.get_properties(activation_type)

    def compare(
        self,
        x: List[float],
        activation_types: List[ActivationType]
    ) -> Dict[str, ActivationStats]:
        """Compare different activations on same input."""
        results = {}

        for act_type in activation_types:
            outputs = self.apply(x, act_type)
            if isinstance(outputs, float):
                outputs = [outputs]
            stats = self.analyze(outputs)
            results[act_type.value] = stats

        return results


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Activation Manager."""
    print("=" * 70)
    print("BAEL - ACTIVATION MANAGER DEMO")
    print("Comprehensive Activation Function Management for AI Agents")
    print("=" * 70)
    print()

    manager = ActivationManager()

    test_values = [-2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0]

    # 1. Standard Activations
    print("1. STANDARD ACTIVATIONS:")
    print("-" * 40)

    for act_type in [ActivationType.RELU, ActivationType.SIGMOID, ActivationType.TANH]:
        outputs = manager.apply(test_values, act_type)
        print(f"   {act_type.value}: {[f'{o:.3f}' for o in outputs]}")
    print()

    # 2. Advanced Activations
    print("2. ADVANCED ACTIVATIONS:")
    print("-" * 40)

    for act_type in [ActivationType.GELU, ActivationType.SWISH, ActivationType.MISH]:
        outputs = manager.apply(test_values, act_type)
        print(f"   {act_type.value}: {[f'{o:.3f}' for o in outputs]}")
    print()

    # 3. ReLU Variants
    print("3. RELU VARIANTS:")
    print("-" * 40)

    for act_type in [ActivationType.RELU, ActivationType.LEAKY_RELU, ActivationType.ELU, ActivationType.SELU]:
        outputs = manager.apply(test_values, act_type)
        print(f"   {act_type.value}: {[f'{o:.3f}' for o in outputs]}")
    print()

    # 4. Derivatives
    print("4. DERIVATIVES:")
    print("-" * 40)

    for act_type in [ActivationType.RELU, ActivationType.SIGMOID, ActivationType.GELU]:
        derivs = manager.derivative(test_values, act_type)
        print(f"   {act_type.value}: {[f'{d:.3f}' for d in derivs]}")
    print()

    # 5. Softmax
    print("5. SOFTMAX:")
    print("-" * 40)

    logits = [2.0, 1.0, 0.5, 0.0]

    for temp in [0.5, 1.0, 2.0]:
        probs = manager.softmax(logits, temperature=temp)
        print(f"   Temperature {temp}: {[f'{p:.3f}' for p in probs]}")
    print()

    # 6. Activation Statistics
    print("6. ACTIVATION STATISTICS:")
    print("-" * 40)

    random_inputs = [random.gauss(0, 1) for _ in range(100)]

    for act_type in [ActivationType.RELU, ActivationType.SIGMOID, ActivationType.TANH]:
        outputs = manager.apply(random_inputs, act_type)
        stats = manager.analyze(outputs)
        print(f"   {act_type.value}:")
        print(f"      Mean: {stats.mean:.3f}, Std: {stats.std:.3f}")
        print(f"      Sparsity: {stats.sparsity:.2%}")
    print()

    # 7. Activation Properties
    print("7. ACTIVATION PROPERTIES:")
    print("-" * 40)

    for act_type in [ActivationType.RELU, ActivationType.SIGMOID, ActivationType.GELU]:
        props = manager.get_properties(act_type)
        prop_names = [p.value for p in props]
        print(f"   {act_type.value}: {', '.join(prop_names)}")
    print()

    # 8. Hard Approximations
    print("8. HARD APPROXIMATIONS:")
    print("-" * 40)

    sig_out = manager.apply(test_values, ActivationType.SIGMOID)
    hard_sig_out = manager.apply(test_values, ActivationType.HARD_SIGMOID)

    print(f"   Sigmoid:      {[f'{o:.3f}' for o in sig_out]}")
    print(f"   Hard Sigmoid: {[f'{o:.3f}' for o in hard_sig_out]}")

    swish_out = manager.apply(test_values, ActivationType.SWISH)
    hard_swish_out = manager.apply(test_values, ActivationType.HARD_SWISH)

    print(f"   Swish:        {[f'{o:.3f}' for o in swish_out]}")
    print(f"   Hard Swish:   {[f'{o:.3f}' for o in hard_swish_out]}")
    print()

    # 9. Comparison
    print("9. ACTIVATION COMPARISON:")
    print("-" * 40)

    comparison = manager.compare(
        random_inputs,
        [ActivationType.RELU, ActivationType.GELU, ActivationType.SWISH]
    )

    print("   Activation | Mean  | Std   | Sparsity")
    for name, stats in comparison.items():
        print(f"   {name:10} | {stats.mean:.3f} | {stats.std:.3f} | {stats.sparsity:.2%}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Activation Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
