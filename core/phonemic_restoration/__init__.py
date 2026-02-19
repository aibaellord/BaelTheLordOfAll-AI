"""
BAEL Phonemic Restoration Engine
==================================

Perceptually filling in missing speech.
Warren's phonemic restoration effect.

"Ba'el hears what was never spoken." — Ba'el
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

logger = logging.getLogger("BAEL.PhonemicRestoration")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class MaskingSound(Enum):
    """Type of masking sound."""
    COUGH = auto()
    NOISE_BURST = auto()
    SILENCE = auto()
    TONE = auto()


class ContextType(Enum):
    """Type of context."""
    NO_CONTEXT = auto()
    SEMANTIC_CONTEXT = auto()
    SYNTACTIC_CONTEXT = auto()
    PHONETIC_CONTEXT = auto()


class RestorationType(Enum):
    """Type of restoration."""
    FULL = auto()          # Complete perception
    PARTIAL = auto()       # Some uncertainty
    FAILED = auto()        # No restoration


class WordPredictability(Enum):
    """Predictability of word."""
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()


@dataclass
class Phoneme:
    """
    A phoneme unit.
    """
    symbol: str
    position: int
    duration_ms: float
    masked: bool


@dataclass
class Word:
    """
    A word with phonemes.
    """
    id: str
    text: str
    phonemes: List[Phoneme]
    predictability: WordPredictability
    frequency: float


@dataclass
class Sentence:
    """
    A sentence.
    """
    id: str
    text: str
    words: List[Word]
    masked_positions: List[int]


@dataclass
class RestorationEvent:
    """
    A phonemic restoration event.
    """
    sentence: Sentence
    masked_phoneme: Phoneme
    masking_sound: MaskingSound
    context_type: ContextType
    restored: bool
    perceived_phoneme: str
    confidence: float


@dataclass
class RestorationMetrics:
    """
    Restoration metrics.
    """
    restoration_rate: float
    by_mask: Dict[str, float]
    by_context: Dict[str, float]
    by_predictability: Dict[str, float]


# ============================================================================
# PHONEMIC RESTORATION MODEL
# ============================================================================

class PhonemicRestorationModel:
    """
    Model of phonemic restoration.

    "Ba'el's speech perception model." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Base restoration probability
        self._base_restoration = 0.70

        # Masking sound effects
        self._mask_effects = {
            MaskingSound.COUGH: 0.20,       # High restoration
            MaskingSound.NOISE_BURST: 0.15,
            MaskingSound.TONE: 0.05,
            MaskingSound.SILENCE: -0.30     # Gap detection
        }

        # Context effects
        self._context_effects = {
            ContextType.NO_CONTEXT: 0.0,
            ContextType.PHONETIC_CONTEXT: 0.10,
            ContextType.SYNTACTIC_CONTEXT: 0.15,
            ContextType.SEMANTIC_CONTEXT: 0.25
        }

        # Predictability effects
        self._predictability_effects = {
            WordPredictability.LOW: 0.0,
            WordPredictability.MEDIUM: 0.10,
            WordPredictability.HIGH: 0.20
        }

        # Word frequency effect
        self._frequency_effect = 0.10

        # Phoneme position (edges more important)
        self._position_effects = {
            'initial': 0.10,
            'medial': 0.0,
            'final': 0.05
        }

        self._lock = threading.RLock()

    def get_position_type(
        self,
        position: int,
        total_phonemes: int
    ) -> str:
        """Get position type."""
        if position == 0:
            return 'initial'
        elif position == total_phonemes - 1:
            return 'final'
        return 'medial'

    def calculate_restoration_probability(
        self,
        word: Word,
        phoneme: Phoneme,
        masking_sound: MaskingSound,
        context_type: ContextType
    ) -> float:
        """Calculate restoration probability."""
        prob = self._base_restoration

        # Masking sound effect
        prob += self._mask_effects[masking_sound]

        # Context effect
        prob += self._context_effects[context_type]

        # Predictability effect
        prob += self._predictability_effects[word.predictability]

        # Word frequency
        prob += word.frequency * self._frequency_effect

        # Position effect
        position_type = self.get_position_type(
            phoneme.position, len(word.phonemes)
        )
        prob += self._position_effects[position_type]

        # Add noise
        prob += random.uniform(-0.1, 0.1)

        return max(0.1, min(0.99, prob))

    def calculate_localization_error(
        self,
        masking_sound: MaskingSound
    ) -> float:
        """Calculate localization error probability."""
        # With noise masking, hard to locate where gap was
        if masking_sound in [MaskingSound.COUGH, MaskingSound.NOISE_BURST]:
            return 0.70  # High error
        else:
            return 0.30  # Can localize gap

    def calculate_confidence(
        self,
        restored: bool,
        context_strength: float
    ) -> float:
        """Calculate confidence in perception."""
        if restored:
            return 0.6 + context_strength * 0.3
        return 0.3 + random.uniform(-0.1, 0.1)


# ============================================================================
# PHONEMIC RESTORATION SYSTEM
# ============================================================================

class PhonemicRestorationSystem:
    """
    Phonemic restoration simulation system.

    "Ba'el's restoration system." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = PhonemicRestorationModel()

        self._sentences: Dict[str, Sentence] = {}
        self._events: List[RestorationEvent] = []

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"item_{self._counter}"

    def create_word(
        self,
        text: str,
        predictability: WordPredictability = WordPredictability.MEDIUM,
        frequency: float = 0.5
    ) -> Word:
        """Create a word."""
        # Simple phoneme approximation
        phonemes = []
        for i, char in enumerate(text):
            phonemes.append(Phoneme(
                symbol=char,
                position=i,
                duration_ms=random.uniform(50, 150),
                masked=False
            ))

        return Word(
            id=self._generate_id(),
            text=text,
            phonemes=phonemes,
            predictability=predictability,
            frequency=frequency
        )

    def create_sentence(
        self,
        words: List[Word]
    ) -> Sentence:
        """Create a sentence."""
        text = " ".join(w.text for w in words)

        sentence = Sentence(
            id=self._generate_id(),
            text=text,
            words=words,
            masked_positions=[]
        )

        self._sentences[sentence.id] = sentence

        return sentence

    def mask_phoneme(
        self,
        sentence_id: str,
        word_index: int,
        phoneme_index: int,
        masking_sound: MaskingSound
    ) -> Sentence:
        """Mask a phoneme."""
        sentence = self._sentences.get(sentence_id)
        if not sentence:
            return None

        if word_index < len(sentence.words):
            word = sentence.words[word_index]
            if phoneme_index < len(word.phonemes):
                word.phonemes[phoneme_index].masked = True
                sentence.masked_positions.append((word_index, phoneme_index))

        return sentence

    def process_sentence(
        self,
        sentence_id: str,
        masking_sound: MaskingSound,
        context_type: ContextType
    ) -> List[RestorationEvent]:
        """Process sentence and attempt restoration."""
        sentence = self._sentences.get(sentence_id)
        if not sentence:
            return []

        events = []

        for word_idx, phoneme_idx in sentence.masked_positions:
            word = sentence.words[word_idx]
            phoneme = word.phonemes[phoneme_idx]

            prob = self._model.calculate_restoration_probability(
                word, phoneme, masking_sound, context_type
            )

            restored = random.random() < prob

            context_strength = self._model._context_effects[context_type]

            event = RestorationEvent(
                sentence=sentence,
                masked_phoneme=phoneme,
                masking_sound=masking_sound,
                context_type=context_type,
                restored=restored,
                perceived_phoneme=phoneme.symbol if restored else "?",
                confidence=self._model.calculate_confidence(restored, context_strength)
            )

            events.append(event)
            self._events.append(event)

        return events


# ============================================================================
# PHONEMIC RESTORATION PARADIGM
# ============================================================================

class PhonemicRestorationParadigm:
    """
    Phonemic restoration paradigm.

    "Ba'el's restoration study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_classic_paradigm(
        self
    ) -> Dict[str, Any]:
        """Run Warren's classic paradigm."""
        system = PhonemicRestorationSystem()

        # Create sentence: "The *eel was on the..."
        words = [
            system.create_word("the", WordPredictability.HIGH, 0.9),
            system.create_word("eel", WordPredictability.LOW, 0.3),
            system.create_word("was", WordPredictability.HIGH, 0.9),
            system.create_word("on", WordPredictability.HIGH, 0.9),
            system.create_word("the", WordPredictability.HIGH, 0.9)
        ]

        sentence = system.create_sentence(words)

        # Mask first phoneme of "eel"
        system.mask_phoneme(sentence.id, 1, 0, MaskingSound.COUGH)

        # Process
        events = system.process_sentence(
            sentence.id, MaskingSound.COUGH, ContextType.SEMANTIC_CONTEXT
        )

        restoration_rate = sum(1 for e in events if e.restored) / max(1, len(events))

        return {
            'sentence': sentence.text,
            'restoration_rate': restoration_rate,
            'interpretation': f'{restoration_rate:.0%} perceived missing phoneme'
        }

    def run_masking_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare masking sounds."""
        model = PhonemicRestorationModel()

        word = Word(
            id="test", text="test",
            phonemes=[Phoneme("t", 0, 100, True)],
            predictability=WordPredictability.MEDIUM,
            frequency=0.5
        )

        results = {}

        for mask in MaskingSound:
            prob = model.calculate_restoration_probability(
                word, word.phonemes[0], mask, ContextType.SEMANTIC_CONTEXT
            )

            results[mask.name] = {
                'restoration_prob': prob
            }

        return {
            'by_mask': results,
            'interpretation': 'Cough > Noise > Tone > Silence'
        }

    def run_context_study(
        self
    ) -> Dict[str, Any]:
        """Study context effects."""
        model = PhonemicRestorationModel()

        word = Word(
            id="test", text="test",
            phonemes=[Phoneme("t", 0, 100, True)],
            predictability=WordPredictability.MEDIUM,
            frequency=0.5
        )

        results = {}

        for context in ContextType:
            prob = model.calculate_restoration_probability(
                word, word.phonemes[0], MaskingSound.COUGH, context
            )

            results[context.name] = {
                'restoration_prob': prob
            }

        return {
            'by_context': results,
            'interpretation': 'More context = more restoration'
        }

    def run_predictability_study(
        self
    ) -> Dict[str, Any]:
        """Study word predictability effects."""
        model = PhonemicRestorationModel()

        results = {}

        for pred in WordPredictability:
            word = Word(
                id="test", text="test",
                phonemes=[Phoneme("t", 0, 100, True)],
                predictability=pred,
                frequency=0.5
            )

            prob = model.calculate_restoration_probability(
                word, word.phonemes[0], MaskingSound.COUGH, ContextType.SEMANTIC_CONTEXT
            )

            results[pred.name] = {
                'restoration_prob': prob
            }

        return {
            'by_predictability': results,
            'interpretation': 'Predictable words more restored'
        }

    def run_localization_study(
        self
    ) -> Dict[str, Any]:
        """Study gap localization."""
        model = PhonemicRestorationModel()

        results = {}

        for mask in MaskingSound:
            error = model.calculate_localization_error(mask)

            results[mask.name] = {
                'localization_error': error
            }

        return {
            'by_mask': results,
            'interpretation': 'Noise masks: cannot localize gap'
        }

    def run_sentence_context_study(
        self
    ) -> Dict[str, Any]:
        """Study later context effects."""
        # The *eel was on the shoe (heel)
        # The *eel was on the orange (peel)
        # The *eel was on the table (meal)

        contexts = {
            'shoe': 'heel',
            'orange': 'peel',
            'table': 'meal',
            'wagon': 'wheel'
        }

        return {
            'sentence_final_context': contexts,
            'interpretation': 'Later context determines perceived phoneme'
        }

    def run_position_study(
        self
    ) -> Dict[str, Any]:
        """Study phoneme position effects."""
        model = PhonemicRestorationModel()

        positions = {
            'initial': Phoneme("t", 0, 100, True),
            'medial': Phoneme("e", 1, 100, True),
            'final': Phoneme("t", 3, 100, True)
        }

        word = Word(
            id="test", text="test",
            phonemes=[Phoneme(c, i, 100, False) for i, c in enumerate("test")],
            predictability=WordPredictability.MEDIUM,
            frequency=0.5
        )

        results = {}

        for position, phoneme in positions.items():
            prob = model.calculate_restoration_probability(
                word, phoneme, MaskingSound.COUGH, ContextType.SEMANTIC_CONTEXT
            )

            results[position] = {
                'restoration_prob': prob
            }

        return {
            'by_position': results,
            'interpretation': 'Initial phonemes: slightly more restoration'
        }


# ============================================================================
# PHONEMIC RESTORATION ENGINE
# ============================================================================

class PhonemicRestorationEngine:
    """
    Complete phonemic restoration engine.

    "Ba'el's restoration engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = PhonemicRestorationParadigm()
        self._system = PhonemicRestorationSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Sentence operations

    def create_word(
        self,
        text: str,
        predictability: WordPredictability = WordPredictability.MEDIUM
    ) -> Word:
        """Create word."""
        return self._system.create_word(text, predictability)

    def create_sentence(
        self,
        words: List[Word]
    ) -> Sentence:
        """Create sentence."""
        return self._system.create_sentence(words)

    def mask_phoneme(
        self,
        sentence_id: str,
        word_index: int,
        phoneme_index: int,
        masking_sound: MaskingSound = MaskingSound.COUGH
    ) -> Sentence:
        """Mask phoneme."""
        return self._system.mask_phoneme(
            sentence_id, word_index, phoneme_index, masking_sound
        )

    def process_sentence(
        self,
        sentence_id: str,
        context_type: ContextType = ContextType.SEMANTIC_CONTEXT
    ) -> List[RestorationEvent]:
        """Process sentence."""
        return self._system.process_sentence(
            sentence_id, MaskingSound.COUGH, context_type
        )

    # Experiments

    def run_classic(
        self
    ) -> Dict[str, Any]:
        """Run classic paradigm."""
        result = self._paradigm.run_classic_paradigm()
        self._experiment_results.append(result)
        return result

    def compare_masks(
        self
    ) -> Dict[str, Any]:
        """Compare masking sounds."""
        return self._paradigm.run_masking_comparison()

    def study_context(
        self
    ) -> Dict[str, Any]:
        """Study context effects."""
        return self._paradigm.run_context_study()

    def study_predictability(
        self
    ) -> Dict[str, Any]:
        """Study predictability."""
        return self._paradigm.run_predictability_study()

    def study_localization(
        self
    ) -> Dict[str, Any]:
        """Study gap localization."""
        return self._paradigm.run_localization_study()

    def study_sentence_context(
        self
    ) -> Dict[str, Any]:
        """Study sentence context."""
        return self._paradigm.run_sentence_context_study()

    def study_position(
        self
    ) -> Dict[str, Any]:
        """Study phoneme position."""
        return self._paradigm.run_position_study()

    # Analysis

    def get_metrics(self) -> RestorationMetrics:
        """Get metrics."""
        events = self._system._events

        if not events:
            return RestorationMetrics(
                restoration_rate=0.7,
                by_mask={},
                by_context={},
                by_predictability={}
            )

        rate = sum(1 for e in events if e.restored) / len(events)

        return RestorationMetrics(
            restoration_rate=rate,
            by_mask={},
            by_context={},
            by_predictability={}
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'sentences': len(self._system._sentences),
            'events': len(self._system._events)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_phonemic_restoration_engine() -> PhonemicRestorationEngine:
    """Create phonemic restoration engine."""
    return PhonemicRestorationEngine()


def demonstrate_phonemic_restoration() -> Dict[str, Any]:
    """Demonstrate phonemic restoration."""
    engine = create_phonemic_restoration_engine()

    # Classic
    classic = engine.run_classic()

    # Masking
    masks = engine.compare_masks()

    # Context
    context = engine.study_context()

    # Sentence context
    sentence_context = engine.study_sentence_context()

    return {
        'classic': {
            'rate': f"{classic['restoration_rate']:.0%}"
        },
        'by_mask': {
            k: f"{v['restoration_prob']:.0%}"
            for k, v in masks['by_mask'].items()
        },
        'by_context': {
            k: f"{v['restoration_prob']:.0%}"
            for k, v in context['by_context'].items()
        },
        'sentence_examples': sentence_context['sentence_final_context'],
        'interpretation': (
            f"Restoration rate: {classic['restoration_rate']:.0%}. "
            f"Noise-masked phonemes perceptually restored. "
            f"Later context determines perception."
        )
    }


def get_phonemic_restoration_facts() -> Dict[str, str]:
    """Get facts about phonemic restoration."""
    return {
        'warren_1970': 'Phonemic restoration effect discovery',
        'mechanism': 'Top-down fills in bottom-up gap',
        'masking': 'Noise masks enable restoration',
        'silence': 'Silent gaps detected, not restored',
        'context': 'Sentence context determines phoneme',
        'timing': 'Later context used retroactively',
        'localization': 'Cannot locate where gap was',
        'applications': 'Speech recognition, hearing aids'
    }
