"""
BAEL Object Pool Engine Implementation
=======================================

Object reuse for performance optimization.

"Ba'el maximizes efficiency through divine recycling." — Ba'el
"""

import asyncio
import logging
import threading
import time
from collections import deque
from typing import Callable, Dict, Generic, List, Optional, TypeVar
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("BAEL.ObjectPool")

T = TypeVar('T')


# ============================================================================
# ENUMS
# ============================================================================

class PooledObjectState(Enum):
    """State of a pooled object."""
    IDLE = "idle"
    IN_USE = "in_use"
    INVALID = "invalid"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class PooledObject(Generic[T]):
    """Wrapper for pooled objects."""
    obj: T
    state: PooledObjectState = PooledObjectState.IDLE
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    use_count: int = 0

    def is_expired(self, max_age: float) -> bool:
        """Check if object has expired."""
        return (time.time() - self.created_at) > max_age

    def is_idle_too_long(self, max_idle: float) -> bool:
        """Check if idle too long."""
        return (time.time() - self.last_used) > max_idle


@dataclass
class ObjectPoolConfig:
    """Object pool configuration."""
    initial_size: int = 0
    min_size: int = 0
    max_size: int = 100
    max_idle_time_seconds: float = 300.0
    max_object_age_seconds: float = 3600.0
    validation_on_borrow: bool = True
    validation_on_return: bool = False


@dataclass
class PoolStats:
    """Pool statistics."""
    current_size: int = 0
    idle_count: int = 0
    in_use_count: int = 0
    total_created: int = 0
    total_destroyed: int = 0
    total_borrows: int = 0
    total_returns: int = 0
    failed_borrows: int = 0
    validation_failures: int = 0


# ============================================================================
# OBJECT POOL
# ============================================================================

class ObjectPool(Generic[T]):
    """
    Generic object pool.

    Features:
    - Object reuse
    - Configurable size limits
    - Object validation
    - Automatic cleanup

    "Ba'el recycles with perfection." — Ba'el
    """

    def __init__(
        self,
        factory: Callable[[], T],
        config: Optional[ObjectPoolConfig] = None,
        validator: Optional[Callable[[T], bool]] = None,
        reset_fn: Optional[Callable[[T], None]] = None,
        destroy_fn: Optional[Callable[[T], None]] = None
    ):
        """
        Initialize object pool.

        Args:
            factory: Function to create new objects
            config: Pool configuration
            validator: Function to validate objects
            reset_fn: Function to reset object state
            destroy_fn: Function to cleanup objects
        """
        self._factory = factory
        self.config = config or ObjectPoolConfig()
        self._validator = validator
        self._reset_fn = reset_fn
        self._destroy_fn = destroy_fn

        # Pool state
        self._idle: deque = deque()
        self._in_use: Dict[int, PooledObject[T]] = {}

        # Statistics
        self._stats = PoolStats()

        # Thread safety
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)

        # Async support
        self._async_lock: Optional[asyncio.Lock] = None

        # Create initial objects
        self._initialize()

        logger.info(
            f"Object pool initialized (initial={self.config.initial_size})"
        )

    def _initialize(self) -> None:
        """Create initial pool of objects."""
        for _ in range(self.config.initial_size):
            self._create_object()

    # ========================================================================
    # OBJECT LIFECYCLE
    # ========================================================================

    def _create_object(self) -> Optional[PooledObject[T]]:
        """Create a new pooled object."""
        if self._stats.current_size >= self.config.max_size:
            return None

        try:
            obj = self._factory()
            pooled = PooledObject(obj=obj)

            self._idle.append(pooled)

            self._stats.current_size += 1
            self._stats.idle_count += 1
            self._stats.total_created += 1

            return pooled

        except Exception as e:
            logger.error(f"Failed to create object: {e}")
            return None

    def _destroy_object(self, pooled: PooledObject[T]) -> None:
        """Destroy a pooled object."""
        try:
            if self._destroy_fn:
                self._destroy_fn(pooled.obj)

            self._stats.current_size -= 1
            self._stats.total_destroyed += 1

        except Exception as e:
            logger.error(f"Error destroying object: {e}")

    def _validate(self, pooled: PooledObject[T]) -> bool:
        """Validate an object."""
        if not self._validator:
            return True

        try:
            return self._validator(pooled.obj)
        except Exception:
            return False

    def _reset(self, pooled: PooledObject[T]) -> None:
        """Reset an object to initial state."""
        if self._reset_fn:
            try:
                self._reset_fn(pooled.obj)
            except Exception as e:
                logger.error(f"Error resetting object: {e}")

    # ========================================================================
    # BORROW/RETURN
    # ========================================================================

    def borrow(self, timeout: Optional[float] = None) -> Optional[T]:
        """
        Borrow an object from the pool.

        Args:
            timeout: Maximum time to wait

        Returns:
            Object or None if unavailable
        """
        deadline = time.time() + timeout if timeout else None

        with self._lock:
            while True:
                # Try to get from idle pool
                while self._idle:
                    pooled = self._idle.popleft()
                    self._stats.idle_count -= 1

                    # Check validity
                    if pooled.is_expired(self.config.max_object_age_seconds):
                        self._destroy_object(pooled)
                        continue

                    if (self.config.validation_on_borrow and
                        not self._validate(pooled)):
                        self._stats.validation_failures += 1
                        self._destroy_object(pooled)
                        continue

                    # Mark as in use
                    pooled.state = PooledObjectState.IN_USE
                    pooled.use_count += 1
                    pooled.last_used = time.time()

                    self._in_use[id(pooled.obj)] = pooled
                    self._stats.in_use_count += 1
                    self._stats.total_borrows += 1

                    return pooled.obj

                # Try to create new object
                if self._stats.current_size < self.config.max_size:
                    pooled = self._create_object()
                    if pooled:
                        # Take from idle immediately
                        self._idle.popleft()
                        self._stats.idle_count -= 1

                        pooled.state = PooledObjectState.IN_USE
                        pooled.use_count += 1
                        pooled.last_used = time.time()

                        self._in_use[id(pooled.obj)] = pooled
                        self._stats.in_use_count += 1
                        self._stats.total_borrows += 1

                        return pooled.obj

                # Wait for return
                if deadline:
                    remaining = deadline - time.time()
                    if remaining <= 0:
                        self._stats.failed_borrows += 1
                        return None
                    self._condition.wait(timeout=remaining)
                else:
                    self._stats.failed_borrows += 1
                    return None

    def return_obj(self, obj: T) -> None:
        """
        Return an object to the pool.

        Args:
            obj: Object to return
        """
        with self._lock:
            obj_id = id(obj)
            pooled = self._in_use.get(obj_id)

            if not pooled:
                logger.warning("Returned unknown object")
                return

            del self._in_use[obj_id]
            self._stats.in_use_count -= 1
            self._stats.total_returns += 1

            # Check if should keep
            keep = True

            if pooled.is_expired(self.config.max_object_age_seconds):
                keep = False
            elif (self.config.validation_on_return and
                  not self._validate(pooled)):
                self._stats.validation_failures += 1
                keep = False
            elif self._stats.idle_count >= self.config.max_size:
                keep = False

            if keep:
                # Reset and return to pool
                self._reset(pooled)

                pooled.state = PooledObjectState.IDLE
                pooled.last_used = time.time()

                self._idle.append(pooled)
                self._stats.idle_count += 1

                self._condition.notify()
            else:
                self._destroy_object(pooled)

    # ========================================================================
    # ASYNC SUPPORT
    # ========================================================================

    async def borrow_async(
        self,
        timeout: Optional[float] = None
    ) -> Optional[T]:
        """Borrow asynchronously."""
        if self._async_lock is None:
            self._async_lock = asyncio.Lock()

        # Try immediate borrow
        obj = self.borrow(timeout=0)
        if obj:
            return obj

        # Wait with timeout
        deadline = time.time() + (timeout or 30.0)

        while time.time() < deadline:
            await asyncio.sleep(0.01)  # Small wait
            obj = self.borrow(timeout=0)
            if obj:
                return obj

        return None

    async def return_async(self, obj: T) -> None:
        """Return asynchronously."""
        self.return_obj(obj)

    # ========================================================================
    # CONTEXT MANAGERS
    # ========================================================================

    class _BorrowContext:
        """Context manager for borrowing."""

        def __init__(self, pool: 'ObjectPool', timeout: Optional[float] = None):
            self.pool = pool
            self.timeout = timeout
            self.obj = None

        def __enter__(self) -> T:
            self.obj = self.pool.borrow(self.timeout)
            if self.obj is None:
                raise RuntimeError("Failed to borrow object")
            return self.obj

        def __exit__(self, *args) -> None:
            if self.obj is not None:
                self.pool.return_obj(self.obj)

        async def __aenter__(self) -> T:
            self.obj = await self.pool.borrow_async(self.timeout)
            if self.obj is None:
                raise RuntimeError("Failed to borrow object")
            return self.obj

        async def __aexit__(self, *args) -> None:
            if self.obj is not None:
                await self.pool.return_async(self.obj)

    def acquire(self, timeout: Optional[float] = None) -> _BorrowContext:
        """Get context manager for borrowing."""
        return self._BorrowContext(self, timeout)

    # ========================================================================
    # MAINTENANCE
    # ========================================================================

    def trim(self, target_idle: Optional[int] = None) -> int:
        """
        Trim excess idle objects.

        Args:
            target_idle: Target idle count

        Returns:
            Number of objects removed
        """
        target = target_idle if target_idle is not None else self.config.min_size
        removed = 0

        with self._lock:
            while self._stats.idle_count > target:
                pooled = self._idle.popleft()
                self._stats.idle_count -= 1
                self._destroy_object(pooled)
                removed += 1

        return removed

    def evict_expired(self) -> int:
        """
        Evict expired objects.

        Returns:
            Number of objects evicted
        """
        evicted = 0

        with self._lock:
            to_evict = []

            for pooled in self._idle:
                if pooled.is_expired(self.config.max_object_age_seconds):
                    to_evict.append(pooled)
                elif pooled.is_idle_too_long(self.config.max_idle_time_seconds):
                    if self._stats.idle_count > self.config.min_size:
                        to_evict.append(pooled)

            for pooled in to_evict:
                try:
                    self._idle.remove(pooled)
                    self._stats.idle_count -= 1
                    self._destroy_object(pooled)
                    evicted += 1
                except ValueError:
                    pass

        return evicted

    def clear(self) -> None:
        """Clear all objects from pool."""
        with self._lock:
            # Destroy idle objects
            while self._idle:
                pooled = self._idle.popleft()
                self._destroy_object(pooled)

            self._stats.idle_count = 0

            # Mark in-use as invalid
            for pooled in self._in_use.values():
                pooled.state = PooledObjectState.INVALID

    # ========================================================================
    # STATS
    # ========================================================================

    @property
    def size(self) -> int:
        """Get current pool size."""
        return self._stats.current_size

    @property
    def available(self) -> int:
        """Get available objects."""
        return self._stats.idle_count

    @property
    def in_use(self) -> int:
        """Get in-use count."""
        return self._stats.in_use_count

    def get_stats(self) -> Dict:
        """Get pool statistics."""
        return {
            'current_size': self._stats.current_size,
            'idle': self._stats.idle_count,
            'in_use': self._stats.in_use_count,
            'total_created': self._stats.total_created,
            'total_destroyed': self._stats.total_destroyed,
            'total_borrows': self._stats.total_borrows,
            'total_returns': self._stats.total_returns,
            'failed_borrows': self._stats.failed_borrows,
            'validation_failures': self._stats.validation_failures
        }


# ============================================================================
# SPECIALIZED POOLS
# ============================================================================

class BufferPool(ObjectPool[bytearray]):
    """Pool for byte buffers."""

    def __init__(
        self,
        buffer_size: int = 4096,
        config: Optional[ObjectPoolConfig] = None
    ):
        self.buffer_size = buffer_size

        super().__init__(
            factory=lambda: bytearray(buffer_size),
            config=config,
            reset_fn=lambda b: b[:] = b'\x00' * len(b)  # Zero out
        )


class ListPool(ObjectPool[list]):
    """Pool for lists."""

    def __init__(self, config: Optional[ObjectPoolConfig] = None):
        super().__init__(
            factory=list,
            config=config,
            reset_fn=lambda l: l.clear()
        )


class DictPool(ObjectPool[dict]):
    """Pool for dictionaries."""

    def __init__(self, config: Optional[ObjectPoolConfig] = None):
        super().__init__(
            factory=dict,
            config=config,
            reset_fn=lambda d: d.clear()
        )


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_pool(
    factory: Callable[[], T],
    initial_size: int = 0,
    max_size: int = 100,
    **kwargs
) -> ObjectPool[T]:
    """Create an object pool."""
    config = ObjectPoolConfig(
        initial_size=initial_size,
        max_size=max_size,
        **kwargs
    )
    return ObjectPool(factory, config)


# Global pools
_list_pool: Optional[ListPool] = None
_dict_pool: Optional[DictPool] = None


def get_list() -> list:
    """Get a list from pool."""
    global _list_pool
    if _list_pool is None:
        _list_pool = ListPool()
    return _list_pool.borrow() or []


def return_list(lst: list) -> None:
    """Return a list to pool."""
    global _list_pool
    if _list_pool:
        _list_pool.return_obj(lst)


def get_dict() -> dict:
    """Get a dict from pool."""
    global _dict_pool
    if _dict_pool is None:
        _dict_pool = DictPool()
    return _dict_pool.borrow() or {}


def return_dict(d: dict) -> None:
    """Return a dict to pool."""
    global _dict_pool
    if _dict_pool:
        _dict_pool.return_obj(d)
