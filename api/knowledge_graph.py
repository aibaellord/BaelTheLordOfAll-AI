"""
Knowledge Graph Engine for BAEL Phase 2

Implements semantic relationship mapping, knowledge extraction, and
graph-based reasoning for enhanced contextual understanding.

Key Components:
- Knowledge graph construction and maintenance
- Relationship extraction and typing
- Semantic reasoning over graphs
- Entity recognition and linking
- Path finding and pattern detection
- Knowledge persistence and querying
"""

import hashlib
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class RelationshipType(str, Enum):
    """Types of relationships in knowledge graph."""
    IS_A = "is_a"  # Inheritance
    PART_OF = "part_of"  # Composition
    DEPENDS_ON = "depends_on"  # Dependency
    RELATED_TO = "related_to"  # Generic relation
    CAUSES = "causes"  # Causality
    ENABLES = "enables"  # Enablement
    PRECEDES = "precedes"  # Temporal order
    SIMILAR_TO = "similar_to"  # Similarity
    CONTRADICTS = "contradicts"  # Opposition
    IMPLIES = "implies"  # Logical implication


class EntityType(str, Enum):
    """Types of entities in knowledge graph."""
    CONCEPT = "concept"
    AGENT = "agent"
    OBJECT = "object"
    EVENT = "event"
    PROPERTY = "property"
    RELATIONSHIP = "relationship"
    RULE = "rule"
    ACTION = "action"


@dataclass
class Entity:
    """Entity in knowledge graph."""
    entity_id: str
    name: str
    entity_type: EntityType
    description: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    source: str = "unknown"
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "entity_id": self.entity_id,
            "name": self.name,
            "entity_type": self.entity_type.value,
            "description": self.description,
            "properties": self.properties,
            "confidence": self.confidence,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class Relationship:
    """Relationship between entities."""
    relationship_id: str
    source_entity_id: str
    target_entity_id: str
    relationship_type: RelationshipType
    strength: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    properties: Dict[str, Any] = field(default_factory=dict)
    source: str = "unknown"
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "relationship_id": self.relationship_id,
            "source_entity_id": self.source_entity_id,
            "target_entity_id": self.target_entity_id,
            "relationship_type": self.relationship_type.value,
            "strength": self.strength,
            "confidence": self.confidence,
            "properties": self.properties,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
        }


class KnowledgeGraph:
    """Main knowledge graph structure."""

    def __init__(self):
        """Initialize knowledge graph."""
        self.entities: Dict[str, Entity] = {}
        self.relationships: Dict[str, Relationship] = {}
        self.adjacency: Dict[str, List[str]] = defaultdict(list)  # entity -> relationships
        self.indexes: Dict[str, Dict[str, Set[str]]] = {
            "by_type": defaultdict(set),
            "by_name": defaultdict(set),
        }

    def add_entity(self, entity: Entity) -> None:
        """Add entity to graph."""
        if entity.entity_id in self.entities:
            logger.debug(f"Updating entity {entity.entity_id}")

        self.entities[entity.entity_id] = entity
        self.indexes["by_type"][entity.entity_type.value].add(entity.entity_id)
        self.indexes["by_name"][entity.name.lower()].add(entity.entity_id)

        logger.debug(f"Added entity: {entity.name}")

    def add_relationship(self, relationship: Relationship) -> None:
        """Add relationship to graph."""
        if relationship.relationship_id in self.relationships:
            logger.debug(f"Updating relationship {relationship.relationship_id}")

        self.relationships[relationship.relationship_id] = relationship
        self.adjacency[relationship.source_entity_id].append(
            relationship.relationship_id
        )
        self.adjacency[relationship.target_entity_id].append(
            relationship.relationship_id
        )

        logger.debug(
            f"Added relationship: {relationship.source_entity_id} -"
            f" {relationship.relationship_type.value} ->"
            f" {relationship.target_entity_id}"
        )

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID."""
        return self.entities.get(entity_id)

    def find_entities_by_name(self, name: str) -> List[Entity]:
        """Find entities by name."""
        entity_ids = self.indexes["by_name"].get(name.lower(), set())
        return [self.entities[eid] for eid in entity_ids]

    def find_entities_by_type(self, entity_type: EntityType) -> List[Entity]:
        """Find entities by type."""
        entity_ids = self.indexes["by_type"].get(entity_type.value, set())
        return [self.entities[eid] for eid in entity_ids]

    def get_relationships(self, source_id: str, target_id: Optional[str] = None) -> List[Relationship]:
        """Get relationships for entity."""
        rel_ids = self.adjacency.get(source_id, [])
        relationships = [self.relationships[rid] for rid in rel_ids if rid in self.relationships]

        if target_id:
            relationships = [
                r for r in relationships
                if (r.source_entity_id == source_id and r.target_entity_id == target_id) or
                   (r.source_entity_id == target_id and r.target_entity_id == source_id)
            ]

        return relationships

    def find_paths(
        self,
        source_id: str,
        target_id: str,
        max_length: int = 5,
    ) -> List[List[Relationship]]:
        """Find paths between entities."""
        paths = []

        def dfs(current_id: str, target: str, path: List[Relationship], visited: Set[str]) -> None:
            if current_id == target:
                paths.append(path.copy())
                return

            if len(path) >= max_length:
                return

            visited.add(current_id)

            for rel in self.get_relationships(current_id):
                next_id = rel.target_entity_id if rel.source_entity_id == current_id else rel.source_entity_id

                if next_id not in visited:
                    path.append(rel)
                    dfs(next_id, target, path, visited.copy())
                    path.pop()

        dfs(source_id, target_id, [], set())
        return paths

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "entities": {eid: e.to_dict() for eid, e in self.entities.items()},
            "relationships": {rid: r.to_dict() for rid, r in self.relationships.items()},
            "entity_count": len(self.entities),
            "relationship_count": len(self.relationships),
        }


class EntityExtractor:
    """Extracts entities from text."""

    def extract(self, text: str, entity_types: Optional[List[EntityType]] = None) -> List[Entity]:
        """
        Extract entities from text.

        Args:
            text: Text to extract from
            entity_types: Entity types to extract (None = all)

        Returns:
            List of extracted entities
        """
        entities = []

        # Simple extraction based on patterns
        words = text.split()
        for word in words:
            if len(word) > 3:  # Minimum word length
                entity = Entity(
                    entity_id=f"entity_{self._hash_word(word)}",
                    name=word,
                    entity_type=EntityType.CONCEPT,
                    confidence=0.7,
                    source="text_extraction",
                )
                entities.append(entity)

        return entities

    def _hash_word(self, word: str) -> str:
        """Hash word to ID."""
        return hashlib.md5(word.encode()).hexdigest()[:8]


class RelationshipExtractor:
    """Extracts relationships between entities."""

    def extract(
        self,
        source: str,
        target: str,
        context: Optional[str] = None,
    ) -> List[Relationship]:
        """
        Extract relationships between entities.

        Args:
            source: Source entity name
            target: Target entity name
            context: Context text

        Returns:
            List of extracted relationships
        """
        relationships = []

        # Simple relationship detection
        relationship_triggers = {
            RelationshipType.DEPENDS_ON: ["depends", "requires", "needs"],
            RelationshipType.CAUSES: ["causes", "results", "leads"],
            RelationshipType.ENABLES: ["enables", "allows", "permits"],
            RelationshipType.IS_A: ["is", "was", "type of"],
            RelationshipType.PART_OF: ["part", "component", "element"],
        }

        context_lower = (context or "").lower()

        for rel_type, triggers in relationship_triggers.items():
            if any(trigger in context_lower for trigger in triggers):
                rel_id = f"rel_{len(relationships)}"
                relationship = Relationship(
                    relationship_id=rel_id,
                    source_entity_id=source,
                    target_entity_id=target,
                    relationship_type=rel_type,
                    strength=0.8,
                    confidence=0.7,
                    source="context_extraction",
                )
                relationships.append(relationship)
                break

        return relationships


class SemanticReasoner:
    """Performs semantic reasoning over knowledge graph."""

    def __init__(self, graph: KnowledgeGraph):
        """Initialize reasoner."""
        self.graph = graph

    def infer_properties(self, entity_id: str) -> Dict[str, Any]:
        """
        Infer properties for entity based on relationships.

        Args:
            entity_id: Entity to infer for

        Returns:
            Inferred properties
        """
        inferred = {}

        entity = self.graph.get_entity(entity_id)
        if not entity:
            return inferred

        # Inherit properties from IS_A relationships
        for rel in self.graph.get_relationships(entity_id):
            if rel.relationship_type == RelationshipType.IS_A:
                parent_id = rel.target_entity_id
                parent = self.graph.get_entity(parent_id)
                if parent:
                    inferred.update(parent.properties)

        return inferred

    def find_similar_entities(
        self,
        entity_id: str,
        max_distance: int = 2,
    ) -> List[Tuple[str, float]]:
        """
        Find entities similar to given entity.

        Args:
            entity_id: Reference entity
            max_distance: Maximum relationship distance

        Returns:
            List of (entity_id, similarity_score) tuples
        """
        similar = []
        visited = set()

        def explore(current_id: str, distance: int, score: float) -> None:
            if distance > max_distance or current_id in visited:
                return

            visited.add(current_id)

            if current_id != entity_id:
                similar.append((current_id, score))

            for rel in self.graph.get_relationships(current_id):
                next_id = (
                    rel.target_entity_id
                    if rel.source_entity_id == current_id
                    else rel.source_entity_id
                )
                new_score = score * rel.strength
                explore(next_id, distance + 1, new_score)

        explore(entity_id, 0, 1.0)
        similar.sort(key=lambda x: x[1], reverse=True)
        return similar[:10]  # Top 10

    def answer_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Answer natural language query over graph.

        Args:
            query: Query string

        Returns:
            Query results
        """
        results = []

        # Simple query handling
        query_lower = query.lower()

        # "What is X?" queries
        if query_lower.startswith("what is"):
            entity_name = query[7:].strip().rstrip("?")
            entities = self.graph.find_entities_by_name(entity_name)
            results = [{"entity": e.to_dict()} for e in entities]

        # "How is X related to Y?" queries
        elif "related" in query_lower:
            # Extract entity names and find paths
            pass

        # "Is X a Y?" queries
        elif query_lower.startswith("is"):
            # Check inheritance
            pass

        return results


class KnowledgeGraphEngine:
    """Main knowledge graph engine."""

    def __init__(self):
        """Initialize engine."""
        self.graph = KnowledgeGraph()
        self.entity_extractor = EntityExtractor()
        self.relationship_extractor = RelationshipExtractor()
        self.reasoner = SemanticReasoner(self.graph)
        self.snapshots: Dict[str, Dict[str, Any]] = {}

    def learn_from_text(self, text: str) -> int:
        """
        Learn from text by extracting entities and relationships.

        Args:
            text: Text to learn from

        Returns:
            Number of new facts learned
        """
        learned = 0

        # Extract entities
        entities = self.entity_extractor.extract(text)
        for entity in entities:
            if entity.entity_id not in self.graph.entities:
                self.graph.add_entity(entity)
                learned += 1

        # Extract relationships
        for i, entity1 in enumerate(entities):
            for entity2 in entities[i + 1 :]:
                relationships = self.relationship_extractor.extract(
                    entity1.entity_id,
                    entity2.entity_id,
                    text,
                )
                for rel in relationships:
                    if rel.relationship_id not in self.graph.relationships:
                        self.graph.add_relationship(rel)
                        learned += 1

        return learned

    def add_knowledge(
        self,
        entity: Entity,
        relationships: Optional[List[Relationship]] = None,
    ) -> None:
        """
        Add knowledge to graph.

        Args:
            entity: Entity to add
            relationships: Optional relationships to add
        """
        self.graph.add_entity(entity)

        if relationships:
            for rel in relationships:
                self.graph.add_relationship(rel)

    def query(self, query: str) -> List[Dict[str, Any]]:
        """Query the knowledge graph."""
        return self.reasoner.answer_query(query)

    def infer(self, entity_id: str) -> Dict[str, Any]:
        """Infer properties for entity."""
        inferred = {
            "properties": self.reasoner.infer_properties(entity_id),
            "similar_entities": self.reasoner.find_similar_entities(entity_id),
        }
        return inferred

    def export_snapshot(self) -> str:
        """Export graph snapshot."""
        snapshot_id = f"snapshot_{datetime.now().timestamp()}"
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "data": self.graph.to_dict(),
        }
        self.snapshots[snapshot_id] = snapshot
        return snapshot_id

    def get_statistics(self) -> Dict[str, Any]:
        """Get graph statistics."""
        return {
            "total_entities": len(self.graph.entities),
            "total_relationships": len(self.graph.relationships),
            "entity_types": {
                t.value: len(ids)
                for t, ids in self.graph.indexes["by_type"].items()
            },
            "relationship_types": self._count_relationship_types(),
            "graph_density": self._calculate_density(),
        }

    def _count_relationship_types(self) -> Dict[str, int]:
        """Count relationships by type."""
        counts = defaultdict(int)
        for rel in self.graph.relationships.values():
            counts[rel.relationship_type.value] += 1
        return dict(counts)

    def _calculate_density(self) -> float:
        """Calculate graph density."""
        n = len(self.graph.entities)
        if n < 2:
            return 0.0

        e = len(self.graph.relationships)
        max_edges = n * (n - 1) / 2  # Undirected graph
        return e / max_edges if max_edges > 0 else 0.0


# Global knowledge graph engine
_kg_engine = None


def get_knowledge_graph_engine() -> KnowledgeGraphEngine:
    """Get or create global knowledge graph engine."""
    global _kg_engine
    if _kg_engine is None:
        _kg_engine = KnowledgeGraphEngine()
    return _kg_engine
