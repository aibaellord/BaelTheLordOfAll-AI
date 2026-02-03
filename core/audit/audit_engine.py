#!/usr/bin/env python3
"""
BAEL - Audit Engine
Audit logging for agents.

Features:
- Comprehensive audit trails
- Tamper-proof logging
- Query and filtering
- Retention policies
- Compliance reporting
"""

import asyncio
import hashlib
import json
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (
    Any, Callable, Dict, Generic, List, Optional, Set, Tuple, Type, TypeVar, Union
)


T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class AuditEventType(Enum):
    """Audit event types."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    EXECUTE = "execute"
    ACCESS = "access"
    DENY = "deny"
    ERROR = "error"
    CONFIG_CHANGE = "config_change"
    SYSTEM = "system"


class AuditSeverity(Enum):
    """Audit severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditCategory(Enum):
    """Audit categories."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    SYSTEM = "system"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    AGENT = "agent"


class RetentionPolicy(Enum):
    """Retention policies."""
    KEEP_ALL = "keep_all"
    DAYS_30 = "days_30"
    DAYS_90 = "days_90"
    DAYS_365 = "days_365"
    YEARS_7 = "years_7"


class AuditStorageType(Enum):
    """Audit storage types."""
    MEMORY = "memory"
    FILE = "file"
    DATABASE = "database"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class AuditConfig:
    """Audit configuration."""
    storage_type: AuditStorageType = AuditStorageType.MEMORY
    retention_policy: RetentionPolicy = RetentionPolicy.DAYS_90
    max_entries: int = 100000
    enable_hashing: bool = True
    enable_compression: bool = False


@dataclass
class AuditActor:
    """Actor in an audit event."""
    id: str = ""
    name: str = ""
    type: str = "user"
    ip_address: str = ""
    session_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditResource:
    """Resource in an audit event."""
    id: str = ""
    type: str = ""
    name: str = ""
    path: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditEvent:
    """Audit event."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    event_type: AuditEventType = AuditEventType.SYSTEM
    severity: AuditSeverity = AuditSeverity.INFO
    category: AuditCategory = AuditCategory.SYSTEM
    actor: AuditActor = field(default_factory=AuditActor)
    resource: AuditResource = field(default_factory=AuditResource)
    action: str = ""
    outcome: str = "success"
    details: Dict[str, Any] = field(default_factory=dict)
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None
    hash: str = ""
    previous_hash: str = ""


@dataclass
class AuditQuery:
    """Query for audit events."""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    event_types: List[AuditEventType] = field(default_factory=list)
    severities: List[AuditSeverity] = field(default_factory=list)
    categories: List[AuditCategory] = field(default_factory=list)
    actor_id: Optional[str] = None
    resource_id: Optional[str] = None
    resource_type: Optional[str] = None
    action: Optional[str] = None
    outcome: Optional[str] = None
    limit: int = 100
    offset: int = 0


@dataclass
class AuditReport:
    """Audit report."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    generated_at: datetime = field(default_factory=datetime.now)
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    total_events: int = 0
    events_by_type: Dict[str, int] = field(default_factory=dict)
    events_by_severity: Dict[str, int] = field(default_factory=dict)
    events_by_category: Dict[str, int] = field(default_factory=dict)
    top_actors: List[Tuple[str, int]] = field(default_factory=list)
    top_resources: List[Tuple[str, int]] = field(default_factory=list)
    security_events: int = 0
    error_events: int = 0


@dataclass
class AuditStats:
    """Audit statistics."""
    total_events: int = 0
    events_today: int = 0
    events_by_type: Dict[str, int] = field(default_factory=dict)
    events_by_severity: Dict[str, int] = field(default_factory=dict)
    storage_size: int = 0
    oldest_event: Optional[datetime] = None
    newest_event: Optional[datetime] = None


# =============================================================================
# AUDIT STORAGE
# =============================================================================

class AuditStorage(ABC):
    """Abstract audit storage."""
    
    @abstractmethod
    async def store(self, event: AuditEvent) -> bool:
        """Store an audit event."""
        pass
    
    @abstractmethod
    async def query(self, query: AuditQuery) -> List[AuditEvent]:
        """Query audit events."""
        pass
    
    @abstractmethod
    async def count(self, query: Optional[AuditQuery] = None) -> int:
        """Count audit events."""
        pass
    
    @abstractmethod
    async def get(self, event_id: str) -> Optional[AuditEvent]:
        """Get an audit event by ID."""
        pass
    
    @abstractmethod
    async def purge(self, before: datetime) -> int:
        """Purge events before a date."""
        pass


class MemoryAuditStorage(AuditStorage):
    """In-memory audit storage."""
    
    def __init__(self, max_entries: int = 100000):
        self._events: List[AuditEvent] = []
        self._index: Dict[str, int] = {}
        self._max_entries = max_entries
    
    async def store(self, event: AuditEvent) -> bool:
        """Store an audit event."""
        if len(self._events) >= self._max_entries:
            oldest = self._events.pop(0)
            if oldest.id in self._index:
                del self._index[oldest.id]
            
            for event_id, idx in self._index.items():
                self._index[event_id] = idx - 1
        
        self._events.append(event)
        self._index[event.id] = len(self._events) - 1
        return True
    
    async def query(self, query: AuditQuery) -> List[AuditEvent]:
        """Query audit events."""
        results = []
        
        for event in self._events:
            if self._matches(event, query):
                results.append(event)
        
        results.sort(key=lambda e: e.timestamp, reverse=True)
        
        start = query.offset
        end = start + query.limit
        return results[start:end]
    
    async def count(self, query: Optional[AuditQuery] = None) -> int:
        """Count audit events."""
        if query is None:
            return len(self._events)
        
        count = 0
        for event in self._events:
            if self._matches(event, query):
                count += 1
        
        return count
    
    async def get(self, event_id: str) -> Optional[AuditEvent]:
        """Get an audit event by ID."""
        idx = self._index.get(event_id)
        if idx is not None and idx < len(self._events):
            return self._events[idx]
        return None
    
    async def purge(self, before: datetime) -> int:
        """Purge events before a date."""
        count = 0
        new_events = []
        new_index = {}
        
        for event in self._events:
            if event.timestamp < before:
                count += 1
            else:
                new_index[event.id] = len(new_events)
                new_events.append(event)
        
        self._events = new_events
        self._index = new_index
        return count
    
    def _matches(self, event: AuditEvent, query: AuditQuery) -> bool:
        """Check if event matches query."""
        if query.start_time and event.timestamp < query.start_time:
            return False
        
        if query.end_time and event.timestamp > query.end_time:
            return False
        
        if query.event_types and event.event_type not in query.event_types:
            return False
        
        if query.severities and event.severity not in query.severities:
            return False
        
        if query.categories and event.category not in query.categories:
            return False
        
        if query.actor_id and event.actor.id != query.actor_id:
            return False
        
        if query.resource_id and event.resource.id != query.resource_id:
            return False
        
        if query.resource_type and event.resource.type != query.resource_type:
            return False
        
        if query.action and event.action != query.action:
            return False
        
        if query.outcome and event.outcome != query.outcome:
            return False
        
        return True


# =============================================================================
# AUDIT HASHER
# =============================================================================

class AuditHasher:
    """Creates tamper-proof hashes for audit events."""
    
    def __init__(self, secret_key: str = "bael-audit-key"):
        self._secret_key = secret_key
        self._last_hash = ""
    
    def hash_event(self, event: AuditEvent) -> str:
        """Create hash for an event."""
        content = json.dumps({
            "id": event.id,
            "timestamp": event.timestamp.isoformat(),
            "event_type": event.event_type.value,
            "actor": event.actor.id,
            "resource": event.resource.id,
            "action": event.action,
            "outcome": event.outcome,
            "previous_hash": self._last_hash
        }, sort_keys=True)
        
        hash_input = f"{self._secret_key}:{content}"
        event_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        
        self._last_hash = event_hash
        return event_hash
    
    def verify_chain(self, events: List[AuditEvent]) -> Tuple[bool, List[str]]:
        """Verify the integrity of the audit chain."""
        errors = []
        previous_hash = ""
        
        for i, event in enumerate(events):
            if event.previous_hash != previous_hash:
                errors.append(f"Hash chain broken at event {i}: {event.id}")
            
            content = json.dumps({
                "id": event.id,
                "timestamp": event.timestamp.isoformat(),
                "event_type": event.event_type.value,
                "actor": event.actor.id,
                "resource": event.resource.id,
                "action": event.action,
                "outcome": event.outcome,
                "previous_hash": event.previous_hash
            }, sort_keys=True)
            
            hash_input = f"{self._secret_key}:{content}"
            calculated_hash = hashlib.sha256(hash_input.encode()).hexdigest()
            
            if event.hash != calculated_hash:
                errors.append(f"Hash mismatch at event {i}: {event.id}")
            
            previous_hash = event.hash
        
        return len(errors) == 0, errors


# =============================================================================
# AUDIT TRAIL
# =============================================================================

class AuditTrail:
    """Audit trail for a specific context."""
    
    def __init__(self, context: str, storage: AuditStorage, hasher: AuditHasher):
        self._context = context
        self._storage = storage
        self._hasher = hasher
    
    @property
    def context(self) -> str:
        return self._context
    
    async def log(
        self,
        event_type: AuditEventType,
        action: str,
        actor: Optional[AuditActor] = None,
        resource: Optional[AuditResource] = None,
        outcome: str = "success",
        severity: AuditSeverity = AuditSeverity.INFO,
        category: AuditCategory = AuditCategory.SYSTEM,
        details: Optional[Dict[str, Any]] = None,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        """Log an audit event."""
        event = AuditEvent(
            event_type=event_type,
            severity=severity,
            category=category,
            actor=actor or AuditActor(),
            resource=resource or AuditResource(),
            action=action,
            outcome=outcome,
            details=details or {},
            before_state=before_state,
            after_state=after_state
        )
        
        event.hash = self._hasher.hash_event(event)
        event.previous_hash = self._hasher._last_hash
        
        await self._storage.store(event)
        return event
    
    async def query(self, query: AuditQuery) -> List[AuditEvent]:
        """Query audit events."""
        return await self._storage.query(query)
    
    async def get_history(
        self,
        resource_id: str,
        limit: int = 100
    ) -> List[AuditEvent]:
        """Get history for a resource."""
        query = AuditQuery(resource_id=resource_id, limit=limit)
        return await self._storage.query(query)
    
    async def get_actor_activity(
        self,
        actor_id: str,
        limit: int = 100
    ) -> List[AuditEvent]:
        """Get activity for an actor."""
        query = AuditQuery(actor_id=actor_id, limit=limit)
        return await self._storage.query(query)


# =============================================================================
# REPORT GENERATOR
# =============================================================================

class AuditReportGenerator:
    """Generates audit reports."""
    
    def __init__(self, storage: AuditStorage):
        self._storage = storage
    
    async def generate(
        self,
        name: str,
        start_time: datetime,
        end_time: datetime
    ) -> AuditReport:
        """Generate an audit report."""
        query = AuditQuery(
            start_time=start_time,
            end_time=end_time,
            limit=1000000
        )
        
        events = await self._storage.query(query)
        
        events_by_type: Dict[str, int] = defaultdict(int)
        events_by_severity: Dict[str, int] = defaultdict(int)
        events_by_category: Dict[str, int] = defaultdict(int)
        actors_count: Dict[str, int] = defaultdict(int)
        resources_count: Dict[str, int] = defaultdict(int)
        security_events = 0
        error_events = 0
        
        for event in events:
            events_by_type[event.event_type.value] += 1
            events_by_severity[event.severity.value] += 1
            events_by_category[event.category.value] += 1
            
            if event.actor.id:
                actors_count[event.actor.id] += 1
            
            if event.resource.id:
                resources_count[event.resource.id] += 1
            
            if event.category == AuditCategory.SECURITY:
                security_events += 1
            
            if event.severity == AuditSeverity.ERROR or event.severity == AuditSeverity.CRITICAL:
                error_events += 1
        
        top_actors = sorted(actors_count.items(), key=lambda x: x[1], reverse=True)[:10]
        top_resources = sorted(resources_count.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return AuditReport(
            name=name,
            period_start=start_time,
            period_end=end_time,
            total_events=len(events),
            events_by_type=dict(events_by_type),
            events_by_severity=dict(events_by_severity),
            events_by_category=dict(events_by_category),
            top_actors=top_actors,
            top_resources=top_resources,
            security_events=security_events,
            error_events=error_events
        )


# =============================================================================
# AUDIT ENGINE
# =============================================================================

class AuditEngine:
    """
    Audit Engine for BAEL.
    
    Audit logging for agents.
    """
    
    def __init__(self, config: Optional[AuditConfig] = None):
        self._config = config or AuditConfig()
        self._storage = MemoryAuditStorage(self._config.max_entries)
        self._hasher = AuditHasher()
        self._trails: Dict[str, AuditTrail] = {}
        self._report_generator = AuditReportGenerator(self._storage)
        self._stats = AuditStats()
        self._callbacks: List[Callable[[AuditEvent], None]] = []
    
    # ----- Trail Management -----
    
    def create_trail(self, context: str) -> AuditTrail:
        """Create an audit trail."""
        trail = AuditTrail(context, self._storage, self._hasher)
        self._trails[context] = trail
        return trail
    
    def get_trail(self, context: str) -> Optional[AuditTrail]:
        """Get an audit trail."""
        return self._trails.get(context)
    
    def list_trails(self) -> List[str]:
        """List all trails."""
        return list(self._trails.keys())
    
    # ----- Direct Logging -----
    
    async def log(
        self,
        event_type: AuditEventType,
        action: str,
        actor: Optional[AuditActor] = None,
        resource: Optional[AuditResource] = None,
        outcome: str = "success",
        severity: AuditSeverity = AuditSeverity.INFO,
        category: AuditCategory = AuditCategory.SYSTEM,
        details: Optional[Dict[str, Any]] = None,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        """Log an audit event directly."""
        event = AuditEvent(
            event_type=event_type,
            severity=severity,
            category=category,
            actor=actor or AuditActor(),
            resource=resource or AuditResource(),
            action=action,
            outcome=outcome,
            details=details or {},
            before_state=before_state,
            after_state=after_state
        )
        
        if self._config.enable_hashing:
            event.previous_hash = self._hasher._last_hash
            event.hash = self._hasher.hash_event(event)
        
        await self._storage.store(event)
        self._update_stats(event)
        
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception:
                pass
        
        return event
    
    # ----- Convenience Methods -----
    
    async def log_create(
        self,
        resource: AuditResource,
        actor: Optional[AuditActor] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        """Log a create event."""
        return await self.log(
            event_type=AuditEventType.CREATE,
            action="create",
            actor=actor,
            resource=resource,
            category=AuditCategory.DATA_MODIFICATION,
            details=details
        )
    
    async def log_read(
        self,
        resource: AuditResource,
        actor: Optional[AuditActor] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        """Log a read event."""
        return await self.log(
            event_type=AuditEventType.READ,
            action="read",
            actor=actor,
            resource=resource,
            category=AuditCategory.DATA_ACCESS,
            details=details
        )
    
    async def log_update(
        self,
        resource: AuditResource,
        actor: Optional[AuditActor] = None,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        """Log an update event."""
        return await self.log(
            event_type=AuditEventType.UPDATE,
            action="update",
            actor=actor,
            resource=resource,
            category=AuditCategory.DATA_MODIFICATION,
            before_state=before_state,
            after_state=after_state,
            details=details
        )
    
    async def log_delete(
        self,
        resource: AuditResource,
        actor: Optional[AuditActor] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        """Log a delete event."""
        return await self.log(
            event_type=AuditEventType.DELETE,
            action="delete",
            actor=actor,
            resource=resource,
            category=AuditCategory.DATA_MODIFICATION,
            details=details
        )
    
    async def log_login(
        self,
        actor: AuditActor,
        outcome: str = "success",
        details: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        """Log a login event."""
        return await self.log(
            event_type=AuditEventType.LOGIN,
            action="login",
            actor=actor,
            outcome=outcome,
            category=AuditCategory.AUTHENTICATION,
            severity=AuditSeverity.INFO if outcome == "success" else AuditSeverity.WARNING,
            details=details
        )
    
    async def log_access_denied(
        self,
        resource: AuditResource,
        actor: Optional[AuditActor] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        """Log an access denied event."""
        return await self.log(
            event_type=AuditEventType.DENY,
            action="access_denied",
            actor=actor,
            resource=resource,
            outcome="denied",
            category=AuditCategory.AUTHORIZATION,
            severity=AuditSeverity.WARNING,
            details=details
        )
    
    async def log_error(
        self,
        action: str,
        error: str,
        actor: Optional[AuditActor] = None,
        resource: Optional[AuditResource] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        """Log an error event."""
        all_details = details or {}
        all_details["error"] = error
        
        return await self.log(
            event_type=AuditEventType.ERROR,
            action=action,
            actor=actor,
            resource=resource,
            outcome="error",
            category=AuditCategory.SYSTEM,
            severity=AuditSeverity.ERROR,
            details=all_details
        )
    
    # ----- Querying -----
    
    async def query(self, query: AuditQuery) -> List[AuditEvent]:
        """Query audit events."""
        return await self._storage.query(query)
    
    async def get_event(self, event_id: str) -> Optional[AuditEvent]:
        """Get a specific event."""
        return await self._storage.get(event_id)
    
    async def get_recent(self, limit: int = 100) -> List[AuditEvent]:
        """Get recent events."""
        query = AuditQuery(limit=limit)
        return await self._storage.query(query)
    
    async def search(
        self,
        event_types: Optional[List[AuditEventType]] = None,
        severities: Optional[List[AuditSeverity]] = None,
        categories: Optional[List[AuditCategory]] = None,
        actor_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditEvent]:
        """Search audit events."""
        query = AuditQuery(
            event_types=event_types or [],
            severities=severities or [],
            categories=categories or [],
            actor_id=actor_id,
            resource_id=resource_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
        return await self._storage.query(query)
    
    # ----- Reporting -----
    
    async def generate_report(
        self,
        name: str,
        start_time: datetime,
        end_time: datetime
    ) -> AuditReport:
        """Generate an audit report."""
        return await self._report_generator.generate(name, start_time, end_time)
    
    async def generate_daily_report(self, date: datetime) -> AuditReport:
        """Generate a daily report."""
        start = datetime(date.year, date.month, date.day)
        end = start + timedelta(days=1)
        return await self.generate_report(f"Daily-{date.strftime('%Y-%m-%d')}", start, end)
    
    # ----- Integrity -----
    
    async def verify_integrity(self, limit: int = 1000) -> Tuple[bool, List[str]]:
        """Verify audit chain integrity."""
        query = AuditQuery(limit=limit)
        events = await self._storage.query(query)
        events.sort(key=lambda e: e.timestamp)
        return self._hasher.verify_chain(events)
    
    # ----- Retention -----
    
    async def apply_retention(self) -> int:
        """Apply retention policy."""
        now = datetime.now()
        
        if self._config.retention_policy == RetentionPolicy.KEEP_ALL:
            return 0
        
        if self._config.retention_policy == RetentionPolicy.DAYS_30:
            cutoff = now - timedelta(days=30)
        elif self._config.retention_policy == RetentionPolicy.DAYS_90:
            cutoff = now - timedelta(days=90)
        elif self._config.retention_policy == RetentionPolicy.DAYS_365:
            cutoff = now - timedelta(days=365)
        elif self._config.retention_policy == RetentionPolicy.YEARS_7:
            cutoff = now - timedelta(days=365 * 7)
        else:
            return 0
        
        return await self._storage.purge(cutoff)
    
    # ----- Callbacks -----
    
    def add_callback(self, callback: Callable[[AuditEvent], None]) -> None:
        """Add an event callback."""
        self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[AuditEvent], None]) -> None:
        """Remove an event callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    # ----- Stats -----
    
    def _update_stats(self, event: AuditEvent) -> None:
        """Update statistics."""
        self._stats.total_events += 1
        
        if event.timestamp.date() == datetime.now().date():
            self._stats.events_today += 1
        
        type_key = event.event_type.value
        self._stats.events_by_type[type_key] = self._stats.events_by_type.get(type_key, 0) + 1
        
        severity_key = event.severity.value
        self._stats.events_by_severity[severity_key] = self._stats.events_by_severity.get(severity_key, 0) + 1
        
        if self._stats.oldest_event is None or event.timestamp < self._stats.oldest_event:
            self._stats.oldest_event = event.timestamp
        
        if self._stats.newest_event is None or event.timestamp > self._stats.newest_event:
            self._stats.newest_event = event.timestamp
    
    @property
    def stats(self) -> AuditStats:
        return self._stats
    
    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "trails": len(self._trails),
            "total_events": self._stats.total_events,
            "events_today": self._stats.events_today,
            "retention_policy": self._config.retention_policy.value,
            "hashing_enabled": self._config.enable_hashing
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Audit Engine."""
    print("=" * 70)
    print("BAEL - AUDIT ENGINE DEMO")
    print("Audit Logging for Agents")
    print("=" * 70)
    print()
    
    engine = AuditEngine()
    
    # 1. Create Audit Trail
    print("1. CREATE AUDIT TRAIL:")
    print("-" * 40)
    
    trail = engine.create_trail("agent-operations")
    print(f"   Created trail: {trail.context}")
    print(f"   Total trails: {len(engine.list_trails())}")
    print()
    
    # 2. Log Create Event
    print("2. LOG CREATE EVENT:")
    print("-" * 40)
    
    actor = AuditActor(id="user-1", name="Alice", type="user", ip_address="192.168.1.1")
    resource = AuditResource(id="agent-1", type="agent", name="SearchAgent")
    
    event = await engine.log_create(resource=resource, actor=actor, details={"priority": "high"})
    
    print(f"   Event ID: {event.id}")
    print(f"   Type: {event.event_type.value}")
    print(f"   Actor: {event.actor.name}")
    print(f"   Resource: {event.resource.name}")
    print()
    
    # 3. Log Read Event
    print("3. LOG READ EVENT:")
    print("-" * 40)
    
    event = await engine.log_read(resource=resource, actor=actor)
    print(f"   Logged read: {event.id}")
    print()
    
    # 4. Log Update Event
    print("4. LOG UPDATE EVENT:")
    print("-" * 40)
    
    event = await engine.log_update(
        resource=resource,
        actor=actor,
        before_state={"status": "idle"},
        after_state={"status": "active"}
    )
    print(f"   Before: {event.before_state}")
    print(f"   After: {event.after_state}")
    print()
    
    # 5. Log Login Events
    print("5. LOG LOGIN EVENTS:")
    print("-" * 40)
    
    await engine.log_login(actor=actor, outcome="success")
    print(f"   Logged successful login for {actor.name}")
    
    bad_actor = AuditActor(id="unknown", name="Unknown", ip_address="10.0.0.1")
    await engine.log_login(actor=bad_actor, outcome="failed", details={"reason": "invalid_password"})
    print(f"   Logged failed login attempt")
    print()
    
    # 6. Log Access Denied
    print("6. LOG ACCESS DENIED:")
    print("-" * 40)
    
    restricted = AuditResource(id="secret-1", type="secret", name="API Key")
    await engine.log_access_denied(resource=restricted, actor=bad_actor)
    print(f"   Logged access denied to {restricted.name}")
    print()
    
    # 7. Log Error
    print("7. LOG ERROR:")
    print("-" * 40)
    
    await engine.log_error(
        action="process_request",
        error="Connection timeout",
        actor=actor,
        details={"timeout": 30}
    )
    print(f"   Logged error event")
    print()
    
    # 8. Log with Trail
    print("8. LOG WITH TRAIL:")
    print("-" * 40)
    
    await trail.log(
        event_type=AuditEventType.EXECUTE,
        action="run_tool",
        actor=actor,
        resource=AuditResource(id="tool-1", type="tool", name="WebSearch"),
        category=AuditCategory.AGENT
    )
    print(f"   Logged via trail: {trail.context}")
    print()
    
    # 9. Query Events
    print("9. QUERY EVENTS:")
    print("-" * 40)
    
    recent = await engine.get_recent(limit=5)
    print(f"   Recent events ({len(recent)}):")
    for e in recent:
        print(f"   - {e.event_type.value}: {e.action} by {e.actor.name or 'N/A'}")
    print()
    
    # 10. Search by Criteria
    print("10. SEARCH BY CRITERIA:")
    print("-" * 40)
    
    errors = await engine.search(
        severities=[AuditSeverity.ERROR, AuditSeverity.WARNING],
        limit=10
    )
    print(f"   Errors/Warnings: {len(errors)}")
    
    actor_events = await engine.search(actor_id="user-1", limit=10)
    print(f"   Events by user-1: {len(actor_events)}")
    print()
    
    # 11. Generate Report
    print("11. GENERATE REPORT:")
    print("-" * 40)
    
    now = datetime.now()
    report = await engine.generate_report(
        "Test Report",
        now - timedelta(hours=1),
        now + timedelta(hours=1)
    )
    
    print(f"   Report: {report.name}")
    print(f"   Total events: {report.total_events}")
    print(f"   Events by type: {report.events_by_type}")
    print(f"   Security events: {report.security_events}")
    print(f"   Error events: {report.error_events}")
    print()
    
    # 12. Verify Integrity
    print("12. VERIFY INTEGRITY:")
    print("-" * 40)
    
    valid, errors = await engine.verify_integrity()
    print(f"   Chain valid: {valid}")
    if errors:
        print(f"   Errors: {errors}")
    print()
    
    # 13. Statistics
    print("13. STATISTICS:")
    print("-" * 40)
    
    stats = engine.stats
    print(f"   Total events: {stats.total_events}")
    print(f"   Events today: {stats.events_today}")
    print(f"   By type: {stats.events_by_type}")
    print(f"   By severity: {stats.events_by_severity}")
    print()
    
    # 14. Engine Summary
    print("14. ENGINE SUMMARY:")
    print("-" * 40)
    
    summary = engine.summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()
    
    print("=" * 70)
    print("DEMO COMPLETE - Audit Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
