"""
BAEL Session Engine
====================

Session management with multiple storage backends.

"Ba'el maintains perfect knowledge of all visitors." — Ba'el
"""

import asyncio
import logging
import uuid
import secrets
import hashlib
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger("BAEL.Session")

T = TypeVar("T")


# ============================================================================
# ENUMS
# ============================================================================

class SessionStatus(Enum):
    """Session status."""
    ACTIVE = "active"
    EXPIRED = "expired"
    INVALIDATED = "invalidated"


class SessionBackend(Enum):
    """Session storage backend."""
    MEMORY = "memory"
    REDIS = "redis"
    DATABASE = "database"
    FILE = "file"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class SessionData:
    """Session data container."""
    data: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value."""
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a value."""
        self.data[key] = value

    def delete(self, key: str) -> bool:
        """Delete a value."""
        if key in self.data:
            del self.data[key]
            return True
        return False

    def clear(self) -> None:
        """Clear all data."""
        self.data.clear()

    def has(self, key: str) -> bool:
        """Check if key exists."""
        return key in self.data

    def keys(self) -> List[str]:
        """Get all keys."""
        return list(self.data.keys())


@dataclass
class Session:
    """A session."""
    id: str

    # Data
    data: SessionData = field(default_factory=SessionData)

    # Status
    status: SessionStatus = SessionStatus.ACTIVE

    # User
    user_id: Optional[str] = None

    # Security
    token: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    # Expiration
    expires_at: Optional[datetime] = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed_at: datetime = field(default_factory=datetime.now)

    @property
    def is_expired(self) -> bool:
        """Check if session is expired."""
        if self.status != SessionStatus.ACTIVE:
            return True
        if self.expires_at and datetime.now() > self.expires_at:
            return True
        return False

    def touch(self) -> None:
        """Update last accessed time."""
        self.last_accessed_at = datetime.now()


@dataclass
class SessionConfig:
    """Session engine configuration."""
    backend: SessionBackend = SessionBackend.MEMORY

    # Expiration
    session_lifetime_seconds: int = 3600 * 24  # 24 hours
    sliding_expiration: bool = True

    # Security
    secure_cookies: bool = True
    http_only: bool = True
    same_site: str = "lax"

    # Cleanup
    cleanup_interval_seconds: int = 300  # 5 minutes


# ============================================================================
# SESSION STORE BASE
# ============================================================================

class SessionStore:
    """Base class for session stores."""

    async def get(self, session_id: str) -> Optional[Session]:
        """Get a session."""
        raise NotImplementedError

    async def set(self, session: Session) -> None:
        """Store a session."""
        raise NotImplementedError

    async def delete(self, session_id: str) -> bool:
        """Delete a session."""
        raise NotImplementedError

    async def exists(self, session_id: str) -> bool:
        """Check if session exists."""
        raise NotImplementedError

    async def cleanup(self) -> int:
        """Cleanup expired sessions. Returns count removed."""
        raise NotImplementedError


# ============================================================================
# MEMORY SESSION STORE
# ============================================================================

class MemorySessionStore(SessionStore):
    """In-memory session store."""

    def __init__(self):
        """Initialize store."""
        self._sessions: Dict[str, Session] = {}
        self._lock = threading.RLock()

    async def get(self, session_id: str) -> Optional[Session]:
        """Get a session."""
        with self._lock:
            session = self._sessions.get(session_id)

            if session and session.is_expired:
                del self._sessions[session_id]
                return None

            return session

    async def set(self, session: Session) -> None:
        """Store a session."""
        with self._lock:
            self._sessions[session.id] = session

    async def delete(self, session_id: str) -> bool:
        """Delete a session."""
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    async def exists(self, session_id: str) -> bool:
        """Check if session exists."""
        session = await self.get(session_id)
        return session is not None

    async def cleanup(self) -> int:
        """Cleanup expired sessions."""
        count = 0

        with self._lock:
            expired = [
                sid for sid, s in self._sessions.items()
                if s.is_expired
            ]

            for sid in expired:
                del self._sessions[sid]
                count += 1

        return count

    def count(self) -> int:
        """Get session count."""
        return len(self._sessions)


# ============================================================================
# MAIN SESSION ENGINE
# ============================================================================

class SessionEngine:
    """
    Main session engine.

    Features:
    - Session creation and management
    - Multiple storage backends
    - Sliding expiration
    - Flash messages

    "Ba'el knows all who visit his realm." — Ba'el
    """

    def __init__(self, config: Optional[SessionConfig] = None):
        """Initialize session engine."""
        self.config = config or SessionConfig()

        # Store
        self._store = self._create_store()

        # Token to session mapping
        self._tokens: Dict[str, str] = {}

        # User to sessions mapping
        self._user_sessions: Dict[str, List[str]] = defaultdict(list)

        # Stats
        self._stats = defaultdict(int)

        # Cleanup task
        self._running = False
        self._cleanup_task: Optional[asyncio.Task] = None

        self._lock = threading.RLock()

        logger.info("SessionEngine initialized")

    def _create_store(self) -> SessionStore:
        """Create storage backend."""
        if self.config.backend == SessionBackend.MEMORY:
            return MemorySessionStore()
        else:
            return MemorySessionStore()  # Default to memory

    # ========================================================================
    # SESSION MANAGEMENT
    # ========================================================================

    async def create(
        self,
        user_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Session:
        """
        Create a new session.

        Args:
            user_id: Optional user ID
            data: Initial session data
            ip_address: Client IP
            user_agent: Client user agent

        Returns:
            Session
        """
        session = Session(
            id=str(uuid.uuid4()),
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.now() + timedelta(seconds=self.config.session_lifetime_seconds)
        )

        if data:
            session.data = SessionData(data=data)

        # Store session
        await self._store.set(session)

        # Index by token
        with self._lock:
            self._tokens[session.token] = session.id

            if user_id:
                self._user_sessions[user_id].append(session.id)

        self._stats['sessions_created'] += 1

        logger.debug(f"Created session: {session.id}")

        return session

    async def get(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        session = await self._store.get(session_id)

        if session and not session.is_expired:
            # Sliding expiration
            if self.config.sliding_expiration:
                session.touch()
                session.expires_at = datetime.now() + timedelta(
                    seconds=self.config.session_lifetime_seconds
                )
                await self._store.set(session)

            return session

        return None

    async def get_by_token(self, token: str) -> Optional[Session]:
        """Get a session by token."""
        with self._lock:
            session_id = self._tokens.get(token)

        if session_id:
            return await self.get(session_id)

        return None

    async def update(self, session: Session) -> None:
        """Update a session."""
        session.touch()
        await self._store.set(session)

    async def destroy(self, session_id: str) -> bool:
        """Destroy a session."""
        session = await self._store.get(session_id)

        if session:
            # Remove from indices
            with self._lock:
                if session.token in self._tokens:
                    del self._tokens[session.token]

                if session.user_id and session.id in self._user_sessions.get(session.user_id, []):
                    self._user_sessions[session.user_id].remove(session.id)

            # Delete from store
            await self._store.delete(session_id)

            self._stats['sessions_destroyed'] += 1

            return True

        return False

    async def invalidate(self, session_id: str) -> bool:
        """Invalidate a session (mark as invalid but keep)."""
        session = await self._store.get(session_id)

        if session:
            session.status = SessionStatus.INVALIDATED
            await self._store.set(session)
            return True

        return False

    # ========================================================================
    # USER SESSIONS
    # ========================================================================

    async def get_user_sessions(self, user_id: str) -> List[Session]:
        """Get all sessions for a user."""
        sessions = []

        with self._lock:
            session_ids = list(self._user_sessions.get(user_id, []))

        for session_id in session_ids:
            session = await self.get(session_id)
            if session:
                sessions.append(session)

        return sessions

    async def destroy_user_sessions(
        self,
        user_id: str,
        except_session_id: Optional[str] = None
    ) -> int:
        """Destroy all sessions for a user."""
        count = 0

        with self._lock:
            session_ids = list(self._user_sessions.get(user_id, []))

        for session_id in session_ids:
            if session_id != except_session_id:
                if await self.destroy(session_id):
                    count += 1

        return count

    # ========================================================================
    # DATA HELPERS
    # ========================================================================

    async def get_data(self, session_id: str, key: str, default: Any = None) -> Any:
        """Get a value from session data."""
        session = await self.get(session_id)

        if session:
            return session.data.get(key, default)

        return default

    async def set_data(self, session_id: str, key: str, value: Any) -> bool:
        """Set a value in session data."""
        session = await self.get(session_id)

        if session:
            session.data.set(key, value)
            await self.update(session)
            return True

        return False

    async def delete_data(self, session_id: str, key: str) -> bool:
        """Delete a value from session data."""
        session = await self.get(session_id)

        if session:
            if session.data.delete(key):
                await self.update(session)
                return True

        return False

    # ========================================================================
    # FLASH MESSAGES
    # ========================================================================

    async def flash(self, session_id: str, message: str, category: str = "info") -> bool:
        """Add a flash message."""
        session = await self.get(session_id)

        if session:
            flashes = session.data.get('_flashes', [])
            flashes.append({'message': message, 'category': category})
            session.data.set('_flashes', flashes)
            await self.update(session)
            return True

        return False

    async def get_flashes(
        self,
        session_id: str,
        category: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Get and clear flash messages."""
        session = await self.get(session_id)

        if not session:
            return []

        flashes = session.data.get('_flashes', [])

        if category:
            result = [f for f in flashes if f['category'] == category]
            remaining = [f for f in flashes if f['category'] != category]
            session.data.set('_flashes', remaining)
        else:
            result = flashes
            session.data.delete('_flashes')

        await self.update(session)

        return result

    # ========================================================================
    # CLEANUP
    # ========================================================================

    async def start_cleanup(self) -> None:
        """Start cleanup task."""
        if self._running:
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop_cleanup(self) -> None:
        """Stop cleanup task."""
        self._running = False

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    async def _cleanup_loop(self) -> None:
        """Cleanup loop."""
        while self._running:
            try:
                await asyncio.sleep(self.config.cleanup_interval_seconds)

                count = await self._store.cleanup()

                if count > 0:
                    logger.debug(f"Cleaned up {count} expired sessions")
                    self._stats['sessions_cleaned'] += count

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")

    # ========================================================================
    # STATUS
    # ========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        store_count = 0
        if isinstance(self._store, MemorySessionStore):
            store_count = self._store.count()

        return {
            'backend': self.config.backend.value,
            'sessions': store_count,
            'cleanup_running': self._running,
            'stats': dict(self._stats)
        }


# ============================================================================
# CONVENIENCE INSTANCE
# ============================================================================

session_engine = SessionEngine()
