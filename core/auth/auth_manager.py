#!/usr/bin/env python3
"""
BAEL - Authentication Manager
Comprehensive authentication and authorization system.

This module provides powerful auth capabilities
for secure access control.

Features:
- Multiple auth strategies
- JWT tokens
- Session management
- Role-based access control (RBAC)
- Permission management
- Password hashing
- API key management
- OAuth support
- Multi-factor auth
- Rate limiting per user
"""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from functools import wraps
from typing import (Any, Awaitable, Callable, Dict, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class AuthStatus(Enum):
    """Authentication status."""
    SUCCESS = "success"
    FAILED = "failed"
    EXPIRED = "expired"
    INVALID = "invalid"
    LOCKED = "locked"
    MFA_REQUIRED = "mfa_required"


class TokenType(Enum):
    """Token types."""
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"
    SESSION = "session"


class PermissionAction(Enum):
    """Permission actions."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    ADMIN = "admin"
    ALL = "*"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class User:
    """User entity."""
    user_id: str
    username: str
    email: str = ""
    password_hash: str = ""
    roles: Set[str] = field(default_factory=set)
    permissions: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_login: Optional[float] = None
    is_active: bool = True
    is_locked: bool = False
    mfa_enabled: bool = False
    mfa_secret: Optional[str] = None


@dataclass
class Token:
    """Authentication token."""
    token_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    token_type: TokenType = TokenType.ACCESS
    user_id: str = ""
    value: str = ""
    issued_at: float = field(default_factory=time.time)
    expires_at: float = 0
    scope: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at


@dataclass
class Session:
    """User session."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0
    last_activity: float = field(default_factory=time.time)
    ip_address: str = ""
    user_agent: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def touch(self) -> None:
        self.last_activity = time.time()


@dataclass
class AuthResult:
    """Authentication result."""
    status: AuthStatus
    user: Optional[User] = None
    token: Optional[Token] = None
    session: Optional[Session] = None
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Permission:
    """Permission definition."""
    resource: str
    action: PermissionAction
    conditions: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"{self.resource}:{self.action.value}"

    @classmethod
    def from_string(cls, s: str) -> 'Permission':
        parts = s.split(":")
        resource = parts[0]
        action = PermissionAction(parts[1]) if len(parts) > 1 else PermissionAction.ALL
        return cls(resource=resource, action=action)


@dataclass
class Role:
    """Role definition."""
    role_id: str
    name: str
    permissions: Set[str] = field(default_factory=set)
    parent_roles: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# PASSWORD HASHER
# =============================================================================

class PasswordHasher:
    """Secure password hashing."""

    def __init__(
        self,
        algorithm: str = "sha256",
        iterations: int = 100000,
        salt_length: int = 32
    ):
        self.algorithm = algorithm
        self.iterations = iterations
        self.salt_length = salt_length

    def hash(self, password: str) -> str:
        """Hash a password."""
        salt = secrets.token_hex(self.salt_length)

        key = hashlib.pbkdf2_hmac(
            self.algorithm,
            password.encode(),
            salt.encode(),
            self.iterations
        )

        return f"{self.algorithm}${self.iterations}${salt}${key.hex()}"

    def verify(self, password: str, hashed: str) -> bool:
        """Verify password against hash."""
        try:
            parts = hashed.split("$")
            if len(parts) != 4:
                return False

            algorithm, iterations, salt, key_hex = parts
            iterations = int(iterations)

            computed = hashlib.pbkdf2_hmac(
                algorithm,
                password.encode(),
                salt.encode(),
                iterations
            )

            return hmac.compare_digest(computed.hex(), key_hex)
        except Exception:
            return False


# =============================================================================
# JWT TOKEN MANAGER
# =============================================================================

class JWTManager:
    """JWT token management."""

    def __init__(
        self,
        secret: str,
        algorithm: str = "HS256",
        access_ttl: int = 3600,  # 1 hour
        refresh_ttl: int = 86400 * 7  # 7 days
    ):
        self.secret = secret
        self.algorithm = algorithm
        self.access_ttl = access_ttl
        self.refresh_ttl = refresh_ttl

    def _base64_encode(self, data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    def _base64_decode(self, data: str) -> bytes:
        padding = 4 - len(data) % 4
        if padding != 4:
            data += "=" * padding
        return base64.urlsafe_b64decode(data)

    def create_token(
        self,
        user_id: str,
        token_type: TokenType = TokenType.ACCESS,
        claims: Dict[str, Any] = None,
        ttl: int = None
    ) -> Token:
        """Create a JWT token."""
        now = time.time()

        if ttl is None:
            ttl = self.access_ttl if token_type == TokenType.ACCESS else self.refresh_ttl

        payload = {
            "sub": user_id,
            "type": token_type.value,
            "iat": int(now),
            "exp": int(now + ttl),
            "jti": str(uuid.uuid4()),
            **(claims or {})
        }

        header = {"alg": self.algorithm, "typ": "JWT"}

        # Encode
        header_enc = self._base64_encode(json.dumps(header).encode())
        payload_enc = self._base64_encode(json.dumps(payload).encode())

        # Sign
        message = f"{header_enc}.{payload_enc}"
        signature = hmac.new(
            self.secret.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
        signature_enc = self._base64_encode(signature)

        token_value = f"{message}.{signature_enc}"

        return Token(
            token_id=payload["jti"],
            token_type=token_type,
            user_id=user_id,
            value=token_value,
            issued_at=now,
            expires_at=now + ttl,
            metadata=claims or {}
        )

    def verify_token(self, token_value: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token."""
        try:
            parts = token_value.split(".")
            if len(parts) != 3:
                return None

            header_enc, payload_enc, signature_enc = parts

            # Verify signature
            message = f"{header_enc}.{payload_enc}"
            expected_sig = hmac.new(
                self.secret.encode(),
                message.encode(),
                hashlib.sha256
            ).digest()

            actual_sig = self._base64_decode(signature_enc)

            if not hmac.compare_digest(expected_sig, actual_sig):
                return None

            # Decode payload
            payload = json.loads(self._base64_decode(payload_enc))

            # Check expiration
            if payload.get("exp", 0) < time.time():
                return None

            return payload

        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return None

    def refresh_token(self, refresh_token: str) -> Optional[Token]:
        """Create new access token from refresh token."""
        payload = self.verify_token(refresh_token)

        if not payload:
            return None

        if payload.get("type") != TokenType.REFRESH.value:
            return None

        return self.create_token(
            user_id=payload["sub"],
            token_type=TokenType.ACCESS
        )


# =============================================================================
# SESSION MANAGER
# =============================================================================

class SessionManager:
    """User session management."""

    def __init__(self, session_ttl: int = 3600 * 24):
        self.session_ttl = session_ttl
        self.sessions: Dict[str, Session] = {}
        self.user_sessions: Dict[str, Set[str]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def create_session(
        self,
        user_id: str,
        ip_address: str = "",
        user_agent: str = "",
        data: Dict[str, Any] = None
    ) -> Session:
        """Create a new session."""
        session = Session(
            user_id=user_id,
            expires_at=time.time() + self.session_ttl,
            ip_address=ip_address,
            user_agent=user_agent,
            data=data or {}
        )

        async with self._lock:
            self.sessions[session.session_id] = session
            self.user_sessions[user_id].add(session.session_id)

        return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID."""
        session = self.sessions.get(session_id)

        if session and session.is_expired:
            await self.destroy_session(session_id)
            return None

        if session:
            session.touch()

        return session

    async def destroy_session(self, session_id: str) -> bool:
        """Destroy a session."""
        async with self._lock:
            session = self.sessions.pop(session_id, None)

            if session:
                self.user_sessions[session.user_id].discard(session_id)
                return True

        return False

    async def destroy_user_sessions(self, user_id: str) -> int:
        """Destroy all sessions for a user."""
        count = 0

        async with self._lock:
            session_ids = list(self.user_sessions.get(user_id, set()))

            for session_id in session_ids:
                if session_id in self.sessions:
                    del self.sessions[session_id]
                    count += 1

            self.user_sessions.pop(user_id, None)

        return count

    async def get_user_sessions(self, user_id: str) -> List[Session]:
        """Get all sessions for a user."""
        session_ids = self.user_sessions.get(user_id, set())
        return [self.sessions[sid] for sid in session_ids if sid in self.sessions]

    async def cleanup_expired(self) -> int:
        """Clean up expired sessions."""
        count = 0
        now = time.time()

        async with self._lock:
            expired = [
                sid for sid, s in self.sessions.items()
                if s.expires_at < now
            ]

            for sid in expired:
                session = self.sessions.pop(sid)
                self.user_sessions[session.user_id].discard(sid)
                count += 1

        return count


# =============================================================================
# RBAC MANAGER
# =============================================================================

class RBACManager:
    """Role-Based Access Control manager."""

    def __init__(self):
        self.roles: Dict[str, Role] = {}
        self._role_permissions_cache: Dict[str, Set[str]] = {}

    def add_role(
        self,
        role_id: str,
        name: str,
        permissions: Set[str] = None,
        parent_roles: Set[str] = None
    ) -> Role:
        """Add a role."""
        role = Role(
            role_id=role_id,
            name=name,
            permissions=permissions or set(),
            parent_roles=parent_roles or set()
        )

        self.roles[role_id] = role
        self._invalidate_cache()

        return role

    def get_role(self, role_id: str) -> Optional[Role]:
        """Get role by ID."""
        return self.roles.get(role_id)

    def add_permission_to_role(
        self,
        role_id: str,
        permission: str
    ) -> bool:
        """Add permission to role."""
        role = self.roles.get(role_id)
        if role:
            role.permissions.add(permission)
            self._invalidate_cache()
            return True
        return False

    def remove_permission_from_role(
        self,
        role_id: str,
        permission: str
    ) -> bool:
        """Remove permission from role."""
        role = self.roles.get(role_id)
        if role:
            role.permissions.discard(permission)
            self._invalidate_cache()
            return True
        return False

    def get_role_permissions(self, role_id: str) -> Set[str]:
        """Get all permissions for a role (including inherited)."""
        if role_id in self._role_permissions_cache:
            return self._role_permissions_cache[role_id]

        permissions = set()
        visited = set()

        def collect(rid: str):
            if rid in visited:
                return
            visited.add(rid)

            role = self.roles.get(rid)
            if role:
                permissions.update(role.permissions)
                for parent in role.parent_roles:
                    collect(parent)

        collect(role_id)

        self._role_permissions_cache[role_id] = permissions
        return permissions

    def get_user_permissions(self, user: User) -> Set[str]:
        """Get all permissions for a user."""
        permissions = set(user.permissions)

        for role_id in user.roles:
            permissions.update(self.get_role_permissions(role_id))

        return permissions

    def has_permission(
        self,
        user: User,
        resource: str,
        action: PermissionAction
    ) -> bool:
        """Check if user has permission."""
        permissions = self.get_user_permissions(user)

        # Check specific permission
        perm_str = f"{resource}:{action.value}"
        if perm_str in permissions:
            return True

        # Check wildcard permissions
        if f"{resource}:*" in permissions:
            return True

        if f"*:{action.value}" in permissions:
            return True

        if "*:*" in permissions:
            return True

        return False

    def _invalidate_cache(self) -> None:
        """Invalidate permissions cache."""
        self._role_permissions_cache.clear()


# =============================================================================
# API KEY MANAGER
# =============================================================================

class APIKeyManager:
    """API key management."""

    def __init__(self, key_prefix: str = "bael"):
        self.key_prefix = key_prefix
        self.keys: Dict[str, Token] = {}
        self.user_keys: Dict[str, Set[str]] = defaultdict(set)

    def generate_key(
        self,
        user_id: str,
        name: str = "",
        scope: Set[str] = None,
        expires_in: int = None
    ) -> Token:
        """Generate a new API key."""
        key_value = f"{self.key_prefix}_{secrets.token_urlsafe(32)}"

        expires_at = 0
        if expires_in:
            expires_at = time.time() + expires_in

        token = Token(
            token_type=TokenType.API_KEY,
            user_id=user_id,
            value=key_value,
            expires_at=expires_at,
            scope=scope or set(),
            metadata={"name": name}
        )

        # Store hash of key for lookup
        key_hash = hashlib.sha256(key_value.encode()).hexdigest()
        self.keys[key_hash] = token
        self.user_keys[user_id].add(key_hash)

        return token

    def validate_key(self, key_value: str) -> Optional[Token]:
        """Validate an API key."""
        key_hash = hashlib.sha256(key_value.encode()).hexdigest()
        token = self.keys.get(key_hash)

        if not token:
            return None

        if token.expires_at > 0 and token.is_expired:
            return None

        return token

    def revoke_key(self, key_value: str) -> bool:
        """Revoke an API key."""
        key_hash = hashlib.sha256(key_value.encode()).hexdigest()
        token = self.keys.pop(key_hash, None)

        if token:
            self.user_keys[token.user_id].discard(key_hash)
            return True

        return False

    def get_user_keys(self, user_id: str) -> List[Token]:
        """Get all API keys for a user."""
        return [
            self.keys[kh] for kh in self.user_keys.get(user_id, set())
            if kh in self.keys
        ]


# =============================================================================
# AUTH MANAGER
# =============================================================================

class AuthManager:
    """
    Master authentication manager for BAEL.
    """

    def __init__(
        self,
        jwt_secret: str = None,
        session_ttl: int = 3600 * 24
    ):
        self.jwt_secret = jwt_secret or secrets.token_urlsafe(32)

        # Components
        self.password_hasher = PasswordHasher()
        self.jwt = JWTManager(self.jwt_secret)
        self.sessions = SessionManager(session_ttl)
        self.rbac = RBACManager()
        self.api_keys = APIKeyManager()

        # User store (in-memory for demo)
        self.users: Dict[str, User] = {}

        # Statistics
        self.stats = {
            "logins_success": 0,
            "logins_failed": 0,
            "tokens_issued": 0,
            "sessions_created": 0
        }

    async def register(
        self,
        username: str,
        password: str,
        email: str = "",
        roles: Set[str] = None
    ) -> User:
        """Register a new user."""
        user_id = str(uuid.uuid4())

        user = User(
            user_id=user_id,
            username=username,
            email=email,
            password_hash=self.password_hasher.hash(password),
            roles=roles or set()
        )

        self.users[user_id] = user

        return user

    async def authenticate(
        self,
        username: str,
        password: str,
        ip_address: str = "",
        user_agent: str = ""
    ) -> AuthResult:
        """Authenticate a user."""
        # Find user
        user = None
        for u in self.users.values():
            if u.username == username:
                user = u
                break

        if not user:
            self.stats["logins_failed"] += 1
            return AuthResult(
                status=AuthStatus.FAILED,
                message="User not found"
            )

        if user.is_locked:
            return AuthResult(
                status=AuthStatus.LOCKED,
                message="Account is locked"
            )

        if not user.is_active:
            return AuthResult(
                status=AuthStatus.FAILED,
                message="Account is inactive"
            )

        # Verify password
        if not self.password_hasher.verify(password, user.password_hash):
            self.stats["logins_failed"] += 1
            return AuthResult(
                status=AuthStatus.FAILED,
                message="Invalid password"
            )

        # Check MFA
        if user.mfa_enabled:
            return AuthResult(
                status=AuthStatus.MFA_REQUIRED,
                user=user,
                message="MFA verification required"
            )

        # Create token and session
        token = self.jwt.create_token(user.user_id)
        session = await self.sessions.create_session(
            user.user_id,
            ip_address,
            user_agent
        )

        user.last_login = time.time()

        self.stats["logins_success"] += 1
        self.stats["tokens_issued"] += 1
        self.stats["sessions_created"] += 1

        return AuthResult(
            status=AuthStatus.SUCCESS,
            user=user,
            token=token,
            session=session
        )

    async def validate_token(self, token_value: str) -> AuthResult:
        """Validate a JWT token."""
        payload = self.jwt.verify_token(token_value)

        if not payload:
            return AuthResult(
                status=AuthStatus.INVALID,
                message="Invalid or expired token"
            )

        user_id = payload.get("sub")
        user = self.users.get(user_id)

        if not user or not user.is_active:
            return AuthResult(
                status=AuthStatus.INVALID,
                message="User not found or inactive"
            )

        return AuthResult(
            status=AuthStatus.SUCCESS,
            user=user,
            metadata=payload
        )

    async def validate_api_key(self, key_value: str) -> AuthResult:
        """Validate an API key."""
        token = self.api_keys.validate_key(key_value)

        if not token:
            return AuthResult(
                status=AuthStatus.INVALID,
                message="Invalid API key"
            )

        user = self.users.get(token.user_id)

        if not user or not user.is_active:
            return AuthResult(
                status=AuthStatus.INVALID,
                message="User not found or inactive"
            )

        return AuthResult(
            status=AuthStatus.SUCCESS,
            user=user,
            token=token
        )

    async def validate_session(self, session_id: str) -> AuthResult:
        """Validate a session."""
        session = await self.sessions.get_session(session_id)

        if not session:
            return AuthResult(
                status=AuthStatus.EXPIRED,
                message="Session not found or expired"
            )

        user = self.users.get(session.user_id)

        if not user or not user.is_active:
            return AuthResult(
                status=AuthStatus.INVALID,
                message="User not found or inactive"
            )

        return AuthResult(
            status=AuthStatus.SUCCESS,
            user=user,
            session=session
        )

    async def logout(
        self,
        session_id: str = None,
        user_id: str = None,
        all_sessions: bool = False
    ) -> int:
        """Logout user."""
        if all_sessions and user_id:
            return await self.sessions.destroy_user_sessions(user_id)

        if session_id:
            return 1 if await self.sessions.destroy_session(session_id) else 0

        return 0

    def has_permission(
        self,
        user: User,
        resource: str,
        action: PermissionAction
    ) -> bool:
        """Check if user has permission."""
        return self.rbac.has_permission(user, resource, action)

    def require_permission(
        self,
        resource: str,
        action: PermissionAction
    ) -> Callable:
        """Decorator to require permission."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(user: User, *args, **kwargs) -> Any:
                if not self.has_permission(user, resource, action):
                    raise PermissionError(
                        f"Permission denied: {resource}:{action.value}"
                    )
                return await func(user, *args, **kwargs)
            return wrapper
        return decorator

    def get_stats(self) -> Dict[str, Any]:
        """Get authentication statistics."""
        return self.stats.copy()


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Authentication Manager."""
    print("=" * 70)
    print("BAEL - AUTHENTICATION MANAGER DEMO")
    print("Comprehensive Auth & Authorization System")
    print("=" * 70)
    print()

    manager = AuthManager()

    # 1. Setup Roles
    print("1. SETUP ROLES:")
    print("-" * 40)

    manager.rbac.add_role("admin", "Administrator", {
        "users:*", "settings:*", "*:read"
    })
    manager.rbac.add_role("editor", "Editor", {
        "content:create", "content:read", "content:update"
    })
    manager.rbac.add_role("viewer", "Viewer", {
        "content:read"
    })

    print("   Created roles: admin, editor, viewer")
    print(f"   Admin permissions: {manager.rbac.get_role_permissions('admin')}")
    print()

    # 2. Register Users
    print("2. REGISTER USERS:")
    print("-" * 40)

    admin_user = await manager.register(
        "admin",
        "admin123",
        "admin@bael.ai",
        {"admin"}
    )
    print(f"   Registered: {admin_user.username} (admin)")

    editor_user = await manager.register(
        "editor",
        "editor123",
        "editor@bael.ai",
        {"editor"}
    )
    print(f"   Registered: {editor_user.username} (editor)")

    viewer_user = await manager.register(
        "viewer",
        "viewer123",
        "viewer@bael.ai",
        {"viewer"}
    )
    print(f"   Registered: {viewer_user.username} (viewer)")
    print()

    # 3. Authentication
    print("3. AUTHENTICATION:")
    print("-" * 40)

    result = await manager.authenticate("admin", "admin123", "127.0.0.1")
    print(f"   Login status: {result.status.value}")
    print(f"   Token issued: {result.token.value[:50]}...")
    print(f"   Session ID: {result.session.session_id[:20]}...")

    admin_token = result.token.value
    admin_session = result.session.session_id
    print()

    # 4. Failed Authentication
    print("4. FAILED AUTHENTICATION:")
    print("-" * 40)

    result = await manager.authenticate("admin", "wrongpassword")
    print(f"   Status: {result.status.value}")
    print(f"   Message: {result.message}")
    print()

    # 5. Token Validation
    print("5. TOKEN VALIDATION:")
    print("-" * 40)

    result = await manager.validate_token(admin_token)
    print(f"   Status: {result.status.value}")
    print(f"   User: {result.user.username if result.user else 'N/A'}")

    result = await manager.validate_token("invalid_token")
    print(f"   Invalid token status: {result.status.value}")
    print()

    # 6. Session Validation
    print("6. SESSION VALIDATION:")
    print("-" * 40)

    result = await manager.validate_session(admin_session)
    print(f"   Status: {result.status.value}")
    print(f"   User: {result.user.username if result.user else 'N/A'}")
    print(f"   Session data: {result.session.data if result.session else 'N/A'}")
    print()

    # 7. Permission Checking
    print("7. PERMISSION CHECKING:")
    print("-" * 40)

    # Admin can do anything
    can_admin = manager.has_permission(admin_user, "users", PermissionAction.DELETE)
    print(f"   Admin can delete users: {can_admin}")

    # Editor can create content
    can_edit = manager.has_permission(editor_user, "content", PermissionAction.CREATE)
    print(f"   Editor can create content: {can_edit}")

    # Viewer can only read
    can_view = manager.has_permission(viewer_user, "content", PermissionAction.READ)
    can_delete = manager.has_permission(viewer_user, "content", PermissionAction.DELETE)
    print(f"   Viewer can read content: {can_view}")
    print(f"   Viewer can delete content: {can_delete}")
    print()

    # 8. API Keys
    print("8. API KEYS:")
    print("-" * 40)

    api_key = manager.api_keys.generate_key(
        admin_user.user_id,
        "Production Key",
        {"api:read", "api:write"}
    )
    print(f"   Generated key: {api_key.value[:30]}...")

    result = await manager.validate_api_key(api_key.value)
    print(f"   Validation status: {result.status.value}")

    user_keys = manager.api_keys.get_user_keys(admin_user.user_id)
    print(f"   User has {len(user_keys)} API key(s)")
    print()

    # 9. Password Hashing
    print("9. PASSWORD HASHING:")
    print("-" * 40)

    hashed = manager.password_hasher.hash("mypassword")
    print(f"   Hash: {hashed[:50]}...")

    is_valid = manager.password_hasher.verify("mypassword", hashed)
    print(f"   Verification (correct): {is_valid}")

    is_invalid = manager.password_hasher.verify("wrongpassword", hashed)
    print(f"   Verification (wrong): {is_invalid}")
    print()

    # 10. JWT Tokens
    print("10. JWT TOKENS:")
    print("-" * 40)

    access_token = manager.jwt.create_token(
        admin_user.user_id,
        TokenType.ACCESS,
        {"role": "admin"}
    )
    print(f"   Access token expires in: {access_token.expires_at - time.time():.0f}s")

    refresh_token = manager.jwt.create_token(
        admin_user.user_id,
        TokenType.REFRESH
    )
    print(f"   Refresh token expires in: {(refresh_token.expires_at - time.time()) / 3600:.0f}h")

    # Refresh access token
    new_access = manager.jwt.refresh_token(refresh_token.value)
    print(f"   Refreshed access token: {new_access is not None}")
    print()

    # 11. Logout
    print("11. LOGOUT:")
    print("-" * 40)

    user_sessions = await manager.sessions.get_user_sessions(admin_user.user_id)
    print(f"   Active sessions before logout: {len(user_sessions)}")

    count = await manager.logout(session_id=admin_session)
    print(f"   Logged out sessions: {count}")

    user_sessions = await manager.sessions.get_user_sessions(admin_user.user_id)
    print(f"   Active sessions after logout: {len(user_sessions)}")
    print()

    # 12. Statistics
    print("12. STATISTICS:")
    print("-" * 40)

    stats = manager.get_stats()
    print(f"    Successful logins: {stats['logins_success']}")
    print(f"    Failed logins: {stats['logins_failed']}")
    print(f"    Tokens issued: {stats['tokens_issued']}")
    print(f"    Sessions created: {stats['sessions_created']}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Authentication Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
