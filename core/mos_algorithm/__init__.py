"""
BAEL Mo's Algorithm Engine
==========================

Offline query processing with sqrt decomposition.

"Ba'el processes queries in square root time." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Tuple, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum, auto
from math import sqrt, ceil
from collections import defaultdict

logger = logging.getLogger("BAEL.MosAlgorithm")


T = TypeVar('T')


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Query:
    """Range query."""
    left: int
    right: int  # Inclusive
    index: int  # Original index for result ordering


@dataclass
class QueryResult:
    """Query result."""
    query_index: int
    answer: Any


# ============================================================================
# MO'S ALGORITHM
# ============================================================================

class MosAlgorithm(Generic[T]):
    """
    Mo's Algorithm for offline range queries.

    Features:
    - O((n + q) * sqrt(n)) time complexity
    - Works for any add/remove operation
    - Optimal query ordering

    "Ba'el orders queries for efficiency." — Ba'el
    """

    def __init__(
        self,
        array: List[T],
        add_right: Callable[[T], None],
        remove_right: Callable[[T], None],
        add_left: Callable[[T], None],
        remove_left: Callable[[T], None],
        get_answer: Callable[[], Any]
    ):
        """
        Initialize Mo's Algorithm.

        Args:
            array: The array to query
            add_right: Add element on right side
            remove_right: Remove element from right side
            add_left: Add element on left side
            remove_left: Remove element from left side
            get_answer: Get current answer
        """
        self._array = array
        self._n = len(array)
        self._block_size = max(1, int(sqrt(self._n)))

        self._add_right = add_right
        self._remove_right = remove_right
        self._add_left = add_left
        self._remove_left = remove_left
        self._get_answer = get_answer

        self._lock = threading.RLock()

    def _get_block(self, index: int) -> int:
        """Get block number for index."""
        return index // self._block_size

    def _compare_queries(self, q: Query) -> Tuple[int, int]:
        """
        Key function for sorting queries.

        Uses Mo's ordering: sort by block of left endpoint,
        then by right endpoint (alternating for better cache).
        """
        block = self._get_block(q.left)
        # Alternate right endpoint ordering for adjacent blocks
        if block % 2 == 0:
            return (block, q.right)
        else:
            return (block, -q.right)

    def process_queries(self, queries: List[Tuple[int, int]]) -> List[Any]:
        """
        Process range queries.

        Args:
            queries: List of (left, right) pairs (0-indexed, inclusive)

        Returns:
            Answers in original query order
        """
        with self._lock:
            if not queries:
                return []

            # Create query objects
            query_objs = [
                Query(left=l, right=r, index=i)
                for i, (l, r) in enumerate(queries)
            ]

            # Sort queries using Mo's ordering
            query_objs.sort(key=self._compare_queries)

            # Initialize window
            current_left = 0
            current_right = -1

            results = [None] * len(queries)

            for query in query_objs:
                # Extend right
                while current_right < query.right:
                    current_right += 1
                    self._add_right(self._array[current_right])

                # Extend left
                while current_left > query.left:
                    current_left -= 1
                    self._add_left(self._array[current_left])

                # Shrink right
                while current_right > query.right:
                    self._remove_right(self._array[current_right])
                    current_right -= 1

                # Shrink left
                while current_left < query.left:
                    self._remove_left(self._array[current_left])
                    current_left += 1

                # Get answer
                results[query.index] = self._get_answer()

            return results


# ============================================================================
# SPECIALIZED MO'S ALGORITHMS
# ============================================================================

class DistinctCountMo:
    """
    Count distinct elements in range using Mo's algorithm.

    "Ba'el counts distinct elements." — Ba'el
    """

    def __init__(self, array: List[int]):
        """Initialize."""
        self._array = array
        self._n = len(array)
        self._block_size = max(1, int(sqrt(self._n)))

        self._count: Dict[int, int] = defaultdict(int)
        self._distinct = 0

    def _add(self, val: int):
        """Add element."""
        if self._count[val] == 0:
            self._distinct += 1
        self._count[val] += 1

    def _remove(self, val: int):
        """Remove element."""
        self._count[val] -= 1
        if self._count[val] == 0:
            self._distinct -= 1

    def process_queries(self, queries: List[Tuple[int, int]]) -> List[int]:
        """Process distinct count queries."""
        mo = MosAlgorithm(
            self._array,
            add_right=self._add,
            remove_right=self._remove,
            add_left=self._add,
            remove_left=self._remove,
            get_answer=lambda: self._distinct
        )
        return mo.process_queries(queries)


class RangeSumMo:
    """
    Range sum using Mo's algorithm.

    Note: Prefix sums are better for this, but demonstrates Mo's.

    "Ba'el sums ranges." — Ba'el
    """

    def __init__(self, array: List[int]):
        """Initialize."""
        self._array = array
        self._n = len(array)
        self._current_sum = 0

    def _add(self, val: int):
        self._current_sum += val

    def _remove(self, val: int):
        self._current_sum -= val

    def process_queries(self, queries: List[Tuple[int, int]]) -> List[int]:
        """Process sum queries."""
        mo = MosAlgorithm(
            self._array,
            add_right=self._add,
            remove_right=self._remove,
            add_left=self._add,
            remove_left=self._remove,
            get_answer=lambda: self._current_sum
        )
        return mo.process_queries(queries)


class FrequencyMo:
    """
    Query frequency statistics using Mo's algorithm.

    "Ba'el tracks frequencies." — Ba'el
    """

    def __init__(self, array: List[int]):
        """Initialize."""
        self._array = array
        self._n = len(array)

        self._count: Dict[int, int] = defaultdict(int)
        self._freq_count: Dict[int, int] = defaultdict(int)  # How many elements have this frequency
        self._max_freq = 0

    def _add(self, val: int):
        """Add element."""
        old_freq = self._count[val]
        if old_freq > 0:
            self._freq_count[old_freq] -= 1

        self._count[val] += 1
        new_freq = self._count[val]
        self._freq_count[new_freq] += 1

        self._max_freq = max(self._max_freq, new_freq)

    def _remove(self, val: int):
        """Remove element."""
        old_freq = self._count[val]
        self._freq_count[old_freq] -= 1

        if old_freq == self._max_freq and self._freq_count[old_freq] == 0:
            self._max_freq -= 1

        self._count[val] -= 1
        new_freq = self._count[val]
        if new_freq > 0:
            self._freq_count[new_freq] += 1

    def get_mode(self) -> int:
        """Get current mode (most frequent element)."""
        return self._max_freq

    def process_mode_queries(self, queries: List[Tuple[int, int]]) -> List[int]:
        """Process mode queries (max frequency in range)."""
        mo = MosAlgorithm(
            self._array,
            add_right=self._add,
            remove_right=self._remove,
            add_left=self._add,
            remove_left=self._remove,
            get_answer=lambda: self._max_freq
        )
        return mo.process_queries(queries)


# ============================================================================
# MO'S ON TREES
# ============================================================================

class MosOnTree:
    """
    Mo's algorithm adapted for tree path queries.

    Uses Euler tour to linearize tree.

    "Ba'el applies Mo's to trees." — Ba'el
    """

    def __init__(
        self,
        n: int,
        edges: List[Tuple[int, int]],
        values: List[int]
    ):
        """
        Initialize Mo's on tree.

        Args:
            n: Number of nodes
            edges: Tree edges
            values: Node values
        """
        self._n = n
        self._values = values
        self._block_size = max(1, int(sqrt(2 * n)))

        # Build adjacency
        self._adj: List[List[int]] = [[] for _ in range(n)]
        for u, v in edges:
            self._adj[u].append(v)
            self._adj[v].append(u)

        # Euler tour
        self._first: List[int] = [0] * n  # First occurrence in tour
        self._last: List[int] = [0] * n   # Last occurrence in tour
        self._euler_tour: List[int] = []
        self._depth: List[int] = [0] * n
        self._parent: List[int] = [-1] * n

        self._build_euler_tour(0, -1)

        # LCA with binary lifting
        self._log = 1
        while (1 << self._log) < n:
            self._log += 1

        self._ancestors: List[List[int]] = [[-1] * self._log for _ in range(n)]
        self._build_lca()

        # State for queries
        self._in_path = [False] * n
        self._count: Dict[int, int] = defaultdict(int)
        self._distinct = 0

    def _build_euler_tour(self, u: int, parent: int):
        """Build Euler tour."""
        self._first[u] = len(self._euler_tour)
        self._euler_tour.append(u)
        self._parent[u] = parent

        for v in self._adj[u]:
            if v != parent:
                self._depth[v] = self._depth[u] + 1
                self._build_euler_tour(v, u)

        self._last[u] = len(self._euler_tour)
        self._euler_tour.append(u)

    def _build_lca(self):
        """Build LCA structure."""
        for i in range(self._n):
            self._ancestors[i][0] = self._parent[i]

        for j in range(1, self._log):
            for i in range(self._n):
                if self._ancestors[i][j - 1] != -1:
                    self._ancestors[i][j] = self._ancestors[
                        self._ancestors[i][j - 1]
                    ][j - 1]

    def _lca(self, u: int, v: int) -> int:
        """Find LCA of u and v."""
        if self._depth[u] < self._depth[v]:
            u, v = v, u

        diff = self._depth[u] - self._depth[v]
        for j in range(self._log):
            if (diff >> j) & 1:
                u = self._ancestors[u][j]

        if u == v:
            return u

        for j in range(self._log - 1, -1, -1):
            if self._ancestors[u][j] != self._ancestors[v][j]:
                u = self._ancestors[u][j]
                v = self._ancestors[v][j]

        return self._parent[u]

    def _toggle(self, u: int):
        """Toggle node in/out of path."""
        if self._in_path[u]:
            # Remove
            val = self._values[u]
            self._count[val] -= 1
            if self._count[val] == 0:
                self._distinct -= 1
            self._in_path[u] = False
        else:
            # Add
            val = self._values[u]
            if self._count[val] == 0:
                self._distinct += 1
            self._count[val] += 1
            self._in_path[u] = True

    def process_path_queries(
        self,
        queries: List[Tuple[int, int]]
    ) -> List[int]:
        """
        Process distinct count queries on tree paths.

        Args:
            queries: List of (u, v) node pairs

        Returns:
            Distinct value counts for each path
        """
        if not queries:
            return []

        # Convert to Euler tour queries
        tour_queries = []
        lca_needed = []

        for i, (u, v) in enumerate(queries):
            # Ensure first[u] <= first[v]
            if self._first[u] > self._first[v]:
                u, v = v, u

            lca = self._lca(u, v)

            if lca == u:
                # u is ancestor of v
                tour_queries.append((self._first[u], self._first[v], i))
                lca_needed.append(-1)  # No need to add LCA
            else:
                # Use last[u] to first[v]
                tour_queries.append((self._last[u], self._first[v], i))
                lca_needed.append(lca)

        # Sort queries (Mo's ordering)
        def query_key(q):
            l, r, idx = q
            block = l // self._block_size
            return (block, r if block % 2 == 0 else -r)

        sorted_queries = sorted(
            enumerate(tour_queries),
            key=lambda x: query_key(x[1])
        )

        # Process queries
        results = [0] * len(queries)
        current_left = 0
        current_right = -1

        for sorted_idx, (orig_idx, (l, r, query_idx)) in enumerate(sorted_queries):
            # Expand/shrink window
            while current_right < r:
                current_right += 1
                self._toggle(self._euler_tour[current_right])

            while current_left > l:
                current_left -= 1
                self._toggle(self._euler_tour[current_left])

            while current_right > r:
                self._toggle(self._euler_tour[current_right])
                current_right -= 1

            while current_left < l:
                self._toggle(self._euler_tour[current_left])
                current_left += 1

            # Handle LCA if needed
            lca = lca_needed[orig_idx]
            if lca != -1:
                self._toggle(lca)

            results[query_idx] = self._distinct

            if lca != -1:
                self._toggle(lca)  # Remove LCA

        return results


# ============================================================================
# CONVENIENCE
# ============================================================================

def distinct_count_queries(
    array: List[int],
    queries: List[Tuple[int, int]]
) -> List[int]:
    """Count distinct elements in ranges."""
    mo = DistinctCountMo(array)
    return mo.process_queries(queries)


def range_mode_queries(
    array: List[int],
    queries: List[Tuple[int, int]]
) -> List[int]:
    """Find mode (max frequency) in ranges."""
    mo = FrequencyMo(array)
    return mo.process_mode_queries(queries)


def tree_path_distinct(
    n: int,
    edges: List[Tuple[int, int]],
    values: List[int],
    queries: List[Tuple[int, int]]
) -> List[int]:
    """Count distinct values on tree paths."""
    mo = MosOnTree(n, edges, values)
    return mo.process_path_queries(queries)


def create_mos_algorithm(
    array: List[Any],
    add: Callable[[Any], None],
    remove: Callable[[Any], None],
    get_answer: Callable[[], Any]
) -> MosAlgorithm:
    """Create custom Mo's algorithm instance."""
    return MosAlgorithm(
        array,
        add_right=add,
        remove_right=remove,
        add_left=add,
        remove_left=remove,
        get_answer=get_answer
    )
