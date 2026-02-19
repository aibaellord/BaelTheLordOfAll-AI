"""
BAEL Auth Engine
================

Authentication and authorization with JWT, OAuth, RBAC.

"Ba'el guards all gates with supreme authority." — Ba'el
"""

from core.auth_engine.auth_engine import (
    # Enums
    AuthMethod,
    TokenType,
    PermissionAction,
    UserStatus,

    # Data structures
    User,
    Role,
    Permission,
    Token,
    Session,
    AuthConfig,
    OAuthProvider,

    # Classes
    AuthEngine,
    TokenManager,
    SessionManager,
    PasswordManager,
    RBACManager,
    OAuthManager,
    MFAManager,

    # Instance
    auth_engine
)

__all__ = [
    # Enums
    'AuthMethod',
    'TokenType',
    'PermissionAction',
    'UserStatus',

    # Data structures
    'User',
    'Role',
    'Permission',
    'Token',
    'Session',
    'AuthConfig',
    'OAuthProvider',

    # Classes
    'AuthEngine',
    'TokenManager',
    'SessionManager',
    'PasswordManager',
    'RBACManager',
    'OAuthManager',
    'MFAManager',

    # Instance
    'auth_engine'
]
