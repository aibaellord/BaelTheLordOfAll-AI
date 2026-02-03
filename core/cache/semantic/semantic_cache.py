"""
BAEL - Semantic Cache
Caches responses with semantic similarity matching.
"""

import asyncio
import hashlib
import json
import logging
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import CacheConfig, CacheEntry, CacheStrategy, SimilarityMetric

logger = logging.getLogger("BAEL.Cache.Semantic")


class SemanticCache:
    """
    Semantic similarity-based cache for LLM responses.

    Features:
    - Exact match caching
    - Semantic similarity matching
    - Embedding-based lookup
    - TTL and LRU eviction
    - Persistence to disk
    """

    def __init__(
        self,
        config: Optional[CacheConfig] = None,
        storage_path: Optional[str] = None
    ):
        self.config = config or CacheConfig()
        self._storage_path = Path(storage_path) if storage_path else None

        self._entries: Dict[str, CacheEntry] = {}
        self._embeddings: Dict[str, List[float]] = {}
        self._exact_index: Dict[str, str] = {}  # hash -> key

        self._embedding_model = None
        self._stats = {
            "hits": 0,
            "misses": 0,
            "semantic_hits": 0,
            "exact_hits": 0
        }

        # Load from disk
        self._load()

    def _load(self) -> None:
        """Load cache from disk."""
        if not self._storage_path:
            return

        cache_file = self._storage_path / "semantic_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r") as f:
                    data = json.load(f)

                    for entry_data in data.get("entries", []):
                        entry = CacheEntry(
                            key=entry_data["key"],
                            query=entry_data["query"],
                            response=entry_data["response"],
                            embedding=entry_data.get("embedding"),
                            metadata=entry_data.get("metadata", {}),
                            created_at=entry_data["created_at"],
                            last_accessed=entry_data["last_accessed"],
                            access_count=entry_data.get("access_count", 0)
                        )
                        self._entries[entry.key] = entry

                        if entry.embedding:
                            self._embeddings[entry.key] = entry.embedding

                        # Index exact match
                        query_hash = self._hash_query(entry.query)
                        self._exact_index[query_hash] = entry.key

                    logger.info(f"Loaded {len(self._entries)} cache entries")

            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")

    def _save(self) -> None:
        """Save cache to disk."""
        if not self._storage_path:
            return

        self._storage_path.mkdir(parents=True, exist_ok=True)
        cache_file = self._storage_path / "semantic_cache.json"

        try:
            data = {
                "entries": [
                    {
                        "key": e.key,
                        "query": e.query,
                        "response": e.response,
                        "embedding": e.embedding,
                        "metadata": e.metadata,
                        "created_at": e.created_at,
                        "last_accessed": e.last_accessed,
                        "access_count": e.access_count
                    }
                    for e in self._entries.values()
                ],
                "saved_at": time.time()
            }

            with open(cache_file, "w") as f:
                json.dump(data, f)

        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    def _hash_query(self, query: str) -> str:
        """Create hash of a query for exact matching."""
        normalized = query.strip().lower()
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding for text."""
        # Try to use local embedding model
        if self._embedding_model is None:
            try:
                # Try sentence-transformers (free, local)
                from sentence_transformers import SentenceTransformer
                self._embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            except ImportError:
                # Fallback to simple TF-IDF-like embedding
                self._embedding_model = "simple"

        if self._embedding_model == "simple":
            return self._simple_embedding(text)

        try:
            embedding = self._embedding_model.encode(text).tolist()
            return embedding
        except Exception as e:
            logger.warning(f"Embedding failed: {e}")
            return self._simple_embedding(text)

    def _simple_embedding(self, text: str) -> List[float]:
        """Simple character-based embedding fallback."""
        # Create a simple hash-based embedding
        embedding = [0.0] * self.config.embedding_dim

        words = text.lower().split()
        for i, word in enumerate(words):
            for j, char in enumerate(word):
                idx = (ord(char) + i * 7 + j * 13) % self.config.embedding_dim
                embedding[idx] += 1.0

        # Normalize
        magnitude = math.sqrt(sum(x * x for x in embedding))
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]

        return embedding

    def _cosine_similarity(
        self,
        a: List[float],
        b: List[float]
    ) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(a) != len(b):
            return 0.0

        dot_product = sum(x * y for x, y in zip(a, b))
        mag_a = math.sqrt(sum(x * x for x in a))
        mag_b = math.sqrt(sum(x * x for x in b))

        if mag_a == 0 or mag_b == 0:
            return 0.0

        return dot_product / (mag_a * mag_b)

    async def get(
        self,
        query: str,
        strategy: Optional[CacheStrategy] = None
    ) -> Optional[Tuple[Any, float]]:
        """
        Get cached response for a query.

        Args:
            query: Query to look up
            strategy: Override cache strategy

        Returns:
            Tuple of (response, similarity_score) or None
        """
        strategy = strategy or self.config.strategy

        # Check exact match first
        if strategy in [CacheStrategy.EXACT, CacheStrategy.HYBRID]:
            query_hash = self._hash_query(query)
            if query_hash in self._exact_index:
                key = self._exact_index[query_hash]
                entry = self._entries.get(key)

                if entry and self._is_valid(entry):
                    self._update_access(entry)
                    self._stats["hits"] += 1
                    self._stats["exact_hits"] += 1
                    return entry.response, 1.0

        # Semantic search
        if strategy in [CacheStrategy.SEMANTIC, CacheStrategy.HYBRID]:
            query_embedding = await self._get_embedding(query)

            if query_embedding:
                best_match = None
                best_score = 0.0

                for key, embedding in self._embeddings.items():
                    score = self._cosine_similarity(query_embedding, embedding)

                    if score > best_score and score >= self.config.similarity_threshold:
                        entry = self._entries.get(key)
                        if entry and self._is_valid(entry):
                            best_match = entry
                            best_score = score

                if best_match:
                    self._update_access(best_match)
                    self._stats["hits"] += 1
                    self._stats["semantic_hits"] += 1
                    return best_match.response, best_score

        self._stats["misses"] += 1
        return None

    async def set(
        self,
        query: str,
        response: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Cache a response.

        Args:
            query: Query that generated the response
            response: Response to cache
            metadata: Optional metadata

        Returns:
            Cache entry key
        """
        # Evict if needed
        if len(self._entries) >= self.config.max_entries:
            self._evict()

        # Create entry
        key = hashlib.sha256(f"{query}:{time.time()}".encode()).hexdigest()[:16]
        embedding = await self._get_embedding(query)

        entry = CacheEntry(
            key=key,
            query=query,
            response=response,
            embedding=embedding,
            metadata=metadata or {},
            created_at=time.time(),
            last_accessed=time.time()
        )

        self._entries[key] = entry

        if embedding:
            self._embeddings[key] = embedding

        # Index for exact match
        query_hash = self._hash_query(query)
        self._exact_index[query_hash] = key

        # Persist periodically
        if len(self._entries) % 100 == 0:
            self._save()

        return key

    def _is_valid(self, entry: CacheEntry) -> bool:
        """Check if entry is still valid (not expired)."""
        if self.config.ttl_seconds <= 0:
            return True

        age = time.time() - entry.created_at
        return age < self.config.ttl_seconds

    def _update_access(self, entry: CacheEntry) -> None:
        """Update access time and count."""
        entry.last_accessed = time.time()
        entry.access_count += 1

    def _evict(self) -> None:
        """Evict entries to make room."""
        if not self._entries:
            return

        # Remove expired entries first
        expired = [
            key for key, entry in self._entries.items()
            if not self._is_valid(entry)
        ]

        for key in expired:
            self._remove(key)

        # If still over limit, use LRU
        while len(self._entries) >= self.config.max_entries:
            # Find least recently used
            lru_key = min(
                self._entries.keys(),
                key=lambda k: self._entries[k].last_accessed
            )
            self._remove(lru_key)

    def _remove(self, key: str) -> None:
        """Remove an entry."""
        if key in self._entries:
            entry = self._entries[key]
            query_hash = self._hash_query(entry.query)

            del self._entries[key]
            self._embeddings.pop(key, None)
            self._exact_index.pop(query_hash, None)

    def invalidate(self, pattern: Optional[str] = None) -> int:
        """
        Invalidate cache entries.

        Args:
            pattern: Optional pattern to match queries (None = all)

        Returns:
            Number of entries invalidated
        """
        if pattern is None:
            count = len(self._entries)
            self._entries.clear()
            self._embeddings.clear()
            self._exact_index.clear()
            return count

        to_remove = [
            key for key, entry in self._entries.items()
            if pattern in entry.query
        ]

        for key in to_remove:
            self._remove(key)

        return len(to_remove)

    async def find_similar(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Tuple[CacheEntry, float]]:
        """
        Find similar cached queries.

        Args:
            query: Query to search for
            top_k: Number of results

        Returns:
            List of (entry, similarity_score) tuples
        """
        query_embedding = await self._get_embedding(query)
        if not query_embedding:
            return []

        results = []

        for key, embedding in self._embeddings.items():
            score = self._cosine_similarity(query_embedding, embedding)
            entry = self._entries.get(key)

            if entry and self._is_valid(entry):
                results.append((entry, score))

        # Sort by score
        results.sort(key=lambda x: x[1], reverse=True)

        return results[:top_k]

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total if total > 0 else 0

        return {
            "total_entries": len(self._entries),
            "total_requests": total,
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": hit_rate,
            "exact_hits": self._stats["exact_hits"],
            "semantic_hits": self._stats["semantic_hits"]
        }

    def clear_stats(self) -> None:
        """Clear statistics."""
        self._stats = {
            "hits": 0,
            "misses": 0,
            "semantic_hits": 0,
            "exact_hits": 0
        }

    def save(self) -> None:
        """Force save to disk."""
        self._save()


# Global instance
_semantic_cache: Optional[SemanticCache] = None


def get_semantic_cache(
    config: Optional[CacheConfig] = None,
    storage_path: Optional[str] = None
) -> SemanticCache:
    """Get or create semantic cache instance."""
    global _semantic_cache
    if _semantic_cache is None or config is not None:
        _semantic_cache = SemanticCache(config, storage_path)
    return _semantic_cache
