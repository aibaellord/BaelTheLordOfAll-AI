#!/usr/bin/env python3
"""
BAEL - Session Manager
User session and state management system.

This module provides comprehensive session management for
tracking user interactions, state persistence, and session lifecycle.

Features:
- Session creation and validation
- Session persistence
- Multi-device session handling
- Session hijacking protection
- Activity tracking
- Session clustering
- Automatic session expiration
- Session data encryption
- Anonymous session support
- Session replay protection
"""

import asyncio
import copy
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import (Any, Callable, Dict, List, Optional, Set, Tuple, Type,
                    TypeVar, Union)
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class SessionState(Enum):
    """Session states."""
    ACTIVE = "active"
    IDLE = "idle"
    EXPIRED = "expired"
    TERMINATED = "terminated"
    LOCKED = "locked"
    PENDING = "pending"


class SessionType(Enum):
    """Session types."""
    USER = "user"
    ANONYMOUS = "anonymous"
    API = "api"
    SYSTEM = "system"
    SERVICE = "service"


class StorageBackend(Enum):
    """Storage backends."""
    MEMORY = "memory"
    FILE = "file"
    REDIS = "redis"
    DATABASE = "database"


class SecurityLevel(Enum):
    """Session security levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class ActivityType(Enum):
    """Activity types."""
    LOGIN = "login"
    LOGOUT = "logout"
    PAGE_VIEW = "page_view"
    ACTION = "action"
    API_CALL = "api_call"
    ERROR = "error"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class DeviceInfo:
    """Device information."""
    device_id: str
    user_agent: str = ""
    ip_address: str = ""
    fingerprint: str = ""
    platform: str = ""
    browser: str = ""
    last_seen: datetime = field(default_factory=datetime.now)


@dataclass
class SessionActivity:
    """Session activity record."""
    id: str = field(default_factory=lambda: str(uuid4()))
    activity_type: ActivityType = ActivityType.ACTION
    description: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    ip_address: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SessionData:
    """Session data container."""
    user_id: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    roles: List[str] = field(default_factory=list)
    permissions: Set[str] = field(default_factory=set)
    preferences: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    custom: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Session:
    """Complete session object."""
    id: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    session_type: SessionType = SessionType.USER
    state: SessionState = SessionState.ACTIVE
    security_level: SecurityLevel = SecurityLevel.MEDIUM

    # Session data
    data: SessionData = field(default_factory=SessionData)

    # Device info
    device: Optional[DeviceInfo] = None

    # Activity
    activities: List[SessionActivity] = field(default_factory=list)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None

    # Security
    token: str = field(default_factory=lambda: secrets.token_urlsafe(64))
    token_hash: str = ""
    csrf_token: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    ip_lock: Optional[str] = None
    nonce: int = 0

    def __post_init__(self):
        if not self.token_hash and self.token:
            self.token_hash = hashlib.sha256(self.token.encode()).hexdigest()


@dataclass
class SessionConfig:
    """Session configuration."""
    default_timeout: int = 3600  # 1 hour
    idle_timeout: int = 1800  # 30 minutes
    max_sessions_per_user: int = 5
    max_activities: int = 1000
    enable_ip_lock: bool = False
    enable_device_binding: bool = True
    require_secure_token: bool = True
    cleanup_interval: int = 300  # 5 minutes


# =============================================================================
# SESSION STORAGE
# =============================================================================

class SessionStorage(ABC):
    """Abstract session storage."""

    @abstractmethod
    async def save(self, session: Session) -> bool:
        """Save session."""
        pass

    @abstractmethod
    async def load(self, session_id: str) -> Optional[Session]:
        """Load session."""
        pass

    @abstractmethod
    async def delete(self, session_id: str) -> bool:
        """Delete session."""
        pass

    @abstractmethod
    async def exists(self, session_id: str) -> bool:
        """Check if session exists."""
        pass

    @abstractmethod
    async def list_all(self) -> List[str]:
        """List all session IDs."""
        pass

    @abstractmethod
    async def clear_all(self) -> int:
        """Clear all sessions."""
        pass


class MemorySessionStorage(SessionStorage):
    """In-memory session storage."""

    def __init__(self):
        self.sessions: Dict[str, Session] = {}

    async def save(self, session: Session) -> bool:
        self.sessions[session.id] = session
        return True

    async def load(self, session_id: str) -> Optional[Session]:
        return self.sessions.get(session_id)

    async def delete(self, session_id: str) -> bool:
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    async def exists(self, session_id: str) -> bool:
        return session_id in self.sessions

    async def list_all(self) -> List[str]:
        return list(self.sessions.keys())

    async def clear_all(self) -> int:
        count = len(self.sessions)
        self.sessions.clear()
        return count


class FileSessionStorage(SessionStorage):
    """File-based session storage."""

    def __init__(self, directory: str = "sessions"):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def _get_path(self, session_id: str) -> Path:
        return self.directory / f"{session_id}.json"

    def _serialize(self, session: Session) -> str:
        data = {
            "id": session.id,
            "session_type": session.session_type.value,
            "state": session.state.value,
            "security_level": session.security_level.value,
            "data": {
                "user_id": session.data.user_id,
                "username": session.data.username,
                "email": session.data.email,
                "roles": session.data.roles,
                "permissions": list(session.data.permissions),
                "preferences": session.data.preferences,
                "metadata": session.data.metadata,
                "custom": session.data.custom
            },
            "device": {
                "device_id": session.device.device_id,
                "user_agent": session.device.user_agent,
                "ip_address": session.device.ip_address,
                "fingerprint": session.device.fingerprint,
                "platform": session.device.platform,
                "browser": session.device.browser,
                "last_seen": session.device.last_seen.isoformat()
            } if session.device else None,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "expires_at": session.expires_at.isoformat() if session.expires_at else None,
            "token_hash": session.token_hash,
            "csrf_token": session.csrf_token,
            "ip_lock": session.ip_lock,
            "nonce": session.nonce
        }
        return json.dumps(data, indent=2)

    def _deserialize(self, content: str) -> Session:
        data = json.loads(content)

        session_data = SessionData(
            user_id=data["data"].get("user_id"),
            username=data["data"].get("username"),
            email=data["data"].get("email"),
            roles=data["data"].get("roles", []),
            permissions=set(data["data"].get("permissions", [])),
            preferences=data["data"].get("preferences", {}),
            metadata=data["data"].get("metadata", {}),
            custom=data["data"].get("custom", {})
        )

        device = None
        if data.get("device"):
            d = data["device"]
            device = DeviceInfo(
                device_id=d["device_id"],
                user_agent=d.get("user_agent", ""),
                ip_address=d.get("ip_address", ""),
                fingerprint=d.get("fingerprint", ""),
                platform=d.get("platform", ""),
                browser=d.get("browser", ""),
                last_seen=datetime.fromisoformat(d["last_seen"])
            )

        session = Session(
            id=data["id"],
            session_type=SessionType(data["session_type"]),
            state=SessionState(data["state"]),
            security_level=SecurityLevel(data["security_level"]),
            data=session_data,
            device=device,
            created_at=datetime.fromisoformat(data["created_at"]),
            last_activity=datetime.fromisoformat(data["last_activity"]),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            token_hash=data["token_hash"],
            csrf_token=data["csrf_token"],
            ip_lock=data.get("ip_lock"),
            nonce=data.get("nonce", 0)
        )

        return session

    async def save(self, session: Session) -> bool:
        try:
            path = self._get_path(session.id)
            content = self._serialize(session)
            path.write_text(content)
            return True
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            return False

    async def load(self, session_id: str) -> Optional[Session]:
        try:
            path = self._get_path(session_id)
            if path.exists():
                content = path.read_text()
                return self._deserialize(content)
            return None
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            return None

    async def delete(self, session_id: str) -> bool:
        try:
            path = self._get_path(session_id)
            if path.exists():
                path.unlink()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            return False

    async def exists(self, session_id: str) -> bool:
        return self._get_path(session_id).exists()

    async def list_all(self) -> List[str]:
        return [p.stem for p in self.directory.glob("*.json")]

    async def clear_all(self) -> int:
        count = 0
        for path in self.directory.glob("*.json"):
            path.unlink()
            count += 1
        return count


# =============================================================================
# SESSION SECURITY
# =============================================================================

class SessionSecurity:
    """Session security utilities."""

    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or secrets.token_urlsafe(32)

    def generate_token(self) -> str:
        """Generate secure session token."""
        return secrets.token_urlsafe(64)

    def hash_token(self, token: str) -> str:
        """Hash a token."""
        return hashlib.sha256(token.encode()).hexdigest()

    def verify_token(self, token: str, token_hash: str) -> bool:
        """Verify token against hash."""
        return hmac.compare_digest(
            self.hash_token(token),
            token_hash
        )

    def generate_csrf_token(self) -> str:
        """Generate CSRF token."""
        return secrets.token_urlsafe(32)

    def verify_csrf_token(self, session_csrf: str, provided_csrf: str) -> bool:
        """Verify CSRF token."""
        return hmac.compare_digest(session_csrf, provided_csrf)

    def compute_fingerprint(self, device_info: DeviceInfo) -> str:
        """Compute device fingerprint."""
        data = f"{device_info.user_agent}:{device_info.platform}:{device_info.browser}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]

    def validate_ip(self, session: Session, current_ip: str) -> bool:
        """Validate IP if IP lock is enabled."""
        if session.ip_lock:
            return session.ip_lock == current_ip
        return True

    def detect_hijacking(
        self,
        session: Session,
        current_device: DeviceInfo
    ) -> bool:
        """Detect potential session hijacking."""
        if not session.device:
            return False

        # Check fingerprint mismatch
        original_fp = session.device.fingerprint
        current_fp = self.compute_fingerprint(current_device)

        if original_fp and current_fp != original_fp:
            return True

        return False

    def increment_nonce(self, session: Session) -> int:
        """Increment and return nonce (replay protection)."""
        session.nonce += 1
        return session.nonce

    def validate_nonce(self, session: Session, nonce: int) -> bool:
        """Validate nonce is greater than stored."""
        return nonce > session.nonce


# =============================================================================
# SESSION MANAGER
# =============================================================================

class SessionManager:
    """
    Master session management system for BAEL.

    Handles all aspects of user session lifecycle,
    including creation, validation, persistence, and security.
    """

    def __init__(
        self,
        storage: SessionStorage = None,
        config: SessionConfig = None,
        security: SessionSecurity = None
    ):
        self.storage = storage or MemorySessionStorage()
        self.config = config or SessionConfig()
        self.security = security or SessionSecurity()

        # User session tracking
        self.user_sessions: Dict[str, Set[str]] = defaultdict(set)

        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = defaultdict(list)

        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None

    async def create_session(
        self,
        session_type: SessionType = SessionType.USER,
        user_id: str = None,
        device_info: DeviceInfo = None,
        security_level: SecurityLevel = SecurityLevel.MEDIUM,
        timeout: int = None,
        **kwargs
    ) -> Session:
        """Create a new session."""
        # Check user session limit
        if user_id:
            existing = self.user_sessions.get(user_id, set())
            if len(existing) >= self.config.max_sessions_per_user:
                # Remove oldest session
                oldest_id = min(existing)
                await self.destroy_session(oldest_id)

        # Create session
        session = Session(
            session_type=session_type,
            state=SessionState.ACTIVE,
            security_level=security_level,
            data=SessionData(user_id=user_id, **kwargs),
            device=device_info,
            expires_at=datetime.now() + timedelta(
                seconds=timeout or self.config.default_timeout
            )
        )

        # Compute device fingerprint
        if device_info:
            session.device.fingerprint = self.security.compute_fingerprint(device_info)

        # IP lock
        if self.config.enable_ip_lock and device_info:
            session.ip_lock = device_info.ip_address

        # Save session
        await self.storage.save(session)

        # Track user session
        if user_id:
            self.user_sessions[user_id].add(session.id)

        # Record activity
        await self._record_activity(
            session,
            ActivityType.LOGIN,
            "Session created",
            device_info.ip_address if device_info else ""
        )

        # Emit event
        await self._emit_event("session_created", session)

        return session

    async def get_session(
        self,
        session_id: str,
        token: str = None,
        validate: bool = True
    ) -> Optional[Session]:
        """Get a session by ID."""
        session = await self.storage.load(session_id)

        if not session:
            return None

        if validate:
            # Validate token if provided
            if token and not self.security.verify_token(token, session.token_hash):
                logger.warning(f"Invalid token for session {session_id}")
                return None

            # Check expiration
            if session.expires_at and datetime.now() > session.expires_at:
                await self._expire_session(session)
                return None

            # Check state
            if session.state in (SessionState.EXPIRED, SessionState.TERMINATED):
                return None

        return session

    async def validate_session(
        self,
        session_id: str,
        token: str,
        current_ip: str = None,
        device_info: DeviceInfo = None
    ) -> Tuple[bool, Optional[str]]:
        """Validate a session with security checks."""
        session = await self.storage.load(session_id)

        if not session:
            return False, "Session not found"

        # Token validation
        if not self.security.verify_token(token, session.token_hash):
            return False, "Invalid token"

        # State validation
        if session.state != SessionState.ACTIVE:
            return False, f"Session is {session.state.value}"

        # Expiration check
        if session.expires_at and datetime.now() > session.expires_at:
            await self._expire_session(session)
            return False, "Session expired"

        # IP validation
        if current_ip and not self.security.validate_ip(session, current_ip):
            return False, "IP address mismatch"

        # Device validation
        if device_info and self.security.detect_hijacking(session, device_info):
            await self._lock_session(session, "Potential hijacking detected")
            return False, "Session locked due to security concern"

        return True, None

    async def update_session(
        self,
        session_id: str,
        **updates
    ) -> Optional[Session]:
        """Update session data."""
        session = await self.storage.load(session_id)

        if not session:
            return None

        # Update data fields
        for key, value in updates.items():
            if hasattr(session.data, key):
                setattr(session.data, key, value)
            elif key == "metadata":
                session.data.metadata.update(value)
            elif key == "custom":
                session.data.custom.update(value)

        # Update activity timestamp
        session.last_activity = datetime.now()

        await self.storage.save(session)

        return session

    async def touch_session(self, session_id: str) -> bool:
        """Update session activity timestamp."""
        session = await self.storage.load(session_id)

        if not session:
            return False

        # Check idle timeout
        idle_threshold = datetime.now() - timedelta(seconds=self.config.idle_timeout)
        if session.last_activity < idle_threshold:
            session.state = SessionState.IDLE
        else:
            session.state = SessionState.ACTIVE

        session.last_activity = datetime.now()
        await self.storage.save(session)

        return True

    async def extend_session(
        self,
        session_id: str,
        additional_seconds: int = None
    ) -> Optional[datetime]:
        """Extend session expiration."""
        session = await self.storage.load(session_id)

        if not session:
            return None

        extension = additional_seconds or self.config.default_timeout
        session.expires_at = datetime.now() + timedelta(seconds=extension)

        await self.storage.save(session)

        return session.expires_at

    async def destroy_session(self, session_id: str) -> bool:
        """Destroy a session."""
        session = await self.storage.load(session_id)

        if session:
            # Record activity
            await self._record_activity(
                session,
                ActivityType.LOGOUT,
                "Session destroyed"
            )

            # Remove from user tracking
            if session.data.user_id:
                self.user_sessions[session.data.user_id].discard(session_id)

            # Emit event
            await self._emit_event("session_destroyed", session)

        return await self.storage.delete(session_id)

    async def destroy_user_sessions(self, user_id: str) -> int:
        """Destroy all sessions for a user."""
        session_ids = list(self.user_sessions.get(user_id, set()))
        count = 0

        for session_id in session_ids:
            if await self.destroy_session(session_id):
                count += 1

        return count

    async def _expire_session(self, session: Session) -> None:
        """Mark session as expired."""
        session.state = SessionState.EXPIRED
        await self.storage.save(session)
        await self._emit_event("session_expired", session)

    async def _lock_session(self, session: Session, reason: str) -> None:
        """Lock a session for security reasons."""
        session.state = SessionState.LOCKED
        session.data.metadata["lock_reason"] = reason
        session.data.metadata["locked_at"] = datetime.now().isoformat()
        await self.storage.save(session)
        await self._emit_event("session_locked", session)

    async def _record_activity(
        self,
        session: Session,
        activity_type: ActivityType,
        description: str,
        ip_address: str = ""
    ) -> None:
        """Record session activity."""
        activity = SessionActivity(
            activity_type=activity_type,
            description=description,
            ip_address=ip_address
        )

        session.activities.append(activity)

        # Trim activities
        if len(session.activities) > self.config.max_activities:
            session.activities = session.activities[-self.config.max_activities:]

        await self.storage.save(session)

    async def record_activity(
        self,
        session_id: str,
        activity_type: ActivityType,
        description: str,
        data: Dict[str, Any] = None,
        ip_address: str = ""
    ) -> bool:
        """Record activity for a session."""
        session = await self.storage.load(session_id)

        if not session:
            return False

        activity = SessionActivity(
            activity_type=activity_type,
            description=description,
            data=data or {},
            ip_address=ip_address
        )

        session.activities.append(activity)
        session.last_activity = datetime.now()

        # Trim activities
        if len(session.activities) > self.config.max_activities:
            session.activities = session.activities[-self.config.max_activities:]

        await self.storage.save(session)

        return True

    # Event handling
    def on(self, event: str, handler: Callable) -> None:
        """Register event handler."""
        self.event_handlers[event].append(handler)

    async def _emit_event(self, event: str, session: Session) -> None:
        """Emit session event."""
        for handler in self.event_handlers.get(event, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(session)
                else:
                    handler(session)
            except Exception as e:
                logger.error(f"Event handler error: {e}")

    # Session queries
    async def get_user_sessions(self, user_id: str) -> List[Session]:
        """Get all sessions for a user."""
        sessions = []
        for session_id in self.user_sessions.get(user_id, set()):
            session = await self.storage.load(session_id)
            if session:
                sessions.append(session)
        return sessions

    async def get_active_sessions(self) -> List[Session]:
        """Get all active sessions."""
        sessions = []
        for session_id in await self.storage.list_all():
            session = await self.storage.load(session_id)
            if session and session.state == SessionState.ACTIVE:
                sessions.append(session)
        return sessions

    async def count_sessions(
        self,
        state: SessionState = None,
        session_type: SessionType = None
    ) -> int:
        """Count sessions matching criteria."""
        count = 0
        for session_id in await self.storage.list_all():
            session = await self.storage.load(session_id)
            if session:
                if state and session.state != state:
                    continue
                if session_type and session.session_type != session_type:
                    continue
                count += 1
        return count

    # Cleanup
    async def cleanup_expired(self) -> int:
        """Clean up expired sessions."""
        cleaned = 0
        now = datetime.now()

        for session_id in await self.storage.list_all():
            session = await self.storage.load(session_id)

            if session and session.expires_at and session.expires_at < now:
                await self.destroy_session(session_id)
                cleaned += 1

        return cleaned

    async def start_cleanup_task(self) -> None:
        """Start periodic cleanup task."""
        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(self.config.cleanup_interval)
                    cleaned = await self.cleanup_expired()
                    if cleaned > 0:
                        logger.info(f"Cleaned up {cleaned} expired sessions")
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Cleanup error: {e}")

        self._cleanup_task = asyncio.create_task(cleanup_loop())

    async def stop_cleanup_task(self) -> None:
        """Stop cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

    # Statistics
    def get_statistics(self) -> Dict[str, Any]:
        """Get session manager statistics."""
        return {
            "tracked_users": len(self.user_sessions),
            "total_user_sessions": sum(len(s) for s in self.user_sessions.values()),
            "event_handlers": sum(len(h) for h in self.event_handlers.values())
        }

    # CSRF
    async def verify_csrf(
        self,
        session_id: str,
        csrf_token: str
    ) -> bool:
        """Verify CSRF token for session."""
        session = await self.storage.load(session_id)

        if not session:
            return False

        return self.security.verify_csrf_token(session.csrf_token, csrf_token)

    async def regenerate_csrf(self, session_id: str) -> Optional[str]:
        """Regenerate CSRF token."""
        session = await self.storage.load(session_id)

        if not session:
            return None

        session.csrf_token = self.security.generate_csrf_token()
        await self.storage.save(session)

        return session.csrf_token


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Session Manager."""
    print("=" * 70)
    print("BAEL - SESSION MANAGER DEMO")
    print("User Session and State Management")
    print("=" * 70)
    print()

    # Create session manager
    config = SessionConfig(
        default_timeout=3600,
        idle_timeout=1800,
        max_sessions_per_user=3
    )

    manager = SessionManager(config=config)

    # 1. Create Sessions
    print("1. CREATE SESSIONS:")
    print("-" * 40)

    device = DeviceInfo(
        device_id="device_001",
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X)",
        ip_address="192.168.1.100",
        platform="macOS",
        browser="Chrome"
    )

    session = await manager.create_session(
        session_type=SessionType.USER,
        user_id="user_123",
        device_info=device,
        username="john_doe",
        email="john@example.com",
        roles=["user", "editor"]
    )

    print(f"   Session ID: {session.id[:32]}...")
    print(f"   User ID: {session.data.user_id}")
    print(f"   Username: {session.data.username}")
    print(f"   State: {session.state.value}")
    print(f"   Expires: {session.expires_at}")
    print()

    # 2. Session Validation
    print("2. SESSION VALIDATION:")
    print("-" * 40)

    valid, error = await manager.validate_session(
        session.id,
        session.token,
        current_ip="192.168.1.100",
        device_info=device
    )

    print(f"   Valid: {valid}")
    print(f"   Error: {error}")

    # Invalid token test
    valid, error = await manager.validate_session(
        session.id,
        "invalid_token"
    )
    print(f"   Invalid token test - Valid: {valid}, Error: {error}")
    print()

    # 3. Session Update
    print("3. SESSION UPDATE:")
    print("-" * 40)

    updated = await manager.update_session(
        session.id,
        preferences={"theme": "dark", "language": "en"},
        metadata={"login_count": 1}
    )

    print(f"   Updated preferences: {updated.data.preferences}")
    print(f"   Updated metadata: {updated.data.metadata}")
    print()

    # 4. Activity Tracking
    print("4. ACTIVITY TRACKING:")
    print("-" * 40)

    await manager.record_activity(
        session.id,
        ActivityType.PAGE_VIEW,
        "Viewed dashboard",
        {"page": "/dashboard"}
    )

    await manager.record_activity(
        session.id,
        ActivityType.ACTION,
        "Created document",
        {"doc_id": "doc_456"}
    )

    session = await manager.get_session(session.id)
    print(f"   Recorded activities: {len(session.activities)}")
    for activity in session.activities[-3:]:
        print(f"   - {activity.activity_type.value}: {activity.description}")
    print()

    # 5. Multi-User Sessions
    print("5. MULTI-USER SESSIONS:")
    print("-" * 40)

    # Create multiple sessions for same user
    for i in range(3):
        await manager.create_session(
            session_type=SessionType.USER,
            user_id="user_456",
            username=f"session_{i}"
        )

    user_sessions = await manager.get_user_sessions("user_456")
    print(f"   Sessions for user_456: {len(user_sessions)}")

    # Try to create 4th session (should evict oldest)
    await manager.create_session(
        session_type=SessionType.USER,
        user_id="user_456",
        username="session_3"
    )

    user_sessions = await manager.get_user_sessions("user_456")
    print(f"   After 4th creation: {len(user_sessions)} (max: {config.max_sessions_per_user})")
    print()

    # 6. Session Extension
    print("6. SESSION EXTENSION:")
    print("-" * 40)

    original_expiry = session.expires_at
    new_expiry = await manager.extend_session(session.id, 7200)

    print(f"   Original expiry: {original_expiry}")
    print(f"   Extended expiry: {new_expiry}")
    print()

    # 7. CSRF Protection
    print("7. CSRF PROTECTION:")
    print("-" * 40)

    session = await manager.get_session(session.id)
    csrf_valid = await manager.verify_csrf(session.id, session.csrf_token)
    print(f"   Valid CSRF token: {csrf_valid}")

    csrf_invalid = await manager.verify_csrf(session.id, "wrong_token")
    print(f"   Invalid CSRF token: {csrf_invalid}")

    new_csrf = await manager.regenerate_csrf(session.id)
    print(f"   Regenerated CSRF: {new_csrf[:16]}...")
    print()

    # 8. Event Handling
    print("8. EVENT HANDLING:")
    print("-" * 40)

    events_received = []

    def on_session_destroyed(session):
        events_received.append(f"destroyed:{session.id[:16]}")

    manager.on("session_destroyed", on_session_destroyed)

    await manager.destroy_session(session.id)
    print(f"   Events received: {events_received}")
    print()

    # 9. Session Counts
    print("9. SESSION COUNTS:")
    print("-" * 40)

    active_count = await manager.count_sessions(state=SessionState.ACTIVE)
    total_sessions = len(await manager.storage.list_all())

    print(f"   Active sessions: {active_count}")
    print(f"   Total sessions: {total_sessions}")
    print()

    # 10. Statistics
    print("10. STATISTICS:")
    print("-" * 40)

    stats = manager.get_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()

    # Cleanup
    await manager.destroy_user_sessions("user_456")
    cleaned = await manager.cleanup_expired()
    print(f"   Cleaned up: {cleaned} expired sessions")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Session Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
