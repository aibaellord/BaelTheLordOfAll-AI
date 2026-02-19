"""
BAEL Emotional Enhancement Engine
===================================

Emotional events are better remembered.
McGaugh's memory modulation hypothesis.

"Ba'el remembers what stirs the heart." — Ba'el
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

logger = logging.getLogger("BAEL.EmotionalEnhancement")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class EmotionValence(Enum):
    """Valence of emotion."""
    POSITIVE = auto()
    NEGATIVE = auto()
    NEUTRAL = auto()


class EmotionArousal(Enum):
    """Arousal level."""
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()


class MemoryComponent(Enum):
    """Component of emotional memory."""
    CENTRAL = auto()         # Core emotional content
    PERIPHERAL = auto()      # Background details
    SOURCE = auto()          # Context details
    TEMPORAL = auto()        # Time information


class ConsolidationType(Enum):
    """Type of consolidation."""
    IMMEDIATE = auto()
    DELAYED = auto()         # Post-encoding
    SLEEP = auto()           # Sleep-dependent


class StressLevel(Enum):
    """Level of stress."""
    NONE = auto()
    MILD = auto()
    MODERATE = auto()
    SEVERE = auto()


@dataclass
class EmotionalEvent:
    """
    An emotional event.
    """
    id: str
    content: str
    valence: EmotionValence
    arousal: EmotionArousal
    central_details: List[str]
    peripheral_details: List[str]


@dataclass
class EncodingState:
    """
    State during encoding.
    """
    stress_level: StressLevel
    attention_focus: float
    arousal_level: float


@dataclass
class MemoryTrace:
    """
    Memory trace for emotional event.
    """
    event: EmotionalEvent
    encoding_state: EncodingState
    central_strength: float
    peripheral_strength: float
    consolidation_time: float


@dataclass
class RecallResult:
    """
    Result of recall.
    """
    event: EmotionalEvent
    central_recall: float
    peripheral_recall: float
    confidence: float
    vividness: float


@dataclass
class EmotionalMetrics:
    """
    Emotional enhancement metrics.
    """
    emotional_enhancement: float
    central_vs_peripheral: float
    by_valence: Dict[str, float]
    by_arousal: Dict[str, float]


# ============================================================================
# EMOTIONAL ENHANCEMENT MODEL
# ============================================================================

class EmotionalEnhancementModel:
    """
    Model of emotional memory enhancement.

    "Ba'el's emotion-memory model." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Base memory strength
        self._base_strength = 0.40

        # Emotional enhancement
        self._arousal_effect = 0.25
        self._valence_effect = 0.05  # Small effect

        # Central vs peripheral trade-off
        self._attention_narrowing = 0.30

        # Consolidation effects
        self._consolidation_boost = 0.15
        self._sleep_boost = 0.10

        # Stress effects
        self._stress_effects = {
            StressLevel.NONE: 0.0,
            StressLevel.MILD: 0.05,
            StressLevel.MODERATE: 0.02,
            StressLevel.SEVERE: -0.10  # Impairs
        }

        # Arousal levels
        self._arousal_values = {
            EmotionArousal.LOW: 0.3,
            EmotionArousal.MEDIUM: 0.6,
            EmotionArousal.HIGH: 0.9
        }

        # Amygdala modulation
        self._amygdala_effect = 0.20

        # Decay rates
        self._neutral_decay = 0.03
        self._emotional_decay = 0.01  # Slower

        self._lock = threading.RLock()

    def calculate_encoding_strength(
        self,
        event: EmotionalEvent,
        state: EncodingState,
        component: MemoryComponent
    ) -> float:
        """Calculate encoding strength."""
        strength = self._base_strength

        # Arousal effect
        arousal_value = self._arousal_values[event.arousal]
        strength += arousal_value * self._arousal_effect

        # Valence effect (negative slightly stronger)
        if event.valence == EmotionValence.NEGATIVE:
            strength += self._valence_effect
        elif event.valence == EmotionValence.POSITIVE:
            strength += self._valence_effect * 0.7

        # Component-specific effects
        if component == MemoryComponent.CENTRAL:
            # Attention narrows to central
            strength += state.attention_focus * 0.2
        elif component == MemoryComponent.PERIPHERAL:
            # Peripheral suffers
            if event.arousal == EmotionArousal.HIGH:
                strength -= self._attention_narrowing

        # Stress effects
        strength += self._stress_effects[state.stress_level]

        # Add noise
        strength += random.uniform(-0.1, 0.1)

        return max(0.1, min(0.95, strength))

    def apply_consolidation(
        self,
        strength: float,
        is_emotional: bool,
        consolidation_type: ConsolidationType
    ) -> float:
        """Apply consolidation effects."""
        if consolidation_type == ConsolidationType.IMMEDIATE:
            return strength

        boost = self._consolidation_boost

        if consolidation_type == ConsolidationType.SLEEP:
            boost += self._sleep_boost

        # Emotional events benefit more
        if is_emotional:
            boost *= 1.3

        return min(0.95, strength + boost)

    def calculate_decay(
        self,
        strength: float,
        is_emotional: bool,
        time_days: float
    ) -> float:
        """Calculate memory decay."""
        decay_rate = self._emotional_decay if is_emotional else self._neutral_decay

        # Exponential decay
        decayed = strength * math.exp(-decay_rate * time_days)

        return max(0.05, decayed)

    def calculate_vividness(
        self,
        arousal: EmotionArousal,
        retention_interval: float = 0.0
    ) -> float:
        """Calculate memory vividness."""
        base = 0.5

        # Arousal increases vividness
        arousal_value = self._arousal_values[arousal]
        base += arousal_value * 0.3

        # Vividness decays but more slowly for emotional
        if retention_interval > 0:
            decay = 0.01 if arousal != EmotionArousal.LOW else 0.02
            base *= math.exp(-decay * retention_interval)

        return max(0.2, min(0.95, base))


# ============================================================================
# EMOTIONAL ENHANCEMENT SYSTEM
# ============================================================================

class EmotionalEnhancementSystem:
    """
    Emotional enhancement simulation system.

    "Ba'el's emotion system." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = EmotionalEnhancementModel()

        self._events: Dict[str, EmotionalEvent] = {}
        self._traces: Dict[str, MemoryTrace] = {}

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"event_{self._counter}"

    def create_event(
        self,
        content: str,
        valence: EmotionValence,
        arousal: EmotionArousal,
        central_details: Optional[List[str]] = None,
        peripheral_details: Optional[List[str]] = None
    ) -> EmotionalEvent:
        """Create emotional event."""
        event = EmotionalEvent(
            id=self._generate_id(),
            content=content,
            valence=valence,
            arousal=arousal,
            central_details=central_details or [f"central_{i}" for i in range(3)],
            peripheral_details=peripheral_details or [f"peripheral_{i}" for i in range(5)]
        )

        self._events[event.id] = event

        return event

    def encode_event(
        self,
        event_id: str,
        state: Optional[EncodingState] = None
    ) -> MemoryTrace:
        """Encode emotional event."""
        event = self._events.get(event_id)
        if not event:
            return None

        if state is None:
            state = EncodingState(
                stress_level=StressLevel.MILD,
                attention_focus=0.7,
                arousal_level=self._model._arousal_values[event.arousal]
            )

        central_strength = self._model.calculate_encoding_strength(
            event, state, MemoryComponent.CENTRAL
        )

        peripheral_strength = self._model.calculate_encoding_strength(
            event, state, MemoryComponent.PERIPHERAL
        )

        trace = MemoryTrace(
            event=event,
            encoding_state=state,
            central_strength=central_strength,
            peripheral_strength=peripheral_strength,
            consolidation_time=0.0
        )

        self._traces[event_id] = trace

        return trace

    def consolidate(
        self,
        event_id: str,
        consolidation_type: ConsolidationType,
        time_hours: float = 8.0
    ) -> MemoryTrace:
        """Apply consolidation."""
        trace = self._traces.get(event_id)
        if not trace:
            return None

        is_emotional = trace.event.arousal != EmotionArousal.LOW

        trace.central_strength = self._model.apply_consolidation(
            trace.central_strength, is_emotional, consolidation_type
        )

        trace.peripheral_strength = self._model.apply_consolidation(
            trace.peripheral_strength, is_emotional, consolidation_type
        )

        trace.consolidation_time += time_hours

        return trace

    def recall_event(
        self,
        event_id: str,
        retention_days: float = 0.0
    ) -> RecallResult:
        """Recall emotional event."""
        trace = self._traces.get(event_id)
        if not trace:
            return None

        is_emotional = trace.event.arousal != EmotionArousal.LOW

        # Apply decay
        central = self._model.calculate_decay(
            trace.central_strength, is_emotional, retention_days
        )

        peripheral = self._model.calculate_decay(
            trace.peripheral_strength, is_emotional, retention_days
        )

        # Calculate vividness
        vividness = self._model.calculate_vividness(
            trace.event.arousal, retention_days
        )

        # Calculate confidence
        confidence = (central + peripheral) / 2 + vividness * 0.1

        return RecallResult(
            event=trace.event,
            central_recall=central,
            peripheral_recall=peripheral,
            confidence=min(0.95, confidence),
            vividness=vividness
        )


# ============================================================================
# EMOTIONAL ENHANCEMENT PARADIGM
# ============================================================================

class EmotionalEnhancementParadigm:
    """
    Emotional enhancement paradigm.

    "Ba'el's emotion study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_arousal_paradigm(
        self
    ) -> Dict[str, Any]:
        """Run arousal comparison paradigm."""
        system = EmotionalEnhancementSystem()

        conditions = {
            'low_arousal': EmotionArousal.LOW,
            'medium_arousal': EmotionArousal.MEDIUM,
            'high_arousal': EmotionArousal.HIGH
        }

        results = {}

        for condition, arousal in conditions.items():
            event = system.create_event(
                f"{condition}_event",
                EmotionValence.NEGATIVE,
                arousal
            )

            system.encode_event(event.id)
            result = system.recall_event(event.id)

            results[condition] = {
                'central': result.central_recall,
                'peripheral': result.peripheral_recall,
                'overall': (result.central_recall + result.peripheral_recall) / 2
            }

        enhancement = (
            results['high_arousal']['overall'] -
            results['low_arousal']['overall']
        )

        return {
            'by_arousal': results,
            'emotional_enhancement': enhancement,
            'interpretation': 'High arousal enhances memory'
        }

    def run_central_peripheral_paradigm(
        self
    ) -> Dict[str, Any]:
        """Study central vs peripheral memory."""
        system = EmotionalEnhancementSystem()
        model = system._model

        # Compare emotional vs neutral
        conditions = {
            'neutral': EmotionArousal.LOW,
            'emotional': EmotionArousal.HIGH
        }

        results = {}

        for condition, arousal in conditions.items():
            event = system.create_event(
                f"{condition}_event",
                EmotionValence.NEGATIVE,
                arousal
            )

            state = EncodingState(
                stress_level=StressLevel.MILD,
                attention_focus=0.7 if arousal == EmotionArousal.HIGH else 0.5,
                arousal_level=model._arousal_values[arousal]
            )

            system.encode_event(event.id, state)
            result = system.recall_event(event.id)

            results[condition] = {
                'central': result.central_recall,
                'peripheral': result.peripheral_recall,
                'trade_off': result.central_recall - result.peripheral_recall
            }

        return {
            'by_emotion': results,
            'interpretation': 'Emotion: better central, worse peripheral'
        }

    def run_valence_paradigm(
        self
    ) -> Dict[str, Any]:
        """Compare positive vs negative valence."""
        system = EmotionalEnhancementSystem()

        conditions = {
            'positive': EmotionValence.POSITIVE,
            'negative': EmotionValence.NEGATIVE,
            'neutral': EmotionValence.NEUTRAL
        }

        results = {}

        for condition, valence in conditions.items():
            # Match arousal for positive/negative
            arousal = (EmotionArousal.HIGH
                       if valence != EmotionValence.NEUTRAL
                       else EmotionArousal.LOW)

            event = system.create_event(
                f"{condition}_event",
                valence,
                arousal
            )

            system.encode_event(event.id)
            result = system.recall_event(event.id)

            results[condition] = {
                'overall': (result.central_recall + result.peripheral_recall) / 2
            }

        return {
            'by_valence': results,
            'interpretation': 'Negative slightly > positive > neutral'
        }

    def run_consolidation_paradigm(
        self
    ) -> Dict[str, Any]:
        """Study consolidation effects."""
        system = EmotionalEnhancementSystem()

        # Create emotional and neutral events
        emotional = system.create_event(
            "emotional", EmotionValence.NEGATIVE, EmotionArousal.HIGH
        )
        neutral = system.create_event(
            "neutral", EmotionValence.NEUTRAL, EmotionArousal.LOW
        )

        system.encode_event(emotional.id)
        system.encode_event(neutral.id)

        conditions = {
            'immediate': ConsolidationType.IMMEDIATE,
            'delayed': ConsolidationType.DELAYED,
            'sleep': ConsolidationType.SLEEP
        }

        results = {}

        for condition, cons_type in conditions.items():
            # Apply consolidation
            if cons_type != ConsolidationType.IMMEDIATE:
                system.consolidate(emotional.id, cons_type)
                system.consolidate(neutral.id, cons_type)

            emo_result = system.recall_event(emotional.id)
            neu_result = system.recall_event(neutral.id)

            results[condition] = {
                'emotional': (emo_result.central_recall + emo_result.peripheral_recall) / 2,
                'neutral': (neu_result.central_recall + neu_result.peripheral_recall) / 2
            }

        return {
            'by_consolidation': results,
            'interpretation': 'Emotional events benefit more from consolidation'
        }

    def run_retention_paradigm(
        self
    ) -> Dict[str, Any]:
        """Study retention over time."""
        system = EmotionalEnhancementSystem()

        emotional = system.create_event(
            "emotional", EmotionValence.NEGATIVE, EmotionArousal.HIGH
        )
        neutral = system.create_event(
            "neutral", EmotionValence.NEUTRAL, EmotionArousal.LOW
        )

        system.encode_event(emotional.id)
        system.encode_event(neutral.id)

        intervals = [0, 1, 7, 30]  # Days

        results = {}

        for days in intervals:
            emo_result = system.recall_event(emotional.id, days)
            neu_result = system.recall_event(neutral.id, days)

            results[f'{days}_days'] = {
                'emotional': (emo_result.central_recall + emo_result.peripheral_recall) / 2,
                'neutral': (neu_result.central_recall + neu_result.peripheral_recall) / 2
            }

        return {
            'by_retention': results,
            'interpretation': 'Emotional memories decay more slowly'
        }

    def run_stress_paradigm(
        self
    ) -> Dict[str, Any]:
        """Study stress effects on emotional memory."""
        system = EmotionalEnhancementSystem()
        model = system._model

        stress_levels = {
            'none': StressLevel.NONE,
            'mild': StressLevel.MILD,
            'moderate': StressLevel.MODERATE,
            'severe': StressLevel.SEVERE
        }

        results = {}

        for condition, stress in stress_levels.items():
            event = system.create_event(
                f"{condition}_event",
                EmotionValence.NEGATIVE,
                EmotionArousal.HIGH
            )

            state = EncodingState(
                stress_level=stress,
                attention_focus=0.7,
                arousal_level=0.8
            )

            system.encode_event(event.id, state)
            result = system.recall_event(event.id)

            results[condition] = {
                'central': result.central_recall,
                'peripheral': result.peripheral_recall
            }

        return {
            'by_stress': results,
            'interpretation': 'Moderate stress enhances, severe impairs'
        }


# ============================================================================
# EMOTIONAL ENHANCEMENT ENGINE
# ============================================================================

class EmotionalEnhancementEngine:
    """
    Complete emotional enhancement engine.

    "Ba'el's emotion engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = EmotionalEnhancementParadigm()
        self._system = EmotionalEnhancementSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Event operations

    def create_event(
        self,
        content: str,
        valence: EmotionValence,
        arousal: EmotionArousal
    ) -> EmotionalEvent:
        """Create event."""
        return self._system.create_event(content, valence, arousal)

    def encode_event(
        self,
        event_id: str
    ) -> MemoryTrace:
        """Encode event."""
        return self._system.encode_event(event_id)

    def consolidate_event(
        self,
        event_id: str,
        consolidation_type: ConsolidationType = ConsolidationType.SLEEP
    ) -> MemoryTrace:
        """Consolidate event."""
        return self._system.consolidate(event_id, consolidation_type)

    def recall_event(
        self,
        event_id: str,
        retention_days: float = 0.0
    ) -> RecallResult:
        """Recall event."""
        return self._system.recall_event(event_id, retention_days)

    # Experiments

    def run_arousal_study(
        self
    ) -> Dict[str, Any]:
        """Run arousal study."""
        result = self._paradigm.run_arousal_paradigm()
        self._experiment_results.append(result)
        return result

    def run_central_peripheral(
        self
    ) -> Dict[str, Any]:
        """Run central-peripheral study."""
        return self._paradigm.run_central_peripheral_paradigm()

    def run_valence_study(
        self
    ) -> Dict[str, Any]:
        """Run valence study."""
        return self._paradigm.run_valence_paradigm()

    def run_consolidation_study(
        self
    ) -> Dict[str, Any]:
        """Run consolidation study."""
        return self._paradigm.run_consolidation_paradigm()

    def run_retention_study(
        self
    ) -> Dict[str, Any]:
        """Run retention study."""
        return self._paradigm.run_retention_paradigm()

    def run_stress_study(
        self
    ) -> Dict[str, Any]:
        """Run stress study."""
        return self._paradigm.run_stress_paradigm()

    # Analysis

    def get_metrics(self) -> EmotionalMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_arousal_study()

        last = self._experiment_results[-1]

        return EmotionalMetrics(
            emotional_enhancement=last['emotional_enhancement'],
            central_vs_peripheral=0.0,
            by_valence={},
            by_arousal={}
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'events': len(self._system._events),
            'traces': len(self._system._traces)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_emotional_enhancement_engine() -> EmotionalEnhancementEngine:
    """Create emotional enhancement engine."""
    return EmotionalEnhancementEngine()


def demonstrate_emotional_enhancement() -> Dict[str, Any]:
    """Demonstrate emotional enhancement."""
    engine = create_emotional_enhancement_engine()

    # Arousal
    arousal = engine.run_arousal_study()

    # Central-peripheral
    central_peripheral = engine.run_central_peripheral()

    # Valence
    valence = engine.run_valence_study()

    # Retention
    retention = engine.run_retention_study()

    return {
        'arousal_effect': {
            k: f"{v['overall']:.0%}"
            for k, v in arousal['by_arousal'].items()
        },
        'emotional_enhancement': f"{arousal['emotional_enhancement']:.0%}",
        'central_peripheral': {
            k: f"trade-off: {v['trade_off']:.2f}"
            for k, v in central_peripheral['by_emotion'].items()
        },
        'valence': {
            k: f"{v['overall']:.0%}"
            for k, v in valence['by_valence'].items()
        },
        'retention_1_week': {
            k: f"{v:.0%}"
            for k, v in retention['by_retention']['7_days'].items()
        },
        'interpretation': (
            f"Emotional enhancement: {arousal['emotional_enhancement']:.0%}. "
            f"Arousal drives enhancement. Emotion narrows attention. "
            f"Emotional memories decay more slowly."
        )
    }


def get_emotional_enhancement_facts() -> Dict[str, str]:
    """Get facts about emotional enhancement."""
    return {
        'mcgaugh_2000': 'Memory modulation hypothesis',
        'mechanism': 'Amygdala modulates hippocampal consolidation',
        'arousal': 'High arousal = better memory',
        'valence': 'Negative slightly > positive',
        'trade_off': 'Better central, worse peripheral',
        'consolidation': 'Emotional events benefit more',
        'stress': 'Inverted-U relationship',
        'flashbulb': 'Related but distinct phenomenon'
    }
