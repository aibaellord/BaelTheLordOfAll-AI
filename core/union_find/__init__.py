"""
BAEL Union-Find Engine Implementation
======================================

Disjoint set operations with path compression.

"Ba'el unites and finds all connected truths." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, Generic, Iterator, List, Optional, Set, TypeVar
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("BAEL.UnionFind")

T = TypeVar('T')


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class UnionFindStats:
    """Union-Find statistics."""
    element_count: int = 0
    set_count: int = 0
    union_operations: int = 0
    find_operations: int = 0
    path_compressions: int = 0


# ============================================================================
# UNION-FIND ENGINE
# ============================================================================

class UnionFindEngine(Generic[T]):
    """
    Disjoint set (Union-Find) implementation.

    Features:
    - Path compression
    - Union by rank
    - O(α(n)) amortized operations

    "Ba'el unifies all connected elements." — Ba'el
    """

    def __init__(self):
        """Initialize Union-Find."""
        # Parent pointers (element -> parent)
        self._parent: Dict[T, T] = {}

        # Rank (for union by rank)
        self._rank: Dict[T, int] = {}

        # Size of each set (stored at root)
        self._size: Dict[T, int] = {}

        # Stats
        self._stats = UnionFindStats()

        # Thread safety
        self._lock = threading.RLock()

        logger.info("Union-Find initialized")

    # ========================================================================
    # BASIC OPERATIONS
    # ========================================================================

    def make_set(self, element: T) -> None:
        """
        Create a new set with single element.

        Args:
            element: Element to add
        """
        with self._lock:
            if element in self._parent:
                return  # Already exists

            self._parent[element] = element
            self._rank[element] = 0
            self._size[element] = 1

            self._stats.element_count += 1
            self._stats.set_count += 1

    def find(self, element: T) -> T:
        """
        Find root of element's set (with path compression).

        Args:
            element: Element to find

        Returns:
            Root element
        """
        with self._lock:
            if element not in self._parent:
                self.make_set(element)

            self._stats.find_operations += 1

            return self._find_with_compression(element)

    def _find_with_compression(self, element: T) -> T:
        """Find with path compression."""
        if self._parent[element] != element:
            # Path compression
            root = self._find_with_compression(self._parent[element])

            if self._parent[element] != root:
                self._stats.path_compressions += 1

            self._parent[element] = root

        return self._parent[element]

    def union(self, a: T, b: T) -> bool:
        """
        Union two sets (by rank).

        Args:
            a: First element
            b: Second element

        Returns:
            True if sets were merged (weren't already same set)
        """
        with self._lock:
            root_a = self.find(a)
            root_b = self.find(b)

            if root_a == root_b:
                return False  # Already in same set

            self._stats.union_operations += 1

            # Union by rank
            if self._rank[root_a] < self._rank[root_b]:
                self._parent[root_a] = root_b
                self._size[root_b] += self._size[root_a]
            elif self._rank[root_a] > self._rank[root_b]:
                self._parent[root_b] = root_a
                self._size[root_a] += self._size[root_b]
            else:
                self._parent[root_b] = root_a
                self._rank[root_a] += 1
                self._size[root_a] += self._size[root_b]

            self._stats.set_count -= 1

            return True

    def connected(self, a: T, b: T) -> bool:
        """
        Check if two elements are in the same set.

        Args:
            a: First element
            b: Second element

        Returns:
            True if connected
        """
        with self._lock:
            if a not in self._parent or b not in self._parent:
                return False

            return self.find(a) == self.find(b)

    # ========================================================================
    # SET OPERATIONS
    # ========================================================================

    def get_set_size(self, element: T) -> int:
        """
        Get size of element's set.

        Args:
            element: Element in set

        Returns:
            Set size
        """
        with self._lock:
            if element not in self._parent:
                return 0

            root = self.find(element)
            return self._size[root]

    def get_set_members(self, element: T) -> Set[T]:
        """
        Get all members of element's set.

        Args:
            element: Element in set

        Returns:
            Set of all members
        """
        with self._lock:
            if element not in self._parent:
                return set()

            root = self.find(element)
            members = set()

            for e in self._parent:
                if self.find(e) == root:
                    members.add(e)

            return members

    def get_all_sets(self) -> List[Set[T]]:
        """
        Get all disjoint sets.

        Returns:
            List of sets
        """
        with self._lock:
            sets: Dict[T, Set[T]] = {}

            for element in self._parent:
                root = self.find(element)

                if root not in sets:
                    sets[root] = set()

                sets[root].add(element)

            return list(sets.values())

    def get_roots(self) -> Set[T]:
        """
        Get all root elements.

        Returns:
            Set of roots
        """
        with self._lock:
            roots = set()

            for element in self._parent:
                if self._parent[element] == element:
                    roots.add(element)

            return roots

    # ========================================================================
    # BULK OPERATIONS
    # ========================================================================

    def union_all(self, elements: List[T]) -> None:
        """
        Union all elements into one set.

        Args:
            elements: Elements to union
        """
        if len(elements) < 2:
            if elements:
                self.make_set(elements[0])
            return

        first = elements[0]
        for element in elements[1:]:
            self.union(first, element)

    def add_elements(self, elements: List[T]) -> None:
        """
        Add multiple elements as separate sets.

        Args:
            elements: Elements to add
        """
        for element in elements:
            self.make_set(element)

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def __contains__(self, element: T) -> bool:
        """Check if element exists."""
        return element in self._parent

    def __len__(self) -> int:
        """Get total element count."""
        return len(self._parent)

    @property
    def set_count(self) -> int:
        """Get number of disjoint sets."""
        return self._stats.set_count

    @property
    def element_count(self) -> int:
        """Get total element count."""
        return self._stats.element_count

    def clear(self) -> None:
        """Clear all data."""
        with self._lock:
            self._parent.clear()
            self._rank.clear()
            self._size.clear()
            self._stats = UnionFindStats()

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'element_count': self._stats.element_count,
            'set_count': self._stats.set_count,
            'union_operations': self._stats.union_operations,
            'find_operations': self._stats.find_operations,
            'path_compressions': self._stats.path_compressions
        }


# ============================================================================
# WEIGHTED UNION-FIND
# ============================================================================

class WeightedUnionFind(Generic[T]):
    """
    Weighted Union-Find with edge weights.

    Supports queries like: what is the relative weight between two elements?

    "Ba'el knows the weight of all connections." — Ba'el
    """

    def __init__(self):
        """Initialize weighted Union-Find."""
        self._parent: Dict[T, T] = {}
        self._rank: Dict[T, int] = {}
        self._weight: Dict[T, float] = {}  # Weight from element to parent

        self._lock = threading.RLock()

        logger.info("Weighted Union-Find initialized")

    def make_set(self, element: T) -> None:
        """Create new set with single element."""
        with self._lock:
            if element in self._parent:
                return

            self._parent[element] = element
            self._rank[element] = 0
            self._weight[element] = 0.0

    def find(self, element: T) -> Tuple[T, float]:
        """
        Find root and weight from element to root.

        Args:
            element: Element to find

        Returns:
            (root, weight_to_root)
        """
        with self._lock:
            if element not in self._parent:
                self.make_set(element)

            return self._find_with_weight(element)

    def _find_with_weight(self, element: T) -> Tuple[T, float]:
        """Find with path compression and weight tracking."""
        if self._parent[element] == element:
            return element, 0.0

        root, parent_weight = self._find_with_weight(self._parent[element])

        # Path compression
        total_weight = self._weight[element] + parent_weight
        self._parent[element] = root
        self._weight[element] = total_weight

        return root, total_weight

    def union(self, a: T, b: T, weight: float = 0.0) -> bool:
        """
        Union with weight: weight(a) - weight(b) = weight.

        Args:
            a: First element
            b: Second element
            weight: Weight difference

        Returns:
            True if merged
        """
        with self._lock:
            root_a, weight_a = self.find(a)
            root_b, weight_b = self.find(b)

            if root_a == root_b:
                return False

            # weight_a + new_edge = weight + weight_b
            new_edge = weight + weight_b - weight_a

            if self._rank[root_a] < self._rank[root_b]:
                self._parent[root_a] = root_b
                self._weight[root_a] = new_edge
            elif self._rank[root_a] > self._rank[root_b]:
                self._parent[root_b] = root_a
                self._weight[root_b] = -new_edge
            else:
                self._parent[root_b] = root_a
                self._weight[root_b] = -new_edge
                self._rank[root_a] += 1

            return True

    def get_weight_difference(self, a: T, b: T) -> Optional[float]:
        """
        Get weight difference between two elements.

        Args:
            a: First element
            b: Second element

        Returns:
            weight(a) - weight(b), or None if not connected
        """
        with self._lock:
            root_a, weight_a = self.find(a)
            root_b, weight_b = self.find(b)

            if root_a != root_b:
                return None

            return weight_a - weight_b


# Import for type hints
from typing import Tuple


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_union_find() -> UnionFindEngine:
    """Create a new Union-Find structure."""
    return UnionFindEngine()


def create_weighted_union_find() -> WeightedUnionFind:
    """Create a weighted Union-Find structure."""
    return WeightedUnionFind()


def find_connected_components(
    edges: List[Tuple[Any, Any]]
) -> List[Set[Any]]:
    """
    Find connected components from edge list.

    Args:
        edges: List of (a, b) edges

    Returns:
        List of connected component sets
    """
    uf = UnionFindEngine()

    for a, b in edges:
        uf.union(a, b)

    return uf.get_all_sets()


def are_connected(
    edges: List[Tuple[Any, Any]],
    a: Any,
    b: Any
) -> bool:
    """
    Check if two nodes are connected via edges.

    Args:
        edges: List of edges
        a: First node
        b: Second node

    Returns:
        True if connected
    """
    uf = UnionFindEngine()

    for x, y in edges:
        uf.union(x, y)

    return uf.connected(a, b)
