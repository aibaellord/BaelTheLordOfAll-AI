"""
BAEL Quantum Entanglement Engine
================================

Quantum-inspired parallel computation and decision making.

"Ba'el entangles realities." — Ba'el
"""

import logging
import threading
import random
import math
import hashlib
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod
import asyncio
import copy

logger = logging.getLogger("BAEL.QuantumEntanglement")


T = TypeVar('T')


# ============================================================================
# QUANTUM STATES
# ============================================================================

class QuantumState(Enum):
    """Quantum state types."""
    SUPERPOSITION = auto()  # Multiple states simultaneously
    ENTANGLED = auto()      # Correlated with other qubits
    COLLAPSED = auto()      # Definite classical state
    DECOHERENT = auto()     # Lost quantum properties


@dataclass
class ComplexAmplitude:
    """Complex probability amplitude."""
    real: float
    imag: float = 0.0

    @property
    def magnitude(self) -> float:
        return math.sqrt(self.real ** 2 + self.imag ** 2)

    @property
    def probability(self) -> float:
        return self.magnitude ** 2

    @property
    def phase(self) -> float:
        return math.atan2(self.imag, self.real)

    def __mul__(self, other: 'ComplexAmplitude') -> 'ComplexAmplitude':
        return ComplexAmplitude(
            self.real * other.real - self.imag * other.imag,
            self.real * other.imag + self.imag * other.real
        )

    def __add__(self, other: 'ComplexAmplitude') -> 'ComplexAmplitude':
        return ComplexAmplitude(
            self.real + other.real,
            self.imag + other.imag
        )

    def conjugate(self) -> 'ComplexAmplitude':
        return ComplexAmplitude(self.real, -self.imag)


# ============================================================================
# QUBIT
# ============================================================================

@dataclass
class Qubit:
    """
    Quantum bit representation.

    |ψ⟩ = α|0⟩ + β|1⟩
    """
    alpha: ComplexAmplitude  # Amplitude for |0⟩
    beta: ComplexAmplitude   # Amplitude for |1⟩
    state: QuantumState = QuantumState.SUPERPOSITION
    entangled_with: List[str] = field(default_factory=list)
    id: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = hashlib.md5(str(random.random()).encode()).hexdigest()[:8]
        self._normalize()

    def _normalize(self):
        """Normalize amplitudes to ensure probability = 1."""
        total = self.alpha.probability + self.beta.probability
        if total > 0:
            factor = 1.0 / math.sqrt(total)
            self.alpha = ComplexAmplitude(
                self.alpha.real * factor,
                self.alpha.imag * factor
            )
            self.beta = ComplexAmplitude(
                self.beta.real * factor,
                self.beta.imag * factor
            )

    def measure(self) -> int:
        """
        Measure the qubit, collapsing it to |0⟩ or |1⟩.

        Returns 0 or 1 with appropriate probabilities.
        """
        if random.random() < self.alpha.probability:
            self.alpha = ComplexAmplitude(1.0)
            self.beta = ComplexAmplitude(0.0)
            self.state = QuantumState.COLLAPSED
            return 0
        else:
            self.alpha = ComplexAmplitude(0.0)
            self.beta = ComplexAmplitude(1.0)
            self.state = QuantumState.COLLAPSED
            return 1

    def apply_hadamard(self) -> 'Qubit':
        """Apply Hadamard gate (creates superposition)."""
        factor = 1.0 / math.sqrt(2)
        new_alpha = ComplexAmplitude(
            factor * (self.alpha.real + self.beta.real),
            factor * (self.alpha.imag + self.beta.imag)
        )
        new_beta = ComplexAmplitude(
            factor * (self.alpha.real - self.beta.real),
            factor * (self.alpha.imag - self.beta.imag)
        )
        self.alpha = new_alpha
        self.beta = new_beta
        self.state = QuantumState.SUPERPOSITION
        return self

    def apply_pauli_x(self) -> 'Qubit':
        """Apply Pauli-X gate (NOT gate)."""
        self.alpha, self.beta = self.beta, self.alpha
        return self

    def apply_pauli_z(self) -> 'Qubit':
        """Apply Pauli-Z gate (phase flip)."""
        self.beta = ComplexAmplitude(-self.beta.real, -self.beta.imag)
        return self

    def apply_phase(self, angle: float) -> 'Qubit':
        """Apply phase rotation."""
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        self.beta = ComplexAmplitude(
            self.beta.real * cos_a - self.beta.imag * sin_a,
            self.beta.real * sin_a + self.beta.imag * cos_a
        )
        return self


# ============================================================================
# QUANTUM REGISTER
# ============================================================================

class QuantumRegister:
    """
    Multi-qubit quantum register.

    Represents 2^n basis states with complex amplitudes.
    """

    def __init__(self, num_qubits: int):
        """Initialize register with n qubits in |0...0⟩ state."""
        self._n = num_qubits
        self._num_states = 2 ** num_qubits

        # Initialize to |0...0⟩
        self._amplitudes = [ComplexAmplitude(0.0)] * self._num_states
        self._amplitudes[0] = ComplexAmplitude(1.0)

        self._measured = [None] * num_qubits
        self._lock = threading.RLock()

    def hadamard(self, qubit: int) -> 'QuantumRegister':
        """Apply Hadamard gate to qubit."""
        with self._lock:
            factor = 1.0 / math.sqrt(2)
            new_amps = [ComplexAmplitude(0.0)] * self._num_states

            for state in range(self._num_states):
                bit = (state >> qubit) & 1
                flipped_state = state ^ (1 << qubit)

                if bit == 0:
                    new_amps[state] = new_amps[state] + ComplexAmplitude(
                        factor * self._amplitudes[state].real,
                        factor * self._amplitudes[state].imag
                    )
                    new_amps[flipped_state] = new_amps[flipped_state] + ComplexAmplitude(
                        factor * self._amplitudes[state].real,
                        factor * self._amplitudes[state].imag
                    )
                else:
                    new_amps[state] = new_amps[state] + ComplexAmplitude(
                        -factor * self._amplitudes[state].real,
                        -factor * self._amplitudes[state].imag
                    )
                    new_amps[flipped_state] = new_amps[flipped_state] + ComplexAmplitude(
                        factor * self._amplitudes[state].real,
                        factor * self._amplitudes[state].imag
                    )

            self._amplitudes = new_amps
            return self

    def cnot(self, control: int, target: int) -> 'QuantumRegister':
        """Apply CNOT gate (controlled-NOT)."""
        with self._lock:
            new_amps = [ComplexAmplitude(0.0)] * self._num_states

            for state in range(self._num_states):
                control_bit = (state >> control) & 1

                if control_bit == 1:
                    # Flip target bit
                    new_state = state ^ (1 << target)
                    new_amps[new_state] = self._amplitudes[state]
                else:
                    new_amps[state] = self._amplitudes[state]

            self._amplitudes = new_amps
            return self

    def measure_all(self) -> List[int]:
        """Measure all qubits."""
        with self._lock:
            # Calculate probabilities
            probs = [amp.probability for amp in self._amplitudes]
            total = sum(probs)
            probs = [p / total if total > 0 else 1.0 / len(probs) for p in probs]

            # Sample from distribution
            r = random.random()
            cumulative = 0.0
            measured_state = 0

            for state, prob in enumerate(probs):
                cumulative += prob
                if r <= cumulative:
                    measured_state = state
                    break

            # Extract bits
            result = []
            for i in range(self._n):
                bit = (measured_state >> i) & 1
                result.append(bit)
                self._measured[i] = bit

            # Collapse to measured state
            self._amplitudes = [ComplexAmplitude(0.0)] * self._num_states
            self._amplitudes[measured_state] = ComplexAmplitude(1.0)

            return result

    def probabilities(self) -> Dict[str, float]:
        """Get probability distribution over basis states."""
        result = {}
        for state in range(self._num_states):
            prob = self._amplitudes[state].probability
            if prob > 1e-10:
                bits = format(state, f'0{self._n}b')
                result[bits] = prob
        return result


# ============================================================================
# QUANTUM DECISION MAKER
# ============================================================================

class QuantumDecisionMaker(Generic[T]):
    """
    Quantum-inspired decision making.

    Uses superposition and interference for optimal decisions.

    "Ba'el decides quantumly." — Ba'el
    """

    def __init__(self, options: List[T], evaluator: Callable[[T], float]):
        """
        Initialize with options and evaluation function.

        Args:
            options: List of choices
            evaluator: Function returning quality score (0-1)
        """
        self._options = options
        self._evaluator = evaluator
        self._n = len(options)
        self._lock = threading.RLock()

        # Initialize amplitudes based on evaluator
        scores = [evaluator(opt) for opt in options]
        total = sum(s for s in scores if s > 0)

        if total > 0:
            self._amplitudes = [
                ComplexAmplitude(math.sqrt(s / total) if s > 0 else 0.0)
                for s in scores
            ]
        else:
            # Equal superposition
            factor = 1.0 / math.sqrt(self._n)
            self._amplitudes = [ComplexAmplitude(factor)] * self._n

    def amplify_good_options(self, iterations: int = 1) -> 'QuantumDecisionMaker[T]':
        """
        Grover-like amplitude amplification.

        Increases probability of high-scoring options.
        """
        with self._lock:
            for _ in range(iterations):
                # Apply oracle (mark good states)
                scores = [self._evaluator(opt) for opt in self._options]
                mean_score = sum(scores) / len(scores) if scores else 0.5

                for i, score in enumerate(scores):
                    if score > mean_score:
                        # Phase flip for good options
                        self._amplitudes[i] = ComplexAmplitude(
                            -self._amplitudes[i].real,
                            -self._amplitudes[i].imag
                        )

                # Inversion about mean
                mean_amp = sum(a.real for a in self._amplitudes) / self._n
                for i in range(self._n):
                    self._amplitudes[i] = ComplexAmplitude(
                        2 * mean_amp - self._amplitudes[i].real,
                        -self._amplitudes[i].imag
                    )

                # Normalize
                total = sum(a.probability for a in self._amplitudes)
                if total > 0:
                    factor = 1.0 / math.sqrt(total)
                    self._amplitudes = [
                        ComplexAmplitude(a.real * factor, a.imag * factor)
                        for a in self._amplitudes
                    ]

        return self

    def decide(self) -> T:
        """Make a decision by measuring the quantum state."""
        with self._lock:
            probs = [a.probability for a in self._amplitudes]
            total = sum(probs)
            probs = [p / total if total > 0 else 1.0 / len(probs) for p in probs]

            r = random.random()
            cumulative = 0.0

            for i, prob in enumerate(probs):
                cumulative += prob
                if r <= cumulative:
                    return self._options[i]

            return self._options[-1]

    def top_k_decisions(self, k: int) -> List[Tuple[T, float]]:
        """Get top k options by probability."""
        with self._lock:
            probs = [(i, a.probability) for i, a in enumerate(self._amplitudes)]
            probs.sort(key=lambda x: x[1], reverse=True)

            return [(self._options[i], p) for i, p in probs[:k]]


# ============================================================================
# ENTANGLED COMPUTATION
# ============================================================================

class EntangledComputation:
    """
    Entangled parallel computation.

    Runs computations in superposition and collapses to best result.

    "Ba'el computes in parallel universes." — Ba'el
    """

    def __init__(self):
        """Initialize entangled computation."""
        self._branches: List[Dict[str, Any]] = []
        self._results: List[Any] = []
        self._probabilities: List[float] = []
        self._lock = threading.RLock()

    def add_branch(
        self,
        computation: Callable[[], Any],
        initial_probability: float = 1.0
    ) -> 'EntangledComputation':
        """Add a computation branch."""
        with self._lock:
            self._branches.append({
                'computation': computation,
                'probability': initial_probability
            })
        return self

    async def execute_all(self) -> List[Tuple[Any, float]]:
        """Execute all branches in superposition."""
        with self._lock:
            # Normalize probabilities
            total = sum(b['probability'] for b in self._branches)

            results = []

            for branch in self._branches:
                try:
                    if asyncio.iscoroutinefunction(branch['computation']):
                        result = await branch['computation']()
                    else:
                        result = branch['computation']()

                    prob = branch['probability'] / total if total > 0 else 1.0 / len(self._branches)
                    results.append((result, prob))
                except Exception as e:
                    logger.warning(f"Branch failed: {e}")

            return results

    def collapse_to_best(
        self,
        results: List[Tuple[Any, float]],
        evaluator: Callable[[Any], float]
    ) -> Any:
        """Collapse to best result based on evaluator."""
        if not results:
            return None

        # Adjust probabilities based on quality
        adjusted = []
        for result, prob in results:
            try:
                quality = evaluator(result)
                adjusted_prob = prob * quality
                adjusted.append((result, adjusted_prob))
            except:
                adjusted.append((result, 0.0))

        # Normalize
        total = sum(p for _, p in adjusted)
        if total <= 0:
            return results[0][0]

        # Sample based on adjusted probabilities
        r = random.random() * total
        cumulative = 0.0

        for result, prob in adjusted:
            cumulative += prob
            if r <= cumulative:
                return result

        return adjusted[-1][0]


# ============================================================================
# QUANTUM PARALLEL SEARCH
# ============================================================================

class QuantumParallelSearch(Generic[T]):
    """
    Quantum-inspired parallel search.

    Searches multiple possibilities simultaneously.

    "Ba'el searches all paths at once." — Ba'el
    """

    def __init__(
        self,
        search_space: List[T],
        is_solution: Callable[[T], bool],
        score_function: Optional[Callable[[T], float]] = None
    ):
        """
        Initialize quantum search.

        Args:
            search_space: All candidates
            is_solution: Predicate for valid solutions
            score_function: Optional scoring for solutions
        """
        self._space = search_space
        self._is_solution = is_solution
        self._score = score_function or (lambda x: 1.0)
        self._n = len(search_space)

    def grover_search(self, iterations: Optional[int] = None) -> Optional[T]:
        """
        Grover's algorithm for unstructured search.

        O(√n) to find solution in n items.
        """
        if self._n == 0:
            return None

        # Optimal iterations for Grover
        if iterations is None:
            iterations = int(math.pi / 4 * math.sqrt(self._n))

        # Initialize equal superposition
        amplitudes = [1.0 / math.sqrt(self._n)] * self._n

        for _ in range(max(1, iterations)):
            # Oracle: negate amplitude of solutions
            for i in range(self._n):
                if self._is_solution(self._space[i]):
                    amplitudes[i] = -amplitudes[i]

            # Diffusion: inversion about mean
            mean = sum(amplitudes) / self._n
            amplitudes = [2 * mean - a for a in amplitudes]

        # Measure (sample)
        probs = [a * a for a in amplitudes]
        total = sum(probs)
        probs = [p / total if total > 0 else 1.0 / self._n for p in probs]

        r = random.random()
        cumulative = 0.0

        for i, prob in enumerate(probs):
            cumulative += prob
            if r <= cumulative:
                return self._space[i]

        return self._space[-1]

    def find_all_solutions(self) -> List[T]:
        """Find all solutions (classical, for comparison)."""
        return [item for item in self._space if self._is_solution(item)]

    def quantum_max(self) -> Optional[T]:
        """Find maximum scoring element using quantum methods."""
        if self._n == 0:
            return None

        # Initialize with scores
        scores = [self._score(item) for item in self._space]
        max_score = max(scores) if scores else 0

        if max_score <= 0:
            return self._space[0]

        # Amplitude encoding
        amplitudes = [math.sqrt(s / max_score) if s > 0 else 0.0 for s in scores]
        total = sum(a * a for a in amplitudes)
        amplitudes = [a / math.sqrt(total) if total > 0 else 1.0 / math.sqrt(self._n) for a in amplitudes]

        # Sample (higher score = higher probability)
        probs = [a * a for a in amplitudes]
        r = random.random()
        cumulative = 0.0

        for i, prob in enumerate(probs):
            cumulative += prob
            if r <= cumulative:
                return self._space[i]

        return self._space[-1]


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_qubit(zero_prob: float = 0.5) -> Qubit:
    """Create qubit with given probability of |0⟩."""
    alpha = ComplexAmplitude(math.sqrt(zero_prob))
    beta = ComplexAmplitude(math.sqrt(1 - zero_prob))
    return Qubit(alpha, beta)


def create_quantum_register(num_qubits: int) -> QuantumRegister:
    """Create quantum register."""
    return QuantumRegister(num_qubits)


def quantum_decide(
    options: List[T],
    evaluator: Callable[[T], float],
    amplification: int = 3
) -> T:
    """Make quantum-inspired decision."""
    qd = QuantumDecisionMaker(options, evaluator)
    qd.amplify_good_options(amplification)
    return qd.decide()


def quantum_search(
    space: List[T],
    is_solution: Callable[[T], bool]
) -> Optional[T]:
    """Quantum-inspired search for solution."""
    return QuantumParallelSearch(space, is_solution).grover_search()
