#!/usr/bin/env python3
"""
BAEL - Embedding Manager
Advanced embedding generation and management system.

Features:
- Multiple embedding providers (simulated)
- Caching and batch processing
- Dimensionality reduction
- Embedding comparison and analysis
- Pooling strategies
- Chunking support
- Async operations
- Provider fallback
- Cost tracking
"""

import asyncio
import hashlib
import logging
import math
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Awaitable, Callable, Dict, Generic, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)


T = TypeVar('T')
Vector = List[float]


# =============================================================================
# ENUMS
# =============================================================================

class EmbeddingProvider(Enum):
    """Embedding providers."""
    LOCAL = "local"
    OPENAI = "openai"
    COHERE = "cohere"
    HUGGINGFACE = "huggingface"
    SENTENCE_TRANSFORMERS = "sentence_transformers"


class PoolingStrategy(Enum):
    """Pooling strategies for token embeddings."""
    MEAN = "mean"
    MAX = "max"
    CLS = "cls"
    LAST = "last"
    WEIGHTED = "weighted"


class ChunkingStrategy(Enum):
    """Text chunking strategies."""
    FIXED = "fixed"
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    SEMANTIC = "semantic"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class EmbeddingConfig:
    """Embedding configuration."""
    provider: EmbeddingProvider = EmbeddingProvider.LOCAL
    model: str = "all-MiniLM-L6-v2"
    dimension: int = 384
    max_tokens: int = 512
    batch_size: int = 32
    normalize: bool = True
    pooling: PoolingStrategy = PoolingStrategy.MEAN


@dataclass
class EmbeddingResult:
    """Result of embedding generation."""
    id: str
    text: str
    embedding: Vector
    model: str
    dimension: int
    tokens_used: int = 0
    processing_time: float = 0.0
    from_cache: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchResult:
    """Result of batch embedding."""
    embeddings: List[EmbeddingResult]
    total_tokens: int = 0
    total_time: float = 0.0
    cache_hits: int = 0


@dataclass
class ChunkConfig:
    """Chunking configuration."""
    strategy: ChunkingStrategy = ChunkingStrategy.FIXED
    chunk_size: int = 500
    overlap: int = 50
    min_chunk_size: int = 100


@dataclass
class ProviderStats:
    """Statistics for an embedding provider."""
    provider: str
    total_requests: int = 0
    total_tokens: int = 0
    total_errors: int = 0
    avg_latency: float = 0.0
    cache_hits: int = 0


# =============================================================================
# CACHE
# =============================================================================

class EmbeddingCache:
    """Cache for embeddings."""

    def __init__(self, max_size: int = 10000, ttl: int = 3600):
        self._cache: Dict[str, Tuple[Vector, datetime]] = {}
        self._max_size = max_size
        self._ttl = ttl
        self._access_times: Dict[str, datetime] = {}

    def _hash_key(self, text: str, model: str) -> str:
        """Generate cache key."""
        data = f"{model}:{text}"
        return hashlib.sha256(data.encode()).hexdigest()

    def get(self, text: str, model: str) -> Optional[Vector]:
        """Get cached embedding."""
        key = self._hash_key(text, model)

        if key in self._cache:
            embedding, created = self._cache[key]

            if datetime.utcnow() - created < timedelta(seconds=self._ttl):
                self._access_times[key] = datetime.utcnow()
                return embedding
            else:
                del self._cache[key]
                del self._access_times[key]

        return None

    def set(self, text: str, model: str, embedding: Vector) -> None:
        """Cache embedding."""
        # Evict if full
        if len(self._cache) >= self._max_size:
            self._evict()

        key = self._hash_key(text, model)
        self._cache[key] = (embedding, datetime.utcnow())
        self._access_times[key] = datetime.utcnow()

    def _evict(self) -> None:
        """Evict least recently used items."""
        if not self._access_times:
            return

        # Find oldest accessed items
        sorted_keys = sorted(self._access_times.items(), key=lambda x: x[1])

        # Remove 10% of cache
        to_remove = max(1, len(sorted_keys) // 10)

        for key, _ in sorted_keys[:to_remove]:
            if key in self._cache:
                del self._cache[key]
            if key in self._access_times:
                del self._access_times[key]

    def clear(self) -> None:
        """Clear cache."""
        self._cache.clear()
        self._access_times.clear()

    def size(self) -> int:
        """Get cache size."""
        return len(self._cache)


# =============================================================================
# CHUNKERS
# =============================================================================

class TextChunker:
    """Text chunking utilities."""

    @staticmethod
    def fixed_chunks(text: str, chunk_size: int, overlap: int) -> List[str]:
        """Split text into fixed-size chunks."""
        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]

            if chunk.strip():
                chunks.append(chunk)

            start = end - overlap

        return chunks

    @staticmethod
    def sentence_chunks(text: str, min_size: int = 100) -> List[str]:
        """Split text into sentence-based chunks."""
        # Simple sentence splitting (in practice, use nltk or spacy)
        sentences = []
        current = []
        current_len = 0

        # Split on common sentence endings
        parts = text.replace('? ', '?|').replace('! ', '!|').replace('. ', '.|').split('|')

        for part in parts:
            part = part.strip()
            if not part:
                continue

            current.append(part)
            current_len += len(part)

            if current_len >= min_size:
                sentences.append(' '.join(current))
                current = []
                current_len = 0

        if current:
            sentences.append(' '.join(current))

        return sentences

    @staticmethod
    def paragraph_chunks(text: str, min_size: int = 100) -> List[str]:
        """Split text into paragraph-based chunks."""
        paragraphs = text.split('\n\n')

        result = []
        current = []
        current_len = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            current.append(para)
            current_len += len(para)

            if current_len >= min_size:
                result.append('\n\n'.join(current))
                current = []
                current_len = 0

        if current:
            result.append('\n\n'.join(current))

        return result

    @staticmethod
    def chunk(text: str, config: ChunkConfig) -> List[str]:
        """Chunk text based on configuration."""
        if config.strategy == ChunkingStrategy.FIXED:
            return TextChunker.fixed_chunks(text, config.chunk_size, config.overlap)
        elif config.strategy == ChunkingStrategy.SENTENCE:
            return TextChunker.sentence_chunks(text, config.min_chunk_size)
        elif config.strategy == ChunkingStrategy.PARAGRAPH:
            return TextChunker.paragraph_chunks(text, config.min_chunk_size)
        else:
            return [text]


# =============================================================================
# EMBEDDING PROVIDERS
# =============================================================================

class BaseEmbeddingProvider(ABC):
    """Base class for embedding providers."""

    @abstractmethod
    async def embed(self, texts: List[str]) -> List[Vector]:
        """Generate embeddings for texts."""
        pass

    @abstractmethod
    def dimension(self) -> int:
        """Get embedding dimension."""
        pass


class LocalEmbeddingProvider(BaseEmbeddingProvider):
    """Local/simulated embedding provider."""

    def __init__(self, dimension: int = 384):
        self._dimension = dimension
        self._vocab: Dict[str, Vector] = {}

    def _get_word_embedding(self, word: str) -> Vector:
        """Get or create word embedding."""
        word = word.lower()

        if word not in self._vocab:
            # Create deterministic pseudo-embedding
            random.seed(hash(word))
            vec = [random.gauss(0, 1) for _ in range(self._dimension)]
            norm = math.sqrt(sum(x * x for x in vec))
            self._vocab[word] = [x / norm for x in vec]

        return self._vocab[word]

    async def embed(self, texts: List[str]) -> List[Vector]:
        """Generate embeddings."""
        results = []

        for text in texts:
            # Tokenize
            words = text.lower().split()

            if not words:
                results.append([0.0] * self._dimension)
                continue

            # Get word embeddings and average
            embeddings = [self._get_word_embedding(w) for w in words]

            # Mean pooling
            result = [0.0] * self._dimension
            for emb in embeddings:
                for i, v in enumerate(emb):
                    result[i] += v

            result = [x / len(embeddings) for x in result]

            # Normalize
            norm = math.sqrt(sum(x * x for x in result))
            if norm > 0:
                result = [x / norm for x in result]

            results.append(result)

        # Simulate latency
        await asyncio.sleep(0.001 * len(texts))

        return results

    def dimension(self) -> int:
        return self._dimension


class SimulatedOpenAIProvider(BaseEmbeddingProvider):
    """Simulated OpenAI-like provider."""

    def __init__(self, model: str = "text-embedding-3-small", dimension: int = 1536):
        self._model = model
        self._dimension = dimension
        self._cost_per_1k_tokens = 0.0001

    async def embed(self, texts: List[str]) -> List[Vector]:
        """Generate embeddings (simulated)."""
        results = []

        for text in texts:
            # Create deterministic embedding
            random.seed(hash(text + self._model))
            vec = [random.gauss(0, 1) for _ in range(self._dimension)]
            norm = math.sqrt(sum(x * x for x in vec))
            results.append([x / norm for x in vec])

        # Simulate API latency
        await asyncio.sleep(0.05 + 0.01 * len(texts))

        return results

    def dimension(self) -> int:
        return self._dimension


# =============================================================================
# EMBEDDING MANAGER
# =============================================================================

class EmbeddingManager:
    """
    Embedding Manager for BAEL.

    Advanced embedding generation and management.
    """

    def __init__(self, config: Optional[EmbeddingConfig] = None):
        self._config = config or EmbeddingConfig()
        self._providers: Dict[EmbeddingProvider, BaseEmbeddingProvider] = {}
        self._cache = EmbeddingCache()
        self._stats: Dict[str, ProviderStats] = defaultdict(lambda: ProviderStats("unknown"))

        # Initialize default providers
        self._init_providers()

    def _init_providers(self) -> None:
        """Initialize embedding providers."""
        self._providers[EmbeddingProvider.LOCAL] = LocalEmbeddingProvider(
            dimension=self._config.dimension
        )
        self._providers[EmbeddingProvider.OPENAI] = SimulatedOpenAIProvider(
            dimension=1536
        )

    # -------------------------------------------------------------------------
    # CORE EMBEDDING
    # -------------------------------------------------------------------------

    async def embed(
        self,
        text: str,
        provider: Optional[EmbeddingProvider] = None,
        use_cache: bool = True
    ) -> EmbeddingResult:
        """Generate embedding for text."""
        provider = provider or self._config.provider
        model = self._config.model

        # Check cache
        if use_cache:
            cached = self._cache.get(text, model)
            if cached:
                self._stats[provider.value].cache_hits += 1
                return EmbeddingResult(
                    id=str(uuid.uuid4()),
                    text=text,
                    embedding=cached,
                    model=model,
                    dimension=len(cached),
                    from_cache=True
                )

        # Get provider
        emb_provider = self._providers.get(provider)
        if not emb_provider:
            raise ValueError(f"Provider {provider} not available")

        # Generate embedding
        start = time.time()

        try:
            embeddings = await emb_provider.embed([text])
            embedding = embeddings[0]

            processing_time = time.time() - start

            # Update stats
            stats = self._stats[provider.value]
            stats.total_requests += 1
            stats.total_tokens += len(text.split())
            stats.avg_latency = (stats.avg_latency * (stats.total_requests - 1) + processing_time) / stats.total_requests

            # Normalize if configured
            if self._config.normalize:
                norm = math.sqrt(sum(x * x for x in embedding))
                if norm > 0:
                    embedding = [x / norm for x in embedding]

            # Cache result
            if use_cache:
                self._cache.set(text, model, embedding)

            return EmbeddingResult(
                id=str(uuid.uuid4()),
                text=text,
                embedding=embedding,
                model=model,
                dimension=len(embedding),
                tokens_used=len(text.split()),
                processing_time=processing_time
            )

        except Exception as e:
            self._stats[provider.value].total_errors += 1
            raise

    async def embed_batch(
        self,
        texts: List[str],
        provider: Optional[EmbeddingProvider] = None,
        use_cache: bool = True
    ) -> BatchResult:
        """Generate embeddings for multiple texts."""
        provider = provider or self._config.provider
        model = self._config.model

        results = []
        cache_hits = 0
        total_tokens = 0
        to_embed = []
        to_embed_indices = []

        # Check cache
        for i, text in enumerate(texts):
            if use_cache:
                cached = self._cache.get(text, model)
                if cached:
                    cache_hits += 1
                    results.append(EmbeddingResult(
                        id=str(uuid.uuid4()),
                        text=text,
                        embedding=cached,
                        model=model,
                        dimension=len(cached),
                        from_cache=True
                    ))
                    continue

            to_embed.append(text)
            to_embed_indices.append(i)
            results.append(None)  # Placeholder

        # Embed non-cached texts
        if to_embed:
            emb_provider = self._providers.get(provider)
            if not emb_provider:
                raise ValueError(f"Provider {provider} not available")

            start = time.time()

            # Process in batches
            all_embeddings = []
            for batch_start in range(0, len(to_embed), self._config.batch_size):
                batch = to_embed[batch_start:batch_start + self._config.batch_size]
                embeddings = await emb_provider.embed(batch)
                all_embeddings.extend(embeddings)

            processing_time = time.time() - start

            # Fill in results
            for i, (text, embedding) in enumerate(zip(to_embed, all_embeddings)):
                idx = to_embed_indices[i]

                # Normalize
                if self._config.normalize:
                    norm = math.sqrt(sum(x * x for x in embedding))
                    if norm > 0:
                        embedding = [x / norm for x in embedding]

                # Cache
                if use_cache:
                    self._cache.set(text, model, embedding)

                tokens = len(text.split())
                total_tokens += tokens

                results[idx] = EmbeddingResult(
                    id=str(uuid.uuid4()),
                    text=text,
                    embedding=embedding,
                    model=model,
                    dimension=len(embedding),
                    tokens_used=tokens,
                    processing_time=processing_time / len(to_embed)
                )

        self._stats[provider.value].cache_hits += cache_hits

        return BatchResult(
            embeddings=results,
            total_tokens=total_tokens,
            total_time=sum(r.processing_time for r in results if r and not r.from_cache),
            cache_hits=cache_hits
        )

    # -------------------------------------------------------------------------
    # CHUNKED EMBEDDING
    # -------------------------------------------------------------------------

    async def embed_long_text(
        self,
        text: str,
        chunk_config: Optional[ChunkConfig] = None,
        aggregation: PoolingStrategy = PoolingStrategy.MEAN
    ) -> EmbeddingResult:
        """Embed long text with chunking."""
        config = chunk_config or ChunkConfig()

        # Chunk text
        chunks = TextChunker.chunk(text, config)

        if not chunks:
            return await self.embed(text)

        # Embed chunks
        batch_result = await self.embed_batch(chunks)

        # Aggregate embeddings
        embeddings = [r.embedding for r in batch_result.embeddings]
        aggregated = self._aggregate_embeddings(embeddings, aggregation)

        return EmbeddingResult(
            id=str(uuid.uuid4()),
            text=text[:100] + "..." if len(text) > 100 else text,
            embedding=aggregated,
            model=self._config.model,
            dimension=len(aggregated),
            tokens_used=batch_result.total_tokens,
            processing_time=batch_result.total_time,
            metadata={"chunks": len(chunks)}
        )

    def _aggregate_embeddings(
        self,
        embeddings: List[Vector],
        strategy: PoolingStrategy
    ) -> Vector:
        """Aggregate multiple embeddings."""
        if not embeddings:
            return []

        dimension = len(embeddings[0])

        if strategy == PoolingStrategy.MEAN:
            result = [0.0] * dimension
            for emb in embeddings:
                for i, v in enumerate(emb):
                    result[i] += v
            result = [x / len(embeddings) for x in result]

        elif strategy == PoolingStrategy.MAX:
            result = [-float('inf')] * dimension
            for emb in embeddings:
                for i, v in enumerate(emb):
                    result[i] = max(result[i], v)

        elif strategy == PoolingStrategy.CLS:
            result = embeddings[0]

        elif strategy == PoolingStrategy.LAST:
            result = embeddings[-1]

        elif strategy == PoolingStrategy.WEIGHTED:
            # Weight by position (later chunks slightly more important)
            weights = [(i + 1) / len(embeddings) for i in range(len(embeddings))]
            total_weight = sum(weights)

            result = [0.0] * dimension
            for emb, weight in zip(embeddings, weights):
                for i, v in enumerate(emb):
                    result[i] += v * weight
            result = [x / total_weight for x in result]

        else:
            result = embeddings[0]

        # Normalize
        norm = math.sqrt(sum(x * x for x in result))
        if norm > 0:
            result = [x / norm for x in result]

        return result

    # -------------------------------------------------------------------------
    # COMPARISON
    # -------------------------------------------------------------------------

    def similarity(self, v1: Vector, v2: Vector) -> float:
        """Calculate cosine similarity."""
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot / (norm1 * norm2)

    def distance(self, v1: Vector, v2: Vector) -> float:
        """Calculate Euclidean distance."""
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2)))

    async def compare(
        self,
        text1: str,
        text2: str
    ) -> Tuple[float, float]:
        """Compare two texts, return (similarity, distance)."""
        result1 = await self.embed(text1)
        result2 = await self.embed(text2)

        sim = self.similarity(result1.embedding, result2.embedding)
        dist = self.distance(result1.embedding, result2.embedding)

        return sim, dist

    # -------------------------------------------------------------------------
    # DIMENSIONALITY REDUCTION
    # -------------------------------------------------------------------------

    def reduce_dimension(
        self,
        embedding: Vector,
        target_dim: int,
        method: str = "pca_like"
    ) -> Vector:
        """Reduce embedding dimension (simplified)."""
        if len(embedding) <= target_dim:
            return embedding

        # Simple approach: average pooling
        chunk_size = len(embedding) // target_dim
        result = []

        for i in range(target_dim):
            start = i * chunk_size
            end = start + chunk_size if i < target_dim - 1 else len(embedding)
            chunk = embedding[start:end]
            result.append(sum(chunk) / len(chunk))

        # Normalize
        norm = math.sqrt(sum(x * x for x in result))
        if norm > 0:
            result = [x / norm for x in result]

        return result

    # -------------------------------------------------------------------------
    # CACHE & STATS
    # -------------------------------------------------------------------------

    def clear_cache(self) -> None:
        """Clear embedding cache."""
        self._cache.clear()

    def cache_size(self) -> int:
        """Get cache size."""
        return self._cache.size()

    def get_stats(self, provider: Optional[str] = None) -> Dict[str, ProviderStats]:
        """Get provider statistics."""
        if provider:
            return {provider: self._stats[provider]}
        return dict(self._stats)

    # -------------------------------------------------------------------------
    # PROVIDER MANAGEMENT
    # -------------------------------------------------------------------------

    def add_provider(
        self,
        name: EmbeddingProvider,
        provider: BaseEmbeddingProvider
    ) -> None:
        """Add custom provider."""
        self._providers[name] = provider

    def list_providers(self) -> List[str]:
        """List available providers."""
        return [p.value for p in self._providers.keys()]


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Embedding Manager."""
    print("=" * 70)
    print("BAEL - EMBEDDING MANAGER DEMO")
    print("Advanced Embedding Generation")
    print("=" * 70)
    print()

    manager = EmbeddingManager(EmbeddingConfig(
        dimension=384,
        normalize=True
    ))

    # 1. Single Embedding
    print("1. SINGLE EMBEDDING:")
    print("-" * 40)

    text = "Machine learning is a subset of artificial intelligence."
    result = await manager.embed(text)

    print(f"   Text: {text}")
    print(f"   Dimension: {result.dimension}")
    print(f"   First 5 values: {result.embedding[:5]}")
    print(f"   Time: {result.processing_time:.4f}s")
    print()

    # 2. Batch Embedding
    print("2. BATCH EMBEDDING:")
    print("-" * 40)

    texts = [
        "Natural language processing",
        "Computer vision and image recognition",
        "Deep learning with neural networks",
        "Reinforcement learning algorithms"
    ]

    batch = await manager.embed_batch(texts)

    print(f"   Texts: {len(texts)}")
    print(f"   Total tokens: {batch.total_tokens}")
    print(f"   Total time: {batch.total_time:.4f}s")
    for r in batch.embeddings:
        print(f"      - {r.text[:30]}... ({r.dimension}d)")
    print()

    # 3. Caching
    print("3. CACHING:")
    print("-" * 40)

    # First request
    r1 = await manager.embed(text)
    print(f"   First request - from cache: {r1.from_cache}")

    # Second request (should be cached)
    r2 = await manager.embed(text)
    print(f"   Second request - from cache: {r2.from_cache}")
    print(f"   Cache size: {manager.cache_size()}")
    print()

    # 4. Similarity Comparison
    print("4. SIMILARITY COMPARISON:")
    print("-" * 40)

    text1 = "Dogs are loyal pets"
    text2 = "Cats are independent animals"
    text3 = "Programming is fun"

    sim12, dist12 = await manager.compare(text1, text2)
    sim13, dist13 = await manager.compare(text1, text3)

    print(f"   '{text1}' vs '{text2}':")
    print(f"      Similarity: {sim12:.4f}")
    print(f"      Distance: {dist12:.4f}")
    print()
    print(f"   '{text1}' vs '{text3}':")
    print(f"      Similarity: {sim13:.4f}")
    print(f"      Distance: {dist13:.4f}")
    print()

    # 5. Long Text with Chunking
    print("5. LONG TEXT CHUNKING:")
    print("-" * 40)

    long_text = """
    Artificial intelligence (AI) is intelligence demonstrated by machines,
    as opposed to natural intelligence displayed by humans. AI research
    has been defined as the field of study of intelligent agents, which
    refers to any system that perceives its environment and takes actions
    that maximize its chance of achieving its goals.

    Machine learning is a type of AI that allows software applications to
    become more accurate at predicting outcomes without being explicitly
    programmed to do so. Machine learning algorithms use historical data
    as input to predict new output values.
    """

    result = await manager.embed_long_text(
        long_text,
        chunk_config=ChunkConfig(chunk_size=200, overlap=50)
    )

    print(f"   Original length: {len(long_text)} chars")
    print(f"   Chunks: {result.metadata.get('chunks', 1)}")
    print(f"   Dimension: {result.dimension}")
    print()

    # 6. Different Pooling Strategies
    print("6. POOLING STRATEGIES:")
    print("-" * 40)

    for strategy in [PoolingStrategy.MEAN, PoolingStrategy.MAX, PoolingStrategy.CLS]:
        result = await manager.embed_long_text(
            long_text,
            aggregation=strategy
        )
        print(f"   {strategy.value}: first 3 values = {result.embedding[:3]}")
    print()

    # 7. Dimensionality Reduction
    print("7. DIMENSIONALITY REDUCTION:")
    print("-" * 40)

    original = await manager.embed("Test embedding")
    reduced = manager.reduce_dimension(original.embedding, 64)

    print(f"   Original: {len(original.embedding)}d")
    print(f"   Reduced: {len(reduced)}d")
    print()

    # 8. Provider Statistics
    print("8. PROVIDER STATISTICS:")
    print("-" * 40)

    stats = manager.get_stats()
    for provider, stat in stats.items():
        print(f"   {provider}:")
        print(f"      Requests: {stat.total_requests}")
        print(f"      Tokens: {stat.total_tokens}")
        print(f"      Cache hits: {stat.cache_hits}")
        print(f"      Avg latency: {stat.avg_latency:.4f}s")
    print()

    # 9. Text Chunking
    print("9. TEXT CHUNKING:")
    print("-" * 40)

    sample = "First sentence. Second sentence. Third sentence. Fourth sentence."

    fixed = TextChunker.fixed_chunks(sample, 20, 5)
    print(f"   Fixed chunks: {len(fixed)}")

    sentences = TextChunker.sentence_chunks(sample, 10)
    print(f"   Sentence chunks: {len(sentences)}")
    print()

    # 10. Similarity Matrix
    print("10. SIMILARITY MATRIX:")
    print("-" * 40)

    concepts = ["cat", "dog", "car", "truck"]
    batch = await manager.embed_batch(concepts)

    print("         ", end="")
    for c in concepts:
        print(f"{c:8}", end="")
    print()

    for i, c1 in enumerate(concepts):
        print(f"{c1:8} ", end="")
        for j, c2 in enumerate(concepts):
            sim = manager.similarity(
                batch.embeddings[i].embedding,
                batch.embeddings[j].embedding
            )
            print(f"{sim:7.3f} ", end="")
        print()
    print()

    # 11. Available Providers
    print("11. AVAILABLE PROVIDERS:")
    print("-" * 40)

    providers = manager.list_providers()
    for p in providers:
        print(f"   - {p}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Embedding Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
