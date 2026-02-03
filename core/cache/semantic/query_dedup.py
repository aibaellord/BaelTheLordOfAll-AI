"""
BAEL - Query Deduplicator
Deduplicates similar queries to avoid redundant LLM calls.
"""

import asyncio
import hashlib
import logging
import math
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.Cache.Dedup")


@dataclass
class PendingQuery:
    """A query being processed."""
    query: str
    normalized: str
    future: asyncio.Future
    timestamp: float


@dataclass
class DedupConfig:
    """Deduplication configuration."""
    similarity_threshold: float = 0.9
    pending_timeout: float = 30.0
    max_pending: int = 100
    use_semantic: bool = True


class QueryDeduplicator:
    """
    Deduplicates similar queries.

    Features:
    - Exact match deduplication
    - Semantic similarity deduplication
    - Coalescing of concurrent queries
    - Query normalization
    """

    def __init__(self, config: Optional[DedupConfig] = None):
        self.config = config or DedupConfig()

        self._pending: Dict[str, PendingQuery] = {}
        self._embedding_cache = None

        self._stats = {
            "total_queries": 0,
            "deduplicated": 0,
            "exact_dedup": 0,
            "semantic_dedup": 0
        }

    def _normalize_query(self, query: str) -> str:
        """Normalize a query for comparison."""
        # Basic normalization
        normalized = query.strip().lower()

        # Remove extra whitespace
        normalized = " ".join(normalized.split())

        # Remove common variations
        for phrase in ["please", "can you", "could you", "i want to", "help me"]:
            normalized = normalized.replace(phrase, "")

        return normalized.strip()

    def _hash_query(self, normalized: str) -> str:
        """Create hash of normalized query."""
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding for semantic comparison."""
        if not self.config.use_semantic:
            return None

        if self._embedding_cache is None:
            try:
                from .embedding_cache import get_embedding_cache
                self._embedding_cache = get_embedding_cache()
            except ImportError:
                return None

        return await self._embedding_cache.get(text)

    def _cosine_similarity(
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

    async def check_duplicate(
        self,
        query: str
    ) -> Tuple[bool, Optional[asyncio.Future], Optional[str]]:
        """
        Check if a query is a duplicate of a pending query.

        Args:
            query: Query to check

        Returns:
            Tuple of (is_duplicate, future_to_wait, matched_key)
        """
        self._stats["total_queries"] += 1

        normalized = self._normalize_query(query)
        query_hash = self._hash_query(normalized)

        # Clean up expired pending queries
        self._cleanup_expired()

        # Check exact match
        if query_hash in self._pending:
            pending = self._pending[query_hash]
            self._stats["deduplicated"] += 1
            self._stats["exact_dedup"] += 1
            return True, pending.future, query_hash

        # Check semantic similarity
        if self.config.use_semantic and self._pending:
            query_embedding = await self._get_embedding(normalized)

            if query_embedding:
                for key, pending in self._pending.items():
                    pending_embedding = await self._get_embedding(pending.normalized)

                    if pending_embedding:
                        similarity = self._cosine_similarity(
                            query_embedding,
                            pending_embedding
                        )

                        if similarity >= self.config.similarity_threshold:
                            self._stats["deduplicated"] += 1
                            self._stats["semantic_dedup"] += 1
                            return True, pending.future, key

        return False, None, None

    async def register_query(
        self,
        query: str
    ) -> Tuple[str, asyncio.Future]:
        """
        Register a new query as pending.

        Args:
            query: Query being processed

        Returns:
            Tuple of (query_key, future)
        """
        normalized = self._normalize_query(query)
        query_hash = self._hash_query(normalized)

        # Limit pending queries
        if len(self._pending) >= self.config.max_pending:
            self._cleanup_oldest()

        future = asyncio.get_event_loop().create_future()

        self._pending[query_hash] = PendingQuery(
            query=query,
            normalized=normalized,
            future=future,
            timestamp=time.time()
        )

        return query_hash, future

    def complete_query(
        self,
        query_key: str,
        result: Any
    ) -> None:
        """
        Mark a query as complete with result.

        Args:
            query_key: Key from register_query
            result: Query result
        """
        if query_key in self._pending:
            pending = self._pending[query_key]

            if not pending.future.done():
                pending.future.set_result(result)

            del self._pending[query_key]

    def fail_query(
        self,
        query_key: str,
        error: Exception
    ) -> None:
        """
        Mark a query as failed.

        Args:
            query_key: Key from register_query
            error: Error that occurred
        """
        if query_key in self._pending:
            pending = self._pending[query_key]

            if not pending.future.done():
                pending.future.set_exception(error)

            del self._pending[query_key]

    def _cleanup_expired(self) -> None:
        """Remove expired pending queries."""
        now = time.time()
        expired = [
            key for key, pending in self._pending.items()
            if now - pending.timestamp > self.config.pending_timeout
        ]

        for key in expired:
            pending = self._pending[key]
            if not pending.future.done():
                pending.future.set_exception(
                    TimeoutError("Query processing timeout")
                )
            del self._pending[key]

    def _cleanup_oldest(self, count: int = 10) -> None:
        """Remove oldest pending queries."""
        if len(self._pending) <= count:
            return

        sorted_keys = sorted(
            self._pending.keys(),
            key=lambda k: self._pending[k].timestamp
        )

        for key in sorted_keys[:count]:
            pending = self._pending[key]
            if not pending.future.done():
                pending.future.cancel()
            del self._pending[key]

    async def deduplicate_and_execute(
        self,
        query: str,
        executor: callable
    ) -> Any:
        """
        Deduplicate query and execute if not duplicate.

        Args:
            query: Query to process
            executor: Async function to execute query

        Returns:
            Query result
        """
        # Check for duplicate
        is_dup, future, _ = await self.check_duplicate(query)

        if is_dup and future:
            # Wait for existing query
            return await future

        # Register and execute
        query_key, future = await self.register_query(query)

        try:
            result = await executor(query)
            self.complete_query(query_key, result)
            return result
        except Exception as e:
            self.fail_query(query_key, e)
            raise

    def get_stats(self) -> Dict[str, Any]:
        """Get deduplication statistics."""
        total = self._stats["total_queries"]
        dedup_rate = self._stats["deduplicated"] / total if total > 0 else 0

        return {
            "total_queries": total,
            "deduplicated": self._stats["deduplicated"],
            "dedup_rate": dedup_rate,
            "exact_dedup": self._stats["exact_dedup"],
            "semantic_dedup": self._stats["semantic_dedup"],
            "pending_queries": len(self._pending)
        }

    def clear_pending(self) -> int:
        """Clear all pending queries."""
        count = len(self._pending)

        for pending in self._pending.values():
            if not pending.future.done():
                pending.future.cancel()

        self._pending.clear()
        return count


# Global instance
_query_dedup: Optional[QueryDeduplicator] = None


def get_query_dedup(
    config: Optional[DedupConfig] = None
) -> QueryDeduplicator:
    """Get or create query deduplicator instance."""
    global _query_dedup
    if _query_dedup is None:
        _query_dedup = QueryDeduplicator(config)
    return _query_dedup
