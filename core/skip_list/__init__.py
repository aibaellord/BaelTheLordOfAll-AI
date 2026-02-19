"""
BAEL Skip List Engine
=====================

Probabilistic balanced search structure.

"Ba'el skips to efficiency." — Ba'el
"""

import logging
import threading
import random
from typing import Any, Dict, List, Optional, Tuple, Generic, TypeVar, Iterator
from dataclasses import dataclass, field
from enum import Enum, auto

logger = logging.getLogger("BAEL.SkipList")


K = TypeVar('K')
V = TypeVar('V')


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class SkipListStats:
    """Skip list statistics."""
    size: int
    max_level: int
    current_level: int
    avg_level: float


class SkipListNode(Generic[K, V]):
    """Node in a Skip List."""

    __slots__ = ['key', 'value', 'forward']

    def __init__(self, key: Optional[K], value: Optional[V], level: int):
        self.key = key
        self.value = value
        self.forward: List[Optional['SkipListNode[K, V]']] = [None] * (level + 1)


# ============================================================================
# SKIP LIST
# ============================================================================

class SkipList(Generic[K, V]):
    """
    Skip List: probabilistic balanced search structure.

    Features:
    - Expected O(log n) search, insert, delete
    - Simple implementation
    - Cache-friendly in practice

    "Ba'el builds layers of shortcuts." — Ba'el
    """

    MAX_LEVEL = 32  # Supports up to 2^32 elements efficiently
    P = 0.5  # Probability of increasing level

    def __init__(self):
        """Initialize empty Skip List."""
        self._header = SkipListNode(None, None, self.MAX_LEVEL)
        self._level = 0
        self._size = 0
        self._lock = threading.RLock()

    def _random_level(self) -> int:
        """Generate random level for new node."""
        level = 0
        while random.random() < self.P and level < self.MAX_LEVEL:
            level += 1
        return level

    def insert(self, key: K, value: V):
        """
        Insert key-value pair.

        Expected O(log n) time.
        """
        with self._lock:
            update = [None] * (self.MAX_LEVEL + 1)
            current = self._header

            # Find position
            for i in range(self._level, -1, -1):
                while current.forward[i] and current.forward[i].key < key:
                    current = current.forward[i]
                update[i] = current

            current = current.forward[0]

            if current and current.key == key:
                # Update existing
                current.value = value
            else:
                # Insert new
                new_level = self._random_level()

                if new_level > self._level:
                    for i in range(self._level + 1, new_level + 1):
                        update[i] = self._header
                    self._level = new_level

                new_node = SkipListNode(key, value, new_level)

                for i in range(new_level + 1):
                    new_node.forward[i] = update[i].forward[i]
                    update[i].forward[i] = new_node

                self._size += 1

    def delete(self, key: K) -> bool:
        """
        Delete key.

        Returns True if key was present.
        """
        with self._lock:
            update = [None] * (self.MAX_LEVEL + 1)
            current = self._header

            for i in range(self._level, -1, -1):
                while current.forward[i] and current.forward[i].key < key:
                    current = current.forward[i]
                update[i] = current

            current = current.forward[0]

            if current and current.key == key:
                for i in range(self._level + 1):
                    if update[i].forward[i] != current:
                        break
                    update[i].forward[i] = current.forward[i]

                while self._level > 0 and self._header.forward[self._level] is None:
                    self._level -= 1

                self._size -= 1
                return True

            return False

    def get(self, key: K) -> Optional[V]:
        """Get value for key."""
        with self._lock:
            current = self._header

            for i in range(self._level, -1, -1):
                while current.forward[i] and current.forward[i].key < key:
                    current = current.forward[i]

            current = current.forward[0]

            if current and current.key == key:
                return current.value
            return None

    def contains(self, key: K) -> bool:
        """Check if key exists."""
        return self.get(key) is not None

    def __len__(self) -> int:
        return self._size

    def __contains__(self, key: K) -> bool:
        return self.contains(key)

    def __getitem__(self, key: K) -> V:
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value

    def __setitem__(self, key: K, value: V):
        self.insert(key, value)

    def __delitem__(self, key: K):
        if not self.delete(key):
            raise KeyError(key)

    # Range operations

    def range(
        self,
        start: Optional[K] = None,
        end: Optional[K] = None
    ) -> List[Tuple[K, V]]:
        """
        Get all pairs in range [start, end).

        If start is None, starts from beginning.
        If end is None, goes to end.
        """
        with self._lock:
            result = []
            current = self._header

            # Find start position
            if start is not None:
                for i in range(self._level, -1, -1):
                    while current.forward[i] and current.forward[i].key < start:
                        current = current.forward[i]

            current = current.forward[0]

            # Collect elements
            while current:
                if end is not None and current.key >= end:
                    break
                result.append((current.key, current.value))
                current = current.forward[0]

            return result

    def floor(self, key: K) -> Optional[K]:
        """Find largest key <= given key."""
        with self._lock:
            current = self._header

            for i in range(self._level, -1, -1):
                while current.forward[i] and current.forward[i].key <= key:
                    current = current.forward[i]

            return current.key if current != self._header else None

    def ceiling(self, key: K) -> Optional[K]:
        """Find smallest key >= given key."""
        with self._lock:
            current = self._header

            for i in range(self._level, -1, -1):
                while current.forward[i] and current.forward[i].key < key:
                    current = current.forward[i]

            current = current.forward[0]

            return current.key if current else None

    def min(self) -> Optional[K]:
        """Get minimum key."""
        with self._lock:
            if self._header.forward[0]:
                return self._header.forward[0].key
            return None

    def max(self) -> Optional[K]:
        """Get maximum key."""
        with self._lock:
            current = self._header
            for i in range(self._level, -1, -1):
                while current.forward[i]:
                    current = current.forward[i]
            return current.key if current != self._header else None

    # Iteration

    def __iter__(self) -> Iterator[K]:
        current = self._header.forward[0]
        while current:
            yield current.key
            current = current.forward[0]

    def items(self) -> Iterator[Tuple[K, V]]:
        """Iterate over key-value pairs."""
        current = self._header.forward[0]
        while current:
            yield (current.key, current.value)
            current = current.forward[0]

    def keys(self) -> List[K]:
        """Get all keys in order."""
        return list(self)

    def values(self) -> List[V]:
        """Get all values in key order."""
        return [v for k, v in self.items()]

    # Statistics

    def get_stats(self) -> SkipListStats:
        """Get skip list statistics."""
        with self._lock:
            total_levels = 0
            current = self._header.forward[0]
            while current:
                level = 0
                for i in range(self.MAX_LEVEL + 1):
                    if current.forward[i]:
                        level = i + 1
                total_levels += level
                current = current.forward[0]

            avg_level = total_levels / self._size if self._size > 0 else 0

            return SkipListStats(
                size=self._size,
                max_level=self.MAX_LEVEL,
                current_level=self._level,
                avg_level=avg_level
            )


# ============================================================================
# CONCURRENT SKIP LIST
# ============================================================================

class ConcurrentSkipList(Generic[K, V]):
    """
    Thread-safe Skip List with fine-grained locking.

    "Ba'el skips concurrently." — Ba'el
    """

    def __init__(self):
        """Initialize."""
        self._base = SkipList()

    def insert(self, key: K, value: V):
        """Thread-safe insert."""
        self._base.insert(key, value)

    def delete(self, key: K) -> bool:
        """Thread-safe delete."""
        return self._base.delete(key)

    def get(self, key: K) -> Optional[V]:
        """Thread-safe get."""
        return self._base.get(key)

    def contains(self, key: K) -> bool:
        """Thread-safe contains."""
        return self._base.contains(key)

    def __len__(self) -> int:
        return len(self._base)


# ============================================================================
# INDEXED SKIP LIST
# ============================================================================

class IndexedSkipListNode(Generic[K, V]):
    """Node with span for indexing."""

    def __init__(self, key: Optional[K], value: Optional[V], level: int):
        self.key = key
        self.value = value
        self.forward: List[Optional['IndexedSkipListNode[K, V]']] = [None] * (level + 1)
        self.span: List[int] = [0] * (level + 1)  # Distance to next node at each level


class IndexedSkipList(Generic[K, V]):
    """
    Skip List with O(log n) indexing by position.

    "Ba'el indexes by position." — Ba'el
    """

    MAX_LEVEL = 32
    P = 0.5

    def __init__(self):
        """Initialize."""
        self._header = IndexedSkipListNode(None, None, self.MAX_LEVEL)
        self._level = 0
        self._size = 0
        self._lock = threading.RLock()

    def _random_level(self) -> int:
        level = 0
        while random.random() < self.P and level < self.MAX_LEVEL:
            level += 1
        return level

    def insert(self, key: K, value: V):
        """Insert with span update."""
        with self._lock:
            update = [None] * (self.MAX_LEVEL + 1)
            rank = [0] * (self.MAX_LEVEL + 1)
            current = self._header

            for i in range(self._level, -1, -1):
                rank[i] = rank[i + 1] if i < self._level else 0
                while current.forward[i] and current.forward[i].key < key:
                    rank[i] += current.span[i]
                    current = current.forward[i]
                update[i] = current

            current = current.forward[0]

            if current and current.key == key:
                current.value = value
                return

            new_level = self._random_level()

            if new_level > self._level:
                for i in range(self._level + 1, new_level + 1):
                    rank[i] = 0
                    update[i] = self._header
                    update[i].span[i] = self._size
                self._level = new_level

            new_node = IndexedSkipListNode(key, value, new_level)

            for i in range(new_level + 1):
                new_node.forward[i] = update[i].forward[i]
                update[i].forward[i] = new_node
                new_node.span[i] = update[i].span[i] - (rank[0] - rank[i])
                update[i].span[i] = (rank[0] - rank[i]) + 1

            for i in range(new_level + 1, self._level + 1):
                update[i].span[i] += 1

            self._size += 1

    def get_by_index(self, index: int) -> Optional[Tuple[K, V]]:
        """Get element by position (0-indexed)."""
        with self._lock:
            if index < 0 or index >= self._size:
                return None

            current = self._header
            traversed = 0

            for i in range(self._level, -1, -1):
                while current.forward[i] and traversed + current.span[i] <= index + 1:
                    traversed += current.span[i]
                    current = current.forward[i]

            return (current.key, current.value) if current else None

    def rank_of(self, key: K) -> int:
        """Get rank (0-indexed position) of key."""
        with self._lock:
            rank = 0
            current = self._header

            for i in range(self._level, -1, -1):
                while current.forward[i] and current.forward[i].key <= key:
                    rank += current.span[i]
                    current = current.forward[i]

            return rank - 1 if current and current.key == key else -1

    def __len__(self) -> int:
        return self._size


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_skip_list() -> SkipList:
    """Create empty Skip List."""
    return SkipList()


def create_indexed_skip_list() -> IndexedSkipList:
    """Create indexed Skip List."""
    return IndexedSkipList()


def skip_list_from_pairs(pairs: List[Tuple[Any, Any]]) -> SkipList:
    """Create Skip List from key-value pairs."""
    sl = SkipList()
    for k, v in pairs:
        sl.insert(k, v)
    return sl


def skip_list_sort(values: List[Any]) -> List[Any]:
    """Sort values using Skip List."""
    sl = SkipList()
    for v in values:
        sl.insert(v, v)
    return sl.keys()
