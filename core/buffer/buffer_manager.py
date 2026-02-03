#!/usr/bin/env python3
"""
BAEL - Buffer Manager
Advanced buffer management for AI agent operations.

Features:
- Ring buffers
- Double buffering
- Buffer pools
- Memory-mapped buffers
- Overflow handling
- Buffer synchronization
- Zero-copy operations
- Buffer statistics
- Automatic resizing
- Buffer compaction
"""

import asyncio
import copy
import mmap
import os
import struct
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, TypeVar, Union)

T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')


# =============================================================================
# ENUMS
# =============================================================================

class BufferType(Enum):
    """Buffer types."""
    RING = "ring"
    DOUBLE = "double"
    POOL = "pool"
    FIFO = "fifo"
    LIFO = "lifo"


class OverflowPolicy(Enum):
    """Overflow policies."""
    DROP_OLDEST = "drop_oldest"
    DROP_NEWEST = "drop_newest"
    BLOCK = "block"
    RESIZE = "resize"
    ERROR = "error"


class BufferState(Enum):
    """Buffer states."""
    EMPTY = "empty"
    PARTIAL = "partial"
    FULL = "full"
    OVERFLOW = "overflow"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class BufferConfig:
    """Buffer configuration."""
    buffer_type: BufferType = BufferType.RING
    capacity: int = 1024
    overflow_policy: OverflowPolicy = OverflowPolicy.DROP_OLDEST
    auto_resize: bool = False
    max_capacity: int = 10240
    resize_factor: float = 2.0


@dataclass
class BufferStats:
    """Buffer statistics."""
    buffer_id: str = ""
    buffer_type: BufferType = BufferType.RING
    capacity: int = 0
    size: int = 0
    reads: int = 0
    writes: int = 0
    overflows: int = 0
    resizes: int = 0
    avg_latency_us: float = 0.0


@dataclass
class BufferEntry(Generic[T]):
    """Buffer entry."""
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    data: Optional[T] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# BUFFER IMPLEMENTATIONS
# =============================================================================

class Buffer(ABC, Generic[T]):
    """Base buffer class."""

    def __init__(self, config: BufferConfig):
        self.buffer_id = str(uuid.uuid4())
        self.config = config
        self._lock = threading.RLock()

        # Statistics
        self._reads = 0
        self._writes = 0
        self._overflows = 0
        self._resizes = 0
        self._total_latency_us = 0.0

    @abstractmethod
    def write(self, data: T) -> bool:
        """Write data to buffer."""
        pass

    @abstractmethod
    def read(self) -> Optional[T]:
        """Read data from buffer."""
        pass

    @abstractmethod
    def peek(self) -> Optional[T]:
        """Peek at data without removing."""
        pass

    @abstractmethod
    def size(self) -> int:
        """Get current size."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear buffer."""
        pass

    def is_empty(self) -> bool:
        """Check if buffer is empty."""
        return self.size() == 0

    def is_full(self) -> bool:
        """Check if buffer is full."""
        return self.size() >= self.config.capacity

    def capacity(self) -> int:
        """Get capacity."""
        return self.config.capacity

    def available(self) -> int:
        """Get available space."""
        return self.config.capacity - self.size()

    def state(self) -> BufferState:
        """Get buffer state."""
        sz = self.size()
        if sz == 0:
            return BufferState.EMPTY
        elif sz >= self.config.capacity:
            return BufferState.FULL
        else:
            return BufferState.PARTIAL

    def stats(self) -> BufferStats:
        """Get buffer statistics."""
        avg_latency = 0.0
        total_ops = self._reads + self._writes
        if total_ops > 0:
            avg_latency = self._total_latency_us / total_ops

        return BufferStats(
            buffer_id=self.buffer_id,
            buffer_type=self.config.buffer_type,
            capacity=self.config.capacity,
            size=self.size(),
            reads=self._reads,
            writes=self._writes,
            overflows=self._overflows,
            resizes=self._resizes,
            avg_latency_us=avg_latency
        )

    def _record_latency(self, start_time: float) -> None:
        """Record operation latency."""
        elapsed_us = (time.time() - start_time) * 1_000_000
        self._total_latency_us += elapsed_us


class RingBuffer(Buffer[T]):
    """Ring/circular buffer."""

    def __init__(self, config: BufferConfig):
        super().__init__(config)
        self._data: List[Optional[T]] = [None] * config.capacity
        self._head = 0  # Read position
        self._tail = 0  # Write position
        self._count = 0

    def write(self, data: T) -> bool:
        start = time.time()

        with self._lock:
            if self._count >= self.config.capacity:
                # Handle overflow
                if self.config.overflow_policy == OverflowPolicy.DROP_OLDEST:
                    self._head = (self._head + 1) % self.config.capacity
                    self._count -= 1
                    self._overflows += 1
                elif self.config.overflow_policy == OverflowPolicy.DROP_NEWEST:
                    self._overflows += 1
                    self._record_latency(start)
                    return False
                elif self.config.overflow_policy == OverflowPolicy.RESIZE:
                    if self.config.auto_resize and self.config.capacity < self.config.max_capacity:
                        self._resize()
                    else:
                        self._overflows += 1
                        self._record_latency(start)
                        return False
                elif self.config.overflow_policy == OverflowPolicy.ERROR:
                    self._overflows += 1
                    self._record_latency(start)
                    raise BufferError("Buffer overflow")

            self._data[self._tail] = data
            self._tail = (self._tail + 1) % self.config.capacity
            self._count += 1
            self._writes += 1

            self._record_latency(start)
            return True

    def read(self) -> Optional[T]:
        start = time.time()

        with self._lock:
            if self._count == 0:
                return None

            data = self._data[self._head]
            self._data[self._head] = None
            self._head = (self._head + 1) % self.config.capacity
            self._count -= 1
            self._reads += 1

            self._record_latency(start)
            return data

    def peek(self) -> Optional[T]:
        with self._lock:
            if self._count == 0:
                return None
            return self._data[self._head]

    def size(self) -> int:
        with self._lock:
            return self._count

    def clear(self) -> None:
        with self._lock:
            self._data = [None] * self.config.capacity
            self._head = 0
            self._tail = 0
            self._count = 0

    def _resize(self) -> None:
        """Resize buffer."""
        new_capacity = int(self.config.capacity * self.config.resize_factor)
        new_capacity = min(new_capacity, self.config.max_capacity)

        new_data: List[Optional[T]] = [None] * new_capacity

        # Copy existing data
        for i in range(self._count):
            idx = (self._head + i) % self.config.capacity
            new_data[i] = self._data[idx]

        self._data = new_data
        self._head = 0
        self._tail = self._count
        self.config.capacity = new_capacity
        self._resizes += 1

    def to_list(self) -> List[T]:
        """Convert to list."""
        with self._lock:
            result = []
            for i in range(self._count):
                idx = (self._head + i) % self.config.capacity
                if self._data[idx] is not None:
                    result.append(self._data[idx])
            return result


class FIFOBuffer(Buffer[T]):
    """First-In-First-Out buffer using deque."""

    def __init__(self, config: BufferConfig):
        super().__init__(config)
        self._data: deque = deque(maxlen=config.capacity if config.overflow_policy == OverflowPolicy.DROP_OLDEST else None)

    def write(self, data: T) -> bool:
        start = time.time()

        with self._lock:
            if len(self._data) >= self.config.capacity:
                if self.config.overflow_policy == OverflowPolicy.DROP_OLDEST:
                    self._data.popleft()
                    self._overflows += 1
                elif self.config.overflow_policy == OverflowPolicy.DROP_NEWEST:
                    self._overflows += 1
                    self._record_latency(start)
                    return False
                elif self.config.overflow_policy == OverflowPolicy.RESIZE:
                    if self.config.auto_resize and self.config.capacity < self.config.max_capacity:
                        self.config.capacity = min(
                            int(self.config.capacity * self.config.resize_factor),
                            self.config.max_capacity
                        )
                        self._resizes += 1
                    else:
                        self._overflows += 1
                        self._record_latency(start)
                        return False
                elif self.config.overflow_policy == OverflowPolicy.ERROR:
                    self._overflows += 1
                    raise BufferError("Buffer overflow")

            self._data.append(data)
            self._writes += 1

            self._record_latency(start)
            return True

    def read(self) -> Optional[T]:
        start = time.time()

        with self._lock:
            if not self._data:
                return None

            data = self._data.popleft()
            self._reads += 1

            self._record_latency(start)
            return data

    def peek(self) -> Optional[T]:
        with self._lock:
            if not self._data:
                return None
            return self._data[0]

    def size(self) -> int:
        with self._lock:
            return len(self._data)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def to_list(self) -> List[T]:
        """Convert to list."""
        with self._lock:
            return list(self._data)


class LIFOBuffer(Buffer[T]):
    """Last-In-First-Out buffer (stack)."""

    def __init__(self, config: BufferConfig):
        super().__init__(config)
        self._data: List[T] = []

    def write(self, data: T) -> bool:
        start = time.time()

        with self._lock:
            if len(self._data) >= self.config.capacity:
                if self.config.overflow_policy == OverflowPolicy.DROP_OLDEST:
                    self._data.pop(0)
                    self._overflows += 1
                elif self.config.overflow_policy == OverflowPolicy.DROP_NEWEST:
                    self._overflows += 1
                    self._record_latency(start)
                    return False
                elif self.config.overflow_policy == OverflowPolicy.RESIZE:
                    if self.config.auto_resize and self.config.capacity < self.config.max_capacity:
                        self.config.capacity = min(
                            int(self.config.capacity * self.config.resize_factor),
                            self.config.max_capacity
                        )
                        self._resizes += 1
                    else:
                        self._overflows += 1
                        self._record_latency(start)
                        return False
                else:
                    self._overflows += 1
                    raise BufferError("Buffer overflow")

            self._data.append(data)
            self._writes += 1

            self._record_latency(start)
            return True

    def read(self) -> Optional[T]:
        start = time.time()

        with self._lock:
            if not self._data:
                return None

            data = self._data.pop()
            self._reads += 1

            self._record_latency(start)
            return data

    def peek(self) -> Optional[T]:
        with self._lock:
            if not self._data:
                return None
            return self._data[-1]

    def size(self) -> int:
        with self._lock:
            return len(self._data)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def to_list(self) -> List[T]:
        """Convert to list."""
        with self._lock:
            return list(self._data)


class DoubleBuffer(Generic[T]):
    """Double buffer for producer-consumer pattern."""

    def __init__(self, config: BufferConfig):
        self.buffer_id = str(uuid.uuid4())
        self.config = config

        # Create two buffers
        self._front = RingBuffer[T](copy.deepcopy(config))
        self._back = RingBuffer[T](copy.deepcopy(config))
        self._lock = threading.RLock()
        self._swapped = False

    def write(self, data: T) -> bool:
        """Write to back buffer."""
        with self._lock:
            return self._back.write(data)

    def read(self) -> Optional[T]:
        """Read from front buffer."""
        with self._lock:
            return self._front.read()

    def swap(self) -> None:
        """Swap front and back buffers."""
        with self._lock:
            self._front, self._back = self._back, self._front
            self._swapped = True

    def front_size(self) -> int:
        """Get front buffer size."""
        with self._lock:
            return self._front.size()

    def back_size(self) -> int:
        """Get back buffer size."""
        with self._lock:
            return self._back.size()

    def clear_front(self) -> None:
        """Clear front buffer."""
        with self._lock:
            self._front.clear()

    def clear_back(self) -> None:
        """Clear back buffer."""
        with self._lock:
            self._back.clear()

    def clear_all(self) -> None:
        """Clear both buffers."""
        with self._lock:
            self._front.clear()
            self._back.clear()


# =============================================================================
# BUFFER POOL
# =============================================================================

class BufferPool(Generic[T]):
    """Pool of reusable buffers."""

    def __init__(
        self,
        pool_size: int,
        buffer_config: BufferConfig
    ):
        self.pool_id = str(uuid.uuid4())
        self.pool_size = pool_size
        self.config = buffer_config

        self._available: deque[Buffer[T]] = deque()
        self._in_use: Dict[str, Buffer[T]] = {}
        self._lock = threading.RLock()

        # Pre-allocate buffers
        for _ in range(pool_size):
            buffer = self._create_buffer()
            self._available.append(buffer)

        # Statistics
        self._acquires = 0
        self._releases = 0
        self._waits = 0

    def _create_buffer(self) -> Buffer[T]:
        """Create buffer based on config."""
        if self.config.buffer_type == BufferType.RING:
            return RingBuffer[T](copy.deepcopy(self.config))
        elif self.config.buffer_type == BufferType.FIFO:
            return FIFOBuffer[T](copy.deepcopy(self.config))
        elif self.config.buffer_type == BufferType.LIFO:
            return LIFOBuffer[T](copy.deepcopy(self.config))
        else:
            return RingBuffer[T](copy.deepcopy(self.config))

    def acquire(self, timeout: Optional[float] = None) -> Optional[Buffer[T]]:
        """Acquire buffer from pool."""
        start = time.time()

        while True:
            with self._lock:
                if self._available:
                    buffer = self._available.popleft()
                    self._in_use[buffer.buffer_id] = buffer
                    self._acquires += 1
                    return buffer

                self._waits += 1

            if timeout is not None:
                if time.time() - start >= timeout:
                    return None
                time.sleep(0.001)
            else:
                time.sleep(0.001)

    def release(self, buffer: Buffer[T]) -> bool:
        """Release buffer back to pool."""
        with self._lock:
            if buffer.buffer_id not in self._in_use:
                return False

            del self._in_use[buffer.buffer_id]
            buffer.clear()
            self._available.append(buffer)
            self._releases += 1
            return True

    def available_count(self) -> int:
        """Get available buffer count."""
        with self._lock:
            return len(self._available)

    def in_use_count(self) -> int:
        """Get in-use buffer count."""
        with self._lock:
            return len(self._in_use)

    def stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        with self._lock:
            return {
                "pool_id": self.pool_id,
                "pool_size": self.pool_size,
                "available": len(self._available),
                "in_use": len(self._in_use),
                "acquires": self._acquires,
                "releases": self._releases,
                "waits": self._waits
            }


# =============================================================================
# BUFFER MANAGER
# =============================================================================

class BufferManager:
    """
    Buffer Manager for BAEL.

    Advanced buffer management.
    """

    def __init__(self):
        self._buffers: Dict[str, Buffer] = {}
        self._double_buffers: Dict[str, DoubleBuffer] = {}
        self._pools: Dict[str, BufferPool] = {}
        self._lock = threading.RLock()

    # -------------------------------------------------------------------------
    # BUFFER CREATION
    # -------------------------------------------------------------------------

    def create_buffer(
        self,
        buffer_type: BufferType = BufferType.RING,
        capacity: int = 1024,
        overflow_policy: OverflowPolicy = OverflowPolicy.DROP_OLDEST,
        auto_resize: bool = False
    ) -> Buffer:
        """Create buffer."""
        config = BufferConfig(
            buffer_type=buffer_type,
            capacity=capacity,
            overflow_policy=overflow_policy,
            auto_resize=auto_resize
        )

        if buffer_type == BufferType.RING:
            buffer: Buffer = RingBuffer(config)
        elif buffer_type == BufferType.FIFO:
            buffer = FIFOBuffer(config)
        elif buffer_type == BufferType.LIFO:
            buffer = LIFOBuffer(config)
        else:
            buffer = RingBuffer(config)

        with self._lock:
            self._buffers[buffer.buffer_id] = buffer

        return buffer

    def create_ring_buffer(
        self,
        capacity: int = 1024,
        overflow_policy: OverflowPolicy = OverflowPolicy.DROP_OLDEST
    ) -> RingBuffer:
        """Create ring buffer."""
        config = BufferConfig(
            buffer_type=BufferType.RING,
            capacity=capacity,
            overflow_policy=overflow_policy
        )

        buffer = RingBuffer(config)

        with self._lock:
            self._buffers[buffer.buffer_id] = buffer

        return buffer

    def create_fifo_buffer(
        self,
        capacity: int = 1024,
        overflow_policy: OverflowPolicy = OverflowPolicy.DROP_OLDEST
    ) -> FIFOBuffer:
        """Create FIFO buffer."""
        config = BufferConfig(
            buffer_type=BufferType.FIFO,
            capacity=capacity,
            overflow_policy=overflow_policy
        )

        buffer = FIFOBuffer(config)

        with self._lock:
            self._buffers[buffer.buffer_id] = buffer

        return buffer

    def create_lifo_buffer(
        self,
        capacity: int = 1024,
        overflow_policy: OverflowPolicy = OverflowPolicy.DROP_OLDEST
    ) -> LIFOBuffer:
        """Create LIFO buffer."""
        config = BufferConfig(
            buffer_type=BufferType.LIFO,
            capacity=capacity,
            overflow_policy=overflow_policy
        )

        buffer = LIFOBuffer(config)

        with self._lock:
            self._buffers[buffer.buffer_id] = buffer

        return buffer

    def create_double_buffer(
        self,
        capacity: int = 1024,
        overflow_policy: OverflowPolicy = OverflowPolicy.DROP_OLDEST
    ) -> DoubleBuffer:
        """Create double buffer."""
        config = BufferConfig(
            buffer_type=BufferType.RING,
            capacity=capacity,
            overflow_policy=overflow_policy
        )

        buffer = DoubleBuffer(config)

        with self._lock:
            self._double_buffers[buffer.buffer_id] = buffer

        return buffer

    # -------------------------------------------------------------------------
    # POOL MANAGEMENT
    # -------------------------------------------------------------------------

    def create_pool(
        self,
        pool_size: int = 10,
        buffer_type: BufferType = BufferType.RING,
        buffer_capacity: int = 1024
    ) -> BufferPool:
        """Create buffer pool."""
        config = BufferConfig(
            buffer_type=buffer_type,
            capacity=buffer_capacity
        )

        pool = BufferPool(pool_size, config)

        with self._lock:
            self._pools[pool.pool_id] = pool

        return pool

    def get_pool(self, pool_id: str) -> Optional[BufferPool]:
        """Get buffer pool."""
        with self._lock:
            return self._pools.get(pool_id)

    # -------------------------------------------------------------------------
    # BUFFER ACCESS
    # -------------------------------------------------------------------------

    def get_buffer(self, buffer_id: str) -> Optional[Buffer]:
        """Get buffer by ID."""
        with self._lock:
            return self._buffers.get(buffer_id)

    def get_double_buffer(
        self,
        buffer_id: str
    ) -> Optional[DoubleBuffer]:
        """Get double buffer by ID."""
        with self._lock:
            return self._double_buffers.get(buffer_id)

    def delete_buffer(self, buffer_id: str) -> bool:
        """Delete buffer."""
        with self._lock:
            if buffer_id in self._buffers:
                del self._buffers[buffer_id]
                return True
            if buffer_id in self._double_buffers:
                del self._double_buffers[buffer_id]
                return True
            return False

    def delete_pool(self, pool_id: str) -> bool:
        """Delete buffer pool."""
        with self._lock:
            if pool_id in self._pools:
                del self._pools[pool_id]
                return True
            return False

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self, buffer_id: str) -> Optional[BufferStats]:
        """Get buffer statistics."""
        with self._lock:
            buffer = self._buffers.get(buffer_id)
            if buffer:
                return buffer.stats()
            return None

    def get_all_stats(self) -> List[BufferStats]:
        """Get all buffer statistics."""
        with self._lock:
            return [b.stats() for b in self._buffers.values()]

    def get_pool_stats(self, pool_id: str) -> Optional[Dict[str, Any]]:
        """Get pool statistics."""
        with self._lock:
            pool = self._pools.get(pool_id)
            if pool:
                return pool.stats()
            return None

    # -------------------------------------------------------------------------
    # LISTING
    # -------------------------------------------------------------------------

    def list_buffers(self) -> List[str]:
        """List buffer IDs."""
        with self._lock:
            return list(self._buffers.keys())

    def list_double_buffers(self) -> List[str]:
        """List double buffer IDs."""
        with self._lock:
            return list(self._double_buffers.keys())

    def list_pools(self) -> List[str]:
        """List pool IDs."""
        with self._lock:
            return list(self._pools.keys())

    def buffer_count(self) -> int:
        """Get total buffer count."""
        with self._lock:
            return (
                len(self._buffers) +
                len(self._double_buffers)
            )


class BufferError(Exception):
    """Buffer error."""
    pass


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Buffer Manager."""
    print("=" * 70)
    print("BAEL - BUFFER MANAGER DEMO")
    print("Advanced Buffer Management for AI Agents")
    print("=" * 70)
    print()

    manager = BufferManager()

    # 1. Ring Buffer
    print("1. RING BUFFER:")
    print("-" * 40)

    ring = manager.create_ring_buffer(capacity=5)

    for i in range(7):
        success = ring.write(i)
        print(f"   Write {i}: {success}")

    print(f"   Size: {ring.size()}")
    print(f"   Contents: {ring.to_list()}")
    print()

    # 2. Read Operations
    print("2. READ OPERATIONS:")
    print("-" * 40)

    while not ring.is_empty():
        data = ring.read()
        print(f"   Read: {data}")
    print()

    # 3. FIFO Buffer
    print("3. FIFO BUFFER:")
    print("-" * 40)

    fifo = manager.create_fifo_buffer(capacity=3)

    fifo.write("first")
    fifo.write("second")
    fifo.write("third")

    print(f"   Peek: {fifo.peek()}")
    print(f"   Read: {fifo.read()}")
    print(f"   Read: {fifo.read()}")
    print()

    # 4. LIFO Buffer
    print("4. LIFO BUFFER (STACK):")
    print("-" * 40)

    lifo = manager.create_lifo_buffer(capacity=3)

    lifo.write("bottom")
    lifo.write("middle")
    lifo.write("top")

    print(f"   Peek: {lifo.peek()}")
    print(f"   Pop: {lifo.read()}")
    print(f"   Pop: {lifo.read()}")
    print()

    # 5. Double Buffer
    print("5. DOUBLE BUFFER:")
    print("-" * 40)

    double = manager.create_double_buffer(capacity=10)

    # Write to back
    for i in range(5):
        double.write(f"frame_{i}")

    print(f"   Back size: {double.back_size()}")
    print(f"   Front size: {double.front_size()}")

    # Swap
    double.swap()
    print(f"   After swap:")
    print(f"   Back size: {double.back_size()}")
    print(f"   Front size: {double.front_size()}")

    # Read from front
    while double.front_size() > 0:
        data = double.read()
        print(f"   Read: {data}")
    print()

    # 6. Buffer Pool
    print("6. BUFFER POOL:")
    print("-" * 40)

    pool = manager.create_pool(pool_size=3, buffer_capacity=10)

    print(f"   Available: {pool.available_count()}")
    print(f"   In use: {pool.in_use_count()}")

    # Acquire buffers
    buf1 = pool.acquire()
    buf2 = pool.acquire()

    print(f"   After acquire 2:")
    print(f"   Available: {pool.available_count()}")
    print(f"   In use: {pool.in_use_count()}")

    # Use and release
    if buf1:
        buf1.write("test")
        pool.release(buf1)

    print(f"   After release 1:")
    print(f"   Available: {pool.available_count()}")
    print()

    # 7. Overflow Policies
    print("7. OVERFLOW POLICIES:")
    print("-" * 40)

    # Drop newest
    drop_new = manager.create_buffer(
        buffer_type=BufferType.RING,
        capacity=3,
        overflow_policy=OverflowPolicy.DROP_NEWEST
    )

    for i in range(5):
        success = drop_new.write(i)
        print(f"   Write {i}: {success}")

    print(f"   Contents: {drop_new.to_list()}")
    print()

    # 8. Auto Resize
    print("8. AUTO RESIZE:")
    print("-" * 40)

    resizable = manager.create_buffer(
        buffer_type=BufferType.RING,
        capacity=3,
        overflow_policy=OverflowPolicy.RESIZE,
        auto_resize=True
    )

    print(f"   Initial capacity: {resizable.capacity()}")

    for i in range(10):
        resizable.write(i)

    print(f"   After 10 writes: {resizable.capacity()}")
    print(f"   Size: {resizable.size()}")
    print()

    # 9. Buffer States
    print("9. BUFFER STATES:")
    print("-" * 40)

    state_buf = manager.create_ring_buffer(capacity=3)

    print(f"   Empty state: {state_buf.state().value}")

    state_buf.write(1)
    print(f"   After write: {state_buf.state().value}")

    state_buf.write(2)
    state_buf.write(3)
    print(f"   Full state: {state_buf.state().value}")
    print()

    # 10. Statistics
    print("10. STATISTICS:")
    print("-" * 40)

    stats = ring.stats()
    print(f"   Buffer: {stats.buffer_id[:8]}...")
    print(f"   Reads: {stats.reads}")
    print(f"   Writes: {stats.writes}")
    print(f"   Overflows: {stats.overflows}")
    print(f"   Avg latency: {stats.avg_latency_us:.2f} us")
    print()

    # 11. Pool Statistics
    print("11. POOL STATISTICS:")
    print("-" * 40)

    pool_stats = pool.stats()
    for key, value in pool_stats.items():
        if key != "pool_id":
            print(f"   {key}: {value}")
    print()

    # 12. List Buffers
    print("12. LIST BUFFERS:")
    print("-" * 40)

    print(f"   Buffers: {len(manager.list_buffers())}")
    print(f"   Double buffers: {len(manager.list_double_buffers())}")
    print(f"   Pools: {len(manager.list_pools())}")
    print(f"   Total: {manager.buffer_count()}")
    print()

    # 13. Buffer Operations
    print("13. BUFFER OPERATIONS:")
    print("-" * 40)

    ops_buf = manager.create_ring_buffer(capacity=5)

    ops_buf.write(10)
    ops_buf.write(20)
    ops_buf.write(30)

    print(f"   Available: {ops_buf.available()}")
    print(f"   Is full: {ops_buf.is_full()}")
    print(f"   Is empty: {ops_buf.is_empty()}")
    print()

    # 14. Clear Buffer
    print("14. CLEAR BUFFER:")
    print("-" * 40)

    print(f"   Before clear: {ops_buf.size()}")
    ops_buf.clear()
    print(f"   After clear: {ops_buf.size()}")
    print()

    # 15. Delete Operations
    print("15. DELETE OPERATIONS:")
    print("-" * 40)

    count_before = len(manager.list_buffers())

    deleted = manager.delete_buffer(ops_buf.buffer_id)

    count_after = len(manager.list_buffers())

    print(f"   Deleted: {deleted}")
    print(f"   Buffers: {count_before} -> {count_after}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Buffer Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
