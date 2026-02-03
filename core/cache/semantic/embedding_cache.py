"""
BAEL - Embedding Cache
Caches embeddings for fast similarity lookup.
"""

import asyncio
import json
import logging
import math
import struct
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("BAEL.Cache.Embedding")


@dataclass
class EmbeddingEntry:
    """Cached embedding entry."""
    text_hash: str
    text_preview: str  # First 100 chars
    embedding: List[float]
    created_at: float
    model: str = "default"


class EmbeddingCache:
    """
    Caches embeddings to avoid recomputation.

    Features:
    - Fast hash-based lookup
    - Disk persistence
    - Multiple model support
    - Memory-efficient storage
    """

    def __init__(
        self,
        storage_path: Optional[str] = None,
        max_entries: int = 50000
    ):
        self._storage_path = Path(storage_path) if storage_path else None
        self._max_entries = max_entries

        self._cache: Dict[str, EmbeddingEntry] = {}
        self._embedding_model = None
        self._model_name = "default"

        self._stats = {
            "hits": 0,
            "misses": 0,
            "computations": 0
        }

        self._load()

    def _load(self) -> None:
        """Load embeddings from disk."""
        if not self._storage_path:
            return

        cache_file = self._storage_path / "embedding_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r") as f:
                    data = json.load(f)

                    for entry_data in data.get("entries", []):
                        entry = EmbeddingEntry(
                            text_hash=entry_data["text_hash"],
                            text_preview=entry_data["text_preview"],
                            embedding=entry_data["embedding"],
                            created_at=entry_data["created_at"],
                            model=entry_data.get("model", "default")
                        )
                        self._cache[entry.text_hash] = entry

                    logger.info(f"Loaded {len(self._cache)} cached embeddings")

            except Exception as e:
                logger.warning(f"Failed to load embedding cache: {e}")

    def _save(self) -> None:
        """Save embeddings to disk."""
        if not self._storage_path:
            return

        self._storage_path.mkdir(parents=True, exist_ok=True)
        cache_file = self._storage_path / "embedding_cache.json"

        try:
            data = {
                "entries": [
                    {
                        "text_hash": e.text_hash,
                        "text_preview": e.text_preview,
                        "embedding": e.embedding,
                        "created_at": e.created_at,
                        "model": e.model
                    }
                    for e in self._cache.values()
                ],
                "saved_at": time.time()
            }

            with open(cache_file, "w") as f:
                json.dump(data, f)

        except Exception as e:
            logger.error(f"Failed to save embedding cache: {e}")

    def _hash_text(self, text: str) -> str:
        """Create hash for text."""
        import hashlib
        normalized = text.strip().lower()
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    async def _compute_embedding(self, text: str) -> List[float]:
        """Compute embedding for text."""
        # Try sentence-transformers first (free, local)
        if self._embedding_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                self._model_name = "all-MiniLM-L6-v2"
            except ImportError:
                self._embedding_model = "simple"
                self._model_name = "simple-hash"

        self._stats["computations"] += 1

        if self._embedding_model == "simple":
            return self._simple_embedding(text)

        try:
            embedding = self._embedding_model.encode(text).tolist()
            return embedding
        except Exception as e:
            logger.warning(f"Embedding computation failed: {e}")
            return self._simple_embedding(text)

    def _simple_embedding(self, text: str, dim: int = 384) -> List[float]:
        """Simple fallback embedding."""
        embedding = [0.0] * dim

        words = text.lower().split()
        for i, word in enumerate(words):
            for j, char in enumerate(word):
                idx = (ord(char) + i * 7 + j * 13) % dim
                embedding[idx] += 1.0

        # Normalize
        magnitude = math.sqrt(sum(x * x for x in embedding))
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]

        return embedding

    async def get(self, text: str) -> Optional[List[float]]:
        """
        Get cached embedding or compute new one.

        Args:
            text: Text to get embedding for

        Returns:
            Embedding vector
        """
        text_hash = self._hash_text(text)

        # Check cache
        entry = self._cache.get(text_hash)
        if entry and entry.model == self._model_name:
            self._stats["hits"] += 1
            return entry.embedding

        self._stats["misses"] += 1

        # Compute and cache
        embedding = await self._compute_embedding(text)

        if len(self._cache) >= self._max_entries:
            self._evict()

        self._cache[text_hash] = EmbeddingEntry(
            text_hash=text_hash,
            text_preview=text[:100],
            embedding=embedding,
            created_at=time.time(),
            model=self._model_name
        )

        return embedding

    async def get_batch(
        self,
        texts: List[str]
    ) -> List[List[float]]:
        """
        Get embeddings for multiple texts.

        Args:
            texts: List of texts

        Returns:
            List of embeddings
        """
        results = []
        to_compute = []
        to_compute_indices = []

        # Check cache for each
        for i, text in enumerate(texts):
            text_hash = self._hash_text(text)
            entry = self._cache.get(text_hash)

            if entry and entry.model == self._model_name:
                results.append(entry.embedding)
                self._stats["hits"] += 1
            else:
                results.append(None)
                to_compute.append(text)
                to_compute_indices.append(i)
                self._stats["misses"] += 1

        # Batch compute missing embeddings
        if to_compute:
            if self._embedding_model not in [None, "simple"]:
                try:
                    computed = self._embedding_model.encode(to_compute).tolist()
                    self._stats["computations"] += len(to_compute)
                except Exception:
                    computed = [self._simple_embedding(t) for t in to_compute]
                    self._stats["computations"] += len(to_compute)
            else:
                computed = [await self._compute_embedding(t) for t in to_compute]

            # Cache and insert results
            for i, embedding in zip(to_compute_indices, computed):
                text = texts[i]
                text_hash = self._hash_text(text)

                self._cache[text_hash] = EmbeddingEntry(
                    text_hash=text_hash,
                    text_preview=text[:100],
                    embedding=embedding,
                    created_at=time.time(),
                    model=self._model_name
                )

                results[i] = embedding

        return results

    def _evict(self, count: int = 1000) -> None:
        """Evict oldest entries."""
        if len(self._cache) <= count:
            return

        # Sort by creation time
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda x: x[1].created_at
        )

        # Remove oldest
        for key, _ in sorted_entries[:count]:
            del self._cache[key]

    def cosine_similarity(
        self,
        a: List[float],
        b: List[float]
    ) -> float:
        """Calculate cosine similarity."""
        if len(a) != len(b):
            return 0.0

        dot = sum(x * y for x, y in zip(a, b))
        mag_a = math.sqrt(sum(x * x for x in a))
        mag_b = math.sqrt(sum(x * x for x in b))

        if mag_a == 0 or mag_b == 0:
            return 0.0

        return dot / (mag_a * mag_b)

    async def find_similar(
        self,
        text: str,
        top_k: int = 5,
        threshold: float = 0.7
    ) -> List[Tuple[str, float]]:
        """
        Find similar texts in cache.

        Args:
            text: Query text
            top_k: Number of results
            threshold: Minimum similarity

        Returns:
            List of (text_preview, similarity) tuples
        """
        query_embedding = await self.get(text)

        results = []
        for entry in self._cache.values():
            if entry.text_preview == text[:100]:
                continue

            sim = self.cosine_similarity(query_embedding, entry.embedding)
            if sim >= threshold:
                results.append((entry.text_preview, sim))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total if total > 0 else 0

        return {
            "cached_embeddings": len(self._cache),
            "total_requests": total,
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": hit_rate,
            "computations": self._stats["computations"],
            "model": self._model_name
        }

    def save(self) -> None:
        """Force save to disk."""
        self._save()

    def clear(self) -> None:
        """Clear all cached embeddings."""
        self._cache.clear()


# Global instance
_embedding_cache: Optional[EmbeddingCache] = None


def get_embedding_cache(
    storage_path: Optional[str] = None,
    max_entries: int = 50000
) -> EmbeddingCache:
    """Get or create embedding cache instance."""
    global _embedding_cache
    if _embedding_cache is None:
        _embedding_cache = EmbeddingCache(storage_path, max_entries)
    return _embedding_cache
