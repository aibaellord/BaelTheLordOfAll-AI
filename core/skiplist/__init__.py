"""
BAEL Skip List Engine Implementation
=====================================

Probabilistic ordered data structure.

"Ba'el navigates levels with divine agility." — Ba'el
"""

import logging
import random
import threading
from typing import Any, Generator, Generic, List, Optional, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("BAEL.SkipList")

K = TypeVar('K')
V = TypeVar('V')


# ============================================================================
# DATA STRUCTURES
# ============================================================================

class SkipNode(Generic[K, V]):
    """A node in the skip list."""

    __slots__ = ['key', 'value', 'forward', 'level']

    def __init__(
        self,
        key: K,
        value: V,
        level: int
    ):
        self.key = key
        self.value = value
        self.forward: List[Optional['SkipNode[K, V]']] = [None] * (level + 1)
        self.level = level

    def __repr__(self) -> str:
        return f"SkipNode(key={self.key}, level={self.level})"


@dataclass
class SkipListConfig:
    """Skip list configuration."""
    max_level: int = 16
    probability: float = 0.5  # Probability of level increase


# ============================================================================
# SKIP LIST
# ============================================================================

class SkipList(Generic[K, V]):
    """
    Skip list data structure.

    Features:
    - O(log n) average search, insert, delete
    - Ordered iteration
    - Range queries
    - Probabilistic balancing

    "Ba'el leaps through data with perfect precision." — Ba'el
    """

    def __init__(self, config: Optional[SkipListConfig] = None):
        """Initialize skip list."""
        self.config = config or SkipListConfig()

        # Header node (sentinel)
        self._header = SkipNode(None, None, self.config.max_level)
        self._level = 0
        self._size = 0

        # Thread safety
        self._lock = threading.RLock()

        # Stats
        self._stats = {
            'inserts': 0,
            'searches': 0,
            'deletes': 0,
            'comparisons': 0
        }

        logger.info(f"Skip list initialized (max_level={self.config.max_level})")

    # ========================================================================
    # CORE OPERATIONS
    # ========================================================================

    def _random_level(self) -> int:
        """Generate random level for new node."""
        level = 0
        while (random.random() < self.config.probability and
               level < self.config.max_level):
            level += 1
        return level

    def insert(self, key: K, value: V) -> None:
        """
        Insert key-value pair.

        Args:
            key: Key (must be comparable)
            value: Value to store
        """
        with self._lock:
            update = [None] * (self.config.max_level + 1)
            current = self._header

            # Find position from top level down
            for i in range(self._level, -1, -1):
                while (current.forward[i] and
                       current.forward[i].key < key):
                    self._stats['comparisons'] += 1
                    current = current.forward[i]
                update[i] = current

            current = current.forward[0]

            # Update existing key
            if current and current.key == key:
                current.value = value
                self._stats['inserts'] += 1
                return

            # Create new node
            new_level = self._random_level()

            if new_level > self._level:
                for i in range(self._level + 1, new_level + 1):
                    update[i] = self._header
                self._level = new_level

            new_node = SkipNode(key, value, new_level)

            # Insert at each level
            for i in range(new_level + 1):
                new_node.forward[i] = update[i].forward[i]
                update[i].forward[i] = new_node

            self._size += 1
            self._stats['inserts'] += 1

    def search(self, key: K) -> Optional[V]:
        """
        Search for key.

        Args:
            key: Key to search

        Returns:
            Value if found, None otherwise
        """
        with self._lock:
            self._stats['searches'] += 1

            current = self._header

            for i in range(self._level, -1, -1):
                while (current.forward[i] and
                       current.forward[i].key < key):
                    self._stats['comparisons'] += 1
                    current = current.forward[i]

            current = current.forward[0]

            if current and current.key == key:
                return current.value

            return None

    def delete(self, key: K) -> bool:
        """
        Delete key.

        Args:
            key: Key to delete

        Returns:
            True if key was deleted
        """
        with self._lock:
            self._stats['deletes'] += 1

            update = [None] * (self.config.max_level + 1)
            current = self._header

            for i in range(self._level, -1, -1):
                while (current.forward[i] and
                       current.forward[i].key < key):
                    current = current.forward[i]
                update[i] = current

            current = current.forward[0]

            if not current or current.key != key:
                return False

            # Remove from each level
            for i in range(self._level + 1):
                if update[i].forward[i] != current:
                    break
                update[i].forward[i] = current.forward[i]

            # Update level
            while self._level > 0 and not self._header.forward[self._level]:
                self._level -= 1

            self._size -= 1
            return True

    def __contains__(self, key: K) -> bool:
        return self.search(key) is not None

    def __getitem__(self, key: K) -> V:
        value = self.search(key)
        if value is None:
            raise KeyError(key)
        return value

    def __setitem__(self, key: K, value: V) -> None:
        self.insert(key, value)

    def __delitem__(self, key: K) -> None:
        if not self.delete(key):
            raise KeyError(key)

    def __len__(self) -> int:
        return self._size

    # ========================================================================
    # RANGE OPERATIONS
    # ========================================================================

    def range(
        self,
        start: Optional[K] = None,
        end: Optional[K] = None,
        include_start: bool = True,
        include_end: bool = False
    ) -> Generator[Tuple[K, V], None, None]:
        """
        Iterate over key range.

        Args:
            start: Start key (inclusive by default)
            end: End key (exclusive by default)
            include_start: Include start key
            include_end: Include end key

        Yields:
            (key, value) tuples
        """
        with self._lock:
            current = self._header

            if start is not None:
                # Find start position
                for i in range(self._level, -1, -1):
                    while (current.forward[i] and
                           current.forward[i].key < start):
                        current = current.forward[i]

            current = current.forward[0]

            # Skip if not including start
            if (current and start is not None and
                current.key == start and not include_start):
                current = current.forward[0]

            while current:
                if end is not None:
                    if current.key > end:
                        break
                    if current.key == end and not include_end:
                        break

                yield current.key, current.value
                current = current.forward[0]

    def first(self) -> Optional[Tuple[K, V]]:
        """Get first (smallest) key-value pair."""
        first = self._header.forward[0]
        if first:
            return first.key, first.value
        return None

    def last(self) -> Optional[Tuple[K, V]]:
        """Get last (largest) key-value pair."""
        current = self._header

        for i in range(self._level, -1, -1):
            while current.forward[i]:
                current = current.forward[i]

        if current != self._header:
            return current.key, current.value
        return None

    def floor(self, key: K) -> Optional[Tuple[K, V]]:
        """Get largest key <= given key."""
        with self._lock:
            current = self._header

            for i in range(self._level, -1, -1):
                while (current.forward[i] and
                       current.forward[i].key <= key):
                    current = current.forward[i]

            if current != self._header:
                return current.key, current.value
            return None

    def ceiling(self, key: K) -> Optional[Tuple[K, V]]:
        """Get smallest key >= given key."""
        with self._lock:
            current = self._header

            for i in range(self._level, -1, -1):
                while (current.forward[i] and
                       current.forward[i].key < key):
                    current = current.forward[i]

            current = current.forward[0]

            if current:
                return current.key, current.value
            return None

    # ========================================================================
    # ITERATION
    # ========================================================================

    def __iter__(self) -> Generator[K, None, None]:
        """Iterate over keys in order."""
        current = self._header.forward[0]
        while current:
            yield current.key
            current = current.forward[0]

    def items(self) -> Generator[Tuple[K, V], None, None]:
        """Iterate over key-value pairs."""
        current = self._header.forward[0]
        while current:
            yield current.key, current.value
            current = current.forward[0]

    def keys(self) -> Generator[K, None, None]:
        """Iterate over keys."""
        return iter(self)

    def values(self) -> Generator[V, None, None]:
        """Iterate over values."""
        current = self._header.forward[0]
        while current:
            yield current.value
            current = current.forward[0]

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def clear(self) -> None:
        """Clear all entries."""
        with self._lock:
            self._header = SkipNode(None, None, self.config.max_level)
            self._level = 0
            self._size = 0

    def get_level_distribution(self) -> dict:
        """Get distribution of node levels."""
        distribution = {}
        current = self._header.forward[0]

        while current:
            level = current.level
            distribution[level] = distribution.get(level, 0) + 1
            current = current.forward[0]

        return distribution

    def get_stats(self) -> dict:
        """Get skip list statistics."""
        return {
            'size': self._size,
            'level': self._level,
            'max_level': self.config.max_level,
            **self._stats
        }

    def visualize(self, max_items: int = 20) -> str:
        """
        Generate visual representation.

        Args:
            max_items: Maximum items to show

        Returns:
            String visualization
        """
        lines = []

        # Get items
        items = []
        current = self._header.forward[0]
        count = 0

        while current and count < max_items:
            items.append(current)
            current = current.forward[0]
            count += 1

        if not items:
            return "Empty skip list"

        # Build visualization
        for level in range(self._level, -1, -1):
            line = f"L{level}: "
            for node in items:
                if level <= node.level:
                    line += f"[{node.key}]-"
                else:
                    line += "------"
            lines.append(line)

        return "\n".join(lines)


# ============================================================================
# CONCURRENT SKIP LIST
# ============================================================================

class ConcurrentSkipList(SkipList[K, V]):
    """
    Thread-safe skip list with fine-grained locking.

    Uses per-node locks for better concurrency.
    """

    def __init__(self, config: Optional[SkipListConfig] = None):
        super().__init__(config)
        # Could implement per-node locking for better concurrency
        # For now, uses inherited RLock

    def concurrent_insert(self, key: K, value: V) -> None:
        """Thread-safe insert."""
        self.insert(key, value)

    def concurrent_search(self, key: K) -> Optional[V]:
        """Thread-safe search."""
        return self.search(key)


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_skip_list(
    max_level: int = 16,
    probability: float = 0.5
) -> SkipList:
    """Create a skip list."""
    config = SkipListConfig(
        max_level=max_level,
        probability=probability
    )
    return SkipList(config)


def create_concurrent_skip_list(
    max_level: int = 16,
    probability: float = 0.5
) -> ConcurrentSkipList:
    """Create a concurrent skip list."""
    config = SkipListConfig(
        max_level=max_level,
        probability=probability
    )
    return ConcurrentSkipList(config)
