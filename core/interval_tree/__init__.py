"""
BAEL Interval Tree Engine Implementation
==========================================

Interval overlap queries with O(log n) performance.

"Ba'el sees all overlapping truths." — Ba'el
"""

import logging
import threading
from typing import Any, Callable, Dict, Generic, Iterator, List, Optional, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("BAEL.IntervalTree")

T = TypeVar('T')  # Value type


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Interval(Generic[T]):
    """An interval with associated value."""
    start: float
    end: float
    value: T

    def __post_init__(self):
        if self.start > self.end:
            raise ValueError(f"Invalid interval: start ({self.start}) > end ({self.end})")

    @property
    def length(self) -> float:
        """Get interval length."""
        return self.end - self.start

    @property
    def midpoint(self) -> float:
        """Get interval midpoint."""
        return (self.start + self.end) / 2

    def overlaps(self, other: 'Interval') -> bool:
        """Check if intervals overlap."""
        return self.start < other.end and other.start < self.end

    def contains(self, point: float) -> bool:
        """Check if interval contains point."""
        return self.start <= point <= self.end

    def contains_interval(self, other: 'Interval') -> bool:
        """Check if this interval contains another."""
        return self.start <= other.start and other.end <= self.end

    def __lt__(self, other: 'Interval') -> bool:
        """Comparison for sorting."""
        return (self.start, self.end) < (other.start, other.end)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Interval):
            return False
        return self.start == other.start and self.end == other.end

    def __hash__(self) -> int:
        return hash((self.start, self.end))

    def __repr__(self) -> str:
        return f"[{self.start}, {self.end}]"


class IntervalNode(Generic[T]):
    """Node in interval tree."""

    def __init__(self, center: float):
        """Initialize node."""
        self.center = center

        # Intervals that span the center
        self.intervals: List[Interval[T]] = []

        # Sorted by start and end for efficient queries
        self.by_start: List[Interval[T]] = []
        self.by_end: List[Interval[T]] = []

        # Children
        self.left: Optional['IntervalNode[T]'] = None
        self.right: Optional['IntervalNode[T]'] = None

    def add_interval(self, interval: Interval[T]) -> None:
        """Add interval to node."""
        self.intervals.append(interval)

        # Keep sorted lists
        self.by_start = sorted(self.intervals, key=lambda i: i.start)
        self.by_end = sorted(self.intervals, key=lambda i: i.end, reverse=True)


@dataclass
class IntervalTreeConfig:
    """Interval tree configuration."""
    min_intervals_for_split: int = 10


# ============================================================================
# INTERVAL TREE ENGINE
# ============================================================================

class IntervalTreeEngine(Generic[T]):
    """
    Augmented interval tree.

    Features:
    - O(log n + k) overlap queries
    - Point stabbing queries
    - Range queries

    "Ba'el perceives all overlapping dimensions." — Ba'el
    """

    def __init__(self, config: Optional[IntervalTreeConfig] = None):
        """Initialize interval tree."""
        self.config = config or IntervalTreeConfig()

        self.root: Optional[IntervalNode[T]] = None
        self._intervals: List[Interval[T]] = []
        self._count = 0

        self._lock = threading.RLock()

        logger.info("Interval tree initialized")

    # ========================================================================
    # BUILDING
    # ========================================================================

    def add(
        self,
        start: float,
        end: float,
        value: T
    ) -> Interval[T]:
        """
        Add an interval.

        Args:
            start: Start of interval
            end: End of interval
            value: Associated value

        Returns:
            Created interval
        """
        interval = Interval(start, end, value)

        with self._lock:
            self._intervals.append(interval)
            self._count += 1

            # Rebuild tree
            self._rebuild()

        return interval

    def add_interval(self, interval: Interval[T]) -> None:
        """Add an existing interval."""
        with self._lock:
            self._intervals.append(interval)
            self._count += 1
            self._rebuild()

    def remove(self, interval: Interval[T]) -> bool:
        """
        Remove an interval.

        Args:
            interval: Interval to remove

        Returns:
            True if removed
        """
        with self._lock:
            try:
                self._intervals.remove(interval)
                self._count -= 1
                self._rebuild()
                return True
            except ValueError:
                return False

    def _rebuild(self) -> None:
        """Rebuild the tree."""
        if not self._intervals:
            self.root = None
            return

        self.root = self._build_node(self._intervals.copy())

    def _build_node(
        self,
        intervals: List[Interval[T]]
    ) -> Optional[IntervalNode[T]]:
        """Build node from intervals."""
        if not intervals:
            return None

        # Find center point
        all_points = []
        for i in intervals:
            all_points.extend([i.start, i.end])
        all_points.sort()
        center = all_points[len(all_points) // 2]

        node = IntervalNode(center)

        left_intervals = []
        right_intervals = []

        for interval in intervals:
            if interval.end < center:
                left_intervals.append(interval)
            elif interval.start > center:
                right_intervals.append(interval)
            else:
                # Interval spans center
                node.add_interval(interval)

        # Build children
        if left_intervals:
            node.left = self._build_node(left_intervals)
        if right_intervals:
            node.right = self._build_node(right_intervals)

        return node

    # ========================================================================
    # QUERIES
    # ========================================================================

    def query_point(self, point: float) -> List[Interval[T]]:
        """
        Find all intervals containing a point.

        Args:
            point: Query point

        Returns:
            List of overlapping intervals
        """
        result: List[Interval[T]] = []

        with self._lock:
            self._query_point_node(self.root, point, result)

        return result

    def _query_point_node(
        self,
        node: Optional[IntervalNode[T]],
        point: float,
        result: List[Interval[T]]
    ) -> None:
        """Query point in subtree."""
        if node is None:
            return

        if point < node.center:
            # Check intervals sorted by start
            for interval in node.by_start:
                if interval.start <= point:
                    if point <= interval.end:
                        result.append(interval)
                else:
                    break

            self._query_point_node(node.left, point, result)

        else:
            # Check intervals sorted by end
            for interval in node.by_end:
                if interval.end >= point:
                    if point >= interval.start:
                        result.append(interval)
                else:
                    break

            self._query_point_node(node.right, point, result)

    def query_overlap(
        self,
        start: float,
        end: float
    ) -> List[Interval[T]]:
        """
        Find all intervals overlapping with range.

        Args:
            start: Range start
            end: Range end

        Returns:
            List of overlapping intervals
        """
        query = Interval(start, end, None)
        result: List[Interval[T]] = []

        with self._lock:
            self._query_overlap_node(self.root, query, result)

        return result

    def _query_overlap_node(
        self,
        node: Optional[IntervalNode[T]],
        query: Interval,
        result: List[Interval[T]]
    ) -> None:
        """Query overlap in subtree."""
        if node is None:
            return

        # Check intervals at this node
        for interval in node.intervals:
            if interval.overlaps(query):
                result.append(interval)

        # Check left subtree
        if node.left and query.start < node.center:
            self._query_overlap_node(node.left, query, result)

        # Check right subtree
        if node.right and query.end > node.center:
            self._query_overlap_node(node.right, query, result)

    def query_containing(
        self,
        start: float,
        end: float
    ) -> List[Interval[T]]:
        """
        Find all intervals containing the given range.

        Args:
            start: Range start
            end: Range end

        Returns:
            List of containing intervals
        """
        query = Interval(start, end, None)
        result: List[Interval[T]] = []

        with self._lock:
            for interval in self._intervals:
                if interval.contains_interval(query):
                    result.append(interval)

        return result

    def query_contained(
        self,
        start: float,
        end: float
    ) -> List[Interval[T]]:
        """
        Find all intervals contained within the given range.

        Args:
            start: Range start
            end: Range end

        Returns:
            List of contained intervals
        """
        container = Interval(start, end, None)
        result: List[Interval[T]] = []

        with self._lock:
            for interval in self._intervals:
                if container.contains_interval(interval):
                    result.append(interval)

        return result

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def all_intervals(self) -> List[Interval[T]]:
        """Get all intervals."""
        return self._intervals.copy()

    def __len__(self) -> int:
        """Get number of intervals."""
        return self._count

    def __iter__(self) -> Iterator[Interval[T]]:
        """Iterate all intervals."""
        return iter(self._intervals)

    def __contains__(self, interval: Interval[T]) -> bool:
        """Check if interval exists."""
        return interval in self._intervals

    def clear(self) -> None:
        """Clear all intervals."""
        with self._lock:
            self._intervals.clear()
            self._count = 0
            self.root = None

    def find_gaps(
        self,
        start: float,
        end: float
    ) -> List[Tuple[float, float]]:
        """
        Find gaps (uncovered regions) in range.

        Args:
            start: Range start
            end: Range end

        Returns:
            List of (start, end) gaps
        """
        # Get overlapping intervals
        overlapping = self.query_overlap(start, end)

        if not overlapping:
            return [(start, end)]

        # Sort by start
        overlapping.sort(key=lambda i: i.start)

        gaps = []
        current = start

        for interval in overlapping:
            if interval.start > current:
                gaps.append((current, interval.start))
            current = max(current, interval.end)

        if current < end:
            gaps.append((current, end))

        return gaps

    def merge_overlapping(self) -> List[Interval[T]]:
        """
        Merge overlapping intervals.

        Returns:
            List of merged intervals
        """
        if not self._intervals:
            return []

        sorted_intervals = sorted(self._intervals, key=lambda i: i.start)

        merged = [sorted_intervals[0]]

        for interval in sorted_intervals[1:]:
            last = merged[-1]

            if interval.start <= last.end:
                # Merge
                merged[-1] = Interval(
                    last.start,
                    max(last.end, interval.end),
                    last.value  # Keep first value
                )
            else:
                merged.append(interval)

        return merged

    def get_stats(self) -> Dict[str, Any]:
        """Get tree statistics."""
        total_coverage = sum(i.length for i in self._intervals)

        return {
            'count': self._count,
            'total_coverage': total_coverage,
            'avg_length': total_coverage / self._count if self._count else 0
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_interval_tree() -> IntervalTreeEngine:
    """Create a new interval tree."""
    return IntervalTreeEngine()


def from_ranges(
    ranges: List[Tuple[float, float, Any]]
) -> IntervalTreeEngine:
    """
    Create interval tree from list of (start, end, value) tuples.

    Args:
        ranges: List of (start, end, value)

    Returns:
        IntervalTreeEngine
    """
    tree = IntervalTreeEngine()
    for start, end, value in ranges:
        tree.add(start, end, value)
    return tree
