"""
BAEL - Security Module
Comprehensive security for the agent system.

Features:
- Input validation & sanitization
- Rate limiting
- Authentication & authorization
- Audit logging
- Threat detection
- Sandboxed execution
"""

import asyncio
import hashlib
import hmac
import json
import logging
import re
import secrets
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.Security")


# =============================================================================
# TYPES & ENUMS
# =============================================================================

class ThreatLevel(Enum):
    """Threat severity levels."""
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class AuthLevel(Enum):
    """Authorization levels."""
    GUEST = 0
    USER = 1
    TRUSTED = 2
    ADMIN = 3
    SYSTEM = 4


class ViolationType(Enum):
    """Types of security violations."""
    INJECTION = "injection"
    XSS = "xss"
    PATH_TRAVERSAL = "path_traversal"
    RATE_LIMIT = "rate_limit"
    AUTH_FAILURE = "auth_failure"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    MALICIOUS_CODE = "malicious_code"
    DATA_EXFILTRATION = "data_exfiltration"


@dataclass
class SecurityEvent:
    """A security event."""
    id: str
    event_type: ViolationType
    threat_level: ThreatLevel
    description: str
    source_ip: Optional[str] = None
    user_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    handled: bool = False


@dataclass
class User:
    """User entity."""
    id: str
    username: str
    auth_level: AuthLevel
    api_key_hash: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_active: Optional[datetime] = None
    permissions: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    burst_limit: int = 10


# =============================================================================
# INPUT VALIDATOR
# =============================================================================

class InputValidator:
    """Validates and sanitizes inputs."""

    def __init__(self):
        # Dangerous patterns
        self.sql_injection_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER)\b)",
            r"(--|\#|\/\*|\*\/)",
            r"(\bOR\b\s+\d+\s*=\s*\d+)",
            r"(\bAND\b\s+\d+\s*=\s*\d+)",
            r"(;.*--)",
        ]

        self.xss_patterns = [
            r"(<script[^>]*>)",
            r"(javascript:)",
            r"(on\w+\s*=)",
            r"(<iframe)",
            r"(<object)",
            r"(<embed)",
        ]

        self.path_traversal_patterns = [
            r"(\.\./)",
            r"(\.\.\\)",
            r"(%2e%2e%2f)",
            r"(%2e%2e/)",
            r"(\.\.%2f)",
        ]

        self.command_injection_patterns = [
            r"(;\s*\w+)",
            r"(\|\s*\w+)",
            r"(`[^`]+`)",
            r"(\$\([^)]+\))",
            r"(&&\s*\w+)",
        ]

        # Compile patterns
        self._compiled = {}
        for name, patterns in [
            ('sql', self.sql_injection_patterns),
            ('xss', self.xss_patterns),
            ('path', self.path_traversal_patterns),
            ('cmd', self.command_injection_patterns),
        ]:
            self._compiled[name] = [re.compile(p, re.IGNORECASE) for p in patterns]

    def validate(self, input_text: str) -> Tuple[bool, List[ViolationType], str]:
        """Validate input for security issues."""
        violations = []

        # Check SQL injection
        for pattern in self._compiled['sql']:
            if pattern.search(input_text):
                violations.append(ViolationType.INJECTION)
                break

        # Check XSS
        for pattern in self._compiled['xss']:
            if pattern.search(input_text):
                violations.append(ViolationType.XSS)
                break

        # Check path traversal
        for pattern in self._compiled['path']:
            if pattern.search(input_text):
                violations.append(ViolationType.PATH_TRAVERSAL)
                break

        # Check command injection
        for pattern in self._compiled['cmd']:
            if pattern.search(input_text):
                violations.append(ViolationType.MALICIOUS_CODE)
                break

        is_valid = len(violations) == 0
        sanitized = self.sanitize(input_text) if not is_valid else input_text

        return is_valid, violations, sanitized

    def sanitize(self, input_text: str) -> str:
        """Sanitize potentially dangerous input."""
        result = input_text

        # HTML entity encoding for XSS
        result = result.replace('<', '&lt;').replace('>', '&gt;')
        result = result.replace('"', '&quot;').replace("'", '&#x27;')

        # Remove path traversal
        result = re.sub(r'\.\.[/\\]', '', result)

        # Remove command injection
        result = re.sub(r'[;|`$]', '', result)

        return result

    def validate_path(self, path: str, allowed_roots: List[str]) -> bool:
        """Validate a file path."""
        import os

        # Normalize path
        normalized = os.path.normpath(os.path.abspath(path))

        # Check against allowed roots
        for root in allowed_roots:
            root_normalized = os.path.normpath(os.path.abspath(root))
            if normalized.startswith(root_normalized):
                return True

        return False

    def validate_code(self, code: str, language: str = "python") -> Tuple[bool, List[str]]:
        """Validate code for dangerous operations."""
        issues = []

        if language == "python":
            # Check for dangerous imports
            dangerous_imports = ['os', 'subprocess', 'sys', 'socket', 'ctypes']
            for imp in dangerous_imports:
                if re.search(rf'\bimport\s+{imp}\b', code):
                    issues.append(f"Potentially dangerous import: {imp}")
                if re.search(rf'\bfrom\s+{imp}\b', code):
                    issues.append(f"Potentially dangerous import: {imp}")

            # Check for eval/exec
            if re.search(r'\b(eval|exec|compile)\s*\(', code):
                issues.append("Dynamic code execution detected")

            # Check for file operations
            if re.search(r'\bopen\s*\([^)]+,\s*["\']w', code):
                issues.append("File write operation detected")

        return len(issues) == 0, issues


# =============================================================================
# RATE LIMITER
# =============================================================================

class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self._buckets: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def check(self, identifier: str) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is allowed."""
        async with self._locks[identifier]:
            now = time.time()
            bucket = self._get_or_create_bucket(identifier, now)

            # Check minute limit
            if bucket['minute_count'] >= self.config.requests_per_minute:
                return False, {
                    "error": "rate_limit_exceeded",
                    "limit": "minute",
                    "retry_after": 60 - (now - bucket['minute_start'])
                }

            # Check hour limit
            if bucket['hour_count'] >= self.config.requests_per_hour:
                return False, {
                    "error": "rate_limit_exceeded",
                    "limit": "hour",
                    "retry_after": 3600 - (now - bucket['hour_start'])
                }

            # Check day limit
            if bucket['day_count'] >= self.config.requests_per_day:
                return False, {
                    "error": "rate_limit_exceeded",
                    "limit": "day",
                    "retry_after": 86400 - (now - bucket['day_start'])
                }

            # Update counts
            bucket['minute_count'] += 1
            bucket['hour_count'] += 1
            bucket['day_count'] += 1

            return True, {
                "remaining_minute": self.config.requests_per_minute - bucket['minute_count'],
                "remaining_hour": self.config.requests_per_hour - bucket['hour_count'],
                "remaining_day": self.config.requests_per_day - bucket['day_count']
            }

    def _get_or_create_bucket(self, identifier: str, now: float) -> Dict[str, Any]:
        """Get or create a rate limit bucket."""
        if identifier not in self._buckets:
            self._buckets[identifier] = {
                'minute_count': 0,
                'minute_start': now,
                'hour_count': 0,
                'hour_start': now,
                'day_count': 0,
                'day_start': now
            }
        else:
            bucket = self._buckets[identifier]

            # Reset minute counter if needed
            if now - bucket['minute_start'] >= 60:
                bucket['minute_count'] = 0
                bucket['minute_start'] = now

            # Reset hour counter if needed
            if now - bucket['hour_start'] >= 3600:
                bucket['hour_count'] = 0
                bucket['hour_start'] = now

            # Reset day counter if needed
            if now - bucket['day_start'] >= 86400:
                bucket['day_count'] = 0
                bucket['day_start'] = now

        return self._buckets[identifier]


# =============================================================================
# AUTHENTICATOR
# =============================================================================

class Authenticator:
    """Handles authentication."""

    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or secrets.token_hex(32)
        self._users: Dict[str, User] = {}
        self._tokens: Dict[str, Tuple[str, datetime]] = {}  # token -> (user_id, expiry)
        self._api_keys: Dict[str, str] = {}  # key_hash -> user_id

    def create_user(self, username: str, auth_level: AuthLevel = AuthLevel.USER) -> User:
        """Create a new user."""
        user_id = secrets.token_hex(16)
        user = User(
            id=user_id,
            username=username,
            auth_level=auth_level
        )
        self._users[user_id] = user
        logger.info(f"Created user: {username} (level: {auth_level.name})")
        return user

    def generate_api_key(self, user_id: str) -> Optional[str]:
        """Generate API key for user."""
        if user_id not in self._users:
            return None

        api_key = f"bael_{secrets.token_urlsafe(32)}"
        key_hash = self._hash_key(api_key)

        self._users[user_id].api_key_hash = key_hash
        self._api_keys[key_hash] = user_id

        return api_key

    def authenticate_api_key(self, api_key: str) -> Optional[User]:
        """Authenticate using API key."""
        key_hash = self._hash_key(api_key)

        if key_hash in self._api_keys:
            user_id = self._api_keys[key_hash]
            user = self._users.get(user_id)
            if user:
                user.last_active = datetime.now()
                return user

        return None

    def generate_token(self, user_id: str, expires_in: int = 3600) -> Optional[str]:
        """Generate session token."""
        if user_id not in self._users:
            return None

        token = secrets.token_urlsafe(32)
        expiry = datetime.now() + timedelta(seconds=expires_in)
        self._tokens[token] = (user_id, expiry)

        return token

    def validate_token(self, token: str) -> Optional[User]:
        """Validate session token."""
        if token not in self._tokens:
            return None

        user_id, expiry = self._tokens[token]

        if datetime.now() > expiry:
            del self._tokens[token]
            return None

        user = self._users.get(user_id)
        if user:
            user.last_active = datetime.now()

        return user

    def revoke_token(self, token: str) -> bool:
        """Revoke a session token."""
        if token in self._tokens:
            del self._tokens[token]
            return True
        return False

    def _hash_key(self, key: str) -> str:
        """Hash an API key."""
        return hashlib.sha256(
            (key + self.secret_key).encode()
        ).hexdigest()


# =============================================================================
# AUTHORIZER
# =============================================================================

class Authorizer:
    """Handles authorization."""

    def __init__(self):
        # Define permission requirements for operations
        self.operation_requirements: Dict[str, AuthLevel] = {
            # Read operations
            "read:public": AuthLevel.GUEST,
            "read:memory": AuthLevel.USER,
            "read:history": AuthLevel.USER,

            # Write operations
            "write:memory": AuthLevel.USER,
            "write:files": AuthLevel.TRUSTED,

            # Execute operations
            "execute:code": AuthLevel.TRUSTED,
            "execute:tools": AuthLevel.USER,
            "execute:browser": AuthLevel.TRUSTED,

            # Admin operations
            "admin:users": AuthLevel.ADMIN,
            "admin:config": AuthLevel.ADMIN,
            "admin:system": AuthLevel.SYSTEM,

            # Dangerous operations
            "system:shell": AuthLevel.SYSTEM,
            "system:network": AuthLevel.SYSTEM,
        }

    def check(self, user: User, operation: str) -> bool:
        """Check if user is authorized for operation."""
        required_level = self.operation_requirements.get(operation, AuthLevel.ADMIN)

        # Check auth level
        if user.auth_level.value >= required_level.value:
            return True

        # Check explicit permissions
        if operation in user.permissions:
            return True

        return False

    def require(self, operation: str) -> Callable:
        """Decorator to require authorization."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract user from kwargs or first arg
                user = kwargs.get('user') or (args[0] if args else None)

                if not isinstance(user, User):
                    raise PermissionError("No user context")

                if not self.check(user, operation):
                    raise PermissionError(f"Unauthorized for: {operation}")

                return await func(*args, **kwargs)
            return wrapper
        return decorator


# =============================================================================
# AUDIT LOGGER
# =============================================================================

class AuditLogger:
    """Security audit logging."""

    def __init__(self, log_file: Optional[str] = None):
        self.log_file = log_file
        self._events: List[SecurityEvent] = []
        self._event_handlers: List[Callable[[SecurityEvent], None]] = []

    def log(self, event: SecurityEvent) -> None:
        """Log a security event."""
        self._events.append(event)

        # Log to file if configured
        if self.log_file:
            self._write_to_file(event)

        # Notify handlers
        for handler in self._event_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Event handler error: {e}")

        # Log based on threat level
        if event.threat_level == ThreatLevel.CRITICAL:
            logger.critical(f"SECURITY: {event.event_type.value} - {event.description}")
        elif event.threat_level == ThreatLevel.HIGH:
            logger.error(f"SECURITY: {event.event_type.value} - {event.description}")
        elif event.threat_level == ThreatLevel.MEDIUM:
            logger.warning(f"SECURITY: {event.event_type.value} - {event.description}")
        else:
            logger.info(f"SECURITY: {event.event_type.value} - {event.description}")

    def _write_to_file(self, event: SecurityEvent) -> None:
        """Write event to log file."""
        try:
            with open(self.log_file, 'a') as f:
                entry = {
                    "id": event.id,
                    "type": event.event_type.value,
                    "level": event.threat_level.name,
                    "description": event.description,
                    "source_ip": event.source_ip,
                    "user_id": event.user_id,
                    "timestamp": event.timestamp.isoformat(),
                    "details": event.details
                }
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    def add_handler(self, handler: Callable[[SecurityEvent], None]) -> None:
        """Add event handler."""
        self._event_handlers.append(handler)

    def get_events(
        self,
        threat_level: Optional[ThreatLevel] = None,
        event_type: Optional[ViolationType] = None,
        since: Optional[datetime] = None
    ) -> List[SecurityEvent]:
        """Get filtered events."""
        results = self._events

        if threat_level:
            results = [e for e in results if e.threat_level == threat_level]

        if event_type:
            results = [e for e in results if e.event_type == event_type]

        if since:
            results = [e for e in results if e.timestamp >= since]

        return results


# =============================================================================
# THREAT DETECTOR
# =============================================================================

class ThreatDetector:
    """Detects potential security threats."""

    def __init__(self, audit_logger: AuditLogger):
        self.audit_logger = audit_logger
        self._failed_attempts: Dict[str, List[datetime]] = defaultdict(list)
        self._blocked_ips: Set[str] = set()

        # Thresholds
        self.failed_attempt_threshold = 5
        self.failed_attempt_window = 300  # 5 minutes
        self.block_duration = 3600  # 1 hour

    def check_brute_force(self, identifier: str) -> bool:
        """Check for brute force attacks."""
        now = datetime.now()
        window_start = now - timedelta(seconds=self.failed_attempt_window)

        # Clean old attempts
        self._failed_attempts[identifier] = [
            t for t in self._failed_attempts[identifier]
            if t > window_start
        ]

        return len(self._failed_attempts[identifier]) >= self.failed_attempt_threshold

    def record_failed_attempt(self, identifier: str) -> None:
        """Record a failed authentication attempt."""
        self._failed_attempts[identifier].append(datetime.now())

        if self.check_brute_force(identifier):
            self._blocked_ips.add(identifier)

            event = SecurityEvent(
                id=secrets.token_hex(8),
                event_type=ViolationType.AUTH_FAILURE,
                threat_level=ThreatLevel.HIGH,
                description=f"Brute force detected from {identifier}",
                source_ip=identifier,
                details={"attempts": len(self._failed_attempts[identifier])}
            )
            self.audit_logger.log(event)

    def is_blocked(self, identifier: str) -> bool:
        """Check if identifier is blocked."""
        return identifier in self._blocked_ips

    def analyze_request(self, request: Dict[str, Any]) -> ThreatLevel:
        """Analyze request for threats."""
        threat_level = ThreatLevel.NONE

        # Check for blocked IP
        source_ip = request.get('source_ip')
        if source_ip and self.is_blocked(source_ip):
            return ThreatLevel.CRITICAL

        # Check payload size
        payload = request.get('payload', '')
        if len(payload) > 1000000:  # 1MB
            threat_level = max(threat_level, ThreatLevel.MEDIUM)

        # Check for suspicious patterns
        validator = InputValidator()
        is_valid, violations, _ = validator.validate(str(payload))

        if not is_valid:
            if ViolationType.INJECTION in violations:
                threat_level = max(threat_level, ThreatLevel.HIGH)
            elif ViolationType.XSS in violations:
                threat_level = max(threat_level, ThreatLevel.MEDIUM)
            else:
                threat_level = max(threat_level, ThreatLevel.LOW)

        return threat_level


# =============================================================================
# SECURITY MANAGER
# =============================================================================

class SecurityManager:
    """Central security management."""

    def __init__(self, secret_key: Optional[str] = None):
        self.validator = InputValidator()
        self.rate_limiter = RateLimiter()
        self.authenticator = Authenticator(secret_key)
        self.authorizer = Authorizer()
        self.audit_logger = AuditLogger()
        self.threat_detector = ThreatDetector(self.audit_logger)

    async def process_request(
        self,
        request: Dict[str, Any],
        require_auth: bool = True
    ) -> Tuple[bool, Optional[User], Dict[str, Any]]:
        """Process and validate a request."""
        source_ip = request.get('source_ip', 'unknown')

        # Check if blocked
        if self.threat_detector.is_blocked(source_ip):
            return False, None, {"error": "blocked"}

        # Analyze threat
        threat_level = self.threat_detector.analyze_request(request)
        if threat_level == ThreatLevel.CRITICAL:
            return False, None, {"error": "threat_detected"}

        # Rate limiting
        allowed, rate_info = await self.rate_limiter.check(source_ip)
        if not allowed:
            return False, None, rate_info

        # Authentication
        user = None
        if require_auth:
            api_key = request.get('api_key')
            token = request.get('token')

            if api_key:
                user = self.authenticator.authenticate_api_key(api_key)
            elif token:
                user = self.authenticator.validate_token(token)

            if not user:
                self.threat_detector.record_failed_attempt(source_ip)
                return False, None, {"error": "authentication_failed"}

        # Validate input
        payload = request.get('payload', '')
        is_valid, violations, sanitized = self.validator.validate(str(payload))

        if not is_valid:
            event = SecurityEvent(
                id=secrets.token_hex(8),
                event_type=violations[0] if violations else ViolationType.INJECTION,
                threat_level=ThreatLevel.MEDIUM,
                description=f"Input validation failed",
                source_ip=source_ip,
                user_id=user.id if user else None,
                details={"violations": [v.value for v in violations]}
            )
            self.audit_logger.log(event)

            # Continue with sanitized input
            request['payload'] = sanitized

        return True, user, {"rate_limit": rate_info}


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Test security module."""
    security = SecurityManager()

    # Create test user
    user = security.authenticator.create_user("test_user", AuthLevel.TRUSTED)
    api_key = security.authenticator.generate_api_key(user.id)

    print(f"Created user: {user.username}")
    print(f"API key: {api_key}")

    # Test request processing
    request = {
        "source_ip": "192.168.1.1",
        "api_key": api_key,
        "payload": "SELECT * FROM users WHERE id=1"
    }

    allowed, auth_user, info = await security.process_request(request)
    print(f"\nRequest 1 (SQL injection test):")
    print(f"  Allowed: {allowed}")
    print(f"  User: {auth_user.username if auth_user else 'None'}")
    print(f"  Info: {info}")

    # Test normal request
    request2 = {
        "source_ip": "192.168.1.1",
        "api_key": api_key,
        "payload": "Hello, this is a normal message"
    }

    allowed, auth_user, info = await security.process_request(request2)
    print(f"\nRequest 2 (normal):")
    print(f"  Allowed: {allowed}")
    print(f"  User: {auth_user.username if auth_user else 'None'}")

    # Test authorization
    print(f"\nAuthorization tests:")
    print(f"  execute:code: {security.authorizer.check(auth_user, 'execute:code')}")
    print(f"  admin:system: {security.authorizer.check(auth_user, 'admin:system')}")


if __name__ == "__main__":
    asyncio.run(main())
