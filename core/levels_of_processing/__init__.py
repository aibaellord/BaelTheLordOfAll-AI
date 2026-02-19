"""
BAEL Levels of Processing Engine
=================================

Craik & Lockhart depth of processing.
Shallow vs deep encoding effects.

"Ba'el processes at all depths." — Ba'el
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

logger = logging.getLogger("BAEL.LevelsOfProcessing")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ProcessingLevel(Enum):
    """Levels of processing."""
    STRUCTURAL = 1      # Physical features (font, case)
    PHONEMIC = 2        # Sound-based processing
    SEMANTIC = 3        # Meaning-based processing
    ELABORATIVE = 4     # Deep elaboration
    SELF_REFERENCE = 5  # Relation to self


class OrientingTask(Enum):
    """Types of orienting tasks."""
    CASE = auto()           # Is it uppercase?
    FONT = auto()           # What font?
    RHYME = auto()          # Does it rhyme with X?
    SYLLABLES = auto()      # How many syllables?
    CATEGORY = auto()       # Is it a type of X?
    SYNONYM = auto()        # Is it similar to X?
    SENTENCE = auto()       # Does it fit in sentence?
    SELF = auto()           # Does it describe you?


class EncodingType(Enum):
    """Encoding types."""
    INCIDENTAL = auto()    # No intention to learn
    INTENTIONAL = auto()   # Intention to learn


@dataclass
class ProcessingTask:
    """
    A processing task.
    """
    id: str
    task_type: OrientingTask
    level: ProcessingLevel
    question: str
    word: str
    correct_answer: bool


@dataclass
class TaskResponse:
    """
    Response to orienting task.
    """
    task_id: str
    response: bool
    correct: bool
    response_time: float


@dataclass
class MemoryTrace:
    """
    Memory trace with depth.
    """
    word: str
    processing_level: ProcessingLevel
    depth_score: float
    elaborations: List[str]
    distinctiveness: float
    creation_time: float


@dataclass
class TestResult:
    """
    Memory test result.
    """
    word: str
    processing_level: ProcessingLevel
    recalled: bool
    recognized: bool
    confidence: float
    latency: float


@dataclass
class LOPMetrics:
    """
    Levels of processing metrics.
    """
    structural_recall: float
    phonemic_recall: float
    semantic_recall: float
    self_reference_recall: float
    depth_correlation: float


# ============================================================================
# TASK GENERATOR
# ============================================================================

class TaskGenerator:
    """
    Generate orienting tasks.

    "Ba'el creates processing tasks." — Ba'el
    """

    def __init__(self):
        """Initialize generator."""
        self._task_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._task_counter += 1
        return f"task_{self._task_counter}"

    def create_structural(
        self,
        word: str
    ) -> ProcessingTask:
        """Create structural processing task."""
        is_upper = word.isupper()
        question = "Is this word in UPPERCASE?"

        return ProcessingTask(
            id=self._generate_id(),
            task_type=OrientingTask.CASE,
            level=ProcessingLevel.STRUCTURAL,
            question=question,
            word=word.upper() if random.random() < 0.5 else word.lower(),
            correct_answer=is_upper
        )

    def create_phonemic(
        self,
        word: str,
        rhyme_word: str
    ) -> ProcessingTask:
        """Create phonemic processing task."""
        # Simple rhyme check (last 2 letters)
        rhymes = word[-2:].lower() == rhyme_word[-2:].lower()
        question = f"Does this word rhyme with '{rhyme_word}'?"

        return ProcessingTask(
            id=self._generate_id(),
            task_type=OrientingTask.RHYME,
            level=ProcessingLevel.PHONEMIC,
            question=question,
            word=word,
            correct_answer=rhymes
        )

    def create_semantic(
        self,
        word: str,
        category: str,
        is_member: bool
    ) -> ProcessingTask:
        """Create semantic processing task."""
        question = f"Is this a type of {category}?"

        return ProcessingTask(
            id=self._generate_id(),
            task_type=OrientingTask.CATEGORY,
            level=ProcessingLevel.SEMANTIC,
            question=question,
            word=word,
            correct_answer=is_member
        )

    def create_sentence(
        self,
        word: str,
        sentence_frame: str,
        fits: bool
    ) -> ProcessingTask:
        """Create sentence completion task."""
        question = f"Does '{word}' fit in: '{sentence_frame}'?"

        return ProcessingTask(
            id=self._generate_id(),
            task_type=OrientingTask.SENTENCE,
            level=ProcessingLevel.ELABORATIVE,
            question=question,
            word=word,
            correct_answer=fits
        )

    def create_self_reference(
        self,
        word: str
    ) -> ProcessingTask:
        """Create self-reference task."""
        question = f"Does this word describe you?"

        return ProcessingTask(
            id=self._generate_id(),
            task_type=OrientingTask.SELF,
            level=ProcessingLevel.SELF_REFERENCE,
            question=question,
            word=word,
            correct_answer=True  # User decides
        )

    def get_depth_score(
        self,
        level: ProcessingLevel
    ) -> float:
        """Get depth score for processing level."""
        depth_map = {
            ProcessingLevel.STRUCTURAL: 0.2,
            ProcessingLevel.PHONEMIC: 0.4,
            ProcessingLevel.SEMANTIC: 0.7,
            ProcessingLevel.ELABORATIVE: 0.85,
            ProcessingLevel.SELF_REFERENCE: 1.0
        }
        return depth_map.get(level, 0.5)


# ============================================================================
# PROCESSOR
# ============================================================================

class DepthProcessor:
    """
    Process items at different depths.

    "Ba'el processes deeply." — Ba'el
    """

    def __init__(self):
        """Initialize processor."""
        self._lock = threading.RLock()

    def process(
        self,
        task: ProcessingTask,
        response: bool
    ) -> TaskResponse:
        """Process a task and record response."""
        correct = (response == task.correct_answer)

        # Deeper processing takes longer
        base_time = {
            ProcessingLevel.STRUCTURAL: 0.5,
            ProcessingLevel.PHONEMIC: 1.0,
            ProcessingLevel.SEMANTIC: 1.5,
            ProcessingLevel.ELABORATIVE: 2.0,
            ProcessingLevel.SELF_REFERENCE: 2.5
        }

        response_time = base_time.get(task.level, 1.0) + random.uniform(0, 0.5)

        return TaskResponse(
            task_id=task.id,
            response=response,
            correct=correct,
            response_time=response_time
        )

    def generate_elaborations(
        self,
        word: str,
        level: ProcessingLevel
    ) -> List[str]:
        """Generate elaborations based on processing level."""
        elaborations = []

        if level == ProcessingLevel.STRUCTURAL:
            elaborations.append(f"length: {len(word)}")

        elif level == ProcessingLevel.PHONEMIC:
            elaborations.append(f"starts with: {word[0]}")
            elaborations.append(f"ends with: {word[-1]}")

        elif level == ProcessingLevel.SEMANTIC:
            elaborations.append(f"meaning related")
            elaborations.append(f"category member")

        elif level == ProcessingLevel.ELABORATIVE:
            elaborations.append(f"sentence context")
            elaborations.append(f"rich associations")

        elif level == ProcessingLevel.SELF_REFERENCE:
            elaborations.append(f"personal relevance")
            elaborations.append(f"self-schema activation")

        return elaborations

    def calculate_distinctiveness(
        self,
        level: ProcessingLevel,
        response_correct: bool
    ) -> float:
        """Calculate trace distinctiveness."""
        base = {
            ProcessingLevel.STRUCTURAL: 0.2,
            ProcessingLevel.PHONEMIC: 0.3,
            ProcessingLevel.SEMANTIC: 0.6,
            ProcessingLevel.ELABORATIVE: 0.8,
            ProcessingLevel.SELF_REFERENCE: 0.9
        }

        score = base.get(level, 0.5)

        # Yes responses create more distinctive traces
        if response_correct:
            score += 0.1

        return min(1.0, score)


# ============================================================================
# MEMORY SYSTEM
# ============================================================================

class LOPMemorySystem:
    """
    Memory system with depth effects.

    "Ba'el's depth-dependent memory." — Ba'el
    """

    def __init__(self):
        """Initialize memory system."""
        self._traces: Dict[str, MemoryTrace] = {}
        self._lock = threading.RLock()

    def encode(
        self,
        word: str,
        level: ProcessingLevel,
        depth_score: float,
        elaborations: List[str],
        distinctiveness: float
    ) -> MemoryTrace:
        """Encode a word with depth information."""
        trace = MemoryTrace(
            word=word,
            processing_level=level,
            depth_score=depth_score,
            elaborations=elaborations,
            distinctiveness=distinctiveness,
            creation_time=time.time()
        )

        self._traces[word] = trace
        return trace

    def retrieve(
        self,
        word: str
    ) -> Tuple[bool, Optional[MemoryTrace]]:
        """Attempt to retrieve a word."""
        trace = self._traces.get(word)

        if not trace:
            return False, None

        # Retrieval probability based on depth and distinctiveness
        retrieval_prob = (
            trace.depth_score * 0.5 +
            trace.distinctiveness * 0.3 +
            len(trace.elaborations) * 0.05
        )

        success = random.random() < retrieval_prob
        return success, trace

    def recognize(
        self,
        word: str
    ) -> Tuple[bool, float]:
        """Recognition test."""
        trace = self._traces.get(word)

        if not trace:
            # False alarm possible
            return random.random() < 0.1, 0.2

        # Recognition easier than recall
        recognition_prob = min(0.95, (
            trace.depth_score * 0.4 +
            trace.distinctiveness * 0.4 +
            0.2  # Base recognition advantage
        ))

        success = random.random() < recognition_prob
        confidence = trace.depth_score * 0.8 + random.uniform(0, 0.2)

        return success, confidence

    def decay(
        self,
        rate: float = 0.1
    ) -> None:
        """Apply decay to traces."""
        for trace in self._traces.values():
            # Deeper traces decay slower
            effective_rate = rate * (1 - trace.depth_score * 0.5)
            trace.depth_score = max(0.01, trace.depth_score - effective_rate)


# ============================================================================
# LEVELS OF PROCESSING ENGINE
# ============================================================================

class LevelsOfProcessingEngine:
    """
    Complete levels of processing engine.

    "Ba'el's depth of processing system." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._generator = TaskGenerator()
        self._processor = DepthProcessor()
        self._memory = LOPMemorySystem()

        self._tasks: Dict[str, ProcessingTask] = {}
        self._responses: List[TaskResponse] = []
        self._test_results: List[TestResult] = []

        self._lock = threading.RLock()

    # Task creation

    def create_task(
        self,
        word: str,
        level: ProcessingLevel,
        **kwargs
    ) -> ProcessingTask:
        """Create orienting task at specified level."""
        if level == ProcessingLevel.STRUCTURAL:
            task = self._generator.create_structural(word)

        elif level == ProcessingLevel.PHONEMIC:
            rhyme_word = kwargs.get('rhyme_word', 'cat')
            task = self._generator.create_phonemic(word, rhyme_word)

        elif level == ProcessingLevel.SEMANTIC:
            category = kwargs.get('category', 'animal')
            is_member = kwargs.get('is_member', True)
            task = self._generator.create_semantic(word, category, is_member)

        elif level == ProcessingLevel.ELABORATIVE:
            sentence = kwargs.get('sentence', 'The ___ is big.')
            fits = kwargs.get('fits', True)
            task = self._generator.create_sentence(word, sentence, fits)

        elif level == ProcessingLevel.SELF_REFERENCE:
            task = self._generator.create_self_reference(word)

        else:
            task = self._generator.create_structural(word)

        self._tasks[task.id] = task
        return task

    # Study phase

    def study(
        self,
        task: ProcessingTask,
        response: bool
    ) -> MemoryTrace:
        """Study word via orienting task."""
        # Process the task
        task_response = self._processor.process(task, response)
        self._responses.append(task_response)

        # Get depth and elaborations
        depth_score = self._generator.get_depth_score(task.level)
        elaborations = self._processor.generate_elaborations(task.word, task.level)
        distinctiveness = self._processor.calculate_distinctiveness(
            task.level, task_response.correct
        )

        # Encode in memory
        trace = self._memory.encode(
            task.word,
            task.level,
            depth_score,
            elaborations,
            distinctiveness
        )

        return trace

    # Test phase

    def test_recall(
        self,
        word: str
    ) -> TestResult:
        """Test free recall."""
        success, trace = self._memory.retrieve(word)

        result = TestResult(
            word=word,
            processing_level=trace.processing_level if trace else ProcessingLevel.STRUCTURAL,
            recalled=success,
            recognized=False,
            confidence=trace.depth_score if trace else 0.0,
            latency=random.uniform(1, 3)
        )

        self._test_results.append(result)
        return result

    def test_recognition(
        self,
        word: str
    ) -> TestResult:
        """Test recognition."""
        success, confidence = self._memory.recognize(word)

        trace = self._memory._traces.get(word)

        result = TestResult(
            word=word,
            processing_level=trace.processing_level if trace else ProcessingLevel.STRUCTURAL,
            recalled=False,
            recognized=success,
            confidence=confidence,
            latency=random.uniform(0.5, 1.5)
        )

        self._test_results.append(result)
        return result

    # Delay simulation

    def simulate_delay(
        self,
        hours: float = 1.0
    ) -> None:
        """Simulate retention interval."""
        decay_rate = 0.05 * hours
        self._memory.decay(decay_rate)

    # Analysis

    def get_recall_by_level(self) -> Dict[ProcessingLevel, float]:
        """Get recall rate by processing level."""
        level_results = defaultdict(list)

        for result in self._test_results:
            if result.recalled or result.recognized:
                level_results[result.processing_level].append(1)
            else:
                level_results[result.processing_level].append(0)

        rates = {}
        for level, results in level_results.items():
            rates[level] = sum(results) / len(results) if results else 0.0

        return rates

    def calculate_depth_correlation(self) -> float:
        """Calculate correlation between depth and recall."""
        if not self._test_results:
            return 0.0

        depths = []
        successes = []

        for result in self._test_results:
            depths.append(result.processing_level.value)
            successes.append(1 if result.recalled or result.recognized else 0)

        if len(depths) < 2:
            return 0.0

        # Simple correlation
        mean_d = sum(depths) / len(depths)
        mean_s = sum(successes) / len(successes)

        numerator = sum((d - mean_d) * (s - mean_s) for d, s in zip(depths, successes))
        denom_d = math.sqrt(sum((d - mean_d) ** 2 for d in depths))
        denom_s = math.sqrt(sum((s - mean_s) ** 2 for s in successes))

        if denom_d == 0 or denom_s == 0:
            return 0.0

        return numerator / (denom_d * denom_s)

    # Metrics

    def get_metrics(self) -> LOPMetrics:
        """Get LOP metrics."""
        rates = self.get_recall_by_level()

        return LOPMetrics(
            structural_recall=rates.get(ProcessingLevel.STRUCTURAL, 0.0),
            phonemic_recall=rates.get(ProcessingLevel.PHONEMIC, 0.0),
            semantic_recall=rates.get(ProcessingLevel.SEMANTIC, 0.0),
            self_reference_recall=rates.get(ProcessingLevel.SELF_REFERENCE, 0.0),
            depth_correlation=self.calculate_depth_correlation()
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'tasks': len(self._tasks),
            'responses': len(self._responses),
            'test_results': len(self._test_results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_levels_of_processing_engine() -> LevelsOfProcessingEngine:
    """Create LOP engine."""
    return LevelsOfProcessingEngine()


def demonstrate_depth_effect() -> Dict[str, Any]:
    """Demonstrate levels of processing effect."""
    engine = create_levels_of_processing_engine()

    words = ["apple", "table", "music", "garden", "river"]

    # Study at different levels
    for i, word in enumerate(words):
        level = list(ProcessingLevel)[i % len(ProcessingLevel)]

        task = engine.create_task(
            word,
            level,
            category="fruit" if word == "apple" else "object",
            is_member=True
        )

        engine.study(task, response=True)

    # Test recall
    for word in words:
        engine.test_recall(word)

    metrics = engine.get_metrics()

    return {
        'structural_recall': metrics.structural_recall,
        'phonemic_recall': metrics.phonemic_recall,
        'semantic_recall': metrics.semantic_recall,
        'self_reference_recall': metrics.self_reference_recall,
        'depth_correlation': metrics.depth_correlation,
        'interpretation': (
            'Deeper processing leads to better memory'
            if metrics.depth_correlation > 0.3
            else 'Depth effect observed'
        )
    }


def get_lop_facts() -> Dict[str, str]:
    """Get facts about levels of processing."""
    return {
        'craik_lockhart_1972': 'Original levels of processing framework',
        'depth_hypothesis': 'Deeper processing leads to stronger memory traces',
        'maintenance': 'Simple rehearsal (maintenance) is shallow',
        'elaborative': 'Elaborative processing is deep and effective',
        'self_reference': 'Self-reference is the deepest processing level',
        'transfer_appropriate': 'Memory depends on encoding-test match',
        'criticism': 'Circular definition of depth criticized',
        'distinctiveness': 'Distinctiveness also contributes to memory'
    }
