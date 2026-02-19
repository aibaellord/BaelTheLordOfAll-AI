"""
BAEL Search Engine
==================

Full-text search, indexing, and ranking.

"Ba'el finds all knowledge instantly." — Ba'el
"""

from core.search_engine.search_engine import (
    # Enums
    IndexType,
    TokenizerType,
    ScoringAlgorithm,
    QueryType,

    # Data structures
    Document,
    SearchResult,
    SearchQuery,
    IndexConfig,
    SearchConfig,

    # Classes
    SearchEngine,
    Tokenizer,
    InvertedIndex,
    DocumentStore,
    QueryParser,
    Scorer,

    # Instance
    search_engine
)

__all__ = [
    # Enums
    'IndexType',
    'TokenizerType',
    'ScoringAlgorithm',
    'QueryType',

    # Data structures
    'Document',
    'SearchResult',
    'SearchQuery',
    'IndexConfig',
    'SearchConfig',

    # Classes
    'SearchEngine',
    'Tokenizer',
    'InvertedIndex',
    'DocumentStore',
    'QueryParser',
    'Scorer',

    # Instance
    'search_engine'
]
