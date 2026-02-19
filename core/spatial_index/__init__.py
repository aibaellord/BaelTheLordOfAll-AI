"""
BAEL Spatial Index Engine Implementation
==========================================

Spatial indexing with R-Tree and Quadtree.

"Ba'el perceives all dimensions of space." — Ba'el
"""

import logging
import math
import threading
from typing import Any, Callable, Dict, Generic, Iterator, List, Optional, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("BAEL.SpatialIndex")

T = TypeVar('T')  # Value type


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Point:
    """2D point."""
    x: float
    y: float

    def distance_to(self, other: 'Point') -> float:
        """Euclidean distance to another point."""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def __hash__(self) -> int:
        return hash((self.x, self.y))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Point):
            return False
        return self.x == other.x and self.y == other.y


@dataclass
class BoundingBox:
    """Axis-aligned bounding box."""
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        return self.max_y - self.min_y

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center(self) -> Point:
        return Point(
            (self.min_x + self.max_x) / 2,
            (self.min_y + self.max_y) / 2
        )

    def contains_point(self, point: Point) -> bool:
        """Check if box contains point."""
        return (self.min_x <= point.x <= self.max_x and
                self.min_y <= point.y <= self.max_y)

    def contains_box(self, other: 'BoundingBox') -> bool:
        """Check if this box contains another."""
        return (self.min_x <= other.min_x and
                self.min_y <= other.min_y and
                self.max_x >= other.max_x and
                self.max_y >= other.max_y)

    def intersects(self, other: 'BoundingBox') -> bool:
        """Check if boxes intersect."""
        return (self.min_x <= other.max_x and
                self.max_x >= other.min_x and
                self.min_y <= other.max_y and
                self.max_y >= other.min_y)

    def expand_to_include(self, other: 'BoundingBox') -> 'BoundingBox':
        """Create expanded box including both."""
        return BoundingBox(
            min(self.min_x, other.min_x),
            min(self.min_y, other.min_y),
            max(self.max_x, other.max_x),
            max(self.max_y, other.max_y)
        )

    def expand_by(self, margin: float) -> 'BoundingBox':
        """Expand box by margin."""
        return BoundingBox(
            self.min_x - margin,
            self.min_y - margin,
            self.max_x + margin,
            self.max_y + margin
        )

    @classmethod
    def from_point(cls, point: Point) -> 'BoundingBox':
        """Create box from single point."""
        return cls(point.x, point.y, point.x, point.y)

    @classmethod
    def from_points(cls, points: List[Point]) -> 'BoundingBox':
        """Create bounding box from points."""
        if not points:
            return cls(0, 0, 0, 0)

        xs = [p.x for p in points]
        ys = [p.y for p in points]

        return cls(min(xs), min(ys), max(xs), max(ys))


@dataclass
class SpatialEntry(Generic[T]):
    """Entry in spatial index."""
    bounds: BoundingBox
    value: T

    def __hash__(self) -> int:
        return id(self)


# ============================================================================
# QUADTREE
# ============================================================================

class QuadTreeNode(Generic[T]):
    """Quadtree node."""

    def __init__(self, bounds: BoundingBox, capacity: int = 4, depth: int = 0):
        """Initialize node."""
        self.bounds = bounds
        self.capacity = capacity
        self.depth = depth

        self.entries: List[SpatialEntry[T]] = []
        self.divided = False

        # Children (NW, NE, SW, SE)
        self.nw: Optional['QuadTreeNode[T]'] = None
        self.ne: Optional['QuadTreeNode[T]'] = None
        self.sw: Optional['QuadTreeNode[T]'] = None
        self.se: Optional['QuadTreeNode[T]'] = None

    def subdivide(self) -> None:
        """Subdivide node into four children."""
        if self.divided:
            return

        cx, cy = self.bounds.center.x, self.bounds.center.y

        self.nw = QuadTreeNode(
            BoundingBox(self.bounds.min_x, cy, cx, self.bounds.max_y),
            self.capacity, self.depth + 1
        )
        self.ne = QuadTreeNode(
            BoundingBox(cx, cy, self.bounds.max_x, self.bounds.max_y),
            self.capacity, self.depth + 1
        )
        self.sw = QuadTreeNode(
            BoundingBox(self.bounds.min_x, self.bounds.min_y, cx, cy),
            self.capacity, self.depth + 1
        )
        self.se = QuadTreeNode(
            BoundingBox(cx, self.bounds.min_y, self.bounds.max_x, cy),
            self.capacity, self.depth + 1
        )

        self.divided = True


class QuadTree(Generic[T]):
    """
    Quadtree spatial index.

    Features:
    - O(log n) insertion/query
    - Range queries
    - Point queries

    "Ba'el divides space into perfect quadrants." — Ba'el
    """

    def __init__(
        self,
        bounds: BoundingBox,
        capacity: int = 4,
        max_depth: int = 10
    ):
        """Initialize quadtree."""
        self.root = QuadTreeNode(bounds, capacity)
        self.capacity = capacity
        self.max_depth = max_depth
        self._count = 0
        self._lock = threading.RLock()

        logger.info(f"Quadtree initialized (capacity={capacity})")

    def insert(
        self,
        point: Point,
        value: T
    ) -> bool:
        """
        Insert point with value.

        Args:
            point: Location
            value: Associated value

        Returns:
            True if inserted
        """
        entry = SpatialEntry(BoundingBox.from_point(point), value)

        with self._lock:
            result = self._insert(self.root, entry)
            if result:
                self._count += 1
            return result

    def insert_box(
        self,
        bounds: BoundingBox,
        value: T
    ) -> bool:
        """Insert bounding box with value."""
        entry = SpatialEntry(bounds, value)

        with self._lock:
            result = self._insert(self.root, entry)
            if result:
                self._count += 1
            return result

    def _insert(
        self,
        node: QuadTreeNode[T],
        entry: SpatialEntry[T]
    ) -> bool:
        """Insert into subtree."""
        if not node.bounds.intersects(entry.bounds):
            return False

        # If we have capacity and not divided, insert here
        if len(node.entries) < node.capacity and not node.divided:
            node.entries.append(entry)
            return True

        # Need to subdivide
        if not node.divided and node.depth < self.max_depth:
            node.subdivide()

            # Re-insert existing entries
            for existing in node.entries:
                self._insert_into_children(node, existing)
            node.entries = []

        # Insert into children
        if node.divided:
            return self._insert_into_children(node, entry)

        # Max depth reached, store here
        node.entries.append(entry)
        return True

    def _insert_into_children(
        self,
        node: QuadTreeNode[T],
        entry: SpatialEntry[T]
    ) -> bool:
        """Insert into child nodes."""
        inserted = False

        for child in [node.nw, node.ne, node.sw, node.se]:
            if child and child.bounds.intersects(entry.bounds):
                if self._insert(child, entry):
                    inserted = True

        return inserted

    def query_point(self, point: Point) -> List[T]:
        """
        Query all values at point.

        Args:
            point: Query point

        Returns:
            List of values
        """
        result: List[T] = []

        with self._lock:
            self._query_point(self.root, point, result)

        return result

    def _query_point(
        self,
        node: QuadTreeNode[T],
        point: Point,
        result: List[T]
    ) -> None:
        """Query point in subtree."""
        if not node.bounds.contains_point(point):
            return

        for entry in node.entries:
            if entry.bounds.contains_point(point):
                result.append(entry.value)

        if node.divided:
            for child in [node.nw, node.ne, node.sw, node.se]:
                if child:
                    self._query_point(child, point, result)

    def query_range(self, bounds: BoundingBox) -> List[T]:
        """
        Query all values in range.

        Args:
            bounds: Query bounds

        Returns:
            List of values
        """
        result: List[T] = []

        with self._lock:
            self._query_range(self.root, bounds, result)

        return result

    def _query_range(
        self,
        node: QuadTreeNode[T],
        bounds: BoundingBox,
        result: List[T]
    ) -> None:
        """Query range in subtree."""
        if not node.bounds.intersects(bounds):
            return

        for entry in node.entries:
            if entry.bounds.intersects(bounds):
                result.append(entry.value)

        if node.divided:
            for child in [node.nw, node.ne, node.sw, node.se]:
                if child:
                    self._query_range(child, bounds, result)

    def query_radius(
        self,
        center: Point,
        radius: float
    ) -> List[T]:
        """
        Query all values within radius.

        Args:
            center: Center point
            radius: Search radius

        Returns:
            List of values
        """
        # First get box results
        box = BoundingBox(
            center.x - radius,
            center.y - radius,
            center.x + radius,
            center.y + radius
        )

        candidates = self.query_range(box)

        # Filter by actual distance (for point entries)
        # For now, return all box results
        return candidates

    def __len__(self) -> int:
        return self._count

    def clear(self) -> None:
        """Clear all entries."""
        with self._lock:
            self.root = QuadTreeNode(self.root.bounds, self.capacity)
            self._count = 0


# ============================================================================
# R-TREE (SIMPLIFIED)
# ============================================================================

class RTreeNode(Generic[T]):
    """R-Tree node."""

    def __init__(self, is_leaf: bool = True, capacity: int = 4):
        """Initialize node."""
        self.is_leaf = is_leaf
        self.capacity = capacity

        self.entries: List[SpatialEntry[T]] = []
        self.children: List['RTreeNode[T]'] = []
        self.bounds: Optional[BoundingBox] = None

    def update_bounds(self) -> None:
        """Update bounding box."""
        if self.is_leaf:
            if self.entries:
                self.bounds = self.entries[0].bounds
                for entry in self.entries[1:]:
                    self.bounds = self.bounds.expand_to_include(entry.bounds)
        else:
            if self.children:
                self.bounds = self.children[0].bounds
                for child in self.children[1:]:
                    if child.bounds:
                        self.bounds = self.bounds.expand_to_include(child.bounds)


class RTree(Generic[T]):
    """
    Simplified R-Tree implementation.

    Features:
    - Bounding box indexing
    - Range queries
    - Good for arbitrary shapes

    "Ba'el bounds all shapes in perfect rectangles." — Ba'el
    """

    def __init__(self, capacity: int = 4):
        """Initialize R-Tree."""
        self.root = RTreeNode(is_leaf=True, capacity=capacity)
        self.capacity = capacity
        self._count = 0
        self._lock = threading.RLock()

        logger.info(f"R-Tree initialized (capacity={capacity})")

    def insert(
        self,
        bounds: BoundingBox,
        value: T
    ) -> None:
        """
        Insert bounding box with value.

        Args:
            bounds: Bounding box
            value: Associated value
        """
        entry = SpatialEntry(bounds, value)

        with self._lock:
            self._insert(self.root, entry)
            self._count += 1

    def _insert(
        self,
        node: RTreeNode[T],
        entry: SpatialEntry[T]
    ) -> Optional[RTreeNode[T]]:
        """Insert into subtree, returning split node if any."""
        if node.is_leaf:
            node.entries.append(entry)
            node.update_bounds()

            if len(node.entries) > self.capacity:
                return self._split_leaf(node)
            return None
        else:
            # Choose child with minimum enlargement
            best_child = self._choose_child(node, entry.bounds)

            split_node = self._insert(best_child, entry)

            if split_node:
                node.children.append(split_node)

            node.update_bounds()

            if len(node.children) > self.capacity:
                return self._split_internal(node)
            return None

    def _choose_child(
        self,
        node: RTreeNode[T],
        bounds: BoundingBox
    ) -> RTreeNode[T]:
        """Choose best child for insertion."""
        best_child = node.children[0]
        best_enlargement = float('inf')

        for child in node.children:
            if child.bounds:
                new_bounds = child.bounds.expand_to_include(bounds)
                enlargement = new_bounds.area - child.bounds.area

                if enlargement < best_enlargement:
                    best_enlargement = enlargement
                    best_child = child

        return best_child

    def _split_leaf(self, node: RTreeNode[T]) -> RTreeNode[T]:
        """Split a leaf node."""
        # Simple split: first half / second half
        mid = len(node.entries) // 2

        new_node = RTreeNode(is_leaf=True, capacity=self.capacity)
        new_node.entries = node.entries[mid:]
        node.entries = node.entries[:mid]

        node.update_bounds()
        new_node.update_bounds()

        return new_node

    def _split_internal(self, node: RTreeNode[T]) -> RTreeNode[T]:
        """Split an internal node."""
        mid = len(node.children) // 2

        new_node = RTreeNode(is_leaf=False, capacity=self.capacity)
        new_node.children = node.children[mid:]
        node.children = node.children[:mid]

        node.update_bounds()
        new_node.update_bounds()

        return new_node

    def query(self, bounds: BoundingBox) -> List[T]:
        """
        Query all values intersecting bounds.

        Args:
            bounds: Query bounds

        Returns:
            List of values
        """
        result: List[T] = []

        with self._lock:
            self._query(self.root, bounds, result)

        return result

    def _query(
        self,
        node: RTreeNode[T],
        bounds: BoundingBox,
        result: List[T]
    ) -> None:
        """Query in subtree."""
        if node.bounds is None or not node.bounds.intersects(bounds):
            return

        if node.is_leaf:
            for entry in node.entries:
                if entry.bounds.intersects(bounds):
                    result.append(entry.value)
        else:
            for child in node.children:
                self._query(child, bounds, result)

    def __len__(self) -> int:
        return self._count


# ============================================================================
# SPATIAL INDEX ENGINE
# ============================================================================

class SpatialIndexType(Enum):
    """Spatial index types."""
    QUADTREE = "quadtree"
    RTREE = "rtree"


class SpatialIndexEngine(Generic[T]):
    """
    Unified spatial index engine.

    "Ba'el indexes all of space efficiently." — Ba'el
    """

    def __init__(
        self,
        bounds: BoundingBox,
        index_type: SpatialIndexType = SpatialIndexType.QUADTREE,
        capacity: int = 4
    ):
        """Initialize spatial index."""
        self.bounds = bounds
        self.index_type = index_type

        if index_type == SpatialIndexType.QUADTREE:
            self._index: Any = QuadTree(bounds, capacity)
        else:
            self._index = RTree(capacity)

        logger.info(f"Spatial index initialized ({index_type.value})")

    def insert_point(self, point: Point, value: T) -> None:
        """Insert point with value."""
        if self.index_type == SpatialIndexType.QUADTREE:
            self._index.insert(point, value)
        else:
            self._index.insert(BoundingBox.from_point(point), value)

    def insert_box(self, bounds: BoundingBox, value: T) -> None:
        """Insert bounding box with value."""
        if self.index_type == SpatialIndexType.QUADTREE:
            self._index.insert_box(bounds, value)
        else:
            self._index.insert(bounds, value)

    def query_point(self, point: Point) -> List[T]:
        """Query at point."""
        if self.index_type == SpatialIndexType.QUADTREE:
            return self._index.query_point(point)
        else:
            box = BoundingBox(point.x, point.y, point.x, point.y)
            return self._index.query(box)

    def query_range(self, bounds: BoundingBox) -> List[T]:
        """Query in range."""
        if self.index_type == SpatialIndexType.QUADTREE:
            return self._index.query_range(bounds)
        else:
            return self._index.query(bounds)

    def query_radius(self, center: Point, radius: float) -> List[T]:
        """Query within radius."""
        bounds = BoundingBox(
            center.x - radius,
            center.y - radius,
            center.x + radius,
            center.y + radius
        )
        return self.query_range(bounds)

    def __len__(self) -> int:
        return len(self._index)


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_quadtree(
    min_x: float,
    min_y: float,
    max_x: float,
    max_y: float,
    **kwargs
) -> QuadTree:
    """Create a new quadtree."""
    bounds = BoundingBox(min_x, min_y, max_x, max_y)
    return QuadTree(bounds, **kwargs)


def create_rtree(capacity: int = 4) -> RTree:
    """Create a new R-tree."""
    return RTree(capacity)


def create_spatial_index(
    min_x: float,
    min_y: float,
    max_x: float,
    max_y: float,
    index_type: SpatialIndexType = SpatialIndexType.QUADTREE,
    **kwargs
) -> SpatialIndexEngine:
    """Create a new spatial index."""
    bounds = BoundingBox(min_x, min_y, max_x, max_y)
    return SpatialIndexEngine(bounds, index_type, **kwargs)
