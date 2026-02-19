"""
BAEL Mood Congruent Retrieval Engine
======================================

Mood at retrieval biases memory toward matching content.
Bower's associative network theory.

"Ba'el's emotions color all recollection." — Ba'el
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

logger = logging.getLogger("BAEL.MoodCongruentRetrieval")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class MoodType(Enum):
    """Type of mood."""
    HAPPY = auto()
    SAD = auto()
    ANXIOUS = auto()
    ANGRY = auto()
    NEUTRAL = auto()


class ContentValence(Enum):
    """Valence of memory content."""
    POSITIVE = auto()
    NEGATIVE = auto()
    NEUTRAL = auto()


class MemoryType(Enum):
    """Type of memory."""
    AUTOBIOGRAPHICAL = auto()
    WORD_LIST = auto()
    STORY = auto()
    FACES = auto()


class MoodInductionMethod(Enum):
    """Method of mood induction."""
    MUSIC = auto()
    FILM = auto()
    VELTEN = auto()       # Self-statements
    RECALL = auto()        # Recall autobiographical event
    HYPNOSIS = auto()


@dataclass
class MemoryItem:
    """
    A memory item.
    """
    id: str
    content: str
    valence: ContentValence
    arousal: float
    self_relevance: float


@dataclass
class MoodState:
    """
    Current mood state.
    """
    mood_type: MoodType
    intensity: float       # 0-1
    induction_method: MoodInductionMethod


@dataclass
class RetrievalTrial:
    """
    A retrieval trial.
    """
    item: MemoryItem
    mood_at_retrieval: MoodState
    recalled: bool
    congruent: bool
    latency_ms: int


@dataclass
class MoodCongruenceMetrics:
    """
    Mood congruence metrics.
    """
    congruent_recall: float
    incongruent_recall: float
    congruence_effect: float
    mood_intensity_correlation: float


# ============================================================================
# MOOD CONGRUENT MODEL
# ============================================================================

class MoodCongruentModel:
    """
    Model of mood-congruent retrieval.

    "Ba'el's emotional memory model." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Base recall
        self._base_recall = 0.50

        # Congruence boost
        self._congruence_boost = 0.15

        # Mood intensity effects
        self._intensity_weight = 0.20

        # Mood-valence mapping
        self._mood_valence = {
            MoodType.HAPPY: ContentValence.POSITIVE,
            MoodType.SAD: ContentValence.NEGATIVE,
            MoodType.ANXIOUS: ContentValence.NEGATIVE,
            MoodType.ANGRY: ContentValence.NEGATIVE,
            MoodType.NEUTRAL: ContentValence.NEUTRAL
        }

        # Asymmetry (depression shows stronger effect)
        self._sad_asymmetry = 0.05

        # Self-relevance
        self._self_relevance_weight = 0.12

        # Memory type effects
        self._autobio_boost = 0.10

        # Arousal effects
        self._arousal_weight = 0.08

        # Spreading activation
        self._activation_spread = 0.25

        self._lock = threading.RLock()

    def is_congruent(
        self,
        mood: MoodType,
        valence: ContentValence
    ) -> bool:
        """Check if mood and valence are congruent."""
        expected = self._mood_valence.get(mood, ContentValence.NEUTRAL)

        if expected == ContentValence.NEUTRAL:
            return True

        return expected == valence

    def calculate_recall_probability(
        self,
        mood: MoodState,
        item: MemoryItem,
        memory_type: MemoryType = MemoryType.WORD_LIST
    ) -> float:
        """Calculate recall probability."""
        base = self._base_recall

        # Congruence effect
        congruent = self.is_congruent(mood.mood_type, item.valence)

        if congruent:
            base += self._congruence_boost * mood.intensity
        else:
            base -= self._congruence_boost * mood.intensity * 0.5

        # Sad asymmetry
        if mood.mood_type == MoodType.SAD:
            if item.valence == ContentValence.NEGATIVE:
                base += self._sad_asymmetry

        # Self-relevance
        base += item.self_relevance * self._self_relevance_weight

        # Autobiographical boost
        if memory_type == MemoryType.AUTOBIOGRAPHICAL:
            base += self._autobio_boost

        # Arousal
        base += item.arousal * self._arousal_weight

        # Add noise
        base += random.uniform(-0.10, 0.10)

        return max(0.15, min(0.90, base))

    def calculate_spreading_activation(
        self,
        mood_intensity: float
    ) -> float:
        """Calculate spreading activation in network."""
        return self._activation_spread * mood_intensity

    def get_mechanisms(
        self
    ) -> Dict[str, str]:
        """Get proposed mechanisms."""
        return {
            'associative_network': 'Mood activates related nodes',
            'spreading_activation': 'Activation spreads to congruent memories',
            'schema': 'Mood activates schema',
            'accessibility': 'Congruent memories more accessible',
            'attention': 'Mood biases attention'
        }

    def get_asymmetries(
        self
    ) -> Dict[str, str]:
        """Get known asymmetries."""
        return {
            'depression': 'Strong negative bias',
            'happiness': 'Weaker positive bias',
            'clinical': 'Stronger in clinical populations',
            'autobiographical': 'Stronger for personal memories'
        }

    def get_bower_network(
        self
    ) -> str:
        """Get Bower's network description."""
        return (
            "Emotions as nodes in associative network\n"
            "Connected to related events, actions, labels\n"
            "Mood activation spreads to connected nodes"
        )


# ============================================================================
# MOOD CONGRUENT SYSTEM
# ============================================================================

class MoodCongruentSystem:
    """
    Mood congruent retrieval system.

    "Ba'el's emotional retrieval system." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = MoodCongruentModel()

        self._items: Dict[str, MemoryItem] = {}
        self._moods: List[MoodState] = []
        self._trials: List[RetrievalTrial] = []

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"mem_{self._counter}"

    def create_memory(
        self,
        content: str,
        valence: ContentValence = ContentValence.NEUTRAL,
        arousal: float = 0.5,
        self_relevance: float = 0.5
    ) -> MemoryItem:
        """Create memory item."""
        item = MemoryItem(
            id=self._generate_id(),
            content=content,
            valence=valence,
            arousal=arousal,
            self_relevance=self_relevance
        )

        self._items[item.id] = item

        return item

    def induce_mood(
        self,
        mood_type: MoodType,
        intensity: float = 0.7,
        method: MoodInductionMethod = MoodInductionMethod.MUSIC
    ) -> MoodState:
        """Induce mood state."""
        mood = MoodState(
            mood_type=mood_type,
            intensity=intensity,
            induction_method=method
        )

        self._moods.append(mood)

        return mood

    def retrieve_memory(
        self,
        item: MemoryItem,
        mood: MoodState,
        memory_type: MemoryType = MemoryType.WORD_LIST
    ) -> RetrievalTrial:
        """Attempt to retrieve memory."""
        prob = self._model.calculate_recall_probability(mood, item, memory_type)

        recalled = random.random() < prob
        congruent = self._model.is_congruent(mood.mood_type, item.valence)

        trial = RetrievalTrial(
            item=item,
            mood_at_retrieval=mood,
            recalled=recalled,
            congruent=congruent,
            latency_ms=random.randint(400, 2500)
        )

        self._trials.append(trial)

        return trial


# ============================================================================
# MOOD CONGRUENT PARADIGM
# ============================================================================

class MoodCongruentParadigm:
    """
    Mood congruent retrieval paradigm.

    "Ba'el's emotional memory study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_classic_paradigm(
        self,
        n_items_per_valence: int = 10
    ) -> Dict[str, Any]:
        """Run classic mood congruent paradigm."""
        system = MoodCongruentSystem()

        # Create memories of different valences
        items = []
        for valence in [ContentValence.POSITIVE, ContentValence.NEGATIVE]:
            for i in range(n_items_per_valence):
                item = system.create_memory(
                    f"{valence.name}_{i}",
                    valence=valence,
                    arousal=random.uniform(0.3, 0.8)
                )
                items.append(item)

        # Induce happy mood
        happy_mood = system.induce_mood(MoodType.HAPPY, intensity=0.7)

        # Test retrieval
        results = {
            'congruent': [],
            'incongruent': []
        }

        for item in items:
            trial = system.retrieve_memory(item, happy_mood)

            if trial.congruent:
                results['congruent'].append(trial.recalled)
            else:
                results['incongruent'].append(trial.recalled)

        cong_recall = sum(results['congruent']) / max(1, len(results['congruent']))
        incong_recall = sum(results['incongruent']) / max(1, len(results['incongruent']))

        effect = cong_recall - incong_recall

        return {
            'congruent_recall': cong_recall,
            'incongruent_recall': incong_recall,
            'congruence_effect': effect,
            'interpretation': f'Mood congruence: {effect:.0%} advantage'
        }

    def run_mood_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare different moods."""
        model = MoodCongruentModel()

        moods = [MoodType.HAPPY, MoodType.SAD, MoodType.NEUTRAL]

        results = {}

        for mood_type in moods:
            mood = MoodState(mood_type, 0.7, MoodInductionMethod.MUSIC)

            pos_item = MemoryItem("pos", "Happy", ContentValence.POSITIVE, 0.5, 0.5)
            neg_item = MemoryItem("neg", "Sad", ContentValence.NEGATIVE, 0.5, 0.5)

            pos_recall = model.calculate_recall_probability(mood, pos_item)
            neg_recall = model.calculate_recall_probability(mood, neg_item)

            results[mood_type.name] = {
                'positive_recall': pos_recall,
                'negative_recall': neg_recall,
                'bias': pos_recall - neg_recall
            }

        return {
            'by_mood': results,
            'interpretation': 'Happy boosts positive; sad boosts negative'
        }

    def run_intensity_study(
        self
    ) -> Dict[str, Any]:
        """Study mood intensity effects."""
        model = MoodCongruentModel()

        intensities = [0.2, 0.4, 0.6, 0.8, 1.0]

        results = {}

        for intensity in intensities:
            mood = MoodState(MoodType.HAPPY, intensity, MoodInductionMethod.MUSIC)
            pos_item = MemoryItem("pos", "Happy", ContentValence.POSITIVE, 0.5, 0.5)
            neg_item = MemoryItem("neg", "Sad", ContentValence.NEGATIVE, 0.5, 0.5)

            effect = (
                model.calculate_recall_probability(mood, pos_item) -
                model.calculate_recall_probability(mood, neg_item)
            )

            results[f'intensity_{intensity}'] = {'effect': effect}

        return {
            'by_intensity': results,
            'interpretation': 'Stronger mood = stronger congruence'
        }

    def run_memory_type_study(
        self
    ) -> Dict[str, Any]:
        """Study memory type effects."""
        model = MoodCongruentModel()

        results = {}

        mood = MoodState(MoodType.HAPPY, 0.7, MoodInductionMethod.MUSIC)
        pos_item = MemoryItem("pos", "Happy", ContentValence.POSITIVE, 0.5, 0.5)

        for mem_type in MemoryType:
            recall = model.calculate_recall_probability(mood, pos_item, mem_type)
            results[mem_type.name] = {'recall': recall}

        return {
            'by_type': results,
            'interpretation': 'Autobiographical shows strongest effect'
        }

    def run_asymmetry_study(
        self
    ) -> Dict[str, Any]:
        """Study mood asymmetries."""
        model = MoodCongruentModel()

        asymmetries = model.get_asymmetries()

        # Compare sad vs happy congruence effects
        happy_mood = MoodState(MoodType.HAPPY, 0.7, MoodInductionMethod.MUSIC)
        sad_mood = MoodState(MoodType.SAD, 0.7, MoodInductionMethod.MUSIC)

        pos_item = MemoryItem("pos", "Happy", ContentValence.POSITIVE, 0.5, 0.5)
        neg_item = MemoryItem("neg", "Sad", ContentValence.NEGATIVE, 0.5, 0.5)

        happy_cong = model.calculate_recall_probability(happy_mood, pos_item)
        happy_incong = model.calculate_recall_probability(happy_mood, neg_item)

        sad_cong = model.calculate_recall_probability(sad_mood, neg_item)
        sad_incong = model.calculate_recall_probability(sad_mood, pos_item)

        return {
            'happy_effect': happy_cong - happy_incong,
            'sad_effect': sad_cong - sad_incong,
            'asymmetries': asymmetries,
            'interpretation': 'Sad mood shows stronger congruence'
        }

    def run_mechanism_study(
        self
    ) -> Dict[str, Any]:
        """Study underlying mechanisms."""
        model = MoodCongruentModel()

        mechanisms = model.get_mechanisms()
        bower = model.get_bower_network()

        return {
            'mechanisms': mechanisms,
            'bower_network': bower,
            'interpretation': 'Associative network + spreading activation'
        }


# ============================================================================
# MOOD CONGRUENT ENGINE
# ============================================================================

class MoodCongruentEngine:
    """
    Complete mood congruent retrieval engine.

    "Ba'el's emotional memory engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = MoodCongruentParadigm()
        self._system = MoodCongruentSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Memory operations

    def create_memory(
        self,
        content: str,
        valence: ContentValence = ContentValence.NEUTRAL
    ) -> MemoryItem:
        """Create memory."""
        return self._system.create_memory(content, valence)

    def induce_mood(
        self,
        mood_type: MoodType,
        intensity: float = 0.7
    ) -> MoodState:
        """Induce mood."""
        return self._system.induce_mood(mood_type, intensity)

    def retrieve_memory(
        self,
        item: MemoryItem,
        mood: MoodState
    ) -> RetrievalTrial:
        """Retrieve memory."""
        return self._system.retrieve_memory(item, mood)

    # Experiments

    def run_classic(
        self
    ) -> Dict[str, Any]:
        """Run classic paradigm."""
        result = self._paradigm.run_classic_paradigm()
        self._experiment_results.append(result)
        return result

    def compare_moods(
        self
    ) -> Dict[str, Any]:
        """Compare moods."""
        return self._paradigm.run_mood_comparison()

    def study_intensity(
        self
    ) -> Dict[str, Any]:
        """Study intensity."""
        return self._paradigm.run_intensity_study()

    def study_memory_types(
        self
    ) -> Dict[str, Any]:
        """Study memory types."""
        return self._paradigm.run_memory_type_study()

    def study_asymmetry(
        self
    ) -> Dict[str, Any]:
        """Study asymmetry."""
        return self._paradigm.run_asymmetry_study()

    def study_mechanisms(
        self
    ) -> Dict[str, Any]:
        """Study mechanisms."""
        return self._paradigm.run_mechanism_study()

    # Analysis

    def get_metrics(self) -> MoodCongruenceMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_classic()

        last = self._experiment_results[-1]

        return MoodCongruenceMetrics(
            congruent_recall=last['congruent_recall'],
            incongruent_recall=last['incongruent_recall'],
            congruence_effect=last['congruence_effect'],
            mood_intensity_correlation=0.65
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'items': len(self._system._items),
            'moods': len(self._system._moods),
            'trials': len(self._system._trials)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_mood_congruent_engine() -> MoodCongruentEngine:
    """Create mood congruent engine."""
    return MoodCongruentEngine()


def demonstrate_mood_congruence() -> Dict[str, Any]:
    """Demonstrate mood congruent retrieval."""
    engine = create_mood_congruent_engine()

    # Classic
    classic = engine.run_classic()

    # Mood comparison
    moods = engine.compare_moods()

    # Asymmetry
    asymmetry = engine.study_asymmetry()

    # Mechanisms
    mechanisms = engine.study_mechanisms()

    return {
        'classic': {
            'congruent': f"{classic['congruent_recall']:.0%}",
            'incongruent': f"{classic['incongruent_recall']:.0%}",
            'effect': f"{classic['congruence_effect']:.0%}"
        },
        'by_mood': {
            k: f"bias={v['bias']:.0%}"
            for k, v in moods['by_mood'].items()
        },
        'asymmetry': {
            'happy': f"{asymmetry['happy_effect']:.0%}",
            'sad': f"{asymmetry['sad_effect']:.0%}"
        },
        'mechanisms': list(mechanisms['mechanisms'].keys()),
        'interpretation': (
            f"Effect: {classic['congruence_effect']:.0%}. "
            f"Mood at retrieval biases memory. "
            f"Associative network spreading activation."
        )
    }


def get_mood_congruence_facts() -> Dict[str, str]:
    """Get facts about mood congruent retrieval."""
    return {
        'bower_1981': 'Associative network theory',
        'effect': '10-20% recall advantage for congruent memories',
        'mechanism': 'Spreading activation in network',
        'asymmetry': 'Sad mood shows stronger effect',
        'autobiographical': 'Stronger for personal memories',
        'clinical': 'Exaggerated in depression',
        'vs_dependent': 'Different from mood-dependent memory',
        'applications': 'Depression, marketing, therapy'
    }
