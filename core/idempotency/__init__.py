"""
BAEL Idempotency Engine
=======================

Ensures operations are executed only once.

"Ba'el acts once, but with perfect precision." — Ba'el
"""

from .idempotency_engine import (
    IdempotencyResult,
    IdempotencyEntry,
    IdempotencyConfig,
    IdempotencyStore,
    IdempotencyEngine,
    idempotency_engine,
    idempotent,
    ensure_idempotent
)

__all__ = [
    'IdempotencyResult',
    'IdempotencyEntry',
    'IdempotencyConfig',
    'IdempotencyStore',
    'IdempotencyEngine',
    'idempotency_engine',
    'idempotent',
    'ensure_idempotent'
]
