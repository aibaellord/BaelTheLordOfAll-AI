"""
BAEL CRDT (Conflict-free Replicated Data Types) Engine
========================================================

Eventual consistency without coordination.

"Ba'el resolves all conflicts without negotiation." — Ba'el
"""

import logging
import threading
import time
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid
import copy

logger = logging.getLogger("BAEL.CRDT")


# ============================================================================
# ENUMS
# ============================================================================

class CRDTType(Enum):
    """CRDT types."""
    G_COUNTER = "g_counter"       # Grow-only counter
    PN_COUNTER = "pn_counter"     # Positive-negative counter
    G_SET = "g_set"               # Grow-only set
    TWO_P_SET = "2p_set"          # Two-phase set
    OR_SET = "or_set"             # Observed-remove set
    LWW_REGISTER = "lww_register"  # Last-write-wins register
    MV_REGISTER = "mv_register"   # Multi-value register
    LWW_MAP = "lww_map"           # Last-write-wins map


# ============================================================================
# BASE CRDT
# ============================================================================

class CRDT:
    """Base CRDT interface."""

    def merge(self, other: 'CRDT') -> 'CRDT':
        """Merge with another CRDT."""
        raise NotImplementedError

    def value(self) -> Any:
        """Get current value."""
        raise NotImplementedError

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        raise NotImplementedError

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CRDT':
        """Deserialize from dict."""
        raise NotImplementedError


# ============================================================================
# G-COUNTER (Grow-only Counter)
# ============================================================================

class GCounter(CRDT):
    """
    Grow-only counter CRDT.

    Only supports increment, never decrement.

    "Ba'el counts eternally forward." — Ba'el
    """

    def __init__(self, node_id: str):
        """Initialize G-Counter."""
        self.node_id = node_id
        self._counts: Dict[str, int] = {}

    def increment(self, amount: int = 1) -> int:
        """Increment the counter."""
        if amount < 0:
            raise ValueError("G-Counter can only increment")

        self._counts[self.node_id] = self._counts.get(self.node_id, 0) + amount
        return self.value()

    def value(self) -> int:
        """Get counter value."""
        return sum(self._counts.values())

    def merge(self, other: 'GCounter') -> 'GCounter':
        """Merge with another G-Counter."""
        all_nodes = set(self._counts.keys()) | set(other._counts.keys())

        for node in all_nodes:
            self._counts[node] = max(
                self._counts.get(node, 0),
                other._counts.get(node, 0)
            )

        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': 'g_counter',
            'node_id': self.node_id,
            'counts': self._counts
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GCounter':
        counter = cls(data['node_id'])
        counter._counts = data['counts']
        return counter


# ============================================================================
# PN-COUNTER (Positive-Negative Counter)
# ============================================================================

class PNCounter(CRDT):
    """
    Positive-negative counter CRDT.

    Supports both increment and decrement.

    "Ba'el measures both gain and loss." — Ba'el
    """

    def __init__(self, node_id: str):
        """Initialize PN-Counter."""
        self.node_id = node_id
        self._p = GCounter(node_id)  # Positive
        self._n = GCounter(node_id)  # Negative

    def increment(self, amount: int = 1) -> int:
        """Increment the counter."""
        self._p.increment(amount)
        return self.value()

    def decrement(self, amount: int = 1) -> int:
        """Decrement the counter."""
        self._n.increment(amount)
        return self.value()

    def value(self) -> int:
        """Get counter value."""
        return self._p.value() - self._n.value()

    def merge(self, other: 'PNCounter') -> 'PNCounter':
        """Merge with another PN-Counter."""
        self._p.merge(other._p)
        self._n.merge(other._n)
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': 'pn_counter',
            'node_id': self.node_id,
            'p': self._p.to_dict(),
            'n': self._n.to_dict()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PNCounter':
        counter = cls(data['node_id'])
        counter._p = GCounter.from_dict(data['p'])
        counter._n = GCounter.from_dict(data['n'])
        return counter


# ============================================================================
# G-SET (Grow-only Set)
# ============================================================================

class GSet(CRDT):
    """
    Grow-only set CRDT.

    Elements can only be added, never removed.

    "Ba'el collects, never discards." — Ba'el
    """

    def __init__(self):
        """Initialize G-Set."""
        self._elements: Set[Any] = set()

    def add(self, element: Any) -> bool:
        """Add an element."""
        # Must be hashable
        if element not in self._elements:
            self._elements.add(element)
            return True
        return False

    def contains(self, element: Any) -> bool:
        """Check if element exists."""
        return element in self._elements

    def value(self) -> FrozenSet[Any]:
        """Get set value."""
        return frozenset(self._elements)

    def merge(self, other: 'GSet') -> 'GSet':
        """Merge with another G-Set."""
        self._elements = self._elements | other._elements
        return self

    def __len__(self) -> int:
        return len(self._elements)

    def __iter__(self):
        return iter(self._elements)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': 'g_set',
            'elements': list(self._elements)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GSet':
        gset = cls()
        gset._elements = set(data['elements'])
        return gset


# ============================================================================
# 2P-SET (Two-Phase Set)
# ============================================================================

class TwoPSet(CRDT):
    """
    Two-phase set CRDT.

    Elements can be added and removed, but removed elements
    can never be re-added.

    "Ba'el remembers both presence and absence." — Ba'el
    """

    def __init__(self):
        """Initialize 2P-Set."""
        self._added = GSet()
        self._removed = GSet()

    def add(self, element: Any) -> bool:
        """Add an element."""
        if element in self._removed._elements:
            return False  # Already removed
        return self._added.add(element)

    def remove(self, element: Any) -> bool:
        """Remove an element."""
        if element in self._added._elements:
            self._removed.add(element)
            return True
        return False

    def contains(self, element: Any) -> bool:
        """Check if element exists."""
        return (
            element in self._added._elements and
            element not in self._removed._elements
        )

    def value(self) -> FrozenSet[Any]:
        """Get set value."""
        return frozenset(
            self._added._elements - self._removed._elements
        )

    def merge(self, other: 'TwoPSet') -> 'TwoPSet':
        """Merge with another 2P-Set."""
        self._added.merge(other._added)
        self._removed.merge(other._removed)
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': '2p_set',
            'added': self._added.to_dict(),
            'removed': self._removed.to_dict()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TwoPSet':
        tpset = cls()
        tpset._added = GSet.from_dict(data['added'])
        tpset._removed = GSet.from_dict(data['removed'])
        return tpset


# ============================================================================
# OR-SET (Observed-Remove Set)
# ============================================================================

class ORSet(CRDT):
    """
    Observed-remove set CRDT.

    Elements can be added and removed multiple times.
    Each add creates a unique tag.

    "Ba'el observes all additions and removals." — Ba'el
    """

    def __init__(self, node_id: str):
        """Initialize OR-Set."""
        self.node_id = node_id
        # element -> set of (node_id, unique_tag)
        self._elements: Dict[Any, Set[Tuple[str, str]]] = {}
        self._tag_counter = 0

    def _generate_tag(self) -> str:
        """Generate unique tag."""
        self._tag_counter += 1
        return f"{self.node_id}:{self._tag_counter}"

    def add(self, element: Any) -> str:
        """Add an element, returns tag."""
        tag = self._generate_tag()

        if element not in self._elements:
            self._elements[element] = set()

        self._elements[element].add((self.node_id, tag))

        return tag

    def remove(self, element: Any) -> bool:
        """Remove all occurrences of element."""
        if element in self._elements and self._elements[element]:
            self._elements[element] = set()
            return True
        return False

    def contains(self, element: Any) -> bool:
        """Check if element exists."""
        return (
            element in self._elements and
            len(self._elements[element]) > 0
        )

    def value(self) -> FrozenSet[Any]:
        """Get set value."""
        return frozenset(
            e for e, tags in self._elements.items()
            if len(tags) > 0
        )

    def merge(self, other: 'ORSet') -> 'ORSet':
        """Merge with another OR-Set."""
        all_elements = set(self._elements.keys()) | set(other._elements.keys())

        for element in all_elements:
            self_tags = self._elements.get(element, set())
            other_tags = other._elements.get(element, set())

            # Union of tags
            self._elements[element] = self_tags | other_tags

        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': 'or_set',
            'node_id': self.node_id,
            'elements': {
                str(k): list(v)
                for k, v in self._elements.items()
            }
        }


# ============================================================================
# LWW-REGISTER (Last-Write-Wins Register)
# ============================================================================

class LWWRegister(CRDT):
    """
    Last-write-wins register CRDT.

    Concurrent writes resolved by timestamp.

    "Ba'el respects the latest proclamation." — Ba'el
    """

    def __init__(self, node_id: str):
        """Initialize LWW-Register."""
        self.node_id = node_id
        self._value: Any = None
        self._timestamp: float = 0.0

    def set(self, value: Any, timestamp: Optional[float] = None) -> bool:
        """Set the value."""
        ts = timestamp or time.time()

        if ts >= self._timestamp:
            self._value = value
            self._timestamp = ts
            return True

        return False

    def get(self) -> Any:
        """Get the value."""
        return self._value

    def value(self) -> Any:
        """Get the value."""
        return self._value

    def merge(self, other: 'LWWRegister') -> 'LWWRegister':
        """Merge with another LWW-Register."""
        if other._timestamp > self._timestamp:
            self._value = other._value
            self._timestamp = other._timestamp
        elif other._timestamp == self._timestamp:
            # Tie-breaker: compare node IDs
            if other.node_id > self.node_id:
                self._value = other._value

        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': 'lww_register',
            'node_id': self.node_id,
            'value': self._value,
            'timestamp': self._timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LWWRegister':
        reg = cls(data['node_id'])
        reg._value = data['value']
        reg._timestamp = data['timestamp']
        return reg


# ============================================================================
# LWW-MAP (Last-Write-Wins Map)
# ============================================================================

class LWWMap(CRDT):
    """
    Last-write-wins map CRDT.

    Each key has an LWW-Register.

    "Ba'el maintains the authoritative record." — Ba'el
    """

    def __init__(self, node_id: str):
        """Initialize LWW-Map."""
        self.node_id = node_id
        self._registers: Dict[str, LWWRegister] = {}

    def set(
        self,
        key: str,
        value: Any,
        timestamp: Optional[float] = None
    ) -> bool:
        """Set a key-value pair."""
        if key not in self._registers:
            self._registers[key] = LWWRegister(self.node_id)

        return self._registers[key].set(value, timestamp)

    def get(self, key: str) -> Optional[Any]:
        """Get value for key."""
        if key in self._registers:
            return self._registers[key].get()
        return None

    def delete(self, key: str, timestamp: Optional[float] = None) -> bool:
        """Delete a key (sets to None)."""
        return self.set(key, None, timestamp)

    def keys(self) -> List[str]:
        """Get all keys with non-None values."""
        return [
            k for k, v in self._registers.items()
            if v.get() is not None
        ]

    def value(self) -> Dict[str, Any]:
        """Get map value."""
        return {
            k: v.get()
            for k, v in self._registers.items()
            if v.get() is not None
        }

    def merge(self, other: 'LWWMap') -> 'LWWMap':
        """Merge with another LWW-Map."""
        all_keys = set(self._registers.keys()) | set(other._registers.keys())

        for key in all_keys:
            if key in other._registers:
                if key in self._registers:
                    self._registers[key].merge(other._registers[key])
                else:
                    self._registers[key] = copy.deepcopy(other._registers[key])

        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': 'lww_map',
            'node_id': self.node_id,
            'registers': {
                k: v.to_dict() for k, v in self._registers.items()
            }
        }


# ============================================================================
# CRDT MANAGER
# ============================================================================

class CRDTManager:
    """
    CRDT manager.

    Creates, stores, and synchronizes CRDTs.

    "Ba'el orchestrates eventual consistency." — Ba'el
    """

    def __init__(self, node_id: str):
        """Initialize CRDT manager."""
        self.node_id = node_id
        self._crdts: Dict[str, CRDT] = {}
        self._lock = threading.RLock()

        self._stats = {
            'crdts_created': 0,
            'merges': 0
        }

    def create(
        self,
        name: str,
        crdt_type: CRDTType
    ) -> CRDT:
        """Create a new CRDT."""
        if crdt_type == CRDTType.G_COUNTER:
            crdt = GCounter(self.node_id)
        elif crdt_type == CRDTType.PN_COUNTER:
            crdt = PNCounter(self.node_id)
        elif crdt_type == CRDTType.G_SET:
            crdt = GSet()
        elif crdt_type == CRDTType.TWO_P_SET:
            crdt = TwoPSet()
        elif crdt_type == CRDTType.OR_SET:
            crdt = ORSet(self.node_id)
        elif crdt_type == CRDTType.LWW_REGISTER:
            crdt = LWWRegister(self.node_id)
        elif crdt_type == CRDTType.LWW_MAP:
            crdt = LWWMap(self.node_id)
        else:
            raise ValueError(f"Unknown CRDT type: {crdt_type}")

        with self._lock:
            self._crdts[name] = crdt
            self._stats['crdts_created'] += 1

        return crdt

    def get(self, name: str) -> Optional[CRDT]:
        """Get CRDT by name."""
        return self._crdts.get(name)

    def get_or_create(
        self,
        name: str,
        crdt_type: CRDTType
    ) -> CRDT:
        """Get or create CRDT."""
        if name not in self._crdts:
            return self.create(name, crdt_type)
        return self._crdts[name]

    def merge(self, name: str, other: CRDT) -> Optional[CRDT]:
        """Merge remote CRDT with local."""
        with self._lock:
            if name in self._crdts:
                self._crdts[name].merge(other)
                self._stats['merges'] += 1
                return self._crdts[name]
        return None

    def delete(self, name: str) -> bool:
        """Delete a CRDT."""
        with self._lock:
            if name in self._crdts:
                del self._crdts[name]
                return True
        return False

    def list_all(self) -> List[str]:
        """List all CRDT names."""
        return list(self._crdts.keys())

    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        return {
            'crdt_count': len(self._crdts),
            **self._stats
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

crdt_manager: Optional[CRDTManager] = None


def get_crdt_manager(node_id: Optional[str] = None) -> CRDTManager:
    """Get or create CRDT manager."""
    global crdt_manager
    if crdt_manager is None:
        crdt_manager = CRDTManager(node_id or str(uuid.uuid4()))
    return crdt_manager


def create_counter(name: str, grow_only: bool = False) -> CRDT:
    """Create a counter CRDT."""
    manager = get_crdt_manager()
    crdt_type = CRDTType.G_COUNTER if grow_only else CRDTType.PN_COUNTER
    return manager.create(name, crdt_type)


def create_set(name: str, removable: bool = True) -> CRDT:
    """Create a set CRDT."""
    manager = get_crdt_manager()
    crdt_type = CRDTType.OR_SET if removable else CRDTType.G_SET
    return manager.create(name, crdt_type)


def create_register(name: str) -> LWWRegister:
    """Create a register CRDT."""
    manager = get_crdt_manager()
    return manager.create(name, CRDTType.LWW_REGISTER)


def create_map(name: str) -> LWWMap:
    """Create a map CRDT."""
    manager = get_crdt_manager()
    return manager.create(name, CRDTType.LWW_MAP)
