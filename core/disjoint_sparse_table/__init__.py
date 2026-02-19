"""
BAEL Disjoint Sparse Table Engine
=================================

O(1) idempotent range queries without overlap.

"Ba'el precomputes for instant answers." — Ba'el
"""

import logging
import threading
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar
from dataclasses import dataclass
import math

logger = logging.getLogger("BAEL.DisjointSparseTable")

T = TypeVar('T')


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class DSTStats:
    """Disjoint sparse table statistics."""
    size: int = 0
    levels: int = 0
    queries: int = 0


# ============================================================================
# DISJOINT SPARSE TABLE ENGINE
# ============================================================================

class DisjointSparseTableEngine(Generic[T]):
    """
    Disjoint Sparse Table for range queries.

    Unlike standard sparse table, supports ANY associative operation,
    not just idempotent ones.

    Features:
    - O(n log n) preprocessing
    - O(1) query (truly O(1), not amortized)
    - Works for non-idempotent operations (sum, product, etc.)

    "Ba'el answers all range queries in constant time." — Ba'el
    """

    def __init__(
        self,
        combine: Callable[[T, T], T],
        identity: T
    ):
        """
        Initialize disjoint sparse table.

        Args:
            combine: Associative binary operation
            identity: Identity element for combine
        """
        self._combine = combine
        self._identity = identity
        self._table: List[List[T]] = []
        self._log_table: List[int] = []
        self._size = 0
        self._levels = 0
        self._stats = DSTStats()
        self._lock = threading.RLock()

        logger.debug("Disjoint sparse table initialized")

    def build(self, array: List[T]) -> None:
        """
        Build disjoint sparse table.

        Args:
            array: Input array
        """
        with self._lock:
            n = len(array)
            self._size = n
            self._stats.size = n

            if n == 0:
                return

            # Calculate levels
            self._levels = max(1, math.ceil(math.log2(n)) + 1)
            self._stats.levels = self._levels

            # Build log table
            self._log_table = [0] * (n + 1)
            for i in range(2, n + 1):
                self._log_table[i] = self._log_table[i // 2] + 1

            # Build table
            self._table = [[self._identity] * n for _ in range(self._levels)]

            # Level 0: single elements
            for i in range(n):
                self._table[0][i] = array[i]

            # Build higher levels
            for level in range(1, self._levels):
                block_size = 1 << level

                for block_start in range(0, n, block_size):
                    mid = min(block_start + block_size // 2, n)
                    block_end = min(block_start + block_size, n)

                    # Build from mid going left
                    if mid > block_start:
                        self._table[level][mid - 1] = array[mid - 1]
                        for i in range(mid - 2, block_start - 1, -1):
                            self._table[level][i] = self._combine(
                                array[i],
                                self._table[level][i + 1]
                            )

                    # Build from mid going right
                    if mid < block_end:
                        self._table[level][mid] = array[mid]
                        for i in range(mid + 1, block_end):
                            self._table[level][i] = self._combine(
                                self._table[level][i - 1],
                                array[i]
                            )

            logger.info(f"DST built: {n} elements, {self._levels} levels")

    def query(self, left: int, right: int) -> T:
        """
        Query range [left, right] in O(1).

        Args:
            left: Left index (inclusive)
            right: Right index (inclusive)

        Returns:
            Combined result
        """
        with self._lock:
            self._stats.queries += 1

            if left > right or left < 0 or right >= self._size:
                return self._identity

            if left == right:
                return self._table[0][left]

            # Find the level where left and right are in different halves
            level = self._log_table[left ^ right] + 1

            if level >= self._levels:
                level = self._levels - 1

            # Combine left part (going right from left) and right part (going left from right)
            return self._combine(
                self._table[level][left],
                self._table[level][right]
            )

    def __len__(self) -> int:
        return self._size

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'size': self._stats.size,
            'levels': self._stats.levels,
            'queries': self._stats.queries,
            'space_complexity': f"O({self._size} * {self._levels})"
        }


# ============================================================================
# SPECIALIZED VARIANTS
# ============================================================================

class DisjointSumTable(DisjointSparseTableEngine[int]):
    """Disjoint sparse table for range sums."""

    def __init__(self):
        super().__init__(combine=lambda a, b: a + b, identity=0)


class DisjointProductTable(DisjointSparseTableEngine[int]):
    """Disjoint sparse table for range products."""

    def __init__(self):
        super().__init__(combine=lambda a, b: a * b, identity=1)


class DisjointMinTable(DisjointSparseTableEngine):
    """Disjoint sparse table for range minimum."""

    def __init__(self):
        super().__init__(
            combine=lambda a, b: min(a, b),
            identity=float('inf')
        )


class DisjointMaxTable(DisjointSparseTableEngine):
    """Disjoint sparse table for range maximum."""

    def __init__(self):
        super().__init__(
            combine=lambda a, b: max(a, b),
            identity=float('-inf')
        )


class DisjointGCDTable(DisjointSparseTableEngine[int]):
    """Disjoint sparse table for range GCD."""

    def __init__(self):
        import math
        super().__init__(combine=math.gcd, identity=0)


class DisjointXORTable(DisjointSparseTableEngine[int]):
    """Disjoint sparse table for range XOR."""

    def __init__(self):
        super().__init__(combine=lambda a, b: a ^ b, identity=0)


# ============================================================================
# MODULAR ARITHMETIC VARIANT
# ============================================================================

class ModularDisjointTable(DisjointSparseTableEngine[int]):
    """
    Disjoint sparse table with modular arithmetic.

    "Ba'el computes in modular space." — Ba'el
    """

    def __init__(self, mod: int = 10**9 + 7, operation: str = "sum"):
        """
        Initialize modular table.

        Args:
            mod: Modulus
            operation: "sum" or "product"
        """
        self._mod = mod

        if operation == "sum":
            combine = lambda a, b: (a + b) % mod
            identity = 0
        elif operation == "product":
            combine = lambda a, b: (a * b) % mod
            identity = 1
        else:
            raise ValueError(f"Unknown operation: {operation}")

        super().__init__(combine=combine, identity=identity)


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_disjoint_sparse_table(
    combine: Callable = lambda a, b: a + b,
    identity: Any = 0
) -> DisjointSparseTableEngine:
    """Create disjoint sparse table."""
    return DisjointSparseTableEngine(combine, identity)


def create_disjoint_sum_table() -> DisjointSumTable:
    """Create sum disjoint sparse table."""
    return DisjointSumTable()


def create_disjoint_min_table() -> DisjointMinTable:
    """Create min disjoint sparse table."""
    return DisjointMinTable()


def create_disjoint_max_table() -> DisjointMaxTable:
    """Create max disjoint sparse table."""
    return DisjointMaxTable()


def build_disjoint_sum_table(array: List[int]) -> DisjointSumTable:
    """Build sum table from array."""
    table = DisjointSumTable()
    table.build(array)
    return table


def build_disjoint_min_table(array: List) -> DisjointMinTable:
    """Build min table from array."""
    table = DisjointMinTable()
    table.build(array)
    return table


def range_sum_o1(array: List[int], left: int, right: int) -> int:
    """
    O(1) range sum query.

    Args:
        array: Input array
        left: Left index
        right: Right index

    Returns:
        Sum of range
    """
    table = build_disjoint_sum_table(array)
    return table.query(left, right)
