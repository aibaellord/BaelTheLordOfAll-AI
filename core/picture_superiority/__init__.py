"""
BAEL Picture Superiority Engine
=================================

Images are remembered better than words.
Dual coding theory.

"Ba'el sees to remember." — Ba'el
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
import copy

logger = logging.getLogger("BAEL.PictureSuperiority")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class StimulusType(Enum):
    """Types of stimuli."""
    WORD = auto()
    PICTURE = auto()
    WORD_AND_PICTURE = auto()


class CodeType(Enum):
    """Types of mental codes (Paivio)."""
    VERBAL = auto()      # Linguistic representation
    IMAGINAL = auto()    # Visual/imagery representation


class PresentationType(Enum):
    """How stimulus is presented."""
    VISUAL = auto()
    AUDITORY = auto()
    TACTILE = auto()


@dataclass
class Stimulus:
    """
    A stimulus item.
    """
    id: str
    concept: str
    stimulus_type: StimulusType
    presentation_type: PresentationType
    imageability: float  # 0-1, how easily imagined
    concreteness: float  # 0-1, how concrete vs abstract


@dataclass
class DualCode:
    """
    Dual coding representation.
    """
    concept: str
    verbal_code: Optional[str]
    imaginal_code: Optional[str]
    verbal_strength: float
    imaginal_strength: float
    referential_connection: float  # Link between codes


@dataclass
class EncodedItem:
    """
    An encoded memory item.
    """
    stimulus_id: str
    concept: str
    stimulus_type: StimulusType
    dual_code: DualCode
    trace_strength: float
    distinctiveness: float


@dataclass
class RecallResult:
    """
    Result of recall attempt.
    """
    stimulus_id: str
    stimulus_type: StimulusType
    recalled: bool
    confidence: float
    codes_used: List[CodeType]


@dataclass
class PictureSuperiorityMetrics:
    """
    Picture superiority metrics.
    """
    picture_recall: float
    word_recall: float
    superiority_effect: float
    dual_code_advantage: float


# ============================================================================
# DUAL CODING THEORY
# ============================================================================

class DualCodingSystem:
    """
    Paivio's Dual Coding Theory.

    "Ba'el's dual representations." — Ba'el
    """

    def __init__(self):
        """Initialize dual coding system."""
        # Verbal and imaginal systems
        self._verbal_codes: Dict[str, str] = {}
        self._imaginal_codes: Dict[str, str] = {}

        # Referential connections between systems
        self._referential_links: Dict[str, float] = {}

        self._lock = threading.RLock()

    def encode_stimulus(
        self,
        stimulus: Stimulus
    ) -> DualCode:
        """Encode stimulus into dual codes."""
        concept = stimulus.concept

        # Verbal code strength
        if stimulus.stimulus_type == StimulusType.WORD:
            verbal_strength = 0.9
        elif stimulus.stimulus_type == StimulusType.PICTURE:
            verbal_strength = 0.4  # Pictures can elicit verbal labels
        else:  # WORD_AND_PICTURE
            verbal_strength = 1.0

        # Imaginal code strength
        if stimulus.stimulus_type == StimulusType.PICTURE:
            imaginal_strength = 0.9
        elif stimulus.stimulus_type == StimulusType.WORD:
            # Words can evoke images, depends on imageability
            imaginal_strength = 0.3 + stimulus.imageability * 0.4
        else:  # WORD_AND_PICTURE
            imaginal_strength = 1.0

        # Store codes
        if verbal_strength > 0.3:
            self._verbal_codes[concept] = f"verbal_{concept}"

        if imaginal_strength > 0.3:
            self._imaginal_codes[concept] = f"imaginal_{concept}"

        # Referential connection
        referential = min(verbal_strength, imaginal_strength) * 0.8
        self._referential_links[concept] = referential

        return DualCode(
            concept=concept,
            verbal_code=self._verbal_codes.get(concept),
            imaginal_code=self._imaginal_codes.get(concept),
            verbal_strength=verbal_strength,
            imaginal_strength=imaginal_strength,
            referential_connection=referential
        )

    def retrieve_codes(
        self,
        concept: str
    ) -> Optional[DualCode]:
        """Retrieve dual codes for concept."""
        verbal = self._verbal_codes.get(concept)
        imaginal = self._imaginal_codes.get(concept)
        referential = self._referential_links.get(concept, 0)

        if not verbal and not imaginal:
            return None

        return DualCode(
            concept=concept,
            verbal_code=verbal,
            imaginal_code=imaginal,
            verbal_strength=0.8 if verbal else 0,
            imaginal_strength=0.8 if imaginal else 0,
            referential_connection=referential
        )


# ============================================================================
# MEMORY MODEL
# ============================================================================

class PictureSuperiorityMemory:
    """
    Memory model incorporating picture superiority.

    "Ba'el's visual memory advantage." — Ba'el
    """

    def __init__(self):
        """Initialize memory."""
        self._dual_coding = DualCodingSystem()
        self._encoded: Dict[str, EncodedItem] = {}

        # Picture superiority parameters
        self._picture_bonus = 0.25       # Memory advantage for pictures
        self._dual_code_bonus = 0.15     # Extra advantage for dual coding
        self._distinctiveness_bonus = 0.1

        self._lock = threading.RLock()

    def encode(
        self,
        stimulus: Stimulus
    ) -> EncodedItem:
        """Encode stimulus into memory."""
        # Get dual codes
        dual_code = self._dual_coding.encode_stimulus(stimulus)

        # Base encoding strength
        base_strength = 0.5

        # Picture superiority effect
        if stimulus.stimulus_type == StimulusType.PICTURE:
            base_strength += self._picture_bonus

            # Pictures are more distinctive
            distinctiveness = 0.7 + random.gauss(0, 0.1)

        elif stimulus.stimulus_type == StimulusType.WORD_AND_PICTURE:
            # Maximum encoding: both codes strong
            base_strength += self._picture_bonus + self._dual_code_bonus
            distinctiveness = 0.8 + random.gauss(0, 0.1)

        else:  # WORD
            distinctiveness = 0.4 + random.gauss(0, 0.1)

            # High imageability words get some benefit
            if stimulus.imageability > 0.7:
                base_strength += self._picture_bonus * 0.3
                distinctiveness += 0.1

        # Dual code advantage
        if dual_code.verbal_code and dual_code.imaginal_code:
            base_strength += self._dual_code_bonus

        trace_strength = min(1.0, max(0.1, base_strength + random.gauss(0, 0.05)))

        encoded = EncodedItem(
            stimulus_id=stimulus.id,
            concept=stimulus.concept,
            stimulus_type=stimulus.stimulus_type,
            dual_code=dual_code,
            trace_strength=trace_strength,
            distinctiveness=max(0, min(1, distinctiveness))
        )

        self._encoded[stimulus.id] = encoded
        return encoded

    def retrieve(
        self,
        stimulus_id: str,
        delay_minutes: float = 0
    ) -> Optional[RecallResult]:
        """Attempt retrieval."""
        encoded = self._encoded.get(stimulus_id)
        if not encoded:
            return None

        # Apply forgetting
        decay = math.exp(-delay_minutes / 30)

        # Multiple retrieval routes
        retrieval_strength = 0.0
        codes_used = []

        # Try verbal route
        if encoded.dual_code.verbal_code:
            verbal_prob = encoded.dual_code.verbal_strength * decay
            if random.random() < verbal_prob:
                retrieval_strength += 0.4
                codes_used.append(CodeType.VERBAL)

        # Try imaginal route
        if encoded.dual_code.imaginal_code:
            imaginal_prob = encoded.dual_code.imaginal_strength * decay
            if random.random() < imaginal_prob:
                retrieval_strength += 0.5  # Images are more memorable
                codes_used.append(CodeType.IMAGINAL)

        # Cross-referential boost
        if codes_used and encoded.dual_code.referential_connection > 0.5:
            retrieval_strength += 0.15

        # Distinctiveness boost
        retrieval_strength += encoded.distinctiveness * 0.2

        # Overall trace strength contribution
        retrieval_strength = retrieval_strength * encoded.trace_strength

        recalled = random.random() < retrieval_strength

        return RecallResult(
            stimulus_id=stimulus_id,
            stimulus_type=encoded.stimulus_type,
            recalled=recalled,
            confidence=retrieval_strength,
            codes_used=codes_used
        )

    def get_encoded(
        self,
        stimulus_id: str
    ) -> Optional[EncodedItem]:
        """Get encoded item."""
        return self._encoded.get(stimulus_id)


# ============================================================================
# EXPERIMENTAL PARADIGM
# ============================================================================

class PictureSuperiorityParadigm:
    """
    Picture superiority experimental paradigm.

    "Ba'el's picture experiment." — Ba'el
    """

    def __init__(
        self,
        memory: PictureSuperiorityMemory
    ):
        """Initialize paradigm."""
        self._memory = memory

        self._stimuli: Dict[str, Stimulus] = {}

        self._item_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._item_counter += 1
        return f"stim_{self._item_counter}"

    def create_stimuli(
        self,
        concepts: List[str],
        stimulus_type: StimulusType,
        imageability: float = 0.5
    ) -> List[Stimulus]:
        """Create stimuli from concepts."""
        stimuli = []

        for concept in concepts:
            stim = Stimulus(
                id=self._generate_id(),
                concept=concept,
                stimulus_type=stimulus_type,
                presentation_type=PresentationType.VISUAL,
                imageability=imageability,
                concreteness=imageability
            )
            self._stimuli[stim.id] = stim
            stimuli.append(stim)

        return stimuli

    def study_phase(
        self,
        stimuli: List[Stimulus]
    ) -> List[EncodedItem]:
        """Run study phase."""
        encoded = []
        for stim in stimuli:
            enc = self._memory.encode(stim)
            encoded.append(enc)
        return encoded

    def test_phase(
        self,
        stimuli: List[Stimulus],
        delay_minutes: float = 0
    ) -> List[RecallResult]:
        """Run test phase."""
        results = []
        for stim in stimuli:
            result = self._memory.retrieve(stim.id, delay_minutes)
            if result:
                results.append(result)
        return results

    def run_experiment(
        self,
        n_per_condition: int = 20,
        delay_minutes: float = 5
    ) -> Dict[str, Any]:
        """Run picture superiority experiment."""
        # Create word stimuli
        word_concepts = [f"word_concept_{i}" for i in range(n_per_condition)]
        word_stimuli = self.create_stimuli(word_concepts, StimulusType.WORD)

        # Create picture stimuli
        picture_concepts = [f"picture_concept_{i}" for i in range(n_per_condition)]
        picture_stimuli = self.create_stimuli(picture_concepts, StimulusType.PICTURE)

        # Study phase
        self.study_phase(word_stimuli)
        self.study_phase(picture_stimuli)

        # Test phase
        word_results = self.test_phase(word_stimuli, delay_minutes)
        picture_results = self.test_phase(picture_stimuli, delay_minutes)

        # Calculate recall rates
        word_recall = sum(1 for r in word_results if r.recalled) / len(word_results)
        picture_recall = sum(1 for r in picture_results if r.recalled) / len(picture_results)

        superiority_effect = picture_recall - word_recall

        # Analyze code usage
        word_imaginal = sum(1 for r in word_results if CodeType.IMAGINAL in r.codes_used)
        picture_verbal = sum(1 for r in picture_results if CodeType.VERBAL in r.codes_used)

        return {
            'word_recall': word_recall,
            'picture_recall': picture_recall,
            'superiority_effect': superiority_effect,
            'word_imaginal_use': word_imaginal / len(word_results) if word_results else 0,
            'picture_verbal_use': picture_verbal / len(picture_results) if picture_results else 0,
            'n_per_condition': n_per_condition
        }


# ============================================================================
# PICTURE SUPERIORITY ENGINE
# ============================================================================

class PictureSuperiorityEngine:
    """
    Complete picture superiority engine.

    "Ba'el's visual memory advantage." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._memory = PictureSuperiorityMemory()
        self._paradigm = PictureSuperiorityParadigm(self._memory)

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Encoding operations

    def encode_word(
        self,
        concept: str,
        imageability: float = 0.5
    ) -> EncodedItem:
        """Encode a word."""
        stim = Stimulus(
            id=f"word_{concept}",
            concept=concept,
            stimulus_type=StimulusType.WORD,
            presentation_type=PresentationType.VISUAL,
            imageability=imageability,
            concreteness=imageability
        )
        return self._memory.encode(stim)

    def encode_picture(
        self,
        concept: str
    ) -> EncodedItem:
        """Encode a picture."""
        stim = Stimulus(
            id=f"picture_{concept}",
            concept=concept,
            stimulus_type=StimulusType.PICTURE,
            presentation_type=PresentationType.VISUAL,
            imageability=0.9,
            concreteness=0.9
        )
        return self._memory.encode(stim)

    def encode_word_and_picture(
        self,
        concept: str
    ) -> EncodedItem:
        """Encode word + picture together."""
        stim = Stimulus(
            id=f"wordpic_{concept}",
            concept=concept,
            stimulus_type=StimulusType.WORD_AND_PICTURE,
            presentation_type=PresentationType.VISUAL,
            imageability=1.0,
            concreteness=1.0
        )
        return self._memory.encode(stim)

    # Retrieval

    def recall(
        self,
        stimulus_id: str,
        delay_minutes: float = 0
    ) -> Optional[RecallResult]:
        """Attempt recall."""
        return self._memory.retrieve(stimulus_id, delay_minutes)

    # Experiments

    def run_picture_superiority_experiment(
        self,
        n_per_condition: int = 20,
        delay_minutes: float = 5
    ) -> Dict[str, Any]:
        """Run picture superiority experiment."""
        result = self._paradigm.run_experiment(n_per_condition, delay_minutes)
        self._experiment_results.append(result)
        return result

    def run_imageability_experiment(
        self,
        n_words: int = 30,
        delay_minutes: float = 5
    ) -> Dict[str, Any]:
        """Test effect of word imageability."""
        # High imageability words
        high_concepts = [f"high_img_{i}" for i in range(n_words)]
        high_stimuli = self._paradigm.create_stimuli(
            high_concepts, StimulusType.WORD, imageability=0.9
        )

        # Low imageability words
        low_concepts = [f"low_img_{i}" for i in range(n_words)]
        low_stimuli = self._paradigm.create_stimuli(
            low_concepts, StimulusType.WORD, imageability=0.2
        )

        # Study
        self._paradigm.study_phase(high_stimuli)
        self._paradigm.study_phase(low_stimuli)

        # Test
        high_results = self._paradigm.test_phase(high_stimuli, delay_minutes)
        low_results = self._paradigm.test_phase(low_stimuli, delay_minutes)

        high_recall = sum(1 for r in high_results if r.recalled) / len(high_results)
        low_recall = sum(1 for r in low_results if r.recalled) / len(low_results)

        return {
            'high_imageability_recall': high_recall,
            'low_imageability_recall': low_recall,
            'imageability_effect': high_recall - low_recall
        }

    # Analysis

    def get_metrics(self) -> PictureSuperiorityMetrics:
        """Get picture superiority metrics."""
        if not self._experiment_results:
            self.run_picture_superiority_experiment(20, 5)

        last = self._experiment_results[-1]

        return PictureSuperiorityMetrics(
            picture_recall=last['picture_recall'],
            word_recall=last['word_recall'],
            superiority_effect=last['superiority_effect'],
            dual_code_advantage=last['picture_verbal_use']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'encoded_items': len(self._memory._encoded),
            'experiments': len(self._experiment_results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_picture_superiority_engine() -> PictureSuperiorityEngine:
    """Create picture superiority engine."""
    return PictureSuperiorityEngine()


def demonstrate_picture_superiority() -> Dict[str, Any]:
    """Demonstrate picture superiority."""
    engine = create_picture_superiority_engine()

    # Basic experiment
    basic = engine.run_picture_superiority_experiment(25, 5)

    # Imageability
    imageability = engine.run_imageability_experiment(20, 5)

    return {
        'picture_superiority': {
            'word_recall': f"{basic['word_recall']:.0%}",
            'picture_recall': f"{basic['picture_recall']:.0%}",
            'effect': f"{basic['superiority_effect']:.0%}"
        },
        'imageability_effect': {
            'high': f"{imageability['high_imageability_recall']:.0%}",
            'low': f"{imageability['low_imageability_recall']:.0%}",
            'effect': f"{imageability['imageability_effect']:.0%}"
        },
        'dual_coding': {
            'pictures_elicit_words': f"{basic['picture_verbal_use']:.0%}",
            'words_elicit_images': f"{basic['word_imaginal_use']:.0%}"
        },
        'interpretation': (
            f"Picture superiority: {basic['superiority_effect']:.0%}. "
            f"Pictures create dual codes and are more distinctive."
        )
    }


def get_picture_superiority_facts() -> Dict[str, str]:
    """Get facts about picture superiority."""
    return {
        'paivio_dct': "Paivio's Dual Coding Theory: verbal and imaginal systems",
        'picture_advantage': 'Pictures remembered 2x better than words',
        'dual_code': 'Pictures automatically evoke verbal labels',
        'distinctiveness': 'Pictures are more visually distinctive',
        'imageability': 'High-imageability words show intermediate effect',
        'concreteness': 'Concrete words also benefit from imagery',
        'referential_links': 'Cross-references between codes aid retrieval',
        'sensory_semantic': 'Proposed alternative to dual coding'
    }
