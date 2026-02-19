"""
BAEL Predictive Coding Engine
==============================

Hierarchical predictive coding.
Prediction, error, and precision.

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
from collections import deque, defaultdict
import copy

logger = logging.getLogger("BAEL.PredictiveCoding")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class SignalType(Enum):
    """Types of signals in hierarchy."""
    PREDICTION = auto()      # Top-down prediction
    ERROR = auto()           # Bottom-up prediction error
    PRECISION = auto()       # Confidence/attention


class UpdateDirection(Enum):
    """Direction of processing."""
    BOTTOM_UP = auto()       # Error propagation
    TOP_DOWN = auto()        # Prediction propagation
    LATERAL = auto()         # Same-level


class LayerType(Enum):
    """Types of processing layers."""
    SENSORY = auto()         # Lowest level
    INTERMEDIATE = auto()    # Middle levels
    CONCEPTUAL = auto()      # Highest level


@dataclass
class Prediction:
    """
    A prediction from higher level.
    """
    id: str
    source_layer: int
    target_layer: int
    content: Any
    precision: float = 0.5
    timestamp: float = field(default_factory=time.time)


@dataclass
class PredictionError:
    """
    Prediction error signal.
    """
    id: str
    source_layer: int
    prediction_id: str
    actual: Any
    predicted: Any
    error_magnitude: float
    precision_weighted: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class PrecisionWeight:
    """
    Precision (confidence) weighting.
    """
    layer: int
    value: float = 0.5
    attention_boost: float = 0.0

    @property
    def effective(self) -> float:
        return min(1.0, self.value + self.attention_boost)


@dataclass
class LayerState:
    """
    State of a processing layer.
    """
    layer_id: int
    layer_type: LayerType
    representation: Any = None
    prediction_error: float = 0.0
    precision: float = 0.5
    predictions_sent: int = 0
    errors_received: int = 0


# ============================================================================
# PROCESSING LAYER
# ============================================================================

class PredictiveLayer:
    """
    A layer in the predictive hierarchy.

    "Ba'el's prediction layer." — Ba'el
    """

    def __init__(
        self,
        layer_id: int,
        layer_type: LayerType,
        learning_rate: float = 0.1
    ):
        """Initialize layer."""
        self._id = layer_id
        self._type = layer_type
        self._learning_rate = learning_rate

        self._representation: Optional[Any] = None
        self._prediction: Optional[Prediction] = None
        self._error: float = 0.0
        self._precision = PrecisionWeight(layer_id, 0.5)

        self._pred_counter = 0
        self._error_counter = 0
        self._lock = threading.RLock()

    def _generate_pred_id(self) -> str:
        self._pred_counter += 1
        return f"pred_{self._id}_{self._pred_counter}"

    def _generate_error_id(self) -> str:
        self._error_counter += 1
        return f"error_{self._id}_{self._error_counter}"

    def set_representation(self, rep: Any) -> None:
        """Set current representation."""
        with self._lock:
            self._representation = rep

    def generate_prediction(
        self,
        target_layer: int
    ) -> Prediction:
        """Generate prediction for lower layer."""
        with self._lock:
            pred = Prediction(
                id=self._generate_pred_id(),
                source_layer=self._id,
                target_layer=target_layer,
                content=self._representation,
                precision=self._precision.effective
            )
            return pred

    def receive_prediction(self, prediction: Prediction) -> None:
        """Receive prediction from higher layer."""
        with self._lock:
            self._prediction = prediction

    def compute_error(self, sensory_input: Any = None) -> PredictionError:
        """Compute prediction error."""
        with self._lock:
            actual = sensory_input if sensory_input is not None else self._representation

            if self._prediction is None:
                error_mag = 0.0
            else:
                # Simple error calculation (for numeric)
                if isinstance(actual, (int, float)) and isinstance(self._prediction.content, (int, float)):
                    error_mag = abs(actual - self._prediction.content)
                else:
                    # Binary match/mismatch
                    error_mag = 0.0 if actual == self._prediction.content else 1.0

            self._error = error_mag

            # Precision-weighted error
            weighted = error_mag * self._precision.effective

            error = PredictionError(
                id=self._generate_error_id(),
                source_layer=self._id,
                prediction_id=self._prediction.id if self._prediction else "",
                actual=actual,
                predicted=self._prediction.content if self._prediction else None,
                error_magnitude=error_mag,
                precision_weighted=weighted
            )

            return error

    def update_from_error(self, error: PredictionError) -> None:
        """Update representation based on error."""
        with self._lock:
            # Simple update: move toward actual
            if isinstance(self._representation, (int, float)):
                if error.actual is not None and isinstance(error.actual, (int, float)):
                    delta = (error.actual - self._representation) * self._learning_rate
                    self._representation += delta

    def set_precision(self, value: float, attention: float = 0.0) -> None:
        """Set precision weight."""
        self._precision.value = max(0.0, min(1.0, value))
        self._precision.attention_boost = max(0.0, min(0.5, attention))

    def get_state(self) -> LayerState:
        """Get layer state."""
        return LayerState(
            layer_id=self._id,
            layer_type=self._type,
            representation=self._representation,
            prediction_error=self._error,
            precision=self._precision.effective,
            predictions_sent=self._pred_counter,
            errors_received=self._error_counter
        )

    @property
    def id(self) -> int:
        return self._id

    @property
    def representation(self) -> Any:
        return self._representation

    @property
    def error(self) -> float:
        return self._error

    @property
    def precision(self) -> float:
        return self._precision.effective


# ============================================================================
# HIERARCHICAL MODEL
# ============================================================================

class PredictiveHierarchy:
    """
    Hierarchical predictive coding model.

    "Ba'el's predictive hierarchy." — Ba'el
    """

    def __init__(
        self,
        num_layers: int = 3,
        learning_rate: float = 0.1
    ):
        """Initialize hierarchy."""
        self._layers: List[PredictiveLayer] = []
        self._learning_rate = learning_rate

        for i in range(num_layers):
            if i == 0:
                layer_type = LayerType.SENSORY
            elif i == num_layers - 1:
                layer_type = LayerType.CONCEPTUAL
            else:
                layer_type = LayerType.INTERMEDIATE

            self._layers.append(PredictiveLayer(i, layer_type, learning_rate))

        self._iteration = 0
        self._lock = threading.RLock()

    def set_input(self, sensory_input: Any) -> None:
        """Set sensory input at bottom layer."""
        with self._lock:
            if self._layers:
                self._layers[0].set_representation(sensory_input)

    def set_prior(self, prior: Any) -> None:
        """Set prior/expectation at top layer."""
        with self._lock:
            if self._layers:
                self._layers[-1].set_representation(prior)

    def top_down_pass(self) -> List[Prediction]:
        """Run top-down prediction pass."""
        with self._lock:
            predictions = []

            for i in range(len(self._layers) - 1, 0, -1):
                pred = self._layers[i].generate_prediction(i - 1)
                self._layers[i - 1].receive_prediction(pred)
                predictions.append(pred)

            return predictions

    def bottom_up_pass(self, sensory_input: Any = None) -> List[PredictionError]:
        """Run bottom-up error pass."""
        with self._lock:
            errors = []

            if sensory_input is not None:
                self._layers[0].set_representation(sensory_input)

            for i in range(len(self._layers) - 1):
                error = self._layers[i].compute_error()
                self._layers[i + 1].update_from_error(error)
                errors.append(error)

            return errors

    def iterate(self, sensory_input: Any = None, iterations: int = 1) -> Dict[str, Any]:
        """Run inference iterations."""
        with self._lock:
            all_predictions = []
            all_errors = []

            for _ in range(iterations):
                self._iteration += 1

                # Top-down predictions
                preds = self.top_down_pass()
                all_predictions.extend(preds)

                # Bottom-up errors
                errors = self.bottom_up_pass(sensory_input)
                all_errors.extend(errors)

            return {
                'iterations': iterations,
                'predictions': len(all_predictions),
                'errors': len(all_errors),
                'final_error': sum(e.error_magnitude for e in all_errors) / max(1, len(all_errors))
            }

    def get_layer_state(self, layer_id: int) -> Optional[LayerState]:
        """Get state of specific layer."""
        if 0 <= layer_id < len(self._layers):
            return self._layers[layer_id].get_state()
        return None

    def get_all_states(self) -> List[LayerState]:
        """Get all layer states."""
        return [layer.get_state() for layer in self._layers]

    def set_attention(self, layer_id: int, attention: float) -> None:
        """Set attention (precision boost) at layer."""
        if 0 <= layer_id < len(self._layers):
            current = self._layers[layer_id].precision
            self._layers[layer_id].set_precision(current, attention)

    @property
    def total_error(self) -> float:
        return sum(layer.error for layer in self._layers)

    @property
    def num_layers(self) -> int:
        return len(self._layers)


# ============================================================================
# FREE ENERGY MINIMIZATION
# ============================================================================

class FreeEnergyMinimizer:
    """
    Minimize free energy through prediction.

    "Ba'el minimizes surprise." — Ba'el
    """

    def __init__(
        self,
        hierarchy: PredictiveHierarchy
    ):
        """Initialize minimizer."""
        self._hierarchy = hierarchy
        self._free_energy_history: deque = deque(maxlen=1000)
        self._lock = threading.RLock()

    def compute_free_energy(self) -> float:
        """Compute variational free energy."""
        with self._lock:
            # Simplified: F ≈ prediction error + complexity
            prediction_error = self._hierarchy.total_error

            # Complexity: difference from prior
            complexity = 0.0
            for layer in self._hierarchy._layers:
                complexity += layer.error * (1 - layer.precision)

            free_energy = prediction_error + 0.1 * complexity
            self._free_energy_history.append(free_energy)

            return free_energy

    def minimize_step(self, sensory_input: Any = None) -> float:
        """Take minimization step."""
        with self._lock:
            # Run inference
            self._hierarchy.iterate(sensory_input, iterations=3)

            # Compute free energy
            fe = self.compute_free_energy()

            return fe

    def minimize(
        self,
        sensory_input: Any,
        max_iterations: int = 10,
        threshold: float = 0.01
    ) -> Tuple[float, int]:
        """Minimize until convergence."""
        with self._lock:
            prev_fe = float('inf')

            for i in range(max_iterations):
                fe = self.minimize_step(sensory_input)

                if abs(prev_fe - fe) < threshold:
                    return fe, i + 1

                prev_fe = fe

            return fe, max_iterations

    @property
    def free_energy(self) -> float:
        if self._free_energy_history:
            return self._free_energy_history[-1]
        return 0.0

    @property
    def free_energy_trajectory(self) -> List[float]:
        return list(self._free_energy_history)


# ============================================================================
# PREDICTIVE CODING ENGINE
# ============================================================================

class PredictiveCodingEngine:
    """
    Complete predictive coding engine.

    "Ba'el's predictive perception." — Ba'el
    """

    def __init__(
        self,
        num_layers: int = 4,
        learning_rate: float = 0.1
    ):
        """Initialize engine."""
        self._hierarchy = PredictiveHierarchy(num_layers, learning_rate)
        self._minimizer = FreeEnergyMinimizer(self._hierarchy)
        self._observations: List[Any] = []
        self._lock = threading.RLock()

    # Input/Prior

    def set_input(self, sensory_input: Any) -> None:
        """Set sensory input."""
        self._hierarchy.set_input(sensory_input)
        self._observations.append(sensory_input)

    def set_prior(self, prior: Any) -> None:
        """Set high-level prior."""
        self._hierarchy.set_prior(prior)

    # Inference

    def infer(
        self,
        sensory_input: Any,
        iterations: int = 5
    ) -> Dict[str, Any]:
        """Run predictive inference."""
        return self._hierarchy.iterate(sensory_input, iterations)

    def perceive(
        self,
        sensory_input: Any,
        max_iterations: int = 10
    ) -> Tuple[Any, float]:
        """Perceive by minimizing free energy."""
        with self._lock:
            fe, iters = self._minimizer.minimize(
                sensory_input, max_iterations
            )

            # Get top-level representation (percept)
            top_state = self._hierarchy.get_layer_state(
                self._hierarchy.num_layers - 1
            )

            percept = top_state.representation if top_state else None

            return percept, fe

    # Attention

    def attend(self, layer: int, amount: float = 0.3) -> None:
        """Apply attention to layer."""
        self._hierarchy.set_attention(layer, amount)

    def attend_sensory(self, amount: float = 0.3) -> None:
        """Attend to sensory layer."""
        self.attend(0, amount)

    def attend_conceptual(self, amount: float = 0.3) -> None:
        """Attend to conceptual layer."""
        self.attend(self._hierarchy.num_layers - 1, amount)

    # Analysis

    def get_prediction_error(self, layer: int = None) -> float:
        """Get prediction error."""
        if layer is None:
            return self._hierarchy.total_error

        state = self._hierarchy.get_layer_state(layer)
        return state.prediction_error if state else 0.0

    def get_free_energy(self) -> float:
        """Get current free energy."""
        return self._minimizer.free_energy

    def get_layer_states(self) -> List[LayerState]:
        """Get all layer states."""
        return self._hierarchy.get_all_states()

    @property
    def free_energy_history(self) -> List[float]:
        return self._minimizer.free_energy_trajectory

    @property
    def hierarchy(self) -> PredictiveHierarchy:
        return self._hierarchy

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'layers': self._hierarchy.num_layers,
            'total_error': self._hierarchy.total_error,
            'free_energy': self._minimizer.free_energy,
            'observations': len(self._observations),
            'layer_errors': [
                s.prediction_error for s in self._hierarchy.get_all_states()
            ]
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_predictive_coding_engine(
    num_layers: int = 4
) -> PredictiveCodingEngine:
    """Create predictive coding engine."""
    return PredictiveCodingEngine(num_layers)


def predict_and_perceive(
    sensory_input: Any,
    prior: Any = None
) -> Tuple[Any, float]:
    """Quick prediction and perception."""
    engine = create_predictive_coding_engine()
    if prior:
        engine.set_prior(prior)
    return engine.perceive(sensory_input)
