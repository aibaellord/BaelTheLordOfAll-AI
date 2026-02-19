"""
BAEL Bloom Filter Engine Implementation
========================================

Probabilistic membership testing.

"Ba'el knows what exists without seeing all." — Ba'el
"""

import hashlib
import logging
import math
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid

logger = logging.getLogger("BAEL.BloomFilter")


# ============================================================================
# ENUMS
# ============================================================================

class BloomFilterType(Enum):
    """Bloom filter variants."""
    STANDARD = "standard"        # Basic bloom filter
    COUNTING = "counting"        # Supports removal
    SCALABLE = "scalable"        # Auto-scaling
    PARTITIONED = "partitioned"  # Partitioned for parallelism


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class BloomFilterStats:
    """Bloom filter statistics."""
    items_added: int = 0
    queries: int = 0
    false_positives_estimate: float = 0.0
    fill_ratio: float = 0.0


@dataclass
class BloomFilterConfig:
    """Bloom filter configuration."""
    expected_items: int = 10000
    false_positive_rate: float = 0.01
    filter_type: BloomFilterType = BloomFilterType.STANDARD

    # Counting bloom filter
    counter_bits: int = 4  # For counting bloom filter


# ============================================================================
# BLOOM FILTER
# ============================================================================

class BloomFilter:
    """
    Bloom filter implementation.

    Features:
    - O(1) add and query
    - Configurable false positive rate
    - Counting variant for deletion
    - Scalable variant for growth

    "Ba'el sees all patterns in the noise." — Ba'el
    """

    def __init__(
        self,
        expected_items: int = 10000,
        false_positive_rate: float = 0.01,
        filter_id: Optional[str] = None
    ):
        """
        Initialize bloom filter.

        Args:
            expected_items: Expected number of items
            false_positive_rate: Desired FP rate
            filter_id: Optional filter ID
        """
        self.id = filter_id or str(uuid.uuid4())
        self.expected_items = expected_items
        self.false_positive_rate = false_positive_rate

        # Calculate optimal size and hash count
        self.size = self._calculate_size(expected_items, false_positive_rate)
        self.hash_count = self._calculate_hash_count(self.size, expected_items)

        # Bit array
        self._bits = [0] * self.size

        # Stats
        self._items_added = 0

        # Thread safety
        self._lock = threading.RLock()

        logger.debug(
            f"Bloom filter: size={self.size}, hashes={self.hash_count}"
        )

    def _calculate_size(self, n: int, p: float) -> int:
        """Calculate optimal bit array size."""
        # m = -(n * ln(p)) / (ln(2)^2)
        m = -(n * math.log(p)) / (math.log(2) ** 2)
        return int(m)

    def _calculate_hash_count(self, m: int, n: int) -> int:
        """Calculate optimal number of hash functions."""
        # k = (m/n) * ln(2)
        k = (m / n) * math.log(2)
        return max(1, int(k))

    def _get_hash_values(self, item: str) -> List[int]:
        """Get hash values for item."""
        # Use double hashing technique
        h1 = int(hashlib.md5(item.encode()).hexdigest(), 16)
        h2 = int(hashlib.sha256(item.encode()).hexdigest(), 16)

        return [
            (h1 + i * h2) % self.size
            for i in range(self.hash_count)
        ]

    def add(self, item: Union[str, Any]) -> None:
        """
        Add item to bloom filter.

        Args:
            item: Item to add
        """
        item_str = str(item)

        with self._lock:
            for index in self._get_hash_values(item_str):
                self._bits[index] = 1

            self._items_added += 1

    def add_all(self, items: List[Union[str, Any]]) -> None:
        """Add multiple items."""
        for item in items:
            self.add(item)

    def might_contain(self, item: Union[str, Any]) -> bool:
        """
        Check if item might be in set.

        Args:
            item: Item to check

        Returns:
            True if might be in set, False if definitely not
        """
        item_str = str(item)

        with self._lock:
            for index in self._get_hash_values(item_str):
                if self._bits[index] == 0:
                    return False

        return True

    def __contains__(self, item: Union[str, Any]) -> bool:
        """Support 'in' operator."""
        return self.might_contain(item)

    def get_fill_ratio(self) -> float:
        """Get ratio of set bits."""
        with self._lock:
            set_bits = sum(self._bits)
            return set_bits / self.size

    def get_false_positive_probability(self) -> float:
        """Get current false positive probability."""
        fill_ratio = self.get_fill_ratio()
        return fill_ratio ** self.hash_count

    def clear(self) -> None:
        """Clear the filter."""
        with self._lock:
            self._bits = [0] * self.size
            self._items_added = 0

    def get_stats(self) -> BloomFilterStats:
        """Get filter statistics."""
        return BloomFilterStats(
            items_added=self._items_added,
            false_positives_estimate=self.get_false_positive_probability(),
            fill_ratio=self.get_fill_ratio()
        )

    def merge(self, other: 'BloomFilter') -> None:
        """Merge another bloom filter (must be same size)."""
        if self.size != other.size:
            raise ValueError("Bloom filters must be same size to merge")

        with self._lock:
            for i in range(self.size):
                self._bits[i] = self._bits[i] | other._bits[i]


# ============================================================================
# COUNTING BLOOM FILTER
# ============================================================================

class CountingBloomFilter:
    """
    Counting bloom filter supporting deletion.

    Features:
    - Support removal
    - Counter overflow protection
    - Same probabilistic guarantees
    """

    def __init__(
        self,
        expected_items: int = 10000,
        false_positive_rate: float = 0.01,
        counter_bits: int = 4,
        filter_id: Optional[str] = None
    ):
        """Initialize counting bloom filter."""
        self.id = filter_id or str(uuid.uuid4())
        self.expected_items = expected_items
        self.false_positive_rate = false_positive_rate
        self.counter_bits = counter_bits
        self.max_count = (1 << counter_bits) - 1

        # Calculate optimal size
        m = -(expected_items * math.log(false_positive_rate)) / (math.log(2) ** 2)
        self.size = int(m)
        self.hash_count = max(1, int((self.size / expected_items) * math.log(2)))

        # Counter array
        self._counters = [0] * self.size

        self._items_added = 0
        self._lock = threading.RLock()

    def _get_hash_values(self, item: str) -> List[int]:
        """Get hash values for item."""
        h1 = int(hashlib.md5(item.encode()).hexdigest(), 16)
        h2 = int(hashlib.sha256(item.encode()).hexdigest(), 16)

        return [
            (h1 + i * h2) % self.size
            for i in range(self.hash_count)
        ]

    def add(self, item: Union[str, Any]) -> None:
        """Add item."""
        item_str = str(item)

        with self._lock:
            for index in self._get_hash_values(item_str):
                if self._counters[index] < self.max_count:
                    self._counters[index] += 1

            self._items_added += 1

    def remove(self, item: Union[str, Any]) -> bool:
        """
        Remove item.

        Returns:
            True if item was likely present
        """
        item_str = str(item)

        with self._lock:
            # Check if present first
            if not self.might_contain(item):
                return False

            for index in self._get_hash_values(item_str):
                if self._counters[index] > 0:
                    self._counters[index] -= 1

            return True

    def might_contain(self, item: Union[str, Any]) -> bool:
        """Check if item might be in set."""
        item_str = str(item)

        with self._lock:
            for index in self._get_hash_values(item_str):
                if self._counters[index] == 0:
                    return False

        return True

    def __contains__(self, item: Union[str, Any]) -> bool:
        return self.might_contain(item)


# ============================================================================
# SCALABLE BLOOM FILTER
# ============================================================================

class ScalableBloomFilter:
    """
    Scalable bloom filter that grows as needed.

    Features:
    - Auto-scaling
    - Maintains FP rate
    - Chain of filters
    """

    def __init__(
        self,
        initial_capacity: int = 1000,
        false_positive_rate: float = 0.01,
        growth_factor: int = 2,
        filter_id: Optional[str] = None
    ):
        """Initialize scalable bloom filter."""
        self.id = filter_id or str(uuid.uuid4())
        self.initial_capacity = initial_capacity
        self.false_positive_rate = false_positive_rate
        self.growth_factor = growth_factor

        # Chain of filters
        self._filters: List[BloomFilter] = []
        self._add_filter()

        self._items_added = 0
        self._lock = threading.RLock()

    def _add_filter(self) -> None:
        """Add a new filter to the chain."""
        # Each successive filter has tighter FP rate
        n = len(self._filters)
        capacity = self.initial_capacity * (self.growth_factor ** n)
        fp_rate = self.false_positive_rate * (0.5 ** n)

        self._filters.append(BloomFilter(
            expected_items=capacity,
            false_positive_rate=fp_rate
        ))

    def add(self, item: Union[str, Any]) -> None:
        """Add item."""
        with self._lock:
            current_filter = self._filters[-1]

            # Check if current filter is full
            if current_filter._items_added >= current_filter.expected_items:
                self._add_filter()
                current_filter = self._filters[-1]

            current_filter.add(item)
            self._items_added += 1

    def might_contain(self, item: Union[str, Any]) -> bool:
        """Check if item might be in set."""
        with self._lock:
            for f in self._filters:
                if item in f:
                    return True
        return False

    def __contains__(self, item: Union[str, Any]) -> bool:
        return self.might_contain(item)

    @property
    def filter_count(self) -> int:
        """Get number of filters in chain."""
        return len(self._filters)


# ============================================================================
# BLOOM FILTER MANAGER
# ============================================================================

class BloomFilterManager:
    """Manager for bloom filter instances."""

    def __init__(self):
        self._filters: Dict[str, Union[BloomFilter, CountingBloomFilter, ScalableBloomFilter]] = {}
        self._lock = threading.RLock()

    def create_filter(
        self,
        name: str,
        filter_type: BloomFilterType = BloomFilterType.STANDARD,
        **kwargs
    ) -> Union[BloomFilter, CountingBloomFilter, ScalableBloomFilter]:
        """Create a bloom filter."""
        if filter_type == BloomFilterType.STANDARD:
            f = BloomFilter(**kwargs)
        elif filter_type == BloomFilterType.COUNTING:
            f = CountingBloomFilter(**kwargs)
        elif filter_type == BloomFilterType.SCALABLE:
            f = ScalableBloomFilter(**kwargs)
        else:
            f = BloomFilter(**kwargs)

        with self._lock:
            self._filters[name] = f

        return f

    def get_filter(self, name: str) -> Optional[Union[BloomFilter, CountingBloomFilter, ScalableBloomFilter]]:
        """Get filter by name."""
        return self._filters.get(name)

    def delete_filter(self, name: str) -> bool:
        """Delete a filter."""
        with self._lock:
            if name in self._filters:
                del self._filters[name]
                return True
        return False

    def list_filters(self) -> List[str]:
        """List all filter names."""
        return list(self._filters.keys())


# ============================================================================
# CONVENIENCE
# ============================================================================

bloom_filter_manager = BloomFilterManager()


def create_bloom_filter(name: str, **kwargs) -> BloomFilter:
    """Create a bloom filter."""
    return bloom_filter_manager.create_filter(name, **kwargs)


def get_bloom_filter(name: str) -> Optional[BloomFilter]:
    """Get bloom filter by name."""
    return bloom_filter_manager.get_filter(name)
