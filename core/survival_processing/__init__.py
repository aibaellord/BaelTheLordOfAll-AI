"""
BAEL Survival Processing Engine
=================================

Enhanced memory for survival-relevant information.
Nairne's evolutionary memory hypothesis.

"Ba'el remembers what keeps us alive." — Ba'el
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

logger = logging.getLogger("BAEL.SurvivalProcessing")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ProcessingScenario(Enum):
    """Types of processing scenarios."""
    SURVIVAL = auto()        # Grasslands survival
    MOVING = auto()          # Moving to new home
    PLEASANTNESS = auto()    # Rate pleasantness
    RELEVANCE = auto()       # Rate personal relevance
    CAMPING = auto()         # Camping trip (modern survival)
    ZOMBIE = auto()          # Zombie apocalypse (fictional survival)


class ItemCategory(Enum):
    """Categories of items."""
    FOOD = auto()
    TOOL = auto()
    SHELTER = auto()
    WEAPON = auto()
    MEDICAL = auto()
    RANDOM = auto()


class SurvivalRelevance(Enum):
    """Survival relevance levels."""
    CRITICAL = auto()
    MODERATE = auto()
    LOW = auto()
    NONE = auto()


@dataclass
class StimulusItem:
    """
    A stimulus item for the experiment.
    """
    id: str
    word: str
    category: ItemCategory
    inherent_survival_relevance: SurvivalRelevance


@dataclass
class Rating:
    """
    A participant rating.
    """
    item_id: str
    scenario: ProcessingScenario
    rating_value: float  # 1-5 scale
    response_time_ms: float


@dataclass
class RecallResult:
    """
    Recall test result.
    """
    item_id: str
    recalled: bool
    scenario: ProcessingScenario


@dataclass
class SurvivalProcessingMetrics:
    """
    Survival processing metrics.
    """
    survival_recall: float
    moving_recall: float
    pleasantness_recall: float
    survival_advantage: float


# ============================================================================
# EVOLUTIONARY MEMORY MODEL
# ============================================================================

class EvolutionaryMemoryModel:
    """
    Evolutionary memory model for survival processing.

    "Ba'el's ancestral memory system." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Scenario encoding bonuses
        self._scenario_bonuses = {
            ProcessingScenario.SURVIVAL: 0.30,
            ProcessingScenario.ZOMBIE: 0.25,
            ProcessingScenario.CAMPING: 0.22,
            ProcessingScenario.RELEVANCE: 0.15,
            ProcessingScenario.MOVING: 0.12,
            ProcessingScenario.PLEASANTNESS: 0.10
        }

        # Item category relevance
        self._category_survival = {
            ItemCategory.FOOD: 0.9,
            ItemCategory.SHELTER: 0.8,
            ItemCategory.TOOL: 0.7,
            ItemCategory.WEAPON: 0.8,
            ItemCategory.MEDICAL: 0.7,
            ItemCategory.RANDOM: 0.3
        }

        self._base_encoding = 0.4

        self._lock = threading.RLock()

    def calculate_encoding_strength(
        self,
        scenario: ProcessingScenario,
        item: StimulusItem,
        rating: float
    ) -> float:
        """Calculate encoding strength."""
        base = self._base_encoding

        # Scenario bonus
        scenario_bonus = self._scenario_bonuses.get(scenario, 0)

        # Category-scenario interaction
        if scenario == ProcessingScenario.SURVIVAL:
            category_relevance = self._category_survival.get(item.category, 0.3)
            interaction_bonus = category_relevance * 0.15
        else:
            interaction_bonus = 0

        # Rating-based elaboration
        rating_bonus = (rating - 1) / 4 * 0.1

        strength = base + scenario_bonus + interaction_bonus + rating_bonus

        return min(1.0, strength)

    def survival_relevance_boost(
        self,
        relevance: SurvivalRelevance
    ) -> float:
        """Get boost for survival relevance."""
        if relevance == SurvivalRelevance.CRITICAL:
            return 0.15
        elif relevance == SurvivalRelevance.MODERATE:
            return 0.08
        elif relevance == SurvivalRelevance.LOW:
            return 0.03
        return 0


# ============================================================================
# SURVIVAL PROCESSING SYSTEM
# ============================================================================

class SurvivalProcessingSystem:
    """
    Survival processing advantage system.

    "Ba'el's ancestral memory advantage." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = EvolutionaryMemoryModel()

        self._items: Dict[str, StimulusItem] = {}
        self._ratings: Dict[str, Rating] = {}
        self._encoding_strengths: Dict[str, float] = {}

        self._item_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._item_counter += 1
        return f"item_{self._item_counter}"

    def add_item(
        self,
        word: str,
        category: ItemCategory = ItemCategory.RANDOM,
        relevance: SurvivalRelevance = SurvivalRelevance.MODERATE
    ) -> StimulusItem:
        """Add a stimulus item."""
        item = StimulusItem(
            id=self._generate_id(),
            word=word,
            category=category,
            inherent_survival_relevance=relevance
        )

        self._items[item.id] = item
        return item

    def rate_item(
        self,
        item_id: str,
        scenario: ProcessingScenario,
        rating: float = None
    ) -> Rating:
        """Rate an item for a scenario."""
        item = self._items.get(item_id)
        if not item:
            return None

        # Simulate rating if not provided
        if rating is None:
            if scenario == ProcessingScenario.SURVIVAL:
                # Higher ratings for survival-relevant items
                base = 3.0
                if item.category in [ItemCategory.FOOD, ItemCategory.TOOL, ItemCategory.SHELTER]:
                    base = 4.0
            else:
                base = 3.0

            rating = base + random.uniform(-1, 1)
            rating = max(1, min(5, rating))

        # Response time varies by scenario
        if scenario == ProcessingScenario.SURVIVAL:
            rt = 1500 + random.uniform(0, 500)  # Deeper processing
        else:
            rt = 1200 + random.uniform(0, 400)

        rating_obj = Rating(
            item_id=item_id,
            scenario=scenario,
            rating_value=rating,
            response_time_ms=rt
        )

        self._ratings[item_id] = rating_obj

        # Calculate encoding
        strength = self._model.calculate_encoding_strength(scenario, item, rating)
        relevance_boost = self._model.survival_relevance_boost(item.inherent_survival_relevance)

        if scenario == ProcessingScenario.SURVIVAL:
            strength += relevance_boost

        self._encoding_strengths[item_id] = strength

        return rating_obj

    def test_recall(
        self,
        item_id: str
    ) -> RecallResult:
        """Test recall of an item."""
        rating = self._ratings.get(item_id)
        if not rating:
            return None

        strength = self._encoding_strengths.get(item_id, 0.3)

        # Recall probability
        recall_prob = strength * 0.7 + 0.15
        recalled = random.random() < recall_prob

        return RecallResult(
            item_id=item_id,
            recalled=recalled,
            scenario=rating.scenario
        )


# ============================================================================
# EXPERIMENTAL PARADIGM
# ============================================================================

class SurvivalProcessingParadigm:
    """
    Survival processing advantage paradigm.

    "Ba'el's ancestral memory study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_standard_experiment(
        self,
        n_words: int = 30,
        n_per_condition: int = 10
    ) -> Dict[str, Any]:
        """Run standard survival processing experiment."""
        system = SurvivalProcessingSystem()

        # Word list
        words = [
            'apple', 'hammer', 'rope', 'blanket', 'knife',
            'water', 'rock', 'stick', 'fire', 'shelter',
            'berry', 'axe', 'vine', 'cave', 'spear',
            'fish', 'net', 'log', 'cliff', 'stream',
            'leaf', 'stone', 'branch', 'hill', 'trap',
            'fruit', 'tool', 'path', 'nest', 'bark'
        ]

        # Add items
        items = []
        for word in words[:n_words]:
            item = system.add_item(word, ItemCategory.RANDOM, SurvivalRelevance.MODERATE)
            items.append(item)

        # Assign to conditions
        random.shuffle(items)
        survival_items = items[:n_per_condition]
        moving_items = items[n_per_condition:n_per_condition*2]
        pleasantness_items = items[n_per_condition*2:n_per_condition*3]

        # Rate phase
        for item in survival_items:
            system.rate_item(item.id, ProcessingScenario.SURVIVAL)

        for item in moving_items:
            system.rate_item(item.id, ProcessingScenario.MOVING)

        for item in pleasantness_items:
            system.rate_item(item.id, ProcessingScenario.PLEASANTNESS)

        # Recall phase
        survival_recalled = sum(1 for item in survival_items
                               if system.test_recall(item.id).recalled)
        moving_recalled = sum(1 for item in moving_items
                             if system.test_recall(item.id).recalled)
        pleasantness_recalled = sum(1 for item in pleasantness_items
                                   if system.test_recall(item.id).recalled)

        survival_rate = survival_recalled / n_per_condition if n_per_condition > 0 else 0
        moving_rate = moving_recalled / n_per_condition if n_per_condition > 0 else 0
        pleasantness_rate = pleasantness_recalled / n_per_condition if n_per_condition > 0 else 0

        survival_advantage = survival_rate - max(moving_rate, pleasantness_rate)

        return {
            'n_words': n_words,
            'survival_recall': survival_rate,
            'moving_recall': moving_rate,
            'pleasantness_recall': pleasantness_rate,
            'survival_advantage': survival_advantage
        }

    def run_scenario_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare multiple scenarios."""
        results = {}

        for scenario in ProcessingScenario:
            system = SurvivalProcessingSystem()

            words = ['apple', 'hammer', 'rope', 'blanket', 'knife',
                    'water', 'rock', 'stick', 'fire', 'shelter']

            for word in words:
                item = system.add_item(word)
                system.rate_item(item.id, scenario)

            recalled = sum(1 for item_id in system._items.keys()
                          if system.test_recall(item_id).recalled)

            results[scenario.name] = recalled / 10

        return results

    def run_fitness_relevance_test(
        self
    ) -> Dict[str, Any]:
        """Test fitness-relevant categories."""
        system = SurvivalProcessingSystem()

        # Fitness-relevant items
        fitness_words = [
            ('apple', ItemCategory.FOOD),
            ('knife', ItemCategory.WEAPON),
            ('shelter', ItemCategory.SHELTER),
            ('water', ItemCategory.FOOD),
            ('fire', ItemCategory.TOOL)
        ]

        # Fitness-irrelevant items
        random_words = [
            ('chair', ItemCategory.RANDOM),
            ('book', ItemCategory.RANDOM),
            ('pen', ItemCategory.RANDOM),
            ('clock', ItemCategory.RANDOM),
            ('lamp', ItemCategory.RANDOM)
        ]

        fitness_items = []
        random_items = []

        for word, cat in fitness_words:
            item = system.add_item(word, cat, SurvivalRelevance.CRITICAL)
            system.rate_item(item.id, ProcessingScenario.SURVIVAL)
            fitness_items.append(item)

        for word, cat in random_words:
            item = system.add_item(word, cat, SurvivalRelevance.NONE)
            system.rate_item(item.id, ProcessingScenario.SURVIVAL)
            random_items.append(item)

        fitness_recalled = sum(1 for item in fitness_items
                              if system.test_recall(item.id).recalled)
        random_recalled = sum(1 for item in random_items
                             if system.test_recall(item.id).recalled)

        return {
            'fitness_relevant_recall': fitness_recalled / 5,
            'fitness_irrelevant_recall': random_recalled / 5,
            'category_effect': (fitness_recalled - random_recalled) / 5
        }


# ============================================================================
# SURVIVAL PROCESSING ENGINE
# ============================================================================

class SurvivalProcessingEngine:
    """
    Complete survival processing advantage engine.

    "Ba'el's evolutionary memory." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = SurvivalProcessingParadigm()
        self._system = SurvivalProcessingSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Item management

    def add_item(
        self,
        word: str,
        category: ItemCategory = ItemCategory.RANDOM
    ) -> StimulusItem:
        """Add an item."""
        return self._system.add_item(word, category)

    # Rating

    def rate(
        self,
        item_id: str,
        scenario: ProcessingScenario,
        rating: float = None
    ) -> Rating:
        """Rate an item."""
        return self._system.rate_item(item_id, scenario, rating)

    # Recall

    def test(
        self,
        item_id: str
    ) -> RecallResult:
        """Test recall."""
        return self._system.test_recall(item_id)

    # Experiments

    def run_survival_experiment(
        self,
        n_words: int = 30
    ) -> Dict[str, Any]:
        """Run survival processing experiment."""
        result = self._paradigm.run_standard_experiment(n_words)
        self._experiment_results.append(result)
        return result

    def run_scenario_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare scenarios."""
        return self._paradigm.run_scenario_comparison()

    def run_fitness_test(
        self
    ) -> Dict[str, Any]:
        """Test fitness relevance."""
        return self._paradigm.run_fitness_relevance_test()

    def run_ancestral_priorities_test(
        self
    ) -> Dict[str, Any]:
        """Test ancestral priority categories."""
        categories = [
            (ItemCategory.FOOD, 'food_recall'),
            (ItemCategory.SHELTER, 'shelter_recall'),
            (ItemCategory.WEAPON, 'weapon_recall'),
            (ItemCategory.RANDOM, 'random_recall')
        ]

        results = {}

        for cat, key in categories:
            system = SurvivalProcessingSystem()

            for i in range(5):
                item = system.add_item(f"item_{i}", cat, SurvivalRelevance.MODERATE)
                system.rate_item(item.id, ProcessingScenario.SURVIVAL)

            recalled = sum(1 for item_id in system._items.keys()
                          if system.test_recall(item_id).recalled)

            results[key] = recalled / 5

        return results

    # Analysis

    def get_metrics(self) -> SurvivalProcessingMetrics:
        """Get survival processing metrics."""
        if not self._experiment_results:
            self.run_survival_experiment()

        last = self._experiment_results[-1]

        return SurvivalProcessingMetrics(
            survival_recall=last['survival_recall'],
            moving_recall=last['moving_recall'],
            pleasantness_recall=last['pleasantness_recall'],
            survival_advantage=last['survival_advantage']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'items': len(self._system._items),
            'ratings': len(self._system._ratings),
            'experiments': len(self._experiment_results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_survival_processing_engine() -> SurvivalProcessingEngine:
    """Create survival processing engine."""
    return SurvivalProcessingEngine()


def demonstrate_survival_processing() -> Dict[str, Any]:
    """Demonstrate survival processing advantage."""
    engine = create_survival_processing_engine()

    # Standard experiment
    standard = engine.run_survival_experiment(30)

    # Scenario comparison
    scenarios = engine.run_scenario_comparison()

    # Fitness test
    fitness = engine.run_fitness_test()

    # Ancestral priorities
    ancestral = engine.run_ancestral_priorities_test()

    return {
        'survival_advantage': {
            'survival_recall': f"{standard['survival_recall']:.0%}",
            'moving_recall': f"{standard['moving_recall']:.0%}",
            'pleasantness_recall': f"{standard['pleasantness_recall']:.0%}",
            'advantage': f"{standard['survival_advantage']:.0%}"
        },
        'scenario_comparison': {
            scenario: f"{recall:.0%}"
            for scenario, recall in scenarios.items()
        },
        'fitness_relevance': {
            'relevant': f"{fitness['fitness_relevant_recall']:.0%}",
            'irrelevant': f"{fitness['fitness_irrelevant_recall']:.0%}",
            'effect': f"{fitness['category_effect']:.0%}"
        },
        'ancestral_categories': {
            cat: f"{recall:.0%}"
            for cat, recall in ancestral.items()
        },
        'interpretation': (
            f"Survival advantage: {standard['survival_advantage']:.0%}. "
            f"Processing for survival relevance enhances memory retention."
        )
    }


def get_survival_processing_facts() -> Dict[str, str]:
    """Get facts about survival processing advantage."""
    return {
        'nairne_et_al_2007': 'Original survival processing advantage',
        'evolutionary': 'Memory shaped by ancestral survival needs',
        'grasslands_scenario': 'Classic survival scenario used',
        'robustness': 'Effect replicates across many variations',
        'fitness_relevance': 'Items relevant to survival remembered better',
        'functional_approach': 'Memory serves adaptive functions',
        'beyond_elaboration': 'Effect exceeds depth of processing',
        'proximate_mechanisms': 'Elaboration, distinctiveness, relevance'
    }
