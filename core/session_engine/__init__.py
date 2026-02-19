"""
BAEL Session Engine
====================

Session management with multiple backends.

"Ba'el remembers all who enter his domain." — Ba'el
"""

from .session_engine import (
    # Enums
    SessionStatus,
    SessionBackend,

    # Data structures
    Session,
    SessionData,
    SessionConfig,

    # Backends
    MemorySessionStore,

    # Engine
    SessionEngine,

    # Instance
    session_engine,
)

__all__ = [
    # Enums
    "SessionStatus",
    "SessionBackend",

    # Data structures
    "Session",
    "SessionData",
    "SessionConfig",

    # Backends
    "MemorySessionStore",

    # Engine
    "SessionEngine",

    # Instance
    "session_engine",
]
