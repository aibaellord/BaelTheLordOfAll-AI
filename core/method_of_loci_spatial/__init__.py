"""
BAEL Method Of Loci Spatial Engine
====================================

Memory palace technique using spatial locations.
Ancient Greek mnemonic system.

"Ba'el walks through infinite memory palaces." — Ba'el
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

logger = logging.getLogger("BAEL.MethodOfLociSpatial")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class LocationType(Enum):
    """Type of locus."""
    ROOM = auto()
    FURNITURE = auto()
    OBJECT = auto()
    LANDMARK = auto()
    PATH_POINT = auto()


class ImageryType(Enum):
    """Type of imagery."""
    STATIC = auto()
    ANIMATED = auto()
    INTERACTIVE = auto()
    BIZARRE = auto()


class PalaceType(Enum):
    """Type of memory palace."""
    HOME = auto()
    ROUTE = auto()
    BUILDING = auto()
    FANTASY = auto()


class EncodingStrength(Enum):
    """Strength of encoding."""
    WEAK = auto()
    MODERATE = auto()
    STRONG = auto()
    VIVID = auto()


@dataclass
class Locus:
    """
    A location in the memory palace.
    """
    id: str
    name: str
    location_type: LocationType
    position: int           # Order in route
    vividness: float


@dataclass
class MemoryPalace:
    """
    A memory palace.
    """
    id: str
    name: str
    palace_type: PalaceType
    loci: List[Locus]
    familiarity: float


@dataclass
class PlacedItem:
    """
    An item placed at a locus.
    """
    id: str
    content: str
    locus: Locus
    imagery: str
    imagery_type: ImageryType
    encoding_strength: EncodingStrength


@dataclass
class RetrievalResult:
    """
    Result of retrieval attempt.
    """
    item: PlacedItem
    recalled: bool
    order_correct: bool
    latency_ms: int


@dataclass
class MethodOfLociMetrics:
    """
    Method of loci metrics.
    """
    recall_rate: float
    order_accuracy: float
    average_latency: float
    advantage_over_rote: float


# ============================================================================
# METHOD OF LOCI MODEL
# ============================================================================

class MethodOfLociModel:
    """
    Model of method of loci.

    "Ba'el's spatial memory model." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Base recall (rote learning)
        self._base_rote_recall = 0.45

        # Loci advantage
        self._loci_advantage = 0.35

        # Imagery effects
        self._imagery_boost = {
            ImageryType.STATIC: 0.10,
            ImageryType.ANIMATED: 0.15,
            ImageryType.INTERACTIVE: 0.18,
            ImageryType.BIZARRE: 0.22
        }

        # Encoding strength
        self._encoding_effects = {
            EncodingStrength.WEAK: -0.10,
            EncodingStrength.MODERATE: 0.0,
            EncodingStrength.STRONG: 0.10,
            EncodingStrength.VIVID: 0.20
        }

        # Palace familiarity
        self._familiarity_weight = 0.15

        # Locus distinctiveness
        self._distinctiveness_weight = 0.10

        # Serial position in palace
        self._primacy = 0.08
        self._recency = 0.05

        # Order preservation
        self._order_accuracy_base = 0.85

        # Retrieval time
        self._base_rt_ms = 1500
        self._rt_per_item = 200

        # Expert effects
        self._expert_boost = 0.15

        self._lock = threading.RLock()

    def calculate_recall_probability(
        self,
        item: PlacedItem,
        palace: MemoryPalace,
        list_length: int = 20
    ) -> float:
        """Calculate recall probability for placed item."""
        # Start with loci advantage
        base = self._base_rote_recall + self._loci_advantage

        # Imagery type
        base += self._imagery_boost[item.imagery_type]

        # Encoding strength
        base += self._encoding_effects[item.encoding_strength]

        # Palace familiarity
        base += palace.familiarity * self._familiarity_weight

        # Locus vividness
        base += item.locus.vividness * self._distinctiveness_weight

        # Serial position
        pos = item.locus.position
        if pos <= 3:  # Primacy
            base += self._primacy * (4 - pos) / 3
        elif pos >= list_length - 2:  # Recency
            base += self._recency * (pos - list_length + 3) / 3

        # Add noise
        base += random.uniform(-0.08, 0.08)

        return max(0.20, min(0.98, base))

    def calculate_order_accuracy(
        self,
        palace: MemoryPalace
    ) -> float:
        """Calculate order accuracy."""
        base = self._order_accuracy_base

        # Familiarity helps order
        base += palace.familiarity * 0.10

        # Add noise
        base += random.uniform(-0.05, 0.05)

        return max(0.50, min(0.99, base))

    def calculate_retrieval_time(
        self,
        position: int
    ) -> int:
        """Calculate retrieval time in ms."""
        rt = self._base_rt_ms + position * self._rt_per_item
        rt += random.gauss(0, 300)
        return max(500, int(rt))

    def get_principles(
        self
    ) -> Dict[str, str]:
        """Get method of loci principles."""
        return {
            'familiar_palace': 'Use well-known location',
            'distinct_loci': 'Choose distinctive locations',
            'vivid_imagery': 'Create vivid, memorable images',
            'interaction': 'Have items interact with loci',
            'sequential': 'Follow consistent path',
            'bizarreness': 'Strange images remembered better'
        }

    def get_history(
        self
    ) -> Dict[str, str]:
        """Get historical context."""
        return {
            'simonides': 'Originated with Simonides of Ceos (~500 BCE)',
            'greece': 'Used by Greek orators',
            'rome': 'Roman rhetoricians (Cicero)',
            'medieval': 'Medieval scholars and monks',
            'modern': 'Memory athletes and competitions'
        }

    def get_advantages(
        self
    ) -> Dict[str, str]:
        """Get advantages of method."""
        return {
            'order': 'Excellent for ordered recall',
            'capacity': 'Can encode long lists',
            'durability': 'Memories persist longer',
            'reusable': 'Palace can be reused',
            'expandable': 'Add new loci as needed'
        }


# ============================================================================
# METHOD OF LOCI SYSTEM
# ============================================================================

class MethodOfLociSystem:
    """
    Method of loci system.

    "Ba'el's memory palace system." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = MethodOfLociModel()

        self._palaces: Dict[str, MemoryPalace] = {}
        self._placed_items: Dict[str, PlacedItem] = {}
        self._results: List[RetrievalResult] = []

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self, prefix: str = "item") -> str:
        self._counter += 1
        return f"{prefix}_{self._counter}"

    def create_palace(
        self,
        name: str,
        palace_type: PalaceType = PalaceType.HOME,
        n_loci: int = 10,
        familiarity: float = 0.8
    ) -> MemoryPalace:
        """Create memory palace with loci."""
        loci = []

        for i in range(n_loci):
            locus = Locus(
                id=self._generate_id("locus"),
                name=f"Locus_{i}",
                location_type=random.choice(list(LocationType)),
                position=i,
                vividness=random.uniform(0.5, 0.9)
            )
            loci.append(locus)

        palace = MemoryPalace(
            id=self._generate_id("palace"),
            name=name,
            palace_type=palace_type,
            loci=loci,
            familiarity=familiarity
        )

        self._palaces[palace.id] = palace

        return palace

    def place_item(
        self,
        content: str,
        locus: Locus,
        imagery_type: ImageryType = ImageryType.INTERACTIVE,
        encoding_strength: EncodingStrength = EncodingStrength.STRONG
    ) -> PlacedItem:
        """Place item at locus."""
        item = PlacedItem(
            id=self._generate_id("item"),
            content=content,
            locus=locus,
            imagery=f"Image of {content} at {locus.name}",
            imagery_type=imagery_type,
            encoding_strength=encoding_strength
        )

        self._placed_items[item.id] = item

        return item

    def retrieve_item(
        self,
        item: PlacedItem,
        palace: MemoryPalace
    ) -> RetrievalResult:
        """Attempt to retrieve item."""
        prob = self._model.calculate_recall_probability(
            item, palace, len(palace.loci)
        )

        recalled = random.random() < prob

        order_acc = self._model.calculate_order_accuracy(palace)
        order_correct = random.random() < order_acc if recalled else False

        rt = self._model.calculate_retrieval_time(item.locus.position)

        result = RetrievalResult(
            item=item,
            recalled=recalled,
            order_correct=order_correct,
            latency_ms=rt
        )

        self._results.append(result)

        return result


# ============================================================================
# METHOD OF LOCI PARADIGM
# ============================================================================

class MethodOfLociParadigm:
    """
    Method of loci paradigm.

    "Ba'el's memory palace study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_basic_paradigm(
        self,
        n_items: int = 20
    ) -> Dict[str, Any]:
        """Run basic method of loci paradigm."""
        system = MethodOfLociSystem()

        # Create palace
        palace = system.create_palace("MyHome", n_loci=n_items)

        # Place items
        items = []
        for i, locus in enumerate(palace.loci):
            item = system.place_item(
                f"Item_{i}",
                locus,
                imagery_type=random.choice(list(ImageryType)),
                encoding_strength=EncodingStrength.STRONG
            )
            items.append(item)

        # Retrieve
        results = []
        for item in items:
            result = system.retrieve_item(item, palace)
            results.append(result)

        # Calculate metrics
        recall_rate = sum(r.recalled for r in results) / len(results)
        order_correct = sum(r.order_correct for r in results) / len(results)
        avg_rt = sum(r.latency_ms for r in results) / len(results)

        # Compare to rote
        model = MethodOfLociModel()
        rote_rate = model._base_rote_recall
        advantage = recall_rate - rote_rate

        return {
            'recall_rate': recall_rate,
            'order_accuracy': order_correct,
            'average_rt_ms': avg_rt,
            'rote_recall': rote_rate,
            'loci_advantage': advantage,
            'interpretation': f'Loci advantage: {advantage:.0%} over rote'
        }

    def run_imagery_study(
        self
    ) -> Dict[str, Any]:
        """Study imagery type effects."""
        model = MethodOfLociModel()

        results = {}

        for imagery_type in ImageryType:
            boost = model._imagery_boost[imagery_type]
            recall = model._base_rote_recall + model._loci_advantage + boost
            results[imagery_type.name] = {'recall': recall, 'boost': boost}

        return {
            'by_imagery': results,
            'interpretation': 'Bizarre imagery most effective'
        }

    def run_familiarity_study(
        self
    ) -> Dict[str, Any]:
        """Study palace familiarity effects."""
        model = MethodOfLociModel()

        familiarities = [0.2, 0.4, 0.6, 0.8, 1.0]

        results = {}

        for fam in familiarities:
            recall = (
                model._base_rote_recall +
                model._loci_advantage +
                fam * model._familiarity_weight
            )
            results[f'familiarity_{int(fam*100)}'] = {'recall': recall}

        return {
            'by_familiarity': results,
            'interpretation': 'More familiar palace = better recall'
        }

    def run_list_length_study(
        self
    ) -> Dict[str, Any]:
        """Study list length effects."""
        lengths = [10, 20, 40, 80]

        results = {}

        for length in lengths:
            system = MethodOfLociSystem()
            palace = system.create_palace("Palace", n_loci=length)

            items = []
            for i, locus in enumerate(palace.loci):
                item = system.place_item(f"Item_{i}", locus)
                items.append(item)

            recalls = []
            for item in items:
                result = system.retrieve_item(item, palace)
                recalls.append(result.recalled)

            recall_rate = sum(recalls) / len(recalls)
            results[f'length_{length}'] = {'recall': recall_rate}

        return {
            'by_length': results,
            'interpretation': 'Method scales well with length'
        }

    def run_principles_study(
        self
    ) -> Dict[str, Any]:
        """Study method principles."""
        model = MethodOfLociModel()

        principles = model.get_principles()
        history = model.get_history()
        advantages = model.get_advantages()

        return {
            'principles': principles,
            'history': history,
            'advantages': advantages,
            'interpretation': 'Ancient technique with proven effectiveness'
        }

    def run_comparison_study(
        self
    ) -> Dict[str, Any]:
        """Compare with other strategies."""
        model = MethodOfLociModel()

        strategies = {
            'rote_rehearsal': model._base_rote_recall,
            'method_of_loci': model._base_rote_recall + model._loci_advantage,
            'loci_with_bizarre': (
                model._base_rote_recall +
                model._loci_advantage +
                model._imagery_boost[ImageryType.BIZARRE]
            ),
            'loci_expert': (
                model._base_rote_recall +
                model._loci_advantage +
                model._expert_boost
            )
        }

        return {
            'by_strategy': strategies,
            'best': max(strategies, key=strategies.get),
            'interpretation': 'Loci with expertise most effective'
        }


# ============================================================================
# METHOD OF LOCI ENGINE
# ============================================================================

class MethodOfLociEngine:
    """
    Complete method of loci engine.

    "Ba'el's memory palace engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = MethodOfLociParadigm()
        self._system = MethodOfLociSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Palace operations

    def create_palace(
        self,
        name: str,
        n_loci: int = 10
    ) -> MemoryPalace:
        """Create palace."""
        return self._system.create_palace(name, n_loci=n_loci)

    def place_item(
        self,
        content: str,
        locus: Locus
    ) -> PlacedItem:
        """Place item."""
        return self._system.place_item(content, locus)

    def retrieve_item(
        self,
        item: PlacedItem,
        palace: MemoryPalace
    ) -> RetrievalResult:
        """Retrieve item."""
        return self._system.retrieve_item(item, palace)

    # Experiments

    def run_basic(
        self
    ) -> Dict[str, Any]:
        """Run basic paradigm."""
        result = self._paradigm.run_basic_paradigm()
        self._experiment_results.append(result)
        return result

    def study_imagery(
        self
    ) -> Dict[str, Any]:
        """Study imagery."""
        return self._paradigm.run_imagery_study()

    def study_familiarity(
        self
    ) -> Dict[str, Any]:
        """Study familiarity."""
        return self._paradigm.run_familiarity_study()

    def study_list_length(
        self
    ) -> Dict[str, Any]:
        """Study list length."""
        return self._paradigm.run_list_length_study()

    def study_principles(
        self
    ) -> Dict[str, Any]:
        """Study principles."""
        return self._paradigm.run_principles_study()

    def compare_strategies(
        self
    ) -> Dict[str, Any]:
        """Compare strategies."""
        return self._paradigm.run_comparison_study()

    # Analysis

    def get_metrics(self) -> MethodOfLociMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_basic()

        last = self._experiment_results[-1]

        return MethodOfLociMetrics(
            recall_rate=last['recall_rate'],
            order_accuracy=last['order_accuracy'],
            average_latency=last['average_rt_ms'],
            advantage_over_rote=last['loci_advantage']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'palaces': len(self._system._palaces),
            'items': len(self._system._placed_items),
            'retrievals': len(self._system._results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_method_of_loci_engine() -> MethodOfLociEngine:
    """Create method of loci engine."""
    return MethodOfLociEngine()


def demonstrate_method_of_loci() -> Dict[str, Any]:
    """Demonstrate method of loci."""
    engine = create_method_of_loci_engine()

    # Basic
    basic = engine.run_basic()

    # Imagery
    imagery = engine.study_imagery()

    # Familiarity
    familiarity = engine.study_familiarity()

    # Principles
    principles = engine.study_principles()

    return {
        'basic': {
            'recall': f"{basic['recall_rate']:.0%}",
            'order': f"{basic['order_accuracy']:.0%}",
            'advantage': f"{basic['loci_advantage']:.0%}"
        },
        'by_imagery': {
            k: f"boost={v['boost']:.0%}"
            for k, v in imagery['by_imagery'].items()
        },
        'principles': list(principles['principles'].keys())[:4],
        'interpretation': (
            f"Recall: {basic['recall_rate']:.0%}. "
            f"Advantage: {basic['loci_advantage']:.0%}. "
            f"Ancient technique with modern validation."
        )
    }


def get_method_of_loci_facts() -> Dict[str, str]:
    """Get facts about method of loci."""
    return {
        'simonides': 'Originated ~500 BCE',
        'name': 'Also called "memory palace"',
        'effectiveness': '30-40% advantage over rote',
        'order': 'Excellent for ordered recall',
        'capacity': 'Can encode 100+ items',
        'athletes': 'Used by memory champions',
        'brain': 'Activates spatial memory regions',
        'reusable': 'Palace can be reused many times'
    }
