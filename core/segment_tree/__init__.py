"""
BAEL Segment Tree Engine Implementation
========================================

Range queries with O(log n) updates.

"Ba'el queries all ranges with divine efficiency." — Ba'el
"""

import logging
import threading
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("BAEL.SegmentTree")

T = TypeVar('T')


# ============================================================================
# DATA STRUCTURES
# ============================================================================

class SegmentTreeOp(Enum):
    """Built-in segment tree operations."""
    SUM = "sum"
    MIN = "min"
    MAX = "max"
    GCD = "gcd"
    PRODUCT = "product"


@dataclass
class SegmentTreeConfig:
    """Segment tree configuration."""
    lazy_propagation: bool = True


# ============================================================================
# SEGMENT TREE ENGINE
# ============================================================================

class SegmentTreeEngine(Generic[T]):
    """
    Segment tree for range queries.

    Features:
    - O(log n) point updates
    - O(log n) range queries
    - Lazy propagation for range updates
    - Custom aggregation functions

    "Ba'el aggregates all segments efficiently." — Ba'el
    """

    def __init__(
        self,
        data: List[T],
        operation: Callable[[T, T], T],
        identity: T,
        config: Optional[SegmentTreeConfig] = None
    ):
        """
        Initialize segment tree.

        Args:
            data: Initial data
            operation: Aggregation function (must be associative)
            identity: Identity element for operation
            config: Configuration
        """
        self.config = config or SegmentTreeConfig()
        self.operation = operation
        self.identity = identity

        self._n = len(data)
        self._data = data.copy()

        # Tree size (next power of 2)
        self._size = 1
        while self._size < self._n:
            self._size *= 2

        # Tree storage
        self._tree: List[T] = [identity] * (2 * self._size)

        # Lazy propagation
        self._lazy: List[Optional[T]] = [None] * (2 * self._size)

        # Build tree
        self._build()

        self._lock = threading.RLock()

        logger.info(f"Segment tree initialized (n={self._n})")

    def _build(self) -> None:
        """Build the tree from data."""
        # Fill leaves
        for i in range(self._n):
            self._tree[self._size + i] = self._data[i]

        # Build internal nodes
        for i in range(self._size - 1, 0, -1):
            self._tree[i] = self.operation(
                self._tree[2 * i],
                self._tree[2 * i + 1]
            )

    def _push_down(self, node: int) -> None:
        """Push lazy value down to children."""
        if self._lazy[node] is not None:
            left = 2 * node
            right = 2 * node + 1

            if left < len(self._tree):
                self._apply_lazy(left, self._lazy[node])
            if right < len(self._tree):
                self._apply_lazy(right, self._lazy[node])

            self._lazy[node] = None

    def _apply_lazy(self, node: int, value: T) -> None:
        """Apply lazy value to node."""
        self._tree[node] = self.operation(self._tree[node], value)

        if node < self._size:  # Not a leaf
            if self._lazy[node] is None:
                self._lazy[node] = value
            else:
                self._lazy[node] = self.operation(self._lazy[node], value)

    # ========================================================================
    # POINT OPERATIONS
    # ========================================================================

    def update(self, index: int, value: T) -> None:
        """
        Update single element.

        Args:
            index: Index to update (0-based)
            value: New value
        """
        if index < 0 or index >= self._n:
            raise IndexError(f"Index {index} out of range [0, {self._n})")

        with self._lock:
            self._data[index] = value

            # Update tree
            pos = self._size + index
            self._tree[pos] = value

            # Update ancestors
            pos //= 2
            while pos >= 1:
                self._tree[pos] = self.operation(
                    self._tree[2 * pos],
                    self._tree[2 * pos + 1]
                )
                pos //= 2

    def get(self, index: int) -> T:
        """
        Get single element.

        Args:
            index: Index (0-based)

        Returns:
            Element value
        """
        if index < 0 or index >= self._n:
            raise IndexError(f"Index {index} out of range")

        return self._data[index]

    # ========================================================================
    # RANGE QUERIES
    # ========================================================================

    def query(self, left: int, right: int) -> T:
        """
        Query range [left, right).

        Args:
            left: Start index (inclusive)
            right: End index (exclusive)

        Returns:
            Aggregated result
        """
        if left < 0:
            left = 0
        if right > self._n:
            right = self._n
        if left >= right:
            return self.identity

        with self._lock:
            return self._query(1, 0, self._size, left, right)

    def _query(
        self,
        node: int,
        node_left: int,
        node_right: int,
        query_left: int,
        query_right: int
    ) -> T:
        """Recursive query."""
        if query_right <= node_left or query_left >= node_right:
            # No overlap
            return self.identity

        if query_left <= node_left and node_right <= query_right:
            # Complete overlap
            return self._tree[node]

        # Push lazy values
        if self.config.lazy_propagation:
            self._push_down(node)

        # Partial overlap
        mid = (node_left + node_right) // 2

        left_result = self._query(
            2 * node, node_left, mid, query_left, query_right
        )
        right_result = self._query(
            2 * node + 1, mid, node_right, query_left, query_right
        )

        return self.operation(left_result, right_result)

    # ========================================================================
    # RANGE UPDATES
    # ========================================================================

    def update_range(self, left: int, right: int, value: T) -> None:
        """
        Update range [left, right) with value.

        Args:
            left: Start index (inclusive)
            right: End index (exclusive)
            value: Value to apply
        """
        if not self.config.lazy_propagation:
            # Fallback to individual updates
            for i in range(left, right):
                self.update(i, self.operation(self._data[i], value))
            return

        if left < 0:
            left = 0
        if right > self._n:
            right = self._n
        if left >= right:
            return

        with self._lock:
            self._update_range(1, 0, self._size, left, right, value)

    def _update_range(
        self,
        node: int,
        node_left: int,
        node_right: int,
        update_left: int,
        update_right: int,
        value: T
    ) -> None:
        """Recursive range update."""
        if update_right <= node_left or update_left >= node_right:
            return

        if update_left <= node_left and node_right <= update_right:
            self._apply_lazy(node, value)
            return

        self._push_down(node)

        mid = (node_left + node_right) // 2

        self._update_range(
            2 * node, node_left, mid, update_left, update_right, value
        )
        self._update_range(
            2 * node + 1, mid, node_right, update_left, update_right, value
        )

        self._tree[node] = self.operation(
            self._tree[2 * node],
            self._tree[2 * node + 1]
        )

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def __len__(self) -> int:
        return self._n

    def __getitem__(self, index: int) -> T:
        return self.get(index)

    def __setitem__(self, index: int, value: T) -> None:
        self.update(index, value)

    def to_list(self) -> List[T]:
        """Get all data as list."""
        return self._data.copy()


# ============================================================================
# SPECIALIZED SEGMENT TREES
# ============================================================================

class SumSegmentTree(SegmentTreeEngine[int]):
    """Segment tree for range sum queries."""

    def __init__(self, data: List[int]):
        super().__init__(data, lambda a, b: a + b, 0)


class MinSegmentTree(SegmentTreeEngine):
    """Segment tree for range minimum queries."""

    def __init__(self, data: List[float]):
        super().__init__(data, min, float('inf'))


class MaxSegmentTree(SegmentTreeEngine):
    """Segment tree for range maximum queries."""

    def __init__(self, data: List[float]):
        super().__init__(data, max, float('-inf'))


class ProductSegmentTree(SegmentTreeEngine[int]):
    """Segment tree for range product queries."""

    def __init__(self, data: List[int]):
        super().__init__(data, lambda a, b: a * b, 1)


# ============================================================================
# 2D SEGMENT TREE
# ============================================================================

class SegmentTree2D:
    """
    2D segment tree for rectangle queries.

    "Ba'el queries two dimensions with equal mastery." — Ba'el
    """

    def __init__(
        self,
        matrix: List[List[int]],
        operation: Callable[[int, int], int] = lambda a, b: a + b,
        identity: int = 0
    ):
        """Initialize 2D segment tree."""
        if not matrix or not matrix[0]:
            self._rows = 0
            self._cols = 0
            self._tree = []
            return

        self._rows = len(matrix)
        self._cols = len(matrix[0])
        self._operation = operation
        self._identity = identity

        # Build 2D tree
        self._size_r = 1
        while self._size_r < self._rows:
            self._size_r *= 2

        self._size_c = 1
        while self._size_c < self._cols:
            self._size_c *= 2

        self._tree = [[identity] * (2 * self._size_c) for _ in range(2 * self._size_r)]

        # Fill leaves
        for i in range(self._rows):
            for j in range(self._cols):
                self._tree[self._size_r + i][self._size_c + j] = matrix[i][j]

        # Build column trees
        for i in range(2 * self._size_r):
            for j in range(self._size_c - 1, 0, -1):
                self._tree[i][j] = self._operation(
                    self._tree[i][2 * j],
                    self._tree[i][2 * j + 1]
                )

        # Build row trees
        for i in range(self._size_r - 1, 0, -1):
            for j in range(2 * self._size_c):
                self._tree[i][j] = self._operation(
                    self._tree[2 * i][j],
                    self._tree[2 * i + 1][j]
                )

        self._lock = threading.RLock()

        logger.info(f"2D segment tree initialized ({self._rows}x{self._cols})")

    def query(
        self,
        r1: int,
        c1: int,
        r2: int,
        c2: int
    ) -> int:
        """
        Query rectangle [r1, r2) x [c1, c2).

        Args:
            r1, c1: Top-left corner
            r2, c2: Bottom-right corner (exclusive)

        Returns:
            Aggregated result
        """
        with self._lock:
            return self._query_rows(1, 0, self._size_r, r1, r2, c1, c2)

    def _query_rows(
        self,
        node: int,
        node_left: int,
        node_right: int,
        r1: int,
        r2: int,
        c1: int,
        c2: int
    ) -> int:
        if r2 <= node_left or r1 >= node_right:
            return self._identity

        if r1 <= node_left and node_right <= r2:
            return self._query_cols(node, c1, c2)

        mid = (node_left + node_right) // 2

        return self._operation(
            self._query_rows(2 * node, node_left, mid, r1, r2, c1, c2),
            self._query_rows(2 * node + 1, mid, node_right, r1, r2, c1, c2)
        )

    def _query_cols(
        self,
        row_node: int,
        c1: int,
        c2: int
    ) -> int:
        result = self._identity

        left = self._size_c + c1
        right = self._size_c + c2

        while left < right:
            if left & 1:
                result = self._operation(result, self._tree[row_node][left])
                left += 1
            if right & 1:
                right -= 1
                result = self._operation(result, self._tree[row_node][right])
            left //= 2
            right //= 2

        return result

    def update(self, row: int, col: int, value: int) -> None:
        """Update single cell."""
        with self._lock:
            # Update column in all row nodes
            pos_r = self._size_r + row
            pos_c = self._size_c + col

            self._tree[pos_r][pos_c] = value

            # Update column ancestors in this row
            c = pos_c // 2
            while c >= 1:
                self._tree[pos_r][c] = self._operation(
                    self._tree[pos_r][2 * c],
                    self._tree[pos_r][2 * c + 1]
                )
                c //= 2

            # Update row ancestors
            r = pos_r // 2
            while r >= 1:
                for c in range(2 * self._size_c):
                    self._tree[r][c] = self._operation(
                        self._tree[2 * r][c],
                        self._tree[2 * r + 1][c]
                    )
                r //= 2


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_sum_tree(data: List[int]) -> SumSegmentTree:
    """Create sum segment tree."""
    return SumSegmentTree(data)


def create_min_tree(data: List[float]) -> MinSegmentTree:
    """Create min segment tree."""
    return MinSegmentTree(data)


def create_max_tree(data: List[float]) -> MaxSegmentTree:
    """Create max segment tree."""
    return MaxSegmentTree(data)


def create_segment_tree(
    data: List[T],
    op: SegmentTreeOp = SegmentTreeOp.SUM
) -> SegmentTreeEngine:
    """
    Create segment tree with built-in operation.

    Args:
        data: Initial data
        op: Operation type

    Returns:
        SegmentTreeEngine
    """
    import math

    if op == SegmentTreeOp.SUM:
        return SegmentTreeEngine(data, lambda a, b: a + b, 0)
    elif op == SegmentTreeOp.MIN:
        return SegmentTreeEngine(data, min, float('inf'))
    elif op == SegmentTreeOp.MAX:
        return SegmentTreeEngine(data, max, float('-inf'))
    elif op == SegmentTreeOp.GCD:
        return SegmentTreeEngine(data, math.gcd, 0)
    elif op == SegmentTreeOp.PRODUCT:
        return SegmentTreeEngine(data, lambda a, b: a * b, 1)
    else:
        return SegmentTreeEngine(data, lambda a, b: a + b, 0)
