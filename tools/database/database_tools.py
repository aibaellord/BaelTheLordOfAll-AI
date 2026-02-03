"""
BAEL Database Tools - Comprehensive Database Interaction Toolkit
Provides SQL, vector store, key-value, and document storage capabilities.
"""

import asyncio
import hashlib
import json
import logging
import math
import pickle
import sqlite3
import threading
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple, Union

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

logger = logging.getLogger("BAEL.Tools.Database")


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class QueryResult:
    """Result of a SQL query."""
    columns: List[str]
    rows: List[Tuple]
    row_count: int
    execution_time_ms: float
    affected_rows: int = 0
    last_insert_id: Optional[int] = None
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None

    def as_dicts(self) -> List[Dict[str, Any]]:
        """Convert rows to list of dictionaries."""
        return [dict(zip(self.columns, row)) for row in self.rows]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "columns": self.columns,
            "rows": [list(row) for row in self.rows],
            "row_count": self.row_count,
            "execution_time_ms": self.execution_time_ms,
            "error": self.error
        }


@dataclass
class TableInfo:
    """Information about a database table."""
    name: str
    columns: List[Dict[str, Any]]
    row_count: int
    size_bytes: Optional[int] = None
    indexes: List[str] = field(default_factory=list)
    primary_key: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "columns": self.columns,
            "row_count": self.row_count,
            "indexes": self.indexes,
            "primary_key": self.primary_key
        }


@dataclass
class VectorSearchResult:
    """Result of a vector similarity search."""
    id: str
    score: float
    metadata: Dict[str, Any]
    vector: Optional[List[float]] = None
    document: Optional[str] = None


# =============================================================================
# SQLITE CLIENT
# =============================================================================

class SQLiteClient:
    """SQLite database client with async support."""

    def __init__(self, db_path: Union[str, Path] = ":memory:"):
        self.db_path = str(db_path)
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = threading.Lock()

    def connect(self) -> None:
        """Connect to database."""
        if self._conn is None:
            self._conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                isolation_level=None  # Autocommit
            )
            self._conn.row_factory = sqlite3.Row

    def disconnect(self) -> None:
        """Disconnect from database."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def execute(
        self,
        query: str,
        params: Optional[Tuple] = None
    ) -> QueryResult:
        """Execute a SQL query."""
        self.connect()

        start_time = time.time()

        try:
            with self._lock:
                cursor = self._conn.cursor()

                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                # Get column names
                columns = []
                if cursor.description:
                    columns = [col[0] for col in cursor.description]

                # Fetch rows
                rows = cursor.fetchall()
                rows = [tuple(row) for row in rows]

                elapsed = (time.time() - start_time) * 1000

                return QueryResult(
                    columns=columns,
                    rows=rows,
                    row_count=len(rows),
                    execution_time_ms=elapsed,
                    affected_rows=cursor.rowcount,
                    last_insert_id=cursor.lastrowid
                )

        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            return QueryResult(
                columns=[],
                rows=[],
                row_count=0,
                execution_time_ms=elapsed,
                error=str(e)
            )

    def execute_many(
        self,
        query: str,
        params_list: List[Tuple]
    ) -> QueryResult:
        """Execute a query multiple times with different params."""
        self.connect()

        start_time = time.time()

        try:
            with self._lock:
                cursor = self._conn.cursor()
                cursor.executemany(query, params_list)

                elapsed = (time.time() - start_time) * 1000

                return QueryResult(
                    columns=[],
                    rows=[],
                    row_count=0,
                    execution_time_ms=elapsed,
                    affected_rows=cursor.rowcount
                )

        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            return QueryResult(
                columns=[],
                rows=[],
                row_count=0,
                execution_time_ms=elapsed,
                error=str(e)
            )

    def get_tables(self) -> List[str]:
        """Get list of tables."""
        result = self.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        return [row[0] for row in result.rows]

    def get_table_info(self, table_name: str) -> TableInfo:
        """Get information about a table."""
        # Get columns
        result = self.execute(f"PRAGMA table_info({table_name})")
        columns = []
        primary_key = None

        for row in result.rows:
            col_info = {
                "name": row[1],
                "type": row[2],
                "notnull": bool(row[3]),
                "default": row[4],
                "primary_key": bool(row[5])
            }
            columns.append(col_info)
            if col_info["primary_key"]:
                primary_key = col_info["name"]

        # Get row count
        count_result = self.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = count_result.rows[0][0] if count_result.rows else 0

        # Get indexes
        index_result = self.execute(f"PRAGMA index_list({table_name})")
        indexes = [row[1] for row in index_result.rows]

        return TableInfo(
            name=table_name,
            columns=columns,
            row_count=row_count,
            indexes=indexes,
            primary_key=primary_key
        )

    def create_table(
        self,
        table_name: str,
        columns: Dict[str, str],
        primary_key: Optional[str] = None,
        if_not_exists: bool = True
    ) -> QueryResult:
        """Create a table."""
        cols = []
        for name, type_ in columns.items():
            col_def = f"{name} {type_}"
            if name == primary_key:
                col_def += " PRIMARY KEY"
            cols.append(col_def)

        exists_clause = "IF NOT EXISTS " if if_not_exists else ""
        query = f"CREATE TABLE {exists_clause}{table_name} ({', '.join(cols)})"

        return self.execute(query)

    def insert(
        self,
        table_name: str,
        data: Dict[str, Any]
    ) -> QueryResult:
        """Insert a row."""
        columns = list(data.keys())
        placeholders = ", ".join(["?" for _ in columns])
        column_str = ", ".join(columns)

        query = f"INSERT INTO {table_name} ({column_str}) VALUES ({placeholders})"
        return self.execute(query, tuple(data.values()))

    def insert_many(
        self,
        table_name: str,
        data: List[Dict[str, Any]]
    ) -> QueryResult:
        """Insert multiple rows."""
        if not data:
            return QueryResult([], [], 0, 0)

        columns = list(data[0].keys())
        placeholders = ", ".join(["?" for _ in columns])
        column_str = ", ".join(columns)

        query = f"INSERT INTO {table_name} ({column_str}) VALUES ({placeholders})"
        params = [tuple(d.values()) for d in data]

        return self.execute_many(query, params)

    def select(
        self,
        table_name: str,
        columns: List[str] = None,
        where: Optional[str] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> QueryResult:
        """Select rows from table."""
        col_str = ", ".join(columns) if columns else "*"
        query = f"SELECT {col_str} FROM {table_name}"

        if where:
            query += f" WHERE {where}"
        if order_by:
            query += f" ORDER BY {order_by}"
        if limit:
            query += f" LIMIT {limit}"
        if offset:
            query += f" OFFSET {offset}"

        return self.execute(query)

    def update(
        self,
        table_name: str,
        data: Dict[str, Any],
        where: str
    ) -> QueryResult:
        """Update rows."""
        set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
        query = f"UPDATE {table_name} SET {set_clause} WHERE {where}"
        return self.execute(query, tuple(data.values()))

    def delete(
        self,
        table_name: str,
        where: str
    ) -> QueryResult:
        """Delete rows."""
        query = f"DELETE FROM {table_name} WHERE {where}"
        return self.execute(query)


# =============================================================================
# VECTOR STORE
# =============================================================================

class VectorStore:
    """
    Simple vector store for similarity search.
    Uses cosine similarity by default.
    """

    def __init__(
        self,
        dimensions: int = 1536,
        metric: str = "cosine"
    ):
        self.dimensions = dimensions
        self.metric = metric
        self._vectors: Dict[str, Dict[str, Any]] = {}

    def add(
        self,
        id: str,
        vector: List[float],
        metadata: Optional[Dict[str, Any]] = None,
        document: Optional[str] = None
    ) -> None:
        """Add a vector to the store."""
        if len(vector) != self.dimensions:
            raise ValueError(f"Vector dimension mismatch: expected {self.dimensions}, got {len(vector)}")

        self._vectors[id] = {
            "vector": vector,
            "metadata": metadata or {},
            "document": document
        }

    def add_many(
        self,
        items: List[Dict[str, Any]]
    ) -> int:
        """Add multiple vectors."""
        count = 0
        for item in items:
            self.add(
                id=item["id"],
                vector=item["vector"],
                metadata=item.get("metadata"),
                document=item.get("document")
            )
            count += 1
        return count

    def get(self, id: str) -> Optional[Dict[str, Any]]:
        """Get a vector by ID."""
        return self._vectors.get(id)

    def delete(self, id: str) -> bool:
        """Delete a vector."""
        if id in self._vectors:
            del self._vectors[id]
            return True
        return False

    def search(
        self,
        query_vector: List[float],
        k: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        """Search for similar vectors."""
        if len(query_vector) != self.dimensions:
            raise ValueError(f"Query vector dimension mismatch")

        results = []

        for id, data in self._vectors.items():
            # Apply metadata filter
            if filter_metadata:
                match = all(
                    data["metadata"].get(k) == v
                    for k, v in filter_metadata.items()
                )
                if not match:
                    continue

            # Calculate similarity
            score = self._similarity(query_vector, data["vector"])

            results.append(VectorSearchResult(
                id=id,
                score=score,
                metadata=data["metadata"],
                vector=data["vector"],
                document=data["document"]
            ))

        # Sort by score (descending)
        results.sort(key=lambda x: x.score, reverse=True)

        return results[:k]

    def _similarity(self, v1: List[float], v2: List[float]) -> float:
        """Calculate similarity between two vectors."""
        if self.metric == "cosine":
            return self._cosine_similarity(v1, v2)
        elif self.metric == "euclidean":
            return -self._euclidean_distance(v1, v2)
        elif self.metric == "dot":
            return self._dot_product(v1, v2)
        else:
            return self._cosine_similarity(v1, v2)

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """Cosine similarity."""
        if NUMPY_AVAILABLE:
            a, b = np.array(v1), np.array(v2)
            return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))

        if norm1 == 0 or norm2 == 0:
            return 0

        return dot / (norm1 * norm2)

    def _euclidean_distance(self, v1: List[float], v2: List[float]) -> float:
        """Euclidean distance."""
        if NUMPY_AVAILABLE:
            return float(np.linalg.norm(np.array(v1) - np.array(v2)))

        return math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2)))

    def _dot_product(self, v1: List[float], v2: List[float]) -> float:
        """Dot product."""
        if NUMPY_AVAILABLE:
            return float(np.dot(np.array(v1), np.array(v2)))

        return sum(a * b for a, b in zip(v1, v2))

    def save(self, path: Union[str, Path]) -> None:
        """Save vector store to disk."""
        path = Path(path)
        with open(path, 'wb') as f:
            pickle.dump({
                "dimensions": self.dimensions,
                "metric": self.metric,
                "vectors": self._vectors
            }, f)

    def load(self, path: Union[str, Path]) -> None:
        """Load vector store from disk."""
        path = Path(path)
        with open(path, 'rb') as f:
            data = pickle.load(f)
            self.dimensions = data["dimensions"]
            self.metric = data["metric"]
            self._vectors = data["vectors"]

    @property
    def count(self) -> int:
        """Number of vectors in store."""
        return len(self._vectors)


# =============================================================================
# KEY-VALUE STORE
# =============================================================================

class KeyValueStore:
    """
    Simple key-value store with optional persistence and TTL support.
    """

    def __init__(
        self,
        persist_path: Optional[Union[str, Path]] = None,
        max_size: int = 10000,
        default_ttl: Optional[float] = None
    ):
        self.persist_path = Path(persist_path) if persist_path else None
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._store: OrderedDict = OrderedDict()
        self._expiry: Dict[str, float] = {}
        self._lock = threading.Lock()

        if self.persist_path and self.persist_path.exists():
            self._load()

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None
    ) -> None:
        """Set a value."""
        with self._lock:
            # Evict if at max size
            while len(self._store) >= self.max_size:
                oldest_key = next(iter(self._store))
                del self._store[oldest_key]
                self._expiry.pop(oldest_key, None)

            self._store[key] = value
            self._store.move_to_end(key)

            if ttl is not None or self.default_ttl is not None:
                expiry_time = time.time() + (ttl or self.default_ttl)
                self._expiry[key] = expiry_time
            elif key in self._expiry:
                del self._expiry[key]

    def get(
        self,
        key: str,
        default: Any = None
    ) -> Any:
        """Get a value."""
        with self._lock:
            # Check expiry
            if key in self._expiry:
                if time.time() > self._expiry[key]:
                    del self._store[key]
                    del self._expiry[key]
                    return default

            if key not in self._store:
                return default

            # Move to end (LRU)
            self._store.move_to_end(key)
            return self._store[key]

    def delete(self, key: str) -> bool:
        """Delete a key."""
        with self._lock:
            if key in self._store:
                del self._store[key]
                self._expiry.pop(key, None)
                return True
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        with self._lock:
            if key in self._expiry and time.time() > self._expiry[key]:
                del self._store[key]
                del self._expiry[key]
                return False
            return key in self._store

    def keys(self, pattern: Optional[str] = None) -> List[str]:
        """Get all keys, optionally filtered by pattern."""
        import fnmatch

        self._cleanup_expired()

        with self._lock:
            if pattern:
                return [k for k in self._store.keys() if fnmatch.fnmatch(k, pattern)]
            return list(self._store.keys())

    def clear(self) -> None:
        """Clear all data."""
        with self._lock:
            self._store.clear()
            self._expiry.clear()

    def size(self) -> int:
        """Get number of items."""
        self._cleanup_expired()
        return len(self._store)

    def _cleanup_expired(self) -> None:
        """Remove expired entries."""
        now = time.time()
        with self._lock:
            expired = [k for k, v in self._expiry.items() if now > v]
            for key in expired:
                self._store.pop(key, None)
                del self._expiry[key]

    def save(self) -> None:
        """Save to disk."""
        if not self.persist_path:
            return

        with self._lock:
            data = {
                "store": dict(self._store),
                "expiry": self._expiry
            }
            with open(self.persist_path, 'wb') as f:
                pickle.dump(data, f)

    def _load(self) -> None:
        """Load from disk."""
        try:
            with open(self.persist_path, 'rb') as f:
                data = pickle.load(f)
                self._store = OrderedDict(data.get("store", {}))
                self._expiry = data.get("expiry", {})
        except Exception as e:
            logger.warning(f"Failed to load KV store: {e}")


# =============================================================================
# DOCUMENT STORE
# =============================================================================

class DocumentStore:
    """
    Document store for JSON-like documents.
    Built on SQLite with indexing support.
    """

    def __init__(
        self,
        db_path: Union[str, Path] = ":memory:",
        collection_name: str = "documents"
    ):
        self.collection_name = collection_name
        self._db = SQLiteClient(db_path)
        self._init_schema()

    def _init_schema(self) -> None:
        """Initialize database schema."""
        self._db.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.collection_name} (
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)

        self._db.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_{self.collection_name}_created
            ON {self.collection_name}(created_at)
        """)

    def insert(
        self,
        document: Dict[str, Any],
        id: Optional[str] = None
    ) -> str:
        """Insert a document."""
        doc_id = id or hashlib.sha256(json.dumps(document, sort_keys=True).encode()).hexdigest()[:16]
        now = time.time()

        self._db.execute(
            f"INSERT OR REPLACE INTO {self.collection_name} (id, data, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (doc_id, json.dumps(document), now, now)
        )

        return doc_id

    def insert_many(self, documents: List[Dict[str, Any]]) -> List[str]:
        """Insert multiple documents."""
        ids = []
        for doc in documents:
            doc_id = self.insert(doc)
            ids.append(doc_id)
        return ids

    def get(self, id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID."""
        result = self._db.execute(
            f"SELECT data FROM {self.collection_name} WHERE id = ?",
            (id,)
        )

        if result.rows:
            return json.loads(result.rows[0][0])
        return None

    def find(
        self,
        query: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Find documents matching query.
        Simple implementation - matches top-level keys.
        """
        result = self._db.execute(
            f"SELECT id, data FROM {self.collection_name} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        )

        documents = []
        for row in result.rows:
            doc = json.loads(row[1])
            doc["_id"] = row[0]

            # Apply query filter
            if query:
                match = all(doc.get(k) == v for k, v in query.items())
                if not match:
                    continue

            documents.append(doc)

        return documents

    def update(
        self,
        id: str,
        updates: Dict[str, Any],
        upsert: bool = False
    ) -> bool:
        """Update a document."""
        existing = self.get(id)

        if existing is None:
            if upsert:
                self.insert(updates, id)
                return True
            return False

        existing.update(updates)

        self._db.execute(
            f"UPDATE {self.collection_name} SET data = ?, updated_at = ? WHERE id = ?",
            (json.dumps(existing), time.time(), id)
        )

        return True

    def delete(self, id: str) -> bool:
        """Delete a document."""
        result = self._db.execute(
            f"DELETE FROM {self.collection_name} WHERE id = ?",
            (id,)
        )
        return result.affected_rows > 0

    def count(self, query: Optional[Dict[str, Any]] = None) -> int:
        """Count documents."""
        if query:
            # Simple count with filter
            docs = self.find(query, limit=100000)
            return len(docs)

        result = self._db.execute(f"SELECT COUNT(*) FROM {self.collection_name}")
        return result.rows[0][0] if result.rows else 0

    def clear(self) -> None:
        """Clear all documents."""
        self._db.execute(f"DELETE FROM {self.collection_name}")

    def create_index(self, field: str) -> None:
        """Create index on a JSON field (requires SQLite JSON1 extension)."""
        # Note: This requires SQLite with JSON1 extension
        self._db.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_{self.collection_name}_{field}
            ON {self.collection_name}(json_extract(data, '$.{field}'))
        """)


# =============================================================================
# DATABASE TOOLKIT - UNIFIED INTERFACE
# =============================================================================

class DatabaseToolkit:
    """
    Unified database toolkit providing all database capabilities.

    Main entry point for database operations in BAEL.
    """

    def __init__(
        self,
        sqlite_path: Union[str, Path] = ":memory:",
        vector_dimensions: int = 1536
    ):
        self.sqlite = SQLiteClient(sqlite_path)
        self.vectors = VectorStore(dimensions=vector_dimensions)
        self.kv = KeyValueStore()
        self.documents = DocumentStore(sqlite_path)

    # SQL Operations
    def sql_execute(self, query: str, params: Tuple = None) -> QueryResult:
        """Execute SQL query."""
        return self.sqlite.execute(query, params)

    def sql_tables(self) -> List[str]:
        """Get list of tables."""
        return self.sqlite.get_tables()

    def sql_table_info(self, table: str) -> TableInfo:
        """Get table information."""
        return self.sqlite.get_table_info(table)

    # Vector Operations
    def vector_add(
        self,
        id: str,
        vector: List[float],
        metadata: Dict[str, Any] = None,
        document: str = None
    ) -> None:
        """Add vector to store."""
        self.vectors.add(id, vector, metadata, document)

    def vector_search(
        self,
        query_vector: List[float],
        k: int = 10,
        filter_metadata: Dict[str, Any] = None
    ) -> List[VectorSearchResult]:
        """Search for similar vectors."""
        return self.vectors.search(query_vector, k, filter_metadata)

    # Key-Value Operations
    def kv_set(self, key: str, value: Any, ttl: float = None) -> None:
        """Set key-value."""
        self.kv.set(key, value, ttl)

    def kv_get(self, key: str, default: Any = None) -> Any:
        """Get value by key."""
        return self.kv.get(key, default)

    def kv_delete(self, key: str) -> bool:
        """Delete key."""
        return self.kv.delete(key)

    # Document Operations
    def doc_insert(self, document: Dict[str, Any]) -> str:
        """Insert document."""
        return self.documents.insert(document)

    def doc_get(self, id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID."""
        return self.documents.get(id)

    def doc_find(
        self,
        query: Dict[str, Any] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Find documents."""
        return self.documents.find(query, limit)

    def doc_delete(self, id: str) -> bool:
        """Delete document."""
        return self.documents.delete(id)

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get tool definitions for BAEL integration."""
        return [
            {
                "name": "sql_query",
                "description": "Execute a SQL query",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "SQL query to execute"},
                        "params": {"type": "array", "description": "Query parameters"}
                    },
                    "required": ["query"]
                },
                "handler": lambda query, params=None: self.sql_execute(query, tuple(params) if params else None).to_dict()
            },
            {
                "name": "vector_search",
                "description": "Search for similar vectors",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query_vector": {"type": "array", "items": {"type": "number"}},
                        "k": {"type": "integer", "default": 10}
                    },
                    "required": ["query_vector"]
                },
                "handler": self.vector_search
            },
            {
                "name": "kv_get",
                "description": "Get value from key-value store",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string"}
                    },
                    "required": ["key"]
                },
                "handler": self.kv_get
            },
            {
                "name": "kv_set",
                "description": "Set value in key-value store",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string"},
                        "value": {},
                        "ttl": {"type": "number"}
                    },
                    "required": ["key", "value"]
                },
                "handler": self.kv_set
            },
            {
                "name": "doc_insert",
                "description": "Insert a document",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "document": {"type": "object"}
                    },
                    "required": ["document"]
                },
                "handler": self.doc_insert
            },
            {
                "name": "doc_find",
                "description": "Find documents matching query",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "object"},
                        "limit": {"type": "integer", "default": 100}
                    }
                },
                "handler": self.doc_find
            }
        ]


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "DatabaseToolkit",
    "SQLiteClient",
    "VectorStore",
    "KeyValueStore",
    "DocumentStore",
    "QueryResult",
    "VectorSearchResult",
    "TableInfo"
]
