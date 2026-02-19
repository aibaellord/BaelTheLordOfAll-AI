"""
🔄 VERSION CONTROL 🔄
=====================
Version management.

Features:
- Capability versioning
- Changelogs
- Rollback management
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid
import hashlib


@dataclass
class ChangeLog:
    """Log of changes in a version"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Change type
    change_type: str = ""  # added, removed, modified, fixed

    # What changed
    component: str = ""
    description: str = ""

    # Impact
    breaking: bool = False

    # Related
    related_modifications: List[str] = field(default_factory=list)


@dataclass
class CapabilitySnapshot:
    """Snapshot of capability state"""
    capability_id: str = ""
    name: str = ""
    proficiency: float = 0.0
    level: str = ""

    # Configuration at snapshot time
    configuration: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Version:
    """A version of the system"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Version number (semver)
    major: int = 1
    minor: int = 0
    patch: int = 0

    # Label
    label: str = ""  # alpha, beta, stable

    # Description
    description: str = ""

    # Changes
    changes: List[ChangeLog] = field(default_factory=list)

    # Capability snapshots
    capability_snapshots: List[CapabilitySnapshot] = field(default_factory=list)

    # State hash
    state_hash: str = ""

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "system"

    # Parent version
    parent_version_id: Optional[str] = None

    @property
    def version_string(self) -> str:
        """Get version string"""
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.label:
            base += f"-{self.label}"
        return base

    def compute_hash(self, data: Dict[str, Any]) -> str:
        """Compute state hash"""
        content = str(sorted(data.items()))
        self.state_hash = hashlib.sha256(content.encode()).hexdigest()[:32]
        return self.state_hash

    def has_breaking_changes(self) -> bool:
        """Check for breaking changes"""
        return any(c.breaking for c in self.changes)

    def increment_major(self):
        """Increment major version"""
        self.major += 1
        self.minor = 0
        self.patch = 0

    def increment_minor(self):
        """Increment minor version"""
        self.minor += 1
        self.patch = 0

    def increment_patch(self):
        """Increment patch version"""
        self.patch += 1


class VersionManager:
    """
    Manages system versions.
    """

    def __init__(self):
        self.versions: Dict[str, Version] = {}
        self.current_version_id: Optional[str] = None

        # Version history (ordered)
        self.version_history: List[str] = []

    @property
    def current_version(self) -> Optional[Version]:
        """Get current version"""
        if self.current_version_id:
            return self.versions.get(self.current_version_id)
        return None

    def create_version(
        self,
        changes: List[ChangeLog] = None,
        description: str = "",
        auto_increment: bool = True
    ) -> Version:
        """Create new version"""
        version = Version(description=description)

        if self.current_version and auto_increment:
            # Copy version numbers
            version.major = self.current_version.major
            version.minor = self.current_version.minor
            version.patch = self.current_version.patch
            version.parent_version_id = self.current_version_id

            # Add changes
            if changes:
                version.changes = changes

            # Auto-increment based on changes
            if version.has_breaking_changes():
                version.increment_major()
            elif any(c.change_type == "added" for c in version.changes):
                version.increment_minor()
            else:
                version.increment_patch()

        self.versions[version.id] = version
        self.version_history.append(version.id)
        self.current_version_id = version.id

        return version

    def snapshot_capabilities(
        self,
        capabilities: Dict[str, Any]
    ) -> List[CapabilitySnapshot]:
        """Create capability snapshots"""
        snapshots = []

        for cap_id, cap in capabilities.items():
            snapshot = CapabilitySnapshot(
                capability_id=cap_id,
                name=getattr(cap, 'name', ''),
                proficiency=getattr(cap, 'proficiency', 0.0),
                level=str(getattr(cap, 'level', '')),
                configuration={}
            )
            snapshots.append(snapshot)

        return snapshots

    def get_version(self, version_string: str) -> Optional[Version]:
        """Get version by string"""
        for version in self.versions.values():
            if version.version_string == version_string:
                return version
        return None

    def get_history(self) -> List[Version]:
        """Get version history"""
        return [self.versions[vid] for vid in self.version_history if vid in self.versions]

    def compare_versions(
        self,
        version1_id: str,
        version2_id: str
    ) -> Dict[str, Any]:
        """Compare two versions"""
        v1 = self.versions.get(version1_id)
        v2 = self.versions.get(version2_id)

        if not v1 or not v2:
            return {}

        # Compare capability snapshots
        v1_caps = {s.capability_id: s for s in v1.capability_snapshots}
        v2_caps = {s.capability_id: s for s in v2.capability_snapshots}

        added = set(v2_caps.keys()) - set(v1_caps.keys())
        removed = set(v1_caps.keys()) - set(v2_caps.keys())
        common = set(v1_caps.keys()) & set(v2_caps.keys())

        changed = []
        for cap_id in common:
            if v1_caps[cap_id].proficiency != v2_caps[cap_id].proficiency:
                changed.append({
                    'capability': cap_id,
                    'old_proficiency': v1_caps[cap_id].proficiency,
                    'new_proficiency': v2_caps[cap_id].proficiency
                })

        return {
            'from_version': v1.version_string,
            'to_version': v2.version_string,
            'capabilities_added': list(added),
            'capabilities_removed': list(removed),
            'capabilities_changed': changed,
            'changes': [c.description for c in v2.changes]
        }


class RollbackManager:
    """
    Manages rollbacks.
    """

    def __init__(self, version_manager: VersionManager):
        self.version_manager = version_manager

        # Rollback history
        self.rollback_history: List[Dict[str, Any]] = []

    def can_rollback(self) -> bool:
        """Check if rollback is possible"""
        if not self.version_manager.current_version:
            return False
        return self.version_manager.current_version.parent_version_id is not None

    def rollback(self, target_version_id: str = None) -> bool:
        """Rollback to previous version"""
        if not self.can_rollback():
            return False

        current = self.version_manager.current_version

        # Determine target
        if target_version_id:
            target_id = target_version_id
        else:
            target_id = current.parent_version_id

        if not target_id or target_id not in self.version_manager.versions:
            return False

        # Record rollback
        self.rollback_history.append({
            'from_version': current.id,
            'to_version': target_id,
            'timestamp': datetime.now().isoformat(),
            'reason': 'manual_rollback'
        })

        # Set current version
        self.version_manager.current_version_id = target_id

        return True

    def rollback_to_stable(self) -> bool:
        """Rollback to last stable version"""
        for vid in reversed(self.version_manager.version_history):
            version = self.version_manager.versions.get(vid)
            if version and version.label == "stable":
                return self.rollback(vid)
        return False

    def get_rollback_history(self) -> List[Dict[str, Any]]:
        """Get rollback history"""
        return self.rollback_history


# Export all
__all__ = [
    'ChangeLog',
    'CapabilitySnapshot',
    'Version',
    'VersionManager',
    'RollbackManager',
]
