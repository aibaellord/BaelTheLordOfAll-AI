"""
BAEL Distributed Lock Engine
============================

Distributed locking for concurrent access control.

"Ba'el controls access to the fabric of reality." — Ba'el
"""

from .distributed_lock_engine import (
    # Enums
    LockType,
    LockState,

    # Data structures
    LockInfo,
    LockConfig,

    # Engine
    DistributedLock,
    LockManager,

    # Convenience
    lock_manager,
    acquire_lock,
    release_lock,
)

__all__ = [
    'LockType',
    'LockState',
    'LockInfo',
    'LockConfig',
    'DistributedLock',
    'LockManager',
    'lock_manager',
    'acquire_lock',
    'release_lock',
]
