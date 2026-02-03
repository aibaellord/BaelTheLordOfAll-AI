#!/usr/bin/env python3
"""
BAEL - Neural Network Manager
Advanced neural network abstraction and management layer.

This module provides a comprehensive neural network management system
for building, training, and deploying neural architectures without
external deep learning dependencies (zero-cost approach).

Features:
- Pure Python neural network implementations
- Multiple activation functions
- Layer abstractions (Dense, Dropout, BatchNorm, etc.)
- Optimizers (SGD, Adam, RMSprop, etc.)
- Loss functions
- Training loops and callbacks
- Model serialization
- Inference optimization
- Architecture search
- Ensemble management
"""

import asyncio
import copy
import json
import logging
import math
import os
import pickle
import random
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import (Any, Callable, Dict, List, Optional, Sequence, Tuple, Type,
                    Union)
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class ActivationType(Enum):
    """Activation function types."""
    LINEAR = "linear"
    SIGMOID = "sigmoid"
    TANH = "tanh"
    RELU = "relu"
    LEAKY_RELU = "leaky_relu"
    ELU = "elu"
    SOFTMAX = "softmax"
    SWISH = "swish"
    GELU = "gelu"


class LayerType(Enum):
    """Layer types."""
    DENSE = "dense"
    DROPOUT = "dropout"
    BATCH_NORM = "batch_norm"
    EMBEDDING = "embedding"
    ATTENTION = "attention"
    RESIDUAL = "residual"
    LSTM = "lstm"
    GRU = "gru"


class OptimizerType(Enum):
    """Optimizer types."""
    SGD = "sgd"
    MOMENTUM = "momentum"
    ADAM = "adam"
    RMSPROP = "rmsprop"
    ADAGRAD = "adagrad"
    ADAMW = "adamw"


class LossType(Enum):
    """Loss function types."""
    MSE = "mse"
    MAE = "mae"
    BINARY_CROSSENTROPY = "binary_crossentropy"
    CATEGORICAL_CROSSENTROPY = "categorical_crossentropy"
    HUBER = "huber"
    HINGE = "hinge"


class InitializationType(Enum):
    """Weight initialization types."""
    ZEROS = "zeros"
    ONES = "ones"
    RANDOM_UNIFORM = "random_uniform"
    RANDOM_NORMAL = "random_normal"
    XAVIER = "xavier"
    HE = "he"
    LECUN = "lecun"


class TrainingPhase(Enum):
    """Training phase."""
    TRAINING = "training"
    VALIDATION = "validation"
    TESTING = "testing"
    INFERENCE = "inference"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Tensor:
    """Simple tensor implementation."""
    data: List[List[float]]
    shape: Tuple[int, ...]

    @classmethod
    def zeros(cls, *shape: int) -> 'Tensor':
        """Create zero tensor."""
        if len(shape) == 1:
            return cls([[0.0] * shape[0]], (1, shape[0]))
        elif len(shape) == 2:
            return cls([[0.0] * shape[1] for _ in range(shape[0])], shape)
        else:
            raise ValueError("Only 1D and 2D tensors supported")

    @classmethod
    def ones(cls, *shape: int) -> 'Tensor':
        """Create ones tensor."""
        if len(shape) == 1:
            return cls([[1.0] * shape[0]], (1, shape[0]))
        elif len(shape) == 2:
            return cls([[1.0] * shape[1] for _ in range(shape[0])], shape)
        else:
            raise ValueError("Only 1D and 2D tensors supported")

    @classmethod
    def random_normal(cls, *shape: int, mean: float = 0.0, std: float = 1.0) -> 'Tensor':
        """Create random normal tensor."""
        def randn():
            u1 = random.random()
            u2 = random.random()
            return mean + std * math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)

        if len(shape) == 1:
            return cls([[randn() for _ in range(shape[0])]], (1, shape[0]))
        elif len(shape) == 2:
            return cls([[randn() for _ in range(shape[1])] for _ in range(shape[0])], shape)
        else:
            raise ValueError("Only 1D and 2D tensors supported")

    def transpose(self) -> 'Tensor':
        """Transpose tensor."""
        transposed = [[self.data[j][i] for j in range(len(self.data))]
                      for i in range(len(self.data[0]))]
        return Tensor(transposed, (self.shape[1], self.shape[0]))

    def matmul(self, other: 'Tensor') -> 'Tensor':
        """Matrix multiplication."""
        result = [[sum(a * b for a, b in zip(row_a, col_b))
                   for col_b in zip(*other.data)]
                  for row_a in self.data]
        return Tensor(result, (self.shape[0], other.shape[1]))

    def add(self, other: Union['Tensor', float]) -> 'Tensor':
        """Element-wise addition."""
        if isinstance(other, (int, float)):
            result = [[val + other for val in row] for row in self.data]
        else:
            result = [[a + b for a, b in zip(row_a, row_b)]
                      for row_a, row_b in zip(self.data, other.data)]
        return Tensor(result, self.shape)

    def subtract(self, other: Union['Tensor', float]) -> 'Tensor':
        """Element-wise subtraction."""
        if isinstance(other, (int, float)):
            result = [[val - other for val in row] for row in self.data]
        else:
            result = [[a - b for a, b in zip(row_a, row_b)]
                      for row_a, row_b in zip(self.data, other.data)]
        return Tensor(result, self.shape)

    def multiply(self, other: Union['Tensor', float]) -> 'Tensor':
        """Element-wise multiplication."""
        if isinstance(other, (int, float)):
            result = [[val * other for val in row] for row in self.data]
        else:
            result = [[a * b for a, b in zip(row_a, row_b)]
                      for row_a, row_b in zip(self.data, other.data)]
        return Tensor(result, self.shape)

    def apply(self, func: Callable[[float], float]) -> 'Tensor':
        """Apply function element-wise."""
        result = [[func(val) for val in row] for row in self.data]
        return Tensor(result, self.shape)

    def sum(self, axis: Optional[int] = None) -> Union['Tensor', float]:
        """Sum along axis."""
        if axis is None:
            return sum(sum(row) for row in self.data)
        elif axis == 0:
            result = [[sum(self.data[i][j] for i in range(len(self.data)))
                       for j in range(len(self.data[0]))]]
            return Tensor(result, (1, len(result[0])))
        elif axis == 1:
            result = [[sum(row)] for row in self.data]
            return Tensor(result, (len(result), 1))
        else:
            raise ValueError(f"Invalid axis: {axis}")

    def mean(self, axis: Optional[int] = None) -> Union['Tensor', float]:
        """Mean along axis."""
        total = self.sum(axis)
        if axis is None:
            return total / (self.shape[0] * self.shape[1])
        elif isinstance(total, Tensor):
            divisor = self.shape[0] if axis == 0 else self.shape[1]
            return total.multiply(1.0 / divisor)
        return total

    def flatten(self) -> List[float]:
        """Flatten to 1D list."""
        return [val for row in self.data for val in row]

    def reshape(self, *shape: int) -> 'Tensor':
        """Reshape tensor."""
        flat = self.flatten()
        if len(shape) == 1:
            return Tensor([flat[:shape[0]]], (1, shape[0]))
        elif len(shape) == 2:
            data = [flat[i * shape[1]:(i + 1) * shape[1]] for i in range(shape[0])]
            return Tensor(data, shape)
        else:
            raise ValueError("Only 1D and 2D tensors supported")

    def clip(self, min_val: float, max_val: float) -> 'Tensor':
        """Clip values."""
        result = [[max(min_val, min(max_val, val)) for val in row] for row in self.data]
        return Tensor(result, self.shape)

    def __repr__(self) -> str:
        return f"Tensor(shape={self.shape})"


@dataclass
class TrainingMetrics:
    """Training metrics."""
    epoch: int
    loss: float
    accuracy: Optional[float] = None
    val_loss: Optional[float] = None
    val_accuracy: Optional[float] = None
    learning_rate: float = 0.001
    duration_ms: float = 0.0


@dataclass
class ModelConfig:
    """Model configuration."""
    name: str
    input_shape: Tuple[int, ...]
    output_shape: Tuple[int, ...]
    layers: List[Dict[str, Any]] = field(default_factory=list)
    optimizer: OptimizerType = OptimizerType.ADAM
    loss: LossType = LossType.MSE
    learning_rate: float = 0.001
    batch_size: int = 32
    epochs: int = 100


# =============================================================================
# ACTIVATION FUNCTIONS
# =============================================================================

class Activation:
    """Activation functions."""

    @staticmethod
    def sigmoid(x: float) -> float:
        """Sigmoid activation."""
        return 1.0 / (1.0 + math.exp(-max(-500, min(500, x))))

    @staticmethod
    def sigmoid_derivative(x: float) -> float:
        """Sigmoid derivative."""
        s = Activation.sigmoid(x)
        return s * (1 - s)

    @staticmethod
    def tanh(x: float) -> float:
        """Tanh activation."""
        return math.tanh(x)

    @staticmethod
    def tanh_derivative(x: float) -> float:
        """Tanh derivative."""
        return 1 - math.tanh(x) ** 2

    @staticmethod
    def relu(x: float) -> float:
        """ReLU activation."""
        return max(0, x)

    @staticmethod
    def relu_derivative(x: float) -> float:
        """ReLU derivative."""
        return 1.0 if x > 0 else 0.0

    @staticmethod
    def leaky_relu(x: float, alpha: float = 0.01) -> float:
        """Leaky ReLU activation."""
        return x if x > 0 else alpha * x

    @staticmethod
    def leaky_relu_derivative(x: float, alpha: float = 0.01) -> float:
        """Leaky ReLU derivative."""
        return 1.0 if x > 0 else alpha

    @staticmethod
    def elu(x: float, alpha: float = 1.0) -> float:
        """ELU activation."""
        return x if x > 0 else alpha * (math.exp(x) - 1)

    @staticmethod
    def softmax(x: List[float]) -> List[float]:
        """Softmax activation."""
        max_x = max(x)
        exp_x = [math.exp(xi - max_x) for xi in x]
        sum_exp = sum(exp_x)
        return [e / sum_exp for e in exp_x]

    @staticmethod
    def swish(x: float) -> float:
        """Swish activation."""
        return x * Activation.sigmoid(x)

    @staticmethod
    def gelu(x: float) -> float:
        """GELU activation (approximate)."""
        return 0.5 * x * (1 + math.tanh(math.sqrt(2 / math.pi) * (x + 0.044715 * x ** 3)))

    @staticmethod
    def get_function(activation_type: ActivationType) -> Callable:
        """Get activation function."""
        functions = {
            ActivationType.LINEAR: lambda x: x,
            ActivationType.SIGMOID: Activation.sigmoid,
            ActivationType.TANH: Activation.tanh,
            ActivationType.RELU: Activation.relu,
            ActivationType.LEAKY_RELU: Activation.leaky_relu,
            ActivationType.ELU: Activation.elu,
            ActivationType.SWISH: Activation.swish,
            ActivationType.GELU: Activation.gelu
        }
        return functions.get(activation_type, lambda x: x)

    @staticmethod
    def get_derivative(activation_type: ActivationType) -> Callable:
        """Get activation derivative."""
        derivatives = {
            ActivationType.LINEAR: lambda x: 1.0,
            ActivationType.SIGMOID: Activation.sigmoid_derivative,
            ActivationType.TANH: Activation.tanh_derivative,
            ActivationType.RELU: Activation.relu_derivative,
            ActivationType.LEAKY_RELU: Activation.leaky_relu_derivative
        }
        return derivatives.get(activation_type, lambda x: 1.0)


# =============================================================================
# LOSS FUNCTIONS
# =============================================================================

class Loss:
    """Loss functions."""

    @staticmethod
    def mse(y_true: Tensor, y_pred: Tensor) -> float:
        """Mean Squared Error."""
        diff = y_true.subtract(y_pred)
        squared = diff.multiply(diff)
        return squared.mean()

    @staticmethod
    def mse_derivative(y_true: Tensor, y_pred: Tensor) -> Tensor:
        """MSE derivative."""
        n = y_true.shape[0] * y_true.shape[1]
        return y_pred.subtract(y_true).multiply(2.0 / n)

    @staticmethod
    def mae(y_true: Tensor, y_pred: Tensor) -> float:
        """Mean Absolute Error."""
        diff = y_true.subtract(y_pred)
        abs_diff = diff.apply(abs)
        return abs_diff.mean()

    @staticmethod
    def binary_crossentropy(y_true: Tensor, y_pred: Tensor) -> float:
        """Binary Cross-Entropy."""
        epsilon = 1e-7
        clipped = y_pred.clip(epsilon, 1 - epsilon)

        total = 0.0
        for i in range(len(y_true.data)):
            for j in range(len(y_true.data[0])):
                yt = y_true.data[i][j]
                yp = clipped.data[i][j]
                total += -(yt * math.log(yp) + (1 - yt) * math.log(1 - yp))

        return total / (len(y_true.data) * len(y_true.data[0]))

    @staticmethod
    def categorical_crossentropy(y_true: Tensor, y_pred: Tensor) -> float:
        """Categorical Cross-Entropy."""
        epsilon = 1e-7
        clipped = y_pred.clip(epsilon, 1 - epsilon)

        total = 0.0
        for i in range(len(y_true.data)):
            for j in range(len(y_true.data[0])):
                if y_true.data[i][j] > 0:
                    total += -y_true.data[i][j] * math.log(clipped.data[i][j])

        return total / len(y_true.data)

    @staticmethod
    def get_function(loss_type: LossType) -> Callable:
        """Get loss function."""
        functions = {
            LossType.MSE: Loss.mse,
            LossType.MAE: Loss.mae,
            LossType.BINARY_CROSSENTROPY: Loss.binary_crossentropy,
            LossType.CATEGORICAL_CROSSENTROPY: Loss.categorical_crossentropy
        }
        return functions.get(loss_type, Loss.mse)


# =============================================================================
# LAYERS
# =============================================================================

class Layer(ABC):
    """Abstract layer class."""

    def __init__(self, name: str = None):
        self.name = name or f"layer_{uuid4().hex[:8]}"
        self.trainable = True
        self.weights: Optional[Tensor] = None
        self.biases: Optional[Tensor] = None
        self.input_cache: Optional[Tensor] = None
        self.output_cache: Optional[Tensor] = None
        self.phase = TrainingPhase.TRAINING

    @abstractmethod
    def forward(self, x: Tensor) -> Tensor:
        """Forward pass."""
        pass

    @abstractmethod
    def backward(self, grad: Tensor) -> Tensor:
        """Backward pass."""
        pass

    def get_params(self) -> Dict[str, Tensor]:
        """Get trainable parameters."""
        params = {}
        if self.weights is not None:
            params[f"{self.name}_weights"] = self.weights
        if self.biases is not None:
            params[f"{self.name}_biases"] = self.biases
        return params

    def set_params(self, params: Dict[str, Tensor]) -> None:
        """Set parameters."""
        if f"{self.name}_weights" in params:
            self.weights = params[f"{self.name}_weights"]
        if f"{self.name}_biases" in params:
            self.biases = params[f"{self.name}_biases"]


class DenseLayer(Layer):
    """Dense (fully connected) layer."""

    def __init__(
        self,
        input_size: int,
        output_size: int,
        activation: ActivationType = ActivationType.RELU,
        initialization: InitializationType = InitializationType.HE,
        name: str = None
    ):
        super().__init__(name)
        self.input_size = input_size
        self.output_size = output_size
        self.activation_type = activation

        # Initialize weights
        if initialization == InitializationType.XAVIER:
            std = math.sqrt(2.0 / (input_size + output_size))
        elif initialization == InitializationType.HE:
            std = math.sqrt(2.0 / input_size)
        elif initialization == InitializationType.LECUN:
            std = math.sqrt(1.0 / input_size)
        else:
            std = 0.1

        self.weights = Tensor.random_normal(input_size, output_size, std=std)
        self.biases = Tensor.zeros(1, output_size)

        self.activation_fn = Activation.get_function(activation)
        self.activation_derivative = Activation.get_derivative(activation)

        # Gradient caches
        self.weight_grad: Optional[Tensor] = None
        self.bias_grad: Optional[Tensor] = None
        self.z_cache: Optional[Tensor] = None

    def forward(self, x: Tensor) -> Tensor:
        """Forward pass."""
        self.input_cache = x

        # Linear transformation: z = x @ W + b
        z = x.matmul(self.weights)
        for i in range(len(z.data)):
            for j in range(len(z.data[0])):
                z.data[i][j] += self.biases.data[0][j]

        self.z_cache = z

        # Apply activation
        if self.activation_type == ActivationType.SOFTMAX:
            result = []
            for row in z.data:
                result.append(Activation.softmax(row))
            output = Tensor(result, z.shape)
        else:
            output = z.apply(self.activation_fn)

        self.output_cache = output
        return output

    def backward(self, grad: Tensor) -> Tensor:
        """Backward pass."""
        # Apply activation derivative
        if self.activation_type == ActivationType.SOFTMAX:
            # For softmax with cross-entropy, grad is already dL/dz
            dz = grad
        else:
            dz = Tensor([[grad.data[i][j] * self.activation_derivative(self.z_cache.data[i][j])
                          for j in range(len(grad.data[0]))]
                         for i in range(len(grad.data))], grad.shape)

        # Weight gradient: dW = X^T @ dz
        self.weight_grad = self.input_cache.transpose().matmul(dz)

        # Bias gradient: db = sum(dz, axis=0)
        self.bias_grad = dz.sum(axis=0)

        # Input gradient: dx = dz @ W^T
        dx = dz.matmul(self.weights.transpose())

        return dx


class DropoutLayer(Layer):
    """Dropout regularization layer."""

    def __init__(self, rate: float = 0.5, name: str = None):
        super().__init__(name)
        self.rate = rate
        self.mask: Optional[Tensor] = None
        self.trainable = False

    def forward(self, x: Tensor) -> Tensor:
        """Forward pass."""
        self.input_cache = x

        if self.phase == TrainingPhase.TRAINING:
            # Create dropout mask
            mask_data = [[1.0 if random.random() > self.rate else 0.0
                          for _ in range(x.shape[1])]
                         for _ in range(x.shape[0])]
            self.mask = Tensor(mask_data, x.shape)

            # Apply mask and scale
            scale = 1.0 / (1.0 - self.rate)
            output = x.multiply(self.mask).multiply(scale)
        else:
            output = x

        self.output_cache = output
        return output

    def backward(self, grad: Tensor) -> Tensor:
        """Backward pass."""
        if self.phase == TrainingPhase.TRAINING:
            scale = 1.0 / (1.0 - self.rate)
            return grad.multiply(self.mask).multiply(scale)
        return grad


class BatchNormLayer(Layer):
    """Batch normalization layer."""

    def __init__(
        self,
        num_features: int,
        momentum: float = 0.1,
        epsilon: float = 1e-5,
        name: str = None
    ):
        super().__init__(name)
        self.num_features = num_features
        self.momentum = momentum
        self.epsilon = epsilon

        # Learnable parameters
        self.gamma = Tensor.ones(1, num_features)
        self.beta = Tensor.zeros(1, num_features)

        # Running statistics
        self.running_mean = Tensor.zeros(1, num_features)
        self.running_var = Tensor.ones(1, num_features)

        # Caches
        self.x_norm: Optional[Tensor] = None
        self.std: Optional[Tensor] = None

    def forward(self, x: Tensor) -> Tensor:
        """Forward pass."""
        self.input_cache = x

        if self.phase == TrainingPhase.TRAINING:
            # Compute batch statistics
            mean = x.mean(axis=0)

            # Compute variance
            diff = Tensor([[x.data[i][j] - mean.data[0][j]
                            for j in range(x.shape[1])]
                           for i in range(x.shape[0])], x.shape)
            var = diff.multiply(diff).mean(axis=0)

            # Update running statistics
            for j in range(self.num_features):
                self.running_mean.data[0][j] = (1 - self.momentum) * self.running_mean.data[0][j] + \
                                               self.momentum * mean.data[0][j]
                self.running_var.data[0][j] = (1 - self.momentum) * self.running_var.data[0][j] + \
                                              self.momentum * var.data[0][j]
        else:
            mean = self.running_mean
            var = self.running_var
            diff = Tensor([[x.data[i][j] - mean.data[0][j]
                            for j in range(x.shape[1])]
                           for i in range(x.shape[0])], x.shape)

        # Normalize
        self.std = Tensor([[math.sqrt(var.data[0][j] + self.epsilon)
                            for j in range(var.shape[1])]], (1, var.shape[1]))

        self.x_norm = Tensor([[diff.data[i][j] / self.std.data[0][j]
                               for j in range(x.shape[1])]
                              for i in range(x.shape[0])], x.shape)

        # Scale and shift
        output = Tensor([[self.x_norm.data[i][j] * self.gamma.data[0][j] + self.beta.data[0][j]
                          for j in range(x.shape[1])]
                         for i in range(x.shape[0])], x.shape)

        self.output_cache = output
        return output

    def backward(self, grad: Tensor) -> Tensor:
        """Backward pass."""
        batch_size = grad.shape[0]

        # Gamma gradient
        gamma_grad = Tensor([[sum(grad.data[i][j] * self.x_norm.data[i][j]
                                   for i in range(batch_size))
                              for j in range(grad.shape[1])]], (1, grad.shape[1]))

        # Beta gradient
        beta_grad = grad.sum(axis=0)

        # Input gradient (simplified)
        dx_norm = Tensor([[grad.data[i][j] * self.gamma.data[0][j]
                           for j in range(grad.shape[1])]
                          for i in range(batch_size)], grad.shape)

        dx = Tensor([[dx_norm.data[i][j] / self.std.data[0][j]
                      for j in range(grad.shape[1])]
                     for i in range(batch_size)], grad.shape)

        return dx


# =============================================================================
# OPTIMIZERS
# =============================================================================

class Optimizer(ABC):
    """Abstract optimizer class."""

    def __init__(self, learning_rate: float = 0.001):
        self.learning_rate = learning_rate
        self.iteration = 0

    @abstractmethod
    def update(self, layer: Layer) -> None:
        """Update layer parameters."""
        pass

    def step(self) -> None:
        """Increment iteration counter."""
        self.iteration += 1


class SGDOptimizer(Optimizer):
    """Stochastic Gradient Descent optimizer."""

    def __init__(
        self,
        learning_rate: float = 0.01,
        momentum: float = 0.0,
        weight_decay: float = 0.0
    ):
        super().__init__(learning_rate)
        self.momentum = momentum
        self.weight_decay = weight_decay
        self.velocity: Dict[str, Tensor] = {}

    def update(self, layer: Layer) -> None:
        """Update layer parameters."""
        if not layer.trainable:
            return

        if hasattr(layer, 'weight_grad') and layer.weight_grad is not None:
            key = f"{layer.name}_weights"

            # Apply weight decay
            grad = layer.weight_grad
            if self.weight_decay > 0:
                grad = grad.add(layer.weights.multiply(self.weight_decay))

            # Apply momentum
            if self.momentum > 0:
                if key not in self.velocity:
                    self.velocity[key] = Tensor.zeros(*layer.weights.shape)

                self.velocity[key] = self.velocity[key].multiply(self.momentum).add(
                    grad.multiply(self.learning_rate)
                )
                layer.weights = layer.weights.subtract(self.velocity[key])
            else:
                layer.weights = layer.weights.subtract(grad.multiply(self.learning_rate))

        if hasattr(layer, 'bias_grad') and layer.bias_grad is not None:
            layer.biases = layer.biases.subtract(layer.bias_grad.multiply(self.learning_rate))


class AdamOptimizer(Optimizer):
    """Adam optimizer."""

    def __init__(
        self,
        learning_rate: float = 0.001,
        beta1: float = 0.9,
        beta2: float = 0.999,
        epsilon: float = 1e-8,
        weight_decay: float = 0.0
    ):
        super().__init__(learning_rate)
        self.beta1 = beta1
        self.beta2 = beta2
        self.epsilon = epsilon
        self.weight_decay = weight_decay
        self.m: Dict[str, Tensor] = {}
        self.v: Dict[str, Tensor] = {}

    def update(self, layer: Layer) -> None:
        """Update layer parameters."""
        if not layer.trainable:
            return

        t = self.iteration + 1

        if hasattr(layer, 'weight_grad') and layer.weight_grad is not None:
            key = f"{layer.name}_weights"

            if key not in self.m:
                self.m[key] = Tensor.zeros(*layer.weights.shape)
                self.v[key] = Tensor.zeros(*layer.weights.shape)

            grad = layer.weight_grad
            if self.weight_decay > 0:
                grad = grad.add(layer.weights.multiply(self.weight_decay))

            # Update biased first moment
            self.m[key] = self.m[key].multiply(self.beta1).add(grad.multiply(1 - self.beta1))

            # Update biased second moment
            self.v[key] = self.v[key].multiply(self.beta2).add(
                grad.multiply(grad).multiply(1 - self.beta2)
            )

            # Bias correction
            m_hat = self.m[key].multiply(1 / (1 - self.beta1 ** t))
            v_hat = self.v[key].multiply(1 / (1 - self.beta2 ** t))

            # Update weights
            update = Tensor([[self.learning_rate * m_hat.data[i][j] /
                              (math.sqrt(v_hat.data[i][j]) + self.epsilon)
                              for j in range(m_hat.shape[1])]
                             for i in range(m_hat.shape[0])], m_hat.shape)

            layer.weights = layer.weights.subtract(update)

        if hasattr(layer, 'bias_grad') and layer.bias_grad is not None:
            key = f"{layer.name}_biases"

            if key not in self.m:
                self.m[key] = Tensor.zeros(*layer.biases.shape)
                self.v[key] = Tensor.zeros(*layer.biases.shape)

            grad = layer.bias_grad

            self.m[key] = self.m[key].multiply(self.beta1).add(grad.multiply(1 - self.beta1))
            self.v[key] = self.v[key].multiply(self.beta2).add(
                grad.multiply(grad).multiply(1 - self.beta2)
            )

            m_hat = self.m[key].multiply(1 / (1 - self.beta1 ** t))
            v_hat = self.v[key].multiply(1 / (1 - self.beta2 ** t))

            update = Tensor([[self.learning_rate * m_hat.data[i][j] /
                              (math.sqrt(v_hat.data[i][j]) + self.epsilon)
                              for j in range(m_hat.shape[1])]
                             for i in range(m_hat.shape[0])], m_hat.shape)

            layer.biases = layer.biases.subtract(update)


# =============================================================================
# NEURAL NETWORK MODEL
# =============================================================================

class NeuralNetwork:
    """Neural network model."""

    def __init__(self, name: str = "model"):
        self.name = name
        self.layers: List[Layer] = []
        self.optimizer: Optional[Optimizer] = None
        self.loss_fn: Callable = Loss.mse
        self.loss_type: LossType = LossType.MSE
        self.training_history: List[TrainingMetrics] = []

    def add(self, layer: Layer) -> 'NeuralNetwork':
        """Add a layer."""
        self.layers.append(layer)
        return self

    def compile(
        self,
        optimizer: Optimizer = None,
        loss: LossType = LossType.MSE
    ) -> None:
        """Compile the model."""
        self.optimizer = optimizer or AdamOptimizer()
        self.loss_type = loss
        self.loss_fn = Loss.get_function(loss)

    def forward(self, x: Tensor, training: bool = True) -> Tensor:
        """Forward pass through all layers."""
        phase = TrainingPhase.TRAINING if training else TrainingPhase.INFERENCE

        output = x
        for layer in self.layers:
            layer.phase = phase
            output = layer.forward(output)

        return output

    def backward(self, grad: Tensor) -> None:
        """Backward pass through all layers."""
        for layer in reversed(self.layers):
            grad = layer.backward(grad)

    def train_step(
        self,
        x: Tensor,
        y: Tensor
    ) -> float:
        """Single training step."""
        # Forward pass
        predictions = self.forward(x, training=True)

        # Compute loss
        loss = self.loss_fn(y, predictions)

        # Compute initial gradient
        if self.loss_type == LossType.MSE:
            grad = Loss.mse_derivative(y, predictions)
        else:
            grad = predictions.subtract(y)

        # Backward pass
        self.backward(grad)

        # Update parameters
        for layer in self.layers:
            self.optimizer.update(layer)

        self.optimizer.step()

        return loss

    def fit(
        self,
        x: Tensor,
        y: Tensor,
        epochs: int = 100,
        batch_size: int = 32,
        validation_data: Tuple[Tensor, Tensor] = None,
        verbose: bool = True
    ) -> List[TrainingMetrics]:
        """Train the model."""
        n_samples = x.shape[0]

        for epoch in range(epochs):
            start_time = datetime.now()
            epoch_loss = 0.0
            n_batches = 0

            # Shuffle indices
            indices = list(range(n_samples))
            random.shuffle(indices)

            # Mini-batch training
            for i in range(0, n_samples, batch_size):
                batch_indices = indices[i:i + batch_size]

                # Create batch
                x_batch = Tensor([x.data[j] for j in batch_indices], (len(batch_indices), x.shape[1]))
                y_batch = Tensor([y.data[j] for j in batch_indices], (len(batch_indices), y.shape[1]))

                # Train step
                loss = self.train_step(x_batch, y_batch)
                epoch_loss += loss
                n_batches += 1

            avg_loss = epoch_loss / n_batches

            # Validation
            val_loss = None
            if validation_data:
                x_val, y_val = validation_data
                predictions = self.forward(x_val, training=False)
                val_loss = self.loss_fn(y_val, predictions)

            duration = (datetime.now() - start_time).total_seconds() * 1000

            metrics = TrainingMetrics(
                epoch=epoch + 1,
                loss=avg_loss,
                val_loss=val_loss,
                learning_rate=self.optimizer.learning_rate,
                duration_ms=duration
            )
            self.training_history.append(metrics)

            if verbose and (epoch + 1) % 10 == 0:
                val_str = f", val_loss: {val_loss:.6f}" if val_loss else ""
                print(f"Epoch {epoch + 1}/{epochs} - loss: {avg_loss:.6f}{val_str}")

        return self.training_history

    def predict(self, x: Tensor) -> Tensor:
        """Make predictions."""
        return self.forward(x, training=False)

    def evaluate(self, x: Tensor, y: Tensor) -> float:
        """Evaluate model."""
        predictions = self.predict(x)
        return self.loss_fn(y, predictions)

    def summary(self) -> str:
        """Get model summary."""
        lines = [
            f"Model: {self.name}",
            "=" * 50,
            f"{'Layer':<20} {'Output Shape':<15} {'Params':<10}",
            "-" * 50
        ]

        total_params = 0
        for layer in self.layers:
            params = 0
            output_shape = "N/A"

            if hasattr(layer, 'weights') and layer.weights is not None:
                params += layer.weights.shape[0] * layer.weights.shape[1]
                output_shape = str(layer.weights.shape[1])

            if hasattr(layer, 'biases') and layer.biases is not None:
                params += layer.biases.shape[1]

            total_params += params
            lines.append(f"{layer.name:<20} {output_shape:<15} {params:<10}")

        lines.append("-" * 50)
        lines.append(f"Total parameters: {total_params}")

        return "\n".join(lines)

    def save(self, path: str) -> None:
        """Save model."""
        state = {
            "name": self.name,
            "layers": []
        }

        for layer in self.layers:
            layer_state = {
                "name": layer.name,
                "type": type(layer).__name__,
                "params": {}
            }

            if layer.weights is not None:
                layer_state["params"]["weights"] = {
                    "data": layer.weights.data,
                    "shape": layer.weights.shape
                }

            if layer.biases is not None:
                layer_state["params"]["biases"] = {
                    "data": layer.biases.data,
                    "shape": layer.biases.shape
                }

            state["layers"].append(layer_state)

        with open(path, 'wb') as f:
            pickle.dump(state, f)

    def load(self, path: str) -> None:
        """Load model."""
        with open(path, 'rb') as f:
            state = pickle.load(f)

        self.name = state["name"]

        for layer, layer_state in zip(self.layers, state["layers"]):
            if "weights" in layer_state["params"]:
                w = layer_state["params"]["weights"]
                layer.weights = Tensor(w["data"], w["shape"])

            if "biases" in layer_state["params"]:
                b = layer_state["params"]["biases"]
                layer.biases = Tensor(b["data"], b["shape"])


# =============================================================================
# NEURAL NETWORK MANAGER
# =============================================================================

class NeuralNetworkManager:
    """
    Master neural network management system for BAEL.

    Provides model building, training, and deployment capabilities.
    """

    def __init__(self):
        self.models: Dict[str, NeuralNetwork] = {}
        self.configs: Dict[str, ModelConfig] = {}
        self.ensemble_models: Dict[str, List[str]] = {}

    def create_model(
        self,
        name: str,
        layers: List[Dict[str, Any]],
        optimizer: OptimizerType = OptimizerType.ADAM,
        loss: LossType = LossType.MSE,
        learning_rate: float = 0.001
    ) -> NeuralNetwork:
        """Create a neural network model."""
        model = NeuralNetwork(name)

        for layer_config in layers:
            layer_type = layer_config.get("type", "dense")

            if layer_type == "dense":
                layer = DenseLayer(
                    input_size=layer_config["input_size"],
                    output_size=layer_config["output_size"],
                    activation=ActivationType(layer_config.get("activation", "relu")),
                    name=layer_config.get("name")
                )
            elif layer_type == "dropout":
                layer = DropoutLayer(
                    rate=layer_config.get("rate", 0.5),
                    name=layer_config.get("name")
                )
            elif layer_type == "batch_norm":
                layer = BatchNormLayer(
                    num_features=layer_config["num_features"],
                    name=layer_config.get("name")
                )
            else:
                continue

            model.add(layer)

        # Create optimizer
        if optimizer == OptimizerType.ADAM:
            opt = AdamOptimizer(learning_rate)
        elif optimizer == OptimizerType.SGD:
            opt = SGDOptimizer(learning_rate)
        else:
            opt = AdamOptimizer(learning_rate)

        model.compile(opt, loss)

        self.models[name] = model
        return model

    def create_mlp(
        self,
        name: str,
        input_size: int,
        hidden_sizes: List[int],
        output_size: int,
        activation: ActivationType = ActivationType.RELU,
        output_activation: ActivationType = ActivationType.LINEAR,
        dropout: float = 0.0
    ) -> NeuralNetwork:
        """Create a multilayer perceptron."""
        layers = []
        prev_size = input_size

        for i, hidden_size in enumerate(hidden_sizes):
            layers.append({
                "type": "dense",
                "input_size": prev_size,
                "output_size": hidden_size,
                "activation": activation.value,
                "name": f"hidden_{i}"
            })

            if dropout > 0:
                layers.append({
                    "type": "dropout",
                    "rate": dropout,
                    "name": f"dropout_{i}"
                })

            prev_size = hidden_size

        layers.append({
            "type": "dense",
            "input_size": prev_size,
            "output_size": output_size,
            "activation": output_activation.value,
            "name": "output"
        })

        return self.create_model(name, layers)

    def create_autoencoder(
        self,
        name: str,
        input_size: int,
        encoding_sizes: List[int],
        latent_size: int
    ) -> NeuralNetwork:
        """Create an autoencoder."""
        layers = []
        prev_size = input_size

        # Encoder
        for i, size in enumerate(encoding_sizes):
            layers.append({
                "type": "dense",
                "input_size": prev_size,
                "output_size": size,
                "activation": "relu",
                "name": f"encoder_{i}"
            })
            prev_size = size

        # Latent
        layers.append({
            "type": "dense",
            "input_size": prev_size,
            "output_size": latent_size,
            "activation": "relu",
            "name": "latent"
        })
        prev_size = latent_size

        # Decoder
        for i, size in enumerate(reversed(encoding_sizes)):
            layers.append({
                "type": "dense",
                "input_size": prev_size,
                "output_size": size,
                "activation": "relu",
                "name": f"decoder_{i}"
            })
            prev_size = size

        # Output
        layers.append({
            "type": "dense",
            "input_size": prev_size,
            "output_size": input_size,
            "activation": "sigmoid",
            "name": "output"
        })

        return self.create_model(name, layers)

    def create_ensemble(
        self,
        name: str,
        model_names: List[str]
    ) -> None:
        """Create an ensemble of models."""
        for model_name in model_names:
            if model_name not in self.models:
                raise ValueError(f"Model {model_name} not found")

        self.ensemble_models[name] = model_names

    def ensemble_predict(
        self,
        ensemble_name: str,
        x: Tensor,
        method: str = "average"
    ) -> Tensor:
        """Make ensemble predictions."""
        if ensemble_name not in self.ensemble_models:
            raise ValueError(f"Ensemble {ensemble_name} not found")

        predictions = []
        for model_name in self.ensemble_models[ensemble_name]:
            pred = self.models[model_name].predict(x)
            predictions.append(pred)

        if method == "average":
            result = predictions[0]
            for pred in predictions[1:]:
                result = result.add(pred)
            result = result.multiply(1.0 / len(predictions))
            return result
        elif method == "vote":
            # Majority voting (for classification)
            pass

        return predictions[0]

    def get_model(self, name: str) -> Optional[NeuralNetwork]:
        """Get a model by name."""
        return self.models.get(name)

    def list_models(self) -> List[str]:
        """List all models."""
        return list(self.models.keys())

    def delete_model(self, name: str) -> bool:
        """Delete a model."""
        if name in self.models:
            del self.models[name]
            return True
        return False

    def get_statistics(self) -> Dict[str, Any]:
        """Get manager statistics."""
        total_params = 0
        for model in self.models.values():
            for layer in model.layers:
                if hasattr(layer, 'weights') and layer.weights is not None:
                    total_params += layer.weights.shape[0] * layer.weights.shape[1]
                if hasattr(layer, 'biases') and layer.biases is not None:
                    total_params += layer.biases.shape[1]

        return {
            "total_models": len(self.models),
            "total_ensembles": len(self.ensemble_models),
            "total_parameters": total_params
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Neural Network Manager."""
    print("=" * 70)
    print("BAEL - NEURAL NETWORK MANAGER DEMO")
    print("Pure Python Neural Networks")
    print("=" * 70)
    print()

    manager = NeuralNetworkManager()

    # 1. Create MLP for XOR problem
    print("1. XOR PROBLEM (MLP):")
    print("-" * 40)

    model = manager.create_mlp(
        name="xor_model",
        input_size=2,
        hidden_sizes=[8, 4],
        output_size=1,
        activation=ActivationType.TANH,
        output_activation=ActivationType.SIGMOID
    )

    print(model.summary())
    print()

    # Training data
    x_train = Tensor([[0, 0], [0, 1], [1, 0], [1, 1]], (4, 2))
    y_train = Tensor([[0], [1], [1], [0]], (4, 1))

    print("Training on XOR data...")
    model.fit(x_train, y_train, epochs=500, batch_size=4, verbose=False)

    predictions = model.predict(x_train)
    print("Predictions after training:")
    for i in range(4):
        print(f"   {x_train.data[i]} -> {predictions.data[i][0]:.4f} (expected: {y_train.data[i][0]})")
    print()

    # 2. Create autoencoder
    print("2. AUTOENCODER:")
    print("-" * 40)

    autoencoder = manager.create_autoencoder(
        name="autoencoder",
        input_size=8,
        encoding_sizes=[6, 4],
        latent_size=2
    )

    print(f"   Layers: {len(autoencoder.layers)}")
    print(f"   Latent dimension: 2")
    print()

    # 3. Custom model with dropout
    print("3. CUSTOM MODEL WITH DROPOUT:")
    print("-" * 40)

    custom = manager.create_model(
        name="custom_model",
        layers=[
            {"type": "dense", "input_size": 10, "output_size": 32, "activation": "relu"},
            {"type": "batch_norm", "num_features": 32},
            {"type": "dropout", "rate": 0.3},
            {"type": "dense", "input_size": 32, "output_size": 16, "activation": "relu"},
            {"type": "dropout", "rate": 0.2},
            {"type": "dense", "input_size": 16, "output_size": 2, "activation": "softmax"}
        ],
        optimizer=OptimizerType.ADAM,
        loss=LossType.CATEGORICAL_CROSSENTROPY,
        learning_rate=0.001
    )

    print(custom.summary())
    print()

    # 4. Ensemble
    print("4. MODEL ENSEMBLE:")
    print("-" * 40)

    # Create multiple models
    for i in range(3):
        manager.create_mlp(
            name=f"ensemble_member_{i}",
            input_size=2,
            hidden_sizes=[4],
            output_size=1
        )

    manager.create_ensemble(
        name="xor_ensemble",
        model_names=[f"ensemble_member_{i}" for i in range(3)]
    )

    print(f"   Created ensemble with {len(manager.ensemble_models['xor_ensemble'])} members")
    print()

    # 5. Statistics
    print("5. MANAGER STATISTICS:")
    print("-" * 40)

    stats = manager.get_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()

    # 6. Model list
    print("6. ALL MODELS:")
    print("-" * 40)

    for model_name in manager.list_models():
        print(f"   - {model_name}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Neural Network Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
