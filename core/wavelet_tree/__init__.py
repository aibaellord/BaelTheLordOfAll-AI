"""
BAEL Wavelet Tree Engine Implementation
========================================

Efficient range-rank-select queries.

"Ba'el decomposes realities at every frequency." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, Generic, List, Optional, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("BAEL.WaveletTree")

T = TypeVar('T')


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class WaveletNode:
    """Node in wavelet tree."""
    bit_vector: List[int]
    rank0: List[int]  # Prefix count of 0s
    rank1: List[int]  # Prefix count of 1s
    left: Optional['WaveletNode'] = None
    right: Optional['WaveletNode'] = None
    lo: int = 0  # Low value of alphabet range
    hi: int = 0  # High value of alphabet range


@dataclass
class WaveletTreeStats:
    """Wavelet tree statistics."""
    size: int = 0
    alphabet_size: int = 0
    height: int = 0
    queries: int = 0


# ============================================================================
# WAVELET TREE ENGINE
# ============================================================================

class WaveletTreeEngine(Generic[T]):
    """
    Wavelet Tree for range-rank-select queries.

    Features:
    - O(log σ) rank/select queries
    - O(log σ) quantile queries
    - O(log σ) range frequency queries
    - Space: O(n log σ) bits

    "Ba'el queries all frequencies of existence." — Ba'el
    """

    def __init__(self, sequence: Optional[List[int]] = None):
        """
        Initialize wavelet tree.

        Args:
            sequence: Integer sequence (alphabet should be contiguous)
        """
        self._sequence: List[int] = []
        self._root: Optional[WaveletNode] = None
        self._alphabet_size = 0
        self._n = 0

        self._stats = WaveletTreeStats()
        self._lock = threading.RLock()

        if sequence:
            self.build(sequence)

    def build(self, sequence: List[int]) -> None:
        """
        Build wavelet tree from sequence.

        Args:
            sequence: Integer sequence
        """
        with self._lock:
            if not sequence:
                self._root = None
                return

            self._sequence = sequence.copy()
            self._n = len(sequence)

            # Get alphabet range
            min_val = min(sequence)
            max_val = max(sequence)
            self._alphabet_size = max_val - min_val + 1

            # Build tree recursively
            self._root = self._build_node(sequence, min_val, max_val)

            # Update stats
            self._stats.size = self._n
            self._stats.alphabet_size = self._alphabet_size
            self._stats.height = self._compute_height()

            logger.info(f"Wavelet tree built (n={self._n}, σ={self._alphabet_size})")

    def _build_node(
        self,
        sequence: List[int],
        lo: int,
        hi: int
    ) -> Optional[WaveletNode]:
        """Build wavelet tree node recursively."""
        if not sequence or lo > hi:
            return None

        if lo == hi:
            # Leaf node
            node = WaveletNode(
                bit_vector=[],
                rank0=[0],
                rank1=[0],
                lo=lo,
                hi=hi
            )
            return node

        mid = (lo + hi) // 2

        # Build bit vector: 0 if value <= mid, 1 if value > mid
        bit_vector = []
        left_seq = []
        right_seq = []

        for val in sequence:
            if val <= mid:
                bit_vector.append(0)
                left_seq.append(val)
            else:
                bit_vector.append(1)
                right_seq.append(val)

        # Build rank arrays
        rank0 = [0]
        rank1 = [0]

        for bit in bit_vector:
            if bit == 0:
                rank0.append(rank0[-1] + 1)
                rank1.append(rank1[-1])
            else:
                rank0.append(rank0[-1])
                rank1.append(rank1[-1] + 1)

        node = WaveletNode(
            bit_vector=bit_vector,
            rank0=rank0,
            rank1=rank1,
            lo=lo,
            hi=hi
        )

        # Build children
        node.left = self._build_node(left_seq, lo, mid)
        node.right = self._build_node(right_seq, mid + 1, hi)

        return node

    def _compute_height(self) -> int:
        """Compute tree height."""
        if not self._root:
            return 0

        def height(node: Optional[WaveletNode]) -> int:
            if not node:
                return 0
            return 1 + max(height(node.left), height(node.right))

        return height(self._root)

    # ========================================================================
    # ACCESS
    # ========================================================================

    def access(self, index: int) -> Optional[int]:
        """
        Get value at index.

        Args:
            index: Position (0-indexed)

        Returns:
            Value at index
        """
        with self._lock:
            self._stats.queries += 1

            if not self._root or index < 0 or index >= self._n:
                return None

            return self._access(self._root, index)

    def _access(self, node: WaveletNode, pos: int) -> int:
        """Access value at position."""
        if node.lo == node.hi:
            return node.lo

        if node.bit_vector[pos] == 0:
            new_pos = node.rank0[pos]
            return self._access(node.left, new_pos)
        else:
            new_pos = node.rank1[pos]
            return self._access(node.right, new_pos)

    # ========================================================================
    # RANK
    # ========================================================================

    def rank(self, value: int, pos: int) -> int:
        """
        Count occurrences of value in sequence[0:pos].

        Args:
            value: Value to count
            pos: End position (exclusive)

        Returns:
            Number of occurrences
        """
        with self._lock:
            self._stats.queries += 1

            if not self._root or pos <= 0:
                return 0

            pos = min(pos, self._n)
            return self._rank(self._root, value, pos)

    def _rank(self, node: WaveletNode, value: int, pos: int) -> int:
        """Count occurrences of value."""
        if node.lo == node.hi:
            return pos

        mid = (node.lo + node.hi) // 2

        if value <= mid:
            new_pos = node.rank0[pos]
            if node.left:
                return self._rank(node.left, value, new_pos)
            return new_pos
        else:
            new_pos = node.rank1[pos]
            if node.right:
                return self._rank(node.right, value, new_pos)
            return new_pos

    # ========================================================================
    # SELECT
    # ========================================================================

    def select(self, value: int, k: int) -> Optional[int]:
        """
        Find position of k-th occurrence of value (1-indexed k).

        Args:
            value: Value to find
            k: Occurrence number (1-indexed)

        Returns:
            Position or None if not found
        """
        with self._lock:
            self._stats.queries += 1

            if not self._root or k <= 0:
                return None

            return self._select(self._root, value, k)

    def _select(self, node: WaveletNode, value: int, k: int) -> Optional[int]:
        """Find k-th occurrence of value."""
        if node.lo == node.hi:
            if k > len(node.bit_vector) if node.bit_vector else k > 0:
                return None
            return k - 1 if k > 0 else None

        mid = (node.lo + node.hi) // 2

        if value <= mid:
            if node.left:
                pos = self._select(node.left, value, k)
                if pos is None:
                    return None
                # Find pos-th 0 in bit vector
                return self._select_bit(node.rank0, 0, node.bit_vector, pos + 1)
            return None
        else:
            if node.right:
                pos = self._select(node.right, value, k)
                if pos is None:
                    return None
                # Find pos-th 1 in bit vector
                return self._select_bit(node.rank1, 1, node.bit_vector, pos + 1)
            return None

    def _select_bit(
        self,
        rank_arr: List[int],
        bit: int,
        bit_vector: List[int],
        k: int
    ) -> Optional[int]:
        """Find k-th occurrence of bit in bit vector."""
        # Binary search
        lo, hi = 0, len(bit_vector)

        while lo < hi:
            mid = (lo + hi) // 2

            if rank_arr[mid + 1] < k:
                lo = mid + 1
            else:
                hi = mid

        if lo < len(bit_vector) and rank_arr[lo + 1] >= k:
            return lo

        return None

    # ========================================================================
    # QUANTILE
    # ========================================================================

    def quantile(self, left: int, right: int, k: int) -> Optional[int]:
        """
        Find k-th smallest value in range [left, right).

        Args:
            left: Start position (inclusive)
            right: End position (exclusive)
            k: k-th smallest (1-indexed)

        Returns:
            k-th smallest value or None
        """
        with self._lock:
            self._stats.queries += 1

            if not self._root or left >= right or k <= 0 or k > right - left:
                return None

            return self._quantile(self._root, left, right, k)

    def _quantile(
        self,
        node: WaveletNode,
        left: int,
        right: int,
        k: int
    ) -> Optional[int]:
        """Find k-th smallest in range."""
        if node.lo == node.hi:
            return node.lo

        # Count 0s in range
        zeros = node.rank0[right] - node.rank0[left]

        if k <= zeros:
            # k-th smallest is in left subtree
            new_left = node.rank0[left]
            new_right = node.rank0[right]

            if node.left:
                return self._quantile(node.left, new_left, new_right, k)
            return node.lo
        else:
            # k-th smallest is in right subtree
            new_left = node.rank1[left]
            new_right = node.rank1[right]

            if node.right:
                return self._quantile(node.right, new_left, new_right, k - zeros)
            return node.hi

    # ========================================================================
    # RANGE FREQUENCY
    # ========================================================================

    def range_count(self, left: int, right: int, lo: int, hi: int) -> int:
        """
        Count values in range [left, right) that are in [lo, hi].

        Args:
            left: Start position (inclusive)
            right: End position (exclusive)
            lo: Low value (inclusive)
            hi: High value (inclusive)

        Returns:
            Count of values in range
        """
        with self._lock:
            self._stats.queries += 1

            if not self._root or left >= right or lo > hi:
                return 0

            return self._range_count(self._root, left, right, lo, hi)

    def _range_count(
        self,
        node: WaveletNode,
        left: int,
        right: int,
        lo: int,
        hi: int
    ) -> int:
        """Count values in position and value ranges."""
        if left >= right:
            return 0

        if lo <= node.lo and node.hi <= hi:
            return right - left

        if hi < node.lo or lo > node.hi:
            return 0

        count = 0
        mid = (node.lo + node.hi) // 2

        if lo <= mid and node.left:
            new_left = node.rank0[left]
            new_right = node.rank0[right]
            count += self._range_count(node.left, new_left, new_right, lo, min(hi, mid))

        if hi > mid and node.right:
            new_left = node.rank1[left]
            new_right = node.rank1[right]
            count += self._range_count(node.right, new_left, new_right, max(lo, mid + 1), hi)

        return count

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def __len__(self) -> int:
        return self._n

    def __getitem__(self, index: int) -> Optional[int]:
        return self.access(index)

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'size': self._stats.size,
            'alphabet_size': self._stats.alphabet_size,
            'height': self._stats.height,
            'queries': self._stats.queries
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_wavelet_tree(sequence: List[int]) -> WaveletTreeEngine:
    """Create wavelet tree from sequence."""
    return WaveletTreeEngine(sequence)


def rank(sequence: List[int], value: int, pos: int) -> int:
    """Quick rank query."""
    tree = WaveletTreeEngine(sequence)
    return tree.rank(value, pos)


def quantile(sequence: List[int], left: int, right: int, k: int) -> Optional[int]:
    """Quick quantile query."""
    tree = WaveletTreeEngine(sequence)
    return tree.quantile(left, right, k)


def range_count(
    sequence: List[int],
    left: int,
    right: int,
    lo: int,
    hi: int
) -> int:
    """Quick range count query."""
    tree = WaveletTreeEngine(sequence)
    return tree.range_count(left, right, lo, hi)
