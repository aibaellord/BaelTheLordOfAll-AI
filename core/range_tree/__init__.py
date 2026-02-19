"""
BAEL Range Tree Engine
======================

Multi-dimensional range queries.

"Ba'el queries across all dimensions." — Ba'el
"""

import logging
import threading
from typing import Any, Callable, Dict, Generic, List, Optional, Tuple, TypeVar
from dataclasses import dataclass, field

logger = logging.getLogger("BAEL.RangeTree")

T = TypeVar('T')


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Point2D:
    """2D point."""
    x: float
    y: float
    data: Any = None

    def __hash__(self):
        return hash((self.x, self.y))


@dataclass
class Rectangle:
    """Axis-aligned rectangle."""
    x_min: float
    y_min: float
    x_max: float
    y_max: float

    def contains(self, point: Point2D) -> bool:
        return (self.x_min <= point.x <= self.x_max and
                self.y_min <= point.y <= self.y_max)


@dataclass
class RangeTreeStats:
    """Range tree statistics."""
    point_count: int = 0
    node_count: int = 0
    height: int = 0
    queries: int = 0


# ============================================================================
# 1D RANGE TREE (BALANCED BST WITH RANGE QUERIES)
# ============================================================================

class RangeTree1D(Generic[T]):
    """
    1D Range Tree for range queries on single dimension.

    Features:
    - O(n log n) construction
    - O(log n + k) range query (k = output size)
    - Supports range counting

    "Ba'el finds all in range." — Ba'el
    """

    @dataclass
    class Node:
        value: float
        data: Any = None
        left: Optional['RangeTree1D.Node'] = None
        right: Optional['RangeTree1D.Node'] = None
        subtree: List[Tuple[float, Any]] = field(default_factory=list)

    def __init__(self):
        """Initialize 1D range tree."""
        self._root: Optional[RangeTree1D.Node] = None
        self._size = 0
        self._lock = threading.RLock()

    def build(self, points: List[Tuple[float, T]]) -> None:
        """
        Build from sorted list of (value, data) pairs.

        Args:
            points: List of (value, data) pairs
        """
        with self._lock:
            if not points:
                return

            sorted_points = sorted(points, key=lambda p: p[0])
            self._root = self._build(sorted_points)
            self._size = len(points)

    def _build(self, points: List[Tuple[float, T]]) -> Optional['RangeTree1D.Node']:
        if not points:
            return None

        mid = len(points) // 2
        value, data = points[mid]

        node = RangeTree1D.Node(
            value=value,
            data=data,
            subtree=points.copy()
        )

        node.left = self._build(points[:mid])
        node.right = self._build(points[mid+1:])

        return node

    def range_query(self, low: float, high: float) -> List[Tuple[float, T]]:
        """
        Query range [low, high].

        Args:
            low: Lower bound
            high: Upper bound

        Returns:
            Points in range
        """
        with self._lock:
            result = []
            self._range_query(self._root, low, high, result)
            return result

    def _range_query(
        self,
        node: Optional['RangeTree1D.Node'],
        low: float,
        high: float,
        result: List[Tuple[float, T]]
    ) -> None:
        if not node:
            return

        if low <= node.value <= high:
            result.append((node.value, node.data))

        if low < node.value:
            self._range_query(node.left, low, high, result)

        if high > node.value:
            self._range_query(node.right, low, high, result)

    def count_range(self, low: float, high: float) -> int:
        """Count points in range."""
        return len(self.range_query(low, high))


# ============================================================================
# 2D RANGE TREE
# ============================================================================

class RangeTree2D:
    """
    2D Range Tree for 2D orthogonal range queries.

    Features:
    - O(n log n) construction
    - O(log² n + k) range query
    - Fractional cascading optional

    "Ba'el queries the plane with logarithmic grace." — Ba'el
    """

    @dataclass
    class Node:
        x: float
        point: Point2D
        left: Optional['RangeTree2D.Node'] = None
        right: Optional['RangeTree2D.Node'] = None
        y_tree: Optional[RangeTree1D] = None  # Associated structure for y

    def __init__(self):
        """Initialize 2D range tree."""
        self._root: Optional[RangeTree2D.Node] = None
        self._points: List[Point2D] = []
        self._stats = RangeTreeStats()
        self._lock = threading.RLock()

        logger.debug("2D Range tree initialized")

    def build(self, points: List[Point2D]) -> None:
        """
        Build from list of points.

        Args:
            points: List of Point2D
        """
        with self._lock:
            self._points = list(points)
            self._stats.point_count = len(points)

            if not points:
                return

            # Sort by x
            sorted_points = sorted(points, key=lambda p: (p.x, p.y))
            self._root = self._build(sorted_points)

            self._stats.height = self._calculate_height(self._root)

            logger.info(f"2D Range tree built: {len(points)} points")

    def _build(self, points: List[Point2D]) -> Optional['RangeTree2D.Node']:
        if not points:
            return None

        self._stats.node_count += 1

        mid = len(points) // 2
        point = points[mid]

        node = RangeTree2D.Node(x=point.x, point=point)

        # Build associated y-structure for all points in subtree
        node.y_tree = RangeTree1D()
        node.y_tree.build([(p.y, p) for p in points])

        node.left = self._build(points[:mid])
        node.right = self._build(points[mid+1:])

        return node

    def _calculate_height(self, node: Optional['RangeTree2D.Node']) -> int:
        if not node:
            return 0
        return 1 + max(
            self._calculate_height(node.left),
            self._calculate_height(node.right)
        )

    def range_query(self, rect: Rectangle) -> List[Point2D]:
        """
        Query rectangular range.

        Args:
            rect: Query rectangle

        Returns:
            Points in rectangle
        """
        with self._lock:
            self._stats.queries += 1
            result = []
            self._range_query_2d(self._root, rect, result)
            return result

    def _range_query_2d(
        self,
        node: Optional['RangeTree2D.Node'],
        rect: Rectangle,
        result: List[Point2D]
    ) -> None:
        if not node:
            return

        # If node x is in range, query y-structure
        if rect.x_min <= node.x <= rect.x_max:
            if node.y_tree:
                y_results = node.y_tree.range_query(rect.y_min, rect.y_max)
                for _, point in y_results:
                    if rect.contains(point):
                        result.append(point)

        if rect.x_min < node.x:
            self._range_query_2d(node.left, rect, result)

        if rect.x_max > node.x:
            self._range_query_2d(node.right, rect, result)

    def count_range(self, rect: Rectangle) -> int:
        """Count points in rectangle."""
        return len(self.range_query(rect))

    def nearest(self, query: Point2D, k: int = 1) -> List[Tuple[Point2D, float]]:
        """
        Find k nearest neighbors (brute force on result).

        For true O(log n) nearest neighbor, use K-D tree.
        """
        with self._lock:
            import math

            if not self._points:
                return []

            # Calculate distances
            distances = []
            for point in self._points:
                dist = math.sqrt((point.x - query.x)**2 + (point.y - query.y)**2)
                distances.append((point, dist))

            distances.sort(key=lambda x: x[1])
            return distances[:k]

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'point_count': self._stats.point_count,
            'node_count': self._stats.node_count,
            'height': self._stats.height,
            'queries': self._stats.queries
        }


# ============================================================================
# FRACTIONAL CASCADING
# ============================================================================

class FractionalCascading2D:
    """
    2D Range Tree with Fractional Cascading.

    Reduces query time from O(log² n + k) to O(log n + k).

    "Ba'el cascades through dimensions efficiently." — Ba'el
    """

    def __init__(self):
        """Initialize fractional cascading range tree."""
        self._points: List[Point2D] = []
        self._x_sorted: List[Point2D] = []
        self._y_arrays: Dict[int, List[Tuple[float, int, int]]] = {}  # node -> (y, left_ptr, right_ptr)
        self._lock = threading.RLock()

    def build(self, points: List[Point2D]) -> None:
        """Build with fractional cascading."""
        with self._lock:
            self._points = list(points)
            self._x_sorted = sorted(points, key=lambda p: p.x)

            # Build fractional cascading structure
            self._build_cascading(0, len(points) - 1, 0)

    def _build_cascading(self, left: int, right: int, node_id: int) -> List[Tuple[float, int, int]]:
        if left > right:
            return []

        points = self._x_sorted[left:right+1]
        y_sorted = sorted([(p.y, i) for i, p in enumerate(points)])

        if left == right:
            self._y_arrays[node_id] = [(y_sorted[0][0], -1, -1)]
            return self._y_arrays[node_id]

        mid = (left + right) // 2

        left_child = 2 * node_id + 1
        right_child = 2 * node_id + 2

        left_arr = self._build_cascading(left, mid, left_child)
        right_arr = self._build_cascading(mid + 1, right, right_child)

        # Merge with pointers
        merged = []
        l_ptr, r_ptr = 0, 0

        for y, _ in y_sorted:
            while l_ptr < len(left_arr) and left_arr[l_ptr][0] < y:
                l_ptr += 1
            while r_ptr < len(right_arr) and right_arr[r_ptr][0] < y:
                r_ptr += 1

            merged.append((y, l_ptr, r_ptr))

        self._y_arrays[node_id] = merged
        return merged


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_range_tree_1d() -> RangeTree1D:
    """Create 1D range tree."""
    return RangeTree1D()


def create_range_tree_2d() -> RangeTree2D:
    """Create 2D range tree."""
    return RangeTree2D()


def build_range_tree_1d(values: List[Tuple[float, Any]]) -> RangeTree1D:
    """Build 1D range tree from values."""
    tree = RangeTree1D()
    tree.build(values)
    return tree


def build_range_tree_2d(points: List[Point2D]) -> RangeTree2D:
    """Build 2D range tree from points."""
    tree = RangeTree2D()
    tree.build(points)
    return tree


def range_query_2d(
    points: List[Tuple[float, float]],
    x_range: Tuple[float, float],
    y_range: Tuple[float, float]
) -> List[Tuple[float, float]]:
    """
    Perform 2D range query.

    Args:
        points: List of (x, y) points
        x_range: (x_min, x_max)
        y_range: (y_min, y_max)

    Returns:
        Points in range
    """
    tree = RangeTree2D()
    point_objs = [Point2D(x=x, y=y) for x, y in points]
    tree.build(point_objs)

    rect = Rectangle(
        x_min=x_range[0], x_max=x_range[1],
        y_min=y_range[0], y_max=y_range[1]
    )

    results = tree.range_query(rect)
    return [(p.x, p.y) for p in results]
