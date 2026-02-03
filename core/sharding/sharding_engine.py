#!/usr/bin/env python3
"""
BAEL - Sharding Engine
Data sharding for agents.

Features:
- Horizontal sharding
- Vertical sharding
- Shard management
- Query routing
- Resharding support
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

class ShardingType(Enum):
    """Sharding types."""
    HASH = "hash"
    RANGE = "range"
    DIRECTORY = "directory"
    GEO = "geo"


class ShardState(Enum):
    """Shard states."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    READONLY = "readonly"
    MIGRATING = "migrating"
    DRAINING = "draining"


class ShardRole(Enum):
    """Shard roles."""
    PRIMARY = "primary"
    REPLICA = "replica"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class ShardConfig:
    """Shard configuration."""
    shard_id: str = ""
    name: str = ""
    endpoint: str = ""
    role: ShardRole = ShardRole.PRIMARY
    weight: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.shard_id:
            self.shard_id = str(uuid.uuid4())[:8]


@dataclass
class ShardingConfig:
    """Sharding configuration."""
    sharding_type: ShardingType = ShardingType.HASH
    shard_count: int = 4
    replication_factor: int = 1
    virtual_shards_per_shard: int = 100


@dataclass
class ShardStats:
    """Shard statistics."""
    key_count: int = 0
    data_size: int = 0
    reads: int = 0
    writes: int = 0


@dataclass
class ShardingStats:
    """Sharding statistics."""
    total_shards: int = 0
    active_shards: int = 0
    total_keys: int = 0
    total_reads: int = 0
    total_writes: int = 0


@dataclass
class ShardRange:
    """Shard range for range sharding."""
    shard_id: str = ""
    start_key: Any = None
    end_key: Any = None


@dataclass
class QueryResult:
    """Query result from shard."""
    shard_id: str = ""
    data: List[Any] = field(default_factory=list)
    count: int = 0
    latency_ms: float = 0.0


# =============================================================================
# SHARD KEY STRATEGIES
# =============================================================================

class ShardKeyStrategy(ABC):
    """Abstract shard key strategy."""
    
    @abstractmethod
    def get_shard(self, key: Any, shard_count: int) -> int:
        """Get shard index for key."""
        pass


class HashShardKeyStrategy(ShardKeyStrategy):
    """Hash-based shard key strategy."""
    
    def get_shard(self, key: Any, shard_count: int) -> int:
        """Hash key to shard."""
        key_str = json.dumps(key, default=str) if not isinstance(key, str) else key
        
        hash_value = int(hashlib.md5(key_str.encode()).hexdigest(), 16)
        
        return hash_value % shard_count


class RangeShardKeyStrategy(ShardKeyStrategy):
    """Range-based shard key strategy."""
    
    def __init__(self, ranges: List[ShardRange] = None):
        self._ranges = ranges or []
    
    def add_range(self, range_spec: ShardRange) -> None:
        """Add range."""
        self._ranges.append(range_spec)
    
    def get_shard(self, key: Any, shard_count: int) -> int:
        """Get shard by range."""
        for i, range_spec in enumerate(self._ranges):
            if self._in_range(key, range_spec):
                return i
        
        return shard_count - 1
    
    def _in_range(self, key: Any, range_spec: ShardRange) -> bool:
        """Check if key in range."""
        if range_spec.start_key is not None and key < range_spec.start_key:
            return False
        if range_spec.end_key is not None and key >= range_spec.end_key:
            return False
        return True


class DirectoryShardKeyStrategy(ShardKeyStrategy):
    """Directory-based shard key strategy."""
    
    def __init__(self):
        self._directory: Dict[Any, int] = {}
    
    def map_key(self, key: Any, shard_index: int) -> None:
        """Map key to shard."""
        self._directory[key] = shard_index
    
    def get_shard(self, key: Any, shard_count: int) -> int:
        """Get shard from directory."""
        if key in self._directory:
            return self._directory[key]
        
        hash_strategy = HashShardKeyStrategy()
        return hash_strategy.get_shard(key, shard_count)


class ConsistentHashShardKeyStrategy(ShardKeyStrategy):
    """Consistent hash shard key strategy."""
    
    def __init__(self, virtual_nodes: int = 100):
        self._virtual_nodes = virtual_nodes
        self._ring: List[Tuple[int, int]] = []
    
    def setup(self, shard_count: int) -> None:
        """Set up hash ring."""
        self._ring = []
        
        for s in range(shard_count):
            for v in range(self._virtual_nodes):
                key = f"{s}:{v}"
                hash_value = int(hashlib.md5(key.encode()).hexdigest(), 16)
                self._ring.append((hash_value, s))
        
        self._ring.sort(key=lambda x: x[0])
    
    def get_shard(self, key: Any, shard_count: int) -> int:
        """Get shard using consistent hash."""
        if not self._ring:
            self.setup(shard_count)
        
        key_str = json.dumps(key, default=str) if not isinstance(key, str) else key
        
        key_hash = int(hashlib.md5(key_str.encode()).hexdigest(), 16)
        
        for ring_hash, shard in self._ring:
            if key_hash <= ring_hash:
                return shard
        
        return self._ring[0][1]


# =============================================================================
# SHARD
# =============================================================================

class Shard(Generic[K, T]):
    """A data shard."""
    
    def __init__(self, config: ShardConfig):
        self._config = config
        
        self._data: Dict[K, T] = {}
        self._state = ShardState.ACTIVE
        self._stats = ShardStats()
    
    def put(self, key: K, value: T) -> bool:
        """Put value into shard."""
        if self._state == ShardState.READONLY:
            return False
        
        self._data[key] = value
        self._stats.key_count = len(self._data)
        self._stats.writes += 1
        
        return True
    
    def get(self, key: K) -> Optional[T]:
        """Get value from shard."""
        self._stats.reads += 1
        return self._data.get(key)
    
    def delete(self, key: K) -> bool:
        """Delete from shard."""
        if self._state == ShardState.READONLY:
            return False
        
        if key in self._data:
            del self._data[key]
            self._stats.key_count = len(self._data)
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
        """Clear shard."""
        self._data.clear()
        self._stats.key_count = 0
    
    def query(
        self,
        predicate: Callable[[K, T], bool]
    ) -> List[Tuple[K, T]]:
        """Query shard with predicate."""
        results = []
        
        for key, value in self._data.items():
            if predicate(key, value):
                results.append((key, value))
        
        return results
    
    @property
    def shard_id(self) -> str:
        return self._config.shard_id
    
    @property
    def name(self) -> str:
        return self._config.name
    
    @property
    def state(self) -> ShardState:
        return self._state
    
    @state.setter
    def state(self, value: ShardState) -> None:
        self._state = value
    
    @property
    def role(self) -> ShardRole:
        return self._config.role
    
    @property
    def stats(self) -> ShardStats:
        return self._stats


# =============================================================================
# SHARD CLUSTER
# =============================================================================

class ShardCluster(Generic[K, T]):
    """A cluster of shards."""
    
    def __init__(
        self,
        name: str,
        config: Optional[ShardingConfig] = None
    ):
        self._name = name
        self._config = config or ShardingConfig()
        
        self._shards: List[Shard[K, T]] = []
        self._strategy = self._create_strategy()
        
        self._stats = ShardingStats()
        
        self._initialize_shards()
    
    def _create_strategy(self) -> ShardKeyStrategy:
        """Create shard key strategy."""
        if self._config.sharding_type == ShardingType.HASH:
            return ConsistentHashShardKeyStrategy(
                self._config.virtual_shards_per_shard
            )
        elif self._config.sharding_type == ShardingType.RANGE:
            return RangeShardKeyStrategy()
        elif self._config.sharding_type == ShardingType.DIRECTORY:
            return DirectoryShardKeyStrategy()
        else:
            return HashShardKeyStrategy()
    
    def _initialize_shards(self) -> None:
        """Initialize shards."""
        for i in range(self._config.shard_count):
            shard_config = ShardConfig(
                name=f"{self._name}_shard_{i}",
                role=ShardRole.PRIMARY
            )
            
            shard = Shard[K, T](shard_config)
            self._shards.append(shard)
        
        if isinstance(self._strategy, ConsistentHashShardKeyStrategy):
            self._strategy.setup(len(self._shards))
        
        self._stats.total_shards = len(self._shards)
        self._stats.active_shards = len(self._shards)
    
    def _get_shard_index(self, key: K) -> int:
        """Get shard index for key."""
        return self._strategy.get_shard(key, len(self._shards))
    
    def put(self, key: K, value: T) -> Tuple[bool, str]:
        """Put value into cluster."""
        shard_idx = self._get_shard_index(key)
        shard = self._shards[shard_idx]
        
        success = shard.put(key, value)
        
        if success:
            self._stats.total_writes += 1
            self._stats.total_keys += 1
        
        return success, shard.shard_id
    
    def get(self, key: K) -> Optional[T]:
        """Get value from cluster."""
        shard_idx = self._get_shard_index(key)
        shard = self._shards[shard_idx]
        
        self._stats.total_reads += 1
        
        return shard.get(key)
    
    def delete(self, key: K) -> bool:
        """Delete from cluster."""
        shard_idx = self._get_shard_index(key)
        shard = self._shards[shard_idx]
        
        deleted = shard.delete(key)
        
        if deleted:
            self._stats.total_keys -= 1
        
        return deleted
    
    def contains(self, key: K) -> bool:
        """Check if key exists."""
        shard_idx = self._get_shard_index(key)
        shard = self._shards[shard_idx]
        
        return shard.contains(key)
    
    def get_shard_for_key(self, key: K) -> Shard[K, T]:
        """Get shard for key."""
        shard_idx = self._get_shard_index(key)
        return self._shards[shard_idx]
    
    def get_shard(self, index: int) -> Optional[Shard[K, T]]:
        """Get shard by index."""
        if 0 <= index < len(self._shards):
            return self._shards[index]
        return None
    
    def get_shard_by_id(self, shard_id: str) -> Optional[Shard[K, T]]:
        """Get shard by ID."""
        for shard in self._shards:
            if shard.shard_id == shard_id:
                return shard
        return None
    
    def get_all_shards(self) -> List[Shard[K, T]]:
        """Get all shards."""
        return list(self._shards)
    
    async def scatter_query(
        self,
        predicate: Callable[[K, T], bool]
    ) -> List[QueryResult]:
        """Query all shards."""
        results = []
        
        for shard in self._shards:
            start = time.time()
            
            items = shard.query(predicate)
            
            latency = (time.time() - start) * 1000
            
            results.append(QueryResult(
                shard_id=shard.shard_id,
                data=items,
                count=len(items),
                latency_ms=latency
            ))
        
        return results
    
    async def gather_results(
        self,
        query_results: List[QueryResult]
    ) -> List[Tuple[K, T]]:
        """Gather results from scatter query."""
        all_items = []
        
        for result in query_results:
            all_items.extend(result.data)
        
        return all_items
    
    async def scatter_gather(
        self,
        predicate: Callable[[K, T], bool]
    ) -> List[Tuple[K, T]]:
        """Scatter-gather query."""
        scatter_results = await self.scatter_query(predicate)
        return await self.gather_results(scatter_results)
    
    async def add_shard(self) -> Shard[K, T]:
        """Add a new shard."""
        shard_config = ShardConfig(
            name=f"{self._name}_shard_{len(self._shards)}",
            role=ShardRole.PRIMARY
        )
        
        shard = Shard[K, T](shard_config)
        self._shards.append(shard)
        
        if isinstance(self._strategy, ConsistentHashShardKeyStrategy):
            self._strategy.setup(len(self._shards))
        
        self._stats.total_shards = len(self._shards)
        self._stats.active_shards = len(self._shards)
        
        return shard
    
    async def reshard(self) -> Dict[str, int]:
        """Reshard all data."""
        all_items = []
        
        for shard in self._shards:
            all_items.extend(shard.items())
            shard.clear()
        
        if isinstance(self._strategy, ConsistentHashShardKeyStrategy):
            self._strategy.setup(len(self._shards))
        
        for key, value in all_items:
            self.put(key, value)
        
        return {
            "items_resharded": len(all_items),
            "shard_count": len(self._shards)
        }
    
    def get_shard_distribution(self) -> Dict[str, int]:
        """Get key distribution across shards."""
        return {
            shard.shard_id: shard.stats.key_count
            for shard in self._shards
        }
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def shard_count(self) -> int:
        return len(self._shards)
    
    @property
    def stats(self) -> ShardingStats:
        return self._stats


# =============================================================================
# SHARDING ENGINE
# =============================================================================

class ShardingEngine:
    """
    Sharding Engine for BAEL.
    
    Data sharding for agents.
    """
    
    def __init__(self, default_config: Optional[ShardingConfig] = None):
        self._default_config = default_config or ShardingConfig()
        
        self._clusters: Dict[str, ShardCluster] = {}
    
    # ----- Cluster Management -----
    
    def create_cluster(
        self,
        name: str,
        config: Optional[ShardingConfig] = None
    ) -> ShardCluster:
        """Create a shard cluster."""
        config = config or self._default_config
        
        cluster = ShardCluster(name, config)
        self._clusters[name] = cluster
        
        return cluster
    
    def create_hash_cluster(
        self,
        name: str,
        shard_count: int = 4
    ) -> ShardCluster:
        """Create hash-sharded cluster."""
        config = ShardingConfig(
            sharding_type=ShardingType.HASH,
            shard_count=shard_count
        )
        
        return self.create_cluster(name, config)
    
    def get_cluster(self, name: str) -> Optional[ShardCluster]:
        """Get a cluster."""
        return self._clusters.get(name)
    
    def remove_cluster(self, name: str) -> bool:
        """Remove a cluster."""
        if name in self._clusters:
            del self._clusters[name]
            return True
        return False
    
    def list_clusters(self) -> List[str]:
        """List cluster names."""
        return list(self._clusters.keys())
    
    # ----- Data Operations -----
    
    def put(
        self,
        cluster_name: str,
        key: Any,
        value: Any
    ) -> Tuple[bool, str]:
        """Put value into cluster."""
        cluster = self._clusters.get(cluster_name)
        
        if cluster:
            return cluster.put(key, value)
        
        return False, ""
    
    def get(
        self,
        cluster_name: str,
        key: Any
    ) -> Optional[Any]:
        """Get value from cluster."""
        cluster = self._clusters.get(cluster_name)
        
        if cluster:
            return cluster.get(key)
        
        return None
    
    def delete(
        self,
        cluster_name: str,
        key: Any
    ) -> bool:
        """Delete from cluster."""
        cluster = self._clusters.get(cluster_name)
        
        if cluster:
            return cluster.delete(key)
        
        return False
    
    def contains(
        self,
        cluster_name: str,
        key: Any
    ) -> bool:
        """Check if key exists."""
        cluster = self._clusters.get(cluster_name)
        
        if cluster:
            return cluster.contains(key)
        
        return False
    
    # ----- Query Operations -----
    
    async def query(
        self,
        cluster_name: str,
        predicate: Callable[[Any, Any], bool]
    ) -> List[Tuple[Any, Any]]:
        """Query cluster."""
        cluster = self._clusters.get(cluster_name)
        
        if cluster:
            return await cluster.scatter_gather(predicate)
        
        return []
    
    # ----- Shard Operations -----
    
    def get_shard_count(self, cluster_name: str) -> int:
        """Get shard count."""
        cluster = self._clusters.get(cluster_name)
        return cluster.shard_count if cluster else 0
    
    def get_shard_distribution(
        self,
        cluster_name: str
    ) -> Dict[str, int]:
        """Get shard distribution."""
        cluster = self._clusters.get(cluster_name)
        
        if cluster:
            return cluster.get_shard_distribution()
        
        return {}
    
    async def add_shard(
        self,
        cluster_name: str
    ) -> Optional[Shard]:
        """Add shard to cluster."""
        cluster = self._clusters.get(cluster_name)
        
        if cluster:
            return await cluster.add_shard()
        
        return None
    
    async def reshard(
        self,
        cluster_name: str
    ) -> Dict[str, int]:
        """Reshard cluster."""
        cluster = self._clusters.get(cluster_name)
        
        if cluster:
            return await cluster.reshard()
        
        return {}
    
    # ----- Status -----
    
    def get_stats(self, cluster_name: str) -> Optional[ShardingStats]:
        """Get cluster stats."""
        cluster = self._clusters.get(cluster_name)
        
        if cluster:
            return cluster.stats
        
        return None
    
    # ----- Engine Stats -----
    
    def stats(self) -> Dict[str, Any]:
        """Get engine stats."""
        total_shards = 0
        total_keys = 0
        
        for cluster in self._clusters.values():
            total_shards += cluster.shard_count
            total_keys += cluster.stats.total_keys
        
        return {
            "clusters": len(self._clusters),
            "total_shards": total_shards,
            "total_keys": total_keys
        }
    
    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        cluster_info = {}
        
        for name, cluster in self._clusters.items():
            cluster_info[name] = {
                "shard_count": cluster.shard_count,
                "total_keys": cluster.stats.total_keys,
                "reads": cluster.stats.total_reads,
                "writes": cluster.stats.total_writes
            }
        
        return {"clusters": cluster_info}


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Sharding Engine."""
    print("=" * 70)
    print("BAEL - SHARDING ENGINE DEMO")
    print("Data Sharding for Agents")
    print("=" * 70)
    print()
    
    engine = ShardingEngine()
    
    # 1. Create Shard Cluster
    print("1. CREATE SHARD CLUSTER:")
    print("-" * 40)
    
    cluster = engine.create_hash_cluster("products", shard_count=4)
    
    print(f"   Created cluster: {cluster.name}")
    print(f"   Shards: {cluster.shard_count}")
    print()
    
    # 2. Insert Data
    print("2. INSERT DATA:")
    print("-" * 40)
    
    for i in range(20):
        product_id = f"prod_{i:04d}"
        product = {
            "name": f"Product {i}",
            "price": 10.99 + i,
            "category": ["electronics", "clothing", "home"][i % 3]
        }
        
        success, shard_id = engine.put("products", product_id, product)
        
        if i < 5:
            print(f"   {product_id} -> shard {shard_id[:8]}")
    
    print(f"   ... inserted 20 products")
    print()
    
    # 3. Get Data
    print("3. GET DATA:")
    print("-" * 40)
    
    product = engine.get("products", "prod_0005")
    print(f"   prod_0005: {product}")
    
    product = engine.get("products", "prod_0010")
    print(f"   prod_0010: {product}")
    print()
    
    # 4. Check Shard Distribution
    print("4. SHARD DISTRIBUTION:")
    print("-" * 40)
    
    distribution = engine.get_shard_distribution("products")
    for shard_id, count in distribution.items():
        print(f"   Shard {shard_id[:8]}: {count} keys")
    print()
    
    # 5. Query with Scatter-Gather
    print("5. SCATTER-GATHER QUERY:")
    print("-" * 40)
    
    results = await engine.query(
        "products",
        lambda k, v: v.get("category") == "electronics"
    )
    
    print(f"   Electronics products: {len(results)}")
    for key, value in results[:3]:
        print(f"      {key}: {value['name']}")
    print()
    
    # 6. Add Shard
    print("6. ADD SHARD:")
    print("-" * 40)
    
    new_shard = await engine.add_shard("products")
    print(f"   Added shard: {new_shard.name}")
    print(f"   Total shards: {engine.get_shard_count('products')}")
    print()
    
    # 7. Reshard
    print("7. RESHARD:")
    print("-" * 40)
    
    result = await engine.reshard("products")
    print(f"   Resharded: {result}")
    
    distribution = engine.get_shard_distribution("products")
    for shard_id, count in distribution.items():
        print(f"   Shard {shard_id[:8]}: {count} keys")
    print()
    
    # 8. Shard States
    print("8. SHARD STATES:")
    print("-" * 40)
    
    for shard in cluster.get_all_shards():
        print(f"   {shard.name}:")
        print(f"      State: {shard.state.value}")
        print(f"      Role: {shard.role.value}")
        print(f"      Keys: {shard.stats.key_count}")
    print()
    
    # 9. Query High-Price Products
    print("9. QUERY HIGH-PRICE PRODUCTS:")
    print("-" * 40)
    
    results = await engine.query(
        "products",
        lambda k, v: v.get("price", 0) > 20
    )
    
    print(f"   Products over $20: {len(results)}")
    for key, value in results[:3]:
        print(f"      {key}: ${value['price']:.2f}")
    print()
    
    # 10. Create Another Cluster
    print("10. CREATE ANOTHER CLUSTER:")
    print("-" * 40)
    
    orders_cluster = engine.create_cluster("orders", ShardingConfig(
        sharding_type=ShardingType.HASH,
        shard_count=3
    ))
    
    for i in range(10):
        order_id = f"order_{i:04d}"
        engine.put("orders", order_id, {"customer": f"cust_{i % 5}", "total": 50 + i * 10})
    
    print(f"   Created: {orders_cluster.name}")
    print(f"   Inserted 10 orders")
    print()
    
    # 11. List Clusters
    print("11. LIST CLUSTERS:")
    print("-" * 40)
    
    clusters = engine.list_clusters()
    for c in clusters:
        print(f"   - {c}")
    print()
    
    # 12. Cluster Statistics
    print("12. CLUSTER STATISTICS:")
    print("-" * 40)
    
    stats = engine.get_stats("products")
    print(f"   Products cluster:")
    print(f"      Total shards: {stats.total_shards}")
    print(f"      Total keys: {stats.total_keys}")
    print(f"      Total reads: {stats.total_reads}")
    print(f"      Total writes: {stats.total_writes}")
    print()
    
    # 13. Engine Statistics
    print("13. ENGINE STATISTICS:")
    print("-" * 40)
    
    stats = engine.stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()
    
    # 14. Engine Summary
    print("14. ENGINE SUMMARY:")
    print("-" * 40)
    
    summary = engine.summary()
    for name, info in summary["clusters"].items():
        print(f"   {name}:")
        print(f"      Shards: {info['shard_count']}")
        print(f"      Keys: {info['total_keys']}")
    print()
    
    print("=" * 70)
    print("DEMO COMPLETE - Sharding Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
