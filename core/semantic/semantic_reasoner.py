#!/usr/bin/env python3
"""
BAEL - Semantic Reasoner
Advanced semantic reasoning and natural language understanding.

Features:
- Semantic parsing
- Entailment detection
- Semantic similarity
- Word sense disambiguation
- Semantic role labeling
- Concept extraction
- Semantic composition
- Meaning representation
"""

import asyncio
import hashlib
import math
import random
import re
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

class SemanticRelationType(Enum):
    """Types of semantic relations."""
    SYNONYM = "synonym"
    ANTONYM = "antonym"
    HYPERNYM = "hypernym"
    HYPONYM = "hyponym"
    MERONYM = "meronym"
    HOLONYM = "holonym"
    ENTAILS = "entails"
    CAUSES = "causes"


class EntailmentType(Enum):
    """Types of textual entailment."""
    ENTAILMENT = "entailment"
    CONTRADICTION = "contradiction"
    NEUTRAL = "neutral"


class SemanticRole(Enum):
    """Semantic roles (thematic roles)."""
    AGENT = "agent"
    PATIENT = "patient"
    THEME = "theme"
    EXPERIENCER = "experiencer"
    BENEFICIARY = "beneficiary"
    INSTRUMENT = "instrument"
    LOCATION = "location"
    SOURCE = "source"
    GOAL = "goal"
    TIME = "time"


class ConceptType(Enum):
    """Types of concepts."""
    ENTITY = "entity"
    EVENT = "event"
    STATE = "state"
    PROPERTY = "property"
    RELATION = "relation"
    QUANTITY = "quantity"


class SenseType(Enum):
    """Word sense types."""
    NOUN = "noun"
    VERB = "verb"
    ADJECTIVE = "adjective"
    ADVERB = "adverb"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class SemanticNode:
    """A node in semantic representation."""
    node_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    concept: str = ""
    concept_type: ConceptType = ConceptType.ENTITY
    properties: Dict[str, Any] = field(default_factory=dict)
    sense_id: Optional[str] = None


@dataclass
class SemanticEdge:
    """An edge in semantic representation."""
    edge_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str = ""
    target_id: str = ""
    relation: SemanticRelationType = SemanticRelationType.SYNONYM
    weight: float = 1.0


@dataclass
class WordSense:
    """A word sense."""
    sense_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    word: str = ""
    sense_type: SenseType = SenseType.NOUN
    definition: str = ""
    examples: List[str] = field(default_factory=list)
    synonyms: List[str] = field(default_factory=list)
    frequency: float = 0.0


@dataclass
class SemanticFrame:
    """A semantic frame."""
    frame_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    predicate: str = ""
    roles: Dict[SemanticRole, str] = field(default_factory=dict)
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Proposition:
    """A logical proposition."""
    proposition_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    predicate: str = ""
    arguments: List[str] = field(default_factory=list)
    negated: bool = False
    modality: Optional[str] = None  # possible, necessary, etc.


@dataclass
class EntailmentResult:
    """Result of entailment analysis."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    premise: str = ""
    hypothesis: str = ""
    entailment: EntailmentType = EntailmentType.NEUTRAL
    confidence: float = 0.0
    explanation: str = ""


@dataclass
class SimilarityResult:
    """Result of similarity computation."""
    text1: str = ""
    text2: str = ""
    similarity: float = 0.0
    method: str = ""


# =============================================================================
# LEXICON
# =============================================================================

class SemanticLexicon:
    """Semantic lexicon for word meanings."""

    def __init__(self):
        self._senses: Dict[str, List[WordSense]] = defaultdict(list)
        self._sense_by_id: Dict[str, WordSense] = {}
        self._relations: Dict[str, Dict[str, List[str]]] = defaultdict(
            lambda: defaultdict(list)
        )  # sense_id -> relation -> [sense_ids]

        # Initialize with some common words
        self._initialize_lexicon()

    def _initialize_lexicon(self) -> None:
        """Initialize with basic lexicon."""
        # Add some example senses
        words = [
            ("dog", SenseType.NOUN, "A domesticated carnivorous mammal"),
            ("cat", SenseType.NOUN, "A small domesticated carnivorous mammal"),
            ("animal", SenseType.NOUN, "A living organism that feeds on organic matter"),
            ("run", SenseType.VERB, "Move at a speed faster than a walk"),
            ("walk", SenseType.VERB, "Move at a regular pace by lifting feet"),
            ("fast", SenseType.ADJECTIVE, "Moving or capable of moving at high speed"),
            ("slow", SenseType.ADJECTIVE, "Moving or operating at a low speed"),
            ("happy", SenseType.ADJECTIVE, "Feeling or showing pleasure or contentment"),
            ("sad", SenseType.ADJECTIVE, "Feeling or showing sorrow"),
            ("big", SenseType.ADJECTIVE, "Of considerable size or extent"),
            ("small", SenseType.ADJECTIVE, "Of limited size"),
        ]

        for word, sense_type, definition in words:
            sense = WordSense(
                word=word,
                sense_type=sense_type,
                definition=definition
            )
            self.add_sense(sense)

        # Add some relations
        self.add_relation("dog", "animal", SemanticRelationType.HYPERNYM)
        self.add_relation("cat", "animal", SemanticRelationType.HYPERNYM)
        self.add_relation("fast", "slow", SemanticRelationType.ANTONYM)
        self.add_relation("happy", "sad", SemanticRelationType.ANTONYM)
        self.add_relation("big", "small", SemanticRelationType.ANTONYM)

    def add_sense(self, sense: WordSense) -> None:
        """Add a word sense."""
        self._senses[sense.word].append(sense)
        self._sense_by_id[sense.sense_id] = sense

    def get_senses(self, word: str) -> List[WordSense]:
        """Get all senses of a word."""
        return self._senses.get(word.lower(), [])

    def get_sense(self, sense_id: str) -> Optional[WordSense]:
        """Get sense by ID."""
        return self._sense_by_id.get(sense_id)

    def add_relation(
        self,
        word1: str,
        word2: str,
        relation: SemanticRelationType
    ) -> None:
        """Add semantic relation between words."""
        senses1 = self.get_senses(word1)
        senses2 = self.get_senses(word2)

        if senses1 and senses2:
            sense1 = senses1[0]
            sense2 = senses2[0]
            self._relations[sense1.sense_id][relation.value].append(sense2.sense_id)

    def get_related(
        self,
        word: str,
        relation: SemanticRelationType
    ) -> List[str]:
        """Get words with given relation."""
        senses = self.get_senses(word)
        if not senses:
            return []

        related_ids = self._relations[senses[0].sense_id].get(relation.value, [])
        return [
            self._sense_by_id[sid].word
            for sid in related_ids
            if sid in self._sense_by_id
        ]


# =============================================================================
# SEMANTIC PARSER
# =============================================================================

class SemanticParser:
    """Parse text into semantic representations."""

    def __init__(self, lexicon: SemanticLexicon):
        self._lexicon = lexicon

    def parse(self, text: str) -> List[SemanticFrame]:
        """Parse text into semantic frames."""
        # Simple rule-based parsing
        frames = []

        # Tokenize
        tokens = self._tokenize(text)

        # Find predicates (verbs)
        for i, token in enumerate(tokens):
            senses = self._lexicon.get_senses(token)
            verb_senses = [s for s in senses if s.sense_type == SenseType.VERB]

            if verb_senses:
                frame = self._extract_frame(tokens, i, verb_senses[0])
                if frame:
                    frames.append(frame)

        return frames

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization."""
        # Remove punctuation and lowercase
        text = re.sub(r'[^\w\s]', '', text.lower())
        return text.split()

    def _extract_frame(
        self,
        tokens: List[str],
        predicate_idx: int,
        predicate_sense: WordSense
    ) -> Optional[SemanticFrame]:
        """Extract semantic frame from tokens."""
        frame = SemanticFrame(
            name=f"{predicate_sense.word}_frame",
            predicate=predicate_sense.word
        )

        # Simple heuristic: word before predicate is agent
        if predicate_idx > 0:
            frame.roles[SemanticRole.AGENT] = tokens[predicate_idx - 1]

        # Word after predicate is patient/theme
        if predicate_idx < len(tokens) - 1:
            frame.roles[SemanticRole.PATIENT] = tokens[predicate_idx + 1]

        return frame

    def to_propositions(self, frames: List[SemanticFrame]) -> List[Proposition]:
        """Convert frames to propositions."""
        propositions = []

        for frame in frames:
            args = []
            for role in [SemanticRole.AGENT, SemanticRole.PATIENT, SemanticRole.THEME]:
                if role in frame.roles:
                    args.append(frame.roles[role])

            prop = Proposition(
                predicate=frame.predicate,
                arguments=args
            )
            propositions.append(prop)

        return propositions


# =============================================================================
# WORD SENSE DISAMBIGUATOR
# =============================================================================

class WordSenseDisambiguator:
    """Disambiguate word senses in context."""

    def __init__(self, lexicon: SemanticLexicon):
        self._lexicon = lexicon

    def disambiguate(
        self,
        word: str,
        context: List[str]
    ) -> Optional[WordSense]:
        """Disambiguate word sense based on context."""
        senses = self._lexicon.get_senses(word)

        if not senses:
            return None

        if len(senses) == 1:
            return senses[0]

        # Simple overlap-based disambiguation
        best_sense = None
        best_score = -1

        for sense in senses:
            score = self._compute_overlap(sense, context)
            if score > best_score:
                best_score = score
                best_sense = sense

        return best_sense

    def _compute_overlap(
        self,
        sense: WordSense,
        context: List[str]
    ) -> float:
        """Compute overlap between sense and context."""
        # Get words from definition and examples
        sense_words = set()

        if sense.definition:
            sense_words.update(sense.definition.lower().split())

        for example in sense.examples:
            sense_words.update(example.lower().split())

        sense_words.update(s.lower() for s in sense.synonyms)

        # Compute overlap
        context_set = set(w.lower() for w in context)
        overlap = len(sense_words & context_set)

        return overlap


# =============================================================================
# SIMILARITY CALCULATOR
# =============================================================================

class SimilarityCalculator:
    """Calculate semantic similarity."""

    def __init__(self, lexicon: SemanticLexicon):
        self._lexicon = lexicon
        self._word_vectors: Dict[str, List[float]] = {}

        # Initialize simple word vectors
        self._initialize_vectors()

    def _initialize_vectors(self) -> None:
        """Initialize simple word vectors."""
        # Generate random but consistent vectors for known words
        random.seed(42)
        dim = 50

        for word in list(self._lexicon._senses.keys()):
            self._word_vectors[word] = [random.gauss(0, 1) for _ in range(dim)]

            # Make related words have similar vectors
            for rel in [SemanticRelationType.SYNONYM, SemanticRelationType.HYPERNYM]:
                related = self._lexicon.get_related(word, rel)
                for rel_word in related:
                    if rel_word not in self._word_vectors:
                        # Similar but not identical
                        base = self._word_vectors[word]
                        noise = [random.gauss(0, 0.1) for _ in range(dim)]
                        self._word_vectors[rel_word] = [
                            b + n for b, n in zip(base, noise)
                        ]

    def word_similarity(self, word1: str, word2: str) -> float:
        """Compute similarity between two words."""
        word1 = word1.lower()
        word2 = word2.lower()

        if word1 == word2:
            return 1.0

        # Check lexical relations
        related = self._lexicon.get_related(word1, SemanticRelationType.SYNONYM)
        if word2 in related:
            return 0.9

        related = self._lexicon.get_related(word1, SemanticRelationType.ANTONYM)
        if word2 in related:
            return 0.1

        # Vector similarity
        vec1 = self._word_vectors.get(word1)
        vec2 = self._word_vectors.get(word2)

        if vec1 and vec2:
            return self._cosine_similarity(vec1, vec2)

        return 0.0

    def _cosine_similarity(
        self,
        vec1: List[float],
        vec2: List[float]
    ) -> float:
        """Compute cosine similarity."""
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return (dot / (norm1 * norm2) + 1) / 2  # Normalize to [0, 1]

    def sentence_similarity(
        self,
        text1: str,
        text2: str
    ) -> SimilarityResult:
        """Compute similarity between two sentences."""
        # Tokenize
        words1 = [w.lower() for w in re.sub(r'[^\w\s]', '', text1).split()]
        words2 = [w.lower() for w in re.sub(r'[^\w\s]', '', text2).split()]

        if not words1 or not words2:
            return SimilarityResult(
                text1=text1,
                text2=text2,
                similarity=0.0,
                method="word_overlap"
            )

        # Compute average pairwise similarity
        total_sim = 0.0
        count = 0

        for w1 in words1:
            best_sim = 0.0
            for w2 in words2:
                sim = self.word_similarity(w1, w2)
                best_sim = max(best_sim, sim)
            total_sim += best_sim
            count += 1

        avg_sim = total_sim / count if count > 0 else 0.0

        return SimilarityResult(
            text1=text1,
            text2=text2,
            similarity=avg_sim,
            method="average_best_match"
        )


# =============================================================================
# ENTAILMENT DETECTOR
# =============================================================================

class EntailmentDetector:
    """Detect textual entailment."""

    def __init__(
        self,
        lexicon: SemanticLexicon,
        similarity_calc: SimilarityCalculator
    ):
        self._lexicon = lexicon
        self._similarity = similarity_calc

    def check_entailment(
        self,
        premise: str,
        hypothesis: str
    ) -> EntailmentResult:
        """Check if premise entails hypothesis."""
        # Simple heuristic-based entailment

        # Tokenize
        premise_words = set(w.lower() for w in re.sub(r'[^\w\s]', '', premise).split())
        hypo_words = set(w.lower() for w in re.sub(r'[^\w\s]', '', hypothesis).split())

        # Check for negation
        negation_words = {"not", "no", "never", "neither", "nobody", "nothing"}
        premise_negated = bool(premise_words & negation_words)
        hypo_negated = bool(hypo_words & negation_words)

        # Check word overlap
        common_words = premise_words & hypo_words
        hypo_coverage = len(common_words) / len(hypo_words) if hypo_words else 0

        # Check for antonyms
        has_antonym = False
        for w1 in premise_words:
            antonyms = self._lexicon.get_related(w1, SemanticRelationType.ANTONYM)
            if any(a in hypo_words for a in antonyms):
                has_antonym = True
                break

        # Compute sentence similarity
        sim_result = self._similarity.sentence_similarity(premise, hypothesis)

        # Decision logic
        if has_antonym or (premise_negated != hypo_negated):
            entailment = EntailmentType.CONTRADICTION
            confidence = 0.7
            explanation = "Detected contradiction through antonyms or negation"
        elif hypo_coverage > 0.8 and sim_result.similarity > 0.7:
            entailment = EntailmentType.ENTAILMENT
            confidence = sim_result.similarity
            explanation = f"High word overlap ({hypo_coverage:.2%}) and similarity ({sim_result.similarity:.2f})"
        elif sim_result.similarity > 0.5:
            entailment = EntailmentType.NEUTRAL
            confidence = 0.5
            explanation = "Moderate similarity but insufficient evidence for entailment"
        else:
            entailment = EntailmentType.NEUTRAL
            confidence = 0.3
            explanation = "Low similarity, cannot determine entailment"

        return EntailmentResult(
            premise=premise,
            hypothesis=hypothesis,
            entailment=entailment,
            confidence=confidence,
            explanation=explanation
        )


# =============================================================================
# CONCEPT EXTRACTOR
# =============================================================================

class ConceptExtractor:
    """Extract concepts from text."""

    def __init__(self, lexicon: SemanticLexicon):
        self._lexicon = lexicon

    def extract_concepts(self, text: str) -> List[SemanticNode]:
        """Extract concepts from text."""
        concepts = []

        # Tokenize
        words = [w.lower() for w in re.sub(r'[^\w\s]', '', text).split()]

        for word in words:
            senses = self._lexicon.get_senses(word)

            if senses:
                sense = senses[0]
                concept_type = self._sense_type_to_concept_type(sense.sense_type)

                concept = SemanticNode(
                    concept=word,
                    concept_type=concept_type,
                    sense_id=sense.sense_id,
                    properties={"definition": sense.definition}
                )
                concepts.append(concept)
            else:
                # Unknown word - add as entity
                concept = SemanticNode(
                    concept=word,
                    concept_type=ConceptType.ENTITY
                )
                concepts.append(concept)

        return concepts

    def _sense_type_to_concept_type(self, sense_type: SenseType) -> ConceptType:
        """Convert sense type to concept type."""
        mapping = {
            SenseType.NOUN: ConceptType.ENTITY,
            SenseType.VERB: ConceptType.EVENT,
            SenseType.ADJECTIVE: ConceptType.PROPERTY,
            SenseType.ADVERB: ConceptType.PROPERTY
        }
        return mapping.get(sense_type, ConceptType.ENTITY)

    def extract_relations(
        self,
        concepts: List[SemanticNode]
    ) -> List[SemanticEdge]:
        """Extract relations between concepts."""
        edges = []

        for i, c1 in enumerate(concepts):
            for c2 in concepts[i + 1:]:
                # Check lexical relations
                for rel_type in SemanticRelationType:
                    related = self._lexicon.get_related(c1.concept, rel_type)
                    if c2.concept in related:
                        edge = SemanticEdge(
                            source_id=c1.node_id,
                            target_id=c2.node_id,
                            relation=rel_type
                        )
                        edges.append(edge)

        return edges


# =============================================================================
# SEMANTIC COMPOSER
# =============================================================================

class SemanticComposer:
    """Compose meanings compositionally."""

    def __init__(self, similarity_calc: SimilarityCalculator):
        self._similarity = similarity_calc

    def compose(
        self,
        concepts: List[SemanticNode]
    ) -> Optional[SemanticNode]:
        """Compose concepts into unified meaning."""
        if not concepts:
            return None

        if len(concepts) == 1:
            return concepts[0]

        # Create composite concept
        composite = SemanticNode(
            concept="_".join(c.concept for c in concepts),
            concept_type=self._determine_composite_type(concepts)
        )

        # Aggregate properties
        for concept in concepts:
            for key, value in concept.properties.items():
                if key not in composite.properties:
                    composite.properties[key] = []
                if isinstance(composite.properties[key], list):
                    composite.properties[key].append(value)

        return composite

    def _determine_composite_type(
        self,
        concepts: List[SemanticNode]
    ) -> ConceptType:
        """Determine type of composite concept."""
        types = [c.concept_type for c in concepts]

        # Events dominate
        if ConceptType.EVENT in types:
            return ConceptType.EVENT

        # Relations next
        if ConceptType.RELATION in types:
            return ConceptType.RELATION

        # Then entities
        if ConceptType.ENTITY in types:
            return ConceptType.ENTITY

        return ConceptType.PROPERTY


# =============================================================================
# SEMANTIC REASONER
# =============================================================================

class SemanticReasoner:
    """
    Semantic Reasoner for BAEL.

    Advanced semantic reasoning and natural language understanding.
    """

    def __init__(self):
        self._lexicon = SemanticLexicon()
        self._parser = SemanticParser(self._lexicon)
        self._wsd = WordSenseDisambiguator(self._lexicon)
        self._similarity = SimilarityCalculator(self._lexicon)
        self._entailment = EntailmentDetector(self._lexicon, self._similarity)
        self._concept_extractor = ConceptExtractor(self._lexicon)
        self._composer = SemanticComposer(self._similarity)

    # -------------------------------------------------------------------------
    # LEXICON
    # -------------------------------------------------------------------------

    def add_word(
        self,
        word: str,
        sense_type: SenseType,
        definition: str,
        synonyms: Optional[List[str]] = None,
        examples: Optional[List[str]] = None
    ) -> WordSense:
        """Add a word to the lexicon."""
        sense = WordSense(
            word=word.lower(),
            sense_type=sense_type,
            definition=definition,
            synonyms=synonyms or [],
            examples=examples or []
        )
        self._lexicon.add_sense(sense)
        return sense

    def add_semantic_relation(
        self,
        word1: str,
        word2: str,
        relation: SemanticRelationType
    ) -> None:
        """Add semantic relation between words."""
        self._lexicon.add_relation(word1, word2, relation)

    def get_synonyms(self, word: str) -> List[str]:
        """Get synonyms of a word."""
        return self._lexicon.get_related(word, SemanticRelationType.SYNONYM)

    def get_antonyms(self, word: str) -> List[str]:
        """Get antonyms of a word."""
        return self._lexicon.get_related(word, SemanticRelationType.ANTONYM)

    def get_hypernyms(self, word: str) -> List[str]:
        """Get hypernyms (more general terms) of a word."""
        return self._lexicon.get_related(word, SemanticRelationType.HYPERNYM)

    # -------------------------------------------------------------------------
    # PARSING
    # -------------------------------------------------------------------------

    def parse(self, text: str) -> List[SemanticFrame]:
        """Parse text into semantic frames."""
        return self._parser.parse(text)

    def to_propositions(self, text: str) -> List[Proposition]:
        """Convert text to logical propositions."""
        frames = self._parser.parse(text)
        return self._parser.to_propositions(frames)

    # -------------------------------------------------------------------------
    # WORD SENSE DISAMBIGUATION
    # -------------------------------------------------------------------------

    def disambiguate(
        self,
        word: str,
        context: str
    ) -> Optional[WordSense]:
        """Disambiguate word sense in context."""
        context_words = context.lower().split()
        return self._wsd.disambiguate(word, context_words)

    def get_word_senses(self, word: str) -> List[WordSense]:
        """Get all senses of a word."""
        return self._lexicon.get_senses(word)

    # -------------------------------------------------------------------------
    # SIMILARITY
    # -------------------------------------------------------------------------

    def word_similarity(self, word1: str, word2: str) -> float:
        """Compute similarity between two words."""
        return self._similarity.word_similarity(word1, word2)

    def sentence_similarity(
        self,
        text1: str,
        text2: str
    ) -> SimilarityResult:
        """Compute similarity between two sentences."""
        return self._similarity.sentence_similarity(text1, text2)

    # -------------------------------------------------------------------------
    # ENTAILMENT
    # -------------------------------------------------------------------------

    def check_entailment(
        self,
        premise: str,
        hypothesis: str
    ) -> EntailmentResult:
        """Check textual entailment."""
        return self._entailment.check_entailment(premise, hypothesis)

    def contradicts(self, text1: str, text2: str) -> bool:
        """Check if two texts contradict each other."""
        result = self._entailment.check_entailment(text1, text2)
        return result.entailment == EntailmentType.CONTRADICTION

    def entails(self, premise: str, hypothesis: str) -> bool:
        """Check if premise entails hypothesis."""
        result = self._entailment.check_entailment(premise, hypothesis)
        return result.entailment == EntailmentType.ENTAILMENT

    # -------------------------------------------------------------------------
    # CONCEPT EXTRACTION
    # -------------------------------------------------------------------------

    def extract_concepts(self, text: str) -> List[SemanticNode]:
        """Extract concepts from text."""
        return self._concept_extractor.extract_concepts(text)

    def extract_relations(
        self,
        text: str
    ) -> Tuple[List[SemanticNode], List[SemanticEdge]]:
        """Extract concepts and relations from text."""
        concepts = self._concept_extractor.extract_concepts(text)
        relations = self._concept_extractor.extract_relations(concepts)
        return concepts, relations

    # -------------------------------------------------------------------------
    # COMPOSITION
    # -------------------------------------------------------------------------

    def compose_meaning(
        self,
        texts: List[str]
    ) -> Optional[SemanticNode]:
        """Compose meaning from multiple texts."""
        all_concepts = []

        for text in texts:
            concepts = self.extract_concepts(text)
            all_concepts.extend(concepts)

        return self._composer.compose(all_concepts)

    # -------------------------------------------------------------------------
    # SEMANTIC ROLES
    # -------------------------------------------------------------------------

    def extract_roles(self, text: str) -> Dict[SemanticRole, List[str]]:
        """Extract semantic roles from text."""
        frames = self.parse(text)

        roles: Dict[SemanticRole, List[str]] = defaultdict(list)

        for frame in frames:
            for role, filler in frame.roles.items():
                roles[role].append(filler)

        return dict(roles)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Semantic Reasoner."""
    print("=" * 70)
    print("BAEL - SEMANTIC REASONER DEMO")
    print("Advanced Semantic Reasoning and Natural Language Understanding")
    print("=" * 70)
    print()

    reasoner = SemanticReasoner()

    # 1. Word Relationships
    print("1. SEMANTIC RELATIONS:")
    print("-" * 40)

    print(f"   Synonyms of 'happy': {reasoner.get_synonyms('happy')}")
    print(f"   Antonyms of 'happy': {reasoner.get_antonyms('happy')}")
    print(f"   Hypernyms of 'dog': {reasoner.get_hypernyms('dog')}")

    # Add more words
    reasoner.add_word(
        "joyful", SenseType.ADJECTIVE,
        "Feeling or expressing great happiness",
        synonyms=["happy", "elated"]
    )
    reasoner.add_semantic_relation("happy", "joyful", SemanticRelationType.SYNONYM)

    print(f"   After adding: Synonyms of 'happy': {reasoner.get_synonyms('happy')}")
    print()

    # 2. Word Similarity
    print("2. WORD SIMILARITY:")
    print("-" * 40)

    pairs = [
        ("dog", "cat"),
        ("dog", "animal"),
        ("happy", "sad"),
        ("fast", "quick"),
        ("big", "large")
    ]

    for w1, w2 in pairs:
        sim = reasoner.word_similarity(w1, w2)
        print(f"   {w1} <-> {w2}: {sim:.3f}")
    print()

    # 3. Sentence Similarity
    print("3. SENTENCE SIMILARITY:")
    print("-" * 40)

    sentences = [
        ("The dog runs fast", "The cat runs quickly"),
        ("I am happy", "I am sad"),
        ("The big dog", "The large animal"),
    ]

    for s1, s2 in sentences:
        result = reasoner.sentence_similarity(s1, s2)
        print(f"   '{s1}'")
        print(f"   '{s2}'")
        print(f"   Similarity: {result.similarity:.3f}")
        print()

    # 4. Textual Entailment
    print("4. TEXTUAL ENTAILMENT:")
    print("-" * 40)

    entailment_pairs = [
        ("The dog runs in the park", "The animal moves in the park"),
        ("John is happy", "John is sad"),
        ("It is raining", "The sky is blue"),
    ]

    for premise, hypothesis in entailment_pairs:
        result = reasoner.check_entailment(premise, hypothesis)
        print(f"   P: '{premise}'")
        print(f"   H: '{hypothesis}'")
        print(f"   Result: {result.entailment.value} (confidence: {result.confidence:.2f})")
        print(f"   Explanation: {result.explanation}")
        print()

    # 5. Semantic Parsing
    print("5. SEMANTIC PARSING:")
    print("-" * 40)

    text = "The dog runs fast"
    frames = reasoner.parse(text)

    print(f"   Text: '{text}'")
    print(f"   Frames extracted: {len(frames)}")

    for frame in frames:
        print(f"     Frame: {frame.name}")
        print(f"     Predicate: {frame.predicate}")
        print(f"     Roles: {dict(frame.roles)}")
    print()

    # 6. Propositions
    print("6. PROPOSITIONS:")
    print("-" * 40)

    text = "The cat walks slowly"
    props = reasoner.to_propositions(text)

    print(f"   Text: '{text}'")
    for prop in props:
        print(f"   Proposition: {prop.predicate}({', '.join(prop.arguments)})")
    print()

    # 7. Concept Extraction
    print("7. CONCEPT EXTRACTION:")
    print("-" * 40)

    text = "The happy dog runs fast in the big park"
    concepts = reasoner.extract_concepts(text)

    print(f"   Text: '{text}'")
    print(f"   Concepts:")
    for concept in concepts:
        print(f"     - {concept.concept} ({concept.concept_type.value})")
    print()

    # 8. Semantic Roles
    print("8. SEMANTIC ROLE LABELING:")
    print("-" * 40)

    text = "John walks the dog"
    roles = reasoner.extract_roles(text)

    print(f"   Text: '{text}'")
    print(f"   Roles:")
    for role, fillers in roles.items():
        print(f"     {role.value}: {fillers}")
    print()

    # 9. Word Sense Disambiguation
    print("9. WORD SENSE DISAMBIGUATION:")
    print("-" * 40)

    word = "run"
    context = "The dog likes to run in the park"
    sense = reasoner.disambiguate(word, context)

    print(f"   Word: '{word}'")
    print(f"   Context: '{context}'")
    if sense:
        print(f"   Disambiguated sense: {sense.definition}")
    print()

    # 10. Meaning Composition
    print("10. MEANING COMPOSITION:")
    print("-" * 40)

    texts = ["happy dog", "fast animal", "big park"]
    composed = reasoner.compose_meaning(texts)

    print(f"   Input texts: {texts}")
    if composed:
        print(f"   Composed concept: {composed.concept}")
        print(f"   Concept type: {composed.concept_type.value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Semantic Reasoner Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
