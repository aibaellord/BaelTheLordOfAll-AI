#!/usr/bin/env python3
"""
BAEL - Checkpoint Manager
Advanced checkpointing for AI agent operations.

Features:
- State checkpointing
- Incremental checkpoints
- Snapshot management
- Recovery points
- Checkpoint validation
- Storage backends
- Compression support
- Retention policies
- Checkpoint metadata
- Rollback operations
"""

import asyncio
import gzip
import hashlib
import json
import os
import pickle
import shutil
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (Any, Awaitable, Callable, Dict, Generic, Iterator, List,
                    Optional, Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')


# =============================================================================
# ENUMS
# =============================================================================

class CheckpointType(Enum):
    """Checkpoint types."""
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"
    SNAPSHOT = "snapshot"


class CheckpointState(Enum):
    """Checkpoint state."""
    PENDING = "pending"
    CREATING = "creating"
    COMPLETE = "complete"
    FAILED = "failed"
    CORRUPTED = "corrupted"


class StorageBackend(Enum):
    """Storage backends."""
    MEMORY = "memory"
    FILESYSTEM = "filesystem"
    CUSTOM = "custom"


class CompressionType(Enum):
    """Compression types."""
    NONE = "none"
    GZIP = "gzip"
    ZLIB = "zlib"


class RetentionPolicy(Enum):
    """Retention policies."""
    KEEP_ALL = "keep_all"
    KEEP_N = "keep_n"
    KEEP_DURATION = "keep_duration"
    KEEP_FULL_ONLY = "keep_full_only"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class CheckpointConfig:
    """Checkpoint configuration."""
    storage: StorageBackend = StorageBackend.MEMORY
    compression: CompressionType = CompressionType.GZIP
    retention: RetentionPolicy = RetentionPolicy.KEEP_N
    max_checkpoints: int = 10
    retention_days: int = 30
    validate_on_create: bool = True
    auto_checkpoint_interval: Optional[int] = None  # seconds
    base_path: str = "/tmp/checkpoints"


@dataclass
class Checkpoint:
    """Checkpoint definition."""
    checkpoint_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    checkpoint_type: CheckpointType = CheckpointType.FULL
    state: CheckpointState = CheckpointState.PENDING
    parent_id: Optional[str] = None
    sequence_num: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    size_bytes: int = 0
    checksum: str = ""
    compressed: bool = False
    path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryPoint:
    """Recovery point."""
    recovery_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    checkpoint_ids: List[str] = field(default_factory=list)
    name: str = ""
    description: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CheckpointDelta:
    """Delta between checkpoints."""
    delta_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    from_checkpoint: str = ""
    to_checkpoint: str = ""
    added_keys: List[str] = field(default_factory=list)
    modified_keys: List[str] = field(default_factory=list)
    deleted_keys: List[str] = field(default_factory=list)
    delta_size: int = 0


@dataclass
class CheckpointStats:
    """Checkpoint statistics."""
    total_checkpoints: int = 0
    full_checkpoints: int = 0
    incremental_checkpoints: int = 0
    total_size_bytes: int = 0
    avg_checkpoint_time_ms: float = 0.0
    last_checkpoint: Optional[datetime] = None
    recovery_operations: int = 0


# =============================================================================
# STORAGE BACKENDS
# =============================================================================

class CheckpointStorage(ABC):
    """Base checkpoint storage."""

    @abstractmethod
    def save(
        self,
        checkpoint_id: str,
        data: bytes
    ) -> str:
        """Save checkpoint data."""
        pass

    @abstractmethod
    def load(self, checkpoint_id: str) -> Optional[bytes]:
        """Load checkpoint data."""
        pass

    @abstractmethod
    def delete(self, checkpoint_id: str) -> bool:
        """Delete checkpoint data."""
        pass

    @abstractmethod
    def exists(self, checkpoint_id: str) -> bool:
        """Check if checkpoint exists."""
        pass


class MemoryStorage(CheckpointStorage):
    """In-memory storage."""

    def __init__(self):
        self._data: Dict[str, bytes] = {}
        self._lock = threading.RLock()

    def save(self, checkpoint_id: str, data: bytes) -> str:
        with self._lock:
            self._data[checkpoint_id] = data
            return f"memory://{checkpoint_id}"

    def load(self, checkpoint_id: str) -> Optional[bytes]:
        with self._lock:
            return self._data.get(checkpoint_id)

    def delete(self, checkpoint_id: str) -> bool:
        with self._lock:
            if checkpoint_id in self._data:
                del self._data[checkpoint_id]
                return True
            return False

    def exists(self, checkpoint_id: str) -> bool:
        with self._lock:
            return checkpoint_id in self._data


class FilesystemStorage(CheckpointStorage):
    """Filesystem storage."""

    def __init__(self, base_path: str):
        self._base_path = Path(base_path)
        self._base_path.mkdir(parents=True, exist_ok=True)

    def _get_path(self, checkpoint_id: str) -> Path:
        return self._base_path / f"{checkpoint_id}.ckpt"

    def save(self, checkpoint_id: str, data: bytes) -> str:
        path = self._get_path(checkpoint_id)
        path.write_bytes(data)
        return str(path)

    def load(self, checkpoint_id: str) -> Optional[bytes]:
        path = self._get_path(checkpoint_id)
        if path.exists():
            return path.read_bytes()
        return None

    def delete(self, checkpoint_id: str) -> bool:
        path = self._get_path(checkpoint_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def exists(self, checkpoint_id: str) -> bool:
        return self._get_path(checkpoint_id).exists()


# =============================================================================
# SERIALIZER
# =============================================================================

class CheckpointSerializer:
    """Checkpoint serializer."""

    def __init__(self, compression: CompressionType = CompressionType.GZIP):
        self._compression = compression

    def serialize(self, data: Any) -> bytes:
        """Serialize data."""
        raw = pickle.dumps(data)

        if self._compression == CompressionType.GZIP:
            return gzip.compress(raw)
        elif self._compression == CompressionType.ZLIB:
            import zlib
            return zlib.compress(raw)

        return raw

    def deserialize(self, data: bytes) -> Any:
        """Deserialize data."""
        if self._compression == CompressionType.GZIP:
            raw = gzip.decompress(data)
        elif self._compression == CompressionType.ZLIB:
            import zlib
            raw = zlib.decompress(data)
        else:
            raw = data

        return pickle.loads(raw)

    @staticmethod
    def compute_checksum(data: bytes) -> str:
        """Compute checksum."""
        return hashlib.sha256(data).hexdigest()


# =============================================================================
# DELTA CALCULATOR
# =============================================================================

class DeltaCalculator:
    """Calculate deltas between states."""

    def calculate(
        self,
        old_state: Dict[str, Any],
        new_state: Dict[str, Any]
    ) -> CheckpointDelta:
        """Calculate delta."""
        delta = CheckpointDelta()

        old_keys = set(old_state.keys())
        new_keys = set(new_state.keys())

        delta.added_keys = list(new_keys - old_keys)
        delta.deleted_keys = list(old_keys - new_keys)

        common = old_keys & new_keys
        delta.modified_keys = [
            k for k in common
            if old_state[k] != new_state[k]
        ]

        return delta

    def apply_delta(
        self,
        base_state: Dict[str, Any],
        delta: CheckpointDelta,
        changes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply delta to base state."""
        result = dict(base_state)

        # Remove deleted keys
        for key in delta.deleted_keys:
            result.pop(key, None)

        # Add new keys
        for key in delta.added_keys:
            if key in changes:
                result[key] = changes[key]

        # Apply modifications
        for key in delta.modified_keys:
            if key in changes:
                result[key] = changes[key]

        return result


# =============================================================================
# CHECKPOINT MANAGER
# =============================================================================

class CheckpointManager:
    """
    Checkpoint Manager for BAEL.

    Advanced state checkpointing.
    """

    def __init__(self, config: Optional[CheckpointConfig] = None):
        self._config = config or CheckpointConfig()
        self._storage = self._create_storage()
        self._serializer = CheckpointSerializer(self._config.compression)
        self._delta_calc = DeltaCalculator()
        self._checkpoints: Dict[str, Checkpoint] = {}
        self._recovery_points: Dict[str, RecoveryPoint] = {}
        self._current_state: Dict[str, Any] = {}
        self._last_full_id: Optional[str] = None
        self._sequence = 0
        self._stats = CheckpointStats()
        self._checkpoint_times: List[float] = []
        self._lock = threading.RLock()

    def _create_storage(self) -> CheckpointStorage:
        """Create storage backend."""
        if self._config.storage == StorageBackend.FILESYSTEM:
            return FilesystemStorage(self._config.base_path)

        return MemoryStorage()

    # -------------------------------------------------------------------------
    # CHECKPOINT CREATION
    # -------------------------------------------------------------------------

    async def create_checkpoint(
        self,
        state: Dict[str, Any],
        checkpoint_type: CheckpointType = CheckpointType.FULL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Checkpoint:
        """Create checkpoint."""
        start_time = time.time()

        with self._lock:
            self._sequence += 1

            checkpoint = Checkpoint(
                checkpoint_type=checkpoint_type,
                state=CheckpointState.CREATING,
                sequence_num=self._sequence,
                metadata=metadata or {}
            )

            try:
                if checkpoint_type == CheckpointType.FULL:
                    data = self._create_full_checkpoint(state)
                    checkpoint.parent_id = None
                    self._last_full_id = checkpoint.checkpoint_id

                elif checkpoint_type == CheckpointType.INCREMENTAL:
                    if not self._last_full_id:
                        # No base checkpoint, create full
                        data = self._create_full_checkpoint(state)
                        self._last_full_id = checkpoint.checkpoint_id
                    else:
                        data = self._create_incremental_checkpoint(state)
                        checkpoint.parent_id = self._last_full_id

                elif checkpoint_type == CheckpointType.DIFFERENTIAL:
                    data = self._create_differential_checkpoint(state)
                    checkpoint.parent_id = self._last_full_id

                else:
                    data = self._create_full_checkpoint(state)

                # Serialize and save
                serialized = self._serializer.serialize(data)
                checkpoint.checksum = CheckpointSerializer.compute_checksum(serialized)
                checkpoint.size_bytes = len(serialized)
                checkpoint.compressed = self._config.compression != CompressionType.NONE

                path = self._storage.save(checkpoint.checkpoint_id, serialized)
                checkpoint.path = path
                checkpoint.state = CheckpointState.COMPLETE

                # Validate if configured
                if self._config.validate_on_create:
                    if not self._validate_checkpoint(checkpoint):
                        checkpoint.state = CheckpointState.CORRUPTED

                # Update current state
                self._current_state = dict(state)

                # Store checkpoint
                self._checkpoints[checkpoint.checkpoint_id] = checkpoint

                # Update stats
                elapsed = (time.time() - start_time) * 1000
                self._checkpoint_times.append(elapsed)
                self._stats.total_checkpoints += 1
                self._stats.total_size_bytes += checkpoint.size_bytes
                self._stats.last_checkpoint = datetime.utcnow()

                if checkpoint_type == CheckpointType.FULL:
                    self._stats.full_checkpoints += 1
                else:
                    self._stats.incremental_checkpoints += 1

                self._stats.avg_checkpoint_time_ms = sum(self._checkpoint_times) / len(self._checkpoint_times)

                # Apply retention
                await self._apply_retention()

            except Exception as e:
                checkpoint.state = CheckpointState.FAILED
                checkpoint.metadata["error"] = str(e)

            return checkpoint

    def _create_full_checkpoint(
        self,
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create full checkpoint data."""
        return {
            "type": "full",
            "state": state,
            "timestamp": datetime.utcnow().isoformat()
        }

    def _create_incremental_checkpoint(
        self,
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create incremental checkpoint data."""
        delta = self._delta_calc.calculate(self._current_state, state)

        changes = {}
        for key in delta.added_keys + delta.modified_keys:
            changes[key] = state[key]

        return {
            "type": "incremental",
            "delta": {
                "added": delta.added_keys,
                "modified": delta.modified_keys,
                "deleted": delta.deleted_keys
            },
            "changes": changes,
            "timestamp": datetime.utcnow().isoformat()
        }

    def _create_differential_checkpoint(
        self,
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create differential checkpoint."""
        # Load base full checkpoint
        if self._last_full_id:
            base = self._load_checkpoint_data(self._last_full_id)
            if base:
                base_state = base.get("state", {})
                delta = self._delta_calc.calculate(base_state, state)

                changes = {}
                for key in delta.added_keys + delta.modified_keys:
                    changes[key] = state[key]

                return {
                    "type": "differential",
                    "base_id": self._last_full_id,
                    "delta": {
                        "added": delta.added_keys,
                        "modified": delta.modified_keys,
                        "deleted": delta.deleted_keys
                    },
                    "changes": changes,
                    "timestamp": datetime.utcnow().isoformat()
                }

        # Fallback to full
        return self._create_full_checkpoint(state)

    def _validate_checkpoint(self, checkpoint: Checkpoint) -> bool:
        """Validate checkpoint."""
        data = self._storage.load(checkpoint.checkpoint_id)

        if not data:
            return False

        actual_checksum = CheckpointSerializer.compute_checksum(data)
        return actual_checksum == checkpoint.checksum

    # -------------------------------------------------------------------------
    # CHECKPOINT RESTORATION
    # -------------------------------------------------------------------------

    async def restore_checkpoint(
        self,
        checkpoint_id: str
    ) -> Optional[Dict[str, Any]]:
        """Restore state from checkpoint."""
        with self._lock:
            checkpoint = self._checkpoints.get(checkpoint_id)

            if not checkpoint:
                return None

            if checkpoint.state != CheckpointState.COMPLETE:
                return None

            data = self._load_checkpoint_data(checkpoint_id)

            if not data:
                return None

            # Handle different checkpoint types
            if data.get("type") == "full":
                state = data.get("state", {})

            elif data.get("type") == "incremental":
                # Build chain back to full
                state = await self._build_state_chain(checkpoint)

            elif data.get("type") == "differential":
                # Apply to base
                base_id = data.get("base_id")
                if base_id:
                    base_data = self._load_checkpoint_data(base_id)
                    if base_data:
                        base_state = base_data.get("state", {})
                        delta = CheckpointDelta(
                            added_keys=data["delta"]["added"],
                            modified_keys=data["delta"]["modified"],
                            deleted_keys=data["delta"]["deleted"]
                        )
                        state = self._delta_calc.apply_delta(
                            base_state, delta, data["changes"]
                        )
                    else:
                        return None
                else:
                    return None
            else:
                state = data.get("state", {})

            self._current_state = state
            self._stats.recovery_operations += 1

            return state

    async def _build_state_chain(
        self,
        checkpoint: Checkpoint
    ) -> Dict[str, Any]:
        """Build state from incremental chain."""
        chain = []
        current = checkpoint

        # Build chain to full checkpoint
        while current and current.checkpoint_type != CheckpointType.FULL:
            chain.append(current)
            if current.parent_id:
                current = self._checkpoints.get(current.parent_id)
            else:
                break

        if current:
            chain.append(current)

        # Reverse to start from full
        chain.reverse()

        # Apply chain
        state = {}

        for ckpt in chain:
            data = self._load_checkpoint_data(ckpt.checkpoint_id)

            if not data:
                continue

            if data.get("type") == "full":
                state = data.get("state", {})
            else:
                delta = CheckpointDelta(
                    added_keys=data["delta"]["added"],
                    modified_keys=data["delta"]["modified"],
                    deleted_keys=data["delta"]["deleted"]
                )
                state = self._delta_calc.apply_delta(
                    state, delta, data["changes"]
                )

        return state

    def _load_checkpoint_data(
        self,
        checkpoint_id: str
    ) -> Optional[Dict[str, Any]]:
        """Load checkpoint data."""
        raw = self._storage.load(checkpoint_id)

        if raw:
            return self._serializer.deserialize(raw)

        return None

    # -------------------------------------------------------------------------
    # RECOVERY POINTS
    # -------------------------------------------------------------------------

    def create_recovery_point(
        self,
        name: str,
        description: str = "",
        checkpoint_ids: Optional[List[str]] = None
    ) -> RecoveryPoint:
        """Create recovery point."""
        with self._lock:
            if checkpoint_ids is None:
                # Use latest checkpoint
                checkpoint_ids = [
                    c.checkpoint_id for c in sorted(
                        self._checkpoints.values(),
                        key=lambda x: x.created_at,
                        reverse=True
                    )[:1]
                ]

            point = RecoveryPoint(
                checkpoint_ids=checkpoint_ids,
                name=name,
                description=description
            )

            self._recovery_points[point.recovery_id] = point
            return point

    async def restore_recovery_point(
        self,
        recovery_id: str
    ) -> Optional[Dict[str, Any]]:
        """Restore from recovery point."""
        with self._lock:
            point = self._recovery_points.get(recovery_id)

            if not point or not point.checkpoint_ids:
                return None

            # Restore latest checkpoint in point
            return await self.restore_checkpoint(point.checkpoint_ids[0])

    def list_recovery_points(self) -> List[RecoveryPoint]:
        """List recovery points."""
        with self._lock:
            return list(self._recovery_points.values())

    # -------------------------------------------------------------------------
    # CHECKPOINT MANAGEMENT
    # -------------------------------------------------------------------------

    def get_checkpoint(
        self,
        checkpoint_id: str
    ) -> Optional[Checkpoint]:
        """Get checkpoint."""
        with self._lock:
            return self._checkpoints.get(checkpoint_id)

    def list_checkpoints(
        self,
        checkpoint_type: Optional[CheckpointType] = None
    ) -> List[Checkpoint]:
        """List checkpoints."""
        with self._lock:
            checkpoints = list(self._checkpoints.values())

            if checkpoint_type:
                checkpoints = [
                    c for c in checkpoints
                    if c.checkpoint_type == checkpoint_type
                ]

            return sorted(checkpoints, key=lambda x: x.created_at)

    def get_latest_checkpoint(
        self,
        checkpoint_type: Optional[CheckpointType] = None
    ) -> Optional[Checkpoint]:
        """Get latest checkpoint."""
        checkpoints = self.list_checkpoints(checkpoint_type)
        return checkpoints[-1] if checkpoints else None

    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete checkpoint."""
        with self._lock:
            checkpoint = self._checkpoints.pop(checkpoint_id, None)

            if checkpoint:
                self._storage.delete(checkpoint_id)
                self._stats.total_size_bytes -= checkpoint.size_bytes
                return True

            return False

    # -------------------------------------------------------------------------
    # RETENTION
    # -------------------------------------------------------------------------

    async def _apply_retention(self) -> int:
        """Apply retention policy."""
        deleted = 0

        with self._lock:
            checkpoints = sorted(
                self._checkpoints.values(),
                key=lambda x: x.created_at
            )

            if self._config.retention == RetentionPolicy.KEEP_N:
                # Keep only last N
                while len(checkpoints) > self._config.max_checkpoints:
                    oldest = checkpoints.pop(0)
                    await self.delete_checkpoint(oldest.checkpoint_id)
                    deleted += 1

            elif self._config.retention == RetentionPolicy.KEEP_DURATION:
                # Keep only within duration
                cutoff = datetime.utcnow() - timedelta(
                    days=self._config.retention_days
                )

                for ckpt in checkpoints:
                    if ckpt.created_at < cutoff:
                        await self.delete_checkpoint(ckpt.checkpoint_id)
                        deleted += 1

            elif self._config.retention == RetentionPolicy.KEEP_FULL_ONLY:
                # Delete incrementals older than latest full
                if self._last_full_id:
                    full = self._checkpoints.get(self._last_full_id)
                    if full:
                        for ckpt in checkpoints:
                            if (ckpt.checkpoint_type != CheckpointType.FULL
                                and ckpt.created_at < full.created_at):
                                await self.delete_checkpoint(ckpt.checkpoint_id)
                                deleted += 1

        return deleted

    # -------------------------------------------------------------------------
    # ROLLBACK
    # -------------------------------------------------------------------------

    async def rollback_to(
        self,
        checkpoint_id: str
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Rollback to checkpoint."""
        state = await self.restore_checkpoint(checkpoint_id)

        if state is None:
            return (False, None)

        # Delete checkpoints after this one
        checkpoint = self._checkpoints.get(checkpoint_id)

        if checkpoint:
            with self._lock:
                to_delete = [
                    c.checkpoint_id for c in self._checkpoints.values()
                    if c.created_at > checkpoint.created_at
                ]

                for cid in to_delete:
                    await self.delete_checkpoint(cid)

        return (True, state)

    # -------------------------------------------------------------------------
    # COMPARISON
    # -------------------------------------------------------------------------

    def compare_checkpoints(
        self,
        checkpoint_id1: str,
        checkpoint_id2: str
    ) -> Optional[CheckpointDelta]:
        """Compare two checkpoints."""
        with self._lock:
            data1 = self._load_checkpoint_data(checkpoint_id1)
            data2 = self._load_checkpoint_data(checkpoint_id2)

            if not data1 or not data2:
                return None

            state1 = data1.get("state", data1.get("changes", {}))
            state2 = data2.get("state", data2.get("changes", {}))

            delta = self._delta_calc.calculate(state1, state2)
            delta.from_checkpoint = checkpoint_id1
            delta.to_checkpoint = checkpoint_id2

            return delta

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> CheckpointStats:
        """Get statistics."""
        with self._lock:
            return CheckpointStats(
                total_checkpoints=self._stats.total_checkpoints,
                full_checkpoints=self._stats.full_checkpoints,
                incremental_checkpoints=self._stats.incremental_checkpoints,
                total_size_bytes=self._stats.total_size_bytes,
                avg_checkpoint_time_ms=self._stats.avg_checkpoint_time_ms,
                last_checkpoint=self._stats.last_checkpoint,
                recovery_operations=self._stats.recovery_operations
            )

    def get_current_state(self) -> Dict[str, Any]:
        """Get current state."""
        with self._lock:
            return dict(self._current_state)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Checkpoint Manager."""
    print("=" * 70)
    print("BAEL - CHECKPOINT MANAGER DEMO")
    print("Advanced State Checkpointing for AI Agents")
    print("=" * 70)
    print()

    manager = CheckpointManager(CheckpointConfig(
        storage=StorageBackend.MEMORY,
        compression=CompressionType.GZIP,
        retention=RetentionPolicy.KEEP_N,
        max_checkpoints=5
    ))

    # 1. Create Full Checkpoint
    print("1. CREATE FULL CHECKPOINT:")
    print("-" * 40)

    state1 = {
        "users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
        "config": {"theme": "dark", "lang": "en"},
        "counter": 100
    }

    ckpt1 = await manager.create_checkpoint(
        state1,
        CheckpointType.FULL,
        {"label": "initial"}
    )

    print(f"   Checkpoint ID: {ckpt1.checkpoint_id[:8]}...")
    print(f"   Type: {ckpt1.checkpoint_type.value}")
    print(f"   Size: {ckpt1.size_bytes} bytes")
    print(f"   State: {ckpt1.state.value}")
    print()

    # 2. Modify State and Create Incremental
    print("2. CREATE INCREMENTAL CHECKPOINT:")
    print("-" * 40)

    state2 = {
        "users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}, {"id": 3, "name": "Charlie"}],
        "config": {"theme": "light", "lang": "en"},
        "counter": 150
    }

    ckpt2 = await manager.create_checkpoint(
        state2,
        CheckpointType.INCREMENTAL
    )

    print(f"   Checkpoint ID: {ckpt2.checkpoint_id[:8]}...")
    print(f"   Type: {ckpt2.checkpoint_type.value}")
    print(f"   Size: {ckpt2.size_bytes} bytes")
    print(f"   Parent: {ckpt2.parent_id[:8] if ckpt2.parent_id else 'None'}...")
    print()

    # 3. Restore Checkpoint
    print("3. RESTORE CHECKPOINT:")
    print("-" * 40)

    restored = await manager.restore_checkpoint(ckpt1.checkpoint_id)

    print(f"   Restored state from checkpoint 1:")
    print(f"   Counter: {restored.get('counter')}")
    print(f"   Theme: {restored.get('config', {}).get('theme')}")
    print()

    # 4. Create Recovery Point
    print("4. CREATE RECOVERY POINT:")
    print("-" * 40)

    recovery = manager.create_recovery_point(
        name="pre_migration",
        description="Before database migration"
    )

    print(f"   Recovery ID: {recovery.recovery_id[:8]}...")
    print(f"   Name: {recovery.name}")
    print(f"   Checkpoints: {len(recovery.checkpoint_ids)}")
    print()

    # 5. List Checkpoints
    print("5. LIST CHECKPOINTS:")
    print("-" * 40)

    checkpoints = manager.list_checkpoints()

    for ckpt in checkpoints:
        print(f"   {ckpt.checkpoint_id[:8]}... - {ckpt.checkpoint_type.value}, "
              f"{ckpt.size_bytes} bytes")
    print()

    # 6. Compare Checkpoints
    print("6. COMPARE CHECKPOINTS:")
    print("-" * 40)

    delta = manager.compare_checkpoints(
        ckpt1.checkpoint_id,
        ckpt2.checkpoint_id
    )

    if delta:
        print(f"   Added keys: {delta.added_keys}")
        print(f"   Modified keys: {delta.modified_keys}")
        print(f"   Deleted keys: {delta.deleted_keys}")
    print()

    # 7. Create More Checkpoints
    print("7. CREATE MORE CHECKPOINTS:")
    print("-" * 40)

    for i in range(4):
        state = {"counter": 200 + i * 10, "iteration": i}
        ckpt = await manager.create_checkpoint(state)
        print(f"   Created checkpoint {i+1}: {ckpt.checkpoint_id[:8]}...")
    print()

    # 8. Check Retention
    print("8. CHECK RETENTION (max 5):")
    print("-" * 40)

    checkpoints = manager.list_checkpoints()
    print(f"   Total checkpoints: {len(checkpoints)}")
    print()

    # 9. Get Latest Checkpoint
    print("9. GET LATEST CHECKPOINT:")
    print("-" * 40)

    latest = manager.get_latest_checkpoint()

    if latest:
        print(f"   ID: {latest.checkpoint_id[:8]}...")
        print(f"   Created: {latest.created_at}")
        print(f"   Sequence: {latest.sequence_num}")
    print()

    # 10. Rollback
    print("10. ROLLBACK TO CHECKPOINT:")
    print("-" * 40)

    first_ckpt = manager.list_checkpoints()[0]
    success, state = await manager.rollback_to(first_ckpt.checkpoint_id)

    print(f"   Rollback success: {success}")
    print(f"   Checkpoints after rollback: {len(manager.list_checkpoints())}")
    print()

    # 11. Restore Recovery Point
    print("11. RESTORE RECOVERY POINT:")
    print("-" * 40)

    # Create new state and checkpoint
    await manager.create_checkpoint({"new": "state"})

    restored = await manager.restore_recovery_point(recovery.recovery_id)

    if restored:
        print(f"   Restored from recovery point: {recovery.name}")
    else:
        print("   Recovery point no longer available (retention)")
    print()

    # 12. Differential Checkpoint
    print("12. DIFFERENTIAL CHECKPOINT:")
    print("-" * 40)

    # Create base
    base = await manager.create_checkpoint(
        {"a": 1, "b": 2, "c": 3},
        CheckpointType.FULL
    )

    # Create differential
    diff = await manager.create_checkpoint(
        {"a": 1, "b": 5, "d": 4},  # b modified, c deleted, d added
        CheckpointType.DIFFERENTIAL
    )

    print(f"   Base: {base.checkpoint_id[:8]}...")
    print(f"   Diff: {diff.checkpoint_id[:8]}...")
    print(f"   Diff parent: {diff.parent_id[:8] if diff.parent_id else 'None'}...")
    print()

    # 13. Statistics
    print("13. STATISTICS:")
    print("-" * 40)

    stats = manager.get_stats()

    print(f"   Total checkpoints: {stats.total_checkpoints}")
    print(f"   Full checkpoints: {stats.full_checkpoints}")
    print(f"   Incremental checkpoints: {stats.incremental_checkpoints}")
    print(f"   Total size: {stats.total_size_bytes} bytes")
    print(f"   Avg checkpoint time: {stats.avg_checkpoint_time_ms:.2f} ms")
    print(f"   Recovery operations: {stats.recovery_operations}")
    print()

    # 14. Current State
    print("14. CURRENT STATE:")
    print("-" * 40)

    current = manager.get_current_state()
    print(f"   Current state: {current}")
    print()

    # 15. List Recovery Points
    print("15. LIST RECOVERY POINTS:")
    print("-" * 40)

    points = manager.list_recovery_points()

    for point in points:
        print(f"   {point.name}: {len(point.checkpoint_ids)} checkpoints")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Checkpoint Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
