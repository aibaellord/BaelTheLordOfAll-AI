"""
BAEL - Context Manager
Advanced context management for infinite conversations.

Features:
- Semantic compression
- Context prioritization
- Sliding window with summary
- Token budget management
- Multi-turn coherence
"""

import asyncio
import hashlib
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("BAEL.Context")


# =============================================================================
# TYPES & CONFIG
# =============================================================================

class ContextPriority(Enum):
    """Priority levels for context."""
    CRITICAL = 1  # Must include
    HIGH = 2      # Strongly prefer
    MEDIUM = 3    # Include if space
    LOW = 4       # Compress or summarize
    MINIMAL = 5   # Drop if needed


@dataclass
class ContextItem:
    """A single context item."""
    id: str
    content: str
    priority: ContextPriority
    token_count: int
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    relevance_score: float = 1.0
    compressed: bool = False


@dataclass
class ContextWindow:
    """Current context window."""
    items: List[ContextItem] = field(default_factory=list)
    total_tokens: int = 0
    max_tokens: int = 100000
    summary: Optional[str] = None
    summary_tokens: int = 0


@dataclass
class ConversationTurn:
    """A single conversation turn."""
    role: str  # user, assistant, system
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    token_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# TOKEN COUNTER
# =============================================================================

class TokenCounter:
    """Estimates token counts."""

    @staticmethod
    def count(text: str) -> int:
        """Estimate token count (rough approximation)."""
        # Average of 4 characters per token for English
        return len(text) // 4 + 1

    @staticmethod
    def count_messages(messages: List[Dict[str, str]]) -> int:
        """Count tokens in message list."""
        total = 0
        for msg in messages:
            total += TokenCounter.count(msg.get("content", ""))
            total += 4  # Role tokens
        return total


# =============================================================================
# CONTEXT COMPRESSOR
# =============================================================================

class ContextCompressor:
    """Compresses context while preserving meaning."""

    def __init__(self, model_router=None):
        self.model_router = model_router

    async def compress(self, content: str, target_ratio: float = 0.5) -> str:
        """Compress content to target ratio."""
        if not self.model_router:
            return self._simple_compress(content, target_ratio)

        current_tokens = TokenCounter.count(content)
        target_tokens = int(current_tokens * target_ratio)

        compress_prompt = f"""Compress this text to approximately {target_tokens} tokens while preserving all important information:

{content}

Provide a compressed version that maintains key facts, code, and context."""

        try:
            compressed = await self.model_router.generate(
                compress_prompt,
                model_type='fast'
            )
            return compressed
        except Exception as e:
            logger.error(f"Compression error: {e}")
            return self._simple_compress(content, target_ratio)

    def _simple_compress(self, content: str, target_ratio: float) -> str:
        """Simple compression without LLM."""
        lines = content.split('\n')

        # Remove empty lines
        lines = [l for l in lines if l.strip()]

        # Calculate target line count
        target_lines = max(int(len(lines) * target_ratio), 1)

        if len(lines) <= target_lines:
            return content

        # Keep first and last sections, compress middle
        keep = target_lines // 2
        compressed_lines = lines[:keep]
        compressed_lines.append("[... compressed ...]")
        compressed_lines.extend(lines[-keep:])

        return '\n'.join(compressed_lines)

    async def summarize(self, content: str, max_tokens: int = 200) -> str:
        """Create a summary of content."""
        if not self.model_router:
            return self._simple_summarize(content, max_tokens)

        summarize_prompt = f"""Summarize this content in {max_tokens} tokens or less:

{content}

Provide a concise summary of the key points."""

        try:
            summary = await self.model_router.generate(
                summarize_prompt,
                model_type='fast'
            )
            return summary
        except Exception as e:
            logger.error(f"Summarization error: {e}")
            return self._simple_summarize(content, max_tokens)

    def _simple_summarize(self, content: str, max_tokens: int) -> str:
        """Simple summarization without LLM."""
        target_chars = max_tokens * 4
        if len(content) <= target_chars:
            return content
        return content[:target_chars] + "..."


# =============================================================================
# CONTEXT MANAGER
# =============================================================================

class ContextManager:
    """Manages conversation context."""

    def __init__(self, max_tokens: int = 100000, model_router=None):
        self.max_tokens = max_tokens
        self.model_router = model_router
        self.compressor = ContextCompressor(model_router)

        self.window = ContextWindow(max_tokens=max_tokens)
        self.history: deque[ConversationTurn] = deque(maxlen=100)
        self.summaries: List[str] = []

        # Priority thresholds
        self.compression_threshold = 0.8  # Start compressing at 80% capacity
        self.summary_threshold = 0.9     # Create summary at 90% capacity

    async def add_turn(self, role: str, content: str, metadata: Dict[str, Any] = None) -> None:
        """Add a conversation turn."""
        token_count = TokenCounter.count(content)

        turn = ConversationTurn(
            role=role,
            content=content,
            token_count=token_count,
            metadata=metadata or {}
        )

        self.history.append(turn)

        # Add to window
        item = ContextItem(
            id=f"turn_{len(self.history)}",
            content=f"{role}: {content}",
            priority=ContextPriority.HIGH if role == "user" else ContextPriority.MEDIUM,
            token_count=token_count
        )

        await self._add_item(item)

    async def add_context(
        self,
        content: str,
        priority: ContextPriority = ContextPriority.MEDIUM,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Add context with priority."""
        item_id = hashlib.md5(content.encode()).hexdigest()[:8]

        item = ContextItem(
            id=item_id,
            content=content,
            priority=priority,
            token_count=TokenCounter.count(content),
            metadata=metadata or {}
        )

        await self._add_item(item)
        return item_id

    async def _add_item(self, item: ContextItem) -> None:
        """Add item to window, managing capacity."""
        # Check if we need to make room
        new_total = self.window.total_tokens + item.token_count

        if new_total > self.max_tokens * self.summary_threshold:
            await self._create_summary()

        if new_total > self.max_tokens * self.compression_threshold:
            await self._compress_low_priority()

        # Still too big? Remove oldest low priority
        while (self.window.total_tokens + item.token_count > self.max_tokens
               and self.window.items):
            removed = self._remove_lowest_priority()
            if not removed:
                break

        # Add item
        self.window.items.append(item)
        self.window.total_tokens += item.token_count

    async def _compress_low_priority(self) -> None:
        """Compress low priority items."""
        for item in self.window.items:
            if item.priority.value >= ContextPriority.LOW.value and not item.compressed:
                original_tokens = item.token_count
                item.content = await self.compressor.compress(item.content, 0.5)
                item.token_count = TokenCounter.count(item.content)
                item.compressed = True

                self.window.total_tokens -= (original_tokens - item.token_count)

                logger.debug(f"Compressed item {item.id}: {original_tokens} -> {item.token_count} tokens")

    async def _create_summary(self) -> None:
        """Create summary of older context."""
        # Find items to summarize (older, lower priority)
        items_to_summarize = []
        items_to_keep = []

        for i, item in enumerate(self.window.items):
            if i < len(self.window.items) // 2 and item.priority.value >= ContextPriority.MEDIUM.value:
                items_to_summarize.append(item)
            else:
                items_to_keep.append(item)

        if not items_to_summarize:
            return

        # Create summary
        combined_content = "\n".join([item.content for item in items_to_summarize])
        summary = await self.compressor.summarize(combined_content)

        # Store summary
        self.summaries.append(summary)
        self.window.summary = summary
        self.window.summary_tokens = TokenCounter.count(summary)

        # Remove summarized items
        self.window.items = items_to_keep
        self.window.total_tokens = sum(item.token_count for item in items_to_keep)
        self.window.total_tokens += self.window.summary_tokens

        logger.info(f"Created summary from {len(items_to_summarize)} items")

    def _remove_lowest_priority(self) -> bool:
        """Remove lowest priority item."""
        if not self.window.items:
            return False

        # Find lowest priority item
        lowest = max(self.window.items, key=lambda x: x.priority.value)

        if lowest.priority == ContextPriority.CRITICAL:
            return False

        self.window.items.remove(lowest)
        self.window.total_tokens -= lowest.token_count

        logger.debug(f"Removed item {lowest.id} ({lowest.priority.name})")
        return True

    def get_context(self, include_summary: bool = True) -> str:
        """Get current context as string."""
        parts = []

        # Include summary if exists
        if include_summary and self.window.summary:
            parts.append(f"[Previous context summary]\n{self.window.summary}\n")

        # Include items by priority
        sorted_items = sorted(self.window.items, key=lambda x: x.priority.value)

        for item in sorted_items:
            parts.append(item.content)

        return "\n\n".join(parts)

    def get_messages(self, max_turns: int = None) -> List[Dict[str, str]]:
        """Get conversation as messages list."""
        messages = []

        # Add summary as system message if exists
        if self.window.summary:
            messages.append({
                "role": "system",
                "content": f"Previous context: {self.window.summary}"
            })

        # Add recent turns
        turns = list(self.history)
        if max_turns:
            turns = turns[-max_turns:]

        for turn in turns:
            messages.append({
                "role": turn.role,
                "content": turn.content
            })

        return messages

    def get_stats(self) -> Dict[str, Any]:
        """Get context statistics."""
        return {
            "total_tokens": self.window.total_tokens,
            "max_tokens": self.max_tokens,
            "usage_percent": (self.window.total_tokens / self.max_tokens) * 100,
            "item_count": len(self.window.items),
            "history_turns": len(self.history),
            "has_summary": self.window.summary is not None,
            "summaries_created": len(self.summaries),
            "priority_distribution": self._get_priority_distribution()
        }

    def _get_priority_distribution(self) -> Dict[str, int]:
        """Get distribution of items by priority."""
        dist = {}
        for item in self.window.items:
            name = item.priority.name
            dist[name] = dist.get(name, 0) + 1
        return dist

    def clear(self) -> None:
        """Clear all context."""
        self.window = ContextWindow(max_tokens=self.max_tokens)
        self.history.clear()
        self.summaries.clear()


# =============================================================================
# RELEVANCE SCORER
# =============================================================================

class RelevanceScorer:
    """Scores context relevance to current query."""

    def __init__(self, model_router=None):
        self.model_router = model_router

    def score(self, item: ContextItem, query: str) -> float:
        """Score item relevance to query."""
        # Simple keyword overlap scoring
        item_words = set(item.content.lower().split())
        query_words = set(query.lower().split())

        overlap = len(item_words & query_words)
        max_possible = max(len(query_words), 1)

        base_score = overlap / max_possible

        # Boost by recency
        age_seconds = (datetime.now() - item.created_at).total_seconds()
        recency_boost = max(0, 1 - (age_seconds / 3600))  # Decay over 1 hour

        # Boost by priority
        priority_boost = (6 - item.priority.value) / 5  # 1.0 for CRITICAL, 0.2 for MINIMAL

        return base_score * 0.5 + recency_boost * 0.25 + priority_boost * 0.25

    async def rank_items(self, items: List[ContextItem], query: str) -> List[ContextItem]:
        """Rank items by relevance to query."""
        for item in items:
            item.relevance_score = self.score(item, query)

        return sorted(items, key=lambda x: x.relevance_score, reverse=True)


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Test context manager."""
    manager = ContextManager(max_tokens=1000)

    # Add some conversation
    await manager.add_turn("user", "Hello, I want to learn about Python async programming")
    await manager.add_turn("assistant", "Great! Async programming in Python uses asyncio...")
    await manager.add_turn("user", "Can you show me an example?")
    await manager.add_turn("assistant", "Here's a simple example: async def main()...")

    # Add some context
    await manager.add_context(
        "Python asyncio documentation summary...",
        priority=ContextPriority.MEDIUM
    )

    # Get stats
    stats = manager.get_stats()
    print("Context Stats:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Get context
    print("\nCurrent Context:")
    print(manager.get_context()[:500])


if __name__ == "__main__":
    asyncio.run(main())
