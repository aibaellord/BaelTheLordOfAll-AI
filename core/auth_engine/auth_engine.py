"""
BAEL Auth Engine
================

Comprehensive authentication and authorization with:
- JWT token management
- OAuth2 providers
- Role-based access control (RBAC)
- Multi-factor authentication
- Session management
- Password hashing

"Ba'el controls access to all realms." — Ba'el
"""

import asyncio
import logging
import re
import json
import base64
import hmac
import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import defaultdict
import threading
import uuid

logger = logging.getLogger("BAEL.Auth")


# ============================================================================
# ENUMS
# ============================================================================

class AuthMethod(Enum):
    """Authentication methods."""
    PASSWORD = "password"
    API_KEY = "api_key"
    JWT = "jwt"
    OAUTH = "oauth"
    SAML = "saml"
    LDAP = "ldap"


class TokenType(Enum):
    """Token types."""
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"
    RESET = "reset"
    VERIFY = "verify"


class PermissionAction(Enum):
    """Permission actions."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    ADMIN = "admin"


class UserStatus(Enum):
    """User statuses."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    LOCKED = "locked"
    SUSPENDED = "suspended"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Permission:
    """A permission."""
    id: str
    resource: str
    action: PermissionAction
    conditions: Dict[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> str:
        return f"{self.resource}:{self.action.value}"


@dataclass
class Role:
    """A role with permissions."""
    id: str
    name: str
    description: str = ""

    permissions: Set[str] = field(default_factory=set)  # Permission keys

    # Hierarchy
    parent_roles: List[str] = field(default_factory=list)  # Role IDs

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class User:
    """A user."""
    id: str
    username: str
    email: str

    # Password (hashed)
    password_hash: str = ""

    # Status
    status: UserStatus = UserStatus.ACTIVE

    # Roles
    roles: Set[str] = field(default_factory=set)  # Role IDs

    # Profile
    first_name: str = ""
    last_name: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    # MFA
    mfa_enabled: bool = False
    mfa_secret: Optional[str] = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    password_changed_at: Optional[datetime] = None

    # Security
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'status': self.status.value,
            'roles': list(self.roles),
            'mfa_enabled': self.mfa_enabled,
            'created_at': self.created_at.isoformat()
        }


@dataclass
class Token:
    """A token."""
    id: str
    token_type: TokenType
    value: str

    # User
    user_id: str

    # Validity
    issued_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None

    # State
    revoked: bool = False
    revoked_at: Optional[datetime] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    @property
    def is_valid(self) -> bool:
        return not self.revoked and not self.is_expired


@dataclass
class Session:
    """A user session."""
    id: str
    user_id: str

    # Token
    access_token: str
    refresh_token: Optional[str] = None

    # Context
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    # Validity
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    last_activity: datetime = field(default_factory=datetime.now)

    # State
    active: bool = True


@dataclass
class OAuthProvider:
    """OAuth provider configuration."""
    id: str
    name: str

    # Endpoints
    authorize_url: str = ""
    token_url: str = ""
    userinfo_url: str = ""

    # Credentials
    client_id: str = ""
    client_secret: str = ""

    # Scopes
    scopes: List[str] = field(default_factory=list)

    # Field mappings
    field_mappings: Dict[str, str] = field(default_factory=dict)


@dataclass
class AuthConfig:
    """Auth engine configuration."""
    # JWT
    jwt_secret: str = "change-this-secret-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Password
    min_password_length: int = 8
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digit: bool = True
    require_special: bool = False
    password_hash_algorithm: str = "sha256"
    password_hash_iterations: int = 100000

    # Login
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 30

    # Session
    session_timeout_minutes: int = 60

    # MFA
    mfa_issuer: str = "BAEL"


# ============================================================================
# PASSWORD MANAGER
# ============================================================================

class PasswordManager:
    """
    Handles password hashing and validation.
    """

    def __init__(self, config: AuthConfig):
        """Initialize password manager."""
        self.config = config

    def hash_password(self, password: str) -> str:
        """Hash a password."""
        salt = secrets.token_hex(16)
        key = hashlib.pbkdf2_hmac(
            self.config.password_hash_algorithm,
            password.encode('utf-8'),
            salt.encode('utf-8'),
            self.config.password_hash_iterations
        )
        return f"{salt}${key.hex()}"

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        try:
            salt, stored_key = password_hash.split('$')
            key = hashlib.pbkdf2_hmac(
                self.config.password_hash_algorithm,
                password.encode('utf-8'),
                salt.encode('utf-8'),
                self.config.password_hash_iterations
            )
            return key.hex() == stored_key
        except Exception:
            return False

    def validate_password(self, password: str) -> Tuple[bool, List[str]]:
        """Validate password against policy."""
        errors = []

        if len(password) < self.config.min_password_length:
            errors.append(f"Password must be at least {self.config.min_password_length} characters")

        if self.config.require_uppercase and not re.search(r'[A-Z]', password):
            errors.append("Password must contain an uppercase letter")

        if self.config.require_lowercase and not re.search(r'[a-z]', password):
            errors.append("Password must contain a lowercase letter")

        if self.config.require_digit and not re.search(r'\d', password):
            errors.append("Password must contain a digit")

        if self.config.require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain a special character")

        return len(errors) == 0, errors

    def generate_password(self, length: int = 16) -> str:
        """Generate a random password."""
        chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()'
        return ''.join(secrets.choice(chars) for _ in range(length))


# ============================================================================
# TOKEN MANAGER
# ============================================================================

class TokenManager:
    """
    Manages JWT and other tokens.
    """

    def __init__(self, config: AuthConfig):
        """Initialize token manager."""
        self.config = config
        self._tokens: Dict[str, Token] = {}
        self._lock = threading.RLock()

    def create_access_token(
        self,
        user_id: str,
        claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create an access token."""
        return self._create_jwt(
            user_id=user_id,
            token_type=TokenType.ACCESS,
            expires_delta=timedelta(minutes=self.config.access_token_expire_minutes),
            claims=claims
        )

    def create_refresh_token(self, user_id: str) -> str:
        """Create a refresh token."""
        return self._create_jwt(
            user_id=user_id,
            token_type=TokenType.REFRESH,
            expires_delta=timedelta(days=self.config.refresh_token_expire_days)
        )

    def create_api_key(self, user_id: str, name: str = "") -> str:
        """Create an API key."""
        api_key = f"bael_{secrets.token_urlsafe(32)}"

        token = Token(
            id=str(uuid.uuid4()),
            token_type=TokenType.API_KEY,
            value=api_key,
            user_id=user_id,
            metadata={'name': name}
        )

        with self._lock:
            self._tokens[api_key] = token

        return api_key

    def _create_jwt(
        self,
        user_id: str,
        token_type: TokenType,
        expires_delta: timedelta,
        claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a JWT token."""
        now = datetime.utcnow()
        expires = now + expires_delta

        payload = {
            'sub': user_id,
            'type': token_type.value,
            'iat': int(now.timestamp()),
            'exp': int(expires.timestamp()),
            'jti': str(uuid.uuid4())
        }

        if claims:
            payload.update(claims)

        # Create JWT
        header = {'alg': self.config.jwt_algorithm, 'typ': 'JWT'}

        header_b64 = base64.urlsafe_b64encode(
            json.dumps(header).encode()
        ).rstrip(b'=').decode()

        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).rstrip(b'=').decode()

        message = f"{header_b64}.{payload_b64}"
        signature = hmac.new(
            self.config.jwt_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()

        signature_b64 = base64.urlsafe_b64encode(signature).rstrip(b'=').decode()

        token_value = f"{message}.{signature_b64}"

        # Store token
        token = Token(
            id=payload['jti'],
            token_type=token_type,
            value=token_value,
            user_id=user_id,
            expires_at=expires
        )

        with self._lock:
            self._tokens[token_value] = token

        return token_value

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a token."""
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None

            header_b64, payload_b64, signature_b64 = parts

            # Verify signature
            message = f"{header_b64}.{payload_b64}"
            expected_signature = hmac.new(
                self.config.jwt_secret.encode(),
                message.encode(),
                hashlib.sha256
            ).digest()

            expected_b64 = base64.urlsafe_b64encode(expected_signature).rstrip(b'=').decode()

            if not hmac.compare_digest(signature_b64, expected_b64):
                return None

            # Decode payload
            padding = 4 - len(payload_b64) % 4
            payload_b64 += '=' * padding

            payload = json.loads(base64.urlsafe_b64decode(payload_b64))

            # Check expiration
            if payload.get('exp') and payload['exp'] < time.time():
                return None

            # Check if revoked
            with self._lock:
                stored_token = self._tokens.get(token)
                if stored_token and stored_token.revoked:
                    return None

            return payload

        except Exception as e:
            logger.debug(f"Token verification failed: {e}")
            return None

    def revoke_token(self, token: str) -> bool:
        """Revoke a token."""
        with self._lock:
            if token in self._tokens:
                self._tokens[token].revoked = True
                self._tokens[token].revoked_at = datetime.now()
                return True
            return False

    def verify_api_key(self, api_key: str) -> Optional[str]:
        """Verify an API key and return user_id."""
        with self._lock:
            token = self._tokens.get(api_key)
            if token and token.is_valid and token.token_type == TokenType.API_KEY:
                return token.user_id
            return None


# ============================================================================
# SESSION MANAGER
# ============================================================================

class SessionManager:
    """
    Manages user sessions.
    """

    def __init__(self, config: AuthConfig):
        """Initialize session manager."""
        self.config = config
        self._sessions: Dict[str, Session] = {}
        self._user_sessions: Dict[str, Set[str]] = defaultdict(set)
        self._lock = threading.RLock()

    def create_session(
        self,
        user_id: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Session:
        """Create a new session."""
        session = Session(
            id=str(uuid.uuid4()),
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.now() + timedelta(minutes=self.config.session_timeout_minutes)
        )

        with self._lock:
            self._sessions[session.id] = session
            self._user_sessions[user_id].add(session.id)

        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session and session.active:
                if session.expires_at and datetime.now() > session.expires_at:
                    session.active = False
                    return None
                return session
            return None

    def refresh_session(self, session_id: str) -> bool:
        """Refresh session activity."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session and session.active:
                session.last_activity = datetime.now()
                session.expires_at = datetime.now() + timedelta(
                    minutes=self.config.session_timeout_minutes
                )
                return True
            return False

    def end_session(self, session_id: str) -> bool:
        """End a session."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.active = False
                self._user_sessions[session.user_id].discard(session_id)
                return True
            return False

    def end_all_user_sessions(self, user_id: str) -> int:
        """End all sessions for a user."""
        count = 0
        with self._lock:
            session_ids = list(self._user_sessions.get(user_id, set()))
            for session_id in session_ids:
                if self.end_session(session_id):
                    count += 1
        return count

    def get_user_sessions(self, user_id: str) -> List[Session]:
        """Get all active sessions for a user."""
        with self._lock:
            session_ids = self._user_sessions.get(user_id, set())
            return [
                self._sessions[sid]
                for sid in session_ids
                if sid in self._sessions and self._sessions[sid].active
            ]


# ============================================================================
# RBAC MANAGER
# ============================================================================

class RBACManager:
    """
    Role-Based Access Control manager.
    """

    def __init__(self):
        """Initialize RBAC manager."""
        self._roles: Dict[str, Role] = {}
        self._permissions: Dict[str, Permission] = {}
        self._lock = threading.RLock()

        # Create default roles
        self._create_default_roles()

    def _create_default_roles(self) -> None:
        """Create default roles."""
        # Admin role
        admin = Role(
            id="admin",
            name="Administrator",
            description="Full system access",
            permissions={"*:admin"}
        )
        self._roles["admin"] = admin

        # User role
        user = Role(
            id="user",
            name="User",
            description="Standard user access",
            permissions={"profile:read", "profile:update"}
        )
        self._roles["user"] = user

    def create_role(
        self,
        name: str,
        description: str = "",
        permissions: Optional[Set[str]] = None,
        parent_roles: Optional[List[str]] = None
    ) -> Role:
        """Create a new role."""
        role = Role(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            permissions=permissions or set(),
            parent_roles=parent_roles or []
        )

        with self._lock:
            self._roles[role.id] = role

        return role

    def get_role(self, role_id: str) -> Optional[Role]:
        """Get a role by ID."""
        return self._roles.get(role_id)

    def add_permission_to_role(
        self,
        role_id: str,
        resource: str,
        action: PermissionAction
    ) -> bool:
        """Add a permission to a role."""
        with self._lock:
            role = self._roles.get(role_id)
            if role:
                role.permissions.add(f"{resource}:{action.value}")
                return True
            return False

    def remove_permission_from_role(
        self,
        role_id: str,
        resource: str,
        action: PermissionAction
    ) -> bool:
        """Remove a permission from a role."""
        with self._lock:
            role = self._roles.get(role_id)
            if role:
                role.permissions.discard(f"{resource}:{action.value}")
                return True
            return False

    def get_role_permissions(
        self,
        role_id: str,
        include_inherited: bool = True
    ) -> Set[str]:
        """Get all permissions for a role."""
        role = self._roles.get(role_id)
        if not role:
            return set()

        permissions = role.permissions.copy()

        if include_inherited:
            for parent_id in role.parent_roles:
                permissions |= self.get_role_permissions(parent_id, True)

        return permissions

    def get_user_permissions(
        self,
        roles: Set[str]
    ) -> Set[str]:
        """Get all permissions for a set of roles."""
        permissions = set()
        for role_id in roles:
            permissions |= self.get_role_permissions(role_id)
        return permissions

    def check_permission(
        self,
        roles: Set[str],
        resource: str,
        action: PermissionAction
    ) -> bool:
        """Check if roles have a permission."""
        permissions = self.get_user_permissions(roles)

        # Check exact match
        permission_key = f"{resource}:{action.value}"
        if permission_key in permissions:
            return True

        # Check wildcard
        if "*:admin" in permissions:
            return True

        if f"{resource}:admin" in permissions:
            return True

        if f"*:{action.value}" in permissions:
            return True

        return False


# ============================================================================
# OAUTH MANAGER
# ============================================================================

class OAuthManager:
    """
    Manages OAuth authentication.
    """

    def __init__(self):
        """Initialize OAuth manager."""
        self._providers: Dict[str, OAuthProvider] = {}
        self._states: Dict[str, Dict[str, Any]] = {}

    def register_provider(self, provider: OAuthProvider) -> None:
        """Register an OAuth provider."""
        self._providers[provider.id] = provider

    def get_provider(self, provider_id: str) -> Optional[OAuthProvider]:
        """Get a provider by ID."""
        return self._providers.get(provider_id)

    def get_authorization_url(
        self,
        provider_id: str,
        redirect_uri: str,
        state: Optional[str] = None
    ) -> Optional[str]:
        """Get OAuth authorization URL."""
        provider = self._providers.get(provider_id)
        if not provider:
            return None

        state = state or secrets.token_urlsafe(32)

        # Store state
        self._states[state] = {
            'provider_id': provider_id,
            'redirect_uri': redirect_uri,
            'created_at': datetime.now()
        }

        params = {
            'client_id': provider.client_id,
            'redirect_uri': redirect_uri,
            'scope': ' '.join(provider.scopes),
            'response_type': 'code',
            'state': state
        }

        query = '&'.join(f"{k}={v}" for k, v in params.items())
        return f"{provider.authorize_url}?{query}"

    async def exchange_code(
        self,
        provider_id: str,
        code: str,
        redirect_uri: str
    ) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for tokens."""
        import aiohttp

        provider = self._providers.get(provider_id)
        if not provider:
            return None

        try:
            async with aiohttp.ClientSession() as session:
                data = {
                    'grant_type': 'authorization_code',
                    'code': code,
                    'redirect_uri': redirect_uri,
                    'client_id': provider.client_id,
                    'client_secret': provider.client_secret
                }

                async with session.post(provider.token_url, data=data) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return None

        except Exception as e:
            logger.error(f"OAuth token exchange failed: {e}")
            return None

    async def get_user_info(
        self,
        provider_id: str,
        access_token: str
    ) -> Optional[Dict[str, Any]]:
        """Get user info from OAuth provider."""
        import aiohttp

        provider = self._providers.get(provider_id)
        if not provider:
            return None

        try:
            async with aiohttp.ClientSession() as session:
                headers = {'Authorization': f'Bearer {access_token}'}

                async with session.get(provider.userinfo_url, headers=headers) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return None

        except Exception as e:
            logger.error(f"OAuth user info failed: {e}")
            return None


# ============================================================================
# MFA MANAGER
# ============================================================================

class MFAManager:
    """
    Multi-Factor Authentication manager.
    """

    def __init__(self, config: AuthConfig):
        """Initialize MFA manager."""
        self.config = config

    def generate_secret(self) -> str:
        """Generate a TOTP secret."""
        return base64.b32encode(secrets.token_bytes(20)).decode()

    def get_totp_uri(
        self,
        secret: str,
        username: str
    ) -> str:
        """Get TOTP URI for authenticator apps."""
        issuer = self.config.mfa_issuer
        return f"otpauth://totp/{issuer}:{username}?secret={secret}&issuer={issuer}"

    def verify_totp(self, secret: str, code: str) -> bool:
        """Verify a TOTP code."""
        try:
            # Decode secret
            key = base64.b32decode(secret)

            # Current time step (30 seconds)
            counter = int(time.time() // 30)

            # Check current and adjacent time steps
            for offset in [-1, 0, 1]:
                expected = self._generate_totp(key, counter + offset)
                if hmac.compare_digest(expected, code):
                    return True

            return False

        except Exception:
            return False

    def _generate_totp(self, key: bytes, counter: int) -> str:
        """Generate TOTP code."""
        counter_bytes = counter.to_bytes(8, 'big')
        hmac_result = hmac.new(key, counter_bytes, hashlib.sha1).digest()

        offset = hmac_result[-1] & 0x0F
        code = (
            (hmac_result[offset] & 0x7F) << 24 |
            hmac_result[offset + 1] << 16 |
            hmac_result[offset + 2] << 8 |
            hmac_result[offset + 3]
        ) % 1000000

        return str(code).zfill(6)

    def generate_backup_codes(self, count: int = 10) -> List[str]:
        """Generate backup codes."""
        return [secrets.token_hex(4).upper() for _ in range(count)]


# ============================================================================
# MAIN AUTH ENGINE
# ============================================================================

class AuthEngine:
    """
    Main authentication engine.

    Features:
    - User management
    - JWT tokens
    - OAuth integration
    - RBAC
    - MFA
    - Sessions

    "Ba'el controls all access." — Ba'el
    """

    def __init__(self, config: Optional[AuthConfig] = None):
        """Initialize auth engine."""
        self.config = config or AuthConfig()

        # Components
        self.passwords = PasswordManager(self.config)
        self.tokens = TokenManager(self.config)
        self.sessions = SessionManager(self.config)
        self.rbac = RBACManager()
        self.oauth = OAuthManager()
        self.mfa = MFAManager(self.config)

        # User storage
        self._users: Dict[str, User] = {}
        self._username_index: Dict[str, str] = {}  # username -> id
        self._email_index: Dict[str, str] = {}  # email -> id

        self._lock = threading.RLock()

        logger.info("AuthEngine initialized")

    # ========================================================================
    # USER MANAGEMENT
    # ========================================================================

    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        roles: Optional[Set[str]] = None,
        **kwargs
    ) -> Tuple[Optional[User], List[str]]:
        """Create a new user."""
        errors = []

        # Validate password
        valid, password_errors = self.passwords.validate_password(password)
        if not valid:
            errors.extend(password_errors)

        # Check uniqueness
        with self._lock:
            if username.lower() in self._username_index:
                errors.append("Username already exists")

            if email.lower() in self._email_index:
                errors.append("Email already exists")

        if errors:
            return None, errors

        # Create user
        user = User(
            id=str(uuid.uuid4()),
            username=username,
            email=email,
            password_hash=self.passwords.hash_password(password),
            roles=roles or {"user"},
            password_changed_at=datetime.now(),
            **kwargs
        )

        with self._lock:
            self._users[user.id] = user
            self._username_index[username.lower()] = user.id
            self._email_index[email.lower()] = user.id

        return user, []

    def get_user(self, user_id: str) -> Optional[User]:
        """Get a user by ID."""
        return self._users.get(user_id)

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get a user by username."""
        user_id = self._username_index.get(username.lower())
        if user_id:
            return self._users.get(user_id)
        return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email."""
        user_id = self._email_index.get(email.lower())
        if user_id:
            return self._users.get(user_id)
        return None

    def update_user(
        self,
        user_id: str,
        **kwargs
    ) -> bool:
        """Update a user."""
        with self._lock:
            user = self._users.get(user_id)
            if not user:
                return False

            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)

            return True

    def delete_user(self, user_id: str) -> bool:
        """Delete a user."""
        with self._lock:
            user = self._users.get(user_id)
            if not user:
                return False

            del self._users[user_id]
            del self._username_index[user.username.lower()]
            del self._email_index[user.email.lower()]

            # End all sessions
            self.sessions.end_all_user_sessions(user_id)

            return True

    # ========================================================================
    # AUTHENTICATION
    # ========================================================================

    def authenticate(
        self,
        username: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[Optional[Session], Optional[str]]:
        """Authenticate a user."""
        # Find user
        user = self.get_user_by_username(username)
        if not user:
            user = self.get_user_by_email(username)

        if not user:
            return None, "Invalid credentials"

        # Check if locked
        if user.locked_until and datetime.now() < user.locked_until:
            return None, "Account is locked"

        # Check status
        if not user.is_active:
            return None, "Account is not active"

        # Verify password
        if not self.passwords.verify_password(password, user.password_hash):
            user.failed_login_attempts += 1

            if user.failed_login_attempts >= self.config.max_login_attempts:
                user.locked_until = datetime.now() + timedelta(
                    minutes=self.config.lockout_duration_minutes
                )

            return None, "Invalid credentials"

        # Reset failed attempts
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.now()

        # Check MFA
        if user.mfa_enabled:
            return None, "MFA_REQUIRED"

        # Create tokens and session
        access_token = self.tokens.create_access_token(
            user.id,
            claims={'roles': list(user.roles)}
        )
        refresh_token = self.tokens.create_refresh_token(user.id)

        session = self.sessions.create_session(
            user_id=user.id,
            access_token=access_token,
            refresh_token=refresh_token,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return session, None

    def verify_mfa(
        self,
        username: str,
        code: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[Optional[Session], Optional[str]]:
        """Verify MFA and complete authentication."""
        user = self.get_user_by_username(username)
        if not user:
            return None, "User not found"

        if not user.mfa_secret:
            return None, "MFA not configured"

        if not self.mfa.verify_totp(user.mfa_secret, code):
            return None, "Invalid MFA code"

        # Create tokens and session
        access_token = self.tokens.create_access_token(
            user.id,
            claims={'roles': list(user.roles)}
        )
        refresh_token = self.tokens.create_refresh_token(user.id)

        session = self.sessions.create_session(
            user_id=user.id,
            access_token=access_token,
            refresh_token=refresh_token,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return session, None

    def refresh_auth(
        self,
        refresh_token: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """Refresh authentication using refresh token."""
        payload = self.tokens.verify_token(refresh_token)

        if not payload:
            return None, "Invalid refresh token"

        if payload.get('type') != TokenType.REFRESH.value:
            return None, "Invalid token type"

        user_id = payload.get('sub')
        user = self.get_user(user_id)

        if not user or not user.is_active:
            return None, "User not found or inactive"

        # Create new access token
        access_token = self.tokens.create_access_token(
            user.id,
            claims={'roles': list(user.roles)}
        )

        return access_token, None

    def logout(self, session_id: str) -> bool:
        """Logout a session."""
        session = self.sessions.get_session(session_id)
        if session:
            self.tokens.revoke_token(session.access_token)
            if session.refresh_token:
                self.tokens.revoke_token(session.refresh_token)
            return self.sessions.end_session(session_id)
        return False

    # ========================================================================
    # AUTHORIZATION
    # ========================================================================

    def authorize(
        self,
        token: str,
        resource: str,
        action: PermissionAction
    ) -> bool:
        """Check if a token is authorized for an action."""
        payload = self.tokens.verify_token(token)

        if not payload:
            return False

        roles = set(payload.get('roles', []))
        return self.rbac.check_permission(roles, resource, action)

    def check_permission(
        self,
        user_id: str,
        resource: str,
        action: PermissionAction
    ) -> bool:
        """Check if a user has a permission."""
        user = self.get_user(user_id)
        if not user:
            return False

        return self.rbac.check_permission(user.roles, resource, action)

    # ========================================================================
    # PASSWORD RESET
    # ========================================================================

    def request_password_reset(self, email: str) -> Optional[str]:
        """Request a password reset token."""
        user = self.get_user_by_email(email)
        if not user:
            return None

        # Create reset token (simple implementation)
        token = secrets.token_urlsafe(32)

        # Store token (in production, use proper token storage)
        reset_token = Token(
            id=str(uuid.uuid4()),
            token_type=TokenType.RESET,
            value=token,
            user_id=user.id,
            expires_at=datetime.now() + timedelta(hours=1)
        )

        with self._lock:
            self.tokens._tokens[token] = reset_token

        return token

    def reset_password(
        self,
        token: str,
        new_password: str
    ) -> Tuple[bool, List[str]]:
        """Reset password using token."""
        with self._lock:
            stored_token = self.tokens._tokens.get(token)

        if not stored_token or not stored_token.is_valid:
            return False, ["Invalid or expired token"]

        if stored_token.token_type != TokenType.RESET:
            return False, ["Invalid token type"]

        # Validate new password
        valid, errors = self.passwords.validate_password(new_password)
        if not valid:
            return False, errors

        # Update password
        user = self.get_user(stored_token.user_id)
        if not user:
            return False, ["User not found"]

        user.password_hash = self.passwords.hash_password(new_password)
        user.password_changed_at = datetime.now()

        # Revoke token
        self.tokens.revoke_token(token)

        # End all sessions
        self.sessions.end_all_user_sessions(user.id)

        return True, []

    # ========================================================================
    # STATUS
    # ========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        return {
            'total_users': len(self._users),
            'active_users': sum(1 for u in self._users.values() if u.is_active),
            'roles': len(self.rbac._roles),
            'oauth_providers': len(self.oauth._providers)
        }


# ============================================================================
# CONVENIENCE INSTANCE
# ============================================================================

auth_engine = AuthEngine()
