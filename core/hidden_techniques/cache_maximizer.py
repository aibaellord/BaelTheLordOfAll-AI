"""
Ultimate Cache System - Maximum Memory Efficiency
==================================================

Advanced caching system for all BAEL operations.

"Memory is infinite when managed wisely." — Ba'el
"""

import asyncio
import hashlib
import json
import logging
import pickle
import time
from collections import OrderedDict
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar, Generic
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import threading

logger = logging.getLogger("BAEL.HiddenTechniques.Cache")

T = TypeVar('T')


class CacheStrategy(Enum):
    """Caching strategies."""
    LRU = "lru"                    # Least Recently Used
    LFU = "lfu"                    # Least Frequently Used
    TTL = "ttl"                    # Time To Live
    ADAPTIVE = "adaptive"          # Adapts to usage patterns
    TIERED = "tiered"             # Multi-level cache
    SEMANTIC = "semantic"          # Semantic similarity cache
    PREDICTIVE = "predictive"      # Pre-caches likely requests


class CacheLevel(Enum):
    """Cache tier levels."""
    L1_MEMORY = "l1_memory"        # In-memory, fastest
    L2_LOCAL = "l2_local"          # Local disk
    L3_DISTRIBUTED = "l3_distributed"  # Distributed cache
    L4_PERSISTENT = "l4_persistent"    # Persistent storage


@dataclass
class CacheEntry:
    """A single cache entry."""
    key: str
    value: Any
    created_at: float = field(default_factory=time.time)
    accessed_at: float = field(default_factory=time.time)
    access_count: int = 0
    ttl_seconds: Optional[float] = None
    size_bytes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        if self.ttl_seconds is None:
            return False
        return time.time() > self.created_at + self.ttl_seconds

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at

    def touch(self) -> None:
        """Update access time and count."""
        self.accessed_at = time.time()
        self.access_count += 1


@dataclass
class CacheStats:
    """Cache statistics."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size_bytes: int = 0
    entry_count: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class BaseCache(Generic[T]):
    """Base cache implementation."""

    def __init__(
        self,
        max_size: int = 1000,
        ttl_seconds: float = None,
        max_memory_mb: int = 100,
    ):
        self.max_size = max_size
        self.default_ttl = ttl_seconds
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._stats = CacheStats()
        self._lock = threading.RLock()

    def _make_key(self, key: Any) -> str:
        """Create a cache key from any hashable input."""
        if isinstance(key, str):
            return key
        try:
            # Try to create a stable hash
            key_str = json.dumps(key, sort_keys=True, default=str)
            return hashlib.md5(key_str.encode()).hexdigest()
        except Exception:
            return hashlib.md5(str(key).encode()).hexdigest()

    def _estimate_size(self, value: Any) -> int:
        """Estimate size of value in bytes."""
        try:
            return len(pickle.dumps(value))
        except Exception:
            return len(str(value))

    def get(self, key: Any, default: T = None) -> Optional[T]:
        """Get value from cache."""
        cache_key = self._make_key(key)

        with self._lock:
            entry = self._cache.get(cache_key)

            if entry is None:
                self._stats.misses += 1
                return default

            if entry.is_expired:
                del self._cache[cache_key]
                self._stats.misses += 1
                self._stats.evictions += 1
                return default

            # Move to end (LRU)
            self._cache.move_to_end(cache_key)
            entry.touch()
            self._stats.hits += 1

            return entry.value

    def set(
        self,
        key: Any,
        value: T,
        ttl_seconds: float = None,
        metadata: Dict[str, Any] = None,
    ) -> None:
        """Set value in cache."""
        cache_key = self._make_key(key)
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        size = self._estimate_size(value)

        with self._lock:
            # Check size limits
            while len(self._cache) >= self.max_size:
                self._evict_one()

            while self._stats.size_bytes + size > self.max_memory_bytes and self._cache:
                self._evict_one()

            # Create entry
            entry = CacheEntry(
                key=cache_key,
                value=value,
                ttl_seconds=ttl,
                size_bytes=size,
                metadata=metadata or {},
            )

            # Update stats if replacing
            if cache_key in self._cache:
                old_size = self._cache[cache_key].size_bytes
                self._stats.size_bytes -= old_size

            self._cache[cache_key] = entry
            self._stats.size_bytes += size
            self._stats.entry_count = len(self._cache)

    def delete(self, key: Any) -> bool:
        """Delete entry from cache."""
        cache_key = self._make_key(key)

        with self._lock:
            if cache_key in self._cache:
                entry = self._cache.pop(cache_key)
                self._stats.size_bytes -= entry.size_bytes
                self._stats.entry_count = len(self._cache)
                return True
            return False

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._stats = CacheStats()

    def _evict_one(self) -> None:
        """Evict one entry based on strategy."""
        if not self._cache:
            return

        # LRU: Remove oldest (first item)
        key, entry = self._cache.popitem(last=False)
        self._stats.size_bytes -= entry.size_bytes
        self._stats.evictions += 1
        self._stats.entry_count = len(self._cache)

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        return self._stats

    def __contains__(self, key: Any) -> bool:
        cache_key = self._make_key(key)
        with self._lock:
            if cache_key not in self._cache:
                return False
            return not self._cache[cache_key].is_expired

    def __len__(self) -> int:
        return len(self._cache)


class LFUCache(BaseCache[T]):
    """Least Frequently Used cache."""

    def _evict_one(self) -> None:
        """Evict least frequently used entry."""
        if not self._cache:
            return

        # Find entry with lowest access count
        min_count = float('inf')
        min_key = None

        for key, entry in self._cache.items():
            if entry.access_count < min_count:
                min_count = entry.access_count
                min_key = key

        if min_key:
            entry = self._cache.pop(min_key)
            self._stats.size_bytes -= entry.size_bytes
            self._stats.evictions += 1
            self._stats.entry_count = len(self._cache)


class AdaptiveCache(BaseCache[T]):
    """
    Adaptive cache that learns access patterns.

    Combines LRU and LFU based on workload.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._lru_weight = 0.5
        self._pattern_history: List[str] = []

    def get(self, key: Any, default: T = None) -> Optional[T]:
        result = super().get(key, default)

        # Track access pattern
        cache_key = self._make_key(key)
        self._pattern_history.append(cache_key)

        # Keep only recent history
        if len(self._pattern_history) > 1000:
            self._pattern_history = self._pattern_history[-500:]

        # Adjust weights based on patterns
        self._adapt_weights()

        return result

    def _adapt_weights(self) -> None:
        """Adapt eviction weights based on access patterns."""
        if len(self._pattern_history) < 100:
            return

        # Count unique accesses vs repeated accesses
        recent = self._pattern_history[-100:]
        unique_rate = len(set(recent)) / len(recent)

        # More unique accesses = favor LRU
        # More repeated accesses = favor LFU
        self._lru_weight = unique_rate

    def _evict_one(self) -> None:
        """Evict based on adaptive weights."""
        if not self._cache:
            return

        # Score each entry
        scores: Dict[str, float] = {}
        now = time.time()

        for key, entry in self._cache.items():
            # LRU score (how recently accessed)
            recency = now - entry.accessed_at
            lru_score = recency  # Higher = older = worse

            # LFU score (how frequently accessed)
            lfu_score = 1 / (entry.access_count + 1)  # Higher = less frequent = worse

            # Combined score
            scores[key] = (self._lru_weight * lru_score +
                          (1 - self._lru_weight) * lfu_score * 1000)

        # Evict highest scoring entry
        worst_key = max(scores, key=scores.get)
        entry = self._cache.pop(worst_key)
        self._stats.size_bytes -= entry.size_bytes
        self._stats.evictions += 1
        self._stats.entry_count = len(self._cache)


class TieredCache:
    """
    Multi-tiered caching system.

    L1: In-memory (fastest, smallest)
    L2: Local disk (slower, larger)
    L3: Distributed (slowest, largest)
    """

    def __init__(
        self,
        l1_size: int = 1000,
        l2_path: Path = None,
        l1_ttl: float = 300,       # 5 minutes
        l2_ttl: float = 3600,      # 1 hour
    ):
        self.l1 = AdaptiveCache(max_size=l1_size, ttl_seconds=l1_ttl)
        self.l2_path = l2_path or Path.home() / ".bael_cache"
        self.l2_ttl = l2_ttl

        # Create L2 directory
        self.l2_path.mkdir(parents=True, exist_ok=True)

        self._stats = {
            "l1_hits": 0,
            "l2_hits": 0,
            "misses": 0,
        }

    def get(self, key: Any, default: T = None) -> Optional[T]:
        """Get from cache, checking L1 then L2."""
        # Try L1
        value = self.l1.get(key)
        if value is not None:
            self._stats["l1_hits"] += 1
            return value

        # Try L2
        value = self._l2_get(key)
        if value is not None:
            self._stats["l2_hits"] += 1
            # Promote to L1
            self.l1.set(key, value)
            return value

        self._stats["misses"] += 1
        return default

    def set(self, key: Any, value: T, persist: bool = True) -> None:
        """Set in L1 and optionally L2."""
        self.l1.set(key, value)

        if persist:
            self._l2_set(key, value)

    def _l2_key_path(self, key: Any) -> Path:
        """Get L2 file path for key."""
        if isinstance(key, str):
            safe_key = hashlib.md5(key.encode()).hexdigest()
        else:
            safe_key = hashlib.md5(str(key).encode()).hexdigest()
        return self.l2_path / f"{safe_key}.cache"

    def _l2_get(self, key: Any) -> Optional[T]:
        """Get from L2 disk cache."""
        path = self._l2_key_path(key)

        if not path.exists():
            return None

        try:
            with open(path, 'rb') as f:
                entry = pickle.load(f)

            # Check TTL
            if time.time() > entry['created_at'] + self.l2_ttl:
                path.unlink()
                return None

            return entry['value']
        except Exception as e:
            logger.debug(f"L2 cache read error: {e}")
            return None

    def _l2_set(self, key: Any, value: T) -> None:
        """Set in L2 disk cache."""
        path = self._l2_key_path(key)

        try:
            entry = {
                'value': value,
                'created_at': time.time(),
            }
            with open(path, 'wb') as f:
                pickle.dump(entry, f)
        except Exception as e:
            logger.debug(f"L2 cache write error: {e}")

    def clear(self) -> None:
        """Clear all cache levels."""
        self.l1.clear()

        # Clear L2
        for path in self.l2_path.glob("*.cache"):
            try:
                path.unlink()
            except Exception:
                pass

    def get_stats(self) -> Dict[str, Any]:
        """Get tiered cache statistics."""
        total = self._stats["l1_hits"] + self._stats["l2_hits"] + self._stats["misses"]
        return {
            "l1_hits": self._stats["l1_hits"],
            "l2_hits": self._stats["l2_hits"],
            "misses": self._stats["misses"],
            "l1_hit_rate": self._stats["l1_hits"] / total if total > 0 else 0,
            "overall_hit_rate": (self._stats["l1_hits"] + self._stats["l2_hits"]) / total if total > 0 else 0,
            "l1_stats": self.l1.get_stats().__dict__,
        }


class UltimateCacheSystem:
    """
    The ultimate caching system for BAEL.

    Features:
    - Multi-tiered caching
    - Adaptive eviction
    - Semantic similarity caching for LLM responses
    - Predictive pre-caching
    - Automatic invalidation
    """

    def __init__(
        self,
        strategy: CacheStrategy = CacheStrategy.TIERED,
        l1_size: int = 1000,
        l2_path: Path = None,
    ):
        self.strategy = strategy

        if strategy == CacheStrategy.TIERED:
            self._cache = TieredCache(l1_size=l1_size, l2_path=l2_path)
        elif strategy == CacheStrategy.LFU:
            self._cache = LFUCache(max_size=l1_size)
        elif strategy == CacheStrategy.ADAPTIVE:
            self._cache = AdaptiveCache(max_size=l1_size)
        else:
            self._cache = BaseCache(max_size=l1_size)

        # Semantic cache for LLM responses
        self._semantic_cache: Dict[str, List[Tuple[str, Any]]] = {}

        # Prediction model for pre-caching
        self._access_patterns: List[str] = []

    def get(self, key: Any, default: Any = None) -> Any:
        """Get from cache."""
        return self._cache.get(key, default)

    def set(self, key: Any, value: Any, **kwargs) -> None:
        """Set in cache."""
        if isinstance(self._cache, TieredCache):
            self._cache.set(key, value, persist=kwargs.get('persist', True))
        else:
            self._cache.set(key, value, **kwargs)

    def get_semantic(self, query: str, threshold: float = 0.8) -> Optional[Any]:
        """
        Get semantically similar cached result.

        For LLM responses where exact match isn't needed.
        """
        # Simple word overlap similarity
        query_words = set(query.lower().split())

        best_match = None
        best_score = 0.0

        for cached_query, responses in self._semantic_cache.items():
            cached_words = set(cached_query.lower().split())

            # Jaccard similarity
            intersection = len(query_words & cached_words)
            union = len(query_words | cached_words)
            similarity = intersection / union if union > 0 else 0

            if similarity > best_score and similarity >= threshold:
                best_score = similarity
                best_match = responses[-1][1] if responses else None

        return best_match

    def set_semantic(self, query: str, response: Any) -> None:
        """Store response with semantic key."""
        if query not in self._semantic_cache:
            self._semantic_cache[query] = []
        self._semantic_cache[query].append((time.time(), response))

        # Keep only recent responses
        if len(self._semantic_cache[query]) > 5:
            self._semantic_cache[query] = self._semantic_cache[query][-5:]

    def prefetch(self, keys: List[Any], loader: Callable[[Any], Any]) -> None:
        """Pre-fetch keys into cache."""
        for key in keys:
            if key not in self._cache:
                try:
                    value = loader(key)
                    self.set(key, value)
                except Exception as e:
                    logger.debug(f"Prefetch failed for {key}: {e}")

    async def prefetch_async(
        self,
        keys: List[Any],
        loader: Callable[[Any], Any],
    ) -> None:
        """Async pre-fetch keys into cache."""
        async def load_one(key):
            if key not in self._cache:
                try:
                    if asyncio.iscoroutinefunction(loader):
                        value = await loader(key)
                    else:
                        value = loader(key)
                    self.set(key, value)
                except Exception as e:
                    logger.debug(f"Async prefetch failed for {key}: {e}")

        await asyncio.gather(*[load_one(k) for k in keys])

    def predict_and_prefetch(self, current_key: Any, loader: Callable) -> None:
        """Predict next likely keys and prefetch."""
        # Record access pattern
        self._access_patterns.append(str(current_key))

        if len(self._access_patterns) > 100:
            self._access_patterns = self._access_patterns[-50:]

        # Simple next-key prediction
        if len(self._access_patterns) >= 2:
            current = self._access_patterns[-1]

            # Find what usually comes after current
            predictions = []
            for i, key in enumerate(self._access_patterns[:-1]):
                if key == current and i + 1 < len(self._access_patterns):
                    predictions.append(self._access_patterns[i + 1])

            if predictions:
                # Prefetch most common prediction
                from collections import Counter
                most_common = Counter(predictions).most_common(1)[0][0]
                self.prefetch([most_common], loader)

    def clear(self) -> None:
        """Clear all caches."""
        self._cache.clear()
        self._semantic_cache.clear()
        self._access_patterns.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive stats."""
        if isinstance(self._cache, TieredCache):
            cache_stats = self._cache.get_stats()
        else:
            cache_stats = self._cache.get_stats().__dict__

        return {
            "strategy": self.strategy.value,
            "cache_stats": cache_stats,
            "semantic_queries": len(self._semantic_cache),
            "pattern_length": len(self._access_patterns),
        }


# =============================================================================
# DECORATORS
# =============================================================================

_default_cache = UltimateCacheSystem()


def cached(
    ttl_seconds: float = None,
    cache: UltimateCacheSystem = None,
):
    """Decorator to cache function results."""
    def decorator(func: Callable) -> Callable:
        nonlocal cache
        if cache is None:
            cache = _default_cache

        async def async_wrapper(*args, **kwargs):
            key = (func.__name__, args, tuple(sorted(kwargs.items())))
            result = cache.get(key)

            if result is not None:
                return result

            result = await func(*args, **kwargs)
            cache.set(key, result, ttl_seconds=ttl_seconds)
            return result

        def sync_wrapper(*args, **kwargs):
            key = (func.__name__, args, tuple(sorted(kwargs.items())))
            result = cache.get(key)

            if result is not None:
                return result

            result = func(*args, **kwargs)
            cache.set(key, result, ttl_seconds=ttl_seconds)
            return result

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def semantic_cached(threshold: float = 0.8, cache: UltimateCacheSystem = None):
    """Decorator for semantic caching of LLM responses."""
    def decorator(func: Callable) -> Callable:
        nonlocal cache
        if cache is None:
            cache = _default_cache

        async def wrapper(query: str, *args, **kwargs):
            # Check semantic cache first
            cached = cache.get_semantic(query, threshold)
            if cached is not None:
                return cached

            # Call function
            result = await func(query, *args, **kwargs)

            # Store in semantic cache
            cache.set_semantic(query, result)

            return result

        return wrapper

    return decorator
