"""
BAEL Analogical Mapping Engine
================================

Structure mapping theory.
Gentner's analogical reasoning.

"Ba'el maps structures across domains." — Ba'el
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

logger = logging.getLogger("BAEL.AnalogicalMapping")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class RelationType(Enum):
    """Types of relations in structure mapping."""
    ATTRIBUTE = auto()         # Property of an object
    FIRST_ORDER = auto()       # Relation between objects
    HIGHER_ORDER = auto()      # Relation between relations


class MappingType(Enum):
    """Types of analogical mappings."""
    LITERAL_SIMILARITY = auto()   # Objects and relations match
    ANALOGY = auto()               # Relations match, objects differ
    MERE_APPEARANCE = auto()       # Objects match, relations differ
    ANOMALY = auto()               # Neither match


class ConstraintType(Enum):
    """SMT constraints on mappings."""
    STRUCTURAL_CONSISTENCY = auto()  # One-to-one mapping
    PARALLEL_CONNECTIVITY = auto()   # Connected elements map together
    SYSTEMATICITY = auto()           # Prefer higher-order relations


@dataclass
class Entity:
    """
    An entity in a domain.
    """
    id: str
    name: str
    attributes: Dict[str, Any]


@dataclass
class Relation:
    """
    A relation between entities.
    """
    id: str
    name: str
    arguments: List[str]  # Entity IDs
    relation_type: RelationType
    parent_relation: Optional[str] = None  # For higher-order


@dataclass
class Domain:
    """
    A domain with entities and relations.
    """
    id: str
    name: str
    entities: Dict[str, Entity]
    relations: Dict[str, Relation]


@dataclass
class Correspondence:
    """
    A correspondence between elements.
    """
    source_id: str
    target_id: str
    element_type: str  # 'entity' or 'relation'
    strength: float


@dataclass
class StructuralAlignment:
    """
    Complete structural alignment.
    """
    correspondences: List[Correspondence]
    structural_evaluation: float
    systematicity_score: float
    mapping_type: MappingType


@dataclass
class AnalogicalInference:
    """
    An inference from analogy.
    """
    source_fact: str
    inferred_fact: str
    confidence: float
    justification: str


@dataclass
class MappingMetrics:
    """
    Mapping quality metrics.
    """
    structural_match: float
    relational_match: float
    systematicity: float
    inference_quality: float


# ============================================================================
# DOMAIN REPRESENTATION
# ============================================================================

class DomainBuilder:
    """
    Builds domain representations.

    "Ba'el constructs knowledge structures." — Ba'el
    """

    def __init__(self):
        """Initialize builder."""
        self._entity_counter = 0
        self._relation_counter = 0

        self._lock = threading.RLock()

    def _generate_entity_id(self) -> str:
        self._entity_counter += 1
        return f"e_{self._entity_counter}"

    def _generate_relation_id(self) -> str:
        self._relation_counter += 1
        return f"r_{self._relation_counter}"

    def create_domain(
        self,
        name: str
    ) -> Domain:
        """Create a new domain."""
        return Domain(
            id=f"domain_{name}",
            name=name,
            entities={},
            relations={}
        )

    def add_entity(
        self,
        domain: Domain,
        name: str,
        attributes: Dict[str, Any] = None
    ) -> Entity:
        """Add entity to domain."""
        entity = Entity(
            id=self._generate_entity_id(),
            name=name,
            attributes=attributes or {}
        )
        domain.entities[entity.id] = entity
        return entity

    def add_relation(
        self,
        domain: Domain,
        name: str,
        arguments: List[Entity],
        relation_type: RelationType = RelationType.FIRST_ORDER,
        parent: Relation = None
    ) -> Relation:
        """Add relation to domain."""
        relation = Relation(
            id=self._generate_relation_id(),
            name=name,
            arguments=[e.id for e in arguments],
            relation_type=relation_type,
            parent_relation=parent.id if parent else None
        )
        domain.relations[relation.id] = relation
        return relation


# ============================================================================
# STRUCTURE MAPPING ENGINE
# ============================================================================

class StructureMappingEngine:
    """
    Gentner's Structure Mapping Theory.

    "Ba'el aligns structures." — Ba'el
    """

    def __init__(self):
        """Initialize SME."""
        # Constraint weights
        self._weights = {
            ConstraintType.STRUCTURAL_CONSISTENCY: 1.0,
            ConstraintType.PARALLEL_CONNECTIVITY: 0.8,
            ConstraintType.SYSTEMATICITY: 1.2
        }

        self._lock = threading.RLock()

    def find_alignments(
        self,
        source: Domain,
        target: Domain
    ) -> List[StructuralAlignment]:
        """Find structural alignments between domains."""
        # Find all possible correspondences
        entity_correspondences = self._find_entity_correspondences(source, target)
        relation_correspondences = self._find_relation_correspondences(source, target)

        # Build consistent alignments
        alignments = self._build_alignments(
            source, target,
            entity_correspondences,
            relation_correspondences
        )

        # Score and sort alignments
        scored_alignments = []
        for alignment in alignments:
            evaluation = self._evaluate_alignment(alignment, source, target)
            alignment.structural_evaluation = evaluation
            alignment.systematicity_score = self._calculate_systematicity(alignment, source)
            alignment.mapping_type = self._classify_mapping(alignment, source, target)
            scored_alignments.append(alignment)

        scored_alignments.sort(key=lambda a: a.structural_evaluation, reverse=True)

        return scored_alignments

    def _find_entity_correspondences(
        self,
        source: Domain,
        target: Domain
    ) -> List[Correspondence]:
        """Find potential entity correspondences."""
        correspondences = []

        for s_entity in source.entities.values():
            for t_entity in target.entities.values():
                # Calculate match strength based on attributes
                strength = self._calculate_attribute_match(s_entity, t_entity)

                correspondences.append(Correspondence(
                    source_id=s_entity.id,
                    target_id=t_entity.id,
                    element_type='entity',
                    strength=strength
                ))

        return correspondences

    def _find_relation_correspondences(
        self,
        source: Domain,
        target: Domain
    ) -> List[Correspondence]:
        """Find potential relation correspondences."""
        correspondences = []

        for s_rel in source.relations.values():
            for t_rel in target.relations.values():
                # Relations must have same name or similar semantics
                if s_rel.name == t_rel.name:
                    strength = 1.0
                else:
                    # Could add semantic similarity here
                    strength = 0.3

                # Same arity required
                if len(s_rel.arguments) != len(t_rel.arguments):
                    continue

                correspondences.append(Correspondence(
                    source_id=s_rel.id,
                    target_id=t_rel.id,
                    element_type='relation',
                    strength=strength
                ))

        return correspondences

    def _calculate_attribute_match(
        self,
        e1: Entity,
        e2: Entity
    ) -> float:
        """Calculate attribute match between entities."""
        if not e1.attributes and not e2.attributes:
            return 0.5

        matching = 0
        total = 0

        for key in set(e1.attributes.keys()) | set(e2.attributes.keys()):
            total += 1
            if e1.attributes.get(key) == e2.attributes.get(key):
                matching += 1

        return matching / total if total > 0 else 0.5

    def _build_alignments(
        self,
        source: Domain,
        target: Domain,
        entity_corrs: List[Correspondence],
        relation_corrs: List[Correspondence]
    ) -> List[StructuralAlignment]:
        """Build consistent alignments."""
        alignments = []

        # Start with relation correspondences (systematicity preference)
        for rel_corr in relation_corrs:
            if rel_corr.strength < 0.3:
                continue

            # Find supporting entity correspondences
            s_rel = source.relations[rel_corr.source_id]
            t_rel = target.relations[rel_corr.target_id]

            supporting_entity_corrs = []
            valid = True

            for i, (s_arg, t_arg) in enumerate(zip(s_rel.arguments, t_rel.arguments)):
                # Find entity correspondence
                entity_corr = None
                for ec in entity_corrs:
                    if ec.source_id == s_arg and ec.target_id == t_arg:
                        entity_corr = ec
                        break

                if entity_corr:
                    supporting_entity_corrs.append(entity_corr)
                else:
                    # Create new correspondence
                    supporting_entity_corrs.append(Correspondence(
                        source_id=s_arg,
                        target_id=t_arg,
                        element_type='entity',
                        strength=0.5
                    ))

            if valid:
                alignment = StructuralAlignment(
                    correspondences=[rel_corr] + supporting_entity_corrs,
                    structural_evaluation=0.0,
                    systematicity_score=0.0,
                    mapping_type=MappingType.ANALOGY
                )
                alignments.append(alignment)

        return alignments if alignments else [
            StructuralAlignment(
                correspondences=[],
                structural_evaluation=0.0,
                systematicity_score=0.0,
                mapping_type=MappingType.ANOMALY
            )
        ]

    def _evaluate_alignment(
        self,
        alignment: StructuralAlignment,
        source: Domain,
        target: Domain
    ) -> float:
        """Evaluate alignment quality."""
        if not alignment.correspondences:
            return 0.0

        # Sum correspondence strengths
        total_strength = sum(c.strength for c in alignment.correspondences)

        # Check one-to-one constraint
        source_ids = [c.source_id for c in alignment.correspondences]
        target_ids = [c.target_id for c in alignment.correspondences]

        if len(source_ids) != len(set(source_ids)) or len(target_ids) != len(set(target_ids)):
            total_strength *= 0.5  # Penalty for violations

        return total_strength / len(alignment.correspondences)

    def _calculate_systematicity(
        self,
        alignment: StructuralAlignment,
        source: Domain
    ) -> float:
        """Calculate systematicity score."""
        relation_corrs = [
            c for c in alignment.correspondences
            if c.element_type == 'relation'
        ]

        if not relation_corrs:
            return 0.0

        # Higher-order relations get bonus
        score = 0.0
        for corr in relation_corrs:
            rel = source.relations.get(corr.source_id)
            if rel:
                if rel.relation_type == RelationType.HIGHER_ORDER:
                    score += 2.0
                elif rel.relation_type == RelationType.FIRST_ORDER:
                    score += 1.0
                else:
                    score += 0.5

        return score / len(relation_corrs)

    def _classify_mapping(
        self,
        alignment: StructuralAlignment,
        source: Domain,
        target: Domain
    ) -> MappingType:
        """Classify the type of mapping."""
        entity_match = sum(
            c.strength for c in alignment.correspondences
            if c.element_type == 'entity'
        )
        relation_match = sum(
            c.strength for c in alignment.correspondences
            if c.element_type == 'relation'
        )

        n_entity = len([c for c in alignment.correspondences if c.element_type == 'entity'])
        n_relation = len([c for c in alignment.correspondences if c.element_type == 'relation'])

        entity_ratio = entity_match / n_entity if n_entity > 0 else 0
        relation_ratio = relation_match / n_relation if n_relation > 0 else 0

        if entity_ratio > 0.7 and relation_ratio > 0.7:
            return MappingType.LITERAL_SIMILARITY
        elif relation_ratio > 0.7:
            return MappingType.ANALOGY
        elif entity_ratio > 0.7:
            return MappingType.MERE_APPEARANCE
        else:
            return MappingType.ANOMALY


# ============================================================================
# INFERENCE ENGINE
# ============================================================================

class AnalogicalInferenceEngine:
    """
    Makes inferences from analogies.

    "Ba'el infers from structure." — Ba'el
    """

    def __init__(self):
        """Initialize inference engine."""
        self._lock = threading.RLock()

    def generate_inferences(
        self,
        alignment: StructuralAlignment,
        source: Domain,
        target: Domain
    ) -> List[AnalogicalInference]:
        """Generate inferences from alignment."""
        inferences = []

        # Find unmapped relations in source
        mapped_source_rels = {
            c.source_id for c in alignment.correspondences
            if c.element_type == 'relation'
        }

        # Entity mapping
        entity_map = {}
        for c in alignment.correspondences:
            if c.element_type == 'entity':
                entity_map[c.source_id] = c.target_id

        for rel_id, relation in source.relations.items():
            if rel_id in mapped_source_rels:
                continue

            # Check if we can map all arguments
            can_infer = True
            mapped_args = []

            for arg_id in relation.arguments:
                if arg_id in entity_map:
                    mapped_args.append(entity_map[arg_id])
                else:
                    can_infer = False
                    break

            if can_infer:
                # Get entity names for readability
                source_entities = [source.entities[a].name for a in relation.arguments]
                target_entities = [target.entities[a].name for a in mapped_args]

                source_fact = f"{relation.name}({', '.join(source_entities)})"
                inferred_fact = f"{relation.name}({', '.join(target_entities)})"

                inference = AnalogicalInference(
                    source_fact=source_fact,
                    inferred_fact=inferred_fact,
                    confidence=alignment.structural_evaluation * 0.8,
                    justification=f"Transferred from source via structural alignment"
                )
                inferences.append(inference)

        return inferences


# ============================================================================
# ANALOGICAL MAPPING ENGINE
# ============================================================================

class AnalogicalMappingEngine:
    """
    Complete analogical mapping engine.

    "Ba'el's analogical reasoning." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._builder = DomainBuilder()
        self._sme = StructureMappingEngine()
        self._inference = AnalogicalInferenceEngine()

        self._domains: Dict[str, Domain] = {}
        self._alignments: List[StructuralAlignment] = []

        self._lock = threading.RLock()

    # Domain construction

    def create_domain(
        self,
        name: str
    ) -> Domain:
        """Create a new domain."""
        domain = self._builder.create_domain(name)
        self._domains[domain.id] = domain
        return domain

    def add_entity(
        self,
        domain: Domain,
        name: str,
        **attributes
    ) -> Entity:
        """Add entity to domain."""
        return self._builder.add_entity(domain, name, attributes)

    def add_relation(
        self,
        domain: Domain,
        name: str,
        *entities: Entity,
        relation_type: RelationType = RelationType.FIRST_ORDER
    ) -> Relation:
        """Add relation to domain."""
        return self._builder.add_relation(
            domain, name, list(entities), relation_type
        )

    # Alignment and inference

    def find_alignment(
        self,
        source: Domain,
        target: Domain
    ) -> StructuralAlignment:
        """Find best structural alignment."""
        alignments = self._sme.find_alignments(source, target)

        if alignments:
            best = alignments[0]
            self._alignments.append(best)
            return best

        return StructuralAlignment(
            correspondences=[],
            structural_evaluation=0.0,
            systematicity_score=0.0,
            mapping_type=MappingType.ANOMALY
        )

    def make_inferences(
        self,
        alignment: StructuralAlignment,
        source: Domain,
        target: Domain
    ) -> List[AnalogicalInference]:
        """Make inferences from alignment."""
        return self._inference.generate_inferences(alignment, source, target)

    # Classic analogies

    def create_solar_system_domain(self) -> Domain:
        """Create solar system domain (classic analogy)."""
        domain = self.create_domain("solar_system")

        sun = self.add_entity(domain, "sun", type="star", mass="large")
        planet = self.add_entity(domain, "planet", type="planet", mass="small")

        self.add_relation(domain, "more_massive", sun, planet)
        self.add_relation(domain, "attracts", sun, planet)
        revolves = self.add_relation(domain, "revolves_around", planet, sun)

        # Higher-order: attraction causes revolution
        self.add_relation(
            domain, "causes", sun, planet,
            relation_type=RelationType.HIGHER_ORDER
        )

        return domain

    def create_atom_domain(self) -> Domain:
        """Create atom domain (target of solar system analogy)."""
        domain = self.create_domain("atom")

        nucleus = self.add_entity(domain, "nucleus", type="nucleus", mass="large")
        electron = self.add_entity(domain, "electron", type="electron", mass="small")

        self.add_relation(domain, "more_massive", nucleus, electron)
        self.add_relation(domain, "attracts", nucleus, electron)
        self.add_relation(domain, "revolves_around", electron, nucleus)

        return domain

    def demonstrate_rutherford_analogy(self) -> Dict[str, Any]:
        """Demonstrate Rutherford's solar system-atom analogy."""
        solar = self.create_solar_system_domain()
        atom = self.create_atom_domain()

        alignment = self.find_alignment(solar, atom)
        inferences = self.make_inferences(alignment, solar, atom)

        return {
            'source': 'solar_system',
            'target': 'atom',
            'mapping_type': alignment.mapping_type.name,
            'structural_evaluation': alignment.structural_evaluation,
            'systematicity': alignment.systematicity_score,
            'correspondences': [
                {
                    'source': c.source_id,
                    'target': c.target_id,
                    'type': c.element_type,
                    'strength': c.strength
                }
                for c in alignment.correspondences
            ],
            'inferences': [
                {
                    'source_fact': inf.source_fact,
                    'inferred': inf.inferred_fact,
                    'confidence': inf.confidence
                }
                for inf in inferences
            ]
        }

    # Metrics

    def get_metrics(self) -> MappingMetrics:
        """Get mapping metrics."""
        if not self._alignments:
            return MappingMetrics(
                structural_match=0.0,
                relational_match=0.0,
                systematicity=0.0,
                inference_quality=0.0
            )

        avg_structural = sum(a.structural_evaluation for a in self._alignments) / len(self._alignments)
        avg_systematicity = sum(a.systematicity_score for a in self._alignments) / len(self._alignments)

        # Relational match: ratio of relation correspondences
        rel_ratios = []
        for a in self._alignments:
            n_rel = len([c for c in a.correspondences if c.element_type == 'relation'])
            n_total = len(a.correspondences)
            if n_total > 0:
                rel_ratios.append(n_rel / n_total)

        avg_relational = sum(rel_ratios) / len(rel_ratios) if rel_ratios else 0

        return MappingMetrics(
            structural_match=avg_structural,
            relational_match=avg_relational,
            systematicity=avg_systematicity,
            inference_quality=avg_systematicity * avg_structural
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'domains': len(self._domains),
            'alignments': len(self._alignments)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_analogical_mapping_engine() -> AnalogicalMappingEngine:
    """Create analogical mapping engine."""
    return AnalogicalMappingEngine()


def demonstrate_analogical_mapping() -> Dict[str, Any]:
    """Demonstrate analogical mapping."""
    engine = create_analogical_mapping_engine()

    # Rutherford analogy
    rutherford = engine.demonstrate_rutherford_analogy()

    metrics = engine.get_metrics()

    return {
        'rutherford_analogy': {
            'mapping_type': rutherford['mapping_type'],
            'structural_match': f"{rutherford['structural_evaluation']:.2f}",
            'systematicity': f"{rutherford['systematicity']:.2f}",
            'n_correspondences': len(rutherford['correspondences']),
            'n_inferences': len(rutherford['inferences'])
        },
        'metrics': {
            'structural_match': f"{metrics.structural_match:.2f}",
            'relational_match': f"{metrics.relational_match:.2f}",
            'systematicity': f"{metrics.systematicity:.2f}"
        },
        'interpretation': (
            f"Solar system → Atom is a {rutherford['mapping_type']} mapping. "
            f"Systematicity score: {rutherford['systematicity']:.2f}"
        )
    }


def get_analogical_mapping_facts() -> Dict[str, str]:
    """Get facts about analogical mapping."""
    return {
        'gentner_smt': 'Structure Mapping Theory: analogy = relational structure match',
        'systematicity': 'Prefer mappings of interconnected relation systems',
        'one_to_one': 'Each element maps to exactly one target element',
        'parallel_connectivity': 'Connected elements map together',
        'relational_shift': 'Development moves from appearance to relational matching',
        'analogical_inference': 'Transfer unmapped predicates from source to target',
        'base_target': 'Source (base) is better known than target',
        'surface_structure': 'Distinguish surface attributes from deep relations'
    }
