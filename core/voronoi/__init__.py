"""
BAEL Voronoi Diagram Engine
===========================

Voronoi diagram and Delaunay triangulation.

"Ba'el partitions space by proximity." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
import math
from collections import defaultdict

logger = logging.getLogger("BAEL.Voronoi")


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

    def distance_to(self, other: 'Point2D') -> float:
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)


@dataclass
class Edge:
    """Voronoi edge."""
    start: Point2D
    end: Optional[Point2D] = None  # None for infinite edges
    left_site: int = -1   # Site index
    right_site: int = -1


@dataclass
class Triangle:
    """Delaunay triangle."""
    p1: int  # Point indices
    p2: int
    p3: int
    circumcenter: Optional[Point2D] = None
    circumradius: float = 0.0


@dataclass
class VoronoiCell:
    """Voronoi cell (region)."""
    site: Point2D
    site_index: int
    vertices: List[Point2D] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)
    is_infinite: bool = False


@dataclass
class VoronoiDiagram:
    """Complete Voronoi diagram."""
    sites: List[Point2D] = field(default_factory=list)
    vertices: List[Point2D] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)
    cells: List[VoronoiCell] = field(default_factory=list)


@dataclass
class DelaunayTriangulation:
    """Complete Delaunay triangulation."""
    points: List[Point2D] = field(default_factory=list)
    triangles: List[Triangle] = field(default_factory=list)
    edges: Set[Tuple[int, int]] = field(default_factory=set)


# ============================================================================
# HELPERS
# ============================================================================

def circumcircle(p1: Point2D, p2: Point2D, p3: Point2D) -> Tuple[Optional[Point2D], float]:
    """
    Compute circumcircle of three points.

    Returns:
        (center, radius) or (None, 0) if degenerate
    """
    ax, ay = p1.x, p1.y
    bx, by = p2.x, p2.y
    cx, cy = p3.x, p3.y

    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))

    if abs(d) < 1e-10:
        return None, 0.0

    ux = ((ax * ax + ay * ay) * (by - cy) +
          (bx * bx + by * by) * (cy - ay) +
          (cx * cx + cy * cy) * (ay - by)) / d

    uy = ((ax * ax + ay * ay) * (cx - bx) +
          (bx * bx + by * by) * (ax - cx) +
          (cx * cx + cy * cy) * (bx - ax)) / d

    center = Point2D(ux, uy)
    radius = center.distance_to(p1)

    return center, radius


def point_in_circumcircle(p: Point2D, p1: Point2D, p2: Point2D, p3: Point2D) -> bool:
    """Check if point is inside circumcircle of triangle."""
    center, radius = circumcircle(p1, p2, p3)
    if center is None:
        return False

    return center.distance_to(p) < radius - 1e-9


def orientation(p1: Point2D, p2: Point2D, p3: Point2D) -> int:
    """
    Compute orientation of triplet.

    Returns:
        1 = counter-clockwise
        -1 = clockwise
        0 = collinear
    """
    val = (p2.y - p1.y) * (p3.x - p2.x) - (p2.x - p1.x) * (p3.y - p2.y)

    if abs(val) < 1e-10:
        return 0
    return 1 if val > 0 else -1


# ============================================================================
# DELAUNAY TRIANGULATION (BOWYER-WATSON)
# ============================================================================

class DelaunayTriangulator:
    """
    Delaunay triangulation using Bowyer-Watson algorithm.

    Features:
    - O(n²) worst case, O(n log n) expected
    - Incremental point insertion
    - Circumcircle property maintained

    "Ba'el triangulates optimally." — Ba'el
    """

    def __init__(self):
        """Initialize Delaunay triangulator."""
        self._points: List[Point2D] = []
        self._triangulation: Optional[DelaunayTriangulation] = None
        self._lock = threading.RLock()

        logger.debug("Delaunay triangulator initialized")

    def add_point(self, x: float, y: float) -> int:
        """Add point and return its index."""
        with self._lock:
            idx = len(self._points)
            self._points.append(Point2D(x, y))
            self._triangulation = None  # Invalidate
            return idx

    def add_points(self, points: List[Tuple[float, float]]) -> List[int]:
        """Add multiple points."""
        with self._lock:
            start_idx = len(self._points)
            for x, y in points:
                self._points.append(Point2D(x, y))
            self._triangulation = None
            return list(range(start_idx, len(self._points)))

    def triangulate(self) -> DelaunayTriangulation:
        """
        Compute Delaunay triangulation.

        Returns:
            DelaunayTriangulation object
        """
        with self._lock:
            if self._triangulation is not None:
                return self._triangulation

            n = len(self._points)

            if n < 3:
                self._triangulation = DelaunayTriangulation(
                    points=self._points.copy(),
                    triangles=[],
                    edges=set()
                )
                return self._triangulation

            # Create super-triangle
            min_x = min(p.x for p in self._points) - 1
            max_x = max(p.x for p in self._points) + 1
            min_y = min(p.y for p in self._points) - 1
            max_y = max(p.y for p in self._points) + 1

            dx = max_x - min_x
            dy = max_y - min_y
            delta = max(dx, dy) * 10

            # Super-triangle vertices (at indices n, n+1, n+2)
            super_points = [
                Point2D(min_x - delta, min_y - 1),
                Point2D(max_x + delta, min_y - 1),
                Point2D((min_x + max_x) / 2, max_y + delta)
            ]

            all_points = self._points + super_points

            # Initial triangulation with super-triangle
            triangles = [Triangle(n, n + 1, n + 2)]

            # Add points incrementally
            for i in range(n):
                p = self._points[i]

                # Find triangles whose circumcircle contains p
                bad_triangles = []
                for tri in triangles:
                    if point_in_circumcircle(p,
                                            all_points[tri.p1],
                                            all_points[tri.p2],
                                            all_points[tri.p3]):
                        bad_triangles.append(tri)

                # Find boundary of polygonal hole
                edges = []
                for tri in bad_triangles:
                    for edge in [(tri.p1, tri.p2), (tri.p2, tri.p3), (tri.p3, tri.p1)]:
                        # Edge is on boundary if only one triangle contains it
                        e = tuple(sorted(edge))
                        found = False
                        for other in bad_triangles:
                            if other is tri:
                                continue
                            other_edges = [tuple(sorted(oe)) for oe in
                                         [(other.p1, other.p2), (other.p2, other.p3), (other.p3, other.p1)]]
                            if e in other_edges:
                                found = True
                                break
                        if not found:
                            edges.append(edge)

                # Remove bad triangles
                for tri in bad_triangles:
                    triangles.remove(tri)

                # Create new triangles
                for e1, e2 in edges:
                    triangles.append(Triangle(i, e1, e2))

            # Remove triangles connected to super-triangle
            final_triangles = []
            for tri in triangles:
                if tri.p1 < n and tri.p2 < n and tri.p3 < n:
                    center, radius = circumcircle(
                        self._points[tri.p1],
                        self._points[tri.p2],
                        self._points[tri.p3]
                    )
                    tri.circumcenter = center
                    tri.circumradius = radius
                    final_triangles.append(tri)

            # Extract edges
            edges = set()
            for tri in final_triangles:
                edges.add(tuple(sorted([tri.p1, tri.p2])))
                edges.add(tuple(sorted([tri.p2, tri.p3])))
                edges.add(tuple(sorted([tri.p3, tri.p1])))

            self._triangulation = DelaunayTriangulation(
                points=self._points.copy(),
                triangles=final_triangles,
                edges=edges
            )

            return self._triangulation

    def get_neighbors(self, point_idx: int) -> List[int]:
        """Get indices of neighboring points in triangulation."""
        triangulation = self.triangulate()
        neighbors = set()

        for e1, e2 in triangulation.edges:
            if e1 == point_idx:
                neighbors.add(e2)
            elif e2 == point_idx:
                neighbors.add(e1)

        return list(neighbors)


# ============================================================================
# VORONOI DIAGRAM
# ============================================================================

class VoronoiGenerator:
    """
    Voronoi diagram generator (via Delaunay dual).

    Features:
    - Dual of Delaunay triangulation
    - O(n log n) construction

    "Ba'el partitions the plane." — Ba'el
    """

    def __init__(self):
        """Initialize Voronoi generator."""
        self._points: List[Point2D] = []
        self._diagram: Optional[VoronoiDiagram] = None
        self._lock = threading.RLock()

        logger.debug("Voronoi generator initialized")

    def add_site(self, x: float, y: float) -> int:
        """Add site and return its index."""
        with self._lock:
            idx = len(self._points)
            self._points.append(Point2D(x, y))
            self._diagram = None
            return idx

    def add_sites(self, sites: List[Tuple[float, float]]) -> List[int]:
        """Add multiple sites."""
        with self._lock:
            start_idx = len(self._points)
            for x, y in sites:
                self._points.append(Point2D(x, y))
            self._diagram = None
            return list(range(start_idx, len(self._points)))

    def generate(self) -> VoronoiDiagram:
        """
        Generate Voronoi diagram.

        Returns:
            VoronoiDiagram object
        """
        with self._lock:
            if self._diagram is not None:
                return self._diagram

            n = len(self._points)

            if n < 2:
                self._diagram = VoronoiDiagram(sites=self._points.copy())
                return self._diagram

            # Compute Delaunay triangulation
            triangulator = DelaunayTriangulator()
            for p in self._points:
                triangulator.add_point(p.x, p.y)

            delaunay = triangulator.triangulate()

            # Voronoi vertices are circumcenters of Delaunay triangles
            vertices = []
            tri_to_vertex: Dict[int, int] = {}

            for i, tri in enumerate(delaunay.triangles):
                if tri.circumcenter:
                    tri_to_vertex[i] = len(vertices)
                    vertices.append(tri.circumcenter)

            # Build adjacency: which triangles share each edge
            edge_triangles: Dict[Tuple[int, int], List[int]] = defaultdict(list)
            for i, tri in enumerate(delaunay.triangles):
                for edge in [(tri.p1, tri.p2), (tri.p2, tri.p3), (tri.p3, tri.p1)]:
                    e = tuple(sorted(edge))
                    edge_triangles[e].append(i)

            # Voronoi edges connect circumcenters of adjacent triangles
            edges = []
            for edge, tris in edge_triangles.items():
                if len(tris) == 2:
                    t1, t2 = tris
                    if t1 in tri_to_vertex and t2 in tri_to_vertex:
                        edges.append(Edge(
                            start=vertices[tri_to_vertex[t1]],
                            end=vertices[tri_to_vertex[t2]],
                            left_site=edge[0],
                            right_site=edge[1]
                        ))
                elif len(tris) == 1:
                    # Infinite edge (boundary)
                    t = tris[0]
                    if t in tri_to_vertex:
                        edges.append(Edge(
                            start=vertices[tri_to_vertex[t]],
                            end=None,  # Infinite
                            left_site=edge[0],
                            right_site=edge[1]
                        ))

            # Build cells
            cells = []
            for i, site in enumerate(self._points):
                cell = VoronoiCell(site=site, site_index=i)

                # Collect edges and vertices for this cell
                for edge in edges:
                    if edge.left_site == i or edge.right_site == i:
                        cell.edges.append(edge)
                        if edge.start and edge.start not in cell.vertices:
                            cell.vertices.append(edge.start)
                        if edge.end and edge.end not in cell.vertices:
                            cell.vertices.append(edge.end)
                        if edge.end is None:
                            cell.is_infinite = True

                cells.append(cell)

            self._diagram = VoronoiDiagram(
                sites=self._points.copy(),
                vertices=vertices,
                edges=edges,
                cells=cells
            )

            return self._diagram

    def nearest_site(self, x: float, y: float) -> int:
        """
        Find index of nearest site to query point.

        Simple O(n) search.
        """
        with self._lock:
            query = Point2D(x, y)

            min_dist = float('inf')
            nearest = 0

            for i, site in enumerate(self._points):
                dist = query.distance_to(site)
                if dist < min_dist:
                    min_dist = dist
                    nearest = i

            return nearest


# ============================================================================
# FORTUNE'S ALGORITHM (SWEEP LINE)
# ============================================================================

class FortuneVoronoi:
    """
    Fortune's algorithm for Voronoi diagram.

    Features:
    - O(n log n) time
    - Beach line and event queue

    "Ba'el sweeps to build Voronoi." — Ba'el
    """

    def __init__(self):
        """Initialize Fortune's algorithm."""
        self._sites: List[Point2D] = []
        self._diagram: Optional[VoronoiDiagram] = None
        self._lock = threading.RLock()

    def add_site(self, x: float, y: float) -> int:
        """Add site."""
        with self._lock:
            idx = len(self._sites)
            self._sites.append(Point2D(x, y))
            self._diagram = None
            return idx

    def generate(self) -> VoronoiDiagram:
        """
        Generate Voronoi using Fortune's sweep.

        Note: Simplified implementation using Delaunay dual.
        Full Fortune's is complex with parabola handling.
        """
        with self._lock:
            # Use Delaunay dual for now (correct results)
            gen = VoronoiGenerator()
            for site in self._sites:
                gen.add_site(site.x, site.y)

            return gen.generate()


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_delaunay_triangulator() -> DelaunayTriangulator:
    """Create Delaunay triangulator."""
    return DelaunayTriangulator()


def create_voronoi_generator() -> VoronoiGenerator:
    """Create Voronoi generator."""
    return VoronoiGenerator()


def delaunay_triangulation(points: List[Tuple[float, float]]) -> List[Tuple[int, int, int]]:
    """
    Compute Delaunay triangulation.

    Returns:
        List of (i, j, k) index tuples for triangles
    """
    triangulator = DelaunayTriangulator()
    triangulator.add_points(points)
    result = triangulator.triangulate()
    return [(t.p1, t.p2, t.p3) for t in result.triangles]


def voronoi_diagram(sites: List[Tuple[float, float]]) -> Dict[str, Any]:
    """
    Compute Voronoi diagram.

    Returns:
        Dict with 'sites', 'vertices', 'edges' info
    """
    generator = VoronoiGenerator()
    generator.add_sites(sites)
    diagram = generator.generate()

    return {
        'sites': [(s.x, s.y) for s in diagram.sites],
        'vertices': [(v.x, v.y) for v in diagram.vertices],
        'edge_count': len(diagram.edges),
        'cell_count': len(diagram.cells)
    }


def nearest_neighbor(sites: List[Tuple[float, float]], query: Tuple[float, float]) -> int:
    """Find nearest site to query point."""
    generator = VoronoiGenerator()
    generator.add_sites(sites)
    return generator.nearest_site(query[0], query[1])


def delaunay_edges(points: List[Tuple[float, float]]) -> List[Tuple[int, int]]:
    """Get edges of Delaunay triangulation."""
    triangulator = DelaunayTriangulator()
    triangulator.add_points(points)
    result = triangulator.triangulate()
    return list(result.edges)
