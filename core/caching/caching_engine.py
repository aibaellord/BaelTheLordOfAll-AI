#!/usr/bin/env python3
"""
BAEL - Caching Engine
High-performance caching for agents.

Features:
- Multi-tier caching
- TTL management
- Eviction policies
- Cache statistics
- Distributed caching support
"""

import asyncio
import hashlib
import json
import math
import pickle
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import OrderedDict, defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')


# =============================================================================
# ENUMS
# =============================================================================

class EvictionPolicy(Enum):
    """Cache eviction policies."""
    LRU = "lru"
    LFU = "lfu"
    FIFO = "fifo"
    TTL = "ttl"
    RANDOM = "random"


class CacheLevel(Enum):
    """Cache levels in hierarchy."""
    L1 = "l1"
    L2 = "l2"
    L3 = "l3"
    REMOTE = "remote"


class CacheState(Enum):
    """Cache entry states."""
    VALID = "valid"
    STALE = "stale"
    EXPIRED = "expired"
    INVALID = "invalid"


class SerializationFormat(Enum):
    """Serialization formats."""
    PICKLE = "pickle"
    JSON = "json"
    RAW = "raw"


class WritePolicy(Enum):
    """Write policies."""
    WRITE_THROUGH = "write_through"
    WRITE_BACK = "write_back"
    WRITE_AROUND = "write_around"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class CacheEntry:
    """A cache entry."""
    key: str = ""
    value: Any = None
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    accessed_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    size: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    def get_state(self) -> CacheState:
        """Get entry state."""
        if self.is_expired():
            return CacheState.EXPIRED
        return CacheState.VALID


@dataclass
class CacheStats:
    """Cache statistics."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expirations: int = 0
    size: int = 0
    max_size: int = 0
    entries: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


@dataclass
class CacheConfig:
    """Cache configuration."""
    max_size: int = 1000
    max_memory: int = 0
    default_ttl: int = 3600
    eviction_policy: EvictionPolicy = EvictionPolicy.LRU
    write_policy: WritePolicy = WritePolicy.WRITE_THROUGH
    serialization: SerializationFormat = SerializationFormat.RAW


# =============================================================================
# CACHE INTERFACE
# =============================================================================

class CacheInterface(ABC, Generic[K, V]):
    """Abstract cache interface."""

    @abstractmethod
    def get(self, key: K) -> Optional[V]:
        """Get value from cache."""
        pass

    @abstractmethod
    def set(self, key: K, value: V, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        pass

    @abstractmethod
    def delete(self, key: K) -> bool:
        """Delete from cache."""
        pass

    @abstractmethod
    def exists(self, key: K) -> bool:
        """Check if key exists."""
        pass

    @abstractmethod
    def clear(self) -> int:
        """Clear all entries."""
        pass


# =============================================================================
# LRU CACHE
# =============================================================================

class LRUCache(CacheInterface[str, Any]):
    """Least Recently Used cache."""

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._stats = CacheStats(max_size=max_size)

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key not in self._cache:
            self._stats.misses += 1
            return None

        entry = self._cache[key]

        if entry.is_expired():
            del self._cache[key]
            self._stats.misses += 1
            self._stats.expirations += 1
            self._stats.entries -= 1
            return None

        self._cache.move_to_end(key)

        entry.accessed_at = datetime.now()
        entry.access_count += 1

        self._stats.hits += 1

        return entry.value

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache."""
        if ttl is None:
            ttl = self._default_ttl

        expires_at = datetime.now() + timedelta(seconds=ttl) if ttl > 0 else None

        entry = CacheEntry(
            key=key,
            value=value,
            expires_at=expires_at
        )

        if key in self._cache:
            self._cache.move_to_end(key)
            self._cache[key] = entry
        else:
            if len(self._cache) >= self._max_size:
                self._evict()

            self._cache[key] = entry
            self._stats.entries += 1

        return True

    def delete(self, key: str) -> bool:
        """Delete from cache."""
        if key in self._cache:
            del self._cache[key]
            self._stats.entries -= 1
            return True
        return False

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        if key not in self._cache:
            return False

        entry = self._cache[key]

        if entry.is_expired():
            del self._cache[key]
            self._stats.entries -= 1
            self._stats.expirations += 1
            return False

        return True

    def clear(self) -> int:
        """Clear all entries."""
        count = len(self._cache)
        self._cache.clear()
        self._stats.entries = 0
        return count

    def _evict(self) -> None:
        """Evict oldest entry."""
        if self._cache:
            self._cache.popitem(last=False)
            self._stats.evictions += 1
            self._stats.entries -= 1

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        return self._stats


# =============================================================================
# LFU CACHE
# =============================================================================

class LFUCache(CacheInterface[str, Any]):
    """Least Frequently Used cache."""

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._freq: Dict[str, int] = defaultdict(int)
        self._freq_list: Dict[int, OrderedDict] = defaultdict(OrderedDict)
        self._min_freq = 0
        self._stats = CacheStats(max_size=max_size)

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key not in self._cache:
            self._stats.misses += 1
            return None

        entry = self._cache[key]

        if entry.is_expired():
            self._remove(key)
            self._stats.misses += 1
            self._stats.expirations += 1
            return None

        self._update_freq(key)

        entry.accessed_at = datetime.now()
        entry.access_count += 1

        self._stats.hits += 1

        return entry.value

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache."""
        if ttl is None:
            ttl = self._default_ttl

        expires_at = datetime.now() + timedelta(seconds=ttl) if ttl > 0 else None

        entry = CacheEntry(
            key=key,
            value=value,
            expires_at=expires_at
        )

        if key in self._cache:
            self._cache[key] = entry
            self._update_freq(key)
        else:
            if len(self._cache) >= self._max_size:
                self._evict()

            self._cache[key] = entry
            self._freq[key] = 1
            self._freq_list[1][key] = True
            self._min_freq = 1
            self._stats.entries += 1

        return True

    def delete(self, key: str) -> bool:
        """Delete from cache."""
        if key in self._cache:
            self._remove(key)
            return True
        return False

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        if key not in self._cache:
            return False

        entry = self._cache[key]

        if entry.is_expired():
            self._remove(key)
            self._stats.expirations += 1
            return False

        return True

    def clear(self) -> int:
        """Clear all entries."""
        count = len(self._cache)
        self._cache.clear()
        self._freq.clear()
        self._freq_list.clear()
        self._min_freq = 0
        self._stats.entries = 0
        return count

    def _update_freq(self, key: str) -> None:
        """Update frequency of key."""
        freq = self._freq[key]

        del self._freq_list[freq][key]

        if not self._freq_list[freq]:
            del self._freq_list[freq]
            if self._min_freq == freq:
                self._min_freq += 1

        self._freq[key] = freq + 1
        self._freq_list[freq + 1][key] = True

    def _remove(self, key: str) -> None:
        """Remove key from cache."""
        if key not in self._cache:
            return

        freq = self._freq[key]

        del self._cache[key]
        del self._freq[key]

        if key in self._freq_list[freq]:
            del self._freq_list[freq][key]

            if not self._freq_list[freq]:
                del self._freq_list[freq]

        self._stats.entries -= 1

    def _evict(self) -> None:
        """Evict least frequently used entry."""
        if not self._freq_list[self._min_freq]:
            return

        key, _ = self._freq_list[self._min_freq].popitem(last=False)

        del self._cache[key]
        del self._freq[key]

        if not self._freq_list[self._min_freq]:
            del self._freq_list[self._min_freq]

        self._stats.evictions += 1
        self._stats.entries -= 1

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        return self._stats


# =============================================================================
# TIERED CACHE
# =============================================================================

class TieredCache:
    """Multi-tier cache with L1/L2/L3 levels."""

    def __init__(
        self,
        l1_size: int = 100,
        l2_size: int = 1000,
        l3_size: int = 10000
    ):
        self._l1 = LRUCache(l1_size, default_ttl=300)
        self._l2 = LRUCache(l2_size, default_ttl=1800)
        self._l3 = LRUCache(l3_size, default_ttl=3600)

        self._levels = [
            (CacheLevel.L1, self._l1),
            (CacheLevel.L2, self._l2),
            (CacheLevel.L3, self._l3)
        ]

    def get(self, key: str) -> Tuple[Optional[Any], Optional[CacheLevel]]:
        """Get value from cache, returning level found."""
        for level, cache in self._levels:
            value = cache.get(key)
            if value is not None:
                self._promote(key, value, level)
                return value, level

        return None, None

    def set(
        self,
        key: str,
        value: Any,
        level: CacheLevel = CacheLevel.L1,
        ttl: Optional[int] = None
    ) -> bool:
        """Set value at specified level."""
        if level == CacheLevel.L1:
            return self._l1.set(key, value, ttl)
        elif level == CacheLevel.L2:
            return self._l2.set(key, value, ttl)
        elif level == CacheLevel.L3:
            return self._l3.set(key, value, ttl)

        return False

    def set_all(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value at all levels."""
        for _, cache in self._levels:
            cache.set(key, value, ttl)
        return True

    def delete(self, key: str) -> int:
        """Delete from all levels."""
        count = 0
        for _, cache in self._levels:
            if cache.delete(key):
                count += 1
        return count

    def exists(self, key: str) -> Optional[CacheLevel]:
        """Check which level contains key."""
        for level, cache in self._levels:
            if cache.exists(key):
                return level
        return None

    def clear(self, level: Optional[CacheLevel] = None) -> int:
        """Clear cache at level or all levels."""
        if level == CacheLevel.L1:
            return self._l1.clear()
        elif level == CacheLevel.L2:
            return self._l2.clear()
        elif level == CacheLevel.L3:
            return self._l3.clear()

        total = 0
        for _, cache in self._levels:
            total += cache.clear()
        return total

    def _promote(self, key: str, value: Any, from_level: CacheLevel) -> None:
        """Promote value to L1 if found in lower level."""
        if from_level != CacheLevel.L1:
            self._l1.set(key, value)

    def get_stats(self) -> Dict[CacheLevel, CacheStats]:
        """Get stats for all levels."""
        return {
            CacheLevel.L1: self._l1.get_stats(),
            CacheLevel.L2: self._l2.get_stats(),
            CacheLevel.L3: self._l3.get_stats()
        }


# =============================================================================
# CACHE DECORATOR
# =============================================================================

class CacheDecorator:
    """Decorator for caching function results."""

    def __init__(self, cache: CacheInterface, ttl: Optional[int] = None):
        self._cache = cache
        self._ttl = ttl

    def __call__(self, func: Callable) -> Callable:
        """Decorate function."""
        def wrapper(*args, **kwargs):
            key = self._make_key(func.__name__, args, kwargs)

            cached = self._cache.get(key)
            if cached is not None:
                return cached

            result = func(*args, **kwargs)
            self._cache.set(key, result, self._ttl)

            return result

        return wrapper

    def _make_key(
        self,
        func_name: str,
        args: tuple,
        kwargs: dict
    ) -> str:
        """Generate cache key from function call."""
        key_parts = [func_name]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))

        key_str = ":".join(key_parts)

        return hashlib.md5(key_str.encode()).hexdigest()


# =============================================================================
# CACHE MANAGER
# =============================================================================

class CacheManager:
    """Manage multiple caches."""

    def __init__(self):
        self._caches: Dict[str, CacheInterface] = {}

    def create(
        self,
        name: str,
        policy: EvictionPolicy = EvictionPolicy.LRU,
        max_size: int = 1000,
        default_ttl: int = 3600
    ) -> CacheInterface:
        """Create a named cache."""
        if policy == EvictionPolicy.LRU:
            cache = LRUCache(max_size, default_ttl)
        elif policy == EvictionPolicy.LFU:
            cache = LFUCache(max_size, default_ttl)
        else:
            cache = LRUCache(max_size, default_ttl)

        self._caches[name] = cache

        return cache

    def get(self, name: str) -> Optional[CacheInterface]:
        """Get cache by name."""
        return self._caches.get(name)

    def delete(self, name: str) -> bool:
        """Delete a cache."""
        if name in self._caches:
            del self._caches[name]
            return True
        return False

    def clear_all(self) -> Dict[str, int]:
        """Clear all caches."""
        return {name: cache.clear() for name, cache in self._caches.items()}

    def count(self) -> int:
        """Count caches."""
        return len(self._caches)

    def names(self) -> List[str]:
        """Get cache names."""
        return list(self._caches.keys())


# =============================================================================
# CACHE WARMUP
# =============================================================================

class CacheWarmup:
    """Warm up cache with initial data."""

    def __init__(self, cache: CacheInterface):
        self._cache = cache

    def warmup_dict(
        self,
        data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> int:
        """Warm up from dictionary."""
        count = 0

        for key, value in data.items():
            if self._cache.set(key, value, ttl):
                count += 1

        return count

    async def warmup_async(
        self,
        keys: List[str],
        loader: Callable[[str], Any],
        ttl: Optional[int] = None
    ) -> int:
        """Warm up asynchronously."""
        count = 0

        for key in keys:
            try:
                if asyncio.iscoroutinefunction(loader):
                    value = await loader(key)
                else:
                    value = loader(key)

                if self._cache.set(key, value, ttl):
                    count += 1
            except Exception:
                pass

        return count


# =============================================================================
# CACHING ENGINE
# =============================================================================

class CachingEngine:
    """
    Caching Engine for BAEL.

    High-performance caching for agents.
    """

    def __init__(self, config: Optional[CacheConfig] = None):
        self._config = config or CacheConfig()

        self._manager = CacheManager()

        if self._config.eviction_policy == EvictionPolicy.LRU:
            self._default_cache = LRUCache(
                self._config.max_size,
                self._config.default_ttl
            )
        else:
            self._default_cache = LFUCache(
                self._config.max_size,
                self._config.default_ttl
            )

        self._tiered_cache: Optional[TieredCache] = None

    # ----- Basic Operations -----

    def get(self, key: str) -> Optional[Any]:
        """Get value from default cache."""
        return self._default_cache.get(key)

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in default cache."""
        return self._default_cache.set(key, value, ttl)

    def delete(self, key: str) -> bool:
        """Delete from default cache."""
        return self._default_cache.delete(key)

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        return self._default_cache.exists(key)

    def clear(self) -> int:
        """Clear default cache."""
        return self._default_cache.clear()

    # ----- Named Caches -----

    def create_cache(
        self,
        name: str,
        policy: EvictionPolicy = EvictionPolicy.LRU,
        max_size: int = 1000,
        ttl: int = 3600
    ) -> CacheInterface:
        """Create a named cache."""
        return self._manager.create(name, policy, max_size, ttl)

    def get_cache(self, name: str) -> Optional[CacheInterface]:
        """Get named cache."""
        return self._manager.get(name)

    def delete_cache(self, name: str) -> bool:
        """Delete named cache."""
        return self._manager.delete(name)

    # ----- Tiered Caching -----

    def enable_tiered(
        self,
        l1_size: int = 100,
        l2_size: int = 1000,
        l3_size: int = 10000
    ) -> TieredCache:
        """Enable tiered caching."""
        self._tiered_cache = TieredCache(l1_size, l2_size, l3_size)
        return self._tiered_cache

    def tiered_get(self, key: str) -> Tuple[Optional[Any], Optional[CacheLevel]]:
        """Get from tiered cache."""
        if self._tiered_cache:
            return self._tiered_cache.get(key)
        return None, None

    def tiered_set(
        self,
        key: str,
        value: Any,
        level: CacheLevel = CacheLevel.L1,
        ttl: Optional[int] = None
    ) -> bool:
        """Set in tiered cache."""
        if self._tiered_cache:
            return self._tiered_cache.set(key, value, level, ttl)
        return False

    # ----- Decorator -----

    def cached(
        self,
        cache_name: Optional[str] = None,
        ttl: Optional[int] = None
    ) -> CacheDecorator:
        """Get cache decorator."""
        cache = self._manager.get(cache_name) if cache_name else self._default_cache
        return CacheDecorator(cache or self._default_cache, ttl)

    # ----- Batch Operations -----

    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values."""
        return {key: self._default_cache.get(key)
                for key in keys
                if self._default_cache.exists(key)}

    def set_many(
        self,
        items: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> int:
        """Set multiple values."""
        count = 0
        for key, value in items.items():
            if self._default_cache.set(key, value, ttl):
                count += 1
        return count

    def delete_many(self, keys: List[str]) -> int:
        """Delete multiple keys."""
        return sum(1 for key in keys if self._default_cache.delete(key))

    # ----- Warmup -----

    def warmup(
        self,
        data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> int:
        """Warm up cache."""
        warmup = CacheWarmup(self._default_cache)
        return warmup.warmup_dict(data, ttl)

    # ----- Stats -----

    def get_stats(self) -> CacheStats:
        """Get default cache stats."""
        if hasattr(self._default_cache, 'get_stats'):
            return self._default_cache.get_stats()
        return CacheStats()

    def get_all_stats(self) -> Dict[str, Any]:
        """Get all cache stats."""
        stats = {"default": self.get_stats()}

        for name in self._manager.names():
            cache = self._manager.get(name)
            if cache and hasattr(cache, 'get_stats'):
                stats[name] = cache.get_stats()

        if self._tiered_cache:
            stats["tiered"] = self._tiered_cache.get_stats()

        return stats

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        stats = self.get_stats()

        return {
            "policy": self._config.eviction_policy.value,
            "max_size": self._config.max_size,
            "entries": stats.entries,
            "hit_rate": f"{stats.hit_rate:.2%}",
            "named_caches": self._manager.count(),
            "tiered_enabled": self._tiered_cache is not None
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Caching Engine."""
    print("=" * 70)
    print("BAEL - CACHING ENGINE DEMO")
    print("High-Performance Caching for Agents")
    print("=" * 70)
    print()

    engine = CachingEngine(CacheConfig(max_size=100))

    # 1. Basic Set/Get
    print("1. BASIC SET/GET:")
    print("-" * 40)

    engine.set("user:1", {"name": "Alice", "age": 30})
    engine.set("user:2", {"name": "Bob", "age": 25})

    print(f"   Set user:1 and user:2")
    print(f"   Get user:1: {engine.get('user:1')}")
    print(f"   Exists user:2: {engine.exists('user:2')}")
    print()

    # 2. TTL
    print("2. TTL (Time-To-Live):")
    print("-" * 40)

    engine.set("temp:1", "temporary", ttl=1)
    print(f"   Set temp:1 with 1s TTL")
    print(f"   Get immediately: {engine.get('temp:1')}")

    await asyncio.sleep(1.1)
    print(f"   Get after 1.1s: {engine.get('temp:1')}")
    print()

    # 3. Delete
    print("3. DELETE:")
    print("-" * 40)

    engine.set("delete:1", "to_delete")
    print(f"   Exists before delete: {engine.exists('delete:1')}")

    engine.delete("delete:1")
    print(f"   Exists after delete: {engine.exists('delete:1')}")
    print()

    # 4. Batch Operations
    print("4. BATCH OPERATIONS:")
    print("-" * 40)

    items = {
        "batch:1": "value1",
        "batch:2": "value2",
        "batch:3": "value3"
    }

    count = engine.set_many(items)
    print(f"   Set {count} items")

    results = engine.get_many(["batch:1", "batch:2", "batch:4"])
    print(f"   Get many: {results}")

    deleted = engine.delete_many(["batch:1", "batch:2"])
    print(f"   Deleted {deleted} items")
    print()

    # 5. Named Caches
    print("5. NAMED CACHES:")
    print("-" * 40)

    user_cache = engine.create_cache("users", EvictionPolicy.LRU, 100)
    session_cache = engine.create_cache("sessions", EvictionPolicy.LFU, 50)

    user_cache.set("u:1", {"name": "Carol"})
    session_cache.set("s:1", {"token": "abc123"})

    print(f"   Created 'users' and 'sessions' caches")
    print(f"   Users cache get: {engine.get_cache('users').get('u:1')}")
    print(f"   Sessions cache get: {engine.get_cache('sessions').get('s:1')}")
    print()

    # 6. Tiered Cache
    print("6. TIERED CACHE:")
    print("-" * 40)

    engine.enable_tiered(l1_size=10, l2_size=50, l3_size=100)

    engine.tiered_set("tier:1", "L1 value", CacheLevel.L1)
    engine.tiered_set("tier:2", "L2 value", CacheLevel.L2)
    engine.tiered_set("tier:3", "L3 value", CacheLevel.L3)

    value, level = engine.tiered_get("tier:1")
    print(f"   tier:1 found in {level.value if level else 'none'}: {value}")

    value, level = engine.tiered_get("tier:3")
    print(f"   tier:3 found in {level.value if level else 'none'}: {value}")

    value, level = engine.tiered_get("tier:3")
    print(f"   tier:3 after promotion: {level.value if level else 'none'}")
    print()

    # 7. Cache Warmup
    print("7. CACHE WARMUP:")
    print("-" * 40)

    warmup_data = {
        "warm:1": "preloaded1",
        "warm:2": "preloaded2",
        "warm:3": "preloaded3"
    }

    count = engine.warmup(warmup_data)
    print(f"   Warmed up {count} entries")
    print(f"   Get warm:2: {engine.get('warm:2')}")
    print()

    # 8. Cache Decorator
    print("8. CACHE DECORATOR:")
    print("-" * 40)

    func_cache = engine.create_cache("func_results", EvictionPolicy.LRU, 100)
    decorator = CacheDecorator(func_cache)

    call_count = 0

    @decorator
    def expensive_function(x):
        nonlocal call_count
        call_count += 1
        return x ** 2

    print(f"   First call (5): {expensive_function(5)}, calls: {call_count}")
    print(f"   Second call (5): {expensive_function(5)}, calls: {call_count}")
    print(f"   Third call (10): {expensive_function(10)}, calls: {call_count}")
    print()

    # 9. LRU Eviction
    print("9. LRU EVICTION:")
    print("-" * 40)

    small_cache = LRUCache(max_size=3)

    small_cache.set("a", 1)
    small_cache.set("b", 2)
    small_cache.set("c", 3)

    print(f"   Set a, b, c")

    small_cache.get("a")
    print(f"   Accessed 'a'")

    small_cache.set("d", 4)
    print(f"   Set 'd' (causes eviction)")

    print(f"   'a' exists: {small_cache.exists('a')}")
    print(f"   'b' exists: {small_cache.exists('b')}")
    print()

    # 10. LFU Eviction
    print("10. LFU EVICTION:")
    print("-" * 40)

    lfu_cache = LFUCache(max_size=3)

    lfu_cache.set("x", 1)
    lfu_cache.set("y", 2)
    lfu_cache.set("z", 3)

    lfu_cache.get("x")
    lfu_cache.get("x")
    lfu_cache.get("y")

    print(f"   x accessed 2x, y accessed 1x, z accessed 0x")

    lfu_cache.set("w", 4)
    print(f"   Set 'w' (evicts least frequent)")

    print(f"   'x' exists: {lfu_cache.exists('x')}")
    print(f"   'z' exists: {lfu_cache.exists('z')}")
    print()

    # 11. Cache Stats
    print("11. CACHE STATS:")
    print("-" * 40)

    stats = engine.get_stats()

    print(f"   Hits: {stats.hits}")
    print(f"   Misses: {stats.misses}")
    print(f"   Hit Rate: {stats.hit_rate:.2%}")
    print(f"   Entries: {stats.entries}")
    print(f"   Evictions: {stats.evictions}")
    print()

    # 12. All Stats
    print("12. ALL CACHE STATS:")
    print("-" * 40)

    all_stats = engine.get_all_stats()

    for name, stat in all_stats.items():
        if isinstance(stat, CacheStats):
            print(f"   {name}: entries={stat.entries}, hit_rate={stat.hit_rate:.2%}")
        elif isinstance(stat, dict):
            print(f"   {name}: {len(stat)} levels")
    print()

    # 13. Clear
    print("13. CLEAR CACHE:")
    print("-" * 40)

    engine.set("clear:1", "to_clear")
    engine.set("clear:2", "to_clear")

    print(f"   Entries before clear: {engine.get_stats().entries}")

    cleared = engine.clear()
    print(f"   Cleared: {cleared}")
    print(f"   Entries after clear: {engine.get_stats().entries}")
    print()

    # 14. Summary
    print("14. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Caching Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
