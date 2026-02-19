"""
BAEL Priority Queue Engine Implementation
==========================================

Multi-level priority queue with advanced scheduling.

"Ba'el schedules reality with perfect priority." — Ba'el
"""

import asyncio
import heapq
import logging
import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto

logger = logging.getLogger("BAEL.PriorityQueue")

T = TypeVar('T')


# ============================================================================
# ENUMS
# ============================================================================

class PriorityLevel(Enum):
    """Priority levels."""
    LOWEST = 0
    LOW = 1
    BELOW_NORMAL = 2
    NORMAL = 3
    ABOVE_NORMAL = 4
    HIGH = 5
    HIGHEST = 6
    REALTIME = 7
    CRITICAL = 8


class SchedulingAlgorithm(Enum):
    """Scheduling algorithms."""
    STRICT = "strict"           # Always highest priority first
    WEIGHTED = "weighted"       # Weighted random selection
    ROUND_ROBIN = "round_robin"  # Rotate between priority levels
    FAIR = "fair"               # Prevent starvation
    DEADLINE = "deadline"       # Earliest deadline first
    AGING = "aging"             # Priority increases with wait time


class QueueState(Enum):
    """Queue states."""
    ACTIVE = "active"
    PAUSED = "paused"
    DRAINING = "draining"
    CLOSED = "closed"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass(order=True)
class PriorityItem(Generic[T]):
    """
    Item in the priority queue.

    Ordering: higher priority first, then by timestamp (FIFO within priority)
    """
    # For heap ordering (lower = higher priority in min-heap)
    sort_key: tuple = field(compare=True, default_factory=tuple)

    # Identity
    id: str = field(compare=False, default_factory=lambda: str(uuid.uuid4()))

    # Priority
    priority: PriorityLevel = field(compare=False, default=PriorityLevel.NORMAL)
    base_priority: PriorityLevel = field(compare=False, default=PriorityLevel.NORMAL)

    # Data
    data: Any = field(compare=False, default=None)

    # Scheduling
    deadline: Optional[datetime] = field(compare=False, default=None)
    enqueued_at: datetime = field(compare=False, default_factory=datetime.now)

    # Aging
    age_boost: int = field(compare=False, default=0)
    max_age_boost: int = field(compare=False, default=3)

    # Metadata
    tags: List[str] = field(compare=False, default_factory=list)
    retries: int = field(compare=False, default=0)
    max_retries: int = field(compare=False, default=3)

    def __post_init__(self):
        """Initialize sort key."""
        self.base_priority = self.priority
        self._update_sort_key()

    def _update_sort_key(self):
        """Update sort key for heap ordering."""
        # Negate priority for min-heap (higher priority = lower value)
        priority_value = -(self.priority.value + self.age_boost)

        # Use deadline if set, otherwise use enqueue time
        time_key = self.deadline or self.enqueued_at
        timestamp = time_key.timestamp() if time_key else 0

        self.sort_key = (priority_value, timestamp)

    def apply_aging(self, boost: int = 1) -> None:
        """Apply aging boost to priority."""
        new_boost = min(self.age_boost + boost, self.max_age_boost)
        self.age_boost = new_boost
        self._update_sort_key()

    def reset_priority(self) -> None:
        """Reset to base priority."""
        self.age_boost = 0
        self.priority = self.base_priority
        self._update_sort_key()

    @property
    def effective_priority(self) -> int:
        """Get effective priority with age boost."""
        return self.priority.value + self.age_boost

    @property
    def wait_time_ms(self) -> float:
        """Get wait time in milliseconds."""
        return (datetime.now() - self.enqueued_at).total_seconds() * 1000

    def is_expired(self) -> bool:
        """Check if deadline has passed."""
        if not self.deadline:
            return False
        return datetime.now() > self.deadline

    def can_retry(self) -> bool:
        """Check if item can be retried."""
        return self.retries < self.max_retries


@dataclass
class QueueConfig:
    """Queue configuration."""
    algorithm: SchedulingAlgorithm = SchedulingAlgorithm.STRICT
    max_size: int = 0  # 0 = unlimited

    # Fair scheduling
    max_consecutive_same_priority: int = 5

    # Aging
    aging_enabled: bool = True
    aging_interval_seconds: float = 10.0
    aging_boost: int = 1

    # Timeouts
    default_deadline_seconds: Optional[float] = None

    # Weights for weighted scheduling
    priority_weights: Dict[PriorityLevel, float] = field(default_factory=dict)


# ============================================================================
# PRIORITY QUEUE ENGINE
# ============================================================================

class PriorityQueueEngine(Generic[T]):
    """
    Advanced priority queue with multiple algorithms.

    Features:
    - Multiple priority levels
    - Configurable scheduling algorithms
    - Priority aging to prevent starvation
    - Deadline support
    - Fair scheduling
    - Async support

    "Ba'el's queue ensures perfect order in chaos." — Ba'el
    """

    def __init__(self, config: Optional[QueueConfig] = None):
        """Initialize queue."""
        self.config = config or QueueConfig()

        # Main heap
        self._heap: List[PriorityItem] = []

        # State
        self._state = QueueState.ACTIVE

        # For round-robin
        self._current_priority_idx = 0
        self._consecutive_count = 0
        self._last_priority: Optional[PriorityLevel] = None

        # Background tasks
        self._aging_task: Optional[asyncio.Task] = None

        # Stats
        self._stats = {
            'enqueued': 0,
            'dequeued': 0,
            'expired': 0,
            'aged': 0
        }

        self._lock = threading.RLock()

        # Initialize weights if not set
        if not self.config.priority_weights:
            self.config.priority_weights = {
                level: float(level.value + 1)
                for level in PriorityLevel
            }

        logger.info(f"Priority Queue initialized (algorithm: {self.config.algorithm.value})")

    # ========================================================================
    # QUEUE OPERATIONS
    # ========================================================================

    def enqueue(
        self,
        data: T,
        priority: PriorityLevel = PriorityLevel.NORMAL,
        deadline: Optional[datetime] = None,
        tags: Optional[List[str]] = None
    ) -> PriorityItem[T]:
        """
        Add item to queue.

        Args:
            data: Item data
            priority: Priority level
            deadline: Optional deadline
            tags: Optional tags

        Returns:
            Created priority item
        """
        if self._state == QueueState.CLOSED:
            raise RuntimeError("Queue is closed")

        # Apply default deadline
        if not deadline and self.config.default_deadline_seconds:
            deadline = datetime.now() + timedelta(
                seconds=self.config.default_deadline_seconds
            )

        item = PriorityItem(
            data=data,
            priority=priority,
            deadline=deadline,
            tags=tags or []
        )

        with self._lock:
            # Check max size
            if self.config.max_size > 0 and len(self._heap) >= self.config.max_size:
                raise RuntimeError("Queue is full")

            heapq.heappush(self._heap, item)
            self._stats['enqueued'] += 1

        logger.debug(f"Enqueued item {item.id} with priority {priority.name}")

        return item

    def dequeue(self) -> Optional[PriorityItem[T]]:
        """
        Remove and return highest priority item.

        Returns:
            Highest priority item or None if empty
        """
        if self._state in [QueueState.PAUSED, QueueState.CLOSED]:
            return None

        with self._lock:
            if not self._heap:
                return None

            # Select based on algorithm
            if self.config.algorithm == SchedulingAlgorithm.STRICT:
                item = heapq.heappop(self._heap)

            elif self.config.algorithm == SchedulingAlgorithm.WEIGHTED:
                item = self._weighted_select()

            elif self.config.algorithm == SchedulingAlgorithm.ROUND_ROBIN:
                item = self._round_robin_select()

            elif self.config.algorithm == SchedulingAlgorithm.FAIR:
                item = self._fair_select()

            elif self.config.algorithm == SchedulingAlgorithm.DEADLINE:
                item = self._deadline_select()

            elif self.config.algorithm == SchedulingAlgorithm.AGING:
                item = heapq.heappop(self._heap)

            else:
                item = heapq.heappop(self._heap)

            if item:
                self._stats['dequeued'] += 1
                self._last_priority = item.priority

            return item

    def peek(self) -> Optional[PriorityItem[T]]:
        """Peek at highest priority item without removing."""
        with self._lock:
            if not self._heap:
                return None
            return self._heap[0]

    def remove(self, item_id: str) -> bool:
        """Remove item by ID."""
        with self._lock:
            for i, item in enumerate(self._heap):
                if item.id == item_id:
                    # Remove and re-heapify
                    self._heap[i] = self._heap[-1]
                    self._heap.pop()
                    heapq.heapify(self._heap)
                    return True
        return False

    def update_priority(
        self,
        item_id: str,
        new_priority: PriorityLevel
    ) -> bool:
        """Update item priority."""
        with self._lock:
            for item in self._heap:
                if item.id == item_id:
                    item.priority = new_priority
                    item._update_sort_key()
                    heapq.heapify(self._heap)
                    return True
        return False

    # ========================================================================
    # SCHEDULING ALGORITHMS
    # ========================================================================

    def _weighted_select(self) -> Optional[PriorityItem]:
        """Weighted random selection."""
        import random

        if not self._heap:
            return None

        # Calculate weights
        weights = []
        for item in self._heap:
            weight = self.config.priority_weights.get(item.priority, 1.0)
            weights.append(weight)

        # Random selection
        total = sum(weights)
        r = random.random() * total
        cumulative = 0.0

        for i, weight in enumerate(weights):
            cumulative += weight
            if r < cumulative:
                item = self._heap[i]
                self._heap[i] = self._heap[-1]
                self._heap.pop()
                heapq.heapify(self._heap)
                return item

        return heapq.heappop(self._heap)

    def _round_robin_select(self) -> Optional[PriorityItem]:
        """Round-robin between priority levels."""
        if not self._heap:
            return None

        # Get unique priorities
        priorities = sorted(
            set(item.priority for item in self._heap),
            key=lambda p: p.value,
            reverse=True
        )

        if not priorities:
            return heapq.heappop(self._heap)

        # Select priority level
        target_priority = priorities[self._current_priority_idx % len(priorities)]

        # Find item with target priority
        for i, item in enumerate(self._heap):
            if item.priority == target_priority:
                self._heap[i] = self._heap[-1]
                self._heap.pop()
                heapq.heapify(self._heap)

                self._current_priority_idx += 1
                return item

        # Fallback
        self._current_priority_idx += 1
        return heapq.heappop(self._heap)

    def _fair_select(self) -> Optional[PriorityItem]:
        """Fair selection with starvation prevention."""
        if not self._heap:
            return None

        # Check if we've taken too many from same priority
        if (self._last_priority and
            self._consecutive_count >= self.config.max_consecutive_same_priority):

            # Find item from different priority
            for i, item in enumerate(self._heap):
                if item.priority != self._last_priority:
                    self._heap[i] = self._heap[-1]
                    self._heap.pop()
                    heapq.heapify(self._heap)

                    self._consecutive_count = 1
                    return item

        # Normal selection
        item = heapq.heappop(self._heap)

        if item.priority == self._last_priority:
            self._consecutive_count += 1
        else:
            self._consecutive_count = 1

        return item

    def _deadline_select(self) -> Optional[PriorityItem]:
        """Earliest deadline first."""
        if not self._heap:
            return None

        # Find earliest deadline
        deadline_items = [
            (i, item) for i, item in enumerate(self._heap)
            if item.deadline
        ]

        if deadline_items:
            deadline_items.sort(key=lambda x: x[1].deadline)
            idx, item = deadline_items[0]

            # Check if deadline is imminent
            if item.deadline and item.deadline < datetime.now() + timedelta(seconds=5):
                self._heap[idx] = self._heap[-1]
                self._heap.pop()
                heapq.heapify(self._heap)
                return item

        # Fallback to normal priority
        return heapq.heappop(self._heap)

    # ========================================================================
    # AGING
    # ========================================================================

    async def start_aging(self) -> None:
        """Start aging background task."""
        if not self.config.aging_enabled:
            return

        if self._aging_task:
            return

        self._aging_task = asyncio.create_task(self._aging_loop())
        logger.debug("Aging task started")

    async def stop_aging(self) -> None:
        """Stop aging background task."""
        if self._aging_task:
            self._aging_task.cancel()
            try:
                await self._aging_task
            except asyncio.CancelledError:
                pass
            self._aging_task = None

    async def _aging_loop(self) -> None:
        """Background aging loop."""
        while True:
            try:
                await asyncio.sleep(self.config.aging_interval_seconds)
                self._apply_aging()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Aging error: {e}")

    def _apply_aging(self) -> None:
        """Apply aging to all items."""
        with self._lock:
            for item in self._heap:
                item.apply_aging(self.config.aging_boost)
                self._stats['aged'] += 1

            heapq.heapify(self._heap)

    # ========================================================================
    # ASYNC OPERATIONS
    # ========================================================================

    async def enqueue_async(
        self,
        data: T,
        **kwargs
    ) -> PriorityItem[T]:
        """Async enqueue."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.enqueue(data, **kwargs)
        )

    async def dequeue_async(
        self,
        timeout: Optional[float] = None
    ) -> Optional[PriorityItem[T]]:
        """
        Async dequeue with optional timeout.

        Will wait for item if queue is empty.
        """
        start = time.time()

        while True:
            item = self.dequeue()
            if item:
                return item

            if timeout and (time.time() - start) >= timeout:
                return None

            await asyncio.sleep(0.1)

    # ========================================================================
    # STATE MANAGEMENT
    # ========================================================================

    def pause(self) -> None:
        """Pause queue processing."""
        self._state = QueueState.PAUSED
        logger.info("Queue paused")

    def resume(self) -> None:
        """Resume queue processing."""
        self._state = QueueState.ACTIVE
        logger.info("Queue resumed")

    def drain(self) -> None:
        """Start draining (no new items, process existing)."""
        self._state = QueueState.DRAINING
        logger.info("Queue draining")

    def close(self) -> None:
        """Close queue."""
        self._state = QueueState.CLOSED
        logger.info("Queue closed")

    def clear(self) -> int:
        """Clear all items."""
        with self._lock:
            count = len(self._heap)
            self._heap.clear()
        return count

    # ========================================================================
    # QUERIES
    # ========================================================================

    def __len__(self) -> int:
        """Get queue size."""
        return len(self._heap)

    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return len(self._heap) == 0

    def get_by_priority(
        self,
        priority: PriorityLevel
    ) -> List[PriorityItem[T]]:
        """Get all items with specific priority."""
        with self._lock:
            return [item for item in self._heap if item.priority == priority]

    def get_expired(self) -> List[PriorityItem[T]]:
        """Get expired items."""
        with self._lock:
            return [item for item in self._heap if item.is_expired()]

    def remove_expired(self) -> int:
        """Remove expired items."""
        with self._lock:
            expired = [item for item in self._heap if item.is_expired()]

            for item in expired:
                self._heap.remove(item)
                self._stats['expired'] += 1

            heapq.heapify(self._heap)
            return len(expired)

    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        with self._lock:
            by_priority = {}
            for level in PriorityLevel:
                count = sum(1 for item in self._heap if item.priority == level)
                if count > 0:
                    by_priority[level.name] = count

            return {
                'size': len(self._heap),
                'state': self._state.value,
                'algorithm': self.config.algorithm.value,
                'by_priority': by_priority,
                'enqueued': self._stats['enqueued'],
                'dequeued': self._stats['dequeued'],
                'expired': self._stats['expired'],
                'aged': self._stats['aged'],
                'aging_enabled': self.config.aging_enabled
            }


# ============================================================================
# CONVENIENCE
# ============================================================================

priority_queue = PriorityQueueEngine()
