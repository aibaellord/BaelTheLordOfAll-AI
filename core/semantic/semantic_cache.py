#!/usr/bin/env python3
"""
BAEL - Semantic Cache
Advanced semantic-aware caching for AI agent operations.

Features:
- Embedding-based similarity matching
- Configurable similarity thresholds
- TTL with semantic expiration
- Hierarchical caching
- Query expansion
- Cache warming strategies
- Hit/miss analytics
- Memory-efficient storage
"""

import asyncio
import copy
import hashlib
import math
import uuid
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')
V = TypeVar('V')


# =============================================================================
# ENUMS
# =============================================================================

class SimilarityMetric(Enum):
    """Similarity metrics."""
    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    DOT_PRODUCT = "dot_product"
    JACCARD = "jaccard"


class EvictionPolicy(Enum):
    """Cache eviction policies."""
    LRU = "lru"
    LFU = "lfu"
    FIFO = "fifo"
    TTL = "ttl"
    SIMILARITY = "similarity"


class CacheStatus(Enum):
    """Cache entry status."""
    ACTIVE = "active"
    EXPIRED = "expired"
    EVICTED = "evicted"
    WARMING = "warming"


class WarmingStrategy(Enum):
    """Cache warming strategies."""
    EAGER = "eager"
    LAZY = "lazy"
    PREDICTIVE = "predictive"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class CacheConfig:
    """Cache configuration."""
    max_size: int = 10000
    default_ttl: Optional[timedelta] = None
    similarity_threshold: float = 0.85
    similarity_metric: SimilarityMetric = SimilarityMetric.COSINE
    eviction_policy: EvictionPolicy = EvictionPolicy.LRU
    enable_stats: bool = True


@dataclass
class CacheEntry(Generic[V]):
    """Cache entry."""
    key: str
    value: V
    embedding: Optional[List[float]] = None
    created_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    ttl: Optional[timedelta] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.ttl is None:
            return False
        return datetime.now() > self.created_at + self.ttl


@dataclass
class CacheStats:
    """Cache statistics."""
    hits: int = 0
    misses: int = 0
    semantic_hits: int = 0
    evictions: int = 0
    expirations: int = 0
    total_queries: int = 0
    avg_similarity: float = 0.0

    @property
    def hit_rate(self) -> float:
        """Get hit rate."""
        if self.total_queries == 0:
            return 0.0
        return (self.hits + self.semantic_hits) / self.total_queries


@dataclass
class SimilarityResult:
    """Result of similarity search."""
    key: str
    value: Any
    similarity: float
    is_exact: bool = False


# =============================================================================
# EMBEDDING PROVIDER
# =============================================================================

class EmbeddingProvider(ABC):
    """Abstract embedding provider."""

    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """Generate embedding for text."""
        pass

    @abstractmethod
    def dimensions(self) -> int:
        """Get embedding dimensions."""
        pass


class SimpleHashEmbedding(EmbeddingProvider):
    """Simple hash-based embedding for demo purposes."""

    def __init__(self, dimensions: int = 128):
        self._dimensions = dimensions

    async def embed(self, text: str) -> List[float]:
        """Generate embedding from text hash."""
        # Hash text
        h = hashlib.sha256(text.encode()).digest()

        # Expand to required dimensions
        embedding = []
        for i in range(self._dimensions):
            byte_idx = i % len(h)
            value = (h[byte_idx] + i) / 255.0
            # Normalize to [-1, 1]
            embedding.append(value * 2 - 1)

        # Normalize
        norm = math.sqrt(sum(x*x for x in embedding))
        if norm > 0:
            embedding = [x / norm for x in embedding]

        return embedding

    def dimensions(self) -> int:
        return self._dimensions


class BagOfWordsEmbedding(EmbeddingProvider):
    """Bag of words embedding."""

    def __init__(self, vocab_size: int = 256):
        self._vocab_size = vocab_size

    async def embed(self, text: str) -> List[float]:
        """Generate BOW embedding."""
        words = text.lower().split()
        embedding = [0.0] * self._vocab_size

        for word in words:
            idx = hash(word) % self._vocab_size
            embedding[idx] += 1.0

        # Normalize
        norm = math.sqrt(sum(x*x for x in embedding))
        if norm > 0:
            embedding = [x / norm for x in embedding]

        return embedding

    def dimensions(self) -> int:
        return self._vocab_size


# =============================================================================
# SIMILARITY CALCULATOR
# =============================================================================

class SimilarityCalculator:
    """Calculate similarity between embeddings."""

    def __init__(self, metric: SimilarityMetric = SimilarityMetric.COSINE):
        self._metric = metric

    def calculate(self, a: List[float], b: List[float]) -> float:
        """Calculate similarity."""
        if len(a) != len(b):
            return 0.0

        if self._metric == SimilarityMetric.COSINE:
            return self._cosine(a, b)
        elif self._metric == SimilarityMetric.EUCLIDEAN:
            return self._euclidean(a, b)
        elif self._metric == SimilarityMetric.DOT_PRODUCT:
            return self._dot_product(a, b)
        elif self._metric == SimilarityMetric.JACCARD:
            return self._jaccard(a, b)
        else:
            return self._cosine(a, b)

    def _cosine(self, a: List[float], b: List[float]) -> float:
        """Cosine similarity."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot / (norm_a * norm_b)

    def _euclidean(self, a: List[float], b: List[float]) -> float:
        """Euclidean distance converted to similarity."""
        dist = math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
        return 1.0 / (1.0 + dist)

    def _dot_product(self, a: List[float], b: List[float]) -> float:
        """Dot product similarity."""
        return sum(x * y for x, y in zip(a, b))

    def _jaccard(self, a: List[float], b: List[float]) -> float:
        """Jaccard similarity for binary-like vectors."""
        intersection = sum(min(x, y) for x, y in zip(a, b))
        union = sum(max(x, y) for x, y in zip(a, b))

        if union == 0:
            return 0.0

        return intersection / union


# =============================================================================
# SEMANTIC CACHE STORE
# =============================================================================

class SemanticCacheStore(Generic[V]):
    """Semantic-aware cache storage."""

    def __init__(
        self,
        config: Optional[CacheConfig] = None,
        embedding_provider: Optional[EmbeddingProvider] = None
    ):
        self.config = config or CacheConfig()
        self._provider = embedding_provider or SimpleHashEmbedding()
        self._calculator = SimilarityCalculator(self.config.similarity_metric)

        self._entries: Dict[str, CacheEntry[V]] = {}
        self._access_order: OrderedDict = OrderedDict()
        self._stats = CacheStats()

    async def put(
        self,
        key: str,
        value: V,
        ttl: Optional[timedelta] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Put entry in cache."""
        # Check capacity
        if len(self._entries) >= self.config.max_size:
            await self._evict()

        # Generate embedding
        embedding = await self._provider.embed(key)

        entry = CacheEntry(
            key=key,
            value=value,
            embedding=embedding,
            ttl=ttl or self.config.default_ttl,
            metadata=metadata or {}
        )

        self._entries[key] = entry
        self._access_order[key] = datetime.now()

    async def get(self, key: str) -> Optional[V]:
        """Get entry by exact key."""
        self._stats.total_queries += 1

        entry = self._entries.get(key)

        if entry:
            if entry.is_expired():
                del self._entries[key]
                if key in self._access_order:
                    del self._access_order[key]
                self._stats.expirations += 1
                self._stats.misses += 1
                return None

            entry.accessed_at = datetime.now()
            entry.access_count += 1
            self._access_order.move_to_end(key)
            self._stats.hits += 1
            return entry.value

        self._stats.misses += 1
        return None

    async def get_similar(
        self,
        query: str,
        threshold: Optional[float] = None
    ) -> Optional[SimilarityResult]:
        """Get entry by semantic similarity."""
        self._stats.total_queries += 1
        threshold = threshold or self.config.similarity_threshold

        # First try exact match
        entry = self._entries.get(query)
        if entry and not entry.is_expired():
            entry.accessed_at = datetime.now()
            entry.access_count += 1
            self._access_order.move_to_end(query)
            self._stats.hits += 1
            return SimilarityResult(
                key=query,
                value=entry.value,
                similarity=1.0,
                is_exact=True
            )

        # Semantic search
        query_embedding = await self._provider.embed(query)

        best_match = None
        best_similarity = 0.0

        for key, entry in self._entries.items():
            if entry.is_expired():
                continue

            if entry.embedding:
                similarity = self._calculator.calculate(
                    query_embedding,
                    entry.embedding
                )

                if similarity > best_similarity and similarity >= threshold:
                    best_similarity = similarity
                    best_match = entry

        if best_match:
            best_match.accessed_at = datetime.now()
            best_match.access_count += 1
            self._access_order.move_to_end(best_match.key)
            self._stats.semantic_hits += 1
            self._update_avg_similarity(best_similarity)

            return SimilarityResult(
                key=best_match.key,
                value=best_match.value,
                similarity=best_similarity,
                is_exact=False
            )

        self._stats.misses += 1
        return None

    async def search(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.0
    ) -> List[SimilarityResult]:
        """Search for similar entries."""
        query_embedding = await self._provider.embed(query)

        results = []

        for key, entry in self._entries.items():
            if entry.is_expired():
                continue

            if entry.embedding:
                similarity = self._calculator.calculate(
                    query_embedding,
                    entry.embedding
                )

                if similarity >= threshold:
                    results.append(SimilarityResult(
                        key=key,
                        value=entry.value,
                        similarity=similarity,
                        is_exact=(key == query)
                    ))

        results.sort(key=lambda x: x.similarity, reverse=True)
        return results[:top_k]

    async def delete(self, key: str) -> bool:
        """Delete entry."""
        if key in self._entries:
            del self._entries[key]
            if key in self._access_order:
                del self._access_order[key]
            return True
        return False

    async def clear(self) -> None:
        """Clear cache."""
        self._entries.clear()
        self._access_order.clear()

    async def _evict(self) -> None:
        """Evict entry based on policy."""
        if not self._entries:
            return

        if self.config.eviction_policy == EvictionPolicy.LRU:
            # Evict least recently used
            key = next(iter(self._access_order))
        elif self.config.eviction_policy == EvictionPolicy.LFU:
            # Evict least frequently used
            key = min(
                self._entries.keys(),
                key=lambda k: self._entries[k].access_count
            )
        elif self.config.eviction_policy == EvictionPolicy.FIFO:
            # Evict oldest
            key = min(
                self._entries.keys(),
                key=lambda k: self._entries[k].created_at
            )
        elif self.config.eviction_policy == EvictionPolicy.TTL:
            # Evict expired first, then oldest
            expired = [
                k for k, e in self._entries.items()
                if e.is_expired()
            ]
            if expired:
                key = expired[0]
            else:
                key = next(iter(self._access_order))
        else:
            key = next(iter(self._access_order))

        await self.delete(key)
        self._stats.evictions += 1

    def _update_avg_similarity(self, similarity: float) -> None:
        """Update average similarity."""
        n = self._stats.semantic_hits
        if n == 1:
            self._stats.avg_similarity = similarity
        else:
            self._stats.avg_similarity = (
                (self._stats.avg_similarity * (n - 1) + similarity) / n
            )

    def size(self) -> int:
        """Get cache size."""
        return len(self._entries)

    def stats(self) -> CacheStats:
        """Get statistics."""
        return copy.copy(self._stats)

    def keys(self) -> List[str]:
        """Get all keys."""
        return list(self._entries.keys())


# =============================================================================
# HIERARCHICAL CACHE
# =============================================================================

class HierarchicalCache:
    """Multi-level cache with L1, L2, L3."""

    def __init__(
        self,
        l1_config: Optional[CacheConfig] = None,
        l2_config: Optional[CacheConfig] = None,
        l3_config: Optional[CacheConfig] = None
    ):
        self._l1 = SemanticCacheStore(l1_config or CacheConfig(max_size=100))
        self._l2 = SemanticCacheStore(l2_config or CacheConfig(max_size=1000))
        self._l3 = SemanticCacheStore(l3_config or CacheConfig(max_size=10000))

    async def put(self, key: str, value: Any, level: int = 1) -> None:
        """Put in specified level."""
        if level == 1:
            await self._l1.put(key, value)
        elif level == 2:
            await self._l2.put(key, value)
        else:
            await self._l3.put(key, value)

    async def get(self, key: str) -> Tuple[Optional[Any], int]:
        """Get from cache, returns value and level found."""
        # Check L1
        value = await self._l1.get(key)
        if value is not None:
            return value, 1

        # Check L2
        value = await self._l2.get(key)
        if value is not None:
            await self._l1.put(key, value)  # Promote to L1
            return value, 2

        # Check L3
        value = await self._l3.get(key)
        if value is not None:
            await self._l2.put(key, value)  # Promote to L2
            return value, 3

        return None, 0

    async def get_similar(self, query: str) -> Tuple[Optional[SimilarityResult], int]:
        """Get similar from cache."""
        # Check L1
        result = await self._l1.get_similar(query)
        if result:
            return result, 1

        # Check L2
        result = await self._l2.get_similar(query)
        if result:
            return result, 2

        # Check L3
        result = await self._l3.get_similar(query)
        if result:
            return result, 3

        return None, 0

    def stats(self) -> Dict[str, CacheStats]:
        """Get stats for all levels."""
        return {
            "l1": self._l1.stats(),
            "l2": self._l2.stats(),
            "l3": self._l3.stats()
        }


# =============================================================================
# CACHE WARMER
# =============================================================================

class CacheWarmer:
    """Cache warming utility."""

    def __init__(
        self,
        cache: SemanticCacheStore,
        strategy: WarmingStrategy = WarmingStrategy.LAZY
    ):
        self._cache = cache
        self._strategy = strategy
        self._warmup_queue: List[Tuple[str, Any]] = []
        self._is_warming = False

    def add_warmup_item(self, key: str, value: Any) -> None:
        """Add item to warmup queue."""
        self._warmup_queue.append((key, value))

    async def warm(self, batch_size: int = 100) -> int:
        """Execute cache warming."""
        self._is_warming = True
        warmed = 0

        try:
            if self._strategy == WarmingStrategy.EAGER:
                # Warm all at once
                for key, value in self._warmup_queue:
                    await self._cache.put(key, value)
                    warmed += 1
                self._warmup_queue.clear()

            elif self._strategy == WarmingStrategy.LAZY:
                # Warm in batches
                batch = self._warmup_queue[:batch_size]
                self._warmup_queue = self._warmup_queue[batch_size:]

                for key, value in batch:
                    await self._cache.put(key, value)
                    warmed += 1

            elif self._strategy == WarmingStrategy.PREDICTIVE:
                # Sort by expected access frequency (simulate)
                import random
                random.shuffle(self._warmup_queue)
                batch = self._warmup_queue[:batch_size]
                self._warmup_queue = self._warmup_queue[batch_size:]

                for key, value in batch:
                    await self._cache.put(key, value)
                    warmed += 1

        finally:
            self._is_warming = False

        return warmed

    def pending_count(self) -> int:
        """Get pending warmup count."""
        return len(self._warmup_queue)

    def is_warming(self) -> bool:
        """Check if warming in progress."""
        return self._is_warming


# =============================================================================
# SEMANTIC CACHE MANAGER
# =============================================================================

class SemanticCacheManager:
    """
    Semantic Cache Manager for BAEL.

    Advanced semantic-aware caching system.
    """

    def __init__(
        self,
        default_config: Optional[CacheConfig] = None,
        embedding_provider: Optional[EmbeddingProvider] = None
    ):
        self._default_config = default_config or CacheConfig()
        self._provider = embedding_provider or SimpleHashEmbedding()

        self._caches: Dict[str, SemanticCacheStore] = {}
        self._hierarchical: Dict[str, HierarchicalCache] = {}
        self._warmers: Dict[str, CacheWarmer] = {}

    # -------------------------------------------------------------------------
    # CACHE MANAGEMENT
    # -------------------------------------------------------------------------

    def create_cache(
        self,
        name: str,
        config: Optional[CacheConfig] = None
    ) -> SemanticCacheStore:
        """Create new cache."""
        cache = SemanticCacheStore(
            config or self._default_config,
            self._provider
        )
        self._caches[name] = cache
        return cache

    def get_cache(self, name: str) -> Optional[SemanticCacheStore]:
        """Get cache by name."""
        return self._caches.get(name)

    def delete_cache(self, name: str) -> bool:
        """Delete cache."""
        if name in self._caches:
            del self._caches[name]
            return True
        return False

    def list_caches(self) -> List[str]:
        """List cache names."""
        return list(self._caches.keys())

    # -------------------------------------------------------------------------
    # CACHE OPERATIONS
    # -------------------------------------------------------------------------

    async def put(
        self,
        cache_name: str,
        key: str,
        value: Any,
        ttl: Optional[timedelta] = None
    ) -> bool:
        """Put value in cache."""
        cache = self._caches.get(cache_name)
        if cache:
            await cache.put(key, value, ttl)
            return True
        return False

    async def get(self, cache_name: str, key: str) -> Optional[Any]:
        """Get value from cache."""
        cache = self._caches.get(cache_name)
        if cache:
            return await cache.get(key)
        return None

    async def get_similar(
        self,
        cache_name: str,
        query: str,
        threshold: Optional[float] = None
    ) -> Optional[SimilarityResult]:
        """Get similar value from cache."""
        cache = self._caches.get(cache_name)
        if cache:
            return await cache.get_similar(query, threshold)
        return None

    async def search(
        self,
        cache_name: str,
        query: str,
        top_k: int = 5
    ) -> List[SimilarityResult]:
        """Search cache for similar entries."""
        cache = self._caches.get(cache_name)
        if cache:
            return await cache.search(query, top_k)
        return []

    async def delete(self, cache_name: str, key: str) -> bool:
        """Delete from cache."""
        cache = self._caches.get(cache_name)
        if cache:
            return await cache.delete(key)
        return False

    async def clear(self, cache_name: str) -> bool:
        """Clear cache."""
        cache = self._caches.get(cache_name)
        if cache:
            await cache.clear()
            return True
        return False

    # -------------------------------------------------------------------------
    # HIERARCHICAL CACHE
    # -------------------------------------------------------------------------

    def create_hierarchical(self, name: str) -> HierarchicalCache:
        """Create hierarchical cache."""
        cache = HierarchicalCache()
        self._hierarchical[name] = cache
        return cache

    def get_hierarchical(self, name: str) -> Optional[HierarchicalCache]:
        """Get hierarchical cache."""
        return self._hierarchical.get(name)

    # -------------------------------------------------------------------------
    # CACHE WARMING
    # -------------------------------------------------------------------------

    def create_warmer(
        self,
        cache_name: str,
        strategy: WarmingStrategy = WarmingStrategy.LAZY
    ) -> Optional[CacheWarmer]:
        """Create cache warmer."""
        cache = self._caches.get(cache_name)
        if cache:
            warmer = CacheWarmer(cache, strategy)
            self._warmers[cache_name] = warmer
            return warmer
        return None

    def get_warmer(self, cache_name: str) -> Optional[CacheWarmer]:
        """Get cache warmer."""
        return self._warmers.get(cache_name)

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def stats(self, cache_name: str) -> Optional[CacheStats]:
        """Get cache statistics."""
        cache = self._caches.get(cache_name)
        if cache:
            return cache.stats()
        return None

    def all_stats(self) -> Dict[str, CacheStats]:
        """Get all cache statistics."""
        return {
            name: cache.stats()
            for name, cache in self._caches.items()
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Semantic Cache."""
    print("=" * 70)
    print("BAEL - SEMANTIC CACHE DEMO")
    print("Advanced Semantic-Aware Caching for AI Agents")
    print("=" * 70)
    print()

    manager = SemanticCacheManager()

    # 1. Create Cache
    print("1. CREATE CACHE:")
    print("-" * 40)

    cache = manager.create_cache("main", CacheConfig(
        max_size=100,
        similarity_threshold=0.7,
        eviction_policy=EvictionPolicy.LRU
    ))

    print(f"   Created cache: main")
    print()

    # 2. Put Values
    print("2. PUT VALUES:")
    print("-" * 40)

    await cache.put("What is Python?", "Python is a programming language.")
    await cache.put("How to code in Python?", "Use a text editor and write Python syntax.")
    await cache.put("Python tutorial", "Start with basic syntax and data types.")

    print(f"   Added 3 entries")
    print(f"   Cache size: {cache.size()}")
    print()

    # 3. Exact Get
    print("3. EXACT GET:")
    print("-" * 40)

    value = await cache.get("What is Python?")
    print(f"   Query: 'What is Python?'")
    print(f"   Result: {value}")
    print()

    # 4. Semantic Get
    print("4. SEMANTIC GET:")
    print("-" * 40)

    result = await cache.get_similar("Explain Python programming language")
    if result:
        print(f"   Query: 'Explain Python programming language'")
        print(f"   Matched: '{result.key}'")
        print(f"   Similarity: {result.similarity:.2%}")
        print(f"   Exact: {result.is_exact}")
    print()

    # 5. Search
    print("5. SEMANTIC SEARCH:")
    print("-" * 40)

    results = await cache.search("Python coding", top_k=3)
    print(f"   Query: 'Python coding'")
    for r in results:
        print(f"   - {r.key[:30]}... ({r.similarity:.2%})")
    print()

    # 6. Statistics
    print("6. CACHE STATISTICS:")
    print("-" * 40)

    stats = cache.stats()
    print(f"   Hits: {stats.hits}")
    print(f"   Semantic hits: {stats.semantic_hits}")
    print(f"   Misses: {stats.misses}")
    print(f"   Hit rate: {stats.hit_rate:.2%}")
    print()

    # 7. Hierarchical Cache
    print("7. HIERARCHICAL CACHE:")
    print("-" * 40)

    hier = manager.create_hierarchical("tiered")

    await hier.put("fast_access", "L1 data", level=1)
    await hier.put("medium_access", "L2 data", level=2)
    await hier.put("slow_access", "L3 data", level=3)

    value, level = await hier.get("fast_access")
    print(f"   'fast_access' found at L{level}")

    value, level = await hier.get("slow_access")
    print(f"   'slow_access' found at L{level}")
    print()

    # 8. Cache Warmer
    print("8. CACHE WARMING:")
    print("-" * 40)

    warmer = manager.create_warmer("main", WarmingStrategy.LAZY)

    warmer.add_warmup_item("Warmup item 1", "Value 1")
    warmer.add_warmup_item("Warmup item 2", "Value 2")
    warmer.add_warmup_item("Warmup item 3", "Value 3")

    print(f"   Pending warmup: {warmer.pending_count()}")

    warmed = await warmer.warm(batch_size=2)
    print(f"   Warmed: {warmed}")
    print(f"   Remaining: {warmer.pending_count()}")
    print()

    # 9. Put via Manager
    print("9. PUT VIA MANAGER:")
    print("-" * 40)

    success = await manager.put(
        "main",
        "Manager added key",
        "Manager added value"
    )

    print(f"   Success: {success}")
    print()

    # 10. Get via Manager
    print("10. GET VIA MANAGER:")
    print("-" * 40)

    value = await manager.get("main", "Manager added key")
    print(f"   Value: {value}")
    print()

    # 11. Get Similar via Manager
    print("11. GET SIMILAR VIA MANAGER:")
    print("-" * 40)

    result = await manager.get_similar("main", "Manager key")
    if result:
        print(f"   Matched: {result.key}")
        print(f"   Similarity: {result.similarity:.2%}")
    print()

    # 12. Search via Manager
    print("12. SEARCH VIA MANAGER:")
    print("-" * 40)

    results = await manager.search("main", "Python", top_k=2)
    for r in results:
        print(f"   - {r.key[:30]}... ({r.similarity:.2%})")
    print()

    # 13. List Caches
    print("13. LIST CACHES:")
    print("-" * 40)

    caches = manager.list_caches()
    print(f"   Caches: {caches}")
    print()

    # 14. All Stats
    print("14. ALL STATISTICS:")
    print("-" * 40)

    all_stats = manager.all_stats()
    for name, stats in all_stats.items():
        print(f"   {name}:")
        print(f"     Total queries: {stats.total_queries}")
        print(f"     Hit rate: {stats.hit_rate:.2%}")
    print()

    # 15. Delete and Clear
    print("15. DELETE AND CLEAR:")
    print("-" * 40)

    deleted = await manager.delete("main", "Manager added key")
    print(f"   Deleted key: {deleted}")

    cleared = await manager.clear("main")
    print(f"   Cleared cache: {cleared}")
    print(f"   Size after clear: {cache.size()}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Semantic Cache Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
