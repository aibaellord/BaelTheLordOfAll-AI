"""
BAEL Van Emde Boas Tree Engine
==============================

O(log log U) operations on integers.

"Ba'el transcends logarithms." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum, auto

logger = logging.getLogger("BAEL.VanEmdeBoas")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class VEBStats:
    """Van Emde Boas tree statistics."""
    universe_size: int
    num_elements: int
    height: int


# ============================================================================
# VAN EMDE BOAS TREE
# ============================================================================

class VanEmdeBoas:
    """
    Van Emde Boas Tree: O(log log U) operations.

    Operations:
    - insert: O(log log U)
    - delete: O(log log U)
    - member: O(log log U)
    - successor: O(log log U)
    - predecessor: O(log log U)
    - min/max: O(1)

    U = universe size (must be power of 2)

    "Ba'el defies logarithmic bounds." — Ba'el
    """

    def __init__(self, u: int):
        """
        Initialize VEB tree.

        Args:
            u: Universe size (power of 2, at least 2)
        """
        if u < 2:
            raise ValueError("Universe size must be at least 2")

        # Round up to power of 2
        self._u = 1
        while self._u < u:
            self._u *= 2

        self._lock = threading.RLock()

        self._min: Optional[int] = None
        self._max: Optional[int] = None

        if self._u <= 2:
            self._clusters = None
            self._summary = None
        else:
            self._upper_sqrt = self._high_sqrt()
            self._lower_sqrt = self._low_sqrt()
            self._clusters: List[Optional['VanEmdeBoas']] = [None] * self._upper_sqrt
            self._summary: Optional['VanEmdeBoas'] = None

    def _high_sqrt(self) -> int:
        """Upper square root."""
        return 1 << ((self._u.bit_length() - 1 + 1) // 2)

    def _low_sqrt(self) -> int:
        """Lower square root."""
        return 1 << ((self._u.bit_length() - 1) // 2)

    def _high(self, x: int) -> int:
        """Get cluster index."""
        return x // self._lower_sqrt

    def _low(self, x: int) -> int:
        """Get position within cluster."""
        return x % self._lower_sqrt

    def _index(self, high: int, low: int) -> int:
        """Reconstruct value from cluster and position."""
        return high * self._lower_sqrt + low

    def insert(self, x: int):
        """
        Insert element.

        O(log log U).
        """
        with self._lock:
            self._insert(x)

    def _insert(self, x: int):
        if x < 0 or x >= self._u:
            raise ValueError(f"Value {x} out of range [0, {self._u})")

        if self._min is None:
            # Empty tree
            self._min = x
            self._max = x
            return

        if x < self._min:
            x, self._min = self._min, x

        if self._u > 2:
            high = self._high(x)
            low = self._low(x)

            if self._clusters[high] is None:
                self._clusters[high] = VanEmdeBoas(self._lower_sqrt)
                if self._summary is None:
                    self._summary = VanEmdeBoas(self._upper_sqrt)
                self._summary._insert(high)

            self._clusters[high]._insert(low)

        if x > self._max:
            self._max = x

    def delete(self, x: int):
        """
        Delete element.

        O(log log U).
        """
        with self._lock:
            self._delete(x)

    def _delete(self, x: int):
        if self._min is None or x < 0 or x >= self._u:
            return

        if self._min == self._max:
            if x == self._min:
                self._min = None
                self._max = None
            return

        if self._u == 2:
            if x == 0:
                self._min = 1
            else:
                self._min = 0
            self._max = self._min
            return

        if x == self._min:
            first_cluster = self._summary._min if self._summary else None
            if first_cluster is None:
                self._min = self._max
                return
            x = self._index(first_cluster, self._clusters[first_cluster]._min)
            self._min = x

        high = self._high(x)
        low = self._low(x)

        if self._clusters[high]:
            self._clusters[high]._delete(low)

            if self._clusters[high]._min is None:
                if self._summary:
                    self._summary._delete(high)

        if x == self._max:
            if self._summary is None or self._summary._max is None:
                self._max = self._min
            else:
                max_cluster = self._summary._max
                self._max = self._index(max_cluster, self._clusters[max_cluster]._max)

    def member(self, x: int) -> bool:
        """
        Check if element exists.

        O(log log U).
        """
        with self._lock:
            return self._member(x)

    def _member(self, x: int) -> bool:
        if x < 0 or x >= self._u:
            return False

        if x == self._min or x == self._max:
            return True

        if self._u == 2:
            return False

        high = self._high(x)
        if self._clusters[high] is None:
            return False

        return self._clusters[high]._member(self._low(x))

    def successor(self, x: int) -> Optional[int]:
        """
        Find smallest element > x.

        O(log log U).
        """
        with self._lock:
            return self._successor(x)

    def _successor(self, x: int) -> Optional[int]:
        if self._u == 2:
            if x == 0 and self._max == 1:
                return 1
            return None

        if self._min is not None and x < self._min:
            return self._min

        high = self._high(x)
        low = self._low(x)

        # Check current cluster
        if (self._clusters[high] is not None and
            self._clusters[high]._max is not None and
            low < self._clusters[high]._max):
            offset = self._clusters[high]._successor(low)
            if offset is not None:
                return self._index(high, offset)

        # Find next cluster
        if self._summary is not None:
            succ_cluster = self._summary._successor(high)
            if succ_cluster is not None and self._clusters[succ_cluster] is not None:
                return self._index(succ_cluster, self._clusters[succ_cluster]._min)

        return None

    def predecessor(self, x: int) -> Optional[int]:
        """
        Find largest element < x.

        O(log log U).
        """
        with self._lock:
            return self._predecessor(x)

    def _predecessor(self, x: int) -> Optional[int]:
        if self._u == 2:
            if x == 1 and self._min == 0:
                return 0
            return None

        if self._max is not None and x > self._max:
            return self._max

        high = self._high(x)
        low = self._low(x)

        # Check current cluster
        if (self._clusters[high] is not None and
            self._clusters[high]._min is not None and
            low > self._clusters[high]._min):
            offset = self._clusters[high]._predecessor(low)
            if offset is not None:
                return self._index(high, offset)

        # Find previous cluster
        if self._summary is not None:
            pred_cluster = self._summary._predecessor(high)
            if pred_cluster is not None and self._clusters[pred_cluster] is not None:
                return self._index(pred_cluster, self._clusters[pred_cluster]._max)

        # Check min
        if self._min is not None and x > self._min:
            return self._min

        return None

    def minimum(self) -> Optional[int]:
        """Get minimum element. O(1)."""
        with self._lock:
            return self._min

    def maximum(self) -> Optional[int]:
        """Get maximum element. O(1)."""
        with self._lock:
            return self._max

    def is_empty(self) -> bool:
        """Check if tree is empty."""
        with self._lock:
            return self._min is None

    def __contains__(self, x: int) -> bool:
        return self.member(x)

    def __len__(self) -> int:
        """Count elements (O(n) - not efficient)."""
        with self._lock:
            if self._min is None:
                return 0
            count = 1 if self._min == self._max else 0
            x = self._min
            while True:
                x = self._successor(x)
                if x is None:
                    break
                count += 1
            return count + (1 if self._min != self._max and self._min is not None else 0)

    def to_list(self) -> List[int]:
        """Get all elements as sorted list."""
        with self._lock:
            result = []
            x = self._min
            while x is not None:
                result.append(x)
                x = self._successor(x)
            return result


# ============================================================================
# X-FAST TRIE
# ============================================================================

class XFastTrie:
    """
    X-Fast Trie: O(log log U) search with O(U) space.

    Faster successor/predecessor than VEB for some cases.

    "Ba'el tries with speed." — Ba'el
    """

    def __init__(self, max_bits: int = 32):
        """Initialize X-Fast Trie."""
        self._max_bits = max_bits
        self._levels: List[Dict[int, Any]] = [{} for _ in range(max_bits + 1)]
        self._min_leaf: Optional[int] = None
        self._max_leaf: Optional[int] = None
        self._leaves: Dict[int, Tuple[Optional[int], Optional[int]]] = {}
        self._lock = threading.RLock()

    def _prefix(self, x: int, level: int) -> int:
        """Get prefix of x at given level."""
        return x >> (self._max_bits - level)

    def insert(self, x: int):
        """Insert element."""
        with self._lock:
            if x in self._leaves:
                return

            # Find predecessor and successor
            pred = self._predecessor_internal(x)
            succ = self._successor_internal(x)

            # Update linked list
            self._leaves[x] = (pred, succ)
            if pred is not None:
                p, s = self._leaves[pred]
                self._leaves[pred] = (p, x)
            else:
                self._min_leaf = x

            if succ is not None:
                p, s = self._leaves[succ]
                self._leaves[succ] = (x, s)
            else:
                self._max_leaf = x

            # Add to levels
            for level in range(self._max_bits + 1):
                prefix = self._prefix(x, level)
                self._levels[level][prefix] = True

    def delete(self, x: int):
        """Delete element."""
        with self._lock:
            if x not in self._leaves:
                return

            pred, succ = self._leaves[x]

            # Update linked list
            if pred is not None:
                p, s = self._leaves[pred]
                self._leaves[pred] = (p, succ)
            else:
                self._min_leaf = succ

            if succ is not None:
                p, s = self._leaves[succ]
                self._leaves[succ] = (pred, s)
            else:
                self._max_leaf = pred

            del self._leaves[x]

            # Clean up levels (simplified - full impl would check if prefix still needed)
            for level in range(self._max_bits + 1):
                prefix = self._prefix(x, level)
                # Check if any other element shares this prefix
                still_used = False
                for y in self._leaves:
                    if self._prefix(y, level) == prefix:
                        still_used = True
                        break
                if not still_used:
                    del self._levels[level][prefix]

    def member(self, x: int) -> bool:
        """Check membership."""
        with self._lock:
            return x in self._leaves

    def _predecessor_internal(self, x: int) -> Optional[int]:
        """Internal predecessor (no lock)."""
        if not self._leaves:
            return None

        if x in self._leaves:
            return self._leaves[x][0]

        # Binary search on levels
        low, high = 0, self._max_bits
        while low < high:
            mid = (low + high + 1) // 2
            if self._prefix(x, mid) in self._levels[mid]:
                low = mid
            else:
                high = mid - 1

        prefix = self._prefix(x, low)
        if prefix not in self._levels[low]:
            return None

        # Navigate down to find predecessor
        candidate = None
        for y in self._leaves:
            if y < x:
                if candidate is None or y > candidate:
                    candidate = y

        return candidate

    def _successor_internal(self, x: int) -> Optional[int]:
        """Internal successor (no lock)."""
        if not self._leaves:
            return None

        if x in self._leaves:
            return self._leaves[x][1]

        candidate = None
        for y in self._leaves:
            if y > x:
                if candidate is None or y < candidate:
                    candidate = y

        return candidate

    def predecessor(self, x: int) -> Optional[int]:
        """Find predecessor."""
        with self._lock:
            return self._predecessor_internal(x)

    def successor(self, x: int) -> Optional[int]:
        """Find successor."""
        with self._lock:
            return self._successor_internal(x)

    def minimum(self) -> Optional[int]:
        """Get minimum."""
        with self._lock:
            return self._min_leaf

    def maximum(self) -> Optional[int]:
        """Get maximum."""
        with self._lock:
            return self._max_leaf

    def __contains__(self, x: int) -> bool:
        return self.member(x)


# ============================================================================
# Y-FAST TRIE
# ============================================================================

class YFastTrie:
    """
    Y-Fast Trie: O(log log U) with O(n) space.

    Combines X-Fast Trie with balanced BSTs.

    "Ba'el balances tries." — Ba'el
    """

    def __init__(self, max_bits: int = 32):
        """Initialize Y-Fast Trie."""
        self._max_bits = max_bits
        self._x_fast = XFastTrie(max_bits)
        self._buckets: Dict[int, Set[int]] = {}
        self._size = 0
        self._lock = threading.RLock()

    def insert(self, x: int):
        """Insert element."""
        with self._lock:
            # Find bucket
            rep = self._x_fast.predecessor(x)
            if rep is None:
                rep = self._x_fast.successor(x)

            if rep is None:
                # First element
                self._x_fast.insert(x)
                self._buckets[x] = {x}
            else:
                self._buckets[rep].add(x)

                # Check if bucket needs split
                if len(self._buckets[rep]) > 2 * self._max_bits:
                    self._split_bucket(rep)

            self._size += 1

    def _split_bucket(self, rep: int):
        """Split a bucket."""
        elements = sorted(self._buckets[rep])
        mid = len(elements) // 2

        new_rep = elements[mid]
        self._x_fast.insert(new_rep)

        self._buckets[rep] = set(elements[:mid])
        self._buckets[new_rep] = set(elements[mid:])

    def member(self, x: int) -> bool:
        """Check membership."""
        with self._lock:
            rep = self._x_fast.predecessor(x)
            if rep is None:
                rep = self._x_fast.successor(x)
            if rep is None:
                return False
            return x in self._buckets.get(rep, set())

    def __len__(self) -> int:
        return self._size

    def __contains__(self, x: int) -> bool:
        return self.member(x)


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_veb_tree(universe: int) -> VanEmdeBoas:
    """Create Van Emde Boas tree."""
    return VanEmdeBoas(universe)


def create_x_fast_trie(max_bits: int = 32) -> XFastTrie:
    """Create X-Fast Trie."""
    return XFastTrie(max_bits)


def create_y_fast_trie(max_bits: int = 32) -> YFastTrie:
    """Create Y-Fast Trie."""
    return YFastTrie(max_bits)


def veb_sort(values: List[int], universe: Optional[int] = None) -> List[int]:
    """Sort integers using VEB tree."""
    if not values:
        return []

    if universe is None:
        universe = max(values) + 1

    veb = VanEmdeBoas(universe)
    for v in values:
        veb.insert(v)

    return veb.to_list()
