"""
BAEL Hyperdimensional Computing Engine
=======================================

Computing with high-dimensional holographic vectors.

"Ba'el computes in hyperspace." — Ba'el
"""

import logging
import threading
import random
import math
import hashlib
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto
import copy

logger = logging.getLogger("BAEL.HyperdimensionalComputing")


T = TypeVar('T')


# ============================================================================
# HYPERVECTOR
# ============================================================================

class HyperVectorType(Enum):
    """Types of hypervectors."""
    BINARY = auto()    # {0, 1}
    BIPOLAR = auto()   # {-1, +1}
    REAL = auto()      # Real-valued
    COMPLEX = auto()   # Complex-valued
    SPARSE = auto()    # Sparse representation


@dataclass
class HyperVector:
    """
    High-dimensional vector for hyperdimensional computing.

    Properties:
    - Holographic: Information distributed across all dimensions
    - Robust: Tolerant to noise and errors
    - Efficient: Simple operations (bundling, binding, permutation)
    """
    values: List[float]
    vector_type: HyperVectorType = HyperVectorType.BIPOLAR

    @property
    def dimension(self) -> int:
        return len(self.values)

    @staticmethod
    def random(dim: int, vtype: HyperVectorType = HyperVectorType.BIPOLAR) -> 'HyperVector':
        """Create random hypervector."""
        if vtype == HyperVectorType.BINARY:
            values = [random.choice([0, 1]) for _ in range(dim)]
        elif vtype == HyperVectorType.BIPOLAR:
            values = [random.choice([-1, 1]) for _ in range(dim)]
        elif vtype == HyperVectorType.REAL:
            values = [random.gauss(0, 1) for _ in range(dim)]
        else:
            values = [random.choice([-1, 1]) for _ in range(dim)]
        return HyperVector(values, vtype)

    @staticmethod
    def from_seed(seed: str, dim: int, vtype: HyperVectorType = HyperVectorType.BIPOLAR) -> 'HyperVector':
        """Create deterministic hypervector from seed."""
        h = hashlib.sha256(seed.encode()).digest()
        random.seed(int.from_bytes(h[:8], 'big'))
        result = HyperVector.random(dim, vtype)
        random.seed()
        return result

    @staticmethod
    def zero(dim: int) -> 'HyperVector':
        """Create zero hypervector."""
        return HyperVector([0.0] * dim, HyperVectorType.REAL)

    def normalize(self) -> 'HyperVector':
        """Normalize to unit length."""
        magnitude = math.sqrt(sum(v * v for v in self.values))
        if magnitude > 0:
            return HyperVector([v / magnitude for v in self.values], self.vector_type)
        return self

    def binarize(self) -> 'HyperVector':
        """Convert to bipolar based on sign."""
        return HyperVector(
            [1.0 if v > 0 else -1.0 for v in self.values],
            HyperVectorType.BIPOLAR
        )

    # =========== CORE OPERATIONS ===========

    def bundle(self, *others: 'HyperVector') -> 'HyperVector':
        """
        Bundling (superposition/addition).

        Creates composite representation.
        Result is similar to all inputs.
        """
        result = list(self.values)
        for other in others:
            for i in range(min(len(result), len(other.values))):
                result[i] += other.values[i]
        return HyperVector(result, HyperVectorType.REAL)

    def bind(self, other: 'HyperVector') -> 'HyperVector':
        """
        Binding (multiplication/XOR).

        Creates association.
        Result is dissimilar to inputs.
        """
        if self.vector_type == HyperVectorType.BIPOLAR:
            # Element-wise multiplication for bipolar
            return HyperVector(
                [a * b for a, b in zip(self.values, other.values)],
                HyperVectorType.BIPOLAR
            )
        elif self.vector_type == HyperVectorType.BINARY:
            # XOR for binary
            return HyperVector(
                [int(a) ^ int(b) for a, b in zip(self.values, other.values)],
                HyperVectorType.BINARY
            )
        else:
            # Circular convolution for real
            n = self.dimension
            result = [0.0] * n
            for i in range(n):
                for j in range(n):
                    result[(i + j) % n] += self.values[i] * other.values[j]
            return HyperVector(result, HyperVectorType.REAL)

    def unbind(self, other: 'HyperVector') -> 'HyperVector':
        """
        Unbinding (inverse of bind).

        Retrieves bound component.
        """
        if self.vector_type == HyperVectorType.BIPOLAR:
            # Self-inverse for bipolar
            return self.bind(other)
        else:
            # Use inverse permutation
            n = self.dimension
            inverse = [other.values[(-i) % n] for i in range(n)]
            return self.bind(HyperVector(inverse, other.vector_type))

    def permute(self, shift: int = 1) -> 'HyperVector':
        """
        Permutation (rotation).

        Creates sequence/position encoding.
        """
        n = self.dimension
        return HyperVector(
            [self.values[(i - shift) % n] for i in range(n)],
            self.vector_type
        )

    # =========== SIMILARITY ===========

    def similarity(self, other: 'HyperVector') -> float:
        """Cosine similarity."""
        dot = sum(a * b for a, b in zip(self.values, other.values))
        mag1 = math.sqrt(sum(v * v for v in self.values))
        mag2 = math.sqrt(sum(v * v for v in other.values))
        if mag1 == 0 or mag2 == 0:
            return 0.0
        return dot / (mag1 * mag2)

    def hamming_distance(self, other: 'HyperVector') -> int:
        """Hamming distance for binary/bipolar vectors."""
        return sum(1 for a, b in zip(self.values, other.values) if a != b)

    def hamming_similarity(self, other: 'HyperVector') -> float:
        """Normalized Hamming similarity."""
        dist = self.hamming_distance(other)
        return 1.0 - dist / self.dimension


# ============================================================================
# ITEM MEMORY
# ============================================================================

class ItemMemory:
    """
    Associative memory for hypervectors.

    "Ba'el stores in hyperspace." — Ba'el
    """

    def __init__(self, dimension: int = 10000):
        """Initialize item memory."""
        self._dim = dimension
        self._items: Dict[str, HyperVector] = {}
        self._lock = threading.RLock()

    def add(self, name: str, vector: Optional[HyperVector] = None) -> HyperVector:
        """Add item to memory."""
        with self._lock:
            if vector is None:
                vector = HyperVector.from_seed(name, self._dim)
            self._items[name] = vector
            return vector

    def get(self, name: str) -> Optional[HyperVector]:
        """Get item by name."""
        return self._items.get(name)

    def get_or_create(self, name: str) -> HyperVector:
        """Get item or create if not exists."""
        with self._lock:
            if name not in self._items:
                self.add(name)
            return self._items[name]

    def query(self, vector: HyperVector, top_k: int = 1) -> List[Tuple[str, float]]:
        """Find most similar items."""
        with self._lock:
            similarities = [
                (name, vector.similarity(v))
                for name, v in self._items.items()
            ]
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:top_k]


# ============================================================================
# ENCODER
# ============================================================================

class HyperdimensionalEncoder:
    """
    Encode various data types to hypervectors.

    "Ba'el encodes reality." — Ba'el
    """

    def __init__(self, dimension: int = 10000):
        """Initialize encoder."""
        self._dim = dimension
        self._item_memory = ItemMemory(dimension)
        self._level_vectors: Dict[str, List[HyperVector]] = {}
        self._lock = threading.RLock()

    def encode_symbol(self, symbol: str) -> HyperVector:
        """Encode symbolic/categorical value."""
        return self._item_memory.get_or_create(symbol)

    def encode_scalar(
        self,
        value: float,
        min_val: float = 0.0,
        max_val: float = 1.0,
        levels: int = 100
    ) -> HyperVector:
        """
        Encode scalar value using level encoding.

        Uses thermometer coding: similar values have similar vectors.
        """
        with self._lock:
            key = f"scalar_{min_val}_{max_val}_{levels}"

            if key not in self._level_vectors:
                # Generate level vectors
                base = HyperVector.random(self._dim)
                self._level_vectors[key] = [base]

                for i in range(1, levels):
                    # Each level differs slightly from previous
                    flip_count = self._dim // levels
                    prev = list(self._level_vectors[key][-1].values)
                    for j in range(flip_count):
                        idx = (i * flip_count + j) % self._dim
                        prev[idx] = -prev[idx]
                    self._level_vectors[key].append(HyperVector(prev))

            # Map value to level
            normalized = (value - min_val) / (max_val - min_val) if max_val > min_val else 0
            normalized = max(0, min(1, normalized))
            level = int(normalized * (levels - 1))

            return self._level_vectors[key][level]

    def encode_sequence(self, items: List[str]) -> HyperVector:
        """
        Encode ordered sequence.

        Uses permutation for position encoding.
        """
        result = HyperVector.zero(self._dim)

        for i, item in enumerate(items):
            item_vec = self.encode_symbol(item)
            # Permute by position
            positioned = item_vec.permute(i)
            result = result.bundle(positioned)

        return result.binarize()

    def encode_set(self, items: Set[str]) -> HyperVector:
        """
        Encode unordered set.

        Uses bundling (order-independent).
        """
        if not items:
            return HyperVector.zero(self._dim)

        vectors = [self.encode_symbol(item) for item in items]
        result = vectors[0]
        for v in vectors[1:]:
            result = result.bundle(v)

        return result.binarize()

    def encode_graph(
        self,
        nodes: List[str],
        edges: List[Tuple[str, str, str]]
    ) -> HyperVector:
        """
        Encode graph structure.

        Edges are (source, relation, target) triples.
        """
        result = HyperVector.zero(self._dim)

        for source, relation, target in edges:
            source_vec = self.encode_symbol(source)
            relation_vec = self.encode_symbol(relation)
            target_vec = self.encode_symbol(target)

            # Bind source-relation-target
            edge_vec = source_vec.bind(relation_vec).bind(target_vec)
            result = result.bundle(edge_vec)

        return result.binarize()

    def encode_image_patch(self, pixels: List[float]) -> HyperVector:
        """Encode image patch as hypervector."""
        # Encode each pixel position with its intensity
        result = HyperVector.zero(self._dim)

        for i, intensity in enumerate(pixels):
            pos_vec = HyperVector.from_seed(f"pixel_pos_{i}", self._dim)
            intensity_vec = self.encode_scalar(intensity, 0.0, 255.0)
            result = result.bundle(pos_vec.bind(intensity_vec))

        return result.binarize()


# ============================================================================
# CLASSIFIER
# ============================================================================

class HyperdimensionalClassifier:
    """
    Classification using hypervectors.

    "Ba'el classifies in hyperspace." — Ba'el
    """

    def __init__(self, encoder: HyperdimensionalEncoder):
        """Initialize classifier."""
        self._encoder = encoder
        self._class_prototypes: Dict[str, HyperVector] = {}
        self._class_counts: Dict[str, int] = {}
        self._lock = threading.RLock()

    def train(self, features: List[str], label: str) -> None:
        """Train on single example."""
        with self._lock:
            # Encode features
            feature_vec = self._encoder.encode_set(set(features))

            # Update class prototype
            if label not in self._class_prototypes:
                self._class_prototypes[label] = feature_vec
                self._class_counts[label] = 1
            else:
                self._class_prototypes[label] = self._class_prototypes[label].bundle(feature_vec)
                self._class_counts[label] += 1

    def predict(self, features: List[str]) -> Tuple[str, float]:
        """
        Predict class for features.

        Returns (predicted_class, confidence).
        """
        with self._lock:
            if not self._class_prototypes:
                return ("unknown", 0.0)

            feature_vec = self._encoder.encode_set(set(features))

            best_class = None
            best_sim = -1.0

            for label, prototype in self._class_prototypes.items():
                sim = feature_vec.similarity(prototype)
                if sim > best_sim:
                    best_sim = sim
                    best_class = label

            return (best_class, best_sim)

    def predict_all(self, features: List[str]) -> List[Tuple[str, float]]:
        """Get similarities to all classes."""
        with self._lock:
            feature_vec = self._encoder.encode_set(set(features))

            results = [
                (label, feature_vec.similarity(prototype))
                for label, prototype in self._class_prototypes.items()
            ]
            results.sort(key=lambda x: x[1], reverse=True)
            return results


# ============================================================================
# REASONING
# ============================================================================

class HyperdimensionalReasoner:
    """
    Reasoning with hypervectors.

    "Ba'el reasons in hyperspace." — Ba'el
    """

    def __init__(self, encoder: HyperdimensionalEncoder):
        """Initialize reasoner."""
        self._encoder = encoder
        self._knowledge: List[HyperVector] = []
        self._rules: Dict[str, Tuple[HyperVector, HyperVector]] = {}
        self._lock = threading.RLock()

    def learn_association(
        self,
        key: str,
        value: str
    ) -> None:
        """Learn key-value association."""
        with self._lock:
            key_vec = self._encoder.encode_symbol(key)
            value_vec = self._encoder.encode_symbol(value)

            # Store binding
            association = key_vec.bind(value_vec)
            self._knowledge.append(association)

    def query_association(self, key: str) -> List[Tuple[str, float]]:
        """Query for associated values."""
        with self._lock:
            key_vec = self._encoder.encode_symbol(key)

            # Unbind from all knowledge
            results = []
            for assoc in self._knowledge:
                retrieved = assoc.unbind(key_vec)
                matches = self._encoder._item_memory.query(retrieved, top_k=1)
                if matches:
                    results.extend(matches)

            return results

    def learn_rule(
        self,
        name: str,
        antecedent: List[str],
        consequent: List[str]
    ) -> None:
        """Learn if-then rule."""
        with self._lock:
            ante_vec = self._encoder.encode_set(set(antecedent))
            cons_vec = self._encoder.encode_set(set(consequent))
            self._rules[name] = (ante_vec, cons_vec)

    def apply_rules(self, facts: List[str]) -> List[str]:
        """Apply rules to derive new facts."""
        with self._lock:
            facts_vec = self._encoder.encode_set(set(facts))
            derived = []

            for name, (ante_vec, cons_vec) in self._rules.items():
                # Check if antecedent is satisfied
                sim = facts_vec.similarity(ante_vec)
                if sim > 0.7:  # Threshold for rule firing
                    # Derive consequent
                    matches = self._encoder._item_memory.query(cons_vec, top_k=3)
                    derived.extend([m[0] for m in matches if m[1] > 0.5])

            return list(set(derived))

    def analogy(
        self,
        a: str,
        b: str,
        c: str
    ) -> List[Tuple[str, float]]:
        """
        Solve analogy: a is to b as c is to ?

        Uses vector arithmetic: d = b - a + c
        """
        with self._lock:
            a_vec = self._encoder.encode_symbol(a)
            b_vec = self._encoder.encode_symbol(b)
            c_vec = self._encoder.encode_symbol(c)

            # d = b ⊗ a^-1 ⊗ c (in binding terms)
            # For bipolar, inverse is the same
            diff = b_vec.unbind(a_vec)
            target = diff.bind(c_vec)

            return self._encoder._item_memory.query(target, top_k=5)


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_hypervector(dim: int = 10000) -> HyperVector:
    """Create random hypervector."""
    return HyperVector.random(dim)


def create_encoder(dim: int = 10000) -> HyperdimensionalEncoder:
    """Create hyperdimensional encoder."""
    return HyperdimensionalEncoder(dim)


def create_classifier(dim: int = 10000) -> HyperdimensionalClassifier:
    """Create hyperdimensional classifier."""
    return HyperdimensionalClassifier(HyperdimensionalEncoder(dim))


def create_reasoner(dim: int = 10000) -> HyperdimensionalReasoner:
    """Create hyperdimensional reasoner."""
    return HyperdimensionalReasoner(HyperdimensionalEncoder(dim))


def bundle(*vectors: HyperVector) -> HyperVector:
    """Bundle multiple hypervectors."""
    if not vectors:
        raise ValueError("Need at least one vector")
    return vectors[0].bundle(*vectors[1:])


def bind(*vectors: HyperVector) -> HyperVector:
    """Bind multiple hypervectors."""
    if not vectors:
        raise ValueError("Need at least one vector")
    result = vectors[0]
    for v in vectors[1:]:
        result = result.bind(v)
    return result
