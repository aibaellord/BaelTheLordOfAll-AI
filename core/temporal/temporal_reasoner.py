#!/usr/bin/env python3
"""
BAEL - Temporal Reasoner
Advanced temporal reasoning and time-based inference.

Features:
- Temporal logic (Allen's interval algebra)
- Time series analysis
- Event ordering
- Temporal constraints
- Duration reasoning
- Timeline management
- Temporal query processing
- Time-aware planning
"""

import asyncio
import hashlib
import heapq
import math
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class TemporalRelation(Enum):
    """Allen's interval algebra relations."""
    BEFORE = "before"           # A ends before B starts
    AFTER = "after"             # A starts after B ends
    MEETS = "meets"             # A ends when B starts
    MET_BY = "met_by"           # A starts when B ends
    OVERLAPS = "overlaps"       # A starts before B, ends during B
    OVERLAPPED_BY = "overlapped_by"  # B starts before A, ends during A
    STARTS = "starts"           # A and B start together, A ends first
    STARTED_BY = "started_by"   # A and B start together, B ends first
    DURING = "during"           # A is contained within B
    CONTAINS = "contains"       # B is contained within A
    FINISHES = "finishes"       # A ends when B ends, A starts after B
    FINISHED_BY = "finished_by" # A ends when B ends, B starts after A
    EQUALS = "equals"           # A and B have same start and end


class TimeUnit(Enum):
    """Time units."""
    MILLISECOND = "millisecond"
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


class ConstraintSatisfaction(Enum):
    """Constraint satisfaction status."""
    SATISFIED = "satisfied"
    VIOLATED = "violated"
    UNKNOWN = "unknown"


class EventType(Enum):
    """Types of temporal events."""
    INSTANT = "instant"
    INTERVAL = "interval"
    RECURRING = "recurring"
    DURATION = "duration"


class TemporalQueryType(Enum):
    """Types of temporal queries."""
    POINT_QUERY = "point_query"
    RANGE_QUERY = "range_query"
    RELATION_QUERY = "relation_query"
    SEQUENCE_QUERY = "sequence_query"
    PATTERN_QUERY = "pattern_query"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class TimePoint:
    """A point in time."""
    point_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = 0.0  # Unix timestamp
    label: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_datetime(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp)

    @staticmethod
    def from_datetime(dt: datetime, label: str = "") -> 'TimePoint':
        return TimePoint(timestamp=dt.timestamp(), label=label)

    def __lt__(self, other: 'TimePoint') -> bool:
        return self.timestamp < other.timestamp

    def __le__(self, other: 'TimePoint') -> bool:
        return self.timestamp <= other.timestamp

    def __eq__(self, other: object) -> bool:
        if isinstance(other, TimePoint):
            return self.timestamp == other.timestamp
        return False


@dataclass
class TimeInterval:
    """A time interval."""
    interval_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    start: float = 0.0
    end: float = 0.0
    label: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        return self.end - self.start

    def contains_point(self, point: float) -> bool:
        return self.start <= point <= self.end

    def contains_interval(self, other: 'TimeInterval') -> bool:
        return self.start <= other.start and self.end >= other.end


@dataclass
class TemporalEvent:
    """A temporal event."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = EventType.INSTANT
    name: str = ""
    description: str = ""
    start_time: float = 0.0
    end_time: Optional[float] = None
    recurrence_pattern: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TemporalConstraint:
    """A temporal constraint."""
    constraint_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str = ""
    target_id: str = ""
    relation: TemporalRelation = TemporalRelation.BEFORE
    min_gap: Optional[float] = None
    max_gap: Optional[float] = None
    priority: int = 1


@dataclass
class Timeline:
    """A timeline of events."""
    timeline_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    events: List[str] = field(default_factory=list)  # Event IDs
    start_time: float = 0.0
    end_time: float = 0.0
    resolution: TimeUnit = TimeUnit.SECOND


@dataclass
class TemporalQueryResult:
    """Result of a temporal query."""
    query_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query_type: TemporalQueryType = TemporalQueryType.POINT_QUERY
    results: List[Any] = field(default_factory=list)
    count: int = 0
    execution_time: float = 0.0


# =============================================================================
# ALLEN'S INTERVAL ALGEBRA
# =============================================================================

class AllenAlgebra:
    """Allen's interval algebra for temporal reasoning."""

    @staticmethod
    def compute_relation(
        a: TimeInterval,
        b: TimeInterval,
        epsilon: float = 1e-9
    ) -> TemporalRelation:
        """Compute Allen's relation between two intervals."""
        # Handle equals
        if abs(a.start - b.start) < epsilon and abs(a.end - b.end) < epsilon:
            return TemporalRelation.EQUALS

        # Before/After
        if a.end < b.start - epsilon:
            return TemporalRelation.BEFORE
        if a.start > b.end + epsilon:
            return TemporalRelation.AFTER

        # Meets/Met by
        if abs(a.end - b.start) < epsilon:
            return TemporalRelation.MEETS
        if abs(a.start - b.end) < epsilon:
            return TemporalRelation.MET_BY

        # Starts/Started by
        if abs(a.start - b.start) < epsilon:
            if a.end < b.end - epsilon:
                return TemporalRelation.STARTS
            else:
                return TemporalRelation.STARTED_BY

        # Finishes/Finished by
        if abs(a.end - b.end) < epsilon:
            if a.start > b.start + epsilon:
                return TemporalRelation.FINISHES
            else:
                return TemporalRelation.FINISHED_BY

        # During/Contains
        if a.start > b.start + epsilon and a.end < b.end - epsilon:
            return TemporalRelation.DURING
        if a.start < b.start - epsilon and a.end > b.end + epsilon:
            return TemporalRelation.CONTAINS

        # Overlaps/Overlapped by
        if a.start < b.start and a.end > b.start and a.end < b.end:
            return TemporalRelation.OVERLAPS
        if b.start < a.start and b.end > a.start and b.end < a.end:
            return TemporalRelation.OVERLAPPED_BY

        # Default
        return TemporalRelation.OVERLAPS

    @staticmethod
    def inverse(relation: TemporalRelation) -> TemporalRelation:
        """Get inverse of a relation."""
        inverses = {
            TemporalRelation.BEFORE: TemporalRelation.AFTER,
            TemporalRelation.AFTER: TemporalRelation.BEFORE,
            TemporalRelation.MEETS: TemporalRelation.MET_BY,
            TemporalRelation.MET_BY: TemporalRelation.MEETS,
            TemporalRelation.OVERLAPS: TemporalRelation.OVERLAPPED_BY,
            TemporalRelation.OVERLAPPED_BY: TemporalRelation.OVERLAPS,
            TemporalRelation.STARTS: TemporalRelation.STARTED_BY,
            TemporalRelation.STARTED_BY: TemporalRelation.STARTS,
            TemporalRelation.DURING: TemporalRelation.CONTAINS,
            TemporalRelation.CONTAINS: TemporalRelation.DURING,
            TemporalRelation.FINISHES: TemporalRelation.FINISHED_BY,
            TemporalRelation.FINISHED_BY: TemporalRelation.FINISHES,
            TemporalRelation.EQUALS: TemporalRelation.EQUALS,
        }
        return inverses.get(relation, relation)

    @staticmethod
    def is_consistent(
        a_b: TemporalRelation,
        b_c: TemporalRelation,
        a_c: TemporalRelation
    ) -> bool:
        """Check if three relations are consistent."""
        # Simplified consistency check
        # Full transitivity table would be more complex

        if a_b == TemporalRelation.BEFORE and b_c == TemporalRelation.BEFORE:
            return a_c == TemporalRelation.BEFORE

        if a_b == TemporalRelation.AFTER and b_c == TemporalRelation.AFTER:
            return a_c == TemporalRelation.AFTER

        if a_b == TemporalRelation.EQUALS:
            return b_c == a_c

        if b_c == TemporalRelation.EQUALS:
            return a_b == a_c

        # Allow other combinations (simplified)
        return True


# =============================================================================
# EVENT MANAGER
# =============================================================================

class EventManager:
    """Manage temporal events."""

    def __init__(self):
        self._events: Dict[str, TemporalEvent] = {}
        self._event_index: Dict[float, List[str]] = defaultdict(list)  # timestamp -> event IDs

    def add_event(self, event: TemporalEvent) -> None:
        """Add an event."""
        self._events[event.event_id] = event
        self._event_index[event.start_time].append(event.event_id)

        if event.end_time:
            self._event_index[event.end_time].append(event.event_id)

    def get_event(self, event_id: str) -> Optional[TemporalEvent]:
        """Get event by ID."""
        return self._events.get(event_id)

    def get_events_at(self, timestamp: float, epsilon: float = 1.0) -> List[TemporalEvent]:
        """Get events at a specific time."""
        result = []

        for event in self._events.values():
            if event.event_type == EventType.INSTANT:
                if abs(event.start_time - timestamp) <= epsilon:
                    result.append(event)
            else:
                if event.end_time:
                    if event.start_time <= timestamp <= event.end_time:
                        result.append(event)

        return result

    def get_events_in_range(
        self,
        start: float,
        end: float
    ) -> List[TemporalEvent]:
        """Get events in a time range."""
        result = []

        for event in self._events.values():
            event_end = event.end_time or event.start_time

            # Check overlap
            if event.start_time <= end and event_end >= start:
                result.append(event)

        return sorted(result, key=lambda e: e.start_time)

    def get_events_before(
        self,
        timestamp: float
    ) -> List[TemporalEvent]:
        """Get events ending before timestamp."""
        result = []

        for event in self._events.values():
            event_end = event.end_time or event.start_time
            if event_end < timestamp:
                result.append(event)

        return sorted(result, key=lambda e: e.start_time)

    def get_events_after(
        self,
        timestamp: float
    ) -> List[TemporalEvent]:
        """Get events starting after timestamp."""
        result = []

        for event in self._events.values():
            if event.start_time > timestamp:
                result.append(event)

        return sorted(result, key=lambda e: e.start_time)

    def get_ordered_events(self) -> List[TemporalEvent]:
        """Get all events in chronological order."""
        return sorted(self._events.values(), key=lambda e: e.start_time)


# =============================================================================
# CONSTRAINT NETWORK
# =============================================================================

class TemporalConstraintNetwork:
    """Network of temporal constraints."""

    def __init__(self):
        self._constraints: Dict[str, TemporalConstraint] = {}
        self._constraint_graph: Dict[str, Dict[str, str]] = defaultdict(dict)  # source -> target -> constraint_id

    def add_constraint(self, constraint: TemporalConstraint) -> None:
        """Add a constraint."""
        self._constraints[constraint.constraint_id] = constraint
        self._constraint_graph[constraint.source_id][constraint.target_id] = constraint.constraint_id

    def get_constraint(self, constraint_id: str) -> Optional[TemporalConstraint]:
        """Get constraint by ID."""
        return self._constraints.get(constraint_id)

    def get_constraints_for(self, event_id: str) -> List[TemporalConstraint]:
        """Get all constraints involving an event."""
        result = []

        # Outgoing constraints
        for target_id, constraint_id in self._constraint_graph.get(event_id, {}).items():
            constraint = self._constraints.get(constraint_id)
            if constraint:
                result.append(constraint)

        # Incoming constraints
        for source_id, targets in self._constraint_graph.items():
            if event_id in targets:
                constraint = self._constraints.get(targets[event_id])
                if constraint:
                    result.append(constraint)

        return result

    def check_constraint(
        self,
        constraint: TemporalConstraint,
        source_interval: TimeInterval,
        target_interval: TimeInterval
    ) -> ConstraintSatisfaction:
        """Check if a constraint is satisfied."""
        actual_relation = AllenAlgebra.compute_relation(source_interval, target_interval)

        if actual_relation == constraint.relation:
            # Check gap constraints if applicable
            if constraint.min_gap is not None or constraint.max_gap is not None:
                gap = target_interval.start - source_interval.end

                if constraint.min_gap is not None and gap < constraint.min_gap:
                    return ConstraintSatisfaction.VIOLATED

                if constraint.max_gap is not None and gap > constraint.max_gap:
                    return ConstraintSatisfaction.VIOLATED

            return ConstraintSatisfaction.SATISFIED

        return ConstraintSatisfaction.VIOLATED

    def propagate_constraints(
        self,
        events: Dict[str, TimeInterval]
    ) -> Dict[str, ConstraintSatisfaction]:
        """Check all constraints and propagate."""
        results = {}

        for constraint_id, constraint in self._constraints.items():
            source = events.get(constraint.source_id)
            target = events.get(constraint.target_id)

            if source and target:
                results[constraint_id] = self.check_constraint(constraint, source, target)
            else:
                results[constraint_id] = ConstraintSatisfaction.UNKNOWN

        return results


# =============================================================================
# TIME SERIES ANALYZER
# =============================================================================

class TimeSeriesAnalyzer:
    """Analyze time series data."""

    def __init__(self):
        self._series: Dict[str, List[Tuple[float, float]]] = {}  # name -> [(timestamp, value)]

    def add_series(self, name: str) -> None:
        """Add a time series."""
        self._series[name] = []

    def add_point(self, name: str, timestamp: float, value: float) -> None:
        """Add a data point to a series."""
        if name not in self._series:
            self._series[name] = []
        self._series[name].append((timestamp, value))
        self._series[name].sort(key=lambda x: x[0])

    def get_series(self, name: str) -> List[Tuple[float, float]]:
        """Get a time series."""
        return self._series.get(name, [])

    def get_value_at(
        self,
        name: str,
        timestamp: float,
        interpolate: bool = True
    ) -> Optional[float]:
        """Get value at a specific timestamp."""
        series = self._series.get(name, [])
        if not series:
            return None

        # Binary search
        left, right = 0, len(series) - 1

        while left < right:
            mid = (left + right) // 2
            if series[mid][0] < timestamp:
                left = mid + 1
            else:
                right = mid

        if series[left][0] == timestamp:
            return series[left][1]

        if not interpolate:
            return None

        # Linear interpolation
        if left == 0:
            return series[0][1]

        t0, v0 = series[left - 1]
        t1, v1 = series[left]

        if t1 == t0:
            return v0

        alpha = (timestamp - t0) / (t1 - t0)
        return v0 + alpha * (v1 - v0)

    def get_range(
        self,
        name: str,
        start: float,
        end: float
    ) -> List[Tuple[float, float]]:
        """Get values in a time range."""
        series = self._series.get(name, [])
        return [(t, v) for t, v in series if start <= t <= end]

    def compute_statistics(
        self,
        name: str,
        start: Optional[float] = None,
        end: Optional[float] = None
    ) -> Dict[str, float]:
        """Compute statistics for a series."""
        series = self._series.get(name, [])

        if start is not None or end is not None:
            series = [
                (t, v) for t, v in series
                if (start is None or t >= start) and (end is None or t <= end)
            ]

        if not series:
            return {}

        values = [v for _, v in series]
        n = len(values)

        mean = sum(values) / n
        variance = sum((v - mean) ** 2 for v in values) / n
        std_dev = math.sqrt(variance)

        sorted_values = sorted(values)
        median = sorted_values[n // 2] if n % 2 else (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2

        return {
            "count": n,
            "min": min(values),
            "max": max(values),
            "mean": mean,
            "median": median,
            "std_dev": std_dev,
            "variance": variance
        }

    def detect_trend(
        self,
        name: str,
        window_size: int = 5
    ) -> str:
        """Detect trend in series."""
        series = self._series.get(name, [])

        if len(series) < window_size:
            return "insufficient_data"

        # Compare moving averages
        values = [v for _, v in series]

        early_avg = sum(values[:window_size]) / window_size
        late_avg = sum(values[-window_size:]) / window_size

        diff = late_avg - early_avg
        threshold = abs(early_avg) * 0.1  # 10% threshold

        if diff > threshold:
            return "increasing"
        elif diff < -threshold:
            return "decreasing"
        else:
            return "stable"


# =============================================================================
# TIMELINE MANAGER
# =============================================================================

class TimelineManager:
    """Manage multiple timelines."""

    def __init__(self, event_manager: EventManager):
        self._event_manager = event_manager
        self._timelines: Dict[str, Timeline] = {}

    def create_timeline(
        self,
        name: str,
        resolution: TimeUnit = TimeUnit.SECOND
    ) -> Timeline:
        """Create a new timeline."""
        timeline = Timeline(
            name=name,
            resolution=resolution
        )
        self._timelines[timeline.timeline_id] = timeline
        return timeline

    def get_timeline(self, timeline_id: str) -> Optional[Timeline]:
        """Get timeline by ID."""
        return self._timelines.get(timeline_id)

    def add_event_to_timeline(
        self,
        timeline_id: str,
        event_id: str
    ) -> bool:
        """Add event to timeline."""
        timeline = self._timelines.get(timeline_id)
        event = self._event_manager.get_event(event_id)

        if not timeline or not event:
            return False

        timeline.events.append(event_id)

        # Update timeline bounds
        if not timeline.events or event.start_time < timeline.start_time:
            timeline.start_time = event.start_time

        event_end = event.end_time or event.start_time
        if event_end > timeline.end_time:
            timeline.end_time = event_end

        return True

    def get_timeline_events(
        self,
        timeline_id: str
    ) -> List[TemporalEvent]:
        """Get all events in timeline order."""
        timeline = self._timelines.get(timeline_id)
        if not timeline:
            return []

        events = [
            self._event_manager.get_event(eid)
            for eid in timeline.events
        ]
        events = [e for e in events if e is not None]
        return sorted(events, key=lambda e: e.start_time)

    def merge_timelines(
        self,
        timeline_ids: List[str],
        new_name: str
    ) -> Optional[Timeline]:
        """Merge multiple timelines."""
        merged = Timeline(name=new_name)

        all_events = []
        for tid in timeline_ids:
            timeline = self._timelines.get(tid)
            if timeline:
                all_events.extend(timeline.events)

        # Remove duplicates
        merged.events = list(set(all_events))

        # Update bounds
        for event_id in merged.events:
            event = self._event_manager.get_event(event_id)
            if event:
                if not merged.start_time or event.start_time < merged.start_time:
                    merged.start_time = event.start_time
                event_end = event.end_time or event.start_time
                if event_end > merged.end_time:
                    merged.end_time = event_end

        self._timelines[merged.timeline_id] = merged
        return merged


# =============================================================================
# TEMPORAL QUERY PROCESSOR
# =============================================================================

class TemporalQueryProcessor:
    """Process temporal queries."""

    def __init__(
        self,
        event_manager: EventManager,
        constraint_network: TemporalConstraintNetwork
    ):
        self._event_manager = event_manager
        self._constraint_network = constraint_network

    def query_point(self, timestamp: float) -> TemporalQueryResult:
        """Query events at a point in time."""
        start = time.time()
        events = self._event_manager.get_events_at(timestamp)

        return TemporalQueryResult(
            query_type=TemporalQueryType.POINT_QUERY,
            results=[e.event_id for e in events],
            count=len(events),
            execution_time=time.time() - start
        )

    def query_range(
        self,
        start_time: float,
        end_time: float
    ) -> TemporalQueryResult:
        """Query events in a range."""
        start = time.time()
        events = self._event_manager.get_events_in_range(start_time, end_time)

        return TemporalQueryResult(
            query_type=TemporalQueryType.RANGE_QUERY,
            results=[e.event_id for e in events],
            count=len(events),
            execution_time=time.time() - start
        )

    def query_relation(
        self,
        event_id: str,
        relation: TemporalRelation
    ) -> TemporalQueryResult:
        """Query events with a specific relation to given event."""
        start = time.time()

        source_event = self._event_manager.get_event(event_id)
        if not source_event:
            return TemporalQueryResult(count=0, execution_time=time.time() - start)

        source_interval = TimeInterval(
            start=source_event.start_time,
            end=source_event.end_time or source_event.start_time
        )

        results = []

        for event in self._event_manager._events.values():
            if event.event_id == event_id:
                continue

            target_interval = TimeInterval(
                start=event.start_time,
                end=event.end_time or event.start_time
            )

            computed_relation = AllenAlgebra.compute_relation(
                source_interval,
                target_interval
            )

            if computed_relation == relation:
                results.append(event.event_id)

        return TemporalQueryResult(
            query_type=TemporalQueryType.RELATION_QUERY,
            results=results,
            count=len(results),
            execution_time=time.time() - start
        )

    def query_sequence(
        self,
        event_names: List[str]
    ) -> TemporalQueryResult:
        """Query if events occur in sequence."""
        start = time.time()

        # Find events by name
        events_by_name = {}
        for event in self._event_manager._events.values():
            if event.name in event_names:
                events_by_name[event.name] = event

        # Check sequence
        in_sequence = True
        last_end = float('-inf')

        for name in event_names:
            event = events_by_name.get(name)
            if not event:
                in_sequence = False
                break

            if event.start_time < last_end:
                in_sequence = False
                break

            last_end = event.end_time or event.start_time

        return TemporalQueryResult(
            query_type=TemporalQueryType.SEQUENCE_QUERY,
            results=[in_sequence],
            count=1 if in_sequence else 0,
            execution_time=time.time() - start
        )


# =============================================================================
# TEMPORAL REASONER
# =============================================================================

class TemporalReasoner:
    """
    Temporal Reasoner for BAEL.

    Advanced temporal reasoning and time-based inference.
    """

    def __init__(self):
        self._event_manager = EventManager()
        self._constraint_network = TemporalConstraintNetwork()
        self._time_series = TimeSeriesAnalyzer()
        self._timeline_manager = TimelineManager(self._event_manager)
        self._query_processor = TemporalQueryProcessor(
            self._event_manager,
            self._constraint_network
        )
        self._allen = AllenAlgebra()

    # -------------------------------------------------------------------------
    # EVENT MANAGEMENT
    # -------------------------------------------------------------------------

    def create_event(
        self,
        name: str,
        event_type: EventType = EventType.INSTANT,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        properties: Optional[Dict[str, Any]] = None
    ) -> TemporalEvent:
        """Create a temporal event."""
        event = TemporalEvent(
            name=name,
            event_type=event_type,
            start_time=start_time or time.time(),
            end_time=end_time,
            properties=properties or {}
        )
        self._event_manager.add_event(event)
        return event

    def get_event(self, event_id: str) -> Optional[TemporalEvent]:
        """Get event by ID."""
        return self._event_manager.get_event(event_id)

    def get_events_at(self, timestamp: float) -> List[TemporalEvent]:
        """Get events at a specific time."""
        return self._event_manager.get_events_at(timestamp)

    def get_events_in_range(
        self,
        start: float,
        end: float
    ) -> List[TemporalEvent]:
        """Get events in a time range."""
        return self._event_manager.get_events_in_range(start, end)

    # -------------------------------------------------------------------------
    # TEMPORAL RELATIONS
    # -------------------------------------------------------------------------

    def compute_relation(
        self,
        event1_id: str,
        event2_id: str
    ) -> Optional[TemporalRelation]:
        """Compute temporal relation between two events."""
        e1 = self._event_manager.get_event(event1_id)
        e2 = self._event_manager.get_event(event2_id)

        if not e1 or not e2:
            return None

        interval1 = TimeInterval(
            start=e1.start_time,
            end=e1.end_time or e1.start_time
        )
        interval2 = TimeInterval(
            start=e2.start_time,
            end=e2.end_time or e2.start_time
        )

        return AllenAlgebra.compute_relation(interval1, interval2)

    def get_events_before(self, event_id: str) -> List[TemporalEvent]:
        """Get events that occur before given event."""
        event = self._event_manager.get_event(event_id)
        if not event:
            return []
        return self._event_manager.get_events_before(event.start_time)

    def get_events_after(self, event_id: str) -> List[TemporalEvent]:
        """Get events that occur after given event."""
        event = self._event_manager.get_event(event_id)
        if not event:
            return []
        event_end = event.end_time or event.start_time
        return self._event_manager.get_events_after(event_end)

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------

    def add_constraint(
        self,
        source_id: str,
        target_id: str,
        relation: TemporalRelation,
        min_gap: Optional[float] = None,
        max_gap: Optional[float] = None
    ) -> TemporalConstraint:
        """Add a temporal constraint."""
        constraint = TemporalConstraint(
            source_id=source_id,
            target_id=target_id,
            relation=relation,
            min_gap=min_gap,
            max_gap=max_gap
        )
        self._constraint_network.add_constraint(constraint)
        return constraint

    def check_constraints(self) -> Dict[str, ConstraintSatisfaction]:
        """Check all constraints."""
        # Build intervals from events
        intervals = {}
        for event in self._event_manager._events.values():
            intervals[event.event_id] = TimeInterval(
                start=event.start_time,
                end=event.end_time or event.start_time
            )

        return self._constraint_network.propagate_constraints(intervals)

    def get_violated_constraints(self) -> List[TemporalConstraint]:
        """Get list of violated constraints."""
        results = self.check_constraints()
        violated = []

        for constraint_id, status in results.items():
            if status == ConstraintSatisfaction.VIOLATED:
                constraint = self._constraint_network.get_constraint(constraint_id)
                if constraint:
                    violated.append(constraint)

        return violated

    # -------------------------------------------------------------------------
    # TIME SERIES
    # -------------------------------------------------------------------------

    def create_time_series(self, name: str) -> None:
        """Create a time series."""
        self._time_series.add_series(name)

    def add_time_point(
        self,
        series_name: str,
        timestamp: float,
        value: float
    ) -> None:
        """Add a point to a time series."""
        self._time_series.add_point(series_name, timestamp, value)

    def get_series_value(
        self,
        series_name: str,
        timestamp: float,
        interpolate: bool = True
    ) -> Optional[float]:
        """Get value from time series at timestamp."""
        return self._time_series.get_value_at(series_name, timestamp, interpolate)

    def analyze_series(
        self,
        series_name: str,
        start: Optional[float] = None,
        end: Optional[float] = None
    ) -> Dict[str, float]:
        """Compute statistics for a time series."""
        return self._time_series.compute_statistics(series_name, start, end)

    def detect_trend(
        self,
        series_name: str,
        window_size: int = 5
    ) -> str:
        """Detect trend in a time series."""
        return self._time_series.detect_trend(series_name, window_size)

    # -------------------------------------------------------------------------
    # TIMELINES
    # -------------------------------------------------------------------------

    def create_timeline(
        self,
        name: str,
        resolution: TimeUnit = TimeUnit.SECOND
    ) -> Timeline:
        """Create a timeline."""
        return self._timeline_manager.create_timeline(name, resolution)

    def add_event_to_timeline(
        self,
        timeline_id: str,
        event_id: str
    ) -> bool:
        """Add event to timeline."""
        return self._timeline_manager.add_event_to_timeline(timeline_id, event_id)

    def get_timeline_events(self, timeline_id: str) -> List[TemporalEvent]:
        """Get events in a timeline."""
        return self._timeline_manager.get_timeline_events(timeline_id)

    # -------------------------------------------------------------------------
    # QUERIES
    # -------------------------------------------------------------------------

    def query_at_time(self, timestamp: float) -> TemporalQueryResult:
        """Query events at a specific time."""
        return self._query_processor.query_point(timestamp)

    def query_time_range(
        self,
        start: float,
        end: float
    ) -> TemporalQueryResult:
        """Query events in a time range."""
        return self._query_processor.query_range(start, end)

    def query_by_relation(
        self,
        event_id: str,
        relation: TemporalRelation
    ) -> TemporalQueryResult:
        """Query events by temporal relation."""
        return self._query_processor.query_relation(event_id, relation)

    def query_sequence(
        self,
        event_names: List[str]
    ) -> TemporalQueryResult:
        """Query if events occur in sequence."""
        return self._query_processor.query_sequence(event_names)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Temporal Reasoner."""
    print("=" * 70)
    print("BAEL - TEMPORAL REASONER DEMO")
    print("Advanced Temporal Reasoning and Time-Based Inference")
    print("=" * 70)
    print()

    reasoner = TemporalReasoner()

    # 1. Create Events
    print("1. CREATE TEMPORAL EVENTS:")
    print("-" * 40)

    base_time = time.time()

    e1 = reasoner.create_event(
        "Project Start",
        EventType.INSTANT,
        start_time=base_time
    )

    e2 = reasoner.create_event(
        "Development Phase",
        EventType.INTERVAL,
        start_time=base_time + 100,
        end_time=base_time + 500
    )

    e3 = reasoner.create_event(
        "Testing Phase",
        EventType.INTERVAL,
        start_time=base_time + 400,
        end_time=base_time + 700
    )

    e4 = reasoner.create_event(
        "Deployment",
        EventType.INSTANT,
        start_time=base_time + 800
    )

    print(f"   Created: {e1.name} (instant)")
    print(f"   Created: {e2.name} (interval, duration={e2.end_time - e2.start_time}s)")
    print(f"   Created: {e3.name} (interval, duration={e3.end_time - e3.start_time}s)")
    print(f"   Created: {e4.name} (instant)")
    print()

    # 2. Compute Temporal Relations
    print("2. ALLEN'S INTERVAL ALGEBRA:")
    print("-" * 40)

    rel_1_2 = reasoner.compute_relation(e1.event_id, e2.event_id)
    print(f"   {e1.name} -> {e2.name}: {rel_1_2.value if rel_1_2 else 'N/A'}")

    rel_2_3 = reasoner.compute_relation(e2.event_id, e3.event_id)
    print(f"   {e2.name} -> {e3.name}: {rel_2_3.value if rel_2_3 else 'N/A'}")

    rel_3_4 = reasoner.compute_relation(e3.event_id, e4.event_id)
    print(f"   {e3.name} -> {e4.name}: {rel_3_4.value if rel_3_4 else 'N/A'}")

    rel_1_4 = reasoner.compute_relation(e1.event_id, e4.event_id)
    print(f"   {e1.name} -> {e4.name}: {rel_1_4.value if rel_1_4 else 'N/A'}")
    print()

    # 3. Add Constraints
    print("3. TEMPORAL CONSTRAINTS:")
    print("-" * 40)

    c1 = reasoner.add_constraint(
        e1.event_id,
        e2.event_id,
        TemporalRelation.BEFORE,
        min_gap=50,
        max_gap=200
    )
    print(f"   Added: {e1.name} BEFORE {e2.name} (gap: 50-200s)")

    c2 = reasoner.add_constraint(
        e3.event_id,
        e4.event_id,
        TemporalRelation.BEFORE
    )
    print(f"   Added: {e3.name} BEFORE {e4.name}")

    # Check constraints
    results = reasoner.check_constraints()
    print(f"   Constraint check results:")
    for cid, status in results.items():
        print(f"     - {cid[:8]}...: {status.value}")
    print()

    # 4. Time Series Analysis
    print("4. TIME SERIES ANALYSIS:")
    print("-" * 40)

    reasoner.create_time_series("cpu_usage")

    # Add sample data
    for i in range(20):
        ts = base_time + i * 10
        value = 30 + i * 2 + random.uniform(-5, 5)
        reasoner.add_time_point("cpu_usage", ts, value)

    stats = reasoner.analyze_series("cpu_usage")
    print(f"   CPU Usage Statistics:")
    print(f"     - Count: {stats.get('count', 0)}")
    print(f"     - Min: {stats.get('min', 0):.2f}")
    print(f"     - Max: {stats.get('max', 0):.2f}")
    print(f"     - Mean: {stats.get('mean', 0):.2f}")
    print(f"     - Std Dev: {stats.get('std_dev', 0):.2f}")

    trend = reasoner.detect_trend("cpu_usage")
    print(f"   Trend: {trend}")
    print()

    # 5. Create Timeline
    print("5. TIMELINE MANAGEMENT:")
    print("-" * 40)

    timeline = reasoner.create_timeline("project_timeline")

    for event in [e1, e2, e3, e4]:
        reasoner.add_event_to_timeline(timeline.timeline_id, event.event_id)

    events = reasoner.get_timeline_events(timeline.timeline_id)
    print(f"   Timeline: {timeline.name}")
    print(f"   Events in order:")
    for event in events:
        print(f"     - {event.name} @ {event.start_time - base_time:.0f}s")
    print()

    # 6. Temporal Queries
    print("6. TEMPORAL QUERIES:")
    print("-" * 40)

    # Point query
    result = reasoner.query_at_time(base_time + 300)
    print(f"   Events at t+300s: {result.count} found")

    # Range query
    result = reasoner.query_time_range(base_time + 200, base_time + 600)
    print(f"   Events in [t+200s, t+600s]: {result.count} found")

    # Relation query
    result = reasoner.query_by_relation(e2.event_id, TemporalRelation.BEFORE)
    print(f"   Events BEFORE {e2.name}: {result.count} found")

    # Sequence query
    result = reasoner.query_sequence(["Project Start", "Development Phase", "Deployment"])
    print(f"   Sequence valid: {result.results[0] if result.results else False}")
    print()

    # 7. Event Queries
    print("7. EVENT QUERIES:")
    print("-" * 40)

    before = reasoner.get_events_before(e3.event_id)
    print(f"   Events before {e3.name}:")
    for event in before:
        print(f"     - {event.name}")

    after = reasoner.get_events_after(e2.event_id)
    print(f"   Events after {e2.name}:")
    for event in after:
        print(f"     - {event.name}")
    print()

    # 8. Allen's Algebra Inverse
    print("8. RELATION INVERSES:")
    print("-" * 40)

    for rel in [TemporalRelation.BEFORE, TemporalRelation.OVERLAPS, TemporalRelation.DURING]:
        inv = AllenAlgebra.inverse(rel)
        print(f"   Inverse of {rel.value}: {inv.value}")
    print()

    # 9. Time Series Interpolation
    print("9. TIME SERIES INTERPOLATION:")
    print("-" * 40)

    for offset in [5, 35, 95]:
        ts = base_time + offset
        value = reasoner.get_series_value("cpu_usage", ts, interpolate=True)
        print(f"   Value at t+{offset}s: {value:.2f if value else 'N/A'}")
    print()

    # 10. Violated Constraints
    print("10. CONSTRAINT VIOLATION CHECK:")
    print("-" * 40)

    violated = reasoner.get_violated_constraints()
    if violated:
        print(f"   Violated constraints: {len(violated)}")
        for c in violated:
            print(f"     - {c.source_id[:8]}... {c.relation.value} {c.target_id[:8]}...")
    else:
        print("   All constraints satisfied!")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Temporal Reasoner Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
