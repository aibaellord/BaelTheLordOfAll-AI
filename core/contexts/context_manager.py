#!/usr/bin/env python3
"""
BAEL - Context Manager
Advanced context window management for AI agent operations.

Features:
- Context window tracking
- Context compression
- Sliding window management
- Priority-based context
- Context summarization
- History management
- Context switching
- Multi-context support
"""

import asyncio
import copy
import hashlib
import json
import re
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ContextType(Enum):
    """Context content types."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    MEMORY = "memory"
    DOCUMENT = "document"


class CompressionStrategy(Enum):
    """Context compression strategies."""
    NONE = "none"
    TRUNCATE = "truncate"
    SUMMARIZE = "summarize"
    SAMPLE = "sample"
    PRIORITY = "priority"


class ContextPriority(Enum):
    """Context item priorities."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    OPTIONAL = 5


class WindowMode(Enum):
    """Sliding window modes."""
    FIFO = "fifo"
    LIFO = "lifo"
    PRIORITY = "priority"
    SMART = "smart"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class ContextItem:
    """A single context item."""
    item_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    context_type: ContextType = ContextType.USER
    priority: ContextPriority = ContextPriority.MEDIUM
    token_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    pinned: bool = False


@dataclass
class ContextWindow:
    """Context window configuration."""
    max_tokens: int = 4096
    reserved_tokens: int = 500
    system_tokens: int = 500
    available_tokens: int = 3096


@dataclass
class ContextSnapshot:
    """Snapshot of context state."""
    snapshot_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    items: List[ContextItem] = field(default_factory=list)
    total_tokens: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextStats:
    """Context statistics."""
    total_items: int = 0
    total_tokens: int = 0
    by_type: Dict[str, int] = field(default_factory=dict)
    by_priority: Dict[str, int] = field(default_factory=dict)
    compression_ratio: float = 1.0


@dataclass
class SummaryConfig:
    """Summary configuration."""
    max_sentences: int = 3
    preserve_key_points: bool = True
    include_metadata: bool = False


# =============================================================================
# TOKEN ESTIMATOR
# =============================================================================

class TokenEstimator:
    """Estimate token counts."""

    def __init__(self, chars_per_token: float = 4.0):
        self._chars_per_token = chars_per_token

    def estimate(self, text: str) -> int:
        """Estimate tokens in text."""
        if not text:
            return 0
        return max(1, int(len(text) / self._chars_per_token))

    def estimate_item(self, item: ContextItem) -> int:
        """Estimate tokens in context item."""
        if item.token_count > 0:
            return item.token_count

        item.token_count = self.estimate(item.content)
        return item.token_count


# =============================================================================
# CONTEXT COMPRESSOR
# =============================================================================

class ContextCompressor(ABC):
    """Abstract context compressor."""

    @abstractmethod
    def compress(
        self,
        items: List[ContextItem],
        target_tokens: int
    ) -> List[ContextItem]:
        """Compress context to target tokens."""
        pass


class TruncateCompressor(ContextCompressor):
    """Compress by truncating content."""

    def __init__(self, estimator: TokenEstimator):
        self._estimator = estimator

    def compress(
        self,
        items: List[ContextItem],
        target_tokens: int
    ) -> List[ContextItem]:
        """Truncate items to fit target."""
        result = []
        current_tokens = 0

        for item in items:
            tokens = self._estimator.estimate_item(item)

            if current_tokens + tokens <= target_tokens:
                result.append(item)
                current_tokens += tokens
            elif current_tokens < target_tokens:
                # Truncate this item
                remaining = target_tokens - current_tokens
                ratio = remaining / tokens
                truncated = item.content[:int(len(item.content) * ratio)]

                new_item = copy.deepcopy(item)
                new_item.content = truncated + "..."
                new_item.token_count = remaining
                result.append(new_item)
                break

        return result


class PriorityCompressor(ContextCompressor):
    """Compress by priority."""

    def __init__(self, estimator: TokenEstimator):
        self._estimator = estimator

    def compress(
        self,
        items: List[ContextItem],
        target_tokens: int
    ) -> List[ContextItem]:
        """Keep highest priority items."""
        # Sort by priority (lower value = higher priority)
        sorted_items = sorted(items, key=lambda x: (x.priority.value, -x.created_at.timestamp()))

        result = []
        current_tokens = 0

        for item in sorted_items:
            tokens = self._estimator.estimate_item(item)

            if current_tokens + tokens <= target_tokens:
                result.append(item)
                current_tokens += tokens

        # Restore original order
        item_ids = {item.item_id: i for i, item in enumerate(items)}
        result.sort(key=lambda x: item_ids.get(x.item_id, 0))

        return result


class SampleCompressor(ContextCompressor):
    """Compress by sampling items."""

    def __init__(self, estimator: TokenEstimator):
        self._estimator = estimator

    def compress(
        self,
        items: List[ContextItem],
        target_tokens: int
    ) -> List[ContextItem]:
        """Sample items to fit target."""
        if not items:
            return []

        total_tokens = sum(self._estimator.estimate_item(i) for i in items)

        if total_tokens <= target_tokens:
            return items

        # Calculate sample rate
        sample_rate = target_tokens / total_tokens

        result = []
        current_tokens = 0

        import random
        for item in items:
            # Always keep pinned items
            if item.pinned or random.random() < sample_rate:
                tokens = self._estimator.estimate_item(item)
                if current_tokens + tokens <= target_tokens:
                    result.append(item)
                    current_tokens += tokens

        return result


class SummarizeCompressor(ContextCompressor):
    """Compress by summarizing content."""

    def __init__(
        self,
        estimator: TokenEstimator,
        config: Optional[SummaryConfig] = None
    ):
        self._estimator = estimator
        self._config = config or SummaryConfig()

    def compress(
        self,
        items: List[ContextItem],
        target_tokens: int
    ) -> List[ContextItem]:
        """Summarize items to fit target."""
        result = []
        current_tokens = 0

        for item in items:
            if item.pinned:
                result.append(item)
                current_tokens += self._estimator.estimate_item(item)
                continue

            tokens = self._estimator.estimate_item(item)

            if current_tokens + tokens <= target_tokens:
                result.append(item)
                current_tokens += tokens
            else:
                # Summarize this item
                summary = self._summarize(item.content)
                new_item = copy.deepcopy(item)
                new_item.content = summary
                new_item.token_count = self._estimator.estimate(summary)

                if current_tokens + new_item.token_count <= target_tokens:
                    result.append(new_item)
                    current_tokens += new_item.token_count

        return result

    def _summarize(self, text: str) -> str:
        """Simple summarization by sentence extraction."""
        sentences = re.split(r'(?<=[.!?])\s+', text)

        if len(sentences) <= self._config.max_sentences:
            return text

        # Take first and last sentences
        selected = [sentences[0]]
        if len(sentences) > 1:
            selected.append(sentences[-1])

        return " ... ".join(selected)


# =============================================================================
# SLIDING WINDOW
# =============================================================================

class SlidingWindow:
    """Sliding window for context management."""

    def __init__(
        self,
        max_items: int = 100,
        mode: WindowMode = WindowMode.FIFO
    ):
        self._max_items = max_items
        self._mode = mode
        self._items: deque = deque(maxlen=max_items)
        self._pinned: List[ContextItem] = []

    def add(self, item: ContextItem) -> Optional[ContextItem]:
        """Add item, return evicted item if any."""
        if item.pinned:
            self._pinned.append(item)
            return None

        evicted = None
        if len(self._items) >= self._max_items:
            if self._mode == WindowMode.FIFO:
                evicted = self._items.popleft()
            elif self._mode == WindowMode.LIFO:
                evicted = self._items.pop()
            elif self._mode == WindowMode.PRIORITY:
                evicted = self._evict_lowest_priority()

        self._items.append(item)
        return evicted

    def _evict_lowest_priority(self) -> Optional[ContextItem]:
        """Evict lowest priority item."""
        if not self._items:
            return None

        # Find lowest priority (highest value)
        min_idx = 0
        min_priority = self._items[0].priority

        for i, item in enumerate(self._items):
            if item.priority.value > min_priority.value:
                min_priority = item.priority
                min_idx = i

        evicted = self._items[min_idx]
        del self._items[min_idx]
        return evicted

    def get_all(self) -> List[ContextItem]:
        """Get all items including pinned."""
        return self._pinned + list(self._items)

    def clear(self, include_pinned: bool = False) -> None:
        """Clear window."""
        self._items.clear()
        if include_pinned:
            self._pinned.clear()

    def __len__(self) -> int:
        return len(self._items) + len(self._pinned)


# =============================================================================
# CONTEXT STORE
# =============================================================================

class ContextStore:
    """Store and manage context items."""

    def __init__(self):
        self._items: Dict[str, ContextItem] = {}
        self._by_type: Dict[ContextType, List[str]] = defaultdict(list)
        self._order: List[str] = []

    def add(self, item: ContextItem) -> str:
        """Add context item."""
        self._items[item.item_id] = item
        self._by_type[item.context_type].append(item.item_id)
        self._order.append(item.item_id)
        return item.item_id

    def get(self, item_id: str) -> Optional[ContextItem]:
        """Get item by ID."""
        return self._items.get(item_id)

    def get_by_type(self, context_type: ContextType) -> List[ContextItem]:
        """Get items by type."""
        item_ids = self._by_type.get(context_type, [])
        return [self._items[iid] for iid in item_ids if iid in self._items]

    def get_ordered(self) -> List[ContextItem]:
        """Get items in insertion order."""
        return [self._items[iid] for iid in self._order if iid in self._items]

    def remove(self, item_id: str) -> bool:
        """Remove item."""
        item = self._items.pop(item_id, None)
        if item:
            if item_id in self._by_type[item.context_type]:
                self._by_type[item.context_type].remove(item_id)
            if item_id in self._order:
                self._order.remove(item_id)
            return True
        return False

    def clear(self) -> int:
        """Clear all items."""
        count = len(self._items)
        self._items.clear()
        self._by_type.clear()
        self._order.clear()
        return count

    def expire(self) -> int:
        """Remove expired items."""
        now = datetime.now()
        expired = [
            iid for iid, item in self._items.items()
            if item.expires_at and item.expires_at < now
        ]

        for iid in expired:
            self.remove(iid)

        return len(expired)


# =============================================================================
# CONTEXT HISTORY
# =============================================================================

class ContextHistory:
    """Manage context history and snapshots."""

    def __init__(self, max_snapshots: int = 10):
        self._max_snapshots = max_snapshots
        self._snapshots: deque = deque(maxlen=max_snapshots)
        self._current: Optional[ContextSnapshot] = None

    def save_snapshot(
        self,
        items: List[ContextItem],
        metadata: Optional[Dict[str, Any]] = None
    ) -> ContextSnapshot:
        """Save context snapshot."""
        total_tokens = sum(i.token_count for i in items)

        snapshot = ContextSnapshot(
            items=[copy.deepcopy(i) for i in items],
            total_tokens=total_tokens,
            metadata=metadata or {}
        )

        self._snapshots.append(snapshot)
        self._current = snapshot

        return snapshot

    def restore_snapshot(self, snapshot_id: str) -> Optional[List[ContextItem]]:
        """Restore from snapshot."""
        for snapshot in self._snapshots:
            if snapshot.snapshot_id == snapshot_id:
                self._current = snapshot
                return [copy.deepcopy(i) for i in snapshot.items]
        return None

    def get_latest(self) -> Optional[ContextSnapshot]:
        """Get latest snapshot."""
        return self._current

    def list_snapshots(self) -> List[ContextSnapshot]:
        """List all snapshots."""
        return list(self._snapshots)

    def rollback(self, steps: int = 1) -> Optional[List[ContextItem]]:
        """Rollback N steps."""
        if len(self._snapshots) <= steps:
            return None

        # Get snapshot from N steps ago
        idx = -(steps + 1)
        snapshot = self._snapshots[idx]
        self._current = snapshot

        return [copy.deepcopy(i) for i in snapshot.items]


# =============================================================================
# CONTEXT MANAGER
# =============================================================================

class ContextManager:
    """
    Context Manager for BAEL.

    Advanced context window management for AI agents.
    """

    def __init__(
        self,
        max_tokens: int = 4096,
        reserved_tokens: int = 500
    ):
        self._window = ContextWindow(
            max_tokens=max_tokens,
            reserved_tokens=reserved_tokens,
            available_tokens=max_tokens - reserved_tokens
        )

        self._estimator = TokenEstimator()
        self._store = ContextStore()
        self._sliding = SlidingWindow(mode=WindowMode.PRIORITY)
        self._history = ContextHistory()

        self._compressors: Dict[CompressionStrategy, ContextCompressor] = {
            CompressionStrategy.TRUNCATE: TruncateCompressor(self._estimator),
            CompressionStrategy.PRIORITY: PriorityCompressor(self._estimator),
            CompressionStrategy.SAMPLE: SampleCompressor(self._estimator),
            CompressionStrategy.SUMMARIZE: SummarizeCompressor(self._estimator),
        }

        self._contexts: Dict[str, List[str]] = {}  # context_name -> item_ids
        self._current_context: str = "default"

    # -------------------------------------------------------------------------
    # CONTEXT ITEMS
    # -------------------------------------------------------------------------

    def add(
        self,
        content: str,
        context_type: ContextType = ContextType.USER,
        priority: ContextPriority = ContextPriority.MEDIUM,
        pinned: bool = False,
        ttl_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add content to context."""
        expires_at = None
        if ttl_seconds:
            expires_at = datetime.now() + timedelta(seconds=ttl_seconds)

        item = ContextItem(
            content=content,
            context_type=context_type,
            priority=priority,
            token_count=self._estimator.estimate(content),
            expires_at=expires_at,
            metadata=metadata or {},
            pinned=pinned
        )

        self._store.add(item)
        self._sliding.add(item)

        # Track in current context
        if self._current_context not in self._contexts:
            self._contexts[self._current_context] = []
        self._contexts[self._current_context].append(item.item_id)

        return item.item_id

    def add_system(self, content: str, pinned: bool = True) -> str:
        """Add system message."""
        return self.add(
            content,
            context_type=ContextType.SYSTEM,
            priority=ContextPriority.CRITICAL,
            pinned=pinned
        )

    def add_user(self, content: str) -> str:
        """Add user message."""
        return self.add(
            content,
            context_type=ContextType.USER,
            priority=ContextPriority.HIGH
        )

    def add_assistant(self, content: str) -> str:
        """Add assistant message."""
        return self.add(
            content,
            context_type=ContextType.ASSISTANT,
            priority=ContextPriority.MEDIUM
        )

    def add_memory(
        self,
        content: str,
        priority: ContextPriority = ContextPriority.LOW
    ) -> str:
        """Add memory content."""
        return self.add(
            content,
            context_type=ContextType.MEMORY,
            priority=priority
        )

    def remove(self, item_id: str) -> bool:
        """Remove item from context."""
        return self._store.remove(item_id)

    def get(self, item_id: str) -> Optional[ContextItem]:
        """Get item by ID."""
        return self._store.get(item_id)

    # -------------------------------------------------------------------------
    # CONTEXT RETRIEVAL
    # -------------------------------------------------------------------------

    def get_context(
        self,
        max_tokens: Optional[int] = None,
        compression: CompressionStrategy = CompressionStrategy.NONE
    ) -> List[ContextItem]:
        """Get current context items."""
        items = self._store.get_ordered()

        # Expire old items
        self._store.expire()

        target = max_tokens or self._window.available_tokens
        total = sum(i.token_count for i in items)

        if total <= target or compression == CompressionStrategy.NONE:
            return items

        compressor = self._compressors.get(compression)
        if compressor:
            return compressor.compress(items, target)

        return items

    def get_as_messages(self) -> List[Dict[str, str]]:
        """Get context as chat messages."""
        items = self.get_context()

        messages = []
        for item in items:
            role = item.context_type.value
            if role in ["system", "user", "assistant"]:
                messages.append({
                    "role": role,
                    "content": item.content
                })

        return messages

    def get_by_type(self, context_type: ContextType) -> List[ContextItem]:
        """Get items by type."""
        return self._store.get_by_type(context_type)

    # -------------------------------------------------------------------------
    # TOKEN MANAGEMENT
    # -------------------------------------------------------------------------

    def get_token_count(self) -> int:
        """Get current token count."""
        items = self._store.get_ordered()
        return sum(i.token_count for i in items)

    def get_available_tokens(self) -> int:
        """Get available tokens."""
        used = self.get_token_count()
        return max(0, self._window.available_tokens - used)

    def fits(self, content: str) -> bool:
        """Check if content fits in available space."""
        tokens = self._estimator.estimate(content)
        return tokens <= self.get_available_tokens()

    def set_window(
        self,
        max_tokens: int,
        reserved_tokens: int = 500
    ) -> None:
        """Set context window size."""
        self._window = ContextWindow(
            max_tokens=max_tokens,
            reserved_tokens=reserved_tokens,
            available_tokens=max_tokens - reserved_tokens
        )

    # -------------------------------------------------------------------------
    # COMPRESSION
    # -------------------------------------------------------------------------

    def compress(
        self,
        strategy: CompressionStrategy = CompressionStrategy.PRIORITY,
        target_tokens: Optional[int] = None
    ) -> int:
        """Compress context."""
        items = self._store.get_ordered()
        original = sum(i.token_count for i in items)

        target = target_tokens or (self._window.available_tokens // 2)

        compressor = self._compressors.get(strategy)
        if not compressor:
            return 0

        compressed = compressor.compress(items, target)

        # Update store with compressed items
        self._store.clear()
        for item in compressed:
            self._store.add(item)

        new_total = sum(i.token_count for i in compressed)
        return original - new_total

    def summarize_history(self, keep_recent: int = 5) -> str:
        """Summarize older messages, keep recent."""
        items = self._store.get_ordered()

        if len(items) <= keep_recent:
            return ""

        # Separate old and recent
        old_items = items[:-keep_recent]

        # Create summary
        summaries = []
        for item in old_items:
            if item.context_type in [ContextType.USER, ContextType.ASSISTANT]:
                prefix = "User" if item.context_type == ContextType.USER else "Assistant"
                snippet = item.content[:100] + "..." if len(item.content) > 100 else item.content
                summaries.append(f"{prefix}: {snippet}")

        summary = "Previous conversation summary:\n" + "\n".join(summaries)

        # Remove old items
        for item in old_items:
            if not item.pinned:
                self._store.remove(item.item_id)

        # Add summary as memory
        self.add_memory(summary, ContextPriority.LOW)

        return summary

    # -------------------------------------------------------------------------
    # CONTEXT SWITCHING
    # -------------------------------------------------------------------------

    def switch_context(self, name: str) -> None:
        """Switch to different context."""
        # Save current
        if self._current_context:
            items = self._store.get_ordered()
            self._history.save_snapshot(items, {"context": self._current_context})

        self._current_context = name

        # Restore if exists
        if name in self._contexts:
            self._store.clear()
            # Contexts would need to be restored from snapshots

    def get_context_name(self) -> str:
        """Get current context name."""
        return self._current_context

    def list_contexts(self) -> List[str]:
        """List all contexts."""
        return list(self._contexts.keys())

    # -------------------------------------------------------------------------
    # SNAPSHOTS
    # -------------------------------------------------------------------------

    def save_snapshot(
        self,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Save context snapshot."""
        items = self._store.get_ordered()
        snapshot = self._history.save_snapshot(items, metadata)
        return snapshot.snapshot_id

    def restore_snapshot(self, snapshot_id: str) -> bool:
        """Restore from snapshot."""
        items = self._history.restore_snapshot(snapshot_id)
        if items:
            self._store.clear()
            for item in items:
                self._store.add(item)
            return True
        return False

    def rollback(self, steps: int = 1) -> bool:
        """Rollback context."""
        items = self._history.rollback(steps)
        if items:
            self._store.clear()
            for item in items:
                self._store.add(item)
            return True
        return False

    def list_snapshots(self) -> List[ContextSnapshot]:
        """List snapshots."""
        return self._history.list_snapshots()

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def clear(self, keep_system: bool = True) -> int:
        """Clear context."""
        if keep_system:
            system_items = self._store.get_by_type(ContextType.SYSTEM)
            count = self._store.clear()
            for item in system_items:
                self._store.add(item)
            return count - len(system_items)
        else:
            return self._store.clear()

    def get_stats(self) -> ContextStats:
        """Get context statistics."""
        items = self._store.get_ordered()

        by_type = {}
        by_priority = {}

        for item in items:
            type_key = item.context_type.value
            by_type[type_key] = by_type.get(type_key, 0) + item.token_count

            priority_key = item.priority.name
            by_priority[priority_key] = by_priority.get(priority_key, 0) + 1

        return ContextStats(
            total_items=len(items),
            total_tokens=sum(i.token_count for i in items),
            by_type=by_type,
            by_priority=by_priority
        )

    def pin(self, item_id: str) -> bool:
        """Pin item to context."""
        item = self._store.get(item_id)
        if item:
            item.pinned = True
            return True
        return False

    def unpin(self, item_id: str) -> bool:
        """Unpin item."""
        item = self._store.get(item_id)
        if item:
            item.pinned = False
            return True
        return False


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Context Manager."""
    print("=" * 70)
    print("BAEL - CONTEXT MANAGER DEMO")
    print("Advanced Context Window Management for AI Agents")
    print("=" * 70)
    print()

    manager = ContextManager(max_tokens=1000, reserved_tokens=200)

    # 1. Add Context Items
    print("1. ADD CONTEXT ITEMS:")
    print("-" * 40)

    system_id = manager.add_system("You are a helpful AI assistant.")
    user_id = manager.add_user("Hello! Can you help me?")
    assistant_id = manager.add_assistant("Of course! How can I assist you?")

    print(f"   Added system message: {system_id[:8]}...")
    print(f"   Added user message: {user_id[:8]}...")
    print(f"   Added assistant message: {assistant_id[:8]}...")
    print()

    # 2. Check Token Count
    print("2. TOKEN COUNT:")
    print("-" * 40)

    total = manager.get_token_count()
    available = manager.get_available_tokens()

    print(f"   Total tokens used: {total}")
    print(f"   Available tokens: {available}")
    print()

    # 3. Get Context
    print("3. GET CONTEXT:")
    print("-" * 40)

    context = manager.get_context()
    print(f"   Context items: {len(context)}")
    for item in context:
        print(f"     [{item.context_type.value}] {item.content[:40]}...")
    print()

    # 4. Get as Messages
    print("4. GET AS CHAT MESSAGES:")
    print("-" * 40)

    messages = manager.get_as_messages()
    print(f"   Messages: {len(messages)}")
    for msg in messages:
        print(f"     [{msg['role']}]: {msg['content'][:40]}...")
    print()

    # 5. Add More Context
    print("5. ADD MORE CONTEXT:")
    print("-" * 40)

    for i in range(5):
        manager.add_user(f"User message {i + 1} with some content to increase tokens.")
        manager.add_assistant(f"Assistant response {i + 1} with helpful information.")

    total = manager.get_token_count()
    print(f"   Added 10 more messages")
    print(f"   Total tokens now: {total}")
    print()

    # 6. Compression
    print("6. CONTEXT COMPRESSION:")
    print("-" * 40)

    before = manager.get_token_count()
    saved = manager.compress(CompressionStrategy.PRIORITY, target_tokens=200)
    after = manager.get_token_count()

    print(f"   Before: {before} tokens")
    print(f"   After: {after} tokens")
    print(f"   Saved: {saved} tokens")
    print()

    # 7. Rebuild and Test Truncate
    print("7. TRUNCATE COMPRESSION:")
    print("-" * 40)

    manager.clear()
    manager.add_system("System prompt")
    for i in range(3):
        manager.add_user(f"Long user message {i}" * 10)

    before = manager.get_token_count()
    saved = manager.compress(CompressionStrategy.TRUNCATE, target_tokens=100)
    after = manager.get_token_count()

    print(f"   Before: {before} tokens")
    print(f"   After: {after} tokens")
    print(f"   Saved: {saved} tokens")
    print()

    # 8. Priority-based Content
    print("8. PRIORITY-BASED CONTENT:")
    print("-" * 40)

    manager.clear()
    manager.add("Critical info", priority=ContextPriority.CRITICAL)
    manager.add("High priority", priority=ContextPriority.HIGH)
    manager.add("Medium priority", priority=ContextPriority.MEDIUM)
    manager.add("Low priority", priority=ContextPriority.LOW)
    manager.add("Optional", priority=ContextPriority.OPTIONAL)

    context = manager.get_context()
    print(f"   Items by priority:")
    for item in context:
        print(f"     [{item.priority.name}] {item.content}")
    print()

    # 9. Snapshots
    print("9. SNAPSHOTS:")
    print("-" * 40)

    snapshot_id = manager.save_snapshot({"note": "initial state"})
    print(f"   Saved snapshot: {snapshot_id[:8]}...")

    manager.add("New content after snapshot")
    manager.add("More new content")

    print(f"   Items before restore: {len(manager.get_context())}")

    manager.restore_snapshot(snapshot_id)
    print(f"   Items after restore: {len(manager.get_context())}")
    print()

    # 10. History Rollback
    print("10. HISTORY ROLLBACK:")
    print("-" * 40)

    manager.clear()
    manager.add("State 1")
    manager.save_snapshot()

    manager.add("State 2")
    manager.save_snapshot()

    manager.add("State 3")
    manager.save_snapshot()

    print(f"   Current items: {[i.content for i in manager.get_context()]}")

    manager.rollback(2)
    print(f"   After rollback(2): {[i.content for i in manager.get_context()]}")
    print()

    # 11. Memory Content
    print("11. MEMORY CONTENT:")
    print("-" * 40)

    manager.clear()
    manager.add_memory("User prefers Python")
    manager.add_memory("Previous topic: machine learning")

    memories = manager.get_by_type(ContextType.MEMORY)
    print(f"   Memory items: {len(memories)}")
    for mem in memories:
        print(f"     - {mem.content}")
    print()

    # 12. Pin/Unpin
    print("12. PIN/UNPIN ITEMS:")
    print("-" * 40)

    manager.clear()
    item_id = manager.add("Important info")
    manager.pin(item_id)

    item = manager.get(item_id)
    print(f"   Item pinned: {item.pinned}")

    manager.unpin(item_id)
    item = manager.get(item_id)
    print(f"   Item after unpin: {item.pinned}")
    print()

    # 13. TTL Expiration
    print("13. TTL EXPIRATION:")
    print("-" * 40)

    manager.clear()
    manager.add("Permanent content")
    manager.add("Temporary content", ttl_seconds=0)  # Expires immediately

    # Trigger expiration check
    await asyncio.sleep(0.1)
    context = manager.get_context()
    print(f"   Items after expiration: {len(context)}")
    print()

    # 14. Context Stats
    print("14. CONTEXT STATISTICS:")
    print("-" * 40)

    manager.clear()
    manager.add_system("System message")
    manager.add_user("User message 1")
    manager.add_user("User message 2")
    manager.add_assistant("Assistant response")
    manager.add_memory("Memory item")

    stats = manager.get_stats()
    print(f"   Total items: {stats.total_items}")
    print(f"   Total tokens: {stats.total_tokens}")
    print(f"   By type: {stats.by_type}")
    print(f"   By priority: {stats.by_priority}")
    print()

    # 15. Summarize History
    print("15. SUMMARIZE HISTORY:")
    print("-" * 40)

    manager.clear()
    for i in range(10):
        manager.add_user(f"User question {i}")
        manager.add_assistant(f"Assistant answer {i}")

    print(f"   Items before: {len(manager.get_context())}")

    summary = manager.summarize_history(keep_recent=4)
    print(f"   Items after: {len(manager.get_context())}")
    print(f"   Summary created: {len(summary)} chars")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Context Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
