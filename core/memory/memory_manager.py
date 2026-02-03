#!/usr/bin/env python3
"""
BAEL - Memory Manager
Advanced memory management and context for AI agents.

Features:
- Short-term memory (working memory)
- Long-term memory (persistent storage)
- Episodic memory (event sequences)
- Semantic memory (knowledge base)
- Memory consolidation
- Context window management
- Memory retrieval (similarity search)
- Memory compression
- Forgetting curves
- Memory indexing
"""

import asyncio
import hashlib
import json
import logging
import math
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Deque, Dict, Generic, Iterator, List,
                    Optional, Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)


T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class MemoryType(Enum):
    """Memory types."""
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


class MemoryPriority(Enum):
    """Memory priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class RetrievalStrategy(Enum):
    """Memory retrieval strategies."""
    RECENCY = "recency"
    RELEVANCE = "relevance"
    IMPORTANCE = "importance"
    HYBRID = "hybrid"


class ConsolidationStrategy(Enum):
    """Memory consolidation strategies."""
    NONE = "none"
    SUMMARIZE = "summarize"
    COMPRESS = "compress"
    HIERARCHICAL = "hierarchical"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class MemoryEntry:
    """A single memory entry."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    memory_type: MemoryType = MemoryType.SHORT_TERM
    priority: MemoryPriority = MemoryPriority.NORMAL
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    accessed_at: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    decay_rate: float = 0.1
    associations: List[str] = field(default_factory=list)
    source: Optional[str] = None

    @property
    def strength(self) -> float:
        """Calculate memory strength based on decay."""
        age = (datetime.utcnow() - self.accessed_at).total_seconds() / 3600  # hours
        base_strength = 1.0 + math.log(1 + self.access_count)
        decay = math.exp(-self.decay_rate * age)
        return base_strength * decay * self.priority.value


@dataclass
class Episode:
    """An episodic memory sequence."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    events: List[MemoryEntry] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    summary: Optional[str] = None


@dataclass
class MemoryQuery:
    """Query for memory retrieval."""
    text: Optional[str] = None
    embedding: Optional[List[float]] = None
    memory_types: List[MemoryType] = field(default_factory=list)
    min_priority: MemoryPriority = MemoryPriority.LOW
    time_range: Optional[Tuple[datetime, datetime]] = None
    limit: int = 10
    strategy: RetrievalStrategy = RetrievalStrategy.HYBRID


@dataclass
class MemoryStats:
    """Memory statistics."""
    total_entries: int = 0
    by_type: Dict[str, int] = field(default_factory=dict)
    avg_strength: float = 0.0
    oldest_entry: Optional[datetime] = None
    newest_entry: Optional[datetime] = None
    total_access_count: int = 0


@dataclass
class ConsolidationResult:
    """Result of memory consolidation."""
    original_count: int = 0
    final_count: int = 0
    removed: int = 0
    merged: int = 0
    summaries_created: int = 0


@dataclass
class ContextWindow:
    """Context window for LLM interactions."""
    max_tokens: int = 4000
    entries: List[MemoryEntry] = field(default_factory=list)
    current_tokens: int = 0

    def has_space(self, tokens: int) -> bool:
        return self.current_tokens + tokens <= self.max_tokens


# =============================================================================
# EMBEDDING GENERATOR
# =============================================================================

class SimpleEmbedding:
    """Simple embedding generator (for demo - use real embeddings in production)."""

    def __init__(self, dim: int = 128):
        self.dim = dim

    def embed(self, text: str) -> List[float]:
        """Generate simple embedding from text."""
        # Create deterministic embedding based on text hash
        text_hash = hashlib.sha256(text.encode()).digest()

        embedding = []
        for i in range(self.dim):
            # Use hash bytes to generate values
            idx = i % len(text_hash)
            value = (text_hash[idx] - 128) / 128.0
            embedding.append(value)

        # Normalize
        norm = math.sqrt(sum(x * x for x in embedding))
        if norm > 0:
            embedding = [x / norm for x in embedding]

        return embedding

    def similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity."""
        if not a or not b or len(a) != len(b):
            return 0.0

        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot / (norm_a * norm_b)


# =============================================================================
# MEMORY STORES
# =============================================================================

class MemoryStore(ABC):
    """Base memory store."""

    @abstractmethod
    def add(self, entry: MemoryEntry) -> str:
        pass

    @abstractmethod
    def get(self, entry_id: str) -> Optional[MemoryEntry]:
        pass

    @abstractmethod
    def delete(self, entry_id: str) -> bool:
        pass

    @abstractmethod
    def search(self, query: MemoryQuery) -> List[MemoryEntry]:
        pass

    @abstractmethod
    def clear(self) -> int:
        pass


class InMemoryStore(MemoryStore):
    """In-memory storage."""

    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self._entries: Dict[str, MemoryEntry] = {}
        self._embedder = SimpleEmbedding()

    def add(self, entry: MemoryEntry) -> str:
        # Generate embedding if not present
        if entry.embedding is None:
            entry.embedding = self._embedder.embed(entry.content)

        # Evict if at capacity
        if len(self._entries) >= self.max_size:
            self._evict_weakest()

        self._entries[entry.id] = entry
        return entry.id

    def get(self, entry_id: str) -> Optional[MemoryEntry]:
        entry = self._entries.get(entry_id)
        if entry:
            entry.accessed_at = datetime.utcnow()
            entry.access_count += 1
        return entry

    def delete(self, entry_id: str) -> bool:
        if entry_id in self._entries:
            del self._entries[entry_id]
            return True
        return False

    def search(self, query: MemoryQuery) -> List[MemoryEntry]:
        candidates = list(self._entries.values())

        # Filter by type
        if query.memory_types:
            candidates = [e for e in candidates if e.memory_type in query.memory_types]

        # Filter by priority
        candidates = [e for e in candidates if e.priority.value >= query.min_priority.value]

        # Filter by time range
        if query.time_range:
            start, end = query.time_range
            candidates = [e for e in candidates if start <= e.created_at <= end]

        # Score and rank
        if query.text or query.embedding:
            query_embedding = query.embedding or self._embedder.embed(query.text or "")

            scored = []
            for entry in candidates:
                if entry.embedding:
                    relevance = self._embedder.similarity(query_embedding, entry.embedding)
                else:
                    relevance = 0.0

                # Calculate score based on strategy
                if query.strategy == RetrievalStrategy.RECENCY:
                    score = -((datetime.utcnow() - entry.accessed_at).total_seconds())
                elif query.strategy == RetrievalStrategy.RELEVANCE:
                    score = relevance
                elif query.strategy == RetrievalStrategy.IMPORTANCE:
                    score = entry.strength
                else:  # HYBRID
                    recency = 1.0 / (1.0 + (datetime.utcnow() - entry.accessed_at).total_seconds() / 3600)
                    score = 0.4 * relevance + 0.3 * entry.strength + 0.3 * recency

                scored.append((entry, score))

            scored.sort(key=lambda x: x[1], reverse=True)
            candidates = [e for e, _ in scored]
        else:
            # Sort by strength
            candidates.sort(key=lambda e: e.strength, reverse=True)

        return candidates[:query.limit]

    def clear(self) -> int:
        count = len(self._entries)
        self._entries.clear()
        return count

    def _evict_weakest(self) -> None:
        """Evict weakest memory."""
        if not self._entries:
            return

        weakest = min(self._entries.values(), key=lambda e: e.strength)
        del self._entries[weakest.id]

    def get_all(self) -> List[MemoryEntry]:
        """Get all entries."""
        return list(self._entries.values())


# =============================================================================
# SHORT-TERM MEMORY
# =============================================================================

class ShortTermMemory:
    """Short-term / working memory with limited capacity."""

    def __init__(self, capacity: int = 7):
        self.capacity = capacity
        self._buffer: Deque[MemoryEntry] = deque(maxlen=capacity)

    def add(self, content: str, **metadata) -> MemoryEntry:
        """Add to short-term memory."""
        entry = MemoryEntry(
            content=content,
            memory_type=MemoryType.SHORT_TERM,
            metadata=metadata
        )
        self._buffer.append(entry)
        return entry

    def get_recent(self, count: int = None) -> List[MemoryEntry]:
        """Get recent entries."""
        entries = list(self._buffer)
        if count:
            entries = entries[-count:]
        return entries

    def clear(self) -> int:
        """Clear short-term memory."""
        count = len(self._buffer)
        self._buffer.clear()
        return count

    def is_full(self) -> bool:
        return len(self._buffer) >= self.capacity

    def __len__(self) -> int:
        return len(self._buffer)


# =============================================================================
# LONG-TERM MEMORY
# =============================================================================

class LongTermMemory:
    """Long-term persistent memory."""

    def __init__(self, store: Optional[MemoryStore] = None):
        self._store = store or InMemoryStore()

    def store(self, entry: MemoryEntry) -> str:
        """Store in long-term memory."""
        entry.memory_type = MemoryType.LONG_TERM
        return self._store.add(entry)

    def recall(self, query: MemoryQuery) -> List[MemoryEntry]:
        """Recall from long-term memory."""
        query.memory_types = [MemoryType.LONG_TERM]
        return self._store.search(query)

    def forget(self, entry_id: str) -> bool:
        """Forget a memory."""
        return self._store.delete(entry_id)

    def get(self, entry_id: str) -> Optional[MemoryEntry]:
        """Get specific memory."""
        return self._store.get(entry_id)


# =============================================================================
# EPISODIC MEMORY
# =============================================================================

class EpisodicMemory:
    """Episodic memory for event sequences."""

    def __init__(self):
        self._episodes: Dict[str, Episode] = {}
        self._current_episode: Optional[Episode] = None

    def start_episode(self, context: Optional[Dict[str, Any]] = None) -> Episode:
        """Start a new episode."""
        if self._current_episode:
            self.end_episode()

        self._current_episode = Episode(context=context or {})
        self._episodes[self._current_episode.id] = self._current_episode
        return self._current_episode

    def add_event(self, content: str, **metadata) -> Optional[MemoryEntry]:
        """Add event to current episode."""
        if not self._current_episode:
            return None

        entry = MemoryEntry(
            content=content,
            memory_type=MemoryType.EPISODIC,
            metadata=metadata
        )
        self._current_episode.events.append(entry)
        return entry

    def end_episode(self, summary: Optional[str] = None) -> Optional[Episode]:
        """End current episode."""
        if not self._current_episode:
            return None

        episode = self._current_episode
        episode.ended_at = datetime.utcnow()
        episode.summary = summary
        self._current_episode = None
        return episode

    def get_episode(self, episode_id: str) -> Optional[Episode]:
        """Get episode by ID."""
        return self._episodes.get(episode_id)

    def get_recent_episodes(self, count: int = 10) -> List[Episode]:
        """Get recent episodes."""
        episodes = sorted(
            self._episodes.values(),
            key=lambda e: e.started_at,
            reverse=True
        )
        return episodes[:count]

    def search_episodes(self, query: str) -> List[Episode]:
        """Search episodes by content."""
        results = []
        query_lower = query.lower()

        for episode in self._episodes.values():
            for event in episode.events:
                if query_lower in event.content.lower():
                    results.append(episode)
                    break

        return results


# =============================================================================
# SEMANTIC MEMORY
# =============================================================================

class SemanticMemory:
    """Semantic memory for knowledge and facts."""

    def __init__(self):
        self._facts: Dict[str, MemoryEntry] = {}
        self._relations: Dict[str, List[Tuple[str, str, str]]] = defaultdict(list)
        self._embedder = SimpleEmbedding()

    def add_fact(self, content: str, category: Optional[str] = None, **metadata) -> MemoryEntry:
        """Add a fact to semantic memory."""
        entry = MemoryEntry(
            content=content,
            memory_type=MemoryType.SEMANTIC,
            priority=MemoryPriority.HIGH,
            metadata={"category": category, **metadata}
        )
        entry.embedding = self._embedder.embed(content)
        self._facts[entry.id] = entry
        return entry

    def add_relation(self, subject: str, predicate: str, obj: str) -> None:
        """Add a relation (triple) to semantic memory."""
        self._relations[subject].append((subject, predicate, obj))
        self._relations[obj].append((subject, predicate, obj))

    def get_fact(self, fact_id: str) -> Optional[MemoryEntry]:
        """Get a fact by ID."""
        return self._facts.get(fact_id)

    def search_facts(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """Search facts by similarity."""
        query_embedding = self._embedder.embed(query)

        scored = []
        for fact in self._facts.values():
            if fact.embedding:
                score = self._embedder.similarity(query_embedding, fact.embedding)
                scored.append((fact, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [f for f, _ in scored[:limit]]

    def get_relations(self, entity: str) -> List[Tuple[str, str, str]]:
        """Get all relations for an entity."""
        return self._relations.get(entity, [])

    def query_relations(self, subject: Optional[str] = None, predicate: Optional[str] = None, obj: Optional[str] = None) -> List[Tuple[str, str, str]]:
        """Query relations by components."""
        results = []

        all_relations = set()
        for rels in self._relations.values():
            all_relations.update(rels)

        for s, p, o in all_relations:
            if subject and s != subject:
                continue
            if predicate and p != predicate:
                continue
            if obj and o != obj:
                continue
            results.append((s, p, o))

        return results


# =============================================================================
# MEMORY CONSOLIDATOR
# =============================================================================

class MemoryConsolidator:
    """Consolidate and compress memories."""

    def __init__(self, strategy: ConsolidationStrategy = ConsolidationStrategy.SUMMARIZE):
        self.strategy = strategy
        self._embedder = SimpleEmbedding()

    def consolidate(
        self,
        memories: List[MemoryEntry],
        threshold: float = 0.8
    ) -> ConsolidationResult:
        """Consolidate similar memories."""
        result = ConsolidationResult(original_count=len(memories))

        if self.strategy == ConsolidationStrategy.NONE:
            result.final_count = len(memories)
            return result

        # Group similar memories
        groups = self._cluster_memories(memories, threshold)

        consolidated = []
        for group in groups:
            if len(group) == 1:
                consolidated.append(group[0])
            else:
                # Merge group
                merged = self._merge_group(group)
                consolidated.append(merged)
                result.merged += len(group) - 1

        result.final_count = len(consolidated)
        result.removed = result.original_count - result.final_count

        return result

    def _cluster_memories(
        self,
        memories: List[MemoryEntry],
        threshold: float
    ) -> List[List[MemoryEntry]]:
        """Cluster similar memories."""
        if not memories:
            return []

        groups = []
        used = set()

        for i, mem in enumerate(memories):
            if i in used:
                continue

            group = [mem]
            used.add(i)

            for j, other in enumerate(memories[i + 1:], i + 1):
                if j in used:
                    continue

                if mem.embedding and other.embedding:
                    sim = self._embedder.similarity(mem.embedding, other.embedding)
                    if sim >= threshold:
                        group.append(other)
                        used.add(j)

            groups.append(group)

        return groups

    def _merge_group(self, group: List[MemoryEntry]) -> MemoryEntry:
        """Merge a group of similar memories."""
        # Take the most recent/strongest as base
        base = max(group, key=lambda m: m.strength)

        # Combine content
        contents = [m.content for m in group]
        combined = " | ".join(set(contents))

        # Combine access counts
        total_access = sum(m.access_count for m in group)

        merged = MemoryEntry(
            content=combined,
            memory_type=base.memory_type,
            priority=max(m.priority for m in group),
            embedding=base.embedding,
            metadata={"merged_count": len(group), **base.metadata},
            access_count=total_access
        )

        return merged


# =============================================================================
# CONTEXT MANAGER
# =============================================================================

class ContextManager:
    """Manage context window for LLM interactions."""

    def __init__(self, max_tokens: int = 4000):
        self.max_tokens = max_tokens
        self._context: List[MemoryEntry] = []
        self._token_count = 0

    def add(self, entry: MemoryEntry, token_estimate: Optional[int] = None) -> bool:
        """Add entry to context if space available."""
        tokens = token_estimate or self._estimate_tokens(entry.content)

        if self._token_count + tokens > self.max_tokens:
            return False

        self._context.append(entry)
        self._token_count += tokens
        return True

    def remove(self, entry_id: str) -> bool:
        """Remove entry from context."""
        for i, entry in enumerate(self._context):
            if entry.id == entry_id:
                tokens = self._estimate_tokens(entry.content)
                self._context.pop(i)
                self._token_count -= tokens
                return True
        return False

    def get_context(self) -> List[MemoryEntry]:
        """Get current context."""
        return self._context.copy()

    def clear(self) -> None:
        """Clear context."""
        self._context.clear()
        self._token_count = 0

    def available_tokens(self) -> int:
        """Get available token space."""
        return self.max_tokens - self._token_count

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count."""
        return int(len(text.split()) * 1.3)


# =============================================================================
# MEMORY MANAGER
# =============================================================================

class MemoryManager:
    """
    Memory Manager for BAEL.

    Advanced memory management for AI agents.
    """

    def __init__(
        self,
        short_term_capacity: int = 7,
        long_term_capacity: int = 10000,
        context_max_tokens: int = 4000
    ):
        self.short_term = ShortTermMemory(capacity=short_term_capacity)
        self.long_term = LongTermMemory(InMemoryStore(max_size=long_term_capacity))
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory()
        self.context = ContextManager(max_tokens=context_max_tokens)
        self._consolidator = MemoryConsolidator()
        self._embedder = SimpleEmbedding()

    # -------------------------------------------------------------------------
    # SHORT-TERM MEMORY
    # -------------------------------------------------------------------------

    def remember(self, content: str, **metadata) -> MemoryEntry:
        """Add to short-term memory."""
        entry = self.short_term.add(content, **metadata)

        # Add to context if space
        self.context.add(entry)

        return entry

    def get_recent(self, count: int = 5) -> List[MemoryEntry]:
        """Get recent memories."""
        return self.short_term.get_recent(count)

    # -------------------------------------------------------------------------
    # LONG-TERM MEMORY
    # -------------------------------------------------------------------------

    def memorize(self, content: str, priority: MemoryPriority = MemoryPriority.NORMAL, **metadata) -> str:
        """Store in long-term memory."""
        entry = MemoryEntry(
            content=content,
            priority=priority,
            metadata=metadata,
            embedding=self._embedder.embed(content)
        )
        return self.long_term.store(entry)

    def recall(
        self,
        query: str,
        limit: int = 10,
        strategy: RetrievalStrategy = RetrievalStrategy.HYBRID
    ) -> List[MemoryEntry]:
        """Recall from long-term memory."""
        mq = MemoryQuery(
            text=query,
            limit=limit,
            strategy=strategy
        )
        return self.long_term.recall(mq)

    def forget(self, memory_id: str) -> bool:
        """Forget a memory."""
        return self.long_term.forget(memory_id)

    # -------------------------------------------------------------------------
    # EPISODIC MEMORY
    # -------------------------------------------------------------------------

    def start_episode(self, context: Optional[Dict[str, Any]] = None) -> Episode:
        """Start a new episode."""
        return self.episodic.start_episode(context)

    def log_event(self, content: str, **metadata) -> Optional[MemoryEntry]:
        """Log event in current episode."""
        return self.episodic.add_event(content, **metadata)

    def end_episode(self, summary: Optional[str] = None) -> Optional[Episode]:
        """End current episode."""
        return self.episodic.end_episode(summary)

    def get_episodes(self, count: int = 10) -> List[Episode]:
        """Get recent episodes."""
        return self.episodic.get_recent_episodes(count)

    # -------------------------------------------------------------------------
    # SEMANTIC MEMORY
    # -------------------------------------------------------------------------

    def learn_fact(self, content: str, category: Optional[str] = None, **metadata) -> MemoryEntry:
        """Learn a new fact."""
        return self.semantic.add_fact(content, category, **metadata)

    def learn_relation(self, subject: str, predicate: str, obj: str) -> None:
        """Learn a relation."""
        self.semantic.add_relation(subject, predicate, obj)

    def query_knowledge(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """Query semantic knowledge."""
        return self.semantic.search_facts(query, limit)

    def get_relations(self, entity: str) -> List[Tuple[str, str, str]]:
        """Get relations for an entity."""
        return self.semantic.get_relations(entity)

    # -------------------------------------------------------------------------
    # CONTEXT MANAGEMENT
    # -------------------------------------------------------------------------

    def add_to_context(self, content: str) -> bool:
        """Add content to context window."""
        entry = MemoryEntry(content=content)
        return self.context.add(entry)

    def get_context(self) -> List[MemoryEntry]:
        """Get current context."""
        return self.context.get_context()

    def clear_context(self) -> None:
        """Clear context window."""
        self.context.clear()

    def available_context_tokens(self) -> int:
        """Get available context tokens."""
        return self.context.available_tokens()

    # -------------------------------------------------------------------------
    # CONSOLIDATION
    # -------------------------------------------------------------------------

    def consolidate(self) -> ConsolidationResult:
        """Consolidate memories to reduce redundancy."""
        store = self.long_term._store
        if isinstance(store, InMemoryStore):
            all_memories = store.get_all()
            result = self._consolidator.consolidate(all_memories)
            return result
        return ConsolidationResult()

    def transfer_to_long_term(self, threshold: float = 0.5) -> int:
        """Transfer strong short-term memories to long-term."""
        transferred = 0

        for entry in self.short_term.get_recent():
            if entry.strength >= threshold:
                self.long_term.store(entry)
                transferred += 1

        return transferred

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> MemoryStats:
        """Get memory statistics."""
        stats = MemoryStats()

        # Short-term
        stats.by_type["short_term"] = len(self.short_term)

        # Long-term
        store = self.long_term._store
        if isinstance(store, InMemoryStore):
            all_memories = store.get_all()
            stats.total_entries = len(all_memories)
            stats.by_type["long_term"] = len(all_memories)

            if all_memories:
                stats.avg_strength = sum(m.strength for m in all_memories) / len(all_memories)
                stats.oldest_entry = min(m.created_at for m in all_memories)
                stats.newest_entry = max(m.created_at for m in all_memories)
                stats.total_access_count = sum(m.access_count for m in all_memories)

        # Episodic
        stats.by_type["episodic"] = len(self.episodic._episodes)

        # Semantic
        stats.by_type["semantic"] = len(self.semantic._facts)

        return stats

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def search(
        self,
        query: str,
        memory_types: Optional[List[MemoryType]] = None,
        limit: int = 10
    ) -> List[MemoryEntry]:
        """Search across all memory types."""
        results = []

        types = memory_types or [MemoryType.SHORT_TERM, MemoryType.LONG_TERM, MemoryType.SEMANTIC]

        if MemoryType.LONG_TERM in types:
            results.extend(self.recall(query, limit))

        if MemoryType.SEMANTIC in types:
            results.extend(self.query_knowledge(query, limit))

        if MemoryType.SHORT_TERM in types:
            query_lower = query.lower()
            for entry in self.short_term.get_recent():
                if query_lower in entry.content.lower():
                    results.append(entry)

        # Deduplicate and sort by strength
        seen = set()
        unique = []
        for entry in results:
            if entry.id not in seen:
                seen.add(entry.id)
                unique.append(entry)

        unique.sort(key=lambda e: e.strength, reverse=True)
        return unique[:limit]

    def clear_all(self) -> Dict[str, int]:
        """Clear all memories."""
        cleared = {
            "short_term": self.short_term.clear(),
            "long_term": self.long_term._store.clear(),
            "episodic": len(self.episodic._episodes),
            "semantic": len(self.semantic._facts)
        }

        self.episodic._episodes.clear()
        self.semantic._facts.clear()
        self.semantic._relations.clear()
        self.context.clear()

        return cleared


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Memory Manager."""
    print("=" * 70)
    print("BAEL - MEMORY MANAGER DEMO")
    print("Advanced Memory Management for AI Agents")
    print("=" * 70)
    print()

    memory = MemoryManager(
        short_term_capacity=5,
        long_term_capacity=1000,
        context_max_tokens=2000
    )

    # 1. Short-Term Memory
    print("1. SHORT-TERM MEMORY:")
    print("-" * 40)

    memory.remember("User asked about weather")
    memory.remember("System responded with forecast")
    memory.remember("User asked about temperature")

    recent = memory.get_recent(3)
    for entry in recent:
        print(f"   - {entry.content}")
    print()

    # 2. Long-Term Memory
    print("2. LONG-TERM MEMORY:")
    print("-" * 40)

    memory.memorize("Python is a programming language", priority=MemoryPriority.HIGH)
    memory.memorize("Machine learning uses data to learn patterns")
    memory.memorize("Neural networks are inspired by brain structure")
    memory.memorize("BAEL is the lord of all AI agents")

    recalled = memory.recall("programming", limit=3)
    print(f"   Query: 'programming'")
    for entry in recalled:
        print(f"   - {entry.content[:50]}...")
    print()

    # 3. Episodic Memory
    print("3. EPISODIC MEMORY:")
    print("-" * 40)

    episode = memory.start_episode({"task": "coding session"})
    memory.log_event("Started coding session")
    memory.log_event("Created new file")
    memory.log_event("Wrote initial code")
    memory.log_event("Fixed bug")
    memory.end_episode(summary="Completed coding task")

    episodes = memory.get_episodes()
    for ep in episodes:
        print(f"   Episode: {ep.id[:8]}...")
        print(f"   Events: {len(ep.events)}")
        print(f"   Summary: {ep.summary}")
    print()

    # 4. Semantic Memory
    print("4. SEMANTIC MEMORY:")
    print("-" * 40)

    memory.learn_fact("Paris is the capital of France", category="geography")
    memory.learn_fact("Einstein developed theory of relativity", category="science")
    memory.learn_fact("Python was created by Guido van Rossum", category="technology")

    memory.learn_relation("Paris", "capital_of", "France")
    memory.learn_relation("Einstein", "created", "Theory of Relativity")

    facts = memory.query_knowledge("France")
    print(f"   Query: 'France'")
    for fact in facts:
        print(f"   - {fact.content}")

    relations = memory.get_relations("Paris")
    print(f"   Relations for 'Paris': {relations}")
    print()

    # 5. Context Management
    print("5. CONTEXT MANAGEMENT:")
    print("-" * 40)

    memory.add_to_context("Previous conversation context")
    memory.add_to_context("User preferences loaded")

    context = memory.get_context()
    print(f"   Context entries: {len(context)}")
    print(f"   Available tokens: {memory.available_context_tokens()}")
    print()

    # 6. Memory Search
    print("6. UNIFIED SEARCH:")
    print("-" * 40)

    results = memory.search("Python programming", limit=5)
    print(f"   Query: 'Python programming'")
    for entry in results:
        print(f"   - [{entry.memory_type.value}] {entry.content[:40]}...")
    print()

    # 7. Memory Strength
    print("7. MEMORY STRENGTH:")
    print("-" * 40)

    # Access a memory multiple times
    memories = memory.recall("BAEL", limit=1)
    if memories:
        mem = memories[0]
        print(f"   Memory: {mem.content[:30]}...")
        print(f"   Initial strength: {mem.strength:.3f}")

        # Simulate multiple accesses
        for _ in range(5):
            memory.long_term.get(mem.id)

        updated = memory.long_term.get(mem.id)
        print(f"   After 5 accesses: {updated.strength:.3f}")
    print()

    # 8. Memory Transfer
    print("8. SHORT TO LONG TERM TRANSFER:")
    print("-" * 40)

    memory.remember("Important information")
    memory.remember("Another important fact")

    transferred = memory.transfer_to_long_term(threshold=0.3)
    print(f"   Transferred: {transferred} memories")
    print()

    # 9. Memory Consolidation
    print("9. MEMORY CONSOLIDATION:")
    print("-" * 40)

    # Add similar memories
    memory.memorize("Machine learning is AI")
    memory.memorize("Machine learning uses algorithms")
    memory.memorize("ML is part of artificial intelligence")

    result = memory.consolidate()
    print(f"   Original: {result.original_count}")
    print(f"   After consolidation: {result.final_count}")
    print(f"   Merged: {result.merged}")
    print()

    # 10. Statistics
    print("10. MEMORY STATISTICS:")
    print("-" * 40)

    stats = memory.get_stats()
    print(f"   Total entries: {stats.total_entries}")
    print(f"   By type: {stats.by_type}")
    print(f"   Average strength: {stats.avg_strength:.3f}")
    print(f"   Total accesses: {stats.total_access_count}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Memory Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
