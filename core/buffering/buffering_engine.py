#!/usr/bin/env python3
"""
BAEL - Buffering Engine
Data buffering for agents.

Features:
- Multiple buffer types
- Overflow handling
- Flush strategies
- Buffer pooling
- Memory management
"""

import asyncio
import hashlib
import json
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (
    Any, Callable, Dict, Generic, List, Optional, Set, Tuple, Type, TypeVar
)


T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class BufferType(Enum):
    """Buffer types."""
    FIFO = "fifo"
    LIFO = "lifo"
    CIRCULAR = "circular"
    PRIORITY = "priority"


class OverflowPolicy(Enum):
    """Overflow policies."""
    DROP_OLDEST = "drop_oldest"
    DROP_NEWEST = "drop_newest"
    BLOCK = "block"
    EXPAND = "expand"
    ERROR = "error"


class FlushTrigger(Enum):
    """Flush triggers."""
    SIZE = "size"
    TIME = "time"
    SIZE_OR_TIME = "size_or_time"
    MANUAL = "manual"


class BufferState(Enum):
    """Buffer states."""
    EMPTY = "empty"
    PARTIAL = "partial"
    FULL = "full"
    OVERFLOWING = "overflowing"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class BufferConfig:
    """Buffer configuration."""
    buffer_type: BufferType = BufferType.FIFO
    max_size: int = 1000
    overflow_policy: OverflowPolicy = OverflowPolicy.DROP_OLDEST
    flush_trigger: FlushTrigger = FlushTrigger.MANUAL
    flush_size: int = 100
    flush_interval_seconds: float = 60.0


@dataclass
class BufferStats:
    """Buffer statistics."""
    items_added: int = 0
    items_removed: int = 0
    items_dropped: int = 0
    flushes: int = 0
    overflows: int = 0
    current_size: int = 0
    max_size_reached: int = 0
    
    @property
    def throughput(self) -> int:
        return self.items_added - self.items_dropped


@dataclass
class BufferItem(Generic[T]):
    """Buffered item."""
    item_id: str = ""
    data: Optional[T] = None
    priority: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not self.item_id:
            self.item_id = str(uuid.uuid4())[:8]


@dataclass
class FlushResult(Generic[T]):
    """Flush result."""
    items: List[T] = field(default_factory=list)
    count: int = 0
    trigger: FlushTrigger = FlushTrigger.MANUAL
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PoolConfig:
    """Buffer pool configuration."""
    initial_buffers: int = 5
    max_buffers: int = 20
    buffer_size: int = 100


# =============================================================================
# BASE BUFFER
# =============================================================================

class BaseBuffer(Generic[T], ABC):
    """Abstract base buffer."""
    
    def __init__(self, config: BufferConfig):
        self._config = config
        self._stats = BufferStats()
    
    @abstractmethod
    async def put(self, item: T) -> bool:
        """Put an item."""
        pass
    
    @abstractmethod
    async def get(self) -> Optional[T]:
        """Get an item."""
        pass
    
    @abstractmethod
    def size(self) -> int:
        """Get current size."""
        pass
    
    @abstractmethod
    def clear(self) -> List[T]:
        """Clear buffer."""
        pass
    
    def is_empty(self) -> bool:
        """Check if empty."""
        return self.size() == 0
    
    def is_full(self) -> bool:
        """Check if full."""
        return self.size() >= self._config.max_size
    
    def state(self) -> BufferState:
        """Get buffer state."""
        size = self.size()
        if size == 0:
            return BufferState.EMPTY
        elif size >= self._config.max_size:
            return BufferState.FULL
        else:
            return BufferState.PARTIAL
    
    @property
    def stats(self) -> BufferStats:
        return self._stats


# =============================================================================
# BUFFER IMPLEMENTATIONS
# =============================================================================

class FIFOBuffer(BaseBuffer[T]):
    """First-In-First-Out buffer."""
    
    def __init__(self, config: BufferConfig):
        super().__init__(config)
        self._buffer: deque = deque()
    
    async def put(self, item: T) -> bool:
        """Put an item."""
        if self.is_full():
            self._stats.overflows += 1
            
            if self._config.overflow_policy == OverflowPolicy.DROP_OLDEST:
                self._buffer.popleft()
                self._stats.items_dropped += 1
            elif self._config.overflow_policy == OverflowPolicy.DROP_NEWEST:
                self._stats.items_dropped += 1
                return False
            elif self._config.overflow_policy == OverflowPolicy.ERROR:
                raise Exception("Buffer overflow")
            elif self._config.overflow_policy == OverflowPolicy.BLOCK:
                while self.is_full():
                    await asyncio.sleep(0.01)
            elif self._config.overflow_policy == OverflowPolicy.EXPAND:
                self._config.max_size *= 2
        
        self._buffer.append(item)
        self._stats.items_added += 1
        self._stats.current_size = self.size()
        self._stats.max_size_reached = max(
            self._stats.max_size_reached,
            self._stats.current_size
        )
        
        return True
    
    async def get(self) -> Optional[T]:
        """Get an item."""
        if self.is_empty():
            return None
        
        item = self._buffer.popleft()
        self._stats.items_removed += 1
        self._stats.current_size = self.size()
        
        return item
    
    def size(self) -> int:
        """Get current size."""
        return len(self._buffer)
    
    def clear(self) -> List[T]:
        """Clear buffer."""
        items = list(self._buffer)
        self._buffer.clear()
        self._stats.current_size = 0
        return items
    
    def peek(self) -> Optional[T]:
        """Peek at next item."""
        if self.is_empty():
            return None
        return self._buffer[0]


class LIFOBuffer(BaseBuffer[T]):
    """Last-In-First-Out buffer (stack)."""
    
    def __init__(self, config: BufferConfig):
        super().__init__(config)
        self._buffer: List[T] = []
    
    async def put(self, item: T) -> bool:
        """Put an item."""
        if self.is_full():
            self._stats.overflows += 1
            
            if self._config.overflow_policy == OverflowPolicy.DROP_OLDEST:
                self._buffer.pop(0)
                self._stats.items_dropped += 1
            elif self._config.overflow_policy == OverflowPolicy.DROP_NEWEST:
                self._stats.items_dropped += 1
                return False
            elif self._config.overflow_policy == OverflowPolicy.ERROR:
                raise Exception("Buffer overflow")
            elif self._config.overflow_policy == OverflowPolicy.EXPAND:
                self._config.max_size *= 2
        
        self._buffer.append(item)
        self._stats.items_added += 1
        self._stats.current_size = self.size()
        self._stats.max_size_reached = max(
            self._stats.max_size_reached,
            self._stats.current_size
        )
        
        return True
    
    async def get(self) -> Optional[T]:
        """Get an item."""
        if self.is_empty():
            return None
        
        item = self._buffer.pop()
        self._stats.items_removed += 1
        self._stats.current_size = self.size()
        
        return item
    
    def size(self) -> int:
        """Get current size."""
        return len(self._buffer)
    
    def clear(self) -> List[T]:
        """Clear buffer."""
        items = list(self._buffer)
        self._buffer.clear()
        self._stats.current_size = 0
        return items
    
    def peek(self) -> Optional[T]:
        """Peek at next item."""
        if self.is_empty():
            return None
        return self._buffer[-1]


class CircularBuffer(BaseBuffer[T]):
    """Circular buffer (ring buffer)."""
    
    def __init__(self, config: BufferConfig):
        super().__init__(config)
        self._buffer: List[Optional[T]] = [None] * config.max_size
        self._head = 0
        self._tail = 0
        self._count = 0
    
    async def put(self, item: T) -> bool:
        """Put an item."""
        if self._count >= self._config.max_size:
            self._stats.overflows += 1
            self._stats.items_dropped += 1
            
            if self._config.overflow_policy != OverflowPolicy.DROP_OLDEST:
                return False
            
            self._head = (self._head + 1) % self._config.max_size
            self._count -= 1
        
        self._buffer[self._tail] = item
        self._tail = (self._tail + 1) % self._config.max_size
        self._count += 1
        
        self._stats.items_added += 1
        self._stats.current_size = self._count
        self._stats.max_size_reached = max(
            self._stats.max_size_reached,
            self._stats.current_size
        )
        
        return True
    
    async def get(self) -> Optional[T]:
        """Get an item."""
        if self._count == 0:
            return None
        
        item = self._buffer[self._head]
        self._buffer[self._head] = None
        self._head = (self._head + 1) % self._config.max_size
        self._count -= 1
        
        self._stats.items_removed += 1
        self._stats.current_size = self._count
        
        return item
    
    def size(self) -> int:
        """Get current size."""
        return self._count
    
    def clear(self) -> List[T]:
        """Clear buffer."""
        items = []
        for i in range(self._count):
            idx = (self._head + i) % self._config.max_size
            if self._buffer[idx] is not None:
                items.append(self._buffer[idx])
        
        self._buffer = [None] * self._config.max_size
        self._head = 0
        self._tail = 0
        self._count = 0
        self._stats.current_size = 0
        
        return items


class PriorityBuffer(BaseBuffer[T]):
    """Priority buffer."""
    
    def __init__(self, config: BufferConfig):
        super().__init__(config)
        self._buffer: List[BufferItem[T]] = []
    
    async def put(self, item: T, priority: int = 0) -> bool:
        """Put an item with priority."""
        if self.is_full():
            self._stats.overflows += 1
            
            if self._config.overflow_policy == OverflowPolicy.DROP_OLDEST:
                self._buffer.pop()
                self._stats.items_dropped += 1
            elif self._config.overflow_policy == OverflowPolicy.DROP_NEWEST:
                self._stats.items_dropped += 1
                return False
            elif self._config.overflow_policy == OverflowPolicy.ERROR:
                raise Exception("Buffer overflow")
        
        buffer_item = BufferItem(data=item, priority=priority)
        self._buffer.append(buffer_item)
        self._buffer.sort(key=lambda x: -x.priority)
        
        self._stats.items_added += 1
        self._stats.current_size = self.size()
        self._stats.max_size_reached = max(
            self._stats.max_size_reached,
            self._stats.current_size
        )
        
        return True
    
    async def get(self) -> Optional[T]:
        """Get highest priority item."""
        if self.is_empty():
            return None
        
        buffer_item = self._buffer.pop(0)
        self._stats.items_removed += 1
        self._stats.current_size = self.size()
        
        return buffer_item.data
    
    def size(self) -> int:
        """Get current size."""
        return len(self._buffer)
    
    def clear(self) -> List[T]:
        """Clear buffer."""
        items = [item.data for item in self._buffer]
        self._buffer.clear()
        self._stats.current_size = 0
        return items


# =============================================================================
# BUFFER FACTORY
# =============================================================================

class BufferFactory:
    """Factory for creating buffers."""
    
    @staticmethod
    def create(config: BufferConfig) -> BaseBuffer:
        """Create a buffer."""
        if config.buffer_type == BufferType.FIFO:
            return FIFOBuffer(config)
        elif config.buffer_type == BufferType.LIFO:
            return LIFOBuffer(config)
        elif config.buffer_type == BufferType.CIRCULAR:
            return CircularBuffer(config)
        elif config.buffer_type == BufferType.PRIORITY:
            return PriorityBuffer(config)
        else:
            return FIFOBuffer(config)


# =============================================================================
# MANAGED BUFFER
# =============================================================================

class ManagedBuffer(Generic[T]):
    """Buffer with automatic flushing."""
    
    def __init__(
        self,
        name: str,
        config: BufferConfig,
        on_flush: Optional[Callable[[List[T]], Any]] = None
    ):
        self._name = name
        self._config = config
        self._buffer = BufferFactory.create(config)
        self._on_flush = on_flush
        
        self._last_flush = datetime.now()
        self._flush_task: Optional[asyncio.Task] = None
        
        if config.flush_trigger in [FlushTrigger.TIME, FlushTrigger.SIZE_OR_TIME]:
            self._start_flush_timer()
    
    def _start_flush_timer(self) -> None:
        """Start flush timer."""
        async def timer():
            while True:
                await asyncio.sleep(self._config.flush_interval_seconds)
                await self.flush(FlushTrigger.TIME)
        
        self._flush_task = asyncio.create_task(timer())
    
    async def put(self, item: T, priority: int = 0) -> bool:
        """Put an item."""
        if isinstance(self._buffer, PriorityBuffer):
            result = await self._buffer.put(item, priority)
        else:
            result = await self._buffer.put(item)
        
        if result and self._should_flush():
            await self.flush(FlushTrigger.SIZE)
        
        return result
    
    def _should_flush(self) -> bool:
        """Check if should flush."""
        if self._config.flush_trigger == FlushTrigger.MANUAL:
            return False
        
        if self._config.flush_trigger in [FlushTrigger.SIZE, FlushTrigger.SIZE_OR_TIME]:
            if self._buffer.size() >= self._config.flush_size:
                return True
        
        return False
    
    async def flush(self, trigger: FlushTrigger = FlushTrigger.MANUAL) -> FlushResult[T]:
        """Flush buffer."""
        items = self._buffer.clear()
        
        self._buffer._stats.flushes += 1
        self._last_flush = datetime.now()
        
        if self._on_flush and items:
            if asyncio.iscoroutinefunction(self._on_flush):
                await self._on_flush(items)
            else:
                self._on_flush(items)
        
        return FlushResult(
            items=items,
            count=len(items),
            trigger=trigger
        )
    
    async def get(self) -> Optional[T]:
        """Get an item."""
        return await self._buffer.get()
    
    def size(self) -> int:
        """Get current size."""
        return self._buffer.size()
    
    def is_empty(self) -> bool:
        """Check if empty."""
        return self._buffer.is_empty()
    
    def state(self) -> BufferState:
        """Get state."""
        return self._buffer.state()
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def stats(self) -> BufferStats:
        return self._buffer.stats
    
    async def close(self) -> None:
        """Close buffer."""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        await self.flush()


# =============================================================================
# BUFFER POOL
# =============================================================================

class BufferPool(Generic[T]):
    """Pool of reusable buffers."""
    
    def __init__(self, config: PoolConfig):
        self._config = config
        self._available: List[BaseBuffer[T]] = []
        self._in_use: Dict[str, BaseBuffer[T]] = {}
        
        self._initialize()
    
    def _initialize(self) -> None:
        """Initialize pool."""
        for _ in range(self._config.initial_buffers):
            buffer_config = BufferConfig(max_size=self._config.buffer_size)
            buffer = BufferFactory.create(buffer_config)
            self._available.append(buffer)
    
    def acquire(self) -> Optional[Tuple[str, BaseBuffer[T]]]:
        """Acquire a buffer from pool."""
        if not self._available:
            if len(self._in_use) >= self._config.max_buffers:
                return None
            
            buffer_config = BufferConfig(max_size=self._config.buffer_size)
            buffer = BufferFactory.create(buffer_config)
        else:
            buffer = self._available.pop()
        
        buffer_id = str(uuid.uuid4())[:8]
        self._in_use[buffer_id] = buffer
        
        return buffer_id, buffer
    
    def release(self, buffer_id: str) -> bool:
        """Release buffer back to pool."""
        buffer = self._in_use.pop(buffer_id, None)
        
        if buffer:
            buffer.clear()
            self._available.append(buffer)
            return True
        
        return False
    
    def size(self) -> int:
        """Get pool size."""
        return len(self._available) + len(self._in_use)
    
    def available_count(self) -> int:
        """Get available buffer count."""
        return len(self._available)
    
    def in_use_count(self) -> int:
        """Get in-use buffer count."""
        return len(self._in_use)


# =============================================================================
# DOUBLE BUFFER
# =============================================================================

class DoubleBuffer(Generic[T]):
    """Double buffering for producer/consumer."""
    
    def __init__(self, config: BufferConfig):
        self._config = config
        self._front = BufferFactory.create(config)
        self._back = BufferFactory.create(config)
        self._lock = asyncio.Lock()
    
    async def write(self, item: T) -> bool:
        """Write to back buffer."""
        return await self._back.put(item)
    
    async def read(self) -> Optional[T]:
        """Read from front buffer."""
        return await self._front.get()
    
    async def swap(self) -> None:
        """Swap front and back buffers."""
        async with self._lock:
            self._front, self._back = self._back, self._front
    
    def front_size(self) -> int:
        """Get front buffer size."""
        return self._front.size()
    
    def back_size(self) -> int:
        """Get back buffer size."""
        return self._back.size()
    
    def front_empty(self) -> bool:
        """Check if front is empty."""
        return self._front.is_empty()
    
    def back_empty(self) -> bool:
        """Check if back is empty."""
        return self._back.is_empty()


# =============================================================================
# BUFFERING ENGINE
# =============================================================================

class BufferingEngine:
    """
    Buffering Engine for BAEL.
    
    Data buffering for agents.
    """
    
    def __init__(self):
        self._buffers: Dict[str, ManagedBuffer] = {}
        self._pools: Dict[str, BufferPool] = {}
        self._double_buffers: Dict[str, DoubleBuffer] = {}
        
        self._factory = BufferFactory()
    
    # ----- Buffer Creation -----
    
    def create_buffer(
        self,
        name: str,
        config: Optional[BufferConfig] = None,
        on_flush: Optional[Callable] = None
    ) -> ManagedBuffer:
        """Create a managed buffer."""
        config = config or BufferConfig()
        buffer = ManagedBuffer(name, config, on_flush)
        self._buffers[name] = buffer
        return buffer
    
    def create_fifo(
        self,
        name: str,
        max_size: int = 1000,
        on_flush: Optional[Callable] = None
    ) -> ManagedBuffer:
        """Create a FIFO buffer."""
        config = BufferConfig(
            buffer_type=BufferType.FIFO,
            max_size=max_size
        )
        return self.create_buffer(name, config, on_flush)
    
    def create_lifo(
        self,
        name: str,
        max_size: int = 1000,
        on_flush: Optional[Callable] = None
    ) -> ManagedBuffer:
        """Create a LIFO buffer."""
        config = BufferConfig(
            buffer_type=BufferType.LIFO,
            max_size=max_size
        )
        return self.create_buffer(name, config, on_flush)
    
    def create_circular(
        self,
        name: str,
        max_size: int = 1000,
        on_flush: Optional[Callable] = None
    ) -> ManagedBuffer:
        """Create a circular buffer."""
        config = BufferConfig(
            buffer_type=BufferType.CIRCULAR,
            max_size=max_size
        )
        return self.create_buffer(name, config, on_flush)
    
    def create_priority(
        self,
        name: str,
        max_size: int = 1000,
        on_flush: Optional[Callable] = None
    ) -> ManagedBuffer:
        """Create a priority buffer."""
        config = BufferConfig(
            buffer_type=BufferType.PRIORITY,
            max_size=max_size
        )
        return self.create_buffer(name, config, on_flush)
    
    def create_auto_flush(
        self,
        name: str,
        flush_size: int = 100,
        flush_interval: float = 60.0,
        on_flush: Optional[Callable] = None
    ) -> ManagedBuffer:
        """Create auto-flushing buffer."""
        config = BufferConfig(
            flush_trigger=FlushTrigger.SIZE_OR_TIME,
            flush_size=flush_size,
            flush_interval_seconds=flush_interval
        )
        return self.create_buffer(name, config, on_flush)
    
    # ----- Buffer Access -----
    
    def get_buffer(self, name: str) -> Optional[ManagedBuffer]:
        """Get a buffer by name."""
        return self._buffers.get(name)
    
    def list_buffers(self) -> List[str]:
        """List buffer names."""
        return list(self._buffers.keys())
    
    async def delete_buffer(self, name: str) -> bool:
        """Delete a buffer."""
        buffer = self._buffers.pop(name, None)
        if buffer:
            await buffer.close()
            return True
        return False
    
    # ----- Buffer Operations -----
    
    async def put(self, name: str, item: Any, priority: int = 0) -> bool:
        """Put item in buffer."""
        buffer = self._buffers.get(name)
        if buffer:
            return await buffer.put(item, priority)
        return False
    
    async def get(self, name: str) -> Optional[Any]:
        """Get item from buffer."""
        buffer = self._buffers.get(name)
        if buffer:
            return await buffer.get()
        return None
    
    async def flush(self, name: str) -> Optional[FlushResult]:
        """Flush buffer."""
        buffer = self._buffers.get(name)
        if buffer:
            return await buffer.flush()
        return None
    
    async def flush_all(self) -> Dict[str, FlushResult]:
        """Flush all buffers."""
        results = {}
        for name, buffer in self._buffers.items():
            results[name] = await buffer.flush()
        return results
    
    def size(self, name: str) -> int:
        """Get buffer size."""
        buffer = self._buffers.get(name)
        return buffer.size() if buffer else 0
    
    def state(self, name: str) -> Optional[BufferState]:
        """Get buffer state."""
        buffer = self._buffers.get(name)
        return buffer.state() if buffer else None
    
    # ----- Buffer Pools -----
    
    def create_pool(
        self,
        name: str,
        config: Optional[PoolConfig] = None
    ) -> BufferPool:
        """Create a buffer pool."""
        config = config or PoolConfig()
        pool = BufferPool(config)
        self._pools[name] = pool
        return pool
    
    def get_pool(self, name: str) -> Optional[BufferPool]:
        """Get a buffer pool."""
        return self._pools.get(name)
    
    def acquire_from_pool(
        self,
        pool_name: str
    ) -> Optional[Tuple[str, BaseBuffer]]:
        """Acquire buffer from pool."""
        pool = self._pools.get(pool_name)
        if pool:
            return pool.acquire()
        return None
    
    def release_to_pool(self, pool_name: str, buffer_id: str) -> bool:
        """Release buffer to pool."""
        pool = self._pools.get(pool_name)
        if pool:
            return pool.release(buffer_id)
        return False
    
    # ----- Double Buffering -----
    
    def create_double_buffer(
        self,
        name: str,
        config: Optional[BufferConfig] = None
    ) -> DoubleBuffer:
        """Create a double buffer."""
        config = config or BufferConfig()
        double_buffer = DoubleBuffer(config)
        self._double_buffers[name] = double_buffer
        return double_buffer
    
    def get_double_buffer(self, name: str) -> Optional[DoubleBuffer]:
        """Get a double buffer."""
        return self._double_buffers.get(name)
    
    async def double_buffer_write(self, name: str, item: Any) -> bool:
        """Write to double buffer."""
        db = self._double_buffers.get(name)
        if db:
            return await db.write(item)
        return False
    
    async def double_buffer_read(self, name: str) -> Optional[Any]:
        """Read from double buffer."""
        db = self._double_buffers.get(name)
        if db:
            return await db.read()
        return None
    
    async def double_buffer_swap(self, name: str) -> bool:
        """Swap double buffer."""
        db = self._double_buffers.get(name)
        if db:
            await db.swap()
            return True
        return False
    
    # ----- Statistics -----
    
    def get_stats(self, name: str) -> Optional[BufferStats]:
        """Get buffer stats."""
        buffer = self._buffers.get(name)
        return buffer.stats if buffer else None
    
    def stats(self) -> Dict[str, Any]:
        """Get engine stats."""
        total_items = 0
        total_dropped = 0
        total_flushes = 0
        
        for buffer in self._buffers.values():
            total_items += buffer.size()
            total_dropped += buffer.stats.items_dropped
            total_flushes += buffer.stats.flushes
        
        return {
            "buffers": len(self._buffers),
            "pools": len(self._pools),
            "double_buffers": len(self._double_buffers),
            "total_items": total_items,
            "total_dropped": total_dropped,
            "total_flushes": total_flushes
        }
    
    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        buffer_states = {}
        for name, buffer in self._buffers.items():
            buffer_states[name] = {
                "size": buffer.size(),
                "state": buffer.state().value
            }
        
        return {
            "buffers": buffer_states,
            "pools": list(self._pools.keys()),
            "double_buffers": list(self._double_buffers.keys())
        }
    
    async def close(self) -> None:
        """Close all buffers."""
        for buffer in self._buffers.values():
            await buffer.close()


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Buffering Engine."""
    print("=" * 70)
    print("BAEL - BUFFERING ENGINE DEMO")
    print("Data Buffering for Agents")
    print("=" * 70)
    print()
    
    engine = BufferingEngine()
    
    # 1. FIFO Buffer
    print("1. FIFO BUFFER:")
    print("-" * 40)
    
    fifo = engine.create_fifo("fifo_buffer", max_size=5)
    
    for i in range(5):
        await fifo.put(i)
        print(f"   Put: {i}")
    
    print(f"   Size: {fifo.size()}")
    
    while not fifo.is_empty():
        item = await fifo.get()
        print(f"   Get: {item}")
    print()
    
    # 2. LIFO Buffer
    print("2. LIFO BUFFER:")
    print("-" * 40)
    
    lifo = engine.create_lifo("lifo_buffer", max_size=5)
    
    for i in range(5):
        await lifo.put(i)
    
    print(f"   Put: 0, 1, 2, 3, 4")
    print(f"   Get order (LIFO):", end=" ")
    
    while not lifo.is_empty():
        item = await lifo.get()
        print(item, end=" ")
    print("\n")
    
    # 3. Circular Buffer
    print("3. CIRCULAR BUFFER:")
    print("-" * 40)
    
    circular = engine.create_circular("circular_buffer", max_size=3)
    
    for i in range(5):
        await circular.put(i)
        print(f"   Put: {i}, Size: {circular.size()}")
    
    print(f"   Buffer contains (last 3):", end=" ")
    while not circular.is_empty():
        item = await circular.get()
        print(item, end=" ")
    print("\n")
    
    # 4. Priority Buffer
    print("4. PRIORITY BUFFER:")
    print("-" * 40)
    
    priority = engine.create_priority("priority_buffer", max_size=5)
    
    await priority.put("low", priority=1)
    await priority.put("high", priority=10)
    await priority.put("medium", priority=5)
    
    print(f"   Put: low(1), high(10), medium(5)")
    print(f"   Get order (by priority):", end=" ")
    
    while not priority.is_empty():
        item = await priority.get()
        print(item, end=" ")
    print("\n")
    
    # 5. Buffer States
    print("5. BUFFER STATES:")
    print("-" * 40)
    
    buf = engine.create_fifo("state_buffer", max_size=3)
    print(f"   Empty: {buf.state()}")
    
    await buf.put(1)
    print(f"   Partial: {buf.state()}")
    
    await buf.put(2)
    await buf.put(3)
    print(f"   Full: {buf.state()}")
    print()
    
    # 6. Overflow Policies
    print("6. OVERFLOW POLICIES:")
    print("-" * 40)
    
    config = BufferConfig(
        max_size=3,
        overflow_policy=OverflowPolicy.DROP_OLDEST
    )
    overflow_buf = engine.create_buffer("overflow_buffer", config)
    
    for i in range(5):
        await overflow_buf.put(i)
    
    print(f"   Put 0-4 with max_size=3")
    print(f"   Dropped: {overflow_buf.stats.items_dropped}")
    print(f"   Contains:", end=" ")
    while not overflow_buf.is_empty():
        item = await overflow_buf.get()
        print(item, end=" ")
    print("\n")
    
    # 7. Flush
    print("7. FLUSH:")
    print("-" * 40)
    
    flush_buf = engine.create_fifo("flush_buffer")
    for i in range(5):
        await flush_buf.put(i)
    
    result = await flush_buf.flush()
    print(f"   Flushed items: {result.items}")
    print(f"   Buffer size after flush: {flush_buf.size()}")
    print()
    
    # 8. Auto-Flush
    print("8. AUTO-FLUSH:")
    print("-" * 40)
    
    flushed_items = []
    
    def on_flush(items):
        flushed_items.extend(items)
        print(f"   Auto-flushed: {items}")
    
    auto_buf = engine.create_auto_flush(
        "auto_buffer",
        flush_size=3,
        flush_interval=10.0,
        on_flush=on_flush
    )
    
    for i in range(5):
        await auto_buf.put(i)
    
    print(f"   Remaining: {auto_buf.size()}")
    await auto_buf.close()
    print()
    
    # 9. Buffer Pool
    print("9. BUFFER POOL:")
    print("-" * 40)
    
    pool = engine.create_pool("main_pool", PoolConfig(
        initial_buffers=3,
        max_buffers=10,
        buffer_size=100
    ))
    
    print(f"   Initial available: {pool.available_count()}")
    
    buf_id, buf = pool.acquire()
    print(f"   Acquired: {buf_id}")
    print(f"   Available after acquire: {pool.available_count()}")
    
    pool.release(buf_id)
    print(f"   Available after release: {pool.available_count()}")
    print()
    
    # 10. Double Buffer
    print("10. DOUBLE BUFFER:")
    print("-" * 40)
    
    db = engine.create_double_buffer("double_buffer")
    
    await db.write(1)
    await db.write(2)
    print(f"   Written to back: 1, 2")
    print(f"   Back size: {db.back_size()}")
    print(f"   Front size: {db.front_size()}")
    
    await db.swap()
    print(f"   After swap:")
    print(f"   Back size: {db.back_size()}")
    print(f"   Front size: {db.front_size()}")
    
    item = await db.read()
    print(f"   Read from front: {item}")
    print()
    
    # 11. Engine Operations
    print("11. ENGINE OPERATIONS:")
    print("-" * 40)
    
    engine.create_fifo("test1")
    engine.create_lifo("test2")
    
    await engine.put("test1", "a")
    await engine.put("test1", "b")
    await engine.put("test2", "x")
    
    print(f"   Buffers: {engine.list_buffers()}")
    print(f"   test1 size: {engine.size('test1')}")
    print(f"   test1 state: {engine.state('test1')}")
    print()
    
    # 12. Flush All
    print("12. FLUSH ALL:")
    print("-" * 40)
    
    results = await engine.flush_all()
    for name, result in results.items():
        if result.count > 0:
            print(f"   {name}: {result.count} items")
    print()
    
    # 13. Buffer Stats
    print("13. BUFFER STATS:")
    print("-" * 40)
    
    stats_buf = engine.create_fifo("stats_buffer", max_size=5)
    for i in range(10):
        await stats_buf.put(i)
    
    for _ in range(3):
        await stats_buf.get()
    
    stats = stats_buf.stats
    print(f"   Items added: {stats.items_added}")
    print(f"   Items removed: {stats.items_removed}")
    print(f"   Items dropped: {stats.items_dropped}")
    print(f"   Current size: {stats.current_size}")
    print(f"   Max size reached: {stats.max_size_reached}")
    print()
    
    # 14. Engine Statistics
    print("14. ENGINE STATISTICS:")
    print("-" * 40)
    
    stats = engine.stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()
    
    # 15. Engine Summary
    print("15. ENGINE SUMMARY:")
    print("-" * 40)
    
    summary = engine.summary()
    print(f"   Pools: {summary['pools']}")
    print(f"   Double buffers: {summary['double_buffers']}")
    print(f"   Buffer count: {len(summary['buffers'])}")
    print()
    
    await engine.close()
    
    print("=" * 70)
    print("DEMO COMPLETE - Buffering Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
