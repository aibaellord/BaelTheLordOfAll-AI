#!/usr/bin/env python3
"""
BAEL - Cache Manager
Multi-tier caching system for AI agent operations.

This module implements intelligent caching with multiple
storage tiers, eviction policies, and cache optimization.

Features:
- Multi-tier caching (L1/L2/L3)
- Multiple eviction policies (LRU, LFU, FIFO, TTL)
- Cache warming and prefetching
- Cache statistics and analytics
- Distributed cache coordination
- Cache invalidation strategies
- Write-through and write-back modes
- Cache compression
- Cache partitioning
"""

import asyncio
import hashlib
import json
import logging
import pickle
import time
import zlib
from abc import ABC, abstractmethod
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from functools import wraps
from heapq import heappop, heappush
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    TypeVar, Union)
from uuid import uuid4

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class CacheLevel(Enum):
    """Cache tier levels."""
    L1_MEMORY = "l1_memory"       # Fastest, smallest
    L2_LOCAL = "l2_local"         # Medium speed, medium size
    L3_DISTRIBUTED = "l3_distributed"  # Slowest, largest


class EvictionPolicy(Enum):
    """Cache eviction policies."""
    LRU = "lru"                   # Least Recently Used
    LFU = "lfu"                   # Least Frequently Used
    FIFO = "fifo"                 # First In First Out
    TTL = "ttl"                   # Time To Live
    RANDOM = "random"             # Random eviction
    ARC = "arc"                   # Adaptive Replacement Cache


class WritePolicy(Enum):
    """Cache write policies."""
    WRITE_THROUGH = "write_through"  # Write to cache and storage
    WRITE_BACK = "write_back"        # Write to cache, async to storage
    WRITE_AROUND = "write_around"    # Write to storage, skip cache


class CacheState(Enum):
    """Cache entry state."""
    VALID = "valid"
    STALE = "stale"
    EXPIRED = "expired"
    INVALIDATED = "invalidated"


class InvalidationStrategy(Enum):
    """Cache invalidation strategies."""
    IMMEDIATE = "immediate"       # Invalidate immediately
    LAZY = "lazy"                 # Invalidate on next access
    PROPAGATE = "propagate"       # Propagate to all tiers
    PATTERN = "pattern"           # Invalidate by pattern


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class CacheEntry:
    """A cache entry with metadata."""
    key: str
    value: Any
    size_bytes: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    access_count: int = 0
    state: CacheState = CacheState.VALID
    tags: Set[str] = field(default_factory=set)
    compressed: bool = False

    def update_access(self) -> None:
        """Update access metadata."""
        self.accessed_at = datetime.now()
        self.access_count += 1

    @property
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if entry is valid."""
        return self.state == CacheState.VALID and not self.is_expired

    @property
    def age_seconds(self) -> float:
        """Get entry age in seconds."""
        return (datetime.now() - self.created_at).total_seconds()


@dataclass
class CacheStats:
    """Cache statistics."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    insertions: int = 0
    updates: int = 0
    invalidations: int = 0
    total_size_bytes: int = 0
    entry_count: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def miss_rate(self) -> float:
        """Calculate miss rate."""
        return 1.0 - self.hit_rate

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate": f"{self.hit_rate:.2%}",
            "total_size": self.total_size_bytes,
            "entry_count": self.entry_count
        }


@dataclass
class CacheConfig:
    """Cache configuration."""
    max_size_bytes: int = 100 * 1024 * 1024  # 100MB
    max_entries: int = 10000
    default_ttl_seconds: int = 3600
    eviction_policy: EvictionPolicy = EvictionPolicy.LRU
    write_policy: WritePolicy = WritePolicy.WRITE_THROUGH
    compression_enabled: bool = False
    compression_threshold: int = 1024  # Compress if larger than 1KB


# =============================================================================
# CACHE IMPLEMENTATIONS
# =============================================================================

class CacheBackend(ABC):
    """Abstract cache backend."""

    @abstractmethod
    async def get(self, key: str) -> Optional[CacheEntry]:
        """Get entry from cache."""
        pass

    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = None
    ) -> bool:
        """Set entry in cache."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        pass

    @abstractmethod
    async def clear(self) -> int:
        """Clear all entries."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        pass


class LRUCache(CacheBackend):
    """LRU (Least Recently Used) cache implementation."""

    def __init__(self, config: CacheConfig):
        self.config = config
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.stats = CacheStats()

    async def get(self, key: str) -> Optional[CacheEntry]:
        """Get entry, moving to end (most recent)."""
        if key in self.cache:
            entry = self.cache[key]

            if entry.is_expired:
                await self.delete(key)
                self.stats.misses += 1
                return None

            # Move to end (most recently used)
            self.cache.move_to_end(key)
            entry.update_access()
            self.stats.hits += 1
            return entry

        self.stats.misses += 1
        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = None
    ) -> bool:
        """Set entry with LRU ordering."""
        ttl = ttl_seconds or self.config.default_ttl_seconds
        expires_at = datetime.now() + timedelta(seconds=ttl)

        # Serialize to get size
        try:
            serialized = pickle.dumps(value)
            size = len(serialized)
        except Exception:
            size = 0

        # Compress if enabled and large enough
        compressed = False
        if (self.config.compression_enabled and
            size >= self.config.compression_threshold):
            serialized = zlib.compress(serialized)
            compressed = True
            size = len(serialized)

        # Check if update or new entry
        is_update = key in self.cache

        if is_update:
            old_entry = self.cache[key]
            self.stats.total_size_bytes -= old_entry.size_bytes
            self.stats.updates += 1
        else:
            self.stats.insertions += 1

        # Evict if necessary
        while (len(self.cache) >= self.config.max_entries or
               self.stats.total_size_bytes + size > self.config.max_size_bytes):
            if not self.cache:
                break
            await self._evict_one()

        # Create entry
        entry = CacheEntry(
            key=key,
            value=value,
            size_bytes=size,
            expires_at=expires_at,
            compressed=compressed
        )

        self.cache[key] = entry
        self.cache.move_to_end(key)
        self.stats.total_size_bytes += size
        self.stats.entry_count = len(self.cache)

        return True

    async def _evict_one(self) -> Optional[str]:
        """Evict the least recently used entry."""
        if not self.cache:
            return None

        # Pop from front (least recently used)
        key, entry = self.cache.popitem(last=False)
        self.stats.total_size_bytes -= entry.size_bytes
        self.stats.evictions += 1
        self.stats.entry_count = len(self.cache)

        return key

    async def delete(self, key: str) -> bool:
        """Delete entry."""
        if key in self.cache:
            entry = self.cache.pop(key)
            self.stats.total_size_bytes -= entry.size_bytes
            self.stats.entry_count = len(self.cache)
            self.stats.invalidations += 1
            return True
        return False

    async def clear(self) -> int:
        """Clear all entries."""
        count = len(self.cache)
        self.cache.clear()
        self.stats.total_size_bytes = 0
        self.stats.entry_count = 0
        return count

    async def exists(self, key: str) -> bool:
        """Check if key exists and is valid."""
        if key in self.cache:
            entry = self.cache[key]
            if entry.is_expired:
                await self.delete(key)
                return False
            return True
        return False


class LFUCache(CacheBackend):
    """LFU (Least Frequently Used) cache implementation."""

    def __init__(self, config: CacheConfig):
        self.config = config
        self.cache: Dict[str, CacheEntry] = {}
        self.freq_map: Dict[int, OrderedDict] = defaultdict(OrderedDict)
        self.min_freq = 0
        self.stats = CacheStats()

    async def get(self, key: str) -> Optional[CacheEntry]:
        """Get entry, updating frequency."""
        if key not in self.cache:
            self.stats.misses += 1
            return None

        entry = self.cache[key]

        if entry.is_expired:
            await self.delete(key)
            self.stats.misses += 1
            return None

        # Update frequency
        old_freq = entry.access_count
        del self.freq_map[old_freq][key]

        if not self.freq_map[old_freq] and old_freq == self.min_freq:
            self.min_freq += 1

        entry.update_access()
        new_freq = entry.access_count
        self.freq_map[new_freq][key] = entry

        self.stats.hits += 1
        return entry

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = None
    ) -> bool:
        """Set entry with frequency tracking."""
        if self.config.max_entries <= 0:
            return False

        ttl = ttl_seconds or self.config.default_ttl_seconds
        expires_at = datetime.now() + timedelta(seconds=ttl)

        try:
            serialized = pickle.dumps(value)
            size = len(serialized)
        except Exception:
            size = 0

        if key in self.cache:
            # Update existing
            entry = self.cache[key]
            old_freq = entry.access_count
            del self.freq_map[old_freq][key]

            self.stats.total_size_bytes -= entry.size_bytes
            entry.value = value
            entry.size_bytes = size
            entry.expires_at = expires_at
            entry.update_access()

            self.freq_map[entry.access_count][key] = entry
            self.stats.total_size_bytes += size
            self.stats.updates += 1
            return True

        # Evict if necessary
        while len(self.cache) >= self.config.max_entries:
            await self._evict_one()

        # New entry
        entry = CacheEntry(
            key=key,
            value=value,
            size_bytes=size,
            expires_at=expires_at,
            access_count=1
        )

        self.cache[key] = entry
        self.freq_map[1][key] = entry
        self.min_freq = 1

        self.stats.total_size_bytes += size
        self.stats.insertions += 1
        self.stats.entry_count = len(self.cache)

        return True

    async def _evict_one(self) -> Optional[str]:
        """Evict least frequently used entry."""
        if not self.cache:
            return None

        # Get from minimum frequency bucket
        min_freq_bucket = self.freq_map[self.min_freq]
        if not min_freq_bucket:
            return None

        key, entry = min_freq_bucket.popitem(last=False)
        del self.cache[key]

        self.stats.total_size_bytes -= entry.size_bytes
        self.stats.evictions += 1
        self.stats.entry_count = len(self.cache)

        return key

    async def delete(self, key: str) -> bool:
        """Delete entry."""
        if key not in self.cache:
            return False

        entry = self.cache[key]
        del self.freq_map[entry.access_count][key]
        del self.cache[key]

        self.stats.total_size_bytes -= entry.size_bytes
        self.stats.invalidations += 1
        self.stats.entry_count = len(self.cache)

        return True

    async def clear(self) -> int:
        """Clear all entries."""
        count = len(self.cache)
        self.cache.clear()
        self.freq_map.clear()
        self.min_freq = 0
        self.stats.total_size_bytes = 0
        self.stats.entry_count = 0
        return count

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        if key in self.cache:
            if self.cache[key].is_expired:
                await self.delete(key)
                return False
            return True
        return False


class TTLCache(CacheBackend):
    """TTL-based cache with automatic expiration."""

    def __init__(self, config: CacheConfig):
        self.config = config
        self.cache: Dict[str, CacheEntry] = {}
        self.expiry_heap: List[Tuple[float, str]] = []
        self.stats = CacheStats()

    async def get(self, key: str) -> Optional[CacheEntry]:
        """Get entry if not expired."""
        await self._cleanup_expired()

        if key not in self.cache:
            self.stats.misses += 1
            return None

        entry = self.cache[key]
        if entry.is_expired:
            await self.delete(key)
            self.stats.misses += 1
            return None

        entry.update_access()
        self.stats.hits += 1
        return entry

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = None
    ) -> bool:
        """Set entry with TTL."""
        await self._cleanup_expired()

        ttl = ttl_seconds or self.config.default_ttl_seconds
        expires_at = datetime.now() + timedelta(seconds=ttl)

        try:
            serialized = pickle.dumps(value)
            size = len(serialized)
        except Exception:
            size = 0

        is_update = key in self.cache

        if is_update:
            self.stats.total_size_bytes -= self.cache[key].size_bytes
            self.stats.updates += 1
        else:
            self.stats.insertions += 1

        entry = CacheEntry(
            key=key,
            value=value,
            size_bytes=size,
            expires_at=expires_at
        )

        self.cache[key] = entry
        heappush(self.expiry_heap, (expires_at.timestamp(), key))

        self.stats.total_size_bytes += size
        self.stats.entry_count = len(self.cache)

        return True

    async def _cleanup_expired(self) -> int:
        """Remove expired entries."""
        now = time.time()
        removed = 0

        while self.expiry_heap:
            expires_ts, key = self.expiry_heap[0]

            if expires_ts > now:
                break

            heappop(self.expiry_heap)

            if key in self.cache and self.cache[key].is_expired:
                await self.delete(key)
                removed += 1

        return removed

    async def delete(self, key: str) -> bool:
        """Delete entry."""
        if key in self.cache:
            entry = self.cache.pop(key)
            self.stats.total_size_bytes -= entry.size_bytes
            self.stats.invalidations += 1
            self.stats.entry_count = len(self.cache)
            return True
        return False

    async def clear(self) -> int:
        """Clear all entries."""
        count = len(self.cache)
        self.cache.clear()
        self.expiry_heap.clear()
        self.stats.total_size_bytes = 0
        self.stats.entry_count = 0
        return count

    async def exists(self, key: str) -> bool:
        """Check if key exists and is valid."""
        if key in self.cache:
            if self.cache[key].is_expired:
                await self.delete(key)
                return False
            return True
        return False


# =============================================================================
# MULTI-TIER CACHE
# =============================================================================

class CacheTier:
    """A single cache tier."""

    def __init__(
        self,
        level: CacheLevel,
        backend: CacheBackend,
        priority: int = 0
    ):
        self.level = level
        self.backend = backend
        self.priority = priority
        self.enabled = True


class MultiTierCache:
    """Multi-tier cache with automatic promotion/demotion."""

    def __init__(self):
        self.tiers: Dict[CacheLevel, CacheTier] = {}
        self.promotion_threshold = 3  # Promote after N accesses

    def add_tier(
        self,
        level: CacheLevel,
        config: CacheConfig,
        policy: EvictionPolicy = EvictionPolicy.LRU
    ) -> None:
        """Add a cache tier."""
        # Select backend based on policy
        if policy == EvictionPolicy.LRU:
            backend = LRUCache(config)
        elif policy == EvictionPolicy.LFU:
            backend = LFUCache(config)
        elif policy == EvictionPolicy.TTL:
            backend = TTLCache(config)
        else:
            backend = LRUCache(config)

        priority = {
            CacheLevel.L1_MEMORY: 0,
            CacheLevel.L2_LOCAL: 1,
            CacheLevel.L3_DISTRIBUTED: 2
        }.get(level, 99)

        self.tiers[level] = CacheTier(level, backend, priority)

    async def get(self, key: str) -> Optional[Any]:
        """Get from cache, checking all tiers."""
        sorted_tiers = sorted(
            self.tiers.values(),
            key=lambda t: t.priority
        )

        for tier in sorted_tiers:
            if not tier.enabled:
                continue

            entry = await tier.backend.get(key)
            if entry:
                # Promote to higher tier if accessed frequently
                if entry.access_count >= self.promotion_threshold:
                    await self._promote(key, entry, tier.level)

                return entry.value

        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = None,
        target_tier: CacheLevel = None
    ) -> bool:
        """Set in cache."""
        # Default to L1
        target = target_tier or CacheLevel.L1_MEMORY

        tier = self.tiers.get(target)
        if tier and tier.enabled:
            return await tier.backend.set(key, value, ttl_seconds)

        # Fall back to any available tier
        for tier in self.tiers.values():
            if tier.enabled:
                return await tier.backend.set(key, value, ttl_seconds)

        return False

    async def _promote(
        self,
        key: str,
        entry: CacheEntry,
        current_level: CacheLevel
    ) -> None:
        """Promote entry to higher tier."""
        higher_tiers = [
            t for t in self.tiers.values()
            if t.priority < self.tiers[current_level].priority
        ]

        if higher_tiers:
            target = min(higher_tiers, key=lambda t: t.priority)
            await target.backend.set(
                key,
                entry.value,
                int((entry.expires_at - datetime.now()).total_seconds())
                if entry.expires_at else None
            )

    async def invalidate(
        self,
        key: str,
        strategy: InvalidationStrategy = InvalidationStrategy.PROPAGATE
    ) -> int:
        """Invalidate cache entry."""
        deleted = 0

        if strategy == InvalidationStrategy.PROPAGATE:
            # Delete from all tiers
            for tier in self.tiers.values():
                if await tier.backend.delete(key):
                    deleted += 1
        else:
            # Delete from first tier only
            for tier in sorted(self.tiers.values(), key=lambda t: t.priority):
                if await tier.backend.delete(key):
                    deleted += 1
                    break

        return deleted

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate entries matching pattern."""
        deleted = 0
        import fnmatch

        for tier in self.tiers.values():
            if isinstance(tier.backend, (LRUCache, LFUCache, TTLCache)):
                keys_to_delete = [
                    k for k in tier.backend.cache.keys()
                    if fnmatch.fnmatch(k, pattern)
                ]
                for key in keys_to_delete:
                    if await tier.backend.delete(key):
                        deleted += 1

        return deleted

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for all tiers."""
        stats = {}

        for level, tier in self.tiers.items():
            if hasattr(tier.backend, 'stats'):
                stats[level.value] = tier.backend.stats.to_dict()

        return stats


# =============================================================================
# CACHE WARMING
# =============================================================================

class CacheWarmer:
    """Pre-populates cache with frequently accessed data."""

    def __init__(self, cache: MultiTierCache):
        self.cache = cache
        self.warm_up_keys: Set[str] = set()
        self.data_loaders: Dict[str, Callable] = {}

    def register_loader(
        self,
        key_pattern: str,
        loader: Callable[[str], Any]
    ) -> None:
        """Register a data loader for a key pattern."""
        self.data_loaders[key_pattern] = loader

    def add_warm_up_key(self, key: str) -> None:
        """Add key to warm-up list."""
        self.warm_up_keys.add(key)

    async def warm_up(self) -> int:
        """Warm up the cache."""
        warmed = 0

        for key in self.warm_up_keys:
            # Find matching loader
            for pattern, loader in self.data_loaders.items():
                import fnmatch
                if fnmatch.fnmatch(key, pattern):
                    try:
                        if asyncio.iscoroutinefunction(loader):
                            value = await loader(key)
                        else:
                            value = loader(key)

                        await self.cache.set(key, value)
                        warmed += 1
                    except Exception as e:
                        logger.error(f"Failed to warm key {key}: {e}")
                    break

        return warmed

    async def prefetch(
        self,
        keys: List[str],
        loader: Callable[[str], Any]
    ) -> int:
        """Prefetch multiple keys."""
        prefetched = 0

        for key in keys:
            try:
                if asyncio.iscoroutinefunction(loader):
                    value = await loader(key)
                else:
                    value = loader(key)

                await self.cache.set(key, value)
                prefetched += 1
            except Exception as e:
                logger.error(f"Failed to prefetch {key}: {e}")

        return prefetched


# =============================================================================
# CACHE DECORATOR
# =============================================================================

def cached(
    ttl_seconds: int = 3600,
    key_prefix: str = "",
    cache_instance: MultiTierCache = None
):
    """Decorator for caching function results."""

    def decorator(func: Callable) -> Callable:
        # Create default cache if not provided
        nonlocal cache_instance
        if cache_instance is None:
            cache_instance = MultiTierCache()
            config = CacheConfig(max_entries=1000)
            cache_instance.add_tier(CacheLevel.L1_MEMORY, config)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            key_parts = [key_prefix, func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = hashlib.md5(
                ":".join(key_parts).encode()
            ).hexdigest()

            # Check cache
            cached_value = await cache_instance.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Execute function
            result = await func(*args, **kwargs)

            # Cache result
            await cache_instance.set(cache_key, result, ttl_seconds)

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return asyncio.get_event_loop().run_until_complete(
                async_wrapper(*args, **kwargs)
            )

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# =============================================================================
# CACHE MANAGER
# =============================================================================

class CacheManager:
    """
    The master cache manager for BAEL.

    Provides comprehensive multi-tier caching with
    automatic optimization and management.
    """

    def __init__(self):
        self.multi_tier = MultiTierCache()
        self.warmer: Optional[CacheWarmer] = None
        self.namespaces: Dict[str, MultiTierCache] = {}

        # Initialize default tiers
        self._setup_default_tiers()

    def _setup_default_tiers(self) -> None:
        """Set up default cache tiers."""
        # L1: Fast in-memory cache
        l1_config = CacheConfig(
            max_size_bytes=50 * 1024 * 1024,  # 50MB
            max_entries=5000,
            default_ttl_seconds=300,  # 5 minutes
            eviction_policy=EvictionPolicy.LRU
        )
        self.multi_tier.add_tier(CacheLevel.L1_MEMORY, l1_config)

        # L2: Larger local cache
        l2_config = CacheConfig(
            max_size_bytes=200 * 1024 * 1024,  # 200MB
            max_entries=20000,
            default_ttl_seconds=1800,  # 30 minutes
            eviction_policy=EvictionPolicy.LFU
        )
        self.multi_tier.add_tier(CacheLevel.L2_LOCAL, l2_config)

        # L3: Long-term cache
        l3_config = CacheConfig(
            max_size_bytes=1024 * 1024 * 1024,  # 1GB
            max_entries=100000,
            default_ttl_seconds=3600,  # 1 hour
            eviction_policy=EvictionPolicy.TTL,
            compression_enabled=True
        )
        self.multi_tier.add_tier(CacheLevel.L3_DISTRIBUTED, l3_config)

        # Initialize warmer
        self.warmer = CacheWarmer(self.multi_tier)

    def create_namespace(self, name: str) -> MultiTierCache:
        """Create an isolated cache namespace."""
        if name not in self.namespaces:
            namespace_cache = MultiTierCache()
            config = CacheConfig(max_entries=1000)
            namespace_cache.add_tier(CacheLevel.L1_MEMORY, config)
            self.namespaces[name] = namespace_cache
        return self.namespaces[name]

    async def get(
        self,
        key: str,
        namespace: str = None
    ) -> Optional[Any]:
        """Get value from cache."""
        cache = self.namespaces.get(namespace) if namespace else self.multi_tier
        return await cache.get(key)

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = None,
        namespace: str = None,
        tier: CacheLevel = None
    ) -> bool:
        """Set value in cache."""
        cache = self.namespaces.get(namespace) if namespace else self.multi_tier
        return await cache.set(key, value, ttl_seconds, tier)

    async def delete(
        self,
        key: str,
        namespace: str = None
    ) -> int:
        """Delete value from cache."""
        cache = self.namespaces.get(namespace) if namespace else self.multi_tier
        return await cache.invalidate(key)

    async def invalidate_pattern(
        self,
        pattern: str,
        namespace: str = None
    ) -> int:
        """Invalidate entries matching pattern."""
        cache = self.namespaces.get(namespace) if namespace else self.multi_tier
        return await cache.invalidate_pattern(pattern)

    async def get_or_set(
        self,
        key: str,
        loader: Callable[[], Any],
        ttl_seconds: int = None,
        namespace: str = None
    ) -> Any:
        """Get from cache or load and cache."""
        value = await self.get(key, namespace)

        if value is not None:
            return value

        # Load value
        if asyncio.iscoroutinefunction(loader):
            value = await loader()
        else:
            value = loader()

        # Cache it
        await self.set(key, value, ttl_seconds, namespace)

        return value

    async def warm_up(self) -> int:
        """Warm up the cache."""
        if self.warmer:
            return await self.warmer.warm_up()
        return 0

    def register_warm_up(
        self,
        pattern: str,
        loader: Callable[[str], Any],
        keys: List[str] = None
    ) -> None:
        """Register data for cache warming."""
        if self.warmer:
            self.warmer.register_loader(pattern, loader)
            if keys:
                for key in keys:
                    self.warmer.add_warm_up_key(key)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = {
            "main_cache": self.multi_tier.get_stats(),
            "namespaces": {}
        }

        for name, cache in self.namespaces.items():
            stats["namespaces"][name] = cache.get_stats()

        return stats

    async def clear(self, namespace: str = None) -> int:
        """Clear cache."""
        total = 0

        if namespace:
            if namespace in self.namespaces:
                cache = self.namespaces[namespace]
                for tier in cache.tiers.values():
                    total += await tier.backend.clear()
        else:
            for tier in self.multi_tier.tiers.values():
                total += await tier.backend.clear()

        return total

    async def optimize(self) -> Dict[str, Any]:
        """Optimize cache based on usage patterns."""
        results = {
            "expired_removed": 0,
            "rebalanced_entries": 0
        }

        # Clean expired entries in TTL caches
        for tier in self.multi_tier.tiers.values():
            if isinstance(tier.backend, TTLCache):
                removed = await tier.backend._cleanup_expired()
                results["expired_removed"] += removed

        return results


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Cache Manager."""
    print("=" * 70)
    print("BAEL - CACHE MANAGER DEMO")
    print("Multi-Tier Caching System")
    print("=" * 70)
    print()

    # Create cache manager
    cache = CacheManager()

    # 1. Basic Operations
    print("1. BASIC CACHE OPERATIONS:")
    print("-" * 40)

    # Set values
    await cache.set("user:123", {"name": "Alice", "role": "admin"})
    await cache.set("config:app", {"debug": True, "version": "1.0"}, ttl_seconds=60)
    print("   Set user:123 and config:app")

    # Get values
    user = await cache.get("user:123")
    print(f"   Get user:123: {user}")

    config = await cache.get("config:app")
    print(f"   Get config:app: {config}")

    # Miss
    missing = await cache.get("nonexistent")
    print(f"   Get nonexistent: {missing}")
    print()

    # 2. Multi-Tier Behavior
    print("2. MULTI-TIER CACHING:")
    print("-" * 40)

    # Add to specific tier
    await cache.set(
        "large:data",
        "x" * 10000,  # Large value
        tier=CacheLevel.L3_DISTRIBUTED
    )
    print("   Stored large data in L3 tier")

    # Check tier stats
    stats = cache.get_stats()
    for tier_name, tier_stats in stats["main_cache"].items():
        print(f"   {tier_name}: {tier_stats['entry_count']} entries, {tier_stats['hit_rate']} hit rate")
    print()

    # 3. Namespaces
    print("3. CACHE NAMESPACES:")
    print("-" * 40)

    # Create namespaces
    cache.create_namespace("api_responses")
    cache.create_namespace("computations")

    await cache.set("result:1", {"data": "api response"}, namespace="api_responses")
    await cache.set("result:1", 42, namespace="computations")

    api_result = await cache.get("result:1", namespace="api_responses")
    comp_result = await cache.get("result:1", namespace="computations")

    print(f"   api_responses/result:1: {api_result}")
    print(f"   computations/result:1: {comp_result}")
    print()

    # 4. Get or Set Pattern
    print("4. GET OR SET PATTERN:")
    print("-" * 40)

    load_count = 0

    async def expensive_loader():
        nonlocal load_count
        load_count += 1
        await asyncio.sleep(0.1)  # Simulate slow operation
        return {"computed": True, "value": 42}

    # First call - loads from source
    result1 = await cache.get_or_set("expensive:key", expensive_loader, ttl_seconds=60)
    print(f"   First call: {result1} (load count: {load_count})")

    # Second call - from cache
    result2 = await cache.get_or_set("expensive:key", expensive_loader, ttl_seconds=60)
    print(f"   Second call: {result2} (load count: {load_count})")
    print()

    # 5. Pattern Invalidation
    print("5. PATTERN INVALIDATION:")
    print("-" * 40)

    await cache.set("session:user1", "data1")
    await cache.set("session:user2", "data2")
    await cache.set("session:user3", "data3")
    await cache.set("other:key", "other_data")

    print("   Added session:user1, session:user2, session:user3, other:key")

    deleted = await cache.invalidate_pattern("session:*")
    print(f"   Invalidated pattern 'session:*': {deleted} entries removed")

    remaining = await cache.get("other:key")
    print(f"   other:key still exists: {remaining is not None}")
    print()

    # 6. Cache Warming
    print("6. CACHE WARMING:")
    print("-" * 40)

    # Register data loader
    def config_loader(key: str):
        return {"loaded_from": key, "timestamp": datetime.now().isoformat()}

    cache.register_warm_up(
        "config:*",
        config_loader,
        keys=["config:db", "config:api", "config:cache"]
    )

    warmed = await cache.warm_up()
    print(f"   Warmed {warmed} cache entries")

    db_config = await cache.get("config:db")
    print(f"   config:db: {db_config}")
    print()

    # 7. LRU Eviction Demo
    print("7. LRU EVICTION:")
    print("-" * 40)

    # Create small LRU cache
    small_lru = LRUCache(CacheConfig(max_entries=3))

    await small_lru.set("a", "value_a")
    await small_lru.set("b", "value_b")
    await small_lru.set("c", "value_c")
    print(f"   Added a, b, c (cache size: {len(small_lru.cache)})")

    # Access 'a' to make it recently used
    await small_lru.get("a")

    # Add 'd' - should evict 'b' (least recently used)
    await small_lru.set("d", "value_d")

    print(f"   Added d after accessing a")
    print(f"   'b' still exists: {await small_lru.exists('b')}")
    print(f"   'a' still exists: {await small_lru.exists('a')}")
    print(f"   Evictions: {small_lru.stats.evictions}")
    print()

    # 8. LFU Eviction Demo
    print("8. LFU EVICTION:")
    print("-" * 40)

    small_lfu = LFUCache(CacheConfig(max_entries=3))

    await small_lfu.set("x", "value_x")
    await small_lfu.set("y", "value_y")
    await small_lfu.set("z", "value_z")

    # Access 'x' multiple times
    for _ in range(5):
        await small_lfu.get("x")

    print(f"   'x' access count: {small_lfu.cache['x'].access_count}")
    print(f"   'y' access count: {small_lfu.cache['y'].access_count}")

    # Add new entry - should evict least frequently used
    await small_lfu.set("w", "value_w")

    print(f"   Added 'w' - 'y' or 'z' evicted")
    print(f"   'x' still exists: {await small_lfu.exists('x')}")
    print()

    # 9. Cache Statistics
    print("9. CACHE STATISTICS:")
    print("-" * 40)

    full_stats = cache.get_stats()

    print("   Main Cache Tiers:")
    for tier_name, tier_stats in full_stats["main_cache"].items():
        print(f"     {tier_name}:")
        print(f"       Entries: {tier_stats['entry_count']}")
        print(f"       Hits: {tier_stats['hits']}, Misses: {tier_stats['misses']}")
        print(f"       Hit Rate: {tier_stats['hit_rate']}")
    print()

    # 10. Cache Optimization
    print("10. CACHE OPTIMIZATION:")
    print("-" * 40)

    results = await cache.optimize()
    print(f"   Expired entries removed: {results['expired_removed']}")

    # Clear demo data
    cleared = await cache.clear()
    print(f"   Cleared {cleared} entries")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Cache Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
