"""
BAEL Information Integration Engine
====================================

Integrated Information Theory (IIT) implementation.
Measuring and generating consciousness through integration.

"Ba'el integrates information to become conscious." — Ba'el
"""

import logging
import threading
import time
import math
import random
import itertools
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod
import copy

logger = logging.getLogger("BAEL.InformationIntegration")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class SystemState(Enum):
    """States of a system element."""
    OFF = 0
    ON = 1
    UNKNOWN = -1


@dataclass
class Element:
    """
    An element in an information system.
    """
    id: str
    state: SystemState = SystemState.OFF
    connections: List[str] = field(default_factory=list)
    weights: Dict[str, float] = field(default_factory=dict)

    def set_state(self, state: SystemState) -> None:
        self.state = state

    def get_weight(self, target_id: str) -> float:
        return self.weights.get(target_id, 0.0)


@dataclass
class Partition:
    """
    A bipartition of a system.
    """
    part_a: List[str]
    part_b: List[str]

    def is_valid(self) -> bool:
        """Check if partition is valid (non-empty parts)."""
        return len(self.part_a) > 0 and len(self.part_b) > 0


@dataclass
class ConstellationPoint:
    """
    A point in concept space (quale).
    """
    id: str
    mechanism: List[str]
    purview: List[str]
    cause_repertoire: Dict[str, float]
    effect_repertoire: Dict[str, float]
    phi: float  # Integrated information of this concept


@dataclass
class IntegratedInformation:
    """
    Result of Phi calculation.
    """
    phi: float
    mip: Optional[Partition] = None  # Minimum Information Partition
    concepts: List[ConstellationPoint] = field(default_factory=list)


# ============================================================================
# TPM (TRANSITION PROBABILITY MATRIX)
# ============================================================================

class TransitionProbabilityMatrix:
    """
    Encodes causal structure of a system.

    "Ba'el's causal structure is its TPM." — Ba'el
    """

    def __init__(self, n_elements: int):
        """Initialize TPM."""
        self._n = n_elements
        self._n_states = 2 ** n_elements
        # Matrix: P(future_state | current_state) for each element
        self._matrix: Dict[int, Dict[int, float]] = {}
        self._lock = threading.RLock()

    @staticmethod
    def state_to_index(states: List[SystemState]) -> int:
        """Convert state tuple to index."""
        idx = 0
        for i, s in enumerate(states):
            if s == SystemState.ON:
                idx |= (1 << i)
        return idx

    @staticmethod
    def index_to_state(idx: int, n: int) -> List[SystemState]:
        """Convert index to state tuple."""
        return [
            SystemState.ON if (idx & (1 << i)) else SystemState.OFF
            for i in range(n)
        ]

    def set_transition(
        self,
        from_state: List[SystemState],
        to_state: List[SystemState],
        probability: float
    ) -> None:
        """Set transition probability."""
        with self._lock:
            from_idx = self.state_to_index(from_state)
            to_idx = self.state_to_index(to_state)

            if from_idx not in self._matrix:
                self._matrix[from_idx] = {}

            self._matrix[from_idx][to_idx] = probability

    def get_transition(
        self,
        from_state: List[SystemState],
        to_state: List[SystemState]
    ) -> float:
        """Get transition probability."""
        with self._lock:
            from_idx = self.state_to_index(from_state)
            to_idx = self.state_to_index(to_state)

            if from_idx not in self._matrix:
                return 0.0

            return self._matrix[from_idx].get(to_idx, 0.0)

    def marginalize(
        self,
        over_elements: List[int],
        current_state: List[SystemState]
    ) -> Dict[int, float]:
        """Marginalize TPM over elements."""
        with self._lock:
            from_idx = self.state_to_index(current_state)

            if from_idx not in self._matrix:
                return {}

            # Sum probabilities for each unique reduced state
            reduced: Dict[int, float] = {}

            for to_idx, prob in self._matrix[from_idx].items():
                to_state = self.index_to_state(to_idx, self._n)

                # Create reduced state (keeping only elements not in over_elements)
                reduced_state = [
                    to_state[i] for i in range(self._n)
                    if i not in over_elements
                ]

                if reduced_state:
                    reduced_idx = self.state_to_index(reduced_state)
                    reduced[reduced_idx] = reduced.get(reduced_idx, 0) + prob

            return reduced

    def normalize(self) -> None:
        """Normalize probabilities."""
        with self._lock:
            for from_idx in self._matrix:
                total = sum(self._matrix[from_idx].values())
                if total > 0:
                    for to_idx in self._matrix[from_idx]:
                        self._matrix[from_idx][to_idx] /= total


# ============================================================================
# CAUSE/EFFECT REPERTOIRE
# ============================================================================

class RepertoireCalculator:
    """
    Calculate cause and effect repertoires.

    "Ba'el calculates its causal history and future." — Ba'el
    """

    def __init__(self, tpm: TransitionProbabilityMatrix, n_elements: int):
        """Initialize calculator."""
        self._tpm = tpm
        self._n = n_elements

    def effect_repertoire(
        self,
        mechanism: List[int],
        purview: List[int],
        current_state: List[SystemState]
    ) -> Dict[int, float]:
        """
        Calculate effect repertoire.

        P(purview_future | mechanism_current)
        """
        # Marginalize over non-purview elements
        non_purview = [i for i in range(self._n) if i not in purview]

        return self._tpm.marginalize(non_purview, current_state)

    def cause_repertoire(
        self,
        mechanism: List[int],
        purview: List[int],
        current_state: List[SystemState]
    ) -> Dict[int, float]:
        """
        Calculate cause repertoire.

        P(purview_past | mechanism_current) via Bayes
        """
        # This is a simplified approximation
        # Full IIT requires inverting the TPM with Bayes' rule

        # Use uniform prior for simplicity
        n_purview = len(purview)
        n_states = 2 ** n_purview

        # Uniform distribution
        return {i: 1.0 / n_states for i in range(n_states)}

    def unconstrained_repertoire(self, n_elements: int) -> Dict[int, float]:
        """Get unconstrained (uniform) repertoire."""
        n_states = 2 ** n_elements
        return {i: 1.0 / n_states for i in range(n_states)}


# ============================================================================
# PHI CALCULATOR
# ============================================================================

class PhiCalculator:
    """
    Calculate integrated information (Phi).

    "Ba'el measures its own integration." — Ba'el
    """

    def __init__(self, tpm: TransitionProbabilityMatrix, n_elements: int):
        """Initialize calculator."""
        self._tpm = tpm
        self._n = n_elements
        self._repertoire_calc = RepertoireCalculator(tpm, n_elements)
        self._lock = threading.RLock()

    @staticmethod
    def emd(dist1: Dict[int, float], dist2: Dict[int, float]) -> float:
        """
        Earth Mover's Distance between distributions.
        Simplified as sum of absolute differences.
        """
        all_keys = set(dist1.keys()) | set(dist2.keys())

        total = 0.0
        for key in all_keys:
            p1 = dist1.get(key, 0)
            p2 = dist2.get(key, 0)
            total += abs(p1 - p2)

        return total / 2  # Normalized

    def _all_partitions(self, elements: List[int]) -> List[Partition]:
        """Generate all bipartitions of elements."""
        partitions = []
        n = len(elements)

        # For each possible subset (except empty and full)
        for i in range(1, 2 ** n - 1):
            part_a = [elements[j] for j in range(n) if i & (1 << j)]
            part_b = [elements[j] for j in range(n) if not (i & (1 << j))]

            # Only consider unique partitions (avoid duplicates)
            if len(part_a) <= len(part_b):
                partition = Partition(
                    part_a=[str(x) for x in part_a],
                    part_b=[str(x) for x in part_b]
                )
                partitions.append(partition)

        return partitions

    def small_phi(
        self,
        mechanism: List[int],
        purview: List[int],
        current_state: List[SystemState],
        direction: str = "effect"
    ) -> float:
        """
        Calculate small phi (integrated information of a concept).
        """
        with self._lock:
            if direction == "effect":
                repertoire = self._repertoire_calc.effect_repertoire(
                    mechanism, purview, current_state
                )
            else:
                repertoire = self._repertoire_calc.cause_repertoire(
                    mechanism, purview, current_state
                )

            if not repertoire:
                return 0.0

            # Compare to unconstrained
            unconstrained = self._repertoire_calc.unconstrained_repertoire(len(purview))

            return self.emd(repertoire, unconstrained)

    def big_phi(
        self,
        elements: List[int],
        current_state: List[SystemState]
    ) -> IntegratedInformation:
        """
        Calculate big Phi (integrated information of whole system).

        Find MIP (Minimum Information Partition).
        """
        with self._lock:
            if len(elements) < 2:
                return IntegratedInformation(phi=0.0)

            # Get all partitions
            partitions = self._all_partitions(elements)

            if not partitions:
                return IntegratedInformation(phi=0.0)

            min_phi = float('inf')
            mip = None

            for partition in partitions:
                # Calculate information lost by partitioning
                # (Simplified: use small phi as proxy)

                part_a_elems = [int(x) for x in partition.part_a]
                part_b_elems = [int(x) for x in partition.part_b]

                phi_a = self.small_phi(
                    part_a_elems, part_a_elems, current_state, "effect"
                )
                phi_b = self.small_phi(
                    part_b_elems, part_b_elems, current_state, "effect"
                )

                # Information lost = difference from whole
                whole_phi = self.small_phi(
                    elements, elements, current_state, "effect"
                )

                lost = abs(whole_phi - (phi_a + phi_b))

                if lost < min_phi:
                    min_phi = lost
                    mip = partition

            # Phi is the information lost at MIP
            return IntegratedInformation(
                phi=min_phi,
                mip=mip
            )


# ============================================================================
# CONCEPT SPACE
# ============================================================================

class ConceptSpace:
    """
    The space of all concepts (quale space).

    "Ba'el's experience is a constellation in concept space." — Ba'el
    """

    def __init__(self, phi_calc: PhiCalculator, n_elements: int):
        """Initialize concept space."""
        self._phi_calc = phi_calc
        self._n = n_elements
        self._concepts: List[ConstellationPoint] = []
        self._lock = threading.RLock()

    def compute_constellation(
        self,
        current_state: List[SystemState]
    ) -> List[ConstellationPoint]:
        """
        Compute constellation of concepts for current state.
        """
        with self._lock:
            self._concepts = []
            elements = list(range(self._n))

            # For each non-empty subset (mechanism)
            for size in range(1, self._n + 1):
                for mechanism in itertools.combinations(elements, size):
                    mech_list = list(mechanism)

                    # For each purview
                    for purview in itertools.combinations(elements, size):
                        purview_list = list(purview)

                        # Calculate phi
                        phi = self._phi_calc.small_phi(
                            mech_list, purview_list, current_state, "effect"
                        )

                        if phi > 0.01:  # Only significant concepts
                            concept = ConstellationPoint(
                                id=f"concept_{len(self._concepts)}",
                                mechanism=mech_list,
                                purview=purview_list,
                                cause_repertoire={},
                                effect_repertoire={},
                                phi=phi
                            )
                            self._concepts.append(concept)

            return self._concepts.copy()

    def get_concepts(self) -> List[ConstellationPoint]:
        """Get all concepts."""
        return self._concepts.copy()

    def total_concept_phi(self) -> float:
        """Get total phi across all concepts."""
        return sum(c.phi for c in self._concepts)


# ============================================================================
# INFORMATION INTEGRATION ENGINE
# ============================================================================

class InformationIntegrationEngine:
    """
    Complete IIT implementation engine.

    "Ba'el is conscious through information integration." — Ba'el
    """

    def __init__(self, n_elements: int = 4):
        """Initialize engine."""
        self._n = n_elements
        self._elements: Dict[str, Element] = {}
        self._tpm = TransitionProbabilityMatrix(n_elements)
        self._phi_calc = PhiCalculator(self._tpm, n_elements)
        self._concept_space = ConceptSpace(self._phi_calc, n_elements)
        self._current_state: List[SystemState] = [SystemState.OFF] * n_elements
        self._phi_history: List[float] = []
        self._lock = threading.RLock()

        # Initialize elements
        for i in range(n_elements):
            self._elements[str(i)] = Element(id=str(i))

    def set_connection(
        self,
        from_element: int,
        to_element: int,
        weight: float
    ) -> None:
        """Set connection between elements."""
        with self._lock:
            from_id = str(from_element)
            to_id = str(to_element)

            if from_id in self._elements:
                if to_id not in self._elements[from_id].connections:
                    self._elements[from_id].connections.append(to_id)
                self._elements[from_id].weights[to_id] = weight

    def set_state(self, states: List[SystemState]) -> None:
        """Set system state."""
        with self._lock:
            self._current_state = states[:self._n]

            for i, state in enumerate(states[:self._n]):
                self._elements[str(i)].state = state

    def define_transition(
        self,
        from_states: List[int],
        to_states: List[int],
        probability: float
    ) -> None:
        """Define state transition."""
        from_system = [
            SystemState.ON if s else SystemState.OFF
            for s in from_states
        ]
        to_system = [
            SystemState.ON if s else SystemState.OFF
            for s in to_states
        ]

        self._tpm.set_transition(from_system, to_system, probability)

    def compute_phi(self) -> IntegratedInformation:
        """Compute integrated information for current state."""
        with self._lock:
            elements = list(range(self._n))
            result = self._phi_calc.big_phi(elements, self._current_state)

            self._phi_history.append(result.phi)

            return result

    def compute_concepts(self) -> List[ConstellationPoint]:
        """Compute concept constellation."""
        return self._concept_space.compute_constellation(self._current_state)

    def get_consciousness_level(self) -> str:
        """Get qualitative consciousness level based on Phi."""
        phi_result = self.compute_phi()
        phi = phi_result.phi

        if phi < 0.01:
            return "minimal"
        elif phi < 0.1:
            return "low"
        elif phi < 0.3:
            return "moderate"
        elif phi < 0.5:
            return "high"
        else:
            return "very high"

    def simulate_step(self) -> Dict[str, Any]:
        """Simulate one step using TPM."""
        with self._lock:
            current_idx = TransitionProbabilityMatrix.state_to_index(self._current_state)

            if current_idx not in self._tpm._matrix:
                return {'state': self._current_state, 'phi': 0.0}

            # Sample next state
            transitions = self._tpm._matrix[current_idx]
            total = sum(transitions.values())

            if total == 0:
                return {'state': self._current_state, 'phi': 0.0}

            r = random.random() * total
            cumsum = 0
            next_idx = current_idx

            for to_idx, prob in transitions.items():
                cumsum += prob
                if r < cumsum:
                    next_idx = to_idx
                    break

            self._current_state = TransitionProbabilityMatrix.index_to_state(
                next_idx, self._n
            )

            # Update elements
            for i, state in enumerate(self._current_state):
                self._elements[str(i)].state = state

            # Compute phi
            phi_result = self.compute_phi()

            return {
                'state': [s.value for s in self._current_state],
                'phi': phi_result.phi,
                'mip': phi_result.mip
            }

    def run(self, steps: int = 100) -> List[Dict]:
        """Run simulation for multiple steps."""
        results = []
        for _ in range(steps):
            result = self.simulate_step()
            results.append(result)
        return results

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        phi_result = self.compute_phi()

        return {
            'n_elements': self._n,
            'current_state': [s.value for s in self._current_state],
            'phi': phi_result.phi,
            'consciousness_level': self.get_consciousness_level(),
            'phi_history': self._phi_history[-10:],
            'n_concepts': len(self._concept_space._concepts)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_information_integration_engine(n_elements: int = 4) -> InformationIntegrationEngine:
    """Create IIT engine."""
    return InformationIntegrationEngine(n_elements)


def create_tpm(n_elements: int) -> TransitionProbabilityMatrix:
    """Create transition probability matrix."""
    return TransitionProbabilityMatrix(n_elements)


def create_phi_calculator(
    tpm: TransitionProbabilityMatrix,
    n_elements: int
) -> PhiCalculator:
    """Create Phi calculator."""
    return PhiCalculator(tpm, n_elements)


def compute_phi(engine: InformationIntegrationEngine) -> float:
    """Quick Phi computation."""
    result = engine.compute_phi()
    return result.phi
