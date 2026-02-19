"""
BAEL Email Engine
==================

Email system with:
- SMTP/API sending
- Templates
- Tracking
- Queuing

"Ba'el communicates across all channels." — Ba'el
"""

from .email_engine import (
    # Enums
    EmailStatus,
    EmailPriority,
    EmailProvider,

    # Data structures
    EmailAddress,
    EmailAttachment,
    Email,
    EmailTemplate,
    EmailConfig,

    # Engine
    EmailEngine,
    email_engine,
)

__all__ = [
    # Enums
    "EmailStatus",
    "EmailPriority",
    "EmailProvider",

    # Data structures
    "EmailAddress",
    "EmailAttachment",
    "Email",
    "EmailTemplate",
    "EmailConfig",

    # Engine
    "EmailEngine",
    "email_engine",
]
