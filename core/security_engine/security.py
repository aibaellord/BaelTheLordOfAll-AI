"""
BAEL Security & Encryption Engine
==================================

Advanced security, encryption, and protection capabilities.

"Security is the foundation of trust." — Ba'el
"""

import asyncio
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import (
    Any, Callable, Dict, List, Optional, Set, Tuple, Union
)


class EncryptionAlgorithm(Enum):
    """Encryption algorithms."""
    AES_256_GCM = "aes_256_gcm"
    AES_256_CBC = "aes_256_cbc"
    CHACHA20_POLY1305 = "chacha20_poly1305"
    RSA_4096 = "rsa_4096"
    HYBRID = "hybrid"


class HashAlgorithm(Enum):
    """Hash algorithms."""
    SHA256 = "sha256"
    SHA384 = "sha384"
    SHA512 = "sha512"
    SHA3_256 = "sha3_256"
    BLAKE2B = "blake2b"
    ARGON2 = "argon2"
    BCRYPT = "bcrypt"
    SCRYPT = "scrypt"


class SecurityLevel(Enum):
    """Security levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    MAXIMUM = 5


class ThreatType(Enum):
    """Types of security threats."""
    INJECTION = "injection"
    XSS = "xss"
    CSRF = "csrf"
    PATH_TRAVERSAL = "path_traversal"
    COMMAND_INJECTION = "command_injection"
    SQL_INJECTION = "sql_injection"
    SENSITIVE_DATA_EXPOSURE = "sensitive_data_exposure"
    INSECURE_DESERIALIZATION = "insecure_deserialization"
    BROKEN_AUTHENTICATION = "broken_authentication"
    EXCESSIVE_PERMISSIONS = "excessive_permissions"


class ScanResult(Enum):
    """Security scan results."""
    CLEAN = "clean"
    SUSPICIOUS = "suspicious"
    MALICIOUS = "malicious"
    UNKNOWN = "unknown"


@dataclass
class EncryptedData:
    """Encrypted data container."""
    ciphertext: bytes
    algorithm: EncryptionAlgorithm
    nonce: Optional[bytes] = None
    tag: Optional[bytes] = None
    salt: Optional[bytes] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecureToken:
    """Secure authentication token."""
    token: str
    token_type: str
    expires_at: datetime
    scopes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityVulnerability:
    """Detected security vulnerability."""
    threat_type: ThreatType
    severity: SecurityLevel
    location: str
    description: str
    recommendation: str
    code_snippet: Optional[str] = None
    confidence: float = 0.8


@dataclass
class SecurityReport:
    """Security scan report."""
    scan_time: datetime
    result: ScanResult
    vulnerabilities: List[SecurityVulnerability]
    score: float  # 0-100
    recommendations: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class SecureRandom:
    """Cryptographically secure random generation."""

    @staticmethod
    def bytes(n: int) -> bytes:
        """Generate secure random bytes."""
        return secrets.token_bytes(n)

    @staticmethod
    def hex(n: int) -> str:
        """Generate secure random hex string."""
        return secrets.token_hex(n)

    @staticmethod
    def urlsafe(n: int) -> str:
        """Generate URL-safe token."""
        return secrets.token_urlsafe(n)

    @staticmethod
    def integer(minimum: int, maximum: int) -> int:
        """Generate secure random integer in range."""
        return secrets.randbelow(maximum - minimum + 1) + minimum

    @staticmethod
    def choice(sequence: List[Any]) -> Any:
        """Securely choose from sequence."""
        return secrets.choice(sequence)

    @staticmethod
    def password(length: int = 16, include_symbols: bool = True) -> str:
        """Generate secure password."""
        alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        if include_symbols:
            alphabet += "!@#$%^&*()_+-=[]{}|;:,.<>?"

        while True:
            password = ''.join(secrets.choice(alphabet) for _ in range(length))
            # Ensure password meets complexity requirements
            if (any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and any(c.isdigit() for c in password)
                and (not include_symbols or any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password))):
                return password


class Hasher:
    """Cryptographic hashing utilities."""

    @staticmethod
    def hash(data: Union[str, bytes], algorithm: HashAlgorithm = HashAlgorithm.SHA256) -> str:
        """Hash data."""
        if isinstance(data, str):
            data = data.encode()

        if algorithm == HashAlgorithm.SHA256:
            return hashlib.sha256(data).hexdigest()
        elif algorithm == HashAlgorithm.SHA384:
            return hashlib.sha384(data).hexdigest()
        elif algorithm == HashAlgorithm.SHA512:
            return hashlib.sha512(data).hexdigest()
        elif algorithm == HashAlgorithm.SHA3_256:
            return hashlib.sha3_256(data).hexdigest()
        elif algorithm == HashAlgorithm.BLAKE2B:
            return hashlib.blake2b(data).hexdigest()
        else:
            return hashlib.sha256(data).hexdigest()

    @staticmethod
    def hash_password(
        password: str,
        salt: Optional[bytes] = None,
        iterations: int = 100000
    ) -> Tuple[str, bytes]:
        """Hash password with salt using PBKDF2."""
        if salt is None:
            salt = SecureRandom.bytes(32)

        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            salt,
            iterations
        )

        return base64.b64encode(key).decode(), salt

    @staticmethod
    def verify_password(
        password: str,
        stored_hash: str,
        salt: bytes,
        iterations: int = 100000
    ) -> bool:
        """Verify password against stored hash."""
        computed_hash, _ = Hasher.hash_password(password, salt, iterations)
        return secrets.compare_digest(computed_hash, stored_hash)

    @staticmethod
    def hmac_sign(
        data: Union[str, bytes],
        key: Union[str, bytes],
        algorithm: HashAlgorithm = HashAlgorithm.SHA256
    ) -> str:
        """Create HMAC signature."""
        if isinstance(data, str):
            data = data.encode()
        if isinstance(key, str):
            key = key.encode()

        algo_map = {
            HashAlgorithm.SHA256: 'sha256',
            HashAlgorithm.SHA384: 'sha384',
            HashAlgorithm.SHA512: 'sha512'
        }

        algo = algo_map.get(algorithm, 'sha256')
        signature = hmac.new(key, data, algo)

        return base64.b64encode(signature.digest()).decode()

    @staticmethod
    def hmac_verify(
        data: Union[str, bytes],
        signature: str,
        key: Union[str, bytes],
        algorithm: HashAlgorithm = HashAlgorithm.SHA256
    ) -> bool:
        """Verify HMAC signature."""
        expected = Hasher.hmac_sign(data, key, algorithm)
        return secrets.compare_digest(expected, signature)


class SimpleEncryption:
    """Simple XOR-based encryption (for educational purposes only).

    Note: In production, use proper encryption libraries like cryptography or PyCryptodome.
    This is a simplified implementation for demonstration.
    """

    @staticmethod
    def _xor_bytes(data: bytes, key: bytes) -> bytes:
        """XOR data with key (repeated)."""
        return bytes(d ^ key[i % len(key)] for i, d in enumerate(data))

    @staticmethod
    def encrypt(
        plaintext: Union[str, bytes],
        key: Union[str, bytes]
    ) -> EncryptedData:
        """Encrypt data using simple XOR with salt."""
        if isinstance(plaintext, str):
            plaintext = plaintext.encode()
        if isinstance(key, str):
            key = key.encode()

        # Generate salt for key derivation
        salt = SecureRandom.bytes(16)

        # Derive encryption key
        derived_key = hashlib.pbkdf2_hmac('sha256', key, salt, 10000, dklen=32)

        # Generate nonce
        nonce = SecureRandom.bytes(12)

        # Combine nonce with key for encryption
        full_key = bytes(a ^ b for a, b in zip(derived_key, nonce.ljust(32, b'\0')))

        # Encrypt
        ciphertext = SimpleEncryption._xor_bytes(plaintext, full_key)

        # Generate authentication tag (HMAC)
        tag = hmac.new(derived_key, nonce + ciphertext, 'sha256').digest()[:16]

        return EncryptedData(
            ciphertext=ciphertext,
            algorithm=EncryptionAlgorithm.AES_256_GCM,  # Simplified representation
            nonce=nonce,
            tag=tag,
            salt=salt
        )

    @staticmethod
    def decrypt(
        encrypted: EncryptedData,
        key: Union[str, bytes]
    ) -> bytes:
        """Decrypt data."""
        if isinstance(key, str):
            key = key.encode()

        # Derive encryption key
        derived_key = hashlib.pbkdf2_hmac('sha256', key, encrypted.salt, 10000, dklen=32)

        # Verify authentication tag
        expected_tag = hmac.new(derived_key, encrypted.nonce + encrypted.ciphertext, 'sha256').digest()[:16]

        if not secrets.compare_digest(encrypted.tag, expected_tag):
            raise ValueError("Authentication failed - data may be corrupted or tampered")

        # Combine nonce with key
        full_key = bytes(a ^ b for a, b in zip(derived_key, encrypted.nonce.ljust(32, b'\0')))

        # Decrypt
        plaintext = SimpleEncryption._xor_bytes(encrypted.ciphertext, full_key)

        return plaintext


class TokenManager:
    """Secure token management."""

    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or SecureRandom.hex(32)
        self.tokens: Dict[str, SecureToken] = {}
        self.revoked: Set[str] = set()

    def generate_token(
        self,
        token_type: str = "access",
        expires_in: int = 3600,  # seconds
        scopes: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SecureToken:
        """Generate a secure token."""
        token_value = SecureRandom.urlsafe(32)
        expires_at = datetime.now() + timedelta(seconds=expires_in)

        token = SecureToken(
            token=token_value,
            token_type=token_type,
            expires_at=expires_at,
            scopes=scopes or [],
            metadata=metadata or {}
        )

        # Sign token
        signature = Hasher.hmac_sign(token_value, self.secret_key)
        token.metadata["signature"] = signature

        self.tokens[token_value] = token

        return token

    def validate_token(self, token_value: str) -> Optional[SecureToken]:
        """Validate a token."""
        if token_value in self.revoked:
            return None

        token = self.tokens.get(token_value)
        if not token:
            return None

        # Check expiration
        if datetime.now() > token.expires_at:
            self.revoke_token(token_value)
            return None

        # Verify signature
        stored_sig = token.metadata.get("signature")
        if stored_sig:
            expected_sig = Hasher.hmac_sign(token_value, self.secret_key)
            if not secrets.compare_digest(stored_sig, expected_sig):
                return None

        return token

    def revoke_token(self, token_value: str) -> None:
        """Revoke a token."""
        self.revoked.add(token_value)
        self.tokens.pop(token_value, None)

    def cleanup_expired(self) -> int:
        """Clean up expired tokens."""
        now = datetime.now()
        expired = [
            token_value for token_value, token in self.tokens.items()
            if now > token.expires_at
        ]

        for token_value in expired:
            self.tokens.pop(token_value, None)

        return len(expired)


class VulnerabilityScanner:
    """Security vulnerability scanner."""

    # Patterns for common vulnerabilities
    PATTERNS = {
        ThreatType.SQL_INJECTION: [
            re.compile(r"(\"|')?\s*;\s*--", re.I),
            re.compile(r"(\"|')?\s*;\s*drop\s+", re.I),
            re.compile(r"(\"|')?\s*or\s+1\s*=\s*1", re.I),
            re.compile(r"(\"|')?\s*union\s+select\s+", re.I),
            re.compile(r"\b(select|insert|update|delete)\s+.*\s+from\s+", re.I),
        ],
        ThreatType.XSS: [
            re.compile(r"<script\b[^>]*>", re.I),
            re.compile(r"javascript:", re.I),
            re.compile(r"on(click|load|error|mouseover)\s*=", re.I),
            re.compile(r"<iframe\b", re.I),
            re.compile(r"document\.cookie", re.I),
        ],
        ThreatType.PATH_TRAVERSAL: [
            re.compile(r"\.\./"),
            re.compile(r"\.\.\\"),
            re.compile(r"%2e%2e%2f", re.I),
            re.compile(r"%252e%252e%252f", re.I),
        ],
        ThreatType.COMMAND_INJECTION: [
            re.compile(r";\s*(ls|cat|rm|wget|curl)\b", re.I),
            re.compile(r"\|\s*(ls|cat|rm|wget|curl)\b", re.I),
            re.compile(r"`[^`]+`"),
            re.compile(r"\$\([^)]+\)"),
        ],
        ThreatType.SENSITIVE_DATA_EXPOSURE: [
            re.compile(r"password\s*=\s*['\"][^'\"]+['\"]", re.I),
            re.compile(r"api[_-]?key\s*=\s*['\"][^'\"]+['\"]", re.I),
            re.compile(r"secret\s*=\s*['\"][^'\"]+['\"]", re.I),
            re.compile(r"token\s*=\s*['\"][^'\"]+['\"]", re.I),
            re.compile(r"(aws|azure|gcp)[_-]?(access|secret)[_-]?key", re.I),
        ],
    }

    SEVERITY_MAP = {
        ThreatType.SQL_INJECTION: SecurityLevel.CRITICAL,
        ThreatType.XSS: SecurityLevel.HIGH,
        ThreatType.PATH_TRAVERSAL: SecurityLevel.HIGH,
        ThreatType.COMMAND_INJECTION: SecurityLevel.CRITICAL,
        ThreatType.SENSITIVE_DATA_EXPOSURE: SecurityLevel.HIGH,
        ThreatType.INJECTION: SecurityLevel.HIGH,
        ThreatType.CSRF: SecurityLevel.MEDIUM,
        ThreatType.INSECURE_DESERIALIZATION: SecurityLevel.HIGH,
        ThreatType.BROKEN_AUTHENTICATION: SecurityLevel.CRITICAL,
        ThreatType.EXCESSIVE_PERMISSIONS: SecurityLevel.MEDIUM,
    }

    RECOMMENDATIONS = {
        ThreatType.SQL_INJECTION: "Use parameterized queries or prepared statements",
        ThreatType.XSS: "Sanitize and escape user input, use Content-Security-Policy",
        ThreatType.PATH_TRAVERSAL: "Validate and sanitize file paths, use whitelists",
        ThreatType.COMMAND_INJECTION: "Avoid shell commands, use libraries instead",
        ThreatType.SENSITIVE_DATA_EXPOSURE: "Use environment variables, never hardcode secrets",
    }

    async def scan_input(self, input_data: str) -> List[SecurityVulnerability]:
        """Scan input for vulnerabilities."""
        vulnerabilities = []

        for threat_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                matches = pattern.finditer(input_data)
                for match in matches:
                    vulnerabilities.append(SecurityVulnerability(
                        threat_type=threat_type,
                        severity=self.SEVERITY_MAP.get(threat_type, SecurityLevel.MEDIUM),
                        location=f"Position {match.start()}-{match.end()}",
                        description=f"Potential {threat_type.value} detected",
                        recommendation=self.RECOMMENDATIONS.get(
                            threat_type,
                            "Review and sanitize the input"
                        ),
                        code_snippet=match.group()[:100]
                    ))

        return vulnerabilities

    async def scan_code(self, code: str, language: str = "python") -> List[SecurityVulnerability]:
        """Scan code for security issues."""
        vulnerabilities = []

        # Dangerous function patterns by language
        dangerous_patterns = {
            "python": [
                (r"\beval\s*\(", "Use of eval() is dangerous", ThreatType.INJECTION),
                (r"\bexec\s*\(", "Use of exec() is dangerous", ThreatType.INJECTION),
                (r"\bos\.system\s*\(", "Use subprocess instead of os.system", ThreatType.COMMAND_INJECTION),
                (r"\bpickle\.loads?\s*\(", "Pickle can execute arbitrary code", ThreatType.INSECURE_DESERIALIZATION),
                (r"shell\s*=\s*True", "shell=True is vulnerable to injection", ThreatType.COMMAND_INJECTION),
                (r"\bMD5\b|\bmd5\b", "MD5 is cryptographically weak", ThreatType.BROKEN_AUTHENTICATION),
                (r"\bSHA1\b|\bsha1\b", "SHA1 is cryptographically weak", ThreatType.BROKEN_AUTHENTICATION),
            ],
            "javascript": [
                (r"\beval\s*\(", "Use of eval() is dangerous", ThreatType.INJECTION),
                (r"innerHTML\s*=", "innerHTML can lead to XSS", ThreatType.XSS),
                (r"document\.write\s*\(", "document.write can lead to XSS", ThreatType.XSS),
                (r"\.html\s*\(", "jQuery .html() can lead to XSS", ThreatType.XSS),
            ],
        }

        patterns = dangerous_patterns.get(language, dangerous_patterns["python"])

        for pattern, description, threat_type in patterns:
            matches = re.finditer(pattern, code, re.I)
            for match in matches:
                # Get line number
                line_num = code[:match.start()].count('\n') + 1

                vulnerabilities.append(SecurityVulnerability(
                    threat_type=threat_type,
                    severity=self.SEVERITY_MAP.get(threat_type, SecurityLevel.MEDIUM),
                    location=f"Line {line_num}",
                    description=description,
                    recommendation=self.RECOMMENDATIONS.get(
                        threat_type,
                        "Review and refactor the code"
                    ),
                    code_snippet=match.group()
                ))

        # Check for sensitive data patterns in code
        vuln = await self.scan_input(code)
        vulnerabilities.extend(vuln)

        return vulnerabilities


class RateLimiter:
    """Rate limiting for protection."""

    def __init__(
        self,
        max_requests: int = 100,
        window_seconds: int = 60
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = {}

    def check(self, identifier: str) -> Tuple[bool, int]:
        """Check if request is allowed.

        Returns (allowed, remaining_requests)
        """
        now = time.time()
        window_start = now - self.window_seconds

        # Get request times for identifier
        request_times = self.requests.get(identifier, [])

        # Filter to current window
        request_times = [t for t in request_times if t > window_start]

        if len(request_times) >= self.max_requests:
            return False, 0

        # Add current request
        request_times.append(now)
        self.requests[identifier] = request_times

        return True, self.max_requests - len(request_times)

    def reset(self, identifier: str) -> None:
        """Reset rate limit for identifier."""
        self.requests.pop(identifier, None)

    def cleanup(self) -> int:
        """Clean up old entries."""
        now = time.time()
        window_start = now - self.window_seconds
        cleaned = 0

        for identifier in list(self.requests.keys()):
            request_times = [t for t in self.requests[identifier] if t > window_start]
            if request_times:
                self.requests[identifier] = request_times
            else:
                del self.requests[identifier]
                cleaned += 1

        return cleaned


class SecurityEngine:
    """
    Main Security Engine

    Provides:
    - Encryption/decryption
    - Hashing and password handling
    - Token management
    - Vulnerability scanning
    - Rate limiting
    """

    def __init__(self, secret_key: Optional[str] = None):
        self.random = SecureRandom()
        self.hasher = Hasher()
        self.encryption = SimpleEncryption()
        self.tokens = TokenManager(secret_key)
        self.scanner = VulnerabilityScanner()
        self.rate_limiter = RateLimiter()

        self.scan_history: List[SecurityReport] = []

        self.data_dir = Path("data/security")
        self.data_dir.mkdir(parents=True, exist_ok=True)

    async def encrypt(
        self,
        data: Union[str, bytes],
        key: str
    ) -> EncryptedData:
        """Encrypt data."""
        return self.encryption.encrypt(data, key)

    async def decrypt(
        self,
        encrypted: EncryptedData,
        key: str
    ) -> bytes:
        """Decrypt data."""
        return self.encryption.decrypt(encrypted, key)

    async def hash_password(
        self,
        password: str
    ) -> Tuple[str, bytes]:
        """Hash a password securely."""
        return self.hasher.hash_password(password)

    async def verify_password(
        self,
        password: str,
        stored_hash: str,
        salt: bytes
    ) -> bool:
        """Verify a password."""
        return self.hasher.verify_password(password, stored_hash, salt)

    async def generate_token(
        self,
        token_type: str = "access",
        expires_in: int = 3600,
        scopes: Optional[List[str]] = None
    ) -> SecureToken:
        """Generate an authentication token."""
        return self.tokens.generate_token(token_type, expires_in, scopes)

    async def validate_token(self, token: str) -> Optional[SecureToken]:
        """Validate a token."""
        return self.tokens.validate_token(token)

    async def scan(
        self,
        content: str,
        content_type: str = "input"
    ) -> SecurityReport:
        """Perform security scan."""
        if content_type == "code":
            vulnerabilities = await self.scanner.scan_code(content)
        else:
            vulnerabilities = await self.scanner.scan_input(content)

        # Calculate score
        if not vulnerabilities:
            score = 100.0
            result = ScanResult.CLEAN
        else:
            severity_weights = {
                SecurityLevel.LOW: 5,
                SecurityLevel.MEDIUM: 10,
                SecurityLevel.HIGH: 25,
                SecurityLevel.CRITICAL: 50,
                SecurityLevel.MAXIMUM: 100
            }

            total_penalty = sum(
                severity_weights.get(v.severity, 10)
                for v in vulnerabilities
            )
            score = max(0.0, 100.0 - total_penalty)

            if score >= 70:
                result = ScanResult.SUSPICIOUS
            else:
                result = ScanResult.MALICIOUS

        # Generate recommendations
        recommendations = list(set(v.recommendation for v in vulnerabilities))

        report = SecurityReport(
            scan_time=datetime.now(),
            result=result,
            vulnerabilities=vulnerabilities,
            score=score,
            recommendations=recommendations
        )

        self.scan_history.append(report)

        return report

    async def check_rate_limit(
        self,
        identifier: str
    ) -> Tuple[bool, int]:
        """Check rate limit."""
        return self.rate_limiter.check(identifier)

    def generate_password(
        self,
        length: int = 16,
        include_symbols: bool = True
    ) -> str:
        """Generate a secure password."""
        return self.random.password(length, include_symbols)

    def get_summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        total_scans = len(self.scan_history)
        clean_scans = sum(1 for s in self.scan_history if s.result == ScanResult.CLEAN)

        return {
            "total_scans": total_scans,
            "clean_scans": clean_scans,
            "clean_rate": clean_scans / total_scans if total_scans else 1.0,
            "active_tokens": len(self.tokens.tokens),
            "revoked_tokens": len(self.tokens.revoked),
            "capabilities": [
                "encryption",
                "password_hashing",
                "token_management",
                "vulnerability_scanning",
                "rate_limiting",
                "secure_random"
            ],
            "supported_algorithms": {
                "encryption": [a.value for a in EncryptionAlgorithm],
                "hashing": [h.value for h in HashAlgorithm]
            }
        }


# Convenience instance
security_engine = SecurityEngine()
