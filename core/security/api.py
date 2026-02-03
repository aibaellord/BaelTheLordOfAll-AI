"""
OAuth2 and security REST API endpoints.

Provides endpoints for:
- User authentication (login, logout)
- OAuth2 token endpoints
- API key management
- Permission checking
- Audit log access
"""

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Import security components (assuming they're available)
try:
    from core.security import (APIKeyManager, AuditLogger, OAuth2Provider,
                               RBACEngine)
except ImportError:
    pass  # For standalone testing


router = APIRouter(prefix="/api/v1/security", tags=["Security"])


# ============================================================================
# Request/Response Models
# ============================================================================

class LoginRequest(BaseModel):
    """User login request."""
    username: str
    password: str


class LoginResponse(BaseModel):
    """User login response."""
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class TokenRequest(BaseModel):
    """OAuth2 token request."""
    grant_type: str  # authorization_code, refresh_token, client_credentials
    code: Optional[str] = None
    refresh_token: Optional[str] = None
    client_id: str
    client_secret: str
    redirect_uri: Optional[str] = None
    scopes: Optional[List[str]] = None


class TokenResponse(BaseModel):
    """OAuth2 token response."""
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: Optional[str] = None


class APIKeyCreateRequest(BaseModel):
    """Create API key request."""
    name: str
    scopes: List[str]
    expires_in_days: Optional[int] = None


class APIKeyCreateResponse(BaseModel):
    """Create API key response."""
    key_id: str
    key: str
    name: str
    scopes: List[str]
    created_at: str
    expires_at: Optional[str] = None


class PermissionCheckRequest(BaseModel):
    """Check permission request."""
    permission: str


class PermissionCheckResponse(BaseModel):
    """Check permission response."""
    permission: str
    granted: bool


class AssignRoleRequest(BaseModel):
    """Assign role request."""
    user_id: str
    role_id: str


class RevokeRoleRequest(BaseModel):
    """Revoke role request."""
    user_id: str
    role_id: str


class AuditLogResponse(BaseModel):
    """Audit log response."""
    log_id: str
    timestamp: str
    user_id: str
    action: str
    resource_type: str
    resource_id: str
    status: str
    details: Dict


# ============================================================================
# Global instances (in production, use dependency injection)
# ============================================================================

rbac = RBACEngine()
oauth2 = OAuth2Provider("bael-secret-key")
api_key_manager = APIKeyManager()
audit_logger = AuditLogger()

# In-memory user storage (use database in production)
users_db = {
    "admin": {
        "password": "admin123",  # In production: hashed
        "user_id": "admin",
        "roles": ["admin"]
    }
}


# ============================================================================
# Authentication Helpers
# ============================================================================

def get_current_user(authorization: Optional[str] = Header(None)) -> str:
    """
    Get current user from Bearer token.

    Args:
        authorization: Authorization header

    Returns:
        str: User ID

    Raises:
        HTTPException: If token is invalid
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization header")

    token = authorization[7:]  # Remove "Bearer "
    payload = oauth2.validate_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    return payload.get("user_id", "")


def require_permission(permission: str):
    """
    Dependency to require specific permission.

    Args:
        permission: Required permission

    Returns:
        Callable: Dependency function
    """
    def _require(user_id: str = Depends(get_current_user)) -> str:
        rbac.require_permission(user_id, permission)
        return user_id
    return _require


# ============================================================================
# Authentication Endpoints
# ============================================================================

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest) -> LoginResponse:
    """
    User login.

    Args:
        request: Login credentials

    Returns:
        LoginResponse: Tokens
    """
    # Verify credentials (in production: use proper authentication)
    if request.username not in users_db:
        audit_logger.log("unknown", "login", "user", request.username, "failure",
                        {"reason": "invalid_username"})
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user = users_db[request.username]
    if user["password"] != request.password:  # In production: check hash
        audit_logger.log(request.username, "login", "user", request.username, "failure",
                        {"reason": "invalid_password"})
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Add user to RBAC if not exists
    if request.username not in rbac.users:
        rbac.add_user(user["user_id"], request.username, f"{request.username}@bael.ai", user["roles"])

    # Generate tokens
    tokens = oauth2.exchange_credentials_for_token(
        client_id=user["user_id"],
        client_secret="secret",  # In production: use proper client secret
        scopes=["read", "write"]
    )

    # Generate refresh token
    refresh_token = oauth2._generate_refresh_token(
        user["user_id"],
        ["read", "write"]
    )

    audit_logger.log(request.username, "login", "user", request.username, "success")

    return LoginResponse(
        access_token=tokens["access_token"],
        refresh_token=refresh_token,
        token_type=tokens["token_type"],
        expires_in=tokens["expires_in"]
    )


@router.post("/logout")
async def logout(user_id: str = Depends(get_current_user)):
    """
    User logout.

    Args:
        user_id: Current user ID
    """
    audit_logger.log(user_id, "logout", "user", user_id, "success")
    return {"message": "Logged out successfully"}


# ============================================================================
# OAuth2 Endpoints
# ============================================================================

@router.post("/oauth2/token", response_model=TokenResponse)
async def oauth2_token(request: TokenRequest) -> TokenResponse:
    """
    OAuth2 token endpoint.

    Supports:
    - authorization_code: Exchange code for token
    - refresh_token: Refresh access token
    - client_credentials: Get token with client credentials

    Args:
        request: Token request

    Returns:
        TokenResponse: New tokens
    """
    if request.grant_type == "authorization_code":
        tokens = oauth2.exchange_code_for_token(
            code=request.code,
            client_id=request.client_id,
            client_secret=request.client_secret
        )

        if not tokens:
            raise HTTPException(status_code=400, detail="Invalid authorization code")

        audit_logger.log(request.client_id, "oauth2_exchange", "token",
                        request.client_id, "success")

        return TokenResponse(
            access_token=tokens["access_token"],
            token_type=tokens["token_type"],
            expires_in=tokens["expires_in"],
            refresh_token=tokens.get("refresh_token")
        )

    elif request.grant_type == "refresh_token":
        tokens = oauth2.refresh_access_token(request.refresh_token)

        if not tokens:
            raise HTTPException(status_code=400, detail="Invalid refresh token")

        audit_logger.log(request.client_id, "oauth2_refresh", "token",
                        request.client_id, "success")

        return TokenResponse(
            access_token=tokens["access_token"],
            token_type=tokens["token_type"],
            expires_in=tokens["expires_in"]
        )

    elif request.grant_type == "client_credentials":
        tokens = oauth2.exchange_credentials_for_token(
            client_id=request.client_id,
            client_secret=request.client_secret,
            scopes=request.scopes or ["read", "write"]
        )

        audit_logger.log(request.client_id, "oauth2_credentials", "token",
                        request.client_id, "success")

        return TokenResponse(
            access_token=tokens["access_token"],
            token_type=tokens["token_type"],
            expires_in=tokens["expires_in"]
        )

    else:
        raise HTTPException(status_code=400, detail="Unsupported grant type")


# ============================================================================
# API Key Endpoints
# ============================================================================

@router.post("/api-keys", response_model=APIKeyCreateResponse)
async def create_api_key(
    request: APIKeyCreateRequest,
    user_id: str = Depends(require_permission("security:manage_keys_self"))
) -> APIKeyCreateResponse:
    """
    Create new API key.

    Args:
        request: API key creation request
        user_id: Current user ID

    Returns:
        APIKeyCreateResponse: New API key
    """
    key, key_obj = api_key_manager.generate_key(
        user_id=user_id,
        name=request.name,
        scopes=request.scopes,
        expires_in_days=request.expires_in_days
    )

    audit_logger.log(user_id, "create_api_key", "api_key", key_obj.key_id, "success")

    return APIKeyCreateResponse(
        key_id=key_obj.key_id,
        key=key,
        name=key_obj.name,
        scopes=key_obj.scopes,
        created_at=key_obj.created_at.isoformat(),
        expires_at=key_obj.expires_at.isoformat() if key_obj.expires_at else None
    )


@router.get("/api-keys")
async def list_api_keys(
    user_id: str = Depends(require_permission("security:manage_keys_self"))
) -> List[Dict]:
    """
    List API keys for current user.

    Args:
        user_id: Current user ID

    Returns:
        List[Dict]: API keys (without actual key values)
    """
    keys = [
        {
            "key_id": key.key_id,
            "name": key.name,
            "scopes": key.scopes,
            "created_at": key.created_at.isoformat(),
            "expires_at": key.expires_at.isoformat() if key.expires_at else None,
            "last_used": key.last_used.isoformat() if key.last_used else None,
            "is_active": key.is_active
        }
        for key in api_key_manager.api_keys.values()
        if key.user_id == user_id
    ]

    return keys


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    user_id: str = Depends(require_permission("security:manage_keys_self"))
) -> Dict:
    """
    Revoke API key.

    Args:
        key_id: API key ID to revoke
        user_id: Current user ID

    Returns:
        Dict: Success message
    """
    api_key_manager.revoke_key(key_id)
    audit_logger.log(user_id, "revoke_api_key", "api_key", key_id, "success")

    return {"message": "API key revoked"}


# ============================================================================
# RBAC Endpoints
# ============================================================================

@router.post("/users/{user_id}/roles/{role_id}")
async def assign_role(
    user_id: str,
    role_id: str,
    admin_user: str = Depends(require_permission("users:assign_roles"))
) -> Dict:
    """
    Assign role to user.

    Args:
        user_id: Target user ID
        role_id: Role ID to assign
        admin_user: Admin user making the change

    Returns:
        Dict: Success message
    """
    success = rbac.assign_role(user_id, role_id)

    if not success:
        raise HTTPException(status_code=400, detail="Invalid user or role")

    audit_logger.log(admin_user, "assign_role", "user", user_id,
                    "success", {"role_id": role_id})

    return {"message": f"Role '{role_id}' assigned to user '{user_id}'"}


@router.delete("/users/{user_id}/roles/{role_id}")
async def revoke_role(
    user_id: str,
    role_id: str,
    admin_user: str = Depends(require_permission("users:assign_roles"))
) -> Dict:
    """
    Revoke role from user.

    Args:
        user_id: Target user ID
        role_id: Role ID to revoke
        admin_user: Admin user making the change

    Returns:
        Dict: Success message
    """
    success = rbac.revoke_role(user_id, role_id)

    if not success:
        raise HTTPException(status_code=400, detail="Invalid user or role")

    audit_logger.log(admin_user, "revoke_role", "user", user_id,
                    "success", {"role_id": role_id})

    return {"message": f"Role '{role_id}' revoked from user '{user_id}'"}


@router.get("/users/{user_id}/permissions")
async def get_user_permissions(
    user_id: str,
    current_user: str = Depends(get_current_user)
) -> Dict:
    """
    Get user's permissions.

    Args:
        user_id: Target user ID
        current_user: Current user ID

    Returns:
        Dict: User permissions
    """
    # Users can view their own permissions, admins can view any
    if user_id != current_user:
        rbac.require_permission(current_user, "users:read")

    permissions = rbac.get_user_permissions(user_id)

    return {
        "user_id": user_id,
        "permissions": sorted(list(permissions)),
        "permission_count": len(permissions)
    }


@router.post("/permissions/check", response_model=PermissionCheckResponse)
async def check_permission(
    request: PermissionCheckRequest,
    user_id: str = Depends(get_current_user)
) -> PermissionCheckResponse:
    """
    Check if current user has specific permission.

    Args:
        request: Permission check request
        user_id: Current user ID

    Returns:
        PermissionCheckResponse: Permission check result
    """
    has_permission = rbac.check_permission(user_id, request.permission)

    return PermissionCheckResponse(
        permission=request.permission,
        granted=has_permission
    )


# ============================================================================
# Audit Log Endpoints
# ============================================================================

@router.get("/audit-log")
async def get_audit_log(
    user_id: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    days: int = Query(90, ge=1, le=365),
    admin_user: str = Depends(require_permission("security:view_audit_log"))
) -> List[AuditLogResponse]:
    """
    Get audit log with optional filtering.

    Args:
        user_id: Filter by user (optional)
        resource_type: Filter by resource type (optional)
        days: Look back days (default 90, max 365)
        admin_user: Admin user making the request

    Returns:
        List[AuditLogResponse]: Audit logs
    """
    logs = audit_logger.get_audit_trail(user_id, resource_type, days)

    return [
        AuditLogResponse(
            log_id=log.log_id,
            timestamp=log.timestamp.isoformat(),
            user_id=log.user_id,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            status=log.status,
            details=log.details
        )
        for log in logs
    ]


@router.get("/audit-log/{log_id}")
async def get_audit_log_entry(
    log_id: str,
    admin_user: str = Depends(require_permission("security:view_audit_log"))
) -> AuditLogResponse:
    """
    Get specific audit log entry.

    Args:
        log_id: Audit log ID
        admin_user: Admin user making the request

    Returns:
        AuditLogResponse: Audit log entry
    """
    for log in audit_logger.logs:
        if log.log_id == log_id:
            return AuditLogResponse(
                log_id=log.log_id,
                timestamp=log.timestamp.isoformat(),
                user_id=log.user_id,
                action=log.action,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                status=log.status,
                details=log.details
            )

    raise HTTPException(status_code=404, detail="Audit log entry not found")
