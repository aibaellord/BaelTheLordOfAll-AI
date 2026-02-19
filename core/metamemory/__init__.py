"""
BAEL Metamemory Engine
=========================

Monitoring and control of memory.
Judgments of learning and feeling of knowing.

"Ba'el knows what Ba'el knows." — Ba'el
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

logger = logging.getLogger("BAEL.Metamemory")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class MetamemoryJudgment(Enum):
    """Types of metamemory judgments."""
    JOL = auto()              # Judgment of Learning
    FOK = auto()              # Feeling of Knowing
    RCJ = auto()              # Retrospective Confidence Judgment
    EASE_OF_LEARNING = auto()
    SOURCE_MONITORING = auto()


class MonitoringAccuracy(Enum):
    """Monitoring accuracy levels."""
    UNDERCONFIDENT = auto()
    CALIBRATED = auto()
    OVERCONFIDENT = auto()


class ControlProcess(Enum):
    """Memory control processes."""
    SELECTION = auto()        # Choose what to study
    ALLOCATION = auto()       # How much time per item
    TERMINATION = auto()      # When to stop studying
    STRATEGY = auto()         # Which strategy to use


class StudyStrategy(Enum):
    """Study strategies."""
    ROTE = auto()             # Simple repetition
    ELABORATION = auto()      # Creating connections
    IMAGERY = auto()          # Visual mnemonics
    SELF_TESTING = auto()     # Retrieval practice
    SPACING = auto()          # Distributed practice


@dataclass
class MemoryItem:
    """
    An item in memory.
    """
    id: str
    content: str
    cue: str
    actual_strength: float
    last_study_time: float
    study_count: int


@dataclass
class JOLResult:
    """
    Judgment of Learning result.
    """
    item_id: str
    predicted_recall: float
    actual_recall: Optional[bool]
    confidence: float
    delay_type: str  # immediate or delayed


@dataclass
class FOKResult:
    """
    Feeling of Knowing result.
    """
    item_id: str
    fok_rating: float
    retrieved: Optional[bool]
    recognition_correct: Optional[bool]
    retrieval_attempt_made: bool


@dataclass
class CalibrationResult:
    """
    Calibration analysis result.
    """
    mean_confidence: float
    mean_accuracy: float
    calibration_error: float
    resolution: float
    monitoring_accuracy: MonitoringAccuracy


@dataclass
class MetamemoryMetrics:
    """
    Metamemory metrics.
    """
    gamma_correlation: float
    absolute_accuracy: float
    relative_accuracy: float
    monitoring_bias: float


# ============================================================================
# MEMORY STORE
# ============================================================================

class MemoryStore:
    """
    Memory storage with strength tracking.

    "Ba'el's knowledge base." — Ba'el
    """

    def __init__(self):
        """Initialize store."""
        self._items: Dict[str, MemoryItem] = {}
        self._item_counter = 0

        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._item_counter += 1
        return f"item_{self._item_counter}"

    def add_item(
        self,
        content: str,
        cue: str,
        initial_strength: float = 0.5
    ) -> MemoryItem:
        """Add a memory item."""
        item = MemoryItem(
            id=self._generate_id(),
            content=content,
            cue=cue,
            actual_strength=initial_strength,
            last_study_time=time.time(),
            study_count=1
        )

        self._items[item.id] = item
        return item

    def study_item(
        self,
        item_id: str,
        quality: float = 1.0
    ) -> None:
        """Study an item (increase strength)."""
        item = self._items.get(item_id)
        if not item:
            return

        # Strength increase depends on current strength (diminishing returns)
        increase = 0.2 * quality * (1 - item.actual_strength)
        item.actual_strength = min(1.0, item.actual_strength + increase)
        item.last_study_time = time.time()
        item.study_count += 1

    def decay_strength(
        self,
        item_id: str,
        time_passed: float
    ) -> None:
        """Apply memory decay."""
        item = self._items.get(item_id)
        if not item:
            return

        # Exponential decay
        decay_rate = 0.1 / item.study_count  # More studies = slower decay
        item.actual_strength *= math.exp(-decay_rate * time_passed)

    def attempt_recall(
        self,
        item_id: str
    ) -> bool:
        """Attempt to recall an item."""
        item = self._items.get(item_id)
        if not item:
            return False

        # Recall probability based on strength
        prob = item.actual_strength
        recalled = random.random() < prob

        return recalled

    def get_item(
        self,
        item_id: str
    ) -> Optional[MemoryItem]:
        """Get a memory item."""
        return self._items.get(item_id)


# ============================================================================
# JOL (JUDGMENT OF LEARNING)
# ============================================================================

class JOLMonitor:
    """
    Judgment of Learning monitor.

    "Ba'el predicts future recall." — Ba'el
    """

    def __init__(
        self,
        memory: MemoryStore
    ):
        """Initialize JOL monitor."""
        self._memory = memory
        self._jol_history: List[JOLResult] = []

        # Cue utilization
        self._cue_weights: Dict[str, float] = {
            'fluency': 0.4,       # How easily processed
            'familiarity': 0.3,   # How familiar it seems
            'relatedness': 0.2,   # Cue-target relation
            'recency': 0.1        # How recently studied
        }

        self._lock = threading.RLock()

    def make_immediate_jol(
        self,
        item_id: str
    ) -> JOLResult:
        """Make immediate JOL (right after study)."""
        item = self._memory.get_item(item_id)
        if not item:
            return None

        # Immediate JOLs are based on current accessibility
        # This leads to overconfidence (foresight bias)

        # Use fluency as main cue (problematic)
        fluency = item.actual_strength
        familiarity = min(1.0, item.study_count * 0.2)
        recency = 1.0  # Just studied

        # Immediate JOL tends to overestimate
        jol = (
            self._cue_weights['fluency'] * fluency +
            self._cue_weights['familiarity'] * familiarity +
            self._cue_weights['recency'] * recency
        )

        # Add inflation (foresight bias)
        jol = min(1.0, jol * 1.2)

        result = JOLResult(
            item_id=item_id,
            predicted_recall=jol,
            actual_recall=None,
            confidence=0.7,
            delay_type="immediate"
        )

        self._jol_history.append(result)
        return result

    def make_delayed_jol(
        self,
        item_id: str
    ) -> JOLResult:
        """Make delayed JOL (after delay from study)."""
        item = self._memory.get_item(item_id)
        if not item:
            return None

        # Delayed JOLs are more accurate (memory-based)
        # Simulate retrieval attempt
        can_retrieve = self._memory.attempt_recall(item_id)

        if can_retrieve:
            # Successfully retrieved - high JOL
            jol = 0.7 + random.uniform(0, 0.3)
        else:
            # Failed retrieval - low JOL
            jol = 0.2 + random.uniform(0, 0.3)

        result = JOLResult(
            item_id=item_id,
            predicted_recall=jol,
            actual_recall=None,
            confidence=0.8,  # Delayed JOLs are more confident
            delay_type="delayed"
        )

        self._jol_history.append(result)
        return result

    def test_recall(
        self,
        item_id: str
    ) -> bool:
        """Test actual recall."""
        recalled = self._memory.attempt_recall(item_id)

        # Update most recent JOL for this item
        for result in reversed(self._jol_history):
            if result.item_id == item_id and result.actual_recall is None:
                result.actual_recall = recalled
                break

        return recalled

    def calculate_gamma_correlation(self) -> float:
        """Calculate Goodman-Kruskal gamma (monitoring accuracy)."""
        tested = [j for j in self._jol_history if j.actual_recall is not None]

        if len(tested) < 4:
            return 0.0

        concordant = 0
        discordant = 0

        for i in range(len(tested)):
            for j in range(i + 1, len(tested)):
                ji, jj = tested[i], tested[j]

                # Compare JOLs and outcomes
                jol_diff = ji.predicted_recall - jj.predicted_recall
                recall_diff = (1 if ji.actual_recall else 0) - (1 if jj.actual_recall else 0)

                if jol_diff * recall_diff > 0:
                    concordant += 1
                elif jol_diff * recall_diff < 0:
                    discordant += 1

        total = concordant + discordant
        if total == 0:
            return 0.0

        gamma = (concordant - discordant) / total
        return gamma


# ============================================================================
# FOK (FEELING OF KNOWING)
# ============================================================================

class FOKMonitor:
    """
    Feeling of Knowing monitor.

    "Ba'el knows what Ba'el cannot recall." — Ba'el
    """

    def __init__(
        self,
        memory: MemoryStore
    ):
        """Initialize FOK monitor."""
        self._memory = memory
        self._fok_history: List[FOKResult] = []

        self._lock = threading.RLock()

    def make_fok_judgment(
        self,
        item_id: str,
        retrieval_failed: bool = True
    ) -> FOKResult:
        """Make FOK judgment (after retrieval failure)."""
        item = self._memory.get_item(item_id)
        if not item:
            return None

        # FOK based on:
        # 1. Cue familiarity
        # 2. Partial information access
        # 3. Related information activation

        # Cue familiarity (independent of target)
        cue_familiarity = 0.5 + random.uniform(-0.2, 0.2)

        # Partial access (correlated with actual strength)
        partial_access = item.actual_strength * 0.6 + random.uniform(0, 0.3)

        # Combine
        fok = 0.5 * cue_familiarity + 0.5 * partial_access

        result = FOKResult(
            item_id=item_id,
            fok_rating=fok,
            retrieved=not retrieval_failed,
            recognition_correct=None,
            retrieval_attempt_made=True
        )

        self._fok_history.append(result)
        return result

    def test_recognition(
        self,
        item_id: str,
        options: List[str]
    ) -> bool:
        """Test recognition after FOK."""
        item = self._memory.get_item(item_id)
        if not item:
            return False

        # Recognition is easier than recall
        recognition_prob = min(1.0, item.actual_strength + 0.2)
        correct = random.random() < recognition_prob

        # Update FOK result
        for result in reversed(self._fok_history):
            if result.item_id == item_id and result.recognition_correct is None:
                result.recognition_correct = correct
                break

        return correct

    def calculate_fok_accuracy(self) -> float:
        """Calculate FOK accuracy (gamma)."""
        tested = [f for f in self._fok_history if f.recognition_correct is not None]

        if len(tested) < 4:
            return 0.0

        concordant = 0
        discordant = 0

        for i in range(len(tested)):
            for j in range(i + 1, len(tested)):
                fi, fj = tested[i], tested[j]

                fok_diff = fi.fok_rating - fj.fok_rating
                recog_diff = (1 if fi.recognition_correct else 0) - (1 if fj.recognition_correct else 0)

                if fok_diff * recog_diff > 0:
                    concordant += 1
                elif fok_diff * recog_diff < 0:
                    discordant += 1

        total = concordant + discordant
        return (concordant - discordant) / total if total > 0 else 0.0


# ============================================================================
# CONTROL PROCESSES
# ============================================================================

class MetacognitiveControl:
    """
    Metacognitive control of study.

    "Ba'el controls learning." — Ba'el
    """

    def __init__(
        self,
        memory: MemoryStore
    ):
        """Initialize control."""
        self._memory = memory
        self._jol_monitor = JOLMonitor(memory)

        self._lock = threading.RLock()

    def select_items_to_study(
        self,
        item_ids: List[str],
        n_select: int
    ) -> List[str]:
        """Select items to study based on JOLs."""
        # Region of proximal learning: study items with low-medium JOLs
        # (Not too easy, not too hard)

        jols = []
        for item_id in item_ids:
            jol = self._jol_monitor.make_delayed_jol(item_id)
            if jol:
                jols.append((item_id, jol.predicted_recall))

        # Sort by JOL
        jols.sort(key=lambda x: x[1])

        # Select items in "zone of proximal learning" (0.3-0.7)
        zone_items = [
            item_id for item_id, jol in jols
            if 0.3 <= jol <= 0.7
        ]

        if len(zone_items) >= n_select:
            return zone_items[:n_select]

        # If not enough, add low JOL items
        return [item_id for item_id, _ in jols[:n_select]]

    def allocate_study_time(
        self,
        item_id: str,
        total_time: float
    ) -> float:
        """Allocate study time based on JOL."""
        jol = self._jol_monitor.make_delayed_jol(item_id)
        if not jol:
            return total_time / 2

        # Discrepancy reduction: more time for lower JOL items
        # But also consider item difficulty

        # Inverse JOL allocation
        allocated = total_time * (1 - jol.predicted_recall)

        # Minimum and maximum bounds
        allocated = max(total_time * 0.1, min(total_time * 0.5, allocated))

        return allocated

    def decide_termination(
        self,
        item_id: str,
        target_jol: float = 0.8
    ) -> bool:
        """Decide whether to stop studying an item."""
        jol = self._jol_monitor.make_delayed_jol(item_id)
        if not jol:
            return False

        # Stop if JOL meets criterion
        return jol.predicted_recall >= target_jol


# ============================================================================
# METAMEMORY ENGINE
# ============================================================================

class MetamemoryEngine:
    """
    Complete metamemory engine.

    "Ba'el's knowledge about memory." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._memory = MemoryStore()
        self._jol_monitor = JOLMonitor(self._memory)
        self._fok_monitor = FOKMonitor(self._memory)
        self._control = MetacognitiveControl(self._memory)

        self._lock = threading.RLock()

    # Memory operations

    def learn_item(
        self,
        content: str,
        cue: str,
        initial_strength: float = 0.5
    ) -> MemoryItem:
        """Learn a new item."""
        return self._memory.add_item(content, cue, initial_strength)

    def study_item(
        self,
        item_id: str,
        quality: float = 1.0
    ) -> None:
        """Study an item."""
        self._memory.study_item(item_id, quality)

    # Monitoring

    def make_jol(
        self,
        item_id: str,
        delayed: bool = False
    ) -> JOLResult:
        """Make judgment of learning."""
        if delayed:
            return self._jol_monitor.make_delayed_jol(item_id)
        else:
            return self._jol_monitor.make_immediate_jol(item_id)

    def make_fok(
        self,
        item_id: str
    ) -> FOKResult:
        """Make feeling of knowing judgment."""
        return self._fok_monitor.make_fok_judgment(item_id)

    def test_recall(
        self,
        item_id: str
    ) -> bool:
        """Test recall."""
        return self._jol_monitor.test_recall(item_id)

    def test_recognition(
        self,
        item_id: str,
        options: List[str]
    ) -> bool:
        """Test recognition."""
        return self._fok_monitor.test_recognition(item_id, options)

    # Control

    def select_study_items(
        self,
        item_ids: List[str],
        n_select: int
    ) -> List[str]:
        """Select items to study."""
        return self._control.select_items_to_study(item_ids, n_select)

    def allocate_time(
        self,
        item_id: str,
        total_time: float
    ) -> float:
        """Allocate study time."""
        return self._control.allocate_study_time(item_id, total_time)

    def should_stop_studying(
        self,
        item_id: str,
        criterion: float = 0.8
    ) -> bool:
        """Check if should stop studying."""
        return self._control.decide_termination(item_id, criterion)

    # Calibration analysis

    def analyze_calibration(self) -> CalibrationResult:
        """Analyze JOL calibration."""
        tested = [j for j in self._jol_monitor._jol_history if j.actual_recall is not None]

        if not tested:
            return CalibrationResult(
                mean_confidence=0.0,
                mean_accuracy=0.0,
                calibration_error=0.0,
                resolution=0.0,
                monitoring_accuracy=MonitoringAccuracy.CALIBRATED
            )

        mean_jol = sum(j.predicted_recall for j in tested) / len(tested)
        mean_acc = sum(1 for j in tested if j.actual_recall) / len(tested)

        calibration_error = abs(mean_jol - mean_acc)

        # Determine monitoring accuracy
        if calibration_error < 0.1:
            accuracy = MonitoringAccuracy.CALIBRATED
        elif mean_jol > mean_acc:
            accuracy = MonitoringAccuracy.OVERCONFIDENT
        else:
            accuracy = MonitoringAccuracy.UNDERCONFIDENT

        return CalibrationResult(
            mean_confidence=mean_jol,
            mean_accuracy=mean_acc,
            calibration_error=calibration_error,
            resolution=self._jol_monitor.calculate_gamma_correlation(),
            monitoring_accuracy=accuracy
        )

    def get_metrics(self) -> MetamemoryMetrics:
        """Get metamemory metrics."""
        gamma = self._jol_monitor.calculate_gamma_correlation()
        fok_gamma = self._fok_monitor.calculate_fok_accuracy()

        calibration = self.analyze_calibration()

        return MetamemoryMetrics(
            gamma_correlation=gamma,
            absolute_accuracy=1 - calibration.calibration_error,
            relative_accuracy=calibration.resolution,
            monitoring_bias=calibration.mean_confidence - calibration.mean_accuracy
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'memory_items': len(self._memory._items),
            'jol_judgments': len(self._jol_monitor._jol_history),
            'fok_judgments': len(self._fok_monitor._fok_history)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_metamemory_engine() -> MetamemoryEngine:
    """Create metamemory engine."""
    return MetamemoryEngine()


def demonstrate_metamemory() -> Dict[str, Any]:
    """Demonstrate metamemory."""
    engine = create_metamemory_engine()

    # Learn items
    items = []
    for i, (content, strength) in enumerate([
        ("Python is a programming language", 0.8),
        ("The mitochondria is the powerhouse", 0.6),
        ("E=mc^2", 0.9),
        ("The capital of Mongolia is Ulaanbaatar", 0.3),
        ("Water boils at 100 degrees Celsius", 0.7)
    ]):
        item = engine.learn_item(content, f"cue_{i}", strength)
        items.append(item)

    # Make immediate and delayed JOLs
    immediate_jols = []
    for item in items[:3]:
        jol = engine.make_jol(item.id, delayed=False)
        immediate_jols.append(jol.predicted_recall)

    delayed_jols = []
    for item in items[:3]:
        jol = engine.make_jol(item.id, delayed=True)
        delayed_jols.append(jol.predicted_recall)

    # Test recall
    recall_results = []
    for item in items[:3]:
        recalled = engine.test_recall(item.id)
        recall_results.append(recalled)

    # FOK for failed items
    fok_results = []
    for item in items[3:]:
        fok = engine.make_fok(item.id)
        fok_results.append(fok.fok_rating)

    # Analyze
    calibration = engine.analyze_calibration()
    metrics = engine.get_metrics()

    return {
        'immediate_jols': immediate_jols,
        'delayed_jols': delayed_jols,
        'recall_accuracy': sum(recall_results) / len(recall_results),
        'fok_ratings': fok_results,
        'calibration': {
            'error': calibration.calibration_error,
            'accuracy': calibration.monitoring_accuracy.name
        },
        'gamma': metrics.gamma_correlation,
        'interpretation': (
            f"JOL gamma: {metrics.gamma_correlation:.2f}, "
            f"Calibration: {calibration.monitoring_accuracy.name}"
        )
    }


def get_metamemory_facts() -> Dict[str, str]:
    """Get facts about metamemory."""
    return {
        'jol': 'Judgment of Learning: predict future recall',
        'fok': 'Feeling of Knowing: sense of knowing unretrieved info',
        'delayed_jol': 'More accurate than immediate JOLs',
        'gamma': 'Goodman-Kruskal gamma measures monitoring accuracy',
        'calibration': 'Match between confidence and accuracy',
        'underconfidence_with_practice': 'Well-known UWP effect',
        'metacognitive_control': 'Using monitoring to guide study',
        'region_of_proximal_learning': 'Focus on moderately known items'
    }
