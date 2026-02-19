"""
BAEL Mood-Dependent Memory Engine
===================================

State-dependent retrieval based on mood congruence.
Bower's associative network model.

"Ba'el remembers through emotional resonance." — Ba'el
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

logger = logging.getLogger("BAEL.MoodDependentMemory")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class MoodState(Enum):
    """Mood states."""
    HAPPY = auto()
    SAD = auto()
    ANXIOUS = auto()
    CALM = auto()
    ANGRY = auto()
    NEUTRAL = auto()


class MoodIntensity(Enum):
    """Intensity of mood."""
    MILD = auto()
    MODERATE = auto()
    INTENSE = auto()


class MemoryValence(Enum):
    """Valence of memory content."""
    POSITIVE = auto()
    NEGATIVE = auto()
    NEUTRAL = auto()


@dataclass
class MoodContext:
    """
    A mood context for encoding/retrieval.
    """
    mood: MoodState
    intensity: MoodIntensity
    arousal: float  # 0-1


@dataclass
class MemoryItem:
    """
    A memory item with mood association.
    """
    id: str
    content: str
    valence: MemoryValence
    encoding_mood: MoodContext
    mood_strength: float  # How strongly associated with mood


@dataclass
class RetrievalAttempt:
    """
    A retrieval attempt result.
    """
    item_id: str
    encoding_mood: MoodState
    retrieval_mood: MoodState
    mood_match: bool
    retrieved: bool
    retrieval_strength: float


@dataclass
class MoodDependentMetrics:
    """
    Mood-dependent memory metrics.
    """
    congruent_recall: float
    incongruent_recall: float
    mood_congruence_effect: float
    mood_dependent_effect: float


# ============================================================================
# ASSOCIATIVE NETWORK MODEL
# ============================================================================

class AssociativeNetworkModel:
    """
    Bower's associative network model.

    "Ba'el's emotional network." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Mood node activation
        self._mood_nodes: Dict[MoodState, float] = {
            mood: 0.0 for mood in MoodState
        }

        # Mood congruence parameters
        self._congruence_boost = 0.25
        self._state_dependency = 0.15
        self._valence_match_boost = 0.1

        self._base_retrieval = 0.4

        self._lock = threading.RLock()

    def activate_mood(
        self,
        mood: MoodState,
        intensity: MoodIntensity
    ) -> None:
        """Activate a mood node."""
        # Reset all moods
        for m in self._mood_nodes:
            self._mood_nodes[m] = 0.1

        # Activate current mood
        if intensity == MoodIntensity.INTENSE:
            activation = 0.9
        elif intensity == MoodIntensity.MODERATE:
            activation = 0.6
        else:
            activation = 0.4

        self._mood_nodes[mood] = activation

        # Some spread to similar moods
        if mood == MoodState.HAPPY:
            self._mood_nodes[MoodState.CALM] = activation * 0.3
        elif mood == MoodState.SAD:
            self._mood_nodes[MoodState.ANXIOUS] = activation * 0.2

    def get_mood_match_strength(
        self,
        encoding_mood: MoodState,
        retrieval_mood: MoodState
    ) -> float:
        """Get strength of mood match."""
        if encoding_mood == retrieval_mood:
            return 1.0

        # Similar moods
        similar_pairs = [
            (MoodState.HAPPY, MoodState.CALM),
            (MoodState.SAD, MoodState.ANXIOUS),
            (MoodState.ANGRY, MoodState.ANXIOUS)
        ]

        for pair in similar_pairs:
            if (encoding_mood, retrieval_mood) in [pair, pair[::-1]]:
                return 0.5

        return 0.0

    def calculate_retrieval_probability(
        self,
        item: MemoryItem,
        retrieval_context: MoodContext
    ) -> float:
        """Calculate retrieval probability."""
        prob = self._base_retrieval

        # Mood state dependency
        mood_match = self.get_mood_match_strength(
            item.encoding_mood.mood,
            retrieval_context.mood
        )
        prob += mood_match * self._state_dependency

        # Mood congruence (current mood matches memory valence)
        if retrieval_context.mood == MoodState.HAPPY and item.valence == MemoryValence.POSITIVE:
            prob += self._congruence_boost
        elif retrieval_context.mood == MoodState.SAD and item.valence == MemoryValence.NEGATIVE:
            prob += self._congruence_boost

        # Intensity effect
        if retrieval_context.intensity == MoodIntensity.INTENSE:
            prob *= 1.2

        # Item's mood association strength
        prob += item.mood_strength * 0.1

        return min(0.95, max(0.1, prob))


# ============================================================================
# MOOD-DEPENDENT MEMORY SYSTEM
# ============================================================================

class MoodDependentMemorySystem:
    """
    Mood-dependent memory system.

    "Ba'el's emotional memories." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._network = AssociativeNetworkModel()

        self._items: Dict[str, MemoryItem] = {}
        self._attempts: List[RetrievalAttempt] = []

        self._current_mood: MoodContext = MoodContext(
            mood=MoodState.NEUTRAL,
            intensity=MoodIntensity.MILD,
            arousal=0.5
        )

        self._item_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._item_counter += 1
        return f"item_{self._item_counter}"

    def set_mood(
        self,
        mood: MoodState,
        intensity: MoodIntensity = MoodIntensity.MODERATE
    ) -> None:
        """Set current mood state."""
        self._current_mood = MoodContext(
            mood=mood,
            intensity=intensity,
            arousal=0.5 if intensity == MoodIntensity.MILD else 0.7
        )
        self._network.activate_mood(mood, intensity)

    def encode_item(
        self,
        content: str,
        valence: MemoryValence = MemoryValence.NEUTRAL
    ) -> MemoryItem:
        """Encode an item in current mood."""
        item = MemoryItem(
            id=self._generate_id(),
            content=content,
            valence=valence,
            encoding_mood=MoodContext(
                mood=self._current_mood.mood,
                intensity=self._current_mood.intensity,
                arousal=self._current_mood.arousal
            ),
            mood_strength=random.uniform(0.3, 0.8)
        )

        self._items[item.id] = item
        return item

    def retrieve_item(
        self,
        item_id: str
    ) -> RetrievalAttempt:
        """Attempt to retrieve an item."""
        item = self._items.get(item_id)
        if not item:
            return None

        prob = self._network.calculate_retrieval_probability(
            item, self._current_mood
        )

        retrieved = random.random() < prob
        mood_match = item.encoding_mood.mood == self._current_mood.mood

        attempt = RetrievalAttempt(
            item_id=item_id,
            encoding_mood=item.encoding_mood.mood,
            retrieval_mood=self._current_mood.mood,
            mood_match=mood_match,
            retrieved=retrieved,
            retrieval_strength=prob
        )

        self._attempts.append(attempt)

        return attempt


# ============================================================================
# EXPERIMENTAL PARADIGM
# ============================================================================

class MoodDependentParadigm:
    """
    Mood-dependent memory paradigm.

    "Ba'el's mood congruence study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_state_dependency_experiment(
        self,
        n_items: int = 20
    ) -> Dict[str, Any]:
        """Run mood state dependency experiment."""
        system = MoodDependentMemorySystem()

        # Encode in happy mood
        system.set_mood(MoodState.HAPPY, MoodIntensity.MODERATE)
        happy_items = []
        for i in range(n_items // 2):
            item = system.encode_item(f"happy_content_{i}")
            happy_items.append(item)

        # Encode in sad mood
        system.set_mood(MoodState.SAD, MoodIntensity.MODERATE)
        sad_items = []
        for i in range(n_items // 2):
            item = system.encode_item(f"sad_content_{i}")
            sad_items.append(item)

        # Test in happy mood
        system.set_mood(MoodState.HAPPY, MoodIntensity.MODERATE)

        happy_match = sum(1 for item in happy_items
                        if system.retrieve_item(item.id).retrieved)
        sad_mismatch = sum(1 for item in sad_items
                         if system.retrieve_item(item.id).retrieved)

        # Test in sad mood
        system.set_mood(MoodState.SAD, MoodIntensity.MODERATE)

        sad_match = sum(1 for item in sad_items
                       if system.retrieve_item(item.id).retrieved)
        happy_mismatch = sum(1 for item in happy_items
                           if system.retrieve_item(item.id).retrieved)

        n = n_items // 2
        match_recall = (happy_match + sad_match) / (n * 2)
        mismatch_recall = (happy_mismatch + sad_mismatch) / (n * 2)

        return {
            'n_items': n_items,
            'mood_match_recall': match_recall,
            'mood_mismatch_recall': mismatch_recall,
            'state_dependency_effect': match_recall - mismatch_recall
        }

    def run_mood_congruence_experiment(
        self,
        n_items: int = 20
    ) -> Dict[str, Any]:
        """Run mood congruence experiment."""
        system = MoodDependentMemorySystem()
        system.set_mood(MoodState.NEUTRAL, MoodIntensity.MILD)

        # Encode positive and negative items
        positive_items = []
        negative_items = []

        for i in range(n_items // 2):
            item = system.encode_item(f"positive_{i}", MemoryValence.POSITIVE)
            positive_items.append(item)

        for i in range(n_items // 2):
            item = system.encode_item(f"negative_{i}", MemoryValence.NEGATIVE)
            negative_items.append(item)

        # Test in happy mood
        system.set_mood(MoodState.HAPPY, MoodIntensity.MODERATE)

        positive_in_happy = sum(1 for item in positive_items
                               if system.retrieve_item(item.id).retrieved)
        negative_in_happy = sum(1 for item in negative_items
                               if system.retrieve_item(item.id).retrieved)

        # Test in sad mood
        system.set_mood(MoodState.SAD, MoodIntensity.MODERATE)

        positive_in_sad = sum(1 for item in positive_items
                             if system.retrieve_item(item.id).retrieved)
        negative_in_sad = sum(1 for item in negative_items
                             if system.retrieve_item(item.id).retrieved)

        n = n_items // 2

        return {
            'positive_in_happy': positive_in_happy / n,
            'negative_in_happy': negative_in_happy / n,
            'positive_in_sad': positive_in_sad / n,
            'negative_in_sad': negative_in_sad / n,
            'happy_congruence': (positive_in_happy - negative_in_happy) / n,
            'sad_congruence': (negative_in_sad - positive_in_sad) / n
        }

    def run_intensity_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare effect across mood intensities."""
        results = {}

        for intensity in MoodIntensity:
            system = MoodDependentMemorySystem()

            # Encode in happy mood
            system.set_mood(MoodState.HAPPY, intensity)
            items = []
            for i in range(10):
                item = system.encode_item(f"item_{i}")
                items.append(item)

            # Test in same mood
            system.set_mood(MoodState.HAPPY, intensity)
            match_recall = sum(1 for item in items
                              if system.retrieve_item(item.id).retrieved) / 10

            # Test in different mood
            system.set_mood(MoodState.SAD, intensity)
            mismatch_recall = sum(1 for item in items
                                 if system.retrieve_item(item.id).retrieved) / 10

            results[intensity.name] = {
                'match': match_recall,
                'mismatch': mismatch_recall,
                'effect': match_recall - mismatch_recall
            }

        return results


# ============================================================================
# MOOD-DEPENDENT MEMORY ENGINE
# ============================================================================

class MoodDependentMemoryEngine:
    """
    Complete mood-dependent memory engine.

    "Ba'el's emotional retrieval system." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = MoodDependentParadigm()
        self._system = MoodDependentMemorySystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Mood control

    def set_mood(
        self,
        mood: MoodState,
        intensity: MoodIntensity = MoodIntensity.MODERATE
    ) -> None:
        """Set current mood."""
        self._system.set_mood(mood, intensity)

    # Memory operations

    def encode(
        self,
        content: str,
        valence: MemoryValence = MemoryValence.NEUTRAL
    ) -> MemoryItem:
        """Encode an item."""
        return self._system.encode_item(content, valence)

    def retrieve(
        self,
        item_id: str
    ) -> RetrievalAttempt:
        """Retrieve an item."""
        return self._system.retrieve_item(item_id)

    # Experiments

    def run_state_dependency_experiment(
        self,
        n_items: int = 20
    ) -> Dict[str, Any]:
        """Run state dependency experiment."""
        result = self._paradigm.run_state_dependency_experiment(n_items)
        self._experiment_results.append(result)
        return result

    def run_congruence_experiment(
        self,
        n_items: int = 20
    ) -> Dict[str, Any]:
        """Run mood congruence experiment."""
        return self._paradigm.run_mood_congruence_experiment(n_items)

    def run_intensity_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare intensity levels."""
        return self._paradigm.run_intensity_comparison()

    def run_asymmetry_test(
        self
    ) -> Dict[str, Any]:
        """Test asymmetry in mood effects."""
        # Typically positive mood shows weaker effects

        system = MoodDependentMemorySystem()

        # Encode in happy
        system.set_mood(MoodState.HAPPY)
        happy_items = [system.encode_item(f"h_{i}") for i in range(10)]

        # Encode in sad
        system.set_mood(MoodState.SAD)
        sad_items = [system.encode_item(f"s_{i}") for i in range(10)]

        # Test happy items in both moods
        system.set_mood(MoodState.HAPPY)
        happy_in_happy = sum(1 for i in happy_items if system.retrieve_item(i.id).retrieved)

        system.set_mood(MoodState.SAD)
        happy_in_sad = sum(1 for i in happy_items if system.retrieve_item(i.id).retrieved)

        # Test sad items in both moods
        system.set_mood(MoodState.HAPPY)
        sad_in_happy = sum(1 for i in sad_items if system.retrieve_item(i.id).retrieved)

        system.set_mood(MoodState.SAD)
        sad_in_sad = sum(1 for i in sad_items if system.retrieve_item(i.id).retrieved)

        return {
            'happy_encoding_effect': (happy_in_happy - happy_in_sad) / 10,
            'sad_encoding_effect': (sad_in_sad - sad_in_happy) / 10,
            'asymmetry': 'Sad mood typically shows stronger effects'
        }

    # Analysis

    def get_metrics(self) -> MoodDependentMetrics:
        """Get mood-dependent metrics."""
        if not self._experiment_results:
            self.run_state_dependency_experiment()

        last = self._experiment_results[-1]
        congruence = self.run_congruence_experiment()

        return MoodDependentMetrics(
            congruent_recall=last['mood_match_recall'],
            incongruent_recall=last['mood_mismatch_recall'],
            mood_congruence_effect=congruence['happy_congruence'],
            mood_dependent_effect=last['state_dependency_effect']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'items': len(self._system._items),
            'attempts': len(self._system._attempts),
            'current_mood': self._system._current_mood.mood.name,
            'experiments': len(self._experiment_results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_mood_dependent_engine() -> MoodDependentMemoryEngine:
    """Create mood-dependent memory engine."""
    return MoodDependentMemoryEngine()


def demonstrate_mood_dependent_memory() -> Dict[str, Any]:
    """Demonstrate mood-dependent memory."""
    engine = create_mood_dependent_engine()

    # State dependency
    state_dep = engine.run_state_dependency_experiment(20)

    # Mood congruence
    congruence = engine.run_congruence_experiment(20)

    # Intensity comparison
    intensity = engine.run_intensity_comparison()

    # Asymmetry test
    asymmetry = engine.run_asymmetry_test()

    return {
        'state_dependency': {
            'mood_match': f"{state_dep['mood_match_recall']:.0%}",
            'mood_mismatch': f"{state_dep['mood_mismatch_recall']:.0%}",
            'effect': f"{state_dep['state_dependency_effect']:.0%}"
        },
        'mood_congruence': {
            'positive_in_happy': f"{congruence['positive_in_happy']:.0%}",
            'negative_in_happy': f"{congruence['negative_in_happy']:.0%}",
            'happy_bias': f"{congruence['happy_congruence']:.0%}",
            'sad_bias': f"{congruence['sad_congruence']:.0%}"
        },
        'intensity_effect': {
            inten: f"effect: {data['effect']:.0%}"
            for inten, data in intensity.items()
        },
        'asymmetry': {
            'happy_effect': f"{asymmetry['happy_encoding_effect']:.0%}",
            'sad_effect': f"{asymmetry['sad_encoding_effect']:.0%}"
        },
        'interpretation': (
            f"State dependency: {state_dep['state_dependency_effect']:.0%}. "
            f"Memory retrieval is enhanced when mood at retrieval matches encoding mood."
        )
    }


def get_mood_dependent_facts() -> Dict[str, str]:
    """Get facts about mood-dependent memory."""
    return {
        'bower_1981': 'Associative network model of mood and memory',
        'state_dependency': 'Same mood at encoding and retrieval helps',
        'mood_congruence': 'Current mood biases toward matching valence',
        'clinical': 'Relevant to depression maintenance',
        'asymmetry': 'Negative moods often show stronger effects',
        'intensity': 'Stronger moods produce stronger effects',
        'music_induction': 'Common method to manipulate mood',
        'real_world': 'Affects autobiographical memory retrieval'
    }
