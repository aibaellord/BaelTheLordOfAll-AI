"""
BAEL Storage Engine
===================

Multi-backend storage with intelligent caching and querying.
"""

from .storage import (
    # Enums
    StorageBackend,
    DataFormat,
    IndexType,
    QueryOperator,

    # Dataclasses
    StorageConfig,
    Document,
    Collection,
    QueryFilter,
    QueryResult,

    # Classes
    StorageEngine,
    DocumentStore,
    KeyValueStore,
    TimeSeriesStore,
    VectorStore,

    # Instance
    storage_engine
)

__all__ = [
    "StorageBackend",
    "DataFormat",
    "IndexType",
    "QueryOperator",
    "StorageConfig",
    "Document",
    "Collection",
    "QueryFilter",
    "QueryResult",
    "StorageEngine",
    "DocumentStore",
    "KeyValueStore",
    "TimeSeriesStore",
    "VectorStore",
    "storage_engine"
]
