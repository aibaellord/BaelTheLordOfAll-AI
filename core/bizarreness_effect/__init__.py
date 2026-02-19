"""
BAEL Bizarreness Effect Engine
================================

Unusual items are remembered better.
Von Restorff effect and distinctiveness.

"Ba'el remembers the unusual." — Ba'el
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
import copy

logger = logging.getLogger("BAEL.BizarrenessEffect")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ItemType(Enum):
    """Types of items."""
    COMMON = auto()      # Ordinary, expected
    BIZARRE = auto()     # Strange, unusual
    ISOLATE = auto()      # Different from neighbors (von Restorff)


class BizarrenessType(Enum):
    """Types of bizarreness."""
    IMPOSSIBLE = auto()   # Physically impossible
    IMPROBABLE = auto()   # Unlikely but possible
    UNCOMMON = auto()     # Unusual
    INTERACTIVE = auto()  # Bizarre interaction between items


class ListContext(Enum):
    """Context for list learning."""
    PURE_COMMON = auto()     # All common items
    PURE_BIZARRE = auto()    # All bizarre items
    MIXED = auto()           # Both types


@dataclass
class LearningItem:
    """
    An item to learn.
    """
    id: str
    content: str
    item_type: ItemType
    bizarreness_type: Optional[BizarrenessType]
    distinctiveness: float
    imagery_strength: float


@dataclass
class EncodedMemory:
    """
    An encoded memory.
    """
    item_id: str
    content: str
    item_type: ItemType
    encoding_strength: float
    distinctiveness_boost: float
    list_position: int


@dataclass
class RecallResult:
    """
    Result of recall attempt.
    """
    item_id: str
    item_type: ItemType
    recalled: bool
    confidence: float
    list_position: int


@dataclass
class BizarrenessMetrics:
    """
    Bizarreness effect metrics.
    """
    common_recall: float
    bizarre_recall: float
    bizarreness_effect: float
    isolation_effect: float


# ============================================================================
# DISTINCTIVENESS MODEL
# ============================================================================

class DistinctivenessProcessor:
    """
    Processes item distinctiveness.

    "Ba'el detects distinctiveness." — Ba'el
    """

    def __init__(self):
        """Initialize processor."""
        self._lock = threading.RLock()

    def calculate_item_distinctiveness(
        self,
        item: LearningItem,
        list_context: ListContext,
        position: int,
        total_items: int
    ) -> float:
        """Calculate item distinctiveness."""
        base_distinctiveness = item.distinctiveness

        # Bizarre items in common context are more distinctive
        if item.item_type == ItemType.BIZARRE:
            if list_context == ListContext.MIXED:
                base_distinctiveness += 0.3
            elif list_context == ListContext.PURE_BIZARRE:
                # All bizarre = none distinctive
                base_distinctiveness -= 0.2

        # Isolate (von Restorff)
        if item.item_type == ItemType.ISOLATE:
            base_distinctiveness += 0.4

        # Serial position effects
        if position == 0:  # Primacy
            base_distinctiveness += 0.1
        elif position == total_items - 1:  # Recency
            base_distinctiveness += 0.15

        return max(0, min(1, base_distinctiveness))

    def calculate_imagery_boost(
        self,
        item: LearningItem
    ) -> float:
        """Calculate imagery boost for bizarre items."""
        if item.item_type == ItemType.BIZARRE:
            # Bizarre items create stronger mental images
            return item.imagery_strength * 0.3
        return item.imagery_strength * 0.1


# ============================================================================
# MEMORY MODEL
# ============================================================================

class BizarrenessMemory:
    """
    Memory model incorporating bizarreness effect.

    "Ba'el's distinctiveness memory." — Ba'el
    """

    def __init__(self):
        """Initialize memory."""
        self._processor = DistinctivenessProcessor()
        self._encoded: Dict[str, EncodedMemory] = {}

        # Bizarreness parameters
        self._bizarre_bonus = 0.15
        self._isolation_bonus = 0.25
        self._imagery_factor = 0.2

        self._lock = threading.RLock()

    def encode_list(
        self,
        items: List[LearningItem],
        list_context: ListContext
    ) -> List[EncodedMemory]:
        """Encode a list of items."""
        encoded = []

        for pos, item in enumerate(items):
            # Calculate distinctiveness
            distinctiveness = self._processor.calculate_item_distinctiveness(
                item, list_context, pos, len(items)
            )

            # Calculate imagery boost
            imagery_boost = self._processor.calculate_imagery_boost(item)

            # Base encoding
            base_strength = 0.5

            # Apply bonuses
            if item.item_type == ItemType.BIZARRE:
                if list_context == ListContext.MIXED:
                    base_strength += self._bizarre_bonus
                # Bizarre imagery helps
                base_strength += imagery_boost

            if item.item_type == ItemType.ISOLATE:
                base_strength += self._isolation_bonus

            # Distinctiveness boost
            distinctiveness_boost = distinctiveness * 0.2

            # Total strength
            trace_strength = min(1.0, base_strength + distinctiveness_boost)
            trace_strength += random.gauss(0, 0.05)
            trace_strength = max(0.1, min(1.0, trace_strength))

            enc = EncodedMemory(
                item_id=item.id,
                content=item.content,
                item_type=item.item_type,
                encoding_strength=trace_strength,
                distinctiveness_boost=distinctiveness_boost,
                list_position=pos
            )

            self._encoded[item.id] = enc
            encoded.append(enc)

        return encoded

    def retrieve(
        self,
        item_id: str,
        delay_minutes: float = 0
    ) -> Optional[RecallResult]:
        """Attempt retrieval."""
        encoded = self._encoded.get(item_id)
        if not encoded:
            return None

        # Apply forgetting
        decay = math.exp(-delay_minutes / 30)

        # Retrieval probability
        retrieval_prob = encoded.encoding_strength * decay

        # Distinctiveness helps resist forgetting
        retrieval_prob += encoded.distinctiveness_boost * 0.5 * (1 - decay)

        retrieval_prob = max(0, min(1, retrieval_prob))

        recalled = random.random() < retrieval_prob

        return RecallResult(
            item_id=item_id,
            item_type=encoded.item_type,
            recalled=recalled,
            confidence=retrieval_prob,
            list_position=encoded.list_position
        )

    def get_encoded(
        self,
        item_id: str
    ) -> Optional[EncodedMemory]:
        """Get encoded memory."""
        return self._encoded.get(item_id)


# ============================================================================
# EXPERIMENTAL PARADIGM
# ============================================================================

class BizarrenessParadigm:
    """
    Bizarreness effect experimental paradigm.

    "Ba'el's bizarreness experiment." — Ba'el
    """

    def __init__(
        self,
        memory: BizarrenessMemory
    ):
        """Initialize paradigm."""
        self._memory = memory

        self._items: Dict[str, LearningItem] = {}

        self._item_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._item_counter += 1
        return f"item_{self._item_counter}"

    def create_common_item(
        self,
        content: str
    ) -> LearningItem:
        """Create a common item."""
        item = LearningItem(
            id=self._generate_id(),
            content=content,
            item_type=ItemType.COMMON,
            bizarreness_type=None,
            distinctiveness=0.4,
            imagery_strength=0.4
        )
        self._items[item.id] = item
        return item

    def create_bizarre_item(
        self,
        content: str,
        bizarreness_type: BizarrenessType = BizarrenessType.IMPROBABLE
    ) -> LearningItem:
        """Create a bizarre item."""
        item = LearningItem(
            id=self._generate_id(),
            content=content,
            item_type=ItemType.BIZARRE,
            bizarreness_type=bizarreness_type,
            distinctiveness=0.7,
            imagery_strength=0.8
        )
        self._items[item.id] = item
        return item

    def create_isolate_item(
        self,
        content: str
    ) -> LearningItem:
        """Create an isolate (von Restorff) item."""
        item = LearningItem(
            id=self._generate_id(),
            content=content,
            item_type=ItemType.ISOLATE,
            bizarreness_type=None,
            distinctiveness=0.9,
            imagery_strength=0.5
        )
        self._items[item.id] = item
        return item

    def run_mixed_list_experiment(
        self,
        n_common: int = 15,
        n_bizarre: int = 5,
        delay_minutes: float = 5
    ) -> Dict[str, Any]:
        """Run mixed list experiment."""
        # Create items
        common_items = [
            self.create_common_item(f"common_sentence_{i}")
            for i in range(n_common)
        ]

        bizarre_items = [
            self.create_bizarre_item(f"bizarre_sentence_{i}")
            for i in range(n_bizarre)
        ]

        # Mix items (intersperse bizarre among common)
        all_items = []
        bizarre_positions = random.sample(range(n_common + n_bizarre), n_bizarre)
        bizarre_idx = 0
        common_idx = 0

        for pos in range(n_common + n_bizarre):
            if pos in bizarre_positions and bizarre_idx < len(bizarre_items):
                all_items.append(bizarre_items[bizarre_idx])
                bizarre_idx += 1
            else:
                all_items.append(common_items[common_idx])
                common_idx += 1

        # Study phase
        self._memory.encode_list(all_items, ListContext.MIXED)

        # Test phase
        common_results = []
        bizarre_results = []

        for item in all_items:
            result = self._memory.retrieve(item.id, delay_minutes)
            if result:
                if item.item_type == ItemType.COMMON:
                    common_results.append(result)
                else:
                    bizarre_results.append(result)

        common_recall = sum(1 for r in common_results if r.recalled) / len(common_results) if common_results else 0
        bizarre_recall = sum(1 for r in bizarre_results if r.recalled) / len(bizarre_results) if bizarre_results else 0

        return {
            'common_recall': common_recall,
            'bizarre_recall': bizarre_recall,
            'bizarreness_effect': bizarre_recall - common_recall,
            'n_common': n_common,
            'n_bizarre': n_bizarre
        }

    def run_von_restorff_experiment(
        self,
        n_items: int = 15,
        isolate_position: int = 7,
        delay_minutes: float = 5
    ) -> Dict[str, Any]:
        """Run von Restorff (isolation) experiment."""
        # Create list with one isolate
        items = []

        for i in range(n_items):
            if i == isolate_position:
                items.append(self.create_isolate_item(f"ISOLATE_ITEM"))
            else:
                items.append(self.create_common_item(f"common_{i}"))

        # Study
        self._memory.encode_list(items, ListContext.MIXED)

        # Test
        results = []
        for item in items:
            result = self._memory.retrieve(item.id, delay_minutes)
            if result:
                results.append(result)

        # Separate isolate and common
        isolate_result = next((r for r in results if r.item_type == ItemType.ISOLATE), None)
        common_results = [r for r in results if r.item_type == ItemType.COMMON]

        common_recall = sum(1 for r in common_results if r.recalled) / len(common_results) if common_results else 0
        isolate_recalled = isolate_result.recalled if isolate_result else False

        return {
            'common_recall': common_recall,
            'isolate_recalled': isolate_recalled,
            'isolation_effect': (1 if isolate_recalled else 0) - common_recall
        }


# ============================================================================
# BIZARRENESS EFFECT ENGINE
# ============================================================================

class BizarrenessEffectEngine:
    """
    Complete bizarreness effect engine.

    "Ba'el's unusual memory advantage." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._memory = BizarrenessMemory()
        self._paradigm = BizarrenessParadigm(self._memory)

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Item creation

    def create_common(
        self,
        content: str
    ) -> LearningItem:
        """Create common item."""
        return self._paradigm.create_common_item(content)

    def create_bizarre(
        self,
        content: str,
        bizarreness_type: BizarrenessType = BizarrenessType.IMPROBABLE
    ) -> LearningItem:
        """Create bizarre item."""
        return self._paradigm.create_bizarre_item(content, bizarreness_type)

    def create_isolate(
        self,
        content: str
    ) -> LearningItem:
        """Create isolate item."""
        return self._paradigm.create_isolate_item(content)

    # Encoding

    def encode_list(
        self,
        items: List[LearningItem],
        context: ListContext = ListContext.MIXED
    ) -> List[EncodedMemory]:
        """Encode a list of items."""
        return self._memory.encode_list(items, context)

    # Retrieval

    def recall(
        self,
        item_id: str,
        delay_minutes: float = 0
    ) -> Optional[RecallResult]:
        """Attempt recall."""
        return self._memory.retrieve(item_id, delay_minutes)

    # Experiments

    def run_bizarreness_experiment(
        self,
        n_common: int = 15,
        n_bizarre: int = 5,
        delay_minutes: float = 5
    ) -> Dict[str, Any]:
        """Run bizarreness experiment."""
        result = self._paradigm.run_mixed_list_experiment(n_common, n_bizarre, delay_minutes)
        self._experiment_results.append(result)
        return result

    def run_isolation_experiment(
        self,
        n_items: int = 15,
        delay_minutes: float = 5
    ) -> Dict[str, Any]:
        """Run von Restorff experiment."""
        result = self._paradigm.run_von_restorff_experiment(n_items, n_items // 2, delay_minutes)
        self._experiment_results.append(result)
        return result

    def compare_list_contexts(
        self,
        n_items: int = 20,
        delay_minutes: float = 5
    ) -> Dict[str, Any]:
        """Compare pure vs mixed list contexts."""
        # Pure bizarre list
        pure_bizarre = BizarrenessMemory()
        bizarre_items = [
            LearningItem(
                id=f"pb_{i}",
                content=f"bizarre_{i}",
                item_type=ItemType.BIZARRE,
                bizarreness_type=BizarrenessType.IMPROBABLE,
                distinctiveness=0.7,
                imagery_strength=0.8
            )
            for i in range(n_items)
        ]
        pure_bizarre.encode_list(bizarre_items, ListContext.PURE_BIZARRE)

        pure_results = []
        for item in bizarre_items:
            result = pure_bizarre.retrieve(item.id, delay_minutes)
            if result:
                pure_results.append(result)

        pure_recall = sum(1 for r in pure_results if r.recalled) / len(pure_results) if pure_results else 0

        # Mixed list (for comparison)
        mixed_result = self.run_bizarreness_experiment(15, 5, delay_minutes)

        return {
            'pure_bizarre_recall': pure_recall,
            'mixed_bizarre_recall': mixed_result['bizarre_recall'],
            'mixed_common_recall': mixed_result['common_recall'],
            'list_context_effect': mixed_result['bizarre_recall'] - pure_recall
        }

    # Analysis

    def get_metrics(self) -> BizarrenessMetrics:
        """Get bizarreness metrics."""
        if not self._experiment_results:
            self.run_bizarreness_experiment(15, 5, 5)

        last = self._experiment_results[-1]

        # Run isolation experiment for isolation effect
        isolation = self.run_isolation_experiment(15, 5)

        return BizarrenessMetrics(
            common_recall=last.get('common_recall', 0),
            bizarre_recall=last.get('bizarre_recall', 0),
            bizarreness_effect=last.get('bizarreness_effect', 0),
            isolation_effect=isolation.get('isolation_effect', 0)
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'encoded_items': len(self._memory._encoded),
            'experiments': len(self._experiment_results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_bizarreness_effect_engine() -> BizarrenessEffectEngine:
    """Create bizarreness effect engine."""
    return BizarrenessEffectEngine()


def demonstrate_bizarreness_effect() -> Dict[str, Any]:
    """Demonstrate bizarreness effect."""
    engine = create_bizarreness_effect_engine()

    # Bizarreness experiment
    bizarre = engine.run_bizarreness_experiment(15, 5, 5)

    # Isolation experiment
    isolation = engine.run_isolation_experiment(15, 5)

    # List context comparison
    context = engine.compare_list_contexts(20, 5)

    return {
        'bizarreness_effect': {
            'common_recall': f"{bizarre['common_recall']:.0%}",
            'bizarre_recall': f"{bizarre['bizarre_recall']:.0%}",
            'effect': f"{bizarre['bizarreness_effect']:.0%}"
        },
        'von_restorff': {
            'common_recall': f"{isolation['common_recall']:.0%}",
            'isolate_recalled': isolation['isolate_recalled'],
            'effect': f"{isolation['isolation_effect']:.0%}"
        },
        'list_context': {
            'pure_bizarre': f"{context['pure_bizarre_recall']:.0%}",
            'mixed_bizarre': f"{context['mixed_bizarre_recall']:.0%}",
            'context_effect': f"{context['list_context_effect']:.0%}"
        },
        'interpretation': (
            f"Bizarreness effect: {bizarre['bizarreness_effect']:.0%}. "
            f"Unusual items stand out and are better remembered in mixed lists."
        )
    }


def get_bizarreness_effect_facts() -> Dict[str, str]:
    """Get facts about bizarreness effect."""
    return {
        'distinctiveness': 'Bizarre items are more distinctive in memory',
        'mixed_list_required': 'Effect strongest when bizarre items are rare in list',
        'von_restorff': 'Isolation effect: different item stands out',
        'imagery': 'Bizarre items create stronger mental images',
        'pure_list_paradox': 'All bizarre = none distinctive',
        'attention': 'Distinctiveness captures attention during encoding',
        'elaboration': 'Bizarre items receive more elaborative processing',
        'false_memory': 'High distinctiveness can reduce false memories'
    }
