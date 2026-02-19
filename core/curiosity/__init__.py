"""
BAEL Curiosity Engine
======================

Intrinsic motivation and curiosity.
Information seeking and exploration.

"Ba'el seeks to know." — Ba'el
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
from collections import defaultdict, deque
import copy

logger = logging.getLogger("BAEL.Curiosity")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class CuriosityType(Enum):
    """Types of curiosity."""
    DIVERSIVE = auto()     # Stimulus seeking
    SPECIFIC = auto()       # Knowledge seeking
    PERCEPTUAL = auto()    # Novelty detection
    EPISTEMIC = auto()     # Understanding seeking


class MotivationType(Enum):
    """Types of intrinsic motivation."""
    CURIOSITY = auto()
    COMPETENCE = auto()
    AUTONOMY = auto()
    MASTERY = auto()


class ExplorationStrategy(Enum):
    """Exploration strategies."""
    RANDOM = auto()
    NOVELTY_SEEKING = auto()
    UNCERTAINTY_REDUCTION = auto()
    INFORMATION_GAIN = auto()
    COMPETENCE_PROGRESS = auto()


@dataclass
class State:
    """
    A state for exploration.
    """
    id: str
    features: Dict[str, float]
    visits: int = 0
    last_visit: float = 0.0
    novelty: float = 1.0

    @property
    def recency(self) -> float:
        if self.last_visit == 0:
            return float('inf')
        return time.time() - self.last_visit


@dataclass
class Action:
    """
    An action to take.
    """
    id: str
    name: str
    expected_novelty: float = 0.5
    expected_learning: float = 0.5


@dataclass
class Prediction:
    """
    A prediction about the world.
    """
    id: str
    input_state: str
    action: str
    predicted_state: Dict[str, float]
    actual_state: Optional[Dict[str, float]] = None
    prediction_error: float = 0.0


@dataclass
class CuriositySignal:
    """
    A curiosity signal.
    """
    type: CuriosityType
    magnitude: float
    target: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class IntrinsicReward:
    """
    An intrinsic reward signal.
    """
    source: MotivationType
    value: float
    state_id: str
    action_id: str


# ============================================================================
# NOVELTY DETECTOR
# ============================================================================

class NoveltyDetector:
    """
    Detect novelty in states.

    "Ba'el detects the new." — Ba'el
    """

    def __init__(self, decay_rate: float = 0.1):
        """Initialize detector."""
        self._state_counts: Dict[str, int] = defaultdict(int)
        self._feature_stats: Dict[str, List[float]] = defaultdict(list)
        self._decay_rate = decay_rate
        self._lock = threading.RLock()

    def compute_novelty(
        self,
        state: State
    ) -> float:
        """Compute novelty of state."""
        with self._lock:
            # Count-based novelty
            state_key = self._state_key(state)
            count = self._state_counts.get(state_key, 0)
            count_novelty = 1.0 / (1.0 + count)

            # Feature-based novelty
            feature_novelty = self._feature_novelty(state)

            # Combine
            novelty = (count_novelty + feature_novelty) / 2

            return novelty

    def _state_key(self, state: State) -> str:
        """Create hashable key for state."""
        features = sorted(state.features.items())
        return str(features)

    def _feature_novelty(self, state: State) -> float:
        """Compute feature-based novelty."""
        if not state.features:
            return 1.0

        novelties = []

        for feature, value in state.features.items():
            history = self._feature_stats.get(feature, [])

            if not history:
                novelties.append(1.0)
            else:
                mean = sum(history) / len(history)
                std = math.sqrt(sum((x - mean) ** 2 for x in history) / len(history)) + 0.01

                # Novelty = deviation from mean
                z = abs(value - mean) / std
                novelty = min(1.0, z / 3.0)  # Normalize
                novelties.append(novelty)

        return sum(novelties) / len(novelties)

    def update(self, state: State) -> None:
        """Update novelty statistics."""
        with self._lock:
            state_key = self._state_key(state)
            self._state_counts[state_key] += 1

            for feature, value in state.features.items():
                self._feature_stats[feature].append(value)

                # Keep limited history
                if len(self._feature_stats[feature]) > 1000:
                    self._feature_stats[feature] = self._feature_stats[feature][-1000:]

    def decay(self) -> None:
        """Decay novelty over time."""
        with self._lock:
            for key in self._state_counts:
                self._state_counts[key] = max(0, self._state_counts[key] - 1)


# ============================================================================
# PREDICTION ERROR
# ============================================================================

class PredictionErrorComputer:
    """
    Compute prediction errors for curiosity.

    "Ba'el learns from surprises." — Ba'el
    """

    def __init__(self):
        """Initialize computer."""
        self._predictions: Dict[str, Prediction] = {}
        self._pred_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._pred_counter += 1
        return f"pred_{self._pred_counter}"

    def predict(
        self,
        state: State,
        action: Action,
        world_model: Callable[[State, Action], Dict[str, float]] = None
    ) -> Prediction:
        """Make prediction about next state."""
        with self._lock:
            if world_model:
                predicted = world_model(state, action)
            else:
                # Default: slight change
                predicted = {
                    k: v + random.gauss(0, 0.1)
                    for k, v in state.features.items()
                }

            pred = Prediction(
                id=self._generate_id(),
                input_state=state.id,
                action=action.id,
                predicted_state=predicted
            )

            self._predictions[pred.id] = pred
            return pred

    def compute_error(
        self,
        prediction: Prediction,
        actual_state: State
    ) -> float:
        """Compute prediction error."""
        with self._lock:
            prediction.actual_state = actual_state.features.copy()

            # Mean squared error
            error = 0.0
            count = 0

            for key, predicted_value in prediction.predicted_state.items():
                actual_value = actual_state.features.get(key, 0.0)
                error += (predicted_value - actual_value) ** 2
                count += 1

            if count == 0:
                return 0.0

            mse = error / count
            prediction.prediction_error = mse

            return mse

    def get_average_error(self) -> float:
        """Get average prediction error."""
        if not self._predictions:
            return 0.0

        errors = [p.prediction_error for p in self._predictions.values() if p.prediction_error > 0]
        if not errors:
            return 0.0

        return sum(errors) / len(errors)


# ============================================================================
# INFORMATION GAIN
# ============================================================================

class InformationGainComputer:
    """
    Compute information gain for exploration.

    "Ba'el maximizes information." — Ba'el
    """

    def __init__(self):
        """Initialize computer."""
        self._beliefs: Dict[str, Dict[str, float]] = {}  # Probability distributions
        self._lock = threading.RLock()

    def compute_entropy(
        self,
        distribution: Dict[str, float]
    ) -> float:
        """Compute entropy of distribution."""
        entropy = 0.0

        for prob in distribution.values():
            if prob > 0:
                entropy -= prob * math.log2(prob)

        return entropy

    def compute_information_gain(
        self,
        prior: Dict[str, float],
        posterior: Dict[str, float]
    ) -> float:
        """Compute information gain (entropy reduction)."""
        with self._lock:
            prior_entropy = self.compute_entropy(prior)
            posterior_entropy = self.compute_entropy(posterior)

            return max(0, prior_entropy - posterior_entropy)

    def expected_information_gain(
        self,
        state: State,
        action: Action,
        possible_outcomes: List[Dict[str, float]] = None
    ) -> float:
        """Compute expected information gain."""
        with self._lock:
            if not possible_outcomes:
                # Estimate based on action properties
                return action.expected_learning

            # Average entropy reduction across outcomes
            gains = []

            for outcome in possible_outcomes:
                current_belief = self._beliefs.get(state.id, {})
                gain = self.compute_information_gain(current_belief, outcome)
                gains.append(gain)

            return sum(gains) / len(gains) if gains else 0.0


# ============================================================================
# CURIOSITY ENGINE
# ============================================================================

class CuriosityEngine:
    """
    Complete curiosity and intrinsic motivation engine.

    "Ba'el's drive to explore." — Ba'el
    """

    def __init__(
        self,
        curiosity_weight: float = 1.0,
        novelty_weight: float = 0.5,
        learning_weight: float = 0.5
    ):
        """Initialize engine."""
        self._curiosity_weight = curiosity_weight
        self._novelty_weight = novelty_weight
        self._learning_weight = learning_weight

        self._novelty = NoveltyDetector()
        self._prediction = PredictionErrorComputer()
        self._information = InformationGainComputer()

        self._states: Dict[str, State] = {}
        self._actions: Dict[str, Action] = {}
        self._signals: List[CuriositySignal] = []
        self._rewards: List[IntrinsicReward] = []

        self._state_counter = 0
        self._action_counter = 0
        self._lock = threading.RLock()

    def _generate_state_id(self) -> str:
        self._state_counter += 1
        return f"state_{self._state_counter}"

    def _generate_action_id(self) -> str:
        self._action_counter += 1
        return f"action_{self._action_counter}"

    # State/Action management

    def create_state(
        self,
        features: Dict[str, float]
    ) -> State:
        """Create state."""
        state = State(
            id=self._generate_state_id(),
            features=features
        )
        self._states[state.id] = state
        return state

    def create_action(
        self,
        name: str,
        expected_novelty: float = 0.5,
        expected_learning: float = 0.5
    ) -> Action:
        """Create action."""
        action = Action(
            id=self._generate_action_id(),
            name=name,
            expected_novelty=expected_novelty,
            expected_learning=expected_learning
        )
        self._actions[action.id] = action
        return action

    # Curiosity computation

    def compute_curiosity(
        self,
        state: State,
        action: Action = None
    ) -> CuriositySignal:
        """Compute curiosity for state (and optionally action)."""
        with self._lock:
            # Novelty component
            novelty = self._novelty.compute_novelty(state)

            # Prediction error component
            avg_error = self._prediction.get_average_error()

            # Combine
            curiosity = (
                self._novelty_weight * novelty +
                self._learning_weight * avg_error
            ) * self._curiosity_weight

            # Determine type
            if novelty > 0.7:
                ctype = CuriosityType.PERCEPTUAL
            elif avg_error > 0.5:
                ctype = CuriosityType.EPISTEMIC
            else:
                ctype = CuriosityType.DIVERSIVE

            signal = CuriositySignal(
                type=ctype,
                magnitude=curiosity,
                target=state.id
            )

            self._signals.append(signal)

            return signal

    def compute_intrinsic_reward(
        self,
        state: State,
        action: Action,
        next_state: State
    ) -> IntrinsicReward:
        """Compute intrinsic reward for transition."""
        with self._lock:
            # Novelty-based reward
            novelty = self._novelty.compute_novelty(next_state)

            # Prediction error reward
            pred = self._prediction.predict(state, action)
            error = self._prediction.compute_error(pred, next_state)

            # Information gain reward
            info_gain = self._information.expected_information_gain(
                state, action
            )

            # Combine
            reward_value = (
                self._novelty_weight * novelty +
                self._learning_weight * (error + info_gain) / 2
            )

            # Determine source
            if novelty > error:
                source = MotivationType.CURIOSITY
            else:
                source = MotivationType.MASTERY

            reward = IntrinsicReward(
                source=source,
                value=reward_value,
                state_id=state.id,
                action_id=action.id
            )

            self._rewards.append(reward)

            # Update novelty detector
            self._novelty.update(next_state)

            return reward

    # Exploration

    def select_action(
        self,
        state: State,
        actions: List[Action],
        strategy: ExplorationStrategy = ExplorationStrategy.NOVELTY_SEEKING
    ) -> Action:
        """Select action based on curiosity."""
        with self._lock:
            if not actions:
                raise ValueError("No actions available")

            if strategy == ExplorationStrategy.RANDOM:
                return random.choice(actions)

            # Score each action
            scores = {}

            for action in actions:
                if strategy == ExplorationStrategy.NOVELTY_SEEKING:
                    scores[action.id] = action.expected_novelty

                elif strategy == ExplorationStrategy.UNCERTAINTY_REDUCTION:
                    scores[action.id] = 1.0 - action.expected_learning

                elif strategy == ExplorationStrategy.INFORMATION_GAIN:
                    scores[action.id] = self._information.expected_information_gain(
                        state, action
                    )

                elif strategy == ExplorationStrategy.COMPETENCE_PROGRESS:
                    scores[action.id] = action.expected_learning * 0.5 + action.expected_novelty * 0.5

            # Select best
            best_id = max(scores, key=scores.get)

            for action in actions:
                if action.id == best_id:
                    return action

            return actions[0]

    # Updates

    def visit(self, state: State) -> None:
        """Record visit to state."""
        with self._lock:
            state.visits += 1
            state.last_visit = time.time()
            state.novelty = self._novelty.compute_novelty(state)
            self._novelty.update(state)

    # Analysis

    def get_most_curious(self, top_k: int = 5) -> List[State]:
        """Get most curiosity-inducing states."""
        states = list(self._states.values())
        states.sort(key=lambda s: s.novelty, reverse=True)
        return states[:top_k]

    def get_average_curiosity(self) -> float:
        """Get average curiosity signal."""
        if not self._signals:
            return 0.0
        return sum(s.magnitude for s in self._signals) / len(self._signals)

    @property
    def signals(self) -> List[CuriositySignal]:
        return list(self._signals)

    @property
    def rewards(self) -> List[IntrinsicReward]:
        return list(self._rewards)

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'states': len(self._states),
            'actions': len(self._actions),
            'signals': len(self._signals),
            'rewards': len(self._rewards),
            'average_curiosity': self.get_average_curiosity()
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_curiosity_engine(
    curiosity_weight: float = 1.0
) -> CuriosityEngine:
    """Create curiosity engine."""
    return CuriosityEngine(curiosity_weight=curiosity_weight)


def compute_novelty(
    features: Dict[str, float]
) -> float:
    """Quick novelty computation."""
    detector = NoveltyDetector()
    state = State(id="temp", features=features)
    return detector.compute_novelty(state)
