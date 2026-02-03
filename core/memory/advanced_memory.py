"""
Advanced Memory & Learning System

Long-term memory with knowledge graphs, context retention, pattern extraction.
Agents remember everything and learn from all history.
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class MemoryType(Enum):
    """Types of memory."""
    EPISODIC = "episodic"  # Specific events/experiences
    SEMANTIC = "semantic"  # Facts and knowledge
    PROCEDURAL = "procedural"  # How-to knowledge
    EMOTIONAL = "emotional"  # Emotional context
    WORKING = "working"  # Short-term context


@dataclass
class MemoryEntry:
    """Single memory entry."""
    id: str
    memory_type: MemoryType
    content: str
    timestamp: datetime
    relevance_score: float = 1.0
    access_count: int = 0
    related_ids: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def update_relevance(self, decay_factor: float = 0.95):
        """Update relevance based on time decay."""
        hours_old = (datetime.now() - self.timestamp).total_seconds() / 3600
        self.relevance_score *= (decay_factor ** (hours_old / 24))


@dataclass
class KnowledgeNode:
    """Node in knowledge graph."""
    id: str
    entity_type: str
    name: str
    properties: Dict[str, Any]
    connections: Dict[str, List[str]] = field(default_factory=dict)
    importance: float = 1.0
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class KnowledgeEdge:
    """Edge between knowledge nodes."""
    source_id: str
    target_id: str
    relationship_type: str
    weight: float = 1.0
    context: Optional[str] = None


class AdvancedMemorySystem:
    """Advanced memory with multiple memory types and knowledge graph."""

    def __init__(self, max_memories: int = 100000):
        """Initialize memory system."""
        self.memories: Dict[str, MemoryEntry] = {}
        self.knowledge_graph: Dict[str, KnowledgeNode] = {}
        self.knowledge_edges: List[KnowledgeEdge] = []

        self.memory_types_count: Dict[MemoryType, int] = {t: 0 for t in MemoryType}
        self.access_patterns: Dict[str, List[datetime]] = {}
        self.max_memories = max_memories

        self.created_at = datetime.now()

    def add_memory(
        self,
        content: str,
        memory_type: MemoryType,
        metadata: Optional[Dict] = None,
        related_ids: Optional[List[str]] = None
    ) -> str:
        """Add memory entry."""
        memory_id = hashlib.md5(
            f"{content}{datetime.now().timestamp()}".encode()
        ).hexdigest()[:16]

        entry = MemoryEntry(
            id=memory_id,
            memory_type=memory_type,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata or {},
            related_ids=set(related_ids or [])
        )

        self.memories[memory_id] = entry
        self.memory_types_count[memory_type] += 1

        # Track access
        if memory_id not in self.access_patterns:
            self.access_patterns[memory_id] = []
        self.access_patterns[memory_id].append(datetime.now())

        return memory_id

    def recall_memory(self, memory_id: str) -> Optional[MemoryEntry]:
        """Recall memory by ID."""
        if memory_id in self.memories:
            entry = self.memories[memory_id]
            entry.access_count += 1

            if memory_id not in self.access_patterns:
                self.access_patterns[memory_id] = []
            self.access_patterns[memory_id].append(datetime.now())

            return entry

        return None

    def search_memories(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        limit: int = 10
    ) -> List[MemoryEntry]:
        """Search memories by content."""
        results = []

        for entry in self.memories.values():
            # Filter by type if specified
            if memory_type and entry.memory_type != memory_type:
                continue

            # Simple keyword matching (in real system, use embeddings)
            if query.lower() in entry.content.lower():
                results.append(entry)

        # Sort by relevance
        results.sort(
            key=lambda x: (x.relevance_score, x.access_count),
            reverse=True
        )

        return results[:limit]

    def add_knowledge_node(
        self,
        entity_type: str,
        name: str,
        properties: Dict[str, Any]
    ) -> str:
        """Add knowledge graph node."""
        node_id = hashlib.md5(f"{name}{entity_type}".encode()).hexdigest()[:16]

        if node_id not in self.knowledge_graph:
            node = KnowledgeNode(
                id=node_id,
                entity_type=entity_type,
                name=name,
                properties=properties
            )
            self.knowledge_graph[node_id] = node

        return node_id

    def add_knowledge_edge(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        weight: float = 1.0,
        context: Optional[str] = None
    ):
        """Add edge between knowledge nodes."""
        # Verify nodes exist
        if source_id not in self.knowledge_graph or target_id not in self.knowledge_graph:
            return False

        edge = KnowledgeEdge(
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
            weight=weight,
            context=context
        )

        self.knowledge_edges.append(edge)

        # Update connections
        if relationship_type not in self.knowledge_graph[source_id].connections:
            self.knowledge_graph[source_id].connections[relationship_type] = []

        self.knowledge_graph[source_id].connections[relationship_type].append(target_id)

        return True

    def get_related_knowledge(self, node_id: str, depth: int = 2) -> Dict[str, Any]:
        """Get related knowledge by traversing graph."""
        if node_id not in self.knowledge_graph:
            return {}

        visited = set()
        queue = [(node_id, 0)]
        related = {}

        while queue:
            current_id, current_depth = queue.pop(0)

            if current_id in visited or current_depth >= depth:
                continue

            visited.add(current_id)
            node = self.knowledge_graph[current_id]

            related[current_id] = {
                "name": node.name,
                "type": node.entity_type,
                "properties": node.properties,
                "depth": current_depth
            }

            # Add connected nodes
            for rel_type, targets in node.connections.items():
                for target_id in targets:
                    if target_id not in visited:
                        queue.append((target_id, current_depth + 1))

        return related

    def get_stats(self) -> Dict[str, Any]:
        """Get memory system statistics."""
        return {
            "total_memories": len(self.memories),
            "memories_by_type": {
                t.value: self.memory_types_count[t]
                for t in MemoryType
            },
            "knowledge_nodes": len(self.knowledge_graph),
            "knowledge_edges": len(self.knowledge_edges),
            "uptime_hours": (datetime.now() - self.created_at).total_seconds() / 3600
        }


class LearningSystem:
    """Learn from execution history and optimize strategies."""

    def __init__(self, memory_system: AdvancedMemorySystem):
        """Initialize learning system."""
        self.memory = memory_system
        self.patterns: Dict[str, Dict[str, Any]] = {}
        self.strategy_performance: Dict[str, List[float]] = {}
        self.optimization_suggestions: List[Dict] = []

        self.learning_count = 0

    def learn_from_success(
        self,
        task_type: str,
        strategy_used: str,
        context: Dict[str, Any],
        result_quality: float = 1.0
    ):
        """Learn from successful execution."""
        # Store memory
        memory_id = self.memory.add_memory(
            content=f"Success with {strategy_used} on {task_type}",
            memory_type=MemoryType.PROCEDURAL,
            metadata={
                "task": task_type,
                "strategy": strategy_used,
                "quality": result_quality,
                "context": context
            }
        )

        # Track strategy performance
        if strategy_used not in self.strategy_performance:
            self.strategy_performance[strategy_used] = []
        self.strategy_performance[strategy_used].append(result_quality)

        # Extract pattern
        pattern_key = f"{task_type}_{strategy_used}"
        if pattern_key not in self.patterns:
            self.patterns[pattern_key] = {
                "successes": 0,
                "failures": 0,
                "avg_quality": 0,
                "contexts": []
            }

        self.patterns[pattern_key]["successes"] += 1
        self.patterns[pattern_key]["contexts"].append(context)

        # Update average
        pattern = self.patterns[pattern_key]
        total = pattern["successes"] + pattern["failures"]
        pattern["avg_quality"] = (
            (pattern["avg_quality"] * (total - 1) + result_quality) / total
        )

        self.learning_count += 1

    def learn_from_failure(
        self,
        task_type: str,
        strategy_used: str,
        error: str,
        context: Dict[str, Any]
    ):
        """Learn from failed execution."""
        # Store memory
        memory_id = self.memory.add_memory(
            content=f"Failure with {strategy_used} on {task_type}: {error}",
            memory_type=MemoryType.EPISODIC,
            metadata={
                "task": task_type,
                "strategy": strategy_used,
                "error": error,
                "context": context
            }
        )

        # Track strategy performance (0 quality)
        if strategy_used not in self.strategy_performance:
            self.strategy_performance[strategy_used] = []
        self.strategy_performance[strategy_used].append(0.0)

        # Extract pattern
        pattern_key = f"{task_type}_{strategy_used}"
        if pattern_key not in self.patterns:
            self.patterns[pattern_key] = {
                "successes": 0,
                "failures": 0,
                "avg_quality": 0,
                "contexts": []
            }

        self.patterns[pattern_key]["failures"] += 1
        self.patterns[pattern_key]["contexts"].append(context)

    def generate_optimization_suggestions(self) -> List[Dict]:
        """Generate optimization suggestions."""
        suggestions = []

        # Analyze pattern performance
        for pattern_key, pattern in self.patterns.items():
            if pattern["successes"] + pattern["failures"] < 5:
                continue  # Not enough data

            success_rate = pattern["successes"] / (
                pattern["successes"] + pattern["failures"]
            )

            if success_rate < 0.5:
                suggestions.append({
                    "type": "low_success_rate",
                    "pattern": pattern_key,
                    "success_rate": success_rate,
                    "recommendation": f"Consider alternative strategies for {pattern_key}"
                })

            if pattern["avg_quality"] < 0.7:
                suggestions.append({
                    "type": "low_quality",
                    "pattern": pattern_key,
                    "quality": pattern["avg_quality"],
                    "recommendation": f"Improve quality handling for {pattern_key}"
                })

        # Analyze strategy performance
        for strategy, scores in self.strategy_performance.items():
            if len(scores) < 5:
                continue

            avg_score = sum(scores) / len(scores)

            if avg_score > 0.8:
                suggestions.append({
                    "type": "high_performing_strategy",
                    "strategy": strategy,
                    "avg_score": avg_score,
                    "recommendation": f"Use {strategy} more often"
                })

        self.optimization_suggestions = suggestions
        return suggestions

    def get_learning_stats(self) -> Dict[str, Any]:
        """Get learning statistics."""
        return {
            "total_learning_events": self.learning_count,
            "patterns_discovered": len(self.patterns),
            "strategies_tracked": len(self.strategy_performance),
            "suggestions_generated": len(self.optimization_suggestions),
            "memory_stats": self.memory.get_stats()
        }


# Integration with agents
if __name__ == "__main__":
    # Demo
    memory = AdvancedMemorySystem()
    learning = LearningSystem(memory)

    # Add some memories
    m1 = memory.add_memory(
        "Successfully executed deployment using parallel strategy",
        MemoryType.PROCEDURAL
    )

    m2 = memory.add_memory(
        "GitHub API rate limit exceeded during sync",
        MemoryType.EPISODIC
    )

    # Add knowledge graph
    github_id = memory.add_knowledge_node("service", "GitHub", {"type": "vcs"})
    slack_id = memory.add_knowledge_node("service", "Slack", {"type": "communication"})

    memory.add_knowledge_edge(github_id, slack_id, "notifies_to")

    # Learn from events
    learning.learn_from_success(
        "deployment",
        "parallel",
        {"services": 3, "duration": 120},
        0.95
    )

    learning.learn_from_failure(
        "sync",
        "sequential",
        "rate_limit",
        {"api": "github"}
    )

    # Get stats
    print(f"Memory stats: {memory.get_stats()}")
    print(f"Learning stats: {learning.get_learning_stats()}")
