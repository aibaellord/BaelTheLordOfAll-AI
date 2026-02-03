#!/usr/bin/env python3
"""
BAEL - Prediction Engine
Future state prediction and forecasting for agents.

Features:
- State prediction
- Trajectory forecasting
- Uncertainty estimation
- Predictive modeling
- Temporal reasoning
"""

import asyncio
import hashlib
import json
import math
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class PredictionType(Enum):
    """Types of predictions."""
    STATE = "state"
    EVENT = "event"
    TRAJECTORY = "trajectory"
    OUTCOME = "outcome"
    BEHAVIOR = "behavior"


class ConfidenceLevel(Enum):
    """Confidence levels."""
    VERY_LOW = 0
    LOW = 1
    MODERATE = 2
    HIGH = 3
    VERY_HIGH = 4


class TemporalHorizon(Enum):
    """Temporal horizons for predictions."""
    IMMEDIATE = "immediate"
    SHORT_TERM = "short_term"
    MEDIUM_TERM = "medium_term"
    LONG_TERM = "long_term"


class PredictionMethod(Enum):
    """Prediction methods."""
    PATTERN_MATCHING = "pattern_matching"
    TREND_ANALYSIS = "trend_analysis"
    MARKOV_CHAIN = "markov_chain"
    EXPONENTIAL_SMOOTHING = "exponential_smoothing"
    ENSEMBLE = "ensemble"


class ValidationResult(Enum):
    """Prediction validation results."""
    CORRECT = "correct"
    PARTIALLY_CORRECT = "partially_correct"
    INCORRECT = "incorrect"
    PENDING = "pending"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Prediction:
    """A prediction."""
    prediction_id: str = ""
    prediction_type: PredictionType = PredictionType.STATE
    target: str = ""
    predicted_value: Any = None
    confidence: float = 0.5
    confidence_level: ConfidenceLevel = ConfidenceLevel.MODERATE
    horizon: TemporalHorizon = TemporalHorizon.SHORT_TERM
    method: PredictionMethod = PredictionMethod.PATTERN_MATCHING
    uncertainty: float = 0.0
    bounds: Optional[Tuple[Any, Any]] = None
    created_at: datetime = field(default_factory=datetime.now)
    valid_until: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.prediction_id:
            self.prediction_id = str(uuid.uuid4())[:8]


@dataclass
class StateObservation:
    """A state observation."""
    observation_id: str = ""
    state: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.observation_id:
            self.observation_id = str(uuid.uuid4())[:8]


@dataclass
class Trajectory:
    """A trajectory of states."""
    trajectory_id: str = ""
    states: List[Dict[str, Any]] = field(default_factory=list)
    timestamps: List[datetime] = field(default_factory=list)
    confidence: float = 0.5

    def __post_init__(self):
        if not self.trajectory_id:
            self.trajectory_id = str(uuid.uuid4())[:8]


@dataclass
class PredictionValidation:
    """A prediction validation."""
    prediction_id: str = ""
    result: ValidationResult = ValidationResult.PENDING
    actual_value: Any = None
    error: float = 0.0
    validated_at: datetime = field(default_factory=datetime.now)


@dataclass
class PredictiveModel:
    """A predictive model."""
    model_id: str = ""
    name: str = ""
    model_type: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    accuracy: float = 0.0
    predictions_made: int = 0
    last_trained: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.model_id:
            self.model_id = str(uuid.uuid4())[:8]


@dataclass
class UncertaintyEstimate:
    """An uncertainty estimate."""
    mean: float = 0.0
    variance: float = 0.0
    std_dev: float = 0.0
    lower_bound: float = 0.0
    upper_bound: float = 0.0
    distribution: str = "normal"


# =============================================================================
# PATTERN MATCHER
# =============================================================================

class PatternMatcher:
    """Match patterns for prediction."""

    def __init__(self, history_size: int = 1000):
        self._history: deque = deque(maxlen=history_size)
        self._patterns: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    def observe(self, state: Dict[str, Any]) -> None:
        """Observe a state."""
        self._history.append(StateObservation(state=state))

        self._extract_patterns()

    def _extract_patterns(self) -> None:
        """Extract patterns from history."""
        if len(self._history) < 3:
            return

        for window_size in [2, 3, 5]:
            if len(self._history) >= window_size + 1:
                pattern_states = list(self._history)[-window_size-1:-1]
                next_state = list(self._history)[-1]

                pattern_key = self._hash_pattern(pattern_states)
                self._patterns[pattern_key].append(next_state.state)

    def _hash_pattern(
        self,
        states: List[StateObservation]
    ) -> str:
        """Create hash for a pattern."""
        serialized = json.dumps(
            [s.state for s in states],
            sort_keys=True,
            default=str
        )
        return hashlib.md5(serialized.encode()).hexdigest()[:16]

    def predict_next(
        self,
        current_states: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Predict next state based on pattern."""
        pattern_key = self._hash_pattern([
            StateObservation(state=s) for s in current_states
        ])

        matches = self._patterns.get(pattern_key, [])

        if not matches:
            return None

        if all(isinstance(m, dict) for m in matches):
            aggregated = {}
            for key in matches[0].keys():
                values = [m.get(key) for m in matches if key in m]
                if values and all(isinstance(v, (int, float)) for v in values):
                    aggregated[key] = sum(values) / len(values)
                elif values:
                    from collections import Counter
                    counter = Counter(values)
                    aggregated[key] = counter.most_common(1)[0][0]
            return aggregated

        return matches[-1]

    def get_confidence(
        self,
        current_states: List[Dict[str, Any]]
    ) -> float:
        """Get confidence for pattern match."""
        pattern_key = self._hash_pattern([
            StateObservation(state=s) for s in current_states
        ])

        matches = self._patterns.get(pattern_key, [])

        if not matches:
            return 0.0

        base_confidence = min(1.0, len(matches) * 0.1)

        return base_confidence


# =============================================================================
# TREND ANALYZER
# =============================================================================

class TrendAnalyzer:
    """Analyze trends for prediction."""

    def __init__(self):
        self._time_series: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)

    def add_observation(
        self,
        variable: str,
        value: float,
        timestamp: Optional[datetime] = None
    ) -> None:
        """Add an observation."""
        ts = timestamp or datetime.now()
        self._time_series[variable].append((ts, value))

        if len(self._time_series[variable]) > 1000:
            self._time_series[variable] = self._time_series[variable][-1000:]

    def predict_value(
        self,
        variable: str,
        steps_ahead: int = 1
    ) -> Tuple[float, float]:
        """Predict future value using trend analysis."""
        series = self._time_series.get(variable, [])

        if len(series) < 2:
            return 0.0, 0.0

        values = [v for _, v in series[-20:]]

        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n

        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator

        intercept = y_mean - slope * x_mean

        predicted = intercept + slope * (n - 1 + steps_ahead)

        residuals = [
            (v - (intercept + slope * i)) ** 2
            for i, v in enumerate(values)
        ]
        mse = sum(residuals) / n
        confidence = max(0.0, 1.0 - math.sqrt(mse) / (max(values) - min(values) + 0.001))

        return predicted, confidence

    def get_trend_direction(
        self,
        variable: str,
        window: int = 5
    ) -> str:
        """Get trend direction."""
        series = self._time_series.get(variable, [])

        if len(series) < window:
            return "stable"

        recent = [v for _, v in series[-window:]]

        diffs = [recent[i+1] - recent[i] for i in range(len(recent)-1)]
        avg_diff = sum(diffs) / len(diffs) if diffs else 0

        if avg_diff > 0.01:
            return "increasing"
        elif avg_diff < -0.01:
            return "decreasing"
        else:
            return "stable"

    def get_volatility(self, variable: str) -> float:
        """Get volatility of a variable."""
        series = self._time_series.get(variable, [])

        if len(series) < 2:
            return 0.0

        values = [v for _, v in series[-20:]]
        mean = sum(values) / len(values)

        variance = sum((v - mean) ** 2 for v in values) / len(values)

        return math.sqrt(variance)


# =============================================================================
# MARKOV PREDICTOR
# =============================================================================

class MarkovPredictor:
    """Markov chain based predictor."""

    def __init__(self):
        self._transitions: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._state_counts: Dict[str, int] = defaultdict(int)
        self._current_state: Optional[str] = None

    def observe_transition(
        self,
        from_state: str,
        to_state: str
    ) -> None:
        """Observe a state transition."""
        self._transitions[from_state][to_state] += 1
        self._state_counts[from_state] += 1
        self._current_state = to_state

    def predict_next(
        self,
        current_state: Optional[str] = None
    ) -> Tuple[Optional[str], float]:
        """Predict next state."""
        state = current_state or self._current_state

        if state is None or state not in self._transitions:
            return None, 0.0

        transitions = self._transitions[state]
        total = self._state_counts[state]

        if total == 0:
            return None, 0.0

        probabilities = {
            s: c / total for s, c in transitions.items()
        }

        most_likely = max(probabilities, key=probabilities.get)
        confidence = probabilities[most_likely]

        return most_likely, confidence

    def predict_sequence(
        self,
        start_state: str,
        length: int
    ) -> List[Tuple[str, float]]:
        """Predict a sequence of states."""
        sequence = []
        current = start_state

        for _ in range(length):
            next_state, confidence = self.predict_next(current)

            if next_state is None:
                break

            sequence.append((next_state, confidence))
            current = next_state

        return sequence

    def get_transition_probability(
        self,
        from_state: str,
        to_state: str
    ) -> float:
        """Get transition probability."""
        if from_state not in self._transitions:
            return 0.0

        total = self._state_counts[from_state]

        if total == 0:
            return 0.0

        count = self._transitions[from_state].get(to_state, 0)

        return count / total

    def get_stationary_distribution(self) -> Dict[str, float]:
        """Get stationary distribution (approximation)."""
        states = list(self._transitions.keys())

        if not states:
            return {}

        dist = {s: 1.0 / len(states) for s in states}

        for _ in range(100):
            new_dist = defaultdict(float)

            for from_state in states:
                total = self._state_counts[from_state]

                if total == 0:
                    continue

                for to_state, count in self._transitions[from_state].items():
                    prob = count / total
                    new_dist[to_state] += dist.get(from_state, 0) * prob

            if new_dist:
                total_new = sum(new_dist.values())
                if total_new > 0:
                    dist = {s: v / total_new for s, v in new_dist.items()}

        return dict(dist)


# =============================================================================
# EXPONENTIAL SMOOTHER
# =============================================================================

class ExponentialSmoother:
    """Exponential smoothing for prediction."""

    def __init__(self, alpha: float = 0.3):
        self._alpha = alpha
        self._series: Dict[str, List[float]] = defaultdict(list)
        self._smoothed: Dict[str, float] = {}

    def observe(self, variable: str, value: float) -> None:
        """Observe a value."""
        self._series[variable].append(value)

        if variable not in self._smoothed:
            self._smoothed[variable] = value
        else:
            self._smoothed[variable] = (
                self._alpha * value +
                (1 - self._alpha) * self._smoothed[variable]
            )

    def predict(
        self,
        variable: str,
        steps_ahead: int = 1
    ) -> Tuple[float, float]:
        """Predict future value."""
        if variable not in self._smoothed:
            return 0.0, 0.0

        predicted = self._smoothed[variable]

        series = self._series.get(variable, [])

        if len(series) < 2:
            return predicted, 0.5

        recent = series[-10:]
        errors = [abs(v - self._smoothed[variable]) for v in recent]
        avg_error = sum(errors) / len(errors)

        value_range = max(series) - min(series)
        if value_range > 0:
            confidence = max(0.0, 1.0 - avg_error / value_range)
        else:
            confidence = 0.8

        return predicted, confidence

    def get_trend(self, variable: str) -> float:
        """Get trend component."""
        series = self._series.get(variable, [])

        if len(series) < 2:
            return 0.0

        recent = series[-5:]

        return (recent[-1] - recent[0]) / len(recent)


# =============================================================================
# UNCERTAINTY ESTIMATOR
# =============================================================================

class UncertaintyEstimator:
    """Estimate prediction uncertainty."""

    def __init__(self):
        self._prediction_errors: Dict[str, List[float]] = defaultdict(list)

    def record_error(
        self,
        model_id: str,
        predicted: float,
        actual: float
    ) -> None:
        """Record a prediction error."""
        error = actual - predicted
        self._prediction_errors[model_id].append(error)

        if len(self._prediction_errors[model_id]) > 100:
            self._prediction_errors[model_id] = self._prediction_errors[model_id][-100:]

    def estimate_uncertainty(
        self,
        model_id: str,
        predicted_value: float
    ) -> UncertaintyEstimate:
        """Estimate uncertainty for a prediction."""
        errors = self._prediction_errors.get(model_id, [])

        if len(errors) < 2:
            return UncertaintyEstimate(
                mean=predicted_value,
                variance=0.1,
                std_dev=0.316,
                lower_bound=predicted_value - 0.316,
                upper_bound=predicted_value + 0.316
            )

        mean_error = sum(errors) / len(errors)
        variance = sum((e - mean_error) ** 2 for e in errors) / len(errors)
        std_dev = math.sqrt(variance)

        return UncertaintyEstimate(
            mean=predicted_value,
            variance=variance,
            std_dev=std_dev,
            lower_bound=predicted_value - 1.96 * std_dev,
            upper_bound=predicted_value + 1.96 * std_dev
        )

    def get_calibration(self, model_id: str) -> float:
        """Get calibration score."""
        errors = self._prediction_errors.get(model_id, [])

        if len(errors) < 10:
            return 0.5

        mean_error = sum(errors) / len(errors)

        return max(0.0, 1.0 - abs(mean_error))


# =============================================================================
# PREDICTION ENGINE
# =============================================================================

class PredictionEngine:
    """
    Prediction Engine for BAEL.

    Future state prediction and forecasting.
    """

    def __init__(self):
        self._pattern_matcher = PatternMatcher()
        self._trend_analyzer = TrendAnalyzer()
        self._markov_predictor = MarkovPredictor()
        self._smoother = ExponentialSmoother()
        self._uncertainty = UncertaintyEstimator()

        self._predictions: Dict[str, Prediction] = {}
        self._validations: List[PredictionValidation] = []

        self._prediction_count = 0
        self._correct_count = 0

    def observe_state(
        self,
        state: Dict[str, Any],
        state_name: Optional[str] = None
    ) -> None:
        """Observe a state."""
        self._pattern_matcher.observe(state)

        for key, value in state.items():
            if isinstance(value, (int, float)):
                self._trend_analyzer.add_observation(key, value)
                self._smoother.observe(key, value)

        if state_name:
            if hasattr(self, '_last_state_name') and self._last_state_name:
                self._markov_predictor.observe_transition(
                    self._last_state_name, state_name
                )
            self._last_state_name = state_name

    def predict_next_state(
        self,
        current_states: List[Dict[str, Any]],
        method: PredictionMethod = PredictionMethod.PATTERN_MATCHING
    ) -> Prediction:
        """Predict next state."""
        if method == PredictionMethod.PATTERN_MATCHING:
            predicted = self._pattern_matcher.predict_next(current_states)
            confidence = self._pattern_matcher.get_confidence(current_states)

        elif method == PredictionMethod.ENSEMBLE:
            pattern_pred = self._pattern_matcher.predict_next(current_states)
            pattern_conf = self._pattern_matcher.get_confidence(current_states)

            predicted = pattern_pred
            confidence = pattern_conf
        else:
            predicted = None
            confidence = 0.0

        prediction = Prediction(
            prediction_type=PredictionType.STATE,
            target="next_state",
            predicted_value=predicted,
            confidence=confidence,
            confidence_level=self._confidence_to_level(confidence),
            method=method,
            valid_until=datetime.now() + timedelta(hours=1)
        )

        self._predictions[prediction.prediction_id] = prediction
        self._prediction_count += 1

        return prediction

    def predict_value(
        self,
        variable: str,
        steps_ahead: int = 1,
        method: PredictionMethod = PredictionMethod.TREND_ANALYSIS
    ) -> Prediction:
        """Predict future value of a variable."""
        if method == PredictionMethod.TREND_ANALYSIS:
            predicted, confidence = self._trend_analyzer.predict_value(
                variable, steps_ahead
            )

        elif method == PredictionMethod.EXPONENTIAL_SMOOTHING:
            predicted, confidence = self._smoother.predict(
                variable, steps_ahead
            )

        elif method == PredictionMethod.ENSEMBLE:
            trend_pred, trend_conf = self._trend_analyzer.predict_value(
                variable, steps_ahead
            )
            smooth_pred, smooth_conf = self._smoother.predict(
                variable, steps_ahead
            )

            predicted = (trend_pred * trend_conf + smooth_pred * smooth_conf)
            if trend_conf + smooth_conf > 0:
                predicted /= (trend_conf + smooth_conf)
            confidence = (trend_conf + smooth_conf) / 2
        else:
            predicted = 0.0
            confidence = 0.0

        uncertainty = self._uncertainty.estimate_uncertainty(
            f"{variable}_{method.value}", predicted
        )

        prediction = Prediction(
            prediction_type=PredictionType.STATE,
            target=variable,
            predicted_value=predicted,
            confidence=confidence,
            confidence_level=self._confidence_to_level(confidence),
            method=method,
            uncertainty=uncertainty.std_dev,
            bounds=(uncertainty.lower_bound, uncertainty.upper_bound),
            valid_until=datetime.now() + timedelta(hours=steps_ahead)
        )

        self._predictions[prediction.prediction_id] = prediction
        self._prediction_count += 1

        return prediction

    def predict_state_sequence(
        self,
        start_state: str,
        length: int
    ) -> Trajectory:
        """Predict a sequence of states."""
        sequence = self._markov_predictor.predict_sequence(start_state, length)

        states = [{"state": s} for s, _ in sequence]
        timestamps = [
            datetime.now() + timedelta(minutes=i*10)
            for i in range(len(sequence))
        ]

        avg_confidence = (
            sum(c for _, c in sequence) / len(sequence)
            if sequence else 0.0
        )

        return Trajectory(
            states=states,
            timestamps=timestamps,
            confidence=avg_confidence
        )

    def predict_event_probability(
        self,
        from_state: str,
        to_state: str
    ) -> Prediction:
        """Predict probability of state transition."""
        probability = self._markov_predictor.get_transition_probability(
            from_state, to_state
        )

        prediction = Prediction(
            prediction_type=PredictionType.EVENT,
            target=f"{from_state} -> {to_state}",
            predicted_value=probability,
            confidence=min(1.0, probability + 0.2),
            confidence_level=self._confidence_to_level(probability),
            method=PredictionMethod.MARKOV_CHAIN
        )

        self._predictions[prediction.prediction_id] = prediction
        self._prediction_count += 1

        return prediction

    def validate_prediction(
        self,
        prediction_id: str,
        actual_value: Any
    ) -> PredictionValidation:
        """Validate a prediction."""
        prediction = self._predictions.get(prediction_id)

        if not prediction:
            return PredictionValidation(
                prediction_id=prediction_id,
                result=ValidationResult.PENDING
            )

        if isinstance(prediction.predicted_value, (int, float)):
            if prediction.bounds:
                in_bounds = (
                    prediction.bounds[0] <= actual_value <= prediction.bounds[1]
                )
            else:
                in_bounds = abs(prediction.predicted_value - actual_value) < 0.1

            error = abs(prediction.predicted_value - actual_value)

            if in_bounds:
                result = ValidationResult.CORRECT
                self._correct_count += 1
            elif error < 0.3:
                result = ValidationResult.PARTIALLY_CORRECT
            else:
                result = ValidationResult.INCORRECT

            model_id = f"{prediction.target}_{prediction.method.value}"
            self._uncertainty.record_error(
                model_id, prediction.predicted_value, actual_value
            )

        else:
            if prediction.predicted_value == actual_value:
                result = ValidationResult.CORRECT
                error = 0.0
                self._correct_count += 1
            else:
                result = ValidationResult.INCORRECT
                error = 1.0

        validation = PredictionValidation(
            prediction_id=prediction_id,
            result=result,
            actual_value=actual_value,
            error=error
        )

        self._validations.append(validation)

        return validation

    def _confidence_to_level(self, confidence: float) -> ConfidenceLevel:
        """Convert confidence to level."""
        if confidence >= 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif confidence >= 0.7:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.5:
            return ConfidenceLevel.MODERATE
        elif confidence >= 0.3:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW

    def get_prediction(
        self,
        prediction_id: str
    ) -> Optional[Prediction]:
        """Get a prediction by ID."""
        return self._predictions.get(prediction_id)

    def get_trend(self, variable: str) -> str:
        """Get trend direction for a variable."""
        return self._trend_analyzer.get_trend_direction(variable)

    def get_volatility(self, variable: str) -> float:
        """Get volatility for a variable."""
        return self._trend_analyzer.get_volatility(variable)

    def get_stationary_distribution(self) -> Dict[str, float]:
        """Get stationary distribution of states."""
        return self._markov_predictor.get_stationary_distribution()

    def get_accuracy(self) -> float:
        """Get overall prediction accuracy."""
        if self._prediction_count == 0:
            return 0.0

        validated = len(self._validations)

        if validated == 0:
            return 0.0

        correct = sum(
            1 for v in self._validations
            if v.result == ValidationResult.CORRECT
        )

        return correct / validated

    def get_recent_validations(
        self,
        limit: int = 20
    ) -> List[PredictionValidation]:
        """Get recent validations."""
        return self._validations[-limit:]

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "predictions_made": self._prediction_count,
            "validations": len(self._validations),
            "accuracy": f"{self.get_accuracy():.2%}",
            "correct_predictions": self._correct_count,
            "active_predictions": len(self._predictions)
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Prediction Engine."""
    print("=" * 70)
    print("BAEL - PREDICTION ENGINE DEMO")
    print("Future State Prediction and Forecasting")
    print("=" * 70)
    print()

    engine = PredictionEngine()

    # 1. Observe States
    print("1. OBSERVE STATES:")
    print("-" * 40)

    states = [
        {"temperature": 20.0, "humidity": 45.0, "pressure": 1013.0},
        {"temperature": 21.0, "humidity": 46.0, "pressure": 1012.5},
        {"temperature": 22.0, "humidity": 47.0, "pressure": 1012.0},
        {"temperature": 23.0, "humidity": 48.0, "pressure": 1011.5},
        {"temperature": 24.0, "humidity": 49.0, "pressure": 1011.0},
    ]

    state_names = ["cold", "cool", "mild", "warm", "warm"]

    for state, name in zip(states, state_names):
        engine.observe_state(state, name)
        print(f"   Observed: temp={state['temperature']}, state={name}")
    print()

    # 2. Predict Value
    print("2. PREDICT VALUE:")
    print("-" * 40)

    pred = engine.predict_value("temperature", steps_ahead=1)

    print(f"   Variable: {pred.target}")
    print(f"   Predicted: {pred.predicted_value:.2f}")
    print(f"   Confidence: {pred.confidence:.2f} ({pred.confidence_level.name})")
    print(f"   Bounds: {pred.bounds}")
    print()

    # 3. Trend Analysis
    print("3. TREND ANALYSIS:")
    print("-" * 40)

    for var in ["temperature", "humidity", "pressure"]:
        trend = engine.get_trend(var)
        volatility = engine.get_volatility(var)
        print(f"   {var}: {trend} (volatility={volatility:.2f})")
    print()

    # 4. Predict State Sequence
    print("4. PREDICT STATE SEQUENCE:")
    print("-" * 40)

    trajectory = engine.predict_state_sequence("warm", length=3)

    print(f"   Trajectory (confidence={trajectory.confidence:.2f}):")
    for i, state in enumerate(trajectory.states):
        print(f"     Step {i+1}: {state}")
    print()

    # 5. Predict Event Probability
    print("5. PREDICT EVENT PROBABILITY:")
    print("-" * 40)

    transitions = [
        ("cold", "cool"),
        ("cool", "mild"),
        ("warm", "cold"),
    ]

    for from_s, to_s in transitions:
        pred = engine.predict_event_probability(from_s, to_s)
        print(f"   {from_s} -> {to_s}: {pred.predicted_value:.2%}")
    print()

    # 6. Different Methods
    print("6. DIFFERENT PREDICTION METHODS:")
    print("-" * 40)

    methods = [
        PredictionMethod.TREND_ANALYSIS,
        PredictionMethod.EXPONENTIAL_SMOOTHING,
        PredictionMethod.ENSEMBLE,
    ]

    for method in methods:
        pred = engine.predict_value("temperature", steps_ahead=2, method=method)
        print(f"   {method.value}: {pred.predicted_value:.2f} (conf={pred.confidence:.2f})")
    print()

    # 7. Validate Predictions
    print("7. VALIDATE PREDICTIONS:")
    print("-" * 40)

    pred = engine.predict_value("temperature", steps_ahead=1)
    actual = 24.5

    print(f"   Predicted: {pred.predicted_value:.2f}")
    print(f"   Actual: {actual}")

    validation = engine.validate_prediction(pred.prediction_id, actual)

    print(f"   Result: {validation.result.value}")
    print(f"   Error: {validation.error:.2f}")
    print()

    # 8. More Observations
    print("8. MORE OBSERVATIONS:")
    print("-" * 40)

    more_states = [
        {"temperature": 25.0, "humidity": 50.0, "pressure": 1010.5},
        {"temperature": 25.5, "humidity": 51.0, "pressure": 1010.0},
        {"temperature": 26.0, "humidity": 52.0, "pressure": 1009.5},
    ]

    for state in more_states:
        engine.observe_state(state, "hot")

    pred2 = engine.predict_value("temperature", method=PredictionMethod.ENSEMBLE)
    print(f"   New prediction: {pred2.predicted_value:.2f}")
    print(f"   Confidence: {pred2.confidence:.2f}")
    print()

    # 9. Stationary Distribution
    print("9. STATIONARY DISTRIBUTION:")
    print("-" * 40)

    dist = engine.get_stationary_distribution()

    for state, prob in sorted(dist.items(), key=lambda x: x[1], reverse=True):
        print(f"   {state}: {prob:.2%}")
    print()

    # 10. Prediction Accuracy
    print("10. PREDICTION ACCURACY:")
    print("-" * 40)

    for _ in range(5):
        pred = engine.predict_value("temperature")
        actual = pred.predicted_value + random.uniform(-0.5, 0.5)
        engine.validate_prediction(pred.prediction_id, actual)

    accuracy = engine.get_accuracy()
    print(f"   Overall Accuracy: {accuracy:.2%}")
    print()

    # 11. Recent Validations
    print("11. RECENT VALIDATIONS:")
    print("-" * 40)

    validations = engine.get_recent_validations(limit=5)

    for v in validations:
        print(f"   {v.prediction_id}: {v.result.value} (error={v.error:.2f})")
    print()

    # 12. Summary
    print("12. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Prediction Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
