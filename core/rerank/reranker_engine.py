#!/usr/bin/env python3
"""
BAEL - Reranker Engine
Search result reranking and relevance scoring.

Features:
- Multiple reranking strategies
- Cross-encoder simulation
- BM25 scoring
- MMR (Maximal Marginal Relevance)
- Reciprocal Rank Fusion
"""

import asyncio
import hashlib
import json
import math
import random
import re
import time
import uuid
from abc import ABC, abstractmethod
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class RerankStrategy(Enum):
    """Reranking strategies."""
    CROSS_ENCODER = "cross_encoder"
    BM25 = "bm25"
    TF_IDF = "tf_idf"
    MMR = "mmr"
    RRF = "rrf"
    COHERE = "cohere"
    ENSEMBLE = "ensemble"


class ScoringMethod(Enum):
    """Scoring methods."""
    ADDITIVE = "additive"
    MULTIPLICATIVE = "multiplicative"
    HARMONIC = "harmonic"
    GEOMETRIC = "geometric"


class NormalizationMethod(Enum):
    """Score normalization methods."""
    NONE = "none"
    MIN_MAX = "min_max"
    Z_SCORE = "z_score"
    SOFTMAX = "softmax"


class DiversityMetric(Enum):
    """Diversity metrics."""
    COSINE = "cosine"
    JACCARD = "jaccard"
    EDIT_DISTANCE = "edit_distance"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Document:
    """Document for reranking."""
    doc_id: str = ""
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    original_score: float = 0.0
    original_rank: int = 0

    def __post_init__(self):
        if not self.doc_id:
            self.doc_id = str(uuid.uuid4())[:8]


@dataclass
class ScoredDocument:
    """Document with reranking score."""
    document: Document
    score: float = 0.0
    rank: int = 0
    scores_breakdown: Dict[str, float] = field(default_factory=dict)


@dataclass
class RerankRequest:
    """Reranking request."""
    request_id: str = ""
    query: str = ""
    documents: List[Document] = field(default_factory=list)
    top_k: int = 10
    strategy: RerankStrategy = RerankStrategy.BM25

    def __post_init__(self):
        if not self.request_id:
            self.request_id = str(uuid.uuid4())[:8]


@dataclass
class RerankResult:
    """Reranking result."""
    request_id: str
    query: str = ""
    documents: List[ScoredDocument] = field(default_factory=list)
    strategy_used: RerankStrategy = RerankStrategy.BM25
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RerankConfig:
    """Reranking configuration."""
    strategy: RerankStrategy = RerankStrategy.BM25
    top_k: int = 10
    normalization: NormalizationMethod = NormalizationMethod.MIN_MAX
    diversity_lambda: float = 0.5
    rrf_k: int = 60
    ensemble_weights: Dict[str, float] = field(default_factory=dict)


@dataclass
class RerankStats:
    """Reranking statistics."""
    total_requests: int = 0
    total_documents: int = 0
    avg_duration_ms: float = 0.0
    by_strategy: Dict[str, int] = field(default_factory=dict)


# =============================================================================
# TOKENIZER
# =============================================================================

class SimpleTokenizer:
    """Simple word tokenizer."""

    def __init__(self, lowercase: bool = True):
        self._lowercase = lowercase
        self._stopwords = {
            "a", "an", "the", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "must", "shall",
            "can", "need", "dare", "ought", "used", "to", "of", "in",
            "for", "on", "with", "at", "by", "from", "as", "into",
            "through", "during", "before", "after", "above", "below",
            "between", "under", "again", "further", "then", "once",
            "here", "there", "when", "where", "why", "how", "all",
            "each", "few", "more", "most", "other", "some", "such",
            "no", "nor", "not", "only", "own", "same", "so", "than",
            "too", "very", "just", "and", "but", "if", "or", "because",
            "until", "while", "this", "that", "these", "those", "it"
        }

    def tokenize(self, text: str) -> List[str]:
        """Tokenize text."""
        if self._lowercase:
            text = text.lower()

        tokens = re.findall(r'\b[a-zA-Z0-9]+\b', text)

        return tokens

    def tokenize_filtered(self, text: str) -> List[str]:
        """Tokenize and remove stopwords."""
        tokens = self.tokenize(text)
        return [t for t in tokens if t not in self._stopwords]


# =============================================================================
# RERANKERS
# =============================================================================

class BaseReranker(ABC):
    """Abstract base reranker."""

    @property
    @abstractmethod
    def strategy(self) -> RerankStrategy:
        """Get reranking strategy."""
        pass

    @abstractmethod
    async def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: int = 10
    ) -> List[ScoredDocument]:
        """Rerank documents."""
        pass


class BM25Reranker(BaseReranker):
    """BM25 reranker."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self._k1 = k1
        self._b = b
        self._tokenizer = SimpleTokenizer()

    @property
    def strategy(self) -> RerankStrategy:
        return RerankStrategy.BM25

    async def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: int = 10
    ) -> List[ScoredDocument]:
        """Rerank using BM25."""
        query_tokens = self._tokenizer.tokenize_filtered(query)

        doc_lengths = []
        doc_tokens_list = []

        for doc in documents:
            tokens = self._tokenizer.tokenize_filtered(doc.content)
            doc_tokens_list.append(tokens)
            doc_lengths.append(len(tokens))

        avg_doc_length = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 1

        doc_freqs = Counter()
        for tokens in doc_tokens_list:
            for token in set(tokens):
                doc_freqs[token] += 1

        N = len(documents)
        scored = []

        for i, (doc, tokens) in enumerate(zip(documents, doc_tokens_list)):
            score = 0.0
            term_freqs = Counter(tokens)
            doc_len = doc_lengths[i]

            for term in query_tokens:
                if term in term_freqs:
                    tf = term_freqs[term]
                    df = doc_freqs[term]

                    idf = math.log((N - df + 0.5) / (df + 0.5) + 1)

                    numerator = tf * (self._k1 + 1)
                    denominator = tf + self._k1 * (1 - self._b + self._b * (doc_len / avg_doc_length))

                    score += idf * (numerator / denominator)

            scored.append(ScoredDocument(
                document=doc,
                score=score,
                scores_breakdown={"bm25": score}
            ))

        scored.sort(key=lambda x: x.score, reverse=True)

        for rank, sd in enumerate(scored[:top_k], 1):
            sd.rank = rank

        return scored[:top_k]


class TFIDFReranker(BaseReranker):
    """TF-IDF reranker."""

    def __init__(self):
        self._tokenizer = SimpleTokenizer()

    @property
    def strategy(self) -> RerankStrategy:
        return RerankStrategy.TF_IDF

    async def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: int = 10
    ) -> List[ScoredDocument]:
        """Rerank using TF-IDF."""
        query_tokens = self._tokenizer.tokenize_filtered(query)

        doc_tokens_list = []
        for doc in documents:
            tokens = self._tokenizer.tokenize_filtered(doc.content)
            doc_tokens_list.append(tokens)

        doc_freqs = Counter()
        for tokens in doc_tokens_list:
            for token in set(tokens):
                doc_freqs[token] += 1

        N = len(documents)
        scored = []

        for i, (doc, tokens) in enumerate(zip(documents, doc_tokens_list)):
            term_freqs = Counter(tokens)
            doc_len = len(tokens) if tokens else 1

            score = 0.0

            for term in query_tokens:
                if term in term_freqs:
                    tf = term_freqs[term] / doc_len

                    df = doc_freqs[term]
                    idf = math.log(N / (df + 1)) + 1

                    score += tf * idf

            scored.append(ScoredDocument(
                document=doc,
                score=score,
                scores_breakdown={"tfidf": score}
            ))

        scored.sort(key=lambda x: x.score, reverse=True)

        for rank, sd in enumerate(scored[:top_k], 1):
            sd.rank = rank

        return scored[:top_k]


class CrossEncoderReranker(BaseReranker):
    """Cross-encoder reranker (simulated)."""

    def __init__(self):
        self._tokenizer = SimpleTokenizer()

    @property
    def strategy(self) -> RerankStrategy:
        return RerankStrategy.CROSS_ENCODER

    async def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: int = 10
    ) -> List[ScoredDocument]:
        """Rerank using cross-encoder simulation."""
        query_tokens = set(self._tokenizer.tokenize_filtered(query))

        scored = []

        for doc in documents:
            doc_tokens = set(self._tokenizer.tokenize_filtered(doc.content))

            overlap = len(query_tokens & doc_tokens)

            union = len(query_tokens | doc_tokens)
            jaccard = overlap / union if union > 0 else 0

            coverage = overlap / len(query_tokens) if query_tokens else 0

            length_factor = min(1.0, len(doc.content) / 500)

            score = 0.4 * jaccard + 0.4 * coverage + 0.2 * length_factor

            await asyncio.sleep(0.001)

            scored.append(ScoredDocument(
                document=doc,
                score=score,
                scores_breakdown={
                    "jaccard": jaccard,
                    "coverage": coverage,
                    "length": length_factor
                }
            ))

        scored.sort(key=lambda x: x.score, reverse=True)

        for rank, sd in enumerate(scored[:top_k], 1):
            sd.rank = rank

        return scored[:top_k]


class MMRReranker(BaseReranker):
    """Maximal Marginal Relevance reranker."""

    def __init__(self, lambda_param: float = 0.5):
        self._lambda = lambda_param
        self._tokenizer = SimpleTokenizer()

    @property
    def strategy(self) -> RerankStrategy:
        return RerankStrategy.MMR

    async def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: int = 10
    ) -> List[ScoredDocument]:
        """Rerank using MMR for diversity."""
        query_tokens = set(self._tokenizer.tokenize_filtered(query))

        doc_vectors = []
        for doc in documents:
            tokens = set(self._tokenizer.tokenize_filtered(doc.content))
            doc_vectors.append(tokens)

        def relevance(doc_tokens: Set[str]) -> float:
            if not query_tokens or not doc_tokens:
                return 0.0

            overlap = len(query_tokens & doc_tokens)
            return overlap / len(query_tokens)

        def similarity(tokens_a: Set[str], tokens_b: Set[str]) -> float:
            if not tokens_a or not tokens_b:
                return 0.0

            intersection = len(tokens_a & tokens_b)
            union = len(tokens_a | tokens_b)
            return intersection / union if union > 0 else 0.0

        selected_indices: List[int] = []
        remaining = set(range(len(documents)))

        while len(selected_indices) < min(top_k, len(documents)) and remaining:
            best_idx = -1
            best_score = float('-inf')

            for idx in remaining:
                rel = relevance(doc_vectors[idx])

                max_sim = 0.0
                if selected_indices:
                    for sel_idx in selected_indices:
                        sim = similarity(doc_vectors[idx], doc_vectors[sel_idx])
                        max_sim = max(max_sim, sim)

                mmr_score = self._lambda * rel - (1 - self._lambda) * max_sim

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx

            if best_idx >= 0:
                selected_indices.append(best_idx)
                remaining.remove(best_idx)

        result = []
        for rank, idx in enumerate(selected_indices, 1):
            doc = documents[idx]
            rel = relevance(doc_vectors[idx])

            result.append(ScoredDocument(
                document=doc,
                score=rel,
                rank=rank,
                scores_breakdown={
                    "relevance": rel,
                    "mmr_rank": rank
                }
            ))

        return result


class RRFReranker(BaseReranker):
    """Reciprocal Rank Fusion reranker."""

    def __init__(self, k: int = 60):
        self._k = k

    @property
    def strategy(self) -> RerankStrategy:
        return RerankStrategy.RRF

    async def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: int = 10
    ) -> List[ScoredDocument]:
        """Rerank using RRF from original ranks."""
        scored = []

        for doc in documents:
            rank = doc.original_rank if doc.original_rank > 0 else 1

            rrf_score = 1.0 / (self._k + rank)

            scored.append(ScoredDocument(
                document=doc,
                score=rrf_score,
                scores_breakdown={
                    "original_rank": rank,
                    "rrf_score": rrf_score
                }
            ))

        scored.sort(key=lambda x: x.score, reverse=True)

        for rank, sd in enumerate(scored[:top_k], 1):
            sd.rank = rank

        return scored[:top_k]

    async def fuse(
        self,
        rankings: List[List[Tuple[str, int]]],
        doc_map: Dict[str, Document],
        top_k: int = 10
    ) -> List[ScoredDocument]:
        """Fuse multiple rankings."""
        rrf_scores: Dict[str, float] = defaultdict(float)

        for ranking in rankings:
            for doc_id, rank in ranking:
                rrf_scores[doc_id] += 1.0 / (self._k + rank)

        sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        result = []
        for rank, (doc_id, score) in enumerate(sorted_docs[:top_k], 1):
            doc = doc_map.get(doc_id)
            if doc:
                result.append(ScoredDocument(
                    document=doc,
                    score=score,
                    rank=rank,
                    scores_breakdown={"rrf_fused": score}
                ))

        return result


class EnsembleReranker(BaseReranker):
    """Ensemble of multiple rerankers."""

    def __init__(self, rerankers: Optional[List[BaseReranker]] = None):
        self._rerankers = rerankers or [
            BM25Reranker(),
            TFIDFReranker(),
            CrossEncoderReranker()
        ]
        self._weights = [1.0 / len(self._rerankers)] * len(self._rerankers)

    @property
    def strategy(self) -> RerankStrategy:
        return RerankStrategy.ENSEMBLE

    def set_weights(self, weights: List[float]) -> None:
        """Set reranker weights."""
        if len(weights) == len(self._rerankers):
            total = sum(weights)
            self._weights = [w / total for w in weights]

    async def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: int = 10
    ) -> List[ScoredDocument]:
        """Rerank using ensemble."""
        all_results = await asyncio.gather(*[
            r.rerank(query, documents, len(documents))
            for r in self._rerankers
        ])

        combined_scores: Dict[str, Dict[str, Any]] = {}

        for results, weight, reranker in zip(all_results, self._weights, self._rerankers):
            for sd in results:
                doc_id = sd.document.doc_id

                if doc_id not in combined_scores:
                    combined_scores[doc_id] = {
                        "document": sd.document,
                        "scores": {},
                        "weighted_sum": 0.0
                    }

                combined_scores[doc_id]["scores"][reranker.strategy.value] = sd.score
                combined_scores[doc_id]["weighted_sum"] += weight * sd.score

        scored = []
        for doc_id, data in combined_scores.items():
            scored.append(ScoredDocument(
                document=data["document"],
                score=data["weighted_sum"],
                scores_breakdown=data["scores"]
            ))

        scored.sort(key=lambda x: x.score, reverse=True)

        for rank, sd in enumerate(scored[:top_k], 1):
            sd.rank = rank

        return scored[:top_k]


# =============================================================================
# SCORE NORMALIZER
# =============================================================================

class ScoreNormalizer:
    """Normalize scores."""

    def normalize(
        self,
        scores: List[float],
        method: NormalizationMethod = NormalizationMethod.MIN_MAX
    ) -> List[float]:
        """Normalize scores."""
        if not scores:
            return []

        if method == NormalizationMethod.NONE:
            return scores

        elif method == NormalizationMethod.MIN_MAX:
            return self._min_max(scores)

        elif method == NormalizationMethod.Z_SCORE:
            return self._z_score(scores)

        elif method == NormalizationMethod.SOFTMAX:
            return self._softmax(scores)

        return scores

    def _min_max(self, scores: List[float]) -> List[float]:
        """Min-max normalization."""
        min_s = min(scores)
        max_s = max(scores)

        if max_s == min_s:
            return [0.5] * len(scores)

        return [(s - min_s) / (max_s - min_s) for s in scores]

    def _z_score(self, scores: List[float]) -> List[float]:
        """Z-score normalization."""
        mean = sum(scores) / len(scores)
        variance = sum((s - mean) ** 2 for s in scores) / len(scores)
        std = math.sqrt(variance) if variance > 0 else 1.0

        return [(s - mean) / std for s in scores]

    def _softmax(self, scores: List[float]) -> List[float]:
        """Softmax normalization."""
        max_s = max(scores)
        exp_scores = [math.exp(s - max_s) for s in scores]
        sum_exp = sum(exp_scores)

        return [e / sum_exp for e in exp_scores]


# =============================================================================
# RERANKER ENGINE
# =============================================================================

class RerankerEngine:
    """
    Reranker Engine for BAEL.

    Search result reranking and relevance scoring.
    """

    def __init__(self, default_strategy: RerankStrategy = RerankStrategy.BM25):
        self._rerankers: Dict[RerankStrategy, BaseReranker] = {
            RerankStrategy.BM25: BM25Reranker(),
            RerankStrategy.TF_IDF: TFIDFReranker(),
            RerankStrategy.CROSS_ENCODER: CrossEncoderReranker(),
            RerankStrategy.MMR: MMRReranker(),
            RerankStrategy.RRF: RRFReranker(),
            RerankStrategy.ENSEMBLE: EnsembleReranker()
        }

        self._default_strategy = default_strategy
        self._normalizer = ScoreNormalizer()

        self._stats = RerankStats()
        self._results: Dict[str, RerankResult] = {}

    def register_reranker(
        self,
        strategy: RerankStrategy,
        reranker: BaseReranker
    ) -> None:
        """Register a custom reranker."""
        self._rerankers[strategy] = reranker

    async def rerank(
        self,
        query: str,
        documents: List[Document],
        strategy: Optional[RerankStrategy] = None,
        top_k: int = 10,
        normalize: NormalizationMethod = NormalizationMethod.MIN_MAX
    ) -> RerankResult:
        """Rerank documents."""
        strategy = strategy or self._default_strategy

        request = RerankRequest(
            query=query,
            documents=documents,
            top_k=top_k,
            strategy=strategy
        )

        reranker = self._rerankers.get(strategy)
        if not reranker:
            raise ValueError(f"Unknown strategy: {strategy}")

        start_time = time.time()

        scored_docs = await reranker.rerank(query, documents, top_k)

        if normalize != NormalizationMethod.NONE and scored_docs:
            scores = [sd.score for sd in scored_docs]
            normalized = self._normalizer.normalize(scores, normalize)

            for sd, norm_score in zip(scored_docs, normalized):
                sd.scores_breakdown["normalized"] = norm_score

        duration_ms = (time.time() - start_time) * 1000

        result = RerankResult(
            request_id=request.request_id,
            query=query,
            documents=scored_docs,
            strategy_used=strategy,
            duration_ms=duration_ms
        )

        self._results[result.request_id] = result
        self._update_stats(strategy, len(documents), duration_ms)

        return result

    async def rerank_with_scores(
        self,
        query: str,
        items: List[Tuple[str, float]],
        strategy: Optional[RerankStrategy] = None,
        top_k: int = 10
    ) -> RerankResult:
        """Rerank items with existing scores."""
        documents = []

        for rank, (content, score) in enumerate(items, 1):
            doc = Document(
                content=content,
                original_score=score,
                original_rank=rank
            )
            documents.append(doc)

        return await self.rerank(query, documents, strategy, top_k)

    async def fuse_rankings(
        self,
        rankings: List[List[Tuple[str, Document, int]]],
        top_k: int = 10
    ) -> List[ScoredDocument]:
        """Fuse multiple rankings using RRF."""
        rrf_reranker = self._rerankers.get(RerankStrategy.RRF)

        if not isinstance(rrf_reranker, RRFReranker):
            rrf_reranker = RRFReranker()

        doc_map: Dict[str, Document] = {}
        converted_rankings: List[List[Tuple[str, int]]] = []

        for ranking in rankings:
            converted = []
            for doc_id, doc, rank in ranking:
                doc_map[doc_id] = doc
                converted.append((doc_id, rank))
            converted_rankings.append(converted)

        return await rrf_reranker.fuse(converted_rankings, doc_map, top_k)

    async def rerank_diverse(
        self,
        query: str,
        documents: List[Document],
        top_k: int = 10,
        lambda_param: float = 0.5
    ) -> RerankResult:
        """Rerank with diversity (MMR)."""
        mmr_reranker = MMRReranker(lambda_param=lambda_param)

        start_time = time.time()
        scored_docs = await mmr_reranker.rerank(query, documents, top_k)
        duration_ms = (time.time() - start_time) * 1000

        result = RerankResult(
            request_id=str(uuid.uuid4())[:8],
            query=query,
            documents=scored_docs,
            strategy_used=RerankStrategy.MMR,
            duration_ms=duration_ms,
            metadata={"lambda": lambda_param}
        )

        self._results[result.request_id] = result
        self._update_stats(RerankStrategy.MMR, len(documents), duration_ms)

        return result

    async def ensemble_rerank(
        self,
        query: str,
        documents: List[Document],
        weights: Optional[Dict[str, float]] = None,
        top_k: int = 10
    ) -> RerankResult:
        """Rerank using ensemble with custom weights."""
        ensemble = self._rerankers.get(RerankStrategy.ENSEMBLE)

        if isinstance(ensemble, EnsembleReranker) and weights:
            weight_list = [
                weights.get("bm25", 1.0),
                weights.get("tfidf", 1.0),
                weights.get("cross_encoder", 1.0)
            ]
            ensemble.set_weights(weight_list)

        return await self.rerank(
            query, documents, RerankStrategy.ENSEMBLE, top_k
        )

    def get_result(self, request_id: str) -> Optional[RerankResult]:
        """Get a reranking result."""
        return self._results.get(request_id)

    def _update_stats(
        self,
        strategy: RerankStrategy,
        doc_count: int,
        duration_ms: float
    ) -> None:
        """Update statistics."""
        self._stats.total_requests += 1
        self._stats.total_documents += doc_count

        strategy_key = strategy.value
        self._stats.by_strategy[strategy_key] = \
            self._stats.by_strategy.get(strategy_key, 0) + 1

        if self._stats.total_requests > 0:
            total_duration = sum(r.duration_ms for r in self._results.values())
            self._stats.avg_duration_ms = total_duration / self._stats.total_requests

    @property
    def stats(self) -> RerankStats:
        """Get engine statistics."""
        return self._stats

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "default_strategy": self._default_strategy.value,
            "available_strategies": [s.value for s in self._rerankers.keys()],
            "total_requests": self._stats.total_requests,
            "total_documents": self._stats.total_documents,
            "avg_duration_ms": round(self._stats.avg_duration_ms, 2),
            "by_strategy": self._stats.by_strategy
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Reranker Engine."""
    print("=" * 70)
    print("BAEL - RERANKER ENGINE DEMO")
    print("Search Result Reranking")
    print("=" * 70)
    print()

    engine = RerankerEngine(default_strategy=RerankStrategy.BM25)

    # Sample documents
    sample_docs = [
        Document(
            content="Python is a programming language known for its simplicity and readability.",
            original_rank=1
        ),
        Document(
            content="Machine learning uses algorithms to learn patterns from data.",
            original_rank=2
        ),
        Document(
            content="Python machine learning libraries include scikit-learn and TensorFlow.",
            original_rank=3
        ),
        Document(
            content="Data science combines statistics, programming, and domain knowledge.",
            original_rank=4
        ),
        Document(
            content="Deep learning is a subset of machine learning using neural networks.",
            original_rank=5
        ),
        Document(
            content="Python is widely used for web development and automation.",
            original_rank=6
        ),
        Document(
            content="Natural language processing enables computers to understand text.",
            original_rank=7
        ),
        Document(
            content="Python data analysis is often done with pandas and numpy.",
            original_rank=8
        )
    ]

    query = "Python machine learning"

    # 1. BM25 Reranking
    print("1. BM25 RERANKING:")
    print("-" * 40)

    result = await engine.rerank(
        query=query,
        documents=sample_docs,
        strategy=RerankStrategy.BM25,
        top_k=5
    )

    for sd in result.documents:
        print(f"   #{sd.rank} (score: {sd.score:.4f})")
        print(f"      {sd.document.content[:60]}...")
    print()

    # 2. TF-IDF Reranking
    print("2. TF-IDF RERANKING:")
    print("-" * 40)

    result = await engine.rerank(
        query=query,
        documents=sample_docs,
        strategy=RerankStrategy.TF_IDF,
        top_k=5
    )

    for sd in result.documents:
        print(f"   #{sd.rank} (score: {sd.score:.4f})")
        print(f"      {sd.document.content[:60]}...")
    print()

    # 3. Cross-Encoder Reranking
    print("3. CROSS-ENCODER RERANKING:")
    print("-" * 40)

    result = await engine.rerank(
        query=query,
        documents=sample_docs,
        strategy=RerankStrategy.CROSS_ENCODER,
        top_k=5
    )

    for sd in result.documents:
        print(f"   #{sd.rank} (score: {sd.score:.4f})")
        print(f"      Breakdown: {sd.scores_breakdown}")
    print()

    # 4. MMR Diverse Reranking
    print("4. MMR DIVERSE RERANKING:")
    print("-" * 40)

    result = await engine.rerank_diverse(
        query=query,
        documents=sample_docs,
        top_k=5,
        lambda_param=0.6
    )

    for sd in result.documents:
        print(f"   #{sd.rank} (relevance: {sd.scores_breakdown.get('relevance', 0):.4f})")
        print(f"      {sd.document.content[:60]}...")
    print()

    # 5. Ensemble Reranking
    print("5. ENSEMBLE RERANKING:")
    print("-" * 40)

    result = await engine.ensemble_rerank(
        query=query,
        documents=sample_docs,
        weights={"bm25": 0.4, "tfidf": 0.3, "cross_encoder": 0.3},
        top_k=5
    )

    for sd in result.documents:
        print(f"   #{sd.rank} (score: {sd.score:.4f})")
        print(f"      Components: {sd.scores_breakdown}")
    print()

    # 6. Reciprocal Rank Fusion
    print("6. RECIPROCAL RANK FUSION:")
    print("-" * 40)

    result = await engine.rerank(
        query=query,
        documents=sample_docs,
        strategy=RerankStrategy.RRF,
        top_k=5
    )

    for sd in result.documents:
        orig = sd.scores_breakdown.get('original_rank', 0)
        print(f"   #{sd.rank} (RRF: {sd.score:.4f}, orig: {orig})")
    print()

    # 7. Score Normalization
    print("7. SCORE NORMALIZATION:")
    print("-" * 40)

    result = await engine.rerank(
        query=query,
        documents=sample_docs,
        strategy=RerankStrategy.BM25,
        top_k=5,
        normalize=NormalizationMethod.MIN_MAX
    )

    for sd in result.documents:
        norm = sd.scores_breakdown.get('normalized', 0)
        print(f"   #{sd.rank} raw: {sd.score:.4f}, normalized: {norm:.4f}")
    print()

    # 8. Rerank with Existing Scores
    print("8. RERANK WITH EXISTING SCORES:")
    print("-" * 40)

    items = [
        ("Python programming basics", 0.8),
        ("Advanced machine learning", 0.7),
        ("Python ML tutorial", 0.85),
        ("Data science overview", 0.6)
    ]

    result = await engine.rerank_with_scores(
        query=query,
        items=items,
        strategy=RerankStrategy.BM25,
        top_k=4
    )

    for sd in result.documents:
        print(f"   #{sd.rank}: {sd.document.content}")
        print(f"      Original: {sd.document.original_score}, New: {sd.score:.4f}")
    print()

    # 9. Statistics
    print("9. ENGINE STATISTICS:")
    print("-" * 40)

    stats = engine.stats

    print(f"   Total Requests: {stats.total_requests}")
    print(f"   Total Documents: {stats.total_documents}")
    print(f"   Avg Duration: {stats.avg_duration_ms:.2f}ms")
    print(f"   By Strategy: {stats.by_strategy}")
    print()

    # 10. Engine Summary
    print("10. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    print(f"   Default: {summary['default_strategy']}")
    print(f"   Available: {summary['available_strategies']}")
    print(f"   Requests: {summary['total_requests']}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Reranker Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
