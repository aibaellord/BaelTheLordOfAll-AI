"""
BAEL Dead Letter Queue Engine
=============================

Dead letter queue for handling failed messages.

"Ba'el gives failed messages a second chance." — Ba'el
"""

from .dlq_engine import (
    # Enums
    DLQReason,
    RetryPolicy,

    # Data structures
    DeadLetter,
    DLQStats,

    # Engine
    DeadLetterQueue,

    # Convenience
    dlq,
)

__all__ = [
    'DLQReason',
    'RetryPolicy',
    'DeadLetter',
    'DLQStats',
    'DeadLetterQueue',
    'dlq',
]
