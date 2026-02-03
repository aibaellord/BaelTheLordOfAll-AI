#!/usr/bin/env python3
"""
BAEL - Memory Engine
Conversation and context memory.

Features:
- Short-term memory
- Long-term memory
- Semantic memory
- Episodic memory
- Memory consolidation
"""

import asyncio
import hashlib
import json
import math
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class MemoryType(Enum):
    """Types of memory."""
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


class MemoryStatus(Enum):
    """Memory entry status."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    EXPIRED = "expired"
    CONSOLIDATED = "consolidated"


class RetrievalStrategy(Enum):
    """Memory retrieval strategies."""
    RECENCY = "recency"
    RELEVANCE = "relevance"
    IMPORTANCE = "importance"
    HYBRID = "hybrid"


class ConsolidationStrategy(Enum):
    """Memory consolidation strategies."""
    SUMMARIZE = "summarize"
    COMPRESS = "compress"
    PRUNE = "prune"
    MERGE = "merge"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class MemoryEntry:
    """Single memory entry."""
    entry_id: str = ""
    content: str = ""
    memory_type: MemoryType = MemoryType.SHORT_TERM
    status: MemoryStatus = MemoryStatus.ACTIVE
    importance: float = 0.5
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    ttl_seconds: Optional[int] = None

    def __post_init__(self):
        if not self.entry_id:
            self.entry_id = str(uuid.uuid4())[:8]

    def is_expired(self) -> bool:
        """Check if memory has expired."""
        if self.ttl_seconds is None:
            return False

        elapsed = (datetime.now() - self.created_at).total_seconds()
        return elapsed > self.ttl_seconds


@dataclass
class ConversationTurn:
    """Single conversation turn."""
    turn_id: str = ""
    role: str = "user"
    content: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.turn_id:
            self.turn_id = str(uuid.uuid4())[:8]


@dataclass
class Conversation:
    """Conversation with turns."""
    conversation_id: str = ""
    turns: List[ConversationTurn] = field(default_factory=list)
    summary: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.conversation_id:
            self.conversation_id = str(uuid.uuid4())[:8]

    def add_turn(self, role: str, content: str) -> ConversationTurn:
        """Add a turn to the conversation."""
        turn = ConversationTurn(role=role, content=content)
        self.turns.append(turn)
        self.updated_at = datetime.now()
        return turn


@dataclass
class Episode:
    """Episodic memory episode."""
    episode_id: str = ""
    title: str = ""
    events: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    outcome: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    importance: float = 0.5

    def __post_init__(self):
        if not self.episode_id:
            self.episode_id = str(uuid.uuid4())[:8]


@dataclass
class Concept:
    """Semantic memory concept."""
    concept_id: str = ""
    name: str = ""
    description: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    relations: List[Tuple[str, str]] = field(default_factory=list)
    embedding: Optional[List[float]] = None

    def __post_init__(self):
        if not self.concept_id:
            self.concept_id = str(uuid.uuid4())[:8]


@dataclass
class MemoryConfig:
    """Memory configuration."""
    max_short_term: int = 100
    max_long_term: int = 10000
    max_working: int = 10
    short_term_ttl: int = 3600
    consolidation_threshold: int = 50
    importance_threshold: float = 0.3


@dataclass
class MemoryStats:
    """Memory statistics."""
    short_term_count: int = 0
    long_term_count: int = 0
    working_count: int = 0
    episodic_count: int = 0
    semantic_count: int = 0
    total_accesses: int = 0
    consolidations: int = 0


# =============================================================================
# VECTOR OPERATIONS
# =============================================================================

class VectorOps:
    """Vector operations."""

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """Compute cosine similarity."""
        dot = sum(a * b for a, b in zip(v1, v2))
        mag1 = math.sqrt(sum(x ** 2 for x in v1))
        mag2 = math.sqrt(sum(x ** 2 for x in v2))

        if mag1 == 0 or mag2 == 0:
            return 0.0

        return dot / (mag1 * mag2)

    @staticmethod
    def normalize(v: List[float]) -> List[float]:
        """Normalize vector."""
        mag = math.sqrt(sum(x ** 2 for x in v))
        if mag == 0:
            return v
        return [x / mag for x in v]


# =============================================================================
# MEMORY STORES
# =============================================================================

class BaseMemoryStore(ABC):
    """Abstract base memory store."""

    @property
    @abstractmethod
    def memory_type(self) -> MemoryType:
        """Get memory type."""
        pass

    @abstractmethod
    async def store(self, entry: MemoryEntry) -> str:
        """Store a memory entry."""
        pass

    @abstractmethod
    async def retrieve(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory entry."""
        pass

    @abstractmethod
    async def search(self, query: str, top_k: int = 5) -> List[MemoryEntry]:
        """Search memory entries."""
        pass


class ShortTermStore(BaseMemoryStore):
    """Short-term memory store."""

    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._entries: Dict[str, MemoryEntry] = {}
        self._access_order: deque = deque()

    @property
    def memory_type(self) -> MemoryType:
        return MemoryType.SHORT_TERM

    async def store(self, entry: MemoryEntry) -> str:
        """Store with LRU eviction."""
        entry.memory_type = MemoryType.SHORT_TERM
        entry.ttl_seconds = self._ttl_seconds

        if len(self._entries) >= self._max_size:
            while self._access_order and len(self._entries) >= self._max_size:
                oldest_id = self._access_order.popleft()
                if oldest_id in self._entries:
                    del self._entries[oldest_id]

        self._entries[entry.entry_id] = entry
        self._access_order.append(entry.entry_id)

        return entry.entry_id

    async def retrieve(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve and update access."""
        entry = self._entries.get(entry_id)

        if entry:
            if entry.is_expired():
                del self._entries[entry_id]
                return None

            entry.accessed_at = datetime.now()
            entry.access_count += 1

        return entry

    async def search(self, query: str, top_k: int = 5) -> List[MemoryEntry]:
        """Search by content match."""
        query_lower = query.lower()
        matches = []

        for entry in self._entries.values():
            if entry.is_expired():
                continue

            if query_lower in entry.content.lower():
                matches.append(entry)

        matches.sort(key=lambda x: x.accessed_at, reverse=True)
        return matches[:top_k]

    def cleanup_expired(self) -> int:
        """Remove expired entries."""
        expired = [eid for eid, e in self._entries.items() if e.is_expired()]

        for eid in expired:
            del self._entries[eid]

        return len(expired)

    @property
    def count(self) -> int:
        return len(self._entries)


class LongTermStore(BaseMemoryStore):
    """Long-term memory store."""

    def __init__(self, max_size: int = 10000, embedding_dim: int = 128):
        self._max_size = max_size
        self._embedding_dim = embedding_dim
        self._entries: Dict[str, MemoryEntry] = {}

    @property
    def memory_type(self) -> MemoryType:
        return MemoryType.LONG_TERM

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        random.seed(hash(text) % (2**32))
        vec = [random.gauss(0, 1) for _ in range(self._embedding_dim)]
        return VectorOps.normalize(vec)

    async def store(self, entry: MemoryEntry) -> str:
        """Store with embedding."""
        entry.memory_type = MemoryType.LONG_TERM

        if entry.embedding is None:
            entry.embedding = self._generate_embedding(entry.content)

        if len(self._entries) >= self._max_size:
            min_importance = min(self._entries.values(), key=lambda x: x.importance)
            del self._entries[min_importance.entry_id]

        self._entries[entry.entry_id] = entry

        return entry.entry_id

    async def retrieve(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve by ID."""
        entry = self._entries.get(entry_id)

        if entry:
            entry.accessed_at = datetime.now()
            entry.access_count += 1

        return entry

    async def search(self, query: str, top_k: int = 5) -> List[MemoryEntry]:
        """Search by semantic similarity."""
        query_embedding = self._generate_embedding(query)

        scored = []

        for entry in self._entries.values():
            if entry.embedding:
                score = VectorOps.cosine_similarity(query_embedding, entry.embedding)
                scored.append((entry, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        return [entry for entry, _ in scored[:top_k]]

    @property
    def count(self) -> int:
        return len(self._entries)


class WorkingMemoryStore(BaseMemoryStore):
    """Working memory store (limited capacity)."""

    def __init__(self, max_size: int = 10):
        self._max_size = max_size
        self._entries: List[MemoryEntry] = []

    @property
    def memory_type(self) -> MemoryType:
        return MemoryType.WORKING

    async def store(self, entry: MemoryEntry) -> str:
        """Store with capacity limit."""
        entry.memory_type = MemoryType.WORKING

        if len(self._entries) >= self._max_size:
            self._entries.pop(0)

        self._entries.append(entry)

        return entry.entry_id

    async def retrieve(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve by ID."""
        for entry in self._entries:
            if entry.entry_id == entry_id:
                entry.accessed_at = datetime.now()
                return entry

        return None

    async def search(self, query: str, top_k: int = 5) -> List[MemoryEntry]:
        """Search working memory."""
        return list(reversed(self._entries))[:top_k]

    def clear(self) -> None:
        """Clear working memory."""
        self._entries.clear()

    @property
    def count(self) -> int:
        return len(self._entries)

    def get_all(self) -> List[MemoryEntry]:
        """Get all entries."""
        return list(self._entries)


class EpisodicStore:
    """Episodic memory store."""

    def __init__(self):
        self._episodes: Dict[str, Episode] = {}

    async def store(self, episode: Episode) -> str:
        """Store an episode."""
        self._episodes[episode.episode_id] = episode
        return episode.episode_id

    async def retrieve(self, episode_id: str) -> Optional[Episode]:
        """Retrieve an episode."""
        return self._episodes.get(episode_id)

    async def search(self, query: str, top_k: int = 5) -> List[Episode]:
        """Search episodes."""
        query_lower = query.lower()
        matches = []

        for episode in self._episodes.values():
            if query_lower in episode.title.lower() or \
               any(query_lower in e.lower() for e in episode.events):
                matches.append(episode)

        matches.sort(key=lambda x: x.importance, reverse=True)
        return matches[:top_k]

    @property
    def count(self) -> int:
        return len(self._episodes)


class SemanticStore:
    """Semantic memory store (concepts)."""

    def __init__(self, embedding_dim: int = 128):
        self._embedding_dim = embedding_dim
        self._concepts: Dict[str, Concept] = {}
        self._relations: Dict[str, Set[Tuple[str, str]]] = defaultdict(set)

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding."""
        random.seed(hash(text) % (2**32))
        vec = [random.gauss(0, 1) for _ in range(self._embedding_dim)]
        return VectorOps.normalize(vec)

    async def store(self, concept: Concept) -> str:
        """Store a concept."""
        if concept.embedding is None:
            concept.embedding = self._generate_embedding(concept.name + " " + concept.description)

        self._concepts[concept.concept_id] = concept

        for relation_type, target_id in concept.relations:
            self._relations[concept.concept_id].add((relation_type, target_id))

        return concept.concept_id

    async def retrieve(self, concept_id: str) -> Optional[Concept]:
        """Retrieve a concept."""
        return self._concepts.get(concept_id)

    async def search(self, query: str, top_k: int = 5) -> List[Concept]:
        """Search concepts semantically."""
        query_embedding = self._generate_embedding(query)

        scored = []

        for concept in self._concepts.values():
            if concept.embedding:
                score = VectorOps.cosine_similarity(query_embedding, concept.embedding)
                scored.append((concept, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        return [concept for concept, _ in scored[:top_k]]

    def get_related(self, concept_id: str, relation_type: Optional[str] = None) -> List[Concept]:
        """Get related concepts."""
        related = []

        for rel_type, target_id in self._relations.get(concept_id, []):
            if relation_type is None or rel_type == relation_type:
                concept = self._concepts.get(target_id)
                if concept:
                    related.append(concept)

        return related

    @property
    def count(self) -> int:
        return len(self._concepts)


# =============================================================================
# MEMORY ENGINE
# =============================================================================

class MemoryEngine:
    """
    Memory Engine for BAEL.

    Conversation and context memory.
    """

    def __init__(self, config: Optional[MemoryConfig] = None):
        self.config = config or MemoryConfig()

        self._short_term = ShortTermStore(
            max_size=self.config.max_short_term,
            ttl_seconds=self.config.short_term_ttl
        )
        self._long_term = LongTermStore(max_size=self.config.max_long_term)
        self._working = WorkingMemoryStore(max_size=self.config.max_working)
        self._episodic = EpisodicStore()
        self._semantic = SemanticStore()

        self._conversations: Dict[str, Conversation] = {}
        self._active_conversation: Optional[str] = None

        self._stats = MemoryStats()

    async def store(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.SHORT_TERM,
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store a memory entry."""
        entry = MemoryEntry(
            content=content,
            memory_type=memory_type,
            importance=importance,
            metadata=metadata or {}
        )

        if memory_type == MemoryType.SHORT_TERM:
            entry_id = await self._short_term.store(entry)
            self._stats.short_term_count = self._short_term.count

        elif memory_type == MemoryType.LONG_TERM:
            entry_id = await self._long_term.store(entry)
            self._stats.long_term_count = self._long_term.count

        elif memory_type == MemoryType.WORKING:
            entry_id = await self._working.store(entry)
            self._stats.working_count = self._working.count

        else:
            entry_id = await self._short_term.store(entry)

        return entry_id

    async def retrieve(
        self,
        entry_id: str,
        memory_type: Optional[MemoryType] = None
    ) -> Optional[MemoryEntry]:
        """Retrieve a memory entry."""
        self._stats.total_accesses += 1

        if memory_type == MemoryType.SHORT_TERM or memory_type is None:
            entry = await self._short_term.retrieve(entry_id)
            if entry:
                return entry

        if memory_type == MemoryType.LONG_TERM or memory_type is None:
            entry = await self._long_term.retrieve(entry_id)
            if entry:
                return entry

        if memory_type == MemoryType.WORKING or memory_type is None:
            entry = await self._working.retrieve(entry_id)
            if entry:
                return entry

        return None

    async def search(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        top_k: int = 5,
        strategy: RetrievalStrategy = RetrievalStrategy.RELEVANCE
    ) -> List[MemoryEntry]:
        """Search memory."""
        results = []

        if memory_type is None or memory_type == MemoryType.SHORT_TERM:
            results.extend(await self._short_term.search(query, top_k))

        if memory_type is None or memory_type == MemoryType.LONG_TERM:
            results.extend(await self._long_term.search(query, top_k))

        if memory_type is None or memory_type == MemoryType.WORKING:
            results.extend(await self._working.search(query, top_k))

        if strategy == RetrievalStrategy.RECENCY:
            results.sort(key=lambda x: x.accessed_at, reverse=True)
        elif strategy == RetrievalStrategy.IMPORTANCE:
            results.sort(key=lambda x: x.importance, reverse=True)
        elif strategy == RetrievalStrategy.HYBRID:
            now = datetime.now()

            def hybrid_score(entry):
                recency = 1.0 / (1.0 + (now - entry.accessed_at).total_seconds() / 3600)
                return entry.importance * 0.5 + recency * 0.5

            results.sort(key=hybrid_score, reverse=True)

        return results[:top_k]

    async def consolidate(
        self,
        strategy: ConsolidationStrategy = ConsolidationStrategy.PRUNE
    ) -> int:
        """Consolidate short-term to long-term memory."""
        consolidated = 0

        if strategy == ConsolidationStrategy.PRUNE:
            expired = self._short_term.cleanup_expired()
            consolidated += expired

        elif strategy == ConsolidationStrategy.SUMMARIZE:
            entries = list(self._short_term._entries.values())

            if len(entries) > self.config.consolidation_threshold:
                important = [e for e in entries if e.importance >= self.config.importance_threshold]

                for entry in important:
                    entry.memory_type = MemoryType.LONG_TERM
                    await self._long_term.store(entry)
                    consolidated += 1

        self._stats.consolidations += 1

        return consolidated

    def start_conversation(self) -> str:
        """Start a new conversation."""
        conversation = Conversation()
        self._conversations[conversation.conversation_id] = conversation
        self._active_conversation = conversation.conversation_id

        return conversation.conversation_id

    def add_message(
        self,
        role: str,
        content: str,
        conversation_id: Optional[str] = None
    ) -> Optional[ConversationTurn]:
        """Add a message to conversation."""
        conv_id = conversation_id or self._active_conversation

        if conv_id not in self._conversations:
            return None

        conversation = self._conversations[conv_id]
        turn = conversation.add_turn(role, content)

        return turn

    def get_conversation(self, conversation_id: Optional[str] = None) -> Optional[Conversation]:
        """Get conversation."""
        conv_id = conversation_id or self._active_conversation
        return self._conversations.get(conv_id)

    def get_conversation_history(
        self,
        conversation_id: Optional[str] = None,
        last_n: Optional[int] = None
    ) -> List[ConversationTurn]:
        """Get conversation history."""
        conversation = self.get_conversation(conversation_id)

        if not conversation:
            return []

        turns = conversation.turns

        if last_n:
            turns = turns[-last_n:]

        return turns

    async def store_episode(
        self,
        title: str,
        events: List[str],
        context: Optional[Dict[str, Any]] = None,
        outcome: str = "",
        importance: float = 0.5
    ) -> str:
        """Store an episode."""
        episode = Episode(
            title=title,
            events=events,
            context=context or {},
            outcome=outcome,
            importance=importance
        )

        episode_id = await self._episodic.store(episode)
        self._stats.episodic_count = self._episodic.count

        return episode_id

    async def search_episodes(self, query: str, top_k: int = 5) -> List[Episode]:
        """Search episodes."""
        return await self._episodic.search(query, top_k)

    async def store_concept(
        self,
        name: str,
        description: str,
        properties: Optional[Dict[str, Any]] = None,
        relations: Optional[List[Tuple[str, str]]] = None
    ) -> str:
        """Store a concept."""
        concept = Concept(
            name=name,
            description=description,
            properties=properties or {},
            relations=relations or []
        )

        concept_id = await self._semantic.store(concept)
        self._stats.semantic_count = self._semantic.count

        return concept_id

    async def search_concepts(self, query: str, top_k: int = 5) -> List[Concept]:
        """Search concepts."""
        return await self._semantic.search(query, top_k)

    def get_working_memory(self) -> List[MemoryEntry]:
        """Get all working memory."""
        return self._working.get_all()

    def clear_working_memory(self) -> None:
        """Clear working memory."""
        self._working.clear()
        self._stats.working_count = 0

    @property
    def stats(self) -> MemoryStats:
        """Get memory statistics."""
        self._stats.short_term_count = self._short_term.count
        self._stats.long_term_count = self._long_term.count
        self._stats.working_count = self._working.count
        self._stats.episodic_count = self._episodic.count
        self._stats.semantic_count = self._semantic.count

        return self._stats

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        stats = self.stats

        return {
            "config": {
                "max_short_term": self.config.max_short_term,
                "max_long_term": self.config.max_long_term,
                "max_working": self.config.max_working
            },
            "counts": {
                "short_term": stats.short_term_count,
                "long_term": stats.long_term_count,
                "working": stats.working_count,
                "episodic": stats.episodic_count,
                "semantic": stats.semantic_count
            },
            "conversations": len(self._conversations),
            "active_conversation": self._active_conversation,
            "total_accesses": stats.total_accesses,
            "consolidations": stats.consolidations
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Memory Engine."""
    print("=" * 70)
    print("BAEL - MEMORY ENGINE DEMO")
    print("Conversation and Context Memory")
    print("=" * 70)
    print()

    engine = MemoryEngine()

    # 1. Store Short-Term Memories
    print("1. SHORT-TERM MEMORY:")
    print("-" * 40)

    m1 = await engine.store("The user's name is Alice", MemoryType.SHORT_TERM, importance=0.8)
    m2 = await engine.store("Alice prefers dark mode", MemoryType.SHORT_TERM, importance=0.6)
    m3 = await engine.store("Current topic is machine learning", MemoryType.SHORT_TERM)

    print(f"   Stored: {m1} - 'The user's name is Alice'")
    print(f"   Stored: {m2} - 'Alice prefers dark mode'")
    print(f"   Stored: {m3} - 'Current topic is machine learning'")
    print()

    # 2. Store Long-Term Memories
    print("2. LONG-TERM MEMORY:")
    print("-" * 40)

    l1 = await engine.store("Python is a programming language", MemoryType.LONG_TERM, importance=0.9)
    l2 = await engine.store("Machine learning uses data to learn patterns", MemoryType.LONG_TERM, importance=0.8)

    print(f"   Stored: {l1} - 'Python is a programming language'")
    print(f"   Stored: {l2} - 'Machine learning uses data...'")
    print()

    # 3. Working Memory
    print("3. WORKING MEMORY:")
    print("-" * 40)

    w1 = await engine.store("Current task: explain neural networks", MemoryType.WORKING)
    w2 = await engine.store("Step 1: Define neurons", MemoryType.WORKING)

    working = engine.get_working_memory()

    print(f"   Stored: {w1}")
    print(f"   Stored: {w2}")
    print(f"   Working Memory Size: {len(working)}")
    print()

    # 4. Memory Search
    print("4. MEMORY SEARCH:")
    print("-" * 40)

    results = await engine.search("Alice", top_k=3)

    print(f"   Query: 'Alice'")
    print(f"   Results: {len(results)}")

    for r in results:
        print(f"      - {r.content[:40]}... (importance: {r.importance})")
    print()

    # 5. Conversation Memory
    print("5. CONVERSATION MEMORY:")
    print("-" * 40)

    conv_id = engine.start_conversation()

    engine.add_message("user", "Hello! I want to learn about AI.")
    engine.add_message("assistant", "Hi! I'd be happy to help you learn about AI.")
    engine.add_message("user", "What is machine learning?")
    engine.add_message("assistant", "Machine learning is a subset of AI...")

    history = engine.get_conversation_history(last_n=2)

    print(f"   Conversation ID: {conv_id}")
    print(f"   Last 2 turns:")

    for turn in history:
        print(f"      {turn.role}: {turn.content[:40]}...")
    print()

    # 6. Episodic Memory
    print("6. EPISODIC MEMORY:")
    print("-" * 40)

    episode_id = await engine.store_episode(
        title="Debugging Session",
        events=[
            "User reported error",
            "Analyzed stack trace",
            "Identified null pointer",
            "Fixed the bug"
        ],
        outcome="Bug resolved",
        importance=0.7
    )

    episodes = await engine.search_episodes("debugging")

    print(f"   Stored Episode: {episode_id}")
    print(f"   Found: {len(episodes)} episodes")

    for ep in episodes:
        print(f"      - {ep.title}: {len(ep.events)} events")
    print()

    # 7. Semantic Memory
    print("7. SEMANTIC MEMORY:")
    print("-" * 40)

    c1 = await engine.store_concept(
        "Neural Network",
        "A computational model inspired by biological neurons",
        properties={"layers": "multiple", "activation": "relu"},
        relations=[("is_part_of", "deep_learning")]
    )

    c2 = await engine.store_concept(
        "Deep Learning",
        "Machine learning with deep neural networks"
    )

    concepts = await engine.search_concepts("neural")

    print(f"   Stored: {c1} - 'Neural Network'")
    print(f"   Stored: {c2} - 'Deep Learning'")
    print(f"   Search 'neural': {len(concepts)} concepts")
    print()

    # 8. Retrieval Strategies
    print("8. RETRIEVAL STRATEGIES:")
    print("-" * 40)

    by_recency = await engine.search("learning", strategy=RetrievalStrategy.RECENCY)
    by_importance = await engine.search("learning", strategy=RetrievalStrategy.IMPORTANCE)
    by_hybrid = await engine.search("learning", strategy=RetrievalStrategy.HYBRID)

    print(f"   Query: 'learning'")
    print(f"   By Recency: {len(by_recency)} results")
    print(f"   By Importance: {len(by_importance)} results")
    print(f"   By Hybrid: {len(by_hybrid)} results")
    print()

    # 9. Memory Consolidation
    print("9. MEMORY CONSOLIDATION:")
    print("-" * 40)

    consolidated = await engine.consolidate(ConsolidationStrategy.PRUNE)

    print(f"   Strategy: PRUNE")
    print(f"   Consolidated: {consolidated} entries")
    print()

    # 10. Engine Summary
    print("10. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    print(f"   Short-Term: {summary['counts']['short_term']}")
    print(f"   Long-Term: {summary['counts']['long_term']}")
    print(f"   Working: {summary['counts']['working']}")
    print(f"   Episodic: {summary['counts']['episodic']}")
    print(f"   Semantic: {summary['counts']['semantic']}")
    print(f"   Conversations: {summary['conversations']}")
    print(f"   Total Accesses: {summary['total_accesses']}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Memory Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
