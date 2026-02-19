"""
BAEL Mo's Algorithm Engine
==========================

Offline query processing with block decomposition.

"Ba'el answers all queries in optimal order." — Ba'el
"""

import logging
import math
import threading
from typing import Any, Callable, Dict, Generic, List, Optional, Tuple, TypeVar
from dataclasses import dataclass, field

logger = logging.getLogger("BAEL.MoAlgorithm")

T = TypeVar('T')


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Query:
    """Range query."""
    left: int
    right: int
    index: int  # Original query index


@dataclass
class MoStats:
    """Mo's Algorithm statistics."""
    array_size: int = 0
    query_count: int = 0
    block_size: int = 0
    add_operations: int = 0
    remove_operations: int = 0


# ============================================================================
# MO'S ALGORITHM ENGINE
# ============================================================================

class MoAlgorithmEngine(Generic[T]):
    """
    Mo's Algorithm for offline range queries.

    Features:
    - O((N + Q) * sqrt(N)) complexity
    - Works for various range query types
    - Custom add/remove operations
    - Optimal query ordering

    "Ba'el orders chaos into sqrt(n) blocks." — Ba'el
    """

    def __init__(self):
        """Initialize Mo's Algorithm engine."""
        self._array: List[T] = []
        self._queries: List[Query] = []
        self._results: List[Any] = []
        self._block_size = 1
        self._stats = MoStats()
        self._lock = threading.RLock()

        # Operation callbacks
        self._add: Optional[Callable[[int], None]] = None
        self._remove: Optional[Callable[[int], None]] = None
        self._get_answer: Optional[Callable[[], Any]] = None

        logger.debug("Mo's Algorithm engine initialized")

    def set_array(self, array: List[T]) -> None:
        """
        Set the array to query.

        Args:
            array: Input array
        """
        with self._lock:
            self._array = list(array)
            self._stats.array_size = len(array)
            self._block_size = max(1, int(math.sqrt(len(array))))
            self._stats.block_size = self._block_size

    def set_operations(
        self,
        add: Callable[[int], None],
        remove: Callable[[int], None],
        get_answer: Callable[[], Any]
    ) -> None:
        """
        Set add/remove/get_answer operations.

        Args:
            add: Function to add element at index to current state
            remove: Function to remove element at index from current state
            get_answer: Function to get current answer
        """
        self._add = add
        self._remove = remove
        self._get_answer = get_answer

    def add_query(self, left: int, right: int) -> int:
        """
        Add a range query [left, right].

        Args:
            left: Left endpoint (inclusive)
            right: Right endpoint (inclusive)

        Returns:
            Query index
        """
        with self._lock:
            index = len(self._queries)
            self._queries.append(Query(left=left, right=right, index=index))
            self._stats.query_count += 1
            return index

    def process(self) -> List[Any]:
        """
        Process all queries.

        Returns:
            List of answers in original query order
        """
        with self._lock:
            if not self._queries:
                return []

            if not all([self._add, self._remove, self._get_answer]):
                raise RuntimeError("Must set operations before processing")

            n = len(self._array)
            q = len(self._queries)

            # Sort queries by Mo's ordering
            block_size = self._block_size

            def mo_compare(query: Query) -> Tuple[int, int]:
                block = query.left // block_size
                # Alternate direction for better cache
                if block % 2 == 0:
                    return (block, query.right)
                else:
                    return (block, -query.right)

            sorted_queries = sorted(self._queries, key=mo_compare)

            # Initialize results
            self._results = [None] * q

            # Process queries
            cur_left = 0
            cur_right = -1

            for query in sorted_queries:
                # Expand/contract range to match query

                # Expand right
                while cur_right < query.right:
                    cur_right += 1
                    self._add(cur_right)
                    self._stats.add_operations += 1

                # Expand left
                while cur_left > query.left:
                    cur_left -= 1
                    self._add(cur_left)
                    self._stats.add_operations += 1

                # Contract right
                while cur_right > query.right:
                    self._remove(cur_right)
                    cur_right -= 1
                    self._stats.remove_operations += 1

                # Contract left
                while cur_left < query.left:
                    self._remove(cur_left)
                    cur_left += 1
                    self._stats.remove_operations += 1

                # Store answer
                self._results[query.index] = self._get_answer()

            logger.info(
                f"Mo's: processed {q} queries, "
                f"{self._stats.add_operations} adds, "
                f"{self._stats.remove_operations} removes"
            )

            return self._results

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'array_size': self._stats.array_size,
            'query_count': self._stats.query_count,
            'block_size': self._stats.block_size,
            'add_operations': self._stats.add_operations,
            'remove_operations': self._stats.remove_operations,
            'total_operations': self._stats.add_operations + self._stats.remove_operations
        }


# ============================================================================
# SPECIALIZED VARIANTS
# ============================================================================

class DistinctCountMo:
    """
    Mo's Algorithm for counting distinct elements in range.

    "Ba'el counts the unique among the many." — Ba'el
    """

    def __init__(self, array: List[int]):
        """
        Initialize with array.

        Args:
            array: Input array of integers
        """
        self._array = list(array)
        self._mo = MoAlgorithmEngine[int]()
        self._mo.set_array(array)

        # State for counting distinct
        self._count: Dict[int, int] = {}
        self._distinct = 0

        self._mo.set_operations(
            add=self._add,
            remove=self._remove,
            get_answer=self._get_answer
        )

    def _add(self, idx: int) -> None:
        """Add element at index."""
        val = self._array[idx]

        if val not in self._count:
            self._count[val] = 0

        if self._count[val] == 0:
            self._distinct += 1

        self._count[val] += 1

    def _remove(self, idx: int) -> None:
        """Remove element at index."""
        val = self._array[idx]
        self._count[val] -= 1

        if self._count[val] == 0:
            self._distinct -= 1

    def _get_answer(self) -> int:
        """Get current distinct count."""
        return self._distinct

    def add_query(self, left: int, right: int) -> int:
        """Add query [left, right]."""
        return self._mo.add_query(left, right)

    def process(self) -> List[int]:
        """Process all queries."""
        # Reset state
        self._count = {}
        self._distinct = 0
        return self._mo.process()


class FrequencyMo:
    """
    Mo's Algorithm for frequency queries.

    "Ba'el tracks the frequency of all things." — Ba'el
    """

    def __init__(self, array: List[int]):
        """Initialize with array."""
        self._array = list(array)
        self._mo = MoAlgorithmEngine[int]()
        self._mo.set_array(array)

        self._count: Dict[int, int] = {}
        self._target: int = 0

        self._mo.set_operations(
            add=self._add,
            remove=self._remove,
            get_answer=self._get_answer
        )

    def _add(self, idx: int) -> None:
        val = self._array[idx]
        self._count[val] = self._count.get(val, 0) + 1

    def _remove(self, idx: int) -> None:
        val = self._array[idx]
        self._count[val] -= 1
        if self._count[val] == 0:
            del self._count[val]

    def _get_answer(self) -> int:
        return self._count.get(self._target, 0)

    def add_query(self, left: int, right: int, target: int) -> int:
        """Add frequency query for target in [left, right]."""
        idx = self._mo.add_query(left, right)
        # Note: This simplified version queries same target
        # Full implementation would store target per query
        self._target = target
        return idx

    def process(self) -> List[int]:
        """Process all queries."""
        self._count = {}
        return self._mo.process()


class ModeMo:
    """
    Mo's Algorithm for finding mode (most frequent) in range.

    "Ba'el finds the dominant among the many." — Ba'el
    """

    def __init__(self, array: List[int]):
        """Initialize with array."""
        self._array = list(array)
        self._mo = MoAlgorithmEngine[int]()
        self._mo.set_array(array)

        self._count: Dict[int, int] = {}
        self._freq_count: Dict[int, int] = {}  # frequency -> count of elements with that frequency
        self._max_freq = 0

        self._mo.set_operations(
            add=self._add,
            remove=self._remove,
            get_answer=self._get_answer
        )

    def _add(self, idx: int) -> None:
        val = self._array[idx]
        old_freq = self._count.get(val, 0)
        new_freq = old_freq + 1

        self._count[val] = new_freq

        if old_freq > 0:
            self._freq_count[old_freq] -= 1

        self._freq_count[new_freq] = self._freq_count.get(new_freq, 0) + 1
        self._max_freq = max(self._max_freq, new_freq)

    def _remove(self, idx: int) -> None:
        val = self._array[idx]
        old_freq = self._count[val]
        new_freq = old_freq - 1

        self._freq_count[old_freq] -= 1

        if new_freq > 0:
            self._count[val] = new_freq
            self._freq_count[new_freq] = self._freq_count.get(new_freq, 0) + 1
        else:
            del self._count[val]

        # Update max_freq if needed
        while self._max_freq > 0 and self._freq_count.get(self._max_freq, 0) == 0:
            self._max_freq -= 1

    def _get_answer(self) -> int:
        """Get maximum frequency."""
        return self._max_freq

    def add_query(self, left: int, right: int) -> int:
        """Add query [left, right]."""
        return self._mo.add_query(left, right)

    def process(self) -> List[int]:
        """Process all queries, returns max frequency for each."""
        self._count = {}
        self._freq_count = {}
        self._max_freq = 0
        return self._mo.process()


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_mo() -> MoAlgorithmEngine:
    """Create Mo's Algorithm engine."""
    return MoAlgorithmEngine()


def distinct_count_queries(
    array: List[int],
    queries: List[Tuple[int, int]]
) -> List[int]:
    """
    Answer distinct count queries.

    Args:
        array: Input array
        queries: List of (left, right) queries

    Returns:
        List of distinct counts
    """
    mo = DistinctCountMo(array)

    for left, right in queries:
        mo.add_query(left, right)

    return mo.process()


def mode_queries(
    array: List[int],
    queries: List[Tuple[int, int]]
) -> List[int]:
    """
    Answer mode (max frequency) queries.

    Args:
        array: Input array
        queries: List of (left, right) queries

    Returns:
        List of max frequencies
    """
    mo = ModeMo(array)

    for left, right in queries:
        mo.add_query(left, right)

    return mo.process()
