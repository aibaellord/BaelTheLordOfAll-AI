"""
BAEL - Hierarchical Memory for Long Contexts
Enables handling of 1M+ token contexts through hierarchical organization.
"""

import asyncio
import hashlib
import json
import logging
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.Context.Hierarchical")


class MemoryLevel(Enum):
    """Levels in the memory hierarchy."""
    WORKING = "working"      # Active context (4K-32K tokens)
    SHORT_TERM = "short_term"  # Recent context (32K-128K tokens)
    LONG_TERM = "long_term"   # Indexed past (128K-1M tokens)
    ARCHIVE = "archive"       # Compressed archive (1M+ tokens)


class ChunkType(Enum):
    """Types of memory chunks."""
    CONVERSATION = "conversation"
    CODE = "code"
    DOCUMENT = "document"
    TOOL_OUTPUT = "tool_output"
    SUMMARY = "summary"
    METADATA = "metadata"


@dataclass
class MemoryChunk:
    """A chunk of memory at any level."""
    id: str
    content: str
    chunk_type: ChunkType
    level: MemoryLevel
    tokens: int
    importance: float  # 0-1, higher = more important
    created_at: float
    last_accessed: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    summary: Optional[str] = None
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)


@dataclass
class HierarchyConfig:
    """Configuration for hierarchical memory."""
    working_limit: int = 16000    # Tokens in working memory
    short_term_limit: int = 64000  # Tokens in short-term
    long_term_limit: int = 500000  # Tokens in long-term
    archive_limit: int = 5000000   # Tokens in archive

    compression_ratio: float = 0.3  # Target compression ratio
    min_importance: float = 0.2    # Minimum importance to keep

    summary_chunk_size: int = 2000  # Tokens to summarize at once
    retrieval_top_k: int = 10       # Chunks to retrieve


class HierarchicalMemory:
    """
    Hierarchical memory system for handling extremely long contexts.

    Features:
    - Four-level memory hierarchy
    - Automatic promotion/demotion
    - Importance-based retention
    - Semantic search across levels
    - Progressive summarization
    """

    def __init__(
        self,
        config: Optional[HierarchyConfig] = None,
        storage_path: Optional[str] = None
    ):
        self.config = config or HierarchyConfig()
        self._storage_path = Path(storage_path) if storage_path else None

        # Memory at each level
        self._memory: Dict[MemoryLevel, Dict[str, MemoryChunk]] = {
            level: {} for level in MemoryLevel
        }

        # Token counts per level
        self._token_counts: Dict[MemoryLevel, int] = {
            level: 0 for level in MemoryLevel
        }

        # Limits per level
        self._limits = {
            MemoryLevel.WORKING: self.config.working_limit,
            MemoryLevel.SHORT_TERM: self.config.short_term_limit,
            MemoryLevel.LONG_TERM: self.config.long_term_limit,
            MemoryLevel.ARCHIVE: self.config.archive_limit
        }

        self._embedding_cache = None
        self._llm = None

        self._load()

    def _load(self) -> None:
        """Load memory from disk."""
        if not self._storage_path:
            return

        memory_file = self._storage_path / "hierarchical_memory.json"
        if memory_file.exists():
            try:
                with open(memory_file, "r") as f:
                    data = json.load(f)

                    for level_name, chunks in data.get("memory", {}).items():
                        level = MemoryLevel(level_name)

                        for chunk_data in chunks:
                            chunk = MemoryChunk(
                                id=chunk_data["id"],
                                content=chunk_data["content"],
                                chunk_type=ChunkType(chunk_data["chunk_type"]),
                                level=level,
                                tokens=chunk_data["tokens"],
                                importance=chunk_data["importance"],
                                created_at=chunk_data["created_at"],
                                last_accessed=chunk_data["last_accessed"],
                                metadata=chunk_data.get("metadata", {}),
                                summary=chunk_data.get("summary"),
                                parent_id=chunk_data.get("parent_id"),
                                children_ids=chunk_data.get("children_ids", [])
                            )

                            self._memory[level][chunk.id] = chunk
                            self._token_counts[level] += chunk.tokens

                    logger.info(f"Loaded hierarchical memory")

            except Exception as e:
                logger.warning(f"Failed to load memory: {e}")

    def _save(self) -> None:
        """Save memory to disk."""
        if not self._storage_path:
            return

        self._storage_path.mkdir(parents=True, exist_ok=True)
        memory_file = self._storage_path / "hierarchical_memory.json"

        try:
            data = {
                "memory": {
                    level.value: [
                        {
                            "id": c.id,
                            "content": c.content,
                            "chunk_type": c.chunk_type.value,
                            "tokens": c.tokens,
                            "importance": c.importance,
                            "created_at": c.created_at,
                            "last_accessed": c.last_accessed,
                            "metadata": c.metadata,
                            "summary": c.summary,
                            "parent_id": c.parent_id,
                            "children_ids": c.children_ids
                        }
                        for c in chunks.values()
                    ]
                    for level, chunks in self._memory.items()
                },
                "saved_at": time.time()
            }

            with open(memory_file, "w") as f:
                json.dump(data, f)

        except Exception as e:
            logger.error(f"Failed to save memory: {e}")

    async def _get_llm(self):
        """Lazy load LLM."""
        if self._llm is None:
            try:
                from core.llm import get_provider
                self._llm = get_provider()
            except ImportError:
                pass
        return self._llm

    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding for text."""
        if self._embedding_cache is None:
            try:
                from core.cache.semantic.embedding_cache import \
                    get_embedding_cache
                self._embedding_cache = get_embedding_cache()
            except ImportError:
                return None

        return await self._embedding_cache.get(text)

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        # Rough estimate: ~4 chars per token
        return len(text) // 4

    def _generate_id(self, content: str) -> str:
        """Generate unique ID for content."""
        return hashlib.sha256(
            f"{content[:100]}:{time.time()}".encode()
        ).hexdigest()[:16]

    async def add(
        self,
        content: str,
        chunk_type: ChunkType = ChunkType.CONVERSATION,
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add content to memory.

        Args:
            content: Content to store
            chunk_type: Type of content
            importance: Importance score (0-1)
            metadata: Optional metadata

        Returns:
            Chunk ID
        """
        tokens = self._estimate_tokens(content)
        chunk_id = self._generate_id(content)

        chunk = MemoryChunk(
            id=chunk_id,
            content=content,
            chunk_type=chunk_type,
            level=MemoryLevel.WORKING,
            tokens=tokens,
            importance=importance,
            created_at=time.time(),
            last_accessed=time.time(),
            metadata=metadata or {}
        )

        # Add to working memory
        self._memory[MemoryLevel.WORKING][chunk_id] = chunk
        self._token_counts[MemoryLevel.WORKING] += tokens

        # Manage memory limits
        await self._manage_limits()

        return chunk_id

    async def _manage_limits(self) -> None:
        """Manage memory limits by promoting/demoting chunks."""
        # Start from working memory and cascade down
        for level in [MemoryLevel.WORKING, MemoryLevel.SHORT_TERM, MemoryLevel.LONG_TERM]:
            while self._token_counts[level] > self._limits[level]:
                await self._demote_chunk(level)

    async def _demote_chunk(self, from_level: MemoryLevel) -> None:
        """Demote least important chunk to next level."""
        chunks = self._memory[from_level]

        if not chunks:
            return

        # Find least important chunk
        least_important = min(
            chunks.values(),
            key=lambda c: (c.importance, c.last_accessed)
        )

        # Determine target level
        level_order = list(MemoryLevel)
        current_idx = level_order.index(from_level)

        if current_idx >= len(level_order) - 1:
            # Already at archive, remove if below threshold
            if least_important.importance < self.config.min_importance:
                self._remove_chunk(least_important.id, from_level)
            return

        next_level = level_order[current_idx + 1]

        # Compress if moving to long-term or archive
        if next_level in [MemoryLevel.LONG_TERM, MemoryLevel.ARCHIVE]:
            compressed = await self._compress_chunk(least_important)
            if compressed:
                least_important = compressed

        # Move to next level
        self._remove_chunk(least_important.id, from_level)

        least_important.level = next_level
        self._memory[next_level][least_important.id] = least_important
        self._token_counts[next_level] += least_important.tokens

    async def _compress_chunk(
        self,
        chunk: MemoryChunk
    ) -> Optional[MemoryChunk]:
        """Compress a chunk through summarization."""
        llm = await self._get_llm()

        if not llm or chunk.tokens < 100:
            return chunk

        # Already has summary
        if chunk.summary and len(chunk.summary) < len(chunk.content) * self.config.compression_ratio:
            compressed = MemoryChunk(
                id=chunk.id,
                content=chunk.summary,
                chunk_type=ChunkType.SUMMARY,
                level=chunk.level,
                tokens=self._estimate_tokens(chunk.summary),
                importance=chunk.importance,
                created_at=chunk.created_at,
                last_accessed=chunk.last_accessed,
                metadata={**chunk.metadata, "original_tokens": chunk.tokens},
                summary=None,
                parent_id=chunk.parent_id,
                children_ids=chunk.children_ids
            )
            return compressed

        # Generate summary
        try:
            prompt = f"""Summarize this content concisely, preserving key information:

{chunk.content[:4000]}

Summary:"""

            summary = await llm.generate(prompt, temperature=0.3, max_tokens=500)

            compressed = MemoryChunk(
                id=chunk.id,
                content=summary.strip(),
                chunk_type=ChunkType.SUMMARY,
                level=chunk.level,
                tokens=self._estimate_tokens(summary),
                importance=chunk.importance,
                created_at=chunk.created_at,
                last_accessed=chunk.last_accessed,
                metadata={**chunk.metadata, "original_tokens": chunk.tokens},
                summary=None,
                parent_id=chunk.parent_id,
                children_ids=chunk.children_ids
            )

            return compressed

        except Exception as e:
            logger.warning(f"Compression failed: {e}")
            return chunk

    def _remove_chunk(self, chunk_id: str, level: MemoryLevel) -> None:
        """Remove a chunk from a level."""
        if chunk_id in self._memory[level]:
            chunk = self._memory[level][chunk_id]
            self._token_counts[level] -= chunk.tokens
            del self._memory[level][chunk_id]

    async def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        levels: Optional[List[MemoryLevel]] = None,
        min_importance: float = 0.0
    ) -> List[MemoryChunk]:
        """
        Retrieve relevant chunks for a query.

        Args:
            query: Query to search for
            top_k: Number of results
            levels: Levels to search
            min_importance: Minimum importance threshold

        Returns:
            List of relevant chunks
        """
        top_k = top_k or self.config.retrieval_top_k
        levels = levels or list(MemoryLevel)

        query_embedding = await self._get_embedding(query)

        candidates = []

        for level in levels:
            for chunk in self._memory[level].values():
                if chunk.importance < min_importance:
                    continue

                # Calculate relevance
                score = await self._calculate_relevance(
                    query, query_embedding, chunk
                )

                candidates.append((chunk, score))

        # Sort by relevance
        candidates.sort(key=lambda x: x[1], reverse=True)

        # Update access times and return
        results = []
        for chunk, _ in candidates[:top_k]:
            chunk.last_accessed = time.time()
            results.append(chunk)

        return results

    async def _calculate_relevance(
        self,
        query: str,
        query_embedding: Optional[List[float]],
        chunk: MemoryChunk
    ) -> float:
        """Calculate relevance score for a chunk."""
        score = 0.0

        # Keyword matching
        query_words = set(query.lower().split())
        chunk_words = set(chunk.content.lower().split())
        overlap = len(query_words & chunk_words)
        keyword_score = overlap / max(len(query_words), 1)
        score += keyword_score * 0.3

        # Semantic similarity
        if query_embedding:
            chunk_embedding = await self._get_embedding(chunk.content[:500])

            if chunk_embedding:
                from core.cache.semantic.embedding_cache import \
                    get_embedding_cache
                cache = get_embedding_cache()
                sim = cache.cosine_similarity(query_embedding, chunk_embedding)
                score += sim * 0.5

        # Recency bonus
        age = time.time() - chunk.last_accessed
        recency = math.exp(-age / 86400)  # Decay over 24 hours
        score += recency * 0.1

        # Importance bonus
        score += chunk.importance * 0.1

        return score

    async def get_context(
        self,
        query: str,
        max_tokens: int = 8000
    ) -> str:
        """
        Get relevant context for a query within token limit.

        Args:
            query: Query to build context for
            max_tokens: Maximum tokens to return

        Returns:
            Context string
        """
        chunks = await self.retrieve(query, top_k=20)

        context_parts = []
        current_tokens = 0

        for chunk in chunks:
            if current_tokens + chunk.tokens > max_tokens:
                break

            context_parts.append(chunk.content)
            current_tokens += chunk.tokens

        return "\n\n---\n\n".join(context_parts)

    def get_working_memory(self) -> List[MemoryChunk]:
        """Get all chunks in working memory."""
        return list(self._memory[MemoryLevel.WORKING].values())

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return {
            "levels": {
                level.value: {
                    "chunks": len(self._memory[level]),
                    "tokens": self._token_counts[level],
                    "limit": self._limits[level],
                    "utilization": self._token_counts[level] / self._limits[level]
                }
                for level in MemoryLevel
            },
            "total_chunks": sum(len(m) for m in self._memory.values()),
            "total_tokens": sum(self._token_counts.values())
        }

    def save(self) -> None:
        """Force save to disk."""
        self._save()

    def clear(self, level: Optional[MemoryLevel] = None) -> None:
        """Clear memory."""
        if level:
            self._memory[level].clear()
            self._token_counts[level] = 0
        else:
            for lvl in MemoryLevel:
                self._memory[lvl].clear()
                self._token_counts[lvl] = 0


# Global instance
_hierarchical_memory: Optional[HierarchicalMemory] = None


def get_hierarchical_memory(
    config: Optional[HierarchyConfig] = None,
    storage_path: Optional[str] = None
) -> HierarchicalMemory:
    """Get or create hierarchical memory instance."""
    global _hierarchical_memory
    if _hierarchical_memory is None or config is not None:
        _hierarchical_memory = HierarchicalMemory(config, storage_path)
    return _hierarchical_memory
