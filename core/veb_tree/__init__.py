"""
BAEL Van Emde Boas Tree Engine
===============================

O(log log U) integer priority queue.

"Ba'el divides universes recursively unto infinity." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, Iterator, List, Optional, Set
from dataclasses import dataclass, field
import math

logger = logging.getLogger("BAEL.VanEmdeBoas")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class VEBStats:
    """Van Emde Boas statistics."""
    universe_size: int = 0
    element_count: int = 0
    insert_count: int = 0
    delete_count: int = 0
    query_count: int = 0


# ============================================================================
# VAN EMDE BOAS TREE ENGINE
# ============================================================================

class VanEmdeBoas:
    """
    Van Emde Boas tree implementation.

    Features:
    - O(log log U) insert, delete, predecessor, successor
    - O(1) minimum, maximum
    - Perfect for integer keys in known universe

    "Ba'el indexes all integers in recursive perfection." — Ba'el
    """

    def __init__(self, universe: int):
        """
        Initialize Van Emde Boas tree.

        Args:
            universe: Size of universe (max value + 1)
        """
        # Round up to power of 2
        self._u = 1
        while self._u < universe:
            self._u *= 2

        self._min: Optional[int] = None
        self._max: Optional[int] = None

        if self._u > 2:
            self._sqrt_u = int(math.sqrt(self._u))

            # Summary structure
            self._summary: Optional['VanEmdeBoas'] = None

            # Clusters
            self._cluster: List[Optional['VanEmdeBoas']] = [None] * self._sqrt_u

        self._stats = VEBStats(universe_size=self._u)
        self._lock = threading.RLock()

        logger.info(f"VEB tree initialized (universe={self._u})")

    def _high(self, x: int) -> int:
        """Get high bits (cluster index)."""
        return x // self._sqrt_u

    def _low(self, x: int) -> int:
        """Get low bits (position in cluster)."""
        return x % self._sqrt_u

    def _index(self, high: int, low: int) -> int:
        """Reconstruct value from high and low bits."""
        return high * self._sqrt_u + low

    # ========================================================================
    # BASIC OPERATIONS
    # ========================================================================

    def insert(self, x: int) -> None:
        """
        Insert element.

        Args:
            x: Element to insert (0 <= x < universe)
        """
        if x < 0 or x >= self._u:
            raise ValueError(f"Value {x} out of universe [0, {self._u})")

        with self._lock:
            self._stats.insert_count += 1
            self._insert(x)

    def _insert(self, x: int) -> None:
        """Internal insert."""
        if self._min is None:
            # Empty tree
            self._min = x
            self._max = x
            self._stats.element_count += 1
            return

        if x == self._min or x == self._max:
            return  # Already exists

        if x < self._min:
            x, self._min = self._min, x

        if self._u > 2:
            high = self._high(x)
            low = self._low(x)

            if self._cluster[high] is None:
                self._cluster[high] = VanEmdeBoas(self._sqrt_u)

            if self._cluster[high]._min is None:
                # Empty cluster
                if self._summary is None:
                    self._summary = VanEmdeBoas(self._sqrt_u)

                self._summary._insert(high)
                self._cluster[high]._min = low
                self._cluster[high]._max = low
                self._stats.element_count += 1
            else:
                self._cluster[high]._insert(low)

        if x > self._max:
            self._max = x

    def delete(self, x: int) -> bool:
        """
        Delete element.

        Args:
            x: Element to delete

        Returns:
            True if deleted
        """
        if x < 0 or x >= self._u:
            return False

        with self._lock:
            self._stats.delete_count += 1
            return self._delete(x)

    def _delete(self, x: int) -> bool:
        """Internal delete."""
        if self._min is None:
            return False

        if self._min == self._max:
            if x == self._min:
                self._min = None
                self._max = None
                self._stats.element_count -= 1
                return True
            return False

        if self._u <= 2:
            if x == 0:
                self._min = 1
            else:
                self._min = 0
            self._max = self._min
            self._stats.element_count -= 1
            return True

        if x == self._min:
            first_cluster = self._summary._min if self._summary else None

            if first_cluster is None:
                return False

            x = self._index(first_cluster, self._cluster[first_cluster]._min)
            self._min = x

        high = self._high(x)
        low = self._low(x)

        if self._cluster[high] is None:
            return False

        deleted = self._cluster[high]._delete(low)

        if deleted:
            if self._cluster[high]._min is None:
                if self._summary:
                    self._summary._delete(high)

                if x == self._max:
                    summary_max = self._summary._max if self._summary and self._summary._min is not None else None

                    if summary_max is None:
                        self._max = self._min
                    else:
                        self._max = self._index(
                            summary_max,
                            self._cluster[summary_max]._max
                        )
            elif x == self._max:
                self._max = self._index(high, self._cluster[high]._max)

            self._stats.element_count -= 1

        return deleted

    def contains(self, x: int) -> bool:
        """
        Check if element exists.

        Args:
            x: Element to check

        Returns:
            True if exists
        """
        if x < 0 or x >= self._u:
            return False

        with self._lock:
            self._stats.query_count += 1
            return self._member(x)

    def _member(self, x: int) -> bool:
        """Check membership."""
        if self._min is None:
            return False

        if x == self._min or x == self._max:
            return True

        if self._u <= 2:
            return False

        high = self._high(x)
        low = self._low(x)

        if self._cluster[high] is None:
            return False

        return self._cluster[high]._member(low)

    def __contains__(self, x: int) -> bool:
        return self.contains(x)

    # ========================================================================
    # MIN / MAX
    # ========================================================================

    @property
    def minimum(self) -> Optional[int]:
        """Get minimum element."""
        return self._min

    @property
    def maximum(self) -> Optional[int]:
        """Get maximum element."""
        return self._max

    # ========================================================================
    # PREDECESSOR / SUCCESSOR
    # ========================================================================

    def successor(self, x: int) -> Optional[int]:
        """
        Find successor (next larger element).

        Args:
            x: Query value

        Returns:
            Successor or None
        """
        with self._lock:
            self._stats.query_count += 1
            return self._successor(x)

    def _successor(self, x: int) -> Optional[int]:
        """Find successor."""
        if self._u <= 2:
            if x == 0 and self._max == 1:
                return 1
            return None

        if self._min is not None and x < self._min:
            return self._min

        high = self._high(x)
        low = self._low(x)

        # Check current cluster
        if (self._cluster[high] is not None and
            self._cluster[high]._max is not None and
            low < self._cluster[high]._max):

            offset = self._cluster[high]._successor(low)
            return self._index(high, offset)

        # Find next non-empty cluster
        if self._summary is not None:
            succ_cluster = self._summary._successor(high)

            if succ_cluster is not None:
                offset = self._cluster[succ_cluster]._min
                return self._index(succ_cluster, offset)

        return None

    def predecessor(self, x: int) -> Optional[int]:
        """
        Find predecessor (previous smaller element).

        Args:
            x: Query value

        Returns:
            Predecessor or None
        """
        with self._lock:
            self._stats.query_count += 1
            return self._predecessor(x)

    def _predecessor(self, x: int) -> Optional[int]:
        """Find predecessor."""
        if self._u <= 2:
            if x == 1 and self._min == 0:
                return 0
            return None

        if self._max is not None and x > self._max:
            return self._max

        high = self._high(x)
        low = self._low(x)

        # Check current cluster
        if (self._cluster[high] is not None and
            self._cluster[high]._min is not None and
            low > self._cluster[high]._min):

            offset = self._cluster[high]._predecessor(low)
            return self._index(high, offset)

        # Find previous non-empty cluster
        if self._summary is not None:
            pred_cluster = self._summary._predecessor(high)

            if pred_cluster is not None:
                offset = self._cluster[pred_cluster]._max
                return self._index(pred_cluster, offset)

        # Check if min is predecessor
        if self._min is not None and x > self._min:
            return self._min

        return None

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def __len__(self) -> int:
        """Get number of elements."""
        return self._stats.element_count

    @property
    def universe_size(self) -> int:
        """Get universe size."""
        return self._u

    def is_empty(self) -> bool:
        """Check if empty."""
        return self._min is None

    def all_elements(self) -> List[int]:
        """Get all elements in sorted order."""
        result = []

        x = self._min
        while x is not None:
            result.append(x)
            x = self._successor(x)

        return result

    def __iter__(self) -> Iterator[int]:
        """Iterate elements in sorted order."""
        x = self._min
        while x is not None:
            yield x
            x = self._successor(x)

    def clear(self) -> None:
        """Clear all elements."""
        with self._lock:
            self._min = None
            self._max = None
            self._summary = None

            if self._u > 2:
                self._cluster = [None] * self._sqrt_u

            self._stats.element_count = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'universe_size': self._stats.universe_size,
            'element_count': self._stats.element_count,
            'insert_count': self._stats.insert_count,
            'delete_count': self._stats.delete_count,
            'query_count': self._stats.query_count
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_veb_tree(universe: int) -> VanEmdeBoas:
    """Create a Van Emde Boas tree."""
    return VanEmdeBoas(universe)


def from_set(elements: Set[int]) -> VanEmdeBoas:
    """
    Create VEB tree from set of integers.

    Args:
        elements: Set of integers

    Returns:
        VanEmdeBoas tree
    """
    if not elements:
        return VanEmdeBoas(2)

    max_elem = max(elements)
    veb = VanEmdeBoas(max_elem + 1)

    for x in elements:
        veb.insert(x)

    return veb


def from_list(elements: List[int]) -> VanEmdeBoas:
    """
    Create VEB tree from list of integers.

    Args:
        elements: List of integers

    Returns:
        VanEmdeBoas tree
    """
    return from_set(set(elements))
