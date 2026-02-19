"""
BAEL Closest Pair Engine
========================

Closest pair algorithms for 2D/3D points.

"Ba'el finds the nearest neighbors." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
import math
import random

logger = logging.getLogger("BAEL.ClosestPair")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Point2D:
    """2D point."""
    x: float
    y: float
    index: int = -1

    def distance_to(self, other: 'Point2D') -> float:
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)


@dataclass
class Point3D:
    """3D point."""
    x: float
    y: float
    z: float
    index: int = -1

    def distance_to(self, other: 'Point3D') -> float:
        return math.sqrt(
            (self.x - other.x) ** 2 +
            (self.y - other.y) ** 2 +
            (self.z - other.z) ** 2
        )


@dataclass
class ClosestPairResult:
    """Closest pair result."""
    point1: Optional[Point2D] = None
    point2: Optional[Point2D] = None
    distance: float = float('inf')
    index1: int = -1
    index2: int = -1


@dataclass
class ClosestPairStats:
    """Statistics for closest pair finding."""
    point_count: int = 0
    comparisons: int = 0
    algorithm: str = ""


# ============================================================================
# BRUTE FORCE O(n²)
# ============================================================================

class BruteForceClosestPair:
    """
    Brute force closest pair finder.

    Features:
    - O(n²) time complexity
    - Simple and correct
    - Good for small datasets

    "Ba'el checks all pairs." — Ba'el
    """

    def __init__(self):
        """Initialize brute force finder."""
        self._points: List[Point2D] = []
        self._stats = ClosestPairStats()
        self._lock = threading.RLock()

        logger.debug("Brute force closest pair initialized")

    def add_point(self, x: float, y: float) -> int:
        """Add point and return its index."""
        with self._lock:
            idx = len(self._points)
            self._points.append(Point2D(x, y, idx))
            return idx

    def add_points(self, points: List[Tuple[float, float]]) -> List[int]:
        """Add multiple points."""
        with self._lock:
            indices = []
            for x, y in points:
                idx = len(self._points)
                self._points.append(Point2D(x, y, idx))
                indices.append(idx)
            return indices

    def find_closest_pair(self) -> ClosestPairResult:
        """
        Find closest pair using brute force.

        Returns:
            ClosestPairResult
        """
        with self._lock:
            n = len(self._points)

            if n < 2:
                return ClosestPairResult()

            min_dist = float('inf')
            closest = (0, 1)
            comparisons = 0

            for i in range(n):
                for j in range(i + 1, n):
                    comparisons += 1
                    dist = self._points[i].distance_to(self._points[j])
                    if dist < min_dist:
                        min_dist = dist
                        closest = (i, j)

            self._stats.point_count = n
            self._stats.comparisons = comparisons
            self._stats.algorithm = "brute_force"

            return ClosestPairResult(
                point1=self._points[closest[0]],
                point2=self._points[closest[1]],
                distance=min_dist,
                index1=closest[0],
                index2=closest[1]
            )


# ============================================================================
# DIVIDE AND CONQUER O(n log n)
# ============================================================================

class DivideConquerClosestPair:
    """
    Divide and conquer closest pair.

    Features:
    - O(n log n) time complexity
    - Optimal for large datasets
    - Recursive with merge step

    "Ba'el divides to conquer." — Ba'el
    """

    def __init__(self):
        """Initialize divide and conquer finder."""
        self._points: List[Point2D] = []
        self._stats = ClosestPairStats()
        self._lock = threading.RLock()

    def add_point(self, x: float, y: float) -> int:
        """Add point and return its index."""
        with self._lock:
            idx = len(self._points)
            self._points.append(Point2D(x, y, idx))
            return idx

    def add_points(self, points: List[Tuple[float, float]]) -> List[int]:
        """Add multiple points."""
        with self._lock:
            indices = []
            for x, y in points:
                idx = len(self._points)
                self._points.append(Point2D(x, y, idx))
                indices.append(idx)
            return indices

    def find_closest_pair(self) -> ClosestPairResult:
        """
        Find closest pair using divide and conquer.

        Returns:
            ClosestPairResult
        """
        with self._lock:
            n = len(self._points)

            if n < 2:
                return ClosestPairResult()

            # Sort points by x and y
            points_x = sorted(self._points, key=lambda p: (p.x, p.y))
            points_y = sorted(self._points, key=lambda p: (p.y, p.x))

            self._stats.comparisons = 0
            result = self._closest_pair_recursive(points_x, points_y)

            self._stats.point_count = n
            self._stats.algorithm = "divide_conquer"

            return result

    def _closest_pair_recursive(
        self,
        points_x: List[Point2D],
        points_y: List[Point2D]
    ) -> ClosestPairResult:
        """Recursive helper."""
        n = len(points_x)

        # Base case: use brute force for small sets
        if n <= 3:
            return self._brute_force(points_x)

        # Divide
        mid = n // 2
        mid_point = points_x[mid]

        left_x = points_x[:mid]
        right_x = points_x[mid:]

        # Partition points_y
        left_set = {p.index for p in left_x}
        left_y = [p for p in points_y if p.index in left_set]
        right_y = [p for p in points_y if p.index not in left_set]

        # Conquer
        left_result = self._closest_pair_recursive(left_x, left_y)
        right_result = self._closest_pair_recursive(right_x, right_y)

        # Take minimum
        if left_result.distance <= right_result.distance:
            best = left_result
        else:
            best = right_result

        delta = best.distance

        # Build strip
        strip = [p for p in points_y if abs(p.x - mid_point.x) < delta]

        # Check strip
        strip_result = self._closest_in_strip(strip, delta)

        if strip_result.distance < best.distance:
            return strip_result

        return best

    def _brute_force(self, points: List[Point2D]) -> ClosestPairResult:
        """Brute force for small sets."""
        n = len(points)
        min_dist = float('inf')
        closest = (None, None)

        for i in range(n):
            for j in range(i + 1, n):
                self._stats.comparisons += 1
                dist = points[i].distance_to(points[j])
                if dist < min_dist:
                    min_dist = dist
                    closest = (points[i], points[j])

        if closest[0] is None:
            return ClosestPairResult()

        return ClosestPairResult(
            point1=closest[0],
            point2=closest[1],
            distance=min_dist,
            index1=closest[0].index,
            index2=closest[1].index
        )

    def _closest_in_strip(self, strip: List[Point2D], delta: float) -> ClosestPairResult:
        """Find closest pair in strip."""
        min_dist = delta
        closest = (None, None)

        for i in range(len(strip)):
            j = i + 1
            while j < len(strip) and strip[j].y - strip[i].y < min_dist:
                self._stats.comparisons += 1
                dist = strip[i].distance_to(strip[j])
                if dist < min_dist:
                    min_dist = dist
                    closest = (strip[i], strip[j])
                j += 1

        if closest[0] is None:
            return ClosestPairResult(distance=float('inf'))

        return ClosestPairResult(
            point1=closest[0],
            point2=closest[1],
            distance=min_dist,
            index1=closest[0].index,
            index2=closest[1].index
        )


# ============================================================================
# RANDOMIZED O(n) EXPECTED
# ============================================================================

class RandomizedClosestPair:
    """
    Randomized closest pair using grid hashing.

    Features:
    - O(n) expected time
    - Grid-based spatial hashing

    "Ba'el uses randomness wisely." — Ba'el
    """

    def __init__(self):
        """Initialize randomized finder."""
        self._points: List[Point2D] = []
        self._stats = ClosestPairStats()
        self._lock = threading.RLock()

    def add_point(self, x: float, y: float) -> int:
        """Add point."""
        with self._lock:
            idx = len(self._points)
            self._points.append(Point2D(x, y, idx))
            return idx

    def find_closest_pair(self) -> ClosestPairResult:
        """
        Find closest pair using randomized algorithm.

        Returns:
            ClosestPairResult
        """
        with self._lock:
            n = len(self._points)

            if n < 2:
                return ClosestPairResult()

            # Shuffle points
            points = self._points.copy()
            random.shuffle(points)

            # Initialize with first two points
            delta = points[0].distance_to(points[1])
            closest = (points[0], points[1])

            # Grid cell size
            grid: Dict[Tuple[int, int], List[Point2D]] = {}

            def get_cell(p: Point2D, d: float) -> Tuple[int, int]:
                return (int(p.x / d), int(p.y / d))

            def get_neighbors(cell: Tuple[int, int]) -> List[Tuple[int, int]]:
                cx, cy = cell
                return [(cx + dx, cy + dy)
                        for dx in range(-1, 2) for dy in range(-1, 2)]

            # Add first two points to grid
            grid[get_cell(points[0], delta)] = [points[0]]
            cell1 = get_cell(points[1], delta)
            if cell1 in grid:
                grid[cell1].append(points[1])
            else:
                grid[cell1] = [points[1]]

            comparisons = 1

            for i in range(2, n):
                p = points[i]
                cell = get_cell(p, delta)

                # Check neighbors
                for neighbor_cell in get_neighbors(cell):
                    if neighbor_cell in grid:
                        for q in grid[neighbor_cell]:
                            comparisons += 1
                            dist = p.distance_to(q)
                            if dist < delta:
                                delta = dist
                                closest = (p, q)

                                # Rebuild grid with new delta
                                grid = {}
                                for j in range(i + 1):
                                    new_cell = get_cell(points[j], delta)
                                    if new_cell in grid:
                                        grid[new_cell].append(points[j])
                                    else:
                                        grid[new_cell] = [points[j]]

                # Add point to grid
                cell = get_cell(p, delta)
                if cell in grid:
                    grid[cell].append(p)
                else:
                    grid[cell] = [p]

            self._stats.point_count = n
            self._stats.comparisons = comparisons
            self._stats.algorithm = "randomized"

            return ClosestPairResult(
                point1=closest[0],
                point2=closest[1],
                distance=delta,
                index1=closest[0].index,
                index2=closest[1].index
            )


# ============================================================================
# 3D CLOSEST PAIR
# ============================================================================

class ClosestPair3D:
    """
    Closest pair in 3D.

    Features:
    - Divide and conquer approach
    - O(n log n) time

    "Ba'el finds pairs in 3D space." — Ba'el
    """

    def __init__(self):
        """Initialize 3D closest pair finder."""
        self._points: List[Point3D] = []
        self._stats = ClosestPairStats()
        self._lock = threading.RLock()

    def add_point(self, x: float, y: float, z: float) -> int:
        """Add 3D point."""
        with self._lock:
            idx = len(self._points)
            self._points.append(Point3D(x, y, z, idx))
            return idx

    def find_closest_pair(self) -> Tuple[Optional[Point3D], Optional[Point3D], float]:
        """
        Find closest pair in 3D.

        Returns:
            (point1, point2, distance)
        """
        with self._lock:
            n = len(self._points)

            if n < 2:
                return None, None, float('inf')

            # Sort by x
            points = sorted(self._points, key=lambda p: p.x)

            result = self._closest_3d_recursive(points)

            self._stats.point_count = n
            self._stats.algorithm = "divide_conquer_3d"

            return result

    def _closest_3d_recursive(
        self,
        points: List[Point3D]
    ) -> Tuple[Point3D, Point3D, float]:
        """Recursive helper for 3D."""
        n = len(points)

        if n <= 3:
            return self._brute_force_3d(points)

        mid = n // 2
        mid_x = points[mid].x

        left = points[:mid]
        right = points[mid:]

        left_result = self._closest_3d_recursive(left)
        right_result = self._closest_3d_recursive(right)

        if left_result[2] <= right_result[2]:
            best = left_result
        else:
            best = right_result

        delta = best[2]

        # Build strip
        strip = [p for p in points if abs(p.x - mid_x) < delta]
        strip.sort(key=lambda p: p.y)

        # Check strip with expanded range for 3D
        for i in range(len(strip)):
            for j in range(i + 1, len(strip)):
                if strip[j].y - strip[i].y >= delta:
                    break

                dist = strip[i].distance_to(strip[j])
                if dist < delta:
                    delta = dist
                    best = (strip[i], strip[j], dist)

        return best

    def _brute_force_3d(
        self,
        points: List[Point3D]
    ) -> Tuple[Point3D, Point3D, float]:
        """Brute force for small 3D sets."""
        min_dist = float('inf')
        closest = (points[0], points[1] if len(points) > 1 else points[0])

        for i in range(len(points)):
            for j in range(i + 1, len(points)):
                dist = points[i].distance_to(points[j])
                if dist < min_dist:
                    min_dist = dist
                    closest = (points[i], points[j])

        return closest[0], closest[1], min_dist


# ============================================================================
# ALL K NEAREST NEIGHBORS
# ============================================================================

class KNearestNeighbors:
    """
    Find k-nearest neighbors for all points.

    "Ba'el finds all neighbors." — Ba'el
    """

    def __init__(self):
        """Initialize k-NN finder."""
        self._points: List[Point2D] = []
        self._lock = threading.RLock()

    def add_point(self, x: float, y: float) -> int:
        """Add point."""
        with self._lock:
            idx = len(self._points)
            self._points.append(Point2D(x, y, idx))
            return idx

    def find_k_nearest(self, query_idx: int, k: int) -> List[Tuple[int, float]]:
        """
        Find k nearest neighbors to a query point.

        Returns:
            List of (point_index, distance) sorted by distance
        """
        with self._lock:
            if query_idx >= len(self._points):
                return []

            query = self._points[query_idx]

            # Compute all distances
            distances = []
            for i, p in enumerate(self._points):
                if i != query_idx:
                    dist = query.distance_to(p)
                    distances.append((i, dist))

            # Sort and return top k
            distances.sort(key=lambda x: x[1])
            return distances[:k]

    def find_all_k_nearest(self, k: int) -> Dict[int, List[Tuple[int, float]]]:
        """
        Find k nearest neighbors for all points.

        Returns:
            Dict mapping point index to list of (neighbor_index, distance)
        """
        with self._lock:
            result = {}

            for i in range(len(self._points)):
                result[i] = self.find_k_nearest(i, k)

            return result


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_brute_force_closest_pair() -> BruteForceClosestPair:
    """Create brute force closest pair finder."""
    return BruteForceClosestPair()


def create_divide_conquer_closest_pair() -> DivideConquerClosestPair:
    """Create divide and conquer closest pair finder."""
    return DivideConquerClosestPair()


def create_randomized_closest_pair() -> RandomizedClosestPair:
    """Create randomized closest pair finder."""
    return RandomizedClosestPair()


def create_closest_pair_3d() -> ClosestPair3D:
    """Create 3D closest pair finder."""
    return ClosestPair3D()


def create_k_nearest_neighbors() -> KNearestNeighbors:
    """Create k-NN finder."""
    return KNearestNeighbors()


def closest_pair(
    points: List[Tuple[float, float]],
    algorithm: str = "divide_conquer"
) -> Tuple[int, int, float]:
    """
    Find closest pair of 2D points.

    Args:
        points: List of (x, y) tuples
        algorithm: "brute_force", "divide_conquer", or "randomized"

    Returns:
        (index1, index2, distance)
    """
    if algorithm == "brute_force":
        finder = BruteForceClosestPair()
    elif algorithm == "randomized":
        finder = RandomizedClosestPair()
    else:
        finder = DivideConquerClosestPair()

    finder.add_points(points)
    result = finder.find_closest_pair()

    return result.index1, result.index2, result.distance


def closest_pair_3d(points: List[Tuple[float, float, float]]) -> Tuple[int, int, float]:
    """Find closest pair of 3D points."""
    finder = ClosestPair3D()
    for x, y, z in points:
        finder.add_point(x, y, z)

    p1, p2, dist = finder.find_closest_pair()

    return (p1.index if p1 else -1, p2.index if p2 else -1, dist)


def k_nearest_neighbors(
    points: List[Tuple[float, float]],
    query_idx: int,
    k: int
) -> List[Tuple[int, float]]:
    """Find k nearest neighbors."""
    finder = KNearestNeighbors()
    for x, y in points:
        finder.add_point(x, y)

    return finder.find_k_nearest(query_idx, k)
