#!/usr/bin/env python3
"""
BAEL - Synchronization Engine
Data synchronization for agents.

Features:
- Conflict resolution
- Version vectors
- State synchronization
- Change detection
- Merge strategies
"""

import asyncio
import hashlib
import json
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class SyncState(Enum):
    """Synchronization states."""
    SYNCED = "synced"
    PENDING = "pending"
    SYNCING = "syncing"
    CONFLICT = "conflict"
    ERROR = "error"


class ConflictStrategy(Enum):
    """Conflict resolution strategies."""
    LAST_WRITE_WINS = "last_write_wins"
    FIRST_WRITE_WINS = "first_write_wins"
    MANUAL = "manual"
    MERGE = "merge"
    CUSTOM = "custom"


class ChangeType(Enum):
    """Change types."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MOVE = "move"


class SyncDirection(Enum):
    """Sync directions."""
    PUSH = "push"
    PULL = "pull"
    BIDIRECTIONAL = "bidirectional"


class SyncPriority(Enum):
    """Sync priorities."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    IMMEDIATE = "immediate"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class VersionVector:
    """Version vector for causality tracking."""
    vector: Dict[str, int] = field(default_factory=dict)

    def increment(self, node_id: str) -> None:
        """Increment version for node."""
        self.vector[node_id] = self.vector.get(node_id, 0) + 1

    def get(self, node_id: str) -> int:
        """Get version for node."""
        return self.vector.get(node_id, 0)

    def merge(self, other: "VersionVector") -> None:
        """Merge with another vector."""
        for node_id, version in other.vector.items():
            self.vector[node_id] = max(self.vector.get(node_id, 0), version)

    def dominates(self, other: "VersionVector") -> bool:
        """Check if this vector dominates another."""
        dominates_one = False

        for node_id, version in self.vector.items():
            other_version = other.vector.get(node_id, 0)
            if version < other_version:
                return False
            if version > other_version:
                dominates_one = True

        for node_id, version in other.vector.items():
            if node_id not in self.vector and version > 0:
                return False

        return dominates_one

    def concurrent(self, other: "VersionVector") -> bool:
        """Check if vectors are concurrent (conflict)."""
        return not self.dominates(other) and not other.dominates(self)

    def copy(self) -> "VersionVector":
        """Create a copy."""
        return VersionVector(vector=dict(self.vector))


@dataclass
class SyncItem:
    """An item to synchronize."""
    item_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    version: VersionVector = field(default_factory=VersionVector)
    checksum: str = ""
    modified_at: datetime = field(default_factory=datetime.now)
    modified_by: str = ""
    state: SyncState = SyncState.SYNCED

    def __post_init__(self):
        if not self.item_id:
            self.item_id = str(uuid.uuid4())[:8]
        if not self.checksum:
            self.checksum = self._compute_checksum()

    def _compute_checksum(self) -> str:
        """Compute data checksum."""
        data_str = json.dumps(self.data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()[:12]


@dataclass
class Change:
    """A change record."""
    change_id: str = ""
    item_id: str = ""
    change_type: ChangeType = ChangeType.UPDATE
    old_data: Optional[Dict[str, Any]] = None
    new_data: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)
    node_id: str = ""

    def __post_init__(self):
        if not self.change_id:
            self.change_id = str(uuid.uuid4())[:8]


@dataclass
class Conflict:
    """A sync conflict."""
    conflict_id: str = ""
    item_id: str = ""
    local_data: Dict[str, Any] = field(default_factory=dict)
    remote_data: Dict[str, Any] = field(default_factory=dict)
    local_version: VersionVector = field(default_factory=VersionVector)
    remote_version: VersionVector = field(default_factory=VersionVector)
    resolved: bool = False
    resolution: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if not self.conflict_id:
            self.conflict_id = str(uuid.uuid4())[:8]


@dataclass
class SyncSession:
    """A sync session."""
    session_id: str = ""
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    direction: SyncDirection = SyncDirection.BIDIRECTIONAL
    items_synced: int = 0
    conflicts: int = 0
    errors: int = 0
    status: str = "in_progress"

    def __post_init__(self):
        if not self.session_id:
            self.session_id = str(uuid.uuid4())[:8]


@dataclass
class SyncConfig:
    """Synchronization configuration."""
    node_id: str = ""
    conflict_strategy: ConflictStrategy = ConflictStrategy.LAST_WRITE_WINS
    sync_direction: SyncDirection = SyncDirection.BIDIRECTIONAL
    batch_size: int = 100
    auto_sync: bool = False
    sync_interval_seconds: float = 60.0

    def __post_init__(self):
        if not self.node_id:
            self.node_id = str(uuid.uuid4())[:8]


# =============================================================================
# CHANGE DETECTOR
# =============================================================================

class ChangeDetector:
    """Detect changes between versions."""

    def detect(
        self,
        old_data: Optional[Dict[str, Any]],
        new_data: Optional[Dict[str, Any]]
    ) -> Tuple[ChangeType, List[str]]:
        """Detect change type and changed fields."""
        if old_data is None and new_data is not None:
            return ChangeType.CREATE, list(new_data.keys())

        if old_data is not None and new_data is None:
            return ChangeType.DELETE, list(old_data.keys())

        if old_data is None and new_data is None:
            return ChangeType.UPDATE, []

        changed_fields = []

        for key in set(list(old_data.keys()) + list(new_data.keys())):
            old_val = old_data.get(key)
            new_val = new_data.get(key)

            if old_val != new_val:
                changed_fields.append(key)

        return ChangeType.UPDATE, changed_fields

    def compute_diff(
        self,
        old_data: Dict[str, Any],
        new_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compute diff between two data versions."""
        diff = {
            "added": {},
            "removed": {},
            "changed": {}
        }

        for key, value in new_data.items():
            if key not in old_data:
                diff["added"][key] = value
            elif old_data[key] != value:
                diff["changed"][key] = {"old": old_data[key], "new": value}

        for key in old_data:
            if key not in new_data:
                diff["removed"][key] = old_data[key]

        return diff

    def has_changes(
        self,
        old_data: Dict[str, Any],
        new_data: Dict[str, Any]
    ) -> bool:
        """Check if there are changes."""
        return old_data != new_data


# =============================================================================
# CONFLICT RESOLVER
# =============================================================================

class ConflictResolver:
    """Resolve sync conflicts."""

    def __init__(self, strategy: ConflictStrategy = ConflictStrategy.LAST_WRITE_WINS):
        self._strategy = strategy
        self._custom_resolver: Optional[Callable] = None

    def set_custom_resolver(self, resolver: Callable) -> None:
        """Set custom resolver function."""
        self._custom_resolver = resolver

    def resolve(
        self,
        conflict: Conflict,
        local_timestamp: datetime,
        remote_timestamp: datetime
    ) -> Dict[str, Any]:
        """Resolve a conflict."""
        if self._strategy == ConflictStrategy.LAST_WRITE_WINS:
            return self._last_write_wins(conflict, local_timestamp, remote_timestamp)

        elif self._strategy == ConflictStrategy.FIRST_WRITE_WINS:
            return self._first_write_wins(conflict, local_timestamp, remote_timestamp)

        elif self._strategy == ConflictStrategy.MERGE:
            return self._merge(conflict)

        elif self._strategy == ConflictStrategy.CUSTOM and self._custom_resolver:
            return self._custom_resolver(conflict)

        else:
            return conflict.local_data

    def _last_write_wins(
        self,
        conflict: Conflict,
        local_timestamp: datetime,
        remote_timestamp: datetime
    ) -> Dict[str, Any]:
        """Last write wins resolution."""
        if local_timestamp >= remote_timestamp:
            return conflict.local_data
        return conflict.remote_data

    def _first_write_wins(
        self,
        conflict: Conflict,
        local_timestamp: datetime,
        remote_timestamp: datetime
    ) -> Dict[str, Any]:
        """First write wins resolution."""
        if local_timestamp <= remote_timestamp:
            return conflict.local_data
        return conflict.remote_data

    def _merge(self, conflict: Conflict) -> Dict[str, Any]:
        """Merge both versions."""
        merged = dict(conflict.local_data)

        for key, value in conflict.remote_data.items():
            if key not in merged:
                merged[key] = value
            elif merged[key] != value:
                if isinstance(merged[key], list) and isinstance(value, list):
                    merged[key] = list(set(merged[key] + value))
                elif isinstance(merged[key], dict) and isinstance(value, dict):
                    merged[key] = {**merged[key], **value}
                else:
                    merged[f"{key}_local"] = merged[key]
                    merged[f"{key}_remote"] = value

        return merged


# =============================================================================
# SYNC STORE
# =============================================================================

class SyncStore:
    """Store synchronized items."""

    def __init__(self):
        self._items: Dict[str, SyncItem] = {}
        self._pending: Set[str] = set()

    def put(self, item: SyncItem) -> str:
        """Put an item."""
        self._items[item.item_id] = item

        if item.state != SyncState.SYNCED:
            self._pending.add(item.item_id)
        elif item.item_id in self._pending:
            self._pending.remove(item.item_id)

        return item.item_id

    def get(self, item_id: str) -> Optional[SyncItem]:
        """Get an item."""
        return self._items.get(item_id)

    def delete(self, item_id: str) -> bool:
        """Delete an item."""
        if item_id in self._items:
            del self._items[item_id]
            self._pending.discard(item_id)
            return True
        return False

    def get_pending(self) -> List[SyncItem]:
        """Get pending items."""
        return [self._items[id] for id in self._pending if id in self._items]

    def mark_synced(self, item_id: str) -> bool:
        """Mark item as synced."""
        item = self._items.get(item_id)
        if item:
            item.state = SyncState.SYNCED
            self._pending.discard(item_id)
            return True
        return False

    def mark_pending(self, item_id: str) -> bool:
        """Mark item as pending."""
        item = self._items.get(item_id)
        if item:
            item.state = SyncState.PENDING
            self._pending.add(item_id)
            return True
        return False

    def list_all(self) -> List[SyncItem]:
        """List all items."""
        return list(self._items.values())

    def count(self) -> int:
        """Count items."""
        return len(self._items)

    def pending_count(self) -> int:
        """Count pending items."""
        return len(self._pending)


# =============================================================================
# CHANGE LOG
# =============================================================================

class ChangeLog:
    """Log of changes."""

    def __init__(self, max_entries: int = 10000):
        self._changes: List[Change] = []
        self._max_entries = max_entries
        self._by_item: Dict[str, List[str]] = defaultdict(list)

    def record(self, change: Change) -> str:
        """Record a change."""
        self._changes.append(change)
        self._by_item[change.item_id].append(change.change_id)

        if len(self._changes) > self._max_entries:
            removed = self._changes.pop(0)
            self._by_item[removed.item_id].remove(removed.change_id)

        return change.change_id

    def get_changes_for_item(self, item_id: str) -> List[Change]:
        """Get changes for an item."""
        change_ids = self._by_item.get(item_id, [])
        return [c for c in self._changes if c.change_id in change_ids]

    def get_changes_since(self, timestamp: datetime) -> List[Change]:
        """Get changes since timestamp."""
        return [c for c in self._changes if c.timestamp > timestamp]

    def get_recent(self, limit: int = 100) -> List[Change]:
        """Get recent changes."""
        return self._changes[-limit:]

    def count(self) -> int:
        """Count changes."""
        return len(self._changes)

    def clear(self) -> int:
        """Clear log."""
        count = len(self._changes)
        self._changes.clear()
        self._by_item.clear()
        return count


# =============================================================================
# CONFLICT MANAGER
# =============================================================================

class ConflictManager:
    """Manage sync conflicts."""

    def __init__(self):
        self._conflicts: Dict[str, Conflict] = {}
        self._by_item: Dict[str, str] = {}

    def add(self, conflict: Conflict) -> str:
        """Add a conflict."""
        self._conflicts[conflict.conflict_id] = conflict
        self._by_item[conflict.item_id] = conflict.conflict_id
        return conflict.conflict_id

    def get(self, conflict_id: str) -> Optional[Conflict]:
        """Get conflict by ID."""
        return self._conflicts.get(conflict_id)

    def get_for_item(self, item_id: str) -> Optional[Conflict]:
        """Get conflict for item."""
        conflict_id = self._by_item.get(item_id)
        if conflict_id:
            return self._conflicts.get(conflict_id)
        return None

    def resolve(self, conflict_id: str, resolution: Dict[str, Any]) -> bool:
        """Resolve a conflict."""
        conflict = self._conflicts.get(conflict_id)
        if conflict:
            conflict.resolved = True
            conflict.resolution = resolution
            return True
        return False

    def get_unresolved(self) -> List[Conflict]:
        """Get unresolved conflicts."""
        return [c for c in self._conflicts.values() if not c.resolved]

    def count(self) -> int:
        """Count conflicts."""
        return len(self._conflicts)

    def unresolved_count(self) -> int:
        """Count unresolved conflicts."""
        return len(self.get_unresolved())


# =============================================================================
# SYNCHRONIZATION ENGINE
# =============================================================================

class SynchronizationEngine:
    """
    Synchronization Engine for BAEL.

    Data synchronization with conflict resolution.
    """

    def __init__(self, config: Optional[SyncConfig] = None):
        self._config = config or SyncConfig()

        self._store = SyncStore()
        self._changelog = ChangeLog()
        self._conflicts = ConflictManager()
        self._detector = ChangeDetector()
        self._resolver = ConflictResolver(self._config.conflict_strategy)

        self._sessions: List[SyncSession] = []
        self._callbacks: List[Callable] = []

    @property
    def node_id(self) -> str:
        """Get node ID."""
        return self._config.node_id

    # ----- Item Operations -----

    def put(
        self,
        item_id: str,
        data: Dict[str, Any],
        sync_immediately: bool = False
    ) -> SyncItem:
        """Put an item (create or update)."""
        existing = self._store.get(item_id)

        if existing:
            change_type = ChangeType.UPDATE
            old_data = existing.data
            version = existing.version.copy()
        else:
            change_type = ChangeType.CREATE
            old_data = None
            version = VersionVector()

        version.increment(self._config.node_id)

        item = SyncItem(
            item_id=item_id,
            data=data,
            version=version,
            modified_by=self._config.node_id,
            state=SyncState.PENDING if not sync_immediately else SyncState.SYNCED
        )

        self._store.put(item)

        change = Change(
            item_id=item_id,
            change_type=change_type,
            old_data=old_data,
            new_data=data,
            node_id=self._config.node_id
        )
        self._changelog.record(change)

        for callback in self._callbacks:
            callback(change)

        return item

    def get(self, item_id: str) -> Optional[SyncItem]:
        """Get an item."""
        return self._store.get(item_id)

    def delete(self, item_id: str) -> bool:
        """Delete an item."""
        item = self._store.get(item_id)

        if item:
            change = Change(
                item_id=item_id,
                change_type=ChangeType.DELETE,
                old_data=item.data,
                new_data=None,
                node_id=self._config.node_id
            )
            self._changelog.record(change)

            for callback in self._callbacks:
                callback(change)

        return self._store.delete(item_id)

    def list_all(self) -> List[SyncItem]:
        """List all items."""
        return self._store.list_all()

    def get_pending(self) -> List[SyncItem]:
        """Get pending items."""
        return self._store.get_pending()

    # ----- Synchronization -----

    def sync_with_remote(
        self,
        remote_items: List[SyncItem]
    ) -> SyncSession:
        """Synchronize with remote items."""
        session = SyncSession(direction=self._config.sync_direction)
        self._sessions.append(session)

        for remote_item in remote_items:
            local_item = self._store.get(remote_item.item_id)

            if local_item is None:
                self._store.put(remote_item)
                session.items_synced += 1

            elif local_item.version.concurrent(remote_item.version):
                conflict = Conflict(
                    item_id=remote_item.item_id,
                    local_data=local_item.data,
                    remote_data=remote_item.data,
                    local_version=local_item.version,
                    remote_version=remote_item.version
                )
                self._conflicts.add(conflict)
                session.conflicts += 1

                resolution = self._resolver.resolve(
                    conflict,
                    local_item.modified_at,
                    remote_item.modified_at
                )

                merged_version = local_item.version.copy()
                merged_version.merge(remote_item.version)
                merged_version.increment(self._config.node_id)

                resolved_item = SyncItem(
                    item_id=remote_item.item_id,
                    data=resolution,
                    version=merged_version,
                    modified_by=self._config.node_id,
                    state=SyncState.SYNCED
                )
                self._store.put(resolved_item)

                self._conflicts.resolve(conflict.conflict_id, resolution)
                session.items_synced += 1

            elif remote_item.version.dominates(local_item.version):
                self._store.put(remote_item)
                session.items_synced += 1

        session.completed_at = datetime.now()
        session.status = "completed"

        return session

    def get_changes_to_push(self) -> List[SyncItem]:
        """Get items that need to be pushed."""
        return self._store.get_pending()

    def mark_synced(self, item_ids: List[str]) -> int:
        """Mark items as synced."""
        count = 0
        for item_id in item_ids:
            if self._store.mark_synced(item_id):
                count += 1
        return count

    # ----- Conflict Management -----

    def get_conflicts(self) -> List[Conflict]:
        """Get all conflicts."""
        return self._conflicts.get_unresolved()

    def get_conflict(self, conflict_id: str) -> Optional[Conflict]:
        """Get conflict by ID."""
        return self._conflicts.get(conflict_id)

    def resolve_conflict(
        self,
        conflict_id: str,
        resolution: Dict[str, Any]
    ) -> bool:
        """Manually resolve a conflict."""
        conflict = self._conflicts.get(conflict_id)

        if not conflict:
            return False

        local_item = self._store.get(conflict.item_id)

        if local_item:
            local_item.version.merge(conflict.remote_version)
            local_item.version.increment(self._config.node_id)

        resolved_item = SyncItem(
            item_id=conflict.item_id,
            data=resolution,
            version=local_item.version if local_item else VersionVector(),
            modified_by=self._config.node_id,
            state=SyncState.SYNCED
        )
        self._store.put(resolved_item)

        return self._conflicts.resolve(conflict_id, resolution)

    # ----- Change Detection -----

    def detect_changes(
        self,
        old_data: Optional[Dict[str, Any]],
        new_data: Optional[Dict[str, Any]]
    ) -> Tuple[ChangeType, List[str]]:
        """Detect changes between versions."""
        return self._detector.detect(old_data, new_data)

    def compute_diff(
        self,
        old_data: Dict[str, Any],
        new_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compute diff between versions."""
        return self._detector.compute_diff(old_data, new_data)

    # ----- Change Log -----

    def get_changes_since(self, timestamp: datetime) -> List[Change]:
        """Get changes since timestamp."""
        return self._changelog.get_changes_since(timestamp)

    def get_recent_changes(self, limit: int = 100) -> List[Change]:
        """Get recent changes."""
        return self._changelog.get_recent(limit)

    def get_item_history(self, item_id: str) -> List[Change]:
        """Get change history for an item."""
        return self._changelog.get_changes_for_item(item_id)

    # ----- Callbacks -----

    def on_change(self, callback: Callable) -> None:
        """Add change callback."""
        self._callbacks.append(callback)

    # ----- Sessions -----

    def get_sessions(self, limit: int = 10) -> List[SyncSession]:
        """Get sync sessions."""
        return self._sessions[-limit:]

    def get_last_session(self) -> Optional[SyncSession]:
        """Get last sync session."""
        return self._sessions[-1] if self._sessions else None

    # ----- Configuration -----

    def set_conflict_strategy(self, strategy: ConflictStrategy) -> None:
        """Set conflict resolution strategy."""
        self._config.conflict_strategy = strategy
        self._resolver = ConflictResolver(strategy)

    def set_custom_resolver(self, resolver: Callable) -> None:
        """Set custom conflict resolver."""
        self._config.conflict_strategy = ConflictStrategy.CUSTOM
        self._resolver = ConflictResolver(ConflictStrategy.CUSTOM)
        self._resolver.set_custom_resolver(resolver)

    # ----- Stats -----

    def stats(self) -> Dict[str, Any]:
        """Get sync stats."""
        return {
            "total_items": self._store.count(),
            "pending_items": self._store.pending_count(),
            "total_changes": self._changelog.count(),
            "unresolved_conflicts": self._conflicts.unresolved_count(),
            "total_sessions": len(self._sessions)
        }

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "node_id": self._config.node_id,
            "items": self._store.count(),
            "pending": self._store.pending_count(),
            "conflicts": self._conflicts.unresolved_count(),
            "strategy": self._config.conflict_strategy.value,
            "direction": self._config.sync_direction.value
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Synchronization Engine."""
    print("=" * 70)
    print("BAEL - SYNCHRONIZATION ENGINE DEMO")
    print("Data Synchronization & Conflict Resolution")
    print("=" * 70)
    print()

    engine = SynchronizationEngine()

    # 1. Put Items
    print("1. PUT ITEMS:")
    print("-" * 40)

    item1 = engine.put("user:1", {"name": "Alice", "email": "alice@example.com"})
    print(f"   Put: {item1.item_id} - version: {item1.version.vector}")

    item2 = engine.put("user:2", {"name": "Bob", "email": "bob@example.com"})
    print(f"   Put: {item2.item_id} - version: {item2.version.vector}")

    item3 = engine.put("config:app", {"theme": "dark", "language": "en"})
    print(f"   Put: {item3.item_id} - version: {item3.version.vector}")
    print()

    # 2. Get Items
    print("2. GET ITEMS:")
    print("-" * 40)

    for item_id in ["user:1", "user:2", "config:app"]:
        item = engine.get(item_id)
        print(f"   {item_id}: {item.data}")
    print()

    # 3. Update Items
    print("3. UPDATE ITEMS:")
    print("-" * 40)

    item1 = engine.put("user:1", {"name": "Alice Smith", "email": "alice.smith@example.com"})
    print(f"   Updated: {item1.item_id}")
    print(f"   New data: {item1.data}")
    print(f"   Version: {item1.version.vector}")
    print()

    # 4. Pending Items
    print("4. PENDING ITEMS:")
    print("-" * 40)

    pending = engine.get_pending()
    print(f"   Pending items: {len(pending)}")
    for item in pending:
        print(f"   - {item.item_id}: {item.state.value}")
    print()

    # 5. Sync with Remote
    print("5. SYNC WITH REMOTE:")
    print("-" * 40)

    remote_items = [
        SyncItem(
            item_id="user:3",
            data={"name": "Charlie", "email": "charlie@example.com"},
            version=VersionVector({"remote": 1}),
            modified_by="remote"
        ),
        SyncItem(
            item_id="config:remote",
            data={"setting": "value"},
            version=VersionVector({"remote": 1}),
            modified_by="remote"
        )
    ]

    session = engine.sync_with_remote(remote_items)
    print(f"   Session: {session.session_id}")
    print(f"   Items synced: {session.items_synced}")
    print(f"   Conflicts: {session.conflicts}")
    print(f"   Status: {session.status}")
    print()

    # 6. List All Items
    print("6. ALL ITEMS AFTER SYNC:")
    print("-" * 40)

    for item in engine.list_all():
        print(f"   {item.item_id}: {item.data}")
    print()

    # 7. Create Conflict
    print("7. CREATE CONFLICT:")
    print("-" * 40)

    local_config = engine.get("config:app")

    conflicting_remote = SyncItem(
        item_id="config:app",
        data={"theme": "light", "language": "fr"},
        version=VersionVector({"remote": 2}),
        modified_by="remote"
    )

    session = engine.sync_with_remote([conflicting_remote])
    print(f"   Conflicts detected: {session.conflicts}")

    conflicts = engine.get_conflicts()
    print(f"   Unresolved conflicts: {len(conflicts)}")

    if conflicts:
        c = conflicts[0]
        print(f"   Conflict: {c.conflict_id}")
        print(f"   Local: {c.local_data}")
        print(f"   Remote: {c.remote_data}")
    print()

    # 8. Check Conflict Resolution
    print("8. CONFLICT RESOLUTION (LAST_WRITE_WINS):")
    print("-" * 40)

    resolved_item = engine.get("config:app")
    print(f"   Resolved data: {resolved_item.data}")
    print(f"   (Default strategy: last_write_wins)")
    print()

    # 9. Manual Conflict Resolution
    print("9. MANUAL CONFLICT RESOLUTION:")
    print("-" * 40)

    engine.put("settings:manual", {"option1": "a", "option2": "b"})

    manual_conflict_remote = SyncItem(
        item_id="settings:manual",
        data={"option1": "x", "option3": "c"},
        version=VersionVector({"remote": 3}),
        modified_by="remote"
    )

    engine.sync_with_remote([manual_conflict_remote])

    conflicts = engine.get_conflicts()
    if conflicts:
        conflict = conflicts[0]

        custom_resolution = {"option1": "merged", "option2": "b", "option3": "c"}
        engine.resolve_conflict(conflict.conflict_id, custom_resolution)

        resolved = engine.get(conflict.item_id)
        print(f"   Manually resolved: {resolved.data}")
    print()

    # 10. Change Detection
    print("10. CHANGE DETECTION:")
    print("-" * 40)

    old = {"name": "Test", "value": 1}
    new = {"name": "Test Updated", "value": 1, "extra": True}

    change_type, changed_fields = engine.detect_changes(old, new)
    print(f"   Change type: {change_type.value}")
    print(f"   Changed fields: {changed_fields}")

    diff = engine.compute_diff(old, new)
    print(f"   Diff: {diff}")
    print()

    # 11. Change Log
    print("11. CHANGE LOG:")
    print("-" * 40)

    changes = engine.get_recent_changes(5)
    print(f"   Recent changes: {len(changes)}")
    for change in changes[:3]:
        print(f"   - {change.item_id}: {change.change_type.value}")
    print()

    # 12. Item History
    print("12. ITEM HISTORY:")
    print("-" * 40)

    history = engine.get_item_history("user:1")
    print(f"   History for user:1: {len(history)} changes")
    for change in history:
        print(f"   - {change.change_type.value} at {change.timestamp}")
    print()

    # 13. Change Callback
    print("13. CHANGE CALLBACK:")
    print("-" * 40)

    changes_recorded = []

    def on_change(change: Change):
        changes_recorded.append(change)
        print(f"   [Callback] Change: {change.item_id}")

    engine.on_change(on_change)

    engine.put("callback:test", {"triggered": True})

    print(f"   Callbacks triggered: {len(changes_recorded)}")
    print()

    # 14. Sync Sessions
    print("14. SYNC SESSIONS:")
    print("-" * 40)

    sessions = engine.get_sessions()
    print(f"   Total sessions: {len(sessions)}")
    for sess in sessions[-2:]:
        print(f"   - {sess.session_id}: {sess.items_synced} synced, {sess.conflicts} conflicts")
    print()

    # 15. Version Vectors
    print("15. VERSION VECTORS:")
    print("-" * 40)

    v1 = VersionVector({"node_a": 2, "node_b": 1})
    v2 = VersionVector({"node_a": 1, "node_b": 2})

    print(f"   V1: {v1.vector}")
    print(f"   V2: {v2.vector}")
    print(f"   V1 dominates V2: {v1.dominates(v2)}")
    print(f"   V2 dominates V1: {v2.dominates(v1)}")
    print(f"   Concurrent: {v1.concurrent(v2)}")

    v1.merge(v2)
    print(f"   Merged: {v1.vector}")
    print()

    # 16. Statistics
    print("16. STATISTICS:")
    print("-" * 40)

    stats = engine.stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()

    # 17. Summary
    print("17. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Synchronization Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
