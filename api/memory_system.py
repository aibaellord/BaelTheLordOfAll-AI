"""
Advanced Multi-Layer Memory System for BAEL

Implements episodic, semantic, procedural, working, and meta-memory layers
with automatic consolidation, decay curves, and context optimization.
"""

import hashlib
import json
import math
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class MemoryType(Enum):
    """Types of memory in the system."""
    EPISODIC = "episodic"  # Specific events and interactions
    SEMANTIC = "semantic"  # General knowledge and concepts
    PROCEDURAL = "procedural"  # Skills and how-to knowledge
    WORKING = "working"  # Current context and active information
    META = "meta"  # Knowledge about knowledge
    IMPLICIT = "implicit"  # Learned patterns and associations


class MemoryPriority(Enum):
    """Priority levels for memory retention."""
    CRITICAL = 5
    HIGH = 4
    NORMAL = 3
    LOW = 2
    MINIMAL = 1


@dataclass
class MemoryEntry:
    """Single memory entry with metadata."""
    entry_id: str
    content: str
    memory_type: MemoryType
    timestamp: datetime
    priority: MemoryPriority
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    related_entries: Set[str] = field(default_factory=set)
    importance_score: float = 0.5
    embedding: Optional[List[float]] = None
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def decay_score(self) -> float:
        """Calculate memory decay based on time since last access."""
        if self.last_accessed is None:
            time_passed = (datetime.now() - self.timestamp).total_seconds()
        else:
            time_passed = (datetime.now() - self.last_accessed).total_seconds()

        # Exponential decay with half-life
        half_life = 86400 * 7  # 7 days in seconds
        decay = math.exp(-time_passed / half_life)
        return decay * self.importance_score

    def retrieval_strength(self) -> float:
        """Calculate retrieval strength based on access patterns."""
        base_strength = math.log(self.access_count + 1)
        decay = self.decay_score()
        priority_boost = self.priority.value / 5.0
        return (base_strength + priority_boost) * decay


@dataclass
class MemoryConsolidationEvent:
    """Consolidation of related memories."""
    consolidated_ids: List[str]
    result_id: str
    timestamp: datetime
    consolidation_type: str


class EpisodicMemory:
    """Stores specific events and interactions with temporal context."""

    def __init__(self, max_entries: int = 10000):
        self.entries: Dict[str, MemoryEntry] = {}
        self.timeline: deque = deque(maxlen=max_entries)
        self.max_entries = max_entries

    def store(self, content: str, priority: MemoryPriority = MemoryPriority.NORMAL,
              tags: Optional[Set[str]] = None, metadata: Optional[Dict] = None) -> str:
        """Store episodic memory with context."""
        entry_id = hashlib.md5(
            f"{content}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        entry = MemoryEntry(
            entry_id=entry_id,
            content=content,
            memory_type=MemoryType.EPISODIC,
            timestamp=datetime.now(),
            priority=priority,
            tags=tags or set(),
            metadata=metadata or {}
        )

        self.entries[entry_id] = entry
        self.timeline.append(entry_id)
        return entry_id

    def retrieve(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve episodic memory and update access time."""
        if entry_id in self.entries:
            entry = self.entries[entry_id]
            entry.access_count += 1
            entry.last_accessed = datetime.now()
            return entry
        return None

    def query_temporal(self, start_time: datetime, end_time: datetime) -> List[MemoryEntry]:
        """Query memories within time range."""
        return [
            self.entries[eid] for eid in self.timeline
            if start_time <= self.entries[eid].timestamp <= end_time
        ]

    def get_recent(self, n: int = 10) -> List[MemoryEntry]:
        """Get most recent memories."""
        ids = list(self.timeline)[-n:]
        return [self.entries[eid] for eid in ids if eid in self.entries]


class SemanticMemory:
    """Stores general knowledge, facts, and concepts."""

    def __init__(self):
        self.concepts: Dict[str, Dict[str, Any]] = {}
        self.relationships: Dict[str, List[Tuple[str, str, str]]] = defaultdict(list)
        self.properties: Dict[str, Dict[str, Any]] = defaultdict(dict)

    def store_concept(self, concept: str, definition: str,
                     properties: Optional[Dict] = None) -> None:
        """Store semantic concept."""
        concept_lower = concept.lower()
        self.concepts[concept_lower] = {
            "name": concept,
            "definition": definition,
            "created": datetime.now(),
            "accessed": 0
        }
        if properties:
            self.properties[concept_lower].update(properties)

    def add_relationship(self, subject: str, relation: str, obj: str) -> None:
        """Add semantic relationship between concepts."""
        key = subject.lower()
        self.relationships[key].append((relation, obj.lower(), obj))

    def get_concept(self, concept: str) -> Optional[Dict]:
        """Retrieve concept definition and properties."""
        key = concept.lower()
        if key in self.concepts:
            self.concepts[key]["accessed"] += 1
            return {
                **self.concepts[key],
                "properties": self.properties[key],
                "relationships": self.relationships[key]
            }
        return None

    def infer_properties(self, concept: str) -> Dict[str, Any]:
        """Infer properties through relationships."""
        key = concept.lower()
        inferred = dict(self.properties[key])

        for relation, related_concept, _ in self.relationships[key]:
            if relation == "is_a" and related_concept in self.properties:
                inferred.update(self.properties[related_concept])

        return inferred


class ProceduralMemory:
    """Stores skills, procedures, and learned patterns."""

    def __init__(self):
        self.procedures: Dict[str, Dict[str, Any]] = {}
        self.skills: Dict[str, Dict[str, Any]] = {}
        self.patterns: Dict[str, List[Dict]] = defaultdict(list)

    def store_procedure(self, name: str, steps: List[str],
                       preconditions: Optional[List[str]] = None,
                       postconditions: Optional[List[str]] = None) -> None:
        """Store procedural knowledge."""
        self.procedures[name] = {
            "name": name,
            "steps": steps,
            "preconditions": preconditions or [],
            "postconditions": postconditions or [],
            "created": datetime.now(),
            "success_rate": 1.0,
            "execution_count": 0
        }

    def store_skill(self, skill_name: str, capability: str,
                   proficiency: float = 0.5) -> None:
        """Store learned skill."""
        self.skills[skill_name] = {
            "name": skill_name,
            "capability": capability,
            "proficiency": min(1.0, max(0.0, proficiency)),
            "learned": datetime.now(),
            "practice_count": 0
        }

    def record_pattern(self, pattern_name: str, context: str, outcome: Any) -> None:
        """Record observed pattern for future matching."""
        self.patterns[pattern_name].append({
            "context": context,
            "outcome": outcome,
            "timestamp": datetime.now()
        })

    def get_procedure(self, name: str) -> Optional[Dict]:
        """Retrieve procedure with execution history."""
        if name in self.procedures:
            proc = self.procedures[name]
            proc["execution_count"] += 1
            return proc
        return None

    def improve_skill(self, skill_name: str, improvement: float) -> None:
        """Improve skill proficiency through practice."""
        if skill_name in self.skills:
            skill = self.skills[skill_name]
            skill["practice_count"] += 1
            skill["proficiency"] = min(1.0, skill["proficiency"] + improvement * 0.01)


class WorkingMemory:
    """Active, limited-capacity buffer for current processing."""

    def __init__(self, capacity: int = 7):
        self.capacity = capacity
        self.buffer: deque = deque(maxlen=capacity)
        self.focus_item: Optional[str] = None
        self.attention_weights: Dict[str, float] = {}

    def add_item(self, item: Any, importance: float = 0.5) -> None:
        """Add item to working memory."""
        self.buffer.append(item)
        self.attention_weights[str(item)] = importance

    def set_focus(self, item: Any) -> None:
        """Set attention focus on specific item."""
        self.focus_item = str(item)
        self.attention_weights[self.focus_item] = 1.0

    def get_buffer(self) -> List[Any]:
        """Get current buffer contents."""
        return list(self.buffer)

    def clear(self) -> None:
        """Clear working memory."""
        self.buffer.clear()
        self.focus_item = None
        self.attention_weights.clear()

    def get_attended_items(self, top_k: int = 3) -> List[Tuple[Any, float]]:
        """Get top-k items by attention weight."""
        sorted_items = sorted(
            self.attention_weights.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]

        buffer_items = [str(item) for item in self.buffer]
        return [
            (item, weight) for item, weight in sorted_items
            if item in buffer_items
        ]


class MetaMemory:
    """Knowledge about memory, learning strategies, and self-reflection."""

    def __init__(self):
        self.learning_strategies: Dict[str, Dict[str, Any]] = {}
        self.memory_effectiveness: Dict[str, float] = defaultdict(float)
        self.self_reflection_logs: List[Dict] = []
        self.confidence_scores: Dict[str, float] = {}

    def record_strategy(self, strategy_name: str, context: str,
                       effectiveness: float) -> None:
        """Record effectiveness of learning strategy."""
        if strategy_name not in self.learning_strategies:
            self.learning_strategies[strategy_name] = {
                "uses": 0,
                "successes": 0,
                "avg_effectiveness": 0.0
            }

        strategy = self.learning_strategies[strategy_name]
        strategy["uses"] += 1
        if effectiveness > 0.5:
            strategy["successes"] += 1
        strategy["avg_effectiveness"] = (
            (strategy["avg_effectiveness"] * (strategy["uses"] - 1) + effectiveness) /
            strategy["uses"]
        )

    def get_best_strategy(self, context: str) -> Optional[str]:
        """Get most effective strategy for context."""
        if not self.learning_strategies:
            return None

        best = max(
            self.learning_strategies.items(),
            key=lambda x: x[1]["avg_effectiveness"]
        )
        return best[0]

    def record_reflection(self, reflection: Dict[str, Any]) -> None:
        """Record self-reflection about performance."""
        self.self_reflection_logs.append({
            **reflection,
            "timestamp": datetime.now()
        })

    def set_confidence(self, topic: str, confidence: float) -> None:
        """Set confidence score for topic."""
        self.confidence_scores[topic] = min(1.0, max(0.0, confidence))

    def get_confidence(self, topic: str) -> float:
        """Get confidence about topic."""
        return self.confidence_scores.get(topic, 0.5)


class MemoryConsolidator:
    """Consolidates and optimizes memory through sleep-like processes."""

    def __init__(self, episodic: EpisodicMemory, semantic: SemanticMemory):
        self.episodic = episodic
        self.semantic = semantic
        self.consolidation_history: List[MemoryConsolidationEvent] = []

    def consolidate_episodic_to_semantic(self, min_occurrences: int = 3) -> List[str]:
        """Consolidate recurring episodic memories into semantic knowledge."""
        pattern_counter: Dict[str, List[str]] = defaultdict(list)

        for entry_id, entry in self.episodic.entries.items():
            pattern_key = hashlib.md5(entry.content.encode()).hexdigest()[:8]
            pattern_counter[pattern_key].append(entry_id)

        consolidated = []
        for pattern, entry_ids in pattern_counter.items():
            if len(entry_ids) >= min_occurrences:
                # Extract concept and consolidate to semantic
                entries = [self.episodic.entries[eid] for eid in entry_ids]
                avg_priority = sum(e.priority.value for e in entries) / len(entries)

                concept = f"concept_{pattern}"
                self.semantic.store_concept(
                    concept,
                    f"Consolidated from {len(entries)} episodic memories"
                )

                self.consolidation_history.append(
                    MemoryConsolidationEvent(
                        consolidated_ids=entry_ids,
                        result_id=concept,
                        timestamp=datetime.now(),
                        consolidation_type="episodic_to_semantic"
                    )
                )
                consolidated.append(concept)

        return consolidated

    def prune_weak_memories(self, decay_threshold: float = 0.1) -> int:
        """Remove memories below retention threshold."""
        weak_entries = [
            eid for eid, entry in self.episodic.entries.items()
            if entry.decay_score() < decay_threshold
        ]

        for eid in weak_entries:
            del self.episodic.entries[eid]

        return len(weak_entries)


class AdvancedMemorySystem:
    """Unified memory system integrating all layers."""

    def __init__(self):
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory()
        self.procedural = ProceduralMemory()
        self.working = WorkingMemory(capacity=7)
        self.meta = MetaMemory()
        self.consolidator = MemoryConsolidator(self.episodic, self.semantic)
        self.total_operations = 0

    def remember_event(self, event: str, priority: MemoryPriority = MemoryPriority.NORMAL,
                      tags: Optional[Set[str]] = None) -> str:
        """Remember an event."""
        self.total_operations += 1
        return self.episodic.store(event, priority, tags)

    def learn_fact(self, concept: str, definition: str,
                   properties: Optional[Dict] = None) -> None:
        """Learn semantic knowledge."""
        self.total_operations += 1
        self.semantic.store_concept(concept, definition, properties)

    def learn_procedure(self, name: str, steps: List[str]) -> None:
        """Learn how to do something."""
        self.total_operations += 1
        self.procedural.store_procedure(name, steps)

    def focus_on(self, item: Any) -> None:
        """Set attention to item in working memory."""
        self.working.set_focus(item)

    def consolidate(self) -> Dict[str, Any]:
        """Run memory consolidation (like sleep)."""
        pruned = self.consolidator.prune_weak_memories()
        consolidated = self.consolidator.consolidate_episodic_to_semantic()

        return {
            "pruned_memories": pruned,
            "consolidated_concepts": consolidated,
            "timestamp": datetime.now().isoformat()
        }

    def get_relevant_memories(self, query: str, k: int = 5) -> Dict[str, List]:
        """Retrieve most relevant memories for query."""
        relevant = {
            "episodic": self.episodic.get_recent(k),
            "semantic": [],
            "procedural": []
        }

        query_lower = query.lower()
        for concept in self.semantic.concepts:
            if concept in query_lower or query_lower in self.semantic.concepts[concept].get("definition", "").lower():
                relevant["semantic"].append(self.semantic.get_concept(concept))

        return {
            k: [e.content if isinstance(e, MemoryEntry) else e for e in v]
            for k, v in relevant.items()
        }

    def get_system_stats(self) -> Dict[str, Any]:
        """Get memory system statistics."""
        return {
            "total_operations": self.total_operations,
            "episodic_entries": len(self.episodic.entries),
            "semantic_concepts": len(self.semantic.concepts),
            "procedural_skills": len(self.procedural.skills),
            "working_memory_size": len(self.working.buffer),
            "consolidation_events": len(self.consolidator.consolidation_history),
            "timestamp": datetime.now().isoformat()
        }


# Global memory system instance
_memory_system = None


def get_memory_system() -> AdvancedMemorySystem:
    """Get or create global memory system."""
    global _memory_system
    if _memory_system is None:
        _memory_system = AdvancedMemorySystem()
    return _memory_system
