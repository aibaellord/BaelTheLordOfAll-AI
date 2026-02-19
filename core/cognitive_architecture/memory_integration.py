"""
🧬 MEMORY INTEGRATION 🧬
========================
Unified memory system.

Features:
- Working memory
- Long-term memory
- Episodic memory
- Semantic memory
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from datetime import datetime
import uuid
import math


class MemoryType(Enum):
    """Types of memory"""
    WORKING = auto()
    EPISODIC = auto()
    SEMANTIC = auto()
    PROCEDURAL = auto()
    SENSORY = auto()


@dataclass
class MemoryItem:
    """An item in memory"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Content
    content: Any = None

    # Memory type
    memory_type: MemoryType = MemoryType.WORKING

    # Activation
    activation: float = 1.0
    base_activation: float = 0.5

    # Access tracking
    access_count: int = 0
    last_access: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)

    # Associations
    associations: Dict[str, float] = field(default_factory=dict)  # item_id -> strength

    # Context
    context: Dict[str, Any] = field(default_factory=dict)

    def access(self):
        """Record access"""
        self.access_count += 1
        self.last_access = datetime.now()
        self._update_activation()

    def _update_activation(self):
        """Update activation based on access"""
        recency = (datetime.now() - self.last_access).total_seconds()
        decay = math.exp(-recency / 3600)  # 1-hour decay constant

        frequency_bonus = math.log(self.access_count + 1)

        self.activation = self.base_activation + decay * frequency_bonus
        self.activation = min(1.0, self.activation)

    def add_association(self, other_id: str, strength: float = 0.5):
        """Add association to another item"""
        self.associations[other_id] = min(1.0, strength)

    def get_association_strength(self, other_id: str) -> float:
        """Get association strength"""
        return self.associations.get(other_id, 0.0)


class WorkingMemory:
    """
    Working memory with limited capacity.
    """

    def __init__(self, capacity: int = 7):
        self.capacity = capacity

        self.items: Dict[str, MemoryItem] = {}

        # Focus of attention
        self.focus: Optional[str] = None

    def store(self, item: MemoryItem) -> bool:
        """Store item in working memory"""
        item.memory_type = MemoryType.WORKING

        # Check capacity
        if len(self.items) >= self.capacity:
            self._evict_least_active()

        self.items[item.id] = item
        return True

    def retrieve(self, item_id: str) -> Optional[MemoryItem]:
        """Retrieve item"""
        item = self.items.get(item_id)
        if item:
            item.access()
        return item

    def _evict_least_active(self):
        """Evict least active item"""
        if not self.items:
            return

        # Update activations
        for item in self.items.values():
            item._update_activation()

        # Find least active
        least_active = min(self.items.values(), key=lambda i: i.activation)
        del self.items[least_active.id]

    def get_contents(self) -> List[MemoryItem]:
        """Get all contents"""
        return list(self.items.values())

    def clear(self):
        """Clear working memory"""
        self.items.clear()
        self.focus = None


class LongTermMemory:
    """
    Long-term memory store.
    """

    def __init__(self):
        self.items: Dict[str, MemoryItem] = {}

        # Index by content type
        self.type_index: Dict[str, Set[str]] = {}

        # Forgetting threshold
        self.forgetting_threshold: float = 0.01

    def store(self, item: MemoryItem):
        """Store item in long-term memory"""
        self.items[item.id] = item

        # Index by content type
        content_type = type(item.content).__name__
        if content_type not in self.type_index:
            self.type_index[content_type] = set()
        self.type_index[content_type].add(item.id)

    def retrieve(self, item_id: str) -> Optional[MemoryItem]:
        """Retrieve item"""
        item = self.items.get(item_id)
        if item:
            item.access()
        return item

    def search(
        self,
        query: Dict[str, Any],
        max_results: int = 10
    ) -> List[MemoryItem]:
        """Search memory by query"""
        results = []

        for item in self.items.values():
            match_score = self._match_score(item, query)
            if match_score > 0:
                results.append((item, match_score))

        results.sort(key=lambda x: x[1], reverse=True)
        return [r[0] for r in results[:max_results]]

    def _match_score(self, item: MemoryItem, query: Dict[str, Any]) -> float:
        """Compute match score"""
        score = 0.0

        for key, value in query.items():
            if key in item.context and item.context[key] == value:
                score += 1.0

        return score * item.activation

    def forget(self):
        """Apply forgetting to low-activation items"""
        to_forget = [
            item_id for item_id, item in self.items.items()
            if item.activation < self.forgetting_threshold
        ]

        for item_id in to_forget:
            del self.items[item_id]

        return len(to_forget)


@dataclass
class Episode:
    """An episodic memory"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Episode content
    events: List[Any] = field(default_factory=list)

    # Temporal info
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

    # Context
    location: str = ""
    context: Dict[str, Any] = field(default_factory=dict)

    # Emotional valence
    valence: float = 0.0  # -1 to 1
    arousal: float = 0.5

    def add_event(self, event: Any):
        """Add event to episode"""
        self.events.append(event)

    def close(self):
        """Close episode"""
        self.end_time = datetime.now()


class EpisodicMemory:
    """
    Episodic memory for personal experiences.
    """

    def __init__(self):
        self.episodes: Dict[str, Episode] = {}

        # Current episode
        self.current_episode: Optional[Episode] = None

        # Timeline
        self.timeline: List[str] = []

    def start_episode(self, context: Dict[str, Any] = None) -> Episode:
        """Start new episode"""
        if self.current_episode:
            self.end_episode()

        self.current_episode = Episode(
            context=context or {}
        )
        return self.current_episode

    def end_episode(self):
        """End current episode"""
        if self.current_episode:
            self.current_episode.close()
            self.episodes[self.current_episode.id] = self.current_episode
            self.timeline.append(self.current_episode.id)
            self.current_episode = None

    def record_event(self, event: Any):
        """Record event to current episode"""
        if not self.current_episode:
            self.start_episode()

        self.current_episode.add_event(event)

    def recall(
        self,
        time_range: Tuple[datetime, datetime] = None,
        context: Dict[str, Any] = None,
        n: int = 10
    ) -> List[Episode]:
        """Recall episodes"""
        results = []

        for episode_id in self.timeline:
            episode = self.episodes.get(episode_id)
            if not episode:
                continue

            # Time filter
            if time_range:
                start, end = time_range
                if episode.start_time < start or episode.start_time > end:
                    continue

            # Context filter
            if context:
                match = all(
                    episode.context.get(k) == v
                    for k, v in context.items()
                )
                if not match:
                    continue

            results.append(episode)

        return results[-n:]

    def get_recent(self, n: int = 5) -> List[Episode]:
        """Get recent episodes"""
        return [
            self.episodes[eid]
            for eid in self.timeline[-n:]
            if eid in self.episodes
        ]


class SemanticMemory:
    """
    Semantic memory for facts and concepts.
    """

    def __init__(self):
        # Concept network
        self.concepts: Dict[str, Dict[str, Any]] = {}

        # Relations
        self.relations: List[Tuple[str, str, str]] = []  # (subject, relation, object)

        # Hierarchies
        self.is_a: Dict[str, Set[str]] = {}  # concept -> parent concepts
        self.has_a: Dict[str, Set[str]] = {}  # concept -> part concepts

    def add_concept(self, name: str, properties: Dict[str, Any] = None):
        """Add concept"""
        self.concepts[name] = properties or {}

    def add_relation(self, subject: str, relation: str, obj: str):
        """Add relation"""
        self.relations.append((subject, relation, obj))

        if relation == "is_a":
            if subject not in self.is_a:
                self.is_a[subject] = set()
            self.is_a[subject].add(obj)
        elif relation == "has_a":
            if subject not in self.has_a:
                self.has_a[subject] = set()
            self.has_a[subject].add(obj)

    def get_concept(self, name: str) -> Optional[Dict[str, Any]]:
        """Get concept properties"""
        return self.concepts.get(name)

    def query(
        self,
        subject: str = None,
        relation: str = None,
        obj: str = None
    ) -> List[Tuple[str, str, str]]:
        """Query relations"""
        results = []

        for s, r, o in self.relations:
            if subject and s != subject:
                continue
            if relation and r != relation:
                continue
            if obj and o != obj:
                continue
            results.append((s, r, o))

        return results

    def get_ancestors(self, concept: str) -> Set[str]:
        """Get all ancestor concepts"""
        ancestors = set()
        to_visit = [concept]

        while to_visit:
            current = to_visit.pop()
            parents = self.is_a.get(current, set())

            for parent in parents:
                if parent not in ancestors:
                    ancestors.add(parent)
                    to_visit.append(parent)

        return ancestors

    def inherits_property(self, concept: str, property_name: str) -> Optional[Any]:
        """Get inherited property"""
        # Check concept directly
        if concept in self.concepts and property_name in self.concepts[concept]:
            return self.concepts[concept][property_name]

        # Check ancestors
        for ancestor in self.get_ancestors(concept):
            if ancestor in self.concepts and property_name in self.concepts[ancestor]:
                return self.concepts[ancestor][property_name]

        return None


class UnifiedMemory:
    """
    Unified memory system integrating all memory types.
    """

    def __init__(self):
        self.working = WorkingMemory()
        self.long_term = LongTermMemory()
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory()

        # Consolidation queue
        self.consolidation_queue: List[MemoryItem] = []

    def encode(self, content: Any, memory_type: MemoryType = MemoryType.WORKING) -> MemoryItem:
        """Encode new memory"""
        item = MemoryItem(
            content=content,
            memory_type=memory_type
        )

        if memory_type == MemoryType.WORKING:
            self.working.store(item)
        elif memory_type in [MemoryType.EPISODIC, MemoryType.SEMANTIC, MemoryType.PROCEDURAL]:
            self.long_term.store(item)

        return item

    def retrieve(self, item_id: str) -> Optional[MemoryItem]:
        """Retrieve from any memory store"""
        # Try working memory first
        item = self.working.retrieve(item_id)
        if item:
            return item

        # Try long-term
        item = self.long_term.retrieve(item_id)
        if item:
            # Load into working memory
            self.working.store(item)
            return item

        return None

    def consolidate(self):
        """Consolidate working memory to long-term"""
        for item in list(self.working.items.values()):
            if item.access_count > 3:  # Rehearsed enough
                self.long_term.store(item)

    def forget(self) -> int:
        """Apply forgetting"""
        return self.long_term.forget()

    def search(self, query: Dict[str, Any]) -> List[MemoryItem]:
        """Search across memory stores"""
        results = []

        # Search long-term
        results.extend(self.long_term.search(query))

        # Include working memory matches
        for item in self.working.get_contents():
            match = all(
                item.context.get(k) == v
                for k, v in query.items()
            )
            if match:
                results.append(item)

        return results


# Export all
__all__ = [
    'MemoryType',
    'MemoryItem',
    'WorkingMemory',
    'LongTermMemory',
    'Episode',
    'EpisodicMemory',
    'SemanticMemory',
    'UnifiedMemory',
]
