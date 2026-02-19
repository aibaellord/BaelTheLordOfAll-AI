"""
BAEL 2D Segment Tree Engine
===========================

Range queries and updates on 2D matrices.

"Ba'el conquers two dimensions." — Ba'el
"""

import logging
import threading
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar
from dataclasses import dataclass

logger = logging.getLogger("BAEL.SegmentTree2D")

T = TypeVar('T')


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ST2DStats:
    """2D segment tree statistics."""
    rows: int = 0
    cols: int = 0
    point_updates: int = 0
    range_queries: int = 0


# ============================================================================
# 2D SEGMENT TREE ENGINE
# ============================================================================

class SegmentTree2DEngine(Generic[T]):
    """
    2D Segment Tree for matrix range queries.

    Features:
    - O(log n * log m) point update
    - O(log n * log m) range query
    - Supports any associative operation

    "Ba'el indexes the plane logarithmically." — Ba'el
    """

    def __init__(
        self,
        combine: Callable[[T, T], T],
        identity: T
    ):
        """
        Initialize 2D segment tree.

        Args:
            combine: Associative binary operation
            identity: Identity element
        """
        self._combine = combine
        self._identity = identity
        self._tree: List[List[T]] = []
        self._rows = 0
        self._cols = 0
        self._stats = ST2DStats()
        self._lock = threading.RLock()

        logger.debug("2D segment tree initialized")

    def build(self, matrix: List[List[T]]) -> None:
        """
        Build 2D segment tree from matrix.

        Args:
            matrix: 2D matrix
        """
        with self._lock:
            if not matrix or not matrix[0]:
                return

            self._rows = len(matrix)
            self._cols = len(matrix[0])
            self._stats.rows = self._rows
            self._stats.cols = self._cols

            # Allocate tree: 4*rows x 4*cols
            tree_rows = 4 * self._rows
            tree_cols = 4 * self._cols
            self._tree = [[self._identity] * tree_cols for _ in range(tree_rows)]

            # Build tree
            self._build_x(matrix, 1, 0, self._rows - 1)

            logger.info(f"2D ST built: {self._rows}x{self._cols}")

    def _build_x(
        self,
        matrix: List[List[T]],
        vx: int,
        tlx: int,
        trx: int
    ) -> None:
        """Build along X dimension."""
        if tlx == trx:
            self._build_y(matrix[tlx], vx, 1, 0, self._cols - 1)
        else:
            mid = (tlx + trx) // 2
            self._build_x(matrix, 2 * vx, tlx, mid)
            self._build_x(matrix, 2 * vx + 1, mid + 1, trx)

            # Merge
            for vy in range(4 * self._cols):
                self._tree[vx][vy] = self._combine(
                    self._tree[2 * vx][vy],
                    self._tree[2 * vx + 1][vy]
                )

    def _build_y(
        self,
        row: List[T],
        vx: int,
        vy: int,
        tly: int,
        try_: int
    ) -> None:
        """Build along Y dimension for a single row."""
        if tly == try_:
            self._tree[vx][vy] = row[tly]
        else:
            mid = (tly + try_) // 2
            self._build_y(row, vx, 2 * vy, tly, mid)
            self._build_y(row, vx, 2 * vy + 1, mid + 1, try_)
            self._tree[vx][vy] = self._combine(
                self._tree[vx][2 * vy],
                self._tree[vx][2 * vy + 1]
            )

    def update(self, x: int, y: int, value: T) -> None:
        """
        Update value at position (x, y).

        Args:
            x: Row index
            y: Column index
            value: New value
        """
        with self._lock:
            self._stats.point_updates += 1
            self._update_x(1, 0, self._rows - 1, x, y, value)

    def _update_x(
        self,
        vx: int,
        tlx: int,
        trx: int,
        x: int,
        y: int,
        value: T
    ) -> None:
        """Update along X dimension."""
        if tlx == trx:
            self._update_y(vx, 1, 0, self._cols - 1, y, value)
        else:
            mid = (tlx + trx) // 2
            if x <= mid:
                self._update_x(2 * vx, tlx, mid, x, y, value)
            else:
                self._update_x(2 * vx + 1, mid + 1, trx, x, y, value)

            # Merge Y trees
            self._merge_y(vx, 2 * vx, 2 * vx + 1, 1, 0, self._cols - 1, y)

    def _update_y(
        self,
        vx: int,
        vy: int,
        tly: int,
        try_: int,
        y: int,
        value: T
    ) -> None:
        """Update along Y dimension."""
        if tly == try_:
            self._tree[vx][vy] = value
        else:
            mid = (tly + try_) // 2
            if y <= mid:
                self._update_y(vx, 2 * vy, tly, mid, y, value)
            else:
                self._update_y(vx, 2 * vy + 1, mid + 1, try_, y, value)

            self._tree[vx][vy] = self._combine(
                self._tree[vx][2 * vy],
                self._tree[vx][2 * vy + 1]
            )

    def _merge_y(
        self,
        vx: int,
        vx1: int,
        vx2: int,
        vy: int,
        tly: int,
        try_: int,
        y: int
    ) -> None:
        """Merge two Y trees."""
        if tly == try_:
            self._tree[vx][vy] = self._combine(
                self._tree[vx1][vy],
                self._tree[vx2][vy]
            )
        else:
            mid = (tly + try_) // 2
            if y <= mid:
                self._merge_y(vx, vx1, vx2, 2 * vy, tly, mid, y)
            else:
                self._merge_y(vx, vx1, vx2, 2 * vy + 1, mid + 1, try_, y)

            self._tree[vx][vy] = self._combine(
                self._tree[vx][2 * vy],
                self._tree[vx][2 * vy + 1]
            )

    def query(self, x1: int, y1: int, x2: int, y2: int) -> T:
        """
        Query range [x1, x2] x [y1, y2].

        Args:
            x1: Top row
            y1: Left column
            x2: Bottom row
            y2: Right column

        Returns:
            Combined result
        """
        with self._lock:
            self._stats.range_queries += 1
            return self._query_x(1, 0, self._rows - 1, x1, x2, y1, y2)

    def _query_x(
        self,
        vx: int,
        tlx: int,
        trx: int,
        x1: int,
        x2: int,
        y1: int,
        y2: int
    ) -> T:
        """Query along X dimension."""
        if x1 > trx or x2 < tlx:
            return self._identity

        if x1 <= tlx and trx <= x2:
            return self._query_y(vx, 1, 0, self._cols - 1, y1, y2)

        mid = (tlx + trx) // 2
        left = self._query_x(2 * vx, tlx, mid, x1, x2, y1, y2)
        right = self._query_x(2 * vx + 1, mid + 1, trx, x1, x2, y1, y2)

        return self._combine(left, right)

    def _query_y(
        self,
        vx: int,
        vy: int,
        tly: int,
        try_: int,
        y1: int,
        y2: int
    ) -> T:
        """Query along Y dimension."""
        if y1 > try_ or y2 < tly:
            return self._identity

        if y1 <= tly and try_ <= y2:
            return self._tree[vx][vy]

        mid = (tly + try_) // 2
        left = self._query_y(vx, 2 * vy, tly, mid, y1, y2)
        right = self._query_y(vx, 2 * vy + 1, mid + 1, try_, y1, y2)

        return self._combine(left, right)

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'rows': self._stats.rows,
            'cols': self._stats.cols,
            'point_updates': self._stats.point_updates,
            'range_queries': self._stats.range_queries
        }


# ============================================================================
# SPECIALIZED VARIANTS
# ============================================================================

class SumSegmentTree2D(SegmentTree2DEngine[int]):
    """2D segment tree for range sums."""

    def __init__(self):
        super().__init__(combine=lambda a, b: a + b, identity=0)


class MinSegmentTree2D(SegmentTree2DEngine):
    """2D segment tree for range minimum."""

    def __init__(self):
        super().__init__(
            combine=lambda a, b: min(a, b),
            identity=float('inf')
        )


class MaxSegmentTree2D(SegmentTree2DEngine):
    """2D segment tree for range maximum."""

    def __init__(self):
        super().__init__(
            combine=lambda a, b: max(a, b),
            identity=float('-inf')
        )


class GCDSegmentTree2D(SegmentTree2DEngine[int]):
    """2D segment tree for range GCD."""

    def __init__(self):
        import math
        super().__init__(combine=math.gcd, identity=0)


# ============================================================================
# 2D FENWICK TREE (BIT)
# ============================================================================

class FenwickTree2D:
    """
    2D Fenwick Tree (Binary Indexed Tree).

    Features:
    - O(log n * log m) point update
    - O(log n * log m) prefix sum
    - O(log n * log m) range sum

    "Ba'el sums the plane with binary magic." — Ba'el
    """

    def __init__(self, rows: int, cols: int):
        """
        Initialize 2D Fenwick tree.

        Args:
            rows: Number of rows
            cols: Number of columns
        """
        self._rows = rows
        self._cols = cols
        self._tree = [[0] * (cols + 1) for _ in range(rows + 1)]
        self._lock = threading.RLock()

    def update(self, x: int, y: int, delta: int) -> None:
        """
        Add delta to position (x, y).

        Args:
            x: Row (0-indexed)
            y: Column (0-indexed)
            delta: Value to add
        """
        with self._lock:
            i = x + 1
            while i <= self._rows:
                j = y + 1
                while j <= self._cols:
                    self._tree[i][j] += delta
                    j += j & (-j)
                i += i & (-i)

    def prefix_sum(self, x: int, y: int) -> int:
        """
        Get sum of rectangle [0, x] x [0, y].

        Args:
            x: Row (0-indexed)
            y: Column (0-indexed)

        Returns:
            Prefix sum
        """
        with self._lock:
            result = 0
            i = x + 1
            while i > 0:
                j = y + 1
                while j > 0:
                    result += self._tree[i][j]
                    j -= j & (-j)
                i -= i & (-i)
            return result

    def range_sum(self, x1: int, y1: int, x2: int, y2: int) -> int:
        """
        Get sum of rectangle [x1, x2] x [y1, y2].

        Args:
            x1: Top row
            y1: Left column
            x2: Bottom row
            y2: Right column

        Returns:
            Range sum
        """
        result = self.prefix_sum(x2, y2)

        if x1 > 0:
            result -= self.prefix_sum(x1 - 1, y2)
        if y1 > 0:
            result -= self.prefix_sum(x2, y1 - 1)
        if x1 > 0 and y1 > 0:
            result += self.prefix_sum(x1 - 1, y1 - 1)

        return result


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_segment_tree_2d(
    combine: Callable = lambda a, b: a + b,
    identity: Any = 0
) -> SegmentTree2DEngine:
    """Create 2D segment tree."""
    return SegmentTree2DEngine(combine, identity)


def create_sum_segment_tree_2d() -> SumSegmentTree2D:
    """Create 2D sum segment tree."""
    return SumSegmentTree2D()


def create_min_segment_tree_2d() -> MinSegmentTree2D:
    """Create 2D min segment tree."""
    return MinSegmentTree2D()


def create_max_segment_tree_2d() -> MaxSegmentTree2D:
    """Create 2D max segment tree."""
    return MaxSegmentTree2D()


def create_fenwick_tree_2d(rows: int, cols: int) -> FenwickTree2D:
    """Create 2D Fenwick tree."""
    return FenwickTree2D(rows, cols)


def build_sum_matrix(matrix: List[List[int]]) -> SumSegmentTree2D:
    """Build 2D sum segment tree from matrix."""
    tree = SumSegmentTree2D()
    tree.build(matrix)
    return tree
