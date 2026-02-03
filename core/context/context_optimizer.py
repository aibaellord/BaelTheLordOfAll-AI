"""
BAEL - Context Window Optimizer
Optimizes context window usage for maximum efficiency.
"""

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("BAEL.Context.Optimizer")


class OptimizationStrategy(Enum):
    """Context optimization strategies."""
    TRUNCATE_OLD = "truncate_old"
    SUMMARIZE = "summarize"
    PRIORITIZE = "prioritize"
    SLIDING_WINDOW = "sliding_window"
    HYBRID = "hybrid"


class ContentPriority(Enum):
    """Priority levels for content."""
    CRITICAL = 5  # System prompts, core instructions
    HIGH = 4      # Recent user messages
    MEDIUM = 3    # Recent assistant responses
    LOW = 2       # Older context
    MINIMAL = 1   # Can be dropped if needed


@dataclass
class ContextBlock:
    """A block of context content."""
    id: str
    content: str
    priority: ContentPriority
    tokens: int
    created_at: float
    can_compress: bool = True
    compressed_version: Optional[str] = None


@dataclass
class OptimizerConfig:
    """Configuration for context optimizer."""
    target_tokens: int = 8000
    max_tokens: int = 16000
    min_tokens: int = 2000

    strategy: OptimizationStrategy = OptimizationStrategy.HYBRID
    compression_threshold: float = 0.8  # Compress when 80% full
    summary_ratio: float = 0.3  # Target 30% of original size


class ContextWindowOptimizer:
    """
    Optimizes context window usage for LLM calls.

    Features:
    - Priority-based content selection
    - Dynamic compression
    - Sliding window management
    - Token budget optimization
    - Efficient content organization
    """

    def __init__(self, config: Optional[OptimizerConfig] = None):
        self.config = config or OptimizerConfig()

        self._blocks: Dict[str, ContextBlock] = {}
        self._current_tokens = 0
        self._llm = None

        self._stats = {
            "optimizations": 0,
            "compressions": 0,
            "tokens_saved": 0
        }

    async def _get_llm(self):
        """Lazy load LLM."""
        if self._llm is None:
            try:
                from core.llm import get_provider
                self._llm = get_provider()
            except ImportError:
                pass
        return self._llm

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count."""
        return len(text) // 4

    def add_block(
        self,
        block_id: str,
        content: str,
        priority: ContentPriority = ContentPriority.MEDIUM,
        can_compress: bool = True
    ) -> None:
        """
        Add a context block.

        Args:
            block_id: Unique block identifier
            content: Block content
            priority: Content priority
            can_compress: Whether this can be compressed
        """
        tokens = self._estimate_tokens(content)

        block = ContextBlock(
            id=block_id,
            content=content,
            priority=priority,
            tokens=tokens,
            created_at=time.time(),
            can_compress=can_compress
        )

        # Remove old version if exists
        if block_id in self._blocks:
            self._current_tokens -= self._blocks[block_id].tokens

        self._blocks[block_id] = block
        self._current_tokens += tokens

    def remove_block(self, block_id: str) -> bool:
        """Remove a context block."""
        if block_id in self._blocks:
            self._current_tokens -= self._blocks[block_id].tokens
            del self._blocks[block_id]
            return True
        return False

    async def optimize(
        self,
        target_tokens: Optional[int] = None
    ) -> str:
        """
        Optimize and return context string.

        Args:
            target_tokens: Optional target token count

        Returns:
            Optimized context string
        """
        target = target_tokens or self.config.target_tokens

        self._stats["optimizations"] += 1

        if self._current_tokens <= target:
            # Already within budget
            return self._build_context()

        # Need to optimize
        if self.config.strategy == OptimizationStrategy.TRUNCATE_OLD:
            return await self._optimize_truncate(target)

        elif self.config.strategy == OptimizationStrategy.SUMMARIZE:
            return await self._optimize_summarize(target)

        elif self.config.strategy == OptimizationStrategy.PRIORITIZE:
            return await self._optimize_prioritize(target)

        elif self.config.strategy == OptimizationStrategy.SLIDING_WINDOW:
            return await self._optimize_sliding(target)

        else:  # HYBRID
            return await self._optimize_hybrid(target)

    async def _optimize_truncate(self, target: int) -> str:
        """Truncate oldest content first."""
        # Sort by creation time (newest first)
        sorted_blocks = sorted(
            self._blocks.values(),
            key=lambda b: (-b.priority.value, -b.created_at)
        )

        selected = []
        current = 0

        for block in sorted_blocks:
            if current + block.tokens <= target:
                selected.append(block)
                current += block.tokens

        return self._build_from_blocks(selected)

    async def _optimize_summarize(self, target: int) -> str:
        """Summarize lower priority content."""
        # Get blocks that can be compressed
        compressible = [
            b for b in self._blocks.values()
            if b.can_compress and b.priority.value <= ContentPriority.MEDIUM.value
        ]

        # Sort by priority (lowest first)
        compressible.sort(key=lambda b: b.priority.value)

        # Compress until we're under budget
        tokens_to_save = self._current_tokens - target

        for block in compressible:
            if tokens_to_save <= 0:
                break

            compressed = await self._compress_block(block)
            if compressed:
                saved = block.tokens - compressed.tokens
                tokens_to_save -= saved
                self._stats["tokens_saved"] += saved
                self._stats["compressions"] += 1

        return self._build_context()

    async def _optimize_prioritize(self, target: int) -> str:
        """Select by priority until budget exhausted."""
        # Sort by priority (highest first), then recency
        sorted_blocks = sorted(
            self._blocks.values(),
            key=lambda b: (b.priority.value, b.created_at),
            reverse=True
        )

        selected = []
        current = 0

        for block in sorted_blocks:
            if current + block.tokens <= target:
                selected.append(block)
                current += block.tokens

        return self._build_from_blocks(selected)

    async def _optimize_sliding(self, target: int) -> str:
        """Sliding window over recent content."""
        # Always keep critical content
        critical = [
            b for b in self._blocks.values()
            if b.priority == ContentPriority.CRITICAL
        ]

        critical_tokens = sum(b.tokens for b in critical)
        remaining = target - critical_tokens

        # Get non-critical sorted by recency
        non_critical = sorted(
            [b for b in self._blocks.values() if b.priority != ContentPriority.CRITICAL],
            key=lambda b: b.created_at,
            reverse=True
        )

        selected = list(critical)
        current = critical_tokens

        for block in non_critical:
            if current + block.tokens <= target:
                selected.append(block)
                current += block.tokens

        return self._build_from_blocks(selected)

    async def _optimize_hybrid(self, target: int) -> str:
        """Hybrid approach combining multiple strategies."""
        # Step 1: Keep all critical content
        critical = [
            b for b in self._blocks.values()
            if b.priority == ContentPriority.CRITICAL
        ]
        critical_tokens = sum(b.tokens for b in critical)

        # Step 2: Compress low-priority if over threshold
        if self._current_tokens > target * self.config.compression_threshold:
            low_priority = [
                b for b in self._blocks.values()
                if b.can_compress and b.priority.value <= ContentPriority.LOW.value
            ]

            for block in low_priority:
                await self._compress_block(block)

        # Step 3: Select by priority with recency tiebreaker
        non_critical = sorted(
            [b for b in self._blocks.values() if b.priority != ContentPriority.CRITICAL],
            key=lambda b: (b.priority.value, b.created_at),
            reverse=True
        )

        selected = list(critical)
        current = critical_tokens

        for block in non_critical:
            effective_tokens = block.tokens
            content = block.content

            if block.compressed_version:
                content = block.compressed_version
                effective_tokens = self._estimate_tokens(content)

            if current + effective_tokens <= target:
                selected.append(block)
                current += effective_tokens

        return self._build_from_blocks(selected, use_compressed=True)

    async def _compress_block(
        self,
        block: ContextBlock
    ) -> Optional[ContextBlock]:
        """Compress a block's content."""
        if block.compressed_version:
            return block

        llm = await self._get_llm()

        if not llm:
            # Fallback: simple truncation
            target_len = int(len(block.content) * self.config.summary_ratio)
            block.compressed_version = block.content[:target_len] + "..."
            return block

        try:
            prompt = f"""Summarize concisely, keeping key information:

{block.content}

Summary:"""

            summary = await llm.generate(prompt, temperature=0.3, max_tokens=200)
            block.compressed_version = summary.strip()
            return block

        except Exception as e:
            logger.warning(f"Compression failed: {e}")
            return None

    def _build_context(self) -> str:
        """Build context from all blocks."""
        # Sort by priority then creation time
        sorted_blocks = sorted(
            self._blocks.values(),
            key=lambda b: (-b.priority.value, b.created_at)
        )

        return "\n\n".join(b.content for b in sorted_blocks)

    def _build_from_blocks(
        self,
        blocks: List[ContextBlock],
        use_compressed: bool = False
    ) -> str:
        """Build context from specific blocks."""
        # Sort by priority then creation time
        sorted_blocks = sorted(
            blocks,
            key=lambda b: (-b.priority.value, b.created_at)
        )

        parts = []
        for block in sorted_blocks:
            if use_compressed and block.compressed_version:
                parts.append(block.compressed_version)
            else:
                parts.append(block.content)

        return "\n\n".join(parts)

    def get_token_count(self) -> int:
        """Get current token count."""
        return self._current_tokens

    def get_utilization(self) -> float:
        """Get utilization as percentage of target."""
        return self._current_tokens / self.config.target_tokens

    def get_stats(self) -> Dict[str, Any]:
        """Get optimizer statistics."""
        return {
            "current_tokens": self._current_tokens,
            "block_count": len(self._blocks),
            "utilization": self.get_utilization(),
            **self._stats
        }

    def clear(self) -> None:
        """Clear all blocks."""
        self._blocks.clear()
        self._current_tokens = 0


# Global instance
_context_optimizer: Optional[ContextWindowOptimizer] = None


def get_context_optimizer(
    config: Optional[OptimizerConfig] = None
) -> ContextWindowOptimizer:
    """Get or create context optimizer instance."""
    global _context_optimizer
    if _context_optimizer is None or config is not None:
        _context_optimizer = ContextWindowOptimizer(config)
    return _context_optimizer
