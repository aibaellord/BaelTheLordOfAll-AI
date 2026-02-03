#!/usr/bin/env python3
"""
BAEL - Security Module
Comprehensive security framework for AI agent operations.

This module implements multi-layered security for
protecting agent operations, data, and communications.

Features:
- Authentication and authorization
- Role-based access control (RBAC)
- API key management
- Rate limiting
- Input sanitization
- Audit logging
- Encryption utilities
- Token management
- Security policies
- Threat detection
- Access control lists
- Security monitoring
"""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, Flag, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class Permission(Flag):
    """System permissions."""
    NONE = 0
    READ = auto()
    WRITE = auto()
    EXECUTE = auto()
    DELETE = auto()
    ADMIN = auto()

    # Combined permissions
    READ_WRITE = READ | WRITE
    FULL = READ | WRITE | EXECUTE | DELETE
    ALL = READ | WRITE | EXECUTE | DELETE | ADMIN


class Role(Enum):
    """System roles."""
    GUEST = "guest"
    USER = "user"
    OPERATOR = "operator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"
    AGENT = "agent"
    ENGINE = "engine"
    COUNCIL = "council"


class TokenType(Enum):
    """Types of security tokens."""
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"
    SESSION = "session"
    TEMPORARY = "temporary"


class ThreatLevel(Enum):
    """Threat severity levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class AuditAction(Enum):
    """Audit log actions."""
    LOGIN = "login"
    LOGOUT = "logout"
    ACCESS = "access"
    MODIFY = "modify"
    DELETE = "delete"
    GRANT = "grant"
    REVOKE = "revoke"
    VIOLATION = "violation"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Identity:
    """A security identity."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    type: str = "user"  # user, agent, service
    roles: List[Role] = field(default_factory=list)
    permissions: Permission = Permission.NONE
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)


@dataclass
class Token:
    """A security token."""
    id: str = field(default_factory=lambda: str(uuid4()))
    token: str = ""
    type: TokenType = TokenType.ACCESS
    identity_id: str = ""
    scopes: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    revoked: bool = False

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if token is valid."""
        return not self.revoked and not self.is_expired


@dataclass
class AuditEntry:
    """An audit log entry."""
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    action: AuditAction = AuditAction.ACCESS
    identity_id: str = ""
    resource: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    ip_address: str = ""
    success: bool = True
    threat_level: Optional[ThreatLevel] = None


@dataclass
class SecurityPolicy:
    """A security policy."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    rules: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    priority: int = 0


@dataclass
class ThreatEvent:
    """A detected security threat."""
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    level: ThreatLevel = ThreatLevel.LOW
    type: str = ""
    description: str = ""
    source: str = ""
    identity_id: Optional[str] = None
    mitigated: bool = False


# =============================================================================
# AUTHENTICATION
# =============================================================================

class PasswordHasher:
    """Secure password hashing."""

    def __init__(self, iterations: int = 100000):
        self.iterations = iterations
        self.algorithm = 'sha256'

    def hash(self, password: str, salt: bytes = None) -> Tuple[str, str]:
        """Hash a password."""
        if salt is None:
            salt = secrets.token_bytes(32)

        key = hashlib.pbkdf2_hmac(
            self.algorithm,
            password.encode('utf-8'),
            salt,
            self.iterations
        )

        return (
            base64.b64encode(salt).decode('utf-8'),
            base64.b64encode(key).decode('utf-8')
        )

    def verify(
        self,
        password: str,
        salt: str,
        hash_value: str
    ) -> bool:
        """Verify a password."""
        salt_bytes = base64.b64decode(salt.encode('utf-8'))
        expected_hash = base64.b64decode(hash_value.encode('utf-8'))

        key = hashlib.pbkdf2_hmac(
            self.algorithm,
            password.encode('utf-8'),
            salt_bytes,
            self.iterations
        )

        return hmac.compare_digest(key, expected_hash)


class TokenManager:
    """Manages security tokens."""

    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or secrets.token_hex(32)
        self.tokens: Dict[str, Token] = {}
        self.identity_tokens: Dict[str, List[str]] = defaultdict(list)

    def generate_token(
        self,
        identity_id: str,
        token_type: TokenType = TokenType.ACCESS,
        scopes: List[str] = None,
        expires_in_seconds: int = 3600
    ) -> Token:
        """Generate a new token."""
        # Create token value
        random_bytes = secrets.token_bytes(32)
        timestamp = str(time.time()).encode('utf-8')
        token_data = random_bytes + timestamp + identity_id.encode('utf-8')

        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            token_data,
            hashlib.sha256
        ).hexdigest()

        token_value = base64.urlsafe_b64encode(
            token_data + signature.encode('utf-8')
        ).decode('utf-8')

        token = Token(
            token=token_value,
            type=token_type,
            identity_id=identity_id,
            scopes=scopes or [],
            expires_at=datetime.now() + timedelta(seconds=expires_in_seconds)
        )

        self.tokens[token.id] = token
        self.identity_tokens[identity_id].append(token.id)

        return token

    def validate_token(self, token_value: str) -> Optional[Token]:
        """Validate a token."""
        for token in self.tokens.values():
            if token.token == token_value and token.is_valid:
                return token
        return None

    def revoke_token(self, token_id: str) -> bool:
        """Revoke a token."""
        token = self.tokens.get(token_id)
        if token:
            token.revoked = True
            return True
        return False

    def revoke_identity_tokens(self, identity_id: str) -> int:
        """Revoke all tokens for an identity."""
        count = 0
        for token_id in self.identity_tokens.get(identity_id, []):
            if self.revoke_token(token_id):
                count += 1
        return count

    def cleanup_expired(self) -> int:
        """Remove expired tokens."""
        expired = [
            tid for tid, token in self.tokens.items()
            if token.is_expired
        ]
        for tid in expired:
            del self.tokens[tid]
        return len(expired)


# =============================================================================
# AUTHORIZATION
# =============================================================================

class RolePermissionMap:
    """Maps roles to permissions."""

    DEFAULT_PERMISSIONS = {
        Role.GUEST: Permission.READ,
        Role.USER: Permission.READ | Permission.WRITE,
        Role.OPERATOR: Permission.READ | Permission.WRITE | Permission.EXECUTE,
        Role.ADMIN: Permission.FULL,
        Role.SUPER_ADMIN: Permission.ALL,
        Role.AGENT: Permission.READ | Permission.WRITE | Permission.EXECUTE,
        Role.ENGINE: Permission.FULL,
        Role.COUNCIL: Permission.ALL,
    }

    def __init__(self):
        self.permissions = dict(self.DEFAULT_PERMISSIONS)

    def get_permissions(self, role: Role) -> Permission:
        """Get permissions for a role."""
        return self.permissions.get(role, Permission.NONE)

    def set_permissions(self, role: Role, permissions: Permission) -> None:
        """Set permissions for a role."""
        self.permissions[role] = permissions

    def get_combined_permissions(self, roles: List[Role]) -> Permission:
        """Get combined permissions for multiple roles."""
        combined = Permission.NONE
        for role in roles:
            combined |= self.get_permissions(role)
        return combined


class AccessController:
    """Controls access to resources."""

    def __init__(self):
        self.role_map = RolePermissionMap()
        self.resource_acls: Dict[str, Dict[str, Permission]] = {}
        self.identities: Dict[str, Identity] = {}

    def register_identity(self, identity: Identity) -> None:
        """Register an identity."""
        self.identities[identity.id] = identity

    def set_resource_acl(
        self,
        resource: str,
        identity_id: str,
        permissions: Permission
    ) -> None:
        """Set ACL for a resource."""
        if resource not in self.resource_acls:
            self.resource_acls[resource] = {}
        self.resource_acls[resource][identity_id] = permissions

    def check_permission(
        self,
        identity_id: str,
        resource: str,
        required_permission: Permission
    ) -> bool:
        """Check if identity has permission for resource."""
        identity = self.identities.get(identity_id)
        if not identity:
            return False

        # Get role-based permissions
        role_permissions = self.role_map.get_combined_permissions(identity.roles)

        # Get identity-level permissions
        identity_permissions = identity.permissions

        # Get resource-specific ACL
        resource_permissions = Permission.NONE
        if resource in self.resource_acls:
            resource_permissions = self.resource_acls[resource].get(
                identity_id, Permission.NONE
            )

        # Combine all permissions
        total_permissions = role_permissions | identity_permissions | resource_permissions

        # Check if required permission is granted
        return bool(total_permissions & required_permission)

    def grant_role(self, identity_id: str, role: Role) -> bool:
        """Grant a role to an identity."""
        identity = self.identities.get(identity_id)
        if identity and role not in identity.roles:
            identity.roles.append(role)
            return True
        return False

    def revoke_role(self, identity_id: str, role: Role) -> bool:
        """Revoke a role from an identity."""
        identity = self.identities.get(identity_id)
        if identity and role in identity.roles:
            identity.roles.remove(role)
            return True
        return False


# =============================================================================
# RATE LIMITING
# =============================================================================

class RateLimiter:
    """Rate limiting implementation."""

    def __init__(
        self,
        max_requests: int = 100,
        window_seconds: float = 60.0
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is allowed."""
        now = time.time()
        window_start = now - self.window_seconds

        # Clean old requests
        self.requests[key] = [
            t for t in self.requests[key]
            if t > window_start
        ]

        current_count = len(self.requests[key])
        remaining = max(0, self.max_requests - current_count)

        if current_count >= self.max_requests:
            # Find when oldest request expires
            oldest = min(self.requests[key]) if self.requests[key] else now
            retry_after = oldest + self.window_seconds - now

            return False, {
                "allowed": False,
                "remaining": 0,
                "retry_after": max(0, retry_after),
                "limit": self.max_requests,
                "window": self.window_seconds
            }

        # Record this request
        self.requests[key].append(now)

        return True, {
            "allowed": True,
            "remaining": remaining - 1,
            "limit": self.max_requests,
            "window": self.window_seconds
        }

    def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        if key in self.requests:
            del self.requests[key]


class AdaptiveRateLimiter(RateLimiter):
    """Adaptive rate limiting with dynamic adjustments."""

    def __init__(
        self,
        base_requests: int = 100,
        window_seconds: float = 60.0,
        burst_multiplier: float = 1.5,
        cooldown_divisor: float = 0.5
    ):
        super().__init__(base_requests, window_seconds)
        self.base_requests = base_requests
        self.burst_multiplier = burst_multiplier
        self.cooldown_divisor = cooldown_divisor
        self.trust_scores: Dict[str, float] = defaultdict(lambda: 1.0)

    def adjust_limit(self, key: str) -> int:
        """Get adjusted limit based on trust score."""
        trust = self.trust_scores[key]
        return int(self.base_requests * trust)

    def increase_trust(self, key: str, amount: float = 0.1) -> None:
        """Increase trust score."""
        self.trust_scores[key] = min(
            self.burst_multiplier,
            self.trust_scores[key] + amount
        )

    def decrease_trust(self, key: str, amount: float = 0.2) -> None:
        """Decrease trust score."""
        self.trust_scores[key] = max(
            self.cooldown_divisor,
            self.trust_scores[key] - amount
        )

    def is_allowed(self, key: str) -> Tuple[bool, Dict[str, Any]]:
        """Check with adaptive limits."""
        adjusted_limit = self.adjust_limit(key)
        original = self.max_requests
        self.max_requests = adjusted_limit

        allowed, info = super().is_allowed(key)

        self.max_requests = original
        info["adjusted_limit"] = adjusted_limit
        info["trust_score"] = self.trust_scores[key]

        return allowed, info


# =============================================================================
# INPUT SANITIZATION
# =============================================================================

class InputSanitizer:
    """Sanitizes user input."""

    def __init__(self):
        self.patterns = {
            "sql_injection": [
                r"(?i)(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|WHERE|FROM)",
                r"(?i)(--|;|'|\"|\bOR\b|\bAND\b)",
            ],
            "xss": [
                r"<script[^>]*>.*?</script>",
                r"javascript:",
                r"on\w+\s*=",
            ],
            "path_traversal": [
                r"\.\./",
                r"\.\.\\",
                r"/etc/passwd",
            ],
            "command_injection": [
                r"[;&|`$]",
                r"\$\([^)]+\)",
            ],
        }

    def detect_threats(
        self,
        input_value: str
    ) -> List[Tuple[str, str]]:
        """Detect potential threats in input."""
        threats = []

        for threat_type, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, input_value, re.IGNORECASE):
                    threats.append((threat_type, pattern))

        return threats

    def sanitize(self, input_value: str) -> str:
        """Sanitize input by removing threats."""
        sanitized = input_value

        # Remove HTML tags
        sanitized = re.sub(r'<[^>]+>', '', sanitized)

        # Escape special characters
        escape_chars = {
            '<': '&lt;',
            '>': '&gt;',
            '&': '&amp;',
            '"': '&quot;',
            "'": '&#x27;',
        }
        for char, escape in escape_chars.items():
            sanitized = sanitized.replace(char, escape)

        return sanitized

    def validate_email(self, email: str) -> bool:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def validate_identifier(self, identifier: str) -> bool:
        """Validate identifier (alphanumeric + underscore)."""
        pattern = r'^[a-zA-Z][a-zA-Z0-9_]*$'
        return bool(re.match(pattern, identifier))


# =============================================================================
# AUDIT LOGGING
# =============================================================================

class AuditLogger:
    """Audit logging for security events."""

    def __init__(self, max_entries: int = 10000):
        self.entries: List[AuditEntry] = []
        self.max_entries = max_entries

    def log(
        self,
        action: AuditAction,
        identity_id: str,
        resource: str,
        success: bool = True,
        details: Dict[str, Any] = None,
        ip_address: str = "",
        threat_level: ThreatLevel = None
    ) -> AuditEntry:
        """Log an audit entry."""
        entry = AuditEntry(
            action=action,
            identity_id=identity_id,
            resource=resource,
            success=success,
            details=details or {},
            ip_address=ip_address,
            threat_level=threat_level
        )

        self.entries.append(entry)

        # Trim if exceeds max
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]

        return entry

    def query(
        self,
        identity_id: str = None,
        action: AuditAction = None,
        resource: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 100
    ) -> List[AuditEntry]:
        """Query audit entries."""
        results = []

        for entry in reversed(self.entries):
            if identity_id and entry.identity_id != identity_id:
                continue
            if action and entry.action != action:
                continue
            if resource and entry.resource != resource:
                continue
            if start_time and entry.timestamp < start_time:
                continue
            if end_time and entry.timestamp > end_time:
                continue

            results.append(entry)

            if len(results) >= limit:
                break

        return results

    def get_violations(self, limit: int = 100) -> List[AuditEntry]:
        """Get security violations."""
        return [
            e for e in self.entries
            if e.action == AuditAction.VIOLATION or not e.success
        ][-limit:]

    def get_summary(self) -> Dict[str, Any]:
        """Get audit summary."""
        by_action = defaultdict(int)
        by_identity = defaultdict(int)
        violations = 0

        for entry in self.entries:
            by_action[entry.action.value] += 1
            by_identity[entry.identity_id] += 1
            if not entry.success or entry.action == AuditAction.VIOLATION:
                violations += 1

        return {
            "total_entries": len(self.entries),
            "by_action": dict(by_action),
            "unique_identities": len(by_identity),
            "violations": violations
        }


# =============================================================================
# THREAT DETECTION
# =============================================================================

class ThreatDetector:
    """Detects security threats."""

    def __init__(self):
        self.events: List[ThreatEvent] = []
        self.blocked_sources: Set[str] = set()
        self.suspicious_patterns: Dict[str, int] = defaultdict(int)

    def analyze_request(
        self,
        source: str,
        data: Dict[str, Any]
    ) -> Optional[ThreatEvent]:
        """Analyze a request for threats."""
        # Check if source is blocked
        if source in self.blocked_sources:
            return ThreatEvent(
                level=ThreatLevel.HIGH,
                type="blocked_source",
                description=f"Request from blocked source: {source}",
                source=source
            )

        # Check for suspicious patterns
        threats = []

        sanitizer = InputSanitizer()
        for key, value in data.items():
            if isinstance(value, str):
                detected = sanitizer.detect_threats(value)
                if detected:
                    threats.extend(detected)

        if threats:
            # Increment suspicious pattern count
            self.suspicious_patterns[source] += len(threats)

            # Block if too many patterns
            if self.suspicious_patterns[source] > 10:
                self.blocked_sources.add(source)

            level = ThreatLevel.LOW
            if len(threats) > 3:
                level = ThreatLevel.MEDIUM
            if len(threats) > 5:
                level = ThreatLevel.HIGH

            event = ThreatEvent(
                level=level,
                type="malicious_input",
                description=f"Detected {len(threats)} suspicious patterns",
                source=source
            )
            self.events.append(event)
            return event

        return None

    def detect_brute_force(
        self,
        identity_id: str,
        failed_attempts: int,
        threshold: int = 5
    ) -> Optional[ThreatEvent]:
        """Detect brute force attacks."""
        if failed_attempts >= threshold:
            event = ThreatEvent(
                level=ThreatLevel.HIGH,
                type="brute_force",
                description=f"Brute force detected: {failed_attempts} failed attempts",
                identity_id=identity_id
            )
            self.events.append(event)
            return event
        return None

    def unblock_source(self, source: str) -> bool:
        """Unblock a source."""
        if source in self.blocked_sources:
            self.blocked_sources.discard(source)
            self.suspicious_patterns[source] = 0
            return True
        return False

    def get_active_threats(self) -> List[ThreatEvent]:
        """Get active (unmitigated) threats."""
        return [e for e in self.events if not e.mitigated]


# =============================================================================
# SECURITY MODULE
# =============================================================================

class SecurityModule:
    """
    The master security module for BAEL.

    Provides comprehensive security with authentication,
    authorization, rate limiting, and threat detection.
    """

    def __init__(self, secret_key: str = None):
        self.hasher = PasswordHasher()
        self.token_manager = TokenManager(secret_key)
        self.access_controller = AccessController()
        self.rate_limiter = AdaptiveRateLimiter()
        self.sanitizer = InputSanitizer()
        self.audit_logger = AuditLogger()
        self.threat_detector = ThreatDetector()

        # Credentials store (in production, use secure database)
        self.credentials: Dict[str, Dict[str, str]] = {}

    def register_identity(
        self,
        name: str,
        password: str,
        identity_type: str = "user",
        roles: List[Role] = None
    ) -> Identity:
        """Register a new identity."""
        identity = Identity(
            name=name,
            type=identity_type,
            roles=roles or [Role.USER]
        )

        # Store password hash
        salt, hash_value = self.hasher.hash(password)
        self.credentials[identity.id] = {
            "salt": salt,
            "hash": hash_value
        }

        self.access_controller.register_identity(identity)

        self.audit_logger.log(
            AuditAction.ACCESS,
            identity.id,
            "identity_registration",
            details={"name": name, "type": identity_type}
        )

        return identity

    def authenticate(
        self,
        identity_id: str,
        password: str,
        source_ip: str = ""
    ) -> Optional[Token]:
        """Authenticate an identity."""
        creds = self.credentials.get(identity_id)

        if not creds:
            self.audit_logger.log(
                AuditAction.LOGIN,
                identity_id,
                "authentication",
                success=False,
                ip_address=source_ip,
                details={"reason": "identity_not_found"}
            )
            return None

        if not self.hasher.verify(password, creds["salt"], creds["hash"]):
            self.audit_logger.log(
                AuditAction.LOGIN,
                identity_id,
                "authentication",
                success=False,
                ip_address=source_ip,
                details={"reason": "invalid_password"}
            )

            # Check for brute force
            self.threat_detector.detect_brute_force(identity_id, 1)

            return None

        # Generate access token
        token = self.token_manager.generate_token(
            identity_id,
            TokenType.ACCESS,
            scopes=["default"]
        )

        # Update identity
        identity = self.access_controller.identities.get(identity_id)
        if identity:
            identity.last_active = datetime.now()

        self.audit_logger.log(
            AuditAction.LOGIN,
            identity_id,
            "authentication",
            success=True,
            ip_address=source_ip
        )

        return token

    def authorize(
        self,
        token_value: str,
        resource: str,
        permission: Permission,
        source_ip: str = ""
    ) -> bool:
        """Authorize access to a resource."""
        # Check rate limit
        allowed, info = self.rate_limiter.is_allowed(source_ip or "default")
        if not allowed:
            self.audit_logger.log(
                AuditAction.ACCESS,
                "",
                resource,
                success=False,
                ip_address=source_ip,
                details={"reason": "rate_limited", **info}
            )
            return False

        # Validate token
        token = self.token_manager.validate_token(token_value)
        if not token:
            self.audit_logger.log(
                AuditAction.ACCESS,
                "",
                resource,
                success=False,
                ip_address=source_ip,
                details={"reason": "invalid_token"}
            )
            return False

        # Check permission
        has_permission = self.access_controller.check_permission(
            token.identity_id,
            resource,
            permission
        )

        self.audit_logger.log(
            AuditAction.ACCESS,
            token.identity_id,
            resource,
            success=has_permission,
            ip_address=source_ip,
            details={"permission": permission.name}
        )

        if has_permission:
            self.rate_limiter.increase_trust(source_ip or "default")
        else:
            self.rate_limiter.decrease_trust(source_ip or "default")

        return has_permission

    def sanitize_input(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize input data."""
        sanitized = {}

        for key, value in data.items():
            if isinstance(value, str):
                # Detect threats
                threats = self.sanitizer.detect_threats(value)
                if threats:
                    logger.warning(f"Threats detected in input '{key}': {threats}")

                sanitized[key] = self.sanitizer.sanitize(value)
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_input(value)
            else:
                sanitized[key] = value

        return sanitized

    def analyze_request(
        self,
        source: str,
        data: Dict[str, Any],
        identity_id: str = None
    ) -> Tuple[bool, Optional[ThreatEvent]]:
        """Analyze a request for security threats."""
        threat = self.threat_detector.analyze_request(source, data)

        if threat:
            self.audit_logger.log(
                AuditAction.VIOLATION,
                identity_id or "",
                "request_analysis",
                success=False,
                ip_address=source,
                threat_level=threat.level,
                details={"threat_type": threat.type}
            )
            return False, threat

        return True, None

    def revoke_access(
        self,
        identity_id: str,
        reason: str = ""
    ) -> int:
        """Revoke all access for an identity."""
        count = self.token_manager.revoke_identity_tokens(identity_id)

        self.audit_logger.log(
            AuditAction.REVOKE,
            identity_id,
            "access_revocation",
            details={"tokens_revoked": count, "reason": reason}
        )

        return count

    def get_security_report(self) -> Dict[str, Any]:
        """Get security status report."""
        return {
            "identities": len(self.access_controller.identities),
            "active_tokens": sum(
                1 for t in self.token_manager.tokens.values()
                if t.is_valid
            ),
            "blocked_sources": len(self.threat_detector.blocked_sources),
            "active_threats": len(self.threat_detector.get_active_threats()),
            "audit_summary": self.audit_logger.get_summary()
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get security statistics."""
        return {
            "identities_registered": len(self.access_controller.identities),
            "tokens_issued": len(self.token_manager.tokens),
            "resource_acls": len(self.access_controller.resource_acls),
            "audit_entries": len(self.audit_logger.entries),
            "threat_events": len(self.threat_detector.events),
            "blocked_sources": len(self.threat_detector.blocked_sources)
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Security Module."""
    print("=" * 70)
    print("BAEL - SECURITY MODULE DEMO")
    print("Comprehensive Security Framework")
    print("=" * 70)
    print()

    # Create security module
    security = SecurityModule(secret_key="demo-secret-key-12345")

    # 1. Identity Registration
    print("1. IDENTITY REGISTRATION:")
    print("-" * 40)

    admin = security.register_identity(
        "admin_user",
        "secure_password_123",
        "user",
        [Role.ADMIN]
    )
    print(f"   Registered: {admin.name} (ID: {admin.id[:8]}...)")
    print(f"   Roles: {[r.value for r in admin.roles]}")

    agent = security.register_identity(
        "agent_001",
        "agent_key_456",
        "agent",
        [Role.AGENT]
    )
    print(f"   Registered: {agent.name} (ID: {agent.id[:8]}...)")
    print()

    # 2. Authentication
    print("2. AUTHENTICATION:")
    print("-" * 40)

    # Successful auth
    token = security.authenticate(admin.id, "secure_password_123", "192.168.1.1")
    if token:
        print(f"   Success: Token issued (expires: {token.expires_at})")

    # Failed auth
    bad_token = security.authenticate(admin.id, "wrong_password", "192.168.1.1")
    if not bad_token:
        print("   Failed: Invalid password correctly rejected")
    print()

    # 3. Authorization
    print("3. AUTHORIZATION:")
    print("-" * 40)

    # Set resource ACL
    security.access_controller.set_resource_acl(
        "/api/admin",
        admin.id,
        Permission.FULL
    )

    # Check permissions
    can_read = security.authorize(token.token, "/api/data", Permission.READ)
    print(f"   Admin can read /api/data: {can_read}")

    can_admin = security.authorize(token.token, "/api/admin", Permission.ADMIN)
    print(f"   Admin can admin /api/admin: {can_admin}")
    print()

    # 4. Rate Limiting
    print("4. RATE LIMITING:")
    print("-" * 40)

    test_ip = "10.0.0.1"
    for i in range(5):
        allowed, info = security.rate_limiter.is_allowed(test_ip)
        if i < 3:
            print(f"   Request {i+1}: Allowed={allowed}, Remaining={info['remaining']}")

    print(f"   Trust score: {info.get('trust_score', 1.0):.2f}")
    print()

    # 5. Input Sanitization
    print("5. INPUT SANITIZATION:")
    print("-" * 40)

    malicious_input = {
        "name": "<script>alert('xss')</script>",
        "query": "SELECT * FROM users; DROP TABLE users;--",
        "safe_field": "Normal text content"
    }

    sanitized = security.sanitize_input(malicious_input)
    print("   Before sanitization:")
    for k, v in malicious_input.items():
        print(f"     {k}: {v[:40]}...")
    print("   After sanitization:")
    for k, v in sanitized.items():
        print(f"     {k}: {v[:40]}...")
    print()

    # 6. Threat Detection
    print("6. THREAT DETECTION:")
    print("-" * 40)

    is_safe, threat = security.analyze_request(
        "suspicious_source",
        {"data": "normal request"}
    )
    print(f"   Normal request safe: {is_safe}")

    is_safe2, threat2 = security.analyze_request(
        "malicious_source",
        {"cmd": "; rm -rf /"}
    )
    print(f"   Malicious request safe: {is_safe2}")
    if threat2:
        print(f"   Threat detected: {threat2.type} (Level: {threat2.level.name})")
    print()

    # 7. Audit Logging
    print("7. AUDIT LOGGING:")
    print("-" * 40)

    # Log some events
    security.audit_logger.log(
        AuditAction.MODIFY,
        admin.id,
        "/api/settings",
        details={"setting": "updated"}
    )

    summary = security.audit_logger.get_summary()
    print(f"   Total entries: {summary['total_entries']}")
    print(f"   Violations: {summary['violations']}")
    print(f"   Actions logged: {list(summary['by_action'].keys())}")
    print()

    # 8. Access Revocation
    print("8. ACCESS REVOCATION:")
    print("-" * 40)

    revoked_count = security.revoke_access(admin.id, "demo revocation")
    print(f"   Revoked {revoked_count} tokens for admin")

    # Verify token no longer valid
    is_valid = security.token_manager.validate_token(token.token)
    print(f"   Token still valid: {is_valid is not None}")
    print()

    # 9. Security Report
    print("9. SECURITY REPORT:")
    print("-" * 40)

    report = security.get_security_report()
    print(f"   Identities: {report['identities']}")
    print(f"   Active Tokens: {report['active_tokens']}")
    print(f"   Blocked Sources: {report['blocked_sources']}")
    print(f"   Active Threats: {report['active_threats']}")
    print()

    # 10. Statistics
    print("10. SECURITY STATISTICS:")
    print("-" * 40)

    stats = security.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Security Module Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
