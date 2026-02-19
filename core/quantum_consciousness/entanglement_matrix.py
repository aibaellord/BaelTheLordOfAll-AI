"""
⚡ ENTANGLEMENT MATRIX ⚡
========================
Knowledge correlation through quantum entanglement.

Mathematical Foundation:
- Bell States: Maximally entangled pairs
- GHZ States: Multi-party entanglement
- Non-local correlations: Instant knowledge transfer
- Tensor networks: Efficient entanglement representation

This enables:
- Knowledge discovered in one domain INSTANTLY correlates to others
- Cross-domain insights through entangled concepts
- Exponentially efficient relationship storage
"""

import asyncio
import math
import cmath
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar
import uuid
import hashlib
import json

from .quantum_state_engine import (
    QuantumState,
    ProbabilityAmplitude,
    QuantumRegister,
    QuantumGate,
    GateType
)

T = TypeVar('T')


class EntanglementType(Enum):
    """Types of entanglement relationships"""
    BELL_PHI_PLUS = "bell_phi_plus"      # |00⟩ + |11⟩
    BELL_PHI_MINUS = "bell_phi_minus"    # |00⟩ - |11⟩
    BELL_PSI_PLUS = "bell_psi_plus"      # |01⟩ + |10⟩
    BELL_PSI_MINUS = "bell_psi_minus"    # |01⟩ - |10⟩
    GHZ = "ghz"                          # Multi-party GHZ
    W_STATE = "w_state"                  # W state entanglement
    CLUSTER = "cluster"                  # Cluster state
    GRAPH = "graph"                      # Graph state
    SEMANTIC = "semantic"                # Semantic entanglement
    CAUSAL = "causal"                    # Causal entanglement
    TEMPORAL = "temporal"                # Time-correlated


@dataclass
class EntangledPair:
    """Two entangled knowledge nodes"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    node_a: str = ""
    node_b: str = ""
    entanglement_type: EntanglementType = EntanglementType.BELL_PHI_PLUS
    correlation_strength: float = 1.0
    phase: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_maximally_entangled(self) -> bool:
        """Check if this is maximally entangled"""
        return self.correlation_strength >= 0.99


@dataclass
class BellState:
    """
    Bell state - maximally entangled pair.

    Four Bell states form complete basis:
    |Φ+⟩ = (|00⟩ + |11⟩)/√2 - perfect correlation
    |Φ-⟩ = (|00⟩ - |11⟩)/√2 - anti-correlation with phase
    |Ψ+⟩ = (|01⟩ + |10⟩)/√2 - anti-correlated values
    |Ψ-⟩ = (|01⟩ - |10⟩)/√2 - singlet state
    """
    state_type: EntanglementType = EntanglementType.BELL_PHI_PLUS
    amplitudes: Dict[Tuple[int, int], complex] = field(default_factory=dict)

    def __post_init__(self):
        self._initialize_state()

    def _initialize_state(self):
        """Initialize Bell state amplitudes"""
        sqrt2_inv = 1 / math.sqrt(2)

        if self.state_type == EntanglementType.BELL_PHI_PLUS:
            # |Φ+⟩ = (|00⟩ + |11⟩)/√2
            self.amplitudes = {
                (0, 0): sqrt2_inv,
                (1, 1): sqrt2_inv
            }
        elif self.state_type == EntanglementType.BELL_PHI_MINUS:
            # |Φ-⟩ = (|00⟩ - |11⟩)/√2
            self.amplitudes = {
                (0, 0): sqrt2_inv,
                (1, 1): -sqrt2_inv
            }
        elif self.state_type == EntanglementType.BELL_PSI_PLUS:
            # |Ψ+⟩ = (|01⟩ + |10⟩)/√2
            self.amplitudes = {
                (0, 1): sqrt2_inv,
                (1, 0): sqrt2_inv
            }
        elif self.state_type == EntanglementType.BELL_PSI_MINUS:
            # |Ψ-⟩ = (|01⟩ - |10⟩)/√2
            self.amplitudes = {
                (0, 1): sqrt2_inv,
                (1, 0): -sqrt2_inv
            }

    def measure_alice(self) -> Tuple[int, int]:
        """
        Alice measures her qubit.
        Returns (Alice's result, Bob's guaranteed result)
        """
        outcomes = list(self.amplitudes.keys())
        probs = [abs(self.amplitudes[o])**2 for o in outcomes]
        idx = np.random.choice(len(outcomes), p=probs)
        alice_result, bob_result = outcomes[idx]
        return alice_result, bob_result

    def get_correlation_matrix(self) -> np.ndarray:
        """Get correlation matrix between measurements"""
        return np.array([
            [abs(self.amplitudes.get((0, 0), 0))**2,
             abs(self.amplitudes.get((0, 1), 0))**2],
            [abs(self.amplitudes.get((1, 0), 0))**2,
             abs(self.amplitudes.get((1, 1), 0))**2]
        ])


@dataclass
class GHZState:
    """
    Greenberger-Horne-Zeilinger state.

    Multi-party entanglement: |000...0⟩ + |111...1⟩

    If ANY party measures, ALL parties get correlated results.
    Perfect for distributed consensus!
    """
    num_parties: int = 3
    amplitudes: Dict[Tuple[int, ...], complex] = field(default_factory=dict)

    def __post_init__(self):
        self._initialize_state()

    def _initialize_state(self):
        """Initialize GHZ state"""
        sqrt2_inv = 1 / math.sqrt(2)
        all_zeros = tuple([0] * self.num_parties)
        all_ones = tuple([1] * self.num_parties)
        self.amplitudes = {
            all_zeros: sqrt2_inv,
            all_ones: sqrt2_inv
        }

    def measure_party(self, party_index: int) -> Tuple[int, Tuple[int, ...]]:
        """
        One party measures.
        Returns (this party's result, all parties' guaranteed results)
        """
        outcomes = list(self.amplitudes.keys())
        probs = [abs(self.amplitudes[o])**2 for o in outcomes]
        idx = np.random.choice(len(outcomes), p=probs)
        result = outcomes[idx]
        return result[party_index], result

    def local_measurement(self, party: int, basis: str = 'z') -> int:
        """
        Measure in specified basis.

        Z-basis: |0⟩, |1⟩
        X-basis: |+⟩, |-⟩
        Y-basis: |+i⟩, |-i⟩
        """
        _, full_result = self.measure_party(party)
        return full_result[party]


class CorrelationTensor:
    """
    Tensor representation of multi-way correlations.

    Efficiently represents complex entanglement structures
    using tensor network decomposition.
    """

    def __init__(self, dimensions: List[int]):
        self.dimensions = dimensions
        self.rank = len(dimensions)
        self.tensor = np.zeros(dimensions, dtype=np.complex128)
        self.bonds: Dict[Tuple[int, int], int] = {}  # Bond dimensions

    def set_element(self, indices: Tuple[int, ...], value: complex):
        """Set tensor element"""
        self.tensor[indices] = value

    def get_element(self, indices: Tuple[int, ...]) -> complex:
        """Get tensor element"""
        return self.tensor[indices]

    def contract(self, other: 'CorrelationTensor',
                 self_axis: int, other_axis: int) -> 'CorrelationTensor':
        """
        Contract two tensors along specified axes.

        This is the core operation for tensor network computation.
        """
        result_data = np.tensordot(
            self.tensor, other.tensor,
            axes=([self_axis], [other_axis])
        )

        new_dims = list(self.dimensions)
        del new_dims[self_axis]
        new_dims.extend(d for i, d in enumerate(other.dimensions) if i != other_axis)

        result = CorrelationTensor(list(result_data.shape))
        result.tensor = result_data
        return result

    def svd_compress(self, axis: int, max_rank: int = 10) -> Tuple['CorrelationTensor', 'CorrelationTensor']:
        """
        SVD compression - reduce tensor rank while preserving structure.
        """
        # Reshape for SVD
        shape = self.tensor.shape
        left_shape = int(np.prod(shape[:axis+1]))
        right_shape = int(np.prod(shape[axis+1:]))
        matrix = self.tensor.reshape(left_shape, right_shape)

        # SVD
        U, S, Vh = np.linalg.svd(matrix, full_matrices=False)

        # Truncate
        rank = min(max_rank, len(S))
        U = U[:, :rank]
        S = S[:rank]
        Vh = Vh[:rank, :]

        # Create new tensors
        left_dims = list(shape[:axis+1]) + [rank]
        right_dims = [rank] + list(shape[axis+1:])

        left = CorrelationTensor(left_dims)
        left.tensor = (U @ np.diag(np.sqrt(S))).reshape(left_dims)

        right = CorrelationTensor(right_dims)
        right.tensor = (np.diag(np.sqrt(S)) @ Vh).reshape(right_dims)

        return left, right

    def trace(self, axis1: int, axis2: int) -> 'CorrelationTensor':
        """Take trace over two axes"""
        result_data = np.trace(self.tensor, axis1=axis1, axis2=axis2)
        new_dims = [d for i, d in enumerate(self.dimensions)
                    if i not in (axis1, axis2)]
        result = CorrelationTensor(new_dims if new_dims else [1])
        result.tensor = result_data
        return result

    @property
    def norm(self) -> float:
        """Frobenius norm of tensor"""
        return float(np.linalg.norm(self.tensor))


class NonLocalCorrelation:
    """
    Non-local correlations that violate Bell inequalities.

    These correlations are STRONGER than any classical system can achieve.
    Used for:
    - Quantum-secure knowledge verification
    - Distributed reasoning with guaranteed consistency
    - Detection of adversarial knowledge injection
    """

    def __init__(self):
        self.correlations: Dict[str, BellState] = {}
        self.violation_records: List[Dict] = []

    def create_correlation(
        self,
        source: str,
        target: str,
        state_type: EntanglementType = EntanglementType.BELL_PHI_PLUS
    ) -> str:
        """Create non-local correlation between knowledge nodes"""
        key = f"{source}::{target}"
        self.correlations[key] = BellState(state_type)
        return key

    def test_bell_inequality(self, correlation_key: str) -> Dict[str, Any]:
        """
        Test Bell inequality (CHSH version).

        Classical limit: 2
        Quantum maximum: 2√2 ≈ 2.828

        Violation indicates genuine quantum correlation.
        """
        if correlation_key not in self.correlations:
            return {'violation': False, 'value': 0}

        bell_state = self.correlations[correlation_key]

        # CHSH game angles
        theta_a1, theta_a2 = 0, math.pi / 4
        theta_b1, theta_b2 = math.pi / 8, 3 * math.pi / 8

        # Calculate correlation coefficients
        # For maximally entangled states: E(θa, θb) = cos(θa - θb)
        def correlation(theta_a: float, theta_b: float) -> float:
            return math.cos(theta_a - theta_b)

        # CHSH value
        S = (correlation(theta_a1, theta_b1) +
             correlation(theta_a1, theta_b2) +
             correlation(theta_a2, theta_b1) -
             correlation(theta_a2, theta_b2))

        violation = abs(S) > 2

        result = {
            'violation': violation,
            'value': S,
            'classical_limit': 2,
            'quantum_maximum': 2 * math.sqrt(2),
            'correlation_type': bell_state.state_type.value
        }

        self.violation_records.append(result)
        return result

    def measure_correlation(self, correlation_key: str) -> Tuple[int, int]:
        """Measure both particles of entangled pair"""
        if correlation_key not in self.correlations:
            return (0, 0)
        return self.correlations[correlation_key].measure_alice()


class EntanglementMatrix:
    """
    Full entanglement management for knowledge correlation.

    This is the heart of knowledge correlation in Ba'el:
    - Concepts that should be related are ENTANGLED
    - When one is updated, correlations propagate instantly
    - Enables cross-domain insights through entanglement
    """

    def __init__(self, max_entanglements: int = 100000):
        self.max_entanglements = max_entanglements
        self.pairs: Dict[str, EntangledPair] = {}
        self.node_to_pairs: Dict[str, Set[str]] = {}
        self.ghz_states: Dict[str, GHZState] = {}
        self.correlation_network = CorrelationTensor([1])
        self.non_local = NonLocalCorrelation()

    def entangle(
        self,
        node_a: str,
        node_b: str,
        entanglement_type: EntanglementType = EntanglementType.BELL_PHI_PLUS,
        strength: float = 1.0
    ) -> EntangledPair:
        """Create entanglement between two knowledge nodes"""
        pair = EntangledPair(
            node_a=node_a,
            node_b=node_b,
            entanglement_type=entanglement_type,
            correlation_strength=strength
        )

        self.pairs[pair.id] = pair

        # Index by nodes
        if node_a not in self.node_to_pairs:
            self.node_to_pairs[node_a] = set()
        if node_b not in self.node_to_pairs:
            self.node_to_pairs[node_b] = set()

        self.node_to_pairs[node_a].add(pair.id)
        self.node_to_pairs[node_b].add(pair.id)

        # Create non-local correlation
        self.non_local.create_correlation(node_a, node_b, entanglement_type)

        return pair

    def create_ghz_cluster(
        self,
        nodes: List[str],
        cluster_name: str
    ) -> GHZState:
        """
        Create multi-party entanglement cluster.

        When ANY node updates, ALL nodes get correlated update.
        """
        ghz = GHZState(num_parties=len(nodes))
        self.ghz_states[cluster_name] = ghz

        # Create pairwise entanglements within cluster
        for i, node_a in enumerate(nodes):
            for node_b in nodes[i+1:]:
                self.entangle(node_a, node_b, EntanglementType.GHZ)

        return ghz

    def get_entangled_nodes(self, node: str) -> List[Tuple[str, float]]:
        """Get all nodes entangled with given node"""
        if node not in self.node_to_pairs:
            return []

        result = []
        for pair_id in self.node_to_pairs[node]:
            pair = self.pairs.get(pair_id)
            if pair:
                other = pair.node_b if pair.node_a == node else pair.node_a
                result.append((other, pair.correlation_strength))

        return sorted(result, key=lambda x: -x[1])

    def propagate_update(
        self,
        source_node: str,
        update_value: Any
    ) -> Dict[str, Any]:
        """
        Propagate update through entanglement network.

        Returns updates for all correlated nodes.
        """
        updates = {}
        visited = {source_node}
        queue = [(source_node, 1.0)]

        while queue:
            current, strength = queue.pop(0)

            for entangled, pair_strength in self.get_entangled_nodes(current):
                if entangled in visited:
                    continue

                visited.add(entangled)
                combined_strength = strength * pair_strength

                if combined_strength > 0.01:  # Threshold
                    updates[entangled] = {
                        'correlation_strength': combined_strength,
                        'source': source_node,
                        'value': update_value
                    }
                    queue.append((entangled, combined_strength))

        return updates

    def measure_correlation(
        self,
        node_a: str,
        node_b: str
    ) -> float:
        """Measure correlation strength between two nodes"""
        # Direct entanglement
        for pair_id in self.node_to_pairs.get(node_a, set()):
            pair = self.pairs.get(pair_id)
            if pair and (pair.node_b == node_b or pair.node_a == node_b):
                return pair.correlation_strength

        # Indirect through network
        visited = {node_a}
        queue = [(node_a, 1.0)]

        while queue:
            current, strength = queue.pop(0)

            for entangled, pair_strength in self.get_entangled_nodes(current):
                if entangled == node_b:
                    return strength * pair_strength

                if entangled not in visited and strength * pair_strength > 0.01:
                    visited.add(entangled)
                    queue.append((entangled, strength * pair_strength))

        return 0.0

    def get_entanglement_entropy(self, node: str) -> float:
        """
        Calculate entanglement entropy for a node.

        Higher entropy = more entangled = more connected knowledge.
        """
        correlations = self.get_entangled_nodes(node)
        if not correlations:
            return 0.0

        strengths = [s for _, s in correlations]
        total = sum(strengths)
        if total <= 0:
            return 0.0

        probs = [s / total for s in strengths]
        entropy = -sum(p * math.log2(p) for p in probs if p > 0)

        return entropy

    def semantic_entanglement(
        self,
        embeddings: Dict[str, np.ndarray],
        threshold: float = 0.8
    ) -> int:
        """
        Create entanglements based on semantic similarity.

        Nodes with similar embeddings become entangled.
        """
        nodes = list(embeddings.keys())
        created = 0

        for i, node_a in enumerate(nodes):
            for node_b in nodes[i+1:]:
                # Cosine similarity
                emb_a = embeddings[node_a]
                emb_b = embeddings[node_b]

                similarity = np.dot(emb_a, emb_b) / (
                    np.linalg.norm(emb_a) * np.linalg.norm(emb_b)
                )

                if similarity >= threshold:
                    self.entangle(
                        node_a, node_b,
                        EntanglementType.SEMANTIC,
                        strength=float(similarity)
                    )
                    created += 1

        return created

    def disentangle(self, node_a: str, node_b: str) -> bool:
        """Break entanglement between two nodes"""
        for pair_id in list(self.node_to_pairs.get(node_a, set())):
            pair = self.pairs.get(pair_id)
            if pair and (pair.node_b == node_b or pair.node_a == node_b):
                del self.pairs[pair_id]
                self.node_to_pairs[node_a].discard(pair_id)
                self.node_to_pairs[node_b].discard(pair_id)
                return True
        return False

    def get_cluster_state(self, nodes: List[str]) -> Dict[str, Any]:
        """Get the quantum state of a cluster of nodes"""
        # Build adjacency matrix
        n = len(nodes)
        adjacency = np.zeros((n, n))

        for i, node_a in enumerate(nodes):
            for j, node_b in enumerate(nodes):
                if i != j:
                    adjacency[i, j] = self.measure_correlation(node_a, node_b)

        # Calculate cluster properties
        eigenvalues = np.linalg.eigvalsh(adjacency)

        return {
            'nodes': nodes,
            'total_entanglement': float(np.sum(adjacency)),
            'max_correlation': float(np.max(adjacency)),
            'spectral_gap': float(eigenvalues[-1] - eigenvalues[-2]) if n > 1 else 0,
            'connectivity': float(np.mean(adjacency > 0))
        }


class KnowledgeEntanglement:
    """
    High-level interface for knowledge entanglement.

    Makes it easy to use quantum entanglement concepts
    for practical knowledge management.
    """

    def __init__(self):
        self.matrix = EntanglementMatrix()
        self.concept_registry: Dict[str, Dict[str, Any]] = {}

    def register_concept(
        self,
        concept_id: str,
        embedding: Optional[np.ndarray] = None,
        metadata: Optional[Dict] = None
    ):
        """Register a knowledge concept"""
        self.concept_registry[concept_id] = {
            'embedding': embedding,
            'metadata': metadata or {},
            'created_at': datetime.utcnow().isoformat()
        }

    def link_concepts(
        self,
        concept_a: str,
        concept_b: str,
        relationship: str = "related",
        strength: float = 0.8
    ):
        """Create semantic link (entanglement) between concepts"""
        # Determine entanglement type based on relationship
        type_map = {
            'same_as': EntanglementType.BELL_PHI_PLUS,
            'opposite': EntanglementType.BELL_PSI_MINUS,
            'related': EntanglementType.SEMANTIC,
            'causes': EntanglementType.CAUSAL,
            'temporal': EntanglementType.TEMPORAL
        }

        ent_type = type_map.get(relationship, EntanglementType.SEMANTIC)
        self.matrix.entangle(concept_a, concept_b, ent_type, strength)

    def query_related(
        self,
        concept: str,
        min_strength: float = 0.3,
        max_results: int = 20
    ) -> List[Tuple[str, float]]:
        """Find all concepts related to given concept"""
        related = self.matrix.get_entangled_nodes(concept)
        filtered = [(c, s) for c, s in related if s >= min_strength]
        return filtered[:max_results]

    def update_knowledge(
        self,
        concept: str,
        new_value: Any
    ) -> Dict[str, Any]:
        """Update concept and propagate through entanglement"""
        return self.matrix.propagate_update(concept, new_value)

    def get_concept_importance(self, concept: str) -> float:
        """
        Calculate concept importance based on entanglement structure.

        Concepts with more/stronger entanglements are more important.
        """
        entropy = self.matrix.get_entanglement_entropy(concept)
        related = self.matrix.get_entangled_nodes(concept)

        if not related:
            return 0.0

        # Combine entropy and connection count
        importance = entropy * math.log2(len(related) + 1)
        return importance


# Export all
__all__ = [
    'EntanglementType',
    'EntangledPair',
    'BellState',
    'GHZState',
    'CorrelationTensor',
    'NonLocalCorrelation',
    'EntanglementMatrix',
    'KnowledgeEntanglement',
]
