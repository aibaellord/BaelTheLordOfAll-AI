#!/usr/bin/env python3
"""
BAEL - Concurrency Manager
Advanced concurrency control for AI agent operations.

Features:
- Async primitives
- Semaphores and locks
- Read/write locks
- Rate limiters
- Throttling
- Backpressure
- Task coordination
- Barrier synchronization
- Async pools
- Deadlock detection
"""

import asyncio
import collections
import logging
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, AsyncIterator, Awaitable, Callable, Deque, Dict,
                    Generic, List, Optional, Set, Tuple, TypeVar)

logger = logging.getLogger(__name__)


T = TypeVar('T')
R = TypeVar('R')


# =============================================================================
# ENUMS
# =============================================================================

class LockType(Enum):
    """Lock types."""
    EXCLUSIVE = "exclusive"
    SHARED = "shared"


class ThrottleMode(Enum):
    """Throttle modes."""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"


class BackpressureStrategy(Enum):
    """Backpressure strategies."""
    DROP_OLDEST = "drop_oldest"
    DROP_NEWEST = "drop_newest"
    BLOCK = "block"
    ERROR = "error"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class LockConfig:
    """Lock configuration."""
    timeout: Optional[float] = None
    max_readers: int = 100
    reentrant: bool = False


@dataclass
class ThrottleConfig:
    """Throttle configuration."""
    rate: float = 10.0  # operations per second
    burst: int = 10
    mode: ThrottleMode = ThrottleMode.TOKEN_BUCKET


@dataclass
class PoolConfig:
    """Pool configuration."""
    min_size: int = 1
    max_size: int = 10
    idle_timeout: float = 300.0


@dataclass
class ConcurrencyStats:
    """Concurrency statistics."""
    total_acquisitions: int = 0
    total_releases: int = 0
    total_timeouts: int = 0
    total_blocked: int = 0
    current_waiters: int = 0
    avg_wait_time_ms: float = 0.0


# =============================================================================
# ASYNC LOCK
# =============================================================================

class AsyncLock:
    """
    Async-compatible lock.
    """

    def __init__(self, config: Optional[LockConfig] = None):
        self._config = config or LockConfig()
        self._lock = asyncio.Lock()
        self._owner: Optional[asyncio.Task] = None
        self._count = 0
        self._stats = ConcurrencyStats()

    async def acquire(self, timeout: Optional[float] = None) -> bool:
        """Acquire the lock."""
        timeout = timeout or self._config.timeout

        if self._config.reentrant:
            current = asyncio.current_task()
            if self._owner == current:
                self._count += 1
                return True

        start = time.time()
        self._stats.current_waiters += 1

        try:
            if timeout:
                try:
                    await asyncio.wait_for(self._lock.acquire(), timeout)
                except asyncio.TimeoutError:
                    self._stats.total_timeouts += 1
                    return False
            else:
                await self._lock.acquire()

            self._owner = asyncio.current_task() if self._config.reentrant else None
            self._count = 1
            self._stats.total_acquisitions += 1

            wait_time = (time.time() - start) * 1000
            n = self._stats.total_acquisitions
            self._stats.avg_wait_time_ms = (
                (self._stats.avg_wait_time_ms * (n - 1) + wait_time) / n
            )

            return True
        finally:
            self._stats.current_waiters -= 1

    def release(self) -> None:
        """Release the lock."""
        if self._config.reentrant:
            self._count -= 1
            if self._count > 0:
                return
            self._owner = None

        self._lock.release()
        self._stats.total_releases += 1

    async def __aenter__(self) -> 'AsyncLock':
        await self.acquire()
        return self

    async def __aexit__(self, *args) -> None:
        self.release()

    @property
    def locked(self) -> bool:
        return self._lock.locked()


# =============================================================================
# READ/WRITE LOCK
# =============================================================================

class AsyncRWLock:
    """
    Async read/write lock.

    Multiple readers can hold the lock simultaneously,
    but writers get exclusive access.
    """

    def __init__(self, config: Optional[LockConfig] = None):
        self._config = config or LockConfig()
        self._read_lock = asyncio.Lock()
        self._write_lock = asyncio.Lock()
        self._readers = 0
        self._readers_lock = asyncio.Lock()
        self._stats = ConcurrencyStats()

    @asynccontextmanager
    async def read_lock(self, timeout: Optional[float] = None) -> AsyncIterator[None]:
        """Acquire a read lock."""
        timeout = timeout or self._config.timeout

        try:
            if timeout:
                await asyncio.wait_for(self._readers_lock.acquire(), timeout)
            else:
                await self._readers_lock.acquire()

            self._readers += 1
            if self._readers == 1:
                await self._write_lock.acquire()

            self._stats.total_acquisitions += 1
        finally:
            self._readers_lock.release()

        try:
            yield
        finally:
            async with self._readers_lock:
                self._readers -= 1
                if self._readers == 0:
                    self._write_lock.release()
                self._stats.total_releases += 1

    @asynccontextmanager
    async def write_lock(self, timeout: Optional[float] = None) -> AsyncIterator[None]:
        """Acquire a write lock."""
        timeout = timeout or self._config.timeout

        if timeout:
            await asyncio.wait_for(self._write_lock.acquire(), timeout)
        else:
            await self._write_lock.acquire()

        self._stats.total_acquisitions += 1

        try:
            yield
        finally:
            self._write_lock.release()
            self._stats.total_releases += 1

    @property
    def readers(self) -> int:
        return self._readers


# =============================================================================
# SEMAPHORE
# =============================================================================

class AsyncSemaphore:
    """
    Async semaphore with additional features.
    """

    def __init__(self, value: int = 1, max_value: Optional[int] = None):
        self._value = value
        self._max_value = max_value or value
        self._semaphore = asyncio.Semaphore(value)
        self._stats = ConcurrencyStats()

    async def acquire(self, timeout: Optional[float] = None) -> bool:
        """Acquire the semaphore."""
        start = time.time()
        self._stats.current_waiters += 1

        try:
            if timeout:
                try:
                    await asyncio.wait_for(self._semaphore.acquire(), timeout)
                except asyncio.TimeoutError:
                    self._stats.total_timeouts += 1
                    return False
            else:
                await self._semaphore.acquire()

            self._stats.total_acquisitions += 1
            return True
        finally:
            self._stats.current_waiters -= 1

    def release(self) -> None:
        """Release the semaphore."""
        self._semaphore.release()
        self._stats.total_releases += 1

    async def __aenter__(self) -> 'AsyncSemaphore':
        await self.acquire()
        return self

    async def __aexit__(self, *args) -> None:
        self.release()

    @property
    def available(self) -> int:
        return self._semaphore._value


# =============================================================================
# TOKEN BUCKET
# =============================================================================

class TokenBucket:
    """
    Token bucket rate limiter.
    """

    def __init__(self, rate: float, capacity: int):
        self._rate = rate  # tokens per second
        self._capacity = capacity
        self._tokens = float(capacity)
        self._last_update = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1, wait: bool = True) -> bool:
        """Acquire tokens."""
        async with self._lock:
            self._refill()

            if self._tokens >= tokens:
                self._tokens -= tokens
                return True

            if not wait:
                return False

            # Calculate wait time
            needed = tokens - self._tokens
            wait_time = needed / self._rate

            await asyncio.sleep(wait_time)
            self._refill()
            self._tokens -= tokens
            return True

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self._last_update
        self._last_update = now

        self._tokens = min(
            self._capacity,
            self._tokens + elapsed * self._rate
        )

    @property
    def available(self) -> float:
        return self._tokens


# =============================================================================
# LEAKY BUCKET
# =============================================================================

class LeakyBucket:
    """
    Leaky bucket rate limiter.
    """

    def __init__(self, rate: float, capacity: int):
        self._rate = rate  # leak rate per second
        self._capacity = capacity
        self._water = 0.0
        self._last_leak = time.time()
        self._lock = asyncio.Lock()

    async def add(self, amount: int = 1, wait: bool = True) -> bool:
        """Add to the bucket."""
        async with self._lock:
            self._leak()

            if self._water + amount <= self._capacity:
                self._water += amount
                return True

            if not wait:
                return False

            # Calculate wait time
            overflow = (self._water + amount) - self._capacity
            wait_time = overflow / self._rate

            await asyncio.sleep(wait_time)
            self._leak()
            self._water += amount
            return True

    def _leak(self) -> None:
        """Leak water based on elapsed time."""
        now = time.time()
        elapsed = now - self._last_leak
        self._last_leak = now

        self._water = max(0, self._water - elapsed * self._rate)

    @property
    def level(self) -> float:
        return self._water


# =============================================================================
# THROTTLER
# =============================================================================

class Throttler:
    """
    Request throttler with multiple algorithms.
    """

    def __init__(self, config: ThrottleConfig):
        self._config = config
        self._window_start = time.time()
        self._window_count = 0
        self._tokens = TokenBucket(config.rate, config.burst)
        self._bucket = LeakyBucket(config.rate, config.burst)
        self._lock = asyncio.Lock()
        self._requests: Deque[float] = collections.deque()

    async def acquire(self, wait: bool = True) -> bool:
        """Acquire permission to proceed."""
        if self._config.mode == ThrottleMode.TOKEN_BUCKET:
            return await self._tokens.acquire(1, wait)

        elif self._config.mode == ThrottleMode.LEAKY_BUCKET:
            return await self._bucket.add(1, wait)

        elif self._config.mode == ThrottleMode.FIXED_WINDOW:
            return await self._fixed_window(wait)

        elif self._config.mode == ThrottleMode.SLIDING_WINDOW:
            return await self._sliding_window(wait)

        return True

    async def _fixed_window(self, wait: bool) -> bool:
        """Fixed window rate limiting."""
        async with self._lock:
            now = time.time()
            window_duration = 1.0  # 1 second window

            if now - self._window_start >= window_duration:
                self._window_start = now
                self._window_count = 0

            if self._window_count < self._config.rate:
                self._window_count += 1
                return True

            if not wait:
                return False

            # Wait for next window
            wait_time = window_duration - (now - self._window_start)
            await asyncio.sleep(wait_time)

            self._window_start = time.time()
            self._window_count = 1
            return True

    async def _sliding_window(self, wait: bool) -> bool:
        """Sliding window rate limiting."""
        async with self._lock:
            now = time.time()
            window = 1.0  # 1 second window

            # Remove old requests
            while self._requests and self._requests[0] < now - window:
                self._requests.popleft()

            if len(self._requests) < self._config.rate:
                self._requests.append(now)
                return True

            if not wait:
                return False

            # Wait until oldest request expires
            oldest = self._requests[0]
            wait_time = (oldest + window) - now
            await asyncio.sleep(wait_time)

            self._requests.popleft()
            self._requests.append(time.time())
            return True


# =============================================================================
# BARRIER
# =============================================================================

class AsyncBarrier:
    """
    Async barrier for task synchronization.
    """

    def __init__(self, parties: int):
        self._parties = parties
        self._count = 0
        self._generation = 0
        self._lock = asyncio.Lock()
        self._condition = asyncio.Condition(self._lock)

    async def wait(self, timeout: Optional[float] = None) -> int:
        """Wait at the barrier."""
        async with self._condition:
            generation = self._generation
            self._count += 1
            index = self._count

            if self._count == self._parties:
                # Last one to arrive, release all
                self._count = 0
                self._generation += 1
                self._condition.notify_all()
                return 0

            # Wait for others
            try:
                await asyncio.wait_for(
                    self._wait_for_generation(generation),
                    timeout
                )
            except asyncio.TimeoutError:
                self._count -= 1
                raise

            return index

    async def _wait_for_generation(self, generation: int) -> None:
        """Wait for generation to change."""
        while self._generation == generation:
            await self._condition.wait()

    def reset(self) -> None:
        """Reset the barrier."""
        self._count = 0
        self._generation += 1


# =============================================================================
# ASYNC POOL
# =============================================================================

class AsyncPool(Generic[T]):
    """
    Async resource pool.
    """

    def __init__(
        self,
        factory: Callable[[], Awaitable[T]],
        config: Optional[PoolConfig] = None
    ):
        self._factory = factory
        self._config = config or PoolConfig()
        self._available: asyncio.Queue[T] = asyncio.Queue()
        self._in_use: Set[int] = set()  # Using id() for tracking
        self._size = 0
        self._lock = asyncio.Lock()

    async def acquire(self, timeout: Optional[float] = None) -> T:
        """Acquire a resource from the pool."""
        # Try to get from available
        try:
            item = self._available.get_nowait()
            self._in_use.add(id(item))
            return item
        except asyncio.QueueEmpty:
            pass

        # Create new if under limit
        async with self._lock:
            if self._size < self._config.max_size:
                item = await self._factory()
                self._size += 1
                self._in_use.add(id(item))
                return item

        # Wait for available
        if timeout:
            item = await asyncio.wait_for(self._available.get(), timeout)
        else:
            item = await self._available.get()

        self._in_use.add(id(item))
        return item

    async def release(self, item: T) -> None:
        """Release a resource back to the pool."""
        item_id = id(item)
        if item_id in self._in_use:
            self._in_use.remove(item_id)
            await self._available.put(item)

    @asynccontextmanager
    async def get(self, timeout: Optional[float] = None) -> AsyncIterator[T]:
        """Context manager for acquiring a resource."""
        item = await self.acquire(timeout)
        try:
            yield item
        finally:
            await self.release(item)

    @property
    def size(self) -> int:
        return self._size

    @property
    def available(self) -> int:
        return self._available.qsize()

    @property
    def in_use(self) -> int:
        return len(self._in_use)


# =============================================================================
# BACKPRESSURE QUEUE
# =============================================================================

class BackpressureQueue(Generic[T]):
    """
    Queue with backpressure handling.
    """

    def __init__(
        self,
        max_size: int = 100,
        strategy: BackpressureStrategy = BackpressureStrategy.BLOCK
    ):
        self._max_size = max_size
        self._strategy = strategy
        self._queue: Deque[T] = collections.deque()
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Condition()
        self._not_full = asyncio.Condition()

    async def put(self, item: T, timeout: Optional[float] = None) -> bool:
        """Put an item in the queue."""
        async with self._lock:
            if len(self._queue) >= self._max_size:
                if self._strategy == BackpressureStrategy.DROP_OLDEST:
                    self._queue.popleft()
                    self._queue.append(item)
                    return True

                elif self._strategy == BackpressureStrategy.DROP_NEWEST:
                    return False

                elif self._strategy == BackpressureStrategy.ERROR:
                    raise QueueFullError("Queue is full")

                elif self._strategy == BackpressureStrategy.BLOCK:
                    async with self._not_full:
                        if timeout:
                            await asyncio.wait_for(
                                self._not_full.wait(),
                                timeout
                            )
                        else:
                            await self._not_full.wait()

            self._queue.append(item)

            async with self._not_empty:
                self._not_empty.notify()

            return True

    async def get(self, timeout: Optional[float] = None) -> T:
        """Get an item from the queue."""
        async with self._not_empty:
            while not self._queue:
                if timeout:
                    await asyncio.wait_for(self._not_empty.wait(), timeout)
                else:
                    await self._not_empty.wait()

            async with self._lock:
                item = self._queue.popleft()

            async with self._not_full:
                self._not_full.notify()

            return item

    @property
    def size(self) -> int:
        return len(self._queue)

    @property
    def is_full(self) -> bool:
        return len(self._queue) >= self._max_size


# =============================================================================
# EXCEPTIONS
# =============================================================================

class ConcurrencyError(Exception):
    """Base concurrency error."""
    pass


class QueueFullError(ConcurrencyError):
    """Queue is full."""
    pass


class TimeoutError(ConcurrencyError):
    """Operation timed out."""
    pass


# =============================================================================
# CONCURRENCY MANAGER
# =============================================================================

class ConcurrencyManager:
    """
    Concurrency Manager for BAEL.

    Advanced concurrency control.
    """

    def __init__(self):
        self._locks: Dict[str, AsyncLock] = {}
        self._rw_locks: Dict[str, AsyncRWLock] = {}
        self._semaphores: Dict[str, AsyncSemaphore] = {}
        self._throttlers: Dict[str, Throttler] = {}
        self._barriers: Dict[str, AsyncBarrier] = {}
        self._pools: Dict[str, AsyncPool] = {}
        self._lock = threading.RLock()

    # -------------------------------------------------------------------------
    # LOCKS
    # -------------------------------------------------------------------------

    def get_lock(
        self,
        name: str,
        config: Optional[LockConfig] = None
    ) -> AsyncLock:
        """Get or create a named lock."""
        with self._lock:
            if name not in self._locks:
                self._locks[name] = AsyncLock(config)
            return self._locks[name]

    def get_rw_lock(
        self,
        name: str,
        config: Optional[LockConfig] = None
    ) -> AsyncRWLock:
        """Get or create a named read/write lock."""
        with self._lock:
            if name not in self._rw_locks:
                self._rw_locks[name] = AsyncRWLock(config)
            return self._rw_locks[name]

    # -------------------------------------------------------------------------
    # SEMAPHORES
    # -------------------------------------------------------------------------

    def get_semaphore(
        self,
        name: str,
        value: int = 1
    ) -> AsyncSemaphore:
        """Get or create a named semaphore."""
        with self._lock:
            if name not in self._semaphores:
                self._semaphores[name] = AsyncSemaphore(value)
            return self._semaphores[name]

    # -------------------------------------------------------------------------
    # THROTTLING
    # -------------------------------------------------------------------------

    def get_throttler(
        self,
        name: str,
        config: Optional[ThrottleConfig] = None
    ) -> Throttler:
        """Get or create a named throttler."""
        with self._lock:
            if name not in self._throttlers:
                self._throttlers[name] = Throttler(config or ThrottleConfig())
            return self._throttlers[name]

    async def throttle(
        self,
        name: str,
        rate: float = 10.0,
        wait: bool = True
    ) -> bool:
        """Throttle an operation."""
        throttler = self.get_throttler(name, ThrottleConfig(rate=rate))
        return await throttler.acquire(wait)

    # -------------------------------------------------------------------------
    # BARRIERS
    # -------------------------------------------------------------------------

    def get_barrier(self, name: str, parties: int) -> AsyncBarrier:
        """Get or create a named barrier."""
        with self._lock:
            if name not in self._barriers:
                self._barriers[name] = AsyncBarrier(parties)
            return self._barriers[name]

    # -------------------------------------------------------------------------
    # POOLS
    # -------------------------------------------------------------------------

    def create_pool(
        self,
        name: str,
        factory: Callable[[], Awaitable[T]],
        config: Optional[PoolConfig] = None
    ) -> AsyncPool[T]:
        """Create a named resource pool."""
        pool = AsyncPool(factory, config)
        with self._lock:
            self._pools[name] = pool
        return pool

    def get_pool(self, name: str) -> Optional[AsyncPool]:
        """Get a pool by name."""
        with self._lock:
            return self._pools.get(name)

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    @asynccontextmanager
    async def limit_concurrency(
        self,
        name: str,
        max_concurrent: int
    ) -> AsyncIterator[None]:
        """Limit concurrent executions."""
        sem = self.get_semaphore(f"_limit_{name}", max_concurrent)
        async with sem:
            yield

    async def run_with_limit(
        self,
        funcs: List[Callable[[], Awaitable[T]]],
        max_concurrent: int
    ) -> List[T]:
        """Run functions with concurrency limit."""
        sem = asyncio.Semaphore(max_concurrent)

        async def limited(func):
            async with sem:
                return await func()

        return await asyncio.gather(*[limited(f) for f in funcs])


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Concurrency Manager."""
    print("=" * 70)
    print("BAEL - CONCURRENCY MANAGER DEMO")
    print("Advanced Concurrency Control for AI Agents")
    print("=" * 70)
    print()

    manager = ConcurrencyManager()

    # 1. Async Lock
    print("1. ASYNC LOCK:")
    print("-" * 40)

    lock = manager.get_lock("resource")

    async with lock:
        print("   Lock acquired")
        await asyncio.sleep(0.1)
    print("   Lock released")
    print()

    # 2. Read/Write Lock
    print("2. READ/WRITE LOCK:")
    print("-" * 40)

    rw_lock = manager.get_rw_lock("data")

    async def reader(id: int):
        async with rw_lock.read_lock():
            print(f"   Reader {id} reading...")
            await asyncio.sleep(0.1)

    async def writer(id: int):
        async with rw_lock.write_lock():
            print(f"   Writer {id} writing...")
            await asyncio.sleep(0.1)

    await asyncio.gather(
        reader(1),
        reader(2),
        writer(1),
        reader(3)
    )
    print()

    # 3. Semaphore
    print("3. SEMAPHORE:")
    print("-" * 40)

    sem = manager.get_semaphore("connections", 2)

    async def use_connection(id: int):
        async with sem:
            print(f"   Connection {id} active (available: {sem.available})")
            await asyncio.sleep(0.1)

    await asyncio.gather(*[use_connection(i) for i in range(4)])
    print()

    # 4. Token Bucket
    print("4. TOKEN BUCKET:")
    print("-" * 40)

    bucket = TokenBucket(rate=5.0, capacity=3)

    for i in range(5):
        start = time.time()
        await bucket.acquire()
        elapsed = (time.time() - start) * 1000
        print(f"   Request {i+1}: {elapsed:.1f}ms wait")
    print()

    # 5. Throttler
    print("5. THROTTLER:")
    print("-" * 40)

    throttler = manager.get_throttler("api", ThrottleConfig(rate=10.0))

    start = time.time()
    for i in range(5):
        await throttler.acquire()
    elapsed = (time.time() - start) * 1000

    print(f"   5 requests throttled in {elapsed:.1f}ms")
    print()

    # 6. Barrier
    print("6. BARRIER:")
    print("-" * 40)

    barrier = manager.get_barrier("sync_point", 3)

    async def worker(id: int):
        print(f"   Worker {id} reached barrier")
        position = await barrier.wait()
        print(f"   Worker {id} passed (position: {position})")

    await asyncio.gather(*[worker(i) for i in range(3)])
    print()

    # 7. Async Pool
    print("7. ASYNC POOL:")
    print("-" * 40)

    counter = {"count": 0}

    async def create_resource():
        counter["count"] += 1
        return f"resource_{counter['count']}"

    pool = manager.create_pool(
        "resources",
        create_resource,
        PoolConfig(max_size=2)
    )

    async with pool.get() as r1:
        async with pool.get() as r2:
            print(f"   Acquired: {r1}, {r2}")
            print(f"   Pool size: {pool.size}, in use: {pool.in_use}")

    print(f"   After release - available: {pool.available}")
    print()

    # 8. Backpressure Queue
    print("8. BACKPRESSURE QUEUE:")
    print("-" * 40)

    queue = BackpressureQueue(max_size=3, strategy=BackpressureStrategy.DROP_OLDEST)

    for i in range(5):
        result = await queue.put(f"item_{i}")
        print(f"   Put item_{i}: size={queue.size}")

    print(f"   Queue contents: ", end="")
    while queue.size > 0:
        item = await queue.get()
        print(f"{item} ", end="")
    print()
    print()

    # 9. Limited Concurrency
    print("9. LIMITED CONCURRENCY:")
    print("-" * 40)

    async def task(id: int):
        print(f"   Task {id} started")
        await asyncio.sleep(0.1)
        print(f"   Task {id} finished")
        return id

    results = await manager.run_with_limit(
        [lambda i=i: task(i) for i in range(4)],
        max_concurrent=2
    )
    print(f"   Results: {results}")
    print()

    # 10. Reentrant Lock
    print("10. REENTRANT LOCK:")
    print("-" * 40)

    reentrant = AsyncLock(LockConfig(reentrant=True))

    async def nested_lock():
        async with reentrant:
            print("   Outer lock acquired")
            async with reentrant:
                print("   Inner lock acquired (reentrant)")

    await nested_lock()
    print()

    # 11. Sliding Window Throttle
    print("11. SLIDING WINDOW THROTTLE:")
    print("-" * 40)

    sliding = Throttler(ThrottleConfig(
        rate=5.0,
        mode=ThrottleMode.SLIDING_WINDOW
    ))

    allowed = 0
    for i in range(10):
        if await sliding.acquire(wait=False):
            allowed += 1

    print(f"   Allowed {allowed}/10 requests (limit: 5/s)")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Concurrency Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
