#!/usr/bin/env python3
"""
BAEL - Semantic Engine
Semantic understanding and representation for agents.

Features:
- Concept modeling
- Semantic similarity
- Ontology management
- Meaning extraction
- Semantic search
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

class ConceptType(Enum):
    """Types of concepts."""
    ENTITY = "entity"
    ACTION = "action"
    PROPERTY = "property"
    RELATION = "relation"
    STATE = "state"
    EVENT = "event"
    ABSTRACT = "abstract"


class RelationType(Enum):
    """Types of semantic relations."""
    IS_A = "is_a"
    HAS_A = "has_a"
    PART_OF = "part_of"
    CAUSES = "causes"
    SIMILAR_TO = "similar_to"
    OPPOSITE_OF = "opposite_of"
    INSTANCE_OF = "instance_of"
    ATTRIBUTE_OF = "attribute_of"


class MeaningType(Enum):
    """Types of meanings."""
    LITERAL = "literal"
    FIGURATIVE = "figurative"
    CONTEXTUAL = "contextual"
    DERIVED = "derived"


class SimilarityMetric(Enum):
    """Types of similarity metrics."""
    COSINE = "cosine"
    JACCARD = "jaccard"
    PATH = "path"
    CONCEPT = "concept"


class OntologyLevel(Enum):
    """Ontology hierarchy levels."""
    ROOT = 0
    DOMAIN = 1
    CATEGORY = 2
    CONCEPT = 3
    INSTANCE = 4


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Concept:
    """A semantic concept."""
    concept_id: str = ""
    name: str = ""
    concept_type: ConceptType = ConceptType.ENTITY
    definition: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    embedding: List[float] = field(default_factory=list)
    synonyms: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.concept_id:
            self.concept_id = str(uuid.uuid4())[:8]


@dataclass
class SemanticRelation:
    """A semantic relation between concepts."""
    relation_id: str = ""
    source_id: str = ""
    target_id: str = ""
    relation_type: RelationType = RelationType.IS_A
    strength: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.relation_id:
            self.relation_id = str(uuid.uuid4())[:8]


@dataclass
class Meaning:
    """A semantic meaning."""
    meaning_id: str = ""
    text: str = ""
    meaning_type: MeaningType = MeaningType.LITERAL
    concepts: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5

    def __post_init__(self):
        if not self.meaning_id:
            self.meaning_id = str(uuid.uuid4())[:8]


@dataclass
class OntologyNode:
    """A node in an ontology."""
    node_id: str = ""
    name: str = ""
    level: OntologyLevel = OntologyLevel.CONCEPT
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    concept_id: Optional[str] = None

    def __post_init__(self):
        if not self.node_id:
            self.node_id = str(uuid.uuid4())[:8]


@dataclass
class SemanticQuery:
    """A semantic query."""
    query_id: str = ""
    text: str = ""
    concepts: List[str] = field(default_factory=list)
    filters: Dict[str, Any] = field(default_factory=dict)
    limit: int = 10

    def __post_init__(self):
        if not self.query_id:
            self.query_id = str(uuid.uuid4())[:8]


@dataclass
class SemanticConfig:
    """Semantic engine configuration."""
    embedding_dim: int = 128
    similarity_threshold: float = 0.7
    max_concepts: int = 10000


# =============================================================================
# CONCEPT MANAGER
# =============================================================================

class ConceptManager:
    """Manage semantic concepts."""

    def __init__(self, max_concepts: int = 10000, embedding_dim: int = 128):
        self._concepts: Dict[str, Concept] = {}
        self._by_name: Dict[str, str] = {}
        self._by_type: Dict[ConceptType, Set[str]] = defaultdict(set)
        self._max_concepts = max_concepts
        self._embedding_dim = embedding_dim

    def create(
        self,
        name: str,
        concept_type: ConceptType,
        definition: str = "",
        properties: Optional[Dict[str, Any]] = None,
        synonyms: Optional[List[str]] = None
    ) -> Concept:
        """Create a concept."""
        if len(self._concepts) >= self._max_concepts:
            raise ValueError("Maximum concept limit reached")

        embedding = self._generate_embedding(name, definition)

        concept = Concept(
            name=name,
            concept_type=concept_type,
            definition=definition,
            properties=properties or {},
            embedding=embedding,
            synonyms=synonyms or []
        )

        self._concepts[concept.concept_id] = concept
        self._by_name[name.lower()] = concept.concept_id
        self._by_type[concept_type].add(concept.concept_id)

        for synonym in concept.synonyms:
            self._by_name[synonym.lower()] = concept.concept_id

        return concept

    def _generate_embedding(self, name: str, definition: str) -> List[float]:
        """Generate a pseudo-embedding for concept."""
        text = f"{name} {definition}"

        random.seed(hash(text) % (2**32))

        embedding = [random.gauss(0, 1) for _ in range(self._embedding_dim)]

        norm = math.sqrt(sum(x*x for x in embedding))
        if norm > 0:
            embedding = [x / norm for x in embedding]

        return embedding

    def get(self, concept_id: str) -> Optional[Concept]:
        """Get concept by ID."""
        return self._concepts.get(concept_id)

    def get_by_name(self, name: str) -> Optional[Concept]:
        """Get concept by name."""
        concept_id = self._by_name.get(name.lower())

        if concept_id:
            return self._concepts.get(concept_id)

        return None

    def get_by_type(self, concept_type: ConceptType) -> List[Concept]:
        """Get concepts by type."""
        concept_ids = self._by_type.get(concept_type, set())
        return [self._concepts[cid] for cid in concept_ids if cid in self._concepts]

    def search(self, query: str) -> List[Concept]:
        """Search concepts by query."""
        query_lower = query.lower()
        results = []

        for concept in self._concepts.values():
            if query_lower in concept.name.lower():
                results.append(concept)
            elif query_lower in concept.definition.lower():
                results.append(concept)
            elif any(query_lower in syn.lower() for syn in concept.synonyms):
                results.append(concept)

        return results

    def add_synonym(self, concept_id: str, synonym: str) -> bool:
        """Add synonym to concept."""
        concept = self._concepts.get(concept_id)

        if not concept:
            return False

        if synonym not in concept.synonyms:
            concept.synonyms.append(synonym)
            self._by_name[synonym.lower()] = concept_id

        return True

    def update_property(
        self,
        concept_id: str,
        key: str,
        value: Any
    ) -> Optional[Concept]:
        """Update concept property."""
        concept = self._concepts.get(concept_id)

        if not concept:
            return None

        concept.properties[key] = value

        return concept

    def delete(self, concept_id: str) -> bool:
        """Delete a concept."""
        concept = self._concepts.get(concept_id)

        if not concept:
            return False

        if concept.name.lower() in self._by_name:
            del self._by_name[concept.name.lower()]

        for synonym in concept.synonyms:
            if synonym.lower() in self._by_name:
                del self._by_name[synonym.lower()]

        self._by_type[concept.concept_type].discard(concept_id)
        del self._concepts[concept_id]

        return True

    def count(self) -> int:
        """Count concepts."""
        return len(self._concepts)

    def all(self) -> List[Concept]:
        """Get all concepts."""
        return list(self._concepts.values())


# =============================================================================
# RELATION MANAGER
# =============================================================================

class RelationManager:
    """Manage semantic relations."""

    def __init__(self):
        self._relations: Dict[str, SemanticRelation] = {}
        self._by_source: Dict[str, List[str]] = defaultdict(list)
        self._by_target: Dict[str, List[str]] = defaultdict(list)
        self._by_type: Dict[RelationType, List[str]] = defaultdict(list)

    def create(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType,
        strength: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SemanticRelation:
        """Create a semantic relation."""
        relation = SemanticRelation(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            strength=strength,
            metadata=metadata or {}
        )

        self._relations[relation.relation_id] = relation
        self._by_source[source_id].append(relation.relation_id)
        self._by_target[target_id].append(relation.relation_id)
        self._by_type[relation_type].append(relation.relation_id)

        return relation

    def get(self, relation_id: str) -> Optional[SemanticRelation]:
        """Get relation by ID."""
        return self._relations.get(relation_id)

    def get_outgoing(self, source_id: str) -> List[SemanticRelation]:
        """Get outgoing relations."""
        rel_ids = self._by_source.get(source_id, [])
        return [self._relations[rid] for rid in rel_ids if rid in self._relations]

    def get_incoming(self, target_id: str) -> List[SemanticRelation]:
        """Get incoming relations."""
        rel_ids = self._by_target.get(target_id, [])
        return [self._relations[rid] for rid in rel_ids if rid in self._relations]

    def get_by_type(self, relation_type: RelationType) -> List[SemanticRelation]:
        """Get relations by type."""
        rel_ids = self._by_type.get(relation_type, [])
        return [self._relations[rid] for rid in rel_ids if rid in self._relations]

    def find(
        self,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        relation_type: Optional[RelationType] = None
    ) -> List[SemanticRelation]:
        """Find relations by criteria."""
        results = []

        for rel in self._relations.values():
            if source_id and rel.source_id != source_id:
                continue
            if target_id and rel.target_id != target_id:
                continue
            if relation_type and rel.relation_type != relation_type:
                continue

            results.append(rel)

        return results

    def get_related(
        self,
        concept_id: str,
        relation_type: Optional[RelationType] = None
    ) -> Set[str]:
        """Get related concept IDs."""
        related = set()

        for rel in self.get_outgoing(concept_id):
            if relation_type is None or rel.relation_type == relation_type:
                related.add(rel.target_id)

        for rel in self.get_incoming(concept_id):
            if relation_type is None or rel.relation_type == relation_type:
                related.add(rel.source_id)

        return related

    def delete(self, relation_id: str) -> bool:
        """Delete a relation."""
        rel = self._relations.get(relation_id)

        if not rel:
            return False

        if relation_id in self._by_source[rel.source_id]:
            self._by_source[rel.source_id].remove(relation_id)
        if relation_id in self._by_target[rel.target_id]:
            self._by_target[rel.target_id].remove(relation_id)
        if relation_id in self._by_type[rel.relation_type]:
            self._by_type[rel.relation_type].remove(relation_id)

        del self._relations[relation_id]

        return True

    def count(self) -> int:
        """Count relations."""
        return len(self._relations)

    def all(self) -> List[SemanticRelation]:
        """Get all relations."""
        return list(self._relations.values())


# =============================================================================
# SIMILARITY CALCULATOR
# =============================================================================

class SimilarityCalculator:
    """Calculate semantic similarity."""

    def __init__(self, threshold: float = 0.7):
        self._threshold = threshold

    def cosine_similarity(
        self,
        embedding_a: List[float],
        embedding_b: List[float]
    ) -> float:
        """Compute cosine similarity."""
        if len(embedding_a) != len(embedding_b):
            return 0.0

        dot_product = sum(a * b for a, b in zip(embedding_a, embedding_b))

        norm_a = math.sqrt(sum(a * a for a in embedding_a))
        norm_b = math.sqrt(sum(b * b for b in embedding_b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    def jaccard_similarity(
        self,
        set_a: Set[str],
        set_b: Set[str]
    ) -> float:
        """Compute Jaccard similarity."""
        if not set_a and not set_b:
            return 0.0

        intersection = len(set_a & set_b)
        union = len(set_a | set_b)

        return intersection / union if union > 0 else 0.0

    def concept_similarity(
        self,
        concept_a: Concept,
        concept_b: Concept
    ) -> float:
        """Compute concept similarity."""
        embedding_sim = self.cosine_similarity(
            concept_a.embedding,
            concept_b.embedding
        )

        words_a = set(concept_a.name.lower().split())
        words_b = set(concept_b.name.lower().split())
        name_sim = self.jaccard_similarity(words_a, words_b)

        synonyms_a = set(s.lower() for s in concept_a.synonyms)
        synonyms_b = set(s.lower() for s in concept_b.synonyms)
        all_a = words_a | synonyms_a
        all_b = words_b | synonyms_b
        lexical_sim = self.jaccard_similarity(all_a, all_b)

        return 0.5 * embedding_sim + 0.3 * name_sim + 0.2 * lexical_sim

    def find_similar(
        self,
        concept: Concept,
        candidates: List[Concept],
        top_k: int = 10
    ) -> List[Tuple[Concept, float]]:
        """Find similar concepts."""
        similarities = []

        for candidate in candidates:
            if candidate.concept_id == concept.concept_id:
                continue

            sim = self.concept_similarity(concept, candidate)

            if sim >= self._threshold:
                similarities.append((candidate, sim))

        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_k]

    def is_similar(
        self,
        concept_a: Concept,
        concept_b: Concept
    ) -> bool:
        """Check if concepts are similar."""
        return self.concept_similarity(concept_a, concept_b) >= self._threshold


# =============================================================================
# ONTOLOGY MANAGER
# =============================================================================

class OntologyManager:
    """Manage semantic ontologies."""

    def __init__(self):
        self._nodes: Dict[str, OntologyNode] = {}
        self._roots: List[str] = []

    def create_node(
        self,
        name: str,
        level: OntologyLevel,
        parent_id: Optional[str] = None,
        concept_id: Optional[str] = None
    ) -> OntologyNode:
        """Create an ontology node."""
        node = OntologyNode(
            name=name,
            level=level,
            parent_id=parent_id,
            concept_id=concept_id
        )

        self._nodes[node.node_id] = node

        if parent_id:
            parent = self._nodes.get(parent_id)
            if parent:
                parent.children_ids.append(node.node_id)
        else:
            self._roots.append(node.node_id)

        return node

    def get_node(self, node_id: str) -> Optional[OntologyNode]:
        """Get node by ID."""
        return self._nodes.get(node_id)

    def get_children(self, node_id: str) -> List[OntologyNode]:
        """Get child nodes."""
        node = self._nodes.get(node_id)

        if not node:
            return []

        return [
            self._nodes[cid]
            for cid in node.children_ids
            if cid in self._nodes
        ]

    def get_parent(self, node_id: str) -> Optional[OntologyNode]:
        """Get parent node."""
        node = self._nodes.get(node_id)

        if not node or not node.parent_id:
            return None

        return self._nodes.get(node.parent_id)

    def get_ancestors(self, node_id: str) -> List[OntologyNode]:
        """Get ancestor nodes."""
        ancestors = []
        current = self._nodes.get(node_id)

        while current and current.parent_id:
            parent = self._nodes.get(current.parent_id)
            if parent:
                ancestors.append(parent)
                current = parent
            else:
                break

        return ancestors

    def get_descendants(self, node_id: str) -> List[OntologyNode]:
        """Get descendant nodes."""
        descendants = []
        to_visit = [node_id]

        while to_visit:
            current_id = to_visit.pop(0)
            current = self._nodes.get(current_id)

            if current:
                for child_id in current.children_ids:
                    child = self._nodes.get(child_id)
                    if child:
                        descendants.append(child)
                        to_visit.append(child_id)

        return descendants

    def get_roots(self) -> List[OntologyNode]:
        """Get root nodes."""
        return [self._nodes[rid] for rid in self._roots if rid in self._nodes]

    def path_distance(self, node_a_id: str, node_b_id: str) -> int:
        """Compute path distance between nodes."""
        if node_a_id == node_b_id:
            return 0

        ancestors_a = {node_a_id}
        current = self._nodes.get(node_a_id)
        while current and current.parent_id:
            ancestors_a.add(current.parent_id)
            current = self._nodes.get(current.parent_id)

        ancestors_b = {node_b_id}
        current = self._nodes.get(node_b_id)
        while current and current.parent_id:
            ancestors_b.add(current.parent_id)
            current = self._nodes.get(current.parent_id)

        common = ancestors_a & ancestors_b

        if not common:
            return -1

        min_distance = float('inf')

        for lca in common:
            dist_a = self._distance_to_ancestor(node_a_id, lca)
            dist_b = self._distance_to_ancestor(node_b_id, lca)

            if dist_a >= 0 and dist_b >= 0:
                min_distance = min(min_distance, dist_a + dist_b)

        return int(min_distance) if min_distance < float('inf') else -1

    def _distance_to_ancestor(self, node_id: str, ancestor_id: str) -> int:
        """Compute distance to ancestor."""
        if node_id == ancestor_id:
            return 0

        distance = 0
        current = self._nodes.get(node_id)

        while current:
            if current.node_id == ancestor_id:
                return distance

            if current.parent_id:
                current = self._nodes.get(current.parent_id)
                distance += 1
            else:
                break

        return -1

    def count(self) -> int:
        """Count nodes."""
        return len(self._nodes)

    def all_nodes(self) -> List[OntologyNode]:
        """Get all nodes."""
        return list(self._nodes.values())


# =============================================================================
# MEANING EXTRACTOR
# =============================================================================

class MeaningExtractor:
    """Extract meaning from text."""

    def __init__(self):
        self._meanings: Dict[str, Meaning] = {}

    def extract(
        self,
        text: str,
        meaning_type: MeaningType = MeaningType.LITERAL,
        context: Optional[Dict[str, Any]] = None
    ) -> Meaning:
        """Extract meaning from text."""
        words = text.lower().split()
        concepts = self._identify_concepts(words)

        confidence = min(1.0, len(concepts) * 0.2 + 0.3)

        meaning = Meaning(
            text=text,
            meaning_type=meaning_type,
            concepts=concepts,
            context=context or {},
            confidence=confidence
        )

        self._meanings[meaning.meaning_id] = meaning

        return meaning

    def _identify_concepts(self, words: List[str]) -> List[str]:
        """Identify concepts from words."""
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
                      "have", "has", "had", "do", "does", "did", "will", "would", "could",
                      "should", "may", "might", "must", "shall", "can", "need", "dare",
                      "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
                      "into", "through", "during", "before", "after", "above", "below",
                      "and", "but", "or", "nor", "so", "yet", "both", "either", "neither",
                      "not", "only", "also", "than", "that", "which", "who", "whom"}

        concepts = [w for w in words if w not in stop_words and len(w) > 2]

        return concepts[:10]

    def get_meaning(self, meaning_id: str) -> Optional[Meaning]:
        """Get meaning by ID."""
        return self._meanings.get(meaning_id)

    def get_meanings_by_type(
        self,
        meaning_type: MeaningType
    ) -> List[Meaning]:
        """Get meanings by type."""
        return [
            m for m in self._meanings.values()
            if m.meaning_type == meaning_type
        ]

    def count(self) -> int:
        """Count meanings."""
        return len(self._meanings)


# =============================================================================
# SEMANTIC ENGINE
# =============================================================================

class SemanticEngine:
    """
    Semantic Engine for BAEL.

    Semantic understanding and representation.
    """

    def __init__(self, config: Optional[SemanticConfig] = None):
        self._config = config or SemanticConfig()

        self._concept_manager = ConceptManager(
            max_concepts=self._config.max_concepts,
            embedding_dim=self._config.embedding_dim
        )
        self._relation_manager = RelationManager()
        self._similarity = SimilarityCalculator(self._config.similarity_threshold)
        self._ontology = OntologyManager()
        self._meaning_extractor = MeaningExtractor()

    # ----- Concept Operations -----

    def create_concept(
        self,
        name: str,
        concept_type: ConceptType,
        definition: str = "",
        properties: Optional[Dict[str, Any]] = None,
        synonyms: Optional[List[str]] = None
    ) -> Concept:
        """Create a concept."""
        return self._concept_manager.create(
            name=name,
            concept_type=concept_type,
            definition=definition,
            properties=properties,
            synonyms=synonyms
        )

    def get_concept(self, concept_id: str) -> Optional[Concept]:
        """Get concept by ID."""
        return self._concept_manager.get(concept_id)

    def get_concept_by_name(self, name: str) -> Optional[Concept]:
        """Get concept by name."""
        return self._concept_manager.get_by_name(name)

    def get_concepts_by_type(
        self,
        concept_type: ConceptType
    ) -> List[Concept]:
        """Get concepts by type."""
        return self._concept_manager.get_by_type(concept_type)

    def search_concepts(self, query: str) -> List[Concept]:
        """Search concepts."""
        return self._concept_manager.search(query)

    def add_synonym(self, concept_id: str, synonym: str) -> bool:
        """Add synonym to concept."""
        return self._concept_manager.add_synonym(concept_id, synonym)

    def delete_concept(self, concept_id: str) -> bool:
        """Delete concept."""
        return self._concept_manager.delete(concept_id)

    # ----- Relation Operations -----

    def create_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType,
        strength: float = 1.0
    ) -> SemanticRelation:
        """Create a semantic relation."""
        return self._relation_manager.create(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            strength=strength
        )

    def get_relations(self, concept_id: str) -> List[SemanticRelation]:
        """Get all relations for concept."""
        outgoing = self._relation_manager.get_outgoing(concept_id)
        incoming = self._relation_manager.get_incoming(concept_id)
        return outgoing + incoming

    def get_related_concepts(
        self,
        concept_id: str,
        relation_type: Optional[RelationType] = None
    ) -> Set[str]:
        """Get related concept IDs."""
        return self._relation_manager.get_related(concept_id, relation_type)

    def find_relations(
        self,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        relation_type: Optional[RelationType] = None
    ) -> List[SemanticRelation]:
        """Find relations by criteria."""
        return self._relation_manager.find(source_id, target_id, relation_type)

    def delete_relation(self, relation_id: str) -> bool:
        """Delete relation."""
        return self._relation_manager.delete(relation_id)

    # ----- Similarity Operations -----

    def compute_similarity(
        self,
        concept_a_id: str,
        concept_b_id: str
    ) -> float:
        """Compute similarity between concepts."""
        concept_a = self._concept_manager.get(concept_a_id)
        concept_b = self._concept_manager.get(concept_b_id)

        if not concept_a or not concept_b:
            return 0.0

        return self._similarity.concept_similarity(concept_a, concept_b)

    def find_similar(
        self,
        concept_id: str,
        top_k: int = 10
    ) -> List[Tuple[Concept, float]]:
        """Find similar concepts."""
        concept = self._concept_manager.get(concept_id)

        if not concept:
            return []

        candidates = self._concept_manager.all()

        return self._similarity.find_similar(concept, candidates, top_k)

    def are_similar(
        self,
        concept_a_id: str,
        concept_b_id: str
    ) -> bool:
        """Check if concepts are similar."""
        concept_a = self._concept_manager.get(concept_a_id)
        concept_b = self._concept_manager.get(concept_b_id)

        if not concept_a or not concept_b:
            return False

        return self._similarity.is_similar(concept_a, concept_b)

    # ----- Ontology Operations -----

    def create_ontology_node(
        self,
        name: str,
        level: OntologyLevel,
        parent_id: Optional[str] = None,
        concept_id: Optional[str] = None
    ) -> OntologyNode:
        """Create ontology node."""
        return self._ontology.create_node(name, level, parent_id, concept_id)

    def get_ontology_node(self, node_id: str) -> Optional[OntologyNode]:
        """Get ontology node."""
        return self._ontology.get_node(node_id)

    def get_children(self, node_id: str) -> List[OntologyNode]:
        """Get child nodes."""
        return self._ontology.get_children(node_id)

    def get_ancestors(self, node_id: str) -> List[OntologyNode]:
        """Get ancestor nodes."""
        return self._ontology.get_ancestors(node_id)

    def get_descendants(self, node_id: str) -> List[OntologyNode]:
        """Get descendant nodes."""
        return self._ontology.get_descendants(node_id)

    def ontology_distance(self, node_a_id: str, node_b_id: str) -> int:
        """Compute ontology distance."""
        return self._ontology.path_distance(node_a_id, node_b_id)

    # ----- Meaning Operations -----

    def extract_meaning(
        self,
        text: str,
        meaning_type: MeaningType = MeaningType.LITERAL,
        context: Optional[Dict[str, Any]] = None
    ) -> Meaning:
        """Extract meaning from text."""
        return self._meaning_extractor.extract(text, meaning_type, context)

    def get_meaning(self, meaning_id: str) -> Optional[Meaning]:
        """Get meaning by ID."""
        return self._meaning_extractor.get_meaning(meaning_id)

    # ----- Search Operations -----

    def semantic_search(
        self,
        query: str,
        limit: int = 10
    ) -> List[Tuple[Concept, float]]:
        """Perform semantic search."""
        meaning = self._meaning_extractor.extract(query)

        if not meaning.concepts:
            return []

        results = []

        for concept_term in meaning.concepts:
            matches = self._concept_manager.search(concept_term)

            for match in matches:
                score = self._compute_search_score(query, match)
                results.append((match, score))

        results.sort(key=lambda x: x[1], reverse=True)

        seen = set()
        unique_results = []
        for concept, score in results:
            if concept.concept_id not in seen:
                seen.add(concept.concept_id)
                unique_results.append((concept, score))

        return unique_results[:limit]

    def _compute_search_score(self, query: str, concept: Concept) -> float:
        """Compute search relevance score."""
        query_lower = query.lower()

        if query_lower in concept.name.lower():
            return 1.0

        if any(query_lower in syn.lower() for syn in concept.synonyms):
            return 0.9

        if query_lower in concept.definition.lower():
            return 0.7

        return 0.5

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "concepts": self._concept_manager.count(),
            "relations": self._relation_manager.count(),
            "ontology_nodes": self._ontology.count(),
            "meanings_extracted": self._meaning_extractor.count()
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Semantic Engine."""
    print("=" * 70)
    print("BAEL - SEMANTIC ENGINE DEMO")
    print("Semantic Understanding and Representation")
    print("=" * 70)
    print()

    engine = SemanticEngine()

    # 1. Create Concepts
    print("1. CREATE CONCEPTS:")
    print("-" * 40)

    vehicle = engine.create_concept(
        "vehicle",
        ConceptType.ENTITY,
        "A machine used for transporting people or goods",
        synonyms=["transport", "conveyance"]
    )

    car = engine.create_concept(
        "car",
        ConceptType.ENTITY,
        "A four-wheeled motor vehicle",
        properties={"wheels": 4, "has_engine": True},
        synonyms=["automobile", "auto"]
    )

    drive = engine.create_concept(
        "drive",
        ConceptType.ACTION,
        "To operate and control the direction of a vehicle"
    )

    fast = engine.create_concept(
        "fast",
        ConceptType.PROPERTY,
        "Moving or capable of moving at high speed",
        synonyms=["quick", "rapid", "speedy"]
    )

    print(f"   Created: {vehicle.name} ({vehicle.concept_id})")
    print(f"   Created: {car.name} ({car.concept_id})")
    print(f"   Created: {drive.name} ({drive.concept_id})")
    print(f"   Created: {fast.name} ({fast.concept_id})")
    print()

    # 2. Create Relations
    print("2. CREATE RELATIONS:")
    print("-" * 40)

    rel1 = engine.create_relation(
        car.concept_id,
        vehicle.concept_id,
        RelationType.IS_A
    )

    rel2 = engine.create_relation(
        drive.concept_id,
        car.concept_id,
        RelationType.HAS_A
    )

    rel3 = engine.create_relation(
        fast.concept_id,
        car.concept_id,
        RelationType.ATTRIBUTE_OF
    )

    print(f"   {car.name} IS_A {vehicle.name}")
    print(f"   {drive.name} HAS_A {car.name}")
    print(f"   {fast.name} ATTRIBUTE_OF {car.name}")
    print()

    # 3. Get Related Concepts
    print("3. GET RELATED CONCEPTS:")
    print("-" * 40)

    related = engine.get_related_concepts(car.concept_id)

    print(f"   Related to {car.name}: {len(related)} concepts")
    for rid in related:
        r = engine.get_concept(rid)
        if r:
            print(f"     - {r.name}")
    print()

    # 4. Compute Similarity
    print("4. COMPUTE SIMILARITY:")
    print("-" * 40)

    truck = engine.create_concept(
        "truck",
        ConceptType.ENTITY,
        "A large motor vehicle for transporting goods",
        properties={"wheels": 6, "has_engine": True}
    )

    sim = engine.compute_similarity(car.concept_id, truck.concept_id)
    print(f"   {car.name} vs {truck.name}: {sim:.2f}")

    sim2 = engine.compute_similarity(car.concept_id, drive.concept_id)
    print(f"   {car.name} vs {drive.name}: {sim2:.2f}")
    print()

    # 5. Find Similar Concepts
    print("5. FIND SIMILAR CONCEPTS:")
    print("-" * 40)

    similar = engine.find_similar(car.concept_id, top_k=3)

    print(f"   Similar to {car.name}:")
    for concept, score in similar:
        print(f"     - {concept.name}: {score:.2f}")
    print()

    # 6. Search Concepts
    print("6. SEARCH CONCEPTS:")
    print("-" * 40)

    results = engine.search_concepts("motor")

    print(f"   Search 'motor': {len(results)} results")
    for r in results:
        print(f"     - {r.name}")
    print()

    # 7. Create Ontology
    print("7. CREATE ONTOLOGY:")
    print("-" * 40)

    root = engine.create_ontology_node(
        "Things",
        OntologyLevel.ROOT
    )

    physical = engine.create_ontology_node(
        "Physical Objects",
        OntologyLevel.DOMAIN,
        parent_id=root.node_id
    )

    vehicles_cat = engine.create_ontology_node(
        "Vehicles",
        OntologyLevel.CATEGORY,
        parent_id=physical.node_id
    )

    cars_node = engine.create_ontology_node(
        "Cars",
        OntologyLevel.CONCEPT,
        parent_id=vehicles_cat.node_id,
        concept_id=car.concept_id
    )

    print(f"   Root: {root.name}")
    print(f"   Domain: {physical.name}")
    print(f"   Category: {vehicles_cat.name}")
    print(f"   Concept: {cars_node.name}")
    print()

    # 8. Navigate Ontology
    print("8. NAVIGATE ONTOLOGY:")
    print("-" * 40)

    ancestors = engine.get_ancestors(cars_node.node_id)
    print(f"   Ancestors of {cars_node.name}:")
    for a in ancestors:
        print(f"     - {a.name} (level: {a.level.name})")

    children = engine.get_children(physical.node_id)
    print(f"   Children of {physical.name}: {[c.name for c in children]}")
    print()

    # 9. Ontology Distance
    print("9. ONTOLOGY DISTANCE:")
    print("-" * 40)

    trucks_node = engine.create_ontology_node(
        "Trucks",
        OntologyLevel.CONCEPT,
        parent_id=vehicles_cat.node_id,
        concept_id=truck.concept_id
    )

    distance = engine.ontology_distance(cars_node.node_id, trucks_node.node_id)
    print(f"   Distance {cars_node.name} to {trucks_node.name}: {distance}")

    distance2 = engine.ontology_distance(cars_node.node_id, root.node_id)
    print(f"   Distance {cars_node.name} to {root.name}: {distance2}")
    print()

    # 10. Extract Meaning
    print("10. EXTRACT MEANING:")
    print("-" * 40)

    text = "The fast car drives through the city"
    meaning = engine.extract_meaning(text)

    print(f"   Text: '{text}'")
    print(f"   Concepts: {meaning.concepts}")
    print(f"   Confidence: {meaning.confidence:.2f}")
    print()

    # 11. Semantic Search
    print("11. SEMANTIC SEARCH:")
    print("-" * 40)

    results = engine.semantic_search("transportation vehicle", limit=5)

    print(f"   Search 'transportation vehicle':")
    for concept, score in results:
        print(f"     - {concept.name}: {score:.2f}")
    print()

    # 12. Add Synonyms
    print("12. ADD SYNONYMS:")
    print("-" * 40)

    engine.add_synonym(car.concept_id, "motorcar")

    updated = engine.get_concept(car.concept_id)
    if updated:
        print(f"   {updated.name} synonyms: {updated.synonyms}")
    print()

    # 13. Find by Name
    print("13. FIND BY NAME:")
    print("-" * 40)

    found = engine.get_concept_by_name("automobile")
    if found:
        print(f"   Found 'automobile': {found.name} ({found.concept_id})")
    print()

    # 14. Get by Type
    print("14. GET BY TYPE:")
    print("-" * 40)

    entities = engine.get_concepts_by_type(ConceptType.ENTITY)
    actions = engine.get_concepts_by_type(ConceptType.ACTION)

    print(f"   Entities: {[e.name for e in entities]}")
    print(f"   Actions: {[a.name for a in actions]}")
    print()

    # 15. Summary
    print("15. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Semantic Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
