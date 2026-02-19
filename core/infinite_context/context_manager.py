"""
⚡ CONTEXT MANAGER ⚡
====================
Intelligent context management.

Features:
- Priority-based context handling
- Sliding window management
- Adaptive context sizing
- Relevance tracking
"""

import math
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import deque
import uuid


class ContextPriority(Enum):
    """Priority levels for context items"""
    CRITICAL = 5      # Must never be removed
    HIGH = 4          # Important context
    NORMAL = 3        # Standard priority
    LOW = 2           # Can be compressed/removed
    EPHEMERAL = 1     # Temporary, remove first


@dataclass
class ContextItem:
    """Single item in context"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: Any = None

    # Metadata
    priority: ContextPriority = ContextPriority.NORMAL
    relevance: float = 1.0
    timestamp: datetime = field(default_factory=datetime.now)

    # Size tracking
    token_count: int = 0

    # Access tracking
    access_count: int = 0
    last_access: datetime = field(default_factory=datetime.now)

    # Embedding for similarity
    embedding: Optional[np.ndarray] = None

    # Relationships
    related_ids: Set[str] = field(default_factory=set)

    def access(self):
        """Record access"""
        self.access_count += 1
        self.last_access = datetime.now()

    def compute_importance(self) -> float:
        """Compute overall importance score"""
        # Factors: priority, relevance, recency, access frequency
        priority_score = self.priority.value / 5

        age_seconds = (datetime.now() - self.timestamp).total_seconds()
        recency_score = math.exp(-age_seconds / 3600)  # Decay over 1 hour

        access_score = min(self.access_count / 10, 1.0)

        return (
            0.4 * priority_score +
            0.3 * self.relevance +
            0.2 * recency_score +
            0.1 * access_score
        )


class ContextWindow:
    """
    Manages a window of context items.
    """

    def __init__(
        self,
        max_tokens: int = 8192,
        max_items: int = 100
    ):
        self.max_tokens = max_tokens
        self.max_items = max_items

        self.items: Dict[str, ContextItem] = {}
        self.order: List[str] = []  # Insertion order

        self.current_tokens = 0

    def add(self, item: ContextItem) -> bool:
        """Add item to context"""
        # Check if fits
        if self.current_tokens + item.token_count > self.max_tokens:
            # Try to make room
            freed = self._evict_to_fit(item.token_count)
            if not freed:
                return False

        if len(self.items) >= self.max_items:
            self._evict_lowest_priority()

        self.items[item.id] = item
        self.order.append(item.id)
        self.current_tokens += item.token_count

        return True

    def get(self, item_id: str) -> Optional[ContextItem]:
        """Get item by ID"""
        item = self.items.get(item_id)
        if item:
            item.access()
        return item

    def remove(self, item_id: str):
        """Remove item"""
        if item_id in self.items:
            item = self.items[item_id]
            self.current_tokens -= item.token_count
            del self.items[item_id]
            if item_id in self.order:
                self.order.remove(item_id)

    def _evict_to_fit(self, required_tokens: int) -> bool:
        """Evict items to fit required tokens"""
        evictable = [
            item for item in self.items.values()
            if item.priority != ContextPriority.CRITICAL
        ]

        # Sort by importance (lowest first)
        evictable.sort(key=lambda i: i.compute_importance())

        freed = 0
        to_remove = []

        for item in evictable:
            if self.current_tokens - freed + required_tokens <= self.max_tokens:
                break

            to_remove.append(item.id)
            freed += item.token_count

        for item_id in to_remove:
            self.remove(item_id)

        return self.current_tokens + required_tokens <= self.max_tokens

    def _evict_lowest_priority(self):
        """Evict lowest priority item"""
        if not self.items:
            return

        evictable = [
            item for item in self.items.values()
            if item.priority != ContextPriority.CRITICAL
        ]

        if evictable:
            lowest = min(evictable, key=lambda i: i.compute_importance())
            self.remove(lowest.id)

    def get_ordered_items(self) -> List[ContextItem]:
        """Get items in insertion order"""
        return [
            self.items[item_id]
            for item_id in self.order
            if item_id in self.items
        ]

    def get_by_priority(
        self,
        min_priority: ContextPriority = ContextPriority.EPHEMERAL
    ) -> List[ContextItem]:
        """Get items with at least given priority"""
        return [
            item for item in self.items.values()
            if item.priority.value >= min_priority.value
        ]

    def search_similar(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5
    ) -> List[Tuple[ContextItem, float]]:
        """Search for similar context items"""
        results = []

        for item in self.items.values():
            if item.embedding is not None:
                similarity = np.dot(query_embedding, item.embedding) / (
                    np.linalg.norm(query_embedding) *
                    np.linalg.norm(item.embedding) + 1e-10
                )
                results.append((item, similarity))

        results.sort(key=lambda x: -x[1])
        return results[:top_k]

    @property
    def utilization(self) -> float:
        """Get token utilization"""
        return self.current_tokens / self.max_tokens


class ContextManager:
    """
    Comprehensive context management system.
    """

    def __init__(
        self,
        max_tokens: int = 32768,
        window_size: int = 8192
    ):
        self.max_tokens = max_tokens
        self.window_size = window_size

        # Main context window
        self.active_window = ContextWindow(max_tokens=window_size)

        # Archive for less relevant items
        self.archive: Dict[str, ContextItem] = {}

        # Pinned items (always in context)
        self.pinned: Set[str] = set()

        # Statistics
        self.total_items_seen = 0
        self.items_archived = 0

    def add(
        self,
        content: Any,
        priority: ContextPriority = ContextPriority.NORMAL,
        token_count: int = 0,
        embedding: np.ndarray = None
    ) -> ContextItem:
        """Add item to context"""
        item = ContextItem(
            content=content,
            priority=priority,
            token_count=token_count,
            embedding=embedding
        )

        if not self.active_window.add(item):
            # Archive lowest priority items
            self._archive_lowest()
            self.active_window.add(item)

        self.total_items_seen += 1
        return item

    def pin(self, item_id: str):
        """Pin item to prevent removal"""
        self.pinned.add(item_id)
        if item_id in self.active_window.items:
            self.active_window.items[item_id].priority = ContextPriority.CRITICAL

    def unpin(self, item_id: str):
        """Unpin item"""
        self.pinned.discard(item_id)

    def _archive_lowest(self):
        """Archive lowest priority items"""
        items = self.active_window.get_ordered_items()

        # Find items to archive
        for item in items:
            if item.id in self.pinned:
                continue
            if item.priority.value <= ContextPriority.LOW.value:
                self.archive[item.id] = item
                self.active_window.remove(item.id)
                self.items_archived += 1
                break

    def retrieve(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        include_archive: bool = True
    ) -> List[ContextItem]:
        """Retrieve relevant context"""
        # Search active window
        results = self.active_window.search_similar(query_embedding, top_k * 2)

        # Search archive if needed
        if include_archive and len(results) < top_k:
            for item in self.archive.values():
                if item.embedding is not None:
                    similarity = np.dot(query_embedding, item.embedding) / (
                        np.linalg.norm(query_embedding) *
                        np.linalg.norm(item.embedding) + 1e-10
                    )
                    results.append((item, similarity))

        # Sort and return
        results.sort(key=lambda x: -x[1])
        return [item for item, _ in results[:top_k]]

    def get_context(
        self,
        max_tokens: int = None
    ) -> List[ContextItem]:
        """Get current context up to token limit"""
        max_tokens = max_tokens or self.window_size

        items = self.active_window.get_ordered_items()

        # Prioritize
        items.sort(key=lambda i: -i.compute_importance())

        result = []
        total_tokens = 0

        for item in items:
            if total_tokens + item.token_count > max_tokens:
                continue
            result.append(item)
            total_tokens += item.token_count

        return result


class SlidingWindowContext:
    """
    Sliding window for streaming context.
    """

    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.window: deque = deque(maxlen=window_size)
        self.position = 0

    def append(self, item: Any):
        """Append item to window"""
        self.window.append((self.position, item))
        self.position += 1

    def get_window(self) -> List[Tuple[int, Any]]:
        """Get current window"""
        return list(self.window)

    def slide(self, amount: int = 1):
        """Slide window forward"""
        for _ in range(min(amount, len(self.window))):
            self.window.popleft()


class AdaptiveContext:
    """
    Adaptive context that adjusts based on task.
    """

    def __init__(self, base_size: int = 4096):
        self.base_size = base_size
        self.current_size = base_size

        self.manager = ContextManager(max_tokens=base_size * 4)

        # Task-specific weights
        self.task_weights: Dict[str, Dict[ContextPriority, float]] = {}
        self.current_task: Optional[str] = None

    def set_task(self, task_type: str):
        """Set current task type"""
        self.current_task = task_type

        # Adjust context based on task
        if task_type == 'analysis':
            self.current_size = self.base_size * 2
        elif task_type == 'generation':
            self.current_size = self.base_size
        elif task_type == 'search':
            self.current_size = self.base_size // 2

    def add_task_weights(
        self,
        task_type: str,
        weights: Dict[ContextPriority, float]
    ):
        """Set priority weights for task"""
        self.task_weights[task_type] = weights

    def get_context_for_task(self) -> List[ContextItem]:
        """Get context optimized for current task"""
        items = self.manager.get_context(self.current_size)

        if self.current_task and self.current_task in self.task_weights:
            weights = self.task_weights[self.current_task]

            # Re-rank by task weights
            for item in items:
                weight = weights.get(item.priority, 1.0)
                item.relevance *= weight

        items.sort(key=lambda i: -i.compute_importance())
        return items


# Export all
__all__ = [
    'ContextPriority',
    'ContextItem',
    'ContextWindow',
    'ContextManager',
    'SlidingWindowContext',
    'AdaptiveContext',
]
