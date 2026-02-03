#!/usr/bin/env python3
"""
BAEL - Knowledge Synthesizer
Knowledge extraction, integration, and synthesis.

This module implements sophisticated knowledge synthesis
for extracting insights from diverse sources, integrating
knowledge, and generating new understanding.

Features:
- Knowledge extraction from text
- Multi-source integration
- Concept mapping
- Relationship discovery
- Knowledge graph construction
- Inference engine
- Contradiction detection
- Knowledge validation
- Abstraction layers
- Knowledge compression
- Insight generation
- Knowledge versioning
"""

import asyncio
import hashlib
import json
import logging
import math
import re
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    TypeVar, Union)
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class KnowledgeType(Enum):
    """Types of knowledge."""
    FACTUAL = "factual"          # Concrete facts
    CONCEPTUAL = "conceptual"     # Abstract concepts
    PROCEDURAL = "procedural"     # How-to knowledge
    RELATIONAL = "relational"     # Relationships between entities
    CAUSAL = "causal"             # Cause-effect relationships
    TEMPORAL = "temporal"         # Time-based knowledge
    CONDITIONAL = "conditional"   # If-then knowledge


class ConfidenceLevel(Enum):
    """Confidence levels for knowledge."""
    CERTAIN = 1.0
    HIGH = 0.8
    MEDIUM = 0.6
    LOW = 0.4
    UNCERTAIN = 0.2
    SPECULATIVE = 0.1


class RelationType(Enum):
    """Types of relationships between concepts."""
    IS_A = "is_a"
    PART_OF = "part_of"
    HAS_PROPERTY = "has_property"
    CAUSES = "causes"
    REQUIRES = "requires"
    SIMILAR_TO = "similar_to"
    OPPOSITE_OF = "opposite_of"
    PRECEDES = "precedes"
    ENABLES = "enables"
    DERIVED_FROM = "derived_from"


class InferenceType(Enum):
    """Types of inference."""
    DEDUCTION = "deduction"
    INDUCTION = "induction"
    ABDUCTION = "abduction"
    ANALOGY = "analogy"


class ValidationStatus(Enum):
    """Status of knowledge validation."""
    UNVALIDATED = "unvalidated"
    VALIDATED = "validated"
    CONTRADICTED = "contradicted"
    SUPERSEDED = "superseded"
    PARTIAL = "partial"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Concept:
    """A knowledge concept."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    type: KnowledgeType = KnowledgeType.CONCEPTUAL
    properties: Dict[str, Any] = field(default_factory=dict)
    aliases: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    embedding: List[float] = field(default_factory=list)


@dataclass
class Relationship:
    """A relationship between concepts."""
    id: str = field(default_factory=lambda: str(uuid4()))
    source_id: str = ""
    target_id: str = ""
    type: RelationType = RelationType.SIMILAR_TO
    strength: float = 1.0  # 0.0 to 1.0
    bidirectional: bool = False
    properties: Dict[str, Any] = field(default_factory=dict)
    evidence: List[str] = field(default_factory=list)


@dataclass
class KnowledgeUnit:
    """A unit of knowledge."""
    id: str = field(default_factory=lambda: str(uuid4()))
    statement: str = ""
    type: KnowledgeType = KnowledgeType.FACTUAL
    concepts: List[str] = field(default_factory=list)  # Concept IDs
    relationships: List[str] = field(default_factory=list)  # Relationship IDs
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    source: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    validation: ValidationStatus = ValidationStatus.UNVALIDATED
    version: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class Insight:
    """A synthesized insight."""
    id: str = field(default_factory=lambda: str(uuid4()))
    description: str = ""
    source_knowledge: List[str] = field(default_factory=list)
    inference_type: InferenceType = InferenceType.DEDUCTION
    confidence: float = 0.5
    implications: List[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)


@dataclass
class Contradiction:
    """A detected contradiction."""
    id: str = field(default_factory=lambda: str(uuid4()))
    knowledge_ids: List[str] = field(default_factory=list)
    description: str = ""
    severity: float = 0.5  # 0.0 to 1.0
    resolution: Optional[str] = None
    detected_at: datetime = field(default_factory=datetime.now)


# =============================================================================
# KNOWLEDGE GRAPH
# =============================================================================

class KnowledgeGraph:
    """
    A graph representation of knowledge.

    Stores concepts as nodes and relationships as edges.
    """

    def __init__(self):
        self.concepts: Dict[str, Concept] = {}
        self.relationships: Dict[str, Relationship] = {}
        self.adjacency: Dict[str, List[str]] = defaultdict(list)  # concept_id -> [relationship_ids]
        self.reverse_adjacency: Dict[str, List[str]] = defaultdict(list)

    def add_concept(self, concept: Concept) -> str:
        """Add a concept to the graph."""
        self.concepts[concept.id] = concept
        return concept.id

    def add_relationship(self, relationship: Relationship) -> str:
        """Add a relationship to the graph."""
        self.relationships[relationship.id] = relationship
        self.adjacency[relationship.source_id].append(relationship.id)
        self.reverse_adjacency[relationship.target_id].append(relationship.id)

        if relationship.bidirectional:
            self.adjacency[relationship.target_id].append(relationship.id)
            self.reverse_adjacency[relationship.source_id].append(relationship.id)

        return relationship.id

    def get_concept(self, concept_id: str) -> Optional[Concept]:
        """Get a concept by ID."""
        return self.concepts.get(concept_id)

    def get_relationships(
        self,
        concept_id: str,
        direction: str = "outgoing"
    ) -> List[Relationship]:
        """Get relationships for a concept."""
        if direction == "outgoing":
            rel_ids = self.adjacency.get(concept_id, [])
        elif direction == "incoming":
            rel_ids = self.reverse_adjacency.get(concept_id, [])
        else:  # both
            rel_ids = list(set(
                self.adjacency.get(concept_id, []) +
                self.reverse_adjacency.get(concept_id, [])
            ))

        return [self.relationships[rid] for rid in rel_ids if rid in self.relationships]

    def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5
    ) -> List[str]:
        """Find path between two concepts."""
        if source_id == target_id:
            return [source_id]

        visited = set()
        queue = [(source_id, [source_id])]

        while queue and len(visited) < 1000:
            current, path = queue.pop(0)

            if current in visited:
                continue
            visited.add(current)

            if len(path) > max_depth:
                continue

            for rel in self.get_relationships(current, "outgoing"):
                next_id = rel.target_id
                if next_id == target_id:
                    return path + [next_id]
                if next_id not in visited:
                    queue.append((next_id, path + [next_id]))

        return []

    def get_neighbors(
        self,
        concept_id: str,
        depth: int = 1
    ) -> Set[str]:
        """Get neighboring concepts up to a certain depth."""
        neighbors = set()
        current_level = {concept_id}

        for _ in range(depth):
            next_level = set()
            for cid in current_level:
                for rel in self.get_relationships(cid, "both"):
                    if rel.source_id != cid:
                        next_level.add(rel.source_id)
                    if rel.target_id != cid:
                        next_level.add(rel.target_id)

            neighbors.update(next_level)
            current_level = next_level

        neighbors.discard(concept_id)
        return neighbors

    def find_by_type(
        self,
        rel_type: RelationType
    ) -> List[Relationship]:
        """Find all relationships of a type."""
        return [r for r in self.relationships.values() if r.type == rel_type]

    def get_stats(self) -> Dict[str, int]:
        """Get graph statistics."""
        return {
            "concepts": len(self.concepts),
            "relationships": len(self.relationships),
            "avg_connections": (
                sum(len(rels) for rels in self.adjacency.values()) /
                max(len(self.concepts), 1)
            )
        }


# =============================================================================
# KNOWLEDGE EXTRACTORS
# =============================================================================

class KnowledgeExtractor(ABC):
    """Base class for knowledge extraction."""

    @abstractmethod
    async def extract(
        self,
        source: Any,
        context: Dict[str, Any] = None
    ) -> List[KnowledgeUnit]:
        """Extract knowledge from source."""
        pass


class TextKnowledgeExtractor(KnowledgeExtractor):
    """
    Extracts knowledge from text.

    Uses pattern matching and NLP techniques.
    """

    def __init__(self):
        self.patterns = {
            KnowledgeType.FACTUAL: [
                r"(\w+) is (?:a|an|the) (\w+)",
                r"(\w+) are (\w+)",
                r"(\w+) has (\w+)"
            ],
            KnowledgeType.CAUSAL: [
                r"(\w+) causes (\w+)",
                r"(\w+) leads to (\w+)",
                r"because of (\w+), (\w+)"
            ],
            KnowledgeType.PROCEDURAL: [
                r"to (\w+), first (\w+)",
                r"(\w+) requires (\w+)",
                r"(\w+) before (\w+)"
            ]
        }

    async def extract(
        self,
        source: str,
        context: Dict[str, Any] = None
    ) -> List[KnowledgeUnit]:
        """Extract knowledge from text."""
        knowledge_units = []

        # Split into sentences
        sentences = re.split(r'[.!?]+', source)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Try each pattern type
            for k_type, patterns in self.patterns.items():
                for pattern in patterns:
                    matches = re.findall(pattern, sentence, re.IGNORECASE)
                    for match in matches:
                        unit = KnowledgeUnit(
                            statement=sentence,
                            type=k_type,
                            source="text_extraction",
                            context=context or {}
                        )
                        knowledge_units.append(unit)
                        break

            # If no pattern matched, still extract as general knowledge
            if sentence and len(sentence) > 10:
                unit = KnowledgeUnit(
                    statement=sentence,
                    type=KnowledgeType.FACTUAL,
                    confidence=ConfidenceLevel.LOW,
                    source="text_extraction",
                    context=context or {}
                )
                knowledge_units.append(unit)

        return knowledge_units


class StructuredKnowledgeExtractor(KnowledgeExtractor):
    """
    Extracts knowledge from structured data.

    Handles JSON, dictionaries, and similar formats.
    """

    async def extract(
        self,
        source: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> List[KnowledgeUnit]:
        """Extract knowledge from structured data."""
        knowledge_units = []

        def extract_recursive(
            data: Any,
            path: List[str] = None
        ) -> None:
            path = path or []

            if isinstance(data, dict):
                for key, value in data.items():
                    new_path = path + [key]

                    if isinstance(value, (str, int, float, bool)):
                        # Create knowledge unit for simple values
                        statement = f"{'.'.join(new_path)} is {value}"
                        unit = KnowledgeUnit(
                            statement=statement,
                            type=KnowledgeType.FACTUAL,
                            confidence=ConfidenceLevel.HIGH,
                            source="structured_extraction",
                            context={"path": new_path, **(context or {})}
                        )
                        knowledge_units.append(unit)
                    else:
                        extract_recursive(value, new_path)

            elif isinstance(data, list):
                for i, item in enumerate(data):
                    extract_recursive(item, path + [f"[{i}]"])

        extract_recursive(source)
        return knowledge_units


# =============================================================================
# INFERENCE ENGINE
# =============================================================================

class InferenceEngine:
    """
    Performs logical inference on knowledge.

    Supports multiple inference types.
    """

    def __init__(self, graph: KnowledgeGraph):
        self.graph = graph
        self.rules: List[Callable] = []

    def add_rule(self, rule: Callable) -> None:
        """Add an inference rule."""
        self.rules.append(rule)

    async def deduce(
        self,
        knowledge_units: List[KnowledgeUnit]
    ) -> List[Insight]:
        """Perform deductive inference."""
        insights = []

        # Transitive inference (A->B, B->C => A->C)
        for rel1 in self.graph.relationships.values():
            for rel2 in self.graph.relationships.values():
                if rel1.target_id == rel2.source_id:
                    if rel1.type == rel2.type == RelationType.IS_A:
                        insight = Insight(
                            description=f"Transitive IS_A: {rel1.source_id} -> {rel2.target_id}",
                            source_knowledge=[rel1.id, rel2.id],
                            inference_type=InferenceType.DEDUCTION,
                            confidence=min(rel1.strength, rel2.strength) * 0.9
                        )
                        insights.append(insight)

        return insights

    async def induce(
        self,
        knowledge_units: List[KnowledgeUnit]
    ) -> List[Insight]:
        """Perform inductive inference."""
        insights = []

        # Find patterns in similar knowledge units
        by_type = defaultdict(list)
        for unit in knowledge_units:
            by_type[unit.type].append(unit)

        for k_type, units in by_type.items():
            if len(units) >= 3:
                # Multiple instances suggest a pattern
                insight = Insight(
                    description=f"Pattern detected: {len(units)} instances of {k_type.value} knowledge",
                    source_knowledge=[u.id for u in units[:5]],
                    inference_type=InferenceType.INDUCTION,
                    confidence=min(0.7, 0.3 + len(units) * 0.1)
                )
                insights.append(insight)

        return insights

    async def abduce(
        self,
        observation: KnowledgeUnit
    ) -> List[Insight]:
        """Perform abductive inference (best explanation)."""
        insights = []

        # Find potential causes
        for rel in self.graph.find_by_type(RelationType.CAUSES):
            target_concept = self.graph.get_concept(rel.target_id)
            if target_concept:
                # Check if observation matches effect
                if observation.statement.lower().find(target_concept.name.lower()) != -1:
                    source_concept = self.graph.get_concept(rel.source_id)
                    if source_concept:
                        insight = Insight(
                            description=f"Possible cause: {source_concept.name} may explain {observation.statement}",
                            source_knowledge=[observation.id],
                            inference_type=InferenceType.ABDUCTION,
                            confidence=rel.strength * 0.6
                        )
                        insights.append(insight)

        return insights

    async def reason_by_analogy(
        self,
        source_concept_id: str,
        target_concept_id: str
    ) -> List[Insight]:
        """Reason by analogy between concepts."""
        insights = []

        source = self.graph.get_concept(source_concept_id)
        target = self.graph.get_concept(target_concept_id)

        if not source or not target:
            return insights

        # Find properties of source that might apply to target
        source_rels = self.graph.get_relationships(source_concept_id, "outgoing")
        target_rels = self.graph.get_relationships(target_concept_id, "outgoing")

        target_types = {r.type for r in target_rels}

        for rel in source_rels:
            if rel.type not in target_types:
                insight = Insight(
                    description=f"By analogy: {target.name} might also have {rel.type.value} relationship",
                    source_knowledge=[],
                    inference_type=InferenceType.ANALOGY,
                    confidence=0.4
                )
                insights.append(insight)

        return insights


# =============================================================================
# CONTRADICTION DETECTOR
# =============================================================================

class ContradictionDetector:
    """
    Detects contradictions in knowledge.

    Identifies conflicting statements.
    """

    def __init__(self):
        self.contradictions: List[Contradiction] = []

    async def detect(
        self,
        knowledge_units: List[KnowledgeUnit]
    ) -> List[Contradiction]:
        """Detect contradictions in knowledge."""
        contradictions = []

        # Group by related concepts
        by_concepts = defaultdict(list)
        for unit in knowledge_units:
            for concept_id in unit.concepts:
                by_concepts[concept_id].append(unit)

        # Check for contradictions within concept groups
        for concept_id, units in by_concepts.items():
            for i, unit1 in enumerate(units):
                for unit2 in units[i+1:]:
                    if self._check_contradiction(unit1, unit2):
                        contradiction = Contradiction(
                            knowledge_ids=[unit1.id, unit2.id],
                            description=f"Potential conflict between statements",
                            severity=0.5
                        )
                        contradictions.append(contradiction)

        self.contradictions.extend(contradictions)
        return contradictions

    def _check_contradiction(
        self,
        unit1: KnowledgeUnit,
        unit2: KnowledgeUnit
    ) -> bool:
        """Check if two units contradict each other."""
        # Simple negation check
        negation_words = ["not", "no", "never", "none", "neither", "cannot"]

        s1_lower = unit1.statement.lower()
        s2_lower = unit2.statement.lower()

        # Check if one negates the other
        s1_has_negation = any(neg in s1_lower for neg in negation_words)
        s2_has_negation = any(neg in s2_lower for neg in negation_words)

        if s1_has_negation != s2_has_negation:
            # Remove negation and check similarity
            s1_clean = s1_lower
            s2_clean = s2_lower
            for neg in negation_words:
                s1_clean = s1_clean.replace(neg, "")
                s2_clean = s2_clean.replace(neg, "")

            # Simple word overlap
            words1 = set(s1_clean.split())
            words2 = set(s2_clean.split())

            overlap = len(words1 & words2) / max(len(words1 | words2), 1)
            return overlap > 0.5

        return False

    async def resolve(
        self,
        contradiction_id: str,
        resolution: str,
        keep_unit_id: str
    ) -> bool:
        """Resolve a contradiction."""
        for c in self.contradictions:
            if c.id == contradiction_id:
                c.resolution = resolution
                return True
        return False


# =============================================================================
# KNOWLEDGE SYNTHESIZER
# =============================================================================

class KnowledgeSynthesizer:
    """
    The master knowledge synthesis system for BAEL.

    Provides unified knowledge extraction, integration,
    inference, and synthesis capabilities.
    """

    def __init__(self):
        self.graph = KnowledgeGraph()
        self.knowledge_units: Dict[str, KnowledgeUnit] = {}
        self.insights: List[Insight] = []

        # Extractors
        self.text_extractor = TextKnowledgeExtractor()
        self.structured_extractor = StructuredKnowledgeExtractor()

        # Engines
        self.inference = InferenceEngine(self.graph)
        self.contradiction_detector = ContradictionDetector()

        # Statistics
        self.extraction_count = 0
        self.inference_count = 0

    async def extract_from_text(
        self,
        text: str,
        source: str = "",
        context: Dict[str, Any] = None
    ) -> List[KnowledgeUnit]:
        """Extract knowledge from text."""
        context = context or {}
        context["source"] = source

        units = await self.text_extractor.extract(text, context)

        for unit in units:
            self.knowledge_units[unit.id] = unit

        self.extraction_count += len(units)
        return units

    async def extract_from_structured(
        self,
        data: Dict[str, Any],
        source: str = "",
        context: Dict[str, Any] = None
    ) -> List[KnowledgeUnit]:
        """Extract knowledge from structured data."""
        context = context or {}
        context["source"] = source

        units = await self.structured_extractor.extract(data, context)

        for unit in units:
            self.knowledge_units[unit.id] = unit

        self.extraction_count += len(units)
        return units

    def add_concept(
        self,
        name: str,
        description: str = "",
        k_type: KnowledgeType = KnowledgeType.CONCEPTUAL,
        properties: Dict[str, Any] = None
    ) -> Concept:
        """Add a concept to the knowledge graph."""
        concept = Concept(
            name=name,
            description=description,
            type=k_type,
            properties=properties or {}
        )

        self.graph.add_concept(concept)
        return concept

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        rel_type: RelationType,
        strength: float = 1.0,
        bidirectional: bool = False
    ) -> Optional[Relationship]:
        """Add a relationship between concepts."""
        if source_id not in self.graph.concepts or target_id not in self.graph.concepts:
            return None

        relationship = Relationship(
            source_id=source_id,
            target_id=target_id,
            type=rel_type,
            strength=strength,
            bidirectional=bidirectional
        )

        self.graph.add_relationship(relationship)
        return relationship

    async def synthesize(
        self,
        knowledge_ids: List[str] = None
    ) -> List[Insight]:
        """Synthesize insights from knowledge."""
        if knowledge_ids:
            units = [
                self.knowledge_units[kid]
                for kid in knowledge_ids
                if kid in self.knowledge_units
            ]
        else:
            units = list(self.knowledge_units.values())

        insights = []

        # Perform different types of inference
        deductions = await self.inference.deduce(units)
        inductions = await self.inference.induce(units)

        insights.extend(deductions)
        insights.extend(inductions)

        self.insights.extend(insights)
        self.inference_count += len(insights)

        return insights

    async def detect_contradictions(
        self,
        knowledge_ids: List[str] = None
    ) -> List[Contradiction]:
        """Detect contradictions in knowledge."""
        if knowledge_ids:
            units = [
                self.knowledge_units[kid]
                for kid in knowledge_ids
                if kid in self.knowledge_units
            ]
        else:
            units = list(self.knowledge_units.values())

        return await self.contradiction_detector.detect(units)

    def validate_knowledge(
        self,
        knowledge_id: str,
        status: ValidationStatus
    ) -> bool:
        """Validate a knowledge unit."""
        unit = self.knowledge_units.get(knowledge_id)
        if unit:
            unit.validation = status
            unit.updated_at = datetime.now()
            return True
        return False

    def query_concepts(
        self,
        concept_id: str,
        depth: int = 2
    ) -> Dict[str, Any]:
        """Query related concepts."""
        concept = self.graph.get_concept(concept_id)
        if not concept:
            return {"error": "Concept not found"}

        neighbors = self.graph.get_neighbors(concept_id, depth)
        relationships = self.graph.get_relationships(concept_id, "both")

        return {
            "concept": concept,
            "neighbors": [
                self.graph.get_concept(nid)
                for nid in neighbors
            ],
            "relationships": relationships
        }

    def find_path(
        self,
        source_id: str,
        target_id: str
    ) -> List[Concept]:
        """Find path between concepts."""
        path_ids = self.graph.find_path(source_id, target_id)
        return [
            self.graph.get_concept(cid)
            for cid in path_ids
            if self.graph.get_concept(cid)
        ]

    async def generate_summary(
        self,
        topic: str = None
    ) -> Dict[str, Any]:
        """Generate knowledge summary."""
        total_units = len(self.knowledge_units)

        by_type = defaultdict(int)
        by_confidence = defaultdict(int)
        by_validation = defaultdict(int)

        for unit in self.knowledge_units.values():
            by_type[unit.type.value] += 1
            by_confidence[unit.confidence.name] += 1
            by_validation[unit.validation.value] += 1

        graph_stats = self.graph.get_stats()

        return {
            "total_knowledge_units": total_units,
            "by_type": dict(by_type),
            "by_confidence": dict(by_confidence),
            "by_validation": dict(by_validation),
            "graph": graph_stats,
            "insights_generated": len(self.insights),
            "contradictions_detected": len(self.contradiction_detector.contradictions)
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get synthesizer statistics."""
        return {
            "knowledge_units": len(self.knowledge_units),
            "concepts": len(self.graph.concepts),
            "relationships": len(self.graph.relationships),
            "insights": len(self.insights),
            "contradictions": len(self.contradiction_detector.contradictions),
            "extraction_count": self.extraction_count,
            "inference_count": self.inference_count
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Knowledge Synthesizer."""
    print("=" * 70)
    print("BAEL - KNOWLEDGE SYNTHESIZER DEMO")
    print("Knowledge Extraction and Synthesis")
    print("=" * 70)
    print()

    # Create synthesizer
    synthesizer = KnowledgeSynthesizer()

    # 1. Extract from Text
    print("1. TEXT KNOWLEDGE EXTRACTION:")
    print("-" * 40)

    text = """
    BAEL is a powerful AI orchestration system. It uses councils for decision making.
    The exploitation engine enables zero-cost operations. Agents execute tasks efficiently.
    Councils coordinate engines. Engines manage agents. Agents use tools.
    Performance optimization leads to better results. Quality assurance prevents errors.
    """

    units = await synthesizer.extract_from_text(text, source="documentation")
    print(f"   Extracted {len(units)} knowledge units from text")
    for unit in units[:3]:
        print(f"   - {unit.statement[:50]}... ({unit.type.value})")
    print()

    # 2. Extract from Structured Data
    print("2. STRUCTURED KNOWLEDGE EXTRACTION:")
    print("-" * 40)

    data = {
        "system": {
            "name": "BAEL",
            "version": "1.0",
            "type": "AI Orchestration"
        },
        "capabilities": {
            "councils": True,
            "engines": True,
            "agents": True
        },
        "cost": "zero"
    }

    structured_units = await synthesizer.extract_from_structured(data, source="config")
    print(f"   Extracted {len(structured_units)} knowledge units from structure")
    for unit in structured_units[:3]:
        print(f"   - {unit.statement}")
    print()

    # 3. Build Knowledge Graph
    print("3. KNOWLEDGE GRAPH CONSTRUCTION:")
    print("-" * 40)

    # Add concepts
    bael = synthesizer.add_concept("BAEL", "The main AI system", KnowledgeType.CONCEPTUAL)
    council = synthesizer.add_concept("Council", "Decision making entity", KnowledgeType.CONCEPTUAL)
    engine = synthesizer.add_concept("Engine", "Execution management entity", KnowledgeType.CONCEPTUAL)
    agent = synthesizer.add_concept("Agent", "Task executor", KnowledgeType.CONCEPTUAL)

    print(f"   Added concepts: BAEL, Council, Engine, Agent")

    # Add relationships
    synthesizer.add_relationship(bael.id, council.id, RelationType.HAS_PROPERTY)
    synthesizer.add_relationship(council.id, engine.id, RelationType.ENABLES)
    synthesizer.add_relationship(engine.id, agent.id, RelationType.ENABLES)
    synthesizer.add_relationship(agent.id, engine.id, RelationType.PART_OF)

    print(f"   Added relationships connecting concepts")

    graph_stats = synthesizer.graph.get_stats()
    print(f"   Graph: {graph_stats['concepts']} concepts, {graph_stats['relationships']} relationships")
    print()

    # 4. Query Knowledge Graph
    print("4. KNOWLEDGE GRAPH QUERIES:")
    print("-" * 40)

    result = synthesizer.query_concepts(council.id, depth=2)
    print(f"   Querying concept: {result['concept'].name}")
    print(f"   Neighbors found: {len(result['neighbors'])}")
    print(f"   Relationships: {len(result['relationships'])}")

    # Find path
    path = synthesizer.find_path(council.id, agent.id)
    print(f"   Path Council -> Agent: {' -> '.join(c.name for c in path)}")
    print()

    # 5. Synthesize Insights
    print("5. INSIGHT SYNTHESIS:")
    print("-" * 40)

    insights = await synthesizer.synthesize()
    print(f"   Generated {len(insights)} insights")
    for insight in insights[:3]:
        print(f"   - {insight.description[:60]}...")
        print(f"     Type: {insight.inference_type.value}, Confidence: {insight.confidence:.2f}")
    print()

    # 6. Detect Contradictions
    print("6. CONTRADICTION DETECTION:")
    print("-" * 40)

    # Add some contradictory knowledge
    await synthesizer.extract_from_text(
        "The system is not scalable. The system cannot handle large loads.",
        source="negative_review"
    )
    await synthesizer.extract_from_text(
        "The system is highly scalable. The system handles large loads easily.",
        source="positive_review"
    )

    contradictions = await synthesizer.detect_contradictions()
    print(f"   Detected {len(contradictions)} potential contradictions")
    for c in contradictions[:2]:
        print(f"   - {c.description} (severity: {c.severity})")
    print()

    # 7. Validate Knowledge
    print("7. KNOWLEDGE VALIDATION:")
    print("-" * 40)

    all_units = list(synthesizer.knowledge_units.values())
    if all_units:
        unit_to_validate = all_units[0]
        synthesizer.validate_knowledge(unit_to_validate.id, ValidationStatus.VALIDATED)
        print(f"   Validated: {unit_to_validate.statement[:50]}...")
    print()

    # 8. Generate Summary
    print("8. KNOWLEDGE SUMMARY:")
    print("-" * 40)

    summary = await synthesizer.generate_summary()

    print(f"   Total Knowledge Units: {summary['total_knowledge_units']}")
    print(f"   By Type:")
    for k_type, count in summary['by_type'].items():
        print(f"     - {k_type}: {count}")
    print(f"   Insights Generated: {summary['insights_generated']}")
    print(f"   Contradictions: {summary['contradictions_detected']}")
    print()

    # 9. Final Statistics
    print("9. FINAL STATISTICS:")
    print("-" * 40)

    stats = synthesizer.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Knowledge Synthesizer Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
