"""
BAEL Déjà Vu Engine
=====================

Illusory familiarity without recollection.
Brown's déjà vu phenomenon.

"Ba'el has seen this before." — Ba'el
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

logger = logging.getLogger("BAEL.DejaVu")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class DejaVuType(Enum):
    """Type of déjà vu experience."""
    DEJA_VU = auto()        # Already seen
    DEJA_VECU = auto()      # Already lived
    DEJA_SENTI = auto()     # Already felt
    DEJA_VISITE = auto()    # Already visited
    JAMAIS_VU = auto()      # Never seen (opposite)


class TriggerType(Enum):
    """What triggered the experience."""
    VISUAL_SCENE = auto()
    CONVERSATION = auto()
    LOCATION = auto()
    EMOTIONAL_STATE = auto()
    RANDOM = auto()


class FamiliaritySource(Enum):
    """Source of familiarity signal."""
    TRUE_MEMORY = auto()
    PARTIAL_MATCH = auto()
    PROCESSING_FLUENCY = auto()
    SOURCE_CONFUSION = auto()
    CRYPTOMNESIA = auto()


@dataclass
class Experience:
    """
    An experience that could trigger déjà vu.
    """
    id: str
    content: str
    features: Dict[str, float]
    emotional_tone: float
    context: str


@dataclass
class MemoryTrace:
    """
    A memory trace that could be matched.
    """
    id: str
    content: str
    features: Dict[str, float]
    strength: float
    recollection_available: bool


@dataclass
class DejaVuEvent:
    """
    A déjà vu event.
    """
    experience_id: str
    deja_vu_type: DejaVuType
    familiarity_strength: float
    recollection_available: bool
    confidence: float
    duration_seconds: float
    trigger: TriggerType
    likely_source: FamiliaritySource


@dataclass
class DejaVuMetrics:
    """
    Déjà vu metrics.
    """
    occurrence_rate: float
    avg_familiarity: float
    avg_confidence: float
    recollection_available_rate: float
    trigger_distribution: Dict[str, float]


# ============================================================================
# FAMILIARITY-RECOLLECTION DISSOCIATION MODEL
# ============================================================================

class FamiliarityRecollectionModel:
    """
    Dual-process model of déjà vu.

    "Ba'el's familiarity without source." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Familiarity parameters
        self._familiarity_threshold = 0.3
        self._strong_familiarity_threshold = 0.6

        # Recollection parameters
        self._recollection_threshold = 0.5

        # Feature matching
        self._feature_match_weight = 0.4
        self._context_match_weight = 0.2
        self._emotional_match_weight = 0.3

        # Déjà vu occurrence factors
        self._dissociation_probability = 0.1  # Base rate
        self._fatigue_boost = 0.15
        self._stress_boost = 0.1

        self._lock = threading.RLock()

    def calculate_feature_similarity(
        self,
        features1: Dict[str, float],
        features2: Dict[str, float]
    ) -> float:
        """Calculate similarity between feature sets."""
        common_keys = set(features1.keys()) & set(features2.keys())
        if not common_keys:
            return 0.0

        distances = [
            abs(features1[k] - features2[k])
            for k in common_keys
        ]

        avg_distance = sum(distances) / len(distances)
        similarity = 1 - avg_distance

        return max(0, similarity)

    def calculate_familiarity(
        self,
        experience: Experience,
        memory: MemoryTrace
    ) -> float:
        """Calculate familiarity signal strength."""
        # Feature similarity
        feature_sim = self.calculate_feature_similarity(
            experience.features, memory.features
        )

        familiarity = feature_sim * self._feature_match_weight

        # Memory strength contribution
        familiarity += memory.strength * 0.3

        return min(1.0, familiarity)

    def calculate_recollection(
        self,
        memory: MemoryTrace,
        familiarity: float
    ) -> bool:
        """Calculate whether recollection is available."""
        if not memory.recollection_available:
            return False

        # Recollection requires stronger memory
        recoll_prob = memory.strength * 0.8

        return random.random() < recoll_prob

    def detect_deja_vu(
        self,
        experience: Experience,
        memory: MemoryTrace,
        fatigue_level: float = 0.3,
        stress_level: float = 0.2
    ) -> Optional[DejaVuEvent]:
        """Detect if déjà vu occurs."""
        familiarity = self.calculate_familiarity(experience, memory)
        recollection = self.calculate_recollection(memory, familiarity)

        # Déjà vu: high familiarity without recollection
        if familiarity >= self._familiarity_threshold and not recollection:
            # Calculate probability of experiencing déjà vu
            deja_vu_prob = self._dissociation_probability
            deja_vu_prob += fatigue_level * self._fatigue_boost
            deja_vu_prob += stress_level * self._stress_boost

            # Stronger familiarity = higher chance
            deja_vu_prob *= (1 + familiarity)

            if random.random() < deja_vu_prob:
                # Déjà vu occurs
                trigger = random.choice(list(TriggerType))

                # Determine likely source
                if memory.strength < 0.3:
                    source = FamiliaritySource.PROCESSING_FLUENCY
                elif not memory.recollection_available:
                    source = FamiliaritySource.SOURCE_CONFUSION
                else:
                    source = FamiliaritySource.PARTIAL_MATCH

                return DejaVuEvent(
                    experience_id=experience.id,
                    deja_vu_type=DejaVuType.DEJA_VU,
                    familiarity_strength=familiarity,
                    recollection_available=False,
                    confidence=familiarity * random.uniform(0.5, 1.0),
                    duration_seconds=random.uniform(1, 30),
                    trigger=trigger,
                    likely_source=source
                )

        return None


# ============================================================================
# DEJA VU SYSTEM
# ============================================================================

class DejaVuSystem:
    """
    Déjà vu simulation system.

    "Ba'el's familiarity illusion." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = FamiliarityRecollectionModel()

        self._memories: Dict[str, MemoryTrace] = {}
        self._experiences: Dict[str, Experience] = {}
        self._events: List[DejaVuEvent] = []

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"item_{self._counter}"

    def create_memory(
        self,
        content: str,
        strength: float = 0.5,
        recollection_available: bool = True
    ) -> MemoryTrace:
        """Create a memory trace."""
        features = {
            f"feature_{i}": random.random()
            for i in range(5)
        }

        memory = MemoryTrace(
            id=self._generate_id(),
            content=content,
            features=features,
            strength=strength,
            recollection_available=recollection_available
        )

        self._memories[memory.id] = memory

        return memory

    def create_experience(
        self,
        content: str,
        similar_to: Optional[MemoryTrace] = None
    ) -> Experience:
        """Create a new experience."""
        if similar_to:
            # Create features similar to the memory
            features = {
                k: v + random.uniform(-0.2, 0.2)
                for k, v in similar_to.features.items()
            }
        else:
            features = {
                f"feature_{i}": random.random()
                for i in range(5)
            }

        experience = Experience(
            id=self._generate_id(),
            content=content,
            features=features,
            emotional_tone=random.uniform(-1, 1),
            context="current_situation"
        )

        self._experiences[experience.id] = experience

        return experience

    def process_experience(
        self,
        experience_id: str,
        fatigue: float = 0.3,
        stress: float = 0.2
    ) -> Optional[DejaVuEvent]:
        """Process an experience for potential déjà vu."""
        experience = self._experiences.get(experience_id)
        if not experience:
            return None

        # Check against all memories
        for memory in self._memories.values():
            event = self._model.detect_deja_vu(
                experience, memory, fatigue, stress
            )
            if event:
                self._events.append(event)
                return event

        return None

    def simulate_day(
        self,
        n_experiences: int = 50,
        fatigue: float = 0.3,
        stress: float = 0.2
    ) -> List[DejaVuEvent]:
        """Simulate a day of experiences."""
        events = []

        for i in range(n_experiences):
            # Some experiences similar to memories
            if random.random() < 0.3 and self._memories:
                similar_to = random.choice(list(self._memories.values()))
                exp = self.create_experience(f"exp_{i}", similar_to)
            else:
                exp = self.create_experience(f"exp_{i}")

            event = self.process_experience(exp.id, fatigue, stress)
            if event:
                events.append(event)

        return events


# ============================================================================
# DEJA VU PARADIGM
# ============================================================================

class DejaVuParadigm:
    """
    Déjà vu experimental paradigm.

    "Ba'el's familiarity study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_frequency_study(
        self,
        n_participants: int = 100,
        days: int = 7
    ) -> Dict[str, Any]:
        """Study déjà vu frequency."""
        total_events = 0
        participants_with_deja_vu = 0

        for _ in range(n_participants):
            system = DejaVuSystem()

            # Create some background memories
            for i in range(20):
                system.create_memory(
                    f"memory_{i}",
                    strength=random.uniform(0.2, 0.8),
                    recollection_available=random.random() > 0.3
                )

            participant_events = 0
            for _ in range(days):
                events = system.simulate_day(50)
                participant_events += len(events)

            total_events += participant_events
            if participant_events > 0:
                participants_with_deja_vu += 1

        return {
            'total_events': total_events,
            'events_per_person': total_events / n_participants,
            'events_per_week': total_events / n_participants,
            'prevalence': participants_with_deja_vu / n_participants,
            'typical_frequency': '1-4 times per month for most people'
        }

    def run_trigger_analysis(
        self
    ) -> Dict[str, Any]:
        """Analyze what triggers déjà vu."""
        trigger_counts = defaultdict(int)
        source_counts = defaultdict(int)

        for _ in range(100):
            system = DejaVuSystem()

            for i in range(10):
                system.create_memory(f"mem_{i}", strength=random.uniform(0.3, 0.7))

            events = system.simulate_day(100)

            for event in events:
                trigger_counts[event.trigger.name] += 1
                source_counts[event.likely_source.name] += 1

        total = sum(trigger_counts.values())

        trigger_dist = {
            k: v / total if total > 0 else 0
            for k, v in trigger_counts.items()
        }

        source_dist = {
            k: v / total if total > 0 else 0
            for k, v in source_counts.items()
        }

        return {
            'trigger_distribution': trigger_dist,
            'source_distribution': source_dist
        }

    def run_fatigue_stress_study(
        self
    ) -> Dict[str, Any]:
        """Study effect of fatigue and stress."""
        conditions = {
            'low_fatigue_low_stress': (0.1, 0.1),
            'high_fatigue_low_stress': (0.7, 0.1),
            'low_fatigue_high_stress': (0.1, 0.7),
            'high_fatigue_high_stress': (0.7, 0.7)
        }

        results = {}

        for condition, (fatigue, stress) in conditions.items():
            total_events = 0

            for _ in range(50):
                system = DejaVuSystem()

                for i in range(10):
                    system.create_memory(f"mem_{i}")

                events = system.simulate_day(50, fatigue, stress)
                total_events += len(events)

            results[condition] = total_events / 50

        return results

    def run_age_simulation(
        self
    ) -> Dict[str, Any]:
        """Simulate age effects on déjà vu."""
        # Déjà vu peaks in young adulthood, decreases with age

        age_groups = {
            'teens': {'freq_modifier': 1.3, 'memory_strength': 0.6},
            'young_adult': {'freq_modifier': 1.5, 'memory_strength': 0.65},
            '30s': {'freq_modifier': 1.0, 'memory_strength': 0.6},
            '40s': {'freq_modifier': 0.8, 'memory_strength': 0.55},
            '50s': {'freq_modifier': 0.6, 'memory_strength': 0.5},
            '60+': {'freq_modifier': 0.4, 'memory_strength': 0.45}
        }

        results = {}

        for age_group, params in age_groups.items():
            total_events = 0

            for _ in range(30):
                system = DejaVuSystem()

                for i in range(10):
                    system.create_memory(
                        f"mem_{i}",
                        strength=params['memory_strength'],
                        recollection_available=random.random() > 0.2
                    )

                events = system.simulate_day(50)
                total_events += len(events) * params['freq_modifier']

            results[age_group] = total_events / 30

        return results

    def run_recognition_without_identification(
        self
    ) -> Dict[str, Any]:
        """Demonstrate recognition without identification."""
        system = DejaVuSystem()

        # Create weak memories without good recollection
        for i in range(20):
            system.create_memory(
                f"forgotten_context_{i}",
                strength=random.uniform(0.2, 0.5),
                recollection_available=False  # Can't recall context
            )

        events = system.simulate_day(100, fatigue=0.5, stress=0.3)

        return {
            'events_triggered': len(events),
            'avg_familiarity': sum(e.familiarity_strength for e in events) / len(events) if events else 0,
            'recollection_available': sum(1 for e in events if e.recollection_available) / len(events) if events else 0,
            'interpretation': 'Strong familiarity without source recall = déjà vu'
        }


# ============================================================================
# DEJA VU ENGINE
# ============================================================================

class DejaVuEngine:
    """
    Complete déjà vu engine.

    "Ba'el's familiarity illusion engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = DejaVuParadigm()
        self._system = DejaVuSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Memory/Experience management

    def create_memory(
        self,
        content: str,
        strength: float = 0.5
    ) -> MemoryTrace:
        """Create a memory."""
        return self._system.create_memory(content, strength)

    def create_experience(
        self,
        content: str,
        similar_to: Optional[MemoryTrace] = None
    ) -> Experience:
        """Create an experience."""
        return self._system.create_experience(content, similar_to)

    def process(
        self,
        experience_id: str
    ) -> Optional[DejaVuEvent]:
        """Process an experience."""
        return self._system.process_experience(experience_id)

    def simulate_day(
        self,
        n_experiences: int = 50
    ) -> List[DejaVuEvent]:
        """Simulate a day."""
        return self._system.simulate_day(n_experiences)

    # Experiments

    def study_frequency(
        self,
        n_participants: int = 100
    ) -> Dict[str, Any]:
        """Study frequency."""
        result = self._paradigm.run_frequency_study(n_participants)
        self._experiment_results.append(result)
        return result

    def analyze_triggers(
        self
    ) -> Dict[str, Any]:
        """Analyze triggers."""
        return self._paradigm.run_trigger_analysis()

    def study_fatigue_stress(
        self
    ) -> Dict[str, Any]:
        """Study fatigue/stress effects."""
        return self._paradigm.run_fatigue_stress_study()

    def study_age_effects(
        self
    ) -> Dict[str, Any]:
        """Study age effects."""
        return self._paradigm.run_age_simulation()

    def demonstrate_dissociation(
        self
    ) -> Dict[str, Any]:
        """Demonstrate familiarity-recollection dissociation."""
        return self._paradigm.run_recognition_without_identification()

    # Analysis

    def get_metrics(self) -> DejaVuMetrics:
        """Get déjà vu metrics."""
        if not self._experiment_results:
            self.study_frequency()

        triggers = self.analyze_triggers()

        return DejaVuMetrics(
            occurrence_rate=self._experiment_results[-1]['events_per_week'],
            avg_familiarity=0.6,  # Typical
            avg_confidence=0.5,
            recollection_available_rate=0.1,
            trigger_distribution=triggers['trigger_distribution']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'memories': len(self._system._memories),
            'experiences': len(self._system._experiences),
            'events': len(self._system._events)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_deja_vu_engine() -> DejaVuEngine:
    """Create déjà vu engine."""
    return DejaVuEngine()


def demonstrate_deja_vu() -> Dict[str, Any]:
    """Demonstrate déjà vu."""
    engine = create_deja_vu_engine()

    # Frequency study
    frequency = engine.study_frequency(50)

    # Trigger analysis
    triggers = engine.analyze_triggers()

    # Fatigue/stress
    fatigue_stress = engine.study_fatigue_stress()

    # Age effects
    age = engine.study_age_effects()

    # Dissociation demo
    dissociation = engine.demonstrate_dissociation()

    return {
        'frequency': {
            'prevalence': f"{frequency['prevalence']:.0%}",
            'events_per_week': f"{frequency['events_per_week']:.1f}"
        },
        'triggers': {
            k: f"{v:.0%}"
            for k, v in triggers['trigger_distribution'].items()
        },
        'fatigue_stress': {
            cond: f"{rate:.2f}/day"
            for cond, rate in fatigue_stress.items()
        },
        'age_effects': {
            age: f"{rate:.2f}/day"
            for age, rate in age.items()
        },
        'interpretation': (
            f"Déjà vu: familiarity signal without recollection. "
            f"Prevalence: {frequency['prevalence']:.0%}. "
            f"Peaks in young adulthood, increases with fatigue."
        )
    }


def get_deja_vu_facts() -> Dict[str, str]:
    """Get facts about déjà vu."""
    return {
        'prevalence': '60-70% of people experience déjà vu',
        'frequency': 'Typically 1-4 times per month',
        'age_peak': 'Most common in teens and young adults',
        'decreases_with_age': 'Frequency decreases after 25',
        'fatigue': 'More common when tired or stressed',
        'dual_process': 'Familiarity without recollection',
        'temporal_lobe': 'Associated with temporal lobe activity',
        'not_precognition': 'Not evidence of actual prior experience'
    }
