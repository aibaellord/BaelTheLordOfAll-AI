"""
BAEL - Retrieval Augmented Generation Engine
Advanced RAG system with hybrid search and reranking.

Features:
- Hybrid search (dense + sparse)
- Document chunking strategies
- Reranking
- Query expansion
- Source attribution
- Streaming generation
"""

import asyncio
import hashlib
import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class ChunkingStrategy(Enum):
    """Document chunking strategies."""
    FIXED_SIZE = "fixed_size"
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    SEMANTIC = "semantic"
    SLIDING_WINDOW = "sliding_window"
    HIERARCHICAL = "hierarchical"


class SearchType(Enum):
    """Types of search."""
    DENSE = "dense"       # Embedding-based
    SPARSE = "sparse"     # Keyword-based (BM25)
    HYBRID = "hybrid"     # Combined


class RerankerType(Enum):
    """Types of rerankers."""
    NONE = "none"
    CROSS_ENCODER = "cross_encoder"
    LLM = "llm"
    RECIPROCAL_RANK_FUSION = "rrf"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Document:
    """A document for indexing."""
    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None

    @classmethod
    def create(cls, content: str, **metadata) -> "Document":
        doc_id = hashlib.md5(content[:100].encode()).hexdigest()[:12]
        return cls(id=doc_id, content=content, metadata=metadata)


@dataclass
class Chunk:
    """A chunk of a document."""
    id: str
    document_id: str
    content: str
    start_char: int
    end_char: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None

    @property
    def length(self) -> int:
        return len(self.content)


@dataclass
class SearchResult:
    """A search result."""
    chunk: Chunk
    score: float
    search_type: SearchType
    highlights: List[str] = field(default_factory=list)

    @property
    def document_id(self) -> str:
        return self.chunk.document_id


@dataclass
class RetrievalResult:
    """Complete retrieval result."""
    query: str
    results: List[SearchResult]
    total_results: int
    search_time_ms: float
    reranked: bool = False
    expanded_query: Optional[str] = None


@dataclass
class RAGResponse:
    """Response from RAG system."""
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float
    tokens_used: int
    retrieval_time_ms: float
    generation_time_ms: float


# =============================================================================
# CHUNKING ENGINE
# =============================================================================

class ChunkingEngine:
    """Splits documents into chunks."""

    def __init__(
        self,
        strategy: ChunkingStrategy = ChunkingStrategy.SENTENCE,
        chunk_size: int = 512,
        chunk_overlap: int = 50
    ):
        self.strategy = strategy
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(self, document: Document) -> List[Chunk]:
        """Chunk a document using the configured strategy."""
        if self.strategy == ChunkingStrategy.FIXED_SIZE:
            return self._chunk_fixed_size(document)
        elif self.strategy == ChunkingStrategy.SENTENCE:
            return self._chunk_by_sentence(document)
        elif self.strategy == ChunkingStrategy.PARAGRAPH:
            return self._chunk_by_paragraph(document)
        elif self.strategy == ChunkingStrategy.SLIDING_WINDOW:
            return self._chunk_sliding_window(document)
        else:
            return self._chunk_fixed_size(document)

    def _chunk_fixed_size(self, document: Document) -> List[Chunk]:
        """Chunk by fixed character size."""
        chunks = []
        content = document.content
        start = 0
        chunk_num = 0

        while start < len(content):
            end = min(start + self.chunk_size, len(content))

            chunk_id = f"{document.id}_chunk_{chunk_num}"
            chunks.append(Chunk(
                id=chunk_id,
                document_id=document.id,
                content=content[start:end],
                start_char=start,
                end_char=end,
                metadata={**document.metadata, "chunk_num": chunk_num}
            ))

            start = end - self.chunk_overlap
            chunk_num += 1

        return chunks

    def _chunk_by_sentence(self, document: Document) -> List[Chunk]:
        """Chunk by sentences, respecting size limits."""
        # Simple sentence splitting
        sentence_pattern = re.compile(r'(?<=[.!?])\s+')
        sentences = sentence_pattern.split(document.content)

        chunks = []
        current_chunk = []
        current_size = 0
        start_char = 0
        chunk_num = 0

        for sentence in sentences:
            sentence_len = len(sentence)

            if current_size + sentence_len > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_content = " ".join(current_chunk)
                chunk_id = f"{document.id}_chunk_{chunk_num}"
                chunks.append(Chunk(
                    id=chunk_id,
                    document_id=document.id,
                    content=chunk_content,
                    start_char=start_char,
                    end_char=start_char + len(chunk_content),
                    metadata={**document.metadata, "chunk_num": chunk_num}
                ))

                start_char += len(chunk_content) + 1
                chunk_num += 1
                current_chunk = []
                current_size = 0

            current_chunk.append(sentence)
            current_size += sentence_len + 1

        # Final chunk
        if current_chunk:
            chunk_content = " ".join(current_chunk)
            chunk_id = f"{document.id}_chunk_{chunk_num}"
            chunks.append(Chunk(
                id=chunk_id,
                document_id=document.id,
                content=chunk_content,
                start_char=start_char,
                end_char=start_char + len(chunk_content),
                metadata={**document.metadata, "chunk_num": chunk_num}
            ))

        return chunks

    def _chunk_by_paragraph(self, document: Document) -> List[Chunk]:
        """Chunk by paragraphs."""
        paragraphs = document.content.split("\n\n")
        chunks = []
        start_char = 0

        for i, para in enumerate(paragraphs):
            para = para.strip()
            if not para:
                continue

            chunk_id = f"{document.id}_chunk_{i}"
            chunks.append(Chunk(
                id=chunk_id,
                document_id=document.id,
                content=para,
                start_char=start_char,
                end_char=start_char + len(para),
                metadata={**document.metadata, "chunk_num": i}
            ))

            start_char += len(para) + 2

        return chunks

    def _chunk_sliding_window(self, document: Document) -> List[Chunk]:
        """Chunk with sliding window."""
        chunks = []
        content = document.content
        window_size = self.chunk_size
        step_size = window_size - self.chunk_overlap

        for i, start in enumerate(range(0, len(content), step_size)):
            end = min(start + window_size, len(content))

            chunk_id = f"{document.id}_chunk_{i}"
            chunks.append(Chunk(
                id=chunk_id,
                document_id=document.id,
                content=content[start:end],
                start_char=start,
                end_char=end,
                metadata={**document.metadata, "chunk_num": i}
            ))

            if end >= len(content):
                break

        return chunks


# =============================================================================
# EMBEDDING ENGINE
# =============================================================================

class EmbeddingEngine:
    """Generates embeddings for text."""

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        dimensions: int = 1536
    ):
        self.model = model
        self.dimensions = dimensions
        self._client = None

    async def embed(self, text: str) -> List[float]:
        """Generate embedding for text."""
        # Would call OpenAI or local model
        # Placeholder: return mock embedding
        import random
        return [random.random() for _ in range(min(self.dimensions, 384))]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        return [await self.embed(text) for text in texts]

    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity."""
        import math

        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)


# =============================================================================
# SPARSE SEARCH (BM25)
# =============================================================================

class BM25Index:
    """BM25 sparse retrieval index."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents: Dict[str, Chunk] = {}
        self.doc_lengths: Dict[str, int] = {}
        self.avg_doc_length: float = 0.0
        self.term_frequencies: Dict[str, Dict[str, int]] = {}  # term -> doc_id -> freq
        self.doc_frequencies: Dict[str, int] = {}  # term -> num docs containing

    def add_document(self, chunk: Chunk) -> None:
        """Add a document to the index."""
        self.documents[chunk.id] = chunk
        tokens = self._tokenize(chunk.content)
        self.doc_lengths[chunk.id] = len(tokens)

        # Update term frequencies
        term_counts: Dict[str, int] = {}
        for token in tokens:
            term_counts[token] = term_counts.get(token, 0) + 1

        for term, count in term_counts.items():
            if term not in self.term_frequencies:
                self.term_frequencies[term] = {}
            self.term_frequencies[term][chunk.id] = count

            if term not in self.doc_frequencies:
                self.doc_frequencies[term] = 0
            self.doc_frequencies[term] += 1

        # Update average document length
        total_length = sum(self.doc_lengths.values())
        self.avg_doc_length = total_length / len(self.documents) if self.documents else 0

    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Search the index."""
        import math

        query_tokens = self._tokenize(query)
        scores: Dict[str, float] = {}

        num_docs = len(self.documents)

        for token in query_tokens:
            if token not in self.term_frequencies:
                continue

            df = self.doc_frequencies.get(token, 0)
            idf = math.log((num_docs - df + 0.5) / (df + 0.5) + 1)

            for doc_id, tf in self.term_frequencies[token].items():
                doc_length = self.doc_lengths[doc_id]

                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (
                    1 - self.b + self.b * doc_length / self.avg_doc_length
                )

                score = idf * numerator / denominator
                scores[doc_id] = scores.get(doc_id, 0) + score

        # Sort by score
        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_results[:top_k]

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization."""
        # Lowercase, split on non-alphanumeric
        tokens = re.findall(r'\b\w+\b', text.lower())
        # Remove stopwords (simplified)
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being'}
        return [t for t in tokens if t not in stopwords and len(t) > 2]


# =============================================================================
# VECTOR STORE
# =============================================================================

class VectorStore:
    """In-memory vector store."""

    def __init__(self, embedding_engine: EmbeddingEngine):
        self.embedding_engine = embedding_engine
        self.chunks: Dict[str, Chunk] = {}
        self.embeddings: Dict[str, List[float]] = {}

    async def add(self, chunk: Chunk) -> None:
        """Add a chunk to the store."""
        if chunk.embedding is None:
            chunk.embedding = await self.embedding_engine.embed(chunk.content)

        self.chunks[chunk.id] = chunk
        self.embeddings[chunk.id] = chunk.embedding

    async def search(
        self,
        query: str,
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """Search by semantic similarity."""
        query_embedding = await self.embedding_engine.embed(query)

        scores = []
        for chunk_id, embedding in self.embeddings.items():
            similarity = self.embedding_engine.cosine_similarity(
                query_embedding,
                embedding
            )
            scores.append((chunk_id, similarity))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def get_chunk(self, chunk_id: str) -> Optional[Chunk]:
        """Get a chunk by ID."""
        return self.chunks.get(chunk_id)


# =============================================================================
# HYBRID RETRIEVER
# =============================================================================

class HybridRetriever:
    """Combines dense and sparse retrieval."""

    def __init__(
        self,
        vector_store: VectorStore,
        bm25_index: BM25Index,
        dense_weight: float = 0.7,
        sparse_weight: float = 0.3
    ):
        self.vector_store = vector_store
        self.bm25_index = bm25_index
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight

    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
        search_type: SearchType = SearchType.HYBRID
    ) -> List[SearchResult]:
        """Retrieve relevant chunks."""
        import time
        start = time.time()

        results = []

        if search_type in [SearchType.DENSE, SearchType.HYBRID]:
            # Dense search
            dense_results = await self.vector_store.search(query, top_k * 2)
            for chunk_id, score in dense_results:
                chunk = self.vector_store.get_chunk(chunk_id)
                if chunk:
                    results.append(SearchResult(
                        chunk=chunk,
                        score=score * self.dense_weight,
                        search_type=SearchType.DENSE
                    ))

        if search_type in [SearchType.SPARSE, SearchType.HYBRID]:
            # Sparse search
            sparse_results = self.bm25_index.search(query, top_k * 2)
            for chunk_id, score in sparse_results:
                chunk = self.bm25_index.documents.get(chunk_id)
                if chunk:
                    # Check if already in results
                    existing = next(
                        (r for r in results if r.chunk.id == chunk_id),
                        None
                    )
                    if existing:
                        # Combine scores
                        existing.score += score * self.sparse_weight
                    else:
                        results.append(SearchResult(
                            chunk=chunk,
                            score=score * self.sparse_weight,
                            search_type=SearchType.SPARSE
                        ))

        # Sort by combined score
        results.sort(key=lambda x: x.score, reverse=True)

        return results[:top_k]


# =============================================================================
# RERANKER
# =============================================================================

class Reranker:
    """Reranks search results."""

    def __init__(
        self,
        reranker_type: RerankerType = RerankerType.RECIPROCAL_RANK_FUSION,
        llm_client: Optional[Any] = None
    ):
        self.reranker_type = reranker_type
        self.llm_client = llm_client

    async def rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_k: int = 5
    ) -> List[SearchResult]:
        """Rerank results."""
        if self.reranker_type == RerankerType.NONE:
            return results[:top_k]

        elif self.reranker_type == RerankerType.RECIPROCAL_RANK_FUSION:
            return self._rrf_rerank(results, top_k)

        elif self.reranker_type == RerankerType.LLM and self.llm_client:
            return await self._llm_rerank(query, results, top_k)

        return results[:top_k]

    def _rrf_rerank(
        self,
        results: List[SearchResult],
        top_k: int,
        k: int = 60
    ) -> List[SearchResult]:
        """Reciprocal Rank Fusion reranking."""
        # Group by search type
        dense_results = [r for r in results if r.search_type == SearchType.DENSE]
        sparse_results = [r for r in results if r.search_type == SearchType.SPARSE]

        # Calculate RRF scores
        rrf_scores: Dict[str, float] = {}

        for i, result in enumerate(dense_results):
            chunk_id = result.chunk.id
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + 1 / (k + i + 1)

        for i, result in enumerate(sparse_results):
            chunk_id = result.chunk.id
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + 1 / (k + i + 1)

        # Update scores
        for result in results:
            result.score = rrf_scores.get(result.chunk.id, 0)

        # Sort and deduplicate
        seen = set()
        unique_results = []
        for result in sorted(results, key=lambda x: x.score, reverse=True):
            if result.chunk.id not in seen:
                seen.add(result.chunk.id)
                unique_results.append(result)

        return unique_results[:top_k]

    async def _llm_rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_k: int
    ) -> List[SearchResult]:
        """LLM-based reranking."""
        # Would call LLM to rerank
        return results[:top_k]


# =============================================================================
# RAG ENGINE
# =============================================================================

class RAGEngine:
    """Complete RAG pipeline."""

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        chunking_strategy: ChunkingStrategy = ChunkingStrategy.SENTENCE,
        search_type: SearchType = SearchType.HYBRID,
        reranker_type: RerankerType = RerankerType.RECIPROCAL_RANK_FUSION
    ):
        self.llm_client = llm_client
        self.embedding_engine = EmbeddingEngine()
        self.chunking_engine = ChunkingEngine(strategy=chunking_strategy)
        self.vector_store = VectorStore(self.embedding_engine)
        self.bm25_index = BM25Index()
        self.retriever = HybridRetriever(self.vector_store, self.bm25_index)
        self.reranker = Reranker(reranker_type, llm_client)
        self.search_type = search_type

        self.documents: Dict[str, Document] = {}

    async def add_document(self, document: Document) -> int:
        """Add a document to the RAG system."""
        self.documents[document.id] = document

        # Chunk document
        chunks = self.chunking_engine.chunk_document(document)

        # Add to stores
        for chunk in chunks:
            await self.vector_store.add(chunk)
            self.bm25_index.add_document(chunk)

        logger.info(f"Added document {document.id} with {len(chunks)} chunks")
        return len(chunks)

    async def add_text(self, text: str, **metadata) -> int:
        """Add text as a document."""
        doc = Document.create(text, **metadata)
        return await self.add_document(doc)

    async def retrieve(
        self,
        query: str,
        top_k: int = 5
    ) -> RetrievalResult:
        """Retrieve relevant context."""
        import time
        start = time.time()

        # Search
        results = await self.retriever.retrieve(
            query,
            top_k * 2,  # Get more for reranking
            self.search_type
        )

        # Rerank
        reranked = await self.reranker.rerank(query, results, top_k)

        elapsed = (time.time() - start) * 1000

        return RetrievalResult(
            query=query,
            results=reranked,
            total_results=len(reranked),
            search_time_ms=elapsed,
            reranked=True
        )

    async def generate(
        self,
        query: str,
        top_k: int = 5,
        max_tokens: int = 1024
    ) -> RAGResponse:
        """Retrieve and generate answer."""
        import time

        # Retrieve
        retrieval_start = time.time()
        retrieval = await self.retrieve(query, top_k)
        retrieval_time = (time.time() - retrieval_start) * 1000

        # Build context
        context_parts = []
        sources = []

        for i, result in enumerate(retrieval.results):
            context_parts.append(f"[{i+1}] {result.chunk.content}")
            sources.append({
                "id": result.chunk.id,
                "document_id": result.chunk.document_id,
                "score": result.score,
                "excerpt": result.chunk.content[:100] + "..."
            })

        context = "\n\n".join(context_parts)

        # Generate
        generation_start = time.time()

        if self.llm_client:
            prompt = f"""Answer the question based on the provided context.
If the context doesn't contain relevant information, say so.
Cite sources using [1], [2], etc.

Context:
{context}

Question: {query}

Answer:"""

            # Would call LLM here
            answer = f"[Generated answer for: {query}]"
            tokens = len(prompt.split()) + len(answer.split())
        else:
            answer = f"Based on {len(sources)} sources, the answer relates to: {query}"
            tokens = 0

        generation_time = (time.time() - generation_start) * 1000

        return RAGResponse(
            answer=answer,
            sources=sources,
            confidence=0.8,
            tokens_used=tokens,
            retrieval_time_ms=retrieval_time,
            generation_time_ms=generation_time
        )

    async def stream_generate(
        self,
        query: str,
        top_k: int = 5
    ) -> AsyncGenerator[str, None]:
        """Stream generated response."""
        # Retrieve
        retrieval = await self.retrieve(query, top_k)

        # Would stream from LLM
        # Placeholder: yield chunks
        response = f"Streaming answer for: {query}..."

        for word in response.split():
            yield word + " "
            await asyncio.sleep(0.05)


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

async def example_rag():
    """Demonstrate RAG capabilities."""
    rag = RAGEngine()

    # Add documents
    await rag.add_text(
        "BAEL is the most advanced AI agent system ever created. "
        "It features multi-model orchestration, hierarchical memory, "
        "and advanced reasoning capabilities.",
        source="bael_docs",
        title="Overview"
    )

    await rag.add_text(
        "The memory system in BAEL consists of five layers: "
        "episodic memory for experiences, semantic memory for knowledge, "
        "procedural memory for skills, working memory for context, "
        "and vector memory for similarity search.",
        source="bael_docs",
        title="Memory"
    )

    await rag.add_text(
        "BAEL supports multiple reasoning strategies including "
        "Chain of Thought, Tree of Thoughts, and Graph of Thoughts. "
        "It can adapt its reasoning based on task complexity.",
        source="bael_docs",
        title="Reasoning"
    )

    # Query
    result = await rag.retrieve("How does BAEL's memory system work?")
    print(f"Retrieved {len(result.results)} results in {result.search_time_ms:.2f}ms")

    for i, r in enumerate(result.results):
        print(f"\n[{i+1}] Score: {r.score:.3f}")
        print(f"    {r.chunk.content[:100]}...")

    # Generate
    response = await rag.generate("Explain BAEL's reasoning capabilities")
    print(f"\nAnswer: {response.answer}")
    print(f"Sources: {len(response.sources)}")


if __name__ == "__main__":
    asyncio.run(example_rag())
