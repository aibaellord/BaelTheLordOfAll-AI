"""
BAEL Sparse Table Engine Implementation
========================================

O(1) range queries with O(n log n) preprocessing.

"Ba'el answers all range queries instantaneously." — Ba'el
"""

import logging
import math
import threading
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("BAEL.SparseTable")

T = TypeVar('T')


# ============================================================================
# DATA STRUCTURES
# ============================================================================

class SparseTableOp(Enum):
    """Built-in sparse table operations."""
    MIN = "min"
    MAX = "max"
    GCD = "gcd"
    AND = "and"
    OR = "or"


@dataclass
class SparseTableStats:
    """Sparse table statistics."""
    size: int = 0
    levels: int = 0
    queries: int = 0


# ============================================================================
# SPARSE TABLE ENGINE
# ============================================================================

class SparseTableEngine(Generic[T]):
    """
    Sparse Table for O(1) range queries.

    Features:
    - O(n log n) preprocessing
    - O(1) idempotent queries (min, max, gcd)
    - O(log n) non-idempotent queries (sum)

    "Ba'el precomputes all possible range answers." — Ba'el
    """

    def __init__(
        self,
        data: List[T],
        operation: Callable[[T, T], T],
        is_idempotent: bool = True
    ):
        """
        Initialize sparse table.

        Args:
            data: Input data
            operation: Associative operation (must be idempotent for O(1) queries)
            is_idempotent: Whether operation is idempotent (f(a,a) = a)
        """
        self._n = len(data)
        self._data = data.copy()
        self._operation = operation
        self._is_idempotent = is_idempotent

        # Compute number of levels
        self._k = max(1, int(math.log2(self._n)) + 1) if self._n > 0 else 0

        # Precompute log values
        self._log = [0] * (self._n + 1)
        for i in range(2, self._n + 1):
            self._log[i] = self._log[i // 2] + 1

        # Build sparse table
        self._table: List[List[T]] = []
        self._build()

        self._stats = SparseTableStats(size=self._n, levels=self._k)
        self._lock = threading.RLock()

        logger.info(f"Sparse table initialized (n={self._n}, levels={self._k})")

    def _build(self) -> None:
        """Build sparse table."""
        if self._n == 0:
            return

        # Initialize table
        self._table = [[None] * self._n for _ in range(self._k)]

        # Level 0: intervals of length 1
        for i in range(self._n):
            self._table[0][i] = self._data[i]

        # Build higher levels
        for j in range(1, self._k):
            length = 1 << j

            for i in range(self._n - length + 1):
                self._table[j][i] = self._operation(
                    self._table[j - 1][i],
                    self._table[j - 1][i + (length >> 1)]
                )

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
            raise ValueError(f"Invalid range [{left}, {right})")

        with self._lock:
            self._stats.queries += 1

        length = right - left

        if self._is_idempotent:
            # O(1) query for idempotent operations
            k = self._log[length]
            return self._operation(
                self._table[k][left],
                self._table[k][right - (1 << k)]
            )
        else:
            # O(log n) query for non-idempotent operations
            result = None

            for j in range(self._k - 1, -1, -1):
                if (1 << j) <= length:
                    if result is None:
                        result = self._table[j][left]
                    else:
                        result = self._operation(result, self._table[j][left])

                    left += (1 << j)
                    length -= (1 << j)

            return result

    def __len__(self) -> int:
        return self._n

    def __getitem__(self, index: int) -> T:
        return self._data[index]

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'size': self._stats.size,
            'levels': self._stats.levels,
            'queries': self._stats.queries
        }


# ============================================================================
# SPECIALIZED SPARSE TABLES
# ============================================================================

class MinSparseTable(SparseTableEngine[float]):
    """Sparse table for range minimum queries."""

    def __init__(self, data: List[float]):
        super().__init__(data, min, is_idempotent=True)


class MaxSparseTable(SparseTableEngine[float]):
    """Sparse table for range maximum queries."""

    def __init__(self, data: List[float]):
        super().__init__(data, max, is_idempotent=True)


class GCDSparseTable(SparseTableEngine[int]):
    """Sparse table for range GCD queries."""

    def __init__(self, data: List[int]):
        import math
        super().__init__(data, math.gcd, is_idempotent=True)


# ============================================================================
# DISJOINT SPARSE TABLE
# ============================================================================

class DisjointSparseTable(Generic[T]):
    """
    Disjoint Sparse Table for any associative operation.

    Features:
    - O(n log n) preprocessing
    - O(1) queries for ANY associative operation
    - No idempotency requirement

    "Ba'el separates ranges for perfect answers." — Ba'el
    """

    def __init__(
        self,
        data: List[T],
        operation: Callable[[T, T], T],
        identity: T
    ):
        """
        Initialize disjoint sparse table.

        Args:
            data: Input data
            operation: Associative operation
            identity: Identity element
        """
        self._n = len(data)
        self._data = data.copy()
        self._operation = operation
        self._identity = identity

        # Round up to power of 2
        self._size = 1
        while self._size < self._n:
            self._size *= 2

        # Pad data
        self._padded = data + [identity] * (self._size - self._n)

        # Compute number of levels
        self._k = int(math.log2(self._size)) + 1 if self._size > 0 else 0

        # Build table
        self._table: List[List[T]] = []
        self._build()

        self._lock = threading.RLock()

        logger.info(f"Disjoint sparse table initialized (n={self._n}, levels={self._k})")

    def _build(self) -> None:
        """Build disjoint sparse table."""
        if self._size == 0:
            return

        self._table = [[self._identity] * self._size for _ in range(self._k)]

        for level in range(self._k):
            block_size = 1 << level

            for block_start in range(0, self._size, block_size * 2):
                mid = block_start + block_size

                # Build left half (prefix from mid going left)
                if mid > 0 and mid <= self._size:
                    self._table[level][mid - 1] = self._padded[mid - 1]

                    for i in range(mid - 2, block_start - 1, -1):
                        self._table[level][i] = self._operation(
                            self._padded[i],
                            self._table[level][i + 1]
                        )

                # Build right half (prefix from mid going right)
                if mid < self._size:
                    self._table[level][mid] = self._padded[mid]

                    for i in range(mid + 1, min(block_start + 2 * block_size, self._size)):
                        self._table[level][i] = self._operation(
                            self._table[level][i - 1],
                            self._padded[i]
                        )

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
            return self._identity

        right -= 1  # Convert to inclusive

        if left == right:
            return self._padded[left]

        # Find level where left and right are in different halves
        level = (left ^ right).bit_length() - 1

        return self._operation(
            self._table[level][left],
            self._table[level][right]
        )

    def __len__(self) -> int:
        return self._n


# ============================================================================
# 2D SPARSE TABLE
# ============================================================================

class SparseTable2D(Generic[T]):
    """
    2D Sparse Table for rectangle queries.

    "Ba'el queries all rectangles of reality." — Ba'el
    """

    def __init__(
        self,
        matrix: List[List[T]],
        operation: Callable[[T, T], T]
    ):
        """
        Initialize 2D sparse table.

        Args:
            matrix: 2D input data
            operation: Associative, idempotent operation
        """
        if not matrix or not matrix[0]:
            self._rows = 0
            self._cols = 0
            self._table = []
            return

        self._rows = len(matrix)
        self._cols = len(matrix[0])
        self._operation = operation

        # Compute log values
        self._log_r = int(math.log2(self._rows)) + 1 if self._rows > 0 else 0
        self._log_c = int(math.log2(self._cols)) + 1 if self._cols > 0 else 0

        # Precompute log table
        self._log = [0] * (max(self._rows, self._cols) + 1)
        for i in range(2, len(self._log)):
            self._log[i] = self._log[i // 2] + 1

        # Build 4D table
        self._build(matrix)

        logger.info(f"2D sparse table initialized ({self._rows}x{self._cols})")

    def _build(self, matrix: List[List[T]]) -> None:
        """Build 2D sparse table."""
        # table[jr][jc][i][k] = answer for rectangle starting at (i,k) with size 2^jr x 2^jc
        self._table = [
            [
                [[None] * self._cols for _ in range(self._rows)]
                for _ in range(self._log_c)
            ]
            for _ in range(self._log_r)
        ]

        # Initialize level (0,0)
        for i in range(self._rows):
            for k in range(self._cols):
                self._table[0][0][i][k] = matrix[i][k]

        # Build column-wise
        for jr in range(self._log_r):
            for jc in range(self._log_c):
                if jr == 0 and jc == 0:
                    continue

                len_r = 1 << jr
                len_c = 1 << jc

                for i in range(self._rows - len_r + 1):
                    for k in range(self._cols - len_c + 1):
                        if jc > 0:
                            self._table[jr][jc][i][k] = self._operation(
                                self._table[jr][jc - 1][i][k],
                                self._table[jr][jc - 1][i][k + (len_c >> 1)]
                            )
                        else:
                            self._table[jr][jc][i][k] = self._operation(
                                self._table[jr - 1][jc][i][k],
                                self._table[jr - 1][jc][i + (len_r >> 1)][k]
                            )

    def query(
        self,
        r1: int,
        c1: int,
        r2: int,
        c2: int
    ) -> T:
        """
        Query rectangle [r1, r2) x [c1, c2).

        Args:
            r1, c1: Top-left corner
            r2, c2: Bottom-right corner (exclusive)

        Returns:
            Aggregated result
        """
        r2 -= 1
        c2 -= 1

        kr = self._log[r2 - r1 + 1]
        kc = self._log[c2 - c1 + 1]

        len_r = 1 << kr
        len_c = 1 << kc

        return self._operation(
            self._operation(
                self._table[kr][kc][r1][c1],
                self._table[kr][kc][r1][c2 - len_c + 1]
            ),
            self._operation(
                self._table[kr][kc][r2 - len_r + 1][c1],
                self._table[kr][kc][r2 - len_r + 1][c2 - len_c + 1]
            )
        )


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_min_sparse_table(data: List[float]) -> MinSparseTable:
    """Create sparse table for RMQ."""
    return MinSparseTable(data)


def create_max_sparse_table(data: List[float]) -> MaxSparseTable:
    """Create sparse table for range max."""
    return MaxSparseTable(data)


def create_gcd_sparse_table(data: List[int]) -> GCDSparseTable:
    """Create sparse table for range GCD."""
    return GCDSparseTable(data)


def create_sparse_table(
    data: List[T],
    op: SparseTableOp = SparseTableOp.MIN
) -> SparseTableEngine:
    """
    Create sparse table with built-in operation.

    Args:
        data: Input data
        op: Operation type

    Returns:
        SparseTableEngine
    """
    import math

    if op == SparseTableOp.MIN:
        return SparseTableEngine(data, min, is_idempotent=True)
    elif op == SparseTableOp.MAX:
        return SparseTableEngine(data, max, is_idempotent=True)
    elif op == SparseTableOp.GCD:
        return SparseTableEngine(data, math.gcd, is_idempotent=True)
    elif op == SparseTableOp.AND:
        return SparseTableEngine(data, lambda a, b: a & b, is_idempotent=True)
    elif op == SparseTableOp.OR:
        return SparseTableEngine(data, lambda a, b: a | b, is_idempotent=True)
    else:
        return SparseTableEngine(data, min, is_idempotent=True)


def create_disjoint_sparse_table(
    data: List[T],
    operation: Callable[[T, T], T],
    identity: T
) -> DisjointSparseTable[T]:
    """Create disjoint sparse table."""
    return DisjointSparseTable(data, operation, identity)
