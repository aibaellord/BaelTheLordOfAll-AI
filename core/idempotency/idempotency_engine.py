"""
BAEL Idempotency Engine Implementation
=======================================

Ensures operations are executed exactly once.

"Ba'el acts once, but with perfect precision." — Ba'el
"""

import asyncio
import functools
import hashlib
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional, TypeVar
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("BAEL.Idempotency")

T = TypeVar('T')


# ============================================================================
# ENUMS
# ============================================================================

class IdempotencyResult(Enum):
    """Result of idempotency check."""
    EXECUTED = "executed"        # First execution
    DUPLICATE = "duplicate"      # Already executed
    IN_PROGRESS = "in_progress"  # Currently executing
    EXPIRED = "expired"          # Entry expired


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class IdempotencyEntry:
    """An idempotency entry."""
    key: str
    result: Optional[Any] = None
    error: Optional[str] = None

    # Status
    completed: bool = False
    in_progress: bool = False

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            'key': self.key,
            'result': self.result,
            'error': self.error,
            'completed': self.completed,
            'in_progress': self.in_progress,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'metadata': self.metadata
        }


@dataclass
class IdempotencyConfig:
    """Idempotency configuration."""
    default_ttl_seconds: float = 86400  # 24 hours
    cleanup_interval_seconds: float = 3600
    max_entries: int = 100000


# ============================================================================
# IDEMPOTENCY STORE
# ============================================================================

class IdempotencyStore:
    """
    In-memory idempotency store.

    Can be extended for Redis/database storage.
    """

    def __init__(self, config: Optional[IdempotencyConfig] = None):
        """Initialize store."""
        self.config = config or IdempotencyConfig()

        # Entries: key -> IdempotencyEntry
        self._entries: Dict[str, IdempotencyEntry] = {}

        # Thread safety
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[IdempotencyEntry]:
        """Get an entry."""
        with self._lock:
            entry = self._entries.get(key)
            if entry and entry.is_expired():
                del self._entries[key]
                return None
            return entry

    def set(
        self,
        key: str,
        result: Optional[Any] = None,
        error: Optional[str] = None,
        completed: bool = True,
        ttl: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> IdempotencyEntry:
        """Set an entry."""
        ttl = ttl or self.config.default_ttl_seconds

        with self._lock:
            entry = self._entries.get(key)

            if entry:
                entry.result = result
                entry.error = error
                entry.completed = completed
                entry.in_progress = not completed
                entry.completed_at = datetime.now() if completed else None
                entry.metadata.update(metadata or {})
            else:
                entry = IdempotencyEntry(
                    key=key,
                    result=result,
                    error=error,
                    completed=completed,
                    in_progress=not completed,
                    completed_at=datetime.now() if completed else None,
                    expires_at=datetime.now() + timedelta(seconds=ttl),
                    metadata=metadata or {}
                )
                self._entries[key] = entry

            return entry

    def mark_in_progress(self, key: str, ttl: Optional[float] = None) -> IdempotencyEntry:
        """Mark as in progress."""
        return self.set(key, completed=False, ttl=ttl)

    def mark_complete(
        self,
        key: str,
        result: Any,
        ttl: Optional[float] = None
    ) -> IdempotencyEntry:
        """Mark as complete with result."""
        return self.set(key, result=result, completed=True, ttl=ttl)

    def mark_error(
        self,
        key: str,
        error: str,
        ttl: Optional[float] = None
    ) -> IdempotencyEntry:
        """Mark as complete with error."""
        return self.set(key, error=error, completed=True, ttl=ttl)

    def remove(self, key: str) -> bool:
        """Remove an entry."""
        with self._lock:
            if key in self._entries:
                del self._entries[key]
                return True
        return False

    def cleanup_expired(self) -> int:
        """Clean up expired entries."""
        now = datetime.now()
        expired = []

        with self._lock:
            for key, entry in self._entries.items():
                if entry.expires_at and entry.expires_at < now:
                    expired.append(key)

            for key in expired:
                del self._entries[key]

        return len(expired)

    def count(self) -> int:
        """Count entries."""
        with self._lock:
            return len(self._entries)


# ============================================================================
# IDEMPOTENCY ENGINE
# ============================================================================

class IdempotencyEngine:
    """
    Idempotency engine.

    Features:
    - Ensure exactly-once execution
    - Configurable TTL
    - Concurrent execution handling
    - Automatic cleanup

    "Ba'el ensures every action happens exactly once." — Ba'el
    """

    def __init__(
        self,
        store: Optional[IdempotencyStore] = None,
        config: Optional[IdempotencyConfig] = None
    ):
        """Initialize engine."""
        self.config = config or IdempotencyConfig()
        self.store = store or IdempotencyStore(self.config)

        # Stats
        self._stats = {
            'executed': 0,
            'duplicates': 0,
            'in_progress': 0,
            'errors': 0
        }

        # Thread safety
        self._lock = threading.RLock()

        # Key generation
        self._key_generators: Dict[str, Callable[..., str]] = {}

        logger.info("Idempotency Engine initialized")

    # ========================================================================
    # KEY GENERATION
    # ========================================================================

    @staticmethod
    def generate_key(*args, **kwargs) -> str:
        """Generate idempotency key from arguments."""
        key_data = str((args, sorted(kwargs.items())))
        return hashlib.sha256(key_data.encode()).hexdigest()

    def register_key_generator(
        self,
        name: str,
        generator: Callable[..., str]
    ) -> None:
        """Register custom key generator."""
        self._key_generators[name] = generator

    # ========================================================================
    # EXECUTION
    # ========================================================================

    def execute(
        self,
        key: str,
        func: Callable[..., T],
        *args,
        ttl: Optional[float] = None,
        wait_for_completion: bool = True,
        wait_timeout: float = 30.0,
        **kwargs
    ) -> tuple[IdempotencyResult, Optional[T]]:
        """
        Execute function with idempotency.

        Args:
            key: Idempotency key
            func: Function to execute
            *args: Function arguments
            ttl: Time-to-live for result
            wait_for_completion: Wait if in progress
            wait_timeout: Timeout for waiting
            **kwargs: Function keyword arguments

        Returns:
            (result_type, result_value)
        """
        # Check existing entry
        entry = self.store.get(key)

        if entry:
            if entry.completed:
                self._stats['duplicates'] += 1
                if entry.error:
                    raise Exception(entry.error)
                return (IdempotencyResult.DUPLICATE, entry.result)

            if entry.in_progress:
                if wait_for_completion:
                    # Wait for completion
                    return self._wait_for_completion(key, wait_timeout)
                else:
                    self._stats['in_progress'] += 1
                    return (IdempotencyResult.IN_PROGRESS, None)

        # Mark in progress
        self.store.mark_in_progress(key, ttl)

        try:
            # Execute function
            result = func(*args, **kwargs)

            # Mark complete
            self.store.mark_complete(key, result, ttl)
            self._stats['executed'] += 1

            return (IdempotencyResult.EXECUTED, result)

        except Exception as e:
            # Mark error
            self.store.mark_error(key, str(e), ttl)
            self._stats['errors'] += 1
            raise

    async def execute_async(
        self,
        key: str,
        func: Callable[..., T],
        *args,
        ttl: Optional[float] = None,
        wait_for_completion: bool = True,
        wait_timeout: float = 30.0,
        **kwargs
    ) -> tuple[IdempotencyResult, Optional[T]]:
        """Execute async function with idempotency."""
        # Check existing entry
        entry = self.store.get(key)

        if entry:
            if entry.completed:
                self._stats['duplicates'] += 1
                if entry.error:
                    raise Exception(entry.error)
                return (IdempotencyResult.DUPLICATE, entry.result)

            if entry.in_progress:
                if wait_for_completion:
                    return await self._wait_for_completion_async(key, wait_timeout)
                else:
                    self._stats['in_progress'] += 1
                    return (IdempotencyResult.IN_PROGRESS, None)

        # Mark in progress
        self.store.mark_in_progress(key, ttl)

        try:
            # Execute function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = await asyncio.to_thread(func, *args, **kwargs)

            # Mark complete
            self.store.mark_complete(key, result, ttl)
            self._stats['executed'] += 1

            return (IdempotencyResult.EXECUTED, result)

        except Exception as e:
            self.store.mark_error(key, str(e), ttl)
            self._stats['errors'] += 1
            raise

    def _wait_for_completion(
        self,
        key: str,
        timeout: float
    ) -> tuple[IdempotencyResult, Optional[Any]]:
        """Wait for completion."""
        start = time.time()

        while time.time() - start < timeout:
            entry = self.store.get(key)

            if not entry:
                # Entry expired
                return (IdempotencyResult.EXPIRED, None)

            if entry.completed:
                self._stats['duplicates'] += 1
                if entry.error:
                    raise Exception(entry.error)
                return (IdempotencyResult.DUPLICATE, entry.result)

            time.sleep(0.1)

        raise TimeoutError(f"Timeout waiting for key: {key}")

    async def _wait_for_completion_async(
        self,
        key: str,
        timeout: float
    ) -> tuple[IdempotencyResult, Optional[Any]]:
        """Wait for completion asynchronously."""
        start = time.time()

        while time.time() - start < timeout:
            entry = self.store.get(key)

            if not entry:
                return (IdempotencyResult.EXPIRED, None)

            if entry.completed:
                self._stats['duplicates'] += 1
                if entry.error:
                    raise Exception(entry.error)
                return (IdempotencyResult.DUPLICATE, entry.result)

            await asyncio.sleep(0.1)

        raise TimeoutError(f"Timeout waiting for key: {key}")

    # ========================================================================
    # QUERIES
    # ========================================================================

    def get_entry(self, key: str) -> Optional[IdempotencyEntry]:
        """Get an entry."""
        return self.store.get(key)

    def is_duplicate(self, key: str) -> bool:
        """Check if key is duplicate."""
        entry = self.store.get(key)
        return entry is not None and entry.completed

    def is_in_progress(self, key: str) -> bool:
        """Check if key is in progress."""
        entry = self.store.get(key)
        return entry is not None and entry.in_progress

    def invalidate(self, key: str) -> bool:
        """Invalidate an entry."""
        return self.store.remove(key)

    # ========================================================================
    # CLEANUP
    # ========================================================================

    def cleanup(self) -> int:
        """Clean up expired entries."""
        return self.store.cleanup_expired()

    # ========================================================================
    # STATS
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            'entries': self.store.count(),
            **self._stats
        }


# ============================================================================
# DECORATOR
# ============================================================================

def idempotent(
    key_func: Optional[Callable[..., str]] = None,
    ttl: Optional[float] = None,
    engine: Optional[IdempotencyEngine] = None
):
    """
    Decorator for idempotent functions.

    Args:
        key_func: Function to generate idempotency key
        ttl: Time-to-live for result
        engine: Idempotency engine to use
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            eng = engine or idempotency_engine

            # Generate key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = IdempotencyEngine.generate_key(*args, **kwargs)

            result_type, result = eng.execute(key, func, *args, ttl=ttl, **kwargs)
            return result

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            eng = engine or idempotency_engine

            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = IdempotencyEngine.generate_key(*args, **kwargs)

            result_type, result = await eng.execute_async(key, func, *args, ttl=ttl, **kwargs)
            return result

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper

    return decorator


# ============================================================================
# CONVENIENCE
# ============================================================================

idempotency_engine = IdempotencyEngine()


def ensure_idempotent(
    key: str,
    func: Callable[..., T],
    *args,
    **kwargs
) -> tuple[IdempotencyResult, Optional[T]]:
    """Ensure idempotent execution."""
    return idempotency_engine.execute(key, func, *args, **kwargs)
