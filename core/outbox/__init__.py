"""
BAEL Outbox Pattern Engine
==========================

Transactional outbox pattern for reliable messaging.

"Ba'el ensures no message is ever lost." — Ba'el
"""

from .outbox_engine import (
    # Enums
    OutboxStatus,
    MessagePriority,

    # Data structures
    OutboxMessage,
    OutboxConfig,

    # Engine
    OutboxProcessor,

    # Convenience
    outbox,
)

__all__ = [
    'OutboxStatus',
    'MessagePriority',
    'OutboxMessage',
    'OutboxConfig',
    'OutboxProcessor',
    'outbox',
]
