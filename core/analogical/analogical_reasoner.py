#!/usr/bin/env python3
"""
BAEL - Analogical Reasoner
Advanced analogical reasoning and case-based learning.

Features:
- Structural mapping
- Analogical retrieval
- Case-based reasoning
- Structure mapping engine
- Relational similarity
- Analogical inference
- Transfer learning via analogy
- Cross-domain mapping
"""

import asyncio
import hashlib
import math
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ElementType(Enum):
    """Types of elements in analogy."""
    OBJECT = "object"
    ATTRIBUTE = "attribute"
    RELATION = "relation"
    HIGHER_ORDER = "higher_order"


class MappingType(Enum):
    """Types of analogical mappings."""
    ONE_TO_ONE = "one_to_one"
    PARTIAL = "partial"
    SYSTEMATIC = "systematic"


class SimilarityType(Enum):
    """Types of similarity."""
    SURFACE = "surface"  # Based on attributes
    STRUCTURAL = "structural"  # Based on relations
    SEMANTIC = "semantic"  # Based on meaning
    FUNCTIONAL = "functional"  # Based on purpose


class RetrievalMethod(Enum):
    """Methods for case retrieval."""
    MAC_FAC = "mac_fac"  # Many Are Called, Few Are Chosen
    NEAREST_NEIGHBOR = "nearest_neighbor"
    STRUCTURAL = "structural"


class AdaptationType(Enum):
    """Types of adaptation."""
    NULL = "null"  # No adaptation
    SUBSTITUTION = "substitution"
    TRANSFORMATION = "transformation"
    ABSTRACTION = "abstraction"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Element:
    """An element in an analogical structure."""
    element_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    element_type: ElementType = ElementType.OBJECT
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Relation:
    """A relation between elements."""
    relation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    arguments: List[str] = field(default_factory=list)  # Element IDs
    is_higher_order: bool = False
    order: int = 1


@dataclass
class AnalogicalStructure:
    """A structure for analogical reasoning."""
    structure_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    domain: str = ""
    elements: Dict[str, Element] = field(default_factory=dict)
    relations: List[Relation] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Mapping:
    """A mapping between two structures."""
    mapping_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: str = ""  # Source structure ID
    target: str = ""  # Target structure ID
    element_mappings: Dict[str, str] = field(default_factory=dict)
    relation_mappings: Dict[str, str] = field(default_factory=dict)
    score: float = 0.0
    mapping_type: MappingType = MappingType.SYSTEMATIC


@dataclass
class Case:
    """A case for case-based reasoning."""
    case_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    problem: AnalogicalStructure = field(default_factory=AnalogicalStructure)
    solution: Dict[str, Any] = field(default_factory=dict)
    outcome: Optional[Any] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class Inference:
    """An analogical inference."""
    inference_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_relation: Relation = field(default_factory=Relation)
    inferred_relation: Relation = field(default_factory=Relation)
    confidence: float = 0.0
    mapping: Optional[Mapping] = None


# =============================================================================
# STRUCTURE BUILDER
# =============================================================================

class StructureBuilder:
    """Build analogical structures."""

    def __init__(self):
        self._current: Optional[AnalogicalStructure] = None

    def new_structure(
        self,
        name: str,
        domain: str = ""
    ) -> AnalogicalStructure:
        """Create new structure."""
        self._current = AnalogicalStructure(name=name, domain=domain)
        return self._current

    def add_object(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Element:
        """Add an object element."""
        if not self._current:
            raise ValueError("No current structure")

        element = Element(
            name=name,
            element_type=ElementType.OBJECT,
            attributes=attributes or {}
        )
        self._current.elements[element.element_id] = element
        return element

    def add_relation(
        self,
        name: str,
        *args: Element,
        is_higher_order: bool = False
    ) -> Relation:
        """Add a relation."""
        if not self._current:
            raise ValueError("No current structure")

        arg_ids = [e.element_id if isinstance(e, Element) else str(e) for e in args]

        relation = Relation(
            name=name,
            arguments=arg_ids,
            is_higher_order=is_higher_order,
            order=2 if is_higher_order else 1
        )
        self._current.relations.append(relation)
        return relation

    def build(self) -> AnalogicalStructure:
        """Finalize and return structure."""
        result = self._current
        self._current = None
        return result if result else AnalogicalStructure()


# =============================================================================
# STRUCTURE MAPPING ENGINE (SME)
# =============================================================================

class StructureMappingEngine:
    """Structure Mapping Engine for analogical reasoning."""

    def __init__(self):
        self._systematicity_weight = 1.5

    def find_mappings(
        self,
        source: AnalogicalStructure,
        target: AnalogicalStructure
    ) -> List[Mapping]:
        """Find all valid mappings between structures."""
        # Match relations
        relation_matches = self._match_relations(source, target)

        # Build consistent mappings
        mappings = self._build_consistent_mappings(
            source, target, relation_matches
        )

        # Score mappings
        for mapping in mappings:
            mapping.score = self._score_mapping(mapping, source, target)

        # Sort by score
        mappings.sort(key=lambda m: m.score, reverse=True)

        return mappings

    def _match_relations(
        self,
        source: AnalogicalStructure,
        target: AnalogicalStructure
    ) -> List[Tuple[Relation, Relation]]:
        """Find matching relations."""
        matches = []

        for s_rel in source.relations:
            for t_rel in target.relations:
                if self._relations_match(s_rel, t_rel):
                    matches.append((s_rel, t_rel))

        return matches

    def _relations_match(
        self,
        rel1: Relation,
        rel2: Relation
    ) -> bool:
        """Check if two relations can match."""
        # Same name and arity
        if rel1.name != rel2.name:
            return False
        if len(rel1.arguments) != len(rel2.arguments):
            return False
        return True

    def _build_consistent_mappings(
        self,
        source: AnalogicalStructure,
        target: AnalogicalStructure,
        relation_matches: List[Tuple[Relation, Relation]]
    ) -> List[Mapping]:
        """Build consistent mappings from relation matches."""
        if not relation_matches:
            return []

        # Start with each relation match as a seed
        mappings = []

        for s_rel, t_rel in relation_matches:
            mapping = Mapping(
                source=source.structure_id,
                target=target.structure_id,
                mapping_type=MappingType.SYSTEMATIC
            )

            # Add relation mapping
            mapping.relation_mappings[s_rel.relation_id] = t_rel.relation_id

            # Add element mappings
            for s_arg, t_arg in zip(s_rel.arguments, t_rel.arguments):
                if s_arg in mapping.element_mappings:
                    if mapping.element_mappings[s_arg] != t_arg:
                        continue  # Inconsistent, skip
                mapping.element_mappings[s_arg] = t_arg

            mappings.append(mapping)

        # Merge compatible mappings
        merged = self._merge_mappings(mappings)

        return merged

    def _merge_mappings(
        self,
        mappings: List[Mapping]
    ) -> List[Mapping]:
        """Merge compatible mappings."""
        if not mappings:
            return []

        merged = [mappings[0]]

        for mapping in mappings[1:]:
            merged_with_existing = False

            for existing in merged:
                if self._mappings_compatible(existing, mapping):
                    # Merge into existing
                    existing.element_mappings.update(mapping.element_mappings)
                    existing.relation_mappings.update(mapping.relation_mappings)
                    merged_with_existing = True
                    break

            if not merged_with_existing:
                merged.append(mapping)

        return merged

    def _mappings_compatible(
        self,
        m1: Mapping,
        m2: Mapping
    ) -> bool:
        """Check if two mappings are compatible."""
        # Check one-to-one constraint
        for s, t in m2.element_mappings.items():
            if s in m1.element_mappings:
                if m1.element_mappings[s] != t:
                    return False
        return True

    def _score_mapping(
        self,
        mapping: Mapping,
        source: AnalogicalStructure,
        target: AnalogicalStructure
    ) -> float:
        """Score a mapping based on systematicity."""
        score = 0.0

        # Count matched relations
        num_relations = len(mapping.relation_mappings)
        score += num_relations

        # Bonus for higher-order relations
        for s_rel_id in mapping.relation_mappings:
            for rel in source.relations:
                if rel.relation_id == s_rel_id and rel.is_higher_order:
                    score += self._systematicity_weight

        # Bonus for connected structure
        connected = self._count_connected_relations(mapping, source)
        score += connected * 0.5

        return score

    def _count_connected_relations(
        self,
        mapping: Mapping,
        source: AnalogicalStructure
    ) -> int:
        """Count connected relation pairs."""
        count = 0
        mapped_rels = list(mapping.relation_mappings.keys())

        for i, rel1_id in enumerate(mapped_rels):
            for rel2_id in mapped_rels[i+1:]:
                # Find relations
                rel1 = rel2 = None
                for rel in source.relations:
                    if rel.relation_id == rel1_id:
                        rel1 = rel
                    if rel.relation_id == rel2_id:
                        rel2 = rel

                if rel1 and rel2:
                    # Check if they share arguments
                    if set(rel1.arguments) & set(rel2.arguments):
                        count += 1

        return count


# =============================================================================
# SIMILARITY CALCULATOR
# =============================================================================

class SimilarityCalculator:
    """Calculate various types of similarity."""

    def surface_similarity(
        self,
        s1: AnalogicalStructure,
        s2: AnalogicalStructure
    ) -> float:
        """Calculate surface (attribute-based) similarity."""
        total_attrs = 0
        matching_attrs = 0

        for e1 in s1.elements.values():
            for e2 in s2.elements.values():
                common_attrs = set(e1.attributes.keys()) & set(e2.attributes.keys())
                total_attrs += len(e1.attributes)

                for attr in common_attrs:
                    if e1.attributes[attr] == e2.attributes[attr]:
                        matching_attrs += 1

        return matching_attrs / total_attrs if total_attrs > 0 else 0.0

    def structural_similarity(
        self,
        s1: AnalogicalStructure,
        s2: AnalogicalStructure
    ) -> float:
        """Calculate structural (relation-based) similarity."""
        rel_names1 = {r.name for r in s1.relations}
        rel_names2 = {r.name for r in s2.relations}

        intersection = len(rel_names1 & rel_names2)
        union = len(rel_names1 | rel_names2)

        return intersection / union if union > 0 else 0.0

    def combined_similarity(
        self,
        s1: AnalogicalStructure,
        s2: AnalogicalStructure,
        surface_weight: float = 0.3,
        structural_weight: float = 0.7
    ) -> float:
        """Calculate combined similarity."""
        surface = self.surface_similarity(s1, s2)
        structural = self.structural_similarity(s1, s2)

        return surface_weight * surface + structural_weight * structural


# =============================================================================
# CASE BASE
# =============================================================================

class CaseBase:
    """Store and retrieve cases."""

    def __init__(self):
        self._cases: Dict[str, Case] = {}
        self._index: Dict[str, List[str]] = defaultdict(list)  # Feature -> Case IDs

    def add_case(self, case: Case) -> None:
        """Add a case to the base."""
        self._cases[case.case_id] = case

        # Index by relation names
        for rel in case.problem.relations:
            self._index[rel.name].append(case.case_id)

    def get_case(self, case_id: str) -> Optional[Case]:
        """Get a case by ID."""
        return self._cases.get(case_id)

    def retrieve(
        self,
        query: AnalogicalStructure,
        method: RetrievalMethod = RetrievalMethod.MAC_FAC,
        top_k: int = 5
    ) -> List[Tuple[Case, float]]:
        """Retrieve similar cases."""
        if method == RetrievalMethod.MAC_FAC:
            return self._mac_fac_retrieve(query, top_k)
        elif method == RetrievalMethod.NEAREST_NEIGHBOR:
            return self._nn_retrieve(query, top_k)
        else:
            return self._structural_retrieve(query, top_k)

    def _mac_fac_retrieve(
        self,
        query: AnalogicalStructure,
        top_k: int
    ) -> List[Tuple[Case, float]]:
        """MAC/FAC: Many Are Called, Few Are Chosen."""
        # MAC: Quick surface matching
        candidates = set()
        for rel in query.relations:
            candidates.update(self._index.get(rel.name, []))

        # FAC: Detailed structural comparison
        sim_calc = SimilarityCalculator()
        sme = StructureMappingEngine()

        scored = []
        for case_id in candidates:
            case = self._cases.get(case_id)
            if case:
                # Structural similarity via SME
                mappings = sme.find_mappings(case.problem, query)
                score = mappings[0].score if mappings else 0
                scored.append((case, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def _nn_retrieve(
        self,
        query: AnalogicalStructure,
        top_k: int
    ) -> List[Tuple[Case, float]]:
        """Nearest neighbor retrieval."""
        sim_calc = SimilarityCalculator()

        scored = []
        for case in self._cases.values():
            sim = sim_calc.combined_similarity(case.problem, query)
            scored.append((case, sim))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def _structural_retrieve(
        self,
        query: AnalogicalStructure,
        top_k: int
    ) -> List[Tuple[Case, float]]:
        """Pure structural retrieval."""
        sim_calc = SimilarityCalculator()

        scored = []
        for case in self._cases.values():
            sim = sim_calc.structural_similarity(case.problem, query)
            scored.append((case, sim))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]


# =============================================================================
# ANALOGICAL INFERENCE ENGINE
# =============================================================================

class AnalogicalInferenceEngine:
    """Generate inferences through analogy."""

    def __init__(self):
        self._sme = StructureMappingEngine()

    def infer(
        self,
        source: AnalogicalStructure,
        target: AnalogicalStructure,
        mapping: Optional[Mapping] = None
    ) -> List[Inference]:
        """Generate analogical inferences."""
        # Find mapping if not provided
        if not mapping:
            mappings = self._sme.find_mappings(source, target)
            if not mappings:
                return []
            mapping = mappings[0]

        inferences = []

        # Find unmapped source relations
        mapped_rel_ids = set(mapping.relation_mappings.keys())

        for rel in source.relations:
            if rel.relation_id not in mapped_rel_ids:
                # Try to project this relation to target
                inferred_rel = self._project_relation(rel, mapping, target)
                if inferred_rel:
                    inference = Inference(
                        source_relation=rel,
                        inferred_relation=inferred_rel,
                        confidence=self._compute_confidence(rel, mapping),
                        mapping=mapping
                    )
                    inferences.append(inference)

        return inferences

    def _project_relation(
        self,
        relation: Relation,
        mapping: Mapping,
        target: AnalogicalStructure
    ) -> Optional[Relation]:
        """Project a relation to target domain."""
        # Map arguments
        new_args = []
        for arg in relation.arguments:
            if arg in mapping.element_mappings:
                new_args.append(mapping.element_mappings[arg])
            else:
                return None  # Can't project without argument mapping

        return Relation(
            name=relation.name,
            arguments=new_args,
            is_higher_order=relation.is_higher_order,
            order=relation.order
        )

    def _compute_confidence(
        self,
        relation: Relation,
        mapping: Mapping
    ) -> float:
        """Compute confidence in inference."""
        base_confidence = 0.5

        # Higher confidence for higher-order relations
        if relation.is_higher_order:
            base_confidence += 0.2

        # Scale by mapping quality
        base_confidence *= min(mapping.score / 5.0, 1.0)

        return min(base_confidence, 1.0)


# =============================================================================
# ADAPTATION ENGINE
# =============================================================================

class AdaptationEngine:
    """Adapt retrieved solutions."""

    def adapt(
        self,
        source_case: Case,
        target_problem: AnalogicalStructure,
        mapping: Mapping,
        method: AdaptationType = AdaptationType.SUBSTITUTION
    ) -> Dict[str, Any]:
        """Adapt source solution to target problem."""
        if method == AdaptationType.NULL:
            return dict(source_case.solution)

        elif method == AdaptationType.SUBSTITUTION:
            return self._substitute(source_case, mapping)

        elif method == AdaptationType.TRANSFORMATION:
            return self._transform(source_case, target_problem, mapping)

        elif method == AdaptationType.ABSTRACTION:
            return self._abstract_adapt(source_case, target_problem)

        return dict(source_case.solution)

    def _substitute(
        self,
        source_case: Case,
        mapping: Mapping
    ) -> Dict[str, Any]:
        """Substitution-based adaptation."""
        solution = {}

        for key, value in source_case.solution.items():
            # Check if key is a mapped element
            if key in mapping.element_mappings:
                new_key = mapping.element_mappings[key]
            else:
                new_key = key

            # Check if value is a mapped element
            if isinstance(value, str) and value in mapping.element_mappings:
                new_value = mapping.element_mappings[value]
            else:
                new_value = value

            solution[new_key] = new_value

        return solution

    def _transform(
        self,
        source_case: Case,
        target_problem: AnalogicalStructure,
        mapping: Mapping
    ) -> Dict[str, Any]:
        """Transformation-based adaptation."""
        solution = self._substitute(source_case, mapping)

        # Apply transformations based on differences
        source_attrs = {}
        for elem in source_case.problem.elements.values():
            source_attrs.update(elem.attributes)

        target_attrs = {}
        for elem in target_problem.elements.values():
            target_attrs.update(elem.attributes)

        # Adjust solution based on attribute differences
        for attr in set(source_attrs.keys()) & set(target_attrs.keys()):
            if source_attrs[attr] != target_attrs[attr]:
                # Apply transformation
                if attr in solution:
                    # Simple scaling for numeric values
                    if isinstance(solution[attr], (int, float)):
                        if isinstance(source_attrs[attr], (int, float)) and source_attrs[attr] != 0:
                            ratio = target_attrs[attr] / source_attrs[attr]
                            solution[attr] = solution[attr] * ratio

        return solution

    def _abstract_adapt(
        self,
        source_case: Case,
        target_problem: AnalogicalStructure
    ) -> Dict[str, Any]:
        """Abstraction-based adaptation."""
        # Extract abstract solution pattern
        abstract_solution = {}

        for key, value in source_case.solution.items():
            if isinstance(value, (int, float)):
                abstract_solution[key] = {"type": "numeric", "base": value}
            elif isinstance(value, str):
                abstract_solution[key] = {"type": "symbolic", "pattern": value}
            else:
                abstract_solution[key] = value

        # Instantiate for target
        solution = {}
        for key, pattern in abstract_solution.items():
            if isinstance(pattern, dict):
                if pattern.get("type") == "numeric":
                    solution[key] = pattern["base"]
                elif pattern.get("type") == "symbolic":
                    solution[key] = pattern["pattern"]
            else:
                solution[key] = pattern

        return solution


# =============================================================================
# ANALOGICAL REASONER
# =============================================================================

class AnalogicalReasoner:
    """
    Analogical Reasoner for BAEL.

    Advanced analogical reasoning and case-based learning.
    """

    def __init__(self):
        self._structures: Dict[str, AnalogicalStructure] = {}
        self._case_base = CaseBase()
        self._sme = StructureMappingEngine()
        self._inference_engine = AnalogicalInferenceEngine()
        self._adaptation_engine = AdaptationEngine()
        self._similarity = SimilarityCalculator()

    # -------------------------------------------------------------------------
    # STRUCTURE MANAGEMENT
    # -------------------------------------------------------------------------

    def create_structure(
        self,
        name: str,
        domain: str = ""
    ) -> StructureBuilder:
        """Create a structure builder."""
        builder = StructureBuilder()
        builder.new_structure(name, domain)
        return builder

    def add_structure(self, structure: AnalogicalStructure) -> None:
        """Add a structure."""
        self._structures[structure.structure_id] = structure

    def get_structure(self, structure_id: str) -> Optional[AnalogicalStructure]:
        """Get a structure."""
        return self._structures.get(structure_id)

    # -------------------------------------------------------------------------
    # MAPPING
    # -------------------------------------------------------------------------

    def find_analogy(
        self,
        source: AnalogicalStructure,
        target: AnalogicalStructure
    ) -> Optional[Mapping]:
        """Find best analogy between structures."""
        mappings = self._sme.find_mappings(source, target)
        return mappings[0] if mappings else None

    def find_all_analogies(
        self,
        source: AnalogicalStructure,
        target: AnalogicalStructure
    ) -> List[Mapping]:
        """Find all analogies between structures."""
        return self._sme.find_mappings(source, target)

    # -------------------------------------------------------------------------
    # INFERENCE
    # -------------------------------------------------------------------------

    def infer_from_analogy(
        self,
        source: AnalogicalStructure,
        target: AnalogicalStructure,
        mapping: Optional[Mapping] = None
    ) -> List[Inference]:
        """Generate inferences from analogy."""
        return self._inference_engine.infer(source, target, mapping)

    # -------------------------------------------------------------------------
    # CASE-BASED REASONING
    # -------------------------------------------------------------------------

    def add_case(
        self,
        name: str,
        problem: AnalogicalStructure,
        solution: Dict[str, Any],
        outcome: Optional[Any] = None
    ) -> Case:
        """Add a case to the case base."""
        case = Case(
            name=name,
            problem=problem,
            solution=solution,
            outcome=outcome
        )
        self._case_base.add_case(case)
        return case

    def retrieve_cases(
        self,
        query: AnalogicalStructure,
        top_k: int = 5,
        method: RetrievalMethod = RetrievalMethod.MAC_FAC
    ) -> List[Tuple[Case, float]]:
        """Retrieve similar cases."""
        return self._case_base.retrieve(query, method, top_k)

    def solve_by_analogy(
        self,
        problem: AnalogicalStructure,
        adaptation: AdaptationType = AdaptationType.SUBSTITUTION
    ) -> Optional[Dict[str, Any]]:
        """Solve problem using analogical case retrieval."""
        # Retrieve best case
        cases = self._case_base.retrieve(problem, RetrievalMethod.MAC_FAC, top_k=1)

        if not cases:
            return None

        best_case, score = cases[0]

        # Find mapping
        mapping = self.find_analogy(best_case.problem, problem)

        if not mapping:
            # Fall back to direct solution copy
            return dict(best_case.solution)

        # Adapt solution
        return self._adaptation_engine.adapt(
            best_case, problem, mapping, adaptation
        )

    # -------------------------------------------------------------------------
    # SIMILARITY
    # -------------------------------------------------------------------------

    def surface_similarity(
        self,
        s1: AnalogicalStructure,
        s2: AnalogicalStructure
    ) -> float:
        """Calculate surface similarity."""
        return self._similarity.surface_similarity(s1, s2)

    def structural_similarity(
        self,
        s1: AnalogicalStructure,
        s2: AnalogicalStructure
    ) -> float:
        """Calculate structural similarity."""
        return self._similarity.structural_similarity(s1, s2)

    # -------------------------------------------------------------------------
    # TRANSFER LEARNING
    # -------------------------------------------------------------------------

    def transfer_knowledge(
        self,
        source_domain: str,
        target_domain: str,
        source_structure: AnalogicalStructure,
        target_structure: AnalogicalStructure
    ) -> Dict[str, Any]:
        """Transfer knowledge between domains."""
        # Find cross-domain analogy
        mapping = self.find_analogy(source_structure, target_structure)

        if not mapping:
            return {"success": False, "reason": "No valid analogy found"}

        # Generate inferences
        inferences = self.infer_from_analogy(
            source_structure, target_structure, mapping
        )

        return {
            "success": True,
            "mapping": mapping,
            "inferences": inferences,
            "source_domain": source_domain,
            "target_domain": target_domain
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Analogical Reasoner."""
    print("=" * 70)
    print("BAEL - ANALOGICAL REASONER DEMO")
    print("Advanced Analogical Reasoning and Case-Based Learning")
    print("=" * 70)
    print()

    reasoner = AnalogicalReasoner()

    # 1. Create Analogical Structures
    print("1. CREATE ANALOGICAL STRUCTURES:")
    print("-" * 40)

    # Solar System (Source)
    builder = reasoner.create_structure("Solar System", "astronomy")
    sun = builder.add_object("Sun", {"type": "star", "mass": "large"})
    earth = builder.add_object("Earth", {"type": "planet", "mass": "medium"})
    moon = builder.add_object("Moon", {"type": "satellite", "mass": "small"})

    builder.add_relation("attracts", sun, earth)
    builder.add_relation("attracts", earth, moon)
    builder.add_relation("revolves_around", earth, sun)
    builder.add_relation("revolves_around", moon, earth)
    builder.add_relation("causes", "attracts", "revolves_around", is_higher_order=True)

    solar_system = builder.build()
    reasoner.add_structure(solar_system)
    print(f"   Created: Solar System with {len(solar_system.elements)} elements, "
          f"{len(solar_system.relations)} relations")

    # Atom (Target)
    builder = reasoner.create_structure("Atom", "physics")
    nucleus = builder.add_object("Nucleus", {"type": "core", "mass": "large"})
    electron = builder.add_object("Electron", {"type": "particle", "mass": "small"})

    builder.add_relation("attracts", nucleus, electron)
    builder.add_relation("revolves_around", electron, nucleus)

    atom = builder.build()
    reasoner.add_structure(atom)
    print(f"   Created: Atom with {len(atom.elements)} elements, "
          f"{len(atom.relations)} relations")
    print()

    # 2. Find Analogy
    print("2. FIND ANALOGY:")
    print("-" * 40)

    mapping = reasoner.find_analogy(solar_system, atom)
    if mapping:
        print(f"   Mapping found (score: {mapping.score:.2f}):")
        for source, target in mapping.element_mappings.items():
            source_elem = solar_system.elements.get(source)
            target_elem = atom.elements.get(target)
            if source_elem and target_elem:
                print(f"     {source_elem.name} → {target_elem.name}")
    print()

    # 3. Analogical Inference
    print("3. ANALOGICAL INFERENCE:")
    print("-" * 40)

    inferences = reasoner.infer_from_analogy(solar_system, atom, mapping)
    if inferences:
        print(f"   Generated {len(inferences)} inference(s):")
        for inf in inferences:
            print(f"     {inf.source_relation.name} → inferred {inf.inferred_relation.name}")
            print(f"       Confidence: {inf.confidence:.2f}")
    else:
        print("   No new inferences (target already has all source relations)")
    print()

    # 4. Case-Based Reasoning
    print("4. CASE-BASED REASONING:")
    print("-" * 40)

    # Add some cases
    # Case 1: Simple lever problem
    builder = reasoner.create_structure("Lever Problem 1", "physics")
    fulcrum = builder.add_object("Fulcrum", {"position": 0.5})
    effort = builder.add_object("Effort", {"force": 100, "distance": 0.3})
    load = builder.add_object("Load", {"force": 50, "distance": 0.6})
    builder.add_relation("balanced_by", effort, load)
    lever1 = builder.build()

    reasoner.add_case(
        "Lever Case 1",
        lever1,
        {"action": "apply_force", "force": 100, "result": "balanced"},
        outcome="success"
    )
    print("   Added case: Lever Problem 1")

    # Case 2: Similar lever problem
    builder = reasoner.create_structure("Lever Problem 2", "physics")
    fulcrum2 = builder.add_object("Fulcrum", {"position": 0.4})
    effort2 = builder.add_object("Effort", {"force": 80, "distance": 0.4})
    load2 = builder.add_object("Load", {"force": 40, "distance": 0.8})
    builder.add_relation("balanced_by", effort2, load2)
    lever2 = builder.build()

    reasoner.add_case(
        "Lever Case 2",
        lever2,
        {"action": "apply_force", "force": 80, "result": "balanced"},
        outcome="success"
    )
    print("   Added case: Lever Problem 2")

    # Query with new problem
    builder = reasoner.create_structure("New Lever Problem", "physics")
    new_fulcrum = builder.add_object("Fulcrum", {"position": 0.5})
    new_effort = builder.add_object("Effort", {"force": 0, "distance": 0.25})
    new_load = builder.add_object("Load", {"force": 60, "distance": 0.5})
    builder.add_relation("balanced_by", new_effort, new_load)
    new_lever = builder.build()

    retrieved = reasoner.retrieve_cases(new_lever, top_k=2)
    print(f"\n   Retrieved cases for new problem:")
    for case, score in retrieved:
        print(f"     {case.name}: score = {score:.2f}")
    print()

    # 5. Solve by Analogy
    print("5. SOLVE BY ANALOGY:")
    print("-" * 40)

    solution = reasoner.solve_by_analogy(new_lever, AdaptationType.SUBSTITUTION)
    if solution:
        print(f"   Solution from analogical reasoning:")
        for key, value in solution.items():
            print(f"     {key}: {value}")
    print()

    # 6. Similarity Measures
    print("6. SIMILARITY MEASURES:")
    print("-" * 40)

    surface_sim = reasoner.surface_similarity(solar_system, atom)
    struct_sim = reasoner.structural_similarity(solar_system, atom)

    print(f"   Solar System vs Atom:")
    print(f"     Surface similarity: {surface_sim:.3f}")
    print(f"     Structural similarity: {struct_sim:.3f}")
    print()

    # 7. Knowledge Transfer
    print("7. KNOWLEDGE TRANSFER:")
    print("-" * 40)

    transfer = reasoner.transfer_knowledge(
        "astronomy", "physics",
        solar_system, atom
    )

    if transfer["success"]:
        print(f"   Successfully transferred knowledge:")
        print(f"     From: {transfer['source_domain']}")
        print(f"     To: {transfer['target_domain']}")
        print(f"     Inferences: {len(transfer['inferences'])}")
    print()

    # 8. Cross-Domain Analogy
    print("8. CROSS-DOMAIN ANALOGY:")
    print("-" * 40)

    # Water flow (hydraulics)
    builder = reasoner.create_structure("Water Flow", "hydraulics")
    pipe = builder.add_object("Pipe", {"type": "conduit"})
    pump = builder.add_object("Pump", {"type": "source"})
    reservoir = builder.add_object("Reservoir", {"type": "storage"})
    builder.add_relation("flows_through", pipe, reservoir)
    builder.add_relation("drives", pump, pipe)
    water_flow = builder.build()

    # Electric circuit (electronics)
    builder = reasoner.create_structure("Electric Circuit", "electronics")
    wire = builder.add_object("Wire", {"type": "conduit"})
    battery = builder.add_object("Battery", {"type": "source"})
    capacitor = builder.add_object("Capacitor", {"type": "storage"})
    builder.add_relation("flows_through", wire, capacitor)
    builder.add_relation("drives", battery, wire)
    circuit = builder.build()

    cross_mapping = reasoner.find_analogy(water_flow, circuit)
    if cross_mapping:
        print("   Water Flow ↔ Electric Circuit mapping:")
        for source, target in cross_mapping.element_mappings.items():
            source_elem = water_flow.elements.get(source)
            target_elem = circuit.elements.get(target)
            if source_elem and target_elem:
                print(f"     {source_elem.name} ↔ {target_elem.name}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Analogical Reasoner Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
