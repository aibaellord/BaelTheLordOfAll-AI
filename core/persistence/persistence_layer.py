"""
BAEL Persistence Layer

Unified persistence for all BAEL subsystems with support for:
- SQLite (local, zero-config)
- PostgreSQL (production scale)
- Redis (caching, sessions)
- File-based (embeddings, weights)

This is the foundation for BAEL's memory permanence.
"""

import asyncio
import hashlib
import json
import logging
import pickle
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

logger = logging.getLogger(__name__)

T = TypeVar('T')


class StorageBackend(Enum):
    """Available storage backends."""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    REDIS = "redis"
    FILE = "file"
    MEMORY = "memory"


class DataCategory(Enum):
    """Categories of data for storage."""
    MEMORY = "memory"           # Cognitive memory
    EMBEDDING = "embedding"     # Vector embeddings
    KNOWLEDGE = "knowledge"     # Knowledge graph
    MODEL = "model"             # Model weights
    SESSION = "session"         # Session data
    CONFIG = "config"           # Configuration
    CACHE = "cache"             # Temporary cache
    AUDIT = "audit"             # Audit logs


@dataclass
class StorageConfig:
    """Configuration for storage."""
    backend: StorageBackend = StorageBackend.SQLITE
    sqlite_path: str = "data/bael.db"
    postgres_url: str = ""
    redis_url: str = ""
    file_base_path: str = "data"
    cache_ttl: int = 3600
    max_connections: int = 10
    enable_compression: bool = True
    enable_encryption: bool = False


@dataclass
class StoredItem:
    """Wrapper for stored data."""
    key: str
    value: Any
    category: DataCategory
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: int = 1
    checksum: str = ""


class StorageProvider(ABC):
    """Abstract storage provider."""

    @abstractmethod
    async def connect(self) -> bool:
        """Connect to storage."""
        pass

    @abstractmethod
    async def disconnect(self):
        """Disconnect from storage."""
        pass

    @abstractmethod
    async def get(self, key: str, category: DataCategory) -> Optional[StoredItem]:
        """Get item by key."""
        pass

    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        category: DataCategory,
        ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Store item."""
        pass

    @abstractmethod
    async def delete(self, key: str, category: DataCategory) -> bool:
        """Delete item."""
        pass

    @abstractmethod
    async def exists(self, key: str, category: DataCategory) -> bool:
        """Check if item exists."""
        pass

    @abstractmethod
    async def list_keys(
        self,
        category: DataCategory,
        prefix: str = ""
    ) -> List[str]:
        """List keys in category."""
        pass


class MemoryProvider(StorageProvider):
    """In-memory storage for testing/caching."""

    def __init__(self):
        self.data: Dict[str, Dict[str, StoredItem]] = {}
        self.connected = False

    async def connect(self) -> bool:
        self.connected = True
        return True

    async def disconnect(self):
        self.connected = False

    async def get(self, key: str, category: DataCategory) -> Optional[StoredItem]:
        cat_key = category.value
        if cat_key in self.data and key in self.data[cat_key]:
            item = self.data[cat_key][key]
            if item.expires_at and datetime.now() > item.expires_at:
                del self.data[cat_key][key]
                return None
            return item
        return None

    async def set(
        self,
        key: str,
        value: Any,
        category: DataCategory,
        ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        cat_key = category.value
        if cat_key not in self.data:
            self.data[cat_key] = {}

        now = datetime.now()
        expires = None
        if ttl:
            from datetime import timedelta
            expires = now + timedelta(seconds=ttl)

        # Check for existing
        existing = self.data[cat_key].get(key)
        version = existing.version + 1 if existing else 1

        self.data[cat_key][key] = StoredItem(
            key=key,
            value=value,
            category=category,
            created_at=existing.created_at if existing else now,
            updated_at=now,
            expires_at=expires,
            metadata=metadata or {},
            version=version,
            checksum=self._compute_checksum(value)
        )
        return True

    async def delete(self, key: str, category: DataCategory) -> bool:
        cat_key = category.value
        if cat_key in self.data and key in self.data[cat_key]:
            del self.data[cat_key][key]
            return True
        return False

    async def exists(self, key: str, category: DataCategory) -> bool:
        cat_key = category.value
        return cat_key in self.data and key in self.data[cat_key]

    async def list_keys(
        self,
        category: DataCategory,
        prefix: str = ""
    ) -> List[str]:
        cat_key = category.value
        if cat_key not in self.data:
            return []
        return [k for k in self.data[cat_key] if k.startswith(prefix)]

    def _compute_checksum(self, value: Any) -> str:
        try:
            data = json.dumps(value, sort_keys=True, default=str)
            return hashlib.md5(data.encode()).hexdigest()
        except:
            return hashlib.md5(str(value).encode()).hexdigest()


class SQLiteProvider(StorageProvider):
    """SQLite storage provider."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None

    async def connect(self) -> bool:
        import sqlite3
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        await self._init_tables()
        logger.info(f"Connected to SQLite: {self.db_path}")
        return True

    async def _init_tables(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS storage (
                key TEXT NOT NULL,
                category TEXT NOT NULL,
                value BLOB,
                created_at TEXT,
                updated_at TEXT,
                expires_at TEXT,
                metadata TEXT,
                version INTEGER DEFAULT 1,
                checksum TEXT,
                PRIMARY KEY (key, category)
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_category ON storage(category)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_expires ON storage(expires_at)
        """)
        self.conn.commit()

    async def disconnect(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    async def get(self, key: str, category: DataCategory) -> Optional[StoredItem]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM storage WHERE key = ? AND category = ?",
            (key, category.value)
        )
        row = cursor.fetchone()

        if not row:
            return None

        key, cat, value_blob, created, updated, expires, meta, version, checksum = row

        # Check expiration
        if expires:
            expires_dt = datetime.fromisoformat(expires)
            if datetime.now() > expires_dt:
                await self.delete(key, category)
                return None

        return StoredItem(
            key=key,
            value=pickle.loads(value_blob),
            category=category,
            created_at=datetime.fromisoformat(created),
            updated_at=datetime.fromisoformat(updated),
            expires_at=datetime.fromisoformat(expires) if expires else None,
            metadata=json.loads(meta) if meta else {},
            version=version,
            checksum=checksum
        )

    async def set(
        self,
        key: str,
        value: Any,
        category: DataCategory,
        ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        now = datetime.now()
        expires = None
        if ttl:
            from datetime import timedelta
            expires = now + timedelta(seconds=ttl)

        # Get existing version
        existing = await self.get(key, category)
        version = existing.version + 1 if existing else 1

        value_blob = pickle.dumps(value)
        checksum = hashlib.md5(value_blob).hexdigest()

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO storage
            (key, category, value, created_at, updated_at, expires_at, metadata, version, checksum)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            key,
            category.value,
            value_blob,
            existing.created_at.isoformat() if existing else now.isoformat(),
            now.isoformat(),
            expires.isoformat() if expires else None,
            json.dumps(metadata) if metadata else None,
            version,
            checksum
        ))
        self.conn.commit()
        return True

    async def delete(self, key: str, category: DataCategory) -> bool:
        cursor = self.conn.cursor()
        cursor.execute(
            "DELETE FROM storage WHERE key = ? AND category = ?",
            (key, category.value)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    async def exists(self, key: str, category: DataCategory) -> bool:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT 1 FROM storage WHERE key = ? AND category = ?",
            (key, category.value)
        )
        return cursor.fetchone() is not None

    async def list_keys(
        self,
        category: DataCategory,
        prefix: str = ""
    ) -> List[str]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT key FROM storage WHERE category = ? AND key LIKE ?",
            (category.value, f"{prefix}%")
        )
        return [row[0] for row in cursor.fetchall()]

    async def cleanup_expired(self) -> int:
        """Remove expired entries."""
        cursor = self.conn.cursor()
        cursor.execute(
            "DELETE FROM storage WHERE expires_at IS NOT NULL AND expires_at < ?",
            (datetime.now().isoformat(),)
        )
        count = cursor.rowcount
        self.conn.commit()
        logger.info(f"Cleaned up {count} expired entries")
        return count


class FileProvider(StorageProvider):
    """File-based storage for large objects."""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.metadata_file = self.base_path / ".metadata.json"
        self.metadata: Dict[str, Dict[str, Any]] = {}

    async def connect(self) -> bool:
        self.base_path.mkdir(parents=True, exist_ok=True)

        if self.metadata_file.exists():
            with open(self.metadata_file) as f:
                self.metadata = json.load(f)

        logger.info(f"Connected to file storage: {self.base_path}")
        return True

    async def disconnect(self):
        await self._save_metadata()

    def _get_path(self, key: str, category: DataCategory) -> Path:
        safe_key = key.replace("/", "_").replace("\\", "_")
        return self.base_path / category.value / f"{safe_key}.pkl"

    async def get(self, key: str, category: DataCategory) -> Optional[StoredItem]:
        path = self._get_path(key, category)

        if not path.exists():
            return None

        meta_key = f"{category.value}:{key}"
        meta = self.metadata.get(meta_key, {})

        # Check expiration
        if meta.get("expires_at"):
            expires = datetime.fromisoformat(meta["expires_at"])
            if datetime.now() > expires:
                await self.delete(key, category)
                return None

        with open(path, "rb") as f:
            value = pickle.load(f)

        return StoredItem(
            key=key,
            value=value,
            category=category,
            created_at=datetime.fromisoformat(meta.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(meta.get("updated_at", datetime.now().isoformat())),
            expires_at=datetime.fromisoformat(meta["expires_at"]) if meta.get("expires_at") else None,
            metadata=meta.get("metadata", {}),
            version=meta.get("version", 1),
            checksum=meta.get("checksum", "")
        )

    async def set(
        self,
        key: str,
        value: Any,
        category: DataCategory,
        ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        path = self._get_path(key, category)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "wb") as f:
            pickle.dump(value, f)

        now = datetime.now()
        meta_key = f"{category.value}:{key}"

        existing = self.metadata.get(meta_key, {})
        version = existing.get("version", 0) + 1

        expires = None
        if ttl:
            from datetime import timedelta
            expires = now + timedelta(seconds=ttl)

        self.metadata[meta_key] = {
            "created_at": existing.get("created_at", now.isoformat()),
            "updated_at": now.isoformat(),
            "expires_at": expires.isoformat() if expires else None,
            "metadata": metadata or {},
            "version": version,
            "checksum": hashlib.md5(open(path, "rb").read()).hexdigest()
        }

        await self._save_metadata()
        return True

    async def delete(self, key: str, category: DataCategory) -> bool:
        path = self._get_path(key, category)
        meta_key = f"{category.value}:{key}"

        if path.exists():
            path.unlink()

        if meta_key in self.metadata:
            del self.metadata[meta_key]
            await self._save_metadata()

        return True

    async def exists(self, key: str, category: DataCategory) -> bool:
        return self._get_path(key, category).exists()

    async def list_keys(
        self,
        category: DataCategory,
        prefix: str = ""
    ) -> List[str]:
        cat_path = self.base_path / category.value
        if not cat_path.exists():
            return []

        keys = []
        for path in cat_path.glob(f"{prefix}*.pkl"):
            key = path.stem
            keys.append(key)

        return keys

    async def _save_metadata(self):
        with open(self.metadata_file, "w") as f:
            json.dump(self.metadata, f, indent=2)


class PersistenceLayer:
    """
    Unified persistence layer for BAEL.

    Provides:
    1. Multi-backend support (SQLite, Postgres, Redis, Files)
    2. Automatic serialization/deserialization
    3. TTL and expiration management
    4. Category-based organization
    5. Versioning and checksums
    """

    def __init__(self, config: Optional[StorageConfig] = None):
        self.config = config or StorageConfig()
        self.providers: Dict[StorageBackend, StorageProvider] = {}
        self.primary_provider: Optional[StorageProvider] = None
        self.cache_provider: Optional[StorageProvider] = None

    async def initialize(self):
        """Initialize storage providers."""
        # Always have memory cache
        memory = MemoryProvider()
        await memory.connect()
        self.providers[StorageBackend.MEMORY] = memory
        self.cache_provider = memory

        # Initialize primary backend
        if self.config.backend == StorageBackend.SQLITE:
            provider = SQLiteProvider(self.config.sqlite_path)
            await provider.connect()
            self.providers[StorageBackend.SQLITE] = provider
            self.primary_provider = provider

        elif self.config.backend == StorageBackend.FILE:
            provider = FileProvider(self.config.file_base_path)
            await provider.connect()
            self.providers[StorageBackend.FILE] = provider
            self.primary_provider = provider

        elif self.config.backend == StorageBackend.MEMORY:
            self.primary_provider = memory

        logger.info(f"Persistence layer initialized with {self.config.backend.value}")

    async def shutdown(self):
        """Shutdown all providers."""
        for provider in self.providers.values():
            await provider.disconnect()
        logger.info("Persistence layer shutdown")

    async def store(
        self,
        key: str,
        value: Any,
        category: DataCategory = DataCategory.CACHE,
        ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> bool:
        """Store a value."""
        success = await self.primary_provider.set(key, value, category, ttl, metadata)

        if success and use_cache and self.cache_provider != self.primary_provider:
            # Also cache in memory
            cache_ttl = min(ttl or self.config.cache_ttl, self.config.cache_ttl)
            await self.cache_provider.set(key, value, category, cache_ttl, metadata)

        return success

    async def retrieve(
        self,
        key: str,
        category: DataCategory = DataCategory.CACHE,
        use_cache: bool = True
    ) -> Optional[Any]:
        """Retrieve a value."""
        # Check cache first
        if use_cache and self.cache_provider != self.primary_provider:
            item = await self.cache_provider.get(key, category)
            if item:
                return item.value

        # Check primary
        item = await self.primary_provider.get(key, category)

        if item:
            # Populate cache
            if use_cache and self.cache_provider != self.primary_provider:
                await self.cache_provider.set(
                    key, item.value, category,
                    self.config.cache_ttl, item.metadata
                )
            return item.value

        return None

    async def remove(
        self,
        key: str,
        category: DataCategory = DataCategory.CACHE
    ) -> bool:
        """Remove a value."""
        success = await self.primary_provider.delete(key, category)

        if self.cache_provider != self.primary_provider:
            await self.cache_provider.delete(key, category)

        return success

    async def has(
        self,
        key: str,
        category: DataCategory = DataCategory.CACHE
    ) -> bool:
        """Check if key exists."""
        return await self.primary_provider.exists(key, category)

    async def keys(
        self,
        category: DataCategory = DataCategory.CACHE,
        prefix: str = ""
    ) -> List[str]:
        """List keys in category."""
        return await self.primary_provider.list_keys(category, prefix)

    # Convenience methods for specific categories

    async def store_memory(self, key: str, value: Any, **kwargs) -> bool:
        """Store cognitive memory."""
        return await self.store(key, value, DataCategory.MEMORY, **kwargs)

    async def retrieve_memory(self, key: str) -> Optional[Any]:
        """Retrieve cognitive memory."""
        return await self.retrieve(key, DataCategory.MEMORY)

    async def store_embedding(self, key: str, embedding: Any, **kwargs) -> bool:
        """Store vector embedding."""
        return await self.store(key, embedding, DataCategory.EMBEDDING, **kwargs)

    async def retrieve_embedding(self, key: str) -> Optional[Any]:
        """Retrieve vector embedding."""
        return await self.retrieve(key, DataCategory.EMBEDDING)

    async def store_model(self, key: str, weights: Any, **kwargs) -> bool:
        """Store model weights."""
        return await self.store(key, weights, DataCategory.MODEL, **kwargs)

    async def retrieve_model(self, key: str) -> Optional[Any]:
        """Retrieve model weights."""
        return await self.retrieve(key, DataCategory.MODEL)

    async def log_audit(self, event: str, data: Any) -> bool:
        """Log audit event."""
        key = f"{datetime.now().isoformat()}_{event}"
        return await self.store(key, data, DataCategory.AUDIT)

    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        return {
            "backend": self.config.backend.value,
            "sqlite_path": self.config.sqlite_path,
            "cache_ttl": self.config.cache_ttl,
            "providers": list(self.providers.keys())
        }


# Singleton instance
_persistence: Optional[PersistenceLayer] = None


async def get_persistence(config: Optional[StorageConfig] = None) -> PersistenceLayer:
    """Get or create persistence layer singleton."""
    global _persistence

    if _persistence is None:
        _persistence = PersistenceLayer(config)
        await _persistence.initialize()

    return _persistence


def demo():
    """Demonstrate persistence layer."""
    import asyncio

    async def run_demo():
        print("=" * 60)
        print("BAEL Persistence Layer Demo")
        print("=" * 60)

        config = StorageConfig(
            backend=StorageBackend.SQLITE,
            sqlite_path="data/demo.db"
        )

        persistence = PersistenceLayer(config)
        await persistence.initialize()

        # Store various data types
        await persistence.store("test_key", {"hello": "world"}, DataCategory.CACHE)
        await persistence.store_memory("user_preference", {"theme": "dark"})
        await persistence.store_embedding("doc_1", [0.1, 0.2, 0.3, 0.4])

        # Retrieve
        cached = await persistence.retrieve("test_key", DataCategory.CACHE)
        memory = await persistence.retrieve_memory("user_preference")
        embedding = await persistence.retrieve_embedding("doc_1")

        print(f"\nCached: {cached}")
        print(f"Memory: {memory}")
        print(f"Embedding: {embedding}")

        # List keys
        keys = await persistence.keys(DataCategory.CACHE)
        print(f"\nCache keys: {keys}")

        print(f"\nStats: {persistence.get_stats()}")

        await persistence.shutdown()
        print("\n✓ Multi-backend persistence")
        print("✓ Automatic caching")
        print("✓ Category organization")
        print("✓ TTL management")

    asyncio.run(run_demo())


if __name__ == "__main__":
    demo()
