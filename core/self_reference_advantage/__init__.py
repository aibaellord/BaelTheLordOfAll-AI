"""
BAEL Self-Reference Memory Advantage Engine
=============================================

Better memory for information related to self.
Rogers et al.'s self-reference effect.

"Ba'el remembers best what touches Ba'el." — Ba'el
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

logger = logging.getLogger("BAEL.SelfReferenceAdvantage")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class EncodingTask(Enum):
    """Type of encoding task."""
    SELF_REFERENCE = auto()       # Does this describe you?
    OTHER_REFERENCE = auto()      # Does this describe Obama?
    SEMANTIC = auto()             # What does this mean?
    STRUCTURAL = auto()           # Is this word uppercase?
    MOTHER_REFERENCE = auto()     # Does this describe your mother?


class WordType(Enum):
    """Type of word."""
    TRAIT_POSITIVE = auto()
    TRAIT_NEGATIVE = auto()
    TRAIT_NEUTRAL = auto()
    OBJECT = auto()


class MemoryMeasure(Enum):
    """Type of memory measure."""
    FREE_RECALL = auto()
    RECOGNITION = auto()
    REMEMBER_KNOW = auto()


class SelfConstrual(Enum):
    """Type of self-construal."""
    INDEPENDENT = auto()      # Western
    INTERDEPENDENT = auto()   # Eastern


@dataclass
class TargetWord:
    """
    A target word for encoding.
    """
    id: str
    word: str
    word_type: WordType
    self_descriptiveness: float
    imagery: float


@dataclass
class EncodingTrial:
    """
    An encoding trial.
    """
    word: TargetWord
    task: EncodingTask
    response: bool
    encoding_time_ms: int


@dataclass
class MemoryTest:
    """
    Memory test result.
    """
    word: TargetWord
    encoding_task: EncodingTask
    recalled: bool
    remember_experience: bool
    confidence: float


@dataclass
class SelfReferenceMetrics:
    """
    Self-reference effect metrics.
    """
    self_recall: float
    semantic_recall: float
    structural_recall: float
    self_advantage: float


# ============================================================================
# SELF REFERENCE MODEL
# ============================================================================

class SelfReferenceModel:
    """
    Model of self-reference advantage.

    "Ba'el's self-schema model." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Base recall rates by task
        self._task_recall = {
            EncodingTask.SELF_REFERENCE: 0.70,
            EncodingTask.OTHER_REFERENCE: 0.55,
            EncodingTask.SEMANTIC: 0.58,
            EncodingTask.STRUCTURAL: 0.35,
            EncodingTask.MOTHER_REFERENCE: 0.62
        }

        # Self-descriptiveness effect
        self._descriptiveness_effect = 0.10

        # Word type effects
        self._word_type_effects = {
            WordType.TRAIT_POSITIVE: 0.05,
            WordType.TRAIT_NEGATIVE: 0.02,
            WordType.TRAIT_NEUTRAL: 0.0,
            WordType.OBJECT: -0.05
        }

        # Self-construal effects
        self._construal_effects = {
            SelfConstrual.INDEPENDENT: 0.0,
            SelfConstrual.INTERDEPENDENT: 0.05  # Other-reference boost
        }

        # Imagery effects
        self._imagery_effect = 0.08

        # Elaboration depth
        self._self_elaboration = 0.90
        self._semantic_elaboration = 0.70
        self._structural_elaboration = 0.30

        # Organization benefits
        self._self_organization = 0.85

        self._lock = threading.RLock()

    def calculate_recall_probability(
        self,
        task: EncodingTask,
        word_type: WordType = WordType.TRAIT_NEUTRAL,
        self_descriptiveness: float = 0.5,
        imagery: float = 0.5,
        self_construal: SelfConstrual = SelfConstrual.INDEPENDENT
    ) -> float:
        """Calculate recall probability."""
        prob = self._task_recall[task]

        # Self-descriptiveness (only matters for self-reference)
        if task == EncodingTask.SELF_REFERENCE:
            prob += (self_descriptiveness - 0.5) * self._descriptiveness_effect * 2

        # Word type
        prob += self._word_type_effects[word_type]

        # Imagery
        prob += (imagery - 0.5) * self._imagery_effect * 2

        # Construal (boosts other-reference for interdependent)
        if task == EncodingTask.OTHER_REFERENCE:
            prob += self._construal_effects[self_construal]

        # Add noise
        prob += random.uniform(-0.08, 0.08)

        return max(0.2, min(0.90, prob))

    def calculate_remember_probability(
        self,
        task: EncodingTask
    ) -> float:
        """Calculate probability of 'remember' (vs 'know')."""
        # Self-reference leads to more 'remember' experiences
        remember_base = {
            EncodingTask.SELF_REFERENCE: 0.75,
            EncodingTask.OTHER_REFERENCE: 0.55,
            EncodingTask.SEMANTIC: 0.60,
            EncodingTask.STRUCTURAL: 0.35,
            EncodingTask.MOTHER_REFERENCE: 0.65
        }

        prob = remember_base[task]
        prob += random.uniform(-0.1, 0.1)

        return max(0.2, min(0.90, prob))

    def get_elaboration_depth(
        self,
        task: EncodingTask
    ) -> float:
        """Get elaboration depth for task."""
        depths = {
            EncodingTask.SELF_REFERENCE: self._self_elaboration,
            EncodingTask.OTHER_REFERENCE: 0.65,
            EncodingTask.SEMANTIC: self._semantic_elaboration,
            EncodingTask.STRUCTURAL: self._structural_elaboration,
            EncodingTask.MOTHER_REFERENCE: 0.70
        }
        return depths[task]

    def get_mechanisms(
        self
    ) -> Dict[str, str]:
        """Get proposed mechanisms."""
        return {
            'elaboration': 'Self-reference promotes deep elaboration',
            'organization': 'Self-schema organizes information',
            'distinctiveness': 'Self-relevant items are distinctive',
            'emotional_engagement': 'Self-relevance evokes emotion',
            'retrieval_cues': 'Self provides rich retrieval structure'
        }

    def get_boundary_conditions(
        self
    ) -> Dict[str, str]:
        """Get boundary conditions."""
        return {
            'trait_words': 'Effect strongest for personality traits',
            'self_descriptive': 'Stronger for self-descriptive items',
            'age': 'Develops in childhood',
            'culture': 'Modified by self-construal',
            'depression': 'Reduced for positive traits in depression'
        }


# ============================================================================
# SELF REFERENCE SYSTEM
# ============================================================================

class SelfReferenceSystem:
    """
    Self-reference effect simulation system.

    "Ba'el's self-reference system." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = SelfReferenceModel()

        self._words: Dict[str, TargetWord] = {}
        self._encoding_trials: List[EncodingTrial] = []
        self._memory_tests: List[MemoryTest] = []

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"word_{self._counter}"

    def create_word(
        self,
        word: str,
        word_type: WordType = WordType.TRAIT_NEUTRAL,
        self_descriptiveness: float = 0.5,
        imagery: float = 0.5
    ) -> TargetWord:
        """Create target word."""
        target = TargetWord(
            id=self._generate_id(),
            word=word,
            word_type=word_type,
            self_descriptiveness=self_descriptiveness,
            imagery=imagery
        )

        self._words[target.id] = target

        return target

    def encode_word(
        self,
        word: TargetWord,
        task: EncodingTask
    ) -> EncodingTrial:
        """Encode word with task."""
        # Response depends on task and word
        if task == EncodingTask.SELF_REFERENCE:
            response = random.random() < word.self_descriptiveness
        elif task == EncodingTask.STRUCTURAL:
            response = random.choice([True, False])
        else:
            response = True

        trial = EncodingTrial(
            word=word,
            task=task,
            response=response,
            encoding_time_ms=random.randint(800, 2500)
        )

        self._encoding_trials.append(trial)

        return trial

    def test_memory(
        self,
        word: TargetWord,
        encoding_task: EncodingTask
    ) -> MemoryTest:
        """Test memory for word."""
        recall_prob = self._model.calculate_recall_probability(
            encoding_task,
            word.word_type,
            word.self_descriptiveness,
            word.imagery
        )

        recalled = random.random() < recall_prob

        remember_prob = self._model.calculate_remember_probability(encoding_task)
        remember = recalled and random.random() < remember_prob

        test = MemoryTest(
            word=word,
            encoding_task=encoding_task,
            recalled=recalled,
            remember_experience=remember,
            confidence=random.uniform(0.5, 0.95) if recalled else 0.3
        )

        self._memory_tests.append(test)

        return test


# ============================================================================
# SELF REFERENCE PARADIGM
# ============================================================================

class SelfReferenceParadigm:
    """
    Self-reference effect paradigm.

    "Ba'el's self-reference study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_classic_paradigm(
        self,
        n_words_per_condition: int = 10
    ) -> Dict[str, Any]:
        """Run classic self-reference paradigm."""
        system = SelfReferenceSystem()

        tasks = [
            EncodingTask.SELF_REFERENCE,
            EncodingTask.SEMANTIC,
            EncodingTask.STRUCTURAL
        ]

        results = defaultdict(list)

        for task in tasks:
            for i in range(n_words_per_condition):
                word = system.create_word(
                    f"{task.name.lower()}_{i}",
                    WordType.TRAIT_NEUTRAL
                )
                system.encode_word(word, task)
                test = system.test_memory(word, task)
                results[task.name].append(test.recalled)

        means = {k: sum(v) / max(1, len(v)) for k, v in results.items()}

        self_adv = means['SELF_REFERENCE'] - means['SEMANTIC']

        return {
            'by_task': means,
            'self_advantage': self_adv,
            'interpretation': f'Self-reference advantage: {self_adv:.0%}'
        }

    def run_other_reference_study(
        self
    ) -> Dict[str, Any]:
        """Compare self vs other reference."""
        model = SelfReferenceModel()

        tasks = [
            EncodingTask.SELF_REFERENCE,
            EncodingTask.OTHER_REFERENCE,
            EncodingTask.MOTHER_REFERENCE
        ]

        results = {}

        for task in tasks:
            recall = model.calculate_recall_probability(task)
            results[task.name] = {'recall': recall}

        return {
            'by_task': results,
            'interpretation': 'Self > Mother > Other'
        }

    def run_word_type_study(
        self
    ) -> Dict[str, Any]:
        """Study word type effects."""
        model = SelfReferenceModel()

        results = {}

        for word_type in WordType:
            recall = model.calculate_recall_probability(
                EncodingTask.SELF_REFERENCE,
                word_type=word_type
            )
            results[word_type.name] = {'recall': recall}

        return {
            'by_word_type': results,
            'interpretation': 'Trait words show strongest effect'
        }

    def run_remember_know_study(
        self
    ) -> Dict[str, Any]:
        """Study remember/know patterns."""
        model = SelfReferenceModel()

        tasks = [
            EncodingTask.SELF_REFERENCE,
            EncodingTask.SEMANTIC,
            EncodingTask.STRUCTURAL
        ]

        results = {}

        for task in tasks:
            remember = model.calculate_remember_probability(task)
            results[task.name] = {'remember': remember}

        return {
            'by_task': results,
            'interpretation': 'Self-reference yields more "remember"'
        }

    def run_elaboration_study(
        self
    ) -> Dict[str, Any]:
        """Study elaboration depth."""
        model = SelfReferenceModel()

        tasks = list(EncodingTask)

        results = {}

        for task in tasks:
            depth = model.get_elaboration_depth(task)
            results[task.name] = {'depth': depth}

        return {
            'by_task': results,
            'interpretation': 'Self-reference promotes deep elaboration'
        }

    def run_mechanism_study(
        self
    ) -> Dict[str, Any]:
        """Study underlying mechanisms."""
        model = SelfReferenceModel()

        mechanisms = model.get_mechanisms()
        boundaries = model.get_boundary_conditions()

        return {
            'mechanisms': mechanisms,
            'boundaries': boundaries,
            'primary': 'Elaboration and organization',
            'interpretation': 'Self-schema provides rich structure'
        }

    def run_culture_study(
        self
    ) -> Dict[str, Any]:
        """Study cultural effects."""
        model = SelfReferenceModel()

        results = {}

        for construal in SelfConstrual:
            self_recall = model.calculate_recall_probability(
                EncodingTask.SELF_REFERENCE,
                self_construal=construal
            )
            other_recall = model.calculate_recall_probability(
                EncodingTask.OTHER_REFERENCE,
                self_construal=construal
            )

            results[construal.name] = {
                'self': self_recall,
                'other': other_recall,
                'advantage': self_recall - other_recall
            }

        return {
            'by_construal': results,
            'interpretation': 'Interdependent shows reduced self-advantage'
        }


# ============================================================================
# SELF REFERENCE ENGINE
# ============================================================================

class SelfReferenceEngine:
    """
    Complete self-reference advantage engine.

    "Ba'el's self-reference engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = SelfReferenceParadigm()
        self._system = SelfReferenceSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Word operations

    def create_word(
        self,
        word: str,
        word_type: WordType = WordType.TRAIT_NEUTRAL
    ) -> TargetWord:
        """Create word."""
        return self._system.create_word(word, word_type)

    def encode_word(
        self,
        word: TargetWord,
        task: EncodingTask
    ) -> EncodingTrial:
        """Encode word."""
        return self._system.encode_word(word, task)

    def test_memory(
        self,
        word: TargetWord,
        task: EncodingTask
    ) -> MemoryTest:
        """Test memory."""
        return self._system.test_memory(word, task)

    # Experiments

    def run_classic(
        self
    ) -> Dict[str, Any]:
        """Run classic paradigm."""
        result = self._paradigm.run_classic_paradigm()
        self._experiment_results.append(result)
        return result

    def compare_references(
        self
    ) -> Dict[str, Any]:
        """Compare self vs other."""
        return self._paradigm.run_other_reference_study()

    def study_word_types(
        self
    ) -> Dict[str, Any]:
        """Study word types."""
        return self._paradigm.run_word_type_study()

    def study_remember_know(
        self
    ) -> Dict[str, Any]:
        """Study remember/know."""
        return self._paradigm.run_remember_know_study()

    def study_elaboration(
        self
    ) -> Dict[str, Any]:
        """Study elaboration."""
        return self._paradigm.run_elaboration_study()

    def study_mechanisms(
        self
    ) -> Dict[str, Any]:
        """Study mechanisms."""
        return self._paradigm.run_mechanism_study()

    def study_culture(
        self
    ) -> Dict[str, Any]:
        """Study culture."""
        return self._paradigm.run_culture_study()

    # Analysis

    def get_metrics(self) -> SelfReferenceMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_classic()

        last = self._experiment_results[-1]
        by_task = last['by_task']

        return SelfReferenceMetrics(
            self_recall=by_task.get('SELF_REFERENCE', 0.70),
            semantic_recall=by_task.get('SEMANTIC', 0.58),
            structural_recall=by_task.get('STRUCTURAL', 0.35),
            self_advantage=last['self_advantage']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'words': len(self._system._words),
            'encoding_trials': len(self._system._encoding_trials),
            'memory_tests': len(self._system._memory_tests)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_self_reference_engine() -> SelfReferenceEngine:
    """Create self-reference advantage engine."""
    return SelfReferenceEngine()


def demonstrate_self_reference_advantage() -> Dict[str, Any]:
    """Demonstrate self-reference advantage."""
    engine = create_self_reference_engine()

    # Classic
    classic = engine.run_classic()

    # References
    references = engine.compare_references()

    # Remember/know
    rk = engine.study_remember_know()

    # Mechanisms
    mechanisms = engine.study_mechanisms()

    return {
        'classic': {
            task: f"{recall:.0%}"
            for task, recall in classic['by_task'].items()
        },
        'advantage': f"{classic['self_advantage']:.0%}",
        'remember_rates': {
            k: f"{v['remember']:.0%}"
            for k, v in rk['by_task'].items()
        },
        'mechanisms': list(mechanisms['mechanisms'].keys()),
        'interpretation': (
            f"Self-advantage: {classic['self_advantage']:.0%}. "
            f"Self-reference promotes elaboration. "
            f"Self-schema organizes information."
        )
    }


def get_self_reference_facts() -> Dict[str, str]:
    """Get facts about self-reference effect."""
    return {
        'rogers_1977': 'Self-reference effect discovery',
        'effect': '10-15% advantage over semantic',
        'mechanism': 'Elaboration and organization',
        'traits': 'Strongest for personality traits',
        'remember': 'More "remember" experiences',
        'culture': 'Modified by self-construal',
        'development': 'Emerges in childhood',
        'applications': 'Education, therapy, advertising'
    }
