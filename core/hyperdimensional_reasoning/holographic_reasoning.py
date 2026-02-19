"""
⚡ HOLOGRAPHIC REASONING ENGINE ⚡
=================================
Advanced reasoning using holographic representations.

Enables:
- Analogical reasoning across domains
- Conceptual blending for creativity
- Metaphor understanding and generation
- Cross-domain knowledge transfer
"""

import math
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import uuid

from .hyperdimensional_core import (
    HyperdimensionalVector,
    HyperdimensionalSpace,
    HDBinding,
    HDBundling,
    HDPermutation,
    HDSimilarity,
    VectorType,
)
from .vector_symbolic_architecture import (
    VectorSymbolicArchitecture,
    SymbolicEncoder,
    SymbolicMemory,
)


@dataclass
class Concept:
    """A concept with holographic representation"""
    name: str
    vector: HyperdimensionalVector
    domain: str = "general"
    properties: Dict[str, str] = field(default_factory=dict)
    relations: Dict[str, List[str]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Analogy:
    """An analogical mapping between domains"""
    source_domain: str
    target_domain: str
    mappings: Dict[str, str]  # source_concept -> target_concept
    confidence: float = 1.0
    structural_similarity: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Blend:
    """Result of conceptual blending"""
    name: str
    input_spaces: List[str]
    generic_space: Dict[str, str]
    blended_space: Dict[str, str]
    emergent_properties: List[str]
    vector: Optional[HyperdimensionalVector] = None


class SemanticBinder:
    """
    Binds semantic structures holographically.

    Creates distributed representations of complex meanings.
    """

    def __init__(self, space: HyperdimensionalSpace):
        self.space = space

    def bind_property(
        self,
        entity: str,
        property_name: str,
        property_value: str
    ) -> HyperdimensionalVector:
        """Bind entity with property"""
        entity_vec = self.space.get_or_create(entity)
        prop_vec = self.space.get_or_create(f"prop:{property_name}")
        value_vec = self.space.get_or_create(property_value)

        # (entity ⊛ property) + (property ⊛ value)
        ep = HDBinding.bind(entity_vec, prop_vec)
        pv = HDBinding.bind(prop_vec, value_vec)

        return HDBundling.bundle([ep, pv])

    def bind_relation(
        self,
        subject: str,
        relation: str,
        obj: str
    ) -> HyperdimensionalVector:
        """Bind semantic relation"""
        subj_vec = self.space.get_or_create(subject)
        rel_vec = self.space.get_or_create(f"rel:{relation}")
        obj_vec = self.space.get_or_create(obj)

        # relation ⊛ (subject + ρ(object))
        obj_shifted = obj_vec.permute(1)
        participants = HDBundling.bundle([subj_vec, obj_shifted])

        return HDBinding.bind(rel_vec, participants)

    def bind_event(
        self,
        verb: str,
        agent: Optional[str] = None,
        patient: Optional[str] = None,
        instrument: Optional[str] = None,
        location: Optional[str] = None,
        time: Optional[str] = None
    ) -> HyperdimensionalVector:
        """Bind event with thematic roles"""
        verb_vec = self.space.get_or_create(f"event:{verb}")

        role_bindings = []

        if agent:
            agent_vec = self.space.get_or_create(agent)
            role_vec = self.space.get_or_create("role:agent")
            role_bindings.append(HDBinding.bind(role_vec, agent_vec))

        if patient:
            patient_vec = self.space.get_or_create(patient)
            role_vec = self.space.get_or_create("role:patient")
            role_bindings.append(HDBinding.bind(role_vec, patient_vec))

        if instrument:
            inst_vec = self.space.get_or_create(instrument)
            role_vec = self.space.get_or_create("role:instrument")
            role_bindings.append(HDBinding.bind(role_vec, inst_vec))

        if location:
            loc_vec = self.space.get_or_create(location)
            role_vec = self.space.get_or_create("role:location")
            role_bindings.append(HDBinding.bind(role_vec, loc_vec))

        if time:
            time_vec = self.space.get_or_create(time)
            role_vec = self.space.get_or_create("role:time")
            role_bindings.append(HDBinding.bind(role_vec, time_vec))

        if role_bindings:
            roles_bundled = HDBundling.bundle(role_bindings)
            return HDBinding.bind(verb_vec, roles_bundled)

        return verb_vec


class AnalogicalMapper:
    """
    Maps analogies between domains.

    Implements Structure Mapping Theory (SMT):
    - Finds structural correspondences
    - Transfers inferences across domains
    """

    def __init__(self, dimension: int = 10000):
        self.dimension = dimension
        self.space = HyperdimensionalSpace(dimension)
        self.domains: Dict[str, Dict[str, Concept]] = {}
        self.analogies: List[Analogy] = []

    def register_concept(
        self,
        name: str,
        domain: str,
        properties: Dict[str, str] = None,
        relations: Dict[str, List[str]] = None
    ) -> Concept:
        """Register concept in domain"""
        vector = self.space.get_or_create(f"{domain}:{name}")

        concept = Concept(
            name=name,
            vector=vector,
            domain=domain,
            properties=properties or {},
            relations=relations or {}
        )

        if domain not in self.domains:
            self.domains[domain] = {}
        self.domains[domain][name] = concept

        return concept

    def compute_structural_similarity(
        self,
        source_concepts: List[Concept],
        target_concepts: List[Concept]
    ) -> np.ndarray:
        """Compute structure-based similarity matrix"""
        n_source = len(source_concepts)
        n_target = len(target_concepts)

        similarity_matrix = np.zeros((n_source, n_target))

        for i, src in enumerate(source_concepts):
            for j, tgt in enumerate(target_concepts):
                # Vector similarity
                vec_sim = src.vector.similarity(tgt.vector)

                # Property overlap
                common_props = set(src.properties.keys()) & set(tgt.properties.keys())
                prop_sim = len(common_props) / max(
                    len(src.properties), len(tgt.properties), 1
                )

                # Relation overlap
                common_rels = set(src.relations.keys()) & set(tgt.relations.keys())
                rel_sim = len(common_rels) / max(
                    len(src.relations), len(tgt.relations), 1
                )

                # Structural emphasis (relations > properties > vectors)
                similarity_matrix[i, j] = (
                    0.2 * vec_sim + 0.3 * prop_sim + 0.5 * rel_sim
                )

        return similarity_matrix

    def find_mapping(
        self,
        source_domain: str,
        target_domain: str
    ) -> Analogy:
        """Find best analogical mapping between domains"""
        if source_domain not in self.domains or target_domain not in self.domains:
            return Analogy(source_domain, target_domain, {})

        source_concepts = list(self.domains[source_domain].values())
        target_concepts = list(self.domains[target_domain].values())

        if not source_concepts or not target_concepts:
            return Analogy(source_domain, target_domain, {})

        # Compute similarity matrix
        sim_matrix = self.compute_structural_similarity(
            source_concepts, target_concepts
        )

        # Greedy mapping (can be improved with Hungarian algorithm)
        mappings = {}
        used_targets = set()

        # Sort by similarity for greedy assignment
        pairs = []
        for i in range(len(source_concepts)):
            for j in range(len(target_concepts)):
                pairs.append((sim_matrix[i, j], i, j))
        pairs.sort(reverse=True)

        for sim, i, j in pairs:
            if i not in [p[1] for p in pairs[:len(mappings)]]:
                if j not in used_targets:
                    mappings[source_concepts[i].name] = target_concepts[j].name
                    used_targets.add(j)

        # Calculate overall structural similarity
        structural_sim = np.mean([
            sim_matrix[i, list(self.domains[target_domain].keys()).index(tgt)]
            for i, (src, tgt) in enumerate(mappings.items())
            if tgt in self.domains[target_domain]
        ]) if mappings else 0.0

        analogy = Analogy(
            source_domain=source_domain,
            target_domain=target_domain,
            mappings=mappings,
            confidence=float(structural_sim),
            structural_similarity=float(structural_sim)
        )

        self.analogies.append(analogy)
        return analogy

    def transfer_inference(
        self,
        analogy: Analogy,
        source_inference: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transfer inference from source to target domain"""
        target_inference = {}

        for key, value in source_inference.items():
            if key in analogy.mappings:
                target_key = analogy.mappings[key]
            else:
                target_key = key

            if isinstance(value, str) and value in analogy.mappings:
                target_value = analogy.mappings[value]
            else:
                target_value = value

            target_inference[target_key] = target_value

        target_inference['_transferred_from'] = analogy.source_domain
        target_inference['_confidence'] = analogy.confidence

        return target_inference

    def solve_analogy(
        self,
        a: str,
        b: str,
        c: str,
        domain: str = "general"
    ) -> List[Tuple[str, float]]:
        """
        Solve: a is to b as c is to ?

        Using vector arithmetic: d = b - a + c
        """
        a_vec = self.space.get_or_create(f"{domain}:{a}")
        b_vec = self.space.get_or_create(f"{domain}:{b}")
        c_vec = self.space.get_or_create(f"{domain}:{c}")

        # Compute relation vector
        relation = HyperdimensionalVector(
            vector=b_vec.vector - a_vec.vector,
            dimension=self.dimension
        )

        # Apply to c
        d_vec = HyperdimensionalVector(
            vector=c_vec.vector + relation.vector,
            dimension=self.dimension
        )

        # Query for best match
        return self.space.fast_query(d_vec)


class ConceptualBlender:
    """
    Blends concepts to create novel combinations.

    Implements Conceptual Blending Theory:
    1. Input spaces (concepts to blend)
    2. Generic space (shared structure)
    3. Blended space (novel combination)
    4. Emergent structure (new properties)
    """

    def __init__(self, vsa: VectorSymbolicArchitecture):
        self.vsa = vsa
        self.blends: List[Blend] = []

    def extract_generic_space(
        self,
        concept_a: Dict[str, str],
        concept_b: Dict[str, str]
    ) -> Dict[str, str]:
        """Extract shared structure (generic space)"""
        generic = {}

        for key in set(concept_a.keys()) & set(concept_b.keys()):
            # Both have same role
            generic[key] = f"generic:{key}"

        return generic

    def blend(
        self,
        name: str,
        concept_a: Dict[str, str],
        concept_b: Dict[str, str],
        blend_weights: Tuple[float, float] = (0.5, 0.5)
    ) -> Blend:
        """
        Blend two concepts.

        Creates novel combination with emergent properties.
        """
        # Encode input spaces
        vec_a = self.vsa.compose(concept_a)
        vec_b = self.vsa.compose(concept_b)

        # Extract generic space
        generic = self.extract_generic_space(concept_a, concept_b)

        # Create blended space
        blended = {}

        # Weighted combination
        for key in set(concept_a.keys()) | set(concept_b.keys()):
            if key in concept_a and key in concept_b:
                # Both have this role - blend values
                if np.random.random() < blend_weights[0]:
                    blended[key] = concept_a[key]
                else:
                    blended[key] = concept_b[key]
            elif key in concept_a:
                blended[key] = concept_a[key]
            else:
                blended[key] = concept_b[key]

        # Create blended vector
        blend_vec = HDBundling.weighted_bundle(
            [vec_a, vec_b],
            list(blend_weights)
        )

        # Find emergent properties
        emergent = self._find_emergent_properties(
            blend_vec, vec_a, vec_b, blended
        )

        blend_result = Blend(
            name=name,
            input_spaces=[str(concept_a), str(concept_b)],
            generic_space=generic,
            blended_space=blended,
            emergent_properties=emergent,
            vector=blend_vec
        )

        self.blends.append(blend_result)
        return blend_result

    def _find_emergent_properties(
        self,
        blend_vec: HyperdimensionalVector,
        vec_a: HyperdimensionalVector,
        vec_b: HyperdimensionalVector,
        blended: Dict[str, str]
    ) -> List[str]:
        """Find properties that emerge from the blend"""
        emergent = []

        # Query for concepts similar to blend but not to inputs
        similar_to_blend = self.vsa.query(blend_vec, top_k=20)
        similar_to_a = set(c for c, _ in self.vsa.query(vec_a, top_k=20))
        similar_to_b = set(c for c, _ in self.vsa.query(vec_b, top_k=20))

        for concept, sim in similar_to_blend:
            if concept not in similar_to_a and concept not in similar_to_b:
                if sim > 0.3:  # Threshold
                    emergent.append(f"emergent:{concept}")

        return emergent[:5]  # Top 5 emergent properties

    def selective_projection(
        self,
        concept_a: Dict[str, str],
        concept_b: Dict[str, str],
        project_from_a: List[str],
        project_from_b: List[str]
    ) -> Dict[str, str]:
        """
        Selective projection blending.

        Explicitly choose which elements project from each input.
        """
        blended = {}

        for key in project_from_a:
            if key in concept_a:
                blended[key] = concept_a[key]

        for key in project_from_b:
            if key in concept_b:
                blended[key] = concept_b[key]

        return blended


class MetaphorEngine:
    """
    Understands and generates metaphors.

    Metaphor = systematic mapping between domains.
    """

    def __init__(self, mapper: AnalogicalMapper):
        self.mapper = mapper
        self.metaphors: Dict[str, Analogy] = {}

    def register_metaphor(
        self,
        name: str,
        source_domain: str,
        target_domain: str,
        mappings: Dict[str, str]
    ):
        """Register conceptual metaphor"""
        analogy = Analogy(
            source_domain=source_domain,
            target_domain=target_domain,
            mappings=mappings,
            confidence=1.0
        )
        self.metaphors[name] = analogy

    def apply_metaphor(
        self,
        metaphor_name: str,
        source_expression: Dict[str, str]
    ) -> Dict[str, str]:
        """Apply metaphor to expression"""
        if metaphor_name not in self.metaphors:
            return source_expression

        metaphor = self.metaphors[metaphor_name]

        target = {}
        for key, value in source_expression.items():
            new_key = metaphor.mappings.get(key, key)
            new_value = metaphor.mappings.get(value, value)
            target[new_key] = new_value

        return target

    def detect_metaphor(
        self,
        expression: Dict[str, str],
        target_domain: str
    ) -> Optional[str]:
        """Detect which metaphor is being used"""
        best_match = None
        best_score = 0

        for name, metaphor in self.metaphors.items():
            if metaphor.target_domain != target_domain:
                continue

            # Count matching mappings
            score = 0
            for value in expression.values():
                if value in metaphor.mappings.values():
                    score += 1

            if score > best_score:
                best_score = score
                best_match = name

        return best_match

    def generate_metaphor(
        self,
        concept: str,
        source_domain: str,
        target_domain: str
    ) -> str:
        """Generate metaphorical expression"""
        # Find mapping
        analogy = self.mapper.find_mapping(source_domain, target_domain)

        if concept in analogy.mappings:
            return analogy.mappings[concept]

        # Try vector similarity
        source_vec = self.mapper.space.get_or_create(f"{source_domain}:{concept}")

        # Find most similar in target domain
        if target_domain in self.mapper.domains:
            best_match = None
            best_sim = -1

            for tgt_name, tgt_concept in self.mapper.domains[target_domain].items():
                sim = source_vec.similarity(tgt_concept.vector)
                if sim > best_sim:
                    best_sim = sim
                    best_match = tgt_name

            if best_match:
                return best_match

        return concept


class HolographicReasoner:
    """
    Complete holographic reasoning system.

    Combines all holographic reasoning capabilities:
    - Semantic binding
    - Analogical mapping
    - Conceptual blending
    - Metaphor processing
    """

    def __init__(self, dimension: int = 10000):
        self.dimension = dimension
        self.space = HyperdimensionalSpace(dimension)
        self.vsa = VectorSymbolicArchitecture(dimension)

        self.binder = SemanticBinder(self.space)
        self.mapper = AnalogicalMapper(dimension)
        self.blender = ConceptualBlender(self.vsa)
        self.metaphor = MetaphorEngine(self.mapper)

    def encode_knowledge(
        self,
        triples: List[Tuple[str, str, str]]
    ) -> HyperdimensionalVector:
        """Encode knowledge graph holographically"""
        relation_vecs = []

        for subj, rel, obj in triples:
            vec = self.binder.bind_relation(subj, rel, obj)
            relation_vecs.append(vec)

        return HDBundling.bundle(relation_vecs)

    def query_knowledge(
        self,
        knowledge_vec: HyperdimensionalVector,
        query: Dict[str, str]
    ) -> List[Tuple[str, float]]:
        """Query encoded knowledge"""
        query_vec = self.vsa.compose(query)
        probe = HDBinding.unbind(knowledge_vec, query_vec)
        return self.vsa.query(probe)

    def reason_by_analogy(
        self,
        source: Dict[str, str],
        source_domain: str,
        target_domain: str
    ) -> Dict[str, str]:
        """Reason about target using source analogy"""
        analogy = self.mapper.find_mapping(source_domain, target_domain)
        return self.mapper.transfer_inference(analogy, source)

    def creative_blend(
        self,
        concept_a: Dict[str, str],
        concept_b: Dict[str, str]
    ) -> Blend:
        """Create creative blend of concepts"""
        name = f"blend_{uuid.uuid4().hex[:8]}"
        return self.blender.blend(name, concept_a, concept_b)

    def understand_metaphor(
        self,
        expression: Dict[str, str]
    ) -> Dict[str, Any]:
        """Understand metaphorical expression"""
        # Try to detect metaphor
        for domain in self.mapper.domains:
            metaphor = self.metaphor.detect_metaphor(expression, domain)
            if metaphor:
                return {
                    'metaphor': metaphor,
                    'domain': domain,
                    'literal': self.metaphor.apply_metaphor(metaphor, expression)
                }

        return {'literal': expression}

    def solve_problem_by_analogy(
        self,
        problem: Dict[str, Any],
        problem_domain: str,
        solution_domains: List[str]
    ) -> List[Dict[str, Any]]:
        """Solve problem by finding analogous solutions"""
        solutions = []

        for domain in solution_domains:
            analogy = self.mapper.find_mapping(domain, problem_domain)

            if analogy.confidence > 0.3:
                solution = self.mapper.transfer_inference(analogy, problem)
                solution['_source_domain'] = domain
                solution['_confidence'] = analogy.confidence
                solutions.append(solution)

        # Sort by confidence
        solutions.sort(key=lambda x: -x.get('_confidence', 0))
        return solutions


# Export all
__all__ = [
    'Concept',
    'Analogy',
    'Blend',
    'SemanticBinder',
    'AnalogicalMapper',
    'ConceptualBlender',
    'MetaphorEngine',
    'HolographicReasoner',
]
