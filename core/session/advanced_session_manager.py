#!/usr/bin/env python3
"""
BAEL - Advanced Session Manager
Comprehensive session and user state management.

Features:
- Session creation and lifecycle
- Session storage backends
- Session data management
- Session expiration
- Session regeneration
- Concurrent session handling
- Session events
- Secure session IDs
- Session serialization
- Flash messages
"""

import asyncio
import base64
import hashlib
import hmac
import logging
import os
import pickle
import secrets
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import (Any, Awaitable, Callable, Dict, Generic, List, Optional,
                    Set, Tuple, TypeVar, Union)

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class SessionState(Enum):
    """Session states."""
    ACTIVE = "active"
    EXPIRED = "expired"
    INVALIDATED = "invalidated"
    LOCKED = "locked"


class SessionEvent(Enum):
    """Session events."""
    CREATED = "created"
    ACCESSED = "accessed"
    MODIFIED = "modified"
    EXPIRED = "expired"
    DESTROYED = "destroyed"
    REGENERATED = "regenerated"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class SessionData:
    """Session data container."""
    session_id: str = ""
    user_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    flash_messages: List[Dict[str, Any]] = field(default_factory=list)
    state: SessionState = SessionState.ACTIVE
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    expires_at: float = 0.0
    ip_address: str = ""
    user_agent: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        if self.expires_at == 0:
            return False
        return time.time() > self.expires_at

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at

    @property
    def idle_seconds(self) -> float:
        return time.time() - self.last_accessed


@dataclass
class SessionConfig:
    """Session configuration."""
    lifetime: float = 3600.0  # 1 hour
    idle_timeout: float = 1800.0  # 30 minutes
    regenerate_interval: float = 900.0  # 15 minutes
    secure: bool = True
    http_only: bool = True
    same_site: str = "lax"
    cookie_name: str = "session_id"
    path: str = "/"
    domain: str = ""


@dataclass
class SessionCookie:
    """Session cookie configuration."""
    name: str = "session_id"
    value: str = ""
    expires: Optional[datetime] = None
    max_age: Optional[int] = None
    path: str = "/"
    domain: str = ""
    secure: bool = True
    http_only: bool = True
    same_site: str = "lax"

    def to_header(self) -> str:
        """Convert to Set-Cookie header."""
        parts = [f"{self.name}={self.value}"]

        if self.expires:
            parts.append(f"Expires={self.expires.strftime('%a, %d %b %Y %H:%M:%S GMT')}")

        if self.max_age is not None:
            parts.append(f"Max-Age={self.max_age}")

        if self.path:
            parts.append(f"Path={self.path}")

        if self.domain:
            parts.append(f"Domain={self.domain}")

        if self.secure:
            parts.append("Secure")

        if self.http_only:
            parts.append("HttpOnly")

        if self.same_site:
            parts.append(f"SameSite={self.same_site}")

        return "; ".join(parts)


# =============================================================================
# SESSION ID GENERATOR
# =============================================================================

class SessionIdGenerator:
    """Generates secure session IDs."""

    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or secrets.token_hex(32)

    def generate(self, length: int = 32) -> str:
        """Generate a secure session ID."""
        random_bytes = secrets.token_bytes(length)
        timestamp = str(time.time()).encode()

        combined = random_bytes + timestamp
        signature = hmac.new(
            self.secret_key.encode(),
            combined,
            hashlib.sha256
        ).digest()

        session_id = base64.urlsafe_b64encode(
            random_bytes + signature[:8]
        ).decode().rstrip("=")

        return session_id

    def validate(self, session_id: str) -> bool:
        """Validate session ID format."""
        if not session_id:
            return False

        try:
            padding = 4 - len(session_id) % 4
            if padding != 4:
                session_id += "=" * padding

            decoded = base64.urlsafe_b64decode(session_id)
            return len(decoded) >= 32
        except Exception:
            return False


# =============================================================================
# STORAGE BACKENDS
# =============================================================================

class SessionStore(ABC):
    """Abstract session store."""

    @abstractmethod
    async def get(self, session_id: str) -> Optional[SessionData]:
        pass

    @abstractmethod
    async def set(self, session: SessionData) -> bool:
        pass

    @abstractmethod
    async def delete(self, session_id: str) -> bool:
        pass

    @abstractmethod
    async def exists(self, session_id: str) -> bool:
        pass

    @abstractmethod
    async def cleanup(self) -> int:
        pass


class InMemorySessionStore(SessionStore):
    """In-memory session store."""

    def __init__(self, max_sessions: int = 10000):
        self._sessions: Dict[str, SessionData] = {}
        self._max_sessions = max_sessions
        self._lock = asyncio.Lock()

    async def get(self, session_id: str) -> Optional[SessionData]:
        session = self._sessions.get(session_id)

        if session and session.is_expired:
            await self.delete(session_id)
            return None

        if session:
            session.last_accessed = time.time()

        return session

    async def set(self, session: SessionData) -> bool:
        async with self._lock:
            if len(self._sessions) >= self._max_sessions:
                oldest_id = min(
                    self._sessions.keys(),
                    key=lambda k: self._sessions[k].last_accessed
                )
                del self._sessions[oldest_id]

            self._sessions[session.session_id] = session
            return True

    async def delete(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    async def exists(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        return session is not None and not session.is_expired

    async def cleanup(self) -> int:
        expired = [
            sid for sid, session in self._sessions.items()
            if session.is_expired
        ]

        for sid in expired:
            del self._sessions[sid]

        return len(expired)

    async def get_by_user(self, user_id: str) -> List[SessionData]:
        return [
            s for s in self._sessions.values()
            if s.user_id == user_id and not s.is_expired
        ]

    @property
    def count(self) -> int:
        return len(self._sessions)


# =============================================================================
# SESSION SERIALIZER
# =============================================================================

class SessionSerializer:
    """Serializes session data."""

    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or secrets.token_hex(32)

    def serialize(self, session: SessionData) -> bytes:
        data = pickle.dumps(session)

        signature = hmac.new(
            self.secret_key.encode(),
            data,
            hashlib.sha256
        ).digest()

        return signature + data

    def deserialize(self, data: bytes) -> Optional[SessionData]:
        if len(data) < 32:
            return None

        signature = data[:32]
        payload = data[32:]

        expected = hmac.new(
            self.secret_key.encode(),
            payload,
            hashlib.sha256
        ).digest()

        if not hmac.compare_digest(signature, expected):
            return None

        try:
            return pickle.loads(payload)
        except Exception:
            return None


# =============================================================================
# EVENT EMITTER
# =============================================================================

class SessionEventEmitter:
    """Emits session events."""

    def __init__(self):
        self._handlers: Dict[SessionEvent, List[Callable]] = defaultdict(list)

    def on(self, event: SessionEvent, handler: Callable) -> None:
        self._handlers[event].append(handler)

    def off(self, event: SessionEvent, handler: Callable) -> None:
        if handler in self._handlers[event]:
            self._handlers[event].remove(handler)

    async def emit(
        self,
        event: SessionEvent,
        session: SessionData,
        **kwargs
    ) -> None:
        for handler in self._handlers[event]:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(session, **kwargs)
                else:
                    handler(session, **kwargs)
            except Exception as e:
                logger.error(f"Event handler error: {e}")


# =============================================================================
# ADVANCED SESSION MANAGER
# =============================================================================

class AdvancedSessionManager:
    """
    Comprehensive Session Manager for BAEL.
    """

    def __init__(
        self,
        store: SessionStore = None,
        config: SessionConfig = None,
        secret_key: str = None
    ):
        self.store = store or InMemorySessionStore()
        self.config = config or SessionConfig()
        self.secret_key = secret_key or secrets.token_hex(32)

        self._id_generator = SessionIdGenerator(self.secret_key)
        self._serializer = SessionSerializer(self.secret_key)
        self._events = SessionEventEmitter()

        self._cleanup_task: Optional[asyncio.Task] = None

    # -------------------------------------------------------------------------
    # SESSION LIFECYCLE
    # -------------------------------------------------------------------------

    async def create(
        self,
        user_id: str = None,
        data: Dict[str, Any] = None,
        ip_address: str = "",
        user_agent: str = ""
    ) -> SessionData:
        """Create a new session."""
        session_id = self._id_generator.generate()
        expires_at = time.time() + self.config.lifetime

        session = SessionData(
            session_id=session_id,
            user_id=user_id,
            data=data or {},
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )

        await self.store.set(session)
        await self._events.emit(SessionEvent.CREATED, session)

        return session

    async def get(self, session_id: str) -> Optional[SessionData]:
        """Get a session."""
        if not self._id_generator.validate(session_id):
            return None

        session = await self.store.get(session_id)

        if not session:
            return None

        if session.state != SessionState.ACTIVE:
            return None

        if session.idle_seconds > self.config.idle_timeout:
            await self.destroy(session_id)
            return None

        await self._events.emit(SessionEvent.ACCESSED, session)

        if session.age_seconds > self.config.regenerate_interval:
            session = await self.regenerate(session_id)

        return session

    async def update(
        self,
        session_id: str,
        data: Dict[str, Any]
    ) -> Optional[SessionData]:
        """Update session data."""
        session = await self.store.get(session_id)

        if not session:
            return None

        session.data.update(data)
        session.last_accessed = time.time()

        await self.store.set(session)
        await self._events.emit(SessionEvent.MODIFIED, session)

        return session

    async def destroy(self, session_id: str) -> bool:
        """Destroy a session."""
        session = await self.store.get(session_id)

        if session:
            session.state = SessionState.INVALIDATED
            await self._events.emit(SessionEvent.DESTROYED, session)

        return await self.store.delete(session_id)

    async def regenerate(self, session_id: str) -> Optional[SessionData]:
        """Regenerate session ID."""
        old_session = await self.store.get(session_id)

        if not old_session:
            return None

        new_session_id = self._id_generator.generate()

        new_session = SessionData(
            session_id=new_session_id,
            user_id=old_session.user_id,
            data=old_session.data.copy(),
            flash_messages=old_session.flash_messages.copy(),
            expires_at=time.time() + self.config.lifetime,
            ip_address=old_session.ip_address,
            user_agent=old_session.user_agent,
            metadata=old_session.metadata.copy()
        )

        await self.store.delete(session_id)
        await self.store.set(new_session)
        await self._events.emit(SessionEvent.REGENERATED, new_session, old_id=session_id)

        return new_session

    # -------------------------------------------------------------------------
    # DATA OPERATIONS
    # -------------------------------------------------------------------------

    async def set_value(
        self,
        session_id: str,
        key: str,
        value: Any
    ) -> bool:
        session = await self.store.get(session_id)

        if not session:
            return False

        session.data[key] = value
        session.last_accessed = time.time()

        await self.store.set(session)
        return True

    async def get_value(
        self,
        session_id: str,
        key: str,
        default: Any = None
    ) -> Any:
        session = await self.store.get(session_id)

        if not session:
            return default

        return session.data.get(key, default)

    async def delete_value(
        self,
        session_id: str,
        key: str
    ) -> bool:
        session = await self.store.get(session_id)

        if not session or key not in session.data:
            return False

        del session.data[key]
        session.last_accessed = time.time()

        await self.store.set(session)
        return True

    async def clear_data(self, session_id: str) -> bool:
        session = await self.store.get(session_id)

        if not session:
            return False

        session.data.clear()
        session.last_accessed = time.time()

        await self.store.set(session)
        return True

    # -------------------------------------------------------------------------
    # FLASH MESSAGES
    # -------------------------------------------------------------------------

    async def flash(
        self,
        session_id: str,
        message: str,
        category: str = "info"
    ) -> bool:
        session = await self.store.get(session_id)

        if not session:
            return False

        session.flash_messages.append({
            "message": message,
            "category": category,
            "timestamp": time.time()
        })

        await self.store.set(session)
        return True

    async def get_flashed(
        self,
        session_id: str,
        category: str = None
    ) -> List[Dict[str, Any]]:
        session = await self.store.get(session_id)

        if not session:
            return []

        messages = session.flash_messages

        if category:
            messages = [m for m in messages if m["category"] == category]
            session.flash_messages = [
                m for m in session.flash_messages
                if m["category"] != category
            ]
        else:
            session.flash_messages = []

        await self.store.set(session)
        return messages

    # -------------------------------------------------------------------------
    # USER SESSIONS
    # -------------------------------------------------------------------------

    async def get_user_sessions(self, user_id: str) -> List[SessionData]:
        if isinstance(self.store, InMemorySessionStore):
            return await self.store.get_by_user(user_id)
        return []

    async def destroy_user_sessions(
        self,
        user_id: str,
        except_session: str = None
    ) -> int:
        sessions = await self.get_user_sessions(user_id)
        count = 0

        for session in sessions:
            if except_session and session.session_id == except_session:
                continue

            await self.destroy(session.session_id)
            count += 1

        return count

    async def count_user_sessions(self, user_id: str) -> int:
        sessions = await self.get_user_sessions(user_id)
        return len(sessions)

    # -------------------------------------------------------------------------
    # COOKIE HELPERS
    # -------------------------------------------------------------------------

    def create_cookie(self, session: SessionData) -> SessionCookie:
        return SessionCookie(
            name=self.config.cookie_name,
            value=session.session_id,
            max_age=int(self.config.lifetime),
            path=self.config.path,
            domain=self.config.domain,
            secure=self.config.secure,
            http_only=self.config.http_only,
            same_site=self.config.same_site
        )

    def create_delete_cookie(self) -> SessionCookie:
        return SessionCookie(
            name=self.config.cookie_name,
            value="",
            max_age=0,
            path=self.config.path,
            domain=self.config.domain,
            secure=self.config.secure,
            http_only=self.config.http_only,
            same_site=self.config.same_site
        )

    def parse_cookie(self, cookie_header: str) -> Optional[str]:
        if not cookie_header:
            return None

        cookies = {}

        for pair in cookie_header.split(";"):
            pair = pair.strip()

            if "=" in pair:
                key, value = pair.split("=", 1)
                cookies[key.strip()] = value.strip()

        return cookies.get(self.config.cookie_name)

    # -------------------------------------------------------------------------
    # EVENTS
    # -------------------------------------------------------------------------

    def on_event(self, event: SessionEvent, handler: Callable) -> None:
        self._events.on(event, handler)

    def off_event(self, event: SessionEvent, handler: Callable) -> None:
        self._events.off(event, handler)

    # -------------------------------------------------------------------------
    # CLEANUP
    # -------------------------------------------------------------------------

    async def start_cleanup(self, interval: float = 60.0) -> None:
        self._cleanup_task = asyncio.create_task(
            self._cleanup_loop(interval)
        )

    async def stop_cleanup(self) -> None:
        if self._cleanup_task:
            self._cleanup_task.cancel()

            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    async def _cleanup_loop(self, interval: float) -> None:
        while True:
            try:
                await asyncio.sleep(interval)
                count = await self.store.cleanup()

                if count > 0:
                    logger.info(f"Cleaned up {count} expired sessions")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")

    # -------------------------------------------------------------------------
    # SECURITY
    # -------------------------------------------------------------------------

    async def validate_session(
        self,
        session_id: str,
        ip_address: str = None,
        user_agent: str = None
    ) -> Tuple[bool, str]:
        session = await self.store.get(session_id)

        if not session:
            return False, "Session not found"

        if session.state != SessionState.ACTIVE:
            return False, f"Session is {session.state.value}"

        if session.is_expired:
            return False, "Session expired"

        if ip_address and session.ip_address:
            if ip_address != session.ip_address:
                return False, "IP address mismatch"

        if user_agent and session.user_agent:
            if user_agent != session.user_agent:
                return False, "User agent mismatch"

        return True, "Valid"

    async def lock_session(self, session_id: str) -> bool:
        session = await self.store.get(session_id)

        if not session:
            return False

        session.state = SessionState.LOCKED
        await self.store.set(session)
        return True

    async def unlock_session(self, session_id: str) -> bool:
        session = await self.store.get(session_id)

        if not session:
            return False

        session.state = SessionState.ACTIVE
        await self.store.set(session)
        return True

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    async def get_stats(self) -> Dict[str, Any]:
        stats = {
            "store_type": type(self.store).__name__,
            "lifetime": self.config.lifetime,
            "idle_timeout": self.config.idle_timeout
        }

        if isinstance(self.store, InMemorySessionStore):
            stats["active_sessions"] = self.store.count

        return stats


# =============================================================================
# MIDDLEWARE
# =============================================================================

class SessionMiddleware:
    """Session middleware for web frameworks."""

    def __init__(self, manager: AdvancedSessionManager):
        self.manager = manager

    async def process_request(
        self,
        cookie_header: str,
        ip_address: str = "",
        user_agent: str = ""
    ) -> Optional[SessionData]:
        session_id = self.manager.parse_cookie(cookie_header)

        if session_id:
            valid, _ = await self.manager.validate_session(
                session_id, ip_address, user_agent
            )

            if valid:
                return await self.manager.get(session_id)

        return await self.manager.create(
            ip_address=ip_address,
            user_agent=user_agent
        )

    def process_response(
        self,
        session: SessionData,
        response_headers: Dict[str, str]
    ) -> None:
        cookie = self.manager.create_cookie(session)
        response_headers["Set-Cookie"] = cookie.to_header()


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Advanced Session Manager."""
    print("=" * 70)
    print("BAEL - ADVANCED SESSION MANAGER DEMO")
    print("Comprehensive Session Management")
    print("=" * 70)
    print()

    config = SessionConfig(
        lifetime=3600.0,
        idle_timeout=1800.0,
        secure=True
    )

    manager = AdvancedSessionManager(config=config)

    # 1. Create Session
    print("1. CREATE SESSION:")
    print("-" * 40)

    session = await manager.create(
        user_id="user-123",
        data={"theme": "dark", "lang": "en"},
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0"
    )

    print(f"   Session ID: {session.session_id[:16]}...")
    print(f"   User ID: {session.user_id}")
    print(f"   Data: {session.data}")
    print()

    # 2. Update Session Data
    print("2. UPDATE SESSION DATA:")
    print("-" * 40)

    await manager.set_value(session.session_id, "cart_items", 5)
    cart = await manager.get_value(session.session_id, "cart_items")
    print(f"   Cart items: {cart}")
    print()

    # 3. Flash Messages
    print("3. FLASH MESSAGES:")
    print("-" * 40)

    await manager.flash(session.session_id, "Welcome back!", "success")
    await manager.flash(session.session_id, "New features", "info")

    messages = await manager.get_flashed(session.session_id)
    for msg in messages:
        print(f"   [{msg['category']}] {msg['message']}")
    print()

    # 4. Session Cookie
    print("4. SESSION COOKIE:")
    print("-" * 40)

    cookie = manager.create_cookie(session)
    print(f"   Cookie: {cookie.to_header()[:50]}...")
    print()

    # 5. Multiple Sessions
    print("5. MULTIPLE USER SESSIONS:")
    print("-" * 40)

    session2 = await manager.create(user_id="user-123")
    user_sessions = await manager.get_user_sessions("user-123")
    print(f"   User has {len(user_sessions)} active sessions")
    print()

    # 6. Validate Session
    print("6. VALIDATE SESSION:")
    print("-" * 40)

    valid, message = await manager.validate_session(
        session.session_id,
        ip_address="192.168.1.100"
    )
    print(f"   Valid: {valid}, Message: {message}")
    print()

    # 7. Regenerate
    print("7. REGENERATE SESSION:")
    print("-" * 40)

    old_id = session.session_id
    new_session = await manager.regenerate(old_id)
    print(f"   Old ID: {old_id[:16]}...")
    print(f"   New ID: {new_session.session_id[:16]}...")
    print()

    # 8. Statistics
    print("8. STATISTICS:")
    print("-" * 40)

    stats = await manager.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()

    # Cleanup
    await manager.destroy(new_session.session_id)

    print("=" * 70)
    print("DEMO COMPLETE - Advanced Session Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
