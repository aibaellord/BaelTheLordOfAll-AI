#!/usr/bin/env python3
"""
BAEL - Spatial Reasoner
Advanced spatial reasoning and geometric computation.

Features:
- Spatial relationships (above, below, left, right, inside, etc.)
- Distance and proximity calculations
- Path planning and navigation
- Geometric transformations
- Collision detection
- Region queries
- Topological reasoning
"""

import asyncio
import heapq
import math
import random
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class SpatialRelation(Enum):
    """Spatial relationships."""
    ABOVE = "above"
    BELOW = "below"
    LEFT_OF = "left_of"
    RIGHT_OF = "right_of"
    IN_FRONT_OF = "in_front_of"
    BEHIND = "behind"
    INSIDE = "inside"
    OUTSIDE = "outside"
    TOUCHING = "touching"
    OVERLAPPING = "overlapping"
    NEAR = "near"
    FAR = "far"
    BETWEEN = "between"


class ShapeType(Enum):
    """Types of shapes."""
    POINT = "point"
    LINE = "line"
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    POLYGON = "polygon"
    BOX_3D = "box_3d"
    SPHERE = "sphere"


class PathAlgorithm(Enum):
    """Path planning algorithms."""
    A_STAR = "a_star"
    DIJKSTRA = "dijkstra"
    RRT = "rrt"
    POTENTIAL_FIELD = "potential_field"


class TransformType(Enum):
    """Geometric transformations."""
    TRANSLATE = "translate"
    ROTATE = "rotate"
    SCALE = "scale"
    REFLECT = "reflect"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Point2D:
    """A 2D point."""
    x: float = 0.0
    y: float = 0.0

    def distance_to(self, other: 'Point2D') -> float:
        """Calculate distance to another point."""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

    def __hash__(self):
        return hash((self.x, self.y))


@dataclass
class Point3D:
    """A 3D point."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def distance_to(self, other: 'Point3D') -> float:
        """Calculate distance to another point."""
        return math.sqrt(
            (self.x - other.x)**2 +
            (self.y - other.y)**2 +
            (self.z - other.z)**2
        )


@dataclass
class Vector2D:
    """A 2D vector."""
    x: float = 0.0
    y: float = 0.0

    def magnitude(self) -> float:
        """Get vector magnitude."""
        return math.sqrt(self.x**2 + self.y**2)

    def normalize(self) -> 'Vector2D':
        """Get normalized vector."""
        mag = self.magnitude()
        if mag == 0:
            return Vector2D(0, 0)
        return Vector2D(self.x / mag, self.y / mag)

    def dot(self, other: 'Vector2D') -> float:
        """Dot product."""
        return self.x * other.x + self.y * other.y


@dataclass
class BoundingBox:
    """An axis-aligned bounding box."""
    min_x: float = 0.0
    min_y: float = 0.0
    max_x: float = 0.0
    max_y: float = 0.0

    def contains(self, point: Point2D) -> bool:
        """Check if point is inside."""
        return (
            self.min_x <= point.x <= self.max_x and
            self.min_y <= point.y <= self.max_y
        )

    def intersects(self, other: 'BoundingBox') -> bool:
        """Check if boxes intersect."""
        return (
            self.min_x <= other.max_x and
            self.max_x >= other.min_x and
            self.min_y <= other.max_y and
            self.max_y >= other.min_y
        )


@dataclass
class Circle:
    """A circle."""
    center: Point2D = field(default_factory=Point2D)
    radius: float = 1.0

    def contains(self, point: Point2D) -> bool:
        """Check if point is inside."""
        return self.center.distance_to(point) <= self.radius


@dataclass
class SpatialObject:
    """A spatial object."""
    object_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    shape_type: ShapeType = ShapeType.POINT
    position: Point2D = field(default_factory=Point2D)
    bounds: Optional[BoundingBox] = None
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Path:
    """A path through space."""
    path_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    waypoints: List[Point2D] = field(default_factory=list)
    total_distance: float = 0.0
    algorithm: PathAlgorithm = PathAlgorithm.A_STAR


@dataclass
class Region:
    """A spatial region."""
    region_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    bounds: BoundingBox = field(default_factory=BoundingBox)
    objects: Set[str] = field(default_factory=set)


# =============================================================================
# GEOMETRY HELPERS
# =============================================================================

class GeometryHelper:
    """Geometric computation helpers."""

    @staticmethod
    def distance_2d(p1: Point2D, p2: Point2D) -> float:
        """Calculate 2D distance."""
        return p1.distance_to(p2)

    @staticmethod
    def distance_3d(p1: Point3D, p2: Point3D) -> float:
        """Calculate 3D distance."""
        return p1.distance_to(p2)

    @staticmethod
    def midpoint_2d(p1: Point2D, p2: Point2D) -> Point2D:
        """Calculate midpoint."""
        return Point2D(
            (p1.x + p2.x) / 2,
            (p1.y + p2.y) / 2
        )

    @staticmethod
    def angle_between(p1: Point2D, p2: Point2D) -> float:
        """Calculate angle between points (in radians)."""
        return math.atan2(p2.y - p1.y, p2.x - p1.x)

    @staticmethod
    def rotate_point(
        point: Point2D,
        center: Point2D,
        angle: float
    ) -> Point2D:
        """Rotate point around center."""
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)

        # Translate to origin
        dx = point.x - center.x
        dy = point.y - center.y

        # Rotate
        new_x = dx * cos_a - dy * sin_a
        new_y = dx * sin_a + dy * cos_a

        # Translate back
        return Point2D(new_x + center.x, new_y + center.y)

    @staticmethod
    def translate_point(
        point: Point2D,
        dx: float,
        dy: float
    ) -> Point2D:
        """Translate a point."""
        return Point2D(point.x + dx, point.y + dy)

    @staticmethod
    def scale_point(
        point: Point2D,
        center: Point2D,
        scale: float
    ) -> Point2D:
        """Scale point relative to center."""
        dx = (point.x - center.x) * scale
        dy = (point.y - center.y) * scale
        return Point2D(center.x + dx, center.y + dy)

    @staticmethod
    def line_intersection(
        p1: Point2D, p2: Point2D,
        p3: Point2D, p4: Point2D
    ) -> Optional[Point2D]:
        """Find intersection of two line segments."""
        x1, y1 = p1.x, p1.y
        x2, y2 = p2.x, p2.y
        x3, y3 = p3.x, p3.y
        x4, y4 = p4.x, p4.y

        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) < 1e-10:
            return None  # Parallel

        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom

        if 0 <= t <= 1 and 0 <= u <= 1:
            x = x1 + t * (x2 - x1)
            y = y1 + t * (y2 - y1)
            return Point2D(x, y)

        return None

    @staticmethod
    def point_in_polygon(
        point: Point2D,
        polygon: List[Point2D]
    ) -> bool:
        """Check if point is inside polygon (ray casting)."""
        n = len(polygon)
        inside = False

        j = n - 1
        for i in range(n):
            if ((polygon[i].y > point.y) != (polygon[j].y > point.y) and
                point.x < (polygon[j].x - polygon[i].x) *
                (point.y - polygon[i].y) / (polygon[j].y - polygon[i].y) +
                polygon[i].x):
                inside = not inside
            j = i

        return inside


# =============================================================================
# SPATIAL RELATION CALCULATOR
# =============================================================================

class SpatialRelationCalculator:
    """Calculate spatial relationships."""

    def __init__(self, near_threshold: float = 5.0):
        self._near_threshold = near_threshold

    def get_relation(
        self,
        obj1: SpatialObject,
        obj2: SpatialObject
    ) -> List[SpatialRelation]:
        """Get all spatial relations between objects."""
        relations = []

        # Directional relations
        if obj1.position.y > obj2.position.y:
            relations.append(SpatialRelation.ABOVE)
        elif obj1.position.y < obj2.position.y:
            relations.append(SpatialRelation.BELOW)

        if obj1.position.x < obj2.position.x:
            relations.append(SpatialRelation.LEFT_OF)
        elif obj1.position.x > obj2.position.x:
            relations.append(SpatialRelation.RIGHT_OF)

        # Proximity
        distance = obj1.position.distance_to(obj2.position)
        if distance < self._near_threshold:
            relations.append(SpatialRelation.NEAR)
        else:
            relations.append(SpatialRelation.FAR)

        # Containment (if bounds available)
        if obj1.bounds and obj2.bounds:
            if self._contains(obj1.bounds, obj2.bounds):
                relations.append(SpatialRelation.INSIDE)
            if self._overlaps(obj1.bounds, obj2.bounds):
                relations.append(SpatialRelation.OVERLAPPING)
            if self._touches(obj1.bounds, obj2.bounds):
                relations.append(SpatialRelation.TOUCHING)

        return relations

    def _contains(self, outer: BoundingBox, inner: BoundingBox) -> bool:
        """Check if outer contains inner."""
        return (
            outer.min_x <= inner.min_x and
            outer.max_x >= inner.max_x and
            outer.min_y <= inner.min_y and
            outer.max_y >= inner.max_y
        )

    def _overlaps(self, box1: BoundingBox, box2: BoundingBox) -> bool:
        """Check if boxes overlap."""
        return box1.intersects(box2)

    def _touches(self, box1: BoundingBox, box2: BoundingBox) -> bool:
        """Check if boxes are touching."""
        # Touching if exactly sharing an edge
        horizontal_touch = (
            (box1.max_x == box2.min_x or box1.min_x == box2.max_x) and
            not (box1.max_y < box2.min_y or box1.min_y > box2.max_y)
        )
        vertical_touch = (
            (box1.max_y == box2.min_y or box1.min_y == box2.max_y) and
            not (box1.max_x < box2.min_x or box1.min_x > box2.max_x)
        )
        return horizontal_touch or vertical_touch

    def is_between(
        self,
        obj: SpatialObject,
        obj1: SpatialObject,
        obj2: SpatialObject
    ) -> bool:
        """Check if obj is between obj1 and obj2."""
        # Check if on the line segment
        min_x = min(obj1.position.x, obj2.position.x)
        max_x = max(obj1.position.x, obj2.position.x)
        min_y = min(obj1.position.y, obj2.position.y)
        max_y = max(obj1.position.y, obj2.position.y)

        return (
            min_x <= obj.position.x <= max_x and
            min_y <= obj.position.y <= max_y
        )


# =============================================================================
# PATH PLANNER
# =============================================================================

class PathPlanner:
    """Plan paths through space."""

    def __init__(self, grid_size: float = 1.0):
        self._grid_size = grid_size
        self._obstacles: List[BoundingBox] = []

    def add_obstacle(self, obstacle: BoundingBox) -> None:
        """Add an obstacle."""
        self._obstacles.append(obstacle)

    def clear_obstacles(self) -> None:
        """Clear all obstacles."""
        self._obstacles.clear()

    def is_free(self, point: Point2D) -> bool:
        """Check if a point is free of obstacles."""
        for obstacle in self._obstacles:
            if obstacle.contains(point):
                return False
        return True

    def a_star(
        self,
        start: Point2D,
        goal: Point2D,
        bounds: BoundingBox
    ) -> Optional[Path]:
        """Find path using A*."""
        def heuristic(p: Tuple[int, int]) -> float:
            return math.sqrt(
                (p[0] * self._grid_size - goal.x)**2 +
                (p[1] * self._grid_size - goal.y)**2
            )

        start_grid = (
            int(start.x / self._grid_size),
            int(start.y / self._grid_size)
        )
        goal_grid = (
            int(goal.x / self._grid_size),
            int(goal.y / self._grid_size)
        )

        open_set = [(heuristic(start_grid), 0, start_grid)]
        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
        g_score: Dict[Tuple[int, int], float] = {start_grid: 0}

        directions = [
            (0, 1), (1, 0), (0, -1), (-1, 0),
            (1, 1), (1, -1), (-1, 1), (-1, -1)
        ]

        while open_set:
            _, _, current = heapq.heappop(open_set)

            if current == goal_grid:
                # Reconstruct path
                path_points = []
                node = current
                while node in came_from:
                    path_points.append(Point2D(
                        node[0] * self._grid_size,
                        node[1] * self._grid_size
                    ))
                    node = came_from[node]
                path_points.append(start)
                path_points.reverse()

                # Calculate total distance
                total_dist = 0.0
                for i in range(len(path_points) - 1):
                    total_dist += path_points[i].distance_to(path_points[i + 1])

                return Path(
                    waypoints=path_points,
                    total_distance=total_dist,
                    algorithm=PathAlgorithm.A_STAR
                )

            for dx, dy in directions:
                neighbor = (current[0] + dx, current[1] + dy)
                neighbor_point = Point2D(
                    neighbor[0] * self._grid_size,
                    neighbor[1] * self._grid_size
                )

                # Check bounds
                if not (bounds.min_x <= neighbor_point.x <= bounds.max_x and
                        bounds.min_y <= neighbor_point.y <= bounds.max_y):
                    continue

                # Check obstacles
                if not self.is_free(neighbor_point):
                    continue

                # Calculate cost
                move_cost = math.sqrt(dx**2 + dy**2) * self._grid_size
                tentative_g = g_score[current] + move_cost

                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score = tentative_g + heuristic(neighbor)
                    heapq.heappush(open_set, (f_score, tentative_g, neighbor))

        return None  # No path found

    def smooth_path(self, path: Path) -> Path:
        """Smooth a path by removing unnecessary waypoints."""
        if len(path.waypoints) < 3:
            return path

        smoothed = [path.waypoints[0]]

        i = 0
        while i < len(path.waypoints) - 1:
            # Try to skip intermediate points
            j = len(path.waypoints) - 1
            while j > i + 1:
                if self._line_of_sight(path.waypoints[i], path.waypoints[j]):
                    break
                j -= 1

            smoothed.append(path.waypoints[j])
            i = j

        # Recalculate distance
        total_dist = 0.0
        for i in range(len(smoothed) - 1):
            total_dist += smoothed[i].distance_to(smoothed[i + 1])

        return Path(
            waypoints=smoothed,
            total_distance=total_dist,
            algorithm=path.algorithm
        )

    def _line_of_sight(self, p1: Point2D, p2: Point2D) -> bool:
        """Check if there's line of sight between points."""
        # Sample points along the line
        dist = p1.distance_to(p2)
        steps = int(dist / (self._grid_size / 2)) + 1

        for i in range(steps + 1):
            t = i / steps if steps > 0 else 0
            x = p1.x + t * (p2.x - p1.x)
            y = p1.y + t * (p2.y - p1.y)

            if not self.is_free(Point2D(x, y)):
                return False

        return True


# =============================================================================
# SPATIAL INDEX
# =============================================================================

class SpatialIndex:
    """Spatial index for efficient queries."""

    def __init__(self, cell_size: float = 10.0):
        self._cell_size = cell_size
        self._grid: Dict[Tuple[int, int], Set[str]] = defaultdict(set)
        self._objects: Dict[str, SpatialObject] = {}

    def _get_cell(self, point: Point2D) -> Tuple[int, int]:
        """Get grid cell for a point."""
        return (
            int(point.x / self._cell_size),
            int(point.y / self._cell_size)
        )

    def insert(self, obj: SpatialObject) -> None:
        """Insert an object."""
        cell = self._get_cell(obj.position)
        self._grid[cell].add(obj.object_id)
        self._objects[obj.object_id] = obj

    def remove(self, object_id: str) -> bool:
        """Remove an object."""
        obj = self._objects.get(object_id)
        if not obj:
            return False

        cell = self._get_cell(obj.position)
        self._grid[cell].discard(object_id)
        del self._objects[object_id]
        return True

    def update(self, object_id: str, new_position: Point2D) -> bool:
        """Update object position."""
        obj = self._objects.get(object_id)
        if not obj:
            return False

        old_cell = self._get_cell(obj.position)
        new_cell = self._get_cell(new_position)

        if old_cell != new_cell:
            self._grid[old_cell].discard(object_id)
            self._grid[new_cell].add(object_id)

        obj.position = new_position
        return True

    def query_radius(
        self,
        center: Point2D,
        radius: float
    ) -> List[SpatialObject]:
        """Find all objects within radius."""
        results = []

        # Determine cells to check
        min_cell = self._get_cell(Point2D(center.x - radius, center.y - radius))
        max_cell = self._get_cell(Point2D(center.x + radius, center.y + radius))

        for cx in range(min_cell[0], max_cell[0] + 1):
            for cy in range(min_cell[1], max_cell[1] + 1):
                for obj_id in self._grid[(cx, cy)]:
                    obj = self._objects[obj_id]
                    if center.distance_to(obj.position) <= radius:
                        results.append(obj)

        return results

    def query_rect(self, bounds: BoundingBox) -> List[SpatialObject]:
        """Find all objects in rectangle."""
        results = []

        min_cell = self._get_cell(Point2D(bounds.min_x, bounds.min_y))
        max_cell = self._get_cell(Point2D(bounds.max_x, bounds.max_y))

        for cx in range(min_cell[0], max_cell[0] + 1):
            for cy in range(min_cell[1], max_cell[1] + 1):
                for obj_id in self._grid[(cx, cy)]:
                    obj = self._objects[obj_id]
                    if bounds.contains(obj.position):
                        results.append(obj)

        return results

    def nearest_neighbor(
        self,
        point: Point2D,
        k: int = 1
    ) -> List[Tuple[SpatialObject, float]]:
        """Find k nearest neighbors."""
        # Simple approach: check all objects
        distances = []

        for obj in self._objects.values():
            dist = point.distance_to(obj.position)
            distances.append((obj, dist))

        distances.sort(key=lambda x: x[1])
        return distances[:k]


# =============================================================================
# SPATIAL REASONER
# =============================================================================

class SpatialReasoner:
    """
    Spatial Reasoner for BAEL.

    Advanced spatial reasoning and geometric computation.
    """

    def __init__(self, grid_size: float = 1.0):
        self._geometry = GeometryHelper()
        self._relation_calc = SpatialRelationCalculator()
        self._path_planner = PathPlanner(grid_size)
        self._spatial_index = SpatialIndex()

        self._objects: Dict[str, SpatialObject] = {}
        self._regions: Dict[str, Region] = {}

    # -------------------------------------------------------------------------
    # OBJECT MANAGEMENT
    # -------------------------------------------------------------------------

    def add_object(
        self,
        name: str,
        x: float,
        y: float,
        shape_type: ShapeType = ShapeType.POINT,
        width: float = 0,
        height: float = 0
    ) -> SpatialObject:
        """Add a spatial object."""
        position = Point2D(x, y)

        bounds = None
        if width > 0 and height > 0:
            bounds = BoundingBox(
                min_x=x - width/2,
                min_y=y - height/2,
                max_x=x + width/2,
                max_y=y + height/2
            )

        obj = SpatialObject(
            name=name,
            shape_type=shape_type,
            position=position,
            bounds=bounds
        )

        self._objects[obj.object_id] = obj
        self._spatial_index.insert(obj)

        return obj

    def get_object(self, object_id: str) -> Optional[SpatialObject]:
        """Get an object."""
        return self._objects.get(object_id)

    def move_object(
        self,
        object_id: str,
        x: float,
        y: float
    ) -> bool:
        """Move an object."""
        obj = self._objects.get(object_id)
        if not obj:
            return False

        new_pos = Point2D(x, y)
        self._spatial_index.update(object_id, new_pos)

        if obj.bounds:
            dx = x - obj.position.x
            dy = y - obj.position.y
            obj.bounds.min_x += dx
            obj.bounds.max_x += dx
            obj.bounds.min_y += dy
            obj.bounds.max_y += dy

        obj.position = new_pos
        return True

    def remove_object(self, object_id: str) -> bool:
        """Remove an object."""
        if object_id not in self._objects:
            return False

        self._spatial_index.remove(object_id)
        del self._objects[object_id]
        return True

    # -------------------------------------------------------------------------
    # SPATIAL RELATIONS
    # -------------------------------------------------------------------------

    def get_relation(
        self,
        object_id1: str,
        object_id2: str
    ) -> List[SpatialRelation]:
        """Get spatial relations between objects."""
        obj1 = self._objects.get(object_id1)
        obj2 = self._objects.get(object_id2)

        if not obj1 or not obj2:
            return []

        return self._relation_calc.get_relation(obj1, obj2)

    def is_near(
        self,
        object_id1: str,
        object_id2: str,
        threshold: float = 5.0
    ) -> bool:
        """Check if objects are near."""
        obj1 = self._objects.get(object_id1)
        obj2 = self._objects.get(object_id2)

        if not obj1 or not obj2:
            return False

        return obj1.position.distance_to(obj2.position) < threshold

    def distance(
        self,
        object_id1: str,
        object_id2: str
    ) -> float:
        """Get distance between objects."""
        obj1 = self._objects.get(object_id1)
        obj2 = self._objects.get(object_id2)

        if not obj1 or not obj2:
            return float('inf')

        return obj1.position.distance_to(obj2.position)

    # -------------------------------------------------------------------------
    # SPATIAL QUERIES
    # -------------------------------------------------------------------------

    def find_in_radius(
        self,
        x: float,
        y: float,
        radius: float
    ) -> List[SpatialObject]:
        """Find objects within radius."""
        return self._spatial_index.query_radius(Point2D(x, y), radius)

    def find_in_rect(
        self,
        min_x: float,
        min_y: float,
        max_x: float,
        max_y: float
    ) -> List[SpatialObject]:
        """Find objects in rectangle."""
        bounds = BoundingBox(min_x, min_y, max_x, max_y)
        return self._spatial_index.query_rect(bounds)

    def find_nearest(
        self,
        x: float,
        y: float,
        k: int = 1
    ) -> List[Tuple[SpatialObject, float]]:
        """Find k nearest objects."""
        return self._spatial_index.nearest_neighbor(Point2D(x, y), k)

    # -------------------------------------------------------------------------
    # PATH PLANNING
    # -------------------------------------------------------------------------

    def add_obstacle(
        self,
        min_x: float,
        min_y: float,
        max_x: float,
        max_y: float
    ) -> None:
        """Add an obstacle for path planning."""
        self._path_planner.add_obstacle(BoundingBox(min_x, min_y, max_x, max_y))

    def find_path(
        self,
        start_x: float,
        start_y: float,
        goal_x: float,
        goal_y: float,
        bounds: Optional[BoundingBox] = None
    ) -> Optional[Path]:
        """Find path between points."""
        start = Point2D(start_x, start_y)
        goal = Point2D(goal_x, goal_y)

        if bounds is None:
            bounds = BoundingBox(-100, -100, 100, 100)

        path = self._path_planner.a_star(start, goal, bounds)

        if path:
            path = self._path_planner.smooth_path(path)

        return path

    # -------------------------------------------------------------------------
    # GEOMETRY
    # -------------------------------------------------------------------------

    def rotate_object(
        self,
        object_id: str,
        angle: float,
        center_x: Optional[float] = None,
        center_y: Optional[float] = None
    ) -> bool:
        """Rotate object around a point."""
        obj = self._objects.get(object_id)
        if not obj:
            return False

        center = Point2D(
            center_x if center_x is not None else obj.position.x,
            center_y if center_y is not None else obj.position.y
        )

        new_pos = self._geometry.rotate_point(obj.position, center, angle)
        return self.move_object(object_id, new_pos.x, new_pos.y)

    def point_distance(
        self,
        x1: float, y1: float,
        x2: float, y2: float
    ) -> float:
        """Calculate distance between points."""
        return self._geometry.distance_2d(Point2D(x1, y1), Point2D(x2, y2))

    def angle_between_points(
        self,
        x1: float, y1: float,
        x2: float, y2: float
    ) -> float:
        """Get angle between points in degrees."""
        radians = self._geometry.angle_between(Point2D(x1, y1), Point2D(x2, y2))
        return math.degrees(radians)

    # -------------------------------------------------------------------------
    # REGIONS
    # -------------------------------------------------------------------------

    def create_region(
        self,
        name: str,
        min_x: float,
        min_y: float,
        max_x: float,
        max_y: float
    ) -> Region:
        """Create a spatial region."""
        region = Region(
            name=name,
            bounds=BoundingBox(min_x, min_y, max_x, max_y)
        )
        self._regions[region.region_id] = region
        return region

    def get_objects_in_region(self, region_id: str) -> List[SpatialObject]:
        """Get objects in a region."""
        region = self._regions.get(region_id)
        if not region:
            return []

        return self.find_in_rect(
            region.bounds.min_x,
            region.bounds.min_y,
            region.bounds.max_x,
            region.bounds.max_y
        )


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Spatial Reasoner."""
    print("=" * 70)
    print("BAEL - SPATIAL REASONER DEMO")
    print("Advanced Spatial Reasoning and Geometric Computation")
    print("=" * 70)
    print()

    reasoner = SpatialReasoner(grid_size=1.0)

    # 1. Add Objects
    print("1. ADD SPATIAL OBJECTS:")
    print("-" * 40)

    robot = reasoner.add_object("Robot", 0, 0, ShapeType.CIRCLE, 2, 2)
    box1 = reasoner.add_object("Box-A", 5, 5, ShapeType.RECTANGLE, 1, 1)
    box2 = reasoner.add_object("Box-B", 10, 3, ShapeType.RECTANGLE, 1, 1)
    goal = reasoner.add_object("Goal", 15, 15, ShapeType.POINT)

    print(f"   Robot at (0, 0)")
    print(f"   Box-A at (5, 5)")
    print(f"   Box-B at (10, 3)")
    print(f"   Goal at (15, 15)")
    print()

    # 2. Spatial Relations
    print("2. SPATIAL RELATIONS:")
    print("-" * 40)

    relations = reasoner.get_relation(robot.object_id, box1.object_id)
    print(f"   Robot to Box-A: {[r.value for r in relations]}")

    relations = reasoner.get_relation(box1.object_id, box2.object_id)
    print(f"   Box-A to Box-B: {[r.value for r in relations]}")
    print()

    # 3. Distance Calculations
    print("3. DISTANCES:")
    print("-" * 40)

    dist = reasoner.distance(robot.object_id, box1.object_id)
    print(f"   Robot to Box-A: {dist:.2f}")

    dist = reasoner.distance(robot.object_id, goal.object_id)
    print(f"   Robot to Goal: {dist:.2f}")

    is_near = reasoner.is_near(robot.object_id, box1.object_id, threshold=10)
    print(f"   Robot near Box-A (threshold=10): {is_near}")
    print()

    # 4. Spatial Queries
    print("4. SPATIAL QUERIES:")
    print("-" * 40)

    nearby = reasoner.find_in_radius(5, 5, 8)
    print(f"   Objects within 8 units of (5,5): {[o.name for o in nearby]}")

    in_rect = reasoner.find_in_rect(0, 0, 12, 12)
    print(f"   Objects in rect (0,0)-(12,12): {[o.name for o in in_rect]}")

    nearest = reasoner.find_nearest(7, 4, k=2)
    print(f"   2 nearest to (7,4): {[(o.name, f'{d:.2f}') for o, d in nearest]}")
    print()

    # 5. Movement
    print("5. OBJECT MOVEMENT:")
    print("-" * 40)

    reasoner.move_object(robot.object_id, 3, 3)
    obj = reasoner.get_object(robot.object_id)
    print(f"   Moved Robot to ({obj.position.x}, {obj.position.y})")

    dist = reasoner.distance(robot.object_id, box1.object_id)
    print(f"   New distance to Box-A: {dist:.2f}")
    print()

    # 6. Path Planning
    print("6. PATH PLANNING:")
    print("-" * 40)

    # Add obstacles
    reasoner.add_obstacle(6, 6, 9, 9)
    print("   Added obstacle at (6,6)-(9,9)")

    path = reasoner.find_path(
        0, 0, 15, 15,
        bounds=BoundingBox(-5, -5, 20, 20)
    )

    if path:
        print(f"   Path found: {len(path.waypoints)} waypoints")
        print(f"   Total distance: {path.total_distance:.2f}")
        print(f"   Algorithm: {path.algorithm.value}")
    else:
        print("   No path found")
    print()

    # 7. Geometry Operations
    print("7. GEOMETRY OPERATIONS:")
    print("-" * 40)

    dist = reasoner.point_distance(0, 0, 3, 4)
    print(f"   Distance (0,0) to (3,4): {dist:.2f}")

    angle = reasoner.angle_between_points(0, 0, 1, 1)
    print(f"   Angle (0,0) to (1,1): {angle:.2f}°")

    angle = reasoner.angle_between_points(0, 0, 0, 1)
    print(f"   Angle (0,0) to (0,1): {angle:.2f}°")
    print()

    # 8. Regions
    print("8. SPATIAL REGIONS:")
    print("-" * 40)

    zone1 = reasoner.create_region("Zone-A", 0, 0, 8, 8)
    zone2 = reasoner.create_region("Zone-B", 8, 0, 20, 20)

    objects_in_zone1 = reasoner.get_objects_in_region(zone1.region_id)
    print(f"   Objects in Zone-A: {[o.name for o in objects_in_zone1]}")

    objects_in_zone2 = reasoner.get_objects_in_region(zone2.region_id)
    print(f"   Objects in Zone-B: {[o.name for o in objects_in_zone2]}")
    print()

    # 9. Multiple Object Demo
    print("9. MULTI-OBJECT SCENE:")
    print("-" * 40)

    # Add more objects
    for i in range(5):
        x = random.uniform(0, 20)
        y = random.uniform(0, 20)
        reasoner.add_object(f"Item-{i}", x, y)

    all_in_scene = reasoner.find_in_rect(-5, -5, 25, 25)
    print(f"   Total objects in scene: {len(all_in_scene)}")

    # Find clusters
    clustered = reasoner.find_in_radius(10, 10, 7)
    print(f"   Objects near center (10,10): {len(clustered)}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Spatial Reasoner Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
