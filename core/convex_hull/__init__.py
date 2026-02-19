"""
BAEL Convex Hull Engine
=======================

Convex hull algorithms for 2D/3D point sets.

"Ba'el encloses all points optimally." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
import math

logger = logging.getLogger("BAEL.ConvexHull")


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

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Point2D):
            return False
        return abs(self.x - other.x) < 1e-9 and abs(self.y - other.y) < 1e-9

    def __hash__(self) -> int:
        return hash((round(self.x, 9), round(self.y, 9)))


@dataclass
class Point3D:
    """3D point."""
    x: float
    y: float
    z: float


@dataclass
class ConvexHullResult:
    """Convex hull result."""
    vertices: List[Point2D] = field(default_factory=list)
    indices: List[int] = field(default_factory=list)
    area: float = 0.0
    perimeter: float = 0.0


@dataclass
class ConvexHullStats:
    """Convex hull statistics."""
    input_points: int = 0
    hull_vertices: int = 0
    algorithm: str = ""


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def cross_product_2d(o: Point2D, a: Point2D, b: Point2D) -> float:
    """
    Compute cross product of vectors OA and OB.

    Positive = counter-clockwise
    Negative = clockwise
    Zero = collinear
    """
    return (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x)


def distance_2d(a: Point2D, b: Point2D) -> float:
    """Euclidean distance between two 2D points."""
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)


def polygon_area(vertices: List[Point2D]) -> float:
    """Compute area of polygon using shoelace formula."""
    n = len(vertices)
    if n < 3:
        return 0.0

    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += vertices[i].x * vertices[j].y
        area -= vertices[j].x * vertices[i].y

    return abs(area) / 2.0


def polygon_perimeter(vertices: List[Point2D]) -> float:
    """Compute perimeter of polygon."""
    n = len(vertices)
    if n < 2:
        return 0.0

    perimeter = 0.0
    for i in range(n):
        j = (i + 1) % n
        perimeter += distance_2d(vertices[i], vertices[j])

    return perimeter


# ============================================================================
# GRAHAM SCAN
# ============================================================================

class GrahamScan:
    """
    Graham scan algorithm for convex hull.

    Features:
    - O(n log n) time complexity
    - Polar angle sorting
    - Stack-based processing

    "Ba'el scans the horizon." — Ba'el
    """

    def __init__(self):
        """Initialize Graham scan."""
        self._points: List[Point2D] = []
        self._stats = ConvexHullStats()
        self._lock = threading.RLock()

        logger.debug("Graham scan initialized")

    def add_point(self, x: float, y: float) -> None:
        """Add point to the set."""
        with self._lock:
            self._points.append(Point2D(x, y))

    def add_points(self, points: List[Tuple[float, float]]) -> None:
        """Add multiple points."""
        with self._lock:
            for x, y in points:
                self._points.append(Point2D(x, y))

    def compute_hull(self) -> ConvexHullResult:
        """
        Compute convex hull using Graham scan.

        Returns:
            ConvexHullResult with hull vertices
        """
        with self._lock:
            n = len(self._points)

            if n < 3:
                return ConvexHullResult(
                    vertices=self._points.copy(),
                    indices=list(range(n))
                )

            # Find bottom-most point (and leftmost if tie)
            start_idx = 0
            for i in range(1, n):
                if (self._points[i].y < self._points[start_idx].y or
                    (self._points[i].y == self._points[start_idx].y and
                     self._points[i].x < self._points[start_idx].x)):
                    start_idx = i

            # Swap to position 0
            self._points[0], self._points[start_idx] = \
                self._points[start_idx], self._points[0]

            pivot = self._points[0]

            # Sort by polar angle
            def polar_angle(p: Point2D) -> Tuple[float, float]:
                angle = math.atan2(p.y - pivot.y, p.x - pivot.x)
                dist = distance_2d(pivot, p)
                return (angle, dist)

            sorted_indices = sorted(range(1, n), key=lambda i: polar_angle(self._points[i]))
            sorted_points = [self._points[0]] + [self._points[i] for i in sorted_indices]

            # Build hull with stack
            stack = []

            for p in sorted_points:
                while len(stack) > 1 and cross_product_2d(stack[-2], stack[-1], p) <= 0:
                    stack.pop()
                stack.append(p)

            self._stats.input_points = n
            self._stats.hull_vertices = len(stack)
            self._stats.algorithm = "graham_scan"

            return ConvexHullResult(
                vertices=stack,
                area=polygon_area(stack),
                perimeter=polygon_perimeter(stack)
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'input_points': self._stats.input_points,
            'hull_vertices': self._stats.hull_vertices,
            'algorithm': self._stats.algorithm
        }


# ============================================================================
# ANDREW'S MONOTONE CHAIN
# ============================================================================

class MonotoneChain:
    """
    Andrew's monotone chain algorithm.

    Features:
    - O(n log n) time complexity
    - X-coordinate sorting
    - Upper and lower hulls

    "Ba'el chains the extremes." — Ba'el
    """

    def __init__(self):
        """Initialize monotone chain."""
        self._points: List[Point2D] = []
        self._stats = ConvexHullStats()
        self._lock = threading.RLock()

    def add_point(self, x: float, y: float) -> None:
        """Add point to the set."""
        with self._lock:
            self._points.append(Point2D(x, y))

    def compute_hull(self) -> ConvexHullResult:
        """
        Compute convex hull using monotone chain.

        Returns:
            ConvexHullResult
        """
        with self._lock:
            n = len(self._points)

            if n < 3:
                return ConvexHullResult(vertices=self._points.copy())

            # Sort by x, then by y
            sorted_points = sorted(self._points, key=lambda p: (p.x, p.y))

            # Build lower hull
            lower = []
            for p in sorted_points:
                while len(lower) >= 2 and cross_product_2d(lower[-2], lower[-1], p) <= 0:
                    lower.pop()
                lower.append(p)

            # Build upper hull
            upper = []
            for p in reversed(sorted_points):
                while len(upper) >= 2 and cross_product_2d(upper[-2], upper[-1], p) <= 0:
                    upper.pop()
                upper.append(p)

            # Remove last point of each half (duplicates)
            hull = lower[:-1] + upper[:-1]

            self._stats.input_points = n
            self._stats.hull_vertices = len(hull)
            self._stats.algorithm = "monotone_chain"

            return ConvexHullResult(
                vertices=hull,
                area=polygon_area(hull),
                perimeter=polygon_perimeter(hull)
            )


# ============================================================================
# JARVIS MARCH (GIFT WRAPPING)
# ============================================================================

class JarvisMarch:
    """
    Jarvis march (gift wrapping) algorithm.

    Features:
    - O(nh) time where h is hull size
    - Good when h is small
    - Intuitive approach

    "Ba'el wraps the gift of points." — Ba'el
    """

    def __init__(self):
        """Initialize Jarvis march."""
        self._points: List[Point2D] = []
        self._stats = ConvexHullStats()
        self._lock = threading.RLock()

    def add_point(self, x: float, y: float) -> None:
        """Add point to the set."""
        with self._lock:
            self._points.append(Point2D(x, y))

    def compute_hull(self) -> ConvexHullResult:
        """
        Compute convex hull using Jarvis march.

        Returns:
            ConvexHullResult
        """
        with self._lock:
            n = len(self._points)

            if n < 3:
                return ConvexHullResult(vertices=self._points.copy())

            # Find leftmost point
            leftmost = 0
            for i in range(1, n):
                if self._points[i].x < self._points[leftmost].x:
                    leftmost = i

            hull = []
            current = leftmost

            while True:
                hull.append(self._points[current])

                # Find next point that is most counter-clockwise
                next_point = 0

                for i in range(n):
                    if i == current:
                        continue

                    cross = cross_product_2d(
                        self._points[current],
                        self._points[next_point],
                        self._points[i]
                    )

                    if (next_point == current or cross > 0 or
                        (cross == 0 and distance_2d(self._points[current], self._points[i]) >
                         distance_2d(self._points[current], self._points[next_point]))):
                        next_point = i

                current = next_point

                if current == leftmost:
                    break

            self._stats.input_points = n
            self._stats.hull_vertices = len(hull)
            self._stats.algorithm = "jarvis_march"

            return ConvexHullResult(
                vertices=hull,
                area=polygon_area(hull),
                perimeter=polygon_perimeter(hull)
            )


# ============================================================================
# QUICKHULL
# ============================================================================

class Quickhull:
    """
    Quickhull algorithm for convex hull.

    Features:
    - O(n log n) average case
    - O(n²) worst case
    - Divide and conquer

    "Ba'el divides and conquers." — Ba'el
    """

    def __init__(self):
        """Initialize Quickhull."""
        self._points: List[Point2D] = []
        self._stats = ConvexHullStats()
        self._lock = threading.RLock()

    def add_point(self, x: float, y: float) -> None:
        """Add point to the set."""
        with self._lock:
            self._points.append(Point2D(x, y))

    def compute_hull(self) -> ConvexHullResult:
        """
        Compute convex hull using Quickhull.

        Returns:
            ConvexHullResult
        """
        with self._lock:
            n = len(self._points)

            if n < 3:
                return ConvexHullResult(vertices=self._points.copy())

            # Find extreme points
            min_x = max_x = 0
            for i in range(1, n):
                if self._points[i].x < self._points[min_x].x:
                    min_x = i
                if self._points[i].x > self._points[max_x].x:
                    max_x = i

            left = self._points[min_x]
            right = self._points[max_x]

            # Partition points
            above = []
            below = []

            for p in self._points:
                cross = cross_product_2d(left, right, p)
                if cross > 0:
                    above.append(p)
                elif cross < 0:
                    below.append(p)

            # Build hull recursively
            hull = []

            self._quickhull_recursive(left, right, above, hull)
            hull.append(right)
            self._quickhull_recursive(right, left, below, hull)
            hull.append(left)

            # Remove duplicates while preserving order
            seen = set()
            unique_hull = []
            for p in hull:
                if p not in seen:
                    seen.add(p)
                    unique_hull.append(p)

            self._stats.input_points = n
            self._stats.hull_vertices = len(unique_hull)
            self._stats.algorithm = "quickhull"

            return ConvexHullResult(
                vertices=unique_hull,
                area=polygon_area(unique_hull),
                perimeter=polygon_perimeter(unique_hull)
            )

    def _quickhull_recursive(self, a: Point2D, b: Point2D,
                             points: List[Point2D], hull: List[Point2D]) -> None:
        """Recursive helper for quickhull."""
        if not points:
            return

        # Find point farthest from line AB
        max_dist = -1
        farthest = points[0]

        for p in points:
            dist = abs(cross_product_2d(a, b, p))
            if dist > max_dist:
                max_dist = dist
                farthest = p

        # Partition remaining points
        left_of_af = []
        left_of_fb = []

        for p in points:
            if p == farthest:
                continue

            if cross_product_2d(a, farthest, p) > 0:
                left_of_af.append(p)
            elif cross_product_2d(farthest, b, p) > 0:
                left_of_fb.append(p)

        self._quickhull_recursive(a, farthest, left_of_af, hull)
        hull.append(farthest)
        self._quickhull_recursive(farthest, b, left_of_fb, hull)


# ============================================================================
# CONVEX HULL UTILITIES
# ============================================================================

class ConvexHullUtils:
    """
    Utilities for convex hull operations.

    "Ba'el provides hull utilities." — Ba'el
    """

    @staticmethod
    def point_in_hull(point: Point2D, hull: List[Point2D]) -> bool:
        """Check if point is inside convex hull."""
        n = len(hull)
        if n < 3:
            return False

        for i in range(n):
            if cross_product_2d(hull[i], hull[(i + 1) % n], point) < 0:
                return False

        return True

    @staticmethod
    def hull_centroid(hull: List[Point2D]) -> Point2D:
        """Compute centroid of convex hull."""
        n = len(hull)
        if n == 0:
            return Point2D(0, 0)

        cx = sum(p.x for p in hull) / n
        cy = sum(p.y for p in hull) / n

        return Point2D(cx, cy)

    @staticmethod
    def rotating_calipers_diameter(hull: List[Point2D]) -> Tuple[Point2D, Point2D, float]:
        """
        Find diameter (farthest pair) using rotating calipers.

        Returns:
            (point1, point2, distance)
        """
        n = len(hull)
        if n < 2:
            return hull[0], hull[0], 0.0 if hull else (Point2D(0, 0), Point2D(0, 0), 0.0)

        if n == 2:
            return hull[0], hull[1], distance_2d(hull[0], hull[1])

        max_dist = 0.0
        p1, p2 = hull[0], hull[1]

        j = 1
        for i in range(n):
            while True:
                next_j = (j + 1) % n

                # Check if advancing j increases distance to edge i
                edge = Point2D(
                    hull[(i + 1) % n].x - hull[i].x,
                    hull[(i + 1) % n].y - hull[i].y
                )
                to_j = Point2D(hull[j].x - hull[i].x, hull[j].y - hull[i].y)
                to_next = Point2D(hull[next_j].x - hull[i].x, hull[next_j].y - hull[i].y)

                cross_j = abs(edge.x * to_j.y - edge.y * to_j.x)
                cross_next = abs(edge.x * to_next.y - edge.y * to_next.x)

                if cross_next > cross_j:
                    j = next_j
                else:
                    break

            dist = distance_2d(hull[i], hull[j])
            if dist > max_dist:
                max_dist = dist
                p1, p2 = hull[i], hull[j]

        return p1, p2, max_dist

    @staticmethod
    def minimum_bounding_rectangle(hull: List[Point2D]) -> List[Point2D]:
        """
        Find minimum area bounding rectangle using rotating calipers.

        Returns:
            4 corner points of the rectangle
        """
        n = len(hull)
        if n < 3:
            return hull.copy()

        min_area = float('inf')
        best_rect = None

        for i in range(n):
            # Edge vector
            edge = Point2D(
                hull[(i + 1) % n].x - hull[i].x,
                hull[(i + 1) % n].y - hull[i].y
            )
            edge_len = math.sqrt(edge.x ** 2 + edge.y ** 2)

            if edge_len < 1e-9:
                continue

            # Normalize
            ex, ey = edge.x / edge_len, edge.y / edge_len

            # Perpendicular
            px, py = -ey, ex

            # Project all points
            projs_e = [p.x * ex + p.y * ey for p in hull]
            projs_p = [p.x * px + p.y * py for p in hull]

            min_e, max_e = min(projs_e), max(projs_e)
            min_p, max_p = min(projs_p), max(projs_p)

            area = (max_e - min_e) * (max_p - min_p)

            if area < min_area:
                min_area = area

                # Compute rectangle corners
                best_rect = [
                    Point2D(min_e * ex + min_p * px, min_e * ey + min_p * py),
                    Point2D(max_e * ex + min_p * px, max_e * ey + min_p * py),
                    Point2D(max_e * ex + max_p * px, max_e * ey + max_p * py),
                    Point2D(min_e * ex + max_p * px, min_e * ey + max_p * py),
                ]

        return best_rect or hull[:4]


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_graham_scan() -> GrahamScan:
    """Create Graham scan engine."""
    return GrahamScan()


def create_monotone_chain() -> MonotoneChain:
    """Create monotone chain engine."""
    return MonotoneChain()


def create_jarvis_march() -> JarvisMarch:
    """Create Jarvis march engine."""
    return JarvisMarch()


def create_quickhull() -> Quickhull:
    """Create Quickhull engine."""
    return Quickhull()


def convex_hull(
    points: List[Tuple[float, float]],
    algorithm: str = "monotone_chain"
) -> List[Tuple[float, float]]:
    """
    Compute convex hull of 2D points.

    Args:
        points: List of (x, y) points
        algorithm: "graham_scan", "monotone_chain", "jarvis_march", or "quickhull"

    Returns:
        List of hull vertices as (x, y) tuples
    """
    if algorithm == "graham_scan":
        engine = GrahamScan()
    elif algorithm == "jarvis_march":
        engine = JarvisMarch()
    elif algorithm == "quickhull":
        engine = Quickhull()
    else:
        engine = MonotoneChain()

    for x, y in points:
        engine.add_point(x, y)

    result = engine.compute_hull()
    return [(p.x, p.y) for p in result.vertices]


def convex_hull_area(points: List[Tuple[float, float]]) -> float:
    """Compute area of convex hull."""
    hull = convex_hull(points)
    vertices = [Point2D(x, y) for x, y in hull]
    return polygon_area(vertices)


def convex_hull_perimeter(points: List[Tuple[float, float]]) -> float:
    """Compute perimeter of convex hull."""
    hull = convex_hull(points)
    vertices = [Point2D(x, y) for x, y in hull]
    return polygon_perimeter(vertices)


def farthest_pair(points: List[Tuple[float, float]]) -> Tuple[Tuple[float, float], Tuple[float, float], float]:
    """Find farthest pair of points."""
    hull = convex_hull(points)
    vertices = [Point2D(x, y) for x, y in hull]
    p1, p2, dist = ConvexHullUtils.rotating_calipers_diameter(vertices)
    return (p1.x, p1.y), (p2.x, p2.y), dist
