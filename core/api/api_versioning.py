#!/usr/bin/env python3
"""
BAEL - API Versioning Manager
Comprehensive API version management and compatibility system.

Features:
- Version routing
- Deprecation management
- Breaking change detection
- Version negotiation
- Backward compatibility
- Migration support
- Version analytics
- Documentation generation
- Header-based versioning
- Path-based versioning
"""

import asyncio
import hashlib
import json
import logging
import re
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import (Any, Awaitable, Callable, Dict, Generic, List, Optional,
                    Set, Tuple, TypeVar, Union)

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class VersioningStrategy(Enum):
    """API versioning strategies."""
    PATH = "path"  # /v1/users
    HEADER = "header"  # X-API-Version: 1.0
    QUERY = "query"  # ?version=1.0
    ACCEPT = "accept"  # Accept: application/vnd.api.v1+json
    CUSTOM = "custom"


class VersionStatus(Enum):
    """API version status."""
    CURRENT = "current"
    SUPPORTED = "supported"
    DEPRECATED = "deprecated"
    SUNSET = "sunset"
    RETIRED = "retired"


class ChangeType(Enum):
    """API change types."""
    BREAKING = "breaking"
    NON_BREAKING = "non_breaking"
    DEPRECATION = "deprecation"
    ADDITION = "addition"
    REMOVAL = "removal"


class CompatibilityLevel(Enum):
    """Compatibility levels."""
    FULL = "full"
    BACKWARD = "backward"
    FORWARD = "forward"
    NONE = "none"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class SemanticVersion:
    """Semantic version."""
    major: int = 1
    minor: int = 0
    patch: int = 0

    @classmethod
    def parse(cls, version_str: str) -> 'SemanticVersion':
        """Parse version string."""
        match = re.match(r'v?(\d+)(?:\.(\d+))?(?:\.(\d+))?', version_str)

        if not match:
            return cls()

        major = int(match.group(1))
        minor = int(match.group(2) or 0)
        patch = int(match.group(3) or 0)

        return cls(major=major, minor=minor, patch=patch)

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def short(self) -> str:
        return f"v{self.major}"

    def __lt__(self, other: 'SemanticVersion') -> bool:
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SemanticVersion):
            return False
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)

    def is_compatible(self, other: 'SemanticVersion') -> bool:
        """Check if versions are backward compatible."""
        return self.major == other.major


@dataclass
class EndpointDefinition:
    """API endpoint definition."""
    endpoint_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    path: str = ""
    method: str = "GET"
    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    request_schema: Dict[str, Any] = field(default_factory=dict)
    response_schema: Dict[str, Any] = field(default_factory=dict)
    deprecated: bool = False
    deprecated_at: float = 0.0
    replacement: str = ""  # Replacement endpoint path


@dataclass
class APIVersion:
    """API version definition."""
    version: SemanticVersion = field(default_factory=SemanticVersion)
    status: VersionStatus = VersionStatus.CURRENT
    released_at: float = field(default_factory=time.time)
    deprecated_at: float = 0.0
    sunset_at: float = 0.0
    endpoints: Dict[str, EndpointDefinition] = field(default_factory=dict)
    changes: List['VersionChange'] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_deprecated(self) -> bool:
        return self.status in [VersionStatus.DEPRECATED, VersionStatus.SUNSET, VersionStatus.RETIRED]

    @property
    def is_active(self) -> bool:
        return self.status in [VersionStatus.CURRENT, VersionStatus.SUPPORTED]


@dataclass
class VersionChange:
    """Version change record."""
    change_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    change_type: ChangeType = ChangeType.NON_BREAKING
    description: str = ""
    affected_endpoints: List[str] = field(default_factory=list)
    migration_notes: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class VersionRequest:
    """Version request context."""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    path: str = ""
    method: str = "GET"
    headers: Dict[str, str] = field(default_factory=dict)
    query_params: Dict[str, str] = field(default_factory=dict)
    requested_version: Optional[str] = None


@dataclass
class VersionResponse:
    """Version response."""
    resolved_version: SemanticVersion = field(default_factory=SemanticVersion)
    endpoint: Optional[EndpointDefinition] = None
    deprecation_warning: str = ""
    migration_url: str = ""
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class MigrationPath:
    """Migration path between versions."""
    from_version: SemanticVersion = field(default_factory=SemanticVersion)
    to_version: SemanticVersion = field(default_factory=SemanticVersion)
    steps: List[str] = field(default_factory=list)
    breaking_changes: List[str] = field(default_factory=list)
    automated: bool = False


@dataclass
class VersionAnalytics:
    """Version usage analytics."""
    version: str = ""
    request_count: int = 0
    unique_clients: Set[str] = field(default_factory=set)
    endpoints_used: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    last_used: float = 0.0


# =============================================================================
# VERSION RESOLVER
# =============================================================================

class VersionResolver:
    """Resolves API version from request."""

    def __init__(self, strategy: VersioningStrategy = VersioningStrategy.PATH):
        self.strategy = strategy
        self.header_name = "X-API-Version"
        self.query_param = "version"
        self.path_prefix = "/api/v"
        self.accept_pattern = r'application/vnd\.api\.v(\d+)\+json'

    def resolve(self, request: VersionRequest) -> Optional[str]:
        """Resolve version from request."""
        if self.strategy == VersioningStrategy.PATH:
            return self._resolve_from_path(request.path)

        if self.strategy == VersioningStrategy.HEADER:
            return self._resolve_from_header(request.headers)

        if self.strategy == VersioningStrategy.QUERY:
            return self._resolve_from_query(request.query_params)

        if self.strategy == VersioningStrategy.ACCEPT:
            return self._resolve_from_accept(request.headers)

        return request.requested_version

    def _resolve_from_path(self, path: str) -> Optional[str]:
        """Resolve from path."""
        match = re.match(r'/(?:api/)?v(\d+(?:\.\d+)?(?:\.\d+)?)', path)

        if match:
            return match.group(1)

        return None

    def _resolve_from_header(self, headers: Dict[str, str]) -> Optional[str]:
        """Resolve from header."""
        return headers.get(self.header_name)

    def _resolve_from_query(self, params: Dict[str, str]) -> Optional[str]:
        """Resolve from query parameter."""
        return params.get(self.query_param)

    def _resolve_from_accept(self, headers: Dict[str, str]) -> Optional[str]:
        """Resolve from Accept header."""
        accept = headers.get("Accept", "")
        match = re.search(self.accept_pattern, accept)

        if match:
            return match.group(1)

        return None


# =============================================================================
# COMPATIBILITY CHECKER
# =============================================================================

class CompatibilityChecker:
    """Checks API compatibility."""

    def check_endpoint_compatibility(
        self,
        old: EndpointDefinition,
        new: EndpointDefinition
    ) -> Tuple[CompatibilityLevel, List[str]]:
        """Check endpoint compatibility."""
        issues = []

        # Check method change
        if old.method != new.method:
            issues.append(f"Method changed from {old.method} to {new.method}")
            return CompatibilityLevel.NONE, issues

        # Check path change
        if old.path != new.path:
            issues.append(f"Path changed from {old.path} to {new.path}")

        # Check parameter changes
        param_issues = self._check_parameters(old.parameters, new.parameters)
        issues.extend(param_issues)

        # Check response schema
        schema_issues = self._check_schema(old.response_schema, new.response_schema)
        issues.extend(schema_issues)

        if not issues:
            return CompatibilityLevel.FULL, []

        # Determine compatibility level
        breaking = any("removed" in i.lower() or "changed" in i.lower() for i in issues)

        if breaking:
            return CompatibilityLevel.NONE, issues

        return CompatibilityLevel.BACKWARD, issues

    def _check_parameters(
        self,
        old: Dict[str, Any],
        new: Dict[str, Any]
    ) -> List[str]:
        """Check parameter compatibility."""
        issues = []

        # Check for removed required parameters
        for name, info in old.items():
            if name not in new:
                issues.append(f"Parameter '{name}' removed")
            elif old[name].get("required") and not new[name].get("required"):
                pass  # Making optional is fine
            elif not old[name].get("required") and new[name].get("required"):
                issues.append(f"Parameter '{name}' now required")

        # Check for new required parameters
        for name, info in new.items():
            if name not in old and info.get("required"):
                issues.append(f"New required parameter '{name}'")

        return issues

    def _check_schema(
        self,
        old: Dict[str, Any],
        new: Dict[str, Any]
    ) -> List[str]:
        """Check schema compatibility."""
        issues = []

        old_props = old.get("properties", {})
        new_props = new.get("properties", {})

        # Check removed fields
        for name in old_props:
            if name not in new_props:
                issues.append(f"Response field '{name}' removed")

        return issues


# =============================================================================
# DEPRECATION MANAGER
# =============================================================================

class DeprecationManager:
    """Manages API deprecation."""

    def __init__(self):
        self._notifications: Dict[str, List[Callable]] = defaultdict(list)
        self._deprecation_warnings: Dict[str, str] = {}

    def deprecate_version(
        self,
        version: APIVersion,
        sunset_date: datetime,
        warning_message: str = ""
    ) -> None:
        """Deprecate a version."""
        version.status = VersionStatus.DEPRECATED
        version.deprecated_at = time.time()
        version.sunset_at = sunset_date.timestamp()

        if not warning_message:
            warning_message = (
                f"API version {version.version} is deprecated and will be "
                f"retired on {sunset_date.strftime('%Y-%m-%d')}"
            )

        self._deprecation_warnings[str(version.version)] = warning_message

    def deprecate_endpoint(
        self,
        endpoint: EndpointDefinition,
        replacement: str = "",
        message: str = ""
    ) -> None:
        """Deprecate an endpoint."""
        endpoint.deprecated = True
        endpoint.deprecated_at = time.time()
        endpoint.replacement = replacement

    def get_deprecation_warning(self, version: str) -> Optional[str]:
        """Get deprecation warning."""
        return self._deprecation_warnings.get(version)

    def get_deprecation_headers(
        self,
        version: APIVersion,
        endpoint: EndpointDefinition = None
    ) -> Dict[str, str]:
        """Get deprecation headers."""
        headers = {}

        if version.is_deprecated:
            headers["Deprecation"] = datetime.fromtimestamp(
                version.deprecated_at
            ).strftime("%a, %d %b %Y %H:%M:%S GMT")

            if version.sunset_at > 0:
                headers["Sunset"] = datetime.fromtimestamp(
                    version.sunset_at
                ).strftime("%a, %d %b %Y %H:%M:%S GMT")

        if endpoint and endpoint.deprecated:
            headers["X-Deprecated-Endpoint"] = "true"

            if endpoint.replacement:
                headers["Link"] = f'<{endpoint.replacement}>; rel="successor-version"'

        return headers


# =============================================================================
# VERSION ANALYTICS
# =============================================================================

class VersionAnalyticsTracker:
    """Tracks version usage analytics."""

    def __init__(self):
        self._analytics: Dict[str, VersionAnalytics] = {}

    def track(
        self,
        version: str,
        endpoint: str,
        client_id: str = ""
    ) -> None:
        """Track version usage."""
        if version not in self._analytics:
            self._analytics[version] = VersionAnalytics(version=version)

        analytics = self._analytics[version]
        analytics.request_count += 1
        analytics.endpoints_used[endpoint] += 1
        analytics.last_used = time.time()

        if client_id:
            analytics.unique_clients.add(client_id)

    def get_analytics(self, version: str) -> Optional[VersionAnalytics]:
        """Get analytics for version."""
        return self._analytics.get(version)

    def get_all_analytics(self) -> Dict[str, VersionAnalytics]:
        """Get all analytics."""
        return self._analytics.copy()

    def get_inactive_versions(self, days: int = 30) -> List[str]:
        """Get versions not used in X days."""
        cutoff = time.time() - (days * 86400)

        return [
            version for version, analytics in self._analytics.items()
            if analytics.last_used < cutoff
        ]


# =============================================================================
# API VERSION MANAGER
# =============================================================================

class APIVersionManager:
    """
    Comprehensive API Version Manager for BAEL.
    """

    def __init__(
        self,
        strategy: VersioningStrategy = VersioningStrategy.PATH
    ):
        self.strategy = strategy
        self.resolver = VersionResolver(strategy)
        self.compatibility = CompatibilityChecker()
        self.deprecation = DeprecationManager()
        self.analytics = VersionAnalyticsTracker()

        self._versions: Dict[str, APIVersion] = {}
        self._current_version: Optional[str] = None
        self._default_version: Optional[str] = None

    # -------------------------------------------------------------------------
    # VERSION MANAGEMENT
    # -------------------------------------------------------------------------

    def create_version(
        self,
        major: int,
        minor: int = 0,
        patch: int = 0,
        status: VersionStatus = VersionStatus.CURRENT
    ) -> APIVersion:
        """Create a new API version."""
        version = SemanticVersion(major=major, minor=minor, patch=patch)

        api_version = APIVersion(
            version=version,
            status=status
        )

        self._versions[str(version)] = api_version

        if status == VersionStatus.CURRENT:
            self._set_current(str(version))

        return api_version

    def _set_current(self, version_str: str) -> None:
        """Set current version."""
        # Demote old current
        if self._current_version and self._current_version in self._versions:
            old = self._versions[self._current_version]

            if old.status == VersionStatus.CURRENT:
                old.status = VersionStatus.SUPPORTED

        self._current_version = version_str

        if not self._default_version:
            self._default_version = version_str

    def get_version(self, version_str: str) -> Optional[APIVersion]:
        """Get API version."""
        return self._versions.get(version_str)

    def list_versions(
        self,
        status: VersionStatus = None,
        active_only: bool = False
    ) -> List[APIVersion]:
        """List API versions."""
        versions = list(self._versions.values())

        if status:
            versions = [v for v in versions if v.status == status]

        if active_only:
            versions = [v for v in versions if v.is_active]

        return sorted(versions, key=lambda v: v.version, reverse=True)

    def get_current_version(self) -> Optional[APIVersion]:
        """Get current version."""
        if self._current_version:
            return self._versions.get(self._current_version)
        return None

    # -------------------------------------------------------------------------
    # ENDPOINT MANAGEMENT
    # -------------------------------------------------------------------------

    def add_endpoint(
        self,
        version_str: str,
        path: str,
        method: str = "GET",
        name: str = "",
        description: str = "",
        parameters: Dict[str, Any] = None,
        request_schema: Dict[str, Any] = None,
        response_schema: Dict[str, Any] = None
    ) -> Optional[EndpointDefinition]:
        """Add endpoint to version."""
        version = self._versions.get(version_str)

        if not version:
            return None

        endpoint = EndpointDefinition(
            path=path,
            method=method.upper(),
            name=name or f"{method} {path}",
            description=description,
            parameters=parameters or {},
            request_schema=request_schema or {},
            response_schema=response_schema or {}
        )

        key = f"{method.upper()}:{path}"
        version.endpoints[key] = endpoint

        return endpoint

    def get_endpoint(
        self,
        version_str: str,
        path: str,
        method: str = "GET"
    ) -> Optional[EndpointDefinition]:
        """Get endpoint from version."""
        version = self._versions.get(version_str)

        if not version:
            return None

        key = f"{method.upper()}:{path}"
        return version.endpoints.get(key)

    def copy_endpoints(
        self,
        from_version: str,
        to_version: str
    ) -> int:
        """Copy endpoints from one version to another."""
        from_ver = self._versions.get(from_version)
        to_ver = self._versions.get(to_version)

        if not from_ver or not to_ver:
            return 0

        copied = 0

        for key, endpoint in from_ver.endpoints.items():
            if key not in to_ver.endpoints:
                # Deep copy
                new_endpoint = EndpointDefinition(
                    path=endpoint.path,
                    method=endpoint.method,
                    name=endpoint.name,
                    description=endpoint.description,
                    parameters=endpoint.parameters.copy(),
                    request_schema=endpoint.request_schema.copy(),
                    response_schema=endpoint.response_schema.copy()
                )
                to_ver.endpoints[key] = new_endpoint
                copied += 1

        return copied

    # -------------------------------------------------------------------------
    # VERSION RESOLUTION
    # -------------------------------------------------------------------------

    def resolve_request(
        self,
        request: VersionRequest
    ) -> VersionResponse:
        """Resolve version for request."""
        # Resolve version
        version_str = self.resolver.resolve(request)

        if not version_str:
            version_str = self._default_version

        # Parse version
        if version_str:
            version = SemanticVersion.parse(version_str)
        else:
            # Use current
            current = self.get_current_version()

            if current:
                version = current.version
            else:
                return VersionResponse()

        # Find matching version
        api_version = self._find_compatible_version(version)

        if not api_version:
            return VersionResponse()

        # Find endpoint
        endpoint_path = self._strip_version_prefix(request.path)
        key = f"{request.method.upper()}:{endpoint_path}"
        endpoint = api_version.endpoints.get(key)

        # Get deprecation warnings
        warning = ""
        headers = {}

        if api_version.is_deprecated:
            warning = self.deprecation.get_deprecation_warning(str(api_version.version))
            headers.update(self.deprecation.get_deprecation_headers(api_version, endpoint))

        # Track analytics
        self.analytics.track(
            str(api_version.version),
            endpoint_path,
            request.headers.get("X-Client-ID", "")
        )

        return VersionResponse(
            resolved_version=api_version.version,
            endpoint=endpoint,
            deprecation_warning=warning or "",
            headers=headers
        )

    def _find_compatible_version(
        self,
        version: SemanticVersion
    ) -> Optional[APIVersion]:
        """Find compatible version."""
        # Exact match
        version_str = str(version)

        if version_str in self._versions:
            return self._versions[version_str]

        # Find compatible version with same major
        compatible = [
            v for v in self._versions.values()
            if v.version.major == version.major and v.is_active
        ]

        if compatible:
            # Return latest minor/patch
            return max(compatible, key=lambda v: v.version)

        return None

    def _strip_version_prefix(self, path: str) -> str:
        """Strip version prefix from path."""
        # Remove /api/vX or /vX prefix
        path = re.sub(r'^/api/v\d+(?:\.\d+)*', '', path)
        path = re.sub(r'^/v\d+(?:\.\d+)*', '', path)

        return path or "/"

    # -------------------------------------------------------------------------
    # DEPRECATION
    # -------------------------------------------------------------------------

    def deprecate_version(
        self,
        version_str: str,
        sunset_date: datetime,
        warning: str = ""
    ) -> bool:
        """Deprecate a version."""
        version = self._versions.get(version_str)

        if not version:
            return False

        self.deprecation.deprecate_version(version, sunset_date, warning)

        return True

    def deprecate_endpoint(
        self,
        version_str: str,
        path: str,
        method: str = "GET",
        replacement: str = ""
    ) -> bool:
        """Deprecate an endpoint."""
        endpoint = self.get_endpoint(version_str, path, method)

        if not endpoint:
            return False

        self.deprecation.deprecate_endpoint(endpoint, replacement)

        return True

    def retire_version(self, version_str: str) -> bool:
        """Retire a version."""
        version = self._versions.get(version_str)

        if not version:
            return False

        version.status = VersionStatus.RETIRED

        return True

    # -------------------------------------------------------------------------
    # COMPATIBILITY
    # -------------------------------------------------------------------------

    def check_compatibility(
        self,
        from_version: str,
        to_version: str
    ) -> Tuple[CompatibilityLevel, List[str]]:
        """Check compatibility between versions."""
        from_ver = self._versions.get(from_version)
        to_ver = self._versions.get(to_version)

        if not from_ver or not to_ver:
            return CompatibilityLevel.NONE, ["Version not found"]

        all_issues = []
        worst_level = CompatibilityLevel.FULL

        for key, old_endpoint in from_ver.endpoints.items():
            new_endpoint = to_ver.endpoints.get(key)

            if not new_endpoint:
                all_issues.append(f"Endpoint removed: {key}")
                worst_level = CompatibilityLevel.NONE
                continue

            level, issues = self.compatibility.check_endpoint_compatibility(
                old_endpoint,
                new_endpoint
            )

            all_issues.extend(issues)

            if level.value > worst_level.value:  # Worse compatibility
                worst_level = level

        return worst_level, all_issues

    def get_migration_path(
        self,
        from_version: str,
        to_version: str
    ) -> MigrationPath:
        """Get migration path between versions."""
        from_ver = SemanticVersion.parse(from_version)
        to_ver = SemanticVersion.parse(to_version)

        level, issues = self.check_compatibility(from_version, to_version)

        steps = []
        breaking = []

        if from_ver.major != to_ver.major:
            steps.append(f"Major version upgrade from v{from_ver.major} to v{to_ver.major}")
            breaking = [i for i in issues if "removed" in i.lower() or "required" in i.lower()]

        if from_ver.minor != to_ver.minor:
            steps.append(f"Minor version update: {from_ver.minor} -> {to_ver.minor}")

        return MigrationPath(
            from_version=from_ver,
            to_version=to_ver,
            steps=steps,
            breaking_changes=breaking,
            automated=(level != CompatibilityLevel.NONE)
        )

    # -------------------------------------------------------------------------
    # CHANGE TRACKING
    # -------------------------------------------------------------------------

    def add_change(
        self,
        version_str: str,
        change_type: ChangeType,
        description: str,
        affected_endpoints: List[str] = None,
        migration_notes: str = ""
    ) -> Optional[VersionChange]:
        """Add change to version."""
        version = self._versions.get(version_str)

        if not version:
            return None

        change = VersionChange(
            change_type=change_type,
            description=description,
            affected_endpoints=affected_endpoints or [],
            migration_notes=migration_notes
        )

        version.changes.append(change)

        return change

    def get_changes(
        self,
        version_str: str,
        change_type: ChangeType = None
    ) -> List[VersionChange]:
        """Get changes for version."""
        version = self._versions.get(version_str)

        if not version:
            return []

        changes = version.changes

        if change_type:
            changes = [c for c in changes if c.change_type == change_type]

        return changes

    # -------------------------------------------------------------------------
    # DOCUMENTATION
    # -------------------------------------------------------------------------

    def generate_changelog(
        self,
        from_version: str = None,
        to_version: str = None
    ) -> str:
        """Generate changelog."""
        versions = self.list_versions()

        if from_version:
            from_ver = SemanticVersion.parse(from_version)
            versions = [v for v in versions if v.version >= from_ver]

        if to_version:
            to_ver = SemanticVersion.parse(to_version)
            versions = [v for v in versions if v.version <= to_ver]

        lines = ["# API Changelog", ""]

        for version in versions:
            lines.append(f"## Version {version.version}")
            lines.append(f"Released: {datetime.fromtimestamp(version.released_at).strftime('%Y-%m-%d')}")
            lines.append(f"Status: {version.status.value}")
            lines.append("")

            if version.changes:
                lines.append("### Changes")

                for change in version.changes:
                    lines.append(f"- **{change.change_type.value}**: {change.description}")

                lines.append("")

        return "\n".join(lines)

    def generate_api_docs(self, version_str: str) -> str:
        """Generate API documentation."""
        version = self._versions.get(version_str)

        if not version:
            return ""

        lines = [f"# API Documentation v{version.version}", ""]

        if version.is_deprecated:
            lines.append(f"> ⚠️ This version is deprecated. Please upgrade.")
            lines.append("")

        lines.append("## Endpoints")
        lines.append("")

        for key, endpoint in version.endpoints.items():
            deprecated = " *(deprecated)*" if endpoint.deprecated else ""
            lines.append(f"### {endpoint.method} {endpoint.path}{deprecated}")
            lines.append(f"{endpoint.description}")
            lines.append("")

            if endpoint.parameters:
                lines.append("**Parameters:**")

                for name, info in endpoint.parameters.items():
                    req = " (required)" if info.get("required") else ""
                    lines.append(f"- `{name}`{req}: {info.get('description', '')}")

                lines.append("")

            if endpoint.replacement:
                lines.append(f"**Replacement:** `{endpoint.replacement}`")
                lines.append("")

        return "\n".join(lines)

    # -------------------------------------------------------------------------
    # ANALYTICS
    # -------------------------------------------------------------------------

    def get_version_analytics(self, version_str: str) -> Optional[Dict[str, Any]]:
        """Get version analytics."""
        analytics = self.analytics.get_analytics(version_str)

        if not analytics:
            return None

        return {
            "version": analytics.version,
            "request_count": analytics.request_count,
            "unique_clients": len(analytics.unique_clients),
            "endpoints_used": dict(analytics.endpoints_used),
            "last_used": analytics.last_used
        }

    def get_inactive_versions(self, days: int = 30) -> List[str]:
        """Get versions not used recently."""
        return self.analytics.get_inactive_versions(days)

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get version statistics."""
        versions = list(self._versions.values())

        return {
            "total_versions": len(versions),
            "current_version": self._current_version,
            "default_version": self._default_version,
            "active_versions": len([v for v in versions if v.is_active]),
            "deprecated_versions": len([v for v in versions if v.is_deprecated]),
            "total_endpoints": sum(len(v.endpoints) for v in versions),
            "strategy": self.strategy.value
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the API Versioning System."""
    print("=" * 70)
    print("BAEL - API VERSIONING MANAGER DEMO")
    print("Comprehensive API Version Management")
    print("=" * 70)
    print()

    manager = APIVersionManager(strategy=VersioningStrategy.PATH)

    # 1. Create Versions
    print("1. CREATE API VERSIONS:")
    print("-" * 40)

    v1 = manager.create_version(1, 0, 0, VersionStatus.SUPPORTED)
    v2 = manager.create_version(2, 0, 0, VersionStatus.CURRENT)

    print(f"   Created: v{v1.version} ({v1.status.value})")
    print(f"   Created: v{v2.version} ({v2.status.value})")
    print()

    # 2. Add Endpoints to v1
    print("2. ADD ENDPOINTS TO v1:")
    print("-" * 40)

    manager.add_endpoint(
        "1.0.0",
        "/users",
        "GET",
        "List Users",
        "Get all users",
        parameters={
            "limit": {"type": "integer", "description": "Max results"},
            "offset": {"type": "integer", "description": "Skip results"}
        },
        response_schema={
            "type": "array",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"}
            }
        }
    )
    print("   Added: GET /users")

    manager.add_endpoint(
        "1.0.0",
        "/users/{id}",
        "GET",
        "Get User",
        "Get user by ID"
    )
    print("   Added: GET /users/{id}")

    manager.add_endpoint(
        "1.0.0",
        "/users",
        "POST",
        "Create User",
        "Create new user"
    )
    print("   Added: POST /users")
    print()

    # 3. Add Endpoints to v2
    print("3. ADD ENDPOINTS TO v2:")
    print("-" * 40)

    # Copy from v1
    copied = manager.copy_endpoints("1.0.0", "2.0.0")
    print(f"   Copied {copied} endpoints from v1")

    # Add new endpoint
    manager.add_endpoint(
        "2.0.0",
        "/users/{id}/profile",
        "GET",
        "Get User Profile",
        "Get detailed user profile"
    )
    print("   Added: GET /users/{id}/profile")
    print()

    # 4. Resolve Version from Request
    print("4. RESOLVE VERSION FROM REQUEST:")
    print("-" * 40)

    request = VersionRequest(
        path="/api/v2/users",
        method="GET",
        headers={"X-Client-ID": "client_123"}
    )

    response = manager.resolve_request(request)

    print(f"   Request: {request.path}")
    print(f"   Resolved version: {response.resolved_version}")
    print(f"   Endpoint: {response.endpoint.name if response.endpoint else 'None'}")
    print()

    # 5. Version Negotiation
    print("5. VERSION NEGOTIATION:")
    print("-" * 40)

    # Request v1.5 (should get v1.0.0)
    request = VersionRequest(
        path="/api/v1.5/users",
        method="GET"
    )

    response = manager.resolve_request(request)
    print(f"   Requested: v1.5")
    print(f"   Resolved: v{response.resolved_version}")
    print()

    # 6. Deprecate Version
    print("6. DEPRECATE VERSION:")
    print("-" * 40)

    sunset_date = datetime.now() + timedelta(days=90)

    manager.deprecate_version(
        "1.0.0",
        sunset_date,
        "Please migrate to v2.0. v1.0 will be retired in 90 days."
    )

    print(f"   Deprecated: v1.0.0")
    print(f"   Sunset: {sunset_date.strftime('%Y-%m-%d')}")

    # Request deprecated version
    request = VersionRequest(path="/api/v1/users", method="GET")
    response = manager.resolve_request(request)

    print(f"   Warning: {response.deprecation_warning[:50]}...")
    print(f"   Headers: {response.headers}")
    print()

    # 7. Deprecate Endpoint
    print("7. DEPRECATE ENDPOINT:")
    print("-" * 40)

    manager.deprecate_endpoint(
        "2.0.0",
        "/users/{id}",
        "GET",
        "/users/{id}/profile"
    )

    endpoint = manager.get_endpoint("2.0.0", "/users/{id}", "GET")

    print(f"   Deprecated: GET /users/{{id}}")
    print(f"   Replacement: {endpoint.replacement}")
    print()

    # 8. Check Compatibility
    print("8. CHECK COMPATIBILITY:")
    print("-" * 40)

    level, issues = manager.check_compatibility("1.0.0", "2.0.0")

    print(f"   v1.0.0 -> v2.0.0")
    print(f"   Compatibility: {level.value}")

    if issues:
        print(f"   Issues:")
        for issue in issues[:3]:
            print(f"      - {issue}")
    print()

    # 9. Migration Path
    print("9. MIGRATION PATH:")
    print("-" * 40)

    path = manager.get_migration_path("1.0.0", "2.0.0")

    print(f"   From: v{path.from_version}")
    print(f"   To: v{path.to_version}")
    print(f"   Steps: {path.steps}")
    print(f"   Breaking changes: {len(path.breaking_changes)}")
    print(f"   Automated: {path.automated}")
    print()

    # 10. Track Changes
    print("10. TRACK CHANGES:")
    print("-" * 40)

    manager.add_change(
        "2.0.0",
        ChangeType.ADDITION,
        "Added /users/{id}/profile endpoint"
    )

    manager.add_change(
        "2.0.0",
        ChangeType.DEPRECATION,
        "Deprecated GET /users/{id} in favor of profile endpoint",
        affected_endpoints=["GET:/users/{id}"]
    )

    changes = manager.get_changes("2.0.0")

    print(f"   Changes in v2.0.0:")
    for change in changes:
        print(f"      - [{change.change_type.value}] {change.description}")
    print()

    # 11. Generate Changelog
    print("11. GENERATE CHANGELOG:")
    print("-" * 40)

    changelog = manager.generate_changelog()

    # Print first 10 lines
    for line in changelog.split("\n")[:10]:
        print(f"   {line}")
    print("   ...")
    print()

    # 12. List Versions
    print("12. LIST VERSIONS:")
    print("-" * 40)

    versions = manager.list_versions()

    for v in versions:
        status = "✓" if v.is_active else "✗"
        print(f"   [{status}] v{v.version} - {v.status.value}")
        print(f"       Endpoints: {len(v.endpoints)}")
    print()

    # 13. Version Analytics
    print("13. VERSION ANALYTICS:")
    print("-" * 40)

    # Make some requests
    for i in range(5):
        request = VersionRequest(path="/api/v2/users", method="GET")
        manager.resolve_request(request)

    for i in range(3):
        request = VersionRequest(path="/api/v1/users", method="GET")
        manager.resolve_request(request)

    analytics = manager.get_version_analytics("2.0.0")

    if analytics:
        print(f"   Version 2.0.0:")
        print(f"      Requests: {analytics['request_count']}")
        print(f"      Unique clients: {analytics['unique_clients']}")
        print(f"      Endpoints: {dict(analytics['endpoints_used'])}")
    print()

    # 14. Overall Stats
    print("14. OVERALL STATS:")
    print("-" * 40)

    stats = manager.get_stats()

    print(f"   Total versions: {stats['total_versions']}")
    print(f"   Current version: {stats['current_version']}")
    print(f"   Active versions: {stats['active_versions']}")
    print(f"   Deprecated versions: {stats['deprecated_versions']}")
    print(f"   Total endpoints: {stats['total_endpoints']}")
    print(f"   Strategy: {stats['strategy']}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - API Versioning System Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
