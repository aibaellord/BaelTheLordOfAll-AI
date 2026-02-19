"""
BAEL Relation Mapper
=====================

Maps relationships between entities.
Builds knowledge graph connections.

Features:
- Relation extraction
- Relation typing
- Triple generation
- Relation validation
- Confidence scoring
"""

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from .entity_extractor import Entity, EntityType

logger = logging.getLogger(__name__)


class RelationType(Enum):
    """Types of relations."""
    # General relations
    IS_A = "is_a"
    HAS = "has"
    PART_OF = "part_of"
    RELATED_TO = "related_to"

    # Person relations
    WORKS_FOR = "works_for"
    KNOWS = "knows"
    CREATED_BY = "created_by"
    AUTHORED_BY = "authored_by"

    # Organizational relations
    OWNS = "owns"
    SUBSIDIARY_OF = "subsidiary_of"
    PARTNER_OF = "partner_of"
    COMPETES_WITH = "competes_with"

    # Location relations
    LOCATED_IN = "located_in"
    BASED_IN = "based_in"
    HEADQUARTERS_IN = "headquarters_in"

    # Technical relations
    DEPENDS_ON = "depends_on"
    USES = "uses"
    IMPLEMENTS = "implements"
    EXTENDS = "extends"
    CALLS = "calls"
    IMPORTS = "imports"

    # Temporal relations
    BEFORE = "before"
    AFTER = "after"
    DURING = "during"

    # Action relations
    SENT_TO = "sent_to"
    RECEIVED_FROM = "received_from"
    MODIFIED = "modified"
    DELETED = "deleted"


@dataclass
class Relation:
    """A relation between entities."""
    id: str
    relation_type: RelationType

    # Source and target
    source_id: str
    target_id: str

    # Confidence
    confidence: float = 1.0

    # Evidence
    evidence: str = ""
    source_text: str = ""

    # Properties
    properties: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    extracted_at: datetime = field(default_factory=datetime.now)


@dataclass
class RelationTriple:
    """A subject-predicate-object triple."""
    subject: Entity
    predicate: RelationType
    object: Entity

    # Relation details
    relation: Optional[Relation] = None

    # Confidence
    confidence: float = 1.0

    def to_tuple(self) -> Tuple[str, str, str]:
        """Convert to simple tuple."""
        return (self.subject.text, self.predicate.value, self.object.text)


class RelationMapper:
    """
    Relation mapper for BAEL.

    Extracts and maps relationships between entities.
    """

    # Relation patterns: (pattern, source_group, target_group, relation_type)
    PATTERNS = [
        # "X works for Y"
        (r"(\w+(?:\s+\w+)?)\s+works?\s+for\s+(\w+(?:\s+\w+)*)", 1, 2, RelationType.WORKS_FOR),
        # "X is a Y"
        (r"(\w+(?:\s+\w+)?)\s+is\s+(?:a|an)\s+(\w+(?:\s+\w+)*)", 1, 2, RelationType.IS_A),
        # "X has Y"
        (r"(\w+(?:\s+\w+)?)\s+has\s+(\w+(?:\s+\w+)*)", 1, 2, RelationType.HAS),
        # "X uses Y"
        (r"(\w+(?:\s+\w+)?)\s+uses?\s+(\w+(?:\s+\w+)*)", 1, 2, RelationType.USES),
        # "X depends on Y"
        (r"(\w+(?:\s+\w+)?)\s+depends?\s+on\s+(\w+(?:\s+\w+)*)", 1, 2, RelationType.DEPENDS_ON),
        # "X located in Y"
        (r"(\w+(?:\s+\w+)?)\s+(?:is\s+)?located\s+in\s+(\w+(?:\s+\w+)*)", 1, 2, RelationType.LOCATED_IN),
        # "X created by Y"
        (r"(\w+(?:\s+\w+)?)\s+(?:was\s+)?created\s+by\s+(\w+(?:\s+\w+)*)", 1, 2, RelationType.CREATED_BY),
        # "X sent to Y"
        (r"(\w+(?:\s+\w+)?)\s+sent\s+to\s+(\w+(?:\s+\w+)*)", 1, 2, RelationType.SENT_TO),
        # "X extends Y"
        (r"(\w+(?:\s+\w+)?)\s+extends\s+(\w+(?:\s+\w+)*)", 1, 2, RelationType.EXTENDS),
        # "X implements Y"
        (r"(\w+(?:\s+\w+)?)\s+implements\s+(\w+(?:\s+\w+)*)", 1, 2, RelationType.IMPLEMENTS),
    ]

    # Relation keywords for inference
    KEYWORDS = {
        RelationType.WORKS_FOR: ["employee", "work", "job", "employed"],
        RelationType.USES: ["use", "utilize", "employ", "leverage"],
        RelationType.DEPENDS_ON: ["depend", "require", "need", "rely"],
        RelationType.CREATED_BY: ["create", "build", "develop", "author"],
        RelationType.LOCATED_IN: ["locate", "based", "headquarters", "office"],
        RelationType.OWNS: ["own", "acquire", "purchase", "buy"],
        RelationType.PART_OF: ["part", "component", "module", "section"],
    }

    def __init__(self):
        # Extracted relations
        self._relations: Dict[str, Relation] = {}

        # Entity index
        self._entity_relations: Dict[str, List[str]] = {}

        # Stats
        self.stats = {
            "relations_extracted": 0,
            "triples_generated": 0,
            "pattern_matches": 0,
        }

    def extract_relations(
        self,
        text: str,
        entities: List[Entity],
    ) -> List[Relation]:
        """
        Extract relations from text.

        Args:
            text: Source text
            entities: Extracted entities

        Returns:
            List of relations
        """
        relations = []

        # Pattern-based extraction
        relations.extend(self._extract_by_patterns(text, entities))

        # Co-occurrence based extraction
        relations.extend(self._extract_by_cooccurrence(text, entities))

        # Inference-based extraction
        relations.extend(self._infer_relations(text, entities))

        # Store relations
        for relation in relations:
            self._relations[relation.id] = relation

            # Index by entity
            for entity_id in [relation.source_id, relation.target_id]:
                if entity_id not in self._entity_relations:
                    self._entity_relations[entity_id] = []
                self._entity_relations[entity_id].append(relation.id)

        self.stats["relations_extracted"] += len(relations)

        return relations

    def _extract_by_patterns(
        self,
        text: str,
        entities: List[Entity],
    ) -> List[Relation]:
        """Extract relations using patterns."""
        relations = []
        entity_map = {e.text.lower(): e for e in entities}

        for pattern, src_grp, tgt_grp, rel_type in self.PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)

            for match in matches:
                source_text = match.group(src_grp).strip()
                target_text = match.group(tgt_grp).strip()

                # Find matching entities
                source = entity_map.get(source_text.lower())
                target = entity_map.get(target_text.lower())

                if source and target:
                    relation = self._create_relation(
                        source=source,
                        target=target,
                        relation_type=rel_type,
                        evidence=match.group(),
                        confidence=0.9,
                    )
                    relations.append(relation)
                    self.stats["pattern_matches"] += 1

        return relations

    def _extract_by_cooccurrence(
        self,
        text: str,
        entities: List[Entity],
    ) -> List[Relation]:
        """Extract relations based on entity co-occurrence."""
        relations = []

        # Split into sentences
        sentences = re.split(r'[.!?]', text)

        for sentence in sentences:
            sentence_lower = sentence.lower()

            # Find entities in sentence
            sentence_entities = []
            for entity in entities:
                if entity.text.lower() in sentence_lower:
                    sentence_entities.append(entity)

            # Create RELATED_TO relations for co-occurring entities
            for i, e1 in enumerate(sentence_entities):
                for e2 in sentence_entities[i+1:]:
                    # Skip if same type (less interesting)
                    if e1.entity_type == e2.entity_type:
                        continue

                    # Infer relation type from context
                    rel_type = self._infer_relation_type(sentence, e1, e2)

                    relation = self._create_relation(
                        source=e1,
                        target=e2,
                        relation_type=rel_type,
                        evidence=sentence.strip(),
                        confidence=0.6,
                    )
                    relations.append(relation)

        return relations

    def _infer_relations(
        self,
        text: str,
        entities: List[Entity],
    ) -> List[Relation]:
        """Infer relations based on entity types."""
        relations = []

        # Type-based inference rules
        for i, e1 in enumerate(entities):
            for e2 in entities[i+1:]:
                rel_type = None
                confidence = 0.5

                # Person -> Organization
                if e1.entity_type == EntityType.PERSON and e2.entity_type == EntityType.ORGANIZATION:
                    rel_type = RelationType.WORKS_FOR

                # Organization -> Location
                elif e1.entity_type == EntityType.ORGANIZATION and e2.entity_type == EntityType.LOCATION:
                    rel_type = RelationType.LOCATED_IN

                # Technology -> Technology
                elif e1.entity_type == EntityType.TECHNOLOGY and e2.entity_type == EntityType.TECHNOLOGY:
                    rel_type = RelationType.RELATED_TO

                # Language -> Technology
                elif e1.entity_type == EntityType.LANGUAGE and e2.entity_type == EntityType.TECHNOLOGY:
                    rel_type = RelationType.USES

                if rel_type:
                    relation = self._create_relation(
                        source=e1,
                        target=e2,
                        relation_type=rel_type,
                        evidence="Inferred from entity types",
                        confidence=confidence,
                    )
                    relations.append(relation)

        return relations

    def _infer_relation_type(
        self,
        sentence: str,
        e1: Entity,
        e2: Entity,
    ) -> RelationType:
        """Infer relation type from sentence context."""
        sentence_lower = sentence.lower()

        # Check for keyword matches
        for rel_type, keywords in self.KEYWORDS.items():
            if any(kw in sentence_lower for kw in keywords):
                return rel_type

        # Default to RELATED_TO
        return RelationType.RELATED_TO

    def _create_relation(
        self,
        source: Entity,
        target: Entity,
        relation_type: RelationType,
        evidence: str = "",
        confidence: float = 1.0,
    ) -> Relation:
        """Create a relation."""
        relation_id = hashlib.md5(
            f"{source.id}:{relation_type.value}:{target.id}".encode()
        ).hexdigest()[:12]

        return Relation(
            id=relation_id,
            relation_type=relation_type,
            source_id=source.id,
            target_id=target.id,
            evidence=evidence,
            confidence=confidence,
        )

    def generate_triples(
        self,
        entities: List[Entity],
        relations: List[Relation],
    ) -> List[RelationTriple]:
        """
        Generate relation triples.

        Args:
            entities: Entity list
            relations: Relation list

        Returns:
            List of triples
        """
        entity_map = {e.id: e for e in entities}
        triples = []

        for relation in relations:
            subject = entity_map.get(relation.source_id)
            obj = entity_map.get(relation.target_id)

            if subject and obj:
                triple = RelationTriple(
                    subject=subject,
                    predicate=relation.relation_type,
                    object=obj,
                    relation=relation,
                    confidence=relation.confidence,
                )
                triples.append(triple)

        self.stats["triples_generated"] = len(triples)

        return triples

    def get_relations_for_entity(
        self,
        entity_id: str,
    ) -> List[Relation]:
        """Get all relations for an entity."""
        relation_ids = self._entity_relations.get(entity_id, [])
        return [self._relations[rid] for rid in relation_ids if rid in self._relations]

    def validate_relation(
        self,
        relation: Relation,
        entities: List[Entity],
    ) -> bool:
        """Validate a relation."""
        entity_ids = {e.id for e in entities}

        # Check entities exist
        if relation.source_id not in entity_ids:
            return False
        if relation.target_id not in entity_ids:
            return False

        # Check for self-loops
        if relation.source_id == relation.target_id:
            return False

        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get mapper statistics."""
        return {
            **self.stats,
            "stored_relations": len(self._relations),
            "indexed_entities": len(self._entity_relations),
        }


def demo():
    """Demonstrate relation mapping."""
    print("=" * 60)
    print("BAEL Relation Mapper Demo")
    print("=" * 60)

    from .entity_extractor import EntityExtractor

    extractor = EntityExtractor()
    mapper = RelationMapper()

    text = """
    John Smith works for Acme Corporation in New York.
    The company uses Python and TensorFlow for machine learning.
    Acme Corporation was created by Sarah Johnson.
    The Python framework depends on NumPy for numerical operations.
    """

    print(f"\nInput text:")
    print(f"  {text[:100]}...")

    # Extract entities
    result = extractor.extract(text)
    print(f"\nExtracted {len(result.entities)} entities")

    # Extract relations
    relations = mapper.extract_relations(text, result.entities)
    print(f"Extracted {len(relations)} relations")

    # Generate triples
    triples = mapper.generate_triples(result.entities, relations)

    print(f"\nRelation triples:")
    for triple in triples:
        print(f"  ({triple.subject.text}) --[{triple.predicate.value}]--> ({triple.object.text})")
        print(f"    Confidence: {triple.confidence:.0%}")

    print(f"\nStats: {mapper.get_stats()}")


if __name__ == "__main__":
    demo()
