#!/usr/bin/env python3
"""
BAEL - Secret Vault Manager
Comprehensive secrets management and secure credential storage.

Features:
- Secure secret storage
- Encryption/decryption
- Secret versioning
- Access control
- Rotation policies
- Audit logging
- Dynamic secrets
- Lease management
- Secret sharing
- Key derivation
"""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import secrets as crypto_secrets
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import (Any, Awaitable, Callable, Dict, Generic, List, Optional,
                    Set, Tuple, TypeVar, Union)

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class SecretType(Enum):
    """Secret types."""
    PASSWORD = "password"
    API_KEY = "api_key"
    TOKEN = "token"
    CERTIFICATE = "certificate"
    SSH_KEY = "ssh_key"
    DATABASE = "database"
    OAUTH = "oauth"
    ENCRYPTION_KEY = "encryption_key"
    GENERIC = "generic"


class SecretStatus(Enum):
    """Secret status."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    ROTATING = "rotating"


class RotationPolicy(Enum):
    """Rotation policies."""
    NONE = "none"
    MANUAL = "manual"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class AccessLevel(Enum):
    """Access levels."""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


class AuditAction(Enum):
    """Audit actions."""
    READ = "read"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    ROTATE = "rotate"
    REVOKE = "revoke"
    ACCESS_DENIED = "access_denied"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class SecretMetadata:
    """Secret metadata."""
    secret_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    path: str = ""
    secret_type: SecretType = SecretType.GENERIC
    status: SecretStatus = SecretStatus.ACTIVE
    version: int = 1
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    rotation_policy: RotationPolicy = RotationPolicy.NONE
    next_rotation: float = 0.0
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        if self.expires_at == 0.0:
            return False
        return time.time() > self.expires_at


@dataclass
class Secret:
    """Secret entry."""
    metadata: SecretMetadata
    value: str = ""  # Encrypted value
    encrypted: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "secret_id": self.metadata.secret_id,
            "name": self.metadata.name,
            "path": self.metadata.path,
            "type": self.metadata.secret_type.value,
            "status": self.metadata.status.value,
            "version": self.metadata.version,
            "created_at": self.metadata.created_at,
            "expires_at": self.metadata.expires_at
        }


@dataclass
class SecretVersion:
    """Secret version."""
    version: int = 1
    value: str = ""
    created_at: float = field(default_factory=time.time)
    created_by: str = ""
    active: bool = True


@dataclass
class AccessPolicy:
    """Access policy."""
    policy_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    path_pattern: str = "*"
    subjects: List[str] = field(default_factory=list)
    permissions: List[AccessLevel] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Lease:
    """Secret lease."""
    lease_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    secret_path: str = ""
    client_id: str = ""
    ttl: int = 3600
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    renewable: bool = True

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def __post_init__(self):
        if self.expires_at == 0.0:
            self.expires_at = self.created_at + self.ttl


@dataclass
class AuditEntry:
    """Audit entry."""
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    action: AuditAction = AuditAction.READ
    path: str = ""
    client_id: str = ""
    client_ip: str = ""
    success: bool = True
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EncryptionConfig:
    """Encryption configuration."""
    algorithm: str = "AES-256-GCM"
    key_derivation: str = "PBKDF2"
    iterations: int = 100000
    salt_length: int = 32


# =============================================================================
# ENCRYPTION ENGINE
# =============================================================================

class EncryptionEngine:
    """
    Simple encryption engine for secrets.
    In production, use proper cryptographic libraries.
    """

    def __init__(self, master_key: str = None):
        self.master_key = master_key or self._generate_key()
        self.salt = crypto_secrets.token_bytes(32)
        self._derived_key = self._derive_key(self.master_key, self.salt)

    @staticmethod
    def _generate_key() -> str:
        """Generate random master key."""
        return crypto_secrets.token_hex(32)

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key."""
        return hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            salt,
            100000,
            dklen=32
        )

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext."""
        # Simple XOR encryption for demo
        # In production, use AES-GCM or ChaCha20-Poly1305

        nonce = crypto_secrets.token_bytes(12)

        plaintext_bytes = plaintext.encode()
        key_stream = self._generate_keystream(nonce, len(plaintext_bytes))

        encrypted = bytes(
            a ^ b for a, b in zip(plaintext_bytes, key_stream)
        )

        combined = nonce + encrypted

        return base64.b64encode(combined).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext."""
        combined = base64.b64decode(ciphertext.encode())

        nonce = combined[:12]
        encrypted = combined[12:]

        key_stream = self._generate_keystream(nonce, len(encrypted))

        decrypted = bytes(
            a ^ b for a, b in zip(encrypted, key_stream)
        )

        return decrypted.decode()

    def _generate_keystream(self, nonce: bytes, length: int) -> bytes:
        """Generate keystream for encryption."""
        blocks = []
        block_count = (length // 32) + 1

        for i in range(block_count):
            block_input = self._derived_key + nonce + i.to_bytes(4, 'big')
            block = hashlib.sha256(block_input).digest()
            blocks.append(block)

        return b''.join(blocks)[:length]

    def generate_secret(self, length: int = 32) -> str:
        """Generate random secret."""
        return crypto_secrets.token_urlsafe(length)

    def hash_secret(self, value: str) -> str:
        """Hash a secret value."""
        return hashlib.sha256(value.encode()).hexdigest()


# =============================================================================
# SECRET STORE
# =============================================================================

class SecretStore(ABC):
    """Abstract secret store."""

    @abstractmethod
    async def store(self, path: str, secret: Secret) -> bool:
        pass

    @abstractmethod
    async def retrieve(self, path: str) -> Optional[Secret]:
        pass

    @abstractmethod
    async def delete(self, path: str) -> bool:
        pass

    @abstractmethod
    async def list_paths(self, prefix: str = "") -> List[str]:
        pass


class InMemorySecretStore(SecretStore):
    """In-memory secret store."""

    def __init__(self):
        self._secrets: Dict[str, Secret] = {}
        self._versions: Dict[str, List[SecretVersion]] = defaultdict(list)

    async def store(self, path: str, secret: Secret) -> bool:
        """Store secret."""
        # Save version
        version = SecretVersion(
            version=secret.metadata.version,
            value=secret.value,
            created_at=time.time()
        )

        self._versions[path].append(version)
        self._secrets[path] = secret

        return True

    async def retrieve(self, path: str) -> Optional[Secret]:
        """Retrieve secret."""
        return self._secrets.get(path)

    async def delete(self, path: str) -> bool:
        """Delete secret."""
        if path in self._secrets:
            del self._secrets[path]

            if path in self._versions:
                del self._versions[path]

            return True

        return False

    async def list_paths(self, prefix: str = "") -> List[str]:
        """List secret paths."""
        if not prefix:
            return list(self._secrets.keys())

        return [
            path for path in self._secrets.keys()
            if path.startswith(prefix)
        ]

    async def get_versions(self, path: str) -> List[SecretVersion]:
        """Get all versions of a secret."""
        return self._versions.get(path, [])


# =============================================================================
# POLICY ENGINE
# =============================================================================

class PolicyEngine:
    """Access policy engine."""

    def __init__(self):
        self._policies: Dict[str, AccessPolicy] = {}

    def add_policy(self, policy: AccessPolicy) -> str:
        """Add access policy."""
        self._policies[policy.policy_id] = policy
        return policy.policy_id

    def remove_policy(self, policy_id: str) -> bool:
        """Remove policy."""
        if policy_id in self._policies:
            del self._policies[policy_id]
            return True
        return False

    def check_access(
        self,
        subject: str,
        path: str,
        action: AccessLevel
    ) -> bool:
        """Check if subject has access."""
        for policy in self._policies.values():
            if self._matches_policy(policy, subject, path, action):
                return True

        return False

    def _matches_policy(
        self,
        policy: AccessPolicy,
        subject: str,
        path: str,
        action: AccessLevel
    ) -> bool:
        """Check if policy matches request."""
        # Check subject
        if policy.subjects and subject not in policy.subjects:
            if "*" not in policy.subjects:
                return False

        # Check path pattern
        if not self._matches_pattern(policy.path_pattern, path):
            return False

        # Check permission
        if action not in policy.permissions:
            return False

        return True

    def _matches_pattern(self, pattern: str, path: str) -> bool:
        """Match path against pattern."""
        import fnmatch
        return fnmatch.fnmatch(path, pattern)


# =============================================================================
# AUDIT LOGGER
# =============================================================================

class VaultAuditLogger:
    """Vault audit logger."""

    def __init__(self, max_entries: int = 10000):
        self._entries: List[AuditEntry] = []
        self._max_entries = max_entries

    def log(
        self,
        action: AuditAction,
        path: str,
        client_id: str,
        client_ip: str = "",
        success: bool = True,
        details: Dict[str, Any] = None
    ) -> str:
        """Log audit entry."""
        entry = AuditEntry(
            action=action,
            path=path,
            client_id=client_id,
            client_ip=client_ip,
            success=success,
            details=details or {}
        )

        self._entries.append(entry)

        # Trim old entries
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]

        return entry.entry_id

    def get_entries(
        self,
        path: str = None,
        client_id: str = None,
        action: AuditAction = None,
        limit: int = 100
    ) -> List[AuditEntry]:
        """Get audit entries."""
        entries = self._entries

        if path:
            entries = [e for e in entries if e.path == path]

        if client_id:
            entries = [e for e in entries if e.client_id == client_id]

        if action:
            entries = [e for e in entries if e.action == action]

        return entries[-limit:]

    def get_failed_accesses(self, hours: int = 24) -> List[AuditEntry]:
        """Get failed access attempts."""
        cutoff = time.time() - (hours * 3600)

        return [
            e for e in self._entries
            if not e.success and e.timestamp > cutoff
        ]


# =============================================================================
# SECRET VAULT
# =============================================================================

class SecretVault:
    """
    Comprehensive Secret Vault Manager for BAEL.
    """

    def __init__(self, master_key: str = None):
        self.encryption = EncryptionEngine(master_key)
        self.store = InMemorySecretStore()
        self.policy_engine = PolicyEngine()
        self.audit = VaultAuditLogger()
        self._leases: Dict[str, Lease] = {}
        self._rotation_callbacks: Dict[str, Callable] = {}

    # -------------------------------------------------------------------------
    # SECRET MANAGEMENT
    # -------------------------------------------------------------------------

    async def create_secret(
        self,
        path: str,
        value: str,
        secret_type: SecretType = SecretType.GENERIC,
        expires_in: int = 0,
        rotation_policy: RotationPolicy = RotationPolicy.NONE,
        tags: Dict[str, str] = None,
        client_id: str = "system"
    ) -> SecretMetadata:
        """Create a new secret."""
        # Check if exists
        existing = await self.store.retrieve(path)

        if existing:
            raise ValueError(f"Secret already exists at {path}")

        # Encrypt value
        encrypted_value = self.encryption.encrypt(value)

        # Calculate expiration
        expires_at = time.time() + expires_in if expires_in > 0 else 0.0

        # Calculate next rotation
        next_rotation = self._calculate_next_rotation(rotation_policy)

        metadata = SecretMetadata(
            name=path.split("/")[-1],
            path=path,
            secret_type=secret_type,
            expires_at=expires_at,
            rotation_policy=rotation_policy,
            next_rotation=next_rotation,
            tags=tags or {}
        )

        secret = Secret(
            metadata=metadata,
            value=encrypted_value,
            encrypted=True
        )

        await self.store.store(path, secret)

        self.audit.log(
            AuditAction.CREATE,
            path,
            client_id,
            success=True,
            details={"type": secret_type.value}
        )

        return metadata

    async def read_secret(
        self,
        path: str,
        client_id: str = "system",
        client_ip: str = ""
    ) -> Optional[str]:
        """Read a secret value."""
        # Check access
        if not self.policy_engine.check_access(client_id, path, AccessLevel.READ):
            self.audit.log(
                AuditAction.ACCESS_DENIED,
                path,
                client_id,
                client_ip,
                success=False
            )
            return None

        secret = await self.store.retrieve(path)

        if not secret:
            return None

        if secret.metadata.is_expired:
            self.audit.log(
                AuditAction.READ,
                path,
                client_id,
                client_ip,
                success=False,
                details={"reason": "expired"}
            )
            return None

        if secret.metadata.status != SecretStatus.ACTIVE:
            return None

        # Decrypt value
        value = self.encryption.decrypt(secret.value)

        self.audit.log(
            AuditAction.READ,
            path,
            client_id,
            client_ip,
            success=True
        )

        return value

    async def update_secret(
        self,
        path: str,
        value: str,
        client_id: str = "system"
    ) -> Optional[SecretMetadata]:
        """Update a secret value."""
        # Check access
        if not self.policy_engine.check_access(client_id, path, AccessLevel.WRITE):
            self.audit.log(
                AuditAction.ACCESS_DENIED,
                path,
                client_id,
                success=False
            )
            return None

        secret = await self.store.retrieve(path)

        if not secret:
            return None

        # Encrypt new value
        encrypted_value = self.encryption.encrypt(value)

        # Update metadata
        secret.metadata.version += 1
        secret.metadata.updated_at = time.time()
        secret.value = encrypted_value

        await self.store.store(path, secret)

        self.audit.log(
            AuditAction.UPDATE,
            path,
            client_id,
            success=True,
            details={"version": secret.metadata.version}
        )

        return secret.metadata

    async def delete_secret(
        self,
        path: str,
        client_id: str = "system"
    ) -> bool:
        """Delete a secret."""
        # Check access
        if not self.policy_engine.check_access(client_id, path, AccessLevel.ADMIN):
            self.audit.log(
                AuditAction.ACCESS_DENIED,
                path,
                client_id,
                success=False
            )
            return False

        result = await self.store.delete(path)

        if result:
            # Revoke leases
            self._revoke_leases_for_path(path)

            self.audit.log(
                AuditAction.DELETE,
                path,
                client_id,
                success=True
            )

        return result

    async def rotate_secret(
        self,
        path: str,
        new_value: str = None,
        client_id: str = "system"
    ) -> Optional[SecretMetadata]:
        """Rotate a secret."""
        secret = await self.store.retrieve(path)

        if not secret:
            return None

        # Generate new value if not provided
        if new_value is None:
            new_value = self.encryption.generate_secret()

        # Mark as rotating
        secret.metadata.status = SecretStatus.ROTATING

        # Encrypt and update
        encrypted_value = self.encryption.encrypt(new_value)
        secret.value = encrypted_value
        secret.metadata.version += 1
        secret.metadata.updated_at = time.time()
        secret.metadata.next_rotation = self._calculate_next_rotation(
            secret.metadata.rotation_policy
        )
        secret.metadata.status = SecretStatus.ACTIVE

        await self.store.store(path, secret)

        # Call rotation callback if registered
        if path in self._rotation_callbacks:
            try:
                self._rotation_callbacks[path](path, new_value)
            except Exception as e:
                logger.error(f"Rotation callback failed: {e}")

        self.audit.log(
            AuditAction.ROTATE,
            path,
            client_id,
            success=True,
            details={"version": secret.metadata.version}
        )

        return secret.metadata

    async def revoke_secret(
        self,
        path: str,
        client_id: str = "system"
    ) -> bool:
        """Revoke a secret."""
        secret = await self.store.retrieve(path)

        if not secret:
            return False

        secret.metadata.status = SecretStatus.REVOKED
        await self.store.store(path, secret)

        # Revoke leases
        self._revoke_leases_for_path(path)

        self.audit.log(
            AuditAction.REVOKE,
            path,
            client_id,
            success=True
        )

        return True

    # -------------------------------------------------------------------------
    # SECRET LISTING
    # -------------------------------------------------------------------------

    async def list_secrets(
        self,
        prefix: str = "",
        client_id: str = "system"
    ) -> List[SecretMetadata]:
        """List secrets."""
        paths = await self.store.list_paths(prefix)

        results = []

        for path in paths:
            if self.policy_engine.check_access(client_id, path, AccessLevel.READ):
                secret = await self.store.retrieve(path)

                if secret:
                    results.append(secret.metadata)

        return results

    async def get_metadata(
        self,
        path: str,
        client_id: str = "system"
    ) -> Optional[SecretMetadata]:
        """Get secret metadata without value."""
        if not self.policy_engine.check_access(client_id, path, AccessLevel.READ):
            return None

        secret = await self.store.retrieve(path)

        if secret:
            return secret.metadata

        return None

    async def get_versions(
        self,
        path: str,
        client_id: str = "system"
    ) -> List[SecretVersion]:
        """Get secret versions."""
        if not self.policy_engine.check_access(client_id, path, AccessLevel.READ):
            return []

        return await self.store.get_versions(path)

    # -------------------------------------------------------------------------
    # LEASE MANAGEMENT
    # -------------------------------------------------------------------------

    async def create_lease(
        self,
        path: str,
        client_id: str,
        ttl: int = 3600
    ) -> Optional[Lease]:
        """Create a lease for secret access."""
        secret = await self.store.retrieve(path)

        if not secret:
            return None

        if not self.policy_engine.check_access(client_id, path, AccessLevel.READ):
            return None

        lease = Lease(
            secret_path=path,
            client_id=client_id,
            ttl=ttl
        )

        self._leases[lease.lease_id] = lease

        return lease

    def renew_lease(self, lease_id: str, ttl: int = 3600) -> Optional[Lease]:
        """Renew a lease."""
        lease = self._leases.get(lease_id)

        if not lease or not lease.renewable:
            return None

        if lease.is_expired:
            del self._leases[lease_id]
            return None

        lease.expires_at = time.time() + ttl

        return lease

    def revoke_lease(self, lease_id: str) -> bool:
        """Revoke a lease."""
        if lease_id in self._leases:
            del self._leases[lease_id]
            return True
        return False

    def _revoke_leases_for_path(self, path: str) -> int:
        """Revoke all leases for a path."""
        revoked = 0

        lease_ids = [
            lid for lid, lease in self._leases.items()
            if lease.secret_path == path
        ]

        for lid in lease_ids:
            del self._leases[lid]
            revoked += 1

        return revoked

    def get_active_leases(self) -> List[Lease]:
        """Get all active leases."""
        now = time.time()

        active = []
        expired_ids = []

        for lid, lease in self._leases.items():
            if lease.is_expired:
                expired_ids.append(lid)
            else:
                active.append(lease)

        # Clean up expired
        for lid in expired_ids:
            del self._leases[lid]

        return active

    # -------------------------------------------------------------------------
    # POLICY MANAGEMENT
    # -------------------------------------------------------------------------

    def create_policy(
        self,
        name: str,
        path_pattern: str,
        subjects: List[str],
        permissions: List[AccessLevel]
    ) -> str:
        """Create access policy."""
        policy = AccessPolicy(
            name=name,
            path_pattern=path_pattern,
            subjects=subjects,
            permissions=permissions
        )

        return self.policy_engine.add_policy(policy)

    def delete_policy(self, policy_id: str) -> bool:
        """Delete access policy."""
        return self.policy_engine.remove_policy(policy_id)

    # -------------------------------------------------------------------------
    # ROTATION MANAGEMENT
    # -------------------------------------------------------------------------

    def register_rotation_callback(
        self,
        path: str,
        callback: Callable[[str, str], None]
    ) -> None:
        """Register rotation callback."""
        self._rotation_callbacks[path] = callback

    def _calculate_next_rotation(
        self,
        policy: RotationPolicy
    ) -> float:
        """Calculate next rotation time."""
        if policy == RotationPolicy.NONE:
            return 0.0

        now = time.time()

        intervals = {
            RotationPolicy.DAILY: 86400,
            RotationPolicy.WEEKLY: 604800,
            RotationPolicy.MONTHLY: 2592000,
            RotationPolicy.QUARTERLY: 7776000
        }

        interval = intervals.get(policy, 0)

        return now + interval if interval > 0 else 0.0

    async def check_rotation_due(self) -> List[str]:
        """Check for secrets due for rotation."""
        paths = await self.store.list_paths()
        due_for_rotation = []

        now = time.time()

        for path in paths:
            secret = await self.store.retrieve(path)

            if secret:
                if secret.metadata.next_rotation > 0:
                    if now >= secret.metadata.next_rotation:
                        due_for_rotation.append(path)

        return due_for_rotation

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def generate_secret(
        self,
        length: int = 32,
        secret_type: SecretType = SecretType.GENERIC
    ) -> str:
        """Generate a random secret."""
        if secret_type == SecretType.PASSWORD:
            # Include special characters
            alphabet = (
                "abcdefghijklmnopqrstuvwxyz"
                "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                "0123456789"
                "!@#$%^&*()_+-="
            )
            return ''.join(
                crypto_secrets.choice(alphabet)
                for _ in range(length)
            )

        if secret_type == SecretType.API_KEY:
            return f"bael_{crypto_secrets.token_urlsafe(length)}"

        return crypto_secrets.token_urlsafe(length)

    def hash_value(self, value: str) -> str:
        """Hash a value."""
        return self.encryption.hash_secret(value)

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    async def get_stats(self) -> Dict[str, Any]:
        """Get vault statistics."""
        paths = await self.store.list_paths()

        type_counts: Dict[str, int] = defaultdict(int)
        status_counts: Dict[str, int] = defaultdict(int)

        for path in paths:
            secret = await self.store.retrieve(path)

            if secret:
                type_counts[secret.metadata.secret_type.value] += 1
                status_counts[secret.metadata.status.value] += 1

        return {
            "total_secrets": len(paths),
            "active_leases": len(self.get_active_leases()),
            "secrets_by_type": dict(type_counts),
            "secrets_by_status": dict(status_counts),
            "audit_entries": len(self.audit._entries)
        }


# =============================================================================
# SECRET VAULT BUILDER
# =============================================================================

class SecretVaultBuilder:
    """Fluent builder for SecretVault."""

    def __init__(self):
        self._master_key: Optional[str] = None
        self._policies: List[AccessPolicy] = []

    def with_master_key(self, key: str) -> 'SecretVaultBuilder':
        """Set master key."""
        self._master_key = key
        return self

    def with_policy(
        self,
        name: str,
        path_pattern: str,
        subjects: List[str],
        permissions: List[AccessLevel]
    ) -> 'SecretVaultBuilder':
        """Add access policy."""
        policy = AccessPolicy(
            name=name,
            path_pattern=path_pattern,
            subjects=subjects,
            permissions=permissions
        )
        self._policies.append(policy)
        return self

    def build(self) -> SecretVault:
        """Build vault."""
        vault = SecretVault(self._master_key)

        for policy in self._policies:
            vault.policy_engine.add_policy(policy)

        return vault


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Secret Vault System."""
    print("=" * 70)
    print("BAEL - SECRET VAULT MANAGER DEMO")
    print("Comprehensive Secrets Management System")
    print("=" * 70)
    print()

    # Build vault with policies
    vault = (
        SecretVaultBuilder()
        .with_master_key("super-secret-master-key-12345")
        .with_policy(
            "admin-all",
            "*",
            ["admin"],
            [AccessLevel.READ, AccessLevel.WRITE, AccessLevel.ADMIN]
        )
        .with_policy(
            "users-read",
            "secrets/*",
            ["user1", "user2"],
            [AccessLevel.READ]
        )
        .with_policy(
            "service-db",
            "secrets/database/*",
            ["service-app"],
            [AccessLevel.READ]
        )
        .build()
    )

    # 1. Create Secrets
    print("1. CREATE SECRETS:")
    print("-" * 40)

    secrets_to_create = [
        ("secrets/database/main", "db_password_123!", SecretType.PASSWORD),
        ("secrets/api/external", "ext_api_key_xyz", SecretType.API_KEY),
        ("secrets/tokens/jwt", "jwt_secret_key", SecretType.TOKEN),
        ("secrets/oauth/google", "google_oauth_secret", SecretType.OAUTH),
    ]

    for path, value, secret_type in secrets_to_create:
        metadata = await vault.create_secret(
            path=path,
            value=value,
            secret_type=secret_type,
            client_id="admin"
        )
        print(f"   Created: {path}")
        print(f"      ID: {metadata.secret_id[:8]}...")
        print(f"      Type: {metadata.secret_type.value}")
    print()

    # 2. Read Secrets
    print("2. READ SECRETS:")
    print("-" * 40)

    value = await vault.read_secret(
        "secrets/database/main",
        client_id="admin"
    )
    print(f"   Path: secrets/database/main")
    print(f"   Value: {value}")

    # Access by allowed user
    value = await vault.read_secret(
        "secrets/database/main",
        client_id="service-app"
    )
    print(f"   Service-app access: {value is not None}")

    # Access denied for unauthorized user
    value = await vault.read_secret(
        "secrets/database/main",
        client_id="unauthorized"
    )
    print(f"   Unauthorized access: {value is None} (expected)")
    print()

    # 3. Update Secrets
    print("3. UPDATE SECRETS:")
    print("-" * 40)

    metadata = await vault.update_secret(
        "secrets/database/main",
        "new_db_password_456!",
        client_id="admin"
    )

    print(f"   Updated: secrets/database/main")
    print(f"   New version: {metadata.version}")

    value = await vault.read_secret(
        "secrets/database/main",
        client_id="admin"
    )
    print(f"   New value: {value}")
    print()

    # 4. Secret with Expiration
    print("4. SECRET WITH EXPIRATION:")
    print("-" * 40)

    metadata = await vault.create_secret(
        path="secrets/temp/token",
        value="temporary_token_123",
        secret_type=SecretType.TOKEN,
        expires_in=3600,  # 1 hour
        client_id="admin"
    )

    print(f"   Created: secrets/temp/token")
    print(f"   Expires: {datetime.fromtimestamp(metadata.expires_at)}")
    print(f"   Is expired: {metadata.is_expired}")
    print()

    # 5. Secret Rotation
    print("5. SECRET ROTATION:")
    print("-" * 40)

    # Register rotation callback
    def on_rotation(path: str, new_value: str):
        print(f"      Callback: {path} rotated!")

    vault.register_rotation_callback(
        "secrets/api/external",
        on_rotation
    )

    metadata = await vault.rotate_secret(
        "secrets/api/external",
        client_id="admin"
    )

    print(f"   Rotated: secrets/api/external")
    print(f"   New version: {metadata.version}")

    new_value = await vault.read_secret(
        "secrets/api/external",
        client_id="admin"
    )
    print(f"   New value: {new_value[:20]}...")
    print()

    # 6. Create Lease
    print("6. LEASE MANAGEMENT:")
    print("-" * 40)

    lease = await vault.create_lease(
        "secrets/database/main",
        client_id="service-app",
        ttl=3600
    )

    print(f"   Lease ID: {lease.lease_id[:8]}...")
    print(f"   Path: {lease.secret_path}")
    print(f"   TTL: {lease.ttl}s")
    print(f"   Renewable: {lease.renewable}")

    # Renew lease
    renewed = vault.renew_lease(lease.lease_id, 7200)
    print(f"   Renewed: {renewed is not None}")

    active_leases = vault.get_active_leases()
    print(f"   Active leases: {len(active_leases)}")
    print()

    # 7. Generate Secrets
    print("7. GENERATE SECRETS:")
    print("-" * 40)

    password = vault.generate_secret(16, SecretType.PASSWORD)
    print(f"   Password: {password}")

    api_key = vault.generate_secret(24, SecretType.API_KEY)
    print(f"   API Key: {api_key}")

    token = vault.generate_secret(32, SecretType.TOKEN)
    print(f"   Token: {token}")
    print()

    # 8. List Secrets
    print("8. LIST SECRETS:")
    print("-" * 40)

    secrets = await vault.list_secrets("secrets/", client_id="admin")

    print(f"   Found {len(secrets)} secrets:")

    for meta in secrets:
        print(f"      - {meta.path} ({meta.secret_type.value})")
    print()

    # 9. Secret Versions
    print("9. SECRET VERSIONS:")
    print("-" * 40)

    versions = await vault.get_versions(
        "secrets/database/main",
        client_id="admin"
    )

    print(f"   Versions for secrets/database/main:")

    for version in versions:
        print(f"      v{version.version} - {datetime.fromtimestamp(version.created_at)}")
    print()

    # 10. Revoke Secret
    print("10. REVOKE SECRET:")
    print("-" * 40)

    revoked = await vault.revoke_secret(
        "secrets/temp/token",
        client_id="admin"
    )

    print(f"   Revoked secrets/temp/token: {revoked}")

    value = await vault.read_secret(
        "secrets/temp/token",
        client_id="admin"
    )
    print(f"   Read after revoke: {value is None} (expected None)")
    print()

    # 11. Audit Log
    print("11. AUDIT LOG:")
    print("-" * 40)

    entries = vault.audit.get_entries(limit=5)

    print(f"   Last 5 audit entries:")

    for entry in entries:
        status = "✓" if entry.success else "✗"
        print(f"      [{status}] {entry.action.value}: {entry.path}")

    failed = vault.audit.get_failed_accesses()
    print(f"   Failed accesses (24h): {len(failed)}")
    print()

    # 12. Vault Statistics
    print("12. VAULT STATISTICS:")
    print("-" * 40)

    stats = await vault.get_stats()

    print(f"   Total secrets: {stats['total_secrets']}")
    print(f"   Active leases: {stats['active_leases']}")
    print(f"   Audit entries: {stats['audit_entries']}")
    print(f"   By type: {dict(stats['secrets_by_type'])}")
    print(f"   By status: {dict(stats['secrets_by_status'])}")
    print()

    # 13. Delete Secret
    print("13. DELETE SECRET:")
    print("-" * 40)

    deleted = await vault.delete_secret(
        "secrets/oauth/google",
        client_id="admin"
    )

    print(f"   Deleted secrets/oauth/google: {deleted}")

    secrets = await vault.list_secrets("secrets/", client_id="admin")
    print(f"   Remaining secrets: {len(secrets)}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Secret Vault System Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
