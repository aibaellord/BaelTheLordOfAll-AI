"""
BAEL Disjoint Set Union (DSU) Engine
====================================

Union-Find with path compression and union by rank.

"Ba'el unifies sets." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, Generic, Iterator, List, Optional, Set, Tuple, TypeVar
from dataclasses import dataclass, field

logger = logging.getLogger("BAEL.DisjointSetUnion")


T = TypeVar('T')


# ============================================================================
# DSU STATISTICS
# ============================================================================

@dataclass
class DSUStats:
    """DSU statistics."""
    num_elements: int
    num_sets: int
    max_set_size: int
    operations_count: int


# ============================================================================
# ARRAY-BASED DSU
# ============================================================================

class DisjointSetUnion:
    """
    Disjoint Set Union (Union-Find) with integers.

    Features:
    - O(α(n)) find with path compression
    - O(α(n)) union by rank/size
    - α(n) is inverse Ackermann (practically constant)

    "Ba'el finds unions." — Ba'el
    """

    def __init__(self, n: int):
        """
        Initialize DSU with n elements (0 to n-1).

        O(n).
        """
        self._parent = list(range(n))
        self._rank = [0] * n
        self._size = [1] * n
        self._n = n
        self._num_sets = n
        self._ops = 0
        self._lock = threading.RLock()

    def find(self, x: int) -> int:
        """
        Find representative of x's set.

        Uses path compression.
        O(α(n)) amortized.
        """
        with self._lock:
            self._ops += 1
            return self._find(x)

    def _find(self, x: int) -> int:
        """Internal find with path compression."""
        if self._parent[x] != x:
            self._parent[x] = self._find(self._parent[x])
        return self._parent[x]

    def union(self, x: int, y: int) -> bool:
        """
        Union sets containing x and y.

        Uses union by rank.
        O(α(n)) amortized.
        Returns True if x and y were in different sets.
        """
        with self._lock:
            self._ops += 1

            rx, ry = self._find(x), self._find(y)

            if rx == ry:
                return False

            # Union by rank
            if self._rank[rx] < self._rank[ry]:
                rx, ry = ry, rx

            self._parent[ry] = rx
            self._size[rx] += self._size[ry]

            if self._rank[rx] == self._rank[ry]:
                self._rank[rx] += 1

            self._num_sets -= 1
            return True

    def connected(self, x: int, y: int) -> bool:
        """Check if x and y are in same set."""
        with self._lock:
            return self._find(x) == self._find(y)

    def set_size(self, x: int) -> int:
        """Get size of set containing x."""
        with self._lock:
            return self._size[self._find(x)]

    def num_sets(self) -> int:
        """Get number of disjoint sets."""
        return self._num_sets

    def get_sets(self) -> Dict[int, List[int]]:
        """Get all sets as dict (representative -> members)."""
        with self._lock:
            sets: Dict[int, List[int]] = {}
            for i in range(self._n):
                rep = self._find(i)
                if rep not in sets:
                    sets[rep] = []
                sets[rep].append(i)
            return sets

    def get_stats(self) -> DSUStats:
        """Get statistics."""
        with self._lock:
            max_size = max(self._size[self._find(i)] for i in range(self._n)) if self._n > 0 else 0
            return DSUStats(
                num_elements=self._n,
                num_sets=self._num_sets,
                max_set_size=max_size,
                operations_count=self._ops
            )


# ============================================================================
# GENERIC DSU
# ============================================================================

class GenericDSU(Generic[T]):
    """
    Generic Disjoint Set Union for any hashable type.

    "Ba'el unifies any type." — Ba'el
    """

    def __init__(self):
        """Initialize empty DSU."""
        self._parent: Dict[T, T] = {}
        self._rank: Dict[T, int] = {}
        self._size: Dict[T, int] = {}
        self._lock = threading.RLock()

    def make_set(self, x: T):
        """Create singleton set for x."""
        with self._lock:
            if x not in self._parent:
                self._parent[x] = x
                self._rank[x] = 0
                self._size[x] = 1

    def find(self, x: T) -> T:
        """Find representative of x's set."""
        with self._lock:
            self.make_set(x)

            if self._parent[x] != x:
                self._parent[x] = self.find(self._parent[x])

            return self._parent[x]

    def union(self, x: T, y: T) -> bool:
        """Union sets containing x and y."""
        with self._lock:
            self.make_set(x)
            self.make_set(y)

            rx, ry = self.find(x), self.find(y)

            if rx == ry:
                return False

            if self._rank[rx] < self._rank[ry]:
                rx, ry = ry, rx

            self._parent[ry] = rx
            self._size[rx] += self._size[ry]

            if self._rank[rx] == self._rank[ry]:
                self._rank[rx] += 1

            return True

    def connected(self, x: T, y: T) -> bool:
        """Check if x and y are connected."""
        with self._lock:
            if x not in self._parent or y not in self._parent:
                return False
            return self.find(x) == self.find(y)

    def set_size(self, x: T) -> int:
        """Get size of set containing x."""
        with self._lock:
            if x not in self._parent:
                return 0
            return self._size[self.find(x)]

    def num_sets(self) -> int:
        """Get number of disjoint sets."""
        with self._lock:
            return len(set(self.find(x) for x in self._parent))

    def __len__(self) -> int:
        """Total number of elements."""
        return len(self._parent)


# ============================================================================
# WEIGHTED DSU
# ============================================================================

class WeightedDSU:
    """
    DSU with weighted edges (for potential/distance queries).

    Supports queries like "what is the difference between x and y?"

    "Ba'el weighs unions." — Ba'el
    """

    def __init__(self, n: int):
        """Initialize weighted DSU with n elements."""
        self._parent = list(range(n))
        self._rank = [0] * n
        self._diff = [0] * n  # diff[x] = value(x) - value(parent[x])
        self._n = n
        self._lock = threading.RLock()

    def find(self, x: int) -> Tuple[int, int]:
        """
        Find representative and weight from x to representative.

        Returns (representative, weight).
        """
        with self._lock:
            if self._parent[x] == x:
                return (x, 0)

            root, w = self.find(self._parent[x])
            self._parent[x] = root
            self._diff[x] += w
            return (root, self._diff[x])

    def union(self, x: int, y: int, weight: int) -> bool:
        """
        Union x and y with value(x) - value(y) = weight.

        Returns True if successful (were in different sets).
        """
        with self._lock:
            rx, wx = self.find(x)
            ry, wy = self.find(y)

            if rx == ry:
                return False

            # Union by rank
            if self._rank[rx] < self._rank[ry]:
                rx, ry = ry, rx
                wx, wy = wy, wx
                weight = -weight

            self._parent[ry] = rx
            # value(y) - value(ry) = wy
            # value(x) - value(rx) = wx
            # value(x) - value(y) = weight
            # value(ry) - value(rx) = value(y) - wy - (value(x) - wx)
            #                       = value(y) - value(x) + wx - wy
            #                       = -weight + wx - wy
            self._diff[ry] = wx - wy - weight

            if self._rank[rx] == self._rank[ry]:
                self._rank[rx] += 1

            return True

    def diff(self, x: int, y: int) -> Optional[int]:
        """
        Get value(x) - value(y) if in same set.

        Returns None if not connected.
        """
        with self._lock:
            rx, wx = self.find(x)
            ry, wy = self.find(y)

            if rx != ry:
                return None

            return wx - wy

    def connected(self, x: int, y: int) -> bool:
        """Check if x and y are connected."""
        with self._lock:
            rx, _ = self.find(x)
            ry, _ = self.find(y)
            return rx == ry


# ============================================================================
# PERSISTENT DSU
# ============================================================================

class PersistentDSU:
    """
    Partially persistent DSU (can query any past version).

    Uses versioned arrays.

    "Ba'el persists unions." — Ba'el
    """

    def __init__(self, n: int):
        """Initialize persistent DSU."""
        self._n = n
        self._parent = list(range(n))
        self._rank = [0] * n

        # History: (version, element, old_parent, old_rank)
        self._history: List[Tuple[int, int, int, int]] = []
        self._version = 0
        self._lock = threading.RLock()

    def find(self, x: int, version: Optional[int] = None) -> int:
        """Find representative at given version (or current)."""
        with self._lock:
            if version is None:
                version = self._version

            # Reconstruct state at version
            parent = list(self._parent)

            # Undo changes after version
            for v, elem, old_p, _ in reversed(self._history):
                if v > version:
                    parent[elem] = old_p
                else:
                    break

            # Path compression (on copy)
            root = x
            while parent[root] != root:
                root = parent[root]

            return root

    def union(self, x: int, y: int) -> bool:
        """Union sets at current version."""
        with self._lock:
            rx, ry = self.find(x), self.find(y)

            if rx == ry:
                return False

            self._version += 1

            if self._rank[rx] < self._rank[ry]:
                rx, ry = ry, rx

            # Save history
            self._history.append((self._version, ry, self._parent[ry], self._rank[rx]))

            self._parent[ry] = rx

            if self._rank[rx] == self._rank[ry]:
                self._rank[rx] += 1

            return True

    def connected(self, x: int, y: int, version: Optional[int] = None) -> bool:
        """Check if connected at version."""
        return self.find(x, version) == self.find(y, version)

    @property
    def version(self) -> int:
        """Current version."""
        return self._version


# ============================================================================
# ROLLBACK DSU
# ============================================================================

class RollbackDSU:
    """
    DSU with rollback support.

    Can undo operations.

    "Ba'el rolls back unions." — Ba'el
    """

    def __init__(self, n: int):
        """Initialize rollback DSU."""
        self._parent = list(range(n))
        self._rank = [0] * n
        self._n = n

        # Stack of (x, old_parent_x, y, old_parent_y, old_rank_x, old_rank_y)
        self._history: List[Tuple] = []
        self._lock = threading.RLock()

    def find(self, x: int) -> int:
        """Find without path compression (to support rollback)."""
        while self._parent[x] != x:
            x = self._parent[x]
        return x

    def union(self, x: int, y: int) -> bool:
        """Union with history tracking."""
        with self._lock:
            rx, ry = self.find(x), self.find(y)

            if rx == ry:
                self._history.append(None)  # No-op marker
                return False

            # Save state before modification
            self._history.append((
                rx, self._parent[rx],
                ry, self._parent[ry],
                self._rank[rx], self._rank[ry]
            ))

            if self._rank[rx] < self._rank[ry]:
                rx, ry = ry, rx

            self._parent[ry] = rx

            if self._rank[rx] == self._rank[ry]:
                self._rank[rx] += 1

            return True

    def rollback(self):
        """Undo last union operation."""
        with self._lock:
            if not self._history:
                return

            state = self._history.pop()

            if state is None:
                return  # Was a no-op

            rx, old_parent_rx, ry, old_parent_ry, old_rank_rx, old_rank_ry = state

            self._parent[rx] = old_parent_rx
            self._parent[ry] = old_parent_ry
            self._rank[rx] = old_rank_rx
            self._rank[ry] = old_rank_ry

    def connected(self, x: int, y: int) -> bool:
        """Check if connected."""
        return self.find(x) == self.find(y)

    def checkpoint(self) -> int:
        """Get current checkpoint (history length)."""
        return len(self._history)

    def rollback_to(self, checkpoint: int):
        """Rollback to checkpoint."""
        with self._lock:
            while len(self._history) > checkpoint:
                self.rollback()


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_dsu(n: int) -> DisjointSetUnion:
    """Create DSU for n elements."""
    return DisjointSetUnion(n)


def create_generic_dsu() -> GenericDSU:
    """Create generic DSU."""
    return GenericDSU()


def create_weighted_dsu(n: int) -> WeightedDSU:
    """Create weighted DSU."""
    return WeightedDSU(n)


def create_rollback_dsu(n: int) -> RollbackDSU:
    """Create rollback DSU."""
    return RollbackDSU(n)


def connected_components(n: int, edges: List[Tuple[int, int]]) -> List[List[int]]:
    """Find connected components using DSU."""
    dsu = DisjointSetUnion(n)
    for u, v in edges:
        dsu.union(u, v)
    return list(dsu.get_sets().values())


def is_connected(n: int, edges: List[Tuple[int, int]]) -> bool:
    """Check if graph is connected."""
    dsu = DisjointSetUnion(n)
    for u, v in edges:
        dsu.union(u, v)
    return dsu.num_sets() == 1
