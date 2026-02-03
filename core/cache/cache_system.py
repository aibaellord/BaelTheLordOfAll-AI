"""
BAEL - Advanced Caching System
Multi-layer intelligent caching with eviction policies.

Features:
- Multi-layer cache (L1/L2/L3)
- Multiple eviction policies
- TTL support
- Cache warming
- Compression
- Distributed cache support
- Cache analytics
"""

import asyncio
import hashlib
import json
import logging
import pickle
import time
import zlib
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, TypeVar,
                    Union)

logger = logging.getLogger(__name__)

T = TypeVar("T")


# =============================================================================
# ENUMS
# =============================================================================

class EvictionPolicy(Enum):
    """Cache eviction policies."""
    LRU = "lru"         # Least Recently Used
    LFU = "lfu"         # Least Frequently Used
    FIFO = "fifo"       # First In First Out
    TTL = "ttl"         # Time To Live
    RANDOM = "random"   # Random eviction
    SIZE = "size"       # Largest first


class CacheLayer(Enum):
    """Cache layer identifiers."""
    L1_MEMORY = "l1_memory"     # Fast in-memory
    L2_LOCAL = "l2_local"       # Local disk
    L3_DISTRIBUTED = "l3_distributed"  # Redis/Memcached


class CompressionLevel(Enum):
    """Compression levels."""
    NONE = 0
    FAST = 1
    BALANCED = 6
    BEST = 9


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class CacheEntry(Generic[T]):
    """A cache entry with metadata."""
    key: str
    value: T
    created_at: float
    last_accessed: float
    access_count: int = 0
    ttl: Optional[float] = None  # seconds
    size_bytes: int = 0
    compressed: bool = False
    tags: Set[str] = field(default_factory=set)

    @property
    def is_expired(self) -> bool:
        if self.ttl is None:
            return False
        return time.time() > (self.created_at + self.ttl)

    @property
    def age(self) -> float:
        return time.time() - self.created_at


@dataclass
class CacheStats:
    """Cache statistics."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expirations: int = 0
    writes: int = 0
    bytes_read: int = 0
    bytes_written: int = 0
    compression_savings: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def miss_rate(self) -> float:
        return 1.0 - self.hit_rate


# =============================================================================
# ABSTRACT CACHE
# =============================================================================

class BaseCache(ABC, Generic[T]):
    """Abstract base cache."""

    @abstractmethod
    async def get(self, key: str) -> Optional[T]:
        pass

    @abstractmethod
    async def set(
        self,
        key: str,
        value: T,
        ttl: Optional[float] = None,
        tags: Optional[Set[str]] = None
    ) -> None:
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass

    @abstractmethod
    async def clear(self) -> None:
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        pass


# =============================================================================
# MEMORY CACHE (L1)
# =============================================================================

class MemoryCache(BaseCache[T]):
    """Fast in-memory cache with eviction."""

    def __init__(
        self,
        max_size: int = 1000,
        policy: EvictionPolicy = EvictionPolicy.LRU,
        default_ttl: Optional[float] = None,
        compression: CompressionLevel = CompressionLevel.NONE
    ):
        self.max_size = max_size
        self.policy = policy
        self.default_ttl = default_ttl
        self.compression = compression

        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._access_counts: Dict[str, int] = {}
        self._stats = CacheStats()
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[T]:
        async with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._stats.misses += 1
                return None

            # Check expiration
            if entry.is_expired:
                del self._cache[key]
                self._stats.expirations += 1
                self._stats.misses += 1
                return None

            # Update access metadata
            entry.last_accessed = time.time()
            entry.access_count += 1
            self._access_counts[key] = entry.access_count

            # Move to end for LRU
            if self.policy == EvictionPolicy.LRU:
                self._cache.move_to_end(key)

            self._stats.hits += 1
            self._stats.bytes_read += entry.size_bytes

            value = entry.value
            if entry.compressed:
                value = self._decompress(value)

            return value

    async def set(
        self,
        key: str,
        value: T,
        ttl: Optional[float] = None,
        tags: Optional[Set[str]] = None
    ) -> None:
        async with self._lock:
            # Evict if necessary
            while len(self._cache) >= self.max_size:
                await self._evict_one()

            # Compress if needed
            stored_value = value
            compressed = False
            original_size = self._get_size(value)

            if self.compression != CompressionLevel.NONE:
                stored_value = self._compress(value)
                compressed = True
                compressed_size = self._get_size(stored_value)
                self._stats.compression_savings += original_size - compressed_size

            entry = CacheEntry(
                key=key,
                value=stored_value,
                created_at=time.time(),
                last_accessed=time.time(),
                ttl=ttl or self.default_ttl,
                size_bytes=self._get_size(stored_value),
                compressed=compressed,
                tags=tags or set()
            )

            self._cache[key] = entry
            self._access_counts[key] = 0
            self._stats.writes += 1
            self._stats.bytes_written += entry.size_bytes

    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._access_counts.pop(key, None)
                return True
            return False

    async def clear(self) -> None:
        async with self._lock:
            self._cache.clear()
            self._access_counts.clear()

    async def exists(self, key: str) -> bool:
        async with self._lock:
            entry = self._cache.get(key)
            if entry and not entry.is_expired:
                return True
            return False

    async def _evict_one(self) -> None:
        """Evict one entry based on policy."""
        if not self._cache:
            return

        key_to_evict = None

        if self.policy == EvictionPolicy.LRU:
            key_to_evict = next(iter(self._cache))

        elif self.policy == EvictionPolicy.LFU:
            key_to_evict = min(
                self._cache.keys(),
                key=lambda k: self._access_counts.get(k, 0)
            )

        elif self.policy == EvictionPolicy.FIFO:
            key_to_evict = next(iter(self._cache))

        elif self.policy == EvictionPolicy.TTL:
            # Evict oldest or expired
            for key, entry in self._cache.items():
                if entry.is_expired:
                    key_to_evict = key
                    break
            if not key_to_evict:
                key_to_evict = min(
                    self._cache.keys(),
                    key=lambda k: self._cache[k].created_at
                )

        elif self.policy == EvictionPolicy.SIZE:
            key_to_evict = max(
                self._cache.keys(),
                key=lambda k: self._cache[k].size_bytes
            )

        elif self.policy == EvictionPolicy.RANDOM:
            import random
            key_to_evict = random.choice(list(self._cache.keys()))

        if key_to_evict:
            del self._cache[key_to_evict]
            self._access_counts.pop(key_to_evict, None)
            self._stats.evictions += 1

    def _compress(self, value: Any) -> bytes:
        """Compress a value."""
        data = pickle.dumps(value)
        return zlib.compress(data, level=self.compression.value)

    def _decompress(self, data: bytes) -> Any:
        """Decompress a value."""
        decompressed = zlib.decompress(data)
        return pickle.loads(decompressed)

    def _get_size(self, value: Any) -> int:
        """Get approximate size in bytes."""
        try:
            return len(pickle.dumps(value))
        except Exception:
            return 0

    async def get_by_tag(self, tag: str) -> List[T]:
        """Get all entries with a specific tag."""
        results = []
        async with self._lock:
            for entry in self._cache.values():
                if tag in entry.tags and not entry.is_expired:
                    value = entry.value
                    if entry.compressed:
                        value = self._decompress(value)
                    results.append(value)
        return results

    async def delete_by_tag(self, tag: str) -> int:
        """Delete all entries with a specific tag."""
        count = 0
        async with self._lock:
            keys_to_delete = [
                key for key, entry in self._cache.items()
                if tag in entry.tags
            ]
            for key in keys_to_delete:
                del self._cache[key]
                count += 1
        return count

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        return self._stats


# =============================================================================
# LOCAL DISK CACHE (L2)
# =============================================================================

class DiskCache(BaseCache[T]):
    """Local disk-based cache."""

    def __init__(
        self,
        cache_dir: str = ".cache/bael",
        max_size_mb: int = 100,
        default_ttl: Optional[float] = None
    ):
        import os
        self.cache_dir = cache_dir
        self.max_size_mb = max_size_mb
        self.default_ttl = default_ttl
        self._stats = CacheStats()

        # Ensure directory exists
        os.makedirs(cache_dir, exist_ok=True)

    def _key_to_path(self, key: str) -> str:
        """Convert key to file path."""
        import os

        # Hash the key for filesystem safety
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{key_hash}.cache")

    async def get(self, key: str) -> Optional[T]:
        import os
        path = self._key_to_path(key)

        if not os.path.exists(path):
            self._stats.misses += 1
            return None

        try:
            with open(path, "rb") as f:
                entry = pickle.load(f)

            # Check expiration
            if entry.is_expired:
                os.remove(path)
                self._stats.expirations += 1
                self._stats.misses += 1
                return None

            self._stats.hits += 1
            self._stats.bytes_read += entry.size_bytes
            return entry.value

        except Exception as e:
            logger.warning(f"Disk cache read error: {e}")
            self._stats.misses += 1
            return None

    async def set(
        self,
        key: str,
        value: T,
        ttl: Optional[float] = None,
        tags: Optional[Set[str]] = None
    ) -> None:
        path = self._key_to_path(key)

        entry = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            last_accessed=time.time(),
            ttl=ttl or self.default_ttl,
            size_bytes=0,
            tags=tags or set()
        )

        try:
            data = pickle.dumps(entry)
            entry.size_bytes = len(data)

            with open(path, "wb") as f:
                pickle.dump(entry, f)

            self._stats.writes += 1
            self._stats.bytes_written += entry.size_bytes

        except Exception as e:
            logger.error(f"Disk cache write error: {e}")

    async def delete(self, key: str) -> bool:
        import os
        path = self._key_to_path(key)

        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    async def clear(self) -> None:
        import os
        import shutil
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)
            os.makedirs(self.cache_dir, exist_ok=True)

    async def exists(self, key: str) -> bool:
        import os
        return os.path.exists(self._key_to_path(key))

    def get_stats(self) -> CacheStats:
        return self._stats


# =============================================================================
# DISTRIBUTED CACHE (L3)
# =============================================================================

class DistributedCache(BaseCache[T]):
    """Distributed cache using Redis."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        prefix: str = "bael:",
        default_ttl: Optional[int] = None
    ):
        self.redis_url = redis_url
        self.prefix = prefix
        self.default_ttl = default_ttl
        self._client = None
        self._stats = CacheStats()

    async def _get_client(self):
        """Get or create Redis client."""
        if self._client is None:
            try:
                import redis.asyncio as redis
                self._client = await redis.from_url(self.redis_url)
            except ImportError:
                logger.warning("Redis not available")
                return None
        return self._client

    def _make_key(self, key: str) -> str:
        return f"{self.prefix}{key}"

    async def get(self, key: str) -> Optional[T]:
        client = await self._get_client()
        if not client:
            self._stats.misses += 1
            return None

        try:
            data = await client.get(self._make_key(key))
            if data is None:
                self._stats.misses += 1
                return None

            value = pickle.loads(data)
            self._stats.hits += 1
            self._stats.bytes_read += len(data)
            return value

        except Exception as e:
            logger.warning(f"Redis get error: {e}")
            self._stats.misses += 1
            return None

    async def set(
        self,
        key: str,
        value: T,
        ttl: Optional[float] = None,
        tags: Optional[Set[str]] = None
    ) -> None:
        client = await self._get_client()
        if not client:
            return

        try:
            data = pickle.dumps(value)
            ttl_seconds = int(ttl or self.default_ttl or 0)

            if ttl_seconds > 0:
                await client.setex(self._make_key(key), ttl_seconds, data)
            else:
                await client.set(self._make_key(key), data)

            self._stats.writes += 1
            self._stats.bytes_written += len(data)

            # Store tags if provided
            if tags:
                for tag in tags:
                    await client.sadd(f"{self.prefix}tag:{tag}", key)

        except Exception as e:
            logger.error(f"Redis set error: {e}")

    async def delete(self, key: str) -> bool:
        client = await self._get_client()
        if not client:
            return False

        try:
            result = await client.delete(self._make_key(key))
            return result > 0
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False

    async def clear(self) -> None:
        client = await self._get_client()
        if not client:
            return

        try:
            keys = await client.keys(f"{self.prefix}*")
            if keys:
                await client.delete(*keys)
        except Exception as e:
            logger.error(f"Redis clear error: {e}")

    async def exists(self, key: str) -> bool:
        client = await self._get_client()
        if not client:
            return False

        try:
            return await client.exists(self._make_key(key)) > 0
        except Exception:
            return False

    def get_stats(self) -> CacheStats:
        return self._stats


# =============================================================================
# MULTI-LAYER CACHE
# =============================================================================

class MultiLayerCache(Generic[T]):
    """Multi-layer cache with write-through and read-through."""

    def __init__(
        self,
        l1_size: int = 1000,
        l1_policy: EvictionPolicy = EvictionPolicy.LRU,
        l2_enabled: bool = True,
        l2_cache_dir: str = ".cache/bael",
        l3_enabled: bool = False,
        l3_redis_url: str = "redis://localhost:6379"
    ):
        # L1: Memory (fastest)
        self.l1 = MemoryCache[T](
            max_size=l1_size,
            policy=l1_policy,
            compression=CompressionLevel.NONE
        )

        # L2: Disk (medium)
        self.l2: Optional[DiskCache] = None
        if l2_enabled:
            self.l2 = DiskCache(cache_dir=l2_cache_dir)

        # L3: Distributed (slowest, largest)
        self.l3: Optional[DistributedCache] = None
        if l3_enabled:
            self.l3 = DistributedCache(redis_url=l3_redis_url)

    async def get(self, key: str) -> Optional[T]:
        """Get from cache, checking layers in order."""
        # Try L1
        value = await self.l1.get(key)
        if value is not None:
            return value

        # Try L2
        if self.l2:
            value = await self.l2.get(key)
            if value is not None:
                # Promote to L1
                await self.l1.set(key, value)
                return value

        # Try L3
        if self.l3:
            value = await self.l3.get(key)
            if value is not None:
                # Promote to L1 and L2
                await self.l1.set(key, value)
                if self.l2:
                    await self.l2.set(key, value)
                return value

        return None

    async def set(
        self,
        key: str,
        value: T,
        ttl: Optional[float] = None,
        tags: Optional[Set[str]] = None,
        layers: Optional[List[CacheLayer]] = None
    ) -> None:
        """Set in cache, write-through to all layers."""
        target_layers = layers or [
            CacheLayer.L1_MEMORY,
            CacheLayer.L2_LOCAL,
            CacheLayer.L3_DISTRIBUTED
        ]

        if CacheLayer.L1_MEMORY in target_layers:
            await self.l1.set(key, value, ttl, tags)

        if CacheLayer.L2_LOCAL in target_layers and self.l2:
            await self.l2.set(key, value, ttl, tags)

        if CacheLayer.L3_DISTRIBUTED in target_layers and self.l3:
            await self.l3.set(key, value, ttl, tags)

    async def delete(self, key: str) -> bool:
        """Delete from all layers."""
        results = [await self.l1.delete(key)]

        if self.l2:
            results.append(await self.l2.delete(key))
        if self.l3:
            results.append(await self.l3.delete(key))

        return any(results)

    async def clear(self) -> None:
        """Clear all layers."""
        await self.l1.clear()
        if self.l2:
            await self.l2.clear()
        if self.l3:
            await self.l3.clear()

    def get_all_stats(self) -> Dict[str, CacheStats]:
        """Get stats from all layers."""
        stats = {"l1": self.l1.get_stats()}
        if self.l2:
            stats["l2"] = self.l2.get_stats()
        if self.l3:
            stats["l3"] = self.l3.get_stats()
        return stats


# =============================================================================
# CACHE DECORATOR
# =============================================================================

def cached(
    cache: BaseCache,
    ttl: Optional[float] = None,
    key_fn: Optional[Callable[..., str]] = None,
    tags: Optional[Set[str]] = None
):
    """Decorator for caching function results."""

    def decorator(func: Callable):
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            if key_fn:
                cache_key = key_fn(*args, **kwargs)
            else:
                key_parts = [func.__name__]
                key_parts.extend(str(a) for a in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)

            # Try to get from cache
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Call function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # Store in cache
            await cache.set(cache_key, result, ttl=ttl, tags=tags)

            return result

        def sync_wrapper(*args, **kwargs):
            return asyncio.get_event_loop().run_until_complete(
                async_wrapper(*args, **kwargs)
            )

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# =============================================================================
# CACHE WARMER
# =============================================================================

class CacheWarmer:
    """Pre-populates cache with expected data."""

    def __init__(self, cache: BaseCache):
        self.cache = cache
        self.warmup_tasks: List[Callable] = []

    def register(self, generator: Callable[[], Dict[str, Any]]):
        """Register a warmup generator."""
        self.warmup_tasks.append(generator)

    async def warm(self) -> int:
        """Execute all warmup tasks."""
        count = 0

        for task in self.warmup_tasks:
            try:
                if asyncio.iscoroutinefunction(task):
                    data = await task()
                else:
                    data = task()

                for key, value in data.items():
                    await self.cache.set(key, value)
                    count += 1

            except Exception as e:
                logger.error(f"Cache warmup error: {e}")

        logger.info(f"Cache warmed with {count} entries")
        return count


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

async def example_caching():
    """Demonstrate caching capabilities."""
    # Create multi-layer cache
    cache = MultiLayerCache[Any](
        l1_size=100,
        l1_policy=EvictionPolicy.LRU,
        l2_enabled=False,  # Disable disk for demo
        l3_enabled=False   # Disable redis for demo
    )

    # Basic operations
    await cache.set("key1", {"data": "value1"}, ttl=60)
    await cache.set("key2", [1, 2, 3], tags={"numbers"})

    value1 = await cache.get("key1")
    print(f"Retrieved: {value1}")

    # Get stats
    stats = cache.get_all_stats()
    print(f"L1 stats: hits={stats['l1'].hits}, misses={stats['l1'].misses}")

    # Use decorator
    @cached(cache.l1, ttl=300)
    async def expensive_operation(n: int):
        await asyncio.sleep(0.1)  # Simulate slow operation
        return n * n

    result1 = await expensive_operation(5)  # Computed
    result2 = await expensive_operation(5)  # Cached
    print(f"Results: {result1}, {result2}")

    # Cache warmer
    warmer = CacheWarmer(cache.l1)
    warmer.register(lambda: {"common1": "value1", "common2": "value2"})
    await warmer.warm()


if __name__ == "__main__":
    asyncio.run(example_caching())
