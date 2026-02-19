"""
⚡ TEMPORAL CORE ⚡
==================
Core temporal representations.

Features:
- Time points and intervals
- Allen's interval algebra
- Temporal graphs
- Timeline management
"""

import math
import numpy as np
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import uuid
from datetime import datetime, timedelta


class TemporalRelation(Enum):
    """Allen's interval relations"""
    BEFORE = auto()       # A before B: A ends before B starts
    AFTER = auto()        # A after B: A starts after B ends
    MEETS = auto()        # A meets B: A end = B start
    MET_BY = auto()       # A met by B: B meets A
    OVERLAPS = auto()     # A overlaps B: A starts before B, ends during B
    OVERLAPPED_BY = auto()
    STARTS = auto()       # A starts B: same start, A ends first
    STARTED_BY = auto()
    DURING = auto()       # A during B: A contained in B
    CONTAINS = auto()
    FINISHES = auto()     # A finishes B: same end, A starts later
    FINISHED_BY = auto()
    EQUALS = auto()       # A equals B: same start and end


@dataclass
class TimePoint:
    """A point in time"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = 0.0  # Unix timestamp or abstract time

    # Uncertainty
    uncertainty: float = 0.0  # ± uncertainty

    # Labels
    label: str = ""

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other: 'TimePoint') -> bool:
        return self.timestamp < other.timestamp

    def __le__(self, other: 'TimePoint') -> bool:
        return self.timestamp <= other.timestamp

    def __gt__(self, other: 'TimePoint') -> bool:
        return self.timestamp > other.timestamp

    def __ge__(self, other: 'TimePoint') -> bool:
        return self.timestamp >= other.timestamp

    def distance_to(self, other: 'TimePoint') -> float:
        """Get temporal distance to another point"""
        return abs(self.timestamp - other.timestamp)

    def to_datetime(self) -> datetime:
        """Convert to datetime"""
        return datetime.fromtimestamp(self.timestamp)


@dataclass
class TimeInterval:
    """An interval of time"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    start: TimePoint = None
    end: TimePoint = None

    # Properties
    label: str = ""

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.start is None:
            self.start = TimePoint()
        if self.end is None:
            self.end = TimePoint(timestamp=self.start.timestamp + 1)

    @property
    def duration(self) -> float:
        """Get duration of interval"""
        return self.end.timestamp - self.start.timestamp

    @property
    def midpoint(self) -> float:
        """Get midpoint of interval"""
        return (self.start.timestamp + self.end.timestamp) / 2

    def contains_point(self, point: TimePoint) -> bool:
        """Check if interval contains a time point"""
        return self.start.timestamp <= point.timestamp <= self.end.timestamp

    def contains_interval(self, other: 'TimeInterval') -> bool:
        """Check if this interval contains another"""
        return (self.start.timestamp <= other.start.timestamp and
                self.end.timestamp >= other.end.timestamp)

    def overlaps_with(self, other: 'TimeInterval') -> bool:
        """Check if intervals overlap"""
        return not (self.end.timestamp <= other.start.timestamp or
                    other.end.timestamp <= self.start.timestamp)

    def get_relation(self, other: 'TimeInterval') -> TemporalRelation:
        """Get Allen's relation to another interval"""
        s1, e1 = self.start.timestamp, self.end.timestamp
        s2, e2 = other.start.timestamp, other.end.timestamp

        eps = 1e-10  # Floating point tolerance

        if abs(s1 - s2) < eps and abs(e1 - e2) < eps:
            return TemporalRelation.EQUALS

        if e1 < s2 - eps:
            return TemporalRelation.BEFORE
        if s1 > e2 + eps:
            return TemporalRelation.AFTER

        if abs(e1 - s2) < eps:
            return TemporalRelation.MEETS
        if abs(s1 - e2) < eps:
            return TemporalRelation.MET_BY

        if s1 < s2 and e1 > s2 and e1 < e2:
            return TemporalRelation.OVERLAPS
        if s2 < s1 and e2 > s1 and e2 < e1:
            return TemporalRelation.OVERLAPPED_BY

        if abs(s1 - s2) < eps and e1 < e2:
            return TemporalRelation.STARTS
        if abs(s1 - s2) < eps and e1 > e2:
            return TemporalRelation.STARTED_BY

        if abs(e1 - e2) < eps and s1 > s2:
            return TemporalRelation.FINISHES
        if abs(e1 - e2) < eps and s1 < s2:
            return TemporalRelation.FINISHED_BY

        if s1 > s2 and e1 < e2:
            return TemporalRelation.DURING
        if s1 < s2 and e1 > e2:
            return TemporalRelation.CONTAINS

        return TemporalRelation.OVERLAPS  # Default


@dataclass
class TemporalEntity:
    """An entity with temporal properties"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""

    # Temporal extent
    valid_time: TimeInterval = None  # When entity is valid
    transaction_time: TimeInterval = None  # When recorded

    # State history
    state_history: List[Tuple[TimePoint, Any]] = field(default_factory=list)

    # Temporal relationships
    temporal_relations: Dict[str, Tuple[str, TemporalRelation]] = field(default_factory=dict)

    def get_state_at(self, time: TimePoint) -> Optional[Any]:
        """Get entity state at a specific time"""
        if not self.state_history:
            return None

        # Find most recent state before or at the given time
        applicable_states = [
            (t, state) for t, state in self.state_history
            if t.timestamp <= time.timestamp
        ]

        if not applicable_states:
            return None

        # Return most recent
        return max(applicable_states, key=lambda x: x[0].timestamp)[1]

    def add_state(self, time: TimePoint, state: Any):
        """Add a state at a specific time"""
        self.state_history.append((time, state))
        self.state_history.sort(key=lambda x: x[0].timestamp)


class Timeline:
    """
    A timeline containing events and intervals.
    """

    def __init__(self, name: str = "default"):
        self.name = name
        self.id = str(uuid.uuid4())

        # Events (points)
        self.events: Dict[str, TimePoint] = {}

        # Intervals
        self.intervals: Dict[str, TimeInterval] = {}

        # Entities
        self.entities: Dict[str, TemporalEntity] = {}

        # Current time
        self.current_time: float = 0.0

    def add_event(self, event: TimePoint):
        """Add event to timeline"""
        self.events[event.id] = event

    def add_interval(self, interval: TimeInterval):
        """Add interval to timeline"""
        self.intervals[interval.id] = interval

    def add_entity(self, entity: TemporalEntity):
        """Add entity to timeline"""
        self.entities[entity.id] = entity

    def advance_time(self, delta: float):
        """Advance current time"""
        self.current_time += delta

    def get_events_in_range(
        self,
        start: float,
        end: float
    ) -> List[TimePoint]:
        """Get events in time range"""
        return [
            e for e in self.events.values()
            if start <= e.timestamp <= end
        ]

    def get_active_intervals(self, time: float = None) -> List[TimeInterval]:
        """Get intervals active at a given time"""
        time = time if time is not None else self.current_time

        return [
            i for i in self.intervals.values()
            if i.start.timestamp <= time <= i.end.timestamp
        ]

    def get_sequence(self) -> List[TimePoint]:
        """Get all events in chronological order"""
        return sorted(self.events.values(), key=lambda e: e.timestamp)

    def find_patterns(
        self,
        pattern_length: int = 3
    ) -> List[List[TimePoint]]:
        """Find recurring patterns in timeline"""
        sequence = self.get_sequence()
        patterns = []

        for i in range(len(sequence) - pattern_length + 1):
            pattern = sequence[i:i + pattern_length]

            # Check if pattern repeats
            for j in range(i + pattern_length, len(sequence) - pattern_length + 1):
                candidate = sequence[j:j + pattern_length]

                # Compare labels
                if [p.label for p in pattern] == [c.label for c in candidate]:
                    patterns.append(pattern)
                    break

        return patterns


class TemporalGraph:
    """
    Graph with temporal edges and nodes.
    """

    def __init__(self):
        self.nodes: Dict[str, TemporalEntity] = {}

        # Edges with temporal validity
        self.edges: Dict[str, Tuple[str, str, TimeInterval]] = {}

        # Temporal constraints
        self.constraints: List[Tuple[str, str, TemporalRelation]] = []

    def add_node(self, entity: TemporalEntity):
        """Add node to graph"""
        self.nodes[entity.id] = entity

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        valid_time: TimeInterval,
        edge_id: str = None
    ):
        """Add temporal edge"""
        edge_id = edge_id or str(uuid.uuid4())
        self.edges[edge_id] = (source_id, target_id, valid_time)

    def add_constraint(
        self,
        entity_a: str,
        entity_b: str,
        relation: TemporalRelation
    ):
        """Add temporal constraint"""
        self.constraints.append((entity_a, entity_b, relation))

    def get_graph_at_time(self, time: float) -> Dict[str, List[str]]:
        """Get graph snapshot at specific time"""
        active_edges = {}

        for edge_id, (source, target, interval) in self.edges.items():
            if interval.start.timestamp <= time <= interval.end.timestamp:
                if source not in active_edges:
                    active_edges[source] = []
                active_edges[source].append(target)

        return active_edges

    def get_temporal_path(
        self,
        source_id: str,
        target_id: str,
        time_range: TimeInterval = None
    ) -> Optional[List[str]]:
        """Find path respecting temporal constraints"""
        if source_id not in self.nodes or target_id not in self.nodes:
            return None

        # BFS with temporal filtering
        visited = {source_id}
        queue = [(source_id, [source_id], 0.0)]

        while queue:
            current, path, current_time = queue.pop(0)

            if current == target_id:
                return path

            # Get valid edges from current node
            for edge_id, (src, tgt, interval) in self.edges.items():
                if src != current:
                    continue

                if tgt in visited:
                    continue

                # Check temporal validity
                if time_range and not interval.overlaps_with(time_range):
                    continue

                if interval.start.timestamp < current_time:
                    continue  # Can't go back in time

                visited.add(tgt)
                queue.append((tgt, path + [tgt], interval.end.timestamp))

        return None

    def check_consistency(self) -> List[str]:
        """Check temporal consistency of constraints"""
        violations = []

        for entity_a, entity_b, required_relation in self.constraints:
            a = self.nodes.get(entity_a)
            b = self.nodes.get(entity_b)

            if not a or not b or not a.valid_time or not b.valid_time:
                continue

            actual_relation = a.valid_time.get_relation(b.valid_time)

            if actual_relation != required_relation:
                violations.append(
                    f"Constraint violated: {entity_a} should be "
                    f"{required_relation.name} {entity_b}, "
                    f"but is {actual_relation.name}"
                )

        return violations


# Export all
__all__ = [
    'TemporalRelation',
    'TimePoint',
    'TimeInterval',
    'TemporalEntity',
    'Timeline',
    'TemporalGraph',
]
