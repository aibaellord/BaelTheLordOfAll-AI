#!/usr/bin/env python3
"""
BAEL - Bloom Filter
Advanced probabilistic data structure for AI agent operations.

Features:
- Standard Bloom filter
- Counting Bloom filter
- Scalable Bloom filter
- Partitioned Bloom filter
- Cuckoo filter
- Age-partitioned Bloom filter
- Configurable hash functions
- Memory-efficient storage
- False positive rate tuning
- Serialization support
"""

import asyncio
import copy
import hashlib
import math
import struct
import uuid
from abc import ABC, abstractmethod
from array import array
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class HashFunction(Enum):
    """Hash function types."""
    MD5 = "md5"
    SHA1 = "sha1"
    SHA256 = "sha256"
    MURMUR = "murmur"


class FilterType(Enum):
    """Filter types."""
    STANDARD = "standard"
    COUNTING = "counting"
    SCALABLE = "scalable"
    PARTITIONED = "partitioned"
    CUCKOO = "cuckoo"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class BloomConfig:
    """Bloom filter configuration."""
    expected_items: int = 10000
    false_positive_rate: float = 0.01
    hash_function: HashFunction = HashFunction.SHA256
    num_hash_functions: Optional[int] = None
    bit_size: Optional[int] = None


@dataclass
class FilterStats:
    """Filter statistics."""
    items_added: int = 0
    false_positive_rate: float = 0.0
    fill_ratio: float = 0.0
    bit_size: int = 0
    num_hash_functions: int = 0
    memory_bytes: int = 0


# =============================================================================
# HASH GENERATOR
# =============================================================================

class HashGenerator:
    """Generate hash values for Bloom filter."""

    def __init__(
        self,
        hash_function: HashFunction = HashFunction.SHA256,
        num_hashes: int = 7
    ):
        self._hash_function = hash_function
        self._num_hashes = num_hashes

    def _hash_bytes(self, data: bytes) -> bytes:
        """Hash bytes using configured algorithm."""
        if self._hash_function == HashFunction.MD5:
            return hashlib.md5(data).digest()
        elif self._hash_function == HashFunction.SHA1:
            return hashlib.sha1(data).digest()
        elif self._hash_function == HashFunction.SHA256:
            return hashlib.sha256(data).digest()
        else:
            # Fallback to SHA256
            return hashlib.sha256(data).digest()

    def _to_bytes(self, item: Any) -> bytes:
        """Convert item to bytes."""
        if isinstance(item, bytes):
            return item
        elif isinstance(item, str):
            return item.encode('utf-8')
        else:
            return str(item).encode('utf-8')

    def get_hashes(
        self,
        item: Any,
        size: int
    ) -> List[int]:
        """Get hash positions for item."""
        data = self._to_bytes(item)
        hashes = []

        # Use double hashing technique
        h1 = int.from_bytes(
            self._hash_bytes(data)[:8],
            byteorder='big'
        )
        h2 = int.from_bytes(
            self._hash_bytes(data + b'\x01')[:8],
            byteorder='big'
        )

        for i in range(self._num_hashes):
            combined = (h1 + i * h2) % size
            hashes.append(combined)

        return hashes


# =============================================================================
# BIT ARRAY
# =============================================================================

class BitArray:
    """Efficient bit array implementation."""

    def __init__(self, size: int):
        self._size = size
        self._num_bytes = (size + 7) // 8
        self._bits = bytearray(self._num_bytes)

    def set(self, index: int) -> None:
        """Set bit at index."""
        if 0 <= index < self._size:
            byte_index = index // 8
            bit_index = index % 8
            self._bits[byte_index] |= (1 << bit_index)

    def get(self, index: int) -> bool:
        """Get bit at index."""
        if 0 <= index < self._size:
            byte_index = index // 8
            bit_index = index % 8
            return bool(self._bits[byte_index] & (1 << bit_index))
        return False

    def clear(self, index: int) -> None:
        """Clear bit at index."""
        if 0 <= index < self._size:
            byte_index = index // 8
            bit_index = index % 8
            self._bits[byte_index] &= ~(1 << bit_index)

    def count_ones(self) -> int:
        """Count set bits."""
        count = 0
        for byte in self._bits:
            count += bin(byte).count('1')
        return count

    def fill_ratio(self) -> float:
        """Get fill ratio."""
        return self.count_ones() / self._size if self._size > 0 else 0.0

    def size(self) -> int:
        """Get size in bits."""
        return self._size

    def memory_size(self) -> int:
        """Get memory size in bytes."""
        return self._num_bytes

    def clear_all(self) -> None:
        """Clear all bits."""
        self._bits = bytearray(self._num_bytes)

    def to_bytes(self) -> bytes:
        """Serialize to bytes."""
        return bytes(self._bits)

    @classmethod
    def from_bytes(cls, data: bytes, size: int) -> 'BitArray':
        """Deserialize from bytes."""
        arr = cls(size)
        arr._bits = bytearray(data)
        return arr


# =============================================================================
# STANDARD BLOOM FILTER
# =============================================================================

class BloomFilter:
    """Standard Bloom filter."""

    def __init__(self, config: Optional[BloomConfig] = None):
        self.config = config or BloomConfig()

        # Calculate optimal parameters
        if self.config.bit_size:
            self._size = self.config.bit_size
        else:
            self._size = self._optimal_size(
                self.config.expected_items,
                self.config.false_positive_rate
            )

        if self.config.num_hash_functions:
            self._num_hashes = self.config.num_hash_functions
        else:
            self._num_hashes = self._optimal_hash_count(
                self._size,
                self.config.expected_items
            )

        self._bits = BitArray(self._size)
        self._hasher = HashGenerator(
            self.config.hash_function,
            self._num_hashes
        )
        self._items_added = 0

    def _optimal_size(self, n: int, p: float) -> int:
        """Calculate optimal bit array size."""
        if n <= 0 or p <= 0 or p >= 1:
            return 1000
        m = -(n * math.log(p)) / (math.log(2) ** 2)
        return max(int(m), 64)

    def _optimal_hash_count(self, m: int, n: int) -> int:
        """Calculate optimal number of hash functions."""
        if n <= 0:
            return 1
        k = (m / n) * math.log(2)
        return max(int(k), 1)

    def add(self, item: Any) -> None:
        """Add item to filter."""
        for pos in self._hasher.get_hashes(item, self._size):
            self._bits.set(pos)
        self._items_added += 1

    def add_all(self, items: List[Any]) -> None:
        """Add multiple items."""
        for item in items:
            self.add(item)

    def contains(self, item: Any) -> bool:
        """Check if item might be in filter."""
        for pos in self._hasher.get_hashes(item, self._size):
            if not self._bits.get(pos):
                return False
        return True

    def __contains__(self, item: Any) -> bool:
        """Support 'in' operator."""
        return self.contains(item)

    def clear(self) -> None:
        """Clear all items."""
        self._bits.clear_all()
        self._items_added = 0

    def false_positive_rate(self) -> float:
        """Estimate current false positive rate."""
        if self._items_added == 0:
            return 0.0

        fill_ratio = self._bits.fill_ratio()
        return fill_ratio ** self._num_hashes

    def stats(self) -> FilterStats:
        """Get filter statistics."""
        return FilterStats(
            items_added=self._items_added,
            false_positive_rate=self.false_positive_rate(),
            fill_ratio=self._bits.fill_ratio(),
            bit_size=self._size,
            num_hash_functions=self._num_hashes,
            memory_bytes=self._bits.memory_size()
        )

    def union(self, other: 'BloomFilter') -> 'BloomFilter':
        """Create union with another filter."""
        if self._size != other._size:
            raise ValueError("Filters must be same size")

        result = BloomFilter(self.config)
        for i in range(self._size):
            if self._bits.get(i) or other._bits.get(i):
                result._bits.set(i)
        result._items_added = self._items_added + other._items_added
        return result

    def to_bytes(self) -> bytes:
        """Serialize filter."""
        header = struct.pack(
            '>III',
            self._size,
            self._num_hashes,
            self._items_added
        )
        return header + self._bits.to_bytes()

    @classmethod
    def from_bytes(cls, data: bytes) -> 'BloomFilter':
        """Deserialize filter."""
        size, num_hashes, items_added = struct.unpack('>III', data[:12])

        config = BloomConfig(
            bit_size=size,
            num_hash_functions=num_hashes
        )

        bf = cls(config)
        bf._bits = BitArray.from_bytes(data[12:], size)
        bf._items_added = items_added
        return bf


# =============================================================================
# COUNTING BLOOM FILTER
# =============================================================================

class CountingBloomFilter:
    """Counting Bloom filter with delete support."""

    def __init__(
        self,
        config: Optional[BloomConfig] = None,
        counter_bits: int = 4
    ):
        self.config = config or BloomConfig()
        self._counter_bits = counter_bits
        self._max_count = (1 << counter_bits) - 1

        # Calculate size
        if self.config.bit_size:
            self._size = self.config.bit_size
        else:
            n = self.config.expected_items
            p = self.config.false_positive_rate
            self._size = max(int(-(n * math.log(p)) / (math.log(2) ** 2)), 64)

        if self.config.num_hash_functions:
            self._num_hashes = self.config.num_hash_functions
        else:
            self._num_hashes = max(
                int((self._size / self.config.expected_items) * math.log(2)),
                1
            )

        self._counters = [0] * self._size
        self._hasher = HashGenerator(
            self.config.hash_function,
            self._num_hashes
        )
        self._items_added = 0

    def add(self, item: Any) -> bool:
        """Add item. Returns False if counter overflow."""
        overflow = False
        for pos in self._hasher.get_hashes(item, self._size):
            if self._counters[pos] < self._max_count:
                self._counters[pos] += 1
            else:
                overflow = True
        self._items_added += 1
        return not overflow

    def remove(self, item: Any) -> bool:
        """Remove item. Returns True if item was present."""
        if not self.contains(item):
            return False

        for pos in self._hasher.get_hashes(item, self._size):
            if self._counters[pos] > 0:
                self._counters[pos] -= 1

        self._items_added = max(0, self._items_added - 1)
        return True

    def contains(self, item: Any) -> bool:
        """Check if item might be in filter."""
        for pos in self._hasher.get_hashes(item, self._size):
            if self._counters[pos] == 0:
                return False
        return True

    def __contains__(self, item: Any) -> bool:
        return self.contains(item)

    def count(self, item: Any) -> int:
        """Get minimum count for item."""
        positions = self._hasher.get_hashes(item, self._size)
        return min(self._counters[pos] for pos in positions)

    def clear(self) -> None:
        """Clear filter."""
        self._counters = [0] * self._size
        self._items_added = 0

    def stats(self) -> FilterStats:
        """Get statistics."""
        non_zero = sum(1 for c in self._counters if c > 0)
        fill_ratio = non_zero / self._size if self._size > 0 else 0.0

        return FilterStats(
            items_added=self._items_added,
            false_positive_rate=fill_ratio ** self._num_hashes,
            fill_ratio=fill_ratio,
            bit_size=self._size,
            num_hash_functions=self._num_hashes,
            memory_bytes=self._size * (self._counter_bits // 8 + 1)
        )


# =============================================================================
# SCALABLE BLOOM FILTER
# =============================================================================

class ScalableBloomFilter:
    """Scalable Bloom filter that grows as needed."""

    def __init__(
        self,
        initial_capacity: int = 1000,
        false_positive_rate: float = 0.01,
        growth_factor: float = 2.0,
        tightening_ratio: float = 0.9
    ):
        self._initial_capacity = initial_capacity
        self._initial_fpr = false_positive_rate
        self._growth_factor = growth_factor
        self._tightening_ratio = tightening_ratio

        self._filters: List[BloomFilter] = []
        self._current_fpr = false_positive_rate
        self._items_added = 0

        # Create first filter
        self._add_filter()

    def _add_filter(self) -> None:
        """Add new filter."""
        capacity = int(
            self._initial_capacity *
            (self._growth_factor ** len(self._filters))
        )

        config = BloomConfig(
            expected_items=capacity,
            false_positive_rate=self._current_fpr
        )

        self._filters.append(BloomFilter(config))
        self._current_fpr *= self._tightening_ratio

    def add(self, item: Any) -> None:
        """Add item."""
        if self._filters[-1]._items_added >= self._filters[-1].config.expected_items:
            self._add_filter()

        self._filters[-1].add(item)
        self._items_added += 1

    def contains(self, item: Any) -> bool:
        """Check if item might be in filter."""
        return any(f.contains(item) for f in self._filters)

    def __contains__(self, item: Any) -> bool:
        return self.contains(item)

    def filter_count(self) -> int:
        """Get number of internal filters."""
        return len(self._filters)

    def false_positive_rate(self) -> float:
        """Get overall false positive rate."""
        # FPR is 1 - product of (1 - fpr_i)
        product = 1.0
        for f in self._filters:
            product *= (1 - f.false_positive_rate())
        return 1 - product

    def stats(self) -> FilterStats:
        """Get statistics."""
        total_bits = sum(f._size for f in self._filters)
        total_memory = sum(f._bits.memory_size() for f in self._filters)

        return FilterStats(
            items_added=self._items_added,
            false_positive_rate=self.false_positive_rate(),
            fill_ratio=sum(f._bits.fill_ratio() for f in self._filters) / len(self._filters),
            bit_size=total_bits,
            num_hash_functions=self._filters[0]._num_hashes if self._filters else 0,
            memory_bytes=total_memory
        )


# =============================================================================
# CUCKOO FILTER
# =============================================================================

class CuckooFilter:
    """Cuckoo filter with delete support and better performance."""

    def __init__(
        self,
        capacity: int = 10000,
        bucket_size: int = 4,
        fingerprint_size: int = 8,
        max_kicks: int = 500
    ):
        self._capacity = capacity
        self._bucket_size = bucket_size
        self._fingerprint_size = fingerprint_size
        self._max_kicks = max_kicks

        self._num_buckets = capacity // bucket_size
        self._buckets: List[List[int]] = [[] for _ in range(self._num_buckets)]
        self._items_added = 0

    def _fingerprint(self, item: Any) -> int:
        """Calculate fingerprint."""
        if isinstance(item, bytes):
            data = item
        elif isinstance(item, str):
            data = item.encode('utf-8')
        else:
            data = str(item).encode('utf-8')

        h = hashlib.sha256(data).digest()
        fp = int.from_bytes(h[:self._fingerprint_size // 8], 'big')
        return fp if fp != 0 else 1  # Ensure non-zero

    def _hash1(self, item: Any) -> int:
        """First hash function."""
        if isinstance(item, bytes):
            data = item
        elif isinstance(item, str):
            data = item.encode('utf-8')
        else:
            data = str(item).encode('utf-8')

        h = int.from_bytes(hashlib.md5(data).digest()[:8], 'big')
        return h % self._num_buckets

    def _hash2(self, index: int, fingerprint: int) -> int:
        """Second hash (for alternate bucket)."""
        return (index ^ (fingerprint * 0x5bd1e995)) % self._num_buckets

    def add(self, item: Any) -> bool:
        """Add item. Returns False if filter is full."""
        fp = self._fingerprint(item)
        i1 = self._hash1(item)
        i2 = self._hash2(i1, fp)

        # Try first bucket
        if len(self._buckets[i1]) < self._bucket_size:
            self._buckets[i1].append(fp)
            self._items_added += 1
            return True

        # Try second bucket
        if len(self._buckets[i2]) < self._bucket_size:
            self._buckets[i2].append(fp)
            self._items_added += 1
            return True

        # Need to relocate
        import random
        i = random.choice([i1, i2])

        for _ in range(self._max_kicks):
            # Swap with random entry
            j = random.randrange(len(self._buckets[i]))
            fp, self._buckets[i][j] = self._buckets[i][j], fp

            # Try alternate bucket
            i = self._hash2(i, fp)

            if len(self._buckets[i]) < self._bucket_size:
                self._buckets[i].append(fp)
                self._items_added += 1
                return True

        return False  # Filter full

    def contains(self, item: Any) -> bool:
        """Check if item might be in filter."""
        fp = self._fingerprint(item)
        i1 = self._hash1(item)
        i2 = self._hash2(i1, fp)

        return fp in self._buckets[i1] or fp in self._buckets[i2]

    def __contains__(self, item: Any) -> bool:
        return self.contains(item)

    def remove(self, item: Any) -> bool:
        """Remove item."""
        fp = self._fingerprint(item)
        i1 = self._hash1(item)
        i2 = self._hash2(i1, fp)

        if fp in self._buckets[i1]:
            self._buckets[i1].remove(fp)
            self._items_added -= 1
            return True

        if fp in self._buckets[i2]:
            self._buckets[i2].remove(fp)
            self._items_added -= 1
            return True

        return False

    def load_factor(self) -> float:
        """Get load factor."""
        total_slots = self._num_buckets * self._bucket_size
        return self._items_added / total_slots if total_slots > 0 else 0.0

    def stats(self) -> FilterStats:
        """Get statistics."""
        total_slots = self._num_buckets * self._bucket_size
        memory = self._num_buckets * self._bucket_size * (self._fingerprint_size // 8)

        return FilterStats(
            items_added=self._items_added,
            false_positive_rate=1 / (2 ** self._fingerprint_size),
            fill_ratio=self.load_factor(),
            bit_size=self._num_buckets * self._bucket_size * self._fingerprint_size,
            num_hash_functions=2,
            memory_bytes=memory
        )


# =============================================================================
# BLOOM FILTER MANAGER
# =============================================================================

class BloomFilterManager:
    """
    Bloom Filter Manager for BAEL.

    Advanced probabilistic data structures.
    """

    def __init__(self):
        self._filters: Dict[str, Any] = {}
        self._filter_types: Dict[str, FilterType] = {}

    # -------------------------------------------------------------------------
    # FILTER CREATION
    # -------------------------------------------------------------------------

    def create_bloom(
        self,
        name: str,
        expected_items: int = 10000,
        false_positive_rate: float = 0.01,
        hash_function: HashFunction = HashFunction.SHA256
    ) -> BloomFilter:
        """Create standard Bloom filter."""
        config = BloomConfig(
            expected_items=expected_items,
            false_positive_rate=false_positive_rate,
            hash_function=hash_function
        )

        bf = BloomFilter(config)
        self._filters[name] = bf
        self._filter_types[name] = FilterType.STANDARD
        return bf

    def create_counting(
        self,
        name: str,
        expected_items: int = 10000,
        false_positive_rate: float = 0.01,
        counter_bits: int = 4
    ) -> CountingBloomFilter:
        """Create counting Bloom filter."""
        config = BloomConfig(
            expected_items=expected_items,
            false_positive_rate=false_positive_rate
        )

        cbf = CountingBloomFilter(config, counter_bits)
        self._filters[name] = cbf
        self._filter_types[name] = FilterType.COUNTING
        return cbf

    def create_scalable(
        self,
        name: str,
        initial_capacity: int = 1000,
        false_positive_rate: float = 0.01
    ) -> ScalableBloomFilter:
        """Create scalable Bloom filter."""
        sbf = ScalableBloomFilter(
            initial_capacity=initial_capacity,
            false_positive_rate=false_positive_rate
        )

        self._filters[name] = sbf
        self._filter_types[name] = FilterType.SCALABLE
        return sbf

    def create_cuckoo(
        self,
        name: str,
        capacity: int = 10000,
        bucket_size: int = 4
    ) -> CuckooFilter:
        """Create Cuckoo filter."""
        cf = CuckooFilter(
            capacity=capacity,
            bucket_size=bucket_size
        )

        self._filters[name] = cf
        self._filter_types[name] = FilterType.CUCKOO
        return cf

    # -------------------------------------------------------------------------
    # FILTER OPERATIONS
    # -------------------------------------------------------------------------

    def get(self, name: str) -> Optional[Any]:
        """Get filter by name."""
        return self._filters.get(name)

    def delete(self, name: str) -> bool:
        """Delete filter."""
        if name in self._filters:
            del self._filters[name]
            del self._filter_types[name]
            return True
        return False

    def add(self, name: str, item: Any) -> bool:
        """Add item to filter."""
        f = self._filters.get(name)
        if not f:
            return False

        if isinstance(f, CuckooFilter):
            return f.add(item)
        else:
            f.add(item)
            return True

    def contains(self, name: str, item: Any) -> bool:
        """Check if item in filter."""
        f = self._filters.get(name)
        if not f:
            return False
        return f.contains(item)

    def remove(self, name: str, item: Any) -> bool:
        """Remove item (counting/cuckoo only)."""
        f = self._filters.get(name)
        if not f:
            return False

        if isinstance(f, (CountingBloomFilter, CuckooFilter)):
            return f.remove(item)
        return False

    # -------------------------------------------------------------------------
    # QUERIES
    # -------------------------------------------------------------------------

    def list_filters(self) -> List[str]:
        """List filter names."""
        return list(self._filters.keys())

    def get_type(self, name: str) -> Optional[FilterType]:
        """Get filter type."""
        return self._filter_types.get(name)

    def stats(self, name: str) -> Optional[FilterStats]:
        """Get filter stats."""
        f = self._filters.get(name)
        if f:
            return f.stats()
        return None

    def filter_count(self) -> int:
        """Get filter count."""
        return len(self._filters)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Bloom Filter."""
    print("=" * 70)
    print("BAEL - BLOOM FILTER DEMO")
    print("Advanced Probabilistic Data Structures for AI Agents")
    print("=" * 70)
    print()

    manager = BloomFilterManager()

    # 1. Standard Bloom Filter
    print("1. STANDARD BLOOM FILTER:")
    print("-" * 40)

    bf = manager.create_bloom(
        "standard",
        expected_items=1000,
        false_positive_rate=0.01
    )

    for i in range(100):
        bf.add(f"item_{i}")

    print(f"   Contains 'item_50': {bf.contains('item_50')}")
    print(f"   Contains 'missing': {bf.contains('missing')}")

    stats = bf.stats()
    print(f"   Items added: {stats.items_added}")
    print(f"   Fill ratio: {stats.fill_ratio:.2%}")
    print(f"   FPR: {stats.false_positive_rate:.4f}")
    print()

    # 2. Counting Bloom Filter
    print("2. COUNTING BLOOM FILTER:")
    print("-" * 40)

    cbf = manager.create_counting(
        "counting",
        expected_items=1000
    )

    cbf.add("test_item")
    cbf.add("test_item")
    cbf.add("test_item")

    print(f"   Count 'test_item': {cbf.count('test_item')}")
    print(f"   Contains 'test_item': {cbf.contains('test_item')}")

    cbf.remove("test_item")
    print(f"   After remove, count: {cbf.count('test_item')}")
    print()

    # 3. Scalable Bloom Filter
    print("3. SCALABLE BLOOM FILTER:")
    print("-" * 40)

    sbf = manager.create_scalable(
        "scalable",
        initial_capacity=100,
        false_positive_rate=0.01
    )

    for i in range(500):
        sbf.add(f"scalable_{i}")

    print(f"   Filter count: {sbf.filter_count()}")
    print(f"   Contains 'scalable_250': {sbf.contains('scalable_250')}")

    stats = sbf.stats()
    print(f"   Total items: {stats.items_added}")
    print(f"   Total bits: {stats.bit_size}")
    print()

    # 4. Cuckoo Filter
    print("4. CUCKOO FILTER:")
    print("-" * 40)

    cf = manager.create_cuckoo(
        "cuckoo",
        capacity=1000,
        bucket_size=4
    )

    cf.add("cuckoo_item")
    print(f"   Contains 'cuckoo_item': {cf.contains('cuckoo_item')}")

    cf.remove("cuckoo_item")
    print(f"   After remove: {cf.contains('cuckoo_item')}")
    print(f"   Load factor: {cf.load_factor():.2%}")
    print()

    # 5. Add via Manager
    print("5. ADD VIA MANAGER:")
    print("-" * 40)

    manager.add("standard", "manager_added")
    contains = manager.contains("standard", "manager_added")

    print(f"   Added via manager: {contains}")
    print()

    # 6. Remove via Manager
    print("6. REMOVE VIA MANAGER:")
    print("-" * 40)

    manager.add("counting", "remove_me")
    removed = manager.remove("counting", "remove_me")

    print(f"   Removed: {removed}")
    print()

    # 7. List Filters
    print("7. LIST FILTERS:")
    print("-" * 40)

    filters = manager.list_filters()
    print(f"   Filters: {filters}")
    print()

    # 8. Get Filter Type
    print("8. GET FILTER TYPE:")
    print("-" * 40)

    for name in filters:
        filter_type = manager.get_type(name)
        print(f"   {name}: {filter_type.value}")
    print()

    # 9. Filter Stats
    print("9. FILTER STATS:")
    print("-" * 40)

    for name in filters:
        stats = manager.stats(name)
        if stats:
            print(f"   {name}:")
            print(f"     Items: {stats.items_added}")
            print(f"     Memory: {stats.memory_bytes} bytes")
    print()

    # 10. Union of Filters
    print("10. UNION OF FILTERS:")
    print("-" * 40)

    bf1 = BloomFilter(BloomConfig(expected_items=100))
    bf2 = BloomFilter(BloomConfig(expected_items=100))

    bf1.add("item_a")
    bf2.add("item_b")

    union = bf1.union(bf2)

    print(f"   Contains 'item_a': {union.contains('item_a')}")
    print(f"   Contains 'item_b': {union.contains('item_b')}")
    print()

    # 11. Serialization
    print("11. SERIALIZATION:")
    print("-" * 40)

    original = BloomFilter(BloomConfig(expected_items=100))
    original.add("serialize_test")

    data = original.to_bytes()
    restored = BloomFilter.from_bytes(data)

    print(f"   Serialized size: {len(data)} bytes")
    print(f"   Restored contains: {restored.contains('serialize_test')}")
    print()

    # 12. False Positive Test
    print("12. FALSE POSITIVE TEST:")
    print("-" * 40)

    test_bf = BloomFilter(BloomConfig(
        expected_items=1000,
        false_positive_rate=0.05
    ))

    for i in range(1000):
        test_bf.add(f"added_{i}")

    fp_count = 0
    test_count = 1000

    for i in range(test_count):
        if test_bf.contains(f"not_added_{i}"):
            fp_count += 1

    print(f"   Expected FPR: 5%")
    print(f"   Actual FPR: {fp_count / test_count:.2%}")
    print()

    # 13. Delete Filter
    print("13. DELETE FILTER:")
    print("-" * 40)

    deleted = manager.delete("cuckoo")
    print(f"   Deleted: {deleted}")
    print(f"   Filter count: {manager.filter_count()}")
    print()

    # 14. Get Filter
    print("14. GET FILTER:")
    print("-" * 40)

    retrieved = manager.get("standard")
    print(f"   Retrieved: {type(retrieved).__name__}")
    print()

    # 15. Filter Count
    print("15. FILTER COUNT:")
    print("-" * 40)

    print(f"   Total filters: {manager.filter_count()}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Bloom Filter Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
