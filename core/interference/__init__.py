"""
BAEL Interference Engine
==========================

Proactive and retroactive interference.
Memory competition and forgetting.

"Ba'el manages memory conflicts." — Ba'el
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
    """Types of interference."""
    PROACTIVE = auto()        # Old interferes with new
    RETROACTIVE = auto()       # New interferes with old
    OUTPUT = auto()            # Retrieved items block others


class SimilarityLevel(Enum):
    """Similarity between items."""
    IDENTICAL = auto()         # Same response expected
    HIGH = auto()              # Very similar
    MEDIUM = auto()            # Moderately similar
    LOW = auto()               # Dissimilar


class ListContext(Enum):
    """Experimental list context."""
    LIST_1 = auto()            # First learned list
    LIST_2 = auto()            # Second learned list


@dataclass
class MemoryAssociation:
    """
    A cue-response association.
    """
    id: str
    cue: str
    response: str
    list_context: ListContext
    strength: float
    encoding_time: float


@dataclass
class InterferenceEvent:
    """
    An interference event.
    """
    target_id: str
    interfering_id: str
    interference_type: InterferenceType
    strength_reduction: float
    similarity: SimilarityLevel


@dataclass
class RetrievalAttempt:
    """
    A retrieval attempt.
    """
    cue: str
    intended_list: ListContext
    retrieved: Optional[str]
    correct: bool
    intrusion: bool
    latency: float


@dataclass
class InterferenceMetrics:
    """
    Interference metrics.
    """
    proactive_interference: float
    retroactive_interference: float
    intrusion_rate: float
    correct_rate: float


# ============================================================================
# INTERFERENCE MEMORY MODEL
# ============================================================================

class InterferenceMemoryModel:
    """
    Memory model with interference dynamics.

    "Ba'el's competing memories." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        self._associations: Dict[str, MemoryAssociation] = {}
        self._cue_index: Dict[str, List[str]] = defaultdict(list)  # cue -> [assoc_ids]

        self._association_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._association_counter += 1
        return f"assoc_{self._association_counter}"

    def encode_association(
        self,
        cue: str,
        response: str,
        list_context: ListContext,
        strength: float = 1.0
    ) -> MemoryAssociation:
        """Encode a cue-response association."""
        assoc = MemoryAssociation(
            id=self._generate_id(),
            cue=cue,
            response=response,
            list_context=list_context,
            strength=strength,
            encoding_time=time.time()
        )

        self._associations[assoc.id] = assoc
        self._cue_index[cue].append(assoc.id)

        return assoc

    def calculate_similarity(
        self,
        response1: str,
        response2: str
    ) -> SimilarityLevel:
        """Calculate similarity between responses."""
        if response1 == response2:
            return SimilarityLevel.IDENTICAL

        # Simple similarity based on shared characters
        chars1 = set(response1.lower())
        chars2 = set(response2.lower())

        if not chars1 or not chars2:
            return SimilarityLevel.LOW

        overlap = len(chars1 & chars2) / len(chars1 | chars2)

        if overlap > 0.7:
            return SimilarityLevel.HIGH
        elif overlap > 0.4:
            return SimilarityLevel.MEDIUM
        else:
            return SimilarityLevel.LOW

    def apply_interference(
        self,
        new_assoc: MemoryAssociation,
        existing_assoc: MemoryAssociation
    ) -> InterferenceEvent:
        """Apply interference between associations."""
        similarity = self.calculate_similarity(
            new_assoc.response, existing_assoc.response
        )

        # Interference strength depends on similarity
        sim_weights = {
            SimilarityLevel.IDENTICAL: 0.5,
            SimilarityLevel.HIGH: 0.4,
            SimilarityLevel.MEDIUM: 0.2,
            SimilarityLevel.LOW: 0.05
        }

        interference_strength = sim_weights.get(similarity, 0.1)

        # Determine interference type
        if new_assoc.encoding_time > existing_assoc.encoding_time:
            # New item: retroactive interference on old
            int_type = InterferenceType.RETROACTIVE
            existing_assoc.strength -= interference_strength
            existing_assoc.strength = max(0.1, existing_assoc.strength)
        else:
            # Old item interfering proactively (harder to encode new)
            int_type = InterferenceType.PROACTIVE
            new_assoc.strength -= interference_strength * 0.5
            new_assoc.strength = max(0.1, new_assoc.strength)

        return InterferenceEvent(
            target_id=existing_assoc.id if int_type == InterferenceType.RETROACTIVE else new_assoc.id,
            interfering_id=new_assoc.id if int_type == InterferenceType.RETROACTIVE else existing_assoc.id,
            interference_type=int_type,
            strength_reduction=interference_strength,
            similarity=similarity
        )

    def retrieve(
        self,
        cue: str,
        target_list: ListContext = None
    ) -> RetrievalAttempt:
        """Attempt to retrieve response for cue."""
        assoc_ids = self._cue_index.get(cue, [])

        if not assoc_ids:
            return RetrievalAttempt(
                cue=cue,
                intended_list=target_list,
                retrieved=None,
                correct=False,
                intrusion=False,
                latency=2.0
            )

        # Get all associations for this cue
        associations = [self._associations[aid] for aid in assoc_ids]

        # Filter by target list if specified
        if target_list:
            target_assocs = [a for a in associations if a.list_context == target_list]
            non_target_assocs = [a for a in associations if a.list_context != target_list]
        else:
            target_assocs = associations
            non_target_assocs = []

        # Competition: strength-based retrieval
        all_candidates = [(a, a.strength) for a in associations]

        # Add noise
        noisy_strengths = [(a, s + random.gauss(0, 0.1)) for a, s in all_candidates]
        noisy_strengths.sort(key=lambda x: x[1], reverse=True)

        # Winner-takes-all (with probability)
        winner = noisy_strengths[0][0]

        # Check if correct (from target list)
        if target_list:
            correct = winner.list_context == target_list
            intrusion = winner.list_context != target_list
        else:
            correct = True  # No list specified
            intrusion = False

        # Latency: competition slows retrieval
        competition = len([s for _, s in noisy_strengths if s > noisy_strengths[0][1] * 0.7])
        latency = 0.5 + competition * 0.3 + random.uniform(0, 0.2)

        return RetrievalAttempt(
            cue=cue,
            intended_list=target_list,
            retrieved=winner.response,
            correct=correct,
            intrusion=intrusion,
            latency=latency
        )

    def get_associations_for_cue(
        self,
        cue: str
    ) -> List[MemoryAssociation]:
        """Get all associations for a cue."""
        assoc_ids = self._cue_index.get(cue, [])
        return [self._associations[aid] for aid in assoc_ids]


# ============================================================================
# EXPERIMENTAL PARADIGMS
# ============================================================================

class ABACParadigm:
    """
    A-B, A-C paired associate paradigm.

    Classic interference paradigm.

    "Ba'el's classic interference." — Ba'el
    """

    def __init__(
        self,
        memory: InterferenceMemoryModel
    ):
        """Initialize paradigm."""
        self._memory = memory
        self._list1: List[MemoryAssociation] = []
        self._list2: List[MemoryAssociation] = []
        self._interference_events: List[InterferenceEvent] = []

        self._lock = threading.RLock()

    def learn_list1(
        self,
        pairs: List[Tuple[str, str]]  # (cue, response) pairs
    ) -> None:
        """Learn first list (A-B pairs)."""
        for cue, response in pairs:
            assoc = self._memory.encode_association(
                cue, response, ListContext.LIST_1
            )
            self._list1.append(assoc)

    def learn_list2(
        self,
        pairs: List[Tuple[str, str]]  # (cue, response) pairs
    ) -> None:
        """Learn second list (A-C pairs, same cues, different responses)."""
        for cue, response in pairs:
            assoc = self._memory.encode_association(
                cue, response, ListContext.LIST_2
            )
            self._list2.append(assoc)

            # Apply interference to List 1 items with same cue
            list1_same_cue = [a for a in self._list1 if a.cue == cue]
            for old_assoc in list1_same_cue:
                event = self._memory.apply_interference(assoc, old_assoc)
                self._interference_events.append(event)

    def test_list1(self) -> List[RetrievalAttempt]:
        """Test recall of List 1."""
        results = []

        for assoc in self._list1:
            attempt = self._memory.retrieve(assoc.cue, ListContext.LIST_1)
            results.append(attempt)

        return results

    def test_list2(self) -> List[RetrievalAttempt]:
        """Test recall of List 2."""
        results = []

        for assoc in self._list2:
            attempt = self._memory.retrieve(assoc.cue, ListContext.LIST_2)
            results.append(attempt)

        return results

    def measure_retroactive_interference(self) -> float:
        """Measure retroactive interference on List 1."""
        # RI = reduction in List 1 recall due to List 2 learning
        list1_results = self.test_list1()

        # Compare to baseline (would be ~100% without interference)
        baseline = 1.0
        actual = sum(1 for r in list1_results if r.correct) / len(list1_results) if list1_results else 0

        return baseline - actual

    def measure_proactive_interference(self) -> float:
        """Measure proactive interference on List 2."""
        # PI = reduction in List 2 recall due to prior List 1 learning
        list2_results = self.test_list2()

        baseline = 1.0
        actual = sum(1 for r in list2_results if r.correct) / len(list2_results) if list2_results else 0

        return baseline - actual

    def get_intrusion_rate(self) -> Dict[str, float]:
        """Get intrusion rates."""
        list1_results = self.test_list1()
        list2_results = self.test_list2()

        list1_intrusions = sum(1 for r in list1_results if r.intrusion)
        list2_intrusions = sum(1 for r in list2_results if r.intrusion)

        return {
            'list1_intrusions': list1_intrusions / len(list1_results) if list1_results else 0,
            'list2_intrusions': list2_intrusions / len(list2_results) if list2_results else 0
        }


# ============================================================================
# INTERFERENCE ENGINE
# ============================================================================

class InterferenceEngine:
    """
    Complete interference engine.

    "Ba'el's memory competition." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._memory = InterferenceMemoryModel()
        self._retrieval_history: List[RetrievalAttempt] = []
        self._interference_events: List[InterferenceEvent] = []

        self._lock = threading.RLock()

    # Association management

    def encode(
        self,
        cue: str,
        response: str,
        list_context: ListContext = ListContext.LIST_1,
        strength: float = 1.0
    ) -> MemoryAssociation:
        """Encode a cue-response association."""
        assoc = self._memory.encode_association(cue, response, list_context, strength)

        # Check for interference with existing associations
        existing = self._memory.get_associations_for_cue(cue)
        for other in existing:
            if other.id != assoc.id:
                event = self._memory.apply_interference(assoc, other)
                self._interference_events.append(event)

        return assoc

    def retrieve(
        self,
        cue: str,
        target_list: ListContext = None
    ) -> RetrievalAttempt:
        """Retrieve response for cue."""
        attempt = self._memory.retrieve(cue, target_list)
        self._retrieval_history.append(attempt)
        return attempt

    # Experimental paradigms

    def run_abac_experiment(
        self,
        list1_pairs: List[Tuple[str, str]],
        list2_pairs: List[Tuple[str, str]]
    ) -> Dict[str, Any]:
        """Run A-B, A-C interference experiment."""
        paradigm = ABACParadigm(self._memory)

        # Learn lists
        paradigm.learn_list1(list1_pairs)
        paradigm.learn_list2(list2_pairs)

        # Measure interference
        ri = paradigm.measure_retroactive_interference()
        pi = paradigm.measure_proactive_interference()
        intrusions = paradigm.get_intrusion_rate()

        return {
            'retroactive_interference': ri,
            'proactive_interference': pi,
            'list1_intrusions': intrusions['list1_intrusions'],
            'list2_intrusions': intrusions['list2_intrusions']
        }

    def run_release_from_pi_experiment(
        self,
        buildup_lists: List[List[Tuple[str, str]]],  # Multiple lists, same category
        release_list: List[Tuple[str, str]]           # Different category
    ) -> Dict[str, Any]:
        """Run release from proactive interference experiment."""
        # Build up PI with same-category lists
        buildup_performance = []

        for i, pairs in enumerate(buildup_lists):
            context = ListContext.LIST_1 if i == 0 else ListContext.LIST_2
            for cue, response in pairs:
                self.encode(cue, response, context)

            # Test performance
            correct = 0
            for cue, _ in pairs:
                result = self.retrieve(cue, context)
                if result.correct:
                    correct += 1

            buildup_performance.append(correct / len(pairs))

        # Release with different category
        context = ListContext.LIST_2
        for cue, response in release_list:
            self.encode(cue, response, context)

        release_correct = 0
        for cue, _ in release_list:
            result = self.retrieve(cue, context)
            if result.correct:
                release_correct += 1

        release_performance = release_correct / len(release_list) if release_list else 0

        # Calculate PI buildup and release
        pi_buildup = buildup_performance[0] - buildup_performance[-1] if len(buildup_performance) > 1 else 0
        pi_release = release_performance - buildup_performance[-1] if buildup_performance else release_performance

        return {
            'buildup_performance': buildup_performance,
            'release_performance': release_performance,
            'pi_buildup': pi_buildup,
            'pi_release': pi_release,
            'release_successful': pi_release > 0.1
        }

    # Analysis

    def get_interference_summary(self) -> Dict[str, Any]:
        """Get summary of interference effects."""
        if not self._interference_events:
            return {
                'total_events': 0,
                'proactive': 0,
                'retroactive': 0,
                'avg_strength_reduction': 0
            }

        proactive = sum(1 for e in self._interference_events if e.interference_type == InterferenceType.PROACTIVE)
        retroactive = sum(1 for e in self._interference_events if e.interference_type == InterferenceType.RETROACTIVE)

        avg_reduction = sum(e.strength_reduction for e in self._interference_events) / len(self._interference_events)

        return {
            'total_events': len(self._interference_events),
            'proactive': proactive,
            'retroactive': retroactive,
            'avg_strength_reduction': avg_reduction
        }

    def get_metrics(self) -> InterferenceMetrics:
        """Get interference metrics."""
        if not self._retrieval_history:
            return InterferenceMetrics(
                proactive_interference=0.0,
                retroactive_interference=0.0,
                intrusion_rate=0.0,
                correct_rate=0.0
            )

        summary = self.get_interference_summary()

        correct = sum(1 for r in self._retrieval_history if r.correct)
        intrusions = sum(1 for r in self._retrieval_history if r.intrusion)

        return InterferenceMetrics(
            proactive_interference=summary['proactive'] / max(1, len(self._interference_events)),
            retroactive_interference=summary['retroactive'] / max(1, len(self._interference_events)),
            intrusion_rate=intrusions / len(self._retrieval_history),
            correct_rate=correct / len(self._retrieval_history)
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'associations': len(self._memory._associations),
            'retrieval_attempts': len(self._retrieval_history),
            'interference_events': len(self._interference_events)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_interference_engine() -> InterferenceEngine:
    """Create interference engine."""
    return InterferenceEngine()


def demonstrate_interference() -> Dict[str, Any]:
    """Demonstrate interference effects."""
    engine = create_interference_engine()

    # A-B, A-C paradigm
    list1 = [
        ("apple", "red"),
        ("banana", "yellow"),
        ("grape", "purple"),
        ("orange", "orange"),
        ("lemon", "yellow")
    ]

    # Same cues, different responses (interference)
    list2 = [
        ("apple", "green"),
        ("banana", "brown"),
        ("grape", "green"),
        ("orange", "blood"),
        ("lemon", "green")
    ]

    results = engine.run_abac_experiment(list1, list2)

    metrics = engine.get_metrics()
    summary = engine.get_interference_summary()

    return {
        'retroactive_interference': f"{results['retroactive_interference']:.0%}",
        'proactive_interference': f"{results['proactive_interference']:.0%}",
        'list1_intrusions': f"{results['list1_intrusions']:.0%}",
        'list2_intrusions': f"{results['list2_intrusions']:.0%}",
        'total_interference_events': summary['total_events'],
        'interpretation': (
            f"RI: {results['retroactive_interference']:.0%}, "
            f"PI: {results['proactive_interference']:.0%}. "
            f"New learning disrupts old memories (RI); old memories hinder new (PI)."
        )
    }


def get_interference_facts() -> Dict[str, str]:
    """Get facts about interference."""
    return {
        'proactive_interference': 'Old learning interferes with new learning',
        'retroactive_interference': 'New learning interferes with old memory',
        'ab_ac_paradigm': 'Classic design: same cues, different responses',
        'intrusions': 'Erroneous recalls from competing list',
        'similarity': 'Higher similarity = more interference',
        'release_from_pi': 'Category switch releases accumulated PI',
        'output_interference': 'Retrieved items block others',
        'unlearning_hypothesis': 'McGeoch: new associations weaken old'
    }
