"""
BAEL Geo Engine
================

Geographic operations and location services.

"Ba'el sees all corners of the earth." — Ba'el
"""

from .geo_engine import (
    # Enums
    DistanceUnit,
    CoordinateSystem,

    # Data structures
    Coordinate,
    BoundingBox,
    GeoPoint,
    GeoPolygon,
    GeoCircle,
    Address,
    GeoConfig,

    # Engine
    GeoEngine,

    # Instance
    geo_engine,
)

__all__ = [
    # Enums
    "DistanceUnit",
    "CoordinateSystem",

    # Data structures
    "Coordinate",
    "BoundingBox",
    "GeoPoint",
    "GeoPolygon",
    "GeoCircle",
    "Address",
    "GeoConfig",

    # Engine
    "GeoEngine",

    # Instance
    "geo_engine",
]
