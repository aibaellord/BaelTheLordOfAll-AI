"""
BAEL K-D Tree Engine Implementation
===================================

K-dimensional spatial indexing.

"Ba'el partitions reality across infinite dimensions." — Ba'el
"""

import logging
import threading
import math
from typing import Any, Callable, Dict, Generic, List, Optional, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("BAEL.KDTree")

T = TypeVar('T')


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class KDNode(Generic[T]):
    """Node in K-D tree."""
    point: List[float]
    data: Optional[T] = None
    left: Optional['KDNode[T]'] = None
    right: Optional['KDNode[T]'] = None
    split_dim: int = 0


@dataclass
class NearestResult(Generic[T]):
    """Nearest neighbor result."""
    point: List[float]
    data: Optional[T]
    distance: float


@dataclass
class KDTreeStats:
    """K-D tree statistics."""
    size: int = 0
    dimensions: int = 0
    height: int = 0
    queries: int = 0


# ============================================================================
# K-D TREE ENGINE
# ============================================================================

class KDTreeEngine(Generic[T]):
    """
    K-D Tree for k-dimensional nearest neighbor queries.

    Features:
    - O(n log n) build time
    - O(log n) average query time
    - O(n^(1-1/k) + k) worst case query
    - Range and radius queries

    "Ba'el finds the nearest point in any dimension." — Ba'el
    """

    def __init__(self, k: int = 2):
        """
        Initialize K-D tree.

        Args:
            k: Number of dimensions
        """
        self._k = k
        self._root: Optional[KDNode[T]] = None
        self._stats = KDTreeStats(dimensions=k)
        self._lock = threading.RLock()

        logger.info(f"K-D tree initialized (k={k})")

    def _distance(self, p1: List[float], p2: List[float]) -> float:
        """Euclidean distance between points."""
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(p1, p2)))

    def _distance_squared(self, p1: List[float], p2: List[float]) -> float:
        """Squared Euclidean distance."""
        return sum((a - b) ** 2 for a, b in zip(p1, p2))

    # ========================================================================
    # BUILD
    # ========================================================================

    def build(self, points: List[Tuple[List[float], T]]) -> None:
        """
        Build K-D tree from points.

        Args:
            points: List of (point, data) tuples
        """
        with self._lock:
            if not points:
                self._root = None
                self._stats.size = 0
                return

            self._root = self._build(points, 0)
            self._stats.size = len(points)
            self._stats.height = self._compute_height(self._root)

            logger.debug(f"K-D tree built with {len(points)} points")

    def _build(
        self,
        points: List[Tuple[List[float], T]],
        depth: int
    ) -> Optional[KDNode[T]]:
        """Build tree recursively."""
        if not points:
            return None

        dim = depth % self._k

        # Sort by current dimension
        points.sort(key=lambda x: x[0][dim])

        mid = len(points) // 2

        node = KDNode(
            point=points[mid][0],
            data=points[mid][1],
            split_dim=dim
        )

        node.left = self._build(points[:mid], depth + 1)
        node.right = self._build(points[mid + 1:], depth + 1)

        return node

    def _compute_height(self, node: Optional[KDNode[T]]) -> int:
        """Compute tree height."""
        if not node:
            return 0
        return 1 + max(
            self._compute_height(node.left),
            self._compute_height(node.right)
        )

    # ========================================================================
    # INSERT
    # ========================================================================

    def insert(self, point: List[float], data: Optional[T] = None) -> None:
        """
        Insert point into tree.

        Args:
            point: K-dimensional point
            data: Associated data
        """
        if len(point) != self._k:
            raise ValueError(f"Point must have {self._k} dimensions")

        with self._lock:
            self._root = self._insert(self._root, point, data, 0)
            self._stats.size += 1

    def _insert(
        self,
        node: Optional[KDNode[T]],
        point: List[float],
        data: Optional[T],
        depth: int
    ) -> KDNode[T]:
        """Insert recursively."""
        if not node:
            return KDNode(point=point, data=data, split_dim=depth % self._k)

        dim = depth % self._k

        if point[dim] < node.point[dim]:
            node.left = self._insert(node.left, point, data, depth + 1)
        else:
            node.right = self._insert(node.right, point, data, depth + 1)

        return node

    # ========================================================================
    # NEAREST NEIGHBOR
    # ========================================================================

    def nearest(self, query: List[float]) -> Optional[NearestResult[T]]:
        """
        Find nearest neighbor.

        Args:
            query: Query point

        Returns:
            NearestResult or None
        """
        with self._lock:
            self._stats.queries += 1

            if not self._root:
                return None

            best = [None, float('inf')]  # [node, distance_squared]
            self._nearest(self._root, query, 0, best)

            if best[0]:
                return NearestResult(
                    point=best[0].point,
                    data=best[0].data,
                    distance=math.sqrt(best[1])
                )

            return None

    def _nearest(
        self,
        node: Optional[KDNode[T]],
        query: List[float],
        depth: int,
        best: List
    ) -> None:
        """Find nearest recursively."""
        if not node:
            return

        # Calculate distance to current node
        dist_sq = self._distance_squared(query, node.point)

        if dist_sq < best[1]:
            best[0] = node
            best[1] = dist_sq

        dim = depth % self._k
        diff = query[dim] - node.point[dim]

        # Search closer subtree first
        if diff < 0:
            first, second = node.left, node.right
        else:
            first, second = node.right, node.left

        self._nearest(first, query, depth + 1, best)

        # Check if we need to search other subtree
        if diff ** 2 < best[1]:
            self._nearest(second, query, depth + 1, best)

    def k_nearest(self, query: List[float], k: int) -> List[NearestResult[T]]:
        """
        Find k nearest neighbors.

        Args:
            query: Query point
            k: Number of neighbors

        Returns:
            List of NearestResult sorted by distance
        """
        import heapq

        with self._lock:
            self._stats.queries += 1

            if not self._root or k <= 0:
                return []

            # Max-heap of (-distance, node)
            heap = []
            self._k_nearest(self._root, query, k, 0, heap)

            # Convert to results
            results = []
            while heap:
                neg_dist_sq, node = heapq.heappop(heap)
                results.append(NearestResult(
                    point=node.point,
                    data=node.data,
                    distance=math.sqrt(-neg_dist_sq)
                ))

            results.reverse()
            return results

    def _k_nearest(
        self,
        node: Optional[KDNode[T]],
        query: List[float],
        k: int,
        depth: int,
        heap: List
    ) -> None:
        """Find k nearest recursively."""
        import heapq

        if not node:
            return

        dist_sq = self._distance_squared(query, node.point)

        if len(heap) < k:
            heapq.heappush(heap, (-dist_sq, node))
        elif -dist_sq > heap[0][0]:
            heapq.heapreplace(heap, (-dist_sq, node))

        dim = depth % self._k
        diff = query[dim] - node.point[dim]

        if diff < 0:
            first, second = node.left, node.right
        else:
            first, second = node.right, node.left

        self._k_nearest(first, query, k, depth + 1, heap)

        if len(heap) < k or diff ** 2 < -heap[0][0]:
            self._k_nearest(second, query, k, depth + 1, heap)

    # ========================================================================
    # RANGE QUERIES
    # ========================================================================

    def range_search(
        self,
        mins: List[float],
        maxs: List[float]
    ) -> List[Tuple[List[float], T]]:
        """
        Find all points in axis-aligned bounding box.

        Args:
            mins: Minimum values for each dimension
            maxs: Maximum values for each dimension

        Returns:
            List of (point, data) tuples
        """
        with self._lock:
            self._stats.queries += 1

            results = []
            self._range_search(self._root, mins, maxs, 0, results)
            return results

    def _range_search(
        self,
        node: Optional[KDNode[T]],
        mins: List[float],
        maxs: List[float],
        depth: int,
        results: List
    ) -> None:
        """Range search recursively."""
        if not node:
            return

        # Check if point is in range
        in_range = all(
            mins[i] <= node.point[i] <= maxs[i]
            for i in range(self._k)
        )

        if in_range:
            results.append((node.point, node.data))

        dim = depth % self._k

        # Check if we need to search subtrees
        if mins[dim] <= node.point[dim]:
            self._range_search(node.left, mins, maxs, depth + 1, results)

        if maxs[dim] >= node.point[dim]:
            self._range_search(node.right, mins, maxs, depth + 1, results)

    def radius_search(
        self,
        center: List[float],
        radius: float
    ) -> List[Tuple[List[float], T]]:
        """
        Find all points within radius of center.

        Args:
            center: Center point
            radius: Search radius

        Returns:
            List of (point, data) tuples
        """
        with self._lock:
            self._stats.queries += 1

            results = []
            radius_sq = radius ** 2
            self._radius_search(self._root, center, radius_sq, 0, results)
            return results

    def _radius_search(
        self,
        node: Optional[KDNode[T]],
        center: List[float],
        radius_sq: float,
        depth: int,
        results: List
    ) -> None:
        """Radius search recursively."""
        if not node:
            return

        dist_sq = self._distance_squared(center, node.point)

        if dist_sq <= radius_sq:
            results.append((node.point, node.data))

        dim = depth % self._k
        diff = center[dim] - node.point[dim]

        if diff < 0:
            first, second = node.left, node.right
        else:
            first, second = node.right, node.left

        self._radius_search(first, center, radius_sq, depth + 1, results)

        if diff ** 2 <= radius_sq:
            self._radius_search(second, center, radius_sq, depth + 1, results)

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def __len__(self) -> int:
        return self._stats.size

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'size': self._stats.size,
            'dimensions': self._stats.dimensions,
            'height': self._stats.height,
            'queries': self._stats.queries
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_kd_tree(k: int = 2) -> KDTreeEngine:
    """Create empty K-D tree."""
    return KDTreeEngine(k)


def create_2d_tree() -> KDTreeEngine:
    """Create 2D K-D tree."""
    return KDTreeEngine(2)


def create_3d_tree() -> KDTreeEngine:
    """Create 3D K-D tree."""
    return KDTreeEngine(3)


def build_kd_tree(
    points: List[List[float]],
    k: Optional[int] = None
) -> KDTreeEngine:
    """
    Build K-D tree from points.

    Args:
        points: List of k-dimensional points
        k: Dimensions (inferred if None)

    Returns:
        KDTreeEngine
    """
    if not points:
        return KDTreeEngine(k or 2)

    k = k or len(points[0])
    tree = KDTreeEngine(k)
    tree.build([(p, None) for p in points])
    return tree


def nearest_neighbor(
    points: List[List[float]],
    query: List[float]
) -> Optional[List[float]]:
    """
    Quick nearest neighbor query.

    Args:
        points: List of points
        query: Query point

    Returns:
        Nearest point or None
    """
    tree = build_kd_tree(points)
    result = tree.nearest(query)
    return result.point if result else None
