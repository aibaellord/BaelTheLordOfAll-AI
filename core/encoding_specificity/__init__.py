"""
BAEL Encoding Specificity Engine
=================================

Tulving's encoding specificity principle.
Context-dependent memory.

"Ba'el remembers in context." — Ba'el
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

logger = logging.getLogger("BAEL.EncodingSpecificity")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ContextType(Enum):
    """Types of context."""
    ENVIRONMENTAL = auto()    # Physical location
    EMOTIONAL = auto()        # Mood state
    PHYSIOLOGICAL = auto()    # Body state
    COGNITIVE = auto()        # Mental state
    SEMANTIC = auto()         # Meaning context


class CueType(Enum):
    """Types of retrieval cues."""
    COPY_CUE = auto()         # Exact encoding cue
    EXTRALIST_CUE = auto()    # Related but not encoded
    CONTEXT_CUE = auto()      # Contextual reinstatement
    CATEGORY_CUE = auto()     # Category name


class MatchLevel(Enum):
    """Level of encoding-retrieval match."""
    IDENTICAL = auto()        # Perfect match
    HIGH = auto()             # Very similar
    MODERATE = auto()         # Some overlap
    LOW = auto()              # Little overlap
    MISMATCH = auto()         # No match


@dataclass
class Context:
    """
    A context for encoding/retrieval.
    """
    id: str
    context_type: ContextType
    features: Dict[str, Any]
    intensity: float = 1.0


@dataclass
class EncodedItem:
    """
    An encoded memory item.
    """
    id: str
    target: str
    cue: str
    encoding_context: Context
    strength: float = 1.0
    timestamp: float = 0.0


@dataclass
class RetrievalCue:
    """
    A retrieval cue.
    """
    cue: str
    cue_type: CueType
    context: Optional[Context]


@dataclass
class RetrievalAttempt:
    """
    A retrieval attempt.
    """
    item_id: str
    cue: RetrievalCue
    match_level: MatchLevel
    success: bool
    recalled_item: Optional[str]
    latency: float


@dataclass
class ESMetrics:
    """
    Encoding specificity metrics.
    """
    copy_cue_recall: float
    extralist_recall: float
    context_effect: float
    match_benefit: float


# ============================================================================
# CONTEXT MANAGER
# ============================================================================

class ContextManager:
    """
    Manage contexts.

    "Ba'el manages encoding contexts." — Ba'el
    """

    def __init__(self):
        """Initialize manager."""
        self._contexts: Dict[str, Context] = {}
        self._context_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._context_counter += 1
        return f"ctx_{self._context_counter}"

    def create_context(
        self,
        context_type: ContextType,
        features: Dict[str, Any],
        intensity: float = 1.0
    ) -> Context:
        """Create a new context."""
        ctx = Context(
            id=self._generate_id(),
            context_type=context_type,
            features=features,
            intensity=intensity
        )

        self._contexts[ctx.id] = ctx
        return ctx

    def calculate_similarity(
        self,
        ctx1: Context,
        ctx2: Context
    ) -> float:
        """Calculate context similarity."""
        if ctx1.id == ctx2.id:
            return 1.0

        if ctx1.context_type != ctx2.context_type:
            return 0.1

        # Feature overlap
        keys1 = set(ctx1.features.keys())
        keys2 = set(ctx2.features.keys())

        common_keys = keys1 & keys2
        all_keys = keys1 | keys2

        if not all_keys:
            return 0.5

        key_overlap = len(common_keys) / len(all_keys)

        # Value match for common keys
        value_matches = 0
        for key in common_keys:
            if ctx1.features[key] == ctx2.features[key]:
                value_matches += 1

        value_sim = value_matches / len(common_keys) if common_keys else 0.5

        return 0.5 * key_overlap + 0.5 * value_sim

    def get_match_level(
        self,
        similarity: float
    ) -> MatchLevel:
        """Get match level from similarity."""
        if similarity >= 0.95:
            return MatchLevel.IDENTICAL
        elif similarity >= 0.7:
            return MatchLevel.HIGH
        elif similarity >= 0.4:
            return MatchLevel.MODERATE
        elif similarity >= 0.2:
            return MatchLevel.LOW
        else:
            return MatchLevel.MISMATCH


# ============================================================================
# ENCODER
# ============================================================================

class ESEncoder:
    """
    Encode items with context.

    "Ba'el encodes with context." — Ba'el
    """

    def __init__(self):
        """Initialize encoder."""
        self._items: Dict[str, EncodedItem] = {}
        self._item_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._item_counter += 1
        return f"item_{self._item_counter}"

    def encode(
        self,
        target: str,
        cue: str,
        context: Context,
        strength: float = 1.0
    ) -> EncodedItem:
        """Encode a target-cue pair in context."""
        item = EncodedItem(
            id=self._generate_id(),
            target=target,
            cue=cue,
            encoding_context=context,
            strength=strength,
            timestamp=time.time()
        )

        self._items[item.id] = item
        return item

    def get_item(
        self,
        item_id: str
    ) -> Optional[EncodedItem]:
        """Get an encoded item."""
        return self._items.get(item_id)

    def find_by_cue(
        self,
        cue: str
    ) -> List[EncodedItem]:
        """Find items by cue."""
        return [
            item for item in self._items.values()
            if item.cue.lower() == cue.lower()
        ]

    def decay(
        self,
        rate: float = 0.1
    ) -> None:
        """Apply decay to all items."""
        for item in self._items.values():
            item.strength = max(0.01, item.strength - rate)


# ============================================================================
# RETRIEVER
# ============================================================================

class ESRetriever:
    """
    Retrieve items with cue matching.

    "Ba'el retrieves with specificity." — Ba'el
    """

    def __init__(
        self,
        encoder: ESEncoder,
        context_mgr: ContextManager
    ):
        """Initialize retriever."""
        self._encoder = encoder
        self._context_mgr = context_mgr
        self._lock = threading.RLock()

    def retrieve(
        self,
        cue: RetrievalCue,
        target_item: EncodedItem = None
    ) -> RetrievalAttempt:
        """Attempt retrieval with cue."""
        # Find items matching the cue
        if target_item:
            items = [target_item]
        else:
            items = self._encoder.find_by_cue(cue.cue)

        if not items:
            return RetrievalAttempt(
                item_id="",
                cue=cue,
                match_level=MatchLevel.MISMATCH,
                success=False,
                recalled_item=None,
                latency=0.0
            )

        # Evaluate each item
        best_item = None
        best_prob = 0.0

        for item in items:
            prob = self._calculate_retrieval_probability(item, cue)
            if prob > best_prob:
                best_prob = prob
                best_item = item

        if not best_item:
            return RetrievalAttempt(
                item_id="",
                cue=cue,
                match_level=MatchLevel.MISMATCH,
                success=False,
                recalled_item=None,
                latency=0.0
            )

        # Determine match level
        if cue.context:
            similarity = self._context_mgr.calculate_similarity(
                best_item.encoding_context, cue.context
            )
            match_level = self._context_mgr.get_match_level(similarity)
        else:
            match_level = MatchLevel.MODERATE

        # Attempt retrieval
        success = random.random() < best_prob

        # Calculate latency (inversely related to match)
        base_latency = 2.0 - best_prob
        latency = max(0.5, base_latency + random.uniform(0, 0.5))

        return RetrievalAttempt(
            item_id=best_item.id,
            cue=cue,
            match_level=match_level,
            success=success,
            recalled_item=best_item.target if success else None,
            latency=latency
        )

    def _calculate_retrieval_probability(
        self,
        item: EncodedItem,
        cue: RetrievalCue
    ) -> float:
        """Calculate retrieval probability."""
        base_prob = item.strength

        # Cue match
        cue_match = 1.0 if item.cue.lower() == cue.cue.lower() else 0.3

        # Context match
        context_match = 1.0
        if cue.context and item.encoding_context:
            context_match = self._context_mgr.calculate_similarity(
                item.encoding_context, cue.context
            )

        # Cue type effect
        cue_type_factor = {
            CueType.COPY_CUE: 1.0,
            CueType.EXTRALIST_CUE: 0.5,
            CueType.CONTEXT_CUE: 0.7,
            CueType.CATEGORY_CUE: 0.6
        }
        type_factor = cue_type_factor.get(cue.cue_type, 0.5)

        # Encoding specificity: effective cue = encoding-retrieval overlap
        probability = (
            base_prob * 0.3 +
            cue_match * 0.3 +
            context_match * 0.3 +
            type_factor * 0.1
        )

        return min(1.0, probability)


# ============================================================================
# ENCODING SPECIFICITY ENGINE
# ============================================================================

class EncodingSpecificityEngine:
    """
    Complete encoding specificity engine.

    "Ba'el's context-dependent memory." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._context_mgr = ContextManager()
        self._encoder = ESEncoder()
        self._retriever = ESRetriever(self._encoder, self._context_mgr)

        self._attempts: List[RetrievalAttempt] = []

        self._lock = threading.RLock()

    # Context management

    def create_context(
        self,
        context_type: ContextType,
        features: Dict[str, Any]
    ) -> Context:
        """Create a context."""
        return self._context_mgr.create_context(context_type, features)

    # Encoding

    def encode(
        self,
        target: str,
        cue: str,
        context: Context
    ) -> EncodedItem:
        """Encode a target-cue pair."""
        return self._encoder.encode(target, cue, context)

    def encode_list(
        self,
        pairs: List[Tuple[str, str]],
        context: Context
    ) -> List[EncodedItem]:
        """Encode a list of target-cue pairs."""
        return [
            self._encoder.encode(target, cue, context)
            for target, cue in pairs
        ]

    # Retrieval

    def recall_with_copy_cue(
        self,
        item: EncodedItem,
        context: Context = None
    ) -> RetrievalAttempt:
        """Recall with the original encoding cue."""
        cue = RetrievalCue(
            cue=item.cue,
            cue_type=CueType.COPY_CUE,
            context=context or item.encoding_context
        )

        attempt = self._retriever.retrieve(cue, item)
        self._attempts.append(attempt)
        return attempt

    def recall_with_extralist_cue(
        self,
        item: EncodedItem,
        extralist_cue: str,
        context: Context = None
    ) -> RetrievalAttempt:
        """Recall with a semantically related but not encoded cue."""
        cue = RetrievalCue(
            cue=extralist_cue,
            cue_type=CueType.EXTRALIST_CUE,
            context=context
        )

        attempt = self._retriever.retrieve(cue, item)
        self._attempts.append(attempt)
        return attempt

    def recall_with_context(
        self,
        item: EncodedItem,
        context: Context
    ) -> RetrievalAttempt:
        """Recall with context reinstatement."""
        cue = RetrievalCue(
            cue=item.cue,
            cue_type=CueType.CONTEXT_CUE,
            context=context
        )

        attempt = self._retriever.retrieve(cue, item)
        self._attempts.append(attempt)
        return attempt

    # Context manipulation

    def test_context_reinstatement(
        self,
        item: EncodedItem,
        same_context: bool
    ) -> RetrievalAttempt:
        """Test effect of context reinstatement."""
        if same_context:
            context = item.encoding_context
        else:
            # Create different context
            context = self._context_mgr.create_context(
                item.encoding_context.context_type,
                {'different': True}
            )

        return self.recall_with_context(item, context)

    # Delay

    def simulate_delay(
        self,
        hours: float = 1.0
    ) -> None:
        """Simulate retention interval."""
        decay_rate = 0.05 * hours
        self._encoder.decay(decay_rate)

    # Analysis

    def get_match_effect(self) -> Dict[MatchLevel, float]:
        """Get recall rate by match level."""
        level_results = defaultdict(list)

        for attempt in self._attempts:
            level_results[attempt.match_level].append(
                1 if attempt.success else 0
            )

        rates = {}
        for level, results in level_results.items():
            rates[level] = sum(results) / len(results) if results else 0.0

        return rates

    def get_cue_type_effect(self) -> Dict[CueType, float]:
        """Get recall rate by cue type."""
        type_results = defaultdict(list)

        for attempt in self._attempts:
            type_results[attempt.cue.cue_type].append(
                1 if attempt.success else 0
            )

        rates = {}
        for cue_type, results in type_results.items():
            rates[cue_type] = sum(results) / len(results) if results else 0.0

        return rates

    # Metrics

    def get_metrics(self) -> ESMetrics:
        """Get encoding specificity metrics."""
        cue_rates = self.get_cue_type_effect()
        match_rates = self.get_match_effect()

        copy_cue = cue_rates.get(CueType.COPY_CUE, 0.0)
        extralist = cue_rates.get(CueType.EXTRALIST_CUE, 0.0)

        identical = match_rates.get(MatchLevel.IDENTICAL, 0.0)
        mismatch = match_rates.get(MatchLevel.MISMATCH, 0.0)

        return ESMetrics(
            copy_cue_recall=copy_cue,
            extralist_recall=extralist,
            context_effect=identical - mismatch,
            match_benefit=copy_cue - extralist
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'encoded_items': len(self._encoder._items),
            'contexts': len(self._context_mgr._contexts),
            'attempts': len(self._attempts)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_encoding_specificity_engine() -> EncodingSpecificityEngine:
    """Create encoding specificity engine."""
    return EncodingSpecificityEngine()


def demonstrate_encoding_specificity() -> Dict[str, Any]:
    """Demonstrate encoding specificity principle."""
    engine = create_encoding_specificity_engine()

    # Create encoding context
    study_context = engine.create_context(
        ContextType.ENVIRONMENTAL,
        {'room': 'library', 'noise': 'quiet', 'lighting': 'bright'}
    )

    # Encode word pairs
    pairs = [
        ("eagle", "bird"),
        ("piano", "music"),
        ("doctor", "hospital")
    ]

    items = engine.encode_list(pairs, study_context)

    results = {
        'copy_cue': [],
        'extralist_cue': [],
        'same_context': [],
        'different_context': []
    }

    # Test with different cues and contexts
    for item in items:
        # Copy cue (original)
        attempt = engine.recall_with_copy_cue(item, study_context)
        results['copy_cue'].append(attempt.success)

        # Extralist cue (related but different)
        attempt = engine.recall_with_extralist_cue(
            item, "associate", study_context
        )
        results['extralist_cue'].append(attempt.success)

        # Same context
        attempt = engine.test_context_reinstatement(item, same_context=True)
        results['same_context'].append(attempt.success)

        # Different context
        attempt = engine.test_context_reinstatement(item, same_context=False)
        results['different_context'].append(attempt.success)

    def rate(lst):
        return sum(lst) / len(lst) if lst else 0.0

    return {
        'copy_cue_rate': rate(results['copy_cue']),
        'extralist_cue_rate': rate(results['extralist_cue']),
        'same_context_rate': rate(results['same_context']),
        'different_context_rate': rate(results['different_context']),
        'interpretation': 'Copy cues and same context should yield better recall'
    }


def get_encoding_specificity_facts() -> Dict[str, str]:
    """Get facts about encoding specificity."""
    return {
        'tulving_1973': 'Encoding specificity principle introduced',
        'definition': 'Effective cue is one encoded with the target',
        'copy_cue': 'Original encoding cue is most effective',
        'recognition_failure': 'Can fail to recognize without proper cue',
        'context_dependent': 'Memory better when contexts match',
        'state_dependent': 'Emotional state can serve as context',
        'transfer_appropriate': 'Related to transfer-appropriate processing',
        'mental_reinstatement': 'Imagining context can help retrieval'
    }
