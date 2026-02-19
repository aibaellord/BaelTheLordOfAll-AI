"""
BAEL Semantic Memory Engine
============================

Conceptual knowledge representation.
Distinct from episodic memory.

"Ba'el knows what things mean." — Ba'el
"""

import logging
import threading
import time
import math
import random
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod
from collections import defaultdict, deque
import copy

logger = logging.getLogger("BAEL.SemanticMemory")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ConceptType(Enum):
    """Types of concepts."""
    ENTITY = auto()        # Objects, people
    PROPERTY = auto()      # Attributes
    RELATION = auto()      # Relationships
    EVENT = auto()         # Event types
    CATEGORY = auto()      # Categories
    ABSTRACT = auto()      # Abstract ideas


class RelationType(Enum):
    """Semantic relation types."""
    IS_A = auto()          # Hypernym
    HAS_A = auto()         # Part-whole
    CAN = auto()           # Capability
    IS = auto()            # Property
    CAUSES = auto()        # Causal
    LOCATED_IN = auto()    # Spatial
    USED_FOR = auto()      # Function
    SIMILAR_TO = auto()    # Similarity
    OPPOSITE_OF = auto()   # Antonym


class ActivationMode(Enum):
    """Spreading activation modes."""
    BREADTH_FIRST = auto()
    DEPTH_FIRST = auto()
    WEIGHTED = auto()


@dataclass
class Concept:
    """
    A semantic concept.
    """
    id: str
    name: str
    concept_type: ConceptType
    features: Dict[str, Any] = field(default_factory=dict)
    activation: float = 0.0
    base_activation: float = 0.0
    frequency: int = 0
    last_access: float = field(default_factory=time.time)

    @property
    def age(self) -> float:
        return time.time() - self.last_access

    def activate(self, amount: float) -> float:
        """Activate concept."""
        self.activation = min(1.0, self.activation + amount)
        self.last_access = time.time()
        self.frequency += 1
        return self.activation


@dataclass
class SemanticRelation:
    """
    A relation between concepts.
    """
    id: str
    source_id: str
    target_id: str
    relation_type: RelationType
    weight: float = 1.0
    bidirectional: bool = False


@dataclass
class SemanticFeature:
    """
    A semantic feature.
    """
    name: str
    value: Any
    salience: float = 0.5
    distinguishing: bool = False


@dataclass
class Category:
    """
    A semantic category.
    """
    id: str
    name: str
    prototype: Optional[str] = None  # Prototype concept ID
    members: List[str] = field(default_factory=list)
    features: Dict[str, float] = field(default_factory=dict)  # Feature -> typicality


@dataclass
class RetrievalResult:
    """
    Result of semantic retrieval.
    """
    concept: Concept
    activation: float
    path: List[str]
    retrieval_time: float


# ============================================================================
# CONCEPT STORE
# ============================================================================

class ConceptStore:
    """
    Store semantic concepts.

    "Ba'el's knowledge store." — Ba'el
    """

    def __init__(self):
        """Initialize store."""
        self._concepts: Dict[str, Concept] = {}
        self._relations: Dict[str, SemanticRelation] = {}
        self._categories: Dict[str, Category] = {}

        # Indices
        self._by_name: Dict[str, str] = {}
        self._by_type: Dict[ConceptType, List[str]] = defaultdict(list)
        self._outgoing: Dict[str, List[str]] = defaultdict(list)
        self._incoming: Dict[str, List[str]] = defaultdict(list)

        self._concept_counter = 0
        self._relation_counter = 0
        self._lock = threading.RLock()

    def _generate_concept_id(self) -> str:
        self._concept_counter += 1
        return f"concept_{self._concept_counter}"

    def _generate_relation_id(self) -> str:
        self._relation_counter += 1
        return f"relation_{self._relation_counter}"

    def add_concept(
        self,
        name: str,
        concept_type: ConceptType,
        features: Dict[str, Any] = None
    ) -> Concept:
        """Add concept to store."""
        with self._lock:
            concept_id = self._generate_concept_id()

            concept = Concept(
                id=concept_id,
                name=name,
                concept_type=concept_type,
                features=features or {}
            )

            self._concepts[concept_id] = concept
            self._by_name[name.lower()] = concept_id
            self._by_type[concept_type].append(concept_id)

            return concept

    def add_relation(
        self,
        source_name: str,
        target_name: str,
        relation_type: RelationType,
        weight: float = 1.0,
        bidirectional: bool = False
    ) -> Optional[SemanticRelation]:
        """Add relation between concepts."""
        with self._lock:
            source_id = self._by_name.get(source_name.lower())
            target_id = self._by_name.get(target_name.lower())

            if not source_id or not target_id:
                return None

            relation_id = self._generate_relation_id()

            relation = SemanticRelation(
                id=relation_id,
                source_id=source_id,
                target_id=target_id,
                relation_type=relation_type,
                weight=weight,
                bidirectional=bidirectional
            )

            self._relations[relation_id] = relation
            self._outgoing[source_id].append(relation_id)
            self._incoming[target_id].append(relation_id)

            if bidirectional:
                self._outgoing[target_id].append(relation_id)
                self._incoming[source_id].append(relation_id)

            return relation

    def get_concept(self, name: str) -> Optional[Concept]:
        """Get concept by name."""
        concept_id = self._by_name.get(name.lower())
        if concept_id:
            return self._concepts.get(concept_id)
        return None

    def get_relations(
        self,
        concept_name: str,
        relation_type: RelationType = None
    ) -> List[SemanticRelation]:
        """Get relations for concept."""
        with self._lock:
            concept_id = self._by_name.get(concept_name.lower())
            if not concept_id:
                return []

            relation_ids = self._outgoing.get(concept_id, [])
            relations = [self._relations[rid] for rid in relation_ids]

            if relation_type:
                relations = [r for r in relations if r.relation_type == relation_type]

            return relations

    def get_related(
        self,
        concept_name: str,
        relation_type: RelationType = None
    ) -> List[Concept]:
        """Get related concepts."""
        relations = self.get_relations(concept_name, relation_type)

        results = []
        for rel in relations:
            concept_id = self._by_name.get(concept_name.lower())
            target_id = rel.target_id if rel.source_id == concept_id else rel.source_id
            concept = self._concepts.get(target_id)
            if concept:
                results.append(concept)

        return results

    @property
    def concepts(self) -> List[Concept]:
        return list(self._concepts.values())

    @property
    def relations(self) -> List[SemanticRelation]:
        return list(self._relations.values())


# ============================================================================
# SPREADING ACTIVATION
# ============================================================================

class SpreadingActivationRetrieval:
    """
    Spreading activation for semantic retrieval.

    "Ba'el spreads activation." — Ba'el
    """

    def __init__(
        self,
        store: ConceptStore,
        decay: float = 0.85,
        threshold: float = 0.1
    ):
        """Initialize retrieval."""
        self._store = store
        self._decay = decay
        self._threshold = threshold
        self._lock = threading.RLock()

    def activate(
        self,
        cue: str,
        initial_activation: float = 1.0,
        max_spread: int = 3
    ) -> List[RetrievalResult]:
        """Spread activation from cue."""
        with self._lock:
            start_time = time.time()

            # Get starting concept
            start_concept = self._store.get_concept(cue)
            if not start_concept:
                return []

            # Reset activations
            for concept in self._store.concepts:
                concept.activation = concept.base_activation

            # Activate start
            start_concept.activate(initial_activation)

            # Spread activation
            results = []
            visited = {start_concept.id}
            frontier = [(start_concept, [cue], initial_activation)]

            for depth in range(max_spread):
                next_frontier = []

                for concept, path, activation in frontier:
                    relations = self._store.get_relations(concept.name)

                    for rel in relations:
                        target_id = rel.target_id if rel.source_id == concept.id else rel.source_id

                        if target_id in visited:
                            continue

                        target = self._store._concepts.get(target_id)
                        if not target:
                            continue

                        # Spread activation
                        spread = activation * self._decay * rel.weight

                        if spread >= self._threshold:
                            target.activate(spread)
                            visited.add(target_id)

                            new_path = path + [target.name]
                            next_frontier.append((target, new_path, spread))

                            results.append(RetrievalResult(
                                concept=target,
                                activation=target.activation,
                                path=new_path,
                                retrieval_time=time.time() - start_time
                            ))

                frontier = next_frontier

            # Sort by activation
            results.sort(key=lambda r: r.activation, reverse=True)

            return results

    def retrieve(
        self,
        cue: str,
        top_k: int = 5
    ) -> List[Concept]:
        """Retrieve top concepts."""
        results = self.activate(cue)
        return [r.concept for r in results[:top_k]]


# ============================================================================
# FEATURE-BASED SIMILARITY
# ============================================================================

class FeatureSimilarity:
    """
    Feature-based semantic similarity.

    "Ba'el compares meanings." — Ba'el
    """

    def __init__(self, store: ConceptStore):
        """Initialize similarity."""
        self._store = store
        self._lock = threading.RLock()

    def jaccard_similarity(
        self,
        concept1: str,
        concept2: str
    ) -> float:
        """Calculate Jaccard similarity."""
        with self._lock:
            c1 = self._store.get_concept(concept1)
            c2 = self._store.get_concept(concept2)

            if not c1 or not c2:
                return 0.0

            features1 = set(c1.features.keys())
            features2 = set(c2.features.keys())

            intersection = features1 & features2
            union = features1 | features2

            if not union:
                return 0.0

            return len(intersection) / len(union)

    def tversky_similarity(
        self,
        concept1: str,
        concept2: str,
        alpha: float = 0.5,
        beta: float = 0.5
    ) -> float:
        """Calculate Tversky similarity (asymmetric)."""
        with self._lock:
            c1 = self._store.get_concept(concept1)
            c2 = self._store.get_concept(concept2)

            if not c1 or not c2:
                return 0.0

            features1 = set(c1.features.keys())
            features2 = set(c2.features.keys())

            common = len(features1 & features2)
            only1 = len(features1 - features2)
            only2 = len(features2 - features1)

            denominator = common + alpha * only1 + beta * only2

            if denominator == 0:
                return 0.0

            return common / denominator

    def path_similarity(
        self,
        concept1: str,
        concept2: str
    ) -> float:
        """Calculate path-based similarity."""
        with self._lock:
            # BFS to find shortest path
            c1 = self._store.get_concept(concept1)
            c2 = self._store.get_concept(concept2)

            if not c1 or not c2:
                return 0.0

            if c1.id == c2.id:
                return 1.0

            # Simple BFS
            visited = {c1.id}
            frontier = [(c1, 0)]

            while frontier:
                concept, depth = frontier.pop(0)

                if depth > 5:  # Max depth
                    break

                related = self._store.get_related(concept.name)

                for rel_concept in related:
                    if rel_concept.id == c2.id:
                        # Found path
                        return 1.0 / (depth + 1)

                    if rel_concept.id not in visited:
                        visited.add(rel_concept.id)
                        frontier.append((rel_concept, depth + 1))

            return 0.0


# ============================================================================
# SEMANTIC MEMORY ENGINE
# ============================================================================

class SemanticMemoryEngine:
    """
    Complete semantic memory engine.

    "Ba'el's world knowledge." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._store = ConceptStore()
        self._retrieval = SpreadingActivationRetrieval(self._store)
        self._similarity = FeatureSimilarity(self._store)
        self._lock = threading.RLock()

    # Concept management

    def add_concept(
        self,
        name: str,
        concept_type: ConceptType = ConceptType.ENTITY,
        features: Dict[str, Any] = None
    ) -> Concept:
        """Add concept."""
        return self._store.add_concept(name, concept_type, features)

    def relate(
        self,
        source: str,
        target: str,
        relation: RelationType,
        weight: float = 1.0
    ) -> Optional[SemanticRelation]:
        """Create relation between concepts."""
        return self._store.add_relation(source, target, relation, weight)

    def is_a(self, concept: str, category: str) -> Optional[SemanticRelation]:
        """Add IS-A relation (hypernym)."""
        return self.relate(concept, category, RelationType.IS_A)

    def has_a(self, whole: str, part: str) -> Optional[SemanticRelation]:
        """Add HAS-A relation (part-whole)."""
        return self.relate(whole, part, RelationType.HAS_A)

    def can(self, agent: str, action: str) -> Optional[SemanticRelation]:
        """Add CAN relation (capability)."""
        return self.relate(agent, action, RelationType.CAN)

    # Retrieval

    def retrieve(
        self,
        cue: str,
        top_k: int = 5
    ) -> List[Concept]:
        """Retrieve related concepts."""
        return self._retrieval.retrieve(cue, top_k)

    def spread_activation(
        self,
        cue: str,
        max_spread: int = 3
    ) -> List[RetrievalResult]:
        """Spread activation from cue."""
        return self._retrieval.activate(cue, max_spread=max_spread)

    def get(self, name: str) -> Optional[Concept]:
        """Get concept by name."""
        return self._store.get_concept(name)

    def get_related(
        self,
        name: str,
        relation: RelationType = None
    ) -> List[Concept]:
        """Get related concepts."""
        return self._store.get_related(name, relation)

    # Similarity

    def similarity(self, concept1: str, concept2: str) -> float:
        """Calculate semantic similarity."""
        # Combine feature and path similarity
        feature_sim = self._similarity.jaccard_similarity(concept1, concept2)
        path_sim = self._similarity.path_similarity(concept1, concept2)
        return (feature_sim + path_sim) / 2

    # Queries

    def is_type_of(self, concept: str, category: str) -> bool:
        """Check if concept is type of category."""
        relations = self._store.get_relations(concept, RelationType.IS_A)
        for rel in relations:
            target = self._store._concepts.get(rel.target_id)
            if target and target.name.lower() == category.lower():
                return True
        return False

    def has_property(self, concept: str, property_name: str) -> Optional[Any]:
        """Check if concept has property."""
        c = self._store.get_concept(concept)
        if c:
            return c.features.get(property_name)
        return None

    @property
    def concepts(self) -> List[Concept]:
        return self._store.concepts

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'concepts': len(self._store.concepts),
            'relations': len(self._store.relations),
            'categories': len(self._store._categories)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_semantic_memory() -> SemanticMemoryEngine:
    """Create semantic memory engine."""
    return SemanticMemoryEngine()


def build_sample_knowledge() -> SemanticMemoryEngine:
    """Build sample semantic network."""
    sm = create_semantic_memory()

    # Add concepts
    sm.add_concept("animal", ConceptType.CATEGORY)
    sm.add_concept("mammal", ConceptType.CATEGORY)
    sm.add_concept("dog", ConceptType.ENTITY, {"legs": 4, "has_fur": True})
    sm.add_concept("cat", ConceptType.ENTITY, {"legs": 4, "has_fur": True})
    sm.add_concept("bark", ConceptType.EVENT)
    sm.add_concept("meow", ConceptType.EVENT)

    # Add relations
    sm.is_a("mammal", "animal")
    sm.is_a("dog", "mammal")
    sm.is_a("cat", "mammal")
    sm.can("dog", "bark")
    sm.can("cat", "meow")

    return sm
