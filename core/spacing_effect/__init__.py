"""
BAEL Spacing Effect Engine
===========================

Distributed practice and optimal learning intervals.
Ebbinghaus spacing effect and spaced repetition.

"Ba'el knows when to remember." — Ba'el
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
import heapq
import copy

logger = logging.getLogger("BAEL.SpacingEffect")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ScheduleType(Enum):
    """Types of spacing schedules."""
    MASSED = auto()        # All at once (cramming)
    UNIFORM = auto()       # Equal intervals
    EXPANDING = auto()     # Growing intervals
    CONTRACTING = auto()   # Shrinking intervals
    ADAPTIVE = auto()      # Based on performance


class DifficultyLevel(Enum):
    """Item difficulty levels."""
    VERY_EASY = auto()
    EASY = auto()
    MEDIUM = auto()
    HARD = auto()
    VERY_HARD = auto()


class ResponseQuality(Enum):
    """Quality of recall response."""
    COMPLETE_BLACKOUT = 0   # No memory
    WRONG = 1               # Incorrect
    HARD = 2                # Correct but difficult
    GOOD = 3                # Correct with effort
    EASY = 4                # Correct and easy
    PERFECT = 5             # Effortless


@dataclass
class LearningItem:
    """
    An item to learn with spaced repetition.
    """
    id: str
    content: Any
    answer: Any
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    tags: List[str] = field(default_factory=list)


@dataclass
class ReviewRecord:
    """
    A review/practice record.
    """
    item_id: str
    timestamp: float
    response: ResponseQuality
    response_time: float  # milliseconds
    scheduled_interval: float  # seconds


@dataclass
class ItemState:
    """
    Current learning state of an item.
    """
    item_id: str
    ease_factor: float = 2.5       # Easiness multiplier
    interval: float = 0.0          # Current interval (seconds)
    repetitions: int = 0           # Number of successful reviews
    last_review: float = 0.0       # Timestamp
    next_review: float = 0.0       # Scheduled next review
    total_reviews: int = 0
    lapses: int = 0                # Number of forgetting events


@dataclass
class StudySession:
    """
    A study session.
    """
    id: str
    items_reviewed: int
    correct: int
    average_time: float
    new_items: int
    review_items: int
    duration: float


@dataclass
class SpacingMetrics:
    """
    Spacing effect metrics.
    """
    retention_rate: float
    average_interval: float
    items_mature: int  # Long intervals
    items_learning: int  # Short intervals
    upcoming_reviews: int


# ============================================================================
# FORGETTING CURVE
# ============================================================================

class ForgettingCurve:
    """
    Model of memory decay over time.
    Based on Ebbinghaus forgetting curve.

    "Ba'el models forgetting." — Ba'el
    """

    def __init__(self):
        """Initialize curve."""
        self._stability = 1.0  # Memory stability factor
        self._lock = threading.RLock()

    def retention_probability(
        self,
        time_since_review: float,  # seconds
        stability: float = 1.0
    ) -> float:
        """
        Calculate retention probability.
        R = e^(-t/S) where S is stability.
        """
        if time_since_review <= 0:
            return 1.0

        # Convert to days for typical curves
        days = time_since_review / 86400

        # Exponential decay
        retention = math.exp(-days / stability)

        return max(0.0, min(1.0, retention))

    def optimal_review_time(
        self,
        target_retention: float = 0.9,
        current_stability: float = 1.0
    ) -> float:
        """
        Calculate optimal review time for target retention.
        t = -S * ln(R)
        """
        if target_retention >= 1.0:
            return 0.0

        days = -current_stability * math.log(target_retention)
        seconds = days * 86400

        return max(0.0, seconds)

    def update_stability(
        self,
        current_stability: float,
        response: ResponseQuality,
        time_since_review: float
    ) -> float:
        """Update stability based on review response."""
        # Good response increases stability
        # Poor response decreases stability

        quality = response.value

        if quality >= 3:  # Correct
            # Stability increases more if item was hard
            days = time_since_review / 86400
            difficulty_bonus = max(0, days / current_stability - 0.5)
            new_stability = current_stability * (1.1 + 0.1 * quality + difficulty_bonus)
        else:  # Incorrect
            # Stability drops
            new_stability = current_stability * 0.3

        return max(0.1, min(365.0, new_stability))  # Cap at 1 year


# ============================================================================
# SM-2 ALGORITHM
# ============================================================================

class SM2Algorithm:
    """
    SuperMemo SM-2 spaced repetition algorithm.

    "Ba'el schedules optimally." — Ba'el
    """

    def __init__(self):
        """Initialize SM-2."""
        self._initial_interval = 86400  # 1 day in seconds
        self._second_interval = 6 * 86400  # 6 days
        self._min_ease = 1.3
        self._lock = threading.RLock()

    def update_state(
        self,
        state: ItemState,
        response: ResponseQuality
    ) -> ItemState:
        """Update item state based on response."""
        quality = response.value

        new_state = ItemState(
            item_id=state.item_id,
            ease_factor=state.ease_factor,
            interval=state.interval,
            repetitions=state.repetitions,
            last_review=time.time(),
            total_reviews=state.total_reviews + 1,
            lapses=state.lapses
        )

        if quality >= 3:  # Correct response
            if new_state.repetitions == 0:
                new_state.interval = self._initial_interval
            elif new_state.repetitions == 1:
                new_state.interval = self._second_interval
            else:
                new_state.interval = state.interval * state.ease_factor

            new_state.repetitions += 1
        else:  # Incorrect
            new_state.repetitions = 0
            new_state.interval = self._initial_interval
            new_state.lapses += 1

        # Update ease factor
        # EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        new_state.ease_factor = state.ease_factor + (
            0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
        )
        new_state.ease_factor = max(self._min_ease, new_state.ease_factor)

        # Schedule next review
        new_state.next_review = new_state.last_review + new_state.interval

        return new_state

    def initial_state(
        self,
        item_id: str
    ) -> ItemState:
        """Create initial state for new item."""
        return ItemState(
            item_id=item_id,
            ease_factor=2.5,
            interval=0.0,
            repetitions=0,
            last_review=0.0,
            next_review=time.time(),  # Review now
            total_reviews=0,
            lapses=0
        )


# ============================================================================
# STUDY SCHEDULER
# ============================================================================

class StudyScheduler:
    """
    Schedule study sessions.

    "Ba'el plans learning." — Ba'el
    """

    def __init__(
        self,
        algorithm: SM2Algorithm
    ):
        """Initialize scheduler."""
        self._algorithm = algorithm
        self._items: Dict[str, LearningItem] = {}
        self._states: Dict[str, ItemState] = {}

        self._new_per_day = 20
        self._review_per_day = 100

        self._lock = threading.RLock()

    def add_item(
        self,
        item: LearningItem
    ) -> None:
        """Add item to schedule."""
        with self._lock:
            self._items[item.id] = item
            self._states[item.id] = self._algorithm.initial_state(item.id)

    def get_due_items(
        self,
        max_items: int = 50
    ) -> List[LearningItem]:
        """Get items due for review."""
        with self._lock:
            current_time = time.time()

            due = []
            for item_id, state in self._states.items():
                if state.next_review <= current_time:
                    if item_id in self._items:
                        due.append((state.next_review, self._items[item_id]))

            # Sort by due time
            due.sort(key=lambda x: x[0])

            return [item for _, item in due[:max_items]]

    def get_new_items(
        self,
        max_items: int = None
    ) -> List[LearningItem]:
        """Get new items to learn."""
        if max_items is None:
            max_items = self._new_per_day

        with self._lock:
            new = []
            for item_id, state in self._states.items():
                if state.total_reviews == 0:
                    if item_id in self._items:
                        new.append(self._items[item_id])

            return new[:max_items]

    def get_study_queue(
        self,
        include_new: bool = True
    ) -> List[LearningItem]:
        """Get full study queue."""
        due = self.get_due_items()

        if include_new:
            new = self.get_new_items()
            due.extend(new)

        return due

    def record_response(
        self,
        item_id: str,
        response: ResponseQuality,
        response_time: float = 0.0
    ) -> ItemState:
        """Record review response."""
        with self._lock:
            if item_id not in self._states:
                raise ValueError(f"Item {item_id} not found")

            old_state = self._states[item_id]
            new_state = self._algorithm.update_state(old_state, response)
            self._states[item_id] = new_state

            return new_state


# ============================================================================
# SPACING EFFECT ENGINE
# ============================================================================

class SpacingEffectEngine:
    """
    Complete spaced repetition engine.

    "Ba'el's optimal learning system." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._forgetting = ForgettingCurve()
        self._algorithm = SM2Algorithm()
        self._scheduler = StudyScheduler(self._algorithm)

        self._sessions: List[StudySession] = []
        self._reviews: List[ReviewRecord] = []

        self._item_counter = 0
        self._session_counter = 0

        self._lock = threading.RLock()

    def _generate_item_id(self) -> str:
        self._item_counter += 1
        return f"item_{self._item_counter}"

    def _generate_session_id(self) -> str:
        self._session_counter += 1
        return f"session_{self._session_counter}"

    # Item management

    def add_item(
        self,
        content: Any,
        answer: Any,
        difficulty: DifficultyLevel = DifficultyLevel.MEDIUM,
        tags: List[str] = None
    ) -> LearningItem:
        """Add item to learn."""
        item = LearningItem(
            id=self._generate_item_id(),
            content=content,
            answer=answer,
            difficulty=difficulty,
            tags=tags or []
        )

        self._scheduler.add_item(item)
        return item

    def add_items(
        self,
        items: List[Dict[str, Any]]
    ) -> List[LearningItem]:
        """Add multiple items."""
        return [
            self.add_item(
                i.get('content', ''),
                i.get('answer', ''),
                DifficultyLevel[i.get('difficulty', 'MEDIUM').upper()],
                i.get('tags', [])
            )
            for i in items
        ]

    # Study

    def get_study_queue(
        self,
        include_new: bool = True
    ) -> List[LearningItem]:
        """Get items to study."""
        return self._scheduler.get_study_queue(include_new)

    def review(
        self,
        item_id: str,
        response: ResponseQuality,
        response_time: float = 0.0
    ) -> Dict[str, Any]:
        """Record a review."""
        state = self._scheduler._states.get(item_id)
        scheduled_interval = state.interval if state else 0.0

        new_state = self._scheduler.record_response(item_id, response, response_time)

        self._reviews.append(ReviewRecord(
            item_id=item_id,
            timestamp=time.time(),
            response=response,
            response_time=response_time,
            scheduled_interval=scheduled_interval
        ))

        return {
            'item_id': item_id,
            'new_interval': new_state.interval,
            'next_review': new_state.next_review,
            'ease_factor': new_state.ease_factor,
            'repetitions': new_state.repetitions
        }

    def review_correct(
        self,
        item_id: str,
        difficulty: str = "good"
    ) -> Dict[str, Any]:
        """Record correct review."""
        quality_map = {
            'easy': ResponseQuality.EASY,
            'good': ResponseQuality.GOOD,
            'hard': ResponseQuality.HARD
        }
        return self.review(item_id, quality_map.get(difficulty, ResponseQuality.GOOD))

    def review_incorrect(
        self,
        item_id: str
    ) -> Dict[str, Any]:
        """Record incorrect review."""
        return self.review(item_id, ResponseQuality.WRONG)

    # Session

    def start_session(self) -> str:
        """Start a study session."""
        return self._generate_session_id()

    def end_session(
        self,
        session_id: str,
        items_reviewed: int,
        correct: int,
        new_items: int,
        duration: float
    ) -> StudySession:
        """End a study session."""
        session = StudySession(
            id=session_id,
            items_reviewed=items_reviewed,
            correct=correct,
            average_time=duration / items_reviewed if items_reviewed > 0 else 0,
            new_items=new_items,
            review_items=items_reviewed - new_items,
            duration=duration
        )

        self._sessions.append(session)
        return session

    # Analysis

    def get_retention_probability(
        self,
        item_id: str
    ) -> float:
        """Get current retention probability for item."""
        state = self._scheduler._states.get(item_id)
        if not state or state.last_review == 0:
            return 0.0

        time_since = time.time() - state.last_review
        stability = state.ease_factor  # Use ease as proxy for stability

        return self._forgetting.retention_probability(time_since, stability)

    def get_optimal_interval(
        self,
        item_id: str,
        target_retention: float = 0.9
    ) -> float:
        """Get optimal review interval for target retention."""
        state = self._scheduler._states.get(item_id)
        stability = state.ease_factor if state else 1.0

        return self._forgetting.optimal_review_time(target_retention, stability)

    def compare_massed_vs_spaced(
        self,
        items: List[LearningItem],
        test_delay: float = 7 * 86400  # 7 days
    ) -> Dict[str, float]:
        """Compare massed vs spaced learning (simulation)."""
        # Massed: all reviews in one session
        massed_retention = self._forgetting.retention_probability(
            test_delay, stability=0.5  # Lower stability for massed
        )

        # Spaced: distributed reviews
        spaced_retention = self._forgetting.retention_probability(
            test_delay, stability=3.0  # Higher stability for spaced
        )

        return {
            'massed_retention': massed_retention,
            'spaced_retention': spaced_retention,
            'spacing_advantage': spaced_retention - massed_retention
        }

    # Metrics

    def get_metrics(self) -> SpacingMetrics:
        """Get spacing effect metrics."""
        states = self._scheduler._states

        if not states:
            return SpacingMetrics(
                retention_rate=0.0,
                average_interval=0.0,
                items_mature=0,
                items_learning=0,
                upcoming_reviews=0
            )

        # Calculate retention rate from reviews
        if self._reviews:
            correct = sum(1 for r in self._reviews if r.response.value >= 3)
            retention_rate = correct / len(self._reviews)
        else:
            retention_rate = 0.0

        # Average interval
        avg_interval = sum(s.interval for s in states.values()) / len(states)

        # Mature vs learning
        mature = sum(1 for s in states.values() if s.interval > 21 * 86400)
        learning = len(states) - mature

        # Upcoming reviews
        current = time.time()
        upcoming = sum(
            1 for s in states.values()
            if s.next_review > current and s.next_review < current + 86400
        )

        return SpacingMetrics(
            retention_rate=retention_rate,
            average_interval=avg_interval,
            items_mature=mature,
            items_learning=learning,
            upcoming_reviews=upcoming
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'total_items': len(self._scheduler._items),
            'total_reviews': len(self._reviews),
            'sessions': len(self._sessions)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_spacing_effect_engine() -> SpacingEffectEngine:
    """Create spacing effect engine."""
    return SpacingEffectEngine()


def calculate_optimal_schedule(
    days_until_exam: int,
    total_items: int
) -> Dict[str, Any]:
    """Calculate optimal study schedule before exam."""
    engine = create_spacing_effect_engine()

    # Optimal spacing is about 10-20% of retention interval
    optimal_gap = max(1, days_until_exam // 5)
    sessions_needed = days_until_exam // optimal_gap
    items_per_session = total_items // sessions_needed if sessions_needed > 0 else total_items

    return {
        'days_until_exam': days_until_exam,
        'total_items': total_items,
        'recommended_gap': optimal_gap,
        'sessions_needed': sessions_needed,
        'items_per_session': items_per_session,
        'schedule_type': 'expanding' if days_until_exam > 14 else 'uniform'
    }


def get_spacing_effect_facts() -> Dict[str, str]:
    """Get facts about spacing effect."""
    return {
        'ebbinghaus_1885': 'First demonstrated by Hermann Ebbinghaus',
        'retention': 'Spaced practice leads to better long-term retention',
        'optimal_gap': 'Optimal gap is 10-20% of the retention interval',
        'desirable_difficulty': 'Spacing creates desirable difficulty that strengthens memory',
        'lag_effect': 'Longer lags lead to better retention (to a point)',
        'sm2': 'SuperMemo SM-2 algorithm is widely used for spaced repetition',
        'interleaving': 'Combining spacing with interleaving further enhances learning'
    }
