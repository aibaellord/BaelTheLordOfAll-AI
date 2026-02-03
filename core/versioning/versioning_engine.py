#!/usr/bin/env python3
"""
BAEL - Versioning Engine
Version control for agents.

Features:
- Semantic versioning
- Version comparison
- Change tracking
- Version ranges
- Compatibility checks
"""

import asyncio
import hashlib
import json
import re
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    Any, Callable, Dict, Generic, List, Optional, Set, Tuple, Type, TypeVar, Union
)


T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class VersionType(Enum):
    """Version types."""
    SEMANTIC = "semantic"
    NUMERIC = "numeric"
    DATE = "date"
    CUSTOM = "custom"


class ChangeType(Enum):
    """Change types."""
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
    PRERELEASE = "prerelease"
    BUILD = "build"


class CompatibilityLevel(Enum):
    """Compatibility levels."""
    FULL = "full"
    BACKWARD = "backward"
    FORWARD = "forward"
    NONE = "none"


class RangeOperator(Enum):
    """Range operators."""
    EXACT = "="
    GREATER = ">"
    GREATER_OR_EQUAL = ">="
    LESS = "<"
    LESS_OR_EQUAL = "<="
    CARET = "^"
    TILDE = "~"
    WILDCARD = "*"


class VersionState(Enum):
    """Version states."""
    DEVELOPMENT = "development"
    ALPHA = "alpha"
    BETA = "beta"
    RELEASE_CANDIDATE = "rc"
    STABLE = "stable"
    DEPRECATED = "deprecated"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class SemanticVersion:
    """Semantic version (SemVer)."""
    major: int = 0
    minor: int = 0
    patch: int = 0
    prerelease: str = ""
    build: str = ""
    
    def __str__(self) -> str:
        result = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            result += f"-{self.prerelease}"
        if self.build:
            result += f"+{self.build}"
        return result
    
    def __lt__(self, other: "SemanticVersion") -> bool:
        if (self.major, self.minor, self.patch) != (other.major, other.minor, other.patch):
            return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)
        
        if self.prerelease and not other.prerelease:
            return True
        if not self.prerelease and other.prerelease:
            return False
        
        return self.prerelease < other.prerelease
    
    def __le__(self, other: "SemanticVersion") -> bool:
        return self == other or self < other
    
    def __gt__(self, other: "SemanticVersion") -> bool:
        return not self <= other
    
    def __ge__(self, other: "SemanticVersion") -> bool:
        return not self < other
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SemanticVersion):
            return False
        return (
            self.major == other.major and
            self.minor == other.minor and
            self.patch == other.patch and
            self.prerelease == other.prerelease
        )
    
    def __hash__(self) -> int:
        return hash((self.major, self.minor, self.patch, self.prerelease))


@dataclass
class VersionRange:
    """Version range specification."""
    operator: RangeOperator = RangeOperator.EXACT
    version: Optional[SemanticVersion] = None
    end_version: Optional[SemanticVersion] = None
    
    def matches(self, version: SemanticVersion) -> bool:
        """Check if version matches range."""
        if not self.version:
            return True
        
        if self.operator == RangeOperator.EXACT:
            return version == self.version
        
        if self.operator == RangeOperator.GREATER:
            return version > self.version
        
        if self.operator == RangeOperator.GREATER_OR_EQUAL:
            return version >= self.version
        
        if self.operator == RangeOperator.LESS:
            return version < self.version
        
        if self.operator == RangeOperator.LESS_OR_EQUAL:
            return version <= self.version
        
        if self.operator == RangeOperator.CARET:
            if self.version.major == 0:
                return (
                    version.major == 0 and
                    version.minor == self.version.minor and
                    version >= self.version
                )
            return (
                version.major == self.version.major and
                version >= self.version
            )
        
        if self.operator == RangeOperator.TILDE:
            return (
                version.major == self.version.major and
                version.minor == self.version.minor and
                version >= self.version
            )
        
        if self.operator == RangeOperator.WILDCARD:
            return True
        
        return False
    
    def __str__(self) -> str:
        if not self.version:
            return "*"
        return f"{self.operator.value}{self.version}"


@dataclass
class ChangeRecord:
    """Record of a change."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    change_type: ChangeType = ChangeType.PATCH
    description: str = ""
    author: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    breaking: bool = False
    files: List[str] = field(default_factory=list)


@dataclass
class VersionInfo:
    """Version information."""
    version: SemanticVersion = field(default_factory=SemanticVersion)
    state: VersionState = VersionState.DEVELOPMENT
    created_at: datetime = field(default_factory=datetime.now)
    released_at: Optional[datetime] = None
    changes: List[ChangeRecord] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VersionDiff:
    """Difference between versions."""
    from_version: SemanticVersion = field(default_factory=SemanticVersion)
    to_version: SemanticVersion = field(default_factory=SemanticVersion)
    change_type: ChangeType = ChangeType.PATCH
    changes: List[ChangeRecord] = field(default_factory=list)
    breaking_changes: int = 0


@dataclass
class CompatibilityResult:
    """Compatibility check result."""
    compatible: bool = True
    level: CompatibilityLevel = CompatibilityLevel.FULL
    issues: List[str] = field(default_factory=list)


@dataclass
class VersionStats:
    """Version statistics."""
    total_versions: int = 0
    major_versions: int = 0
    minor_versions: int = 0
    patch_versions: int = 0
    total_changes: int = 0
    breaking_changes: int = 0


# =============================================================================
# VERSION PARSER
# =============================================================================

class VersionParser:
    """Parse version strings."""
    
    SEMVER_PATTERN = re.compile(
        r'^(?P<major>0|[1-9]\d*)'
        r'\.(?P<minor>0|[1-9]\d*)'
        r'\.(?P<patch>0|[1-9]\d*)'
        r'(?:-(?P<prerelease>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?'
        r'(?:\+(?P<build>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$'
    )
    
    RANGE_PATTERN = re.compile(
        r'^(?P<operator>[<>=^~]*)?(?P<version>.+)$'
    )
    
    @classmethod
    def parse(cls, version_str: str) -> Optional[SemanticVersion]:
        """Parse a version string."""
        version_str = version_str.strip()
        
        if version_str.startswith('v'):
            version_str = version_str[1:]
        
        match = cls.SEMVER_PATTERN.match(version_str)
        
        if not match:
            parts = version_str.split('.')
            if len(parts) >= 1:
                try:
                    major = int(parts[0])
                    minor = int(parts[1]) if len(parts) > 1 else 0
                    patch = int(parts[2].split('-')[0].split('+')[0]) if len(parts) > 2 else 0
                    return SemanticVersion(major=major, minor=minor, patch=patch)
                except ValueError:
                    return None
            return None
        
        return SemanticVersion(
            major=int(match.group('major')),
            minor=int(match.group('minor')),
            patch=int(match.group('patch')),
            prerelease=match.group('prerelease') or "",
            build=match.group('build') or ""
        )
    
    @classmethod
    def parse_range(cls, range_str: str) -> Optional[VersionRange]:
        """Parse a version range string."""
        range_str = range_str.strip()
        
        if range_str == '*' or range_str == 'latest':
            return VersionRange(operator=RangeOperator.WILDCARD)
        
        operator = RangeOperator.EXACT
        version_str = range_str
        
        if range_str.startswith('>='):
            operator = RangeOperator.GREATER_OR_EQUAL
            version_str = range_str[2:]
        elif range_str.startswith('<='):
            operator = RangeOperator.LESS_OR_EQUAL
            version_str = range_str[2:]
        elif range_str.startswith('>'):
            operator = RangeOperator.GREATER
            version_str = range_str[1:]
        elif range_str.startswith('<'):
            operator = RangeOperator.LESS
            version_str = range_str[1:]
        elif range_str.startswith('^'):
            operator = RangeOperator.CARET
            version_str = range_str[1:]
        elif range_str.startswith('~'):
            operator = RangeOperator.TILDE
            version_str = range_str[1:]
        elif range_str.startswith('='):
            operator = RangeOperator.EXACT
            version_str = range_str[1:]
        
        version = cls.parse(version_str)
        
        if not version:
            return None
        
        return VersionRange(operator=operator, version=version)


# =============================================================================
# VERSION HISTORY
# =============================================================================

class VersionHistory:
    """Manages version history for an artifact."""
    
    def __init__(self, artifact_id: str):
        self._artifact_id = artifact_id
        self._versions: Dict[str, VersionInfo] = {}
        self._current: Optional[SemanticVersion] = None
        self._tags: Dict[str, SemanticVersion] = {}
    
    @property
    def artifact_id(self) -> str:
        return self._artifact_id
    
    @property
    def current(self) -> Optional[SemanticVersion]:
        return self._current
    
    def add_version(self, info: VersionInfo) -> None:
        """Add a version."""
        key = str(info.version)
        self._versions[key] = info
        
        if self._current is None or info.version > self._current:
            self._current = info.version
    
    def get_version(self, version: Union[str, SemanticVersion]) -> Optional[VersionInfo]:
        """Get version info."""
        key = str(version)
        return self._versions.get(key)
    
    def list_versions(self) -> List[SemanticVersion]:
        """List all versions in order."""
        return sorted(
            [v.version for v in self._versions.values()],
            key=lambda v: (v.major, v.minor, v.patch)
        )
    
    def get_latest(self, state: Optional[VersionState] = None) -> Optional[VersionInfo]:
        """Get latest version."""
        if state:
            versions = [v for v in self._versions.values() if v.state == state]
        else:
            versions = list(self._versions.values())
        
        if not versions:
            return None
        
        return max(versions, key=lambda v: v.version)
    
    def tag(self, tag_name: str, version: SemanticVersion) -> None:
        """Add a tag to a version."""
        self._tags[tag_name] = version
    
    def get_by_tag(self, tag_name: str) -> Optional[VersionInfo]:
        """Get version by tag."""
        version = self._tags.get(tag_name)
        if version:
            return self.get_version(version)
        return None
    
    def find_matching(self, version_range: VersionRange) -> List[VersionInfo]:
        """Find versions matching range."""
        return [
            v for v in self._versions.values()
            if version_range.matches(v.version)
        ]
    
    def diff(
        self,
        from_version: SemanticVersion,
        to_version: SemanticVersion
    ) -> VersionDiff:
        """Get diff between versions."""
        from_info = self.get_version(from_version)
        to_info = self.get_version(to_version)
        
        if not from_info or not to_info:
            return VersionDiff(
                from_version=from_version,
                to_version=to_version
            )
        
        if to_version.major > from_version.major:
            change_type = ChangeType.MAJOR
        elif to_version.minor > from_version.minor:
            change_type = ChangeType.MINOR
        else:
            change_type = ChangeType.PATCH
        
        changes = []
        breaking_count = 0
        
        for v in self._versions.values():
            if from_version < v.version <= to_version:
                changes.extend(v.changes)
                breaking_count += sum(1 for c in v.changes if c.breaking)
        
        return VersionDiff(
            from_version=from_version,
            to_version=to_version,
            change_type=change_type,
            changes=changes,
            breaking_changes=breaking_count
        )
    
    def count(self) -> int:
        """Count versions."""
        return len(self._versions)


# =============================================================================
# VERSION BUMPER
# =============================================================================

class VersionBumper:
    """Bump versions based on change type."""
    
    @staticmethod
    def bump(version: SemanticVersion, change_type: ChangeType) -> SemanticVersion:
        """Bump version based on change type."""
        if change_type == ChangeType.MAJOR:
            return SemanticVersion(
                major=version.major + 1,
                minor=0,
                patch=0
            )
        
        if change_type == ChangeType.MINOR:
            return SemanticVersion(
                major=version.major,
                minor=version.minor + 1,
                patch=0
            )
        
        if change_type == ChangeType.PATCH:
            return SemanticVersion(
                major=version.major,
                minor=version.minor,
                patch=version.patch + 1
            )
        
        if change_type == ChangeType.PRERELEASE:
            prerelease = version.prerelease
            
            if prerelease:
                parts = prerelease.rsplit('.', 1)
                if len(parts) == 2 and parts[1].isdigit():
                    new_prerelease = f"{parts[0]}.{int(parts[1]) + 1}"
                else:
                    new_prerelease = f"{prerelease}.1"
            else:
                new_prerelease = "alpha.1"
            
            return SemanticVersion(
                major=version.major,
                minor=version.minor,
                patch=version.patch,
                prerelease=new_prerelease
            )
        
        if change_type == ChangeType.BUILD:
            build = version.build
            
            if build:
                if build.isdigit():
                    new_build = str(int(build) + 1)
                else:
                    new_build = f"{build}.1"
            else:
                new_build = "1"
            
            return SemanticVersion(
                major=version.major,
                minor=version.minor,
                patch=version.patch,
                prerelease=version.prerelease,
                build=new_build
            )
        
        return version
    
    @staticmethod
    def suggest(changes: List[ChangeRecord]) -> ChangeType:
        """Suggest change type based on changes."""
        if any(c.breaking for c in changes):
            return ChangeType.MAJOR
        
        if any(c.change_type == ChangeType.MAJOR for c in changes):
            return ChangeType.MAJOR
        
        if any(c.change_type == ChangeType.MINOR for c in changes):
            return ChangeType.MINOR
        
        return ChangeType.PATCH


# =============================================================================
# COMPATIBILITY CHECKER
# =============================================================================

class CompatibilityChecker:
    """Check version compatibility."""
    
    def __init__(self):
        self._rules: List[Callable[[SemanticVersion, SemanticVersion], Optional[str]]] = []
    
    def add_rule(
        self,
        rule: Callable[[SemanticVersion, SemanticVersion], Optional[str]]
    ) -> None:
        """Add a compatibility rule."""
        self._rules.append(rule)
    
    def check(
        self,
        from_version: SemanticVersion,
        to_version: SemanticVersion
    ) -> CompatibilityResult:
        """Check compatibility between versions."""
        issues = []
        
        for rule in self._rules:
            issue = rule(from_version, to_version)
            if issue:
                issues.append(issue)
        
        if to_version.major > from_version.major:
            level = CompatibilityLevel.NONE
            issues.append("Major version change - breaking changes expected")
        elif to_version.major < from_version.major:
            level = CompatibilityLevel.NONE
            issues.append("Downgrade not supported")
        elif to_version.minor > from_version.minor:
            level = CompatibilityLevel.BACKWARD
        elif to_version.minor < from_version.minor:
            level = CompatibilityLevel.FORWARD
        else:
            level = CompatibilityLevel.FULL
        
        return CompatibilityResult(
            compatible=len(issues) == 0,
            level=level,
            issues=issues
        )
    
    @staticmethod
    def is_compatible(
        required: VersionRange,
        available: SemanticVersion
    ) -> bool:
        """Check if available version satisfies requirement."""
        return required.matches(available)


# =============================================================================
# CHANGELOG GENERATOR
# =============================================================================

class ChangelogGenerator:
    """Generate changelogs."""
    
    def __init__(self):
        self._format = "markdown"
    
    def generate(
        self,
        history: VersionHistory,
        from_version: Optional[SemanticVersion] = None,
        to_version: Optional[SemanticVersion] = None
    ) -> str:
        """Generate changelog."""
        versions = history.list_versions()
        
        if from_version:
            versions = [v for v in versions if v >= from_version]
        if to_version:
            versions = [v for v in versions if v <= to_version]
        
        lines = ["# Changelog", ""]
        
        for version in reversed(versions):
            info = history.get_version(version)
            if not info:
                continue
            
            lines.append(f"## [{version}] - {info.created_at.strftime('%Y-%m-%d')}")
            lines.append("")
            
            breaking = [c for c in info.changes if c.breaking]
            added = [c for c in info.changes if c.change_type == ChangeType.MINOR and not c.breaking]
            fixed = [c for c in info.changes if c.change_type == ChangeType.PATCH and not c.breaking]
            
            if breaking:
                lines.append("### Breaking Changes")
                for change in breaking:
                    lines.append(f"- {change.description}")
                lines.append("")
            
            if added:
                lines.append("### Added")
                for change in added:
                    lines.append(f"- {change.description}")
                lines.append("")
            
            if fixed:
                lines.append("### Fixed")
                for change in fixed:
                    lines.append(f"- {change.description}")
                lines.append("")
        
        return "\n".join(lines)


# =============================================================================
# VERSIONING ENGINE
# =============================================================================

class VersioningEngine:
    """
    Versioning Engine for BAEL.
    
    Version control for agents.
    """
    
    def __init__(self):
        self._histories: Dict[str, VersionHistory] = {}
        self._checker = CompatibilityChecker()
        self._changelog_gen = ChangelogGenerator()
        self._stats = VersionStats()
    
    # ----- History Management -----
    
    def create_history(self, artifact_id: str) -> VersionHistory:
        """Create version history for an artifact."""
        history = VersionHistory(artifact_id)
        self._histories[artifact_id] = history
        return history
    
    def get_history(self, artifact_id: str) -> Optional[VersionHistory]:
        """Get version history."""
        return self._histories.get(artifact_id)
    
    def list_artifacts(self) -> List[str]:
        """List all artifacts."""
        return list(self._histories.keys())
    
    # ----- Version Parsing -----
    
    def parse(self, version_str: str) -> Optional[SemanticVersion]:
        """Parse a version string."""
        return VersionParser.parse(version_str)
    
    def parse_range(self, range_str: str) -> Optional[VersionRange]:
        """Parse a version range."""
        return VersionParser.parse_range(range_str)
    
    # ----- Version Creation -----
    
    def create_version(
        self,
        artifact_id: str,
        version: Union[str, SemanticVersion],
        state: VersionState = VersionState.DEVELOPMENT,
        changes: Optional[List[ChangeRecord]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[VersionInfo]:
        """Create a new version."""
        history = self._histories.get(artifact_id)
        
        if not history:
            history = self.create_history(artifact_id)
        
        if isinstance(version, str):
            parsed = self.parse(version)
            if not parsed:
                return None
            version = parsed
        
        info = VersionInfo(
            version=version,
            state=state,
            changes=changes or [],
            metadata=metadata or {}
        )
        
        history.add_version(info)
        self._update_stats(info)
        
        return info
    
    def bump_version(
        self,
        artifact_id: str,
        change_type: ChangeType,
        changes: Optional[List[ChangeRecord]] = None
    ) -> Optional[SemanticVersion]:
        """Bump version."""
        history = self._histories.get(artifact_id)
        
        if not history or not history.current:
            return None
        
        new_version = VersionBumper.bump(history.current, change_type)
        
        info = VersionInfo(
            version=new_version,
            changes=changes or []
        )
        
        history.add_version(info)
        self._update_stats(info)
        
        return new_version
    
    # ----- Version Queries -----
    
    def get_version(
        self,
        artifact_id: str,
        version: Union[str, SemanticVersion]
    ) -> Optional[VersionInfo]:
        """Get version info."""
        history = self._histories.get(artifact_id)
        
        if not history:
            return None
        
        return history.get_version(version)
    
    def get_latest(
        self,
        artifact_id: str,
        state: Optional[VersionState] = None
    ) -> Optional[VersionInfo]:
        """Get latest version."""
        history = self._histories.get(artifact_id)
        
        if not history:
            return None
        
        return history.get_latest(state)
    
    def find_versions(
        self,
        artifact_id: str,
        range_str: str
    ) -> List[VersionInfo]:
        """Find versions matching range."""
        history = self._histories.get(artifact_id)
        
        if not history:
            return []
        
        version_range = self.parse_range(range_str)
        
        if not version_range:
            return []
        
        return history.find_matching(version_range)
    
    # ----- Tagging -----
    
    def tag(
        self,
        artifact_id: str,
        tag_name: str,
        version: Union[str, SemanticVersion]
    ) -> bool:
        """Tag a version."""
        history = self._histories.get(artifact_id)
        
        if not history:
            return False
        
        if isinstance(version, str):
            parsed = self.parse(version)
            if not parsed:
                return False
            version = parsed
        
        history.tag(tag_name, version)
        return True
    
    def get_by_tag(self, artifact_id: str, tag_name: str) -> Optional[VersionInfo]:
        """Get version by tag."""
        history = self._histories.get(artifact_id)
        
        if not history:
            return None
        
        return history.get_by_tag(tag_name)
    
    # ----- Comparison -----
    
    def compare(
        self,
        v1: Union[str, SemanticVersion],
        v2: Union[str, SemanticVersion]
    ) -> int:
        """Compare two versions. Returns -1, 0, or 1."""
        if isinstance(v1, str):
            v1 = self.parse(v1) or SemanticVersion()
        if isinstance(v2, str):
            v2 = self.parse(v2) or SemanticVersion()
        
        if v1 < v2:
            return -1
        if v1 > v2:
            return 1
        return 0
    
    def diff(
        self,
        artifact_id: str,
        from_version: Union[str, SemanticVersion],
        to_version: Union[str, SemanticVersion]
    ) -> Optional[VersionDiff]:
        """Get diff between versions."""
        history = self._histories.get(artifact_id)
        
        if not history:
            return None
        
        if isinstance(from_version, str):
            from_version = self.parse(from_version) or SemanticVersion()
        if isinstance(to_version, str):
            to_version = self.parse(to_version) or SemanticVersion()
        
        return history.diff(from_version, to_version)
    
    # ----- Compatibility -----
    
    def check_compatibility(
        self,
        from_version: Union[str, SemanticVersion],
        to_version: Union[str, SemanticVersion]
    ) -> CompatibilityResult:
        """Check compatibility between versions."""
        if isinstance(from_version, str):
            from_version = self.parse(from_version) or SemanticVersion()
        if isinstance(to_version, str):
            to_version = self.parse(to_version) or SemanticVersion()
        
        return self._checker.check(from_version, to_version)
    
    def is_satisfying(
        self,
        requirement: str,
        version: Union[str, SemanticVersion]
    ) -> bool:
        """Check if version satisfies requirement."""
        version_range = self.parse_range(requirement)
        
        if not version_range:
            return False
        
        if isinstance(version, str):
            version = self.parse(version)
            if not version:
                return False
        
        return version_range.matches(version)
    
    # ----- Changelog -----
    
    def generate_changelog(
        self,
        artifact_id: str,
        from_version: Optional[str] = None,
        to_version: Optional[str] = None
    ) -> str:
        """Generate changelog."""
        history = self._histories.get(artifact_id)
        
        if not history:
            return ""
        
        from_v = self.parse(from_version) if from_version else None
        to_v = self.parse(to_version) if to_version else None
        
        return self._changelog_gen.generate(history, from_v, to_v)
    
    # ----- Stats -----
    
    def _update_stats(self, info: VersionInfo) -> None:
        """Update statistics."""
        self._stats.total_versions += 1
        self._stats.total_changes += len(info.changes)
        self._stats.breaking_changes += sum(1 for c in info.changes if c.breaking)
        
        if info.version.major > 0:
            self._stats.major_versions += 1
        if info.version.minor > 0:
            self._stats.minor_versions += 1
        if info.version.patch > 0:
            self._stats.patch_versions += 1
    
    @property
    def stats(self) -> VersionStats:
        return self._stats
    
    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "artifacts": len(self._histories),
            "total_versions": self._stats.total_versions,
            "total_changes": self._stats.total_changes,
            "breaking_changes": self._stats.breaking_changes
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Versioning Engine."""
    print("=" * 70)
    print("BAEL - VERSIONING ENGINE DEMO")
    print("Version Control for Agents")
    print("=" * 70)
    print()
    
    engine = VersioningEngine()
    
    # 1. Parse Versions
    print("1. PARSE VERSIONS:")
    print("-" * 40)
    
    versions_to_parse = ["1.0.0", "2.1.3", "1.0.0-alpha.1", "1.0.0-beta+build.123", "v3.2.1"]
    
    for v_str in versions_to_parse:
        v = engine.parse(v_str)
        print(f"   '{v_str}' -> {v}")
    print()
    
    # 2. Compare Versions
    print("2. COMPARE VERSIONS:")
    print("-" * 40)
    
    comparisons = [
        ("1.0.0", "2.0.0"),
        ("1.2.0", "1.2.1"),
        ("1.0.0", "1.0.0"),
        ("1.0.0-alpha", "1.0.0"),
    ]
    
    for v1, v2 in comparisons:
        result = engine.compare(v1, v2)
        symbol = "<" if result < 0 else (">" if result > 0 else "=")
        print(f"   {v1} {symbol} {v2}")
    print()
    
    # 3. Create Version History
    print("3. CREATE VERSION HISTORY:")
    print("-" * 40)
    
    history = engine.create_history("bael-core")
    print(f"   Created history for: {history.artifact_id}")
    print()
    
    # 4. Add Versions
    print("4. ADD VERSIONS:")
    print("-" * 40)
    
    engine.create_version(
        "bael-core", "1.0.0",
        state=VersionState.STABLE,
        changes=[
            ChangeRecord(change_type=ChangeType.MAJOR, description="Initial release")
        ]
    )
    
    engine.create_version(
        "bael-core", "1.1.0",
        changes=[
            ChangeRecord(change_type=ChangeType.MINOR, description="Added agent support"),
            ChangeRecord(change_type=ChangeType.MINOR, description="Added tool registry")
        ]
    )
    
    engine.create_version(
        "bael-core", "1.1.1",
        changes=[
            ChangeRecord(change_type=ChangeType.PATCH, description="Fixed agent bug")
        ]
    )
    
    engine.create_version(
        "bael-core", "2.0.0",
        changes=[
            ChangeRecord(change_type=ChangeType.MAJOR, description="Async rewrite", breaking=True),
            ChangeRecord(change_type=ChangeType.MAJOR, description="New API", breaking=True)
        ]
    )
    
    for v in engine.get_history("bael-core").list_versions():
        print(f"   - {v}")
    print()
    
    # 5. Version Bumping
    print("5. VERSION BUMPING:")
    print("-" * 40)
    
    current = engine.get_latest("bael-core")
    print(f"   Current: {current.version}")
    
    new_patch = engine.bump_version("bael-core", ChangeType.PATCH, [
        ChangeRecord(change_type=ChangeType.PATCH, description="Bug fix")
    ])
    print(f"   After patch bump: {new_patch}")
    print()
    
    # 6. Version Ranges
    print("6. VERSION RANGES:")
    print("-" * 40)
    
    ranges = [">=1.0.0", "^1.1.0", "~1.1.0", "<2.0.0", "*"]
    
    for range_str in ranges:
        vr = engine.parse_range(range_str)
        print(f"   {range_str}: {vr}")
    print()
    
    # 7. Range Matching
    print("7. RANGE MATCHING:")
    print("-" * 40)
    
    test_cases = [
        ("^1.0.0", "1.5.0"),
        ("^1.0.0", "2.0.0"),
        ("~1.1.0", "1.1.5"),
        ("~1.1.0", "1.2.0"),
        (">=1.0.0", "0.9.0"),
    ]
    
    for req, ver in test_cases:
        satisfies = engine.is_satisfying(req, ver)
        symbol = "✓" if satisfies else "✗"
        print(f"   {ver} satisfies {req}: {symbol}")
    print()
    
    # 8. Find Matching Versions
    print("8. FIND MATCHING VERSIONS:")
    print("-" * 40)
    
    matching = engine.find_versions("bael-core", "^1.0.0")
    print(f"   Versions matching ^1.0.0:")
    for info in matching:
        print(f"   - {info.version}")
    print()
    
    # 9. Tagging
    print("9. TAGGING:")
    print("-" * 40)
    
    engine.tag("bael-core", "latest", "2.0.1")
    engine.tag("bael-core", "stable", "1.1.1")
    
    latest = engine.get_by_tag("bael-core", "latest")
    stable = engine.get_by_tag("bael-core", "stable")
    
    print(f"   latest: {latest.version if latest else 'N/A'}")
    print(f"   stable: {stable.version if stable else 'N/A'}")
    print()
    
    # 10. Version Diff
    print("10. VERSION DIFF:")
    print("-" * 40)
    
    diff = engine.diff("bael-core", "1.0.0", "2.0.0")
    
    if diff:
        print(f"   From: {diff.from_version}")
        print(f"   To: {diff.to_version}")
        print(f"   Change type: {diff.change_type.value}")
        print(f"   Total changes: {len(diff.changes)}")
        print(f"   Breaking changes: {diff.breaking_changes}")
    print()
    
    # 11. Compatibility Check
    print("11. COMPATIBILITY CHECK:")
    print("-" * 40)
    
    checks = [
        ("1.0.0", "1.1.0"),
        ("1.0.0", "2.0.0"),
        ("2.0.0", "1.0.0"),
    ]
    
    for from_v, to_v in checks:
        result = engine.check_compatibility(from_v, to_v)
        print(f"   {from_v} -> {to_v}:")
        print(f"     Compatible: {result.compatible}")
        print(f"     Level: {result.level.value}")
    print()
    
    # 12. Generate Changelog
    print("12. GENERATE CHANGELOG:")
    print("-" * 40)
    
    changelog = engine.generate_changelog("bael-core")
    print(changelog[:500] + "..." if len(changelog) > 500 else changelog)
    print()
    
    # 13. Statistics
    print("13. STATISTICS:")
    print("-" * 40)
    
    stats = engine.stats
    print(f"   Total versions: {stats.total_versions}")
    print(f"   Total changes: {stats.total_changes}")
    print(f"   Breaking changes: {stats.breaking_changes}")
    print()
    
    # 14. Engine Summary
    print("14. ENGINE SUMMARY:")
    print("-" * 40)
    
    summary = engine.summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()
    
    print("=" * 70)
    print("DEMO COMPLETE - Versioning Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
