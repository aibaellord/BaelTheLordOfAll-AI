"""
BAEL - Vector Memory Module
Embedding-based storage and semantic similarity search.
"""

from .vector_memory import (DistanceMetric, SearchResult, VectorEntry,
                            VectorMemoryManager, VectorMemoryStore, VectorOps,
                            VectorStats)

__all__ = [
    "DistanceMetric",
    "VectorEntry",
    "SearchResult",
    "VectorStats",
    "VectorOps",
    "VectorMemoryStore",
    "VectorMemoryManager"
]
