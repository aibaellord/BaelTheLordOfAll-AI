"""
BAEL Fan Effect Engine
========================

More associations to a concept slows retrieval.
ACT-R inspired spreading activation interference.

"Ba'el's association overload." — Ba'el
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

logger = logging.getLogger("BAEL.FanEffect")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class AssociationType(Enum):
    """Types of associations."""
    LOCATION = auto()
    PERSON = auto()
    OBJECT = auto()
    ACTION = auto()
    PROPERTY = auto()


class NodeType(Enum):
    """Types of memory nodes."""
    CONCEPT = auto()
    INSTANCE = auto()
    PROPOSITION = auto()


@dataclass
class MemoryNode:
    """
    A node in associative memory.
    """
    id: str
    content: str
    node_type: NodeType
    base_activation: float


@dataclass
class Association:
    """
    An association between nodes.
    """
    source_id: str
    target_id: str
    association_type: AssociationType
    strength: float


@dataclass
class Proposition:
    """
    A proposition (fact) linking concepts.
    """
    id: str
    subject: str
    predicate: str
    object_: str


@dataclass
class RetrievalResult:
    """
    Result of retrieval attempt.
    """
    proposition_id: str
    retrieved: bool
    reaction_time_ms: float
    activation: float
    fan_count: int


@dataclass
class FanEffectMetrics:
    """
    Fan effect metrics.
    """
    mean_rt_fan1: float
    mean_rt_fan2: float
    mean_rt_fan3: float
    fan_effect_slope: float
    accuracy: float


# ============================================================================
# ACTIVATION SPREADING
# ============================================================================

class ActivationSpreader:
    """
    ACT-R style spreading activation.

    "Ba'el's activation flow." — Ba'el
    """

    def __init__(self):
        """Initialize spreader."""
        # ACT-R parameters
        self._source_activation = 1.0  # W in ACT-R
        self._decay_rate = 0.5

        self._lock = threading.RLock()

    def calculate_spreading(
        self,
        source_activation: float,
        fan: int
    ) -> float:
        """Calculate spreading activation given fan."""
        if fan <= 0:
            return 0

        # ACT-R: S_ji = W / fan
        spreading = source_activation / fan

        return spreading

    def calculate_total_activation(
        self,
        base_activation: float,
        spreading_activations: List[float]
    ) -> float:
        """Calculate total activation."""
        # Total = base + sum of spreading
        total = base_activation + sum(spreading_activations)

        return total


# ============================================================================
# MEMORY NETWORK
# ============================================================================

class AssociativeMemory:
    """
    Associative memory network.

    "Ba'el's web of knowledge." — Ba'el
    """

    def __init__(self):
        """Initialize memory."""
        self._spreader = ActivationSpreader()

        self._nodes: Dict[str, MemoryNode] = {}
        self._associations: List[Association] = {}
        self._propositions: Dict[str, Proposition] = {}

        # Fan counts per concept
        self._fan_counts: Dict[str, int] = defaultdict(int)

        self._node_counter = 0
        self._prop_counter = 0
        self._lock = threading.RLock()

    def _generate_node_id(self) -> str:
        self._node_counter += 1
        return f"node_{self._node_counter}"

    def _generate_prop_id(self) -> str:
        self._prop_counter += 1
        return f"prop_{self._prop_counter}"

    def add_concept(
        self,
        content: str,
        base_activation: float = 0.5
    ) -> MemoryNode:
        """Add a concept node."""
        node = MemoryNode(
            id=self._generate_node_id(),
            content=content,
            node_type=NodeType.CONCEPT,
            base_activation=base_activation
        )

        self._nodes[node.id] = node
        return node

    def add_proposition(
        self,
        subject: str,
        predicate: str,
        object_: str
    ) -> Proposition:
        """Add a proposition, updating fan counts."""
        # Create or get nodes
        subject_node = self._get_or_create_node(subject)
        object_node = self._get_or_create_node(object_)

        prop = Proposition(
            id=self._generate_prop_id(),
            subject=subject,
            predicate=predicate,
            object_=object_
        )

        self._propositions[prop.id] = prop

        # Update fan counts
        self._fan_counts[subject] += 1
        self._fan_counts[object_] += 1

        return prop

    def _get_or_create_node(
        self,
        content: str
    ) -> MemoryNode:
        """Get existing or create new node."""
        for node in self._nodes.values():
            if node.content == content:
                return node

        return self.add_concept(content)

    def get_fan(
        self,
        concept: str
    ) -> int:
        """Get fan count for a concept."""
        return self._fan_counts.get(concept, 0)

    def retrieve_proposition(
        self,
        subject: str,
        object_: str
    ) -> RetrievalResult:
        """Retrieve proposition with fan effect."""
        # Find matching proposition
        matching = None
        for prop in self._propositions.values():
            if prop.subject == subject and prop.object_ == object_:
                matching = prop
                break

        if not matching:
            # Proposition not found
            return RetrievalResult(
                proposition_id="",
                retrieved=False,
                reaction_time_ms=2000,
                activation=0,
                fan_count=0
            )

        # Calculate activation with fan effect
        subject_fan = self.get_fan(subject)
        object_fan = self.get_fan(object_)

        # Spreading activation from each concept
        subject_spreading = self._spreader.calculate_spreading(1.0, subject_fan)
        object_spreading = self._spreader.calculate_spreading(1.0, object_fan)

        # Total activation
        base_activation = 0.4
        total_activation = self._spreader.calculate_total_activation(
            base_activation,
            [subject_spreading, object_spreading]
        )

        # RT = F - f * activation (faster with higher activation)
        base_rt = 1500  # ms
        activation_effect = total_activation * 500

        rt = base_rt - activation_effect
        rt += random.gauss(0, 50)
        rt = max(500, rt)

        # Fan effect: more fan = slower RT
        fan_penalty = (subject_fan + object_fan) * 50  # ms per fan
        rt += fan_penalty

        # Accuracy
        retrieval_prob = min(0.99, 0.7 + total_activation * 0.2)
        retrieved = random.random() < retrieval_prob

        return RetrievalResult(
            proposition_id=matching.id,
            retrieved=retrieved,
            reaction_time_ms=rt,
            activation=total_activation,
            fan_count=subject_fan + object_fan
        )


# ============================================================================
# EXPERIMENTAL PARADIGM
# ============================================================================

class FanEffectParadigm:
    """
    Fan effect experimental paradigm.

    "Ba'el's fan experiment." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._memory = AssociativeMemory()

        self._study_items: List[Proposition] = []
        self._retrieval_results: List[RetrievalResult] = []

        self._lock = threading.RLock()

    def create_study_set(
        self,
        n_locations: int = 4,
        n_people: int = 4,
        fan_per_location: List[int] = None,
        fan_per_person: List[int] = None
    ) -> List[Proposition]:
        """Create study set with controlled fan."""
        if fan_per_location is None:
            fan_per_location = [1, 2, 3, 4][:n_locations]
        if fan_per_person is None:
            fan_per_person = [1, 2, 3, 4][:n_people]

        locations = [f"location_{i}" for i in range(n_locations)]
        people = [f"person_{i}" for i in range(n_people)]

        propositions = []
        person_idx = 0

        for loc_idx, (location, loc_fan) in enumerate(zip(locations, fan_per_location)):
            for _ in range(loc_fan):
                if person_idx >= len(people):
                    person_idx = 0

                person = people[person_idx]
                prop = self._memory.add_proposition(
                    subject=person,
                    predicate="is_in",
                    object_=location
                )
                propositions.append(prop)
                person_idx += 1

        self._study_items = propositions
        return propositions

    def study_phase(
        self,
        study_time_per_item: float = 2.0
    ) -> None:
        """Study phase (items already in memory)."""
        # In real experiment, this would involve presentation
        # Here, items are already encoded via add_proposition
        pass

    def test_phase(
        self
    ) -> List[RetrievalResult]:
        """Test phase - retrieve studied propositions."""
        results = []

        for prop in self._study_items:
            result = self._memory.retrieve_proposition(prop.subject, prop.object_)
            results.append(result)

        self._retrieval_results = results
        return results

    def run_experiment(
        self
    ) -> Dict[str, Any]:
        """Run full fan effect experiment."""
        # Create study set with varying fan
        self.create_study_set(
            n_locations=4,
            n_people=4,
            fan_per_location=[1, 2, 3, 4],
            fan_per_person=[1, 1, 2, 2]
        )

        # Study phase
        self.study_phase()

        # Test phase
        results = self.test_phase()

        # Analyze by fan
        fan_results: Dict[int, List[float]] = defaultdict(list)

        for result in results:
            fan = result.fan_count
            fan_results[fan].append(result.reaction_time_ms)

        # Calculate means
        mean_rts = {}
        for fan, rts in sorted(fan_results.items()):
            mean_rts[f"fan_{fan}"] = sum(rts) / len(rts) if rts else 0

        # Calculate slope
        fans = list(fan_results.keys())
        rts_means = [sum(fan_results[f]) / len(fan_results[f]) for f in fans]

        if len(fans) >= 2:
            slope = (rts_means[-1] - rts_means[0]) / (fans[-1] - fans[0])
        else:
            slope = 0

        accuracy = sum(1 for r in results if r.retrieved) / len(results) if results else 0

        return {
            'mean_rts_by_fan': mean_rts,
            'fan_effect_slope': slope,
            'accuracy': accuracy,
            'n_items': len(self._study_items)
        }


# ============================================================================
# FAN EFFECT ENGINE
# ============================================================================

class FanEffectEngine:
    """
    Complete fan effect engine.

    "Ba'el's association interference." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = FanEffectParadigm()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Memory operations

    def add_fact(
        self,
        subject: str,
        predicate: str,
        object_: str
    ) -> Proposition:
        """Add a fact to memory."""
        return self._paradigm._memory.add_proposition(subject, predicate, object_)

    def get_fan(
        self,
        concept: str
    ) -> int:
        """Get fan for a concept."""
        return self._paradigm._memory.get_fan(concept)

    # Retrieval

    def retrieve(
        self,
        subject: str,
        object_: str
    ) -> RetrievalResult:
        """Retrieve a fact."""
        return self._paradigm._memory.retrieve_proposition(subject, object_)

    # Experiments

    def run_fan_experiment(
        self
    ) -> Dict[str, Any]:
        """Run fan effect experiment."""
        # Reset paradigm
        self._paradigm = FanEffectParadigm()
        result = self._paradigm.run_experiment()
        self._experiment_results.append(result)
        return result

    def run_fan_comparison(
        self,
        fans_to_test: List[int] = None
    ) -> Dict[str, Any]:
        """Compare retrieval across different fan levels."""
        if fans_to_test is None:
            fans_to_test = [1, 2, 3, 4, 5]

        results = {}

        for fan in fans_to_test:
            # Create memory with specific fan
            paradigm = FanEffectParadigm()

            # Add one concept with specified fan
            concept = f"concept_fan{fan}"
            for i in range(fan):
                paradigm._memory.add_proposition(
                    subject=concept,
                    predicate="has",
                    object_=f"property_{i}"
                )

            # Retrieve
            rts = []
            for i in range(fan):
                result = paradigm._memory.retrieve_proposition(concept, f"property_{i}")
                rts.append(result.reaction_time_ms)

            results[f"fan_{fan}"] = {
                'mean_rt': sum(rts) / len(rts) if rts else 0,
                'n_associations': fan
            }

        return results

    def demonstrate_actr_spreading(
        self
    ) -> Dict[str, Any]:
        """Demonstrate ACT-R spreading activation."""
        memory = AssociativeMemory()

        # Low fan concept
        memory.add_proposition("specialist", "knows", "rare_skill")

        # High fan concept
        for i in range(5):
            memory.add_proposition("generalist", "knows", f"common_skill_{i}")

        # Retrieve
        specialist_result = memory.retrieve_proposition("specialist", "rare_skill")
        generalist_results = []
        for i in range(5):
            result = memory.retrieve_proposition("generalist", f"common_skill_{i}")
            generalist_results.append(result)

        return {
            'specialist': {
                'fan': memory.get_fan("specialist"),
                'rt': f"{specialist_result.reaction_time_ms:.0f} ms",
                'activation': f"{specialist_result.activation:.2f}"
            },
            'generalist': {
                'fan': memory.get_fan("generalist"),
                'mean_rt': f"{sum(r.reaction_time_ms for r in generalist_results) / len(generalist_results):.0f} ms",
                'mean_activation': f"{sum(r.activation for r in generalist_results) / len(generalist_results):.2f}"
            },
            'interpretation': 'More associations = slower retrieval (fan effect)'
        }

    # Analysis

    def get_metrics(self) -> FanEffectMetrics:
        """Get fan effect metrics."""
        if not self._experiment_results:
            self.run_fan_experiment()

        last = self._experiment_results[-1]
        rts = last['mean_rts_by_fan']

        return FanEffectMetrics(
            mean_rt_fan1=rts.get('fan_1', rts.get('fan_2', 0)),
            mean_rt_fan2=rts.get('fan_3', rts.get('fan_4', 0)),
            mean_rt_fan3=rts.get('fan_5', rts.get('fan_6', 0)),
            fan_effect_slope=last['fan_effect_slope'],
            accuracy=last['accuracy']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'propositions': len(self._paradigm._memory._propositions),
            'experiments': len(self._experiment_results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_fan_effect_engine() -> FanEffectEngine:
    """Create fan effect engine."""
    return FanEffectEngine()


def demonstrate_fan_effect() -> Dict[str, Any]:
    """Demonstrate fan effect."""
    engine = create_fan_effect_engine()

    # Basic experiment
    basic = engine.run_fan_experiment()

    # Fan comparison
    comparison = engine.run_fan_comparison([1, 2, 3, 4])

    # ACT-R demonstration
    actr = engine.demonstrate_actr_spreading()

    return {
        'fan_effect': {
            'rts_by_fan': basic['mean_rts_by_fan'],
            'slope': f"{basic['fan_effect_slope']:.0f} ms/association",
            'accuracy': f"{basic['accuracy']:.0%}"
        },
        'fan_comparison': {
            fan: f"{data['mean_rt']:.0f} ms"
            for fan, data in comparison.items()
        },
        'actr_demo': actr,
        'interpretation': (
            f"Fan effect slope: {basic['fan_effect_slope']:.0f} ms/association. "
            f"More associations slow retrieval due to spreading activation division."
        )
    }


def get_fan_effect_facts() -> Dict[str, str]:
    """Get facts about fan effect."""
    return {
        'anderson_1974': 'Original demonstration of fan effect',
        'act_r': 'Core phenomenon in ACT-R cognitive architecture',
        'spreading_activation': 'Activation spreads and divides among associations',
        'retrieval_interference': 'More associations = more retrieval competition',
        'expertise': 'Experts show reduced fan effect in their domain',
        'elaboration': 'Rich elaboration can reduce fan effect',
        'proposition_network': 'Memory as network of propositions',
        'verification_time': 'RT increases linearly with fan'
    }
