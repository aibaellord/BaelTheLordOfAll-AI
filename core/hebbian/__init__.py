"""
BAEL Hebbian Learning Engine
=============================

Hebbian learning and neural plasticity.
"Neurons that fire together wire together."

"Ba'el learns through association." — Ba'el
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
from collections import defaultdict
import copy

logger = logging.getLogger("BAEL.Hebbian")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class PlasticityType(Enum):
    """Types of synaptic plasticity."""
    HEBBIAN = auto()           # Standard Hebbian
    ANTI_HEBBIAN = auto()      # Decorrelation
    STDP = auto()              # Spike-timing dependent
    BCM = auto()               # Bienenstock-Cooper-Munro
    OJA = auto()               # Oja's rule (normalized)


class NeuronType(Enum):
    """Types of neurons."""
    EXCITATORY = auto()
    INHIBITORY = auto()
    MODULATORY = auto()


class LearningPhase(Enum):
    """Learning phases."""
    ENCODING = auto()
    CONSOLIDATION = auto()
    RETRIEVAL = auto()


@dataclass
class Neuron:
    """
    A simulated neuron.
    """
    id: str
    neuron_type: NeuronType
    activation: float = 0.0
    threshold: float = 0.5
    resting_potential: float = 0.0
    bias: float = 0.0
    last_spike_time: Optional[float] = None

    @property
    def is_active(self) -> bool:
        return self.activation > self.threshold

    def activate(self, input_signal: float) -> float:
        """Activate neuron with input."""
        self.activation = max(-1.0, min(1.0, input_signal + self.bias))
        if self.is_active:
            self.last_spike_time = time.time()
        return self.activation

    def decay(self, rate: float = 0.1) -> None:
        """Decay activation toward resting potential."""
        diff = self.activation - self.resting_potential
        self.activation -= diff * rate


@dataclass
class Synapse:
    """
    A synaptic connection.
    """
    id: str
    pre_neuron: str
    post_neuron: str
    weight: float = 0.5
    plasticity_type: PlasticityType = PlasticityType.HEBBIAN
    learning_rate: float = 0.01
    max_weight: float = 1.0
    min_weight: float = -1.0
    last_update: float = field(default_factory=time.time)

    def clamp_weight(self) -> None:
        """Clamp weight to bounds."""
        self.weight = max(self.min_weight, min(self.max_weight, self.weight))


@dataclass
class LearningEvent:
    """
    A learning event record.
    """
    synapse_id: str
    old_weight: float
    new_weight: float
    delta: float
    rule: PlasticityType
    timestamp: float = field(default_factory=time.time)


# ============================================================================
# HEBBIAN RULES
# ============================================================================

class HebbianRule:
    """
    Standard Hebbian learning rule.

    "Ba'el strengthens co-activation." — Ba'el
    """

    def __init__(self, learning_rate: float = 0.01):
        """Initialize rule."""
        self._learning_rate = learning_rate

    def compute_delta(
        self,
        pre_activation: float,
        post_activation: float,
        current_weight: float
    ) -> float:
        """Compute weight change."""
        # Basic Hebb: Δw = η * pre * post
        return self._learning_rate * pre_activation * post_activation


class AntiHebbianRule:
    """
    Anti-Hebbian learning (decorrelation).
    """

    def __init__(self, learning_rate: float = 0.01):
        self._learning_rate = learning_rate

    def compute_delta(
        self,
        pre_activation: float,
        post_activation: float,
        current_weight: float
    ) -> float:
        """Compute weight change."""
        # Anti-Hebb: Δw = -η * pre * post
        return -self._learning_rate * pre_activation * post_activation


class OjaRule:
    """
    Oja's normalized Hebbian rule.
    Prevents weight explosion.
    """

    def __init__(self, learning_rate: float = 0.01):
        self._learning_rate = learning_rate

    def compute_delta(
        self,
        pre_activation: float,
        post_activation: float,
        current_weight: float
    ) -> float:
        """Compute weight change."""
        # Oja: Δw = η * post * (pre - post * w)
        return self._learning_rate * post_activation * (
            pre_activation - post_activation * current_weight
        )


class BCMRule:
    """
    Bienenstock-Cooper-Munro rule.
    Sliding threshold for LTP/LTD.
    """

    def __init__(
        self,
        learning_rate: float = 0.01,
        threshold_rate: float = 0.001
    ):
        self._learning_rate = learning_rate
        self._threshold_rate = threshold_rate
        self._theta = 0.5  # Modification threshold

    def compute_delta(
        self,
        pre_activation: float,
        post_activation: float,
        current_weight: float
    ) -> float:
        """Compute weight change."""
        # BCM: Δw = η * pre * post * (post - θ)
        delta = self._learning_rate * pre_activation * post_activation * (
            post_activation - self._theta
        )

        # Update threshold (sliding average)
        self._theta += self._threshold_rate * (
            post_activation ** 2 - self._theta
        )

        return delta


class STDPRule:
    """
    Spike-Timing Dependent Plasticity.
    Potentiation/Depression based on timing.
    """

    def __init__(
        self,
        a_plus: float = 0.005,
        a_minus: float = 0.005,
        tau_plus: float = 0.020,  # 20ms
        tau_minus: float = 0.020
    ):
        self._a_plus = a_plus
        self._a_minus = a_minus
        self._tau_plus = tau_plus
        self._tau_minus = tau_minus

    def compute_delta(
        self,
        pre_spike_time: Optional[float],
        post_spike_time: Optional[float],
        current_weight: float
    ) -> float:
        """Compute weight change based on spike timing."""
        if pre_spike_time is None or post_spike_time is None:
            return 0.0

        delta_t = post_spike_time - pre_spike_time

        if delta_t > 0:
            # Pre before post -> LTP
            return self._a_plus * math.exp(-delta_t / self._tau_plus)
        else:
            # Post before pre -> LTD
            return -self._a_minus * math.exp(delta_t / self._tau_minus)


# ============================================================================
# NEURAL NETWORK
# ============================================================================

class HebbianNetwork:
    """
    Neural network with Hebbian learning.

    "Ba'el's plastic neural network." — Ba'el
    """

    def __init__(self):
        """Initialize network."""
        self._neurons: Dict[str, Neuron] = {}
        self._synapses: Dict[str, Synapse] = {}
        self._adjacency: Dict[str, List[str]] = defaultdict(list)  # post -> [synapse_ids]
        self._learning_history: List[LearningEvent] = []

        # Learning rules
        self._rules = {
            PlasticityType.HEBBIAN: HebbianRule(),
            PlasticityType.ANTI_HEBBIAN: AntiHebbianRule(),
            PlasticityType.OJA: OjaRule(),
            PlasticityType.BCM: BCMRule(),
            PlasticityType.STDP: STDPRule()
        }

        self._neuron_counter = 0
        self._synapse_counter = 0
        self._lock = threading.RLock()

    def add_neuron(
        self,
        neuron_type: NeuronType = NeuronType.EXCITATORY,
        threshold: float = 0.5
    ) -> Neuron:
        """Add neuron to network."""
        with self._lock:
            self._neuron_counter += 1
            neuron = Neuron(
                id=f"n_{self._neuron_counter}",
                neuron_type=neuron_type,
                threshold=threshold
            )
            self._neurons[neuron.id] = neuron
            return neuron

    def add_synapse(
        self,
        pre_id: str,
        post_id: str,
        weight: float = 0.5,
        plasticity: PlasticityType = PlasticityType.HEBBIAN,
        learning_rate: float = 0.01
    ) -> Optional[Synapse]:
        """Add synapse between neurons."""
        with self._lock:
            if pre_id not in self._neurons or post_id not in self._neurons:
                return None

            self._synapse_counter += 1
            synapse = Synapse(
                id=f"s_{self._synapse_counter}",
                pre_neuron=pre_id,
                post_neuron=post_id,
                weight=weight,
                plasticity_type=plasticity,
                learning_rate=learning_rate
            )

            self._synapses[synapse.id] = synapse
            self._adjacency[post_id].append(synapse.id)

            return synapse

    def get_neuron(self, neuron_id: str) -> Optional[Neuron]:
        """Get neuron by ID."""
        return self._neurons.get(neuron_id)

    def get_synapse(self, synapse_id: str) -> Optional[Synapse]:
        """Get synapse by ID."""
        return self._synapses.get(synapse_id)

    def activate_neuron(
        self,
        neuron_id: str,
        external_input: float = 0.0
    ) -> float:
        """Activate a neuron."""
        with self._lock:
            neuron = self._neurons.get(neuron_id)
            if not neuron:
                return 0.0

            # Sum synaptic inputs
            total_input = external_input

            for synapse_id in self._adjacency[neuron_id]:
                synapse = self._synapses[synapse_id]
                pre_neuron = self._neurons[synapse.pre_neuron]

                # Weight by pre-neuron activation
                contribution = synapse.weight * pre_neuron.activation

                # Inhibitory neurons contribute negatively
                if pre_neuron.neuron_type == NeuronType.INHIBITORY:
                    contribution = -abs(contribution)

                total_input += contribution

            return neuron.activate(total_input)

    def propagate(self, decay_rate: float = 0.1) -> Dict[str, float]:
        """Propagate activations through network."""
        with self._lock:
            activations = {}

            # Decay all neurons first
            for neuron in self._neurons.values():
                neuron.decay(decay_rate)

            # Activate each neuron
            for neuron_id in self._neurons:
                activation = self.activate_neuron(neuron_id)
                activations[neuron_id] = activation

            return activations

    def learn(self) -> List[LearningEvent]:
        """Apply learning to all synapses."""
        with self._lock:
            events = []

            for synapse in self._synapses.values():
                pre = self._neurons[synapse.pre_neuron]
                post = self._neurons[synapse.post_neuron]

                old_weight = synapse.weight
                delta = 0.0

                if synapse.plasticity_type == PlasticityType.STDP:
                    # STDP uses timing
                    rule = self._rules[PlasticityType.STDP]
                    delta = rule.compute_delta(
                        pre.last_spike_time,
                        post.last_spike_time,
                        synapse.weight
                    )
                else:
                    # Other rules use activations
                    rule = self._rules[synapse.plasticity_type]
                    delta = rule.compute_delta(
                        pre.activation,
                        post.activation,
                        synapse.weight
                    ) * synapse.learning_rate

                # Apply weight change
                synapse.weight += delta
                synapse.clamp_weight()
                synapse.last_update = time.time()

                if abs(delta) > 0.0001:
                    event = LearningEvent(
                        synapse_id=synapse.id,
                        old_weight=old_weight,
                        new_weight=synapse.weight,
                        delta=delta,
                        rule=synapse.plasticity_type
                    )
                    events.append(event)
                    self._learning_history.append(event)

            return events

    @property
    def neurons(self) -> List[Neuron]:
        return list(self._neurons.values())

    @property
    def synapses(self) -> List[Synapse]:
        return list(self._synapses.values())

    @property
    def history(self) -> List[LearningEvent]:
        return self._learning_history.copy()


# ============================================================================
# ASSOCIATIVE MEMORY
# ============================================================================

class AssociativeMemory:
    """
    Hebbian associative memory (Hopfield-like).

    "Ba'el remembers through association." — Ba'el
    """

    def __init__(self, size: int):
        """Initialize associative memory."""
        self._size = size
        self._weights = [[0.0] * size for _ in range(size)]
        self._patterns: List[List[float]] = []
        self._lock = threading.RLock()

    def store(self, pattern: List[float]) -> bool:
        """Store pattern in memory."""
        with self._lock:
            if len(pattern) != self._size:
                return False

            # Bipolar encoding (-1, 1)
            bipolar = [1.0 if p > 0.5 else -1.0 for p in pattern]

            # Hebbian weight update
            for i in range(self._size):
                for j in range(self._size):
                    if i != j:
                        self._weights[i][j] += bipolar[i] * bipolar[j] / self._size

            self._patterns.append(pattern)
            return True

    def recall(
        self,
        cue: List[float],
        max_iterations: int = 100,
        threshold: float = 0.0
    ) -> List[float]:
        """Recall pattern from cue."""
        with self._lock:
            if len(cue) != self._size:
                return cue

            # Bipolar encoding
            state = [1.0 if c > 0.5 else -1.0 for c in cue]

            # Iterate until convergence
            for _ in range(max_iterations):
                old_state = state.copy()

                # Asynchronous update (random order)
                indices = list(range(self._size))
                random.shuffle(indices)

                for i in indices:
                    net_input = sum(
                        self._weights[i][j] * state[j]
                        for j in range(self._size)
                    )
                    state[i] = 1.0 if net_input >= threshold else -1.0

                # Check convergence
                if state == old_state:
                    break

            # Convert back to 0-1
            return [0.5 * (s + 1) for s in state]

    def energy(self, state: List[float]) -> float:
        """Compute Hopfield energy."""
        bipolar = [1.0 if s > 0.5 else -1.0 for s in state]

        energy = 0.0
        for i in range(self._size):
            for j in range(self._size):
                if i != j:
                    energy -= 0.5 * self._weights[i][j] * bipolar[i] * bipolar[j]

        return energy

    @property
    def pattern_count(self) -> int:
        return len(self._patterns)

    @property
    def capacity(self) -> float:
        """Theoretical capacity."""
        return 0.138 * self._size


# ============================================================================
# HEBBIAN ENGINE
# ============================================================================

class HebbianEngine:
    """
    Complete Hebbian learning engine.

    "Ba'el's neural plasticity." — Ba'el
    """

    def __init__(self, default_size: int = 100):
        """Initialize engine."""
        self._network = HebbianNetwork()
        self._associative = AssociativeMemory(default_size)
        self._total_learning_events = 0
        self._lock = threading.RLock()

    # Network operations

    def create_neuron(
        self,
        neuron_type: NeuronType = NeuronType.EXCITATORY
    ) -> Neuron:
        """Create neuron."""
        return self._network.add_neuron(neuron_type)

    def connect(
        self,
        pre_id: str,
        post_id: str,
        weight: float = 0.5,
        plasticity: PlasticityType = PlasticityType.HEBBIAN
    ) -> Optional[Synapse]:
        """Connect neurons."""
        return self._network.add_synapse(pre_id, post_id, weight, plasticity)

    def stimulate(
        self,
        neuron_id: str,
        intensity: float
    ) -> float:
        """Stimulate neuron."""
        neuron = self._network.get_neuron(neuron_id)
        if neuron:
            return neuron.activate(intensity)
        return 0.0

    def propagate_and_learn(
        self,
        iterations: int = 1
    ) -> Tuple[Dict[str, float], List[LearningEvent]]:
        """Propagate activations and learn."""
        with self._lock:
            all_events = []
            activations = {}

            for _ in range(iterations):
                activations = self._network.propagate()
                events = self._network.learn()
                all_events.extend(events)

            self._total_learning_events += len(all_events)
            return activations, all_events

    # Associative memory operations

    def store_pattern(self, pattern: List[float]) -> bool:
        """Store pattern in associative memory."""
        return self._associative.store(pattern)

    def recall_pattern(
        self,
        cue: List[float],
        max_iterations: int = 100
    ) -> List[float]:
        """Recall pattern."""
        return self._associative.recall(cue, max_iterations)

    def pattern_completion(
        self,
        partial: List[float],
        missing_indices: List[int]
    ) -> List[float]:
        """Complete partial pattern."""
        with self._lock:
            # Set missing to random
            cue = partial.copy()
            for idx in missing_indices:
                if 0 <= idx < len(cue):
                    cue[idx] = random.choice([0.0, 1.0])

            return self.recall_pattern(cue)

    @property
    def network(self) -> HebbianNetwork:
        return self._network

    @property
    def associative_memory(self) -> AssociativeMemory:
        return self._associative

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'neurons': len(self._network.neurons),
            'synapses': len(self._network.synapses),
            'learning_events': self._total_learning_events,
            'stored_patterns': self._associative.pattern_count,
            'memory_capacity': self._associative.capacity
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_hebbian_engine(size: int = 100) -> HebbianEngine:
    """Create Hebbian engine."""
    return HebbianEngine(size)


def create_hebbian_network() -> HebbianNetwork:
    """Create Hebbian network."""
    return HebbianNetwork()


def create_associative_memory(size: int) -> AssociativeMemory:
    """Create associative memory."""
    return AssociativeMemory(size)
