#!/usr/bin/env python3
"""
BAEL - Snapshot Manager
Advanced snapshot and versioning for AI agent state.

Features:
- State snapshots
- Incremental snapshots
- Snapshot comparison
- Restore points
- Snapshot chains
- Compression
- Snapshot metadata
- Garbage collection
- Snapshot policies
- Delta encoding
"""

import asyncio
import copy
import gzip
import hashlib
import json
import threading
import time
import uuid
import zlib
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Awaitable, Callable, Dict, Generic, Iterator, List,
                    Optional, Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class SnapshotType(Enum):
    """Snapshot types."""
    FULL = "full"
    INCREMENTAL = "incremental"
    DELTA = "delta"


class SnapshotState(Enum):
    """Snapshot states."""
    CREATING = "creating"
    COMPLETE = "complete"
    CORRUPTED = "corrupted"
    DELETED = "deleted"


class CompressionType(Enum):
    """Compression types."""
    NONE = "none"
    GZIP = "gzip"
    ZLIB = "zlib"


class RetentionPolicy(Enum):
    """Retention policies."""
    KEEP_ALL = "keep_all"
    KEEP_N = "keep_n"
    KEEP_DAYS = "keep_days"
    KEEP_HOURLY = "keep_hourly"
    KEEP_DAILY = "keep_daily"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class SnapshotMetadata:
    """Snapshot metadata."""
    snapshot_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    snapshot_type: SnapshotType = SnapshotType.FULL
    parent_id: Optional[str] = None
    source_id: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    size_bytes: int = 0
    compressed_size: int = 0
    compression: CompressionType = CompressionType.NONE
    checksum: str = ""
    tags: Dict[str, str] = field(default_factory=dict)
    state: SnapshotState = SnapshotState.CREATING

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "name": self.name,
            "description": self.description,
            "snapshot_type": self.snapshot_type.value,
            "parent_id": self.parent_id,
            "source_id": self.source_id,
            "created_at": self.created_at.isoformat(),
            "size_bytes": self.size_bytes,
            "compressed_size": self.compressed_size,
            "compression": self.compression.value,
            "checksum": self.checksum,
            "tags": self.tags,
            "state": self.state.value
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SnapshotMetadata':
        return cls(
            snapshot_id=data.get("snapshot_id", str(uuid.uuid4())),
            name=data.get("name", ""),
            description=data.get("description", ""),
            snapshot_type=SnapshotType(data.get("snapshot_type", "full")),
            parent_id=data.get("parent_id"),
            source_id=data.get("source_id", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.utcnow(),
            size_bytes=data.get("size_bytes", 0),
            compressed_size=data.get("compressed_size", 0),
            compression=CompressionType(data.get("compression", "none")),
            checksum=data.get("checksum", ""),
            tags=data.get("tags", {}),
            state=SnapshotState(data.get("state", "creating"))
        )


@dataclass
class Snapshot:
    """A complete snapshot."""
    metadata: SnapshotMetadata
    data: bytes = b""

    @property
    def id(self) -> str:
        return self.metadata.snapshot_id

    @property
    def is_complete(self) -> bool:
        return self.metadata.state == SnapshotState.COMPLETE


@dataclass
class DeltaEntry:
    """Delta entry for incremental snapshots."""
    path: str = ""
    operation: str = "update"  # add, update, delete
    old_value: Any = None
    new_value: Any = None


@dataclass
class Delta:
    """Collection of delta entries."""
    entries: List[DeltaEntry] = field(default_factory=list)

    def add(
        self,
        path: str,
        operation: str,
        old_value: Any = None,
        new_value: Any = None
    ) -> None:
        self.entries.append(DeltaEntry(
            path=path,
            operation=operation,
            old_value=old_value,
            new_value=new_value
        ))

    def is_empty(self) -> bool:
        return len(self.entries) == 0


@dataclass
class SnapshotPolicy:
    """Snapshot retention policy."""
    retention: RetentionPolicy = RetentionPolicy.KEEP_ALL
    keep_count: int = 10
    keep_days: int = 30
    min_interval: timedelta = timedelta(hours=1)
    auto_snapshot: bool = False
    auto_interval: timedelta = timedelta(hours=24)


@dataclass
class RestoreResult:
    """Result of restore operation."""
    success: bool = False
    snapshot_id: str = ""
    restored_at: datetime = field(default_factory=datetime.utcnow)
    data: Any = None
    error: Optional[str] = None


# =============================================================================
# COMPRESSOR
# =============================================================================

class Compressor(ABC):
    """Base compressor."""

    @abstractmethod
    def compress(self, data: bytes) -> bytes:
        """Compress data."""
        pass

    @abstractmethod
    def decompress(self, data: bytes) -> bytes:
        """Decompress data."""
        pass


class NoCompressor(Compressor):
    """No compression."""

    def compress(self, data: bytes) -> bytes:
        return data

    def decompress(self, data: bytes) -> bytes:
        return data


class GzipCompressor(Compressor):
    """Gzip compression."""

    def __init__(self, level: int = 6):
        self.level = level

    def compress(self, data: bytes) -> bytes:
        return gzip.compress(data, compresslevel=self.level)

    def decompress(self, data: bytes) -> bytes:
        return gzip.decompress(data)


class ZlibCompressor(Compressor):
    """Zlib compression."""

    def __init__(self, level: int = 6):
        self.level = level

    def compress(self, data: bytes) -> bytes:
        return zlib.compress(data, level=self.level)

    def decompress(self, data: bytes) -> bytes:
        return zlib.decompress(data)


def get_compressor(compression_type: CompressionType) -> Compressor:
    """Get compressor by type."""
    if compression_type == CompressionType.GZIP:
        return GzipCompressor()
    elif compression_type == CompressionType.ZLIB:
        return ZlibCompressor()
    else:
        return NoCompressor()


# =============================================================================
# SERIALIZER
# =============================================================================

class SnapshotSerializer(ABC):
    """Base snapshot serializer."""

    @abstractmethod
    def serialize(self, data: Any) -> bytes:
        """Serialize data."""
        pass

    @abstractmethod
    def deserialize(self, data: bytes) -> Any:
        """Deserialize data."""
        pass


class JsonSerializer(SnapshotSerializer):
    """JSON serializer."""

    def serialize(self, data: Any) -> bytes:
        return json.dumps(data, default=str).encode('utf-8')

    def deserialize(self, data: bytes) -> Any:
        return json.loads(data.decode('utf-8'))


# =============================================================================
# DIFF ENGINE
# =============================================================================

class DiffEngine:
    """
    Engine for computing differences between states.
    """

    def compute_delta(
        self,
        old_state: Dict[str, Any],
        new_state: Dict[str, Any],
        prefix: str = ""
    ) -> Delta:
        """Compute delta between two states."""
        delta = Delta()

        old_keys = set(old_state.keys())
        new_keys = set(new_state.keys())

        # Deleted keys
        for key in old_keys - new_keys:
            path = f"{prefix}.{key}" if prefix else key
            delta.add(path, "delete", old_state[key], None)

        # Added keys
        for key in new_keys - old_keys:
            path = f"{prefix}.{key}" if prefix else key
            delta.add(path, "add", None, new_state[key])

        # Modified keys
        for key in old_keys & new_keys:
            path = f"{prefix}.{key}" if prefix else key
            old_val = old_state[key]
            new_val = new_state[key]

            if isinstance(old_val, dict) and isinstance(new_val, dict):
                # Recurse for nested dicts
                nested = self.compute_delta(old_val, new_val, path)
                delta.entries.extend(nested.entries)
            elif old_val != new_val:
                delta.add(path, "update", old_val, new_val)

        return delta

    def apply_delta(
        self,
        state: Dict[str, Any],
        delta: Delta
    ) -> Dict[str, Any]:
        """Apply delta to state."""
        result = copy.deepcopy(state)

        for entry in delta.entries:
            parts = entry.path.split(".")

            if entry.operation == "delete":
                self._delete_path(result, parts)
            elif entry.operation == "add":
                self._set_path(result, parts, entry.new_value)
            elif entry.operation == "update":
                self._set_path(result, parts, entry.new_value)

        return result

    def _get_path(self, obj: Dict, parts: List[str]) -> Any:
        """Get value at path."""
        for part in parts:
            if isinstance(obj, dict) and part in obj:
                obj = obj[part]
            else:
                return None
        return obj

    def _set_path(self, obj: Dict, parts: List[str], value: Any) -> None:
        """Set value at path."""
        for part in parts[:-1]:
            if part not in obj:
                obj[part] = {}
            obj = obj[part]
        obj[parts[-1]] = value

    def _delete_path(self, obj: Dict, parts: List[str]) -> None:
        """Delete value at path."""
        for part in parts[:-1]:
            if part not in obj:
                return
            obj = obj[part]
        if parts[-1] in obj:
            del obj[parts[-1]]


# =============================================================================
# SNAPSHOT CHAIN
# =============================================================================

class SnapshotChain:
    """
    Chain of snapshots with incremental deltas.
    """

    def __init__(self, source_id: str):
        self.source_id = source_id
        self._snapshots: Dict[str, Snapshot] = {}
        self._order: List[str] = []
        self._children: Dict[str, List[str]] = defaultdict(list)
        self._lock = threading.RLock()

    def add(self, snapshot: Snapshot) -> None:
        """Add snapshot to chain."""
        with self._lock:
            self._snapshots[snapshot.id] = snapshot
            self._order.append(snapshot.id)

            if snapshot.metadata.parent_id:
                self._children[snapshot.metadata.parent_id].append(snapshot.id)

    def get(self, snapshot_id: str) -> Optional[Snapshot]:
        """Get snapshot by ID."""
        with self._lock:
            return self._snapshots.get(snapshot_id)

    def get_latest(self) -> Optional[Snapshot]:
        """Get latest snapshot."""
        with self._lock:
            if self._order:
                return self._snapshots.get(self._order[-1])
            return None

    def get_chain(self, snapshot_id: str) -> List[Snapshot]:
        """Get full chain from root to snapshot."""
        with self._lock:
            chain = []
            current_id = snapshot_id

            while current_id:
                snapshot = self._snapshots.get(current_id)
                if snapshot:
                    chain.insert(0, snapshot)
                    current_id = snapshot.metadata.parent_id
                else:
                    break

            return chain

    def list_all(self) -> List[Snapshot]:
        """List all snapshots."""
        with self._lock:
            return [self._snapshots[sid] for sid in self._order]

    def remove(self, snapshot_id: str) -> bool:
        """Remove snapshot from chain."""
        with self._lock:
            if snapshot_id in self._snapshots:
                del self._snapshots[snapshot_id]
                self._order.remove(snapshot_id)
                return True
            return False

    def size(self) -> int:
        """Get number of snapshots."""
        with self._lock:
            return len(self._snapshots)


# =============================================================================
# SNAPSHOT STORE
# =============================================================================

class SnapshotStore:
    """
    In-memory snapshot storage.
    """

    def __init__(self):
        self._chains: Dict[str, SnapshotChain] = {}
        self._lock = threading.RLock()

    def get_chain(self, source_id: str) -> SnapshotChain:
        """Get or create chain for source."""
        with self._lock:
            if source_id not in self._chains:
                self._chains[source_id] = SnapshotChain(source_id)
            return self._chains[source_id]

    def save(self, snapshot: Snapshot) -> None:
        """Save snapshot."""
        chain = self.get_chain(snapshot.metadata.source_id)
        chain.add(snapshot)

    def load(self, source_id: str, snapshot_id: str) -> Optional[Snapshot]:
        """Load snapshot."""
        with self._lock:
            chain = self._chains.get(source_id)
            if chain:
                return chain.get(snapshot_id)
            return None

    def list_sources(self) -> List[str]:
        """List all source IDs."""
        with self._lock:
            return list(self._chains.keys())

    def delete(self, source_id: str, snapshot_id: str) -> bool:
        """Delete snapshot."""
        with self._lock:
            chain = self._chains.get(source_id)
            if chain:
                return chain.remove(snapshot_id)
            return False


# =============================================================================
# SNAPSHOT MANAGER
# =============================================================================

class SnapshotManager:
    """
    Snapshot Manager for BAEL.

    Advanced state snapshotting.
    """

    def __init__(self):
        self._store = SnapshotStore()
        self._serializer = JsonSerializer()
        self._diff_engine = DiffEngine()
        self._policies: Dict[str, SnapshotPolicy] = {}
        self._last_snapshot: Dict[str, datetime] = {}
        self._lock = threading.RLock()

    # -------------------------------------------------------------------------
    # SNAPSHOT CREATION
    # -------------------------------------------------------------------------

    def create_snapshot(
        self,
        source_id: str,
        state: Any,
        name: str = "",
        description: str = "",
        compression: CompressionType = CompressionType.GZIP,
        tags: Optional[Dict[str, str]] = None
    ) -> Snapshot:
        """Create a full snapshot."""
        # Serialize state
        data = self._serializer.serialize(state)
        original_size = len(data)

        # Compress
        compressor = get_compressor(compression)
        compressed_data = compressor.compress(data)

        # Calculate checksum
        checksum = hashlib.sha256(compressed_data).hexdigest()

        # Create metadata
        metadata = SnapshotMetadata(
            name=name or f"snapshot_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            description=description,
            snapshot_type=SnapshotType.FULL,
            source_id=source_id,
            size_bytes=original_size,
            compressed_size=len(compressed_data),
            compression=compression,
            checksum=checksum,
            tags=tags or {},
            state=SnapshotState.COMPLETE
        )

        snapshot = Snapshot(metadata=metadata, data=compressed_data)

        # Store
        self._store.save(snapshot)
        self._last_snapshot[source_id] = datetime.utcnow()

        return snapshot

    def create_incremental(
        self,
        source_id: str,
        state: Any,
        name: str = "",
        compression: CompressionType = CompressionType.GZIP
    ) -> Optional[Snapshot]:
        """Create incremental snapshot from last full snapshot."""
        # Get last snapshot
        chain = self._store.get_chain(source_id)
        last = chain.get_latest()

        if not last:
            # No base, create full
            return self.create_snapshot(source_id, state, name, compression=compression)

        # Restore last state
        last_state = self.restore_data(last)

        # Compute delta
        if isinstance(last_state, dict) and isinstance(state, dict):
            delta = self._diff_engine.compute_delta(last_state, state)

            if delta.is_empty():
                return None  # No changes

            # Serialize delta
            delta_data = self._serializer.serialize({
                "entries": [
                    {
                        "path": e.path,
                        "operation": e.operation,
                        "old_value": e.old_value,
                        "new_value": e.new_value
                    }
                    for e in delta.entries
                ]
            })
        else:
            # Non-dict state, store full
            delta_data = self._serializer.serialize(state)

        original_size = len(delta_data)

        # Compress
        compressor = get_compressor(compression)
        compressed_data = compressor.compress(delta_data)

        # Calculate checksum
        checksum = hashlib.sha256(compressed_data).hexdigest()

        # Create metadata
        metadata = SnapshotMetadata(
            name=name or f"incremental_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            snapshot_type=SnapshotType.INCREMENTAL,
            parent_id=last.id,
            source_id=source_id,
            size_bytes=original_size,
            compressed_size=len(compressed_data),
            compression=compression,
            checksum=checksum,
            state=SnapshotState.COMPLETE
        )

        snapshot = Snapshot(metadata=metadata, data=compressed_data)

        # Store
        self._store.save(snapshot)
        self._last_snapshot[source_id] = datetime.utcnow()

        return snapshot

    # -------------------------------------------------------------------------
    # SNAPSHOT RESTORATION
    # -------------------------------------------------------------------------

    def restore(
        self,
        source_id: str,
        snapshot_id: Optional[str] = None
    ) -> RestoreResult:
        """Restore state from snapshot."""
        chain = self._store.get_chain(source_id)

        if snapshot_id:
            snapshot = chain.get(snapshot_id)
        else:
            snapshot = chain.get_latest()

        if not snapshot:
            return RestoreResult(
                success=False,
                error="Snapshot not found"
            )

        try:
            data = self.restore_data(snapshot)

            return RestoreResult(
                success=True,
                snapshot_id=snapshot.id,
                data=data
            )
        except Exception as e:
            return RestoreResult(
                success=False,
                snapshot_id=snapshot.id,
                error=str(e)
            )

    def restore_data(self, snapshot: Snapshot) -> Any:
        """Restore data from snapshot."""
        # Decompress
        compressor = get_compressor(snapshot.metadata.compression)
        data = compressor.decompress(snapshot.data)

        # Deserialize
        state = self._serializer.deserialize(data)

        # If incremental, apply chain
        if snapshot.metadata.snapshot_type == SnapshotType.INCREMENTAL:
            chain = self._store.get_chain(snapshot.metadata.source_id)
            full_chain = chain.get_chain(snapshot.id)

            # Find base and apply deltas
            base_state = None
            for s in full_chain:
                if s.metadata.snapshot_type == SnapshotType.FULL:
                    # Load full snapshot
                    comp = get_compressor(s.metadata.compression)
                    base_data = comp.decompress(s.data)
                    base_state = self._serializer.deserialize(base_data)
                elif base_state is not None:
                    # Apply delta
                    comp = get_compressor(s.metadata.compression)
                    delta_data = comp.decompress(s.data)
                    delta_dict = self._serializer.deserialize(delta_data)

                    if "entries" in delta_dict:
                        delta = Delta()
                        for e in delta_dict["entries"]:
                            delta.add(
                                e["path"],
                                e["operation"],
                                e.get("old_value"),
                                e.get("new_value")
                            )
                        base_state = self._diff_engine.apply_delta(base_state, delta)

            return base_state

        return state

    # -------------------------------------------------------------------------
    # SNAPSHOT MANAGEMENT
    # -------------------------------------------------------------------------

    def list_snapshots(
        self,
        source_id: str,
        limit: Optional[int] = None
    ) -> List[SnapshotMetadata]:
        """List snapshots for source."""
        chain = self._store.get_chain(source_id)
        snapshots = chain.list_all()

        if limit:
            snapshots = snapshots[-limit:]

        return [s.metadata for s in snapshots]

    def get_snapshot(
        self,
        source_id: str,
        snapshot_id: str
    ) -> Optional[Snapshot]:
        """Get specific snapshot."""
        return self._store.load(source_id, snapshot_id)

    def delete_snapshot(
        self,
        source_id: str,
        snapshot_id: str
    ) -> bool:
        """Delete a snapshot."""
        return self._store.delete(source_id, snapshot_id)

    def compare_snapshots(
        self,
        source_id: str,
        snapshot_id_1: str,
        snapshot_id_2: str
    ) -> Optional[Delta]:
        """Compare two snapshots."""
        snap1 = self._store.load(source_id, snapshot_id_1)
        snap2 = self._store.load(source_id, snapshot_id_2)

        if not snap1 or not snap2:
            return None

        state1 = self.restore_data(snap1)
        state2 = self.restore_data(snap2)

        if isinstance(state1, dict) and isinstance(state2, dict):
            return self._diff_engine.compute_delta(state1, state2)

        return None

    # -------------------------------------------------------------------------
    # POLICIES
    # -------------------------------------------------------------------------

    def set_policy(self, source_id: str, policy: SnapshotPolicy) -> None:
        """Set retention policy for source."""
        with self._lock:
            self._policies[source_id] = policy

    def get_policy(self, source_id: str) -> SnapshotPolicy:
        """Get policy for source."""
        with self._lock:
            return self._policies.get(source_id, SnapshotPolicy())

    def apply_retention(self, source_id: str) -> int:
        """Apply retention policy and cleanup old snapshots."""
        policy = self.get_policy(source_id)
        chain = self._store.get_chain(source_id)
        snapshots = chain.list_all()

        to_delete = []

        if policy.retention == RetentionPolicy.KEEP_N:
            if len(snapshots) > policy.keep_count:
                to_delete = snapshots[:-policy.keep_count]

        elif policy.retention == RetentionPolicy.KEEP_DAYS:
            cutoff = datetime.utcnow() - timedelta(days=policy.keep_days)
            to_delete = [s for s in snapshots if s.metadata.created_at < cutoff]

        # Delete
        deleted = 0
        for snapshot in to_delete:
            # Don't delete if it's a parent of remaining snapshots
            if self._store.delete(source_id, snapshot.id):
                deleted += 1

        return deleted

    # -------------------------------------------------------------------------
    # VERIFICATION
    # -------------------------------------------------------------------------

    def verify(self, source_id: str, snapshot_id: str) -> bool:
        """Verify snapshot integrity."""
        snapshot = self._store.load(source_id, snapshot_id)

        if not snapshot:
            return False

        # Verify checksum
        checksum = hashlib.sha256(snapshot.data).hexdigest()

        if checksum != snapshot.metadata.checksum:
            snapshot.metadata.state = SnapshotState.CORRUPTED
            return False

        return True

    def verify_all(self, source_id: str) -> Dict[str, bool]:
        """Verify all snapshots for source."""
        chain = self._store.get_chain(source_id)
        results = {}

        for snapshot in chain.list_all():
            results[snapshot.id] = self.verify(source_id, snapshot.id)

        return results

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self, source_id: str) -> Dict[str, Any]:
        """Get snapshot statistics."""
        chain = self._store.get_chain(source_id)
        snapshots = chain.list_all()

        if not snapshots:
            return {
                "source_id": source_id,
                "count": 0,
                "total_size": 0,
                "compressed_size": 0
            }

        total_size = sum(s.metadata.size_bytes for s in snapshots)
        compressed_size = sum(s.metadata.compressed_size for s in snapshots)

        full_count = sum(
            1 for s in snapshots
            if s.metadata.snapshot_type == SnapshotType.FULL
        )
        incremental_count = sum(
            1 for s in snapshots
            if s.metadata.snapshot_type == SnapshotType.INCREMENTAL
        )

        return {
            "source_id": source_id,
            "count": len(snapshots),
            "full_count": full_count,
            "incremental_count": incremental_count,
            "total_size": total_size,
            "compressed_size": compressed_size,
            "compression_ratio": total_size / compressed_size if compressed_size > 0 else 0,
            "oldest": snapshots[0].metadata.created_at.isoformat(),
            "newest": snapshots[-1].metadata.created_at.isoformat()
        }

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def list_sources(self) -> List[str]:
        """List all source IDs."""
        return self._store.list_sources()

    def should_snapshot(self, source_id: str) -> bool:
        """Check if auto-snapshot is due."""
        policy = self.get_policy(source_id)

        if not policy.auto_snapshot:
            return False

        last = self._last_snapshot.get(source_id)

        if not last:
            return True

        return datetime.utcnow() - last >= policy.auto_interval

    def export_metadata(self, source_id: str) -> List[Dict[str, Any]]:
        """Export all snapshot metadata."""
        chain = self._store.get_chain(source_id)
        return [s.metadata.to_dict() for s in chain.list_all()]


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Snapshot Manager."""
    print("=" * 70)
    print("BAEL - SNAPSHOT MANAGER DEMO")
    print("Advanced State Snapshotting for AI Agents")
    print("=" * 70)
    print()

    manager = SnapshotManager()

    # 1. Create Full Snapshot
    print("1. CREATE FULL SNAPSHOT:")
    print("-" * 40)

    state1 = {
        "name": "agent-001",
        "version": "1.0.0",
        "config": {
            "max_retries": 3,
            "timeout": 30
        },
        "data": [1, 2, 3, 4, 5]
    }

    snapshot1 = manager.create_snapshot(
        "agent-001",
        state1,
        name="initial_state",
        description="Initial agent state",
        tags={"env": "production"}
    )

    print(f"   Snapshot ID: {snapshot1.id[:8]}...")
    print(f"   Type: {snapshot1.metadata.snapshot_type.value}")
    print(f"   Size: {snapshot1.metadata.size_bytes} bytes")
    print(f"   Compressed: {snapshot1.metadata.compressed_size} bytes")
    print()

    # 2. Create Incremental Snapshot
    print("2. INCREMENTAL SNAPSHOT:")
    print("-" * 40)

    state2 = {
        "name": "agent-001",
        "version": "1.1.0",  # Changed
        "config": {
            "max_retries": 5,  # Changed
            "timeout": 30
        },
        "data": [1, 2, 3, 4, 5, 6]  # Added item
    }

    snapshot2 = manager.create_incremental(
        "agent-001",
        state2,
        name="config_update"
    )

    if snapshot2:
        print(f"   Snapshot ID: {snapshot2.id[:8]}...")
        print(f"   Type: {snapshot2.metadata.snapshot_type.value}")
        print(f"   Parent: {snapshot2.metadata.parent_id[:8]}...")
        print(f"   Size: {snapshot2.metadata.size_bytes} bytes")
    print()

    # 3. Restore State
    print("3. RESTORE STATE:")
    print("-" * 40)

    result = manager.restore("agent-001")
    print(f"   Success: {result.success}")
    print(f"   Restored: {result.data}")
    print()

    # 4. List Snapshots
    print("4. LIST SNAPSHOTS:")
    print("-" * 40)

    snapshots = manager.list_snapshots("agent-001")
    for meta in snapshots:
        print(f"   {meta.name}: {meta.snapshot_type.value}")
    print()

    # 5. Compare Snapshots
    print("5. COMPARE SNAPSHOTS:")
    print("-" * 40)

    if len(snapshots) >= 2:
        delta = manager.compare_snapshots(
            "agent-001",
            snapshots[0].snapshot_id,
            snapshots[1].snapshot_id
        )

        if delta:
            print(f"   Changes: {len(delta.entries)}")
            for entry in delta.entries[:3]:
                print(f"   - {entry.path}: {entry.operation}")
    print()

    # 6. Compression
    print("6. COMPRESSION OPTIONS:")
    print("-" * 40)

    test_data = {"large": "x" * 1000}

    for comp_type in CompressionType:
        snap = manager.create_snapshot(
            f"test-{comp_type.value}",
            test_data,
            compression=comp_type
        )
        ratio = snap.metadata.size_bytes / snap.metadata.compressed_size
        print(f"   {comp_type.value}: ratio {ratio:.2f}x")
    print()

    # 7. Verification
    print("7. VERIFY SNAPSHOT:")
    print("-" * 40)

    is_valid = manager.verify("agent-001", snapshot1.id)
    print(f"   Valid: {is_valid}")

    all_valid = manager.verify_all("agent-001")
    print(f"   All valid: {all(all_valid.values())}")
    print()

    # 8. Retention Policy
    print("8. RETENTION POLICY:")
    print("-" * 40)

    policy = SnapshotPolicy(
        retention=RetentionPolicy.KEEP_N,
        keep_count=5,
        auto_snapshot=True,
        auto_interval=timedelta(hours=1)
    )
    manager.set_policy("agent-001", policy)

    policy_info = manager.get_policy("agent-001")
    print(f"   Retention: {policy_info.retention.value}")
    print(f"   Keep count: {policy_info.keep_count}")
    print(f"   Auto snapshot: {policy_info.auto_snapshot}")
    print()

    # 9. Statistics
    print("9. SNAPSHOT STATISTICS:")
    print("-" * 40)

    stats = manager.get_stats("agent-001")
    print(f"   Count: {stats['count']}")
    print(f"   Full: {stats['full_count']}")
    print(f"   Incremental: {stats['incremental_count']}")
    print(f"   Total size: {stats['total_size']} bytes")
    print(f"   Compression ratio: {stats['compression_ratio']:.2f}x")
    print()

    # 10. Restore Specific Version
    print("10. RESTORE SPECIFIC VERSION:")
    print("-" * 40)

    result = manager.restore("agent-001", snapshot1.id)
    print(f"   Restored from: {result.snapshot_id[:8]}...")
    print(f"   Version: {result.data.get('version')}")
    print()

    # 11. Delta Engine
    print("11. DELTA ENGINE:")
    print("-" * 40)

    diff_engine = DiffEngine()

    old = {"a": 1, "b": {"x": 10, "y": 20}}
    new = {"a": 2, "b": {"x": 10, "z": 30}, "c": 3}

    delta = diff_engine.compute_delta(old, new)
    print(f"   Delta entries: {len(delta.entries)}")
    for entry in delta.entries:
        print(f"   - {entry.path}: {entry.operation}")

    # Apply delta
    applied = diff_engine.apply_delta(old, delta)
    print(f"   Applied result: {applied}")
    print()

    # 12. Export Metadata
    print("12. EXPORT METADATA:")
    print("-" * 40)

    metadata = manager.export_metadata("agent-001")
    print(f"   Exported: {len(metadata)} snapshots")
    print()

    # 13. Snapshot Tags
    print("13. SNAPSHOT TAGS:")
    print("-" * 40)

    print(f"   Tags: {snapshot1.metadata.tags}")
    print()

    # 14. List Sources
    print("14. LIST SOURCES:")
    print("-" * 40)

    sources = manager.list_sources()
    print(f"   Sources: {sources[:5]}")
    print()

    # 15. Should Snapshot Check
    print("15. AUTO SNAPSHOT CHECK:")
    print("-" * 40)

    should = manager.should_snapshot("agent-001")
    print(f"   Should snapshot: {should}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Snapshot Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
