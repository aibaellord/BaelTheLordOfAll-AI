"""
🧬 GLOBAL WORKSPACE 🧬
======================
Global workspace theory implementation.

Features:
- Conscious access
- Coalition competition
- Broadcast mechanism
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set
from datetime import datetime
import uuid


@dataclass
class WorkspaceItem:
    """Item in global workspace"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Content
    content: Any = None
    source_module: str = ""

    # Activation
    activation: float = 0.0
    salience: float = 0.0

    # Timing
    entered_at: datetime = field(default_factory=datetime.now)
    duration_ms: int = 0

    # Context
    context: Dict[str, Any] = field(default_factory=dict)

    @property
    def strength(self) -> float:
        """Combined strength"""
        return self.activation * self.salience


@dataclass
class BroadcastEvent:
    """A broadcast event"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    item: WorkspaceItem = None

    # Broadcast info
    broadcast_at: datetime = field(default_factory=datetime.now)
    recipients: List[str] = field(default_factory=list)

    # Results
    responses: Dict[str, Any] = field(default_factory=dict)


class Coalition:
    """
    Coalition of workspace items competing for access.
    """

    def __init__(self, items: List[WorkspaceItem] = None):
        self.id = str(uuid.uuid4())
        self.items = items or []

        # Coalition properties
        self.strength: float = 0.0
        self.coherence: float = 0.0

        # Update strength
        self._update_strength()

    def _update_strength(self):
        """Update coalition strength"""
        if not self.items:
            self.strength = 0.0
            return

        # Sum of item strengths
        total = sum(item.strength for item in self.items)

        # Coherence bonus (items from same source)
        sources = set(item.source_module for item in self.items)
        if len(sources) > 1:
            self.coherence = 0.5  # Multi-source integration bonus
        else:
            self.coherence = 1.0

        self.strength = total * self.coherence

    def add_item(self, item: WorkspaceItem):
        """Add item to coalition"""
        self.items.append(item)
        self._update_strength()

    def remove_item(self, item_id: str):
        """Remove item from coalition"""
        self.items = [i for i in self.items if i.id != item_id]
        self._update_strength()

    def merge(self, other: 'Coalition') -> 'Coalition':
        """Merge with another coalition"""
        merged = Coalition(self.items + other.items)
        return merged


class CoalitionBuilder:
    """
    Builds coalitions from workspace items.
    """

    def __init__(self):
        self.coalition_strategies: List[Callable] = []

    def add_strategy(self, strategy: Callable[[List[WorkspaceItem]], List[Coalition]]):
        """Add coalition building strategy"""
        self.coalition_strategies.append(strategy)

    def build_coalitions(self, items: List[WorkspaceItem]) -> List[Coalition]:
        """Build coalitions from items"""
        all_coalitions = []

        # Apply strategies
        for strategy in self.coalition_strategies:
            try:
                coalitions = strategy(items)
                all_coalitions.extend(coalitions)
            except Exception:
                pass

        # Default: each item is its own coalition
        if not all_coalitions:
            all_coalitions = [Coalition([item]) for item in items]

        return all_coalitions

    def by_source(self, items: List[WorkspaceItem]) -> List[Coalition]:
        """Group by source module"""
        by_source: Dict[str, List[WorkspaceItem]] = {}

        for item in items:
            source = item.source_module
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(item)

        return [Coalition(items) for items in by_source.values()]

    def by_salience(
        self,
        items: List[WorkspaceItem],
        threshold: float = 0.5
    ) -> List[Coalition]:
        """Group by salience level"""
        high_salience = [i for i in items if i.salience >= threshold]
        low_salience = [i for i in items if i.salience < threshold]

        coalitions = []
        if high_salience:
            coalitions.append(Coalition(high_salience))
        if low_salience:
            coalitions.append(Coalition(low_salience))

        return coalitions


class AttentionController:
    """
    Controls attention in global workspace.
    """

    def __init__(self):
        self.focus: Optional[WorkspaceItem] = None
        self.focus_strength: float = 0.0

        # Attention filters
        self.filters: List[Callable[[WorkspaceItem], bool]] = []

        # Attention bias
        self.bias: Dict[str, float] = {}  # source_module -> bias

        # History
        self.attention_history: List[str] = []
        self.max_history: int = 100

    def add_filter(self, filter_fn: Callable[[WorkspaceItem], bool]):
        """Add attention filter"""
        self.filters.append(filter_fn)

    def set_bias(self, source: str, bias: float):
        """Set attention bias for source"""
        self.bias[source] = bias

    def compute_salience(self, item: WorkspaceItem) -> float:
        """Compute item salience"""
        base_salience = item.activation

        # Apply bias
        bias = self.bias.get(item.source_module, 1.0)
        salience = base_salience * bias

        # Novelty bonus (not in recent history)
        if item.id not in self.attention_history:
            salience *= 1.2

        return min(1.0, salience)

    def filter_items(self, items: List[WorkspaceItem]) -> List[WorkspaceItem]:
        """Apply attention filters"""
        filtered = items

        for filter_fn in self.filters:
            filtered = [i for i in filtered if filter_fn(i)]

        return filtered

    def select_focus(self, items: List[WorkspaceItem]) -> Optional[WorkspaceItem]:
        """Select item to focus on"""
        if not items:
            return None

        # Filter
        filtered = self.filter_items(items)

        if not filtered:
            return None

        # Compute salience
        for item in filtered:
            item.salience = self.compute_salience(item)

        # Select highest salience
        best = max(filtered, key=lambda i: i.salience)

        self.focus = best
        self.focus_strength = best.salience

        # Update history
        self.attention_history.append(best.id)
        if len(self.attention_history) > self.max_history:
            self.attention_history.pop(0)

        return best

    def shift_attention(self, item: WorkspaceItem):
        """Shift attention to item"""
        self.focus = item
        self.focus_strength = item.salience
        self.attention_history.append(item.id)


class GlobalWorkspace:
    """
    Global Workspace Theory implementation.
    """

    def __init__(self, capacity: int = 10):
        self.capacity = capacity

        # Workspace contents
        self.contents: List[WorkspaceItem] = []

        # Coalition builder
        self.coalition_builder = CoalitionBuilder()

        # Attention controller
        self.attention = AttentionController()

        # Broadcast history
        self.broadcast_history: List[BroadcastEvent] = []

        # Subscribers (modules that receive broadcasts)
        self.subscribers: Dict[str, Callable[[WorkspaceItem], Any]] = {}

        # Competition threshold
        self.threshold: float = 0.5

    def add_item(self, item: WorkspaceItem) -> bool:
        """Add item to workspace"""
        # Compute salience
        item.salience = self.attention.compute_salience(item)

        # Check threshold
        if item.salience < self.threshold and len(self.contents) >= self.capacity:
            return False

        self.contents.append(item)

        # Enforce capacity
        if len(self.contents) > self.capacity:
            # Remove lowest salience item
            self.contents.sort(key=lambda i: i.salience)
            self.contents.pop(0)

        return True

    def compete(self) -> Optional[Coalition]:
        """Run coalition competition"""
        if not self.contents:
            return None

        # Build coalitions
        coalitions = self.coalition_builder.build_coalitions(self.contents)

        if not coalitions:
            return None

        # Select winning coalition
        winner = max(coalitions, key=lambda c: c.strength)

        return winner

    def broadcast(self, item: WorkspaceItem) -> BroadcastEvent:
        """Broadcast item to all subscribers"""
        event = BroadcastEvent(
            item=item,
            recipients=list(self.subscribers.keys())
        )

        # Notify subscribers
        for sub_id, callback in self.subscribers.items():
            try:
                response = callback(item)
                event.responses[sub_id] = response
            except Exception as e:
                event.responses[sub_id] = {'error': str(e)}

        self.broadcast_history.append(event)

        return event

    def subscribe(self, module_id: str, callback: Callable[[WorkspaceItem], Any]):
        """Subscribe to broadcasts"""
        self.subscribers[module_id] = callback

    def unsubscribe(self, module_id: str):
        """Unsubscribe from broadcasts"""
        if module_id in self.subscribers:
            del self.subscribers[module_id]

    def step(self) -> Optional[BroadcastEvent]:
        """Run one step of global workspace"""
        # Run competition
        winner = self.compete()

        if not winner or not winner.items:
            return None

        # Select focus from winning coalition
        focus = self.attention.select_focus(winner.items)

        if not focus:
            return None

        # Broadcast
        event = self.broadcast(focus)

        # Decay non-broadcast items
        for item in self.contents:
            if item.id != focus.id:
                item.activation *= 0.9

        # Remove decayed items
        self.contents = [i for i in self.contents if i.activation > 0.1]

        return event

    def get_conscious_content(self) -> Optional[WorkspaceItem]:
        """Get current conscious content"""
        return self.attention.focus

    def clear(self):
        """Clear workspace"""
        self.contents.clear()
        self.attention.focus = None


# Export all
__all__ = [
    'WorkspaceItem',
    'BroadcastEvent',
    'Coalition',
    'CoalitionBuilder',
    'AttentionController',
    'GlobalWorkspace',
]
