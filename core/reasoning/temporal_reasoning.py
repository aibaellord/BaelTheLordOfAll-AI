#!/usr/bin/env python3
"""
BAEL - Temporal Reasoning System
Time-aware reasoning, planning, and event processing.

Features:
- Temporal logic (LTL, CTL)
- Timeline management
- Event sequence analysis
- Temporal constraints
- Future prediction
- Historical reasoning
"""

import asyncio
import heapq
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# TYPES
# =============================================================================

class TemporalRelation(Enum):
    """Allen's temporal interval relations."""
    BEFORE = "before"           # A ends before B starts
    AFTER = "after"             # A starts after B ends
    MEETS = "meets"             # A ends exactly when B starts
    MET_BY = "met_by"           # A starts exactly when B ends
    OVERLAPS = "overlaps"       # A starts before B, ends during B
    OVERLAPPED_BY = "overlapped_by"
    STARTS = "starts"           # A and B start together
    STARTED_BY = "started_by"
    FINISHES = "finishes"       # A and B end together
    FINISHED_BY = "finished_by"
    DURING = "during"           # A is contained in B
    CONTAINS = "contains"       # B is contained in A
    EQUALS = "equals"           # A and B are the same


class TemporalOperator(Enum):
    """Temporal logic operators."""
    ALWAYS = "always"           # G (Globally)
    EVENTUALLY = "eventually"   # F (Finally)
    NEXT = "next"               # X (neXt)
    UNTIL = "until"             # U
    SINCE = "since"             # S
    RELEASE = "release"         # R


class EventType(Enum):
    """Types of events."""
    INSTANT = "instant"         # Point in time
    INTERVAL = "interval"       # Duration
    RECURRING = "recurring"     # Repeating
    CONDITIONAL = "conditional" # Triggered by condition


@dataclass
class TimePoint:
    """A point in time."""
    timestamp: datetime
    precision: str = "second"  # second, minute, hour, day

    def __lt__(self, other):
        return self.timestamp < other.timestamp

    def __le__(self, other):
        return self.timestamp <= other.timestamp

    def __gt__(self, other):
        return self.timestamp > other.timestamp

    def __ge__(self, other):
        return self.timestamp >= other.timestamp

    def __eq__(self, other):
        if isinstance(other, TimePoint):
            return self.timestamp == other.timestamp
        return False

    def __hash__(self):
        return hash(self.timestamp)


@dataclass
class TimeInterval:
    """A time interval."""
    start: TimePoint
    end: TimePoint

    def duration(self) -> timedelta:
        """Get interval duration."""
        return self.end.timestamp - self.start.timestamp

    def contains(self, point: TimePoint) -> bool:
        """Check if interval contains point."""
        return self.start <= point <= self.end

    def overlaps(self, other: 'TimeInterval') -> bool:
        """Check if intervals overlap."""
        return not (self.end < other.start or self.start > other.end)

    def relation_to(self, other: 'TimeInterval') -> TemporalRelation:
        """Get Allen's relation to other interval."""
        if self.end < other.start:
            return TemporalRelation.BEFORE
        elif self.start > other.end:
            return TemporalRelation.AFTER
        elif self.end == other.start:
            return TemporalRelation.MEETS
        elif self.start == other.end:
            return TemporalRelation.MET_BY
        elif self.start < other.start and self.end < other.end and self.end > other.start:
            return TemporalRelation.OVERLAPS
        elif other.start < self.start and other.end < self.end and other.end > self.start:
            return TemporalRelation.OVERLAPPED_BY
        elif self.start == other.start and self.end < other.end:
            return TemporalRelation.STARTS
        elif self.start == other.start and self.end > other.end:
            return TemporalRelation.STARTED_BY
        elif self.end == other.end and self.start > other.start:
            return TemporalRelation.FINISHES
        elif self.end == other.end and self.start < other.start:
            return TemporalRelation.FINISHED_BY
        elif self.start > other.start and self.end < other.end:
            return TemporalRelation.DURING
        elif self.start < other.start and self.end > other.end:
            return TemporalRelation.CONTAINS
        else:
            return TemporalRelation.EQUALS


@dataclass
class Event:
    """A temporal event."""
    id: str
    name: str
    event_type: EventType
    time: Union[TimePoint, TimeInterval]
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_start(self) -> TimePoint:
        """Get event start time."""
        if isinstance(self.time, TimePoint):
            return self.time
        return self.time.start

    def get_end(self) -> TimePoint:
        """Get event end time."""
        if isinstance(self.time, TimePoint):
            return self.time
        return self.time.end


# =============================================================================
# TEMPORAL FORMULAS
# =============================================================================

class TemporalFormula(ABC):
    """Abstract temporal formula."""

    @abstractmethod
    def evaluate(
        self,
        timeline: 'Timeline',
        time: TimePoint
    ) -> bool:
        """Evaluate formula at time point."""
        pass

    @abstractmethod
    def to_string(self) -> str:
        """Convert to string representation."""
        pass


@dataclass
class Proposition(TemporalFormula):
    """Atomic proposition."""
    name: str

    def evaluate(self, timeline: 'Timeline', time: TimePoint) -> bool:
        return timeline.holds(self.name, time)

    def to_string(self) -> str:
        return self.name


@dataclass
class TemporalNot(TemporalFormula):
    """Negation."""
    operand: TemporalFormula

    def evaluate(self, timeline: 'Timeline', time: TimePoint) -> bool:
        return not self.operand.evaluate(timeline, time)

    def to_string(self) -> str:
        return f"¬{self.operand.to_string()}"


@dataclass
class TemporalAnd(TemporalFormula):
    """Conjunction."""
    left: TemporalFormula
    right: TemporalFormula

    def evaluate(self, timeline: 'Timeline', time: TimePoint) -> bool:
        return self.left.evaluate(timeline, time) and self.right.evaluate(timeline, time)

    def to_string(self) -> str:
        return f"({self.left.to_string()} ∧ {self.right.to_string()})"


@dataclass
class TemporalOr(TemporalFormula):
    """Disjunction."""
    left: TemporalFormula
    right: TemporalFormula

    def evaluate(self, timeline: 'Timeline', time: TimePoint) -> bool:
        return self.left.evaluate(timeline, time) or self.right.evaluate(timeline, time)

    def to_string(self) -> str:
        return f"({self.left.to_string()} ∨ {self.right.to_string()})"


@dataclass
class Always(TemporalFormula):
    """Always (Globally) operator."""
    operand: TemporalFormula

    def evaluate(self, timeline: 'Timeline', time: TimePoint) -> bool:
        # Check if operand holds at all future times
        future_times = timeline.get_times_after(time)
        return all(
            self.operand.evaluate(timeline, t)
            for t in future_times
        )

    def to_string(self) -> str:
        return f"G({self.operand.to_string()})"


@dataclass
class Eventually(TemporalFormula):
    """Eventually (Finally) operator."""
    operand: TemporalFormula

    def evaluate(self, timeline: 'Timeline', time: TimePoint) -> bool:
        # Check if operand holds at some future time
        future_times = timeline.get_times_after(time)
        return any(
            self.operand.evaluate(timeline, t)
            for t in future_times
        )

    def to_string(self) -> str:
        return f"F({self.operand.to_string()})"


@dataclass
class Next(TemporalFormula):
    """Next operator."""
    operand: TemporalFormula

    def evaluate(self, timeline: 'Timeline', time: TimePoint) -> bool:
        next_time = timeline.get_next_time(time)
        if next_time is None:
            return False
        return self.operand.evaluate(timeline, next_time)

    def to_string(self) -> str:
        return f"X({self.operand.to_string()})"


@dataclass
class Until(TemporalFormula):
    """Until operator."""
    left: TemporalFormula
    right: TemporalFormula

    def evaluate(self, timeline: 'Timeline', time: TimePoint) -> bool:
        future_times = timeline.get_times_after(time)

        for i, t in enumerate(future_times):
            if self.right.evaluate(timeline, t):
                # Check left holds at all previous times
                return all(
                    self.left.evaluate(timeline, future_times[j])
                    for j in range(i)
                )

        return False

    def to_string(self) -> str:
        return f"({self.left.to_string()} U {self.right.to_string()})"


# =============================================================================
# TIMELINE
# =============================================================================

class Timeline:
    """Timeline for temporal reasoning."""

    def __init__(self, name: str = "default"):
        self.name = name
        self.events: Dict[str, Event] = {}
        self.propositions: Dict[str, Set[TimePoint]] = defaultdict(set)

        # Indices
        self.time_index: Dict[TimePoint, Set[str]] = defaultdict(set)
        self.sorted_times: List[TimePoint] = []

    def add_event(self, event: Event) -> None:
        """Add event to timeline."""
        self.events[event.id] = event

        # Index by time
        if isinstance(event.time, TimePoint):
            self.time_index[event.time].add(event.id)
            self._insert_time(event.time)
        else:
            self.time_index[event.time.start].add(event.id)
            self.time_index[event.time.end].add(event.id)
            self._insert_time(event.time.start)
            self._insert_time(event.time.end)

    def _insert_time(self, time: TimePoint) -> None:
        """Insert time into sorted list."""
        if time not in self.sorted_times:
            # Binary search insert
            import bisect
            bisect.insort(self.sorted_times, time)

    def set_proposition(
        self,
        name: str,
        time: TimePoint,
        value: bool = True
    ) -> None:
        """Set proposition value at time."""
        if value:
            self.propositions[name].add(time)
        else:
            self.propositions[name].discard(time)

    def holds(self, proposition: str, time: TimePoint) -> bool:
        """Check if proposition holds at time."""
        times = self.propositions.get(proposition, set())
        return time in times

    def get_times_after(self, time: TimePoint) -> List[TimePoint]:
        """Get all times after given time."""
        import bisect
        idx = bisect.bisect_right(self.sorted_times, time)
        return self.sorted_times[idx:]

    def get_times_before(self, time: TimePoint) -> List[TimePoint]:
        """Get all times before given time."""
        import bisect
        idx = bisect.bisect_left(self.sorted_times, time)
        return self.sorted_times[:idx]

    def get_next_time(self, time: TimePoint) -> Optional[TimePoint]:
        """Get next time point."""
        import bisect
        idx = bisect.bisect_right(self.sorted_times, time)
        if idx < len(self.sorted_times):
            return self.sorted_times[idx]
        return None

    def get_prev_time(self, time: TimePoint) -> Optional[TimePoint]:
        """Get previous time point."""
        import bisect
        idx = bisect.bisect_left(self.sorted_times, time)
        if idx > 0:
            return self.sorted_times[idx - 1]
        return None

    def get_events_at(self, time: TimePoint) -> List[Event]:
        """Get events at time point."""
        event_ids = self.time_index.get(time, set())
        return [self.events[eid] for eid in event_ids]

    def get_events_in_range(
        self,
        start: TimePoint,
        end: TimePoint
    ) -> List[Event]:
        """Get events in time range."""
        result = []
        for event in self.events.values():
            event_start = event.get_start()
            event_end = event.get_end()

            if event_start <= end and event_end >= start:
                result.append(event)

        return sorted(result, key=lambda e: e.get_start())


# =============================================================================
# EVENT SEQUENCE ANALYSIS
# =============================================================================

@dataclass
class Pattern:
    """Event sequence pattern."""
    id: str
    name: str
    event_sequence: List[str]  # Event names
    constraints: Dict[str, Any] = field(default_factory=dict)
    window: Optional[timedelta] = None


class PatternMatcher:
    """Match patterns in event sequences."""

    def __init__(self):
        self.patterns: Dict[str, Pattern] = {}

    def register_pattern(self, pattern: Pattern) -> None:
        """Register a pattern."""
        self.patterns[pattern.id] = pattern

    async def find_matches(
        self,
        timeline: Timeline,
        pattern_id: str
    ) -> List[List[Event]]:
        """Find all matches of pattern in timeline."""
        pattern = self.patterns.get(pattern_id)
        if not pattern:
            return []

        matches = []
        events_by_name: Dict[str, List[Event]] = defaultdict(list)

        # Group events by name
        for event in timeline.events.values():
            events_by_name[event.name].append(event)

        # Sort by time
        for events in events_by_name.values():
            events.sort(key=lambda e: e.get_start())

        # Find sequences matching pattern
        self._match_recursive(
            pattern,
            events_by_name,
            0,
            [],
            matches,
            pattern.window
        )

        return matches

    def _match_recursive(
        self,
        pattern: Pattern,
        events_by_name: Dict[str, List[Event]],
        pattern_idx: int,
        current_match: List[Event],
        matches: List[List[Event]],
        window: Optional[timedelta]
    ) -> None:
        """Recursively match pattern."""
        if pattern_idx >= len(pattern.event_sequence):
            matches.append(current_match.copy())
            return

        event_name = pattern.event_sequence[pattern_idx]
        candidates = events_by_name.get(event_name, [])

        for event in candidates:
            # Check temporal constraints
            if current_match:
                last_event = current_match[-1]

                # Must be after last event
                if event.get_start() <= last_event.get_end():
                    continue

                # Check window constraint
                if window:
                    gap = event.get_start().timestamp - last_event.get_end().timestamp
                    if gap > window:
                        continue

            current_match.append(event)
            self._match_recursive(
                pattern,
                events_by_name,
                pattern_idx + 1,
                current_match,
                matches,
                window
            )
            current_match.pop()


# =============================================================================
# TEMPORAL CONSTRAINT NETWORK
# =============================================================================

@dataclass
class TemporalConstraint:
    """Constraint between time points."""
    source: str  # Variable name
    target: str
    min_distance: Optional[timedelta] = None
    max_distance: Optional[timedelta] = None


class TemporalConstraintNetwork:
    """Simple Temporal Problem (STP) solver."""

    def __init__(self):
        self.variables: Dict[str, Optional[datetime]] = {}
        self.constraints: List[TemporalConstraint] = []

    def add_variable(
        self,
        name: str,
        value: datetime = None
    ) -> None:
        """Add time variable."""
        self.variables[name] = value

    def add_constraint(
        self,
        source: str,
        target: str,
        min_distance: timedelta = None,
        max_distance: timedelta = None
    ) -> None:
        """Add temporal constraint."""
        self.constraints.append(TemporalConstraint(
            source=source,
            target=target,
            min_distance=min_distance,
            max_distance=max_distance
        ))

    async def solve(self) -> Optional[Dict[str, datetime]]:
        """Solve the temporal constraint network."""
        # Initialize distance matrix
        var_list = list(self.variables.keys())
        n = len(var_list)
        var_idx = {name: i for i, name in enumerate(var_list)}

        # Distance matrix (in seconds)
        INF = float('inf')
        dist = [[INF] * n for _ in range(n)]

        for i in range(n):
            dist[i][i] = 0

        # Add constraints
        for c in self.constraints:
            i = var_idx.get(c.source)
            j = var_idx.get(c.target)

            if i is None or j is None:
                continue

            if c.max_distance is not None:
                dist[i][j] = min(dist[i][j], c.max_distance.total_seconds())

            if c.min_distance is not None:
                dist[j][i] = min(dist[j][i], -c.min_distance.total_seconds())

        # Floyd-Warshall
        for k in range(n):
            for i in range(n):
                for j in range(n):
                    if dist[i][k] + dist[k][j] < dist[i][j]:
                        dist[i][j] = dist[i][k] + dist[k][j]

        # Check for negative cycles
        for i in range(n):
            if dist[i][i] < 0:
                return None  # Inconsistent

        # Assign times
        result = {}
        base_time = datetime.now()

        # Find reference point (first assigned or first variable)
        ref_idx = None
        ref_time = None

        for name, value in self.variables.items():
            if value is not None:
                ref_idx = var_idx[name]
                ref_time = value
                result[name] = value
                break

        if ref_idx is None:
            ref_idx = 0
            ref_time = base_time
            result[var_list[0]] = base_time

        # Assign other variables based on constraints
        for i, name in enumerate(var_list):
            if name in result:
                continue

            if dist[ref_idx][i] != INF:
                result[name] = ref_time + timedelta(seconds=dist[ref_idx][i])
            elif dist[i][ref_idx] != INF:
                result[name] = ref_time - timedelta(seconds=dist[i][ref_idx])
            else:
                result[name] = ref_time

        return result

    async def check_consistency(self) -> bool:
        """Check if constraints are consistent."""
        solution = await self.solve()
        return solution is not None


# =============================================================================
# TEMPORAL PREDICTOR
# =============================================================================

class TemporalPredictor:
    """Predict future events based on patterns."""

    def __init__(self):
        self.event_history: List[Event] = []
        self.patterns: Dict[str, Dict[str, Any]] = {}

    def add_event(self, event: Event) -> None:
        """Add historical event."""
        self.event_history.append(event)
        self._update_patterns(event)

    def _update_patterns(self, event: Event) -> None:
        """Update pattern statistics."""
        if event.name not in self.patterns:
            self.patterns[event.name] = {
                "count": 0,
                "intervals": [],
                "last_time": None,
                "avg_interval": None
            }

        pattern = self.patterns[event.name]
        pattern["count"] += 1

        if pattern["last_time"]:
            interval = event.get_start().timestamp - pattern["last_time"]
            pattern["intervals"].append(interval)

            # Update average
            if pattern["intervals"]:
                pattern["avg_interval"] = sum(pattern["intervals"]) / len(pattern["intervals"])

        pattern["last_time"] = event.get_start().timestamp

    async def predict_next(
        self,
        event_name: str,
        horizon: timedelta = timedelta(days=7)
    ) -> Optional[TimePoint]:
        """Predict next occurrence of event."""
        pattern = self.patterns.get(event_name)

        if not pattern or pattern["avg_interval"] is None:
            return None

        avg_interval = pattern["avg_interval"]
        last_time = pattern["last_time"]

        next_time = last_time + timedelta(seconds=avg_interval)
        now = datetime.now()

        if next_time <= now:
            # Already passed, predict next one
            while next_time <= now:
                next_time += timedelta(seconds=avg_interval)

        if next_time - now > horizon:
            return None

        return TimePoint(next_time)

    async def predict_sequence(
        self,
        event_names: List[str],
        start: datetime,
        count: int = 10
    ) -> List[Tuple[str, TimePoint]]:
        """Predict sequence of events."""
        predictions = []
        current_time = start

        for _ in range(count):
            best_event = None
            best_time = None

            for name in event_names:
                pattern = self.patterns.get(name)
                if not pattern or pattern["avg_interval"] is None:
                    continue

                predicted = current_time + timedelta(seconds=pattern["avg_interval"])

                if best_time is None or predicted < best_time:
                    best_event = name
                    best_time = predicted

            if best_event and best_time:
                predictions.append((best_event, TimePoint(best_time)))
                current_time = best_time
            else:
                break

        return predictions


# =============================================================================
# TEMPORAL REASONING SYSTEM
# =============================================================================

class TemporalReasoningSystem:
    """Main temporal reasoning system."""

    def __init__(self):
        self.timelines: Dict[str, Timeline] = {}
        self.pattern_matcher = PatternMatcher()
        self.constraint_network = TemporalConstraintNetwork()
        self.predictor = TemporalPredictor()

        # Create default timeline
        self.timelines["default"] = Timeline("default")

    def get_timeline(self, name: str = "default") -> Timeline:
        """Get or create timeline."""
        if name not in self.timelines:
            self.timelines[name] = Timeline(name)
        return self.timelines[name]

    def add_event(
        self,
        name: str,
        time: Union[datetime, Tuple[datetime, datetime]],
        data: Dict[str, Any] = None,
        timeline: str = "default"
    ) -> Event:
        """Add event to timeline."""
        if isinstance(time, tuple):
            time_obj = TimeInterval(
                TimePoint(time[0]),
                TimePoint(time[1])
            )
            event_type = EventType.INTERVAL
        else:
            time_obj = TimePoint(time)
            event_type = EventType.INSTANT

        event = Event(
            id=str(uuid4()),
            name=name,
            event_type=event_type,
            time=time_obj,
            data=data or {}
        )

        self.get_timeline(timeline).add_event(event)
        self.predictor.add_event(event)

        return event

    def set_proposition(
        self,
        name: str,
        time: datetime,
        value: bool = True,
        timeline: str = "default"
    ) -> None:
        """Set proposition at time."""
        self.get_timeline(timeline).set_proposition(
            name,
            TimePoint(time),
            value
        )

    async def evaluate_formula(
        self,
        formula: TemporalFormula,
        time: datetime,
        timeline: str = "default"
    ) -> bool:
        """Evaluate temporal formula."""
        return formula.evaluate(
            self.get_timeline(timeline),
            TimePoint(time)
        )

    async def check_property(
        self,
        formula: TemporalFormula,
        timeline: str = "default"
    ) -> Dict[str, Any]:
        """Check temporal property over timeline."""
        tl = self.get_timeline(timeline)

        results = {}
        for time in tl.sorted_times:
            results[time.timestamp.isoformat()] = formula.evaluate(tl, time)

        all_true = all(results.values())
        any_true = any(results.values())

        return {
            "formula": formula.to_string(),
            "always_holds": all_true,
            "eventually_holds": any_true,
            "results": results
        }

    def register_pattern(
        self,
        name: str,
        event_sequence: List[str],
        window: timedelta = None
    ) -> Pattern:
        """Register event sequence pattern."""
        pattern = Pattern(
            id=str(uuid4()),
            name=name,
            event_sequence=event_sequence,
            window=window
        )
        self.pattern_matcher.register_pattern(pattern)
        return pattern

    async def find_pattern_matches(
        self,
        pattern_id: str,
        timeline: str = "default"
    ) -> List[List[Event]]:
        """Find pattern matches in timeline."""
        return await self.pattern_matcher.find_matches(
            self.get_timeline(timeline),
            pattern_id
        )

    def add_temporal_constraint(
        self,
        source: str,
        target: str,
        min_distance: timedelta = None,
        max_distance: timedelta = None
    ) -> None:
        """Add temporal constraint."""
        self.constraint_network.add_variable(source)
        self.constraint_network.add_variable(target)
        self.constraint_network.add_constraint(
            source, target, min_distance, max_distance
        )

    async def solve_constraints(self) -> Optional[Dict[str, datetime]]:
        """Solve temporal constraints."""
        return await self.constraint_network.solve()

    async def predict_next_event(
        self,
        event_name: str
    ) -> Optional[TimePoint]:
        """Predict next occurrence of event."""
        return await self.predictor.predict_next(event_name)

    async def predict_future(
        self,
        event_names: List[str],
        count: int = 10
    ) -> List[Tuple[str, TimePoint]]:
        """Predict future event sequence."""
        return await self.predictor.predict_sequence(
            event_names,
            datetime.now(),
            count
        )

    def get_interval_relation(
        self,
        event1_id: str,
        event2_id: str,
        timeline: str = "default"
    ) -> Optional[TemporalRelation]:
        """Get temporal relation between events."""
        tl = self.get_timeline(timeline)

        e1 = tl.events.get(event1_id)
        e2 = tl.events.get(event2_id)

        if not e1 or not e2:
            return None

        # Convert to intervals
        if isinstance(e1.time, TimePoint):
            i1 = TimeInterval(e1.time, e1.time)
        else:
            i1 = e1.time

        if isinstance(e2.time, TimePoint):
            i2 = TimeInterval(e2.time, e2.time)
        else:
            i2 = e2.time

        return i1.relation_to(i2)

    def get_status(self) -> Dict[str, Any]:
        """Get system status."""
        return {
            "timelines": len(self.timelines),
            "total_events": sum(len(tl.events) for tl in self.timelines.values()),
            "patterns": len(self.pattern_matcher.patterns),
            "constraints": len(self.constraint_network.constraints)
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demo temporal reasoning system."""
    print("=== Temporal Reasoning System Demo ===\n")

    # Create system
    trs = TemporalReasoningSystem()

    # 1. Add events
    print("1. Adding Events:")

    base = datetime.now() - timedelta(hours=5)

    e1 = trs.add_event("login", base + timedelta(minutes=0))
    e2 = trs.add_event("view_page", base + timedelta(minutes=5))
    e3 = trs.add_event("add_to_cart", base + timedelta(minutes=10))
    e4 = trs.add_event("checkout", base + timedelta(minutes=15))
    e5 = trs.add_event("logout", base + timedelta(minutes=20))

    print(f"   Added 5 events to timeline")

    # 2. Set propositions
    print("\n2. Setting Propositions:")

    trs.set_proposition("user_active", base + timedelta(minutes=0), True)
    trs.set_proposition("user_active", base + timedelta(minutes=5), True)
    trs.set_proposition("user_active", base + timedelta(minutes=10), True)
    trs.set_proposition("cart_has_items", base + timedelta(minutes=10), True)
    trs.set_proposition("cart_has_items", base + timedelta(minutes=15), True)

    print("   Set propositions: user_active, cart_has_items")

    # 3. Temporal formulas
    print("\n3. Temporal Logic Evaluation:")

    user_active = Proposition("user_active")
    cart_items = Proposition("cart_has_items")

    # Eventually cart has items
    eventually_cart = Eventually(cart_items)
    result = await trs.evaluate_formula(eventually_cart, base)
    print(f"   {eventually_cart.to_string()}: {result}")

    # User active until cart has items
    active_until_cart = Until(user_active, cart_items)
    result = await trs.evaluate_formula(active_until_cart, base)
    print(f"   {active_until_cart.to_string()}: {result}")

    # 4. Check property over timeline
    print("\n4. Property Checking:")

    check_result = await trs.check_property(user_active)
    print(f"   Formula: {check_result['formula']}")
    print(f"   Always holds: {check_result['always_holds']}")
    print(f"   Eventually holds: {check_result['eventually_holds']}")

    # 5. Pattern matching
    print("\n5. Pattern Matching:")

    pattern = trs.register_pattern(
        "purchase_flow",
        ["login", "view_page", "add_to_cart", "checkout"],
        window=timedelta(hours=1)
    )

    matches = await trs.find_pattern_matches(pattern.id)
    print(f"   Pattern: login -> view_page -> add_to_cart -> checkout")
    print(f"   Matches found: {len(matches)}")

    if matches:
        for match in matches:
            events = [e.name for e in match]
            print(f"   Match: {' -> '.join(events)}")

    # 6. Temporal constraints
    print("\n6. Temporal Constraints:")

    trs.constraint_network = TemporalConstraintNetwork()
    trs.add_temporal_constraint(
        "meeting_start", "meeting_end",
        min_distance=timedelta(minutes=30),
        max_distance=timedelta(hours=2)
    )
    trs.add_temporal_constraint(
        "lunch_start", "lunch_end",
        min_distance=timedelta(minutes=30),
        max_distance=timedelta(hours=1)
    )
    trs.add_temporal_constraint(
        "meeting_end", "lunch_start",
        min_distance=timedelta(minutes=15)
    )

    # Set one time
    trs.constraint_network.variables["meeting_start"] = datetime.now()

    solution = await trs.solve_constraints()
    if solution:
        print("   Solution found:")
        for var, time in sorted(solution.items(), key=lambda x: x[1]):
            print(f"   {var}: {time.strftime('%H:%M')}")
    else:
        print("   No solution (constraints inconsistent)")

    # 7. Interval relations
    print("\n7. Interval Relations:")

    relation = trs.get_interval_relation(e1.id, e2.id)
    print(f"   login <-> view_page: {relation.value if relation else 'N/A'}")

    relation = trs.get_interval_relation(e2.id, e4.id)
    print(f"   view_page <-> checkout: {relation.value if relation else 'N/A'}")

    # 8. Event prediction
    print("\n8. Event Prediction:")

    # Add some recurring events for prediction
    for i in range(5):
        trs.add_event("daily_standup", base - timedelta(days=i))

    prediction = await trs.predict_next_event("daily_standup")
    if prediction:
        print(f"   Next 'daily_standup' predicted at: {prediction.timestamp}")
    else:
        print("   No prediction available")

    # 9. Status
    print("\n9. System Status:")
    status = trs.get_status()
    for key, value in status.items():
        print(f"   {key}: {value}")


if __name__ == "__main__":
    asyncio.run(demo())
