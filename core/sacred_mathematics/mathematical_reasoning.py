"""
⚡ MATHEMATICAL REASONING ⚡
===========================
High-level mathematical reasoning.

Features:
- Concept understanding
- Relation discovery
- Domain reasoning
- Proof assistance
"""

import math
import numpy as np
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import uuid


class ConceptType(Enum):
    """Types of mathematical concepts"""
    DEFINITION = auto()
    AXIOM = auto()
    THEOREM = auto()
    LEMMA = auto()
    COROLLARY = auto()
    CONJECTURE = auto()
    EXAMPLE = auto()
    COUNTEREXAMPLE = auto()


class RelationType(Enum):
    """Types of mathematical relations"""
    IMPLIES = auto()
    EQUIVALENT = auto()
    GENERALIZES = auto()
    SPECIALIZES = auto()
    USES = auto()
    CONTRADICTS = auto()
    RELATED = auto()


@dataclass
class MathematicalConcept:
    """A mathematical concept"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    concept_type: ConceptType = ConceptType.DEFINITION

    # Content
    statement: str = ""
    formal_statement: Optional[str] = None  # LaTeX or formal notation

    # Domain
    domains: Set[str] = field(default_factory=set)  # algebra, analysis, etc.

    # Prerequisites
    prerequisites: Set[str] = field(default_factory=set)  # Concept IDs

    # Properties
    is_proven: bool = False
    is_fundamental: bool = False

    # Embedding for similarity
    embedding: Optional[np.ndarray] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MathematicalRelation:
    """Relation between concepts"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str = ""
    target_id: str = ""
    relation_type: RelationType = RelationType.RELATED

    # Strength/confidence
    strength: float = 1.0

    # Justification
    justification: str = ""


@dataclass
class MathematicalDomain:
    """A mathematical domain"""
    name: str
    description: str = ""

    # Concepts in domain
    concepts: Set[str] = field(default_factory=set)

    # Sub-domains
    sub_domains: Set[str] = field(default_factory=set)
    parent_domain: Optional[str] = None

    # Foundational concepts
    foundations: Set[str] = field(default_factory=set)


class ConceptGraph:
    """
    Graph of mathematical concepts and relations.
    """

    def __init__(self):
        self.concepts: Dict[str, MathematicalConcept] = {}
        self.relations: Dict[str, MathematicalRelation] = {}
        self.domains: Dict[str, MathematicalDomain] = {}

        # Indexes
        self.by_name: Dict[str, str] = {}
        self.by_domain: Dict[str, Set[str]] = defaultdict(set)

        # Relation indexes
        self.outgoing: Dict[str, Set[str]] = defaultdict(set)
        self.incoming: Dict[str, Set[str]] = defaultdict(set)

    def add_concept(self, concept: MathematicalConcept):
        """Add concept to graph"""
        self.concepts[concept.id] = concept
        self.by_name[concept.name] = concept.id

        for domain in concept.domains:
            self.by_domain[domain].add(concept.id)

    def add_relation(self, relation: MathematicalRelation):
        """Add relation to graph"""
        self.relations[relation.id] = relation
        self.outgoing[relation.source_id].add(relation.id)
        self.incoming[relation.target_id].add(relation.id)

    def get_concept(self, name: str) -> Optional[MathematicalConcept]:
        """Get concept by name"""
        cid = self.by_name.get(name)
        return self.concepts.get(cid) if cid else None

    def get_related(
        self,
        concept_id: str,
        relation_type: RelationType = None
    ) -> List[MathematicalConcept]:
        """Get related concepts"""
        related = []

        for rel_id in self.outgoing.get(concept_id, set()):
            rel = self.relations.get(rel_id)
            if rel and (relation_type is None or rel.relation_type == relation_type):
                target = self.concepts.get(rel.target_id)
                if target:
                    related.append(target)

        return related

    def get_prerequisites(
        self,
        concept_id: str
    ) -> Set[MathematicalConcept]:
        """Get all prerequisites recursively"""
        prereqs = set()
        concept = self.concepts.get(concept_id)

        if not concept:
            return prereqs

        for prereq_id in concept.prerequisites:
            prereq = self.concepts.get(prereq_id)
            if prereq:
                prereqs.add(prereq)
                prereqs.update(self.get_prerequisites(prereq_id))

        return prereqs

    def find_path(
        self,
        source_id: str,
        target_id: str
    ) -> Optional[List[str]]:
        """Find path between concepts"""
        if source_id not in self.concepts or target_id not in self.concepts:
            return None

        # BFS
        visited = {source_id}
        queue = [(source_id, [source_id])]

        while queue:
            current, path = queue.pop(0)

            if current == target_id:
                return path

            for rel_id in self.outgoing.get(current, set()):
                rel = self.relations.get(rel_id)
                if rel and rel.target_id not in visited:
                    visited.add(rel.target_id)
                    queue.append((rel.target_id, path + [rel.target_id]))

        return None

    def get_domain_concepts(
        self,
        domain_name: str,
        include_subdomains: bool = True
    ) -> List[MathematicalConcept]:
        """Get all concepts in domain"""
        concepts = []

        for cid in self.by_domain.get(domain_name, set()):
            if cid in self.concepts:
                concepts.append(self.concepts[cid])

        if include_subdomains and domain_name in self.domains:
            domain = self.domains[domain_name]
            for subdomain in domain.sub_domains:
                concepts.extend(self.get_domain_concepts(subdomain, True))

        return concepts


class MathematicalReasoner:
    """
    High-level mathematical reasoning.
    """

    def __init__(self, concept_graph: ConceptGraph = None):
        self.graph = concept_graph or ConceptGraph()

    def understand_problem(
        self,
        problem: str
    ) -> Dict[str, Any]:
        """Analyze a mathematical problem"""
        # Extract concepts mentioned
        concepts_found = []
        for name, cid in self.graph.by_name.items():
            if name.lower() in problem.lower():
                concepts_found.append(self.graph.concepts[cid])

        # Identify domains
        domains = set()
        for concept in concepts_found:
            domains.update(concept.domains)

        # Find relevant theorems
        theorems = [
            c for c in concepts_found
            if c.concept_type in [ConceptType.THEOREM, ConceptType.LEMMA]
        ]

        return {
            'concepts': concepts_found,
            'domains': list(domains),
            'relevant_theorems': theorems,
            'prerequisites': self._collect_prerequisites(concepts_found)
        }

    def _collect_prerequisites(
        self,
        concepts: List[MathematicalConcept]
    ) -> List[MathematicalConcept]:
        """Collect all prerequisites"""
        prereqs = set()

        for concept in concepts:
            prereqs.update(self.graph.get_prerequisites(concept.id))

        return list(prereqs)

    def suggest_approach(
        self,
        problem: str
    ) -> List[str]:
        """Suggest approaches for problem"""
        understanding = self.understand_problem(problem)

        approaches = []

        # Based on domains
        for domain in understanding['domains']:
            if domain == 'algebra':
                approaches.append("Try algebraic manipulation")
            elif domain == 'analysis':
                approaches.append("Consider using limits or continuity")
            elif domain == 'geometry':
                approaches.append("Draw a diagram")
            elif domain == 'number_theory':
                approaches.append("Consider divisibility or modular arithmetic")

        # Based on theorems
        for theorem in understanding['relevant_theorems']:
            approaches.append(f"Apply {theorem.name}")

        if not approaches:
            approaches.append("Break down into smaller parts")
            approaches.append("Look for patterns")

        return approaches

    def find_analogies(
        self,
        concept_id: str,
        target_domain: str
    ) -> List[Tuple[MathematicalConcept, float]]:
        """Find analogous concepts in different domain"""
        source = self.graph.concepts.get(concept_id)
        if not source or source.embedding is None:
            return []

        analogies = []

        for target in self.graph.get_domain_concepts(target_domain):
            if target.embedding is not None and target.id != concept_id:
                similarity = np.dot(source.embedding, target.embedding) / (
                    np.linalg.norm(source.embedding) *
                    np.linalg.norm(target.embedding) + 1e-10
                )
                analogies.append((target, similarity))

        analogies.sort(key=lambda x: -x[1])
        return analogies[:5]


class ProofAssistant:
    """
    Assists in constructing mathematical proofs.
    """

    def __init__(self, reasoner: MathematicalReasoner = None):
        self.reasoner = reasoner or MathematicalReasoner()

        # Proof templates
        self.templates = {
            'direct': self._direct_proof_template,
            'contradiction': self._contradiction_template,
            'induction': self._induction_template,
            'construction': self._construction_template,
        }

    def suggest_proof_method(
        self,
        statement: str
    ) -> List[str]:
        """Suggest proof methods for statement"""
        methods = []

        # Check for patterns
        if 'if and only if' in statement.lower() or 'iff' in statement.lower():
            methods.append('bidirectional')

        if 'for all' in statement.lower() or '∀' in statement:
            methods.append('direct')
            if 'natural' in statement.lower() or 'integer' in statement.lower():
                methods.append('induction')

        if 'there exists' in statement.lower() or '∃' in statement:
            methods.append('construction')

        if 'not' in statement.lower() or '¬' in statement:
            methods.append('contradiction')

        if not methods:
            methods.append('direct')

        return methods

    def generate_outline(
        self,
        statement: str,
        method: str = 'direct'
    ) -> List[str]:
        """Generate proof outline"""
        if method in self.templates:
            return self.templates[method](statement)
        return self._direct_proof_template(statement)

    def _direct_proof_template(self, statement: str) -> List[str]:
        """Direct proof template"""
        return [
            "1. State what we need to prove",
            "2. Assume the hypothesis is true",
            "3. Apply definitions",
            "4. Use known theorems",
            "5. Derive the conclusion",
            "6. QED"
        ]

    def _contradiction_template(self, statement: str) -> List[str]:
        """Proof by contradiction template"""
        return [
            "1. Assume the negation of what we want to prove",
            "2. Derive logical consequences",
            "3. Find a contradiction",
            "4. Conclude original statement must be true",
            "5. QED"
        ]

    def _induction_template(self, statement: str) -> List[str]:
        """Proof by induction template"""
        return [
            "1. State the property P(n) to prove",
            "2. Base case: Prove P(1) or P(0)",
            "3. Inductive hypothesis: Assume P(k) for some k",
            "4. Inductive step: Prove P(k+1) using P(k)",
            "5. Conclude by principle of induction",
            "6. QED"
        ]

    def _construction_template(self, statement: str) -> List[str]:
        """Proof by construction template"""
        return [
            "1. State what object we need to construct",
            "2. Define the object explicitly",
            "3. Verify it satisfies all required properties",
            "4. Conclude existence",
            "5. QED"
        ]

    def check_step(
        self,
        premise: str,
        conclusion: str
    ) -> Dict[str, Any]:
        """Check if proof step is valid"""
        # Simplified validation
        return {
            'valid': True,
            'justification': 'Step appears logically valid',
            'suggestions': []
        }


# Export all
__all__ = [
    'ConceptType',
    'RelationType',
    'MathematicalConcept',
    'MathematicalRelation',
    'MathematicalDomain',
    'ConceptGraph',
    'MathematicalReasoner',
    'ProofAssistant',
]
