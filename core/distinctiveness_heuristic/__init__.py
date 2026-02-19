"""
BAEL Distinctiveness Heuristic Engine
=======================================

Using distinctive features to reject false memories.
Schacter's source monitoring heuristic.

"Ba'el distinguishes truth from illusion." — Ba'el
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

logger = logging.getLogger("BAEL.DistinctivenessHeuristic")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class EncodingFormat(Enum):
    """Format of encoding."""
    WORD_ONLY = auto()
    PICTURE_WORD = auto()     # Pictures with words
    PICTURE_ONLY = auto()
    RICH_ENCODING = auto()    # Multiple modalities


class ItemType(Enum):
    """Type of item in recognition."""
    OLD_STUDIED = auto()
    NEW_LURE = auto()
    RELATED_LURE = auto()     # DRM critical lure


class ResponseType(Enum):
    """Type of recognition response."""
    HIT = auto()              # Old correctly identified
    MISS = auto()             # Old incorrectly rejected
    FALSE_ALARM = auto()      # New incorrectly accepted
    CORRECT_REJECTION = auto()


class HeuristicType(Enum):
    """Type of heuristic."""
    DISTINCTIVENESS = auto()   # "Would remember if seen"
    FAMILIARITY = auto()       # "Seems familiar"
    FLUENCY = auto()           # "Easy to process"


@dataclass
class StudyItem:
    """
    An item studied.
    """
    id: str
    word: str
    format: EncodingFormat
    has_picture: bool
    distinctiveness_level: float
    category: Optional[str]


@dataclass
class TestItem:
    """
    An item at test.
    """
    id: str
    word: str
    item_type: ItemType
    studied_format: Optional[EncodingFormat]
    expected_picture: bool


@dataclass
class RecognitionResponse:
    """
    A recognition response.
    """
    test_item: TestItem
    response: str           # "old" or "new"
    confidence: float
    response_type: ResponseType
    heuristic_used: HeuristicType
    response_time_ms: float


@dataclass
class DistinctivenessMetrics:
    """
    Distinctiveness heuristic metrics.
    """
    hit_rate: float
    false_alarm_rate: float
    false_alarm_reduction: float  # Picture vs word-only
    dprime: float
    heuristic_effectiveness: float


# ============================================================================
# DISTINCTIVENESS HEURISTIC MODEL
# ============================================================================

class DistinctivenessHeuristicModel:
    """
    Model of the distinctiveness heuristic.

    "Ba'el's distinctiveness model." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Base rates
        self._base_hit_rate = 0.75
        self._base_fa_rate = 0.25

        # Picture encoding effects
        self._picture_hit_boost = 0.10
        self._picture_fa_reduction = 0.15  # Key DH effect

        # Heuristic parameters
        self._dh_threshold = 0.6  # "Would remember picture"
        self._dh_effectiveness = 0.7

        # DRM lure effects
        self._drm_lure_familiarity = 0.8
        self._drm_dh_protection = 0.3  # How much DH helps with DRM

        # Distinctiveness levels
        self._distinctiveness_effects = {
            'low': 0.0,
            'medium': 0.10,
            'high': 0.20
        }

        # Age effects (older adults use DH less)
        self._young_adult_dh = 1.0
        self._older_adult_dh = 0.6

        self._lock = threading.RLock()

    def calculate_recollection(
        self,
        item: StudyItem
    ) -> float:
        """Calculate recollection probability."""
        base = 0.5

        # Picture boost
        if item.has_picture:
            base += 0.2

        # Distinctiveness
        base += item.distinctiveness_level * 0.2

        return min(0.95, base)

    def calculate_familiarity(
        self,
        item_type: ItemType,
        is_drm_lure: bool = False
    ) -> float:
        """Calculate familiarity signal."""
        if item_type == ItemType.OLD_STUDIED:
            return 0.7 + random.uniform(-0.1, 0.1)
        elif item_type == ItemType.RELATED_LURE or is_drm_lure:
            return self._drm_lure_familiarity + random.uniform(-0.1, 0.1)
        else:
            return 0.3 + random.uniform(-0.1, 0.1)

    def apply_distinctiveness_heuristic(
        self,
        item: TestItem,
        familiarity: float,
        expect_picture: bool
    ) -> Tuple[bool, float]:
        """Apply distinctiveness heuristic."""
        # If would expect to remember picture but don't...
        if expect_picture and item.item_type != ItemType.OLD_STUDIED:
            # Use heuristic to reject
            heuristic_strength = self._dh_effectiveness
            rejection_prob = heuristic_strength

            if random.random() < rejection_prob:
                return True, 0.3  # Reject with low confidence

        # Otherwise use familiarity
        return False, familiarity

    def calculate_hit_rate(
        self,
        format: EncodingFormat
    ) -> float:
        """Calculate hit rate."""
        rate = self._base_hit_rate

        if format in [EncodingFormat.PICTURE_WORD, EncodingFormat.PICTURE_ONLY]:
            rate += self._picture_hit_boost

        return min(0.95, rate)

    def calculate_false_alarm_rate(
        self,
        studied_format: EncodingFormat,
        lure_type: ItemType
    ) -> float:
        """Calculate false alarm rate."""
        rate = self._base_fa_rate

        # DRM lures have higher FA
        if lure_type == ItemType.RELATED_LURE:
            rate += 0.30

        # Picture encoding reduces FA (distinctiveness heuristic)
        if studied_format in [EncodingFormat.PICTURE_WORD, EncodingFormat.PICTURE_ONLY]:
            rate -= self._picture_fa_reduction

            # Extra protection for DRM
            if lure_type == ItemType.RELATED_LURE:
                rate -= self._drm_dh_protection

        return max(0.05, min(0.70, rate))


# ============================================================================
# DISTINCTIVENESS HEURISTIC SYSTEM
# ============================================================================

class DistinctivenessHeuristicSystem:
    """
    Distinctiveness heuristic simulation system.

    "Ba'el's DH system." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = DistinctivenessHeuristicModel()

        self._study_items: Dict[str, StudyItem] = {}
        self._test_items: Dict[str, TestItem] = {}
        self._responses: List[RecognitionResponse] = []

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"item_{self._counter}"

    def create_study_item(
        self,
        word: str,
        format: EncodingFormat,
        category: Optional[str] = None
    ) -> StudyItem:
        """Create a study item."""
        has_picture = format in [EncodingFormat.PICTURE_WORD, EncodingFormat.PICTURE_ONLY]

        item = StudyItem(
            id=self._generate_id(),
            word=word,
            format=format,
            has_picture=has_picture,
            distinctiveness_level=0.7 if has_picture else 0.3,
            category=category
        )

        self._study_items[item.id] = item

        return item

    def create_test_item(
        self,
        word: str,
        item_type: ItemType,
        studied_format: Optional[EncodingFormat] = None
    ) -> TestItem:
        """Create a test item."""
        expected_picture = (
            studied_format is not None and
            studied_format in [EncodingFormat.PICTURE_WORD, EncodingFormat.PICTURE_ONLY]
        )

        item = TestItem(
            id=self._generate_id(),
            word=word,
            item_type=item_type,
            studied_format=studied_format,
            expected_picture=expected_picture
        )

        self._test_items[item.id] = item

        return item

    def run_recognition(
        self,
        test_item_id: str,
        study_format: EncodingFormat
    ) -> RecognitionResponse:
        """Run recognition test."""
        item = self._test_items.get(test_item_id)
        if not item:
            return None

        # Get familiarity
        familiarity = self._model.calculate_familiarity(item.item_type)

        # Apply distinctiveness heuristic
        expect_picture = study_format in [EncodingFormat.PICTURE_WORD, EncodingFormat.PICTURE_ONLY]
        dh_used, adjusted_signal = self._model.apply_distinctiveness_heuristic(
            item, familiarity, expect_picture
        )

        # Make decision
        threshold = 0.5
        responded_old = adjusted_signal > threshold

        # Determine response type
        if item.item_type == ItemType.OLD_STUDIED:
            if responded_old:
                response_type = ResponseType.HIT
            else:
                response_type = ResponseType.MISS
        else:
            if responded_old:
                response_type = ResponseType.FALSE_ALARM
            else:
                response_type = ResponseType.CORRECT_REJECTION

        response = RecognitionResponse(
            test_item=item,
            response="old" if responded_old else "new",
            confidence=adjusted_signal,
            response_type=response_type,
            heuristic_used=HeuristicType.DISTINCTIVENESS if dh_used else HeuristicType.FAMILIARITY,
            response_time_ms=random.uniform(800, 2000)
        )

        self._responses.append(response)

        return response


# ============================================================================
# DISTINCTIVENESS HEURISTIC PARADIGM
# ============================================================================

class DistinctivenessHeuristicParadigm:
    """
    Distinctiveness heuristic paradigm.

    "Ba'el's DH study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_classic_paradigm(
        self,
        n_items: int = 40
    ) -> Dict[str, Any]:
        """Run classic picture-word paradigm."""
        system = DistinctivenessHeuristicSystem()

        # Study words with pictures
        words = [f"word_{i}" for i in range(n_items)]

        for word in words:
            system.create_study_item(word, EncodingFormat.PICTURE_WORD)

        # Test: old items + new lures
        old_items = words[:n_items // 2]
        new_lures = [f"lure_{i}" for i in range(n_items // 2)]

        responses = []

        for word in old_items:
            test_item = system.create_test_item(word, ItemType.OLD_STUDIED, EncodingFormat.PICTURE_WORD)
            response = system.run_recognition(test_item.id, EncodingFormat.PICTURE_WORD)
            responses.append(response)

        for word in new_lures:
            test_item = system.create_test_item(word, ItemType.NEW_LURE)
            response = system.run_recognition(test_item.id, EncodingFormat.PICTURE_WORD)
            responses.append(response)

        # Calculate rates
        hits = sum(1 for r in responses if r.response_type == ResponseType.HIT)
        fas = sum(1 for r in responses if r.response_type == ResponseType.FALSE_ALARM)
        old_count = len(old_items)
        new_count = len(new_lures)

        hit_rate = hits / max(1, old_count)
        fa_rate = fas / max(1, new_count)

        return {
            'hit_rate': hit_rate,
            'false_alarm_rate': fa_rate,
            'dprime': self._calculate_dprime(hit_rate, fa_rate),
            'interpretation': f'Low FA ({fa_rate:.0%}) due to distinctiveness heuristic'
        }

    def _calculate_dprime(self, hit_rate: float, fa_rate: float) -> float:
        """Calculate d-prime."""
        from math import erfinv

        # Clip to avoid infinite values
        hit_rate = max(0.01, min(0.99, hit_rate))
        fa_rate = max(0.01, min(0.99, fa_rate))

        z_hit = erfinv(2 * hit_rate - 1) * math.sqrt(2)
        z_fa = erfinv(2 * fa_rate - 1) * math.sqrt(2)

        return z_hit - z_fa

    def run_picture_vs_word_study(
        self
    ) -> Dict[str, Any]:
        """Compare picture vs word encoding."""
        model = DistinctivenessHeuristicModel()

        conditions = {
            'picture_word': EncodingFormat.PICTURE_WORD,
            'word_only': EncodingFormat.WORD_ONLY
        }

        results = {}

        for condition, format in conditions.items():
            hit = model.calculate_hit_rate(format)
            fa_new = model.calculate_false_alarm_rate(format, ItemType.NEW_LURE)
            fa_related = model.calculate_false_alarm_rate(format, ItemType.RELATED_LURE)

            results[condition] = {
                'hit_rate': hit,
                'fa_new': fa_new,
                'fa_related': fa_related
            }

        # Calculate DH effect
        fa_reduction = (
            results['word_only']['fa_related'] -
            results['picture_word']['fa_related']
        )

        return {
            'by_condition': results,
            'fa_reduction': fa_reduction,
            'interpretation': f'Pictures reduce FA by {fa_reduction:.0%}'
        }

    def run_drm_study(
        self
    ) -> Dict[str, Any]:
        """Study DRM false memories with pictures."""
        model = DistinctivenessHeuristicModel()

        conditions = {
            'word_only': EncodingFormat.WORD_ONLY,
            'picture_word': EncodingFormat.PICTURE_WORD
        }

        results = {}

        for condition, format in conditions.items():
            # Critical lure FA
            fa = model.calculate_false_alarm_rate(format, ItemType.RELATED_LURE)

            results[condition] = {
                'critical_lure_fa': fa
            }

        protection = (
            results['word_only']['critical_lure_fa'] -
            results['picture_word']['critical_lure_fa']
        )

        return {
            'by_condition': results,
            'protection': protection,
            'interpretation': f'Pictures reduce DRM FA by {protection:.0%}'
        }

    def run_age_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare young vs older adults."""
        model = DistinctivenessHeuristicModel()

        # Older adults use DH less effectively
        conditions = {
            'young_adults': {
                'dh_effectiveness': model._dh_effectiveness
            },
            'older_adults': {
                'dh_effectiveness': model._dh_effectiveness * model._older_adult_dh
            }
        }

        results = {}

        for condition, params in conditions.items():
            base_fa = 0.25

            # FA reduction depends on DH effectiveness
            fa_with_pictures = base_fa * (1 - params['dh_effectiveness'] * 0.4)

            results[condition] = {
                'fa_with_pictures': fa_with_pictures,
                'dh_benefit': base_fa - fa_with_pictures
            }

        return {
            'by_age': results,
            'interpretation': 'Older adults benefit less from pictures'
        }

    def run_warning_study(
        self
    ) -> Dict[str, Any]:
        """Study effect of warning about false memories."""
        conditions = {
            'no_warning': {'boost': 0.0},
            'warning': {'boost': 0.10}  # Warning increases DH use
        }

        results = {}
        base_fa = 0.40  # DRM FA

        for condition, params in conditions.items():
            fa = base_fa * (1 - params['boost'])

            results[condition] = {
                'fa_rate': fa
            }

        return {
            'by_warning': results,
            'interpretation': 'Warning enhances DH use'
        }

    def run_heuristic_mechanism_study(
        self
    ) -> Dict[str, Any]:
        """Study mechanism of distinctiveness heuristic."""
        mechanisms = {
            'absence_of_recollection': (
                "Expecting vivid memory but not having it"
            ),
            'metacognitive_judgment': (
                "Would remember if actually seen"
            ),
            'source_monitoring': (
                "No picture source = not studied"
            )
        }

        return {
            'mechanisms': mechanisms,
            'key_insight': 'DH uses absence of distinctive memory as evidence',
            'interpretation': 'Metacognitive reasoning about memory expectations'
        }


# ============================================================================
# DISTINCTIVENESS HEURISTIC ENGINE
# ============================================================================

class DistinctivenessHeuristicEngine:
    """
    Complete distinctiveness heuristic engine.

    "Ba'el's DH engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = DistinctivenessHeuristicParadigm()
        self._system = DistinctivenessHeuristicSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Trial operations

    def study_item(
        self,
        word: str,
        format: EncodingFormat
    ) -> StudyItem:
        """Study an item."""
        return self._system.create_study_item(word, format)

    def test_item(
        self,
        word: str,
        item_type: ItemType,
        format: EncodingFormat
    ) -> RecognitionResponse:
        """Test an item."""
        test_item = self._system.create_test_item(word, item_type, format)
        return self._system.run_recognition(test_item.id, format)

    # Experiments

    def run_classic(
        self
    ) -> Dict[str, Any]:
        """Run classic paradigm."""
        result = self._paradigm.run_classic_paradigm()
        self._experiment_results.append(result)
        return result

    def compare_formats(
        self
    ) -> Dict[str, Any]:
        """Compare picture vs word."""
        return self._paradigm.run_picture_vs_word_study()

    def study_drm(
        self
    ) -> Dict[str, Any]:
        """Study DRM with pictures."""
        return self._paradigm.run_drm_study()

    def compare_ages(
        self
    ) -> Dict[str, Any]:
        """Compare age groups."""
        return self._paradigm.run_age_comparison()

    def study_warning(
        self
    ) -> Dict[str, Any]:
        """Study warning effects."""
        return self._paradigm.run_warning_study()

    def study_mechanism(
        self
    ) -> Dict[str, Any]:
        """Study mechanism."""
        return self._paradigm.run_heuristic_mechanism_study()

    # Analysis

    def get_metrics(self) -> DistinctivenessMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_classic()

        last = self._experiment_results[-1]

        return DistinctivenessMetrics(
            hit_rate=last['hit_rate'],
            false_alarm_rate=last['false_alarm_rate'],
            false_alarm_reduction=0.15,
            dprime=last['dprime'],
            heuristic_effectiveness=0.7
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'study_items': len(self._system._study_items),
            'test_items': len(self._system._test_items),
            'responses': len(self._system._responses)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_distinctiveness_heuristic_engine() -> DistinctivenessHeuristicEngine:
    """Create distinctiveness heuristic engine."""
    return DistinctivenessHeuristicEngine()


def demonstrate_distinctiveness_heuristic() -> Dict[str, Any]:
    """Demonstrate distinctiveness heuristic."""
    engine = create_distinctiveness_heuristic_engine()

    # Classic
    classic = engine.run_classic()

    # Format comparison
    formats = engine.compare_formats()

    # DRM
    drm = engine.study_drm()

    # Age comparison
    ages = engine.compare_ages()

    return {
        'classic': {
            'hit_rate': f"{classic['hit_rate']:.0%}",
            'fa_rate': f"{classic['false_alarm_rate']:.0%}",
            'dprime': f"{classic['dprime']:.2f}"
        },
        'picture_vs_word': {
            k: f"FA: {v['fa_related']:.0%}"
            for k, v in formats['by_condition'].items()
        },
        'drm_protection': {
            k: f"Critical FA: {v['critical_lure_fa']:.0%}"
            for k, v in drm['by_condition'].items()
        },
        'age_effect': {
            k: f"DH benefit: {v['dh_benefit']:.0%}"
            for k, v in ages['by_age'].items()
        },
        'interpretation': (
            f"FA rate: {classic['false_alarm_rate']:.0%}. "
            f"Pictures protect via distinctiveness heuristic. "
            f"'Would remember picture if really seen.'"
        )
    }


def get_distinctiveness_heuristic_facts() -> Dict[str, str]:
    """Get facts about distinctiveness heuristic."""
    return {
        'schacter_1999': 'Distinctiveness heuristic discovery',
        'mechanism': 'Absence of expected distinctive memory',
        'key_effect': 'Reduces false alarms',
        'drm': 'Protects against DRM false memories',
        'pictures': 'Picture encoding enables DH',
        'older_adults': 'Reduced DH effectiveness with age',
        'warning': 'Instructions can enhance DH use',
        'applications': 'Eyewitness memory, avoiding false memories'
    }
