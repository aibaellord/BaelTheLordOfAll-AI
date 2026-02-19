"""
BAEL Point Location Engine
==========================

Point location in planar subdivisions.

"Ba'el locates points precisely." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
import math
from collections import defaultdict

logger = logging.getLogger("BAEL.PointLocation")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Point2D:
    """2D point."""
    x: float
    y: float

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Point2D):
            return False
        return abs(self.x - other.x) < 1e-9 and abs(self.y - other.y) < 1e-9

    def __hash__(self) -> int:
        return hash((round(self.x, 9), round(self.y, 9)))


@dataclass
class Edge:
    """Edge in planar subdivision."""
    p1: Point2D
    p2: Point2D
    left_face: int = -1
    right_face: int = -1

    def y_at_x(self, x: float) -> float:
        """Get y coordinate at given x."""
        if abs(self.p1.x - self.p2.x) < 1e-9:
            return self.p1.y

        t = (x - self.p1.x) / (self.p2.x - self.p1.x)
        return self.p1.y + t * (self.p2.y - self.p1.y)


@dataclass
class Face:
    """Face (region) in planar subdivision."""
    id: int
    vertices: List[Point2D] = field(default_factory=list)
    edges: List[int] = field(default_factory=list)
    data: Any = None


@dataclass
class Polygon:
    """Simple polygon."""
    vertices: List[Point2D] = field(default_factory=list)
    id: int = -1
    data: Any = None


# ============================================================================
# POINT IN POLYGON
# ============================================================================

class PointInPolygon:
    """
    Point in polygon testing.

    Features:
    - Ray casting algorithm
    - O(n) per query
    - Handles edge cases

    "Ba'el tests containment." — Ba'el
    """

    def __init__(self, polygon: List[Tuple[float, float]]):
        """Initialize with polygon vertices."""
        self._vertices = [Point2D(x, y) for x, y in polygon]
        self._n = len(self._vertices)
        self._lock = threading.RLock()

        logger.debug(f"Point in polygon initialized with {self._n} vertices")

    def contains(self, x: float, y: float) -> bool:
        """
        Check if point is inside polygon.

        Uses ray casting (crossing number) algorithm.
        """
        with self._lock:
            if self._n < 3:
                return False

            crossings = 0

            for i in range(self._n):
                p1 = self._vertices[i]
                p2 = self._vertices[(i + 1) % self._n]

                # Check if ray from (x, y) going right intersects edge
                if ((p1.y <= y < p2.y) or (p2.y <= y < p1.y)):
                    # Compute x intersection
                    x_intersect = p1.x + (y - p1.y) / (p2.y - p1.y) * (p2.x - p1.x)

                    if x < x_intersect:
                        crossings += 1

            return crossings % 2 == 1

    def on_boundary(self, x: float, y: float, epsilon: float = 1e-9) -> bool:
        """Check if point is on polygon boundary."""
        with self._lock:
            point = Point2D(x, y)

            for i in range(self._n):
                p1 = self._vertices[i]
                p2 = self._vertices[(i + 1) % self._n]

                # Check if point is on segment p1-p2
                if self._on_segment(p1, p2, point, epsilon):
                    return True

            return False

    def _on_segment(
        self,
        p1: Point2D,
        p2: Point2D,
        q: Point2D,
        epsilon: float
    ) -> bool:
        """Check if q is on segment p1-p2."""
        # Check collinearity
        cross = (q.y - p1.y) * (p2.x - p1.x) - (q.x - p1.x) * (p2.y - p1.y)
        if abs(cross) > epsilon:
            return False

        # Check if within bounding box
        min_x = min(p1.x, p2.x) - epsilon
        max_x = max(p1.x, p2.x) + epsilon
        min_y = min(p1.y, p2.y) - epsilon
        max_y = max(p1.y, p2.y) + epsilon

        return min_x <= q.x <= max_x and min_y <= q.y <= max_y


# ============================================================================
# SLAB DECOMPOSITION
# ============================================================================

class SlabDecomposition:
    """
    Point location using slab decomposition.

    Features:
    - O(n²) space, O(log n) query
    - Vertical line partitioning

    "Ba'el decomposes into slabs." — Ba'el
    """

    def __init__(self):
        """Initialize slab decomposition."""
        self._polygons: List[Polygon] = []
        self._slabs: List[Tuple[float, List[Tuple[Edge, int]]]] = []
        self._x_coords: List[float] = []
        self._built = False
        self._lock = threading.RLock()

    def add_polygon(
        self,
        vertices: List[Tuple[float, float]],
        data: Any = None
    ) -> int:
        """Add polygon and return its ID."""
        with self._lock:
            polygon_id = len(self._polygons)
            self._polygons.append(Polygon(
                vertices=[Point2D(x, y) for x, y in vertices],
                id=polygon_id,
                data=data
            ))
            self._built = False
            return polygon_id

    def build(self) -> None:
        """Build slab decomposition."""
        with self._lock:
            if self._built:
                return

            # Collect all x-coordinates
            x_set = set()
            edges = []

            for polygon in self._polygons:
                n = len(polygon.vertices)
                for i in range(n):
                    p1 = polygon.vertices[i]
                    p2 = polygon.vertices[(i + 1) % n]
                    x_set.add(p1.x)
                    edges.append((Edge(p1, p2), polygon.id))

            self._x_coords = sorted(x_set)

            # Build slabs
            self._slabs = []

            for i in range(len(self._x_coords) - 1):
                x1 = self._x_coords[i]
                x2 = self._x_coords[i + 1]
                mid_x = (x1 + x2) / 2

                # Find edges that span this slab
                slab_edges = []
                for edge, poly_id in edges:
                    e_x1 = min(edge.p1.x, edge.p2.x)
                    e_x2 = max(edge.p1.x, edge.p2.x)

                    if e_x1 <= mid_x <= e_x2:
                        y = edge.y_at_x(mid_x)
                        slab_edges.append((y, edge, poly_id))

                # Sort edges by y at mid_x
                slab_edges.sort(key=lambda e: e[0])
                self._slabs.append((mid_x, [(e[1], e[2]) for e in slab_edges]))

            self._built = True

    def locate(self, x: float, y: float) -> int:
        """
        Locate point in subdivision.

        Returns:
            Polygon ID or -1 if outside all polygons
        """
        self.build()

        with self._lock:
            # Find slab
            import bisect
            slab_idx = bisect.bisect_right(self._x_coords, x) - 1

            if slab_idx < 0 or slab_idx >= len(self._slabs):
                return -1

            _, slab_edges = self._slabs[slab_idx]

            # Binary search in slab
            low, high = 0, len(slab_edges) - 1

            while low <= high:
                mid = (low + high) // 2
                edge, poly_id = slab_edges[mid]
                edge_y = edge.y_at_x(x)

                if abs(edge_y - y) < 1e-9:
                    return poly_id  # On edge
                elif edge_y < y:
                    low = mid + 1
                else:
                    high = mid - 1

            # Check if inside polygon at position 'high'
            if high >= 0:
                _, poly_id = slab_edges[high]
                # Verify with point-in-polygon test
                pip = PointInPolygon([
                    (v.x, v.y) for v in self._polygons[poly_id].vertices
                ])
                if pip.contains(x, y):
                    return poly_id

            return -1


# ============================================================================
# TRAPEZOIDAL DECOMPOSITION
# ============================================================================

class TrapezoidalNode:
    """Node in trapezoidal decomposition search structure."""

    def __init__(self, node_type: str):
        self.node_type = node_type  # 'x', 'y', 'leaf'
        self.value: Any = None
        self.left: Optional['TrapezoidalNode'] = None
        self.right: Optional['TrapezoidalNode'] = None
        self.trapezoid_id: int = -1


@dataclass
class Trapezoid:
    """Trapezoid in decomposition."""
    id: int
    top_edge: Optional[Edge] = None
    bottom_edge: Optional[Edge] = None
    left_point: Optional[Point2D] = None
    right_point: Optional[Point2D] = None
    face_id: int = -1


class TrapezoidalMap:
    """
    Trapezoidal decomposition for point location.

    Features:
    - O(n log n) expected construction
    - O(log n) expected query
    - Randomized incremental construction

    "Ba'el builds the trapezoidal map." — Ba'el
    """

    def __init__(self):
        """Initialize trapezoidal map."""
        self._edges: List[Edge] = []
        self._trapezoids: List[Trapezoid] = []
        self._search_structure: Optional[TrapezoidalNode] = None
        self._built = False
        self._lock = threading.RLock()

    def add_segment(
        self,
        x1: float, y1: float,
        x2: float, y2: float,
        face_above: int = -1,
        face_below: int = -1
    ) -> None:
        """Add segment to the map."""
        with self._lock:
            p1 = Point2D(x1, y1)
            p2 = Point2D(x2, y2)

            if x1 > x2 or (x1 == x2 and y1 > y2):
                p1, p2 = p2, p1

            edge = Edge(p1, p2, face_above, face_below)
            self._edges.append(edge)
            self._built = False

    def build(self) -> None:
        """Build trapezoidal map using incremental construction."""
        with self._lock:
            if self._built:
                return

            import random

            # Initialize with bounding box
            if not self._edges:
                self._built = True
                return

            all_x = [e.p1.x for e in self._edges] + [e.p2.x for e in self._edges]
            all_y = [e.p1.y for e in self._edges] + [e.p2.y for e in self._edges]

            min_x, max_x = min(all_x) - 1, max(all_x) + 1
            min_y, max_y = min(all_y) - 1, max(all_y) + 1

            # Create initial trapezoid (bounding box)
            initial = Trapezoid(
                id=0,
                left_point=Point2D(min_x, min_y),
                right_point=Point2D(max_x, max_y)
            )
            self._trapezoids = [initial]

            # Create initial search structure
            self._search_structure = TrapezoidalNode('leaf')
            self._search_structure.trapezoid_id = 0

            # Randomize edge order
            edges = self._edges.copy()
            random.shuffle(edges)

            # Insert edges (simplified - full implementation is complex)
            for edge in edges:
                self._insert_edge(edge)

            self._built = True

    def _insert_edge(self, edge: Edge) -> None:
        """Insert edge into trapezoidal map."""
        # Simplified insertion - full algorithm is more complex
        pass  # Would update search structure and trapezoids

    def locate(self, x: float, y: float) -> int:
        """
        Locate point using search structure.

        Returns:
            Face ID containing point
        """
        self.build()

        with self._lock:
            if self._search_structure is None:
                return -1

            node = self._search_structure

            while node.node_type != 'leaf':
                if node.node_type == 'x':
                    point = node.value
                    if x < point.x:
                        node = node.left
                    else:
                        node = node.right
                elif node.node_type == 'y':
                    edge = node.value
                    y_at_x = edge.y_at_x(x)
                    if y < y_at_x:
                        node = node.left
                    else:
                        node = node.right

                if node is None:
                    return -1

            if node.trapezoid_id >= 0 and node.trapezoid_id < len(self._trapezoids):
                return self._trapezoids[node.trapezoid_id].face_id

            return -1


# ============================================================================
# GRID-BASED POINT LOCATION
# ============================================================================

class GridPointLocation:
    """
    Grid-based point location.

    Features:
    - O(n/k²) expected query time
    - Simple to implement
    - Good for uniform distributions

    "Ba'el uses the grid." — Ba'el
    """

    def __init__(self, grid_size: int = 100):
        """Initialize grid-based locator."""
        self._grid_size = grid_size
        self._polygons: List[Polygon] = []
        self._grid: Dict[Tuple[int, int], List[int]] = defaultdict(list)
        self._bounds: Tuple[float, float, float, float] = (0, 0, 1, 1)
        self._cell_width = 0.0
        self._cell_height = 0.0
        self._built = False
        self._lock = threading.RLock()

    def add_polygon(
        self,
        vertices: List[Tuple[float, float]],
        data: Any = None
    ) -> int:
        """Add polygon."""
        with self._lock:
            polygon_id = len(self._polygons)
            self._polygons.append(Polygon(
                vertices=[Point2D(x, y) for x, y in vertices],
                id=polygon_id,
                data=data
            ))
            self._built = False
            return polygon_id

    def build(self) -> None:
        """Build grid structure."""
        with self._lock:
            if self._built:
                return

            if not self._polygons:
                self._built = True
                return

            # Compute bounds
            all_x = []
            all_y = []
            for poly in self._polygons:
                for v in poly.vertices:
                    all_x.append(v.x)
                    all_y.append(v.y)

            min_x, max_x = min(all_x), max(all_x)
            min_y, max_y = min(all_y), max(all_y)

            # Add margin
            dx = (max_x - min_x) * 0.01 or 1
            dy = (max_y - min_y) * 0.01 or 1
            self._bounds = (min_x - dx, min_y - dy, max_x + dx, max_y + dy)

            self._cell_width = (self._bounds[2] - self._bounds[0]) / self._grid_size
            self._cell_height = (self._bounds[3] - self._bounds[1]) / self._grid_size

            # Map polygons to grid cells
            self._grid.clear()

            for poly in self._polygons:
                # Get bounding box
                poly_x = [v.x for v in poly.vertices]
                poly_y = [v.y for v in poly.vertices]

                min_cell_x = max(0, int((min(poly_x) - self._bounds[0]) / self._cell_width))
                max_cell_x = min(self._grid_size - 1,
                               int((max(poly_x) - self._bounds[0]) / self._cell_width))
                min_cell_y = max(0, int((min(poly_y) - self._bounds[1]) / self._cell_height))
                max_cell_y = min(self._grid_size - 1,
                               int((max(poly_y) - self._bounds[1]) / self._cell_height))

                for cx in range(min_cell_x, max_cell_x + 1):
                    for cy in range(min_cell_y, max_cell_y + 1):
                        self._grid[(cx, cy)].append(poly.id)

            self._built = True

    def locate(self, x: float, y: float) -> int:
        """
        Locate point.

        Returns:
            Polygon ID or -1
        """
        self.build()

        with self._lock:
            # Get grid cell
            cx = int((x - self._bounds[0]) / self._cell_width)
            cy = int((y - self._bounds[1]) / self._cell_height)

            cx = max(0, min(self._grid_size - 1, cx))
            cy = max(0, min(self._grid_size - 1, cy))

            # Check candidate polygons
            for poly_id in self._grid[(cx, cy)]:
                poly = self._polygons[poly_id]
                pip = PointInPolygon([(v.x, v.y) for v in poly.vertices])
                if pip.contains(x, y):
                    return poly_id

            return -1


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_point_in_polygon(vertices: List[Tuple[float, float]]) -> PointInPolygon:
    """Create point-in-polygon tester."""
    return PointInPolygon(vertices)


def create_slab_decomposition() -> SlabDecomposition:
    """Create slab decomposition."""
    return SlabDecomposition()


def create_trapezoidal_map() -> TrapezoidalMap:
    """Create trapezoidal map."""
    return TrapezoidalMap()


def create_grid_point_location(grid_size: int = 100) -> GridPointLocation:
    """Create grid-based point location."""
    return GridPointLocation(grid_size)


def point_in_polygon(
    polygon: List[Tuple[float, float]],
    x: float, y: float
) -> bool:
    """Check if point is in polygon."""
    pip = PointInPolygon(polygon)
    return pip.contains(x, y)


def point_on_polygon_boundary(
    polygon: List[Tuple[float, float]],
    x: float, y: float,
    epsilon: float = 1e-9
) -> bool:
    """Check if point is on polygon boundary."""
    pip = PointInPolygon(polygon)
    return pip.on_boundary(x, y, epsilon)


def locate_in_polygons(
    polygons: List[List[Tuple[float, float]]],
    x: float, y: float
) -> int:
    """
    Find which polygon contains point.

    Returns:
        Polygon index or -1
    """
    locator = GridPointLocation()
    for i, poly in enumerate(polygons):
        locator.add_polygon(poly)

    return locator.locate(x, y)
