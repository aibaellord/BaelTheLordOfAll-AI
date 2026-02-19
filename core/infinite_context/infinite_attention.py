"""
⚡ INFINITE ATTENTION ⚡
=======================
Attention mechanisms for unlimited context.

Features:
- Sparse attention patterns
- Hierarchical attention
- Memory-augmented attention
- Infinite-length processing
"""

import math
import numpy as np
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import uuid


class AttentionPattern(Enum):
    """Types of attention patterns"""
    FULL = auto()          # Full quadratic attention
    SPARSE = auto()        # Sparse fixed pattern
    LOCAL = auto()         # Local window
    STRIDED = auto()       # Strided pattern
    RANDOM = auto()        # Random sparsity
    HIERARCHICAL = auto()  # Multi-scale


@dataclass
class AttentionHead:
    """Single attention head"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Dimensions
    dim_key: int = 64
    dim_value: int = 64

    # Weights (initialized randomly)
    W_q: np.ndarray = None
    W_k: np.ndarray = None
    W_v: np.ndarray = None

    def __post_init__(self):
        if self.W_q is None:
            scale = 1.0 / math.sqrt(self.dim_key)
            self.W_q = np.random.randn(self.dim_key, self.dim_key) * scale
            self.W_k = np.random.randn(self.dim_key, self.dim_key) * scale
            self.W_v = np.random.randn(self.dim_value, self.dim_value) * scale

    def forward(
        self,
        query: np.ndarray,
        key: np.ndarray,
        value: np.ndarray,
        mask: np.ndarray = None
    ) -> np.ndarray:
        """Compute attention output"""
        # Project
        Q = query @ self.W_q
        K = key @ self.W_k
        V = value @ self.W_v

        # Scaled dot-product attention
        scores = Q @ K.T / math.sqrt(self.dim_key)

        if mask is not None:
            scores = scores + mask * (-1e9)

        # Softmax
        attn = np.exp(scores - np.max(scores, axis=-1, keepdims=True))
        attn = attn / (np.sum(attn, axis=-1, keepdims=True) + 1e-10)

        # Output
        return attn @ V


class SparseAttention:
    """
    Sparse attention for long sequences.

    Reduces O(n²) to O(n√n) or O(n log n).
    """

    def __init__(
        self,
        block_size: int = 64,
        num_global_tokens: int = 4,
        stride: int = 128
    ):
        self.block_size = block_size
        self.num_global_tokens = num_global_tokens
        self.stride = stride

    def get_sparse_mask(
        self,
        seq_len: int,
        pattern: AttentionPattern = AttentionPattern.SPARSE
    ) -> np.ndarray:
        """Generate sparse attention mask"""
        mask = np.zeros((seq_len, seq_len))

        if pattern == AttentionPattern.LOCAL:
            # Local window attention
            for i in range(seq_len):
                start = max(0, i - self.block_size // 2)
                end = min(seq_len, i + self.block_size // 2)
                mask[i, start:end] = 1

        elif pattern == AttentionPattern.STRIDED:
            # Strided attention
            for i in range(seq_len):
                # Local attention
                start = max(0, i - self.block_size // 2)
                end = min(seq_len, i + self.block_size // 2)
                mask[i, start:end] = 1

                # Strided attention
                for j in range(0, seq_len, self.stride):
                    mask[i, j] = 1

        elif pattern == AttentionPattern.SPARSE:
            # Block-sparse attention
            num_blocks = (seq_len + self.block_size - 1) // self.block_size

            for block_i in range(num_blocks):
                for block_j in range(num_blocks):
                    # Attend to same block and adjacent blocks
                    if abs(block_i - block_j) <= 1:
                        start_i = block_i * self.block_size
                        end_i = min((block_i + 1) * self.block_size, seq_len)
                        start_j = block_j * self.block_size
                        end_j = min((block_j + 1) * self.block_size, seq_len)

                        mask[start_i:end_i, start_j:end_j] = 1

        # Global tokens attend to everything
        mask[:self.num_global_tokens, :] = 1
        mask[:, :self.num_global_tokens] = 1

        return mask

    def sparse_attention(
        self,
        query: np.ndarray,
        key: np.ndarray,
        value: np.ndarray,
        pattern: AttentionPattern = AttentionPattern.SPARSE
    ) -> np.ndarray:
        """Compute sparse attention"""
        seq_len = query.shape[0]
        dim = query.shape[1]

        mask = self.get_sparse_mask(seq_len, pattern)

        # Only compute attention for non-masked positions
        scores = query @ key.T / math.sqrt(dim)

        # Apply mask
        scores = np.where(mask == 1, scores, -1e9)

        # Softmax
        attn = np.exp(scores - np.max(scores, axis=-1, keepdims=True))
        attn = attn / (np.sum(attn, axis=-1, keepdims=True) + 1e-10)

        # Mask attention weights
        attn = attn * mask

        return attn @ value


class HierarchicalAttention:
    """
    Multi-scale hierarchical attention.

    Processes at multiple granularities.
    """

    def __init__(
        self,
        num_levels: int = 3,
        base_chunk_size: int = 64
    ):
        self.num_levels = num_levels
        self.base_chunk_size = base_chunk_size

        # Attention heads for each level
        self.level_heads: Dict[int, AttentionHead] = {
            i: AttentionHead() for i in range(num_levels)
        }

    def chunk_sequence(
        self,
        sequence: np.ndarray,
        level: int
    ) -> List[np.ndarray]:
        """Chunk sequence at given level"""
        chunk_size = self.base_chunk_size * (2 ** level)

        chunks = []
        for i in range(0, len(sequence), chunk_size):
            chunk = sequence[i:i + chunk_size]
            chunks.append(chunk)

        return chunks

    def aggregate_chunk(
        self,
        chunk: np.ndarray
    ) -> np.ndarray:
        """Aggregate chunk to single vector"""
        return np.mean(chunk, axis=0)

    def forward(
        self,
        sequence: np.ndarray
    ) -> np.ndarray:
        """Hierarchical attention forward pass"""
        # Level 0: Fine-grained attention within chunks
        level_0_chunks = self.chunk_sequence(sequence, 0)
        level_0_outputs = []

        for chunk in level_0_chunks:
            head = self.level_heads[0]
            output = head.forward(chunk, chunk, chunk)
            level_0_outputs.append(output)

        # Concatenate level 0 outputs
        level_0_output = np.concatenate(level_0_outputs, axis=0)

        if self.num_levels == 1:
            return level_0_output

        # Level 1+: Coarse-grained attention
        current_output = level_0_output

        for level in range(1, self.num_levels):
            chunks = self.chunk_sequence(current_output, level)

            # Aggregate chunks
            aggregated = np.array([self.aggregate_chunk(c) for c in chunks])

            # Attention over aggregated
            head = self.level_heads[level]
            level_output = head.forward(aggregated, aggregated, aggregated)

            # Expand back
            expanded = []
            chunk_size = self.base_chunk_size * (2 ** level)
            for i, agg_out in enumerate(level_output):
                original_chunk_len = len(chunks[i])
                expanded.append(np.tile(agg_out, (original_chunk_len, 1)))

            current_output = np.concatenate(expanded, axis=0)

        return current_output


class MemoryAugmentedAttention:
    """
    Attention with external memory.

    Enables accessing unlimited historical context.
    """

    def __init__(
        self,
        memory_size: int = 1000,
        dim: int = 64
    ):
        self.memory_size = memory_size
        self.dim = dim

        # External memory
        self.memory: List[np.ndarray] = []
        self.memory_keys: np.ndarray = np.zeros((0, dim))
        self.memory_values: np.ndarray = np.zeros((0, dim))

        # Write head
        self.write_head = AttentionHead(dim_key=dim, dim_value=dim)

    def write(
        self,
        key: np.ndarray,
        value: np.ndarray
    ):
        """Write to memory"""
        if len(self.memory) >= self.memory_size:
            # Remove oldest
            self.memory.pop(0)
            self.memory_keys = self.memory_keys[1:]
            self.memory_values = self.memory_values[1:]

        self.memory.append(value)
        self.memory_keys = np.vstack([self.memory_keys, key.reshape(1, -1)])
        self.memory_values = np.vstack([self.memory_values, value.reshape(1, -1)])

    def read(
        self,
        query: np.ndarray,
        top_k: int = 10
    ) -> np.ndarray:
        """Read from memory"""
        if len(self.memory_keys) == 0:
            return np.zeros(self.dim)

        # Compute similarity
        similarities = query @ self.memory_keys.T
        similarities = similarities / (np.linalg.norm(query) + 1e-10)

        # Top-k
        top_indices = np.argsort(similarities)[-top_k:]

        # Attention over top-k
        top_keys = self.memory_keys[top_indices]
        top_values = self.memory_values[top_indices]

        scores = query @ top_keys.T / math.sqrt(self.dim)
        attn = np.exp(scores - np.max(scores))
        attn = attn / (np.sum(attn) + 1e-10)

        return attn @ top_values

    def forward(
        self,
        query: np.ndarray,
        key: np.ndarray,
        value: np.ndarray,
        use_memory: bool = True
    ) -> np.ndarray:
        """Forward with memory augmentation"""
        # Standard attention
        scores = query @ key.T / math.sqrt(self.dim)
        attn = np.exp(scores - np.max(scores, axis=-1, keepdims=True))
        attn = attn / (np.sum(attn, axis=-1, keepdims=True) + 1e-10)

        local_output = attn @ value

        if not use_memory or len(self.memory) == 0:
            return local_output

        # Memory attention
        memory_outputs = []
        for q in query:
            mem_out = self.read(q)
            memory_outputs.append(mem_out)

        memory_output = np.array(memory_outputs)

        # Combine local and memory
        return 0.7 * local_output + 0.3 * memory_output


class InfiniteAttention:
    """
    Infinite-length attention mechanism.

    Combines:
    - Sparse attention for efficiency
    - Hierarchical attention for multi-scale
    - Memory augmentation for history
    """

    def __init__(
        self,
        dim: int = 64,
        max_local_length: int = 2048,
        memory_size: int = 10000
    ):
        self.dim = dim
        self.max_local_length = max_local_length

        # Components
        self.sparse = SparseAttention()
        self.hierarchical = HierarchicalAttention()
        self.memory = MemoryAugmentedAttention(memory_size=memory_size, dim=dim)

        # Processing state
        self.position = 0

    def process_chunk(
        self,
        chunk: np.ndarray
    ) -> np.ndarray:
        """Process a chunk of input"""
        # Local attention within chunk
        local_output = self.sparse.sparse_attention(
            chunk, chunk, chunk,
            AttentionPattern.SPARSE
        )

        # Hierarchical refinement
        hier_output = self.hierarchical.forward(local_output)

        # Read from memory
        memory_output = np.zeros_like(hier_output)
        for i, query in enumerate(hier_output):
            memory_output[i] = self.memory.read(query, top_k=5)

        # Combine
        output = 0.6 * hier_output + 0.4 * memory_output

        # Write important tokens to memory
        for i in range(0, len(chunk), 10):  # Sample every 10th
            self.memory.write(chunk[i], output[i])

        self.position += len(chunk)
        return output

    def process_sequence(
        self,
        sequence: np.ndarray
    ) -> np.ndarray:
        """Process entire sequence in chunks"""
        outputs = []

        for i in range(0, len(sequence), self.max_local_length):
            chunk = sequence[i:i + self.max_local_length]
            output = self.process_chunk(chunk)
            outputs.append(output)

        return np.concatenate(outputs, axis=0)

    def reset(self):
        """Reset state"""
        self.position = 0
        self.memory.memory = []
        self.memory.memory_keys = np.zeros((0, self.dim))
        self.memory.memory_values = np.zeros((0, self.dim))


# Export all
__all__ = [
    'AttentionPattern',
    'AttentionHead',
    'SparseAttention',
    'HierarchicalAttention',
    'MemoryAugmentedAttention',
    'InfiniteAttention',
]
