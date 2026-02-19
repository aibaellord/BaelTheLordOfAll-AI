"""
BAEL Working Memory
====================

Short-term active memory for AI agents.
Manages current context and attention.

Features:
- Limited capacity buffer
- Attention management
- Context windowing
- Activation decay
- Rehearsal mechanisms
"""

import asyncio
import heapq
import logging
import math
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class ActivationLevel(Enum):
    """Activation levels for items."""
    DORMANT = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    FOCUSED = 4


@dataclass
class WorkingItem:
    """An item in working memory."""
    id: str
    content: Any

    # Activation
    activation: float = 1.0  # 0.0 to 1.0
    activation_level: ActivationLevel = ActivationLevel.MEDIUM

    # Timing
    added_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0

    # Associations
    links: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    # Priority
    priority: float = 0.5

    def decay(self, rate: float = 0.1) -> None:
        """Apply activation decay."""
        time_diff = (datetime.now() - self.last_accessed).total_seconds()
        self.activation *= math.exp(-rate * time_diff / 60)  # Per minute

        # Update level
        if self.activation < 0.2:
            self.activation_level = ActivationLevel.DORMANT
        elif self.activation < 0.4:
            self.activation_level = ActivationLevel.LOW
        elif self.activation < 0.6:
            self.activation_level = ActivationLevel.MEDIUM
        elif self.activation < 0.8:
            self.activation_level = ActivationLevel.HIGH
        else:
            self.activation_level = ActivationLevel.FOCUSED

    def boost(self, amount: float = 0.2) -> None:
        """Boost activation."""
        self.activation = min(1.0, self.activation + amount)
        self.last_accessed = datetime.now()
        self.access_count += 1

    def __lt__(self, other: "WorkingItem") -> bool:
        """Compare by activation for heap."""
        return self.activation < other.activation


@dataclass
class AttentionBuffer:
    """Attention buffer for focused items."""
    capacity: int = 4  # Miller's 7±2, using 4 for safety
    items: List[WorkingItem] = field(default_factory=list)

    def add(self, item: WorkingItem) -> Optional[WorkingItem]:
        """Add item to attention, return evicted if any."""
        evicted = None

        if len(self.items) >= self.capacity:
            # Evict lowest activation
            self.items.sort(key=lambda x: x.activation)
            evicted = self.items.pop(0)

        item.activation_level = ActivationLevel.FOCUSED
        self.items.append(item)

        return evicted

    def remove(self, item_id: str) -> bool:
        """Remove item from attention."""
        for i, item in enumerate(self.items):
            if item.id == item_id:
                del self.items[i]
                return True
        return False

    def get_focused(self) -> List[WorkingItem]:
        """Get all focused items."""
        return list(self.items)


@dataclass
class ContextWindow:
    """Sliding context window."""
    max_tokens: int = 8000
    items: List[WorkingItem] = field(default_factory=list)
    current_tokens: int = 0

    def add(self, item: WorkingItem, tokens: int) -> List[WorkingItem]:
        """Add item, return evicted items if over capacity."""
        evicted = []

        # Evict oldest/least active if needed
        while self.current_tokens + tokens > self.max_tokens and self.items:
            self.items.sort(key=lambda x: (x.activation, -x.added_at.timestamp()))
            removed = self.items.pop(0)
            # Estimate token reduction (placeholder)
            self.current_tokens -= 100
            evicted.append(removed)

        self.items.append(item)
        self.current_tokens += tokens

        return evicted

    def get_context(self) -> List[Any]:
        """Get context contents."""
        return [item.content for item in self.items]


@dataclass
class WorkingContext:
    """Current working context."""
    task: Optional[str] = None
    goal: Optional[str] = None

    # State
    variables: Dict[str, Any] = field(default_factory=dict)

    # History
    recent_actions: List[str] = field(default_factory=list)

    # Focus
    focus_stack: List[str] = field(default_factory=list)

    def push_focus(self, focus: str) -> None:
        """Push a new focus."""
        self.focus_stack.append(focus)

    def pop_focus(self) -> Optional[str]:
        """Pop current focus."""
        if self.focus_stack:
            return self.focus_stack.pop()
        return None

    def current_focus(self) -> Optional[str]:
        """Get current focus."""
        return self.focus_stack[-1] if self.focus_stack else None


class WorkingMemory:
    """
    Working memory system for BAEL.

    Manages active context and attention.
    """

    def __init__(
        self,
        capacity: int = 50,
        attention_slots: int = 4,
        context_tokens: int = 8000,
        decay_rate: float = 0.1,
    ):
        self.capacity = capacity
        self.decay_rate = decay_rate

        # Storage
        self._items: Dict[str, WorkingItem] = {}

        # Attention buffer
        self.attention = AttentionBuffer(capacity=attention_slots)

        # Context window
        self.context = ContextWindow(max_tokens=context_tokens)

        # Working context
        self.working_context = WorkingContext()

        # Rehearsal queue
        self._rehearsal_queue: deque = deque(maxlen=20)

        # Stats
        self.stats = {
            "items_added": 0,
            "items_evicted": 0,
            "retrievals": 0,
            "rehearsals": 0,
        }

    def store(
        self,
        item_id: str,
        content: Any,
        priority: float = 0.5,
        focus: bool = False,
        tags: Optional[List[str]] = None,
    ) -> WorkingItem:
        """
        Store item in working memory.

        Args:
            item_id: Item identifier
            content: Content to store
            priority: Item priority
            focus: Whether to focus attention
            tags: Item tags

        Returns:
            Stored item
        """
        item = WorkingItem(
            id=item_id,
            content=content,
            priority=priority,
            tags=tags or [],
            activation=1.0 if focus else 0.7,
        )

        # Check capacity
        if len(self._items) >= self.capacity and item_id not in self._items:
            self._evict_lowest()

        self._items[item_id] = item
        self.stats["items_added"] += 1

        # Add to attention if focused
        if focus:
            evicted = self.attention.add(item)
            if evicted:
                evicted.activation_level = ActivationLevel.HIGH

        # Add to context window
        tokens = self._estimate_tokens(content)
        self.context.add(item, tokens)

        # Add to rehearsal queue
        self._rehearsal_queue.append(item_id)

        logger.debug(f"Stored in working memory: {item_id}")

        return item

    def _estimate_tokens(self, content: Any) -> int:
        """Estimate token count for content."""
        if isinstance(content, str):
            return len(content.split()) * 1.3  # Rough estimate
        elif isinstance(content, dict):
            return sum(self._estimate_tokens(v) for v in content.values()) + len(content)
        elif isinstance(content, list):
            return sum(self._estimate_tokens(i) for i in content)
        else:
            return 10  # Default

    def retrieve(
        self,
        item_id: str,
        boost: bool = True,
    ) -> Optional[WorkingItem]:
        """Retrieve item from working memory."""
        if item_id not in self._items:
            return None

        item = self._items[item_id]
        self.stats["retrievals"] += 1

        if boost:
            item.boost()

        return item

    def focus(self, item_id: str) -> bool:
        """Focus attention on an item."""
        if item_id not in self._items:
            return False

        item = self._items[item_id]
        item.activation = 1.0

        evicted = self.attention.add(item)
        if evicted:
            evicted.activation_level = ActivationLevel.HIGH

        return True

    def unfocus(self, item_id: str) -> bool:
        """Remove item from attention focus."""
        return self.attention.remove(item_id)

    def search(
        self,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        min_activation: float = 0.0,
        limit: int = 10,
    ) -> List[WorkingItem]:
        """Search working memory."""
        results = []

        for item in self._items.values():
            if item.activation < min_activation:
                continue

            if tags and not any(t in item.tags for t in tags):
                continue

            if query:
                content_str = str(item.content).lower()
                if query.lower() not in content_str:
                    continue

            results.append(item)

        # Sort by activation
        results.sort(key=lambda x: x.activation, reverse=True)

        return results[:limit]

    def get_focused(self) -> List[WorkingItem]:
        """Get focused items."""
        return self.attention.get_focused()

    def get_context(self) -> List[Any]:
        """Get current context contents."""
        return self.context.get_context()

    def apply_decay(self) -> int:
        """Apply decay to all items."""
        decayed = 0
        to_remove = []

        for item_id, item in self._items.items():
            item.decay(self.decay_rate)

            if item.activation < 0.05:
                to_remove.append(item_id)

            decayed += 1

        # Remove dormant items
        for item_id in to_remove:
            self._remove_item(item_id)

        return decayed

    def rehearse(self) -> int:
        """Rehearse items to prevent decay."""
        rehearsed = 0

        for _ in range(min(3, len(self._rehearsal_queue))):
            if not self._rehearsal_queue:
                break

            item_id = self._rehearsal_queue.popleft()

            if item_id in self._items:
                self._items[item_id].boost(0.1)
                self._rehearsal_queue.append(item_id)
                rehearsed += 1

        self.stats["rehearsals"] += rehearsed

        return rehearsed

    def _evict_lowest(self) -> None:
        """Evict lowest activation item."""
        if not self._items:
            return

        # Find lowest activation not in attention
        focused_ids = {i.id for i in self.attention.items}

        candidates = [
            (item.activation, item_id)
            for item_id, item in self._items.items()
            if item_id not in focused_ids
        ]

        if candidates:
            _, evict_id = min(candidates)
            self._remove_item(evict_id)
            self.stats["items_evicted"] += 1

    def _remove_item(self, item_id: str) -> None:
        """Remove an item."""
        if item_id in self._items:
            del self._items[item_id]
            self.attention.remove(item_id)

    def clear(self) -> None:
        """Clear working memory."""
        self._items.clear()
        self.attention.items.clear()
        self.context.items.clear()
        self.context.current_tokens = 0
        self._rehearsal_queue.clear()
        self.working_context = WorkingContext()

    def set_task(self, task: str, goal: str) -> None:
        """Set current task and goal."""
        self.working_context.task = task
        self.working_context.goal = goal

    def set_variable(self, name: str, value: Any) -> None:
        """Set a context variable."""
        self.working_context.variables[name] = value

    def get_variable(self, name: str) -> Any:
        """Get a context variable."""
        return self.working_context.variables.get(name)

    def add_action(self, action: str) -> None:
        """Add action to history."""
        self.working_context.recent_actions.append(action)
        if len(self.working_context.recent_actions) > 50:
            self.working_context.recent_actions = self.working_context.recent_actions[-50:]

    def get_summary(self) -> Dict[str, Any]:
        """Get working memory summary."""
        return {
            "total_items": len(self._items),
            "focused_items": len(self.attention.items),
            "context_tokens": self.context.current_tokens,
            "avg_activation": (
                sum(i.activation for i in self._items.values()) / len(self._items)
                if self._items else 0
            ),
            "task": self.working_context.task,
            "goal": self.working_context.goal,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return {
            **self.stats,
            **self.get_summary(),
        }


def demo():
    """Demonstrate working memory."""
    print("=" * 60)
    print("BAEL Working Memory Demo")
    print("=" * 60)

    memory = WorkingMemory(capacity=20, attention_slots=4)

    # Set task
    memory.set_task("Debug authentication", "Fix login issue")

    # Store items
    print("\nStoring items...")

    memory.store("error", {"type": "AuthError", "line": 42}, priority=0.9, focus=True, tags=["error"])
    memory.store("file", "auth_handler.py", priority=0.8, tags=["context"])
    memory.store("hypothesis", "Token expired", priority=0.7, focus=True, tags=["analysis"])
    memory.store("code", "def verify_token()...", priority=0.6, tags=["code"])

    # Add some lower priority items
    for i in range(5):
        memory.store(f"note_{i}", f"Debug note {i}", priority=0.3, tags=["notes"])

    print(f"  Stored {len(memory._items)} items")

    # Check attention
    print("\nFocused items:")
    for item in memory.get_focused():
        print(f"  - {item.id}: activation={item.activation:.2f}")

    # Set context variables
    memory.set_variable("current_file", "auth_handler.py")
    memory.set_variable("line_number", 42)

    # Retrieve and boost
    print("\nRetrieving...")
    error = memory.retrieve("error")
    print(f"  Error: {error.content}")
    print(f"  Access count: {error.access_count}")

    # Search
    print("\nSearching...")
    results = memory.search(tags=["error", "analysis"])
    print(f"  Found {len(results)} items with error/analysis tags")

    # Apply decay
    print("\nApplying decay...")
    import time
    time.sleep(0.1)  # Small delay for demo
    decayed = memory.apply_decay()
    print(f"  Decayed {decayed} items")

    # Rehearse
    rehearsed = memory.rehearse()
    print(f"  Rehearsed {rehearsed} items")

    # Summary
    print("\nWorking memory summary:")
    summary = memory.get_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")

    # Get context
    print(f"\nContext items: {len(memory.get_context())}")

    print(f"\nStats: {memory.get_stats()}")


if __name__ == "__main__":
    demo()
