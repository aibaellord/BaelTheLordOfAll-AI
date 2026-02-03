"""
Security hardening utilities including input sanitization, validation, and protection mechanisms.
Ensures secure defaults and prevents common attacks.
"""

import hashlib
import logging
import re
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import Request

logger = logging.getLogger("BAEL.Security")


class InputSanitizer:
    """Sanitize and validate user input."""

    # Patterns for common injection attacks
    SQL_INJECTION_PATTERN = re.compile(r"('|\"|-{2}|;|\/\*|\*\/|xp_|sp_)", re.IGNORECASE)
    SCRIPT_INJECTION_PATTERN = re.compile(r"(<script|javascript:|onerror=|onclick=)", re.IGNORECASE)
    PATH_TRAVERSAL_PATTERN = re.compile(r"(\.\.|~|/etc|/var|C:\\|System32)", re.IGNORECASE)

    @staticmethod
    def sanitize_string(value: str, max_length: int = 10000) -> str:
        """Sanitize string input."""
        if not isinstance(value, str):
            return str(value)[:max_length]

        # Limit length
        value = value[:max_length]

        # Remove null bytes
        value = value.replace('\x00', '')

        # Remove control characters
        value = ''.join(char for char in value if ord(char) >= 32 or char in '\t\n\r')

        return value

    @staticmethod
    def validate_sql_safe(value: str) -> bool:
        """Check if string is safe from SQL injection."""
        return not InputSanitizer.SQL_INJECTION_PATTERN.search(value)

    @staticmethod
    def validate_script_safe(value: str) -> bool:
        """Check if string is safe from script injection."""
        return not InputSanitizer.SCRIPT_INJECTION_PATTERN.search(value)

    @staticmethod
    def validate_path_safe(value: str) -> bool:
        """Check if string is safe from path traversal."""
        return not InputSanitizer.PATH_TRAVERSAL_PATTERN.search(value)

    @staticmethod
    def sanitize_dict(data: Dict[str, Any], max_depth: int = 5) -> Dict[str, Any]:
        """Recursively sanitize dictionary."""
        if max_depth <= 0:
            return {}

        sanitized = {}
        for key, value in data.items():
            # Sanitize key
            key = InputSanitizer.sanitize_string(str(key), max_length=256)

            if isinstance(value, str):
                sanitized[key] = InputSanitizer.sanitize_string(value)
            elif isinstance(value, dict):
                sanitized[key] = InputSanitizer.sanitize_dict(value, max_depth - 1)
            elif isinstance(value, list):
                sanitized[key] = [
                    InputSanitizer.sanitize_string(str(v)) if isinstance(v, str) else v
                    for v in value[:100]  # Limit list size
                ]
            else:
                sanitized[key] = value

        return sanitized


class RateLimiter:
    """Rate limiting to prevent abuse."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[datetime]] = {}

    def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed."""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)

        if identifier not in self.requests:
            self.requests[identifier] = []

        # Clean old requests
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if req_time > window_start
        ]

        # Check if allowed
        if len(self.requests[identifier]) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for {identifier}")
            return False

        # Record request
        self.requests[identifier].append(now)
        return True

    def get_remaining(self, identifier: str) -> int:
        """Get remaining requests for identifier."""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)

        if identifier not in self.requests:
            return self.max_requests

        recent = [
            req_time for req_time in self.requests[identifier]
            if req_time > window_start
        ]

        return max(0, self.max_requests - len(recent))


class PasswordHasher:
    """Secure password hashing."""

    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> str:
        """Hash password with salt."""
        if salt is None:
            salt = secrets.token_hex(16)

        # Use PBKDF2 equivalent
        hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}${hash_obj.hex()}"

    @staticmethod
    def verify_password(password: str, hash_value: str) -> bool:
        """Verify password against hash."""
        try:
            salt, stored_hash = hash_value.split('$')
            computed_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
            return computed_hash == stored_hash
        except (ValueError, AttributeError):
            return False


class SecretManager:
    """Manage sensitive secrets securely."""

    def __init__(self):
        self.secrets: Dict[str, str] = {}

    def set_secret(self, key: str, value: str):
        """Store a secret."""
        # Hash the key for storage
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        self.secrets[key_hash] = value
        logger.info(f"Secret '{key}' registered")

    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve a secret."""
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self.secrets.get(key_hash)

    def has_secret(self, key: str) -> bool:
        """Check if secret exists."""
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return key_hash in self.secrets

    def delete_secret(self, key: str) -> bool:
        """Delete a secret."""
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        if key_hash in self.secrets:
            del self.secrets[key_hash]
            logger.info(f"Secret '{key}' deleted")
            return True
        return False


class AuditLog:
    """Audit log for security events."""

    def __init__(self):
        self.logs: List[Dict[str, Any]] = []

    def log_event(self, event_type: str, severity: str, actor: str,
                  action: str, resource: str, result: str, details: Optional[Dict] = None):
        """Log a security event."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "severity": severity,
            "actor": actor,
            "action": action,
            "resource": resource,
            "result": result,
            "details": details or {}
        }
        self.logs.append(entry)

        if severity in ["HIGH", "CRITICAL"]:
            logger.warning(f"Security event [{severity}]: {action} on {resource} by {actor}")
        else:
            logger.info(f"Audit event: {action} on {resource} by {actor}")

    def get_logs(self, actor: Optional[str] = None,
                 severity: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve audit logs with filtering."""
        filtered = self.logs

        if actor:
            filtered = [log for log in filtered if log["actor"] == actor]

        if severity:
            filtered = [log for log in filtered if log["severity"] == severity]

        return filtered[-limit:]

    def clear_old_logs(self, days: int = 30):
        """Clear logs older than specified days."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        original_count = len(self.logs)

        self.logs = [
            log for log in self.logs
            if datetime.fromisoformat(log["timestamp"]) > cutoff
        ]

        removed = original_count - len(self.logs)
        logger.info(f"Cleared {removed} old audit logs")


class SecurityHeaders:
    """Security headers for HTTP responses."""

    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """Get recommended security headers."""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
        }


# Global instances
input_sanitizer = InputSanitizer()
rate_limiter = RateLimiter(max_requests=1000, window_seconds=3600)
secret_manager = SecretManager()
audit_log = AuditLog()
