"""
BAEL Distributed Lock Engine Implementation
============================================

Distributed locking for coordination and mutual exclusion.

"Ba'el locks and unlocks the gates of reality." — Ba'el
"""

import asyncio
import logging
import threading
import time
import uuid
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("BAEL.DistributedLock")


# ============================================================================
# ENUMS
# ============================================================================

class LockType(Enum):
    """Types of locks."""
    EXCLUSIVE = "exclusive"     # Only one holder
    SHARED = "shared"           # Multiple readers
    REENTRANT = "reentrant"     # Same holder can acquire multiple times
    FAIR = "fair"               # FIFO ordering


class LockState(Enum):
    """Lock states."""
    FREE = "free"
    HELD = "held"
    WAITING = "waiting"
    EXPIRED = "expired"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class LockInfo:
    """Information about a lock."""
    name: str
    lock_type: LockType
    state: LockState

    # Holder
    holder_id: Optional[str] = None
    holders: List[str] = field(default_factory=list)  # For shared locks

    # Reentrant count
    count: int = 0

    # Timing
    acquired_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    # Waiting
    waiters: List[str] = field(default_factory=list)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_held(self) -> bool:
        """Check if lock is held."""
        return self.state == LockState.HELD

    def is_expired(self) -> bool:
        """Check if lock has expired."""
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at

    def time_held_ms(self) -> float:
        """Get time lock has been held."""
        if not self.acquired_at:
            return 0.0
        return (datetime.now() - self.acquired_at).total_seconds() * 1000


@dataclass
class LockConfig:
    """Lock configuration."""
    default_timeout_seconds: float = 30.0
    default_ttl_seconds: float = 60.0

    # Retry
    retry_interval_seconds: float = 0.1
    max_retries: int = 100

    # Fair lock queue size
    max_waiters: int = 1000

    # Cleanup
    cleanup_interval_seconds: float = 60.0


# ============================================================================
# DISTRIBUTED LOCK
# ============================================================================

class DistributedLock:
    """
    Single distributed lock.

    Can be used as context manager.
    """

    def __init__(
        self,
        name: str,
        manager: 'LockManager',
        lock_type: LockType = LockType.EXCLUSIVE,
        timeout: Optional[float] = None,
        ttl: Optional[float] = None
    ):
        """Initialize lock."""
        self.name = name
        self.manager = manager
        self.lock_type = lock_type
        self.timeout = timeout or manager.config.default_timeout_seconds
        self.ttl = ttl or manager.config.default_ttl_seconds

        self._owner_id = str(uuid.uuid4())
        self._acquired = False

    def acquire(self, blocking: bool = True) -> bool:
        """
        Acquire the lock.

        Args:
            blocking: Whether to block until acquired

        Returns:
            True if acquired
        """
        return self.manager.acquire(
            self.name,
            self._owner_id,
            self.lock_type,
            blocking=blocking,
            timeout=self.timeout,
            ttl=self.ttl
        )

    async def acquire_async(self, blocking: bool = True) -> bool:
        """Acquire lock asynchronously."""
        return await self.manager.acquire_async(
            self.name,
            self._owner_id,
            self.lock_type,
            blocking=blocking,
            timeout=self.timeout,
            ttl=self.ttl
        )

    def release(self) -> bool:
        """Release the lock."""
        result = self.manager.release(self.name, self._owner_id)
        if result:
            self._acquired = False
        return result

    def extend(self, additional_seconds: float) -> bool:
        """Extend lock TTL."""
        return self.manager.extend(self.name, self._owner_id, additional_seconds)

    @property
    def acquired(self) -> bool:
        """Check if lock is acquired."""
        return self._acquired

    def __enter__(self) -> 'DistributedLock':
        """Enter context manager."""
        self._acquired = self.acquire()
        if not self._acquired:
            raise TimeoutError(f"Failed to acquire lock: {self.name}")
        return self

    def __exit__(self, *args):
        """Exit context manager."""
        self.release()

    async def __aenter__(self) -> 'DistributedLock':
        """Enter async context manager."""
        self._acquired = await self.acquire_async()
        if not self._acquired:
            raise TimeoutError(f"Failed to acquire lock: {self.name}")
        return self

    async def __aexit__(self, *args):
        """Exit async context manager."""
        self.release()


# ============================================================================
# LOCK MANAGER
# ============================================================================

class LockManager:
    """
    Distributed lock manager.

    Features:
    - Multiple lock types
    - TTL support
    - Fair locking
    - Reentrant locks
    - Shared/exclusive locks

    "Ba'el manages the locks that guard reality." — Ba'el
    """

    def __init__(self, config: Optional[LockConfig] = None):
        """Initialize lock manager."""
        self.config = config or LockConfig()

        # Lock info: name -> LockInfo
        self._locks: Dict[str, LockInfo] = {}

        # Internal locks for thread safety
        self._internal_locks: Dict[str, threading.RLock] = {}
        self._global_lock = threading.RLock()

        # Stats
        self._stats = {
            'acquired': 0,
            'released': 0,
            'timeouts': 0,
            'contentions': 0
        }

        logger.info("Lock Manager initialized")

    # ========================================================================
    # LOCK OPERATIONS
    # ========================================================================

    def acquire(
        self,
        name: str,
        owner_id: str,
        lock_type: LockType = LockType.EXCLUSIVE,
        blocking: bool = True,
        timeout: Optional[float] = None,
        ttl: Optional[float] = None
    ) -> bool:
        """
        Acquire a lock.

        Args:
            name: Lock name
            owner_id: Owner identifier
            lock_type: Type of lock
            blocking: Wait for lock if held
            timeout: Max time to wait
            ttl: Lock time-to-live

        Returns:
            True if acquired
        """
        timeout = timeout or self.config.default_timeout_seconds
        ttl = ttl or self.config.default_ttl_seconds

        start_time = time.time()

        while True:
            acquired = self._try_acquire(name, owner_id, lock_type, ttl)

            if acquired:
                self._stats['acquired'] += 1
                return True

            if not blocking:
                return False

            # Check timeout
            if time.time() - start_time >= timeout:
                self._stats['timeouts'] += 1
                return False

            # Wait and retry
            time.sleep(self.config.retry_interval_seconds)

    async def acquire_async(
        self,
        name: str,
        owner_id: str,
        lock_type: LockType = LockType.EXCLUSIVE,
        blocking: bool = True,
        timeout: Optional[float] = None,
        ttl: Optional[float] = None
    ) -> bool:
        """Acquire lock asynchronously."""
        timeout = timeout or self.config.default_timeout_seconds
        ttl = ttl or self.config.default_ttl_seconds

        start_time = time.time()

        while True:
            acquired = self._try_acquire(name, owner_id, lock_type, ttl)

            if acquired:
                self._stats['acquired'] += 1
                return True

            if not blocking:
                return False

            if time.time() - start_time >= timeout:
                self._stats['timeouts'] += 1
                return False

            await asyncio.sleep(self.config.retry_interval_seconds)

    def _try_acquire(
        self,
        name: str,
        owner_id: str,
        lock_type: LockType,
        ttl: float
    ) -> bool:
        """Try to acquire lock once."""
        internal_lock = self._get_internal_lock(name)

        with internal_lock:
            lock_info = self._locks.get(name)

            # Check for expired lock
            if lock_info and lock_info.is_expired():
                self._expire_lock(name)
                lock_info = None

            # Lock is free
            if not lock_info or lock_info.state == LockState.FREE:
                self._create_lock(name, owner_id, lock_type, ttl)
                return True

            # Reentrant check
            if lock_type == LockType.REENTRANT and lock_info.holder_id == owner_id:
                lock_info.count += 1
                return True

            # Shared lock check
            if lock_type == LockType.SHARED and lock_info.lock_type == LockType.SHARED:
                lock_info.holders.append(owner_id)
                return True

            # Lock is held, add to waiters
            if owner_id not in lock_info.waiters:
                if len(lock_info.waiters) < self.config.max_waiters:
                    lock_info.waiters.append(owner_id)
                    self._stats['contentions'] += 1

            return False

    def _create_lock(
        self,
        name: str,
        owner_id: str,
        lock_type: LockType,
        ttl: float
    ) -> None:
        """Create new lock."""
        self._locks[name] = LockInfo(
            name=name,
            lock_type=lock_type,
            state=LockState.HELD,
            holder_id=owner_id,
            holders=[owner_id] if lock_type == LockType.SHARED else [],
            count=1,
            acquired_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=ttl)
        )

        logger.debug(f"Lock acquired: {name} by {owner_id}")

    def _expire_lock(self, name: str) -> None:
        """Expire a lock."""
        if name in self._locks:
            logger.debug(f"Lock expired: {name}")
            del self._locks[name]

    def release(self, name: str, owner_id: str) -> bool:
        """
        Release a lock.

        Args:
            name: Lock name
            owner_id: Owner identifier

        Returns:
            True if released
        """
        internal_lock = self._get_internal_lock(name)

        with internal_lock:
            lock_info = self._locks.get(name)

            if not lock_info:
                return False

            # Check owner
            if lock_info.lock_type == LockType.SHARED:
                if owner_id not in lock_info.holders:
                    return False
                lock_info.holders.remove(owner_id)

                if lock_info.holders:
                    return True  # Other holders remain
            else:
                if lock_info.holder_id != owner_id:
                    return False

            # Reentrant check
            if lock_info.lock_type == LockType.REENTRANT and lock_info.count > 1:
                lock_info.count -= 1
                return True

            # Release lock
            del self._locks[name]
            self._stats['released'] += 1

            logger.debug(f"Lock released: {name} by {owner_id}")

            return True

    def extend(
        self,
        name: str,
        owner_id: str,
        additional_seconds: float
    ) -> bool:
        """Extend lock TTL."""
        internal_lock = self._get_internal_lock(name)

        with internal_lock:
            lock_info = self._locks.get(name)

            if not lock_info or lock_info.holder_id != owner_id:
                return False

            lock_info.expires_at = datetime.now() + timedelta(seconds=additional_seconds)

            logger.debug(f"Lock extended: {name} by {additional_seconds}s")

            return True

    def force_release(self, name: str) -> bool:
        """Force release a lock (admin operation)."""
        internal_lock = self._get_internal_lock(name)

        with internal_lock:
            if name in self._locks:
                del self._locks[name]
                logger.warning(f"Lock force released: {name}")
                return True
        return False

    # ========================================================================
    # LOCK ACCESS
    # ========================================================================

    def lock(
        self,
        name: str,
        lock_type: LockType = LockType.EXCLUSIVE,
        timeout: Optional[float] = None,
        ttl: Optional[float] = None
    ) -> DistributedLock:
        """
        Get a lock object.

        Can be used as context manager.
        """
        return DistributedLock(
            name=name,
            manager=self,
            lock_type=lock_type,
            timeout=timeout,
            ttl=ttl
        )

    @contextmanager
    def held(
        self,
        name: str,
        lock_type: LockType = LockType.EXCLUSIVE,
        timeout: Optional[float] = None,
        ttl: Optional[float] = None
    ):
        """Context manager for lock."""
        lock = self.lock(name, lock_type, timeout, ttl)
        try:
            with lock:
                yield lock
        finally:
            pass

    @asynccontextmanager
    async def held_async(
        self,
        name: str,
        lock_type: LockType = LockType.EXCLUSIVE,
        timeout: Optional[float] = None,
        ttl: Optional[float] = None
    ):
        """Async context manager for lock."""
        lock = self.lock(name, lock_type, timeout, ttl)
        try:
            async with lock:
                yield lock
        finally:
            pass

    # ========================================================================
    # QUERIES
    # ========================================================================

    def is_locked(self, name: str) -> bool:
        """Check if lock is held."""
        lock_info = self._locks.get(name)
        return lock_info is not None and lock_info.is_held()

    def get_lock_info(self, name: str) -> Optional[LockInfo]:
        """Get lock information."""
        return self._locks.get(name)

    def list_locks(self) -> List[LockInfo]:
        """List all locks."""
        return list(self._locks.values())

    def _get_internal_lock(self, name: str) -> threading.RLock:
        """Get or create internal lock for a lock name."""
        with self._global_lock:
            if name not in self._internal_locks:
                self._internal_locks[name] = threading.RLock()
            return self._internal_locks[name]

    # ========================================================================
    # CLEANUP
    # ========================================================================

    def cleanup_expired(self) -> int:
        """Clean up expired locks."""
        expired = []

        with self._global_lock:
            for name, lock_info in self._locks.items():
                if lock_info.is_expired():
                    expired.append(name)

        for name in expired:
            self._expire_lock(name)

        return len(expired)

    # ========================================================================
    # STATS
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        with self._global_lock:
            active_locks = sum(
                1 for l in self._locks.values()
                if l.is_held()
            )
            waiting = sum(
                len(l.waiters) for l in self._locks.values()
            )

        return {
            'active_locks': active_locks,
            'total_locks': len(self._locks),
            'waiting': waiting,
            'acquired': self._stats['acquired'],
            'released': self._stats['released'],
            'timeouts': self._stats['timeouts'],
            'contentions': self._stats['contentions']
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

lock_manager = LockManager()


def acquire_lock(
    name: str,
    timeout: Optional[float] = None,
    ttl: Optional[float] = None
) -> DistributedLock:
    """Acquire a lock."""
    return lock_manager.lock(name, timeout=timeout, ttl=ttl)


def release_lock(name: str, owner_id: str) -> bool:
    """Release a lock."""
    return lock_manager.release(name, owner_id)
