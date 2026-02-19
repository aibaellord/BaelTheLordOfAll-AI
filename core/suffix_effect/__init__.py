"""
BAEL Suffix Effect Engine
===========================

Recency impairment from auditory suffix.
Crowder & Morton's suffix effect phenomenon.

"Ba'el's recency disrupted." — Ba'el
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

logger = logging.getLogger("BAEL.SuffixEffect")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class PresentationModality(Enum):
    """Modality of list presentation."""
    AUDITORY = auto()
    VISUAL = auto()


class SuffixType(Enum):
    """Type of suffix stimulus."""
    SPEECH = auto()      # "Recall"
    TONE = auto()        # Pure tone
    NOISE = auto()       # White noise
    NONE = auto()        # No suffix


class SuffixSimilarity(Enum):
    """Similarity of suffix to list items."""
    SAME_VOICE = auto()
    DIFFERENT_VOICE = auto()
    DIFFERENT_LANGUAGE = auto()
    NON_SPEECH = auto()


@dataclass
class ListItem:
    """
    An item in the memory list.
    """
    id: str
    content: str
    position: int  # 0-indexed
    modality: PresentationModality


@dataclass
class RecallResult:
    """
    Result of recall attempt.
    """
    position: int
    correct: bool
    response: Optional[str]


@dataclass
class SuffixCondition:
    """
    Suffix condition for experiment.
    """
    suffix_type: SuffixType
    similarity: SuffixSimilarity
    suffix_content: Optional[str]


@dataclass
class SuffixEffectMetrics:
    """
    Suffix effect metrics.
    """
    recency_no_suffix: float
    recency_with_suffix: float
    suffix_effect_magnitude: float
    primacy_effect: float


# ============================================================================
# PRECATEGORICAL ACOUSTIC STORE MODEL
# ============================================================================

class PrecategoricalAcousticStore:
    """
    Crowder & Morton's PAS model.

    "Ba'el's acoustic echo." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # PAS capacity and duration
        self._pas_duration_ms = 2000  # ~2 seconds
        self._pas_capacity = 3  # Final 2-3 items benefit

        # Recency advantage from PAS
        self._pas_recency_boost = 0.25

        # Suffix masking parameters
        self._speech_suffix_mask = 0.8
        self._tone_suffix_mask = 0.2
        self._noise_suffix_mask = 0.1

        # Similarity effects
        self._same_voice_mask = 1.0
        self._different_voice_mask = 0.6
        self._different_language_mask = 0.4

        self._lock = threading.RLock()

    def calculate_pas_availability(
        self,
        position: int,
        list_length: int,
        suffix: SuffixCondition
    ) -> float:
        """Calculate PAS availability for an item."""
        # Only final items in PAS
        distance_from_end = list_length - 1 - position

        if distance_from_end >= self._pas_capacity:
            # Not in PAS
            return 0.0

        # Base PAS strength
        pas_strength = 1.0 - (distance_from_end / self._pas_capacity)

        if suffix.suffix_type == SuffixType.NONE:
            return pas_strength * self._pas_recency_boost

        # Suffix masks PAS
        if suffix.suffix_type == SuffixType.SPEECH:
            mask = self._speech_suffix_mask

            # Similarity modulates masking
            if suffix.similarity == SuffixSimilarity.SAME_VOICE:
                mask *= self._same_voice_mask
            elif suffix.similarity == SuffixSimilarity.DIFFERENT_VOICE:
                mask *= self._different_voice_mask
            elif suffix.similarity == SuffixSimilarity.DIFFERENT_LANGUAGE:
                mask *= self._different_language_mask
        elif suffix.suffix_type == SuffixType.TONE:
            mask = self._tone_suffix_mask
        else:
            mask = self._noise_suffix_mask

        remaining = pas_strength * (1 - mask) * self._pas_recency_boost

        return remaining

    def calculate_recall_probability(
        self,
        position: int,
        list_length: int,
        modality: PresentationModality,
        suffix: SuffixCondition
    ) -> float:
        """Calculate recall probability."""
        # Serial position curve baseline
        # Primacy
        if position < 3:
            primacy = 0.15 * (1 - position / 3)
        else:
            primacy = 0

        # Asymptote
        asymptote = 0.4

        # Recency - different for modalities
        if modality == PresentationModality.AUDITORY:
            pas_contribution = self.calculate_pas_availability(
                position, list_length, suffix
            )
        else:
            # Visual presentation - minimal modality effect
            pas_contribution = 0.05 if (list_length - 1 - position) < 2 else 0

        prob = asymptote + primacy + pas_contribution

        return min(0.95, max(0.1, prob))


# ============================================================================
# SUFFIX EFFECT SYSTEM
# ============================================================================

class SuffixEffectSystem:
    """
    Suffix effect experimental system.

    "Ba'el's recency masking." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = PrecategoricalAcousticStore()

        self._items: List[ListItem] = []
        self._recalls: List[RecallResult] = []

        self._item_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._item_counter += 1
        return f"item_{self._item_counter}"

    def present_list(
        self,
        items: List[str],
        modality: PresentationModality = PresentationModality.AUDITORY
    ) -> List[ListItem]:
        """Present a list of items."""
        self._items = []

        for i, content in enumerate(items):
            item = ListItem(
                id=self._generate_id(),
                content=content,
                position=i,
                modality=modality
            )
            self._items.append(item)

        return self._items

    def recall(
        self,
        suffix: SuffixCondition
    ) -> List[RecallResult]:
        """Test recall with suffix condition."""
        results = []
        list_length = len(self._items)

        for item in self._items:
            prob = self._model.calculate_recall_probability(
                item.position,
                list_length,
                item.modality,
                suffix
            )

            correct = random.random() < prob

            result = RecallResult(
                position=item.position,
                correct=correct,
                response=item.content if correct else None
            )
            results.append(result)

        self._recalls = results
        return results


# ============================================================================
# SUFFIX PARADIGM
# ============================================================================

class SuffixEffectParadigm:
    """
    Suffix effect experimental paradigm.

    "Ba'el's suffix study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_basic_suffix_experiment(
        self,
        list_length: int = 9
    ) -> Dict[str, Any]:
        """Run basic suffix effect experiment."""
        digits = [str(i) for i in range(1, list_length + 1)]

        # No suffix condition
        system = SuffixEffectSystem()
        system.present_list(digits, PresentationModality.AUDITORY)

        no_suffix_results = system.recall(SuffixCondition(
            suffix_type=SuffixType.NONE,
            similarity=SuffixSimilarity.SAME_VOICE,
            suffix_content=None
        ))

        # Speech suffix condition
        system = SuffixEffectSystem()
        system.present_list(digits, PresentationModality.AUDITORY)

        suffix_results = system.recall(SuffixCondition(
            suffix_type=SuffixType.SPEECH,
            similarity=SuffixSimilarity.SAME_VOICE,
            suffix_content="Recall"
        ))

        # Calculate recency (last 2 positions)
        no_suffix_recency = sum(1 for r in no_suffix_results[-2:] if r.correct) / 2
        suffix_recency = sum(1 for r in suffix_results[-2:] if r.correct) / 2

        # Primacy (first 2 positions)
        no_suffix_primacy = sum(1 for r in no_suffix_results[:2] if r.correct) / 2
        suffix_primacy = sum(1 for r in suffix_results[:2] if r.correct) / 2

        return {
            'list_length': list_length,
            'no_suffix_recency': no_suffix_recency,
            'suffix_recency': suffix_recency,
            'suffix_effect': no_suffix_recency - suffix_recency,
            'no_suffix_primacy': no_suffix_primacy,
            'suffix_primacy': suffix_primacy,
            'primacy_unaffected': abs(no_suffix_primacy - suffix_primacy) < 0.1
        }

    def run_suffix_type_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare different suffix types."""
        digits = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
        results = {}

        for suffix_type in SuffixType:
            system = SuffixEffectSystem()
            system.present_list(digits, PresentationModality.AUDITORY)

            recall_results = system.recall(SuffixCondition(
                suffix_type=suffix_type,
                similarity=SuffixSimilarity.SAME_VOICE,
                suffix_content="Recall" if suffix_type == SuffixType.SPEECH else None
            ))

            recency = sum(1 for r in recall_results[-2:] if r.correct) / 2

            results[suffix_type.name] = recency

        return results

    def run_similarity_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare suffix similarity effects."""
        digits = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
        results = {}

        for similarity in SuffixSimilarity:
            system = SuffixEffectSystem()
            system.present_list(digits, PresentationModality.AUDITORY)

            recall_results = system.recall(SuffixCondition(
                suffix_type=SuffixType.SPEECH,
                similarity=similarity,
                suffix_content="Recall"
            ))

            recency = sum(1 for r in recall_results[-2:] if r.correct) / 2

            results[similarity.name] = recency

        return results

    def run_modality_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare auditory vs visual presentation."""
        digits = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]

        # Auditory no suffix
        system = SuffixEffectSystem()
        system.present_list(digits, PresentationModality.AUDITORY)
        aud_no_suffix = system.recall(SuffixCondition(
            suffix_type=SuffixType.NONE,
            similarity=SuffixSimilarity.SAME_VOICE,
            suffix_content=None
        ))

        # Visual no suffix
        system = SuffixEffectSystem()
        system.present_list(digits, PresentationModality.VISUAL)
        vis_no_suffix = system.recall(SuffixCondition(
            suffix_type=SuffixType.NONE,
            similarity=SuffixSimilarity.SAME_VOICE,
            suffix_content=None
        ))

        # Auditory with suffix
        system = SuffixEffectSystem()
        system.present_list(digits, PresentationModality.AUDITORY)
        aud_suffix = system.recall(SuffixCondition(
            suffix_type=SuffixType.SPEECH,
            similarity=SuffixSimilarity.SAME_VOICE,
            suffix_content="Recall"
        ))

        return {
            'auditory_no_suffix_recency': sum(1 for r in aud_no_suffix[-2:] if r.correct) / 2,
            'visual_no_suffix_recency': sum(1 for r in vis_no_suffix[-2:] if r.correct) / 2,
            'auditory_suffix_recency': sum(1 for r in aud_suffix[-2:] if r.correct) / 2,
            'modality_effect': 'Larger recency for auditory - PAS advantage',
            'suffix_specificity': 'Suffix primarily affects auditory recency'
        }

    def get_serial_position_curve(
        self,
        suffix_type: SuffixType = SuffixType.NONE
    ) -> Dict[int, float]:
        """Get full serial position curve."""
        digits = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]

        # Multiple trials for stability
        position_correct = defaultdict(int)
        n_trials = 10

        for _ in range(n_trials):
            system = SuffixEffectSystem()
            system.present_list(digits, PresentationModality.AUDITORY)

            results = system.recall(SuffixCondition(
                suffix_type=suffix_type,
                similarity=SuffixSimilarity.SAME_VOICE,
                suffix_content="Recall" if suffix_type == SuffixType.SPEECH else None
            ))

            for r in results:
                if r.correct:
                    position_correct[r.position] += 1

        curve = {
            pos: count / n_trials
            for pos, count in position_correct.items()
        }

        return dict(sorted(curve.items()))


# ============================================================================
# SUFFIX EFFECT ENGINE
# ============================================================================

class SuffixEffectEngine:
    """
    Complete suffix effect engine.

    "Ba'el's recency masking engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = SuffixEffectParadigm()
        self._system = SuffixEffectSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # List presentation

    def present_list(
        self,
        items: List[str],
        modality: PresentationModality = PresentationModality.AUDITORY
    ) -> List[ListItem]:
        """Present a list."""
        return self._system.present_list(items, modality)

    # Recall

    def recall(
        self,
        suffix: SuffixCondition
    ) -> List[RecallResult]:
        """Test recall."""
        return self._system.recall(suffix)

    # Experiments

    def run_basic_experiment(
        self,
        list_length: int = 9
    ) -> Dict[str, Any]:
        """Run basic experiment."""
        result = self._paradigm.run_basic_suffix_experiment(list_length)
        self._experiment_results.append(result)
        return result

    def compare_suffix_types(
        self
    ) -> Dict[str, Any]:
        """Compare suffix types."""
        return self._paradigm.run_suffix_type_comparison()

    def compare_similarity(
        self
    ) -> Dict[str, Any]:
        """Compare similarity effects."""
        return self._paradigm.run_similarity_comparison()

    def compare_modalities(
        self
    ) -> Dict[str, Any]:
        """Compare modalities."""
        return self._paradigm.run_modality_comparison()

    def get_serial_position_curve(
        self,
        with_suffix: bool = False
    ) -> Dict[int, float]:
        """Get serial position curve."""
        suffix = SuffixType.SPEECH if with_suffix else SuffixType.NONE
        return self._paradigm.get_serial_position_curve(suffix)

    def run_lip_read_suffix_test(
        self
    ) -> Dict[str, Any]:
        """Test lip-read suffix (visual suffix can affect auditory list)."""
        # This demonstrates PAS is not purely acoustic
        system = SuffixEffectSystem()
        digits = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
        system.present_list(digits, PresentationModality.AUDITORY)

        # Simulating lip-read suffix (treated as partial speech)
        results = system.recall(SuffixCondition(
            suffix_type=SuffixType.SPEECH,
            similarity=SuffixSimilarity.DIFFERENT_VOICE,  # Less effect
            suffix_content="Recall"
        ))

        recency = sum(1 for r in results[-2:] if r.correct) / 2

        return {
            'lip_read_suffix_recency': recency,
            'interpretation': 'Even visual speech (lip-reading) can produce suffix effect'
        }

    # Analysis

    def get_metrics(self) -> SuffixEffectMetrics:
        """Get suffix effect metrics."""
        if not self._experiment_results:
            self.run_basic_experiment()

        last = self._experiment_results[-1]

        return SuffixEffectMetrics(
            recency_no_suffix=last['no_suffix_recency'],
            recency_with_suffix=last['suffix_recency'],
            suffix_effect_magnitude=last['suffix_effect'],
            primacy_effect=last['no_suffix_primacy']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'items': len(self._system._items),
            'experiments': len(self._experiment_results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_suffix_effect_engine() -> SuffixEffectEngine:
    """Create suffix effect engine."""
    return SuffixEffectEngine()


def demonstrate_suffix_effect() -> Dict[str, Any]:
    """Demonstrate suffix effect."""
    engine = create_suffix_effect_engine()

    # Basic experiment
    basic = engine.run_basic_experiment(9)

    # Suffix type comparison
    suffix_types = engine.compare_suffix_types()

    # Similarity comparison
    similarity = engine.compare_similarity()

    # Modality comparison
    modality = engine.compare_modalities()

    # Serial position curves
    curve_no_suffix = engine.get_serial_position_curve(False)
    curve_suffix = engine.get_serial_position_curve(True)

    return {
        'suffix_effect': {
            'no_suffix_recency': f"{basic['no_suffix_recency']:.0%}",
            'with_suffix_recency': f"{basic['suffix_recency']:.0%}",
            'effect': f"{basic['suffix_effect']:.0%}",
            'primacy_unaffected': basic['primacy_unaffected']
        },
        'suffix_type': {
            stype: f"{rec:.0%}"
            for stype, rec in suffix_types.items()
        },
        'similarity': {
            sim: f"{rec:.0%}"
            for sim, rec in similarity.items()
        },
        'modality': {
            'auditory_advantage': f"{modality['auditory_no_suffix_recency']:.0%}",
            'visual_recency': f"{modality['visual_no_suffix_recency']:.0%}"
        },
        'interpretation': (
            f"Suffix effect: {basic['suffix_effect']:.0%}. "
            f"Speech suffix selectively impairs recency in auditory presentation."
        )
    }


def get_suffix_effect_facts() -> Dict[str, str]:
    """Get facts about suffix effect."""
    return {
        'crowder_morton_1969': 'PAS model and suffix effect discovery',
        'pas': 'Precategorical Acoustic Store - brief sensory memory',
        'selective': 'Suffix affects recency, not primacy',
        'speech_specific': 'Speech suffix more disruptive than tones',
        'similarity': 'More similar suffix = larger effect',
        'modality_effect': 'Larger recency for auditory presentation',
        'duration': 'PAS lasts approximately 2 seconds',
        'alternatives': 'Later accounts emphasize perceptual grouping'
    }
