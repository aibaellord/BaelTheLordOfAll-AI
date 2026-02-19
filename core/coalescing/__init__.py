"""
BAEL Request Coalescing Engine Implementation
==============================================

Combine duplicate requests for efficiency.

"Ba'el consolidates power for maximum impact." — Ba'el
"""

import asyncio
import hashlib
import json
import logging
import threading
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid

logger = logging.getLogger("BAEL.Coalescing")


# ============================================================================
# ENUMS
# ============================================================================

class CoalescingStrategy(Enum):
    """Coalescing strategies."""
    FIRST_WINS = "first_wins"   # First request triggers, others wait
    BATCH = "batch"             # Collect and batch process
    DEDUPE = "dedupe"           # Deduplicate in window


class CoalescingState(Enum):
    """Request state."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class CoalescedRequest:
    """A coalesced request group."""
    key: str
    state: CoalescingState = CoalescingState.PENDING

    # Requests
    request_count: int = 0
    first_request_time: datetime = field(default_factory=datetime.now)

    # Result
    result: Optional[Any] = None
    error: Optional[str] = None

    # Waiters
    waiters: List[asyncio.Future] = field(default_factory=list)


@dataclass
class CoalescingConfig:
    """Coalescing configuration."""
    strategy: CoalescingStrategy = CoalescingStrategy.FIRST_WINS

    # Batching
    batch_size: int = 10
    batch_timeout_ms: float = 100.0

    # Deduplication
    dedupe_window_ms: float = 500.0

    # Cache
    cache_ttl_ms: float = 1000.0

    # Key generation
    include_args: bool = True
    include_kwargs: bool = True


@dataclass
class CoalescingStats:
    """Coalescing statistics."""
    total_requests: int = 0
    coalesced_requests: int = 0
    batches_processed: int = 0
    cache_hits: int = 0
    avg_batch_size: float = 0.0


# ============================================================================
# COALESCING ENGINE
# ============================================================================

class CoalescingEngine:
    """
    Request coalescing engine.

    Features:
    - Duplicate request elimination
    - Request batching
    - Result caching
    - Key-based grouping

    "Ba'el merges streams into rivers of power." — Ba'el
    """

    def __init__(self, config: Optional[CoalescingConfig] = None):
        """Initialize coalescing engine."""
        self.config = config or CoalescingConfig()

        # Active requests
        self._requests: Dict[str, CoalescedRequest] = {}

        # Result cache
        self._cache: Dict[str, Tuple[Any, float]] = {}

        # Batching
        self._batches: Dict[str, List[Tuple[str, Any, Any]]] = {}
        self._batch_timers: Dict[str, asyncio.Task] = {}

        # Thread safety
        self._lock = threading.RLock()

        # Stats
        self._stats = CoalescingStats()

        logger.info("Coalescing Engine initialized")

    # ========================================================================
    # MAIN INTERFACE
    # ========================================================================

    async def execute(
        self,
        func: Callable,
        *args,
        key: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        Execute function with coalescing.

        Args:
            func: Function to execute
            *args: Function arguments
            key: Optional explicit key
            **kwargs: Function keyword arguments

        Returns:
            Function result
        """
        # Generate key
        request_key = key or self._generate_key(func, args, kwargs)

        self._stats.total_requests += 1

        # Check cache
        cached = self._get_cached(request_key)
        if cached is not None:
            self._stats.cache_hits += 1
            return cached

        if self.config.strategy == CoalescingStrategy.FIRST_WINS:
            return await self._execute_first_wins(
                request_key, func, args, kwargs
            )

        elif self.config.strategy == CoalescingStrategy.BATCH:
            return await self._execute_batch(
                request_key, func, args, kwargs
            )

        elif self.config.strategy == CoalescingStrategy.DEDUPE:
            return await self._execute_dedupe(
                request_key, func, args, kwargs
            )

        # Fallback: direct execution
        return await self._call_func(func, args, kwargs)

    # ========================================================================
    # STRATEGIES
    # ========================================================================

    async def _execute_first_wins(
        self,
        key: str,
        func: Callable,
        args: tuple,
        kwargs: dict
    ) -> Any:
        """First request wins strategy."""
        with self._lock:
            if key in self._requests:
                # Already executing, wait for result
                request = self._requests[key]
                request.request_count += 1
                self._stats.coalesced_requests += 1

                future = asyncio.get_event_loop().create_future()
                request.waiters.append(future)

            else:
                # First request, execute
                request = CoalescedRequest(key=key, request_count=1)
                self._requests[key] = request
                future = None

        if future:
            # Wait for first request to complete
            return await future

        # Execute and notify waiters
        try:
            request.state = CoalescingState.EXECUTING
            result = await self._call_func(func, args, kwargs)
            request.state = CoalescingState.COMPLETED
            request.result = result

            # Cache result
            self._cache_result(key, result)

            # Notify waiters
            for waiter in request.waiters:
                if not waiter.done():
                    waiter.set_result(result)

            return result

        except Exception as e:
            request.state = CoalescingState.FAILED
            request.error = str(e)

            for waiter in request.waiters:
                if not waiter.done():
                    waiter.set_exception(e)

            raise

        finally:
            with self._lock:
                if key in self._requests:
                    del self._requests[key]

    async def _execute_batch(
        self,
        key: str,
        func: Callable,
        args: tuple,
        kwargs: dict
    ) -> Any:
        """Batch processing strategy."""
        func_key = self._get_func_key(func)

        future = asyncio.get_event_loop().create_future()

        with self._lock:
            if func_key not in self._batches:
                self._batches[func_key] = []

            self._batches[func_key].append((key, args, kwargs, future))

            # Check if batch is full
            if len(self._batches[func_key]) >= self.config.batch_size:
                await self._process_batch(func_key, func)

            # Start timeout timer if first in batch
            elif len(self._batches[func_key]) == 1:
                task = asyncio.create_task(
                    self._batch_timer(func_key, func)
                )
                self._batch_timers[func_key] = task

        return await future

    async def _batch_timer(self, func_key: str, func: Callable) -> None:
        """Timer for batch timeout."""
        await asyncio.sleep(self.config.batch_timeout_ms / 1000)

        with self._lock:
            if func_key in self._batches and self._batches[func_key]:
                await self._process_batch(func_key, func)

    async def _process_batch(self, func_key: str, func: Callable) -> None:
        """Process a batch of requests."""
        with self._lock:
            batch = self._batches.pop(func_key, [])

            if func_key in self._batch_timers:
                self._batch_timers[func_key].cancel()
                del self._batch_timers[func_key]

        if not batch:
            return

        self._stats.batches_processed += 1
        batch_size = len(batch)

        # Update average batch size
        n = self._stats.batches_processed
        avg = self._stats.avg_batch_size
        self._stats.avg_batch_size = (avg * (n - 1) + batch_size) / n

        # Execute for each unique key
        unique_requests: Dict[str, List[asyncio.Future]] = {}

        for key, args, kwargs, future in batch:
            if key not in unique_requests:
                unique_requests[key] = (args, kwargs, [])
            unique_requests[key][2].append(future)

            if len(unique_requests[key][2]) > 1:
                self._stats.coalesced_requests += 1

        # Execute each unique request
        for key, (args, kwargs, futures) in unique_requests.items():
            try:
                result = await self._call_func(func, args, kwargs)
                self._cache_result(key, result)

                for f in futures:
                    if not f.done():
                        f.set_result(result)

            except Exception as e:
                for f in futures:
                    if not f.done():
                        f.set_exception(e)

    async def _execute_dedupe(
        self,
        key: str,
        func: Callable,
        args: tuple,
        kwargs: dict
    ) -> Any:
        """Deduplication strategy."""
        # Check if recently executed
        now = time.time() * 1000

        with self._lock:
            if key in self._cache:
                result, cached_at = self._cache[key]
                if (now - cached_at) < self.config.dedupe_window_ms:
                    self._stats.coalesced_requests += 1
                    return result

        # Execute
        result = await self._call_func(func, args, kwargs)
        self._cache_result(key, result)

        return result

    # ========================================================================
    # KEY GENERATION
    # ========================================================================

    def _generate_key(
        self,
        func: Callable,
        args: tuple,
        kwargs: dict
    ) -> str:
        """Generate request key."""
        parts = [self._get_func_key(func)]

        if self.config.include_args:
            parts.append(json.dumps(args, sort_keys=True, default=str))

        if self.config.include_kwargs:
            parts.append(json.dumps(kwargs, sort_keys=True, default=str))

        key_str = "|".join(parts)
        return hashlib.md5(key_str.encode()).hexdigest()

    def _get_func_key(self, func: Callable) -> str:
        """Get function identifier."""
        return f"{func.__module__}.{func.__name__}"

    # ========================================================================
    # CACHING
    # ========================================================================

    def _cache_result(self, key: str, result: Any) -> None:
        """Cache a result."""
        with self._lock:
            self._cache[key] = (result, time.time() * 1000)

    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached result if valid."""
        with self._lock:
            if key not in self._cache:
                return None

            result, cached_at = self._cache[key]
            now = time.time() * 1000

            if (now - cached_at) < self.config.cache_ttl_ms:
                return result

            # Expired, remove
            del self._cache[key]
            return None

    def invalidate_cache(self, key: Optional[str] = None) -> None:
        """Invalidate cache entries."""
        with self._lock:
            if key:
                self._cache.pop(key, None)
            else:
                self._cache.clear()

    # ========================================================================
    # HELPERS
    # ========================================================================

    async def _call_func(
        self,
        func: Callable,
        args: tuple,
        kwargs: dict
    ) -> Any:
        """Call function (async or sync)."""
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return await asyncio.to_thread(func, *args, **kwargs)

    # ========================================================================
    # DECORATOR
    # ========================================================================

    def coalesce(
        self,
        key_func: Optional[Callable] = None
    ) -> Callable:
        """
        Decorator for request coalescing.

        Args:
            key_func: Optional custom key function
        """
        def decorator(func: Callable) -> Callable:
            async def wrapper(*args, **kwargs):
                key = key_func(*args, **kwargs) if key_func else None
                return await self.execute(func, *args, key=key, **kwargs)

            wrapper.__name__ = func.__name__
            wrapper.__doc__ = func.__doc__
            return wrapper

        return decorator

    # ========================================================================
    # STATS
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            'total_requests': self._stats.total_requests,
            'coalesced_requests': self._stats.coalesced_requests,
            'batches_processed': self._stats.batches_processed,
            'cache_hits': self._stats.cache_hits,
            'avg_batch_size': self._stats.avg_batch_size,
            'coalescing_rate': (
                self._stats.coalesced_requests / max(1, self._stats.total_requests)
            ),
            'active_requests': len(self._requests),
            'cache_size': len(self._cache)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

coalescing_engine = CoalescingEngine()


async def coalesce_request(func: Callable, *args, **kwargs) -> Any:
    """Execute with coalescing."""
    return await coalescing_engine.execute(func, *args, **kwargs)


def coalesce(key_func: Optional[Callable] = None) -> Callable:
    """Decorator for coalescing."""
    return coalescing_engine.coalesce(key_func)
