"""
BAEL Snapshot/Checkpoint Engine Implementation
===============================================

Point-in-time state capture and recovery.

"Ba'el preserves moments in eternal memory." — Ba'el
"""

import asyncio
import gzip
import hashlib
import json
import logging
import os
import pickle
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import uuid

logger = logging.getLogger("BAEL.Snapshot")


# ============================================================================
# ENUMS
# ============================================================================

class SnapshotType(Enum):
    """Snapshot types."""
    FULL = "full"           # Complete state
    INCREMENTAL = "incremental"  # Changes since last
    DIFFERENTIAL = "differential"  # Changes since last full


class SnapshotState(Enum):
    """Snapshot states."""
    PENDING = "pending"
    CREATING = "creating"
    COMPLETED = "completed"
    FAILED = "failed"
    RESTORING = "restoring"
    RESTORED = "restored"


class CompressionType(Enum):
    """Compression types."""
    NONE = "none"
    GZIP = "gzip"
    LZ4 = "lz4"
    ZSTD = "zstd"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Snapshot:
    """A snapshot."""
    id: str
    name: str
    snapshot_type: SnapshotType

    # State
    state: SnapshotState = SnapshotState.PENDING

    # Data
    data: Optional[Dict[str, Any]] = None
    size_bytes: int = 0
    checksum: Optional[str] = None

    # Parent (for incremental)
    parent_id: Optional[str] = None

    # Compression
    compression: CompressionType = CompressionType.GZIP

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    # Storage
    file_path: Optional[str] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'type': self.snapshot_type.value,
            'state': self.state.value,
            'size_bytes': self.size_bytes,
            'checksum': self.checksum,
            'created_at': self.created_at.isoformat()
        }


@dataclass
class SnapshotConfig:
    """Snapshot configuration."""
    storage_path: str = "./snapshots"
    compression: CompressionType = CompressionType.GZIP
    max_snapshots: int = 10
    auto_cleanup: bool = True
    include_timestamp: bool = True


# ============================================================================
# SNAPSHOT ENGINE
# ============================================================================

class SnapshotEngine:
    """
    Snapshot/checkpoint engine.

    Features:
    - Full and incremental snapshots
    - Compression
    - Verification
    - Automatic cleanup

    "Ba'el captures reality at any moment." — Ba'el
    """

    def __init__(self, config: Optional[SnapshotConfig] = None):
        """Initialize snapshot engine."""
        self.config = config or SnapshotConfig()

        # Snapshots
        self._snapshots: Dict[str, Snapshot] = {}
        self._latest_full: Optional[str] = None
        self._latest: Optional[str] = None

        # State providers
        self._state_providers: Dict[str, Callable] = {}
        self._restore_handlers: Dict[str, Callable] = {}

        # Storage
        self._storage_path = Path(self.config.storage_path)
        self._storage_path.mkdir(parents=True, exist_ok=True)

        # Thread safety
        self._lock = threading.RLock()

        # Stats
        self._stats = {
            'snapshots_created': 0,
            'snapshots_restored': 0,
            'total_size_bytes': 0
        }

        logger.info(f"Snapshot Engine initialized: {self._storage_path}")

    # ========================================================================
    # STATE PROVIDERS
    # ========================================================================

    def register_state_provider(
        self,
        name: str,
        provider: Callable[[], Any],
        restore_handler: Callable[[Any], None]
    ) -> None:
        """
        Register a state provider.

        Args:
            name: Provider name
            provider: Function that returns state
            restore_handler: Function to restore state
        """
        self._state_providers[name] = provider
        self._restore_handlers[name] = restore_handler

        logger.debug(f"State provider registered: {name}")

    # ========================================================================
    # SNAPSHOT CREATION
    # ========================================================================

    async def create_snapshot(
        self,
        name: str,
        snapshot_type: SnapshotType = SnapshotType.FULL,
        snapshot_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Snapshot:
        """
        Create a snapshot.

        Args:
            name: Snapshot name
            snapshot_type: Type of snapshot
            snapshot_id: Optional ID
            metadata: Additional metadata

        Returns:
            Snapshot
        """
        snapshot = Snapshot(
            id=snapshot_id or str(uuid.uuid4()),
            name=name,
            snapshot_type=snapshot_type,
            compression=self.config.compression,
            metadata=metadata or {}
        )

        with self._lock:
            self._snapshots[snapshot.id] = snapshot

        try:
            snapshot.state = SnapshotState.CREATING

            # Collect state
            if snapshot_type == SnapshotType.FULL:
                state_data = await self._collect_full_state()
            else:
                state_data = await self._collect_incremental_state()

            snapshot.data = state_data

            # Save to disk
            await self._save_snapshot(snapshot)

            # Calculate checksum
            snapshot.checksum = self._calculate_checksum(snapshot.data)

            # Update tracking
            snapshot.state = SnapshotState.COMPLETED
            snapshot.completed_at = datetime.now()

            with self._lock:
                self._latest = snapshot.id
                if snapshot_type == SnapshotType.FULL:
                    self._latest_full = snapshot.id

            self._stats['snapshots_created'] += 1
            self._stats['total_size_bytes'] += snapshot.size_bytes

            # Cleanup old snapshots
            if self.config.auto_cleanup:
                await self._cleanup_old_snapshots()

            logger.info(f"Snapshot created: {name} ({snapshot.size_bytes} bytes)")

        except Exception as e:
            snapshot.state = SnapshotState.FAILED
            snapshot.metadata['error'] = str(e)
            logger.error(f"Snapshot failed: {e}")
            raise

        return snapshot

    async def _collect_full_state(self) -> Dict[str, Any]:
        """Collect full state from all providers."""
        state = {}

        for name, provider in self._state_providers.items():
            try:
                if asyncio.iscoroutinefunction(provider):
                    state[name] = await provider()
                else:
                    state[name] = await asyncio.to_thread(provider)
            except Exception as e:
                logger.error(f"State collection failed for {name}: {e}")
                state[name] = None

        return state

    async def _collect_incremental_state(self) -> Dict[str, Any]:
        """Collect incremental state (changes since last)."""
        # For simplicity, just collect full state
        # Real implementation would track changes
        return await self._collect_full_state()

    async def _save_snapshot(self, snapshot: Snapshot) -> None:
        """Save snapshot to disk."""
        filename = f"{snapshot.id}"

        if self.config.include_timestamp:
            timestamp = snapshot.created_at.strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{filename}"

        # Serialize
        serialized = pickle.dumps(snapshot.data)

        # Compress
        if snapshot.compression == CompressionType.GZIP:
            compressed = gzip.compress(serialized)
            filename += ".pkl.gz"
        else:
            compressed = serialized
            filename += ".pkl"

        # Save
        file_path = self._storage_path / filename

        await asyncio.to_thread(file_path.write_bytes, compressed)

        snapshot.file_path = str(file_path)
        snapshot.size_bytes = len(compressed)

    def _calculate_checksum(self, data: Any) -> str:
        """Calculate checksum for data."""
        serialized = pickle.dumps(data)
        return hashlib.sha256(serialized).hexdigest()

    # ========================================================================
    # SNAPSHOT RESTORATION
    # ========================================================================

    async def restore_snapshot(
        self,
        snapshot_id: str,
        verify: bool = True
    ) -> bool:
        """
        Restore from snapshot.

        Args:
            snapshot_id: Snapshot to restore
            verify: Verify checksum

        Returns:
            True if restored
        """
        snapshot = self._snapshots.get(snapshot_id)
        if not snapshot:
            raise ValueError(f"Snapshot not found: {snapshot_id}")

        snapshot.state = SnapshotState.RESTORING

        try:
            # Load data if not in memory
            if snapshot.data is None:
                await self._load_snapshot(snapshot)

            # Verify
            if verify:
                checksum = self._calculate_checksum(snapshot.data)
                if checksum != snapshot.checksum:
                    raise ValueError("Checksum mismatch")

            # Restore each provider's state
            for name, data in snapshot.data.items():
                if name in self._restore_handlers:
                    handler = self._restore_handlers[name]

                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(data)
                        else:
                            await asyncio.to_thread(handler, data)
                    except Exception as e:
                        logger.error(f"Restore failed for {name}: {e}")

            snapshot.state = SnapshotState.RESTORED
            self._stats['snapshots_restored'] += 1

            logger.info(f"Snapshot restored: {snapshot_id}")

            return True

        except Exception as e:
            snapshot.state = SnapshotState.FAILED
            logger.error(f"Restore failed: {e}")
            return False

    async def _load_snapshot(self, snapshot: Snapshot) -> None:
        """Load snapshot from disk."""
        if not snapshot.file_path:
            raise ValueError("Snapshot has no file path")

        file_path = Path(snapshot.file_path)
        if not file_path.exists():
            raise ValueError(f"Snapshot file not found: {file_path}")

        # Read
        compressed = await asyncio.to_thread(file_path.read_bytes)

        # Decompress
        if snapshot.compression == CompressionType.GZIP:
            serialized = gzip.decompress(compressed)
        else:
            serialized = compressed

        # Deserialize
        snapshot.data = pickle.loads(serialized)

    # ========================================================================
    # CLEANUP
    # ========================================================================

    async def _cleanup_old_snapshots(self) -> int:
        """Clean up old snapshots."""
        with self._lock:
            snapshots = sorted(
                self._snapshots.values(),
                key=lambda s: s.created_at,
                reverse=True
            )

            if len(snapshots) <= self.config.max_snapshots:
                return 0

            removed = 0
            for snapshot in snapshots[self.config.max_snapshots:]:
                # Don't remove latest full
                if snapshot.id == self._latest_full:
                    continue

                # Remove file
                if snapshot.file_path:
                    try:
                        Path(snapshot.file_path).unlink(missing_ok=True)
                    except Exception as e:
                        logger.error(f"Failed to remove snapshot file: {e}")

                del self._snapshots[snapshot.id]
                removed += 1

            if removed:
                logger.info(f"Cleaned up {removed} old snapshots")

            return removed

    async def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a snapshot."""
        with self._lock:
            snapshot = self._snapshots.get(snapshot_id)
            if not snapshot:
                return False

            if snapshot.file_path:
                Path(snapshot.file_path).unlink(missing_ok=True)

            del self._snapshots[snapshot_id]

            return True

    # ========================================================================
    # QUERIES
    # ========================================================================

    def get_snapshot(self, snapshot_id: str) -> Optional[Snapshot]:
        """Get snapshot by ID."""
        return self._snapshots.get(snapshot_id)

    def get_latest(self) -> Optional[Snapshot]:
        """Get latest snapshot."""
        if self._latest:
            return self._snapshots.get(self._latest)
        return None

    def get_latest_full(self) -> Optional[Snapshot]:
        """Get latest full snapshot."""
        if self._latest_full:
            return self._snapshots.get(self._latest_full)
        return None

    def list_snapshots(
        self,
        snapshot_type: Optional[SnapshotType] = None
    ) -> List[Snapshot]:
        """List snapshots."""
        snapshots = list(self._snapshots.values())

        if snapshot_type:
            snapshots = [s for s in snapshots if s.snapshot_type == snapshot_type]

        return sorted(snapshots, key=lambda s: s.created_at, reverse=True)

    # ========================================================================
    # STATS
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            'snapshot_count': len(self._snapshots),
            'latest_id': self._latest,
            'latest_full_id': self._latest_full,
            **self._stats
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

snapshot_engine = SnapshotEngine()


async def create_snapshot(name: str, **kwargs) -> Snapshot:
    """Create a snapshot."""
    return await snapshot_engine.create_snapshot(name, **kwargs)


async def restore_snapshot(snapshot_id: str) -> bool:
    """Restore from snapshot."""
    return await snapshot_engine.restore_snapshot(snapshot_id)


def register_state_provider(
    name: str,
    provider: Callable,
    restore_handler: Callable
) -> None:
    """Register state provider."""
    snapshot_engine.register_state_provider(name, provider, restore_handler)
