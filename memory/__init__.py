"""
BAEL - Memory System
Comprehensive multi-layer memory architecture.

This package provides five specialized memory types:
- Episodic: Autobiographical experiences and events
- Semantic: Concepts, facts, and knowledge
- Procedural: Skills, procedures, and how-to knowledge
- Working: Active context and attention management
- Vector: Embedding-based semantic similarity storage
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("BAEL.Memory")

# Lazy imports to avoid circular dependencies
_episodic = None
_semantic = None
_procedural = None
_working = None
_vector = None


def get_episodic_memory():
    """Get episodic memory module."""
    global _episodic
    if _episodic is None:
        from . import episodic as _episodic
    return _episodic


def get_semantic_memory():
    """Get semantic memory module."""
    global _semantic
    if _semantic is None:
        from . import semantic as _semantic
    return _semantic


def get_procedural_memory():
    """Get procedural memory module."""
    global _procedural
    if _procedural is None:
        from . import procedural as _procedural
    return _procedural


def get_working_memory():
    """Get working memory module."""
    global _working
    if _working is None:
        from . import working as _working
    return _working


def get_vector_memory():
    """Get vector memory module."""
    global _vector
    if _vector is None:
        from . import vector as _vector
    return _vector


class UnifiedMemory:
    """
    Unified interface to all memory systems.

    Provides:
    - Centralized memory access
    - Cross-memory operations
    - Memory statistics
    - Lifecycle management
    """

    def __init__(
        self,
        base_path: str = "memory",
        working_capacity: int = 50,
        vector_dimension: int = 1536
    ):
        self.base_path = base_path
        self.working_capacity = working_capacity
        self.vector_dimension = vector_dimension

        self._episodic = None
        self._semantic = None
        self._procedural = None
        self._working = None
        self._vector = None

        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all memory systems."""
        if self._initialized:
            return

        # Initialize episodic
        ep = get_episodic_memory()
        self._episodic = ep.EpisodicMemoryManager(
            ep.EpisodicMemoryStore(f"{self.base_path}/episodic/episodes.db")
        )
        await self._episodic.initialize()

        # Initialize semantic
        sem = get_semantic_memory()
        self._semantic = sem.SemanticMemoryManager(
            sem.SemanticMemoryStore(f"{self.base_path}/semantic/concepts.db")
        )
        await self._semantic.initialize()

        # Initialize procedural
        proc = get_procedural_memory()
        self._procedural = proc.ProceduralMemoryManager(
            proc.ProceduralMemoryStore(f"{self.base_path}/procedural/procedures.db")
        )
        await self._procedural.initialize()

        # Initialize working
        work = get_working_memory()
        self._working = work.WorkingMemoryManager(
            work.WorkingMemoryStore(capacity=self.working_capacity)
        )

        # Initialize vector
        vec = get_vector_memory()
        self._vector = vec.VectorMemoryManager(
            vec.VectorMemoryStore(
                f"{self.base_path}/vector/vectors.db",
                dimension=self.vector_dimension
            )
        )
        await self._vector.initialize()

        self._initialized = True
        logger.info("Unified memory system initialized")

    @property
    def episodic(self):
        """Access episodic memory."""
        if not self._episodic:
            raise RuntimeError("Memory not initialized")
        return self._episodic

    @property
    def semantic(self):
        """Access semantic memory."""
        if not self._semantic:
            raise RuntimeError("Memory not initialized")
        return self._semantic

    @property
    def procedural(self):
        """Access procedural memory."""
        if not self._procedural:
            raise RuntimeError("Memory not initialized")
        return self._procedural

    @property
    def working(self):
        """Access working memory."""
        if not self._working:
            raise RuntimeError("Memory not initialized")
        return self._working

    @property
    def vector(self):
        """Access vector memory."""
        if not self._vector:
            raise RuntimeError("Memory not initialized")
        return self._vector

    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics from all memory systems."""
        stats = {}

        if self._episodic:
            stats["episodic"] = await self._episodic.store.get_stats()

        if self._semantic:
            stats["semantic"] = await self._semantic.store.get_stats()

        if self._procedural:
            stats["procedural"] = await self._procedural.store.get_stats()

        if self._working:
            stats["working"] = self._working.get_stats()

        if self._vector:
            stats["vector"] = await self._vector.get_stats()

        return stats

    async def consolidate(self) -> Dict[str, int]:
        """Run consolidation across memory systems."""
        results = {}

        if self._episodic:
            results["episodic_consolidated"] = await self._episodic.store.consolidate()

        return results

    def reset_working(self) -> None:
        """Reset working memory."""
        if self._working:
            self._working.exit_context()


__all__ = [
    "get_episodic_memory",
    "get_semantic_memory",
    "get_procedural_memory",
    "get_working_memory",
    "get_vector_memory",
    "UnifiedMemory"
]
