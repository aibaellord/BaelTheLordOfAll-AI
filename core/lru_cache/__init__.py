"""
BAEL LRU Cache Engine Implementation
=====================================

Least Recently Used cache implementation.

"Ba'el remembers what matters most." — Ba'el
"""

import asyncio
import hashlib
import logging
import threading
import time
from collections import OrderedDict
from typing import Any, Callable, Dict, Generic, Optional, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("BAEL.LRUCache")

K = TypeVar('K')
V = TypeVar('V')


# ============================================================================
# ENUMS
# ============================================================================

class EvictionPolicy(Enum):
    """Cache eviction policies."""
    LRU = "lru"      # Least Recently Used
    LFU = "lfu"      # Least Frequently Used
    FIFO = "fifo"    # First In First Out
    TTL = "ttl"      # Time To Live based


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class CacheEntry(Generic[V]):
    """A cache entry with metadata."""
    value: V
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    ttl: Optional[float] = None
    size: int = 0

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.ttl is None:
            return False
        return (time.time() - self.created_at) > self.ttl

    def touch(self) -> None:
        """Update access time and count."""
        self.last_accessed = time.time()
        self.access_count += 1


@dataclass
class LRUCacheConfig:
    """LRU cache configuration."""
    max_size: int = 1000
    max_memory_bytes: Optional[int] = None
    default_ttl: Optional[float] = None
    eviction_policy: EvictionPolicy = EvictionPolicy.LRU


@dataclass
class CacheStats:
    """Cache statistics."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expirations: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'hits': self.hits,
            'misses': self.misses,
            'evictions': self.evictions,
            'expirations': self.expirations,
            'hit_rate': self.hit_rate
        }


# ============================================================================
# LRU CACHE
# ============================================================================

class LRUCache(Generic[K, V]):
    """
    LRU (Least Recently Used) Cache.

    Features:
    - O(1) get/put operations
    - Automatic eviction
    - Optional TTL
    - Memory size limits

    "Ba'el optimizes access with divine efficiency." — Ba'el
    """

    def __init__(self, config: Optional[LRUCacheConfig] = None):
        """Initialize LRU cache."""
        self.config = config or LRUCacheConfig()

        # Use OrderedDict for O(1) operations
        self._cache: OrderedDict[K, CacheEntry[V]] = OrderedDict()

        # For LFU tracking
        self._freq_map: Dict[K, int] = {}

        # Memory tracking
        self._current_memory = 0

        # Statistics
        self._stats = CacheStats()

        # Thread safety
        self._lock = threading.RLock()

        logger.info(f"LRU cache initialized (max_size={self.config.max_size})")

    # ========================================================================
    # CORE OPERATIONS
    # ========================================================================

    def get(
        self,
        key: K,
        default: Optional[V] = None
    ) -> Optional[V]:
        """
        Get value from cache.

        Args:
            key: Cache key
            default: Default value if not found

        Returns:
            Cached value or default
        """
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._stats.misses += 1
                return default

            # Check expiration
            if entry.is_expired():
                self._remove(key)
                self._stats.expirations += 1
                self._stats.misses += 1
                return default

            # Update access
            entry.touch()
            self._freq_map[key] = self._freq_map.get(key, 0) + 1

            # Move to end (most recently used)
            self._cache.move_to_end(key)

            self._stats.hits += 1
            return entry.value

    def put(
        self,
        key: K,
        value: V,
        ttl: Optional[float] = None,
        size: Optional[int] = None
    ) -> None:
        """
        Put value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            size: Optional size in bytes
        """
        with self._lock:
            # Remove existing if present
            if key in self._cache:
                self._remove(key)

            # Calculate size
            entry_size = size or self._estimate_size(value)

            # Evict if needed
            self._evict_if_needed(entry_size)

            # Create entry
            entry = CacheEntry(
                value=value,
                ttl=ttl or self.config.default_ttl,
                size=entry_size
            )

            self._cache[key] = entry
            self._freq_map[key] = 1
            self._current_memory += entry_size

    def delete(self, key: K) -> bool:
        """
        Delete key from cache.

        Args:
            key: Key to delete

        Returns:
            True if key was deleted
        """
        with self._lock:
            if key in self._cache:
                self._remove(key)
                return True
            return False

    def _remove(self, key: K) -> None:
        """Remove key from cache."""
        entry = self._cache.get(key)
        if entry:
            self._current_memory -= entry.size
            del self._cache[key]
            self._freq_map.pop(key, None)

    def _evict_if_needed(self, new_entry_size: int = 0) -> None:
        """Evict entries if over limits."""
        # Check count limit
        while len(self._cache) >= self.config.max_size:
            self._evict_one()

        # Check memory limit
        if self.config.max_memory_bytes:
            while (self._current_memory + new_entry_size >
                   self.config.max_memory_bytes and self._cache):
                self._evict_one()

    def _evict_one(self) -> None:
        """Evict one entry based on policy."""
        if not self._cache:
            return

        if self.config.eviction_policy == EvictionPolicy.LRU:
            # Remove first (least recently used)
            key = next(iter(self._cache))

        elif self.config.eviction_policy == EvictionPolicy.LFU:
            # Remove least frequently used
            key = min(self._cache.keys(),
                     key=lambda k: self._freq_map.get(k, 0))

        elif self.config.eviction_policy == EvictionPolicy.FIFO:
            # Remove first inserted
            key = next(iter(self._cache))

        elif self.config.eviction_policy == EvictionPolicy.TTL:
            # Remove oldest by creation time
            key = min(self._cache.keys(),
                     key=lambda k: self._cache[k].created_at)
        else:
            key = next(iter(self._cache))

        self._remove(key)
        self._stats.evictions += 1

    def _estimate_size(self, value: Any) -> int:
        """Estimate size of value in bytes."""
        try:
            import sys
            return sys.getsizeof(value)
        except Exception:
            return 1  # Fallback

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def contains(self, key: K) -> bool:
        """Check if key exists (without updating access)."""
        with self._lock:
            if key not in self._cache:
                return False

            entry = self._cache[key]
            if entry.is_expired():
                self._remove(key)
                self._stats.expirations += 1
                return False

            return True

    def __contains__(self, key: K) -> bool:
        return self.contains(key)

    def __getitem__(self, key: K) -> V:
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value

    def __setitem__(self, key: K, value: V) -> None:
        self.put(key, value)

    def __delitem__(self, key: K) -> None:
        if not self.delete(key):
            raise KeyError(key)

    def __len__(self) -> int:
        return len(self._cache)

    def clear(self) -> None:
        """Clear all entries."""
        with self._lock:
            self._cache.clear()
            self._freq_map.clear()
            self._current_memory = 0

    def keys(self) -> list:
        """Get all keys."""
        with self._lock:
            return list(self._cache.keys())

    def expire_old(self) -> int:
        """Remove expired entries."""
        expired = 0
        with self._lock:
            for key in list(self._cache.keys()):
                if self._cache[key].is_expired():
                    self._remove(key)
                    self._stats.expirations += 1
                    expired += 1
        return expired

    # ========================================================================
    # STATS
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'size': len(self._cache),
            'max_size': self.config.max_size,
            'memory_used': self._current_memory,
            **self._stats.to_dict()
        }


# ============================================================================
# MEMOIZATION DECORATOR
# ============================================================================

def memoize(
    max_size: int = 1000,
    ttl: Optional[float] = None
) -> Callable:
    """
    Memoization decorator using LRU cache.

    Args:
        max_size: Maximum cache size
        ttl: Time to live for entries

    Returns:
        Decorator function
    """
    cache = LRUCache(LRUCacheConfig(
        max_size=max_size,
        default_ttl=ttl
    ))

    def decorator(func: Callable) -> Callable:
        def make_key(*args, **kwargs) -> str:
            key_parts = [str(args)]
            key_parts.append(str(sorted(kwargs.items())))
            key_str = "|".join(key_parts)
            return hashlib.md5(key_str.encode()).hexdigest()

        def wrapper(*args, **kwargs):
            key = make_key(*args, **kwargs)

            result = cache.get(key)
            if result is not None:
                return result

            result = func(*args, **kwargs)
            cache.put(key, result)

            return result

        async def async_wrapper(*args, **kwargs):
            key = make_key(*args, **kwargs)

            result = cache.get(key)
            if result is not None:
                return result

            result = await func(*args, **kwargs)
            cache.put(key, result)

            return result

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper

    return decorator


# ============================================================================
# TWO-TIER CACHE
# ============================================================================

class TwoTierCache(Generic[K, V]):
    """
    Two-tier cache with L1 (fast/small) and L2 (slow/large).
    """

    def __init__(
        self,
        l1_size: int = 100,
        l2_size: int = 1000,
        l1_ttl: Optional[float] = 60.0,
        l2_ttl: Optional[float] = 300.0
    ):
        self._l1 = LRUCache(LRUCacheConfig(
            max_size=l1_size,
            default_ttl=l1_ttl
        ))
        self._l2 = LRUCache(LRUCacheConfig(
            max_size=l2_size,
            default_ttl=l2_ttl
        ))

    def get(self, key: K, default: Optional[V] = None) -> Optional[V]:
        """Get from L1, then L2."""
        # Try L1
        value = self._l1.get(key)
        if value is not None:
            return value

        # Try L2
        value = self._l2.get(key)
        if value is not None:
            # Promote to L1
            self._l1.put(key, value)
            return value

        return default

    def put(self, key: K, value: V) -> None:
        """Put in both L1 and L2."""
        self._l1.put(key, value)
        self._l2.put(key, value)

    def delete(self, key: K) -> bool:
        """Delete from both tiers."""
        l1_deleted = self._l1.delete(key)
        l2_deleted = self._l2.delete(key)
        return l1_deleted or l2_deleted


# ============================================================================
# CONVENIENCE
# ============================================================================

_global_cache: Optional[LRUCache] = None


def get_cache(config: Optional[LRUCacheConfig] = None) -> LRUCache:
    """Get or create global cache."""
    global _global_cache
    if _global_cache is None:
        _global_cache = LRUCache(config)
    return _global_cache


def cache_get(key: Any, default: Any = None) -> Any:
    """Get from global cache."""
    return get_cache().get(key, default)


def cache_put(key: Any, value: Any, ttl: Optional[float] = None) -> None:
    """Put in global cache."""
    get_cache().put(key, value, ttl)


def cache_delete(key: Any) -> bool:
    """Delete from global cache."""
    return get_cache().delete(key)
