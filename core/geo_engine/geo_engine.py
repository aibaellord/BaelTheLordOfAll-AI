"""
BAEL Geo Engine
================

Geographic operations, geocoding, and spatial calculations.

"Ba'el's domain spans all coordinates of existence." — Ba'el
"""

import asyncio
import logging
import math
import uuid
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("BAEL.Geo")

# Earth's radius in kilometers
EARTH_RADIUS_KM = 6371.0
EARTH_RADIUS_MI = 3958.8


# ============================================================================
# ENUMS
# ============================================================================

class DistanceUnit(Enum):
    """Distance units."""
    METERS = "meters"
    KILOMETERS = "kilometers"
    MILES = "miles"
    FEET = "feet"
    NAUTICAL_MILES = "nautical_miles"


class CoordinateSystem(Enum):
    """Coordinate systems."""
    WGS84 = "wgs84"  # GPS standard
    MERCATOR = "mercator"
    UTM = "utm"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Coordinate:
    """A geographic coordinate."""
    latitude: float
    longitude: float
    altitude: Optional[float] = None

    def __post_init__(self):
        """Validate coordinates."""
        if not -90 <= self.latitude <= 90:
            raise ValueError(f"Invalid latitude: {self.latitude}")
        if not -180 <= self.longitude <= 180:
            raise ValueError(f"Invalid longitude: {self.longitude}")

    def to_tuple(self) -> Tuple[float, float]:
        """Convert to tuple."""
        return (self.latitude, self.longitude)

    def to_radians(self) -> Tuple[float, float]:
        """Convert to radians."""
        return (math.radians(self.latitude), math.radians(self.longitude))

    @classmethod
    def from_tuple(cls, coords: Tuple[float, float]) -> 'Coordinate':
        """Create from tuple."""
        return cls(latitude=coords[0], longitude=coords[1])


@dataclass
class BoundingBox:
    """A geographic bounding box."""
    min_lat: float
    min_lon: float
    max_lat: float
    max_lon: float

    @property
    def southwest(self) -> Coordinate:
        """Get southwest corner."""
        return Coordinate(self.min_lat, self.min_lon)

    @property
    def northeast(self) -> Coordinate:
        """Get northeast corner."""
        return Coordinate(self.max_lat, self.max_lon)

    @property
    def center(self) -> Coordinate:
        """Get center point."""
        return Coordinate(
            (self.min_lat + self.max_lat) / 2,
            (self.min_lon + self.max_lon) / 2
        )

    def contains(self, coord: Coordinate) -> bool:
        """Check if coordinate is within bounds."""
        return (
            self.min_lat <= coord.latitude <= self.max_lat and
            self.min_lon <= coord.longitude <= self.max_lon
        )


@dataclass
class GeoPoint:
    """A named geographic point."""
    id: str
    name: str
    coordinate: Coordinate
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GeoPolygon:
    """A geographic polygon."""
    id: str
    name: str
    vertices: List[Coordinate]
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def bounding_box(self) -> BoundingBox:
        """Get bounding box."""
        lats = [v.latitude for v in self.vertices]
        lons = [v.longitude for v in self.vertices]
        return BoundingBox(
            min_lat=min(lats),
            min_lon=min(lons),
            max_lat=max(lats),
            max_lon=max(lons)
        )

    def contains(self, point: Coordinate) -> bool:
        """Check if point is inside polygon using ray casting."""
        n = len(self.vertices)
        inside = False

        j = n - 1
        for i in range(n):
            xi, yi = self.vertices[i].longitude, self.vertices[i].latitude
            xj, yj = self.vertices[j].longitude, self.vertices[j].latitude

            if ((yi > point.latitude) != (yj > point.latitude) and
                point.longitude < (xj - xi) * (point.latitude - yi) / (yj - yi) + xi):
                inside = not inside

            j = i

        return inside


@dataclass
class GeoCircle:
    """A geographic circle."""
    center: Coordinate
    radius: float  # In kilometers

    def contains(self, point: Coordinate) -> bool:
        """Check if point is inside circle."""
        distance = haversine_distance(self.center, point)
        return distance <= self.radius


@dataclass
class Address:
    """A postal address."""
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None

    # Geocoded
    coordinate: Optional[Coordinate] = None
    formatted: Optional[str] = None

    def to_string(self) -> str:
        """Convert to string."""
        parts = [
            self.street,
            self.city,
            self.state,
            self.postal_code,
            self.country
        ]
        return ", ".join(p for p in parts if p)


@dataclass
class GeoConfig:
    """Geo engine configuration."""
    default_unit: DistanceUnit = DistanceUnit.KILOMETERS
    geocoding_provider: str = "mock"
    api_key: Optional[str] = None


# ============================================================================
# DISTANCE CALCULATIONS
# ============================================================================

def haversine_distance(
    coord1: Coordinate,
    coord2: Coordinate,
    unit: DistanceUnit = DistanceUnit.KILOMETERS
) -> float:
    """
    Calculate the great-circle distance between two points using Haversine formula.

    Args:
        coord1: First coordinate
        coord2: Second coordinate
        unit: Distance unit

    Returns:
        Distance in specified unit
    """
    lat1, lon1 = coord1.to_radians()
    lat2, lon2 = coord2.to_radians()

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    # Distance in kilometers
    distance_km = EARTH_RADIUS_KM * c

    # Convert to requested unit
    return convert_distance(distance_km, DistanceUnit.KILOMETERS, unit)


def vincenty_distance(
    coord1: Coordinate,
    coord2: Coordinate,
    unit: DistanceUnit = DistanceUnit.KILOMETERS
) -> float:
    """
    Calculate distance using Vincenty formula (more accurate for long distances).

    Simplified implementation using WGS-84 ellipsoid.
    """
    # For simplicity, use haversine with a correction factor
    # Full Vincenty requires iterative solution
    distance = haversine_distance(coord1, coord2, unit)

    # Apply approximate correction for ellipsoid
    return distance * 1.0003  # Rough correction factor


def convert_distance(
    distance: float,
    from_unit: DistanceUnit,
    to_unit: DistanceUnit
) -> float:
    """Convert distance between units."""
    # Convert to meters first
    to_meters = {
        DistanceUnit.METERS: 1.0,
        DistanceUnit.KILOMETERS: 1000.0,
        DistanceUnit.MILES: 1609.344,
        DistanceUnit.FEET: 0.3048,
        DistanceUnit.NAUTICAL_MILES: 1852.0
    }

    meters = distance * to_meters[from_unit]
    return meters / to_meters[to_unit]


def bearing(coord1: Coordinate, coord2: Coordinate) -> float:
    """
    Calculate initial bearing from coord1 to coord2.

    Returns:
        Bearing in degrees (0-360)
    """
    lat1, lon1 = coord1.to_radians()
    lat2, lon2 = coord2.to_radians()

    dlon = lon2 - lon1

    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)

    initial_bearing = math.atan2(x, y)

    # Convert to degrees
    bearing_degrees = math.degrees(initial_bearing)

    # Normalize to 0-360
    return (bearing_degrees + 360) % 360


def destination_point(
    start: Coordinate,
    bearing_degrees: float,
    distance_km: float
) -> Coordinate:
    """
    Calculate destination point given start, bearing, and distance.

    Args:
        start: Starting coordinate
        bearing_degrees: Bearing in degrees
        distance_km: Distance in kilometers

    Returns:
        Destination coordinate
    """
    lat1, lon1 = start.to_radians()
    bearing_rad = math.radians(bearing_degrees)

    angular_distance = distance_km / EARTH_RADIUS_KM

    lat2 = math.asin(
        math.sin(lat1) * math.cos(angular_distance) +
        math.cos(lat1) * math.sin(angular_distance) * math.cos(bearing_rad)
    )

    lon2 = lon1 + math.atan2(
        math.sin(bearing_rad) * math.sin(angular_distance) * math.cos(lat1),
        math.cos(angular_distance) - math.sin(lat1) * math.sin(lat2)
    )

    return Coordinate(
        latitude=math.degrees(lat2),
        longitude=math.degrees(lon2)
    )


def midpoint(coord1: Coordinate, coord2: Coordinate) -> Coordinate:
    """Calculate midpoint between two coordinates."""
    lat1, lon1 = coord1.to_radians()
    lat2, lon2 = coord2.to_radians()

    dlon = lon2 - lon1

    bx = math.cos(lat2) * math.cos(dlon)
    by = math.cos(lat2) * math.sin(dlon)

    lat3 = math.atan2(
        math.sin(lat1) + math.sin(lat2),
        math.sqrt((math.cos(lat1) + bx) ** 2 + by ** 2)
    )

    lon3 = lon1 + math.atan2(by, math.cos(lat1) + bx)

    return Coordinate(
        latitude=math.degrees(lat3),
        longitude=math.degrees(lon3)
    )


# ============================================================================
# MAIN GEO ENGINE
# ============================================================================

class GeoEngine:
    """
    Main geo engine.

    Features:
    - Distance calculations
    - Geocoding
    - Spatial queries
    - Geofencing

    "Ba'el's reach extends to all coordinates." — Ba'el
    """

    def __init__(self, config: Optional[GeoConfig] = None):
        """Initialize geo engine."""
        self.config = config or GeoConfig()

        # Storage
        self._points: Dict[str, GeoPoint] = {}
        self._polygons: Dict[str, GeoPolygon] = {}
        self._geofences: Dict[str, GeoCircle] = {}

        # Mock geocoding data
        self._mock_geocoding: Dict[str, Coordinate] = {
            "new york": Coordinate(40.7128, -74.0060),
            "los angeles": Coordinate(34.0522, -118.2437),
            "london": Coordinate(51.5074, -0.1278),
            "paris": Coordinate(48.8566, 2.3522),
            "tokyo": Coordinate(35.6762, 139.6503),
            "sydney": Coordinate(-33.8688, 151.2093),
        }

        self._lock = threading.RLock()

        logger.info("GeoEngine initialized")

    # ========================================================================
    # DISTANCE
    # ========================================================================

    def distance(
        self,
        coord1: Union[Coordinate, Tuple[float, float]],
        coord2: Union[Coordinate, Tuple[float, float]],
        unit: Optional[DistanceUnit] = None
    ) -> float:
        """Calculate distance between two coordinates."""
        if isinstance(coord1, tuple):
            coord1 = Coordinate.from_tuple(coord1)
        if isinstance(coord2, tuple):
            coord2 = Coordinate.from_tuple(coord2)

        return haversine_distance(
            coord1, coord2,
            unit or self.config.default_unit
        )

    def bearing(
        self,
        coord1: Union[Coordinate, Tuple[float, float]],
        coord2: Union[Coordinate, Tuple[float, float]]
    ) -> float:
        """Calculate bearing between two coordinates."""
        if isinstance(coord1, tuple):
            coord1 = Coordinate.from_tuple(coord1)
        if isinstance(coord2, tuple):
            coord2 = Coordinate.from_tuple(coord2)

        return bearing(coord1, coord2)

    def destination(
        self,
        start: Union[Coordinate, Tuple[float, float]],
        bearing_degrees: float,
        distance: float,
        unit: Optional[DistanceUnit] = None
    ) -> Coordinate:
        """Calculate destination point."""
        if isinstance(start, tuple):
            start = Coordinate.from_tuple(start)

        # Convert to km
        unit = unit or self.config.default_unit
        distance_km = convert_distance(distance, unit, DistanceUnit.KILOMETERS)

        return destination_point(start, bearing_degrees, distance_km)

    def midpoint(
        self,
        coord1: Union[Coordinate, Tuple[float, float]],
        coord2: Union[Coordinate, Tuple[float, float]]
    ) -> Coordinate:
        """Calculate midpoint."""
        if isinstance(coord1, tuple):
            coord1 = Coordinate.from_tuple(coord1)
        if isinstance(coord2, tuple):
            coord2 = Coordinate.from_tuple(coord2)

        return midpoint(coord1, coord2)

    # ========================================================================
    # GEOCODING
    # ========================================================================

    async def geocode(self, address: Union[str, Address]) -> Optional[Coordinate]:
        """
        Geocode an address to coordinates.

        Args:
            address: Address string or object

        Returns:
            Coordinate or None
        """
        if isinstance(address, Address):
            query = address.to_string().lower()
        else:
            query = address.lower()

        # Mock geocoding
        for city, coord in self._mock_geocoding.items():
            if city in query:
                return coord

        return None

    async def reverse_geocode(self, coord: Coordinate) -> Optional[Address]:
        """
        Reverse geocode coordinates to address.

        Args:
            coord: Coordinate

        Returns:
            Address or None
        """
        # Find nearest mock city
        nearest = None
        nearest_dist = float('inf')

        for city, city_coord in self._mock_geocoding.items():
            dist = self.distance(coord, city_coord)
            if dist < nearest_dist:
                nearest = city
                nearest_dist = dist

        if nearest and nearest_dist < 100:  # Within 100 km
            return Address(
                city=nearest.title(),
                coordinate=self._mock_geocoding[nearest]
            )

        return None

    # ========================================================================
    # POINTS
    # ========================================================================

    def add_point(
        self,
        name: str,
        coordinate: Coordinate,
        **metadata
    ) -> GeoPoint:
        """Add a named point."""
        point = GeoPoint(
            id=str(uuid.uuid4()),
            name=name,
            coordinate=coordinate,
            metadata=metadata
        )

        with self._lock:
            self._points[point.id] = point

        return point

    def find_nearest(
        self,
        coord: Coordinate,
        limit: int = 10,
        max_distance: Optional[float] = None
    ) -> List[Tuple[GeoPoint, float]]:
        """Find nearest points to a coordinate."""
        results = []

        for point in self._points.values():
            dist = self.distance(coord, point.coordinate)

            if max_distance is None or dist <= max_distance:
                results.append((point, dist))

        results.sort(key=lambda x: x[1])

        return results[:limit]

    def find_within_radius(
        self,
        center: Coordinate,
        radius: float,
        unit: Optional[DistanceUnit] = None
    ) -> List[GeoPoint]:
        """Find all points within radius."""
        unit = unit or self.config.default_unit
        radius_km = convert_distance(radius, unit, DistanceUnit.KILOMETERS)

        results = []

        for point in self._points.values():
            dist = self.distance(center, point.coordinate, DistanceUnit.KILOMETERS)
            if dist <= radius_km:
                results.append(point)

        return results

    # ========================================================================
    # POLYGONS
    # ========================================================================

    def add_polygon(
        self,
        name: str,
        vertices: List[Coordinate],
        **metadata
    ) -> GeoPolygon:
        """Add a polygon."""
        polygon = GeoPolygon(
            id=str(uuid.uuid4()),
            name=name,
            vertices=vertices,
            metadata=metadata
        )

        with self._lock:
            self._polygons[polygon.id] = polygon

        return polygon

    def point_in_polygon(
        self,
        point: Coordinate,
        polygon_id: str
    ) -> bool:
        """Check if point is in polygon."""
        polygon = self._polygons.get(polygon_id)

        if not polygon:
            return False

        return polygon.contains(point)

    def find_containing_polygons(self, point: Coordinate) -> List[GeoPolygon]:
        """Find all polygons containing a point."""
        return [
            p for p in self._polygons.values()
            if p.contains(point)
        ]

    # ========================================================================
    # GEOFENCING
    # ========================================================================

    def create_geofence(
        self,
        name: str,
        center: Coordinate,
        radius_km: float
    ) -> str:
        """Create a circular geofence."""
        fence_id = str(uuid.uuid4())

        with self._lock:
            self._geofences[fence_id] = GeoCircle(center, radius_km)

        return fence_id

    def check_geofence(
        self,
        fence_id: str,
        point: Coordinate
    ) -> bool:
        """Check if point is inside geofence."""
        fence = self._geofences.get(fence_id)

        if not fence:
            return False

        return fence.contains(point)

    def check_all_geofences(
        self,
        point: Coordinate
    ) -> List[str]:
        """Get all geofences containing a point."""
        return [
            fence_id
            for fence_id, fence in self._geofences.items()
            if fence.contains(point)
        ]

    # ========================================================================
    # BOUNDING BOX
    # ========================================================================

    def create_bounding_box(
        self,
        center: Coordinate,
        radius_km: float
    ) -> BoundingBox:
        """Create a bounding box around a center point."""
        # Calculate corners
        north = destination_point(center, 0, radius_km)
        south = destination_point(center, 180, radius_km)
        east = destination_point(center, 90, radius_km)
        west = destination_point(center, 270, radius_km)

        return BoundingBox(
            min_lat=south.latitude,
            max_lat=north.latitude,
            min_lon=west.longitude,
            max_lon=east.longitude
        )

    # ========================================================================
    # STATUS
    # ========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        return {
            'points': len(self._points),
            'polygons': len(self._polygons),
            'geofences': len(self._geofences),
            'default_unit': self.config.default_unit.value
        }


# ============================================================================
# CONVENIENCE INSTANCE
# ============================================================================

geo_engine = GeoEngine()
