"""
BAEL Cognitive Load Engine
===========================

Cognitive Load Theory (Sweller).
Intrinsic, extraneous, and germane load.

"Ba'el manages mental effort." — Ba'el
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
from collections import deque
import copy

logger = logging.getLogger("BAEL.CognitiveLoad")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class LoadType(Enum):
    """Types of cognitive load."""
    INTRINSIC = auto()    # Complexity of material
    EXTRANEOUS = auto()   # Poor presentation
    GERMANE = auto()      # Schema construction


class ChannelType(Enum):
    """Processing channels."""
    VISUAL = auto()
    AUDITORY = auto()
    VERBAL = auto()
    SPATIAL = auto()


class TaskComplexity(Enum):
    """Task complexity levels."""
    TRIVIAL = auto()
    SIMPLE = auto()
    MODERATE = auto()
    COMPLEX = auto()
    OVERWHELMING = auto()


@dataclass
class CognitiveElement:
    """
    An element to be processed.
    """
    id: str
    content: Any
    complexity: float = 0.5    # 0-1
    channel: ChannelType = ChannelType.VISUAL
    interactivity: int = 0     # Elements it interacts with
    novelty: float = 0.5       # 0-1


@dataclass
class LoadState:
    """
    Current cognitive load state.
    """
    intrinsic: float = 0.0
    extraneous: float = 0.0
    germane: float = 0.0

    @property
    def total(self) -> float:
        return self.intrinsic + self.extraneous + self.germane

    @property
    def effective(self) -> float:
        """Load contributing to learning."""
        return self.intrinsic + self.germane

    @property
    def wasted(self) -> float:
        """Wasted load."""
        return self.extraneous

    def is_overloaded(self, capacity: float = 1.0) -> bool:
        return self.total > capacity


@dataclass
class WorkingMemoryState:
    """
    Working memory state.
    """
    capacity: int = 7
    current_items: List[Any] = field(default_factory=list)
    channel_loads: Dict[ChannelType, float] = field(default_factory=dict)

    @property
    def used_slots(self) -> int:
        return len(self.current_items)

    @property
    def available_slots(self) -> int:
        return max(0, self.capacity - self.used_slots)

    @property
    def utilization(self) -> float:
        return self.used_slots / self.capacity if self.capacity > 0 else 0


# ============================================================================
# LOAD CALCULATOR
# ============================================================================

class LoadCalculator:
    """
    Calculate cognitive load.

    "Ba'el calculates mental load." — Ba'el
    """

    def __init__(self):
        """Initialize calculator."""
        self._lock = threading.RLock()

    def intrinsic_load(
        self,
        elements: List[CognitiveElement],
        expertise: float = 0.5
    ) -> float:
        """Calculate intrinsic load."""
        with self._lock:
            if not elements:
                return 0.0

            # Base complexity
            complexity_sum = sum(e.complexity for e in elements)

            # Element interactivity (exponential with interactions)
            interactivity = sum(e.interactivity for e in elements)
            interaction_factor = 1.0 + 0.1 * interactivity

            # Expertise reduces load
            expertise_factor = 1.0 - (expertise * 0.5)

            # Calculate load
            load = complexity_sum * interaction_factor * expertise_factor

            # Normalize to 0-1
            return min(1.0, load / (len(elements) * 2))

    def extraneous_load(
        self,
        presentation_quality: float,
        split_attention: bool = False,
        redundancy: bool = False,
        modality_mismatch: bool = False
    ) -> float:
        """Calculate extraneous load."""
        with self._lock:
            # Base from presentation quality (inverted)
            load = 1.0 - presentation_quality

            # Split attention effect
            if split_attention:
                load += 0.2

            # Redundancy effect
            if redundancy:
                load += 0.15

            # Modality mismatch
            if modality_mismatch:
                load += 0.1

            return min(1.0, load)

    def germane_load(
        self,
        schema_relevance: float,
        elaboration_depth: float,
        practice_variability: float
    ) -> float:
        """Calculate germane load."""
        with self._lock:
            # Germane load from meaningful processing
            load = (schema_relevance * 0.4 +
                   elaboration_depth * 0.3 +
                   practice_variability * 0.3)

            return min(1.0, load)

    def total_load(self, state: LoadState) -> float:
        """Calculate total load."""
        return state.total

    def element_interactivity(
        self,
        elements: List[CognitiveElement]
    ) -> float:
        """Calculate overall element interactivity."""
        if not elements:
            return 0.0

        total_interactions = sum(e.interactivity for e in elements)
        max_possible = len(elements) * (len(elements) - 1)

        if max_possible == 0:
            return 0.0

        return total_interactions / max_possible


# ============================================================================
# WORKING MEMORY
# ============================================================================

class CognitiveWorkingMemory:
    """
    Cognitive working memory with limits.

    "Ba'el's limited workspace." — Ba'el
    """

    def __init__(
        self,
        capacity: int = 7,
        decay_rate: float = 0.1
    ):
        """Initialize working memory."""
        self._capacity = capacity
        self._decay_rate = decay_rate
        self._items: List[Tuple[CognitiveElement, float]] = []  # (element, activation)
        self._channel_loads: Dict[ChannelType, float] = {c: 0.0 for c in ChannelType}
        self._lock = threading.RLock()

    def add(self, element: CognitiveElement) -> bool:
        """Add element to working memory."""
        with self._lock:
            # Check capacity
            if len(self._items) >= self._capacity:
                # Try to evict lowest activation
                if not self._evict_weakest():
                    return False

            # Check channel load
            current_channel = self._channel_loads.get(element.channel, 0.0)
            if current_channel + element.complexity > 1.0:
                return False

            self._items.append((element, 1.0))
            self._channel_loads[element.channel] += element.complexity

            return True

    def _evict_weakest(self) -> bool:
        """Evict lowest activation item."""
        if not self._items:
            return False

        min_idx = min(range(len(self._items)), key=lambda i: self._items[i][1])
        element, _ = self._items.pop(min_idx)
        self._channel_loads[element.channel] -= element.complexity

        return True

    def rehearse(self, element_id: str) -> bool:
        """Rehearse item to maintain activation."""
        with self._lock:
            for i, (element, activation) in enumerate(self._items):
                if element.id == element_id:
                    self._items[i] = (element, min(1.0, activation + 0.2))
                    return True
            return False

    def decay(self) -> None:
        """Apply decay to all items."""
        with self._lock:
            new_items = []

            for element, activation in self._items:
                new_activation = activation * (1 - self._decay_rate)

                if new_activation > 0.1:
                    new_items.append((element, new_activation))
                else:
                    # Item forgotten
                    self._channel_loads[element.channel] -= element.complexity

            self._items = new_items

    def get_state(self) -> WorkingMemoryState:
        """Get working memory state."""
        return WorkingMemoryState(
            capacity=self._capacity,
            current_items=[e for e, _ in self._items],
            channel_loads=self._channel_loads.copy()
        )

    @property
    def utilization(self) -> float:
        return len(self._items) / self._capacity if self._capacity > 0 else 0

    @property
    def items(self) -> List[CognitiveElement]:
        return [e for e, _ in self._items]


# ============================================================================
# LOAD MANAGER
# ============================================================================

class LoadManager:
    """
    Manage cognitive load.

    "Ba'el optimizes mental load." — Ba'el
    """

    def __init__(
        self,
        wm_capacity: int = 7,
        max_total_load: float = 1.0
    ):
        """Initialize load manager."""
        self._calculator = LoadCalculator()
        self._working_memory = CognitiveWorkingMemory(wm_capacity)
        self._max_load = max_total_load
        self._current_state = LoadState()
        self._expertise_level = 0.5
        self._lock = threading.RLock()

    def set_expertise(self, level: float) -> None:
        """Set expertise level (0-1)."""
        with self._lock:
            self._expertise_level = max(0.0, min(1.0, level))

    def process_elements(
        self,
        elements: List[CognitiveElement],
        presentation_quality: float = 0.8,
        schema_relevance: float = 0.5
    ) -> Tuple[LoadState, List[CognitiveElement]]:
        """Process elements and return load state."""
        with self._lock:
            # Calculate loads
            intrinsic = self._calculator.intrinsic_load(
                elements, self._expertise_level
            )

            extraneous = self._calculator.extraneous_load(
                presentation_quality,
                split_attention=len(set(e.channel for e in elements)) > 1
            )

            germane = self._calculator.germane_load(
                schema_relevance,
                elaboration_depth=0.5,
                practice_variability=0.3
            )

            state = LoadState(
                intrinsic=intrinsic,
                extraneous=extraneous,
                germane=germane
            )

            self._current_state = state

            # Try to add elements to working memory
            processed = []
            for element in elements:
                if not state.is_overloaded(self._max_load):
                    if self._working_memory.add(element):
                        processed.append(element)

            return state, processed

    def recommend_chunking(
        self,
        elements: List[CognitiveElement],
        target_load: float = 0.6
    ) -> List[List[CognitiveElement]]:
        """Recommend element chunking."""
        with self._lock:
            if not elements:
                return []

            chunks = []
            current_chunk = []
            current_load = 0.0

            for element in elements:
                element_load = element.complexity * (1 + 0.1 * element.interactivity)

                if current_load + element_load <= target_load:
                    current_chunk.append(element)
                    current_load += element_load
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = [element]
                    current_load = element_load

            if current_chunk:
                chunks.append(current_chunk)

            return chunks

    def optimize_presentation(
        self,
        elements: List[CognitiveElement]
    ) -> Dict[str, Any]:
        """Recommend optimizations."""
        with self._lock:
            recommendations = []

            # Check channel distribution
            channels = [e.channel for e in elements]
            if len(set(channels)) > 2:
                recommendations.append("reduce_modalities")

            # Check interactivity
            high_interactivity = [e for e in elements if e.interactivity > 3]
            if high_interactivity:
                recommendations.append("pre_train_schemas")

            # Check novelty
            high_novelty = [e for e in elements if e.novelty > 0.7]
            if high_novelty:
                recommendations.append("provide_worked_examples")

            # Check total complexity
            total_complexity = sum(e.complexity for e in elements)
            if total_complexity > 3.0:
                recommendations.append("use_segmenting")

            return {
                'recommendations': recommendations,
                'optimal_chunk_size': min(4, len(elements)),
                'estimated_load': self._calculator.intrinsic_load(
                    elements, self._expertise_level
                )
            }

    @property
    def current_load(self) -> LoadState:
        return self._current_state

    @property
    def working_memory(self) -> CognitiveWorkingMemory:
        return self._working_memory

    @property
    def is_overloaded(self) -> bool:
        return self._current_state.is_overloaded(self._max_load)


# ============================================================================
# COGNITIVE LOAD ENGINE
# ============================================================================

class CognitiveLoadEngine:
    """
    Complete cognitive load management.

    "Ba'el masters mental effort." — Ba'el
    """

    def __init__(
        self,
        wm_capacity: int = 7,
        max_load: float = 1.0
    ):
        """Initialize engine."""
        self._manager = LoadManager(wm_capacity, max_load)
        self._element_counter = 0
        self._history: List[LoadState] = []
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._element_counter += 1
        return f"element_{self._element_counter}"

    def create_element(
        self,
        content: Any,
        complexity: float = 0.5,
        channel: ChannelType = ChannelType.VISUAL,
        interactivity: int = 0
    ) -> CognitiveElement:
        """Create cognitive element."""
        return CognitiveElement(
            id=self._generate_id(),
            content=content,
            complexity=complexity,
            channel=channel,
            interactivity=interactivity
        )

    def process(
        self,
        content: Any,
        complexity: float = 0.5,
        channel: ChannelType = ChannelType.VISUAL
    ) -> LoadState:
        """Process content and return load."""
        element = self.create_element(content, complexity, channel)
        state, _ = self._manager.process_elements([element])
        self._history.append(state)
        return state

    def process_batch(
        self,
        elements: List[CognitiveElement],
        presentation_quality: float = 0.8
    ) -> Tuple[LoadState, List[CognitiveElement]]:
        """Process batch of elements."""
        state, processed = self._manager.process_elements(
            elements, presentation_quality
        )
        self._history.append(state)
        return state, processed

    def set_expertise(self, level: float) -> None:
        """Set expertise level."""
        self._manager.set_expertise(level)

    def chunk(
        self,
        elements: List[CognitiveElement],
        target_load: float = 0.6
    ) -> List[List[CognitiveElement]]:
        """Chunk elements for optimal processing."""
        return self._manager.recommend_chunking(elements, target_load)

    def optimize(
        self,
        elements: List[CognitiveElement]
    ) -> Dict[str, Any]:
        """Get optimization recommendations."""
        return self._manager.optimize_presentation(elements)

    def decay_working_memory(self) -> None:
        """Apply decay."""
        self._manager.working_memory.decay()

    @property
    def current_load(self) -> LoadState:
        return self._manager.current_load

    @property
    def is_overloaded(self) -> bool:
        return self._manager.is_overloaded

    @property
    def working_memory_utilization(self) -> float:
        return self._manager.working_memory.utilization

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'current_load': {
                'intrinsic': self._manager.current_load.intrinsic,
                'extraneous': self._manager.current_load.extraneous,
                'germane': self._manager.current_load.germane,
                'total': self._manager.current_load.total
            },
            'wm_utilization': self._manager.working_memory.utilization,
            'is_overloaded': self._manager.is_overloaded,
            'history_size': len(self._history)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_cognitive_load_engine(
    wm_capacity: int = 7,
    max_load: float = 1.0
) -> CognitiveLoadEngine:
    """Create cognitive load engine."""
    return CognitiveLoadEngine(wm_capacity, max_load)


def estimate_load(
    complexity: float,
    element_count: int,
    expertise: float = 0.5
) -> float:
    """Quick load estimation."""
    base_load = complexity * element_count
    expertise_factor = 1.0 - (expertise * 0.5)
    return min(1.0, base_load * expertise_factor / 5)
