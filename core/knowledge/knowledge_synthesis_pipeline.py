"""
BAEL Knowledge Synthesis Pipeline

Advanced knowledge processing with:
- Multi-source knowledge fusion
- Contradiction resolution
- Knowledge graph construction
- Semantic deduplication
- Confidence scoring
- Provenance tracking

This is how BAEL builds and maintains its understanding.
"""

import hashlib
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4

logger = logging.getLogger(__name__)


class KnowledgeType(Enum):
    """Types of knowledge."""
    FACT = "fact"
    CONCEPT = "concept"
    PROCEDURE = "procedure"
    RULE = "rule"
    BELIEF = "belief"
    OBSERVATION = "observation"
    INFERENCE = "inference"
    HYPOTHESIS = "hypothesis"


class SourceType(Enum):
    """Types of knowledge sources."""
    DOCUMENT = "document"
    WEB = "web"
    DATABASE = "database"
    USER = "user"
    LLM = "llm"
    INFERENCE = "inference"
    MEMORY = "memory"
    EXTERNAL_API = "external_api"


class ConfidenceLevel(Enum):
    """Confidence levels for knowledge."""
    CERTAIN = 1.0
    HIGH = 0.8
    MEDIUM = 0.6
    LOW = 0.4
    UNCERTAIN = 0.2
    UNKNOWN = 0.0


class RelationType(Enum):
    """Types of relationships between knowledge."""
    IS_A = "is_a"
    HAS_PART = "has_part"
    PART_OF = "part_of"
    CAUSES = "causes"
    CAUSED_BY = "caused_by"
    RELATED_TO = "related_to"
    CONTRADICTS = "contradicts"
    SUPPORTS = "supports"
    SAME_AS = "same_as"
    DERIVED_FROM = "derived_from"
    IMPLIES = "implies"
    REQUIRES = "requires"


@dataclass
class KnowledgeSource:
    """Source of a piece of knowledge."""
    id: str
    source_type: SourceType
    name: str
    url: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    reliability: float = 0.8
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KnowledgeEntity:
    """An entity in the knowledge base."""
    id: str
    name: str
    entity_type: str
    aliases: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None

    def matches(self, query: str) -> bool:
        """Check if entity matches a query."""
        query_lower = query.lower()
        if self.name.lower() == query_lower:
            return True
        return any(a.lower() == query_lower for a in self.aliases)


@dataclass
class KnowledgeItem:
    """A single piece of knowledge."""
    id: str
    content: str
    knowledge_type: KnowledgeType

    # Provenance
    sources: List[KnowledgeSource] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # Confidence and validity
    confidence: float = 0.8
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None

    # Semantic
    entities: List[str] = field(default_factory=list)  # Entity IDs
    topics: List[str] = field(default_factory=list)
    embedding: Optional[List[float]] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def content_hash(self) -> str:
        """Get hash of content for deduplication."""
        return hashlib.md5(self.content.encode()).hexdigest()


@dataclass
class KnowledgeRelation:
    """A relationship between knowledge items."""
    id: str
    source_id: str  # ID of source knowledge
    target_id: str  # ID of target knowledge
    relation_type: RelationType
    confidence: float = 0.8
    bidirectional: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SynthesisResult:
    """Result of knowledge synthesis."""
    synthesized_knowledge: List[KnowledgeItem]
    new_relations: List[KnowledgeRelation]
    resolved_contradictions: List[Dict[str, Any]]
    merged_duplicates: List[Tuple[str, str]]
    confidence_updates: Dict[str, float]
    processing_stats: Dict[str, Any]


class ContradictionResolver:
    """Resolves contradictions between knowledge items."""

    def __init__(self):
        self.resolution_strategies = {
            "source_reliability": self._resolve_by_reliability,
            "recency": self._resolve_by_recency,
            "consensus": self._resolve_by_consensus,
            "specificity": self._resolve_by_specificity,
        }

    async def detect_contradictions(
        self,
        items: List[KnowledgeItem]
    ) -> List[Tuple[KnowledgeItem, KnowledgeItem]]:
        """Detect contradictory knowledge items."""
        contradictions = []

        for i, item1 in enumerate(items):
            for item2 in items[i+1:]:
                if await self._are_contradictory(item1, item2):
                    contradictions.append((item1, item2))

        return contradictions

    async def _are_contradictory(
        self,
        item1: KnowledgeItem,
        item2: KnowledgeItem
    ) -> bool:
        """Check if two items are contradictory."""
        # Check for overlapping entities (same subject)
        common_entities = set(item1.entities) & set(item2.entities)
        if not common_entities:
            return False

        # Simple heuristics for contradiction
        # In real implementation, would use semantic analysis
        negation_words = ["not", "never", "no", "false", "wrong", "incorrect"]

        item1_has_negation = any(w in item1.content.lower() for w in negation_words)
        item2_has_negation = any(w in item2.content.lower() for w in negation_words)

        # If one has negation and other doesn't, might be contradiction
        return item1_has_negation != item2_has_negation

    async def resolve(
        self,
        item1: KnowledgeItem,
        item2: KnowledgeItem,
        strategy: str = "source_reliability"
    ) -> Dict[str, Any]:
        """Resolve contradiction between two items."""
        resolver = self.resolution_strategies.get(strategy, self._resolve_by_reliability)
        return await resolver(item1, item2)

    async def _resolve_by_reliability(
        self,
        item1: KnowledgeItem,
        item2: KnowledgeItem
    ) -> Dict[str, Any]:
        """Resolve by source reliability."""
        rel1 = max((s.reliability for s in item1.sources), default=0.5)
        rel2 = max((s.reliability for s in item2.sources), default=0.5)

        if rel1 > rel2:
            winner, loser = item1, item2
        else:
            winner, loser = item2, item1

        return {
            "winner_id": winner.id,
            "loser_id": loser.id,
            "strategy": "source_reliability",
            "confidence": abs(rel1 - rel2),
            "action": "deprecate_loser"
        }

    async def _resolve_by_recency(
        self,
        item1: KnowledgeItem,
        item2: KnowledgeItem
    ) -> Dict[str, Any]:
        """Resolve by recency (newer wins)."""
        if item1.updated_at > item2.updated_at:
            winner, loser = item1, item2
        else:
            winner, loser = item2, item1

        return {
            "winner_id": winner.id,
            "loser_id": loser.id,
            "strategy": "recency",
            "action": "deprecate_loser"
        }

    async def _resolve_by_consensus(
        self,
        item1: KnowledgeItem,
        item2: KnowledgeItem
    ) -> Dict[str, Any]:
        """Resolve by number of supporting sources."""
        if len(item1.sources) > len(item2.sources):
            winner, loser = item1, item2
        else:
            winner, loser = item2, item1

        return {
            "winner_id": winner.id,
            "loser_id": loser.id,
            "strategy": "consensus",
            "action": "deprecate_loser"
        }

    async def _resolve_by_specificity(
        self,
        item1: KnowledgeItem,
        item2: KnowledgeItem
    ) -> Dict[str, Any]:
        """Resolve by specificity (more specific wins)."""
        # More specific = more entities/details
        spec1 = len(item1.entities) + len(item1.content.split())
        spec2 = len(item2.entities) + len(item2.content.split())

        if spec1 > spec2:
            winner, loser = item1, item2
        else:
            winner, loser = item2, item1

        return {
            "winner_id": winner.id,
            "loser_id": loser.id,
            "strategy": "specificity",
            "action": "keep_both_with_relation"
        }


class SemanticDeduplicator:
    """Deduplicates knowledge items semantically."""

    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold

    async def find_duplicates(
        self,
        items: List[KnowledgeItem]
    ) -> List[Tuple[KnowledgeItem, KnowledgeItem]]:
        """Find duplicate knowledge items."""
        duplicates = []

        for i, item1 in enumerate(items):
            for item2 in items[i+1:]:
                similarity = await self._compute_similarity(item1, item2)
                if similarity >= self.similarity_threshold:
                    duplicates.append((item1, item2))

        return duplicates

    async def _compute_similarity(
        self,
        item1: KnowledgeItem,
        item2: KnowledgeItem
    ) -> float:
        """Compute semantic similarity between items."""
        # Simple word overlap similarity
        # In real implementation, would use embeddings
        words1 = set(item1.content.lower().split())
        words2 = set(item2.content.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    async def merge(
        self,
        item1: KnowledgeItem,
        item2: KnowledgeItem
    ) -> KnowledgeItem:
        """Merge two duplicate items."""
        # Combine sources
        all_sources = item1.sources + item2.sources
        unique_sources = {s.id: s for s in all_sources}

        # Combine entities
        all_entities = list(set(item1.entities + item2.entities))

        # Use content from higher confidence item
        if item1.confidence >= item2.confidence:
            content = item1.content
            base_confidence = item1.confidence
        else:
            content = item2.content
            base_confidence = item2.confidence

        # Boost confidence due to multiple sources
        merged_confidence = min(base_confidence * 1.1, 1.0)

        return KnowledgeItem(
            id=str(uuid4())[:8],
            content=content,
            knowledge_type=item1.knowledge_type,
            sources=list(unique_sources.values()),
            confidence=merged_confidence,
            entities=all_entities,
            topics=list(set(item1.topics + item2.topics)),
            metadata={
                "merged_from": [item1.id, item2.id],
                "merge_timestamp": datetime.now().isoformat()
            }
        )


class KnowledgeGraphBuilder:
    """Builds knowledge graph from items."""

    def __init__(self):
        self.entities: Dict[str, KnowledgeEntity] = {}
        self.relations: List[KnowledgeRelation] = []

    async def extract_entities(
        self,
        item: KnowledgeItem
    ) -> List[KnowledgeEntity]:
        """Extract entities from a knowledge item."""
        # Simple noun extraction
        # In real implementation, would use NER
        words = item.content.split()
        entities = []

        # Find capitalized words as potential entities
        for word in words:
            if word[0].isupper() and len(word) > 2:
                entity = KnowledgeEntity(
                    id=str(uuid4())[:8],
                    name=word.strip('.,!?'),
                    entity_type="unknown"
                )
                entities.append(entity)

        return entities

    async def infer_relations(
        self,
        items: List[KnowledgeItem]
    ) -> List[KnowledgeRelation]:
        """Infer relations between knowledge items."""
        relations = []

        for i, item1 in enumerate(items):
            for item2 in items[i+1:]:
                # Check for common entities
                common = set(item1.entities) & set(item2.entities)
                if common:
                    relation = KnowledgeRelation(
                        id=str(uuid4())[:8],
                        source_id=item1.id,
                        target_id=item2.id,
                        relation_type=RelationType.RELATED_TO,
                        confidence=0.5 + 0.1 * len(common)
                    )
                    relations.append(relation)

                # Check for derivation
                if item2.knowledge_type == KnowledgeType.INFERENCE:
                    if any(s.source_type == SourceType.INFERENCE for s in item2.sources):
                        relation = KnowledgeRelation(
                            id=str(uuid4())[:8],
                            source_id=item1.id,
                            target_id=item2.id,
                            relation_type=RelationType.DERIVED_FROM,
                            confidence=0.7
                        )
                        relations.append(relation)

        return relations

    async def build_graph(
        self,
        items: List[KnowledgeItem]
    ) -> Dict[str, Any]:
        """Build a knowledge graph from items."""
        nodes = []
        edges = []

        for item in items:
            nodes.append({
                "id": item.id,
                "label": item.content[:50],
                "type": item.knowledge_type.value,
                "confidence": item.confidence
            })

        relations = await self.infer_relations(items)

        for rel in relations:
            edges.append({
                "source": rel.source_id,
                "target": rel.target_id,
                "type": rel.relation_type.value,
                "confidence": rel.confidence
            })

        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "node_count": len(nodes),
                "edge_count": len(edges)
            }
        }


class KnowledgeSynthesisPipeline:
    """
    Main knowledge synthesis pipeline.

    Orchestrates:
    - Knowledge extraction
    - Deduplication
    - Contradiction resolution
    - Graph construction
    - Confidence scoring
    """

    def __init__(self):
        self.deduplicator = SemanticDeduplicator()
        self.contradiction_resolver = ContradictionResolver()
        self.graph_builder = KnowledgeGraphBuilder()

        # Knowledge store
        self.knowledge_items: Dict[str, KnowledgeItem] = {}
        self.relations: List[KnowledgeRelation] = []

    async def ingest(
        self,
        content: str,
        source: KnowledgeSource,
        knowledge_type: KnowledgeType = KnowledgeType.FACT
    ) -> KnowledgeItem:
        """Ingest new knowledge."""
        item = KnowledgeItem(
            id=str(uuid4())[:8],
            content=content,
            knowledge_type=knowledge_type,
            sources=[source],
            confidence=source.reliability
        )

        # Extract entities
        entities = await self.graph_builder.extract_entities(item)
        item.entities = [e.id for e in entities]

        for entity in entities:
            self.graph_builder.entities[entity.id] = entity

        self.knowledge_items[item.id] = item
        return item

    async def synthesize(
        self,
        new_items: List[KnowledgeItem]
    ) -> SynthesisResult:
        """Synthesize new knowledge with existing knowledge."""
        all_items = list(self.knowledge_items.values()) + new_items

        # Find and merge duplicates
        duplicates = await self.deduplicator.find_duplicates(all_items)
        merged_pairs = []

        for item1, item2 in duplicates:
            merged = await self.deduplicator.merge(item1, item2)

            # Remove originals, add merged
            if item1.id in self.knowledge_items:
                del self.knowledge_items[item1.id]
            if item2.id in self.knowledge_items:
                del self.knowledge_items[item2.id]

            self.knowledge_items[merged.id] = merged
            merged_pairs.append((item1.id, item2.id))

        # Detect and resolve contradictions
        current_items = list(self.knowledge_items.values())
        contradictions = await self.contradiction_resolver.detect_contradictions(current_items)
        resolutions = []

        for item1, item2 in contradictions:
            resolution = await self.contradiction_resolver.resolve(item1, item2)
            resolutions.append(resolution)

            # Apply resolution
            if resolution["action"] == "deprecate_loser":
                loser_id = resolution["loser_id"]
                if loser_id in self.knowledge_items:
                    self.knowledge_items[loser_id].confidence *= 0.5

        # Infer new relations
        new_relations = await self.graph_builder.infer_relations(current_items)
        self.relations.extend(new_relations)

        # Update confidence scores
        confidence_updates = await self._update_confidences()

        return SynthesisResult(
            synthesized_knowledge=list(self.knowledge_items.values()),
            new_relations=new_relations,
            resolved_contradictions=resolutions,
            merged_duplicates=merged_pairs,
            confidence_updates=confidence_updates,
            processing_stats={
                "total_items": len(self.knowledge_items),
                "duplicates_merged": len(merged_pairs),
                "contradictions_resolved": len(resolutions),
                "new_relations": len(new_relations)
            }
        )

    async def _update_confidences(self) -> Dict[str, float]:
        """Update confidence scores based on supporting evidence."""
        updates = {}

        for item_id, item in self.knowledge_items.items():
            # Confidence boost from multiple sources
            source_boost = min(len(item.sources) * 0.05, 0.2)

            # Confidence boost from supporting relations
            supporting = [
                r for r in self.relations
                if r.target_id == item_id and r.relation_type == RelationType.SUPPORTS
            ]
            support_boost = min(len(supporting) * 0.1, 0.3)

            new_confidence = min(item.confidence + source_boost + support_boost, 1.0)

            if new_confidence != item.confidence:
                item.confidence = new_confidence
                updates[item_id] = new_confidence

        return updates

    async def query(
        self,
        query: str,
        min_confidence: float = 0.5
    ) -> List[KnowledgeItem]:
        """Query the knowledge base."""
        results = []
        query_words = set(query.lower().split())

        for item in self.knowledge_items.values():
            if item.confidence < min_confidence:
                continue

            item_words = set(item.content.lower().split())
            overlap = len(query_words & item_words)

            if overlap > 0:
                results.append((item, overlap))

        # Sort by relevance
        results.sort(key=lambda x: x[1], reverse=True)
        return [item for item, _ in results]

    async def get_graph(self) -> Dict[str, Any]:
        """Get the knowledge graph."""
        return await self.graph_builder.build_graph(
            list(self.knowledge_items.values())
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        type_counts = {}
        for item in self.knowledge_items.values():
            type_name = item.knowledge_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        avg_confidence = sum(
            i.confidence for i in self.knowledge_items.values()
        ) / len(self.knowledge_items) if self.knowledge_items else 0

        return {
            "total_items": len(self.knowledge_items),
            "total_relations": len(self.relations),
            "total_entities": len(self.graph_builder.entities),
            "by_type": type_counts,
            "average_confidence": avg_confidence
        }


async def demo():
    """Demonstrate knowledge synthesis pipeline."""
    print("=" * 60)
    print("BAEL Knowledge Synthesis Pipeline Demo")
    print("=" * 60)

    pipeline = KnowledgeSynthesisPipeline()

    # Create sources
    wikipedia = KnowledgeSource(
        id="wiki",
        source_type=SourceType.WEB,
        name="Wikipedia",
        reliability=0.85
    )

    user = KnowledgeSource(
        id="user",
        source_type=SourceType.USER,
        name="User Input",
        reliability=0.7
    )

    # Ingest knowledge
    await pipeline.ingest(
        "Python is a programming language created by Guido van Rossum.",
        wikipedia,
        KnowledgeType.FACT
    )

    await pipeline.ingest(
        "Python emphasizes code readability and simplicity.",
        wikipedia,
        KnowledgeType.FACT
    )

    await pipeline.ingest(
        "Guido van Rossum created Python in the late 1980s.",
        user,
        KnowledgeType.FACT
    )

    print(f"\nIngested {len(pipeline.knowledge_items)} knowledge items")

    # Synthesize
    new_items = [
        KnowledgeItem(
            id="new1",
            content="Python supports multiple programming paradigms.",
            knowledge_type=KnowledgeType.FACT,
            sources=[wikipedia],
            confidence=0.8
        )
    ]

    result = await pipeline.synthesize(new_items)
    print(f"\nSynthesis results:")
    print(f"  Items after synthesis: {len(result.synthesized_knowledge)}")
    print(f"  Duplicates merged: {len(result.merged_duplicates)}")
    print(f"  Contradictions resolved: {len(result.resolved_contradictions)}")
    print(f"  New relations: {len(result.new_relations)}")

    # Query
    results = await pipeline.query("Python programming")
    print(f"\nQuery 'Python programming': {len(results)} results")

    # Get graph
    graph = await pipeline.get_graph()
    print(f"\nKnowledge graph: {graph['stats']}")

    # Statistics
    stats = pipeline.get_statistics()
    print(f"\nStatistics: {stats}")

    print("\n✓ Multi-source knowledge fusion")
    print("✓ Semantic deduplication")
    print("✓ Contradiction resolution")
    print("✓ Knowledge graph construction")
    print("✓ Confidence scoring")
    print("✓ Provenance tracking")


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo())
