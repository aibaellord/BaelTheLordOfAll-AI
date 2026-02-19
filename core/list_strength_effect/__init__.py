"""
BAEL List Strength Effect Engine
==================================

Strong items impair weak items' recall.
Ratcliff's list strength paradigm.

"Ba'el's strong memories eclipse the weak." — Ba'el
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

logger = logging.getLogger("BAEL.ListStrength")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ItemStrength(Enum):
    """Strength level of item."""
    WEAK = auto()      # Single presentation
    STRONG = auto()    # Multiple presentations


class ListComposition(Enum):
    """List composition type."""
    PURE_WEAK = auto()       # All weak items
    PURE_STRONG = auto()     # All strong items
    MIXED = auto()           # Both weak and strong


class TestType(Enum):
    """Type of memory test."""
    FREE_RECALL = auto()
    CUED_RECALL = auto()
    RECOGNITION = auto()


@dataclass
class StudyItem:
    """
    An item studied with strength manipulation.
    """
    id: str
    content: str
    strength: ItemStrength
    presentations: int
    encoding_strength: float


@dataclass
class ListContext:
    """
    List context for study.
    """
    id: str
    composition: ListComposition
    items: List[str]
    strong_ratio: float


@dataclass
class TestResult:
    """
    Result of memory test.
    """
    item_id: str
    item_strength: ItemStrength
    list_composition: ListComposition
    correctly_retrieved: bool
    response_time_ms: float


@dataclass
class ListStrengthMetrics:
    """
    List strength effect metrics.
    """
    weak_in_pure_list: float
    weak_in_mixed_list: float
    strength_effect: float
    strong_item_rate: float


# ============================================================================
# LIST STRENGTH MODEL
# ============================================================================

class ListStrengthModel:
    """
    Model of list strength effects.

    "Ba'el's competition model." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Encoding parameters
        self._weak_encoding = 0.4
        self._strong_encoding = 0.7
        self._presentation_boost = 0.1

        # Competition parameters
        self._competition_weight = 0.2

        # Retrieval parameters
        self._retrieval_threshold = 0.35

        # Differentiation parameter (for recognition)
        self._differentiation_benefit = 0.1

        self._lock = threading.RLock()

    def calculate_encoding_strength(
        self,
        strength: ItemStrength,
        presentations: int
    ) -> float:
        """Calculate encoding strength."""
        if strength == ItemStrength.WEAK:
            base = self._weak_encoding
        else:
            base = self._strong_encoding

        # Additional presentations boost
        boost = (presentations - 1) * self._presentation_boost

        return min(0.95, base + boost)

    def calculate_retrieval_probability(
        self,
        item: StudyItem,
        list_context: ListContext,
        test_type: TestType = TestType.FREE_RECALL
    ) -> float:
        """Calculate retrieval probability considering list strength."""
        # Base probability from encoding
        prob = item.encoding_strength

        if test_type == TestType.FREE_RECALL:
            # Free recall shows list strength effect
            # Strong items in list compete with weak items

            if item.strength == ItemStrength.WEAK:
                # Weak items suffer from strong items
                competition = list_context.strong_ratio * self._competition_weight
                prob -= competition

        elif test_type == TestType.RECOGNITION:
            # Recognition shows null/reversed effect (differentiation)
            # Strong items make the list more distinctive

            if item.strength == ItemStrength.WEAK:
                # Weak items might BENEFIT from distinctive strong items
                if list_context.strong_ratio > 0:
                    prob += list_context.strong_ratio * self._differentiation_benefit

        return max(0.1, min(0.95, prob))


# ============================================================================
# LIST STRENGTH SYSTEM
# ============================================================================

class ListStrengthSystem:
    """
    List strength experimental system.

    "Ba'el's strength competition system." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = ListStrengthModel()

        self._items: Dict[str, StudyItem] = {}
        self._lists: Dict[str, ListContext] = {}
        self._results: List[TestResult] = []

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"item_{self._counter}"

    def create_item(
        self,
        content: str,
        strength: ItemStrength
    ) -> StudyItem:
        """Create a study item."""
        presentations = 1 if strength == ItemStrength.WEAK else 3

        encoding = self._model.calculate_encoding_strength(strength, presentations)

        item = StudyItem(
            id=self._generate_id(),
            content=content,
            strength=strength,
            presentations=presentations,
            encoding_strength=encoding
        )

        self._items[item.id] = item

        return item

    def create_list(
        self,
        composition: ListComposition,
        n_items: int = 20
    ) -> ListContext:
        """Create a study list."""
        items = []

        if composition == ListComposition.PURE_WEAK:
            for i in range(n_items):
                item = self.create_item(f"weak_{i}", ItemStrength.WEAK)
                items.append(item.id)
            strong_ratio = 0.0

        elif composition == ListComposition.PURE_STRONG:
            for i in range(n_items):
                item = self.create_item(f"strong_{i}", ItemStrength.STRONG)
                items.append(item.id)
            strong_ratio = 1.0

        else:  # MIXED
            half = n_items // 2
            for i in range(half):
                item = self.create_item(f"weak_{i}", ItemStrength.WEAK)
                items.append(item.id)
            for i in range(half):
                item = self.create_item(f"strong_{i}", ItemStrength.STRONG)
                items.append(item.id)
            strong_ratio = 0.5

        list_context = ListContext(
            id=self._generate_id(),
            composition=composition,
            items=items,
            strong_ratio=strong_ratio
        )

        self._lists[list_context.id] = list_context

        return list_context

    def test_item(
        self,
        item_id: str,
        list_id: str,
        test_type: TestType = TestType.FREE_RECALL
    ) -> TestResult:
        """Test an item from a list."""
        item = self._items.get(item_id)
        list_context = self._lists.get(list_id)

        if not item or not list_context:
            return None

        prob = self._model.calculate_retrieval_probability(
            item, list_context, test_type
        )

        success = random.random() < prob
        latency = (1 - prob) * 2000 + 300

        result = TestResult(
            item_id=item_id,
            item_strength=item.strength,
            list_composition=list_context.composition,
            correctly_retrieved=success,
            response_time_ms=latency
        )

        self._results.append(result)

        return result

    def test_list(
        self,
        list_id: str,
        test_type: TestType = TestType.FREE_RECALL
    ) -> List[TestResult]:
        """Test all items in a list."""
        list_context = self._lists.get(list_id)
        if not list_context:
            return []

        results = []
        for item_id in list_context.items:
            result = self.test_item(item_id, list_id, test_type)
            results.append(result)

        return results


# ============================================================================
# LIST STRENGTH PARADIGM
# ============================================================================

class ListStrengthParadigm:
    """
    List strength experimental paradigm.

    "Ba'el's mixed list study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_basic_paradigm(
        self,
        n_items: int = 20,
        n_trials: int = 10
    ) -> Dict[str, Any]:
        """Run basic list strength paradigm."""
        results = {
            'weak_pure': [],
            'weak_mixed': [],
            'strong_mixed': []
        }

        for _ in range(n_trials):
            # Pure weak list
            system1 = ListStrengthSystem()
            pure_weak = system1.create_list(ListComposition.PURE_WEAK, n_items)
            weak_results = system1.test_list(pure_weak.id)

            weak_correct = sum(1 for r in weak_results if r.correctly_retrieved)
            results['weak_pure'].append(weak_correct / len(weak_results))

            # Mixed list
            system2 = ListStrengthSystem()
            mixed = system2.create_list(ListComposition.MIXED, n_items)
            mixed_results = system2.test_list(mixed.id)

            # Separate weak and strong
            weak_in_mixed = [r for r in mixed_results if r.item_strength == ItemStrength.WEAK]
            strong_in_mixed = [r for r in mixed_results if r.item_strength == ItemStrength.STRONG]

            if weak_in_mixed:
                results['weak_mixed'].append(
                    sum(1 for r in weak_in_mixed if r.correctly_retrieved) / len(weak_in_mixed)
                )
            if strong_in_mixed:
                results['strong_mixed'].append(
                    sum(1 for r in strong_in_mixed if r.correctly_retrieved) / len(strong_in_mixed)
                )

        # Calculate averages
        avg_weak_pure = sum(results['weak_pure']) / len(results['weak_pure'])
        avg_weak_mixed = sum(results['weak_mixed']) / len(results['weak_mixed'])
        avg_strong_mixed = sum(results['strong_mixed']) / len(results['strong_mixed'])

        return {
            'weak_in_pure_list': avg_weak_pure,
            'weak_in_mixed_list': avg_weak_mixed,
            'strong_in_mixed_list': avg_strong_mixed,
            'list_strength_effect': avg_weak_pure - avg_weak_mixed
        }

    def run_recognition_study(
        self,
        n_items: int = 20,
        n_trials: int = 10
    ) -> Dict[str, Any]:
        """Run recognition test (should show null/reversed effect)."""
        results = {
            'weak_pure': [],
            'weak_mixed': []
        }

        for _ in range(n_trials):
            # Pure weak list - recognition
            system1 = ListStrengthSystem()
            pure_weak = system1.create_list(ListComposition.PURE_WEAK, n_items)
            weak_results = system1.test_list(pure_weak.id, TestType.RECOGNITION)

            weak_correct = sum(1 for r in weak_results if r.correctly_retrieved)
            results['weak_pure'].append(weak_correct / len(weak_results))

            # Mixed list - recognition
            system2 = ListStrengthSystem()
            mixed = system2.create_list(ListComposition.MIXED, n_items)
            mixed_results = system2.test_list(mixed.id, TestType.RECOGNITION)

            weak_in_mixed = [r for r in mixed_results if r.item_strength == ItemStrength.WEAK]
            if weak_in_mixed:
                results['weak_mixed'].append(
                    sum(1 for r in weak_in_mixed if r.correctly_retrieved) / len(weak_in_mixed)
                )

        avg_weak_pure = sum(results['weak_pure']) / len(results['weak_pure'])
        avg_weak_mixed = sum(results['weak_mixed']) / len(results['weak_mixed'])

        return {
            'weak_in_pure_recognition': avg_weak_pure,
            'weak_in_mixed_recognition': avg_weak_mixed,
            'recognition_effect': avg_weak_mixed - avg_weak_pure,  # Should be null or positive
            'interpretation': 'Recognition shows null or reversed effect (differentiation)'
        }

    def run_strong_ratio_manipulation(
        self
    ) -> Dict[str, Any]:
        """Manipulate the proportion of strong items."""
        ratios = [0.0, 0.25, 0.5, 0.75, 1.0]
        results = {}

        for ratio in ratios:
            system = ListStrengthSystem()

            # Create custom mixed list
            n_items = 20
            n_strong = int(n_items * ratio)
            n_weak = n_items - n_strong

            items = []
            for i in range(n_weak):
                item = system.create_item(f"weak_{i}", ItemStrength.WEAK)
                items.append(item.id)
            for i in range(n_strong):
                item = system.create_item(f"strong_{i}", ItemStrength.STRONG)
                items.append(item.id)

            list_context = ListContext(
                id=system._generate_id(),
                composition=ListComposition.MIXED if 0 < ratio < 1 else (
                    ListComposition.PURE_WEAK if ratio == 0 else ListComposition.PURE_STRONG
                ),
                items=items,
                strong_ratio=ratio
            )
            system._lists[list_context.id] = list_context

            # Test weak items only
            weak_results = []
            for item_id in items[:n_weak]:
                result = system.test_item(item_id, list_context.id)
                weak_results.append(result)

            if weak_results:
                recall = sum(1 for r in weak_results if r.correctly_retrieved) / len(weak_results)
            else:
                recall = None

            results[f"ratio_{ratio}"] = {
                'strong_ratio': ratio,
                'weak_recall': recall
            }

        return results

    def run_presentation_study(
        self
    ) -> Dict[str, Any]:
        """Study effect of number of presentations."""
        presentation_counts = [1, 2, 3, 5]
        results = {}

        for presentations in presentation_counts:
            system = ListStrengthSystem()

            # Modify strong item presentations
            system._model._presentation_boost = 0.08

            items = []
            for i in range(10):
                item = system.create_item(f"item_{i}", ItemStrength.STRONG)
                item.presentations = presentations
                item.encoding_strength = system._model.calculate_encoding_strength(
                    ItemStrength.STRONG, presentations
                )
                items.append(item)

            list_context = ListContext(
                id=system._generate_id(),
                composition=ListComposition.PURE_STRONG,
                items=[i.id for i in items],
                strong_ratio=1.0
            )
            system._lists[list_context.id] = list_context

            test_results = system.test_list(list_context.id)
            recall = sum(1 for r in test_results if r.correctly_retrieved) / len(test_results)

            results[f"presentations_{presentations}"] = recall

        return results


# ============================================================================
# LIST STRENGTH ENGINE
# ============================================================================

class ListStrengthEngine:
    """
    Complete list strength engine.

    "Ba'el's strength competition engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = ListStrengthParadigm()
        self._system = ListStrengthSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Item/List management

    def create_item(
        self,
        content: str,
        strength: ItemStrength
    ) -> StudyItem:
        """Create an item."""
        return self._system.create_item(content, strength)

    def create_list(
        self,
        composition: ListComposition,
        n_items: int = 20
    ) -> ListContext:
        """Create a list."""
        return self._system.create_list(composition, n_items)

    def test_list(
        self,
        list_id: str,
        test_type: TestType = TestType.FREE_RECALL
    ) -> List[TestResult]:
        """Test a list."""
        return self._system.test_list(list_id, test_type)

    # Experiments

    def run_basic_experiment(
        self
    ) -> Dict[str, Any]:
        """Run basic experiment."""
        result = self._paradigm.run_basic_paradigm()
        self._experiment_results.append(result)
        return result

    def study_recognition(
        self
    ) -> Dict[str, Any]:
        """Study recognition test."""
        return self._paradigm.run_recognition_study()

    def study_strong_ratio(
        self
    ) -> Dict[str, Any]:
        """Study strong item ratio."""
        return self._paradigm.run_strong_ratio_manipulation()

    def study_presentations(
        self
    ) -> Dict[str, Any]:
        """Study number of presentations."""
        return self._paradigm.run_presentation_study()

    def compare_recall_recognition(
        self
    ) -> Dict[str, Any]:
        """Compare recall vs recognition."""
        recall = self.run_basic_experiment()
        recog = self.study_recognition()

        return {
            'recall': {
                'weak_pure': recall['weak_in_pure_list'],
                'weak_mixed': recall['weak_in_mixed_list'],
                'effect': recall['list_strength_effect']
            },
            'recognition': {
                'weak_pure': recog['weak_in_pure_recognition'],
                'weak_mixed': recog['weak_in_mixed_recognition'],
                'effect': recog['recognition_effect']
            },
            'interpretation': 'Recall shows list strength effect; recognition does not'
        }

    # Analysis

    def get_metrics(self) -> ListStrengthMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_basic_experiment()

        last = self._experiment_results[-1]

        return ListStrengthMetrics(
            weak_in_pure_list=last['weak_in_pure_list'],
            weak_in_mixed_list=last['weak_in_mixed_list'],
            strength_effect=last['list_strength_effect'],
            strong_item_rate=last['strong_in_mixed_list']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'items': len(self._system._items),
            'lists': len(self._system._lists),
            'results': len(self._system._results)
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

    # Basic experiment
    basic = engine.run_basic_experiment()

    # Recognition
    recog = engine.study_recognition()

    # Strong ratio
    ratio = engine.study_strong_ratio()

    # Compare
    compare = engine.compare_recall_recognition()

    return {
        'recall_test': {
            'weak_pure': f"{basic['weak_in_pure_list']:.0%}",
            'weak_mixed': f"{basic['weak_in_mixed_list']:.0%}",
            'strong_mixed': f"{basic['strong_in_mixed_list']:.0%}",
            'effect': f"{basic['list_strength_effect']:.0%}"
        },
        'recognition_test': {
            'weak_pure': f"{recog['weak_in_pure_recognition']:.0%}",
            'weak_mixed': f"{recog['weak_in_mixed_recognition']:.0%}",
            'effect': f"{recog['recognition_effect']:.0%}"
        },
        'by_strong_ratio': {
            k: f"{v['weak_recall']:.0%}" if v['weak_recall'] else 'N/A'
            for k, v in ratio.items()
        },
        'interpretation': (
            f"List strength effect: {basic['list_strength_effect']:.0%}. "
            f"Strong items impair weak item recall but not recognition."
        )
    }


def get_list_strength_facts() -> Dict[str, str]:
    """Get facts about list strength effect."""
    return {
        'ratcliff_1990': 'SAM model predictions and testing',
        'recall_vs_recognition': 'Effect in recall but not recognition',
        'competition': 'Strong items compete for retrieval resources',
        'differentiation': 'Recognition benefits from distinctiveness',
        'presentations': 'More presentations = stronger item',
        'practical': 'Study all material equally for best recall'
    }
