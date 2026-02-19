"""
BAEL Bulkhead Pattern Engine Implementation
============================================

Isolation for fault tolerance.

"Ba'el compartmentalizes to survive catastrophe." — Ba'el
"""

import asyncio
import logging
import threading
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import uuid

logger = logging.getLogger("BAEL.Bulkhead")


# ============================================================================
# ENUMS
# ============================================================================

class BulkheadType(Enum):
    """Bulkhead isolation types."""
    SEMAPHORE = "semaphore"     # Limit concurrent calls
    THREAD_POOL = "thread_pool" # Dedicated thread pool
    PROCESS_POOL = "process_pool"  # Dedicated processes


class BulkheadState(Enum):
    """Bulkhead states."""
    OPEN = "open"           # Accepting requests
    HALF_FULL = "half_full" # Approaching limit
    FULL = "full"           # At capacity
    REJECTING = "rejecting" # Rejecting new requests


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class BulkheadStats:
    """Bulkhead statistics."""
    total_calls: int = 0
    rejected_calls: int = 0
    concurrent_calls: int = 0
    peak_concurrent: int = 0
    avg_wait_time_ms: float = 0.0


@dataclass
class Bulkhead:
    """A bulkhead instance."""
    id: str
    name: str
    bulkhead_type: BulkheadType

    # Limits
    max_concurrent: int = 10
    max_wait_ms: int = 0  # 0 = fail fast

    # State
    state: BulkheadState = BulkheadState.OPEN
    current_concurrent: int = 0
    waiting: int = 0

    # Stats
    stats: BulkheadStats = field(default_factory=BulkheadStats)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'type': self.bulkhead_type.value,
            'state': self.state.value,
            'max_concurrent': self.max_concurrent,
            'current_concurrent': self.current_concurrent,
            'waiting': self.waiting
        }


@dataclass
class BulkheadConfig:
    """Bulkhead configuration."""
    default_max_concurrent: int = 10
    default_max_wait_ms: int = 0
    half_full_threshold: float = 0.7  # 70% = half full


# ============================================================================
# BULKHEAD MANAGER
# ============================================================================

class BulkheadManager:
    """
    Bulkhead pattern manager.

    Features:
    - Resource isolation
    - Concurrency limiting
    - Fail-fast or wait
    - Multiple bulkhead types

    "Ba'el builds walls to protect from cascading failure." — Ba'el
    """

    def __init__(self, config: Optional[BulkheadConfig] = None):
        """Initialize bulkhead manager."""
        self.config = config or BulkheadConfig()

        # Bulkheads
        self._bulkheads: Dict[str, Bulkhead] = {}
        self._semaphores: Dict[str, asyncio.Semaphore] = {}

        # Thread safety
        self._lock = threading.RLock()

        # Global stats
        self._stats = {
            'bulkheads_created': 0,
            'total_calls': 0,
            'total_rejected': 0
        }

        logger.info("Bulkhead Manager initialized")

    # ========================================================================
    # BULKHEAD MANAGEMENT
    # ========================================================================

    def create_bulkhead(
        self,
        name: str,
        max_concurrent: Optional[int] = None,
        max_wait_ms: Optional[int] = None,
        bulkhead_type: BulkheadType = BulkheadType.SEMAPHORE,
        bulkhead_id: Optional[str] = None
    ) -> Bulkhead:
        """
        Create a bulkhead.

        Args:
            name: Bulkhead name
            max_concurrent: Maximum concurrent calls
            max_wait_ms: Maximum wait time (0 = fail fast)
            bulkhead_type: Type of bulkhead
            bulkhead_id: Optional ID

        Returns:
            Bulkhead
        """
        bulkhead = Bulkhead(
            id=bulkhead_id or str(uuid.uuid4()),
            name=name,
            bulkhead_type=bulkhead_type,
            max_concurrent=max_concurrent or self.config.default_max_concurrent,
            max_wait_ms=max_wait_ms if max_wait_ms is not None else self.config.default_max_wait_ms
        )

        with self._lock:
            self._bulkheads[bulkhead.id] = bulkhead
            self._semaphores[bulkhead.id] = asyncio.Semaphore(bulkhead.max_concurrent)
            self._stats['bulkheads_created'] += 1

        logger.info(f"Bulkhead created: {name} (max={max_concurrent})")

        return bulkhead

    def get_or_create(
        self,
        name: str,
        **kwargs
    ) -> Bulkhead:
        """Get bulkhead or create if not exists."""
        with self._lock:
            for bulkhead in self._bulkheads.values():
                if bulkhead.name == name:
                    return bulkhead

        return self.create_bulkhead(name, **kwargs)

    def delete_bulkhead(self, bulkhead_id: str) -> bool:
        """Delete a bulkhead."""
        with self._lock:
            if bulkhead_id in self._bulkheads:
                del self._bulkheads[bulkhead_id]
                del self._semaphores[bulkhead_id]
                return True
        return False

    # ========================================================================
    # EXECUTION
    # ========================================================================

    async def execute(
        self,
        bulkhead_id: str,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function within bulkhead.

        Args:
            bulkhead_id: Bulkhead to use
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            BulkheadFullException: If bulkhead is full
        """
        bulkhead = self._bulkheads.get(bulkhead_id)
        if not bulkhead:
            raise ValueError(f"Bulkhead not found: {bulkhead_id}")

        semaphore = self._semaphores[bulkhead_id]

        bulkhead.stats.total_calls += 1
        self._stats['total_calls'] += 1

        # Update state
        self._update_state(bulkhead)

        # Check if should reject immediately
        if bulkhead.max_wait_ms == 0 and bulkhead.current_concurrent >= bulkhead.max_concurrent:
            bulkhead.stats.rejected_calls += 1
            self._stats['total_rejected'] += 1
            raise BulkheadFullException(f"Bulkhead {bulkhead.name} is full")

        # Try to acquire with timeout
        try:
            bulkhead.waiting += 1
            timeout = bulkhead.max_wait_ms / 1000 if bulkhead.max_wait_ms > 0 else None

            acquired = await asyncio.wait_for(
                semaphore.acquire(),
                timeout=timeout
            )

            if not acquired:
                raise BulkheadFullException(f"Could not acquire bulkhead {bulkhead.name}")

        except asyncio.TimeoutError:
            bulkhead.waiting -= 1
            bulkhead.stats.rejected_calls += 1
            self._stats['total_rejected'] += 1
            raise BulkheadFullException(f"Timeout waiting for bulkhead {bulkhead.name}")

        finally:
            bulkhead.waiting -= 1

        # Execute within bulkhead
        try:
            bulkhead.current_concurrent += 1
            bulkhead.stats.concurrent_calls = bulkhead.current_concurrent
            bulkhead.stats.peak_concurrent = max(
                bulkhead.stats.peak_concurrent,
                bulkhead.current_concurrent
            )

            self._update_state(bulkhead)

            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return await asyncio.to_thread(func, *args, **kwargs)

        finally:
            bulkhead.current_concurrent -= 1
            semaphore.release()
            self._update_state(bulkhead)

    def _update_state(self, bulkhead: Bulkhead) -> None:
        """Update bulkhead state."""
        ratio = bulkhead.current_concurrent / bulkhead.max_concurrent

        if bulkhead.current_concurrent >= bulkhead.max_concurrent:
            bulkhead.state = BulkheadState.FULL
        elif ratio >= self.config.half_full_threshold:
            bulkhead.state = BulkheadState.HALF_FULL
        else:
            bulkhead.state = BulkheadState.OPEN

    # ========================================================================
    # CONTEXT MANAGER
    # ========================================================================

    def acquire(self, bulkhead_id: str) -> 'BulkheadContext':
        """Get context manager for bulkhead."""
        return BulkheadContext(self, bulkhead_id)

    # ========================================================================
    # DECORATOR
    # ========================================================================

    def bulkhead(
        self,
        name: str,
        max_concurrent: Optional[int] = None
    ) -> Callable:
        """
        Decorator to protect function with bulkhead.

        Args:
            name: Bulkhead name
            max_concurrent: Maximum concurrent calls
        """
        bulkhead = self.get_or_create(name, max_concurrent=max_concurrent)

        def decorator(func: Callable) -> Callable:
            async def wrapper(*args, **kwargs):
                return await self.execute(bulkhead.id, func, *args, **kwargs)

            wrapper.__name__ = func.__name__
            wrapper.__doc__ = func.__doc__
            return wrapper

        return decorator

    # ========================================================================
    # QUERIES
    # ========================================================================

    def get_bulkhead(self, bulkhead_id: str) -> Optional[Bulkhead]:
        """Get bulkhead by ID."""
        return self._bulkheads.get(bulkhead_id)

    def list_bulkheads(self) -> List[Bulkhead]:
        """List all bulkheads."""
        return list(self._bulkheads.values())

    # ========================================================================
    # STATS
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        bulkhead_stats = {
            b.name: {
                'state': b.state.value,
                'concurrent': b.current_concurrent,
                'max': b.max_concurrent
            }
            for b in self._bulkheads.values()
        }

        return {
            'bulkheads': bulkhead_stats,
            **self._stats
        }


# ============================================================================
# CONTEXT MANAGER
# ============================================================================

class BulkheadContext:
    """Context manager for bulkhead."""

    def __init__(self, manager: BulkheadManager, bulkhead_id: str):
        self.manager = manager
        self.bulkhead_id = bulkhead_id

    async def __aenter__(self):
        bulkhead = self.manager._bulkheads.get(self.bulkhead_id)
        if not bulkhead:
            raise ValueError(f"Bulkhead not found: {self.bulkhead_id}")

        semaphore = self.manager._semaphores[self.bulkhead_id]
        await semaphore.acquire()
        bulkhead.current_concurrent += 1
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        bulkhead = self.manager._bulkheads.get(self.bulkhead_id)
        if bulkhead:
            bulkhead.current_concurrent -= 1
            semaphore = self.manager._semaphores[self.bulkhead_id]
            semaphore.release()


# ============================================================================
# EXCEPTION
# ============================================================================

class BulkheadFullException(Exception):
    """Raised when bulkhead is at capacity."""
    pass


# ============================================================================
# CONVENIENCE
# ============================================================================

bulkhead_manager = BulkheadManager()


def create_bulkhead(name: str, **kwargs) -> Bulkhead:
    """Create a bulkhead."""
    return bulkhead_manager.create_bulkhead(name, **kwargs)


async def execute_in_bulkhead(bulkhead_id: str, func: Callable, *args, **kwargs) -> Any:
    """Execute within bulkhead."""
    return await bulkhead_manager.execute(bulkhead_id, func, *args, **kwargs)
