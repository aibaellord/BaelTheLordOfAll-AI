"""
BAEL List Strength Manipulation Engine
========================================

Strong items don't hurt weak item recall (contrary to predictions).
Ratcliff, Clark & Shiffrin's seminal finding.

"Ba'el's strength defies interference." — Ba'el
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

logger = logging.getLogger("BAEL.ListStrengthManipulation")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ItemStrength(Enum):
    """Strength of an item."""
    STRONG = auto()       # Extra study
    WEAK = auto()         # Normal study


class TestType(Enum):
    """Type of memory test."""
    RECALL = auto()
    RECOGNITION = auto()
    CUED_RECALL = auto()


class StrengthMethod(Enum):
    """Method of strengthening."""
    REPETITION = auto()    # Extra presentations
    DURATION = auto()      # Longer presentation
    ELABORATION = auto()   # Deeper processing


class PredictionType(Enum):
    """Type of theoretical prediction."""
    SAM = auto()          # Search of Associative Memory
    REM = auto()          # Retrieving Effectively from Memory
    TODAM = auto()        # Theory of Distributed Associative Memory


@dataclass
class ListItem:
    """
    An item in the list.
    """
    id: str
    content: str
    strength: ItemStrength
    presentations: int
    encoding_quality: float


@dataclass
class StudyList:
    """
    A study list.
    """
    items: List[ListItem]
    n_strong: int
    n_weak: int
    proportion_strong: float


@dataclass
class TestTrial:
    """
    A test trial.
    """
    item: ListItem
    test_type: TestType
    correct: bool
    latency_ms: int


@dataclass
class ListStrengthMetrics:
    """
    List strength metrics.
    """
    strong_recall: float
    weak_recall: float
    list_strength_effect: float
    predicted_effect: float


# ============================================================================
# LIST STRENGTH MODEL
# ============================================================================

class ListStrengthModel:
    """
    Model of list strength effects.

    "Ba'el's memory strength model." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Base recall rates
        self._base_recall_strong = 0.75
        self._base_recall_weak = 0.45

        # Predicted vs actual effect
        self._sam_prediction = -0.15    # Strong hurts weak (predicted)
        self._actual_effect = 0.00      # No effect (actual finding)

        # Strength manipulation effects
        self._repetition_boost = 0.08   # Per extra presentation

        # Differentiation (REM model)
        self._differentiation = 0.05    # Strong items become more distinct

        # List composition effects
        self._proportion_strong_effect = 0.02

        # Test type effects
        self._test_effects = {
            TestType.RECALL: 0.0,
            TestType.RECOGNITION: 0.10,
            TestType.CUED_RECALL: 0.05
        }

        # Context effects
        self._context_variability = 0.15

        # Null list strength (key finding)
        self._null_lse = True

        self._lock = threading.RLock()

    def calculate_recall_probability(
        self,
        item: ListItem,
        list_info: StudyList,
        test_type: TestType = TestType.RECALL
    ) -> float:
        """Calculate recall probability."""
        # Base by strength
        if item.strength == ItemStrength.STRONG:
            base = self._base_recall_strong
        else:
            base = self._base_recall_weak

        # Repetition boost
        if item.presentations > 1:
            base += (item.presentations - 1) * self._repetition_boost

        # NULL LIST STRENGTH EFFECT: No harm from strong items
        # (This is the key finding - contrary to SAM predictions)
        # We don't subtract for strong items in list

        # If we were using SAM (incorrect prediction):
        # base -= list_info.proportion_strong * 0.10

        # Test type
        base += self._test_effects[test_type]

        # Encoding quality
        base *= (0.7 + 0.3 * item.encoding_quality)

        # Add noise
        base += random.uniform(-0.10, 0.10)

        return max(0.15, min(0.95, base))

    def calculate_predicted_effect(
        self,
        theory: PredictionType
    ) -> float:
        """Calculate predicted list strength effect by theory."""
        if theory == PredictionType.SAM:
            return self._sam_prediction  # Negative (interference)
        elif theory == PredictionType.REM:
            return 0.0  # Null (differentiation)
        elif theory == PredictionType.TODAM:
            return -0.10  # Negative
        return 0.0

    def get_theoretical_explanations(
        self
    ) -> Dict[str, str]:
        """Get theoretical explanations."""
        return {
            'sam_prediction': 'Strong compete with weak at retrieval',
            'sam_failure': 'SAM incorrectly predicts negative effect',
            'rem_explanation': 'Differentiation - strong become more distinct',
            'rem_success': 'REM correctly predicts null effect',
            'todam': 'Distributed memory predicts negative'
        }

    def get_key_findings(
        self
    ) -> Dict[str, str]:
        """Get key empirical findings."""
        return {
            'null_effect': 'No list strength effect in most conditions',
            'recall_vs_recognition': 'Sometimes appears in recognition',
            'cued_recall': 'Null effect in cued recall',
            'differentiation': 'Strong items become more distinctive',
            'competition': 'No competition at retrieval'
        }

    def get_model_comparison(
        self
    ) -> Dict[str, Dict[str, Any]]:
        """Compare memory models."""
        return {
            'SAM': {
                'prediction': 'Negative effect',
                'actual': 'Null',
                'status': 'Failed'
            },
            'REM': {
                'prediction': 'Null effect',
                'actual': 'Null',
                'status': 'Confirmed'
            },
            'TODAM': {
                'prediction': 'Negative effect',
                'actual': 'Null',
                'status': 'Failed'
            }
        }


# ============================================================================
# LIST STRENGTH SYSTEM
# ============================================================================

class ListStrengthSystem:
    """
    List strength manipulation system.

    "Ba'el's strength manipulation system." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = ListStrengthModel()

        self._lists: List[StudyList] = []
        self._trials: List[TestTrial] = []

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"item_{self._counter}"

    def create_list(
        self,
        n_strong: int = 10,
        n_weak: int = 10,
        strong_presentations: int = 5
    ) -> StudyList:
        """Create study list."""
        items = []

        # Strong items
        for i in range(n_strong):
            item = ListItem(
                id=self._generate_id(),
                content=f"Strong_{i}",
                strength=ItemStrength.STRONG,
                presentations=strong_presentations,
                encoding_quality=random.uniform(0.6, 0.9)
            )
            items.append(item)

        # Weak items
        for i in range(n_weak):
            item = ListItem(
                id=self._generate_id(),
                content=f"Weak_{i}",
                strength=ItemStrength.WEAK,
                presentations=1,
                encoding_quality=random.uniform(0.4, 0.7)
            )
            items.append(item)

        study_list = StudyList(
            items=items,
            n_strong=n_strong,
            n_weak=n_weak,
            proportion_strong=n_strong / (n_strong + n_weak)
        )

        self._lists.append(study_list)

        return study_list

    def test_item(
        self,
        item: ListItem,
        study_list: StudyList,
        test_type: TestType = TestType.RECALL
    ) -> TestTrial:
        """Test an item."""
        prob = self._model.calculate_recall_probability(
            item, study_list, test_type
        )

        correct = random.random() < prob

        trial = TestTrial(
            item=item,
            test_type=test_type,
            correct=correct,
            latency_ms=random.randint(500, 3000)
        )

        self._trials.append(trial)

        return trial


# ============================================================================
# LIST STRENGTH PARADIGM
# ============================================================================

class ListStrengthParadigm:
    """
    List strength paradigm.

    "Ba'el's strength manipulation study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_classic_paradigm(
        self
    ) -> Dict[str, Any]:
        """Run classic list strength paradigm."""
        # Mixed list (50% strong, 50% weak)
        mixed_system = ListStrengthSystem()
        mixed_list = mixed_system.create_list(n_strong=10, n_weak=10)

        # Pure weak list (all weak)
        pure_system = ListStrengthSystem()
        pure_list = pure_system.create_list(n_strong=0, n_weak=20)

        # Test mixed list
        mixed_strong = []
        mixed_weak = []

        for item in mixed_list.items:
            trial = mixed_system.test_item(item, mixed_list)
            if item.strength == ItemStrength.STRONG:
                mixed_strong.append(trial.correct)
            else:
                mixed_weak.append(trial.correct)

        # Test pure list
        pure_weak = []
        for item in pure_list.items:
            trial = pure_system.test_item(item, pure_list)
            pure_weak.append(trial.correct)

        # Calculate rates
        mixed_strong_rate = sum(mixed_strong) / max(1, len(mixed_strong))
        mixed_weak_rate = sum(mixed_weak) / max(1, len(mixed_weak))
        pure_weak_rate = sum(pure_weak) / max(1, len(pure_weak))

        # List strength effect = Pure weak - Mixed weak
        lse = pure_weak_rate - mixed_weak_rate

        return {
            'mixed_strong': mixed_strong_rate,
            'mixed_weak': mixed_weak_rate,
            'pure_weak': pure_weak_rate,
            'list_strength_effect': lse,
            'interpretation': f'List strength effect: {lse:.0%} (expected ~0)'
        }

    def run_proportion_study(
        self
    ) -> Dict[str, Any]:
        """Study effect of proportion strong."""
        proportions = [0.0, 0.25, 0.50, 0.75]

        results = {}

        for prop in proportions:
            n_total = 20
            n_strong = int(n_total * prop)
            n_weak = n_total - n_strong

            if n_weak == 0:
                continue

            system = ListStrengthSystem()
            study_list = system.create_list(n_strong, n_weak)

            weak_correct = []
            for item in study_list.items:
                if item.strength == ItemStrength.WEAK:
                    trial = system.test_item(item, study_list)
                    weak_correct.append(trial.correct)

            rate = sum(weak_correct) / max(1, len(weak_correct))
            results[f'prop_{int(prop*100)}'] = {'weak_recall': rate}

        return {
            'by_proportion': results,
            'interpretation': 'Weak recall stable across proportions'
        }

    def run_test_type_study(
        self
    ) -> Dict[str, Any]:
        """Study effect across test types."""
        results = {}

        for test_type in TestType:
            system = ListStrengthSystem()
            study_list = system.create_list(n_strong=10, n_weak=10)

            weak_correct = []
            for item in study_list.items:
                if item.strength == ItemStrength.WEAK:
                    trial = system.test_item(item, study_list, test_type)
                    weak_correct.append(trial.correct)

            rate = sum(weak_correct) / max(1, len(weak_correct))
            results[test_type.name] = {'weak_recall': rate}

        return {
            'by_test_type': results,
            'interpretation': 'Null effect across test types'
        }

    def run_theory_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare theoretical predictions."""
        model = ListStrengthModel()

        theories = {}
        for theory in PredictionType:
            prediction = model.calculate_predicted_effect(theory)
            theories[theory.name] = {
                'prediction': prediction,
                'matches_data': abs(prediction) < 0.05
            }

        explanations = model.get_theoretical_explanations()
        comparison = model.get_model_comparison()

        return {
            'by_theory': theories,
            'explanations': explanations,
            'comparison': comparison,
            'interpretation': 'REM explains null effect via differentiation'
        }

    def run_strength_manipulation_study(
        self
    ) -> Dict[str, Any]:
        """Study strength manipulation methods."""
        model = ListStrengthModel()

        results = {}

        presentations_list = [1, 3, 5, 10]

        for n_pres in presentations_list:
            item = ListItem(
                "test", "test",
                ItemStrength.STRONG if n_pres > 1 else ItemStrength.WEAK,
                n_pres, 0.7
            )
            list_info = StudyList([], 1, 1, 0.5)

            prob = model.calculate_recall_probability(item, list_info)
            results[f'presentations_{n_pres}'] = {'recall': prob}

        return {
            'by_presentations': results,
            'interpretation': 'More presentations increase item strength'
        }

    def run_key_findings(
        self
    ) -> Dict[str, Any]:
        """Summarize key findings."""
        model = ListStrengthModel()

        findings = model.get_key_findings()
        explanations = model.get_theoretical_explanations()

        return {
            'findings': findings,
            'explanations': explanations,
            'interpretation': 'Null LSE supports differentiation theory'
        }


# ============================================================================
# LIST STRENGTH ENGINE
# ============================================================================

class ListStrengthEngine:
    """
    Complete list strength engine.

    "Ba'el's strength manipulation engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = ListStrengthParadigm()
        self._system = ListStrengthSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # List operations

    def create_list(
        self,
        n_strong: int = 10,
        n_weak: int = 10
    ) -> StudyList:
        """Create list."""
        return self._system.create_list(n_strong, n_weak)

    def test_item(
        self,
        item: ListItem,
        study_list: StudyList
    ) -> TestTrial:
        """Test item."""
        return self._system.test_item(item, study_list)

    # Experiments

    def run_classic(
        self
    ) -> Dict[str, Any]:
        """Run classic paradigm."""
        result = self._paradigm.run_classic_paradigm()
        self._experiment_results.append(result)
        return result

    def study_proportion(
        self
    ) -> Dict[str, Any]:
        """Study proportion."""
        return self._paradigm.run_proportion_study()

    def study_test_types(
        self
    ) -> Dict[str, Any]:
        """Study test types."""
        return self._paradigm.run_test_type_study()

    def compare_theories(
        self
    ) -> Dict[str, Any]:
        """Compare theories."""
        return self._paradigm.run_theory_comparison()

    def study_strength_methods(
        self
    ) -> Dict[str, Any]:
        """Study strength methods."""
        return self._paradigm.run_strength_manipulation_study()

    def get_key_findings(
        self
    ) -> Dict[str, Any]:
        """Get key findings."""
        return self._paradigm.run_key_findings()

    # Analysis

    def get_metrics(self) -> ListStrengthMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_classic()

        last = self._experiment_results[-1]

        return ListStrengthMetrics(
            strong_recall=last['mixed_strong'],
            weak_recall=last['mixed_weak'],
            list_strength_effect=last['list_strength_effect'],
            predicted_effect=0.0
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'lists': len(self._system._lists),
            'trials': len(self._system._trials)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_list_strength_engine() -> ListStrengthEngine:
    """Create list strength engine."""
    return ListStrengthEngine()


def demonstrate_list_strength() -> Dict[str, Any]:
    """Demonstrate list strength effect."""
    engine = create_list_strength_engine()

    # Classic
    classic = engine.run_classic()

    # Proportion
    proportion = engine.study_proportion()

    # Theories
    theories = engine.compare_theories()

    # Key findings
    findings = engine.get_key_findings()

    return {
        'classic': {
            'mixed_weak': f"{classic['mixed_weak']:.0%}",
            'pure_weak': f"{classic['pure_weak']:.0%}",
            'lse': f"{classic['list_strength_effect']:.0%}"
        },
        'by_proportion': {
            k: f"weak={v['weak_recall']:.0%}"
            for k, v in proportion['by_proportion'].items()
        },
        'theories': {
            k: 'matches' if v['matches_data'] else 'fails'
            for k, v in theories['by_theory'].items()
        },
        'interpretation': (
            f"LSE: {classic['list_strength_effect']:.0%}. "
            f"Null effect: Strong don't hurt weak. "
            f"REM's differentiation explains this."
        )
    }


def get_list_strength_facts() -> Dict[str, str]:
    """Get facts about list strength effect."""
    return {
        'ratcliff_1990': 'Seminal null LSE finding',
        'sam_failure': 'SAM incorrectly predicts negative effect',
        'rem_success': 'REM correctly predicts null effect',
        'differentiation': 'Strong become more distinctive',
        'no_competition': 'No retrieval competition',
        'theoretical': 'Crucial for memory model evaluation',
        'paradigm': 'Mixed vs pure lists',
        'key_finding': 'Strength helps item, doesn\'t hurt others'
    }
