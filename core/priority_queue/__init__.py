"""
BAEL Priority Queue Engine
==========================

Advanced priority queue with multiple scheduling algorithms.

"Ba'el prioritizes tasks with divine wisdom." — Ba'el
"""

from .priority_queue_engine import (
    # Enums
    PriorityLevel,
    SchedulingAlgorithm,
    QueueState,

    # Data structures
    PriorityItem,
    QueueConfig,

    # Engine
    PriorityQueueEngine,

    # Convenience
    priority_queue,
)

__all__ = [
    'PriorityLevel',
    'SchedulingAlgorithm',
    'QueueState',
    'PriorityItem',
    'QueueConfig',
    'PriorityQueueEngine',
    'priority_queue',
]
