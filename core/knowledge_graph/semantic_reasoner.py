"""
BAEL Semantic Reasoner
=======================

Semantic reasoning over knowledge graphs.
Enables inference and logical deduction.

Features:
- Transitive reasoning
- Inheritance inference
- Rule-based reasoning
- Contradiction detection
- Confidence propagation
"""

import hashlib
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .graph_store import GraphEdge, GraphNode, GraphStore

logger = logging.getLogger(__name__)


class InferenceType(Enum):
    """Types of inference."""
    TRANSITIVE = "transitive"  # If A->B and B->C, then A->C
    INHERITANCE = "inheritance"  # Subclass inference
    RULE_BASED = "rule_based"  # Custom rules
    SYMMETRIC = "symmetric"  # If A->B, then B->A
    INVERSE = "inverse"  # If A->B with R, then B->A with R^-1
    CLOSURE = "closure"  # Reflexive transitive closure


@dataclass
class InferenceRule:
    """A rule for inference."""
    id: str
    name: str

    # Pattern
    antecedent: List[Tuple[str, str, str]]  # [(subject_type, relation, object_type)]
    consequent: Tuple[str, str, str]  # (subject_type, relation, object_type)

    # Confidence
    confidence_factor: float = 0.9

    # Metadata
    description: str = ""


@dataclass
class Inference:
    """An inferred fact."""
    id: str
    inference_type: InferenceType

    # The inferred triple
    subject_id: str
    relation: str
    object_id: str

    # Provenance
    source_facts: List[str] = field(default_factory=list)
    rule_id: Optional[str] = None

    # Confidence
    confidence: float = 1.0

    # Metadata
    inferred_at: datetime = field(default_factory=datetime.now)


@dataclass
class ReasoningResult:
    """Result of reasoning."""
    inferences: List[Inference] = field(default_factory=list)

    # Contradictions found
    contradictions: List[Tuple[Inference, Inference]] = field(default_factory=list)

    # Stats
    rules_applied: int = 0
    iterations: int = 0

    # Timing
    duration_ms: float = 0.0


class SemanticReasoner:
    """
    Semantic reasoner for BAEL.

    Performs inference over knowledge graphs.
    """

    # Transitive relations
    TRANSITIVE_RELATIONS = {
        "is_a", "part_of", "contains", "depends_on",
        "ancestor_of", "descendant_of", "located_in",
    }

    # Symmetric relations
    SYMMETRIC_RELATIONS = {
        "related_to", "similar_to", "connected_to",
        "sibling_of", "partner_of", "knows",
    }

    # Inverse relation pairs
    INVERSE_RELATIONS = {
        "parent_of": "child_of",
        "created_by": "creator_of",
        "contains": "contained_in",
        "owns": "owned_by",
        "works_for": "employs",
    }

    def __init__(self, graph: GraphStore):
        self.graph = graph

        # Rules
        self._rules: Dict[str, InferenceRule] = {}

        # Inferences
        self._inferences: Dict[str, Inference] = {}

        # Contradiction handlers
        self._contradiction_handlers: List[Callable] = []

        # Stats
        self.stats = {
            "inferences_made": 0,
            "contradictions_found": 0,
            "rules_registered": 0,
        }

    def add_rule(self, rule: InferenceRule) -> None:
        """Add an inference rule."""
        self._rules[rule.id] = rule
        self.stats["rules_registered"] += 1

    def reason(
        self,
        max_iterations: int = 10,
        inference_types: Optional[List[InferenceType]] = None,
    ) -> ReasoningResult:
        """
        Perform reasoning over the graph.

        Args:
            max_iterations: Maximum reasoning iterations
            inference_types: Types of inference to perform

        Returns:
            Reasoning result
        """
        import time
        start = time.time()

        result = ReasoningResult()
        inference_types = inference_types or list(InferenceType)

        # Fixed-point iteration
        for iteration in range(max_iterations):
            new_inferences = []

            if InferenceType.TRANSITIVE in inference_types:
                new_inferences.extend(self._infer_transitive())

            if InferenceType.SYMMETRIC in inference_types:
                new_inferences.extend(self._infer_symmetric())

            if InferenceType.INVERSE in inference_types:
                new_inferences.extend(self._infer_inverse())

            if InferenceType.RULE_BASED in inference_types:
                rule_inferences = self._infer_by_rules()
                new_inferences.extend(rule_inferences)
                result.rules_applied += len(rule_inferences)

            if InferenceType.INHERITANCE in inference_types:
                new_inferences.extend(self._infer_inheritance())

            # Check for contradictions
            for inf in new_inferences:
                contradiction = self._check_contradiction(inf)
                if contradiction:
                    result.contradictions.append((inf, contradiction))
                    self.stats["contradictions_found"] += 1

            # Add to graph
            for inf in new_inferences:
                self._add_inference_to_graph(inf)
                self._inferences[inf.id] = inf

            result.inferences.extend(new_inferences)
            result.iterations = iteration + 1

            # Fixed point reached
            if not new_inferences:
                break

        result.duration_ms = (time.time() - start) * 1000
        self.stats["inferences_made"] += len(result.inferences)

        return result

    def _infer_transitive(self) -> List[Inference]:
        """Infer transitive relations."""
        inferences = []

        for relation in self.TRANSITIVE_RELATIONS:
            # Find edges with this relation
            edges = [e for e in self.graph._edges.values() if e.label == relation]

            # Build adjacency map
            adjacency: Dict[str, Set[str]] = defaultdict(set)
            for edge in edges:
                adjacency[edge.source_id].add(edge.target_id)

            # Find transitive closure
            for a in adjacency:
                for b in adjacency[a]:
                    for c in adjacency.get(b, []):
                        if c not in adjacency[a] and a != c:
                            # Check if not already inferred
                            inf_id = hashlib.md5(
                                f"trans:{a}:{relation}:{c}".encode()
                            ).hexdigest()[:12]

                            if inf_id not in self._inferences:
                                inference = Inference(
                                    id=inf_id,
                                    inference_type=InferenceType.TRANSITIVE,
                                    subject_id=a,
                                    relation=relation,
                                    object_id=c,
                                    source_facts=[f"{a}->{b}", f"{b}->{c}"],
                                    confidence=0.9,
                                )
                                inferences.append(inference)

        return inferences

    def _infer_symmetric(self) -> List[Inference]:
        """Infer symmetric relations."""
        inferences = []

        for relation in self.SYMMETRIC_RELATIONS:
            edges = [e for e in self.graph._edges.values() if e.label == relation]

            for edge in edges:
                # Check if reverse exists
                reverse_exists = any(
                    e.source_id == edge.target_id and
                    e.target_id == edge.source_id and
                    e.label == relation
                    for e in self.graph._edges.values()
                )

                if not reverse_exists:
                    inf_id = hashlib.md5(
                        f"sym:{edge.target_id}:{relation}:{edge.source_id}".encode()
                    ).hexdigest()[:12]

                    if inf_id not in self._inferences:
                        inference = Inference(
                            id=inf_id,
                            inference_type=InferenceType.SYMMETRIC,
                            subject_id=edge.target_id,
                            relation=relation,
                            object_id=edge.source_id,
                            source_facts=[edge.id],
                            confidence=1.0,
                        )
                        inferences.append(inference)

        return inferences

    def _infer_inverse(self) -> List[Inference]:
        """Infer inverse relations."""
        inferences = []

        for relation, inverse in self.INVERSE_RELATIONS.items():
            edges = [e for e in self.graph._edges.values() if e.label == relation]

            for edge in edges:
                # Check if inverse exists
                inverse_exists = any(
                    e.source_id == edge.target_id and
                    e.target_id == edge.source_id and
                    e.label == inverse
                    for e in self.graph._edges.values()
                )

                if not inverse_exists:
                    inf_id = hashlib.md5(
                        f"inv:{edge.target_id}:{inverse}:{edge.source_id}".encode()
                    ).hexdigest()[:12]

                    if inf_id not in self._inferences:
                        inference = Inference(
                            id=inf_id,
                            inference_type=InferenceType.INVERSE,
                            subject_id=edge.target_id,
                            relation=inverse,
                            object_id=edge.source_id,
                            source_facts=[edge.id],
                            confidence=1.0,
                        )
                        inferences.append(inference)

        return inferences

    def _infer_by_rules(self) -> List[Inference]:
        """Apply custom inference rules."""
        inferences = []

        for rule in self._rules.values():
            # Try to match antecedent pattern
            matches = self._match_pattern(rule.antecedent)

            for match in matches:
                # Generate consequent
                subject_id = match.get("subject")
                object_id = match.get("object")

                if subject_id and object_id:
                    inf_id = hashlib.md5(
                        f"rule:{rule.id}:{subject_id}:{object_id}".encode()
                    ).hexdigest()[:12]

                    if inf_id not in self._inferences:
                        inference = Inference(
                            id=inf_id,
                            inference_type=InferenceType.RULE_BASED,
                            subject_id=subject_id,
                            relation=rule.consequent[1],
                            object_id=object_id,
                            rule_id=rule.id,
                            confidence=rule.confidence_factor,
                        )
                        inferences.append(inference)

        return inferences

    def _match_pattern(
        self,
        pattern: List[Tuple[str, str, str]],
    ) -> List[Dict[str, str]]:
        """Match a pattern against the graph."""
        matches = []

        # Simplified pattern matching
        # In production, would use proper graph pattern matching
        for edge in self.graph._edges.values():
            source = self.graph.get_node(edge.source_id)
            target = self.graph.get_node(edge.target_id)

            if source and target:
                for subj_type, relation, obj_type in pattern:
                    if (source.node_type == subj_type or subj_type == "*") and \
                       (edge.label == relation or relation == "*") and \
                       (target.node_type == obj_type or obj_type == "*"):
                        matches.append({
                            "subject": edge.source_id,
                            "object": edge.target_id,
                            "relation": edge.label,
                        })

        return matches

    def _infer_inheritance(self) -> List[Inference]:
        """Infer based on inheritance (is_a relations)."""
        inferences = []

        # Find is_a hierarchy
        is_a_edges = [e for e in self.graph._edges.values() if e.label == "is_a"]

        # For each instance, inherit properties from its class
        for edge in is_a_edges:
            instance_id = edge.source_id
            class_id = edge.target_id

            # Get class properties (edges)
            class_edges = self.graph.get_edges_for_node(class_id, "out")

            for class_edge in class_edges:
                if class_edge.label not in ["is_a", "instance_of"]:
                    # Check if instance already has this relation
                    instance_edges = self.graph.get_edges_for_node(instance_id, "out")
                    has_relation = any(
                        e.label == class_edge.label and e.target_id == class_edge.target_id
                        for e in instance_edges
                    )

                    if not has_relation:
                        inf_id = hashlib.md5(
                            f"inherit:{instance_id}:{class_edge.label}:{class_edge.target_id}".encode()
                        ).hexdigest()[:12]

                        if inf_id not in self._inferences:
                            inference = Inference(
                                id=inf_id,
                                inference_type=InferenceType.INHERITANCE,
                                subject_id=instance_id,
                                relation=class_edge.label,
                                object_id=class_edge.target_id,
                                source_facts=[edge.id, class_edge.id],
                                confidence=0.85,
                            )
                            inferences.append(inference)

        return inferences

    def _check_contradiction(
        self,
        inference: Inference,
    ) -> Optional[Inference]:
        """Check if inference contradicts existing facts."""
        # Check for mutually exclusive relations
        exclusions = {
            "alive": "dead",
            "true": "false",
            "open": "closed",
            "active": "inactive",
        }

        for existing in self._inferences.values():
            if existing.subject_id == inference.subject_id:
                if existing.relation in exclusions:
                    if inference.relation == exclusions[existing.relation]:
                        return existing

        return None

    def _add_inference_to_graph(self, inference: Inference) -> None:
        """Add inference as edge to graph."""
        self.graph.add_edge(
            source_id=inference.subject_id,
            target_id=inference.object_id,
            label=inference.relation,
            weight=inference.confidence,
            properties={"inferred": True, "inference_id": inference.id},
        )

    def explain(self, inference_id: str) -> str:
        """Explain how an inference was made."""
        if inference_id not in self._inferences:
            return "Inference not found"

        inf = self._inferences[inference_id]

        subject = self.graph.get_node(inf.subject_id)
        obj = self.graph.get_node(inf.object_id)

        lines = [
            f"Inference: {subject.label if subject else inf.subject_id} "
            f"--[{inf.relation}]--> {obj.label if obj else inf.object_id}",
            f"Type: {inf.inference_type.value}",
            f"Confidence: {inf.confidence:.0%}",
        ]

        if inf.source_facts:
            lines.append(f"Based on: {inf.source_facts}")

        if inf.rule_id:
            rule = self._rules.get(inf.rule_id)
            if rule:
                lines.append(f"Rule: {rule.name}")

        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        """Get reasoner statistics."""
        return {
            **self.stats,
            "active_inferences": len(self._inferences),
        }


def demo():
    """Demonstrate semantic reasoner."""
    print("=" * 60)
    print("BAEL Semantic Reasoner Demo")
    print("=" * 60)

    # Create graph
    store = GraphStore()

    # Add some facts
    dog = store.add_node("Dog", "class")
    animal = store.add_node("Animal", "class")
    mammal = store.add_node("Mammal", "class")
    fido = store.add_node("Fido", "instance")
    legs = store.add_node("Legs", "property")

    store.add_edge(dog.id, mammal.id, "is_a")
    store.add_edge(mammal.id, animal.id, "is_a")
    store.add_edge(fido.id, dog.id, "is_a")
    store.add_edge(dog.id, legs.id, "has")

    john = store.add_node("John", "person")
    mary = store.add_node("Mary", "person")
    store.add_edge(john.id, mary.id, "knows")

    print(f"\nInitial graph: {store.stats['nodes_added']} nodes, {store.stats['edges_added']} edges")

    # Create reasoner
    reasoner = SemanticReasoner(store)

    # Perform reasoning
    print("\nPerforming reasoning...")
    result = reasoner.reason(max_iterations=5)

    print(f"  Iterations: {result.iterations}")
    print(f"  Inferences made: {len(result.inferences)}")
    print(f"  Duration: {result.duration_ms:.2f}ms")

    print("\nInferences:")
    for inf in result.inferences:
        subject = store.get_node(inf.subject_id)
        obj = store.get_node(inf.object_id)
        print(f"  [{inf.inference_type.value}] {subject.label} --[{inf.relation}]--> {obj.label}")
        print(f"    Confidence: {inf.confidence:.0%}")

    if result.contradictions:
        print(f"\nContradictions found: {len(result.contradictions)}")

    # Explain an inference
    if result.inferences:
        print(f"\nExplanation for first inference:")
        print(reasoner.explain(result.inferences[0].id))

    print(f"\nStats: {reasoner.get_stats()}")


if __name__ == "__main__":
    demo()
