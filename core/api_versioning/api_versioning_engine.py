"""
BAEL API Versioning Engine Implementation
==========================================

API versioning and deprecation management.

"Ba'el evolves APIs while honoring the past." — Ba'el
"""

import asyncio
import functools
import logging
import re
import threading
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, TypeVar
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("BAEL.APIVersioning")

T = TypeVar('T')


# ============================================================================
# ENUMS
# ============================================================================

class VersionScheme(Enum):
    """API versioning schemes."""
    URL_PATH = "url_path"       # /v1/resource
    HEADER = "header"           # X-API-Version: 1
    QUERY_PARAM = "query_param" # ?version=1
    ACCEPT_HEADER = "accept"    # Accept: application/vnd.api.v1+json
    SEMANTIC = "semantic"       # Major.Minor.Patch


class VersionStatus(Enum):
    """API version status."""
    CURRENT = "current"         # Active, recommended
    SUPPORTED = "supported"     # Active, not recommended
    DEPRECATED = "deprecated"   # Active, will be removed
    SUNSET = "sunset"           # Removed
    PREVIEW = "preview"         # Beta, may change


class ChangeType(Enum):
    """Types of API changes."""
    BREAKING = "breaking"       # Not backward compatible
    FEATURE = "feature"         # New functionality
    FIX = "fix"                 # Bug fix
    DEPRECATION = "deprecation" # Marking deprecation


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class APIVersion:
    """An API version."""
    version: str
    status: VersionStatus = VersionStatus.CURRENT

    # Timing
    released_at: Optional[datetime] = None
    deprecated_at: Optional[datetime] = None
    sunset_at: Optional[datetime] = None

    # Changes
    changes: List[Dict[str, Any]] = field(default_factory=list)

    # Routing
    handlers: Dict[str, Callable] = field(default_factory=dict)

    # Metadata
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        """Check if version is active."""
        return self.status not in (VersionStatus.SUNSET,)

    @property
    def is_deprecated(self) -> bool:
        """Check if version is deprecated."""
        return self.status == VersionStatus.DEPRECATED

    def to_dict(self) -> Dict[str, Any]:
        return {
            'version': self.version,
            'status': self.status.value,
            'released_at': self.released_at.isoformat() if self.released_at else None,
            'deprecated_at': self.deprecated_at.isoformat() if self.deprecated_at else None,
            'sunset_at': self.sunset_at.isoformat() if self.sunset_at else None,
            'changes': self.changes,
            'description': self.description,
            'metadata': self.metadata
        }


@dataclass
class VersionConfig:
    """Versioning configuration."""
    scheme: VersionScheme = VersionScheme.URL_PATH
    default_version: str = "v1"
    header_name: str = "X-API-Version"
    query_param_name: str = "version"
    deprecation_warning_header: str = "X-API-Deprecated"
    sunset_header: str = "Sunset"


# ============================================================================
# VERSION MANAGER
# ============================================================================

class APIVersionManager:
    """
    API version manager.

    Features:
    - Multiple versioning schemes
    - Version lifecycle management
    - Deprecation warnings
    - Sunset scheduling
    - Handler routing

    "Ba'el manages the evolution of all interfaces." — Ba'el
    """

    def __init__(self, config: Optional[VersionConfig] = None):
        """Initialize version manager."""
        self.config = config or VersionConfig()

        # Versions: version_string -> APIVersion
        self._versions: Dict[str, APIVersion] = {}

        # Default handlers
        self._default_handlers: Dict[str, Callable] = {}

        # Thread safety
        self._lock = threading.RLock()

        # Stats
        self._stats = {
            'requests': {},  # version -> count
            'deprecated_warnings': 0
        }

        logger.info("API Version Manager initialized")

    # ========================================================================
    # VERSION MANAGEMENT
    # ========================================================================

    def register_version(
        self,
        version: str,
        status: VersionStatus = VersionStatus.CURRENT,
        released_at: Optional[datetime] = None,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> APIVersion:
        """
        Register an API version.

        Args:
            version: Version string
            status: Version status
            released_at: Release date
            description: Version description
            metadata: Additional metadata

        Returns:
            APIVersion
        """
        api_version = APIVersion(
            version=version,
            status=status,
            released_at=released_at or datetime.now(),
            description=description,
            metadata=metadata or {}
        )

        with self._lock:
            self._versions[version] = api_version
            self._stats['requests'][version] = 0

        logger.info(f"API version registered: {version}")

        return api_version

    def deprecate_version(
        self,
        version: str,
        sunset_at: Optional[datetime] = None,
        sunset_days: Optional[int] = None,
        reason: str = ""
    ) -> bool:
        """
        Deprecate an API version.

        Args:
            version: Version to deprecate
            sunset_at: When version will be removed
            sunset_days: Days until sunset
            reason: Deprecation reason

        Returns:
            True if deprecated
        """
        with self._lock:
            api_version = self._versions.get(version)

            if not api_version:
                return False

            api_version.status = VersionStatus.DEPRECATED
            api_version.deprecated_at = datetime.now()

            if sunset_at:
                api_version.sunset_at = sunset_at
            elif sunset_days:
                api_version.sunset_at = datetime.now() + timedelta(days=sunset_days)

            api_version.changes.append({
                'type': ChangeType.DEPRECATION.value,
                'reason': reason,
                'date': datetime.now().isoformat()
            })

        logger.warning(f"API version deprecated: {version}")

        return True

    def sunset_version(self, version: str) -> bool:
        """Mark version as sunset (removed)."""
        with self._lock:
            api_version = self._versions.get(version)

            if not api_version:
                return False

            api_version.status = VersionStatus.SUNSET

        logger.warning(f"API version sunset: {version}")

        return True

    # ========================================================================
    # HANDLER REGISTRATION
    # ========================================================================

    def register_handler(
        self,
        version: str,
        route: str,
        handler: Callable
    ) -> None:
        """
        Register a route handler for a version.

        Args:
            version: API version
            route: Route path
            handler: Handler function
        """
        with self._lock:
            api_version = self._versions.get(version)

            if not api_version:
                # Create version if doesn't exist
                api_version = self.register_version(version)

            api_version.handlers[route] = handler

    def register_default_handler(
        self,
        route: str,
        handler: Callable
    ) -> None:
        """Register a default handler for unversioned routes."""
        self._default_handlers[route] = handler

    # ========================================================================
    # VERSION RESOLUTION
    # ========================================================================

    def resolve_version(
        self,
        request: Dict[str, Any]
    ) -> Optional[str]:
        """
        Resolve version from request.

        Args:
            request: Request dict with path, headers, params

        Returns:
            Version string or None
        """
        scheme = self.config.scheme

        if scheme == VersionScheme.URL_PATH:
            path = request.get('path', '')
            match = re.match(r'/v(\d+)', path)
            if match:
                return f"v{match.group(1)}"

        elif scheme == VersionScheme.HEADER:
            headers = request.get('headers', {})
            return headers.get(self.config.header_name)

        elif scheme == VersionScheme.QUERY_PARAM:
            params = request.get('params', {})
            return params.get(self.config.query_param_name)

        elif scheme == VersionScheme.ACCEPT_HEADER:
            accept = request.get('headers', {}).get('Accept', '')
            match = re.search(r'v(\d+)', accept)
            if match:
                return f"v{match.group(1)}"

        elif scheme == VersionScheme.SEMANTIC:
            # Try multiple sources for semantic version
            version = request.get('headers', {}).get(self.config.header_name)
            if not version:
                version = request.get('params', {}).get(self.config.query_param_name)
            return version

        return self.config.default_version

    def get_handler(
        self,
        version: str,
        route: str
    ) -> Optional[Callable]:
        """
        Get handler for version and route.

        Args:
            version: API version
            route: Route path

        Returns:
            Handler function or None
        """
        with self._lock:
            api_version = self._versions.get(version)

            if api_version and api_version.is_active:
                handler = api_version.handlers.get(route)
                if handler:
                    return handler

            # Fall back to default
            return self._default_handlers.get(route)

    # ========================================================================
    # REQUEST HANDLING
    # ========================================================================

    async def handle_request(
        self,
        request: Dict[str, Any],
        route: str,
        *args,
        **kwargs
    ) -> Any:
        """
        Handle a versioned request.

        Args:
            request: Request dict
            route: Route path
            *args: Handler args
            **kwargs: Handler kwargs

        Returns:
            Handler result
        """
        # Resolve version
        version = self.resolve_version(request)

        if not version:
            version = self.config.default_version

        # Track stats
        with self._lock:
            if version in self._stats['requests']:
                self._stats['requests'][version] += 1

        # Get API version
        api_version = self._versions.get(version)

        # Check deprecation
        if api_version and api_version.is_deprecated:
            self._stats['deprecated_warnings'] += 1
            logger.warning(f"Deprecated API called: {version}")

        # Get handler
        handler = self.get_handler(version, route)

        if not handler:
            raise NotImplementedError(
                f"No handler for {route} in version {version}"
            )

        # Call handler
        if asyncio.iscoroutinefunction(handler):
            return await handler(*args, **kwargs)
        else:
            return handler(*args, **kwargs)

    def get_deprecation_headers(
        self,
        version: str
    ) -> Dict[str, str]:
        """Get deprecation warning headers."""
        headers = {}

        api_version = self._versions.get(version)

        if api_version and api_version.is_deprecated:
            headers[self.config.deprecation_warning_header] = "true"

            if api_version.sunset_at:
                headers[self.config.sunset_header] = (
                    api_version.sunset_at.isoformat()
                )

        return headers

    # ========================================================================
    # QUERIES
    # ========================================================================

    def get_version(self, version: str) -> Optional[APIVersion]:
        """Get a specific version."""
        return self._versions.get(version)

    def list_versions(
        self,
        status: Optional[VersionStatus] = None,
        only_active: bool = False
    ) -> List[APIVersion]:
        """List all versions."""
        with self._lock:
            versions = list(self._versions.values())

            if status:
                versions = [v for v in versions if v.status == status]

            if only_active:
                versions = [v for v in versions if v.is_active]

            return versions

    def get_current_version(self) -> Optional[APIVersion]:
        """Get the current (recommended) version."""
        current = [
            v for v in self._versions.values()
            if v.status == VersionStatus.CURRENT
        ]
        return current[0] if current else None

    # ========================================================================
    # CHANGELOG
    # ========================================================================

    def add_change(
        self,
        version: str,
        change_type: ChangeType,
        description: str,
        breaking: bool = False,
        affected: Optional[List[str]] = None
    ) -> bool:
        """Add a change to version changelog."""
        with self._lock:
            api_version = self._versions.get(version)

            if not api_version:
                return False

            api_version.changes.append({
                'type': change_type.value,
                'description': description,
                'breaking': breaking,
                'affected': affected or [],
                'date': datetime.now().isoformat()
            })

        return True

    def get_changelog(
        self,
        version: str
    ) -> List[Dict[str, Any]]:
        """Get changelog for a version."""
        api_version = self._versions.get(version)
        return api_version.changes if api_version else []

    # ========================================================================
    # STATS
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        with self._lock:
            total_requests = sum(self._stats['requests'].values())

        return {
            'versions': len(self._versions),
            'active_versions': sum(1 for v in self._versions.values() if v.is_active),
            'deprecated_versions': sum(1 for v in self._versions.values() if v.is_deprecated),
            'total_requests': total_requests,
            'requests_by_version': dict(self._stats['requests']),
            'deprecated_warnings': self._stats['deprecated_warnings']
        }


# ============================================================================
# DECORATOR
# ============================================================================

def versioned(
    versions: List[str],
    manager: Optional[APIVersionManager] = None
):
    """
    Decorator for versioned handlers.

    Args:
        versions: Versions this handler supports
        manager: Version manager to use
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            return func(*args, **kwargs)

        # Register with manager
        mgr = manager or version_manager
        route = func.__name__

        for version in versions:
            mgr.register_handler(version, route, func)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# ============================================================================
# CONVENIENCE
# ============================================================================

version_manager = APIVersionManager()


def route_version(version: str, route: str, handler: Callable) -> None:
    """Register a route handler."""
    version_manager.register_handler(version, route, handler)


def deprecate_version(version: str, **kwargs) -> bool:
    """Deprecate a version."""
    return version_manager.deprecate_version(version, **kwargs)
