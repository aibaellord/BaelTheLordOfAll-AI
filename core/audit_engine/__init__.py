"""
BAEL Audit Engine
==================

Comprehensive audit logging with:
- Event tracking
- Compliance logging
- Tamper-proof records
- Query and search

"Ba'el records all actions across reality." — Ba'el
"""

from .audit_engine import (
    # Enums
    AuditEventType,
    AuditSeverity,
    AuditStatus,
    ComplianceStandard,

    # Data structures
    AuditEvent,
    AuditQuery,
    AuditConfig,

    # Engine
    AuditEngine,
    audit_engine,
)

__all__ = [
    # Enums
    "AuditEventType",
    "AuditSeverity",
    "AuditStatus",
    "ComplianceStandard",

    # Data structures
    "AuditEvent",
    "AuditQuery",
    "AuditConfig",

    # Engine
    "AuditEngine",
    "audit_engine",
]
