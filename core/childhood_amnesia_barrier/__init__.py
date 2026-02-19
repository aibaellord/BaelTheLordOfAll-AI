"""
BAEL Childhood Amnesia Barrier Engine
=======================================

Adults cannot recall events before age 3-4.
Freud's original concept, modern cognitive view.

"Ba'el's earliest memories are beyond reach." — Ba'el
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

logger = logging.getLogger("BAEL.ChildhoodAmnesiaBarrier")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class AgeRange(Enum):
    """Age range of memory."""
    PREVERBAL = auto()      # 0-2
    EARLY_VERBAL = auto()   # 2-4
    CHILDHOOD = auto()      # 4-7
    SCHOOL_AGE = auto()     # 7-12
    ADOLESCENCE = auto()    # 12-18
    ADULTHOOD = auto()      # 18+


class MemoryType(Enum):
    """Type of early memory."""
    EPISODIC = auto()
    SEMANTIC = auto()
    PROCEDURAL = auto()
    IMPLICIT = auto()


class AmnesiaTheory(Enum):
    """Theory of childhood amnesia."""
    FREUDIAN = auto()        # Repression
    COGNITIVE = auto()       # Brain development
    LANGUAGE = auto()        # Language acquisition
    SELF_CONCEPT = auto()    # Self-awareness
    SOCIAL = auto()          # Social construction


class CueType(Enum):
    """Type of memory cue."""
    VERBAL = auto()
    PHOTO = auto()
    OBJECT = auto()
    LOCATION = auto()


@dataclass
class EarlyMemory:
    """
    An early childhood memory.
    """
    id: str
    age_at_event: float
    description: str
    memory_type: MemoryType
    verified: bool


@dataclass
class RecallAttempt:
    """
    An attempt to recall early memory.
    """
    earliest_age_reported: float
    n_memories_before_5: int
    cue_type: CueType
    confidence: float


@dataclass
class AmnesiaMetrics:
    """
    Childhood amnesia metrics.
    """
    amnesia_offset_age: float
    memories_before_3: int
    memories_3_to_5: int
    first_memory_age: float


# ============================================================================
# CHILDHOOD AMNESIA MODEL
# ============================================================================

class ChildhoodAmnesiaModel:
    """
    Model of childhood amnesia.

    "Ba'el's early memory model." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Amnesia offset (average age of first memory)
        self._amnesia_offset = 3.5  # Years
        self._offset_variance = 0.8

        # Age-memory density function
        self._density_slope = 0.35  # Memories/year increase
        self._critical_age = 3.0    # Sharp increase after

        # Memory accessibility by age
        self._accessibility = {
            AgeRange.PREVERBAL: 0.02,
            AgeRange.EARLY_VERBAL: 0.15,
            AgeRange.CHILDHOOD: 0.55,
            AgeRange.SCHOOL_AGE: 0.75,
            AgeRange.ADOLESCENCE: 0.85,
            AgeRange.ADULTHOOD: 0.80
        }

        # Memory type effects
        self._type_effects = {
            MemoryType.EPISODIC: 0.0,
            MemoryType.SEMANTIC: 0.15,     # Earlier access
            MemoryType.PROCEDURAL: 0.25,   # Earliest
            MemoryType.IMPLICIT: 0.30
        }

        # Cultural effects
        self._cultural_offset = {
            'western': 3.5,
            'asian': 4.0,        # Later offset
            'maori': 2.5         # Earlier offset
        }

        # Gender effects
        self._gender_offset = {
            'female': -0.3,      # Earlier memories
            'male': 0.0
        }

        # Language development effects
        self._language_weight = 0.25

        # Self-concept effects
        self._self_concept_weight = 0.20

        self._lock = threading.RLock()

    def calculate_recall_probability(
        self,
        age_at_event: float,
        memory_type: MemoryType = MemoryType.EPISODIC,
        cue_type: CueType = CueType.VERBAL
    ) -> float:
        """Calculate probability of recalling memory from given age."""
        # Below amnesia offset
        if age_at_event < self._amnesia_offset:
            # Very steep decline
            ratio = age_at_event / self._amnesia_offset
            base = ratio ** 3 * 0.15
        else:
            # Normal forgetting
            years_above = age_at_event - self._amnesia_offset
            base = 0.15 + min(years_above * 0.1, 0.6)

        # Memory type
        base += self._type_effects[memory_type]

        # Cue effects
        if cue_type == CueType.PHOTO:
            base += 0.10
        elif cue_type == CueType.OBJECT:
            base += 0.08

        # Add noise
        base += random.uniform(-0.08, 0.08)

        return max(0.01, min(0.80, base))

    def calculate_first_memory_age(
        self,
        culture: str = 'western',
        gender: str = 'male'
    ) -> float:
        """Calculate expected age of first memory."""
        base = self._cultural_offset.get(culture, 3.5)

        base += self._gender_offset.get(gender, 0.0)

        # Add individual variation
        base += random.gauss(0, self._offset_variance)

        return max(0.5, base)

    def calculate_memory_density(
        self,
        age: float
    ) -> float:
        """Calculate memory density (memories/year) at given age."""
        if age < self._critical_age:
            return 0.1 * (age / self._critical_age) ** 2
        else:
            years_above = age - self._critical_age
            return 0.1 + years_above * self._density_slope

    def get_mechanisms(
        self
    ) -> Dict[str, str]:
        """Get proposed mechanisms."""
        return {
            'neural': 'Hippocampus development',
            'language': 'Language needed for encoding',
            'self_concept': 'Need self-awareness for autobiographical',
            'social': 'Social construction of memories',
            'schema': 'Lack of schemas for organization'
        }

    def get_theory_comparison(
        self
    ) -> Dict[str, Dict[str, str]]:
        """Compare theories of childhood amnesia."""
        return {
            AmnesiaTheory.FREUDIAN.name: {
                'mechanism': 'Repression of early experiences',
                'status': 'Largely abandoned'
            },
            AmnesiaTheory.COGNITIVE.name: {
                'mechanism': 'Brain structures immature',
                'status': 'Well-supported'
            },
            AmnesiaTheory.LANGUAGE.name: {
                'mechanism': 'Verbal encoding required',
                'status': 'Partially supported'
            },
            AmnesiaTheory.SELF_CONCEPT.name: {
                'mechanism': 'Self-awareness needed',
                'status': 'Supported'
            },
            AmnesiaTheory.SOCIAL.name: {
                'mechanism': 'Parents shape memory',
                'status': 'Supported'
            }
        }

    def get_development_milestones(
        self
    ) -> Dict[float, str]:
        """Get cognitive milestones."""
        return {
            0.5: 'Basic memory formation',
            1.5: 'Deferred imitation',
            2.0: 'Mirror self-recognition',
            2.5: 'Simple past tense',
            3.0: 'Narrative ability',
            3.5: 'Autobiographical memory begins',
            4.0: 'Source monitoring develops',
            5.0: 'Theory of mind'
        }


# ============================================================================
# CHILDHOOD AMNESIA SYSTEM
# ============================================================================

class ChildhoodAmnesiaSystem:
    """
    Childhood amnesia simulation system.

    "Ba'el's early memory system." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = ChildhoodAmnesiaModel()

        self._memories: Dict[str, EarlyMemory] = {}
        self._recall_attempts: List[RecallAttempt] = []

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"mem_{self._counter}"

    def create_memory(
        self,
        age_at_event: float,
        description: str,
        memory_type: MemoryType = MemoryType.EPISODIC,
        verified: bool = False
    ) -> EarlyMemory:
        """Create early memory."""
        memory = EarlyMemory(
            id=self._generate_id(),
            age_at_event=age_at_event,
            description=description,
            memory_type=memory_type,
            verified=verified
        )

        self._memories[memory.id] = memory

        return memory

    def generate_lifespan_memories(
        self,
        current_age: int = 30
    ) -> List[EarlyMemory]:
        """Generate simulated memories across lifespan."""
        memories = []

        for age in range(1, min(current_age, 18) + 1):
            density = self._model.calculate_memory_density(age)
            n_mems = max(1, int(density * 5))

            for i in range(n_mems):
                mem = self.create_memory(
                    age + random.uniform(0, 1),
                    f"Memory from age {age}",
                    random.choice(list(MemoryType))
                )
                memories.append(mem)

        return memories

    def recall_earliest(
        self,
        cue_type: CueType = CueType.VERBAL
    ) -> RecallAttempt:
        """Attempt to recall earliest memories."""
        # Find successfully recalled
        recalled = []

        for mem in self._memories.values():
            prob = self._model.calculate_recall_probability(
                mem.age_at_event, mem.memory_type, cue_type
            )
            if random.random() < prob:
                recalled.append(mem)

        # Find earliest and count before 5
        if recalled:
            earliest = min(m.age_at_event for m in recalled)
            before_5 = sum(1 for m in recalled if m.age_at_event < 5)
        else:
            earliest = self._model.calculate_first_memory_age()
            before_5 = 0

        attempt = RecallAttempt(
            earliest_age_reported=earliest,
            n_memories_before_5=before_5,
            cue_type=cue_type,
            confidence=random.uniform(0.4, 0.9)
        )

        self._recall_attempts.append(attempt)

        return attempt


# ============================================================================
# CHILDHOOD AMNESIA PARADIGM
# ============================================================================

class ChildhoodAmnesiaParadigm:
    """
    Childhood amnesia paradigm.

    "Ba'el's early memory study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_earliest_memory_study(
        self,
        n_participants: int = 50
    ) -> Dict[str, Any]:
        """Run earliest memory study."""
        earliest_ages = []
        memories_before_5 = []

        for _ in range(n_participants):
            system = ChildhoodAmnesiaSystem()
            system.generate_lifespan_memories(30)
            attempt = system.recall_earliest()

            earliest_ages.append(attempt.earliest_age_reported)
            memories_before_5.append(attempt.n_memories_before_5)

        mean_earliest = sum(earliest_ages) / len(earliest_ages)
        mean_before_5 = sum(memories_before_5) / len(memories_before_5)

        return {
            'mean_first_memory_age': mean_earliest,
            'std_first_memory': statistics_std(earliest_ages),
            'mean_memories_before_5': mean_before_5,
            'interpretation': f'Childhood amnesia offset: {mean_earliest:.1f} years'
        }

    def run_age_density_study(
        self
    ) -> Dict[str, Any]:
        """Study memory density by age."""
        model = ChildhoodAmnesiaModel()

        ages = [1, 2, 3, 4, 5, 6, 7, 8, 10, 12]

        results = {}

        for age in ages:
            density = model.calculate_memory_density(age)
            prob = model.calculate_recall_probability(age)

            results[f'age_{age}'] = {
                'density': density,
                'recall_prob': prob
            }

        return {
            'by_age': results,
            'interpretation': 'Sharp increase after age 3-4'
        }

    def run_culture_study(
        self
    ) -> Dict[str, Any]:
        """Study cultural differences."""
        model = ChildhoodAmnesiaModel()

        cultures = ['western', 'asian', 'maori']

        results = {}

        for culture in cultures:
            first_mem = model.calculate_first_memory_age(culture)
            results[culture] = {'first_memory_age': first_mem}

        return {
            'by_culture': results,
            'interpretation': 'Cultural variation in amnesia offset'
        }

    def run_gender_study(
        self
    ) -> Dict[str, Any]:
        """Study gender differences."""
        model = ChildhoodAmnesiaModel()

        genders = ['male', 'female']

        results = {}

        for gender in genders:
            first_mem = model.calculate_first_memory_age('western', gender)
            results[gender] = {'first_memory_age': first_mem}

        return {
            'by_gender': results,
            'interpretation': 'Females report earlier memories'
        }

    def run_memory_type_study(
        self
    ) -> Dict[str, Any]:
        """Study memory type effects."""
        model = ChildhoodAmnesiaModel()

        results = {}

        for mem_type in MemoryType:
            prob_2 = model.calculate_recall_probability(2, mem_type)
            prob_4 = model.calculate_recall_probability(4, mem_type)

            results[mem_type.name] = {
                'recall_at_2': prob_2,
                'recall_at_4': prob_4
            }

        return {
            'by_type': results,
            'interpretation': 'Procedural/implicit preserved earlier'
        }

    def run_mechanism_study(
        self
    ) -> Dict[str, Any]:
        """Study underlying mechanisms."""
        model = ChildhoodAmnesiaModel()

        mechanisms = model.get_mechanisms()
        theories = model.get_theory_comparison()
        milestones = model.get_development_milestones()

        return {
            'mechanisms': mechanisms,
            'theories': theories,
            'milestones': milestones,
            'interpretation': 'Multiple factors: neural, language, self-concept'
        }


def statistics_std(values: List[float]) -> float:
    """Calculate standard deviation."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)


# ============================================================================
# CHILDHOOD AMNESIA ENGINE
# ============================================================================

class ChildhoodAmnesiaEngine:
    """
    Complete childhood amnesia engine.

    "Ba'el's early memory barrier engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = ChildhoodAmnesiaParadigm()
        self._system = ChildhoodAmnesiaSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Memory operations

    def create_memory(
        self,
        age_at_event: float,
        description: str
    ) -> EarlyMemory:
        """Create memory."""
        return self._system.create_memory(age_at_event, description)

    def generate_lifespan(
        self,
        current_age: int = 30
    ) -> List[EarlyMemory]:
        """Generate lifespan memories."""
        return self._system.generate_lifespan_memories(current_age)

    def recall_earliest(
        self
    ) -> RecallAttempt:
        """Recall earliest."""
        return self._system.recall_earliest()

    # Experiments

    def run_earliest_study(
        self
    ) -> Dict[str, Any]:
        """Run earliest memory study."""
        result = self._paradigm.run_earliest_memory_study()
        self._experiment_results.append(result)
        return result

    def study_age_density(
        self
    ) -> Dict[str, Any]:
        """Study age density."""
        return self._paradigm.run_age_density_study()

    def study_culture(
        self
    ) -> Dict[str, Any]:
        """Study culture."""
        return self._paradigm.run_culture_study()

    def study_gender(
        self
    ) -> Dict[str, Any]:
        """Study gender."""
        return self._paradigm.run_gender_study()

    def study_memory_types(
        self
    ) -> Dict[str, Any]:
        """Study memory types."""
        return self._paradigm.run_memory_type_study()

    def study_mechanisms(
        self
    ) -> Dict[str, Any]:
        """Study mechanisms."""
        return self._paradigm.run_mechanism_study()

    # Analysis

    def get_metrics(self) -> AmnesiaMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_earliest_study()

        last = self._experiment_results[-1]

        return AmnesiaMetrics(
            amnesia_offset_age=last['mean_first_memory_age'],
            memories_before_3=0,
            memories_3_to_5=int(last['mean_memories_before_5']),
            first_memory_age=last['mean_first_memory_age']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'memories': len(self._system._memories),
            'recall_attempts': len(self._system._recall_attempts)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_childhood_amnesia_engine() -> ChildhoodAmnesiaEngine:
    """Create childhood amnesia engine."""
    return ChildhoodAmnesiaEngine()


def demonstrate_childhood_amnesia() -> Dict[str, Any]:
    """Demonstrate childhood amnesia."""
    engine = create_childhood_amnesia_engine()

    # Age density
    density = engine.study_age_density()

    # Culture
    culture = engine.study_culture()

    # Memory types
    types = engine.study_memory_types()

    # Mechanisms
    mechanisms = engine.study_mechanisms()

    return {
        'by_age': {
            k: f"recall={v['recall_prob']:.0%}"
            for k, v in list(density['by_age'].items())[:5]
        },
        'by_culture': {
            k: f"first={v['first_memory_age']:.1f}"
            for k, v in culture['by_culture'].items()
        },
        'by_type': {
            k: f"at_2={v['recall_at_2']:.0%}"
            for k, v in types['by_type'].items()
        },
        'mechanisms': list(mechanisms['mechanisms'].keys()),
        'interpretation': (
            "Childhood amnesia barrier at ~3.5 years. "
            "Sharp decline before age 3-4. "
            "Neural, language, and self-concept development."
        )
    }


def get_childhood_amnesia_facts() -> Dict[str, str]:
    """Get facts about childhood amnesia."""
    return {
        'freud_1905': 'First description (repression theory)',
        'offset': 'Average first memory at 3.5 years',
        'cultural': 'Asian cultures later, Maori earlier',
        'gender': 'Females report earlier memories',
        'neural': 'Hippocampus development key',
        'language': 'Verbal encoding important',
        'self': 'Self-awareness needed',
        'implicit': 'Implicit memory preserved earlier'
    }
