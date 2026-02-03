#!/usr/bin/env python3
"""
BAEL - Embedding Manager
Advanced vector embedding management for AI agents.

Features:
- Text embedding (simplified)
- Embedding storage
- Similarity search
- Embedding aggregation
- Dimension reduction
"""

import asyncio
import hashlib
import math
import random
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class EmbeddingType(Enum):
    """Types of embeddings."""
    TEXT = "text"
    TOKEN = "token"
    SENTENCE = "sentence"
    DOCUMENT = "document"
    ENTITY = "entity"
    CONCEPT = "concept"


class PoolingStrategy(Enum):
    """Pooling strategies for aggregation."""
    MEAN = "mean"
    MAX = "max"
    MIN = "min"
    CLS = "cls"
    ATTENTION = "attention"


class SimilarityMetric(Enum):
    """Similarity metrics."""
    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    DOT_PRODUCT = "dot_product"
    MANHATTAN = "manhattan"


class NormalizationType(Enum):
    """Normalization types."""
    L2 = "l2"
    L1 = "l1"
    MINMAX = "minmax"
    NONE = "none"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Embedding:
    """A vector embedding."""
    embedding_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    vector: List[float] = field(default_factory=list)
    source_text: str = ""
    embedding_type: EmbeddingType = EmbeddingType.TEXT
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class EmbeddingMatch:
    """A similarity match result."""
    embedding: Embedding
    score: float
    rank: int


@dataclass
class EmbeddingSearchResult:
    """Search result for embeddings."""
    query_embedding: Embedding
    matches: List[EmbeddingMatch] = field(default_factory=list)
    metric: SimilarityMetric = SimilarityMetric.COSINE


@dataclass
class AggregatedEmbedding:
    """Aggregated embedding from multiple sources."""
    embedding_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    vector: List[float] = field(default_factory=list)
    source_ids: List[str] = field(default_factory=list)
    strategy: PoolingStrategy = PoolingStrategy.MEAN


@dataclass
class EmbeddingCluster:
    """A cluster of similar embeddings."""
    cluster_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    centroid: List[float] = field(default_factory=list)
    member_ids: List[str] = field(default_factory=list)
    avg_similarity: float = 0.0


# =============================================================================
# EMBEDDING STORE
# =============================================================================

class EmbeddingStore:
    """Store for embeddings with indexing."""

    def __init__(self):
        self._embeddings: Dict[str, Embedding] = {}
        self._type_index: Dict[EmbeddingType, Set[str]] = defaultdict(set)
        self._text_index: Dict[str, str] = {}

    def add(self, embedding: Embedding) -> None:
        """Add an embedding."""
        self._embeddings[embedding.embedding_id] = embedding
        self._type_index[embedding.embedding_type].add(embedding.embedding_id)

        if embedding.source_text:
            text_hash = hashlib.md5(embedding.source_text.encode()).hexdigest()
            self._text_index[text_hash] = embedding.embedding_id

    def get(self, embedding_id: str) -> Optional[Embedding]:
        """Get an embedding by ID."""
        return self._embeddings.get(embedding_id)

    def get_by_text(self, text: str) -> Optional[Embedding]:
        """Get embedding by source text."""
        text_hash = hashlib.md5(text.encode()).hexdigest()
        emb_id = self._text_index.get(text_hash)
        return self._embeddings.get(emb_id) if emb_id else None

    def get_by_type(self, emb_type: EmbeddingType) -> List[Embedding]:
        """Get embeddings by type."""
        ids = self._type_index.get(emb_type, set())
        return [self._embeddings[eid] for eid in ids if eid in self._embeddings]

    def all_embeddings(self) -> List[Embedding]:
        """Get all embeddings."""
        return list(self._embeddings.values())

    def remove(self, embedding_id: str) -> bool:
        """Remove an embedding."""
        if embedding_id not in self._embeddings:
            return False

        emb = self._embeddings[embedding_id]
        del self._embeddings[embedding_id]

        self._type_index[emb.embedding_type].discard(embedding_id)

        if emb.source_text:
            text_hash = hashlib.md5(emb.source_text.encode()).hexdigest()
            self._text_index.pop(text_hash, None)

        return True

    def count(self) -> int:
        """Count embeddings."""
        return len(self._embeddings)


# =============================================================================
# TEXT EMBEDDER (Simplified)
# =============================================================================

class SimpleTextEmbedder:
    """Simple text embedder using character-level features."""

    def __init__(self, dim: int = 128):
        self._dim = dim
        self._char_vectors: Dict[str, List[float]] = {}
        self._init_char_vectors()

    def _init_char_vectors(self) -> None:
        """Initialize character vectors."""
        chars = "abcdefghijklmnopqrstuvwxyz0123456789 .,!?"
        for char in chars:
            random.seed(ord(char))
            self._char_vectors[char] = [
                random.gauss(0, 0.1) for _ in range(self._dim)
            ]
        random.seed()

    def _normalize_l2(self, vector: List[float]) -> List[float]:
        """L2 normalize a vector."""
        norm = math.sqrt(sum(v ** 2 for v in vector))
        if norm == 0:
            return vector.copy()
        return [v / norm for v in vector]

    def embed(self, text: str) -> Embedding:
        """Embed a text string."""
        text = text.lower()

        embedding = [0.0] * self._dim
        count = 0

        for char in text:
            if char in self._char_vectors:
                for i, v in enumerate(self._char_vectors[char]):
                    embedding[i] += v
                count += 1

        if count > 0:
            embedding = [v / count for v in embedding]

        embedding = self._normalize_l2(embedding)

        return Embedding(
            vector=embedding,
            source_text=text,
            embedding_type=EmbeddingType.TEXT
        )

    def embed_batch(self, texts: List[str]) -> List[Embedding]:
        """Embed multiple texts."""
        return [self.embed(text) for text in texts]


# =============================================================================
# SIMILARITY CALCULATOR
# =============================================================================

class SimilarityCalculator:
    """Calculate similarity between embeddings."""

    def cosine(self, v1: List[float], v2: List[float]) -> float:
        """Calculate cosine similarity."""
        if len(v1) != len(v2):
            return 0.0

        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a ** 2 for a in v1))
        norm2 = math.sqrt(sum(b ** 2 for b in v2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot / (norm1 * norm2)

    def euclidean(self, v1: List[float], v2: List[float]) -> float:
        """Calculate euclidean distance (converted to similarity)."""
        if len(v1) != len(v2):
            return 0.0

        dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2)))
        return 1.0 / (1.0 + dist)

    def dot_product(self, v1: List[float], v2: List[float]) -> float:
        """Calculate dot product."""
        if len(v1) != len(v2):
            return 0.0
        return sum(a * b for a, b in zip(v1, v2))

    def manhattan(self, v1: List[float], v2: List[float]) -> float:
        """Calculate manhattan distance (converted to similarity)."""
        if len(v1) != len(v2):
            return 0.0

        dist = sum(abs(a - b) for a, b in zip(v1, v2))
        return 1.0 / (1.0 + dist)

    def calculate(
        self,
        v1: List[float],
        v2: List[float],
        metric: SimilarityMetric = SimilarityMetric.COSINE
    ) -> float:
        """Calculate similarity using specified metric."""
        if metric == SimilarityMetric.COSINE:
            return self.cosine(v1, v2)
        elif metric == SimilarityMetric.EUCLIDEAN:
            return self.euclidean(v1, v2)
        elif metric == SimilarityMetric.DOT_PRODUCT:
            return self.dot_product(v1, v2)
        elif metric == SimilarityMetric.MANHATTAN:
            return self.manhattan(v1, v2)
        return 0.0


# =============================================================================
# EMBEDDING AGGREGATOR
# =============================================================================

class EmbeddingAggregator:
    """Aggregate multiple embeddings."""

    def mean_pool(self, embeddings: List[List[float]]) -> List[float]:
        """Mean pooling of embeddings."""
        if not embeddings:
            return []

        dim = len(embeddings[0])
        result = [0.0] * dim

        for emb in embeddings:
            for i, v in enumerate(emb):
                result[i] += v

        n = len(embeddings)
        return [v / n for v in result]

    def max_pool(self, embeddings: List[List[float]]) -> List[float]:
        """Max pooling of embeddings."""
        if not embeddings:
            return []

        dim = len(embeddings[0])
        result = [float('-inf')] * dim

        for emb in embeddings:
            for i, v in enumerate(emb):
                result[i] = max(result[i], v)

        return result

    def min_pool(self, embeddings: List[List[float]]) -> List[float]:
        """Min pooling of embeddings."""
        if not embeddings:
            return []

        dim = len(embeddings[0])
        result = [float('inf')] * dim

        for emb in embeddings:
            for i, v in enumerate(emb):
                result[i] = min(result[i], v)

        return result

    def attention_pool(
        self,
        embeddings: List[List[float]],
        weights: List[float]
    ) -> List[float]:
        """Attention-weighted pooling."""
        if not embeddings or len(embeddings) != len(weights):
            return []

        total_weight = sum(weights)
        if total_weight == 0:
            return self.mean_pool(embeddings)

        norm_weights = [w / total_weight for w in weights]

        dim = len(embeddings[0])
        result = [0.0] * dim

        for emb, weight in zip(embeddings, norm_weights):
            for i, v in enumerate(emb):
                result[i] += v * weight

        return result

    def aggregate(
        self,
        embeddings: List[Embedding],
        strategy: PoolingStrategy = PoolingStrategy.MEAN
    ) -> AggregatedEmbedding:
        """Aggregate embeddings using strategy."""
        vectors = [emb.vector for emb in embeddings]

        if strategy == PoolingStrategy.MEAN:
            result = self.mean_pool(vectors)
        elif strategy == PoolingStrategy.MAX:
            result = self.max_pool(vectors)
        elif strategy == PoolingStrategy.MIN:
            result = self.min_pool(vectors)
        elif strategy == PoolingStrategy.CLS:
            result = vectors[0] if vectors else []
        else:
            result = self.mean_pool(vectors)

        return AggregatedEmbedding(
            vector=result,
            source_ids=[emb.embedding_id for emb in embeddings],
            strategy=strategy
        )


# =============================================================================
# EMBEDDING NORMALIZER
# =============================================================================

class EmbeddingNormalizer:
    """Normalize embeddings."""

    def l2_normalize(self, vector: List[float]) -> List[float]:
        """L2 normalize."""
        norm = math.sqrt(sum(v ** 2 for v in vector))
        if norm == 0:
            return vector.copy()
        return [v / norm for v in vector]

    def l1_normalize(self, vector: List[float]) -> List[float]:
        """L1 normalize."""
        total = sum(abs(v) for v in vector)
        if total == 0:
            return vector.copy()
        return [v / total for v in vector]

    def minmax_normalize(
        self,
        vector: List[float],
        min_val: Optional[float] = None,
        max_val: Optional[float] = None
    ) -> List[float]:
        """Min-max normalize."""
        if not vector:
            return []

        if min_val is None:
            min_val = min(vector)
        if max_val is None:
            max_val = max(vector)

        range_val = max_val - min_val
        if range_val == 0:
            return [0.5] * len(vector)

        return [(v - min_val) / range_val for v in vector]

    def normalize(
        self,
        embedding: Embedding,
        norm_type: NormalizationType = NormalizationType.L2
    ) -> Embedding:
        """Normalize an embedding."""
        if norm_type == NormalizationType.L2:
            normalized = self.l2_normalize(embedding.vector)
        elif norm_type == NormalizationType.L1:
            normalized = self.l1_normalize(embedding.vector)
        elif norm_type == NormalizationType.MINMAX:
            normalized = self.minmax_normalize(embedding.vector)
        else:
            normalized = embedding.vector.copy()

        return Embedding(
            embedding_id=embedding.embedding_id,
            vector=normalized,
            source_text=embedding.source_text,
            embedding_type=embedding.embedding_type,
            metadata=embedding.metadata,
            created_at=embedding.created_at
        )


# =============================================================================
# EMBEDDING MANAGER
# =============================================================================

class EmbeddingManager:
    """
    Embedding Manager for BAEL.

    Advanced vector embedding management for AI agents.
    """

    def __init__(self, dim: int = 128):
        self._dim = dim
        self._store = EmbeddingStore()
        self._embedder = SimpleTextEmbedder(dim)
        self._similarity = SimilarityCalculator()
        self._aggregator = EmbeddingAggregator()
        self._normalizer = EmbeddingNormalizer()

    # -------------------------------------------------------------------------
    # EMBEDDING CREATION
    # -------------------------------------------------------------------------

    def embed_text(self, text: str) -> Embedding:
        """Embed a text string."""
        cached = self._store.get_by_text(text)
        if cached:
            return cached

        embedding = self._embedder.embed(text)
        self._store.add(embedding)
        return embedding

    def embed_texts(self, texts: List[str]) -> List[Embedding]:
        """Embed multiple texts."""
        return [self.embed_text(text) for text in texts]

    def create_embedding(
        self,
        vector: List[float],
        source_text: str = "",
        emb_type: EmbeddingType = EmbeddingType.TEXT,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Embedding:
        """Create embedding from vector."""
        embedding = Embedding(
            vector=vector,
            source_text=source_text,
            embedding_type=emb_type,
            metadata=metadata or {}
        )
        self._store.add(embedding)
        return embedding

    # -------------------------------------------------------------------------
    # SEARCH
    # -------------------------------------------------------------------------

    def search(
        self,
        query: str,
        top_k: int = 5,
        metric: SimilarityMetric = SimilarityMetric.COSINE
    ) -> EmbeddingSearchResult:
        """Search for similar embeddings."""
        query_emb = self._embedder.embed(query)
        return self.search_by_embedding(query_emb, top_k, metric)

    def search_by_embedding(
        self,
        query_embedding: Embedding,
        top_k: int = 5,
        metric: SimilarityMetric = SimilarityMetric.COSINE
    ) -> EmbeddingSearchResult:
        """Search using embedding."""
        all_embeddings = self._store.all_embeddings()

        scores = []
        for emb in all_embeddings:
            if emb.embedding_id == query_embedding.embedding_id:
                continue
            score = self._similarity.calculate(
                query_embedding.vector,
                emb.vector,
                metric
            )
            scores.append((emb, score))

        scores.sort(key=lambda x: x[1], reverse=True)

        matches = [
            EmbeddingMatch(embedding=emb, score=score, rank=i + 1)
            for i, (emb, score) in enumerate(scores[:top_k])
        ]

        return EmbeddingSearchResult(
            query_embedding=query_embedding,
            matches=matches,
            metric=metric
        )

    # -------------------------------------------------------------------------
    # AGGREGATION
    # -------------------------------------------------------------------------

    def aggregate(
        self,
        embedding_ids: List[str],
        strategy: PoolingStrategy = PoolingStrategy.MEAN
    ) -> AggregatedEmbedding:
        """Aggregate embeddings."""
        embeddings = [
            self._store.get(eid) for eid in embedding_ids
            if self._store.get(eid)
        ]
        return self._aggregator.aggregate(embeddings, strategy)

    def aggregate_texts(
        self,
        texts: List[str],
        strategy: PoolingStrategy = PoolingStrategy.MEAN
    ) -> AggregatedEmbedding:
        """Embed and aggregate texts."""
        embeddings = self.embed_texts(texts)
        return self._aggregator.aggregate(embeddings, strategy)

    # -------------------------------------------------------------------------
    # NORMALIZATION
    # -------------------------------------------------------------------------

    def normalize(
        self,
        embedding_id: str,
        norm_type: NormalizationType = NormalizationType.L2
    ) -> Optional[Embedding]:
        """Normalize an embedding."""
        embedding = self._store.get(embedding_id)
        if not embedding:
            return None
        return self._normalizer.normalize(embedding, norm_type)

    # -------------------------------------------------------------------------
    # SIMILARITY
    # -------------------------------------------------------------------------

    def similarity(
        self,
        text1: str,
        text2: str,
        metric: SimilarityMetric = SimilarityMetric.COSINE
    ) -> float:
        """Calculate similarity between texts."""
        emb1 = self.embed_text(text1)
        emb2 = self.embed_text(text2)
        return self._similarity.calculate(emb1.vector, emb2.vector, metric)

    def pairwise_similarity(
        self,
        texts: List[str],
        metric: SimilarityMetric = SimilarityMetric.COSINE
    ) -> List[List[float]]:
        """Calculate pairwise similarities."""
        embeddings = self.embed_texts(texts)

        n = len(embeddings)
        matrix = [[0.0] * n for _ in range(n)]

        for i in range(n):
            for j in range(n):
                if i == j:
                    matrix[i][j] = 1.0
                elif i < j:
                    sim = self._similarity.calculate(
                        embeddings[i].vector,
                        embeddings[j].vector,
                        metric
                    )
                    matrix[i][j] = sim
                    matrix[j][i] = sim

        return matrix

    # -------------------------------------------------------------------------
    # STORAGE
    # -------------------------------------------------------------------------

    def get(self, embedding_id: str) -> Optional[Embedding]:
        """Get embedding by ID."""
        return self._store.get(embedding_id)

    def count(self) -> int:
        """Count embeddings."""
        return self._store.count()

    def get_by_type(self, emb_type: EmbeddingType) -> List[Embedding]:
        """Get embeddings by type."""
        return self._store.get_by_type(emb_type)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Embedding Manager."""
    print("=" * 70)
    print("BAEL - EMBEDDING MANAGER DEMO")
    print("Advanced Vector Embedding Management for AI Agents")
    print("=" * 70)
    print()

    manager = EmbeddingManager(dim=64)

    # 1. Text Embedding
    print("1. TEXT EMBEDDING:")
    print("-" * 40)

    texts = [
        "The quick brown fox jumps over the lazy dog",
        "A fast dark fox leaps across a sleepy hound",
        "Python is a programming language",
        "JavaScript runs in web browsers",
        "Machine learning uses neural networks"
    ]

    for text in texts:
        emb = manager.embed_text(text)
        print(f"   Embedded: '{text[:40]}...'")
        print(f"      ID: {emb.embedding_id[:8]}...")
        print(f"      Dim: {len(emb.vector)}")
    print()

    # 2. Similarity Search
    print("2. SIMILARITY SEARCH:")
    print("-" * 40)

    query = "A quick fox jumping"
    result = manager.search(query, top_k=3)

    print(f"   Query: '{query}'")
    print(f"   Top matches:")
    for match in result.matches:
        print(f"      {match.rank}. '{match.embedding.source_text[:40]}...' (score: {match.score:.3f})")
    print()

    # 3. Pairwise Similarity
    print("3. PAIRWISE SIMILARITY:")
    print("-" * 40)

    test_texts = texts[:3]
    matrix = manager.pairwise_similarity(test_texts)

    print("   Similarity matrix:")
    for i, row in enumerate(matrix):
        print(f"      {i}: {[f'{s:.2f}' for s in row]}")
    print()

    # 4. Text Aggregation
    print("4. TEXT AGGREGATION:")
    print("-" * 40)

    related_texts = [
        "cats are cute pets",
        "dogs are loyal friends",
        "rabbits are fluffy animals"
    ]

    agg = manager.aggregate_texts(related_texts, PoolingStrategy.MEAN)
    print(f"   Aggregated {len(related_texts)} texts")
    print(f"   Strategy: {agg.strategy.value}")
    print(f"   Result dim: {len(agg.vector)}")
    print()

    # 5. Different Metrics
    print("5. DIFFERENT SIMILARITY METRICS:")
    print("-" * 40)

    text_a = "Hello world"
    text_b = "Hello there"

    for metric in SimilarityMetric:
        sim = manager.similarity(text_a, text_b, metric)
        print(f"   {metric.value}: {sim:.4f}")
    print()

    # 6. Normalization
    print("6. NORMALIZATION:")
    print("-" * 40)

    emb = manager.embed_text("test normalization")

    for norm_type in NormalizationType:
        if norm_type != NormalizationType.NONE:
            normalized = manager.normalize(emb.embedding_id, norm_type)
            if normalized:
                vec = normalized.vector
                if norm_type == NormalizationType.L2:
                    norm = math.sqrt(sum(v ** 2 for v in vec))
                elif norm_type == NormalizationType.L1:
                    norm = sum(abs(v) for v in vec)
                else:
                    norm = max(vec) - min(vec) if vec else 0
                print(f"   {norm_type.value}: norm = {norm:.4f}")
    print()

    # 7. Statistics
    print("7. STATISTICS:")
    print("-" * 40)
    print(f"   Total embeddings: {manager.count()}")
    print(f"   Embedding dimension: {manager._dim}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Embedding Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
