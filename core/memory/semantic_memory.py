"""
BAEL Semantic Memory
=====================

Factual knowledge and concept storage for AI agents.
Manages structured knowledge with relationships.

Features:
- Concept storage
- Relationship mapping
- Hierarchical knowledge
- Semantic search
- Knowledge inference
"""

import asyncio
import hashlib
import logging
import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class RelationType(Enum):
    """Types of relationships between concepts."""
    IS_A = "is_a"  # Inheritance
    HAS_A = "has_a"  # Composition
    PART_OF = "part_of"  # Meronymy
    RELATED_TO = "related_to"  # Association
    CAUSES = "causes"  # Causation
    PRECEDES = "precedes"  # Temporal
    CONTRADICTS = "contradicts"  # Opposition
    IMPLIES = "implies"  # Logical
    SYNONYM = "synonym"  # Equivalence
    ANTONYM = "antonym"  # Opposition


class ConceptType(Enum):
    """Types of concepts."""
    ENTITY = "entity"
    ACTION = "action"
    PROPERTY = "property"
    ABSTRACT = "abstract"
    EVENT = "event"
    PROCESS = "process"


@dataclass
class Relation:
    """A relationship between concepts."""
    source: str
    target: str
    relation_type: RelationType

    # Properties
    weight: float = 1.0  # Strength of relation
    confidence: float = 1.0  # Certainty

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    source_info: str = ""  # Where this came from


@dataclass
class Concept:
    """A semantic concept."""
    id: str
    name: str
    concept_type: ConceptType = ConceptType.ENTITY

    # Definition
    definition: str = ""
    aliases: List[str] = field(default_factory=list)

    # Properties
    properties: Dict[str, Any] = field(default_factory=dict)

    # Hierarchy
    parent: Optional[str] = None
    children: List[str] = field(default_factory=list)

    # Embedding for semantic search
    embedding: Optional[List[float]] = None

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    importance: float = 0.5

    # Sources
    sources: List[str] = field(default_factory=list)


class KnowledgeGraph:
    """
    Knowledge graph for storing and querying relationships.
    """

    def __init__(self):
        # Adjacency lists
        self._outgoing: Dict[str, List[Relation]] = defaultdict(list)
        self._incoming: Dict[str, List[Relation]] = defaultdict(list)

        # Relation index by type
        self._by_type: Dict[RelationType, List[Relation]] = defaultdict(list)

    def add_relation(self, relation: Relation) -> None:
        """Add a relation to the graph."""
        self._outgoing[relation.source].append(relation)
        self._incoming[relation.target].append(relation)
        self._by_type[relation.relation_type].append(relation)

    def get_relations(
        self,
        concept_id: str,
        direction: str = "both",
        relation_type: Optional[RelationType] = None,
    ) -> List[Relation]:
        """Get relations for a concept."""
        results = []

        if direction in ("out", "both"):
            for rel in self._outgoing.get(concept_id, []):
                if relation_type is None or rel.relation_type == relation_type:
                    results.append(rel)

        if direction in ("in", "both"):
            for rel in self._incoming.get(concept_id, []):
                if relation_type is None or rel.relation_type == relation_type:
                    results.append(rel)

        return results

    def find_path(
        self,
        source: str,
        target: str,
        max_depth: int = 5,
    ) -> Optional[List[Relation]]:
        """Find path between concepts using BFS."""
        if source == target:
            return []

        visited = {source}
        queue = [(source, [])]

        while queue and len(visited) < 1000:
            current, path = queue.pop(0)

            for rel in self._outgoing.get(current, []):
                if rel.target == target:
                    return path + [rel]

                if rel.target not in visited and len(path) < max_depth:
                    visited.add(rel.target)
                    queue.append((rel.target, path + [rel]))

        return None

    def get_neighbors(
        self,
        concept_id: str,
        depth: int = 1,
    ) -> Set[str]:
        """Get neighboring concepts."""
        neighbors = set()
        current = {concept_id}

        for _ in range(depth):
            next_level = set()
            for cid in current:
                for rel in self._outgoing.get(cid, []):
                    next_level.add(rel.target)
                for rel in self._incoming.get(cid, []):
                    next_level.add(rel.source)

            neighbors.update(next_level)
            current = next_level - neighbors

        neighbors.discard(concept_id)
        return neighbors


class SemanticMemory:
    """
    Semantic memory system for BAEL.

    Manages factual knowledge with concept relationships.
    """

    def __init__(self):
        # Concepts
        self._concepts: Dict[str, Concept] = {}
        self._name_index: Dict[str, str] = {}  # name -> id
        self._alias_index: Dict[str, str] = {}  # alias -> id

        # Knowledge graph
        self.graph = KnowledgeGraph()

        # Categories
        self._categories: Dict[str, Set[str]] = defaultdict(set)

        # Stats
        self.stats = {
            "concepts_created": 0,
            "relations_created": 0,
            "queries": 0,
            "inferences": 0,
        }

    def add_concept(
        self,
        name: str,
        concept_type: ConceptType = ConceptType.ENTITY,
        definition: str = "",
        properties: Optional[Dict[str, Any]] = None,
        aliases: Optional[List[str]] = None,
        parent: Optional[str] = None,
    ) -> Concept:
        """
        Add a concept to semantic memory.

        Args:
            name: Concept name
            concept_type: Type of concept
            definition: Definition text
            properties: Concept properties
            aliases: Alternative names
            parent: Parent concept ID

        Returns:
            Created concept
        """
        concept_id = hashlib.md5(name.lower().encode()).hexdigest()[:12]

        # Check if exists
        if concept_id in self._concepts:
            return self._concepts[concept_id]

        concept = Concept(
            id=concept_id,
            name=name,
            concept_type=concept_type,
            definition=definition,
            properties=properties or {},
            aliases=aliases or [],
            parent=parent,
        )

        self._concepts[concept_id] = concept
        self._name_index[name.lower()] = concept_id

        for alias in concept.aliases:
            self._alias_index[alias.lower()] = concept_id

        # Add to parent
        if parent and parent in self._concepts:
            self._concepts[parent].children.append(concept_id)

            # Create IS_A relation
            self.add_relation(concept_id, parent, RelationType.IS_A)

        # Index by type
        self._categories[concept_type.value].add(concept_id)

        self.stats["concepts_created"] += 1

        logger.debug(f"Added concept: {name}")

        return concept

    def get_concept(
        self,
        identifier: str,
        by_name: bool = False,
    ) -> Optional[Concept]:
        """Get a concept by ID or name."""
        self.stats["queries"] += 1

        if by_name:
            concept_id = self._name_index.get(identifier.lower())
            if not concept_id:
                concept_id = self._alias_index.get(identifier.lower())
            if concept_id:
                return self._concepts.get(concept_id)
            return None

        return self._concepts.get(identifier)

    def add_relation(
        self,
        source: str,
        target: str,
        relation_type: RelationType,
        weight: float = 1.0,
        confidence: float = 1.0,
    ) -> Relation:
        """Add a relation between concepts."""
        relation = Relation(
            source=source,
            target=target,
            relation_type=relation_type,
            weight=weight,
            confidence=confidence,
        )

        self.graph.add_relation(relation)
        self.stats["relations_created"] += 1

        return relation

    def query_relations(
        self,
        concept: str,
        relation_type: Optional[RelationType] = None,
        direction: str = "both",
    ) -> List[Tuple[Concept, Relation]]:
        """
        Query relations for a concept.

        Args:
            concept: Concept ID or name
            relation_type: Filter by relation type
            direction: 'in', 'out', or 'both'

        Returns:
            List of (related_concept, relation)
        """
        # Resolve concept
        if concept not in self._concepts:
            resolved = self.get_concept(concept, by_name=True)
            if resolved:
                concept = resolved.id
            else:
                return []

        relations = self.graph.get_relations(concept, direction, relation_type)

        results = []
        for rel in relations:
            other_id = rel.target if rel.source == concept else rel.source
            other = self._concepts.get(other_id)
            if other:
                results.append((other, rel))

        return results

    def find_path(
        self,
        source_name: str,
        target_name: str,
    ) -> Optional[List[str]]:
        """Find conceptual path between two concepts."""
        source = self.get_concept(source_name, by_name=True)
        target = self.get_concept(target_name, by_name=True)

        if not source or not target:
            return None

        path = self.graph.find_path(source.id, target.id)

        if path:
            result = [source.name]
            for rel in path:
                concept = self._concepts.get(rel.target)
                if concept:
                    result.append(f"--[{rel.relation_type.value}]-->")
                    result.append(concept.name)
            return result

        return None

    def get_ancestors(
        self,
        concept_id: str,
    ) -> List[Concept]:
        """Get all ancestors (IS_A chain)."""
        ancestors = []
        current = concept_id
        visited = set()

        while current and current not in visited:
            visited.add(current)
            concept = self._concepts.get(current)
            if not concept or not concept.parent:
                break

            parent = self._concepts.get(concept.parent)
            if parent:
                ancestors.append(parent)
                current = parent.id
            else:
                break

        return ancestors

    def get_descendants(
        self,
        concept_id: str,
        max_depth: int = 10,
    ) -> List[Concept]:
        """Get all descendants."""
        descendants = []
        queue = [(concept_id, 0)]
        visited = {concept_id}

        while queue:
            current_id, depth = queue.pop(0)
            if depth >= max_depth:
                continue

            concept = self._concepts.get(current_id)
            if not concept:
                continue

            for child_id in concept.children:
                if child_id not in visited:
                    visited.add(child_id)
                    child = self._concepts.get(child_id)
                    if child:
                        descendants.append(child)
                        queue.append((child_id, depth + 1))

        return descendants

    def infer(
        self,
        concept_id: str,
        property_name: str,
    ) -> Optional[Any]:
        """
        Infer a property value through inheritance.

        Args:
            concept_id: Concept to query
            property_name: Property to infer

        Returns:
            Inferred value or None
        """
        self.stats["inferences"] += 1

        concept = self._concepts.get(concept_id)
        if not concept:
            return None

        # Check direct property
        if property_name in concept.properties:
            return concept.properties[property_name]

        # Check ancestors
        for ancestor in self.get_ancestors(concept_id):
            if property_name in ancestor.properties:
                return ancestor.properties[property_name]

        return None

    def search(
        self,
        query: str,
        concept_type: Optional[ConceptType] = None,
        limit: int = 10,
    ) -> List[Concept]:
        """Search concepts by text."""
        query_lower = query.lower()
        results = []

        for concept in self._concepts.values():
            if concept_type and concept.concept_type != concept_type:
                continue

            # Score by name/alias match
            score = 0.0
            if query_lower == concept.name.lower():
                score = 1.0
            elif query_lower in concept.name.lower():
                score = 0.8
            elif any(query_lower in a.lower() for a in concept.aliases):
                score = 0.6
            elif query_lower in concept.definition.lower():
                score = 0.4

            if score > 0:
                results.append((concept, score))

        results.sort(key=lambda x: x[1], reverse=True)

        return [c for c, _ in results[:limit]]

    def semantic_search(
        self,
        query_embedding: List[float],
        limit: int = 5,
    ) -> List[Tuple[Concept, float]]:
        """Search by semantic similarity."""
        results = []

        for concept in self._concepts.values():
            if concept.embedding:
                similarity = self._cosine_similarity(query_embedding, concept.embedding)
                results.append((concept, similarity))

        results.sort(key=lambda x: x[1], reverse=True)

        return results[:limit]

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

    def get_related_concepts(
        self,
        concept_id: str,
        depth: int = 2,
    ) -> List[Concept]:
        """Get concepts related within N hops."""
        neighbor_ids = self.graph.get_neighbors(concept_id, depth)

        return [
            self._concepts[cid]
            for cid in neighbor_ids
            if cid in self._concepts
        ]

    def export_knowledge(self) -> Dict[str, Any]:
        """Export knowledge base."""
        return {
            "concepts": [
                {
                    "id": c.id,
                    "name": c.name,
                    "type": c.concept_type.value,
                    "definition": c.definition,
                    "properties": c.properties,
                }
                for c in self._concepts.values()
            ],
            "relations": [
                {
                    "source": r.source,
                    "target": r.target,
                    "type": r.relation_type.value,
                    "weight": r.weight,
                }
                for rels in self.graph._outgoing.values()
                for r in rels
            ],
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return {
            **self.stats,
            "total_concepts": len(self._concepts),
            "total_relations": sum(len(r) for r in self.graph._outgoing.values()),
        }


def demo():
    """Demonstrate semantic memory."""
    print("=" * 60)
    print("BAEL Semantic Memory Demo")
    print("=" * 60)

    memory = SemanticMemory()

    # Build concept hierarchy
    print("\nBuilding knowledge base...")

    # Root concepts
    prog_lang = memory.add_concept(
        "Programming Language",
        ConceptType.ABSTRACT,
        definition="A formal language for expressing computations",
        properties={"domain": "computing"},
    )

    # Add languages
    python = memory.add_concept(
        "Python",
        ConceptType.ENTITY,
        definition="A high-level programming language",
        properties={"typing": "dynamic", "paradigm": "multi"},
        aliases=["Python3", "CPython"],
        parent=prog_lang.id,
    )

    javascript = memory.add_concept(
        "JavaScript",
        ConceptType.ENTITY,
        definition="A scripting language for the web",
        properties={"typing": "dynamic", "paradigm": "multi"},
        aliases=["JS", "ECMAScript"],
        parent=prog_lang.id,
    )

    # Add related concepts
    web_dev = memory.add_concept(
        "Web Development",
        ConceptType.PROCESS,
        definition="Building websites and web applications",
    )

    framework = memory.add_concept(
        "Framework",
        ConceptType.ABSTRACT,
        definition="A software framework providing abstractions",
    )

    django = memory.add_concept(
        "Django",
        ConceptType.ENTITY,
        definition="A Python web framework",
        parent=framework.id,
    )

    react = memory.add_concept(
        "React",
        ConceptType.ENTITY,
        definition="A JavaScript library for UIs",
        parent=framework.id,
    )

    # Add relations
    memory.add_relation(django.id, python.id, RelationType.RELATED_TO)
    memory.add_relation(react.id, javascript.id, RelationType.RELATED_TO)
    memory.add_relation(django.id, web_dev.id, RelationType.RELATED_TO)
    memory.add_relation(react.id, web_dev.id, RelationType.RELATED_TO)

    print(f"  Created {memory.stats['concepts_created']} concepts")
    print(f"  Created {memory.stats['relations_created']} relations")

    # Query
    print("\nQuerying knowledge...")

    py = memory.get_concept("Python", by_name=True)
    print(f"  Found Python: {py.definition}")

    # Get relations
    relations = memory.query_relations(python.id)
    print(f"\n  Python relations:")
    for concept, rel in relations:
        print(f"    --[{rel.relation_type.value}]--> {concept.name}")

    # Find path
    print("\n  Path from Django to JavaScript:")
    path = memory.find_path("Django", "JavaScript")
    if path:
        print(f"    {' '.join(path)}")

    # Inheritance
    print("\n  Ancestors of Django:")
    for ancestor in memory.get_ancestors(django.id):
        print(f"    - {ancestor.name}")

    # Inference
    print("\n  Inferring properties...")
    domain = memory.infer(python.id, "domain")
    print(f"    Python domain (inherited): {domain}")

    # Search
    print("\n  Searching for 'web':")
    results = memory.search("web")
    for concept in results:
        print(f"    - {concept.name}: {concept.definition[:40]}...")

    print(f"\nStats: {memory.get_stats()}")


if __name__ == "__main__":
    demo()
