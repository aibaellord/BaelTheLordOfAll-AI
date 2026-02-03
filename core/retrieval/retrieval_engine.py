#!/usr/bin/env python3
"""
BAEL - Retrieval Engine
Advanced information retrieval for AI agents.

Features:
- BM25 retrieval
- Vector retrieval
- Hybrid retrieval
- Query expansion
- Result re-ranking
"""

import asyncio
import hashlib
import math
import random
import re
import uuid
from abc import ABC, abstractmethod
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class RetrievalMethod(Enum):
    """Retrieval methods."""
    BM25 = "bm25"
    VECTOR = "vector"
    TF_IDF = "tf_idf"
    BOOLEAN = "boolean"
    HYBRID = "hybrid"


class IndexType(Enum):
    """Index types."""
    INVERTED = "inverted"
    FORWARD = "forward"
    POSITIONAL = "positional"


class RerankingMethod(Enum):
    """Re-ranking methods."""
    NONE = "none"
    CROSS_ENCODER = "cross_encoder"
    MMR = "mmr"
    DIVERSITY = "diversity"


class ExpansionMethod(Enum):
    """Query expansion methods."""
    NONE = "none"
    SYNONYMS = "synonyms"
    PSEUDO_RELEVANCE = "pseudo_relevance"
    EMBEDDING = "embedding"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Document:
    """A document for retrieval."""
    doc_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    tokens: List[str] = field(default_factory=list)
    embedding: List[float] = field(default_factory=list)


@dataclass
class Query:
    """A retrieval query."""
    query_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    text: str = ""
    tokens: List[str] = field(default_factory=list)
    embedding: List[float] = field(default_factory=list)
    filters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalResult:
    """A single retrieval result."""
    document: Document
    score: float
    rank: int
    method: RetrievalMethod = RetrievalMethod.BM25


@dataclass
class RetrievalResponse:
    """Response from retrieval."""
    query: Query
    results: List[RetrievalResult] = field(default_factory=list)
    total_docs: int = 0
    retrieval_time_ms: float = 0.0


@dataclass
class InvertedIndex:
    """Inverted index structure."""
    term_to_docs: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    term_frequencies: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(dict))
    document_frequencies: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    doc_lengths: Dict[str, int] = field(default_factory=dict)
    total_docs: int = 0
    avg_doc_length: float = 0.0


# =============================================================================
# TOKENIZER
# =============================================================================

class SimpleTokenizer:
    """Simple text tokenizer."""

    def __init__(self):
        self._stopwords = {
            "a", "an", "the", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "can", "and",
            "but", "or", "nor", "for", "so", "yet", "to", "of", "in",
            "on", "at", "by", "with", "from", "as", "into", "through",
            "during", "before", "after", "above", "below", "between",
            "under", "again", "further", "then", "once", "here", "there",
            "when", "where", "why", "how", "all", "each", "few", "more",
            "most", "other", "some", "such", "no", "not", "only", "own",
            "same", "than", "too", "very", "just", "this", "that", "these",
            "those", "it", "its", "if"
        }

    def tokenize(self, text: str) -> List[str]:
        """Tokenize text."""
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        tokens = text.split()
        return [t for t in tokens if t and t not in self._stopwords]

    def tokenize_with_stopwords(self, text: str) -> List[str]:
        """Tokenize without removing stopwords."""
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        return [t for t in text.split() if t]


# =============================================================================
# DOCUMENT STORE
# =============================================================================

class DocumentStore:
    """Store for documents."""

    def __init__(self):
        self._documents: Dict[str, Document] = {}
        self._tokenizer = SimpleTokenizer()

    def add(self, document: Document) -> None:
        """Add a document."""
        if not document.tokens:
            document.tokens = self._tokenizer.tokenize(document.content)
        self._documents[document.doc_id] = document

    def get(self, doc_id: str) -> Optional[Document]:
        """Get a document."""
        return self._documents.get(doc_id)

    def all_documents(self) -> List[Document]:
        """Get all documents."""
        return list(self._documents.values())

    def count(self) -> int:
        """Count documents."""
        return len(self._documents)

    def remove(self, doc_id: str) -> bool:
        """Remove a document."""
        if doc_id in self._documents:
            del self._documents[doc_id]
            return True
        return False


# =============================================================================
# INVERTED INDEX BUILDER
# =============================================================================

class InvertedIndexBuilder:
    """Build inverted index from documents."""

    def build(self, documents: List[Document]) -> InvertedIndex:
        """Build inverted index."""
        index = InvertedIndex()
        index.total_docs = len(documents)

        total_length = 0

        for doc in documents:
            tokens = doc.tokens
            doc_length = len(tokens)
            index.doc_lengths[doc.doc_id] = doc_length
            total_length += doc_length

            term_counts = Counter(tokens)

            for term, count in term_counts.items():
                index.term_to_docs[term].add(doc.doc_id)
                index.term_frequencies[term][doc.doc_id] = count

            for term in set(tokens):
                index.document_frequencies[term] += 1

        if documents:
            index.avg_doc_length = total_length / len(documents)

        return index


# =============================================================================
# BM25 RETRIEVER
# =============================================================================

class BM25Retriever:
    """BM25 retrieval algorithm."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self._k1 = k1
        self._b = b
        self._index: Optional[InvertedIndex] = None

    def index(self, documents: List[Document]) -> None:
        """Index documents."""
        builder = InvertedIndexBuilder()
        self._index = builder.build(documents)

    def _idf(self, term: str) -> float:
        """Calculate IDF for term."""
        if not self._index:
            return 0.0

        n = self._index.total_docs
        df = self._index.document_frequencies.get(term, 0)

        if df == 0:
            return 0.0

        return math.log((n - df + 0.5) / (df + 0.5) + 1)

    def _score_document(self, doc_id: str, query_terms: List[str]) -> float:
        """Score a document for query."""
        if not self._index:
            return 0.0

        doc_length = self._index.doc_lengths.get(doc_id, 0)
        avg_length = self._index.avg_doc_length

        score = 0.0

        for term in query_terms:
            if term not in self._index.term_frequencies:
                continue

            tf = self._index.term_frequencies[term].get(doc_id, 0)
            idf = self._idf(term)

            numerator = tf * (self._k1 + 1)
            denominator = tf + self._k1 * (1 - self._b + self._b * doc_length / avg_length)

            score += idf * numerator / denominator

        return score

    def retrieve(
        self,
        query_terms: List[str],
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """Retrieve documents for query."""
        if not self._index:
            return []

        candidate_docs = set()
        for term in query_terms:
            if term in self._index.term_to_docs:
                candidate_docs.update(self._index.term_to_docs[term])

        scores = []
        for doc_id in candidate_docs:
            score = self._score_document(doc_id, query_terms)
            scores.append((doc_id, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


# =============================================================================
# TF-IDF RETRIEVER
# =============================================================================

class TFIDFRetriever:
    """TF-IDF retrieval."""

    def __init__(self):
        self._index: Optional[InvertedIndex] = None

    def index(self, documents: List[Document]) -> None:
        """Index documents."""
        builder = InvertedIndexBuilder()
        self._index = builder.build(documents)

    def _tf(self, term: str, doc_id: str) -> float:
        """Calculate TF."""
        if not self._index:
            return 0.0

        tf = self._index.term_frequencies.get(term, {}).get(doc_id, 0)
        if tf == 0:
            return 0.0

        return 1 + math.log(tf)

    def _idf(self, term: str) -> float:
        """Calculate IDF."""
        if not self._index:
            return 0.0

        n = self._index.total_docs
        df = self._index.document_frequencies.get(term, 0)

        if df == 0:
            return 0.0

        return math.log(n / df)

    def retrieve(
        self,
        query_terms: List[str],
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """Retrieve documents."""
        if not self._index:
            return []

        candidate_docs = set()
        for term in query_terms:
            if term in self._index.term_to_docs:
                candidate_docs.update(self._index.term_to_docs[term])

        scores = []
        for doc_id in candidate_docs:
            score = 0.0
            for term in query_terms:
                tf = self._tf(term, doc_id)
                idf = self._idf(term)
                score += tf * idf
            scores.append((doc_id, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


# =============================================================================
# VECTOR RETRIEVER
# =============================================================================

class VectorRetriever:
    """Vector-based retrieval."""

    def __init__(self):
        self._documents: Dict[str, Document] = {}

    def index(self, documents: List[Document]) -> None:
        """Index documents with embeddings."""
        for doc in documents:
            if doc.embedding:
                self._documents[doc.doc_id] = doc

    def _cosine_similarity(
        self,
        v1: List[float],
        v2: List[float]
    ) -> float:
        """Calculate cosine similarity."""
        if len(v1) != len(v2):
            return 0.0

        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a ** 2 for a in v1))
        norm2 = math.sqrt(sum(b ** 2 for b in v2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot / (norm1 * norm2)

    def retrieve(
        self,
        query_embedding: List[float],
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """Retrieve by vector similarity."""
        scores = []

        for doc_id, doc in self._documents.items():
            sim = self._cosine_similarity(query_embedding, doc.embedding)
            scores.append((doc_id, sim))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


# =============================================================================
# HYBRID RETRIEVER
# =============================================================================

class HybridRetriever:
    """Hybrid retrieval combining multiple methods."""

    def __init__(self, alpha: float = 0.5):
        self._alpha = alpha
        self._bm25 = BM25Retriever()
        self._vector = VectorRetriever()

    def index(self, documents: List[Document]) -> None:
        """Index documents."""
        self._bm25.index(documents)
        self._vector.index(documents)

    def _normalize_scores(
        self,
        scores: List[Tuple[str, float]]
    ) -> Dict[str, float]:
        """Normalize scores to 0-1."""
        if not scores:
            return {}

        max_score = max(s for _, s in scores)
        min_score = min(s for _, s in scores)

        range_score = max_score - min_score
        if range_score == 0:
            return {doc_id: 0.5 for doc_id, _ in scores}

        return {
            doc_id: (score - min_score) / range_score
            for doc_id, score in scores
        }

    def retrieve(
        self,
        query_terms: List[str],
        query_embedding: List[float],
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """Hybrid retrieval."""
        bm25_results = self._bm25.retrieve(query_terms, top_k * 2)
        vector_results = self._vector.retrieve(query_embedding, top_k * 2)

        bm25_scores = self._normalize_scores(bm25_results)
        vector_scores = self._normalize_scores(vector_results)

        all_docs = set(bm25_scores.keys()) | set(vector_scores.keys())

        combined = []
        for doc_id in all_docs:
            bm25_s = bm25_scores.get(doc_id, 0)
            vector_s = vector_scores.get(doc_id, 0)
            combined_score = self._alpha * bm25_s + (1 - self._alpha) * vector_s
            combined.append((doc_id, combined_score))

        combined.sort(key=lambda x: x[1], reverse=True)
        return combined[:top_k]


# =============================================================================
# QUERY EXPANDER
# =============================================================================

class QueryExpander:
    """Expand queries with synonyms."""

    def __init__(self):
        self._synonyms = {
            "fast": ["quick", "rapid", "swift"],
            "big": ["large", "huge", "giant"],
            "small": ["tiny", "little", "mini"],
            "good": ["great", "excellent", "fine"],
            "bad": ["poor", "terrible", "awful"],
            "search": ["find", "look", "query"],
            "create": ["make", "build", "generate"]
        }

    def expand(
        self,
        terms: List[str],
        method: ExpansionMethod = ExpansionMethod.SYNONYMS
    ) -> List[str]:
        """Expand query terms."""
        if method == ExpansionMethod.NONE:
            return terms.copy()

        expanded = terms.copy()

        if method == ExpansionMethod.SYNONYMS:
            for term in terms:
                if term in self._synonyms:
                    expanded.extend(self._synonyms[term])

        return list(set(expanded))


# =============================================================================
# RESULT RE-RANKER
# =============================================================================

class ResultReranker:
    """Re-rank retrieval results."""

    def mmr(
        self,
        results: List[RetrievalResult],
        lambda_param: float = 0.5,
        top_k: int = 10
    ) -> List[RetrievalResult]:
        """Maximal Marginal Relevance re-ranking."""
        if not results:
            return []

        selected = [results[0]]
        remaining = results[1:]

        while len(selected) < top_k and remaining:
            best_score = float('-inf')
            best_idx = 0

            for i, candidate in enumerate(remaining):
                relevance = candidate.score

                max_sim = 0.0
                for sel in selected:
                    if candidate.document.embedding and sel.document.embedding:
                        sim = self._cosine_sim(
                            candidate.document.embedding,
                            sel.document.embedding
                        )
                        max_sim = max(max_sim, sim)

                mmr_score = lambda_param * relevance - (1 - lambda_param) * max_sim

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = i

            selected.append(remaining.pop(best_idx))

        for i, result in enumerate(selected):
            result.rank = i + 1

        return selected

    def _cosine_sim(
        self,
        v1: List[float],
        v2: List[float]
    ) -> float:
        """Calculate cosine similarity."""
        if len(v1) != len(v2):
            return 0.0

        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a ** 2 for a in v1))
        norm2 = math.sqrt(sum(b ** 2 for b in v2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot / (norm1 * norm2)


# =============================================================================
# RETRIEVAL ENGINE
# =============================================================================

class RetrievalEngine:
    """
    Retrieval Engine for BAEL.

    Advanced information retrieval for AI agents.
    """

    def __init__(self):
        self._store = DocumentStore()
        self._tokenizer = SimpleTokenizer()
        self._bm25 = BM25Retriever()
        self._tfidf = TFIDFRetriever()
        self._vector = VectorRetriever()
        self._hybrid = HybridRetriever()
        self._expander = QueryExpander()
        self._reranker = ResultReranker()
        self._indexed = False

    # -------------------------------------------------------------------------
    # INDEXING
    # -------------------------------------------------------------------------

    def add_document(
        self,
        content: str,
        title: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None
    ) -> Document:
        """Add a document."""
        tokens = self._tokenizer.tokenize(content)

        doc = Document(
            title=title,
            content=content,
            metadata=metadata or {},
            tokens=tokens,
            embedding=embedding or []
        )

        self._store.add(doc)
        self._indexed = False
        return doc

    def index(self) -> None:
        """Build indices."""
        documents = self._store.all_documents()

        self._bm25.index(documents)
        self._tfidf.index(documents)
        self._vector.index(documents)
        self._hybrid.index(documents)

        self._indexed = True

    # -------------------------------------------------------------------------
    # RETRIEVAL
    # -------------------------------------------------------------------------

    def retrieve(
        self,
        query_text: str,
        top_k: int = 10,
        method: RetrievalMethod = RetrievalMethod.BM25,
        expand: bool = False
    ) -> RetrievalResponse:
        """Retrieve documents."""
        import time
        start = time.time()

        if not self._indexed:
            self.index()

        tokens = self._tokenizer.tokenize(query_text)

        if expand:
            tokens = self._expander.expand(tokens)

        query = Query(text=query_text, tokens=tokens)

        if method == RetrievalMethod.BM25:
            raw_results = self._bm25.retrieve(tokens, top_k)
        elif method == RetrievalMethod.TF_IDF:
            raw_results = self._tfidf.retrieve(tokens, top_k)
        else:
            raw_results = self._bm25.retrieve(tokens, top_k)

        results = []
        for rank, (doc_id, score) in enumerate(raw_results, 1):
            doc = self._store.get(doc_id)
            if doc:
                results.append(RetrievalResult(
                    document=doc,
                    score=score,
                    rank=rank,
                    method=method
                ))

        elapsed = (time.time() - start) * 1000

        return RetrievalResponse(
            query=query,
            results=results,
            total_docs=self._store.count(),
            retrieval_time_ms=elapsed
        )

    def retrieve_hybrid(
        self,
        query_text: str,
        query_embedding: List[float],
        top_k: int = 10,
        alpha: float = 0.5
    ) -> RetrievalResponse:
        """Hybrid retrieval."""
        import time
        start = time.time()

        if not self._indexed:
            self.index()

        tokens = self._tokenizer.tokenize(query_text)
        query = Query(text=query_text, tokens=tokens, embedding=query_embedding)

        self._hybrid._alpha = alpha
        raw_results = self._hybrid.retrieve(tokens, query_embedding, top_k)

        results = []
        for rank, (doc_id, score) in enumerate(raw_results, 1):
            doc = self._store.get(doc_id)
            if doc:
                results.append(RetrievalResult(
                    document=doc,
                    score=score,
                    rank=rank,
                    method=RetrievalMethod.HYBRID
                ))

        elapsed = (time.time() - start) * 1000

        return RetrievalResponse(
            query=query,
            results=results,
            total_docs=self._store.count(),
            retrieval_time_ms=elapsed
        )

    def rerank_mmr(
        self,
        response: RetrievalResponse,
        lambda_param: float = 0.5
    ) -> RetrievalResponse:
        """Re-rank results with MMR."""
        reranked = self._reranker.mmr(response.results, lambda_param)

        return RetrievalResponse(
            query=response.query,
            results=reranked,
            total_docs=response.total_docs,
            retrieval_time_ms=response.retrieval_time_ms
        )

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def count_documents(self) -> int:
        """Count indexed documents."""
        return self._store.count()


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Retrieval Engine."""
    print("=" * 70)
    print("BAEL - RETRIEVAL ENGINE DEMO")
    print("Advanced Information Retrieval for AI Agents")
    print("=" * 70)
    print()

    engine = RetrievalEngine()

    # 1. Add Documents
    print("1. ADDING DOCUMENTS:")
    print("-" * 40)

    docs = [
        ("Machine learning basics", "Machine learning is a subset of artificial intelligence that enables systems to learn from data."),
        ("Deep learning guide", "Deep learning uses neural networks with many layers to model complex patterns in data."),
        ("Python programming", "Python is a versatile programming language widely used for data science and machine learning."),
        ("Data preprocessing", "Data preprocessing involves cleaning and transforming raw data before analysis."),
        ("Model evaluation", "Model evaluation helps assess the performance of machine learning models using metrics."),
        ("Feature engineering", "Feature engineering creates new features from existing data to improve model performance."),
        ("Neural network architecture", "Neural networks consist of layers of nodes that process and transform input data."),
        ("Natural language processing", "NLP enables computers to understand, interpret, and generate human language."),
        ("Computer vision", "Computer vision allows machines to interpret and understand visual information from images."),
        ("Reinforcement learning", "Reinforcement learning trains agents to make decisions by rewarding desired behaviors.")
    ]

    for title, content in docs:
        engine.add_document(content, title=title)
        print(f"   Added: {title}")

    print(f"   Total documents: {engine.count_documents()}")
    print()

    # 2. BM25 Retrieval
    print("2. BM25 RETRIEVAL:")
    print("-" * 40)

    query = "machine learning neural networks"
    response = engine.retrieve(query, top_k=5, method=RetrievalMethod.BM25)

    print(f"   Query: '{query}'")
    print(f"   Time: {response.retrieval_time_ms:.2f}ms")
    print(f"   Results:")
    for result in response.results:
        print(f"      {result.rank}. {result.document.title} (score: {result.score:.3f})")
    print()

    # 3. TF-IDF Retrieval
    print("3. TF-IDF RETRIEVAL:")
    print("-" * 40)

    query = "data preprocessing"
    response = engine.retrieve(query, top_k=5, method=RetrievalMethod.TF_IDF)

    print(f"   Query: '{query}'")
    print(f"   Time: {response.retrieval_time_ms:.2f}ms")
    print(f"   Results:")
    for result in response.results:
        print(f"      {result.rank}. {result.document.title} (score: {result.score:.3f})")
    print()

    # 4. Query Expansion
    print("4. QUERY EXPANSION:")
    print("-" * 40)

    query = "create fast search"

    response_no_expand = engine.retrieve(query, top_k=3, expand=False)
    response_expand = engine.retrieve(query, top_k=3, expand=True)

    print(f"   Query: '{query}'")
    print(f"   Without expansion: {len(response_no_expand.results)} results")
    print(f"   With expansion: {len(response_expand.results)} results")

    expander = QueryExpander()
    original = engine._tokenizer.tokenize(query)
    expanded = expander.expand(original)
    print(f"   Original terms: {original}")
    print(f"   Expanded terms: {expanded}")
    print()

    # 5. Different Queries
    print("5. DIFFERENT QUERIES:")
    print("-" * 40)

    queries = [
        "computer vision images",
        "language processing",
        "reinforcement agents"
    ]

    for q in queries:
        response = engine.retrieve(q, top_k=2)
        print(f"   '{q}':")
        for r in response.results:
            print(f"      - {r.document.title}")
    print()

    # 6. Statistics
    print("6. STATISTICS:")
    print("-" * 40)
    print(f"   Total documents: {engine.count_documents()}")
    print(f"   Indexed: {engine._indexed}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Retrieval Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
