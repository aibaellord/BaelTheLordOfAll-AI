#!/usr/bin/env python3
"""
BAEL - Partitioning Engine
Data partitioning for agents.

Features:
- Hash partitioning
- Range partitioning
- List partitioning
- Composite partitioning
- Partition management
"""

import asyncio
import hashlib
import json
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar
)


T = TypeVar('T')
K = TypeVar('K')


# =============================================================================
# ENUMS
# =============================================================================

class PartitionType(Enum):
    """Partition types."""
    HASH = "hash"
    RANGE = "range"
    LIST = "list"
    COMPOSITE = "composite"


class PartitionState(Enum):
    """Partition states."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SPLITTING = "splitting"
    MERGING = "merging"
    MIGRATING = "migrating"


class RebalanceStrategy(Enum):
    """Rebalance strategies."""
    IMMEDIATE = "immediate"
    LAZY = "lazy"
    SCHEDULED = "scheduled"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class PartitionInfo:
    """Partition information."""
    partition_id: str = ""
    name: str = ""
    partition_type: PartitionType = PartitionType.HASH
    state: PartitionState = PartitionState.ACTIVE
    key_count: int = 0
    data_size: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not self.partition_id:
            self.partition_id = str(uuid.uuid4())[:8]


@dataclass
class RangeSpec:
    """Range specification for range partitioning."""
    start: Any = None
    end: Any = None
    inclusive_start: bool = True
    inclusive_end: bool = False


@dataclass
class PartitionConfig:
    """Partition configuration."""
    partition_type: PartitionType = PartitionType.HASH
    partition_count: int = 4
    rebalance_threshold: float = 0.2
    rebalance_strategy: RebalanceStrategy = RebalanceStrategy.LAZY


@dataclass
class PartitionStats:
    """Partition statistics."""
    total_keys: int = 0
    total_partitions: int = 0
    writes: int = 0
    reads: int = 0
    rebalances: int = 0


# =============================================================================
# PARTITION KEY EXTRACTORS
# =============================================================================

class KeyExtractor(ABC):
    """Abstract key extractor."""
    
    @abstractmethod
    def extract(self, data: Any) -> Any:
        """Extract partition key from data."""
        pass


class FieldKeyExtractor(KeyExtractor):
    """Extract key from field."""
    
    def __init__(self, field_name: str):
        self._field_name = field_name
    
    def extract(self, data: Any) -> Any:
        """Extract field value."""
        if isinstance(data, dict):
            return data.get(self._field_name)
        return getattr(data, self._field_name, None)


class IdentityKeyExtractor(KeyExtractor):
    """Use data as key."""
    
    def extract(self, data: Any) -> Any:
        """Return data itself."""
        return data


class CompositeKeyExtractor(KeyExtractor):
    """Composite key extractor."""
    
    def __init__(self, field_names: List[str]):
        self._field_names = field_names
    
    def extract(self, data: Any) -> Tuple:
        """Extract composite key."""
        values = []
        
        for field in self._field_names:
            if isinstance(data, dict):
                values.append(data.get(field))
            else:
                values.append(getattr(data, field, None))
        
        return tuple(values)


# =============================================================================
# PARTITION STRATEGIES
# =============================================================================

class PartitionStrategy(ABC):
    """Abstract partition strategy."""
    
    @abstractmethod
    def get_partition(self, key: Any, partition_count: int) -> int:
        """Get partition index for key."""
        pass


class HashPartitionStrategy(PartitionStrategy):
    """Hash-based partitioning."""
    
    def get_partition(self, key: Any, partition_count: int) -> int:
        """Hash key to partition."""
        key_str = json.dumps(key, default=str) if not isinstance(key, str) else key
        
        hash_value = int(hashlib.md5(key_str.encode()).hexdigest(), 16)
        
        return hash_value % partition_count


class RangePartitionStrategy(PartitionStrategy):
    """Range-based partitioning."""
    
    def __init__(self, ranges: List[RangeSpec]):
        self._ranges = ranges
    
    def get_partition(self, key: Any, partition_count: int) -> int:
        """Get partition by range."""
        for i, range_spec in enumerate(self._ranges):
            if self._in_range(key, range_spec):
                return i
        
        return partition_count - 1
    
    def _in_range(self, key: Any, range_spec: RangeSpec) -> bool:
        """Check if key in range."""
        if range_spec.start is not None:
            if range_spec.inclusive_start:
                if key < range_spec.start:
                    return False
            else:
                if key <= range_spec.start:
                    return False
        
        if range_spec.end is not None:
            if range_spec.inclusive_end:
                if key > range_spec.end:
                    return False
            else:
                if key >= range_spec.end:
                    return False
        
        return True


class ListPartitionStrategy(PartitionStrategy):
    """List-based partitioning."""
    
    def __init__(self, value_lists: List[List[Any]]):
        self._value_lists = value_lists
        
        self._value_map: Dict[Any, int] = {}
        
        for i, values in enumerate(value_lists):
            for v in values:
                self._value_map[v] = i
    
    def get_partition(self, key: Any, partition_count: int) -> int:
        """Get partition by value list."""
        return self._value_map.get(key, partition_count - 1)


class ConsistentHashPartitionStrategy(PartitionStrategy):
    """Consistent hash partitioning."""
    
    def __init__(self, virtual_nodes: int = 100):
        self._virtual_nodes = virtual_nodes
        self._ring: List[Tuple[int, int]] = []
    
    def setup(self, partition_count: int) -> None:
        """Set up hash ring."""
        self._ring = []
        
        for p in range(partition_count):
            for v in range(self._virtual_nodes):
                key = f"{p}:{v}"
                hash_value = int(hashlib.md5(key.encode()).hexdigest(), 16)
                self._ring.append((hash_value, p))
        
        self._ring.sort(key=lambda x: x[0])
    
    def get_partition(self, key: Any, partition_count: int) -> int:
        """Get partition using consistent hash."""
        if not self._ring:
            self.setup(partition_count)
        
        key_str = json.dumps(key, default=str) if not isinstance(key, str) else key
        
        key_hash = int(hashlib.md5(key_str.encode()).hexdigest(), 16)
        
        for ring_hash, partition in self._ring:
            if key_hash <= ring_hash:
                return partition
        
        return self._ring[0][1]


# =============================================================================
# PARTITION
# =============================================================================

class Partition(Generic[K, T]):
    """A data partition."""
    
    def __init__(self, info: PartitionInfo):
        self._info = info
        
        self._data: Dict[K, T] = {}
    
    def put(self, key: K, value: T) -> None:
        """Put value into partition."""
        self._data[key] = value
        self._info.key_count = len(self._data)
    
    def get(self, key: K) -> Optional[T]:
        """Get value from partition."""
        return self._data.get(key)
    
    def delete(self, key: K) -> bool:
        """Delete from partition."""
        if key in self._data:
            del self._data[key]
            self._info.key_count = len(self._data)
            return True
        return False
    
    def contains(self, key: K) -> bool:
        """Check if key exists."""
        return key in self._data
    
    def keys(self) -> List[K]:
        """Get all keys."""
        return list(self._data.keys())
    
    def values(self) -> List[T]:
        """Get all values."""
        return list(self._data.values())
    
    def items(self) -> List[Tuple[K, T]]:
        """Get all items."""
        return list(self._data.items())
    
    def clear(self) -> None:
        """Clear partition."""
        self._data.clear()
        self._info.key_count = 0
    
    @property
    def info(self) -> PartitionInfo:
        return self._info
    
    @property
    def partition_id(self) -> str:
        return self._info.partition_id
    
    @property
    def name(self) -> str:
        return self._info.name
    
    @property
    def state(self) -> PartitionState:
        return self._info.state
    
    @state.setter
    def state(self, value: PartitionState) -> None:
        self._info.state = value
    
    @property
    def key_count(self) -> int:
        return len(self._data)


# =============================================================================
# PARTITIONED TABLE
# =============================================================================

class PartitionedTable(Generic[K, T]):
    """A partitioned data table."""
    
    def __init__(
        self,
        name: str,
        config: Optional[PartitionConfig] = None,
        key_extractor: Optional[KeyExtractor] = None
    ):
        self._name = name
        self._config = config or PartitionConfig()
        self._key_extractor = key_extractor or IdentityKeyExtractor()
        
        self._partitions: List[Partition[K, T]] = []
        self._strategy = self._create_strategy()
        
        self._stats = PartitionStats()
        
        self._initialize_partitions()
    
    def _create_strategy(self) -> PartitionStrategy:
        """Create partition strategy."""
        if self._config.partition_type == PartitionType.HASH:
            return HashPartitionStrategy()
        elif self._config.partition_type == PartitionType.RANGE:
            return RangePartitionStrategy([])
        elif self._config.partition_type == PartitionType.LIST:
            return ListPartitionStrategy([])
        else:
            return HashPartitionStrategy()
    
    def _initialize_partitions(self) -> None:
        """Initialize partitions."""
        for i in range(self._config.partition_count):
            info = PartitionInfo(
                name=f"{self._name}_p{i}",
                partition_type=self._config.partition_type
            )
            
            partition = Partition[K, T](info)
            self._partitions.append(partition)
        
        self._stats.total_partitions = len(self._partitions)
    
    def _get_partition_index(self, key: K) -> int:
        """Get partition index for key."""
        return self._strategy.get_partition(key, len(self._partitions))
    
    def put(self, key: K, value: T) -> int:
        """Put value into table."""
        partition_idx = self._get_partition_index(key)
        
        self._partitions[partition_idx].put(key, value)
        
        self._stats.writes += 1
        self._stats.total_keys += 1
        
        return partition_idx
    
    def get(self, key: K) -> Optional[T]:
        """Get value from table."""
        partition_idx = self._get_partition_index(key)
        
        value = self._partitions[partition_idx].get(key)
        
        self._stats.reads += 1
        
        return value
    
    def delete(self, key: K) -> bool:
        """Delete from table."""
        partition_idx = self._get_partition_index(key)
        
        deleted = self._partitions[partition_idx].delete(key)
        
        if deleted:
            self._stats.total_keys -= 1
        
        return deleted
    
    def contains(self, key: K) -> bool:
        """Check if key exists."""
        partition_idx = self._get_partition_index(key)
        
        return self._partitions[partition_idx].contains(key)
    
    def get_partition(self, index: int) -> Optional[Partition[K, T]]:
        """Get partition by index."""
        if 0 <= index < len(self._partitions):
            return self._partitions[index]
        return None
    
    def get_all_partitions(self) -> List[Partition[K, T]]:
        """Get all partitions."""
        return list(self._partitions)
    
    def get_partition_for_key(self, key: K) -> Optional[Partition[K, T]]:
        """Get partition for key."""
        index = self._get_partition_index(key)
        return self._partitions[index]
    
    def scan_partition(self, index: int) -> List[Tuple[K, T]]:
        """Scan a partition."""
        partition = self.get_partition(index)
        
        if partition:
            return partition.items()
        
        return []
    
    def scan_all(self) -> List[Tuple[K, T]]:
        """Scan all partitions."""
        items = []
        
        for partition in self._partitions:
            items.extend(partition.items())
        
        return items
    
    def get_partition_distribution(self) -> Dict[int, int]:
        """Get key distribution across partitions."""
        return {
            i: p.key_count
            for i, p in enumerate(self._partitions)
        }
    
    def is_balanced(self) -> bool:
        """Check if partitions are balanced."""
        distribution = self.get_partition_distribution()
        
        if not distribution:
            return True
        
        counts = list(distribution.values())
        
        if not counts:
            return True
        
        avg = sum(counts) / len(counts)
        
        if avg == 0:
            return True
        
        for count in counts:
            if abs(count - avg) / avg > self._config.rebalance_threshold:
                return False
        
        return True
    
    async def rebalance(self) -> Dict[str, int]:
        """Rebalance partitions."""
        all_items = self.scan_all()
        
        for partition in self._partitions:
            partition.clear()
        
        for key, value in all_items:
            self.put(key, value)
        
        self._stats.rebalances += 1
        
        return {
            "items_moved": len(all_items),
            "partitions": len(self._partitions)
        }
    
    async def add_partition(self) -> Partition[K, T]:
        """Add a new partition."""
        info = PartitionInfo(
            name=f"{self._name}_p{len(self._partitions)}",
            partition_type=self._config.partition_type
        )
        
        partition = Partition[K, T](info)
        self._partitions.append(partition)
        
        self._stats.total_partitions = len(self._partitions)
        
        if self._config.rebalance_strategy == RebalanceStrategy.IMMEDIATE:
            await self.rebalance()
        
        return partition
    
    async def remove_partition(self, index: int) -> bool:
        """Remove a partition."""
        if index < 0 or index >= len(self._partitions):
            return False
        
        if len(self._partitions) <= 1:
            return False
        
        partition = self._partitions[index]
        items = partition.items()
        
        del self._partitions[index]
        
        for key, value in items:
            self.put(key, value)
        
        self._stats.total_partitions = len(self._partitions)
        
        return True
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def partition_count(self) -> int:
        return len(self._partitions)
    
    @property
    def stats(self) -> PartitionStats:
        return self._stats


# =============================================================================
# PARTITIONING ENGINE
# =============================================================================

class PartitioningEngine:
    """
    Partitioning Engine for BAEL.
    
    Data partitioning for agents.
    """
    
    def __init__(self, default_config: Optional[PartitionConfig] = None):
        self._default_config = default_config or PartitionConfig()
        
        self._tables: Dict[str, PartitionedTable] = {}
    
    # ----- Table Management -----
    
    def create_table(
        self,
        name: str,
        config: Optional[PartitionConfig] = None,
        key_extractor: Optional[KeyExtractor] = None
    ) -> PartitionedTable:
        """Create a partitioned table."""
        config = config or self._default_config
        
        table = PartitionedTable(name, config, key_extractor)
        self._tables[name] = table
        
        return table
    
    def create_hash_table(
        self,
        name: str,
        partition_count: int = 4
    ) -> PartitionedTable:
        """Create hash-partitioned table."""
        config = PartitionConfig(
            partition_type=PartitionType.HASH,
            partition_count=partition_count
        )
        
        return self.create_table(name, config)
    
    def get_table(self, name: str) -> Optional[PartitionedTable]:
        """Get a table."""
        return self._tables.get(name)
    
    def remove_table(self, name: str) -> bool:
        """Remove a table."""
        if name in self._tables:
            del self._tables[name]
            return True
        return False
    
    def list_tables(self) -> List[str]:
        """List table names."""
        return list(self._tables.keys())
    
    # ----- Data Operations -----
    
    def put(self, table_name: str, key: Any, value: Any) -> int:
        """Put value into table."""
        table = self._tables.get(table_name)
        
        if table:
            return table.put(key, value)
        
        return -1
    
    def get(self, table_name: str, key: Any) -> Optional[Any]:
        """Get value from table."""
        table = self._tables.get(table_name)
        
        if table:
            return table.get(key)
        
        return None
    
    def delete(self, table_name: str, key: Any) -> bool:
        """Delete from table."""
        table = self._tables.get(table_name)
        
        if table:
            return table.delete(key)
        
        return False
    
    def contains(self, table_name: str, key: Any) -> bool:
        """Check if key exists."""
        table = self._tables.get(table_name)
        
        if table:
            return table.contains(key)
        
        return False
    
    # ----- Partition Operations -----
    
    def get_partition_count(self, table_name: str) -> int:
        """Get partition count."""
        table = self._tables.get(table_name)
        return table.partition_count if table else 0
    
    def get_partition_distribution(
        self,
        table_name: str
    ) -> Dict[int, int]:
        """Get partition distribution."""
        table = self._tables.get(table_name)
        
        if table:
            return table.get_partition_distribution()
        
        return {}
    
    def is_balanced(self, table_name: str) -> bool:
        """Check if table is balanced."""
        table = self._tables.get(table_name)
        
        if table:
            return table.is_balanced()
        
        return True
    
    async def rebalance(self, table_name: str) -> Dict[str, int]:
        """Rebalance table."""
        table = self._tables.get(table_name)
        
        if table:
            return await table.rebalance()
        
        return {}
    
    async def add_partition(
        self,
        table_name: str
    ) -> Optional[Partition]:
        """Add partition to table."""
        table = self._tables.get(table_name)
        
        if table:
            return await table.add_partition()
        
        return None
    
    async def remove_partition(
        self,
        table_name: str,
        index: int
    ) -> bool:
        """Remove partition from table."""
        table = self._tables.get(table_name)
        
        if table:
            return await table.remove_partition(index)
        
        return False
    
    # ----- Scanning -----
    
    def scan_partition(
        self,
        table_name: str,
        partition_index: int
    ) -> List[Tuple[Any, Any]]:
        """Scan a partition."""
        table = self._tables.get(table_name)
        
        if table:
            return table.scan_partition(partition_index)
        
        return []
    
    def scan_table(self, table_name: str) -> List[Tuple[Any, Any]]:
        """Scan entire table."""
        table = self._tables.get(table_name)
        
        if table:
            return table.scan_all()
        
        return []
    
    # ----- Status -----
    
    def get_stats(self, table_name: str) -> Optional[PartitionStats]:
        """Get table stats."""
        table = self._tables.get(table_name)
        
        if table:
            return table.stats
        
        return None
    
    # ----- Engine Stats -----
    
    def stats(self) -> Dict[str, Any]:
        """Get engine stats."""
        total_keys = 0
        total_partitions = 0
        
        for table in self._tables.values():
            total_keys += table.stats.total_keys
            total_partitions += table.partition_count
        
        return {
            "tables": len(self._tables),
            "total_keys": total_keys,
            "total_partitions": total_partitions
        }
    
    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        table_info = {}
        
        for name, table in self._tables.items():
            table_info[name] = {
                "partition_count": table.partition_count,
                "total_keys": table.stats.total_keys,
                "balanced": table.is_balanced()
            }
        
        return {"tables": table_info}


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Partitioning Engine."""
    print("=" * 70)
    print("BAEL - PARTITIONING ENGINE DEMO")
    print("Data Partitioning for Agents")
    print("=" * 70)
    print()
    
    engine = PartitioningEngine()
    
    # 1. Create Hash-Partitioned Table
    print("1. CREATE HASH-PARTITIONED TABLE:")
    print("-" * 40)
    
    users_table = engine.create_hash_table("users", partition_count=4)
    
    print(f"   Created table: {users_table.name}")
    print(f"   Partitions: {users_table.partition_count}")
    print()
    
    # 2. Insert Data
    print("2. INSERT DATA:")
    print("-" * 40)
    
    for i in range(20):
        user_id = f"user_{i:03d}"
        user_data = {"name": f"User {i}", "email": f"user{i}@example.com"}
        
        partition = engine.put("users", user_id, user_data)
        
        if i < 5:
            print(f"   {user_id} -> partition {partition}")
    
    print(f"   ... inserted 20 users")
    print()
    
    # 3. Get Data
    print("3. GET DATA:")
    print("-" * 40)
    
    user = engine.get("users", "user_005")
    print(f"   user_005: {user}")
    
    user = engine.get("users", "user_010")
    print(f"   user_010: {user}")
    print()
    
    # 4. Check Partition Distribution
    print("4. PARTITION DISTRIBUTION:")
    print("-" * 40)
    
    distribution = engine.get_partition_distribution("users")
    for p_idx, count in distribution.items():
        print(f"   Partition {p_idx}: {count} keys")
    print()
    
    # 5. Check Balance
    print("5. CHECK BALANCE:")
    print("-" * 40)
    
    balanced = engine.is_balanced("users")
    print(f"   Table balanced: {balanced}")
    print()
    
    # 6. Scan Partition
    print("6. SCAN PARTITION:")
    print("-" * 40)
    
    items = engine.scan_partition("users", 0)
    print(f"   Partition 0 has {len(items)} items:")
    for key, value in items[:3]:
        print(f"      {key}: {value['name']}")
    print()
    
    # 7. Add Partition
    print("7. ADD PARTITION:")
    print("-" * 40)
    
    new_partition = await engine.add_partition("users")
    print(f"   Added partition: {new_partition.name}")
    print(f"   Total partitions: {engine.get_partition_count('users')}")
    print()
    
    # 8. Rebalance
    print("8. REBALANCE:")
    print("-" * 40)
    
    result = await engine.rebalance("users")
    print(f"   Rebalanced: {result}")
    
    distribution = engine.get_partition_distribution("users")
    for p_idx, count in distribution.items():
        print(f"   Partition {p_idx}: {count} keys")
    print()
    
    # 9. Create Range-Partitioned Table
    print("9. CREATE CUSTOM TABLE:")
    print("-" * 40)
    
    config = PartitionConfig(
        partition_type=PartitionType.HASH,
        partition_count=3
    )
    
    orders_table = engine.create_table(
        "orders",
        config,
        FieldKeyExtractor("customer_id")
    )
    
    print(f"   Created table: {orders_table.name}")
    print(f"   Partitions: {orders_table.partition_count}")
    print()
    
    # 10. Insert Orders
    print("10. INSERT ORDERS:")
    print("-" * 40)
    
    for i in range(10):
        order = {
            "order_id": f"ord_{i:03d}",
            "customer_id": f"cust_{i % 3:02d}",
            "amount": 100 + i * 10
        }
        
        key = order["customer_id"]
        engine.put("orders", key, order)
    
    print(f"   Inserted 10 orders")
    
    order = engine.get("orders", "cust_01")
    print(f"   cust_01 order: {order}")
    print()
    
    # 11. Scan Table
    print("11. SCAN TABLE:")
    print("-" * 40)
    
    all_orders = engine.scan_table("orders")
    print(f"   Total orders: {len(all_orders)}")
    for key, value in all_orders[:3]:
        print(f"      {key}: order_id={value['order_id']}")
    print()
    
    # 12. Table Statistics
    print("12. TABLE STATISTICS:")
    print("-" * 40)
    
    stats = engine.get_stats("users")
    print(f"   Users table:")
    print(f"      Total keys: {stats.total_keys}")
    print(f"      Writes: {stats.writes}")
    print(f"      Reads: {stats.reads}")
    print(f"      Rebalances: {stats.rebalances}")
    print()
    
    # 13. List Tables
    print("13. LIST TABLES:")
    print("-" * 40)
    
    tables = engine.list_tables()
    for t in tables:
        print(f"   - {t}")
    print()
    
    # 14. Engine Statistics
    print("14. ENGINE STATISTICS:")
    print("-" * 40)
    
    stats = engine.stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()
    
    # 15. Engine Summary
    print("15. ENGINE SUMMARY:")
    print("-" * 40)
    
    summary = engine.summary()
    for name, info in summary["tables"].items():
        print(f"   {name}:")
        print(f"      Partitions: {info['partition_count']}")
        print(f"      Keys: {info['total_keys']}")
        print(f"      Balanced: {info['balanced']}")
    print()
    
    print("=" * 70)
    print("DEMO COMPLETE - Partitioning Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
