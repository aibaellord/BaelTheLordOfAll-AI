"""
BAEL API Versioning Engine
==========================

API versioning and deprecation management.

"Ba'el evolves APIs while honoring the past." — Ba'el
"""

from .api_versioning_engine import (
    VersionScheme,
    VersionStatus,
    APIVersion,
    VersionConfig,
    APIVersionManager,
    version_manager,
    route_version,
    deprecate_version
)

__all__ = [
    'VersionScheme',
    'VersionStatus',
    'APIVersion',
    'VersionConfig',
    'APIVersionManager',
    'version_manager',
    'route_version',
    'deprecate_version'
]
