#!/usr/bin/env python3
"""
BAEL - Lock Manager
Advanced distributed locking for AI agent operations.

Features:
- Mutex locks
- Read-write locks
- Distributed locks
- Lock timeouts
- Deadlock detection
- Lock queuing
- Fair locking
- Reentrant locks
- Lock monitoring
- Automatic cleanup
"""

import asyncio
import collections
import threading
import time
import uuid
import weakref
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    TypeVar)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class LockType(Enum):
    """Lock types."""
    EXCLUSIVE = "exclusive"
    SHARED = "shared"
    READ = "read"
    WRITE = "write"


class LockState(Enum):
    """Lock states."""
    FREE = "free"
    LOCKED = "locked"
    WAITING = "waiting"


class LockResult(Enum):
    """Lock acquisition result."""
    ACQUIRED = "acquired"
    TIMEOUT = "timeout"
    DEADLOCK = "deadlock"
    ALREADY_HELD = "already_held"
    ERROR = "error"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class LockInfo:
    """Lock information."""
    lock_id: str
    resource: str
    lock_type: LockType
    owner: str
    acquired_at: datetime
    expires_at: Optional[datetime] = None
    reentrant_count: int = 1


@dataclass
class LockRequest:
    """A lock request."""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    resource: str = ""
    lock_type: LockType = LockType.EXCLUSIVE
    owner: str = ""
    timeout: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class LockStats:
    """Lock statistics."""
    total_acquired: int = 0
    total_released: int = 0
    total_timeouts: int = 0
    total_deadlocks: int = 0
    current_locks: int = 0
    current_waiting: int = 0
    avg_wait_time_ms: float = 0.0


@dataclass
class WaitGraphNode:
    """Node in wait-for graph for deadlock detection."""
    owner: str
    waiting_for: Set[str] = field(default_factory=set)


# =============================================================================
# LOCK IMPLEMENTATIONS
# =============================================================================

class Lock(ABC):
    """Abstract lock interface."""

    @abstractmethod
    async def acquire(
        self,
        owner: str,
        timeout: Optional[float] = None
    ) -> LockResult:
        pass

    @abstractmethod
    async def release(self, owner: str) -> bool:
        pass

    @abstractmethod
    def is_locked(self) -> bool:
        pass

    @abstractmethod
    def get_owner(self) -> Optional[str]:
        pass


class MutexLock(Lock):
    """
    Exclusive mutex lock.
    """

    def __init__(
        self,
        resource: str,
        reentrant: bool = False
    ):
        self.lock_id = str(uuid.uuid4())
        self.resource = resource
        self.reentrant = reentrant

        self._owner: Optional[str] = None
        self._reentrant_count = 0
        self._lock = asyncio.Lock()
        self._condition = asyncio.Condition()
        self._acquired_at: Optional[datetime] = None
        self._expires_at: Optional[datetime] = None

    async def acquire(
        self,
        owner: str,
        timeout: Optional[float] = None
    ) -> LockResult:
        """Acquire the lock."""
        async with self._condition:
            # Check reentrant
            if self.reentrant and self._owner == owner:
                self._reentrant_count += 1
                return LockResult.ALREADY_HELD

            # Wait for lock
            start = time.time()

            while self._owner is not None:
                if timeout is not None:
                    remaining = timeout - (time.time() - start)
                    if remaining <= 0:
                        return LockResult.TIMEOUT

                    try:
                        await asyncio.wait_for(
                            self._condition.wait(),
                            timeout=remaining
                        )
                    except asyncio.TimeoutError:
                        return LockResult.TIMEOUT
                else:
                    await self._condition.wait()

            # Acquire
            self._owner = owner
            self._reentrant_count = 1
            self._acquired_at = datetime.utcnow()

            return LockResult.ACQUIRED

    async def release(self, owner: str) -> bool:
        """Release the lock."""
        async with self._condition:
            if self._owner != owner:
                return False

            if self.reentrant and self._reentrant_count > 1:
                self._reentrant_count -= 1
                return True

            self._owner = None
            self._reentrant_count = 0
            self._acquired_at = None
            self._condition.notify()

            return True

    def is_locked(self) -> bool:
        return self._owner is not None

    def get_owner(self) -> Optional[str]:
        return self._owner

    def get_info(self) -> Optional[LockInfo]:
        if not self._owner:
            return None

        return LockInfo(
            lock_id=self.lock_id,
            resource=self.resource,
            lock_type=LockType.EXCLUSIVE,
            owner=self._owner,
            acquired_at=self._acquired_at or datetime.utcnow(),
            reentrant_count=self._reentrant_count
        )


class ReadWriteLock(Lock):
    """
    Read-write lock allowing multiple readers or single writer.
    """

    def __init__(self, resource: str):
        self.lock_id = str(uuid.uuid4())
        self.resource = resource

        self._readers: Set[str] = set()
        self._writer: Optional[str] = None
        self._condition = asyncio.Condition()
        self._acquired_at: Optional[datetime] = None

    async def acquire_read(
        self,
        owner: str,
        timeout: Optional[float] = None
    ) -> LockResult:
        """Acquire read lock."""
        async with self._condition:
            start = time.time()

            while self._writer is not None:
                if timeout is not None:
                    remaining = timeout - (time.time() - start)
                    if remaining <= 0:
                        return LockResult.TIMEOUT

                    try:
                        await asyncio.wait_for(
                            self._condition.wait(),
                            timeout=remaining
                        )
                    except asyncio.TimeoutError:
                        return LockResult.TIMEOUT
                else:
                    await self._condition.wait()

            self._readers.add(owner)

            if not self._acquired_at:
                self._acquired_at = datetime.utcnow()

            return LockResult.ACQUIRED

    async def acquire_write(
        self,
        owner: str,
        timeout: Optional[float] = None
    ) -> LockResult:
        """Acquire write lock."""
        async with self._condition:
            start = time.time()

            while self._writer is not None or self._readers:
                if timeout is not None:
                    remaining = timeout - (time.time() - start)
                    if remaining <= 0:
                        return LockResult.TIMEOUT

                    try:
                        await asyncio.wait_for(
                            self._condition.wait(),
                            timeout=remaining
                        )
                    except asyncio.TimeoutError:
                        return LockResult.TIMEOUT
                else:
                    await self._condition.wait()

            self._writer = owner
            self._acquired_at = datetime.utcnow()

            return LockResult.ACQUIRED

    async def acquire(
        self,
        owner: str,
        timeout: Optional[float] = None
    ) -> LockResult:
        """Acquire exclusive (write) lock."""
        return await self.acquire_write(owner, timeout)

    async def release_read(self, owner: str) -> bool:
        """Release read lock."""
        async with self._condition:
            if owner not in self._readers:
                return False

            self._readers.remove(owner)

            if not self._readers and not self._writer:
                self._acquired_at = None

            self._condition.notify_all()
            return True

    async def release_write(self, owner: str) -> bool:
        """Release write lock."""
        async with self._condition:
            if self._writer != owner:
                return False

            self._writer = None
            self._acquired_at = None
            self._condition.notify_all()

            return True

    async def release(self, owner: str) -> bool:
        """Release any held lock."""
        if await self.release_write(owner):
            return True
        return await self.release_read(owner)

    def is_locked(self) -> bool:
        return self._writer is not None or bool(self._readers)

    def get_owner(self) -> Optional[str]:
        return self._writer

    def get_readers(self) -> Set[str]:
        return self._readers.copy()

    def reader_count(self) -> int:
        return len(self._readers)


class SemaphoreLock:
    """
    Counting semaphore lock.
    """

    def __init__(self, resource: str, max_concurrent: int = 1):
        self.lock_id = str(uuid.uuid4())
        self.resource = resource
        self.max_concurrent = max_concurrent

        self._holders: Set[str] = set()
        self._condition = asyncio.Condition()

    async def acquire(
        self,
        owner: str,
        timeout: Optional[float] = None
    ) -> LockResult:
        """Acquire semaphore slot."""
        async with self._condition:
            start = time.time()

            while len(self._holders) >= self.max_concurrent:
                if timeout is not None:
                    remaining = timeout - (time.time() - start)
                    if remaining <= 0:
                        return LockResult.TIMEOUT

                    try:
                        await asyncio.wait_for(
                            self._condition.wait(),
                            timeout=remaining
                        )
                    except asyncio.TimeoutError:
                        return LockResult.TIMEOUT
                else:
                    await self._condition.wait()

            self._holders.add(owner)
            return LockResult.ACQUIRED

    async def release(self, owner: str) -> bool:
        """Release semaphore slot."""
        async with self._condition:
            if owner not in self._holders:
                return False

            self._holders.remove(owner)
            self._condition.notify()

            return True

    def available(self) -> int:
        return self.max_concurrent - len(self._holders)

    def is_full(self) -> bool:
        return len(self._holders) >= self.max_concurrent


class FairLock(Lock):
    """
    Fair lock with FIFO ordering.
    """

    def __init__(self, resource: str):
        self.lock_id = str(uuid.uuid4())
        self.resource = resource

        self._owner: Optional[str] = None
        self._queue: collections.deque = collections.deque()
        self._waiters: Dict[str, asyncio.Event] = {}
        self._lock = asyncio.Lock()

    async def acquire(
        self,
        owner: str,
        timeout: Optional[float] = None
    ) -> LockResult:
        """Acquire lock in FIFO order."""
        event = asyncio.Event()

        async with self._lock:
            if self._owner is None and not self._queue:
                self._owner = owner
                return LockResult.ACQUIRED

            self._queue.append(owner)
            self._waiters[owner] = event

        # Wait for our turn
        try:
            if timeout:
                await asyncio.wait_for(event.wait(), timeout=timeout)
            else:
                await event.wait()

            return LockResult.ACQUIRED

        except asyncio.TimeoutError:
            async with self._lock:
                if owner in self._queue:
                    self._queue.remove(owner)
                self._waiters.pop(owner, None)
            return LockResult.TIMEOUT

    async def release(self, owner: str) -> bool:
        """Release lock and notify next in queue."""
        async with self._lock:
            if self._owner != owner:
                return False

            if self._queue:
                next_owner = self._queue.popleft()
                self._owner = next_owner

                if next_owner in self._waiters:
                    self._waiters[next_owner].set()
                    del self._waiters[next_owner]
            else:
                self._owner = None

            return True

    def is_locked(self) -> bool:
        return self._owner is not None

    def get_owner(self) -> Optional[str]:
        return self._owner

    def queue_length(self) -> int:
        return len(self._queue)


# =============================================================================
# DEADLOCK DETECTOR
# =============================================================================

class DeadlockDetector:
    """
    Deadlock detection using wait-for graph.
    """

    def __init__(self):
        self._graph: Dict[str, Set[str]] = defaultdict(set)
        self._lock = threading.RLock()

    def add_wait(self, waiter: str, holder: str) -> bool:
        """
        Add wait edge. Returns True if deadlock detected.
        """
        with self._lock:
            self._graph[waiter].add(holder)
            return self._has_cycle()

    def remove_wait(self, waiter: str, holder: Optional[str] = None) -> None:
        """Remove wait edge."""
        with self._lock:
            if holder:
                self._graph[waiter].discard(holder)
            else:
                self._graph.pop(waiter, None)

    def clear(self, owner: str) -> None:
        """Clear all edges for owner."""
        with self._lock:
            self._graph.pop(owner, None)

            for waiting_for in self._graph.values():
                waiting_for.discard(owner)

    def _has_cycle(self) -> bool:
        """Check for cycle using DFS."""
        visited = set()
        rec_stack = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in self._graph.get(node, set()):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for node in list(self._graph.keys()):
            if node not in visited:
                if dfs(node):
                    return True

        return False

    def find_cycle(self) -> Optional[List[str]]:
        """Find a cycle if one exists."""
        with self._lock:
            visited = set()
            path = []

            def dfs(node: str) -> Optional[List[str]]:
                visited.add(node)
                path.append(node)

                for neighbor in self._graph.get(node, set()):
                    if neighbor in path:
                        # Found cycle
                        idx = path.index(neighbor)
                        return path[idx:] + [neighbor]

                    if neighbor not in visited:
                        result = dfs(neighbor)
                        if result:
                            return result

                path.pop()
                return None

            for node in list(self._graph.keys()):
                if node not in visited:
                    cycle = dfs(node)
                    if cycle:
                        return cycle

            return None


# =============================================================================
# LOCK MANAGER
# =============================================================================

class LockManager:
    """
    Lock Manager for BAEL.

    Advanced lock management.
    """

    def __init__(
        self,
        default_timeout: float = 30.0,
        enable_deadlock_detection: bool = True
    ):
        self.default_timeout = default_timeout
        self.enable_deadlock_detection = enable_deadlock_detection

        self._locks: Dict[str, Lock] = {}
        self._rw_locks: Dict[str, ReadWriteLock] = {}
        self._semaphores: Dict[str, SemaphoreLock] = {}
        self._fair_locks: Dict[str, FairLock] = {}

        self._owner_locks: Dict[str, Set[str]] = defaultdict(set)
        self._deadlock_detector = DeadlockDetector()

        self._stats = LockStats()
        self._lock = asyncio.Lock()

    # -------------------------------------------------------------------------
    # MUTEX LOCKS
    # -------------------------------------------------------------------------

    async def acquire(
        self,
        resource: str,
        owner: str,
        timeout: Optional[float] = None,
        reentrant: bool = False
    ) -> LockResult:
        """Acquire exclusive lock on resource."""
        async with self._lock:
            if resource not in self._locks:
                self._locks[resource] = MutexLock(resource, reentrant)

            lock = self._locks[resource]

        # Check for deadlock
        if self.enable_deadlock_detection:
            current_owner = lock.get_owner()
            if current_owner and current_owner != owner:
                if self._deadlock_detector.add_wait(owner, current_owner):
                    self._stats.total_deadlocks += 1
                    self._deadlock_detector.remove_wait(owner)
                    return LockResult.DEADLOCK

        self._stats.current_waiting += 1
        start = time.time()

        result = await lock.acquire(
            owner,
            timeout=timeout or self.default_timeout
        )

        wait_time = (time.time() - start) * 1000
        self._stats.current_waiting -= 1

        # Update stats
        if result == LockResult.ACQUIRED:
            self._stats.total_acquired += 1
            self._stats.current_locks += 1
            self._owner_locks[owner].add(resource)

            n = self._stats.total_acquired
            self._stats.avg_wait_time_ms = (
                (self._stats.avg_wait_time_ms * (n - 1) + wait_time) / n
            )
        elif result == LockResult.TIMEOUT:
            self._stats.total_timeouts += 1

        if self.enable_deadlock_detection:
            self._deadlock_detector.remove_wait(owner)

        return result

    async def release(self, resource: str, owner: str) -> bool:
        """Release lock on resource."""
        async with self._lock:
            lock = self._locks.get(resource)

        if not lock:
            return False

        result = await lock.release(owner)

        if result:
            self._stats.total_released += 1
            self._stats.current_locks -= 1
            self._owner_locks[owner].discard(resource)

            if self.enable_deadlock_detection:
                self._deadlock_detector.clear(owner)

        return result

    # -------------------------------------------------------------------------
    # READ-WRITE LOCKS
    # -------------------------------------------------------------------------

    async def acquire_read(
        self,
        resource: str,
        owner: str,
        timeout: Optional[float] = None
    ) -> LockResult:
        """Acquire read lock."""
        async with self._lock:
            if resource not in self._rw_locks:
                self._rw_locks[resource] = ReadWriteLock(resource)

            lock = self._rw_locks[resource]

        result = await lock.acquire_read(owner, timeout or self.default_timeout)

        if result == LockResult.ACQUIRED:
            self._stats.total_acquired += 1
            self._owner_locks[owner].add(f"{resource}:read")

        return result

    async def acquire_write(
        self,
        resource: str,
        owner: str,
        timeout: Optional[float] = None
    ) -> LockResult:
        """Acquire write lock."""
        async with self._lock:
            if resource not in self._rw_locks:
                self._rw_locks[resource] = ReadWriteLock(resource)

            lock = self._rw_locks[resource]

        result = await lock.acquire_write(owner, timeout or self.default_timeout)

        if result == LockResult.ACQUIRED:
            self._stats.total_acquired += 1
            self._owner_locks[owner].add(f"{resource}:write")

        return result

    async def release_read(self, resource: str, owner: str) -> bool:
        """Release read lock."""
        async with self._lock:
            lock = self._rw_locks.get(resource)

        if not lock:
            return False

        result = await lock.release_read(owner)

        if result:
            self._stats.total_released += 1
            self._owner_locks[owner].discard(f"{resource}:read")

        return result

    async def release_write(self, resource: str, owner: str) -> bool:
        """Release write lock."""
        async with self._lock:
            lock = self._rw_locks.get(resource)

        if not lock:
            return False

        result = await lock.release_write(owner)

        if result:
            self._stats.total_released += 1
            self._owner_locks[owner].discard(f"{resource}:write")

        return result

    # -------------------------------------------------------------------------
    # SEMAPHORES
    # -------------------------------------------------------------------------

    def create_semaphore(self, resource: str, max_concurrent: int) -> SemaphoreLock:
        """Create a semaphore."""
        sem = SemaphoreLock(resource, max_concurrent)
        self._semaphores[resource] = sem
        return sem

    async def acquire_semaphore(
        self,
        resource: str,
        owner: str,
        timeout: Optional[float] = None
    ) -> LockResult:
        """Acquire semaphore slot."""
        sem = self._semaphores.get(resource)
        if not sem:
            return LockResult.ERROR

        return await sem.acquire(owner, timeout or self.default_timeout)

    async def release_semaphore(self, resource: str, owner: str) -> bool:
        """Release semaphore slot."""
        sem = self._semaphores.get(resource)
        if not sem:
            return False
        return await sem.release(owner)

    # -------------------------------------------------------------------------
    # FAIR LOCKS
    # -------------------------------------------------------------------------

    async def acquire_fair(
        self,
        resource: str,
        owner: str,
        timeout: Optional[float] = None
    ) -> LockResult:
        """Acquire fair lock (FIFO order)."""
        async with self._lock:
            if resource not in self._fair_locks:
                self._fair_locks[resource] = FairLock(resource)

            lock = self._fair_locks[resource]

        return await lock.acquire(owner, timeout or self.default_timeout)

    async def release_fair(self, resource: str, owner: str) -> bool:
        """Release fair lock."""
        async with self._lock:
            lock = self._fair_locks.get(resource)

        if not lock:
            return False

        return await lock.release(owner)

    # -------------------------------------------------------------------------
    # CONTEXT MANAGERS
    # -------------------------------------------------------------------------

    def lock(
        self,
        resource: str,
        owner: str,
        timeout: Optional[float] = None
    ):
        """Context manager for exclusive lock."""
        return LockContext(self, resource, owner, timeout)

    def read_lock(
        self,
        resource: str,
        owner: str,
        timeout: Optional[float] = None
    ):
        """Context manager for read lock."""
        return ReadLockContext(self, resource, owner, timeout)

    def write_lock(
        self,
        resource: str,
        owner: str,
        timeout: Optional[float] = None
    ):
        """Context manager for write lock."""
        return WriteLockContext(self, resource, owner, timeout)

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def get_owner_locks(self, owner: str) -> Set[str]:
        """Get all locks held by owner."""
        return self._owner_locks.get(owner, set()).copy()

    async def release_all(self, owner: str) -> int:
        """Release all locks held by owner."""
        locks = self.get_owner_locks(owner)
        released = 0

        for resource in locks:
            if resource.endswith(":read"):
                base = resource[:-5]
                if await self.release_read(base, owner):
                    released += 1
            elif resource.endswith(":write"):
                base = resource[:-6]
                if await self.release_write(base, owner):
                    released += 1
            else:
                if await self.release(resource, owner):
                    released += 1

        return released

    def is_locked(self, resource: str) -> bool:
        """Check if resource is locked."""
        lock = self._locks.get(resource)
        if lock:
            return lock.is_locked()

        rw_lock = self._rw_locks.get(resource)
        if rw_lock:
            return rw_lock.is_locked()

        return False

    def get_lock_info(self, resource: str) -> Optional[LockInfo]:
        """Get lock info for resource."""
        lock = self._locks.get(resource)
        if lock and isinstance(lock, MutexLock):
            return lock.get_info()
        return None

    def get_stats(self) -> LockStats:
        """Get lock statistics."""
        return LockStats(
            total_acquired=self._stats.total_acquired,
            total_released=self._stats.total_released,
            total_timeouts=self._stats.total_timeouts,
            total_deadlocks=self._stats.total_deadlocks,
            current_locks=self._stats.current_locks,
            current_waiting=self._stats.current_waiting,
            avg_wait_time_ms=self._stats.avg_wait_time_ms
        )

    def detect_deadlock(self) -> Optional[List[str]]:
        """Detect deadlock cycle."""
        return self._deadlock_detector.find_cycle()


# =============================================================================
# CONTEXT MANAGERS
# =============================================================================

class LockContext:
    """Context manager for exclusive lock."""

    def __init__(
        self,
        manager: LockManager,
        resource: str,
        owner: str,
        timeout: Optional[float]
    ):
        self.manager = manager
        self.resource = resource
        self.owner = owner
        self.timeout = timeout
        self._acquired = False

    async def __aenter__(self) -> LockResult:
        result = await self.manager.acquire(
            self.resource,
            self.owner,
            self.timeout
        )
        self._acquired = result == LockResult.ACQUIRED
        return result

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._acquired:
            await self.manager.release(self.resource, self.owner)


class ReadLockContext:
    """Context manager for read lock."""

    def __init__(
        self,
        manager: LockManager,
        resource: str,
        owner: str,
        timeout: Optional[float]
    ):
        self.manager = manager
        self.resource = resource
        self.owner = owner
        self.timeout = timeout
        self._acquired = False

    async def __aenter__(self) -> LockResult:
        result = await self.manager.acquire_read(
            self.resource,
            self.owner,
            self.timeout
        )
        self._acquired = result == LockResult.ACQUIRED
        return result

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._acquired:
            await self.manager.release_read(self.resource, self.owner)


class WriteLockContext:
    """Context manager for write lock."""

    def __init__(
        self,
        manager: LockManager,
        resource: str,
        owner: str,
        timeout: Optional[float]
    ):
        self.manager = manager
        self.resource = resource
        self.owner = owner
        self.timeout = timeout
        self._acquired = False

    async def __aenter__(self) -> LockResult:
        result = await self.manager.acquire_write(
            self.resource,
            self.owner,
            self.timeout
        )
        self._acquired = result == LockResult.ACQUIRED
        return result

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._acquired:
            await self.manager.release_write(self.resource, self.owner)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Lock Manager."""
    print("=" * 70)
    print("BAEL - LOCK MANAGER DEMO")
    print("Advanced Locking for AI Agents")
    print("=" * 70)
    print()

    manager = LockManager(default_timeout=5.0)

    # 1. Basic Exclusive Lock
    print("1. EXCLUSIVE LOCK:")
    print("-" * 40)

    result = await manager.acquire("resource1", "owner1")
    print(f"   Owner1 acquired: {result.value}")

    result = await manager.acquire("resource1", "owner2", timeout=0.1)
    print(f"   Owner2 acquired: {result.value}")

    released = await manager.release("resource1", "owner1")
    print(f"   Owner1 released: {released}")

    result = await manager.acquire("resource1", "owner2", timeout=0.1)
    print(f"   Owner2 acquired: {result.value}")
    await manager.release("resource1", "owner2")
    print()

    # 2. Context Manager
    print("2. CONTEXT MANAGER:")
    print("-" * 40)

    async with manager.lock("resource2", "agent1") as result:
        print(f"   Acquired in context: {result.value}")
        print(f"   Is locked: {manager.is_locked('resource2')}")

    print(f"   After context: {manager.is_locked('resource2')}")
    print()

    # 3. Read-Write Lock
    print("3. READ-WRITE LOCK:")
    print("-" * 40)

    result1 = await manager.acquire_read("data", "reader1")
    result2 = await manager.acquire_read("data", "reader2")
    print(f"   Reader1: {result1.value}, Reader2: {result2.value}")

    # Writer should timeout
    result = await manager.acquire_write("data", "writer1", timeout=0.1)
    print(f"   Writer (with readers): {result.value}")

    await manager.release_read("data", "reader1")
    await manager.release_read("data", "reader2")

    result = await manager.acquire_write("data", "writer1", timeout=0.1)
    print(f"   Writer (after readers): {result.value}")
    await manager.release_write("data", "writer1")
    print()

    # 4. Reentrant Lock
    print("4. REENTRANT LOCK:")
    print("-" * 40)

    result1 = await manager.acquire("reentrant_res", "owner1", reentrant=True)
    print(f"   First acquire: {result1.value}")

    result2 = await manager.acquire("reentrant_res", "owner1", reentrant=True)
    print(f"   Second acquire: {result2.value}")

    info = manager.get_lock_info("reentrant_res")
    if info:
        print(f"   Reentrant count: {info.reentrant_count}")

    await manager.release("reentrant_res", "owner1")
    await manager.release("reentrant_res", "owner1")
    print()

    # 5. Semaphore
    print("5. SEMAPHORE:")
    print("-" * 40)

    manager.create_semaphore("pool", max_concurrent=2)

    r1 = await manager.acquire_semaphore("pool", "user1")
    r2 = await manager.acquire_semaphore("pool", "user2")
    print(f"   User1: {r1.value}, User2: {r2.value}")

    r3 = await manager.acquire_semaphore("pool", "user3", timeout=0.1)
    print(f"   User3 (pool full): {r3.value}")

    await manager.release_semaphore("pool", "user1")
    r3 = await manager.acquire_semaphore("pool", "user3", timeout=0.1)
    print(f"   User3 (after release): {r3.value}")

    await manager.release_semaphore("pool", "user2")
    await manager.release_semaphore("pool", "user3")
    print()

    # 6. Fair Lock
    print("6. FAIR LOCK (FIFO):")
    print("-" * 40)

    async def fair_worker(name: str, delay: float):
        await asyncio.sleep(delay)
        result = await manager.acquire_fair("fair_res", name)
        print(f"   {name} acquired: {result.value}")
        await asyncio.sleep(0.1)
        await manager.release_fair("fair_res", name)

    await asyncio.gather(
        fair_worker("First", 0),
        fair_worker("Second", 0.01),
        fair_worker("Third", 0.02)
    )
    print()

    # 7. Concurrent Access
    print("7. CONCURRENT ACCESS:")
    print("-" * 40)

    async def worker(name: str, resource: str):
        async with manager.lock(resource, name, timeout=1.0) as result:
            if result == LockResult.ACQUIRED:
                await asyncio.sleep(0.1)
                return f"{name}: success"
            return f"{name}: {result.value}"

    results = await asyncio.gather(*[
        worker(f"worker_{i}", "shared") for i in range(3)
    ])

    for r in results:
        print(f"   {r}")
    print()

    # 8. Lock Timeout
    print("8. LOCK TIMEOUT:")
    print("-" * 40)

    await manager.acquire("timeout_test", "holder")

    start = time.time()
    result = await manager.acquire("timeout_test", "waiter", timeout=0.5)
    elapsed = time.time() - start

    print(f"   Result: {result.value}")
    print(f"   Wait time: {elapsed:.2f}s")

    await manager.release("timeout_test", "holder")
    print()

    # 9. Owner's Locks
    print("9. OWNER'S LOCKS:")
    print("-" * 40)

    await manager.acquire("res_a", "multi_owner")
    await manager.acquire("res_b", "multi_owner")
    await manager.acquire_read("res_c", "multi_owner")

    locks = manager.get_owner_locks("multi_owner")
    print(f"   Locks held: {locks}")

    released = await manager.release_all("multi_owner")
    print(f"   Released: {released}")
    print()

    # 10. Lock Statistics
    print("10. LOCK STATISTICS:")
    print("-" * 40)

    stats = manager.get_stats()
    print(f"   Total acquired: {stats.total_acquired}")
    print(f"   Total released: {stats.total_released}")
    print(f"   Total timeouts: {stats.total_timeouts}")
    print(f"   Avg wait time: {stats.avg_wait_time_ms:.2f}ms")
    print()

    # 11. Deadlock Detection
    print("11. DEADLOCK DETECTION:")
    print("-" * 40)

    detector = DeadlockDetector()

    # Create deadlock scenario: A waits for B, B waits for A
    detector.add_wait("A", "B")
    has_deadlock = detector.add_wait("B", "A")

    print(f"   Deadlock detected: {has_deadlock}")

    cycle = detector.find_cycle()
    if cycle:
        print(f"   Cycle: {' -> '.join(cycle)}")
    print()

    # 12. Read-Write Context
    print("12. READ-WRITE CONTEXT:")
    print("-" * 40)

    async with manager.read_lock("doc", "reader") as result:
        print(f"   Read lock: {result.value}")

    async with manager.write_lock("doc", "writer") as result:
        print(f"   Write lock: {result.value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Lock Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
