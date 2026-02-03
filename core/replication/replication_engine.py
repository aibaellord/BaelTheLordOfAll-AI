#!/usr/bin/env python3
"""
BAEL - Replication Engine
Data replication for agents.

Features:
- Synchronous replication
- Asynchronous replication
- Conflict resolution
- Replica management
- Consistency guarantees
"""

import asyncio
import hashlib
import json
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (
    Any, Callable, Coroutine, Dict, Generic, List, Optional, Set, Tuple, TypeVar
)


T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ReplicationMode(Enum):
    """Replication modes."""
    SYNC = "sync"
    ASYNC = "async"
    SEMI_SYNC = "semi_sync"


class ReplicaRole(Enum):
    """Replica roles."""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    ARBITER = "arbiter"


class ReplicaState(Enum):
    """Replica states."""
    ACTIVE = "active"
    SYNCING = "syncing"
    LAGGING = "lagging"
    OFFLINE = "offline"


class ConflictStrategy(Enum):
    """Conflict resolution strategies."""
    LAST_WRITE_WINS = "last_write_wins"
    FIRST_WRITE_WINS = "first_write_wins"
    HIGHEST_VERSION = "highest_version"
    CUSTOM = "custom"


class ConsistencyLevel(Enum):
    """Consistency levels."""
    ONE = "one"
    QUORUM = "quorum"
    ALL = "all"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class ReplicationEntry:
    """A replication log entry."""
    entry_id: str = ""
    key: str = ""
    value: Any = None
    version: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    source_replica: str = ""
    checksum: str = ""
    
    def __post_init__(self):
        if not self.entry_id:
            self.entry_id = str(uuid.uuid4())[:8]
        if not self.checksum and self.value is not None:
            self.checksum = hashlib.md5(
                json.dumps(self.value, default=str).encode()
            ).hexdigest()[:8]


@dataclass
class ReplicaConfig:
    """Replica configuration."""
    replica_id: str = ""
    name: str = ""
    endpoint: str = ""
    role: ReplicaRole = ReplicaRole.SECONDARY
    priority: int = 0
    
    def __post_init__(self):
        if not self.replica_id:
            self.replica_id = str(uuid.uuid4())[:8]


@dataclass
class ReplicationConfig:
    """Replication configuration."""
    mode: ReplicationMode = ReplicationMode.ASYNC
    consistency: ConsistencyLevel = ConsistencyLevel.QUORUM
    conflict_strategy: ConflictStrategy = ConflictStrategy.LAST_WRITE_WINS
    sync_interval: float = 1.0
    max_lag_entries: int = 100
    write_concern: int = 1


@dataclass
class ConflictInfo:
    """Conflict information."""
    key: str = ""
    local_entry: Optional[ReplicationEntry] = None
    remote_entry: Optional[ReplicationEntry] = None
    resolution: str = ""
    resolved_value: Any = None


@dataclass
class ReplicaStats:
    """Replica statistics."""
    entries_written: int = 0
    entries_replicated: int = 0
    conflicts_detected: int = 0
    conflicts_resolved: int = 0
    bytes_transferred: int = 0
    lag_entries: int = 0


@dataclass
class ReplicationStats:
    """Replication statistics."""
    total_replicas: int = 0
    active_replicas: int = 0
    entries_replicated: int = 0
    conflicts_resolved: int = 0
    last_sync: Optional[datetime] = None


# =============================================================================
# REPLICA
# =============================================================================

class Replica:
    """A data replica."""
    
    def __init__(self, config: ReplicaConfig):
        self._config = config
        
        self._data: Dict[str, Any] = {}
        self._versions: Dict[str, int] = {}
        self._log: deque = deque(maxlen=1000)
        
        self._state = ReplicaState.ACTIVE
        self._stats = ReplicaStats()
        
        self._last_applied_id: str = ""
    
    def write(
        self,
        key: str,
        value: Any,
        version: Optional[int] = None
    ) -> ReplicationEntry:
        """Write data to replica."""
        current_version = self._versions.get(key, 0)
        new_version = version if version is not None else current_version + 1
        
        self._data[key] = value
        self._versions[key] = new_version
        
        entry = ReplicationEntry(
            key=key,
            value=value,
            version=new_version,
            source_replica=self._config.replica_id
        )
        
        self._log.append(entry)
        self._last_applied_id = entry.entry_id
        self._stats.entries_written += 1
        
        return entry
    
    def read(self, key: str) -> Optional[Any]:
        """Read data from replica."""
        return self._data.get(key)
    
    def get_version(self, key: str) -> int:
        """Get version for key."""
        return self._versions.get(key, 0)
    
    def apply_entry(self, entry: ReplicationEntry) -> bool:
        """Apply replication entry."""
        current_version = self._versions.get(entry.key, 0)
        
        if entry.version > current_version:
            self._data[entry.key] = entry.value
            self._versions[entry.key] = entry.version
            self._last_applied_id = entry.entry_id
            self._stats.entries_replicated += 1
            return True
        
        return False
    
    def get_log_since(self, entry_id: str) -> List[ReplicationEntry]:
        """Get log entries since given ID."""
        entries = []
        found = False
        
        for entry in self._log:
            if found:
                entries.append(entry)
            elif entry.entry_id == entry_id:
                found = True
        
        if not entry_id:
            return list(self._log)
        
        return entries
    
    def get_all_data(self) -> Dict[str, Any]:
        """Get all data."""
        return dict(self._data)
    
    def get_all_versions(self) -> Dict[str, int]:
        """Get all versions."""
        return dict(self._versions)
    
    @property
    def replica_id(self) -> str:
        return self._config.replica_id
    
    @property
    def name(self) -> str:
        return self._config.name
    
    @property
    def role(self) -> ReplicaRole:
        return self._config.role
    
    @property
    def state(self) -> ReplicaState:
        return self._state
    
    @state.setter
    def state(self, value: ReplicaState) -> None:
        self._state = value
    
    @property
    def stats(self) -> ReplicaStats:
        return self._stats
    
    @property
    def last_applied_id(self) -> str:
        return self._last_applied_id


# =============================================================================
# CONFLICT RESOLVER
# =============================================================================

class ConflictResolver(ABC):
    """Abstract conflict resolver."""
    
    @abstractmethod
    def resolve(
        self,
        local: ReplicationEntry,
        remote: ReplicationEntry
    ) -> ReplicationEntry:
        """Resolve conflict."""
        pass


class LastWriteWinsResolver(ConflictResolver):
    """Last write wins resolver."""
    
    def resolve(
        self,
        local: ReplicationEntry,
        remote: ReplicationEntry
    ) -> ReplicationEntry:
        """Return entry with latest timestamp."""
        if remote.timestamp > local.timestamp:
            return remote
        return local


class FirstWriteWinsResolver(ConflictResolver):
    """First write wins resolver."""
    
    def resolve(
        self,
        local: ReplicationEntry,
        remote: ReplicationEntry
    ) -> ReplicationEntry:
        """Return entry with earliest timestamp."""
        if remote.timestamp < local.timestamp:
            return remote
        return local


class HighestVersionResolver(ConflictResolver):
    """Highest version wins resolver."""
    
    def resolve(
        self,
        local: ReplicationEntry,
        remote: ReplicationEntry
    ) -> ReplicationEntry:
        """Return entry with highest version."""
        if remote.version > local.version:
            return remote
        return local


class CustomResolver(ConflictResolver):
    """Custom conflict resolver."""
    
    def __init__(
        self,
        resolve_func: Callable[[ReplicationEntry, ReplicationEntry], ReplicationEntry]
    ):
        self._resolve_func = resolve_func
    
    def resolve(
        self,
        local: ReplicationEntry,
        remote: ReplicationEntry
    ) -> ReplicationEntry:
        """Run custom resolution."""
        return self._resolve_func(local, remote)


# =============================================================================
# REPLICATION GROUP
# =============================================================================

class ReplicationGroup:
    """Group of replicas."""
    
    def __init__(
        self,
        name: str,
        config: Optional[ReplicationConfig] = None
    ):
        self._name = name
        self._config = config or ReplicationConfig()
        
        self._replicas: Dict[str, Replica] = {}
        self._primary_id: Optional[str] = None
        
        self._resolver = self._create_resolver()
        self._conflicts: List[ConflictInfo] = []
        
        self._sync_task: Optional[asyncio.Task] = None
        self._stats = ReplicationStats()
    
    def _create_resolver(self) -> ConflictResolver:
        """Create conflict resolver."""
        if self._config.conflict_strategy == ConflictStrategy.LAST_WRITE_WINS:
            return LastWriteWinsResolver()
        elif self._config.conflict_strategy == ConflictStrategy.FIRST_WRITE_WINS:
            return FirstWriteWinsResolver()
        elif self._config.conflict_strategy == ConflictStrategy.HIGHEST_VERSION:
            return HighestVersionResolver()
        else:
            return LastWriteWinsResolver()
    
    def add_replica(
        self,
        name: str,
        role: ReplicaRole = ReplicaRole.SECONDARY,
        endpoint: str = "",
        priority: int = 0
    ) -> Replica:
        """Add a replica."""
        config = ReplicaConfig(
            name=name,
            role=role,
            endpoint=endpoint,
            priority=priority
        )
        
        replica = Replica(config)
        self._replicas[replica.replica_id] = replica
        
        if role == ReplicaRole.PRIMARY:
            self._primary_id = replica.replica_id
        
        self._stats.total_replicas = len(self._replicas)
        
        return replica
    
    def remove_replica(self, replica_id: str) -> bool:
        """Remove a replica."""
        if replica_id in self._replicas:
            del self._replicas[replica_id]
            
            if self._primary_id == replica_id:
                self._elect_primary()
            
            self._stats.total_replicas = len(self._replicas)
            return True
        
        return False
    
    def _elect_primary(self) -> Optional[str]:
        """Elect a new primary."""
        candidates = [
            r for r in self._replicas.values()
            if r.role != ReplicaRole.ARBITER
        ]
        
        if not candidates:
            self._primary_id = None
            return None
        
        candidates.sort(key=lambda r: -r._config.priority)
        
        new_primary = candidates[0]
        new_primary._config.role = ReplicaRole.PRIMARY
        self._primary_id = new_primary.replica_id
        
        return new_primary.replica_id
    
    def get_primary(self) -> Optional[Replica]:
        """Get primary replica."""
        if self._primary_id:
            return self._replicas.get(self._primary_id)
        return None
    
    def get_secondaries(self) -> List[Replica]:
        """Get secondary replicas."""
        return [
            r for r in self._replicas.values()
            if r.role == ReplicaRole.SECONDARY
        ]
    
    async def write(
        self,
        key: str,
        value: Any
    ) -> Tuple[bool, Optional[ReplicationEntry]]:
        """Write to primary and replicate."""
        primary = self.get_primary()
        
        if not primary:
            return False, None
        
        entry = primary.write(key, value)
        
        if self._config.mode == ReplicationMode.SYNC:
            success = await self._sync_replicate(entry)
            return success, entry
        
        elif self._config.mode == ReplicationMode.ASYNC:
            asyncio.create_task(self._async_replicate(entry))
            return True, entry
        
        elif self._config.mode == ReplicationMode.SEMI_SYNC:
            success = await self._semi_sync_replicate(entry)
            return success, entry
        
        return True, entry
    
    async def _sync_replicate(self, entry: ReplicationEntry) -> bool:
        """Synchronous replication."""
        secondaries = self.get_secondaries()
        
        success_count = 1
        
        for replica in secondaries:
            if replica.apply_entry(entry):
                success_count += 1
                self._stats.entries_replicated += 1
        
        required = self._get_required_acks()
        
        return success_count >= required
    
    async def _async_replicate(self, entry: ReplicationEntry) -> None:
        """Asynchronous replication."""
        secondaries = self.get_secondaries()
        
        for replica in secondaries:
            if replica.apply_entry(entry):
                self._stats.entries_replicated += 1
    
    async def _semi_sync_replicate(self, entry: ReplicationEntry) -> bool:
        """Semi-synchronous replication."""
        secondaries = self.get_secondaries()
        
        if not secondaries:
            return True
        
        replica = secondaries[0]
        
        if replica.apply_entry(entry):
            self._stats.entries_replicated += 1
            return True
        
        return False
    
    def _get_required_acks(self) -> int:
        """Get required acknowledgments."""
        total = len(self._replicas)
        
        if self._config.consistency == ConsistencyLevel.ONE:
            return 1
        elif self._config.consistency == ConsistencyLevel.QUORUM:
            return (total // 2) + 1
        elif self._config.consistency == ConsistencyLevel.ALL:
            return total
        
        return self._config.write_concern
    
    async def read(
        self,
        key: str,
        from_primary: bool = True
    ) -> Optional[Any]:
        """Read from replica."""
        if from_primary:
            primary = self.get_primary()
            if primary:
                return primary.read(key)
        else:
            for replica in self._replicas.values():
                value = replica.read(key)
                if value is not None:
                    return value
        
        return None
    
    async def sync_replica(self, replica_id: str) -> int:
        """Sync a replica from primary."""
        primary = self.get_primary()
        replica = self._replicas.get(replica_id)
        
        if not primary or not replica:
            return 0
        
        entries = primary.get_log_since(replica.last_applied_id)
        
        synced = 0
        
        for entry in entries:
            local_version = replica.get_version(entry.key)
            
            if entry.version > local_version:
                replica.apply_entry(entry)
                synced += 1
            elif entry.version == local_version:
                local_value = replica.read(entry.key)
                
                if local_value != entry.value:
                    local_entry = ReplicationEntry(
                        key=entry.key,
                        value=local_value,
                        version=local_version,
                        source_replica=replica_id
                    )
                    
                    resolved = self._resolver.resolve(local_entry, entry)
                    
                    conflict = ConflictInfo(
                        key=entry.key,
                        local_entry=local_entry,
                        remote_entry=entry,
                        resolution="resolved",
                        resolved_value=resolved.value
                    )
                    
                    self._conflicts.append(conflict)
                    self._stats.conflicts_resolved += 1
                    
                    replica.apply_entry(resolved)
                    synced += 1
        
        self._stats.entries_replicated += synced
        
        return synced
    
    async def sync_all(self) -> Dict[str, int]:
        """Sync all secondaries."""
        results = {}
        
        for replica in self.get_secondaries():
            synced = await self.sync_replica(replica.replica_id)
            results[replica.replica_id] = synced
        
        self._stats.last_sync = datetime.now()
        
        return results
    
    def start_sync(self) -> None:
        """Start background sync."""
        async def sync_loop():
            while True:
                await asyncio.sleep(self._config.sync_interval)
                await self.sync_all()
        
        self._sync_task = asyncio.create_task(sync_loop())
    
    def stop_sync(self) -> None:
        """Stop background sync."""
        if self._sync_task:
            self._sync_task.cancel()
            self._sync_task = None
    
    def get_conflicts(self) -> List[ConflictInfo]:
        """Get conflict history."""
        return list(self._conflicts)
    
    def get_replica_states(self) -> Dict[str, ReplicaState]:
        """Get replica states."""
        return {
            r.replica_id: r.state
            for r in self._replicas.values()
        }
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def stats(self) -> ReplicationStats:
        self._stats.active_replicas = sum(
            1 for r in self._replicas.values()
            if r.state == ReplicaState.ACTIVE
        )
        return self._stats


# =============================================================================
# REPLICATION ENGINE
# =============================================================================

class ReplicationEngine:
    """
    Replication Engine for BAEL.
    
    Data replication for agents.
    """
    
    def __init__(self, default_config: Optional[ReplicationConfig] = None):
        self._default_config = default_config or ReplicationConfig()
        
        self._groups: Dict[str, ReplicationGroup] = {}
    
    # ----- Group Management -----
    
    def create_group(
        self,
        name: str,
        config: Optional[ReplicationConfig] = None
    ) -> ReplicationGroup:
        """Create a replication group."""
        config = config or self._default_config
        group = ReplicationGroup(name, config)
        self._groups[name] = group
        return group
    
    def get_group(self, name: str) -> Optional[ReplicationGroup]:
        """Get a replication group."""
        return self._groups.get(name)
    
    def remove_group(self, name: str) -> bool:
        """Remove a replication group."""
        group = self._groups.pop(name, None)
        
        if group:
            group.stop_sync()
            return True
        
        return False
    
    def list_groups(self) -> List[str]:
        """List group names."""
        return list(self._groups.keys())
    
    # ----- Replica Management -----
    
    def add_replica(
        self,
        group_name: str,
        name: str,
        role: ReplicaRole = ReplicaRole.SECONDARY,
        endpoint: str = "",
        priority: int = 0
    ) -> Optional[Replica]:
        """Add replica to group."""
        group = self._groups.get(group_name)
        
        if group:
            return group.add_replica(name, role, endpoint, priority)
        
        return None
    
    def remove_replica(self, group_name: str, replica_id: str) -> bool:
        """Remove replica from group."""
        group = self._groups.get(group_name)
        
        if group:
            return group.remove_replica(replica_id)
        
        return False
    
    # ----- Data Operations -----
    
    async def write(
        self,
        group_name: str,
        key: str,
        value: Any
    ) -> Tuple[bool, Optional[ReplicationEntry]]:
        """Write to group."""
        group = self._groups.get(group_name)
        
        if group:
            return await group.write(key, value)
        
        return False, None
    
    async def read(
        self,
        group_name: str,
        key: str,
        from_primary: bool = True
    ) -> Optional[Any]:
        """Read from group."""
        group = self._groups.get(group_name)
        
        if group:
            return await group.read(key, from_primary)
        
        return None
    
    # ----- Sync Operations -----
    
    async def sync_replica(
        self,
        group_name: str,
        replica_id: str
    ) -> int:
        """Sync a replica."""
        group = self._groups.get(group_name)
        
        if group:
            return await group.sync_replica(replica_id)
        
        return 0
    
    async def sync_group(self, group_name: str) -> Dict[str, int]:
        """Sync all replicas in group."""
        group = self._groups.get(group_name)
        
        if group:
            return await group.sync_all()
        
        return {}
    
    def start_sync(self, group_name: str) -> bool:
        """Start background sync."""
        group = self._groups.get(group_name)
        
        if group:
            group.start_sync()
            return True
        
        return False
    
    def stop_sync(self, group_name: str) -> bool:
        """Stop background sync."""
        group = self._groups.get(group_name)
        
        if group:
            group.stop_sync()
            return True
        
        return False
    
    # ----- Status -----
    
    def get_primary(self, group_name: str) -> Optional[Replica]:
        """Get primary for group."""
        group = self._groups.get(group_name)
        
        if group:
            return group.get_primary()
        
        return None
    
    def get_secondaries(self, group_name: str) -> List[Replica]:
        """Get secondaries for group."""
        group = self._groups.get(group_name)
        
        if group:
            return group.get_secondaries()
        
        return []
    
    def get_replica_states(self, group_name: str) -> Dict[str, ReplicaState]:
        """Get replica states."""
        group = self._groups.get(group_name)
        
        if group:
            return group.get_replica_states()
        
        return {}
    
    def get_conflicts(self, group_name: str) -> List[ConflictInfo]:
        """Get conflicts for group."""
        group = self._groups.get(group_name)
        
        if group:
            return group.get_conflicts()
        
        return []
    
    def get_stats(self, group_name: str) -> Optional[ReplicationStats]:
        """Get group stats."""
        group = self._groups.get(group_name)
        
        if group:
            return group.stats
        
        return None
    
    # ----- Engine Stats -----
    
    def stats(self) -> Dict[str, Any]:
        """Get engine stats."""
        total_replicas = 0
        total_entries = 0
        
        for group in self._groups.values():
            total_replicas += group.stats.total_replicas
            total_entries += group.stats.entries_replicated
        
        return {
            "groups": len(self._groups),
            "total_replicas": total_replicas,
            "total_entries_replicated": total_entries
        }
    
    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        group_info = {}
        
        for name, group in self._groups.items():
            primary = group.get_primary()
            
            group_info[name] = {
                "primary": primary.name if primary else None,
                "replica_count": group.stats.total_replicas,
                "entries_replicated": group.stats.entries_replicated
            }
        
        return {"groups": group_info}


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Replication Engine."""
    print("=" * 70)
    print("BAEL - REPLICATION ENGINE DEMO")
    print("Data Replication for Agents")
    print("=" * 70)
    print()
    
    engine = ReplicationEngine()
    
    # 1. Create Replication Group
    print("1. CREATE REPLICATION GROUP:")
    print("-" * 40)
    
    group = engine.create_group("user-data", ReplicationConfig(
        mode=ReplicationMode.SYNC,
        consistency=ConsistencyLevel.QUORUM,
        conflict_strategy=ConflictStrategy.LAST_WRITE_WINS
    ))
    
    print(f"   Created group: {group.name}")
    print(f"   Mode: {group._config.mode.value}")
    print(f"   Consistency: {group._config.consistency.value}")
    print()
    
    # 2. Add Replicas
    print("2. ADD REPLICAS:")
    print("-" * 40)
    
    primary = engine.add_replica(
        "user-data",
        name="primary",
        role=ReplicaRole.PRIMARY,
        priority=10
    )
    
    secondary1 = engine.add_replica(
        "user-data",
        name="secondary-1",
        role=ReplicaRole.SECONDARY,
        priority=5
    )
    
    secondary2 = engine.add_replica(
        "user-data",
        name="secondary-2",
        role=ReplicaRole.SECONDARY,
        priority=3
    )
    
    print(f"   Primary: {primary.name}")
    print(f"   Secondary 1: {secondary1.name}")
    print(f"   Secondary 2: {secondary2.name}")
    print()
    
    # 3. Write Data
    print("3. WRITE DATA:")
    print("-" * 40)
    
    success, entry = await engine.write("user-data", "user:1001", {"name": "Alice", "age": 30})
    print(f"   Write success: {success}")
    print(f"   Entry ID: {entry.entry_id}")
    print(f"   Version: {entry.version}")
    
    await engine.write("user-data", "user:1002", {"name": "Bob", "age": 25})
    await engine.write("user-data", "user:1003", {"name": "Charlie", "age": 35})
    
    print(f"   Written 3 users")
    print()
    
    # 4. Read Data
    print("4. READ DATA:")
    print("-" * 40)
    
    user1 = await engine.read("user-data", "user:1001")
    print(f"   User 1001: {user1}")
    
    user2 = await engine.read("user-data", "user:1002")
    print(f"   User 1002: {user2}")
    print()
    
    # 5. Check Replica Data
    print("5. CHECK REPLICA DATA:")
    print("-" * 40)
    
    primary_replica = engine.get_primary("user-data")
    print(f"   Primary data: {primary_replica.get_all_data()}")
    
    secondaries = engine.get_secondaries("user-data")
    for sec in secondaries:
        print(f"   {sec.name} data: {sec.get_all_data()}")
    print()
    
    # 6. Check Replica States
    print("6. CHECK REPLICA STATES:")
    print("-" * 40)
    
    states = engine.get_replica_states("user-data")
    for replica_id, state in states.items():
        print(f"   {replica_id[:8]}: {state.value}")
    print()
    
    # 7. Sync Replicas
    print("7. SYNC REPLICAS:")
    print("-" * 40)
    
    sync_results = await engine.sync_group("user-data")
    for replica_id, count in sync_results.items():
        print(f"   {replica_id[:8]}: {count} entries synced")
    print()
    
    # 8. Update Data
    print("8. UPDATE DATA:")
    print("-" * 40)
    
    await engine.write("user-data", "user:1001", {"name": "Alice", "age": 31})
    print(f"   Updated user:1001 age to 31")
    
    user1_updated = await engine.read("user-data", "user:1001")
    print(f"   Read: {user1_updated}")
    print()
    
    # 9. Check Versions
    print("9. CHECK VERSIONS:")
    print("-" * 40)
    
    versions = primary_replica.get_all_versions()
    for key, version in versions.items():
        print(f"   {key}: v{version}")
    print()
    
    # 10. Group Statistics
    print("10. GROUP STATISTICS:")
    print("-" * 40)
    
    stats = engine.get_stats("user-data")
    print(f"   Total replicas: {stats.total_replicas}")
    print(f"   Entries replicated: {stats.entries_replicated}")
    print(f"   Conflicts resolved: {stats.conflicts_resolved}")
    print()
    
    # 11. Create Async Group
    print("11. CREATE ASYNC GROUP:")
    print("-" * 40)
    
    async_group = engine.create_group("session-data", ReplicationConfig(
        mode=ReplicationMode.ASYNC,
        consistency=ConsistencyLevel.ONE
    ))
    
    engine.add_replica("session-data", "primary", ReplicaRole.PRIMARY)
    engine.add_replica("session-data", "replica-1", ReplicaRole.SECONDARY)
    
    print(f"   Created async group: {async_group.name}")
    
    await engine.write("session-data", "session:abc", {"user": "Alice", "active": True})
    
    print(f"   Written session data")
    print()
    
    # 12. List Groups
    print("12. LIST GROUPS:")
    print("-" * 40)
    
    groups = engine.list_groups()
    for g in groups:
        print(f"   - {g}")
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
    for name, info in summary["groups"].items():
        print(f"   {name}:")
        print(f"      Primary: {info['primary']}")
        print(f"      Replicas: {info['replica_count']}")
    print()
    
    print("=" * 70)
    print("DEMO COMPLETE - Replication Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
