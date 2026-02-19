"""
BAEL Production Effect Engine
===============================

Saying words aloud improves memory.
MacLeod's distinctiveness effect.

"Ba'el speaks to remember." — Ba'el
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

logger = logging.getLogger("BAEL.ProductionEffect")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ProductionType(Enum):
    """Type of production."""
    SILENT = auto()        # Read silently
    ALOUD = auto()         # Say aloud
    MOUTHED = auto()       # Mouth without sound
    TYPED = auto()         # Type the word
    WRITTEN = auto()       # Write by hand
    SUNG = auto()          # Sing the word
    WHISPERED = auto()     # Whisper
    SPELLED = auto()       # Spell aloud


class DesignType(Enum):
    """Experimental design."""
    WITHIN_LIST = auto()   # Mixed list
    BETWEEN_LIST = auto()  # Pure lists


class TestType(Enum):
    """Type of memory test."""
    FREE_RECALL = auto()
    CUED_RECALL = auto()
    RECOGNITION = auto()


class MechanismType(Enum):
    """Mechanism of the effect."""
    DISTINCTIVENESS = auto()
    SELF_REFERENCE = auto()
    MOTOR = auto()
    AUDITORY = auto()
    ARTICULATORY = auto()


@dataclass
class Word:
    """
    A word stimulus.
    """
    id: str
    word: str
    frequency: float
    concreteness: float
    length: int


@dataclass
class StudyTrial:
    """
    A study trial.
    """
    id: str
    word: Word
    production: ProductionType
    study_time_ms: float
    list_position: int


@dataclass
class TestTrial:
    """
    A test trial.
    """
    id: str
    word: Word
    production_at_study: ProductionType
    response: Optional[str]
    correct: bool
    response_time_ms: float


@dataclass
class RecallResult:
    """
    Result of recall.
    """
    production_type: ProductionType
    words_presented: List[str]
    words_recalled: List[str]
    proportion_recalled: float
    production_effect: float


@dataclass
class ProductionMetrics:
    """
    Production effect metrics.
    """
    aloud_recall: float
    silent_recall: float
    production_effect: float
    by_production_type: Dict[str, float]
    design_effect: Dict[str, float]


# ============================================================================
# PRODUCTION EFFECT MODEL
# ============================================================================

class ProductionEffectModel:
    """
    Model of the production effect.

    "Ba'el's production model." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Base recall probability
        self._base_recall = 0.45

        # Production effects
        self._production_boosts = {
            ProductionType.SILENT: 0.0,
            ProductionType.ALOUD: 0.15,
            ProductionType.MOUTHED: 0.10,
            ProductionType.TYPED: 0.08,
            ProductionType.WRITTEN: 0.12,
            ProductionType.SUNG: 0.14,
            ProductionType.WHISPERED: 0.09,
            ProductionType.SPELLED: 0.11
        }

        # Within-list distinctiveness bonus
        self._within_list_bonus = 0.05

        # Test type effects
        self._test_effects = {
            TestType.FREE_RECALL: 1.0,
            TestType.CUED_RECALL: 0.9,
            TestType.RECOGNITION: 0.6  # Smaller in recognition
        }

        # Mechanism contributions
        self._mechanism_contributions = {
            MechanismType.DISTINCTIVENESS: 0.40,
            MechanismType.SELF_REFERENCE: 0.20,
            MechanismType.MOTOR: 0.15,
            MechanismType.AUDITORY: 0.15,
            MechanismType.ARTICULATORY: 0.10
        }

        # Study time effect
        self._study_time_effect = 0.01  # Per 100ms

        self._lock = threading.RLock()

    def get_production_boost(
        self,
        production: ProductionType,
        design: DesignType
    ) -> float:
        """Get memory boost for production."""
        boost = self._production_boosts[production]

        # Within-list distinctiveness bonus
        if design == DesignType.WITHIN_LIST and production != ProductionType.SILENT:
            boost += self._within_list_bonus

        return boost

    def calculate_recall_probability(
        self,
        word: Word,
        production: ProductionType,
        design: DesignType,
        test_type: TestType = TestType.FREE_RECALL
    ) -> float:
        """Calculate recall probability."""
        prob = self._base_recall

        # Production effect
        boost = self.get_production_boost(production, design)
        prob += boost

        # Test type modulation
        prob *= self._test_effects[test_type]

        # Word effects
        prob += word.concreteness * 0.05
        prob += (7 - word.length) * 0.01  # Shorter = easier

        # Add noise
        prob += random.uniform(-0.1, 0.1)

        return max(0.05, min(0.95, prob))

    def calculate_production_effect(
        self,
        aloud_recall: float,
        silent_recall: float
    ) -> float:
        """Calculate production effect size."""
        return aloud_recall - silent_recall

    def get_mechanism_breakdown(
        self
    ) -> Dict[MechanismType, float]:
        """Get mechanism contributions."""
        return self._mechanism_contributions.copy()


# ============================================================================
# PRODUCTION EFFECT SYSTEM
# ============================================================================

class ProductionEffectSystem:
    """
    Production effect simulation system.

    "Ba'el's production system." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = ProductionEffectModel()

        self._words: Dict[str, Word] = {}
        self._study_trials: Dict[str, StudyTrial] = {}
        self._test_trials: Dict[str, TestTrial] = {}

        self._counter = 0
        self._lock = threading.RLock()

        # Initialize word pool
        self._initialize_words()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"item_{self._counter}"

    def _initialize_words(self):
        """Initialize word pool."""
        words = [
            ("apple", 6.0, 0.9),
            ("book", 7.0, 0.85),
            ("chair", 6.5, 0.9),
            ("dream", 5.0, 0.4),
            ("eagle", 4.5, 0.9),
            ("flower", 5.5, 0.95),
            ("garden", 5.0, 0.85),
            ("horse", 6.0, 0.95),
            ("island", 5.0, 0.8),
            ("jungle", 4.0, 0.75),
            ("kitchen", 5.5, 0.9),
            ("lemon", 5.0, 0.95),
            ("mountain", 5.5, 0.85),
            ("nature", 5.0, 0.5),
            ("ocean", 5.5, 0.8),
            ("pencil", 5.0, 0.95),
            ("queen", 5.5, 0.7),
            ("river", 6.0, 0.85),
            ("sunset", 4.5, 0.7),
            ("table", 6.5, 0.95)
        ]

        for word, freq, conc in words:
            self._words[word] = Word(
                id=self._generate_id(),
                word=word,
                frequency=freq,
                concreteness=conc,
                length=len(word)
            )

    def create_study_trial(
        self,
        word: str,
        production: ProductionType,
        position: int
    ) -> StudyTrial:
        """Create study trial."""
        word_obj = self._words.get(word)
        if not word_obj:
            word_obj = Word(
                id=self._generate_id(),
                word=word,
                frequency=5.0,
                concreteness=0.5,
                length=len(word)
            )
            self._words[word] = word_obj

        trial = StudyTrial(
            id=self._generate_id(),
            word=word_obj,
            production=production,
            study_time_ms=random.uniform(2000, 3000),
            list_position=position
        )

        self._study_trials[trial.id] = trial

        return trial

    def run_free_recall(
        self,
        trial_ids: List[str],
        design: DesignType
    ) -> Dict[ProductionType, RecallResult]:
        """Run free recall test."""
        trials = [self._study_trials[tid] for tid in trial_ids if tid in self._study_trials]

        # Group by production type
        by_production = defaultdict(list)
        for trial in trials:
            by_production[trial.production].append(trial)

        results = {}

        for production, prod_trials in by_production.items():
            words_presented = [t.word.word for t in prod_trials]
            words_recalled = []

            for trial in prod_trials:
                prob = self._model.calculate_recall_probability(
                    trial.word, production, design
                )

                if random.random() < prob:
                    words_recalled.append(trial.word.word)

            proportion = len(words_recalled) / max(1, len(words_presented))

            results[production] = RecallResult(
                production_type=production,
                words_presented=words_presented,
                words_recalled=words_recalled,
                proportion_recalled=proportion,
                production_effect=0  # Calculated later
            )

        # Calculate production effect
        if ProductionType.ALOUD in results and ProductionType.SILENT in results:
            effect = (
                results[ProductionType.ALOUD].proportion_recalled -
                results[ProductionType.SILENT].proportion_recalled
            )
            results[ProductionType.ALOUD] = RecallResult(
                production_type=ProductionType.ALOUD,
                words_presented=results[ProductionType.ALOUD].words_presented,
                words_recalled=results[ProductionType.ALOUD].words_recalled,
                proportion_recalled=results[ProductionType.ALOUD].proportion_recalled,
                production_effect=effect
            )

        return results


# ============================================================================
# PRODUCTION EFFECT PARADIGM
# ============================================================================

class ProductionEffectParadigm:
    """
    Production effect paradigm.

    "Ba'el's production study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_classic_paradigm(
        self,
        n_words: int = 20
    ) -> Dict[str, Any]:
        """Run classic production effect paradigm."""
        system = ProductionEffectSystem()

        words = list(system._words.keys())[:n_words]

        # Randomly assign to conditions
        random.shuffle(words)
        aloud_words = words[:n_words // 2]
        silent_words = words[n_words // 2:]

        trial_ids = []

        # Create study trials
        for i, word in enumerate(aloud_words):
            trial = system.create_study_trial(word, ProductionType.ALOUD, i)
            trial_ids.append(trial.id)

        for i, word in enumerate(silent_words):
            trial = system.create_study_trial(word, ProductionType.SILENT, i + len(aloud_words))
            trial_ids.append(trial.id)

        # Test
        results = system.run_free_recall(trial_ids, DesignType.WITHIN_LIST)

        aloud_recall = results[ProductionType.ALOUD].proportion_recalled
        silent_recall = results[ProductionType.SILENT].proportion_recalled

        return {
            'aloud_recall': aloud_recall,
            'silent_recall': silent_recall,
            'production_effect': aloud_recall - silent_recall,
            'interpretation': f'Production effect: {(aloud_recall - silent_recall):.0%}'
        }

    def run_design_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare within-list vs between-list designs."""
        results = {}

        for design in [DesignType.WITHIN_LIST, DesignType.BETWEEN_LIST]:
            system = ProductionEffectSystem()
            model = system._model

            # Simulate
            aloud_probs = []
            silent_probs = []

            for word in list(system._words.values())[:20]:
                aloud_prob = model.calculate_recall_probability(
                    word, ProductionType.ALOUD, design
                )
                silent_prob = model.calculate_recall_probability(
                    word, ProductionType.SILENT, design
                )
                aloud_probs.append(aloud_prob)
                silent_probs.append(silent_prob)

            aloud_mean = sum(aloud_probs) / len(aloud_probs)
            silent_mean = sum(silent_probs) / len(silent_probs)

            results[design.name] = {
                'aloud': aloud_mean,
                'silent': silent_mean,
                'effect': aloud_mean - silent_mean
            }

        return {
            'by_design': results,
            'interpretation': 'Larger effect with within-list design'
        }

    def run_production_type_study(
        self
    ) -> Dict[str, Any]:
        """Study different production types."""
        model = ProductionEffectModel()

        results = {}

        for production in ProductionType:
            boost = model.get_production_boost(production, DesignType.WITHIN_LIST)

            results[production.name] = {
                'memory_boost': boost
            }

        return {
            'by_production': results,
            'interpretation': 'Aloud and sung produce largest effects'
        }

    def run_test_type_study(
        self
    ) -> Dict[str, Any]:
        """Study effect across test types."""
        system = ProductionEffectSystem()
        model = system._model

        results = {}

        for test_type in TestType:
            aloud_probs = []
            silent_probs = []

            for word in list(system._words.values())[:10]:
                aloud = model.calculate_recall_probability(
                    word, ProductionType.ALOUD, DesignType.WITHIN_LIST, test_type
                )
                silent = model.calculate_recall_probability(
                    word, ProductionType.SILENT, DesignType.WITHIN_LIST, test_type
                )
                aloud_probs.append(aloud)
                silent_probs.append(silent)

            effect = (sum(aloud_probs) - sum(silent_probs)) / len(aloud_probs)

            results[test_type.name] = {
                'production_effect': effect
            }

        return {
            'by_test': results,
            'interpretation': 'Largest in recall, smaller in recognition'
        }

    def run_mechanism_study(
        self
    ) -> Dict[str, Any]:
        """Study underlying mechanisms."""
        model = ProductionEffectModel()

        breakdown = model.get_mechanism_breakdown()

        return {
            'mechanism_contributions': {
                m.name: f"{c:.0%}" for m, c in breakdown.items()
            },
            'interpretation': 'Distinctiveness is primary mechanism'
        }

    def run_list_length_study(
        self
    ) -> Dict[str, Any]:
        """Study effect of list length."""
        results = {}

        for length in [10, 20, 40]:
            system = ProductionEffectSystem()

            words = list(system._words.keys())[:length]
            random.shuffle(words)

            n_aloud = length // 2

            aloud_recalled = 0
            silent_recalled = 0

            for i, word in enumerate(words):
                prod = ProductionType.ALOUD if i < n_aloud else ProductionType.SILENT
                word_obj = system._words[word]

                prob = system._model.calculate_recall_probability(
                    word_obj, prod, DesignType.WITHIN_LIST
                )

                if random.random() < prob:
                    if prod == ProductionType.ALOUD:
                        aloud_recalled += 1
                    else:
                        silent_recalled += 1

            aloud_rate = aloud_recalled / max(1, n_aloud)
            silent_rate = silent_recalled / max(1, length - n_aloud)

            results[f"length_{length}"] = {
                'aloud': aloud_rate,
                'silent': silent_rate,
                'effect': aloud_rate - silent_rate
            }

        return {
            'by_length': results,
            'interpretation': 'Effect persists across list lengths'
        }


# ============================================================================
# PRODUCTION EFFECT ENGINE
# ============================================================================

class ProductionEffectEngine:
    """
    Complete production effect engine.

    "Ba'el's production engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = ProductionEffectParadigm()
        self._system = ProductionEffectSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Trial operations

    def study_word(
        self,
        word: str,
        production: ProductionType
    ) -> StudyTrial:
        """Study a word."""
        return self._system.create_study_trial(word, production, 0)

    def test_recall(
        self,
        trial_ids: List[str],
        design: DesignType = DesignType.WITHIN_LIST
    ) -> Dict[ProductionType, RecallResult]:
        """Test recall."""
        return self._system.run_free_recall(trial_ids, design)

    # Experiments

    def run_classic(
        self
    ) -> Dict[str, Any]:
        """Run classic paradigm."""
        result = self._paradigm.run_classic_paradigm()
        self._experiment_results.append(result)
        return result

    def compare_designs(
        self
    ) -> Dict[str, Any]:
        """Compare designs."""
        return self._paradigm.run_design_comparison()

    def study_production_types(
        self
    ) -> Dict[str, Any]:
        """Study production types."""
        return self._paradigm.run_production_type_study()

    def study_test_types(
        self
    ) -> Dict[str, Any]:
        """Study test types."""
        return self._paradigm.run_test_type_study()

    def study_mechanisms(
        self
    ) -> Dict[str, Any]:
        """Study mechanisms."""
        return self._paradigm.run_mechanism_study()

    def study_list_length(
        self
    ) -> Dict[str, Any]:
        """Study list length."""
        return self._paradigm.run_list_length_study()

    # Analysis

    def get_metrics(self) -> ProductionMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_classic()

        last = self._experiment_results[-1]

        return ProductionMetrics(
            aloud_recall=last['aloud_recall'],
            silent_recall=last['silent_recall'],
            production_effect=last['production_effect'],
            by_production_type={},
            design_effect={}
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'words': len(self._system._words),
            'study_trials': len(self._system._study_trials)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_production_effect_engine() -> ProductionEffectEngine:
    """Create production effect engine."""
    return ProductionEffectEngine()


def demonstrate_production_effect() -> Dict[str, Any]:
    """Demonstrate production effect."""
    engine = create_production_effect_engine()

    # Classic
    classic = engine.run_classic()

    # Design comparison
    designs = engine.compare_designs()

    # Production types
    types = engine.study_production_types()

    # Mechanisms
    mechanisms = engine.study_mechanisms()

    return {
        'classic_effect': {
            'aloud': f"{classic['aloud_recall']:.0%}",
            'silent': f"{classic['silent_recall']:.0%}",
            'effect': f"{classic['production_effect']:.0%}"
        },
        'by_design': {
            k: f"{v['effect']:.0%}"
            for k, v in designs['by_design'].items()
        },
        'by_production': {
            k: f"+{v['memory_boost']:.0%}"
            for k, v in types['by_production'].items()
        },
        'mechanisms': mechanisms['mechanism_contributions'],
        'interpretation': (
            f"Production effect: {classic['production_effect']:.0%}. "
            f"Saying aloud improves memory via distinctiveness."
        )
    }


def get_production_effect_facts() -> Dict[str, str]:
    """Get facts about production effect."""
    return {
        'macleod_2010': 'Discovery of production effect',
        'effect_size': '~10-15% better recall',
        'mechanism': 'Distinctiveness at encoding',
        'within_list': 'Larger effect than between-list',
        'test_type': 'Larger in recall than recognition',
        'production_types': 'Aloud, mouthed, written, typed',
        'robust': 'Replicates across many conditions',
        'applications': 'Study strategies, vocabulary learning'
    }
