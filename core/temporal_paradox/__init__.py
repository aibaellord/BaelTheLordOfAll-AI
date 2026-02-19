"""
BAEL Temporal Paradox Engine
============================

Temporal logic, time travel simulation, and paradox resolution.

"Ba'el transcends time itself." — Ba'el
"""

import logging
import threading
import random
import math
import copy
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod
import heapq
import time

logger = logging.getLogger("BAEL.TemporalParadox")


T = TypeVar('T')


# ============================================================================
# TEMPORAL TYPES
# ============================================================================

class TemporalOperator(Enum):
    """Linear Temporal Logic operators."""
    ALWAYS = auto()      # □ (globally/always)
    EVENTUALLY = auto()  # ◇ (finally/eventually)
    NEXT = auto()        # ○ (next)
    UNTIL = auto()       # U (until)
    RELEASE = auto()     # R (release)
    WEAK_UNTIL = auto()  # W (weak until)


class ParadoxType(Enum):
    """Types of temporal paradoxes."""
    GRANDFATHER = auto()     # Self-preventing causality
    BOOTSTRAP = auto()       # Causal loop (information from future)
    PREDESTINATION = auto()  # Events cause themselves
    ONTOLOGICAL = auto()     # Object with no origin
    TEMPORAL_SPLIT = auto()  # Timeline bifurcation
    FIXED_POINT = auto()     # Unchangeable event


class TimelineState(Enum):
    """State of a timeline."""
    STABLE = auto()      # Consistent causality
    UNSTABLE = auto()    # Paradox detected
    BRANCHED = auto()    # Split into multiple
    COLLAPSED = auto()   # Destroyed by paradox
    QUANTUM = auto()     # Superposition of states


# ============================================================================
# TEMPORAL EVENT
# ============================================================================

@dataclass
class TemporalEvent:
    """
    An event in spacetime.
    """
    id: str
    timestamp: float
    description: str
    causes: List[str] = field(default_factory=list)
    effects: List[str] = field(default_factory=list)
    probability: float = 1.0
    is_fixed: bool = False  # Fixed point in time
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other):
        return self.timestamp < other.timestamp


@dataclass
class CausalLink:
    """
    Causal relationship between events.
    """
    cause_id: str
    effect_id: str
    strength: float = 1.0  # 0-1, probability of causation
    delay: float = 0.0     # Time between cause and effect
    is_necessary: bool = True  # Effect requires cause


# ============================================================================
# TIMELINE
# ============================================================================

class Timeline:
    """
    A single timeline / worldline.

    "Ba'el navigates timelines." — Ba'el
    """

    def __init__(self, name: str = "prime"):
        """Initialize timeline."""
        self._name = name
        self._events: Dict[str, TemporalEvent] = {}
        self._causal_links: List[CausalLink] = []
        self._state = TimelineState.STABLE
        self._branch_point: Optional[float] = None
        self._parent_timeline: Optional[str] = None
        self._lock = threading.RLock()

    @property
    def name(self) -> str:
        return self._name

    @property
    def state(self) -> TimelineState:
        return self._state

    def add_event(self, event: TemporalEvent) -> None:
        """Add event to timeline."""
        with self._lock:
            self._events[event.id] = event

    def add_causal_link(self, link: CausalLink) -> None:
        """Add causal relationship."""
        with self._lock:
            self._causal_links.append(link)

            # Update event references
            if link.cause_id in self._events:
                self._events[link.cause_id].effects.append(link.effect_id)
            if link.effect_id in self._events:
                self._events[link.effect_id].causes.append(link.cause_id)

    def get_events_in_range(
        self,
        start: float,
        end: float
    ) -> List[TemporalEvent]:
        """Get events in time range."""
        with self._lock:
            return sorted([
                e for e in self._events.values()
                if start <= e.timestamp <= end
            ])

    def get_causal_chain(self, event_id: str) -> List[TemporalEvent]:
        """Get full causal chain leading to event."""
        with self._lock:
            if event_id not in self._events:
                return []

            chain = []
            visited = set()
            queue = [event_id]

            while queue:
                current_id = queue.pop(0)
                if current_id in visited:
                    continue
                visited.add(current_id)

                if current_id in self._events:
                    event = self._events[current_id]
                    chain.append(event)
                    queue.extend(event.causes)

            return sorted(chain, key=lambda e: e.timestamp)

    def detect_paradox(self) -> Optional[Tuple[ParadoxType, List[str]]]:
        """
        Detect temporal paradoxes.

        Returns paradox type and involved events.
        """
        with self._lock:
            # Check for causal loops
            for event_id in self._events:
                cycle = self._find_causal_cycle(event_id)
                if cycle:
                    # Determine paradox type
                    if self._is_grandfather_paradox(cycle):
                        return (ParadoxType.GRANDFATHER, cycle)
                    else:
                        return (ParadoxType.BOOTSTRAP, cycle)

            # Check for backward causation
            for link in self._causal_links:
                if link.cause_id in self._events and link.effect_id in self._events:
                    cause = self._events[link.cause_id]
                    effect = self._events[link.effect_id]
                    if cause.timestamp > effect.timestamp:
                        return (ParadoxType.PREDESTINATION, [link.cause_id, link.effect_id])

            return None

    def _find_causal_cycle(self, start_id: str) -> Optional[List[str]]:
        """Find causal cycle starting from event."""
        visited = set()
        path = []

        def dfs(event_id: str) -> Optional[List[str]]:
            if event_id in visited:
                if event_id == start_id:
                    return path + [event_id]
                return None

            visited.add(event_id)
            path.append(event_id)

            if event_id in self._events:
                for effect_id in self._events[event_id].effects:
                    cycle = dfs(effect_id)
                    if cycle:
                        return cycle

            path.pop()
            return None

        return dfs(start_id)

    def _is_grandfather_paradox(self, cycle: List[str]) -> bool:
        """Check if cycle is grandfather paradox (self-preventing)."""
        # Grandfather paradox involves negation of cause
        for event_id in cycle:
            if event_id in self._events:
                event = self._events[event_id]
                if event.metadata.get('negates_cause', False):
                    return True
        return False

    def branch(self, branch_point: float, name: str) -> 'Timeline':
        """
        Create branch at given time.

        Returns new timeline branching from this one.
        """
        with self._lock:
            new_timeline = Timeline(name)
            new_timeline._parent_timeline = self._name
            new_timeline._branch_point = branch_point

            # Copy events before branch point
            for event in self._events.values():
                if event.timestamp < branch_point:
                    new_timeline.add_event(copy.deepcopy(event))

            # Copy relevant causal links
            for link in self._causal_links:
                cause_time = self._events.get(link.cause_id, TemporalEvent("", float('inf'), "")).timestamp
                if cause_time < branch_point:
                    new_timeline.add_causal_link(copy.deepcopy(link))

            self._state = TimelineState.BRANCHED
            return new_timeline


# ============================================================================
# MULTIVERSE MANAGER
# ============================================================================

class TemporalMultiverse:
    """
    Manage multiple timelines.

    "Ba'el oversees the multiverse." — Ba'el
    """

    def __init__(self):
        """Initialize multiverse."""
        self._timelines: Dict[str, Timeline] = {}
        self._active_timeline: str = "prime"
        self._lock = threading.RLock()

        # Create prime timeline
        self._timelines["prime"] = Timeline("prime")

    def get_timeline(self, name: str) -> Optional[Timeline]:
        """Get timeline by name."""
        return self._timelines.get(name)

    def get_active_timeline(self) -> Timeline:
        """Get currently active timeline."""
        return self._timelines[self._active_timeline]

    def switch_timeline(self, name: str) -> bool:
        """Switch to different timeline."""
        with self._lock:
            if name in self._timelines:
                self._active_timeline = name
                return True
            return False

    def create_branch(
        self,
        branch_point: float,
        name: str
    ) -> Timeline:
        """Create new timeline branch."""
        with self._lock:
            active = self.get_active_timeline()
            new_timeline = active.branch(branch_point, name)
            self._timelines[name] = new_timeline
            return new_timeline

    def merge_timelines(
        self,
        name1: str,
        name2: str,
        merge_point: float
    ) -> Optional[Timeline]:
        """
        Attempt to merge two timelines.

        Only possible if no paradoxes result.
        """
        with self._lock:
            if name1 not in self._timelines or name2 not in self._timelines:
                return None

            t1 = self._timelines[name1]
            t2 = self._timelines[name2]

            # Create merged timeline
            merged = Timeline(f"merged_{name1}_{name2}")

            # Add events from both
            for event in t1._events.values():
                merged.add_event(copy.deepcopy(event))

            for event in t2._events.values():
                if event.id not in merged._events:
                    merged.add_event(copy.deepcopy(event))

            # Check for paradoxes
            paradox = merged.detect_paradox()
            if paradox:
                logger.warning(f"Cannot merge: {paradox[0]} paradox detected")
                return None

            self._timelines[merged._name] = merged
            return merged

    def find_divergence_point(
        self,
        name1: str,
        name2: str
    ) -> Optional[float]:
        """Find where two timelines diverge."""
        with self._lock:
            if name1 not in self._timelines or name2 not in self._timelines:
                return None

            t1 = self._timelines[name1]
            t2 = self._timelines[name2]

            events1 = sorted(t1._events.values())
            events2 = sorted(t2._events.values())

            for e1, e2 in zip(events1, events2):
                if e1.id != e2.id or e1.description != e2.description:
                    return min(e1.timestamp, e2.timestamp)

            return None


# ============================================================================
# TEMPORAL LOGIC ENGINE
# ============================================================================

class TemporalLogicEngine:
    """
    Evaluate Linear Temporal Logic (LTL) formulas.

    "Ba'el reasons temporally." — Ba'el
    """

    def __init__(self, timeline: Timeline):
        """Initialize with timeline."""
        self._timeline = timeline
        self._lock = threading.RLock()

    def check(
        self,
        operator: TemporalOperator,
        predicate: Callable[[TemporalEvent], bool],
        start_time: float = 0.0,
        end_time: float = float('inf')
    ) -> bool:
        """
        Check temporal formula.

        Args:
            operator: Temporal operator to check
            predicate: Property to check for each event
            start_time: Start of time window
            end_time: End of time window
        """
        with self._lock:
            events = self._timeline.get_events_in_range(start_time, end_time)

            if operator == TemporalOperator.ALWAYS:
                # □P: P holds at all times
                return all(predicate(e) for e in events)

            elif operator == TemporalOperator.EVENTUALLY:
                # ◇P: P holds at some time
                return any(predicate(e) for e in events)

            elif operator == TemporalOperator.NEXT:
                # ○P: P holds at next time step
                future = [e for e in events if e.timestamp > start_time]
                if future:
                    return predicate(min(future))
                return False

            else:
                logger.warning(f"Unsupported operator: {operator}")
                return False

    def check_until(
        self,
        predicate_p: Callable[[TemporalEvent], bool],
        predicate_q: Callable[[TemporalEvent], bool],
        start_time: float = 0.0,
        end_time: float = float('inf')
    ) -> bool:
        """
        Check P U Q (P until Q).

        P holds until Q becomes true.
        """
        with self._lock:
            events = sorted(self._timeline.get_events_in_range(start_time, end_time))

            for i, event in enumerate(events):
                if predicate_q(event):
                    # Q holds, check P held until now
                    return all(predicate_p(e) for e in events[:i])

            return False  # Q never held


# ============================================================================
# PARADOX RESOLVER
# ============================================================================

class ParadoxResolver:
    """
    Resolve temporal paradoxes.

    "Ba'el resolves the impossible." — Ba'el
    """

    def __init__(self, multiverse: TemporalMultiverse):
        """Initialize resolver."""
        self._multiverse = multiverse
        self._lock = threading.RLock()

    def resolve(
        self,
        timeline_name: str
    ) -> Tuple[bool, str]:
        """
        Attempt to resolve paradox in timeline.

        Returns (success, resolution_method).
        """
        with self._lock:
            timeline = self._multiverse.get_timeline(timeline_name)
            if not timeline:
                return (False, "Timeline not found")

            paradox = timeline.detect_paradox()
            if not paradox:
                return (True, "No paradox detected")

            paradox_type, events = paradox

            if paradox_type == ParadoxType.GRANDFATHER:
                return self._resolve_grandfather(timeline, events)

            elif paradox_type == ParadoxType.BOOTSTRAP:
                return self._resolve_bootstrap(timeline, events)

            elif paradox_type == ParadoxType.PREDESTINATION:
                return self._resolve_predestination(timeline, events)

            else:
                return (False, f"Cannot resolve {paradox_type}")

    def _resolve_grandfather(
        self,
        timeline: Timeline,
        events: List[str]
    ) -> Tuple[bool, str]:
        """
        Resolve grandfather paradox.

        Solution: Create branch where negation doesn't occur.
        """
        # Find the negating event
        for event_id in events:
            event = timeline._events.get(event_id)
            if event and event.metadata.get('negates_cause', False):
                # Create branch before this event
                branch_point = event.timestamp - 0.001
                new_timeline = self._multiverse.create_branch(
                    branch_point,
                    f"resolved_{timeline._name}"
                )
                return (True, f"Created branch at {branch_point}")

        return (False, "Could not identify negating event")

    def _resolve_bootstrap(
        self,
        timeline: Timeline,
        events: List[str]
    ) -> Tuple[bool, str]:
        """
        Resolve bootstrap paradox.

        Solution: Accept as stable causal loop (Novikov self-consistency).
        """
        # Bootstrap paradoxes can be stable
        timeline._state = TimelineState.STABLE
        return (True, "Accepted as stable causal loop (Novikov)")

    def _resolve_predestination(
        self,
        timeline: Timeline,
        events: List[str]
    ) -> Tuple[bool, str]:
        """
        Resolve predestination paradox.

        Solution: Reinterpret as fixed point.
        """
        for event_id in events:
            if event_id in timeline._events:
                timeline._events[event_id].is_fixed = True

        return (True, "Events marked as fixed points")


# ============================================================================
# TIME TRAVEL SIMULATOR
# ============================================================================

class TimeTravelSimulator:
    """
    Simulate time travel scenarios.

    "Ba'el travels through time." — Ba'el
    """

    def __init__(self):
        """Initialize simulator."""
        self._multiverse = TemporalMultiverse()
        self._resolver = ParadoxResolver(self._multiverse)
        self._lock = threading.RLock()

    @property
    def multiverse(self) -> TemporalMultiverse:
        return self._multiverse

    def travel(
        self,
        from_time: float,
        to_time: float,
        traveler_id: str,
        changes: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """
        Perform time travel.

        Args:
            from_time: Departure time
            to_time: Destination time
            traveler_id: Who is traveling
            changes: Changes to make at destination

        Returns (success, result_description).
        """
        with self._lock:
            timeline = self._multiverse.get_active_timeline()

            # Create departure event
            departure = TemporalEvent(
                id=f"departure_{traveler_id}_{from_time}",
                timestamp=from_time,
                description=f"{traveler_id} departs to time {to_time}"
            )
            timeline.add_event(departure)

            # Create arrival event
            arrival = TemporalEvent(
                id=f"arrival_{traveler_id}_{to_time}",
                timestamp=to_time,
                description=f"{traveler_id} arrives from time {from_time}",
                metadata={'changes': changes or {}}
            )
            timeline.add_event(arrival)

            # Link causally
            link = CausalLink(
                cause_id=departure.id,
                effect_id=arrival.id,
                delay=to_time - from_time
            )
            timeline.add_causal_link(link)

            # Apply changes
            if changes and to_time < from_time:
                # Past travel with changes
                self._apply_changes(timeline, to_time, changes)

            # Check for paradoxes
            paradox = timeline.detect_paradox()
            if paradox:
                # Try to resolve
                success, method = self._resolver.resolve(timeline._name)
                if success:
                    return (True, f"Travel successful, paradox resolved via {method}")
                else:
                    return (False, f"Paradox detected: {paradox[0]}")

            return (True, "Travel successful, no paradox")

    def _apply_changes(
        self,
        timeline: Timeline,
        time: float,
        changes: Dict[str, Any]
    ) -> None:
        """Apply changes from time travel."""
        for key, value in changes.items():
            if key == 'prevent_event':
                # Try to prevent an event
                event_id = value
                if event_id in timeline._events:
                    # Mark as prevented
                    timeline._events[event_id].probability = 0.0

            elif key == 'add_event':
                # Add new event
                event = TemporalEvent(
                    id=value.get('id', f"added_{time}"),
                    timestamp=time + 0.001,
                    description=value.get('description', 'Time traveler intervention'),
                    metadata=value
                )
                timeline.add_event(event)

    def run_scenario(
        self,
        scenario: List[Dict[str, Any]]
    ) -> List[Tuple[bool, str]]:
        """
        Run a time travel scenario.

        Each item has: from_time, to_time, traveler, changes
        """
        results = []

        for step in scenario:
            result = self.travel(
                from_time=step.get('from_time', 0),
                to_time=step.get('to_time', 0),
                traveler_id=step.get('traveler', 'agent'),
                changes=step.get('changes')
            )
            results.append(result)

        return results


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_timeline(name: str = "prime") -> Timeline:
    """Create new timeline."""
    return Timeline(name)


def create_multiverse() -> TemporalMultiverse:
    """Create temporal multiverse."""
    return TemporalMultiverse()


def create_time_travel_simulator() -> TimeTravelSimulator:
    """Create time travel simulator."""
    return TimeTravelSimulator()


def check_temporal_consistency(timeline: Timeline) -> bool:
    """Check if timeline is temporally consistent."""
    return timeline.detect_paradox() is None
