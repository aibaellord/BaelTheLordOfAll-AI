#!/usr/bin/env python3
"""
BAEL - Audit Logger System
Comprehensive audit logging for compliance and security.

Features:
- Immutable audit trail
- Structured audit events
- Tamper detection
- Search and filtering
- Retention policies
- Export capabilities
- Compliance reporting
- Real-time streaming
- Event correlation
- Digital signatures
"""

import asyncio
import base64
import hashlib
import json
import logging
import os
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import (Any, Awaitable, Callable, Dict, Generator, List, Optional,
                    Set, Tuple, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class AuditAction(Enum):
    """Audit action types."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    FAILED_LOGIN = "failed_login"
    ACCESS_DENIED = "access_denied"
    PERMISSION_CHANGE = "permission_change"
    CONFIGURATION_CHANGE = "configuration_change"
    DATA_EXPORT = "data_export"
    DATA_IMPORT = "data_import"
    SYSTEM_EVENT = "system_event"
    SECURITY_EVENT = "security_event"
    CUSTOM = "custom"


class AuditSeverity(Enum):
    """Audit event severity."""
    DEBUG = 10
    INFO = 20
    NOTICE = 25
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class AuditStatus(Enum):
    """Audit event status."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    PENDING = "pending"


class RetentionPolicy(Enum):
    """Audit retention policies."""
    KEEP_ALL = "keep_all"
    DAYS_30 = "days_30"
    DAYS_90 = "days_90"
    DAYS_365 = "days_365"
    YEARS_7 = "years_7"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class AuditActor:
    """Actor (user/system) performing the action."""
    actor_id: str
    actor_type: str = "user"  # user, system, service, api
    name: str = ""
    email: str = ""
    ip_address: str = ""
    user_agent: str = ""
    session_id: str = ""
    roles: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditResource:
    """Resource being acted upon."""
    resource_id: str
    resource_type: str
    name: str = ""
    path: str = ""
    parent_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditEvent:
    """Audit event record."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    action: AuditAction = AuditAction.CUSTOM
    severity: AuditSeverity = AuditSeverity.INFO
    status: AuditStatus = AuditStatus.SUCCESS
    actor: Optional[AuditActor] = None
    resource: Optional[AuditResource] = None
    description: str = ""
    old_value: Any = None
    new_value: Any = None
    changes: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    correlation_id: str = ""
    parent_event_id: str = ""
    hash: str = ""
    signature: str = ""

    @property
    def datetime(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "datetime": self.datetime.isoformat(),
            "action": self.action.value,
            "severity": self.severity.value,
            "status": self.status.value,
            "actor": {
                "id": self.actor.actor_id,
                "type": self.actor.actor_type,
                "name": self.actor.name,
                "ip": self.actor.ip_address
            } if self.actor else None,
            "resource": {
                "id": self.resource.resource_id,
                "type": self.resource.resource_type,
                "name": self.resource.name
            } if self.resource else None,
            "description": self.description,
            "changes": self.changes,
            "tags": self.tags,
            "metadata": self.metadata,
            "correlation_id": self.correlation_id,
            "hash": self.hash
        }


@dataclass
class AuditQuery:
    """Audit log query parameters."""
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    actions: List[AuditAction] = field(default_factory=list)
    severities: List[AuditSeverity] = field(default_factory=list)
    statuses: List[AuditStatus] = field(default_factory=list)
    actor_ids: List[str] = field(default_factory=list)
    resource_ids: List[str] = field(default_factory=list)
    resource_types: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    text_search: str = ""
    correlation_id: str = ""
    limit: int = 100
    offset: int = 0
    order_desc: bool = True


@dataclass
class AuditStats:
    """Audit statistics."""
    total_events: int = 0
    events_by_action: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    events_by_severity: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    events_by_status: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    events_by_actor: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    events_by_resource_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    first_event_time: Optional[float] = None
    last_event_time: Optional[float] = None


# =============================================================================
# STORAGE BACKENDS
# =============================================================================

class AuditStorage(ABC):
    """Abstract audit storage backend."""

    @abstractmethod
    async def store(self, event: AuditEvent) -> bool:
        """Store an audit event."""
        pass

    @abstractmethod
    async def query(self, query: AuditQuery) -> List[AuditEvent]:
        """Query audit events."""
        pass

    @abstractmethod
    async def get_by_id(self, event_id: str) -> Optional[AuditEvent]:
        """Get event by ID."""
        pass

    @abstractmethod
    async def get_stats(self) -> AuditStats:
        """Get audit statistics."""
        pass

    async def delete_before(self, timestamp: float) -> int:
        """Delete events before timestamp (for retention)."""
        return 0


class InMemoryAuditStorage(AuditStorage):
    """In-memory audit storage."""

    def __init__(self, max_events: int = 100000):
        self.max_events = max_events
        self.events: deque = deque(maxlen=max_events)
        self.index: Dict[str, AuditEvent] = {}
        self._lock = asyncio.Lock()

    async def store(self, event: AuditEvent) -> bool:
        async with self._lock:
            self.events.append(event)
            self.index[event.event_id] = event

            # Cleanup old index entries
            if len(self.index) > self.max_events:
                old_ids = list(self.index.keys())[:-self.max_events]
                for eid in old_ids:
                    self.index.pop(eid, None)

            return True

    async def query(self, query: AuditQuery) -> List[AuditEvent]:
        results = list(self.events)

        # Filter by time
        if query.start_time:
            results = [e for e in results if e.timestamp >= query.start_time]

        if query.end_time:
            results = [e for e in results if e.timestamp <= query.end_time]

        # Filter by action
        if query.actions:
            results = [e for e in results if e.action in query.actions]

        # Filter by severity
        if query.severities:
            results = [e for e in results if e.severity in query.severities]

        # Filter by status
        if query.statuses:
            results = [e for e in results if e.status in query.statuses]

        # Filter by actor
        if query.actor_ids:
            results = [
                e for e in results
                if e.actor and e.actor.actor_id in query.actor_ids
            ]

        # Filter by resource
        if query.resource_ids:
            results = [
                e for e in results
                if e.resource and e.resource.resource_id in query.resource_ids
            ]

        if query.resource_types:
            results = [
                e for e in results
                if e.resource and e.resource.resource_type in query.resource_types
            ]

        # Filter by tags
        if query.tags:
            results = [
                e for e in results
                if any(t in e.tags for t in query.tags)
            ]

        # Filter by correlation
        if query.correlation_id:
            results = [
                e for e in results
                if e.correlation_id == query.correlation_id
            ]

        # Text search
        if query.text_search:
            search = query.text_search.lower()
            results = [
                e for e in results
                if search in e.description.lower()
            ]

        # Sort
        results.sort(
            key=lambda e: e.timestamp,
            reverse=query.order_desc
        )

        # Pagination
        return results[query.offset:query.offset + query.limit]

    async def get_by_id(self, event_id: str) -> Optional[AuditEvent]:
        return self.index.get(event_id)

    async def get_stats(self) -> AuditStats:
        stats = AuditStats()

        for event in self.events:
            stats.total_events += 1
            stats.events_by_action[event.action.value] += 1
            stats.events_by_severity[event.severity.name] += 1
            stats.events_by_status[event.status.value] += 1

            if event.actor:
                stats.events_by_actor[event.actor.actor_id] += 1

            if event.resource:
                stats.events_by_resource_type[event.resource.resource_type] += 1

            if stats.first_event_time is None:
                stats.first_event_time = event.timestamp
            stats.last_event_time = event.timestamp

        return stats

    async def delete_before(self, timestamp: float) -> int:
        async with self._lock:
            original = len(self.events)

            self.events = deque(
                (e for e in self.events if e.timestamp >= timestamp),
                maxlen=self.max_events
            )

            # Rebuild index
            self.index = {e.event_id: e for e in self.events}

            return original - len(self.events)


class FileAuditStorage(AuditStorage):
    """File-based audit storage."""

    def __init__(self, directory: str, rotate_size: int = 10 * 1024 * 1024):
        self.directory = Path(directory)
        self.rotate_size = rotate_size
        self.current_file: Optional[Path] = None
        self._lock = asyncio.Lock()

        self.directory.mkdir(parents=True, exist_ok=True)

    def _get_current_file(self) -> Path:
        """Get current log file."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        return self.directory / f"audit_{date_str}.jsonl"

    async def store(self, event: AuditEvent) -> bool:
        async with self._lock:
            try:
                file_path = self._get_current_file()

                with open(file_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(event.to_dict(), default=str) + "\n")

                return True
            except Exception as e:
                logger.error(f"Failed to store audit event: {e}")
                return False

    async def query(self, query: AuditQuery) -> List[AuditEvent]:
        # For file storage, we'd need to scan files
        # This is a simplified implementation
        return []

    async def get_by_id(self, event_id: str) -> Optional[AuditEvent]:
        return None

    async def get_stats(self) -> AuditStats:
        stats = AuditStats()

        for file_path in self.directory.glob("audit_*.jsonl"):
            with open(file_path, 'r') as f:
                for line in f:
                    stats.total_events += 1

        return stats


# =============================================================================
# INTEGRITY MANAGER
# =============================================================================

class IntegrityManager:
    """Manages audit event integrity."""

    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or os.urandom(32).hex()
        self._previous_hash = ""

    def compute_hash(self, event: AuditEvent) -> str:
        """Compute hash for an event."""
        data = {
            "event_id": event.event_id,
            "timestamp": event.timestamp,
            "action": event.action.value,
            "description": event.description,
            "actor_id": event.actor.actor_id if event.actor else "",
            "resource_id": event.resource.resource_id if event.resource else "",
            "previous_hash": self._previous_hash
        }

        content = json.dumps(data, sort_keys=True)
        hash_value = hashlib.sha256(content.encode()).hexdigest()

        self._previous_hash = hash_value
        return hash_value

    def compute_signature(self, event: AuditEvent) -> str:
        """Compute digital signature for event."""
        content = f"{event.event_id}:{event.timestamp}:{event.hash}"

        signature = hashlib.sha256(
            (self.secret_key + content).encode()
        ).hexdigest()

        return signature

    def verify_hash(self, event: AuditEvent, expected_hash: str) -> bool:
        """Verify event hash."""
        return event.hash == expected_hash

    def verify_signature(self, event: AuditEvent) -> bool:
        """Verify event signature."""
        content = f"{event.event_id}:{event.timestamp}:{event.hash}"

        expected = hashlib.sha256(
            (self.secret_key + content).encode()
        ).hexdigest()

        return event.signature == expected


# =============================================================================
# AUDIT LOGGER
# =============================================================================

class AuditLogger:
    """
    Comprehensive Audit Logger for BAEL.
    """

    def __init__(
        self,
        storage: AuditStorage = None,
        retention: RetentionPolicy = RetentionPolicy.DAYS_90
    ):
        self.storage = storage or InMemoryAuditStorage()
        self.retention = retention
        self.integrity = IntegrityManager()

        # Event listeners
        self._listeners: List[Callable[[AuditEvent], Awaitable[None]]] = []

        # Correlation context
        self._correlation_id: Optional[str] = None

    def set_correlation_id(self, correlation_id: str) -> None:
        """Set correlation ID for subsequent events."""
        self._correlation_id = correlation_id

    def clear_correlation_id(self) -> None:
        """Clear correlation ID."""
        self._correlation_id = None

    def on_event(
        self,
        listener: Callable[[AuditEvent], Awaitable[None]]
    ) -> None:
        """Register event listener."""
        self._listeners.append(listener)

    async def log(
        self,
        action: AuditAction,
        actor: AuditActor = None,
        resource: AuditResource = None,
        description: str = "",
        severity: AuditSeverity = AuditSeverity.INFO,
        status: AuditStatus = AuditStatus.SUCCESS,
        old_value: Any = None,
        new_value: Any = None,
        changes: Dict[str, Any] = None,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> AuditEvent:
        """Log an audit event."""
        event = AuditEvent(
            action=action,
            severity=severity,
            status=status,
            actor=actor,
            resource=resource,
            description=description,
            old_value=old_value,
            new_value=new_value,
            changes=changes or {},
            tags=tags or [],
            metadata=metadata or {},
            correlation_id=self._correlation_id or ""
        )

        # Compute integrity
        event.hash = self.integrity.compute_hash(event)
        event.signature = self.integrity.compute_signature(event)

        # Store
        await self.storage.store(event)

        # Notify listeners
        for listener in self._listeners:
            try:
                await listener(event)
            except Exception as e:
                logger.error(f"Audit listener error: {e}")

        return event

    async def log_login(
        self,
        actor: AuditActor,
        success: bool = True,
        method: str = "password"
    ) -> AuditEvent:
        """Log a login event."""
        return await self.log(
            action=AuditAction.LOGIN if success else AuditAction.FAILED_LOGIN,
            actor=actor,
            description=f"User login via {method}",
            status=AuditStatus.SUCCESS if success else AuditStatus.FAILURE,
            severity=AuditSeverity.INFO if success else AuditSeverity.WARNING,
            metadata={"method": method}
        )

    async def log_logout(self, actor: AuditActor) -> AuditEvent:
        """Log a logout event."""
        return await self.log(
            action=AuditAction.LOGOUT,
            actor=actor,
            description="User logout",
            status=AuditStatus.SUCCESS
        )

    async def log_access_denied(
        self,
        actor: AuditActor,
        resource: AuditResource,
        reason: str = ""
    ) -> AuditEvent:
        """Log an access denied event."""
        return await self.log(
            action=AuditAction.ACCESS_DENIED,
            actor=actor,
            resource=resource,
            description=f"Access denied: {reason}",
            severity=AuditSeverity.WARNING,
            status=AuditStatus.FAILURE
        )

    async def log_data_change(
        self,
        action: AuditAction,
        actor: AuditActor,
        resource: AuditResource,
        old_value: Any = None,
        new_value: Any = None,
        changes: Dict[str, Any] = None
    ) -> AuditEvent:
        """Log a data change event."""
        return await self.log(
            action=action,
            actor=actor,
            resource=resource,
            description=f"{action.value} on {resource.resource_type}/{resource.resource_id}",
            old_value=old_value,
            new_value=new_value,
            changes=changes
        )

    async def query(self, query: AuditQuery) -> List[AuditEvent]:
        """Query audit events."""
        return await self.storage.query(query)

    async def get_event(self, event_id: str) -> Optional[AuditEvent]:
        """Get event by ID."""
        return await self.storage.get_by_id(event_id)

    async def get_stats(self) -> AuditStats:
        """Get audit statistics."""
        return await self.storage.get_stats()

    async def apply_retention(self) -> int:
        """Apply retention policy."""
        retention_days = {
            RetentionPolicy.KEEP_ALL: 0,
            RetentionPolicy.DAYS_30: 30,
            RetentionPolicy.DAYS_90: 90,
            RetentionPolicy.DAYS_365: 365,
            RetentionPolicy.YEARS_7: 365 * 7
        }

        days = retention_days.get(self.retention, 90)

        if days == 0:
            return 0

        cutoff = time.time() - (days * 86400)
        return await self.storage.delete_before(cutoff)

    async def export(
        self,
        query: AuditQuery,
        format: str = "json"
    ) -> str:
        """Export audit events."""
        events = await self.query(query)

        if format == "json":
            return json.dumps(
                [e.to_dict() for e in events],
                indent=2,
                default=str
            )

        # CSV format
        if format == "csv":
            lines = ["timestamp,action,actor,resource,description,status"]

            for event in events:
                actor_id = event.actor.actor_id if event.actor else ""
                resource_id = event.resource.resource_id if event.resource else ""

                lines.append(
                    f"{event.datetime.isoformat()},"
                    f"{event.action.value},"
                    f"{actor_id},"
                    f"{resource_id},"
                    f'"{event.description}",'
                    f"{event.status.value}"
                )

            return "\n".join(lines)

        return ""

    def verify_integrity(self, event: AuditEvent) -> bool:
        """Verify event integrity."""
        return self.integrity.verify_signature(event)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Audit Logger System."""
    print("=" * 70)
    print("BAEL - AUDIT LOGGER SYSTEM DEMO")
    print("Comprehensive Audit & Compliance Logging")
    print("=" * 70)
    print()

    audit = AuditLogger()

    # 1. Create Actors
    print("1. CREATE ACTORS:")
    print("-" * 40)

    admin = AuditActor(
        actor_id="admin-001",
        actor_type="user",
        name="Admin User",
        email="admin@bael.ai",
        ip_address="192.168.1.100",
        roles=["admin", "superuser"]
    )

    user = AuditActor(
        actor_id="user-001",
        actor_type="user",
        name="Regular User",
        email="user@bael.ai",
        ip_address="192.168.1.101"
    )

    system = AuditActor(
        actor_id="system",
        actor_type="system",
        name="BAEL System"
    )

    print(f"   Created: {admin.name} ({admin.actor_id})")
    print(f"   Created: {user.name} ({user.actor_id})")
    print(f"   Created: {system.name} ({system.actor_id})")
    print()

    # 2. Create Resources
    print("2. CREATE RESOURCES:")
    print("-" * 40)

    config_resource = AuditResource(
        resource_id="config-001",
        resource_type="configuration",
        name="System Configuration"
    )

    user_resource = AuditResource(
        resource_id="user-002",
        resource_type="user",
        name="Target User Account"
    )

    print(f"   Created: {config_resource.name}")
    print(f"   Created: {user_resource.name}")
    print()

    # 3. Log Login Events
    print("3. LOG LOGIN EVENTS:")
    print("-" * 40)

    event = await audit.log_login(admin, success=True, method="oauth")
    print(f"   Login success: {event.event_id[:8]}")

    event = await audit.log_login(user, success=False, method="password")
    print(f"   Login failed: {event.event_id[:8]}")

    event = await audit.log_login(user, success=True, method="password")
    print(f"   Login success: {event.event_id[:8]}")
    print()

    # 4. Log Data Changes
    print("4. LOG DATA CHANGES:")
    print("-" * 40)

    event = await audit.log_data_change(
        action=AuditAction.UPDATE,
        actor=admin,
        resource=config_resource,
        old_value={"debug": False},
        new_value={"debug": True},
        changes={"debug": {"old": False, "new": True}}
    )
    print(f"   Config change: {event.event_id[:8]}")

    event = await audit.log_data_change(
        action=AuditAction.CREATE,
        actor=admin,
        resource=user_resource
    )
    print(f"   User created: {event.event_id[:8]}")
    print()

    # 5. Log Access Denied
    print("5. LOG ACCESS DENIED:")
    print("-" * 40)

    event = await audit.log_access_denied(
        actor=user,
        resource=config_resource,
        reason="Insufficient permissions"
    )
    print(f"   Access denied: {event.event_id[:8]}")
    print(f"   Severity: {event.severity.name}")
    print()

    # 6. Custom Events
    print("6. CUSTOM EVENTS:")
    print("-" * 40)

    event = await audit.log(
        action=AuditAction.SECURITY_EVENT,
        actor=system,
        description="Suspicious activity detected",
        severity=AuditSeverity.CRITICAL,
        tags=["security", "alert"],
        metadata={"threat_level": "high"}
    )
    print(f"   Security event: {event.event_id[:8]}")

    event = await audit.log(
        action=AuditAction.DATA_EXPORT,
        actor=admin,
        description="Exported user data",
        metadata={"record_count": 1500, "format": "csv"}
    )
    print(f"   Data export: {event.event_id[:8]}")
    print()

    # 7. Correlation
    print("7. CORRELATED EVENTS:")
    print("-" * 40)

    correlation_id = str(uuid.uuid4())[:8]
    audit.set_correlation_id(correlation_id)

    await audit.log(
        action=AuditAction.READ,
        actor=admin,
        resource=user_resource,
        description="Step 1: Read user data"
    )

    await audit.log(
        action=AuditAction.UPDATE,
        actor=admin,
        resource=user_resource,
        description="Step 2: Update user"
    )

    await audit.log(
        action=AuditAction.SYSTEM_EVENT,
        actor=system,
        description="Step 3: Send notification"
    )

    audit.clear_correlation_id()

    print(f"   Correlation ID: {correlation_id}")
    print("   Logged 3 correlated events")
    print()

    # 8. Query Events
    print("8. QUERY EVENTS:")
    print("-" * 40)

    # All events
    query = AuditQuery(limit=100)
    events = await audit.query(query)
    print(f"   Total events: {len(events)}")

    # By action
    query = AuditQuery(actions=[AuditAction.LOGIN])
    events = await audit.query(query)
    print(f"   Login events: {len(events)}")

    # By severity
    query = AuditQuery(severities=[AuditSeverity.WARNING, AuditSeverity.CRITICAL])
    events = await audit.query(query)
    print(f"   Warning/Critical: {len(events)}")

    # By actor
    query = AuditQuery(actor_ids=["admin-001"])
    events = await audit.query(query)
    print(f"   Admin events: {len(events)}")

    # By correlation
    query = AuditQuery(correlation_id=correlation_id)
    events = await audit.query(query)
    print(f"   Correlated events: {len(events)}")
    print()

    # 9. Event Integrity
    print("9. EVENT INTEGRITY:")
    print("-" * 40)

    query = AuditQuery(limit=1)
    events = await audit.query(query)

    if events:
        event = events[0]
        print(f"   Event ID: {event.event_id[:8]}")
        print(f"   Hash: {event.hash[:20]}...")
        print(f"   Signature: {event.signature[:20]}...")

        is_valid = audit.verify_integrity(event)
        print(f"   Integrity valid: {is_valid}")
    print()

    # 10. Statistics
    print("10. STATISTICS:")
    print("-" * 40)

    stats = await audit.get_stats()
    print(f"   Total events: {stats.total_events}")
    print(f"   By action: {dict(stats.events_by_action)}")
    print(f"   By severity: {dict(stats.events_by_severity)}")
    print(f"   By status: {dict(stats.events_by_status)}")
    print()

    # 11. Export
    print("11. EXPORT:")
    print("-" * 40)

    query = AuditQuery(limit=3)

    json_export = await audit.export(query, format="json")
    print(f"   JSON export: {len(json_export)} bytes")

    csv_export = await audit.export(query, format="csv")
    print(f"   CSV export: {len(csv_export)} bytes")
    print(f"   CSV preview:\n{csv_export[:200]}...")
    print()

    # 12. Event Listener
    print("12. EVENT LISTENER:")
    print("-" * 40)

    listener_events = []

    async def on_event(event: AuditEvent):
        listener_events.append(event)

    audit.on_event(on_event)

    await audit.log(
        action=AuditAction.CUSTOM,
        description="Listener test event"
    )

    print(f"   Events captured by listener: {len(listener_events)}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Audit Logger System Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
