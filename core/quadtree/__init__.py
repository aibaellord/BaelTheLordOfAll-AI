"""
BAEL Quadtree Engine
====================

Spatial partitioning for 2D data.

"Ba'el quarters space." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Tuple, Generic, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto
import math

logger = logging.getLogger("BAEL.Quadtree")


V = TypeVar('V')


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Point2D:
    """2D point."""
    x: float
    y: float

    def distance_to(self, other: 'Point2D') -> float:
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)


@dataclass
class Rectangle:
    """Axis-aligned rectangle."""
    x: float  # Center x
    y: float  # Center y
    half_width: float
    half_height: float

    def contains(self, point: Point2D) -> bool:
        return (abs(point.x - self.x) <= self.half_width and
                abs(point.y - self.y) <= self.half_height)

    def intersects(self, other: 'Rectangle') -> bool:
        return not (other.x - other.half_width > self.x + self.half_width or
                   other.x + other.half_width < self.x - self.half_width or
                   other.y - other.half_height > self.y + self.half_height or
                   other.y + other.half_height < self.y - self.half_height)


@dataclass
class QuadtreeStats:
    """Quadtree statistics."""
    num_points: int
    depth: int
    num_nodes: int
    capacity: int


# ============================================================================
# QUADTREE
# ============================================================================

class Quadtree(Generic[V]):
    """
    Quadtree for spatial indexing.

    Features:
    - O(log n) insertion (average)
    - O(log n + k) range queries
    - O(log n + k) nearest neighbor

    "Ba'el divides to conquer space." — Ba'el
    """

    def __init__(
        self,
        boundary: Rectangle,
        capacity: int = 4,
        max_depth: int = 20
    ):
        """
        Initialize quadtree.

        Args:
            boundary: Bounding rectangle
            capacity: Points per node before splitting
            max_depth: Maximum tree depth
        """
        self._boundary = boundary
        self._capacity = capacity
        self._max_depth = max_depth
        self._depth = 0

        self._points: List[Tuple[Point2D, V]] = []
        self._divided = False

        self._nw: Optional['Quadtree[V]'] = None
        self._ne: Optional['Quadtree[V]'] = None
        self._sw: Optional['Quadtree[V]'] = None
        self._se: Optional['Quadtree[V]'] = None

        self._lock = threading.RLock()

    def _subdivide(self):
        """Create four children."""
        x = self._boundary.x
        y = self._boundary.y
        hw = self._boundary.half_width / 2
        hh = self._boundary.half_height / 2

        nw_bound = Rectangle(x - hw, y + hh, hw, hh)
        ne_bound = Rectangle(x + hw, y + hh, hw, hh)
        sw_bound = Rectangle(x - hw, y - hh, hw, hh)
        se_bound = Rectangle(x + hw, y - hh, hw, hh)

        self._nw = Quadtree(nw_bound, self._capacity, self._max_depth)
        self._ne = Quadtree(ne_bound, self._capacity, self._max_depth)
        self._sw = Quadtree(sw_bound, self._capacity, self._max_depth)
        self._se = Quadtree(se_bound, self._capacity, self._max_depth)

        self._nw._depth = self._depth + 1
        self._ne._depth = self._depth + 1
        self._sw._depth = self._depth + 1
        self._se._depth = self._depth + 1

        self._divided = True

    def insert(self, x: float, y: float, value: V) -> bool:
        """
        Insert point with value.

        Returns False if point outside boundary.
        """
        point = Point2D(x, y)

        with self._lock:
            return self._insert(point, value)

    def _insert(self, point: Point2D, value: V) -> bool:
        if not self._boundary.contains(point):
            return False

        if len(self._points) < self._capacity or self._depth >= self._max_depth:
            self._points.append((point, value))
            return True

        if not self._divided:
            self._subdivide()

        if self._nw._insert(point, value):
            return True
        if self._ne._insert(point, value):
            return True
        if self._sw._insert(point, value):
            return True
        if self._se._insert(point, value):
            return True

        return False

    def query_range(self, x: float, y: float, width: float, height: float) -> List[Tuple[Point2D, V]]:
        """
        Find all points in rectangle.

        Args:
            x, y: Center of query rectangle
            width, height: Full width and height
        """
        range_rect = Rectangle(x, y, width / 2, height / 2)

        with self._lock:
            found = []
            self._query_range(range_rect, found)
            return found

    def _query_range(self, range_rect: Rectangle, found: List):
        if not self._boundary.intersects(range_rect):
            return

        for point, value in self._points:
            if range_rect.contains(point):
                found.append((point, value))

        if self._divided:
            self._nw._query_range(range_rect, found)
            self._ne._query_range(range_rect, found)
            self._sw._query_range(range_rect, found)
            self._se._query_range(range_rect, found)

    def query_circle(self, x: float, y: float, radius: float) -> List[Tuple[Point2D, V]]:
        """Find all points within radius of (x, y)."""
        center = Point2D(x, y)

        with self._lock:
            found = []
            self._query_circle(center, radius, found)
            return found

    def _query_circle(self, center: Point2D, radius: float, found: List):
        # Use bounding rectangle for initial filter
        if not self._boundary.intersects(Rectangle(center.x, center.y, radius, radius)):
            return

        for point, value in self._points:
            if point.distance_to(center) <= radius:
                found.append((point, value))

        if self._divided:
            self._nw._query_circle(center, radius, found)
            self._ne._query_circle(center, radius, found)
            self._sw._query_circle(center, radius, found)
            self._se._query_circle(center, radius, found)

    def nearest(self, x: float, y: float, count: int = 1) -> List[Tuple[Point2D, V, float]]:
        """
        Find k nearest neighbors.

        Returns list of (point, value, distance).
        """
        query = Point2D(x, y)

        with self._lock:
            candidates = []
            self._collect_all(candidates)

            # Sort by distance
            candidates.sort(key=lambda pv: pv[0].distance_to(query))

            result = []
            for point, value in candidates[:count]:
                dist = point.distance_to(query)
                result.append((point, value, dist))

            return result

    def _collect_all(self, result: List):
        """Collect all points."""
        result.extend(self._points)

        if self._divided:
            self._nw._collect_all(result)
            self._ne._collect_all(result)
            self._sw._collect_all(result)
            self._se._collect_all(result)

    def count(self) -> int:
        """Count all points."""
        with self._lock:
            total = len(self._points)
            if self._divided:
                total += self._nw.count()
                total += self._ne.count()
                total += self._sw.count()
                total += self._se.count()
            return total

    def __len__(self) -> int:
        return self.count()

    def get_stats(self) -> QuadtreeStats:
        """Get tree statistics."""
        with self._lock:
            def get_depth_and_nodes(node):
                if not node._divided:
                    return node._depth, 1

                depths_nodes = [
                    get_depth_and_nodes(node._nw),
                    get_depth_and_nodes(node._ne),
                    get_depth_and_nodes(node._sw),
                    get_depth_and_nodes(node._se)
                ]

                max_depth = max(d for d, _ in depths_nodes)
                total_nodes = 1 + sum(n for _, n in depths_nodes)
                return max_depth, total_nodes

            depth, nodes = get_depth_and_nodes(self)

            return QuadtreeStats(
                num_points=self.count(),
                depth=depth,
                num_nodes=nodes,
                capacity=self._capacity
            )


# ============================================================================
# POINT QUADTREE
# ============================================================================

class PointQuadtreeNode(Generic[V]):
    """Node in point quadtree."""

    def __init__(self, x: float, y: float, value: V):
        self.x = x
        self.y = y
        self.value = value
        self.nw: Optional['PointQuadtreeNode[V]'] = None
        self.ne: Optional['PointQuadtreeNode[V]'] = None
        self.sw: Optional['PointQuadtreeNode[V]'] = None
        self.se: Optional['PointQuadtreeNode[V]'] = None


class PointQuadtree(Generic[V]):
    """
    Point Quadtree: each point is a partition.

    "Ba'el points to divisions." — Ba'el
    """

    def __init__(self):
        """Initialize empty tree."""
        self._root: Optional[PointQuadtreeNode[V]] = None
        self._size = 0
        self._lock = threading.RLock()

    def insert(self, x: float, y: float, value: V):
        """Insert point."""
        with self._lock:
            if not self._root:
                self._root = PointQuadtreeNode(x, y, value)
            else:
                self._insert(self._root, x, y, value)
            self._size += 1

    def _insert(self, node: PointQuadtreeNode[V], x: float, y: float, value: V):
        if x < node.x:
            if y < node.y:
                # SW
                if node.sw:
                    self._insert(node.sw, x, y, value)
                else:
                    node.sw = PointQuadtreeNode(x, y, value)
            else:
                # NW
                if node.nw:
                    self._insert(node.nw, x, y, value)
                else:
                    node.nw = PointQuadtreeNode(x, y, value)
        else:
            if y < node.y:
                # SE
                if node.se:
                    self._insert(node.se, x, y, value)
                else:
                    node.se = PointQuadtreeNode(x, y, value)
            else:
                # NE
                if node.ne:
                    self._insert(node.ne, x, y, value)
                else:
                    node.ne = PointQuadtreeNode(x, y, value)

    def search(self, x: float, y: float) -> Optional[V]:
        """Find value at exact point."""
        with self._lock:
            node = self._root
            while node:
                if node.x == x and node.y == y:
                    return node.value

                if x < node.x:
                    node = node.sw if y < node.y else node.nw
                else:
                    node = node.se if y < node.y else node.ne

            return None

    def __len__(self) -> int:
        return self._size


# ============================================================================
# COMPRESSED QUADTREE
# ============================================================================

class CompressedQuadtree(Generic[V]):
    """
    Compressed Quadtree: O(n) space regardless of distribution.

    Collapses chains of single-child nodes.

    "Ba'el compresses space." — Ba'el
    """

    def __init__(self, boundary: Rectangle):
        """Initialize."""
        self._boundary = boundary
        self._point: Optional[Tuple[Point2D, V]] = None
        self._children: Optional[List['CompressedQuadtree[V]']] = None
        self._lock = threading.RLock()

    def insert(self, x: float, y: float, value: V) -> bool:
        """Insert point."""
        point = Point2D(x, y)

        with self._lock:
            if not self._boundary.contains(point):
                return False

            if self._point is None and self._children is None:
                self._point = (point, value)
                return True

            if self._point is not None:
                # Split
                old_point, old_value = self._point
                self._point = None
                self._create_children()
                self._insert_to_child(old_point, old_value)

            self._insert_to_child(point, value)
            return True

    def _create_children(self):
        """Create 4 children."""
        x = self._boundary.x
        y = self._boundary.y
        hw = self._boundary.half_width / 2
        hh = self._boundary.half_height / 2

        self._children = [
            CompressedQuadtree(Rectangle(x - hw, y + hh, hw, hh)),  # NW
            CompressedQuadtree(Rectangle(x + hw, y + hh, hw, hh)),  # NE
            CompressedQuadtree(Rectangle(x - hw, y - hh, hw, hh)),  # SW
            CompressedQuadtree(Rectangle(x + hw, y - hh, hw, hh)),  # SE
        ]

    def _insert_to_child(self, point: Point2D, value: V):
        """Insert to appropriate child."""
        for child in self._children:
            if child.insert(point.x, point.y, value):
                return


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_quadtree(
    x: float,
    y: float,
    width: float,
    height: float,
    capacity: int = 4
) -> Quadtree:
    """Create quadtree with given bounds."""
    boundary = Rectangle(x, y, width / 2, height / 2)
    return Quadtree(boundary, capacity)


def create_point_quadtree() -> PointQuadtree:
    """Create empty point quadtree."""
    return PointQuadtree()


def build_quadtree(
    points: List[Tuple[float, float, Any]],
    boundary: Optional[Tuple[float, float, float, float]] = None
) -> Quadtree:
    """
    Build quadtree from points.

    Args:
        points: List of (x, y, value)
        boundary: Optional (center_x, center_y, width, height)
    """
    if not points:
        return create_quadtree(0, 0, 100, 100)

    if boundary is None:
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        cx = (min_x + max_x) / 2
        cy = (min_y + max_y) / 2
        width = max(max_x - min_x, 1) * 1.1
        height = max(max_y - min_y, 1) * 1.1
    else:
        cx, cy, width, height = boundary

    tree = create_quadtree(cx, cy, width, height)

    for x, y, value in points:
        tree.insert(x, y, value)

    return tree
