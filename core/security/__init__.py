"""
OAuth2 and RBAC (Role-Based Access Control) security module.

Implements:
- OAuth2 authorization code flow
- JWT token generation and validation
- Role-based access control with 4 roles
- API key management
- Comprehensive audit logging
- Permission caching
"""

import hashlib
import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

import jwt

logger = logging.getLogger(__name__)


@dataclass
class Role:
    """Role definition."""
    id: str
    name: str
    permissions: Set[str]
    description: str


@dataclass
class User:
    """User definition."""
    user_id: str
    username: str
    email: str
    roles: List[str]
    created_at: datetime = field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    is_active: bool = True


@dataclass
class APIKey:
    """API key definition."""
    key_id: str
    key_hash: str  # SHA256 hash of actual key
    user_id: str
    name: str
    scopes: List[str]
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    is_active: bool = True


@dataclass
class AuditLog:
    """Audit log entry."""
    log_id: str
    timestamp: datetime
    user_id: str
    action: str
    resource_type: str
    resource_id: str
    status: str  # success, failure
    details: Dict = field(default_factory=dict)


class RBACEngine:
    """Role-Based Access Control engine."""

    def __init__(self):
        """Initialize RBAC with predefined roles."""
        self.roles: Dict[str, Role] = {}
        self.users: Dict[str, User] = {}
        self.user_permissions_cache: Dict[str, Set[str]] = {}
        self._setup_default_roles()

    def _setup_default_roles(self):
        """Set up default BAEL roles."""
        roles = {
            "admin": Role(
                id="admin",
                name="Administrator",
                permissions={
                    # Agent management
                    "agents:create", "agents:read", "agents:update", "agents:delete",
                    # Workflow management
                    "workflows:create", "workflows:read", "workflows:update", "workflows:delete",
                    "workflows:execute", "workflows:cancel",
                    # Plugin management
                    "plugins:create", "plugins:read", "plugins:update", "plugins:delete",
                    "plugins:install", "plugins:uninstall",
                    # Cluster management
                    "cluster:read", "cluster:configure", "cluster:scale",
                    # User management
                    "users:create", "users:read", "users:update", "users:delete",
                    "users:assign_roles",
                    # Security
                    "security:manage_keys", "security:view_audit_log",
                    # System
                    "system:configure", "system:view_metrics"
                },
                description="Full system access"
            ),
            "developer": Role(
                id="developer",
                name="Developer",
                permissions={
                    # Agent management
                    "agents:read", "agents:create", "agents:update",
                    # Workflow management
                    "workflows:read", "workflows:create", "workflows:update",
                    "workflows:execute", "workflows:cancel",
                    # Plugin management
                    "plugins:read", "plugins:install",
                    # Cluster
                    "cluster:read",
                    # Self service
                    "users:read_self",
                    # Security
                    "security:manage_keys_self",
                    # Metrics
                    "system:view_metrics"
                },
                description="Development and deployment access"
            ),
            "operator": Role(
                id="operator",
                name="Operator",
                permissions={
                    # Agent execution only
                    "agents:read", "agents:execute",
                    # Workflow execution
                    "workflows:read", "workflows:execute", "workflows:cancel",
                    # Plugin
                    "plugins:read",
                    # Cluster monitoring
                    "cluster:read",
                    # Metrics
                    "system:view_metrics"
                },
                description="Operational and execution access"
            ),
            "viewer": Role(
                id="viewer",
                name="Viewer",
                permissions={
                    # Read-only access
                    "agents:read",
                    "workflows:read",
                    "plugins:read",
                    "cluster:read",
                    "system:view_metrics",
                    "users:read_self"
                },
                description="Read-only access"
            )
        }

        for role in roles.values():
            self.roles[role.id] = role

    def add_user(self, user_id: str, username: str, email: str, roles: List[str]) -> User:
        """Add user to the system."""
        user = User(
            user_id=user_id,
            username=username,
            email=email,
            roles=roles
        )
        self.users[user_id] = user
        self._invalidate_permission_cache(user_id)
        logger.info(f"User created: {user_id} with roles {roles}")
        return user

    def assign_role(self, user_id: str, role_id: str) -> bool:
        """Assign role to user."""
        if user_id not in self.users:
            return False
        if role_id not in self.roles:
            return False

        if role_id not in self.users[user_id].roles:
            self.users[user_id].roles.append(role_id)
            self._invalidate_permission_cache(user_id)
            logger.info(f"Role '{role_id}' assigned to user '{user_id}'")

        return True

    def revoke_role(self, user_id: str, role_id: str) -> bool:
        """Revoke role from user."""
        if user_id not in self.users:
            return False

        if role_id in self.users[user_id].roles:
            self.users[user_id].roles.remove(role_id)
            self._invalidate_permission_cache(user_id)
            logger.info(f"Role '{role_id}' revoked from user '{user_id}'")

        return True

    def get_user_permissions(self, user_id: str) -> Set[str]:
        """Get all permissions for user (with caching)."""
        if user_id in self.user_permissions_cache:
            return self.user_permissions_cache[user_id]

        if user_id not in self.users:
            return set()

        user = self.users[user_id]
        permissions = set()

        for role_id in user.roles:
            if role_id in self.roles:
                permissions.update(self.roles[role_id].permissions)

        self.user_permissions_cache[user_id] = permissions
        return permissions

    def check_permission(self, user_id: str, permission: str) -> bool:
        """Check if user has specific permission."""
        permissions = self.get_user_permissions(user_id)

        # Support wildcard permissions (e.g., "agents:*")
        if permission in permissions:
            return True

        resource, action = permission.split(":", 1)
        wildcard = f"{resource}:*"
        return wildcard in permissions

    def require_permission(self, user_id: str, permission: str) -> bool:
        """Require permission, raise exception if not granted."""
        if not self.check_permission(user_id, permission):
            logger.warning(f"Permission denied: user '{user_id}' for '{permission}'")
            raise PermissionError(f"User lacks permission: {permission}")
        return True

    def _invalidate_permission_cache(self, user_id: str):
        """Invalidate permission cache for user."""
        if user_id in self.user_permissions_cache:
            del self.user_permissions_cache[user_id]


class OAuth2Provider:
    """OAuth2 authorization provider."""

    def __init__(self, secret_key: str, access_token_expire_minutes: int = 60):
        """
        Initialize OAuth2 provider.

        Args:
            secret_key: Secret key for JWT signing
            access_token_expire_minutes: Access token expiration time
        """
        self.secret_key = secret_key
        self.access_token_expire_minutes = access_token_expire_minutes
        self.authorization_codes: Dict[str, Dict] = {}
        self.refresh_tokens: Dict[str, Dict] = {}

    def generate_authorization_code(
        self,
        client_id: str,
        user_id: str,
        scopes: List[str],
        redirect_uri: str
    ) -> str:
        """
        Generate authorization code for authorization code flow.

        Args:
            client_id: OAuth2 client ID
            user_id: User ID
            scopes: Requested scopes
            redirect_uri: Redirect URI

        Returns:
            str: Authorization code
        """
        code = secrets.token_urlsafe(32)
        self.authorization_codes[code] = {
            "client_id": client_id,
            "user_id": user_id,
            "scopes": scopes,
            "redirect_uri": redirect_uri,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(minutes=10)  # 10 min expiry
        }

        logger.info(f"Authorization code generated for client '{client_id}' user '{user_id}'")
        return code

    def exchange_code_for_token(
        self,
        code: str,
        client_id: str,
        client_secret: str
    ) -> Optional[Dict]:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret

        Returns:
            Dict with access_token, refresh_token, expires_in
        """
        if code not in self.authorization_codes:
            logger.warning(f"Invalid authorization code: {code}")
            return None

        auth_code_data = self.authorization_codes[code]

        # Verify not expired
        if datetime.now() > auth_code_data["expires_at"]:
            del self.authorization_codes[code]
            logger.warning(f"Authorization code expired: {code}")
            return None

        # Verify client
        if client_id != auth_code_data["client_id"]:
            logger.warning(f"Client mismatch for authorization code")
            return None

        # Generate tokens
        access_token = self._generate_access_token(
            auth_code_data["user_id"],
            auth_code_data["scopes"]
        )

        refresh_token = self._generate_refresh_token(
            auth_code_data["user_id"],
            auth_code_data["scopes"]
        )

        # Clean up used code
        del self.authorization_codes[code]

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": self.access_token_expire_minutes * 60
        }

    def exchange_credentials_for_token(
        self,
        client_id: str,
        client_secret: str,
        scopes: List[str]
    ) -> Dict:
        """
        Exchange client credentials for token (client credentials flow).

        Args:
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            scopes: Requested scopes

        Returns:
            Dict with access_token, expires_in
        """
        # In production, verify client_secret
        access_token = self._generate_client_token(client_id, scopes)

        logger.info(f"Client credentials token generated for '{client_id}'")

        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": self.access_token_expire_minutes * 60
        }

    def refresh_access_token(self, refresh_token: str) -> Optional[Dict]:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Refresh token

        Returns:
            Dict with new access_token, expires_in
        """
        try:
            payload = jwt.decode(refresh_token, self.secret_key, algorithms=['HS256'])

            if payload.get("type") != "refresh":
                return None

            user_id = payload.get("user_id")
            scopes = payload.get("scopes", [])

            new_access_token = self._generate_access_token(user_id, scopes)

            logger.info(f"Access token refreshed for user '{user_id}'")

            return {
                "access_token": new_access_token,
                "token_type": "Bearer",
                "expires_in": self.access_token_expire_minutes * 60
            }

        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid refresh token: {e}")
            return None

    def _generate_access_token(self, user_id: str, scopes: List[str]) -> str:
        """Generate JWT access token."""
        payload = {
            "user_id": user_id,
            "scopes": scopes,
            "type": "access",
            "iat": datetime.now(),
            "exp": datetime.now() + timedelta(minutes=self.access_token_expire_minutes)
        }

        return jwt.encode(payload, self.secret_key, algorithm='HS256')

    def _generate_refresh_token(self, user_id: str, scopes: List[str]) -> str:
        """Generate JWT refresh token."""
        payload = {
            "user_id": user_id,
            "scopes": scopes,
            "type": "refresh",
            "iat": datetime.now(),
            "exp": datetime.now() + timedelta(days=30)  # 30 days
        }

        return jwt.encode(payload, self.secret_key, algorithm='HS256')

    def _generate_client_token(self, client_id: str, scopes: List[str]) -> str:
        """Generate JWT client token."""
        payload = {
            "client_id": client_id,
            "scopes": scopes,
            "type": "client",
            "iat": datetime.now(),
            "exp": datetime.now() + timedelta(minutes=self.access_token_expire_minutes)
        }

        return jwt.encode(payload, self.secret_key, algorithm='HS256')

    def validate_token(self, token: str) -> Optional[Dict]:
        """
        Validate JWT token and return payload.

        Args:
            token: JWT token

        Returns:
            Dict with token payload, or None if invalid
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None


class APIKeyManager:
    """Manage API keys for service-to-service authentication."""

    def __init__(self):
        """Initialize API key manager."""
        self.api_keys: Dict[str, APIKey] = {}

    def generate_key(
        self,
        user_id: str,
        name: str,
        scopes: List[str],
        expires_in_days: Optional[int] = None
    ) -> Tuple[str, APIKey]:
        """
        Generate new API key.

        Args:
            user_id: User ID
            name: Key name
            scopes: Key scopes
            expires_in_days: Expiration in days (None = no expiry)

        Returns:
            Tuple[str, APIKey]: (actual_key, key_object)
        """
        # Generate random key
        actual_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(actual_key.encode()).hexdigest()

        key_id = f"key_{secrets.token_hex(8)}"

        api_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            user_id=user_id,
            name=name,
            scopes=scopes,
            expires_at=datetime.now() + timedelta(days=expires_in_days) if expires_in_days else None
        )

        self.api_keys[key_id] = api_key
        logger.info(f"API key generated: '{name}' for user '{user_id}'")

        return actual_key, api_key

    def validate_key(self, api_key: str) -> Optional[APIKey]:
        """
        Validate API key and return key object.

        Args:
            api_key: API key to validate

        Returns:
            APIKey object if valid, else None
        """
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        for key_id, key_obj in self.api_keys.items():
            if key_obj.key_hash == key_hash:
                # Check if expired
                if key_obj.expires_at and datetime.now() > key_obj.expires_at:
                    logger.warning(f"API key expired: {key_id}")
                    return None

                # Check if active
                if not key_obj.is_active:
                    logger.warning(f"API key disabled: {key_id}")
                    return None

                # Update last used
                key_obj.last_used = datetime.now()
                return key_obj

        logger.warning("Invalid API key")
        return None

    def revoke_key(self, key_id: str) -> bool:
        """
        Revoke API key.

        Args:
            key_id: Key ID to revoke

        Returns:
            bool: Success status
        """
        if key_id in self.api_keys:
            self.api_keys[key_id].is_active = False
            logger.info(f"API key revoked: {key_id}")
            return True
        return False


class AuditLogger:
    """Comprehensive audit logging."""

    def __init__(self):
        """Initialize audit logger."""
        self.logs: List[AuditLog] = []

    def log(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        status: str = "success",
        details: Optional[Dict] = None
    ):
        """
        Log action for audit trail.

        Args:
            user_id: User performing action
            action: Action taken
            resource_type: Type of resource
            resource_id: ID of resource
            status: success or failure
            details: Additional details
        """
        log_id = f"log_{secrets.token_hex(8)}"

        audit_log = AuditLog(
            log_id=log_id,
            timestamp=datetime.now(),
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            details=details or {}
        )

        self.logs.append(audit_log)

        level = logging.INFO if status == "success" else logging.WARNING
        logger.log(
            level,
            f"AUDIT: {user_id} {action} {resource_type}:{resource_id} [{status}]"
        )

    def get_audit_trail(
        self,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        days: int = 90
    ) -> List[AuditLog]:
        """
        Get audit trail with filtering.

        Args:
            user_id: Filter by user
            resource_type: Filter by resource type
            days: Look back days (default 90)

        Returns:
            List of audit logs
        """
        cutoff = datetime.now() - timedelta(days=days)

        logs = [log for log in self.logs if log.timestamp > cutoff]

        if user_id:
            logs = [log for log in logs if log.user_id == user_id]

        if resource_type:
            logs = [log for log in logs if log.resource_type == resource_type]

        return logs


if __name__ == "__main__":
    # Example usage
    rbac = RBACEngine()
    oauth2 = OAuth2Provider("secret-key")
    api_key_manager = APIKeyManager()
    audit_logger = AuditLogger()

    # Create user with developer role
    user = rbac.add_user("user1", "john", "john@example.com", ["developer"])
    print(f"User created: {user.user_id}")

    # Check permissions
    permissions = rbac.get_user_permissions("user1")
    print(f"Developer permissions: {len(permissions)}")

    # Generate API key
    key, key_obj = api_key_manager.generate_key("user1", "production-key", ["read", "write"])
    print(f"API key generated: {key_obj.key_id}")

    # Validate key
    validated = api_key_manager.validate_key(key)
    print(f"Key validated: {validated is not None}")
