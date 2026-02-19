"""
BAEL Directed Forgetting Engine
=================================

Intentional forgetting via instruction to forget.
Bjork's directed forgetting paradigm.

"Ba'el forgets on command." — Ba'el
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

logger = logging.getLogger("BAEL.DirectedForgetting")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class InstructionType(Enum):
    """Types of memory instructions."""
    REMEMBER = auto()
    FORGET = auto()


class ParadigmType(Enum):
    """Directed forgetting paradigm types."""
    ITEM_METHOD = auto()      # Instruction after each item
    LIST_METHOD = auto()       # Instruction after entire list


class ForgettingMechanism(Enum):
    """Mechanisms of directed forgetting."""
    RETRIEVAL_INHIBITION = auto()  # Items inhibited at retrieval
    SELECTIVE_REHEARSAL = auto()   # Items not rehearsed
    CONTEXT_CHANGE = auto()        # Mental context reset


@dataclass
class StudyItem:
    """
    An item to be studied.
    """
    id: str
    word: str
    list_position: int
    instruction: InstructionType
    encoding_strength: float


@dataclass
class RecallResult:
    """
    Recall test result.
    """
    item_id: str
    instruction: InstructionType
    recalled: bool
    intrusion: bool  # Did a forget item intrude?


@dataclass
class RecognitionResult:
    """
    Recognition test result.
    """
    item_id: str
    instruction: InstructionType
    hit: bool
    confidence: float


@dataclass
class DirectedForgettingMetrics:
    """
    Directed forgetting metrics.
    """
    remember_recall: float
    forget_recall: float
    directed_forgetting_effect: float
    cost_to_forget: float


# ============================================================================
# DIRECTED FORGETTING MODEL
# ============================================================================

class DirectedForgettingModel:
    """
    Model of directed forgetting mechanisms.

    "Ba'el's intentional forgetting." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Encoding parameters
        self._base_encoding = 0.5
        self._remember_boost = 0.25
        self._forget_reduction = 0.2

        # Retrieval parameters
        self._remember_access = 0.7
        self._forget_access = 0.35

        # Method-specific parameters
        self._item_method_effect = 0.25  # Selective rehearsal
        self._list_method_effect = 0.20  # Retrieval inhibition

        self._lock = threading.RLock()

    def calculate_encoding_strength(
        self,
        instruction: InstructionType,
        paradigm: ParadigmType
    ) -> float:
        """Calculate encoding strength based on instruction."""
        strength = self._base_encoding

        if paradigm == ParadigmType.ITEM_METHOD:
            # Instruction comes after each item
            if instruction == InstructionType.REMEMBER:
                strength += self._remember_boost
            else:
                strength -= self._forget_reduction
        else:
            # List method - encoding same initially
            strength = self._base_encoding

        return max(0.1, min(0.9, strength))

    def calculate_retrieval_probability(
        self,
        item: StudyItem,
        paradigm: ParadigmType
    ) -> float:
        """Calculate retrieval probability."""
        if paradigm == ParadigmType.ITEM_METHOD:
            # Selective rehearsal - encoding difference
            if item.instruction == InstructionType.REMEMBER:
                prob = self._remember_access
            else:
                prob = self._forget_access

            prob *= item.encoding_strength
        else:
            # List method - retrieval inhibition
            if item.instruction == InstructionType.REMEMBER:
                prob = self._remember_access
            else:
                prob = self._forget_access * 0.8  # Extra inhibition

        return min(0.95, max(0.1, prob))

    def calculate_recognition_probability(
        self,
        item: StudyItem,
        paradigm: ParadigmType
    ) -> float:
        """Calculate recognition probability."""
        # Recognition less affected than recall
        if item.instruction == InstructionType.REMEMBER:
            prob = 0.8
        else:
            if paradigm == ParadigmType.ITEM_METHOD:
                prob = 0.6  # Weaker encoding
            else:
                prob = 0.65  # Inhibition, not encoding

        return min(0.95, max(0.2, prob))


# ============================================================================
# DIRECTED FORGETTING SYSTEM
# ============================================================================

class DirectedForgettingSystem:
    """
    Directed forgetting experimental system.

    "Ba'el's forget instruction system." — Ba'el
    """

    def __init__(
        self,
        paradigm: ParadigmType = ParadigmType.ITEM_METHOD
    ):
        """Initialize system."""
        self._model = DirectedForgettingModel()
        self._paradigm = paradigm

        self._items: Dict[str, StudyItem] = {}
        self._recall_results: List[RecallResult] = []
        self._recognition_results: List[RecognitionResult] = []

        self._item_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._item_counter += 1
        return f"item_{self._item_counter}"

    def present_item(
        self,
        word: str,
        instruction: InstructionType
    ) -> StudyItem:
        """Present an item with instruction."""
        encoding_strength = self._model.calculate_encoding_strength(
            instruction, self._paradigm
        )

        item = StudyItem(
            id=self._generate_id(),
            word=word,
            list_position=len(self._items),
            instruction=instruction,
            encoding_strength=encoding_strength
        )

        self._items[item.id] = item

        return item

    def test_recall(
        self,
        item_id: str
    ) -> RecallResult:
        """Test recall of an item."""
        item = self._items.get(item_id)
        if not item:
            return None

        prob = self._model.calculate_retrieval_probability(
            item, self._paradigm
        )

        recalled = random.random() < prob

        result = RecallResult(
            item_id=item_id,
            instruction=item.instruction,
            recalled=recalled,
            intrusion=False
        )

        self._recall_results.append(result)

        return result

    def test_recognition(
        self,
        item_id: str
    ) -> RecognitionResult:
        """Test recognition of an item."""
        item = self._items.get(item_id)
        if not item:
            return None

        prob = self._model.calculate_recognition_probability(
            item, self._paradigm
        )

        hit = random.random() < prob

        result = RecognitionResult(
            item_id=item_id,
            instruction=item.instruction,
            hit=hit,
            confidence=prob * random.uniform(0.8, 1.0)
        )

        self._recognition_results.append(result)

        return result


# ============================================================================
# EXPERIMENTAL PARADIGM
# ============================================================================

class DirectedForgettingParadigm:
    """
    Directed forgetting experimental paradigm.

    "Ba'el's forget instruction study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_item_method_experiment(
        self,
        n_items: int = 20
    ) -> Dict[str, Any]:
        """Run item-method directed forgetting."""
        system = DirectedForgettingSystem(ParadigmType.ITEM_METHOD)

        words = [f"word_{i}" for i in range(n_items)]
        random.shuffle(words)

        remember_items = []
        forget_items = []

        for i, word in enumerate(words):
            if i % 2 == 0:
                instruction = InstructionType.REMEMBER
            else:
                instruction = InstructionType.FORGET

            item = system.present_item(word, instruction)

            if instruction == InstructionType.REMEMBER:
                remember_items.append(item)
            else:
                forget_items.append(item)

        # Test all items (despite instruction)
        remember_recalled = sum(1 for item in remember_items
                               if system.test_recall(item.id).recalled)
        forget_recalled = sum(1 for item in forget_items
                             if system.test_recall(item.id).recalled)

        n_r = len(remember_items)
        n_f = len(forget_items)

        return {
            'paradigm': 'item_method',
            'remember_recall': remember_recalled / n_r if n_r > 0 else 0,
            'forget_recall': forget_recalled / n_f if n_f > 0 else 0,
            'df_effect': (remember_recalled / n_r if n_r > 0 else 0) - (forget_recalled / n_f if n_f > 0 else 0)
        }

    def run_list_method_experiment(
        self,
        n_items: int = 20
    ) -> Dict[str, Any]:
        """Run list-method directed forgetting."""
        system = DirectedForgettingSystem(ParadigmType.LIST_METHOD)

        words = [f"word_{i}" for i in range(n_items)]

        # First list - to be forgotten
        forget_items = []
        for word in words[:n_items // 2]:
            item = system.present_item(word, InstructionType.FORGET)
            forget_items.append(item)

        # Forget instruction given here

        # Second list - to be remembered
        remember_items = []
        for word in words[n_items // 2:]:
            item = system.present_item(word, InstructionType.REMEMBER)
            remember_items.append(item)

        # Test
        remember_recalled = sum(1 for item in remember_items
                               if system.test_recall(item.id).recalled)
        forget_recalled = sum(1 for item in forget_items
                             if system.test_recall(item.id).recalled)

        n_r = len(remember_items)
        n_f = len(forget_items)

        return {
            'paradigm': 'list_method',
            'remember_recall': remember_recalled / n_r if n_r > 0 else 0,
            'forget_recall': forget_recalled / n_f if n_f > 0 else 0,
            'df_effect': (remember_recalled / n_r if n_r > 0 else 0) - (forget_recalled / n_f if n_f > 0 else 0)
        }

    def run_recognition_test(
        self,
        paradigm: ParadigmType
    ) -> Dict[str, Any]:
        """Test recognition instead of recall."""
        system = DirectedForgettingSystem(paradigm)

        words = [f"word_{i}" for i in range(20)]

        remember_items = []
        forget_items = []

        for i, word in enumerate(words):
            instruction = InstructionType.REMEMBER if i % 2 == 0 else InstructionType.FORGET
            item = system.present_item(word, instruction)

            if instruction == InstructionType.REMEMBER:
                remember_items.append(item)
            else:
                forget_items.append(item)

        remember_hits = sum(1 for item in remember_items
                          if system.test_recognition(item.id).hit)
        forget_hits = sum(1 for item in forget_items
                        if system.test_recognition(item.id).hit)

        return {
            'paradigm': paradigm.name,
            'remember_recognition': remember_hits / 10,
            'forget_recognition': forget_hits / 10,
            'recognition_effect': (remember_hits - forget_hits) / 10
        }

    def compare_methods(
        self
    ) -> Dict[str, Any]:
        """Compare item vs list method."""
        item_result = self.run_item_method_experiment(20)
        list_result = self.run_list_method_experiment(20)

        return {
            'item_method': item_result,
            'list_method': list_result,
            'comparison': {
                'item_effect': item_result['df_effect'],
                'list_effect': list_result['df_effect'],
                'interpretation': 'Item method: selective rehearsal. List method: retrieval inhibition.'
            }
        }


# ============================================================================
# DIRECTED FORGETTING ENGINE
# ============================================================================

class DirectedForgettingEngine:
    """
    Complete directed forgetting engine.

    "Ba'el's intentional forgetting engine." — Ba'el
    """

    def __init__(
        self,
        paradigm: ParadigmType = ParadigmType.ITEM_METHOD
    ):
        """Initialize engine."""
        self._paradigm_runner = DirectedForgettingParadigm()
        self._system = DirectedForgettingSystem(paradigm)

        self._current_paradigm = paradigm
        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Paradigm selection

    def set_paradigm(
        self,
        paradigm: ParadigmType
    ) -> None:
        """Set the paradigm type."""
        self._current_paradigm = paradigm
        self._system = DirectedForgettingSystem(paradigm)

    # Item presentation

    def present(
        self,
        word: str,
        instruction: InstructionType
    ) -> StudyItem:
        """Present an item."""
        return self._system.present_item(word, instruction)

    # Testing

    def test_recall(
        self,
        item_id: str
    ) -> RecallResult:
        """Test recall."""
        return self._system.test_recall(item_id)

    def test_recognition(
        self,
        item_id: str
    ) -> RecognitionResult:
        """Test recognition."""
        return self._system.test_recognition(item_id)

    # Experiments

    def run_item_method(
        self,
        n_items: int = 20
    ) -> Dict[str, Any]:
        """Run item method experiment."""
        result = self._paradigm_runner.run_item_method_experiment(n_items)
        self._experiment_results.append(result)
        return result

    def run_list_method(
        self,
        n_items: int = 20
    ) -> Dict[str, Any]:
        """Run list method experiment."""
        result = self._paradigm_runner.run_list_method_experiment(n_items)
        self._experiment_results.append(result)
        return result

    def compare_methods(
        self
    ) -> Dict[str, Any]:
        """Compare methods."""
        return self._paradigm_runner.compare_methods()

    def run_recognition_test(
        self
    ) -> Dict[str, Any]:
        """Run recognition test."""
        return self._paradigm_runner.run_recognition_test(self._current_paradigm)

    def run_mechanism_test(
        self
    ) -> Dict[str, Any]:
        """Test different forgetting mechanisms."""
        # Item method: recall impaired, recognition less so
        item_recall = self.run_item_method(20)

        self.set_paradigm(ParadigmType.ITEM_METHOD)
        item_recog = self.run_recognition_test()

        # List method: recall impaired, recognition moderately affected
        list_recall = self.run_list_method(20)

        self.set_paradigm(ParadigmType.LIST_METHOD)
        list_recog = self.run_recognition_test()

        return {
            'item_method': {
                'recall_effect': item_recall['df_effect'],
                'recognition_effect': item_recog['recognition_effect'],
                'mechanism': ForgettingMechanism.SELECTIVE_REHEARSAL.name
            },
            'list_method': {
                'recall_effect': list_recall['df_effect'],
                'recognition_effect': list_recog['recognition_effect'],
                'mechanism': ForgettingMechanism.RETRIEVAL_INHIBITION.name
            }
        }

    # Analysis

    def get_metrics(self) -> DirectedForgettingMetrics:
        """Get directed forgetting metrics."""
        if not self._experiment_results:
            self.run_item_method()

        last = self._experiment_results[-1]

        return DirectedForgettingMetrics(
            remember_recall=last['remember_recall'],
            forget_recall=last['forget_recall'],
            directed_forgetting_effect=last['df_effect'],
            cost_to_forget=0.0  # Could measure processing cost
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'paradigm': self._current_paradigm.name,
            'items': len(self._system._items),
            'experiments': len(self._experiment_results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_directed_forgetting_engine(
    paradigm: ParadigmType = ParadigmType.ITEM_METHOD
) -> DirectedForgettingEngine:
    """Create directed forgetting engine."""
    return DirectedForgettingEngine(paradigm)


def demonstrate_directed_forgetting() -> Dict[str, Any]:
    """Demonstrate directed forgetting."""
    engine = create_directed_forgetting_engine()

    # Item method
    item = engine.run_item_method(20)

    # List method
    list_result = engine.run_list_method(20)

    # Method comparison
    comparison = engine.compare_methods()

    # Mechanism test
    mechanisms = engine.run_mechanism_test()

    return {
        'item_method': {
            'remember': f"{item['remember_recall']:.0%}",
            'forget': f"{item['forget_recall']:.0%}",
            'effect': f"{item['df_effect']:.0%}"
        },
        'list_method': {
            'remember': f"{list_result['remember_recall']:.0%}",
            'forget': f"{list_result['forget_recall']:.0%}",
            'effect': f"{list_result['df_effect']:.0%}"
        },
        'mechanisms': {
            'item_method_mechanism': mechanisms['item_method']['mechanism'],
            'list_method_mechanism': mechanisms['list_method']['mechanism']
        },
        'interpretation': (
            f"Item method effect: {item['df_effect']:.0%}. "
            f"List method effect: {list_result['df_effect']:.0%}. "
            f"Different mechanisms underlie each method."
        )
    }


def get_directed_forgetting_facts() -> Dict[str, str]:
    """Get facts about directed forgetting."""
    return {
        'bjork_1972': 'Classic directed forgetting paradigm',
        'item_method': 'Instruction after each item - selective rehearsal',
        'list_method': 'Instruction after list - retrieval inhibition',
        'intentional': 'Demonstrates intentional control over memory',
        'clinical': 'Relevant to trauma and unwanted memories',
        'recognition': 'Less affected than recall',
        'costs_benefits': 'Forget items impaired, remember items enhanced',
        'context': 'Mental context change may contribute'
    }
