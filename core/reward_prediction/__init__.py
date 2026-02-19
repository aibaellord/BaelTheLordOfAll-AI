"""
BAEL Reward Prediction Error Engine
=====================================

Dopamine-like reward prediction and learning.
TD-error, reward anticipation, surprise signals.

"Ba'el learns from unexpected rewards." — Ba'el
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

logger = logging.getLogger("BAEL.RewardPrediction")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class SignalType(Enum):
    """Types of dopamine-like signals."""
    REWARD = auto()
    PUNISHMENT = auto()
    NEUTRAL = auto()


class LearningState(Enum):
    """Learning states."""
    EXPECTATION = auto()      # Building expectations
    SURPRISE = auto()         # Prediction error
    UPDATING = auto()         # Updating predictions
    HABITUATED = auto()       # Low error, stable


class CueType(Enum):
    """Types of predictive cues."""
    PRIMARY = auto()          # Direct reward predictor
    SECONDARY = auto()        # Learned predictor
    CONTEXTUAL = auto()       # Context cue


@dataclass
class Reward:
    """
    A reward or punishment signal.
    """
    id: str
    value: float              # Positive = reward, negative = punishment
    timestamp: float = field(default_factory=time.time)
    source: str = ""

    @property
    def signal_type(self) -> SignalType:
        if self.value > 0:
            return SignalType.REWARD
        elif self.value < 0:
            return SignalType.PUNISHMENT
        return SignalType.NEUTRAL


@dataclass
class Cue:
    """
    A predictive cue.
    """
    id: str
    name: str
    cue_type: CueType
    strength: float = 1.0
    onset_time: float = field(default_factory=time.time)


@dataclass
class Prediction:
    """
    A reward prediction.
    """
    cue_id: str
    predicted_value: float
    predicted_time: float
    confidence: float = 0.5

    @property
    def is_pending(self) -> bool:
        return time.time() < self.predicted_time


@dataclass
class PredictionError:
    """
    A reward prediction error (RPE).
    """
    prediction: Prediction
    actual_reward: float
    error: float              # actual - predicted
    timestamp: float = field(default_factory=time.time)

    @property
    def is_positive(self) -> bool:
        """Positive surprise (better than expected)."""
        return self.error > 0

    @property
    def is_negative(self) -> bool:
        """Negative surprise (worse than expected)."""
        return self.error < 0

    @property
    def magnitude(self) -> float:
        return abs(self.error)


# ============================================================================
# VALUE FUNCTION
# ============================================================================

class ValueFunction:
    """
    Learned value function for states/cues.

    "Ba'el predicts future value." — Ba'el
    """

    def __init__(
        self,
        learning_rate: float = 0.1,
        discount: float = 0.95
    ):
        """Initialize value function."""
        self._values: Dict[str, float] = defaultdict(float)
        self._eligibility: Dict[str, float] = defaultdict(float)
        self._learning_rate = learning_rate
        self._discount = discount
        self._decay = 0.9
        self._lock = threading.RLock()

    def get_value(self, state_id: str) -> float:
        """Get predicted value for state."""
        return self._values.get(state_id, 0.0)

    def update(
        self,
        state_id: str,
        td_error: float
    ) -> float:
        """Update value with TD error."""
        with self._lock:
            # Update eligibility
            self._eligibility[state_id] = 1.0

            # Update all values by eligibility
            for sid in self._eligibility:
                delta = self._learning_rate * td_error * self._eligibility[sid]
                self._values[sid] += delta
                self._eligibility[sid] *= self._decay * self._discount

            return self._values[state_id]

    def td_error(
        self,
        reward: float,
        current_state: str,
        next_state: Optional[str] = None
    ) -> float:
        """Compute TD error."""
        current_value = self.get_value(current_state)
        next_value = self.get_value(next_state) if next_state else 0.0

        # TD(0) error: r + γV(s') - V(s)
        return reward + self._discount * next_value - current_value

    def reset_eligibility(self) -> None:
        """Reset eligibility traces."""
        with self._lock:
            self._eligibility.clear()

    @property
    def values(self) -> Dict[str, float]:
        return self._values.copy()


# ============================================================================
# CUE-REWARD ASSOCIATIONS
# ============================================================================

class CueRewardLearning:
    """
    Learn cue-reward associations (Rescorla-Wagner).

    "Ba'el associates cues with rewards." — Ba'el
    """

    def __init__(
        self,
        learning_rate: float = 0.1,
        max_associative_strength: float = 1.0
    ):
        """Initialize cue-reward learning."""
        self._associations: Dict[str, float] = {}
        self._learning_rate = learning_rate
        self._max_strength = max_associative_strength
        self._update_history: List[Tuple[str, float, float]] = []
        self._lock = threading.RLock()

    def get_expectation(self, cue_id: str) -> float:
        """Get reward expectation for cue."""
        return self._associations.get(cue_id, 0.0)

    def total_expectation(self, cue_ids: List[str]) -> float:
        """Get total expectation for multiple cues."""
        return sum(self.get_expectation(cid) for cid in cue_ids)

    def update(
        self,
        cue_ids: List[str],
        actual_reward: float,
        saliences: Dict[str, float] = None
    ) -> Dict[str, float]:
        """
        Update associations using Rescorla-Wagner.

        ΔV = α * β * (λ - ΣV)
        """
        with self._lock:
            saliences = saliences or {cid: 1.0 for cid in cue_ids}

            # Total prediction
            total_v = self.total_expectation(cue_ids)

            # Prediction error
            error = actual_reward - total_v

            updates = {}
            for cue_id in cue_ids:
                salience = saliences.get(cue_id, 1.0)

                # Rescorla-Wagner update
                delta = self._learning_rate * salience * error

                old_value = self._associations.get(cue_id, 0.0)
                new_value = old_value + delta

                # Clamp
                new_value = max(-self._max_strength, min(self._max_strength, new_value))

                self._associations[cue_id] = new_value
                updates[cue_id] = delta

                self._update_history.append((cue_id, delta, error))

            return updates

    def extinction(
        self,
        cue_id: str,
        rate: float = 0.1
    ) -> float:
        """Extinguish association."""
        with self._lock:
            if cue_id in self._associations:
                old = self._associations[cue_id]
                self._associations[cue_id] *= (1 - rate)
                return old - self._associations[cue_id]
            return 0.0

    @property
    def associations(self) -> Dict[str, float]:
        return self._associations.copy()


# ============================================================================
# DOPAMINE-LIKE SIGNALING
# ============================================================================

class DopamineSignaling:
    """
    Simulated dopamine-like reward signaling.

    "Ba'el's reward signal." — Ba'el
    """

    def __init__(
        self,
        baseline: float = 1.0,
        max_signal: float = 5.0,
        min_signal: float = 0.0
    ):
        """Initialize dopamine signaling."""
        self._baseline = baseline
        self._current_level = baseline
        self._max_signal = max_signal
        self._min_signal = min_signal
        self._signal_history: deque = deque(maxlen=1000)
        self._lock = threading.RLock()

    def fire(self, prediction_error: float) -> float:
        """Generate dopamine signal from prediction error."""
        with self._lock:
            # Phasic response to prediction error
            # Positive error -> burst above baseline
            # Negative error -> dip below baseline

            if prediction_error > 0:
                # Burst (positive surprise)
                signal = self._baseline + prediction_error * 2
            elif prediction_error < 0:
                # Dip (negative surprise)
                signal = self._baseline + prediction_error
            else:
                # No surprise
                signal = self._baseline

            # Clamp
            signal = max(self._min_signal, min(self._max_signal, signal))

            self._current_level = signal
            self._signal_history.append({
                'time': time.time(),
                'level': signal,
                'error': prediction_error
            })

            return signal

    def decay_to_baseline(self, rate: float = 0.1) -> float:
        """Decay signal toward baseline."""
        with self._lock:
            diff = self._current_level - self._baseline
            self._current_level -= diff * rate
            return self._current_level

    @property
    def level(self) -> float:
        return self._current_level

    @property
    def is_above_baseline(self) -> bool:
        return self._current_level > self._baseline

    @property
    def is_below_baseline(self) -> bool:
        return self._current_level < self._baseline

    @property
    def history(self) -> List[Dict]:
        return list(self._signal_history)


# ============================================================================
# PREDICTION ERROR ENGINE
# ============================================================================

class RewardPredictionEngine:
    """
    Complete reward prediction error engine.

    "Ba'el predicts and learns from reward." — Ba'el
    """

    def __init__(
        self,
        learning_rate: float = 0.1,
        discount: float = 0.95
    ):
        """Initialize engine."""
        self._value_function = ValueFunction(learning_rate, discount)
        self._cue_reward = CueRewardLearning(learning_rate)
        self._dopamine = DopamineSignaling()

        self._active_cues: Dict[str, Cue] = {}
        self._pending_predictions: List[Prediction] = []
        self._error_history: List[PredictionError] = []
        self._current_state: Optional[str] = None

        self._reward_counter = 0
        self._cue_counter = 0
        self._lock = threading.RLock()

    def _generate_reward_id(self) -> str:
        self._reward_counter += 1
        return f"reward_{self._reward_counter}"

    def _generate_cue_id(self) -> str:
        self._cue_counter += 1
        return f"cue_{self._cue_counter}"

    # Cue operations

    def present_cue(
        self,
        name: str,
        cue_type: CueType = CueType.PRIMARY,
        strength: float = 1.0
    ) -> Cue:
        """Present a predictive cue."""
        with self._lock:
            cue = Cue(
                id=self._generate_cue_id(),
                name=name,
                cue_type=cue_type,
                strength=strength
            )

            self._active_cues[cue.id] = cue

            # Generate prediction
            expected_value = self._cue_reward.get_expectation(cue.id)
            prediction = Prediction(
                cue_id=cue.id,
                predicted_value=expected_value,
                predicted_time=time.time() + 1.0,  # Expected in 1 second
                confidence=min(abs(expected_value), 1.0)
            )
            self._pending_predictions.append(prediction)

            return cue

    def remove_cue(self, cue_id: str) -> None:
        """Remove cue."""
        with self._lock:
            if cue_id in self._active_cues:
                del self._active_cues[cue_id]

    # Reward operations

    def deliver_reward(self, value: float, source: str = "") -> PredictionError:
        """Deliver reward and compute prediction error."""
        with self._lock:
            reward = Reward(
                id=self._generate_reward_id(),
                value=value,
                source=source
            )

            # Get total prediction from active cues
            cue_ids = list(self._active_cues.keys())
            predicted = self._cue_reward.total_expectation(cue_ids)

            # Compute error
            error = value - predicted

            # Find matching prediction
            matching_pred = None
            for pred in self._pending_predictions:
                if not pred.is_pending:
                    matching_pred = pred
                    break

            if matching_pred is None:
                matching_pred = Prediction(
                    cue_id="implicit",
                    predicted_value=predicted,
                    predicted_time=time.time()
                )

            # Create prediction error
            rpe = PredictionError(
                prediction=matching_pred,
                actual_reward=value,
                error=error
            )
            self._error_history.append(rpe)

            # Fire dopamine signal
            self._dopamine.fire(error)

            # Update cue-reward associations
            self._cue_reward.update(cue_ids, value)

            # Update value function
            if self._current_state:
                self._value_function.update(self._current_state, error)

            # Clear pending predictions
            self._pending_predictions = [
                p for p in self._pending_predictions if p.is_pending
            ]

            return rpe

    def omit_expected_reward(self) -> Optional[PredictionError]:
        """Signal that expected reward was omitted."""
        with self._lock:
            # Get total prediction
            cue_ids = list(self._active_cues.keys())
            predicted = self._cue_reward.total_expectation(cue_ids)

            if predicted > 0:
                # Negative prediction error from omission
                return self.deliver_reward(0.0, source="omission")

            return None

    # State operations

    def set_state(self, state_id: str) -> float:
        """Set current state and get value."""
        with self._lock:
            old_state = self._current_state
            self._current_state = state_id

            # Compute TD error if transitioning
            if old_state:
                td_error = self._value_function.td_error(0, old_state, state_id)
                self._dopamine.fire(td_error * 0.5)  # Scaled for state value

            return self._value_function.get_value(state_id)

    def state_value(self, state_id: str) -> float:
        """Get state value."""
        return self._value_function.get_value(state_id)

    # Expectations

    def expect(self, cue_name: str) -> float:
        """Get expected reward for cue."""
        for cue in self._active_cues.values():
            if cue.name == cue_name:
                return self._cue_reward.get_expectation(cue.id)
        return 0.0

    def surprise_level(self) -> float:
        """Get current surprise level."""
        return abs(self._dopamine.level - 1.0)  # Deviation from baseline

    @property
    def dopamine_level(self) -> float:
        return self._dopamine.level

    @property
    def active_cues(self) -> List[Cue]:
        return list(self._active_cues.values())

    @property
    def error_history(self) -> List[PredictionError]:
        return self._error_history.copy()

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'active_cues': len(self._active_cues),
            'pending_predictions': len(self._pending_predictions),
            'error_history_size': len(self._error_history),
            'dopamine_level': self._dopamine.level,
            'current_state': self._current_state,
            'associations': len(self._cue_reward.associations),
            'value_states': len(self._value_function.values)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_reward_prediction_engine(
    learning_rate: float = 0.1,
    discount: float = 0.95
) -> RewardPredictionEngine:
    """Create reward prediction engine."""
    return RewardPredictionEngine(learning_rate, discount)


def create_cue(
    name: str,
    cue_type: CueType = CueType.PRIMARY
) -> Cue:
    """Create cue."""
    return Cue(
        id=f"cue_{random.randint(1000, 9999)}",
        name=name,
        cue_type=cue_type
    )


def compute_td_error(
    reward: float,
    current_value: float,
    next_value: float,
    discount: float = 0.95
) -> float:
    """Compute TD error."""
    return reward + discount * next_value - current_value
