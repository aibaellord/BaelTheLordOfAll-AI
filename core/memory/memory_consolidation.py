#!/usr/bin/env python3
"""
BAEL - Memory Consolidation System
Advanced long-term memory management and consolidation.

This module implements sophisticated memory consolidation
for converting short-term experiences into stable long-term
knowledge with intelligent compression and retrieval.

Features:
- Working to long-term memory transfer
- Memory compression and summarization
- Importance-based retention
- Temporal decay management
- Associative memory networks
- Memory reconstruction
- Forgetting curves implementation
- Semantic clustering
- Experience replay
- Memory indexing
- Cross-reference linking
- Memory defragmentation
"""

import asyncio
import hashlib
import json
import logging
import math
import random
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    TypeVar, Union)
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class MemoryType(Enum):
    """Types of memory."""
    EPISODIC = "episodic"      # Event-based memories
    SEMANTIC = "semantic"       # Fact-based knowledge
    PROCEDURAL = "procedural"   # How-to knowledge
    WORKING = "working"         # Short-term active memory
    SENSORY = "sensory"         # Raw sensory input


class MemoryState(Enum):
    """State of a memory."""
    ACTIVE = "active"
    CONSOLIDATING = "consolidating"
    CONSOLIDATED = "consolidated"
    DECAYING = "decaying"
    ARCHIVED = "archived"
    FORGOTTEN = "forgotten"


class ConsolidationPhase(Enum):
    """Phases of memory consolidation."""
    ENCODING = "encoding"
    STABILIZATION = "stabilization"
    INTEGRATION = "integration"
    COMPRESSION = "compression"
    STORAGE = "storage"


class ImportanceLevel(Enum):
    """Importance levels for memory retention."""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    TRIVIAL = 5


class RetrievalMode(Enum):
    """Modes of memory retrieval."""
    EXACT = "exact"
    SEMANTIC = "semantic"
    ASSOCIATIVE = "associative"
    TEMPORAL = "temporal"
    CONTEXTUAL = "contextual"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class MemoryMetadata:
    """Metadata for a memory item."""
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    importance: ImportanceLevel = ImportanceLevel.NORMAL
    strength: float = 1.0  # 0.0 to 1.0
    decay_rate: float = 0.1
    tags: List[str] = field(default_factory=list)
    source: str = ""
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryItem:
    """A single memory item."""
    id: str = field(default_factory=lambda: str(uuid4()))
    type: MemoryType = MemoryType.EPISODIC
    state: MemoryState = MemoryState.ACTIVE
    content: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    embedding: List[float] = field(default_factory=list)
    associations: List[str] = field(default_factory=list)  # Related memory IDs
    metadata: MemoryMetadata = field(default_factory=MemoryMetadata)

    def decay(self, time_delta_hours: float) -> None:
        """Apply decay to memory strength."""
        # Ebbinghaus forgetting curve
        decay_factor = math.exp(-self.metadata.decay_rate * time_delta_hours)
        self.metadata.strength *= decay_factor

        if self.metadata.strength < 0.1:
            self.state = MemoryState.DECAYING
        if self.metadata.strength < 0.01:
            self.state = MemoryState.FORGOTTEN

    def reinforce(self, amount: float = 0.2) -> None:
        """Reinforce memory through access."""
        self.metadata.strength = min(1.0, self.metadata.strength + amount)
        self.metadata.access_count += 1
        self.metadata.last_accessed = datetime.now()

        # Reduce decay rate with reinforcement (spaced repetition effect)
        self.metadata.decay_rate *= 0.9


@dataclass
class MemoryCluster:
    """A cluster of related memories."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    memory_ids: List[str] = field(default_factory=list)
    centroid: List[float] = field(default_factory=list)
    coherence: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ConsolidationJob:
    """A memory consolidation job."""
    id: str = field(default_factory=lambda: str(uuid4()))
    memory_ids: List[str] = field(default_factory=list)
    phase: ConsolidationPhase = ConsolidationPhase.ENCODING
    progress: float = 0.0
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    result: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalResult:
    """Result of memory retrieval."""
    memories: List[MemoryItem] = field(default_factory=list)
    scores: List[float] = field(default_factory=list)
    total_found: int = 0
    retrieval_time_ms: float = 0.0
    mode: RetrievalMode = RetrievalMode.EXACT


# =============================================================================
# MEMORY STORES
# =============================================================================

class MemoryStore(ABC):
    """Base class for memory storage."""

    @abstractmethod
    async def store(self, memory: MemoryItem) -> bool:
        """Store a memory item."""
        pass

    @abstractmethod
    async def retrieve(self, memory_id: str) -> Optional[MemoryItem]:
        """Retrieve a memory by ID."""
        pass

    @abstractmethod
    async def search(
        self,
        query: Dict[str, Any],
        limit: int = 10
    ) -> List[MemoryItem]:
        """Search memories."""
        pass

    @abstractmethod
    async def delete(self, memory_id: str) -> bool:
        """Delete a memory."""
        pass


class WorkingMemoryStore(MemoryStore):
    """
    Fast, limited-capacity working memory.

    Implements a bounded buffer with rapid access.
    """

    def __init__(self, capacity: int = 7):  # Miller's magic number
        self.capacity = capacity
        self.memories: Dict[str, MemoryItem] = {}
        self.access_order: List[str] = []

    async def store(self, memory: MemoryItem) -> bool:
        """Store in working memory with capacity limit."""
        if len(self.memories) >= self.capacity:
            # Remove least recently used
            if self.access_order:
                lru_id = self.access_order.pop(0)
                del self.memories[lru_id]

        self.memories[memory.id] = memory
        self.access_order.append(memory.id)
        return True

    async def retrieve(self, memory_id: str) -> Optional[MemoryItem]:
        """Retrieve from working memory."""
        memory = self.memories.get(memory_id)
        if memory:
            # Move to end of access order
            if memory_id in self.access_order:
                self.access_order.remove(memory_id)
            self.access_order.append(memory_id)
            memory.reinforce(0.1)
        return memory

    async def search(
        self,
        query: Dict[str, Any],
        limit: int = 10
    ) -> List[MemoryItem]:
        """Search working memory."""
        results = []
        for memory in self.memories.values():
            # Simple content matching
            matches = True
            for key, value in query.items():
                if key in memory.content:
                    if memory.content[key] != value:
                        matches = False
                        break
                elif key in memory.metadata.tags:
                    continue
                else:
                    matches = False
                    break

            if matches:
                results.append(memory)

        return results[:limit]

    async def delete(self, memory_id: str) -> bool:
        """Delete from working memory."""
        if memory_id in self.memories:
            del self.memories[memory_id]
            if memory_id in self.access_order:
                self.access_order.remove(memory_id)
            return True
        return False

    def get_all(self) -> List[MemoryItem]:
        """Get all working memories."""
        return list(self.memories.values())


class LongTermMemoryStore(MemoryStore):
    """
    High-capacity long-term memory storage.

    Implements indexed storage with semantic clustering.
    """

    def __init__(self):
        self.memories: Dict[str, MemoryItem] = {}
        self.index_by_type: Dict[MemoryType, List[str]] = defaultdict(list)
        self.index_by_tag: Dict[str, List[str]] = defaultdict(list)
        self.clusters: Dict[str, MemoryCluster] = {}

    async def store(self, memory: MemoryItem) -> bool:
        """Store in long-term memory with indexing."""
        self.memories[memory.id] = memory

        # Index by type
        self.index_by_type[memory.type].append(memory.id)

        # Index by tags
        for tag in memory.metadata.tags:
            self.index_by_tag[tag].append(memory.id)

        return True

    async def retrieve(self, memory_id: str) -> Optional[MemoryItem]:
        """Retrieve from long-term memory."""
        memory = self.memories.get(memory_id)
        if memory:
            memory.reinforce(0.15)
        return memory

    async def search(
        self,
        query: Dict[str, Any],
        limit: int = 10
    ) -> List[MemoryItem]:
        """Search long-term memory."""
        candidates = set()

        # Search by type
        if "type" in query:
            memory_type = MemoryType(query["type"])
            candidates.update(self.index_by_type.get(memory_type, []))

        # Search by tags
        if "tags" in query:
            for tag in query["tags"]:
                candidates.update(self.index_by_tag.get(tag, []))

        # If no index matches, search all
        if not candidates:
            candidates = set(self.memories.keys())

        results = []
        for memory_id in candidates:
            memory = self.memories.get(memory_id)
            if memory and memory.state != MemoryState.FORGOTTEN:
                results.append(memory)

        # Sort by strength
        results.sort(key=lambda m: m.metadata.strength, reverse=True)
        return results[:limit]

    async def delete(self, memory_id: str) -> bool:
        """Delete from long-term memory."""
        memory = self.memories.get(memory_id)
        if memory:
            # Remove from indexes
            if memory.id in self.index_by_type[memory.type]:
                self.index_by_type[memory.type].remove(memory.id)
            for tag in memory.metadata.tags:
                if memory.id in self.index_by_tag[tag]:
                    self.index_by_tag[tag].remove(memory.id)

            del self.memories[memory_id]
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get memory store statistics."""
        active = sum(1 for m in self.memories.values() if m.state == MemoryState.ACTIVE)
        consolidated = sum(1 for m in self.memories.values() if m.state == MemoryState.CONSOLIDATED)

        return {
            "total_memories": len(self.memories),
            "active": active,
            "consolidated": consolidated,
            "clusters": len(self.clusters),
            "indexed_tags": len(self.index_by_tag)
        }


# =============================================================================
# CONSOLIDATION ENGINE
# =============================================================================

class ConsolidationEngine:
    """
    Handles memory consolidation process.

    Transfers working memory to long-term storage
    with compression and integration.
    """

    def __init__(
        self,
        working_memory: WorkingMemoryStore,
        long_term_memory: LongTermMemoryStore
    ):
        self.working = working_memory
        self.long_term = long_term_memory
        self.jobs: Dict[str, ConsolidationJob] = {}
        self.compression_ratio = 0.5  # Target 50% compression

    async def consolidate(
        self,
        memories: List[MemoryItem],
        importance_threshold: ImportanceLevel = ImportanceLevel.LOW
    ) -> ConsolidationJob:
        """Start consolidation process."""
        # Filter by importance
        important_memories = [
            m for m in memories
            if m.metadata.importance.value <= importance_threshold.value
        ]

        job = ConsolidationJob(
            memory_ids=[m.id for m in important_memories]
        )
        self.jobs[job.id] = job

        # Run consolidation phases
        await self._run_phases(job, important_memories)

        return job

    async def _run_phases(
        self,
        job: ConsolidationJob,
        memories: List[MemoryItem]
    ) -> None:
        """Run all consolidation phases."""
        # Phase 1: Encoding
        job.phase = ConsolidationPhase.ENCODING
        encoded = await self._encode(memories)
        job.progress = 0.2

        # Phase 2: Stabilization
        job.phase = ConsolidationPhase.STABILIZATION
        stabilized = await self._stabilize(encoded)
        job.progress = 0.4

        # Phase 3: Integration
        job.phase = ConsolidationPhase.INTEGRATION
        integrated = await self._integrate(stabilized)
        job.progress = 0.6

        # Phase 4: Compression
        job.phase = ConsolidationPhase.COMPRESSION
        compressed = await self._compress(integrated)
        job.progress = 0.8

        # Phase 5: Storage
        job.phase = ConsolidationPhase.STORAGE
        await self._store(compressed)
        job.progress = 1.0

        job.completed_at = datetime.now()
        job.result = {
            "memories_processed": len(memories),
            "memories_stored": len(compressed),
            "compression_achieved": 1 - len(compressed) / max(len(memories), 1)
        }

    async def _encode(self, memories: List[MemoryItem]) -> List[MemoryItem]:
        """Encode memories for consolidation."""
        for memory in memories:
            # Generate summary if not present
            if not memory.summary:
                memory.summary = self._generate_summary(memory.content)

            # Generate embedding placeholder
            if not memory.embedding:
                memory.embedding = self._generate_embedding(memory.content)

            memory.state = MemoryState.CONSOLIDATING

        return memories

    async def _stabilize(self, memories: List[MemoryItem]) -> List[MemoryItem]:
        """Stabilize memory representations."""
        for memory in memories:
            # Increase strength for stabilized memories
            memory.metadata.strength = min(1.0, memory.metadata.strength + 0.1)
            # Reduce decay rate
            memory.metadata.decay_rate *= 0.8

        return memories

    async def _integrate(self, memories: List[MemoryItem]) -> List[MemoryItem]:
        """Integrate with existing knowledge."""
        for memory in memories:
            # Find related memories in long-term storage
            related = await self.long_term.search(
                {"tags": memory.metadata.tags},
                limit=5
            )

            # Create associations
            for related_memory in related:
                if related_memory.id not in memory.associations:
                    memory.associations.append(related_memory.id)
                if memory.id not in related_memory.associations:
                    related_memory.associations.append(memory.id)

        return memories

    async def _compress(self, memories: List[MemoryItem]) -> List[MemoryItem]:
        """Compress similar memories."""
        if len(memories) <= 1:
            return memories

        # Simple compression: merge very similar memories
        compressed = []
        used = set()

        for i, memory in enumerate(memories):
            if memory.id in used:
                continue

            # Find similar memories
            similar = []
            for j, other in enumerate(memories[i+1:], i+1):
                if other.id in used:
                    continue

                similarity = self._calculate_similarity(memory, other)
                if similarity > 0.8:  # High similarity threshold
                    similar.append(other)
                    used.add(other.id)

            if similar:
                # Merge similar memories
                merged = self._merge_memories(memory, similar)
                compressed.append(merged)
            else:
                compressed.append(memory)

            used.add(memory.id)

        return compressed

    async def _store(self, memories: List[MemoryItem]) -> None:
        """Store consolidated memories."""
        for memory in memories:
            memory.state = MemoryState.CONSOLIDATED
            await self.long_term.store(memory)

    def _generate_summary(self, content: Dict[str, Any]) -> str:
        """Generate a summary of memory content."""
        # Simple summary generation
        parts = []
        for key, value in list(content.items())[:3]:
            if isinstance(value, str):
                parts.append(f"{key}: {value[:50]}")
            else:
                parts.append(f"{key}: {type(value).__name__}")
        return "; ".join(parts)

    def _generate_embedding(self, content: Dict[str, Any]) -> List[float]:
        """Generate embedding vector for content."""
        # Placeholder embedding (would use actual embedding model)
        text = json.dumps(content)
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)

        # Generate pseudo-random but deterministic embedding
        random.seed(hash_val)
        return [random.random() for _ in range(64)]

    def _calculate_similarity(
        self,
        memory1: MemoryItem,
        memory2: MemoryItem
    ) -> float:
        """Calculate similarity between memories."""
        if not memory1.embedding or not memory2.embedding:
            return 0.0

        # Cosine similarity
        dot_product = sum(
            a * b for a, b in zip(memory1.embedding, memory2.embedding)
        )
        norm1 = math.sqrt(sum(a ** 2 for a in memory1.embedding))
        norm2 = math.sqrt(sum(b ** 2 for b in memory2.embedding))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def _merge_memories(
        self,
        primary: MemoryItem,
        similar: List[MemoryItem]
    ) -> MemoryItem:
        """Merge similar memories into one."""
        # Combine content
        merged_content = dict(primary.content)
        for mem in similar:
            for key, value in mem.content.items():
                if key not in merged_content:
                    merged_content[key] = value

        # Combine tags
        all_tags = set(primary.metadata.tags)
        for mem in similar:
            all_tags.update(mem.metadata.tags)

        # Calculate combined importance
        importance_values = [primary.metadata.importance.value]
        importance_values.extend(m.metadata.importance.value for m in similar)
        best_importance = min(importance_values)

        merged = MemoryItem(
            type=primary.type,
            content=merged_content,
            summary=primary.summary + f" (merged from {len(similar) + 1} memories)",
            embedding=primary.embedding,
            associations=list(set(primary.associations)),
            metadata=MemoryMetadata(
                importance=ImportanceLevel(best_importance),
                strength=primary.metadata.strength,
                tags=list(all_tags)
            )
        )

        return merged


# =============================================================================
# RETRIEVAL ENGINE
# =============================================================================

class RetrievalEngine:
    """
    Handles memory retrieval with multiple modes.

    Supports exact, semantic, associative, and temporal retrieval.
    """

    def __init__(self, long_term_memory: LongTermMemoryStore):
        self.long_term = long_term_memory

    async def retrieve(
        self,
        query: Union[str, Dict[str, Any]],
        mode: RetrievalMode = RetrievalMode.SEMANTIC,
        limit: int = 10,
        min_strength: float = 0.1
    ) -> RetrievalResult:
        """Retrieve memories based on query and mode."""
        start_time = time.time()

        if mode == RetrievalMode.EXACT:
            memories = await self._exact_retrieval(query, limit)
        elif mode == RetrievalMode.SEMANTIC:
            memories = await self._semantic_retrieval(query, limit)
        elif mode == RetrievalMode.ASSOCIATIVE:
            memories = await self._associative_retrieval(query, limit)
        elif mode == RetrievalMode.TEMPORAL:
            memories = await self._temporal_retrieval(query, limit)
        elif mode == RetrievalMode.CONTEXTUAL:
            memories = await self._contextual_retrieval(query, limit)
        else:
            memories = []

        # Filter by strength
        memories = [m for m in memories if m.metadata.strength >= min_strength]

        # Calculate relevance scores
        scores = self._calculate_scores(query, memories, mode)

        retrieval_time = (time.time() - start_time) * 1000

        return RetrievalResult(
            memories=memories,
            scores=scores,
            total_found=len(memories),
            retrieval_time_ms=retrieval_time,
            mode=mode
        )

    async def _exact_retrieval(
        self,
        query: Union[str, Dict[str, Any]],
        limit: int
    ) -> List[MemoryItem]:
        """Exact match retrieval."""
        if isinstance(query, str):
            query = {"id": query}

        return await self.long_term.search(query, limit)

    async def _semantic_retrieval(
        self,
        query: Union[str, Dict[str, Any]],
        limit: int
    ) -> List[MemoryItem]:
        """Semantic similarity retrieval."""
        # Generate query embedding
        if isinstance(query, str):
            query_content = {"text": query}
        else:
            query_content = query

        query_embedding = self._generate_query_embedding(query_content)

        # Search all memories and rank by similarity
        all_memories = await self.long_term.search({}, limit=1000)

        scored = []
        for memory in all_memories:
            if memory.embedding:
                similarity = self._cosine_similarity(query_embedding, memory.embedding)
                scored.append((memory, similarity))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [m for m, _ in scored[:limit]]

    async def _associative_retrieval(
        self,
        query: Union[str, Dict[str, Any]],
        limit: int
    ) -> List[MemoryItem]:
        """Association-based retrieval."""
        if isinstance(query, str):
            # Assume query is a memory ID
            start_memory = await self.long_term.retrieve(query)
            if not start_memory:
                return []

            # Follow associations
            visited = set()
            to_visit = [start_memory.id]
            results = []

            while to_visit and len(results) < limit:
                current_id = to_visit.pop(0)
                if current_id in visited:
                    continue

                visited.add(current_id)
                memory = await self.long_term.retrieve(current_id)

                if memory:
                    results.append(memory)
                    to_visit.extend(memory.associations)

            return results

        return []

    async def _temporal_retrieval(
        self,
        query: Union[str, Dict[str, Any]],
        limit: int
    ) -> List[MemoryItem]:
        """Time-based retrieval."""
        if isinstance(query, dict):
            start_time = query.get("start_time")
            end_time = query.get("end_time")
        else:
            return []

        all_memories = await self.long_term.search({}, limit=1000)

        filtered = []
        for memory in all_memories:
            created = memory.metadata.created_at
            if start_time and created < start_time:
                continue
            if end_time and created > end_time:
                continue
            filtered.append(memory)

        # Sort by time
        filtered.sort(key=lambda m: m.metadata.created_at, reverse=True)
        return filtered[:limit]

    async def _contextual_retrieval(
        self,
        query: Union[str, Dict[str, Any]],
        limit: int
    ) -> List[MemoryItem]:
        """Context-aware retrieval."""
        if isinstance(query, dict) and "context" in query:
            context = query["context"]
            all_memories = await self.long_term.search({}, limit=1000)

            scored = []
            for memory in all_memories:
                # Score based on context overlap
                mem_context = memory.metadata.context
                overlap = sum(
                    1 for k, v in context.items()
                    if k in mem_context and mem_context[k] == v
                )
                if overlap > 0:
                    scored.append((memory, overlap))

            scored.sort(key=lambda x: x[1], reverse=True)
            return [m for m, _ in scored[:limit]]

        return []

    def _generate_query_embedding(self, content: Dict[str, Any]) -> List[float]:
        """Generate embedding for query."""
        text = json.dumps(content)
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        random.seed(hash_val)
        return [random.random() for _ in range(64)]

    def _cosine_similarity(
        self,
        vec1: List[float],
        vec2: List[float]
    ) -> float:
        """Calculate cosine similarity."""
        if len(vec1) != len(vec2):
            return 0.0

        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a ** 2 for a in vec1))
        norm2 = math.sqrt(sum(b ** 2 for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot / (norm1 * norm2)

    def _calculate_scores(
        self,
        query: Union[str, Dict[str, Any]],
        memories: List[MemoryItem],
        mode: RetrievalMode
    ) -> List[float]:
        """Calculate relevance scores for retrieved memories."""
        scores = []

        for memory in memories:
            # Base score from strength
            score = memory.metadata.strength

            # Boost for high importance
            importance_boost = 1.0 + (0.2 * (5 - memory.metadata.importance.value))

            # Recency boost
            hours_ago = (datetime.now() - memory.metadata.last_accessed).total_seconds() / 3600
            recency_boost = 1.0 / (1.0 + hours_ago / 24)

            final_score = score * importance_boost * recency_boost
            scores.append(min(1.0, final_score))

        return scores


# =============================================================================
# MEMORY CONSOLIDATION SYSTEM
# =============================================================================

class MemoryConsolidation:
    """
    The master memory consolidation system for BAEL.

    Provides unified memory management with working memory,
    long-term storage, consolidation, and retrieval.
    """

    def __init__(self, working_capacity: int = 7):
        self.working = WorkingMemoryStore(capacity=working_capacity)
        self.long_term = LongTermMemoryStore()
        self.consolidation = ConsolidationEngine(self.working, self.long_term)
        self.retrieval = RetrievalEngine(self.long_term)
        self.auto_consolidation = True
        self.consolidation_threshold = 5  # Consolidate when working memory is 5+ items

    async def remember(
        self,
        content: Dict[str, Any],
        memory_type: MemoryType = MemoryType.EPISODIC,
        importance: ImportanceLevel = ImportanceLevel.NORMAL,
        tags: List[str] = None,
        context: Dict[str, Any] = None
    ) -> MemoryItem:
        """Store a new memory."""
        memory = MemoryItem(
            type=memory_type,
            content=content,
            metadata=MemoryMetadata(
                importance=importance,
                tags=tags or [],
                context=context or {}
            )
        )

        await self.working.store(memory)

        # Auto-consolidate if threshold reached
        if self.auto_consolidation:
            working_memories = self.working.get_all()
            if len(working_memories) >= self.consolidation_threshold:
                await self.consolidate()

        return memory

    async def recall(
        self,
        query: Union[str, Dict[str, Any]],
        mode: RetrievalMode = RetrievalMode.SEMANTIC,
        limit: int = 10,
        include_working: bool = True
    ) -> RetrievalResult:
        """Recall memories matching query."""
        # Search long-term memory
        result = await self.retrieval.retrieve(query, mode, limit)

        # Include working memory if requested
        if include_working:
            if isinstance(query, dict):
                working_results = await self.working.search(query, limit)
            else:
                working_results = self.working.get_all()

            # Merge results, prioritizing working memory
            for mem in working_results:
                if mem not in result.memories:
                    result.memories.insert(0, mem)
                    result.scores.insert(0, 1.0)

            result.total_found = len(result.memories)

        return result

    async def consolidate(self) -> ConsolidationJob:
        """Consolidate working memory to long-term storage."""
        working_memories = self.working.get_all()

        if not working_memories:
            return ConsolidationJob(result={"memories_processed": 0})

        job = await self.consolidation.consolidate(working_memories)

        # Clear consolidated memories from working memory
        for memory_id in job.memory_ids:
            await self.working.delete(memory_id)

        return job

    async def forget(
        self,
        memory_id: str,
        from_long_term: bool = True
    ) -> bool:
        """Forget a specific memory."""
        if from_long_term:
            return await self.long_term.delete(memory_id)
        else:
            return await self.working.delete(memory_id)

    async def decay_memories(self, hours: float = 1.0) -> int:
        """Apply decay to all memories."""
        decayed_count = 0

        for memory in self.long_term.memories.values():
            old_strength = memory.metadata.strength
            memory.decay(hours)
            if memory.metadata.strength < old_strength:
                decayed_count += 1

        return decayed_count

    async def reinforce(
        self,
        memory_id: str,
        amount: float = 0.2
    ) -> bool:
        """Reinforce a memory."""
        memory = await self.long_term.retrieve(memory_id)
        if memory:
            memory.reinforce(amount)
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get memory system statistics."""
        lt_stats = self.long_term.get_stats()

        return {
            "working_memory": {
                "count": len(self.working.memories),
                "capacity": self.working.capacity,
                "usage_percent": len(self.working.memories) / self.working.capacity * 100
            },
            "long_term_memory": lt_stats,
            "consolidation_jobs": len(self.consolidation.jobs),
            "auto_consolidation": self.auto_consolidation
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Memory Consolidation System."""
    print("=" * 70)
    print("BAEL - MEMORY CONSOLIDATION DEMO")
    print("Long-term Memory Management")
    print("=" * 70)
    print()

    # Create memory system
    memory = MemoryConsolidation(working_capacity=5)

    # 1. Store Memories
    print("1. STORING MEMORIES:")
    print("-" * 40)

    # Store various memories
    await memory.remember(
        {"event": "System startup", "time": "now"},
        memory_type=MemoryType.EPISODIC,
        importance=ImportanceLevel.HIGH,
        tags=["system", "startup"]
    )

    await memory.remember(
        {"fact": "BAEL uses councils for decision making"},
        memory_type=MemoryType.SEMANTIC,
        importance=ImportanceLevel.NORMAL,
        tags=["architecture", "councils"]
    )

    await memory.remember(
        {"procedure": "Initialize engines before starting agents"},
        memory_type=MemoryType.PROCEDURAL,
        importance=ImportanceLevel.HIGH,
        tags=["procedure", "startup"]
    )

    await memory.remember(
        {"task": "Completed optimization task", "result": "success"},
        memory_type=MemoryType.EPISODIC,
        importance=ImportanceLevel.NORMAL,
        tags=["task", "optimization"]
    )

    stats = memory.get_stats()
    print(f"   Working Memory: {stats['working_memory']['count']}/{stats['working_memory']['capacity']}")
    print()

    # 2. Recall Memories
    print("2. RECALLING MEMORIES:")
    print("-" * 40)

    result = await memory.recall(
        {"tags": ["startup"]},
        mode=RetrievalMode.EXACT,
        limit=5
    )

    print(f"   Found: {result.total_found} memories")
    for mem, score in zip(result.memories[:3], result.scores[:3]):
        print(f"   - {mem.summary or str(mem.content)[:40]}... (score: {score:.2f})")
    print()

    # 3. Consolidation
    print("3. MEMORY CONSOLIDATION:")
    print("-" * 40)

    # Add more memories to trigger consolidation
    for i in range(3):
        await memory.remember(
            {"data": f"Test memory {i}", "index": i},
            memory_type=MemoryType.EPISODIC,
            importance=ImportanceLevel.LOW,
            tags=["test"]
        )

    job = await memory.consolidate()
    print(f"   Memories processed: {job.result.get('memories_processed', 0)}")
    print(f"   Compression achieved: {job.result.get('compression_achieved', 0):.1%}")

    stats = memory.get_stats()
    print(f"   Working Memory after: {stats['working_memory']['count']}")
    print(f"   Long-term Memory: {stats['long_term_memory']['total_memories']}")
    print()

    # 4. Semantic Retrieval
    print("4. SEMANTIC RETRIEVAL:")
    print("-" * 40)

    result = await memory.recall(
        {"text": "system architecture councils"},
        mode=RetrievalMode.SEMANTIC,
        limit=5
    )

    print(f"   Mode: {result.mode.value}")
    print(f"   Retrieval time: {result.retrieval_time_ms:.2f}ms")
    print(f"   Results: {result.total_found}")
    print()

    # 5. Memory Decay
    print("5. MEMORY DECAY:")
    print("-" * 40)

    # Get a memory before decay
    all_memories = await memory.long_term.search({}, limit=1)
    if all_memories:
        before_strength = all_memories[0].metadata.strength

        # Apply decay
        decayed = await memory.decay_memories(hours=24)
        print(f"   Decayed memories: {decayed}")

        after_strength = all_memories[0].metadata.strength
        print(f"   Strength before: {before_strength:.3f}")
        print(f"   Strength after: {after_strength:.3f}")
    print()

    # 6. Reinforcement
    print("6. MEMORY REINFORCEMENT:")
    print("-" * 40)

    if all_memories:
        memory_id = all_memories[0].id
        before = all_memories[0].metadata.strength

        await memory.reinforce(memory_id, amount=0.3)

        mem = await memory.long_term.retrieve(memory_id)
        after = mem.metadata.strength

        print(f"   Before reinforcement: {before:.3f}")
        print(f"   After reinforcement: {after:.3f}")
    print()

    # 7. Final Stats
    print("7. FINAL STATISTICS:")
    print("-" * 40)

    final_stats = memory.get_stats()
    print(f"   Working Memory: {final_stats['working_memory']['count']}")
    print(f"   Long-term Memories: {final_stats['long_term_memory']['total_memories']}")
    print(f"   Active: {final_stats['long_term_memory']['active']}")
    print(f"   Consolidated: {final_stats['long_term_memory']['consolidated']}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Memory Consolidation Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
