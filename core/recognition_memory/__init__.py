"""
BAEL Recognition Memory Engine
================================

Signal detection and recognition.
Recollection and familiarity.

"Ba'el knows what was seen." — Ba'el
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

logger = logging.getLogger("BAEL.RecognitionMemory")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ItemStatus(Enum):
    """True status of item."""
    OLD = auto()       # Previously studied
    NEW = auto()       # Not studied


class Response(Enum):
    """Recognition response."""
    YES = auto()       # "Old" response
    NO = auto()        # "New" response


class SignalType(Enum):
    """Signal detection outcomes."""
    HIT = auto()           # Old item, "old" response
    MISS = auto()          # Old item, "new" response
    FALSE_ALARM = auto()   # New item, "old" response
    CORRECT_REJECTION = auto()  # New item, "new" response


class RecognitionBasis(Enum):
    """Basis for recognition (dual-process)."""
    RECOLLECTION = auto()  # Episodic details
    FAMILIARITY = auto()   # Feeling of knowing
    GUESS = auto()         # Random


class ConfidenceLevel(Enum):
    """Confidence levels for ROC."""
    HIGH_NEW = 1
    MEDIUM_NEW = 2
    LOW_NEW = 3
    LOW_OLD = 4
    MEDIUM_OLD = 5
    HIGH_OLD = 6


@dataclass
class StudyItem:
    """
    An item at study.
    """
    id: str
    content: Any
    context: Dict[str, Any]
    encoding_strength: float


@dataclass
class TestItem:
    """
    An item at test.
    """
    id: str
    content: Any
    status: ItemStatus
    matched_study: Optional[str] = None


@dataclass
class RecognitionResponse:
    """
    A recognition response.
    """
    item_id: str
    response: Response
    confidence: ConfidenceLevel
    basis: RecognitionBasis
    signal_type: SignalType
    response_time: float


@dataclass
class SDTMetrics:
    """
    Signal detection theory metrics.
    """
    hit_rate: float
    false_alarm_rate: float
    d_prime: float
    criterion: float
    accuracy: float


@dataclass
class DualProcessMetrics:
    """
    Dual-process metrics.
    """
    recollection: float     # R parameter
    familiarity: float      # F (or d') parameter
    recollection_rate: float
    familiarity_rate: float


# ============================================================================
# SIGNAL DETECTION
# ============================================================================

class SignalDetectionAnalyzer:
    """
    Signal detection theory analysis.

    "Ba'el separates signal from noise." — Ba'el
    """

    def __init__(self):
        """Initialize analyzer."""
        self._lock = threading.RLock()

    def classify_response(
        self,
        item_status: ItemStatus,
        response: Response
    ) -> SignalType:
        """Classify response into SDT category."""
        if item_status == ItemStatus.OLD:
            if response == Response.YES:
                return SignalType.HIT
            else:
                return SignalType.MISS
        else:
            if response == Response.YES:
                return SignalType.FALSE_ALARM
            else:
                return SignalType.CORRECT_REJECTION

    def calculate_d_prime(
        self,
        hit_rate: float,
        false_alarm_rate: float
    ) -> float:
        """Calculate d' (sensitivity)."""
        # Avoid extreme values
        hr = max(0.01, min(0.99, hit_rate))
        far = max(0.01, min(0.99, false_alarm_rate))

        # Z-transform
        z_hr = self._z_score(hr)
        z_far = self._z_score(far)

        return z_hr - z_far

    def calculate_criterion(
        self,
        hit_rate: float,
        false_alarm_rate: float
    ) -> float:
        """Calculate c (criterion/bias)."""
        hr = max(0.01, min(0.99, hit_rate))
        far = max(0.01, min(0.99, false_alarm_rate))

        z_hr = self._z_score(hr)
        z_far = self._z_score(far)

        return -0.5 * (z_hr + z_far)

    def _z_score(
        self,
        p: float
    ) -> float:
        """Convert probability to z-score (approximation)."""
        # Approximation of inverse normal CDF
        if p <= 0:
            return -3.0
        if p >= 1:
            return 3.0

        # Simple approximation
        if p == 0.5:
            return 0.0

        sign = 1 if p > 0.5 else -1
        p_adj = p if p > 0.5 else 1 - p

        # Rough approximation
        t = math.sqrt(-2 * math.log(1 - p_adj))
        z = t - (2.515517 + 0.802853 * t + 0.010328 * t * t) / \
            (1 + 1.432788 * t + 0.189269 * t * t + 0.001308 * t * t * t)

        return sign * z

    def generate_roc_points(
        self,
        responses: List[RecognitionResponse]
    ) -> List[Tuple[float, float]]:
        """Generate ROC curve points."""
        points = []

        # Sort by confidence
        sorted_responses = sorted(
            responses,
            key=lambda r: r.confidence.value,
            reverse=True
        )

        # Cumulative hits and FAs at each threshold
        total_old = sum(1 for r in sorted_responses if r.signal_type in [SignalType.HIT, SignalType.MISS])
        total_new = sum(1 for r in sorted_responses if r.signal_type in [SignalType.FALSE_ALARM, SignalType.CORRECT_REJECTION])

        cum_hits = 0
        cum_fa = 0

        for response in sorted_responses:
            if response.signal_type == SignalType.HIT:
                cum_hits += 1
            elif response.signal_type == SignalType.FALSE_ALARM:
                cum_fa += 1

            hr = cum_hits / total_old if total_old > 0 else 0
            far = cum_fa / total_new if total_new > 0 else 0
            points.append((far, hr))

        return points


# ============================================================================
# DUAL PROCESS MODEL
# ============================================================================

class DualProcessModel:
    """
    Dual-process recognition model.

    "Ba'el knows through recollection and familiarity." — Ba'el
    """

    def __init__(
        self,
        recollection: float = 0.3,
        familiarity: float = 0.5
    ):
        """Initialize model."""
        self._R = recollection
        self._F = familiarity
        self._lock = threading.RLock()

    def simulate_recognition(
        self,
        item: TestItem,
        study_items: Dict[str, StudyItem]
    ) -> Tuple[Response, RecognitionBasis]:
        """Simulate recognition decision."""
        if item.status == ItemStatus.OLD:
            # Old item
            study_item = study_items.get(item.matched_study)

            if study_item:
                # Recollection attempt
                recollection_success = random.random() < self._R * study_item.encoding_strength

                if recollection_success:
                    return Response.YES, RecognitionBasis.RECOLLECTION

                # Familiarity
                familiarity_signal = self._F + random.gauss(0, 0.2)
                if familiarity_signal > 0.5:
                    return Response.YES, RecognitionBasis.FAMILIARITY
                else:
                    return Response.NO, RecognitionBasis.GUESS

        else:
            # New item
            # No recollection (by definition)
            # Familiarity can produce false alarms
            familiarity_signal = random.gauss(0, 0.3)

            if familiarity_signal > 0.3:  # Criterion
                return Response.YES, RecognitionBasis.FAMILIARITY
            else:
                return Response.NO, RecognitionBasis.FAMILIARITY

        return Response.NO, RecognitionBasis.GUESS

    def fit_remember_know(
        self,
        responses: List[RecognitionResponse]
    ) -> DualProcessMetrics:
        """Fit model to Remember/Know data."""
        hits = [r for r in responses if r.signal_type == SignalType.HIT]
        fas = [r for r in responses if r.signal_type == SignalType.FALSE_ALARM]

        # Remember = recollection
        remember_hits = sum(1 for r in hits if r.basis == RecognitionBasis.RECOLLECTION)
        know_hits = sum(1 for r in hits if r.basis == RecognitionBasis.FAMILIARITY)

        total_old = len(hits) + len([r for r in responses if r.signal_type == SignalType.MISS])

        R = remember_hits / total_old if total_old > 0 else 0

        # F = Know / (1 - R)
        if R < 1:
            F = (know_hits / total_old) / (1 - R) if total_old > 0 else 0
        else:
            F = 0

        return DualProcessMetrics(
            recollection=R,
            familiarity=F,
            recollection_rate=remember_hits / len(hits) if hits else 0,
            familiarity_rate=know_hits / len(hits) if hits else 0
        )


# ============================================================================
# RECOGNITION MEMORY ENGINE
# ============================================================================

class RecognitionMemoryEngine:
    """
    Complete recognition memory engine.

    "Ba'el's recognition system." — Ba'el
    """

    def __init__(
        self,
        recollection: float = 0.3,
        familiarity: float = 0.5
    ):
        """Initialize engine."""
        self._sdt = SignalDetectionAnalyzer()
        self._dual_process = DualProcessModel(recollection, familiarity)

        self._study_items: Dict[str, StudyItem] = {}
        self._test_items: Dict[str, TestItem] = {}
        self._responses: List[RecognitionResponse] = []

        self._item_counter = 0

        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._item_counter += 1
        return f"item_{self._item_counter}"

    # Study phase

    def study_item(
        self,
        content: Any,
        context: Dict[str, Any] = None,
        strength: float = 0.7
    ) -> StudyItem:
        """Study an item."""
        item = StudyItem(
            id=self._generate_id(),
            content=content,
            context=context or {},
            encoding_strength=strength
        )

        self._study_items[item.id] = item
        return item

    def study_list(
        self,
        contents: List[Any]
    ) -> List[StudyItem]:
        """Study a list of items."""
        items = []
        for content in contents:
            # Serial position effects
            position = len(items)
            if position < 3:  # Primacy
                strength = 0.8
            elif position >= len(contents) - 3:  # Recency
                strength = 0.75
            else:
                strength = 0.6

            item = self.study_item(content, strength=strength)
            items.append(item)

        return items

    # Test phase

    def create_test_item(
        self,
        content: Any,
        status: ItemStatus,
        matched_study_id: str = None
    ) -> TestItem:
        """Create a test item."""
        item = TestItem(
            id=self._generate_id(),
            content=content,
            status=status,
            matched_study=matched_study_id
        )

        self._test_items[item.id] = item
        return item

    def recognize(
        self,
        item: TestItem
    ) -> RecognitionResponse:
        """Make recognition judgment."""
        response, basis = self._dual_process.simulate_recognition(
            item, self._study_items
        )

        signal_type = self._sdt.classify_response(item.status, response)

        # Confidence based on basis
        if basis == RecognitionBasis.RECOLLECTION:
            confidence = ConfidenceLevel.HIGH_OLD
        elif basis == RecognitionBasis.FAMILIARITY:
            confidence = ConfidenceLevel.MEDIUM_OLD if response == Response.YES else ConfidenceLevel.MEDIUM_NEW
        else:
            confidence = ConfidenceLevel.LOW_OLD if response == Response.YES else ConfidenceLevel.LOW_NEW

        # Response time
        base_rt = 1.0
        if basis == RecognitionBasis.RECOLLECTION:
            rt = base_rt - 0.2  # Faster
        else:
            rt = base_rt + random.uniform(-0.2, 0.3)

        result = RecognitionResponse(
            item_id=item.id,
            response=response,
            confidence=confidence,
            basis=basis,
            signal_type=signal_type,
            response_time=max(0.3, rt)
        )

        self._responses.append(result)
        return result

    def run_recognition_test(
        self,
        old_items: List[str] = None,
        new_items: List[Any] = None,
        n_new: int = None
    ) -> List[RecognitionResponse]:
        """Run full recognition test."""
        test_items = []

        # Add old items
        if old_items is None:
            old_items = list(self._study_items.keys())

        for study_id in old_items:
            study_item = self._study_items.get(study_id)
            if study_item:
                test = self.create_test_item(
                    study_item.content,
                    ItemStatus.OLD,
                    study_id
                )
                test_items.append(test)

        # Add new items
        if new_items is None:
            n_new = n_new or len(old_items)
            new_items = [f"new_lure_{i}" for i in range(n_new)]

        for content in new_items:
            test = self.create_test_item(content, ItemStatus.NEW)
            test_items.append(test)

        # Shuffle
        random.shuffle(test_items)

        # Test
        results = []
        for item in test_items:
            response = self.recognize(item)
            results.append(response)

        return results

    # Analysis

    def get_sdt_metrics(self) -> SDTMetrics:
        """Get SDT metrics."""
        hits = sum(1 for r in self._responses if r.signal_type == SignalType.HIT)
        misses = sum(1 for r in self._responses if r.signal_type == SignalType.MISS)
        fas = sum(1 for r in self._responses if r.signal_type == SignalType.FALSE_ALARM)
        crs = sum(1 for r in self._responses if r.signal_type == SignalType.CORRECT_REJECTION)

        total_old = hits + misses
        total_new = fas + crs

        hit_rate = hits / total_old if total_old > 0 else 0.5
        fa_rate = fas / total_new if total_new > 0 else 0.5

        d_prime = self._sdt.calculate_d_prime(hit_rate, fa_rate)
        criterion = self._sdt.calculate_criterion(hit_rate, fa_rate)

        accuracy = (hits + crs) / (total_old + total_new) if (total_old + total_new) > 0 else 0.5

        return SDTMetrics(
            hit_rate=hit_rate,
            false_alarm_rate=fa_rate,
            d_prime=d_prime,
            criterion=criterion,
            accuracy=accuracy
        )

    def get_dual_process_metrics(self) -> DualProcessMetrics:
        """Get dual-process metrics."""
        return self._dual_process.fit_remember_know(self._responses)

    def get_roc_curve(self) -> List[Tuple[float, float]]:
        """Get ROC curve."""
        return self._sdt.generate_roc_points(self._responses)

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'study_items': len(self._study_items),
            'test_items': len(self._test_items),
            'responses': len(self._responses)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_recognition_memory_engine(
    recollection: float = 0.3,
    familiarity: float = 0.5
) -> RecognitionMemoryEngine:
    """Create recognition memory engine."""
    return RecognitionMemoryEngine(recollection, familiarity)


def demonstrate_recognition_memory() -> Dict[str, Any]:
    """Demonstrate recognition memory."""
    engine = create_recognition_memory_engine()

    # Study phase
    study_items = engine.study_list(
        [f"word_{i}" for i in range(20)]
    )

    # Test phase
    results = engine.run_recognition_test(n_new=20)

    # Analysis
    sdt = engine.get_sdt_metrics()
    dual = engine.get_dual_process_metrics()

    return {
        'studied': 20,
        'tested': len(results),
        'hit_rate': sdt.hit_rate,
        'false_alarm_rate': sdt.false_alarm_rate,
        'd_prime': sdt.d_prime,
        'criterion': sdt.criterion,
        'recollection': dual.recollection,
        'familiarity': dual.familiarity,
        'interpretation': f"d' = {sdt.d_prime:.2f}, R = {dual.recollection:.2f}"
    }


def get_recognition_memory_facts() -> Dict[str, str]:
    """Get facts about recognition memory."""
    return {
        'sdt': 'Signal detection theory separates sensitivity from bias',
        'd_prime': 'Measure of discriminability between old and new',
        'criterion': 'Response bias (liberal vs conservative)',
        'dual_process': 'Yonelinas: Recollection + Familiarity',
        'remember_know': 'Tulving: R = recollection, K = familiarity',
        'roc': 'Receiver operating characteristic curves',
        'old_new': 'Standard recognition paradigm',
        'source_memory': 'Remembering context is recollection-based'
    }
