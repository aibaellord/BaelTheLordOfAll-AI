"""
BAEL Octree Engine
==================

Spatial partitioning for 3D data.

"Ba'el divides three dimensions." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Tuple, Generic, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto
import math

logger = logging.getLogger("BAEL.Octree")


V = TypeVar('V')


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Point3D:
    """3D point."""
    x: float
    y: float
    z: float

    def distance_to(self, other: 'Point3D') -> float:
        return math.sqrt(
            (self.x - other.x) ** 2 +
            (self.y - other.y) ** 2 +
            (self.z - other.z) ** 2
        )


@dataclass
class BoundingBox:
    """Axis-aligned 3D bounding box."""
    center_x: float
    center_y: float
    center_z: float
    half_size: float  # Half the side length (cube)

    def contains(self, point: Point3D) -> bool:
        return (abs(point.x - self.center_x) <= self.half_size and
                abs(point.y - self.center_y) <= self.half_size and
                abs(point.z - self.center_z) <= self.half_size)

    def intersects(self, other: 'BoundingBox') -> bool:
        return not (
            abs(self.center_x - other.center_x) > self.half_size + other.half_size or
            abs(self.center_y - other.center_y) > self.half_size + other.half_size or
            abs(self.center_z - other.center_z) > self.half_size + other.half_size
        )


@dataclass
class OctreeStats:
    """Octree statistics."""
    num_points: int
    depth: int
    num_nodes: int
    capacity: int


# ============================================================================
# OCTANT ENUMERATION
# ============================================================================

class Octant(Enum):
    """Eight octants of 3D space."""
    TOP_LEFT_FRONT = 0     # -x, +y, +z
    TOP_RIGHT_FRONT = 1    # +x, +y, +z
    TOP_LEFT_BACK = 2      # -x, +y, -z
    TOP_RIGHT_BACK = 3     # +x, +y, -z
    BOTTOM_LEFT_FRONT = 4  # -x, -y, +z
    BOTTOM_RIGHT_FRONT = 5 # +x, -y, +z
    BOTTOM_LEFT_BACK = 6   # -x, -y, -z
    BOTTOM_RIGHT_BACK = 7  # +x, -y, -z


# ============================================================================
# OCTREE
# ============================================================================

class Octree(Generic[V]):
    """
    Octree for 3D spatial indexing.

    Features:
    - O(log n) insertion (average)
    - O(log n + k) range queries
    - O(log n + k) sphere queries

    "Ba'el partitions volume." — Ba'el
    """

    def __init__(
        self,
        boundary: BoundingBox,
        capacity: int = 8,
        max_depth: int = 20
    ):
        """
        Initialize octree.

        Args:
            boundary: Bounding box
            capacity: Points per node before splitting
            max_depth: Maximum tree depth
        """
        self._boundary = boundary
        self._capacity = capacity
        self._max_depth = max_depth
        self._depth = 0

        self._points: List[Tuple[Point3D, V]] = []
        self._divided = False

        # 8 children (octants)
        self._children: List[Optional['Octree[V]']] = [None] * 8

        self._lock = threading.RLock()

    def _get_octant(self, point: Point3D) -> int:
        """Determine which octant a point belongs to."""
        cx, cy, cz = self._boundary.center_x, self._boundary.center_y, self._boundary.center_z

        idx = 0
        if point.x >= cx:
            idx |= 1
        if point.y < cy:
            idx |= 4
        if point.z < cz:
            idx |= 2

        return idx

    def _subdivide(self):
        """Create eight children."""
        cx = self._boundary.center_x
        cy = self._boundary.center_y
        cz = self._boundary.center_z
        hs = self._boundary.half_size / 2  # Half of half size

        offsets = [
            (-hs, +hs, +hs),  # TOP_LEFT_FRONT
            (+hs, +hs, +hs),  # TOP_RIGHT_FRONT
            (-hs, +hs, -hs),  # TOP_LEFT_BACK
            (+hs, +hs, -hs),  # TOP_RIGHT_BACK
            (-hs, -hs, +hs),  # BOTTOM_LEFT_FRONT
            (+hs, -hs, +hs),  # BOTTOM_RIGHT_FRONT
            (-hs, -hs, -hs),  # BOTTOM_LEFT_BACK
            (+hs, -hs, -hs),  # BOTTOM_RIGHT_BACK
        ]

        for i, (dx, dy, dz) in enumerate(offsets):
            child_boundary = BoundingBox(cx + dx, cy + dy, cz + dz, hs)
            self._children[i] = Octree(child_boundary, self._capacity, self._max_depth)
            self._children[i]._depth = self._depth + 1

        self._divided = True

    def insert(self, x: float, y: float, z: float, value: V) -> bool:
        """
        Insert point with value.

        Returns False if point outside boundary.
        """
        point = Point3D(x, y, z)

        with self._lock:
            return self._insert(point, value)

    def _insert(self, point: Point3D, value: V) -> bool:
        if not self._boundary.contains(point):
            return False

        if len(self._points) < self._capacity or self._depth >= self._max_depth:
            self._points.append((point, value))
            return True

        if not self._divided:
            self._subdivide()

        octant = self._get_octant(point)
        return self._children[octant]._insert(point, value)

    def query_box(
        self,
        center_x: float,
        center_y: float,
        center_z: float,
        half_size: float
    ) -> List[Tuple[Point3D, V]]:
        """Find all points in bounding box."""
        query_box = BoundingBox(center_x, center_y, center_z, half_size)

        with self._lock:
            found = []
            self._query_box(query_box, found)
            return found

    def _query_box(self, query_box: BoundingBox, found: List):
        if not self._boundary.intersects(query_box):
            return

        for point, value in self._points:
            if query_box.contains(point):
                found.append((point, value))

        if self._divided:
            for child in self._children:
                if child:
                    child._query_box(query_box, found)

    def query_sphere(
        self,
        center_x: float,
        center_y: float,
        center_z: float,
        radius: float
    ) -> List[Tuple[Point3D, V]]:
        """Find all points within sphere."""
        center = Point3D(center_x, center_y, center_z)

        with self._lock:
            found = []
            self._query_sphere(center, radius, found)
            return found

    def _query_sphere(self, center: Point3D, radius: float, found: List):
        # Use bounding box for initial filter
        bbox = BoundingBox(center.x, center.y, center.z, radius)
        if not self._boundary.intersects(bbox):
            return

        for point, value in self._points:
            if point.distance_to(center) <= radius:
                found.append((point, value))

        if self._divided:
            for child in self._children:
                if child:
                    child._query_sphere(center, radius, found)

    def nearest(
        self,
        x: float,
        y: float,
        z: float,
        count: int = 1
    ) -> List[Tuple[Point3D, V, float]]:
        """
        Find k nearest neighbors.

        Returns list of (point, value, distance).
        """
        query = Point3D(x, y, z)

        with self._lock:
            candidates = []
            self._collect_all(candidates)

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
            for child in self._children:
                if child:
                    child._collect_all(result)

    def count(self) -> int:
        """Count all points."""
        with self._lock:
            total = len(self._points)
            if self._divided:
                for child in self._children:
                    if child:
                        total += child.count()
            return total

    def __len__(self) -> int:
        return self.count()

    def get_stats(self) -> OctreeStats:
        """Get tree statistics."""
        with self._lock:
            def get_depth_and_nodes(node):
                if not node._divided:
                    return node._depth, 1

                max_depth = node._depth
                total_nodes = 1

                for child in node._children:
                    if child:
                        d, n = get_depth_and_nodes(child)
                        max_depth = max(max_depth, d)
                        total_nodes += n

                return max_depth, total_nodes

            depth, nodes = get_depth_and_nodes(self)

            return OctreeStats(
                num_points=self.count(),
                depth=depth,
                num_nodes=nodes,
                capacity=self._capacity
            )


# ============================================================================
# SPARSE VOXEL OCTREE
# ============================================================================

class SparseVoxelOctree:
    """
    Sparse Voxel Octree for volumetric data.

    Only stores occupied voxels.

    "Ba'el voxelizes sparsely." — Ba'el
    """

    def __init__(self, depth: int = 8):
        """
        Initialize SVO.

        Args:
            depth: Tree depth (resolution = 2^depth)
        """
        self._depth = depth
        self._resolution = 2 ** depth
        self._root: Dict[int, Any] = {}
        self._lock = threading.RLock()

    def _morton_encode(self, x: int, y: int, z: int) -> int:
        """Encode 3D coordinates to Morton code."""
        def expand(v):
            v = (v | (v << 16)) & 0x030000FF
            v = (v | (v << 8)) & 0x0300F00F
            v = (v | (v << 4)) & 0x030C30C3
            v = (v | (v << 2)) & 0x09249249
            return v

        return expand(x) | (expand(y) << 1) | (expand(z) << 2)

    def _morton_decode(self, morton: int) -> Tuple[int, int, int]:
        """Decode Morton code to 3D coordinates."""
        def compact(v):
            v &= 0x09249249
            v = (v | (v >> 2)) & 0x030C30C3
            v = (v | (v >> 4)) & 0x0300F00F
            v = (v | (v >> 8)) & 0x030000FF
            v = (v | (v >> 16)) & 0x000003FF
            return v

        return compact(morton), compact(morton >> 1), compact(morton >> 2)

    def set_voxel(self, x: int, y: int, z: int, value: Any = True):
        """Set voxel at position."""
        with self._lock:
            if 0 <= x < self._resolution and 0 <= y < self._resolution and 0 <= z < self._resolution:
                morton = self._morton_encode(x, y, z)
                self._root[morton] = value

    def get_voxel(self, x: int, y: int, z: int) -> Optional[Any]:
        """Get voxel at position."""
        with self._lock:
            if 0 <= x < self._resolution and 0 <= y < self._resolution and 0 <= z < self._resolution:
                morton = self._morton_encode(x, y, z)
                return self._root.get(morton)
            return None

    def clear_voxel(self, x: int, y: int, z: int):
        """Clear voxel at position."""
        with self._lock:
            morton = self._morton_encode(x, y, z)
            self._root.pop(morton, None)

    def is_occupied(self, x: int, y: int, z: int) -> bool:
        """Check if voxel is occupied."""
        return self.get_voxel(x, y, z) is not None

    def occupied_voxels(self) -> List[Tuple[int, int, int, Any]]:
        """Get all occupied voxels."""
        with self._lock:
            result = []
            for morton, value in self._root.items():
                x, y, z = self._morton_decode(morton)
                result.append((x, y, z, value))
            return result

    def count(self) -> int:
        """Count occupied voxels."""
        return len(self._root)


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_octree(
    center_x: float,
    center_y: float,
    center_z: float,
    half_size: float,
    capacity: int = 8
) -> Octree:
    """Create octree with given bounds."""
    boundary = BoundingBox(center_x, center_y, center_z, half_size)
    return Octree(boundary, capacity)


def create_svo(depth: int = 8) -> SparseVoxelOctree:
    """Create sparse voxel octree."""
    return SparseVoxelOctree(depth)


def build_octree(
    points: List[Tuple[float, float, float, Any]],
    boundary: Optional[Tuple[float, float, float, float]] = None
) -> Octree:
    """
    Build octree from points.

    Args:
        points: List of (x, y, z, value)
        boundary: Optional (center_x, center_y, center_z, half_size)
    """
    if not points:
        return create_octree(0, 0, 0, 50)

    if boundary is None:
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        zs = [p[2] for p in points]

        cx = (min(xs) + max(xs)) / 2
        cy = (min(ys) + max(ys)) / 2
        cz = (min(zs) + max(zs)) / 2

        half_size = max(
            max(xs) - min(xs),
            max(ys) - min(ys),
            max(zs) - min(zs)
        ) / 2 * 1.1
    else:
        cx, cy, cz, half_size = boundary

    tree = create_octree(cx, cy, cz, max(half_size, 1))

    for x, y, z, value in points:
        tree.insert(x, y, z, value)

    return tree
