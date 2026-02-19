"""
BAEL Retrieval-Induced Forgetting Engine
==========================================

Retrieving some items impairs memory for related items.
Anderson's inhibitory control model.

"Ba'el's selective suppression." — Ba'el
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

logger = logging.getLogger("BAEL.RetrievalInducedForgetting")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ItemStatus(Enum):
    """Status of items in RIF paradigm."""
    RP_PLUS = auto()      # Practiced items from practiced categories
    RP_MINUS = auto()     # Unpracticed items from practiced categories
    NRP = auto()          # Items from non-practiced categories


class InhibitionType(Enum):
    """Types of inhibition."""
    RETRIEVAL_SPECIFIC = auto()
    INTERFERENCE_DEPENDENT = auto()
    CUE_INDEPENDENT = auto()


class CompetitionStrength(Enum):
    """Strength of competition."""
    WEAK = auto()
    MODERATE = auto()
    STRONG = auto()


@dataclass
class CategoryItem:
    """
    An item belonging to a category.
    """
    id: str
    category: str
    exemplar: str
    baseline_strength: float
    current_strength: float
    inhibition_level: float


@dataclass
class RetrievalPractice:
    """
    A retrieval practice event.
    """
    item_id: str
    category: str
    successful: bool
    practice_number: int


@dataclass
class RIFMetrics:
    """
    Retrieval-induced forgetting metrics.
    """
    rp_plus_recall: float
    rp_minus_recall: float
    nrp_recall: float
    rif_effect: float  # NRP - RP-


# ============================================================================
# INHIBITORY CONTROL MODEL
# ============================================================================

class InhibitoryControlModel:
    """
    Anderson's inhibitory control model.

    "Ba'el's suppression mechanism." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Inhibition parameters
        self._inhibition_per_practice = 0.1
        self._inhibition_decay = 0.02
        self._competition_threshold = 0.3

        # Retrieval parameters
        self._practice_boost = 0.15
        self._baseline_recall = 0.6

        self._lock = threading.RLock()

    def calculate_inhibition(
        self,
        competitor_strength: float,
        target_strength: float,
        n_practices: int
    ) -> float:
        """Calculate inhibition applied to competitor."""
        # Only inhibit if competitor is strong enough to interfere
        competition = competitor_strength - self._competition_threshold

        if competition <= 0:
            return 0

        # Stronger competitors get more inhibition
        base_inhibition = competition * self._inhibition_per_practice

        # Multiple practices increase inhibition
        total_inhibition = base_inhibition * math.sqrt(n_practices)

        return min(0.5, total_inhibition)

    def apply_inhibition(
        self,
        current_strength: float,
        inhibition: float
    ) -> float:
        """Apply inhibition to item strength."""
        new_strength = current_strength * (1 - inhibition)
        return max(0.1, new_strength)

    def calculate_recall_probability(
        self,
        item_strength: float,
        inhibition_level: float
    ) -> float:
        """Calculate recall probability."""
        effective_strength = item_strength * (1 - inhibition_level)

        # Sigmoid transform
        prob = 1 / (1 + math.exp(-5 * (effective_strength - 0.5)))

        return prob


# ============================================================================
# RIF MEMORY SYSTEM
# ============================================================================

class RIFMemorySystem:
    """
    Retrieval-induced forgetting memory system.

    "Ba'el's competitive memory." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = InhibitoryControlModel()

        self._items: Dict[str, CategoryItem] = {}
        self._categories: Dict[str, List[str]] = defaultdict(list)
        self._practice_log: List[RetrievalPractice] = []

        # Track category status
        self._practiced_categories: Set[str] = set()
        self._practiced_items: Set[str] = set()

        self._item_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._item_counter += 1
        return f"item_{self._item_counter}"

    def add_item(
        self,
        category: str,
        exemplar: str,
        strength: float = 0.6
    ) -> CategoryItem:
        """Add an item to a category."""
        item = CategoryItem(
            id=self._generate_id(),
            category=category,
            exemplar=exemplar,
            baseline_strength=strength,
            current_strength=strength,
            inhibition_level=0
        )

        self._items[item.id] = item
        self._categories[category].append(item.id)

        return item

    def practice_item(
        self,
        item_id: str
    ) -> RetrievalPractice:
        """Practice retrieving an item."""
        item = self._items.get(item_id)
        if not item:
            return None

        # Record practice
        practice_num = sum(1 for p in self._practice_log if p.item_id == item_id) + 1

        # Boost practiced item
        success_prob = self._model.calculate_recall_probability(
            item.current_strength, item.inhibition_level
        )
        successful = random.random() < success_prob

        if successful:
            item.current_strength = min(1.0, item.current_strength + self._model._practice_boost)

        # Mark as practiced
        self._practiced_categories.add(item.category)
        self._practiced_items.add(item_id)

        # Apply inhibition to competitors (same category, not practiced)
        for other_id in self._categories[item.category]:
            if other_id != item_id and other_id not in self._practiced_items:
                other = self._items[other_id]

                inhibition = self._model.calculate_inhibition(
                    other.current_strength,
                    item.current_strength,
                    practice_num
                )

                other.inhibition_level = min(0.5, other.inhibition_level + inhibition)

        practice = RetrievalPractice(
            item_id=item_id,
            category=item.category,
            successful=successful,
            practice_number=practice_num
        )

        self._practice_log.append(practice)

        return practice

    def test_recall(
        self,
        item_id: str
    ) -> Tuple[bool, float]:
        """Test recall of an item."""
        item = self._items.get(item_id)
        if not item:
            return False, 0

        recall_prob = self._model.calculate_recall_probability(
            item.current_strength,
            item.inhibition_level
        )

        recalled = random.random() < recall_prob

        return recalled, recall_prob

    def get_item_status(
        self,
        item_id: str
    ) -> ItemStatus:
        """Get the status of an item in RIF paradigm."""
        item = self._items.get(item_id)
        if not item:
            return None

        if item_id in self._practiced_items:
            return ItemStatus.RP_PLUS
        elif item.category in self._practiced_categories:
            return ItemStatus.RP_MINUS
        else:
            return ItemStatus.NRP


# ============================================================================
# EXPERIMENTAL PARADIGM
# ============================================================================

class RIFParadigm:
    """
    Retrieval-induced forgetting experimental paradigm.

    "Ba'el's competitive retrieval." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_standard_experiment(
        self,
        n_categories: int = 8,
        items_per_category: int = 6,
        n_practiced_categories: int = 4,
        n_practiced_per_category: int = 3,
        n_practice_rounds: int = 3
    ) -> Dict[str, Any]:
        """Run standard RIF experiment."""
        system = RIFMemorySystem()

        # Study phase - add items
        categories = [f"category_{i}" for i in range(n_categories)]

        for cat in categories:
            for j in range(items_per_category):
                system.add_item(cat, f"{cat}_exemplar_{j}")

        # Retrieval practice phase
        practiced_categories = categories[:n_practiced_categories]

        for _ in range(n_practice_rounds):
            for cat in practiced_categories:
                cat_items = system._categories[cat]
                practiced_items = cat_items[:n_practiced_per_category]

                for item_id in practiced_items:
                    system.practice_item(item_id)

        # Test phase
        rp_plus_results = []
        rp_minus_results = []
        nrp_results = []

        for item_id, item in system._items.items():
            status = system.get_item_status(item_id)
            recalled, prob = system.test_recall(item_id)

            if status == ItemStatus.RP_PLUS:
                rp_plus_results.append(recalled)
            elif status == ItemStatus.RP_MINUS:
                rp_minus_results.append(recalled)
            else:
                nrp_results.append(recalled)

        rp_plus_recall = sum(rp_plus_results) / len(rp_plus_results) if rp_plus_results else 0
        rp_minus_recall = sum(rp_minus_results) / len(rp_minus_results) if rp_minus_results else 0
        nrp_recall = sum(nrp_results) / len(nrp_results) if nrp_results else 0

        rif_effect = nrp_recall - rp_minus_recall

        return {
            'n_categories': n_categories,
            'items_per_category': items_per_category,
            'rp_plus_recall': rp_plus_recall,
            'rp_minus_recall': rp_minus_recall,
            'nrp_recall': nrp_recall,
            'rif_effect': rif_effect
        }

    def run_competition_strength_test(
        self
    ) -> Dict[str, Any]:
        """Test effect of competitor strength."""
        results = {}

        for strength_level, base_strength in [
            ('weak', 0.3),
            ('moderate', 0.6),
            ('strong', 0.9)
        ]:
            system = RIFMemorySystem()

            # Add items with varying strength
            for i in range(4):
                system.add_item("practiced_cat", f"item_{i}", base_strength)

            for i in range(4):
                system.add_item("control_cat", f"control_{i}", base_strength)

            # Practice some items
            for item_id in list(system._categories["practiced_cat"])[:2]:
                for _ in range(3):
                    system.practice_item(item_id)

            # Test RP- items
            rp_minus_recalled = 0
            rp_minus_items = [id for id in system._categories["practiced_cat"]
                            if id not in system._practiced_items]

            for item_id in rp_minus_items:
                recalled, _ = system.test_recall(item_id)
                if recalled:
                    rp_minus_recalled += 1

            # Test NRP items
            nrp_recalled = 0
            for item_id in system._categories["control_cat"]:
                recalled, _ = system.test_recall(item_id)
                if recalled:
                    nrp_recalled += 1

            results[strength_level] = {
                'rp_minus': rp_minus_recalled / 2 if rp_minus_items else 0,
                'nrp': nrp_recalled / 4,
                'rif': (nrp_recalled / 4) - (rp_minus_recalled / 2 if rp_minus_items else 0)
            }

        return results

    def run_practice_amount_test(
        self
    ) -> Dict[str, Any]:
        """Test effect of practice amount on RIF."""
        results = {}

        for n_practice in [1, 3, 6, 10]:
            system = RIFMemorySystem()

            # Add items
            for i in range(6):
                system.add_item("practiced_cat", f"item_{i}", 0.6)

            for i in range(6):
                system.add_item("control_cat", f"control_{i}", 0.6)

            # Practice
            for item_id in list(system._categories["practiced_cat"])[:3]:
                for _ in range(n_practice):
                    system.practice_item(item_id)

            # Test
            rp_minus_results = []
            for item_id in system._categories["practiced_cat"]:
                if item_id not in system._practiced_items:
                    recalled, _ = system.test_recall(item_id)
                    rp_minus_results.append(recalled)

            nrp_results = []
            for item_id in system._categories["control_cat"]:
                recalled, _ = system.test_recall(item_id)
                nrp_results.append(recalled)

            results[f"{n_practice}_practices"] = {
                'rp_minus': sum(rp_minus_results) / len(rp_minus_results) if rp_minus_results else 0,
                'nrp': sum(nrp_results) / len(nrp_results) if nrp_results else 0
            }

        return results


# ============================================================================
# RIF ENGINE
# ============================================================================

class RetrievalInducedForgettingEngine:
    """
    Complete retrieval-induced forgetting engine.

    "Ba'el's inhibitory control." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = RIFParadigm()
        self._system = RIFMemorySystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Item management

    def add_item(
        self,
        category: str,
        exemplar: str,
        strength: float = 0.6
    ) -> CategoryItem:
        """Add an item."""
        return self._system.add_item(category, exemplar, strength)

    # Practice

    def practice(
        self,
        item_id: str
    ) -> RetrievalPractice:
        """Practice retrieving an item."""
        return self._system.practice_item(item_id)

    # Testing

    def test(
        self,
        item_id: str
    ) -> Tuple[bool, float]:
        """Test recall of an item."""
        return self._system.test_recall(item_id)

    def get_status(
        self,
        item_id: str
    ) -> ItemStatus:
        """Get item status."""
        return self._system.get_item_status(item_id)

    # Experiments

    def run_rif_experiment(
        self,
        n_categories: int = 8,
        items_per_category: int = 6
    ) -> Dict[str, Any]:
        """Run RIF experiment."""
        result = self._paradigm.run_standard_experiment(
            n_categories, items_per_category
        )
        self._experiment_results.append(result)
        return result

    def run_competition_test(
        self
    ) -> Dict[str, Any]:
        """Test competition strength effect."""
        return self._paradigm.run_competition_strength_test()

    def run_practice_amount_test(
        self
    ) -> Dict[str, Any]:
        """Test practice amount effect."""
        return self._paradigm.run_practice_amount_test()

    def run_output_interference_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare RIF to output interference."""
        # RIF: inhibition during practice
        # Output interference: interference during test

        rif_result = self._paradigm.run_standard_experiment(6, 6, 3, 3, 3)

        return {
            'rif_effect': rif_result['rif_effect'],
            'rp_plus_recall': rif_result['rp_plus_recall'],
            'rp_minus_recall': rif_result['rp_minus_recall'],
            'interpretation': (
                'RIF occurs during practice, not output. '
                'Demonstrated by cue-independence of effect.'
            )
        }

    # Analysis

    def get_metrics(self) -> RIFMetrics:
        """Get RIF metrics."""
        if not self._experiment_results:
            self.run_rif_experiment()

        last = self._experiment_results[-1]

        return RIFMetrics(
            rp_plus_recall=last['rp_plus_recall'],
            rp_minus_recall=last['rp_minus_recall'],
            nrp_recall=last['nrp_recall'],
            rif_effect=last['rif_effect']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'items': len(self._system._items),
            'categories': len(self._system._categories),
            'practices': len(self._system._practice_log),
            'experiments': len(self._experiment_results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_rif_engine() -> RetrievalInducedForgettingEngine:
    """Create RIF engine."""
    return RetrievalInducedForgettingEngine()


def demonstrate_retrieval_induced_forgetting() -> Dict[str, Any]:
    """Demonstrate retrieval-induced forgetting."""
    engine = create_rif_engine()

    # Standard experiment
    standard = engine.run_rif_experiment(8, 6)

    # Competition strength
    competition = engine.run_competition_test()

    # Practice amount
    practice = engine.run_practice_amount_test()

    # Output interference comparison
    output = engine.run_output_interference_comparison()

    return {
        'standard_rif': {
            'rp_plus': f"{standard['rp_plus_recall']:.0%}",
            'rp_minus': f"{standard['rp_minus_recall']:.0%}",
            'nrp': f"{standard['nrp_recall']:.0%}",
            'rif_effect': f"{standard['rif_effect']:.0%}"
        },
        'competition_effect': {
            strength: f"RIF: {data['rif']:.0%}"
            for strength, data in competition.items()
        },
        'practice_effect': {
            n: f"RP-: {data['rp_minus']:.0%}"
            for n, data in practice.items()
        },
        'interpretation': (
            f"RIF effect: {standard['rif_effect']:.0%}. "
            f"Practicing some items inhibits recall of related unpracticed items."
        )
    }


def get_rif_facts() -> Dict[str, str]:
    """Get facts about retrieval-induced forgetting."""
    return {
        'anderson_et_al_1994': 'Original RIF demonstration',
        'inhibitory_control': 'Active suppression of competitors',
        'competition_dependent': 'Stronger competitors get more inhibition',
        'cue_independent': 'Effect occurs with novel cues at test',
        'rp_plus_rp_minus_nrp': 'Three item types in paradigm',
        'retrieval_specific': 'Requires retrieval, not just re-exposure',
        'practical_implications': 'Selective review can harm related knowledge',
        'executive_function': 'Related to inhibitory control abilities'
    }
