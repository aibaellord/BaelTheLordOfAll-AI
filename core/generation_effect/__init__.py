"""
BAEL Generation Effect Engine
==============================

Self-generated learning enhancement.
Slamecka & Graf generation effect.

"Ba'el learns through creation." — Ba'el
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

logger = logging.getLogger("BAEL.GenerationEffect")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class GenerationType(Enum):
    """Types of generation tasks."""
    COMPLETE = auto()       # Complete a word fragment
    ASSOCIATE = auto()      # Generate association
    SYNONYM = auto()        # Generate synonym
    RHYME = auto()          # Generate rhyming word
    CATEGORY = auto()       # Generate category member
    SENTENCE = auto()       # Generate sentence
    TRANSFORM = auto()      # Transform existing item


class EncodingType(Enum):
    """Encoding conditions."""
    READ = auto()           # Just read (control)
    GENERATE = auto()       # Self-generate


class CueType(Enum):
    """Types of generation cues."""
    FRAGMENT = auto()       # Word fragment (s_xt_nt)
    FIRST_LETTER = auto()   # First letter cue
    RHYME_CUE = auto()      # Rhyming word cue
    SEMANTIC_CUE = auto()   # Semantic/meaning cue
    CONTEXT_CUE = auto()    # Context/sentence cue


@dataclass
class StudyItem:
    """
    An item to study.
    """
    id: str
    target: str              # Target word/answer
    cue: str                 # Generation cue
    cue_type: CueType
    encoding: EncodingType
    rule: str                # Generation rule used


@dataclass
class GenerationAttempt:
    """
    A generation attempt.
    """
    item_id: str
    generated: str
    correct: bool
    latency: float
    difficulty: float


@dataclass
class MemoryTrace:
    """
    Memory trace for an item.
    """
    item_id: str
    encoding: EncodingType
    strength: float
    distinctiveness: float
    effort_invested: float
    elaborations: List[str]


@dataclass
class TestResult:
    """
    Result of a memory test.
    """
    item_id: str
    encoding: EncodingType
    recalled: bool
    response: Optional[str]
    latency: float


@dataclass
class GenerationMetrics:
    """
    Generation effect metrics.
    """
    read_recall_rate: float
    generate_recall_rate: float
    generation_advantage: float   # Generate - Read
    generation_accuracy: float    # Correct generations


# ============================================================================
# CUE GENERATOR
# ============================================================================

class CueGenerator:
    """
    Generate cues for generation tasks.

    "Ba'el creates generation cues." — Ba'el
    """

    def __init__(self):
        """Initialize generator."""
        self._lock = threading.RLock()

    def create_fragment(
        self,
        word: str,
        difficulty: float = 0.5
    ) -> str:
        """Create word fragment cue."""
        # Remove some letters based on difficulty
        chars = list(word)
        num_remove = int(len(word) * difficulty)

        # Keep first and last letter
        removable = list(range(1, len(word) - 1))
        random.shuffle(removable)

        for i in removable[:num_remove]:
            chars[i] = '_'

        return ''.join(chars)

    def create_first_letter(
        self,
        word: str
    ) -> str:
        """Create first letter cue."""
        return word[0] + '_' * (len(word) - 1)

    def create_rhyme_cue(
        self,
        word: str,
        rhymes: List[str]
    ) -> str:
        """Create rhyme cue."""
        if rhymes:
            return f"rhymes with {random.choice(rhymes)}"
        return f"rhymes with {word[-2:]}"

    def create_semantic_cue(
        self,
        word: str,
        category: str
    ) -> str:
        """Create semantic cue."""
        return f"{category}: starts with {word[0]}"

    def evaluate_difficulty(
        self,
        cue: str,
        target: str
    ) -> float:
        """Evaluate cue difficulty."""
        if not cue or not target:
            return 1.0

        # Count how much of target is visible
        visible = sum(1 for c in cue if c != '_' and c.isalpha())
        total = len(target)

        return 1.0 - (visible / max(1, total))


# ============================================================================
# GENERATION PROCESSOR
# ============================================================================

class GenerationProcessor:
    """
    Process generation attempts.

    "Ba'el evaluates generation." — Ba'el
    """

    def __init__(self):
        """Initialize processor."""
        self._lock = threading.RLock()

    def evaluate_response(
        self,
        target: str,
        response: str,
        cue_type: CueType
    ) -> Tuple[bool, float]:
        """Evaluate a generation response."""
        target_lower = target.lower().strip()
        response_lower = response.lower().strip()

        # Exact match
        if target_lower == response_lower:
            return True, 1.0

        # Partial credit for close matches
        if cue_type == CueType.FRAGMENT:
            # Check if response fits fragment pattern
            similarity = self._calculate_similarity(target_lower, response_lower)
            return False, similarity

        elif cue_type == CueType.RHYME_CUE:
            # Check if rhymes
            if target_lower[-2:] == response_lower[-2:]:
                return True, 0.8

        return False, 0.0

    def _calculate_similarity(
        self,
        s1: str,
        s2: str
    ) -> float:
        """Calculate string similarity."""
        if not s1 or not s2:
            return 0.0

        # Character overlap
        chars1 = set(s1)
        chars2 = set(s2)
        overlap = len(chars1 & chars2) / len(chars1 | chars2)

        # Length similarity
        len_sim = min(len(s1), len(s2)) / max(len(s1), len(s2))

        return 0.5 * overlap + 0.5 * len_sim

    def calculate_effort(
        self,
        difficulty: float,
        latency: float
    ) -> float:
        """Calculate cognitive effort invested."""
        # Higher difficulty and longer time = more effort
        return min(1.0, difficulty * 0.6 + (latency / 10.0) * 0.4)


# ============================================================================
# MEMORY ENCODER
# ============================================================================

class MemoryEncoder:
    """
    Encode items based on study condition.

    "Ba'el encodes with generation benefit." — Ba'el
    """

    def __init__(self):
        """Initialize encoder."""
        self._traces: Dict[str, MemoryTrace] = {}
        self._lock = threading.RLock()

    def encode_read(
        self,
        item: StudyItem
    ) -> MemoryTrace:
        """Encode via reading (passive)."""
        trace = MemoryTrace(
            item_id=item.id,
            encoding=EncodingType.READ,
            strength=0.5,
            distinctiveness=0.3,
            effort_invested=0.2,
            elaborations=[]
        )

        self._traces[item.id] = trace
        return trace

    def encode_generate(
        self,
        item: StudyItem,
        success: bool,
        effort: float
    ) -> MemoryTrace:
        """Encode via generation (active)."""
        # Generation provides:
        # 1. Stronger trace (more effort)
        # 2. More distinctive encoding
        # 3. Self-generated elaborations

        base_strength = 0.7 if success else 0.4
        strength_bonus = effort * 0.2

        trace = MemoryTrace(
            item_id=item.id,
            encoding=EncodingType.GENERATE,
            strength=min(1.0, base_strength + strength_bonus),
            distinctiveness=0.7 if success else 0.4,
            effort_invested=effort,
            elaborations=[item.rule, item.cue]
        )

        self._traces[item.id] = trace
        return trace

    def get_trace(
        self,
        item_id: str
    ) -> Optional[MemoryTrace]:
        """Get memory trace."""
        return self._traces.get(item_id)

    def decay_traces(
        self,
        rate: float = 0.1
    ) -> None:
        """Apply decay to all traces."""
        for trace in self._traces.values():
            trace.strength = max(0.01, trace.strength - rate)


# ============================================================================
# RETRIEVAL TESTER
# ============================================================================

class RetrievalTester:
    """
    Test memory retrieval.

    "Ba'el tests generation advantage." — Ba'el
    """

    def __init__(
        self,
        encoder: MemoryEncoder
    ):
        """Initialize tester."""
        self._encoder = encoder
        self._lock = threading.RLock()

    def test(
        self,
        item: StudyItem
    ) -> TestResult:
        """Test recall for an item."""
        trace = self._encoder.get_trace(item.id)

        if not trace:
            return TestResult(
                item_id=item.id,
                encoding=item.encoding,
                recalled=False,
                response=None,
                latency=0.0
            )

        # Recall probability based on trace
        recall_prob = (
            trace.strength * 0.5 +
            trace.distinctiveness * 0.3 +
            trace.effort_invested * 0.2
        )

        recalled = random.random() < recall_prob

        # Latency inversely related to strength
        base_latency = 2.0 - trace.strength
        latency = base_latency + random.uniform(0, 1)

        return TestResult(
            item_id=item.id,
            encoding=trace.encoding,
            recalled=recalled,
            response=item.target if recalled else None,
            latency=latency
        )

    def test_all(
        self,
        items: List[StudyItem]
    ) -> List[TestResult]:
        """Test all items."""
        return [self.test(item) for item in items]


# ============================================================================
# GENERATION EFFECT ENGINE
# ============================================================================

class GenerationEffectEngine:
    """
    Complete generation effect engine.

    "Ba'el's generation advantage system." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._cue_gen = CueGenerator()
        self._processor = GenerationProcessor()
        self._encoder = MemoryEncoder()
        self._tester = RetrievalTester(self._encoder)

        self._items: Dict[str, StudyItem] = {}
        self._attempts: List[GenerationAttempt] = []
        self._test_results: List[TestResult] = []

        self._item_counter = 0

        self._lock = threading.RLock()

    def _generate_item_id(self) -> str:
        self._item_counter += 1
        return f"item_{self._item_counter}"

    # Item creation

    def create_read_item(
        self,
        target: str
    ) -> StudyItem:
        """Create item for read condition."""
        item = StudyItem(
            id=self._generate_item_id(),
            target=target,
            cue=target,  # Full word visible
            cue_type=CueType.FRAGMENT,
            encoding=EncodingType.READ,
            rule="read"
        )

        self._items[item.id] = item
        return item

    def create_generate_item(
        self,
        target: str,
        cue_type: CueType = CueType.FRAGMENT,
        difficulty: float = 0.5
    ) -> StudyItem:
        """Create item for generate condition."""
        if cue_type == CueType.FRAGMENT:
            cue = self._cue_gen.create_fragment(target, difficulty)
            rule = "complete fragment"
        elif cue_type == CueType.FIRST_LETTER:
            cue = self._cue_gen.create_first_letter(target)
            rule = "first letter cue"
        else:
            cue = self._cue_gen.create_fragment(target, difficulty)
            rule = "generate"

        item = StudyItem(
            id=self._generate_item_id(),
            target=target,
            cue=cue,
            cue_type=cue_type,
            encoding=EncodingType.GENERATE,
            rule=rule
        )

        self._items[item.id] = item
        return item

    def create_paired_items(
        self,
        target: str,
        cue_type: CueType = CueType.FRAGMENT,
        difficulty: float = 0.5
    ) -> Tuple[StudyItem, StudyItem]:
        """Create matched read and generate items."""
        read = self.create_read_item(target)
        generate = self.create_generate_item(target, cue_type, difficulty)
        return read, generate

    # Study phase

    def study_read(
        self,
        item: StudyItem
    ) -> MemoryTrace:
        """Study by reading."""
        return self._encoder.encode_read(item)

    def study_generate(
        self,
        item: StudyItem,
        response: str,
        latency: float = 1.0
    ) -> Tuple[MemoryTrace, GenerationAttempt]:
        """Study by generating."""
        difficulty = self._cue_gen.evaluate_difficulty(item.cue, item.target)
        correct, score = self._processor.evaluate_response(
            item.target, response, item.cue_type
        )
        effort = self._processor.calculate_effort(difficulty, latency)

        attempt = GenerationAttempt(
            item_id=item.id,
            generated=response,
            correct=correct,
            latency=latency,
            difficulty=difficulty
        )

        self._attempts.append(attempt)

        trace = self._encoder.encode_generate(item, correct, effort)

        return trace, attempt

    # Test phase

    def test_recall(
        self,
        item: StudyItem
    ) -> TestResult:
        """Test recall of item."""
        result = self._tester.test(item)
        self._test_results.append(result)
        return result

    def test_all(self) -> List[TestResult]:
        """Test all items."""
        results = []
        for item in self._items.values():
            result = self.test_recall(item)
            results.append(result)
        return results

    # Decay simulation

    def simulate_delay(
        self,
        minutes: float = 30
    ) -> None:
        """Simulate retention interval."""
        decay_rate = 0.02 * (minutes / 30)
        self._encoder.decay_traces(decay_rate)

    # Analysis

    def get_generation_effect(self) -> float:
        """Calculate the generation effect size."""
        read_results = [r for r in self._test_results if r.encoding == EncodingType.READ]
        gen_results = [r for r in self._test_results if r.encoding == EncodingType.GENERATE]

        if not read_results or not gen_results:
            return 0.0

        read_rate = sum(1 for r in read_results if r.recalled) / len(read_results)
        gen_rate = sum(1 for r in gen_results if r.recalled) / len(gen_results)

        return gen_rate - read_rate

    # Metrics

    def get_metrics(self) -> GenerationMetrics:
        """Get generation effect metrics."""
        read_results = [r for r in self._test_results if r.encoding == EncodingType.READ]
        gen_results = [r for r in self._test_results if r.encoding == EncodingType.GENERATE]

        read_rate = (
            sum(1 for r in read_results if r.recalled) / len(read_results)
            if read_results else 0.0
        )
        gen_rate = (
            sum(1 for r in gen_results if r.recalled) / len(gen_results)
            if gen_results else 0.0
        )

        gen_accuracy = (
            sum(1 for a in self._attempts if a.correct) / len(self._attempts)
            if self._attempts else 0.0
        )

        return GenerationMetrics(
            read_recall_rate=read_rate,
            generate_recall_rate=gen_rate,
            generation_advantage=gen_rate - read_rate,
            generation_accuracy=gen_accuracy
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'items': len(self._items),
            'attempts': len(self._attempts),
            'test_results': len(self._test_results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_generation_effect_engine() -> GenerationEffectEngine:
    """Create generation effect engine."""
    return GenerationEffectEngine()


def demonstrate_generation_effect() -> Dict[str, Any]:
    """Demonstrate the generation effect."""
    engine = create_generation_effect_engine()

    words = ["memory", "learning", "cognition", "brain", "recall"]

    # Create paired items
    for word in words:
        read, generate = engine.create_paired_items(word, difficulty=0.4)

        # Study read condition
        engine.study_read(read)

        # Study generate condition (simulate correct generation)
        engine.study_generate(generate, word, latency=2.0)

    # Simulate delay
    engine.simulate_delay(minutes=30)

    # Test all
    results = engine.test_all()

    metrics = engine.get_metrics()

    return {
        'read_recall_rate': metrics.read_recall_rate,
        'generate_recall_rate': metrics.generate_recall_rate,
        'generation_advantage': metrics.generation_advantage,
        'interpretation': (
            'Generation leads to better memory'
            if metrics.generation_advantage > 0
            else 'No generation effect observed'
        )
    }


def get_generation_effect_facts() -> Dict[str, str]:
    """Get facts about generation effect."""
    return {
        'slamecka_graf_1978': 'Original demonstration of generation effect',
        'definition': 'Self-generated items are better remembered than read items',
        'mechanisms': 'Increased effort, elaboration, and distinctiveness',
        'conditions': 'Works best with meaningful generation rules',
        'cue_presence': 'Cue must be present at test for full effect',
        'semantic_memory': 'Generation activates semantic memory networks',
        'transfer_appropriate': 'Effect depends on encoding-test match',
        'educational': 'Active learning better than passive reading'
    }
