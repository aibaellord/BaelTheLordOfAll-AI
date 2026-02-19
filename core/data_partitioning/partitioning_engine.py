"""
BAEL Data Partitioning Engine Implementation
=============================================

Data partitioning and sharding for scalability.

"Ba'el divides and conquers the data realm." — Ba'el
"""

import asyncio
import hashlib
import logging
import threading
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("BAEL.Partitioning")


# ============================================================================
# ENUMS
# ============================================================================

class PartitionStrategy(Enum):
    """Partitioning strategies."""
    HASH = "hash"               # Hash-based
    RANGE = "range"             # Range-based
    LIST = "list"               # List of values
    ROUND_ROBIN = "round_robin" # Even distribution
    CONSISTENT_HASH = "consistent_hash"  # Consistent hashing
    COMPOSITE = "composite"     # Multiple keys


class PartitionState(Enum):
    """Partition states."""
    ACTIVE = "active"
    READONLY = "readonly"
    REBALANCING = "rebalancing"
    OFFLINE = "offline"


class RebalanceStrategy(Enum):
    """Rebalancing strategies."""
    IMMEDIATE = "immediate"     # Move data now
    GRADUAL = "gradual"         # Move over time
    LAZY = "lazy"               # Move on access


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Partition:
    """A data partition."""
    id: str
    shard_id: str

    # Strategy config
    strategy: PartitionStrategy
    key_column: str

    # Ranges (for range partitioning)
    range_start: Optional[Any] = None
    range_end: Optional[Any] = None

    # Values (for list partitioning)
    values: List[Any] = field(default_factory=list)

    # State
    state: PartitionState = PartitionState.ACTIVE

    # Metrics
    record_count: int = 0
    size_bytes: int = 0

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: Optional[datetime] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def contains(self, value: Any) -> bool:
        """Check if partition contains value."""
        if self.strategy == PartitionStrategy.RANGE:
            return self.range_start <= value < self.range_end
        elif self.strategy == PartitionStrategy.LIST:
            return value in self.values
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'shard_id': self.shard_id,
            'strategy': self.strategy.value,
            'key_column': self.key_column,
            'range_start': self.range_start,
            'range_end': self.range_end,
            'values': self.values,
            'state': self.state.value,
            'record_count': self.record_count,
            'size_bytes': self.size_bytes,
            'metadata': self.metadata
        }


@dataclass
class Shard:
    """A data shard (physical location)."""
    id: str
    host: str
    port: int

    # State
    state: PartitionState = PartitionState.ACTIVE
    weight: float = 1.0

    # Metrics
    partition_count: int = 0
    total_records: int = 0
    total_size_bytes: int = 0

    # Connection info
    connection_string: Optional[str] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'host': self.host,
            'port': self.port,
            'address': self.address,
            'state': self.state.value,
            'weight': self.weight,
            'partition_count': self.partition_count,
            'total_records': self.total_records,
            'total_size_bytes': self.total_size_bytes,
            'metadata': self.metadata
        }


@dataclass
class PartitionConfig:
    """Partitioning configuration."""
    default_strategy: PartitionStrategy = PartitionStrategy.HASH
    num_partitions: int = 16
    virtual_nodes: int = 150  # For consistent hashing
    rebalance_threshold: float = 0.2  # 20% imbalance triggers rebalance


# ============================================================================
# PARTITION MANAGER
# ============================================================================

class PartitionManager:
    """
    Data partitioning manager.

    Features:
    - Multiple partitioning strategies
    - Consistent hashing
    - Automatic rebalancing
    - Partition routing

    "Ba'el distributes the load across all dimensions." — Ba'el
    """

    def __init__(self, config: Optional[PartitionConfig] = None):
        """Initialize partition manager."""
        self.config = config or PartitionConfig()

        # Partitions: partition_id -> Partition
        self._partitions: Dict[str, Partition] = {}

        # Shards: shard_id -> Shard
        self._shards: Dict[str, Shard] = {}

        # Hash ring for consistent hashing
        self._hash_ring: List[Tuple[int, str]] = []

        # Round robin index
        self._rr_index = 0

        # Thread safety
        self._lock = threading.RLock()

        # Stats
        self._stats = {
            'lookups': 0,
            'rebalances': 0
        }

        logger.info("Partition Manager initialized")

    # ========================================================================
    # SHARD MANAGEMENT
    # ========================================================================

    def add_shard(
        self,
        shard_id: str,
        host: str,
        port: int,
        weight: float = 1.0,
        connection_string: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Shard:
        """
        Add a shard.

        Args:
            shard_id: Shard identifier
            host: Shard host
            port: Shard port
            weight: Load balancing weight
            connection_string: Optional connection string
            metadata: Additional metadata

        Returns:
            Shard
        """
        shard = Shard(
            id=shard_id,
            host=host,
            port=port,
            weight=weight,
            connection_string=connection_string,
            metadata=metadata or {}
        )

        with self._lock:
            self._shards[shard_id] = shard
            self._rebuild_hash_ring()

        logger.info(f"Shard added: {shard_id}")

        return shard

    def remove_shard(
        self,
        shard_id: str,
        rebalance: bool = True
    ) -> bool:
        """Remove a shard."""
        with self._lock:
            if shard_id not in self._shards:
                return False

            # Remove partitions on this shard
            partitions_to_remove = [
                p.id for p in self._partitions.values()
                if p.shard_id == shard_id
            ]

            for pid in partitions_to_remove:
                del self._partitions[pid]

            del self._shards[shard_id]

            if rebalance:
                self._rebuild_hash_ring()

            logger.info(f"Shard removed: {shard_id}")

        return True

    def _rebuild_hash_ring(self) -> None:
        """Rebuild consistent hash ring."""
        self._hash_ring = []

        for shard_id, shard in self._shards.items():
            # Add virtual nodes based on weight
            vnodes = int(self.config.virtual_nodes * shard.weight)

            for i in range(vnodes):
                key = f"{shard_id}:{i}"
                hash_value = self._hash(key)
                self._hash_ring.append((hash_value, shard_id))

        self._hash_ring.sort(key=lambda x: x[0])

    # ========================================================================
    # PARTITION MANAGEMENT
    # ========================================================================

    def create_partition(
        self,
        partition_id: str,
        shard_id: str,
        key_column: str,
        strategy: Optional[PartitionStrategy] = None,
        range_start: Optional[Any] = None,
        range_end: Optional[Any] = None,
        values: Optional[List[Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Partition:
        """
        Create a partition.

        Args:
            partition_id: Partition identifier
            shard_id: Target shard
            key_column: Partitioning key column
            strategy: Partitioning strategy
            range_start: Start of range
            range_end: End of range
            values: List values
            metadata: Additional metadata

        Returns:
            Partition
        """
        strategy = strategy or self.config.default_strategy

        partition = Partition(
            id=partition_id,
            shard_id=shard_id,
            strategy=strategy,
            key_column=key_column,
            range_start=range_start,
            range_end=range_end,
            values=values or [],
            metadata=metadata or {}
        )

        with self._lock:
            self._partitions[partition_id] = partition

            # Update shard counts
            if shard_id in self._shards:
                self._shards[shard_id].partition_count += 1

        logger.info(f"Partition created: {partition_id} on {shard_id}")

        return partition

    def delete_partition(self, partition_id: str) -> bool:
        """Delete a partition."""
        with self._lock:
            partition = self._partitions.get(partition_id)

            if not partition:
                return False

            # Update shard counts
            if partition.shard_id in self._shards:
                self._shards[partition.shard_id].partition_count -= 1

            del self._partitions[partition_id]

            logger.info(f"Partition deleted: {partition_id}")

        return True

    # ========================================================================
    # ROUTING
    # ========================================================================

    def get_partition(
        self,
        key: Any,
        strategy: Optional[PartitionStrategy] = None
    ) -> Optional[Partition]:
        """
        Get partition for a key.

        Args:
            key: Partition key value
            strategy: Partitioning strategy

        Returns:
            Partition or None
        """
        strategy = strategy or self.config.default_strategy
        self._stats['lookups'] += 1

        with self._lock:
            if strategy == PartitionStrategy.HASH:
                return self._get_hash_partition(key)
            elif strategy == PartitionStrategy.CONSISTENT_HASH:
                return self._get_consistent_hash_partition(key)
            elif strategy == PartitionStrategy.RANGE:
                return self._get_range_partition(key)
            elif strategy == PartitionStrategy.LIST:
                return self._get_list_partition(key)
            elif strategy == PartitionStrategy.ROUND_ROBIN:
                return self._get_round_robin_partition()

        return None

    def get_shard(
        self,
        key: Any,
        strategy: Optional[PartitionStrategy] = None
    ) -> Optional[Shard]:
        """Get shard for a key."""
        partition = self.get_partition(key, strategy)

        if partition:
            return self._shards.get(partition.shard_id)

        # Direct shard lookup via consistent hash
        if strategy == PartitionStrategy.CONSISTENT_HASH:
            shard_id = self._get_shard_from_ring(key)
            return self._shards.get(shard_id)

        return None

    def _get_hash_partition(self, key: Any) -> Optional[Partition]:
        """Hash-based partition lookup."""
        partitions = list(self._partitions.values())
        if not partitions:
            return None

        hash_value = self._hash(str(key))
        index = hash_value % len(partitions)
        return partitions[index]

    def _get_consistent_hash_partition(self, key: Any) -> Optional[Partition]:
        """Consistent hash partition lookup."""
        shard_id = self._get_shard_from_ring(key)

        if not shard_id:
            return None

        # Find first partition on this shard
        for partition in self._partitions.values():
            if partition.shard_id == shard_id:
                return partition

        return None

    def _get_shard_from_ring(self, key: Any) -> Optional[str]:
        """Get shard from hash ring."""
        if not self._hash_ring:
            return None

        hash_value = self._hash(str(key))

        # Binary search for first node >= hash
        for ring_hash, shard_id in self._hash_ring:
            if ring_hash >= hash_value:
                return shard_id

        # Wrap around
        return self._hash_ring[0][1]

    def _get_range_partition(self, key: Any) -> Optional[Partition]:
        """Range-based partition lookup."""
        for partition in self._partitions.values():
            if partition.strategy == PartitionStrategy.RANGE:
                if partition.contains(key):
                    return partition
        return None

    def _get_list_partition(self, key: Any) -> Optional[Partition]:
        """List-based partition lookup."""
        for partition in self._partitions.values():
            if partition.strategy == PartitionStrategy.LIST:
                if partition.contains(key):
                    return partition
        return None

    def _get_round_robin_partition(self) -> Optional[Partition]:
        """Round-robin partition selection."""
        partitions = list(self._partitions.values())
        if not partitions:
            return None

        partition = partitions[self._rr_index % len(partitions)]
        self._rr_index += 1
        return partition

    def _hash(self, key: str) -> int:
        """Hash function."""
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

    # ========================================================================
    # REBALANCING
    # ========================================================================

    async def rebalance(
        self,
        strategy: RebalanceStrategy = RebalanceStrategy.IMMEDIATE
    ) -> Dict[str, Any]:
        """
        Rebalance partitions across shards.

        Args:
            strategy: Rebalancing strategy

        Returns:
            Rebalance results
        """
        self._stats['rebalances'] += 1

        with self._lock:
            # Calculate ideal distribution
            total_partitions = len(self._partitions)
            total_weight = sum(s.weight for s in self._shards.values())

            if total_weight == 0 or total_partitions == 0:
                return {'moved': 0}

            moves = []

            for shard_id, shard in self._shards.items():
                ideal_count = int((shard.weight / total_weight) * total_partitions)
                current = len([
                    p for p in self._partitions.values()
                    if p.shard_id == shard_id
                ])

                if current > ideal_count:
                    # Need to move some out
                    excess = current - ideal_count
                    shard_partitions = [
                        p for p in self._partitions.values()
                        if p.shard_id == shard_id
                    ]
                    for p in shard_partitions[:excess]:
                        moves.append(p.id)

            # Execute moves
            moved = 0
            for partition_id in moves:
                # Find target shard
                target = min(
                    self._shards.values(),
                    key=lambda s: s.partition_count
                )

                partition = self._partitions.get(partition_id)
                if partition and partition.shard_id != target.id:
                    old_shard = self._shards.get(partition.shard_id)
                    if old_shard:
                        old_shard.partition_count -= 1

                    partition.shard_id = target.id
                    target.partition_count += 1
                    moved += 1

            logger.info(f"Rebalanced {moved} partitions")

            return {
                'moved': moved,
                'total_partitions': total_partitions
            }

    # ========================================================================
    # QUERIES
    # ========================================================================

    def list_partitions(
        self,
        shard_id: Optional[str] = None
    ) -> List[Partition]:
        """List partitions."""
        with self._lock:
            partitions = list(self._partitions.values())
            if shard_id:
                partitions = [p for p in partitions if p.shard_id == shard_id]
            return partitions

    def list_shards(self) -> List[Shard]:
        """List all shards."""
        with self._lock:
            return list(self._shards.values())

    def get_shard_by_id(self, shard_id: str) -> Optional[Shard]:
        """Get shard by ID."""
        return self._shards.get(shard_id)

    # ========================================================================
    # STATS
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        with self._lock:
            shard_stats = {}
            for shard_id, shard in self._shards.items():
                shard_stats[shard_id] = {
                    'partitions': shard.partition_count,
                    'state': shard.state.value
                }

        return {
            'shards': len(self._shards),
            'partitions': len(self._partitions),
            'shard_stats': shard_stats,
            **self._stats
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

partition_manager = PartitionManager()


def get_partition(key: Any, **kwargs) -> Optional[Partition]:
    """Get partition for key."""
    return partition_manager.get_partition(key, **kwargs)


async def rebalance(**kwargs) -> Dict[str, Any]:
    """Rebalance partitions."""
    return await partition_manager.rebalance(**kwargs)
