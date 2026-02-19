"""
BAEL Hypermnesia Engine
=========================

Increased recall over repeated testing.
Erdelyi & Becker's hypermnesia phenomenon.

"Ba'el's memory grows stronger with use." — Ba'el
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

logger = logging.getLogger("BAEL.Hypermnesia")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class MaterialType(Enum):
    """Type of studied material."""
    PICTURES = auto()
    WORDS = auto()
    STORIES = auto()
    SENTENCES = auto()


class RecallType(Enum):
    """Type of recall test."""
    FREE_RECALL = auto()
    CUED_RECALL = auto()


class ChangeType(Enum):
    """Type of memory change across tests."""
    REMINISCENCE = auto()      # Newly recalled
    INTERTEST_FORGETTING = auto()  # Previously recalled, now forgotten
    STABLE_RECALL = auto()     # Recalled on both tests


@dataclass
class StudyItem:
    """
    An item to study.
    """
    id: str
    content: str
    material_type: MaterialType
    encoding_strength: float


@dataclass
class RecallTrial:
    """
    A recall trial result.
    """
    test_number: int
    recalled_ids: Set[str]
    recall_order: List[str]
    duration_seconds: float


@dataclass
class ItemHistory:
    """
    History of recall for an item.
    """
    item_id: str
    tests_recalled: List[int]
    first_recall_test: Optional[int]
    reminiscence_test: Optional[int]


@dataclass
class HypermnesiaMetrics:
    """
    Hypermnesia metrics.
    """
    test1_recall: int
    test2_recall: int
    test3_recall: int
    net_hypermnesia: int
    reminiscence_count: int
    forgetting_count: int
    cumulative_recall: int


# ============================================================================
# RETRIEVAL IMPROVEMENT MODEL
# ============================================================================

class RetrievalImprovementModel:
    """
    Model of retrieval improvement across tests.

    "Ba'el's growing recall." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Retrieval parameters
        self._base_recall_prob = 0.4

        # Across-test improvement
        self._retrieval_practice_boost = 0.15

        # Material effects
        self._material_imagability = {
            MaterialType.PICTURES: 0.8,
            MaterialType.WORDS: 0.4,
            MaterialType.STORIES: 0.6,
            MaterialType.SENTENCES: 0.5
        }

        # Hypermnesia is stronger for imagable material
        self._imagery_hypermnesia_factor = 1.5

        # Reminiscence vs forgetting balance
        self._base_reminiscence_rate = 0.12
        self._base_forgetting_rate = 0.08

        self._lock = threading.RLock()

    def calculate_recall_probability(
        self,
        item: StudyItem,
        test_number: int,
        previously_recalled: bool
    ) -> float:
        """Calculate recall probability for a test."""
        # Base probability from encoding
        prob = self._base_recall_prob * item.encoding_strength

        # Imagability effect
        imagability = self._material_imagability.get(item.material_type, 0.5)
        prob *= (0.7 + imagability * 0.6)

        # Test number effect
        if test_number > 1:
            # Retrieval practice improves access
            boost = self._retrieval_practice_boost * (test_number - 1)
            prob += boost

            # But stronger for imagable items
            if imagability > 0.5:
                prob += boost * (self._imagery_hypermnesia_factor - 1)

        # Previously recalled items more likely to be recalled again
        if previously_recalled:
            prob *= 1.3

        return min(0.95, max(0.05, prob))

    def calculate_reminiscence_probability(
        self,
        item: StudyItem,
        test_number: int
    ) -> float:
        """Calculate probability of reminiscence (new recall)."""
        # Base reminiscence rate
        prob = self._base_reminiscence_rate

        # Imagability increases reminiscence
        imagability = self._material_imagability.get(item.material_type, 0.5)
        prob *= (0.5 + imagability)

        # More tests = more opportunity for reminiscence
        prob *= (1 + 0.1 * (test_number - 1))

        # But diminishing returns
        prob *= 0.9 ** (test_number - 1)

        return min(0.3, prob)

    def calculate_forgetting_probability(
        self,
        item: StudyItem,
        test_number: int
    ) -> float:
        """Calculate probability of intertest forgetting."""
        # Base forgetting rate
        prob = self._base_forgetting_rate

        # Imagable items less likely to be forgotten
        imagability = self._material_imagability.get(item.material_type, 0.5)
        prob *= (1.2 - imagability * 0.4)

        # Later tests = less forgetting (consolidation)
        prob *= 0.8 ** (test_number - 1)

        return max(0.02, prob)


# ============================================================================
# HYPERMNESIA SYSTEM
# ============================================================================

class HypermnesiaSystem:
    """
    Hypermnesia experimental system.

    "Ba'el's recall growth system." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = RetrievalImprovementModel()

        self._items: Dict[str, StudyItem] = {}
        self._trials: List[RecallTrial] = []
        self._item_histories: Dict[str, ItemHistory] = {}

        self._item_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._item_counter += 1
        return f"item_{self._item_counter}"

    def study_item(
        self,
        content: str,
        material_type: MaterialType = MaterialType.WORDS
    ) -> StudyItem:
        """Study an item."""
        item = StudyItem(
            id=self._generate_id(),
            content=content,
            material_type=material_type,
            encoding_strength=random.uniform(0.4, 0.9)
        )

        self._items[item.id] = item
        self._item_histories[item.id] = ItemHistory(
            item_id=item.id,
            tests_recalled=[],
            first_recall_test=None,
            reminiscence_test=None
        )

        return item

    def run_recall_test(
        self,
        duration_seconds: float = 60.0
    ) -> RecallTrial:
        """Run a recall test."""
        test_number = len(self._trials) + 1

        recalled_ids = set()
        recall_order = []

        for item_id, item in self._items.items():
            history = self._item_histories[item_id]
            previously_recalled = len(history.tests_recalled) > 0

            if previously_recalled:
                # Check for intertest forgetting
                forget_prob = self._model.calculate_forgetting_probability(
                    item, test_number
                )
                if random.random() < forget_prob:
                    continue  # Forgotten on this test

                # Previously recalled - likely to recall again
                recall_prob = self._model.calculate_recall_probability(
                    item, test_number, True
                )
            else:
                # Check for reminiscence
                remin_prob = self._model.calculate_reminiscence_probability(
                    item, test_number
                )
                recall_prob = self._model.calculate_recall_probability(
                    item, test_number, False
                )
                recall_prob = max(recall_prob, remin_prob)

            if random.random() < recall_prob:
                recalled_ids.add(item_id)
                recall_order.append(item_id)

                # Update history
                history.tests_recalled.append(test_number)

                if history.first_recall_test is None:
                    history.first_recall_test = test_number
                elif test_number > 1 and test_number not in history.tests_recalled[:-1]:
                    history.reminiscence_test = test_number

        trial = RecallTrial(
            test_number=test_number,
            recalled_ids=recalled_ids,
            recall_order=recall_order,
            duration_seconds=duration_seconds
        )

        self._trials.append(trial)

        return trial

    def get_cumulative_recall(self) -> Set[str]:
        """Get all items ever recalled across tests."""
        cumulative = set()
        for trial in self._trials:
            cumulative.update(trial.recalled_ids)
        return cumulative

    def count_reminiscences(self, from_test: int, to_test: int) -> int:
        """Count items recalled on to_test but not from_test."""
        if from_test > len(self._trials) or to_test > len(self._trials):
            return 0

        from_recalled = self._trials[from_test - 1].recalled_ids
        to_recalled = self._trials[to_test - 1].recalled_ids

        return len(to_recalled - from_recalled)

    def count_forgettings(self, from_test: int, to_test: int) -> int:
        """Count items recalled on from_test but not to_test."""
        if from_test > len(self._trials) or to_test > len(self._trials):
            return 0

        from_recalled = self._trials[from_test - 1].recalled_ids
        to_recalled = self._trials[to_test - 1].recalled_ids

        return len(from_recalled - to_recalled)


# ============================================================================
# HYPERMNESIA PARADIGM
# ============================================================================

class HypermnesiaParadigm:
    """
    Hypermnesia experimental paradigm.

    "Ba'el's recall improvement study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_basic_experiment(
        self,
        n_items: int = 40,
        n_tests: int = 3,
        material: MaterialType = MaterialType.PICTURES
    ) -> Dict[str, Any]:
        """Run basic hypermnesia experiment."""
        system = HypermnesiaSystem()

        # Study phase
        for i in range(n_items):
            system.study_item(f"item_{i}", material)

        # Test phases
        recalls_per_test = []
        for _ in range(n_tests):
            trial = system.run_recall_test(60.0)
            recalls_per_test.append(len(trial.recalled_ids))

        # Calculate metrics
        cumulative = len(system.get_cumulative_recall())

        reminiscences_1_2 = system.count_reminiscences(1, 2)
        reminiscences_2_3 = system.count_reminiscences(2, 3)

        forgettings_1_2 = system.count_forgettings(1, 2)
        forgettings_2_3 = system.count_forgettings(2, 3)

        net_hypermnesia = recalls_per_test[-1] - recalls_per_test[0]

        return {
            'material': material.name,
            'n_items': n_items,
            'n_tests': n_tests,
            'recalls_per_test': recalls_per_test,
            'cumulative_recall': cumulative,
            'net_hypermnesia': net_hypermnesia,
            'reminiscences': reminiscences_1_2 + reminiscences_2_3,
            'forgettings': forgettings_1_2 + forgettings_2_3
        }

    def run_material_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare hypermnesia across material types."""
        results = {}

        for material in MaterialType:
            system = HypermnesiaSystem()

            for i in range(30):
                system.study_item(f"item_{i}", material)

            recalls = []
            for _ in range(3):
                trial = system.run_recall_test()
                recalls.append(len(trial.recalled_ids))

            hypermnesia = recalls[-1] - recalls[0]

            results[material.name] = {
                'test1': recalls[0],
                'test3': recalls[-1],
                'hypermnesia': hypermnesia
            }

        return results

    def run_forced_vs_free_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare forced recall vs free recall."""
        # Forced recall (criterion raised) shows more hypermnesia

        results = {}

        # Free recall
        system = HypermnesiaSystem()
        for i in range(30):
            system.study_item(f"item_{i}", MaterialType.PICTURES)

        free_recalls = []
        for _ in range(3):
            trial = system.run_recall_test()
            free_recalls.append(len(trial.recalled_ids))

        results['free_recall'] = {
            'recalls': free_recalls,
            'hypermnesia': free_recalls[-1] - free_recalls[0]
        }

        # Forced recall (higher baseline, less room to grow)
        system = HypermnesiaSystem()
        for i in range(30):
            item = system.study_item(f"item_{i}", MaterialType.PICTURES)
            item.encoding_strength = min(0.95, item.encoding_strength + 0.2)  # Stronger encoding

        forced_recalls = []
        for _ in range(3):
            trial = system.run_recall_test()
            forced_recalls.append(len(trial.recalled_ids))

        results['forced_recall'] = {
            'recalls': forced_recalls,
            'hypermnesia': forced_recalls[-1] - forced_recalls[0]
        }

        return results

    def run_reminiscence_analysis(
        self
    ) -> Dict[str, Any]:
        """Detailed reminiscence analysis."""
        system = HypermnesiaSystem()

        for i in range(40):
            system.study_item(f"item_{i}", MaterialType.PICTURES)

        # Run multiple tests
        for _ in range(5):
            system.run_recall_test()

        # Analyze reminiscence patterns
        reminiscence_counts = []
        forgetting_counts = []

        for i in range(1, 5):
            remin = system.count_reminiscences(i, i + 1)
            forget = system.count_forgettings(i, i + 1)
            reminiscence_counts.append(remin)
            forgetting_counts.append(forget)

        return {
            'test_transitions': ['1->2', '2->3', '3->4', '4->5'],
            'reminiscences': reminiscence_counts,
            'forgettings': forgetting_counts,
            'net_changes': [r - f for r, f in zip(reminiscence_counts, forgetting_counts)],
            'total_reminiscence': sum(reminiscence_counts),
            'total_forgetting': sum(forgetting_counts)
        }


# ============================================================================
# HYPERMNESIA ENGINE
# ============================================================================

class HypermnesiaEngine:
    """
    Complete hypermnesia engine.

    "Ba'el's recall growth engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = HypermnesiaParadigm()
        self._system = HypermnesiaSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Item management

    def study(
        self,
        content: str,
        material: MaterialType = MaterialType.WORDS
    ) -> StudyItem:
        """Study an item."""
        return self._system.study_item(content, material)

    def test(
        self,
        duration: float = 60.0
    ) -> RecallTrial:
        """Run recall test."""
        return self._system.run_recall_test(duration)

    def get_cumulative(self) -> Set[str]:
        """Get cumulative recall."""
        return self._system.get_cumulative_recall()

    # Experiments

    def run_basic_experiment(
        self,
        n_items: int = 40,
        n_tests: int = 3,
        material: MaterialType = MaterialType.PICTURES
    ) -> Dict[str, Any]:
        """Run basic experiment."""
        result = self._paradigm.run_basic_experiment(n_items, n_tests, material)
        self._experiment_results.append(result)
        return result

    def compare_materials(
        self
    ) -> Dict[str, Any]:
        """Compare material types."""
        return self._paradigm.run_material_comparison()

    def compare_recall_types(
        self
    ) -> Dict[str, Any]:
        """Compare forced vs free recall."""
        return self._paradigm.run_forced_vs_free_comparison()

    def analyze_reminiscence(
        self
    ) -> Dict[str, Any]:
        """Analyze reminiscence patterns."""
        return self._paradigm.run_reminiscence_analysis()

    def run_many_tests(
        self,
        n_tests: int = 10
    ) -> Dict[str, Any]:
        """Run many repeated tests."""
        system = HypermnesiaSystem()

        for i in range(30):
            system.study_item(f"item_{i}", MaterialType.PICTURES)

        recalls = []
        for _ in range(n_tests):
            trial = system.run_recall_test()
            recalls.append(len(trial.recalled_ids))

        return {
            'n_tests': n_tests,
            'recalls': recalls,
            'total_hypermnesia': recalls[-1] - recalls[0],
            'cumulative': len(system.get_cumulative_recall()),
            'asymptote_approach': 'Recall approaches cumulative with more tests'
        }

    # Analysis

    def get_metrics(self) -> HypermnesiaMetrics:
        """Get hypermnesia metrics."""
        if not self._experiment_results:
            self.run_basic_experiment()

        last = self._experiment_results[-1]

        return HypermnesiaMetrics(
            test1_recall=last['recalls_per_test'][0],
            test2_recall=last['recalls_per_test'][1] if len(last['recalls_per_test']) > 1 else 0,
            test3_recall=last['recalls_per_test'][-1],
            net_hypermnesia=last['net_hypermnesia'],
            reminiscence_count=last['reminiscences'],
            forgetting_count=last['forgettings'],
            cumulative_recall=last['cumulative_recall']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'items': len(self._system._items),
            'tests': len(self._system._trials),
            'experiments': len(self._experiment_results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_hypermnesia_engine() -> HypermnesiaEngine:
    """Create hypermnesia engine."""
    return HypermnesiaEngine()


def demonstrate_hypermnesia() -> Dict[str, Any]:
    """Demonstrate hypermnesia."""
    engine = create_hypermnesia_engine()

    # Basic experiment
    basic = engine.run_basic_experiment(40, 3, MaterialType.PICTURES)

    # Material comparison
    materials = engine.compare_materials()

    # Reminiscence analysis
    reminiscence = engine.analyze_reminiscence()

    # Many tests
    many = engine.run_many_tests(7)

    return {
        'hypermnesia': {
            'test1': basic['recalls_per_test'][0],
            'test2': basic['recalls_per_test'][1],
            'test3': basic['recalls_per_test'][2],
            'net_hypermnesia': basic['net_hypermnesia'],
            'cumulative': basic['cumulative_recall']
        },
        'by_material': {
            mat: f"hypermnesia: {data['hypermnesia']}"
            for mat, data in materials.items()
        },
        'reminiscence': {
            'total_reminiscence': reminiscence['total_reminiscence'],
            'total_forgetting': reminiscence['total_forgetting'],
            'net_changes': reminiscence['net_changes']
        },
        'many_tests': {
            'recalls': many['recalls'],
            'asymptote': many['cumulative']
        },
        'interpretation': (
            f"Hypermnesia: {basic['net_hypermnesia']} items. "
            f"Reminiscence ({basic['reminiscences']}) exceeds forgetting ({basic['forgettings']})."
        )
    }


def get_hypermnesia_facts() -> Dict[str, str]:
    """Get facts about hypermnesia."""
    return {
        'erdelyi_becker_1974': 'Hypermnesia discovery with pictures',
        'pictures_best': 'Imagable material shows most hypermnesia',
        'reminiscence_forgetting': 'Hypermnesia = reminiscence > forgetting',
        'cumulative': 'Individual test < cumulative recall',
        'retrieval_practice': 'Each test improves retrieval routes',
        'forced_recall': 'Forced criterion shows more hypermnesia',
        'eyewitness': 'Multiple interviews can improve recall',
        'asymptote': 'Recall approaches cumulative with more tests'
    }
