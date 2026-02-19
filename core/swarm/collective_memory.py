"""
BAEL Collective Memory
=======================

Shared memory system for swarm agents.
Enables knowledge sharing and synchronization.

Features:
- Distributed key-value store
- Knowledge graphs
- Vector similarity search
- Memory synchronization
- Conflict resolution
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class MemoryType(Enum):
    """Memory types."""
    EPHEMERAL = "ephemeral"  # Short-lived
    WORKING = "working"  # Session-based
    LONG_TERM = "long_term"  # Persistent
    SEMANTIC = "semantic"  # Vector-indexed


class ConflictResolution(Enum):
    """Conflict resolution strategies."""
    LAST_WRITE_WINS = "last_write_wins"
    FIRST_WRITE_WINS = "first_write_wins"
    MERGE = "merge"
    VOTE = "vote"
    VERSION_VECTOR = "version_vector"


@dataclass
class MemoryEntry:
    """A memory entry."""
    key: str
    value: Any

    # Type
    memory_type: MemoryType = MemoryType.WORKING

    # Versioning
    version: int = 1
    vector_clock: Dict[str, int] = field(default_factory=dict)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""

    # TTL
    expires_at: Optional[datetime] = None

    # Tags for semantic search
    tags: List[str] = field(default_factory=list)
    embedding: Optional[List[float]] = None


@dataclass
class SharedKnowledge:
    """Shared knowledge item."""
    id: str
    topic: str
    content: Any

    # Source
    sources: List[str] = field(default_factory=list)
    confidence: float = 1.0

    # Validation
    validated_by: List[str] = field(default_factory=list)
    contradicted_by: List[str] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)


class DistributedCache:
    """Distributed cache with replication."""

    def __init__(
        self,
        replication_factor: int = 2,
    ):
        self.replication_factor = replication_factor

        # Local storage
        self._store: Dict[str, MemoryEntry] = {}

        # Replication tracking
        self._replicas: Dict[str, Set[str]] = {}  # key -> nodes

        # Stats
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
        }

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key not in self._store:
            self.stats["misses"] += 1
            return None

        entry = self._store[key]

        # Check expiration
        if entry.expires_at and datetime.now() > entry.expires_at:
            del self._store[key]
            self.stats["evictions"] += 1
            return None

        self.stats["hits"] += 1
        return entry.value

    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
        node_id: str = "",
    ) -> None:
        """Set value in cache."""
        expires_at = None
        if ttl_seconds:
            expires_at = datetime.now() + timedelta(seconds=ttl_seconds)

        if key in self._store:
            entry = self._store[key]
            entry.value = value
            entry.version += 1
            entry.updated_at = datetime.now()
            entry.expires_at = expires_at

            if node_id:
                entry.vector_clock[node_id] = entry.vector_clock.get(node_id, 0) + 1
        else:
            self._store[key] = MemoryEntry(
                key=key,
                value=value,
                expires_at=expires_at,
                created_by=node_id,
                vector_clock={node_id: 1} if node_id else {},
            )

    def delete(self, key: str) -> bool:
        """Delete from cache."""
        if key in self._store:
            del self._store[key]
            return True
        return False

    def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        if pattern == "*":
            return list(self._store.keys())

        import fnmatch
        return [k for k in self._store.keys() if fnmatch.fnmatch(k, pattern)]


class MemorySync:
    """Memory synchronization between nodes."""

    def __init__(
        self,
        resolution: ConflictResolution = ConflictResolution.LAST_WRITE_WINS,
    ):
        self.resolution = resolution

        # Pending syncs
        self._pending: List[Dict[str, Any]] = []

        # Conflict log
        self._conflicts: List[Dict[str, Any]] = []

    def prepare_sync(
        self,
        entry: MemoryEntry,
        source_node: str,
    ) -> Dict[str, Any]:
        """Prepare entry for synchronization."""
        return {
            "key": entry.key,
            "value": entry.value,
            "version": entry.version,
            "vector_clock": entry.vector_clock.copy(),
            "updated_at": entry.updated_at.isoformat(),
            "source_node": source_node,
        }

    def apply_sync(
        self,
        cache: DistributedCache,
        sync_data: Dict[str, Any],
        target_node: str,
    ) -> bool:
        """Apply synchronization to cache."""
        key = sync_data["key"]

        if key not in cache._store:
            # No conflict, apply directly
            cache.set(key, sync_data["value"], node_id=sync_data["source_node"])
            return True

        local = cache._store[key]

        # Check for conflict
        if self._is_conflict(local.vector_clock, sync_data["vector_clock"]):
            return self._resolve_conflict(cache, local, sync_data, target_node)

        # Check if incoming is newer
        if self._is_newer(sync_data["vector_clock"], local.vector_clock):
            cache.set(key, sync_data["value"], node_id=sync_data["source_node"])
            return True

        return False

    def _is_conflict(
        self,
        vc1: Dict[str, int],
        vc2: Dict[str, int],
    ) -> bool:
        """Check if vector clocks indicate conflict."""
        all_nodes = set(vc1.keys()) | set(vc2.keys())

        vc1_greater = False
        vc2_greater = False

        for node in all_nodes:
            v1 = vc1.get(node, 0)
            v2 = vc2.get(node, 0)

            if v1 > v2:
                vc1_greater = True
            elif v2 > v1:
                vc2_greater = True

        return vc1_greater and vc2_greater

    def _is_newer(
        self,
        vc1: Dict[str, int],
        vc2: Dict[str, int],
    ) -> bool:
        """Check if vc1 is newer than vc2."""
        all_nodes = set(vc1.keys()) | set(vc2.keys())

        for node in all_nodes:
            if vc1.get(node, 0) < vc2.get(node, 0):
                return False

        return sum(vc1.values()) > sum(vc2.values())

    def _resolve_conflict(
        self,
        cache: DistributedCache,
        local: MemoryEntry,
        remote: Dict[str, Any],
        target_node: str,
    ) -> bool:
        """Resolve a conflict."""
        self._conflicts.append({
            "key": local.key,
            "local_value": local.value,
            "remote_value": remote["value"],
            "resolution": self.resolution.value,
            "timestamp": datetime.now().isoformat(),
        })

        if self.resolution == ConflictResolution.LAST_WRITE_WINS:
            remote_time = datetime.fromisoformat(remote["updated_at"])
            if remote_time > local.updated_at:
                cache.set(local.key, remote["value"], node_id=remote["source_node"])
                return True
            return False

        elif self.resolution == ConflictResolution.FIRST_WRITE_WINS:
            return False

        elif self.resolution == ConflictResolution.MERGE:
            # Attempt merge if both are dicts
            if isinstance(local.value, dict) and isinstance(remote["value"], dict):
                merged = {**local.value, **remote["value"]}
                cache.set(local.key, merged, node_id=target_node)
                return True
            # Otherwise, last write wins
            remote_time = datetime.fromisoformat(remote["updated_at"])
            if remote_time > local.updated_at:
                cache.set(local.key, remote["value"], node_id=remote["source_node"])
                return True
            return False

        return False


class CollectiveMemory:
    """
    Collective memory system for BAEL swarm.

    Enables shared knowledge across all agents.
    """

    def __init__(
        self,
        node_id: str = "primary",
        resolution: ConflictResolution = ConflictResolution.LAST_WRITE_WINS,
    ):
        self.node_id = node_id

        # Storage layers
        self.ephemeral = DistributedCache()
        self.working = DistributedCache()
        self.long_term = DistributedCache()

        # Knowledge base
        self._knowledge: Dict[str, SharedKnowledge] = {}

        # Synchronization
        self.sync = MemorySync(resolution=resolution)

        # Vector store for semantic search
        self._embeddings: Dict[str, Tuple[List[float], str]] = {}

        # Subscriptions
        self._subscriptions: Dict[str, List[Callable]] = {}

        # Stats
        self.stats = {
            "reads": 0,
            "writes": 0,
            "syncs": 0,
            "conflicts": 0,
        }

    def store(
        self,
        key: str,
        value: Any,
        memory_type: MemoryType = MemoryType.WORKING,
        ttl_seconds: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ) -> None:
        """
        Store a value in collective memory.

        Args:
            key: Storage key
            value: Value to store
            memory_type: Type of memory
            ttl_seconds: Time-to-live
            tags: Tags for semantic search
        """
        self.stats["writes"] += 1

        cache = self._get_cache(memory_type)
        cache.set(key, value, ttl_seconds=ttl_seconds, node_id=self.node_id)

        # Notify subscribers
        self._notify(key, value, "write")

        logger.debug(f"Stored {key} in {memory_type.value}")

    def retrieve(
        self,
        key: str,
        memory_type: Optional[MemoryType] = None,
    ) -> Optional[Any]:
        """
        Retrieve a value from collective memory.

        Args:
            key: Storage key
            memory_type: Specific memory type (or search all)

        Returns:
            Stored value or None
        """
        self.stats["reads"] += 1

        if memory_type:
            return self._get_cache(memory_type).get(key)

        # Search all caches
        for cache in [self.ephemeral, self.working, self.long_term]:
            value = cache.get(key)
            if value is not None:
                return value

        return None

    def delete(
        self,
        key: str,
        memory_type: Optional[MemoryType] = None,
    ) -> bool:
        """Delete a value."""
        if memory_type:
            return self._get_cache(memory_type).delete(key)

        deleted = False
        for cache in [self.ephemeral, self.working, self.long_term]:
            if cache.delete(key):
                deleted = True

        return deleted

    def share_knowledge(
        self,
        topic: str,
        content: Any,
        confidence: float = 1.0,
    ) -> SharedKnowledge:
        """
        Share knowledge with the swarm.

        Args:
            topic: Knowledge topic
            content: Knowledge content
            confidence: Confidence level

        Returns:
            SharedKnowledge item
        """
        knowledge_id = hashlib.md5(
            f"{topic}:{datetime.now()}".encode()
        ).hexdigest()[:12]

        knowledge = SharedKnowledge(
            id=knowledge_id,
            topic=topic,
            content=content,
            sources=[self.node_id],
            confidence=confidence,
        )

        self._knowledge[knowledge_id] = knowledge

        # Store in long-term memory
        self.store(
            f"knowledge:{knowledge_id}",
            knowledge,
            memory_type=MemoryType.LONG_TERM,
        )

        return knowledge

    def validate_knowledge(
        self,
        knowledge_id: str,
        agrees: bool,
        validator: str,
    ) -> None:
        """Validate or contradict knowledge."""
        if knowledge_id not in self._knowledge:
            return

        knowledge = self._knowledge[knowledge_id]

        if agrees:
            if validator not in knowledge.validated_by:
                knowledge.validated_by.append(validator)
                # Increase confidence
                knowledge.confidence = min(1.0, knowledge.confidence + 0.1)
        else:
            if validator not in knowledge.contradicted_by:
                knowledge.contradicted_by.append(validator)
                # Decrease confidence
                knowledge.confidence = max(0.0, knowledge.confidence - 0.1)

    def search_knowledge(
        self,
        topic: Optional[str] = None,
        min_confidence: float = 0.0,
    ) -> List[SharedKnowledge]:
        """Search knowledge base."""
        results = []

        for knowledge in self._knowledge.values():
            if topic and topic.lower() not in knowledge.topic.lower():
                continue
            if knowledge.confidence < min_confidence:
                continue
            results.append(knowledge)

        return sorted(results, key=lambda k: k.confidence, reverse=True)

    def add_embedding(
        self,
        key: str,
        embedding: List[float],
        content: str,
    ) -> None:
        """Add embedding for semantic search."""
        self._embeddings[key] = (embedding, content)

    def semantic_search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
    ) -> List[Tuple[str, float, str]]:
        """
        Search by semantic similarity.

        Args:
            query_embedding: Query vector
            top_k: Number of results

        Returns:
            List of (key, similarity, content)
        """
        results = []

        for key, (embedding, content) in self._embeddings.items():
            similarity = self._cosine_similarity(query_embedding, embedding)
            results.append((key, similarity, content))

        results.sort(key=lambda x: x[1], reverse=True)

        return results[:top_k]

    def _cosine_similarity(
        self,
        v1: List[float],
        v2: List[float],
    ) -> float:
        """Calculate cosine similarity."""
        if len(v1) != len(v2):
            return 0.0

        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = sum(a * a for a in v1) ** 0.5
        norm2 = sum(b * b for b in v2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot / (norm1 * norm2)

    def subscribe(
        self,
        pattern: str,
        callback: Callable,
    ) -> None:
        """Subscribe to memory changes."""
        if pattern not in self._subscriptions:
            self._subscriptions[pattern] = []
        self._subscriptions[pattern].append(callback)

    def _notify(
        self,
        key: str,
        value: Any,
        event_type: str,
    ) -> None:
        """Notify subscribers."""
        import fnmatch

        for pattern, callbacks in self._subscriptions.items():
            if fnmatch.fnmatch(key, pattern):
                for callback in callbacks:
                    try:
                        callback(key, value, event_type)
                    except Exception as e:
                        logger.error(f"Subscription callback error: {e}")

    def _get_cache(self, memory_type: MemoryType) -> DistributedCache:
        """Get cache by type."""
        if memory_type == MemoryType.EPHEMERAL:
            return self.ephemeral
        elif memory_type == MemoryType.LONG_TERM:
            return self.long_term
        else:
            return self.working

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return {
            **self.stats,
            "ephemeral_keys": len(self.ephemeral._store),
            "working_keys": len(self.working._store),
            "long_term_keys": len(self.long_term._store),
            "knowledge_items": len(self._knowledge),
            "embeddings": len(self._embeddings),
        }


def demo():
    """Demonstrate collective memory."""
    print("=" * 60)
    print("BAEL Collective Memory Demo")
    print("=" * 60)

    memory = CollectiveMemory(node_id="agent_1")

    # Subscribe to changes
    def on_change(key, value, event):
        print(f"  [Event] {event}: {key}")

    memory.subscribe("task:*", on_change)

    # Store values
    print("\nStoring values...")
    memory.store("config:debug", True, MemoryType.WORKING)
    memory.store("task:123", {"status": "running"}, MemoryType.EPHEMERAL, ttl_seconds=60)
    memory.store("result:analysis", {"score": 0.95}, MemoryType.LONG_TERM)

    # Retrieve
    print("\nRetrieving values...")
    print(f"  config:debug = {memory.retrieve('config:debug')}")
    print(f"  task:123 = {memory.retrieve('task:123')}")
    print(f"  result:analysis = {memory.retrieve('result:analysis')}")

    # Share knowledge
    print("\nSharing knowledge...")
    knowledge = memory.share_knowledge(
        topic="best_practices",
        content={"pattern": "use_async", "benefit": "performance"},
        confidence=0.8,
    )

    print(f"  Created: {knowledge.id}")

    # Validate
    memory.validate_knowledge(knowledge.id, agrees=True, validator="agent_2")
    memory.validate_knowledge(knowledge.id, agrees=True, validator="agent_3")

    # Search
    results = memory.search_knowledge(topic="best", min_confidence=0.5)
    print(f"\nKnowledge search results: {len(results)}")
    for k in results:
        print(f"  - {k.topic}: confidence={k.confidence:.2f}")

    # Semantic search
    print("\nSemantic search...")
    memory.add_embedding("doc:1", [0.1, 0.2, 0.3, 0.4], "Python async programming")
    memory.add_embedding("doc:2", [0.15, 0.25, 0.3, 0.35], "Async/await patterns")
    memory.add_embedding("doc:3", [0.9, 0.1, 0.0, 0.0], "Database optimization")

    query = [0.12, 0.22, 0.32, 0.38]
    results = memory.semantic_search(query, top_k=2)
    for key, sim, content in results:
        print(f"  {key}: {content} (similarity: {sim:.3f})")

    print(f"\nStats: {memory.get_stats()}")


if __name__ == "__main__":
    demo()
