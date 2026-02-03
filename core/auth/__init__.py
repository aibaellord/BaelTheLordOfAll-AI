"""
BAEL - API Authentication Middleware
JWT-based authentication for the BAEL API.
"""

import hashlib
import logging
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

logger = logging.getLogger("BAEL.Auth")


@dataclass
class User:
    """API user."""
    id: str
    username: str
    roles: list
    created_at: datetime
    api_key_hash: Optional[str] = None


@dataclass
class TokenPayload:
    """JWT token payload."""
    user_id: str
    username: str
    roles: list
    exp: datetime
    iat: datetime


class AuthManager:
    """
    Authentication manager for BAEL API.

    Supports:
    - API key authentication
    - JWT tokens
    - Role-based access control
    """

    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or os.getenv("BAEL_JWT_SECRET", secrets.token_hex(32))
        self._api_keys: Dict[str, User] = {}
        self._tokens: Dict[str, TokenPayload] = {}

    def generate_api_key(self, user: User) -> str:
        """Generate an API key for a user."""
        key = f"bael_{secrets.token_hex(24)}"
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        user.api_key_hash = key_hash
        self._api_keys[key_hash] = user
        logger.info(f"Generated API key for user: {user.username}")
        return key

    def validate_api_key(self, api_key: str) -> Optional[User]:
        """Validate an API key and return the user."""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        return self._api_keys.get(key_hash)

    def create_token(
        self,
        user: User,
        expires_in_hours: int = 24
    ) -> str:
        """Create a JWT-like token for a user."""
        now = datetime.utcnow()
        payload = TokenPayload(
            user_id=user.id,
            username=user.username,
            roles=user.roles,
            exp=now + timedelta(hours=expires_in_hours),
            iat=now
        )

        # Simple token generation (in production, use proper JWT)
        token_data = f"{payload.user_id}:{payload.exp.timestamp()}:{secrets.token_hex(16)}"
        token = hashlib.sha256(f"{token_data}{self.secret_key}".encode()).hexdigest()

        self._tokens[token] = payload
        return token

    def validate_token(self, token: str) -> Optional[TokenPayload]:
        """Validate a token and return the payload."""
        payload = self._tokens.get(token)
        if not payload:
            return None

        if datetime.utcnow() > payload.exp:
            del self._tokens[token]
            return None

        return payload

    def revoke_token(self, token: str) -> bool:
        """Revoke a token."""
        if token in self._tokens:
            del self._tokens[token]
            return True
        return False

    def has_role(self, payload: TokenPayload, role: str) -> bool:
        """Check if user has a specific role."""
        return role in payload.roles or "admin" in payload.roles

    def require_auth(self, auth_header: Optional[str]) -> Optional[User]:
        """
        Validate authorization header.
        Supports: 'Bearer <token>' or 'ApiKey <key>'
        """
        if not auth_header:
            return None

        parts = auth_header.split(" ", 1)
        if len(parts) != 2:
            return None

        auth_type, credential = parts

        if auth_type.lower() == "bearer":
            payload = self.validate_token(credential)
            if payload:
                return User(
                    id=payload.user_id,
                    username=payload.username,
                    roles=payload.roles,
                    created_at=payload.iat
                )
        elif auth_type.lower() == "apikey":
            return self.validate_api_key(credential)

        return None


# FastAPI middleware helper
def create_auth_dependency(auth_manager: AuthManager):
    """Create FastAPI authentication dependency."""

    async def verify_auth(authorization: Optional[str] = None):
        """Verify authentication."""
        if not authorization:
            return None

        user = auth_manager.require_auth(authorization)
        if not user:
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="Invalid authentication")

        return user

    return verify_auth


# Global auth manager
auth_manager = AuthManager()


__all__ = [
    "User",
    "TokenPayload",
    "AuthManager",
    "auth_manager",
    "create_auth_dependency"
]
