"""
BAEL Knowledge Fusion Engine
============================

Ultimate knowledge synthesis, integration, and reasoning.

"All knowledge is one. The fragments must be unified." — Ba'el
"""

import asyncio
import hashlib
import json
import math
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import (
    Any, Callable, Dict, List, Optional, Set, Tuple, Union,
    TypeVar, Generic, AsyncIterator
)
from collections import defaultdict
import heapq


class KnowledgeType(Enum):
    """Types of knowledge."""
    FACTUAL = "factual"              # Declarative facts
    PROCEDURAL = "procedural"        # How-to knowledge
    CONCEPTUAL = "conceptual"        # Abstract concepts
    RELATIONAL = "relational"        # Relationships between entities
    TEMPORAL = "temporal"            # Time-based knowledge
    CAUSAL = "causal"                # Cause-effect relationships
    SPATIAL = "spatial"              # Location-based knowledge
    EXPERIENTIAL = "experiential"    # Learned from experience
    HYPOTHETICAL = "hypothetical"    # Uncertain/speculative
    META = "meta"                    # Knowledge about knowledge


class ConfidenceLevel(Enum):
    """Confidence levels for knowledge."""
    CERTAIN = 1.0
    HIGH = 0.85
    MEDIUM = 0.65
    LOW = 0.4
    UNCERTAIN = 0.2
    SPECULATIVE = 0.1


class ReasoningMode(Enum):
    """Reasoning strategies."""
    DEDUCTIVE = "deductive"          # General to specific
    INDUCTIVE = "inductive"          # Specific to general
    ABDUCTIVE = "abductive"          # Best explanation
    ANALOGICAL = "analogical"        # By analogy
    CAUSAL = "causal"                # Cause-effect
    COUNTERFACTUAL = "counterfactual"  # What-if
    PROBABILISTIC = "probabilistic"  # Statistical
    FUZZY = "fuzzy"                  # Approximate reasoning
    TEMPORAL = "temporal"            # Over time
    SPATIAL = "spatial"              # Spatial relationships


class FusionStrategy(Enum):
    """Knowledge fusion strategies."""
    UNION = "union"                  # Combine all
    INTERSECTION = "intersection"    # Common only
    WEIGHTED = "weighted"            # By confidence
    HIERARCHICAL = "hierarchical"    # Priority-based
    CONSENSUS = "consensus"          # Agreement-based
    ADAPTIVE = "adaptive"            # Context-dependent


@dataclass
class Entity:
    """A knowledge entity."""
    id: str
    name: str
    entity_type: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    embeddings: Optional[List[float]] = None
    confidence: float = 1.0
    source: str = "system"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.entity_type,
            "attributes": self.attributes,
            "confidence": self.confidence,
            "source": self.source
        }


@dataclass
class Relation:
    """A relationship between entities."""
    id: str
    source_id: str
    target_id: str
    relation_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    confidence: float = 1.0
    bidirectional: bool = False
    temporal: Optional[Tuple[datetime, datetime]] = None

    def reverse(self) -> "Relation":
        """Create reverse relation."""
        return Relation(
            id=f"{self.id}_reverse",
            source_id=self.target_id,
            target_id=self.source_id,
            relation_type=f"inverse_{self.relation_type}",
            properties=self.properties.copy(),
            weight=self.weight,
            confidence=self.confidence,
            bidirectional=self.bidirectional,
            temporal=self.temporal
        )


@dataclass
class KnowledgeFragment:
    """A piece of knowledge."""
    id: str
    content: str
    knowledge_type: KnowledgeType
    entities: List[str] = field(default_factory=list)
    relations: List[str] = field(default_factory=list)
    confidence: float = 1.0
    source: str = "system"
    context: Dict[str, Any] = field(default_factory=dict)
    embeddings: Optional[List[float]] = None
    created_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    relevance_score: float = 0.0


@dataclass
class Inference:
    """An inferred piece of knowledge."""
    id: str
    conclusion: str
    premises: List[str]
    reasoning_mode: ReasoningMode
    confidence: float
    explanation: str
    supporting_evidence: List[str] = field(default_factory=list)
    counter_evidence: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Query:
    """A knowledge query."""
    question: str
    context: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    reasoning_modes: List[ReasoningMode] = field(default_factory=list)
    max_hops: int = 3
    min_confidence: float = 0.5
    max_results: int = 10


@dataclass
class QueryResult:
    """Result of a knowledge query."""
    query: Query
    answers: List[Dict[str, Any]]
    inferences: List[Inference]
    confidence: float
    reasoning_path: List[str]
    sources: List[str]
    processing_time_ms: float


class KnowledgeGraph:
    """Advanced knowledge graph with reasoning."""

    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.relations: Dict[str, Relation] = {}
        self.fragments: Dict[str, KnowledgeFragment] = {}
        self.adjacency: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_adjacency: Dict[str, Set[str]] = defaultdict(set)
        self.type_index: Dict[str, Set[str]] = defaultdict(set)
        self.relation_type_index: Dict[str, Set[str]] = defaultdict(set)

    async def add_entity(self, entity: Entity) -> None:
        """Add or update an entity."""
        self.entities[entity.id] = entity
        self.type_index[entity.entity_type].add(entity.id)

    async def add_relation(self, relation: Relation) -> None:
        """Add a relationship."""
        self.relations[relation.id] = relation
        self.adjacency[relation.source_id].add(relation.target_id)
        self.reverse_adjacency[relation.target_id].add(relation.source_id)
        self.relation_type_index[relation.relation_type].add(relation.id)

        if relation.bidirectional:
            reverse = relation.reverse()
            self.relations[reverse.id] = reverse
            self.adjacency[reverse.source_id].add(reverse.target_id)
            self.reverse_adjacency[reverse.target_id].add(reverse.source_id)

    async def add_fragment(self, fragment: KnowledgeFragment) -> None:
        """Add a knowledge fragment."""
        self.fragments[fragment.id] = fragment

    async def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID."""
        entity = self.entities.get(entity_id)
        if entity:
            entity.access_count += 1
        return entity

    async def get_neighbors(
        self,
        entity_id: str,
        relation_types: Optional[List[str]] = None,
        direction: str = "outgoing"
    ) -> List[Tuple[Entity, Relation]]:
        """Get neighboring entities."""
        neighbors = []

        if direction in ("outgoing", "both"):
            for target_id in self.adjacency.get(entity_id, set()):
                for rel_id, rel in self.relations.items():
                    if rel.source_id == entity_id and rel.target_id == target_id:
                        if relation_types is None or rel.relation_type in relation_types:
                            target = self.entities.get(target_id)
                            if target:
                                neighbors.append((target, rel))

        if direction in ("incoming", "both"):
            for source_id in self.reverse_adjacency.get(entity_id, set()):
                for rel_id, rel in self.relations.items():
                    if rel.target_id == entity_id and rel.source_id == source_id:
                        if relation_types is None or rel.relation_type in relation_types:
                            source = self.entities.get(source_id)
                            if source:
                                neighbors.append((source, rel))

        return neighbors

    async def find_paths(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5,
        relation_types: Optional[List[str]] = None
    ) -> List[List[Tuple[str, str, str]]]:
        """Find all paths between two entities."""
        paths = []
        visited = set()

        async def dfs(
            current: str,
            path: List[Tuple[str, str, str]],
            depth: int
        ):
            if depth > max_depth:
                return

            if current == target_id:
                paths.append(path.copy())
                return

            if current in visited:
                return

            visited.add(current)

            for neighbor_id in self.adjacency.get(current, set()):
                for rel_id, rel in self.relations.items():
                    if rel.source_id == current and rel.target_id == neighbor_id:
                        if relation_types is None or rel.relation_type in relation_types:
                            path.append((current, rel.relation_type, neighbor_id))
                            await dfs(neighbor_id, path, depth + 1)
                            path.pop()

            visited.remove(current)

        await dfs(source_id, [], 0)
        return paths

    async def subgraph(
        self,
        entity_ids: Set[str],
        include_neighbors: bool = True
    ) -> "KnowledgeGraph":
        """Extract a subgraph."""
        subgraph = KnowledgeGraph()

        all_ids = set(entity_ids)

        if include_neighbors:
            for eid in entity_ids:
                all_ids.update(self.adjacency.get(eid, set()))
                all_ids.update(self.reverse_adjacency.get(eid, set()))

        for eid in all_ids:
            if eid in self.entities:
                await subgraph.add_entity(self.entities[eid])

        for rel in self.relations.values():
            if rel.source_id in all_ids and rel.target_id in all_ids:
                await subgraph.add_relation(rel)

        return subgraph

    def get_statistics(self) -> Dict[str, Any]:
        """Get graph statistics."""
        return {
            "entity_count": len(self.entities),
            "relation_count": len(self.relations),
            "fragment_count": len(self.fragments),
            "entity_types": len(self.type_index),
            "relation_types": len(self.relation_type_index),
            "avg_degree": sum(len(adj) for adj in self.adjacency.values()) / max(len(self.adjacency), 1)
        }


class ReasoningEngine:
    """Multi-strategy reasoning engine."""

    def __init__(self, knowledge_graph: KnowledgeGraph):
        self.kg = knowledge_graph
        self.inference_cache: Dict[str, Inference] = {}
        self.reasoning_stats: Dict[str, int] = defaultdict(int)

    async def reason(
        self,
        query: Query,
        mode: Optional[ReasoningMode] = None
    ) -> List[Inference]:
        """Perform reasoning over the knowledge graph."""
        modes = [mode] if mode else (query.reasoning_modes or [ReasoningMode.DEDUCTIVE])
        inferences = []

        for reasoning_mode in modes:
            self.reasoning_stats[reasoning_mode.value] += 1

            if reasoning_mode == ReasoningMode.DEDUCTIVE:
                infs = await self._deductive_reasoning(query)
            elif reasoning_mode == ReasoningMode.INDUCTIVE:
                infs = await self._inductive_reasoning(query)
            elif reasoning_mode == ReasoningMode.ABDUCTIVE:
                infs = await self._abductive_reasoning(query)
            elif reasoning_mode == ReasoningMode.ANALOGICAL:
                infs = await self._analogical_reasoning(query)
            elif reasoning_mode == ReasoningMode.CAUSAL:
                infs = await self._causal_reasoning(query)
            elif reasoning_mode == ReasoningMode.PROBABILISTIC:
                infs = await self._probabilistic_reasoning(query)
            else:
                infs = await self._deductive_reasoning(query)

            inferences.extend(infs)

        # Deduplicate and rank
        seen = set()
        unique_inferences = []
        for inf in sorted(inferences, key=lambda x: -x.confidence):
            key = (inf.conclusion, tuple(inf.premises))
            if key not in seen:
                seen.add(key)
                unique_inferences.append(inf)

        return unique_inferences[:query.max_results]

    async def _deductive_reasoning(self, query: Query) -> List[Inference]:
        """Apply general rules to specific cases."""
        inferences = []

        # Example: If A is-a B and B has-property P, then A has-property P
        for entity_id, entity in self.kg.entities.items():
            # Find is-a relationships
            is_a_relations = [
                rel for rel in self.kg.relations.values()
                if rel.source_id == entity_id and rel.relation_type == "is_a"
            ]

            for is_a in is_a_relations:
                parent = self.kg.entities.get(is_a.target_id)
                if parent and parent.attributes:
                    for attr, value in parent.attributes.items():
                        if attr not in entity.attributes:
                            inf = Inference(
                                id=f"ded_{entity_id}_{attr}",
                                conclusion=f"{entity.name} has {attr} = {value}",
                                premises=[
                                    f"{entity.name} is-a {parent.name}",
                                    f"{parent.name} has {attr} = {value}"
                                ],
                                reasoning_mode=ReasoningMode.DEDUCTIVE,
                                confidence=is_a.confidence * 0.9,
                                explanation=f"Inherited from parent type {parent.name}"
                            )
                            inferences.append(inf)

        return inferences

    async def _inductive_reasoning(self, query: Query) -> List[Inference]:
        """Generalize from specific observations."""
        inferences = []

        # Find common patterns in similar entities
        type_groups: Dict[str, List[Entity]] = defaultdict(list)
        for entity in self.kg.entities.values():
            type_groups[entity.entity_type].append(entity)

        for entity_type, entities in type_groups.items():
            if len(entities) < 3:
                continue

            # Find common attributes
            common_attrs: Dict[str, Dict[Any, int]] = defaultdict(lambda: defaultdict(int))
            for entity in entities:
                for attr, value in entity.attributes.items():
                    common_attrs[attr][str(value)] += 1

            for attr, value_counts in common_attrs.items():
                total = sum(value_counts.values())
                for value, count in value_counts.items():
                    ratio = count / total
                    if ratio >= 0.8:  # 80% threshold
                        inf = Inference(
                            id=f"ind_{entity_type}_{attr}",
                            conclusion=f"Most {entity_type} entities have {attr} = {value}",
                            premises=[f"Observed in {count}/{total} instances"],
                            reasoning_mode=ReasoningMode.INDUCTIVE,
                            confidence=ratio,
                            explanation=f"Pattern detected across {count} entities"
                        )
                        inferences.append(inf)

        return inferences

    async def _abductive_reasoning(self, query: Query) -> List[Inference]:
        """Find the best explanation for observations."""
        inferences = []

        # Look for explanatory patterns
        for relation in self.kg.relations.values():
            if relation.relation_type == "causes":
                source = self.kg.entities.get(relation.source_id)
                target = self.kg.entities.get(relation.target_id)

                if source and target:
                    inf = Inference(
                        id=f"abd_{relation.id}",
                        conclusion=f"{source.name} might explain {target.name}",
                        premises=[f"{source.name} causes {target.name}"],
                        reasoning_mode=ReasoningMode.ABDUCTIVE,
                        confidence=relation.confidence * 0.8,
                        explanation="Causal relationship suggests explanation"
                    )
                    inferences.append(inf)

        return inferences

    async def _analogical_reasoning(self, query: Query) -> List[Inference]:
        """Reason by analogy between similar entities."""
        inferences = []

        # Find similar entities and transfer properties
        entities_list = list(self.kg.entities.values())

        for i, entity1 in enumerate(entities_list):
            for entity2 in entities_list[i+1:]:
                if entity1.entity_type == entity2.entity_type:
                    # Same type - check for structural similarity
                    common = set(entity1.attributes.keys()) & set(entity2.attributes.keys())

                    if len(common) >= 2:
                        # Transfer missing attributes
                        for attr in entity1.attributes:
                            if attr not in entity2.attributes:
                                inf = Inference(
                                    id=f"ana_{entity2.id}_{attr}",
                                    conclusion=f"{entity2.name} might have {attr} similar to {entity1.name}",
                                    premises=[
                                        f"{entity1.name} and {entity2.name} share {len(common)} attributes",
                                        f"{entity1.name} has {attr}"
                                    ],
                                    reasoning_mode=ReasoningMode.ANALOGICAL,
                                    confidence=min(len(common) / 5, 0.8),
                                    explanation=f"Analogical transfer from similar entity"
                                )
                                inferences.append(inf)

        return inferences

    async def _causal_reasoning(self, query: Query) -> List[Inference]:
        """Reason about cause-effect relationships."""
        inferences = []

        # Build causal chains
        causal_rels = [
            rel for rel in self.kg.relations.values()
            if rel.relation_type in ("causes", "enables", "prevents", "leads_to")
        ]

        for rel in causal_rels:
            source = self.kg.entities.get(rel.source_id)
            target = self.kg.entities.get(rel.target_id)

            if source and target:
                # Check for transitive causation
                for rel2 in causal_rels:
                    if rel2.source_id == rel.target_id:
                        final_target = self.kg.entities.get(rel2.target_id)
                        if final_target:
                            inf = Inference(
                                id=f"caus_{source.id}_{final_target.id}",
                                conclusion=f"{source.name} indirectly {rel.relation_type} {final_target.name}",
                                premises=[
                                    f"{source.name} {rel.relation_type} {target.name}",
                                    f"{target.name} {rel2.relation_type} {final_target.name}"
                                ],
                                reasoning_mode=ReasoningMode.CAUSAL,
                                confidence=rel.confidence * rel2.confidence,
                                explanation="Transitive causal chain"
                            )
                            inferences.append(inf)

        return inferences

    async def _probabilistic_reasoning(self, query: Query) -> List[Inference]:
        """Reason with probabilities and uncertainty."""
        inferences = []

        # Simple Bayesian-style reasoning
        for entity in self.kg.entities.values():
            # Calculate overall confidence based on evidence
            supporting = 0
            total = 0

            for rel in self.kg.relations.values():
                if rel.target_id == entity.id:
                    total += 1
                    supporting += rel.confidence

            if total > 0:
                posterior = supporting / total
                inf = Inference(
                    id=f"prob_{entity.id}",
                    conclusion=f"Confidence in {entity.name} = {posterior:.2f}",
                    premises=[f"{total} supporting relationships"],
                    reasoning_mode=ReasoningMode.PROBABILISTIC,
                    confidence=posterior,
                    explanation=f"Aggregated from {total} evidence sources"
                )
                inferences.append(inf)

        return inferences

    def get_reasoning_stats(self) -> Dict[str, int]:
        """Get reasoning usage statistics."""
        return dict(self.reasoning_stats)


class KnowledgeFusion:
    """Fuses knowledge from multiple sources."""

    def __init__(self):
        self.sources: Dict[str, KnowledgeGraph] = {}
        self.fusion_history: List[Dict[str, Any]] = []

    async def add_source(self, name: str, graph: KnowledgeGraph) -> None:
        """Register a knowledge source."""
        self.sources[name] = graph

    async def fuse(
        self,
        strategy: FusionStrategy = FusionStrategy.WEIGHTED,
        sources: Optional[List[str]] = None
    ) -> KnowledgeGraph:
        """Fuse knowledge from multiple sources."""
        target_sources = sources or list(self.sources.keys())
        graphs = [self.sources[s] for s in target_sources if s in self.sources]

        if not graphs:
            return KnowledgeGraph()

        if strategy == FusionStrategy.UNION:
            return await self._union_fusion(graphs)
        elif strategy == FusionStrategy.INTERSECTION:
            return await self._intersection_fusion(graphs)
        elif strategy == FusionStrategy.WEIGHTED:
            return await self._weighted_fusion(graphs)
        elif strategy == FusionStrategy.HIERARCHICAL:
            return await self._hierarchical_fusion(graphs, target_sources)
        elif strategy == FusionStrategy.CONSENSUS:
            return await self._consensus_fusion(graphs)
        else:
            return await self._weighted_fusion(graphs)

    async def _union_fusion(self, graphs: List[KnowledgeGraph]) -> KnowledgeGraph:
        """Combine all knowledge."""
        result = KnowledgeGraph()

        for graph in graphs:
            for entity in graph.entities.values():
                if entity.id not in result.entities:
                    await result.add_entity(entity)
                else:
                    # Merge attributes
                    existing = result.entities[entity.id]
                    existing.attributes.update(entity.attributes)
                    existing.confidence = max(existing.confidence, entity.confidence)

            for relation in graph.relations.values():
                if relation.id not in result.relations:
                    await result.add_relation(relation)

            for fragment in graph.fragments.values():
                if fragment.id not in result.fragments:
                    await result.add_fragment(fragment)

        return result

    async def _intersection_fusion(self, graphs: List[KnowledgeGraph]) -> KnowledgeGraph:
        """Keep only common knowledge."""
        if not graphs:
            return KnowledgeGraph()

        result = KnowledgeGraph()

        # Find common entities
        common_entities = set(graphs[0].entities.keys())
        for graph in graphs[1:]:
            common_entities &= set(graph.entities.keys())

        for eid in common_entities:
            # Average confidence
            entities = [g.entities[eid] for g in graphs]
            merged = entities[0]
            merged.confidence = sum(e.confidence for e in entities) / len(entities)
            await result.add_entity(merged)

        # Find common relations
        common_relations = set(graphs[0].relations.keys())
        for graph in graphs[1:]:
            common_relations &= set(graph.relations.keys())

        for rid in common_relations:
            relations = [g.relations[rid] for g in graphs]
            merged = relations[0]
            merged.confidence = sum(r.confidence for r in relations) / len(relations)
            await result.add_relation(merged)

        return result

    async def _weighted_fusion(self, graphs: List[KnowledgeGraph]) -> KnowledgeGraph:
        """Fuse with confidence weighting."""
        result = KnowledgeGraph()
        entity_weights: Dict[str, List[Tuple[Entity, float]]] = defaultdict(list)
        relation_weights: Dict[str, List[Tuple[Relation, float]]] = defaultdict(list)

        for i, graph in enumerate(graphs):
            source_weight = 1.0 / (i + 1)  # Priority to earlier sources

            for entity in graph.entities.values():
                entity_weights[entity.id].append((entity, source_weight * entity.confidence))

            for relation in graph.relations.values():
                relation_weights[relation.id].append((relation, source_weight * relation.confidence))

        # Merge entities with weighted confidence
        for eid, weighted in entity_weights.items():
            best = max(weighted, key=lambda x: x[1])
            entity = best[0]
            entity.confidence = sum(w for _, w in weighted) / len(weighted)
            await result.add_entity(entity)

        # Merge relations
        for rid, weighted in relation_weights.items():
            best = max(weighted, key=lambda x: x[1])
            relation = best[0]
            relation.confidence = sum(w for _, w in weighted) / len(weighted)
            await result.add_relation(relation)

        return result

    async def _hierarchical_fusion(
        self,
        graphs: List[KnowledgeGraph],
        source_names: List[str]
    ) -> KnowledgeGraph:
        """Priority-based fusion."""
        result = KnowledgeGraph()

        # Process in order of priority (first = highest)
        for graph in graphs:
            for entity in graph.entities.values():
                if entity.id not in result.entities:
                    await result.add_entity(entity)

            for relation in graph.relations.values():
                if relation.id not in result.relations:
                    await result.add_relation(relation)

        return result

    async def _consensus_fusion(self, graphs: List[KnowledgeGraph]) -> KnowledgeGraph:
        """Keep knowledge with agreement."""
        if len(graphs) < 2:
            return graphs[0] if graphs else KnowledgeGraph()

        result = KnowledgeGraph()
        threshold = len(graphs) / 2  # Majority

        # Count entity occurrences
        entity_counts: Dict[str, int] = defaultdict(int)
        for graph in graphs:
            for eid in graph.entities:
                entity_counts[eid] += 1

        # Keep entities with consensus
        for eid, count in entity_counts.items():
            if count >= threshold:
                # Find best version
                entities = [g.entities[eid] for g in graphs if eid in g.entities]
                best = max(entities, key=lambda e: e.confidence)
                best.confidence *= (count / len(graphs))
                await result.add_entity(best)

        # Count relation occurrences
        relation_counts: Dict[str, int] = defaultdict(int)
        for graph in graphs:
            for rid in graph.relations:
                relation_counts[rid] += 1

        for rid, count in relation_counts.items():
            if count >= threshold:
                relations = [g.relations[rid] for g in graphs if rid in g.relations]
                best = max(relations, key=lambda r: r.confidence)
                best.confidence *= (count / len(graphs))
                await result.add_relation(best)

        return result


class KnowledgeFusionEngine:
    """
    The ultimate knowledge fusion engine.

    Combines knowledge graphs, reasoning, and fusion strategies
    for comprehensive intelligence.
    """

    def __init__(self):
        self.master_graph = KnowledgeGraph()
        self.reasoning_engine = ReasoningEngine(self.master_graph)
        self.fusion = KnowledgeFusion()
        self.query_history: List[QueryResult] = []
        self.data_dir = Path("data/knowledge")
        self.data_dir.mkdir(parents=True, exist_ok=True)

    async def ingest(
        self,
        content: str,
        source: str = "user",
        knowledge_type: KnowledgeType = KnowledgeType.FACTUAL
    ) -> KnowledgeFragment:
        """Ingest raw content as knowledge."""
        fragment_id = hashlib.sha256(content.encode()).hexdigest()[:16]

        fragment = KnowledgeFragment(
            id=fragment_id,
            content=content,
            knowledge_type=knowledge_type,
            source=source,
            confidence=0.9 if source == "user" else 0.7
        )

        await self.master_graph.add_fragment(fragment)
        return fragment

    async def add_entity(
        self,
        name: str,
        entity_type: str,
        attributes: Optional[Dict[str, Any]] = None,
        source: str = "system"
    ) -> Entity:
        """Add an entity to the knowledge graph."""
        entity_id = hashlib.sha256(f"{entity_type}:{name}".encode()).hexdigest()[:16]

        entity = Entity(
            id=entity_id,
            name=name,
            entity_type=entity_type,
            attributes=attributes or {},
            source=source
        )

        await self.master_graph.add_entity(entity)
        return entity

    async def add_relation(
        self,
        source_name: str,
        relation_type: str,
        target_name: str,
        properties: Optional[Dict[str, Any]] = None,
        bidirectional: bool = False
    ) -> Relation:
        """Add a relationship between entities."""
        # Find or create entities
        source_entity = None
        target_entity = None

        for entity in self.master_graph.entities.values():
            if entity.name == source_name:
                source_entity = entity
            if entity.name == target_name:
                target_entity = entity

        if not source_entity:
            source_entity = await self.add_entity(source_name, "auto")
        if not target_entity:
            target_entity = await self.add_entity(target_name, "auto")

        relation_id = hashlib.sha256(
            f"{source_entity.id}:{relation_type}:{target_entity.id}".encode()
        ).hexdigest()[:16]

        relation = Relation(
            id=relation_id,
            source_id=source_entity.id,
            target_id=target_entity.id,
            relation_type=relation_type,
            properties=properties or {},
            bidirectional=bidirectional
        )

        await self.master_graph.add_relation(relation)
        return relation

    async def query(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None,
        reasoning_modes: Optional[List[ReasoningMode]] = None,
        max_results: int = 10
    ) -> QueryResult:
        """Query the knowledge base."""
        start_time = time.time()

        q = Query(
            question=question,
            context=context or {},
            reasoning_modes=reasoning_modes or [ReasoningMode.DEDUCTIVE, ReasoningMode.INDUCTIVE],
            max_results=max_results
        )

        # Get inferences
        inferences = await self.reasoning_engine.reason(q)

        # Find relevant entities
        relevant_entities = []
        question_lower = question.lower()
        for entity in self.master_graph.entities.values():
            if entity.name.lower() in question_lower or question_lower in entity.name.lower():
                relevant_entities.append(entity)

        # Find relevant fragments
        relevant_fragments = []
        for fragment in self.master_graph.fragments.values():
            if any(word in fragment.content.lower() for word in question_lower.split()):
                relevant_fragments.append(fragment)

        answers = []
        for entity in relevant_entities[:5]:
            answers.append(entity.to_dict())

        for fragment in relevant_fragments[:5]:
            answers.append({
                "type": "fragment",
                "content": fragment.content,
                "confidence": fragment.confidence
            })

        result = QueryResult(
            query=q,
            answers=answers,
            inferences=inferences,
            confidence=max((inf.confidence for inf in inferences), default=0.5),
            reasoning_path=[inf.explanation for inf in inferences],
            sources=[e.source for e in relevant_entities],
            processing_time_ms=(time.time() - start_time) * 1000
        )

        self.query_history.append(result)
        return result

    async def fuse_sources(
        self,
        graphs: Dict[str, KnowledgeGraph],
        strategy: FusionStrategy = FusionStrategy.WEIGHTED
    ) -> KnowledgeGraph:
        """Fuse multiple knowledge sources."""
        for name, graph in graphs.items():
            await self.fusion.add_source(name, graph)

        fused = await self.fusion.fuse(strategy)

        # Merge into master graph
        for entity in fused.entities.values():
            if entity.id not in self.master_graph.entities:
                await self.master_graph.add_entity(entity)

        for relation in fused.relations.values():
            if relation.id not in self.master_graph.relations:
                await self.master_graph.add_relation(relation)

        return fused

    async def save(self, filename: str = "knowledge_state.json") -> None:
        """Save knowledge state."""
        state = {
            "entities": {
                eid: {
                    "id": e.id,
                    "name": e.name,
                    "type": e.entity_type,
                    "attributes": e.attributes,
                    "confidence": e.confidence,
                    "source": e.source,
                    "access_count": e.access_count
                }
                for eid, e in self.master_graph.entities.items()
            },
            "relations": {
                rid: {
                    "id": r.id,
                    "source_id": r.source_id,
                    "target_id": r.target_id,
                    "relation_type": r.relation_type,
                    "properties": r.properties,
                    "weight": r.weight,
                    "confidence": r.confidence,
                    "bidirectional": r.bidirectional
                }
                for rid, r in self.master_graph.relations.items()
            },
            "fragments": {
                fid: {
                    "id": f.id,
                    "content": f.content,
                    "knowledge_type": f.knowledge_type.value,
                    "entities": f.entities,
                    "relations": f.relations,
                    "confidence": f.confidence,
                    "source": f.source
                }
                for fid, f in self.master_graph.fragments.items()
            },
            "reasoning_stats": self.reasoning_engine.get_reasoning_stats(),
            "graph_stats": self.master_graph.get_statistics()
        }

        filepath = self.data_dir / filename
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2, default=str)

    async def load(self, filename: str = "knowledge_state.json") -> bool:
        """Load knowledge state."""
        filepath = self.data_dir / filename
        if not filepath.exists():
            return False

        try:
            with open(filepath) as f:
                state = json.load(f)

            # Restore entities
            for eid, data in state.get("entities", {}).items():
                entity = Entity(
                    id=data["id"],
                    name=data["name"],
                    entity_type=data["type"],
                    attributes=data["attributes"],
                    confidence=data["confidence"],
                    source=data["source"],
                    access_count=data["access_count"]
                )
                await self.master_graph.add_entity(entity)

            # Restore relations
            for rid, data in state.get("relations", {}).items():
                relation = Relation(
                    id=data["id"],
                    source_id=data["source_id"],
                    target_id=data["target_id"],
                    relation_type=data["relation_type"],
                    properties=data["properties"],
                    weight=data["weight"],
                    confidence=data["confidence"],
                    bidirectional=data["bidirectional"]
                )
                await self.master_graph.add_relation(relation)

            # Restore fragments
            for fid, data in state.get("fragments", {}).items():
                fragment = KnowledgeFragment(
                    id=data["id"],
                    content=data["content"],
                    knowledge_type=KnowledgeType(data["knowledge_type"]),
                    entities=data["entities"],
                    relations=data["relations"],
                    confidence=data["confidence"],
                    source=data["source"]
                )
                await self.master_graph.add_fragment(fragment)

            return True

        except Exception as e:
            print(f"Error loading knowledge state: {e}")
            return False

    def get_summary(self) -> Dict[str, Any]:
        """Get knowledge base summary."""
        return {
            "graph_stats": self.master_graph.get_statistics(),
            "reasoning_stats": self.reasoning_engine.get_reasoning_stats(),
            "query_count": len(self.query_history),
            "sources_count": len(self.fusion.sources),
            "avg_query_time_ms": (
                sum(q.processing_time_ms for q in self.query_history) / len(self.query_history)
                if self.query_history else 0
            )
        }


# Convenience instance
knowledge_engine = KnowledgeFusionEngine()
