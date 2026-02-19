"""
BAEL Reminiscence Bump Engine
===============================

Enhanced autobiographical memory for adolescence/early adulthood.
Rubin's lifespan retrieval curve.

"Ba'el's youth echoes eternal." — Ba'el
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

logger = logging.getLogger("BAEL.ReminiscenceBump")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class LifePeriod(Enum):
    """Life periods for memories."""
    CHILDHOOD = auto()        # 0-10 years
    ADOLESCENCE = auto()      # 10-20 years
    YOUNG_ADULT = auto()      # 20-30 years
    MIDDLE_ADULT = auto()     # 30-50 years
    OLDER_ADULT = auto()      # 50+ years


class MemoryType(Enum):
    """Types of autobiographical memories."""
    PERSONAL_EVENT = auto()
    FIRST_EXPERIENCE = auto()
    PUBLIC_EVENT = auto()
    RELATIONSHIP = auto()
    ACHIEVEMENT = auto()


class CueType(Enum):
    """Types of memory cues."""
    WORD_CUE = auto()
    MUSIC_CUE = auto()
    PHOTO_CUE = auto()
    SMELL_CUE = auto()
    FREE_RECALL = auto()


@dataclass
class AutobiographicalMemory:
    """
    An autobiographical memory.
    """
    id: str
    description: str
    age_at_event: int
    life_period: LifePeriod
    memory_type: MemoryType
    emotional_intensity: float
    self_relevance: float
    novelty: float


@dataclass
class RetrievalResult:
    """
    Result of memory retrieval.
    """
    memory_id: str
    retrieved: bool
    age_at_event: int
    life_period: LifePeriod
    retrieval_time_ms: float
    vividness: float


@dataclass
class ReminiscenceBumpMetrics:
    """
    Reminiscence bump metrics.
    """
    bump_peak_age: int
    bump_magnitude: float
    childhood_amnesia_cutoff: int
    recency_effect: float


# ============================================================================
# LIFESPAN RETRIEVAL MODEL
# ============================================================================

class LifespanRetrievalModel:
    """
    Model of lifespan autobiographical memory retrieval.

    "Ba'el's life story arc." — Ba'el
    """

    def __init__(
        self,
        current_age: int = 50
    ):
        """Initialize model."""
        self._current_age = current_age

        # Bump parameters
        self._bump_peak = 20  # Peak around 15-25
        self._bump_width = 10
        self._bump_height = 0.4

        # Childhood amnesia
        self._amnesia_cutoff = 3
        self._amnesia_transition = 5

        # Recency parameters
        self._recency_window = 5  # years
        self._recency_boost = 0.3

        # Base retrieval
        self._base_retrieval = 0.3

        self._lock = threading.RLock()

    def get_retrieval_probability(
        self,
        age_at_event: int
    ) -> float:
        """Get probability of retrieving a memory from given age."""
        if age_at_event < 0 or age_at_event > self._current_age:
            return 0.0

        prob = self._base_retrieval

        # Childhood amnesia
        if age_at_event < self._amnesia_cutoff:
            prob *= 0.1
        elif age_at_event < self._amnesia_cutoff + self._amnesia_transition:
            transition = (age_at_event - self._amnesia_cutoff) / self._amnesia_transition
            prob *= 0.1 + transition * 0.9

        # Reminiscence bump
        bump_distance = abs(age_at_event - self._bump_peak)
        if bump_distance < self._bump_width:
            bump_factor = 1 - (bump_distance / self._bump_width)
            prob += self._bump_height * bump_factor

        # Recency effect
        years_ago = self._current_age - age_at_event
        if years_ago < self._recency_window:
            recency_factor = 1 - (years_ago / self._recency_window)
            prob += self._recency_boost * recency_factor

        return min(0.9, max(0.05, prob))

    def get_period_for_age(
        self,
        age: int
    ) -> LifePeriod:
        """Get life period for age."""
        if age < 10:
            return LifePeriod.CHILDHOOD
        elif age < 20:
            return LifePeriod.ADOLESCENCE
        elif age < 30:
            return LifePeriod.YOUNG_ADULT
        elif age < 50:
            return LifePeriod.MIDDLE_ADULT
        else:
            return LifePeriod.OLDER_ADULT

    def get_expected_distribution(
        self
    ) -> Dict[int, float]:
        """Get expected age distribution of memories."""
        distribution = {}
        for age in range(self._current_age + 1):
            distribution[age] = self.get_retrieval_probability(age)
        return distribution


# ============================================================================
# AUTOBIOGRAPHICAL MEMORY SYSTEM
# ============================================================================

class AutobiographicalMemorySystem:
    """
    Autobiographical memory system with reminiscence bump.

    "Ba'el's life narrative." — Ba'el
    """

    def __init__(
        self,
        current_age: int = 50
    ):
        """Initialize system."""
        self._model = LifespanRetrievalModel(current_age)
        self._current_age = current_age

        self._memories: Dict[str, AutobiographicalMemory] = {}
        self._retrievals: List[RetrievalResult] = []

        self._memory_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._memory_counter += 1
        return f"memory_{self._memory_counter}"

    def store_memory(
        self,
        description: str,
        age_at_event: int,
        memory_type: MemoryType = MemoryType.PERSONAL_EVENT,
        emotional_intensity: float = 0.5
    ) -> AutobiographicalMemory:
        """Store an autobiographical memory."""
        memory = AutobiographicalMemory(
            id=self._generate_id(),
            description=description,
            age_at_event=age_at_event,
            life_period=self._model.get_period_for_age(age_at_event),
            memory_type=memory_type,
            emotional_intensity=emotional_intensity,
            self_relevance=random.uniform(0.5, 1.0),
            novelty=0.8 if memory_type == MemoryType.FIRST_EXPERIENCE else 0.4
        )

        self._memories[memory.id] = memory

        return memory

    def retrieve_memory(
        self,
        memory_id: str
    ) -> RetrievalResult:
        """Attempt to retrieve a memory."""
        memory = self._memories.get(memory_id)
        if not memory:
            return None

        base_prob = self._model.get_retrieval_probability(memory.age_at_event)

        # Emotional boost
        emotional_boost = memory.emotional_intensity * 0.15

        # Novelty/first experience boost
        novelty_boost = memory.novelty * 0.1

        prob = base_prob + emotional_boost + novelty_boost
        prob = min(0.95, max(0.05, prob))

        retrieved = random.random() < prob

        result = RetrievalResult(
            memory_id=memory_id,
            retrieved=retrieved,
            age_at_event=memory.age_at_event,
            life_period=memory.life_period,
            retrieval_time_ms=500 + random.uniform(0, 2000),
            vividness=prob * random.uniform(0.7, 1.0)
        )

        self._retrievals.append(result)

        return result

    def cued_retrieval(
        self,
        cue: str,
        cue_type: CueType
    ) -> List[AutobiographicalMemory]:
        """Retrieve memories based on cue."""
        # Simulate cued retrieval - returns memories with probability based on model
        retrieved_memories = []

        for memory in self._memories.values():
            prob = self._model.get_retrieval_probability(memory.age_at_event)

            # Music cues especially effective for bump period
            if cue_type == CueType.MUSIC_CUE:
                if memory.life_period == LifePeriod.ADOLESCENCE:
                    prob *= 1.3

            if random.random() < prob:
                retrieved_memories.append(memory)

        return retrieved_memories

    def generate_lifespan_memories(
        self
    ) -> None:
        """Generate memories across lifespan."""
        for age in range(self._current_age):
            # More events in adolescence/young adulthood
            if 15 <= age <= 25:
                n_events = random.randint(3, 6)
            elif 10 <= age <= 30:
                n_events = random.randint(2, 4)
            else:
                n_events = random.randint(1, 3)

            for i in range(n_events):
                memory_type = random.choice(list(MemoryType))
                emotional = random.uniform(0.3, 0.9)

                self.store_memory(
                    f"event_at_age_{age}_{i}",
                    age,
                    memory_type,
                    emotional
                )


# ============================================================================
# REMINISCENCE BUMP PARADIGM
# ============================================================================

class ReminiscenceBumpParadigm:
    """
    Reminiscence bump experimental paradigm.

    "Ba'el's lifespan memory study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_lifespan_retrieval(
        self,
        current_age: int = 50
    ) -> Dict[str, Any]:
        """Run lifespan retrieval experiment."""
        system = AutobiographicalMemorySystem(current_age)
        system.generate_lifespan_memories()

        # Retrieve all memories
        age_counts = defaultdict(int)

        for memory in system._memories.values():
            result = system.retrieve_memory(memory.id)
            if result.retrieved:
                age_counts[memory.age_at_event] += 1

        # Normalize by age
        total = sum(age_counts.values())
        age_distribution = {
            age: count / total if total > 0 else 0
            for age, count in age_counts.items()
        }

        # Find bump
        bump_ages = [age for age in range(15, 26) if age in age_distribution]
        bump_proportion = sum(age_distribution.get(age, 0) for age in bump_ages)

        # Childhood amnesia
        childhood_ages = [age for age in range(0, 5) if age in age_distribution]
        childhood_proportion = sum(age_distribution.get(age, 0) for age in childhood_ages)

        # Recency
        recent_ages = [age for age in range(current_age - 5, current_age + 1)]
        recency_proportion = sum(age_distribution.get(age, 0) for age in recent_ages)

        return {
            'current_age': current_age,
            'bump_proportion': bump_proportion,
            'childhood_proportion': childhood_proportion,
            'recency_proportion': recency_proportion,
            'age_distribution': dict(sorted(age_distribution.items()))
        }

    def run_cue_word_experiment(
        self,
        current_age: int = 50
    ) -> Dict[str, Any]:
        """Run cue word experiment."""
        system = AutobiographicalMemorySystem(current_age)
        system.generate_lifespan_memories()

        cues = ["happy", "school", "friend", "home", "love"]

        period_counts = defaultdict(int)

        for cue in cues:
            memories = system.cued_retrieval(cue, CueType.WORD_CUE)
            for memory in memories:
                period_counts[memory.life_period.name] += 1

        total = sum(period_counts.values())

        return {
            'cue_count': len(cues),
            'period_distribution': {
                period: count / total if total > 0 else 0
                for period, count in period_counts.items()
            }
        }

    def run_music_cue_experiment(
        self,
        current_age: int = 50
    ) -> Dict[str, Any]:
        """Run music cue experiment - enhanced bump effect."""
        system = AutobiographicalMemorySystem(current_age)
        system.generate_lifespan_memories()

        # Music cues
        music_memories = system.cued_retrieval("favorite_song", CueType.MUSIC_CUE)

        # Word cues for comparison
        word_memories = system.cued_retrieval("memory", CueType.WORD_CUE)

        music_bump = sum(1 for m in music_memories if 15 <= m.age_at_event <= 25)
        word_bump = sum(1 for m in word_memories if 15 <= m.age_at_event <= 25)

        return {
            'music_memories': len(music_memories),
            'word_memories': len(word_memories),
            'music_bump_proportion': music_bump / len(music_memories) if music_memories else 0,
            'word_bump_proportion': word_bump / len(word_memories) if word_memories else 0,
            'music_enhancement': 'Music cues enhance bump period retrieval'
        }

    def run_age_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare bump across different current ages."""
        results = {}

        for current_age in [30, 50, 70]:
            system = AutobiographicalMemorySystem(current_age)
            system.generate_lifespan_memories()

            bump_memories = 0
            total_retrieved = 0

            for memory in system._memories.values():
                result = system.retrieve_memory(memory.id)
                if result.retrieved:
                    total_retrieved += 1
                    if 15 <= memory.age_at_event <= 25:
                        bump_memories += 1

            results[f"age_{current_age}"] = {
                'bump_proportion': bump_memories / total_retrieved if total_retrieved > 0 else 0,
                'total_retrieved': total_retrieved
            }

        return results


# ============================================================================
# REMINISCENCE BUMP ENGINE
# ============================================================================

class ReminiscenceBumpEngine:
    """
    Complete reminiscence bump engine.

    "Ba'el's lifespan memory engine." — Ba'el
    """

    def __init__(
        self,
        current_age: int = 50
    ):
        """Initialize engine."""
        self._paradigm = ReminiscenceBumpParadigm()
        self._system = AutobiographicalMemorySystem(current_age)
        self._current_age = current_age

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Memory operations

    def store_memory(
        self,
        description: str,
        age_at_event: int,
        memory_type: MemoryType = MemoryType.PERSONAL_EVENT
    ) -> AutobiographicalMemory:
        """Store a memory."""
        return self._system.store_memory(description, age_at_event, memory_type)

    def retrieve(
        self,
        memory_id: str
    ) -> RetrievalResult:
        """Retrieve a memory."""
        return self._system.retrieve_memory(memory_id)

    def cued_retrieval(
        self,
        cue: str,
        cue_type: CueType = CueType.WORD_CUE
    ) -> List[AutobiographicalMemory]:
        """Cued retrieval."""
        return self._system.cued_retrieval(cue, cue_type)

    # Experiments

    def run_lifespan_retrieval(
        self
    ) -> Dict[str, Any]:
        """Run lifespan retrieval experiment."""
        result = self._paradigm.run_lifespan_retrieval(self._current_age)
        self._experiment_results.append(result)
        return result

    def run_cue_word_experiment(
        self
    ) -> Dict[str, Any]:
        """Run cue word experiment."""
        return self._paradigm.run_cue_word_experiment(self._current_age)

    def run_music_experiment(
        self
    ) -> Dict[str, Any]:
        """Run music cue experiment."""
        return self._paradigm.run_music_cue_experiment(self._current_age)

    def run_age_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare across ages."""
        return self._paradigm.run_age_comparison()

    def run_first_experience_test(
        self
    ) -> Dict[str, Any]:
        """Test first experience hypothesis."""
        system = AutobiographicalMemorySystem(self._current_age)

        # Add first experiences in adolescence
        first_kiss = system.store_memory("first_kiss", 16, MemoryType.FIRST_EXPERIENCE, 0.9)
        first_job = system.store_memory("first_job", 18, MemoryType.FIRST_EXPERIENCE, 0.7)
        first_car = system.store_memory("first_car", 20, MemoryType.FIRST_EXPERIENCE, 0.8)

        # Add regular events
        regular_30 = system.store_memory("regular_event", 30, MemoryType.PERSONAL_EVENT, 0.5)
        regular_40 = system.store_memory("regular_event", 40, MemoryType.PERSONAL_EVENT, 0.5)

        first_retrieved = sum(1 for m in [first_kiss, first_job, first_car]
                             if system.retrieve_memory(m.id).retrieved)
        regular_retrieved = sum(1 for m in [regular_30, regular_40]
                               if system.retrieve_memory(m.id).retrieved)

        return {
            'first_experiences_retrieved': first_retrieved / 3,
            'regular_events_retrieved': regular_retrieved / 2,
            'first_experience_advantage': first_retrieved / 3 - regular_retrieved / 2
        }

    # Analysis

    def get_metrics(self) -> ReminiscenceBumpMetrics:
        """Get reminiscence bump metrics."""
        if not self._experiment_results:
            self.run_lifespan_retrieval()

        last = self._experiment_results[-1]

        return ReminiscenceBumpMetrics(
            bump_peak_age=20,
            bump_magnitude=last['bump_proportion'],
            childhood_amnesia_cutoff=3,
            recency_effect=last['recency_proportion']
        )

    def get_retrieval_curve(
        self
    ) -> Dict[int, float]:
        """Get expected retrieval curve by age."""
        return self._system._model.get_expected_distribution()

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'current_age': self._current_age,
            'memories': len(self._system._memories),
            'experiments': len(self._experiment_results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_reminiscence_bump_engine(
    current_age: int = 50
) -> ReminiscenceBumpEngine:
    """Create reminiscence bump engine."""
    return ReminiscenceBumpEngine(current_age)


def demonstrate_reminiscence_bump() -> Dict[str, Any]:
    """Demonstrate reminiscence bump."""
    engine = create_reminiscence_bump_engine(50)

    # Lifespan retrieval
    lifespan = engine.run_lifespan_retrieval()

    # Cue word experiment
    cue_word = engine.run_cue_word_experiment()

    # Music experiment
    music = engine.run_music_experiment()

    # Age comparison
    age_comp = engine.run_age_comparison()

    # First experience test
    first_exp = engine.run_first_experience_test()

    return {
        'reminiscence_bump': {
            'bump_proportion': f"{lifespan['bump_proportion']:.0%}",
            'childhood_proportion': f"{lifespan['childhood_proportion']:.0%}",
            'recency_proportion': f"{lifespan['recency_proportion']:.0%}"
        },
        'cue_word': {
            period: f"{prop:.0%}"
            for period, prop in cue_word['period_distribution'].items()
        },
        'music_effect': {
            'music_bump': f"{music['music_bump_proportion']:.0%}",
            'word_bump': f"{music['word_bump_proportion']:.0%}"
        },
        'first_experiences': {
            'first_exp': f"{first_exp['first_experiences_retrieved']:.0%}",
            'regular': f"{first_exp['regular_events_retrieved']:.0%}",
            'advantage': f"{first_exp['first_experience_advantage']:.0%}"
        },
        'interpretation': (
            f"Bump: {lifespan['bump_proportion']:.0%}. "
            f"Disproportionate memories from adolescence and early adulthood."
        )
    }


def get_reminiscence_bump_facts() -> Dict[str, str]:
    """Get facts about reminiscence bump."""
    return {
        'rubin_1986': 'Original reminiscence bump discovery',
        'age_range': 'Peak typically 15-25 years old',
        'cultural_universality': 'Found across cultures',
        'identity_formation': 'Period of identity development',
        'novel_experiences': 'Many firsts occur in this period',
        'cognitive_abilities': 'Peak cognitive abilities',
        'life_scripts': 'Cultural life scripts cluster here',
        'music_preferences': 'Musical taste also formed here'
    }
