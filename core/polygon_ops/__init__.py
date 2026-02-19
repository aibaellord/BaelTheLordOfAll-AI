"""
BAEL Polygon Operations Engine
==============================

Comprehensive polygon algorithms.

"Ba'el manipulates polygons." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
import math
from enum import Enum, auto

logger = logging.getLogger("BAEL.PolygonOps")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Point2D:
    """2D point."""
    x: float
    y: float

    def __sub__(self, other: 'Point2D') -> 'Point2D':
        return Point2D(self.x - other.x, self.y - other.y)

    def __add__(self, other: 'Point2D') -> 'Point2D':
        return Point2D(self.x + other.x, self.y + other.y)

    def __mul__(self, scalar: float) -> 'Point2D':
        return Point2D(self.x * scalar, self.y * scalar)

    def cross(self, other: 'Point2D') -> float:
        """2D cross product (z-component)."""
        return self.x * other.y - self.y * other.x

    def dot(self, other: 'Point2D') -> float:
        """Dot product."""
        return self.x * other.x + self.y * other.y

    def length(self) -> float:
        """Vector length."""
        return math.sqrt(self.x ** 2 + self.y ** 2)

    def normalize(self) -> 'Point2D':
        """Normalize vector."""
        l = self.length()
        if l < 1e-9:
            return Point2D(0, 0)
        return Point2D(self.x / l, self.y / l)


class WindingOrder(Enum):
    """Polygon winding order."""
    CLOCKWISE = auto()
    COUNTER_CLOCKWISE = auto()
    INVALID = auto()


@dataclass
class Polygon:
    """Simple polygon."""
    vertices: List[Point2D] = field(default_factory=list)

    def copy(self) -> 'Polygon':
        return Polygon([Point2D(v.x, v.y) for v in self.vertices])


@dataclass
class PolygonStats:
    """Polygon statistics."""
    vertex_count: int = 0
    area: float = 0.0
    perimeter: float = 0.0
    is_convex: bool = False
    winding_order: WindingOrder = WindingOrder.INVALID


# ============================================================================
# BASIC POLYGON OPERATIONS
# ============================================================================

class PolygonOperations:
    """
    Basic polygon operations.

    Features:
    - Area, perimeter, centroid
    - Convexity testing
    - Winding order detection

    "Ba'el computes polygon properties." — Ba'el
    """

    def __init__(self, polygon: List[Tuple[float, float]]):
        """Initialize with polygon vertices."""
        self._vertices = [Point2D(x, y) for x, y in polygon]
        self._n = len(self._vertices)
        self._lock = threading.RLock()

        logger.debug(f"Polygon operations initialized with {self._n} vertices")

    def signed_area(self) -> float:
        """
        Compute signed area (shoelace formula).

        Positive = counter-clockwise
        Negative = clockwise
        """
        with self._lock:
            area = 0.0
            for i in range(self._n):
                j = (i + 1) % self._n
                area += self._vertices[i].x * self._vertices[j].y
                area -= self._vertices[j].x * self._vertices[i].y
            return area / 2.0

    def area(self) -> float:
        """Compute polygon area."""
        return abs(self.signed_area())

    def perimeter(self) -> float:
        """Compute polygon perimeter."""
        with self._lock:
            perimeter = 0.0
            for i in range(self._n):
                j = (i + 1) % self._n
                dx = self._vertices[j].x - self._vertices[i].x
                dy = self._vertices[j].y - self._vertices[i].y
                perimeter += math.sqrt(dx ** 2 + dy ** 2)
            return perimeter

    def centroid(self) -> Tuple[float, float]:
        """Compute polygon centroid."""
        with self._lock:
            if self._n == 0:
                return 0.0, 0.0

            cx, cy = 0.0, 0.0
            area = self.signed_area()

            if abs(area) < 1e-10:
                # Degenerate polygon, return average
                for v in self._vertices:
                    cx += v.x
                    cy += v.y
                return cx / self._n, cy / self._n

            for i in range(self._n):
                j = (i + 1) % self._n
                cross = (self._vertices[i].x * self._vertices[j].y -
                        self._vertices[j].x * self._vertices[i].y)
                cx += (self._vertices[i].x + self._vertices[j].x) * cross
                cy += (self._vertices[i].y + self._vertices[j].y) * cross

            cx /= (6.0 * area)
            cy /= (6.0 * area)

            return cx, cy

    def winding_order(self) -> WindingOrder:
        """Determine winding order."""
        area = self.signed_area()
        if area > 1e-10:
            return WindingOrder.COUNTER_CLOCKWISE
        elif area < -1e-10:
            return WindingOrder.CLOCKWISE
        else:
            return WindingOrder.INVALID

    def is_convex(self) -> bool:
        """Check if polygon is convex."""
        with self._lock:
            if self._n < 3:
                return False

            sign = None

            for i in range(self._n):
                p1 = self._vertices[i]
                p2 = self._vertices[(i + 1) % self._n]
                p3 = self._vertices[(i + 2) % self._n]

                cross = (p2 - p1).cross(p3 - p2)

                if abs(cross) < 1e-10:
                    continue

                if sign is None:
                    sign = cross > 0
                elif (cross > 0) != sign:
                    return False

            return True

    def is_simple(self) -> bool:
        """Check if polygon is simple (no self-intersections)."""
        with self._lock:
            # Check all pairs of non-adjacent edges
            for i in range(self._n):
                for j in range(i + 2, self._n):
                    if i == 0 and j == self._n - 1:
                        continue  # Adjacent edges

                    if self._segments_intersect(
                        self._vertices[i], self._vertices[(i + 1) % self._n],
                        self._vertices[j], self._vertices[(j + 1) % self._n]
                    ):
                        return False

            return True

    def _segments_intersect(
        self,
        p1: Point2D, p2: Point2D,
        p3: Point2D, p4: Point2D
    ) -> bool:
        """Check if segments p1-p2 and p3-p4 intersect."""
        d1 = (p2 - p1).cross(p3 - p1)
        d2 = (p2 - p1).cross(p4 - p1)
        d3 = (p4 - p3).cross(p1 - p3)
        d4 = (p4 - p3).cross(p2 - p3)

        if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and \
           ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)):
            return True

        return False

    def reverse(self) -> List[Tuple[float, float]]:
        """Reverse polygon winding order."""
        with self._lock:
            return [(v.x, v.y) for v in reversed(self._vertices)]

    def get_stats(self) -> PolygonStats:
        """Get comprehensive polygon statistics."""
        return PolygonStats(
            vertex_count=self._n,
            area=self.area(),
            perimeter=self.perimeter(),
            is_convex=self.is_convex(),
            winding_order=self.winding_order()
        )


# ============================================================================
# POLYGON TRIANGULATION
# ============================================================================

class EarClipping:
    """
    Ear clipping triangulation.

    Features:
    - O(n²) time complexity
    - Works for simple polygons
    - Intuitive algorithm

    "Ba'el clips ears to triangulate." — Ba'el
    """

    def __init__(self, polygon: List[Tuple[float, float]]):
        """Initialize with polygon vertices."""
        self._original = [Point2D(x, y) for x, y in polygon]
        self._lock = threading.RLock()

    def triangulate(self) -> List[Tuple[int, int, int]]:
        """
        Triangulate polygon.

        Returns:
            List of (i, j, k) index tuples for triangles
        """
        with self._lock:
            n = len(self._original)

            if n < 3:
                return []

            # Create index list
            indices = list(range(n))
            triangles = []

            # Ensure counter-clockwise
            area = 0.0
            for i in range(n):
                j = (i + 1) % n
                area += self._original[i].x * self._original[j].y
                area -= self._original[j].x * self._original[i].y

            if area < 0:
                indices.reverse()

            while len(indices) > 3:
                ear_found = False

                for i in range(len(indices)):
                    prev_idx = indices[(i - 1) % len(indices)]
                    curr_idx = indices[i]
                    next_idx = indices[(i + 1) % len(indices)]

                    if self._is_ear(indices, i, prev_idx, curr_idx, next_idx):
                        triangles.append((prev_idx, curr_idx, next_idx))
                        indices.pop(i)
                        ear_found = True
                        break

                if not ear_found:
                    break

            if len(indices) == 3:
                triangles.append(tuple(indices))

            return triangles

    def _is_ear(
        self,
        indices: List[int],
        i: int,
        prev_idx: int,
        curr_idx: int,
        next_idx: int
    ) -> bool:
        """Check if vertex i forms an ear."""
        p1 = self._original[prev_idx]
        p2 = self._original[curr_idx]
        p3 = self._original[next_idx]

        # Check if convex
        if (p2 - p1).cross(p3 - p2) <= 0:
            return False

        # Check if any other vertex is inside this triangle
        for j in range(len(indices)):
            idx = indices[j]
            if idx in (prev_idx, curr_idx, next_idx):
                continue

            if self._point_in_triangle(self._original[idx], p1, p2, p3):
                return False

        return True

    def _point_in_triangle(
        self,
        p: Point2D,
        a: Point2D, b: Point2D, c: Point2D
    ) -> bool:
        """Check if point is inside triangle."""
        v0 = c - a
        v1 = b - a
        v2 = p - a

        dot00 = v0.dot(v0)
        dot01 = v0.dot(v1)
        dot02 = v0.dot(v2)
        dot11 = v1.dot(v1)
        dot12 = v1.dot(v2)

        denom = dot00 * dot11 - dot01 * dot01
        if abs(denom) < 1e-10:
            return False

        inv_denom = 1.0 / denom
        u = (dot11 * dot02 - dot01 * dot12) * inv_denom
        v = (dot00 * dot12 - dot01 * dot02) * inv_denom

        return u > 0 and v > 0 and u + v < 1


# ============================================================================
# POLYGON CLIPPING (SUTHERLAND-HODGMAN)
# ============================================================================

class PolygonClipping:
    """
    Polygon clipping algorithms.

    "Ba'el clips polygons precisely." — Ba'el
    """

    def __init__(self):
        """Initialize polygon clipping."""
        self._lock = threading.RLock()

    def sutherland_hodgman(
        self,
        subject: List[Tuple[float, float]],
        clip: List[Tuple[float, float]]
    ) -> List[Tuple[float, float]]:
        """
        Clip subject polygon against convex clip polygon.

        Uses Sutherland-Hodgman algorithm.

        Returns:
            Clipped polygon vertices
        """
        with self._lock:
            output = [Point2D(x, y) for x, y in subject]
            clip_pts = [Point2D(x, y) for x, y in clip]

            n_clip = len(clip_pts)

            for i in range(n_clip):
                if not output:
                    break

                input_list = output
                output = []

                edge_start = clip_pts[i]
                edge_end = clip_pts[(i + 1) % n_clip]

                for j in range(len(input_list)):
                    current = input_list[j]
                    next_pt = input_list[(j + 1) % len(input_list)]

                    current_inside = self._is_inside(current, edge_start, edge_end)
                    next_inside = self._is_inside(next_pt, edge_start, edge_end)

                    if current_inside:
                        output.append(current)

                        if not next_inside:
                            intersection = self._line_intersection(
                                current, next_pt, edge_start, edge_end
                            )
                            if intersection:
                                output.append(intersection)
                    elif next_inside:
                        intersection = self._line_intersection(
                            current, next_pt, edge_start, edge_end
                        )
                        if intersection:
                            output.append(intersection)

            return [(p.x, p.y) for p in output]

    def _is_inside(self, p: Point2D, edge_start: Point2D, edge_end: Point2D) -> bool:
        """Check if point is inside (left of) edge."""
        return (edge_end - edge_start).cross(p - edge_start) >= 0

    def _line_intersection(
        self,
        p1: Point2D, p2: Point2D,
        p3: Point2D, p4: Point2D
    ) -> Optional[Point2D]:
        """Compute line-line intersection."""
        d1 = p2 - p1
        d2 = p4 - p3

        cross = d1.cross(d2)
        if abs(cross) < 1e-10:
            return None

        d = p3 - p1
        t = d.cross(d2) / cross

        return p1 + d1 * t


# ============================================================================
# POLYGON BOOLEAN OPERATIONS
# ============================================================================

class PolygonBoolean:
    """
    Boolean operations on polygons.

    "Ba'el performs set operations." — Ba'el
    """

    def __init__(self):
        """Initialize boolean operations."""
        self._clipper = PolygonClipping()
        self._lock = threading.RLock()

    def union(
        self,
        poly1: List[Tuple[float, float]],
        poly2: List[Tuple[float, float]]
    ) -> List[List[Tuple[float, float]]]:
        """
        Compute union of two polygons.

        Simplified implementation for convex polygons.
        """
        with self._lock:
            # For convex polygons, union is the convex hull of vertices
            all_points = list(poly1) + list(poly2)
            return [self._convex_hull(all_points)]

    def intersection(
        self,
        poly1: List[Tuple[float, float]],
        poly2: List[Tuple[float, float]]
    ) -> List[Tuple[float, float]]:
        """
        Compute intersection of two polygons.

        Uses Sutherland-Hodgman for convex polygons.
        """
        with self._lock:
            return self._clipper.sutherland_hodgman(poly1, poly2)

    def difference(
        self,
        poly1: List[Tuple[float, float]],
        poly2: List[Tuple[float, float]]
    ) -> List[List[Tuple[float, float]]]:
        """
        Compute difference poly1 - poly2.

        Simplified implementation.
        """
        with self._lock:
            # For complex boolean ops, would need full implementation
            # This is a placeholder
            return [poly1]

    def _convex_hull(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Compute convex hull using Andrew's monotone chain."""
        pts = sorted(points)

        if len(pts) <= 1:
            return pts

        def cross(o: Tuple[float, float], a: Tuple[float, float], b: Tuple[float, float]) -> float:
            return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

        lower = []
        for p in pts:
            while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
                lower.pop()
            lower.append(p)

        upper = []
        for p in reversed(pts):
            while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
                upper.pop()
            upper.append(p)

        return lower[:-1] + upper[:-1]


# ============================================================================
# POLYGON OFFSET/BUFFER
# ============================================================================

class PolygonOffset:
    """
    Polygon offset (buffer) operations.

    "Ba'el expands and shrinks polygons." — Ba'el
    """

    def __init__(self, polygon: List[Tuple[float, float]]):
        """Initialize with polygon."""
        self._vertices = [Point2D(x, y) for x, y in polygon]
        self._n = len(self._vertices)
        self._lock = threading.RLock()

    def offset(self, distance: float) -> List[Tuple[float, float]]:
        """
        Offset polygon by distance.

        Positive = expand (outward)
        Negative = shrink (inward)

        Returns:
            Offset polygon vertices
        """
        with self._lock:
            if self._n < 3:
                return []

            result = []

            for i in range(self._n):
                prev = self._vertices[(i - 1) % self._n]
                curr = self._vertices[i]
                next_v = self._vertices[(i + 1) % self._n]

                # Compute edge normals
                n1 = self._edge_normal(prev, curr)
                n2 = self._edge_normal(curr, next_v)

                # Offset lines
                l1_p = curr + n1 * distance
                l2_p = curr + n2 * distance

                # Bisector approach for corner
                bisector = (n1 + n2).normalize()

                if bisector.length() < 1e-9:
                    bisector = n1

                # Adjust distance for corner angle
                cos_half = n1.dot(bisector)
                if abs(cos_half) > 1e-9:
                    adjusted_dist = distance / cos_half
                else:
                    adjusted_dist = distance

                new_vertex = curr + bisector * adjusted_dist
                result.append((new_vertex.x, new_vertex.y))

            return result

    def _edge_normal(self, p1: Point2D, p2: Point2D) -> Point2D:
        """Compute outward normal of edge."""
        edge = p2 - p1
        # Perpendicular (rotated 90 degrees counter-clockwise)
        normal = Point2D(-edge.y, edge.x)
        return normal.normalize()


# ============================================================================
# MINKOWSKI SUM
# ============================================================================

class MinkowskiSum:
    """
    Minkowski sum of convex polygons.

    "Ba'el computes Minkowski sums." — Ba'el
    """

    def __init__(self):
        """Initialize Minkowski sum."""
        self._lock = threading.RLock()

    def compute(
        self,
        poly1: List[Tuple[float, float]],
        poly2: List[Tuple[float, float]]
    ) -> List[Tuple[float, float]]:
        """
        Compute Minkowski sum of two convex polygons.

        Returns:
            Minkowski sum polygon
        """
        with self._lock:
            if not poly1 or not poly2:
                return []

            # Ensure counter-clockwise
            p1 = self._ensure_ccw(poly1)
            p2 = self._ensure_ccw(poly2)

            # Get edge vectors
            edges1 = self._get_edge_vectors(p1)
            edges2 = self._get_edge_vectors(p2)

            # Merge edge lists by angle
            all_edges = []
            i, j = 0, 0

            while i < len(edges1) or j < len(edges2):
                if i >= len(edges1):
                    all_edges.append(edges2[j])
                    j += 1
                elif j >= len(edges2):
                    all_edges.append(edges1[i])
                    i += 1
                else:
                    angle1 = math.atan2(edges1[i][1], edges1[i][0])
                    angle2 = math.atan2(edges2[j][1], edges2[j][0])

                    if angle1 <= angle2:
                        all_edges.append(edges1[i])
                        i += 1
                    else:
                        all_edges.append(edges2[j])
                        j += 1

            # Build result starting from sum of lowest points
            start = (p1[0][0] + p2[0][0], p1[0][1] + p2[0][1])

            result = [start]
            current = start

            for dx, dy in all_edges:
                current = (current[0] + dx, current[1] + dy)
                result.append(current)

            return result[:-1]  # Remove duplicate of start

    def _ensure_ccw(self, poly: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Ensure polygon is counter-clockwise."""
        area = 0.0
        n = len(poly)
        for i in range(n):
            j = (i + 1) % n
            area += poly[i][0] * poly[j][1] - poly[j][0] * poly[i][1]

        if area < 0:
            return list(reversed(poly))
        return poly

    def _get_edge_vectors(
        self,
        poly: List[Tuple[float, float]]
    ) -> List[Tuple[float, float]]:
        """Get edge vectors sorted by angle."""
        n = len(poly)
        edges = []

        # Find bottom-most point to start
        start_idx = 0
        for i in range(1, n):
            if poly[i][1] < poly[start_idx][1] or \
               (poly[i][1] == poly[start_idx][1] and poly[i][0] < poly[start_idx][0]):
                start_idx = i

        for i in range(n):
            idx = (start_idx + i) % n
            next_idx = (start_idx + i + 1) % n

            dx = poly[next_idx][0] - poly[idx][0]
            dy = poly[next_idx][1] - poly[idx][1]
            edges.append((dx, dy))

        return edges


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_polygon_operations(vertices: List[Tuple[float, float]]) -> PolygonOperations:
    """Create polygon operations helper."""
    return PolygonOperations(vertices)


def create_ear_clipping(vertices: List[Tuple[float, float]]) -> EarClipping:
    """Create ear clipping triangulator."""
    return EarClipping(vertices)


def create_polygon_clipping() -> PolygonClipping:
    """Create polygon clipping helper."""
    return PolygonClipping()


def create_polygon_boolean() -> PolygonBoolean:
    """Create polygon boolean operations."""
    return PolygonBoolean()


def create_polygon_offset(vertices: List[Tuple[float, float]]) -> PolygonOffset:
    """Create polygon offset helper."""
    return PolygonOffset(vertices)


def create_minkowski_sum() -> MinkowskiSum:
    """Create Minkowski sum computer."""
    return MinkowskiSum()


def polygon_area(vertices: List[Tuple[float, float]]) -> float:
    """Compute polygon area."""
    return PolygonOperations(vertices).area()


def polygon_perimeter(vertices: List[Tuple[float, float]]) -> float:
    """Compute polygon perimeter."""
    return PolygonOperations(vertices).perimeter()


def polygon_centroid(vertices: List[Tuple[float, float]]) -> Tuple[float, float]:
    """Compute polygon centroid."""
    return PolygonOperations(vertices).centroid()


def is_convex_polygon(vertices: List[Tuple[float, float]]) -> bool:
    """Check if polygon is convex."""
    return PolygonOperations(vertices).is_convex()


def triangulate_polygon(vertices: List[Tuple[float, float]]) -> List[Tuple[int, int, int]]:
    """Triangulate polygon."""
    return EarClipping(vertices).triangulate()


def clip_polygon(
    subject: List[Tuple[float, float]],
    clip: List[Tuple[float, float]]
) -> List[Tuple[float, float]]:
    """Clip polygon against convex clip polygon."""
    return PolygonClipping().sutherland_hodgman(subject, clip)


def offset_polygon(
    vertices: List[Tuple[float, float]],
    distance: float
) -> List[Tuple[float, float]]:
    """Offset polygon by distance."""
    return PolygonOffset(vertices).offset(distance)


def minkowski_sum(
    poly1: List[Tuple[float, float]],
    poly2: List[Tuple[float, float]]
) -> List[Tuple[float, float]]:
    """Compute Minkowski sum of two convex polygons."""
    return MinkowskiSum().compute(poly1, poly2)
