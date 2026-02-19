"""
BAEL Ring Buffer Engine Implementation
=======================================

Circular buffer for efficient fixed-size queuing.

"Ba'el cycles through data with eternal precision." — Ba'el
"""

import logging
import threading
from typing import Any, Callable, Generator, Generic, List, Optional, TypeVar
from dataclasses import dataclass, field
from enum import Enum
import time

logger = logging.getLogger("BAEL.RingBuffer")

T = TypeVar('T')


# ============================================================================
# ENUMS
# ============================================================================

class OverflowPolicy(Enum):
    """Policy when buffer is full."""
    OVERWRITE = "overwrite"  # Overwrite oldest
    DROP_NEWEST = "drop_newest"  # Drop new item
    BLOCK = "block"  # Block until space
    RAISE = "raise"  # Raise exception


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class RingBufferConfig:
    """Ring buffer configuration."""
    capacity: int = 1024
    overflow_policy: OverflowPolicy = OverflowPolicy.OVERWRITE


# ============================================================================
# RING BUFFER
# ============================================================================

class RingBuffer(Generic[T]):
    """
    Ring buffer (circular buffer) implementation.

    Features:
    - Fixed size
    - O(1) push/pop
    - Configurable overflow handling
    - Thread-safe

    "Ba'el maintains perfect circular flow." — Ba'el
    """

    def __init__(
        self,
        capacity: int = 1024,
        overflow_policy: OverflowPolicy = OverflowPolicy.OVERWRITE
    ):
        """
        Initialize ring buffer.

        Args:
            capacity: Buffer capacity
            overflow_policy: Policy when full
        """
        if capacity <= 0:
            raise ValueError("Capacity must be positive")

        self._capacity = capacity
        self._overflow_policy = overflow_policy

        # Buffer storage
        self._buffer: List[Optional[T]] = [None] * capacity

        # Pointers
        self._head = 0  # Next write position
        self._tail = 0  # Next read position
        self._size = 0

        # Thread safety
        self._lock = threading.RLock()
        self._not_full = threading.Condition(self._lock)
        self._not_empty = threading.Condition(self._lock)

        # Stats
        self._stats = {
            'writes': 0,
            'reads': 0,
            'overwrites': 0,
            'drops': 0
        }

        logger.info(f"Ring buffer initialized (capacity={capacity})")

    # ========================================================================
    # CORE OPERATIONS
    # ========================================================================

    def push(
        self,
        item: T,
        timeout: Optional[float] = None
    ) -> bool:
        """
        Push item to buffer.

        Args:
            item: Item to push
            timeout: Timeout for blocking policy

        Returns:
            True if item was added
        """
        with self._lock:
            if self._size >= self._capacity:
                if self._overflow_policy == OverflowPolicy.OVERWRITE:
                    # Overwrite oldest
                    self._tail = (self._tail + 1) % self._capacity
                    self._size -= 1
                    self._stats['overwrites'] += 1

                elif self._overflow_policy == OverflowPolicy.DROP_NEWEST:
                    self._stats['drops'] += 1
                    return False

                elif self._overflow_policy == OverflowPolicy.BLOCK:
                    deadline = time.time() + (timeout or float('inf'))
                    while self._size >= self._capacity:
                        remaining = deadline - time.time()
                        if remaining <= 0:
                            return False
                        self._not_full.wait(timeout=remaining)

                elif self._overflow_policy == OverflowPolicy.RAISE:
                    raise BufferError("Ring buffer is full")

            self._buffer[self._head] = item
            self._head = (self._head + 1) % self._capacity
            self._size += 1

            self._stats['writes'] += 1

            self._not_empty.notify()

            return True

    def pop(self, timeout: Optional[float] = None) -> Optional[T]:
        """
        Pop oldest item from buffer.

        Args:
            timeout: Timeout for blocking

        Returns:
            Item or None if empty
        """
        with self._lock:
            if self._size == 0:
                if timeout is not None and timeout > 0:
                    if not self._not_empty.wait(timeout=timeout):
                        return None
                else:
                    return None

            if self._size == 0:
                return None

            item = self._buffer[self._tail]
            self._buffer[self._tail] = None
            self._tail = (self._tail + 1) % self._capacity
            self._size -= 1

            self._stats['reads'] += 1

            self._not_full.notify()

            return item

    def peek(self) -> Optional[T]:
        """
        Peek at oldest item without removing.

        Returns:
            Oldest item or None
        """
        with self._lock:
            if self._size == 0:
                return None
            return self._buffer[self._tail]

    def peek_newest(self) -> Optional[T]:
        """
        Peek at newest item.

        Returns:
            Newest item or None
        """
        with self._lock:
            if self._size == 0:
                return None
            newest_idx = (self._head - 1) % self._capacity
            return self._buffer[newest_idx]

    # ========================================================================
    # BULK OPERATIONS
    # ========================================================================

    def push_many(self, items: List[T]) -> int:
        """
        Push multiple items.

        Args:
            items: Items to push

        Returns:
            Number of items pushed
        """
        count = 0
        for item in items:
            if self.push(item):
                count += 1
        return count

    def pop_many(self, count: int) -> List[T]:
        """
        Pop multiple items.

        Args:
            count: Maximum items to pop

        Returns:
            List of items
        """
        items = []
        for _ in range(count):
            item = self.pop()
            if item is None:
                break
            items.append(item)
        return items

    def drain(self) -> List[T]:
        """
        Drain all items from buffer.

        Returns:
            List of all items
        """
        return self.pop_many(self._size)

    # ========================================================================
    # ITERATION
    # ========================================================================

    def __iter__(self) -> Generator[T, None, None]:
        """Iterate over items (oldest to newest)."""
        with self._lock:
            for i in range(self._size):
                idx = (self._tail + i) % self._capacity
                yield self._buffer[idx]

    def items(self) -> List[T]:
        """Get all items as list."""
        with self._lock:
            result = []
            for i in range(self._size):
                idx = (self._tail + i) % self._capacity
                result.append(self._buffer[idx])
            return result

    def reversed_items(self) -> List[T]:
        """Get items in reverse order (newest first)."""
        with self._lock:
            result = []
            for i in range(self._size - 1, -1, -1):
                idx = (self._tail + i) % self._capacity
                result.append(self._buffer[idx])
            return result

    # ========================================================================
    # UTILITY
    # ========================================================================

    def clear(self) -> None:
        """Clear the buffer."""
        with self._lock:
            self._buffer = [None] * self._capacity
            self._head = 0
            self._tail = 0
            self._size = 0
            self._not_full.notify_all()

    @property
    def capacity(self) -> int:
        """Get buffer capacity."""
        return self._capacity

    def __len__(self) -> int:
        """Get current size."""
        return self._size

    def is_empty(self) -> bool:
        """Check if buffer is empty."""
        return self._size == 0

    def is_full(self) -> bool:
        """Check if buffer is full."""
        return self._size >= self._capacity

    def available_space(self) -> int:
        """Get available space."""
        return self._capacity - self._size

    def get_stats(self) -> dict:
        """Get buffer statistics."""
        return {
            'capacity': self._capacity,
            'size': self._size,
            'available': self.available_space(),
            **self._stats
        }


# ============================================================================
# TYPED RING BUFFERS
# ============================================================================

class ByteRingBuffer(RingBuffer[int]):
    """Ring buffer for bytes."""

    def push_bytes(self, data: bytes) -> int:
        """Push bytes to buffer."""
        count = 0
        for byte in data:
            if self.push(byte):
                count += 1
        return count

    def pop_bytes(self, count: int) -> bytes:
        """Pop bytes from buffer."""
        result = bytearray()
        for _ in range(count):
            byte = self.pop()
            if byte is None:
                break
            result.append(byte)
        return bytes(result)


class TimestampedRingBuffer(Generic[T]):
    """Ring buffer with timestamps."""

    def __init__(
        self,
        capacity: int = 1024,
        overflow_policy: OverflowPolicy = OverflowPolicy.OVERWRITE
    ):
        self._buffer = RingBuffer[(float, T)](capacity, overflow_policy)

    def push(self, item: T, timestamp: Optional[float] = None) -> bool:
        """Push with timestamp."""
        ts = timestamp or time.time()
        return self._buffer.push((ts, item))

    def pop(self) -> Optional[tuple]:
        """Pop (timestamp, item) tuple."""
        return self._buffer.pop()

    def get_items_since(self, since: float) -> List[tuple]:
        """Get items since timestamp."""
        return [
            (ts, item) for ts, item in self._buffer
            if ts >= since
        ]

    def get_items_in_range(
        self,
        start: float,
        end: float
    ) -> List[tuple]:
        """Get items in time range."""
        return [
            (ts, item) for ts, item in self._buffer
            if start <= ts <= end
        ]


# ============================================================================
# MULTI-PRODUCER/CONSUMER
# ============================================================================

class MPMCRingBuffer(RingBuffer[T]):
    """
    Multi-producer, multi-consumer ring buffer.

    Thread-safe for multiple producers and consumers.
    """

    def __init__(
        self,
        capacity: int = 1024,
        overflow_policy: OverflowPolicy = OverflowPolicy.BLOCK
    ):
        super().__init__(capacity, overflow_policy)

        # Separate locks for producers and consumers
        self._producer_lock = threading.Lock()
        self._consumer_lock = threading.Lock()

    def produce(
        self,
        item: T,
        timeout: Optional[float] = None
    ) -> bool:
        """Thread-safe produce."""
        with self._producer_lock:
            return self.push(item, timeout)

    def consume(
        self,
        timeout: Optional[float] = None
    ) -> Optional[T]:
        """Thread-safe consume."""
        with self._consumer_lock:
            return self.pop(timeout)


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_ring_buffer(
    capacity: int = 1024,
    overflow_policy: OverflowPolicy = OverflowPolicy.OVERWRITE
) -> RingBuffer:
    """Create a ring buffer."""
    return RingBuffer(capacity, overflow_policy)


def create_byte_buffer(capacity: int = 4096) -> ByteRingBuffer:
    """Create a byte ring buffer."""
    return ByteRingBuffer(capacity)


def create_timestamped_buffer(
    capacity: int = 1024
) -> TimestampedRingBuffer:
    """Create a timestamped ring buffer."""
    return TimestampedRingBuffer(capacity)


def create_mpmc_buffer(
    capacity: int = 1024
) -> MPMCRingBuffer:
    """Create an MPMC ring buffer."""
    return MPMCRingBuffer(capacity)
