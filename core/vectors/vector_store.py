#!/usr/bin/env python3
"""
BAEL - Vector Store
High-performance vector storage and similarity search system.

Features:
- Multiple distance metrics (Cosine, Euclidean, Manhattan, Dot Product)
- HNSW-like index for approximate nearest neighbor
- Brute force exact search
- Vector normalization
- Batch operations
- Filtering support
- Persistence
- Metadata storage
- Namespace support
- Async operations
"""

import asyncio
import json
import logging
import math
import random
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from heapq import heappop, heappush, nlargest
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, TypeVar, Union)

logger = logging.getLogger(__name__)


T = TypeVar('T')
Vector = List[float]


# =============================================================================
# ENUMS
# =============================================================================

class DistanceMetric(Enum):
    """Distance/similarity metrics."""
    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    MANHATTAN = "manhattan"
    DOT_PRODUCT = "dot_product"
    HAMMING = "hamming"


class IndexType(Enum):
    """Index types."""
    FLAT = "flat"  # Brute force
    HNSW = "hnsw"  # Hierarchical Navigable Small World


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class VectorEntry:
    """A vector entry in the store."""
    id: str
    vector: Vector
    metadata: Dict[str, Any] = field(default_factory=dict)
    namespace: str = "default"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SearchResult:
    """Result of a vector search."""
    id: str
    score: float
    vector: Optional[Vector] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    distance: float = 0.0


@dataclass
class IndexConfig:
    """Index configuration."""
    index_type: IndexType = IndexType.FLAT
    dimension: int = 128
    metric: DistanceMetric = DistanceMetric.COSINE
    # HNSW parameters
    m: int = 16  # Number of connections per layer
    ef_construction: int = 200  # Size of dynamic list during construction
    ef_search: int = 50  # Size of dynamic list during search


@dataclass
class CollectionStats:
    """Statistics for a collection."""
    name: str
    vector_count: int = 0
    dimension: int = 0
    index_type: str = ""
    metric: str = ""
    namespaces: List[str] = field(default_factory=list)


# =============================================================================
# DISTANCE FUNCTIONS
# =============================================================================

class DistanceCalculator:
    """Calculate distances between vectors."""

    @staticmethod
    def cosine_similarity(v1: Vector, v2: Vector) -> float:
        """Calculate cosine similarity."""
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot / (norm1 * norm2)

    @staticmethod
    def cosine_distance(v1: Vector, v2: Vector) -> float:
        """Calculate cosine distance (1 - similarity)."""
        return 1 - DistanceCalculator.cosine_similarity(v1, v2)

    @staticmethod
    def euclidean_distance(v1: Vector, v2: Vector) -> float:
        """Calculate Euclidean distance."""
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2)))

    @staticmethod
    def manhattan_distance(v1: Vector, v2: Vector) -> float:
        """Calculate Manhattan distance."""
        return sum(abs(a - b) for a, b in zip(v1, v2))

    @staticmethod
    def dot_product(v1: Vector, v2: Vector) -> float:
        """Calculate dot product (higher is more similar)."""
        return sum(a * b for a, b in zip(v1, v2))

    @staticmethod
    def hamming_distance(v1: Vector, v2: Vector) -> float:
        """Calculate Hamming distance (for binary vectors)."""
        return sum(1 for a, b in zip(v1, v2) if a != b)

    @staticmethod
    def get_calculator(metric: DistanceMetric) -> Callable[[Vector, Vector], float]:
        """Get distance calculator for metric."""
        calculators = {
            DistanceMetric.COSINE: DistanceCalculator.cosine_distance,
            DistanceMetric.EUCLIDEAN: DistanceCalculator.euclidean_distance,
            DistanceMetric.MANHATTAN: DistanceCalculator.manhattan_distance,
            DistanceMetric.DOT_PRODUCT: lambda v1, v2: -DistanceCalculator.dot_product(v1, v2),
            DistanceMetric.HAMMING: DistanceCalculator.hamming_distance,
        }
        return calculators[metric]


# =============================================================================
# VECTOR UTILITIES
# =============================================================================

class VectorUtils:
    """Vector utility functions."""

    @staticmethod
    def normalize(vector: Vector) -> Vector:
        """Normalize vector to unit length."""
        norm = math.sqrt(sum(x * x for x in vector))
        if norm == 0:
            return vector
        return [x / norm for x in vector]

    @staticmethod
    def random_vector(dimension: int) -> Vector:
        """Generate random unit vector."""
        vector = [random.gauss(0, 1) for _ in range(dimension)]
        return VectorUtils.normalize(vector)

    @staticmethod
    def validate_dimension(vector: Vector, expected: int) -> bool:
        """Validate vector dimension."""
        return len(vector) == expected

    @staticmethod
    def mean_vector(vectors: List[Vector]) -> Vector:
        """Calculate mean of vectors."""
        if not vectors:
            return []

        dimension = len(vectors[0])
        result = [0.0] * dimension

        for vector in vectors:
            for i, v in enumerate(vector):
                result[i] += v

        n = len(vectors)
        return [x / n for x in result]

    @staticmethod
    def quantize(vector: Vector, bits: int = 8) -> List[int]:
        """Quantize vector to integer values."""
        max_val = 2 ** bits - 1
        min_v = min(vector)
        max_v = max(vector)
        range_v = max_v - min_v or 1

        return [int((v - min_v) / range_v * max_val) for v in vector]


# =============================================================================
# INDEX IMPLEMENTATIONS
# =============================================================================

class VectorIndex(ABC):
    """Abstract vector index."""

    @abstractmethod
    def add(self, id: str, vector: Vector) -> None:
        """Add vector to index."""
        pass

    @abstractmethod
    def remove(self, id: str) -> None:
        """Remove vector from index."""
        pass

    @abstractmethod
    def search(
        self,
        query: Vector,
        k: int,
        filter_ids: Optional[Set[str]] = None
    ) -> List[Tuple[str, float]]:
        """Search for k nearest neighbors."""
        pass


class FlatIndex(VectorIndex):
    """Brute force flat index."""

    def __init__(self, config: IndexConfig):
        self.config = config
        self._vectors: Dict[str, Vector] = {}
        self._distance = DistanceCalculator.get_calculator(config.metric)

    def add(self, id: str, vector: Vector) -> None:
        self._vectors[id] = vector

    def remove(self, id: str) -> None:
        if id in self._vectors:
            del self._vectors[id]

    def search(
        self,
        query: Vector,
        k: int,
        filter_ids: Optional[Set[str]] = None
    ) -> List[Tuple[str, float]]:
        results = []

        for id, vector in self._vectors.items():
            if filter_ids and id not in filter_ids:
                continue

            distance = self._distance(query, vector)
            results.append((id, distance))

        # Sort by distance (ascending)
        results.sort(key=lambda x: x[1])

        return results[:k]


class HNSWIndex(VectorIndex):
    """
    Hierarchical Navigable Small World index.
    Approximate nearest neighbor search.
    """

    def __init__(self, config: IndexConfig):
        self.config = config
        self._vectors: Dict[str, Vector] = {}
        self._distance = DistanceCalculator.get_calculator(config.metric)

        # Graph structure: level -> node_id -> list of neighbors
        self._graph: Dict[int, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
        self._entry_point: Optional[str] = None
        self._max_level: int = 0
        self._node_levels: Dict[str, int] = {}

        # Parameters
        self._m = config.m
        self._m_max = config.m * 2
        self._ef_construction = config.ef_construction
        self._ef_search = config.ef_search
        self._level_multiplier = 1 / math.log(config.m)

    def _random_level(self) -> int:
        """Generate random level for new node."""
        level = 0
        while random.random() < 0.5 and level < 16:
            level += 1
        return level

    def add(self, id: str, vector: Vector) -> None:
        self._vectors[id] = vector

        # First node
        if not self._entry_point:
            self._entry_point = id
            self._node_levels[id] = 0
            self._graph[0][id] = []
            return

        # Determine level for new node
        level = self._random_level()
        self._node_levels[id] = level

        # Initialize graph for this node
        for l in range(level + 1):
            self._graph[l][id] = []

        # Find entry point
        current = self._entry_point

        # Descend to insertion level
        for l in range(self._max_level, level + 1, -1):
            current = self._search_layer(vector, current, 1, l)[0][0]

        # Insert at each level
        for l in range(min(level, self._max_level), -1, -1):
            candidates = self._search_layer(vector, current, self._ef_construction, l)
            neighbors = self._select_neighbors(vector, candidates, self._m)

            # Add bidirectional connections
            self._graph[l][id] = [n[0] for n in neighbors]

            for neighbor_id, _ in neighbors:
                neighbor_conns = self._graph[l][neighbor_id]
                neighbor_conns.append(id)

                # Prune if too many connections
                if len(neighbor_conns) > self._m_max:
                    neighbor_vec = self._vectors[neighbor_id]
                    pruned = self._select_neighbors(
                        neighbor_vec,
                        [(n, self._distance(neighbor_vec, self._vectors[n])) for n in neighbor_conns],
                        self._m_max
                    )
                    self._graph[l][neighbor_id] = [n[0] for n in pruned]

            if candidates:
                current = candidates[0][0]

        # Update entry point if needed
        if level > self._max_level:
            self._max_level = level
            self._entry_point = id

    def _search_layer(
        self,
        query: Vector,
        entry_point: str,
        ef: int,
        level: int
    ) -> List[Tuple[str, float]]:
        """Search single layer."""
        visited = {entry_point}
        candidates = [(self._distance(query, self._vectors[entry_point]), entry_point)]
        result = [(-candidates[0][0], entry_point)]  # Max heap for results

        while candidates:
            dist, current = heappop(candidates)

            # Check if we can stop
            if result and dist > -result[0][0]:
                break

            # Explore neighbors
            for neighbor in self._graph[level].get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    neighbor_dist = self._distance(query, self._vectors[neighbor])

                    if len(result) < ef or neighbor_dist < -result[0][0]:
                        heappush(candidates, (neighbor_dist, neighbor))
                        heappush(result, (-neighbor_dist, neighbor))

                        if len(result) > ef:
                            heappop(result)

        return [(-d, id) for d, id in sorted(result, reverse=True)]

    def _select_neighbors(
        self,
        query: Vector,
        candidates: List[Tuple[str, float]],
        m: int
    ) -> List[Tuple[str, float]]:
        """Select M nearest neighbors."""
        sorted_candidates = sorted(candidates, key=lambda x: x[1])
        return sorted_candidates[:m]

    def remove(self, id: str) -> None:
        if id not in self._vectors:
            return

        del self._vectors[id]
        level = self._node_levels.get(id, 0)

        # Remove from all levels
        for l in range(level + 1):
            # Remove connections to this node
            for neighbor in self._graph[l].get(id, []):
                if neighbor in self._graph[l]:
                    self._graph[l][neighbor] = [
                        n for n in self._graph[l][neighbor] if n != id
                    ]

            # Remove node from level
            if id in self._graph[l]:
                del self._graph[l][id]

        if id in self._node_levels:
            del self._node_levels[id]

        # Update entry point if needed
        if self._entry_point == id:
            if self._vectors:
                self._entry_point = next(iter(self._vectors.keys()))
            else:
                self._entry_point = None
                self._max_level = 0

    def search(
        self,
        query: Vector,
        k: int,
        filter_ids: Optional[Set[str]] = None
    ) -> List[Tuple[str, float]]:
        if not self._entry_point:
            return []

        # Find entry point for lowest level
        current = self._entry_point

        for l in range(self._max_level, 0, -1):
            current = self._search_layer(query, current, 1, l)[0][0]

        # Search at level 0
        candidates = self._search_layer(query, current, self._ef_search, 0)

        # Apply filter
        if filter_ids:
            candidates = [(id, d) for id, d in candidates if id in filter_ids]

        return candidates[:k]


# =============================================================================
# COLLECTION
# =============================================================================

class VectorCollection:
    """A collection of vectors with indexing."""

    def __init__(self, name: str, config: IndexConfig):
        self.name = name
        self.config = config
        self._entries: Dict[str, VectorEntry] = {}
        self._namespaces: Dict[str, Set[str]] = defaultdict(set)
        self._index = self._create_index(config)

    def _create_index(self, config: IndexConfig) -> VectorIndex:
        """Create index based on config."""
        if config.index_type == IndexType.HNSW:
            return HNSWIndex(config)
        return FlatIndex(config)

    def upsert(
        self,
        id: str,
        vector: Vector,
        metadata: Optional[Dict[str, Any]] = None,
        namespace: str = "default"
    ) -> VectorEntry:
        """Insert or update a vector."""
        # Validate dimension
        if not VectorUtils.validate_dimension(vector, self.config.dimension):
            raise ValueError(f"Expected dimension {self.config.dimension}, got {len(vector)}")

        # Normalize for cosine similarity
        if self.config.metric == DistanceMetric.COSINE:
            vector = VectorUtils.normalize(vector)

        now = datetime.utcnow()

        if id in self._entries:
            # Update existing
            entry = self._entries[id]
            old_namespace = entry.namespace

            entry.vector = vector
            entry.metadata = metadata or {}
            entry.namespace = namespace
            entry.updated_at = now

            # Update namespace tracking
            if old_namespace != namespace:
                self._namespaces[old_namespace].discard(id)
                self._namespaces[namespace].add(id)
        else:
            # Create new
            entry = VectorEntry(
                id=id,
                vector=vector,
                metadata=metadata or {},
                namespace=namespace,
                created_at=now,
                updated_at=now
            )
            self._entries[id] = entry
            self._namespaces[namespace].add(id)

        # Update index
        self._index.add(id, vector)

        return entry

    def get(self, id: str) -> Optional[VectorEntry]:
        """Get a vector by ID."""
        return self._entries.get(id)

    def delete(self, id: str) -> bool:
        """Delete a vector."""
        if id not in self._entries:
            return False

        entry = self._entries[id]
        self._namespaces[entry.namespace].discard(id)
        del self._entries[id]
        self._index.remove(id)

        return True

    def search(
        self,
        query: Vector,
        k: int = 10,
        namespace: Optional[str] = None,
        filter_fn: Optional[Callable[[VectorEntry], bool]] = None,
        include_vectors: bool = False
    ) -> List[SearchResult]:
        """Search for similar vectors."""
        # Validate and normalize query
        if not VectorUtils.validate_dimension(query, self.config.dimension):
            raise ValueError(f"Expected dimension {self.config.dimension}, got {len(query)}")

        if self.config.metric == DistanceMetric.COSINE:
            query = VectorUtils.normalize(query)

        # Build filter set
        filter_ids = None
        if namespace:
            filter_ids = self._namespaces.get(namespace, set())

        if filter_fn:
            if filter_ids:
                filter_ids = {
                    id for id in filter_ids
                    if filter_fn(self._entries[id])
                }
            else:
                filter_ids = {
                    id for id, entry in self._entries.items()
                    if filter_fn(entry)
                }

        # Search
        results = self._index.search(query, k, filter_ids)

        # Build response
        return [
            SearchResult(
                id=id,
                score=1 - distance if self.config.metric in [DistanceMetric.COSINE, DistanceMetric.EUCLIDEAN] else -distance,
                distance=distance,
                vector=self._entries[id].vector if include_vectors else None,
                metadata=self._entries[id].metadata
            )
            for id, distance in results
            if id in self._entries
        ]

    def list_namespaces(self) -> List[str]:
        """List all namespaces."""
        return list(self._namespaces.keys())

    def count(self, namespace: Optional[str] = None) -> int:
        """Count vectors."""
        if namespace:
            return len(self._namespaces.get(namespace, set()))
        return len(self._entries)

    def stats(self) -> CollectionStats:
        """Get collection statistics."""
        return CollectionStats(
            name=self.name,
            vector_count=len(self._entries),
            dimension=self.config.dimension,
            index_type=self.config.index_type.value,
            metric=self.config.metric.value,
            namespaces=list(self._namespaces.keys())
        )


# =============================================================================
# VECTOR STORE
# =============================================================================

class VectorStore:
    """
    Vector Store for BAEL.

    High-performance vector storage and similarity search.
    """

    def __init__(self, default_dimension: int = 768):
        self._collections: Dict[str, VectorCollection] = {}
        self._default_dimension = default_dimension

    # -------------------------------------------------------------------------
    # COLLECTION MANAGEMENT
    # -------------------------------------------------------------------------

    def create_collection(
        self,
        name: str,
        dimension: Optional[int] = None,
        metric: DistanceMetric = DistanceMetric.COSINE,
        index_type: IndexType = IndexType.FLAT
    ) -> VectorCollection:
        """Create a new collection."""
        if name in self._collections:
            raise ValueError(f"Collection {name} already exists")

        config = IndexConfig(
            dimension=dimension or self._default_dimension,
            metric=metric,
            index_type=index_type
        )

        collection = VectorCollection(name, config)
        self._collections[name] = collection

        return collection

    def get_collection(self, name: str) -> Optional[VectorCollection]:
        """Get collection by name."""
        return self._collections.get(name)

    def delete_collection(self, name: str) -> bool:
        """Delete a collection."""
        if name in self._collections:
            del self._collections[name]
            return True
        return False

    def list_collections(self) -> List[str]:
        """List all collections."""
        return list(self._collections.keys())

    # -------------------------------------------------------------------------
    # VECTOR OPERATIONS
    # -------------------------------------------------------------------------

    def upsert(
        self,
        collection: str,
        id: str,
        vector: Vector,
        metadata: Optional[Dict[str, Any]] = None,
        namespace: str = "default"
    ) -> VectorEntry:
        """Upsert a vector."""
        coll = self._collections.get(collection)
        if not coll:
            raise ValueError(f"Collection {collection} not found")

        return coll.upsert(id, vector, metadata, namespace)

    def upsert_batch(
        self,
        collection: str,
        vectors: List[Tuple[str, Vector, Optional[Dict[str, Any]]]],
        namespace: str = "default"
    ) -> List[VectorEntry]:
        """Upsert multiple vectors."""
        return [
            self.upsert(collection, id, vector, metadata, namespace)
            for id, vector, metadata in vectors
        ]

    def get(self, collection: str, id: str) -> Optional[VectorEntry]:
        """Get a vector."""
        coll = self._collections.get(collection)
        if not coll:
            return None
        return coll.get(id)

    def delete(self, collection: str, id: str) -> bool:
        """Delete a vector."""
        coll = self._collections.get(collection)
        if not coll:
            return False
        return coll.delete(id)

    def search(
        self,
        collection: str,
        query: Vector,
        k: int = 10,
        namespace: Optional[str] = None,
        filter_fn: Optional[Callable[[VectorEntry], bool]] = None,
        include_vectors: bool = False
    ) -> List[SearchResult]:
        """Search for similar vectors."""
        coll = self._collections.get(collection)
        if not coll:
            return []

        return coll.search(query, k, namespace, filter_fn, include_vectors)

    # -------------------------------------------------------------------------
    # PERSISTENCE
    # -------------------------------------------------------------------------

    def save(self, path: str) -> None:
        """Save store to file."""
        data = {
            "collections": {}
        }

        for name, coll in self._collections.items():
            data["collections"][name] = {
                "config": {
                    "dimension": coll.config.dimension,
                    "metric": coll.config.metric.value,
                    "index_type": coll.config.index_type.value,
                },
                "entries": [
                    {
                        "id": entry.id,
                        "vector": entry.vector,
                        "metadata": entry.metadata,
                        "namespace": entry.namespace,
                        "created_at": entry.created_at.isoformat(),
                        "updated_at": entry.updated_at.isoformat(),
                    }
                    for entry in coll._entries.values()
                ]
            }

        with open(path, 'w') as f:
            json.dump(data, f)

    def load(self, path: str) -> None:
        """Load store from file."""
        with open(path, 'r') as f:
            data = json.load(f)

        for name, coll_data in data["collections"].items():
            config = coll_data["config"]

            self.create_collection(
                name=name,
                dimension=config["dimension"],
                metric=DistanceMetric(config["metric"]),
                index_type=IndexType(config["index_type"])
            )

            for entry_data in coll_data["entries"]:
                self.upsert(
                    collection=name,
                    id=entry_data["id"],
                    vector=entry_data["vector"],
                    metadata=entry_data["metadata"],
                    namespace=entry_data["namespace"]
                )

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def stats(self) -> Dict[str, CollectionStats]:
        """Get stats for all collections."""
        return {
            name: coll.stats()
            for name, coll in self._collections.items()
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Vector Store."""
    print("=" * 70)
    print("BAEL - VECTOR STORE DEMO")
    print("High-Performance Similarity Search")
    print("=" * 70)
    print()

    store = VectorStore(default_dimension=128)

    # 1. Create Collection
    print("1. CREATE COLLECTION:")
    print("-" * 40)

    coll = store.create_collection(
        name="documents",
        dimension=128,
        metric=DistanceMetric.COSINE,
        index_type=IndexType.FLAT
    )

    print(f"   Created: {coll.name}")
    print(f"   Dimension: {coll.config.dimension}")
    print(f"   Metric: {coll.config.metric.value}")
    print()

    # 2. Insert Vectors
    print("2. INSERT VECTORS:")
    print("-" * 40)

    # Create some sample vectors
    documents = [
        ("doc1", "Introduction to machine learning", {"category": "ml"}),
        ("doc2", "Deep learning fundamentals", {"category": "ml"}),
        ("doc3", "Natural language processing", {"category": "nlp"}),
        ("doc4", "Computer vision basics", {"category": "cv"}),
        ("doc5", "Reinforcement learning", {"category": "ml"}),
    ]

    # Simulate embeddings (in practice, use a real embedding model)
    for doc_id, title, metadata in documents:
        # Create pseudo-embedding based on title
        vector = VectorUtils.random_vector(128)
        store.upsert("documents", doc_id, vector, {"title": title, **metadata})
        print(f"   Inserted: {doc_id} - {title}")

    print()

    # 3. Search
    print("3. SIMILARITY SEARCH:")
    print("-" * 40)

    # Search with a query vector
    query = VectorUtils.random_vector(128)
    results = store.search("documents", query, k=3, include_vectors=False)

    print(f"   Query: random vector")
    print(f"   Results:")
    for r in results:
        print(f"      {r.id}: score={r.score:.4f}, {r.metadata.get('title', '')}")
    print()

    # 4. Namespaces
    print("4. NAMESPACES:")
    print("-" * 40)

    # Add vectors to different namespaces
    store.upsert("documents", "private1", VectorUtils.random_vector(128),
                 {"title": "Private doc 1"}, namespace="private")
    store.upsert("documents", "private2", VectorUtils.random_vector(128),
                 {"title": "Private doc 2"}, namespace="private")

    namespaces = coll.list_namespaces()
    print(f"   Namespaces: {namespaces}")
    print(f"   Default count: {coll.count('default')}")
    print(f"   Private count: {coll.count('private')}")
    print()

    # 5. Filtered Search
    print("5. FILTERED SEARCH:")
    print("-" * 40)

    # Search only ML documents
    results = store.search(
        "documents",
        query,
        k=5,
        filter_fn=lambda e: e.metadata.get("category") == "ml"
    )

    print(f"   Filter: category == 'ml'")
    for r in results:
        print(f"      {r.id}: {r.metadata.get('title', '')}")
    print()

    # 6. HNSW Index
    print("6. HNSW INDEX:")
    print("-" * 40)

    # Create collection with HNSW index
    hnsw_coll = store.create_collection(
        name="embeddings",
        dimension=128,
        metric=DistanceMetric.COSINE,
        index_type=IndexType.HNSW
    )

    # Add many vectors
    for i in range(100):
        vector = VectorUtils.random_vector(128)
        store.upsert("embeddings", f"vec_{i}", vector, {"index": i})

    print(f"   Collection: {hnsw_coll.name}")
    print(f"   Index type: {hnsw_coll.config.index_type.value}")
    print(f"   Vector count: {hnsw_coll.count()}")
    print()

    # 7. HNSW Search
    print("7. HNSW SEARCH:")
    print("-" * 40)

    query = VectorUtils.random_vector(128)
    results = store.search("embeddings", query, k=5)

    print(f"   Top 5 results:")
    for r in results:
        print(f"      {r.id}: score={r.score:.4f}")
    print()

    # 8. Distance Metrics
    print("8. DISTANCE METRICS:")
    print("-" * 40)

    v1 = [1.0, 0.0, 0.0]
    v2 = [0.0, 1.0, 0.0]
    v3 = [1.0, 1.0, 0.0]

    print(f"   v1 = {v1}")
    print(f"   v2 = {v2}")
    print(f"   v3 = {v3}")
    print()
    print(f"   Cosine(v1, v2): {DistanceCalculator.cosine_distance(v1, v2):.4f}")
    print(f"   Cosine(v1, v3): {DistanceCalculator.cosine_distance(v1, v3):.4f}")
    print(f"   Euclidean(v1, v2): {DistanceCalculator.euclidean_distance(v1, v2):.4f}")
    print(f"   Manhattan(v1, v2): {DistanceCalculator.manhattan_distance(v1, v2):.4f}")
    print()

    # 9. Vector Utilities
    print("9. VECTOR UTILITIES:")
    print("-" * 40)

    v = [3.0, 4.0]
    normalized = VectorUtils.normalize(v)

    print(f"   Original: {v}")
    print(f"   Normalized: {normalized}")
    print(f"   Norm: {math.sqrt(sum(x*x for x in normalized)):.4f}")
    print()

    # 10. Statistics
    print("10. STATISTICS:")
    print("-" * 40)

    stats = store.stats()
    for name, s in stats.items():
        print(f"   {name}:")
        print(f"      Vectors: {s.vector_count}")
        print(f"      Dimension: {s.dimension}")
        print(f"      Index: {s.index_type}")
    print()

    # 11. Batch Operations
    print("11. BATCH OPERATIONS:")
    print("-" * 40)

    batch = [
        ("batch1", VectorUtils.random_vector(128), {"batch": True}),
        ("batch2", VectorUtils.random_vector(128), {"batch": True}),
        ("batch3", VectorUtils.random_vector(128), {"batch": True}),
    ]

    entries = store.upsert_batch("documents", batch)
    print(f"   Inserted {len(entries)} vectors in batch")
    print()

    # 12. Delete
    print("12. DELETE VECTOR:")
    print("-" * 40)

    before = coll.count()
    store.delete("documents", "doc1")
    after = coll.count()

    print(f"   Deleted: doc1")
    print(f"   Count before: {before}")
    print(f"   Count after: {after}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Vector Store Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
