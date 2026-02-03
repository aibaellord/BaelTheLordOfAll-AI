"""
BAEL - Semantic Caching System
Intelligent caching with semantic similarity matching.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("BAEL.Cache.Semantic")


class CacheStrategy(Enum):
    """Caching strategies."""
    EXACT = "exact"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"
    FUZZY = "fuzzy"


class SimilarityMetric(Enum):
    """Similarity metrics."""
    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    JACCARD = "jaccard"
    LEVENSHTEIN = "levenshtein"


@dataclass
class CacheEntry:
    """A semantic cache entry."""
    key: str
    query: str
    response: Any
    embedding: Optional[List[float]]
    metadata: Dict[str, Any]
    created_at: float
    last_accessed: float
    access_count: int = 0
    similarity_score: float = 1.0


@dataclass
class CacheConfig:
    """Semantic cache configuration."""
    max_entries: int = 10000
    similarity_threshold: float = 0.85
    ttl_seconds: float = 3600
    embedding_dim: int = 384
    strategy: CacheStrategy = CacheStrategy.HYBRID


# Lazy imports
def get_semantic_cache():
    """Get the semantic cache."""
    from .semantic_cache import SemanticCache
    return SemanticCache()


def get_embedding_cache():
    """Get the embedding cache."""
    from .embedding_cache import EmbeddingCache
    return EmbeddingCache()


def get_query_dedup():
    """Get the query deduplicator."""
    from .query_dedup import QueryDeduplicator
    return QueryDeduplicator()


__all__ = [
    "CacheStrategy",
    "SimilarityMetric",
    "CacheEntry",
    "CacheConfig",
    "get_semantic_cache",
    "get_embedding_cache",
    "get_query_dedup"
]
