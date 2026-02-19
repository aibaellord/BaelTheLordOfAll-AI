"""
⚡ UNIVERSAL KNOWLEDGE ⚡
========================
Universal knowledge representation.

Features:
- Multi-domain knowledge
- Knowledge taxonomy
- Semantic indexing
- Knowledge graphs
"""

import math
import numpy as np
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import uuid


class KnowledgeType(Enum):
    """Types of knowledge"""
    FACTUAL = auto()      # Facts
    PROCEDURAL = auto()   # How-to
    CONCEPTUAL = auto()   # Concepts
    METACOGNITIVE = auto() # About knowing
    TACIT = auto()        # Implicit
    EXPLICIT = auto()     # Stated
    CAUSAL = auto()       # Cause-effect
    RELATIONAL = auto()   # Relationships


@dataclass
class KnowledgeUnit:
    """Atomic unit of knowledge"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Content
    content: str = ""
    knowledge_type: KnowledgeType = KnowledgeType.FACTUAL

    # Source
    source: str = ""
    confidence: float = 1.0

    # Connections
    related: Set[str] = field(default_factory=set)
    derived_from: Set[str] = field(default_factory=set)
    supports: Set[str] = field(default_factory=set)
    contradicts: Set[str] = field(default_factory=set)

    # Embedding
    embedding: Optional[np.ndarray] = None

    # Metadata
    domains: Set[str] = field(default_factory=set)
    tags: Set[str] = field(default_factory=set)
    importance: float = 0.5

    # Temporal
    created_at: float = 0.0
    accessed_at: float = 0.0
    access_count: int = 0


@dataclass
class KnowledgeDomain:
    """A domain of knowledge"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""

    # Hierarchy
    parent: Optional[str] = None
    children: Set[str] = field(default_factory=set)

    # Knowledge in domain
    knowledge_units: Set[str] = field(default_factory=set)

    # Domain properties
    maturity: float = 0.5  # How well-developed
    coherence: float = 0.5  # How consistent
    completeness: float = 0.5  # How complete

    # Connections to other domains
    related_domains: Dict[str, float] = field(default_factory=dict)  # domain_id -> strength


class UniversalKnowledge:
    """
    Universal knowledge storage and retrieval.
    """

    def __init__(self):
        self.units: Dict[str, KnowledgeUnit] = {}
        self.domains: Dict[str, KnowledgeDomain] = {}

        # Indexes
        self.by_type: Dict[KnowledgeType, Set[str]] = defaultdict(set)
        self.by_domain: Dict[str, Set[str]] = defaultdict(set)
        self.by_tag: Dict[str, Set[str]] = defaultdict(set)

        # Graph structure
        self.knowledge_graph: Dict[str, Set[str]] = defaultdict(set)

    def add_knowledge(self, unit: KnowledgeUnit):
        """Add knowledge unit"""
        self.units[unit.id] = unit

        # Update indexes
        self.by_type[unit.knowledge_type].add(unit.id)

        for domain in unit.domains:
            self.by_domain[domain].add(unit.id)

        for tag in unit.tags:
            self.by_tag[tag].add(unit.id)

        # Update graph
        for related_id in unit.related:
            self.knowledge_graph[unit.id].add(related_id)
            self.knowledge_graph[related_id].add(unit.id)

    def add_domain(self, domain: KnowledgeDomain):
        """Add knowledge domain"""
        self.domains[domain.id] = domain

        if domain.parent and domain.parent in self.domains:
            self.domains[domain.parent].children.add(domain.id)

    def query(
        self,
        query_embedding: np.ndarray = None,
        knowledge_type: KnowledgeType = None,
        domain: str = None,
        tags: Set[str] = None,
        min_confidence: float = 0.0,
        limit: int = 10
    ) -> List[KnowledgeUnit]:
        """Query knowledge base"""
        candidates = set(self.units.keys())

        # Filter by type
        if knowledge_type:
            candidates &= self.by_type.get(knowledge_type, set())

        # Filter by domain
        if domain:
            candidates &= self.by_domain.get(domain, set())

        # Filter by tags
        if tags:
            for tag in tags:
                candidates &= self.by_tag.get(tag, set())

        # Get units
        results = []
        for uid in candidates:
            unit = self.units.get(uid)
            if unit and unit.confidence >= min_confidence:
                results.append(unit)

        # Semantic similarity if embedding provided
        if query_embedding is not None:
            def similarity(unit):
                if unit.embedding is None:
                    return 0.0
                return np.dot(query_embedding, unit.embedding) / (
                    np.linalg.norm(query_embedding) *
                    np.linalg.norm(unit.embedding) + 1e-10
                )

            results.sort(key=similarity, reverse=True)
        else:
            results.sort(key=lambda u: -u.importance)

        return results[:limit]

    def get_related(
        self,
        unit_id: str,
        depth: int = 1
    ) -> Set[KnowledgeUnit]:
        """Get related knowledge"""
        related = set()
        visited = {unit_id}
        current = {unit_id}

        for _ in range(depth):
            next_level = set()
            for uid in current:
                for neighbor in self.knowledge_graph.get(uid, set()):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        next_level.add(neighbor)
                        if neighbor in self.units:
                            related.add(self.units[neighbor])
            current = next_level

        return related

    def get_contradictions(self) -> List[Tuple[KnowledgeUnit, KnowledgeUnit]]:
        """Find contradicting knowledge"""
        contradictions = []

        for unit in self.units.values():
            for contra_id in unit.contradicts:
                if contra_id in self.units:
                    contradictions.append((unit, self.units[contra_id]))

        return contradictions

    def get_domain_knowledge(
        self,
        domain_id: str,
        include_children: bool = True
    ) -> List[KnowledgeUnit]:
        """Get all knowledge in domain"""
        domain = self.domains.get(domain_id)
        if not domain:
            return []

        unit_ids = set(domain.knowledge_units)

        if include_children:
            for child_id in domain.children:
                child_units = self.get_domain_knowledge(child_id, True)
                unit_ids.update(u.id for u in child_units)

        return [self.units[uid] for uid in unit_ids if uid in self.units]


class KnowledgeIndex:
    """
    Advanced knowledge indexing.
    """

    def __init__(self, universal: UniversalKnowledge = None):
        self.universal = universal or UniversalKnowledge()

        # Inverted index
        self.inverted_index: Dict[str, Set[str]] = defaultdict(set)

        # Semantic clusters
        self.clusters: Dict[int, Set[str]] = {}

        # Concept hierarchy
        self.concept_hierarchy: Dict[str, Set[str]] = defaultdict(set)

    def build_inverted_index(self):
        """Build inverted index from content"""
        self.inverted_index.clear()

        for unit in self.universal.units.values():
            # Simple tokenization
            words = unit.content.lower().split()

            for word in words:
                self.inverted_index[word].add(unit.id)

    def search(self, query: str) -> List[KnowledgeUnit]:
        """Search knowledge by text"""
        words = query.lower().split()

        if not words:
            return []

        # Get units containing all words
        result_ids = self.inverted_index.get(words[0], set()).copy()

        for word in words[1:]:
            result_ids &= self.inverted_index.get(word, set())

        return [
            self.universal.units[uid]
            for uid in result_ids
            if uid in self.universal.units
        ]

    def cluster_knowledge(self, n_clusters: int = 10):
        """Cluster knowledge by similarity"""
        # Get units with embeddings
        units_with_emb = [
            (uid, unit.embedding)
            for uid, unit in self.universal.units.items()
            if unit.embedding is not None
        ]

        if not units_with_emb:
            return

        # Simple k-means-like clustering
        embeddings = np.array([e for _, e in units_with_emb])
        uids = [uid for uid, _ in units_with_emb]

        # Random initial centers
        indices = np.random.choice(len(embeddings), min(n_clusters, len(embeddings)), replace=False)
        centers = embeddings[indices]

        for _ in range(10):  # Iterations
            # Assign to clusters
            assignments = []
            for emb in embeddings:
                distances = [np.linalg.norm(emb - c) for c in centers]
                assignments.append(np.argmin(distances))

            # Update centers
            new_centers = []
            for i in range(n_clusters):
                cluster_points = embeddings[np.array(assignments) == i]
                if len(cluster_points) > 0:
                    new_centers.append(cluster_points.mean(axis=0))
                else:
                    new_centers.append(centers[i])
            centers = np.array(new_centers)

        # Store clusters
        self.clusters = defaultdict(set)
        for uid, cluster_id in zip(uids, assignments):
            self.clusters[cluster_id].add(uid)

    def get_cluster(self, cluster_id: int) -> List[KnowledgeUnit]:
        """Get knowledge in cluster"""
        return [
            self.universal.units[uid]
            for uid in self.clusters.get(cluster_id, set())
            if uid in self.universal.units
        ]

    def build_concept_hierarchy(self):
        """Build concept hierarchy from domains"""
        self.concept_hierarchy.clear()

        for domain in self.universal.domains.values():
            if domain.parent:
                self.concept_hierarchy[domain.parent].add(domain.id)

    def get_descendants(self, concept_id: str) -> Set[str]:
        """Get all descendant concepts"""
        descendants = set()
        to_visit = list(self.concept_hierarchy.get(concept_id, set()))

        while to_visit:
            child = to_visit.pop()
            descendants.add(child)
            to_visit.extend(self.concept_hierarchy.get(child, set()))

        return descendants


# Export all
__all__ = [
    'KnowledgeType',
    'KnowledgeUnit',
    'KnowledgeDomain',
    'UniversalKnowledge',
    'KnowledgeIndex',
]
