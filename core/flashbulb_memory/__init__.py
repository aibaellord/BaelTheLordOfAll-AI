"""
BAEL Flashbulb Memory Engine
==============================

Brown & Kulik flashbulb memories.
Emotional memory enhancement.

"Ba'el remembers the vivid moments." — Ba'el
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

logger = logging.getLogger("BAEL.FlashbulbMemory")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class EmotionalValence(Enum):
    """Emotional valence."""
    VERY_NEGATIVE = -2
    NEGATIVE = -1
    NEUTRAL = 0
    POSITIVE = 1
    VERY_POSITIVE = 2


class EmotionalArousal(Enum):
    """Emotional arousal level."""
    LOW = 1
    MODERATE = 2
    HIGH = 3
    EXTREME = 4


class FlashbulbCategory(Enum):
    """Categories of flashbulb events."""
    PERSONAL = auto()      # Personal life events
    NATIONAL = auto()      # National/world events
    CELEBRITY = auto()     # Celebrity news
    NATURAL_DISASTER = auto()
    TERRORISM = auto()
    POLITICAL = auto()


class MemoryConfidence(Enum):
    """Confidence in memory."""
    VERY_LOW = 1
    LOW = 2
    MODERATE = 3
    HIGH = 4
    VERY_HIGH = 5


@dataclass
class EmotionalState:
    """
    Emotional state at encoding.
    """
    valence: EmotionalValence
    arousal: EmotionalArousal
    surprise: float  # 0-1


@dataclass
class FlashbulbDetail:
    """
    A detail in flashbulb memory.
    """
    category: str
    content: Any
    confidence: float
    consistency: float = 1.0  # Consistency over time


@dataclass
class FlashbulbMemory:
    """
    A flashbulb memory.
    """
    id: str
    event_description: str
    category: FlashbulbCategory

    # Reception context
    where_you_were: str
    what_you_were_doing: str
    who_told_you: str
    how_you_felt: str

    # Emotional properties
    emotional_state: EmotionalState
    personal_importance: float
    rehearsal_count: int

    # Memory properties
    vividness: float
    confidence: MemoryConfidence
    accuracy: float  # Hidden - actual accuracy

    creation_time: float = field(default_factory=time.time)
    last_recall: float = field(default_factory=time.time)


@dataclass
class RecallAttempt:
    """
    A recall attempt.
    """
    memory_id: str
    timestamp: float
    details_recalled: Dict[str, Any]
    confidence: MemoryConfidence
    vividness: float


@dataclass
class ConsistencyAnalysis:
    """
    Analysis of memory consistency.
    """
    memory_id: str
    recall_count: int
    overall_consistency: float
    detail_consistencies: Dict[str, float]
    confidence_accuracy_correlation: float


@dataclass
class FlashbulbMetrics:
    """
    Flashbulb memory metrics.
    """
    total_memories: int
    average_vividness: float
    average_confidence: float
    average_accuracy: float
    confidence_accuracy_gap: float


# ============================================================================
# NOW-PRINT MECHANISM
# ============================================================================

class NowPrintMechanism:
    """
    Brown & Kulik's Now Print hypothesis.

    "Ba'el captures the moment." — Ba'el
    """

    def __init__(
        self,
        surprise_threshold: float = 0.5,
        importance_threshold: float = 0.5
    ):
        """Initialize mechanism."""
        self._surprise_threshold = surprise_threshold
        self._importance_threshold = importance_threshold
        self._lock = threading.RLock()

    def evaluate_event(
        self,
        surprise: float,
        personal_importance: float,
        emotional_arousal: EmotionalArousal
    ) -> Tuple[bool, float]:
        """Evaluate if event triggers flashbulb memory."""
        # Now Print theory: surprise + importance triggers special encoding

        arousal_factor = emotional_arousal.value / 4.0

        triggers_flashbulb = (
            surprise >= self._surprise_threshold and
            personal_importance >= self._importance_threshold and
            emotional_arousal.value >= EmotionalArousal.HIGH.value
        )

        encoding_strength = (
            surprise * 0.3 +
            personal_importance * 0.4 +
            arousal_factor * 0.3
        )

        return triggers_flashbulb, min(1.0, encoding_strength)

    def calculate_vividness(
        self,
        encoding_strength: float,
        rehearsals: int,
        time_elapsed: float
    ) -> float:
        """Calculate memory vividness."""
        # High initial vividness with slow decay
        base_vividness = encoding_strength * 0.9

        # Rehearsal maintenance
        rehearsal_boost = min(0.2, rehearsals * 0.02)

        # Very slow decay for flashbulb memories
        decay = 0.01 * (time_elapsed / (3600 * 24 * 365))  # Per year

        vividness = base_vividness + rehearsal_boost - decay
        return max(0.3, min(1.0, vividness))


# ============================================================================
# ACCURACY TRACKER
# ============================================================================

class AccuracyTracker:
    """
    Track memory accuracy vs confidence.

    "Ba'el knows the gap between belief and truth." — Ba'el
    """

    def __init__(self):
        """Initialize tracker."""
        self._recall_history: Dict[str, List[RecallAttempt]] = defaultdict(list)
        self._original_details: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def store_original(
        self,
        memory_id: str,
        details: Dict[str, Any]
    ) -> None:
        """Store original details for comparison."""
        self._original_details[memory_id] = copy.deepcopy(details)

    def record_recall(
        self,
        attempt: RecallAttempt
    ) -> None:
        """Record a recall attempt."""
        self._recall_history[attempt.memory_id].append(attempt)

    def calculate_consistency(
        self,
        memory_id: str
    ) -> Optional[ConsistencyAnalysis]:
        """Calculate memory consistency over time."""
        attempts = self._recall_history.get(memory_id, [])

        if len(attempts) < 2:
            return None

        # Compare each recall to the first
        first = attempts[0].details_recalled
        consistencies = {}

        for key in first.keys():
            matches = 0
            total = 0

            for attempt in attempts[1:]:
                if key in attempt.details_recalled:
                    total += 1
                    if attempt.details_recalled[key] == first[key]:
                        matches += 1

            if total > 0:
                consistencies[key] = matches / total

        overall = (
            sum(consistencies.values()) / len(consistencies)
            if consistencies else 0.0
        )

        # Confidence-accuracy correlation
        # Flashbulb memories often show high confidence but variable accuracy
        confidences = [a.confidence.value for a in attempts]
        avg_confidence = sum(confidences) / len(confidences)

        return ConsistencyAnalysis(
            memory_id=memory_id,
            recall_count=len(attempts),
            overall_consistency=overall,
            detail_consistencies=consistencies,
            confidence_accuracy_correlation=overall  # Simplified
        )

    def calculate_accuracy(
        self,
        memory_id: str,
        current_details: Dict[str, Any]
    ) -> float:
        """Calculate accuracy against original."""
        original = self._original_details.get(memory_id)

        if not original:
            return 0.5  # Unknown

        matches = 0
        total = 0

        for key in original.keys():
            if key in current_details:
                total += 1
                if current_details[key] == original[key]:
                    matches += 1

        return matches / total if total > 0 else 0.5


# ============================================================================
# FLASHBULB MEMORY ENGINE
# ============================================================================

class FlashbulbMemoryEngine:
    """
    Complete flashbulb memory engine.

    "Ba'el's vivid memory system." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._now_print = NowPrintMechanism()
        self._accuracy = AccuracyTracker()

        self._memories: Dict[str, FlashbulbMemory] = {}
        self._memory_counter = 0

        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._memory_counter += 1
        return f"flashbulb_{self._memory_counter}"

    # Memory creation

    def encode_event(
        self,
        event_description: str,
        category: FlashbulbCategory,
        where_you_were: str,
        what_you_were_doing: str,
        who_told_you: str,
        how_you_felt: str,
        emotional_state: EmotionalState,
        personal_importance: float
    ) -> Optional[FlashbulbMemory]:
        """Encode a potentially flashbulb event."""
        # Check if triggers flashbulb memory
        triggers, encoding_strength = self._now_print.evaluate_event(
            emotional_state.surprise,
            personal_importance,
            emotional_state.arousal
        )

        if not triggers:
            # Not salient enough for flashbulb memory
            return None

        vividness = self._now_print.calculate_vividness(
            encoding_strength, 0, 0
        )

        # Add some inaccuracy from the start
        accuracy = 0.7 + random.uniform(-0.1, 0.2)

        memory = FlashbulbMemory(
            id=self._generate_id(),
            event_description=event_description,
            category=category,
            where_you_were=where_you_were,
            what_you_were_doing=what_you_were_doing,
            who_told_you=who_told_you,
            how_you_felt=how_you_felt,
            emotional_state=emotional_state,
            personal_importance=personal_importance,
            rehearsal_count=0,
            vividness=vividness,
            confidence=MemoryConfidence.VERY_HIGH,
            accuracy=accuracy
        )

        self._memories[memory.id] = memory

        # Store original for accuracy tracking
        self._accuracy.store_original(memory.id, {
            'where': where_you_were,
            'what': what_you_were_doing,
            'who': who_told_you,
            'how': how_you_felt
        })

        return memory

    # Memory recall

    def recall(
        self,
        memory_id: str
    ) -> Optional[RecallAttempt]:
        """Recall a flashbulb memory."""
        memory = self._memories.get(memory_id)

        if not memory:
            return None

        # Recall details with potential errors
        details = {}

        # Each detail may be accurate or reconstructed
        for key, value in [
            ('where', memory.where_you_were),
            ('what', memory.what_you_were_doing),
            ('who', memory.who_told_you),
            ('how', memory.how_you_felt)
        ]:
            if random.random() < memory.accuracy:
                details[key] = value
            else:
                # Reconstruct (potentially wrong)
                details[key] = f"{value} (reconstructed)"

        attempt = RecallAttempt(
            memory_id=memory_id,
            timestamp=time.time(),
            details_recalled=details,
            confidence=memory.confidence,
            vividness=memory.vividness
        )

        self._accuracy.record_recall(attempt)

        # Rehearsal increases count
        memory.rehearsal_count += 1
        memory.last_recall = time.time()

        # Paradox: confidence may increase while accuracy doesn't
        if memory.rehearsal_count > 5:
            memory.confidence = MemoryConfidence.VERY_HIGH

        return attempt

    def rehearse(
        self,
        memory_id: str,
        times: int = 1
    ) -> None:
        """Rehearse a memory."""
        for _ in range(times):
            self.recall(memory_id)

    # Analysis

    def analyze_memory(
        self,
        memory_id: str
    ) -> Optional[Dict[str, Any]]:
        """Analyze a flashbulb memory."""
        memory = self._memories.get(memory_id)

        if not memory:
            return None

        consistency = self._accuracy.calculate_consistency(memory_id)

        return {
            'event': memory.event_description,
            'vividness': memory.vividness,
            'confidence': memory.confidence.name,
            'actual_accuracy': memory.accuracy,
            'rehearsals': memory.rehearsal_count,
            'consistency': consistency.overall_consistency if consistency else None,
            'confidence_accuracy_gap': (
                (memory.confidence.value / 5) - memory.accuracy
            )
        }

    def get_confidence_accuracy_gap(self) -> List[Tuple[float, float]]:
        """Get confidence-accuracy relationship."""
        gaps = []

        for memory in self._memories.values():
            confidence = memory.confidence.value / 5  # Normalize
            gaps.append((confidence, memory.accuracy))

        return gaps

    # Simulate classic effects

    def simulate_9_11_study(
        self,
        n_participants: int = 50
    ) -> Dict[str, Any]:
        """Simulate Talarico & Rubin 2003 9/11 study."""
        # Flashbulb memories for 9/11
        # Everyday memories same day

        results = {
            'flashbulb_confidence': [],
            'flashbulb_consistency': [],
            'everyday_confidence': [],
            'everyday_consistency': []
        }

        for _ in range(n_participants):
            # Flashbulb memory
            fb_memory = self.encode_event(
                event_description="9/11 attacks",
                category=FlashbulbCategory.TERRORISM,
                where_you_were="At school/work",
                what_you_were_doing="Normal routine",
                who_told_you="Coworker/TV",
                how_you_felt="Shocked, scared",
                emotional_state=EmotionalState(
                    valence=EmotionalValence.VERY_NEGATIVE,
                    arousal=EmotionalArousal.EXTREME,
                    surprise=0.95
                ),
                personal_importance=0.9
            )

            if fb_memory:
                # Simulate recalls over time
                for _ in range(3):  # 3 recall sessions
                    self.recall(fb_memory.id)
                    fb_memory.accuracy *= 0.98  # Slight decay

                results['flashbulb_confidence'].append(
                    fb_memory.confidence.value / 5
                )
                results['flashbulb_consistency'].append(
                    fb_memory.accuracy
                )

            # Everyday memory (higher initial decay)
            everyday_confidence = 0.6 + random.uniform(-0.2, 0.2)
            everyday_consistency = 0.5 + random.uniform(-0.2, 0.2)

            results['everyday_confidence'].append(everyday_confidence)
            results['everyday_consistency'].append(everyday_consistency)

        return {
            'flashbulb_mean_confidence': (
                sum(results['flashbulb_confidence']) /
                len(results['flashbulb_confidence'])
            ),
            'flashbulb_mean_consistency': (
                sum(results['flashbulb_consistency']) /
                len(results['flashbulb_consistency'])
            ),
            'everyday_mean_confidence': (
                sum(results['everyday_confidence']) /
                len(results['everyday_confidence'])
            ),
            'everyday_mean_consistency': (
                sum(results['everyday_consistency']) /
                len(results['everyday_consistency'])
            ),
            'interpretation': (
                'Flashbulb memories have higher confidence but similar '
                'consistency decline as everyday memories'
            )
        }

    # Metrics

    def get_metrics(self) -> FlashbulbMetrics:
        """Get flashbulb memory metrics."""
        if not self._memories:
            return FlashbulbMetrics(
                total_memories=0,
                average_vividness=0.0,
                average_confidence=0.0,
                average_accuracy=0.0,
                confidence_accuracy_gap=0.0
            )

        memories = list(self._memories.values())

        avg_vividness = sum(m.vividness for m in memories) / len(memories)
        avg_confidence = sum(m.confidence.value / 5 for m in memories) / len(memories)
        avg_accuracy = sum(m.accuracy for m in memories) / len(memories)

        return FlashbulbMetrics(
            total_memories=len(memories),
            average_vividness=avg_vividness,
            average_confidence=avg_confidence,
            average_accuracy=avg_accuracy,
            confidence_accuracy_gap=avg_confidence - avg_accuracy
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'memories': len(self._memories),
            'total_rehearsals': sum(
                m.rehearsal_count for m in self._memories.values()
            )
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_flashbulb_memory_engine() -> FlashbulbMemoryEngine:
    """Create flashbulb memory engine."""
    return FlashbulbMemoryEngine()


def demonstrate_flashbulb_memory() -> Dict[str, Any]:
    """Demonstrate flashbulb memory."""
    engine = create_flashbulb_memory_engine()

    # Create a flashbulb memory
    memory = engine.encode_event(
        event_description="Significant historical event",
        category=FlashbulbCategory.NATIONAL,
        where_you_were="In living room",
        what_you_were_doing="Watching TV",
        who_told_you="News anchor",
        how_you_felt="Shocked and disbelieving",
        emotional_state=EmotionalState(
            valence=EmotionalValence.NEGATIVE,
            arousal=EmotionalArousal.EXTREME,
            surprise=0.9
        ),
        personal_importance=0.85
    )

    if memory:
        # Recall several times
        for _ in range(5):
            engine.recall(memory.id)

        analysis = engine.analyze_memory(memory.id)
        metrics = engine.get_metrics()

        return {
            'memory_created': True,
            'vividness': analysis['vividness'],
            'confidence': analysis['confidence'],
            'actual_accuracy': analysis['actual_accuracy'],
            'confidence_accuracy_gap': analysis['confidence_accuracy_gap'],
            'interpretation': (
                f"High confidence ({analysis['confidence']}) but "
                f"accuracy is {analysis['actual_accuracy']:.2f} - "
                f"classic flashbulb pattern"
            )
        }

    return {'memory_created': False}


def get_flashbulb_memory_facts() -> Dict[str, str]:
    """Get facts about flashbulb memories."""
    return {
        'brown_kulik_1977': 'Coined term "flashbulb memory"',
        'now_print': 'Hypothesized special encoding mechanism',
        'canonical_categories': 'Where, what doing, who told, how felt',
        'confidence_accuracy': 'High confidence does not mean high accuracy',
        'talarico_rubin': 'Flashbulb memories fade like ordinary memories',
        'neisser': 'Criticized special mechanism hypothesis',
        'emotional_enhancement': 'Emotion enhances encoding but not accuracy',
        'rehearsal': 'Social rehearsal maintains memories but adds distortion'
    }
