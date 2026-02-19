"""
BAEL Emotion Regulation Engine
===============================

Affective processing and emotion regulation.
Gross's process model of emotion regulation.

"Ba'el masters emotions." — Ba'el
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

logger = logging.getLogger("BAEL.EmotionRegulation")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class EmotionType(Enum):
    """Basic emotion types."""
    JOY = auto()
    SADNESS = auto()
    ANGER = auto()
    FEAR = auto()
    DISGUST = auto()
    SURPRISE = auto()
    TRUST = auto()
    ANTICIPATION = auto()


class Valence(Enum):
    """Emotional valence."""
    POSITIVE = auto()
    NEGATIVE = auto()
    NEUTRAL = auto()


class Arousal(Enum):
    """Arousal level."""
    HIGH = auto()
    MEDIUM = auto()
    LOW = auto()


class RegulationStrategy(Enum):
    """Emotion regulation strategies (Gross model)."""
    SITUATION_SELECTION = auto()     # Choose situations
    SITUATION_MODIFICATION = auto()  # Change situation
    ATTENTION_DEPLOYMENT = auto()    # Focus attention
    COGNITIVE_REAPPRAISAL = auto()   # Reinterpret meaning
    RESPONSE_MODULATION = auto()     # Modify response


class AppraisalDimension(Enum):
    """Appraisal dimensions."""
    RELEVANCE = auto()        # Personal relevance
    CONGRUENCE = auto()       # Goal congruence
    CONTROLLABILITY = auto()  # Can influence?
    AGENCY = auto()           # Self/other caused
    CERTAINTY = auto()        # Outcome certainty
    NOVELTY = auto()          # Unexpectedness


@dataclass
class Stimulus:
    """
    An emotional stimulus.
    """
    id: str
    content: str
    intensity: float = 0.5
    features: Dict[str, float] = field(default_factory=dict)


@dataclass
class Appraisal:
    """
    Cognitive appraisal of stimulus.
    """
    stimulus_id: str
    dimensions: Dict[AppraisalDimension, float]

    @property
    def is_threatening(self) -> bool:
        return (
            self.dimensions.get(AppraisalDimension.RELEVANCE, 0) > 0.5 and
            self.dimensions.get(AppraisalDimension.CONGRUENCE, 1) < 0.5
        )


@dataclass
class Emotion:
    """
    An emotional state.
    """
    type: EmotionType
    intensity: float  # 0-1
    valence: Valence
    arousal: Arousal
    trigger: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class EmotionalState:
    """
    Complete emotional state.
    """
    emotions: Dict[EmotionType, float]  # Type -> intensity
    dominant: Optional[EmotionType] = None
    valence: float = 0.0  # -1 to 1
    arousal: float = 0.5  # 0 to 1

    def __post_init__(self):
        if self.emotions and not self.dominant:
            self.dominant = max(self.emotions, key=self.emotions.get)


@dataclass
class RegulationAction:
    """
    A regulation action.
    """
    strategy: RegulationStrategy
    target_emotion: EmotionType
    intensity: float
    success_probability: float = 0.5
    timestamp: float = field(default_factory=time.time)


@dataclass
class RegulationResult:
    """
    Result of emotion regulation.
    """
    initial_state: EmotionalState
    final_state: EmotionalState
    strategy_used: RegulationStrategy
    intensity_change: float
    success: bool


# ============================================================================
# APPRAISAL SYSTEM
# ============================================================================

class AppraisalSystem:
    """
    Cognitive appraisal of stimuli.

    "Ba'el evaluates meaning." — Ba'el
    """

    def __init__(self):
        """Initialize appraisal system."""
        # Goals and values
        self._goals: Dict[str, float] = {}  # Goal -> importance
        self._values: Dict[str, float] = {}  # Value -> importance

        self._lock = threading.RLock()

    def set_goal(
        self,
        goal: str,
        importance: float
    ) -> None:
        """Set goal importance."""
        self._goals[goal] = max(0, min(1, importance))

    def set_value(
        self,
        value: str,
        importance: float
    ) -> None:
        """Set value importance."""
        self._values[value] = max(0, min(1, importance))

    def appraise(
        self,
        stimulus: Stimulus
    ) -> Appraisal:
        """Appraise stimulus."""
        with self._lock:
            dimensions = {}

            # Relevance - based on feature matching to goals
            relevance = stimulus.intensity
            for goal, importance in self._goals.items():
                if goal.lower() in stimulus.content.lower():
                    relevance = max(relevance, importance)
            dimensions[AppraisalDimension.RELEVANCE] = relevance

            # Congruence - goal support/threat
            congruence = 0.5
            positive_words = ['good', 'success', 'achieve', 'win', 'help']
            negative_words = ['bad', 'fail', 'lose', 'threat', 'harm']

            for word in positive_words:
                if word in stimulus.content.lower():
                    congruence += 0.1
            for word in negative_words:
                if word in stimulus.content.lower():
                    congruence -= 0.1
            dimensions[AppraisalDimension.CONGRUENCE] = max(0, min(1, congruence))

            # Controllability
            control_words = ['can', 'control', 'choice', 'decide']
            uncontrol_words = ['must', 'forced', 'inevitable', 'cannot']

            controllability = 0.5
            for word in control_words:
                if word in stimulus.content.lower():
                    controllability += 0.15
            for word in uncontrol_words:
                if word in stimulus.content.lower():
                    controllability -= 0.15
            dimensions[AppraisalDimension.CONTROLLABILITY] = max(0, min(1, controllability))

            # Agency - self vs other caused
            self_words = ['i', 'my', 'me', 'myself']
            other_words = ['they', 'their', 'someone', 'others']

            agency = 0.5
            for word in self_words:
                if word in stimulus.content.lower():
                    agency += 0.1
            for word in other_words:
                if word in stimulus.content.lower():
                    agency -= 0.1
            dimensions[AppraisalDimension.AGENCY] = max(0, min(1, agency))

            # Certainty
            certain_words = ['definitely', 'certain', 'sure', 'will']
            uncertain_words = ['maybe', 'might', 'uncertain', 'possibly']

            certainty = 0.5
            for word in certain_words:
                if word in stimulus.content.lower():
                    certainty += 0.15
            for word in uncertain_words:
                if word in stimulus.content.lower():
                    certainty -= 0.15
            dimensions[AppraisalDimension.CERTAINTY] = max(0, min(1, certainty))

            # Novelty
            dimensions[AppraisalDimension.NOVELTY] = stimulus.features.get('novelty', 0.5)

            return Appraisal(
                stimulus_id=stimulus.id,
                dimensions=dimensions
            )


# ============================================================================
# EMOTION GENERATOR
# ============================================================================

class EmotionGenerator:
    """
    Generate emotions from appraisals.

    "Ba'el feels appropriately." — Ba'el
    """

    def __init__(self):
        """Initialize generator."""
        self._lock = threading.RLock()

    def generate(
        self,
        appraisal: Appraisal
    ) -> EmotionalState:
        """Generate emotions from appraisal."""
        with self._lock:
            emotions = {}

            relevance = appraisal.dimensions.get(AppraisalDimension.RELEVANCE, 0.5)
            congruence = appraisal.dimensions.get(AppraisalDimension.CONGRUENCE, 0.5)
            controllability = appraisal.dimensions.get(AppraisalDimension.CONTROLLABILITY, 0.5)
            agency = appraisal.dimensions.get(AppraisalDimension.AGENCY, 0.5)
            certainty = appraisal.dimensions.get(AppraisalDimension.CERTAINTY, 0.5)
            novelty = appraisal.dimensions.get(AppraisalDimension.NOVELTY, 0.5)

            # Joy: high congruence, high relevance
            joy = congruence * relevance
            emotions[EmotionType.JOY] = max(0, min(1, joy))

            # Sadness: low congruence, high relevance, low control
            sadness = (1 - congruence) * relevance * (1 - controllability)
            emotions[EmotionType.SADNESS] = max(0, min(1, sadness))

            # Anger: low congruence, high relevance, other-caused
            anger = (1 - congruence) * relevance * (1 - agency)
            emotions[EmotionType.ANGER] = max(0, min(1, anger))

            # Fear: low congruence, high relevance, low certainty
            fear = (1 - congruence) * relevance * certainty
            emotions[EmotionType.FEAR] = max(0, min(1, fear))

            # Surprise: high novelty
            surprise = novelty * relevance
            emotions[EmotionType.SURPRISE] = max(0, min(1, surprise))

            # Trust: high congruence, high controllability
            trust = congruence * controllability
            emotions[EmotionType.TRUST] = max(0, min(1, trust))

            # Anticipation: future-oriented, moderate certainty
            anticipation = relevance * (1 - abs(certainty - 0.5) * 2)
            emotions[EmotionType.ANTICIPATION] = max(0, min(1, anticipation))

            # Compute overall valence and arousal
            positive = emotions[EmotionType.JOY] + emotions[EmotionType.TRUST]
            negative = emotions[EmotionType.SADNESS] + emotions[EmotionType.ANGER] + emotions[EmotionType.FEAR]

            valence = (positive - negative) / max(1, positive + negative)
            arousal = (emotions[EmotionType.ANGER] + emotions[EmotionType.FEAR] +
                      emotions[EmotionType.SURPRISE] + emotions[EmotionType.JOY]) / 4

            return EmotionalState(
                emotions=emotions,
                valence=valence,
                arousal=arousal
            )


# ============================================================================
# EMOTION REGULATOR
# ============================================================================

class EmotionRegulator:
    """
    Regulate emotional states.

    "Ba'el regulates affect." — Ba'el
    """

    def __init__(self):
        """Initialize regulator."""
        self._strategy_effectiveness: Dict[RegulationStrategy, float] = {
            RegulationStrategy.SITUATION_SELECTION: 0.7,
            RegulationStrategy.SITUATION_MODIFICATION: 0.6,
            RegulationStrategy.ATTENTION_DEPLOYMENT: 0.5,
            RegulationStrategy.COGNITIVE_REAPPRAISAL: 0.65,
            RegulationStrategy.RESPONSE_MODULATION: 0.4
        }

        self._lock = threading.RLock()

    def select_strategy(
        self,
        state: EmotionalState,
        target_emotion: EmotionType
    ) -> RegulationStrategy:
        """Select best regulation strategy."""
        with self._lock:
            intensity = state.emotions.get(target_emotion, 0)

            # High intensity: earlier strategies better
            if intensity > 0.7:
                return RegulationStrategy.SITUATION_SELECTION
            elif intensity > 0.5:
                return RegulationStrategy.COGNITIVE_REAPPRAISAL
            else:
                return RegulationStrategy.ATTENTION_DEPLOYMENT

    def apply_strategy(
        self,
        state: EmotionalState,
        strategy: RegulationStrategy,
        target_emotion: EmotionType,
        effort: float = 0.5
    ) -> RegulationResult:
        """Apply regulation strategy."""
        with self._lock:
            initial = copy.deepcopy(state)

            # Get effectiveness
            base_effectiveness = self._strategy_effectiveness.get(strategy, 0.5)
            actual_effectiveness = base_effectiveness * effort * (0.8 + random.random() * 0.4)

            # Apply regulation
            new_emotions = state.emotions.copy()
            current = new_emotions.get(target_emotion, 0)

            if strategy == RegulationStrategy.SITUATION_SELECTION:
                # Avoid situation entirely
                reduction = current * actual_effectiveness
                new_emotions[target_emotion] = max(0, current - reduction)

            elif strategy == RegulationStrategy.SITUATION_MODIFICATION:
                # Change aspects of situation
                reduction = current * actual_effectiveness * 0.8
                new_emotions[target_emotion] = max(0, current - reduction)

            elif strategy == RegulationStrategy.ATTENTION_DEPLOYMENT:
                # Redirect attention
                reduction = current * actual_effectiveness * 0.6
                new_emotions[target_emotion] = max(0, current - reduction)
                # May increase positive emotions
                if EmotionType.JOY in new_emotions:
                    new_emotions[EmotionType.JOY] = min(1, new_emotions[EmotionType.JOY] + 0.1)

            elif strategy == RegulationStrategy.COGNITIVE_REAPPRAISAL:
                # Reinterpret meaning
                reduction = current * actual_effectiveness * 0.7
                new_emotions[target_emotion] = max(0, current - reduction)

            elif strategy == RegulationStrategy.RESPONSE_MODULATION:
                # Suppress expression (less effective long-term)
                reduction = current * actual_effectiveness * 0.3
                new_emotions[target_emotion] = max(0, current - reduction)

            final = EmotionalState(emotions=new_emotions)

            intensity_change = new_emotions[target_emotion] - current
            success = intensity_change < -0.1

            return RegulationResult(
                initial_state=initial,
                final_state=final,
                strategy_used=strategy,
                intensity_change=intensity_change,
                success=success
            )


# ============================================================================
# EMOTION REGULATION ENGINE
# ============================================================================

class EmotionRegulationEngine:
    """
    Complete emotion regulation engine.

    "Ba'el's emotional wisdom." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._appraisal = AppraisalSystem()
        self._generator = EmotionGenerator()
        self._regulator = EmotionRegulator()

        self._current_state = EmotionalState(emotions={e: 0.0 for e in EmotionType})
        self._history: List[Tuple[Stimulus, EmotionalState]] = []

        self._stimulus_counter = 0
        self._lock = threading.RLock()

    def _generate_stimulus_id(self) -> str:
        self._stimulus_counter += 1
        return f"stim_{self._stimulus_counter}"

    # Configuration

    def set_goal(
        self,
        goal: str,
        importance: float = 0.5
    ) -> None:
        """Set goal."""
        self._appraisal.set_goal(goal, importance)

    def set_value(
        self,
        value: str,
        importance: float = 0.5
    ) -> None:
        """Set value."""
        self._appraisal.set_value(value, importance)

    # Processing

    def process_stimulus(
        self,
        content: str,
        intensity: float = 0.5
    ) -> EmotionalState:
        """Process emotional stimulus."""
        with self._lock:
            stimulus = Stimulus(
                id=self._generate_stimulus_id(),
                content=content,
                intensity=intensity
            )

            # Appraise
            appraisal = self._appraisal.appraise(stimulus)

            # Generate emotion
            generated = self._generator.generate(appraisal)

            # Blend with current state
            for etype, eint in generated.emotions.items():
                current = self._current_state.emotions.get(etype, 0)
                self._current_state.emotions[etype] = current * 0.7 + eint * 0.3

            # Update overall
            self._current_state.valence = generated.valence
            self._current_state.arousal = generated.arousal
            self._current_state.dominant = max(
                self._current_state.emotions,
                key=self._current_state.emotions.get
            )

            self._history.append((stimulus, copy.deepcopy(self._current_state)))

            return self._current_state

    # Regulation

    def regulate(
        self,
        target_emotion: EmotionType = None,
        strategy: RegulationStrategy = None,
        effort: float = 0.5
    ) -> RegulationResult:
        """Regulate emotional state."""
        with self._lock:
            # Default to dominant negative emotion
            if target_emotion is None:
                negatives = [EmotionType.SADNESS, EmotionType.ANGER, EmotionType.FEAR]
                intensities = [(e, self._current_state.emotions.get(e, 0)) for e in negatives]
                intensities.sort(key=lambda x: x[1], reverse=True)
                target_emotion = intensities[0][0]

            # Auto-select strategy if not provided
            if strategy is None:
                strategy = self._regulator.select_strategy(self._current_state, target_emotion)

            # Apply regulation
            result = self._regulator.apply_strategy(
                self._current_state, strategy, target_emotion, effort
            )

            # Update current state
            self._current_state = result.final_state

            return result

    def reappraise(
        self,
        new_interpretation: str
    ) -> EmotionalState:
        """Cognitively reappraise situation."""
        with self._lock:
            # Process new interpretation
            new_state = self.process_stimulus(new_interpretation, intensity=0.3)

            # Blend more heavily toward new appraisal
            for etype in EmotionType:
                old = self._current_state.emotions.get(etype, 0)
                new = new_state.emotions.get(etype, 0)
                self._current_state.emotions[etype] = old * 0.4 + new * 0.6

            return self._current_state

    # State access

    @property
    def current_state(self) -> EmotionalState:
        return copy.deepcopy(self._current_state)

    @property
    def dominant_emotion(self) -> EmotionType:
        return self._current_state.dominant

    @property
    def valence(self) -> float:
        return self._current_state.valence

    @property
    def arousal(self) -> float:
        return self._current_state.arousal

    def get_emotion_intensity(self, etype: EmotionType) -> float:
        return self._current_state.emotions.get(etype, 0)

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'dominant': self.dominant_emotion.name if self.dominant_emotion else None,
            'valence': self.valence,
            'arousal': self.arousal,
            'emotions': {e.name: v for e, v in self._current_state.emotions.items()},
            'history_length': len(self._history)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_emotion_engine() -> EmotionRegulationEngine:
    """Create emotion regulation engine."""
    return EmotionRegulationEngine()


def process_emotion(
    content: str,
    intensity: float = 0.5
) -> Dict[str, float]:
    """Quick emotion processing."""
    engine = create_emotion_engine()
    state = engine.process_stimulus(content, intensity)
    return {e.name: v for e, v in state.emotions.items()}
