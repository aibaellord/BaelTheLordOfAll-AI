"""
BAEL Count-Min Sketch Engine
============================

Probabilistic frequency estimation with bounded error.

"Ba'el sketches frequencies." — Ba'el
"""

import logging
import threading
import math
import hashlib
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger("BAEL.CountMinSketch")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class CMSStats:
    """Count-Min Sketch statistics."""
    width: int
    depth: int
    total_count: int
    epsilon: float
    delta: float


# ============================================================================
# COUNT-MIN SKETCH
# ============================================================================

class CountMinSketch:
    """
    Count-Min Sketch for frequency estimation.

    Features:
    - O(d) update and query (d = depth)
    - Bounded error: estimate <= true + epsilon*N with probability >= 1-delta
    - Space: O(1/epsilon * log(1/delta))

    "Ba'el counts approximately." — Ba'el
    """

    def __init__(self, epsilon: float = 0.01, delta: float = 0.01):
        """
        Initialize Count-Min Sketch.

        Args:
            epsilon: Error factor (estimate within epsilon*N of true count)
            delta: Failure probability
        """
        self._width = int(math.ceil(math.e / epsilon))
        self._depth = int(math.ceil(math.log(1 / delta)))

        self._table = [[0] * self._width for _ in range(self._depth)]
        self._total = 0
        self._epsilon = epsilon
        self._delta = delta
        self._lock = threading.RLock()

    def _hashes(self, item: Any) -> List[int]:
        """Generate hash indices for each row."""
        item_bytes = str(item).encode('utf-8')

        # Use different hash functions for each row
        hashes = []
        for i in range(self._depth):
            h = hashlib.sha256(item_bytes + str(i).encode()).hexdigest()
            hashes.append(int(h, 16) % self._width)

        return hashes

    def add(self, item: Any, count: int = 1):
        """
        Add item with count.

        O(depth).
        """
        with self._lock:
            for row, col in enumerate(self._hashes(item)):
                self._table[row][col] += count
            self._total += count

    def estimate(self, item: Any) -> int:
        """
        Estimate frequency of item.

        Returns minimum across all hash positions.
        O(depth).
        """
        with self._lock:
            return min(
                self._table[row][col]
                for row, col in enumerate(self._hashes(item))
            )

    def __getitem__(self, item: Any) -> int:
        return self.estimate(item)

    def merge(self, other: 'CountMinSketch') -> 'CountMinSketch':
        """Merge two sketches."""
        if self._width != other._width or self._depth != other._depth:
            raise ValueError("Sketches must have same dimensions")

        with self._lock:
            result = CountMinSketch.__new__(CountMinSketch)
            result._width = self._width
            result._depth = self._depth
            result._epsilon = self._epsilon
            result._delta = self._delta
            result._total = self._total + other._total
            result._lock = threading.RLock()

            result._table = [
                [self._table[i][j] + other._table[i][j] for j in range(self._width)]
                for i in range(self._depth)
            ]

            return result

    def get_stats(self) -> CMSStats:
        """Get sketch statistics."""
        return CMSStats(
            width=self._width,
            depth=self._depth,
            total_count=self._total,
            epsilon=self._epsilon,
            delta=self._delta
        )


# ============================================================================
# COUNT-MEAN-MIN SKETCH
# ============================================================================

class CountMeanMinSketch:
    """
    Count-Mean-Min Sketch with better estimates for skewed distributions.

    Uses median instead of minimum for estimation.

    "Ba'el means well." — Ba'el
    """

    def __init__(self, epsilon: float = 0.01, delta: float = 0.01):
        """Initialize sketch."""
        self._width = int(math.ceil(math.e / epsilon))
        self._depth = int(math.ceil(math.log(1 / delta)))

        self._table = [[0] * self._width for _ in range(self._depth)]
        self._total = 0
        self._lock = threading.RLock()

    def _hashes(self, item: Any) -> List[int]:
        """Generate hash indices."""
        item_bytes = str(item).encode('utf-8')
        return [
            int(hashlib.sha256(item_bytes + str(i).encode()).hexdigest(), 16) % self._width
            for i in range(self._depth)
        ]

    def add(self, item: Any, count: int = 1):
        """Add item with count."""
        with self._lock:
            for row, col in enumerate(self._hashes(item)):
                self._table[row][col] += count
            self._total += count

    def estimate(self, item: Any) -> int:
        """Estimate using median."""
        with self._lock:
            estimates = []
            for row, col in enumerate(self._hashes(item)):
                # Subtract noise estimate
                noise = (self._total - self._table[row][col]) / (self._width - 1)
                est = self._table[row][col] - noise
                estimates.append(max(0, est))

            estimates.sort()
            mid = len(estimates) // 2
            if len(estimates) % 2 == 0:
                return int((estimates[mid - 1] + estimates[mid]) / 2)
            return int(estimates[mid])


# ============================================================================
# HEAVY HITTERS
# ============================================================================

class HeavyHitters:
    """
    Find items with frequency above threshold.

    Uses Count-Min Sketch with heap.

    "Ba'el finds the heavy." — Ba'el
    """

    def __init__(
        self,
        k: int = 10,
        epsilon: float = 0.01,
        delta: float = 0.01
    ):
        """
        Initialize heavy hitters finder.

        Args:
            k: Number of top items to track
            epsilon, delta: CMS parameters
        """
        self._k = k
        self._cms = CountMinSketch(epsilon, delta)
        self._candidates: Dict[Any, int] = {}
        self._threshold = 0
        self._lock = threading.RLock()

    def add(self, item: Any, count: int = 1):
        """Add item."""
        with self._lock:
            self._cms.add(item, count)

            est = self._cms.estimate(item)
            self._candidates[item] = est

            # Prune if too many candidates
            if len(self._candidates) > 2 * self._k:
                self._prune()

    def _prune(self):
        """Keep only top candidates."""
        sorted_items = sorted(
            self._candidates.items(),
            key=lambda x: x[1],
            reverse=True
        )

        self._candidates = dict(sorted_items[:self._k])

        if sorted_items:
            self._threshold = sorted_items[min(self._k, len(sorted_items) - 1)][1]

    def get_heavy_hitters(self, threshold: Optional[float] = None) -> List[Tuple[Any, int]]:
        """
        Get items above threshold.

        Args:
            threshold: Minimum count (or use top-k)
        """
        with self._lock:
            if threshold is None:
                # Return top k
                return sorted(
                    self._candidates.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:self._k]

            return [
                (item, count)
                for item, count in self._candidates.items()
                if count >= threshold
            ]


# ============================================================================
# HYPERLOGLOG
# ============================================================================

class HyperLogLog:
    """
    Cardinality estimation with O(1) space.

    Features:
    - O(1) update
    - O(1) estimate
    - Error: ~1.04/sqrt(m) where m = registers

    "Ba'el counts uniquely." — Ba'el
    """

    def __init__(self, precision: int = 14):
        """
        Initialize HyperLogLog.

        Args:
            precision: Number of bits for register addressing (4-16)
        """
        self._precision = min(16, max(4, precision))
        self._num_registers = 1 << self._precision
        self._registers = [0] * self._num_registers

        # Alpha constant for bias correction
        if self._num_registers == 16:
            self._alpha = 0.673
        elif self._num_registers == 32:
            self._alpha = 0.697
        elif self._num_registers == 64:
            self._alpha = 0.709
        else:
            self._alpha = 0.7213 / (1 + 1.079 / self._num_registers)

        self._lock = threading.RLock()

    def _hash(self, item: Any) -> int:
        """Get 64-bit hash."""
        h = hashlib.sha256(str(item).encode()).hexdigest()
        return int(h[:16], 16)  # 64 bits

    def _count_leading_zeros(self, value: int, bits: int) -> int:
        """Count leading zeros in value with given bits."""
        if value == 0:
            return bits

        count = 0
        mask = 1 << (bits - 1)

        while (value & mask) == 0 and count < bits:
            count += 1
            mask >>= 1

        return count

    def add(self, item: Any):
        """Add item to set."""
        with self._lock:
            h = self._hash(item)

            # Use first p bits for register index
            register_idx = h >> (64 - self._precision)

            # Use remaining bits for counting zeros
            remaining = h & ((1 << (64 - self._precision)) - 1)
            zeros = self._count_leading_zeros(remaining, 64 - self._precision) + 1

            self._registers[register_idx] = max(self._registers[register_idx], zeros)

    def estimate(self) -> int:
        """Estimate cardinality."""
        with self._lock:
            m = self._num_registers

            # Harmonic mean
            indicator = sum(2 ** (-r) for r in self._registers)
            raw_estimate = self._alpha * m * m / indicator

            # Small range correction
            if raw_estimate <= 2.5 * m:
                zeros = self._registers.count(0)
                if zeros > 0:
                    return int(m * math.log(m / zeros))

            # Large range correction
            if raw_estimate > (1 << 32) / 30:
                return int(-((1 << 32) * math.log(1 - raw_estimate / (1 << 32))))

            return int(raw_estimate)

    def merge(self, other: 'HyperLogLog') -> 'HyperLogLog':
        """Merge two HLLs."""
        if self._precision != other._precision:
            raise ValueError("Precisions must match")

        result = HyperLogLog(self._precision)
        result._registers = [
            max(a, b)
            for a, b in zip(self._registers, other._registers)
        ]

        return result

    def __len__(self) -> int:
        return self.estimate()


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_count_min_sketch(
    epsilon: float = 0.01,
    delta: float = 0.01
) -> CountMinSketch:
    """Create Count-Min Sketch."""
    return CountMinSketch(epsilon, delta)


def create_hyperloglog(precision: int = 14) -> HyperLogLog:
    """Create HyperLogLog."""
    return HyperLogLog(precision)


def create_heavy_hitters(k: int = 10) -> HeavyHitters:
    """Create heavy hitters finder."""
    return HeavyHitters(k)


def estimate_frequency(
    stream: List[Any],
    queries: List[Any],
    epsilon: float = 0.01
) -> Dict[Any, int]:
    """
    Estimate frequencies from stream.

    Args:
        stream: Items to count
        queries: Items to query
        epsilon: Error factor
    """
    cms = CountMinSketch(epsilon)
    for item in stream:
        cms.add(item)

    return {q: cms.estimate(q) for q in queries}


def estimate_cardinality(stream: List[Any]) -> int:
    """Estimate number of unique items in stream."""
    hll = HyperLogLog()
    for item in stream:
        hll.add(item)
    return hll.estimate()
