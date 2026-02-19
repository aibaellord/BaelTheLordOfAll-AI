"""
BAEL Interference Engine
=========================

Memory interference and forgetting.
Proactive and retroactive interference.

"Ba'el understands memory conflicts." — Ba'el
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

logger = logging.getLogger("BAEL.Interference")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class InterferenceType(Enum):
    """Types of memory interference."""
    PROACTIVE = auto()     # Old interferes with new
    RETROACTIVE = auto()   # New interferes with old
    OUTPUT = auto()        # Recall interferes with other recall


class SimilarityType(Enum):
    """Types of similarity."""
    IDENTICAL = auto()     # Same item
    HIGH = auto()          # Very similar
    MODERATE = auto()      # Somewhat similar
    LOW = auto()           # Different


class ListPosition(Enum):
    """Position in list."""
    PRIMACY = auto()       # Beginning
    MIDDLE = auto()        # Middle
    RECENCY = auto()       # End


@dataclass
class MemoryTrace:
    """
    A memory trace.
    """
    id: str
    content: Any
    context: str          # Learning context
    list_id: str          # Which list it belongs to
    position: int         # Position in list
    strength: float = 1.0
    encoded_time: float = 0.0
    last_accessed: float = 0.0
    access_count: int = 0


@dataclass
class MemoryList:
    """
    A list of items learned together.
    """
    id: str
    name: str
    items: List[MemoryTrace]
    context: str
    learned_time: float


@dataclass
class InterferenceEvent:
    """
    An interference event.
    """
    type: InterferenceType
    interfering_item: str
    target_item: str
    strength_loss: float
    similarity: SimilarityType


@dataclass
class RetrievalResult:
    """
    Result of memory retrieval.
    """
    target_id: str
    retrieved: bool
    intrusions: List[str]   # Wrong items retrieved
    latency: float
    interference_events: List[InterferenceEvent]


@dataclass
class InterferenceMetrics:
    """
    Interference metrics.
    """
    proactive_rate: float
    retroactive_rate: float
    intrusion_rate: float
    release_from_pi: float  # Release from proactive interference


# ============================================================================
# SIMILARITY CALCULATOR
# ============================================================================

class SimilarityCalculator:
    """
    Calculate similarity between items.

    "Ba'el measures likeness." — Ba'el
    """

    def __init__(self):
        """Initialize calculator."""
        self._lock = threading.RLock()

    def calculate(
        self,
        item1: Any,
        item2: Any
    ) -> float:
        """Calculate similarity score."""
        if item1 == item2:
            return 1.0

        str1 = str(item1).lower()
        str2 = str(item2).lower()

        # Character overlap
        chars1 = set(str1)
        chars2 = set(str2)
        overlap = len(chars1 & chars2) / max(len(chars1 | chars2), 1)

        # Length similarity
        len_ratio = min(len(str1), len(str2)) / max(len(str1), len(str2), 1)

        # First letter match
        first_match = 0.2 if str1 and str2 and str1[0] == str2[0] else 0.0

        return 0.4 * overlap + 0.3 * len_ratio + 0.3 * first_match

    def categorize(
        self,
        similarity: float
    ) -> SimilarityType:
        """Categorize similarity level."""
        if similarity >= 0.95:
            return SimilarityType.IDENTICAL
        elif similarity >= 0.7:
            return SimilarityType.HIGH
        elif similarity >= 0.4:
            return SimilarityType.MODERATE
        else:
            return SimilarityType.LOW

    def context_similarity(
        self,
        context1: str,
        context2: str
    ) -> float:
        """Calculate context similarity."""
        if context1 == context2:
            return 1.0

        words1 = set(context1.lower().split())
        words2 = set(context2.lower().split())

        if not words1 or not words2:
            return 0.0

        return len(words1 & words2) / len(words1 | words2)


# ============================================================================
# INTERFERENCE MODELER
# ============================================================================

class InterferenceModeler:
    """
    Model interference effects.

    "Ba'el predicts memory conflicts." — Ba'el
    """

    def __init__(
        self,
        similarity_calc: SimilarityCalculator
    ):
        """Initialize modeler."""
        self._similarity = similarity_calc
        self._lock = threading.RLock()

    def calculate_proactive(
        self,
        old_trace: MemoryTrace,
        new_trace: MemoryTrace
    ) -> float:
        """Calculate proactive interference."""
        # Old memory interfering with new

        # Content similarity
        content_sim = self._similarity.calculate(old_trace.content, new_trace.content)

        # Context similarity (same context = more interference)
        context_sim = self._similarity.context_similarity(
            old_trace.context, new_trace.context
        )

        # Old trace strength
        old_strength = old_trace.strength

        # PI = similarity * old_strength * context_overlap
        pi = content_sim * old_strength * (0.5 + 0.5 * context_sim)

        return min(1.0, pi)

    def calculate_retroactive(
        self,
        old_trace: MemoryTrace,
        new_trace: MemoryTrace
    ) -> float:
        """Calculate retroactive interference."""
        # New memory interfering with old

        # Content similarity
        content_sim = self._similarity.calculate(old_trace.content, new_trace.content)

        # Context similarity
        context_sim = self._similarity.context_similarity(
            old_trace.context, new_trace.context
        )

        # New trace strength
        new_strength = new_trace.strength

        # Time since old encoded (more time = more vulnerable)
        time_factor = 1.0 - old_trace.strength * 0.5

        # RI = similarity * new_strength * time_factor
        ri = content_sim * new_strength * time_factor * (0.5 + 0.5 * context_sim)

        return min(1.0, ri)

    def calculate_output(
        self,
        recalled_trace: MemoryTrace,
        target_trace: MemoryTrace
    ) -> float:
        """Calculate output interference."""
        # Recalling one item interferes with recalling another

        content_sim = self._similarity.calculate(recalled_trace.content, target_trace.content)

        # Output interference depends on:
        # - Similarity (higher = more interference)
        # - How recently recalled (recent = more interference)

        recency = 0.5  # Assume just recalled

        return content_sim * recency * 0.5


# ============================================================================
# MEMORY SYSTEM
# ============================================================================

class MemorySystem:
    """
    Memory system with interference.

    "Ba'el stores with conflict." — Ba'el
    """

    def __init__(self):
        """Initialize memory system."""
        self._traces: Dict[str, MemoryTrace] = {}
        self._lists: Dict[str, MemoryList] = {}

        self._trace_counter = 0
        self._list_counter = 0

        self._decay_rate = 0.01

        self._lock = threading.RLock()

    def _generate_trace_id(self) -> str:
        self._trace_counter += 1
        return f"trace_{self._trace_counter}"

    def _generate_list_id(self) -> str:
        self._list_counter += 1
        return f"list_{self._list_counter}"

    def encode(
        self,
        content: Any,
        context: str = "default",
        list_id: str = None
    ) -> MemoryTrace:
        """Encode a new memory trace."""
        if list_id and list_id in self._lists:
            position = len(self._lists[list_id].items)
        else:
            position = 0

        trace = MemoryTrace(
            id=self._generate_trace_id(),
            content=content,
            context=context,
            list_id=list_id or "none",
            position=position,
            strength=1.0,
            encoded_time=time.time(),
            last_accessed=time.time()
        )

        self._traces[trace.id] = trace

        if list_id and list_id in self._lists:
            self._lists[list_id].items.append(trace)

        return trace

    def create_list(
        self,
        name: str,
        context: str = "default"
    ) -> MemoryList:
        """Create a new memory list."""
        memory_list = MemoryList(
            id=self._generate_list_id(),
            name=name,
            items=[],
            context=context,
            learned_time=time.time()
        )

        self._lists[memory_list.id] = memory_list
        return memory_list

    def get_trace(
        self,
        trace_id: str
    ) -> Optional[MemoryTrace]:
        """Get a memory trace."""
        return self._traces.get(trace_id)

    def apply_decay(self) -> None:
        """Apply decay to all traces."""
        for trace in self._traces.values():
            trace.strength = max(0.01, trace.strength - self._decay_rate)

    def weaken_trace(
        self,
        trace_id: str,
        amount: float
    ) -> None:
        """Weaken a trace."""
        if trace_id in self._traces:
            trace = self._traces[trace_id]
            trace.strength = max(0.01, trace.strength - amount)


# ============================================================================
# INTERFERENCE ENGINE
# ============================================================================

class InterferenceEngine:
    """
    Complete interference engine.

    "Ba'el's memory interference system." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._similarity = SimilarityCalculator()
        self._modeler = InterferenceModeler(self._similarity)
        self._memory = MemorySystem()

        self._interference_events: List[InterferenceEvent] = []
        self._retrieval_results: List[RetrievalResult] = []

        self._lock = threading.RLock()

    # Encoding

    def learn_list(
        self,
        name: str,
        items: List[Any],
        context: str = "default"
    ) -> MemoryList:
        """Learn a list of items."""
        memory_list = self._memory.create_list(name, context)

        for item in items:
            trace = self._memory.encode(item, context, memory_list.id)

            # Apply proactive interference from existing traces
            for existing in self._memory._traces.values():
                if existing.id != trace.id:
                    pi = self._modeler.calculate_proactive(existing, trace)
                    if pi > 0.1:
                        trace.strength -= pi * 0.2

                        self._interference_events.append(InterferenceEvent(
                            type=InterferenceType.PROACTIVE,
                            interfering_item=str(existing.content),
                            target_item=str(item),
                            strength_loss=pi * 0.2,
                            similarity=self._similarity.categorize(
                                self._similarity.calculate(existing.content, item)
                            )
                        ))

        # Apply retroactive interference to old traces
        for new_trace in memory_list.items:
            for old_trace in self._memory._traces.values():
                if old_trace.list_id != memory_list.id:
                    ri = self._modeler.calculate_retroactive(old_trace, new_trace)
                    if ri > 0.1:
                        self._memory.weaken_trace(old_trace.id, ri * 0.3)

                        self._interference_events.append(InterferenceEvent(
                            type=InterferenceType.RETROACTIVE,
                            interfering_item=str(new_trace.content),
                            target_item=str(old_trace.content),
                            strength_loss=ri * 0.3,
                            similarity=self._similarity.categorize(
                                self._similarity.calculate(new_trace.content, old_trace.content)
                            )
                        ))

        return memory_list

    # Retrieval

    def recall_list(
        self,
        list_id: str
    ) -> RetrievalResult:
        """Recall items from a list."""
        if list_id not in self._memory._lists:
            return RetrievalResult(
                target_id=list_id,
                retrieved=False,
                intrusions=[],
                latency=0.0,
                interference_events=[]
            )

        memory_list = self._memory._lists[list_id]
        recalled_items = []
        intrusions = []
        events = []

        # Try to recall each item
        for trace in memory_list.items:
            # Recall probability based on strength
            if random.random() < trace.strength:
                recalled_items.append(trace.content)
                trace.access_count += 1
                trace.last_accessed = time.time()

                # Output interference affects subsequent items
                for other_trace in memory_list.items:
                    if other_trace.id != trace.id:
                        oi = self._modeler.calculate_output(trace, other_trace)
                        if oi > 0.05:
                            other_trace.strength -= oi * 0.1
            else:
                # Might get an intrusion instead
                if random.random() < 0.3:
                    # Find similar items from other lists
                    for other_id, other_list in self._memory._lists.items():
                        if other_id != list_id:
                            for other_trace in other_list.items:
                                sim = self._similarity.calculate(
                                    trace.content, other_trace.content
                                )
                                if sim > 0.5 and random.random() < sim * 0.5:
                                    intrusions.append(str(other_trace.content))
                                    break

        result = RetrievalResult(
            target_id=list_id,
            retrieved=len(recalled_items) > 0,
            intrusions=intrusions[:3],
            latency=random.uniform(0.5, 2.0),
            interference_events=events
        )

        self._retrieval_results.append(result)
        return result

    def recall_item(
        self,
        trace_id: str
    ) -> Tuple[bool, Optional[Any]]:
        """Recall a specific item."""
        trace = self._memory.get_trace(trace_id)
        if not trace:
            return False, None

        if random.random() < trace.strength:
            trace.access_count += 1
            trace.last_accessed = time.time()
            return True, trace.content

        return False, None

    # Interference manipulation

    def release_from_pi(
        self,
        context: str
    ) -> None:
        """Release from proactive interference via context change."""
        # Changing context reduces PI
        for trace in self._memory._traces.values():
            if trace.context != context:
                trace.strength = min(1.0, trace.strength + 0.2)

    def simulate_interpolated_activity(
        self,
        similar: bool = True
    ) -> None:
        """Simulate activity between learning and recall."""
        # Similar activity = more RI
        # Dissimilar activity = less RI

        decay_amount = 0.15 if similar else 0.05

        for trace in self._memory._traces.values():
            trace.strength = max(0.01, trace.strength - decay_amount)

    # Analysis

    def get_serial_position_effect(
        self,
        list_id: str
    ) -> Dict[str, float]:
        """Analyze serial position effect."""
        if list_id not in self._memory._lists:
            return {}

        memory_list = self._memory._lists[list_id]

        primacy_items = memory_list.items[:2]
        recency_items = memory_list.items[-2:]
        middle_items = memory_list.items[2:-2] if len(memory_list.items) > 4 else []

        def avg_strength(items):
            if not items:
                return 0.0
            return sum(t.strength for t in items) / len(items)

        return {
            'primacy': avg_strength(primacy_items),
            'middle': avg_strength(middle_items),
            'recency': avg_strength(recency_items)
        }

    # Metrics

    def get_metrics(self) -> InterferenceMetrics:
        """Get interference metrics."""
        if not self._interference_events:
            return InterferenceMetrics(
                proactive_rate=0.0,
                retroactive_rate=0.0,
                intrusion_rate=0.0,
                release_from_pi=0.0
            )

        pi_count = sum(1 for e in self._interference_events if e.type == InterferenceType.PROACTIVE)
        ri_count = sum(1 for e in self._interference_events if e.type == InterferenceType.RETROACTIVE)
        total = len(self._interference_events)

        intrusion_count = sum(len(r.intrusions) for r in self._retrieval_results)
        recall_count = len(self._retrieval_results)

        return InterferenceMetrics(
            proactive_rate=pi_count / total if total > 0 else 0.0,
            retroactive_rate=ri_count / total if total > 0 else 0.0,
            intrusion_rate=intrusion_count / recall_count if recall_count > 0 else 0.0,
            release_from_pi=0.0  # Would need experimental design
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'traces': len(self._memory._traces),
            'lists': len(self._memory._lists),
            'interference_events': len(self._interference_events)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_interference_engine() -> InterferenceEngine:
    """Create interference engine."""
    return InterferenceEngine()


def demonstrate_ab_ac_paradigm() -> Dict[str, Any]:
    """Demonstrate A-B, A-C retroactive interference paradigm."""
    engine = create_interference_engine()

    # Learn A-B pairs
    list1 = engine.learn_list(
        "List 1 (A-B)",
        ["dog-bone", "cat-fish", "bird-seed"],
        context="learning"
    )

    # Learn A-C pairs (same cues, different responses)
    list2 = engine.learn_list(
        "List 2 (A-C)",
        ["dog-ball", "cat-milk", "bird-worm"],
        context="learning"
    )

    # Recall original A-B list
    result = engine.recall_list(list1.id)

    # Get strength of original items
    original_strengths = [t.strength for t in list1.items]

    return {
        'paradigm': 'A-B, A-C',
        'original_list': 'dog-bone, cat-fish, bird-seed',
        'interfering_list': 'dog-ball, cat-milk, bird-worm',
        'original_strengths_after': original_strengths,
        'intrusions': result.intrusions,
        'interference_type': 'Retroactive (new interferes with old)'
    }


def get_interference_facts() -> Dict[str, str]:
    """Get facts about interference."""
    return {
        'proactive': 'Old learning interferes with new (PI)',
        'retroactive': 'New learning interferes with old (RI)',
        'similarity': 'More similar materials = more interference',
        'release_from_pi': 'Changing category releases from PI',
        'mcgeoch_1932': 'Retroactive interference paradigm established',
        'underwood_1957': 'Proactive interference in paired-associate learning',
        'cue_overload': 'Too many associations to cue causes interference',
        'output': 'Recalling one item inhibits similar items'
    }
