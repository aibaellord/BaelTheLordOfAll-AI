"""
BAEL Analogical Reasoning Engine
=================================

Structure mapping and analogy-based reasoning.
Gentner's Structure Mapping Theory.

"Ba'el sees the hidden similarities." — Ba'el
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

logger = logging.getLogger("BAEL.AnalogicalReasoning")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class RelationType(Enum):
    """Types of relations."""
    ATTRIBUTE = auto()     # Property of entity
    FUNCTION = auto()      # Functional relation
    CAUSAL = auto()        # Causes
    PART_OF = auto()       # Part-whole
    IS_A = auto()          # Type hierarchy
    SPATIAL = auto()       # Spatial relation
    TEMPORAL = auto()      # Temporal relation
    COMPARISON = auto()    # Greater/less/equal


class MappingType(Enum):
    """Types of mapping."""
    ONE_TO_ONE = auto()    # Entity to entity
    MANY_TO_ONE = auto()   # Many to one
    STRUCTURE = auto()     # Structural mapping


class AnalogyType(Enum):
    """Types of analogy."""
    LITERAL_SIMILARITY = auto()  # Many shared attributes
    ANALOGY = auto()             # Shared relational structure
    MERE_APPEARANCE = auto()     # Only surface similarities
    ANOMALY = auto()             # Few similarities


@dataclass
class Entity:
    """
    An entity in a domain.
    """
    id: str
    name: str
    attributes: Dict[str, Any] = field(default_factory=dict)

    def get_attribute(self, name: str) -> Optional[Any]:
        return self.attributes.get(name)


@dataclass
class Relation:
    """
    A relation between entities.
    """
    id: str
    name: str
    type: RelationType
    arguments: List[str]  # Entity IDs
    order: int = 1  # Order (higher = more abstract)

    @property
    def arity(self) -> int:
        return len(self.arguments)


@dataclass
class Domain:
    """
    A knowledge domain with entities and relations.
    """
    id: str
    name: str
    entities: Dict[str, Entity] = field(default_factory=dict)
    relations: Dict[str, Relation] = field(default_factory=dict)

    def add_entity(self, entity: Entity) -> None:
        self.entities[entity.id] = entity

    def add_relation(self, relation: Relation) -> None:
        self.relations[relation.id] = relation

    def get_relations_for(self, entity_id: str) -> List[Relation]:
        return [r for r in self.relations.values() if entity_id in r.arguments]


@dataclass
class Mapping:
    """
    A mapping between entities in two domains.
    """
    source_id: str
    target_id: str
    confidence: float = 1.0
    type: MappingType = MappingType.ONE_TO_ONE


@dataclass
class StructureMatch:
    """
    A structural match between domains.
    """
    id: str
    source_domain: str
    target_domain: str
    entity_mappings: List[Mapping]
    relation_mappings: List[Tuple[str, str]]
    score: float
    analogy_type: AnalogyType


@dataclass
class Inference:
    """
    An inference made from analogy.
    """
    id: str
    source_relation: str
    inferred_relation: Relation
    confidence: float
    basis: str  # What the inference is based on


# ============================================================================
# STRUCTURE MAPPER
# ============================================================================

class StructureMapper:
    """
    Map structure between domains.
    Implements Gentner's Structure Mapping Theory.

    "Ba'el maps deep structure." — Ba'el
    """

    def __init__(self):
        """Initialize mapper."""
        self._match_counter = 0
        self._lock = threading.RLock()

    def _generate_match_id(self) -> str:
        self._match_counter += 1
        return f"match_{self._match_counter}"

    def find_matches(
        self,
        source: Domain,
        target: Domain,
        min_score: float = 0.3
    ) -> List[StructureMatch]:
        """Find structural matches between domains."""
        with self._lock:
            # Generate candidate entity mappings
            entity_candidates = self._generate_entity_candidates(source, target)

            # Generate all consistent mapping hypotheses
            hypotheses = self._generate_hypotheses(entity_candidates)

            # Score each hypothesis
            scored = []
            for hyp in hypotheses:
                score, rel_mappings = self._score_hypothesis(source, target, hyp)
                if score >= min_score:
                    analogy_type = self._classify_analogy(source, target, hyp, score)

                    match = StructureMatch(
                        id=self._generate_match_id(),
                        source_domain=source.id,
                        target_domain=target.id,
                        entity_mappings=hyp,
                        relation_mappings=rel_mappings,
                        score=score,
                        analogy_type=analogy_type
                    )
                    scored.append(match)

            # Sort by score
            scored.sort(key=lambda x: x.score, reverse=True)

            return scored

    def _generate_entity_candidates(
        self,
        source: Domain,
        target: Domain
    ) -> Dict[str, List[Tuple[str, float]]]:
        """Generate candidate mappings for each source entity."""
        candidates = {}

        for se in source.entities.values():
            candidates[se.id] = []

            for te in target.entities.values():
                # Score based on attribute similarity
                similarity = self._attribute_similarity(se, te)

                # Boost if same type
                if se.attributes.get('type') == te.attributes.get('type'):
                    similarity += 0.2

                candidates[se.id].append((te.id, similarity))

            # Sort by similarity
            candidates[se.id].sort(key=lambda x: x[1], reverse=True)

        return candidates

    def _attribute_similarity(
        self,
        entity1: Entity,
        entity2: Entity
    ) -> float:
        """Compute attribute similarity."""
        if not entity1.attributes and not entity2.attributes:
            return 0.5

        all_keys = set(entity1.attributes.keys()) | set(entity2.attributes.keys())

        if not all_keys:
            return 0.5

        matches = 0
        for key in all_keys:
            v1 = entity1.attributes.get(key)
            v2 = entity2.attributes.get(key)

            if v1 is not None and v2 is not None:
                if v1 == v2:
                    matches += 1
                elif isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                    # Numeric similarity
                    if max(abs(v1), abs(v2)) > 0:
                        matches += 1 - abs(v1 - v2) / max(abs(v1), abs(v2))

        return matches / len(all_keys)

    def _generate_hypotheses(
        self,
        candidates: Dict[str, List[Tuple[str, float]]]
    ) -> List[List[Mapping]]:
        """Generate mapping hypotheses."""
        # Simplified: generate top-k consistent mappings
        hypotheses = []

        if not candidates:
            return hypotheses

        # Greedy: take best mapping for each entity
        used_targets = set()
        greedy = []

        for source_id, target_list in candidates.items():
            for target_id, score in target_list:
                if target_id not in used_targets:
                    greedy.append(Mapping(
                        source_id=source_id,
                        target_id=target_id,
                        confidence=score
                    ))
                    used_targets.add(target_id)
                    break

        hypotheses.append(greedy)

        # Generate some alternatives by swapping
        for _ in range(min(5, len(greedy))):
            alt = copy.deepcopy(greedy)
            if len(alt) >= 2:
                i, j = random.sample(range(len(alt)), 2)
                alt[i].target_id, alt[j].target_id = alt[j].target_id, alt[i].target_id
                hypotheses.append(alt)

        return hypotheses

    def _score_hypothesis(
        self,
        source: Domain,
        target: Domain,
        mappings: List[Mapping]
    ) -> Tuple[float, List[Tuple[str, str]]]:
        """Score a mapping hypothesis."""
        mapping_dict = {m.source_id: m.target_id for m in mappings}

        # Count matched relations (structural match)
        matched_relations = []
        structural_score = 0.0

        for src_rel in source.relations.values():
            # Try to find matching relation in target
            mapped_args = []
            valid = True

            for arg in src_rel.arguments:
                if arg in mapping_dict:
                    mapped_args.append(mapping_dict[arg])
                else:
                    valid = False
                    break

            if not valid:
                continue

            # Look for matching relation in target
            for tgt_rel in target.relations.values():
                if (tgt_rel.name == src_rel.name and
                    tgt_rel.arguments == mapped_args):
                    matched_relations.append((src_rel.id, tgt_rel.id))
                    # Higher order relations worth more
                    structural_score += src_rel.order
                    break

        # Normalize score
        max_score = sum(r.order for r in source.relations.values())
        if max_score > 0:
            structural_score /= max_score
        else:
            structural_score = 0.5

        # Average entity confidence
        entity_score = sum(m.confidence for m in mappings) / len(mappings) if mappings else 0

        # Combine (structure > entities per SMT)
        total_score = 0.7 * structural_score + 0.3 * entity_score

        return total_score, matched_relations

    def _classify_analogy(
        self,
        source: Domain,
        target: Domain,
        mappings: List[Mapping],
        score: float
    ) -> AnalogyType:
        """Classify type of analogy."""
        # Count attribute matches
        attr_matches = 0
        for m in mappings:
            se = source.entities.get(m.source_id)
            te = target.entities.get(m.target_id)
            if se and te:
                common = set(se.attributes.keys()) & set(te.attributes.keys())
                for key in common:
                    if se.attributes[key] == te.attributes[key]:
                        attr_matches += 1

        has_structural = score > 0.5
        has_surface = attr_matches > 2

        if has_structural and has_surface:
            return AnalogyType.LITERAL_SIMILARITY
        elif has_structural and not has_surface:
            return AnalogyType.ANALOGY
        elif has_surface and not has_structural:
            return AnalogyType.MERE_APPEARANCE
        else:
            return AnalogyType.ANOMALY


# ============================================================================
# INFERENCE ENGINE
# ============================================================================

class AnalogicalInferenceEngine:
    """
    Make inferences from analogies.

    "Ba'el infers from similarity." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._inference_counter = 0
        self._lock = threading.RLock()

    def _generate_inference_id(self) -> str:
        self._inference_counter += 1
        return f"inference_{self._inference_counter}"

    def generate_inferences(
        self,
        source: Domain,
        target: Domain,
        match: StructureMatch,
        min_confidence: float = 0.3
    ) -> List[Inference]:
        """Generate inferences from structure match."""
        with self._lock:
            inferences = []

            # Build mapping dictionary
            mapping_dict = {m.source_id: m.target_id for m in match.entity_mappings}
            mapped_relations = set(r[0] for r in match.relation_mappings)

            # Find unmapped source relations
            for src_rel in source.relations.values():
                if src_rel.id in mapped_relations:
                    continue

                # Check if all arguments map
                mapped_args = []
                valid = True

                for arg in src_rel.arguments:
                    if arg in mapping_dict:
                        mapped_args.append(mapping_dict[arg])
                    else:
                        valid = False
                        break

                if not valid:
                    continue

                # Check if relation already exists in target
                exists = False
                for tgt_rel in target.relations.values():
                    if (tgt_rel.name == src_rel.name and
                        tgt_rel.arguments == mapped_args):
                        exists = True
                        break

                if exists:
                    continue

                # Generate inference
                confidence = match.score * 0.8  # Discount for inference

                if confidence >= min_confidence:
                    inferred = Relation(
                        id=f"inferred_{src_rel.id}",
                        name=src_rel.name,
                        type=src_rel.type,
                        arguments=mapped_args,
                        order=src_rel.order
                    )

                    inference = Inference(
                        id=self._generate_inference_id(),
                        source_relation=src_rel.id,
                        inferred_relation=inferred,
                        confidence=confidence,
                        basis=f"Analogy from {source.name} to {target.name}"
                    )

                    inferences.append(inference)

            return inferences


# ============================================================================
# ANALOGY RETRIEVER
# ============================================================================

class AnalogyRetriever:
    """
    Retrieve analogous domains from memory.

    "Ba'el finds similar situations." — Ba'el
    """

    def __init__(self):
        """Initialize retriever."""
        self._domains: Dict[str, Domain] = {}
        self._lock = threading.RLock()

    def store_domain(self, domain: Domain) -> None:
        """Store domain in memory."""
        with self._lock:
            self._domains[domain.id] = domain

    def retrieve_similar(
        self,
        query: Domain,
        top_k: int = 5
    ) -> List[Tuple[Domain, float]]:
        """Retrieve similar domains."""
        with self._lock:
            if not self._domains:
                return []

            scores = []

            for domain in self._domains.values():
                if domain.id == query.id:
                    continue

                # Quick similarity based on relation names
                query_rels = set(r.name for r in query.relations.values())
                domain_rels = set(r.name for r in domain.relations.values())

                overlap = len(query_rels & domain_rels)
                total = len(query_rels | domain_rels)

                if total > 0:
                    similarity = overlap / total
                    scores.append((domain, similarity))

            # Sort by similarity
            scores.sort(key=lambda x: x[1], reverse=True)

            return scores[:top_k]


# ============================================================================
# ANALOGICAL REASONING ENGINE
# ============================================================================

class AnalogicalReasoningEngine:
    """
    Complete analogical reasoning engine.

    "Ba'el reasons by analogy." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._mapper = StructureMapper()
        self._inference_engine = AnalogicalInferenceEngine()
        self._retriever = AnalogyRetriever()

        self._domain_counter = 0
        self._entity_counter = 0
        self._relation_counter = 0
        self._lock = threading.RLock()

    def _generate_domain_id(self) -> str:
        self._domain_counter += 1
        return f"domain_{self._domain_counter}"

    def _generate_entity_id(self) -> str:
        self._entity_counter += 1
        return f"entity_{self._entity_counter}"

    def _generate_relation_id(self) -> str:
        self._relation_counter += 1
        return f"rel_{self._relation_counter}"

    # Domain creation

    def create_domain(self, name: str) -> Domain:
        """Create new domain."""
        return Domain(
            id=self._generate_domain_id(),
            name=name
        )

    def create_entity(
        self,
        name: str,
        attributes: Dict[str, Any] = None
    ) -> Entity:
        """Create entity."""
        return Entity(
            id=self._generate_entity_id(),
            name=name,
            attributes=attributes or {}
        )

    def create_relation(
        self,
        name: str,
        arguments: List[str],
        type: RelationType = RelationType.FUNCTION,
        order: int = 1
    ) -> Relation:
        """Create relation."""
        return Relation(
            id=self._generate_relation_id(),
            name=name,
            type=type,
            arguments=arguments,
            order=order
        )

    # Analogical mapping

    def find_analogy(
        self,
        source: Domain,
        target: Domain
    ) -> Optional[StructureMatch]:
        """Find best analogy between domains."""
        matches = self._mapper.find_matches(source, target)
        return matches[0] if matches else None

    def find_all_analogies(
        self,
        source: Domain,
        target: Domain,
        min_score: float = 0.3
    ) -> List[StructureMatch]:
        """Find all analogies."""
        return self._mapper.find_matches(source, target, min_score)

    # Inference

    def make_inferences(
        self,
        source: Domain,
        target: Domain,
        match: StructureMatch
    ) -> List[Inference]:
        """Generate inferences from analogy."""
        return self._inference_engine.generate_inferences(source, target, match)

    # Memory

    def store_domain(self, domain: Domain) -> None:
        """Store domain for later retrieval."""
        self._retriever.store_domain(domain)

    def find_similar_domains(
        self,
        query: Domain,
        top_k: int = 5
    ) -> List[Tuple[Domain, float]]:
        """Find similar domains from memory."""
        return self._retriever.retrieve_similar(query, top_k)

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'domains_stored': len(self._retriever._domains),
            'domains_created': self._domain_counter,
            'entities_created': self._entity_counter,
            'relations_created': self._relation_counter
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_analogical_reasoning_engine() -> AnalogicalReasoningEngine:
    """Create analogical reasoning engine."""
    return AnalogicalReasoningEngine()


def find_analogy(
    source_entities: List[Dict[str, Any]],
    source_relations: List[Dict[str, Any]],
    target_entities: List[Dict[str, Any]],
    target_relations: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """Find analogy between simple domain representations."""
    engine = create_analogical_reasoning_engine()

    # Build source domain
    source = engine.create_domain("source")
    entity_map_s = {}
    for e in source_entities:
        entity = engine.create_entity(e['name'], e.get('attributes', {}))
        source.add_entity(entity)
        entity_map_s[e['name']] = entity.id

    for r in source_relations:
        args = [entity_map_s[a] for a in r['arguments']]
        rel = engine.create_relation(r['name'], args)
        source.add_relation(rel)

    # Build target domain
    target = engine.create_domain("target")
    entity_map_t = {}
    for e in target_entities:
        entity = engine.create_entity(e['name'], e.get('attributes', {}))
        target.add_entity(entity)
        entity_map_t[e['name']] = entity.id

    for r in target_relations:
        args = [entity_map_t[a] for a in r['arguments']]
        rel = engine.create_relation(r['name'], args)
        target.add_relation(rel)

    # Find analogy
    match = engine.find_analogy(source, target)

    if match:
        return {
            'score': match.score,
            'type': match.analogy_type.name,
            'mappings': [
                {'source': m.source_id, 'target': m.target_id}
                for m in match.entity_mappings
            ]
        }

    return None
