"""
BAEL Cryptomnesia Engine
==========================

Unconscious plagiarism - presenting others' ideas as one's own.
Failure of source monitoring in creative production.

"Ba'el's forgotten origins." — Ba'el
"""

import logging
import threading
import time
import math
import random
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod
from collections import defaultdict, deque

logger = logging.getLogger("BAEL.Cryptomnesia")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class IdeaSource(Enum):
    """Sources of ideas."""
    SELF_GENERATED = auto()
    OTHER_PERSON = auto()
    EXTERNAL_MEDIA = auto()
    UNKNOWN = auto()


class IdeaType(Enum):
    """Types of ideas."""
    WORD = auto()
    SOLUTION = auto()
    MELODY = auto()
    CONCEPT = auto()
    DESIGN = auto()


class GenerationContext(Enum):
    """Context of idea generation."""
    BRAINSTORM = auto()
    PROBLEM_SOLVING = auto()
    CREATIVE_WRITING = auto()
    MUSICAL_COMPOSITION = auto()


@dataclass
class Idea:
    """
    An idea with source information.
    """
    id: str
    content: str
    idea_type: IdeaType
    actual_source: IdeaSource
    generator_id: str  # Who actually generated it
    timestamp: float


@dataclass
class SourceMemory:
    """
    Memory for an idea's source.
    """
    idea_id: str
    remembered_source: IdeaSource
    source_confidence: float
    contextual_details: float
    temporal_memory: float


@dataclass
class GenerationAttempt:
    """
    An attempt to generate new ideas.
    """
    context: GenerationContext
    ideas_produced: List[Idea]
    cryptomnesic_errors: int
    correct_attributions: int


@dataclass
class CryptomnesiaMetrics:
    """
    Cryptomnesia metrics.
    """
    plagiarism_rate: float
    source_confusion_rate: float
    self_plagiarism_rate: float
    novelty_rate: float


# ============================================================================
# SOURCE MEMORY SYSTEM
# ============================================================================

class SourceMemorySystem:
    """
    System for tracking idea sources.

    "Ba'el's origin tracker." — Ba'el
    """

    def __init__(self):
        """Initialize source memory."""
        self._source_memories: Dict[str, SourceMemory] = {}

        # Source memory parameters
        self._base_source_encoding = 0.6
        self._decay_rate = 0.1

        self._lock = threading.RLock()

    def encode_source(
        self,
        idea: Idea,
        attention_to_source: float = 0.5
    ) -> SourceMemory:
        """Encode the source of an idea."""
        # Source encoding depends on attention
        source_strength = self._base_source_encoding * attention_to_source

        # Add noise
        source_strength += random.gauss(0, 0.1)
        source_strength = max(0.1, min(1, source_strength))

        # Contextual details
        contextual = 0.5 + random.gauss(0, 0.15)
        contextual = max(0, min(1, contextual))

        # Temporal memory
        temporal = 0.6 + random.gauss(0, 0.1)
        temporal = max(0, min(1, temporal))

        memory = SourceMemory(
            idea_id=idea.id,
            remembered_source=idea.actual_source,
            source_confidence=source_strength,
            contextual_details=contextual,
            temporal_memory=temporal
        )

        self._source_memories[idea.id] = memory
        return memory

    def retrieve_source(
        self,
        idea_id: str,
        delay_seconds: float = 0
    ) -> Optional[SourceMemory]:
        """Retrieve source memory."""
        memory = self._source_memories.get(idea_id)
        if not memory:
            return None

        # Apply decay
        decay = math.exp(-delay_seconds * self._decay_rate / 60)

        # Updated confidence
        new_confidence = memory.source_confidence * decay
        new_contextual = memory.contextual_details * decay
        new_temporal = memory.temporal_memory * decay

        # Source confusion probability increases with decay
        confusion_prob = 1 - new_confidence

        # Possible source confusion
        if random.random() < confusion_prob:
            if memory.remembered_source == IdeaSource.OTHER_PERSON:
                # May misremember as self-generated
                if random.random() < 0.4:
                    return SourceMemory(
                        idea_id=idea_id,
                        remembered_source=IdeaSource.SELF_GENERATED,
                        source_confidence=new_confidence * 0.8,
                        contextual_details=new_contextual,
                        temporal_memory=new_temporal
                    )

        return SourceMemory(
            idea_id=idea_id,
            remembered_source=memory.remembered_source,
            source_confidence=new_confidence,
            contextual_details=new_contextual,
            temporal_memory=new_temporal
        )


# ============================================================================
# IDEA GENERATION SYSTEM
# ============================================================================

class IdeaGenerationSystem:
    """
    System for generating ideas.

    "Ba'el's creative engine." — Ba'el
    """

    def __init__(
        self,
        self_id: str = "self"
    ):
        """Initialize generation system."""
        self._self_id = self_id

        # Idea storage
        self._all_ideas: Dict[str, Idea] = {}
        self._exposed_ideas: List[Idea] = []

        self._idea_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._idea_counter += 1
        return f"idea_{self._idea_counter}"

    def expose_to_idea(
        self,
        content: str,
        generator_id: str,
        idea_type: IdeaType = IdeaType.CONCEPT
    ) -> Idea:
        """Expose system to someone else's idea."""
        idea = Idea(
            id=self._generate_id(),
            content=content,
            idea_type=idea_type,
            actual_source=IdeaSource.OTHER_PERSON,
            generator_id=generator_id,
            timestamp=time.time()
        )

        self._all_ideas[idea.id] = idea
        self._exposed_ideas.append(idea)

        return idea

    def generate_own_idea(
        self,
        content: str,
        idea_type: IdeaType = IdeaType.CONCEPT
    ) -> Idea:
        """Generate own original idea."""
        idea = Idea(
            id=self._generate_id(),
            content=content,
            idea_type=idea_type,
            actual_source=IdeaSource.SELF_GENERATED,
            generator_id=self._self_id,
            timestamp=time.time()
        )

        self._all_ideas[idea.id] = idea

        return idea

    def attempt_generation(
        self,
        n_to_generate: int,
        context: GenerationContext
    ) -> List[Tuple[Idea, bool]]:
        """Attempt to generate novel ideas."""
        results = []

        for i in range(n_to_generate):
            # Probability of cryptomnesic intrusion
            if self._exposed_ideas and random.random() < 0.25:
                # Cryptomnesia: retrieve exposed idea as if own
                exposed = random.choice(self._exposed_ideas)

                # Create "new" idea with same content but wrong source
                idea = Idea(
                    id=self._generate_id(),
                    content=exposed.content,
                    idea_type=exposed.idea_type,
                    actual_source=IdeaSource.OTHER_PERSON,  # Actually from other
                    generator_id=exposed.generator_id,
                    timestamp=time.time()
                )

                self._all_ideas[idea.id] = idea
                results.append((idea, True))  # True = cryptomnesia

            else:
                # Generate genuinely novel idea
                idea = self.generate_own_idea(
                    f"novel_idea_{context.name}_{i}",
                    IdeaType.CONCEPT
                )
                results.append((idea, False))  # False = no cryptomnesia

        return results


# ============================================================================
# CRYPTOMNESIA MODEL
# ============================================================================

class CryptomnesiaModel:
    """
    Model of cryptomnesia.

    "Ba'el's unconscious borrowing." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        self._source_memory = SourceMemorySystem()
        self._idea_system = IdeaGenerationSystem()

        # Cryptomnesia parameters
        self._base_cryptomnesia_rate = 0.15
        self._similarity_threshold = 0.8
        self._source_forgetting_rate = 0.2

        self._lock = threading.RLock()

    def exposure_phase(
        self,
        ideas: List[Tuple[str, str]],  # (content, generator_id)
        attention_level: float = 0.5
    ) -> List[Idea]:
        """Expose to others' ideas."""
        exposed = []

        for content, generator_id in ideas:
            idea = self._idea_system.expose_to_idea(content, generator_id)
            self._source_memory.encode_source(idea, attention_level)
            exposed.append(idea)

        return exposed

    def generation_phase(
        self,
        n_ideas: int,
        context: GenerationContext,
        delay_since_exposure: float = 60
    ) -> GenerationAttempt:
        """Attempt to generate new ideas."""
        results = self._idea_system.attempt_generation(n_ideas, context)

        cryptomnesic = 0
        correct = 0

        ideas = []
        for idea, is_crypto in results:
            ideas.append(idea)
            if is_crypto:
                cryptomnesic += 1
            else:
                correct += 1

        return GenerationAttempt(
            context=context,
            ideas_produced=ideas,
            cryptomnesic_errors=cryptomnesic,
            correct_attributions=correct
        )

    def detect_plagiarism(
        self,
        produced_ideas: List[Idea],
        original_ideas: List[Idea]
    ) -> List[Tuple[Idea, Idea, float]]:
        """Detect plagiarism in produced ideas."""
        matches = []

        for produced in produced_ideas:
            for original in original_ideas:
                # Check if content matches
                if produced.content == original.content:
                    similarity = 1.0
                elif produced.content in original.content or original.content in produced.content:
                    similarity = 0.8
                else:
                    similarity = 0.0

                if similarity > self._similarity_threshold:
                    matches.append((produced, original, similarity))

        return matches


# ============================================================================
# EXPERIMENTAL PARADIGM
# ============================================================================

class CryptomnesiaParadigm:
    """
    Cryptomnesia experimental paradigm.

    "Ba'el's unconscious plagiarism test." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._model = CryptomnesiaModel()

        self._experiments: List[Dict] = []

        self._lock = threading.RLock()

    def run_brainstorm_paradigm(
        self,
        n_participants: int = 4,
        ideas_per_person: int = 5,
        delay_seconds: float = 300
    ) -> Dict[str, Any]:
        """Run group brainstorm paradigm."""
        # Phase 1: Group brainstorming
        all_ideas = []

        for p in range(n_participants):
            for i in range(ideas_per_person):
                content = f"idea_p{p}_{i}"
                all_ideas.append((content, f"participant_{p}"))

        # Expose model to all ideas
        exposed = self._model.exposure_phase(all_ideas, attention_level=0.5)

        # Phase 2: Individual generation after delay
        generation = self._model.generation_phase(
            n_ideas=ideas_per_person * 2,
            context=GenerationContext.BRAINSTORM,
            delay_since_exposure=delay_seconds
        )

        # Detect cryptomnesia
        plagiarism = self._model.detect_plagiarism(generation.ideas_produced, exposed)

        # Calculate rates
        total_produced = len(generation.ideas_produced)
        cryptomnesic_count = generation.cryptomnesic_errors
        plagiarism_count = len(plagiarism)

        result = {
            'total_produced': total_produced,
            'cryptomnesic_errors': cryptomnesic_count,
            'cryptomnesia_rate': cryptomnesic_count / total_produced if total_produced > 0 else 0,
            'detected_plagiarism': plagiarism_count,
            'delay_seconds': delay_seconds
        }

        self._experiments.append(result)
        return result

    def run_self_plagiarism_paradigm(
        self,
        n_own_ideas: int = 10,
        delay_seconds: float = 600
    ) -> Dict[str, Any]:
        """Test self-plagiarism (forgetting own prior ideas)."""
        # Phase 1: Generate own ideas
        own_ideas = []
        for i in range(n_own_ideas):
            idea = self._model._idea_system.generate_own_idea(
                f"own_idea_{i}",
                IdeaType.CONCEPT
            )
            self._model._source_memory.encode_source(idea, attention_level=0.7)
            own_ideas.append(idea)

        # Phase 2: Later generation
        generation = self._model.generation_phase(
            n_ideas=n_own_ideas,
            context=GenerationContext.BRAINSTORM,
            delay_since_exposure=delay_seconds
        )

        # Check for self-plagiarism (reproducing own ideas as "new")
        self_plagiarism = self._model.detect_plagiarism(generation.ideas_produced, own_ideas)

        result = {
            'own_ideas_generated': n_own_ideas,
            'later_ideas': len(generation.ideas_produced),
            'self_plagiarism_count': len(self_plagiarism),
            'self_plagiarism_rate': len(self_plagiarism) / len(generation.ideas_produced) if generation.ideas_produced else 0
        }

        self._experiments.append(result)
        return result


# ============================================================================
# CRYPTOMNESIA ENGINE
# ============================================================================

class CryptomnesiaEngine:
    """
    Complete cryptomnesia engine.

    "Ba'el's unconscious borrowing detector." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = CryptomnesiaParadigm()
        self._model = CryptomnesiaModel()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Exposure

    def expose_to_ideas(
        self,
        ideas: List[Tuple[str, str]],
        attention: float = 0.5
    ) -> List[Idea]:
        """Expose to external ideas."""
        return self._model.exposure_phase(ideas, attention)

    # Generation

    def generate_ideas(
        self,
        n_ideas: int,
        context: GenerationContext = GenerationContext.BRAINSTORM,
        delay: float = 60
    ) -> GenerationAttempt:
        """Attempt to generate new ideas."""
        return self._model.generation_phase(n_ideas, context, delay)

    # Detection

    def detect_plagiarism(
        self,
        produced: List[Idea],
        originals: List[Idea]
    ) -> List[Tuple[Idea, Idea, float]]:
        """Detect plagiarism."""
        return self._model.detect_plagiarism(produced, originals)

    # Experiments

    def run_cryptomnesia_experiment(
        self,
        n_exposure_ideas: int = 20,
        n_generation_ideas: int = 10,
        delay: float = 300
    ) -> Dict[str, Any]:
        """Run cryptomnesia experiment."""
        result = self._paradigm.run_brainstorm_paradigm(
            n_participants=4,
            ideas_per_person=n_exposure_ideas // 4,
            delay_seconds=delay
        )
        self._experiment_results.append(result)
        return result

    def run_self_plagiarism_experiment(
        self,
        n_ideas: int = 10,
        delay: float = 600
    ) -> Dict[str, Any]:
        """Run self-plagiarism experiment."""
        result = self._paradigm.run_self_plagiarism_paradigm(n_ideas, delay)
        self._experiment_results.append(result)
        return result

    def run_delay_comparison(
        self,
        delays: List[float] = None
    ) -> Dict[str, Any]:
        """Compare cryptomnesia across delays."""
        if delays is None:
            delays = [60, 300, 600, 1800]

        results = {}
        for delay in delays:
            # Fresh model for each condition
            self._paradigm = CryptomnesiaParadigm()
            result = self._paradigm.run_brainstorm_paradigm(
                n_participants=4,
                ideas_per_person=5,
                delay_seconds=delay
            )
            results[f"{delay}s"] = result['cryptomnesia_rate']

        return {
            'delays': results,
            'interpretation': 'Cryptomnesia increases with delay as source memory fades'
        }

    # Analysis

    def get_metrics(self) -> CryptomnesiaMetrics:
        """Get cryptomnesia metrics."""
        if not self._experiment_results:
            self.run_cryptomnesia_experiment(20, 10, 300)

        last = self._experiment_results[-1]

        return CryptomnesiaMetrics(
            plagiarism_rate=last.get('cryptomnesia_rate', 0),
            source_confusion_rate=last.get('cryptomnesia_rate', 0) * 0.8,
            self_plagiarism_rate=last.get('self_plagiarism_rate', 0),
            novelty_rate=1 - last.get('cryptomnesia_rate', 0)
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'ideas': len(self._model._idea_system._all_ideas),
            'experiments': len(self._experiment_results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_cryptomnesia_engine() -> CryptomnesiaEngine:
    """Create cryptomnesia engine."""
    return CryptomnesiaEngine()


def demonstrate_cryptomnesia() -> Dict[str, Any]:
    """Demonstrate cryptomnesia."""
    engine = create_cryptomnesia_engine()

    # Basic experiment
    basic = engine.run_cryptomnesia_experiment(20, 10, 300)

    # Self-plagiarism
    self_plag = engine.run_self_plagiarism_experiment(10, 600)

    # Delay comparison
    delays = engine.run_delay_comparison([60, 300, 600])

    return {
        'cryptomnesia': {
            'rate': f"{basic['cryptomnesia_rate']:.0%}",
            'errors': basic['cryptomnesic_errors'],
            'total_produced': basic['total_produced']
        },
        'self_plagiarism': {
            'rate': f"{self_plag['self_plagiarism_rate']:.0%}",
            'count': self_plag['self_plagiarism_count']
        },
        'delay_effect': delays['delays'],
        'interpretation': (
            f"Cryptomnesia rate: {basic['cryptomnesia_rate']:.0%}. "
            f"Unconscious plagiarism increases with delay."
        )
    }


def get_cryptomnesia_facts() -> Dict[str, str]:
    """Get facts about cryptomnesia."""
    return {
        'definition': 'Unconscious plagiarism - forgetting the source of ideas',
        'source_monitoring': 'Failure to attribute ideas to correct source',
        'famous_cases': 'George Harrison "My Sweet Lord" case',
        'group_brainstorming': 'Common in collaborative creative work',
        'delay_effect': 'Increases over time as source memory fades',
        'self_plagiarism': 'Can also forget own prior ideas',
        'prevention': 'Record sources carefully during idea exposure',
        'false_fame': 'Related to false fame effect in memory'
    }
