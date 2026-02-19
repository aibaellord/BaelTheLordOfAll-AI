"""
BAEL Fenwick Tree (Binary Indexed Tree) Engine
===============================================

Prefix sums with O(log n) updates.

"Ba'el computes all prefix sums with divine speed." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, Generic, List, Optional, TypeVar
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("BAEL.FenwickTree")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class FenwickTreeStats:
    """Fenwick tree statistics."""
    size: int = 0
    update_count: int = 0
    query_count: int = 0


# ============================================================================
# FENWICK TREE ENGINE
# ============================================================================

class FenwickTreeEngine:
    """
    Fenwick Tree (Binary Indexed Tree) implementation.

    Features:
    - O(log n) point updates
    - O(log n) prefix sum queries
    - O(log n) range sum queries
    - Low memory overhead

    "Ba'el indexes all bits with perfect precision." — Ba'el
    """

    def __init__(self, size: int):
        """
        Initialize Fenwick tree.

        Args:
            size: Number of elements
        """
        self._n = size
        self._tree: List[int] = [0] * (size + 1)  # 1-indexed

        self._stats = FenwickTreeStats(size=size)
        self._lock = threading.RLock()

        logger.info(f"Fenwick tree initialized (size={size})")

    @classmethod
    def from_list(cls, data: List[int]) -> 'FenwickTreeEngine':
        """
        Create Fenwick tree from list.

        Args:
            data: Initial data

        Returns:
            FenwickTreeEngine
        """
        tree = cls(len(data))

        for i, value in enumerate(data):
            tree.update(i, value)

        return tree

    # ========================================================================
    # BASIC OPERATIONS
    # ========================================================================

    def update(self, index: int, delta: int) -> None:
        """
        Add delta to element at index.

        Args:
            index: Index (0-based)
            delta: Value to add
        """
        if index < 0 or index >= self._n:
            raise IndexError(f"Index {index} out of range [0, {self._n})")

        with self._lock:
            self._stats.update_count += 1

            # Convert to 1-indexed
            i = index + 1

            while i <= self._n:
                self._tree[i] += delta
                i += i & (-i)  # Add lowest set bit

    def set(self, index: int, value: int) -> None:
        """
        Set element at index to value.

        Args:
            index: Index (0-based)
            value: New value
        """
        current = self.get(index)
        self.update(index, value - current)

    def get(self, index: int) -> int:
        """
        Get element at index.

        Args:
            index: Index (0-based)

        Returns:
            Element value
        """
        if index == 0:
            return self.prefix_sum(1)
        return self.range_sum(index, index + 1)

    # ========================================================================
    # QUERIES
    # ========================================================================

    def prefix_sum(self, end: int) -> int:
        """
        Get sum of elements [0, end).

        Args:
            end: End index (exclusive)

        Returns:
            Sum
        """
        if end <= 0:
            return 0
        if end > self._n:
            end = self._n

        with self._lock:
            self._stats.query_count += 1

            result = 0
            i = end  # Already 1-indexed due to exclusive end

            while i > 0:
                result += self._tree[i]
                i -= i & (-i)  # Remove lowest set bit

            return result

    def range_sum(self, start: int, end: int) -> int:
        """
        Get sum of elements [start, end).

        Args:
            start: Start index (inclusive)
            end: End index (exclusive)

        Returns:
            Sum
        """
        if start >= end:
            return 0

        return self.prefix_sum(end) - self.prefix_sum(start)

    def total_sum(self) -> int:
        """Get sum of all elements."""
        return self.prefix_sum(self._n)

    # ========================================================================
    # ADVANCED OPERATIONS
    # ========================================================================

    def lower_bound(self, target_sum: int) -> int:
        """
        Find smallest index where prefix sum >= target.

        Args:
            target_sum: Target sum

        Returns:
            Index (0-based), or -1 if not found
        """
        if target_sum <= 0:
            return 0

        with self._lock:
            pos = 0
            current_sum = 0

            # Find highest bit
            bit = 1
            while bit * 2 <= self._n:
                bit *= 2

            while bit > 0:
                if pos + bit <= self._n and current_sum + self._tree[pos + bit] < target_sum:
                    pos += bit
                    current_sum += self._tree[pos]
                bit //= 2

            if pos >= self._n:
                return -1

            return pos  # Convert to 0-based

    def kth_element(self, k: int) -> int:
        """
        Find k-th element in sorted order (if tree represents frequencies).

        Args:
            k: 1-based rank

        Returns:
            Index of k-th element, or -1 if not found
        """
        return self.lower_bound(k)

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def __len__(self) -> int:
        return self._n

    def __getitem__(self, index: int) -> int:
        return self.get(index)

    def __setitem__(self, index: int, value: int) -> None:
        self.set(index, value)

    def to_list(self) -> List[int]:
        """Convert to list."""
        result = []
        for i in range(self._n):
            result.append(self.get(i))
        return result

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'size': self._stats.size,
            'update_count': self._stats.update_count,
            'query_count': self._stats.query_count
        }


# ============================================================================
# 2D FENWICK TREE
# ============================================================================

class FenwickTree2D:
    """
    2D Fenwick Tree for rectangle sum queries.

    "Ba'el indexes all dimensions with equal precision." — Ba'el
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

        logger.info(f"2D Fenwick tree initialized ({rows}x{cols})")

    @classmethod
    def from_matrix(cls, matrix: List[List[int]]) -> 'FenwickTree2D':
        """Create from matrix."""
        if not matrix or not matrix[0]:
            return cls(0, 0)

        rows = len(matrix)
        cols = len(matrix[0])

        tree = cls(rows, cols)

        for i in range(rows):
            for j in range(cols):
                tree.update(i, j, matrix[i][j])

        return tree

    def update(self, row: int, col: int, delta: int) -> None:
        """
        Add delta to element at (row, col).

        Args:
            row: Row index (0-based)
            col: Column index (0-based)
            delta: Value to add
        """
        with self._lock:
            i = row + 1
            while i <= self._rows:
                j = col + 1
                while j <= self._cols:
                    self._tree[i][j] += delta
                    j += j & (-j)
                i += i & (-i)

    def prefix_sum(self, row: int, col: int) -> int:
        """
        Get sum of rectangle [0, row) x [0, col).

        Args:
            row: End row (exclusive)
            col: End column (exclusive)

        Returns:
            Sum
        """
        if row <= 0 or col <= 0:
            return 0

        with self._lock:
            result = 0
            i = min(row, self._rows)

            while i > 0:
                j = min(col, self._cols)
                while j > 0:
                    result += self._tree[i][j]
                    j -= j & (-j)
                i -= i & (-i)

            return result

    def range_sum(
        self,
        r1: int,
        c1: int,
        r2: int,
        c2: int
    ) -> int:
        """
        Get sum of rectangle [r1, r2) x [c1, c2).

        Args:
            r1, c1: Top-left corner
            r2, c2: Bottom-right corner (exclusive)

        Returns:
            Sum
        """
        if r1 >= r2 or c1 >= c2:
            return 0

        return (self.prefix_sum(r2, c2)
                - self.prefix_sum(r1, c2)
                - self.prefix_sum(r2, c1)
                + self.prefix_sum(r1, c1))


# ============================================================================
# RANGE UPDATE FENWICK TREE
# ============================================================================

class RangeUpdateFenwickTree:
    """
    Fenwick Tree with range updates and point queries.

    Uses difference array technique.

    "Ba'el updates ranges with singular efficiency." — Ba'el
    """

    def __init__(self, size: int):
        """
        Initialize range update Fenwick tree.

        Args:
            size: Number of elements
        """
        self._n = size
        self._tree = FenwickTreeEngine(size)

        logger.info(f"Range update Fenwick tree initialized (size={size})")

    def update_range(self, start: int, end: int, delta: int) -> None:
        """
        Add delta to all elements in [start, end).

        Args:
            start: Start index (inclusive)
            end: End index (exclusive)
            delta: Value to add
        """
        self._tree.update(start, delta)
        if end < self._n:
            self._tree.update(end, -delta)

    def get(self, index: int) -> int:
        """
        Get element at index.

        Args:
            index: Index (0-based)

        Returns:
            Element value
        """
        return self._tree.prefix_sum(index + 1)


# ============================================================================
# RANGE UPDATE RANGE QUERY FENWICK TREE
# ============================================================================

class RURQFenwickTree:
    """
    Fenwick Tree with range updates AND range queries.

    Uses two BITs: one for values, one for weighted values.

    "Ba'el masters all range operations." — Ba'el
    """

    def __init__(self, size: int):
        """
        Initialize RURQ Fenwick tree.

        Args:
            size: Number of elements
        """
        self._n = size
        self._bit1 = [0] * (size + 1)  # Coefficients for i
        self._bit2 = [0] * (size + 1)  # Constant terms

        self._lock = threading.RLock()

        logger.info(f"RURQ Fenwick tree initialized (size={size})")

    def _update_bit(self, bit: List[int], index: int, delta: int) -> None:
        """Update a BIT."""
        i = index + 1
        while i <= self._n:
            bit[i] += delta
            i += i & (-i)

    def _query_bit(self, bit: List[int], index: int) -> int:
        """Query a BIT."""
        result = 0
        i = index
        while i > 0:
            result += bit[i]
            i -= i & (-i)
        return result

    def update_range(self, start: int, end: int, delta: int) -> None:
        """
        Add delta to all elements in [start, end).

        Args:
            start: Start index (inclusive)
            end: End index (exclusive)
            delta: Value to add
        """
        with self._lock:
            # Update BIT1
            self._update_bit(self._bit1, start, delta)
            self._update_bit(self._bit1, end, -delta)

            # Update BIT2
            self._update_bit(self._bit2, start, delta * (start - 1))
            self._update_bit(self._bit2, end, -delta * (end - 1))

    def prefix_sum(self, end: int) -> int:
        """
        Get sum of elements [0, end).

        Args:
            end: End index (exclusive)

        Returns:
            Sum
        """
        if end <= 0:
            return 0

        with self._lock:
            return (self._query_bit(self._bit1, end) * (end - 1)
                    - self._query_bit(self._bit2, end))

    def range_sum(self, start: int, end: int) -> int:
        """
        Get sum of elements [start, end).

        Args:
            start: Start index (inclusive)
            end: End index (exclusive)

        Returns:
            Sum
        """
        return self.prefix_sum(end) - self.prefix_sum(start)


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_fenwick_tree(size: int) -> FenwickTreeEngine:
    """Create a new Fenwick tree."""
    return FenwickTreeEngine(size)


def from_list(data: List[int]) -> FenwickTreeEngine:
    """Create Fenwick tree from list."""
    return FenwickTreeEngine.from_list(data)


def create_2d_fenwick_tree(rows: int, cols: int) -> FenwickTree2D:
    """Create 2D Fenwick tree."""
    return FenwickTree2D(rows, cols)


def create_range_update_tree(size: int) -> RangeUpdateFenwickTree:
    """Create range update Fenwick tree."""
    return RangeUpdateFenwickTree(size)


def create_rurq_tree(size: int) -> RURQFenwickTree:
    """Create range update range query Fenwick tree."""
    return RURQFenwickTree(size)
