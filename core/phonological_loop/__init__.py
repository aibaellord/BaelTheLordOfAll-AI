"""
BAEL Phonological Loop Engine
==============================

Baddeley's phonological loop component.
Verbal short-term memory system.

"Ba'el echoes in the mind." — Ba'el
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
import copy

logger = logging.getLogger("BAEL.PhonologicalLoop")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ItemType(Enum):
    """Types of verbal items."""
    WORD = auto()
    DIGIT = auto()
    LETTER = auto()
    NONSENSE = auto()
    SENTENCE = auto()


class EncodingMode(Enum):
    """Encoding modality."""
    AUDITORY = auto()      # Spoken input
    VISUAL = auto()         # Written input (requires articulation)
    SUBVOCAL = auto()       # Inner speech


class PhonologicalEffect(Enum):
    """Known phonological effects."""
    WORD_LENGTH = auto()         # Longer words = worse
    PHONOLOGICAL_SIMILARITY = auto()  # Similar sounds = worse
    ARTICULATORY_SUPPRESSION = auto()  # Blocks rehearsal
    IRRELEVANT_SPEECH = auto()   # Disrupts store


@dataclass
class PhonologicalItem:
    """
    An item in the phonological store.
    """
    id: str
    content: str
    syllables: int
    phonemes: List[str]
    duration_ms: int
    entry_time: float
    decay_progress: float = 0.0


@dataclass
class RehearsalCycle:
    """
    A rehearsal cycle.
    """
    items: List[str]
    duration_ms: int
    successful: bool


@dataclass
class SpanTest:
    """
    A span test trial.
    """
    sequence: List[str]
    recalled: List[str]
    correct: bool
    span_length: int


@dataclass
class PhonologicalMetrics:
    """
    Phonological loop metrics.
    """
    store_capacity: float    # Items before decay
    rehearsal_rate: float    # Items per second
    decay_time_ms: int       # Time to full decay
    span: int                # Digit/word span


# ============================================================================
# PHONOLOGICAL STORE
# ============================================================================

class PhonologicalStore:
    """
    The phonological store (passive).

    "Ba'el's echo chamber." — Ba'el
    """

    def __init__(
        self,
        decay_time_ms: int = 2000
    ):
        """Initialize store."""
        self._items: Dict[str, PhonologicalItem] = {}
        self._decay_time = decay_time_ms
        self._item_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._item_counter += 1
        return f"item_{self._item_counter}"

    def add_item(
        self,
        content: str,
        syllables: int = None,
        phonemes: List[str] = None
    ) -> PhonologicalItem:
        """Add item to store."""
        # Estimate syllables if not provided
        if syllables is None:
            syllables = max(1, len(content) // 3)

        # Estimate phonemes if not provided
        if phonemes is None:
            phonemes = list(content.lower())

        # Duration based on syllables (250ms per syllable)
        duration = syllables * 250

        item = PhonologicalItem(
            id=self._generate_id(),
            content=content,
            syllables=syllables,
            phonemes=phonemes,
            duration_ms=duration,
            entry_time=time.time()
        )

        self._items[item.id] = item
        return item

    def get_items(self) -> List[PhonologicalItem]:
        """Get all items in store."""
        return list(self._items.values())

    def apply_decay(
        self,
        elapsed_ms: int
    ) -> List[str]:
        """Apply decay and return lost items."""
        lost = []

        for item_id, item in list(self._items.items()):
            # Calculate decay progress
            item.decay_progress += elapsed_ms / self._decay_time

            if item.decay_progress >= 1.0:
                lost.append(item.content)
                del self._items[item_id]

        return lost

    def refresh_item(
        self,
        item_id: str
    ) -> bool:
        """Refresh item through rehearsal."""
        if item_id in self._items:
            self._items[item_id].decay_progress = 0.0
            self._items[item_id].entry_time = time.time()
            return True
        return False

    def clear(self) -> None:
        """Clear store."""
        self._items.clear()

    @property
    def item_count(self) -> int:
        return len(self._items)


# ============================================================================
# ARTICULATORY REHEARSAL
# ============================================================================

class ArticulatoryProcess:
    """
    Articulatory rehearsal process.

    "Ba'el whispers in silence." — Ba'el
    """

    def __init__(
        self,
        rate_per_second: float = 3.0
    ):
        """Initialize rehearsal process."""
        self._rate = rate_per_second
        self._suppressed = False
        self._lock = threading.RLock()

    def get_rehearsal_time(
        self,
        item: PhonologicalItem
    ) -> int:
        """Get time to rehearse an item (ms)."""
        # Based on articulation duration
        base_time = item.duration_ms
        return int(base_time * 1.2)  # Slightly longer than speaking

    def can_rehearse_sequence(
        self,
        items: List[PhonologicalItem],
        window_ms: int = 2000
    ) -> Tuple[bool, int]:
        """Check if sequence can be rehearsed within window."""
        if self._suppressed:
            return False, 0

        total_time = sum(self.get_rehearsal_time(i) for i in items)
        return total_time <= window_ms, total_time

    def rehearse_cycle(
        self,
        store: PhonologicalStore,
        window_ms: int = 2000
    ) -> RehearsalCycle:
        """Perform one rehearsal cycle."""
        if self._suppressed:
            return RehearsalCycle(
                items=[],
                duration_ms=0,
                successful=False
            )

        items = store.get_items()
        rehearsed = []
        total_time = 0

        for item in items:
            rehearsal_time = self.get_rehearsal_time(item)

            if total_time + rehearsal_time <= window_ms:
                store.refresh_item(item.id)
                rehearsed.append(item.content)
                total_time += rehearsal_time
            else:
                break

        return RehearsalCycle(
            items=rehearsed,
            duration_ms=total_time,
            successful=len(rehearsed) == len(items)
        )

    def set_suppression(
        self,
        suppressed: bool
    ) -> None:
        """Set articulatory suppression state."""
        self._suppressed = suppressed

    def calculate_span(
        self,
        word_lengths: List[int]
    ) -> int:
        """Calculate maximum span given word lengths."""
        # How many items can be rehearsed in 2 seconds?
        time_per_item = sum(word_lengths) * 250 / len(word_lengths)  # Average
        return int(2000 / time_per_item)


# ============================================================================
# PHONOLOGICAL EFFECTS
# ============================================================================

class EffectsSimulator:
    """
    Simulate phonological effects.

    "Ba'el demonstrates memory limits." — Ba'el
    """

    def __init__(self):
        """Initialize simulator."""
        self._lock = threading.RLock()

    def word_length_effect(
        self,
        short_words: List[str],
        long_words: List[str]
    ) -> Dict[str, float]:
        """Simulate word length effect."""
        # Longer words = more time to rehearse = lower span
        short_span = min(7, len(short_words))  # ~7 short words

        avg_long = sum(len(w) for w in long_words) / len(long_words)
        avg_short = sum(len(w) for w in short_words) / len(short_words)

        ratio = avg_short / avg_long
        long_span = int(short_span * ratio)

        return {
            'short_word_span': short_span,
            'long_word_span': long_span,
            'effect_size': short_span - long_span
        }

    def phonological_similarity_effect(
        self,
        similar_items: List[str],
        dissimilar_items: List[str]
    ) -> Dict[str, float]:
        """Simulate phonological similarity effect."""
        # Similar sounding items confuse each other
        similar_accuracy = 0.6 + random.uniform(-0.1, 0.1)
        dissimilar_accuracy = 0.85 + random.uniform(-0.1, 0.1)

        return {
            'similar_accuracy': similar_accuracy,
            'dissimilar_accuracy': dissimilar_accuracy,
            'effect_size': dissimilar_accuracy - similar_accuracy
        }

    def articulatory_suppression_effect(
        self,
        with_suppression: bool = True
    ) -> Dict[str, float]:
        """Simulate articulatory suppression effect."""
        if with_suppression:
            # Rehearsal blocked
            span = 2 + random.randint(0, 1)  # Very reduced
            visual_encoding = 0.3  # Visual items suffer most
        else:
            span = 6 + random.randint(0, 2)
            visual_encoding = 0.85

        return {
            'span': span,
            'visual_encoding_accuracy': visual_encoding,
            'suppression_active': with_suppression
        }

    def irrelevant_speech_effect(
        self,
        with_speech: bool = True
    ) -> Dict[str, float]:
        """Simulate irrelevant speech effect."""
        if with_speech:
            # Irrelevant speech disrupts store
            accuracy = 0.65 + random.uniform(-0.1, 0.1)
        else:
            accuracy = 0.85 + random.uniform(-0.05, 0.05)

        return {
            'accuracy': accuracy,
            'irrelevant_speech_present': with_speech,
            'effect_size': 0.85 - accuracy if with_speech else 0.0
        }


# ============================================================================
# PHONOLOGICAL LOOP ENGINE
# ============================================================================

class PhonologicalLoopEngine:
    """
    Complete phonological loop engine.

    "Ba'el's verbal memory system." — Ba'el
    """

    def __init__(
        self,
        decay_time_ms: int = 2000,
        rehearsal_rate: float = 3.0
    ):
        """Initialize engine."""
        self._store = PhonologicalStore(decay_time_ms)
        self._articulatory = ArticulatoryProcess(rehearsal_rate)
        self._effects = EffectsSimulator()

        self._span_tests: List[SpanTest] = []
        self._rehearsal_history: List[RehearsalCycle] = []

        self._lock = threading.RLock()

    # Basic operations

    def encode(
        self,
        content: str,
        mode: EncodingMode = EncodingMode.AUDITORY
    ) -> PhonologicalItem:
        """Encode item into phonological store."""
        # Visual input requires articulatory recoding
        if mode == EncodingMode.VISUAL:
            if self._articulatory._suppressed:
                # Cannot recode if suppressed
                return None

        syllables = max(1, len(content) // 3)
        return self._store.add_item(content, syllables)

    def encode_sequence(
        self,
        items: List[str],
        mode: EncodingMode = EncodingMode.AUDITORY
    ) -> List[PhonologicalItem]:
        """Encode a sequence of items."""
        encoded = []
        for item in items:
            result = self.encode(item, mode)
            if result:
                encoded.append(result)
        return encoded

    # Rehearsal

    def rehearse(self) -> RehearsalCycle:
        """Perform one rehearsal cycle."""
        cycle = self._articulatory.rehearse_cycle(self._store)
        self._rehearsal_history.append(cycle)
        return cycle

    def maintain(
        self,
        duration_seconds: float = 5.0
    ) -> int:
        """Maintain items through continuous rehearsal."""
        cycles = 0
        elapsed = 0

        while elapsed < duration_seconds:
            cycle = self.rehearse()
            cycles += 1

            # Simulate time passing
            cycle_time = cycle.duration_ms / 1000
            self._store.apply_decay(int(cycle_time * 1000))
            elapsed += cycle_time + 0.1  # Small gap between cycles

        return cycles

    # Span testing

    def digit_span_test(
        self,
        sequence: List[str]
    ) -> SpanTest:
        """Run digit span test."""
        self._store.clear()

        # Encode
        self.encode_sequence(sequence)

        # Allow one rehearsal cycle
        self.rehearse()

        # Recall (simulated)
        items = self._store.get_items()
        recalled = [i.content for i in items]

        # Check order
        correct = recalled == sequence[:len(recalled)]

        test = SpanTest(
            sequence=sequence,
            recalled=recalled,
            correct=correct,
            span_length=len(sequence)
        )

        self._span_tests.append(test)
        return test

    def measure_span(
        self,
        item_pool: List[str] = None
    ) -> int:
        """Measure memory span."""
        if item_pool is None:
            item_pool = ['1', '2', '3', '4', '5', '6', '7', '8', '9']

        span = 0

        for length in range(2, len(item_pool) + 1):
            sequence = item_pool[:length]
            test = self.digit_span_test(sequence)

            if test.correct:
                span = length
            else:
                break

        return span

    # Effects demonstrations

    def demonstrate_word_length(self) -> Dict[str, Any]:
        """Demonstrate word length effect."""
        short = ['cat', 'dog', 'hat', 'pen', 'cup']
        long = ['helicopter', 'university', 'refrigerator', 'encyclopedia', 'administrative']

        return self._effects.word_length_effect(short, long)

    def demonstrate_similarity(self) -> Dict[str, Any]:
        """Demonstrate phonological similarity effect."""
        similar = ['B', 'C', 'D', 'G', 'P', 'T', 'V']  # Rhyming letters
        dissimilar = ['F', 'K', 'L', 'Q', 'R', 'W', 'Y']

        return self._effects.phonological_similarity_effect(similar, dissimilar)

    def demonstrate_suppression(self) -> Dict[str, Any]:
        """Demonstrate articulatory suppression effect."""
        # Without suppression
        no_supp = self._effects.articulatory_suppression_effect(False)

        # With suppression
        with_supp = self._effects.articulatory_suppression_effect(True)

        return {
            'without_suppression': no_supp,
            'with_suppression': with_supp
        }

    def set_suppression(
        self,
        suppressed: bool
    ) -> None:
        """Set articulatory suppression."""
        self._articulatory.set_suppression(suppressed)

    # Metrics

    def get_metrics(self) -> PhonologicalMetrics:
        """Get phonological loop metrics."""
        # Estimate capacity from successful tests
        successful_spans = [
            t.span_length for t in self._span_tests if t.correct
        ]
        max_span = max(successful_spans) if successful_spans else 0

        # Rehearsal rate from history
        if self._rehearsal_history:
            total_items = sum(len(c.items) for c in self._rehearsal_history)
            total_time = sum(c.duration_ms for c in self._rehearsal_history) / 1000
            rate = total_items / total_time if total_time > 0 else 3.0
        else:
            rate = 3.0

        return PhonologicalMetrics(
            store_capacity=max_span,
            rehearsal_rate=rate,
            decay_time_ms=self._store._decay_time,
            span=max_span
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'store_items': self._store.item_count,
            'tests_completed': len(self._span_tests),
            'rehearsal_cycles': len(self._rehearsal_history),
            'suppression_active': self._articulatory._suppressed
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_phonological_loop_engine(
    decay_time_ms: int = 2000
) -> PhonologicalLoopEngine:
    """Create phonological loop engine."""
    return PhonologicalLoopEngine(decay_time_ms=decay_time_ms)


def demonstrate_phonological_loop() -> Dict[str, Any]:
    """Demonstrate phonological loop."""
    engine = create_phonological_loop_engine()

    # Measure basic span
    span = engine.measure_span()

    # Demonstrate effects
    word_length = engine.demonstrate_word_length()
    similarity = engine.demonstrate_similarity()

    return {
        'digit_span': span,
        'word_length_effect': word_length,
        'similarity_effect': similarity,
        'interpretation': (
            f'Span of {span} digits, with word length and '
            f'phonological similarity effects demonstrated'
        )
    }


def get_phonological_loop_facts() -> Dict[str, str]:
    """Get facts about phonological loop."""
    return {
        'baddeley_1974': 'Phonological loop proposed as WM component',
        'components': 'Phonological store + Articulatory rehearsal',
        'decay_time': '~2 seconds without rehearsal',
        'word_length': 'Longer words = smaller span',
        'similarity': 'Similar sounds = more confusion',
        'suppression': 'Saying "the the the" blocks rehearsal',
        'irrelevant_speech': 'Background speech disrupts store',
        'span': 'Typically 5-9 items for digits'
    }
