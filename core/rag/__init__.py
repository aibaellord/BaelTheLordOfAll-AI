"""
BAEL - Retrieval Augmented Generation (RAG) System
Comprehensive RAG implementation for knowledge-grounded generation.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("BAEL.RAG")


class ChunkingStrategy(Enum):
    """Document chunking strategies."""
    FIXED_SIZE = "fixed_size"
    SEMANTIC = "semantic"
    PARAGRAPH = "paragraph"
    SENTENCE = "sentence"
    RECURSIVE = "recursive"


class SearchMode(Enum):
    """Search modes for retrieval."""
    VECTOR = "vector"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


@dataclass
class Document:
    """A document for RAG."""
    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


@dataclass
class Chunk:
    """A document chunk."""
    id: str
    document_id: str
    content: str
    start_index: int
    end_index: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


@dataclass
class RetrievalResult:
    """Result from retrieval."""
    chunks: List[Chunk]
    query: str
    scores: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RAGResponse:
    """Response from RAG pipeline."""
    answer: str
    sources: List[Chunk]
    confidence: float
    reasoning: Optional[str] = None


# Import main RAG engine if available
try:
    from .rag_engine import RAGConfig, RAGEngine
    __all__ = [
        "ChunkingStrategy",
        "SearchMode",
        "Document",
        "Chunk",
        "RetrievalResult",
        "RAGResponse",
        "RAGEngine",
        "RAGConfig"
    ]
except ImportError:
    __all__ = [
        "ChunkingStrategy",
        "SearchMode",
        "Document",
        "Chunk",
        "RetrievalResult",
        "RAGResponse"
    ]
    logger.warning("RAG engine not fully loaded")
