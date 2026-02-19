"""
🌐 DISTRIBUTED MEMORY 🌐
========================
Shared memory system.

Features:
- Distributed cache
- Memory consistency
- Replication
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set
from datetime import datetime
import uuid
import hashlib


class ConsistencyLevel(Enum):
    """Consistency levels"""
    STRONG = auto()      # Linearizability
    SEQUENTIAL = auto()  # Sequential consistency
    CAUSAL = auto()      # Causal consistency
    EVENTUAL = auto()    # Eventual consistency


@dataclass
class MemorySegment:
    """A memory segment"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Key
    key: str = ""

    # Value
    value: Any = None

    # Version
    version: int = 0
    vector_clock: Dict[str, int] = field(default_factory=dict)

    # Ownership
    owner_node: str = ""

    # Replication
    replicas: List[str] = field(default_factory=list)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # TTL
    ttl_seconds: Optional[int] = None

    def update(self, value: Any, node_id: str):
        """Update value"""
        self.value = value
        self.version += 1
        self.updated_at = datetime.now()

        # Update vector clock
        if node_id not in self.vector_clock:
            self.vector_clock[node_id] = 0
        self.vector_clock[node_id] += 1

    def is_expired(self) -> bool:
        """Check if expired"""
        if self.ttl_seconds is None:
            return False

        elapsed = (datetime.now() - self.updated_at).total_seconds()
        return elapsed > self.ttl_seconds

    def get_hash(self) -> str:
        """Get content hash"""
        return hashlib.sha256(str(self.value).encode()).hexdigest()[:16]


class SharedMemory:
    """
    Distributed shared memory.
    """

    def __init__(self, node_id: str):
        self.node_id = node_id

        self.segments: Dict[str, MemorySegment] = {}

        # Local cache
        self.cache: Dict[str, Any] = {}
        self.cache_versions: Dict[str, int] = {}

        # Consistency
        self.consistency_level = ConsistencyLevel.EVENTUAL

    def read(self, key: str) -> Optional[Any]:
        """Read value"""
        # Check cache first
        if key in self.cache:
            segment = self.segments.get(key)
            if segment and self.cache_versions.get(key) == segment.version:
                return self.cache[key]

        # Read from segment
        segment = self.segments.get(key)
        if segment:
            if segment.is_expired():
                del self.segments[key]
                return None

            # Update cache
            self.cache[key] = segment.value
            self.cache_versions[key] = segment.version

            return segment.value

        return None

    def write(self, key: str, value: Any, ttl: int = None) -> bool:
        """Write value"""
        if key in self.segments:
            segment = self.segments[key]
            segment.update(value, self.node_id)
            if ttl:
                segment.ttl_seconds = ttl
        else:
            segment = MemorySegment(
                key=key,
                value=value,
                owner_node=self.node_id,
                ttl_seconds=ttl
            )
            segment.vector_clock[self.node_id] = 1
            self.segments[key] = segment

        # Update cache
        self.cache[key] = value
        self.cache_versions[key] = segment.version

        return True

    def delete(self, key: str) -> bool:
        """Delete value"""
        if key in self.segments:
            del self.segments[key]

        if key in self.cache:
            del self.cache[key]
            del self.cache_versions[key]

        return True

    def get_segment(self, key: str) -> Optional[MemorySegment]:
        """Get raw segment"""
        return self.segments.get(key)

    def list_keys(self) -> List[str]:
        """List all keys"""
        return list(self.segments.keys())

    def sync(self, remote_segment: MemorySegment):
        """Sync with remote segment"""
        key = remote_segment.key

        if key not in self.segments:
            # New key
            self.segments[key] = remote_segment
        else:
            local = self.segments[key]

            # Compare vector clocks
            if self._happens_before(local.vector_clock, remote_segment.vector_clock):
                # Remote is newer
                self.segments[key] = remote_segment
            elif self._happens_before(remote_segment.vector_clock, local.vector_clock):
                # Local is newer, keep it
                pass
            else:
                # Concurrent - merge
                self._merge(local, remote_segment)

    def _happens_before(
        self,
        vc1: Dict[str, int],
        vc2: Dict[str, int]
    ) -> bool:
        """Check if vc1 happens before vc2"""
        all_keys = set(vc1.keys()) | set(vc2.keys())

        at_least_one_less = False
        for key in all_keys:
            v1 = vc1.get(key, 0)
            v2 = vc2.get(key, 0)

            if v1 > v2:
                return False
            if v1 < v2:
                at_least_one_less = True

        return at_least_one_less

    def _merge(self, local: MemorySegment, remote: MemorySegment):
        """Merge concurrent updates (last-writer-wins for simplicity)"""
        if remote.updated_at > local.updated_at:
            self.segments[local.key] = remote


class DistributedCache:
    """
    Distributed cache with partitioning.
    """

    def __init__(self, node_id: str, num_partitions: int = 16):
        self.node_id = node_id
        self.num_partitions = num_partitions

        self.partitions: Dict[int, SharedMemory] = {}

        for i in range(num_partitions):
            self.partitions[i] = SharedMemory(node_id)

        # Partition ownership
        self.partition_owners: Dict[int, str] = {}

        # Stats
        self.hits: int = 0
        self.misses: int = 0

    def _get_partition(self, key: str) -> int:
        """Get partition for key"""
        return hash(key) % self.num_partitions

    def get(self, key: str) -> Optional[Any]:
        """Get value"""
        partition_id = self._get_partition(key)
        partition = self.partitions[partition_id]

        value = partition.read(key)

        if value is not None:
            self.hits += 1
        else:
            self.misses += 1

        return value

    def put(self, key: str, value: Any, ttl: int = None) -> bool:
        """Put value"""
        partition_id = self._get_partition(key)
        partition = self.partitions[partition_id]
        return partition.write(key, value, ttl)

    def remove(self, key: str) -> bool:
        """Remove value"""
        partition_id = self._get_partition(key)
        partition = self.partitions[partition_id]
        return partition.delete(key)

    def get_hit_rate(self) -> float:
        """Get cache hit rate"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache stats"""
        total_keys = sum(
            len(p.segments) for p in self.partitions.values()
        )

        return {
            'total_keys': total_keys,
            'partitions': self.num_partitions,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': self.get_hit_rate()
        }


class MemoryConsistency:
    """
    Memory consistency manager.
    """

    def __init__(self, level: ConsistencyLevel = ConsistencyLevel.EVENTUAL):
        self.level = level

        # Write log for ordering
        self.write_log: List[Dict[str, Any]] = []

        # Lock for strong consistency
        self.locks: Dict[str, str] = {}  # key -> node_id

    def acquire_lock(self, key: str, node_id: str) -> bool:
        """Acquire lock (for strong consistency)"""
        if self.level != ConsistencyLevel.STRONG:
            return True

        if key in self.locks:
            return False

        self.locks[key] = node_id
        return True

    def release_lock(self, key: str, node_id: str):
        """Release lock"""
        if key in self.locks and self.locks[key] == node_id:
            del self.locks[key]

    def log_write(self, key: str, value: Any, node_id: str):
        """Log write for ordering"""
        self.write_log.append({
            'key': key,
            'value': value,
            'node_id': node_id,
            'timestamp': datetime.now().isoformat()
        })

        # Keep last 10000
        if len(self.write_log) > 10000:
            self.write_log = self.write_log[-10000:]

    def get_write_order(self, key: str) -> List[Dict[str, Any]]:
        """Get write order for key"""
        return [w for w in self.write_log if w['key'] == key]


class EventualConsistency:
    """
    Eventual consistency implementation.
    """

    def __init__(self):
        self.anti_entropy_interval_seconds: int = 10

        # Pending syncs
        self.pending_syncs: List[MemorySegment] = []

        # Merkle tree for efficient sync
        self.merkle_roots: Dict[str, str] = {}

    def add_pending_sync(self, segment: MemorySegment):
        """Add segment to pending sync"""
        self.pending_syncs.append(segment)

    def get_pending_syncs(self) -> List[MemorySegment]:
        """Get and clear pending syncs"""
        syncs = self.pending_syncs
        self.pending_syncs = []
        return syncs

    def compute_merkle_root(self, segments: Dict[str, MemorySegment]) -> str:
        """Compute Merkle root for sync detection"""
        if not segments:
            return hashlib.sha256(b"empty").hexdigest()

        # Sort keys
        sorted_keys = sorted(segments.keys())

        # Compute leaf hashes
        leaves = [segments[k].get_hash() for k in sorted_keys]

        # Build tree
        while len(leaves) > 1:
            new_leaves = []
            for i in range(0, len(leaves), 2):
                left = leaves[i]
                right = leaves[i + 1] if i + 1 < len(leaves) else left
                combined = hashlib.sha256(f"{left}{right}".encode()).hexdigest()
                new_leaves.append(combined)
            leaves = new_leaves

        return leaves[0]

    def needs_sync(
        self,
        local_segments: Dict[str, MemorySegment],
        remote_root: str
    ) -> bool:
        """Check if sync needed"""
        local_root = self.compute_merkle_root(local_segments)
        return local_root != remote_root


# Export all
__all__ = [
    'ConsistencyLevel',
    'MemorySegment',
    'SharedMemory',
    'DistributedCache',
    'MemoryConsistency',
    'EventualConsistency',
]
