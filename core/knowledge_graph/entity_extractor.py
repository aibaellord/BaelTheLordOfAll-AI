"""
BAEL Entity Extractor
======================

Extracts named entities from text.
Identifies people, organizations, concepts, etc.

Features:
- Named entity recognition
- Entity typing
- Coreference resolution
- Entity linking
- Confidence scoring
"""

import hashlib
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class EntityType(Enum):
    """Types of entities."""
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    DATE = "date"
    TIME = "time"
    MONEY = "money"
    PERCENT = "percent"
    PRODUCT = "product"
    EVENT = "event"
    CONCEPT = "concept"
    TECHNOLOGY = "technology"
    LANGUAGE = "language"
    CODE = "code"
    FILE = "file"
    URL = "url"
    EMAIL = "email"
    UNKNOWN = "unknown"


@dataclass
class EntityMention:
    """A mention of an entity in text."""
    text: str
    start: int
    end: int

    # Context
    sentence: str = ""
    context_before: str = ""
    context_after: str = ""


@dataclass
class Entity:
    """An extracted entity."""
    id: str
    text: str
    entity_type: EntityType

    # Mentions
    mentions: List[EntityMention] = field(default_factory=list)

    # Normalization
    canonical_form: str = ""
    aliases: List[str] = field(default_factory=list)

    # Confidence
    confidence: float = 1.0

    # Linking
    linked_id: Optional[str] = None  # External KB ID
    linked_source: Optional[str] = None  # KB source

    # Metadata
    attributes: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.canonical_form:
            self.canonical_form = self.text


@dataclass
class ExtractionResult:
    """Result of entity extraction."""
    text: str

    # Entities
    entities: List[Entity] = field(default_factory=list)

    # Statistics
    entity_count: int = 0
    by_type: Dict[EntityType, int] = field(default_factory=dict)

    # Timing
    extraction_time_ms: float = 0.0

    # Metadata
    extracted_at: datetime = field(default_factory=datetime.now)


class EntityExtractor:
    """
    Entity extractor for BAEL.

    Extracts and classifies named entities.
    """

    # Pattern-based extraction rules
    PATTERNS = {
        EntityType.EMAIL: r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        EntityType.URL: r'https?://[^\s<>"{}|\\^`\[\]]+',
        EntityType.FILE: r'\b[\w-]+\.(py|js|ts|json|yaml|yml|md|txt|csv|xml|html|css)\b',
        EntityType.DATE: r'\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b|\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b',
        EntityType.TIME: r'\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?\b',
        EntityType.MONEY: r'\$[\d,]+(?:\.\d{2})?|\€[\d,]+(?:\.\d{2})?',
        EntityType.PERCENT: r'\b\d+(?:\.\d+)?%\b',
        EntityType.CODE: r'`[^`]+`|```[\s\S]*?```',
    }

    # Common technology terms
    TECH_TERMS = {
        "python", "javascript", "typescript", "java", "rust", "go", "golang",
        "react", "vue", "angular", "node", "django", "flask", "fastapi",
        "docker", "kubernetes", "aws", "azure", "gcp", "linux", "windows",
        "api", "rest", "graphql", "sql", "nosql", "mongodb", "postgresql",
        "redis", "elasticsearch", "kafka", "rabbitmq", "git", "github",
        "machine learning", "deep learning", "neural network", "ai", "ml",
        "transformer", "gpt", "llm", "embedding", "vector", "database",
    }

    # Common programming languages
    LANGUAGES = {
        "python", "javascript", "typescript", "java", "c", "c++", "c#",
        "ruby", "go", "rust", "swift", "kotlin", "scala", "php", "perl",
        "r", "matlab", "julia", "haskell", "erlang", "elixir", "clojure",
    }

    def __init__(self):
        # Entity cache
        self._cache: Dict[str, Entity] = {}

        # Coreference groups
        self._coref_groups: Dict[str, List[str]] = {}

        # Stats
        self.stats = {
            "texts_processed": 0,
            "entities_extracted": 0,
            "cache_hits": 0,
        }

    def extract(
        self,
        text: str,
        types: Optional[List[EntityType]] = None,
        min_confidence: float = 0.5,
    ) -> ExtractionResult:
        """
        Extract entities from text.

        Args:
            text: Input text
            types: Entity types to extract (None = all)
            min_confidence: Minimum confidence threshold

        Returns:
            Extraction result
        """
        import time
        start = time.time()

        result = ExtractionResult(text=text)
        entities = []

        # Pattern-based extraction
        for entity_type, pattern in self.PATTERNS.items():
            if types and entity_type not in types:
                continue

            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                entity = self._create_entity(
                    text=match.group(),
                    entity_type=entity_type,
                    start=match.start(),
                    end=match.end(),
                    full_text=text,
                    confidence=0.95,  # High confidence for patterns
                )
                entities.append(entity)

        # Rule-based extraction
        entities.extend(self._extract_by_rules(text, types))

        # NLP-based extraction (capitalization heuristics)
        entities.extend(self._extract_by_heuristics(text, types))

        # Filter by confidence
        entities = [e for e in entities if e.confidence >= min_confidence]

        # Deduplicate
        entities = self._deduplicate(entities)

        # Resolve coreferences
        entities = self._resolve_coreferences(entities, text)

        result.entities = entities
        result.entity_count = len(entities)
        result.by_type = self._count_by_type(entities)
        result.extraction_time_ms = (time.time() - start) * 1000

        self.stats["texts_processed"] += 1
        self.stats["entities_extracted"] += len(entities)

        return result

    def _create_entity(
        self,
        text: str,
        entity_type: EntityType,
        start: int,
        end: int,
        full_text: str,
        confidence: float = 1.0,
    ) -> Entity:
        """Create an entity from a match."""
        entity_id = hashlib.md5(
            f"{text}:{entity_type.value}".encode()
        ).hexdigest()[:12]

        # Get context
        context_start = max(0, start - 50)
        context_end = min(len(full_text), end + 50)

        mention = EntityMention(
            text=text,
            start=start,
            end=end,
            context_before=full_text[context_start:start],
            context_after=full_text[end:context_end],
        )

        entity = Entity(
            id=entity_id,
            text=text,
            entity_type=entity_type,
            mentions=[mention],
            confidence=confidence,
        )

        return entity

    def _extract_by_rules(
        self,
        text: str,
        types: Optional[List[EntityType]],
    ) -> List[Entity]:
        """Extract entities using rules."""
        entities = []

        # Technology terms
        if not types or EntityType.TECHNOLOGY in types:
            text_lower = text.lower()
            for term in self.TECH_TERMS:
                if term in text_lower:
                    # Find actual position
                    pattern = re.compile(re.escape(term), re.IGNORECASE)
                    for match in pattern.finditer(text):
                        entity = self._create_entity(
                            text=match.group(),
                            entity_type=EntityType.TECHNOLOGY,
                            start=match.start(),
                            end=match.end(),
                            full_text=text,
                            confidence=0.85,
                        )
                        entities.append(entity)

        # Programming languages
        if not types or EntityType.LANGUAGE in types:
            text_lower = text.lower()
            for lang in self.LANGUAGES:
                if lang in text_lower:
                    pattern = re.compile(r'\b' + re.escape(lang) + r'\b', re.IGNORECASE)
                    for match in pattern.finditer(text):
                        entity = self._create_entity(
                            text=match.group(),
                            entity_type=EntityType.LANGUAGE,
                            start=match.start(),
                            end=match.end(),
                            full_text=text,
                            confidence=0.9,
                        )
                        entities.append(entity)

        return entities

    def _extract_by_heuristics(
        self,
        text: str,
        types: Optional[List[EntityType]],
    ) -> List[Entity]:
        """Extract entities using heuristics."""
        entities = []

        # Capitalized phrases (potential proper nouns)
        if not types or EntityType.PERSON in types or EntityType.ORGANIZATION in types:
            # Match sequences of capitalized words
            pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b'

            for match in re.finditer(pattern, text):
                phrase = match.group()

                # Skip if it's a sentence start
                if match.start() > 0 and text[match.start() - 1] not in '.!?\n':
                    # Determine type based on context
                    entity_type = self._classify_proper_noun(phrase, text, match.start())

                    entity = self._create_entity(
                        text=phrase,
                        entity_type=entity_type,
                        start=match.start(),
                        end=match.end(),
                        full_text=text,
                        confidence=0.7,
                    )
                    entities.append(entity)

        return entities

    def _classify_proper_noun(
        self,
        phrase: str,
        text: str,
        position: int,
    ) -> EntityType:
        """Classify a proper noun phrase."""
        phrase_lower = phrase.lower()
        context = text[max(0, position - 100):position + len(phrase) + 100].lower()

        # Person indicators
        person_indicators = ["mr.", "mrs.", "ms.", "dr.", "prof.", "said", "wrote", "thinks"]
        if any(ind in context for ind in person_indicators):
            return EntityType.PERSON

        # Organization indicators
        org_indicators = ["inc.", "corp.", "ltd.", "company", "organization", "team", "group"]
        if any(ind in phrase_lower or ind in context for ind in org_indicators):
            return EntityType.ORGANIZATION

        # Location indicators
        loc_indicators = ["city", "country", "state", "region", "in", "at", "from"]
        if any(ind in context for ind in loc_indicators):
            return EntityType.LOCATION

        # Default to concept
        return EntityType.CONCEPT

    def _deduplicate(self, entities: List[Entity]) -> List[Entity]:
        """Deduplicate entities."""
        seen = {}

        for entity in entities:
            key = (entity.text.lower(), entity.entity_type)

            if key in seen:
                # Merge mentions
                existing = seen[key]
                existing.mentions.extend(entity.mentions)
                existing.confidence = max(existing.confidence, entity.confidence)
            else:
                seen[key] = entity

        return list(seen.values())

    def _resolve_coreferences(
        self,
        entities: List[Entity],
        text: str,
    ) -> List[Entity]:
        """Resolve coreferences between entities."""
        # Simple pronoun resolution
        pronouns = {"he", "she", "it", "they", "him", "her", "them", "his", "their"}

        # Find pronouns
        for match in re.finditer(r'\b(' + '|'.join(pronouns) + r')\b', text, re.IGNORECASE):
            pronoun = match.group().lower()
            position = match.start()

            # Find nearest preceding entity
            nearest = None
            nearest_dist = float('inf')

            for entity in entities:
                for mention in entity.mentions:
                    dist = position - mention.end
                    if 0 < dist < nearest_dist:
                        if entity.entity_type in [EntityType.PERSON, EntityType.ORGANIZATION]:
                            nearest = entity
                            nearest_dist = dist

            if nearest:
                # Add pronoun as alias
                if pronoun not in nearest.aliases:
                    nearest.aliases.append(pronoun)

        return entities

    def _count_by_type(
        self,
        entities: List[Entity],
    ) -> Dict[EntityType, int]:
        """Count entities by type."""
        counts = defaultdict(int)
        for entity in entities:
            counts[entity.entity_type] += 1
        return dict(counts)

    def link_entity(
        self,
        entity: Entity,
        kb_id: str,
        kb_source: str = "internal",
    ) -> None:
        """Link entity to knowledge base."""
        entity.linked_id = kb_id
        entity.linked_source = kb_source

        # Cache for future lookups
        self._cache[entity.text.lower()] = entity

    def get_cached(self, text: str) -> Optional[Entity]:
        """Get cached entity."""
        cached = self._cache.get(text.lower())
        if cached:
            self.stats["cache_hits"] += 1
        return cached

    def get_stats(self) -> Dict[str, Any]:
        """Get extractor statistics."""
        return {
            **self.stats,
            "cached_entities": len(self._cache),
        }


def demo():
    """Demonstrate entity extraction."""
    print("=" * 60)
    print("BAEL Entity Extractor Demo")
    print("=" * 60)

    extractor = EntityExtractor()

    text = """
    John Smith from Acme Corporation sent an email to jane@example.com
    about the Python project. The meeting is scheduled for 2024-03-15 at
    10:30 AM. They discussed using TensorFlow and PyTorch for the
    machine learning pipeline. The budget is $50,000 with a 15%
    contingency. Check the config.yaml file and visit https://api.example.com
    for more details.
    """

    print(f"\nInput text:")
    print(f"  {text[:100]}...")

    result = extractor.extract(text)

    print(f"\nExtracted {result.entity_count} entities:")

    for entity in result.entities:
        print(f"\n  [{entity.entity_type.value}] {entity.text}")
        print(f"    Confidence: {entity.confidence:.0%}")
        if entity.mentions:
            print(f"    Position: {entity.mentions[0].start}-{entity.mentions[0].end}")

    print(f"\nBy type:")
    for entity_type, count in result.by_type.items():
        print(f"  {entity_type.value}: {count}")

    print(f"\nExtraction time: {result.extraction_time_ms:.2f}ms")
    print(f"\nStats: {extractor.get_stats()}")


if __name__ == "__main__":
    demo()
