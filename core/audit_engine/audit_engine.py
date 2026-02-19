"""
BAEL Audit Engine
==================

Enterprise-grade audit logging and compliance tracking.

"Ba'el witnesses all actions in all dimensions." — Ba'el
"""

import asyncio
import logging
import hashlib
import json
import uuid
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Set, Union
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import defaultdict
import os

logger = logging.getLogger("BAEL.Audit")


# ============================================================================
# ENUMS
# ============================================================================

class AuditEventType(Enum):
    """Audit event types."""
    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGE = "password_change"
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"

    # Authorization
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    PERMISSION_CHANGE = "permission_change"
    ROLE_CHANGE = "role_change"

    # Data Operations
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXPORT = "export"
    IMPORT = "import"

    # System
    CONFIG_CHANGE = "config_change"
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    ERROR = "error"

    # Security
    SECURITY_ALERT = "security_alert"
    INTRUSION_ATTEMPT = "intrusion_attempt"
    DATA_BREACH = "data_breach"

    # Compliance
    CONSENT_GIVEN = "consent_given"
    CONSENT_REVOKED = "consent_revoked"
    DATA_RETENTION = "data_retention"
    DATA_DELETION = "data_deletion"

    # Custom
    CUSTOM = "custom"


class AuditSeverity(Enum):
    """Audit event severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditStatus(Enum):
    """Audit event status."""
    SUCCESS = "success"
    FAILURE = "failure"
    PENDING = "pending"
    PARTIAL = "partial"


class ComplianceStandard(Enum):
    """Compliance standards."""
    GDPR = "gdpr"
    HIPAA = "hipaa"
    SOC2 = "soc2"
    PCI_DSS = "pci_dss"
    ISO_27001 = "iso_27001"
    SOX = "sox"
    CCPA = "ccpa"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class AuditEvent:
    """An audit event."""
    id: str
    timestamp: datetime
    event_type: AuditEventType

    # Actor
    actor_id: Optional[str] = None
    actor_type: str = "user"  # user, system, service
    actor_ip: Optional[str] = None
    actor_user_agent: Optional[str] = None

    # Action
    action: str = ""
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None

    # Context
    severity: AuditSeverity = AuditSeverity.INFO
    status: AuditStatus = AuditStatus.SUCCESS

    # Details
    description: str = ""
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Compliance
    compliance_tags: List[str] = field(default_factory=list)

    # Integrity
    checksum: Optional[str] = None
    previous_checksum: Optional[str] = None

    def compute_checksum(self, previous: Optional[str] = None) -> str:
        """Compute event checksum for integrity."""
        data = {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'event_type': self.event_type.value,
            'actor_id': self.actor_id,
            'action': self.action,
            'resource_id': self.resource_id,
            'previous': previous or ''
        }

        content = json.dumps(data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'event_type': self.event_type.value,
            'actor_id': self.actor_id,
            'actor_type': self.actor_type,
            'actor_ip': self.actor_ip,
            'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'severity': self.severity.value,
            'status': self.status.value,
            'description': self.description,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'metadata': self.metadata,
            'compliance_tags': self.compliance_tags,
            'checksum': self.checksum,
            'previous_checksum': self.previous_checksum
        }


@dataclass
class AuditQuery:
    """Query for searching audit events."""
    # Time range
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    # Filters
    event_types: Optional[List[AuditEventType]] = None
    actor_ids: Optional[List[str]] = None
    resource_ids: Optional[List[str]] = None
    severities: Optional[List[AuditSeverity]] = None
    statuses: Optional[List[AuditStatus]] = None

    # Search
    search_text: Optional[str] = None

    # Compliance
    compliance_tags: Optional[List[str]] = None

    # Pagination
    limit: int = 100
    offset: int = 0

    # Sorting
    sort_by: str = "timestamp"
    sort_order: str = "desc"


@dataclass
class AuditConfig:
    """Audit engine configuration."""
    enabled: bool = True
    retention_days: int = 365

    # Storage
    storage_path: str = "./audit_logs"
    max_file_size_mb: int = 100

    # Integrity
    enable_checksums: bool = True
    enable_chain: bool = True

    # Real-time
    enable_realtime: bool = True

    # Compliance
    default_compliance_tags: List[str] = field(default_factory=list)


# ============================================================================
# AUDIT STORE
# ============================================================================

class AuditStore:
    """Storage for audit events."""

    def __init__(self, config: AuditConfig):
        """Initialize store."""
        self.config = config
        self._events: List[AuditEvent] = []
        self._indices: Dict[str, Dict[Any, Set[str]]] = defaultdict(lambda: defaultdict(set))
        self._lock = threading.RLock()

        # Last checksum for chain
        self._last_checksum: Optional[str] = None

    def append(self, event: AuditEvent) -> None:
        """Append an event."""
        with self._lock:
            # Compute checksum
            if self.config.enable_checksums:
                if self.config.enable_chain:
                    event.previous_checksum = self._last_checksum

                event.checksum = event.compute_checksum(self._last_checksum)
                self._last_checksum = event.checksum

            # Store event
            self._events.append(event)

            # Update indices
            self._indices['event_type'][event.event_type].add(event.id)

            if event.actor_id:
                self._indices['actor_id'][event.actor_id].add(event.id)

            if event.resource_id:
                self._indices['resource_id'][event.resource_id].add(event.id)

            self._indices['severity'][event.severity].add(event.id)
            self._indices['status'][event.status].add(event.id)

    def query(self, query: AuditQuery) -> List[AuditEvent]:
        """Query events."""
        with self._lock:
            results = self._events.copy()

            # Time range
            if query.start_time:
                results = [e for e in results if e.timestamp >= query.start_time]

            if query.end_time:
                results = [e for e in results if e.timestamp <= query.end_time]

            # Event types
            if query.event_types:
                type_ids = set()
                for et in query.event_types:
                    type_ids.update(self._indices['event_type'].get(et, set()))
                results = [e for e in results if e.id in type_ids]

            # Actor IDs
            if query.actor_ids:
                actor_ids = set()
                for aid in query.actor_ids:
                    actor_ids.update(self._indices['actor_id'].get(aid, set()))
                results = [e for e in results if e.id in actor_ids]

            # Resource IDs
            if query.resource_ids:
                resource_ids = set()
                for rid in query.resource_ids:
                    resource_ids.update(self._indices['resource_id'].get(rid, set()))
                results = [e for e in results if e.id in resource_ids]

            # Severities
            if query.severities:
                severity_ids = set()
                for s in query.severities:
                    severity_ids.update(self._indices['severity'].get(s, set()))
                results = [e for e in results if e.id in severity_ids]

            # Statuses
            if query.statuses:
                status_ids = set()
                for s in query.statuses:
                    status_ids.update(self._indices['status'].get(s, set()))
                results = [e for e in results if e.id in status_ids]

            # Search text
            if query.search_text:
                search_lower = query.search_text.lower()
                results = [
                    e for e in results
                    if search_lower in e.description.lower() or
                       search_lower in e.action.lower()
                ]

            # Compliance tags
            if query.compliance_tags:
                results = [
                    e for e in results
                    if any(t in e.compliance_tags for t in query.compliance_tags)
                ]

            # Sort
            reverse = query.sort_order == "desc"
            if query.sort_by == "timestamp":
                results.sort(key=lambda e: e.timestamp, reverse=reverse)
            elif query.sort_by == "severity":
                severity_order = {
                    AuditSeverity.DEBUG: 0,
                    AuditSeverity.INFO: 1,
                    AuditSeverity.WARNING: 2,
                    AuditSeverity.ERROR: 3,
                    AuditSeverity.CRITICAL: 4
                }
                results.sort(key=lambda e: severity_order.get(e.severity, 0), reverse=reverse)

            # Pagination
            start = query.offset
            end = query.offset + query.limit

            return results[start:end]

    def get_by_id(self, event_id: str) -> Optional[AuditEvent]:
        """Get event by ID."""
        with self._lock:
            for event in self._events:
                if event.id == event_id:
                    return event
            return None

    def verify_chain(self) -> Tuple[bool, List[str]]:
        """Verify the integrity chain."""
        errors = []

        with self._lock:
            previous = None

            for event in self._events:
                if not self.config.enable_checksums:
                    break

                # Verify checksum
                expected = event.compute_checksum(previous)

                if event.checksum != expected:
                    errors.append(f"Invalid checksum for event {event.id}")

                # Verify chain
                if self.config.enable_chain:
                    if event.previous_checksum != previous:
                        errors.append(f"Broken chain at event {event.id}")

                previous = event.checksum

        return len(errors) == 0, errors

    def count(self) -> int:
        """Get total event count."""
        return len(self._events)

    def cleanup(self, before: datetime) -> int:
        """Remove events before a date."""
        with self._lock:
            original_count = len(self._events)
            self._events = [e for e in self._events if e.timestamp >= before]
            return original_count - len(self._events)


# ============================================================================
# AUDIT HANDLERS
# ============================================================================

class AuditHandler:
    """Base class for audit handlers."""

    async def handle(self, event: AuditEvent) -> None:
        """Handle an audit event."""
        raise NotImplementedError


class ConsoleHandler(AuditHandler):
    """Handler that logs to console."""

    async def handle(self, event: AuditEvent) -> None:
        """Log event to console."""
        log_level = {
            AuditSeverity.DEBUG: logging.DEBUG,
            AuditSeverity.INFO: logging.INFO,
            AuditSeverity.WARNING: logging.WARNING,
            AuditSeverity.ERROR: logging.ERROR,
            AuditSeverity.CRITICAL: logging.CRITICAL
        }.get(event.severity, logging.INFO)

        message = (
            f"[AUDIT] {event.event_type.value} | "
            f"actor={event.actor_id} | "
            f"resource={event.resource_id} | "
            f"status={event.status.value} | "
            f"{event.description}"
        )

        logger.log(log_level, message)


class FileHandler(AuditHandler):
    """Handler that writes to file."""

    def __init__(self, path: str):
        """Initialize handler."""
        self.path = path
        self._lock = threading.Lock()

        # Ensure directory exists
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)

    async def handle(self, event: AuditEvent) -> None:
        """Write event to file."""
        with self._lock:
            with open(self.path, 'a') as f:
                f.write(json.dumps(event.to_dict()) + '\n')


class WebhookHandler(AuditHandler):
    """Handler that sends to webhook."""

    def __init__(self, url: str, headers: Optional[Dict[str, str]] = None):
        """Initialize handler."""
        self.url = url
        self.headers = headers or {}

    async def handle(self, event: AuditEvent) -> None:
        """Send event to webhook."""
        # Would use aiohttp to send
        logger.debug(f"Would send audit event to {self.url}")


# ============================================================================
# MAIN AUDIT ENGINE
# ============================================================================

class AuditEngine:
    """
    Main audit engine.

    Features:
    - Comprehensive audit logging
    - Tamper-proof records
    - Compliance tagging
    - Query and search

    "Ba'el records all that transpires." — Ba'el
    """

    def __init__(self, config: Optional[AuditConfig] = None):
        """Initialize audit engine."""
        self.config = config or AuditConfig()

        self._store = AuditStore(self.config)
        self._handlers: List[AuditHandler] = []

        # Default console handler
        if self.config.enable_realtime:
            self._handlers.append(ConsoleHandler())

        self._lock = threading.RLock()

        logger.info("AuditEngine initialized")

    # ========================================================================
    # LOGGING
    # ========================================================================

    async def log(
        self,
        event_type: AuditEventType,
        action: str,
        actor_id: Optional[str] = None,
        actor_type: str = "user",
        actor_ip: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        severity: AuditSeverity = AuditSeverity.INFO,
        status: AuditStatus = AuditStatus.SUCCESS,
        description: str = "",
        old_value: Optional[Any] = None,
        new_value: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
        compliance_tags: Optional[List[str]] = None
    ) -> AuditEvent:
        """Log an audit event."""
        if not self.config.enabled:
            return None

        # Create event
        event = AuditEvent(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            event_type=event_type,
            actor_id=actor_id,
            actor_type=actor_type,
            actor_ip=actor_ip,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            severity=severity,
            status=status,
            description=description,
            old_value=old_value,
            new_value=new_value,
            metadata=metadata or {},
            compliance_tags=compliance_tags or self.config.default_compliance_tags
        )

        # Store event
        self._store.append(event)

        # Dispatch to handlers
        for handler in self._handlers:
            try:
                await handler.handle(event)
            except Exception as e:
                logger.error(f"Handler error: {e}")

        return event

    # ========================================================================
    # CONVENIENCE METHODS
    # ========================================================================

    async def log_login(
        self,
        actor_id: str,
        success: bool,
        actor_ip: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        """Log a login event."""
        return await self.log(
            event_type=AuditEventType.LOGIN if success else AuditEventType.LOGIN_FAILED,
            action="authenticate",
            actor_id=actor_id,
            actor_ip=actor_ip,
            status=AuditStatus.SUCCESS if success else AuditStatus.FAILURE,
            description=f"User {'successfully logged in' if success else 'login failed'}",
            metadata=metadata
        )

    async def log_logout(
        self,
        actor_id: str,
        actor_ip: Optional[str] = None
    ) -> AuditEvent:
        """Log a logout event."""
        return await self.log(
            event_type=AuditEventType.LOGOUT,
            action="logout",
            actor_id=actor_id,
            actor_ip=actor_ip,
            description="User logged out"
        )

    async def log_access(
        self,
        actor_id: str,
        resource_type: str,
        resource_id: str,
        granted: bool,
        action: str = "access"
    ) -> AuditEvent:
        """Log an access event."""
        return await self.log(
            event_type=AuditEventType.ACCESS_GRANTED if granted else AuditEventType.ACCESS_DENIED,
            action=action,
            actor_id=actor_id,
            resource_type=resource_type,
            resource_id=resource_id,
            status=AuditStatus.SUCCESS if granted else AuditStatus.FAILURE,
            severity=AuditSeverity.INFO if granted else AuditSeverity.WARNING,
            description=f"Access {'granted' if granted else 'denied'} to {resource_type}/{resource_id}"
        )

    async def log_data_change(
        self,
        actor_id: str,
        resource_type: str,
        resource_id: str,
        change_type: str,  # create, update, delete
        old_value: Optional[Any] = None,
        new_value: Optional[Any] = None
    ) -> AuditEvent:
        """Log a data change event."""
        event_type = {
            'create': AuditEventType.CREATE,
            'update': AuditEventType.UPDATE,
            'delete': AuditEventType.DELETE
        }.get(change_type, AuditEventType.UPDATE)

        return await self.log(
            event_type=event_type,
            action=change_type,
            actor_id=actor_id,
            resource_type=resource_type,
            resource_id=resource_id,
            old_value=old_value,
            new_value=new_value,
            description=f"{change_type.capitalize()}d {resource_type}/{resource_id}"
        )

    async def log_security_alert(
        self,
        description: str,
        actor_id: Optional[str] = None,
        actor_ip: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        """Log a security alert."""
        return await self.log(
            event_type=AuditEventType.SECURITY_ALERT,
            action="security_alert",
            actor_id=actor_id,
            actor_ip=actor_ip,
            severity=AuditSeverity.CRITICAL,
            description=description,
            metadata=metadata
        )

    # ========================================================================
    # QUERYING
    # ========================================================================

    def query(self, query: AuditQuery) -> List[AuditEvent]:
        """Query audit events."""
        return self._store.query(query)

    def get_by_id(self, event_id: str) -> Optional[AuditEvent]:
        """Get event by ID."""
        return self._store.get_by_id(event_id)

    def get_recent(
        self,
        limit: int = 100,
        event_types: Optional[List[AuditEventType]] = None
    ) -> List[AuditEvent]:
        """Get recent events."""
        query = AuditQuery(
            limit=limit,
            event_types=event_types,
            sort_by="timestamp",
            sort_order="desc"
        )
        return self.query(query)

    def get_by_actor(
        self,
        actor_id: str,
        limit: int = 100
    ) -> List[AuditEvent]:
        """Get events for an actor."""
        query = AuditQuery(
            actor_ids=[actor_id],
            limit=limit,
            sort_order="desc"
        )
        return self.query(query)

    def get_by_resource(
        self,
        resource_id: str,
        limit: int = 100
    ) -> List[AuditEvent]:
        """Get events for a resource."""
        query = AuditQuery(
            resource_ids=[resource_id],
            limit=limit,
            sort_order="desc"
        )
        return self.query(query)

    # ========================================================================
    # HANDLERS
    # ========================================================================

    def add_handler(self, handler: AuditHandler) -> None:
        """Add an audit handler."""
        self._handlers.append(handler)

    def remove_handler(self, handler: AuditHandler) -> None:
        """Remove an audit handler."""
        if handler in self._handlers:
            self._handlers.remove(handler)

    # ========================================================================
    # INTEGRITY
    # ========================================================================

    def verify_integrity(self) -> Tuple[bool, List[str]]:
        """Verify audit log integrity."""
        return self._store.verify_chain()

    # ========================================================================
    # MAINTENANCE
    # ========================================================================

    def cleanup_old_events(self, days: Optional[int] = None) -> int:
        """Cleanup events older than retention period."""
        retention_days = days or self.config.retention_days
        cutoff = datetime.now() - timedelta(days=retention_days)
        return self._store.cleanup(cutoff)

    # ========================================================================
    # STATUS
    # ========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get audit engine status."""
        valid, errors = self.verify_integrity()

        return {
            'enabled': self.config.enabled,
            'total_events': self._store.count(),
            'handlers': len(self._handlers),
            'integrity_valid': valid,
            'integrity_errors': len(errors),
            'retention_days': self.config.retention_days
        }


# ============================================================================
# CONVENIENCE INSTANCE
# ============================================================================

audit_engine = AuditEngine()
