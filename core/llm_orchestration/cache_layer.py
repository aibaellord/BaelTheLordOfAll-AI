"""
BAEL Semantic Cache Layer
==========================

Intelligent caching with semantic similarity matching.
Reduces API costs by reusing responses for similar queries.

Features:
- Exact match caching
- Semantic similarity caching (embeddings)
- TTL and LRU eviction
- Cache warming and preloading
- Namespace isolation
- Compression support
- Hit rate analytics
- Distributed cache support
"""

import hashlib
import json
import logging
import time
import zlib
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """Cache lookup strategies."""
    EXACT_MATCH = "exact_match"       # Only exact query matches
    SEMANTIC = "semantic"             # Embedding similarity
    FUZZY = "fuzzy"                   # Text similarity heuristics
    HYBRID = "hybrid"                 # Combine all strategies


class EvictionPolicy(Enum):
    """Cache eviction policies."""
    LRU = "lru"         # Least Recently Used
    LFU = "lfu"         # Least Frequently Used
    TTL = "ttl"         # Time To Live
    FIFO = "fifo"       # First In First Out


@dataclass
class CacheEntry:
    """A single cache entry."""
    key: str
    value: Any
    created_at: datetime
    accessed_at: datetime
    expires_at: Optional[datetime]
    access_count: int = 1
    size_bytes: int = 0
    compressed: bool = False
    namespace: str = "default"
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at


@dataclass
class CacheStats:
    """Cache statistics."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expirations: int = 0
    total_entries: int = 0
    total_size_bytes: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class SemanticCache:
    """
    Intelligent caching layer with semantic similarity support.
    """

    def __init__(
        self,
        max_entries: int = 10000,
        max_size_bytes: int = 100 * 1024 * 1024,  # 100MB
        default_ttl: int = 3600,  # 1 hour
        strategy: CacheStrategy = CacheStrategy.HYBRID,
        eviction_policy: EvictionPolicy = EvictionPolicy.LRU,
        compression_threshold: int = 1024,  # Compress if > 1KB
        similarity_threshold: float = 0.92,  # For semantic matching
    ):
        self.max_entries = max_entries
        self.max_size_bytes = max_size_bytes
        self.default_ttl = default_ttl
        self.strategy = strategy
        self.eviction_policy = eviction_policy
        self.compression_threshold = compression_threshold
        self.similarity_threshold = similarity_threshold

        # Storage (OrderedDict for LRU support)
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()

        # Namespace separation
        self._namespaces: Dict[str, set] = {"default": set()}

        # Embedding index for semantic search
        self._embedding_index: Dict[str, List[float]] = {}

        # Statistics
        self.stats = CacheStats()

        # Current size tracking
        self._current_size = 0

    def _hash_key(self, key: str, namespace: str = "default") -> str:
        """Create hash key for cache lookup."""
        combined = f"{namespace}:{key}"
        return hashlib.sha256(combined.encode()).hexdigest()[:32]

    def _hash_messages(self, messages: List[Dict[str, str]]) -> str:
        """Create hash from message list."""
        content = json.dumps(messages, sort_keys=True)
        return self._hash_key(content)

    def _compress(self, data: str) -> Tuple[bytes, bool]:
        """Compress data if above threshold."""
        data_bytes = data.encode()
        if len(data_bytes) > self.compression_threshold:
            compressed = zlib.compress(data_bytes, level=6)
            if len(compressed) < len(data_bytes) * 0.8:  # Only if 20%+ savings
                return compressed, True
        return data_bytes, False

    def _decompress(self, data: bytes, compressed: bool) -> str:
        """Decompress data if needed."""
        if compressed:
            return zlib.decompress(data).decode()
        return data.decode()

    def _evict_if_needed(self) -> None:
        """Evict entries if cache is full."""
        # Check entry count
        while len(self._cache) >= self.max_entries:
            self._evict_one()

        # Check size
        while self._current_size >= self.max_size_bytes:
            self._evict_one()

    def _evict_one(self) -> None:
        """Evict one entry based on policy."""
        if not self._cache:
            return

        if self.eviction_policy == EvictionPolicy.LRU:
            # Remove first (least recently used)
            key, entry = self._cache.popitem(last=False)
        elif self.eviction_policy == EvictionPolicy.LFU:
            # Remove least frequently accessed
            min_entry = min(self._cache.items(), key=lambda x: x[1].access_count)
            key = min_entry[0]
            entry = self._cache.pop(key)
        elif self.eviction_policy == EvictionPolicy.FIFO:
            # Remove oldest
            min_entry = min(self._cache.items(), key=lambda x: x[1].created_at)
            key = min_entry[0]
            entry = self._cache.pop(key)
        elif self.eviction_policy == EvictionPolicy.TTL:
            # Remove expired first, then oldest
            expired = [k for k, v in self._cache.items() if v.is_expired()]
            if expired:
                key = expired[0]
                entry = self._cache.pop(key)
            else:
                key, entry = self._cache.popitem(last=False)
        else:
            key, entry = self._cache.popitem(last=False)

        self._current_size -= entry.size_bytes
        self.stats.evictions += 1

        # Remove from namespace tracking
        if entry.namespace in self._namespaces:
            self._namespaces[entry.namespace].discard(key)

        # Remove from embedding index
        if key in self._embedding_index:
            del self._embedding_index[key]

    def _cosine_similarity(
        self,
        vec1: List[float],
        vec2: List[float],
    ) -> float:
        """Calculate cosine similarity between vectors."""
        if len(vec1) != len(vec2):
            return 0.0

        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot / (norm1 * norm2)

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Simple text similarity (Jaccard on words)."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def get(
        self,
        key: str,
        namespace: str = "default",
    ) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key
            namespace: Cache namespace

        Returns:
            Cached value or None
        """
        hash_key = self._hash_key(key, namespace)

        if hash_key in self._cache:
            entry = self._cache[hash_key]

            # Check expiration
            if entry.is_expired():
                self._cache.pop(hash_key)
                self._current_size -= entry.size_bytes
                self.stats.expirations += 1
                self.stats.misses += 1
                return None

            # Update access
            entry.accessed_at = datetime.now()
            entry.access_count += 1

            # Move to end for LRU
            self._cache.move_to_end(hash_key)

            self.stats.hits += 1

            # Decompress if needed
            if isinstance(entry.value, bytes):
                return self._decompress(entry.value, entry.compressed)
            return entry.value

        self.stats.misses += 1
        return None

    def get_by_messages(
        self,
        messages: List[Dict[str, str]],
        namespace: str = "default",
    ) -> Optional[Any]:
        """Get cached response for messages."""
        key = self._hash_messages(messages)
        return self.get(key, namespace)

    def set(
        self,
        key: str,
        value: Any,
        namespace: str = "default",
        ttl: Optional[int] = None,
        embedding: Optional[List[float]] = None,
    ) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            namespace: Cache namespace
            ttl: Time to live in seconds
            embedding: Optional embedding for semantic search
        """
        hash_key = self._hash_key(key, namespace)
        ttl = ttl or self.default_ttl

        # Compress if string and large
        compressed = False
        if isinstance(value, str):
            value, compressed = self._compress(value)

        # Calculate size
        if isinstance(value, bytes):
            size_bytes = len(value)
        elif isinstance(value, str):
            size_bytes = len(value.encode())
        else:
            size_bytes = len(json.dumps(value).encode())

        # Evict if needed
        self._evict_if_needed()

        entry = CacheEntry(
            key=hash_key,
            value=value,
            created_at=datetime.now(),
            accessed_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=ttl) if ttl > 0 else None,
            size_bytes=size_bytes,
            compressed=compressed,
            namespace=namespace,
            embedding=embedding,
        )

        # Update size
        if hash_key in self._cache:
            self._current_size -= self._cache[hash_key].size_bytes
        self._current_size += size_bytes

        self._cache[hash_key] = entry
        self.stats.total_entries = len(self._cache)
        self.stats.total_size_bytes = self._current_size

        # Track namespace
        if namespace not in self._namespaces:
            self._namespaces[namespace] = set()
        self._namespaces[namespace].add(hash_key)

        # Index embedding
        if embedding:
            self._embedding_index[hash_key] = embedding

    def set_by_messages(
        self,
        messages: List[Dict[str, str]],
        value: Any,
        namespace: str = "default",
        ttl: Optional[int] = None,
        embedding: Optional[List[float]] = None,
    ) -> None:
        """Cache response for messages."""
        key = self._hash_messages(messages)
        self.set(key, value, namespace, ttl, embedding)

    def find_similar(
        self,
        embedding: List[float],
        threshold: Optional[float] = None,
        namespace: str = "default",
    ) -> Optional[Tuple[str, float]]:
        """
        Find semantically similar cached entry.

        Args:
            embedding: Query embedding
            threshold: Similarity threshold (default: self.similarity_threshold)
            namespace: Cache namespace

        Returns:
            Tuple of (cached_value, similarity_score) or None
        """
        threshold = threshold or self.similarity_threshold
        best_match = None
        best_score = 0.0

        for key, cached_embedding in self._embedding_index.items():
            if key in self._cache:
                entry = self._cache[key]
                if entry.namespace != namespace:
                    continue
                if entry.is_expired():
                    continue

                similarity = self._cosine_similarity(embedding, cached_embedding)
                if similarity > best_score and similarity >= threshold:
                    best_score = similarity
                    best_match = key

        if best_match:
            value = self.get(best_match)  # This updates stats
            return (value, best_score)

        return None

    def find_fuzzy(
        self,
        query: str,
        threshold: float = 0.7,
        namespace: str = "default",
    ) -> Optional[Tuple[Any, float]]:
        """
        Find fuzzy text match in cache.

        Args:
            query: Query text
            threshold: Similarity threshold
            namespace: Cache namespace

        Returns:
            Tuple of (cached_value, similarity_score) or None
        """
        best_match = None
        best_score = 0.0

        for key, entry in self._cache.items():
            if entry.namespace != namespace:
                continue
            if entry.is_expired():
                continue

            # Try to get original key from metadata
            original_key = entry.metadata.get("original_key", "")
            if original_key:
                similarity = self._text_similarity(query, original_key)
                if similarity > best_score and similarity >= threshold:
                    best_score = similarity
                    best_match = key

        if best_match:
            value = self.get(best_match)
            return (value, best_score)

        return None

    def delete(
        self,
        key: str,
        namespace: str = "default",
    ) -> bool:
        """Delete entry from cache."""
        hash_key = self._hash_key(key, namespace)

        if hash_key in self._cache:
            entry = self._cache.pop(hash_key)
            self._current_size -= entry.size_bytes

            if namespace in self._namespaces:
                self._namespaces[namespace].discard(hash_key)

            if hash_key in self._embedding_index:
                del self._embedding_index[hash_key]

            return True
        return False

    def clear(self, namespace: Optional[str] = None) -> int:
        """
        Clear cache entries.

        Args:
            namespace: If provided, only clear this namespace

        Returns:
            Number of entries cleared
        """
        if namespace is None:
            count = len(self._cache)
            self._cache.clear()
            self._embedding_index.clear()
            self._namespaces = {"default": set()}
            self._current_size = 0
            return count

        if namespace not in self._namespaces:
            return 0

        count = 0
        keys_to_remove = list(self._namespaces[namespace])
        for key in keys_to_remove:
            if key in self._cache:
                entry = self._cache.pop(key)
                self._current_size -= entry.size_bytes
                count += 1
            if key in self._embedding_index:
                del self._embedding_index[key]

        self._namespaces[namespace].clear()
        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "entries": len(self._cache),
            "size_bytes": self._current_size,
            "size_mb": self._current_size / (1024 * 1024),
            "hits": self.stats.hits,
            "misses": self.stats.misses,
            "hit_rate": f"{self.stats.hit_rate:.2%}",
            "evictions": self.stats.evictions,
            "expirations": self.stats.expirations,
            "namespaces": list(self._namespaces.keys()),
            "embeddings_indexed": len(self._embedding_index),
        }


def demo():
    """Demonstrate semantic cache."""
    print("=" * 60)
    print("BAEL Semantic Cache Demo")
    print("=" * 60)

    cache = SemanticCache(max_entries=100)

    # Test basic caching
    cache.set("test_key", "test_value")
    result = cache.get("test_key")
    print(f"\nBasic get: {result}")

    # Test message caching
    messages = [{"role": "user", "content": "What is Python?"}]
    cache.set_by_messages(messages, "Python is a programming language...")
    result = cache.get_by_messages(messages)
    print(f"Message cache get: {result[:50]}...")

    # Test stats
    print(f"\nCache stats: {cache.get_stats()}")


if __name__ == "__main__":
    demo()
