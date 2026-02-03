#!/usr/bin/env python3
"""
BAEL - Neural Engine
Neural network concepts and building blocks for AI agents.

Features:
- Neurons and layers
- Activation functions
- Forward propagation
- Backpropagation concepts
- Layer types (Dense, Dropout)
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
    SIGMOID = "sigmoid"
    TANH = "tanh"
    LEAKY_RELU = "leaky_relu"
    ELU = "elu"
    SOFTMAX = "softmax"
    LINEAR = "linear"
    GELU = "gelu"
    SWISH = "swish"


class LayerType(Enum):
    """Layer types."""
    DENSE = "dense"
    DROPOUT = "dropout"
    BATCH_NORM = "batch_norm"
    LAYER_NORM = "layer_norm"
    EMBEDDING = "embedding"


class InitializationType(Enum):
    """Weight initialization types."""
    XAVIER = "xavier"
    HE = "he"
    UNIFORM = "uniform"
    NORMAL = "normal"
    ZEROS = "zeros"


class LossType(Enum):
    """Loss function types."""
    MSE = "mse"
    MAE = "mae"
    CROSS_ENTROPY = "cross_entropy"
    BINARY_CROSS_ENTROPY = "binary_cross_entropy"
    HUBER = "huber"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Neuron:
    """A single neuron."""
    neuron_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    weights: List[float] = field(default_factory=list)
    bias: float = 0.0
    output: float = 0.0
    gradient: float = 0.0


@dataclass
class LayerConfig:
    """Layer configuration."""
    layer_type: LayerType = LayerType.DENSE
    input_size: int = 0
    output_size: int = 0
    activation: ActivationType = ActivationType.RELU
    dropout_rate: float = 0.0


@dataclass
class ForwardResult:
    """Result of forward pass."""
    outputs: List[List[float]] = field(default_factory=list)
    activations: List[List[float]] = field(default_factory=list)


@dataclass
class GradientResult:
    """Result of gradient computation."""
    weight_gradients: List[List[List[float]]] = field(default_factory=list)
    bias_gradients: List[List[float]] = field(default_factory=list)


@dataclass
class TrainingMetrics:
    """Training metrics."""
    epoch: int = 0
    loss: float = 0.0
    accuracy: float = 0.0


# =============================================================================
# ACTIVATION FUNCTIONS
# =============================================================================

class ActivationFunctions:
    """Collection of activation functions."""

    @staticmethod
    def relu(x: float) -> float:
        """ReLU activation."""
        return max(0.0, x)

    @staticmethod
    def relu_derivative(x: float) -> float:
        """ReLU derivative."""
        return 1.0 if x > 0 else 0.0

    @staticmethod
    def sigmoid(x: float) -> float:
        """Sigmoid activation."""
        x = max(-500, min(500, x))
        return 1.0 / (1.0 + math.exp(-x))

    @staticmethod
    def sigmoid_derivative(x: float) -> float:
        """Sigmoid derivative."""
        s = ActivationFunctions.sigmoid(x)
        return s * (1 - s)

    @staticmethod
    def tanh(x: float) -> float:
        """Tanh activation."""
        return math.tanh(x)

    @staticmethod
    def tanh_derivative(x: float) -> float:
        """Tanh derivative."""
        t = math.tanh(x)
        return 1 - t ** 2

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
    def elu_derivative(x: float, alpha: float = 1.0) -> float:
        """ELU derivative."""
        return 1.0 if x > 0 else alpha * math.exp(x)

    @staticmethod
    def softmax(values: List[float]) -> List[float]:
        """Softmax activation."""
        if not values:
            return []

        max_val = max(values)
        exp_vals = [math.exp(v - max_val) for v in values]
        total = sum(exp_vals)

        if total == 0:
            return [1.0 / len(values)] * len(values)

        return [e / total for e in exp_vals]

    @staticmethod
    def gelu(x: float) -> float:
        """GELU activation (approximation)."""
        return 0.5 * x * (1 + math.tanh(math.sqrt(2 / math.pi) * (x + 0.044715 * x ** 3)))

    @staticmethod
    def swish(x: float, beta: float = 1.0) -> float:
        """Swish activation."""
        return x * ActivationFunctions.sigmoid(beta * x)

    @staticmethod
    def apply(x: float, activation: ActivationType) -> float:
        """Apply activation function."""
        if activation == ActivationType.RELU:
            return ActivationFunctions.relu(x)
        elif activation == ActivationType.SIGMOID:
            return ActivationFunctions.sigmoid(x)
        elif activation == ActivationType.TANH:
            return ActivationFunctions.tanh(x)
        elif activation == ActivationType.LEAKY_RELU:
            return ActivationFunctions.leaky_relu(x)
        elif activation == ActivationType.ELU:
            return ActivationFunctions.elu(x)
        elif activation == ActivationType.GELU:
            return ActivationFunctions.gelu(x)
        elif activation == ActivationType.SWISH:
            return ActivationFunctions.swish(x)
        elif activation == ActivationType.LINEAR:
            return x
        return x


# =============================================================================
# LOSS FUNCTIONS
# =============================================================================

class LossFunctions:
    """Collection of loss functions."""

    @staticmethod
    def mse(predictions: List[float], targets: List[float]) -> float:
        """Mean Squared Error."""
        if len(predictions) != len(targets):
            return 0.0

        n = len(predictions)
        if n == 0:
            return 0.0

        return sum((p - t) ** 2 for p, t in zip(predictions, targets)) / n

    @staticmethod
    def mae(predictions: List[float], targets: List[float]) -> float:
        """Mean Absolute Error."""
        if len(predictions) != len(targets):
            return 0.0

        n = len(predictions)
        if n == 0:
            return 0.0

        return sum(abs(p - t) for p, t in zip(predictions, targets)) / n

    @staticmethod
    def binary_cross_entropy(
        predictions: List[float],
        targets: List[float],
        epsilon: float = 1e-15
    ) -> float:
        """Binary Cross Entropy."""
        if len(predictions) != len(targets):
            return 0.0

        n = len(predictions)
        if n == 0:
            return 0.0

        total = 0.0
        for p, t in zip(predictions, targets):
            p = max(epsilon, min(1 - epsilon, p))
            total += t * math.log(p) + (1 - t) * math.log(1 - p)

        return -total / n

    @staticmethod
    def cross_entropy(
        predictions: List[float],
        targets: List[float],
        epsilon: float = 1e-15
    ) -> float:
        """Cross Entropy."""
        if len(predictions) != len(targets):
            return 0.0

        total = 0.0
        for p, t in zip(predictions, targets):
            if t > 0:
                p = max(epsilon, p)
                total += t * math.log(p)

        return -total

    @staticmethod
    def huber(
        predictions: List[float],
        targets: List[float],
        delta: float = 1.0
    ) -> float:
        """Huber Loss."""
        if len(predictions) != len(targets):
            return 0.0

        n = len(predictions)
        if n == 0:
            return 0.0

        total = 0.0
        for p, t in zip(predictions, targets):
            error = abs(p - t)
            if error <= delta:
                total += 0.5 * error ** 2
            else:
                total += delta * error - 0.5 * delta ** 2

        return total / n


# =============================================================================
# WEIGHT INITIALIZER
# =============================================================================

class WeightInitializer:
    """Initialize weights."""

    @staticmethod
    def xavier(fan_in: int, fan_out: int) -> List[float]:
        """Xavier/Glorot initialization."""
        std = math.sqrt(2.0 / (fan_in + fan_out))
        return [random.gauss(0, std) for _ in range(fan_in)]

    @staticmethod
    def he(fan_in: int) -> List[float]:
        """He initialization."""
        std = math.sqrt(2.0 / fan_in)
        return [random.gauss(0, std) for _ in range(fan_in)]

    @staticmethod
    def uniform(fan_in: int, low: float = -0.1, high: float = 0.1) -> List[float]:
        """Uniform initialization."""
        return [random.uniform(low, high) for _ in range(fan_in)]

    @staticmethod
    def normal(fan_in: int, mean: float = 0.0, std: float = 0.01) -> List[float]:
        """Normal initialization."""
        return [random.gauss(mean, std) for _ in range(fan_in)]

    @staticmethod
    def zeros(fan_in: int) -> List[float]:
        """Zero initialization."""
        return [0.0] * fan_in

    @staticmethod
    def initialize(
        fan_in: int,
        fan_out: int,
        method: InitializationType = InitializationType.XAVIER
    ) -> List[float]:
        """Initialize weights using specified method."""
        if method == InitializationType.XAVIER:
            return WeightInitializer.xavier(fan_in, fan_out)
        elif method == InitializationType.HE:
            return WeightInitializer.he(fan_in)
        elif method == InitializationType.UNIFORM:
            return WeightInitializer.uniform(fan_in)
        elif method == InitializationType.NORMAL:
            return WeightInitializer.normal(fan_in)
        elif method == InitializationType.ZEROS:
            return WeightInitializer.zeros(fan_in)
        return WeightInitializer.xavier(fan_in, fan_out)


# =============================================================================
# LAYER BASE
# =============================================================================

class Layer(ABC):
    """Abstract base layer."""

    @abstractmethod
    def forward(self, inputs: List[List[float]]) -> List[List[float]]:
        """Forward pass."""
        pass

    @abstractmethod
    def backward(
        self,
        gradients: List[List[float]]
    ) -> Tuple[List[List[float]], List[List[List[float]]], List[List[float]]]:
        """Backward pass returning (input gradients, weight gradients, bias gradients)."""
        pass


# =============================================================================
# DENSE LAYER
# =============================================================================

class DenseLayer(Layer):
    """Fully connected layer."""

    def __init__(
        self,
        input_size: int,
        output_size: int,
        activation: ActivationType = ActivationType.RELU,
        init_method: InitializationType = InitializationType.XAVIER
    ):
        self._input_size = input_size
        self._output_size = output_size
        self._activation = activation

        self._weights = [
            WeightInitializer.initialize(input_size, output_size, init_method)
            for _ in range(output_size)
        ]
        self._biases = [0.0] * output_size

        self._last_input: List[List[float]] = []
        self._last_pre_activation: List[List[float]] = []

    def forward(self, inputs: List[List[float]]) -> List[List[float]]:
        """Forward pass."""
        self._last_input = inputs

        outputs = []
        pre_activations = []

        for input_vec in inputs:
            pre_act = []
            out = []

            for j in range(self._output_size):
                z = self._biases[j]
                for i, inp in enumerate(input_vec):
                    z += self._weights[j][i] * inp
                pre_act.append(z)

                if self._activation == ActivationType.SOFTMAX:
                    out.append(z)
                else:
                    out.append(ActivationFunctions.apply(z, self._activation))

            if self._activation == ActivationType.SOFTMAX:
                out = ActivationFunctions.softmax(pre_act)

            pre_activations.append(pre_act)
            outputs.append(out)

        self._last_pre_activation = pre_activations
        return outputs

    def backward(
        self,
        gradients: List[List[float]]
    ) -> Tuple[List[List[float]], List[List[List[float]]], List[List[float]]]:
        """Backward pass."""
        batch_size = len(gradients)

        input_gradients = []
        weight_gradients = [[0.0] * self._input_size for _ in range(self._output_size)]
        bias_gradients = [0.0] * self._output_size

        for b, grad in enumerate(gradients):
            input_grad = [0.0] * self._input_size

            for j in range(self._output_size):
                if self._activation == ActivationType.RELU:
                    d_act = ActivationFunctions.relu_derivative(self._last_pre_activation[b][j])
                elif self._activation == ActivationType.SIGMOID:
                    d_act = ActivationFunctions.sigmoid_derivative(self._last_pre_activation[b][j])
                elif self._activation == ActivationType.TANH:
                    d_act = ActivationFunctions.tanh_derivative(self._last_pre_activation[b][j])
                else:
                    d_act = 1.0

                delta = grad[j] * d_act

                bias_gradients[j] += delta

                for i in range(self._input_size):
                    weight_gradients[j][i] += delta * self._last_input[b][i]
                    input_grad[i] += delta * self._weights[j][i]

            input_gradients.append(input_grad)

        weight_gradients = [[w / batch_size for w in wg] for wg in weight_gradients]
        bias_gradients = [b / batch_size for b in bias_gradients]

        return input_gradients, weight_gradients, [bias_gradients]

    def get_weights(self) -> List[List[float]]:
        """Get weights."""
        return self._weights

    def set_weights(self, weights: List[List[float]]) -> None:
        """Set weights."""
        self._weights = weights

    def get_biases(self) -> List[float]:
        """Get biases."""
        return self._biases

    def set_biases(self, biases: List[float]) -> None:
        """Set biases."""
        self._biases = biases


# =============================================================================
# DROPOUT LAYER
# =============================================================================

class DropoutLayer(Layer):
    """Dropout regularization layer."""

    def __init__(self, rate: float = 0.5):
        self._rate = rate
        self._training = True
        self._mask: List[List[float]] = []

    def set_training(self, training: bool) -> None:
        """Set training mode."""
        self._training = training

    def forward(self, inputs: List[List[float]]) -> List[List[float]]:
        """Forward pass."""
        if not self._training or self._rate == 0:
            return inputs

        outputs = []
        self._mask = []

        scale = 1.0 / (1.0 - self._rate)

        for input_vec in inputs:
            mask = [1.0 if random.random() > self._rate else 0.0 for _ in input_vec]
            output = [v * m * scale for v, m in zip(input_vec, mask)]
            outputs.append(output)
            self._mask.append(mask)

        return outputs

    def backward(
        self,
        gradients: List[List[float]]
    ) -> Tuple[List[List[float]], List[List[List[float]]], List[List[float]]]:
        """Backward pass."""
        if not self._training or self._rate == 0:
            return gradients, [], []

        scale = 1.0 / (1.0 - self._rate)
        input_gradients = [
            [g * m * scale for g, m in zip(grad, mask)]
            for grad, mask in zip(gradients, self._mask)
        ]

        return input_gradients, [], []


# =============================================================================
# LAYER NORMALIZATION
# =============================================================================

class LayerNormalization(Layer):
    """Layer normalization."""

    def __init__(self, size: int, epsilon: float = 1e-6):
        self._size = size
        self._epsilon = epsilon
        self._gamma = [1.0] * size
        self._beta = [0.0] * size

        self._last_input: List[List[float]] = []
        self._last_normalized: List[List[float]] = []
        self._last_std: List[float] = []

    def forward(self, inputs: List[List[float]]) -> List[List[float]]:
        """Forward pass."""
        self._last_input = inputs
        outputs = []
        self._last_normalized = []
        self._last_std = []

        for input_vec in inputs:
            mean = sum(input_vec) / len(input_vec)
            variance = sum((x - mean) ** 2 for x in input_vec) / len(input_vec)
            std = math.sqrt(variance + self._epsilon)

            normalized = [(x - mean) / std for x in input_vec]
            output = [g * n + b for g, n, b in zip(self._gamma, normalized, self._beta)]

            outputs.append(output)
            self._last_normalized.append(normalized)
            self._last_std.append(std)

        return outputs

    def backward(
        self,
        gradients: List[List[float]]
    ) -> Tuple[List[List[float]], List[List[List[float]]], List[List[float]]]:
        """Backward pass (simplified)."""
        return gradients, [], []


# =============================================================================
# NEURAL NETWORK
# =============================================================================

class NeuralNetwork:
    """Simple neural network."""

    def __init__(self):
        self._layers: List[Layer] = []

    def add_layer(self, layer: Layer) -> None:
        """Add a layer."""
        self._layers.append(layer)

    def forward(self, inputs: List[List[float]]) -> List[List[float]]:
        """Forward pass through all layers."""
        x = inputs
        for layer in self._layers:
            x = layer.forward(x)
        return x

    def backward(self, loss_gradients: List[List[float]]) -> None:
        """Backward pass through all layers."""
        gradients = loss_gradients
        for layer in reversed(self._layers):
            gradients, _, _ = layer.backward(gradients)

    def predict(self, inputs: List[List[float]]) -> List[List[float]]:
        """Make predictions."""
        for layer in self._layers:
            if isinstance(layer, DropoutLayer):
                layer.set_training(False)

        outputs = self.forward(inputs)

        for layer in self._layers:
            if isinstance(layer, DropoutLayer):
                layer.set_training(True)

        return outputs


# =============================================================================
# NEURAL ENGINE
# =============================================================================

class NeuralEngine:
    """
    Neural Engine for BAEL.

    Neural network building blocks for AI agents.
    """

    def __init__(self):
        self._networks: Dict[str, NeuralNetwork] = {}
        self._activation_funcs = ActivationFunctions()
        self._loss_funcs = LossFunctions()
        self._initializer = WeightInitializer()

    def create_network(self, name: str) -> NeuralNetwork:
        """Create a new network."""
        network = NeuralNetwork()
        self._networks[name] = network
        return network

    def get_network(self, name: str) -> Optional[NeuralNetwork]:
        """Get a network by name."""
        return self._networks.get(name)

    def create_dense_layer(
        self,
        input_size: int,
        output_size: int,
        activation: ActivationType = ActivationType.RELU,
        init_method: InitializationType = InitializationType.XAVIER
    ) -> DenseLayer:
        """Create a dense layer."""
        return DenseLayer(input_size, output_size, activation, init_method)

    def create_dropout_layer(self, rate: float = 0.5) -> DropoutLayer:
        """Create a dropout layer."""
        return DropoutLayer(rate)

    def create_layer_norm(
        self,
        size: int,
        epsilon: float = 1e-6
    ) -> LayerNormalization:
        """Create layer normalization."""
        return LayerNormalization(size, epsilon)

    def compute_loss(
        self,
        predictions: List[float],
        targets: List[float],
        loss_type: LossType = LossType.MSE
    ) -> float:
        """Compute loss."""
        if loss_type == LossType.MSE:
            return self._loss_funcs.mse(predictions, targets)
        elif loss_type == LossType.MAE:
            return self._loss_funcs.mae(predictions, targets)
        elif loss_type == LossType.CROSS_ENTROPY:
            return self._loss_funcs.cross_entropy(predictions, targets)
        elif loss_type == LossType.BINARY_CROSS_ENTROPY:
            return self._loss_funcs.binary_cross_entropy(predictions, targets)
        elif loss_type == LossType.HUBER:
            return self._loss_funcs.huber(predictions, targets)
        return 0.0

    def apply_activation(
        self,
        value: float,
        activation: ActivationType
    ) -> float:
        """Apply activation function."""
        return self._activation_funcs.apply(value, activation)

    def softmax(self, values: List[float]) -> List[float]:
        """Apply softmax."""
        return self._activation_funcs.softmax(values)

    def initialize_weights(
        self,
        fan_in: int,
        fan_out: int,
        method: InitializationType = InitializationType.XAVIER
    ) -> List[float]:
        """Initialize weights."""
        return self._initializer.initialize(fan_in, fan_out, method)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Neural Engine."""
    print("=" * 70)
    print("BAEL - NEURAL ENGINE DEMO")
    print("Neural Network Building Blocks for AI Agents")
    print("=" * 70)
    print()

    engine = NeuralEngine()

    # 1. Activation Functions
    print("1. ACTIVATION FUNCTIONS:")
    print("-" * 40)

    test_values = [-2.0, -1.0, 0.0, 1.0, 2.0]

    for activation in [ActivationType.RELU, ActivationType.SIGMOID, ActivationType.TANH]:
        outputs = [engine.apply_activation(v, activation) for v in test_values]
        print(f"   {activation.value}: {[f'{o:.3f}' for o in outputs]}")
    print()

    # 2. Softmax
    print("2. SOFTMAX:")
    print("-" * 40)

    logits = [2.0, 1.0, 0.5, -1.0]
    probs = engine.softmax(logits)
    print(f"   Logits: {logits}")
    print(f"   Probabilities: {[f'{p:.3f}' for p in probs]}")
    print(f"   Sum: {sum(probs):.3f}")
    print()

    # 3. Loss Functions
    print("3. LOSS FUNCTIONS:")
    print("-" * 40)

    predictions = [0.9, 0.1, 0.8]
    targets = [1.0, 0.0, 1.0]

    for loss_type in [LossType.MSE, LossType.MAE, LossType.BINARY_CROSS_ENTROPY]:
        loss = engine.compute_loss(predictions, targets, loss_type)
        print(f"   {loss_type.value}: {loss:.4f}")
    print()

    # 4. Weight Initialization
    print("4. WEIGHT INITIALIZATION:")
    print("-" * 40)

    for method in InitializationType:
        weights = engine.initialize_weights(5, 3, method)
        mean = sum(weights) / len(weights)
        std = math.sqrt(sum((w - mean) ** 2 for w in weights) / len(weights))
        print(f"   {method.value}: mean={mean:.4f}, std={std:.4f}")
    print()

    # 5. Create Network
    print("5. CREATE NEURAL NETWORK:")
    print("-" * 40)

    network = engine.create_network("demo_network")

    network.add_layer(engine.create_dense_layer(4, 8, ActivationType.RELU))
    network.add_layer(engine.create_dropout_layer(0.2))
    network.add_layer(engine.create_dense_layer(8, 4, ActivationType.RELU))
    network.add_layer(engine.create_dense_layer(4, 2, ActivationType.SOFTMAX))

    print(f"   Created network with {len(network._layers)} layers")
    print(f"   Architecture: 4 -> 8 (ReLU) -> Dropout -> 4 (ReLU) -> 2 (Softmax)")
    print()

    # 6. Forward Pass
    print("6. FORWARD PASS:")
    print("-" * 40)

    batch = [
        [1.0, 0.5, -0.5, 0.0],
        [0.0, 1.0, 0.5, -0.5],
        [-0.5, 0.0, 1.0, 0.5]
    ]

    outputs = network.predict(batch)

    print(f"   Input batch size: {len(batch)}")
    print(f"   Output shape: {len(outputs)}x{len(outputs[0])}")
    print(f"   Sample outputs (probabilities):")
    for i, out in enumerate(outputs):
        print(f"      Sample {i}: {[f'{o:.3f}' for o in out]}")
    print()

    # 7. Dense Layer Details
    print("7. DENSE LAYER DETAILS:")
    print("-" * 40)

    dense = engine.create_dense_layer(3, 2, ActivationType.SIGMOID)
    input_data = [[1.0, 0.5, -0.5]]
    output = dense.forward(input_data)

    print(f"   Input: {input_data[0]}")
    print(f"   Output: {[f'{o:.3f}' for o in output[0]]}")
    print(f"   Weights shape: {len(dense.get_weights())}x{len(dense.get_weights()[0])}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Neural Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
