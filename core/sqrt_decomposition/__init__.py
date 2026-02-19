"""
BAEL Square Root Decomposition Engine
=====================================

Block-based range query optimization.

"Ba'el divides the world into sqrt(n) pieces." — Ba'el
"""

import logging
import math
import threading
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar
from dataclasses import dataclass, field

logger = logging.getLogger("BAEL.SqrtDecomposition")

T = TypeVar('T')


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class SqrtStats:
    """Square Root Decomposition statistics."""
    array_size: int = 0
    block_size: int = 0
    block_count: int = 0
    queries: int = 0
    updates: int = 0


# ============================================================================
# SQUARE ROOT DECOMPOSITION ENGINE
# ============================================================================

class SqrtDecompositionEngine(Generic[T]):
    """
    Square Root Decomposition for range queries.

    Features:
    - O(sqrt(n)) query and update
    - Works for various operations
    - Range sum, min, max, GCD, etc.
    - Lazy propagation support

    "Ba'el balances query and update in sqrt harmony." — Ba'el
    """

    def __init__(
        self,
        combine: Callable[[T, T], T],
        identity: T
    ):
        """
        Initialize square root decomposition.

        Args:
            combine: Function to combine two values
            identity: Identity element for combine
        """
        self._combine = combine
        self._identity = identity
        self._array: List[T] = []
        self._blocks: List[T] = []
        self._block_size = 1
        self._stats = SqrtStats()
        self._lock = threading.RLock()

        logger.debug("Sqrt decomposition initialized")

    def build(self, array: List[T]) -> None:
        """
        Build from array.

        Args:
            array: Input array
        """
        with self._lock:
            n = len(array)
            self._array = list(array)
            self._block_size = max(1, int(math.sqrt(n)))

            self._stats.array_size = n
            self._stats.block_size = self._block_size

            # Build blocks
            block_count = (n + self._block_size - 1) // self._block_size
            self._blocks = [self._identity] * block_count
            self._stats.block_count = block_count

            for i in range(n):
                block = i // self._block_size
                self._blocks[block] = self._combine(
                    self._blocks[block],
                    array[i]
                )

            logger.debug(f"Built {block_count} blocks of size {self._block_size}")

    def query(self, left: int, right: int) -> T:
        """
        Query range [left, right].

        Args:
            left: Left endpoint (inclusive)
            right: Right endpoint (inclusive)

        Returns:
            Combined value
        """
        with self._lock:
            self._stats.queries += 1

            result = self._identity

            left_block = left // self._block_size
            right_block = right // self._block_size

            if left_block == right_block:
                # Same block - iterate through elements
                for i in range(left, right + 1):
                    result = self._combine(result, self._array[i])
            else:
                # Left partial block
                left_block_end = (left_block + 1) * self._block_size - 1
                for i in range(left, min(left_block_end + 1, len(self._array))):
                    result = self._combine(result, self._array[i])

                # Complete blocks
                for block in range(left_block + 1, right_block):
                    result = self._combine(result, self._blocks[block])

                # Right partial block
                right_block_start = right_block * self._block_size
                for i in range(right_block_start, right + 1):
                    result = self._combine(result, self._array[i])

            return result

    def update(self, index: int, value: T) -> None:
        """
        Update single element.

        Args:
            index: Index to update
            value: New value
        """
        with self._lock:
            self._stats.updates += 1

            block = index // self._block_size
            self._array[index] = value

            # Rebuild block
            block_start = block * self._block_size
            block_end = min(block_start + self._block_size, len(self._array))

            self._blocks[block] = self._identity
            for i in range(block_start, block_end):
                self._blocks[block] = self._combine(
                    self._blocks[block],
                    self._array[i]
                )

    def get(self, index: int) -> T:
        """Get element at index."""
        return self._array[index]

    def __getitem__(self, index: int) -> T:
        return self.get(index)

    def __len__(self) -> int:
        return len(self._array)

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'array_size': self._stats.array_size,
            'block_size': self._stats.block_size,
            'block_count': self._stats.block_count,
            'queries': self._stats.queries,
            'updates': self._stats.updates
        }


# ============================================================================
# SPECIALIZED VARIANTS
# ============================================================================

class SumSqrt(SqrtDecompositionEngine[int]):
    """Square root decomposition for range sums."""

    def __init__(self):
        super().__init__(combine=lambda a, b: a + b, identity=0)


class MinSqrt(SqrtDecompositionEngine):
    """Square root decomposition for range minimum."""

    def __init__(self):
        super().__init__(
            combine=lambda a, b: min(a, b) if a is not None and b is not None
                                 else a if b is None else b,
            identity=float('inf')
        )


class MaxSqrt(SqrtDecompositionEngine):
    """Square root decomposition for range maximum."""

    def __init__(self):
        super().__init__(
            combine=lambda a, b: max(a, b) if a is not None and b is not None
                                 else a if b is None else b,
            identity=float('-inf')
        )


class GCDSqrt(SqrtDecompositionEngine[int]):
    """Square root decomposition for range GCD."""

    def __init__(self):
        import math
        super().__init__(combine=math.gcd, identity=0)


# ============================================================================
# RANGE UPDATE VARIANT
# ============================================================================

class RangeUpdateSqrt:
    """
    Square root decomposition with range updates.

    Supports:
    - Range add
    - Point query

    "Ba'el updates ranges with lazy precision." — Ba'el
    """

    def __init__(self):
        """Initialize range update sqrt decomposition."""
        self._array: List[int] = []
        self._block_add: List[int] = []  # Lazy add for each block
        self._block_size = 1
        self._stats = SqrtStats()
        self._lock = threading.RLock()

    def build(self, array: List[int]) -> None:
        """Build from array."""
        with self._lock:
            n = len(array)
            self._array = list(array)
            self._block_size = max(1, int(math.sqrt(n)))

            block_count = (n + self._block_size - 1) // self._block_size
            self._block_add = [0] * block_count

            self._stats.array_size = n
            self._stats.block_size = self._block_size
            self._stats.block_count = block_count

    def range_add(self, left: int, right: int, delta: int) -> None:
        """
        Add delta to all elements in [left, right].

        Args:
            left: Left endpoint
            right: Right endpoint
            delta: Value to add
        """
        with self._lock:
            self._stats.updates += 1

            left_block = left // self._block_size
            right_block = right // self._block_size

            if left_block == right_block:
                # Same block - update elements
                for i in range(left, right + 1):
                    self._array[i] += delta
            else:
                # Left partial block
                left_block_end = (left_block + 1) * self._block_size - 1
                for i in range(left, min(left_block_end + 1, len(self._array))):
                    self._array[i] += delta

                # Complete blocks - lazy update
                for block in range(left_block + 1, right_block):
                    self._block_add[block] += delta

                # Right partial block
                right_block_start = right_block * self._block_size
                for i in range(right_block_start, right + 1):
                    self._array[i] += delta

    def get(self, index: int) -> int:
        """Get element at index."""
        with self._lock:
            self._stats.queries += 1
            block = index // self._block_size
            return self._array[index] + self._block_add[block]

    def __getitem__(self, index: int) -> int:
        return self.get(index)


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_sum_sqrt(array: List[int]) -> SumSqrt:
    """Create sqrt decomposition for range sums."""
    sqrt = SumSqrt()
    sqrt.build(array)
    return sqrt


def create_min_sqrt(array: List[int]) -> MinSqrt:
    """Create sqrt decomposition for range minimum."""
    sqrt = MinSqrt()
    sqrt.build(array)
    return sqrt


def create_max_sqrt(array: List[int]) -> MaxSqrt:
    """Create sqrt decomposition for range maximum."""
    sqrt = MaxSqrt()
    sqrt.build(array)
    return sqrt


def create_gcd_sqrt(array: List[int]) -> GCDSqrt:
    """Create sqrt decomposition for range GCD."""
    sqrt = GCDSqrt()
    sqrt.build(array)
    return sqrt


def create_range_update_sqrt(array: List[int]) -> RangeUpdateSqrt:
    """Create sqrt decomposition with range updates."""
    sqrt = RangeUpdateSqrt()
    sqrt.build(array)
    return sqrt
