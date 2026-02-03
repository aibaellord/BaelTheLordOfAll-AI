#!/usr/bin/env python3
"""
BAEL - Cognitive Memory Manager
Advanced cognitive memory management for AI agents.

Features:
- Working memory
- Long-term memory
- Episodic memory
- Semantic memory
- Memory consolidation
- Retrieval mechanisms
"""

import asyncio
import hashlib
import math
import random
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class CogMemoryType(Enum):
    """Types of memory."""
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


class CogMemoryStatus(Enum):
    """Memory status."""
    ACTIVE = "active"
    DORMANT = "dormant"
    CONSOLIDATED = "consolidated"
    FORGOTTEN = "forgotten"


class CogRetrievalMode(Enum):
    """Retrieval modes."""
    EXACT = "exact"
    SIMILARITY = "similarity"
    TEMPORAL = "temporal"
    ASSOCIATIVE = "associative"


class CogConsolidationPhase(Enum):
    """Consolidation phases."""
    ENCODING = "encoding"
    STORAGE = "storage"
    CONSOLIDATION = "consolidation"
    RETRIEVAL = "retrieval"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class CogMemoryItem:
    """A memory item."""
    item_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: Any = None
    memory_type: CogMemoryType = CogMemoryType.WORKING
    status: CogMemoryStatus = CogMemoryStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    importance: float = 0.5
    tags: Set[str] = field(default_factory=set)
    associations: List[str] = field(default_factory=list)
    embedding: List[float] = field(default_factory=list)


@dataclass
class CogEpisode:
    """An episodic memory."""
    episode_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    context: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    outcome: Optional[str] = None
    emotions: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class CogConcept:
    """A semantic concept."""
    concept_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    definition: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    relations: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class CogRetrievalResult:
    """Memory retrieval result."""
    items: List[CogMemoryItem] = field(default_factory=list)
    scores: Dict[str, float] = field(default_factory=dict)
    mode: CogRetrievalMode = CogRetrievalMode.EXACT


@dataclass
class CogMemoryStats:
    """Memory statistics."""
    working_count: int = 0
    episodic_count: int = 0
    semantic_count: int = 0
    total_access: int = 0
    avg_importance: float = 0.0


# =============================================================================
# WORKING MEMORY
# =============================================================================

class CogWorkingMemory:
    """Short-term working memory."""

    def __init__(self, capacity: int = 7):
        self._capacity = capacity
        self._items: deque = deque(maxlen=capacity)
        self._attention: Dict[str, float] = {}

    def add(self, item: CogMemoryItem) -> None:
        """Add item to working memory."""
        item.memory_type = CogMemoryType.WORKING
        self._items.append(item)
        self._attention[item.item_id] = 1.0

    def get(self, item_id: str) -> Optional[CogMemoryItem]:
        """Get item from working memory."""
        for item in self._items:
            if item.item_id == item_id:
                item.access_count += 1
                item.accessed_at = datetime.now()
                return item
        return None

    def all_items(self) -> List[CogMemoryItem]:
        """Get all items."""
        return list(self._items)

    def update_attention(self, item_id: str, attention: float) -> None:
        """Update attention on an item."""
        self._attention[item_id] = max(0.0, min(1.0, attention))

    def decay_attention(self, rate: float = 0.1) -> None:
        """Decay attention over time."""
        for item_id in list(self._attention.keys()):
            self._attention[item_id] *= (1 - rate)
            if self._attention[item_id] < 0.1:
                del self._attention[item_id]

    def most_attended(self, n: int = 3) -> List[CogMemoryItem]:
        """Get most attended items."""
        sorted_items = sorted(
            self._items,
            key=lambda x: self._attention.get(x.item_id, 0),
            reverse=True
        )
        return sorted_items[:n]

    def is_full(self) -> bool:
        """Check if memory is full."""
        return len(self._items) >= self._capacity

    def clear(self) -> None:
        """Clear working memory."""
        self._items.clear()
        self._attention.clear()


# =============================================================================
# EPISODIC MEMORY
# =============================================================================

class CogEpisodicMemory:
    """Memory for episodes and experiences."""

    def __init__(self):
        self._episodes: Dict[str, CogEpisode] = {}
        self._temporal_index: List[Tuple[datetime, str]] = []

    def store(self, episode: CogEpisode) -> None:
        """Store an episode."""
        self._episodes[episode.episode_id] = episode
        self._temporal_index.append((episode.timestamp, episode.episode_id))
        self._temporal_index.sort(key=lambda x: x[0])

    def retrieve(self, episode_id: str) -> Optional[CogEpisode]:
        """Retrieve an episode."""
        return self._episodes.get(episode_id)

    def retrieve_recent(self, n: int = 5) -> List[CogEpisode]:
        """Retrieve recent episodes."""
        recent_ids = [eid for _, eid in self._temporal_index[-n:]]
        return [self._episodes[eid] for eid in reversed(recent_ids)]

    def retrieve_by_context(
        self,
        context_key: str,
        context_value: Any
    ) -> List[CogEpisode]:
        """Retrieve episodes by context."""
        return [
            ep for ep in self._episodes.values()
            if ep.context.get(context_key) == context_value
        ]

    def retrieve_by_emotion(
        self,
        emotion: str,
        threshold: float = 0.5
    ) -> List[CogEpisode]:
        """Retrieve episodes by emotion."""
        return [
            ep for ep in self._episodes.values()
            if ep.emotions.get(emotion, 0) >= threshold
        ]

    def all_episodes(self) -> List[CogEpisode]:
        """Get all episodes."""
        return list(self._episodes.values())


# =============================================================================
# SEMANTIC MEMORY
# =============================================================================

class CogSemanticMemory:
    """Memory for concepts and facts."""

    def __init__(self):
        self._concepts: Dict[str, CogConcept] = {}
        self._name_index: Dict[str, str] = {}

    def store(self, concept: CogConcept) -> None:
        """Store a concept."""
        self._concepts[concept.concept_id] = concept
        self._name_index[concept.name.lower()] = concept.concept_id

    def retrieve(self, concept_id: str) -> Optional[CogConcept]:
        """Retrieve a concept by ID."""
        return self._concepts.get(concept_id)

    def retrieve_by_name(self, name: str) -> Optional[CogConcept]:
        """Retrieve a concept by name."""
        concept_id = self._name_index.get(name.lower())
        return self._concepts.get(concept_id) if concept_id else None

    def add_relation(
        self,
        source_name: str,
        relation: str,
        target_name: str
    ) -> None:
        """Add a relation between concepts."""
        source = self.retrieve_by_name(source_name)
        if source:
            if relation not in source.relations:
                source.relations[relation] = []
            source.relations[relation].append(target_name)

    def get_related(
        self,
        name: str,
        relation: str
    ) -> List[CogConcept]:
        """Get related concepts."""
        concept = self.retrieve_by_name(name)
        if not concept:
            return []

        related_names = concept.relations.get(relation, [])
        return [
            c for name in related_names
            if (c := self.retrieve_by_name(name))
        ]

    def all_concepts(self) -> List[CogConcept]:
        """Get all concepts."""
        return list(self._concepts.values())


# =============================================================================
# MEMORY CONSOLIDATOR
# =============================================================================

class CogMemoryConsolidator:
    """Consolidate memories from working to long-term."""

    def __init__(self):
        self._importance_threshold = 0.5
        self._rehearsal_boost = 0.1

    def should_consolidate(self, item: CogMemoryItem) -> bool:
        """Determine if item should be consolidated."""
        if item.importance >= self._importance_threshold:
            return True
        if item.access_count >= 3:
            return True
        if len(item.associations) >= 2:
            return True
        return False

    def consolidate(
        self,
        working: CogWorkingMemory,
        episodic: CogEpisodicMemory,
        semantic: CogSemanticMemory
    ) -> List[str]:
        """Consolidate working memory to long-term."""
        consolidated = []

        for item in working.all_items():
            if not self.should_consolidate(item):
                continue

            episode = CogEpisode(
                context={"source": "working_memory"},
                events=[{"content": item.content, "time": item.created_at.isoformat()}],
                timestamp=item.created_at
            )

            episodic.store(episode)
            item.status = CogMemoryStatus.CONSOLIDATED
            consolidated.append(item.item_id)

        return consolidated

    def rehearse(self, item: CogMemoryItem) -> None:
        """Rehearse a memory to strengthen it."""
        item.importance = min(1.0, item.importance + self._rehearsal_boost)
        item.access_count += 1
        item.accessed_at = datetime.now()


# =============================================================================
# RETRIEVAL ENGINE
# =============================================================================

class CogRetrievalEngine:
    """Engine for memory retrieval."""

    def _cosine_similarity(
        self,
        v1: List[float],
        v2: List[float]
    ) -> float:
        """Calculate cosine similarity."""
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0

        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a ** 2 for a in v1))
        norm2 = math.sqrt(sum(b ** 2 for b in v2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot / (norm1 * norm2)

    def retrieve_by_similarity(
        self,
        query_embedding: List[float],
        items: List[CogMemoryItem],
        top_k: int = 5
    ) -> CogRetrievalResult:
        """Retrieve by embedding similarity."""
        scores = {}

        for item in items:
            if item.embedding:
                score = self._cosine_similarity(query_embedding, item.embedding)
                scores[item.item_id] = score

        sorted_items = sorted(
            items,
            key=lambda x: scores.get(x.item_id, 0),
            reverse=True
        )

        return CogRetrievalResult(
            items=sorted_items[:top_k],
            scores=scores,
            mode=CogRetrievalMode.SIMILARITY
        )

    def retrieve_by_tags(
        self,
        tags: Set[str],
        items: List[CogMemoryItem]
    ) -> CogRetrievalResult:
        """Retrieve by tags."""
        scored_items = []
        scores = {}

        for item in items:
            overlap = len(tags & item.tags)
            if overlap > 0:
                score = overlap / len(tags)
                scores[item.item_id] = score
                scored_items.append((item, score))

        sorted_items = sorted(scored_items, key=lambda x: x[1], reverse=True)

        return CogRetrievalResult(
            items=[item for item, _ in sorted_items],
            scores=scores,
            mode=CogRetrievalMode.EXACT
        )

    def retrieve_by_recency(
        self,
        items: List[CogMemoryItem],
        hours: int = 24
    ) -> CogRetrievalResult:
        """Retrieve recent items."""
        cutoff = datetime.now() - timedelta(hours=hours)

        recent = [
            item for item in items
            if item.accessed_at >= cutoff
        ]

        sorted_items = sorted(recent, key=lambda x: x.accessed_at, reverse=True)

        scores = {
            item.item_id: 1.0 - (datetime.now() - item.accessed_at).seconds / (hours * 3600)
            for item in sorted_items
        }

        return CogRetrievalResult(
            items=sorted_items,
            scores=scores,
            mode=CogRetrievalMode.TEMPORAL
        )


# =============================================================================
# COGNITIVE MEMORY MANAGER
# =============================================================================

class CognitiveMemoryManager:
    """
    Cognitive Memory Manager for BAEL.

    Advanced cognitive memory management for AI agents.
    """

    def __init__(self, working_capacity: int = 7):
        self._working = CogWorkingMemory(capacity=working_capacity)
        self._episodic = CogEpisodicMemory()
        self._semantic = CogSemanticMemory()
        self._consolidator = CogMemoryConsolidator()
        self._retrieval = CogRetrievalEngine()

    # -------------------------------------------------------------------------
    # WORKING MEMORY
    # -------------------------------------------------------------------------

    def remember(
        self,
        content: Any,
        importance: float = 0.5,
        tags: Optional[Set[str]] = None
    ) -> CogMemoryItem:
        """Add to working memory."""
        item = CogMemoryItem(
            content=content,
            importance=importance,
            tags=tags or set()
        )
        self._working.add(item)
        return item

    def recall(self, item_id: str) -> Optional[CogMemoryItem]:
        """Recall from working memory."""
        return self._working.get(item_id)

    def focus(self, item_id: str) -> None:
        """Focus attention on an item."""
        self._working.update_attention(item_id, 1.0)

    def get_focused(self, n: int = 3) -> List[CogMemoryItem]:
        """Get most focused items."""
        return self._working.most_attended(n)

    # -------------------------------------------------------------------------
    # EPISODIC MEMORY
    # -------------------------------------------------------------------------

    def store_episode(
        self,
        context: Dict[str, Any],
        events: List[Dict[str, Any]],
        outcome: Optional[str] = None,
        emotions: Optional[Dict[str, float]] = None
    ) -> CogEpisode:
        """Store an episode."""
        episode = CogEpisode(
            context=context,
            events=events,
            outcome=outcome,
            emotions=emotions or {}
        )
        self._episodic.store(episode)
        return episode

    def recall_recent_episodes(self, n: int = 5) -> List[CogEpisode]:
        """Recall recent episodes."""
        return self._episodic.retrieve_recent(n)

    def recall_emotional_episodes(
        self,
        emotion: str,
        threshold: float = 0.5
    ) -> List[CogEpisode]:
        """Recall emotional episodes."""
        return self._episodic.retrieve_by_emotion(emotion, threshold)

    # -------------------------------------------------------------------------
    # SEMANTIC MEMORY
    # -------------------------------------------------------------------------

    def learn_concept(
        self,
        name: str,
        definition: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> CogConcept:
        """Learn a new concept."""
        concept = CogConcept(
            name=name,
            definition=definition,
            properties=properties or {}
        )
        self._semantic.store(concept)
        return concept

    def recall_concept(self, name: str) -> Optional[CogConcept]:
        """Recall a concept by name."""
        return self._semantic.retrieve_by_name(name)

    def relate_concepts(
        self,
        source: str,
        relation: str,
        target: str
    ) -> None:
        """Relate two concepts."""
        self._semantic.add_relation(source, relation, target)

    # -------------------------------------------------------------------------
    # CONSOLIDATION
    # -------------------------------------------------------------------------

    def consolidate(self) -> List[str]:
        """Consolidate working memory."""
        return self._consolidator.consolidate(
            self._working,
            self._episodic,
            self._semantic
        )

    def rehearse(self, item_id: str) -> None:
        """Rehearse a memory."""
        item = self._working.get(item_id)
        if item:
            self._consolidator.rehearse(item)

    # -------------------------------------------------------------------------
    # RETRIEVAL
    # -------------------------------------------------------------------------

    def search_by_tags(self, tags: Set[str]) -> CogRetrievalResult:
        """Search memories by tags."""
        all_items = self._working.all_items()
        return self._retrieval.retrieve_by_tags(tags, all_items)

    def search_recent(self, hours: int = 24) -> CogRetrievalResult:
        """Search recent memories."""
        all_items = self._working.all_items()
        return self._retrieval.retrieve_by_recency(all_items, hours)

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def statistics(self) -> CogMemoryStats:
        """Get memory statistics."""
        working = self._working.all_items()
        episodic = self._episodic.all_episodes()
        semantic = self._semantic.all_concepts()

        total_access = sum(item.access_count for item in working)
        avg_importance = (
            sum(item.importance for item in working) / len(working)
            if working else 0.0
        )

        return CogMemoryStats(
            working_count=len(working),
            episodic_count=len(episodic),
            semantic_count=len(semantic),
            total_access=total_access,
            avg_importance=avg_importance
        )


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Cognitive Memory Manager."""
    print("=" * 70)
    print("BAEL - COGNITIVE MEMORY MANAGER DEMO")
    print("Advanced Cognitive Memory Management for AI Agents")
    print("=" * 70)
    print()

    manager = CognitiveMemoryManager(working_capacity=7)

    # 1. Working Memory
    print("1. WORKING MEMORY:")
    print("-" * 40)

    items = []
    contents = [
        "User asked about weather",
        "Today is sunny",
        "Temperature is 72°F",
        "User location: New York",
        "Previous query: restaurants"
    ]

    for content in contents:
        item = manager.remember(
            content,
            importance=random.uniform(0.3, 0.9),
            tags={"context", "query"}
        )
        items.append(item)
        print(f"   Stored: {content[:30]}...")

    print(f"   Total in working memory: {len(manager._working.all_items())}")
    print()

    # 2. Focus and Attention
    print("2. FOCUS AND ATTENTION:")
    print("-" * 40)

    manager.focus(items[0].item_id)
    manager.focus(items[2].item_id)

    focused = manager.get_focused(3)
    print(f"   Most focused items:")
    for item in focused:
        print(f"      - {str(item.content)[:40]}...")
    print()

    # 3. Episodic Memory
    print("3. EPISODIC MEMORY:")
    print("-" * 40)

    episodes = [
        {
            "context": {"task": "weather_query"},
            "events": [
                {"action": "user_input", "data": "What's the weather?"},
                {"action": "api_call", "data": "weather_api"},
                {"action": "response", "data": "72°F, sunny"}
            ],
            "outcome": "success",
            "emotions": {"satisfaction": 0.8}
        },
        {
            "context": {"task": "restaurant_query"},
            "events": [
                {"action": "user_input", "data": "Find restaurants"},
                {"action": "search", "data": "restaurant_db"}
            ],
            "outcome": "success",
            "emotions": {"satisfaction": 0.7, "curiosity": 0.5}
        }
    ]

    for ep in episodes:
        manager.store_episode(**ep)
        print(f"   Stored episode: {ep['context']['task']}")

    recent = manager.recall_recent_episodes(2)
    print(f"   Recent episodes: {len(recent)}")
    print()

    # 4. Semantic Memory
    print("4. SEMANTIC MEMORY:")
    print("-" * 40)

    concepts = [
        ("weather", "Atmospheric conditions at a specific time and place"),
        ("temperature", "Measure of heat or coldness"),
        ("forecast", "Prediction of future weather conditions")
    ]

    for name, definition in concepts:
        manager.learn_concept(name, definition)
        print(f"   Learned: {name}")

    manager.relate_concepts("weather", "includes", "temperature")
    manager.relate_concepts("forecast", "predicts", "weather")

    concept = manager.recall_concept("weather")
    if concept:
        print(f"   Recalled: {concept.name} - {concept.definition[:40]}...")
    print()

    # 5. Rehearsal
    print("5. REHEARSAL:")
    print("-" * 40)

    item = items[0]
    print(f"   Before rehearsal - importance: {item.importance:.2f}, access: {item.access_count}")

    manager.rehearse(item.item_id)
    manager.rehearse(item.item_id)

    print(f"   After rehearsal - importance: {item.importance:.2f}, access: {item.access_count}")
    print()

    # 6. Consolidation
    print("6. CONSOLIDATION:")
    print("-" * 40)

    consolidated = manager.consolidate()
    print(f"   Consolidated {len(consolidated)} items to long-term memory")
    print()

    # 7. Statistics
    print("7. STATISTICS:")
    print("-" * 40)

    stats = manager.statistics()
    print(f"   Working memory: {stats.working_count} items")
    print(f"   Episodic memory: {stats.episodic_count} episodes")
    print(f"   Semantic memory: {stats.semantic_count} concepts")
    print(f"   Total access: {stats.total_access}")
    print(f"   Avg importance: {stats.avg_importance:.2f}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Cognitive Memory Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
