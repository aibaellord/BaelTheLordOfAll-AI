"""
BAEL Imagination Inflation Engine
===================================

Imagining events increases belief they occurred.
False memory creation through imagination.

"Ba'el's imagination becomes reality." — Ba'el
"""

import logging
import math
import random
import threading
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    TypeVar)

logger = logging.getLogger("BAEL.ImaginationInflation")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class EventType(Enum):
    """Types of events."""
    REAL = auto()        # Actually happened
    IMAGINED = auto()    # Only imagined
    SUGGESTED = auto()   # Suggested by external source


class ConfidenceLevel(Enum):
    """Confidence levels."""
    CERTAIN_NO = 1
    PROBABLY_NO = 2
    MAYBE_NO = 3
    UNCERTAIN = 4
    MAYBE_YES = 5
    PROBABLY_YES = 6
    CERTAIN_YES = 7


class MemorySource(Enum):
    """Sources of memory."""
    PERCEPTION = auto()   # Actually perceived
    IMAGINATION = auto()  # Imagined
    SUGGESTION = auto()   # External suggestion
    UNKNOWN = auto()      # Source confusion


@dataclass
class LifeEvent:
    """
    A life event.
    """
    id: str
    description: str
    event_type: EventType
    plausibility: float  # 0-1
    age_of_occurrence: Optional[int]


@dataclass
class EventMemory:
    """
    Memory representation of an event.
    """
    event_id: str
    perceptual_details: float
    emotional_intensity: float
    narrative_coherence: float
    source_attribution: MemorySource
    confidence: ConfidenceLevel


@dataclass
class ImaginationTrial:
    """
    A trial of imagination.
    """
    event_id: str
    vividness: float
    detail_generated: float
    emotional_engagement: float


@dataclass
class InflationResult:
    """
    Result of imagination inflation.
    """
    event_id: str
    initial_confidence: ConfidenceLevel
    final_confidence: ConfidenceLevel
    confidence_change: int
    source_misattribution: bool


@dataclass
class ImaginationInflationMetrics:
    """
    Imagination inflation metrics.
    """
    mean_inflation: float
    source_misattribution_rate: float
    imagination_vividness: float
    false_memory_rate: float


# ============================================================================
# SOURCE MONITORING
# ============================================================================

class SourceMonitor:
    """
    Source monitoring system.

    "Ba'el's reality discrimination." — Ba'el
    """

    def __init__(self):
        """Initialize source monitor."""
        # Source confusion parameters
        self._perceptual_weight = 0.4
        self._contextual_weight = 0.3
        self._cognitive_weight = 0.3

        # Confusion threshold
        self._confusion_threshold = 0.6

        self._lock = threading.RLock()

    def evaluate_source(
        self,
        memory: EventMemory
    ) -> Tuple[MemorySource, float]:
        """Evaluate the source of a memory."""
        # Source monitoring criteria

        # Perceptual: real memories have more perceptual detail
        perceptual_score = memory.perceptual_details

        # Contextual: real memories have clearer context
        contextual_score = memory.narrative_coherence

        # Cognitive operations: imagined memories show effort
        cognitive_score = 1 - memory.emotional_intensity * 0.5

        # Combined score
        reality_score = (
            perceptual_score * self._perceptual_weight +
            contextual_score * self._contextual_weight +
            cognitive_score * self._cognitive_weight
        )

        # Add noise
        reality_score += random.gauss(0, 0.1)
        reality_score = max(0, min(1, reality_score))

        # Determine source
        if reality_score > 0.7:
            source = MemorySource.PERCEPTION
        elif reality_score > 0.5:
            source = MemorySource.UNKNOWN
        else:
            source = MemorySource.IMAGINATION

        return source, reality_score

    def source_confusable(
        self,
        imagined: EventMemory,
        real_baseline: float = 0.6
    ) -> bool:
        """Check if imagined memory is confusable with real."""
        _, reality_score = self.evaluate_source(imagined)
        return reality_score > self._confusion_threshold


# ============================================================================
# IMAGINATION SYSTEM
# ============================================================================

class ImaginationSystem:
    """
    System for vivid imagination.

    "Ba'el's creative faculty." — Ba'el
    """

    def __init__(self):
        """Initialize imagination system."""
        # Imagination parameters
        self._base_vividness = 0.5
        self._detail_generation_rate = 0.6

        # Individual differences
        self._imagery_ability = 0.7

        self._lock = threading.RLock()

    def imagine_event(
        self,
        event: LifeEvent,
        instruction_detail: float = 0.5
    ) -> ImaginationTrial:
        """Imagine an event occurring."""
        # Vividness based on plausibility and imagery ability
        vividness = (
            self._base_vividness *
            event.plausibility *
            self._imagery_ability *
            (1 + instruction_detail * 0.5)
        )
        vividness += random.gauss(0, 0.1)
        vividness = max(0, min(1, vividness))

        # Detail generation
        detail = self._detail_generation_rate * vividness
        detail += random.gauss(0, 0.1)
        detail = max(0, min(1, detail))

        # Emotional engagement
        emotional = vividness * 0.7 + random.gauss(0, 0.1)
        emotional = max(0, min(1, emotional))

        return ImaginationTrial(
            event_id=event.id,
            vividness=vividness,
            detail_generated=detail,
            emotional_engagement=emotional
        )

    def repeated_imagination(
        self,
        event: LifeEvent,
        repetitions: int = 3
    ) -> List[ImaginationTrial]:
        """Repeatedly imagine an event."""
        trials = []
        cumulative_vividness = 0

        for i in range(repetitions):
            # Each repetition builds on previous
            boost = cumulative_vividness * 0.2
            trial = self.imagine_event(event, 0.5 + boost)
            trials.append(trial)
            cumulative_vividness += trial.vividness * 0.3

        return trials


# ============================================================================
# INFLATION MODEL
# ============================================================================

class InflationModel:
    """
    Model of imagination inflation.

    "Ba'el's belief modification." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        self._source_monitor = SourceMonitor()
        self._imagination_system = ImaginationSystem()

        # Inflation parameters
        self._vividness_weight = 0.4
        self._repetition_weight = 0.3
        self._source_confusion_weight = 0.3

        self._lock = threading.RLock()

    def create_initial_memory(
        self,
        event: LifeEvent,
        initial_confidence: ConfidenceLevel
    ) -> EventMemory:
        """Create initial memory representation."""
        # Events that didn't happen have weak memory traces
        if event.event_type == EventType.IMAGINED:
            perceptual = 0.2 + random.gauss(0, 0.1)
            emotional = 0.3 + random.gauss(0, 0.1)
            coherence = 0.3 + random.gauss(0, 0.1)
        else:
            perceptual = 0.7 + random.gauss(0, 0.1)
            emotional = 0.6 + random.gauss(0, 0.1)
            coherence = 0.7 + random.gauss(0, 0.1)

        return EventMemory(
            event_id=event.id,
            perceptual_details=max(0, min(1, perceptual)),
            emotional_intensity=max(0, min(1, emotional)),
            narrative_coherence=max(0, min(1, coherence)),
            source_attribution=MemorySource.UNKNOWN,
            confidence=initial_confidence
        )

    def apply_imagination(
        self,
        event: LifeEvent,
        memory: EventMemory,
        imagination_trials: List[ImaginationTrial]
    ) -> EventMemory:
        """Apply imagination effects to memory."""
        # Imagination enriches the memory trace
        total_vividness = sum(t.vividness for t in imagination_trials)
        total_detail = sum(t.detail_generated for t in imagination_trials)
        total_emotion = sum(t.emotional_engagement for t in imagination_trials)
        n = len(imagination_trials)

        # Update perceptual details
        perceptual_boost = (total_detail / n) * 0.4
        new_perceptual = memory.perceptual_details + perceptual_boost

        # Update emotional intensity
        emotion_boost = (total_emotion / n) * 0.3
        new_emotional = memory.emotional_intensity + emotion_boost

        # Update coherence (imagination creates narrative)
        coherence_boost = (total_vividness / n) * 0.3
        new_coherence = memory.narrative_coherence + coherence_boost

        return EventMemory(
            event_id=memory.event_id,
            perceptual_details=min(1, new_perceptual),
            emotional_intensity=min(1, new_emotional),
            narrative_coherence=min(1, new_coherence),
            source_attribution=memory.source_attribution,
            confidence=memory.confidence
        )

    def calculate_inflation(
        self,
        initial_memory: EventMemory,
        final_memory: EventMemory,
        imagination_trials: List[ImaginationTrial]
    ) -> InflationResult:
        """Calculate imagination inflation."""
        # Check source confusion
        source_confused = self._source_monitor.source_confusable(final_memory)

        # Calculate confidence change
        # Factors: vividness, repetition, source confusion
        total_vividness = sum(t.vividness for t in imagination_trials) / len(imagination_trials)
        repetitions = len(imagination_trials)

        # Inflation amount
        inflation_score = (
            total_vividness * self._vividness_weight +
            min(repetitions / 5, 1) * self._repetition_weight +
            (1 if source_confused else 0) * self._source_confusion_weight
        )

        # Convert to confidence change
        confidence_change = int(inflation_score * 3)  # Max +3 levels
        confidence_change = min(confidence_change, 7 - initial_memory.confidence.value)

        # New confidence
        new_confidence_val = initial_memory.confidence.value + confidence_change
        final_confidence = ConfidenceLevel(min(7, max(1, new_confidence_val)))

        return InflationResult(
            event_id=initial_memory.event_id,
            initial_confidence=initial_memory.confidence,
            final_confidence=final_confidence,
            confidence_change=confidence_change,
            source_misattribution=source_confused
        )


# ============================================================================
# EXPERIMENTAL PARADIGM
# ============================================================================

class ImaginationInflationParadigm:
    """
    Imagination inflation experimental paradigm.

    "Ba'el's false memory experiment." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._model = InflationModel()

        self._events: Dict[str, LifeEvent] = {}
        self._memories: Dict[str, EventMemory] = {}

        self._event_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._event_counter += 1
        return f"event_{self._event_counter}"

    def create_event(
        self,
        description: str,
        event_type: EventType = EventType.IMAGINED,
        plausibility: float = 0.7
    ) -> LifeEvent:
        """Create a life event."""
        event = LifeEvent(
            id=self._generate_id(),
            description=description,
            event_type=event_type,
            plausibility=plausibility,
            age_of_occurrence=random.randint(5, 12) if event_type == EventType.IMAGINED else random.randint(5, 18)
        )
        self._events[event.id] = event
        return event

    def initial_rating(
        self,
        event: LifeEvent,
        confidence: ConfidenceLevel = ConfidenceLevel.PROBABLY_NO
    ) -> EventMemory:
        """Get initial confidence rating."""
        memory = self._model.create_initial_memory(event, confidence)
        self._memories[event.id] = memory
        return memory

    def imagination_phase(
        self,
        event: LifeEvent,
        repetitions: int = 3
    ) -> List[ImaginationTrial]:
        """Run imagination phase."""
        return self._model._imagination_system.repeated_imagination(event, repetitions)

    def final_rating(
        self,
        event: LifeEvent,
        imagination_trials: List[ImaginationTrial]
    ) -> InflationResult:
        """Get final rating and calculate inflation."""
        initial = self._memories.get(event.id)
        if not initial:
            initial = self._model.create_initial_memory(event, ConfidenceLevel.UNCERTAIN)

        # Apply imagination effects
        final = self._model.apply_imagination(event, initial, imagination_trials)

        # Calculate inflation
        return self._model.calculate_inflation(initial, final, imagination_trials)

    def run_experiment(
        self,
        n_imagined: int = 10,
        n_control: int = 10,
        repetitions: int = 3
    ) -> Dict[str, Any]:
        """Run full imagination inflation experiment."""
        # Create events
        imagined_events = [
            self.create_event(f"imagined_event_{i}", EventType.IMAGINED, 0.7)
            for i in range(n_imagined)
        ]

        control_events = [
            self.create_event(f"control_event_{i}", EventType.IMAGINED, 0.7)
            for i in range(n_control)
        ]

        # Initial ratings (all low confidence for never-happened events)
        for event in imagined_events + control_events:
            self.initial_rating(event, ConfidenceLevel.PROBABLY_NO)

        # Imagination phase (only for imagined condition)
        imagined_results = []
        for event in imagined_events:
            trials = self.imagination_phase(event, repetitions)
            result = self.final_rating(event, trials)
            imagined_results.append(result)

        # Control: no imagination
        control_results = []
        for event in control_events:
            # No imagination, just re-rate
            result = self.final_rating(event, [])
            control_results.append(result)

        # Calculate effects
        imagined_inflation = sum(r.confidence_change for r in imagined_results) / len(imagined_results) if imagined_results else 0
        control_inflation = sum(r.confidence_change for r in control_results) / len(control_results) if control_results else 0

        source_misattribution = sum(1 for r in imagined_results if r.source_misattribution) / len(imagined_results) if imagined_results else 0

        # False memory rate (initially "probably no" becoming "probably yes" or higher)
        false_memory_rate = sum(
            1 for r in imagined_results
            if r.final_confidence.value >= ConfidenceLevel.PROBABLY_YES.value
        ) / len(imagined_results) if imagined_results else 0

        return {
            'imagined_condition': {
                'mean_inflation': imagined_inflation,
                'source_misattribution': source_misattribution,
                'false_memory_rate': false_memory_rate
            },
            'control_condition': {
                'mean_inflation': control_inflation
            },
            'imagination_inflation_effect': imagined_inflation - control_inflation,
            'n_imagined': n_imagined,
            'n_control': n_control,
            'repetitions': repetitions
        }


# ============================================================================
# IMAGINATION INFLATION ENGINE
# ============================================================================

class ImaginationInflationEngine:
    """
    Complete imagination inflation engine.

    "Ba'el's imagination-to-memory converter." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = ImaginationInflationParadigm()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Event creation

    def create_plausible_event(
        self,
        description: str
    ) -> LifeEvent:
        """Create a plausible but imagined event."""
        return self._paradigm.create_event(description, EventType.IMAGINED, 0.8)

    def create_implausible_event(
        self,
        description: str
    ) -> LifeEvent:
        """Create an implausible imagined event."""
        return self._paradigm.create_event(description, EventType.IMAGINED, 0.3)

    # Rating

    def rate_initial(
        self,
        event: LifeEvent,
        confidence: ConfidenceLevel
    ) -> EventMemory:
        """Rate initial confidence."""
        return self._paradigm.initial_rating(event, confidence)

    # Imagination

    def imagine(
        self,
        event: LifeEvent,
        repetitions: int = 3
    ) -> List[ImaginationTrial]:
        """Imagine event occurring."""
        return self._paradigm.imagination_phase(event, repetitions)

    # Final rating

    def rate_final(
        self,
        event: LifeEvent,
        trials: List[ImaginationTrial]
    ) -> InflationResult:
        """Rate final confidence."""
        return self._paradigm.final_rating(event, trials)

    # Experiments

    def run_inflation_experiment(
        self,
        n_per_condition: int = 15,
        repetitions: int = 3
    ) -> Dict[str, Any]:
        """Run imagination inflation experiment."""
        result = self._paradigm.run_experiment(n_per_condition, n_per_condition, repetitions)
        self._experiment_results.append(result)
        return result

    def run_plausibility_comparison(
        self,
        n_per_condition: int = 10,
        repetitions: int = 3
    ) -> Dict[str, Any]:
        """Compare plausible vs implausible events."""
        # Plausible events
        plausible = [
            self.create_plausible_event(f"plausible_{i}")
            for i in range(n_per_condition)
        ]

        # Implausible events
        implausible = [
            self.create_implausible_event(f"implausible_{i}")
            for i in range(n_per_condition)
        ]

        # Rate and imagine
        plausible_results = []
        for event in plausible:
            self.rate_initial(event, ConfidenceLevel.PROBABLY_NO)
            trials = self.imagine(event, repetitions)
            result = self.rate_final(event, trials)
            plausible_results.append(result)

        implausible_results = []
        for event in implausible:
            self.rate_initial(event, ConfidenceLevel.PROBABLY_NO)
            trials = self.imagine(event, repetitions)
            result = self.rate_final(event, trials)
            implausible_results.append(result)

        plausible_inflation = sum(r.confidence_change for r in plausible_results) / len(plausible_results)
        implausible_inflation = sum(r.confidence_change for r in implausible_results) / len(implausible_results)

        return {
            'plausible_inflation': plausible_inflation,
            'implausible_inflation': implausible_inflation,
            'plausibility_effect': plausible_inflation - implausible_inflation
        }

    # Analysis

    def get_metrics(self) -> ImaginationInflationMetrics:
        """Get imagination inflation metrics."""
        if not self._experiment_results:
            self.run_inflation_experiment(10, 3)

        last = self._experiment_results[-1]

        return ImaginationInflationMetrics(
            mean_inflation=last['imagined_condition']['mean_inflation'],
            source_misattribution_rate=last['imagined_condition']['source_misattribution'],
            imagination_vividness=0.7,  # Placeholder
            false_memory_rate=last['imagined_condition']['false_memory_rate']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'events': len(self._paradigm._events),
            'experiments': len(self._experiment_results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_imagination_inflation_engine() -> ImaginationInflationEngine:
    """Create imagination inflation engine."""
    return ImaginationInflationEngine()


def demonstrate_imagination_inflation() -> Dict[str, Any]:
    """Demonstrate imagination inflation."""
    engine = create_imagination_inflation_engine()

    # Basic experiment
    basic = engine.run_inflation_experiment(15, 3)

    # Plausibility comparison
    plausibility = engine.run_plausibility_comparison(10, 3)

    return {
        'imagination_inflation': {
            'imagined_condition': f"+{basic['imagined_condition']['mean_inflation']:.1f} levels",
            'control_condition': f"+{basic['control_condition']['mean_inflation']:.1f} levels",
            'effect': f"+{basic['imagination_inflation_effect']:.1f} levels"
        },
        'false_memories': {
            'rate': f"{basic['imagined_condition']['false_memory_rate']:.0%}",
            'source_confusion': f"{basic['imagined_condition']['source_misattribution']:.0%}"
        },
        'plausibility': {
            'plausible': f"+{plausibility['plausible_inflation']:.1f} levels",
            'implausible': f"+{plausibility['implausible_inflation']:.1f} levels"
        },
        'interpretation': (
            f"Imagination inflation: {basic['imagination_inflation_effect']:.1f} confidence levels. "
            f"Imagining events increases false beliefs they occurred."
        )
    }


def get_imagination_inflation_facts() -> Dict[str, str]:
    """Get facts about imagination inflation."""
    return {
        'garry_1996': 'Original demonstration of imagination inflation',
        'source_monitoring': 'Confusion between imagined and perceived sources',
        'vividness': 'More vivid imagination leads to greater inflation',
        'repetition': 'Repeated imagination increases the effect',
        'plausibility': 'More plausible events show greater inflation',
        'therapeutic_concern': 'Relevant to recovered memory therapy',
        'childhood_events': 'Effect stronger for distant childhood memories',
        'imagery_ability': 'High imagers may be more susceptible'
    }
