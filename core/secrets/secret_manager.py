#!/usr/bin/env python3
"""
BAEL - Secret Manager
Secure secret storage and management.

Features:
- Secret encryption
- Secret rotation
- Access control
- Audit logging
- Key derivation
- Environment integration
- Secret versioning
- Expiration handling
- Masking
- Secret references
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
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import (Any, Awaitable, Callable, Dict, Generic, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)


T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class SecretType(Enum):
    """Types of secrets."""
    PASSWORD = "password"
    API_KEY = "api_key"
    TOKEN = "token"
    CERTIFICATE = "certificate"
    PRIVATE_KEY = "private_key"
    CONNECTION_STRING = "connection_string"
    SSH_KEY = "ssh_key"
    ENCRYPTION_KEY = "encryption_key"
    GENERIC = "generic"


class RotationStrategy(Enum):
    """Secret rotation strategies."""
    MANUAL = "manual"
    TIME_BASED = "time_based"
    USAGE_BASED = "usage_based"
    ON_DEMAND = "on_demand"


class AccessLevel(Enum):
    """Access levels for secrets."""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    ROTATE = "rotate"


class AuditAction(Enum):
    """Audit log actions."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    ROTATE = "rotate"
    GRANT = "grant"
    REVOKE = "revoke"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class SecretMetadata:
    """Metadata for a secret."""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    expires_at: Optional[datetime] = None
    rotation_period: Optional[int] = None  # days
    last_rotated: Optional[datetime] = None
    access_count: int = 0
    custom: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecretVersion:
    """A version of a secret value."""
    version_id: str
    value: bytes
    created_at: datetime = field(default_factory=datetime.utcnow)
    is_current: bool = True
    checksum: str = ""

    def __post_init__(self):
        if not self.checksum:
            self.checksum = hashlib.sha256(self.value).hexdigest()[:16]


@dataclass
class Secret:
    """A secret with its metadata and versions."""
    id: str
    name: str
    secret_type: SecretType = SecretType.GENERIC
    metadata: SecretMetadata = field(default_factory=SecretMetadata)
    versions: List[SecretVersion] = field(default_factory=list)
    rotation_strategy: RotationStrategy = RotationStrategy.MANUAL

    @property
    def current_version(self) -> Optional[SecretVersion]:
        for v in self.versions:
            if v.is_current:
                return v
        return self.versions[-1] if self.versions else None


@dataclass
class AccessPolicy:
    """Access policy for secrets."""
    principal: str  # user/role/service
    secret_pattern: str  # glob pattern
    levels: List[AccessLevel] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)
    expires_at: Optional[datetime] = None


@dataclass
class AuditEntry:
    """Audit log entry."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action: AuditAction = AuditAction.READ
    secret_id: str = ""
    principal: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None
    success: bool = True
    details: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# ENCRYPTION
# =============================================================================

class Encryptor(ABC):
    """Abstract encryptor."""

    @abstractmethod
    def encrypt(self, plaintext: bytes) -> bytes:
        """Encrypt data."""
        pass

    @abstractmethod
    def decrypt(self, ciphertext: bytes) -> bytes:
        """Decrypt data."""
        pass


class XOREncryptor(Encryptor):
    """Simple XOR encryption (for demo - use proper crypto in production)."""

    def __init__(self, key: bytes):
        self.key = key

    def encrypt(self, plaintext: bytes) -> bytes:
        key_len = len(self.key)
        return bytes(p ^ self.key[i % key_len] for i, p in enumerate(plaintext))

    def decrypt(self, ciphertext: bytes) -> bytes:
        # XOR is symmetric
        return self.encrypt(ciphertext)


class FernetLikeEncryptor(Encryptor):
    """Fernet-like encryption using HMAC and XOR (demo implementation)."""

    def __init__(self, key: bytes):
        # Derive encryption and signing keys
        self.enc_key = hashlib.sha256(key + b"enc").digest()
        self.sign_key = hashlib.sha256(key + b"sign").digest()

    def encrypt(self, plaintext: bytes) -> bytes:
        # Generate IV
        iv = secrets.token_bytes(16)

        # Encrypt with XOR (simplified)
        encrypted = bytes(
            p ^ self.enc_key[(i + iv[i % 16]) % 32]
            for i, p in enumerate(plaintext)
        )

        # Create message
        message = iv + encrypted

        # Sign
        signature = hmac.new(self.sign_key, message, hashlib.sha256).digest()

        return signature + message

    def decrypt(self, ciphertext: bytes) -> bytes:
        if len(ciphertext) < 48:  # 32 sig + 16 iv
            raise ValueError("Invalid ciphertext")

        signature = ciphertext[:32]
        message = ciphertext[32:]

        # Verify
        expected_sig = hmac.new(self.sign_key, message, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected_sig):
            raise ValueError("Invalid signature")

        iv = message[:16]
        encrypted = message[16:]

        # Decrypt
        plaintext = bytes(
            c ^ self.enc_key[(i + iv[i % 16]) % 32]
            for i, c in enumerate(encrypted)
        )

        return plaintext


# =============================================================================
# KEY DERIVATION
# =============================================================================

class KeyDerivation:
    """Key derivation functions."""

    @staticmethod
    def derive_key(
        password: str,
        salt: bytes,
        iterations: int = 100000,
        key_length: int = 32
    ) -> bytes:
        """Derive key using PBKDF2-like algorithm."""
        derived = password.encode()

        for i in range(iterations):
            derived = hashlib.pbkdf2_hmac(
                'sha256',
                derived,
                salt + i.to_bytes(4, 'big'),
                1
            )

        return derived[:key_length]

    @staticmethod
    def generate_salt(length: int = 16) -> bytes:
        """Generate random salt."""
        return secrets.token_bytes(length)

    @staticmethod
    def generate_key(length: int = 32) -> bytes:
        """Generate random key."""
        return secrets.token_bytes(length)


# =============================================================================
# SECRET GENERATOR
# =============================================================================

class SecretGenerator:
    """Generate secure secrets."""

    LOWERCASE = "abcdefghijklmnopqrstuvwxyz"
    UPPERCASE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    DIGITS = "0123456789"
    SYMBOLS = "!@#$%^&*()-_=+[]{}|;:,.<>?"

    @classmethod
    def generate_password(
        cls,
        length: int = 16,
        lowercase: bool = True,
        uppercase: bool = True,
        digits: bool = True,
        symbols: bool = True
    ) -> str:
        """Generate secure password."""
        charset = ""
        required = []

        if lowercase:
            charset += cls.LOWERCASE
            required.append(secrets.choice(cls.LOWERCASE))
        if uppercase:
            charset += cls.UPPERCASE
            required.append(secrets.choice(cls.UPPERCASE))
        if digits:
            charset += cls.DIGITS
            required.append(secrets.choice(cls.DIGITS))
        if symbols:
            charset += cls.SYMBOLS
            required.append(secrets.choice(cls.SYMBOLS))

        if not charset:
            charset = cls.LOWERCASE + cls.DIGITS

        # Generate rest of password
        remaining_length = length - len(required)
        password = [secrets.choice(charset) for _ in range(remaining_length)]
        password.extend(required)

        # Shuffle
        password_list = list(password)
        for i in range(len(password_list) - 1, 0, -1):
            j = secrets.randbelow(i + 1)
            password_list[i], password_list[j] = password_list[j], password_list[i]

        return "".join(password_list)

    @classmethod
    def generate_api_key(cls, prefix: str = "bael") -> str:
        """Generate API key."""
        random_part = secrets.token_urlsafe(32)
        return f"{prefix}_{random_part}"

    @classmethod
    def generate_token(cls, length: int = 32) -> str:
        """Generate random token."""
        return secrets.token_urlsafe(length)

    @classmethod
    def generate_uuid(cls) -> str:
        """Generate UUID."""
        return str(uuid.uuid4())


# =============================================================================
# SECRET MANAGER
# =============================================================================

class SecretManager:
    """
    Secret Manager for BAEL.

    Provides secure storage and management of secrets.
    """

    def __init__(self, master_key: Optional[bytes] = None):
        self._master_key = master_key or KeyDerivation.generate_key()
        self._encryptor = FernetLikeEncryptor(self._master_key)
        self._secrets: Dict[str, Secret] = {}
        self._policies: List[AccessPolicy] = []
        self._audit_log: List[AuditEntry] = []
        self._lock = asyncio.Lock()

    # -------------------------------------------------------------------------
    # SECRET CRUD
    # -------------------------------------------------------------------------

    async def create_secret(
        self,
        name: str,
        value: str,
        secret_type: SecretType = SecretType.GENERIC,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        expires_in_days: Optional[int] = None,
        principal: str = "system"
    ) -> Secret:
        """Create a new secret."""
        async with self._lock:
            if name in self._secrets:
                raise ValueError(f"Secret already exists: {name}")

            secret_id = str(uuid.uuid4())

            # Encrypt value
            encrypted = self._encryptor.encrypt(value.encode())

            version = SecretVersion(
                version_id=str(uuid.uuid4()),
                value=encrypted
            )

            metadata = SecretMetadata(
                created_by=principal,
                description=description,
                tags=tags or []
            )

            if expires_in_days:
                metadata.expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

            secret = Secret(
                id=secret_id,
                name=name,
                secret_type=secret_type,
                metadata=metadata,
                versions=[version]
            )

            self._secrets[name] = secret

            await self._audit(
                AuditAction.CREATE,
                secret_id,
                principal,
                {"name": name, "type": secret_type.value}
            )

            return secret

    async def get_secret(
        self,
        name: str,
        version_id: Optional[str] = None,
        principal: str = "system"
    ) -> Optional[str]:
        """Get secret value."""
        secret = self._secrets.get(name)

        if not secret:
            return None

        # Check expiration
        if secret.metadata.expires_at:
            if datetime.utcnow() > secret.metadata.expires_at:
                await self._audit(
                    AuditAction.READ,
                    secret.id,
                    principal,
                    {"expired": True},
                    success=False
                )
                raise ValueError("Secret has expired")

        # Get version
        if version_id:
            version = next((v for v in secret.versions if v.version_id == version_id), None)
        else:
            version = secret.current_version

        if not version:
            return None

        # Decrypt
        decrypted = self._encryptor.decrypt(version.value)

        # Update access count
        secret.metadata.access_count += 1

        await self._audit(
            AuditAction.READ,
            secret.id,
            principal,
            {"version": version.version_id}
        )

        return decrypted.decode()

    async def update_secret(
        self,
        name: str,
        value: str,
        principal: str = "system"
    ) -> Secret:
        """Update secret with new value (creates new version)."""
        async with self._lock:
            secret = self._secrets.get(name)

            if not secret:
                raise ValueError(f"Secret not found: {name}")

            # Mark current as not current
            for v in secret.versions:
                v.is_current = False

            # Create new version
            encrypted = self._encryptor.encrypt(value.encode())

            version = SecretVersion(
                version_id=str(uuid.uuid4()),
                value=encrypted,
                is_current=True
            )

            secret.versions.append(version)
            secret.metadata.updated_at = datetime.utcnow()

            await self._audit(
                AuditAction.UPDATE,
                secret.id,
                principal,
                {"new_version": version.version_id}
            )

            return secret

    async def delete_secret(
        self,
        name: str,
        principal: str = "system"
    ) -> bool:
        """Delete a secret."""
        async with self._lock:
            if name not in self._secrets:
                return False

            secret = self._secrets[name]
            del self._secrets[name]

            await self._audit(
                AuditAction.DELETE,
                secret.id,
                principal
            )

            return True

    # -------------------------------------------------------------------------
    # SECRET ROTATION
    # -------------------------------------------------------------------------

    async def rotate_secret(
        self,
        name: str,
        new_value: Optional[str] = None,
        principal: str = "system"
    ) -> Secret:
        """Rotate a secret."""
        secret = self._secrets.get(name)

        if not secret:
            raise ValueError(f"Secret not found: {name}")

        # Generate new value if not provided
        if new_value is None:
            if secret.secret_type == SecretType.PASSWORD:
                new_value = SecretGenerator.generate_password()
            elif secret.secret_type == SecretType.API_KEY:
                new_value = SecretGenerator.generate_api_key()
            elif secret.secret_type == SecretType.TOKEN:
                new_value = SecretGenerator.generate_token()
            else:
                new_value = SecretGenerator.generate_token(32)

        # Update with rotation
        result = await self.update_secret(name, new_value, principal)
        result.metadata.last_rotated = datetime.utcnow()

        await self._audit(
            AuditAction.ROTATE,
            secret.id,
            principal
        )

        return result

    async def check_rotation_needed(self) -> List[str]:
        """Check which secrets need rotation."""
        needs_rotation = []

        for name, secret in self._secrets.items():
            if secret.rotation_strategy == RotationStrategy.MANUAL:
                continue

            if secret.metadata.rotation_period:
                last = secret.metadata.last_rotated or secret.metadata.created_at
                days_since = (datetime.utcnow() - last).days

                if days_since >= secret.metadata.rotation_period:
                    needs_rotation.append(name)

        return needs_rotation

    # -------------------------------------------------------------------------
    # ACCESS CONTROL
    # -------------------------------------------------------------------------

    async def grant_access(
        self,
        principal: str,
        secret_pattern: str,
        levels: List[AccessLevel],
        expires_in_days: Optional[int] = None,
        granting_principal: str = "system"
    ) -> AccessPolicy:
        """Grant access to secrets."""
        policy = AccessPolicy(
            principal=principal,
            secret_pattern=secret_pattern,
            levels=levels
        )

        if expires_in_days:
            policy.expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        self._policies.append(policy)

        await self._audit(
            AuditAction.GRANT,
            secret_pattern,
            granting_principal,
            {"principal": principal, "levels": [l.value for l in levels]}
        )

        return policy

    async def revoke_access(
        self,
        principal: str,
        secret_pattern: str,
        revoking_principal: str = "system"
    ) -> bool:
        """Revoke access to secrets."""
        initial_count = len(self._policies)

        self._policies = [
            p for p in self._policies
            if not (p.principal == principal and p.secret_pattern == secret_pattern)
        ]

        removed = initial_count - len(self._policies)

        if removed > 0:
            await self._audit(
                AuditAction.REVOKE,
                secret_pattern,
                revoking_principal,
                {"principal": principal}
            )

        return removed > 0

    def check_access(
        self,
        principal: str,
        secret_name: str,
        level: AccessLevel
    ) -> bool:
        """Check if principal has access."""
        import fnmatch

        for policy in self._policies:
            if policy.principal != principal:
                continue

            if not fnmatch.fnmatch(secret_name, policy.secret_pattern):
                continue

            if level not in policy.levels:
                continue

            if policy.expires_at and datetime.utcnow() > policy.expires_at:
                continue

            return True

        return False

    # -------------------------------------------------------------------------
    # AUDIT
    # -------------------------------------------------------------------------

    async def _audit(
        self,
        action: AuditAction,
        secret_id: str,
        principal: str,
        details: Optional[Dict] = None,
        success: bool = True
    ) -> None:
        """Log audit entry."""
        entry = AuditEntry(
            action=action,
            secret_id=secret_id,
            principal=principal,
            details=details or {},
            success=success
        )

        self._audit_log.append(entry)

    async def get_audit_log(
        self,
        secret_id: Optional[str] = None,
        principal: Optional[str] = None,
        action: Optional[AuditAction] = None,
        limit: int = 100
    ) -> List[AuditEntry]:
        """Get audit log entries."""
        entries = list(self._audit_log)

        if secret_id:
            entries = [e for e in entries if e.secret_id == secret_id]

        if principal:
            entries = [e for e in entries if e.principal == principal]

        if action:
            entries = [e for e in entries if e.action == action]

        # Most recent first
        entries.sort(key=lambda e: e.timestamp, reverse=True)

        return entries[:limit]

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def list_secrets(self) -> List[Dict[str, Any]]:
        """List all secrets (metadata only)."""
        return [
            {
                "id": s.id,
                "name": s.name,
                "type": s.secret_type.value,
                "versions": len(s.versions),
                "created_at": s.metadata.created_at.isoformat(),
                "expires_at": s.metadata.expires_at.isoformat() if s.metadata.expires_at else None,
                "tags": s.metadata.tags
            }
            for s in self._secrets.values()
        ]

    def mask_value(self, value: str, visible_chars: int = 4) -> str:
        """Mask a secret value for display."""
        if len(value) <= visible_chars * 2:
            return "*" * len(value)

        return value[:visible_chars] + "*" * (len(value) - visible_chars * 2) + value[-visible_chars:]

    async def export_secrets(
        self,
        pattern: Optional[str] = None,
        encrypt: bool = True
    ) -> Dict[str, Any]:
        """Export secrets (for backup)."""
        import fnmatch

        export_data = {}

        for name, secret in self._secrets.items():
            if pattern and not fnmatch.fnmatch(name, pattern):
                continue

            version = secret.current_version
            if version:
                value = version.value
                if encrypt:
                    value = base64.b64encode(value).decode()
                else:
                    decrypted = self._encryptor.decrypt(value)
                    value = base64.b64encode(decrypted).decode()

                export_data[name] = {
                    "type": secret.secret_type.value,
                    "value": value,
                    "encrypted": encrypt,
                    "metadata": {
                        "description": secret.metadata.description,
                        "tags": secret.metadata.tags
                    }
                }

        return export_data

    def get_environment_dict(self, prefix: str = "") -> Dict[str, str]:
        """Get secrets as environment variable dict."""
        env = {}

        for name, secret in self._secrets.items():
            version = secret.current_version
            if version:
                decrypted = self._encryptor.decrypt(version.value)
                env_name = prefix + name.upper().replace("-", "_").replace(".", "_")
                env[env_name] = decrypted.decode()

        return env


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Secret Manager."""
    print("=" * 70)
    print("BAEL - SECRET MANAGER DEMO")
    print("Secure Secret Storage")
    print("=" * 70)
    print()

    manager = SecretManager()

    # 1. Create Secrets
    print("1. CREATE SECRETS:")
    print("-" * 40)

    secret1 = await manager.create_secret(
        name="database-password",
        value="super-secret-password-123",
        secret_type=SecretType.PASSWORD,
        description="Production database password",
        tags=["production", "database"]
    )

    print(f"   Created: {secret1.name}")
    print(f"   Type: {secret1.secret_type.value}")
    print(f"   ID: {secret1.id[:8]}...")

    await manager.create_secret(
        name="api-key",
        value="bael_live_abcdef123456",
        secret_type=SecretType.API_KEY,
        tags=["api", "external"]
    )

    print(f"   Created: api-key")
    print()

    # 2. Retrieve Secrets
    print("2. RETRIEVE SECRETS:")
    print("-" * 40)

    password = await manager.get_secret("database-password")

    print(f"   database-password: {manager.mask_value(password)}")

    api_key = await manager.get_secret("api-key")
    print(f"   api-key: {manager.mask_value(api_key)}")
    print()

    # 3. Secret Generation
    print("3. SECRET GENERATION:")
    print("-" * 40)

    generated_password = SecretGenerator.generate_password(length=20)
    print(f"   Password: {generated_password}")

    generated_api_key = SecretGenerator.generate_api_key()
    print(f"   API Key: {generated_api_key[:30]}...")

    generated_token = SecretGenerator.generate_token()
    print(f"   Token: {generated_token[:30]}...")
    print()

    # 4. Secret Versioning
    print("4. SECRET VERSIONING:")
    print("-" * 40)

    secret = await manager.update_secret("database-password", "new-password-456")

    print(f"   Versions: {len(secret.versions)}")
    for i, v in enumerate(secret.versions):
        print(f"   v{i+1}: {v.version_id[:8]}... (current: {v.is_current})")
    print()

    # 5. Secret Rotation
    print("5. SECRET ROTATION:")
    print("-" * 40)

    await manager.create_secret(
        name="rotating-secret",
        value="old-value",
        secret_type=SecretType.TOKEN
    )

    old_value = await manager.get_secret("rotating-secret")
    print(f"   Before rotation: {old_value}")

    await manager.rotate_secret("rotating-secret")

    new_value = await manager.get_secret("rotating-secret")
    print(f"   After rotation: {new_value[:20]}...")
    print()

    # 6. Access Control
    print("6. ACCESS CONTROL:")
    print("-" * 40)

    await manager.grant_access(
        principal="service-a",
        secret_pattern="database-*",
        levels=[AccessLevel.READ]
    )

    await manager.grant_access(
        principal="admin",
        secret_pattern="*",
        levels=[AccessLevel.READ, AccessLevel.WRITE, AccessLevel.ADMIN]
    )

    has_read = manager.check_access("service-a", "database-password", AccessLevel.READ)
    has_write = manager.check_access("service-a", "database-password", AccessLevel.WRITE)

    print(f"   service-a read database-password: {has_read}")
    print(f"   service-a write database-password: {has_write}")
    print()

    # 7. Audit Logging
    print("7. AUDIT LOG:")
    print("-" * 40)

    audit_entries = await manager.get_audit_log(limit=5)

    for entry in audit_entries[:5]:
        print(f"   [{entry.action.value:8}] {entry.secret_id[:20]}... by {entry.principal}")
    print()

    # 8. Secret Expiration
    print("8. SECRET EXPIRATION:")
    print("-" * 40)

    expiring = await manager.create_secret(
        name="temp-token",
        value="temporary-access",
        expires_in_days=7
    )

    print(f"   Created: {expiring.name}")
    print(f"   Expires: {expiring.metadata.expires_at.isoformat()}")
    print()

    # 9. List Secrets
    print("9. LIST SECRETS:")
    print("-" * 40)

    secrets_list = manager.list_secrets()

    for s in secrets_list:
        print(f"   {s['name']}: {s['type']} ({s['versions']} versions)")
    print()

    # 10. Environment Export
    print("10. ENVIRONMENT EXPORT:")
    print("-" * 40)

    env_dict = manager.get_environment_dict(prefix="BAEL_")

    for key in list(env_dict.keys())[:3]:
        value = env_dict[key]
        print(f"   {key}={manager.mask_value(value)}")
    print()

    # 11. Key Derivation
    print("11. KEY DERIVATION:")
    print("-" * 40)

    salt = KeyDerivation.generate_salt()
    derived = KeyDerivation.derive_key("my-password", salt)

    print(f"   Salt: {base64.b64encode(salt).decode()[:20]}...")
    print(f"   Derived key: {base64.b64encode(derived).decode()[:20]}...")
    print()

    # 12. Encryption Demo
    print("12. ENCRYPTION:")
    print("-" * 40)

    key = KeyDerivation.generate_key()
    encryptor = FernetLikeEncryptor(key)

    plaintext = b"Hello, BAEL!"
    ciphertext = encryptor.encrypt(plaintext)
    decrypted = encryptor.decrypt(ciphertext)

    print(f"   Plaintext: {plaintext.decode()}")
    print(f"   Ciphertext: {base64.b64encode(ciphertext).decode()[:30]}...")
    print(f"   Decrypted: {decrypted.decode()}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Secret Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
