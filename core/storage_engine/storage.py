"""
BAEL Storage Engine
===================

Multi-paradigm storage with:
- Document store (JSON-based)
- Key-Value store
- Time-series store
- Vector store (for embeddings)
- Intelligent caching

"Store everything, retrieve anything." — Ba'el
"""

import asyncio
import hashlib
import json
import logging
import math
import pickle
import sqlite3
import time
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, Generic, Iterator, List, Optional, Set, Tuple, TypeVar, Union

logger = logging.getLogger("BAEL.Storage")

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class StorageBackend(Enum):
    """Storage backend types."""
    MEMORY = "memory"
    FILE = "file"
    SQLITE = "sqlite"
    JSON = "json"
    PICKLE = "pickle"


class DataFormat(Enum):
    """Data serialization formats."""
    JSON = "json"
    PICKLE = "pickle"
    MSGPACK = "msgpack"
    BINARY = "binary"


class IndexType(Enum):
    """Index types."""
    HASH = "hash"
    BTREE = "btree"
    FULLTEXT = "fulltext"
    VECTOR = "vector"


class QueryOperator(Enum):
    """Query operators."""
    EQ = "eq"         # Equal
    NE = "ne"         # Not equal
    GT = "gt"         # Greater than
    GTE = "gte"       # Greater than or equal
    LT = "lt"         # Less than
    LTE = "lte"       # Less than or equal
    IN = "in"         # In list
    NIN = "nin"       # Not in list
    CONTAINS = "contains"
    STARTSWITH = "startswith"
    ENDSWITH = "endswith"
    REGEX = "regex"
    EXISTS = "exists"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class StorageConfig:
    """Configuration for storage engine."""
    data_dir: Path = field(default_factory=lambda: Path("data/storage"))
    backend: StorageBackend = StorageBackend.SQLITE
    cache_size: int = 10000
    cache_ttl_seconds: int = 3600
    auto_compact: bool = True
    compact_threshold: int = 1000
    sync_writes: bool = True


@dataclass
class Document:
    """A stored document."""
    id: str
    data: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    version: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "data": self.data,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Document":
        """Create from dictionary."""
        return cls(
            id=d["id"],
            data=d["data"],
            created_at=datetime.fromisoformat(d["created_at"]) if isinstance(d["created_at"], str) else d["created_at"],
            updated_at=datetime.fromisoformat(d["updated_at"]) if isinstance(d["updated_at"], str) else d["updated_at"],
            version=d.get("version", 1),
            metadata=d.get("metadata", {})
        )


@dataclass
class Collection:
    """A collection of documents."""
    name: str
    document_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    indexes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueryFilter:
    """A query filter."""
    field: str
    operator: QueryOperator
    value: Any


@dataclass
class QueryResult:
    """Result of a query."""
    documents: List[Document]
    total_count: int
    execution_time_ms: float
    has_more: bool = False
    cursor: Optional[str] = None


@dataclass
class TimeSeriesPoint:
    """A point in a time series."""
    timestamp: datetime
    value: float
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# LRU CACHE
# =============================================================================

class LRUCache(Generic[T]):
    """Least Recently Used cache."""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, Tuple[T, float]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[T]:
        """Get item from cache."""
        with self._lock:
            if key not in self._cache:
                return None

            value, timestamp = self._cache[key]

            # Check TTL
            if time.time() - timestamp > self.ttl_seconds:
                del self._cache[key]
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return value

    def set(self, key: str, value: T):
        """Set item in cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]

            self._cache[key] = (value, time.time())

            # Evict oldest if over capacity
            while len(self._cache) > self.max_size:
                self._cache.popitem(last=False)

    def delete(self, key: str):
        """Delete item from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]

    def clear(self):
        """Clear the cache."""
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        """Get cache size."""
        return len(self._cache)


# =============================================================================
# KEY-VALUE STORE
# =============================================================================

class KeyValueStore:
    """Simple key-value store."""

    def __init__(
        self,
        name: str,
        storage_path: Optional[Path] = None,
        backend: StorageBackend = StorageBackend.SQLITE
    ):
        self.name = name
        self.backend = backend
        self.storage_path = storage_path or Path("data/kv")
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self._cache = LRUCache(max_size=10000)

        if backend == StorageBackend.SQLITE:
            self._init_sqlite()
        elif backend == StorageBackend.FILE:
            self._store_path = self.storage_path / name
            self._store_path.mkdir(parents=True, exist_ok=True)
        else:
            self._memory_store: Dict[str, bytes] = {}

    def _init_sqlite(self):
        """Initialize SQLite backend."""
        self._db_path = self.storage_path / f"{self.name}.db"
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS kv_store (
                key TEXT PRIMARY KEY,
                value BLOB,
                created_at REAL,
                updated_at REAL,
                expires_at REAL
            )
        """)
        self._conn.commit()

    def get(self, key: str) -> Optional[Any]:
        """Get value by key."""
        # Check cache
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        # Get from backend
        if self.backend == StorageBackend.SQLITE:
            cursor = self._conn.execute(
                "SELECT value, expires_at FROM kv_store WHERE key = ?",
                (key,)
            )
            row = cursor.fetchone()
            if row:
                value_bytes, expires_at = row
                if expires_at and time.time() > expires_at:
                    self.delete(key)
                    return None
                value = pickle.loads(value_bytes)
                self._cache.set(key, value)
                return value
        elif self.backend == StorageBackend.FILE:
            key_path = self._store_path / f"{hashlib.md5(key.encode()).hexdigest()}.pkl"
            if key_path.exists():
                value = pickle.loads(key_path.read_bytes())
                self._cache.set(key, value)
                return value
        else:
            if key in self._memory_store:
                value = pickle.loads(self._memory_store[key])
                return value

        return None

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        """Set value by key."""
        value_bytes = pickle.dumps(value)
        now = time.time()
        expires_at = now + ttl_seconds if ttl_seconds else None

        # Update cache
        self._cache.set(key, value)

        # Update backend
        if self.backend == StorageBackend.SQLITE:
            self._conn.execute("""
                INSERT OR REPLACE INTO kv_store (key, value, created_at, updated_at, expires_at)
                VALUES (?, ?, ?, ?, ?)
            """, (key, value_bytes, now, now, expires_at))
            self._conn.commit()
        elif self.backend == StorageBackend.FILE:
            key_path = self._store_path / f"{hashlib.md5(key.encode()).hexdigest()}.pkl"
            key_path.write_bytes(value_bytes)
        else:
            self._memory_store[key] = value_bytes

    def delete(self, key: str):
        """Delete key."""
        self._cache.delete(key)

        if self.backend == StorageBackend.SQLITE:
            self._conn.execute("DELETE FROM kv_store WHERE key = ?", (key,))
            self._conn.commit()
        elif self.backend == StorageBackend.FILE:
            key_path = self._store_path / f"{hashlib.md5(key.encode()).hexdigest()}.pkl"
            if key_path.exists():
                key_path.unlink()
        else:
            if key in self._memory_store:
                del self._memory_store[key]

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        return self.get(key) is not None

    def keys(self, pattern: str = "*") -> List[str]:
        """Get all keys matching pattern."""
        if self.backend == StorageBackend.SQLITE:
            if pattern == "*":
                cursor = self._conn.execute("SELECT key FROM kv_store")
            else:
                sql_pattern = pattern.replace("*", "%")
                cursor = self._conn.execute(
                    "SELECT key FROM kv_store WHERE key LIKE ?",
                    (sql_pattern,)
                )
            return [row[0] for row in cursor.fetchall()]
        elif self.backend == StorageBackend.FILE:
            # Would need to store key mapping
            return []
        else:
            import fnmatch
            return [k for k in self._memory_store.keys() if fnmatch.fnmatch(k, pattern)]

    def clear(self):
        """Clear all keys."""
        self._cache.clear()

        if self.backend == StorageBackend.SQLITE:
            self._conn.execute("DELETE FROM kv_store")
            self._conn.commit()
        elif self.backend == StorageBackend.FILE:
            for f in self._store_path.glob("*.pkl"):
                f.unlink()
        else:
            self._memory_store.clear()


# =============================================================================
# DOCUMENT STORE
# =============================================================================

class DocumentStore:
    """Document-oriented store."""

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        backend: StorageBackend = StorageBackend.SQLITE
    ):
        self.backend = backend
        self.storage_path = storage_path or Path("data/documents")
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self._collections: Dict[str, Collection] = {}
        self._cache = LRUCache(max_size=10000)

        if backend == StorageBackend.SQLITE:
            self._init_sqlite()

    def _init_sqlite(self):
        """Initialize SQLite backend."""
        self._db_path = self.storage_path / "documents.db"
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS collections (
                name TEXT PRIMARY KEY,
                metadata TEXT,
                created_at REAL
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                collection TEXT,
                data TEXT,
                created_at REAL,
                updated_at REAL,
                version INTEGER,
                metadata TEXT,
                FOREIGN KEY (collection) REFERENCES collections(name)
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_collection
            ON documents(collection)
        """)
        self._conn.commit()

    def create_collection(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> Collection:
        """Create a new collection."""
        collection = Collection(
            name=name,
            metadata=metadata or {}
        )

        self._collections[name] = collection

        if self.backend == StorageBackend.SQLITE:
            self._conn.execute("""
                INSERT OR REPLACE INTO collections (name, metadata, created_at)
                VALUES (?, ?, ?)
            """, (name, json.dumps(metadata or {}), time.time()))
            self._conn.commit()

        return collection

    def get_collection(self, name: str) -> Optional[Collection]:
        """Get a collection by name."""
        if name in self._collections:
            return self._collections[name]

        if self.backend == StorageBackend.SQLITE:
            cursor = self._conn.execute(
                "SELECT name, metadata, created_at FROM collections WHERE name = ?",
                (name,)
            )
            row = cursor.fetchone()
            if row:
                collection = Collection(
                    name=row[0],
                    metadata=json.loads(row[1]),
                    created_at=datetime.fromtimestamp(row[2])
                )
                self._collections[name] = collection
                return collection

        return None

    def list_collections(self) -> List[Collection]:
        """List all collections."""
        if self.backend == StorageBackend.SQLITE:
            cursor = self._conn.execute(
                "SELECT name, metadata, created_at FROM collections"
            )
            collections = []
            for row in cursor.fetchall():
                collection = Collection(
                    name=row[0],
                    metadata=json.loads(row[1]),
                    created_at=datetime.fromtimestamp(row[2])
                )
                collections.append(collection)
                self._collections[row[0]] = collection
            return collections

        return list(self._collections.values())

    def insert(self, collection: str, data: Dict[str, Any], doc_id: Optional[str] = None) -> Document:
        """Insert a document."""
        # Ensure collection exists
        if collection not in self._collections:
            self.create_collection(collection)

        doc_id = doc_id or hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()[:12]
        now = datetime.now()

        doc = Document(
            id=doc_id,
            data=data,
            created_at=now,
            updated_at=now
        )

        # Cache
        cache_key = f"{collection}:{doc_id}"
        self._cache.set(cache_key, doc)

        if self.backend == StorageBackend.SQLITE:
            self._conn.execute("""
                INSERT OR REPLACE INTO documents
                (id, collection, data, created_at, updated_at, version, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                doc_id, collection, json.dumps(data),
                now.timestamp(), now.timestamp(), 1, "{}"
            ))
            self._conn.commit()

        return doc

    def get(self, collection: str, doc_id: str) -> Optional[Document]:
        """Get a document by ID."""
        cache_key = f"{collection}:{doc_id}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        if self.backend == StorageBackend.SQLITE:
            cursor = self._conn.execute(
                "SELECT id, data, created_at, updated_at, version, metadata FROM documents WHERE id = ? AND collection = ?",
                (doc_id, collection)
            )
            row = cursor.fetchone()
            if row:
                doc = Document(
                    id=row[0],
                    data=json.loads(row[1]),
                    created_at=datetime.fromtimestamp(row[2]),
                    updated_at=datetime.fromtimestamp(row[3]),
                    version=row[4],
                    metadata=json.loads(row[5])
                )
                self._cache.set(cache_key, doc)
                return doc

        return None

    def update(self, collection: str, doc_id: str, data: Dict[str, Any]) -> Optional[Document]:
        """Update a document."""
        existing = self.get(collection, doc_id)
        if not existing:
            return None

        now = datetime.now()
        existing.data.update(data)
        existing.updated_at = now
        existing.version += 1

        cache_key = f"{collection}:{doc_id}"
        self._cache.set(cache_key, existing)

        if self.backend == StorageBackend.SQLITE:
            self._conn.execute("""
                UPDATE documents
                SET data = ?, updated_at = ?, version = ?
                WHERE id = ? AND collection = ?
            """, (
                json.dumps(existing.data), now.timestamp(),
                existing.version, doc_id, collection
            ))
            self._conn.commit()

        return existing

    def delete(self, collection: str, doc_id: str) -> bool:
        """Delete a document."""
        cache_key = f"{collection}:{doc_id}"
        self._cache.delete(cache_key)

        if self.backend == StorageBackend.SQLITE:
            cursor = self._conn.execute(
                "DELETE FROM documents WHERE id = ? AND collection = ?",
                (doc_id, collection)
            )
            self._conn.commit()
            return cursor.rowcount > 0

        return False

    def query(
        self,
        collection: str,
        filters: Optional[List[QueryFilter]] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: Optional[str] = None,
        order_desc: bool = False
    ) -> QueryResult:
        """Query documents."""
        start_time = time.time()

        if self.backend == StorageBackend.SQLITE:
            # Build SQL query
            sql = "SELECT id, data, created_at, updated_at, version, metadata FROM documents WHERE collection = ?"
            params: List[Any] = [collection]

            if filters:
                for f in filters:
                    if f.operator == QueryOperator.EQ:
                        sql += f" AND json_extract(data, '$.{f.field}') = ?"
                        params.append(f.value)
                    elif f.operator == QueryOperator.NE:
                        sql += f" AND json_extract(data, '$.{f.field}') != ?"
                        params.append(f.value)
                    elif f.operator == QueryOperator.GT:
                        sql += f" AND json_extract(data, '$.{f.field}') > ?"
                        params.append(f.value)
                    elif f.operator == QueryOperator.GTE:
                        sql += f" AND json_extract(data, '$.{f.field}') >= ?"
                        params.append(f.value)
                    elif f.operator == QueryOperator.LT:
                        sql += f" AND json_extract(data, '$.{f.field}') < ?"
                        params.append(f.value)
                    elif f.operator == QueryOperator.LTE:
                        sql += f" AND json_extract(data, '$.{f.field}') <= ?"
                        params.append(f.value)
                    elif f.operator == QueryOperator.CONTAINS:
                        sql += f" AND json_extract(data, '$.{f.field}') LIKE ?"
                        params.append(f"%{f.value}%")

            # Get total count
            count_sql = f"SELECT COUNT(*) FROM ({sql})"
            count_cursor = self._conn.execute(count_sql, params)
            total_count = count_cursor.fetchone()[0]

            # Add ordering
            if order_by:
                direction = "DESC" if order_desc else "ASC"
                sql += f" ORDER BY json_extract(data, '$.{order_by}') {direction}"

            # Add pagination
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor = self._conn.execute(sql, params)

            documents = []
            for row in cursor.fetchall():
                doc = Document(
                    id=row[0],
                    data=json.loads(row[1]),
                    created_at=datetime.fromtimestamp(row[2]),
                    updated_at=datetime.fromtimestamp(row[3]),
                    version=row[4],
                    metadata=json.loads(row[5])
                )
                documents.append(doc)

            return QueryResult(
                documents=documents,
                total_count=total_count,
                execution_time_ms=(time.time() - start_time) * 1000,
                has_more=offset + limit < total_count
            )

        return QueryResult(
            documents=[],
            total_count=0,
            execution_time_ms=(time.time() - start_time) * 1000
        )

    def find_one(
        self,
        collection: str,
        filters: List[QueryFilter]
    ) -> Optional[Document]:
        """Find a single document."""
        result = self.query(collection, filters, limit=1)
        return result.documents[0] if result.documents else None


# =============================================================================
# TIME SERIES STORE
# =============================================================================

class TimeSeriesStore:
    """Time series data store."""

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        backend: StorageBackend = StorageBackend.SQLITE
    ):
        self.backend = backend
        self.storage_path = storage_path or Path("data/timeseries")
        self.storage_path.mkdir(parents=True, exist_ok=True)

        if backend == StorageBackend.SQLITE:
            self._init_sqlite()
        else:
            self._memory_store: Dict[str, List[TimeSeriesPoint]] = {}

    def _init_sqlite(self):
        """Initialize SQLite backend."""
        self._db_path = self.storage_path / "timeseries.db"
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS timeseries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric TEXT,
                timestamp REAL,
                value REAL,
                tags TEXT,
                metadata TEXT
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_timeseries_metric_time
            ON timeseries(metric, timestamp)
        """)
        self._conn.commit()

    def write(
        self,
        metric: str,
        value: float,
        timestamp: Optional[datetime] = None,
        tags: Optional[Dict[str, str]] = None
    ):
        """Write a data point."""
        ts = timestamp or datetime.now()
        point = TimeSeriesPoint(
            timestamp=ts,
            value=value,
            tags=tags or {}
        )

        if self.backend == StorageBackend.SQLITE:
            self._conn.execute("""
                INSERT INTO timeseries (metric, timestamp, value, tags, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (metric, ts.timestamp(), value, json.dumps(tags or {}), "{}"))
            self._conn.commit()
        else:
            if metric not in self._memory_store:
                self._memory_store[metric] = []
            self._memory_store[metric].append(point)

    def write_batch(
        self,
        metric: str,
        points: List[Tuple[datetime, float]]
    ):
        """Write multiple data points."""
        if self.backend == StorageBackend.SQLITE:
            self._conn.executemany("""
                INSERT INTO timeseries (metric, timestamp, value, tags, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, [(metric, ts.timestamp(), value, "{}", "{}") for ts, value in points])
            self._conn.commit()
        else:
            if metric not in self._memory_store:
                self._memory_store[metric] = []
            for ts, value in points:
                self._memory_store[metric].append(TimeSeriesPoint(
                    timestamp=ts,
                    value=value
                ))

    def query(
        self,
        metric: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
        aggregation: Optional[str] = None,
        interval_seconds: int = 60
    ) -> List[TimeSeriesPoint]:
        """Query time series data."""
        if self.backend == StorageBackend.SQLITE:
            sql = "SELECT timestamp, value, tags, metadata FROM timeseries WHERE metric = ?"
            params: List[Any] = [metric]

            if start_time:
                sql += " AND timestamp >= ?"
                params.append(start_time.timestamp())
            if end_time:
                sql += " AND timestamp <= ?"
                params.append(end_time.timestamp())

            sql += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor = self._conn.execute(sql, params)

            points = []
            for row in cursor.fetchall():
                points.append(TimeSeriesPoint(
                    timestamp=datetime.fromtimestamp(row[0]),
                    value=row[1],
                    tags=json.loads(row[2]),
                    metadata=json.loads(row[3])
                ))

            # Apply aggregation if requested
            if aggregation and points:
                points = self._aggregate(points, aggregation, interval_seconds)

            return points

        return []

    def _aggregate(
        self,
        points: List[TimeSeriesPoint],
        aggregation: str,
        interval_seconds: int
    ) -> List[TimeSeriesPoint]:
        """Aggregate time series data."""
        if not points:
            return []

        # Group by interval
        buckets: Dict[int, List[float]] = {}
        for point in points:
            bucket = int(point.timestamp.timestamp()) // interval_seconds
            if bucket not in buckets:
                buckets[bucket] = []
            buckets[bucket].append(point.value)

        # Apply aggregation function
        result = []
        for bucket, values in sorted(buckets.items()):
            ts = datetime.fromtimestamp(bucket * interval_seconds)

            if aggregation == "avg":
                agg_value = sum(values) / len(values)
            elif aggregation == "sum":
                agg_value = sum(values)
            elif aggregation == "min":
                agg_value = min(values)
            elif aggregation == "max":
                agg_value = max(values)
            elif aggregation == "count":
                agg_value = float(len(values))
            elif aggregation == "first":
                agg_value = values[0]
            elif aggregation == "last":
                agg_value = values[-1]
            else:
                agg_value = sum(values) / len(values)

            result.append(TimeSeriesPoint(
                timestamp=ts,
                value=agg_value
            ))

        return result

    def metrics(self) -> List[str]:
        """List all metrics."""
        if self.backend == StorageBackend.SQLITE:
            cursor = self._conn.execute(
                "SELECT DISTINCT metric FROM timeseries"
            )
            return [row[0] for row in cursor.fetchall()]
        return list(self._memory_store.keys())

    def delete_metric(self, metric: str):
        """Delete a metric and all its data."""
        if self.backend == StorageBackend.SQLITE:
            self._conn.execute("DELETE FROM timeseries WHERE metric = ?", (metric,))
            self._conn.commit()
        else:
            if metric in self._memory_store:
                del self._memory_store[metric]


# =============================================================================
# VECTOR STORE
# =============================================================================

class VectorStore:
    """Vector store for embeddings."""

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        dimensions: int = 384
    ):
        self.storage_path = storage_path or Path("data/vectors")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.dimensions = dimensions

        self._vectors: Dict[str, Tuple[List[float], Dict[str, Any]]] = {}
        self._load()

    def _load(self):
        """Load vectors from disk."""
        index_file = self.storage_path / "vectors.json"
        if index_file.exists():
            data = json.loads(index_file.read_text())
            self._vectors = {
                k: (v["vector"], v["metadata"])
                for k, v in data.items()
            }

    def _save(self):
        """Save vectors to disk."""
        data = {
            k: {"vector": v[0], "metadata": v[1]}
            for k, v in self._vectors.items()
        }
        index_file = self.storage_path / "vectors.json"
        index_file.write_text(json.dumps(data))

    def add(
        self,
        id: str,
        vector: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Add a vector."""
        if len(vector) != self.dimensions:
            raise ValueError(f"Expected {self.dimensions} dimensions, got {len(vector)}")

        self._vectors[id] = (vector, metadata or {})
        self._save()

    def add_batch(
        self,
        items: List[Tuple[str, List[float], Dict[str, Any]]]
    ):
        """Add multiple vectors."""
        for id, vector, metadata in items:
            if len(vector) == self.dimensions:
                self._vectors[id] = (vector, metadata)
        self._save()

    def get(self, id: str) -> Optional[Tuple[List[float], Dict[str, Any]]]:
        """Get a vector by ID."""
        return self._vectors.get(id)

    def delete(self, id: str):
        """Delete a vector."""
        if id in self._vectors:
            del self._vectors[id]
            self._save()

    def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        min_similarity: float = 0.0
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Search for similar vectors."""
        if len(query_vector) != self.dimensions:
            raise ValueError(f"Expected {self.dimensions} dimensions")

        results = []

        for id, (vector, metadata) in self._vectors.items():
            similarity = self._cosine_similarity(query_vector, vector)
            if similarity >= min_similarity:
                results.append((id, similarity, metadata))

        # Sort by similarity (descending)
        results.sort(key=lambda x: x[1], reverse=True)

        return results[:top_k]

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = sum(a * b for a, b in zip(v1, v2))
        magnitude1 = math.sqrt(sum(a * a for a in v1))
        magnitude2 = math.sqrt(sum(b * b for b in v2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def count(self) -> int:
        """Get number of vectors."""
        return len(self._vectors)

    def clear(self):
        """Clear all vectors."""
        self._vectors.clear()
        self._save()


# =============================================================================
# STORAGE ENGINE
# =============================================================================

class StorageEngine:
    """Main storage engine combining all storage types."""

    def __init__(self, config: Optional[StorageConfig] = None):
        self.config = config or StorageConfig()
        self.config.data_dir.mkdir(parents=True, exist_ok=True)

        # Initialize sub-stores
        self.kv = KeyValueStore(
            "default",
            self.config.data_dir / "kv",
            self.config.backend
        )
        self.documents = DocumentStore(
            self.config.data_dir / "documents",
            self.config.backend
        )
        self.timeseries = TimeSeriesStore(
            self.config.data_dir / "timeseries",
            self.config.backend
        )
        self.vectors = VectorStore(
            self.config.data_dir / "vectors"
        )

        self._kv_stores: Dict[str, KeyValueStore] = {"default": self.kv}

    def get_kv_store(self, name: str) -> KeyValueStore:
        """Get or create a named KV store."""
        if name not in self._kv_stores:
            self._kv_stores[name] = KeyValueStore(
                name,
                self.config.data_dir / "kv",
                self.config.backend
            )
        return self._kv_stores[name]

    # KV shortcuts
    def get(self, key: str) -> Optional[Any]:
        """Get value from default KV store."""
        return self.kv.get(key)

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in default KV store."""
        self.kv.set(key, value, ttl)

    def delete(self, key: str):
        """Delete from default KV store."""
        self.kv.delete(key)

    # Document shortcuts
    def insert_doc(self, collection: str, data: Dict[str, Any]) -> Document:
        """Insert a document."""
        return self.documents.insert(collection, data)

    def get_doc(self, collection: str, doc_id: str) -> Optional[Document]:
        """Get a document."""
        return self.documents.get(collection, doc_id)

    def query_docs(
        self,
        collection: str,
        filters: Optional[List[QueryFilter]] = None,
        **kwargs
    ) -> QueryResult:
        """Query documents."""
        return self.documents.query(collection, filters, **kwargs)

    # Timeseries shortcuts
    def write_metric(
        self,
        metric: str,
        value: float,
        timestamp: Optional[datetime] = None,
        tags: Optional[Dict[str, str]] = None
    ):
        """Write a metric value."""
        self.timeseries.write(metric, value, timestamp, tags)

    def query_metric(
        self,
        metric: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        **kwargs
    ) -> List[TimeSeriesPoint]:
        """Query metric data."""
        return self.timeseries.query(metric, start_time, end_time, **kwargs)

    # Vector shortcuts
    def add_vector(
        self,
        id: str,
        vector: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Add a vector."""
        self.vectors.add(id, vector, metadata)

    def search_vectors(
        self,
        query_vector: List[float],
        top_k: int = 10
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Search for similar vectors."""
        return self.vectors.search(query_vector, top_k)

    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        return {
            "kv_stores": len(self._kv_stores),
            "collections": len(self.documents.list_collections()),
            "metrics": len(self.timeseries.metrics()),
            "vectors": self.vectors.count()
        }


# =============================================================================
# CONVENIENCE INSTANCE
# =============================================================================

storage_engine = StorageEngine()
