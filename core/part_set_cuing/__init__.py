"""
BAEL Part-Set Cuing Engine
============================

Providing some items as cues impairs recall of remaining items.
Retrieval inhibition and output interference.

"Ba'el's helpful hindrance." — Ba'el
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

logger = logging.getLogger("BAEL.PartSetCuing")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class CueType(Enum):
    """Types of cuing."""
    NO_CUE = auto()           # Free recall
    CATEGORY_CUE = auto()     # Category name provided
    PART_SET_CUE = auto()     # Some list items provided
    EXTRA_LIST_CUE = auto()   # Related but not studied items


class ListType(Enum):
    """Types of lists."""
    CATEGORIZED = auto()      # Items from categories
    RANDOM = auto()           # Random items
    ASSOCIATED = auto()       # Semantically associated


class InhibitionType(Enum):
    """Types of inhibition."""
    RETRIEVAL_INHIBITION = auto()  # Cues block retrieval
    OUTPUT_INTERFERENCE = auto()    # Output of cues interferes
    STRATEGY_DISRUPTION = auto()    # Cues disrupt retrieval strategy


@dataclass
class ListItem:
    """
    An item in a list.
    """
    id: str
    content: str
    category: Optional[str]
    serial_position: int
    strength: float


@dataclass
class CueSet:
    """
    A set of cues.
    """
    items: List[ListItem]
    cue_type: CueType
    proportion_cued: float


@dataclass
class RecallResult:
    """
    Result of recall attempt.
    """
    item_id: str
    recalled: bool
    recall_position: int
    was_cued: bool
    retrieval_time_ms: float


@dataclass
class PartSetCuingMetrics:
    """
    Part-set cuing metrics.
    """
    cued_condition_recall: float
    uncued_condition_recall: float
    part_set_cuing_effect: float
    inhibition_strength: float


# ============================================================================
# RETRIEVAL INHIBITION MODEL
# ============================================================================

class RetrievalInhibitionModel:
    """
    Model of retrieval inhibition.

    "Ba'el's blocking effect." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Inhibition parameters
        self._base_inhibition = 0.15
        self._cue_competition = 0.2
        self._output_interference = 0.1

        self._lock = threading.RLock()

    def calculate_inhibition(
        self,
        n_cues: int,
        n_total: int
    ) -> float:
        """Calculate inhibition from part-set cues."""
        if n_total == 0:
            return 0

        cue_proportion = n_cues / n_total

        # More cues = more inhibition (up to a point)
        inhibition = self._base_inhibition + self._cue_competition * cue_proportion

        return min(0.5, inhibition)

    def apply_output_interference(
        self,
        base_recall_prob: float,
        output_position: int
    ) -> float:
        """Apply output interference from prior recalls."""
        # Each prior output reduces recall probability slightly
        interference = output_position * self._output_interference

        return max(0.1, base_recall_prob - interference)


# ============================================================================
# MEMORY MODEL
# ============================================================================

class PartSetCuingMemory:
    """
    Memory model for part-set cuing.

    "Ba'el's cue-impaired recall." — Ba'el
    """

    def __init__(self):
        """Initialize memory."""
        self._inhibition_model = RetrievalInhibitionModel()

        self._items: Dict[str, ListItem] = {}
        self._categories: Dict[str, List[str]] = defaultdict(list)

        # Encoding parameters
        self._base_encoding = 0.7

        self._item_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._item_counter += 1
        return f"item_{self._item_counter}"

    def encode_item(
        self,
        content: str,
        category: Optional[str] = None,
        position: int = 0
    ) -> ListItem:
        """Encode an item into memory."""
        # Primacy and recency effects
        if position < 3:
            strength = self._base_encoding + 0.15
        elif position > 10:
            strength = self._base_encoding + 0.1
        else:
            strength = self._base_encoding

        strength += random.gauss(0, 0.05)
        strength = max(0.3, min(1, strength))

        item = ListItem(
            id=self._generate_id(),
            content=content,
            category=category,
            serial_position=position,
            strength=strength
        )

        self._items[item.id] = item
        if category:
            self._categories[category].append(item.id)

        return item

    def free_recall(
        self,
        delay_minutes: float = 0
    ) -> List[RecallResult]:
        """Free recall without cues."""
        decay = math.exp(-delay_minutes / 20)

        results = []
        output_position = 0

        # Recall in rough strength order (with noise)
        items_by_strength = sorted(
            self._items.values(),
            key=lambda x: x.strength + random.gauss(0, 0.1),
            reverse=True
        )

        for item in items_by_strength:
            recall_prob = item.strength * decay
            recall_prob = self._inhibition_model.apply_output_interference(
                recall_prob, output_position
            )

            recalled = random.random() < recall_prob

            results.append(RecallResult(
                item_id=item.id,
                recalled=recalled,
                recall_position=output_position if recalled else -1,
                was_cued=False,
                retrieval_time_ms=1000 + random.gauss(0, 200)
            ))

            if recalled:
                output_position += 1

        return results

    def cued_recall(
        self,
        cue_items: List[str],
        delay_minutes: float = 0
    ) -> List[RecallResult]:
        """Recall with part-set cues."""
        decay = math.exp(-delay_minutes / 20)

        # Calculate inhibition from cues
        n_cues = len(cue_items)
        n_total = len(self._items)
        inhibition = self._inhibition_model.calculate_inhibition(n_cues, n_total)

        results = []
        output_position = 0

        # Cued items first (always "recalled" since provided)
        for item_id in cue_items:
            item = self._items.get(item_id)
            if item:
                results.append(RecallResult(
                    item_id=item_id,
                    recalled=True,
                    recall_position=output_position,
                    was_cued=True,
                    retrieval_time_ms=500  # Fast for cues
                ))
                output_position += 1

        # Non-cued items with inhibition
        non_cued = [item for item in self._items.values() if item.id not in cue_items]

        for item in sorted(non_cued, key=lambda x: x.strength + random.gauss(0, 0.1), reverse=True):
            # Apply inhibition from cues
            recall_prob = item.strength * decay * (1 - inhibition)
            recall_prob = self._inhibition_model.apply_output_interference(
                recall_prob, output_position
            )

            recalled = random.random() < recall_prob

            results.append(RecallResult(
                item_id=item.id,
                recalled=recalled,
                recall_position=output_position if recalled else -1,
                was_cued=False,
                retrieval_time_ms=1200 + random.gauss(0, 300)  # Slower with inhibition
            ))

            if recalled:
                output_position += 1

        return results


# ============================================================================
# EXPERIMENTAL PARADIGM
# ============================================================================

class PartSetCuingParadigm:
    """
    Part-set cuing experimental paradigm.

    "Ba'el's cuing experiment." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_experiment(
        self,
        n_items: int = 20,
        cue_proportion: float = 0.5,
        delay_minutes: float = 5
    ) -> Dict[str, Any]:
        """Run part-set cuing experiment."""
        # Create two conditions

        # Condition 1: Free recall (no cues)
        free_memory = PartSetCuingMemory()
        for i in range(n_items):
            free_memory.encode_item(f"item_{i}", position=i)

        free_results = free_memory.free_recall(delay_minutes)
        free_recall_rate = sum(1 for r in free_results if r.recalled) / len(free_results)

        # Condition 2: Part-set cued recall
        cued_memory = PartSetCuingMemory()
        for i in range(n_items):
            cued_memory.encode_item(f"item_{i}", position=i)

        # Select cue items
        all_item_ids = list(cued_memory._items.keys())
        n_cues = int(n_items * cue_proportion)
        cue_ids = random.sample(all_item_ids, n_cues)

        cued_results = cued_memory.cued_recall(cue_ids, delay_minutes)

        # Calculate recall of non-cued items only
        non_cued_results = [r for r in cued_results if not r.was_cued]
        non_cued_recall_rate = sum(1 for r in non_cued_results if r.recalled) / len(non_cued_results) if non_cued_results else 0

        # Part-set cuing effect = free recall - cued recall of non-cued items
        part_set_effect = free_recall_rate - non_cued_recall_rate

        return {
            'n_items': n_items,
            'cue_proportion': cue_proportion,
            'free_recall_rate': free_recall_rate,
            'cued_non_cued_rate': non_cued_recall_rate,
            'part_set_cuing_effect': part_set_effect,
            'delay_minutes': delay_minutes
        }

    def run_cue_proportion_comparison(
        self,
        n_items: int = 20,
        proportions: List[float] = None
    ) -> Dict[str, Any]:
        """Compare effect across cue proportions."""
        if proportions is None:
            proportions = [0.25, 0.50, 0.75]

        results = {}

        for prop in proportions:
            result = self.run_experiment(n_items, prop, 5)
            results[f"cue_{int(prop*100)}%"] = {
                'non_cued_recall': result['cued_non_cued_rate'],
                'effect': result['part_set_cuing_effect']
            }

        return results


# ============================================================================
# PART-SET CUING ENGINE
# ============================================================================

class PartSetCuingEngine:
    """
    Complete part-set cuing engine.

    "Ba'el's cuing inhibition." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = PartSetCuingParadigm()
        self._memory = PartSetCuingMemory()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Memory operations

    def encode(
        self,
        content: str,
        category: Optional[str] = None,
        position: int = 0
    ) -> ListItem:
        """Encode an item."""
        return self._memory.encode_item(content, category, position)

    # Recall

    def free_recall(
        self,
        delay: float = 0
    ) -> List[RecallResult]:
        """Free recall."""
        return self._memory.free_recall(delay)

    def cued_recall(
        self,
        cue_ids: List[str],
        delay: float = 0
    ) -> List[RecallResult]:
        """Recall with part-set cues."""
        return self._memory.cued_recall(cue_ids, delay)

    # Experiments

    def run_part_set_experiment(
        self,
        n_items: int = 20,
        cue_proportion: float = 0.5
    ) -> Dict[str, Any]:
        """Run part-set cuing experiment."""
        result = self._paradigm.run_experiment(n_items, cue_proportion, 5)
        self._experiment_results.append(result)
        return result

    def run_proportion_comparison(
        self,
        n_items: int = 20
    ) -> Dict[str, Any]:
        """Compare effect across cue proportions."""
        return self._paradigm.run_cue_proportion_comparison(n_items)

    def run_strategy_disruption_test(
        self,
        n_items: int = 20
    ) -> Dict[str, Any]:
        """Test strategy disruption hypothesis."""
        # Categorized list
        memory = PartSetCuingMemory()
        categories = ["animals", "tools", "foods", "colors"]

        items_per_cat = n_items // len(categories)
        for cat_idx, cat in enumerate(categories):
            for i in range(items_per_cat):
                pos = cat_idx * items_per_cat + i
                memory.encode_item(f"{cat}_{i}", category=cat, position=pos)

        # Cue with items from mixed categories (disrupts organization)
        all_ids = list(memory._items.keys())
        random_cues = random.sample(all_ids, n_items // 2)

        cued_results = memory.cued_recall(random_cues, 5)
        non_cued = [r for r in cued_results if not r.was_cued]
        non_cued_rate = sum(1 for r in non_cued if r.recalled) / len(non_cued) if non_cued else 0

        # Compare to free recall baseline
        free_memory = PartSetCuingMemory()
        for cat_idx, cat in enumerate(categories):
            for i in range(items_per_cat):
                pos = cat_idx * items_per_cat + i
                free_memory.encode_item(f"{cat}_{i}", category=cat, position=pos)

        free_results = free_memory.free_recall(5)
        free_rate = sum(1 for r in free_results if r.recalled) / len(free_results)

        return {
            'strategy_disruption_effect': free_rate - non_cued_rate,
            'free_recall': free_rate,
            'cued_non_cued': non_cued_rate,
            'interpretation': 'Random cues disrupt categorical retrieval strategy'
        }

    # Analysis

    def get_metrics(self) -> PartSetCuingMetrics:
        """Get part-set cuing metrics."""
        if not self._experiment_results:
            self.run_part_set_experiment(20, 0.5)

        last = self._experiment_results[-1]

        return PartSetCuingMetrics(
            cued_condition_recall=last['cued_non_cued_rate'],
            uncued_condition_recall=last['free_recall_rate'],
            part_set_cuing_effect=last['part_set_cuing_effect'],
            inhibition_strength=last['part_set_cuing_effect'] / last['free_recall_rate'] if last['free_recall_rate'] > 0 else 0
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'items': len(self._memory._items),
            'experiments': len(self._experiment_results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_part_set_cuing_engine() -> PartSetCuingEngine:
    """Create part-set cuing engine."""
    return PartSetCuingEngine()


def demonstrate_part_set_cuing() -> Dict[str, Any]:
    """Demonstrate part-set cuing effect."""
    engine = create_part_set_cuing_engine()

    # Basic experiment
    basic = engine.run_part_set_experiment(20, 0.5)

    # Proportion comparison
    proportions = engine.run_proportion_comparison(20)

    # Strategy disruption
    strategy = engine.run_strategy_disruption_test(20)

    return {
        'part_set_cuing': {
            'free_recall': f"{basic['free_recall_rate']:.0%}",
            'cued_non_cued_recall': f"{basic['cued_non_cued_rate']:.0%}",
            'effect': f"{basic['part_set_cuing_effect']:.0%}"
        },
        'cue_proportion_effect': {
            prop: f"effect: {data['effect']:.0%}"
            for prop, data in proportions.items()
        },
        'strategy_disruption': {
            'effect': f"{strategy['strategy_disruption_effect']:.0%}",
            'interpretation': strategy['interpretation']
        },
        'interpretation': (
            f"Part-set cuing effect: {basic['part_set_cuing_effect']:.0%}. "
            f"Providing some items as cues impairs recall of remaining items."
        )
    }


def get_part_set_cuing_facts() -> Dict[str, str]:
    """Get facts about part-set cuing."""
    return {
        'slamecka_1968': 'Original demonstration of part-set cuing inhibition',
        'helpful_hurts': 'Cues intended to help actually impair recall',
        'retrieval_inhibition': 'Cues compete for retrieval with non-cued items',
        'strategy_disruption': 'Cues disrupt natural retrieval organization',
        'output_interference': 'Outputting cues creates interference',
        'categorized_lists': 'Effect stronger with organized lists',
        'practical': 'Relevant to study guides and hints',
        'generation_benefit': 'Self-generated cues may help rather than hurt'
    }
