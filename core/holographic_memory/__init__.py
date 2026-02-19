"""
BAEL Holographic Memory Engine
==============================

Holographic associative memory with high-dimensional vectors.

"Ba'el remembers holographically." — Ba'el
"""

import logging
import threading
import random
import math
import hashlib
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar
from dataclasses import dataclass, field
import copy

logger = logging.getLogger("BAEL.HolographicMemory")


T = TypeVar('T')


# ============================================================================
# HOLOGRAPHIC VECTOR
# ============================================================================

@dataclass
class HolographicVector:
    """
    High-dimensional holographic vector.

    Uses bipolar encoding (-1, +1).
    """
    dimensions: List[float]

    @property
    def dim(self) -> int:
        return len(self.dimensions)

    @staticmethod
    def random(dim: int) -> 'HolographicVector':
        """Create random bipolar vector."""
        return HolographicVector([
            1.0 if random.random() > 0.5 else -1.0
            for _ in range(dim)
        ])

    @staticmethod
    def from_text(text: str, dim: int) -> 'HolographicVector':
        """Create deterministic vector from text."""
        # Use hash-based deterministic random
        h = hashlib.sha256(text.encode()).digest()
        random.seed(int.from_bytes(h[:8], 'big'))
        vec = HolographicVector.random(dim)
        random.seed()  # Reset
        return vec

    def normalize(self) -> 'HolographicVector':
        """Normalize to unit length."""
        magnitude = math.sqrt(sum(d * d for d in self.dimensions))
        if magnitude > 0:
            return HolographicVector([d / magnitude for d in self.dimensions])
        return self

    def bind(self, other: 'HolographicVector') -> 'HolographicVector':
        """
        Binding operation (circular convolution).

        Creates association between vectors.
        """
        n = self.dim
        result = [0.0] * n

        for i in range(n):
            for j in range(n):
                k = (i + j) % n
                result[k] += self.dimensions[i] * other.dimensions[j]

        return HolographicVector(result).normalize()

    def unbind(self, other: 'HolographicVector') -> 'HolographicVector':
        """
        Unbinding operation (correlation / approximate inverse).

        Retrieves associated vector.
        """
        # Inverse is the same as bind with permuted other
        n = self.dim
        permuted = [other.dimensions[(-i) % n] for i in range(n)]
        return self.bind(HolographicVector(permuted))

    def bundle(self, *others: 'HolographicVector') -> 'HolographicVector':
        """
        Bundling operation (superposition).

        Creates composite representation.
        """
        result = list(self.dimensions)
        for other in others:
            for i in range(self.dim):
                result[i] += other.dimensions[i]
        return HolographicVector(result).normalize()

    def permute(self, shift: int = 1) -> 'HolographicVector':
        """
        Permutation operation.

        Creates role/position marker.
        """
        n = self.dim
        return HolographicVector([
            self.dimensions[(i - shift) % n]
            for i in range(n)
        ])

    def similarity(self, other: 'HolographicVector') -> float:
        """
        Cosine similarity between vectors.
        """
        dot = sum(a * b for a, b in zip(self.dimensions, other.dimensions))
        mag1 = math.sqrt(sum(d * d for d in self.dimensions))
        mag2 = math.sqrt(sum(d * d for d in other.dimensions))

        if mag1 == 0 or mag2 == 0:
            return 0.0

        return dot / (mag1 * mag2)

    def threshold(self, t: float = 0.0) -> 'HolographicVector':
        """Apply threshold to create bipolar vector."""
        return HolographicVector([
            1.0 if d > t else -1.0
            for d in self.dimensions
        ])


# ============================================================================
# HOLOGRAPHIC MEMORY
# ============================================================================

class HolographicMemory:
    """
    Holographic associative memory.

    Features:
    - Content-addressable retrieval
    - Distributed representation
    - Graceful degradation
    - Fault tolerance

    "Ba'el stores holographically." — Ba'el
    """

    def __init__(self, dim: int = 10000):
        """
        Initialize holographic memory.

        Args:
            dim: Vector dimensionality (higher = more capacity)
        """
        self._dim = dim
        self._memory = HolographicVector([0.0] * dim)
        self._item_vectors: Dict[str, HolographicVector] = {}
        self._lock = threading.RLock()

    def store(self, key: str, value: Any) -> None:
        """
        Store key-value association.

        Creates holographic trace in memory.
        """
        with self._lock:
            # Create vectors for key and value
            key_vec = HolographicVector.from_text(key, self._dim)

            # Store value representation
            if isinstance(value, str):
                value_vec = HolographicVector.from_text(value, self._dim)
            else:
                value_vec = HolographicVector.from_text(str(value), self._dim)

            # Bind key and value
            association = key_vec.bind(value_vec)

            # Add to memory (bundle)
            self._memory = self._memory.bundle(association)

            # Store for retrieval verification
            self._item_vectors[key] = value_vec

    def retrieve(self, key: str, top_k: int = 1) -> List[Tuple[str, float]]:
        """
        Retrieve value associated with key.

        Uses holographic unbinding.
        """
        with self._lock:
            key_vec = HolographicVector.from_text(key, self._dim)

            # Unbind to get approximate value
            retrieved = self._memory.unbind(key_vec)

            # Find best matches in stored vectors
            similarities = []
            for stored_key, stored_vec in self._item_vectors.items():
                sim = retrieved.similarity(stored_vec)
                similarities.append((stored_key, sim))

            # Sort by similarity
            similarities.sort(key=lambda x: x[1], reverse=True)

            return similarities[:top_k]

    def query_similar(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """
        Find items similar to query.
        """
        with self._lock:
            query_vec = HolographicVector.from_text(query, self._dim)

            similarities = []
            for key, vec in self._item_vectors.items():
                sim = query_vec.similarity(vec)
                similarities.append((key, sim))

            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:top_k]

    def store_sequence(self, name: str, sequence: List[str]) -> None:
        """
        Store ordered sequence using permutation.
        """
        with self._lock:
            # Create sequence vector by binding with position
            seq_vec = HolographicVector([0.0] * self._dim)

            for i, item in enumerate(sequence):
                item_vec = HolographicVector.from_text(item, self._dim)
                # Use permutation for position encoding
                positioned = item_vec.permute(i)
                seq_vec = seq_vec.bundle(positioned)

            # Store sequence
            name_vec = HolographicVector.from_text(name, self._dim)
            association = name_vec.bind(seq_vec)
            self._memory = self._memory.bundle(association)
            self._item_vectors[name] = seq_vec

    def retrieve_sequence(self, name: str, length: int) -> List[str]:
        """
        Retrieve ordered sequence.
        """
        with self._lock:
            name_vec = HolographicVector.from_text(name, self._dim)
            seq_vec = self._memory.unbind(name_vec)

            # Retrieve each position
            result = []
            for i in range(length):
                # Unpermute to get item at position
                item_vec = seq_vec.permute(-i)

                # Find best match
                best_match = None
                best_sim = -1.0

                for key, vec in self._item_vectors.items():
                    sim = item_vec.similarity(vec)
                    if sim > best_sim:
                        best_sim = sim
                        best_match = key

                if best_match:
                    result.append(best_match)

            return result

    def create_analogy(
        self,
        a: str,
        b: str,
        c: str
    ) -> List[Tuple[str, float]]:
        """
        Solve analogy: a is to b as c is to ?

        Uses holographic arithmetic: d = b - a + c
        """
        with self._lock:
            a_vec = HolographicVector.from_text(a, self._dim)
            b_vec = HolographicVector.from_text(b, self._dim)
            c_vec = HolographicVector.from_text(c, self._dim)

            # Compute analogy vector
            # d = b + (c - a) using unbind as inverse
            diff = c_vec.unbind(a_vec)
            target = b_vec.bind(diff)

            # Find nearest neighbors
            similarities = []
            for key, vec in self._item_vectors.items():
                if key not in [a, b, c]:
                    sim = target.similarity(vec)
                    similarities.append((key, sim))

            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:5]

    @property
    def capacity(self) -> int:
        """Estimated memory capacity."""
        return self._dim // 10  # Rule of thumb

    @property
    def utilization(self) -> float:
        """Current memory utilization."""
        return len(self._item_vectors) / self.capacity


# ============================================================================
# SEMANTIC HOLOGRAPHIC MEMORY
# ============================================================================

class SemanticHolographicMemory:
    """
    Semantic holographic memory with concept binding.

    "Ba'el understands semantically." — Ba'el
    """

    def __init__(self, dim: int = 10000):
        """Initialize semantic memory."""
        self._dim = dim
        self._base = HolographicMemory(dim)

        # Role vectors for semantic structure
        self._roles: Dict[str, HolographicVector] = {}
        self._concepts: Dict[str, HolographicVector] = {}
        self._lock = threading.RLock()

    def define_role(self, role_name: str) -> None:
        """Define a semantic role."""
        with self._lock:
            self._roles[role_name] = HolographicVector.random(self._dim)

    def define_concept(self, concept: str) -> None:
        """Define a concept."""
        with self._lock:
            self._concepts[concept] = HolographicVector.from_text(concept, self._dim)

    def store_frame(
        self,
        frame_name: str,
        bindings: Dict[str, str]
    ) -> None:
        """
        Store semantic frame with role bindings.

        Example: store_frame("event1", {"agent": "john", "action": "run"})
        """
        with self._lock:
            frame_vec = HolographicVector([0.0] * self._dim)

            for role, filler in bindings.items():
                if role not in self._roles:
                    self.define_role(role)
                if filler not in self._concepts:
                    self.define_concept(filler)

                role_vec = self._roles[role]
                filler_vec = self._concepts[filler]

                # Bind role to filler
                binding = role_vec.bind(filler_vec)
                frame_vec = frame_vec.bundle(binding)

            # Store frame
            self._base.store(frame_name, frame_vec)
            self._concepts[frame_name] = frame_vec

    def query_role(self, frame_name: str, role: str) -> List[Tuple[str, float]]:
        """
        Query role filler from frame.
        """
        with self._lock:
            if frame_name not in self._concepts or role not in self._roles:
                return []

            frame_vec = self._concepts[frame_name]
            role_vec = self._roles[role]

            # Unbind to get filler
            filler_vec = frame_vec.unbind(role_vec)

            # Find best matching concept
            results = []
            for concept, vec in self._concepts.items():
                if concept != frame_name:
                    sim = filler_vec.similarity(vec)
                    results.append((concept, sim))

            results.sort(key=lambda x: x[1], reverse=True)
            return results[:5]

    def find_similar_frames(
        self,
        frame_name: str,
        top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """Find semantically similar frames."""
        return self._base.query_similar(frame_name, top_k)


# ============================================================================
# SPARSE DISTRIBUTED MEMORY
# ============================================================================

class SparseDistributedMemory:
    """
    Sparse Distributed Memory (Kanerva).

    High-dimensional content-addressable memory.

    "Ba'el distributes sparsely." — Ba'el
    """

    def __init__(
        self,
        address_dim: int = 1000,
        data_dim: int = 1000,
        num_hard_locations: int = 10000,
        access_radius: int = 451
    ):
        """
        Initialize SDM.

        Args:
            address_dim: Dimensionality of address space
            data_dim: Dimensionality of data stored
            num_hard_locations: Number of memory locations
            access_radius: Hamming radius for access
        """
        self._address_dim = address_dim
        self._data_dim = data_dim
        self._num_locations = num_hard_locations
        self._access_radius = access_radius

        # Hard locations (random addresses)
        self._addresses = [
            HolographicVector.random(address_dim).threshold()
            for _ in range(num_hard_locations)
        ]

        # Counters at each location
        self._counters = [[0] * data_dim for _ in range(num_hard_locations)]

        self._lock = threading.RLock()

    def _hamming_distance(
        self,
        v1: HolographicVector,
        v2: HolographicVector
    ) -> int:
        """Calculate Hamming distance."""
        return sum(
            1 for a, b in zip(v1.dimensions, v2.dimensions)
            if a != b
        )

    def _get_activated_locations(
        self,
        address: HolographicVector
    ) -> List[int]:
        """Get locations within access radius."""
        activated = []
        for i, loc_addr in enumerate(self._addresses):
            dist = self._hamming_distance(address, loc_addr)
            if dist <= self._access_radius:
                activated.append(i)
        return activated

    def write(
        self,
        address: HolographicVector,
        data: HolographicVector
    ) -> None:
        """
        Write data at address.

        Updates all locations within access radius.
        """
        with self._lock:
            activated = self._get_activated_locations(address)

            for loc in activated:
                for j in range(self._data_dim):
                    if data.dimensions[j] > 0:
                        self._counters[loc][j] += 1
                    else:
                        self._counters[loc][j] -= 1

    def read(self, address: HolographicVector) -> HolographicVector:
        """
        Read data at address.

        Sums counters from activated locations.
        """
        with self._lock:
            activated = self._get_activated_locations(address)

            if not activated:
                return HolographicVector([0.0] * self._data_dim)

            # Sum counters
            sums = [0] * self._data_dim
            for loc in activated:
                for j in range(self._data_dim):
                    sums[j] += self._counters[loc][j]

            # Threshold to bipolar
            result = [1.0 if s > 0 else -1.0 for s in sums]
            return HolographicVector(result)

    def store_pattern(self, pattern: HolographicVector) -> None:
        """Store pattern as both address and data (autoassociative)."""
        self.write(pattern, pattern)

    def recall_pattern(
        self,
        cue: HolographicVector,
        iterations: int = 5
    ) -> HolographicVector:
        """
        Recall pattern from partial cue.

        Uses iterative cleanup.
        """
        current = cue
        for _ in range(iterations):
            current = self.read(current)
        return current


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_holographic_memory(dim: int = 10000) -> HolographicMemory:
    """Create holographic memory."""
    return HolographicMemory(dim)


def create_semantic_memory(dim: int = 10000) -> SemanticHolographicMemory:
    """Create semantic holographic memory."""
    return SemanticHolographicMemory(dim)


def create_sdm(
    address_dim: int = 1000,
    data_dim: int = 1000,
    num_locations: int = 10000
) -> SparseDistributedMemory:
    """Create sparse distributed memory."""
    return SparseDistributedMemory(address_dim, data_dim, num_locations)


def vector_similarity(v1: HolographicVector, v2: HolographicVector) -> float:
    """Calculate similarity between vectors."""
    return v1.similarity(v2)
