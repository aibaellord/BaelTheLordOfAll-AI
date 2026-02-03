"""
BAEL - Semantic Memory System
Stores and retrieves concepts, facts, and general knowledge.

Semantic memory captures:
- Factual knowledge
- Concept definitions
- Relationships between concepts
- Domain expertise
- General truths and rules
"""

import asyncio
import hashlib
import json
import logging
import math
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.Memory.Semantic")


# =============================================================================
# ENUMS & DATA CLASSES
# =============================================================================

class ConceptType(Enum):
    """Types of semantic concepts."""
    FACT = "fact"
    DEFINITION = "definition"
    RULE = "rule"
    PROCEDURE = "procedure"
    CATEGORY = "category"
    ENTITY = "entity"
    RELATIONSHIP = "relationship"
    PATTERN = "pattern"
    PRINCIPLE = "principle"
    DOMAIN = "domain"


class RelationType(Enum):
    """Types of relationships between concepts."""
    IS_A = "is_a"  # Taxonomy
    HAS_A = "has_a"  # Composition
    PART_OF = "part_of"  # Meronymy
    RELATED_TO = "related_to"  # General association
    CAUSES = "causes"  # Causality
    REQUIRES = "requires"  # Dependency
    CONTRADICTS = "contradicts"  # Opposition
    SIMILAR_TO = "similar_to"  # Similarity
    OPPOSITE_OF = "opposite_of"  # Antonymy
    EXAMPLE_OF = "example_of"  # Instance
    IMPLEMENTS = "implements"  # Realization
    DERIVED_FROM = "derived_from"  # Origin


class ConfidenceLevel(Enum):
    """Confidence levels for knowledge."""
    CERTAIN = 1.0
    HIGH = 0.85
    MEDIUM = 0.65
    LOW = 0.4
    UNCERTAIN = 0.2


@dataclass
class Concept:
    """A semantic memory concept."""
    id: str
    name: str
    concept_type: ConceptType
    definition: str
    domain: str  # Knowledge domain (e.g., "programming", "science")
    properties: Dict[str, Any]
    confidence: float
    source: str  # Where this knowledge came from
    created_at: datetime
    updated_at: datetime
    access_count: int = 0
    embedding: Optional[List[float]] = None
    aliases: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    counter_examples: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "concept_type": self.concept_type.value,
            "definition": self.definition,
            "domain": self.domain,
            "properties": self.properties,
            "confidence": self.confidence,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "access_count": self.access_count,
            "aliases": self.aliases,
            "examples": self.examples,
            "counter_examples": self.counter_examples,
            "tags": self.tags
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Concept":
        return cls(
            id=data["id"],
            name=data["name"],
            concept_type=ConceptType(data["concept_type"]),
            definition=data["definition"],
            domain=data.get("domain", "general"),
            properties=data.get("properties", {}),
            confidence=data.get("confidence", 0.5),
            source=data.get("source", "unknown"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            access_count=data.get("access_count", 0),
            aliases=data.get("aliases", []),
            examples=data.get("examples", []),
            counter_examples=data.get("counter_examples", []),
            tags=data.get("tags", [])
        )


@dataclass
class ConceptRelation:
    """A relationship between two concepts."""
    id: str
    source_id: str
    target_id: str
    relation_type: RelationType
    strength: float  # 0.0 to 1.0
    properties: Dict[str, Any]
    bidirectional: bool
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "strength": self.strength,
            "properties": self.properties,
            "bidirectional": self.bidirectional,
            "confidence": self.confidence
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConceptRelation":
        return cls(
            id=data["id"],
            source_id=data["source_id"],
            target_id=data["target_id"],
            relation_type=RelationType(data["relation_type"]),
            strength=data.get("strength", 0.5),
            properties=data.get("properties", {}),
            bidirectional=data.get("bidirectional", False),
            confidence=data.get("confidence", 0.5)
        )


@dataclass
class SemanticQuery:
    """Query parameters for searching semantic memory."""
    text: Optional[str] = None
    concept_types: Optional[List[ConceptType]] = None
    domains: Optional[List[str]] = None
    min_confidence: float = 0.0
    tags: Optional[List[str]] = None
    limit: int = 20


# =============================================================================
# SEMANTIC MEMORY STORE
# =============================================================================

class SemanticMemoryStore:
    """
    Persistent storage for semantic memories (concepts and relations).

    Implements a knowledge graph with:
    - Concept nodes
    - Typed relationships
    - Property storage
    - Confidence tracking
    """

    def __init__(self, db_path: str = "memory/semantic/concepts.db"):
        self.db_path = db_path
        self._concept_cache: Dict[str, Concept] = {}
        self._relation_cache: Dict[str, ConceptRelation] = {}
        self._cache_limit = 500
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the database."""
        if self._initialized:
            return

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Concepts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS concepts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                concept_type TEXT NOT NULL,
                definition TEXT NOT NULL,
                domain TEXT,
                properties TEXT,
                confidence REAL,
                source TEXT,
                created_at TEXT,
                updated_at TEXT,
                access_count INTEGER DEFAULT 0,
                embedding BLOB,
                aliases TEXT,
                examples TEXT,
                counter_examples TEXT,
                tags TEXT
            )
        """)

        # Relations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS relations (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                strength REAL,
                properties TEXT,
                bidirectional INTEGER,
                confidence REAL,
                FOREIGN KEY (source_id) REFERENCES concepts(id),
                FOREIGN KEY (target_id) REFERENCES concepts(id)
            )
        """)

        # Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_concept_name ON concepts(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_concept_type ON concepts(concept_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_concept_domain ON concepts(domain)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_relation_source ON relations(source_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_relation_target ON relations(target_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_relation_type ON relations(relation_type)")

        conn.commit()
        conn.close()

        self._initialized = True
        logger.info(f"Semantic memory store initialized at {self.db_path}")

    def _generate_id(self, name: str, concept_type: str) -> str:
        """Generate unique concept ID."""
        data = f"{name}{concept_type}{datetime.now().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    # -------------------------------------------------------------------------
    # Concept Operations
    # -------------------------------------------------------------------------

    async def store_concept(self, concept: Concept) -> str:
        """Store a concept."""
        await self.initialize()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO concepts
            (id, name, concept_type, definition, domain, properties, confidence,
             source, created_at, updated_at, access_count, embedding, aliases,
             examples, counter_examples, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            concept.id,
            concept.name,
            concept.concept_type.value,
            concept.definition,
            concept.domain,
            json.dumps(concept.properties),
            concept.confidence,
            concept.source,
            concept.created_at.isoformat(),
            concept.updated_at.isoformat(),
            concept.access_count,
            json.dumps(concept.embedding) if concept.embedding else None,
            json.dumps(concept.aliases),
            json.dumps(concept.examples),
            json.dumps(concept.counter_examples),
            json.dumps(concept.tags)
        ))

        conn.commit()
        conn.close()

        self._concept_cache[concept.id] = concept
        self._trim_cache()

        logger.debug(f"Stored concept: {concept.name}")
        return concept.id

    async def get_concept(self, concept_id: str) -> Optional[Concept]:
        """Get a concept by ID."""
        await self.initialize()

        if concept_id in self._concept_cache:
            return self._concept_cache[concept_id]

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM concepts WHERE id = ?", (concept_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        concept = self._row_to_concept(row)
        self._concept_cache[concept_id] = concept
        return concept

    async def find_concept_by_name(self, name: str) -> Optional[Concept]:
        """Find a concept by name or alias."""
        await self.initialize()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check exact name match
        cursor.execute(
            "SELECT * FROM concepts WHERE name = ? COLLATE NOCASE",
            (name,)
        )
        row = cursor.fetchone()

        if not row:
            # Check aliases
            cursor.execute("SELECT * FROM concepts")
            for r in cursor.fetchall():
                aliases = json.loads(r[12]) if r[12] else []
                if name.lower() in [a.lower() for a in aliases]:
                    row = r
                    break

        conn.close()

        if not row:
            return None

        return self._row_to_concept(row)

    async def search_concepts(self, query: SemanticQuery) -> List[Concept]:
        """Search concepts based on query parameters."""
        await self.initialize()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        sql = "SELECT * FROM concepts WHERE 1=1"
        params = []

        if query.concept_types:
            placeholders = ",".join("?" * len(query.concept_types))
            sql += f" AND concept_type IN ({placeholders})"
            params.extend([ct.value for ct in query.concept_types])

        if query.domains:
            placeholders = ",".join("?" * len(query.domains))
            sql += f" AND domain IN ({placeholders})"
            params.extend(query.domains)

        if query.min_confidence > 0:
            sql += " AND confidence >= ?"
            params.append(query.min_confidence)

        sql += " ORDER BY confidence DESC, access_count DESC LIMIT ?"
        params.append(query.limit * 2)

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        concepts = [self._row_to_concept(row) for row in rows]

        # Apply text filter
        if query.text:
            text_lower = query.text.lower()
            concepts = [c for c in concepts
                       if text_lower in c.name.lower()
                       or text_lower in c.definition.lower()]

        # Apply tag filter
        if query.tags:
            concepts = [c for c in concepts
                       if any(t in c.tags for t in query.tags)]

        return concepts[:query.limit]

    async def update_confidence(
        self,
        concept_id: str,
        delta: float
    ) -> Optional[float]:
        """Update concept confidence."""
        concept = await self.get_concept(concept_id)
        if not concept:
            return None

        concept.confidence = max(0.0, min(1.0, concept.confidence + delta))
        concept.updated_at = datetime.now()
        await self.store_concept(concept)

        return concept.confidence

    # -------------------------------------------------------------------------
    # Relation Operations
    # -------------------------------------------------------------------------

    async def store_relation(self, relation: ConceptRelation) -> str:
        """Store a relation between concepts."""
        await self.initialize()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO relations
            (id, source_id, target_id, relation_type, strength, properties,
             bidirectional, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            relation.id,
            relation.source_id,
            relation.target_id,
            relation.relation_type.value,
            relation.strength,
            json.dumps(relation.properties),
            1 if relation.bidirectional else 0,
            relation.confidence
        ))

        conn.commit()
        conn.close()

        self._relation_cache[relation.id] = relation
        logger.debug(f"Stored relation: {relation.source_id} -> {relation.target_id}")
        return relation.id

    async def get_relations(
        self,
        concept_id: str,
        direction: str = "both",  # "outgoing", "incoming", "both"
        relation_types: Optional[List[RelationType]] = None
    ) -> List[ConceptRelation]:
        """Get relations for a concept."""
        await self.initialize()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        relations = []

        if direction in ["outgoing", "both"]:
            sql = "SELECT * FROM relations WHERE source_id = ?"
            cursor.execute(sql, (concept_id,))
            relations.extend([self._row_to_relation(r) for r in cursor.fetchall()])

        if direction in ["incoming", "both"]:
            sql = "SELECT * FROM relations WHERE target_id = ?"
            cursor.execute(sql, (concept_id,))
            relations.extend([self._row_to_relation(r) for r in cursor.fetchall()])

        conn.close()

        # Filter by type
        if relation_types:
            relations = [r for r in relations if r.relation_type in relation_types]

        return relations

    async def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5
    ) -> Optional[List[str]]:
        """Find a path between two concepts using BFS."""
        await self.initialize()

        visited = set()
        queue = [(source_id, [source_id])]

        while queue:
            current_id, path = queue.pop(0)

            if current_id == target_id:
                return path

            if current_id in visited or len(path) > max_depth:
                continue

            visited.add(current_id)

            relations = await self.get_relations(current_id, direction="outgoing")
            for rel in relations:
                if rel.target_id not in visited:
                    queue.append((rel.target_id, path + [rel.target_id]))

        return None

    async def get_related_concepts(
        self,
        concept_id: str,
        relation_types: Optional[List[RelationType]] = None,
        limit: int = 20
    ) -> List[Tuple[Concept, ConceptRelation]]:
        """Get concepts related to a given concept."""
        relations = await self.get_relations(
            concept_id,
            direction="both",
            relation_types=relation_types
        )

        results = []
        for rel in relations[:limit]:
            related_id = rel.target_id if rel.source_id == concept_id else rel.source_id
            concept = await self.get_concept(related_id)
            if concept:
                results.append((concept, rel))

        return results

    # -------------------------------------------------------------------------
    # Knowledge Graph Operations
    # -------------------------------------------------------------------------

    async def get_subgraph(
        self,
        center_id: str,
        depth: int = 2
    ) -> Dict[str, Any]:
        """Get a subgraph centered on a concept."""
        concepts = {}
        relations = []

        async def expand(concept_id: str, current_depth: int):
            if current_depth > depth or concept_id in concepts:
                return

            concept = await self.get_concept(concept_id)
            if not concept:
                return

            concepts[concept_id] = concept

            rels = await self.get_relations(concept_id, direction="both")
            for rel in rels:
                if rel not in relations:
                    relations.append(rel)

                related_id = rel.target_id if rel.source_id == concept_id else rel.source_id
                await expand(related_id, current_depth + 1)

        await expand(center_id, 0)

        return {
            "concepts": {k: v.to_dict() for k, v in concepts.items()},
            "relations": [r.to_dict() for r in relations]
        }

    async def get_domain_concepts(
        self,
        domain: str,
        limit: int = 50
    ) -> List[Concept]:
        """Get all concepts in a domain."""
        query = SemanticQuery(domains=[domain], limit=limit)
        return await self.search_concepts(query)

    async def merge_concepts(
        self,
        concept_id1: str,
        concept_id2: str
    ) -> Optional[str]:
        """Merge two concepts into one."""
        c1 = await self.get_concept(concept_id1)
        c2 = await self.get_concept(concept_id2)

        if not c1 or not c2:
            return None

        # Merge into the one with higher confidence
        if c1.confidence >= c2.confidence:
            primary, secondary = c1, c2
        else:
            primary, secondary = c2, c1

        # Merge aliases
        primary.aliases = list(set(primary.aliases + secondary.aliases + [secondary.name]))

        # Merge examples
        primary.examples = list(set(primary.examples + secondary.examples))

        # Merge tags
        primary.tags = list(set(primary.tags + secondary.tags))

        # Update confidence (weighted average)
        total_access = primary.access_count + secondary.access_count
        if total_access > 0:
            primary.confidence = (
                (primary.confidence * primary.access_count +
                 secondary.confidence * secondary.access_count) / total_access
            )

        primary.access_count = total_access
        primary.updated_at = datetime.now()

        # Redirect relations
        secondary_relations = await self.get_relations(secondary.id, direction="both")
        for rel in secondary_relations:
            if rel.source_id == secondary.id:
                rel.source_id = primary.id
            if rel.target_id == secondary.id:
                rel.target_id = primary.id
            await self.store_relation(rel)

        # Store merged concept and delete secondary
        await self.store_concept(primary)
        await self.delete_concept(secondary.id)

        return primary.id

    async def delete_concept(self, concept_id: str) -> bool:
        """Delete a concept and its relations."""
        await self.initialize()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM relations WHERE source_id = ? OR target_id = ?",
                      (concept_id, concept_id))
        cursor.execute("DELETE FROM concepts WHERE id = ?", (concept_id,))

        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()

        if concept_id in self._concept_cache:
            del self._concept_cache[concept_id]

        return deleted

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _row_to_concept(self, row: tuple) -> Concept:
        """Convert database row to Concept."""
        return Concept(
            id=row[0],
            name=row[1],
            concept_type=ConceptType(row[2]),
            definition=row[3],
            domain=row[4] or "general",
            properties=json.loads(row[5]) if row[5] else {},
            confidence=row[6] or 0.5,
            source=row[7] or "unknown",
            created_at=datetime.fromisoformat(row[8]) if row[8] else datetime.now(),
            updated_at=datetime.fromisoformat(row[9]) if row[9] else datetime.now(),
            access_count=row[10] or 0,
            embedding=json.loads(row[11]) if row[11] else None,
            aliases=json.loads(row[12]) if row[12] else [],
            examples=json.loads(row[13]) if row[13] else [],
            counter_examples=json.loads(row[14]) if row[14] else [],
            tags=json.loads(row[15]) if row[15] else []
        )

    def _row_to_relation(self, row: tuple) -> ConceptRelation:
        """Convert database row to ConceptRelation."""
        return ConceptRelation(
            id=row[0],
            source_id=row[1],
            target_id=row[2],
            relation_type=RelationType(row[3]),
            strength=row[4] or 0.5,
            properties=json.loads(row[5]) if row[5] else {},
            bidirectional=bool(row[6]),
            confidence=row[7] or 0.5
        )

    def _trim_cache(self) -> None:
        """Trim caches to limit."""
        if len(self._concept_cache) > self._cache_limit:
            sorted_items = sorted(
                self._concept_cache.items(),
                key=lambda x: x[1].access_count
            )
            for key, _ in sorted_items[:len(self._concept_cache) - self._cache_limit]:
                del self._concept_cache[key]

    async def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        await self.initialize()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM concepts")
        total_concepts = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM relations")
        total_relations = cursor.fetchone()[0]

        cursor.execute("""
            SELECT domain, COUNT(*) FROM concepts GROUP BY domain
        """)
        by_domain = dict(cursor.fetchall())

        cursor.execute("""
            SELECT concept_type, COUNT(*) FROM concepts GROUP BY concept_type
        """)
        by_type = dict(cursor.fetchall())

        conn.close()

        return {
            "total_concepts": total_concepts,
            "total_relations": total_relations,
            "by_domain": by_domain,
            "by_type": by_type,
            "cache_size": len(self._concept_cache)
        }


# =============================================================================
# SEMANTIC MEMORY MANAGER
# =============================================================================

class SemanticMemoryManager:
    """
    High-level interface for semantic memory operations.

    Provides:
    - Easy concept/fact creation
    - Intelligent knowledge retrieval
    - Reasoning support
    - Knowledge organization
    """

    def __init__(self, store: Optional[SemanticMemoryStore] = None):
        self.store = store or SemanticMemoryStore()

    async def initialize(self) -> None:
        """Initialize the manager."""
        await self.store.initialize()

    async def learn_fact(
        self,
        name: str,
        definition: str,
        domain: str = "general",
        source: str = "learned",
        confidence: float = 0.7,
        examples: Optional[List[str]] = None
    ) -> str:
        """Learn a new fact."""
        concept_id = self.store._generate_id(name, "fact")

        concept = Concept(
            id=concept_id,
            name=name,
            concept_type=ConceptType.FACT,
            definition=definition,
            domain=domain,
            properties={},
            confidence=confidence,
            source=source,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            examples=examples or []
        )

        return await self.store.store_concept(concept)

    async def define_concept(
        self,
        name: str,
        definition: str,
        domain: str = "general",
        properties: Optional[Dict[str, Any]] = None,
        aliases: Optional[List[str]] = None
    ) -> str:
        """Define a new concept."""
        concept_id = self.store._generate_id(name, "definition")

        concept = Concept(
            id=concept_id,
            name=name,
            concept_type=ConceptType.DEFINITION,
            definition=definition,
            domain=domain,
            properties=properties or {},
            confidence=0.9,
            source="defined",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            aliases=aliases or []
        )

        return await self.store.store_concept(concept)

    async def learn_rule(
        self,
        name: str,
        rule: str,
        domain: str = "general",
        conditions: Optional[List[str]] = None,
        exceptions: Optional[List[str]] = None
    ) -> str:
        """Learn a new rule."""
        concept_id = self.store._generate_id(name, "rule")

        concept = Concept(
            id=concept_id,
            name=name,
            concept_type=ConceptType.RULE,
            definition=rule,
            domain=domain,
            properties={
                "conditions": conditions or [],
                "exceptions": exceptions or []
            },
            confidence=0.8,
            source="learned",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        return await self.store.store_concept(concept)

    async def learn_pattern(
        self,
        name: str,
        description: str,
        domain: str = "general",
        structure: Optional[Dict[str, Any]] = None,
        use_cases: Optional[List[str]] = None
    ) -> str:
        """Learn a new pattern."""
        concept_id = self.store._generate_id(name, "pattern")

        concept = Concept(
            id=concept_id,
            name=name,
            concept_type=ConceptType.PATTERN,
            definition=description,
            domain=domain,
            properties={"structure": structure or {}},
            confidence=0.85,
            source="learned",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            examples=use_cases or [],
            tags=["pattern"]
        )

        return await self.store.store_concept(concept)

    async def relate(
        self,
        source_name: str,
        target_name: str,
        relation: RelationType,
        strength: float = 0.7,
        bidirectional: bool = False
    ) -> Optional[str]:
        """Create a relationship between concepts."""
        source = await self.store.find_concept_by_name(source_name)
        target = await self.store.find_concept_by_name(target_name)

        if not source or not target:
            return None

        rel_id = self.store._generate_id(
            f"{source.id}{target.id}", relation.value
        )

        rel = ConceptRelation(
            id=rel_id,
            source_id=source.id,
            target_id=target.id,
            relation_type=relation,
            strength=strength,
            properties={},
            bidirectional=bidirectional,
            confidence=0.8
        )

        return await self.store.store_relation(rel)

    async def recall(
        self,
        query: str,
        domain: Optional[str] = None,
        limit: int = 10
    ) -> List[Concept]:
        """Recall concepts matching a query."""
        sq = SemanticQuery(
            text=query,
            domains=[domain] if domain else None,
            limit=limit
        )
        return await self.store.search_concepts(sq)

    async def what_is(self, name: str) -> Optional[str]:
        """Get the definition of a concept."""
        concept = await self.store.find_concept_by_name(name)
        if concept:
            return concept.definition
        return None

    async def get_related(
        self,
        name: str,
        relation: Optional[RelationType] = None
    ) -> List[str]:
        """Get concepts related to a given concept."""
        concept = await self.store.find_concept_by_name(name)
        if not concept:
            return []

        related = await self.store.get_related_concepts(
            concept.id,
            relation_types=[relation] if relation else None
        )

        return [c.name for c, _ in related]

    async def get_domain_knowledge(self, domain: str) -> List[Concept]:
        """Get all knowledge in a domain."""
        return await self.store.get_domain_concepts(domain)

    async def reinforce(self, name: str, delta: float = 0.05) -> bool:
        """Reinforce knowledge (increase confidence)."""
        concept = await self.store.find_concept_by_name(name)
        if concept:
            await self.store.update_confidence(concept.id, delta)
            return True
        return False

    async def challenge(self, name: str, delta: float = 0.1) -> bool:
        """Challenge knowledge (decrease confidence)."""
        return await self.reinforce(name, -delta)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "ConceptType",
    "RelationType",
    "ConfidenceLevel",
    "Concept",
    "ConceptRelation",
    "SemanticQuery",
    "SemanticMemoryStore",
    "SemanticMemoryManager"
]
