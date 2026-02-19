"""
BAEL Self-Reference Effect Engine
===================================

Enhanced memory for information processed in relation to self.
Rogers, Kuiper & Kirker's self-reference paradigm.

"Ba'el remembers what touches the self." — Ba'el
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

logger = logging.getLogger("BAEL.SelfReference")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ProcessingTask(Enum):
    """Types of processing tasks."""
    STRUCTURAL = auto()       # Physical features (e.g., uppercase?)
    PHONEMIC = auto()         # Sound features (e.g., rhymes?)
    SEMANTIC = auto()         # Meaning (e.g., synonym of?)
    SELF_REFERENCE = auto()   # Relates to self (e.g., describes me?)
    OTHER_REFERENCE = auto()  # Relates to someone else


class TraitValence(Enum):
    """Valence of trait words."""
    POSITIVE = auto()
    NEUTRAL = auto()
    NEGATIVE = auto()


class SelfSchemaType(Enum):
    """Types of self-schema domains."""
    TRAITS = auto()
    ROLES = auto()
    PHYSICAL = auto()
    ABILITIES = auto()
    VALUES = auto()


@dataclass
class TraitWord:
    """
    A trait word for processing.
    """
    id: str
    word: str
    valence: TraitValence
    self_descriptive: bool
    processing_task: ProcessingTask
    processing_depth: float


@dataclass
class EncodingResult:
    """
    Result of encoding a trait word.
    """
    word_id: str
    task: ProcessingTask
    response: bool
    response_time_ms: float
    encoding_strength: float


@dataclass
class RecallResult:
    """
    Result of recall test.
    """
    word_id: str
    recalled: bool
    source_correct: bool


@dataclass
class SelfReferenceMetrics:
    """
    Self-reference effect metrics.
    """
    structural_recall: float
    phonemic_recall: float
    semantic_recall: float
    self_reference_recall: float
    sre_effect: float


# ============================================================================
# SELF-SCHEMA MODEL
# ============================================================================

class SelfSchemaModel:
    """
    Model of self-schema and self-referential processing.

    "Ba'el's self-knowledge structure." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Self-schema content
        self._self_traits: Set[str] = set([
            'intelligent', 'kind', 'hardworking', 'creative',
            'honest', 'curious', 'patient', 'determined'
        ])

        # Processing depth parameters
        self._structural_depth = 0.2
        self._phonemic_depth = 0.4
        self._semantic_depth = 0.6
        self._self_reference_depth = 0.9
        self._other_reference_depth = 0.7

        # Elaboration bonus
        self._self_elaboration = 0.25
        self._organization_bonus = 0.15

        self._lock = threading.RLock()

    def get_processing_depth(
        self,
        task: ProcessingTask
    ) -> float:
        """Get processing depth for a task."""
        if task == ProcessingTask.STRUCTURAL:
            return self._structural_depth
        elif task == ProcessingTask.PHONEMIC:
            return self._phonemic_depth
        elif task == ProcessingTask.SEMANTIC:
            return self._semantic_depth
        elif task == ProcessingTask.SELF_REFERENCE:
            return self._self_reference_depth
        else:
            return self._other_reference_depth

    def check_self_descriptive(
        self,
        word: str
    ) -> bool:
        """Check if word is self-descriptive."""
        return word.lower() in self._self_traits

    def calculate_encoding_strength(
        self,
        task: ProcessingTask,
        self_descriptive: bool,
        response_yes: bool
    ) -> float:
        """Calculate encoding strength."""
        base_depth = self.get_processing_depth(task)

        # Self-reference bonus
        if task == ProcessingTask.SELF_REFERENCE:
            # Extra elaboration through self-schema
            bonus = self._self_elaboration

            # Organization within self-schema
            if self_descriptive and response_yes:
                bonus += self._organization_bonus
        else:
            bonus = 0

        # Yes responses get slight boost (commitment)
        if response_yes:
            bonus += 0.05

        return min(1.0, base_depth + bonus)


# ============================================================================
# SELF-REFERENCE MEMORY SYSTEM
# ============================================================================

class SelfReferenceMemory:
    """
    Self-reference effect memory system.

    "Ba'el's self-connected memories." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._schema = SelfSchemaModel()

        self._words: Dict[str, TraitWord] = {}
        self._encodings: Dict[str, EncodingResult] = {}

        self._word_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._word_counter += 1
        return f"word_{self._word_counter}"

    def process_word(
        self,
        word: str,
        task: ProcessingTask,
        valence: TraitValence = TraitValence.NEUTRAL
    ) -> EncodingResult:
        """Process a word with a given task."""
        word_id = self._generate_id()

        # Determine if self-descriptive
        self_descriptive = self._schema.check_self_descriptive(word)

        # Simulate response
        if task == ProcessingTask.STRUCTURAL:
            response = random.random() < 0.5  # Random structural judgment
            rt = 400 + random.uniform(0, 200)
        elif task == ProcessingTask.PHONEMIC:
            response = random.random() < 0.5
            rt = 500 + random.uniform(0, 200)
        elif task == ProcessingTask.SEMANTIC:
            response = random.random() < 0.6
            rt = 700 + random.uniform(0, 300)
        elif task == ProcessingTask.SELF_REFERENCE:
            response = self_descriptive or random.random() < 0.3
            rt = 900 + random.uniform(0, 400)  # Deeper processing takes longer
        else:
            response = random.random() < 0.5
            rt = 800 + random.uniform(0, 300)

        # Calculate encoding
        depth = self._schema.get_processing_depth(task)
        encoding_strength = self._schema.calculate_encoding_strength(
            task, self_descriptive, response
        )

        trait_word = TraitWord(
            id=word_id,
            word=word,
            valence=valence,
            self_descriptive=self_descriptive,
            processing_task=task,
            processing_depth=depth
        )

        result = EncodingResult(
            word_id=word_id,
            task=task,
            response=response,
            response_time_ms=rt,
            encoding_strength=encoding_strength
        )

        self._words[word_id] = trait_word
        self._encodings[word_id] = result

        return result

    def test_recall(
        self,
        word_id: str,
        delay_minutes: float = 0
    ) -> RecallResult:
        """Test recall of a word."""
        encoding = self._encodings.get(word_id)
        if not encoding:
            return None

        # Recall probability based on encoding strength
        strength = encoding.encoding_strength

        # Decay with time
        if delay_minutes > 0:
            decay = 0.02 * math.sqrt(delay_minutes)
            strength = strength * (1 - decay)

        recall_prob = strength * 0.8 + 0.1
        recalled = random.random() < recall_prob

        # Source memory (what task?)
        if recalled:
            source_prob = 0.5 + 0.3 * encoding.encoding_strength
            source_correct = random.random() < source_prob
        else:
            source_correct = False

        return RecallResult(
            word_id=word_id,
            recalled=recalled,
            source_correct=source_correct
        )


# ============================================================================
# EXPERIMENTAL PARADIGM
# ============================================================================

class SelfReferenceParadigm:
    """
    Self-reference effect experimental paradigm.

    "Ba'el's SRE study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_classic_experiment(
        self,
        words_per_condition: int = 10,
        delay_minutes: float = 10
    ) -> Dict[str, Any]:
        """Run classic self-reference experiment."""
        system = SelfReferenceMemory()

        # Word lists for each condition
        trait_words = [
            'honest', 'clever', 'cruel', 'lazy', 'brave', 'shy',
            'bold', 'calm', 'cold', 'warm', 'wise', 'rude',
            'fair', 'mean', 'kind', 'dull', 'nice', 'vain',
            'weak', 'firm', 'loud', 'soft', 'tough', 'mild',
            'smart', 'slow', 'quick', 'rash', 'cool', 'keen',
            'bright', 'dim', 'clear', 'vague', 'pure', 'foul',
            'sweet', 'sour', 'fresh', 'stale'
        ]

        random.shuffle(trait_words)

        conditions = [
            ProcessingTask.STRUCTURAL,
            ProcessingTask.PHONEMIC,
            ProcessingTask.SEMANTIC,
            ProcessingTask.SELF_REFERENCE
        ]

        results_by_condition: Dict[ProcessingTask, List[str]] = defaultdict(list)

        for i, word in enumerate(trait_words[:words_per_condition * 4]):
            condition = conditions[i // words_per_condition]
            result = system.process_word(word, condition)
            results_by_condition[condition].append(result.word_id)

        # Recall test
        recall_by_condition: Dict[str, List[bool]] = defaultdict(list)

        for condition, word_ids in results_by_condition.items():
            for word_id in word_ids:
                recall = system.test_recall(word_id, delay_minutes)
                recall_by_condition[condition.name].append(recall.recalled if recall else False)

        # Calculate means
        means = {}
        for condition_name, recalls in recall_by_condition.items():
            means[condition_name] = sum(recalls) / len(recalls) if recalls else 0

        sre_effect = means.get('SELF_REFERENCE', 0) - means.get('SEMANTIC', 0)

        return {
            'words_per_condition': words_per_condition,
            'structural_recall': means.get('STRUCTURAL', 0),
            'phonemic_recall': means.get('PHONEMIC', 0),
            'semantic_recall': means.get('SEMANTIC', 0),
            'self_reference_recall': means.get('SELF_REFERENCE', 0),
            'sre_effect': sre_effect
        }

    def run_other_reference_comparison(
        self,
        n_words: int = 10
    ) -> Dict[str, Any]:
        """Compare self vs other reference."""
        system = SelfReferenceMemory()

        words = ['honest', 'clever', 'kind', 'brave', 'shy',
                 'bold', 'calm', 'wise', 'fair', 'smart']

        # Self-reference condition
        self_ref_ids = []
        for word in words[:n_words // 2]:
            result = system.process_word(word, ProcessingTask.SELF_REFERENCE)
            self_ref_ids.append(result.word_id)

        # Other-reference condition
        other_ref_ids = []
        for word in words[n_words // 2:]:
            result = system.process_word(word, ProcessingTask.OTHER_REFERENCE)
            other_ref_ids.append(result.word_id)

        # Recall
        self_recalled = sum(1 for wid in self_ref_ids
                          if system.test_recall(wid, 10).recalled)
        other_recalled = sum(1 for wid in other_ref_ids
                           if system.test_recall(wid, 10).recalled)

        return {
            'self_reference_recall': self_recalled / (n_words // 2) if n_words > 0 else 0,
            'other_reference_recall': other_recalled / (n_words // 2) if n_words > 0 else 0,
            'self_advantage': (self_recalled - other_recalled) / (n_words // 2) if n_words > 0 else 0
        }

    def run_valence_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare SRE for positive vs negative traits."""
        system = SelfReferenceMemory()

        positive = ['kind', 'clever', 'honest', 'brave', 'wise']
        negative = ['cruel', 'lazy', 'rude', 'mean', 'dull']

        results = {}

        for valence, words in [('positive', positive), ('negative', negative)]:
            word_ids = []
            for word in words:
                val = TraitValence.POSITIVE if valence == 'positive' else TraitValence.NEGATIVE
                result = system.process_word(word, ProcessingTask.SELF_REFERENCE, val)
                word_ids.append(result.word_id)

            recalled = sum(1 for wid in word_ids if system.test_recall(wid, 10).recalled)
            results[valence] = recalled / len(words)

        return results


# ============================================================================
# SELF-REFERENCE ENGINE
# ============================================================================

class SelfReferenceEngine:
    """
    Complete self-reference effect engine.

    "Ba'el's self-enhanced memory." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = SelfReferenceParadigm()
        self._system = SelfReferenceMemory()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Processing

    def process_word(
        self,
        word: str,
        task: ProcessingTask,
        valence: TraitValence = TraitValence.NEUTRAL
    ) -> EncodingResult:
        """Process a word."""
        return self._system.process_word(word, task, valence)

    # Recall

    def test_recall(
        self,
        word_id: str,
        delay: float = 0
    ) -> RecallResult:
        """Test recall."""
        return self._system.test_recall(word_id, delay)

    # Experiments

    def run_sre_experiment(
        self,
        words_per_condition: int = 10
    ) -> Dict[str, Any]:
        """Run self-reference experiment."""
        result = self._paradigm.run_classic_experiment(words_per_condition, 10)
        self._experiment_results.append(result)
        return result

    def run_other_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare self vs other reference."""
        return self._paradigm.run_other_reference_comparison()

    def run_valence_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare by valence."""
        return self._paradigm.run_valence_comparison()

    def run_levels_replication(
        self
    ) -> Dict[str, Any]:
        """Replicate levels-of-processing with SRE."""
        result = self._paradigm.run_classic_experiment(10, 10)

        return {
            'structural': result['structural_recall'],
            'phonemic': result['phonemic_recall'],
            'semantic': result['semantic_recall'],
            'self_reference': result['self_reference_recall'],
            'levels_effect': (
                result['semantic_recall'] - result['structural_recall']
            ),
            'sre_beyond_semantic': (
                result['self_reference_recall'] - result['semantic_recall']
            )
        }

    # Analysis

    def get_metrics(self) -> SelfReferenceMetrics:
        """Get self-reference metrics."""
        if not self._experiment_results:
            self.run_sre_experiment()

        last = self._experiment_results[-1]

        return SelfReferenceMetrics(
            structural_recall=last['structural_recall'],
            phonemic_recall=last['phonemic_recall'],
            semantic_recall=last['semantic_recall'],
            self_reference_recall=last['self_reference_recall'],
            sre_effect=last['sre_effect']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'words': len(self._system._words),
            'encodings': len(self._system._encodings),
            'experiments': len(self._experiment_results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_self_reference_engine() -> SelfReferenceEngine:
    """Create self-reference engine."""
    return SelfReferenceEngine()


def demonstrate_self_reference() -> Dict[str, Any]:
    """Demonstrate self-reference effect."""
    engine = create_self_reference_engine()

    # Classic experiment
    classic = engine.run_sre_experiment(10)

    # Other reference comparison
    other = engine.run_other_comparison()

    # Valence comparison
    valence = engine.run_valence_comparison()

    # Levels replication
    levels = engine.run_levels_replication()

    return {
        'classic_sre': {
            'structural': f"{classic['structural_recall']:.0%}",
            'phonemic': f"{classic['phonemic_recall']:.0%}",
            'semantic': f"{classic['semantic_recall']:.0%}",
            'self_reference': f"{classic['self_reference_recall']:.0%}",
            'sre_effect': f"{classic['sre_effect']:.0%}"
        },
        'self_vs_other': {
            'self': f"{other['self_reference_recall']:.0%}",
            'other': f"{other['other_reference_recall']:.0%}",
            'advantage': f"{other['self_advantage']:.0%}"
        },
        'valence': {
            'positive': f"{valence['positive']:.0%}",
            'negative': f"{valence['negative']:.0%}"
        },
        'levels_plus_sre': {
            'levels_effect': f"{levels['levels_effect']:.0%}",
            'sre_beyond_semantic': f"{levels['sre_beyond_semantic']:.0%}"
        },
        'interpretation': (
            f"SRE: {classic['sre_effect']:.0%} advantage for self-referential processing. "
            f"Self-schema provides rich elaboration and organization."
        )
    }


def get_self_reference_facts() -> Dict[str, str]:
    """Get facts about self-reference effect."""
    return {
        'rogers_et_al_1977': 'Original demonstration of SRE',
        'self_schema': 'Self as rich, organized knowledge structure',
        'elaboration': 'Self-reference promotes deep elaboration',
        'organization': 'Self integrates new information',
        'beyond_semantic': 'SRE exceeds semantic processing advantage',
        'clinical': 'Reduced in depression (negative self-schema)',
        'development': 'Emerges around age 3-4',
        'cross_cultural': 'Varies with independent vs interdependent self'
    }
