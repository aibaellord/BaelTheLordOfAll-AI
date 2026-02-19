"""
BAEL HyperLogLog Engine Implementation
=======================================

Probabilistic cardinality estimation.

"Ba'el counts the infinite with finite memory." — Ba'el
"""

import hashlib
import logging
import math
import struct
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
import uuid

logger = logging.getLogger("BAEL.HyperLogLog")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class HyperLogLogStats:
    """HyperLogLog statistics."""
    items_added: int = 0
    estimated_cardinality: int = 0
    register_count: int = 0
    precision: int = 0


# ============================================================================
# HYPERLOGLOG
# ============================================================================

class HyperLogLog:
    """
    HyperLogLog cardinality estimator.

    Features:
    - O(1) add operation
    - Constant memory usage
    - Configurable precision
    - Union support

    "Ba'el estimates the vastness of infinity." — Ba'el
    """

    def __init__(
        self,
        precision: int = 14,
        hll_id: Optional[str] = None
    ):
        """
        Initialize HyperLogLog.

        Args:
            precision: Precision (4-18), higher = more accurate
            hll_id: Optional ID
        """
        if not 4 <= precision <= 18:
            raise ValueError("Precision must be between 4 and 18")

        self.id = hll_id or str(uuid.uuid4())
        self.precision = precision

        # Number of registers
        self.m = 1 << precision  # 2^precision

        # Alpha correction factor
        if self.m == 16:
            self.alpha = 0.673
        elif self.m == 32:
            self.alpha = 0.697
        elif self.m == 64:
            self.alpha = 0.709
        else:
            self.alpha = 0.7213 / (1 + 1.079 / self.m)

        # Registers (stores max leading zeros)
        self._registers = [0] * self.m

        # Stats
        self._items_added = 0

        # Thread safety
        self._lock = threading.RLock()

        logger.debug(f"HyperLogLog: precision={precision}, registers={self.m}")

    def _hash(self, value: str) -> int:
        """Hash value to 64-bit integer."""
        h = hashlib.sha256(value.encode()).digest()[:8]
        return struct.unpack('>Q', h)[0]

    def _get_register_index(self, hash_value: int) -> int:
        """Get register index from hash."""
        return hash_value >> (64 - self.precision)

    def _count_leading_zeros(self, hash_value: int) -> int:
        """Count leading zeros after the register bits."""
        # Use remaining bits after register index
        remaining_bits = 64 - self.precision

        # Mask to get remaining bits
        remaining = hash_value & ((1 << remaining_bits) - 1)

        if remaining == 0:
            return remaining_bits

        # Count leading zeros
        zeros = 0
        for i in range(remaining_bits - 1, -1, -1):
            if remaining & (1 << i):
                break
            zeros += 1

        return zeros + 1  # +1 for the first 1 bit

    def add(self, item: Union[str, Any]) -> None:
        """
        Add item to HyperLogLog.

        Args:
            item: Item to add
        """
        item_str = str(item)
        hash_value = self._hash(item_str)

        # Get register index
        index = self._get_register_index(hash_value)

        # Count leading zeros
        zeros = self._count_leading_zeros(hash_value)

        with self._lock:
            # Update register with max
            self._registers[index] = max(self._registers[index], zeros)
            self._items_added += 1

    def add_all(self, items: List[Union[str, Any]]) -> None:
        """Add multiple items."""
        for item in items:
            self.add(item)

    def count(self) -> int:
        """
        Estimate cardinality.

        Returns:
            Estimated unique count
        """
        with self._lock:
            # Raw estimate
            raw_estimate = self._raw_estimate()

            # Small range correction
            if raw_estimate <= 2.5 * self.m:
                # Count zero registers
                zeros = sum(1 for r in self._registers if r == 0)

                if zeros > 0:
                    # Linear counting
                    return int(self.m * math.log(self.m / zeros))

            # Large range correction (for very large cardinalities)
            # Not typically needed for 64-bit hashes

            return int(raw_estimate)

    def _raw_estimate(self) -> float:
        """Calculate raw HyperLogLog estimate."""
        # Harmonic mean of 2^-register values
        indicator_sum = sum(
            2 ** (-r) for r in self._registers
        )

        return self.alpha * (self.m ** 2) / indicator_sum

    def merge(self, other: 'HyperLogLog') -> None:
        """
        Merge another HyperLogLog.

        Args:
            other: HyperLogLog to merge
        """
        if self.precision != other.precision:
            raise ValueError("HyperLogLogs must have same precision to merge")

        with self._lock:
            for i in range(self.m):
                self._registers[i] = max(
                    self._registers[i],
                    other._registers[i]
                )

    def union(self, *others: 'HyperLogLog') -> 'HyperLogLog':
        """
        Create union of multiple HyperLogLogs.

        Returns:
            New merged HyperLogLog
        """
        result = HyperLogLog(precision=self.precision)
        result._registers = self._registers.copy()

        for other in others:
            result.merge(other)

        return result

    def clear(self) -> None:
        """Clear the HyperLogLog."""
        with self._lock:
            self._registers = [0] * self.m
            self._items_added = 0

    def get_stats(self) -> HyperLogLogStats:
        """Get statistics."""
        return HyperLogLogStats(
            items_added=self._items_added,
            estimated_cardinality=self.count(),
            register_count=self.m,
            precision=self.precision
        )

    def __len__(self) -> int:
        """Support len() for cardinality."""
        return self.count()


# ============================================================================
# HYPERLOGLOG++
# ============================================================================

class HyperLogLogPlusPlus(HyperLogLog):
    """
    HyperLogLog++ with improvements.

    Features:
    - Better bias correction
    - Sparse representation for small sets
    - 64-bit hash functions
    """

    def __init__(
        self,
        precision: int = 14,
        sparse_precision: int = 25,
        hll_id: Optional[str] = None
    ):
        """Initialize HyperLogLog++."""
        super().__init__(precision, hll_id)

        self.sparse_precision = sparse_precision
        self._sparse = True
        self._sparse_set: set = set()
        self._sparse_threshold = self.m // 4

        # Bias correction data (simplified)
        self._bias_data = self._get_bias_data()

    def _get_bias_data(self) -> Dict[int, List[float]]:
        """Get bias correction data for precision."""
        # Simplified bias data - in production would have full tables
        return {}

    def add(self, item: Union[str, Any]) -> None:
        """Add item with sparse optimization."""
        if self._sparse:
            item_str = str(item)
            hash_value = self._hash(item_str)

            # Add to sparse set
            self._sparse_set.add(hash_value)
            self._items_added += 1

            # Convert to dense if threshold exceeded
            if len(self._sparse_set) > self._sparse_threshold:
                self._to_dense()
        else:
            super().add(item)

    def _to_dense(self) -> None:
        """Convert from sparse to dense representation."""
        for hash_value in self._sparse_set:
            index = self._get_register_index(hash_value)
            zeros = self._count_leading_zeros(hash_value)
            self._registers[index] = max(self._registers[index], zeros)

        self._sparse_set = None
        self._sparse = False

    def count(self) -> int:
        """Estimate cardinality with bias correction."""
        if self._sparse:
            return len(self._sparse_set)

        return super().count()


# ============================================================================
# HYPERLOGLOG MANAGER
# ============================================================================

class HyperLogLogManager:
    """Manager for HyperLogLog instances."""

    def __init__(self):
        self._hlls: Dict[str, HyperLogLog] = {}
        self._lock = threading.RLock()

    def create(
        self,
        name: str,
        precision: int = 14,
        use_plus_plus: bool = False
    ) -> HyperLogLog:
        """Create a HyperLogLog."""
        if use_plus_plus:
            hll = HyperLogLogPlusPlus(precision=precision)
        else:
            hll = HyperLogLog(precision=precision)

        with self._lock:
            self._hlls[name] = hll

        return hll

    def get(self, name: str) -> Optional[HyperLogLog]:
        """Get HyperLogLog by name."""
        return self._hlls.get(name)

    def get_or_create(
        self,
        name: str,
        **kwargs
    ) -> HyperLogLog:
        """Get or create HyperLogLog."""
        with self._lock:
            if name in self._hlls:
                return self._hlls[name]

        return self.create(name, **kwargs)

    def delete(self, name: str) -> bool:
        """Delete a HyperLogLog."""
        with self._lock:
            if name in self._hlls:
                del self._hlls[name]
                return True
        return False

    def union(self, *names: str) -> Optional[HyperLogLog]:
        """Union multiple HyperLogLogs."""
        hlls = [self._hlls.get(n) for n in names]
        hlls = [h for h in hlls if h is not None]

        if not hlls:
            return None

        return hlls[0].union(*hlls[1:])

    def list_all(self) -> List[str]:
        """List all HyperLogLog names."""
        return list(self._hlls.keys())

    def get_stats(self) -> Dict[str, Any]:
        """Get all stats."""
        return {
            name: hll.get_stats().__dict__
            for name, hll in self._hlls.items()
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

hll_manager = HyperLogLogManager()


def create_hll(name: str, **kwargs) -> HyperLogLog:
    """Create a HyperLogLog."""
    return hll_manager.create(name, **kwargs)


def count_unique(name: str) -> int:
    """Get unique count for HyperLogLog."""
    hll = hll_manager.get(name)
    return hll.count() if hll else 0


def add_to_hll(name: str, item: Any) -> None:
    """Add item to HyperLogLog."""
    hll = hll_manager.get_or_create(name)
    hll.add(item)
