"""
BAEL Predictive Processing Engine
==================================

Hierarchical predictive coding and error minimization.

"Ba'el predicts to perceive." — Ba'el
"""

import logging
import threading
import time
import math
import random
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod
import copy

logger = logging.getLogger("BAEL.PredictiveProcessing")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class LayerType(Enum):
    """Types of processing layers."""
    SENSORY = auto()        # Bottom level
    FEATURE = auto()        # Feature extraction
    OBJECT = auto()         # Object recognition
    SEMANTIC = auto()       # Semantic meaning
    ABSTRACT = auto()       # Abstract concepts
    META = auto()           # Meta-cognitive


@dataclass
class Prediction:
    """
    A prediction about sensory input.
    """
    id: str
    content: Any
    confidence: float = 0.5
    precision: float = 1.0        # Inverse variance
    source_layer: str = ""
    target_layer: str = ""
    timestamp: float = field(default_factory=time.time)

    @property
    def weighted_confidence(self) -> float:
        return self.confidence * self.precision


@dataclass
class PredictionError:
    """
    Error between prediction and actual input.
    """
    id: str
    prediction_id: str
    predicted: Any
    actual: Any
    error_magnitude: float
    precision: float = 1.0
    timestamp: float = field(default_factory=time.time)

    @property
    def weighted_error(self) -> float:
        return self.error_magnitude * self.precision


@dataclass
class ProcessingUnit:
    """
    A unit in the predictive hierarchy.
    """
    id: str
    layer: LayerType
    state: Any = None
    prediction_precision: float = 1.0
    error_precision: float = 1.0
    learning_rate: float = 0.1


# ============================================================================
# HIERARCHICAL LAYER
# ============================================================================

class PredictiveLayer:
    """
    A layer in the predictive hierarchy.

    "Ba'el predicts at every level." — Ba'el
    """

    def __init__(
        self,
        name: str,
        layer_type: LayerType,
        state_size: int = 10
    ):
        """Initialize layer."""
        self._name = name
        self._type = layer_type
        self._state = [0.0] * state_size
        self._predictions: List[Prediction] = []
        self._errors: List[PredictionError] = []
        self._learning_rate = 0.1
        self._precision = 1.0
        self._lock = threading.RLock()

    @property
    def name(self) -> str:
        return self._name

    @property
    def layer_type(self) -> LayerType:
        return self._type

    @property
    def state(self) -> List[float]:
        return self._state.copy()

    def predict_down(self, target_size: int) -> Prediction:
        """Generate prediction for lower layer."""
        with self._lock:
            # Simple linear projection
            predicted = []
            for i in range(target_size):
                idx = i % len(self._state)
                predicted.append(self._state[idx] * 0.9)

            pred = Prediction(
                id=f"pred_{self._name}_{time.time()}",
                content=predicted,
                confidence=0.8,
                precision=self._precision,
                source_layer=self._name
            )
            self._predictions.append(pred)

            return pred

    def receive_error(self, error: PredictionError) -> None:
        """Receive prediction error from lower layer."""
        with self._lock:
            self._errors.append(error)

            # Update state based on error
            self._update_state(error)

    def _update_state(self, error: PredictionError) -> None:
        """Update internal state based on error."""
        if isinstance(error.actual, list) and len(error.actual) == len(self._state):
            # Gradient-like update
            for i in range(len(self._state)):
                diff = error.actual[i] - self._state[i]
                self._state[i] += self._learning_rate * diff * error.precision

    def receive_input(
        self,
        input_data: List[float],
        prediction: Optional[Prediction] = None
    ) -> PredictionError:
        """Receive input and calculate error."""
        with self._lock:
            # Calculate error
            if prediction and isinstance(prediction.content, list):
                predicted = prediction.content
            else:
                predicted = self._state

            # Pad or truncate
            if len(predicted) != len(input_data):
                if len(predicted) < len(input_data):
                    predicted = predicted + [0.0] * (len(input_data) - len(predicted))
                else:
                    predicted = predicted[:len(input_data)]

            # Calculate error magnitude
            error_magnitude = sum(
                (p - a) ** 2 for p, a in zip(predicted, input_data)
            ) ** 0.5 / len(input_data)

            error = PredictionError(
                id=f"err_{self._name}_{time.time()}",
                prediction_id=prediction.id if prediction else "",
                predicted=predicted,
                actual=input_data,
                error_magnitude=error_magnitude,
                precision=self._precision
            )
            self._errors.append(error)

            # Update state toward input
            for i in range(min(len(self._state), len(input_data))):
                self._state[i] += self._learning_rate * (input_data[i] - self._state[i])

            return error

    def adjust_precision(self, error_history: List[float]) -> None:
        """Adjust precision based on error history."""
        with self._lock:
            if len(error_history) < 5:
                return

            avg_error = sum(error_history[-5:]) / 5

            # Lower precision if errors are high
            if avg_error > 0.5:
                self._precision *= 0.9
            elif avg_error < 0.1:
                self._precision *= 1.1

            self._precision = max(0.1, min(10.0, self._precision))

    @property
    def recent_error(self) -> float:
        """Get average recent error."""
        if not self._errors:
            return 0.0

        recent = self._errors[-10:]
        return sum(e.error_magnitude for e in recent) / len(recent)


# ============================================================================
# PREDICTIVE HIERARCHY
# ============================================================================

class PredictiveHierarchy:
    """
    Multi-level predictive processing hierarchy.

    "Ba'el builds hierarchies of prediction." — Ba'el
    """

    def __init__(self):
        """Initialize hierarchy."""
        self._layers: Dict[str, PredictiveLayer] = {}
        self._layer_order: List[str] = []
        self._connections: Dict[str, List[str]] = {}  # layer -> lower layers
        self._lock = threading.RLock()

    def add_layer(
        self,
        name: str,
        layer_type: LayerType,
        state_size: int = 10,
        below: Optional[str] = None
    ) -> PredictiveLayer:
        """Add layer to hierarchy."""
        with self._lock:
            layer = PredictiveLayer(name, layer_type, state_size)
            self._layers[name] = layer
            self._layer_order.append(name)
            self._connections[name] = []

            if below and below in self._layers:
                self._connections[name].append(below)

            return layer

    def connect_layers(self, higher: str, lower: str) -> bool:
        """Connect higher layer to lower layer."""
        with self._lock:
            if higher in self._layers and lower in self._layers:
                if lower not in self._connections[higher]:
                    self._connections[higher].append(lower)
                return True
            return False

    def top_down_pass(self) -> Dict[str, Prediction]:
        """Generate predictions from top to bottom."""
        with self._lock:
            predictions = {}

            # Process from top to bottom
            for layer_name in reversed(self._layer_order):
                layer = self._layers[layer_name]

                for lower_name in self._connections.get(layer_name, []):
                    lower_layer = self._layers[lower_name]

                    pred = layer.predict_down(len(lower_layer.state))
                    pred.target_layer = lower_name
                    predictions[f"{layer_name}->{lower_name}"] = pred

            return predictions

    def bottom_up_pass(
        self,
        sensory_input: List[float],
        predictions: Dict[str, Prediction]
    ) -> Dict[str, PredictionError]:
        """Process input from bottom to top."""
        with self._lock:
            errors = {}
            current_input = sensory_input

            # Process from bottom to top
            for layer_name in self._layer_order:
                layer = self._layers[layer_name]

                # Find prediction for this layer
                relevant_pred = None
                for key, pred in predictions.items():
                    if pred.target_layer == layer_name:
                        relevant_pred = pred
                        break

                # Calculate error
                error = layer.receive_input(current_input, relevant_pred)
                errors[layer_name] = error

                # Pass error up
                for higher_name, lower_names in self._connections.items():
                    if layer_name in lower_names:
                        self._layers[higher_name].receive_error(error)

                # Transform for next layer
                current_input = layer.state

            return errors

    def process(
        self,
        sensory_input: List[float]
    ) -> Tuple[Dict[str, Prediction], Dict[str, PredictionError]]:
        """Complete processing cycle."""
        predictions = self.top_down_pass()
        errors = self.bottom_up_pass(sensory_input, predictions)
        return predictions, errors

    def get_representation(self, layer_name: str) -> Optional[List[float]]:
        """Get current state of a layer."""
        if layer_name in self._layers:
            return self._layers[layer_name].state
        return None

    def total_prediction_error(self) -> float:
        """Calculate total prediction error across hierarchy."""
        with self._lock:
            total = 0.0
            for layer in self._layers.values():
                total += layer.recent_error
            return total / max(1, len(self._layers))

    @property
    def state(self) -> Dict[str, Any]:
        """Get hierarchy state."""
        return {
            'layer_count': len(self._layers),
            'layers': {
                name: {
                    'type': layer.layer_type.name,
                    'precision': layer._precision,
                    'recent_error': layer.recent_error
                }
                for name, layer in self._layers.items()
            },
            'total_error': self.total_prediction_error()
        }


# ============================================================================
# PRECISION WEIGHTING
# ============================================================================

class PrecisionWeighter:
    """
    Manage precision weighting across the hierarchy.

    "Ba'el weights by certainty." — Ba'el
    """

    def __init__(self):
        """Initialize weighter."""
        self._precision_history: Dict[str, List[float]] = {}
        self._lock = threading.RLock()

    def update_precision(
        self,
        layer_name: str,
        error: float,
        volatility: float = 0.1
    ) -> float:
        """
        Update precision based on prediction error.

        Lower error -> higher precision
        Higher volatility -> lower precision
        """
        with self._lock:
            if layer_name not in self._precision_history:
                self._precision_history[layer_name] = []

            self._precision_history[layer_name].append(error)

            # Keep last 100
            if len(self._precision_history[layer_name]) > 100:
                self._precision_history[layer_name] = self._precision_history[layer_name][-100:]

            # Calculate precision
            recent = self._precision_history[layer_name][-10:]
            avg_error = sum(recent) / len(recent)
            variance = sum((e - avg_error) ** 2 for e in recent) / len(recent)

            # Precision is inverse of variance (with floor)
            precision = 1.0 / (variance + 0.1 + volatility)

            return precision

    def get_weights(self) -> Dict[str, float]:
        """Get precision weights for all layers."""
        with self._lock:
            weights = {}

            for layer_name, history in self._precision_history.items():
                if history:
                    recent = history[-10:]
                    avg_error = sum(recent) / len(recent)
                    weights[layer_name] = 1.0 / (avg_error + 0.1)

            # Normalize
            total = sum(weights.values())
            if total > 0:
                weights = {k: v/total for k, v in weights.items()}

            return weights


# ============================================================================
# ATTENTION MECHANISM
# ============================================================================

class PredictiveAttention:
    """
    Attention through precision modulation.

    "Ba'el attends through precision." — Ba'el
    """

    def __init__(self):
        """Initialize attention."""
        self._attention_map: Dict[str, float] = {}
        self._saliency: Dict[str, float] = {}
        self._lock = threading.RLock()

    def update_attention(
        self,
        layer_name: str,
        prediction_error: float,
        expected_precision: float
    ) -> float:
        """
        Update attention based on prediction error.

        High precision + high error -> high attention (surprising)
        Low precision + high error -> low attention (expected uncertainty)
        """
        with self._lock:
            # Surprise = precision-weighted prediction error
            surprise = prediction_error * expected_precision

            # Saliency accumulates
            current_saliency = self._saliency.get(layer_name, 0)
            self._saliency[layer_name] = current_saliency * 0.9 + surprise * 0.1

            # Attention is proportional to saliency
            self._attention_map[layer_name] = self._saliency[layer_name]

            return self._attention_map[layer_name]

    def get_attention_distribution(self) -> Dict[str, float]:
        """Get normalized attention distribution."""
        with self._lock:
            if not self._attention_map:
                return {}

            total = sum(self._attention_map.values())
            if total == 0:
                return {k: 1/len(self._attention_map) for k in self._attention_map}

            return {k: v/total for k, v in self._attention_map.items()}

    def focus(self, layer_name: str, boost: float = 2.0) -> None:
        """Manually boost attention to a layer."""
        with self._lock:
            current = self._attention_map.get(layer_name, 0.5)
            self._attention_map[layer_name] = min(10.0, current * boost)

    def defocus(self, layer_name: str, factor: float = 0.5) -> None:
        """Reduce attention to a layer."""
        with self._lock:
            current = self._attention_map.get(layer_name, 0.5)
            self._attention_map[layer_name] = current * factor


# ============================================================================
# PREDICTIVE PROCESSING ENGINE
# ============================================================================

class PredictiveProcessingEngine:
    """
    Complete predictive processing system.

    "Ba'el processes through prediction." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._hierarchy = PredictiveHierarchy()
        self._weighter = PrecisionWeighter()
        self._attention = PredictiveAttention()
        self._history: List[Dict] = []
        self._lock = threading.RLock()

        # Build default hierarchy
        self._build_default_hierarchy()

    def _build_default_hierarchy(self) -> None:
        """Build default 4-layer hierarchy."""
        self._hierarchy.add_layer("sensory", LayerType.SENSORY, state_size=20)
        self._hierarchy.add_layer("feature", LayerType.FEATURE, state_size=15, below="sensory")
        self._hierarchy.add_layer("object", LayerType.OBJECT, state_size=10, below="feature")
        self._hierarchy.add_layer("semantic", LayerType.SEMANTIC, state_size=5, below="object")

    def process(
        self,
        sensory_input: List[float]
    ) -> Dict[str, Any]:
        """Process sensory input through hierarchy."""
        with self._lock:
            # Run predictive processing
            predictions, errors = self._hierarchy.process(sensory_input)

            # Update precision weights
            for layer_name, error in errors.items():
                precision = self._weighter.update_precision(
                    layer_name, error.error_magnitude
                )

                # Update attention
                self._attention.update_attention(
                    layer_name, error.error_magnitude, precision
                )

            # Record history
            result = {
                'timestamp': time.time(),
                'total_error': self._hierarchy.total_prediction_error(),
                'attention': self._attention.get_attention_distribution(),
                'precisions': self._weighter.get_weights()
            }
            self._history.append(result)

            return result

    def process_sequence(
        self,
        inputs: List[List[float]]
    ) -> List[Dict]:
        """Process sequence of inputs."""
        results = []
        for input_data in inputs:
            result = self.process(input_data)
            results.append(result)
        return results

    def get_representation(self, layer_name: str) -> Optional[List[float]]:
        """Get representation at layer."""
        return self._hierarchy.get_representation(layer_name)

    def get_prediction(self, target_layer: str) -> Optional[Prediction]:
        """Get current prediction for layer."""
        predictions = self._hierarchy.top_down_pass()

        for key, pred in predictions.items():
            if pred.target_layer == target_layer:
                return pred

        return None

    def focus_attention(self, layer_name: str) -> None:
        """Focus attention on layer."""
        self._attention.focus(layer_name)

    def learning_rate(self, new_rate: float) -> None:
        """Set learning rate for all layers."""
        with self._lock:
            for layer in self._hierarchy._layers.values():
                layer._learning_rate = new_rate

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'hierarchy': self._hierarchy.state,
            'attention': self._attention.get_attention_distribution(),
            'precision_weights': self._weighter.get_weights(),
            'history_length': len(self._history)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_predictive_processing_engine() -> PredictiveProcessingEngine:
    """Create predictive processing engine."""
    return PredictiveProcessingEngine()


def create_hierarchy() -> PredictiveHierarchy:
    """Create predictive hierarchy."""
    return PredictiveHierarchy()


def create_layer(
    name: str,
    layer_type: LayerType,
    state_size: int = 10
) -> PredictiveLayer:
    """Create predictive layer."""
    return PredictiveLayer(name, layer_type, state_size)


def process_input(
    input_data: List[float],
    engine: Optional[PredictiveProcessingEngine] = None
) -> Dict[str, Any]:
    """Quick input processing."""
    if engine is None:
        engine = create_predictive_processing_engine()
    return engine.process(input_data)
