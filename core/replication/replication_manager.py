#!/usr/bin/env python3
"""
BAEL - Replication Manager
Advanced data replication for AI agent operations.

Features:
- Synchronous replication
- Asynchronous replication
- Multi-master replication
- Conflict resolution
- Change data capture
- Replication lag tracking
- Failover management
- Consistency levels
- Quorum operations
- Replication topology
"""

import asyncio
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

class ReplicationType(Enum):
    """Replication types."""
    SYNCHRONOUS = "synchronous"
    ASYNCHRONOUS = "asynchronous"
    SEMI_SYNCHRONOUS = "semi_synchronous"


class ReplicationRole(Enum):
    """Replication roles."""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    ARBITER = "arbiter"


class ReplicaState(Enum):
    """Replica state."""
    ACTIVE = "active"
    SYNCING = "syncing"
    LAGGING = "lagging"
    OFFLINE = "offline"
    RECOVERING = "recovering"


class ConsistencyLevel(Enum):
    """Consistency levels."""
    ONE = "one"
    QUORUM = "quorum"
    ALL = "all"
    LOCAL_QUORUM = "local_quorum"


class ConflictResolution(Enum):
    """Conflict resolution strategies."""
    LAST_WRITE_WINS = "last_write_wins"
    FIRST_WRITE_WINS = "first_write_wins"
    HIGHEST_VERSION = "highest_version"
    CUSTOM = "custom"


class OperationType(Enum):
    """Operation types."""
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class ReplicationConfig:
    """Replication configuration."""
    replication_type: ReplicationType = ReplicationType.ASYNCHRONOUS
    replication_factor: int = 3
    consistency_level: ConsistencyLevel = ConsistencyLevel.QUORUM
    conflict_resolution: ConflictResolution = ConflictResolution.LAST_WRITE_WINS
    sync_interval_ms: int = 100
    max_lag_ms: int = 5000
    enable_cdc: bool = True


@dataclass
class Replica:
    """Replica node."""
    replica_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: ReplicationRole = ReplicationRole.SECONDARY
    state: ReplicaState = ReplicaState.ACTIVE
    host: str = "localhost"
    port: int = 5432
    datacenter: str = "dc1"
    rack: str = "rack1"
    last_sync: Optional[datetime] = None
    lag_ms: int = 0
    version: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChangeEvent:
    """Change data capture event."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    operation: OperationType = OperationType.INSERT
    key: str = ""
    value: Any = None
    old_value: Any = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    version: int = 0
    source_replica: str = ""


@dataclass
class ConflictRecord:
    """Conflict record."""
    conflict_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    key: str = ""
    events: List[ChangeEvent] = field(default_factory=list)
    resolved_value: Any = None
    resolution_method: ConflictResolution = ConflictResolution.LAST_WRITE_WINS
    resolved_at: Optional[datetime] = None


@dataclass
class ReplicationStats:
    """Replication statistics."""
    replica_id: str = ""
    operations_replicated: int = 0
    bytes_replicated: int = 0
    conflicts_detected: int = 0
    conflicts_resolved: int = 0
    avg_lag_ms: float = 0.0
    max_lag_ms: int = 0
    last_sync: Optional[datetime] = None


@dataclass
class WriteResult:
    """Write result."""
    success: bool = False
    version: int = 0
    replicas_written: int = 0
    replicas_required: int = 0
    error: Optional[str] = None


# =============================================================================
# VECTOR CLOCK
# =============================================================================

class VectorClock:
    """Vector clock for conflict detection."""

    def __init__(self):
        self._clocks: Dict[str, int] = {}
        self._lock = threading.Lock()

    def increment(self, node_id: str) -> None:
        """Increment clock for node."""
        with self._lock:
            self._clocks[node_id] = self._clocks.get(node_id, 0) + 1

    def update(self, other: 'VectorClock') -> None:
        """Update clock from another clock."""
        with self._lock:
            for node_id, value in other._clocks.items():
                self._clocks[node_id] = max(
                    self._clocks.get(node_id, 0),
                    value
                )

    def get(self, node_id: str) -> int:
        """Get clock value for node."""
        with self._lock:
            return self._clocks.get(node_id, 0)

    def compare(self, other: 'VectorClock') -> int:
        """
        Compare clocks.
        Returns:
          -1: self < other
           0: concurrent
           1: self > other
        """
        with self._lock:
            all_nodes = set(self._clocks.keys()) | set(other._clocks.keys())

            self_greater = False
            other_greater = False

            for node in all_nodes:
                self_val = self._clocks.get(node, 0)
                other_val = other._clocks.get(node, 0)

                if self_val > other_val:
                    self_greater = True
                elif other_val > self_val:
                    other_greater = True

            if self_greater and not other_greater:
                return 1
            elif other_greater and not self_greater:
                return -1
            else:
                return 0

    def copy(self) -> 'VectorClock':
        """Create a copy."""
        vc = VectorClock()
        with self._lock:
            vc._clocks = dict(self._clocks)
        return vc

    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary."""
        with self._lock:
            return dict(self._clocks)


# =============================================================================
# CONFLICT RESOLVER
# =============================================================================

class ConflictResolver(ABC):
    """Base conflict resolver."""

    @abstractmethod
    def resolve(
        self,
        key: str,
        events: List[ChangeEvent]
    ) -> ChangeEvent:
        """Resolve conflict."""
        pass


class LastWriteWinsResolver(ConflictResolver):
    """Last write wins resolver."""

    def resolve(
        self,
        key: str,
        events: List[ChangeEvent]
    ) -> ChangeEvent:
        return max(events, key=lambda e: e.timestamp)


class FirstWriteWinsResolver(ConflictResolver):
    """First write wins resolver."""

    def resolve(
        self,
        key: str,
        events: List[ChangeEvent]
    ) -> ChangeEvent:
        return min(events, key=lambda e: e.timestamp)


class HighestVersionResolver(ConflictResolver):
    """Highest version wins resolver."""

    def resolve(
        self,
        key: str,
        events: List[ChangeEvent]
    ) -> ChangeEvent:
        return max(events, key=lambda e: e.version)


class MergeResolver(ConflictResolver):
    """Merge-based resolver for dictionaries."""

    def resolve(
        self,
        key: str,
        events: List[ChangeEvent]
    ) -> ChangeEvent:
        # Sort by timestamp
        sorted_events = sorted(events, key=lambda e: e.timestamp)

        # Merge all values
        merged = {}
        for event in sorted_events:
            if isinstance(event.value, dict):
                merged.update(event.value)
            else:
                merged = event.value

        # Return event with merged value
        result = sorted_events[-1]
        result.value = merged
        return result


# =============================================================================
# REPLICA STORE
# =============================================================================

class ReplicaStore:
    """In-memory replica data store."""

    def __init__(self, replica_id: str):
        self._replica_id = replica_id
        self._data: Dict[str, Any] = {}
        self._versions: Dict[str, int] = {}
        self._clocks: Dict[str, VectorClock] = {}
        self._changelog: List[ChangeEvent] = []
        self._lock = threading.RLock()

    def write(
        self,
        key: str,
        value: Any,
        version: Optional[int] = None
    ) -> ChangeEvent:
        """Write value."""
        with self._lock:
            old_value = self._data.get(key)

            # Determine version
            if version is None:
                version = self._versions.get(key, 0) + 1

            self._data[key] = value
            self._versions[key] = version

            # Update vector clock
            if key not in self._clocks:
                self._clocks[key] = VectorClock()
            self._clocks[key].increment(self._replica_id)

            # Create change event
            operation = OperationType.UPDATE if old_value else OperationType.INSERT

            event = ChangeEvent(
                operation=operation,
                key=key,
                value=value,
                old_value=old_value,
                version=version,
                source_replica=self._replica_id
            )

            self._changelog.append(event)

            return event

    def read(self, key: str) -> Optional[Any]:
        """Read value."""
        with self._lock:
            return self._data.get(key)

    def delete(self, key: str) -> Optional[ChangeEvent]:
        """Delete value."""
        with self._lock:
            if key not in self._data:
                return None

            old_value = self._data.pop(key)
            version = self._versions.pop(key, 0)

            if key in self._clocks:
                self._clocks[key].increment(self._replica_id)

            event = ChangeEvent(
                operation=OperationType.DELETE,
                key=key,
                old_value=old_value,
                version=version,
                source_replica=self._replica_id
            )

            self._changelog.append(event)

            return event

    def get_version(self, key: str) -> int:
        """Get version for key."""
        with self._lock:
            return self._versions.get(key, 0)

    def get_clock(self, key: str) -> Optional[VectorClock]:
        """Get vector clock for key."""
        with self._lock:
            vc = self._clocks.get(key)
            return vc.copy() if vc else None

    def get_changelog(
        self,
        since_version: int = 0
    ) -> List[ChangeEvent]:
        """Get changelog since version."""
        with self._lock:
            return [
                e for e in self._changelog
                if e.version > since_version
            ]

    def apply_event(self, event: ChangeEvent) -> bool:
        """Apply change event from another replica."""
        with self._lock:
            current_version = self._versions.get(event.key, 0)

            if event.version <= current_version:
                return False

            if event.operation == OperationType.DELETE:
                self._data.pop(event.key, None)
                self._versions.pop(event.key, None)
            else:
                self._data[event.key] = event.value
                self._versions[event.key] = event.version

            # Update clock
            if event.key not in self._clocks:
                self._clocks[event.key] = VectorClock()
            self._clocks[event.key].increment(event.source_replica)

            return True

    def get_all_keys(self) -> List[str]:
        """Get all keys."""
        with self._lock:
            return list(self._data.keys())

    def snapshot(self) -> Dict[str, Any]:
        """Get data snapshot."""
        with self._lock:
            return dict(self._data)


# =============================================================================
# REPLICATION MANAGER
# =============================================================================

class ReplicationManager:
    """
    Replication Manager for BAEL.

    Advanced data replication.
    """

    def __init__(self, config: Optional[ReplicationConfig] = None):
        self._config = config or ReplicationConfig()
        self._replicas: Dict[str, Replica] = {}
        self._stores: Dict[str, ReplicaStore] = {}
        self._primary_id: Optional[str] = None
        self._conflicts: List[ConflictRecord] = []
        self._stats: Dict[str, ReplicationStats] = {}
        self._resolver = self._create_resolver()
        self._lock = threading.RLock()
        self._running = False
        self._sync_task: Optional[asyncio.Task] = None

    def _create_resolver(self) -> ConflictResolver:
        """Create conflict resolver."""
        if self._config.conflict_resolution == ConflictResolution.LAST_WRITE_WINS:
            return LastWriteWinsResolver()
        elif self._config.conflict_resolution == ConflictResolution.FIRST_WRITE_WINS:
            return FirstWriteWinsResolver()
        elif self._config.conflict_resolution == ConflictResolution.HIGHEST_VERSION:
            return HighestVersionResolver()

        return LastWriteWinsResolver()

    # -------------------------------------------------------------------------
    # REPLICA MANAGEMENT
    # -------------------------------------------------------------------------

    def add_replica(
        self,
        host: str = "localhost",
        port: int = 5432,
        role: ReplicationRole = ReplicationRole.SECONDARY,
        datacenter: str = "dc1"
    ) -> Replica:
        """Add replica."""
        replica = Replica(
            role=role,
            host=host,
            port=port,
            datacenter=datacenter
        )

        with self._lock:
            self._replicas[replica.replica_id] = replica
            self._stores[replica.replica_id] = ReplicaStore(replica.replica_id)
            self._stats[replica.replica_id] = ReplicationStats(
                replica_id=replica.replica_id
            )

            if role == ReplicationRole.PRIMARY:
                self._primary_id = replica.replica_id

        return replica

    def remove_replica(self, replica_id: str) -> bool:
        """Remove replica."""
        with self._lock:
            if replica_id in self._replicas:
                del self._replicas[replica_id]
                del self._stores[replica_id]
                del self._stats[replica_id]

                if self._primary_id == replica_id:
                    self._primary_id = None

                return True

        return False

    def get_replica(self, replica_id: str) -> Optional[Replica]:
        """Get replica."""
        with self._lock:
            return self._replicas.get(replica_id)

    def list_replicas(self) -> List[Replica]:
        """List replicas."""
        with self._lock:
            return list(self._replicas.values())

    def get_primary(self) -> Optional[Replica]:
        """Get primary replica."""
        with self._lock:
            if self._primary_id:
                return self._replicas.get(self._primary_id)
        return None

    def get_secondaries(self) -> List[Replica]:
        """Get secondary replicas."""
        with self._lock:
            return [
                r for r in self._replicas.values()
                if r.role == ReplicationRole.SECONDARY
            ]

    # -------------------------------------------------------------------------
    # WRITE OPERATIONS
    # -------------------------------------------------------------------------

    async def write(
        self,
        key: str,
        value: Any,
        consistency: Optional[ConsistencyLevel] = None
    ) -> WriteResult:
        """Write with specified consistency."""
        consistency = consistency or self._config.consistency_level

        with self._lock:
            if not self._primary_id:
                return WriteResult(
                    success=False,
                    error="No primary replica"
                )

            primary_store = self._stores.get(self._primary_id)
            if not primary_store:
                return WriteResult(
                    success=False,
                    error="Primary store not found"
                )

            # Write to primary
            event = primary_store.write(key, value)
            replicas_written = 1

            # Determine required replicas
            secondaries = self.get_secondaries()

            if consistency == ConsistencyLevel.ONE:
                replicas_required = 1
            elif consistency == ConsistencyLevel.QUORUM:
                replicas_required = (len(secondaries) + 1) // 2 + 1
            elif consistency == ConsistencyLevel.ALL:
                replicas_required = len(secondaries) + 1
            else:
                replicas_required = 1

            # Replicate based on type
            if self._config.replication_type == ReplicationType.SYNCHRONOUS:
                # Synchronous: wait for all required
                for replica in secondaries:
                    store = self._stores.get(replica.replica_id)
                    if store:
                        if store.apply_event(event):
                            replicas_written += 1
                            self._update_stats(replica.replica_id, event)

            elif self._config.replication_type == ReplicationType.ASYNCHRONOUS:
                # Async: replicate in background
                asyncio.create_task(
                    self._async_replicate(event, secondaries)
                )

            elif self._config.replication_type == ReplicationType.SEMI_SYNCHRONOUS:
                # Semi-sync: wait for at least one secondary
                for replica in secondaries:
                    store = self._stores.get(replica.replica_id)
                    if store:
                        if store.apply_event(event):
                            replicas_written += 1
                            self._update_stats(replica.replica_id, event)
                            break

                # Replicate rest async
                asyncio.create_task(
                    self._async_replicate(event, secondaries[1:])
                )

        return WriteResult(
            success=replicas_written >= replicas_required,
            version=event.version,
            replicas_written=replicas_written,
            replicas_required=replicas_required
        )

    async def _async_replicate(
        self,
        event: ChangeEvent,
        replicas: List[Replica]
    ) -> None:
        """Async replication."""
        for replica in replicas:
            store = self._stores.get(replica.replica_id)
            if store:
                if store.apply_event(event):
                    self._update_stats(replica.replica_id, event)

            await asyncio.sleep(0)

    def _update_stats(
        self,
        replica_id: str,
        event: ChangeEvent
    ) -> None:
        """Update replication stats."""
        with self._lock:
            stats = self._stats.get(replica_id)
            if stats:
                stats.operations_replicated += 1
                stats.last_sync = datetime.utcnow()

            replica = self._replicas.get(replica_id)
            if replica:
                replica.last_sync = datetime.utcnow()
                replica.version = event.version

    # -------------------------------------------------------------------------
    # READ OPERATIONS
    # -------------------------------------------------------------------------

    async def read(
        self,
        key: str,
        consistency: Optional[ConsistencyLevel] = None
    ) -> Optional[Any]:
        """Read with specified consistency."""
        consistency = consistency or self._config.consistency_level

        with self._lock:
            if consistency == ConsistencyLevel.ONE:
                # Read from any replica
                for store in self._stores.values():
                    value = store.read(key)
                    if value is not None:
                        return value
                return None

            elif consistency == ConsistencyLevel.ALL:
                # Read from all and check consistency
                values = []
                for store in self._stores.values():
                    value = store.read(key)
                    if value is not None:
                        values.append(value)

                if not values:
                    return None

                # Check all values are same
                first = values[0]
                if all(v == first for v in values):
                    return first

                # Conflict - resolve
                return values[0]

            else:
                # Quorum read
                replicas = list(self._stores.values())
                quorum = len(replicas) // 2 + 1

                values = []
                for store in replicas:
                    value = store.read(key)
                    if value is not None:
                        values.append(value)
                        if len(values) >= quorum:
                            break

                return values[0] if values else None

    async def read_from_replica(
        self,
        key: str,
        replica_id: str
    ) -> Optional[Any]:
        """Read from specific replica."""
        with self._lock:
            store = self._stores.get(replica_id)
            if store:
                return store.read(key)
        return None

    # -------------------------------------------------------------------------
    # CONFLICT DETECTION
    # -------------------------------------------------------------------------

    def detect_conflicts(self, key: str) -> Optional[ConflictRecord]:
        """Detect conflicts for key."""
        with self._lock:
            events = []

            for replica_id, store in self._stores.items():
                value = store.read(key)
                version = store.get_version(key)

                if value is not None:
                    events.append(ChangeEvent(
                        key=key,
                        value=value,
                        version=version,
                        source_replica=replica_id
                    ))

            if len(events) <= 1:
                return None

            # Check if values differ
            first_value = events[0].value
            has_conflict = any(e.value != first_value for e in events)

            if has_conflict:
                record = ConflictRecord(
                    key=key,
                    events=events
                )
                self._conflicts.append(record)
                return record

        return None

    def resolve_conflict(
        self,
        conflict_id: str
    ) -> Optional[ConflictRecord]:
        """Resolve conflict."""
        with self._lock:
            for record in self._conflicts:
                if record.conflict_id == conflict_id:
                    # Resolve
                    winner = self._resolver.resolve(
                        record.key,
                        record.events
                    )

                    record.resolved_value = winner.value
                    record.resolved_at = datetime.utcnow()

                    # Apply to all replicas
                    for store in self._stores.values():
                        store.write(
                            record.key,
                            winner.value,
                            winner.version + 1
                        )

                    return record

        return None

    def get_conflicts(self) -> List[ConflictRecord]:
        """Get all conflicts."""
        with self._lock:
            return list(self._conflicts)

    # -------------------------------------------------------------------------
    # CHANGE DATA CAPTURE
    # -------------------------------------------------------------------------

    def get_changes(
        self,
        replica_id: str,
        since_version: int = 0
    ) -> List[ChangeEvent]:
        """Get changes from replica."""
        with self._lock:
            store = self._stores.get(replica_id)
            if store:
                return store.get_changelog(since_version)
        return []

    def subscribe_changes(
        self,
        callback: Callable[[ChangeEvent], None],
        replica_id: Optional[str] = None
    ) -> str:
        """Subscribe to changes."""
        # In real implementation, would use event system
        subscription_id = str(uuid.uuid4())
        return subscription_id

    # -------------------------------------------------------------------------
    # FAILOVER
    # -------------------------------------------------------------------------

    async def failover_to(self, replica_id: str) -> bool:
        """Failover to specified replica."""
        with self._lock:
            replica = self._replicas.get(replica_id)

            if not replica:
                return False

            if replica.role == ReplicationRole.PRIMARY:
                return True  # Already primary

            # Demote current primary
            if self._primary_id:
                old_primary = self._replicas.get(self._primary_id)
                if old_primary:
                    old_primary.role = ReplicationRole.SECONDARY

            # Promote new primary
            replica.role = ReplicationRole.PRIMARY
            self._primary_id = replica_id

        return True

    async def auto_failover(self) -> Optional[Replica]:
        """Auto failover to best secondary."""
        with self._lock:
            secondaries = self.get_secondaries()

            if not secondaries:
                return None

            # Find best candidate (lowest lag, highest version)
            best = min(
                secondaries,
                key=lambda r: (r.lag_ms, -r.version)
            )

            await self.failover_to(best.replica_id)
            return best

    # -------------------------------------------------------------------------
    # SYNC AND LAG
    # -------------------------------------------------------------------------

    async def sync_replica(self, replica_id: str) -> bool:
        """Sync replica with primary."""
        with self._lock:
            if not self._primary_id:
                return False

            primary_store = self._stores.get(self._primary_id)
            replica_store = self._stores.get(replica_id)
            replica = self._replicas.get(replica_id)

            if not all([primary_store, replica_store, replica]):
                return False

            replica.state = ReplicaState.SYNCING

            # Get changes from primary
            replica_version = max(
                (replica_store.get_version(k) for k in replica_store.get_all_keys()),
                default=0
            )

            changes = primary_store.get_changelog(replica_version)

            # Apply changes
            for change in changes:
                replica_store.apply_event(change)

            replica.state = ReplicaState.ACTIVE
            replica.last_sync = datetime.utcnow()
            replica.lag_ms = 0

        return True

    def get_lag(self, replica_id: str) -> int:
        """Get replication lag in ms."""
        with self._lock:
            replica = self._replicas.get(replica_id)

            if not replica or not replica.last_sync:
                return -1

            lag = (datetime.utcnow() - replica.last_sync).total_seconds() * 1000
            replica.lag_ms = int(lag)

            if lag > self._config.max_lag_ms:
                replica.state = ReplicaState.LAGGING

            return int(lag)

    # -------------------------------------------------------------------------
    # QUORUM OPERATIONS
    # -------------------------------------------------------------------------

    def calculate_quorum(self) -> int:
        """Calculate quorum size."""
        with self._lock:
            total = len(self._replicas)
            return total // 2 + 1

    def has_quorum(self) -> bool:
        """Check if quorum is available."""
        with self._lock:
            active = sum(
                1 for r in self._replicas.values()
                if r.state == ReplicaState.ACTIVE
            )
            return active >= self.calculate_quorum()

    async def quorum_write(
        self,
        key: str,
        value: Any
    ) -> WriteResult:
        """Write with quorum consistency."""
        return await self.write(key, value, ConsistencyLevel.QUORUM)

    async def quorum_read(self, key: str) -> Optional[Any]:
        """Read with quorum consistency."""
        return await self.read(key, ConsistencyLevel.QUORUM)

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self, replica_id: str) -> Optional[ReplicationStats]:
        """Get replica stats."""
        with self._lock:
            return self._stats.get(replica_id)

    def get_all_stats(self) -> Dict[str, ReplicationStats]:
        """Get all stats."""
        with self._lock:
            return dict(self._stats)

    def get_cluster_status(self) -> Dict[str, Any]:
        """Get cluster status."""
        with self._lock:
            return {
                "total_replicas": len(self._replicas),
                "primary": self._primary_id,
                "has_quorum": self.has_quorum(),
                "quorum_size": self.calculate_quorum(),
                "active_replicas": sum(
                    1 for r in self._replicas.values()
                    if r.state == ReplicaState.ACTIVE
                ),
                "conflicts": len(self._conflicts)
            }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Replication Manager."""
    print("=" * 70)
    print("BAEL - REPLICATION MANAGER DEMO")
    print("Advanced Data Replication for AI Agents")
    print("=" * 70)
    print()

    manager = ReplicationManager(ReplicationConfig(
        replication_type=ReplicationType.SYNCHRONOUS,
        replication_factor=3,
        consistency_level=ConsistencyLevel.QUORUM
    ))

    # 1. Add Replicas
    print("1. ADD REPLICAS:")
    print("-" * 40)

    primary = manager.add_replica(
        host="primary.local",
        port=5432,
        role=ReplicationRole.PRIMARY
    )
    print(f"   Primary: {primary.replica_id[:8]}...")

    secondary1 = manager.add_replica(
        host="secondary1.local",
        port=5432,
        role=ReplicationRole.SECONDARY
    )
    print(f"   Secondary 1: {secondary1.replica_id[:8]}...")

    secondary2 = manager.add_replica(
        host="secondary2.local",
        port=5432,
        role=ReplicationRole.SECONDARY
    )
    print(f"   Secondary 2: {secondary2.replica_id[:8]}...")
    print()

    # 2. Write Operations
    print("2. WRITE OPERATIONS:")
    print("-" * 40)

    result = await manager.write("user:1", {"name": "Alice", "age": 30})
    print(f"   Write user:1: success={result.success}, "
          f"replicas={result.replicas_written}/{result.replicas_required}")

    result = await manager.write("user:2", {"name": "Bob", "age": 25})
    print(f"   Write user:2: success={result.success}, "
          f"replicas={result.replicas_written}/{result.replicas_required}")
    print()

    # 3. Read Operations
    print("3. READ OPERATIONS:")
    print("-" * 40)

    value = await manager.read("user:1")
    print(f"   Read user:1: {value}")

    value = await manager.read("user:2", ConsistencyLevel.ALL)
    print(f"   Read user:2 (ALL): {value}")
    print()

    # 4. List Replicas
    print("4. LIST REPLICAS:")
    print("-" * 40)

    replicas = manager.list_replicas()

    for replica in replicas:
        print(f"   {replica.replica_id[:8]}...: {replica.role.value}, "
              f"state={replica.state.value}")
    print()

    # 5. Cluster Status
    print("5. CLUSTER STATUS:")
    print("-" * 40)

    status = manager.get_cluster_status()

    print(f"   Total replicas: {status['total_replicas']}")
    print(f"   Has quorum: {status['has_quorum']}")
    print(f"   Quorum size: {status['quorum_size']}")
    print(f"   Active replicas: {status['active_replicas']}")
    print()

    # 6. Read from Specific Replica
    print("6. READ FROM SPECIFIC REPLICA:")
    print("-" * 40)

    value = await manager.read_from_replica("user:1", secondary1.replica_id)
    print(f"   Read from secondary1: {value}")
    print()

    # 7. Get Changes (CDC)
    print("7. CHANGE DATA CAPTURE:")
    print("-" * 40)

    changes = manager.get_changes(primary.replica_id)

    for change in changes:
        print(f"   {change.operation.value}: {change.key} v{change.version}")
    print()

    # 8. Check Replication Lag
    print("8. REPLICATION LAG:")
    print("-" * 40)

    for replica in manager.get_secondaries():
        lag = manager.get_lag(replica.replica_id)
        print(f"   {replica.replica_id[:8]}...: {lag}ms")
    print()

    # 9. Sync Replica
    print("9. SYNC REPLICA:")
    print("-" * 40)

    success = await manager.sync_replica(secondary1.replica_id)
    print(f"   Sync secondary1: {success}")
    print()

    # 10. Quorum Operations
    print("10. QUORUM OPERATIONS:")
    print("-" * 40)

    result = await manager.quorum_write("config:1", {"setting": "value"})
    print(f"   Quorum write: success={result.success}")

    value = await manager.quorum_read("config:1")
    print(f"   Quorum read: {value}")
    print()

    # 11. Failover
    print("11. FAILOVER:")
    print("-" * 40)

    current_primary = manager.get_primary()
    print(f"   Current primary: {current_primary.replica_id[:8] if current_primary else 'None'}...")

    success = await manager.failover_to(secondary1.replica_id)
    print(f"   Failover to secondary1: {success}")

    new_primary = manager.get_primary()
    print(f"   New primary: {new_primary.replica_id[:8] if new_primary else 'None'}...")
    print()

    # 12. Conflict Detection
    print("12. CONFLICT DETECTION:")
    print("-" * 40)

    conflict = manager.detect_conflicts("user:1")

    if conflict:
        print(f"   Conflict detected: {conflict.conflict_id[:8]}...")
        print(f"   Events: {len(conflict.events)}")
    else:
        print("   No conflicts detected")
    print()

    # 13. Replication Stats
    print("13. REPLICATION STATS:")
    print("-" * 40)

    all_stats = manager.get_all_stats()

    for rid, stats in all_stats.items():
        print(f"   {rid[:8]}...: ops={stats.operations_replicated}")
    print()

    # 14. Vector Clock
    print("14. VECTOR CLOCK:")
    print("-" * 40)

    vc1 = VectorClock()
    vc1.increment("node1")
    vc1.increment("node1")
    vc1.increment("node2")

    vc2 = VectorClock()
    vc2.increment("node2")
    vc2.increment("node2")

    print(f"   VC1: {vc1.to_dict()}")
    print(f"   VC2: {vc2.to_dict()}")
    print(f"   Comparison: {vc1.compare(vc2)}")
    print()

    # 15. Has Quorum Check
    print("15. QUORUM CHECK:")
    print("-" * 40)

    print(f"   Required quorum: {manager.calculate_quorum()}")
    print(f"   Has quorum: {manager.has_quorum()}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Replication Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
