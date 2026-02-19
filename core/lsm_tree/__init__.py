"""
BAEL LSM Tree Engine Implementation
====================================

Log-Structured Merge Tree for write-optimized storage.

"Ba'el writes with perfect efficiency." — Ba'el
"""

import bisect
import hashlib
import json
import logging
import os
import shutil
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, Generic, Iterator, List, Optional, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("BAEL.LSMTree")

K = TypeVar('K')
V = TypeVar('V')


# ============================================================================
# ENUMS
# ============================================================================

class CompactionStrategy(Enum):
    """Compaction strategies."""
    SIZE_TIERED = "size_tiered"
    LEVELED = "leveled"
    FIFO = "fifo"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class LSMConfig:
    """LSM Tree configuration."""
    memtable_size: int = 4 * 1024 * 1024  # 4MB
    level0_size: int = 10 * 1024 * 1024   # 10MB
    level_ratio: int = 10                   # Size ratio between levels
    max_levels: int = 7
    bloom_filter_bits: int = 10
    compaction_strategy: CompactionStrategy = CompactionStrategy.SIZE_TIERED
    data_dir: Optional[str] = None


@dataclass
class SSTableMeta:
    """SSTable metadata."""
    id: str
    level: int
    min_key: Any
    max_key: Any
    size: int
    entry_count: int
    created_at: float = field(default_factory=time.time)


class MemTable(Generic[K, V]):
    """In-memory write buffer."""

    def __init__(self, max_size: int = 4 * 1024 * 1024):
        """Initialize memtable."""
        self._data: OrderedDict[K, Tuple[V, bool]] = OrderedDict()  # (value, deleted)
        self._size = 0
        self._max_size = max_size
        self._lock = threading.RLock()

    def put(self, key: K, value: V) -> None:
        """Put a key-value pair."""
        with self._lock:
            old_size = self._estimate_size(key, self._data.get(key, (None, False))[0])
            new_size = self._estimate_size(key, value)

            self._data[key] = (value, False)
            self._size += new_size - old_size

    def delete(self, key: K) -> None:
        """Mark key as deleted (tombstone)."""
        with self._lock:
            self._data[key] = (None, True)

    def get(self, key: K) -> Tuple[Optional[V], bool, bool]:
        """
        Get value for key.

        Returns:
            (value, found, deleted)
        """
        with self._lock:
            if key in self._data:
                value, deleted = self._data[key]
                return value, True, deleted
            return None, False, False

    def is_full(self) -> bool:
        """Check if memtable is full."""
        return self._size >= self._max_size

    def items(self) -> List[Tuple[K, V, bool]]:
        """Get all items sorted by key."""
        with self._lock:
            return [(k, v, d) for k, (v, d) in sorted(self._data.items())]

    def clear(self) -> None:
        """Clear memtable."""
        with self._lock:
            self._data.clear()
            self._size = 0

    def __len__(self) -> int:
        return len(self._data)

    def _estimate_size(self, key: Any, value: Any) -> int:
        """Estimate size of key-value pair."""
        if value is None:
            return 0
        return len(str(key)) + len(str(value))


class BloomFilter:
    """Simple bloom filter for quick lookups."""

    def __init__(self, capacity: int = 10000, error_rate: float = 0.01):
        """Initialize bloom filter."""
        import math

        self.capacity = capacity
        self.error_rate = error_rate

        # Calculate optimal size
        self.size = int(-capacity * math.log(error_rate) / (math.log(2) ** 2))
        self.hash_count = int(self.size / capacity * math.log(2))

        self.bit_array = [False] * self.size

    def add(self, key: Any) -> None:
        """Add key to filter."""
        for i in range(self.hash_count):
            idx = self._hash(key, i)
            self.bit_array[idx] = True

    def might_contain(self, key: Any) -> bool:
        """Check if key might be in filter (false positives possible)."""
        for i in range(self.hash_count):
            idx = self._hash(key, i)
            if not self.bit_array[idx]:
                return False
        return True

    def _hash(self, key: Any, seed: int) -> int:
        """Hash key with seed."""
        key_bytes = str(key).encode()
        h = hashlib.md5(key_bytes + str(seed).encode()).hexdigest()
        return int(h, 16) % self.size


class SSTable(Generic[K, V]):
    """Sorted String Table (on-disk)."""

    def __init__(
        self,
        meta: SSTableMeta,
        data: Optional[List[Tuple[K, V, bool]]] = None,
        data_dir: Optional[Path] = None
    ):
        """Initialize SSTable."""
        self.meta = meta
        self._data_dir = data_dir

        # In-memory for now (would be on disk in production)
        self._data: List[Tuple[K, V, bool]] = data or []
        self._keys: List[K] = [d[0] for d in self._data]

        # Bloom filter
        self._bloom = BloomFilter(len(self._data) + 1)
        for key in self._keys:
            self._bloom.add(key)

    def get(self, key: K) -> Tuple[Optional[V], bool, bool]:
        """
        Get value for key.

        Returns:
            (value, found, deleted)
        """
        # Check bloom filter first
        if not self._bloom.might_contain(key):
            return None, False, False

        # Binary search
        idx = bisect.bisect_left(self._keys, key)

        if idx < len(self._keys) and self._keys[idx] == key:
            _, value, deleted = self._data[idx]
            return value, True, deleted

        return None, False, False

    def range(
        self,
        start: Optional[K] = None,
        end: Optional[K] = None
    ) -> Iterator[Tuple[K, V, bool]]:
        """Range query."""
        start_idx = 0
        end_idx = len(self._data)

        if start is not None:
            start_idx = bisect.bisect_left(self._keys, start)

        if end is not None:
            end_idx = bisect.bisect_right(self._keys, end)

        for i in range(start_idx, end_idx):
            yield self._data[i]

    def items(self) -> Iterator[Tuple[K, V, bool]]:
        """Iterate all items."""
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)


# ============================================================================
# LSM TREE ENGINE
# ============================================================================

class LSMTreeEngine(Generic[K, V]):
    """
    Log-Structured Merge Tree.

    Features:
    - Fast writes (append-only)
    - Compaction
    - Bloom filters
    - Range queries

    "Ba'el writes wisdom with perfect efficiency." — Ba'el
    """

    def __init__(self, config: Optional[LSMConfig] = None):
        """Initialize LSM Tree."""
        self.config = config or LSMConfig()

        # Data directory
        if self.config.data_dir:
            self._data_dir = Path(self.config.data_dir)
            self._data_dir.mkdir(parents=True, exist_ok=True)
        else:
            self._data_dir = None

        # Active memtable
        self._memtable: MemTable[K, V] = MemTable(self.config.memtable_size)

        # Immutable memtables waiting to be flushed
        self._immutable: List[MemTable[K, V]] = []

        # SSTables organized by level
        self._levels: List[List[SSTable[K, V]]] = [[] for _ in range(self.config.max_levels)]

        # Stats
        self._stats = {
            'writes': 0,
            'reads': 0,
            'flushes': 0,
            'compactions': 0
        }

        # Sequence number for SSTable IDs
        self._sstable_seq = 0

        # Thread safety
        self._lock = threading.RLock()

        logger.info(
            f"LSM Tree initialized "
            f"(memtable_size={self.config.memtable_size})"
        )

    # ========================================================================
    # BASIC OPERATIONS
    # ========================================================================

    def put(self, key: K, value: V) -> None:
        """
        Put a key-value pair.

        Args:
            key: Key
            value: Value
        """
        with self._lock:
            self._memtable.put(key, value)
            self._stats['writes'] += 1

            if self._memtable.is_full():
                self._flush_memtable()

    def get(self, key: K) -> Optional[V]:
        """
        Get value for key.

        Args:
            key: Key to get

        Returns:
            Value if found, None otherwise
        """
        with self._lock:
            self._stats['reads'] += 1

            # Check active memtable
            value, found, deleted = self._memtable.get(key)
            if found:
                return None if deleted else value

            # Check immutable memtables
            for imm in reversed(self._immutable):
                value, found, deleted = imm.get(key)
                if found:
                    return None if deleted else value

            # Check SSTables level by level
            for level in self._levels:
                for sstable in reversed(level):
                    value, found, deleted = sstable.get(key)
                    if found:
                        return None if deleted else value

            return None

    def delete(self, key: K) -> None:
        """
        Delete a key.

        Args:
            key: Key to delete
        """
        with self._lock:
            self._memtable.delete(key)
            self._stats['writes'] += 1

            if self._memtable.is_full():
                self._flush_memtable()

    # ========================================================================
    # RANGE QUERIES
    # ========================================================================

    def range(
        self,
        start: Optional[K] = None,
        end: Optional[K] = None
    ) -> Iterator[Tuple[K, V]]:
        """
        Range query.

        Args:
            start: Start key (inclusive)
            end: End key (inclusive)

        Yields:
            (key, value) pairs
        """
        with self._lock:
            # Collect all iterators
            merged = self._merge_iterators(start, end)

            seen: set = set()
            for key, value, deleted in merged:
                if key in seen:
                    continue
                seen.add(key)

                if not deleted:
                    yield key, value

    def _merge_iterators(
        self,
        start: Optional[K],
        end: Optional[K]
    ) -> Iterator[Tuple[K, V, bool]]:
        """Merge all iterators in order."""
        # Collect all data sources
        all_items: List[Tuple[K, V, bool]] = []

        # From memtable
        for key, value, deleted in self._memtable.items():
            if start is not None and key < start:
                continue
            if end is not None and key > end:
                continue
            all_items.append((key, value, deleted))

        # From immutable memtables
        for imm in self._immutable:
            for key, value, deleted in imm.items():
                if start is not None and key < start:
                    continue
                if end is not None and key > end:
                    continue
                all_items.append((key, value, deleted))

        # From SSTables
        for level in self._levels:
            for sstable in level:
                for key, value, deleted in sstable.range(start, end):
                    all_items.append((key, value, deleted))

        # Sort by key
        all_items.sort(key=lambda x: x[0])

        return iter(all_items)

    # ========================================================================
    # FLUSH & COMPACTION
    # ========================================================================

    def _flush_memtable(self) -> None:
        """Flush memtable to SSTable."""
        if not self._memtable:
            return

        # Make memtable immutable
        imm = self._memtable
        self._immutable.append(imm)
        self._memtable = MemTable(self.config.memtable_size)

        # Create SSTable
        items = imm.items()
        if items:
            sstable = self._create_sstable(items, level=0)
            self._levels[0].append(sstable)

        self._immutable.remove(imm)
        self._stats['flushes'] += 1

        # Maybe compact
        self._maybe_compact()

        logger.debug(f"Flushed memtable to SSTable")

    def _create_sstable(
        self,
        items: List[Tuple[K, V, bool]],
        level: int
    ) -> SSTable[K, V]:
        """Create a new SSTable."""
        self._sstable_seq += 1

        meta = SSTableMeta(
            id=f"sst_{self._sstable_seq:06d}",
            level=level,
            min_key=items[0][0] if items else None,
            max_key=items[-1][0] if items else None,
            size=sum(len(str(k)) + len(str(v)) for k, v, _ in items),
            entry_count=len(items)
        )

        return SSTable(meta, items, self._data_dir)

    def _maybe_compact(self) -> None:
        """Check if compaction is needed."""
        if self.config.compaction_strategy == CompactionStrategy.SIZE_TIERED:
            self._size_tiered_compaction()
        elif self.config.compaction_strategy == CompactionStrategy.LEVELED:
            self._leveled_compaction()

    def _size_tiered_compaction(self) -> None:
        """Size-tiered compaction strategy."""
        for level in range(len(self._levels) - 1):
            tables = self._levels[level]

            # Compact when we have too many tables at a level
            if len(tables) >= 4:
                self._compact_level(level)

    def _leveled_compaction(self) -> None:
        """Leveled compaction strategy."""
        level_sizes = [sum(t.meta.size for t in level) for level in self._levels]

        for level in range(len(self._levels) - 1):
            max_size = self.config.level0_size * (self.config.level_ratio ** level)

            if level_sizes[level] > max_size:
                self._compact_level(level)

    def _compact_level(self, level: int) -> None:
        """Compact a level."""
        if level >= len(self._levels) - 1:
            return

        tables = self._levels[level]
        if not tables:
            return

        # Merge all tables in level
        all_items: Dict[K, Tuple[V, bool]] = {}

        for table in tables:
            for key, value, deleted in table.items():
                # Keep most recent
                all_items[key] = (value, deleted)

        # Sort and create new SSTable
        sorted_items = [(k, v, d) for k, (v, d) in sorted(all_items.items())]

        if sorted_items:
            new_table = self._create_sstable(sorted_items, level + 1)
            self._levels[level + 1].append(new_table)

        # Clear current level
        self._levels[level] = []
        self._stats['compactions'] += 1

        logger.debug(f"Compacted level {level} to level {level + 1}")

    def force_flush(self) -> None:
        """Force flush memtable."""
        with self._lock:
            if len(self._memtable) > 0:
                self._flush_memtable()

    def force_compact(self) -> None:
        """Force full compaction."""
        with self._lock:
            self.force_flush()

            for level in range(len(self._levels) - 1):
                if self._levels[level]:
                    self._compact_level(level)

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def __contains__(self, key: K) -> bool:
        """Check if key exists."""
        return self.get(key) is not None

    def __getitem__(self, key: K) -> V:
        """Get value by key."""
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value

    def __setitem__(self, key: K, value: V) -> None:
        """Set value by key."""
        self.put(key, value)

    def __delitem__(self, key: K) -> None:
        """Delete by key."""
        self.delete(key)

    def __len__(self) -> int:
        """Approximate count."""
        count = len(self._memtable)
        for imm in self._immutable:
            count += len(imm)
        for level in self._levels:
            for table in level:
                count += len(table)
        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get tree statistics."""
        level_info = []
        for i, level in enumerate(self._levels):
            if level:
                level_info.append({
                    'level': i,
                    'tables': len(level),
                    'size': sum(t.meta.size for t in level)
                })

        return {
            **self._stats,
            'memtable_size': len(self._memtable),
            'immutable_count': len(self._immutable),
            'levels': level_info,
            'total_sstables': sum(len(l) for l in self._levels)
        }

    def clear(self) -> None:
        """Clear all data."""
        with self._lock:
            self._memtable.clear()
            self._immutable.clear()
            self._levels = [[] for _ in range(self.config.max_levels)]
            self._stats = {'writes': 0, 'reads': 0, 'flushes': 0, 'compactions': 0}


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_lsm_tree(
    memtable_size: int = 4 * 1024 * 1024,
    **kwargs
) -> LSMTreeEngine:
    """Create a new LSM Tree."""
    config = LSMConfig(memtable_size=memtable_size, **kwargs)
    return LSMTreeEngine(config)


def create_small_lsm() -> LSMTreeEngine:
    """Create a small LSM Tree for testing."""
    return create_lsm_tree(memtable_size=1024)


def create_write_optimized_lsm() -> LSMTreeEngine:
    """Create a write-optimized LSM Tree."""
    return create_lsm_tree(
        memtable_size=16 * 1024 * 1024,
        compaction_strategy=CompactionStrategy.SIZE_TIERED
    )
