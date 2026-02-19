"""
BAEL Temporal Cognition Engine
===============================

Time perception, temporal reasoning, and chronesthesia.

"Ba'el perceives all times." — Ba'el
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

logger = logging.getLogger("BAEL.TemporalCognition")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class TimeScale(Enum):
    """Temporal scales."""
    MILLISECONDS = auto()
    SECONDS = auto()
    MINUTES = auto()
    HOURS = auto()
    DAYS = auto()
    WEEKS = auto()
    MONTHS = auto()
    YEARS = auto()


class TemporalRelation(Enum):
    """Allen's interval relations."""
    BEFORE = auto()        # A entirely before B
    AFTER = auto()         # A entirely after B
    MEETS = auto()         # A ends where B starts
    MET_BY = auto()        # B ends where A starts
    OVERLAPS = auto()      # A starts before B, ends during B
    OVERLAPPED_BY = auto() # B starts before A, ends during A
    DURING = auto()        # A contained within B
    CONTAINS = auto()      # B contained within A
    STARTS = auto()        # A starts when B starts, ends earlier
    STARTED_BY = auto()    # B starts when A starts, ends earlier
    FINISHES = auto()      # A ends when B ends, starts later
    FINISHED_BY = auto()   # B ends when A ends, starts later
    EQUALS = auto()        # Same start and end


class TimeDirection(Enum):
    """Time direction."""
    PAST = auto()
    PRESENT = auto()
    FUTURE = auto()


class TemporalMode(Enum):
    """Temporal processing modes."""
    PROSPECTIVE = auto()   # Looking forward
    RETROSPECTIVE = auto() # Looking backward
    SYNCHRONIC = auto()    # At one time
    DIACHRONIC = auto()    # Across time


@dataclass
class TimePoint:
    """
    A point in time.
    """
    timestamp: float
    label: Optional[str] = None
    uncertainty: float = 0.0  # Temporal uncertainty


@dataclass
class TimeInterval:
    """
    A time interval.
    """
    id: str
    start: TimePoint
    end: TimePoint
    label: Optional[str] = None

    @property
    def duration(self) -> float:
        return self.end.timestamp - self.start.timestamp

    @property
    def midpoint(self) -> float:
        return (self.start.timestamp + self.end.timestamp) / 2


@dataclass
class TemporalEvent:
    """
    A temporal event.
    """
    id: str
    name: str
    interval: TimeInterval
    properties: Dict[str, Any] = field(default_factory=dict)
    participants: List[str] = field(default_factory=list)


@dataclass
class TemporalPattern:
    """
    A temporal pattern.
    """
    id: str
    name: str
    events: List[str]  # Event IDs in order
    relations: List[Tuple[str, TemporalRelation, str]]
    frequency: Optional[float] = None  # Repetitions per time unit


@dataclass
class TimeEstimate:
    """
    Subjective time estimate.
    """
    estimated_duration: float
    actual_duration: float
    ratio: float  # estimated / actual
    direction: TimeDirection


@dataclass
class TemporalPrediction:
    """
    Prediction about future time.
    """
    event_name: str
    predicted_time: float
    confidence: float
    basis: str  # What the prediction is based on


# ============================================================================
# INTERVAL REASONER
# ============================================================================

class IntervalReasoner:
    """
    Reason about temporal intervals.
    Allen's interval algebra.

    "Ba'el reasons about intervals." — Ba'el
    """

    def __init__(self):
        """Initialize reasoner."""
        self._lock = threading.RLock()

    def compute_relation(
        self,
        interval_a: TimeInterval,
        interval_b: TimeInterval
    ) -> TemporalRelation:
        """Compute Allen's relation between intervals."""
        with self._lock:
            a_start = interval_a.start.timestamp
            a_end = interval_a.end.timestamp
            b_start = interval_b.start.timestamp
            b_end = interval_b.end.timestamp

            epsilon = 0.001  # Tolerance for "equals"

            # Check all 13 relations
            if abs(a_start - b_start) < epsilon and abs(a_end - b_end) < epsilon:
                return TemporalRelation.EQUALS

            if a_end < b_start:
                return TemporalRelation.BEFORE

            if b_end < a_start:
                return TemporalRelation.AFTER

            if abs(a_end - b_start) < epsilon:
                return TemporalRelation.MEETS

            if abs(b_end - a_start) < epsilon:
                return TemporalRelation.MET_BY

            if a_start < b_start and a_end > b_start and a_end < b_end:
                return TemporalRelation.OVERLAPS

            if b_start < a_start and b_end > a_start and b_end < a_end:
                return TemporalRelation.OVERLAPPED_BY

            if a_start > b_start and a_end < b_end:
                return TemporalRelation.DURING

            if b_start > a_start and b_end < a_end:
                return TemporalRelation.CONTAINS

            if abs(a_start - b_start) < epsilon and a_end < b_end:
                return TemporalRelation.STARTS

            if abs(a_start - b_start) < epsilon and a_end > b_end:
                return TemporalRelation.STARTED_BY

            if abs(a_end - b_end) < epsilon and a_start > b_start:
                return TemporalRelation.FINISHES

            if abs(a_end - b_end) < epsilon and a_start < b_start:
                return TemporalRelation.FINISHED_BY

            return TemporalRelation.OVERLAPS  # Default

    def compose(
        self,
        rel1: TemporalRelation,
        rel2: TemporalRelation
    ) -> List[TemporalRelation]:
        """Compose two temporal relations (simplified)."""
        # Simplified composition table
        if rel1 == TemporalRelation.BEFORE and rel2 == TemporalRelation.BEFORE:
            return [TemporalRelation.BEFORE]

        if rel1 == TemporalRelation.AFTER and rel2 == TemporalRelation.AFTER:
            return [TemporalRelation.AFTER]

        if rel1 == TemporalRelation.EQUALS:
            return [rel2]

        if rel2 == TemporalRelation.EQUALS:
            return [rel1]

        # Many relations are possible
        return list(TemporalRelation)

    def check_consistency(
        self,
        relations: List[Tuple[str, TemporalRelation, str]]
    ) -> bool:
        """Check if relations are consistent (simplified)."""
        with self._lock:
            # Build constraint graph
            graph: Dict[str, Dict[str, TemporalRelation]] = defaultdict(dict)

            for a, rel, b in relations:
                if b in graph[a]:
                    # Check for conflict
                    if graph[a][b] != rel:
                        return False
                graph[a][b] = rel

            return True


# ============================================================================
# TIME PERCEPTION
# ============================================================================

class TimePerception:
    """
    Subjective time perception.

    "Ba'el perceives time's flow." — Ba'el
    """

    def __init__(self):
        """Initialize perception."""
        self._clock_rate = 1.0  # Subjective clock speed
        self._attention_factor = 1.0
        self._arousal_factor = 1.0

        self._estimates: List[TimeEstimate] = []
        self._lock = threading.RLock()

    def set_attention(self, level: float) -> None:
        """Set attention level (0-1)."""
        self._attention_factor = max(0.1, min(2.0, level))

    def set_arousal(self, level: float) -> None:
        """Set arousal level (0-1)."""
        self._arousal_factor = max(0.5, min(1.5, 0.5 + level))

    def estimate_duration(
        self,
        actual_duration: float,
        attention: float = None,
        arousal: float = None
    ) -> TimeEstimate:
        """Estimate subjective duration."""
        with self._lock:
            if attention is not None:
                self._attention_factor = max(0.1, min(2.0, attention))
            if arousal is not None:
                self._arousal_factor = max(0.5, min(1.5, 0.5 + arousal))

            # Time flies when having fun (high attention = shorter perceived)
            # High arousal = slower perceived time

            base_rate = self._clock_rate * self._arousal_factor
            attention_mod = 1.0 / (0.5 + 0.5 * self._attention_factor)

            estimated = actual_duration * base_rate * attention_mod

            # Add noise
            noise = random.gauss(0, 0.1 * actual_duration)
            estimated += noise
            estimated = max(0, estimated)

            estimate = TimeEstimate(
                estimated_duration=estimated,
                actual_duration=actual_duration,
                ratio=estimated / actual_duration if actual_duration > 0 else 1.0,
                direction=TimeDirection.PAST  # Retrospective
            )

            self._estimates.append(estimate)
            return estimate

    def prospective_estimate(
        self,
        target_duration: float
    ) -> float:
        """Estimate how long target duration will feel."""
        with self._lock:
            # Prospective timing tends to overestimate
            overestimate = 1.1 + 0.1 * (1 - self._attention_factor)
            return target_duration * overestimate

    def get_average_ratio(self) -> float:
        """Get average estimation ratio."""
        if not self._estimates:
            return 1.0
        return sum(e.ratio for e in self._estimates) / len(self._estimates)


# ============================================================================
# TEMPORAL MEMORY
# ============================================================================

class TemporalMemory:
    """
    Memory for temporal events.

    "Ba'el remembers all times." — Ba'el
    """

    def __init__(self):
        """Initialize memory."""
        self._events: Dict[str, TemporalEvent] = {}
        self._timeline: List[str] = []  # Event IDs in chronological order

        self._event_counter = 0
        self._interval_counter = 0
        self._lock = threading.RLock()

    def _generate_event_id(self) -> str:
        self._event_counter += 1
        return f"tevent_{self._event_counter}"

    def _generate_interval_id(self) -> str:
        self._interval_counter += 1
        return f"interval_{self._interval_counter}"

    def store_event(
        self,
        name: str,
        start_time: float,
        end_time: float,
        properties: Dict[str, Any] = None
    ) -> TemporalEvent:
        """Store temporal event."""
        with self._lock:
            interval = TimeInterval(
                id=self._generate_interval_id(),
                start=TimePoint(start_time),
                end=TimePoint(end_time)
            )

            event = TemporalEvent(
                id=self._generate_event_id(),
                name=name,
                interval=interval,
                properties=properties or {}
            )

            self._events[event.id] = event

            # Insert in timeline (sorted by start time)
            inserted = False
            for i, eid in enumerate(self._timeline):
                if self._events[eid].interval.start.timestamp > start_time:
                    self._timeline.insert(i, event.id)
                    inserted = True
                    break

            if not inserted:
                self._timeline.append(event.id)

            return event

    def get_event(self, event_id: str) -> Optional[TemporalEvent]:
        """Get event by ID."""
        return self._events.get(event_id)

    def get_events_in_range(
        self,
        start_time: float,
        end_time: float
    ) -> List[TemporalEvent]:
        """Get events in time range."""
        with self._lock:
            results = []

            for eid in self._timeline:
                event = self._events[eid]
                if (event.interval.end.timestamp >= start_time and
                    event.interval.start.timestamp <= end_time):
                    results.append(event)

            return results

    def get_events_before(
        self,
        timestamp: float,
        limit: int = 10
    ) -> List[TemporalEvent]:
        """Get events before timestamp."""
        with self._lock:
            results = []

            for eid in reversed(self._timeline):
                event = self._events[eid]
                if event.interval.end.timestamp < timestamp:
                    results.append(event)
                    if len(results) >= limit:
                        break

            return results

    def get_events_after(
        self,
        timestamp: float,
        limit: int = 10
    ) -> List[TemporalEvent]:
        """Get events after timestamp."""
        with self._lock:
            results = []

            for eid in self._timeline:
                event = self._events[eid]
                if event.interval.start.timestamp > timestamp:
                    results.append(event)
                    if len(results) >= limit:
                        break

            return results


# ============================================================================
# TEMPORAL PREDICTOR
# ============================================================================

class TemporalPredictor:
    """
    Predict future temporal events.

    "Ba'el foresees timing." — Ba'el
    """

    def __init__(self, memory: TemporalMemory):
        """Initialize predictor."""
        self._memory = memory
        self._patterns: Dict[str, TemporalPattern] = {}
        self._lock = threading.RLock()

    def learn_pattern(
        self,
        event_names: List[str],
        intervals: List[float]
    ) -> TemporalPattern:
        """Learn temporal pattern from events."""
        with self._lock:
            pattern_id = f"pattern_{len(self._patterns)}"

            relations = []
            for i in range(len(event_names) - 1):
                relations.append((
                    event_names[i],
                    TemporalRelation.BEFORE,
                    event_names[i + 1]
                ))

            pattern = TemporalPattern(
                id=pattern_id,
                name=f"Pattern {len(self._patterns)}",
                events=event_names,
                relations=relations
            )

            self._patterns[pattern_id] = pattern
            return pattern

    def predict_next(
        self,
        current_event: str,
        current_time: float
    ) -> Optional[TemporalPrediction]:
        """Predict next event based on patterns."""
        with self._lock:
            for pattern in self._patterns.values():
                if current_event in pattern.events:
                    idx = pattern.events.index(current_event)
                    if idx < len(pattern.events) - 1:
                        next_event = pattern.events[idx + 1]

                        # Estimate time based on historical intervals
                        events = self._memory.get_events_in_range(
                            current_time - 3600, current_time
                        )

                        avg_interval = 60.0  # Default
                        if len(events) >= 2:
                            intervals = []
                            for i in range(len(events) - 1):
                                diff = (events[i + 1].interval.start.timestamp -
                                       events[i].interval.start.timestamp)
                                intervals.append(diff)
                            avg_interval = sum(intervals) / len(intervals)

                        return TemporalPrediction(
                            event_name=next_event,
                            predicted_time=current_time + avg_interval,
                            confidence=0.6,
                            basis=f"Pattern: {pattern.name}"
                        )

            return None


# ============================================================================
# TEMPORAL COGNITION ENGINE
# ============================================================================

class TemporalCognitionEngine:
    """
    Complete temporal cognition engine.

    "Ba'el's temporal mind." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._reasoner = IntervalReasoner()
        self._perception = TimePerception()
        self._memory = TemporalMemory()
        self._predictor = TemporalPredictor(self._memory)

        self._current_time = time.time()
        self._lock = threading.RLock()

    # Time perception

    def estimate_duration(
        self,
        actual_duration: float,
        attention: float = 0.5
    ) -> TimeEstimate:
        """Estimate subjective duration."""
        return self._perception.estimate_duration(actual_duration, attention)

    def set_attention(self, level: float) -> None:
        """Set attention level."""
        self._perception.set_attention(level)

    # Interval reasoning

    def compute_relation(
        self,
        interval_a: TimeInterval,
        interval_b: TimeInterval
    ) -> TemporalRelation:
        """Compute temporal relation."""
        return self._reasoner.compute_relation(interval_a, interval_b)

    def create_interval(
        self,
        start: float,
        end: float,
        label: str = None
    ) -> TimeInterval:
        """Create time interval."""
        return TimeInterval(
            id=f"int_{int(start)}_{int(end)}",
            start=TimePoint(start),
            end=TimePoint(end),
            label=label
        )

    # Event memory

    def store_event(
        self,
        name: str,
        start_time: float,
        duration: float,
        properties: Dict[str, Any] = None
    ) -> TemporalEvent:
        """Store event."""
        return self._memory.store_event(
            name, start_time, start_time + duration, properties
        )

    def get_recent_events(
        self,
        limit: int = 10
    ) -> List[TemporalEvent]:
        """Get recent events."""
        return self._memory.get_events_before(time.time(), limit)

    def get_events_in_range(
        self,
        start: float,
        end: float
    ) -> List[TemporalEvent]:
        """Get events in range."""
        return self._memory.get_events_in_range(start, end)

    # Prediction

    def learn_pattern(
        self,
        event_names: List[str]
    ) -> TemporalPattern:
        """Learn temporal pattern."""
        return self._predictor.learn_pattern(event_names, [])

    def predict_next(
        self,
        current_event: str
    ) -> Optional[TemporalPrediction]:
        """Predict next event."""
        return self._predictor.predict_next(current_event, time.time())

    # Time tracking

    def now(self) -> float:
        """Get current time."""
        return time.time()

    def elapsed_since(self, timestamp: float) -> float:
        """Get elapsed time since timestamp."""
        return time.time() - timestamp

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'events': len(self._memory._events),
            'patterns': len(self._predictor._patterns),
            'average_time_ratio': self._perception.get_average_ratio()
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_temporal_cognition_engine() -> TemporalCognitionEngine:
    """Create temporal cognition engine."""
    return TemporalCognitionEngine()


def compute_temporal_relation(
    start1: float, end1: float,
    start2: float, end2: float
) -> str:
    """Compute temporal relation between two intervals."""
    engine = create_temporal_cognition_engine()
    int_a = engine.create_interval(start1, end1)
    int_b = engine.create_interval(start2, end2)
    return engine.compute_relation(int_a, int_b).name
