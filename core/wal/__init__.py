"""
BAEL Write-Ahead Log (WAL) Engine Implementation
=================================================

Durability through logging.

"Ba'el writes intention before action." — Ba'el
"""

import asyncio
import hashlib
import logging
import os
import struct
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid
import json

logger = logging.getLogger("BAEL.WAL")


# ============================================================================
# ENUMS
# ============================================================================

class WALEntryType(Enum):
    """WAL entry types."""
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    CHECKPOINT = "checkpoint"
    BEGIN = "begin"
    COMMIT = "commit"
    ROLLBACK = "rollback"


class WALState(Enum):
    """WAL states."""
    OPEN = "open"
    SYNCED = "synced"
    CLOSED = "closed"
    CORRUPTED = "corrupted"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class WALEntry:
    """A WAL entry."""
    lsn: int  # Log Sequence Number
    entry_type: WALEntryType

    # Transaction
    transaction_id: Optional[str] = None

    # Data
    table_name: Optional[str] = None
    key: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    old_data: Optional[Dict[str, Any]] = None

    # Timing
    timestamp: datetime = field(default_factory=datetime.now)

    # Checksum
    checksum: Optional[str] = None

    def to_bytes(self) -> bytes:
        """Serialize entry to bytes."""
        payload = json.dumps({
            'lsn': self.lsn,
            'type': self.entry_type.value,
            'txn_id': self.transaction_id,
            'table': self.table_name,
            'key': self.key,
            'data': self.data,
            'old_data': self.old_data,
            'ts': self.timestamp.isoformat()
        }).encode('utf-8')

        # Calculate checksum
        checksum = hashlib.crc32(payload).to_bytes(4, 'big')

        # Format: length (4 bytes) + checksum (4 bytes) + payload
        length = len(payload)
        return struct.pack('>I', length) + checksum + payload

    @classmethod
    def from_bytes(cls, data: bytes) -> Tuple['WALEntry', int]:
        """Deserialize entry from bytes."""
        length = struct.unpack('>I', data[:4])[0]
        stored_checksum = data[4:8]
        payload = data[8:8+length]

        # Verify checksum
        calculated_checksum = hashlib.crc32(payload).to_bytes(4, 'big')
        if stored_checksum != calculated_checksum:
            raise ValueError("Checksum mismatch")

        obj = json.loads(payload.decode('utf-8'))

        entry = cls(
            lsn=obj['lsn'],
            entry_type=WALEntryType(obj['type']),
            transaction_id=obj.get('txn_id'),
            table_name=obj.get('table'),
            key=obj.get('key'),
            data=obj.get('data'),
            old_data=obj.get('old_data'),
            timestamp=datetime.fromisoformat(obj['ts'])
        )
        entry.checksum = stored_checksum.hex()

        return entry, 8 + length


@dataclass
class WALConfig:
    """WAL configuration."""
    directory: str = "./wal"
    max_segment_size: int = 16 * 1024 * 1024  # 16MB
    sync_on_write: bool = True
    checkpoint_interval: int = 1000  # entries


# ============================================================================
# WRITE-AHEAD LOG
# ============================================================================

class WriteAheadLog:
    """
    Write-ahead log implementation.

    Features:
    - Durability guarantee
    - Crash recovery
    - Checkpointing
    - Segment rotation

    "Ba'el ensures no intention is lost." — Ba'el
    """

    def __init__(self, config: Optional[WALConfig] = None):
        """Initialize WAL."""
        self.config = config or WALConfig()

        # Directory
        self._directory = Path(self.config.directory)
        self._directory.mkdir(parents=True, exist_ok=True)

        # Current segment
        self._current_segment: Optional[int] = None
        self._current_file = None
        self._current_path: Optional[Path] = None

        # LSN tracking
        self._next_lsn = 0
        self._last_checkpoint_lsn = 0

        # Entries since checkpoint
        self._entries_since_checkpoint = 0

        # Thread safety
        self._lock = threading.RLock()

        # Recovery handlers
        self._recovery_handlers: Dict[WALEntryType, Callable] = {}

        # Stats
        self._stats = {
            'entries_written': 0,
            'bytes_written': 0,
            'segments_created': 0,
            'checkpoints': 0
        }

        # Initialize
        self._initialize()

        logger.info(f"WAL initialized: {self._directory}")

    def _initialize(self) -> None:
        """Initialize WAL from disk."""
        # Find existing segments
        segments = sorted(self._directory.glob("wal_*.log"))

        if segments:
            # Find highest LSN
            last_segment = segments[-1]
            self._current_segment = int(last_segment.stem.split('_')[1])

            # Read last segment to find next LSN
            try:
                entries = self._read_segment(last_segment)
                if entries:
                    self._next_lsn = entries[-1].lsn + 1
            except Exception as e:
                logger.error(f"Error reading last segment: {e}")
        else:
            self._current_segment = 0

        # Open current segment
        self._open_segment()

    def _open_segment(self) -> None:
        """Open current segment for writing."""
        segment_name = f"wal_{self._current_segment:06d}.log"
        self._current_path = self._directory / segment_name

        self._current_file = open(self._current_path, 'ab')

        if self._current_path.stat().st_size == 0:
            self._stats['segments_created'] += 1

    def _rotate_segment(self) -> None:
        """Rotate to new segment."""
        if self._current_file:
            self._current_file.close()

        self._current_segment += 1
        self._open_segment()

        logger.info(f"Rotated to segment {self._current_segment}")

    # ========================================================================
    # WRITING
    # ========================================================================

    def append(
        self,
        entry_type: WALEntryType,
        table_name: Optional[str] = None,
        key: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        old_data: Optional[Dict[str, Any]] = None,
        transaction_id: Optional[str] = None
    ) -> int:
        """
        Append entry to WAL.

        Returns:
            LSN of the entry
        """
        with self._lock:
            # Create entry
            entry = WALEntry(
                lsn=self._next_lsn,
                entry_type=entry_type,
                table_name=table_name,
                key=key,
                data=data,
                old_data=old_data,
                transaction_id=transaction_id
            )

            # Serialize
            entry_bytes = entry.to_bytes()

            # Check if need rotation
            if self._current_file.tell() + len(entry_bytes) > self.config.max_segment_size:
                self._rotate_segment()

            # Write
            self._current_file.write(entry_bytes)

            # Sync if configured
            if self.config.sync_on_write:
                self._current_file.flush()
                os.fsync(self._current_file.fileno())

            # Update tracking
            lsn = self._next_lsn
            self._next_lsn += 1
            self._entries_since_checkpoint += 1

            self._stats['entries_written'] += 1
            self._stats['bytes_written'] += len(entry_bytes)

            # Check if checkpoint needed
            if self._entries_since_checkpoint >= self.config.checkpoint_interval:
                self._write_checkpoint()

            return lsn

    def _write_checkpoint(self) -> int:
        """Write checkpoint entry."""
        lsn = self.append(WALEntryType.CHECKPOINT)
        self._last_checkpoint_lsn = lsn
        self._entries_since_checkpoint = 0
        self._stats['checkpoints'] += 1

        logger.info(f"Checkpoint at LSN {lsn}")

        return lsn

    def sync(self) -> None:
        """Force sync to disk."""
        with self._lock:
            if self._current_file:
                self._current_file.flush()
                os.fsync(self._current_file.fileno())

    # ========================================================================
    # READING
    # ========================================================================

    def _read_segment(self, path: Path) -> List[WALEntry]:
        """Read all entries from a segment."""
        entries = []

        with open(path, 'rb') as f:
            data = f.read()

        offset = 0
        while offset < len(data):
            try:
                entry, consumed = WALEntry.from_bytes(data[offset:])
                entries.append(entry)
                offset += consumed
            except Exception as e:
                logger.error(f"Error reading entry at offset {offset}: {e}")
                break

        return entries

    def read_from_lsn(
        self,
        start_lsn: int,
        end_lsn: Optional[int] = None
    ) -> List[WALEntry]:
        """
        Read entries from LSN.

        Args:
            start_lsn: Starting LSN (inclusive)
            end_lsn: Ending LSN (exclusive)

        Returns:
            List of entries
        """
        entries = []

        for segment_path in sorted(self._directory.glob("wal_*.log")):
            segment_entries = self._read_segment(segment_path)

            for entry in segment_entries:
                if entry.lsn >= start_lsn:
                    if end_lsn is not None and entry.lsn >= end_lsn:
                        return entries
                    entries.append(entry)

        return entries

    # ========================================================================
    # RECOVERY
    # ========================================================================

    def register_recovery_handler(
        self,
        entry_type: WALEntryType,
        handler: Callable[[WALEntry], None]
    ) -> None:
        """Register recovery handler for entry type."""
        self._recovery_handlers[entry_type] = handler

    async def recover(
        self,
        from_lsn: Optional[int] = None
    ) -> int:
        """
        Recover by replaying WAL entries.

        Args:
            from_lsn: Start from this LSN (default: last checkpoint)

        Returns:
            Number of entries replayed
        """
        start_lsn = from_lsn if from_lsn is not None else self._last_checkpoint_lsn

        entries = self.read_from_lsn(start_lsn)
        replayed = 0

        for entry in entries:
            # Skip checkpoints
            if entry.entry_type == WALEntryType.CHECKPOINT:
                continue

            handler = self._recovery_handlers.get(entry.entry_type)

            if handler:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(entry)
                    else:
                        await asyncio.to_thread(handler, entry)

                    replayed += 1

                except Exception as e:
                    logger.error(f"Recovery error at LSN {entry.lsn}: {e}")

        logger.info(f"Recovered {replayed} entries from LSN {start_lsn}")

        return replayed

    # ========================================================================
    # CLEANUP
    # ========================================================================

    def truncate_before(self, lsn: int) -> int:
        """
        Remove entries before LSN.

        Args:
            lsn: Truncate before this LSN

        Returns:
            Number of segments removed
        """
        removed = 0

        for segment_path in sorted(self._directory.glob("wal_*.log")):
            if segment_path == self._current_path:
                continue

            entries = self._read_segment(segment_path)

            if entries and entries[-1].lsn < lsn:
                segment_path.unlink()
                removed += 1

        logger.info(f"Truncated {removed} segments before LSN {lsn}")

        return removed

    # ========================================================================
    # LIFECYCLE
    # ========================================================================

    def close(self) -> None:
        """Close WAL."""
        with self._lock:
            if self._current_file:
                self.sync()
                self._current_file.close()
                self._current_file = None

        logger.info("WAL closed")

    # ========================================================================
    # STATS
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get WAL statistics."""
        return {
            'current_lsn': self._next_lsn,
            'last_checkpoint_lsn': self._last_checkpoint_lsn,
            'current_segment': self._current_segment,
            'directory': str(self._directory),
            **self._stats
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

wal = None


def get_wal(config: Optional[WALConfig] = None) -> WriteAheadLog:
    """Get or create WAL instance."""
    global wal
    if wal is None:
        wal = WriteAheadLog(config)
    return wal


def append_to_wal(entry_type: WALEntryType, **kwargs) -> int:
    """Append to WAL."""
    return get_wal().append(entry_type, **kwargs)
