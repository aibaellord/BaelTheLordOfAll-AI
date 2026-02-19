"""
BAEL Mental Time Travel Engine
================================

Re-experiencing past and pre-experiencing future.
Tulving's autonoetic consciousness.

"Ba'el travels the timeline of memory." — Ba'el
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

logger = logging.getLogger("BAEL.MentalTimeTravel")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class TemporalDirection(Enum):
    """Direction of mental time travel."""
    PAST = auto()      # Episodic memory
    FUTURE = auto()    # Episodic future thinking


class TemporalDistance(Enum):
    """Distance in time."""
    RECENT = auto()      # Days to weeks
    MODERATE = auto()    # Months
    DISTANT = auto()     # Years
    VERY_DISTANT = auto()  # Decades


class Phenomenology(Enum):
    """Phenomenological qualities."""
    VIVID = auto()
    MODERATE = auto()
    VAGUE = auto()
    SCHEMATIC = auto()


class EventType(Enum):
    """Type of mental event."""
    PERSONAL = auto()
    SEMANTIC = auto()
    IMAGINED = auto()


@dataclass
class MentalEvent:
    """
    A mental time travel event.
    """
    id: str
    content: str
    direction: TemporalDirection
    distance: TemporalDistance
    event_type: EventType
    emotional_intensity: float
    sensory_detail: float
    self_involvement: float


@dataclass
class TimeTravelExperience:
    """
    Experience of mental time travel.
    """
    event_id: str
    vividness: float
    phenomenology: Phenomenology
    autonoetic_consciousness: float  # Sense of self in time
    temporal_orientation: float      # Accuracy of time placement
    emotional_re_experiencing: float


@dataclass
class MentalTimeTravelMetrics:
    """
    Mental time travel metrics.
    """
    past_vividness: float
    future_vividness: float
    temporal_asymmetry: float
    autonoetic_level: float


# ============================================================================
# CONSTRUCTIVE EPISODIC SIMULATION MODEL
# ============================================================================

class ConstructiveSimulationModel:
    """
    Model of constructive episodic simulation.

    "Ba'el's temporal construction." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Vividness parameters
        self._base_vividness = 0.6
        self._distance_decay = 0.1
        self._emotional_boost = 0.2
        self._detail_weight = 0.3

        # Phenomenology thresholds
        self._vivid_threshold = 0.7
        self._moderate_threshold = 0.4
        self._vague_threshold = 0.2

        # Temporal asymmetry (past vs future)
        self._past_advantage = 0.1  # Past slightly more vivid

        # Autonoetic parameters
        self._base_autonoetic = 0.5
        self._self_involvement_weight = 0.4

        self._lock = threading.RLock()

    def calculate_distance_factor(
        self,
        distance: TemporalDistance
    ) -> float:
        """Calculate temporal distance effect."""
        distance_values = {
            TemporalDistance.RECENT: 0.0,
            TemporalDistance.MODERATE: 1.0,
            TemporalDistance.DISTANT: 2.0,
            TemporalDistance.VERY_DISTANT: 3.0
        }

        return distance_values.get(distance, 1.0) * self._distance_decay

    def calculate_vividness(
        self,
        event: MentalEvent
    ) -> float:
        """Calculate vividness of mental time travel."""
        vividness = self._base_vividness

        # Distance decay
        vividness -= self.calculate_distance_factor(event.distance)

        # Emotional boost
        vividness += event.emotional_intensity * self._emotional_boost

        # Sensory detail
        vividness += event.sensory_detail * self._detail_weight

        # Temporal direction asymmetry
        if event.direction == TemporalDirection.PAST:
            vividness += self._past_advantage

        return max(0.1, min(1.0, vividness))

    def get_phenomenology(
        self,
        vividness: float
    ) -> Phenomenology:
        """Determine phenomenological quality."""
        if vividness >= self._vivid_threshold:
            return Phenomenology.VIVID
        elif vividness >= self._moderate_threshold:
            return Phenomenology.MODERATE
        elif vividness >= self._vague_threshold:
            return Phenomenology.VAGUE
        else:
            return Phenomenology.SCHEMATIC

    def calculate_autonoetic(
        self,
        event: MentalEvent
    ) -> float:
        """Calculate autonoetic consciousness level."""
        autonoetic = self._base_autonoetic

        # Self-involvement increases autonoetic
        autonoetic += event.self_involvement * self._self_involvement_weight

        # Personal events more autonoetic
        if event.event_type == EventType.PERSONAL:
            autonoetic += 0.15
        elif event.event_type == EventType.SEMANTIC:
            autonoetic -= 0.1

        return max(0.1, min(1.0, autonoetic))

    def simulate_experience(
        self,
        event: MentalEvent
    ) -> TimeTravelExperience:
        """Simulate mental time travel experience."""
        vividness = self.calculate_vividness(event)
        phenomenology = self.get_phenomenology(vividness)
        autonoetic = self.calculate_autonoetic(event)

        # Temporal orientation (how accurately placed in time)
        temporal_orientation = 0.7 - self.calculate_distance_factor(event.distance)

        # Emotional re-experiencing
        emotional_re = event.emotional_intensity * vividness

        return TimeTravelExperience(
            event_id=event.id,
            vividness=vividness,
            phenomenology=phenomenology,
            autonoetic_consciousness=autonoetic,
            temporal_orientation=max(0.2, temporal_orientation),
            emotional_re_experiencing=emotional_re
        )


# ============================================================================
# MENTAL TIME TRAVEL SYSTEM
# ============================================================================

class MentalTimeTravelSystem:
    """
    Mental time travel simulation system.

    "Ba'el's temporal consciousness." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = ConstructiveSimulationModel()

        self._events: Dict[str, MentalEvent] = {}
        self._experiences: List[TimeTravelExperience] = []

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"event_{self._counter}"

    def create_event(
        self,
        content: str,
        direction: TemporalDirection,
        distance: TemporalDistance = TemporalDistance.MODERATE,
        event_type: EventType = EventType.PERSONAL
    ) -> MentalEvent:
        """Create a mental event."""
        event = MentalEvent(
            id=self._generate_id(),
            content=content,
            direction=direction,
            distance=distance,
            event_type=event_type,
            emotional_intensity=random.uniform(0.3, 0.8),
            sensory_detail=random.uniform(0.3, 0.7),
            self_involvement=random.uniform(0.5, 0.9)
        )

        self._events[event.id] = event

        return event

    def travel_to(
        self,
        event_id: str
    ) -> TimeTravelExperience:
        """Mentally travel to an event."""
        event = self._events.get(event_id)
        if not event:
            return None

        experience = self._model.simulate_experience(event)
        self._experiences.append(experience)

        return experience

    def remember_past(
        self,
        content: str,
        distance: TemporalDistance = TemporalDistance.MODERATE
    ) -> TimeTravelExperience:
        """Remember a past event."""
        event = self.create_event(
            content, TemporalDirection.PAST, distance, EventType.PERSONAL
        )
        return self.travel_to(event.id)

    def imagine_future(
        self,
        content: str,
        distance: TemporalDistance = TemporalDistance.MODERATE
    ) -> TimeTravelExperience:
        """Imagine a future event."""
        event = self.create_event(
            content, TemporalDirection.FUTURE, distance, EventType.IMAGINED
        )
        return self.travel_to(event.id)


# ============================================================================
# MENTAL TIME TRAVEL PARADIGM
# ============================================================================

class MentalTimeTravelParadigm:
    """
    Mental time travel experimental paradigm.

    "Ba'el's temporal study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_past_future_comparison(
        self,
        n_events: int = 20
    ) -> Dict[str, Any]:
        """Compare past and future mental time travel."""
        system = MentalTimeTravelSystem()

        past_experiences = []
        future_experiences = []

        for i in range(n_events // 2):
            # Past events
            exp = system.remember_past(f"past_event_{i}")
            past_experiences.append(exp)

            # Future events
            exp = system.imagine_future(f"future_event_{i}")
            future_experiences.append(exp)

        # Calculate averages
        past_vividness = sum(e.vividness for e in past_experiences) / len(past_experiences)
        future_vividness = sum(e.vividness for e in future_experiences) / len(future_experiences)

        past_autonoetic = sum(e.autonoetic_consciousness for e in past_experiences) / len(past_experiences)
        future_autonoetic = sum(e.autonoetic_consciousness for e in future_experiences) / len(future_experiences)

        return {
            'past_vividness': past_vividness,
            'future_vividness': future_vividness,
            'vividness_asymmetry': past_vividness - future_vividness,
            'past_autonoetic': past_autonoetic,
            'future_autonoetic': future_autonoetic
        }

    def run_temporal_distance_study(
        self
    ) -> Dict[str, Any]:
        """Study effect of temporal distance."""
        distances = [
            TemporalDistance.RECENT,
            TemporalDistance.MODERATE,
            TemporalDistance.DISTANT,
            TemporalDistance.VERY_DISTANT
        ]

        results = {}

        for direction in [TemporalDirection.PAST, TemporalDirection.FUTURE]:
            dir_results = {}

            for distance in distances:
                system = MentalTimeTravelSystem()

                experiences = []
                for i in range(10):
                    event = system.create_event(
                        f"event_{i}", direction, distance
                    )
                    exp = system.travel_to(event.id)
                    experiences.append(exp)

                avg_vividness = sum(e.vividness for e in experiences) / len(experiences)
                dir_results[distance.name] = avg_vividness

            results[direction.name] = dir_results

        return results

    def run_emotional_intensity_study(
        self
    ) -> Dict[str, Any]:
        """Study effect of emotional intensity."""
        intensities = [0.2, 0.5, 0.8]
        results = {}

        for intensity in intensities:
            system = MentalTimeTravelSystem()

            experiences = []
            for i in range(10):
                event = system.create_event(
                    f"event_{i}", TemporalDirection.PAST, TemporalDistance.MODERATE
                )
                event.emotional_intensity = intensity
                exp = system.travel_to(event.id)
                experiences.append(exp)

            avg_vividness = sum(e.vividness for e in experiences) / len(experiences)
            avg_reexp = sum(e.emotional_re_experiencing for e in experiences) / len(experiences)

            results[f"intensity_{intensity}"] = {
                'vividness': avg_vividness,
                'emotional_reexperiencing': avg_reexp
            }

        return results

    def run_phenomenology_analysis(
        self
    ) -> Dict[str, Any]:
        """Analyze phenomenological qualities."""
        system = MentalTimeTravelSystem()

        phenomenology_counts = defaultdict(int)

        for i in range(50):
            direction = random.choice(list(TemporalDirection))
            distance = random.choice(list(TemporalDistance))

            event = system.create_event(
                f"event_{i}", direction, distance
            )
            exp = system.travel_to(event.id)
            phenomenology_counts[exp.phenomenology.name] += 1

        total = sum(phenomenology_counts.values())

        distribution = {
            k: v / total
            for k, v in phenomenology_counts.items()
        }

        return {
            'phenomenology_distribution': distribution,
            'interpretation': 'Mental time travel varies in phenomenological quality'
        }

    def run_self_continuity_study(
        self
    ) -> Dict[str, Any]:
        """Study sense of self-continuity across time."""
        system = MentalTimeTravelSystem()

        # High self-involvement events
        high_self = []
        for i in range(10):
            event = system.create_event(
                f"personal_{i}", TemporalDirection.PAST
            )
            event.self_involvement = 0.9
            exp = system.travel_to(event.id)
            high_self.append(exp)

        # Low self-involvement events
        low_self = []
        for i in range(10):
            event = system.create_event(
                f"observed_{i}", TemporalDirection.PAST
            )
            event.self_involvement = 0.3
            exp = system.travel_to(event.id)
            low_self.append(exp)

        return {
            'high_self_autonoetic': sum(e.autonoetic_consciousness for e in high_self) / len(high_self),
            'low_self_autonoetic': sum(e.autonoetic_consciousness for e in low_self) / len(low_self),
            'interpretation': 'Self-involvement enhances autonoetic consciousness'
        }

    def run_adaptive_function_study(
        self
    ) -> Dict[str, Any]:
        """Study adaptive functions of mental time travel."""
        system = MentalTimeTravelSystem()

        # Planning (future)
        planning_events = []
        for i in range(10):
            exp = system.imagine_future(f"plan_{i}", TemporalDistance.MODERATE)
            planning_events.append(exp)

        # Decision making (compare past outcomes)
        decision_events = []
        for i in range(10):
            exp = system.remember_past(f"outcome_{i}", TemporalDistance.MODERATE)
            decision_events.append(exp)

        return {
            'planning_vividness': sum(e.vividness for e in planning_events) / len(planning_events),
            'decision_vividness': sum(e.vividness for e in decision_events) / len(decision_events),
            'functions': ['planning', 'decision_making', 'emotion_regulation', 'social_bonding']
        }


# ============================================================================
# MENTAL TIME TRAVEL ENGINE
# ============================================================================

class MentalTimeTravelEngine:
    """
    Complete mental time travel engine.

    "Ba'el's temporal consciousness engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = MentalTimeTravelParadigm()
        self._system = MentalTimeTravelSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Event management

    def create_event(
        self,
        content: str,
        direction: TemporalDirection,
        distance: TemporalDistance = TemporalDistance.MODERATE
    ) -> MentalEvent:
        """Create an event."""
        return self._system.create_event(content, direction, distance)

    def travel(
        self,
        event_id: str
    ) -> TimeTravelExperience:
        """Travel to an event."""
        return self._system.travel_to(event_id)

    def remember(
        self,
        content: str
    ) -> TimeTravelExperience:
        """Remember past."""
        return self._system.remember_past(content)

    def imagine(
        self,
        content: str
    ) -> TimeTravelExperience:
        """Imagine future."""
        return self._system.imagine_future(content)

    # Experiments

    def compare_past_future(
        self
    ) -> Dict[str, Any]:
        """Compare past and future."""
        result = self._paradigm.run_past_future_comparison()
        self._experiment_results.append(result)
        return result

    def study_temporal_distance(
        self
    ) -> Dict[str, Any]:
        """Study temporal distance effects."""
        return self._paradigm.run_temporal_distance_study()

    def study_emotion(
        self
    ) -> Dict[str, Any]:
        """Study emotion effects."""
        return self._paradigm.run_emotional_intensity_study()

    def analyze_phenomenology(
        self
    ) -> Dict[str, Any]:
        """Analyze phenomenology."""
        return self._paradigm.run_phenomenology_analysis()

    def study_self_continuity(
        self
    ) -> Dict[str, Any]:
        """Study self-continuity."""
        return self._paradigm.run_self_continuity_study()

    def study_adaptive_functions(
        self
    ) -> Dict[str, Any]:
        """Study adaptive functions."""
        return self._paradigm.run_adaptive_function_study()

    # Analysis

    def get_metrics(self) -> MentalTimeTravelMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.compare_past_future()

        last = self._experiment_results[-1]

        return MentalTimeTravelMetrics(
            past_vividness=last['past_vividness'],
            future_vividness=last['future_vividness'],
            temporal_asymmetry=last['vividness_asymmetry'],
            autonoetic_level=last['past_autonoetic']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'events': len(self._system._events),
            'experiences': len(self._system._experiences)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_mental_time_travel_engine() -> MentalTimeTravelEngine:
    """Create mental time travel engine."""
    return MentalTimeTravelEngine()


def demonstrate_mental_time_travel() -> Dict[str, Any]:
    """Demonstrate mental time travel."""
    engine = create_mental_time_travel_engine()

    # Compare past/future
    comparison = engine.compare_past_future()

    # Distance study
    distance = engine.study_temporal_distance()

    # Emotion study
    emotion = engine.study_emotion()

    # Phenomenology
    phenom = engine.analyze_phenomenology()

    # Self-continuity
    self_cont = engine.study_self_continuity()

    return {
        'past_vs_future': {
            'past_vividness': f"{comparison['past_vividness']:.0%}",
            'future_vividness': f"{comparison['future_vividness']:.0%}",
            'asymmetry': f"{comparison['vividness_asymmetry']:.0%}"
        },
        'temporal_distance': {
            direction: {k: f"{v:.0%}" for k, v in dists.items()}
            for direction, dists in distance.items()
        },
        'emotion_effect': {
            k: f"vividness: {v['vividness']:.0%}"
            for k, v in emotion.items()
        },
        'phenomenology': {
            k: f"{v:.0%}"
            for k, v in phenom['phenomenology_distribution'].items()
        },
        'interpretation': (
            f"Past vividness: {comparison['past_vividness']:.0%}, "
            f"Future: {comparison['future_vividness']:.0%}. "
            f"Mental time travel shows temporal asymmetry."
        )
    }


def get_mental_time_travel_facts() -> Dict[str, str]:
    """Get facts about mental time travel."""
    return {
        'tulving_2002': 'Autonoetic consciousness and chronesthesia',
        'schacter_addis_2007': 'Constructive episodic simulation hypothesis',
        'past_future_link': 'Same system supports memory and imagination',
        'hippocampus': 'Critical for both past and future thinking',
        'temporal_asymmetry': 'Past slightly more vivid than future',
        'adaptive': 'Serves planning, decision-making, social functions',
        'phenomenology': 'Varies from vivid to schematic'
    }
