#!/usr/bin/env python3
"""
BAEL - Context Manager
Context handling, threading, and state management.

This module implements sophisticated context management
for maintaining conversation state, threading contexts,
and managing contextual information flow.

Features:
- Multi-level context hierarchy
- Context threading and forking
- State persistence
- Context compression
- Relevance scoring
- Context switching
- Memory-context integration
- Attention mechanisms
- Context windowing
- Priority context handling
- Context merging
- Automatic pruning
"""

import asyncio
import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    TypeVar, Union)
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class ContextLevel(Enum):
    """Levels of context hierarchy."""
    GLOBAL = "global"           # System-wide context
    SESSION = "session"         # Session-level context
    CONVERSATION = "conversation"  # Conversation context
    TURN = "turn"               # Single turn context
    FRAGMENT = "fragment"       # Sub-turn fragments


class ContextState(Enum):
    """State of a context."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"
    EXPIRED = "expired"


class AttentionType(Enum):
    """Types of attention mechanisms."""
    UNIFORM = "uniform"
    RECENCY = "recency"
    RELEVANCE = "relevance"
    PRIORITY = "priority"
    HYBRID = "hybrid"


class MergeStrategy(Enum):
    """Strategies for merging contexts."""
    REPLACE = "replace"
    APPEND = "append"
    MERGE = "merge"
    PRIORITY = "priority"


class PruneStrategy(Enum):
    """Strategies for pruning context."""
    FIFO = "fifo"              # First in, first out
    LRU = "lru"                # Least recently used
    IMPORTANCE = "importance"   # Lowest importance first
    RELEVANCE = "relevance"     # Least relevant first


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ContextItem:
    """A single context item."""
    id: str = field(default_factory=lambda: str(uuid4()))
    key: str = ""
    value: Any = None
    level: ContextLevel = ContextLevel.CONVERSATION
    priority: int = 5  # 1-10 scale
    created_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    expires_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def access(self) -> None:
        """Record access to this item."""
        self.accessed_at = datetime.now()
        self.access_count += 1

    @property
    def is_expired(self) -> bool:
        """Check if item has expired."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    @property
    def age_seconds(self) -> float:
        """Get age in seconds."""
        return (datetime.now() - self.created_at).total_seconds()


@dataclass
class ContextWindow:
    """A sliding window of context."""
    id: str = field(default_factory=lambda: str(uuid4()))
    items: List[ContextItem] = field(default_factory=list)
    max_size: int = 100
    max_tokens: int = 8000
    current_tokens: int = 0


@dataclass
class ContextThread:
    """A threaded context branch."""
    id: str = field(default_factory=lambda: str(uuid4()))
    parent_id: Optional[str] = None
    name: str = ""
    items: Dict[str, ContextItem] = field(default_factory=dict)
    state: ContextState = ContextState.ACTIVE
    created_at: datetime = field(default_factory=datetime.now)
    child_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextSnapshot:
    """A snapshot of context state."""
    id: str = field(default_factory=lambda: str(uuid4()))
    thread_id: str = ""
    items: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    description: str = ""


# =============================================================================
# ATTENTION MECHANISM
# =============================================================================

class AttentionMechanism(ABC):
    """Base class for attention mechanisms."""

    @abstractmethod
    def compute_attention(
        self,
        query: Any,
        items: List[ContextItem]
    ) -> List[float]:
        """Compute attention weights for items."""
        pass


class UniformAttention(AttentionMechanism):
    """Uniform attention weights."""

    def compute_attention(
        self,
        query: Any,
        items: List[ContextItem]
    ) -> List[float]:
        """Equal weight to all items."""
        if not items:
            return []
        weight = 1.0 / len(items)
        return [weight] * len(items)


class RecencyAttention(AttentionMechanism):
    """Attention based on recency."""

    def __init__(self, decay_rate: float = 0.1):
        self.decay_rate = decay_rate

    def compute_attention(
        self,
        query: Any,
        items: List[ContextItem]
    ) -> List[float]:
        """Weight based on how recently accessed."""
        if not items:
            return []

        weights = []
        now = datetime.now()

        for item in items:
            age = (now - item.accessed_at).total_seconds()
            weight = 2.718 ** (-self.decay_rate * age / 3600)  # Decay per hour
            weights.append(weight)

        # Normalize
        total = sum(weights)
        if total > 0:
            weights = [w / total for w in weights]

        return weights


class PriorityAttention(AttentionMechanism):
    """Attention based on priority."""

    def compute_attention(
        self,
        query: Any,
        items: List[ContextItem]
    ) -> List[float]:
        """Weight based on priority."""
        if not items:
            return []

        weights = [item.priority for item in items]
        total = sum(weights)

        if total > 0:
            weights = [w / total for w in weights]

        return weights


class HybridAttention(AttentionMechanism):
    """Hybrid attention combining multiple factors."""

    def __init__(
        self,
        recency_weight: float = 0.3,
        priority_weight: float = 0.4,
        access_weight: float = 0.3
    ):
        self.recency_weight = recency_weight
        self.priority_weight = priority_weight
        self.access_weight = access_weight

    def compute_attention(
        self,
        query: Any,
        items: List[ContextItem]
    ) -> List[float]:
        """Weight based on multiple factors."""
        if not items:
            return []

        weights = []
        now = datetime.now()

        # Normalize access counts
        max_access = max((item.access_count for item in items), default=1) or 1

        for item in items:
            # Recency score
            age = (now - item.accessed_at).total_seconds()
            recency_score = 2.718 ** (-0.1 * age / 3600)

            # Priority score (normalized to 0-1)
            priority_score = item.priority / 10

            # Access frequency score
            access_score = item.access_count / max_access

            # Combined weight
            weight = (
                self.recency_weight * recency_score +
                self.priority_weight * priority_score +
                self.access_weight * access_score
            )
            weights.append(weight)

        # Normalize
        total = sum(weights)
        if total > 0:
            weights = [w / total for w in weights]

        return weights


# =============================================================================
# CONTEXT PRUNER
# =============================================================================

class ContextPruner:
    """
    Handles context pruning to manage size.

    Removes least important items when limits are exceeded.
    """

    def __init__(
        self,
        strategy: PruneStrategy = PruneStrategy.LRU,
        max_items: int = 1000
    ):
        self.strategy = strategy
        self.max_items = max_items

    def prune(
        self,
        items: Dict[str, ContextItem],
        target_size: int = None
    ) -> List[str]:
        """Prune items and return IDs of removed items."""
        target = target_size or self.max_items

        if len(items) <= target:
            return []

        # Sort items by pruning criteria
        sorted_items = self._sort_for_pruning(list(items.values()))

        # Remove excess items
        to_remove = len(items) - target
        removed_ids = []

        for item in sorted_items[:to_remove]:
            if item.priority < 9:  # Never remove critical items
                del items[item.id]
                removed_ids.append(item.id)

        return removed_ids

    def _sort_for_pruning(
        self,
        items: List[ContextItem]
    ) -> List[ContextItem]:
        """Sort items by pruning priority (first = most likely to prune)."""
        if self.strategy == PruneStrategy.FIFO:
            return sorted(items, key=lambda x: x.created_at)
        elif self.strategy == PruneStrategy.LRU:
            return sorted(items, key=lambda x: x.accessed_at)
        elif self.strategy == PruneStrategy.IMPORTANCE:
            return sorted(items, key=lambda x: x.priority)
        elif self.strategy == PruneStrategy.RELEVANCE:
            # Use access count as proxy for relevance
            return sorted(items, key=lambda x: x.access_count)
        else:
            return items


# =============================================================================
# CONTEXT COMPRESSOR
# =============================================================================

class ContextCompressor:
    """
    Compresses context to reduce size.

    Summarizes or aggregates context items.
    """

    def __init__(self, compression_ratio: float = 0.5):
        self.compression_ratio = compression_ratio

    async def compress(
        self,
        items: List[ContextItem]
    ) -> List[ContextItem]:
        """Compress context items."""
        if not items:
            return []

        # Group by tags
        by_tag = defaultdict(list)
        untagged = []

        for item in items:
            if item.tags:
                for tag in item.tags:
                    by_tag[tag].append(item)
            else:
                untagged.append(item)

        compressed = []

        # Compress each group
        for tag, group in by_tag.items():
            if len(group) > 3:
                # Merge into summary
                merged = self._merge_items(group, f"compressed_{tag}")
                compressed.append(merged)
            else:
                compressed.extend(group)

        # Keep untagged as is
        compressed.extend(untagged)

        return compressed

    def _merge_items(
        self,
        items: List[ContextItem],
        key: str
    ) -> ContextItem:
        """Merge multiple items into one."""
        # Combine values
        combined_value = {
            "merged_count": len(items),
            "items": [
                {"key": item.key, "value": item.value}
                for item in items
            ]
        }

        # Use highest priority
        max_priority = max(item.priority for item in items)

        # Combine tags
        all_tags = set()
        for item in items:
            all_tags.update(item.tags)

        return ContextItem(
            key=key,
            value=combined_value,
            level=items[0].level if items else ContextLevel.CONVERSATION,
            priority=max_priority,
            tags=list(all_tags)
        )


# =============================================================================
# CONTEXT MANAGER
# =============================================================================

class ContextManager:
    """
    The master context manager for BAEL.

    Provides comprehensive context handling with threading,
    attention, compression, and pruning.
    """

    def __init__(
        self,
        max_items: int = 1000,
        max_threads: int = 100,
        attention_type: AttentionType = AttentionType.HYBRID
    ):
        self.threads: Dict[str, ContextThread] = {}
        self.active_thread_id: Optional[str] = None
        self.snapshots: Dict[str, ContextSnapshot] = {}

        # Create root thread
        self.root_thread = ContextThread(name="root")
        self.threads[self.root_thread.id] = self.root_thread
        self.active_thread_id = self.root_thread.id

        # Initialize components
        self.pruner = ContextPruner(
            strategy=PruneStrategy.LRU,
            max_items=max_items
        )
        self.compressor = ContextCompressor()
        self.attention = self._create_attention(attention_type)

        # Settings
        self.max_threads = max_threads
        self.auto_prune = True
        self.auto_compress = True

    def _create_attention(
        self,
        attention_type: AttentionType
    ) -> AttentionMechanism:
        """Create attention mechanism."""
        if attention_type == AttentionType.UNIFORM:
            return UniformAttention()
        elif attention_type == AttentionType.RECENCY:
            return RecencyAttention()
        elif attention_type == AttentionType.PRIORITY:
            return PriorityAttention()
        else:
            return HybridAttention()

    @property
    def active_thread(self) -> Optional[ContextThread]:
        """Get the active thread."""
        return self.threads.get(self.active_thread_id)

    def set(
        self,
        key: str,
        value: Any,
        level: ContextLevel = ContextLevel.CONVERSATION,
        priority: int = 5,
        tags: List[str] = None,
        ttl_seconds: Optional[int] = None,
        thread_id: Optional[str] = None
    ) -> ContextItem:
        """Set a context item."""
        target_thread = self.threads.get(thread_id or self.active_thread_id)
        if not target_thread:
            target_thread = self.active_thread

        expires_at = None
        if ttl_seconds:
            expires_at = datetime.now() + timedelta(seconds=ttl_seconds)

        item = ContextItem(
            key=key,
            value=value,
            level=level,
            priority=priority,
            tags=tags or [],
            expires_at=expires_at
        )

        target_thread.items[key] = item

        # Auto prune if needed
        if self.auto_prune:
            self.pruner.prune(target_thread.items)

        return item

    def get(
        self,
        key: str,
        default: Any = None,
        thread_id: Optional[str] = None
    ) -> Any:
        """Get a context value."""
        target_thread = self.threads.get(thread_id or self.active_thread_id)
        if not target_thread:
            return default

        item = target_thread.items.get(key)

        if item:
            if item.is_expired:
                del target_thread.items[key]
                return default
            item.access()
            return item.value

        # Check parent thread
        if target_thread.parent_id:
            return self.get(key, default, target_thread.parent_id)

        return default

    def get_item(
        self,
        key: str,
        thread_id: Optional[str] = None
    ) -> Optional[ContextItem]:
        """Get a context item."""
        target_thread = self.threads.get(thread_id or self.active_thread_id)
        if not target_thread:
            return None

        item = target_thread.items.get(key)
        if item and not item.is_expired:
            item.access()
            return item

        return None

    def delete(
        self,
        key: str,
        thread_id: Optional[str] = None
    ) -> bool:
        """Delete a context item."""
        target_thread = self.threads.get(thread_id or self.active_thread_id)
        if not target_thread:
            return False

        if key in target_thread.items:
            del target_thread.items[key]
            return True
        return False

    def create_thread(
        self,
        name: str,
        parent_id: Optional[str] = None,
        inherit_context: bool = True
    ) -> ContextThread:
        """Create a new context thread."""
        parent = self.threads.get(parent_id or self.active_thread_id)

        thread = ContextThread(
            name=name,
            parent_id=parent.id if parent else None
        )

        if inherit_context and parent:
            # Copy parent context
            for key, item in parent.items.items():
                thread.items[key] = ContextItem(
                    key=item.key,
                    value=item.value,
                    level=item.level,
                    priority=item.priority,
                    tags=list(item.tags)
                )
            parent.child_ids.append(thread.id)

        self.threads[thread.id] = thread
        return thread

    def switch_thread(self, thread_id: str) -> bool:
        """Switch to a different thread."""
        if thread_id in self.threads:
            self.active_thread_id = thread_id
            return True
        return False

    def merge_threads(
        self,
        source_id: str,
        target_id: str,
        strategy: MergeStrategy = MergeStrategy.MERGE
    ) -> bool:
        """Merge source thread into target."""
        source = self.threads.get(source_id)
        target = self.threads.get(target_id)

        if not source or not target:
            return False

        for key, item in source.items.items():
            if strategy == MergeStrategy.REPLACE:
                target.items[key] = item
            elif strategy == MergeStrategy.APPEND:
                if key not in target.items:
                    target.items[key] = item
            elif strategy == MergeStrategy.MERGE:
                if key in target.items:
                    # Merge values if both are dicts
                    if isinstance(target.items[key].value, dict) and isinstance(item.value, dict):
                        target.items[key].value.update(item.value)
                    else:
                        # Keep higher priority
                        if item.priority > target.items[key].priority:
                            target.items[key] = item
                else:
                    target.items[key] = item
            elif strategy == MergeStrategy.PRIORITY:
                if key not in target.items or item.priority > target.items[key].priority:
                    target.items[key] = item

        # Archive source thread
        source.state = ContextState.ARCHIVED

        return True

    def fork_thread(
        self,
        thread_id: Optional[str] = None,
        name: Optional[str] = None
    ) -> ContextThread:
        """Fork a thread to create a branch."""
        source = self.threads.get(thread_id or self.active_thread_id)
        if not source:
            source = self.active_thread

        return self.create_thread(
            name=name or f"fork_{source.name}",
            parent_id=source.id,
            inherit_context=True
        )

    def create_snapshot(
        self,
        thread_id: Optional[str] = None,
        description: str = ""
    ) -> ContextSnapshot:
        """Create a snapshot of current context."""
        target = self.threads.get(thread_id or self.active_thread_id)
        if not target:
            target = self.active_thread

        snapshot = ContextSnapshot(
            thread_id=target.id,
            items={
                key: item.value
                for key, item in target.items.items()
            },
            description=description
        )

        self.snapshots[snapshot.id] = snapshot
        return snapshot

    def restore_snapshot(
        self,
        snapshot_id: str,
        thread_id: Optional[str] = None
    ) -> bool:
        """Restore context from a snapshot."""
        snapshot = self.snapshots.get(snapshot_id)
        if not snapshot:
            return False

        target = self.threads.get(thread_id or self.active_thread_id)
        if not target:
            return False

        # Clear current items
        target.items.clear()

        # Restore from snapshot
        for key, value in snapshot.items.items():
            target.items[key] = ContextItem(
                key=key,
                value=value,
                level=ContextLevel.CONVERSATION
            )

        return True

    def query(
        self,
        query: Any,
        limit: int = 10,
        thread_id: Optional[str] = None
    ) -> List[Tuple[ContextItem, float]]:
        """Query context with attention weighting."""
        target = self.threads.get(thread_id or self.active_thread_id)
        if not target:
            return []

        items = list(target.items.values())

        # Remove expired items
        items = [item for item in items if not item.is_expired]

        if not items:
            return []

        # Compute attention weights
        weights = self.attention.compute_attention(query, items)

        # Sort by weight
        weighted = list(zip(items, weights))
        weighted.sort(key=lambda x: x[1], reverse=True)

        # Access top items
        for item, _ in weighted[:limit]:
            item.access()

        return weighted[:limit]

    def get_by_level(
        self,
        level: ContextLevel,
        thread_id: Optional[str] = None
    ) -> List[ContextItem]:
        """Get items by context level."""
        target = self.threads.get(thread_id or self.active_thread_id)
        if not target:
            return []

        return [
            item for item in target.items.values()
            if item.level == level and not item.is_expired
        ]

    def get_by_tags(
        self,
        tags: List[str],
        thread_id: Optional[str] = None
    ) -> List[ContextItem]:
        """Get items by tags."""
        target = self.threads.get(thread_id or self.active_thread_id)
        if not target:
            return []

        tag_set = set(tags)
        return [
            item for item in target.items.values()
            if tag_set & set(item.tags) and not item.is_expired
        ]

    async def compress_thread(
        self,
        thread_id: Optional[str] = None
    ) -> int:
        """Compress a thread's context."""
        target = self.threads.get(thread_id or self.active_thread_id)
        if not target:
            return 0

        original_count = len(target.items)

        items = list(target.items.values())
        compressed = await self.compressor.compress(items)

        # Replace items
        target.items.clear()
        for item in compressed:
            target.items[item.key] = item

        return original_count - len(target.items)

    def prune_thread(
        self,
        thread_id: Optional[str] = None,
        target_size: Optional[int] = None
    ) -> int:
        """Prune a thread's context."""
        target = self.threads.get(thread_id or self.active_thread_id)
        if not target:
            return 0

        removed = self.pruner.prune(target.items, target_size)
        return len(removed)

    def cleanup_expired(self) -> int:
        """Remove all expired items across threads."""
        removed_count = 0

        for thread in self.threads.values():
            expired_keys = [
                key for key, item in thread.items.items()
                if item.is_expired
            ]
            for key in expired_keys:
                del thread.items[key]
                removed_count += 1

        return removed_count

    def get_stats(self) -> Dict[str, Any]:
        """Get context manager statistics."""
        total_items = sum(len(t.items) for t in self.threads.values())
        active_threads = sum(1 for t in self.threads.values() if t.state == ContextState.ACTIVE)

        return {
            "total_threads": len(self.threads),
            "active_threads": active_threads,
            "total_items": total_items,
            "snapshots": len(self.snapshots),
            "active_thread": self.active_thread.name if self.active_thread else None
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Context Manager."""
    print("=" * 70)
    print("BAEL - CONTEXT MANAGER DEMO")
    print("Context Handling and Threading")
    print("=" * 70)
    print()

    # Create context manager
    ctx = ContextManager(
        max_items=100,
        attention_type=AttentionType.HYBRID
    )

    # 1. Basic Context Operations
    print("1. BASIC CONTEXT OPERATIONS:")
    print("-" * 40)

    # Set context items
    ctx.set("user_name", "BAEL User", priority=8)
    ctx.set("session_id", "sess_12345", level=ContextLevel.SESSION)
    ctx.set("task", "Build AI system", tags=["task", "current"])
    ctx.set("mode", "development", priority=6)

    print(f"   Set 4 context items")
    print(f"   user_name: {ctx.get('user_name')}")
    print(f"   session_id: {ctx.get('session_id')}")
    print()

    # 2. Context Levels
    print("2. CONTEXT LEVELS:")
    print("-" * 40)

    ctx.set("global_setting", "value", level=ContextLevel.GLOBAL, priority=10)
    ctx.set("turn_data", {"step": 1}, level=ContextLevel.TURN)

    session_items = ctx.get_by_level(ContextLevel.SESSION)
    turn_items = ctx.get_by_level(ContextLevel.TURN)

    print(f"   Session-level items: {len(session_items)}")
    print(f"   Turn-level items: {len(turn_items)}")
    print()

    # 3. Context Threading
    print("3. CONTEXT THREADING:")
    print("-" * 40)

    # Create child threads
    analysis_thread = ctx.create_thread("analysis", inherit_context=True)
    print(f"   Created thread: {analysis_thread.name}")

    # Fork current thread
    fork_thread = ctx.fork_thread(name="experiment")
    print(f"   Forked thread: {fork_thread.name}")

    # Set context in specific thread
    ctx.switch_thread(analysis_thread.id)
    ctx.set("analysis_type", "deep", tags=["analysis"])

    # Switch back
    ctx.switch_thread(ctx.root_thread.id)
    print(f"   Active thread: {ctx.active_thread.name}")
    print()

    # 4. Tags and Queries
    print("4. TAGS AND QUERIES:")
    print("-" * 40)

    ctx.set("important_config", {"key": "value"}, tags=["config", "important"])
    ctx.set("another_config", {"key2": "value2"}, tags=["config"])

    tagged_items = ctx.get_by_tags(["config"])
    print(f"   Items with 'config' tag: {len(tagged_items)}")

    # Query with attention
    results = ctx.query("task configuration", limit=5)
    print(f"   Query results: {len(results)} items")
    for item, weight in results[:3]:
        print(f"   - {item.key}: {weight:.3f}")
    print()

    # 5. Snapshots
    print("5. CONTEXT SNAPSHOTS:")
    print("-" * 40)

    snapshot = ctx.create_snapshot(description="Before changes")
    print(f"   Created snapshot: {snapshot.id[:8]}...")

    # Make changes
    ctx.set("new_item", "added after snapshot")
    print(f"   Added new item after snapshot")

    # Restore
    items_before_restore = len(ctx.active_thread.items)
    ctx.restore_snapshot(snapshot.id)
    items_after_restore = len(ctx.active_thread.items)

    print(f"   Items before restore: {items_before_restore}")
    print(f"   Items after restore: {items_after_restore}")
    print()

    # 6. Expiring Context
    print("6. EXPIRING CONTEXT:")
    print("-" * 40)

    ctx.set("temporary", "expires soon", ttl_seconds=1)
    print(f"   Set temporary item with 1 second TTL")
    print(f"   Value now: {ctx.get('temporary')}")

    await asyncio.sleep(1.1)
    print(f"   Value after 1.1s: {ctx.get('temporary', 'EXPIRED')}")

    expired_count = ctx.cleanup_expired()
    print(f"   Cleaned up {expired_count} expired items")
    print()

    # 7. Thread Merging
    print("7. THREAD MERGING:")
    print("-" * 40)

    # Create thread with additional context
    feature_thread = ctx.create_thread("feature", inherit_context=False)
    ctx.switch_thread(feature_thread.id)
    ctx.set("feature_flag", True, priority=7)
    ctx.set("feature_data", {"version": 2})

    # Merge back to root
    ctx.merge_threads(feature_thread.id, ctx.root_thread.id, MergeStrategy.MERGE)
    ctx.switch_thread(ctx.root_thread.id)

    print(f"   Merged feature thread into root")
    print(f"   feature_flag in root: {ctx.get('feature_flag')}")
    print()

    # 8. Compression
    print("8. CONTEXT COMPRESSION:")
    print("-" * 40)

    # Add many items with same tag
    for i in range(10):
        ctx.set(f"log_{i}", f"Log entry {i}", tags=["log"])

    items_before = len(ctx.active_thread.items)
    compressed = await ctx.compress_thread()
    items_after = len(ctx.active_thread.items)

    print(f"   Items before compression: {items_before}")
    print(f"   Items after compression: {items_after}")
    print(f"   Compressed {compressed} items")
    print()

    # 9. Pruning
    print("9. CONTEXT PRUNING:")
    print("-" * 40)

    # Add more items
    for i in range(50):
        ctx.set(f"temp_{i}", f"value {i}", priority=3)

    items_before = len(ctx.active_thread.items)
    pruned = ctx.prune_thread(target_size=20)
    items_after = len(ctx.active_thread.items)

    print(f"   Items before pruning: {items_before}")
    print(f"   Items after pruning: {items_after}")
    print(f"   Pruned {pruned} items")
    print()

    # 10. Final Statistics
    print("10. FINAL STATISTICS:")
    print("-" * 40)

    stats = ctx.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Context Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
