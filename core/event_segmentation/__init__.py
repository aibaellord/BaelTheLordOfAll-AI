"""
BAEL Event Segmentation Engine
===============================

Segmenting continuous experience into events.
Zacks & Tversky's Event Segmentation Theory.

"Ba'el divides the stream of time." — Ba'el
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

logger = logging.getLogger("BAEL.EventSegmentation")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class GranularityLevel(Enum):
    """Event granularity levels."""
    FINE = auto()      # Small, brief events
    MEDIUM = auto()    # Standard events
    COARSE = auto()    # Large, extended events
    HIERARCHICAL = auto()  # Nested levels


class BoundaryType(Enum):
    """Types of event boundaries."""
    GOAL_CHANGE = auto()       # Change in goal
    LOCATION_CHANGE = auto()   # Change in location
    ACTOR_CHANGE = auto()      # Change in actors
    OBJECT_CHANGE = auto()     # Change in objects
    TIME_JUMP = auto()         # Discontinuity in time
    CAUSAL_BREAK = auto()      # Break in causal chain
    PREDICTION_ERROR = auto()  # Unexpected change


class EventModel(Enum):
    """Types of event models."""
    SCRIPT = auto()      # Expected sequence
    SCHEMA = auto()      # General structure
    SITUATION = auto()   # Current situation model


@dataclass
class Moment:
    """
    A moment in the experience stream.
    """
    id: str
    timestamp: float
    features: Dict[str, Any]

    @property
    def feature_vector(self) -> List[float]:
        return [float(v) for v in self.features.values() if isinstance(v, (int, float))]


@dataclass
class EventBoundary:
    """
    A boundary between events.
    """
    id: str
    position: int  # Index in moment stream
    timestamp: float
    boundary_type: BoundaryType
    strength: float  # 0-1, how strong the boundary
    features: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Event:
    """
    A segmented event.
    """
    id: str
    start_index: int
    end_index: int
    start_time: float
    end_time: float
    moments: List[Moment]
    label: Optional[str] = None
    granularity: GranularityLevel = GranularityLevel.MEDIUM
    parent_event_id: Optional[str] = None
    child_event_ids: List[str] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

    @property
    def size(self) -> int:
        return len(self.moments)


@dataclass
class PredictionState:
    """
    Current prediction about ongoing event.
    """
    expected_features: Dict[str, float]
    confidence: float
    event_model: EventModel
    steps_since_update: int = 0


@dataclass
class SegmentationResult:
    """
    Result of event segmentation.
    """
    events: List[Event]
    boundaries: List[EventBoundary]
    total_moments: int
    average_event_duration: float


# ============================================================================
# PREDICTION ERROR MONITOR
# ============================================================================

class PredictionErrorMonitor:
    """
    Monitor prediction errors for boundary detection.

    "Ba'el detects the unexpected." — Ba'el
    """

    def __init__(
        self,
        error_threshold: float = 0.3,
        learning_rate: float = 0.1
    ):
        """Initialize monitor."""
        self._threshold = error_threshold
        self._learning_rate = learning_rate

        # Current prediction model
        self._prediction = PredictionState(
            expected_features={},
            confidence=0.5,
            event_model=EventModel.SITUATION
        )

        self._error_history: deque = deque(maxlen=100)
        self._lock = threading.RLock()

    def update_prediction(
        self,
        moment: Moment
    ) -> None:
        """Update prediction model with new moment."""
        with self._lock:
            # Blend current features into prediction
            for key, value in moment.features.items():
                if isinstance(value, (int, float)):
                    current = self._prediction.expected_features.get(key, value)
                    updated = current * (1 - self._learning_rate) + value * self._learning_rate
                    self._prediction.expected_features[key] = updated

            self._prediction.steps_since_update = 0

    def compute_error(
        self,
        moment: Moment
    ) -> float:
        """Compute prediction error for moment."""
        with self._lock:
            if not self._prediction.expected_features:
                return 0.0

            errors = []
            for key, expected in self._prediction.expected_features.items():
                actual = moment.features.get(key)
                if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
                    # Normalize error
                    if abs(expected) > 0.001:
                        error = abs(actual - expected) / max(1.0, abs(expected))
                    else:
                        error = abs(actual - expected)
                    errors.append(min(1.0, error))

            if not errors:
                return 0.0

            mean_error = sum(errors) / len(errors)
            self._error_history.append(mean_error)

            self._prediction.steps_since_update += 1

            return mean_error

    def is_boundary(
        self,
        moment: Moment
    ) -> Tuple[bool, float]:
        """Check if moment represents event boundary."""
        with self._lock:
            error = self.compute_error(moment)

            # Adaptive threshold based on history
            if len(self._error_history) > 10:
                mean = sum(self._error_history) / len(self._error_history)
                std = math.sqrt(
                    sum((e - mean) ** 2 for e in self._error_history) / len(self._error_history)
                )
                adaptive_threshold = mean + 2 * std
            else:
                adaptive_threshold = self._threshold

            is_bound = error > adaptive_threshold

            return is_bound, error

    def reset(self) -> None:
        """Reset prediction model for new event."""
        self._prediction = PredictionState(
            expected_features={},
            confidence=0.5,
            event_model=EventModel.SITUATION
        )


# ============================================================================
# FEATURE CHANGE DETECTOR
# ============================================================================

class FeatureChangeDetector:
    """
    Detect changes in features for boundary detection.

    "Ba'el senses change." — Ba'el
    """

    def __init__(
        self,
        change_threshold: float = 0.4
    ):
        """Initialize detector."""
        self._threshold = change_threshold
        self._previous_moment: Optional[Moment] = None
        self._lock = threading.RLock()

    def detect_changes(
        self,
        moment: Moment
    ) -> Dict[BoundaryType, float]:
        """Detect feature changes."""
        with self._lock:
            changes = {}

            if self._previous_moment is None:
                self._previous_moment = moment
                return changes

            prev = self._previous_moment.features
            curr = moment.features

            # Check goal change
            if 'goal' in prev or 'goal' in curr:
                if prev.get('goal') != curr.get('goal'):
                    changes[BoundaryType.GOAL_CHANGE] = 0.8

            # Check location change
            if 'location' in prev or 'location' in curr:
                if prev.get('location') != curr.get('location'):
                    changes[BoundaryType.LOCATION_CHANGE] = 0.7

            # Check actor change
            if 'actor' in prev or 'actor' in curr:
                if prev.get('actor') != curr.get('actor'):
                    changes[BoundaryType.ACTOR_CHANGE] = 0.6

            # Check object change
            if 'object' in prev or 'object' in curr:
                if prev.get('object') != curr.get('object'):
                    changes[BoundaryType.OBJECT_CHANGE] = 0.5

            # Check time jump
            time_diff = moment.timestamp - self._previous_moment.timestamp
            if time_diff > 10.0:  # Arbitrary threshold
                changes[BoundaryType.TIME_JUMP] = min(1.0, time_diff / 60.0)

            # General feature distance
            dist = self._compute_distance(prev, curr)
            if dist > self._threshold:
                if BoundaryType.PREDICTION_ERROR not in changes:
                    changes[BoundaryType.PREDICTION_ERROR] = dist

            self._previous_moment = moment

            return changes

    def _compute_distance(
        self,
        features1: Dict[str, Any],
        features2: Dict[str, Any]
    ) -> float:
        """Compute distance between feature sets."""
        all_keys = set(features1.keys()) | set(features2.keys())

        if not all_keys:
            return 0.0

        differences = 0
        numeric_diffs = []

        for key in all_keys:
            v1 = features1.get(key)
            v2 = features2.get(key)

            if v1 is None or v2 is None:
                differences += 1
            elif isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                if abs(v1) > 0.001:
                    diff = abs(v1 - v2) / max(1.0, abs(v1))
                else:
                    diff = abs(v1 - v2)
                numeric_diffs.append(min(1.0, diff))
            elif v1 != v2:
                differences += 1

        categorical_dist = differences / len(all_keys)
        numeric_dist = sum(numeric_diffs) / len(numeric_diffs) if numeric_diffs else 0.0

        return (categorical_dist + numeric_dist) / 2

    def reset(self) -> None:
        """Reset detector."""
        self._previous_moment = None


# ============================================================================
# HIERARCHICAL SEGMENTER
# ============================================================================

class HierarchicalSegmenter:
    """
    Hierarchical event segmentation.

    "Ba'el sees events within events." — Ba'el
    """

    def __init__(self):
        """Initialize segmenter."""
        self._event_counter = 0
        self._boundary_counter = 0
        self._lock = threading.RLock()

    def _generate_event_id(self) -> str:
        self._event_counter += 1
        return f"event_{self._event_counter}"

    def _generate_boundary_id(self) -> str:
        self._boundary_counter += 1
        return f"boundary_{self._boundary_counter}"

    def segment_at_granularity(
        self,
        moments: List[Moment],
        boundaries: List[EventBoundary],
        granularity: GranularityLevel
    ) -> List[Event]:
        """Segment at specific granularity."""
        with self._lock:
            # Filter boundaries by strength for granularity
            if granularity == GranularityLevel.FINE:
                min_strength = 0.3
            elif granularity == GranularityLevel.MEDIUM:
                min_strength = 0.5
            elif granularity == GranularityLevel.COARSE:
                min_strength = 0.7
            else:
                min_strength = 0.5

            filtered = [b for b in boundaries if b.strength >= min_strength]

            return self._create_events(moments, filtered, granularity)

    def _create_events(
        self,
        moments: List[Moment],
        boundaries: List[EventBoundary],
        granularity: GranularityLevel
    ) -> List[Event]:
        """Create events from moments and boundaries."""
        if not moments:
            return []

        events = []
        boundary_positions = sorted([b.position for b in boundaries])

        # Add implicit boundaries at start and end
        if 0 not in boundary_positions:
            boundary_positions.insert(0, 0)
        if len(moments) not in boundary_positions:
            boundary_positions.append(len(moments))

        # Create events between boundaries
        for i in range(len(boundary_positions) - 1):
            start_idx = boundary_positions[i]
            end_idx = boundary_positions[i + 1]

            if start_idx >= end_idx:
                continue

            event_moments = moments[start_idx:end_idx]

            event = Event(
                id=self._generate_event_id(),
                start_index=start_idx,
                end_index=end_idx,
                start_time=event_moments[0].timestamp,
                end_time=event_moments[-1].timestamp,
                moments=event_moments,
                granularity=granularity
            )

            events.append(event)

        return events

    def create_hierarchy(
        self,
        moments: List[Moment],
        boundaries: List[EventBoundary]
    ) -> List[Event]:
        """Create hierarchical event structure."""
        with self._lock:
            # Segment at each granularity
            fine = self.segment_at_granularity(moments, boundaries, GranularityLevel.FINE)
            medium = self.segment_at_granularity(moments, boundaries, GranularityLevel.MEDIUM)
            coarse = self.segment_at_granularity(moments, boundaries, GranularityLevel.COARSE)

            # Link hierarchy
            for med_event in medium:
                for fine_event in fine:
                    if (fine_event.start_index >= med_event.start_index and
                        fine_event.end_index <= med_event.end_index):
                        fine_event.parent_event_id = med_event.id
                        med_event.child_event_ids.append(fine_event.id)

            for coarse_event in coarse:
                for med_event in medium:
                    if (med_event.start_index >= coarse_event.start_index and
                        med_event.end_index <= coarse_event.end_index):
                        med_event.parent_event_id = coarse_event.id
                        coarse_event.child_event_ids.append(med_event.id)

            return fine + medium + coarse


# ============================================================================
# EVENT SEGMENTATION ENGINE
# ============================================================================

class EventSegmentationEngine:
    """
    Complete event segmentation engine.

    "Ba'el parses experience." — Ba'el
    """

    def __init__(
        self,
        error_threshold: float = 0.3,
        change_threshold: float = 0.4
    ):
        """Initialize engine."""
        self._error_monitor = PredictionErrorMonitor(error_threshold)
        self._change_detector = FeatureChangeDetector(change_threshold)
        self._segmenter = HierarchicalSegmenter()

        self._moments: List[Moment] = []
        self._boundaries: List[EventBoundary] = []
        self._events: List[Event] = []

        self._moment_counter = 0
        self._boundary_counter = 0
        self._lock = threading.RLock()

    def _generate_moment_id(self) -> str:
        self._moment_counter += 1
        return f"moment_{self._moment_counter}"

    def _generate_boundary_id(self) -> str:
        self._boundary_counter += 1
        return f"boundary_{self._boundary_counter}"

    def process_moment(
        self,
        features: Dict[str, Any],
        timestamp: float = None
    ) -> Optional[EventBoundary]:
        """Process new moment, check for boundary."""
        with self._lock:
            if timestamp is None:
                timestamp = time.time()

            moment = Moment(
                id=self._generate_moment_id(),
                timestamp=timestamp,
                features=features
            )

            # Check for boundary
            is_error_boundary, error_strength = self._error_monitor.is_boundary(moment)
            feature_changes = self._change_detector.detect_changes(moment)

            boundary = None

            if is_error_boundary or feature_changes:
                # Determine strongest boundary type
                if feature_changes:
                    strongest_type = max(feature_changes, key=feature_changes.get)
                    strength = feature_changes[strongest_type]
                else:
                    strongest_type = BoundaryType.PREDICTION_ERROR
                    strength = error_strength

                boundary = EventBoundary(
                    id=self._generate_boundary_id(),
                    position=len(self._moments),
                    timestamp=timestamp,
                    boundary_type=strongest_type,
                    strength=strength,
                    features=features
                )

                self._boundaries.append(boundary)

                # Reset prediction model for new event
                self._error_monitor.reset()

            # Update prediction model
            self._error_monitor.update_prediction(moment)

            self._moments.append(moment)

            return boundary

    def segment(
        self,
        granularity: GranularityLevel = GranularityLevel.MEDIUM
    ) -> SegmentationResult:
        """Segment current moments into events."""
        with self._lock:
            events = self._segmenter.segment_at_granularity(
                self._moments, self._boundaries, granularity
            )

            self._events = events

            avg_duration = 0.0
            if events:
                avg_duration = sum(e.duration for e in events) / len(events)

            return SegmentationResult(
                events=events,
                boundaries=self._boundaries.copy(),
                total_moments=len(self._moments),
                average_event_duration=avg_duration
            )

    def segment_hierarchical(self) -> List[Event]:
        """Create hierarchical segmentation."""
        with self._lock:
            return self._segmenter.create_hierarchy(self._moments, self._boundaries)

    def get_current_event(self) -> Optional[Event]:
        """Get the current (most recent) event."""
        if self._events:
            return self._events[-1]
        return None

    def get_events_in_range(
        self,
        start_time: float,
        end_time: float
    ) -> List[Event]:
        """Get events in time range."""
        return [
            e for e in self._events
            if e.end_time >= start_time and e.start_time <= end_time
        ]

    def label_event(
        self,
        event_id: str,
        label: str
    ) -> None:
        """Label an event."""
        for event in self._events:
            if event.id == event_id:
                event.label = label
                break

    def clear(self) -> None:
        """Clear all data."""
        self._moments.clear()
        self._boundaries.clear()
        self._events.clear()
        self._error_monitor.reset()
        self._change_detector.reset()

    @property
    def moment_count(self) -> int:
        return len(self._moments)

    @property
    def boundary_count(self) -> int:
        return len(self._boundaries)

    @property
    def event_count(self) -> int:
        return len(self._events)

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'moments': len(self._moments),
            'boundaries': len(self._boundaries),
            'events': len(self._events)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_event_segmentation_engine() -> EventSegmentationEngine:
    """Create event segmentation engine."""
    return EventSegmentationEngine()


def segment_sequence(
    feature_sequence: List[Dict[str, Any]]
) -> SegmentationResult:
    """Segment a sequence of features."""
    engine = create_event_segmentation_engine()

    for i, features in enumerate(feature_sequence):
        engine.process_moment(features, timestamp=float(i))

    return engine.segment()
