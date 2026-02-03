"""
BAEL Persistence Package

Unified persistence layer with multi-backend support:
- SQLite (local, zero-config)
- PostgreSQL (production scale)
- Redis (caching)
- File-based (large objects)
- In-memory (testing)
"""

from .persistence_layer import (DataCategory, FileProvider, MemoryProvider,
                                PersistenceLayer, SQLiteProvider,
                                StorageBackend, StorageConfig, StorageProvider,
                                StoredItem, get_persistence)

__all__ = [
    "PersistenceLayer",
    "StorageConfig",
    "StorageBackend",
    "DataCategory",
    "StoredItem",
    "StorageProvider",
    "MemoryProvider",
    "SQLiteProvider",
    "FileProvider",
    "get_persistence"
]
