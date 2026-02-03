"""
BAEL - Vector Memory System
Embedding-based storage and retrieval for semantic similarity.

Vector memory provides:
- Embedding storage
- Similarity search
- Clustering
- Dimensionality reduction
- Hybrid retrieval (vector + keyword)
"""

import asyncio
import hashlib
import json
import logging
import math
import os
import sqlite3
import struct
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("BAEL.Memory.Vector")


# =============================================================================
# DATA CLASSES
# =============================================================================

class DistanceMetric(Enum):
    """Distance metrics for vector comparison."""
    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    DOT_PRODUCT = "dot_product"
    MANHATTAN = "manhattan"


@dataclass
class VectorEntry:
    """An entry in the vector store."""
    id: str
    vector: List[float]
    content: str
    metadata: Dict[str, Any]
    created_at: datetime
    source: str
    namespace: str = "default"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "vector_dim": len(self.vector),
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "source": self.source,
            "namespace": self.namespace
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], vector: List[float]) -> "VectorEntry":
        return cls(
            id=data["id"],
            vector=vector,
            content=data["content"],
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            source=data.get("source", "unknown"),
            namespace=data.get("namespace", "default")
        )


@dataclass
class SearchResult:
    """Result from a vector search."""
    entry: VectorEntry
    score: float
    rank: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.entry.id,
            "score": self.score,
            "rank": self.rank,
            "content": self.entry.content,
            "metadata": self.entry.metadata
        }


@dataclass
class VectorStats:
    """Statistics about the vector store."""
    total_entries: int
    namespaces: Dict[str, int]
    dimensions: int
    avg_vector_magnitude: float
    storage_bytes: int


# =============================================================================
# VECTOR OPERATIONS
# =============================================================================

class VectorOps:
    """Pure Python vector operations."""

    @staticmethod
    def cosine_similarity(a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(a) != len(b):
            raise ValueError("Vectors must have same dimension")

        dot = sum(x * y for x, y in zip(a, b))
        mag_a = math.sqrt(sum(x * x for x in a))
        mag_b = math.sqrt(sum(x * x for x in b))

        if mag_a == 0 or mag_b == 0:
            return 0.0

        return dot / (mag_a * mag_b)

    @staticmethod
    def euclidean_distance(a: List[float], b: List[float]) -> float:
        """Calculate Euclidean distance between two vectors."""
        if len(a) != len(b):
            raise ValueError("Vectors must have same dimension")

        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

    @staticmethod
    def dot_product(a: List[float], b: List[float]) -> float:
        """Calculate dot product of two vectors."""
        if len(a) != len(b):
            raise ValueError("Vectors must have same dimension")

        return sum(x * y for x, y in zip(a, b))

    @staticmethod
    def manhattan_distance(a: List[float], b: List[float]) -> float:
        """Calculate Manhattan distance between two vectors."""
        if len(a) != len(b):
            raise ValueError("Vectors must have same dimension")

        return sum(abs(x - y) for x, y in zip(a, b))

    @staticmethod
    def normalize(v: List[float]) -> List[float]:
        """Normalize a vector to unit length."""
        magnitude = math.sqrt(sum(x * x for x in v))
        if magnitude == 0:
            return v
        return [x / magnitude for x in v]

    @staticmethod
    def magnitude(v: List[float]) -> float:
        """Calculate vector magnitude."""
        return math.sqrt(sum(x * x for x in v))

    @staticmethod
    def add(a: List[float], b: List[float]) -> List[float]:
        """Add two vectors."""
        return [x + y for x, y in zip(a, b)]

    @staticmethod
    def subtract(a: List[float], b: List[float]) -> List[float]:
        """Subtract vector b from a."""
        return [x - y for x, y in zip(a, b)]

    @staticmethod
    def scale(v: List[float], scalar: float) -> List[float]:
        """Scale a vector by a scalar."""
        return [x * scalar for x in v]

    @staticmethod
    def centroid(vectors: List[List[float]]) -> List[float]:
        """Calculate centroid of multiple vectors."""
        if not vectors:
            return []

        dim = len(vectors[0])
        result = [0.0] * dim

        for v in vectors:
            for i in range(dim):
                result[i] += v[i]

        n = len(vectors)
        return [x / n for x in result]


# =============================================================================
# VECTOR MEMORY STORE
# =============================================================================

class VectorMemoryStore:
    """
    SQLite-backed vector store with in-memory indexing.

    Features:
    - Persistent storage
    - Namespace support
    - Multiple distance metrics
    - Efficient similarity search
    """

    def __init__(
        self,
        db_path: str = "memory/vector/vectors.db",
        dimension: int = 1536,  # OpenAI ada-002 default
        metric: DistanceMetric = DistanceMetric.COSINE
    ):
        self.db_path = db_path
        self.dimension = dimension
        self.metric = metric
        self._cache: Dict[str, VectorEntry] = {}
        self._index_dirty = True
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the database."""
        if self._initialized:
            return

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vectors (
                id TEXT PRIMARY KEY,
                vector BLOB NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT,
                source TEXT,
                namespace TEXT DEFAULT 'default'
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_namespace ON vectors(namespace)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_source ON vectors(source)")

        conn.commit()
        conn.close()

        self._initialized = True
        logger.info(f"Vector memory store initialized at {self.db_path}")

    def _generate_id(self, content: str) -> str:
        """Generate unique entry ID."""
        data = f"{content}{datetime.now().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def _pack_vector(self, vector: List[float]) -> bytes:
        """Pack vector to bytes for storage."""
        return struct.pack(f'{len(vector)}f', *vector)

    def _unpack_vector(self, data: bytes) -> List[float]:
        """Unpack vector from bytes."""
        count = len(data) // 4  # 4 bytes per float
        return list(struct.unpack(f'{count}f', data))

    def _compute_similarity(
        self,
        a: List[float],
        b: List[float]
    ) -> float:
        """Compute similarity based on configured metric."""
        if self.metric == DistanceMetric.COSINE:
            return VectorOps.cosine_similarity(a, b)
        elif self.metric == DistanceMetric.EUCLIDEAN:
            # Convert distance to similarity (0-1 range)
            dist = VectorOps.euclidean_distance(a, b)
            return 1 / (1 + dist)
        elif self.metric == DistanceMetric.DOT_PRODUCT:
            return VectorOps.dot_product(a, b)
        elif self.metric == DistanceMetric.MANHATTAN:
            dist = VectorOps.manhattan_distance(a, b)
            return 1 / (1 + dist)
        else:
            return VectorOps.cosine_similarity(a, b)

    # -------------------------------------------------------------------------
    # Core Operations
    # -------------------------------------------------------------------------

    async def store(
        self,
        vector: List[float],
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        source: str = "unknown",
        namespace: str = "default",
        entry_id: Optional[str] = None
    ) -> str:
        """Store a vector entry."""
        await self.initialize()

        if len(vector) != self.dimension:
            # Pad or truncate to match dimension
            if len(vector) < self.dimension:
                vector = vector + [0.0] * (self.dimension - len(vector))
            else:
                vector = vector[:self.dimension]

        if entry_id is None:
            entry_id = self._generate_id(content)

        entry = VectorEntry(
            id=entry_id,
            vector=vector,
            content=content,
            metadata=metadata or {},
            created_at=datetime.now(),
            source=source,
            namespace=namespace
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO vectors
            (id, vector, content, metadata, created_at, source, namespace)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.id,
            self._pack_vector(entry.vector),
            entry.content,
            json.dumps(entry.metadata),
            entry.created_at.isoformat(),
            entry.source,
            entry.namespace
        ))

        conn.commit()
        conn.close()

        self._cache[entry_id] = entry
        self._index_dirty = True

        logger.debug(f"Stored vector: {entry_id}")
        return entry_id

    async def get(self, entry_id: str) -> Optional[VectorEntry]:
        """Get a vector entry by ID."""
        await self.initialize()

        if entry_id in self._cache:
            return self._cache[entry_id]

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM vectors WHERE id = ?", (entry_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        entry = self._row_to_entry(row)
        self._cache[entry_id] = entry
        return entry

    async def delete(self, entry_id: str) -> bool:
        """Delete a vector entry."""
        await self.initialize()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM vectors WHERE id = ?", (entry_id,))
        deleted = cursor.rowcount > 0

        conn.commit()
        conn.close()

        if entry_id in self._cache:
            del self._cache[entry_id]

        self._index_dirty = True
        return deleted

    async def search(
        self,
        query_vector: List[float],
        limit: int = 10,
        namespace: Optional[str] = None,
        min_score: float = 0.0,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Search for similar vectors."""
        await self.initialize()

        # Normalize query vector for cosine similarity
        if self.metric == DistanceMetric.COSINE:
            query_vector = VectorOps.normalize(query_vector)

        # Pad/truncate query to match dimension
        if len(query_vector) != self.dimension:
            if len(query_vector) < self.dimension:
                query_vector = query_vector + [0.0] * (self.dimension - len(query_vector))
            else:
                query_vector = query_vector[:self.dimension]

        # Get all entries (in production, would use proper indexing)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if namespace:
            cursor.execute(
                "SELECT * FROM vectors WHERE namespace = ?",
                (namespace,)
            )
        else:
            cursor.execute("SELECT * FROM vectors")

        rows = cursor.fetchall()
        conn.close()

        # Compute similarities
        results = []
        for row in rows:
            entry = self._row_to_entry(row)

            # Apply metadata filter
            if filter_metadata:
                match = all(
                    entry.metadata.get(k) == v
                    for k, v in filter_metadata.items()
                )
                if not match:
                    continue

            score = self._compute_similarity(query_vector, entry.vector)

            if score >= min_score:
                results.append((entry, score))

        # Sort by score (descending)
        results.sort(key=lambda x: x[1], reverse=True)

        # Build search results
        search_results = []
        for rank, (entry, score) in enumerate(results[:limit], 1):
            search_results.append(SearchResult(
                entry=entry,
                score=score,
                rank=rank
            ))

        return search_results

    async def search_by_content(
        self,
        content: str,
        embedder: Callable[[str], List[float]],
        limit: int = 10,
        namespace: Optional[str] = None
    ) -> List[SearchResult]:
        """Search by content using an embedder function."""
        query_vector = embedder(content)
        return await self.search(
            query_vector=query_vector,
            limit=limit,
            namespace=namespace
        )

    # -------------------------------------------------------------------------
    # Batch Operations
    # -------------------------------------------------------------------------

    async def store_batch(
        self,
        entries: List[Dict[str, Any]]
    ) -> List[str]:
        """Store multiple entries at once."""
        await self.initialize()

        ids = []
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for entry_data in entries:
            entry_id = entry_data.get("id") or self._generate_id(entry_data["content"])
            vector = entry_data["vector"]

            # Pad/truncate
            if len(vector) != self.dimension:
                if len(vector) < self.dimension:
                    vector = vector + [0.0] * (self.dimension - len(vector))
                else:
                    vector = vector[:self.dimension]

            cursor.execute("""
                INSERT OR REPLACE INTO vectors
                (id, vector, content, metadata, created_at, source, namespace)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                entry_id,
                self._pack_vector(vector),
                entry_data["content"],
                json.dumps(entry_data.get("metadata", {})),
                datetime.now().isoformat(),
                entry_data.get("source", "batch"),
                entry_data.get("namespace", "default")
            ))

            ids.append(entry_id)

        conn.commit()
        conn.close()

        self._index_dirty = True
        logger.info(f"Stored batch of {len(ids)} vectors")

        return ids

    async def get_by_namespace(
        self,
        namespace: str,
        limit: int = 100
    ) -> List[VectorEntry]:
        """Get all entries in a namespace."""
        await self.initialize()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM vectors WHERE namespace = ? LIMIT ?",
            (namespace, limit)
        )
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_entry(row) for row in rows]

    async def delete_namespace(self, namespace: str) -> int:
        """Delete all entries in a namespace."""
        await self.initialize()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM vectors WHERE namespace = ?", (namespace,))
        deleted = cursor.rowcount

        conn.commit()
        conn.close()

        # Clear cache entries for this namespace
        to_remove = [
            k for k, v in self._cache.items()
            if v.namespace == namespace
        ]
        for k in to_remove:
            del self._cache[k]

        self._index_dirty = True
        return deleted

    # -------------------------------------------------------------------------
    # Analysis Operations
    # -------------------------------------------------------------------------

    async def find_clusters(
        self,
        namespace: Optional[str] = None,
        n_clusters: int = 5
    ) -> List[Dict[str, Any]]:
        """Find clusters in the vector space using k-means-like approach."""
        entries = []

        if namespace:
            entries = await self.get_by_namespace(namespace, limit=1000)
        else:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM vectors LIMIT 1000")
            rows = cursor.fetchall()
            conn.close()
            entries = [self._row_to_entry(row) for row in rows]

        if len(entries) < n_clusters:
            return []

        vectors = [e.vector for e in entries]

        # Simple k-means clustering
        # Initialize centroids randomly
        import random
        centroids = random.sample(vectors, n_clusters)

        for _ in range(10):  # 10 iterations
            # Assign points to clusters
            clusters = [[] for _ in range(n_clusters)]

            for i, vec in enumerate(vectors):
                # Find nearest centroid
                best_cluster = 0
                best_dist = float('inf')

                for j, centroid in enumerate(centroids):
                    dist = VectorOps.euclidean_distance(vec, centroid)
                    if dist < best_dist:
                        best_dist = dist
                        best_cluster = j

                clusters[best_cluster].append(i)

            # Update centroids
            new_centroids = []
            for cluster_indices in clusters:
                if cluster_indices:
                    cluster_vectors = [vectors[i] for i in cluster_indices]
                    new_centroids.append(VectorOps.centroid(cluster_vectors))
                else:
                    new_centroids.append(random.choice(vectors))

            centroids = new_centroids

        # Build result
        result = []
        for i, cluster_indices in enumerate(clusters):
            cluster_entries = [entries[j] for j in cluster_indices]
            result.append({
                "cluster_id": i,
                "centroid": centroids[i][:10],  # First 10 dims
                "size": len(cluster_entries),
                "sample_contents": [e.content[:100] for e in cluster_entries[:3]]
            })

        return result

    async def find_outliers(
        self,
        namespace: Optional[str] = None,
        threshold: float = 2.0
    ) -> List[VectorEntry]:
        """Find outlier vectors (far from centroid)."""
        entries = []

        if namespace:
            entries = await self.get_by_namespace(namespace, limit=1000)
        else:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM vectors LIMIT 1000")
            rows = cursor.fetchall()
            conn.close()
            entries = [self._row_to_entry(row) for row in rows]

        if len(entries) < 10:
            return []

        vectors = [e.vector for e in entries]
        centroid = VectorOps.centroid(vectors)

        # Calculate distances from centroid
        distances = [
            VectorOps.euclidean_distance(v, centroid)
            for v in vectors
        ]

        # Calculate mean and std
        mean_dist = sum(distances) / len(distances)
        variance = sum((d - mean_dist) ** 2 for d in distances) / len(distances)
        std_dist = math.sqrt(variance)

        # Find outliers (beyond threshold std deviations)
        outliers = []
        for i, dist in enumerate(distances):
            if dist > mean_dist + threshold * std_dist:
                outliers.append(entries[i])

        return outliers

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _row_to_entry(self, row: tuple) -> VectorEntry:
        """Convert database row to VectorEntry."""
        return VectorEntry(
            id=row[0],
            vector=self._unpack_vector(row[1]),
            content=row[2],
            metadata=json.loads(row[3]) if row[3] else {},
            created_at=datetime.fromisoformat(row[4]) if row[4] else datetime.now(),
            source=row[5] or "unknown",
            namespace=row[6] or "default"
        )

    async def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        await self.initialize()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM vectors")
        total = cursor.fetchone()[0]

        cursor.execute("""
            SELECT namespace, COUNT(*) FROM vectors GROUP BY namespace
        """)
        namespaces = dict(cursor.fetchall())

        # Get file size
        storage_bytes = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0

        conn.close()

        return {
            "total_entries": total,
            "namespaces": namespaces,
            "dimension": self.dimension,
            "metric": self.metric.value,
            "storage_bytes": storage_bytes,
            "cache_size": len(self._cache)
        }


# =============================================================================
# VECTOR MEMORY MANAGER
# =============================================================================

class VectorMemoryManager:
    """
    High-level interface for vector memory operations.

    Provides:
    - Easy embedding and retrieval
    - Semantic search
    - Content deduplication
    - Namespace management
    """

    def __init__(
        self,
        store: Optional[VectorMemoryStore] = None,
        embedder: Optional[Callable[[str], List[float]]] = None
    ):
        self.store = store or VectorMemoryStore()
        self._embedder = embedder

    async def initialize(self) -> None:
        """Initialize the manager."""
        await self.store.initialize()

    def set_embedder(self, embedder: Callable[[str], List[float]]) -> None:
        """Set the embedding function."""
        self._embedder = embedder

    async def embed_and_store(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        namespace: str = "default"
    ) -> Optional[str]:
        """Embed content and store it."""
        if not self._embedder:
            logger.warning("No embedder configured")
            return None

        vector = self._embedder(content)

        return await self.store.store(
            vector=vector,
            content=content,
            metadata=metadata,
            namespace=namespace
        )

    async def search_similar(
        self,
        query: str,
        limit: int = 10,
        namespace: Optional[str] = None
    ) -> List[SearchResult]:
        """Search for similar content."""
        if not self._embedder:
            logger.warning("No embedder configured")
            return []

        query_vector = self._embedder(query)

        return await self.store.search(
            query_vector=query_vector,
            limit=limit,
            namespace=namespace
        )

    async def find_similar_to(
        self,
        entry_id: str,
        limit: int = 10
    ) -> List[SearchResult]:
        """Find entries similar to an existing entry."""
        entry = await self.store.get(entry_id)
        if not entry:
            return []

        results = await self.store.search(
            query_vector=entry.vector,
            limit=limit + 1,  # +1 because it will find itself
            namespace=entry.namespace
        )

        # Remove the entry itself from results
        return [r for r in results if r.entry.id != entry_id][:limit]

    async def deduplicate(
        self,
        namespace: str,
        similarity_threshold: float = 0.95
    ) -> int:
        """Remove near-duplicate entries."""
        entries = await self.store.get_by_namespace(namespace, limit=1000)

        to_delete = set()
        seen = {}

        for entry in entries:
            # Check if similar to any seen entry
            for seen_id, seen_vec in seen.items():
                sim = VectorOps.cosine_similarity(entry.vector, seen_vec)
                if sim >= similarity_threshold:
                    to_delete.add(entry.id)
                    break
            else:
                seen[entry.id] = entry.vector

        # Delete duplicates
        for entry_id in to_delete:
            await self.store.delete(entry_id)

        return len(to_delete)

    async def get_stats(self) -> Dict[str, Any]:
        """Get vector memory statistics."""
        return await self.store.get_stats()


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "DistanceMetric",
    "VectorEntry",
    "SearchResult",
    "VectorStats",
    "VectorOps",
    "VectorMemoryStore",
    "VectorMemoryManager"
]
