"""
BAEL Output Interference Engine
=================================

Remembering hurts other memories.
Roediger's output interference paradigm.

"Ba'el's recall impairs further recall." — Ba'el
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

logger = logging.getLogger("BAEL.OutputInterference")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class OutputPosition(Enum):
    """Position in output sequence."""
    EARLY = auto()
    MIDDLE = auto()
    LATE = auto()


class InterferenceType(Enum):
    """Type of interference."""
    OUTPUT_INTERFERENCE = auto()   # Recall blocks other recall
    RETRIEVAL_INDUCED = auto()     # Practice blocks related items
    PART_SET_CUING = auto()        # Cues block other items


@dataclass
class MemoryItem:
    """
    A memory item.
    """
    id: str
    content: str
    category: str
    strength: float
    output_position: Optional[int] = None


@dataclass
class RecallAttempt:
    """
    A recall attempt.
    """
    item_id: str
    output_position: int
    successfully_recalled: bool
    latency_ms: float
    cumulative_interference: float


@dataclass
class OutputInterferenceMetrics:
    """
    Output interference metrics.
    """
    early_recall_rate: float
    late_recall_rate: float
    interference_slope: float
    total_recalled: int


# ============================================================================
# OUTPUT INTERFERENCE MODEL
# ============================================================================

class OutputInterferenceModel:
    """
    Model of output interference.

    "Ba'el's recall decay." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Interference parameters
        self._base_interference_rate = 0.02  # Per prior output
        self._cumulative_factor = 1.2        # Interference accumulates faster

        # Retrieval parameters
        self._base_retrieval_prob = 0.7
        self._strength_weight = 0.3

        # Latency parameters
        self._base_latency = 500  # ms
        self._latency_increase = 100  # ms per prior output

        self._lock = threading.RLock()

    def calculate_interference(
        self,
        output_position: int
    ) -> float:
        """Calculate cumulative interference at this output position."""
        if output_position == 0:
            return 0.0

        # Interference accumulates with each prior recall
        interference = 0.0
        for i in range(output_position):
            interference += self._base_interference_rate * (self._cumulative_factor ** i)

        return min(0.6, interference)  # Cap at 60% interference

    def calculate_retrieval_probability(
        self,
        item: MemoryItem,
        output_position: int,
        already_recalled: List[str]
    ) -> float:
        """Calculate probability of recalling this item."""
        # Base probability
        prob = self._base_retrieval_prob

        # Item strength
        prob += item.strength * self._strength_weight

        # Subtract interference
        interference = self.calculate_interference(output_position)
        prob -= interference

        # Already recalled items can't be recalled again
        if item.id in already_recalled:
            return 0.0

        return max(0.1, min(0.95, prob))

    def calculate_latency(
        self,
        output_position: int
    ) -> float:
        """Calculate retrieval latency at this position."""
        return self._base_latency + output_position * self._latency_increase


# ============================================================================
# OUTPUT INTERFERENCE SYSTEM
# ============================================================================

class OutputInterferenceSystem:
    """
    Output interference simulation system.

    "Ba'el's recall competition." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = OutputInterferenceModel()

        self._items: Dict[str, MemoryItem] = {}
        self._recalled: List[str] = []
        self._attempts: List[RecallAttempt] = []

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"item_{self._counter}"

    def create_item(
        self,
        content: str,
        category: str = "default",
        strength: float = 0.5
    ) -> MemoryItem:
        """Create a memory item."""
        item = MemoryItem(
            id=self._generate_id(),
            content=content,
            category=category,
            strength=strength
        )

        self._items[item.id] = item

        return item

    def attempt_recall(
        self,
        item_id: str
    ) -> RecallAttempt:
        """Attempt to recall an item."""
        item = self._items.get(item_id)
        if not item:
            return None

        output_position = len(self._recalled)

        prob = self._model.calculate_retrieval_probability(
            item, output_position, self._recalled
        )

        success = random.random() < prob
        latency = self._model.calculate_latency(output_position)
        interference = self._model.calculate_interference(output_position)

        if success:
            self._recalled.append(item_id)
            item.output_position = output_position

        attempt = RecallAttempt(
            item_id=item_id,
            output_position=output_position,
            successfully_recalled=success,
            latency_ms=latency,
            cumulative_interference=interference
        )

        self._attempts.append(attempt)

        return attempt

    def free_recall(
        self,
        max_attempts: int = 50
    ) -> List[RecallAttempt]:
        """Perform free recall until exhaustion."""
        attempts = []
        remaining = list(self._items.keys())

        for _ in range(max_attempts):
            if not remaining:
                break

            # Pick random remaining item to try
            item_id = random.choice(remaining)
            attempt = self.attempt_recall(item_id)
            attempts.append(attempt)

            if attempt.successfully_recalled:
                remaining.remove(item_id)
            elif random.random() < 0.3:  # Give up on some items
                remaining.remove(item_id)

        return attempts

    def reset_recall(self):
        """Reset recall state."""
        self._recalled = []
        self._attempts = []
        for item in self._items.values():
            item.output_position = None


# ============================================================================
# OUTPUT INTERFERENCE PARADIGM
# ============================================================================

class OutputInterferenceParadigm:
    """
    Output interference experimental paradigm.

    "Ba'el's recall position study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_basic_paradigm(
        self,
        n_items: int = 30
    ) -> Dict[str, Any]:
        """Run basic output interference paradigm."""
        system = OutputInterferenceSystem()

        # Create items with varying strength
        for i in range(n_items):
            strength = 0.4 + random.uniform(0, 0.4)
            system.create_item(f"word_{i}", "words", strength)

        # Free recall
        attempts = system.free_recall()

        # Analyze by output position
        position_success = defaultdict(list)

        for attempt in attempts:
            if attempt.successfully_recalled:
                pos_category = (
                    'early' if attempt.output_position < n_items // 3
                    else 'middle' if attempt.output_position < 2 * n_items // 3
                    else 'late'
                )
                position_success[pos_category].append(1)
            else:
                pos_category = (
                    'early' if attempt.output_position < n_items // 3
                    else 'middle' if attempt.output_position < 2 * n_items // 3
                    else 'late'
                )
                position_success[pos_category].append(0)

        # Calculate success rates
        rates = {}
        for pos, successes in position_success.items():
            rates[pos] = sum(successes) / len(successes) if successes else 0

        # Calculate slope (decline over positions)
        total_recalled = len(system._recalled)

        return {
            'position_rates': rates,
            'total_recalled': total_recalled,
            'recall_rate': total_recalled / n_items,
            'interference_slope': rates.get('early', 0) - rates.get('late', 0)
        }

    def run_category_clustering_study(
        self,
        n_categories: int = 4,
        items_per_category: int = 6
    ) -> Dict[str, Any]:
        """Study how category clustering interacts with output interference."""
        system = OutputInterferenceSystem()

        # Create categorized items
        categories = [f"category_{i}" for i in range(n_categories)]
        for cat in categories:
            for j in range(items_per_category):
                system.create_item(f"{cat}_item_{j}", cat)

        # Free recall
        attempts = system.free_recall()

        # Analyze within-category interference
        category_outputs = defaultdict(list)
        for item_id in system._recalled:
            item = system._items[item_id]
            category_outputs[item.category].append(item.output_position)

        # First vs last in each category
        within_category_decline = []
        for cat, positions in category_outputs.items():
            if len(positions) >= 2:
                decline = positions[-1] - positions[0]  # More decline = more interference
                within_category_decline.append(decline)

        return {
            'total_recalled': len(system._recalled),
            'categories_recalled': len(category_outputs),
            'avg_within_category_spread': sum(within_category_decline) / len(within_category_decline) if within_category_decline else 0,
            'interpretation': 'Recalling one category item interferes with others in same category'
        }

    def run_output_order_manipulation(
        self
    ) -> Dict[str, Any]:
        """Manipulate output order to show interference effect."""
        # Random order vs forced order

        results = {}

        # Random recall order
        system1 = OutputInterferenceSystem()
        for i in range(20):
            system1.create_item(f"word_{i}")
        system1.free_recall()
        results['random_order'] = len(system1._recalled)

        # In interference model, early items get recalled easier
        # Let's show cumulative interference
        cumulative = []
        for i, item_id in enumerate(system1._recalled):
            interference = system1._model.calculate_interference(i)
            cumulative.append(interference)

        results['avg_interference'] = sum(cumulative) / len(cumulative) if cumulative else 0
        results['final_interference'] = cumulative[-1] if cumulative else 0

        return results

    def run_list_length_study(
        self
    ) -> Dict[str, Any]:
        """Study effect of list length on output interference."""
        lengths = [10, 20, 30, 40]
        results = {}

        for length in lengths:
            system = OutputInterferenceSystem()

            for i in range(length):
                system.create_item(f"word_{i}")

            system.free_recall()

            results[f"length_{length}"] = {
                'recalled': len(system._recalled),
                'rate': len(system._recalled) / length,
                'final_interference': system._model.calculate_interference(
                    min(len(system._recalled), length)
                )
            }

        return results

    def run_recall_latency_study(
        self
    ) -> Dict[str, Any]:
        """Study latency increase across output positions."""
        system = OutputInterferenceSystem()

        for i in range(25):
            system.create_item(f"word_{i}")

        attempts = system.free_recall()

        # Group latencies by position
        position_latencies = defaultdict(list)
        for attempt in attempts:
            if attempt.successfully_recalled:
                pos_group = attempt.output_position // 5  # Groups of 5
                position_latencies[pos_group].append(attempt.latency_ms)

        avg_latencies = {
            f"positions_{k*5}-{k*5+4}": sum(v)/len(v) if v else 0
            for k, v in position_latencies.items()
        }

        return {
            'latencies_by_position': avg_latencies,
            'interpretation': 'Latency increases with output position'
        }


# ============================================================================
# OUTPUT INTERFERENCE ENGINE
# ============================================================================

class OutputInterferenceEngine:
    """
    Complete output interference engine.

    "Ba'el's recall competition engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = OutputInterferenceParadigm()
        self._system = OutputInterferenceSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Item management

    def create_item(
        self,
        content: str,
        category: str = "default"
    ) -> MemoryItem:
        """Create an item."""
        return self._system.create_item(content, category)

    def attempt_recall(
        self,
        item_id: str
    ) -> RecallAttempt:
        """Attempt recall."""
        return self._system.attempt_recall(item_id)

    def free_recall(
        self
    ) -> List[RecallAttempt]:
        """Free recall."""
        return self._system.free_recall()

    def reset(self):
        """Reset recall state."""
        self._system.reset_recall()

    # Experiments

    def run_basic_experiment(
        self
    ) -> Dict[str, Any]:
        """Run basic experiment."""
        result = self._paradigm.run_basic_paradigm()
        self._experiment_results.append(result)
        return result

    def study_category_clustering(
        self
    ) -> Dict[str, Any]:
        """Study category effects."""
        return self._paradigm.run_category_clustering_study()

    def study_output_order(
        self
    ) -> Dict[str, Any]:
        """Study output order effects."""
        return self._paradigm.run_output_order_manipulation()

    def study_list_length(
        self
    ) -> Dict[str, Any]:
        """Study list length effects."""
        return self._paradigm.run_list_length_study()

    def study_latency(
        self
    ) -> Dict[str, Any]:
        """Study latency increases."""
        return self._paradigm.run_recall_latency_study()

    def simulate_exam_scenario(
        self
    ) -> Dict[str, Any]:
        """Simulate output interference in exam."""
        system = OutputInterferenceSystem()

        # Study material organized by topic
        topics = ['History', 'Science', 'Math']
        for topic in topics:
            for i in range(8):
                strength = random.uniform(0.4, 0.8)
                system.create_item(f"{topic}_fact_{i}", topic, strength)

        # Exam recall
        system.free_recall()

        # Analyze by topic
        topic_recall = defaultdict(list)
        for item_id in system._recalled:
            item = system._items[item_id]
            topic_recall[item.category].append(item.output_position)

        topic_rates = {
            topic: len(positions) / 8
            for topic, positions in topic_recall.items()
        }

        return {
            'total_recalled': len(system._recalled),
            'topic_rates': topic_rates,
            'interpretation': 'Earlier recalled topics may interfere with later ones'
        }

    # Analysis

    def get_metrics(self) -> OutputInterferenceMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_basic_experiment()

        last = self._experiment_results[-1]
        rates = last['position_rates']

        return OutputInterferenceMetrics(
            early_recall_rate=rates.get('early', 0),
            late_recall_rate=rates.get('late', 0),
            interference_slope=last['interference_slope'],
            total_recalled=last['total_recalled']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'items': len(self._system._items),
            'recalled': len(self._system._recalled),
            'attempts': len(self._system._attempts)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_output_interference_engine() -> OutputInterferenceEngine:
    """Create output interference engine."""
    return OutputInterferenceEngine()


def demonstrate_output_interference() -> Dict[str, Any]:
    """Demonstrate output interference."""
    engine = create_output_interference_engine()

    # Basic experiment
    basic = engine.run_basic_experiment()

    # Category study
    category = engine.study_category_clustering()

    # Output order
    order = engine.study_output_order()

    # List length
    length = engine.study_list_length()

    # Latency
    latency = engine.study_latency()

    # Exam scenario
    exam = engine.simulate_exam_scenario()

    return {
        'basic': {
            'early_rate': f"{basic['position_rates'].get('early', 0):.0%}",
            'late_rate': f"{basic['position_rates'].get('late', 0):.0%}",
            'slope': f"{basic['interference_slope']:.0%}",
            'total': basic['total_recalled']
        },
        'category': {
            'recalled': category['total_recalled'],
            'categories': category['categories_recalled']
        },
        'list_length': {
            k: f"{v['rate']:.0%}"
            for k, v in length.items()
        },
        'latency': {
            k: f"{v:.0f}ms"
            for k, v in latency['latencies_by_position'].items()
        },
        'interpretation': (
            f"Early success: {basic['position_rates'].get('early', 0):.0%}, "
            f"late: {basic['position_rates'].get('late', 0):.0%}. "
            f"Recall causes interference."
        )
    }


def get_output_interference_facts() -> Dict[str, str]:
    """Get facts about output interference."""
    return {
        'roediger_1978': 'Classic output interference demonstration',
        'mechanism': 'Each recall creates interference for remaining items',
        'cumulative': 'Interference accumulates across output positions',
        'latency': 'Response times increase across output',
        'category': 'Within-category items particularly affected',
        'strength': 'Strong items recalled first, weak items suffer more',
        'practical': 'Explains why we forget things during recall'
    }
