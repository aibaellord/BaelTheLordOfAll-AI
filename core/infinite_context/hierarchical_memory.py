"""
⚡ HIERARCHICAL MEMORY ⚡
========================
Multi-level memory system.

Features:
- Working memory buffer
- Short-term memory
- Long-term memory
- Memory consolidation
"""

import math
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict, deque
import uuid


class MemoryLevel(Enum):
    """Memory hierarchy levels"""
    IMMEDIATE = 0      # Current focus
    WORKING = 1        # Active processing
    SHORT_TERM = 2     # Recent memory
    LONG_TERM = 3      # Consolidated memory
    PERMANENT = 4      # Core knowledge


@dataclass
class MemoryChunk:
    """Chunk of memory content"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: Any = None

    # Level in hierarchy
    level: MemoryLevel = MemoryLevel.WORKING

    # Strength and decay
    strength: float = 1.0
    decay_rate: float = 0.01

    # Timestamps
    created: datetime = field(default_factory=datetime.now)
    last_access: datetime = field(default_factory=datetime.now)
    last_rehearsal: datetime = field(default_factory=datetime.now)

    # Connections
    associations: Dict[str, float] = field(default_factory=dict)

    # Embedding
    embedding: Optional[np.ndarray] = None

    # Compression
    is_compressed: bool = False
    original_size: int = 0

    def access(self):
        """Access memory, strengthening it"""
        self.last_access = datetime.now()
        self.strength = min(1.0, self.strength + 0.1)

    def decay(self, time_delta: float):
        """Apply time-based decay"""
        self.strength *= math.exp(-self.decay_rate * time_delta)

    def rehearse(self):
        """Rehearse memory to strengthen"""
        self.last_rehearsal = datetime.now()
        self.strength = min(1.0, self.strength + 0.2)
        self.decay_rate *= 0.9  # Rehearsal reduces decay


@dataclass
class MemoryNode:
    """Node in memory graph"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    chunks: List[str] = field(default_factory=list)  # Chunk IDs

    # Hierarchical structure
    parent_id: Optional[str] = None
    child_ids: List[str] = field(default_factory=list)

    # Summary/abstraction
    summary: Optional[str] = None
    abstraction_level: int = 0

    # Metadata
    topic: str = ""
    importance: float = 0.5


class HierarchicalMemory:
    """
    Multi-level hierarchical memory system.

    Implements memory consolidation across levels.
    """

    def __init__(
        self,
        working_capacity: int = 7,
        short_term_capacity: int = 100,
        long_term_capacity: int = 10000
    ):
        # Capacities
        self.capacities = {
            MemoryLevel.IMMEDIATE: 1,
            MemoryLevel.WORKING: working_capacity,
            MemoryLevel.SHORT_TERM: short_term_capacity,
            MemoryLevel.LONG_TERM: long_term_capacity,
            MemoryLevel.PERMANENT: float('inf')
        }

        # Storage
        self.chunks: Dict[str, MemoryChunk] = {}
        self.by_level: Dict[MemoryLevel, Set[str]] = {
            level: set() for level in MemoryLevel
        }

        # Hierarchical nodes
        self.nodes: Dict[str, MemoryNode] = {}

        # Index
        self.by_topic: Dict[str, Set[str]] = defaultdict(set)

    def store(
        self,
        content: Any,
        level: MemoryLevel = MemoryLevel.WORKING,
        embedding: np.ndarray = None,
        topic: str = ""
    ) -> MemoryChunk:
        """Store content in memory"""
        chunk = MemoryChunk(
            content=content,
            level=level,
            embedding=embedding
        )

        self.chunks[chunk.id] = chunk
        self.by_level[level].add(chunk.id)

        if topic:
            self.by_topic[topic].add(chunk.id)

        # Enforce capacity
        self._enforce_capacity(level)

        return chunk

    def retrieve(
        self,
        chunk_id: str
    ) -> Optional[MemoryChunk]:
        """Retrieve memory chunk"""
        chunk = self.chunks.get(chunk_id)
        if chunk:
            chunk.access()
        return chunk

    def search(
        self,
        query_embedding: np.ndarray,
        levels: List[MemoryLevel] = None,
        top_k: int = 10
    ) -> List[Tuple[MemoryChunk, float]]:
        """Search memory by similarity"""
        levels = levels or list(MemoryLevel)

        results = []

        for level in levels:
            for chunk_id in self.by_level[level]:
                chunk = self.chunks.get(chunk_id)
                if chunk and chunk.embedding is not None:
                    similarity = np.dot(query_embedding, chunk.embedding) / (
                        np.linalg.norm(query_embedding) *
                        np.linalg.norm(chunk.embedding) + 1e-10
                    )
                    # Weight by strength
                    weighted_sim = similarity * chunk.strength
                    results.append((chunk, weighted_sim))

        results.sort(key=lambda x: -x[1])
        return results[:top_k]

    def promote(self, chunk_id: str):
        """Promote chunk to higher level"""
        chunk = self.chunks.get(chunk_id)
        if not chunk:
            return

        current_level = chunk.level

        # Find next level
        levels = list(MemoryLevel)
        current_idx = levels.index(current_level)

        if current_idx < len(levels) - 1:
            new_level = levels[current_idx + 1]

            self.by_level[current_level].discard(chunk_id)
            self.by_level[new_level].add(chunk_id)
            chunk.level = new_level

    def demote(self, chunk_id: str):
        """Demote chunk to lower level"""
        chunk = self.chunks.get(chunk_id)
        if not chunk:
            return

        current_level = chunk.level

        # Find previous level
        levels = list(MemoryLevel)
        current_idx = levels.index(current_level)

        if current_idx > 0:
            new_level = levels[current_idx - 1]

            self.by_level[current_level].discard(chunk_id)
            self.by_level[new_level].add(chunk_id)
            chunk.level = new_level

    def forget(self, chunk_id: str):
        """Remove chunk from memory"""
        chunk = self.chunks.get(chunk_id)
        if chunk:
            self.by_level[chunk.level].discard(chunk_id)
            del self.chunks[chunk_id]

    def _enforce_capacity(self, level: MemoryLevel):
        """Enforce capacity limits"""
        capacity = self.capacities[level]

        while len(self.by_level[level]) > capacity:
            # Remove weakest
            weakest_id = None
            weakest_strength = float('inf')

            for chunk_id in self.by_level[level]:
                chunk = self.chunks.get(chunk_id)
                if chunk and chunk.strength < weakest_strength:
                    weakest_strength = chunk.strength
                    weakest_id = chunk_id

            if weakest_id:
                # Either demote or forget
                if level.value > 0:
                    self.demote(weakest_id)
                else:
                    self.forget(weakest_id)

    def decay_all(self, time_delta: float = 1.0):
        """Apply decay to all memories"""
        for chunk in self.chunks.values():
            chunk.decay(time_delta)

        # Forget very weak memories
        to_forget = [
            cid for cid, chunk in self.chunks.items()
            if chunk.strength < 0.01 and chunk.level.value < MemoryLevel.PERMANENT.value
        ]

        for chunk_id in to_forget:
            self.forget(chunk_id)

    def create_node(
        self,
        chunk_ids: List[str],
        topic: str,
        summary: str = None
    ) -> MemoryNode:
        """Create hierarchical node grouping chunks"""
        node = MemoryNode(
            chunks=chunk_ids,
            topic=topic,
            summary=summary
        )

        self.nodes[node.id] = node
        return node


class MemoryConsolidation:
    """
    Memory consolidation process.

    Consolidates working memory to long-term.
    """

    def __init__(self, memory: HierarchicalMemory):
        self.memory = memory

        # Consolidation thresholds
        self.rehearsal_threshold = 3
        self.strength_threshold = 0.7
        self.age_threshold = 3600  # 1 hour

    def consolidate(self):
        """Run consolidation process"""
        now = datetime.now()

        # Check working and short-term memories
        for level in [MemoryLevel.WORKING, MemoryLevel.SHORT_TERM]:
            for chunk_id in list(self.memory.by_level[level]):
                chunk = self.memory.chunks.get(chunk_id)
                if not chunk:
                    continue

                # Check consolidation criteria
                should_consolidate = False

                # High strength
                if chunk.strength >= self.strength_threshold:
                    should_consolidate = True

                # Multiple rehearsals
                rehearsal_count = (now - chunk.created).total_seconds() / 3600
                if rehearsal_count >= self.rehearsal_threshold:
                    should_consolidate = True

                if should_consolidate:
                    self.memory.promote(chunk_id)

    def integrate(
        self,
        new_chunk_id: str,
        related_chunk_ids: List[str]
    ):
        """Integrate new memory with existing ones"""
        new_chunk = self.memory.chunks.get(new_chunk_id)
        if not new_chunk:
            return

        for related_id in related_chunk_ids:
            related = self.memory.chunks.get(related_id)
            if related:
                # Create bidirectional association
                similarity = 0.5  # Default

                if new_chunk.embedding is not None and related.embedding is not None:
                    similarity = np.dot(new_chunk.embedding, related.embedding) / (
                        np.linalg.norm(new_chunk.embedding) *
                        np.linalg.norm(related.embedding) + 1e-10
                    )

                new_chunk.associations[related_id] = similarity
                related.associations[new_chunk_id] = similarity


class WorkingMemoryBuffer:
    """
    Working memory buffer for active processing.
    """

    def __init__(self, capacity: int = 7):
        self.capacity = capacity
        self.buffer: deque = deque(maxlen=capacity)

        # Attention weights
        self.attention: Dict[str, float] = {}

        # Focus
        self.focus_id: Optional[str] = None

    def push(self, item: MemoryChunk):
        """Push item to buffer"""
        self.buffer.append(item.id)
        self.attention[item.id] = 1.0

        # Normalize attention
        total = sum(self.attention.values())
        self.attention = {k: v / total for k, v in self.attention.items()}

    def pop(self) -> Optional[str]:
        """Pop oldest item"""
        if self.buffer:
            item_id = self.buffer.popleft()
            self.attention.pop(item_id, None)
            return item_id
        return None

    def focus(self, item_id: str):
        """Focus attention on item"""
        if item_id in self.attention:
            self.focus_id = item_id
            self.attention[item_id] = 2.0

            # Renormalize
            total = sum(self.attention.values())
            self.attention = {k: v / total for k, v in self.attention.items()}

    def get_attended(self, top_k: int = 3) -> List[str]:
        """Get most attended items"""
        sorted_items = sorted(
            self.attention.items(),
            key=lambda x: -x[1]
        )
        return [item_id for item_id, _ in sorted_items[:top_k]]


# Export all
__all__ = [
    'MemoryLevel',
    'MemoryChunk',
    'MemoryNode',
    'HierarchicalMemory',
    'MemoryConsolidation',
    'WorkingMemoryBuffer',
]
