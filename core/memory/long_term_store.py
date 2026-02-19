"""
BAEL Long-Term Store
=====================

Persistent storage for AI agent memories.
Manages indexed long-term memory storage.

Features:
- Multiple storage backends
- Indexed retrieval
- Compression strategies
- Distributed storage
- Backup/restore
"""

import asyncio
import base64
import gzip
import hashlib
import json
import logging
import os
import pickle
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


class CompressionStrategy(Enum):
    """Compression strategies."""
    NONE = "none"
    GZIP = "gzip"
    LZ4 = "lz4"
    ZSTD = "zstd"
    SEMANTIC = "semantic"  # Summarization-based


class StorageType(Enum):
    """Storage backend types."""
    MEMORY = "memory"
    FILE = "file"
    SQLITE = "sqlite"
    REDIS = "redis"
    VECTOR_DB = "vector_db"


@dataclass
class StorageEntry:
    """An entry in long-term storage."""
    key: str
    value: Any

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0

    # Index keys
    index_keys: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    # Storage info
    compressed: bool = False
    compression: CompressionStrategy = CompressionStrategy.NONE
    size_bytes: int = 0

    # TTL
    expires_at: Optional[datetime] = None


@dataclass
class MemoryIndex:
    """Index for memory retrieval."""
    name: str

    # Index type
    index_type: str = "hash"  # hash, btree, inverted

    # Mappings
    key_to_entries: Dict[str, Set[str]] = field(default_factory=dict)

    def add(self, key: str, entry_key: str) -> None:
        """Add entry to index."""
        if key not in self.key_to_entries:
            self.key_to_entries[key] = set()
        self.key_to_entries[key].add(entry_key)

    def remove(self, key: str, entry_key: str) -> None:
        """Remove entry from index."""
        if key in self.key_to_entries:
            self.key_to_entries[key].discard(entry_key)

    def lookup(self, key: str) -> Set[str]:
        """Look up entries by key."""
        return self.key_to_entries.get(key, set())


class StorageBackend(ABC):
    """Abstract storage backend."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value by key."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, **kwargs) -> bool:
        """Set value."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        pass

    @abstractmethod
    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        pass


class MemoryBackend(StorageBackend):
    """In-memory storage backend."""

    def __init__(self):
        self._store: Dict[str, Any] = {}

    async def get(self, key: str) -> Optional[Any]:
        return self._store.get(key)

    async def set(self, key: str, value: Any, **kwargs) -> bool:
        self._store[key] = value
        return True

    async def delete(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]
            return True
        return False

    async def exists(self, key: str) -> bool:
        return key in self._store

    async def keys(self, pattern: str = "*") -> List[str]:
        import fnmatch
        if pattern == "*":
            return list(self._store.keys())
        return [k for k in self._store.keys() if fnmatch.fnmatch(k, pattern)]


class FileBackend(StorageBackend):
    """File-based storage backend."""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _key_to_path(self, key: str) -> Path:
        """Convert key to file path."""
        safe_key = hashlib.md5(key.encode()).hexdigest()
        return self.base_path / f"{safe_key}.pkl"

    async def get(self, key: str) -> Optional[Any]:
        path = self._key_to_path(key)
        if path.exists():
            with open(path, "rb") as f:
                return pickle.load(f)
        return None

    async def set(self, key: str, value: Any, **kwargs) -> bool:
        path = self._key_to_path(key)
        with open(path, "wb") as f:
            pickle.dump(value, f)
        return True

    async def delete(self, key: str) -> bool:
        path = self._key_to_path(key)
        if path.exists():
            path.unlink()
            return True
        return False

    async def exists(self, key: str) -> bool:
        return self._key_to_path(key).exists()

    async def keys(self, pattern: str = "*") -> List[str]:
        # Would need key mapping for full implementation
        return [p.stem for p in self.base_path.glob("*.pkl")]


class LongTermStore:
    """
    Long-term memory storage for BAEL.

    Manages persistent memory with indexing and compression.
    """

    def __init__(
        self,
        backend: Optional[StorageBackend] = None,
        compression: CompressionStrategy = CompressionStrategy.GZIP,
    ):
        self.backend = backend or MemoryBackend()
        self.compression = compression

        # Indices
        self._indices: Dict[str, MemoryIndex] = {}

        # Entry metadata (kept in memory for fast access)
        self._metadata: Dict[str, StorageEntry] = {}

        # Stats
        self.stats = {
            "entries_stored": 0,
            "entries_retrieved": 0,
            "bytes_stored": 0,
            "bytes_compressed": 0,
        }

    def create_index(
        self,
        name: str,
        index_type: str = "hash",
    ) -> MemoryIndex:
        """Create an index."""
        index = MemoryIndex(name=name, index_type=index_type)
        self._indices[name] = index
        return index

    async def store(
        self,
        key: str,
        value: Any,
        index_keys: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        ttl_seconds: Optional[int] = None,
        compress: bool = True,
    ) -> StorageEntry:
        """
        Store a value in long-term memory.

        Args:
            key: Storage key
            value: Value to store
            index_keys: Keys for indexing
            tags: Value tags
            ttl_seconds: Time-to-live
            compress: Whether to compress

        Returns:
            Storage entry
        """
        # Serialize value
        serialized = self._serialize(value)
        original_size = len(serialized)

        # Compress if needed
        compressed = False
        if compress and self.compression != CompressionStrategy.NONE:
            serialized = self._compress(serialized)
            compressed = True

        # Create entry
        entry = StorageEntry(
            key=key,
            value=value,
            index_keys=index_keys or [],
            tags=tags or [],
            compressed=compressed,
            compression=self.compression if compressed else CompressionStrategy.NONE,
            size_bytes=len(serialized),
        )

        if ttl_seconds:
            from datetime import timedelta
            entry.expires_at = datetime.now() + timedelta(seconds=ttl_seconds)

        # Store
        await self.backend.set(key, serialized)
        self._metadata[key] = entry

        # Update indices
        for idx_key in entry.index_keys:
            for index in self._indices.values():
                index.add(idx_key, key)

        for tag in entry.tags:
            if "tags" not in self._indices:
                self.create_index("tags")
            self._indices["tags"].add(tag, key)

        # Stats
        self.stats["entries_stored"] += 1
        self.stats["bytes_stored"] += original_size
        self.stats["bytes_compressed"] += len(serialized)

        logger.debug(f"Stored in long-term: {key}")

        return entry

    async def retrieve(
        self,
        key: str,
    ) -> Optional[Any]:
        """Retrieve a value."""
        if key not in self._metadata:
            return None

        entry = self._metadata[key]

        # Check expiration
        if entry.expires_at and datetime.now() > entry.expires_at:
            await self.delete(key)
            return None

        # Get from backend
        serialized = await self.backend.get(key)
        if serialized is None:
            return None

        # Decompress if needed
        if entry.compressed:
            serialized = self._decompress(serialized)

        # Deserialize
        value = self._deserialize(serialized)

        # Update access stats
        entry.access_count += 1
        entry.updated_at = datetime.now()

        self.stats["entries_retrieved"] += 1

        return value

    async def delete(self, key: str) -> bool:
        """Delete an entry."""
        if key not in self._metadata:
            return False

        entry = self._metadata[key]

        # Remove from indices
        for idx_key in entry.index_keys:
            for index in self._indices.values():
                index.remove(idx_key, key)

        for tag in entry.tags:
            if "tags" in self._indices:
                self._indices["tags"].remove(tag, key)

        # Delete from backend
        await self.backend.delete(key)
        del self._metadata[key]

        return True

    async def search_by_index(
        self,
        index_name: str,
        key: str,
    ) -> List[Any]:
        """Search using an index."""
        if index_name not in self._indices:
            return []

        index = self._indices[index_name]
        entry_keys = index.lookup(key)

        results = []
        for entry_key in entry_keys:
            value = await self.retrieve(entry_key)
            if value is not None:
                results.append(value)

        return results

    async def search_by_tags(
        self,
        tags: List[str],
        match_all: bool = False,
    ) -> List[Any]:
        """Search by tags."""
        if "tags" not in self._indices:
            return []

        tag_index = self._indices["tags"]

        if match_all:
            # Intersection
            entry_sets = [tag_index.lookup(tag) for tag in tags]
            if not entry_sets:
                return []
            matching_keys = set.intersection(*entry_sets)
        else:
            # Union
            matching_keys = set()
            for tag in tags:
                matching_keys.update(tag_index.lookup(tag))

        results = []
        for key in matching_keys:
            value = await self.retrieve(key)
            if value is not None:
                results.append(value)

        return results

    def _serialize(self, value: Any) -> bytes:
        """Serialize a value."""
        return pickle.dumps(value)

    def _deserialize(self, data: bytes) -> Any:
        """Deserialize a value."""
        return pickle.loads(data)

    def _compress(self, data: bytes) -> bytes:
        """Compress data."""
        if self.compression == CompressionStrategy.GZIP:
            return gzip.compress(data)
        return data

    def _decompress(self, data: bytes) -> bytes:
        """Decompress data."""
        if self.compression == CompressionStrategy.GZIP:
            return gzip.decompress(data)
        return data

    async def vacuum(self) -> int:
        """Remove expired entries."""
        now = datetime.now()
        expired = []

        for key, entry in self._metadata.items():
            if entry.expires_at and now > entry.expires_at:
                expired.append(key)

        for key in expired:
            await self.delete(key)

        return len(expired)

    async def backup(self, path: str) -> bool:
        """Backup store to file."""
        try:
            backup_data = {
                "metadata": {k: self._entry_to_dict(v) for k, v in self._metadata.items()},
                "indices": {
                    name: {k: list(v) for k, v in idx.key_to_entries.items()}
                    for name, idx in self._indices.items()
                },
            }

            with gzip.open(path, "wt") as f:
                json.dump(backup_data, f)

            return True
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return False

    def _entry_to_dict(self, entry: StorageEntry) -> Dict[str, Any]:
        """Convert entry to dict for serialization."""
        return {
            "key": entry.key,
            "created_at": entry.created_at.isoformat(),
            "updated_at": entry.updated_at.isoformat(),
            "access_count": entry.access_count,
            "index_keys": entry.index_keys,
            "tags": entry.tags,
            "size_bytes": entry.size_bytes,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        compression_ratio = (
            self.stats["bytes_compressed"] / self.stats["bytes_stored"]
            if self.stats["bytes_stored"] > 0 else 1.0
        )

        return {
            **self.stats,
            "total_entries": len(self._metadata),
            "indices": len(self._indices),
            "compression_ratio": compression_ratio,
        }


def demo():
    """Demonstrate long-term store."""
    import asyncio

    print("=" * 60)
    print("BAEL Long-Term Store Demo")
    print("=" * 60)

    async def run_demo():
        store = LongTermStore(compression=CompressionStrategy.GZIP)

        # Create indices
        store.create_index("topic")
        store.create_index("type")

        # Store entries
        print("\nStoring entries...")

        await store.store(
            "memory_001",
            {"event": "learned Python decorators", "importance": 0.8},
            index_keys=["python", "learning"],
            tags=["python", "decorators", "learning"],
        )

        await store.store(
            "memory_002",
            {"event": "debugged async race condition", "importance": 0.9},
            index_keys=["debugging", "async"],
            tags=["debugging", "async", "important"],
        )

        await store.store(
            "memory_003",
            {"event": "built web scraper", "importance": 0.7},
            index_keys=["python", "web"],
            tags=["python", "scraping", "project"],
        )

        print(f"  Stored {store.stats['entries_stored']} entries")

        # Retrieve
        print("\nRetrieving...")
        value = await store.retrieve("memory_001")
        print(f"  memory_001: {value}")

        # Search by tags
        print("\nSearching by tags...")
        results = await store.search_by_tags(["python"])
        print(f"  Tag 'python': {len(results)} results")

        results = await store.search_by_tags(["python", "debugging"], match_all=True)
        print(f"  Tags 'python' AND 'debugging': {len(results)} results")

        # Stats
        print(f"\nStats: {store.get_stats()}")

        # Compression info
        stats = store.get_stats()
        print(f"\nCompression ratio: {stats['compression_ratio']:.2%}")

    asyncio.run(run_demo())


if __name__ == "__main__":
    demo()
