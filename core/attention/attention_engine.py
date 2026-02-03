#!/usr/bin/env python3
"""
BAEL - Attention Engine
Advanced attention mechanisms for AI agents.

Features:
- Self-attention
- Multi-head attention
- Cross-attention
- Sparse attention
- Linear attention approximation
"""

import asyncio
import math
import random
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class AttentionType(Enum):
    """Types of attention mechanisms."""
    SELF = "self"
    CROSS = "cross"
    CAUSAL = "causal"
    SPARSE = "sparse"
    LINEAR = "linear"


class AttentionScoring(Enum):
    """Attention scoring functions."""
    DOT_PRODUCT = "dot_product"
    SCALED_DOT = "scaled_dot"
    ADDITIVE = "additive"
    MULTIPLICATIVE = "multiplicative"


class MaskType(Enum):
    """Mask types for attention."""
    NONE = "none"
    CAUSAL = "causal"
    PADDING = "padding"
    CUSTOM = "custom"


class NormType(Enum):
    """Normalization types."""
    SOFTMAX = "softmax"
    SIGMOID = "sigmoid"
    LAYER_NORM = "layer_norm"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class AttentionVector:
    """A vector for attention computation."""
    vector_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    values: List[float] = field(default_factory=list)
    position: int = 0


@dataclass
class AttentionQuery:
    """Query for attention mechanism."""
    query_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    vector: List[float] = field(default_factory=list)
    mask: Optional[List[bool]] = None


@dataclass
class AttentionKey:
    """Key for attention mechanism."""
    key_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    vector: List[float] = field(default_factory=list)
    position: int = 0


@dataclass
class AttentionValue:
    """Value for attention mechanism."""
    value_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    vector: List[float] = field(default_factory=list)
    position: int = 0


@dataclass
class AttentionWeights:
    """Attention weights result."""
    weights: List[List[float]] = field(default_factory=list)
    attended_positions: List[int] = field(default_factory=list)


@dataclass
class AttentionOutput:
    """Attention computation output."""
    output_vectors: List[List[float]] = field(default_factory=list)
    attention_weights: AttentionWeights = field(default_factory=AttentionWeights)
    attention_type: AttentionType = AttentionType.SELF


@dataclass
class HeadOutput:
    """Output from a single attention head."""
    head_id: int = 0
    output: List[List[float]] = field(default_factory=list)
    weights: List[List[float]] = field(default_factory=list)


@dataclass
class MultiHeadOutput:
    """Output from multi-head attention."""
    combined_output: List[List[float]] = field(default_factory=list)
    head_outputs: List[HeadOutput] = field(default_factory=list)


# =============================================================================
# VECTOR OPERATIONS
# =============================================================================

class VectorOps:
    """Vector operations for attention."""

    @staticmethod
    def dot_product(v1: List[float], v2: List[float]) -> float:
        """Compute dot product."""
        if len(v1) != len(v2):
            return 0.0
        return sum(a * b for a, b in zip(v1, v2))

    @staticmethod
    def scale(v: List[float], scalar: float) -> List[float]:
        """Scale a vector."""
        return [x * scalar for x in v]

    @staticmethod
    def add(v1: List[float], v2: List[float]) -> List[float]:
        """Add two vectors."""
        if len(v1) != len(v2):
            return v1.copy()
        return [a + b for a, b in zip(v1, v2)]

    @staticmethod
    def matrix_multiply(
        m1: List[List[float]],
        m2: List[List[float]]
    ) -> List[List[float]]:
        """Multiply two matrices."""
        if not m1 or not m2:
            return []

        rows1, cols1 = len(m1), len(m1[0])
        rows2, cols2 = len(m2), len(m2[0])

        if cols1 != rows2:
            return []

        result = [[0.0] * cols2 for _ in range(rows1)]

        for i in range(rows1):
            for j in range(cols2):
                for k in range(cols1):
                    result[i][j] += m1[i][k] * m2[k][j]

        return result

    @staticmethod
    def transpose(m: List[List[float]]) -> List[List[float]]:
        """Transpose a matrix."""
        if not m:
            return []
        return [[m[j][i] for j in range(len(m))] for i in range(len(m[0]))]

    @staticmethod
    def norm(v: List[float]) -> float:
        """Calculate vector norm."""
        return math.sqrt(sum(x ** 2 for x in v))

    @staticmethod
    def normalize(v: List[float]) -> List[float]:
        """Normalize a vector."""
        n = VectorOps.norm(v)
        if n == 0:
            return v.copy()
        return [x / n for x in v]


# =============================================================================
# SOFTMAX
# =============================================================================

class Softmax:
    """Softmax normalization."""

    @staticmethod
    def apply(values: List[float], temperature: float = 1.0) -> List[float]:
        """Apply softmax."""
        if not values:
            return []

        max_val = max(values)
        scaled = [(v - max_val) / temperature for v in values]

        exp_vals = [math.exp(v) for v in scaled]
        total = sum(exp_vals)

        if total == 0:
            return [1.0 / len(values)] * len(values)

        return [e / total for e in exp_vals]

    @staticmethod
    def apply_masked(
        values: List[float],
        mask: List[bool],
        temperature: float = 1.0
    ) -> List[float]:
        """Apply softmax with mask."""
        if not values or len(values) != len(mask):
            return values.copy() if values else []

        masked_values = [
            v if m else float('-inf')
            for v, m in zip(values, mask)
        ]

        return Softmax.apply(masked_values, temperature)


# =============================================================================
# ATTENTION SCORER
# =============================================================================

class AttentionScorer:
    """Score attention between queries and keys."""

    def __init__(self, scoring: AttentionScoring = AttentionScoring.SCALED_DOT):
        self._scoring = scoring

    def score(
        self,
        query: List[float],
        key: List[float],
        dim: Optional[int] = None
    ) -> float:
        """Compute attention score."""
        if self._scoring == AttentionScoring.DOT_PRODUCT:
            return VectorOps.dot_product(query, key)

        elif self._scoring == AttentionScoring.SCALED_DOT:
            d = dim or len(query)
            scale = 1.0 / math.sqrt(d) if d > 0 else 1.0
            return VectorOps.dot_product(query, key) * scale

        elif self._scoring == AttentionScoring.ADDITIVE:
            combined = VectorOps.add(query, key)
            return sum(math.tanh(v) for v in combined)

        elif self._scoring == AttentionScoring.MULTIPLICATIVE:
            return sum(q * k for q, k in zip(query, key)) / len(query)

        return 0.0

    def score_all(
        self,
        queries: List[List[float]],
        keys: List[List[float]],
        dim: Optional[int] = None
    ) -> List[List[float]]:
        """Score all query-key pairs."""
        scores = []
        for query in queries:
            row = [self.score(query, key, dim) for key in keys]
            scores.append(row)
        return scores


# =============================================================================
# SELF ATTENTION
# =============================================================================

class SelfAttention:
    """Self-attention mechanism."""

    def __init__(self, dim: int, scoring: AttentionScoring = AttentionScoring.SCALED_DOT):
        self._dim = dim
        self._scorer = AttentionScorer(scoring)
        self._w_q = self._init_weights(dim, dim)
        self._w_k = self._init_weights(dim, dim)
        self._w_v = self._init_weights(dim, dim)

    def _init_weights(self, rows: int, cols: int) -> List[List[float]]:
        """Initialize weight matrix."""
        scale = math.sqrt(2.0 / (rows + cols))
        return [
            [random.gauss(0, scale) for _ in range(cols)]
            for _ in range(rows)
        ]

    def _linear_transform(
        self,
        vectors: List[List[float]],
        weights: List[List[float]]
    ) -> List[List[float]]:
        """Apply linear transformation."""
        return VectorOps.matrix_multiply(vectors, weights)

    def forward(
        self,
        x: List[List[float]],
        mask: Optional[List[List[bool]]] = None
    ) -> AttentionOutput:
        """Forward pass of self-attention."""
        queries = self._linear_transform(x, self._w_q)
        keys = self._linear_transform(x, self._w_k)
        values = self._linear_transform(x, self._w_v)

        scores = self._scorer.score_all(queries, keys, self._dim)

        weights = []
        for i, row in enumerate(scores):
            if mask:
                w = Softmax.apply_masked(row, mask[i])
            else:
                w = Softmax.apply(row)
            weights.append(w)

        output = []
        for w_row in weights:
            out_vec = [0.0] * len(values[0])
            for j, weight in enumerate(w_row):
                for k, val in enumerate(values[j]):
                    out_vec[k] += weight * val
            output.append(out_vec)

        return AttentionOutput(
            output_vectors=output,
            attention_weights=AttentionWeights(weights=weights),
            attention_type=AttentionType.SELF
        )


# =============================================================================
# CROSS ATTENTION
# =============================================================================

class CrossAttention:
    """Cross-attention mechanism."""

    def __init__(self, dim: int, scoring: AttentionScoring = AttentionScoring.SCALED_DOT):
        self._dim = dim
        self._scorer = AttentionScorer(scoring)
        self._w_q = self._init_weights(dim, dim)
        self._w_k = self._init_weights(dim, dim)
        self._w_v = self._init_weights(dim, dim)

    def _init_weights(self, rows: int, cols: int) -> List[List[float]]:
        """Initialize weight matrix."""
        scale = math.sqrt(2.0 / (rows + cols))
        return [
            [random.gauss(0, scale) for _ in range(cols)]
            for _ in range(rows)
        ]

    def forward(
        self,
        query_vectors: List[List[float]],
        key_value_vectors: List[List[float]]
    ) -> AttentionOutput:
        """Forward pass with cross-attention."""
        queries = VectorOps.matrix_multiply(query_vectors, self._w_q)
        keys = VectorOps.matrix_multiply(key_value_vectors, self._w_k)
        values = VectorOps.matrix_multiply(key_value_vectors, self._w_v)

        scores = self._scorer.score_all(queries, keys, self._dim)

        weights = [Softmax.apply(row) for row in scores]

        output = []
        for w_row in weights:
            out_vec = [0.0] * len(values[0])
            for j, weight in enumerate(w_row):
                for k, val in enumerate(values[j]):
                    out_vec[k] += weight * val
            output.append(out_vec)

        return AttentionOutput(
            output_vectors=output,
            attention_weights=AttentionWeights(weights=weights),
            attention_type=AttentionType.CROSS
        )


# =============================================================================
# MULTI-HEAD ATTENTION
# =============================================================================

class MultiHeadAttention:
    """Multi-head attention mechanism."""

    def __init__(
        self,
        dim: int,
        num_heads: int,
        scoring: AttentionScoring = AttentionScoring.SCALED_DOT
    ):
        self._dim = dim
        self._num_heads = num_heads
        self._head_dim = dim // num_heads
        self._heads = [
            SelfAttention(self._head_dim, scoring)
            for _ in range(num_heads)
        ]
        self._w_o = self._init_weights(dim, dim)

    def _init_weights(self, rows: int, cols: int) -> List[List[float]]:
        """Initialize weight matrix."""
        scale = math.sqrt(2.0 / (rows + cols))
        return [
            [random.gauss(0, scale) for _ in range(cols)]
            for _ in range(rows)
        ]

    def _split_heads(
        self,
        vectors: List[List[float]]
    ) -> List[List[List[float]]]:
        """Split vectors for multi-head."""
        splits = []
        for h in range(self._num_heads):
            start = h * self._head_dim
            end = start + self._head_dim
            head_vecs = [v[start:end] for v in vectors]
            splits.append(head_vecs)
        return splits

    def _concat_heads(
        self,
        head_outputs: List[List[List[float]]]
    ) -> List[List[float]]:
        """Concatenate head outputs."""
        if not head_outputs:
            return []

        seq_len = len(head_outputs[0])
        combined = []

        for i in range(seq_len):
            vec = []
            for head_out in head_outputs:
                vec.extend(head_out[i])
            combined.append(vec)

        return combined

    def forward(
        self,
        x: List[List[float]],
        mask: Optional[List[List[bool]]] = None
    ) -> MultiHeadOutput:
        """Forward pass."""
        head_splits = self._split_heads(x)
        head_outputs = []

        for h, (head, split) in enumerate(zip(self._heads, head_splits)):
            out = head.forward(split, mask)
            head_outputs.append(HeadOutput(
                head_id=h,
                output=out.output_vectors,
                weights=out.attention_weights.weights
            ))

        concat = self._concat_heads([ho.output for ho in head_outputs])
        combined = VectorOps.matrix_multiply(concat, self._w_o)

        return MultiHeadOutput(
            combined_output=combined,
            head_outputs=head_outputs
        )


# =============================================================================
# CAUSAL ATTENTION
# =============================================================================

class CausalAttention(SelfAttention):
    """Causal (masked) self-attention."""

    def _create_causal_mask(self, seq_len: int) -> List[List[bool]]:
        """Create causal mask."""
        mask = []
        for i in range(seq_len):
            row = [j <= i for j in range(seq_len)]
            mask.append(row)
        return mask

    def forward(
        self,
        x: List[List[float]],
        mask: Optional[List[List[bool]]] = None
    ) -> AttentionOutput:
        """Forward pass with causal mask."""
        causal_mask = self._create_causal_mask(len(x))

        if mask:
            combined_mask = [
                [cm and m for cm, m in zip(c_row, m_row)]
                for c_row, m_row in zip(causal_mask, mask)
            ]
        else:
            combined_mask = causal_mask

        output = super().forward(x, combined_mask)
        output.attention_type = AttentionType.CAUSAL
        return output


# =============================================================================
# SPARSE ATTENTION
# =============================================================================

class SparseAttention:
    """Sparse attention mechanism."""

    def __init__(
        self,
        dim: int,
        window_size: int = 3,
        scoring: AttentionScoring = AttentionScoring.SCALED_DOT
    ):
        self._dim = dim
        self._window_size = window_size
        self._scorer = AttentionScorer(scoring)

    def _create_sparse_mask(self, seq_len: int) -> List[List[bool]]:
        """Create sparse attention mask."""
        mask = []
        half_window = self._window_size // 2

        for i in range(seq_len):
            row = []
            for j in range(seq_len):
                in_window = abs(i - j) <= half_window
                row.append(in_window)
            mask.append(row)

        return mask

    def forward(
        self,
        queries: List[List[float]],
        keys: List[List[float]],
        values: List[List[float]]
    ) -> AttentionOutput:
        """Forward pass with sparse attention."""
        seq_len = len(queries)
        sparse_mask = self._create_sparse_mask(seq_len)

        scores = self._scorer.score_all(queries, keys, self._dim)

        weights = []
        for i, row in enumerate(scores):
            w = Softmax.apply_masked(row, sparse_mask[i])
            weights.append(w)

        output = []
        for w_row in weights:
            out_vec = [0.0] * len(values[0])
            for j, weight in enumerate(w_row):
                for k, val in enumerate(values[j]):
                    out_vec[k] += weight * val
            output.append(out_vec)

        return AttentionOutput(
            output_vectors=output,
            attention_weights=AttentionWeights(weights=weights),
            attention_type=AttentionType.SPARSE
        )


# =============================================================================
# LINEAR ATTENTION
# =============================================================================

class LinearAttention:
    """Linear attention approximation."""

    def __init__(self, dim: int):
        self._dim = dim

    def _feature_map(self, x: List[float]) -> List[float]:
        """Apply feature map (ELU + 1)."""
        return [max(0, v) + 1 if v >= 0 else math.exp(v) for v in x]

    def forward(
        self,
        queries: List[List[float]],
        keys: List[List[float]],
        values: List[List[float]]
    ) -> AttentionOutput:
        """Forward pass with linear attention."""
        phi_q = [self._feature_map(q) for q in queries]
        phi_k = [self._feature_map(k) for k in keys]

        kv = [[0.0] * len(values[0]) for _ in range(len(keys[0]))]
        for k_vec, v_vec in zip(phi_k, values):
            for i, ki in enumerate(k_vec):
                for j, vj in enumerate(v_vec):
                    kv[i][j] += ki * vj

        k_sum = [0.0] * len(keys[0])
        for k_vec in phi_k:
            for i, ki in enumerate(k_vec):
                k_sum[i] += ki

        output = []
        weights = []

        for q_vec in phi_q:
            qkv = [0.0] * len(values[0])
            for i, qi in enumerate(q_vec):
                for j in range(len(qkv)):
                    qkv[j] += qi * kv[i][j]

            qk_sum = sum(qi * ki for qi, ki in zip(q_vec, k_sum))

            if qk_sum > 0:
                out_vec = [v / qk_sum for v in qkv]
            else:
                out_vec = qkv

            output.append(out_vec)
            weights.append([1.0 / len(keys)] * len(keys))

        return AttentionOutput(
            output_vectors=output,
            attention_weights=AttentionWeights(weights=weights),
            attention_type=AttentionType.LINEAR
        )


# =============================================================================
# ATTENTION ENGINE
# =============================================================================

class AttentionEngine:
    """
    Attention Engine for BAEL.

    Provides various attention mechanisms for AI agents.
    """

    def __init__(self, dim: int = 64, num_heads: int = 4):
        self._dim = dim
        self._num_heads = num_heads
        self._self_attention = SelfAttention(dim)
        self._cross_attention = CrossAttention(dim)
        self._multi_head = MultiHeadAttention(dim, num_heads)
        self._causal_attention = CausalAttention(dim)
        self._sparse_attention = SparseAttention(dim, window_size=5)
        self._linear_attention = LinearAttention(dim)

    def self_attend(
        self,
        vectors: List[List[float]],
        mask: Optional[List[List[bool]]] = None
    ) -> AttentionOutput:
        """Apply self-attention."""
        return self._self_attention.forward(vectors, mask)

    def cross_attend(
        self,
        query_vectors: List[List[float]],
        key_value_vectors: List[List[float]]
    ) -> AttentionOutput:
        """Apply cross-attention."""
        return self._cross_attention.forward(query_vectors, key_value_vectors)

    def multi_head_attend(
        self,
        vectors: List[List[float]],
        mask: Optional[List[List[bool]]] = None
    ) -> MultiHeadOutput:
        """Apply multi-head attention."""
        return self._multi_head.forward(vectors, mask)

    def causal_attend(
        self,
        vectors: List[List[float]]
    ) -> AttentionOutput:
        """Apply causal attention."""
        return self._causal_attention.forward(vectors)

    def sparse_attend(
        self,
        queries: List[List[float]],
        keys: List[List[float]],
        values: List[List[float]]
    ) -> AttentionOutput:
        """Apply sparse attention."""
        return self._sparse_attention.forward(queries, keys, values)

    def linear_attend(
        self,
        queries: List[List[float]],
        keys: List[List[float]],
        values: List[List[float]]
    ) -> AttentionOutput:
        """Apply linear attention."""
        return self._linear_attention.forward(queries, keys, values)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Attention Engine."""
    print("=" * 70)
    print("BAEL - ATTENTION ENGINE DEMO")
    print("Advanced Attention Mechanisms for AI Agents")
    print("=" * 70)
    print()

    dim = 16
    num_heads = 4
    seq_len = 5

    engine = AttentionEngine(dim=dim, num_heads=num_heads)

    def random_vectors(n: int, d: int) -> List[List[float]]:
        return [[random.gauss(0, 1) for _ in range(d)] for _ in range(n)]

    vectors = random_vectors(seq_len, dim)

    # 1. Self-Attention
    print("1. SELF-ATTENTION:")
    print("-" * 40)
    result = engine.self_attend(vectors)
    print(f"   Input: {seq_len} vectors of dim {dim}")
    print(f"   Output: {len(result.output_vectors)} vectors")
    print(f"   Attention weights shape: {len(result.attention_weights.weights)}x{len(result.attention_weights.weights[0])}")
    print()

    # 2. Cross-Attention
    print("2. CROSS-ATTENTION:")
    print("-" * 40)
    query_vecs = random_vectors(3, dim)
    kv_vecs = random_vectors(7, dim)
    result = engine.cross_attend(query_vecs, kv_vecs)
    print(f"   Queries: 3 vectors")
    print(f"   Keys/Values: 7 vectors")
    print(f"   Output: {len(result.output_vectors)} vectors")
    print()

    # 3. Multi-Head Attention
    print("3. MULTI-HEAD ATTENTION:")
    print("-" * 40)
    result = engine.multi_head_attend(vectors)
    print(f"   Num heads: {num_heads}")
    print(f"   Head dim: {dim // num_heads}")
    print(f"   Output: {len(result.combined_output)} vectors")
    print(f"   Head outputs: {len(result.head_outputs)}")
    print()

    # 4. Causal Attention
    print("4. CAUSAL ATTENTION:")
    print("-" * 40)
    result = engine.causal_attend(vectors)
    print(f"   Type: {result.attention_type.value}")
    print(f"   Output: {len(result.output_vectors)} vectors")

    print("   Causal mask pattern (position can attend to):")
    for i, row in enumerate(result.attention_weights.weights):
        attended = [j for j, w in enumerate(row) if w > 0.01]
        print(f"      Position {i}: {attended}")
    print()

    # 5. Sparse Attention
    print("5. SPARSE ATTENTION:")
    print("-" * 40)
    queries = random_vectors(seq_len, dim)
    keys = random_vectors(seq_len, dim)
    values = random_vectors(seq_len, dim)
    result = engine.sparse_attend(queries, keys, values)
    print(f"   Window size: 5")
    print(f"   Type: {result.attention_type.value}")
    print(f"   Output: {len(result.output_vectors)} vectors")
    print()

    # 6. Linear Attention
    print("6. LINEAR ATTENTION:")
    print("-" * 40)
    result = engine.linear_attend(queries, keys, values)
    print(f"   Type: {result.attention_type.value}")
    print(f"   Output: {len(result.output_vectors)} vectors")
    print(f"   Complexity: O(n) vs O(n²) for standard")
    print()

    # 7. Softmax Demo
    print("7. SOFTMAX NORMALIZATION:")
    print("-" * 40)
    raw_scores = [2.0, 1.0, 0.5, -1.0, 3.0]
    normalized = Softmax.apply(raw_scores)
    print(f"   Raw scores: {raw_scores}")
    print(f"   Normalized: {[f'{w:.3f}' for w in normalized]}")
    print(f"   Sum: {sum(normalized):.3f}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Attention Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
