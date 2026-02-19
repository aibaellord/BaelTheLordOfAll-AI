"""
BAEL Cache Manager
==================

Comprehensive caching system with:
- Multiple eviction policies (LRU, LFU, TTL, FIFO)
- Multi-level caching (L1, L2, distributed)
- Cache warming and prefetching
- Statistics and monitoring
- Serialization support

"Cache everything, forget nothing of value." — Ba'el
"""

import asyncio
import logging
import json
import pickle
import hashlib
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Set, Tuple, Union, Generic, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import OrderedDict, defaultdict
import threading
import uuid
from functools import wraps

logger = logging.getLogger("BAEL.CacheEngine")

T = TypeVar('T')


# ============================================================================
# ENUMS
# ============================================================================

class EvictionPolicy(Enum):
    """Cache eviction policies."""
    LRU = "lru"         # Least Recently Used
    LFU = "lfu"         # Least Frequently Used
    FIFO = "fifo"       # First In First Out
    TTL = "ttl"         # Time To Live
    RANDOM = "random"   # Random eviction
    SIZE = "size"       # Largest items first
    NONE = "none"       # No eviction (unbounded)


class CacheType(Enum):
    """Types of caches."""
    MEMORY = "memory"       # In-memory
    DISK = "disk"           # Disk-based
    REDIS = "redis"         # Redis backend
    MEMCACHED = "memcached" # Memcached backend
    HYBRID = "hybrid"       # Multi-level


class CacheStatus(Enum):
    """Status of cache operations."""
    HIT = "hit"
    MISS = "miss"
    EXPIRED = "expired"
    EVICTED = "evicted"
    ERROR = "error"


class SerializationFormat(Enum):
    """Serialization formats for cache values."""
    PICKLE = "pickle"
    JSON = "json"
    MSGPACK = "msgpack"
    NONE = "none"       # No serialization


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class CacheEntry:
    """A cache entry with metadata."""
    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None

    # Access tracking
    access_count: int = 0

    # Size tracking
    size_bytes: int = 0

    # Tags for grouping
    tags: Set[str] = field(default_factory=set)

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    def touch(self) -> None:
        """Update access time and count."""
        self.accessed_at = datetime.now()
        self.access_count += 1


@dataclass
class CacheConfig:
    """Configuration for the cache."""
    max_size: int = 10000           # Max number of entries
    max_memory_mb: int = 256        # Max memory in MB
    default_ttl_seconds: int = 3600 # Default TTL
    eviction_policy: EvictionPolicy = EvictionPolicy.LRU
    serialization: SerializationFormat = SerializationFormat.PICKLE
    enable_stats: bool = True
    enable_compression: bool = False
    namespace: str = "default"


@dataclass
class CacheStats:
    """Statistics for cache operations."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expirations: int = 0

    sets: int = 0
    deletes: int = 0

    total_size_bytes: int = 0
    entry_count: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def miss_rate(self) -> float:
        return 1.0 - self.hit_rate

    def to_dict(self) -> Dict[str, Any]:
        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': round(self.hit_rate * 100, 2),
            'evictions': self.evictions,
            'expirations': self.expirations,
            'sets': self.sets,
            'deletes': self.deletes,
            'total_size_bytes': self.total_size_bytes,
            'entry_count': self.entry_count
        }


# ============================================================================
# BASE CACHE
# ============================================================================

class BaseCache:
    """Base cache implementation."""

    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        self._stats = CacheStats()
        self._lock = threading.RLock()

    def get(self, key: str) -> Tuple[Optional[Any], CacheStatus]:
        """Get a value from cache."""
        raise NotImplementedError

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[Set[str]] = None
    ) -> bool:
        """Set a value in cache."""
        raise NotImplementedError

    def delete(self, key: str) -> bool:
        """Delete a value from cache."""
        raise NotImplementedError

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        raise NotImplementedError

    def clear(self) -> int:
        """Clear all entries."""
        raise NotImplementedError

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        return self._stats

    def _serialize(self, value: Any) -> bytes:
        """Serialize a value."""
        if self.config.serialization == SerializationFormat.PICKLE:
            return pickle.dumps(value)
        elif self.config.serialization == SerializationFormat.JSON:
            return json.dumps(value).encode()
        return value

    def _deserialize(self, data: bytes) -> Any:
        """Deserialize a value."""
        if self.config.serialization == SerializationFormat.PICKLE:
            return pickle.loads(data)
        elif self.config.serialization == SerializationFormat.JSON:
            return json.loads(data.decode())
        return data


# ============================================================================
# LRU CACHE
# ============================================================================

class LRUCache(BaseCache):
    """
    Least Recently Used cache.

    Evicts least recently accessed items first.
    """

    def __init__(self, config: Optional[CacheConfig] = None):
        super().__init__(config)
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()

    def get(self, key: str) -> Tuple[Optional[Any], CacheStatus]:
        """Get a value from cache."""
        with self._lock:
            full_key = f"{self.config.namespace}:{key}"

            if full_key not in self._cache:
                self._stats.misses += 1
                return None, CacheStatus.MISS

            entry = self._cache[full_key]

            # Check expiration
            if entry.is_expired:
                del self._cache[full_key]
                self._stats.expirations += 1
                self._stats.entry_count -= 1
                return None, CacheStatus.EXPIRED

            # Move to end (most recently used)
            self._cache.move_to_end(full_key)
            entry.touch()

            self._stats.hits += 1
            return entry.value, CacheStatus.HIT

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[Set[str]] = None
    ) -> bool:
        """Set a value in cache."""
        with self._lock:
            full_key = f"{self.config.namespace}:{key}"
            ttl = ttl if ttl is not None else self.config.default_ttl_seconds

            # Evict if necessary
            while len(self._cache) >= self.config.max_size:
                evicted_key = next(iter(self._cache))
                del self._cache[evicted_key]
                self._stats.evictions += 1
                self._stats.entry_count -= 1

            # Calculate size
            try:
                size = len(self._serialize(value))
            except:
                size = 0

            expires_at = None
            if ttl > 0:
                expires_at = datetime.now() + timedelta(seconds=ttl)

            entry = CacheEntry(
                key=full_key,
                value=value,
                expires_at=expires_at,
                size_bytes=size,
                tags=tags or set()
            )

            # Update or insert
            if full_key in self._cache:
                old_entry = self._cache[full_key]
                self._stats.total_size_bytes -= old_entry.size_bytes
            else:
                self._stats.entry_count += 1

            self._cache[full_key] = entry
            self._cache.move_to_end(full_key)

            self._stats.sets += 1
            self._stats.total_size_bytes += size

            return True

    def delete(self, key: str) -> bool:
        """Delete a value from cache."""
        with self._lock:
            full_key = f"{self.config.namespace}:{key}"

            if full_key in self._cache:
                entry = self._cache.pop(full_key)
                self._stats.deletes += 1
                self._stats.entry_count -= 1
                self._stats.total_size_bytes -= entry.size_bytes
                return True

            return False

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        with self._lock:
            full_key = f"{self.config.namespace}:{key}"

            if full_key not in self._cache:
                return False

            entry = self._cache[full_key]
            if entry.is_expired:
                del self._cache[full_key]
                self._stats.expirations += 1
                self._stats.entry_count -= 1
                return False

            return True

    def clear(self) -> int:
        """Clear all entries."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._stats.entry_count = 0
            self._stats.total_size_bytes = 0
            return count

    def keys(self) -> List[str]:
        """Get all keys."""
        with self._lock:
            prefix = f"{self.config.namespace}:"
            return [k[len(prefix):] for k in self._cache.keys()]


# ============================================================================
# LFU CACHE
# ============================================================================

class LFUCache(BaseCache):
    """
    Least Frequently Used cache.

    Evicts least accessed items first.
    """

    def __init__(self, config: Optional[CacheConfig] = None):
        super().__init__(config)
        self._cache: Dict[str, CacheEntry] = {}
        self._freq_to_keys: Dict[int, OrderedDict] = defaultdict(OrderedDict)
        self._min_freq: int = 0

    def get(self, key: str) -> Tuple[Optional[Any], CacheStatus]:
        """Get a value from cache."""
        with self._lock:
            full_key = f"{self.config.namespace}:{key}"

            if full_key not in self._cache:
                self._stats.misses += 1
                return None, CacheStatus.MISS

            entry = self._cache[full_key]

            if entry.is_expired:
                self._remove_entry(full_key, entry)
                self._stats.expirations += 1
                return None, CacheStatus.EXPIRED

            # Update frequency
            old_freq = entry.access_count
            entry.touch()
            new_freq = entry.access_count

            # Move to new frequency bucket
            del self._freq_to_keys[old_freq][full_key]
            if not self._freq_to_keys[old_freq]:
                del self._freq_to_keys[old_freq]
                if self._min_freq == old_freq:
                    self._min_freq = new_freq

            self._freq_to_keys[new_freq][full_key] = True

            self._stats.hits += 1
            return entry.value, CacheStatus.HIT

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[Set[str]] = None
    ) -> bool:
        """Set a value in cache."""
        with self._lock:
            full_key = f"{self.config.namespace}:{key}"
            ttl = ttl if ttl is not None else self.config.default_ttl_seconds

            # If updating existing entry
            if full_key in self._cache:
                entry = self._cache[full_key]
                old_size = entry.size_bytes

                entry.value = value
                entry.accessed_at = datetime.now()

                if ttl > 0:
                    entry.expires_at = datetime.now() + timedelta(seconds=ttl)

                try:
                    entry.size_bytes = len(self._serialize(value))
                except:
                    entry.size_bytes = 0

                self._stats.total_size_bytes += entry.size_bytes - old_size
                self._stats.sets += 1
                return True

            # Evict if necessary
            while len(self._cache) >= self.config.max_size:
                # Evict from minimum frequency bucket
                if self._min_freq in self._freq_to_keys:
                    evict_key = next(iter(self._freq_to_keys[self._min_freq]))
                    self._remove_entry(evict_key, self._cache[evict_key])
                    self._stats.evictions += 1
                else:
                    break

            # Create new entry
            expires_at = None
            if ttl > 0:
                expires_at = datetime.now() + timedelta(seconds=ttl)

            try:
                size = len(self._serialize(value))
            except:
                size = 0

            entry = CacheEntry(
                key=full_key,
                value=value,
                expires_at=expires_at,
                size_bytes=size,
                tags=tags or set()
            )

            self._cache[full_key] = entry
            self._freq_to_keys[0][full_key] = True
            self._min_freq = 0

            self._stats.sets += 1
            self._stats.entry_count += 1
            self._stats.total_size_bytes += size

            return True

    def _remove_entry(self, key: str, entry: CacheEntry) -> None:
        """Remove an entry from cache."""
        freq = entry.access_count

        if key in self._freq_to_keys[freq]:
            del self._freq_to_keys[freq][key]
            if not self._freq_to_keys[freq]:
                del self._freq_to_keys[freq]

        if key in self._cache:
            del self._cache[key]
            self._stats.entry_count -= 1
            self._stats.total_size_bytes -= entry.size_bytes

    def delete(self, key: str) -> bool:
        """Delete a value from cache."""
        with self._lock:
            full_key = f"{self.config.namespace}:{key}"

            if full_key in self._cache:
                entry = self._cache[full_key]
                self._remove_entry(full_key, entry)
                self._stats.deletes += 1
                return True

            return False

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        with self._lock:
            full_key = f"{self.config.namespace}:{key}"

            if full_key not in self._cache:
                return False

            entry = self._cache[full_key]
            if entry.is_expired:
                self._remove_entry(full_key, entry)
                self._stats.expirations += 1
                return False

            return True

    def clear(self) -> int:
        """Clear all entries."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._freq_to_keys.clear()
            self._min_freq = 0
            self._stats.entry_count = 0
            self._stats.total_size_bytes = 0
            return count


# ============================================================================
# TTL CACHE
# ============================================================================

class TTLCache(BaseCache):
    """
    Time To Live cache.

    Entries are evicted after their TTL expires.
    """

    def __init__(self, config: Optional[CacheConfig] = None):
        super().__init__(config)
        self._cache: Dict[str, CacheEntry] = {}
        self._expiration_index: Dict[float, Set[str]] = defaultdict(set)
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start_cleanup(self, interval: int = 60) -> None:
        """Start background cleanup task."""
        async def cleanup_loop():
            while True:
                await asyncio.sleep(interval)
                self._cleanup_expired()

        self._cleanup_task = asyncio.create_task(cleanup_loop())

    async def stop_cleanup(self) -> None:
        """Stop background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None

    def _cleanup_expired(self) -> int:
        """Clean up expired entries."""
        with self._lock:
            now = datetime.now().timestamp()
            expired_count = 0

            expired_times = [t for t in self._expiration_index.keys() if t <= now]

            for exp_time in expired_times:
                for key in self._expiration_index[exp_time]:
                    if key in self._cache:
                        entry = self._cache[key]
                        del self._cache[key]
                        self._stats.expirations += 1
                        self._stats.entry_count -= 1
                        self._stats.total_size_bytes -= entry.size_bytes
                        expired_count += 1

                del self._expiration_index[exp_time]

            return expired_count

    def get(self, key: str) -> Tuple[Optional[Any], CacheStatus]:
        """Get a value from cache."""
        with self._lock:
            full_key = f"{self.config.namespace}:{key}"

            if full_key not in self._cache:
                self._stats.misses += 1
                return None, CacheStatus.MISS

            entry = self._cache[full_key]

            if entry.is_expired:
                del self._cache[full_key]
                self._stats.expirations += 1
                self._stats.entry_count -= 1
                self._stats.total_size_bytes -= entry.size_bytes
                return None, CacheStatus.EXPIRED

            entry.touch()
            self._stats.hits += 1
            return entry.value, CacheStatus.HIT

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[Set[str]] = None
    ) -> bool:
        """Set a value in cache."""
        with self._lock:
            full_key = f"{self.config.namespace}:{key}"
            ttl = ttl if ttl is not None else self.config.default_ttl_seconds

            # Calculate expiration
            expires_at = None
            if ttl > 0:
                expires_at = datetime.now() + timedelta(seconds=ttl)

            # Calculate size
            try:
                size = len(self._serialize(value))
            except:
                size = 0

            # Remove old entry if exists
            if full_key in self._cache:
                old_entry = self._cache[full_key]
                self._stats.total_size_bytes -= old_entry.size_bytes

                if old_entry.expires_at:
                    exp_time = old_entry.expires_at.timestamp()
                    if exp_time in self._expiration_index:
                        self._expiration_index[exp_time].discard(full_key)
            else:
                self._stats.entry_count += 1

            # Evict if necessary
            while len(self._cache) >= self.config.max_size:
                self._cleanup_expired()
                if len(self._cache) >= self.config.max_size:
                    # Evict oldest
                    oldest_key = min(
                        self._cache.keys(),
                        key=lambda k: self._cache[k].created_at
                    )
                    entry = self._cache.pop(oldest_key)
                    self._stats.evictions += 1
                    self._stats.entry_count -= 1
                    self._stats.total_size_bytes -= entry.size_bytes

            entry = CacheEntry(
                key=full_key,
                value=value,
                expires_at=expires_at,
                size_bytes=size,
                tags=tags or set()
            )

            self._cache[full_key] = entry

            if expires_at:
                self._expiration_index[expires_at.timestamp()].add(full_key)

            self._stats.sets += 1
            self._stats.total_size_bytes += size

            return True

    def delete(self, key: str) -> bool:
        """Delete a value from cache."""
        with self._lock:
            full_key = f"{self.config.namespace}:{key}"

            if full_key in self._cache:
                entry = self._cache.pop(full_key)

                if entry.expires_at:
                    exp_time = entry.expires_at.timestamp()
                    if exp_time in self._expiration_index:
                        self._expiration_index[exp_time].discard(full_key)

                self._stats.deletes += 1
                self._stats.entry_count -= 1
                self._stats.total_size_bytes -= entry.size_bytes
                return True

            return False

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        value, status = self.get(key)
        return status == CacheStatus.HIT

    def clear(self) -> int:
        """Clear all entries."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._expiration_index.clear()
            self._stats.entry_count = 0
            self._stats.total_size_bytes = 0
            return count


# ============================================================================
# DISTRIBUTED CACHE
# ============================================================================

class DistributedCache(BaseCache):
    """
    Distributed cache with sharding support.

    Distributes entries across multiple cache nodes.
    """

    def __init__(
        self,
        config: Optional[CacheConfig] = None,
        num_shards: int = 4
    ):
        super().__init__(config)
        self._shards: List[LRUCache] = [
            LRUCache(CacheConfig(
                max_size=config.max_size // num_shards if config else 2500,
                namespace=f"{config.namespace if config else 'default'}_shard{i}"
            ))
            for i in range(num_shards)
        ]
        self._num_shards = num_shards

    def _get_shard(self, key: str) -> LRUCache:
        """Get the shard for a key."""
        hash_val = int(hashlib.md5(key.encode()).hexdigest(), 16)
        return self._shards[hash_val % self._num_shards]

    def get(self, key: str) -> Tuple[Optional[Any], CacheStatus]:
        """Get a value from cache."""
        shard = self._get_shard(key)
        result = shard.get(key)

        # Aggregate stats
        if result[1] == CacheStatus.HIT:
            self._stats.hits += 1
        else:
            self._stats.misses += 1

        return result

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[Set[str]] = None
    ) -> bool:
        """Set a value in cache."""
        shard = self._get_shard(key)
        result = shard.set(key, value, ttl, tags)
        self._stats.sets += 1
        return result

    def delete(self, key: str) -> bool:
        """Delete a value from cache."""
        shard = self._get_shard(key)
        result = shard.delete(key)
        if result:
            self._stats.deletes += 1
        return result

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        shard = self._get_shard(key)
        return shard.exists(key)

    def clear(self) -> int:
        """Clear all entries."""
        total = 0
        for shard in self._shards:
            total += shard.clear()
        self._stats.entry_count = 0
        self._stats.total_size_bytes = 0
        return total

    def get_stats(self) -> CacheStats:
        """Get aggregated cache statistics."""
        stats = CacheStats()

        for shard in self._shards:
            shard_stats = shard.get_stats()
            stats.hits += shard_stats.hits
            stats.misses += shard_stats.misses
            stats.evictions += shard_stats.evictions
            stats.expirations += shard_stats.expirations
            stats.sets += shard_stats.sets
            stats.deletes += shard_stats.deletes
            stats.total_size_bytes += shard_stats.total_size_bytes
            stats.entry_count += shard_stats.entry_count

        return stats


# ============================================================================
# MULTI-LEVEL CACHE
# ============================================================================

class MultiLevelCache(BaseCache):
    """
    Multi-level cache (L1 + L2).

    L1: Fast in-memory cache (small)
    L2: Larger cache (may be disk or distributed)
    """

    def __init__(
        self,
        l1_config: Optional[CacheConfig] = None,
        l2_config: Optional[CacheConfig] = None
    ):
        super().__init__(l1_config)

        # L1: Small, fast LRU cache
        l1_cfg = l1_config or CacheConfig(max_size=1000, namespace="l1")
        self._l1 = LRUCache(l1_cfg)

        # L2: Larger LFU cache
        l2_cfg = l2_config or CacheConfig(max_size=10000, namespace="l2")
        self._l2 = LFUCache(l2_cfg)

    def get(self, key: str) -> Tuple[Optional[Any], CacheStatus]:
        """Get a value from cache."""
        # Try L1 first
        value, status = self._l1.get(key)
        if status == CacheStatus.HIT:
            self._stats.hits += 1
            return value, status

        # Try L2
        value, status = self._l2.get(key)
        if status == CacheStatus.HIT:
            # Promote to L1
            self._l1.set(key, value)
            self._stats.hits += 1
            return value, status

        self._stats.misses += 1
        return None, CacheStatus.MISS

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[Set[str]] = None
    ) -> bool:
        """Set a value in cache."""
        # Set in both levels
        self._l1.set(key, value, ttl, tags)
        self._l2.set(key, value, ttl, tags)
        self._stats.sets += 1
        return True

    def delete(self, key: str) -> bool:
        """Delete a value from cache."""
        r1 = self._l1.delete(key)
        r2 = self._l2.delete(key)
        if r1 or r2:
            self._stats.deletes += 1
        return r1 or r2

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        return self._l1.exists(key) or self._l2.exists(key)

    def clear(self) -> int:
        """Clear all entries."""
        total = self._l1.clear() + self._l2.clear()
        self._stats.entry_count = 0
        self._stats.total_size_bytes = 0
        return total

    def get_stats(self) -> CacheStats:
        """Get aggregated cache statistics."""
        l1_stats = self._l1.get_stats()
        l2_stats = self._l2.get_stats()

        stats = CacheStats(
            hits=self._stats.hits,
            misses=self._stats.misses,
            evictions=l1_stats.evictions + l2_stats.evictions,
            expirations=l1_stats.expirations + l2_stats.expirations,
            sets=self._stats.sets,
            deletes=self._stats.deletes,
            total_size_bytes=l1_stats.total_size_bytes + l2_stats.total_size_bytes,
            entry_count=l1_stats.entry_count + l2_stats.entry_count
        )

        return stats


# ============================================================================
# MAIN CACHE ENGINE
# ============================================================================

class CacheEngine:
    """
    Main cache engine with multiple backends.

    Features:
    - Multiple cache types (LRU, LFU, TTL, Distributed, Multi-level)
    - Decorators for function caching
    - Cache warming
    - Statistics and monitoring

    "Ba'el remembers all that is worth remembering." — Ba'el
    """

    def __init__(self, config: Optional[CacheConfig] = None):
        """Initialize cache engine."""
        self.config = config or CacheConfig()

        # Create default cache based on policy
        if self.config.eviction_policy == EvictionPolicy.LRU:
            self._default_cache = LRUCache(self.config)
        elif self.config.eviction_policy == EvictionPolicy.LFU:
            self._default_cache = LFUCache(self.config)
        elif self.config.eviction_policy == EvictionPolicy.TTL:
            self._default_cache = TTLCache(self.config)
        else:
            self._default_cache = LRUCache(self.config)

        # Named caches
        self._caches: Dict[str, BaseCache] = {
            'default': self._default_cache
        }

        logger.info("CacheEngine initialized")

    # ========================================================================
    # CACHE MANAGEMENT
    # ========================================================================

    def create_cache(
        self,
        name: str,
        config: Optional[CacheConfig] = None,
        cache_type: CacheType = CacheType.MEMORY
    ) -> BaseCache:
        """Create a named cache."""
        cfg = config or CacheConfig()

        if cache_type == CacheType.MEMORY:
            if cfg.eviction_policy == EvictionPolicy.LRU:
                cache = LRUCache(cfg)
            elif cfg.eviction_policy == EvictionPolicy.LFU:
                cache = LFUCache(cfg)
            elif cfg.eviction_policy == EvictionPolicy.TTL:
                cache = TTLCache(cfg)
            else:
                cache = LRUCache(cfg)
        elif cache_type == CacheType.HYBRID:
            cache = MultiLevelCache()
        else:
            cache = LRUCache(cfg)

        self._caches[name] = cache
        logger.info(f"Created cache: {name}")
        return cache

    def get_cache(self, name: str = 'default') -> Optional[BaseCache]:
        """Get a named cache."""
        return self._caches.get(name)

    def delete_cache(self, name: str) -> bool:
        """Delete a named cache."""
        if name == 'default':
            return False

        if name in self._caches:
            self._caches[name].clear()
            del self._caches[name]
            return True
        return False

    # ========================================================================
    # BASIC OPERATIONS
    # ========================================================================

    def get(
        self,
        key: str,
        cache_name: str = 'default'
    ) -> Tuple[Optional[Any], CacheStatus]:
        """Get a value from cache."""
        cache = self._caches.get(cache_name, self._default_cache)
        return cache.get(key)

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[Set[str]] = None,
        cache_name: str = 'default'
    ) -> bool:
        """Set a value in cache."""
        cache = self._caches.get(cache_name, self._default_cache)
        return cache.set(key, value, ttl, tags)

    def delete(
        self,
        key: str,
        cache_name: str = 'default'
    ) -> bool:
        """Delete a value from cache."""
        cache = self._caches.get(cache_name, self._default_cache)
        return cache.delete(key)

    def exists(
        self,
        key: str,
        cache_name: str = 'default'
    ) -> bool:
        """Check if key exists."""
        cache = self._caches.get(cache_name, self._default_cache)
        return cache.exists(key)

    def clear(self, cache_name: Optional[str] = None) -> int:
        """Clear cache(s)."""
        if cache_name:
            cache = self._caches.get(cache_name)
            if cache:
                return cache.clear()
            return 0

        total = 0
        for cache in self._caches.values():
            total += cache.clear()
        return total

    # ========================================================================
    # ADVANCED OPERATIONS
    # ========================================================================

    def get_or_set(
        self,
        key: str,
        default_factory: Callable[[], Any],
        ttl: Optional[int] = None,
        cache_name: str = 'default'
    ) -> Any:
        """Get value or set it using a factory function."""
        value, status = self.get(key, cache_name)

        if status == CacheStatus.HIT:
            return value

        value = default_factory()
        self.set(key, value, ttl, cache_name=cache_name)
        return value

    async def get_or_set_async(
        self,
        key: str,
        default_factory: Callable[[], Any],
        ttl: Optional[int] = None,
        cache_name: str = 'default'
    ) -> Any:
        """Async version of get_or_set."""
        value, status = self.get(key, cache_name)

        if status == CacheStatus.HIT:
            return value

        if asyncio.iscoroutinefunction(default_factory):
            value = await default_factory()
        else:
            value = default_factory()

        self.set(key, value, ttl, cache_name=cache_name)
        return value

    def mget(
        self,
        keys: List[str],
        cache_name: str = 'default'
    ) -> Dict[str, Any]:
        """Get multiple values at once."""
        results = {}
        for key in keys:
            value, status = self.get(key, cache_name)
            if status == CacheStatus.HIT:
                results[key] = value
        return results

    def mset(
        self,
        items: Dict[str, Any],
        ttl: Optional[int] = None,
        cache_name: str = 'default'
    ) -> int:
        """Set multiple values at once."""
        count = 0
        for key, value in items.items():
            if self.set(key, value, ttl, cache_name=cache_name):
                count += 1
        return count

    def delete_by_tags(
        self,
        tags: Set[str],
        cache_name: str = 'default'
    ) -> int:
        """Delete entries matching any of the tags."""
        cache = self._caches.get(cache_name)
        if not cache:
            return 0

        # For caches that support tags
        if isinstance(cache, (LRUCache, LFUCache, TTLCache)):
            count = 0
            if hasattr(cache, '_cache'):
                keys_to_delete = []
                for key, entry in cache._cache.items():
                    if entry.tags & tags:
                        keys_to_delete.append(entry.key)

                for key in keys_to_delete:
                    if cache.delete(key.split(':', 1)[-1]):
                        count += 1
            return count

        return 0

    # ========================================================================
    # DECORATORS
    # ========================================================================

    def cached(
        self,
        ttl: Optional[int] = None,
        key_prefix: str = "",
        cache_name: str = 'default'
    ) -> Callable:
        """Decorator to cache function results."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Build cache key
                key_parts = [key_prefix or func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)

                # Try cache
                value, status = self.get(cache_key, cache_name)
                if status == CacheStatus.HIT:
                    return value

                # Call function
                result = func(*args, **kwargs)

                # Cache result
                self.set(cache_key, result, ttl, cache_name=cache_name)
                return result

            return wrapper
        return decorator

    def async_cached(
        self,
        ttl: Optional[int] = None,
        key_prefix: str = "",
        cache_name: str = 'default'
    ) -> Callable:
        """Decorator to cache async function results."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Build cache key
                key_parts = [key_prefix or func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)

                # Try cache
                value, status = self.get(cache_key, cache_name)
                if status == CacheStatus.HIT:
                    return value

                # Call function
                result = await func(*args, **kwargs)

                # Cache result
                self.set(cache_key, result, ttl, cache_name=cache_name)
                return result

            return wrapper
        return decorator

    # ========================================================================
    # WARMING
    # ========================================================================

    async def warm(
        self,
        keys: List[str],
        loader: Callable[[str], Any],
        cache_name: str = 'default',
        ttl: Optional[int] = None
    ) -> int:
        """Warm cache with pre-loaded values."""
        count = 0

        for key in keys:
            try:
                if asyncio.iscoroutinefunction(loader):
                    value = await loader(key)
                else:
                    value = loader(key)

                if self.set(key, value, ttl, cache_name=cache_name):
                    count += 1
            except Exception as e:
                logger.error(f"Failed to warm cache key {key}: {e}")

        logger.info(f"Warmed {count} cache entries")
        return count

    # ========================================================================
    # STATISTICS
    # ========================================================================

    def get_stats(self, cache_name: Optional[str] = None) -> Dict[str, Any]:
        """Get cache statistics."""
        if cache_name:
            cache = self._caches.get(cache_name)
            if cache:
                return cache.get_stats().to_dict()
            return {}

        # Aggregate all stats
        stats = {
            'caches': {},
            'total': CacheStats().to_dict()
        }

        total_stats = CacheStats()

        for name, cache in self._caches.items():
            cache_stats = cache.get_stats()
            stats['caches'][name] = cache_stats.to_dict()

            total_stats.hits += cache_stats.hits
            total_stats.misses += cache_stats.misses
            total_stats.evictions += cache_stats.evictions
            total_stats.expirations += cache_stats.expirations
            total_stats.sets += cache_stats.sets
            total_stats.deletes += cache_stats.deletes
            total_stats.total_size_bytes += cache_stats.total_size_bytes
            total_stats.entry_count += cache_stats.entry_count

        stats['total'] = total_stats.to_dict()
        return stats

    def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        return {
            'caches': list(self._caches.keys()),
            'statistics': self.get_stats()
        }


# ============================================================================
# CONVENIENCE INSTANCE
# ============================================================================

cache_engine = CacheEngine()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def cached(
    ttl: Optional[int] = None,
    key_prefix: str = "",
    cache_name: str = 'default'
) -> Callable:
    """Decorator to cache function results."""
    return cache_engine.cached(ttl, key_prefix, cache_name)


def async_cached(
    ttl: Optional[int] = None,
    key_prefix: str = "",
    cache_name: str = 'default'
) -> Callable:
    """Decorator to cache async function results."""
    return cache_engine.async_cached(ttl, key_prefix, cache_name)
