#!/usr/bin/env python3
"""
BAEL - Knowledge Synthesis System
Advanced knowledge creation, integration, and synthesis.

Features:
- Knowledge extraction from multiple sources
- Concept synthesis and abstraction
- Knowledge graph construction
- Inference and deduction
- Knowledge validation and verification
- Cross-domain integration
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
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# TYPES
# =============================================================================

class KnowledgeType(Enum):
    """Types of knowledge."""
    FACTUAL = "factual"           # Facts and data
    PROCEDURAL = "procedural"     # How-to knowledge
    CONCEPTUAL = "conceptual"     # Abstract concepts
    METACOGNITIVE = "metacognitive"  # Knowledge about knowledge
    CAUSAL = "causal"             # Cause-effect relationships
    TEMPORAL = "temporal"         # Time-based knowledge
    SPATIAL = "spatial"           # Location-based knowledge


class ConfidenceLevel(Enum):
    """Confidence levels."""
    CERTAIN = "certain"           # Verified multiple times
    HIGH = "high"                 # Strong evidence
    MEDIUM = "medium"             # Moderate evidence
    LOW = "low"                   # Weak evidence
    UNCERTAIN = "uncertain"       # No verification


class RelationType(Enum):
    """Types of relationships."""
    IS_A = "is_a"                # Taxonomy
    PART_OF = "part_of"          # Composition
    CAUSES = "causes"            # Causation
    CORRELATES = "correlates"    # Correlation
    PRECEDES = "precedes"        # Temporal
    CONTRADICTS = "contradicts"  # Conflict
    SUPPORTS = "supports"        # Support
    SIMILAR_TO = "similar_to"    # Similarity
    OPPOSITE_OF = "opposite_of"  # Opposition
    INSTANCE_OF = "instance_of"  # Instantiation


@dataclass
class KnowledgeUnit:
    """A unit of knowledge."""
    id: str
    content: str
    knowledge_type: KnowledgeType
    confidence: ConfidenceLevel
    source: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "content": self.content,
            "knowledge_type": self.knowledge_type.value,
            "confidence": self.confidence.value,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
            "tags": list(self.tags),
            "evidence": self.evidence
        }


@dataclass
class Concept:
    """An abstract concept."""
    id: str
    name: str
    definition: str
    properties: Dict[str, Any] = field(default_factory=dict)
    examples: List[str] = field(default_factory=list)
    counter_examples: List[str] = field(default_factory=list)
    parent_concepts: Set[str] = field(default_factory=set)
    child_concepts: Set[str] = field(default_factory=set)
    related_knowledge: Set[str] = field(default_factory=set)


@dataclass
class Relationship:
    """A relationship between knowledge units or concepts."""
    id: str
    source_id: str
    target_id: str
    relation_type: RelationType
    strength: float = 1.0
    evidence: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Inference:
    """An inference from knowledge."""
    id: str
    premise_ids: List[str]
    conclusion: str
    inference_type: str  # deduction, induction, abduction
    confidence: float
    reasoning_chain: List[str] = field(default_factory=list)


# =============================================================================
# KNOWLEDGE EXTRACTION
# =============================================================================

class KnowledgeExtractor(ABC):
    """Abstract knowledge extractor."""

    @abstractmethod
    async def extract(
        self,
        source: Any,
        context: Dict[str, Any] = None
    ) -> List[KnowledgeUnit]:
        """Extract knowledge from source."""
        pass


class TextExtractor(KnowledgeExtractor):
    """Extract knowledge from text."""

    def __init__(self):
        # Patterns for extraction
        self.fact_patterns = [
            r"(.+?) is (.+)",
            r"(.+?) are (.+)",
            r"(.+?) has (.+)",
            r"(.+?) can (.+)",
            r"(.+?) means (.+)"
        ]

        self.causal_patterns = [
            r"(.+?) causes (.+)",
            r"(.+?) leads to (.+)",
            r"(.+?) results in (.+)",
            r"because (.+?), (.+)",
            r"(.+?) due to (.+)"
        ]

        self.procedure_patterns = [
            r"to (.+?), you (.+)",
            r"first (.+?), then (.+)",
            r"step \d+: (.+)"
        ]

    async def extract(
        self,
        source: str,
        context: Dict[str, Any] = None
    ) -> List[KnowledgeUnit]:
        """Extract knowledge from text."""
        units = []
        context = context or {}

        # Split into sentences
        sentences = self._split_sentences(source)

        for sentence in sentences:
            # Try fact patterns
            for pattern in self.fact_patterns:
                match = re.match(pattern, sentence, re.IGNORECASE)
                if match:
                    units.append(KnowledgeUnit(
                        id=str(uuid4()),
                        content=sentence,
                        knowledge_type=KnowledgeType.FACTUAL,
                        confidence=ConfidenceLevel.MEDIUM,
                        source=context.get("source", "text"),
                        metadata={"pattern": "fact", "groups": match.groups()}
                    ))
                    break

            # Try causal patterns
            for pattern in self.causal_patterns:
                match = re.search(pattern, sentence, re.IGNORECASE)
                if match:
                    units.append(KnowledgeUnit(
                        id=str(uuid4()),
                        content=sentence,
                        knowledge_type=KnowledgeType.CAUSAL,
                        confidence=ConfidenceLevel.MEDIUM,
                        source=context.get("source", "text"),
                        metadata={"pattern": "causal", "groups": match.groups()}
                    ))
                    break

            # Try procedure patterns
            for pattern in self.procedure_patterns:
                match = re.search(pattern, sentence, re.IGNORECASE)
                if match:
                    units.append(KnowledgeUnit(
                        id=str(uuid4()),
                        content=sentence,
                        knowledge_type=KnowledgeType.PROCEDURAL,
                        confidence=ConfidenceLevel.MEDIUM,
                        source=context.get("source", "text"),
                        metadata={"pattern": "procedure", "groups": match.groups()}
                    ))
                    break

        return units

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]


class StructuredExtractor(KnowledgeExtractor):
    """Extract knowledge from structured data."""

    async def extract(
        self,
        source: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> List[KnowledgeUnit]:
        """Extract knowledge from structured data."""
        units = []
        context = context or {}

        def process_dict(d: Dict, path: str = ""):
            for key, value in d.items():
                current_path = f"{path}.{key}" if path else key

                if isinstance(value, dict):
                    process_dict(value, current_path)
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            process_dict(item, f"{current_path}[{i}]")
                        else:
                            units.append(KnowledgeUnit(
                                id=str(uuid4()),
                                content=f"{current_path}[{i}] = {item}",
                                knowledge_type=KnowledgeType.FACTUAL,
                                confidence=ConfidenceLevel.HIGH,
                                source=context.get("source", "structured"),
                                metadata={"path": f"{current_path}[{i}]", "value": item}
                            ))
                else:
                    units.append(KnowledgeUnit(
                        id=str(uuid4()),
                        content=f"{current_path} = {value}",
                        knowledge_type=KnowledgeType.FACTUAL,
                        confidence=ConfidenceLevel.HIGH,
                        source=context.get("source", "structured"),
                        metadata={"path": current_path, "value": value}
                    ))

        process_dict(source)
        return units


# =============================================================================
# KNOWLEDGE GRAPH
# =============================================================================

class KnowledgeGraph:
    """Graph-based knowledge storage."""

    def __init__(self):
        self.units: Dict[str, KnowledgeUnit] = {}
        self.concepts: Dict[str, Concept] = {}
        self.relationships: Dict[str, Relationship] = {}

        # Indices
        self.type_index: Dict[KnowledgeType, Set[str]] = defaultdict(set)
        self.tag_index: Dict[str, Set[str]] = defaultdict(set)
        self.source_index: Dict[str, Set[str]] = defaultdict(set)
        self.relation_index: Dict[str, Set[str]] = defaultdict(set)

    def add_unit(self, unit: KnowledgeUnit) -> None:
        """Add knowledge unit to graph."""
        self.units[unit.id] = unit
        self.type_index[unit.knowledge_type].add(unit.id)
        self.source_index[unit.source].add(unit.id)

        for tag in unit.tags:
            self.tag_index[tag].add(unit.id)

    def add_concept(self, concept: Concept) -> None:
        """Add concept to graph."""
        self.concepts[concept.id] = concept

    def add_relationship(self, relationship: Relationship) -> None:
        """Add relationship to graph."""
        self.relationships[relationship.id] = relationship
        self.relation_index[relationship.source_id].add(relationship.id)
        self.relation_index[relationship.target_id].add(relationship.id)

    def get_unit(self, unit_id: str) -> Optional[KnowledgeUnit]:
        """Get knowledge unit by ID."""
        return self.units.get(unit_id)

    def get_concept(self, concept_id: str) -> Optional[Concept]:
        """Get concept by ID."""
        return self.concepts.get(concept_id)

    def get_related(self, entity_id: str) -> List[Relationship]:
        """Get relationships for entity."""
        relation_ids = self.relation_index.get(entity_id, set())
        return [self.relationships[rid] for rid in relation_ids]

    def query_by_type(self, knowledge_type: KnowledgeType) -> List[KnowledgeUnit]:
        """Query by knowledge type."""
        unit_ids = self.type_index.get(knowledge_type, set())
        return [self.units[uid] for uid in unit_ids]

    def query_by_tag(self, tag: str) -> List[KnowledgeUnit]:
        """Query by tag."""
        unit_ids = self.tag_index.get(tag, set())
        return [self.units[uid] for uid in unit_ids]

    def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5
    ) -> Optional[List[str]]:
        """Find path between entities."""
        visited = set()
        queue = [(source_id, [source_id])]

        while queue:
            current, path = queue.pop(0)

            if current == target_id:
                return path

            if current in visited or len(path) > max_depth:
                continue

            visited.add(current)

            for rel in self.get_related(current):
                next_id = rel.target_id if rel.source_id == current else rel.source_id
                if next_id not in visited:
                    queue.append((next_id, path + [next_id]))

        return None

    def get_neighborhood(
        self,
        entity_id: str,
        depth: int = 2
    ) -> Dict[str, Any]:
        """Get neighborhood of entity."""
        nodes = set()
        edges = []

        def traverse(eid: str, d: int):
            if d <= 0 or eid in nodes:
                return
            nodes.add(eid)

            for rel in self.get_related(eid):
                edges.append({
                    "source": rel.source_id,
                    "target": rel.target_id,
                    "type": rel.relation_type.value
                })
                other = rel.target_id if rel.source_id == eid else rel.source_id
                traverse(other, d - 1)

        traverse(entity_id, depth)

        return {
            "nodes": list(nodes),
            "edges": edges
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        return {
            "units": len(self.units),
            "concepts": len(self.concepts),
            "relationships": len(self.relationships),
            "types": {t.value: len(ids) for t, ids in self.type_index.items()},
            "sources": {s: len(ids) for s, ids in self.source_index.items()}
        }


# =============================================================================
# CONCEPT SYNTHESIS
# =============================================================================

class ConceptSynthesizer:
    """Synthesize abstract concepts from knowledge."""

    def __init__(self):
        self.synthesis_history: List[Dict[str, Any]] = []

    async def synthesize(
        self,
        knowledge_units: List[KnowledgeUnit]
    ) -> Optional[Concept]:
        """Synthesize concept from knowledge units."""
        if not knowledge_units:
            return None

        # Find common patterns
        patterns = self._find_patterns(knowledge_units)

        # Generate concept name
        name = self._generate_name(patterns, knowledge_units)

        # Generate definition
        definition = self._generate_definition(patterns, knowledge_units)

        # Extract properties
        properties = self._extract_properties(knowledge_units)

        # Create concept
        concept = Concept(
            id=str(uuid4()),
            name=name,
            definition=definition,
            properties=properties,
            examples=[u.content for u in knowledge_units[:3]],
            related_knowledge={u.id for u in knowledge_units}
        )

        self.synthesis_history.append({
            "concept_id": concept.id,
            "from_units": [u.id for u in knowledge_units],
            "timestamp": datetime.now().isoformat()
        })

        return concept

    def _find_patterns(
        self,
        units: List[KnowledgeUnit]
    ) -> Dict[str, Any]:
        """Find common patterns in knowledge units."""
        patterns = {
            "common_words": defaultdict(int),
            "common_types": defaultdict(int),
            "common_tags": defaultdict(int)
        }

        for unit in units:
            # Word frequency
            words = unit.content.lower().split()
            for word in words:
                if len(word) > 3:  # Skip short words
                    patterns["common_words"][word] += 1

            # Type frequency
            patterns["common_types"][unit.knowledge_type.value] += 1

            # Tag frequency
            for tag in unit.tags:
                patterns["common_tags"][tag] += 1

        return patterns

    def _generate_name(
        self,
        patterns: Dict[str, Any],
        units: List[KnowledgeUnit]
    ) -> str:
        """Generate concept name."""
        # Get most common significant words
        word_counts = patterns["common_words"]
        if word_counts:
            top_words = sorted(
                word_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:2]
            return "_".join(word for word, _ in top_words)
        return f"concept_{len(units)}"

    def _generate_definition(
        self,
        patterns: Dict[str, Any],
        units: List[KnowledgeUnit]
    ) -> str:
        """Generate concept definition."""
        if not units:
            return ""

        # Find most common type
        type_counts = patterns["common_types"]
        main_type = max(type_counts.items(), key=lambda x: x[1])[0] if type_counts else "general"

        # Build definition
        sample = units[0].content if units else ""
        return f"A {main_type} concept representing: {sample[:100]}"

    def _extract_properties(
        self,
        units: List[KnowledgeUnit]
    ) -> Dict[str, Any]:
        """Extract concept properties."""
        properties = {
            "count": len(units),
            "types": list(set(u.knowledge_type.value for u in units)),
            "avg_confidence": sum(
                {"certain": 1.0, "high": 0.8, "medium": 0.6, "low": 0.4, "uncertain": 0.2}.get(
                    u.confidence.value, 0.5
                ) for u in units
            ) / len(units) if units else 0,
            "sources": list(set(u.source for u in units))
        }
        return properties


# =============================================================================
# INFERENCE ENGINE
# =============================================================================

class InferenceEngine:
    """Engine for knowledge inference."""

    def __init__(self, knowledge_graph: KnowledgeGraph):
        self.graph = knowledge_graph
        self.inference_cache: Dict[str, Inference] = {}

    async def deduce(
        self,
        premises: List[str]
    ) -> List[Inference]:
        """Perform deductive inference."""
        inferences = []

        # Get knowledge units for premises
        premise_units = []
        for premise_id in premises:
            unit = self.graph.get_unit(premise_id)
            if unit:
                premise_units.append(unit)

        if len(premise_units) < 2:
            return []

        # Check for transitive relationships
        # If A -> B and B -> C, then A -> C
        for i, unit1 in enumerate(premise_units):
            for unit2 in premise_units[i+1:]:
                rels1 = self.graph.get_related(unit1.id)
                for rel1 in rels1:
                    if rel1.target_id == unit2.id or rel1.source_id == unit2.id:
                        continue

                    # Check if unit2 is related to rel1's target
                    rels2 = self.graph.get_related(unit2.id)
                    for rel2 in rels2:
                        # Transitive inference
                        if rel1.relation_type == rel2.relation_type:
                            inference = Inference(
                                id=str(uuid4()),
                                premise_ids=[unit1.id, unit2.id],
                                conclusion=f"Transitive {rel1.relation_type.value}: {unit1.content} -> {rel2.target_id}",
                                inference_type="deduction",
                                confidence=rel1.strength * rel2.strength,
                                reasoning_chain=[
                                    f"{unit1.id} {rel1.relation_type.value} {rel1.target_id}",
                                    f"{unit2.id} {rel2.relation_type.value} {rel2.target_id}"
                                ]
                            )
                            inferences.append(inference)

        return inferences

    async def induce(
        self,
        examples: List[str]
    ) -> List[Inference]:
        """Perform inductive inference."""
        inferences = []

        # Get knowledge units
        example_units = []
        for example_id in examples:
            unit = self.graph.get_unit(example_id)
            if unit:
                example_units.append(unit)

        if len(example_units) < 2:
            return []

        # Find common patterns
        common_types = set(u.knowledge_type for u in example_units)
        common_tags = set.intersection(*[u.tags for u in example_units]) if example_units else set()

        # Generate generalizations
        if len(common_types) == 1:
            kt = list(common_types)[0]
            inference = Inference(
                id=str(uuid4()),
                premise_ids=[u.id for u in example_units],
                conclusion=f"All examples are of type {kt.value}",
                inference_type="induction",
                confidence=len(example_units) / (len(example_units) + 1),
                reasoning_chain=[f"Example {i+1}: {u.content[:50]}" for i, u in enumerate(example_units)]
            )
            inferences.append(inference)

        if common_tags:
            inference = Inference(
                id=str(uuid4()),
                premise_ids=[u.id for u in example_units],
                conclusion=f"Common tags: {', '.join(common_tags)}",
                inference_type="induction",
                confidence=len(example_units) / (len(example_units) + 2),
                reasoning_chain=[f"Tags for {u.id}: {u.tags}" for u in example_units]
            )
            inferences.append(inference)

        return inferences

    async def abduct(
        self,
        observation: str,
        hypotheses: List[str]
    ) -> List[Tuple[str, float]]:
        """Perform abductive inference (inference to best explanation)."""
        scored_hypotheses = []

        for hypothesis_id in hypotheses:
            unit = self.graph.get_unit(hypothesis_id)
            if not unit:
                continue

            # Score hypothesis based on:
            # 1. Type match
            # 2. Confidence level
            # 3. Connections to observation

            score = 0.5

            # Higher confidence = better explanation
            conf_scores = {"certain": 0.3, "high": 0.2, "medium": 0.1, "low": 0.05, "uncertain": 0}
            score += conf_scores.get(unit.confidence.value, 0)

            # Check for causal relationships
            rels = self.graph.get_related(unit.id)
            for rel in rels:
                if rel.relation_type == RelationType.CAUSES:
                    score += 0.2 * rel.strength

            scored_hypotheses.append((hypothesis_id, min(1.0, score)))

        # Sort by score
        scored_hypotheses.sort(key=lambda x: x[1], reverse=True)

        return scored_hypotheses


# =============================================================================
# KNOWLEDGE VALIDATOR
# =============================================================================

class KnowledgeValidator:
    """Validate knowledge consistency and accuracy."""

    def __init__(self, knowledge_graph: KnowledgeGraph):
        self.graph = knowledge_graph

    async def validate(
        self,
        unit: KnowledgeUnit
    ) -> Dict[str, Any]:
        """Validate a knowledge unit."""
        validation = {
            "is_valid": True,
            "confidence_score": 0.5,
            "issues": [],
            "supporting_evidence": [],
            "contradicting_evidence": []
        }

        # Check for contradictions
        related = self.graph.get_related(unit.id)
        for rel in related:
            if rel.relation_type == RelationType.CONTRADICTS:
                validation["is_valid"] = False
                other = self.graph.get_unit(rel.target_id)
                if other:
                    validation["issues"].append(f"Contradicts: {other.content[:50]}")
                    validation["contradicting_evidence"].append(rel.target_id)
            elif rel.relation_type == RelationType.SUPPORTS:
                validation["supporting_evidence"].append(rel.target_id)

        # Calculate confidence
        support_count = len(validation["supporting_evidence"])
        contradict_count = len(validation["contradicting_evidence"])

        base_conf = {"certain": 0.9, "high": 0.75, "medium": 0.5, "low": 0.25, "uncertain": 0.1}
        confidence = base_conf.get(unit.confidence.value, 0.5)

        # Adjust based on evidence
        confidence += 0.1 * support_count
        confidence -= 0.15 * contradict_count

        validation["confidence_score"] = max(0, min(1, confidence))

        return validation

    async def find_contradictions(self) -> List[Tuple[str, str]]:
        """Find contradictions in knowledge graph."""
        contradictions = []

        for rel_id, rel in self.graph.relationships.items():
            if rel.relation_type == RelationType.CONTRADICTS:
                contradictions.append((rel.source_id, rel.target_id))

        return contradictions

    async def verify_chain(
        self,
        chain: List[str]
    ) -> Dict[str, Any]:
        """Verify a chain of knowledge."""
        verification = {
            "is_valid": True,
            "weak_links": [],
            "chain_confidence": 1.0
        }

        for i in range(len(chain) - 1):
            source_id = chain[i]
            target_id = chain[i + 1]

            # Check if relationship exists
            path = self.graph.find_path(source_id, target_id, max_depth=2)

            if not path or len(path) > 2:
                verification["is_valid"] = False
                verification["weak_links"].append((source_id, target_id))
                verification["chain_confidence"] *= 0.5
            else:
                # Get relationship strength
                rels = self.graph.get_related(source_id)
                max_strength = 0
                for rel in rels:
                    if rel.target_id == target_id or rel.source_id == target_id:
                        max_strength = max(max_strength, rel.strength)

                verification["chain_confidence"] *= max_strength if max_strength > 0 else 0.7

        return verification


# =============================================================================
# KNOWLEDGE SYNTHESIS SYSTEM
# =============================================================================

class KnowledgeSynthesisSystem:
    """Main knowledge synthesis system."""

    def __init__(self):
        self.graph = KnowledgeGraph()
        self.synthesizer = ConceptSynthesizer()
        self.inference_engine = InferenceEngine(self.graph)
        self.validator = KnowledgeValidator(self.graph)

        # Extractors
        self.extractors: Dict[str, KnowledgeExtractor] = {
            "text": TextExtractor(),
            "structured": StructuredExtractor()
        }

    async def ingest(
        self,
        source: Any,
        source_type: str = "text",
        context: Dict[str, Any] = None
    ) -> List[KnowledgeUnit]:
        """Ingest knowledge from source."""
        extractor = self.extractors.get(source_type)
        if not extractor:
            logger.warning(f"Unknown source type: {source_type}")
            return []

        # Extract knowledge
        units = await extractor.extract(source, context)

        # Add to graph
        for unit in units:
            self.graph.add_unit(unit)

        logger.info(f"Ingested {len(units)} knowledge units from {source_type}")
        return units

    async def synthesize_concept(
        self,
        unit_ids: List[str]
    ) -> Optional[Concept]:
        """Synthesize concept from knowledge units."""
        units = [
            self.graph.get_unit(uid)
            for uid in unit_ids
            if self.graph.get_unit(uid)
        ]

        concept = await self.synthesizer.synthesize(units)

        if concept:
            self.graph.add_concept(concept)

        return concept

    async def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType,
        strength: float = 1.0
    ) -> Relationship:
        """Add relationship between entities."""
        relationship = Relationship(
            id=str(uuid4()),
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            strength=strength
        )

        self.graph.add_relationship(relationship)
        return relationship

    async def infer(
        self,
        premise_ids: List[str],
        inference_type: str = "deduction"
    ) -> List[Inference]:
        """Make inferences from premises."""
        if inference_type == "deduction":
            return await self.inference_engine.deduce(premise_ids)
        elif inference_type == "induction":
            return await self.inference_engine.induce(premise_ids)
        else:
            return []

    async def explain(
        self,
        observation: str,
        candidate_ids: List[str]
    ) -> List[Tuple[str, float]]:
        """Find best explanation for observation."""
        return await self.inference_engine.abduct(observation, candidate_ids)

    async def validate(
        self,
        unit_id: str
    ) -> Dict[str, Any]:
        """Validate knowledge unit."""
        unit = self.graph.get_unit(unit_id)
        if not unit:
            return {"error": "Unit not found"}

        return await self.validator.validate(unit)

    async def query(
        self,
        query_type: str,
        **kwargs
    ) -> List[KnowledgeUnit]:
        """Query knowledge graph."""
        if query_type == "type":
            kt = KnowledgeType(kwargs.get("knowledge_type", "factual"))
            return self.graph.query_by_type(kt)
        elif query_type == "tag":
            return self.graph.query_by_tag(kwargs.get("tag", ""))
        else:
            return list(self.graph.units.values())

    def get_status(self) -> Dict[str, Any]:
        """Get system status."""
        stats = self.graph.get_stats()
        stats["synthesis_count"] = len(self.synthesizer.synthesis_history)
        return stats


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demo knowledge synthesis system."""
    print("=== Knowledge Synthesis System Demo ===\n")

    # Create system
    kss = KnowledgeSynthesisSystem()

    # 1. Ingest text knowledge
    print("1. Ingesting Text Knowledge:")
    text = """
    Python is a programming language.
    Python has dynamic typing.
    Python can be used for web development.
    Python is popular for machine learning.
    Machine learning leads to artificial intelligence.
    AI causes automation of many tasks.
    To install Python, you first download it, then run the installer.
    """

    units = await kss.ingest(text, "text", {"source": "documentation"})
    print(f"   Extracted {len(units)} knowledge units")
    for unit in units[:3]:
        print(f"   - [{unit.knowledge_type.value}] {unit.content[:50]}...")

    # 2. Ingest structured knowledge
    print("\n2. Ingesting Structured Knowledge:")
    data = {
        "language": "Python",
        "version": "3.11",
        "paradigms": ["procedural", "object-oriented", "functional"],
        "features": {
            "typing": "dynamic",
            "memory": "garbage collected",
            "compilation": "interpreted"
        }
    }

    struct_units = await kss.ingest(data, "structured", {"source": "metadata"})
    print(f"   Extracted {len(struct_units)} knowledge units")

    # 3. Add relationships
    print("\n3. Adding Relationships:")

    if len(units) >= 2:
        rel = await kss.add_relationship(
            units[0].id,
            units[1].id,
            RelationType.SUPPORTS,
            strength=0.8
        )
        print(f"   Added relationship: {rel.relation_type.value}")

    if len(units) >= 4:
        rel = await kss.add_relationship(
            units[2].id,
            units[3].id,
            RelationType.SIMILAR_TO,
            strength=0.7
        )
        print(f"   Added relationship: {rel.relation_type.value}")

    # 4. Synthesize concept
    print("\n4. Synthesizing Concept:")

    if len(units) >= 3:
        concept = await kss.synthesize_concept([u.id for u in units[:3]])
        if concept:
            print(f"   Name: {concept.name}")
            print(f"   Definition: {concept.definition[:100]}...")
            print(f"   Properties: {concept.properties}")

    # 5. Make inferences
    print("\n5. Making Inferences:")

    if len(units) >= 2:
        deductions = await kss.infer(
            [units[0].id, units[1].id],
            "deduction"
        )
        print(f"   Deductive inferences: {len(deductions)}")

        inductions = await kss.infer(
            [u.id for u in units[:4]],
            "induction"
        )
        print(f"   Inductive inferences: {len(inductions)}")
        for inf in inductions[:2]:
            print(f"   - {inf.conclusion[:60]}...")

    # 6. Find explanations
    print("\n6. Finding Explanations:")

    if len(units) >= 3:
        explanations = await kss.explain(
            "Why is Python popular?",
            [u.id for u in units[:3]]
        )
        print("   Best explanations:")
        for exp_id, score in explanations[:3]:
            unit = kss.graph.get_unit(exp_id)
            if unit:
                print(f"   - [{score:.2f}] {unit.content[:50]}...")

    # 7. Validate knowledge
    print("\n7. Validating Knowledge:")

    if units:
        validation = await kss.validate(units[0].id)
        print(f"   Is valid: {validation['is_valid']}")
        print(f"   Confidence: {validation['confidence_score']:.2f}")
        print(f"   Supporting evidence: {len(validation['supporting_evidence'])}")

    # 8. Query knowledge
    print("\n8. Querying Knowledge Graph:")

    factual = await kss.query("type", knowledge_type="factual")
    print(f"   Factual units: {len(factual)}")

    causal = await kss.query("type", knowledge_type="causal")
    print(f"   Causal units: {len(causal)}")

    procedural = await kss.query("type", knowledge_type="procedural")
    print(f"   Procedural units: {len(procedural)}")

    # 9. Get status
    print("\n9. System Status:")
    status = kss.get_status()
    for key, value in status.items():
        print(f"   {key}: {value}")


if __name__ == "__main__":
    asyncio.run(demo())
