"""
Performance optimization utilities including caching, batching, and async operations.
Provides mechanisms for improving system performance and response times.
"""

import asyncio
import hashlib
import json
import logging
import time
from collections import OrderedDict
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar

logger = logging.getLogger("BAEL.Performance")

T = TypeVar('T')


class CacheEntry(Generic[T]):
    """Cache entry with TTL support."""

    def __init__(self, value: T, ttl_seconds: Optional[int] = None):
        self.value = value
        self.created_at = datetime.utcnow()
        self.ttl_seconds = ttl_seconds
        self.access_count = 0
        self.last_accessed = datetime.utcnow()

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.ttl_seconds is None:
            return False

        age = (datetime.utcnow() - self.created_at).total_seconds()
        return age > self.ttl_seconds

    def access(self) -> T:
        """Access the cached value."""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()
        return self.value


class LRUCache(Generic[T]):
    """Least Recently Used cache with configurable size and TTL."""

    def __init__(self, max_size: int = 1000, default_ttl: Optional[int] = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, CacheEntry[T]] = OrderedDict()
        self.hits = 0
        self.misses = 0

    def _make_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_data = json.dumps({
            "args": args,
            "kwargs": kwargs
        }, sort_keys=True, default=str)
        return hashlib.md5(key_data.encode()).hexdigest()

    def get(self, key: str) -> Optional[T]:
        """Get value from cache."""
        if key not in self.cache:
            self.misses += 1
            return None

        entry = self.cache[key]
        if entry.is_expired():
            del self.cache[key]
            self.misses += 1
            return None

        # Move to end (most recently used)
        self.cache.move_to_end(key)
        self.hits += 1
        return entry.access()

    def set(self, key: str, value: T, ttl: Optional[int] = None):
        """Set value in cache."""
        # Remove oldest if at capacity
        if len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)

        ttl = ttl or self.default_ttl
        self.cache[key] = CacheEntry(value, ttl)
        self.cache.move_to_end(key)

    def clear(self):
        """Clear all cache entries."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0

    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0

        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "total_requests": total
        }


def cached(ttl: Optional[int] = 3600, max_size: int = 1000):
    """Decorator for caching async function results."""
    cache = LRUCache(max_size=max_size, default_ttl=ttl)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = cache._make_key(*args, **kwargs)

            # Check cache
            cached_value = cache.get(key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_value

            # Execute function
            logger.debug(f"Cache miss for {func.__name__}, executing")
            result = await func(*args, **kwargs)

            # Store in cache
            cache.set(key, result, ttl)
            return result

        wrapper.cache = cache
        wrapper.clear_cache = cache.clear
        wrapper.get_statistics = cache.get_statistics

        return wrapper

    return decorator


class BatchProcessor:
    """Process items in batches for efficiency."""

    def __init__(self, batch_size: int = 10, timeout_seconds: int = 5):
        self.batch_size = batch_size
        self.timeout_seconds = timeout_seconds
        self.queue: List[Any] = []
        self.lock = asyncio.Lock()
        self.pending_future: Optional[asyncio.Future] = None

    async def add(self, item: Any) -> Optional[List[Any]]:
        """Add item to batch, returning batch if ready."""
        async with self.lock:
            self.queue.append(item)

            if len(self.queue) >= self.batch_size:
                batch = self.queue[:]
                self.queue.clear()
                return batch

        return None

    async def flush(self) -> Optional[List[Any]]:
        """Force flush current batch."""
        async with self.lock:
            if self.queue:
                batch = self.queue[:]
                self.queue.clear()
                return batch

        return None

    async def process_with_batching(self, items: List[Any],
                                   processor: Callable[[List[Any]], Any]) -> List[Any]:
        """Process items in batches."""
        results = []

        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            logger.debug(f"Processing batch {i // self.batch_size + 1} with {len(batch)} items")
            result = await processor(batch)
            results.extend(result if isinstance(result, list) else [result])

        return results


class PerformanceMonitor:
    """Monitor and track performance metrics."""

    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
        self.operation_count: Dict[str, int] = {}

    def record_operation(self, operation: str, duration_ms: float):
        """Record operation duration."""
        if operation not in self.metrics:
            self.metrics[operation] = []
            self.operation_count[operation] = 0

        self.metrics[operation].append(duration_ms)
        self.operation_count[operation] += 1

    def get_statistics(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """Get performance statistics."""
        if operation:
            if operation not in self.metrics:
                return {"error": f"No metrics for operation {operation}"}

            durations = self.metrics[operation]
            return {
                "operation": operation,
                "count": len(durations),
                "min_ms": min(durations),
                "max_ms": max(durations),
                "avg_ms": sum(durations) / len(durations),
                "median_ms": sorted(durations)[len(durations) // 2] if durations else 0,
                "total_time_ms": sum(durations)
            }

        # Return all statistics
        stats = {}
        for op in self.metrics.keys():
            stats[op] = self.get_statistics(op)

        return stats

    def reset(self):
        """Reset all metrics."""
        self.metrics.clear()
        self.operation_count.clear()


def measure_performance(operation: str, monitor: PerformanceMonitor):
    """Decorator to measure operation performance."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration_ms = (time.time() - start_time) * 1000
                monitor.record_operation(operation, duration_ms)
                logger.debug(f"{operation} took {duration_ms:.2f}ms")

        return wrapper

    return decorator


class AsyncTaskPool:
    """Manage a pool of async tasks for concurrent execution."""

    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.tasks: List[asyncio.Task] = []

    async def submit(self, coro):
        """Submit a coroutine to the pool."""
        async def bounded_coro():
            async with self.semaphore:
                return await coro

        task = asyncio.create_task(bounded_coro())
        self.tasks.append(task)
        return task

    async def wait_all(self):
        """Wait for all tasks to complete."""
        results = await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()
        return results

    def get_active_count(self) -> int:
        """Get number of active tasks."""
        return len([t for t in self.tasks if not t.done()])


# Global instances
performance_monitor = PerformanceMonitor()
async_task_pool = AsyncTaskPool(max_concurrent=20)
