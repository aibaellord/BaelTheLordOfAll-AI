"""
BAEL - Knowledge Graph
Advanced knowledge representation and reasoning.

Features:
- Entity extraction
- Relationship mapping
- Graph traversal
- Inference engine
- Semantic queries
- Visualization export
"""

import asyncio
import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.KnowledgeGraph")


# =============================================================================
# TYPES & ENUMS
# =============================================================================

class EntityType(Enum):
    """Types of entities."""
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    CONCEPT = "concept"
    TECHNOLOGY = "technology"
    EVENT = "event"
    DOCUMENT = "document"
    CODE = "code"
    TASK = "task"
    UNKNOWN = "unknown"


class RelationType(Enum):
    """Types of relationships."""
    # Hierarchical
    IS_A = "is_a"
    PART_OF = "part_of"
    CONTAINS = "contains"

    # Associative
    RELATED_TO = "related_to"
    SIMILAR_TO = "similar_to"
    DEPENDS_ON = "depends_on"

    # Temporal
    BEFORE = "before"
    AFTER = "after"
    DURING = "during"

    # Causal
    CAUSES = "causes"
    PREVENTS = "prevents"
    ENABLES = "enables"

    # Action
    USES = "uses"
    CREATES = "creates"
    MODIFIES = "modifies"

    # Attribution
    AUTHORED_BY = "authored_by"
    OWNED_BY = "owned_by"
    LOCATED_IN = "located_in"


@dataclass
class Entity:
    """A node in the knowledge graph."""
    id: str
    name: str
    entity_type: EntityType

    # Properties
    properties: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    confidence: float = 1.0
    source: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # Embedding for semantic search
    embedding: Optional[List[float]] = None


@dataclass
class Relationship:
    """An edge in the knowledge graph."""
    id: str
    source_id: str
    target_id: str
    relation_type: RelationType

    # Properties
    properties: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0

    # Metadata
    confidence: float = 1.0
    source: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    # Bidirectional flag
    bidirectional: bool = False


@dataclass
class GraphPath:
    """A path through the graph."""
    nodes: List[Entity]
    edges: List[Relationship]
    total_weight: float = 0.0

    def __len__(self) -> int:
        return len(self.nodes)


# =============================================================================
# KNOWLEDGE GRAPH
# =============================================================================

class KnowledgeGraph:
    """A knowledge graph for storing and reasoning over entities."""

    def __init__(self):
        self._entities: Dict[str, Entity] = {}
        self._relationships: Dict[str, Relationship] = {}

        # Indexes
        self._by_type: Dict[EntityType, Set[str]] = defaultdict(set)
        self._by_name: Dict[str, Set[str]] = defaultdict(set)
        self._outgoing: Dict[str, Set[str]] = defaultdict(set)  # entity -> relationships
        self._incoming: Dict[str, Set[str]] = defaultdict(set)  # entity -> relationships

        self._entity_counter = 0
        self._rel_counter = 0

    def add_entity(
        self,
        name: str,
        entity_type: EntityType,
        properties: Dict[str, Any] = None,
        confidence: float = 1.0,
        source: str = None
    ) -> Entity:
        """Add an entity to the graph."""
        entity_id = f"e_{self._entity_counter}"
        self._entity_counter += 1

        entity = Entity(
            id=entity_id,
            name=name,
            entity_type=entity_type,
            properties=properties or {},
            confidence=confidence,
            source=source
        )

        self._entities[entity_id] = entity
        self._by_type[entity_type].add(entity_id)
        self._by_name[name.lower()].add(entity_id)

        logger.debug(f"Added entity: {name} ({entity_type.value})")
        return entity

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType,
        properties: Dict[str, Any] = None,
        weight: float = 1.0,
        bidirectional: bool = False
    ) -> Optional[Relationship]:
        """Add a relationship to the graph."""
        if source_id not in self._entities or target_id not in self._entities:
            logger.warning(f"Invalid entity IDs for relationship")
            return None

        rel_id = f"r_{self._rel_counter}"
        self._rel_counter += 1

        relationship = Relationship(
            id=rel_id,
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            properties=properties or {},
            weight=weight,
            bidirectional=bidirectional
        )

        self._relationships[rel_id] = relationship
        self._outgoing[source_id].add(rel_id)
        self._incoming[target_id].add(rel_id)

        if bidirectional:
            self._incoming[source_id].add(rel_id)
            self._outgoing[target_id].add(rel_id)

        source = self._entities[source_id]
        target = self._entities[target_id]
        logger.debug(f"Added relationship: {source.name} -{relation_type.value}-> {target.name}")

        return relationship

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get an entity by ID."""
        return self._entities.get(entity_id)

    def find_entities(
        self,
        name: str = None,
        entity_type: EntityType = None,
        properties: Dict[str, Any] = None
    ) -> List[Entity]:
        """Find entities matching criteria."""
        candidates = set(self._entities.keys())

        # Filter by name
        if name:
            name_matches = self._by_name.get(name.lower(), set())
            # Also try partial match
            for n, ids in self._by_name.items():
                if name.lower() in n:
                    name_matches.update(ids)
            candidates &= name_matches

        # Filter by type
        if entity_type:
            type_matches = self._by_type.get(entity_type, set())
            candidates &= type_matches

        # Filter by properties
        if properties:
            prop_matches = set()
            for eid in candidates:
                entity = self._entities[eid]
                if all(entity.properties.get(k) == v for k, v in properties.items()):
                    prop_matches.add(eid)
            candidates &= prop_matches

        return [self._entities[eid] for eid in candidates]

    def get_neighbors(
        self,
        entity_id: str,
        relation_type: RelationType = None,
        direction: str = "both"
    ) -> List[Tuple[Entity, Relationship]]:
        """Get neighboring entities."""
        neighbors = []

        # Outgoing relationships
        if direction in ["both", "out"]:
            for rel_id in self._outgoing.get(entity_id, set()):
                rel = self._relationships[rel_id]
                if relation_type and rel.relation_type != relation_type:
                    continue
                target = self._entities.get(rel.target_id)
                if target:
                    neighbors.append((target, rel))

        # Incoming relationships
        if direction in ["both", "in"]:
            for rel_id in self._incoming.get(entity_id, set()):
                rel = self._relationships[rel_id]
                if relation_type and rel.relation_type != relation_type:
                    continue
                source = self._entities.get(rel.source_id)
                if source and source.id != entity_id:
                    neighbors.append((source, rel))

        return neighbors

    def find_path(
        self,
        start_id: str,
        end_id: str,
        max_depth: int = 5
    ) -> Optional[GraphPath]:
        """Find shortest path between entities."""
        if start_id not in self._entities or end_id not in self._entities:
            return None

        # BFS for shortest path
        visited = {start_id}
        queue = [(start_id, [self._entities[start_id]], [])]

        while queue:
            current_id, path_nodes, path_edges = queue.pop(0)

            if len(path_nodes) > max_depth:
                continue

            if current_id == end_id:
                return GraphPath(
                    nodes=path_nodes,
                    edges=path_edges,
                    total_weight=sum(e.weight for e in path_edges)
                )

            for neighbor, rel in self.get_neighbors(current_id):
                if neighbor.id not in visited:
                    visited.add(neighbor.id)
                    queue.append((
                        neighbor.id,
                        path_nodes + [neighbor],
                        path_edges + [rel]
                    ))

        return None

    def get_subgraph(
        self,
        center_id: str,
        depth: int = 2
    ) -> 'KnowledgeGraph':
        """Extract a subgraph around an entity."""
        subgraph = KnowledgeGraph()

        if center_id not in self._entities:
            return subgraph

        # BFS to collect entities
        visited = {center_id}
        queue = [(center_id, 0)]

        while queue:
            current_id, current_depth = queue.pop(0)

            entity = self._entities[current_id]
            subgraph._entities[entity.id] = entity
            subgraph._by_type[entity.entity_type].add(entity.id)
            subgraph._by_name[entity.name.lower()].add(entity.id)

            if current_depth >= depth:
                continue

            for neighbor, rel in self.get_neighbors(current_id):
                # Add relationship
                subgraph._relationships[rel.id] = rel
                subgraph._outgoing[rel.source_id].add(rel.id)
                subgraph._incoming[rel.target_id].add(rel.id)

                if neighbor.id not in visited:
                    visited.add(neighbor.id)
                    queue.append((neighbor.id, current_depth + 1))

        return subgraph


# =============================================================================
# ENTITY EXTRACTOR
# =============================================================================

class EntityExtractor:
    """Extracts entities from text."""

    def __init__(self, model_router=None):
        self.model_router = model_router

        # Simple patterns for rule-based extraction
        self.patterns = {
            EntityType.PERSON: [
                r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b',  # Names
            ],
            EntityType.ORGANIZATION: [
                r'\b([A-Z][a-z]+ (?:Inc|Corp|LLC|Ltd|Company)\.?)\b',
            ],
            EntityType.TECHNOLOGY: [
                r'\b(Python|JavaScript|Java|TypeScript|React|Node\.js|Docker)\b',
            ],
            EntityType.LOCATION: [
                r'\b(New York|San Francisco|London|Tokyo|Berlin)\b',
            ]
        }

    async def extract(self, text: str) -> List[Entity]:
        """Extract entities from text."""
        if self.model_router:
            return await self._ai_extract(text)
        return self._rule_extract(text)

    async def _ai_extract(self, text: str) -> List[Entity]:
        """Extract entities using AI."""
        prompt = f"""Extract entities from this text. For each entity provide:
- Name
- Type (person/organization/location/concept/technology/event)
- Confidence (0-1)

Text: {text}

Format as:
ENTITY: [name]
TYPE: [type]
CONFIDENCE: [confidence]

---"""

        try:
            response = await self.model_router.generate(prompt)
            return self._parse_entities(response)
        except Exception as e:
            logger.error(f"AI extraction failed: {e}")
            return self._rule_extract(text)

    def _rule_extract(self, text: str) -> List[Entity]:
        """Extract entities using rules."""
        entities = []
        seen = set()

        for entity_type, patterns in self.patterns.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text):
                    name = match.group(1)
                    if name.lower() not in seen:
                        seen.add(name.lower())
                        entities.append(Entity(
                            id=f"extracted_{len(entities)}",
                            name=name,
                            entity_type=entity_type,
                            confidence=0.8
                        ))

        return entities

    def _parse_entities(self, response: str) -> List[Entity]:
        """Parse entities from AI response."""
        entities = []
        current = {}

        for line in response.split('\n'):
            line = line.strip()

            if line.startswith('ENTITY:'):
                if current:
                    entities.append(self._create_entity(current))
                current = {'name': line[7:].strip()}

            elif line.startswith('TYPE:'):
                current['type'] = line[5:].strip()

            elif line.startswith('CONFIDENCE:'):
                try:
                    current['confidence'] = float(line[11:].strip())
                except:
                    current['confidence'] = 0.8

        if current:
            entities.append(self._create_entity(current))

        return entities

    def _create_entity(self, data: Dict) -> Entity:
        """Create entity from parsed data."""
        type_mapping = {
            'person': EntityType.PERSON,
            'organization': EntityType.ORGANIZATION,
            'location': EntityType.LOCATION,
            'concept': EntityType.CONCEPT,
            'technology': EntityType.TECHNOLOGY,
            'event': EntityType.EVENT
        }

        return Entity(
            id=f"extracted_{id(data)}",
            name=data.get('name', 'Unknown'),
            entity_type=type_mapping.get(data.get('type', '').lower(), EntityType.UNKNOWN),
            confidence=data.get('confidence', 0.8)
        )


# =============================================================================
# INFERENCE ENGINE
# =============================================================================

class InferenceEngine:
    """Inference over knowledge graph."""

    def __init__(self, graph: KnowledgeGraph):
        self.graph = graph

        # Inference rules
        self.rules: List[Callable[[KnowledgeGraph], List[Relationship]]] = [
            self._rule_transitivity,
            self._rule_symmetry,
            self._rule_inheritance,
        ]

    def infer(self) -> List[Relationship]:
        """Run inference and return new relationships."""
        new_relationships = []

        for rule in self.rules:
            new_rels = rule(self.graph)
            new_relationships.extend(new_rels)

        return new_relationships

    def _rule_transitivity(self, graph: KnowledgeGraph) -> List[Relationship]:
        """Infer transitive relationships (A->B, B->C => A->C)."""
        new_rels = []
        transitive_types = {RelationType.IS_A, RelationType.PART_OF}

        for rel in graph._relationships.values():
            if rel.relation_type not in transitive_types:
                continue

            # Find relationships from target
            target_rels = graph.get_neighbors(rel.target_id, rel.relation_type, "out")

            for entity, second_rel in target_rels:
                # Check if relationship already exists
                existing = graph.get_neighbors(rel.source_id, rel.relation_type, "out")
                if not any(e.id == entity.id for e, _ in existing):
                    # Create inferred relationship
                    new_rel = Relationship(
                        id=f"inferred_{len(new_rels)}",
                        source_id=rel.source_id,
                        target_id=entity.id,
                        relation_type=rel.relation_type,
                        confidence=rel.confidence * second_rel.confidence * 0.9,
                        properties={"inferred": True, "rule": "transitivity"}
                    )
                    new_rels.append(new_rel)

        return new_rels

    def _rule_symmetry(self, graph: KnowledgeGraph) -> List[Relationship]:
        """Infer symmetric relationships (A->B => B->A)."""
        new_rels = []
        symmetric_types = {RelationType.RELATED_TO, RelationType.SIMILAR_TO}

        for rel in graph._relationships.values():
            if rel.relation_type not in symmetric_types:
                continue

            if rel.bidirectional:
                continue

            # Check if reverse exists
            existing = graph.get_neighbors(rel.target_id, rel.relation_type, "out")
            if not any(e.id == rel.source_id for e, _ in existing):
                new_rel = Relationship(
                    id=f"inferred_{len(new_rels)}",
                    source_id=rel.target_id,
                    target_id=rel.source_id,
                    relation_type=rel.relation_type,
                    confidence=rel.confidence * 0.95,
                    properties={"inferred": True, "rule": "symmetry"}
                )
                new_rels.append(new_rel)

        return new_rels

    def _rule_inheritance(self, graph: KnowledgeGraph) -> List[Relationship]:
        """Infer inherited properties (A is_a B, B has X => A has X)."""
        new_rels = []

        # Find IS_A relationships
        for rel in graph._relationships.values():
            if rel.relation_type != RelationType.IS_A:
                continue

            # Get parent's relationships (except IS_A)
            parent_rels = graph.get_neighbors(rel.target_id, direction="out")

            for entity, parent_rel in parent_rels:
                if parent_rel.relation_type == RelationType.IS_A:
                    continue

                # Check if child already has this relationship
                child_rels = graph.get_neighbors(rel.source_id, parent_rel.relation_type, "out")
                if not any(e.id == entity.id for e, _ in child_rels):
                    new_rel = Relationship(
                        id=f"inferred_{len(new_rels)}",
                        source_id=rel.source_id,
                        target_id=entity.id,
                        relation_type=parent_rel.relation_type,
                        confidence=rel.confidence * parent_rel.confidence * 0.8,
                        properties={"inferred": True, "rule": "inheritance"}
                    )
                    new_rels.append(new_rel)

        return new_rels


# =============================================================================
# GRAPH VISUALIZER
# =============================================================================

class GraphVisualizer:
    """Export graph for visualization."""

    @staticmethod
    def to_json(graph: KnowledgeGraph) -> Dict[str, Any]:
        """Export to JSON format."""
        nodes = [
            {
                "id": e.id,
                "label": e.name,
                "type": e.entity_type.value,
                "properties": e.properties,
                "confidence": e.confidence
            }
            for e in graph._entities.values()
        ]

        edges = [
            {
                "id": r.id,
                "source": r.source_id,
                "target": r.target_id,
                "label": r.relation_type.value,
                "weight": r.weight,
                "properties": r.properties
            }
            for r in graph._relationships.values()
        ]

        return {"nodes": nodes, "edges": edges}

    @staticmethod
    def to_cytoscape(graph: KnowledgeGraph) -> Dict[str, Any]:
        """Export to Cytoscape.js format."""
        elements = []

        for entity in graph._entities.values():
            elements.append({
                "data": {
                    "id": entity.id,
                    "label": entity.name,
                    "type": entity.entity_type.value
                },
                "classes": entity.entity_type.value
            })

        for rel in graph._relationships.values():
            elements.append({
                "data": {
                    "id": rel.id,
                    "source": rel.source_id,
                    "target": rel.target_id,
                    "label": rel.relation_type.value
                }
            })

        return {"elements": elements}

    @staticmethod
    def to_mermaid(graph: KnowledgeGraph) -> str:
        """Export to Mermaid diagram format."""
        lines = ["graph TD"]

        for entity in graph._entities.values():
            label = entity.name.replace('"', "'")
            lines.append(f'    {entity.id}["{label}"]')

        for rel in graph._relationships.values():
            label = rel.relation_type.value.replace("_", " ")
            lines.append(f'    {rel.source_id} -->|{label}| {rel.target_id}')

        return "\n".join(lines)


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Test knowledge graph."""
    graph = KnowledgeGraph()

    # Add entities
    python = graph.add_entity("Python", EntityType.TECHNOLOGY)
    fastapi = graph.add_entity("FastAPI", EntityType.TECHNOLOGY)
    flask = graph.add_entity("Flask", EntityType.TECHNOLOGY)
    web_framework = graph.add_entity("Web Framework", EntityType.CONCEPT)
    programming_lang = graph.add_entity("Programming Language", EntityType.CONCEPT)

    # Add relationships
    graph.add_relationship(python.id, programming_lang.id, RelationType.IS_A)
    graph.add_relationship(fastapi.id, web_framework.id, RelationType.IS_A)
    graph.add_relationship(flask.id, web_framework.id, RelationType.IS_A)
    graph.add_relationship(fastapi.id, python.id, RelationType.USES)
    graph.add_relationship(flask.id, python.id, RelationType.USES)
    graph.add_relationship(fastapi.id, flask.id, RelationType.SIMILAR_TO)

    print("Knowledge Graph:")
    print(f"  Entities: {len(graph._entities)}")
    print(f"  Relationships: {len(graph._relationships)}")

    # Find path
    path = graph.find_path(fastapi.id, programming_lang.id)
    if path:
        print(f"\nPath from FastAPI to Programming Language:")
        for i, node in enumerate(path.nodes):
            print(f"  {i+1}. {node.name}")

    # Run inference
    engine = InferenceEngine(graph)
    new_rels = engine.infer()
    print(f"\nInferred {len(new_rels)} new relationships")

    # Export
    mermaid = GraphVisualizer.to_mermaid(graph)
    print(f"\nMermaid diagram:")
    print(mermaid)


if __name__ == "__main__":
    asyncio.run(main())
