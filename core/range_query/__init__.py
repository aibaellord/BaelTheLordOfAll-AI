"""
BAEL Range Query Engine
=======================

2D range query data structures.

"Ba'el queries regions efficiently." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Set, Tuple, Generic, TypeVar
from dataclasses import dataclass, field
from collections import defaultdict
import bisect

logger = logging.getLogger("BAEL.RangeQuery")

T = TypeVar('T')


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Point2D:
    """2D point with data."""
    x: float
    y: float
    data: Any = None
    index: int = -1


@dataclass
class Rectangle:
    """Axis-aligned rectangle."""
    x1: float  # left
    y1: float  # bottom
    x2: float  # right
    y2: float  # top

    def contains(self, x: float, y: float) -> bool:
        """Check if point is inside rectangle."""
        return self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2

    def intersects(self, other: 'Rectangle') -> bool:
        """Check if rectangles intersect."""
        return not (self.x2 < other.x1 or other.x2 < self.x1 or
                   self.y2 < other.y1 or other.y2 < self.y1)


@dataclass
class RangeQueryResult:
    """Result of range query."""
    points: List[Point2D] = field(default_factory=list)
    count: int = 0


# ============================================================================
# KD-TREE
# ============================================================================

class KDTreeNode:
    """Node in KD-tree."""

    def __init__(self, point: Point2D, axis: int):
        self.point = point
        self.axis = axis
        self.left: Optional['KDTreeNode'] = None
        self.right: Optional['KDTreeNode'] = None


class KDTree:
    """
    K-dimensional tree for 2D range queries.

    Features:
    - O(log n) insertion
    - O(√n + k) range query
    - O(log n) nearest neighbor

    "Ba'el partitions space optimally." — Ba'el
    """

    def __init__(self):
        """Initialize KD-tree."""
        self._root: Optional[KDTreeNode] = None
        self._size = 0
        self._lock = threading.RLock()

        logger.debug("KD-tree initialized")

    def insert(self, x: float, y: float, data: Any = None) -> int:
        """Insert point into tree."""
        with self._lock:
            point = Point2D(x, y, data, self._size)
            self._root = self._insert_recursive(self._root, point, 0)
            self._size += 1
            return point.index

    def _insert_recursive(
        self,
        node: Optional[KDTreeNode],
        point: Point2D,
        depth: int
    ) -> KDTreeNode:
        """Recursive insertion."""
        if node is None:
            return KDTreeNode(point, depth % 2)

        axis = depth % 2

        if axis == 0:  # Compare x
            if point.x < node.point.x:
                node.left = self._insert_recursive(node.left, point, depth + 1)
            else:
                node.right = self._insert_recursive(node.right, point, depth + 1)
        else:  # Compare y
            if point.y < node.point.y:
                node.left = self._insert_recursive(node.left, point, depth + 1)
            else:
                node.right = self._insert_recursive(node.right, point, depth + 1)

        return node

    def build(self, points: List[Tuple[float, float]]) -> None:
        """Build tree from list of points."""
        with self._lock:
            point_objs = [Point2D(x, y, None, i) for i, (x, y) in enumerate(points)]
            self._root = self._build_recursive(point_objs, 0)
            self._size = len(points)

    def _build_recursive(
        self,
        points: List[Point2D],
        depth: int
    ) -> Optional[KDTreeNode]:
        """Build tree recursively."""
        if not points:
            return None

        axis = depth % 2

        # Sort by axis
        points.sort(key=lambda p: p.x if axis == 0 else p.y)

        mid = len(points) // 2
        node = KDTreeNode(points[mid], axis)

        node.left = self._build_recursive(points[:mid], depth + 1)
        node.right = self._build_recursive(points[mid + 1:], depth + 1)

        return node

    def range_query(self, rect: Rectangle) -> List[Point2D]:
        """
        Find all points in rectangle.

        Returns:
            List of points in range
        """
        with self._lock:
            result = []
            self._range_query_recursive(self._root, rect, result)
            return result

    def _range_query_recursive(
        self,
        node: Optional[KDTreeNode],
        rect: Rectangle,
        result: List[Point2D]
    ) -> None:
        """Recursive range query."""
        if node is None:
            return

        # Check if current point is in range
        if rect.contains(node.point.x, node.point.y):
            result.append(node.point)

        axis = node.axis

        if axis == 0:  # x-axis
            if rect.x1 <= node.point.x:
                self._range_query_recursive(node.left, rect, result)
            if rect.x2 >= node.point.x:
                self._range_query_recursive(node.right, rect, result)
        else:  # y-axis
            if rect.y1 <= node.point.y:
                self._range_query_recursive(node.left, rect, result)
            if rect.y2 >= node.point.y:
                self._range_query_recursive(node.right, rect, result)

    def nearest_neighbor(self, x: float, y: float) -> Optional[Point2D]:
        """
        Find nearest neighbor to query point.

        Returns:
            Nearest point or None
        """
        with self._lock:
            if self._root is None:
                return None

            best = [None, float('inf')]  # [point, distance²]
            self._nearest_recursive(self._root, x, y, best)
            return best[0]

    def _nearest_recursive(
        self,
        node: Optional[KDTreeNode],
        x: float,
        y: float,
        best: List
    ) -> None:
        """Recursive nearest neighbor search."""
        if node is None:
            return

        # Compute distance to current point
        dist_sq = (node.point.x - x) ** 2 + (node.point.y - y) ** 2

        if dist_sq < best[1]:
            best[0] = node.point
            best[1] = dist_sq

        axis = node.axis

        if axis == 0:
            diff = x - node.point.x
        else:
            diff = y - node.point.y

        # Search closer subtree first
        if diff < 0:
            first, second = node.left, node.right
        else:
            first, second = node.right, node.left

        self._nearest_recursive(first, x, y, best)

        # Check if we need to search other subtree
        if diff ** 2 < best[1]:
            self._nearest_recursive(second, x, y, best)

    def k_nearest(self, x: float, y: float, k: int) -> List[Point2D]:
        """
        Find k nearest neighbors.

        Returns:
            List of k nearest points sorted by distance
        """
        with self._lock:
            import heapq

            # Max heap (negative distances)
            heap = []
            self._k_nearest_recursive(self._root, x, y, k, heap)

            # Extract and sort
            result = [point for _, point in sorted(heap, key=lambda x: -x[0])]
            return result

    def _k_nearest_recursive(
        self,
        node: Optional[KDTreeNode],
        x: float,
        y: float,
        k: int,
        heap: List
    ) -> None:
        """Recursive k-nearest search."""
        if node is None:
            return

        import heapq

        dist_sq = (node.point.x - x) ** 2 + (node.point.y - y) ** 2

        if len(heap) < k:
            heapq.heappush(heap, (-dist_sq, node.point))
        elif -heap[0][0] > dist_sq:
            heapq.heapreplace(heap, (-dist_sq, node.point))

        axis = node.axis

        if axis == 0:
            diff = x - node.point.x
        else:
            diff = y - node.point.y

        if diff < 0:
            first, second = node.left, node.right
        else:
            first, second = node.right, node.left

        self._k_nearest_recursive(first, x, y, k, heap)

        if len(heap) < k or diff ** 2 < -heap[0][0]:
            self._k_nearest_recursive(second, x, y, k, heap)


# ============================================================================
# RANGE TREE (2D)
# ============================================================================

class RangeTreeNode:
    """Node in 2D range tree."""

    def __init__(self, x: float):
        self.x = x
        self.left: Optional['RangeTreeNode'] = None
        self.right: Optional['RangeTreeNode'] = None
        self.y_sorted: List[Point2D] = []  # Associated structure


class RangeTree2D:
    """
    2D Range Tree for orthogonal range queries.

    Features:
    - O(log² n + k) range query
    - Fractional cascading possible for O(log n + k)

    "Ba'el queries in two dimensions." — Ba'el
    """

    def __init__(self):
        """Initialize range tree."""
        self._root: Optional[RangeTreeNode] = None
        self._points: List[Point2D] = []
        self._lock = threading.RLock()

    def build(self, points: List[Tuple[float, float]]) -> None:
        """Build range tree from points."""
        with self._lock:
            self._points = [Point2D(x, y, None, i) for i, (x, y) in enumerate(points)]
            self._points.sort(key=lambda p: p.x)
            self._root = self._build_recursive(self._points)

    def _build_recursive(self, points: List[Point2D]) -> Optional[RangeTreeNode]:
        """Build tree recursively."""
        if not points:
            return None

        mid = len(points) // 2
        node = RangeTreeNode(points[mid].x)

        # Store all points sorted by y
        node.y_sorted = sorted(points, key=lambda p: p.y)

        node.left = self._build_recursive(points[:mid])
        node.right = self._build_recursive(points[mid + 1:])

        return node

    def range_query(self, x1: float, x2: float, y1: float, y2: float) -> List[Point2D]:
        """
        Find points in rectangle [x1, x2] × [y1, y2].

        Returns:
            List of points in range
        """
        with self._lock:
            result = []
            self._range_query_recursive(self._root, x1, x2, y1, y2, result)
            return result

    def _range_query_recursive(
        self,
        node: Optional[RangeTreeNode],
        x1: float,
        x2: float,
        y1: float,
        y2: float,
        result: List[Point2D]
    ) -> None:
        """Recursive range query."""
        if node is None:
            return

        if x1 <= node.x <= x2:
            # Search in y-sorted list
            for p in node.y_sorted:
                if x1 <= p.x <= x2 and y1 <= p.y <= y2:
                    result.append(p)

        if x1 < node.x:
            self._range_query_recursive(node.left, x1, x2, y1, y2, result)
        if x2 > node.x:
            self._range_query_recursive(node.right, x1, x2, y1, y2, result)


# ============================================================================
# QUADTREE
# ============================================================================

class QuadTreeNode:
    """Node in quadtree."""

    def __init__(self, x1: float, y1: float, x2: float, y2: float, capacity: int = 4):
        self.boundary = Rectangle(x1, y1, x2, y2)
        self.capacity = capacity
        self.points: List[Point2D] = []
        self.divided = False
        self.nw: Optional['QuadTreeNode'] = None
        self.ne: Optional['QuadTreeNode'] = None
        self.sw: Optional['QuadTreeNode'] = None
        self.se: Optional['QuadTreeNode'] = None


class QuadTree:
    """
    Quadtree for 2D spatial queries.

    Features:
    - Variable depth based on data
    - O(log n) average operations
    - Good for clustered data

    "Ba'el divides space into four." — Ba'el
    """

    def __init__(
        self,
        x1: float = 0,
        y1: float = 0,
        x2: float = 1000,
        y2: float = 1000,
        capacity: int = 4
    ):
        """Initialize quadtree."""
        self._root = QuadTreeNode(x1, y1, x2, y2, capacity)
        self._size = 0
        self._lock = threading.RLock()

        logger.debug("Quadtree initialized")

    def insert(self, x: float, y: float, data: Any = None) -> bool:
        """Insert point into quadtree."""
        with self._lock:
            point = Point2D(x, y, data, self._size)
            result = self._insert_recursive(self._root, point)
            if result:
                self._size += 1
            return result

    def _insert_recursive(self, node: QuadTreeNode, point: Point2D) -> bool:
        """Recursive insertion."""
        if not node.boundary.contains(point.x, point.y):
            return False

        if len(node.points) < node.capacity and not node.divided:
            node.points.append(point)
            return True

        if not node.divided:
            self._subdivide(node)

        if self._insert_recursive(node.nw, point):
            return True
        if self._insert_recursive(node.ne, point):
            return True
        if self._insert_recursive(node.sw, point):
            return True
        if self._insert_recursive(node.se, point):
            return True

        return False

    def _subdivide(self, node: QuadTreeNode) -> None:
        """Subdivide node into 4 quadrants."""
        b = node.boundary
        mx = (b.x1 + b.x2) / 2
        my = (b.y1 + b.y2) / 2

        node.nw = QuadTreeNode(b.x1, my, mx, b.y2, node.capacity)
        node.ne = QuadTreeNode(mx, my, b.x2, b.y2, node.capacity)
        node.sw = QuadTreeNode(b.x1, b.y1, mx, my, node.capacity)
        node.se = QuadTreeNode(mx, b.y1, b.x2, my, node.capacity)

        node.divided = True

        # Redistribute points
        for p in node.points:
            self._insert_recursive(node.nw, p) or \
            self._insert_recursive(node.ne, p) or \
            self._insert_recursive(node.sw, p) or \
            self._insert_recursive(node.se, p)

        node.points = []

    def range_query(self, rect: Rectangle) -> List[Point2D]:
        """Find all points in rectangle."""
        with self._lock:
            result = []
            self._range_query_recursive(self._root, rect, result)
            return result

    def _range_query_recursive(
        self,
        node: QuadTreeNode,
        rect: Rectangle,
        result: List[Point2D]
    ) -> None:
        """Recursive range query."""
        if not node.boundary.intersects(rect):
            return

        for p in node.points:
            if rect.contains(p.x, p.y):
                result.append(p)

        if node.divided:
            self._range_query_recursive(node.nw, rect, result)
            self._range_query_recursive(node.ne, rect, result)
            self._range_query_recursive(node.sw, rect, result)
            self._range_query_recursive(node.se, rect, result)


# ============================================================================
# R-TREE (SIMPLIFIED)
# ============================================================================

class RTreeNode:
    """Node in R-tree."""

    def __init__(self, is_leaf: bool = True, max_entries: int = 4):
        self.is_leaf = is_leaf
        self.max_entries = max_entries
        self.mbr = Rectangle(float('inf'), float('inf'), float('-inf'), float('-inf'))
        self.children: List['RTreeNode'] = []
        self.entries: List[Tuple[Rectangle, Any]] = []  # For leaves: (point_rect, data)


class RTree:
    """
    R-tree for spatial indexing.

    Features:
    - Minimum bounding rectangles
    - Good for rectangle queries
    - Balanced tree structure

    "Ba'el indexes rectangles." — Ba'el
    """

    def __init__(self, max_entries: int = 4):
        """Initialize R-tree."""
        self._root = RTreeNode(is_leaf=True, max_entries=max_entries)
        self._max_entries = max_entries
        self._size = 0
        self._lock = threading.RLock()

    def insert(self, x: float, y: float, data: Any = None) -> None:
        """Insert point."""
        with self._lock:
            rect = Rectangle(x, y, x, y)
            self._insert(self._root, rect, data)
            self._size += 1

    def _insert(self, node: RTreeNode, rect: Rectangle, data: Any) -> Optional[RTreeNode]:
        """Recursive insertion."""
        self._expand_mbr(node.mbr, rect)

        if node.is_leaf:
            node.entries.append((rect, data))

            if len(node.entries) > self._max_entries:
                return self._split_leaf(node)
            return None

        # Choose subtree
        best_child = min(node.children,
                        key=lambda c: self._enlargement(c.mbr, rect))

        new_node = self._insert(best_child, rect, data)

        if new_node:
            node.children.append(new_node)
            self._expand_mbr(node.mbr, new_node.mbr)

            if len(node.children) > self._max_entries:
                return self._split_internal(node)

        return None

    def _expand_mbr(self, mbr: Rectangle, rect: Rectangle) -> None:
        """Expand MBR to include rectangle."""
        mbr.x1 = min(mbr.x1, rect.x1)
        mbr.y1 = min(mbr.y1, rect.y1)
        mbr.x2 = max(mbr.x2, rect.x2)
        mbr.y2 = max(mbr.y2, rect.y2)

    def _enlargement(self, mbr: Rectangle, rect: Rectangle) -> float:
        """Compute area enlargement needed."""
        new_mbr = Rectangle(
            min(mbr.x1, rect.x1),
            min(mbr.y1, rect.y1),
            max(mbr.x2, rect.x2),
            max(mbr.y2, rect.y2)
        )

        old_area = (mbr.x2 - mbr.x1) * (mbr.y2 - mbr.y1)
        new_area = (new_mbr.x2 - new_mbr.x1) * (new_mbr.y2 - new_mbr.y1)

        return new_area - old_area

    def _split_leaf(self, node: RTreeNode) -> RTreeNode:
        """Split leaf node."""
        # Simple linear split
        node.entries.sort(key=lambda e: e[0].x1)
        mid = len(node.entries) // 2

        new_node = RTreeNode(is_leaf=True, max_entries=self._max_entries)
        new_node.entries = node.entries[mid:]
        node.entries = node.entries[:mid]

        # Recompute MBRs
        node.mbr = Rectangle(float('inf'), float('inf'), float('-inf'), float('-inf'))
        for rect, _ in node.entries:
            self._expand_mbr(node.mbr, rect)

        new_node.mbr = Rectangle(float('inf'), float('inf'), float('-inf'), float('-inf'))
        for rect, _ in new_node.entries:
            self._expand_mbr(new_node.mbr, rect)

        return new_node

    def _split_internal(self, node: RTreeNode) -> RTreeNode:
        """Split internal node."""
        node.children.sort(key=lambda c: c.mbr.x1)
        mid = len(node.children) // 2

        new_node = RTreeNode(is_leaf=False, max_entries=self._max_entries)
        new_node.children = node.children[mid:]
        node.children = node.children[:mid]

        # Recompute MBRs
        node.mbr = Rectangle(float('inf'), float('inf'), float('-inf'), float('-inf'))
        for child in node.children:
            self._expand_mbr(node.mbr, child.mbr)

        new_node.mbr = Rectangle(float('inf'), float('inf'), float('-inf'), float('-inf'))
        for child in new_node.children:
            self._expand_mbr(new_node.mbr, child.mbr)

        return new_node

    def range_query(self, rect: Rectangle) -> List[Any]:
        """Find all data in rectangle."""
        with self._lock:
            result = []
            self._range_query_recursive(self._root, rect, result)
            return result

    def _range_query_recursive(
        self,
        node: RTreeNode,
        rect: Rectangle,
        result: List[Any]
    ) -> None:
        """Recursive range query."""
        if not node.mbr.intersects(rect):
            return

        if node.is_leaf:
            for entry_rect, data in node.entries:
                if entry_rect.intersects(rect):
                    result.append(data)
        else:
            for child in node.children:
                self._range_query_recursive(child, rect, result)


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_kd_tree() -> KDTree:
    """Create KD-tree."""
    return KDTree()


def create_range_tree_2d() -> RangeTree2D:
    """Create 2D range tree."""
    return RangeTree2D()


def create_quadtree(
    x1: float = 0, y1: float = 0,
    x2: float = 1000, y2: float = 1000,
    capacity: int = 4
) -> QuadTree:
    """Create quadtree."""
    return QuadTree(x1, y1, x2, y2, capacity)


def create_r_tree(max_entries: int = 4) -> RTree:
    """Create R-tree."""
    return RTree(max_entries)


def range_query_kd(
    points: List[Tuple[float, float]],
    x1: float, y1: float, x2: float, y2: float
) -> List[int]:
    """Query range using KD-tree."""
    tree = KDTree()
    tree.build(points)
    result = tree.range_query(Rectangle(x1, y1, x2, y2))
    return [p.index for p in result]


def nearest_neighbor_kd(
    points: List[Tuple[float, float]],
    qx: float, qy: float
) -> int:
    """Find nearest neighbor using KD-tree."""
    tree = KDTree()
    tree.build(points)
    result = tree.nearest_neighbor(qx, qy)
    return result.index if result else -1


def k_nearest_kd(
    points: List[Tuple[float, float]],
    qx: float, qy: float, k: int
) -> List[int]:
    """Find k nearest neighbors using KD-tree."""
    tree = KDTree()
    tree.build(points)
    result = tree.k_nearest(qx, qy, k)
    return [p.index for p in result]
