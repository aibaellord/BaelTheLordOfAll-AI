"""
BAEL Bit Array Engine Implementation
=====================================

Compact boolean storage with operations.

"Ba'el stores truth in the smallest possible space." — Ba'el
"""

import logging
import struct
import threading
from typing import Any, Dict, Iterator, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("BAEL.BitArray")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class BitArrayConfig:
    """Bit array configuration."""
    initial_size: int = 64
    auto_grow: bool = True
    growth_factor: float = 2.0


@dataclass
class BitArrayStats:
    """Bit array statistics."""
    size: int = 0
    set_bits: int = 0
    capacity: int = 0


# ============================================================================
# BIT ARRAY ENGINE
# ============================================================================

class BitArrayEngine:
    """
    Compact bit array implementation.

    Features:
    - O(1) bit operations
    - Bitwise operations
    - Population count
    - Iteration

    "Ba'el compresses truth to its essence." — Ba'el
    """

    def __init__(self, config: Optional[BitArrayConfig] = None):
        """Initialize bit array."""
        self.config = config or BitArrayConfig()

        # Calculate bytes needed
        self._size = self.config.initial_size
        self._byte_count = (self._size + 7) // 8

        # Storage
        self._data = bytearray(self._byte_count)

        # Cached count
        self._count = 0
        self._count_dirty = False

        # Thread safety
        self._lock = threading.RLock()

        logger.debug(f"Bit array initialized (size={self._size})")

    # ========================================================================
    # BASIC OPERATIONS
    # ========================================================================

    def set(self, index: int) -> None:
        """
        Set bit at index.

        Args:
            index: Bit index
        """
        with self._lock:
            self._ensure_capacity(index + 1)

            byte_idx = index // 8
            bit_idx = index % 8

            if not (self._data[byte_idx] & (1 << bit_idx)):
                self._count += 1

            self._data[byte_idx] |= (1 << bit_idx)

    def clear(self, index: int) -> None:
        """
        Clear bit at index.

        Args:
            index: Bit index
        """
        with self._lock:
            if index >= self._size:
                return

            byte_idx = index // 8
            bit_idx = index % 8

            if self._data[byte_idx] & (1 << bit_idx):
                self._count -= 1

            self._data[byte_idx] &= ~(1 << bit_idx)

    def toggle(self, index: int) -> bool:
        """
        Toggle bit at index.

        Args:
            index: Bit index

        Returns:
            New value
        """
        with self._lock:
            self._ensure_capacity(index + 1)

            byte_idx = index // 8
            bit_idx = index % 8

            was_set = bool(self._data[byte_idx] & (1 << bit_idx))
            self._data[byte_idx] ^= (1 << bit_idx)

            self._count += -1 if was_set else 1

            return not was_set

    def get(self, index: int) -> bool:
        """
        Get bit at index.

        Args:
            index: Bit index

        Returns:
            Bit value
        """
        with self._lock:
            if index >= self._size:
                return False

            byte_idx = index // 8
            bit_idx = index % 8

            return bool(self._data[byte_idx] & (1 << bit_idx))

    def __getitem__(self, index: int) -> bool:
        """Get bit by index."""
        return self.get(index)

    def __setitem__(self, index: int, value: bool) -> None:
        """Set bit by index."""
        if value:
            self.set(index)
        else:
            self.clear(index)

    # ========================================================================
    # RANGE OPERATIONS
    # ========================================================================

    def set_range(self, start: int, end: int) -> None:
        """
        Set bits in range [start, end).

        Args:
            start: Start index
            end: End index (exclusive)
        """
        with self._lock:
            self._ensure_capacity(end)

            for i in range(start, end):
                byte_idx = i // 8
                bit_idx = i % 8

                if not (self._data[byte_idx] & (1 << bit_idx)):
                    self._count += 1

                self._data[byte_idx] |= (1 << bit_idx)

    def clear_range(self, start: int, end: int) -> None:
        """
        Clear bits in range [start, end).

        Args:
            start: Start index
            end: End index (exclusive)
        """
        with self._lock:
            for i in range(start, min(end, self._size)):
                byte_idx = i // 8
                bit_idx = i % 8

                if self._data[byte_idx] & (1 << bit_idx):
                    self._count -= 1

                self._data[byte_idx] &= ~(1 << bit_idx)

    def set_all(self) -> None:
        """Set all bits."""
        with self._lock:
            for i in range(self._byte_count):
                self._data[i] = 0xFF
            self._count = self._size

    def clear_all(self) -> None:
        """Clear all bits."""
        with self._lock:
            for i in range(self._byte_count):
                self._data[i] = 0
            self._count = 0

    # ========================================================================
    # BITWISE OPERATIONS
    # ========================================================================

    def and_with(self, other: 'BitArrayEngine') -> 'BitArrayEngine':
        """
        AND with another bit array.

        Args:
            other: Other bit array

        Returns:
            New bit array
        """
        result = BitArrayEngine(BitArrayConfig(
            initial_size=max(self._size, other._size)
        ))

        min_bytes = min(self._byte_count, other._byte_count)
        for i in range(min_bytes):
            result._data[i] = self._data[i] & other._data[i]

        result._count_dirty = True
        return result

    def or_with(self, other: 'BitArrayEngine') -> 'BitArrayEngine':
        """
        OR with another bit array.

        Args:
            other: Other bit array

        Returns:
            New bit array
        """
        result = BitArrayEngine(BitArrayConfig(
            initial_size=max(self._size, other._size)
        ))

        for i in range(max(self._byte_count, other._byte_count)):
            a = self._data[i] if i < self._byte_count else 0
            b = other._data[i] if i < other._byte_count else 0
            result._data[i] = a | b

        result._count_dirty = True
        return result

    def xor_with(self, other: 'BitArrayEngine') -> 'BitArrayEngine':
        """
        XOR with another bit array.

        Args:
            other: Other bit array

        Returns:
            New bit array
        """
        result = BitArrayEngine(BitArrayConfig(
            initial_size=max(self._size, other._size)
        ))

        for i in range(max(self._byte_count, other._byte_count)):
            a = self._data[i] if i < self._byte_count else 0
            b = other._data[i] if i < other._byte_count else 0
            result._data[i] = a ^ b

        result._count_dirty = True
        return result

    def invert(self) -> 'BitArrayEngine':
        """
        Invert all bits.

        Returns:
            New bit array
        """
        result = BitArrayEngine(BitArrayConfig(initial_size=self._size))

        for i in range(self._byte_count):
            result._data[i] = ~self._data[i] & 0xFF

        result._count = self._size - self._count
        return result

    def __and__(self, other: 'BitArrayEngine') -> 'BitArrayEngine':
        return self.and_with(other)

    def __or__(self, other: 'BitArrayEngine') -> 'BitArrayEngine':
        return self.or_with(other)

    def __xor__(self, other: 'BitArrayEngine') -> 'BitArrayEngine':
        return self.xor_with(other)

    def __invert__(self) -> 'BitArrayEngine':
        return self.invert()

    # ========================================================================
    # COUNTING
    # ========================================================================

    def count(self) -> int:
        """
        Count set bits (population count).

        Returns:
            Number of set bits
        """
        if self._count_dirty:
            self._recount()
        return self._count

    def count_range(self, start: int, end: int) -> int:
        """
        Count set bits in range.

        Args:
            start: Start index
            end: End index (exclusive)

        Returns:
            Number of set bits in range
        """
        count = 0
        for i in range(start, min(end, self._size)):
            if self.get(i):
                count += 1
        return count

    def _recount(self) -> None:
        """Recount all set bits."""
        count = 0
        for byte in self._data:
            # Brian Kernighan's algorithm
            while byte:
                byte &= byte - 1
                count += 1
        self._count = count
        self._count_dirty = False

    @property
    def popcount(self) -> int:
        """Population count (alias for count)."""
        return self.count()

    # ========================================================================
    # SEARCHING
    # ========================================================================

    def first_set(self) -> Optional[int]:
        """
        Find first set bit.

        Returns:
            Index of first set bit, or None
        """
        for i in range(self._byte_count):
            if self._data[i]:
                for j in range(8):
                    if self._data[i] & (1 << j):
                        idx = i * 8 + j
                        return idx if idx < self._size else None
        return None

    def first_clear(self) -> Optional[int]:
        """
        Find first clear bit.

        Returns:
            Index of first clear bit, or None
        """
        for i in range(self._byte_count):
            if self._data[i] != 0xFF:
                for j in range(8):
                    if not (self._data[i] & (1 << j)):
                        idx = i * 8 + j
                        return idx if idx < self._size else None
        return None

    def last_set(self) -> Optional[int]:
        """
        Find last set bit.

        Returns:
            Index of last set bit, or None
        """
        for i in range(self._byte_count - 1, -1, -1):
            if self._data[i]:
                for j in range(7, -1, -1):
                    if self._data[i] & (1 << j):
                        idx = i * 8 + j
                        return idx if idx < self._size else None
        return None

    def next_set(self, start: int) -> Optional[int]:
        """
        Find next set bit after start.

        Args:
            start: Starting index

        Returns:
            Index of next set bit, or None
        """
        for i in range(start + 1, self._size):
            if self.get(i):
                return i
        return None

    def next_clear(self, start: int) -> Optional[int]:
        """
        Find next clear bit after start.

        Args:
            start: Starting index

        Returns:
            Index of next clear bit, or None
        """
        for i in range(start + 1, self._size):
            if not self.get(i):
                return i
        return None

    # ========================================================================
    # ITERATION
    # ========================================================================

    def iter_set(self) -> Iterator[int]:
        """
        Iterate set bit indices.

        Yields:
            Indices of set bits
        """
        for i in range(self._size):
            if self.get(i):
                yield i

    def iter_clear(self) -> Iterator[int]:
        """
        Iterate clear bit indices.

        Yields:
            Indices of clear bits
        """
        for i in range(self._size):
            if not self.get(i):
                yield i

    def __iter__(self) -> Iterator[bool]:
        """Iterate all bits."""
        for i in range(self._size):
            yield self.get(i)

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def _ensure_capacity(self, required: int) -> None:
        """Ensure capacity for index."""
        if required <= self._size:
            return

        if not self.config.auto_grow:
            raise IndexError(f"Index {required - 1} out of bounds")

        # Calculate new size
        new_size = self._size
        while new_size < required:
            new_size = int(new_size * self.config.growth_factor)

        new_byte_count = (new_size + 7) // 8

        # Extend data
        self._data.extend(bytes(new_byte_count - self._byte_count))

        self._size = new_size
        self._byte_count = new_byte_count

    def __len__(self) -> int:
        """Get size."""
        return self._size

    def __bool__(self) -> bool:
        """Check if any bit is set."""
        return self._count > 0

    def resize(self, new_size: int) -> None:
        """
        Resize bit array.

        Args:
            new_size: New size
        """
        with self._lock:
            if new_size > self._size:
                self._ensure_capacity(new_size)
            elif new_size < self._size:
                # Truncate
                self._size = new_size
                self._byte_count = (new_size + 7) // 8
                self._data = self._data[:self._byte_count]
                self._count_dirty = True

    def to_bytes(self) -> bytes:
        """Convert to bytes."""
        return bytes(self._data)

    @classmethod
    def from_bytes(cls, data: bytes, size: Optional[int] = None) -> 'BitArrayEngine':
        """
        Create from bytes.

        Args:
            data: Byte data
            size: Bit size (defaults to len(data) * 8)

        Returns:
            New BitArrayEngine
        """
        size = size or len(data) * 8
        ba = cls(BitArrayConfig(initial_size=size))
        ba._data = bytearray(data)
        ba._count_dirty = True
        return ba

    def to_list(self) -> List[bool]:
        """Convert to list of booleans."""
        return [self.get(i) for i in range(self._size)]

    @classmethod
    def from_list(cls, bits: List[bool]) -> 'BitArrayEngine':
        """
        Create from list of booleans.

        Args:
            bits: List of booleans

        Returns:
            New BitArrayEngine
        """
        ba = cls(BitArrayConfig(initial_size=len(bits)))
        for i, bit in enumerate(bits):
            if bit:
                ba.set(i)
        return ba

    def __repr__(self) -> str:
        """String representation."""
        if self._size <= 64:
            bits = ''.join('1' if self.get(i) else '0' for i in range(self._size))
            return f"BitArray({bits})"
        return f"BitArray(size={self._size}, count={self.count()})"

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'size': self._size,
            'capacity_bytes': self._byte_count,
            'set_bits': self.count(),
            'density': self.count() / self._size if self._size else 0
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_bit_array(size: int = 64, **kwargs) -> BitArrayEngine:
    """Create a new bit array."""
    config = BitArrayConfig(initial_size=size, **kwargs)
    return BitArrayEngine(config)


def from_integers(values: List[int], max_value: Optional[int] = None) -> BitArrayEngine:
    """
    Create bit array from list of integer indices.

    Args:
        values: List of indices to set
        max_value: Maximum expected value

    Returns:
        BitArrayEngine with specified bits set
    """
    max_val = max_value or (max(values) + 1 if values else 64)
    ba = create_bit_array(max_val)
    for v in values:
        ba.set(v)
    return ba
