"""
BAEL False Memory Engine
=========================

DRM paradigm and false memories.
Memory distortion and misinformation.

"Ba'el knows truth from illusion." — Ba'el
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

logger = logging.getLogger("BAEL.FalseMemory")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class MemoryType(Enum):
    """Types of memory responses."""
    TRUE = auto()          # Actually presented
    FALSE = auto()         # Not presented but related
    CORRECT_REJECTION = auto()  # Correctly rejected
    MISS = auto()          # Forgotten true item


class ListType(Enum):
    """Types of DRM lists."""
    SEMANTIC = auto()      # Semantically related
    PHONOLOGICAL = auto()  # Phonologically related
    MIXED = auto()         # Both types


class ConfidenceLevel(Enum):
    """Memory confidence levels."""
    GUESS = 1
    MAYBE = 2
    PROBABLY = 3
    CONFIDENT = 4
    CERTAIN = 5


class MisinformationType(Enum):
    """Types of misinformation."""
    MISLEADING_QUESTION = auto()
    POST_EVENT_INFO = auto()
    SOCIAL_INFLUENCE = auto()
    IMAGINATION = auto()


@dataclass
class WordItem:
    """
    A word item in a list.
    """
    word: str
    presented: bool
    is_critical_lure: bool
    semantic_relatedness: float
    position: Optional[int]


@dataclass
class DRMList:
    """
    A DRM word list.
    """
    id: str
    critical_lure: str
    presented_words: List[WordItem]
    list_type: ListType


@dataclass
class MemoryResponse:
    """
    A memory response.
    """
    word: str
    response: str  # "old" or "new"
    confidence: ConfidenceLevel
    memory_type: MemoryType
    response_time: float


@dataclass
class MisinformationEvent:
    """
    A misinformation event.
    """
    original_item: str
    misleading_item: str
    misinfo_type: MisinformationType
    accepted: bool


@dataclass
class FalseMemoryMetrics:
    """
    False memory metrics.
    """
    hit_rate: float           # Correct "old" to presented
    false_alarm_critical: float  # "Old" to critical lure
    false_alarm_unrelated: float # "Old" to unrelated
    misinformation_effect: float


# ============================================================================
# DRM LIST GENERATOR
# ============================================================================

class DRMListGenerator:
    """
    Generate DRM word lists.

    "Ba'el creates memory traps." — Ba'el
    """

    def __init__(self):
        """Initialize generator."""
        # Pre-built DRM lists (simplified)
        self._drm_norms = {
            'sleep': ['bed', 'rest', 'awake', 'tired', 'dream', 'wake', 'snooze', 'blanket', 'doze', 'slumber', 'nap', 'peace'],
            'sweet': ['sour', 'candy', 'sugar', 'bitter', 'good', 'taste', 'tooth', 'nice', 'honey', 'chocolate', 'heart', 'cake'],
            'cold': ['hot', 'snow', 'warm', 'winter', 'ice', 'wet', 'freeze', 'air', 'shiver', 'chill', 'weather', 'frost'],
            'doctor': ['nurse', 'sick', 'medicine', 'hospital', 'patient', 'health', 'stethoscope', 'surgeon', 'clinic', 'cure'],
            'chair': ['table', 'sit', 'legs', 'seat', 'couch', 'desk', 'rocking', 'leg', 'sitting', 'furniture', 'stool', 'wood']
        }

        self._list_counter = 0
        self._lock = threading.RLock()

    def _generate_list_id(self) -> str:
        self._list_counter += 1
        return f"list_{self._list_counter}"

    def generate_list(
        self,
        critical_lure: str,
        list_length: int = 12
    ) -> DRMList:
        """Generate a DRM list for a critical lure."""
        if critical_lure in self._drm_norms:
            associates = self._drm_norms[critical_lure][:list_length]
        else:
            # Generate pseudo-associates
            associates = [f"{critical_lure}_{i}" for i in range(list_length)]

        presented = []
        for i, word in enumerate(associates):
            relatedness = 1.0 - (i * 0.05)  # Higher ranked = more related

            presented.append(WordItem(
                word=word,
                presented=True,
                is_critical_lure=False,
                semantic_relatedness=relatedness,
                position=i + 1
            ))

        return DRMList(
            id=self._generate_list_id(),
            critical_lure=critical_lure,
            presented_words=presented,
            list_type=ListType.SEMANTIC
        )

    def get_critical_lure_item(
        self,
        drm_list: DRMList
    ) -> WordItem:
        """Get the critical lure as a test item."""
        return WordItem(
            word=drm_list.critical_lure,
            presented=False,
            is_critical_lure=True,
            semantic_relatedness=1.0,  # Maximally related
            position=None
        )

    def get_unrelated_word(
        self,
        exclude: Set[str]
    ) -> WordItem:
        """Get an unrelated distractor word."""
        unrelated = ['lamp', 'window', 'pencil', 'water', 'phone']
        word = random.choice([w for w in unrelated if w not in exclude])

        return WordItem(
            word=word,
            presented=False,
            is_critical_lure=False,
            semantic_relatedness=0.0,
            position=None
        )


# ============================================================================
# MEMORY SIMULATOR
# ============================================================================

class FalseMemorySimulator:
    """
    Simulate memory with false memory effects.

    "Ba'el simulates memory errors." — Ba'el
    """

    def __init__(self):
        """Initialize simulator."""
        self._lock = threading.RLock()

    def simulate_recognition(
        self,
        item: WordItem,
        list_context: DRMList = None
    ) -> MemoryResponse:
        """Simulate recognition response."""
        # Base recognition probability
        if item.presented:
            # True memory
            hit_prob = 0.7 + item.semantic_relatedness * 0.1

            # Position effect (primacy/recency)
            if item.position:
                if item.position <= 3:  # Primacy
                    hit_prob += 0.1
                elif item.position >= 10:  # Recency
                    hit_prob += 0.05

            responds_old = random.random() < hit_prob

            if responds_old:
                memory_type = MemoryType.TRUE
            else:
                memory_type = MemoryType.MISS

        elif item.is_critical_lure:
            # Critical lure - high false alarm rate
            fa_prob = 0.6 + item.semantic_relatedness * 0.2
            responds_old = random.random() < fa_prob

            if responds_old:
                memory_type = MemoryType.FALSE
            else:
                memory_type = MemoryType.CORRECT_REJECTION

        else:
            # Unrelated distractor
            fa_prob = 0.1
            responds_old = random.random() < fa_prob

            if responds_old:
                memory_type = MemoryType.FALSE
            else:
                memory_type = MemoryType.CORRECT_REJECTION

        # Confidence depends on memory strength
        if memory_type in [MemoryType.TRUE, MemoryType.FALSE]:
            if memory_type == MemoryType.TRUE:
                confidence = random.choice([ConfidenceLevel.PROBABLY, ConfidenceLevel.CONFIDENT, ConfidenceLevel.CERTAIN])
            else:
                # False memories often high confidence
                confidence = random.choice([ConfidenceLevel.PROBABLY, ConfidenceLevel.CONFIDENT])
        else:
            confidence = random.choice([ConfidenceLevel.GUESS, ConfidenceLevel.MAYBE, ConfidenceLevel.PROBABLY])

        response_time = 1.0 + random.uniform(-0.3, 0.5)
        if memory_type == MemoryType.FALSE:
            response_time += 0.2  # Slight hesitation

        return MemoryResponse(
            word=item.word,
            response="old" if responds_old else "new",
            confidence=confidence,
            memory_type=memory_type,
            response_time=response_time
        )

    def apply_misinformation(
        self,
        original: str,
        misleading: str,
        misinfo_type: MisinformationType
    ) -> MisinformationEvent:
        """Apply misinformation effect."""
        # Acceptance probability depends on type
        acceptance_probs = {
            MisinformationType.MISLEADING_QUESTION: 0.4,
            MisinformationType.POST_EVENT_INFO: 0.35,
            MisinformationType.SOCIAL_INFLUENCE: 0.45,
            MisinformationType.IMAGINATION: 0.3
        }

        prob = acceptance_probs.get(misinfo_type, 0.3)
        accepted = random.random() < prob

        return MisinformationEvent(
            original_item=original,
            misleading_item=misleading,
            misinfo_type=misinfo_type,
            accepted=accepted
        )


# ============================================================================
# FALSE MEMORY ENGINE
# ============================================================================

class FalseMemoryEngine:
    """
    Complete false memory engine.

    "Ba'el's memory distortion system." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._generator = DRMListGenerator()
        self._simulator = FalseMemorySimulator()

        self._lists: Dict[str, DRMList] = {}
        self._responses: List[MemoryResponse] = []
        self._misinformation: List[MisinformationEvent] = []

        self._lock = threading.RLock()

    # List creation

    def create_drm_list(
        self,
        critical_lure: str,
        list_length: int = 12
    ) -> DRMList:
        """Create a DRM list."""
        drm_list = self._generator.generate_list(critical_lure, list_length)
        self._lists[drm_list.id] = drm_list
        return drm_list

    def get_available_lures(self) -> List[str]:
        """Get available critical lures."""
        return list(self._generator._drm_norms.keys())

    # Testing

    def test_item(
        self,
        item: WordItem,
        list_context: DRMList = None
    ) -> MemoryResponse:
        """Test recognition of an item."""
        response = self._simulator.simulate_recognition(item, list_context)
        self._responses.append(response)
        return response

    def run_recognition_test(
        self,
        drm_list: DRMList,
        include_lure: bool = True,
        include_distractors: int = 3
    ) -> List[MemoryResponse]:
        """Run full recognition test for a list."""
        test_items = []

        # Add presented words
        test_items.extend(drm_list.presented_words)

        # Add critical lure
        if include_lure:
            lure = self._generator.get_critical_lure_item(drm_list)
            test_items.append(lure)

        # Add unrelated distractors
        presented_words = {w.word for w in drm_list.presented_words}
        presented_words.add(drm_list.critical_lure)

        for _ in range(include_distractors):
            distractor = self._generator.get_unrelated_word(presented_words)
            test_items.append(distractor)
            presented_words.add(distractor.word)

        # Shuffle and test
        random.shuffle(test_items)

        results = []
        for item in test_items:
            response = self.test_item(item, drm_list)
            results.append(response)

        return results

    # Misinformation

    def introduce_misinformation(
        self,
        original: str,
        misleading: str,
        misinfo_type: MisinformationType
    ) -> MisinformationEvent:
        """Introduce misinformation about a memory."""
        event = self._simulator.apply_misinformation(
            original, misleading, misinfo_type
        )
        self._misinformation.append(event)
        return event

    def simulate_loftus_experiment(
        self,
        original_event: str,
        misleading_info: str
    ) -> Dict[str, Any]:
        """Simulate Loftus misinformation experiment."""
        # Introduce misinformation
        event = self.introduce_misinformation(
            original_event,
            misleading_info,
            MisinformationType.MISLEADING_QUESTION
        )

        return {
            'original': original_event,
            'misinformation': misleading_info,
            'accepted': event.accepted,
            'interpretation': (
                'Memory was altered by post-event information'
                if event.accepted
                else 'Original memory maintained'
            )
        }

    # Analysis

    def get_drm_results(self) -> Dict[str, float]:
        """Get DRM paradigm results."""
        true_responses = [r for r in self._responses if r.memory_type == MemoryType.TRUE]
        false_lure = [r for r in self._responses if r.memory_type == MemoryType.FALSE]
        miss = [r for r in self._responses if r.memory_type == MemoryType.MISS]
        correct_rej = [r for r in self._responses if r.memory_type == MemoryType.CORRECT_REJECTION]

        total_presented = len(true_responses) + len(miss)
        total_lures = len([r for r in self._responses
                         for item in self._lists.values()
                         if r.word == item.critical_lure])

        hit_rate = len(true_responses) / total_presented if total_presented > 0 else 0.0

        # Find critical lure false alarms
        critical_fa = 0
        unrelated_fa = 0

        for r in self._responses:
            if r.memory_type == MemoryType.FALSE:
                is_critical = any(
                    r.word == lst.critical_lure
                    for lst in self._lists.values()
                )
                if is_critical:
                    critical_fa += 1
                else:
                    unrelated_fa += 1

        return {
            'hit_rate': hit_rate,
            'critical_lure_fa': critical_fa,
            'unrelated_fa': unrelated_fa,
            'correct_rejections': len(correct_rej)
        }

    # Metrics

    def get_metrics(self) -> FalseMemoryMetrics:
        """Get false memory metrics."""
        results = self.get_drm_results()

        # Calculate rates
        all_false = [r for r in self._responses if r.memory_type == MemoryType.FALSE]
        critical_lure_responses = results['critical_lure_fa']

        misinformation_rate = (
            sum(1 for m in self._misinformation if m.accepted) / len(self._misinformation)
            if self._misinformation else 0.0
        )

        return FalseMemoryMetrics(
            hit_rate=results['hit_rate'],
            false_alarm_critical=critical_lure_responses / max(1, len(self._lists)),
            false_alarm_unrelated=results['unrelated_fa'] / max(1, len(all_false)),
            misinformation_effect=misinformation_rate
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'lists': len(self._lists),
            'responses': len(self._responses),
            'misinformation_events': len(self._misinformation)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_false_memory_engine() -> FalseMemoryEngine:
    """Create false memory engine."""
    return FalseMemoryEngine()


def demonstrate_drm_paradigm() -> Dict[str, Any]:
    """Demonstrate DRM false memory paradigm."""
    engine = create_false_memory_engine()

    # Create list with "sleep" as critical lure
    sleep_list = engine.create_drm_list("sleep", list_length=10)

    # Run recognition test
    results = engine.run_recognition_test(
        sleep_list,
        include_lure=True,
        include_distractors=3
    )

    # Analyze
    drm_results = engine.get_drm_results()

    # Find if critical lure was falsely recognized
    lure_responses = [r for r in results if r.word == "sleep"]
    lure_accepted = any(r.response == "old" for r in lure_responses)

    return {
        'critical_lure': 'sleep',
        'presented_words': [w.word for w in sleep_list.presented_words[:5]],
        'hit_rate': drm_results['hit_rate'],
        'lure_falsely_recognized': lure_accepted,
        'interpretation': (
            'Critical lure "sleep" was falsely remembered!'
            if lure_accepted
            else 'Critical lure correctly rejected'
        )
    }


def get_false_memory_facts() -> Dict[str, str]:
    """Get facts about false memory."""
    return {
        'roediger_mcdermott_1995': 'DRM paradigm revival',
        'deese_1959': 'Original semantic association procedure',
        'critical_lure': 'Never-presented word that is falsely remembered',
        'gist_memory': 'False memories from semantic gist extraction',
        'high_confidence': 'False memories can have high confidence',
        'loftus_1974': 'Misinformation effect in eyewitness memory',
        'source_monitoring': 'False memories from source confusion',
        'imagination_inflation': 'Imagining increases false memory'
    }
