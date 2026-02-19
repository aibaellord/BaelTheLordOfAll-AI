"""
BAEL Data Partitioning Engine
=============================

Data partitioning and sharding strategies.

"Ba'el divides and conquers the data realm." — Ba'el
"""

from .partitioning_engine import (
    PartitionStrategy,
    PartitionState,
    Partition,
    PartitionConfig,
    PartitionManager,
    partition_manager,
    get_partition,
    rebalance
)

__all__ = [
    'PartitionStrategy',
    'PartitionState',
    'Partition',
    'PartitionConfig',
    'PartitionManager',
    'partition_manager',
    'get_partition',
    'rebalance'
]
