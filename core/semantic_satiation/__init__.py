"""
BAEL Semantic Satiation Engine
================================

Temporary loss of meaning with repetition.
Severance's semantic satiation phenomenon.

"Ba'el repeats until meaning dissolves." — Ba'el
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

logger = logging.getLogger("BAEL.SemanticSatiation")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class WordType(Enum):
    """Type of word."""
    CONCRETE = auto()
    ABSTRACT = auto()
    FUNCTION_WORD = auto()
    PROPER_NOUN = auto()


class SatiationLevel(Enum):
    """Level of semantic satiation."""
    NONE = auto()
    MILD = auto()
    MODERATE = auto()
    SEVERE = auto()
    COMPLETE = auto()


class RecoveryState(Enum):
    """State of recovery from satiation."""
    SATIATED = auto()
    RECOVERING = auto()
    RECOVERED = auto()


@dataclass
class Word:
    """
    A word that can be satiated.
    """
    id: str
    text: str
    word_type: WordType
    semantic_richness: float  # How much meaning
    frequency: float          # Usage frequency


@dataclass
class SemanticState:
    """
    Semantic state of a word.
    """
    word_id: str
    meaning_availability: float  # 0-1
    satiation_level: SatiationLevel
    repetition_count: int
    recovery_state: RecoveryState


@dataclass
class SatiationEvent:
    """
    A satiation event.
    """
    word_id: str
    repetitions_to_satiate: int
    max_satiation_level: SatiationLevel
    recovery_time_seconds: float


@dataclass
class SemanticSatiationMetrics:
    """
    Semantic satiation metrics.
    """
    avg_repetitions_to_satiate: float
    satiation_depth: float
    recovery_rate: float
    concrete_abstract_diff: float


# ============================================================================
# SEMANTIC NETWORK FATIGUE MODEL
# ============================================================================

class SemanticNetworkFatigueModel:
    """
    Model of semantic network fatigue from repetition.

    "Ba'el's meaning exhaustion." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Satiation parameters
        self._base_satiation_rate = 0.05  # Per repetition
        self._max_satiation = 1.0

        # Word type effects
        self._type_satiation_rates = {
            WordType.CONCRETE: 0.04,   # Concrete words satiate slower
            WordType.ABSTRACT: 0.06,   # Abstract words satiate faster
            WordType.FUNCTION_WORD: 0.03,  # Function words very resistant
            WordType.PROPER_NOUN: 0.05
        }

        # Semantic richness effect
        self._richness_protection = 0.3  # Higher richness = more resistant

        # Recovery parameters
        self._base_recovery_rate = 0.1  # Per second
        self._recovery_variability = 0.05

        self._lock = threading.RLock()

    def calculate_satiation_rate(
        self,
        word: Word
    ) -> float:
        """Calculate satiation rate for a word."""
        base_rate = self._type_satiation_rates.get(
            word.word_type, self._base_satiation_rate
        )

        # Semantic richness protects against satiation
        rate = base_rate * (1 - word.semantic_richness * self._richness_protection)

        # High frequency words more resistant
        rate *= (1 - word.frequency * 0.2)

        return max(0.01, rate)

    def calculate_satiation_after_repetition(
        self,
        state: SemanticState,
        word: Word
    ) -> float:
        """Calculate satiation level after one more repetition."""
        rate = self.calculate_satiation_rate(word)

        # Satiation increases with each repetition
        new_satiation = 1 - state.meaning_availability
        new_satiation += rate

        # Diminishing returns at high satiation
        new_satiation = min(self._max_satiation, new_satiation)

        return 1 - new_satiation  # Return meaning availability

    def get_satiation_level(
        self,
        meaning_availability: float
    ) -> SatiationLevel:
        """Get satiation level category."""
        if meaning_availability >= 0.9:
            return SatiationLevel.NONE
        elif meaning_availability >= 0.7:
            return SatiationLevel.MILD
        elif meaning_availability >= 0.5:
            return SatiationLevel.MODERATE
        elif meaning_availability >= 0.3:
            return SatiationLevel.SEVERE
        else:
            return SatiationLevel.COMPLETE

    def calculate_recovery(
        self,
        state: SemanticState,
        time_seconds: float
    ) -> float:
        """Calculate meaning recovery over time."""
        if state.meaning_availability >= 1.0:
            return 1.0

        # Recovery is exponential
        recovery_amount = self._base_recovery_rate * time_seconds
        recovery_amount *= (1 + random.uniform(-self._recovery_variability, self._recovery_variability))

        new_availability = state.meaning_availability + recovery_amount

        return min(1.0, new_availability)


# ============================================================================
# SEMANTIC SATIATION SYSTEM
# ============================================================================

class SemanticSatiationSystem:
    """
    Semantic satiation simulation system.

    "Ba'el's meaning loss system." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = SemanticNetworkFatigueModel()

        self._words: Dict[str, Word] = {}
        self._states: Dict[str, SemanticState] = {}
        self._events: List[SatiationEvent] = []

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"word_{self._counter}"

    def create_word(
        self,
        text: str,
        word_type: WordType = WordType.CONCRETE,
        semantic_richness: float = 0.5
    ) -> Word:
        """Create a word."""
        word = Word(
            id=self._generate_id(),
            text=text,
            word_type=word_type,
            semantic_richness=semantic_richness,
            frequency=random.uniform(0.1, 0.8)
        )

        self._words[word.id] = word

        # Initialize state
        self._states[word.id] = SemanticState(
            word_id=word.id,
            meaning_availability=1.0,
            satiation_level=SatiationLevel.NONE,
            repetition_count=0,
            recovery_state=RecoveryState.RECOVERED
        )

        return word

    def repeat_word(
        self,
        word_id: str,
        times: int = 1
    ) -> SemanticState:
        """Repeat a word and update satiation."""
        word = self._words.get(word_id)
        state = self._states.get(word_id)

        if not word or not state:
            return None

        for _ in range(times):
            state.repetition_count += 1
            state.meaning_availability = self._model.calculate_satiation_after_repetition(
                state, word
            )
            state.satiation_level = self._model.get_satiation_level(state.meaning_availability)

            if state.meaning_availability < 0.7:
                state.recovery_state = RecoveryState.SATIATED

        return state

    def let_recover(
        self,
        word_id: str,
        seconds: float
    ) -> SemanticState:
        """Let a word recover for some time."""
        state = self._states.get(word_id)

        if not state:
            return None

        old_availability = state.meaning_availability
        state.meaning_availability = self._model.calculate_recovery(state, seconds)

        # Update recovery state
        if state.meaning_availability >= 0.95:
            state.recovery_state = RecoveryState.RECOVERED
        elif state.meaning_availability > old_availability:
            state.recovery_state = RecoveryState.RECOVERING

        state.satiation_level = self._model.get_satiation_level(state.meaning_availability)

        return state

    def run_satiation_trial(
        self,
        word_id: str,
        max_repetitions: int = 100
    ) -> SatiationEvent:
        """Run satiation trial until word is satiated."""
        word = self._words.get(word_id)
        state = self._states.get(word_id)

        if not word or not state:
            return None

        # Reset state
        state.meaning_availability = 1.0
        state.repetition_count = 0
        state.satiation_level = SatiationLevel.NONE

        # Repeat until satiated or max reached
        while state.meaning_availability > 0.5 and state.repetition_count < max_repetitions:
            self.repeat_word(word_id, 1)

        # Test recovery
        recovery_time = 0.0
        while state.meaning_availability < 0.9 and recovery_time < 60:
            self.let_recover(word_id, 1.0)
            recovery_time += 1.0

        event = SatiationEvent(
            word_id=word_id,
            repetitions_to_satiate=state.repetition_count,
            max_satiation_level=state.satiation_level,
            recovery_time_seconds=recovery_time
        )

        self._events.append(event)

        return event


# ============================================================================
# SEMANTIC SATIATION PARADIGM
# ============================================================================

class SemanticSatiationParadigm:
    """
    Semantic satiation experimental paradigm.

    "Ba'el's repetition study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_basic_satiation_experiment(
        self,
        word_text: str = "tree",
        word_type: WordType = WordType.CONCRETE
    ) -> Dict[str, Any]:
        """Run basic satiation experiment."""
        system = SemanticSatiationSystem()

        word = system.create_word(word_text, word_type)

        # Track satiation across repetitions
        repetition_curve = []

        for i in range(50):
            system.repeat_word(word.id, 1)
            state = system._states[word.id]
            repetition_curve.append({
                'repetition': i + 1,
                'meaning': state.meaning_availability,
                'level': state.satiation_level.name
            })

        # Find satiation point
        satiation_point = None
        for point in repetition_curve:
            if point['meaning'] < 0.5:
                satiation_point = point['repetition']
                break

        return {
            'word': word_text,
            'type': word_type.name,
            'satiation_point': satiation_point,
            'final_meaning': repetition_curve[-1]['meaning'],
            'curve': repetition_curve
        }

    def run_word_type_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare satiation across word types."""
        results = {}

        test_words = {
            WordType.CONCRETE: "table",
            WordType.ABSTRACT: "freedom",
            WordType.FUNCTION_WORD: "the",
            WordType.PROPER_NOUN: "Paris"
        }

        for word_type, word_text in test_words.items():
            system = SemanticSatiationSystem()
            word = system.create_word(word_text, word_type)

            event = system.run_satiation_trial(word.id)

            results[word_type.name] = {
                'word': word_text,
                'repetitions_to_satiate': event.repetitions_to_satiate,
                'max_level': event.max_satiation_level.name,
                'recovery_time': event.recovery_time_seconds
            }

        return results

    def run_semantic_richness_study(
        self
    ) -> Dict[str, Any]:
        """Study effect of semantic richness on satiation."""
        richness_levels = [0.2, 0.5, 0.8]
        results = {}

        for richness in richness_levels:
            system = SemanticSatiationSystem()

            word = system.create_word(
                f"word_r{richness}",
                WordType.CONCRETE,
                semantic_richness=richness
            )

            event = system.run_satiation_trial(word.id)

            results[f"richness_{richness}"] = {
                'repetitions': event.repetitions_to_satiate,
                'recovery': event.recovery_time_seconds
            }

        return results

    def run_recovery_study(
        self
    ) -> Dict[str, Any]:
        """Study recovery from satiation."""
        system = SemanticSatiationSystem()
        word = system.create_word("test", WordType.CONCRETE)

        # Satiate the word
        for _ in range(40):
            system.repeat_word(word.id, 1)

        satiated_level = system._states[word.id].meaning_availability

        # Track recovery
        recovery_curve = []
        for second in range(30):
            system.let_recover(word.id, 1.0)
            state = system._states[word.id]
            recovery_curve.append({
                'time': second + 1,
                'meaning': state.meaning_availability
            })

        # Find recovery point
        recovery_point = None
        for point in recovery_curve:
            if point['meaning'] >= 0.9:
                recovery_point = point['time']
                break

        return {
            'satiated_level': satiated_level,
            'recovery_point_seconds': recovery_point,
            'final_recovery': recovery_curve[-1]['meaning'],
            'curve': recovery_curve
        }

    def run_massed_vs_spaced_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare massed vs spaced repetition."""
        # Massed: all repetitions at once
        massed_system = SemanticSatiationSystem()
        massed_word = massed_system.create_word("massed", WordType.CONCRETE)

        for _ in range(30):
            massed_system.repeat_word(massed_word.id, 1)

        massed_satiation = massed_system._states[massed_word.id].meaning_availability

        # Spaced: repetitions with gaps
        spaced_system = SemanticSatiationSystem()
        spaced_word = spaced_system.create_word("spaced", WordType.CONCRETE)

        for _ in range(30):
            spaced_system.repeat_word(spaced_word.id, 1)
            spaced_system.let_recover(spaced_word.id, 2.0)  # Brief pause

        spaced_satiation = spaced_system._states[spaced_word.id].meaning_availability

        return {
            'massed_meaning': massed_satiation,
            'spaced_meaning': spaced_satiation,
            'spacing_protection': spaced_satiation - massed_satiation,
            'interpretation': 'Spacing prevents satiation by allowing recovery'
        }


# ============================================================================
# SEMANTIC SATIATION ENGINE
# ============================================================================

class SemanticSatiationEngine:
    """
    Complete semantic satiation engine.

    "Ba'el's meaning exhaustion engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = SemanticSatiationParadigm()
        self._system = SemanticSatiationSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Word management

    def create_word(
        self,
        text: str,
        word_type: WordType = WordType.CONCRETE
    ) -> Word:
        """Create a word."""
        return self._system.create_word(text, word_type)

    def repeat(
        self,
        word_id: str,
        times: int = 1
    ) -> SemanticState:
        """Repeat a word."""
        return self._system.repeat_word(word_id, times)

    def recover(
        self,
        word_id: str,
        seconds: float
    ) -> SemanticState:
        """Let word recover."""
        return self._system.let_recover(word_id, seconds)

    def run_trial(
        self,
        word_id: str
    ) -> SatiationEvent:
        """Run satiation trial."""
        return self._system.run_satiation_trial(word_id)

    # Experiments

    def run_basic_experiment(
        self,
        word: str = "tree"
    ) -> Dict[str, Any]:
        """Run basic experiment."""
        result = self._paradigm.run_basic_satiation_experiment(word)
        self._experiment_results.append(result)
        return result

    def compare_word_types(
        self
    ) -> Dict[str, Any]:
        """Compare word types."""
        return self._paradigm.run_word_type_comparison()

    def study_richness(
        self
    ) -> Dict[str, Any]:
        """Study semantic richness."""
        return self._paradigm.run_semantic_richness_study()

    def study_recovery(
        self
    ) -> Dict[str, Any]:
        """Study recovery."""
        return self._paradigm.run_recovery_study()

    def compare_massed_spaced(
        self
    ) -> Dict[str, Any]:
        """Compare massed vs spaced."""
        return self._paradigm.run_massed_vs_spaced_comparison()

    def demonstrate_subjective_experience(
        self,
        word: str = "bowl"
    ) -> Dict[str, Any]:
        """Demonstrate subjective satiation experience."""
        system = SemanticSatiationSystem()
        w = system.create_word(word, WordType.CONCRETE)

        stages = []

        # Initial state
        stages.append({
            'repetition': 0,
            'experience': f"'{word}' has clear meaning",
            'meaning': system._states[w.id].meaning_availability
        })

        # Repeat
        for i in [5, 15, 30]:
            target = i - (stages[-1]['repetition'] if stages else 0)
            system.repeat_word(w.id, target)
            state = system._states[w.id]

            if state.meaning_availability > 0.8:
                exp = f"'{word}' still meaningful"
            elif state.meaning_availability > 0.5:
                exp = f"'{word}' starting to feel strange"
            else:
                exp = f"'{word}' feels like nonsense syllables"

            stages.append({
                'repetition': i,
                'experience': exp,
                'meaning': state.meaning_availability
            })

        return {
            'word': word,
            'progression': stages,
            'final_state': stages[-1]['experience']
        }

    # Analysis

    def get_metrics(self) -> SemanticSatiationMetrics:
        """Get semantic satiation metrics."""
        if not self._experiment_results:
            self.run_basic_experiment()

        types = self.compare_word_types()

        concrete_reps = types['CONCRETE']['repetitions_to_satiate']
        abstract_reps = types['ABSTRACT']['repetitions_to_satiate']

        return SemanticSatiationMetrics(
            avg_repetitions_to_satiate=self._experiment_results[-1]['satiation_point'] or 30,
            satiation_depth=1 - self._experiment_results[-1]['final_meaning'],
            recovery_rate=0.1,  # Per second
            concrete_abstract_diff=concrete_reps - abstract_reps
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'words': len(self._system._words),
            'events': len(self._system._events),
            'experiments': len(self._experiment_results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_semantic_satiation_engine() -> SemanticSatiationEngine:
    """Create semantic satiation engine."""
    return SemanticSatiationEngine()


def demonstrate_semantic_satiation() -> Dict[str, Any]:
    """Demonstrate semantic satiation."""
    engine = create_semantic_satiation_engine()

    # Basic experiment
    basic = engine.run_basic_experiment("tree")

    # Word type comparison
    types = engine.compare_word_types()

    # Richness study
    richness = engine.study_richness()

    # Recovery study
    recovery = engine.study_recovery()

    # Massed vs spaced
    spacing = engine.compare_massed_spaced()

    # Subjective experience
    subjective = engine.demonstrate_subjective_experience("bowl")

    return {
        'satiation': {
            'word': basic['word'],
            'satiation_point': basic['satiation_point'],
            'final_meaning': f"{basic['final_meaning']:.0%}"
        },
        'by_word_type': {
            wtype: f"{data['repetitions_to_satiate']} reps"
            for wtype, data in types.items()
        },
        'richness_effect': {
            level: f"{data['repetitions']} reps"
            for level, data in richness.items()
        },
        'recovery': {
            'time_to_recover': f"{recovery['recovery_point_seconds']}s",
            'final': f"{recovery['final_recovery']:.0%}"
        },
        'spacing': {
            'massed': f"{spacing['massed_meaning']:.0%}",
            'spaced': f"{spacing['spaced_meaning']:.0%}",
            'protection': f"{spacing['spacing_protection']:.0%}"
        },
        'interpretation': (
            f"Satiation at ~{basic['satiation_point']} repetitions. "
            f"Abstract words satiate faster. Recovery in ~{recovery['recovery_point_seconds']}s."
        )
    }


def get_semantic_satiation_facts() -> Dict[str, str]:
    """Get facts about semantic satiation."""
    return {
        'severance_1910': 'Early observations of the phenomenon',
        'smith_klein_1990': 'Modern experimental study',
        'temporary': 'Effect is temporary, recovers in seconds',
        'abstract_faster': 'Abstract words satiate faster',
        'network_fatigue': 'Caused by semantic network fatigue',
        'subjective': 'Word feels like meaningless syllables',
        'recovery': 'Full recovery within 10-30 seconds typically',
        'applications': 'Used in studies of semantic processing'
    }
