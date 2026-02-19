"""
BAEL Vector Clock Engine Implementation
========================================

Distributed causality tracking.

"Ba'el sees the true order of events across realms." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid
import copy

logger = logging.getLogger("BAEL.VectorClock")


# ============================================================================
# ENUMS
# ============================================================================

class CausalOrder(Enum):
    """Causal ordering relationship."""
    BEFORE = "before"        # A happened before B
    AFTER = "after"          # A happened after B
    CONCURRENT = "concurrent"  # A and B are concurrent


# ============================================================================
# VECTOR CLOCK
# ============================================================================

class VectorClock:
    """
    Vector clock for distributed causality.

    Features:
    - Tracks logical time across nodes
    - Determines causal ordering
    - Detects concurrent events

    "Ba'el measures time across all dimensions." — Ba'el
    """

    def __init__(self, node_id: Optional[str] = None):
        """Initialize vector clock."""
        self.node_id = node_id or str(uuid.uuid4())
        self._clock: Dict[str, int] = {}
        self._lock = threading.RLock()

    def increment(self, node_id: Optional[str] = None) -> 'VectorClock':
        """
        Increment clock for a node.

        Args:
            node_id: Node to increment (default: self)

        Returns:
            Self for chaining
        """
        node = node_id or self.node_id

        with self._lock:
            self._clock[node] = self._clock.get(node, 0) + 1

        return self

    def get(self, node_id: str) -> int:
        """Get clock value for a node."""
        return self._clock.get(node_id, 0)

    def set(self, node_id: str, value: int) -> None:
        """Set clock value for a node."""
        with self._lock:
            self._clock[node_id] = value

    def merge(self, other: 'VectorClock') -> 'VectorClock':
        """
        Merge with another vector clock (take max of each).

        Args:
            other: Other vector clock

        Returns:
            Self for chaining
        """
        with self._lock:
            for node_id, value in other._clock.items():
                self._clock[node_id] = max(self._clock.get(node_id, 0), value)

        return self

    def update(self, other: 'VectorClock') -> 'VectorClock':
        """
        Update from another clock and increment self.

        Standard receive operation.

        Returns:
            Self for chaining
        """
        self.merge(other)
        self.increment()
        return self

    def compare(self, other: 'VectorClock') -> CausalOrder:
        """
        Compare with another vector clock.

        Args:
            other: Other vector clock

        Returns:
            Causal ordering relationship
        """
        all_nodes = set(self._clock.keys()) | set(other._clock.keys())

        less_or_equal = True
        greater_or_equal = True

        for node_id in all_nodes:
            self_value = self._clock.get(node_id, 0)
            other_value = other._clock.get(node_id, 0)

            if self_value < other_value:
                greater_or_equal = False
            if self_value > other_value:
                less_or_equal = False

        if less_or_equal and not greater_or_equal:
            return CausalOrder.BEFORE
        elif greater_or_equal and not less_or_equal:
            return CausalOrder.AFTER
        elif less_or_equal and greater_or_equal:
            # Equal clocks - treat as concurrent for safety
            return CausalOrder.CONCURRENT
        else:
            return CausalOrder.CONCURRENT

    def happens_before(self, other: 'VectorClock') -> bool:
        """Check if self happens before other."""
        return self.compare(other) == CausalOrder.BEFORE

    def happens_after(self, other: 'VectorClock') -> bool:
        """Check if self happens after other."""
        return self.compare(other) == CausalOrder.AFTER

    def is_concurrent_with(self, other: 'VectorClock') -> bool:
        """Check if self is concurrent with other."""
        return self.compare(other) == CausalOrder.CONCURRENT

    def copy(self) -> 'VectorClock':
        """Create a copy of this clock."""
        new_clock = VectorClock(self.node_id)
        new_clock._clock = copy.deepcopy(self._clock)
        return new_clock

    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary."""
        return copy.deepcopy(self._clock)

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, int],
        node_id: Optional[str] = None
    ) -> 'VectorClock':
        """Create from dictionary."""
        clock = cls(node_id)
        clock._clock = copy.deepcopy(data)
        return clock

    def __repr__(self) -> str:
        return f"VectorClock({self._clock})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VectorClock):
            return False
        return self._clock == other._clock


# ============================================================================
# VERSIONED VALUE
# ============================================================================

@dataclass
class VersionedValue:
    """A value with vector clock version."""
    value: Any
    clock: VectorClock
    node_id: str
    timestamp: float = field(default_factory=lambda: __import__('time').time())

    def update(self, new_value: Any, node_id: str) -> 'VersionedValue':
        """Create updated version."""
        new_clock = self.clock.copy()
        new_clock.increment(node_id)

        return VersionedValue(
            value=new_value,
            clock=new_clock,
            node_id=node_id
        )

    def compare(self, other: 'VersionedValue') -> CausalOrder:
        """Compare with another versioned value."""
        return self.clock.compare(other.clock)


# ============================================================================
# VECTOR CLOCK STORE
# ============================================================================

class VectorClockStore:
    """
    Key-value store with vector clock versioning.

    Features:
    - Conflict detection
    - Sibling tracking
    - Automatic resolution

    "Ba'el maintains truth across parallel realities." — Ba'el
    """

    def __init__(
        self,
        node_id: str,
        conflict_resolver: Optional[callable] = None
    ):
        """Initialize store."""
        self.node_id = node_id
        self._conflict_resolver = conflict_resolver or self._default_resolver

        # Key -> List of versioned values (siblings)
        self._data: Dict[str, List[VersionedValue]] = {}

        self._lock = threading.RLock()

        self._stats = {
            'puts': 0,
            'gets': 0,
            'conflicts': 0,
            'resolutions': 0
        }

    def put(
        self,
        key: str,
        value: Any,
        clock: Optional[VectorClock] = None
    ) -> VersionedValue:
        """
        Put a value with vector clock.

        Args:
            key: Key
            value: Value
            clock: Optional clock context

        Returns:
            Versioned value
        """
        with self._lock:
            if key in self._data:
                siblings = self._data[key]

                if clock:
                    # Check for conflicts
                    new_siblings = []

                    for sibling in siblings:
                        order = clock.compare(sibling.clock)

                        if order == CausalOrder.AFTER:
                            # New value supersedes sibling
                            continue
                        elif order == CausalOrder.BEFORE:
                            # Sibling supersedes new value - ignore new
                            self._stats['puts'] += 1
                            return sibling
                        else:
                            # Concurrent - keep sibling
                            new_siblings.append(sibling)
                            self._stats['conflicts'] += 1

                    # Add new value
                    new_clock = clock.copy()
                    new_clock.increment(self.node_id)

                    versioned = VersionedValue(
                        value=value,
                        clock=new_clock,
                        node_id=self.node_id
                    )
                    new_siblings.append(versioned)

                    # Try to resolve conflicts
                    if len(new_siblings) > 1:
                        resolved = self._resolve_conflicts(key, new_siblings)
                        self._data[key] = resolved
                    else:
                        self._data[key] = new_siblings

                else:
                    # No context - create fresh with merged clock
                    merged_clock = VectorClock(self.node_id)
                    for sibling in siblings:
                        merged_clock.merge(sibling.clock)
                    merged_clock.increment(self.node_id)

                    versioned = VersionedValue(
                        value=value,
                        clock=merged_clock,
                        node_id=self.node_id
                    )
                    self._data[key] = [versioned]

            else:
                # New key
                new_clock = VectorClock(self.node_id)
                new_clock.increment(self.node_id)

                versioned = VersionedValue(
                    value=value,
                    clock=new_clock,
                    node_id=self.node_id
                )
                self._data[key] = [versioned]

            self._stats['puts'] += 1

            return self._data[key][0]

    def get(self, key: str) -> Optional[List[VersionedValue]]:
        """
        Get values for a key.

        Returns list of siblings if there are conflicts.

        Args:
            key: Key

        Returns:
            List of versioned values or None
        """
        self._stats['gets'] += 1
        return self._data.get(key)

    def get_value(self, key: str) -> Optional[Any]:
        """Get single value (first sibling)."""
        siblings = self.get(key)
        if siblings:
            return siblings[0].value
        return None

    def has_conflicts(self, key: str) -> bool:
        """Check if key has unresolved conflicts."""
        siblings = self._data.get(key)
        return siblings is not None and len(siblings) > 1

    def resolve(
        self,
        key: str,
        resolved_value: Any
    ) -> VersionedValue:
        """
        Manually resolve conflicts.

        Args:
            key: Key
            resolved_value: Resolved value

        Returns:
            New versioned value
        """
        siblings = self._data.get(key, [])

        # Merge all clocks
        merged_clock = VectorClock(self.node_id)
        for sibling in siblings:
            merged_clock.merge(sibling.clock)
        merged_clock.increment(self.node_id)

        versioned = VersionedValue(
            value=resolved_value,
            clock=merged_clock,
            node_id=self.node_id
        )

        self._data[key] = [versioned]
        self._stats['resolutions'] += 1

        return versioned

    def _resolve_conflicts(
        self,
        key: str,
        siblings: List[VersionedValue]
    ) -> List[VersionedValue]:
        """Try to resolve conflicts automatically."""
        if len(siblings) <= 1:
            return siblings

        resolved = self._conflict_resolver(key, siblings)

        if resolved:
            self._stats['resolutions'] += 1
            return [resolved]

        return siblings

    def _default_resolver(
        self,
        key: str,
        siblings: List[VersionedValue]
    ) -> Optional[VersionedValue]:
        """Default resolver: take latest by timestamp."""
        if not siblings:
            return None

        # Take latest by timestamp
        latest = max(siblings, key=lambda s: s.timestamp)

        # Create new version with merged clock
        merged_clock = VectorClock(self.node_id)
        for sibling in siblings:
            merged_clock.merge(sibling.clock)
        merged_clock.increment(self.node_id)

        return VersionedValue(
            value=latest.value,
            clock=merged_clock,
            node_id=self.node_id
        )

    def delete(self, key: str) -> bool:
        """Delete a key."""
        with self._lock:
            if key in self._data:
                del self._data[key]
                return True
        return False

    def keys(self) -> List[str]:
        """Get all keys."""
        return list(self._data.keys())

    def get_stats(self) -> Dict[str, Any]:
        """Get store statistics."""
        return {
            'key_count': len(self._data),
            'conflict_keys': sum(1 for k in self._data if self.has_conflicts(k)),
            **self._stats
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_vector_clock(node_id: Optional[str] = None) -> VectorClock:
    """Create a new vector clock."""
    return VectorClock(node_id)


def create_store(
    node_id: str,
    resolver: Optional[callable] = None
) -> VectorClockStore:
    """Create a vector clock store."""
    return VectorClockStore(node_id, resolver)
