"""
BAEL Spatial Cognition Engine
==============================

Spatial reasoning, navigation, and mental maps.
Cognitive mapping and spatial representation.

"Ba'el navigates all spaces." — Ba'el
"""

import logging
import threading
import time
import math
import random
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod
from collections import defaultdict, deque
import heapq
import copy

logger = logging.getLogger("BAEL.SpatialCognition")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ReferenceFrame(Enum):
    """Spatial reference frames."""
    EGOCENTRIC = auto()    # Self-centered (left/right/front/back)
    ALLOCENTRIC = auto()   # World-centered (north/south/east/west)
    OBJECT_CENTERED = auto()  # Relative to object


class SpatialRelation(Enum):
    """Spatial relations."""
    ABOVE = auto()
    BELOW = auto()
    LEFT = auto()
    RIGHT = auto()
    IN_FRONT = auto()
    BEHIND = auto()
    INSIDE = auto()
    OUTSIDE = auto()
    NEAR = auto()
    FAR = auto()
    ADJACENT = auto()
    OVERLAPPING = auto()


class NavigationMode(Enum):
    """Navigation modes."""
    ROUTE = auto()       # Turn-by-turn
    SURVEY = auto()      # Map-based
    LANDMARK = auto()    # Landmark-guided


@dataclass
class Point:
    """
    A point in space.
    """
    x: float
    y: float
    z: float = 0.0

    def distance_to(self, other: 'Point') -> float:
        return math.sqrt(
            (self.x - other.x) ** 2 +
            (self.y - other.y) ** 2 +
            (self.z - other.z) ** 2
        )

    def __add__(self, other: 'Point') -> 'Point':
        return Point(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: 'Point') -> 'Point':
        return Point(self.x - other.x, self.y - other.y, self.z - other.z)


@dataclass
class Location:
    """
    A named location.
    """
    id: str
    name: str
    position: Point
    properties: Dict[str, Any] = field(default_factory=dict)
    is_landmark: bool = False


@dataclass
class Path:
    """
    A path between locations.
    """
    id: str
    start_id: str
    end_id: str
    distance: float
    traversable: bool = True
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Region:
    """
    A spatial region.
    """
    id: str
    name: str
    boundary: List[Point]
    center: Point
    area: float = 0.0

    def contains(self, point: Point) -> bool:
        """Check if point is inside region (ray casting)."""
        if len(self.boundary) < 3:
            return False

        n = len(self.boundary)
        inside = False

        p1x, p1y = self.boundary[0].x, self.boundary[0].y
        for i in range(1, n + 1):
            p2x, p2y = self.boundary[i % n].x, self.boundary[i % n].y
            if point.y > min(p1y, p2y):
                if point.y <= max(p1y, p2y):
                    if point.x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (point.y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or point.x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y

        return inside


@dataclass
class SpatialRelationship:
    """
    A spatial relationship.
    """
    subject_id: str
    relation: SpatialRelation
    object_id: str
    reference_frame: ReferenceFrame
    confidence: float = 1.0


@dataclass
class NavigationInstruction:
    """
    A navigation instruction.
    """
    action: str  # "turn", "go", "arrive"
    direction: Optional[str]
    distance: Optional[float]
    landmark: Optional[str]


@dataclass
class Route:
    """
    A navigation route.
    """
    locations: List[str]
    total_distance: float
    instructions: List[NavigationInstruction]
    mode: NavigationMode


# ============================================================================
# COGNITIVE MAP
# ============================================================================

class CognitiveMap:
    """
    Mental map representation.

    "Ba'el maps the world." — Ba'el
    """

    def __init__(self):
        """Initialize cognitive map."""
        self._locations: Dict[str, Location] = {}
        self._paths: Dict[str, Path] = {}
        self._regions: Dict[str, Region] = {}

        # Adjacency list for navigation
        self._adjacency: Dict[str, List[Tuple[str, float]]] = defaultdict(list)

        self._location_counter = 0
        self._path_counter = 0
        self._region_counter = 0
        self._lock = threading.RLock()

    def _generate_location_id(self) -> str:
        self._location_counter += 1
        return f"loc_{self._location_counter}"

    def _generate_path_id(self) -> str:
        self._path_counter += 1
        return f"path_{self._path_counter}"

    def _generate_region_id(self) -> str:
        self._region_counter += 1
        return f"region_{self._region_counter}"

    def add_location(
        self,
        name: str,
        x: float,
        y: float,
        z: float = 0.0,
        is_landmark: bool = False,
        properties: Dict[str, Any] = None
    ) -> Location:
        """Add location to map."""
        with self._lock:
            location = Location(
                id=self._generate_location_id(),
                name=name,
                position=Point(x, y, z),
                properties=properties or {},
                is_landmark=is_landmark
            )

            self._locations[location.id] = location
            return location

    def add_path(
        self,
        start_id: str,
        end_id: str,
        bidirectional: bool = True
    ) -> Optional[Path]:
        """Add path between locations."""
        with self._lock:
            if start_id not in self._locations or end_id not in self._locations:
                return None

            start = self._locations[start_id]
            end = self._locations[end_id]
            distance = start.position.distance_to(end.position)

            path = Path(
                id=self._generate_path_id(),
                start_id=start_id,
                end_id=end_id,
                distance=distance
            )

            self._paths[path.id] = path
            self._adjacency[start_id].append((end_id, distance))

            if bidirectional:
                self._adjacency[end_id].append((start_id, distance))

            return path

    def add_region(
        self,
        name: str,
        boundary: List[Tuple[float, float]]
    ) -> Region:
        """Add region to map."""
        with self._lock:
            points = [Point(x, y) for x, y in boundary]

            # Compute center
            cx = sum(p.x for p in points) / len(points)
            cy = sum(p.y for p in points) / len(points)

            region = Region(
                id=self._generate_region_id(),
                name=name,
                boundary=points,
                center=Point(cx, cy)
            )

            self._regions[region.id] = region
            return region

    def get_location(self, location_id: str) -> Optional[Location]:
        """Get location by ID."""
        return self._locations.get(location_id)

    def find_location(self, name: str) -> Optional[Location]:
        """Find location by name."""
        for loc in self._locations.values():
            if loc.name.lower() == name.lower():
                return loc
        return None

    def get_landmarks(self) -> List[Location]:
        """Get all landmarks."""
        return [loc for loc in self._locations.values() if loc.is_landmark]

    def get_nearest(
        self,
        point: Point,
        k: int = 1
    ) -> List[Location]:
        """Get k nearest locations to point."""
        distances = [
            (loc, point.distance_to(loc.position))
            for loc in self._locations.values()
        ]
        distances.sort(key=lambda x: x[1])
        return [loc for loc, _ in distances[:k]]

    def get_locations_in_region(
        self,
        region_id: str
    ) -> List[Location]:
        """Get locations within region."""
        region = self._regions.get(region_id)
        if not region:
            return []

        return [
            loc for loc in self._locations.values()
            if region.contains(loc.position)
        ]


# ============================================================================
# SPATIAL REASONER
# ============================================================================

class SpatialReasoner:
    """
    Reason about spatial relationships.

    "Ba'el understands space." — Ba'el
    """

    def __init__(self, cognitive_map: CognitiveMap):
        """Initialize reasoner."""
        self._map = cognitive_map
        self._lock = threading.RLock()

    def compute_relation(
        self,
        subject_id: str,
        object_id: str,
        reference_frame: ReferenceFrame = ReferenceFrame.ALLOCENTRIC
    ) -> Optional[SpatialRelationship]:
        """Compute spatial relation between locations."""
        with self._lock:
            subject = self._map.get_location(subject_id)
            obj = self._map.get_location(object_id)

            if not subject or not obj:
                return None

            dx = obj.position.x - subject.position.x
            dy = obj.position.y - subject.position.y
            dz = obj.position.z - subject.position.z

            distance = subject.position.distance_to(obj.position)

            # Determine relation
            if reference_frame == ReferenceFrame.ALLOCENTRIC:
                # Use cardinal directions
                if abs(dx) > abs(dy):
                    if dx > 0:
                        relation = SpatialRelation.RIGHT  # East
                    else:
                        relation = SpatialRelation.LEFT   # West
                else:
                    if dy > 0:
                        relation = SpatialRelation.IN_FRONT  # North
                    else:
                        relation = SpatialRelation.BEHIND    # South
            else:
                # Egocentric (simplified)
                if abs(dx) > abs(dy):
                    relation = SpatialRelation.RIGHT if dx > 0 else SpatialRelation.LEFT
                else:
                    relation = SpatialRelation.IN_FRONT if dy > 0 else SpatialRelation.BEHIND

            # Check vertical
            if abs(dz) > max(abs(dx), abs(dy)) * 0.5:
                relation = SpatialRelation.ABOVE if dz > 0 else SpatialRelation.BELOW

            # Check proximity
            if distance < 1.0:
                relation = SpatialRelation.NEAR
            elif distance < 0.1:
                relation = SpatialRelation.ADJACENT

            return SpatialRelationship(
                subject_id=subject_id,
                relation=relation,
                object_id=object_id,
                reference_frame=reference_frame,
                confidence=1.0
            )

    def find_by_relation(
        self,
        reference_id: str,
        relation: SpatialRelation
    ) -> List[Location]:
        """Find locations with given relation to reference."""
        with self._lock:
            results = []

            for loc_id in self._map._locations:
                if loc_id == reference_id:
                    continue

                rel = self.compute_relation(reference_id, loc_id)
                if rel and rel.relation == relation:
                    results.append(self._map.get_location(loc_id))

            return results

    def describe_location(
        self,
        location_id: str
    ) -> str:
        """Generate description of location."""
        with self._lock:
            location = self._map.get_location(location_id)
            if not location:
                return ""

            parts = [f"{location.name}"]

            # Find nearby landmarks
            landmarks = self._map.get_landmarks()
            nearby = []

            for lm in landmarks:
                if lm.id == location_id:
                    continue

                dist = location.position.distance_to(lm.position)
                if dist < 100:  # Nearby threshold
                    rel = self.compute_relation(location_id, lm.id)
                    if rel:
                        nearby.append((lm, rel.relation, dist))

            if nearby:
                nearby.sort(key=lambda x: x[2])
                lm, rel, _ = nearby[0]
                parts.append(f"{rel.name.lower().replace('_', ' ')} of {lm.name}")

            return ", ".join(parts)


# ============================================================================
# NAVIGATOR
# ============================================================================

class Navigator:
    """
    Pathfinding and navigation.

    "Ba'el finds the way." — Ba'el
    """

    def __init__(self, cognitive_map: CognitiveMap):
        """Initialize navigator."""
        self._map = cognitive_map
        self._lock = threading.RLock()

    def find_path(
        self,
        start_id: str,
        end_id: str
    ) -> Optional[List[str]]:
        """Find shortest path using Dijkstra."""
        with self._lock:
            if start_id not in self._map._locations or end_id not in self._map._locations:
                return None

            distances = {start_id: 0.0}
            previous = {}
            heap = [(0.0, start_id)]
            visited = set()

            while heap:
                dist, current = heapq.heappop(heap)

                if current in visited:
                    continue

                visited.add(current)

                if current == end_id:
                    # Reconstruct path
                    path = []
                    node = end_id
                    while node:
                        path.append(node)
                        node = previous.get(node)
                    return list(reversed(path))

                for neighbor, edge_dist in self._map._adjacency.get(current, []):
                    if neighbor in visited:
                        continue

                    new_dist = dist + edge_dist

                    if neighbor not in distances or new_dist < distances[neighbor]:
                        distances[neighbor] = new_dist
                        previous[neighbor] = current
                        heapq.heappush(heap, (new_dist, neighbor))

            return None

    def generate_route(
        self,
        start_id: str,
        end_id: str,
        mode: NavigationMode = NavigationMode.ROUTE
    ) -> Optional[Route]:
        """Generate navigation route."""
        with self._lock:
            path = self.find_path(start_id, end_id)

            if not path:
                return None

            instructions = []
            total_distance = 0.0

            for i in range(len(path) - 1):
                curr = self._map.get_location(path[i])
                next_loc = self._map.get_location(path[i + 1])

                if not curr or not next_loc:
                    continue

                dist = curr.position.distance_to(next_loc.position)
                total_distance += dist

                # Compute direction
                dx = next_loc.position.x - curr.position.x
                dy = next_loc.position.y - curr.position.y

                angle = math.atan2(dy, dx)

                if angle > -math.pi/4 and angle <= math.pi/4:
                    direction = "east"
                elif angle > math.pi/4 and angle <= 3*math.pi/4:
                    direction = "north"
                elif angle > -3*math.pi/4 and angle <= -math.pi/4:
                    direction = "south"
                else:
                    direction = "west"

                # Find landmark
                landmark = None
                if next_loc.is_landmark:
                    landmark = next_loc.name

                if mode == NavigationMode.ROUTE:
                    instructions.append(NavigationInstruction(
                        action="go",
                        direction=direction,
                        distance=dist,
                        landmark=landmark
                    ))
                elif mode == NavigationMode.LANDMARK:
                    if landmark:
                        instructions.append(NavigationInstruction(
                            action="go",
                            direction=None,
                            distance=None,
                            landmark=f"toward {landmark}"
                        ))

            # Final arrival
            end_loc = self._map.get_location(end_id)
            instructions.append(NavigationInstruction(
                action="arrive",
                direction=None,
                distance=None,
                landmark=end_loc.name if end_loc else None
            ))

            return Route(
                locations=path,
                total_distance=total_distance,
                instructions=instructions,
                mode=mode
            )


# ============================================================================
# SPATIAL COGNITION ENGINE
# ============================================================================

class SpatialCognitionEngine:
    """
    Complete spatial cognition engine.

    "Ba'el's spatial intelligence." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._map = CognitiveMap()
        self._reasoner = SpatialReasoner(self._map)
        self._navigator = Navigator(self._map)

        self._current_location: Optional[str] = None
        self._lock = threading.RLock()

    # Map building

    def add_location(
        self,
        name: str,
        x: float,
        y: float,
        is_landmark: bool = False
    ) -> Location:
        """Add location."""
        return self._map.add_location(name, x, y, is_landmark=is_landmark)

    def add_path(
        self,
        start_id: str,
        end_id: str
    ) -> Optional[Path]:
        """Add path."""
        return self._map.add_path(start_id, end_id)

    def add_region(
        self,
        name: str,
        boundary: List[Tuple[float, float]]
    ) -> Region:
        """Add region."""
        return self._map.add_region(name, boundary)

    # Location queries

    def get_location(self, location_id: str) -> Optional[Location]:
        """Get location."""
        return self._map.get_location(location_id)

    def find_location(self, name: str) -> Optional[Location]:
        """Find location by name."""
        return self._map.find_location(name)

    def get_nearest(self, x: float, y: float, k: int = 1) -> List[Location]:
        """Get nearest locations."""
        return self._map.get_nearest(Point(x, y), k)

    def get_landmarks(self) -> List[Location]:
        """Get all landmarks."""
        return self._map.get_landmarks()

    # Spatial reasoning

    def compute_relation(
        self,
        subject_id: str,
        object_id: str
    ) -> Optional[SpatialRelationship]:
        """Compute spatial relation."""
        return self._reasoner.compute_relation(subject_id, object_id)

    def find_by_relation(
        self,
        reference_id: str,
        relation: SpatialRelation
    ) -> List[Location]:
        """Find by relation."""
        return self._reasoner.find_by_relation(reference_id, relation)

    def describe_location(self, location_id: str) -> str:
        """Describe location."""
        return self._reasoner.describe_location(location_id)

    # Navigation

    def set_current_location(self, location_id: str) -> None:
        """Set current location."""
        self._current_location = location_id

    def find_path(
        self,
        start_id: str,
        end_id: str
    ) -> Optional[List[str]]:
        """Find path."""
        return self._navigator.find_path(start_id, end_id)

    def navigate_to(
        self,
        destination_id: str,
        mode: NavigationMode = NavigationMode.ROUTE
    ) -> Optional[Route]:
        """Navigate from current location."""
        if not self._current_location:
            return None
        return self._navigator.generate_route(
            self._current_location, destination_id, mode
        )

    def generate_route(
        self,
        start_id: str,
        end_id: str,
        mode: NavigationMode = NavigationMode.ROUTE
    ) -> Optional[Route]:
        """Generate route."""
        return self._navigator.generate_route(start_id, end_id, mode)

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'locations': len(self._map._locations),
            'paths': len(self._map._paths),
            'regions': len(self._map._regions),
            'current_location': self._current_location
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_spatial_cognition_engine() -> SpatialCognitionEngine:
    """Create spatial cognition engine."""
    return SpatialCognitionEngine()


def compute_distance(
    x1: float, y1: float,
    x2: float, y2: float
) -> float:
    """Compute distance between points."""
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
