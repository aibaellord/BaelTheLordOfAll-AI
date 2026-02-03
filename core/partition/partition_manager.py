#!/usr/bin/env python3
"""
BAEL - Partition Manager
Advanced data partitioning for AI agent operations.

Features:
- Hash partitioning
- Range partitioning
- List partitioning
- Composite partitioning
- Dynamic rebalancing
- Partition routing
- Shard management
- Replica management
- Statistics tracking
- Partition pruning
"""

import asyncio
import bisect
import hashlib
import random
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Awaitable, Callable, Dict, Generic, Iterator, List,
                    Optional, Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')


# =============================================================================
# ENUMS
# =============================================================================

class PartitionStrategy(Enum):
    """Partition strategies."""
    HASH = "hash"
    RANGE = "range"
    LIST = "list"
    ROUND_ROBIN = "round_robin"
    CONSISTENT_HASH = "consistent_hash"
    COMPOSITE = "composite"


class PartitionState(Enum):
    """Partition state."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MIGRATING = "migrating"
    SPLITTING = "splitting"
    MERGING = "merging"
    READONLY = "readonly"


class RebalanceState(Enum):
    """Rebalance state."""
    IDLE = "idle"
    PLANNING = "planning"
    MIGRATING = "migrating"
    COMPLETING = "completing"
    FAILED = "failed"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class PartitionConfig:
    """Partition configuration."""
    strategy: PartitionStrategy = PartitionStrategy.HASH
    num_partitions: int = 16
    replication_factor: int = 1
    virtual_nodes: int = 100  # For consistent hashing
    partition_key: str = "id"
    range_bounds: List[Any] = field(default_factory=list)
    list_values: Dict[str, int] = field(default_factory=dict)  # value -> partition


@dataclass
class Partition:
    """Partition definition."""
    partition_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    partition_num: int = 0
    state: PartitionState = PartitionState.ACTIVE
    node_id: Optional[str] = None
    replicas: List[str] = field(default_factory=list)
    key_range: Tuple[Any, Any] = (None, None)
    item_count: int = 0
    size_bytes: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PartitionStats:
    """Partition statistics."""
    partition_id: str = ""
    item_count: int = 0
    size_bytes: int = 0
    reads: int = 0
    writes: int = 0
    last_read: Optional[datetime] = None
    last_write: Optional[datetime] = None


@dataclass
class RebalancePlan:
    """Rebalance plan."""
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: RebalanceState = RebalanceState.IDLE
    moves: List[Tuple[str, str, str]] = field(default_factory=list)  # (key, from, to)
    progress: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class ShardInfo:
    """Shard information."""
    shard_id: str = ""
    partitions: List[str] = field(default_factory=list)
    node_id: str = ""
    is_primary: bool = True
    load: float = 0.0


# =============================================================================
# PARTITION FUNCTIONS
# =============================================================================

class PartitionFunction(ABC):
    """Base partition function."""

    @abstractmethod
    def get_partition(self, key: Any, num_partitions: int) -> int:
        """Get partition number for key."""
        pass


class HashPartition(PartitionFunction):
    """Hash-based partitioning."""

    def get_partition(self, key: Any, num_partitions: int) -> int:
        key_str = str(key)
        h = hashlib.md5(key_str.encode()).hexdigest()
        return int(h, 16) % num_partitions


class RangePartition(PartitionFunction):
    """Range-based partitioning."""

    def __init__(self, bounds: List[Any]):
        self._bounds = sorted(bounds)

    def get_partition(self, key: Any, num_partitions: int) -> int:
        return bisect.bisect_right(self._bounds, key)


class ListPartition(PartitionFunction):
    """List-based partitioning."""

    def __init__(self, value_map: Dict[Any, int]):
        self._map = value_map
        self._default = 0

    def get_partition(self, key: Any, num_partitions: int) -> int:
        return self._map.get(key, self._default) % num_partitions


class RoundRobinPartition(PartitionFunction):
    """Round-robin partitioning."""

    def __init__(self):
        self._counter = 0
        self._lock = threading.Lock()

    def get_partition(self, key: Any, num_partitions: int) -> int:
        with self._lock:
            partition = self._counter % num_partitions
            self._counter += 1
            return partition


# =============================================================================
# CONSISTENT HASH RING
# =============================================================================

class ConsistentHashRing:
    """Consistent hash ring for partition routing."""

    def __init__(self, virtual_nodes: int = 100):
        self._virtual_nodes = virtual_nodes
        self._ring: List[Tuple[int, str]] = []
        self._nodes: Set[str] = set()
        self._lock = threading.RLock()

    def _hash(self, key: str) -> int:
        """Hash key to ring position."""
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

    def add_node(self, node_id: str) -> None:
        """Add node to ring."""
        with self._lock:
            if node_id in self._nodes:
                return

            self._nodes.add(node_id)

            for i in range(self._virtual_nodes):
                key = f"{node_id}:{i}"
                h = self._hash(key)
                bisect.insort(self._ring, (h, node_id))

    def remove_node(self, node_id: str) -> None:
        """Remove node from ring."""
        with self._lock:
            if node_id not in self._nodes:
                return

            self._nodes.remove(node_id)
            self._ring = [(h, n) for h, n in self._ring if n != node_id]

    def get_node(self, key: str) -> Optional[str]:
        """Get node for key."""
        with self._lock:
            if not self._ring:
                return None

            h = self._hash(key)
            idx = bisect.bisect_left(self._ring, (h,))

            if idx >= len(self._ring):
                idx = 0

            return self._ring[idx][1]

    def get_nodes(self, key: str, count: int = 1) -> List[str]:
        """Get multiple nodes for key (for replication)."""
        with self._lock:
            if not self._ring:
                return []

            h = self._hash(key)
            idx = bisect.bisect_left(self._ring, (h,))

            nodes = []
            seen = set()

            for i in range(len(self._ring)):
                pos = (idx + i) % len(self._ring)
                node = self._ring[pos][1]

                if node not in seen:
                    seen.add(node)
                    nodes.append(node)

                    if len(nodes) >= count:
                        break

            return nodes

    def get_all_nodes(self) -> List[str]:
        """Get all nodes."""
        with self._lock:
            return list(self._nodes)


# =============================================================================
# PARTITION ROUTER
# =============================================================================

class PartitionRouter:
    """Routes requests to partitions."""

    def __init__(self, config: PartitionConfig):
        self._config = config
        self._function = self._create_function(config)
        self._partitions: Dict[int, Partition] = {}
        self._consistent_ring: Optional[ConsistentHashRing] = None

        if config.strategy == PartitionStrategy.CONSISTENT_HASH:
            self._consistent_ring = ConsistentHashRing(config.virtual_nodes)

        self._lock = threading.RLock()

    def _create_function(self, config: PartitionConfig) -> PartitionFunction:
        """Create partition function."""
        if config.strategy == PartitionStrategy.HASH:
            return HashPartition()
        elif config.strategy == PartitionStrategy.RANGE:
            return RangePartition(config.range_bounds)
        elif config.strategy == PartitionStrategy.LIST:
            return ListPartition(config.list_values)
        elif config.strategy == PartitionStrategy.ROUND_ROBIN:
            return RoundRobinPartition()

        return HashPartition()

    def route(self, key: Any) -> Optional[Partition]:
        """Route key to partition."""
        with self._lock:
            if self._config.strategy == PartitionStrategy.CONSISTENT_HASH:
                if self._consistent_ring:
                    node = self._consistent_ring.get_node(str(key))
                    if node:
                        # Find partition on this node
                        for p in self._partitions.values():
                            if p.node_id == node:
                                return p
                return None

            partition_num = self._function.get_partition(
                key,
                self._config.num_partitions
            )

            return self._partitions.get(partition_num)

    def route_with_replicas(
        self,
        key: Any,
        count: int = 1
    ) -> List[Partition]:
        """Route key to partition and replicas."""
        with self._lock:
            if self._config.strategy == PartitionStrategy.CONSISTENT_HASH:
                if self._consistent_ring:
                    nodes = self._consistent_ring.get_nodes(str(key), count)
                    partitions = []
                    for node in nodes:
                        for p in self._partitions.values():
                            if p.node_id == node:
                                partitions.append(p)
                                break
                    return partitions
                return []

            partition_num = self._function.get_partition(
                key,
                self._config.num_partitions
            )

            primary = self._partitions.get(partition_num)
            if not primary:
                return []

            result = [primary]

            # Add replicas
            for replica_id in primary.replicas:
                for p in self._partitions.values():
                    if p.partition_id == replica_id:
                        result.append(p)

            return result[:count]

    def add_partition(self, partition: Partition) -> None:
        """Add partition to router."""
        with self._lock:
            self._partitions[partition.partition_num] = partition

            if self._consistent_ring and partition.node_id:
                self._consistent_ring.add_node(partition.node_id)

    def remove_partition(self, partition_num: int) -> Optional[Partition]:
        """Remove partition from router."""
        with self._lock:
            partition = self._partitions.pop(partition_num, None)

            if partition and self._consistent_ring and partition.node_id:
                # Only remove if no other partitions on this node
                has_others = any(
                    p.node_id == partition.node_id
                    for p in self._partitions.values()
                )
                if not has_others:
                    self._consistent_ring.remove_node(partition.node_id)

            return partition

    def get_all_partitions(self) -> List[Partition]:
        """Get all partitions."""
        with self._lock:
            return list(self._partitions.values())


# =============================================================================
# PARTITION MANAGER
# =============================================================================

class PartitionManager:
    """
    Partition Manager for BAEL.

    Advanced data partitioning.
    """

    def __init__(self, config: Optional[PartitionConfig] = None):
        self._config = config or PartitionConfig()
        self._router = PartitionRouter(self._config)
        self._data: Dict[str, Dict[str, Any]] = defaultdict(dict)  # partition_id -> {key: value}
        self._stats: Dict[str, PartitionStats] = {}
        self._rebalance_plan: Optional[RebalancePlan] = None
        self._lock = threading.RLock()

        # Initialize partitions
        self._initialize_partitions()

    def _initialize_partitions(self) -> None:
        """Initialize partitions."""
        for i in range(self._config.num_partitions):
            partition = Partition(
                partition_num=i,
                node_id=f"node_{i % 4}"  # Distribute across 4 nodes
            )
            self._router.add_partition(partition)
            self._stats[partition.partition_id] = PartitionStats(
                partition_id=partition.partition_id
            )

    # -------------------------------------------------------------------------
    # DATA OPERATIONS
    # -------------------------------------------------------------------------

    def put(self, key: str, value: Any) -> bool:
        """Put value in appropriate partition."""
        partition = self._router.route(key)

        if not partition:
            return False

        with self._lock:
            self._data[partition.partition_id][key] = value
            partition.item_count = len(self._data[partition.partition_id])

            stats = self._stats.get(partition.partition_id)
            if stats:
                stats.writes += 1
                stats.last_write = datetime.utcnow()
                stats.item_count = partition.item_count

        return True

    def get(self, key: str) -> Optional[Any]:
        """Get value from appropriate partition."""
        partition = self._router.route(key)

        if not partition:
            return None

        with self._lock:
            stats = self._stats.get(partition.partition_id)
            if stats:
                stats.reads += 1
                stats.last_read = datetime.utcnow()

            return self._data[partition.partition_id].get(key)

    def delete(self, key: str) -> bool:
        """Delete value from partition."""
        partition = self._router.route(key)

        if not partition:
            return False

        with self._lock:
            if key in self._data[partition.partition_id]:
                del self._data[partition.partition_id][key]
                partition.item_count = len(self._data[partition.partition_id])
                return True

        return False

    def get_from_partition(
        self,
        partition_num: int,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get all data from a partition."""
        partitions = self._router.get_all_partitions()

        for partition in partitions:
            if partition.partition_num == partition_num:
                with self._lock:
                    data = dict(self._data[partition.partition_id])
                    if limit:
                        data = dict(list(data.items())[:limit])
                    return data

        return {}

    # -------------------------------------------------------------------------
    # PARTITION OPERATIONS
    # -------------------------------------------------------------------------

    def get_partition(self, key: str) -> Optional[Partition]:
        """Get partition for key."""
        return self._router.route(key)

    def get_partition_num(self, key: str) -> int:
        """Get partition number for key."""
        partition = self._router.route(key)
        return partition.partition_num if partition else -1

    def list_partitions(self) -> List[Partition]:
        """List all partitions."""
        return self._router.get_all_partitions()

    def get_partition_by_id(
        self,
        partition_id: str
    ) -> Optional[Partition]:
        """Get partition by ID."""
        for partition in self._router.get_all_partitions():
            if partition.partition_id == partition_id:
                return partition
        return None

    # -------------------------------------------------------------------------
    # PARTITION MANAGEMENT
    # -------------------------------------------------------------------------

    def split_partition(self, partition_num: int) -> Tuple[Partition, Partition]:
        """Split a partition into two."""
        partitions = self._router.get_all_partitions()

        source = None
        for p in partitions:
            if p.partition_num == partition_num:
                source = p
                break

        if not source:
            raise ValueError(f"Partition {partition_num} not found")

        # Create two new partitions
        new_num = self._config.num_partitions
        self._config.num_partitions += 1

        new_partition = Partition(
            partition_num=new_num,
            node_id=source.node_id
        )

        # Move half the data
        with self._lock:
            source_data = self._data[source.partition_id]
            keys = list(source_data.keys())
            mid = len(keys) // 2

            for key in keys[mid:]:
                self._data[new_partition.partition_id][key] = source_data.pop(key)

            source.item_count = len(source_data)
            new_partition.item_count = len(self._data[new_partition.partition_id])

        self._router.add_partition(new_partition)
        self._stats[new_partition.partition_id] = PartitionStats(
            partition_id=new_partition.partition_id
        )

        return (source, new_partition)

    def merge_partitions(
        self,
        partition_num1: int,
        partition_num2: int
    ) -> Partition:
        """Merge two partitions."""
        partitions = self._router.get_all_partitions()

        p1 = p2 = None
        for p in partitions:
            if p.partition_num == partition_num1:
                p1 = p
            elif p.partition_num == partition_num2:
                p2 = p

        if not p1 or not p2:
            raise ValueError("Partition not found")

        # Merge data into p1
        with self._lock:
            self._data[p1.partition_id].update(self._data[p2.partition_id])
            del self._data[p2.partition_id]

            p1.item_count = len(self._data[p1.partition_id])

        self._router.remove_partition(partition_num2)

        if p2.partition_id in self._stats:
            del self._stats[p2.partition_id]

        return p1

    # -------------------------------------------------------------------------
    # REBALANCING
    # -------------------------------------------------------------------------

    def plan_rebalance(self) -> RebalancePlan:
        """Plan partition rebalance."""
        plan = RebalancePlan(state=RebalanceState.PLANNING)

        partitions = self._router.get_all_partitions()

        # Calculate load per node
        node_load: Dict[str, int] = defaultdict(int)
        for p in partitions:
            if p.node_id:
                node_load[p.node_id] += p.item_count

        if not node_load:
            plan.state = RebalanceState.IDLE
            return plan

        # Find overloaded and underloaded nodes
        avg_load = sum(node_load.values()) / len(node_load)
        threshold = avg_load * 0.2  # 20% threshold

        overloaded = [n for n, l in node_load.items() if l > avg_load + threshold]
        underloaded = [n for n, l in node_load.items() if l < avg_load - threshold]

        # Plan moves
        for over in overloaded:
            for under in underloaded:
                # Find partition to move
                for p in partitions:
                    if p.node_id == over and node_load[over] > avg_load:
                        # Get some keys to move
                        with self._lock:
                            data = self._data[p.partition_id]
                            move_count = min(len(data) // 2, int(threshold))

                            for i, key in enumerate(list(data.keys())):
                                if i >= move_count:
                                    break
                                plan.moves.append((key, over, under))
                                node_load[over] -= 1
                                node_load[under] += 1

        self._rebalance_plan = plan
        return plan

    async def execute_rebalance(self) -> bool:
        """Execute rebalance plan."""
        if not self._rebalance_plan:
            return False

        plan = self._rebalance_plan
        plan.state = RebalanceState.MIGRATING
        plan.started_at = datetime.utcnow()

        total_moves = len(plan.moves)

        for i, (key, from_node, to_node) in enumerate(plan.moves):
            # Find source and target partitions
            partitions = self._router.get_all_partitions()

            source = target = None
            for p in partitions:
                if p.node_id == from_node:
                    source = p
                if p.node_id == to_node:
                    target = p

            if source and target:
                with self._lock:
                    value = self._data[source.partition_id].pop(key, None)
                    if value:
                        self._data[target.partition_id][key] = value

            plan.progress = (i + 1) / total_moves
            await asyncio.sleep(0)  # Yield

        plan.state = RebalanceState.COMPLETING
        plan.completed_at = datetime.utcnow()

        return True

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self, partition_id: str) -> Optional[PartitionStats]:
        """Get partition statistics."""
        with self._lock:
            return self._stats.get(partition_id)

    def get_all_stats(self) -> Dict[str, PartitionStats]:
        """Get all partition statistics."""
        with self._lock:
            return dict(self._stats)

    def get_distribution(self) -> Dict[int, int]:
        """Get data distribution across partitions."""
        with self._lock:
            return {
                p.partition_num: p.item_count
                for p in self._router.get_all_partitions()
            }

    def get_node_distribution(self) -> Dict[str, int]:
        """Get data distribution across nodes."""
        with self._lock:
            distribution: Dict[str, int] = defaultdict(int)
            for p in self._router.get_all_partitions():
                if p.node_id:
                    distribution[p.node_id] += p.item_count
            return dict(distribution)

    # -------------------------------------------------------------------------
    # SHARD MANAGEMENT
    # -------------------------------------------------------------------------

    def get_shard_info(self, node_id: str) -> ShardInfo:
        """Get shard info for node."""
        partitions = self._router.get_all_partitions()

        shard = ShardInfo(
            shard_id=node_id,
            node_id=node_id
        )

        for p in partitions:
            if p.node_id == node_id:
                shard.partitions.append(p.partition_id)
                shard.load += p.item_count

        return shard

    def list_shards(self) -> List[ShardInfo]:
        """List all shards."""
        partitions = self._router.get_all_partitions()

        nodes: Set[str] = set()
        for p in partitions:
            if p.node_id:
                nodes.add(p.node_id)

        return [self.get_shard_info(node) for node in nodes]

    # -------------------------------------------------------------------------
    # REPLICA MANAGEMENT
    # -------------------------------------------------------------------------

    def add_replica(
        self,
        partition_num: int,
        replica_node: str
    ) -> Optional[Partition]:
        """Add replica for partition."""
        partitions = self._router.get_all_partitions()

        for partition in partitions:
            if partition.partition_num == partition_num:
                # Create replica partition
                replica = Partition(
                    partition_num=self._config.num_partitions,
                    node_id=replica_node,
                    state=PartitionState.ACTIVE
                )
                self._config.num_partitions += 1

                partition.replicas.append(replica.partition_id)

                # Copy data
                with self._lock:
                    self._data[replica.partition_id] = dict(
                        self._data[partition.partition_id]
                    )
                    replica.item_count = partition.item_count

                self._router.add_partition(replica)
                self._stats[replica.partition_id] = PartitionStats(
                    partition_id=replica.partition_id
                )

                return replica

        return None


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Partition Manager."""
    print("=" * 70)
    print("BAEL - PARTITION MANAGER DEMO")
    print("Advanced Data Partitioning for AI Agents")
    print("=" * 70)
    print()

    manager = PartitionManager(PartitionConfig(
        strategy=PartitionStrategy.HASH,
        num_partitions=8
    ))

    # 1. Basic Operations
    print("1. BASIC OPERATIONS:")
    print("-" * 40)

    manager.put("user:1", {"name": "Alice", "age": 30})
    manager.put("user:2", {"name": "Bob", "age": 25})
    manager.put("user:3", {"name": "Charlie", "age": 35})

    user = manager.get("user:1")
    print(f"   Put and get user:1: {user}")
    print()

    # 2. Partition Routing
    print("2. PARTITION ROUTING:")
    print("-" * 40)

    for key in ["user:1", "user:2", "user:3", "order:100", "product:50"]:
        partition = manager.get_partition(key)
        if partition:
            print(f"   {key} -> partition {partition.partition_num} (node: {partition.node_id})")
    print()

    # 3. Add More Data
    print("3. ADD MORE DATA:")
    print("-" * 40)

    for i in range(100):
        manager.put(f"item:{i}", {"value": i * 10})

    print(f"   Added 100 items")
    print()

    # 4. Distribution
    print("4. DATA DISTRIBUTION:")
    print("-" * 40)

    distribution = manager.get_distribution()

    for partition_num, count in sorted(distribution.items()):
        print(f"   Partition {partition_num}: {count} items")
    print()

    # 5. Node Distribution
    print("5. NODE DISTRIBUTION:")
    print("-" * 40)

    node_dist = manager.get_node_distribution()

    for node, count in sorted(node_dist.items()):
        print(f"   {node}: {count} items")
    print()

    # 6. List Partitions
    print("6. LIST PARTITIONS:")
    print("-" * 40)

    partitions = manager.list_partitions()

    for p in partitions[:4]:
        print(f"   Partition {p.partition_num}: {p.state.value}, "
              f"node={p.node_id}, items={p.item_count}")
    print(f"   ... and {len(partitions) - 4} more")
    print()

    # 7. Partition Statistics
    print("7. PARTITION STATISTICS:")
    print("-" * 40)

    all_stats = manager.get_all_stats()

    for pid, stats in list(all_stats.items())[:3]:
        print(f"   {pid[:8]}...: reads={stats.reads}, writes={stats.writes}")
    print()

    # 8. Split Partition
    print("8. SPLIT PARTITION:")
    print("-" * 40)

    p1, p2 = manager.split_partition(0)

    print(f"   Split partition 0:")
    print(f"   Original: {p1.item_count} items")
    print(f"   New: {p2.item_count} items")
    print()

    # 9. Get from Partition
    print("9. GET FROM PARTITION:")
    print("-" * 40)

    partition_data = manager.get_from_partition(1, limit=3)

    print(f"   Data from partition 1:")
    for key, value in list(partition_data.items())[:3]:
        print(f"   {key}: {value}")
    print()

    # 10. Rebalance Planning
    print("10. REBALANCE PLANNING:")
    print("-" * 40)

    plan = manager.plan_rebalance()

    print(f"   Plan ID: {plan.plan_id[:8]}...")
    print(f"   State: {plan.state.value}")
    print(f"   Planned moves: {len(plan.moves)}")
    print()

    # 11. Execute Rebalance
    print("11. EXECUTE REBALANCE:")
    print("-" * 40)

    if plan.moves:
        success = await manager.execute_rebalance()
        print(f"   Rebalance success: {success}")
        print(f"   Progress: {plan.progress:.0%}")
    else:
        print("   No moves needed")
    print()

    # 12. Shard Info
    print("12. SHARD INFO:")
    print("-" * 40)

    shards = manager.list_shards()

    for shard in shards[:4]:
        print(f"   Shard {shard.node_id}: {len(shard.partitions)} partitions, "
              f"load={shard.load}")
    print()

    # 13. Add Replica
    print("13. ADD REPLICA:")
    print("-" * 40)

    replica = manager.add_replica(1, "replica_node")

    if replica:
        print(f"   Added replica for partition 1")
        print(f"   Replica partition: {replica.partition_num}")
        print(f"   Replica node: {replica.node_id}")
    print()

    # 14. Consistent Hash Ring
    print("14. CONSISTENT HASH RING:")
    print("-" * 40)

    ch_manager = PartitionManager(PartitionConfig(
        strategy=PartitionStrategy.CONSISTENT_HASH,
        num_partitions=4,
        virtual_nodes=50
    ))

    for i in range(10):
        ch_manager.put(f"key_{i}", f"value_{i}")

    for key in ["key_0", "key_5", "key_9"]:
        partition = ch_manager.get_partition(key)
        if partition:
            print(f"   {key} -> node {partition.node_id}")
    print()

    # 15. Range Partitioning
    print("15. RANGE PARTITIONING:")
    print("-" * 40)

    range_manager = PartitionManager(PartitionConfig(
        strategy=PartitionStrategy.RANGE,
        num_partitions=4,
        range_bounds=[100, 500, 1000]
    ))

    for key in [50, 200, 800, 1500]:
        range_manager.put(str(key), {"value": key})
        partition = range_manager.get_partition(str(key))
        if partition:
            print(f"   Key {key} -> partition {partition.partition_num}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Partition Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
