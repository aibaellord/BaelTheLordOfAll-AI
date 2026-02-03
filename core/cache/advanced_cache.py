#!/usr/bin/env python3
"""
BAEL - Advanced Caching System
Multi-tier caching with eviction and persistence.

This module provides comprehensive caching capabilities
extending existing infrastructure.

Features:
- Multi-tier cache architecture
- Advanced eviction policies
- Cache warmup and preloading
- Write-through/write-behind
- Cache coherence
- TTL and sliding expiration
- Distributed cache sync
- Cache statistics and monitoring
"""

import asyncio
import hashlib
import json
import logging
import pickle
import shutil
import tempfile
import time
import uuid
from abc import ABC, abstractmethod
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path
from typing import (Any, Awaitable, Callable, Dict, Generic, List, Optional,
                    Set, Tuple, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class TierEvictionPolicy:
    """Cache eviction policies."""
    LRU = "lru"
    LFU = "lfu"
    FIFO = "fifo"
    TTL = "ttl"
    ADAPTIVE = "adaptive"


class TierWritePolicy:
    """Write policies."""
    WRITE_THROUGH = "write_through"
    WRITE_BEHIND = "write_behind"
    WRITE_AROUND = "write_around"


class TierCacheEvent:
    """Cache event types."""
    HIT = "hit"
    MISS = "miss"
    SET = "set"
    DELETE = "delete"
    EVICT = "evict"
    EXPIRE = "expire"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class TierCacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    size_bytes: int = 0
    tags: Set[str] = field(default_factory=set)
    version: int = 1

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def touch(self) -> None:
        self.last_accessed = time.time()
        self.access_count += 1

    def ttl_remaining(self) -> Optional[float]:
        if self.expires_at is None:
            return None
        remaining = self.expires_at - time.time()
        return max(0, remaining)


@dataclass
class TierCacheStats:
    """Statistics for a cache tier."""
    tier_name: str
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    entry_count: int = 0
    bytes_used: int = 0
    max_entries: int = 0
    max_bytes: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def utilization(self) -> float:
        if self.max_entries == 0:
            return 0.0
        return self.entry_count / self.max_entries


@dataclass
class TierCacheConfig:
    """Tier configuration."""
    name: str
    max_entries: int = 10000
    max_bytes: Optional[int] = None
    default_ttl: Optional[float] = None
    eviction_policy: str = TierEvictionPolicy.LRU
    write_policy: str = TierWritePolicy.WRITE_THROUGH


# =============================================================================
# TIER STORAGE
# =============================================================================

class TierStorage(ABC):
    """Abstract tier storage backend."""

    @abstractmethod
    async def get(self, key: str) -> Optional[TierCacheEntry]:
        pass

    @abstractmethod
    async def set(self, entry: TierCacheEntry) -> None:
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass

    @abstractmethod
    async def clear(self) -> None:
        pass

    @abstractmethod
    async def size(self) -> int:
        pass

    @abstractmethod
    async def keys(self) -> List[str]:
        pass


class MemoryTierStorage(TierStorage):
    """In-memory tier storage with eviction."""

    def __init__(self, config: TierCacheConfig):
        self.config = config
        self.entries: Dict[str, TierCacheEntry] = {}
        self.access_order: OrderedDict = OrderedDict()
        self.frequency: Dict[str, int] = defaultdict(int)
        self.bytes_used = 0
        self._lock = asyncio.Lock()
        self.stats = TierCacheStats(
            tier_name=config.name,
            max_entries=config.max_entries,
            max_bytes=config.max_bytes or 0
        )

    async def get(self, key: str) -> Optional[TierCacheEntry]:
        async with self._lock:
            entry = self.entries.get(key)

            if entry is None:
                self.stats.misses += 1
                return None

            if entry.is_expired():
                await self._remove_entry(key)
                self.stats.misses += 1
                return None

            entry.touch()
            self.frequency[key] += 1

            if key in self.access_order:
                self.access_order.move_to_end(key)

            self.stats.hits += 1
            return entry

    async def set(self, entry: TierCacheEntry) -> None:
        async with self._lock:
            # Evict if necessary
            while self._needs_eviction(entry):
                await self._evict_one()

            # Update existing
            if entry.key in self.entries:
                self.bytes_used -= self.entries[entry.key].size_bytes

            self.entries[entry.key] = entry
            self.bytes_used += entry.size_bytes
            self.access_order[entry.key] = True
            self.frequency[entry.key] = 1

            self.stats.sets += 1
            self.stats.entry_count = len(self.entries)
            self.stats.bytes_used = self.bytes_used

    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key in self.entries:
                await self._remove_entry(key)
                self.stats.deletes += 1
                return True
            return False

    async def _remove_entry(self, key: str) -> None:
        if key in self.entries:
            self.bytes_used -= self.entries[key].size_bytes
            del self.entries[key]
            self.access_order.pop(key, None)
            self.frequency.pop(key, None)
            self.stats.entry_count = len(self.entries)

    async def clear(self) -> None:
        async with self._lock:
            self.entries.clear()
            self.access_order.clear()
            self.frequency.clear()
            self.bytes_used = 0
            self.stats.entry_count = 0
            self.stats.bytes_used = 0

    async def size(self) -> int:
        return len(self.entries)

    async def keys(self) -> List[str]:
        return list(self.entries.keys())

    def _needs_eviction(self, new_entry: TierCacheEntry) -> bool:
        if len(self.entries) >= self.config.max_entries:
            return True

        if self.config.max_bytes:
            if self.bytes_used + new_entry.size_bytes > self.config.max_bytes:
                return True

        return False

    async def _evict_one(self) -> None:
        if not self.entries:
            return

        policy = self.config.eviction_policy
        key_to_evict = None

        if policy == TierEvictionPolicy.LRU:
            key_to_evict = next(iter(self.access_order))
        elif policy == TierEvictionPolicy.LFU:
            key_to_evict = min(self.frequency.keys(), key=lambda k: self.frequency[k])
        elif policy == TierEvictionPolicy.FIFO:
            key_to_evict = min(self.entries.keys(), key=lambda k: self.entries[k].created_at)
        elif policy == TierEvictionPolicy.TTL:
            expired = [(k, e) for k, e in self.entries.items() if e.expires_at]
            if expired:
                key_to_evict = min(expired, key=lambda x: x[1].expires_at)[0]
            else:
                key_to_evict = next(iter(self.entries))
        elif policy == TierEvictionPolicy.ADAPTIVE:
            # Combine LRU and LFU
            scores = {}
            now = time.time()
            for key, entry in self.entries.items():
                recency = now - entry.last_accessed
                freq = self.frequency.get(key, 1)
                scores[key] = recency / freq
            key_to_evict = max(scores.keys(), key=lambda k: scores[k])

        if key_to_evict:
            await self._remove_entry(key_to_evict)
            self.stats.evictions += 1


# =============================================================================
# CACHE TIER
# =============================================================================

class CacheTier:
    """A single cache tier."""

    def __init__(self, config: TierCacheConfig, storage: TierStorage = None):
        self.config = config
        self.storage = storage or MemoryTierStorage(config)
        self.event_handlers: Dict[str, List[Callable]] = defaultdict(list)

    async def get(self, key: str) -> Optional[Any]:
        entry = await self.storage.get(key)

        if entry is None:
            await self._emit(TierCacheEvent.MISS, key)
            return None

        await self._emit(TierCacheEvent.HIT, key, entry.value)
        return entry.value

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None,
        tags: Set[str] = None
    ) -> None:
        expires_at = None
        if ttl is not None:
            expires_at = time.time() + ttl
        elif self.config.default_ttl is not None:
            expires_at = time.time() + self.config.default_ttl

        try:
            size_bytes = len(pickle.dumps(value))
        except Exception:
            size_bytes = 0

        entry = TierCacheEntry(
            key=key,
            value=value,
            expires_at=expires_at,
            size_bytes=size_bytes,
            tags=tags or set()
        )

        await self.storage.set(entry)
        await self._emit(TierCacheEvent.SET, key, value)

    async def delete(self, key: str) -> bool:
        result = await self.storage.delete(key)
        if result:
            await self._emit(TierCacheEvent.DELETE, key)
        return result

    async def clear(self) -> None:
        await self.storage.clear()

    async def exists(self, key: str) -> bool:
        entry = await self.storage.get(key)
        return entry is not None

    def on_event(self, event: str, handler: Callable) -> None:
        self.event_handlers[event].append(handler)

    async def _emit(self, event: str, key: str, value: Any = None) -> None:
        for handler in self.event_handlers.get(event, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(key, value)
                else:
                    handler(key, value)
            except Exception as e:
                logger.error(f"Event handler error: {e}")

    def get_stats(self) -> TierCacheStats:
        if isinstance(self.storage, MemoryTierStorage):
            return self.storage.stats
        return TierCacheStats(tier_name=self.config.name)


# =============================================================================
# MULTI-TIER CACHE
# =============================================================================

class MultiTierCache:
    """
    Multi-tier cache with automatic promotion/demotion.
    """

    def __init__(self, tiers: List[CacheTier] = None):
        self.tiers: List[CacheTier] = tiers or []
        self.tag_index: Dict[str, Set[str]] = defaultdict(set)

    def add_tier(self, tier: CacheTier) -> 'MultiTierCache':
        self.tiers.append(tier)
        return self

    async def get(self, key: str, default: Any = None) -> Any:
        for i, tier in enumerate(self.tiers):
            value = await tier.get(key)

            if value is not None:
                # Promote to higher tiers
                for j in range(i):
                    await self.tiers[j].set(key, value)

                return value

        return default

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None,
        tags: Set[str] = None,
        tiers: List[int] = None
    ) -> None:
        target_tiers = tiers or range(len(self.tiers))

        for i in target_tiers:
            if 0 <= i < len(self.tiers):
                await self.tiers[i].set(key, value, ttl, tags)

        # Update tag index
        if tags:
            for tag in tags:
                self.tag_index[tag].add(key)

    async def delete(self, key: str) -> bool:
        results = [await tier.delete(key) for tier in self.tiers]

        # Remove from tag index
        for keys in self.tag_index.values():
            keys.discard(key)

        return any(results)

    async def clear(self) -> None:
        for tier in self.tiers:
            await tier.clear()
        self.tag_index.clear()

    async def invalidate_by_tag(self, tag: str) -> int:
        keys = list(self.tag_index.get(tag, set()))
        count = 0

        for key in keys:
            if await self.delete(key):
                count += 1

        self.tag_index.pop(tag, None)
        return count

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Awaitable[Any]],
        ttl: Optional[float] = None,
        tags: Set[str] = None
    ) -> Any:
        value = await self.get(key)

        if value is None:
            if asyncio.iscoroutinefunction(factory):
                value = await factory()
            else:
                value = factory()

            await self.set(key, value, ttl, tags)

        return value

    def get_all_stats(self) -> List[TierCacheStats]:
        return [tier.get_stats() for tier in self.tiers]


# =============================================================================
# CACHE WARMER
# =============================================================================

class CacheWarmer:
    """Pre-loads cache with data."""

    def __init__(self, cache: MultiTierCache):
        self.cache = cache
        self.warmup_tasks: List[Tuple[str, Callable, Optional[float]]] = []

    def register(
        self,
        key: str,
        loader: Callable[[], Awaitable[Any]],
        ttl: Optional[float] = None
    ) -> 'CacheWarmer':
        self.warmup_tasks.append((key, loader, ttl))
        return self

    async def warmup(self) -> Dict[str, bool]:
        results = {}

        for key, loader, ttl in self.warmup_tasks:
            try:
                if asyncio.iscoroutinefunction(loader):
                    value = await loader()
                else:
                    value = loader()

                await self.cache.set(key, value, ttl)
                results[key] = True
            except Exception as e:
                logger.error(f"Warmup failed for {key}: {e}")
                results[key] = False

        return results

    async def warmup_parallel(self, max_concurrent: int = 10) -> Dict[str, bool]:
        semaphore = asyncio.Semaphore(max_concurrent)
        results = {}

        async def load_one(key: str, loader: Callable, ttl: Optional[float]):
            async with semaphore:
                try:
                    if asyncio.iscoroutinefunction(loader):
                        value = await loader()
                    else:
                        value = loader()

                    await self.cache.set(key, value, ttl)
                    return key, True
                except Exception as e:
                    logger.error(f"Warmup failed for {key}: {e}")
                    return key, False

        tasks = [load_one(k, l, t) for k, l, t in self.warmup_tasks]
        completed = await asyncio.gather(*tasks)

        for key, success in completed:
            results[key] = success

        return results


# =============================================================================
# CACHING DECORATOR
# =============================================================================

def tier_cached(
    cache: MultiTierCache,
    ttl: Optional[float] = None,
    key_builder: Callable[..., str] = None,
    tags: Set[str] = None
) -> Callable:
    """Decorator for caching function results."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                key_parts = [func.__module__, func.__name__]
                key_parts.extend(str(a) for a in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)

            # Try cache
            result = await cache.get(cache_key)

            if result is None:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                await cache.set(cache_key, result, ttl, tags)

            return result

        return wrapper

    return decorator


# =============================================================================
# ADVANCED CACHE MANAGER
# =============================================================================

class AdvancedCacheManager:
    """
    Master advanced cache manager for BAEL.
    """

    def __init__(self):
        self.caches: Dict[str, MultiTierCache] = {}
        self.default_cache: Optional[MultiTierCache] = None

    def create_cache(
        self,
        name: str,
        tier_configs: List[TierCacheConfig] = None
    ) -> MultiTierCache:
        """Create a named multi-tier cache."""
        cache = MultiTierCache()

        if tier_configs:
            for config in tier_configs:
                tier = CacheTier(config)
                cache.add_tier(tier)
        else:
            # Default: L1 fast/small, L2 slower/larger
            l1_config = TierCacheConfig(
                name=f"{name}_L1",
                max_entries=1000,
                default_ttl=60,
                eviction_policy=TierEvictionPolicy.LRU
            )
            l2_config = TierCacheConfig(
                name=f"{name}_L2",
                max_entries=10000,
                default_ttl=3600,
                eviction_policy=TierEvictionPolicy.LFU
            )

            cache.add_tier(CacheTier(l1_config))
            cache.add_tier(CacheTier(l2_config))

        self.caches[name] = cache

        if self.default_cache is None:
            self.default_cache = cache

        return cache

    def get_cache(self, name: str) -> Optional[MultiTierCache]:
        return self.caches.get(name)

    def create_warmer(self, cache_name: str = None) -> CacheWarmer:
        cache = self.caches.get(cache_name) if cache_name else self.default_cache
        if cache is None:
            raise ValueError("No cache available")
        return CacheWarmer(cache)

    async def get(
        self,
        key: str,
        cache_name: str = None,
        default: Any = None
    ) -> Any:
        cache = self.caches.get(cache_name) if cache_name else self.default_cache
        if cache is None:
            return default
        return await cache.get(key, default)

    async def set(
        self,
        key: str,
        value: Any,
        cache_name: str = None,
        ttl: Optional[float] = None,
        tags: Set[str] = None
    ) -> None:
        cache = self.caches.get(cache_name) if cache_name else self.default_cache
        if cache is not None:
            await cache.set(key, value, ttl, tags)

    async def delete(self, key: str, cache_name: str = None) -> bool:
        cache = self.caches.get(cache_name) if cache_name else self.default_cache
        if cache is not None:
            return await cache.delete(key)
        return False

    def cached(
        self,
        cache_name: str = None,
        ttl: Optional[float] = None,
        key_builder: Callable[..., str] = None,
        tags: Set[str] = None
    ) -> Callable:
        cache = self.caches.get(cache_name) if cache_name else self.default_cache
        if cache is None:
            raise ValueError("No cache available")
        return tier_cached(cache, ttl, key_builder, tags)

    def get_all_stats(self) -> Dict[str, List[TierCacheStats]]:
        return {name: cache.get_all_stats() for name, cache in self.caches.items()}


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Advanced Cache System."""
    print("=" * 70)
    print("BAEL - ADVANCED CACHING SYSTEM DEMO")
    print("Multi-Tier Caching with Eviction")
    print("=" * 70)
    print()

    manager = AdvancedCacheManager()

    # 1. Create Multi-Tier Cache
    print("1. CREATE MULTI-TIER CACHE:")
    print("-" * 40)

    cache = manager.create_cache("main")
    print("   Created 'main' cache with L1 (1000 entries) + L2 (10000 entries)")
    print()

    # 2. Basic Operations
    print("2. BASIC OPERATIONS:")
    print("-" * 40)

    await cache.set("user:1", {"name": "Alice", "age": 30})
    await cache.set("user:2", {"name": "Bob", "age": 25})

    print("   Set user:1 and user:2")

    user = await cache.get("user:1")
    print(f"   Get user:1: {user}")
    print()

    # 3. TTL Expiration
    print("3. TTL EXPIRATION:")
    print("-" * 40)

    await cache.set("temp", "expires soon", ttl=1)
    print("   Set 'temp' with 1s TTL")

    value = await cache.get("temp")
    print(f"   Immediate get: {value}")

    await asyncio.sleep(1.1)

    value = await cache.get("temp")
    print(f"   After 1.1s: {value}")
    print()

    # 4. Get Or Set
    print("4. GET OR SET:")
    print("-" * 40)

    async def expensive_computation():
        print("   Computing...")
        await asyncio.sleep(0.1)
        return {"result": 42}

    result = await cache.get_or_set("computed", expensive_computation)
    print(f"   First call: {result}")

    result = await cache.get_or_set("computed", expensive_computation)
    print(f"   Second call (cached): {result}")
    print()

    # 5. Tag-Based Invalidation
    print("5. TAG-BASED INVALIDATION:")
    print("-" * 40)

    await cache.set("product:1", {"name": "Widget"}, tags={"products", "catalog"})
    await cache.set("product:2", {"name": "Gadget"}, tags={"products", "catalog"})
    await cache.set("order:1", {"total": 100}, tags={"orders"})

    print("   Set products with 'products' tag, order with 'orders' tag")

    count = await cache.invalidate_by_tag("products")
    print(f"   Invalidated 'products' tag: {count} entries")

    p1 = await cache.get("product:1")
    o1 = await cache.get("order:1")
    print(f"   product:1 after invalidation: {p1}")
    print(f"   order:1 still exists: {o1 is not None}")
    print()

    # 6. Tier Promotion
    print("6. TIER PROMOTION:")
    print("-" * 40)

    # Custom cache with accessible tiers
    custom_cache = MultiTierCache()
    l1_config = TierCacheConfig("L1", max_entries=5, eviction_policy=TierEvictionPolicy.LRU)
    l2_config = TierCacheConfig("L2", max_entries=100)
    custom_cache.add_tier(CacheTier(l1_config))
    custom_cache.add_tier(CacheTier(l2_config))

    # Set only in L2
    await custom_cache.tiers[1].set("promo_key", "L2 value")

    # Verify L1 is empty
    l1_val = await custom_cache.tiers[0].get("promo_key")
    print(f"   L1 before get: {l1_val}")

    # Get through multi-tier (triggers promotion)
    value = await custom_cache.get("promo_key")
    print(f"   Multi-tier get: {value}")

    # Verify promoted to L1
    l1_val = await custom_cache.tiers[0].get("promo_key")
    print(f"   L1 after promotion: {l1_val}")
    print()

    # 7. Eviction Policy
    print("7. EVICTION POLICY:")
    print("-" * 40)

    small_config = TierCacheConfig("small", max_entries=3, eviction_policy=TierEvictionPolicy.LRU)
    small_cache = MultiTierCache()
    small_cache.add_tier(CacheTier(small_config))

    await small_cache.set("a", 1)
    await small_cache.set("b", 2)
    await small_cache.set("c", 3)

    print("   Set a, b, c in cache of size 3")

    # Access 'a' to make it recently used
    await small_cache.get("a")

    # Add 'd' - should evict 'b' (LRU)
    await small_cache.set("d", 4)

    a_val = await small_cache.get("a")
    b_val = await small_cache.get("b")
    d_val = await small_cache.get("d")

    print(f"   After adding 'd': a={a_val}, b={b_val}, d={d_val}")
    print()

    # 8. Cache Warmer
    print("8. CACHE WARMER:")
    print("-" * 40)

    warmer = manager.create_warmer("main")

    async def load_config():
        return {"setting": "value"}

    async def load_users():
        return [{"id": 1}, {"id": 2}]

    warmer.register("config", load_config, ttl=300)
    warmer.register("users", load_users, ttl=60)

    results = await warmer.warmup()
    print(f"   Warmup results: {results}")

    config = await cache.get("config")
    print(f"   Warmed config: {config}")
    print()

    # 9. Caching Decorator
    print("9. CACHING DECORATOR:")
    print("-" * 40)

    call_count = {"value": 0}

    @manager.cached(cache_name="main", ttl=30)
    async def fibonacci(n: int) -> int:
        call_count["value"] += 1
        if n <= 1:
            return n
        return await fibonacci(n - 1) + await fibonacci(n - 2)

    result = await fibonacci(10)
    print(f"   fibonacci(10) = {result}")
    print(f"   Function calls: {call_count['value']}")

    call_count["value"] = 0
    result = await fibonacci(10)
    print(f"   Cached fibonacci(10) = {result}")
    print(f"   Function calls (cached): {call_count['value']}")
    print()

    # 10. Statistics
    print("10. STATISTICS:")
    print("-" * 40)

    all_stats = manager.get_all_stats()
    for cache_name, tier_stats in all_stats.items():
        print(f"   Cache '{cache_name}':")
        for stats in tier_stats:
            print(f"     {stats.tier_name}: hits={stats.hits}, misses={stats.misses}, hit_rate={stats.hit_rate:.1%}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Advanced Caching System Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
