"""
BAEL Context Reinstatement Engine
===================================

Encoding-retrieval match for memory.
Tulving's encoding specificity + Godden & Baddeley's context effects.

"Ba'el returns to the scene to remember." — Ba'el
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

logger = logging.getLogger("BAEL.ContextReinstatement")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ContextType(Enum):
    """Type of context."""
    PHYSICAL_ENVIRONMENT = auto()
    INTERNAL_STATE = auto()
    COGNITIVE_STATE = auto()
    SOCIAL_CONTEXT = auto()
    TEMPORAL_CONTEXT = auto()


class ContextMatchLevel(Enum):
    """Level of context match."""
    IDENTICAL = auto()       # Same context
    SIMILAR = auto()         # Overlapping features
    DIFFERENT = auto()       # Mostly different
    OPPOSITE = auto()        # Maximally different


@dataclass
class ContextState:
    """
    A context state.
    """
    id: str
    context_type: ContextType
    features: Dict[str, float]
    description: str


@dataclass
class MemoryItem:
    """
    An item encoded with context.
    """
    id: str
    content: str
    encoding_context: ContextState
    encoding_strength: float


@dataclass
class RetrievalAttempt:
    """
    A retrieval attempt.
    """
    item_id: str
    retrieval_context: ContextState
    context_overlap: float
    retrieved: bool
    retrieval_latency_ms: float


@dataclass
class ContextReinstateMetrics:
    """
    Context reinstatement metrics.
    """
    same_context_recall: float
    different_context_recall: float
    context_effect: float
    avg_overlap_benefit: float


# ============================================================================
# ENCODING SPECIFICITY MODEL
# ============================================================================

class EncodingSpecificityModel:
    """
    Tulving's encoding specificity model.

    "Ba'el's context-memory binding." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Context weight in retrieval
        self._context_weight = 0.4  # 40% contribution to retrieval

        # Item strength weight
        self._item_weight = 0.6

        # Retrieval threshold
        self._retrieval_threshold = 0.4

        # Context feature decay
        self._context_decay_rate = 0.02

        self._lock = threading.RLock()

    def calculate_context_overlap(
        self,
        encoding_context: ContextState,
        retrieval_context: ContextState
    ) -> float:
        """Calculate overlap between encoding and retrieval contexts."""
        enc_features = encoding_context.features
        ret_features = retrieval_context.features

        common_keys = set(enc_features.keys()) & set(ret_features.keys())
        all_keys = set(enc_features.keys()) | set(ret_features.keys())

        if not all_keys:
            return 0.5

        # Calculate similarity for common features
        similarities = []
        for key in common_keys:
            sim = 1 - abs(enc_features[key] - ret_features[key])
            similarities.append(sim)

        # Missing features count as 0 similarity
        missing = len(all_keys) - len(common_keys)
        similarities.extend([0] * missing)

        if similarities:
            return sum(similarities) / len(similarities)
        return 0.5

    def calculate_retrieval_strength(
        self,
        item: MemoryItem,
        retrieval_context: ContextState
    ) -> float:
        """Calculate retrieval strength for an item."""
        # Item strength contribution
        item_strength = item.encoding_strength * self._item_weight

        # Context match contribution
        context_overlap = self.calculate_context_overlap(
            item.encoding_context, retrieval_context
        )
        context_strength = context_overlap * self._context_weight

        # Combined strength
        total_strength = item_strength + context_strength

        return min(1.0, total_strength)

    def will_retrieve(
        self,
        item: MemoryItem,
        retrieval_context: ContextState
    ) -> Tuple[bool, float, float]:
        """Determine if item will be retrieved."""
        strength = self.calculate_retrieval_strength(item, retrieval_context)
        context_overlap = self.calculate_context_overlap(
            item.encoding_context, retrieval_context
        )

        # Add noise
        strength += random.uniform(-0.1, 0.1)

        retrieved = strength >= self._retrieval_threshold

        # Latency inversely related to strength
        latency = (1 - strength) * 2000 + 200  # 200-2200ms

        return retrieved, context_overlap, latency


# ============================================================================
# CONTEXT REINSTATEMENT SYSTEM
# ============================================================================

class ContextReinstateSystem:
    """
    Context reinstatement system.

    "Ba'el's context-dependent memory." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = EncodingSpecificityModel()

        self._contexts: Dict[str, ContextState] = {}
        self._items: Dict[str, MemoryItem] = {}
        self._attempts: List[RetrievalAttempt] = []

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"item_{self._counter}"

    def create_context(
        self,
        context_type: ContextType,
        description: str
    ) -> ContextState:
        """Create a context state."""
        features = {
            f"feature_{i}": random.random()
            for i in range(5)
        }

        context = ContextState(
            id=self._generate_id(),
            context_type=context_type,
            features=features,
            description=description
        )

        self._contexts[context.id] = context

        return context

    def create_similar_context(
        self,
        base_context: ContextState,
        similarity: float = 0.7
    ) -> ContextState:
        """Create a context similar to another."""
        features = {}
        for key, value in base_context.features.items():
            if random.random() < similarity:
                # Keep similar
                features[key] = value + random.uniform(-0.1, 0.1)
            else:
                # Change
                features[key] = random.random()

        context = ContextState(
            id=self._generate_id(),
            context_type=base_context.context_type,
            features=features,
            description=f"Similar to {base_context.description}"
        )

        self._contexts[context.id] = context

        return context

    def encode_item(
        self,
        content: str,
        context: ContextState,
        encoding_strength: float = 0.6
    ) -> MemoryItem:
        """Encode an item in a context."""
        item = MemoryItem(
            id=self._generate_id(),
            content=content,
            encoding_context=context,
            encoding_strength=encoding_strength
        )

        self._items[item.id] = item

        return item

    def retrieve_item(
        self,
        item_id: str,
        context: ContextState
    ) -> RetrievalAttempt:
        """Attempt to retrieve an item in a context."""
        item = self._items.get(item_id)
        if not item:
            return None

        retrieved, overlap, latency = self._model.will_retrieve(item, context)

        attempt = RetrievalAttempt(
            item_id=item_id,
            retrieval_context=context,
            context_overlap=overlap,
            retrieved=retrieved,
            retrieval_latency_ms=latency
        )

        self._attempts.append(attempt)

        return attempt

    def retrieve_all(
        self,
        context: ContextState
    ) -> List[RetrievalAttempt]:
        """Attempt to retrieve all items in a context."""
        attempts = []
        for item_id in self._items:
            attempt = self.retrieve_item(item_id, context)
            attempts.append(attempt)
        return attempts


# ============================================================================
# CONTEXT REINSTATEMENT PARADIGM
# ============================================================================

class ContextReinstateParadigm:
    """
    Context reinstatement experimental paradigm.

    "Ba'el's context study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_godden_baddeley_paradigm(
        self,
        n_items: int = 40
    ) -> Dict[str, Any]:
        """Run underwater/land context study."""
        system = ContextReinstateSystem()

        # Create contexts
        underwater = system.create_context(
            ContextType.PHYSICAL_ENVIRONMENT,
            "underwater_diving"
        )
        land = system.create_context(
            ContextType.PHYSICAL_ENVIRONMENT,
            "on_land"
        )
        # Make them very different
        for key in land.features:
            land.features[key] = 1 - underwater.features[key]

        # Encode items in both contexts
        underwater_items = []
        land_items = []

        for i in range(n_items // 2):
            item = system.encode_item(f"underwater_word_{i}", underwater)
            underwater_items.append(item)

        for i in range(n_items // 2):
            item = system.encode_item(f"land_word_{i}", land)
            land_items.append(item)

        # Test in different conditions
        results = {
            'underwater_underwater': 0,  # Same context
            'underwater_land': 0,         # Different
            'land_land': 0,               # Same context
            'land_underwater': 0          # Different
        }

        n_per_condition = len(underwater_items)

        # UU: Learn underwater, test underwater
        for item in underwater_items:
            attempt = system.retrieve_item(item.id, underwater)
            if attempt.retrieved:
                results['underwater_underwater'] += 1

        # Reset and test UL
        system._attempts = []
        for item in underwater_items:
            attempt = system.retrieve_item(item.id, land)
            if attempt.retrieved:
                results['underwater_land'] += 1

        # LL: Learn land, test land
        for item in land_items:
            attempt = system.retrieve_item(item.id, land)
            if attempt.retrieved:
                results['land_land'] += 1

        # LU: Learn land, test underwater
        for item in land_items:
            attempt = system.retrieve_item(item.id, underwater)
            if attempt.retrieved:
                results['land_underwater'] += 1

        # Calculate rates
        same_context = (results['underwater_underwater'] + results['land_land']) / (2 * n_per_condition)
        diff_context = (results['underwater_land'] + results['land_underwater']) / (2 * n_per_condition)

        return {
            'conditions': {k: v / n_per_condition for k, v in results.items()},
            'same_context_recall': same_context,
            'different_context_recall': diff_context,
            'context_effect': same_context - diff_context
        }

    def run_mental_reinstatement(
        self,
        n_items: int = 20
    ) -> Dict[str, Any]:
        """Test mental context reinstatement."""
        system = ContextReinstateSystem()

        # Create encoding context
        original = system.create_context(
            ContextType.PHYSICAL_ENVIRONMENT,
            "original_room"
        )

        # Create different test context
        different = system.create_context(
            ContextType.PHYSICAL_ENVIRONMENT,
            "different_room"
        )
        # Make very different
        for key in different.features:
            different.features[key] = 1 - original.features[key]

        # Create mentally reinstated context (imagined original)
        mental = system.create_similar_context(original, similarity=0.6)
        mental.description = "mentally_reinstated"

        # Encode items
        items = []
        for i in range(n_items):
            item = system.encode_item(f"word_{i}", original)
            items.append(item)

        # Test conditions
        original_recall = sum(
            1 for item in items
            if system.retrieve_item(item.id, original).retrieved
        ) / n_items

        different_recall = sum(
            1 for item in items
            if system.retrieve_item(item.id, different).retrieved
        ) / n_items

        mental_recall = sum(
            1 for item in items
            if system.retrieve_item(item.id, mental).retrieved
        ) / n_items

        return {
            'original_context': original_recall,
            'different_context': different_recall,
            'mental_reinstatement': mental_recall,
            'mental_benefit': mental_recall - different_recall,
            'interpretation': 'Mental reinstatement partially restores context'
        }

    def run_state_dependent_study(
        self,
        n_items: int = 20
    ) -> Dict[str, Any]:
        """Test internal state-dependent memory."""
        system = ContextReinstateSystem()

        # Create mood states
        happy = system.create_context(
            ContextType.INTERNAL_STATE,
            "happy_mood"
        )
        sad = system.create_context(
            ContextType.INTERNAL_STATE,
            "sad_mood"
        )
        # Make opposite
        for key in sad.features:
            sad.features[key] = 1 - happy.features[key]

        # Encode in happy mood
        items = []
        for i in range(n_items):
            item = system.encode_item(f"word_{i}", happy)
            items.append(item)

        # Test in same vs different mood
        same_mood = sum(
            1 for item in items
            if system.retrieve_item(item.id, happy).retrieved
        ) / n_items

        diff_mood = sum(
            1 for item in items
            if system.retrieve_item(item.id, sad).retrieved
        ) / n_items

        return {
            'same_mood_recall': same_mood,
            'different_mood_recall': diff_mood,
            'state_dependence': same_mood - diff_mood
        }

    def run_environmental_detail_study(
        self
    ) -> Dict[str, Any]:
        """Test importance of specific vs global context."""
        system = ContextReinstateSystem()

        # Full context
        full_context = system.create_context(
            ContextType.PHYSICAL_ENVIRONMENT,
            "full_room"
        )

        # Encode items
        items = []
        for i in range(20):
            item = system.encode_item(f"word_{i}", full_context)
            items.append(item)

        # Different context variations
        partial = system.create_similar_context(full_context, 0.5)
        minimal = system.create_similar_context(full_context, 0.2)
        none = system.create_context(ContextType.PHYSICAL_ENVIRONMENT, "new")

        results = {}
        for label, ctx in [('full', full_context), ('partial', partial),
                            ('minimal', minimal), ('none', none)]:
            recall = sum(
                1 for item in items
                if system.retrieve_item(item.id, ctx).retrieved
            ) / len(items)
            results[label] = recall

        return {
            'overlap_levels': results,
            'interpretation': 'More context overlap = better retrieval'
        }


# ============================================================================
# CONTEXT REINSTATEMENT ENGINE
# ============================================================================

class ContextReinstateEngine:
    """
    Complete context reinstatement engine.

    "Ba'el's encoding-retrieval match engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = ContextReinstateParadigm()
        self._system = ContextReinstateSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Context/item management

    def create_context(
        self,
        description: str,
        context_type: ContextType = ContextType.PHYSICAL_ENVIRONMENT
    ) -> ContextState:
        """Create a context."""
        return self._system.create_context(context_type, description)

    def encode(
        self,
        content: str,
        context: ContextState
    ) -> MemoryItem:
        """Encode an item."""
        return self._system.encode_item(content, context)

    def retrieve(
        self,
        item_id: str,
        context: ContextState
    ) -> RetrievalAttempt:
        """Retrieve an item."""
        return self._system.retrieve_item(item_id, context)

    def retrieve_all(
        self,
        context: ContextState
    ) -> List[RetrievalAttempt]:
        """Retrieve all items."""
        return self._system.retrieve_all(context)

    # Experiments

    def run_godden_baddeley(
        self
    ) -> Dict[str, Any]:
        """Run underwater study."""
        result = self._paradigm.run_godden_baddeley_paradigm()
        self._experiment_results.append(result)
        return result

    def test_mental_reinstatement(
        self
    ) -> Dict[str, Any]:
        """Test mental reinstatement."""
        return self._paradigm.run_mental_reinstatement()

    def study_state_dependence(
        self
    ) -> Dict[str, Any]:
        """Study state dependence."""
        return self._paradigm.run_state_dependent_study()

    def study_context_detail(
        self
    ) -> Dict[str, Any]:
        """Study context detail importance."""
        return self._paradigm.run_environmental_detail_study()

    def simulate_cognitive_interview(
        self
    ) -> Dict[str, Any]:
        """Simulate cognitive interview technique."""
        system = ContextReinstateSystem()

        # Crime scene context
        crime_scene = system.create_context(
            ContextType.PHYSICAL_ENVIRONMENT,
            "crime_scene"
        )

        # Encode witnessed details
        details = []
        for i in range(15):
            item = system.encode_item(
                f"detail_{i}",
                crime_scene,
                encoding_strength=random.uniform(0.4, 0.7)
            )
            details.append(item)

        # Standard interview (different context)
        interview_room = system.create_context(
            ContextType.PHYSICAL_ENVIRONMENT,
            "interview_room"
        )

        standard_recall = sum(
            1 for d in details
            if system.retrieve_item(d.id, interview_room).retrieved
        ) / len(details)

        # Cognitive interview (mentally reinstate)
        mental_crime_scene = system.create_similar_context(crime_scene, 0.65)

        cognitive_recall = sum(
            1 for d in details
            if system.retrieve_item(d.id, mental_crime_scene).retrieved
        ) / len(details)

        return {
            'standard_interview': standard_recall,
            'cognitive_interview': cognitive_recall,
            'improvement': cognitive_recall - standard_recall,
            'technique': 'Mentally reinstate original context'
        }

    # Analysis

    def get_metrics(self) -> ContextReinstateMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_godden_baddeley()

        last = self._experiment_results[-1]

        return ContextReinstateMetrics(
            same_context_recall=last['same_context_recall'],
            different_context_recall=last['different_context_recall'],
            context_effect=last['context_effect'],
            avg_overlap_benefit=last['context_effect'] / 2
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'contexts': len(self._system._contexts),
            'items': len(self._system._items),
            'attempts': len(self._system._attempts)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_context_reinstatement_engine() -> ContextReinstateEngine:
    """Create context reinstatement engine."""
    return ContextReinstateEngine()


def demonstrate_context_reinstatement() -> Dict[str, Any]:
    """Demonstrate context reinstatement."""
    engine = create_context_reinstatement_engine()

    # Godden & Baddeley
    underwater = engine.run_godden_baddeley()

    # Mental reinstatement
    mental = engine.test_mental_reinstatement()

    # State dependence
    state = engine.study_state_dependence()

    # Context detail
    detail = engine.study_context_detail()

    # Cognitive interview
    interview = engine.simulate_cognitive_interview()

    return {
        'underwater_study': {
            'same_context': f"{underwater['same_context_recall']:.0%}",
            'different_context': f"{underwater['different_context_recall']:.0%}",
            'effect': f"{underwater['context_effect']:.0%}"
        },
        'mental_reinstatement': {
            'different_context': f"{mental['different_context']:.0%}",
            'mental_reinstate': f"{mental['mental_reinstatement']:.0%}",
            'benefit': f"{mental['mental_benefit']:.0%}"
        },
        'state_dependence': {
            'same_mood': f"{state['same_mood_recall']:.0%}",
            'different_mood': f"{state['different_mood_recall']:.0%}"
        },
        'cognitive_interview': {
            'standard': f"{interview['standard_interview']:.0%}",
            'cognitive': f"{interview['cognitive_interview']:.0%}",
            'improvement': f"{interview['improvement']:.0%}"
        },
        'interpretation': (
            f"Same context: {underwater['same_context_recall']:.0%} vs "
            f"different: {underwater['different_context_recall']:.0%}. "
            f"Mental reinstatement helps."
        )
    }


def get_context_reinstatement_facts() -> Dict[str, str]:
    """Get facts about context reinstatement."""
    return {
        'godden_baddeley_1975': 'Underwater study showing 50% better recall in same context',
        'encoding_specificity': 'Tulving: retrieval cues effective if encoded with item',
        'mental_reinstatement': 'Imagining original context helps retrieval',
        'cognitive_interview': 'Police technique using context reinstatement',
        'state_dependence': 'Internal states also provide retrieval context',
        'outshining': 'Strong cues can outshine context effects',
        'applications': 'Eyewitness testimony, studying, therapy'
    }
