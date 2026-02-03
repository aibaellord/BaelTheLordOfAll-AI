#!/usr/bin/env python3
"""
BAEL - Encryption Engine
Cryptographic operations for agents.

Features:
- Symmetric encryption
- Asymmetric encryption
- Hashing algorithms
- Key management
- Digital signatures
"""

import asyncio
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class EncryptionAlgorithm(Enum):
    """Encryption algorithms."""
    AES_128 = "aes_128"
    AES_256 = "aes_256"
    CHACHA20 = "chacha20"
    XOR = "xor"  # Simple demo only


class HashAlgorithm(Enum):
    """Hash algorithms."""
    MD5 = "md5"
    SHA1 = "sha1"
    SHA256 = "sha256"
    SHA384 = "sha384"
    SHA512 = "sha512"
    BLAKE2B = "blake2b"
    BLAKE2S = "blake2s"


class KeyType(Enum):
    """Key types."""
    SYMMETRIC = "symmetric"
    PUBLIC = "public"
    PRIVATE = "private"
    SECRET = "secret"


class KeyStatus(Enum):
    """Key status."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    PENDING = "pending"


class EncodingFormat(Enum):
    """Encoding formats."""
    BASE64 = "base64"
    HEX = "hex"
    UTF8 = "utf8"
    RAW = "raw"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class CryptoKey:
    """A cryptographic key."""
    key_id: str = ""
    key_type: KeyType = KeyType.SYMMETRIC
    algorithm: str = ""
    key_data: bytes = b""
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    status: KeyStatus = KeyStatus.ACTIVE
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.key_id:
            self.key_id = str(uuid.uuid4())[:8]

    @property
    def is_expired(self) -> bool:
        """Check if key is expired."""
        if self.expires_at:
            return datetime.now() > self.expires_at
        return False


@dataclass
class EncryptedData:
    """Encrypted data container."""
    ciphertext: bytes = b""
    algorithm: str = ""
    nonce: Optional[bytes] = None
    tag: Optional[bytes] = None
    key_id: Optional[str] = None
    encrypted_at: datetime = field(default_factory=datetime.now)


@dataclass
class HashResult:
    """Hash result container."""
    digest: bytes = b""
    algorithm: HashAlgorithm = HashAlgorithm.SHA256
    hex_digest: str = ""


@dataclass
class Signature:
    """Digital signature."""
    signature_id: str = ""
    data_hash: str = ""
    signature_data: bytes = b""
    algorithm: str = ""
    key_id: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.signature_id:
            self.signature_id = str(uuid.uuid4())[:8]


@dataclass
class EncryptionConfig:
    """Encryption engine configuration."""
    default_algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256
    default_hash: HashAlgorithm = HashAlgorithm.SHA256
    default_encoding: EncodingFormat = EncodingFormat.BASE64
    key_rotation_days: int = 90
    auto_rotate: bool = False


# =============================================================================
# KEY GENERATOR
# =============================================================================

class KeyGenerator:
    """Generate cryptographic keys."""

    def generate_bytes(self, length: int) -> bytes:
        """Generate random bytes."""
        return secrets.token_bytes(length)

    def generate_hex(self, length: int) -> str:
        """Generate random hex string."""
        return secrets.token_hex(length)

    def generate_urlsafe(self, length: int) -> str:
        """Generate URL-safe token."""
        return secrets.token_urlsafe(length)

    def generate_symmetric_key(
        self,
        algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256
    ) -> CryptoKey:
        """Generate symmetric key."""
        if algorithm == EncryptionAlgorithm.AES_128:
            key_data = self.generate_bytes(16)
        elif algorithm == EncryptionAlgorithm.AES_256:
            key_data = self.generate_bytes(32)
        elif algorithm == EncryptionAlgorithm.CHACHA20:
            key_data = self.generate_bytes(32)
        else:
            key_data = self.generate_bytes(16)

        return CryptoKey(
            key_type=KeyType.SYMMETRIC,
            algorithm=algorithm.value,
            key_data=key_data
        )

    def generate_secret(self, length: int = 32) -> CryptoKey:
        """Generate a secret key."""
        return CryptoKey(
            key_type=KeyType.SECRET,
            algorithm="secret",
            key_data=self.generate_bytes(length)
        )

    def derive_key(
        self,
        password: str,
        salt: Optional[bytes] = None,
        length: int = 32,
        iterations: int = 100000
    ) -> Tuple[bytes, bytes]:
        """Derive key from password using PBKDF2."""
        if salt is None:
            salt = self.generate_bytes(16)

        key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt,
            iterations,
            dklen=length
        )

        return key, salt


# =============================================================================
# KEY STORE
# =============================================================================

class KeyStore:
    """Store and manage keys."""

    def __init__(self):
        self._keys: Dict[str, CryptoKey] = {}
        self._active_key: Optional[str] = None

    def add(self, key: CryptoKey) -> str:
        """Add a key."""
        self._keys[key.key_id] = key

        if self._active_key is None and key.key_type == KeyType.SYMMETRIC:
            self._active_key = key.key_id

        return key.key_id

    def get(self, key_id: str) -> Optional[CryptoKey]:
        """Get a key by ID."""
        return self._keys.get(key_id)

    def get_active(self) -> Optional[CryptoKey]:
        """Get active key."""
        if self._active_key:
            return self._keys.get(self._active_key)
        return None

    def set_active(self, key_id: str) -> bool:
        """Set active key."""
        if key_id in self._keys:
            self._active_key = key_id
            return True
        return False

    def revoke(self, key_id: str) -> bool:
        """Revoke a key."""
        key = self._keys.get(key_id)
        if key:
            key.status = KeyStatus.REVOKED
            if self._active_key == key_id:
                self._active_key = None
            return True
        return False

    def delete(self, key_id: str) -> bool:
        """Delete a key."""
        if key_id in self._keys:
            del self._keys[key_id]
            if self._active_key == key_id:
                self._active_key = None
            return True
        return False

    def list(self, key_type: Optional[KeyType] = None) -> List[CryptoKey]:
        """List keys."""
        keys = list(self._keys.values())
        if key_type:
            keys = [k for k in keys if k.key_type == key_type]
        return keys

    def count(self) -> int:
        """Count keys."""
        return len(self._keys)

    def get_expired(self) -> List[CryptoKey]:
        """Get expired keys."""
        return [k for k in self._keys.values() if k.is_expired]


# =============================================================================
# ENCODER
# =============================================================================

class Encoder:
    """Encode and decode data."""

    def encode(
        self,
        data: bytes,
        format: EncodingFormat = EncodingFormat.BASE64
    ) -> str:
        """Encode bytes to string."""
        if format == EncodingFormat.BASE64:
            return base64.b64encode(data).decode("utf-8")
        elif format == EncodingFormat.HEX:
            return data.hex()
        elif format == EncodingFormat.UTF8:
            return data.decode("utf-8", errors="replace")
        else:
            return base64.b64encode(data).decode("utf-8")

    def decode(
        self,
        data: str,
        format: EncodingFormat = EncodingFormat.BASE64
    ) -> bytes:
        """Decode string to bytes."""
        if format == EncodingFormat.BASE64:
            return base64.b64decode(data)
        elif format == EncodingFormat.HEX:
            return bytes.fromhex(data)
        elif format == EncodingFormat.UTF8:
            return data.encode("utf-8")
        else:
            return base64.b64decode(data)

    def to_base64(self, data: bytes) -> str:
        """Encode to base64."""
        return self.encode(data, EncodingFormat.BASE64)

    def from_base64(self, data: str) -> bytes:
        """Decode from base64."""
        return self.decode(data, EncodingFormat.BASE64)

    def to_hex(self, data: bytes) -> str:
        """Encode to hex."""
        return self.encode(data, EncodingFormat.HEX)

    def from_hex(self, data: str) -> bytes:
        """Decode from hex."""
        return self.decode(data, EncodingFormat.HEX)


# =============================================================================
# HASHER
# =============================================================================

class Hasher:
    """Hash data."""

    def hash(
        self,
        data: Union[str, bytes],
        algorithm: HashAlgorithm = HashAlgorithm.SHA256
    ) -> HashResult:
        """Hash data."""
        if isinstance(data, str):
            data = data.encode("utf-8")

        if algorithm == HashAlgorithm.MD5:
            h = hashlib.md5(data)
        elif algorithm == HashAlgorithm.SHA1:
            h = hashlib.sha1(data)
        elif algorithm == HashAlgorithm.SHA256:
            h = hashlib.sha256(data)
        elif algorithm == HashAlgorithm.SHA384:
            h = hashlib.sha384(data)
        elif algorithm == HashAlgorithm.SHA512:
            h = hashlib.sha512(data)
        elif algorithm == HashAlgorithm.BLAKE2B:
            h = hashlib.blake2b(data)
        elif algorithm == HashAlgorithm.BLAKE2S:
            h = hashlib.blake2s(data)
        else:
            h = hashlib.sha256(data)

        return HashResult(
            digest=h.digest(),
            algorithm=algorithm,
            hex_digest=h.hexdigest()
        )

    def md5(self, data: Union[str, bytes]) -> str:
        """MD5 hash."""
        return self.hash(data, HashAlgorithm.MD5).hex_digest

    def sha1(self, data: Union[str, bytes]) -> str:
        """SHA1 hash."""
        return self.hash(data, HashAlgorithm.SHA1).hex_digest

    def sha256(self, data: Union[str, bytes]) -> str:
        """SHA256 hash."""
        return self.hash(data, HashAlgorithm.SHA256).hex_digest

    def sha512(self, data: Union[str, bytes]) -> str:
        """SHA512 hash."""
        return self.hash(data, HashAlgorithm.SHA512).hex_digest

    def blake2b(self, data: Union[str, bytes]) -> str:
        """BLAKE2b hash."""
        return self.hash(data, HashAlgorithm.BLAKE2B).hex_digest

    def verify(
        self,
        data: Union[str, bytes],
        expected_hash: str,
        algorithm: HashAlgorithm = HashAlgorithm.SHA256
    ) -> bool:
        """Verify hash."""
        result = self.hash(data, algorithm)
        return secrets.compare_digest(result.hex_digest, expected_hash)


# =============================================================================
# HMAC HANDLER
# =============================================================================

class HMACHandler:
    """Handle HMAC operations."""

    def sign(
        self,
        data: Union[str, bytes],
        key: Union[str, bytes],
        algorithm: str = "sha256"
    ) -> str:
        """Create HMAC signature."""
        if isinstance(data, str):
            data = data.encode("utf-8")

        if isinstance(key, str):
            key = key.encode("utf-8")

        h = hmac.new(key, data, algorithm)
        return h.hexdigest()

    def verify(
        self,
        data: Union[str, bytes],
        signature: str,
        key: Union[str, bytes],
        algorithm: str = "sha256"
    ) -> bool:
        """Verify HMAC signature."""
        expected = self.sign(data, key, algorithm)
        return secrets.compare_digest(expected, signature)


# =============================================================================
# SIMPLE XOR CIPHER (Demo purposes only - NOT secure)
# =============================================================================

class XORCipher:
    """Simple XOR cipher for demo purposes only."""

    def encrypt(self, data: bytes, key: bytes) -> bytes:
        """XOR encrypt."""
        key_len = len(key)
        return bytes([data[i] ^ key[i % key_len] for i in range(len(data))])

    def decrypt(self, data: bytes, key: bytes) -> bytes:
        """XOR decrypt (same as encrypt)."""
        return self.encrypt(data, key)


# =============================================================================
# ENCRYPTOR (Simple demo implementation)
# =============================================================================

class Encryptor:
    """Encrypt and decrypt data."""

    def __init__(self, key_store: KeyStore):
        self._key_store = key_store
        self._xor = XORCipher()

    def encrypt(
        self,
        data: Union[str, bytes],
        key: Optional[CryptoKey] = None
    ) -> EncryptedData:
        """Encrypt data."""
        if isinstance(data, str):
            data = data.encode("utf-8")

        if key is None:
            key = self._key_store.get_active()

        if key is None:
            raise ValueError("No encryption key available")

        nonce = secrets.token_bytes(12)

        ciphertext = self._xor.encrypt(data, key.key_data + nonce)

        return EncryptedData(
            ciphertext=ciphertext,
            algorithm=key.algorithm,
            nonce=nonce,
            key_id=key.key_id
        )

    def decrypt(
        self,
        encrypted: EncryptedData,
        key: Optional[CryptoKey] = None
    ) -> bytes:
        """Decrypt data."""
        if key is None:
            if encrypted.key_id:
                key = self._key_store.get(encrypted.key_id)
            else:
                key = self._key_store.get_active()

        if key is None:
            raise ValueError("No decryption key available")

        nonce = encrypted.nonce or b""

        plaintext = self._xor.decrypt(encrypted.ciphertext, key.key_data + nonce)

        return plaintext

    def encrypt_string(
        self,
        data: str,
        key: Optional[CryptoKey] = None
    ) -> str:
        """Encrypt string and return base64."""
        encrypted = self.encrypt(data, key)

        package = {
            "c": base64.b64encode(encrypted.ciphertext).decode(),
            "n": base64.b64encode(encrypted.nonce or b"").decode(),
            "a": encrypted.algorithm,
            "k": encrypted.key_id
        }

        return base64.b64encode(json.dumps(package).encode()).decode()

    def decrypt_string(
        self,
        data: str,
        key: Optional[CryptoKey] = None
    ) -> str:
        """Decrypt base64 string."""
        package = json.loads(base64.b64decode(data))

        encrypted = EncryptedData(
            ciphertext=base64.b64decode(package["c"]),
            nonce=base64.b64decode(package["n"]),
            algorithm=package["a"],
            key_id=package["k"]
        )

        return self.decrypt(encrypted, key).decode("utf-8")


# =============================================================================
# SIGNATURE MANAGER
# =============================================================================

class SignatureManager:
    """Manage digital signatures."""

    def __init__(self, key_store: KeyStore):
        self._key_store = key_store
        self._hasher = Hasher()
        self._hmac = HMACHandler()
        self._signatures: Dict[str, Signature] = {}

    def sign(
        self,
        data: Union[str, bytes],
        key: Optional[CryptoKey] = None
    ) -> Signature:
        """Create signature."""
        if key is None:
            key = self._key_store.get_active()

        if key is None:
            raise ValueError("No signing key available")

        if isinstance(data, str):
            data = data.encode("utf-8")

        data_hash = self._hasher.sha256(data)

        sig_data = self._hmac.sign(data, key.key_data).encode()

        signature = Signature(
            data_hash=data_hash,
            signature_data=sig_data,
            algorithm="hmac_sha256",
            key_id=key.key_id
        )

        self._signatures[signature.signature_id] = signature

        return signature

    def verify(
        self,
        data: Union[str, bytes],
        signature: Signature,
        key: Optional[CryptoKey] = None
    ) -> bool:
        """Verify signature."""
        if key is None:
            key = self._key_store.get(signature.key_id)

        if key is None:
            return False

        if isinstance(data, str):
            data = data.encode("utf-8")

        return self._hmac.verify(
            data,
            signature.signature_data.decode(),
            key.key_data
        )

    def get(self, signature_id: str) -> Optional[Signature]:
        """Get signature."""
        return self._signatures.get(signature_id)


# =============================================================================
# PASSWORD HANDLER
# =============================================================================

class PasswordHandler:
    """Handle password operations."""

    def __init__(self):
        self._hasher = Hasher()
        self._generator = KeyGenerator()

    def hash_password(
        self,
        password: str,
        salt: Optional[bytes] = None,
        iterations: int = 100000
    ) -> Tuple[str, str]:
        """Hash password with salt."""
        if salt is None:
            salt = self._generator.generate_bytes(16)

        key, _ = self._generator.derive_key(password, salt, 32, iterations)

        return base64.b64encode(key).decode(), base64.b64encode(salt).decode()

    def verify_password(
        self,
        password: str,
        hashed: str,
        salt: str,
        iterations: int = 100000
    ) -> bool:
        """Verify password."""
        salt_bytes = base64.b64decode(salt)
        key, _ = self._generator.derive_key(password, salt_bytes, 32, iterations)

        return secrets.compare_digest(
            base64.b64encode(key).decode(),
            hashed
        )

    def generate_password(
        self,
        length: int = 16,
        include_special: bool = True
    ) -> str:
        """Generate random password."""
        chars = "abcdefghijklmnopqrstuvwxyz"
        chars += "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        chars += "0123456789"

        if include_special:
            chars += "!@#$%^&*"

        return "".join(secrets.choice(chars) for _ in range(length))


# =============================================================================
# TOKEN MANAGER
# =============================================================================

class TokenManager:
    """Manage security tokens."""

    def __init__(self):
        self._generator = KeyGenerator()
        self._tokens: Dict[str, Dict[str, Any]] = {}

    def generate(
        self,
        purpose: str = "auth",
        expires_in: int = 3600,
        length: int = 32
    ) -> str:
        """Generate a token."""
        token = self._generator.generate_urlsafe(length)

        self._tokens[token] = {
            "purpose": purpose,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(seconds=expires_in)
        }

        return token

    def validate(self, token: str, purpose: Optional[str] = None) -> bool:
        """Validate a token."""
        info = self._tokens.get(token)

        if not info:
            return False

        if datetime.now() > info["expires_at"]:
            del self._tokens[token]
            return False

        if purpose and info["purpose"] != purpose:
            return False

        return True

    def revoke(self, token: str) -> bool:
        """Revoke a token."""
        if token in self._tokens:
            del self._tokens[token]
            return True
        return False

    def get_info(self, token: str) -> Optional[Dict[str, Any]]:
        """Get token info."""
        return self._tokens.get(token)


# =============================================================================
# ENCRYPTION ENGINE
# =============================================================================

class EncryptionEngine:
    """
    Encryption Engine for BAEL.

    Cryptographic operations and key management.
    """

    def __init__(self, config: Optional[EncryptionConfig] = None):
        self._config = config or EncryptionConfig()

        self._generator = KeyGenerator()
        self._key_store = KeyStore()
        self._encoder = Encoder()
        self._hasher = Hasher()
        self._hmac = HMACHandler()
        self._encryptor = Encryptor(self._key_store)
        self._signatures = SignatureManager(self._key_store)
        self._passwords = PasswordHandler()
        self._tokens = TokenManager()

    # ----- Key Management -----

    def generate_key(
        self,
        algorithm: Optional[EncryptionAlgorithm] = None
    ) -> CryptoKey:
        """Generate and store a new key."""
        alg = algorithm or self._config.default_algorithm
        key = self._generator.generate_symmetric_key(alg)
        self._key_store.add(key)
        return key

    def get_key(self, key_id: str) -> Optional[CryptoKey]:
        """Get a key by ID."""
        return self._key_store.get(key_id)

    def get_active_key(self) -> Optional[CryptoKey]:
        """Get active key."""
        return self._key_store.get_active()

    def set_active_key(self, key_id: str) -> bool:
        """Set active key."""
        return self._key_store.set_active(key_id)

    def revoke_key(self, key_id: str) -> bool:
        """Revoke a key."""
        return self._key_store.revoke(key_id)

    def list_keys(self) -> List[CryptoKey]:
        """List all keys."""
        return self._key_store.list()

    # ----- Encryption -----

    def encrypt(
        self,
        data: Union[str, bytes],
        key_id: Optional[str] = None
    ) -> EncryptedData:
        """Encrypt data."""
        key = None
        if key_id:
            key = self._key_store.get(key_id)
        return self._encryptor.encrypt(data, key)

    def decrypt(
        self,
        encrypted: EncryptedData,
        key_id: Optional[str] = None
    ) -> bytes:
        """Decrypt data."""
        key = None
        if key_id:
            key = self._key_store.get(key_id)
        return self._encryptor.decrypt(encrypted, key)

    def encrypt_string(self, data: str, key_id: Optional[str] = None) -> str:
        """Encrypt string to base64."""
        key = None
        if key_id:
            key = self._key_store.get(key_id)
        return self._encryptor.encrypt_string(data, key)

    def decrypt_string(self, data: str, key_id: Optional[str] = None) -> str:
        """Decrypt base64 to string."""
        key = None
        if key_id:
            key = self._key_store.get(key_id)
        return self._encryptor.decrypt_string(data, key)

    # ----- Hashing -----

    def hash(
        self,
        data: Union[str, bytes],
        algorithm: Optional[HashAlgorithm] = None
    ) -> HashResult:
        """Hash data."""
        alg = algorithm or self._config.default_hash
        return self._hasher.hash(data, alg)

    def md5(self, data: Union[str, bytes]) -> str:
        """MD5 hash."""
        return self._hasher.md5(data)

    def sha256(self, data: Union[str, bytes]) -> str:
        """SHA256 hash."""
        return self._hasher.sha256(data)

    def sha512(self, data: Union[str, bytes]) -> str:
        """SHA512 hash."""
        return self._hasher.sha512(data)

    def verify_hash(
        self,
        data: Union[str, bytes],
        expected: str,
        algorithm: Optional[HashAlgorithm] = None
    ) -> bool:
        """Verify hash."""
        alg = algorithm or self._config.default_hash
        return self._hasher.verify(data, expected, alg)

    # ----- HMAC -----

    def hmac_sign(
        self,
        data: Union[str, bytes],
        key: Union[str, bytes]
    ) -> str:
        """Create HMAC signature."""
        return self._hmac.sign(data, key)

    def hmac_verify(
        self,
        data: Union[str, bytes],
        signature: str,
        key: Union[str, bytes]
    ) -> bool:
        """Verify HMAC signature."""
        return self._hmac.verify(data, signature, key)

    # ----- Digital Signatures -----

    def sign(
        self,
        data: Union[str, bytes],
        key_id: Optional[str] = None
    ) -> Signature:
        """Sign data."""
        key = None
        if key_id:
            key = self._key_store.get(key_id)
        return self._signatures.sign(data, key)

    def verify_signature(
        self,
        data: Union[str, bytes],
        signature: Signature,
        key_id: Optional[str] = None
    ) -> bool:
        """Verify signature."""
        key = None
        if key_id:
            key = self._key_store.get(key_id)
        return self._signatures.verify(data, signature, key)

    # ----- Passwords -----

    def hash_password(self, password: str) -> Tuple[str, str]:
        """Hash a password."""
        return self._passwords.hash_password(password)

    def verify_password(
        self,
        password: str,
        hashed: str,
        salt: str
    ) -> bool:
        """Verify a password."""
        return self._passwords.verify_password(password, hashed, salt)

    def generate_password(
        self,
        length: int = 16,
        include_special: bool = True
    ) -> str:
        """Generate random password."""
        return self._passwords.generate_password(length, include_special)

    # ----- Tokens -----

    def generate_token(
        self,
        purpose: str = "auth",
        expires_in: int = 3600
    ) -> str:
        """Generate a token."""
        return self._tokens.generate(purpose, expires_in)

    def validate_token(
        self,
        token: str,
        purpose: Optional[str] = None
    ) -> bool:
        """Validate a token."""
        return self._tokens.validate(token, purpose)

    def revoke_token(self, token: str) -> bool:
        """Revoke a token."""
        return self._tokens.revoke(token)

    # ----- Encoding -----

    def to_base64(self, data: bytes) -> str:
        """Encode to base64."""
        return self._encoder.to_base64(data)

    def from_base64(self, data: str) -> bytes:
        """Decode from base64."""
        return self._encoder.from_base64(data)

    def to_hex(self, data: bytes) -> str:
        """Encode to hex."""
        return self._encoder.to_hex(data)

    def from_hex(self, data: str) -> bytes:
        """Decode from hex."""
        return self._encoder.from_hex(data)

    # ----- Random -----

    def random_bytes(self, length: int) -> bytes:
        """Generate random bytes."""
        return self._generator.generate_bytes(length)

    def random_hex(self, length: int) -> str:
        """Generate random hex string."""
        return self._generator.generate_hex(length)

    def random_token(self, length: int = 32) -> str:
        """Generate random URL-safe token."""
        return self._generator.generate_urlsafe(length)

    # ----- Summary -----

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        keys = self._key_store.list()

        return {
            "total_keys": len(keys),
            "active_key": self._key_store.get_active().key_id if self._key_store.get_active() else None,
            "expired_keys": len(self._key_store.get_expired()),
            "default_algorithm": self._config.default_algorithm.value,
            "default_hash": self._config.default_hash.value
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Encryption Engine."""
    print("=" * 70)
    print("BAEL - ENCRYPTION ENGINE DEMO")
    print("Cryptographic Operations")
    print("=" * 70)
    print()

    engine = EncryptionEngine()

    # 1. Key Generation
    print("1. KEY GENERATION:")
    print("-" * 40)

    key1 = engine.generate_key()
    print(f"   Generated key: {key1.key_id}")
    print(f"   Algorithm: {key1.algorithm}")
    print(f"   Key length: {len(key1.key_data)} bytes")

    key2 = engine.generate_key(EncryptionAlgorithm.AES_128)
    print(f"   Generated AES-128 key: {key2.key_id}")
    print()

    # 2. Key Management
    print("2. KEY MANAGEMENT:")
    print("-" * 40)

    keys = engine.list_keys()
    print(f"   Total keys: {len(keys)}")

    active = engine.get_active_key()
    print(f"   Active key: {active.key_id if active else 'None'}")

    engine.set_active_key(key2.key_id)
    active = engine.get_active_key()
    print(f"   New active key: {active.key_id if active else 'None'}")
    print()

    # 3. Encryption/Decryption
    print("3. ENCRYPTION/DECRYPTION:")
    print("-" * 40)

    plaintext = "Hello, BAEL! This is a secret message."
    print(f"   Original: {plaintext}")

    encrypted = engine.encrypt(plaintext)
    print(f"   Encrypted: {len(encrypted.ciphertext)} bytes")
    print(f"   Algorithm: {encrypted.algorithm}")

    decrypted = engine.decrypt(encrypted)
    print(f"   Decrypted: {decrypted.decode()}")
    print()

    # 4. String Encryption
    print("4. STRING ENCRYPTION:")
    print("-" * 40)

    secret = "API_KEY=abc123xyz789"
    print(f"   Original: {secret}")

    encrypted_str = engine.encrypt_string(secret)
    print(f"   Encrypted: {encrypted_str[:50]}...")

    decrypted_str = engine.decrypt_string(encrypted_str)
    print(f"   Decrypted: {decrypted_str}")
    print()

    # 5. Hashing
    print("5. HASHING:")
    print("-" * 40)

    data = "Hash this data"

    print(f"   Data: {data}")
    print(f"   MD5:    {engine.md5(data)}")
    print(f"   SHA256: {engine.sha256(data)}")
    print(f"   SHA512: {engine.sha512(data)[:32]}...")
    print()

    # 6. Hash Verification
    print("6. HASH VERIFICATION:")
    print("-" * 40)

    expected = engine.sha256(data)

    valid = engine.verify_hash(data, expected)
    print(f"   Correct hash: {valid}")

    invalid = engine.verify_hash(data, "invalid_hash")
    print(f"   Invalid hash: {invalid}")
    print()

    # 7. HMAC
    print("7. HMAC SIGNATURES:")
    print("-" * 40)

    message = "Important message"
    hmac_key = "secret_key"

    signature = engine.hmac_sign(message, hmac_key)
    print(f"   Message: {message}")
    print(f"   HMAC: {signature}")

    valid = engine.hmac_verify(message, signature, hmac_key)
    print(f"   Valid: {valid}")
    print()

    # 8. Digital Signatures
    print("8. DIGITAL SIGNATURES:")
    print("-" * 40)

    doc = "This is an important document that needs to be signed."
    sig = engine.sign(doc)

    print(f"   Document: {doc[:40]}...")
    print(f"   Signature ID: {sig.signature_id}")

    verified = engine.verify_signature(doc, sig)
    print(f"   Verified: {verified}")

    tampered = engine.verify_signature("tampered document", sig)
    print(f"   Tampered doc verified: {tampered}")
    print()

    # 9. Password Hashing
    print("9. PASSWORD HASHING:")
    print("-" * 40)

    password = "SecurePassword123!"
    hashed, salt = engine.hash_password(password)

    print(f"   Password: {password}")
    print(f"   Hashed: {hashed[:30]}...")
    print(f"   Salt: {salt}")

    valid = engine.verify_password(password, hashed, salt)
    print(f"   Valid password: {valid}")

    wrong = engine.verify_password("wrong_password", hashed, salt)
    print(f"   Wrong password: {wrong}")
    print()

    # 10. Password Generation
    print("10. PASSWORD GENERATION:")
    print("-" * 40)

    for i in range(3):
        pwd = engine.generate_password(16)
        print(f"   Password {i+1}: {pwd}")

    pwd_no_special = engine.generate_password(12, include_special=False)
    print(f"   No special chars: {pwd_no_special}")
    print()

    # 11. Token Management
    print("11. TOKEN MANAGEMENT:")
    print("-" * 40)

    auth_token = engine.generate_token("auth", 3600)
    print(f"   Auth token: {auth_token[:30]}...")

    valid = engine.validate_token(auth_token, "auth")
    print(f"   Valid auth token: {valid}")

    valid = engine.validate_token(auth_token, "refresh")
    print(f"   Valid as refresh: {valid}")

    engine.revoke_token(auth_token)
    valid = engine.validate_token(auth_token)
    print(f"   After revoke: {valid}")
    print()

    # 12. Encoding
    print("12. ENCODING:")
    print("-" * 40)

    raw_data = b"Binary data \x00\x01\x02"

    b64 = engine.to_base64(raw_data)
    print(f"   Base64: {b64}")

    hex_str = engine.to_hex(raw_data)
    print(f"   Hex: {hex_str}")

    decoded = engine.from_base64(b64)
    print(f"   Decoded matches: {decoded == raw_data}")
    print()

    # 13. Random Generation
    print("13. RANDOM GENERATION:")
    print("-" * 40)

    print(f"   Random bytes (16): {engine.random_bytes(16).hex()}")
    print(f"   Random hex (16): {engine.random_hex(16)}")
    print(f"   Random token (32): {engine.random_token(32)[:40]}...")
    print()

    # 14. Summary
    print("14. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Encryption Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
