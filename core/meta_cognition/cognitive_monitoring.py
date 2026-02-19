"""
⚡ COGNITIVE MONITORING ⚡
=========================
Real-time monitoring of cognitive resources.

Tracks:
- Attention allocation
- Working memory usage
- Reasoning load
- Resource optimization
"""

import math
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import deque
import uuid


@dataclass
class CognitiveLoad:
    """Current cognitive load measurement"""
    attention: float = 0.0       # 0-1
    working_memory: float = 0.0  # 0-1
    reasoning: float = 0.0       # 0-1
    perception: float = 0.0      # 0-1

    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def total_load(self) -> float:
        """Total cognitive load"""
        return (self.attention + self.working_memory +
                self.reasoning + self.perception) / 4

    @property
    def is_overloaded(self) -> bool:
        """Check if any resource is overloaded"""
        return any([
            self.attention > 0.9,
            self.working_memory > 0.9,
            self.reasoning > 0.9
        ])


@dataclass
class AttentionTarget:
    """Something attention is focused on"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    priority: float = 0.5
    allocated_attention: float = 0.0
    start_time: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AttentionMonitor:
    """
    Monitors and manages attention allocation.
    """

    def __init__(self, total_attention: float = 1.0):
        self.total_attention = total_attention
        self.targets: Dict[str, AttentionTarget] = {}

        # History
        self.attention_history: deque = deque(maxlen=1000)
        self.switch_count = 0

        # Current focus
        self.primary_focus: Optional[str] = None

    def allocate(
        self,
        target_name: str,
        attention: float,
        priority: float = 0.5
    ) -> AttentionTarget:
        """Allocate attention to target"""
        # Check if can allocate
        current_total = sum(t.allocated_attention for t in self.targets.values())
        available = self.total_attention - current_total

        actual_allocation = min(attention, available)

        if target_name in self.targets:
            target = self.targets[target_name]
            target.allocated_attention = actual_allocation
            target.priority = priority
        else:
            target = AttentionTarget(
                name=target_name,
                priority=priority,
                allocated_attention=actual_allocation
            )
            self.targets[target_name] = target

        # Update primary focus
        if actual_allocation > 0:
            self._update_primary_focus()

        self._record_state()
        return target

    def release(self, target_name: str):
        """Release attention from target"""
        if target_name in self.targets:
            del self.targets[target_name]
            self._update_primary_focus()
            self._record_state()

    def switch_focus(self, target_name: str):
        """Switch primary focus"""
        if target_name not in self.targets:
            # Create new target with default attention
            self.allocate(target_name, 0.5)

        if self.primary_focus != target_name:
            self.primary_focus = target_name
            self.switch_count += 1

        self._record_state()

    def _update_primary_focus(self):
        """Update primary focus based on allocation"""
        if not self.targets:
            self.primary_focus = None
            return

        # Highest allocated attention
        primary = max(self.targets.values(), key=lambda t: t.allocated_attention)
        self.primary_focus = primary.name

    def _record_state(self):
        """Record current attention state"""
        self.attention_history.append({
            'timestamp': datetime.now(),
            'primary_focus': self.primary_focus,
            'targets': {
                name: target.allocated_attention
                for name, target in self.targets.items()
            },
            'total_allocated': sum(t.allocated_attention for t in self.targets.values())
        })

    def get_attention_load(self) -> float:
        """Get current attention load"""
        total = sum(t.allocated_attention for t in self.targets.values())
        return total / self.total_attention

    def get_focus_duration(self, target_name: str) -> float:
        """Get how long focused on target (seconds)"""
        if target_name not in self.targets:
            return 0.0

        target = self.targets[target_name]
        return (datetime.now() - target.start_time).total_seconds()

    def get_fragmentation(self) -> float:
        """
        Get attention fragmentation.

        High fragmentation = attention spread across many targets.
        """
        if not self.targets:
            return 0.0

        allocations = [t.allocated_attention for t in self.targets.values()]

        if len(allocations) == 1:
            return 0.0

        # Entropy-based fragmentation
        total = sum(allocations)
        if total == 0:
            return 0.0

        probs = [a / total for a in allocations if a > 0]
        entropy = -sum(p * math.log2(p + 1e-10) for p in probs)
        max_entropy = math.log2(len(probs))

        return entropy / max_entropy if max_entropy > 0 else 0.0


@dataclass
class MemoryItem:
    """Item in working memory"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: Any = None
    size: float = 1.0  # Memory units
    priority: float = 0.5
    access_count: int = 0
    last_access: datetime = field(default_factory=datetime.now)
    created: datetime = field(default_factory=datetime.now)


class MemoryMonitor:
    """
    Monitors working memory usage.
    """

    def __init__(self, capacity: float = 7.0):  # Miller's magic number
        self.capacity = capacity
        self.items: Dict[str, MemoryItem] = {}

        # History
        self.load_history: deque = deque(maxlen=1000)
        self.eviction_count = 0

    def store(
        self,
        item_id: str,
        content: Any,
        size: float = 1.0,
        priority: float = 0.5
    ) -> bool:
        """Store item in working memory"""
        current_load = self.get_load()

        # Check if room available
        if current_load + size > self.capacity:
            # Try to evict low-priority items
            freed = self._evict_to_fit(size)
            if not freed:
                return False

        item = MemoryItem(
            id=item_id,
            content=content,
            size=size,
            priority=priority
        )
        self.items[item_id] = item

        self._record_state()
        return True

    def retrieve(self, item_id: str) -> Optional[Any]:
        """Retrieve item from working memory"""
        if item_id in self.items:
            item = self.items[item_id]
            item.access_count += 1
            item.last_access = datetime.now()
            return item.content
        return None

    def forget(self, item_id: str):
        """Remove item from working memory"""
        if item_id in self.items:
            del self.items[item_id]
            self._record_state()

    def _evict_to_fit(self, required_size: float) -> bool:
        """Evict items to fit new item"""
        if not self.items:
            return required_size <= self.capacity

        # Sort by priority (low first) then by last access (old first)
        sorted_items = sorted(
            self.items.values(),
            key=lambda i: (i.priority, i.last_access.timestamp())
        )

        freed = 0.0
        to_evict = []

        for item in sorted_items:
            if self.get_load() - freed + required_size <= self.capacity:
                break

            to_evict.append(item.id)
            freed += item.size

        for item_id in to_evict:
            del self.items[item_id]
            self.eviction_count += 1

        return self.get_load() + required_size <= self.capacity

    def _record_state(self):
        """Record memory state"""
        self.load_history.append({
            'timestamp': datetime.now(),
            'load': self.get_load(),
            'item_count': len(self.items)
        })

    def get_load(self) -> float:
        """Get current memory load"""
        return sum(item.size for item in self.items.values())

    def get_load_ratio(self) -> float:
        """Get load as ratio of capacity"""
        return self.get_load() / self.capacity

    def decay(self, amount: float = 0.1):
        """Apply memory decay"""
        now = datetime.now()
        to_decay = []

        for item_id, item in self.items.items():
            age = (now - item.last_access).total_seconds()

            # Decay priority based on age
            decay_factor = 1 - amount * (age / 3600)  # Per hour
            item.priority *= max(0.1, decay_factor)

            if item.priority < 0.1:
                to_decay.append(item_id)

        for item_id in to_decay:
            del self.items[item_id]


class ReasoningMonitor:
    """
    Monitors reasoning processes.
    """

    def __init__(self, max_depth: int = 10, max_breadth: int = 20):
        self.max_depth = max_depth
        self.max_breadth = max_breadth

        # Current reasoning state
        self.current_depth = 0
        self.current_breadth = 0
        self.active_chains: List[str] = []

        # History
        self.depth_history: deque = deque(maxlen=1000)
        self.complexity_history: deque = deque(maxlen=1000)

    def start_chain(self, chain_id: str):
        """Start new reasoning chain"""
        self.active_chains.append(chain_id)
        self.current_breadth = len(self.active_chains)
        self._record_state()

    def end_chain(self, chain_id: str):
        """End reasoning chain"""
        if chain_id in self.active_chains:
            self.active_chains.remove(chain_id)
            self.current_breadth = len(self.active_chains)
            self._record_state()

    def increment_depth(self):
        """Increase reasoning depth"""
        self.current_depth += 1
        self._record_state()

    def decrement_depth(self):
        """Decrease reasoning depth"""
        self.current_depth = max(0, self.current_depth - 1)
        self._record_state()

    def reset_depth(self):
        """Reset depth counter"""
        self.current_depth = 0
        self._record_state()

    def _record_state(self):
        """Record reasoning state"""
        self.depth_history.append({
            'timestamp': datetime.now(),
            'depth': self.current_depth,
            'breadth': self.current_breadth
        })

        self.complexity_history.append({
            'timestamp': datetime.now(),
            'complexity': self.get_complexity()
        })

    def get_depth_ratio(self) -> float:
        """Get depth as ratio of max"""
        return self.current_depth / self.max_depth

    def get_breadth_ratio(self) -> float:
        """Get breadth as ratio of max"""
        return self.current_breadth / self.max_breadth

    def get_complexity(self) -> float:
        """Get reasoning complexity (depth * breadth normalized)"""
        depth_norm = self.current_depth / self.max_depth
        breadth_norm = self.current_breadth / self.max_breadth
        return math.sqrt(depth_norm ** 2 + breadth_norm ** 2) / math.sqrt(2)

    def is_overloaded(self) -> bool:
        """Check if reasoning is overloaded"""
        return (
            self.current_depth >= self.max_depth or
            self.current_breadth >= self.max_breadth
        )


class CognitiveResourceManager:
    """
    Manages all cognitive resources.
    """

    def __init__(self):
        self.attention = AttentionMonitor()
        self.memory = MemoryMonitor()
        self.reasoning = ReasoningMonitor()

        # Load history
        self.load_history: deque = deque(maxlen=1000)

        # Alerts
        self.alerts: List[Dict[str, Any]] = []

    def get_current_load(self) -> CognitiveLoad:
        """Get current cognitive load"""
        load = CognitiveLoad(
            attention=self.attention.get_attention_load(),
            working_memory=self.memory.get_load_ratio(),
            reasoning=self.reasoning.get_complexity(),
            perception=0.0  # Not tracked yet
        )

        self.load_history.append({
            'timestamp': datetime.now(),
            'load': load
        })

        return load

    def check_resources(self) -> List[Dict[str, Any]]:
        """Check resources and return alerts"""
        alerts = []
        load = self.get_current_load()

        if load.attention > 0.8:
            alerts.append({
                'type': 'attention',
                'severity': 'warning' if load.attention < 0.9 else 'critical',
                'message': f'Attention overload: {load.attention:.0%}'
            })

        if load.working_memory > 0.8:
            alerts.append({
                'type': 'memory',
                'severity': 'warning' if load.working_memory < 0.9 else 'critical',
                'message': f'Working memory near capacity: {load.working_memory:.0%}'
            })

        if load.reasoning > 0.8:
            alerts.append({
                'type': 'reasoning',
                'severity': 'warning' if load.reasoning < 0.9 else 'critical',
                'message': f'Reasoning complexity high: {load.reasoning:.0%}'
            })

        fragmentation = self.attention.get_fragmentation()
        if fragmentation > 0.7:
            alerts.append({
                'type': 'attention',
                'severity': 'info',
                'message': f'Attention fragmented across {len(self.attention.targets)} targets'
            })

        self.alerts.extend(alerts)
        return alerts

    def get_available_capacity(self) -> Dict[str, float]:
        """Get available capacity for each resource"""
        load = self.get_current_load()

        return {
            'attention': 1 - load.attention,
            'working_memory': 1 - load.working_memory,
            'reasoning': 1 - load.reasoning,
            'total': 1 - load.total_load
        }

    def optimize_allocation(self):
        """Optimize resource allocation"""
        # Apply memory decay
        self.memory.decay(0.05)

        # Clear old attention targets
        now = datetime.now()
        old_targets = [
            name for name, target in self.attention.targets.items()
            if (now - target.start_time).total_seconds() > 3600  # 1 hour
            and target.priority < 0.3
        ]

        for name in old_targets:
            self.attention.release(name)

    def get_summary(self) -> Dict[str, Any]:
        """Get cognitive resource summary"""
        load = self.get_current_load()
        capacity = self.get_available_capacity()

        return {
            'current_load': {
                'attention': load.attention,
                'working_memory': load.working_memory,
                'reasoning': load.reasoning,
                'total': load.total_load
            },
            'available_capacity': capacity,
            'attention_targets': len(self.attention.targets),
            'memory_items': len(self.memory.items),
            'reasoning_depth': self.reasoning.current_depth,
            'reasoning_chains': len(self.reasoning.active_chains),
            'is_overloaded': load.is_overloaded,
            'recent_alerts': len(self.alerts)
        }


# Export all
__all__ = [
    'CognitiveLoad',
    'AttentionTarget',
    'AttentionMonitor',
    'MemoryItem',
    'MemoryMonitor',
    'ReasoningMonitor',
    'CognitiveResourceManager',
]
