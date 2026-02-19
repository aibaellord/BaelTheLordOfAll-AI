"""
⚡ HYPERDIMENSIONAL CORE ⚡
==========================
Core hyperdimensional computing primitives.

In high dimensions, random vectors are nearly orthogonal!
This enables:
- Exponentially many nearly-orthogonal concepts
- Robust distributed representations
- Mathematical operations for reasoning
"""

import math
import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import (
    Any, Callable, Dict, Generic, List, Optional,
    Set, Tuple, TypeVar, Union
)
import uuid
import hashlib


class VectorType(Enum):
    """Types of hyperdimensional vectors"""
    BINARY = "binary"           # {-1, +1}
    BIPOLAR = "bipolar"         # {-1, +1} (same as binary)
    HOLOGRAPHIC = "holographic" # Complex unit vectors
    REAL = "real"               # Real-valued
    SPARSE = "sparse"           # Sparse binary


@dataclass
class HyperdimensionalVector:
    """
    A vector in high-dimensional space.

    The fundamental unit of hyperdimensional computing.
    In D=10000 dimensions, random vectors are ~orthogonal.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    vector: np.ndarray = field(default_factory=lambda: np.zeros(10000))
    dimension: int = 10000
    vector_type: VectorType = VectorType.BIPOLAR
    label: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if len(self.vector) != self.dimension:
            self.vector = np.resize(self.vector, self.dimension)

    @property
    def magnitude(self) -> float:
        """Vector magnitude"""
        return float(np.linalg.norm(self.vector))

    @property
    def normalized(self) -> 'HyperdimensionalVector':
        """Return normalized vector"""
        mag = self.magnitude
        if mag < 1e-10:
            return self

        return HyperdimensionalVector(
            vector=self.vector / mag,
            dimension=self.dimension,
            vector_type=self.vector_type,
            label=self.label
        )

    @classmethod
    def random(
        cls,
        dimension: int = 10000,
        vector_type: VectorType = VectorType.BIPOLAR,
        seed: Optional[str] = None
    ) -> 'HyperdimensionalVector':
        """Generate random hyperdimensional vector"""
        if seed:
            rng = np.random.default_rng(
                int(hashlib.sha256(seed.encode()).hexdigest()[:8], 16)
            )
        else:
            rng = np.random.default_rng()

        if vector_type == VectorType.BINARY or vector_type == VectorType.BIPOLAR:
            # Random ±1
            vec = rng.choice([-1, 1], size=dimension).astype(np.float32)
        elif vector_type == VectorType.HOLOGRAPHIC:
            # Random complex phase
            phases = rng.uniform(0, 2 * np.pi, dimension)
            vec = np.exp(1j * phases)
        elif vector_type == VectorType.REAL:
            # Random normal
            vec = rng.normal(0, 1, dimension).astype(np.float32)
            vec = vec / np.linalg.norm(vec)
        elif vector_type == VectorType.SPARSE:
            # Sparse binary
            vec = np.zeros(dimension)
            active = rng.choice(dimension, size=dimension // 100, replace=False)
            vec[active] = rng.choice([-1, 1], size=len(active))
        else:
            vec = rng.normal(0, 1, dimension)

        return cls(
            vector=vec,
            dimension=dimension,
            vector_type=vector_type,
            label=seed or ""
        )

    @classmethod
    def from_seed(
        cls,
        seed: str,
        dimension: int = 10000
    ) -> 'HyperdimensionalVector':
        """Create deterministic vector from seed"""
        return cls.random(dimension, VectorType.BIPOLAR, seed)

    def similarity(self, other: 'HyperdimensionalVector') -> float:
        """Compute similarity (cosine)"""
        if self.dimension != other.dimension:
            return 0.0

        if self.vector_type == VectorType.HOLOGRAPHIC:
            # Complex correlation
            return float(np.abs(np.vdot(self.vector, other.vector)) / self.dimension)
        else:
            # Cosine similarity
            mag1 = np.linalg.norm(self.vector)
            mag2 = np.linalg.norm(other.vector)
            if mag1 < 1e-10 or mag2 < 1e-10:
                return 0.0
            return float(np.dot(self.vector, other.vector) / (mag1 * mag2))

    def hamming_similarity(self, other: 'HyperdimensionalVector') -> float:
        """Compute Hamming similarity (for binary vectors)"""
        if self.vector_type not in [VectorType.BINARY, VectorType.BIPOLAR]:
            return self.similarity(other)

        agreements = np.sum(np.sign(self.vector) == np.sign(other.vector))
        return float(agreements / self.dimension)

    def __add__(self, other: 'HyperdimensionalVector') -> 'HyperdimensionalVector':
        """Vector addition (bundling)"""
        return HyperdimensionalVector(
            vector=self.vector + other.vector,
            dimension=self.dimension,
            vector_type=self.vector_type
        )

    def __mul__(self, other: Union['HyperdimensionalVector', float]) -> 'HyperdimensionalVector':
        """Element-wise multiplication (binding) or scalar multiplication"""
        if isinstance(other, HyperdimensionalVector):
            return HyperdimensionalVector(
                vector=self.vector * other.vector,
                dimension=self.dimension,
                vector_type=self.vector_type
            )
        else:
            return HyperdimensionalVector(
                vector=self.vector * other,
                dimension=self.dimension,
                vector_type=self.vector_type
            )

    def __neg__(self) -> 'HyperdimensionalVector':
        """Negation"""
        return HyperdimensionalVector(
            vector=-self.vector,
            dimension=self.dimension,
            vector_type=self.vector_type
        )

    def permute(self, shift: int = 1) -> 'HyperdimensionalVector':
        """Cyclic permutation"""
        return HyperdimensionalVector(
            vector=np.roll(self.vector, shift),
            dimension=self.dimension,
            vector_type=self.vector_type
        )

    def binarize(self) -> 'HyperdimensionalVector':
        """Convert to binary ±1"""
        return HyperdimensionalVector(
            vector=np.sign(self.vector + 1e-10),  # Avoid zeros
            dimension=self.dimension,
            vector_type=VectorType.BIPOLAR
        )


class HyperdimensionalSpace:
    """
    A space of hyperdimensional vectors with operations.

    Manages vocabulary of concepts and their vectors.
    """

    def __init__(
        self,
        dimension: int = 10000,
        vector_type: VectorType = VectorType.BIPOLAR
    ):
        self.dimension = dimension
        self.vector_type = vector_type
        self.vocabulary: Dict[str, HyperdimensionalVector] = {}
        self.reverse_index: Optional[np.ndarray] = None
        self.labels: List[str] = []

    def add_concept(
        self,
        name: str,
        vector: Optional[HyperdimensionalVector] = None
    ) -> HyperdimensionalVector:
        """Add concept to vocabulary"""
        if vector is None:
            vector = HyperdimensionalVector.from_seed(name, self.dimension)
            vector.label = name

        self.vocabulary[name] = vector
        self.reverse_index = None  # Invalidate

        return vector

    def get_concept(self, name: str) -> Optional[HyperdimensionalVector]:
        """Get concept vector"""
        return self.vocabulary.get(name)

    def get_or_create(self, name: str) -> HyperdimensionalVector:
        """Get concept or create if not exists"""
        if name not in self.vocabulary:
            self.add_concept(name)
        return self.vocabulary[name]

    def query(
        self,
        query_vector: HyperdimensionalVector,
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """Find most similar concepts"""
        results = []

        for name, vector in self.vocabulary.items():
            sim = query_vector.similarity(vector)
            results.append((name, sim))

        results.sort(key=lambda x: -x[1])
        return results[:top_k]

    def _build_index(self):
        """Build matrix index for fast search"""
        self.labels = list(self.vocabulary.keys())
        vectors = [self.vocabulary[l].vector for l in self.labels]
        self.reverse_index = np.array(vectors)

    def fast_query(
        self,
        query_vector: HyperdimensionalVector,
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """Fast batch query using matrix operations"""
        if self.reverse_index is None:
            self._build_index()

        if len(self.labels) == 0:
            return []

        # Compute all similarities at once
        query = query_vector.vector.reshape(1, -1)
        norms = np.linalg.norm(self.reverse_index, axis=1, keepdims=True)
        norms[norms < 1e-10] = 1
        normalized = self.reverse_index / norms

        query_norm = np.linalg.norm(query)
        if query_norm > 1e-10:
            query = query / query_norm

        similarities = (normalized @ query.T).flatten()

        # Get top-k
        indices = np.argsort(-similarities)[:top_k]

        return [(self.labels[i], float(similarities[i])) for i in indices]


class HDBinding:
    """
    Binding operation for hyperdimensional computing.

    Binding creates new vector representing PAIR of concepts.
    X ⊛ Y represents "X bound to Y" or "X in relation to Y"

    Properties:
    - Preserves dimension
    - Result is dissimilar to inputs
    - Self-inverse: (X ⊛ Y) ⊛ Y ≈ X
    """

    @staticmethod
    def bind(
        a: HyperdimensionalVector,
        b: HyperdimensionalVector
    ) -> HyperdimensionalVector:
        """
        Bind two vectors.

        For bipolar: element-wise XOR (multiplication)
        For holographic: circular convolution
        """
        if a.vector_type == VectorType.HOLOGRAPHIC:
            # Circular convolution
            result = np.fft.ifft(np.fft.fft(a.vector) * np.fft.fft(b.vector))
            return HyperdimensionalVector(
                vector=result,
                dimension=a.dimension,
                vector_type=a.vector_type
            )
        else:
            # Element-wise multiplication
            return a * b

    @staticmethod
    def unbind(
        bound: HyperdimensionalVector,
        key: HyperdimensionalVector
    ) -> HyperdimensionalVector:
        """
        Unbind to retrieve the other vector.

        For bipolar: same as bind (self-inverse)
        For holographic: circular correlation
        """
        if bound.vector_type == VectorType.HOLOGRAPHIC:
            # Circular correlation
            result = np.fft.ifft(
                np.conj(np.fft.fft(key.vector)) * np.fft.fft(bound.vector)
            )
            return HyperdimensionalVector(
                vector=result,
                dimension=bound.dimension,
                vector_type=bound.vector_type
            )
        else:
            # Self-inverse multiplication
            return bound * key

    @staticmethod
    def bind_sequence(vectors: List[HyperdimensionalVector]) -> HyperdimensionalVector:
        """Bind sequence with position encoding"""
        if not vectors:
            return HyperdimensionalVector()

        result = vectors[0]
        for i, vec in enumerate(vectors[1:], 1):
            # Permute to encode position
            shifted = vec.permute(i)
            result = HDBinding.bind(result, shifted)

        return result


class HDBundling:
    """
    Bundling operation for hyperdimensional computing.

    Bundling creates vector representing SET of concepts.
    X + Y + Z represents "X and Y and Z"

    Properties:
    - Result is similar to all inputs
    - More items = lower similarity to each
    - Approximate set membership test
    """

    @staticmethod
    def bundle(vectors: List[HyperdimensionalVector]) -> HyperdimensionalVector:
        """
        Bundle multiple vectors into one.

        Sum and threshold for cleanup.
        """
        if not vectors:
            return HyperdimensionalVector()

        result_vec = np.zeros(vectors[0].dimension)

        for vec in vectors:
            result_vec += vec.vector

        return HyperdimensionalVector(
            vector=result_vec,
            dimension=vectors[0].dimension,
            vector_type=vectors[0].vector_type
        )

    @staticmethod
    def weighted_bundle(
        vectors: List[HyperdimensionalVector],
        weights: List[float]
    ) -> HyperdimensionalVector:
        """Bundle with importance weights"""
        if not vectors:
            return HyperdimensionalVector()

        result_vec = np.zeros(vectors[0].dimension)

        for vec, weight in zip(vectors, weights):
            result_vec += weight * vec.vector

        return HyperdimensionalVector(
            vector=result_vec,
            dimension=vectors[0].dimension,
            vector_type=vectors[0].vector_type
        )

    @staticmethod
    def resonator_cleanup(
        noisy: HyperdimensionalVector,
        codebook: List[HyperdimensionalVector],
        iterations: int = 10
    ) -> HyperdimensionalVector:
        """
        Resonator network for cleanup/factorization.

        Iteratively finds best matching atomic concepts.
        """
        current = noisy.vector.copy()

        for _ in range(iterations):
            # Find best match in codebook
            best_sim = -1
            best_idx = 0

            for i, code in enumerate(codebook):
                sim = np.dot(current, code.vector) / (
                    np.linalg.norm(current) * np.linalg.norm(code.vector) + 1e-10
                )
                if sim > best_sim:
                    best_sim = sim
                    best_idx = i

            # Project onto best match
            best = codebook[best_idx].vector
            current = best * np.dot(current, best) / (np.dot(best, best) + 1e-10)

        return HyperdimensionalVector(
            vector=current,
            dimension=noisy.dimension,
            vector_type=noisy.vector_type
        )


class HDPermutation:
    """
    Permutation operation for position/role encoding.

    ρ(X) represents "X in different role/position"

    Properties:
    - Preserves similarity between vectors
    - ρ^n(X) is dissimilar to X for n > 0
    - Used for sequence encoding
    """

    @staticmethod
    def permute(
        vector: HyperdimensionalVector,
        shift: int = 1
    ) -> HyperdimensionalVector:
        """Cyclic permutation"""
        return vector.permute(shift)

    @staticmethod
    def inverse_permute(
        vector: HyperdimensionalVector,
        shift: int = 1
    ) -> HyperdimensionalVector:
        """Inverse permutation"""
        return vector.permute(-shift)

    @staticmethod
    def encode_sequence(
        vectors: List[HyperdimensionalVector]
    ) -> HyperdimensionalVector:
        """
        Encode sequence with positional permutation.

        Result encodes both content AND position.
        """
        if not vectors:
            return HyperdimensionalVector()

        result_vec = np.zeros(vectors[0].dimension)

        for i, vec in enumerate(vectors):
            permuted = vec.permute(i)
            result_vec += permuted.vector

        return HyperdimensionalVector(
            vector=result_vec,
            dimension=vectors[0].dimension,
            vector_type=vectors[0].vector_type
        )

    @staticmethod
    def decode_position(
        encoded: HyperdimensionalVector,
        content: HyperdimensionalVector,
        max_position: int = 100
    ) -> int:
        """Decode position of content in encoded sequence"""
        best_sim = -1
        best_pos = 0

        for pos in range(max_position):
            permuted = content.permute(pos)
            sim = encoded.similarity(permuted)
            if sim > best_sim:
                best_sim = sim
                best_pos = pos

        return best_pos


class HDSimilarity:
    """
    Similarity metrics for hyperdimensional vectors.
    """

    @staticmethod
    def cosine(a: HyperdimensionalVector, b: HyperdimensionalVector) -> float:
        """Cosine similarity"""
        return a.similarity(b)

    @staticmethod
    def hamming(a: HyperdimensionalVector, b: HyperdimensionalVector) -> float:
        """Hamming similarity for binary vectors"""
        return a.hamming_similarity(b)

    @staticmethod
    def dot(a: HyperdimensionalVector, b: HyperdimensionalVector) -> float:
        """Dot product"""
        return float(np.dot(a.vector, b.vector))

    @staticmethod
    def angular(a: HyperdimensionalVector, b: HyperdimensionalVector) -> float:
        """Angular similarity (1 - angle/π)"""
        cos_sim = a.similarity(b)
        cos_sim = np.clip(cos_sim, -1, 1)
        angle = np.arccos(cos_sim)
        return 1 - angle / np.pi

    @staticmethod
    def overlap(a: HyperdimensionalVector, b: HyperdimensionalVector) -> float:
        """Overlap coefficient for sparse vectors"""
        nonzero_a = np.abs(a.vector) > 1e-10
        nonzero_b = np.abs(b.vector) > 1e-10

        intersection = np.sum(nonzero_a & nonzero_b)
        min_size = min(np.sum(nonzero_a), np.sum(nonzero_b))

        if min_size == 0:
            return 0.0
        return float(intersection / min_size)


# Export all
__all__ = [
    'VectorType',
    'HyperdimensionalVector',
    'HyperdimensionalSpace',
    'HDBinding',
    'HDBundling',
    'HDPermutation',
    'HDSimilarity',
]
